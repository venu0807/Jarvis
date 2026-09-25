"""
Jarvis Shared Database Schema (db_schema.py)
--------------------------------------------
Initializes and upgrades the PostgreSQL database for the central orchestrator.
Adds shared tables for events, jobs, contacts, revenue, and health logs.
"""

import os
from sqlalchemy import create_engine, text

# Use the same credentials as pinterest bot
DB_URL = os.getenv("DATABASE_URL", "postgresql://venu:venu@127.0.0.1:5432/pinterest_db")

TABLE_SCHEMAS = {
    "events": """
        CREATE TABLE IF NOT EXISTS events (
            id SERIAL PRIMARY KEY,
            source VARCHAR(255) NOT NULL,
            event_type VARCHAR(255) NOT NULL,
            payload JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "jobs": """
        CREATE TABLE IF NOT EXISTS jobs (
            id SERIAL PRIMARY KEY,
            portal VARCHAR(255) NOT NULL,
            company VARCHAR(255) NOT NULL,
            title VARCHAR(255) NOT NULL,
            status VARCHAR(50) DEFAULT 'APPLIED',
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "contacts": """
        CREATE TABLE IF NOT EXISTS contacts (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            company VARCHAR(255),
            linkedin_url VARCHAR(255),
            email VARCHAR(255),
            dm_sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """,
    "revenue": """
        CREATE TABLE IF NOT EXISTS revenue (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL UNIQUE,
            estimated_clicks INTEGER DEFAULT 0,
            estimated_earnings NUMERIC(10, 2) DEFAULT 0.00
        )
    """,
    "health_log": """
        CREATE TABLE IF NOT EXISTS health_log (
            id SERIAL PRIMARY KEY,
            bot_name VARCHAR(100) NOT NULL,
            status VARCHAR(50) NOT NULL,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            error_msg TEXT
        )
    """
}

def _create_table(conn, table_name: str, schema_sql: str) -> None:
    """Helper function to create a table and print a success message."""
    conn.execute(text(schema_sql))
    print(f"  ✅ Table '{table_name}' ready.")

def init_db():
    engine = create_engine(DB_URL)
    with engine.connect() as conn:
        print("🔧 Initializing shared brain tables...")
        
        for table_name, schema_sql in TABLE_SCHEMAS.items():
            _create_table(conn, table_name, schema_sql)
        
        conn.commit()
    print("🎉 Database initialization complete!")

if __name__ == "__main__":
    init_db()
