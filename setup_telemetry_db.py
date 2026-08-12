import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

def setup_db():
    print("Connecting to default postgres database to create 'jarvis'...")
    try:
        # Connect to default postgres DB
        conn = psycopg2.connect(dbname="postgres", user="postgres", host="127.0.0.1")
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if jarvis DB exists
        cursor.execute("SELECT 1 FROM pg_catalog.pg_database WHERE datname = 'jarvis'")
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute("CREATE DATABASE jarvis")
            print("Created 'jarvis' database.")
        else:
            print("'jarvis' database already exists.")
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error checking/creating database: {e}")

    print("Connecting to 'jarvis' database to create tables...")
    try:
        conn = psycopg2.connect(dbname="jarvis", user="postgres", host="127.0.0.1")
        cursor = conn.cursor()
        
        # Create the telemetry table
        create_table_query = """
        CREATE TABLE IF NOT EXISTS automation_telemetry (
            id SERIAL PRIMARY KEY,
            job_id VARCHAR(50) NOT NULL,
            status VARCHAR(20) NOT NULL,
            duration_seconds INT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        cursor.execute(create_table_query)
        conn.commit()
        print("Table 'automation_telemetry' created successfully.")
        
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error creating table: {e}")

if __name__ == "__main__":
    setup_db()
