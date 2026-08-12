import os
import time
import re
from pathlib import Path
import pandas as pd
from database import get_products_df, save_products_df
from jarvis_browser import SyncBrowser
from bs4 import BeautifulSoup

CSV_FILE = "data.csv"
# LOCALAPPDATA set on real Windows; under WSL fall back to a real Linux path
# (the old "C:\Users\..." fallback materialized a literal backslash dir inside
# the repo).
USER_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", str(Path.home() / ".cache")), "AmazonBot")
AFFILIATE_TAG = "venu080d-21"

from get_pinterest_trends import get_trending_keywords

def get_dynamic_niches():
    trends = get_trending_keywords()
    niches = []
    
    # 1. Add core static user niches mapped to specific boards
    core_niches = [
        {"query": "baby nursery must haves", "board": "Baby & Nursery", "category": "baby", "tags": "#nurserydecor #babymusthaves #momlife"},
        {"query": "home organization storage", "board": "Home Organization", "category": "home", "tags": "#homeorganization #storagehacks #cleantok"},
        {"query": "travel essentials hacks", "board": "Travel Finds", "category": "travel", "tags": "#travelhacks #travelessentials #vacation"},
        {"query": "work from home desk setup", "board": "Desk & Tech Setup", "category": "tech", "tags": "#wfhsetup #desksetup #techgadgets"}
    ]
    for niche in core_niches:
        niches.append(niche)
        
    # 2. Add live Pinterest trends
    import random
    for t in trends:
        niches.append({
            "query": t,
            "board": random.choice(["Trending Finds", "Trending Now"]),
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
    if True:
        try:
            df_existing = get_products_df()
            if 'Affiliate Link' in df_existing.columns:
                for link in df_existing['Affiliate Link'].dropna():
                    asin = extract_asin(str(link))
                    if asin:
                        existing_asins.add(asin)
        except Exception:
            pass
    
    new_products = []
    
    with SyncBrowser(headless=False) as browser:
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
                        raw_url = href.split('?')[0]
                        if not raw_url.startswith('http'):
                            raw_url = "https://www.amazon.com" + raw_url
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
                    
                # Extract Lifestyle Image (usually 2nd or 3rd image in gallery)
                lifestyle_url = img_url
                alt_images = soup.select("#altImages img")
                if alt_images and len(alt_images) > 1:
                    # Skip the first one as it's the main white-background image
                    for alt_img in alt_images[1:]:
                        src = alt_img.get("src", "")
                        if src and "._" in src:
                            # Convert Amazon thumbnail URL to hi-res URL
                            hi_res = re.sub(r'\._[a-zA-Z0-9_,-]+_\.', '.', src)
                            if hi_res:
                                lifestyle_url = hi_res
                                break
                
                # Price
                price_el = soup.select_one(".a-price .a-offscreen")
                price = price_el.text.strip() if price_el else ""
                
                if not title or not img_url or not asin:
                    print(f"  ⚠️  Failed to extract core details for {product_url}")
                    continue
                    
                aff_link = f"https://www.amazon.com/dp/{asin}?tag={AFFILIATE_TAG}"
                
                print(f"  ✅ Title: {title[:50]}...")
                print(f"  ✅ Image: {img_url}")
                print(f"  ✅ Lifestyle Image: {lifestyle_url}")
                print(f"  ✅ Affiliate Link: {aff_link}")
                
                new_products.append({
                    "Product Name": title,
                    "Image URL": img_url,
                    "Lifestyle Image": lifestyle_url,
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
        if not True:
            df = pd.DataFrame(new_products)
        else:
            df = get_products_df()
            if 'Board' not in df.columns:
                df['Board'] = ''
            new_df = pd.DataFrame(new_products)
            df = pd.concat([df, new_df], ignore_index=True)
            
        save_products_df(df)
        print("  ✅ Saved successfully!")
    else:
        print("\n  ⚠️ No products were successfully scraped.")

if __name__ == "__main__":
    scrape_amazon()
