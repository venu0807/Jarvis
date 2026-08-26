"""
Pinterest Affiliate Bot — Full Orchestrator
============================================
Modes:
  1. run       — Post pins from data.csv (default)
  2. refill    — Auto-fill data.csv with products from database
  3. stats     — Show product/post stats
  4. schedule  — Post at optimal times throughout the day
  5. video     — Convert pin image to vertical video (Reels format)
  6. crosspost — Generate videos AND post to Instagram Reels
  7. bio       — Generate/regenerate the bio link page

Usage:
  python main.py                       → run automation (post pins)
  python main.py crosspost --count 3    → cross-post 3 to Instagram Reels
  python main.py video                 → generate video from latest pin
  python main.py bio                   → regenerate bio link page
  python main.py stats                 → show stats
"""

import sys
import os
import time
import random
import argparse
import requests

import pandas as pd
from database import get_products_df, save_products_df
from dotenv import load_dotenv

load_dotenv()

from seo_gemini import generate_seo_title, generate_seo_description
from generator import generate_pin
from aesthetic_blender import generate_aesthetic_pin
from collage_builder import generate_collage_pin
from video_builder import generate_video_pin
from video_collage import generate_flash_collage
from poster import post_pin
from datetime import datetime
from products import (
    PRODUCTS, CONTENT_PINS, get_all_categories,
    get_affiliate_link, get_image_url, get_product_count
)
from trending import get_trending_asins, enrich_with_trending

# ── Configuration ───────────────────────────────────────────────────────
CSV_FILE = "data.csv"
SLEEP_BETWEEN_PINS = 12  # seconds
PINS_PER_RUN = 20        # default max pins per run
AMAZON_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "studentdeals0a-20")
# ── Stats ───────────────────────────────────────────────────────────────


def show_stats():
    """Display a dashboard of products, pins posted, and earnings potential."""
    print("\n" + "=" * 55)
    print("   📊  PINTEREST BOT — STAT DASHBOARD")
    print("=" * 55)

    # Product database stats
    counts = get_product_count()
    print(f"\n  📦 Product Database:")
    for cat in get_all_categories():
        print(f"     • {cat.replace('_',' ').title()}: {counts[cat]} products")
    print(f"     ─────────────────────")
    print(f"     📝 Content pin templates: {counts['content_pins']}")
    print(f"     🛍️  Total products:        {counts['total']}")
    print(f"     💡 Total pin ideas:       {counts['total'] + counts['content_pins']}")

    # CSV stats
    if True:
        df = get_products_df()
        total = len(df)
        pinned = len(df[df.get("Status", "").astype(str).str.strip().str.lower() == "pinned"])
        pending = total - pinned
        print(f"\n  📋 Database Status:")
        print(f"     ✅ Pinned:  {pinned}")
        print(f"     ⏳ Pending: {pending}")
        print(f"     📊 Total:   {total}")
        if pinned > 0:
            print(f"\n  💰 Earnings Potential (estimated):")
            print(f"     • At 100 pins/month → ~{pinned * 5} monthly views (avg)")
            print(f"     • At 1% CTR → ~{int(pinned * 5 * 0.01)} clicks/month")
            print(f"     • At $0.50/click → ~${int(pinned * 5 * 0.01 * 0.50)}/month")
            print(f"     • SCALE TIP: 500+ pins = real income!")

        # Template distribution (new)
        if "Pin_Template" in df.columns:
            from collections import Counter
            template_counts = Counter(
                df["Pin_Template"].astype(str).str.strip().replace("", "auto")
            )
            if template_counts:
                print(f"\n  📐 Template Distribution:")
                # Sort by count desc, then alpha
                items = sorted(template_counts.items(), key=lambda x: (-x[1], x[0]))
                max_count = max(items, key=lambda x: x[1])[1]
                for tpl, count in items:
                    bar_len = int(20 * count / max_count)
                    bar = "█" * bar_len + "░" * (20 - bar_len)
                    print(f"     {tpl:18} {bar} {count}")
    else:
        print(f"\n  ❌ {CSV_FILE} not found!")

    print(f"\n  ⚙️  Configuration:")
    print(f"     • Post method: API v5 (→ browser fallback if needed)")
    print(f"     • Pins per run: {PINS_PER_RUN}")
    print(f"     • Delay: {SLEEP_BETWEEN_PINS}s between pins")
    print(f"     • Amazon tag: {AMAZON_TAG}")
    print("=" * 55 + "\n")


# ── Refill CSV ──────────────────────────────────────────────────────────


def refill_csv():
    """Auto-fill data.csv with products from our curated database.
    
    Adds products that aren't already in the CSV to avoid duplicates.
    """
    print("\n  🔄 Refilling data.csv with products from database...")

    # Load existing CSV
    existing_names = set()
    if True:
        df_existing = get_products_df()
        existing_names = set(df_existing["Product Name"].str.strip().str.lower())
        print(f"  📋 Found {len(df_existing)} existing products in CSV")

    # Also add some content pins (text-based tips)
    new_rows = []
    added = 0

    for p in PRODUCTS:
        name = p["name"].strip().lower()
        if name not in existing_names:
            # Use store_url if available (affiliate store products), else use Amazon direct link
            link = p.get("store_url") or get_affiliate_link(p["asin"], AMAZON_TAG)
            img_url = get_image_url(p["asin"], p.get("image_id"), p.get("category", "tech"))
            new_rows.append({
                "Product Name": p["name"],
                "Image URL": img_url,
                "Affiliate Link": link,
                "Status": "",
                "Category": p["category"],
                "Price": p["price"],
                "Tags": p.get("tags", ""),
                "Description": p.get("description", ""),
                "Pin Type": "product",
                "Board": p.get("board", "")
            })
            existing_names.add(name)
            added += 1

    # Add content pins (text-based tips)
    for cp in CONTENT_PINS:
        title = cp["title"].strip().lower()
        if title not in existing_names:
            # Generate a generic Amazon link for content pins
            link = f"https://www.amazon.com/s?k={'+'.join(cp['title'].split()[:5])}&tag={AMAZON_TAG}"
            new_rows.append({
                "Product Name": cp["title"],
                "Image URL": "",  # No image — will generate text-only pin
                "Affiliate Link": link,
                "Status": "",
                "Category": cp["category"],
                "Price": "",
                "Tags": cp.get("tags", ""),
                "Description": cp.get("description", ""),
                "Pin Type": "content",
                "Content Lines": "|".join(cp["lines"]),
                "Board": cp.get("board", "")
            })
            existing_names.add(title)
            added += 1

    if added == 0:
        print("  ✅ No new products to add — CSV is up to date!")
        return

    # Append to CSV
    new_df = pd.DataFrame(new_rows)
    if True:
        combined = pd.concat([df_existing, new_df], ignore_index=True)
        save_products_df(combined)
    else:
        save_products_df(new_df)

    print(f"  ✅ Added {added} new entries to {CSV_FILE}!")
    print(f"  📊 Total products now: {len(get_products_df())}")

    # Show categories added
    categories = set(r["Category"] for r in new_rows)
    print(f"  📂 Categories: {', '.join(categories)}")


def refill_csv_trending():
    """Refill CSV with trending products prioritized at the top."""
    print("\n  🔥 Refilling data.csv with TRENDING products prioritized...")

    # Get trending ASINs
    trending_asins = get_trending_asins(limit=20)
    print(f"  📈 Found {len(trending_asins)} trending ASINs")

    # Load existing CSV
    existing_names = set()
    if True:
        df_existing = get_products_df()
        existing_names = set(df_existing["Product Name"].str.strip().str.lower())
        print(f"  📋 Found {len(df_existing)} existing products in CSV")

    # Enrich products with trending data
    enriched_products = enrich_with_trending(PRODUCTS, trending_asins)

    new_rows = []
    added = 0

    # First pass: add trending products
    for p in enriched_products:
        if p.get("is_trending", False):
            name = p["name"].strip().lower()
            if name not in existing_names:
                link = get_affiliate_link(p["asin"], AMAZON_TAG)
                img_url = get_image_url(p["asin"], p.get("image_id"), p.get("category", "tech"))
                new_rows.append({
                    "Product Name": p["name"],
                    "Image URL": img_url,
                    "Affiliate Link": link,
                    "Status": "",
                    "Category": p["category"],
                    "Price": p["price"],
                    "Tags": p.get("tags", "") + " #TRENDING",
                    "Description": p.get("description", "") + " 🔥 TRENDING NOW!",
                    "Pin Type": "product"
                })
                existing_names.add(name)
                added += 1
                print(f"    🔥 Added TRENDING: {p['name'][:50]}")

    # Second pass: add regular products
    for p in enriched_products:
        if not p.get("is_trending", False):
            name = p["name"].strip().lower()
            if name not in existing_names:
                link = get_affiliate_link(p["asin"], AMAZON_TAG)
                img_url = get_image_url(p["asin"], p.get("image_id"), p.get("category", "tech"))
                new_rows.append({
                    "Product Name": p["name"],
                    "Image URL": img_url,
                    "Affiliate Link": link,
                    "Status": "",
                    "Category": p["category"],
                    "Price": p["price"],
                    "Tags": p.get("tags", ""),
                    "Description": p.get("description", ""),
                    "Pin Type": "product"
                })
                existing_names.add(name)
                added += 1

    if added == 0:
        print("  ✅ No new products to add — CSV is up to date!")
        return

    # Append to CSV (trending products first)
    new_df = pd.DataFrame(new_rows)
    if True:
        combined = pd.concat([df_existing, new_df], ignore_index=True)
        save_products_df(combined)
    else:
        save_products_df(new_df)

    print(f"  ✅ Added {added} new entries to {CSV_FILE}!")
    print(f"  📊 Total products now: {len(get_products_df())}")

    # Show categories added
    categories = set(r["Category"] for r in new_rows)
    print(f"  📂 Categories: {', '.join(categories)}")


# ── Refill with Trending Products ────────────────────────────────────────────


def refill_trending():
    """Fetch live trending products and add them to data.csv.

    Uses Amazon Best Sellers for current trending student products.
    Caches results for 6 hours to avoid hammering Amazon.
    """
    try:
        from trending_fetcher import get_trending_products
    except ImportError:
        print("  ❌ trending_fetcher.py not found")
        return

    print("\n  🔥 Fetching LIVE TRENDING products from Amazon...")
    trending = get_trending_products(force_refresh=True)

    print("\n=====================================")
    print("   REFILLING FROM DYNAMIC TRENDS     ")
    print("=====================================")
    from amazon_scraper import scrape_amazon
    scrape_amazon()
    print("✅ Successfully filled CSV with dynamic Pinterest trends from Amazon!")



# ── Run Automation ──────────────────────────────────────────────────────

def send_to_n8n(image_path: str, title: str, description: str, link: str):
    """Fires a webhook to n8n containing the generated video and SEO metadata."""
    webhook_url = os.getenv("N8N_WEBHOOK_URL")
    if not webhook_url:
        return
    
    try:
        print(f"  🌐 Firing webhook to n8n...")
        
        # We send the text data as form data
        data = {
            "title": title,
            "description": description,
            "link": link
        }
        
        # We upload the raw .mp4 or .png file directly to n8n
        if image_path and os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                files = {'file': (os.path.basename(image_path), f)}
                response = requests.post(webhook_url, data=data, files=files, timeout=15)
        else:
            response = requests.post(webhook_url, data=data, timeout=15)
            
        if response.status_code in [200, 201]:
            print(f"  ✅ Successfully sent to n8n!")
        else:
            print(f"  ⚠️  n8n Webhook returned status code: {response.status_code}")
    except Exception as e:
        print(f"  ❌ Failed to send webhook to n8n: {e}")


def run_automation(max_pins: int = None, category: str = None):
    """Main automation loop — post pending pins from CSV."""
    if max_pins is None:
        max_pins = PINS_PER_RUN

    print("\n" + "=" * 55)
    print("   🚀  PINTEREST AUTOMATION BOT")
    if category:
        print(f"   Category: {category}")
    print("   Using API v5 → Browser fallback")
    print("=" * 55)

    # Check CSV exists
    if not True:
        print(f"\n  ❌ {CSV_FILE} not found!")
        print("  💡 Run 'python main.py refill' to populate it first!")
        return

    df = get_products_df().fillna("")
    total = len(df)

    # Find pending pins
    pending_mask = df["Status"].astype(str).str.strip().str.lower() != "pinned" if "Status" in df.columns else pd.Series([True] * len(df))
    if category:
        pending_mask = pending_mask & (df["Category"].astype(str).str.strip().str.lower() == category.lower() if "Category" in df.columns else pd.Series([True] * len(df)))
    pending_indices = df[pending_mask].index.tolist()

    if not pending_indices:
        print("\n  ✅ All products have been pinned!")
        print("  💡 Run 'python main.py refill' to add more products!")
        return

    print(f"\n  📋 {len(pending_indices)} pins pending out of {total} total")
    print(f"  🎯 Posting up to {max_pins} pins this run")

    # Limit to max_pins
    target_indices = pending_indices[:max_pins]
    pinned_count = 0
    skipped_count = 0
    failed_count = 0
    start_time = time.time()

    try:
        for idx, csv_idx in enumerate(target_indices):
            row = df.loc[csv_idx]
            title = row["Product Name"]
            # Use SEO Title if present, otherwise auto-generate one
            seo_title = str(row.get("SEO Title", "")).strip()
            category = str(row.get("Category", "")).strip()
            is_trending_row = (csv_idx >= len(df) - 6)  # last 6 = trending

            if seo_title:
                post_title = seo_title
            else:
                try:
                    post_title = generate_seo_title(title, category, is_trending=is_trending_row)
                except Exception:
                    post_title = title
            img_url = str(row.get("Image URL", ""))
            aff_link = str(row.get("Affiliate Link", ""))
            price = str(row.get("Price", ""))
            tags = str(row.get("Tags", ""))
            description = str(row.get("Description", ""))
            pin_type = str(row.get("Pin Type", "product"))
            content_lines_raw = str(row.get("Content Lines", ""))
            pin_template = str(row.get("Pin_Template", "")).strip()
            board_name = str(row.get("Board", "")).strip()

            if not board_name:
                category_board_map = {
                    "student": "College & Student Essentials",
                    "beauty": "Viral Beauty Hacks & Skincare",
                    "decor": "Trendy Home Decor & Apartment Ideas",
                    "dorm_decor": "Aesthetic Dorm Decor & Organization",
                    "kitchen": "Genius Kitchen Gadgets & Finds",
                    "tech": "Aesthetic Desk Setup & Tech Gadgets",
                    "tech_gadgets": "Aesthetic Desk Setup & Tech Gadgets",
                    "womens_fashion": "Women's Fashion & Style Inspo",
                    "mens_fashion": "Men's Fashion & Outfit Ideas",
                    "wellness": "Wellness Routine & Self Care",
                    "self_care": "Wellness Routine & Self Care",
                    "cozy_home": "Cozy Home Decor Ideas"
                }
                board_name = category_board_map.get(category.lower(), "Trending Amazon Finds")


            # --- Seasonal Trend Surfing (Holiday Spike Engine) ---
            month = datetime.now().month
            seasonal_prefix = ""
            seasonal_tags = ""
            
            if month in [1, 2]:
                seasonal_prefix = "Valentine's Gift: "
                seasonal_tags = " #valentinesgift #giftideas #selflove"
            elif month == 5:
                seasonal_prefix = "Mother's Day Find: "
                seasonal_tags = " #mothersdaygift #giftformom"
            elif month == 7:
                seasonal_prefix = "Prime Day Deal: "
                seasonal_tags = " #primedaydeals #amazonmusthaves"
            elif month in [8, 9]:
                seasonal_prefix = "Back to School: "
                seasonal_tags = " #backtoschool #dormessentials #collegelife"
            elif month == 10:
                seasonal_prefix = "Fall Aesthetic: "
                seasonal_tags = " #fallaesthetic #halloweenfinds #cozyseason"
            elif month in [11, 12]:
                seasonal_prefix = "Holiday Gift Guide: "
                seasonal_tags = " #blackfridaydeals #christmasgifts #giftguide"

            # Inject SEO prefix if title isn't already too long
            if seasonal_prefix and len(post_title) < 65:
                post_title = f"{seasonal_prefix}{post_title}"
                
            # Inject high-conversion seasonal tags
            if seasonal_tags:
                tags = f"{tags}{seasonal_tags}"
                description = f"{description}{seasonal_tags}"

            # --- Layout --- 
            chosen_layout = "seo_full_bleed"

            # --- Format Probability ---
            # 20% Collage, 40% Video, 40% Static
            # User requested strictly quality static images only
            pin_format = "static"

            print(f"\n{'─' * 50}")
            print(f"  [{idx + 1}/{len(target_indices)}] {post_title[:70]}")
            print(f"  📏 Format: {pin_format.upper()} | Layout: {chosen_layout.upper()}")
            print(f"{'─' * 50}")

            # Generate pin image
            output_file = f"pin_{csv_idx}.png"
            video_file = f"pin_{csv_idx}.mp4"
            try:
                is_content = pin_type.strip().lower() == "content" or not img_url

                if is_content:
                    lines = [l.strip() for l in content_lines_raw.split("|") if l.strip()] if content_lines_raw else None
                    if not lines: lines = [post_title[:30]]
                    local_img = generate_pin(
                        post_title, "", output_file,
                        is_content=True, lines=lines,
                        tags=tags, template=pin_template or None
                    )
                elif pin_format == "collage":
                    same_cat = [p for p in PRODUCTS if p["category"] == category]
                    if len(same_cat) >= 4:
                        urls = [get_image_url(p["asin"], p.get("image_id"), category) for p in random.sample(same_cat, 4)]
                        local_img = generate_collage_pin(urls, f"Ultimate {category.replace('_', ' ').title()} Pack", category, os.path.join("output", output_file))
                        post_title = f"Ultimate {category.replace('_', ' ').title()} Starter Pack! #aesthetic #starterpack"
                    else:
                        pin_format = "static"

                if not is_content and pin_format in ["static", "video"]:
                    lifestyle_img = str(row.get("Lifestyle Image", ""))
                    if not lifestyle_img:
                        lifestyle_img = img_url
                        
                    import random
                    post_as_video = random.choice([True, False])
                    
                    # Generate aesthetic template variations (3 for video, 1 for static)
                    temp_imgs = []
                    num_templates = 3 if post_as_video else 1
                    for t_idx in range(num_templates):
                        t_out = os.path.join("output", f"temp_{t_idx}_{output_file}")
                        t_success = generate_aesthetic_pin(
                            image_url=lifestyle_img,
                            category=category,
                            output_path=t_out,
                            title=post_title,
                            subtitle=description[:60] + "..." if len(description) > 60 else description,
                            price=row.get("Price", ""),
                            product_image_url=row.get("Image URL", "")
                        )
                        if t_success:
                            temp_imgs.append(t_out)

                    # Convert to Fast Collage Video OR keep as single static image
                    if temp_imgs:
                        if post_as_video and len(temp_imgs) > 1:
                            video_out = os.path.join("output", video_file)
                            print(f"  🎬 Generating Flash Collage Video: {video_out}")
                            generated_video = generate_flash_collage(temp_imgs, video_out, fps=30, duration_per_image=1.5)
                            if generated_video and os.path.exists(generated_video):
                                local_img = generated_video # Override static image path with video path
                            else:
                                local_img = temp_imgs[0] # Fallback
                        else:
                            print(f"  🖼️ Using single Aesthetic Static Image instead of video")
                            local_img = temp_imgs[0]
                    else:
                        local_img = None
            except Exception as e:
                print(f"  ❌ Image generation failed: {e}")
                failed_count += 1
                continue

            if not local_img or not os.path.exists(local_img):
                print(f"  ⚠️  Image not generated — skipping pin")
                failed_count += 1
                continue

            bio_link = os.getenv("BIO_LINK")
            if bio_link:
                utm = "utm_source=Pinterest&utm_medium=organic"
                final_link = f"{bio_link}?{utm}&asin={row.get('ASIN', '')}" if row.get('ASIN') else f"{bio_link}?{utm}"
            else:
                final_link = aff_link

            success = post_pin(
                image_path=local_img, 
                title=post_title, 
                link=final_link,
                description=description,
                board_name=board_name if board_name else None
            )

            if success:
                df.at[csv_idx, "Status"] = "Pinned"
                save_products_df(df)
                print(f"  ✅ CSV updated")
                pinned_count += 1
                
                # Instantly ping the n8n Webhook with the video and data
                send_to_n8n(image_path=local_img, title=post_title, description=description, link=final_link)
                
                # Publish event to the unified Jarvis Event Bus
                try:
                    import sys
                    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
                    from event_bus import get_bus
                    bus = get_bus()
                    bus.publish("pinterest.*", "pinterest.pin_posted", {
                        "product": post_title,
                        "board": board_name if board_name else "",
                        "link": final_link
                    })
                except Exception as e:
                    print(f"  ⚠️ Could not publish event: {e}")
            else:
                print(f"  ❌ Failed to post '{title}'")
                failed_count += 1

            # Pause between pins (but not after the last one)
            if idx < len(target_indices) - 1:
                delay = SLEEP_BETWEEN_PINS + random.uniform(-2, 3)
                print(f"  ⏳ Waiting {delay:.0f}s before next pin...")
                time.sleep(delay)
    finally:
        # Cleanup browser
        from poster import cleanup_browser
        cleanup_browser()

    # ── Run Summary ──
    elapsed = time.time() - start_time
    print(f"\n{'=' * 55}")
    print(f"   📊 RUN COMPLETE")
    print(f"   {'=' * 50}")
    print(f"   ✅ Posted:    {pinned_count}")
    print(f"   ❌ Failed:    {failed_count}")
    print(f"   ⏭️  Skipped:   {skipped_count}")
    print(f"   ⏱️  Duration:  {elapsed:.0f}s")
    print(f"   ⚡ Rate:      {pinned_count / max(elapsed, 1) * 60:.1f} pins/hr")

    # Remaining estimate
    df = get_products_df()
    remaining = len(df[df.get("Status", "").astype(str).str.strip().str.lower() != "pinned"])
    if remaining > 0:
        eta = remaining * SLEEP_BETWEEN_PINS / 60
        print(f"   📋 Remaining: {remaining} pins (~{eta:.0f} min at current rate)")
    print(f"{'=' * 55}\n")

    # Earning tip
    if pinned_count > 0:
        print(f"  💰 TIP: Run this daily to see real results!")
        print(f"      python main.py\n")

# ── Schedule Mode ───────────────────────────────────────────────────────


def run_schedule():
    """Post pins at optimal times throughout the day.
    
    Best posting times for Pinterest (student audience):
      • Morning:    7-9 AM (before class)
      • Lunch:     12-1 PM (study break)
      • Evening:    7-10 PM (homework time)
      • Late night: 11 PM - 1 AM (scrolling before bed)
    """
    print("\n" + "=" * 55)
    print("   📅  SCHEDULE MODE — Optimal Posting")
    print("=" * 55)

    slots = [
        ("🌅 Morning",   7, 0),
        ("☀️ Lunch",    12, 0),
        ("🌆 Evening",  18, 0),
        ("🌙 Night",    22, 0),
    ]

    print("\n  Today's scheduled posting slots:")
    for name, h, m in slots:
        print(f"     {name}: {h:02d}:{m:02d}")

    print(f"\n  📌 {PINS_PER_RUN} pins per slot")
    print(f"  ⏱️  {SLEEP_BETWEEN_PINS}s between pins")
    print()

    for slot_name, hour, minute in slots:
        current_hour = time.localtime().tm_hour
        if current_hour < hour:
            wait = (hour - current_hour) * 3600 - time.localtime().tm_min * 60
            print(f"  ⏳ Waiting {wait // 60} min until {hour:02d}:00...")
            if wait > 0:
                time.sleep(wait)
        
        print(f"\n  {slot_name} slot ({hour:02d}:00) — posting {PINS_PER_RUN} pins...")
        print(f"  ⚠️  If this is your first run, you'll need to log in to Pinterest in the browser window.")
        print(f"     The session will be saved for future runs.")
        run_automation(max_pins=PINS_PER_RUN)
        print(f"  ✅ {slot_name} slot complete!")


# ── CLI Entry Point ─────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Pinterest Affiliate Bot + Instagram Reels Cross-Poster",
        usage="python main.py [command] [options]"
    )
    parser.add_argument("command", nargs="?", default="run",
                        help="Command: run (default), refill, stats, schedule, "
                             "crosspost, video, bio, trending, seo")
    parser.add_argument("--count", type=int, default=None,
                        help="Max items to post this run")
    parser.add_argument("--category", type=str, default=None,
                        help="Filter by category (tech, dorm_decor, study_supplies, etc.)")
    parser.add_argument("--trending", action="store_true",
                        help="Use live trending products instead of static database")
    parser.add_argument("--platforms", type=str, default="pinterest",
                        help="Platforms for crosspost: pinterest (default), "
                             "tiktok (comma-separated)")

    args = parser.parse_args()

    if args.command == "stats":
        show_stats()
    elif args.command == "refill":
        if args.trending:
            refill_trending()
        else:
            refill_csv()
    elif args.command == "schedule":
        run_schedule()
    elif args.command == "crosspost":
        from cross_post import cross_post
        platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
        cross_post(
            count=args.count or 3,
            platforms=platforms,
            category=args.category,
        )
    elif args.command == "video":
        from cross_post import _build_video_for_row
        import pandas as pd
        from database import get_products_df, save_products_df
        df = get_products_df().fillna("")
        pending = df[
            df["Status"].astype(str).str.strip().str.lower().isin(["", "pending"])
        ]
        if pending.empty:
            print("  ⚠️  No pending products — run refill first")
        else:
            row = pending.iloc[0]
            print(f"  🎬 Generating video for: {row['Product Name']}")
            vid = _build_video_for_row(row)
            if vid:
                print(f"  ✅ Video saved: {vid}")
    elif args.command == "bio":
        from bio_page import generate_bio_page
        out = generate_bio_page(max_products=8)
        print(f"\n  📄 Preview: file://{os.path.abspath(out)}")
        print(f"  🚀 Deploy free: github.io, netlify.com, or surge.sh")
    elif args.command == "seo":
        from seo_optimizer import optimize_csv_column, seo_variants
        print("  🔧 SEO-optimizing all products in database...")
        optimize_csv_column()
        # Show 3 sample variants
        import pandas as pd
        from database import get_products_df, save_products_df
        df = get_products_df().fillna("")
        print("\n  📝 Sample SEO variants:")
        for i, row in df.head(3).iterrows():
            raw = str(row.get("Product Name", ""))
            seo = str(row.get("SEO Title", ""))
            print(f"    {raw[:50]}")
            print(f"    → {seo[:80]}")
            print()
    elif args.command == "trending":
        # Fetch and add trending products
        refill_trending()
        run_automation(max_pins=args.count or PINS_PER_RUN, category=args.category)
    else:  # run (default)
        if args.trending:
            refill_trending()
        run_automation(max_pins=args.count or PINS_PER_RUN, category=args.category)


if __name__ == "__main__":
    main()
