import os
from sqlalchemy import create_engine, text

ENGINE = create_engine('postgresql://venu:venu@127.0.0.1:5432/pinterest_db')

def update_db():
    try:
        with ENGINE.begin() as conn:
            conn.execute(text("UPDATE products SET affiliate_link = REPLACE(affiliate_link, 'venu080d-21', 'venupins-20')"))
        print("Database updated successfully.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_db()
