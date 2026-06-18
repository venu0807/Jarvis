"""
Robust Amazon Product Image Fetcher
====================================
Fetches and caches working product images for ASINs.
Supports multiple fallback strategies.
"""

import os
import json
import time
import requests
from pathlib import Path
from typing import Optional
from urllib.parse import quote

CACHE_FILE = Path(__file__).parent / "image_cache.json"
CACHE_TTL_DAYS = 30

# High-resolution placeholder images by category (Unsplash - free, premium quality)
PLACEHOLDER_IMAGES = {
    "tech": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&h=1800&fit=crop&auto=format&q=90",
    "dorm_decor": "https://images.unsplash.com/photo-1618220179428-22790b461013?w=1200&h=1800&fit=crop&auto=format&q=90",
    "study_supplies": "https://images.unsplash.com/photo-1497633762265-9d179a990aa6?w=1200&h=1800&fit=crop&auto=format&q=90",
    "self_care": "https://images.unsplash.com/photo-1544367567-0f2fcb009e0b?w=1200&h=1800&fit=crop&auto=format&q=90",
    "kitchen": "https://images.unsplash.com/photo-1556909114-f6e7ad7d3136?w=1200&h=1800&fit=crop&auto=format&q=90",
    "fashion": "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=1200&h=1800&fit=crop&auto=format&q=90",
}

# Generic fallback - higher resolution
GENERIC_PLACEHOLDER = "https://images.unsplash.com/photo-1560472354-b33ff0c44a43?w=1200&h=1800&fit=crop&auto=format&q=90"


def load_cache() -> dict:
    """Load image cache from disk."""
    if CACHE_FILE.exists():
        try:
            with open(CACHE_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def save_cache(cache: dict):
    """Save image cache to disk."""
    try:
        with open(CACHE_FILE, "w") as f:
            json.dump(cache, f, indent=2)
    except Exception:
        pass


def is_cache_valid(cache_entry: dict) -> bool:
    """Check if cache entry is still valid (not expired)."""
    if "timestamp" not in cache_entry:
        return False
    age_days = (time.time() - cache_entry["timestamp"]) / 86400
    return age_days < CACHE_TTL_DAYS


def fetch_amazon_image(asin: str) -> Optional[str]:
    """
    Try to fetch a working Amazon product image URL for an ASIN.
    Uses multiple strategies.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }

    # Strategy 1: Try Amazon's product image endpoint patterns directly with ASIN
    patterns = [
        f"https://m.media-amazon.com/images/I/{asin}._AC_SL1500_.jpg",
        f"https://m.media-amazon.com/images/I/{asin}._AC_SX679_.jpg",
        f"https://m.media-amazon.com/images/I/{asin}._AC_UL1500_.jpg",
        f"https://m.media-amazon.com/images/I/{asin}._AC_.jpg",
        f"https://images-na.ssl-images-amazon.com/images/I/{asin}._AC_SL1500_.jpg",
    ]

    for url in patterns:
        try:
            r = requests.head(url, headers=headers, timeout=5, allow_redirects=True)
            if r.status_code == 200:
                return url
        except Exception:
            continue

    # Strategy 2: Try to scrape the product page for image URLs
    try:
        product_url = f"https://www.amazon.com/dp/{asin}"
        r = requests.get(product_url, headers=headers, timeout=10)
        if r.status_code == 200:
            # Look for image URLs in the HTML
            import re
            # Try multiple patterns
            img_patterns = [
                r'"hiRes"\s*:\s*"([^"]+)"',
                r'"large"\s*:\s*"([^"]+)"',
                r'data-a-dynamic-image\s*=\s*"([^"]+)"',
                r'imageUrl"\s*:\s*"([^"]+)"',
                r'https://m\.media-amazon\.com/images/I/[^"\s]+\.jpg',
            ]
            for pattern in img_patterns:
                matches = re.findall(pattern, r.text)
                for match in matches:
                    # Clean up escaped characters
                    clean_url = match.replace("\\u002F", "/").replace("\\/", "/")
                    if clean_url.startswith("http") and ("jpg" in clean_url or "png" in clean_url):
                        # Verify the URL works
                        try:
                            vr = requests.head(clean_url, headers=headers, timeout=5, allow_redirects=True)
                            if vr.status_code == 200:
                                return clean_url
                        except Exception:
                            continue
    except Exception:
        pass

    # Strategy 3: Try Amazon's image CDN with common prefixes + ASIN suffix
    # Many products use image IDs starting with specific prefixes
    common_prefixes = ["71", "61", "81", "91", "51", "41", "31", "21", "11"]
    for prefix in common_prefixes:
        test_url = f"https://m.media-amazon.com/images/I/{prefix}{asin[-8:]}._AC_SL1500_.jpg"
        try:
            r = requests.head(test_url, headers=headers, timeout=3, allow_redirects=True)
            if r.status_code == 200:
                return test_url
        except Exception:
            continue

    return None


def get_product_image(asin: str, category: str = "tech") -> str:
    """
    Get a working product image URL for an ASIN.
    Uses cache, then fetches from Amazon, then falls back to placeholders.
    """
    cache = load_cache()

    # Check cache first
    if asin in cache and is_cache_valid(cache[asin]):
        return cache[asin]["url"]

    # Try to fetch from Amazon
    print(f"  🔍 Fetching image for {asin}...")
    image_url = fetch_amazon_image(asin)

    if image_url:
        cache[asin] = {"url": image_url, "timestamp": time.time()}
        save_cache(cache)
        print(f"  ✅ Found working Amazon image for {asin}")
        return image_url

    # Fallback to category-appropriate placeholder
    print(f"  ⚠️  No Amazon image found for {asin}, using placeholder")
    placeholder = PLACEHOLDER_IMAGES.get(category, GENERIC_PLACEHOLDER)

    cache[asin] = {"url": placeholder, "timestamp": time.time()}
    save_cache(cache)
    return placeholder


def get_content_pin_image(category: str = "tech") -> str:
    """Get a relevant placeholder image for content pins."""
    return PLACEHOLDER_IMAGES.get(category, GENERIC_PLACEHOLDER)


def preload_images(asin_list: list, category_map: dict = None):
    """Preload images for a list of ASINs (useful for batch operations)."""
    for asin in asin_list:
        cat = category_map.get(asin, "tech") if category_map else "tech"
        get_product_image(asin, cat)
        time.sleep(0.5)  # Be nice to servers


if __name__ == "__main__":
    # Test
    test_asins = ["B0863FR3S9", "B0BDHWDR12", "B09VPHVT2V"]
    for asin in test_asins:
        url = get_product_image(asin, "tech")
        print(f"{asin}: {url}")