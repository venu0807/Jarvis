#!/usr/bin/env python3
"""
cleanup_bot.py — Prune stale skipped/error jobs older than 30 days from jobs.db

Run nightly via cron: 0 0 * * * python3 cleanup_bot.py
"""
import sqlite3
import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "output" / "jobs.db"
KEEP_DAYS = 30


def main():
    if not DB_PATH.exists():
        print(f"DB not found: {DB_PATH}")
        return

    cutoff = (datetime.datetime.now() - datetime.timedelta(days=KEEP_DAYS)).isoformat()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("""
        DELETE FROM jobs
        WHERE status IN ('skipped', 'error')
          AND timestamp <= ?
    """, (cutoff,))
    deleted = cur.rowcount
    conn.commit()

    # Also vacuum to reclaim disk space
    conn.execute("VACUUM")
    conn.close()

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    print(f"[{now}] 🗑️  Cleanup complete: removed {deleted} stale jobs (>{KEEP_DAYS} days old, status=skipped/error)")


if __name__ == "__main__":
    main()
