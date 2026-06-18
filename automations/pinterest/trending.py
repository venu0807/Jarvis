"""
Trending Products Fetcher
=========================
Fetches trending/popular products from multiple sources:
1. Amazon Best Sellers (via scraping)
2. Reddit r/BuyItForLife, r/AmazonDeals, r/StudentDeals
3. TikTok trending hashtags
4. Google Trends

All results cached for 24 hours to avoid rate limits.
"""

import os
import json
import time
import random
import requests
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

TRENDING_CACHE_FILE = CACHE_DIR / "trending_products.json"
REDDIT_CACHE_FILE = CACHE_DIR / "reddit_products.json"
CACHE_TTL_HOURS = 24


def load_cache(cache_file: Path) -> dict:
    """Load cache from disk."""
    if cache_file.exists():
        try:
            with open(cache_file, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache_file: Path, data: dict):
    """Save cache to disk."""
    try:
        with open(cache_file, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass


def is_cache_valid(cache_data: dict) -> bool:
    """Check if cache is still valid (within TTL)."""
    if "timestamp" not in cache_data:
        return False
    age_hours = (time.time() - cache_data["timestamp"]) / 3600
    return age_hours < CACHE_TTL_HOURS


def fetch_reddit_trending(subreddit: str = "BuyItForLife", limit: int = 20) -> List[Dict]:
    """
    Fetch trending product mentions from Reddit.
    Uses Reddit's public JSON API (no auth needed for read-only).
    """
    url = f"https://www.reddit.com/r/{subreddit}/hot.json"
    params = {"limit": limit, "t": "week"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Jarvis/1.0"}

    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            posts = data.get("data", {}).get("children", [])
            products = []

            for post in posts:
                post_data = post.get("data", {})
                title = post_data.get("title", "")
                score = post_data.get("score", 0)
                url = post_data.get("url", "")
                permalink = f"https://reddit.com{post_data.get('permalink', '')}"

                # Extract potential ASINs or product names from title
                import re
                asin_matches = re.findall(r'\b(B0[A-Z0-9]{8})\b', title + " " + url)

                products.append({
                    "title": title,
                    "score": score,
                    "url": url,
                    "permalink": permalink,
                    "subreddit": subreddit,
                    "asins": asin_matches,
                    "timestamp": time.time()
                })

            return products
    except Exception as e:
        print(f"Reddit fetch error for r/{subreddit}: {e}")

    return []


def fetch_amazon_bestsellers(category_url: str = "https://www.amazon.com/gp/bestsellers") -> List[Dict]:
    """
    Scrape Amazon Best Sellers page for trending ASINs.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:
        r = requests.get(category_url, headers=headers, timeout=15)
        if r.status_code == 200:
            import re
            # Extract ASINs from bestseller page
            asin_pattern = r'/dp/(B0[A-Z0-9]{8})'
            asins = re.findall(asin_pattern, r.text)

            # Also look for data-asin attributes
            data_asin_pattern = r'data-asin=["\'](B0[A-Z0-9]{8})["\']'
            asins += re.findall(data_asin_pattern, r.text)

            # Deduplicate
            unique_asins = list(dict.fromkeys(asins))

            products = []
            for asin in unique_asins[:30]:
                products.append({
                    "asin": asin,
                    "source": "amazon_bestsellers",
                    "category_url": category_url,
                    "timestamp": time.time()
                })
            return products
    except Exception as e:
        print(f"Amazon bestsellers fetch error: {e}")

    return []


def get_cached_trending() -> List[Dict]:
    """Get trending products from cache or fetch fresh."""
    cache = load_cache(TRENDING_CACHE_FILE)
    
    if is_cache_valid(cache):
        print(f"  📦 Using cached trending products ({len(cache.get('products', []))} items)")
        return cache.get("products", [])

    print("  🔄 Fetching fresh trending products...")
    all_products = []

    # Fetch from multiple Reddit communities
    subreddits = ["BuyItForLife", "AmazonDeals", "StudentDeals", "Frugal", "Productivity"]
    for sub in subreddits:
        products = fetch_reddit_trending(sub, limit=15)
        all_products.extend(products)
        time.sleep(1)  # Be nice to Reddit

    # Fetch Amazon bestsellers
    asin_products = fetch_amazon_bestsellers()
    all_products.extend(asin_products)

    # Cache results
    cache_data = {
        "timestamp": time.time(),
        "products": all_products
    }
    save_cache(TRENDING_CACHE_FILE, cache_data)

    print(f"  ✅ Fetched {len(all_products)} trending product signals")
    return all_products


def get_trending_asins(category: str = None, limit: int = 10) -> List[str]:
    """
    Get trending ASINs, optionally filtered by category relevance.
    Returns list of ASIN strings.
    """
    trending = get_cached_trending()
    asins = []

    for item in trending:
        if "asin" in item:
            asins.append(item["asin"])
        elif "asins" in item:
            asins.extend(item["asins"])

    # Deduplicate while preserving order
    seen = set()
    unique_asins = []
    for asin in asins:
        if asin not in seen:
            seen.add(asin)
            unique_asins.append(asin)

    return unique_asins[:limit]


def enrich_with_trending(products: List[Dict], trending_asins: List[str]) -> List[Dict]:
    """
    Add trending score/metadata to existing products.
    Boosts products that appear in trending sources.
    """
    trending_set = set(trending_asins)
    
    for p in products:
        p["is_trending"] = p.get("asin", "") in trending_set
        p["trending_score"] = 10 if p["is_trending"] else 0
    
    # Sort: trending first, then by existing priority
    return sorted(products, key=lambda x: (-x.get("trending_score", 0), x.get("name", "")))


if __name__ == "__main__":
    # Test
    print("Testing trending products fetcher...")
    trending = get_cached_trending()
    asins = get_trending_asins()
    print(f"Trending ASINs: {asins[:10]}")