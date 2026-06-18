"""
db_tracker.py — SQLite-based dedup + tracking for LinkedIn outreach.

Replaces the JSONL-only sent_log tracking with a proper database that:
  - Prevents sending duplicate emails to the same recipient
  - Tracks per-role daily caps
  - Persists across runs so restarts don't re-send

Usage:
    tracker = SentTracker()
    
    # Check if we can send to this recipient today
    if tracker.can_send_to("recruiter@example.com", role="Python Developer"):
        # ... send email ...
        tracker.record_sent("recruiter@example.com", "Python Developer", 
                            "Some Company", "Interest in Python/Django Role")

    # Check daily cap
    remaining = tracker.daily_remaining(cap=15)
    fallback_remaining = tracker.daily_fallback_remaining(cap=30)
"""

from __future__ import annotations

import datetime
import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).resolve().parent / "sent_tracker.db"


class SentTracker:
    """Persistent dedup + rate-limit tracker using SQLite."""

    def __init__(self, db_path: str | Path = DB_PATH):
        self._path = Path(db_path)
        self._init_db()

    # ── Schema ────────────────────────────────────────────────────────────

    def _init_db(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self._path) as conn:
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
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sent_recipient 
                ON sent_emails(recipient)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sent_date 
                ON sent_emails(sent_at)
            """)
            conn.commit()

    # ── Connection helper ────────────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

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
    ) -> None:
        """Record that an email was sent."""
        now = datetime.datetime.now().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sent_emails "
                "(recipient, role, company, subject, sent_at, is_fallback, status) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (recipient, role, company, subject, now, 1 if is_fallback else 0, status),
            )
            conn.commit()

    # ── Stats ────────────────────────────────────────────────────────────

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
            return {
                "total_sent": total,
                "today_sent": today,
                "per_role": dict(roles),
            }
