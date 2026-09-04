"""test_db_tracker.py — Tests for the upgraded SentTracker.

Covers:
- Tier + template_id columns (migration safety)
- Reply tracking + reply_rate calculation
- Follow-up scheduling + due detection
- CSV export
- Auto-scheduling on record_sent
- Sentiment + per-tier stats

Run:  python test_db_tracker.py
"""

import datetime
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(__file__))
from db_tracker import SentTracker


class TestSentTracker(unittest.TestCase):

    def setUp(self):
        # Fresh DB for each test
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.tmp.close()
        self.db_path = self.tmp.name
        self.tracker = SentTracker(db_path=self.db_path)

    def tearDown(self):
        try:
            os.unlink(self.db_path)
        except OSError:
            pass

    # ── Tier + template_id columns ──────────────────────────────────────

    def test_record_sent_with_tier(self):
        self.tracker.record_sent(
            "a@b.com", "Python Developer", "TestCo", "Subject",
            tier="T1", template_id="T1",
        )
        stats = self.tracker.stats()
        self.assertEqual(stats["total_sent"], 1)
        self.assertEqual(stats["per_tier"].get("T1"), 1)
        self.assertEqual(stats["per_role"].get("Python Developer"), 1)

    def test_migrate_add_column_error_paths(self):
        import sqlite3
        from unittest.mock import MagicMock

        # Test 1: Duplicate column name is ignored
        mock_conn = MagicMock()
        mock_conn.execute.side_effect = sqlite3.OperationalError("duplicate column name: tier")

        # This should not raise an exception
        self.tracker._migrate_add_column(mock_conn, "sent_emails", "tier", "TEXT DEFAULT 'T3'")

        # Test 2: Other operational errors are raised
        mock_conn.execute.side_effect = sqlite3.OperationalError("no such table: fake_table")

        with self.assertRaises(sqlite3.OperationalError):
            self.tracker._migrate_add_column(mock_conn, "fake_table", "tier", "TEXT DEFAULT 'T3'")

    def test_migration_from_v1_schema(self):
        """Simulate a v1 DB without tier/template_id columns, then init."""
        import sqlite3
        # Drop tracker, create v1-style DB
        del self.tracker
        v1_path = self.db_path + ".v1"
        with sqlite3.connect(v1_path) as conn:
            conn.execute("""
                CREATE TABLE sent_emails (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient TEXT NOT NULL,
                    role TEXT NOT NULL,
                    company TEXT DEFAULT '',
                    subject TEXT DEFAULT '',
                    sent_at TEXT NOT NULL,
                    is_fallback INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'sent'
                )
            """)
            conn.execute(
                "INSERT INTO sent_emails (recipient, role, sent_at) VALUES (?, ?, ?)",
                ("legacy@example.com", "Legacy Role", "2026-01-01T00:00:00"),
            )
            conn.commit()
        # Now init tracker against the v1 DB
        tracker = SentTracker(db_path=v1_path)
        # Should auto-migrate
        stats = tracker.stats()
        self.assertEqual(stats["total_sent"], 1)  # legacy row preserved
        # Should be able to record new rows
        tracker.record_sent("new@example.com", "New", "NewCo", "Sub",
                            tier="T2", template_id="T2")
        self.assertEqual(tracker.stats()["total_sent"], 2)
        self.assertEqual(tracker.stats()["per_tier"].get("T2"), 1)
        os.unlink(v1_path)

    # ── Reply tracking ──────────────────────────────────────────────────

    def test_record_reply(self):
        self.tracker.record_sent("a@b.com", "Python", "Co", "Sub")
        self.tracker.record_reply(
            "a@b.com", "Re: Sub", "Thanks for reaching out!", sentiment="positive",
        )
        stats = self.tracker.stats()
        self.assertEqual(stats["total_replied"], 1)
        self.assertEqual(stats["reply_rate"], 1.0)

    def test_reply_rate_calculation(self):
        # 3 sends, 1 reply → 33.3%
        self.tracker.record_sent("a@b.com", "Role", "Co", "Sub")
        self.tracker.record_sent("c@d.com", "Role", "Co", "Sub")
        self.tracker.record_sent("e@f.com", "Role", "Co", "Sub")
        self.tracker.record_reply("a@b.com", "Re: Sub", "Hi")
        rate = self.tracker.stats()["reply_rate"]
        self.assertAlmostEqual(rate, 1/3, places=2)

    def test_get_replies(self):
        self.tracker.record_sent("a@b.com", "Role", "Co", "Sub")
        self.tracker.record_reply("a@b.com", "Re: Sub", "Hi", sentiment="positive")
        replies = self.tracker.get_replies()
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]["recipient"], "a@b.com")
        self.assertEqual(replies[0]["sentiment"], "positive")

    # ── Follow-up scheduling ────────────────────────────────────────────

    def test_auto_schedule_followup_on_record_sent(self):
        self.tracker.record_sent("a@b.com", "Role", "Co", "Sub")
        # Should auto-schedule Day-5 follow-up
        pending = self.tracker.stats()["pending_followups"]
        self.assertEqual(pending, 1)

    def test_no_double_schedule(self):
        """Two record_sent to same recipient should not double-schedule."""
        self.tracker.record_sent("a@b.com", "Role", "Co", "Sub")
        self.tracker.record_sent("a@b.com", "Role", "Co", "Sub 2")
        # Should still be 1 pending follow-up (not 2)
        pending = self.tracker.stats()["pending_followups"]
        self.assertEqual(pending, 1)

    def test_get_due_followups(self):
        # Schedule a follow-up for yesterday
        self.tracker.schedule_followup(
            "a@b.com", send_date="2020-01-01", template_id="T5",
        )
        due = self.tracker.get_due_followups()
        self.assertEqual(len(due), 1)
        self.assertEqual(due[0]["recipient"], "a@b.com")
        self.assertEqual(due[0]["template_id"], "T5")

    def test_mark_followup_sent(self):
        self.tracker.schedule_followup("a@b.com", send_date="2020-01-01")
        due = self.tracker.get_due_followups()
        self.assertEqual(len(due), 1)
        self.tracker.mark_followup_sent(due[0]["id"])
        # Should not be due anymore
        due_after = self.tracker.get_due_followups()
        self.assertEqual(len(due_after), 0)

    # ── CSV export ──────────────────────────────────────────────────────

    def test_export_to_csv(self):
        self.tracker.record_sent("a@b.com", "Role", "Co", "Sub", tier="T1", template_id="T1")
        self.tracker.record_reply("a@b.com", "Re: Sub", "Hi")
        out_path = self.db_path + ".csv"
        self.tracker.export_to_csv(out_path)
        self.assertTrue(os.path.exists(out_path))
        # Read + verify content
        with open(out_path, "r") as f:
            content = f.read()
        self.assertIn("recipient", content)
        self.assertIn("a@b.com", content)
        self.assertIn("T1", content)
        os.unlink(out_path)

    # ── Per-tier stats ──────────────────────────────────────────────────

    def test_per_tier_stats(self):
        self.tracker.record_sent("a@b.com", "Role", "Co", "Sub", tier="T1", template_id="T1")
        self.tracker.record_sent("c@d.com", "Role", "Co", "Sub", tier="T1", template_id="T1")
        self.tracker.record_sent("e@f.com", "Role", "Co", "Sub", tier="T2", template_id="T2")
        stats = self.tracker.stats()
        self.assertEqual(stats["per_tier"]["T1"], 2)
        self.assertEqual(stats["per_tier"]["T2"], 1)

    # ── Dedup still works ───────────────────────────────────────────────

    def test_already_sent_to_still_works(self):
        self.tracker.record_sent("a@b.com", "Role", "Co", "Sub")
        self.assertTrue(self.tracker.already_sent_to("a@b.com"))
        self.assertFalse(self.tracker.already_sent_to("never@seen.com"))


class TestTemplates(unittest.TestCase):

    def test_list_templates(self):
        from templates import list_templates
        templates = list_templates()
        self.assertEqual(set(templates), {"T1", "T2", "T3", "T4", "T5"})

    def test_get_template(self):
        from templates import get_template
        for tid in ["T1", "T2", "T3", "T4", "T5"]:
            body = get_template(tid)
            self.assertIn("{first_name}", body)
            self.assertIn("{role}", body)
            self.assertIn("{company}", body)

    def test_default_template(self):
        from templates import get_template
        body = get_template("UNKNOWN_ID")
        # Should fall back to T2 (hiring manager DM)
        self.assertIn("{first_name}", body)
        self.assertIn("MCA graduate", body)
        # T2 should mention portfolio or projects
        self.assertIn("github.com/venu0807", body)


if __name__ == "__main__":
    unittest.main(verbosity=2)
