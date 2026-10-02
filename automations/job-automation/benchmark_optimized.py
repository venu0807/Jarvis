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

        data = [("job_bot", "jobs.applied", json.dumps(r.job)) for r in applied_results]
        try:
            psycopg2.extras.execute_values(
                pg_cur,
                "INSERT INTO events (source, event_type, payload) VALUES %s",
                data
            )
        except Exception as e:
            # Fallback to single inserts if bulk fails
            print(f"Bulk insert failed, falling back: {e}")
            pg_conn.rollback()
            for row in data:
                try:
                    pg_cur.execute(
                        "INSERT INTO events (source, event_type, payload) VALUES (%s, %s, %s)",
                        row
                    )
                except Exception as inner_e:
                    print(f"Failed to insert row: {inner_e}")
                    pg_conn.rollback()

        pg_conn.commit()

        end = time.time()
        print(f"Optimized execution time: {end - start:.4f} seconds")

        pg_cur.close()
        pg_conn.close()
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    run_benchmark()
