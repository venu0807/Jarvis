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
    Try to fetch a working Amazon product image URL for an ASIN using Playwright.
    """
    try:
        # Import SyncBrowser dynamically to avoid circular imports if any
        from jarvis_browser import SyncBrowser
        with SyncBrowser(headless=True) as browser:
            context = browser.new_context()
            page = context.new_page()
            
            product_url = f"https://www.amazon.com/dp/{asin}"
            print(f"  🌐 Navigating to {product_url}...")
            
            # Using domcontentloaded is faster, we just need the HTML to parse the image src
            page.goto(product_url, timeout=30000, wait_until="domcontentloaded")
            
            try:
                page.wait_for_selector("#landingImage, #imgBlkFront, .a-dynamic-image", timeout=5000)
            except Exception:
                pass  # Try evaluating anyway

            js_extract = """
            () => {
                let img = document.querySelector("#landingImage, #imgBlkFront, #main-image, img.a-dynamic-image");
                if (!img) return null;
                
                // 1. Try to parse data-a-dynamic-image (JSON of hi-res variants)
                let dyn = img.getAttribute("data-a-dynamic-image");
                if (dyn) {
                    try {
                        let parsed = JSON.parse(dyn);
                        let maxW = 0;
                        let bestUrl = null;
                        for (let url in parsed) {
                            if (parsed[url][0] > maxW) {
                                maxW = parsed[url][0];
                                bestUrl = url;
                            }
                        }
                        if (bestUrl) return bestUrl;
                    } catch(e) {}
                }
                
                // 2. Try highRes attribute
                let hiRes = img.getAttribute("data-old-hires");
                if (hiRes) return hiRes;
                
                // 3. Fallback to src
                return img.getAttribute("src");
            }
            """
            
            best_url = page.evaluate(js_extract)
            context.close()
            
            if best_url and best_url.startswith("http"):
                return best_url
            return None
            
    except Exception as e:
        print(f"  ⚠️  Playwright scraping error for {asin}: {e}")
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