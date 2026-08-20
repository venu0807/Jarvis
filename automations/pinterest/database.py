import pandas as pd
from sqlalchemy import create_engine, text
import os

# Database connection - use DATABASE_URL from environment or fallback to container name
DATABASE_URL = os.environ.get('DATABASE_URL', 'postgresql://jarvis:***@jarvis-postgres:5432/jarvis')
ENGINE = create_engine(DATABASE_URL)

# CSV file path for fallback
CSV_FILE = os.path.join(os.path.dirname(__file__), "data.csv")

# Mapping from DB snake_case columns to CSV Title Case columns
COLUMN_MAP_TO_DF = {
    "product_name": "Product Name",
    "image_url": "Image URL",
    "lifestyle_image": "Lifestyle Image",
    "affiliate_link": "Affiliate Link",
    "status": "Status",
    "category": "Category",
    "price": "Price",
    "tags": "Tags",
    "description": "Description",
    "pin_type": "Pin Type",
    "content_lines": "Content Lines",
    "seo_title": "SEO Title",
    "pin_template": "Pin_Template",
    "board": "Board"
}

# Reverse mapping for saving back to DB
COLUMN_MAP_TO_DB = {v: k for k, v in COLUMN_MAP_TO_DF.items()}


def get_products_df(dtype=None):
    """
    Returns the products table as a pandas DataFrame, 
    matching the exact column names and structure of the old data.csv.
    Falls back to CSV file if database is unavailable.
    """
    try:
        df = pd.read_sql_query("SELECT * FROM products ORDER BY id ASC", ENGINE)
        
        # We drop the internal Postgres 'id' column before returning to the app
        # to ensure it behaves exactly like the old CSV did.
        if 'id' in df.columns:
            df = df.drop(columns=['id'])
            
        df = df.rename(columns=COLUMN_MAP_TO_DF)
        
        # If specific types are requested (like {"Status": str}), apply them
        if dtype:
            for col, t in dtype.items():
                if col in df.columns:
                    df[col] = df[col].astype(t)
                    
        return df
    except Exception as e:
        print(f"Database error: {e}")
        # Fallback to CSV file
        if os.path.exists(CSV_FILE):
            try:
                df = pd.read_csv(CSV_FILE)
                if dtype:
                    for col, t in dtype.items():
                        if col in df.columns:
                            df[col] = df[col].astype(t)
                return df
            except Exception as csv_e:
                print(f"CSV read error: {csv_e}")
        # Return empty DataFrame with expected columns
        return pd.DataFrame(columns=list(COLUMN_MAP_TO_DF.values()))


def save_products_df(df):
    """
    Takes the modified DataFrame and saves it back to the PostgreSQL database.
    Since the app historically replaces the entire CSV, we do the same here securely:
    we delete the rows and re-insert them, preserving the schema.
    Falls back to CSV file if database is unavailable.
    """
    try:
        # Map columns back to database snake_case
        db_df = df.rename(columns=COLUMN_MAP_TO_DB)
        
        with ENGINE.begin() as connection:
            # Clear the table safely
            connection.execute(text("TRUNCATE TABLE products RESTART IDENTITY"))
            # Insert the new data
            db_df.to_sql('products', connection, if_exists='append', index=False)
            
        return True
    except Exception as e:
        print(f"Database save error: {e}")
        # Fallback to CSV file
        try:
            # Map columns to CSV format
            csv_df = df.rename(columns=COLUMN_MAP_TO_DF)
            csv_df.to_csv(CSV_FILE, index=False)
            print(f"Saved to CSV fallback: {CSV_FILE}")
            return True
        except Exception as csv_e:
            print(f"CSV save error: {csv_e}")
            return False