"""
Trending Products Fetcher
=========================
Fetches trending products from Amazon Best Sellers and other sources.
Replaces static products with live, currently-trending data.
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Optional
import re

CACHE_FILE = Path(__file__).parent / "trending_cache.json"
CACHE_TTL_HOURS = 6


def load_cache() -> dict:
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache: dict):
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def fetch_amazon_bestsellers(category_url: str, max_items: int = 10) -> list:
    """Scrape Amazon Best Sellers page for a category."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    products = []
    try:
        resp = requests.get(category_url, headers=headers, timeout=15)
        if resp.status_code != 200:
            return products

        html = resp.text
        # Find product ASINs (dp/XXXX pattern)
        asin_matches = re.findall(r'/dp/([A-Z0-9]{10})', html)
        # Find product titles
        title_matches = re.findall(r'class="a-link-normal"[^>]*>\s*<span[^>]*>([^<]+)</span>', html)

        seen = set()
        for i, asin in enumerate(asin_matches[:max_items]):
            if asin in seen:
                continue
            seen.add(asin)
            title = title_matches[i] if i < len(title_matches) else f"Trending Product {asin}"
            products.append({
                "asin": asin,
                "name": title.strip()[:100],
                "image_id": "",
                "price": "",
                "source": "amazon_bestsellers",
            })
    except Exception as e:
        print(f"  ⚠️  Amazon bestsellers fetch error: {e}")
    return products


def fetch_trending_students() -> list:
    """Fetch trending student products from Amazon Best Sellers (student niche)."""
    categories = [
        ("tech", "https://www.amazon.com/Best-Sellers-Electronics/zgbs/electronics/"),
        ("dorm_decor", "https://www.amazon.com/Best-Sellers-Home-Kitchen/zgbs/home-garden/"),
        ("study_supplies", "https://www.amazon.com/Best-Sellers-Office-Products/zgbs/office-products/"),
    ]

    all_products = []
    for cat_name, url in categories:
        print(f"  🔍 Fetching trending {cat_name}...")
        items = fetch_amazon_bestsellers(url, max_items=5)
        for item in items:
            item["category"] = cat_name
        all_products.extend(items)
        time.sleep(1)

    cache = load_cache()
    cache["trending"] = {"products": all_products, "timestamp": time.time()}
    save_cache(cache)
    return all_products


def get_trending_products(force_refresh: bool = False) -> list:
    """Get trending products from cache or fetch fresh."""
    if not force_refresh:
        cache = load_cache()
        if "trending" in cache:
            age_hours = (time.time() - cache["trending"]["timestamp"]) / 3600
            if age_hours < CACHE_TTL_HOURS:
                return cache["trending"]["products"]

    return fetch_trending_students()


if __name__ == "__main__":
    products = get_trending_products(force_refresh=True)
    print(f"\n  📊 Found {len(products)} trending products:")
    for p in products[:10]:
        print(f"     • {p['name'][:60]} ({p['asin']})")
