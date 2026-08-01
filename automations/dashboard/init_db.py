import psycopg2

DB_PARAMS = {
    "dbname": "pinterest_db",
    "user": "venu",
    "password": "venu",
    "host": "127.0.0.1"
}

def init():
    conn = psycopg2.connect(**DB_PARAMS)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS automation_tasks (
            id SERIAL PRIMARY KEY,
            task_description TEXT,
            status VARCHAR(50) DEFAULT 'pending',
            proposed_code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()
    print("Table created successfully")

if __name__ == "__main__":
    init()
