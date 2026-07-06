import pandas as pd
from sqlalchemy import create_engine, text

# Database connection
ENGINE = create_engine('postgresql://venu:venu@127.0.0.1:5432/pinterest_db')

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
        return pd.DataFrame()


def save_products_df(df):
    """
    Takes the modified DataFrame and saves it back to the PostgreSQL database.
    Since the app historically replaces the entire CSV, we do the same here securely:
    we delete the rows and re-insert them, preserving the schema.
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
        return False
