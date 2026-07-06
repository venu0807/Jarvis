#!/usr/bin/env python3
"""
Fix image URLs in data.csv for the 9 affiliate store products.
Replace placeholder images with real Unsplash images from the affiliate store.
"""
import pandas as pd
from database import get_products_df, save_products_df

CSV_FILE = "/home/venu/Proposals/Jarvis/automations/pinterest/data.csv"

# Map product names to their real Unsplash image URLs
REAL_IMAGES = {
    "Aesthetic Linen Throw Pillow Set": "https://images.unsplash.com/photo-1586023492125-27b2c045efd7?q=80&w=1200&auto=format&fit=crop",
    "Minimalist Boho Wall Art Print": "https://images.unsplash.com/photo-1513519245088-0e12902e5a38?q=80&w=1200&auto=format&fit=crop",
    "Rattan Wicker Storage Basket Set": "https://images.unsplash.com/photo-1595428774223-ef52624120d2?q=80&w=1200&auto=format&fit=crop",
    "Viral Tallow Whipped Face Cream": "https://images.unsplash.com/photo-1556228578-8c89e6adf883?q=80&w=1200&auto=format&fit=crop",
    "Gua Sha Facial Sculpting Tool": "https://images.unsplash.com/photo-1620916566398-39f1143ab7be?q=80&w=1200&auto=format&fit=crop",
    "Aesthetic Glass Water Bottle": "https://images.unsplash.com/photo-1602143407151-7111542de6e8?q=80&w=1200&auto=format&fit=crop",
    "Smart LED Desk Lamp with USB Charging": "https://images.unsplash.com/photo-1534073828943-f801091bb18c?q=80&w=1200&auto=format&fit=crop",
    "Matcha Bamboo Whisk & Ceremony Set": "https://images.unsplash.com/photo-1536256263959-770b48d82b0a?q=80&w=1200&auto=format&fit=crop",
    "Portable Bluetooth Mini Projector": "https://images.unsplash.com/photo-1626379953822-baec19c3accd?q=80&w=1200&auto=format&fit=crop",
}

df = get_products_df()
updated = 0

for product_name, image_url in REAL_IMAGES.items():
    mask = df["Product Name"].str.strip() == product_name
    if mask.any():
        df.loc[mask, "Image URL"] = image_url
        updated += mask.sum()
        print(f"  ✅ Updated image for: {product_name} ({mask.sum()} rows)")
    else:
        print(f"  ⚠️  Not found: {product_name}")

save_products_df(df)
print(f"\n✅ Done! Updated {updated} rows in data.csv")
