import csv
import os

import psycopg2
from psycopg2 import extras


def migrate():
    # Connect to PostgreSQL
    conn = psycopg2.connect(
        dbname="pinterest_db",
        user=os.environ.get("PINTEREST_DB_USER", "venu"),
        password=os.environ.get("PINTEREST_DB_PASSWORD"),
        host="127.0.0.1"
    )
    cur = conn.cursor()

    # Create table matching CSV columns
    cur.execute("""
    CREATE TABLE IF NOT EXISTS products (
        id SERIAL PRIMARY KEY,
        product_name TEXT,
        image_url TEXT,
        affiliate_link TEXT,
        status TEXT,
        category TEXT,
        price TEXT,
        tags TEXT,
        description TEXT,
        pin_type TEXT,
        content_lines TEXT,
        seo_title TEXT,
        pin_template TEXT,
        board TEXT
    );
    """)

    # Read CSV and insert data
    with open('data.csv', 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader) # Skip header row
        
        insert_query = """
        INSERT INTO products (
            product_name, image_url, affiliate_link, status, category, price,
            tags, description, pin_type, content_lines, seo_title, pin_template, board
        ) VALUES %s
        """

        insert_query_fallback = """
        INSERT INTO products (
            product_name, image_url, affiliate_link, status, category, price,
            tags, description, pin_type, content_lines, seo_title, pin_template, board
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        count = 0
        rows_to_insert = []
        for row in reader:
            if not row or not any(row):
                continue
            
            # Ensure row has exactly 13 elements, padding if necessary
            row = row + [''] * (13 - len(row))
            row = row[:13]
            rows_to_insert.append(tuple(row))
            
        try:
            extras.execute_values(cur, insert_query, rows_to_insert)
            count = len(rows_to_insert)
        except Exception as e:
            print(f"Bulk insert failed: {e}. Falling back to row-by-row insert.")
            conn.rollback()
            for row in rows_to_insert:
                try:
                    cur.execute(insert_query_fallback, row)
                    count += 1
                except Exception as row_e:
                    print(f"Failed to insert row: {row}. Error: {row_e}")
            
    conn.commit()
    cur.close()
    conn.close()
    print(f"Migration completed successfully. Inserted {count} products into PostgreSQL.")

if __name__ == "__main__":
    migrate()
