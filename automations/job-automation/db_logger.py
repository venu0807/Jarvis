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
                timestamp TEXT
            )
        """)
        conn.commit()

def save_jobs_to_db(results: list[ApplicationResult]):
    if not results:
        return
        
    init_db()
    now = datetime.datetime.now().isoformat()
    
    with sqlite3.connect(DB_PATH) as conn:
        for r in results:
            job = r.job
            try:
                conn.execute("""
                    INSERT INTO jobs (id, title, company, location, portal, url, description, status, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET 
                        status=excluded.status, 
                        timestamp=excluded.timestamp,
                        description=CASE WHEN excluded.description != '' THEN excluded.description ELSE jobs.description END
                """, (
                    job.get("id", ""),
                    job.get("title", ""),
                    job.get("company", ""),
                    job.get("location", ""),
                    job.get("portal", ""),
                    job.get("url", ""),
                    job.get("description", ""),
                    r.status,
                    now
                ))
            except Exception as e:
                print(f"⚠️ Could not insert job {job.get('id', 'unknown')} into DB: {e}")
        conn.commit()

    # Sync to PostgreSQL if applied successfully — only when explicitly
    # configured (PG_PASSWORD set). Previously defaulted to pinterest_db with
    # an empty password, silently writing job data to the wrong DB.
    applied_results = [r for r in results if r.status == "applied"]
    if applied_results and os.getenv("PG_PASSWORD"):
        try:
            import psycopg2  # optional — job DB must work without PG
            pg_conn = psycopg2.connect(
                dbname=os.getenv("PG_DB", "pinterest_db"),
                user=os.getenv("PG_USER", "venu"),
                password=os.getenv("PG_PASSWORD"),
                host=os.getenv("PG_HOST", "127.0.0.1"),
            )
            pg_cur = pg_conn.cursor()
            for r in applied_results:
                job_payload = json.dumps(r.job)
                pg_cur.execute(
                    "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
                    ("job_bot", "jobs.applied", job_payload)
                )
            pg_conn.commit()
            pg_cur.close()
            pg_conn.close()
            print(f"✅ Synced {len(applied_results)} applied jobs to PostgreSQL (events table).")
        except Exception as e:
            print(f"⚠️ Failed to sync to PostgreSQL: {e}")
    elif applied_results:
        print("ℹ️  PG_PASSWORD not set — skipping PostgreSQL sync (jobs saved to output/jobs.db)")
