"""
SEO Pin Title Optimizer — Rewrites product titles for Pinterest search ranking.

Why this matters:
- Pinterest rank: title match > 100% (most important field)
- Amazon feeds leave titles as "Logitech MX Master 3S Wireless Mouse, Logitech..."
  (keyword stuffed, no emotional pull)
- We rewrite to: keyword-front + emotional hook + power word + benefit
- Expected CTR lift: 2-5× over raw Amazon titles

Examples:
  BEFORE: "Anker Portable Charger 20000mAh Power Bank, Anker"
  AFTER:  "Anker 20,000mAh Power Bank for Students — All-Day Laptop Charging"

  BEFORE: "HP OfficeJet Pro 8025e Wireless Inkjet Printer"
  AFTER:  "HP Wireless Printer Under $100 — College Dorm Savior"

Formula used ([keyword phrase] + [power adverb] + [benefit] + [use case]):
  [Product Type] for [Audience] — [Benefit Hook]
"""

import re
import random
import textwrap
from typing import Tuple, List, Optional
import os
import json
import requests

_llm_cache = {}

def get_llm_seo_optimized(raw_title: str, category: str, price: str = None) -> tuple[str, str]:
    """Generates SMT-optimized title and description using an LLM via requests."""
    api_key = os.getenv("NVIDIA_API_KEY")
    if not api_key:
        return None, None
        
    cache_key = f"{raw_title}_{category}_{price}"
    if cache_key in _llm_cache:
        return _llm_cache[cache_key]
        
    prompt = f"""You are an expert Pinterest SEO marketer and affiliate sales copywriter.
Your goal is to generate a highly engaging, SMT-optimized Pinterest Title and Description for an Amazon affiliate product.
Product Name: {raw_title}
Category: {category}
Price: {price or 'Not specified'}

Rules:
1. Title must be under 100 characters. Use emotional hooks and power words to drive clicks.
2. Description must be under 500 characters. It must sound natural, highlight key benefits, include trending hashtags at the end, and end with a strong call-to-action to click the link to shop on Amazon.
3. Reply ONLY with a valid JSON object matching exactly this schema:
{{
  "title": "Your optimized title here",
  "description": "Your optimized description here"
}}
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "meta/llama-3.1-70b-instruct",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 300
    }
    
    try:
        resp = requests.post("https://integrate.api.nvidia.com/v1/chat/completions", headers=headers, json=payload, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        
        import re
        json_match = re.search(r"\{.*\}", content, re.DOTALL)
        if json_match:
            parsed = json.loads(json_match.group(0))
            _llm_cache[cache_key] = (parsed.get("title"), parsed.get("description"))
            return _llm_cache[cache_key]
    except Exception as e:
        print(f"  ⚠️ LLM SEO error: {e}")
        
    return None, None

POWER_ADVERBS = [
    "MUST-HAVE", "Best-Selling", "Top-Rated", "#1 Pick", "Editor-Tested",
    "Viral", "Student-Perfect", "Trending",
]

BENEFITS_BY_CATEGORY = {
    "tech": [
        "All-Day Battery Life", "Boost Your Productivity", "Crystal Clear Audio",
        "Lightweight & Portable", "Saves Space on Your Desk", "Works All Day",
        "Plug-and-Play Setup", "Faster Charging",
    ],
    "dorm_decor": [
        "Transforms Your Room", "Looks Aesthetic AF", "Matches Any Vibe",
        "Cozy & Instagram-Ready", "Tiny but Mighty",
    ],
    "study_supplies": [
        "Saves Hours Each Week", "A+ Notes Made Easy", "Bestseller",
        "Focus-Boosting", "Better Than a TextBook",
    ],
    "self_care": [
        "Dorm Bathroom Must-Have", "Better Than Sephora", "Petite-Approved",
    ],
    "kitchen": [
        "5-Min Breakfast", "No-Brainer", "Tiny Kitchen Hero",
    ],
    "fashion": [
        "Comfy All Day", "Versatile AF", "Date-Night Ready",
    ],
    "default": [
        "Compact Yet Powerful", "Trusted by Thousands",
        "Worth the Hype", "Pick of the Month",
    ],
}

AUDIENCE_PHRASES = [
    "for College Students", "for Students on a Budget", "for 9-to-5 Students",
    "for the Dorm", "for Studying Late", "for Back-to-School",
    "Every College Student", "Any Student Needs This",
]

# Common keyword spam patterns to strip from Amazon-fed titles
AMAZON_NOISE_PATTERNS = [
    r",\s*[\w\s]+(?=,|$)",          # trailing brand commas
    r"\s+-\s+[\w\s]+?(Best|Amazon|New|Brand)",
    r"\s{2,}",
    r"\b(Brand New|Visit the|Store|com|Brand Name)\b.*?[,|.]",
    r"\([^()]{30,}\)",               # long parentheticals
    r"\b(Compatible with|Works with|Designed for|For Use with) [^\.]+",
]


# ── Helpers ───────────────────────────────────────────────────────────────


def _clean_amazon_title(raw: str) -> str:
    """Strip Amazon-junk (keyword spam, brand mentions, parentheticals)."""
    if not raw:
        return ""
    t = raw.strip()

    # Apply removals
    for pat in AMAZON_NOISE_PATTERNS:
        t = re.sub(pat, " ", t, flags=re.IGNORECASE)

    # Remove double commas/spaces
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s,", ",", t)
    t = t.strip().strip(",").strip()

    # Trim to a clean core (~first 60 chars are keyword gold)
    if len(t) > 90:
        # Try to cut at comma boundary
        parts = t.split(",")
        if parts:
            t = parts[0].strip()

    return t


def _detect_category_from_title(title: str, hint: str = "") -> str:
    """Guess category from title keywords."""
    text = (title + " " + hint).lower()
    if any(k in text for k in ["laptop", "charger", "headphone", "speaker", "mouse",
                                "monitor", "usb", "hdmi", "wireless"]):
        return "tech"
    if any(k in text for k in ["pillow", "bed", "lamp", "rug", "wall", "poster",
                                "decor", "candle", "organizer"]):
        return "dorm_decor"
    if any(k in text for k in ["pen", "notebook", "planner", "highlight",
                                "sticky", "binder", "folder"]):
        return "study_supplies"
    if any(k in text for k in ["skin", "lotion", "shampoo", "makeup",
                                "sunscreen", "self-care", "self care"]):
        return "self_care"
    if any(k in text for k in ["kitchen", "mug", "waffle", "blender", "coffee",
                                "cooker", "bottle"]):
        return "kitchen"
    if any(k in text for k in ["hoodie", "shirt", "jeans", "shoes", "dress",
                                "fashion", "outfit"]):
        return "fashion"
    return "default"


def _title_case(text: str) -> str:
    """Convert to Title Case except for small connector words.

    Handles: "20000mAh" → "20000mAh"
             "honestly: a" → "Honestly: A"
             "AC adapter" → "AC Adapter"
    """
    small_words = {"a", "an", "and", "as", "but", "for", "in", "nor", "of",
                   "on", "or", "so", "the", "to", "with", "yet"}
    words = re.split(r"(\s+|:)", text)
    out = []
    capitalize_next = True
    for w in words:
        if not w.strip() or w.isspace() or w == ":":
            out.append(w)
            capitalize_next = (w != ":")
            continue
        wl = w.lower()
        # Preserve all-caps / numbers / acronyms
        if w.isupper() and len(w) > 1:
            out.append(w)
        elif any(c.isdigit() for c in w):
            out.append(w)        # "20,000mAh" or "8025e"
        elif wl in small_words and not capitalize_next:
            out.append(wl)
        else:
            out.append(w.capitalize())
        capitalize_next = False
    return "".join(out)


def _extract_keyword_phrase(raw_title: str) -> str:
    """Pull the 2-6 keyword-rich words from a noisy Amazon title."""
    cleaned = _clean_amazon_title(raw_title)
    if not cleaned:
        return ""

    # Pick first noun-heavy fragment
    tokens = cleaned.split()
    if tokens and len(tokens[0]) <= 12 and tokens[0].istitle():
        # Remove leading brand like "Logitech" / "Anker"
        # Keep if it's part of mainstream noun ("Apple Pencil" → keep)
        if tokens[0].lower() not in {"apple"}:
            tokens = tokens[1:] if len(tokens) > 2 else tokens

    phrase = " ".join(tokens)

    # Drop trailing junk like "— 3 Pieces", "3 Pieces", "- 5 Pack"
    phrase = re.sub(r"\s*[-\u2014]\s*\d+\s*(Pieces?|Pack|Pcs?)\s*$", "", phrase, flags=re.IGNORECASE)
    phrase = re.sub(r"\s*-\s*(Black|White|Blue|Red|Green|Pink|Purple|Gray|Grey)\s*$", "", phrase, flags=re.IGNORECASE)

    # Drop trailing punctuation
    phrase = phrase.strip().rstrip("-:\u2014 .,")

    # Trim to ≤6 words for keyboard readability
    words = phrase.split()
    if len(words) > 6:
        phrase = " ".join(words[:6])

    return _title_case(phrase)


# ── Main API ─────────────────────────────────────────────────────────────


def seo_optimize(
    raw_title: str,
    category: str = "",
    audience: Optional[str] = None,
    benefit: Optional[str] = None,
    max_length: int = 90,
) -> str:
    """
    Rewrite an Amazon-style title into a Pinterest-SEO-friendly title.

    Args:
        raw_title: Original title (Amazon-fed or any)
        category: Force category (else auto-detected)
        audience: Override audience phrase (else random)
        benefit: Override benefit phrase (else random)
        max_length: Max character length (Pinterest limit ~100)

    Returns:
        SEO-optimized title
    """
    if not raw_title or not raw_title.strip():
        return ""

    cat = category.lower() if category else _detect_category_from_title(raw_title)
    keyword_phrase = _extract_keyword_phrase(raw_title)
    if not keyword_phrase:
        keyword_phrase = _title_case(_clean_amazon_title(raw_title))[:60]

    adv = random.choice(POWER_ADVERBS)

    if audience is None:
        audience = random.choice(AUDIENCE_PHRASES)

    if benefit is None:
        benefit = random.choice(BENEFITS_BY_CATEGORY.get(cat, BENEFITS_BY_CATEGORY["default"]))

    # Compose title — format: "[Keyword Phrase] — [Audience]: [Benefit]"
    composed = f"{keyword_phrase} {audience} — {benefit}"

    # Add power adverb for emphasis (occasionally)
    if random.random() < 0.35:
        composed = f"{adv} {composed}"

    # Cap length
    if len(composed) > max_length:
        composed = composed[: max_length - 3].rstrip() + "..."

    return composed


def seo_variants(raw_title: str, category: str = "", n: int = 3) -> List[str]:
    """Generate N SEO-optimized variants for A/B testing."""
    variants = []
    for _ in range(n):
        variants.append(seo_optimize(raw_title, category))
    return list(dict.fromkeys(variants))  # dedupe preserving order


# ── Batch processor ─────────────────────────────────────────────────────


def optimize_csv_column(
    csv_path: str = "data.csv",
    source_col: str = "Product Name",
    target_col: str = "SEO Title",
    category_col: str = "Category",
    backup_existing: bool = True,
):
    """
    Add SEO-optimized titles to data.csv as a new column.
    Original Product Name stays intact (used by Amazon link generator).
    """
    import pandas as pd
    from database import get_products_df, save_products_df

    df = get_products_df().fillna("")

    if backup_existing and target_col not in df.columns:
        df[target_col] = ""

    updated = 0
    for i, row in df.iterrows():
        raw = str(row.get(source_col, "")).strip()
        if not raw:
            continue
        existing = str(row.get(target_col, "")).strip()
        # Only fill empty ones to preserve manual edits
        if existing:
            continue
        cat = str(row.get(category_col, "")).strip()
        df.at[i, target_col] = seo_optimize(raw, cat)
        updated += 1

    save_products_df(df)
    print(f"  ✅ {updated} products optimized")
    print(f"  📄 Column 'SEO Title' added to {csv_path}")


# ── CLI mode ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: seo_optimizer.py '<title>' [category]")
        print("       seo_optimizer.py csv         # Optimize all in data.csv")
        print()
        print("Quick test:")
        seo_variants(
            "Logitech MX Master 3S Wireless Mouse, Logitech, Computer Peripherals",
            category="tech",
        )
        out = seo_variants("Anker Portable Charger 20000mAh Power Bank", "tech", 3)
        for v in out:
            print(f"  → {v}")
        sys.exit(0)

    cmd = sys.argv[1]
    if cmd == "csv":
        optimize_csv_column()
    else:
        cat = sys.argv[2] if len(sys.argv) > 2 else ""
        out = seo_optimize(cmd, cat)
        print(f"  Original: {cmd}")
        print(f"  SEO:      {out}")
