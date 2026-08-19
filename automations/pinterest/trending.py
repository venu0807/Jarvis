"""
Trending products module for Pinterest automation
Handles fetching and enriching products with trending data
"""

import random
import time

# Mock trending ASINs - in practice this would come from Amazon API or scraping
MOCK_TRENDING_ASINS = [
    "B08XYZ1234",  # Trending tech gadget
    "B08ABC5678",  # Trending beauty product
    "B08DEF9012",  # Trending dorm item
    "B08GHI3456",  # Trending kitchen gadget
    "B08JKL7890"   # Trending fashion accessory
]

def get_trending_asins(limit=20):
    """Get list of trending ASINs"""
    # Return mock trending ASINs, limited to requested amount
    return MOCK_TRENDING_ASINS[:limit]

def enrich_with_trending(products, trending_asins):
    """Enrich products with trending flag"""
    enriched = []
    trending_set = set(trending_asins)
    
    for product in products:
        # Create a copy so we don't modify the original
        enriched_product = product.copy()
        
        # Check if this product's ASIN is in trending list
        # Note: In real implementation, products would have 'asin' field
        # For now, we'll mock it by marking some products as trending
        if len(enriched) < len(trending_asins):
            enriched_product["is_trending"] = True
        else:
            enriched_product["is_trending"] = False
            
        enriched.append(enriched_product)
        
    return enriched

# Additional trending helper functions that might be needed
def get_trending_products(force_refresh=False):
    """Fetch live trending products (mock implementation)"""
    # In a real implementation, this would scrape Amazon Best Sellers
    # or use their API to get current trending products
    
    # For now, return some sample products with trending flag
    trending_products = []
    
    # Mark first few products as trending
    for i, product in enumerate(PRODUCTS[:3] if 'PRODUCTS' in globals() else []):
        product_copy = product.copy()
        product_copy["is_trending"] = True
        trending_products.append(product_copy)
        
    # Add some mock trending-specific products
    mock_trending = [
        {
            "name": "Viral TikTok Gadget",
            "asin": "B08TRENDING1",
            "image_id": "default",
            "category": "tech",
            "price": "25.99",
            "tags": "#tiktoktrend #viral gadget #musthave",
            "description": "The gadget everyone's talking about on TikTok",
            "board": "Trending Finds",
            "is_trending": True
        },
        {
            "name": "Aesthetic Room LED Strip Lights",
            "asin": "B08TRENDING2", 
            "image_id": "default",
            "category": "dorm_decor",
            "price": "15.99",
            "tags": "#ledlights #roomdecor #aesthetic",
            "description": "Color-changing LED strip lights for room ambiance",
            "board": "Dorm Decor",
            "is_trending": True
        }
    ]
    
    trending_products.extend(mock_trending)
    return trending_products

# Import products here to avoid circular imports
try:
    from .products import PRODUCTS
except ImportError:
    # Fallback if products.py not available yet
    PRODUCTS = []