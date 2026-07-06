import os
import re
from datetime import datetime
from database import get_products_df

BLOG_DIR = os.path.join(os.path.dirname(__file__), "blog", "content", "posts")

def sanitize_filename(name):
    # Convert to lowercase and replace non-alphanumeric with hyphens
    s = str(name).strip().lower()
    return re.sub(r'[^a-z0-9]+', '-', s).strip('-')

def generate_markdown(row):
    title = row.get("SEO Title") or row.get("Product Name") or "Amazing Product"
    filename = sanitize_filename(title) + ".md"
    filepath = os.path.join(BLOG_DIR, filename)
    
    # Avoid regenerating if it already exists (unless we want to update it)
    if os.path.exists(filepath):
        return False
        
    date_str = datetime.now().strftime("%Y-%m-%d")
    category = str(row.get("Category", "home")).replace('_', ' ').title()
    tags = str(row.get("Tags", "")).replace('#', '').split()
    tags_formatted = "\n  - ".join([t for t in tags if t])
    if not tags_formatted:
        tags_formatted = "general"
        
    affiliate_link = row.get("Affiliate Link", "#")
    image_url = row.get("Image URL", "")
    description = row.get("Description", "Discover this amazing find that is going viral on Pinterest right now!")
    price = row.get("Price", "Check latest price")

    md_content = f"""---
title: "{title}"
date: {date_str}
category: "{category}"
tags:
  - {tags_formatted}
---

# {title}

![{title}]({image_url})

Looking for the perfect aesthetic addition to your {category.lower()} setup? We found exactly what you've been searching for.

## Why We Love It
{description}

This product is currently trending all over Pinterest, and for good reason! It perfectly captures the cozy, minimalist aesthetic that everyone is trying to recreate.

### Features
* Beautiful {category.lower()} design
* Highly rated on Amazon
* Perfect for your aesthetic pinterest boards

**Current Price:** {price}

[👉 Click here to check the current price and availability on Amazon]({affiliate_link})

---
*Disclaimer: As an Amazon Associate we earn from qualifying purchases. This helps support our blog at no extra cost to you!*
"""

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    return True

def export_to_blog():
    print("🌐 Starting Auto-Blogger generation...")
    os.makedirs(BLOG_DIR, exist_ok=True)
    
    df = get_products_df().fillna("")
    if df.empty:
        print("  ❌ Database is empty.")
        return
        
    count = 0
    for _, row in df.iterrows():
        # Only generate blogs for actual products (skip content pins)
        if str(row.get("Pin Type")).lower() == "content":
            continue
            
        # Optional: Only generate for Pinned products
        status = str(row.get("Status", "")).strip().lower()
        if status != "pinned":
            continue
            
        if generate_markdown(row):
            count += 1
            
    print(f"  ✅ Successfully generated {count} new SEO blog posts.")
    print(f"  📂 Files saved to: {os.path.abspath(BLOG_DIR)}")
    print("  💡 You can now push this directory to GitHub Pages or Netlify!")

if __name__ == "__main__":
    export_to_blog()
