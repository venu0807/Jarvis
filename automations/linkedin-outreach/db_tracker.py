"""
db_tracker.py — SQLite-based dedup + tracking for LinkedIn outreach.

Replaces the JSONL-only sent_log tracking with a proper database that:
  - Prevents sending duplicate emails to the same recipient
  - Tracks per-role daily caps
  - Persists across runs so restarts don't re-send
  - Tracks replies (was missing in v1 — added per 2-month plan)
  - Tracks follow-ups scheduled vs sent
  - Generates CSV for Google Sheets import

Usage:
    tracker = SentTracker()

    # Check if we can send to this recipient today
    if tracker.can_send_to("recruiter@example.com", role="Python Developer"):
        # ... send email ...
        tracker.record_sent("recruiter@example.com", "Python Developer",
                            "Some Company", "Interest in Python/Django Role")

    # Reply tracking
    tracker.record_reply("recruiter@example.com", subject="Re: Application",
                        snippet="Thanks for reaching out...")

    # Follow-up scheduling
    tracker.schedule_followup("recruiter@example.com", send_date="2026-08-29",
                              template_id="T5")

    # Stats + export
    stats = tracker.stats()
    tracker.export_to_csv("outreach_export.csv")
"""

from __future__ import annotations

import csv
import datetime
import os
import sqlite3
from pathlib import Path
import re
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "sent_tracker.db"


class SentTracker:
    """Persistent dedup + rate-limit + reply tracker using SQLite."""

    def __init__(self, db_path: str | Path = DB_PATH):
        self._path = Path(db_path)
        self._init_db()

    # ── Schema ───────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        # Use timeout to avoid WinError 32 when file is locked briefly
        with sqlite3.connect(self._path, timeout=10) as conn:
            # ── sent_emails table (with new tier + template_id columns) ──
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sent_emails (
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
            # Migration: add tier + template_id columns if missing (for v1 DBs)
            self._migrate_add_column(conn, "sent_emails", "tier", "TEXT DEFAULT 'T3'")
            self._migrate_add_column(conn, "sent_emails", "template_id", "TEXT DEFAULT 'T2'")
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sent_recipient
                ON sent_emails(recipient)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sent_date
                ON sent_emails(sent_at)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sent_tier
                ON sent_emails(tier)
            """)
            # ── replies table ───────────────────────────────────
            conn.execute("""
                CREATE TABLE IF NOT EXISTS replies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient TEXT NOT NULL,
                    subject TEXT DEFAULT '',
                    snippet TEXT DEFAULT '',
                    received_at TEXT NOT NULL,
                    sentiment TEXT DEFAULT 'neutral'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_replies_recipient
                ON replies(recipient)
            """)
            # ── follow-ups table ────────────────────────────────
            conn.execute("""
                CREATE TABLE IF NOT EXISTS followups (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recipient TEXT NOT NULL,
                    scheduled_for TEXT NOT NULL,
                    template_id TEXT DEFAULT 'T5',
                    sent_at TEXT DEFAULT NULL,
                    status TEXT DEFAULT 'pending'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_followups_recipient
                ON followups(recipient)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_followups_status
                ON followups(status)
            """)
            conn.commit()

    def _migrate_add_column(self, conn, table: str, column: str, definition: str) -> None:
        """Add a column to an existing table if it doesn't exist (safe migration)."""
        if not re.match(r"^[A-Za-z0-9_]+$", table):
            raise ValueError(f"Invalid table name: {table}")
        if not re.match(r"^[A-Za-z0-9_]+$", column):
            raise ValueError(f"Invalid column name: {column}")
        if not re.match(r"^[A-Za-z0-9_ ']+$", definition):
            raise ValueError(f"Invalid column definition: {definition}")

        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
            # Only print during actual migrations, not during tests
            if os.environ.get("JARVIS_TRACKER_VERBOSE") == "1":
                print(f"  [migration] Added column {table}.{column}")
        except sqlite3.OperationalError as e:
            # "duplicate column name" = already exists, that's fine
            if "duplicate column" not in str(e):
                raise

    # ── Connection helper ────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        # timeout avoids WinError 32 / "database is locked" on Windows
        conn = sqlite3.connect(self._path, timeout=10)
        # Allow concurrent reads, serialize writes
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    # ── Dedup check ──────────────────────────────────────────────────────

    def already_sent_to(self, recipient: str, days: int = 30) -> bool:
        """Check if we've sent to this recipient in the last `days` days."""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM sent_emails WHERE recipient = ? AND sent_at > ? LIMIT 1",
                (recipient, cutoff),
            ).fetchone()
            return row is not None

    # ── Cap checks ───────────────────────────────────────────────────────

    def today_count(self, is_fallback: bool = False) -> int:
        """Number of (non-fallback / fallback) emails sent today."""
        today = datetime.date.today().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sent_emails "
                "WHERE sent_at >= ? AND is_fallback = ?",
                (today, 1 if is_fallback else 0),
            ).fetchone()
            return row[0] if row else 0

    def today_role_count(self, role: str) -> int:
        """Number of emails sent today for a specific role."""
        today = datetime.date.today().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sent_emails "
                "WHERE sent_at >= ? AND role = ? AND is_fallback = 0",
                (today, role),
            ).fetchone()
            return row[0] if row else 0

    def today_tier_count(self, tier: str) -> int:
        """Number of emails sent today for a specific tier (T1/T2/T3)."""
        today = datetime.date.today().isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) FROM sent_emails "
                "WHERE sent_at >= ? AND tier = ? AND is_fallback = 0",
                (today, tier),
            ).fetchone()
            return row[0] if row else 0

    def can_send(
        self,
        recipient: str,
        role: str,
        daily_cap: int = 15,
        per_role_cap: int = 2,
    ) -> bool:
        """Can we send to this recipient today?"""
        if self.already_sent_to(recipient):
            return False
        if self.today_count() >= daily_cap:
            return False
        if self.today_role_count(role) >= per_role_cap:
            return False
        return True

    def can_send_fallback(self, recipient: str, fallback_cap: int = 30) -> bool:
        """Can we send a fallback email today?"""
        if self.already_sent_to(recipient):
            return False
        if self.today_count(is_fallback=True) >= fallback_cap:
            return False
        return True

    def daily_remaining(self, cap: int = 15) -> int:
        """How many non-fallback emails can we still send today."""
        return max(0, cap - self.today_count())

    def daily_fallback_remaining(self, cap: int = 30) -> int:
        """How many fallback emails can we still send today."""
        return max(0, cap - self.today_count(is_fallback=True))

    # ── Record ───────────────────────────────────────────────────────────

    def record_sent(
        self,
        recipient: str,
        role: str,
        company: str = "",
        subject: str = "",
        is_fallback: bool = False,
        status: str = "sent",
        tier: str = "T3",
        template_id: str = "T2",
    ) -> None:
        """Record that an email was sent. Auto-schedules a follow-up
        unless one is already pending for this recipient."""
        now = datetime.datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sent_emails "
                "(recipient, role, company, subject, sent_at, is_fallback, status, tier, template_id) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (recipient, role, company, subject, now,
                 1 if is_fallback else 0, status, tier, template_id),
            )
            conn.commit()

        # Auto-schedule Day 5 follow-up if not already pending
        if not is_fallback:
            self.schedule_followup(recipient, days=5, template_id="T5")

    # ── Reply tracking (NEW) ────────────────────────────────────────────

    def record_reply(
        self,
        recipient: str,
        subject: str = "",
        snippet: str = "",
        sentiment: str = "neutral",
    ) -> None:
        """Record a reply received from a recruiter."""
        now = datetime.datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO replies "
                "(recipient, subject, snippet, received_at, sentiment) "
                "VALUES (?, ?, ?, ?, ?)",
                (recipient, subject, snippet, now, sentiment),
            )
            # Also update sent_emails.status to 'replied'
            conn.execute(
                "UPDATE sent_emails SET status = 'replied' "
                "WHERE recipient = ? AND sent_at = "
                "(SELECT MAX(sent_at) FROM sent_emails WHERE recipient = ?)",
                (recipient, recipient),
            )
            conn.commit()

    def get_replies(self, days: int = 30) -> list:
        """Return list of replies received in the last N days."""
        cutoff = (datetime.datetime.now() - datetime.timedelta(days=days)).isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT recipient, subject, snippet, received_at, sentiment "
                "FROM replies WHERE received_at > ? ORDER BY received_at DESC",
                (cutoff,),
            ).fetchall()
            return [
                {"recipient": r[0], "subject": r[1], "snippet": r[2],
                 "received_at": r[3], "sentiment": r[4]}
                for r in rows
            ]

    def reply_rate(self) -> float:
        """Overall reply rate as a fraction (0.0 - 1.0)."""
        with self._conn() as conn:
            total = conn.execute(
                "SELECT COUNT(*) FROM sent_emails WHERE is_fallback = 0"
            ).fetchone()[0]
            replied = conn.execute(
                "SELECT COUNT(*) FROM sent_emails "
                "WHERE is_fallback = 0 AND status = 'replied'"
            ).fetchone()[0]
            return (replied / total) if total > 0 else 0.0

    # ── Follow-up scheduling (NEW) ───────────────────────────────────────

    def schedule_followup(
        self,
        recipient: str,
        days: int = 5,
        template_id: str = "T5",
        send_date: Optional[str] = None,
    ) -> None:
        """Schedule a follow-up email N days from now (or on a specific date)."""
        if send_date is None:
            follow_up_date = (
                datetime.date.today() + datetime.timedelta(days=days)
            ).isoformat()
        else:
            follow_up_date = send_date

        with self._conn() as conn:
            # Check if one is already pending
            existing = conn.execute(
                "SELECT 1 FROM followups WHERE recipient = ? AND status = 'pending'",
                (recipient,),
            ).fetchone()
            if existing:
                return  # Don't double-schedule
            conn.execute(
                "INSERT INTO followups "
                "(recipient, scheduled_for, template_id, status) "
                "VALUES (?, ?, ?, 'pending')",
                (recipient, follow_up_date, template_id),
            )
            conn.commit()

    def get_due_followups(self) -> list:
        """Return list of follow-ups due today or earlier (not yet sent)."""
        today = datetime.date.today().isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, recipient, scheduled_for, template_id "
                "FROM followups WHERE status = 'pending' "
                "AND scheduled_for <= ? ORDER BY scheduled_for",
                (today,),
            ).fetchall()
            return [
                {"id": r[0], "recipient": r[1],
                 "scheduled_for": r[2], "template_id": r[3]}
                for r in rows
            ]

    def mark_followup_sent(self, followup_id: int) -> None:
        """Mark a follow-up as sent."""
        now = datetime.datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "UPDATE followups SET status = 'sent', sent_at = ? WHERE id = ?",
                (now, followup_id),
            )
            conn.commit()

    # ── Stats + export (NEW) ─────────────────────────────────────────────

    def stats(self) -> dict:
        """Return summary stats for the dashboard."""
        with self._conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM sent_emails").fetchone()[0]
            today = conn.execute(
                "SELECT COUNT(*) FROM sent_emails WHERE sent_at >= ?",
                (datetime.date.today().isoformat(),),
            ).fetchone()[0]
            roles = conn.execute(
                "SELECT role, COUNT(*) as cnt FROM sent_emails "
                "WHERE is_fallback = 0 GROUP BY role ORDER BY cnt DESC"
            ).fetchall()
            tiers = conn.execute(
                "SELECT tier, COUNT(*) as cnt FROM sent_emails "
                "WHERE is_fallback = 0 GROUP BY tier ORDER BY cnt DESC"
            ).fetchall()
            replied = conn.execute(
                "SELECT COUNT(*) FROM sent_emails "
                "WHERE is_fallback = 0 AND status = 'replied'"
            ).fetchone()[0]
            pending_followups = conn.execute(
                "SELECT COUNT(*) FROM followups WHERE status = 'pending'"
            ).fetchone()[0]
            return {
                "total_sent": total,
                "today_sent": today,
                "total_replied": replied,
                "reply_rate": (replied / total) if total > 0 else 0.0,
                "pending_followups": pending_followups,
                "per_role": dict(roles),
                "per_tier": dict(tiers),
            }

    def export_to_csv(self, output_path: str) -> None:
        """Export all sent emails + replies to a single CSV for Google Sheets import."""
        with self._conn() as conn:
            # Combine sent_emails and replies via LEFT JOIN
            rows = conn.execute("""
                SELECT
                    se.recipient,
                    se.role,
                    se.company,
                    se.tier,
                    se.template_id,
                    se.subject,
                    se.sent_at,
                    se.is_fallback,
                    se.status,
                    r.received_at AS replied_at,
                    r.sentiment
                FROM sent_emails se
                LEFT JOIN replies r ON se.recipient = r.recipient
                ORDER BY se.sent_at DESC
            """).fetchall()

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "recipient", "role", "company", "tier", "template_id",
                "subject", "sent_at", "is_fallback", "status",
                "replied_at", "sentiment",
            ])
            for row in rows:
                writer.writerow(row)
