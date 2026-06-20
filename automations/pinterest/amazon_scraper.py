import os
import time
import re
import pandas as pd
from jarvis_browser import SyncBrowser
from bs4 import BeautifulSoup

CSV_FILE = "data.csv"
USER_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Venu\\AppData\\Local"), "AmazonBot")
AFFILIATE_TAG = "venu080d-21"

from get_pinterest_trends import get_trending_keywords

def get_dynamic_niches():
    trends = get_trending_keywords()
    niches = []
    
    # 1. Add core static user niches mapped to existing boards to build consistency
    core_queries = [
        {"query": "college dorm essentials", "board": "Student Essentials", "tags": "#collegelife #dormdecor"},
        {"query": "student tech gadgets", "board": "Student Essentials", "tags": "#studenttech #studygram"},
        {"query": "aesthetic room decor", "board": "Aesthetic Room Decor", "tags": "#roomdecor #aesthetic"},
        {"query": "korean skincare viral", "board": "Beauty & Vanity", "tags": "#skincare #kbeauty"},
        {"query": "viral kitchen gadgets", "board": "Kitchen Gadgets", "tags": "#kitchenfinds #amazonkitchen"}
    ]
    for cq in core_queries:
        niches.append({
            "query": cq["query"],
            "board": cq["board"],
            "category": cq["board"].lower(),
            "tags": cq["tags"]
        })
        
    # 2. Add live Pinterest trends mapped to the 'Trending' boards
    import random
    for t in trends:
        # Alternate randomly between the two trending boards to build consistency
        trending_board = random.choice(["Trending Finds", "Trending Now"])
        niches.append({
            "query": t,
            "board": trending_board,
            "category": "trending",
            "tags": "#trending #amazonfinds #" + t.replace(' ', '')
        })
    return niches

def extract_asin(url):
    match = re.search(r'/dp/([A-Z0-9]{10})', url)
    return match.group(1) if match else None

def scrape_amazon(custom_niches=None):
    print("🚀 Starting Amazon Affiliate Scraper...")
    
    active_niches = custom_niches if custom_niches is not None else get_dynamic_niches()
    
    existing_asins = set()
    if os.path.exists(CSV_FILE):
        try:
            df_existing = pd.read_csv(CSV_FILE)
            if 'Affiliate Link' in df_existing.columns:
                for link in df_existing['Affiliate Link'].dropna():
                    asin = extract_asin(str(link))
                    if asin:
                        existing_asins.add(asin)
        except Exception:
            pass
    
    new_products = []
    
    with SyncBrowser(headless=True) as browser:
        context = browser.launch_persistent(USER_DATA_DIR)
        page = context.pages[0] if context.pages else context.new_page()
        
        for niche in active_niches:
            print(f"\n🔍 Searching for: {niche['query']}")
            try:
                page.goto(f"https://www.amazon.com/s?k={niche['query'].replace(' ', '+')}", wait_until="domcontentloaded", timeout=30000)
                time.sleep(3) # Wait for anti-bot
                
                # Get all product links
                links = page.locator("a.a-link-normal.s-no-outline").all()
                if not links:
                    print("  ⚠️  No products found (Possible CAPTCHA). Skipping niche.")
                    continue
                    
                # Click the first non-sponsored product
                product_url = None
                import random
                valid_links = []
                for link in links:
                    href = link.get_attribute("href")
                    if href and "/dp/" in href and "slredirect" not in href:
                        raw_url = "https://www.amazon.com" + href.split('?')[0]
                        asin = extract_asin(raw_url)
                        if asin and asin not in existing_asins:
                            valid_links.append(raw_url)
                if valid_links:
                    product_url = random.choice(valid_links)
                
                if not product_url:
                    print("  ⚠️  Could not find a valid new organic product link.")
                    continue
                    
                print(f"  📦 Found Product URL: {product_url}")
                
                page.goto(product_url, wait_until="domcontentloaded", timeout=30000)
                time.sleep(3)
                
                html = page.content()
                soup = BeautifulSoup(html, 'html.parser')
                
                # Extract Data
                asin = extract_asin(product_url)
                
                title_el = soup.find(id="productTitle")
                title = title_el.text.strip() if title_el else ""
                
                # Try to get highest resolution image
                img_el = soup.find(id="landingImage")
                img_url = ""
                if img_el:
                    img_url = img_el.get("data-old-hires") or img_el.get("src")
                
                # Price
                price_el = soup.select_one(".a-price .a-offscreen")
                price = price_el.text.strip() if price_el else ""
                
                if not title or not img_url or not asin:
                    print(f"  ⚠️  Failed to extract core details for {product_url}")
                    continue
                    
                aff_link = f"https://www.amazon.com/dp/{asin}?tag={AFFILIATE_TAG}"
                
                print(f"  ✅ Title: {title[:50]}...")
                print(f"  ✅ Image: {img_url}")
                print(f"  ✅ Affiliate Link: {aff_link}")
                
                new_products.append({
                    "Product Name": title,
                    "Image URL": img_url,
                    "Affiliate Link": aff_link,
                    "Status": "",
                    "Category": niche["category"],
                    "Price": price,
                    "Tags": niche["tags"],
                    "Description": f"I just found the ultimate {niche['query']}! Grab it before it goes viral. {niche['tags']}",
                    "Pin Type": "product",
                    "Content Lines": "",
                    "SEO Title": title[:80],
                    "Pin_Template": "",
                    "Board": niche["board"]
                })
                
            except Exception as e:
                print(f"  ⚠️  Error processing {niche['query']}: {e}")

    if new_products:
        print(f"\n💾 Saving {len(new_products)} scraped products to {CSV_FILE}...")
        if not os.path.exists(CSV_FILE):
            df = pd.DataFrame(new_products)
        else:
            df = pd.read_csv(CSV_FILE)
            if 'Board' not in df.columns:
                df['Board'] = ''
            new_df = pd.DataFrame(new_products)
            df = pd.concat([df, new_df], ignore_index=True)
            
        df.to_csv(CSV_FILE, index=False)
        print("  ✅ Saved successfully!")
    else:
        print("\n  ⚠️ No products were successfully scraped.")

if __name__ == "__main__":
    scrape_amazon()
