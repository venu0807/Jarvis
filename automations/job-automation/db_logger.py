"""db_logger.py — Centralized database logger for job applications."""

try:
    from telegram_notifier import notify_daily_summary, notify_crash
    _TG_LOGGER = True
except ImportError:
    _TG_LOGGER = False

import os
import sqlite3
import datetime
import json
from pathlib import Path
from portals.base import ApplicationResult

DB_PATH = Path(__file__).parent / "output" / "jobs.db"

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id TEXT PRIMARY KEY,
                title TEXT,
                company TEXT,
                location TEXT,
                portal TEXT,
                url TEXT,
                description TEXT,
                status TEXT,
                skip_reason TEXT,
                timestamp TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                id TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS followups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                company TEXT,
                sent_at TEXT NOT NULL,
                status TEXT DEFAULT 'sent'
            )
        """)
        conn.commit()

def record_seen_job(job_id: str):
    """Mark a job ID as seen so scrapers skip it."""
    if not job_id:
        return
    init_db()
    now = datetime.datetime.now().isoformat()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("INSERT OR IGNORE INTO seen_jobs (id, first_seen) VALUES (?, ?)", (job_id, now))
        conn.commit()

def is_job_seen(job_id: str) -> bool:
    """Check if a job has already been evaluated."""
    if not job_id:
        return False
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute("SELECT 1 FROM seen_jobs WHERE id = ?", (job_id,)).fetchone()
        return row is not None

def save_jobs_to_db(results: list[ApplicationResult]):
    if not results:
        return
        
    init_db()
    now = datetime.datetime.now().isoformat()
    
    with sqlite3.connect(DB_PATH) as conn:
        jobs_data = []
        seen_jobs_data = []
        for r in results:
            job = r.job
            job_id = job.get("id", "")
            if not job_id:
                continue
                
            jobs_data.append((
                job_id,
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("portal", ""),
                job.get("url", ""),
                job.get("description", ""),
                r.status,
                getattr(r, "skip_reason", None) or getattr(r, "reason", None) or "",
                now
            ))
            seen_jobs_data.append((job_id, now))

        if jobs_data:
            try:
                conn.executemany("""
                    INSERT INTO jobs (id, title, company, location, portal, url, description, status, skip_reason, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET 
                        status=excluded.status, 
                        skip_reason=COALESCE(excluded.skip_reason, jobs.skip_reason),
                        timestamp=excluded.timestamp,
                        description=CASE WHEN excluded.description != '' THEN excluded.description ELSE jobs.description END
                """, jobs_data)
                conn.executemany("INSERT OR IGNORE INTO seen_jobs (id, first_seen) VALUES (?, ?)", seen_jobs_data)
            except Exception as e:
                # Fallback to individual inserts to preserve error handling per row
                for job_data, seen_data in zip(jobs_data, seen_jobs_data):
                    try:
                        conn.execute("""
                            INSERT INTO jobs (id, title, company, location, portal, url, description, status, skip_reason, timestamp)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ON CONFLICT(id) DO UPDATE SET
                                status=excluded.status,
                                skip_reason=COALESCE(excluded.skip_reason, jobs.skip_reason),
                                timestamp=excluded.timestamp,
                                description=CASE WHEN excluded.description != '' THEN excluded.description ELSE jobs.description END
                        """, job_data)
                        conn.execute("INSERT OR IGNORE INTO seen_jobs (id, first_seen) VALUES (?, ?)", seen_data)
                    except Exception as inner_e:
                        print(f"⚠️ Could not insert job {job_data[0]} into DB: {inner_e}")

        conn.commit()

    applied_results = [r for r in results if r.status == "applied"]
    if applied_results and os.getenv("PG_PASSWORD"):
        try:
            import psycopg2
            pg_conn = psycopg2.connect(
                dbname=os.getenv("PG_DB", "pinterest_db"),
                user=os.getenv("PG_USER", "venu"),
                password=os.getenv("PG_PASSWORD"),
                host=os.getenv("PG_HOST", "127.0.0.1"),
            )
            pg_cur = pg_conn.cursor()

            pg_data = [("job_bot", "jobs.applied", json.dumps(r.job)) for r in applied_results]
            if pg_data:
                pg_cur.executemany(
                    "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
                    pg_data
                )

            pg_conn.commit()
            pg_cur.close()
            pg_conn.close()
            print(f"✅ Synced {len(applied_results)} applied jobs to PostgreSQL (events table).")
        except Exception as e:
            print(f"⚠️ Failed to sync to PostgreSQL: {e}")
