"""
Products database for Pinterest automation
Contains product data and content pin templates
"""

# Sample product data - in practice this would be much larger and likely loaded from a database
PRODUCTS = [
    {
        "name": "LED Desk Lamp with USB Ports",
        "asin": "B08B4V3Y3Y",
        "image_id": "default",
        "category": "tech",
        "price": "29.99",
        "tags": "#desklamp #techgadgets #studylight",
        "description": "Adjustable LED desk lamp with built-in USB charging ports for your devices",
        "board": "Tech Gadgets",
        "store_url": None
    },
    {
        "name": "Memory Foam Seat Cushion",
        "asin": "B07FZ8S74R",
        "image_id": "default", 
        "category": "self_care",
        "price": "21.99",
        "tags": "#seatcushion #backpainrelief #officeessentials",
        "description": "Ergonomic memory foam seat cushion for office chairs and gaming seats",
        "board": "Wellness",
        "store_url": None
    },
    {
        "name": "Wireless Bluetooth Earbuds",
        "asin": "B07ZPVV8R3",
        "image_id": "default",
        "category": "tech", 
        "price": "39.99",
        "tags": "#bluetoothearbuds #wirelessaudio #tech",
        "description": "True wireless earbuds with noise cancellation and 24hr battery life",
        "board": "Tech Gadgets",
        "store_url": None
    },
    {
        "name": "Mini Fridge for Dorm Room",
        "asin": "B07Q3K6Z7K",
        "image_id": "default",
        "category": "dorm_decor",
        "price": "89.99", 
        "tags": "#minifridge #dormlife #collegeessentials",
        "description": "Compact 3.2 cubic foot mini fridge perfect for dorm rooms and offices",
        "board": "Dorm Decor",
        "store_url": None
    },
    {
        "name": "Aesthetic Desk Organizer Set",
        "asin": "B08L5RN93L",
        "image_id": "default",
        "category": "study_supplies",
        "price": "19.99",
        "tags": "#deskorganizer #studysupplies #aestheticdesk",
        "description": "Marble and gold desk organizer set with pen holder, tray, and card holder",
        "board": "Study Supplies", 
        "store_url": None
    },
    {
        "name": "Fleece Lined Leggings",
        "asin": "B07Q6ZHD7V",
        "image_id": "default",
        "category": "womens_fashion",
        "price": "24.99",
        "tags": "#fleeceleggings #winterfashion #cozyclothes",
        "description": "Thermal fleece lined leggings for winter warmth and comfort",
        "board": "Women's Fashion",
        "store_url": None
    }
]

# Content pin templates (text-based pins that perform well on Pinterest)
CONTENT_PINS = [
    {
        "title": "10 Study Hacks for College Students",
        "category": "study_supplies", 
        "tags": "#studytips #collegehacks #productivity",
        "description": "Essential study techniques every college student needs to know",
        "lines": [
            "Use the Pomodoro technique (25 min focus, 5 min break)",
            "Create mind maps for complex subjects", 
            "Teach the material to someone else to test understanding",
            "Use spaced repetition for long-term retention",
            "Study in different locations to improve memory",
            "Take handwritten notes instead of typing",
            "Use color coding for different subjects",
            "Create cheat sheets even if you can't use them",
            "Form a study group with focused peers",
            "Review material within 24 hours of learning it"
        ],
        "board": "Study Supplies"
    },
    {
        "title": "7 Budget-Friendly Dorm Room Essentials",
        "category": "dorm_decor",
        "tags": "#dormlife #collegeonbudget #roomdecor", 
        "description": "Affordable items that make any dorm feel like home",
        "lines": [
            "Command hooks for damage-free hanging",
            "Under-bed storage bins for seasonal clothing", 
            "Clip-on desk lamp for late-night studying",
            "Shower caddy for bathroom organization",
            "Mini fan for air circulation",
            "Laundry bag with handles",
            "Desk organizer for school supplies"
        ],
        "board": "Dorm Decor"
    },
    {
        "title": "5-Minute Morning Routine for Energy",
        "category": "self_care",
        "tags": "#morningroutine #wellness #selfcare",
        "description": "Quick morning habits to boost energy and focus all day",
        "lines": [
            "Drink a glass of water with lemon",
            "Do 10 jumping jacks or stretch",
            "Write down 3 priorities for the day", 
            "Listen to an upbeat song while getting ready",
            "Eat a protein-rich breakfast",
            "Step outside for natural sunlight",
            "Say one positive affirmation"
        ],
        "board": "Wellness"
    }
]

def get_all_categories():
    """Return list of all unique categories"""
    categories = set()
    for p in PRODUCTS:
        categories.add(p["category"])
    for cp in CONTENT_PINS:
        categories.add(cp["category"])
    return list(categories)

def get_affiliate_link(asin, tag="venu080d-21"):
    """Generate Amazon affiliate link"""
    return f"https://www.amazon.com/dp/{asin}?tag={tag}"

def get_image_url(asin, image_id="default", category="tech"):
    """Get product image URL - placeholder implementation"""
    # In a real implementation, this would look up actual image URLs
    # For now, return a placeholder or use the ASIN to construct a URL
    return f"https://m.media-amazon.com/images/I/{asin}._AC_SL1500_.jpg"

def get_product_count():
    """Get count of products by category"""
    from collections import Counter
    counts = Counter()
    
    # Count products
    for p in PRODUCTS:
        counts[p["category"]] += 1
    
    # Count content pins  
    for cp in CONTENT_PINS:
        counts[cp["category"]] += 1
        
    counts["total"] = sum(counts.values())
    counts["content_pins"] = len(CONTENT_PINS)
    
    return dict(counts)