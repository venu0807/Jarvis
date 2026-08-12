import sys
import psycopg2

def log_telemetry(job_id, status, duration):
    try:
        # We use host=127.0.0.1 to avoid socket path issues in WSL
        conn = psycopg2.connect(dbname="jarvis", user="postgres", host="127.0.0.1")
        cursor = conn.cursor()
        
        insert_query = """
        INSERT INTO automation_telemetry (job_id, status, duration_seconds)
        VALUES (%s, %s, %s);
        """
        cursor.execute(insert_query, (job_id, status, int(duration)))
        conn.commit()
        
        cursor.close()
        conn.close()
        print(f"Logged {status} for {job_id} ({duration}s) to PostgreSQL.")
    except Exception as e:
        print(f"Failed to log telemetry to PostgreSQL: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python3 telemetry.py <job_id> <status> <duration_seconds>")
        sys.exit(1)
        
    job_id = sys.argv[1]
    status = sys.argv[2]
    duration = sys.argv[3]
    
    log_telemetry(job_id, status, duration)
