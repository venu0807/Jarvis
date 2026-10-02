import time
import json
import os
import psycopg2
import psycopg2.extras
from portals.base import ApplicationResult

# Mock data
class MockApplicationResult:
    def __init__(self, i):
        self.status = "applied"
        self.job = {"id": f"job_{i}", "title": f"Engineer {i}", "company": "Test Co", "location": "Remote", "portal": "test", "url": "http://test", "description": "Test test"}

results = [MockApplicationResult(i) for i in range(1000)]
applied_results = [r for r in results if r.status == "applied"]

def run_benchmark():
    try:
        pg_conn = psycopg2.connect(
            dbname=os.getenv("PG_DB", "pinterest_db"),
            user=os.getenv("PG_USER", "venu"),
            password=os.getenv("PG_PASSWORD", "postgres"), # Use fallback for test
            host=os.getenv("PG_HOST", "127.0.0.1"),
        )
        pg_cur = pg_conn.cursor()

        # Ensure table exists for test
        pg_cur.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                source TEXT,
                event_type TEXT,
                payload JSONB
            )
        """)
        pg_conn.commit()

        # Clear table
        pg_cur.execute("TRUNCATE TABLE events")
        pg_conn.commit()

        start = time.time()

        for r in applied_results:
            job_payload = json.dumps(r.job)
            pg_cur.execute(
                "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
                ("job_bot", "jobs.applied", job_payload)
            )
        pg_conn.commit()

        end = time.time()
        print(f"Original execution time: {end - start:.4f} seconds")

        pg_cur.close()
        pg_conn.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    run_benchmark()
