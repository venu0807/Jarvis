import sqlite3
import datetime
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
