#!/usr/bin/env python3
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
  8. health    — Run health check server only

Usage:
  python main.py                       → run automation (post pins)
  python main.py crosspost --count 3    → cross-post 3 to Instagram Reels
  python main.py video                 → generate video from latest pin
  python main.py bio                   → regenerate bio link page
  python main.py stats                 → show stats
  python main.py health                → run health server only
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

# ── Health Check Server ─────────────────────────────────────────────────────

async def start_health_server():
    """Start the health check HTTP server."""
    from aiohttp import web
    import httpx
    import asyncpg
    import structlog
    
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    logger = structlog.get_logger()
    
    async def health_check(request):
        """Health check endpoint."""
        try:
            ollama_url = os.getenv("OLLAMA_HOST", "http://host.docker.internal:11434")
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{ollama_url}/api/tags")
                ollama_healthy = resp.status_code == 200
                models = resp.json().get("models", []) if ollama_healthy else []
        except Exception:
            ollama_healthy = False
            models = []
        
        try:
            db_url = os.getenv("DATABASE_URL", "postgresql://jarvis:jarvis@postgres:5432/jarvis")
            conn = await asyncpg.connect(db_url, timeout=3.0)
            await conn.close()
            db_healthy = True
        except Exception:
            db_healthy = False
        
        try:
            router_url = os.getenv("MODEL_ROUTER_URL", "http://model-router:8090")
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{router_url}/healthz")
                router_healthy = resp.status_code == 200
        except Exception:
            router_healthy = False
        
        healthy = ollama_healthy and db_healthy
        status = "healthy" if healthy else "degraded"
        
        return web.json_response({
            "status": status,
            "service": "pinterest",
            "ollama_healthy": ollama_healthy,
            "models_loaded": len(models),
            "db_healthy": db_healthy,
            "router_healthy": router_healthy,
        }, status=200 if healthy else 503)
    
    app = web.Application()
    app.router.add_get("/healthz", health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8081)
    await site.start()
    logger.info("health_server_started", port=8081)
    return runner


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
                items = sorted(template_counts.items(), key=lambda x: (-x[1], x[0]))
                max_count = max(items, key=lambda x: x[1])[1]
                for tpl, count in items:
                    bar = "█" * int((count / max_count) * 20) if max_count > 0 else ""
                    print(f"     {tpl:<20} {count:>3} {bar}")


# ── Refill ───────────────────────────────────────────────────────────────

def refill_database(max_per_category: int = 5):
    """Fill data.csv with products from the database."""
    print("\n🔄 Refilling data.csv from product database...")
    
    df = get_products_df().fillna("")
    pending = df[df["Status"].astype(str).str.strip().str.lower().isin(["", "pending"])]
    
    if pending.empty:
        print("  ⚠️  No pending products in database")
        return
    
    # Group by category and take N per category
    refill_rows = []
    for cat in get_all_categories():
        cat_products = pending[pending["Category"] == cat].head(max_per_category)
        refill_rows.append(cat_products)
    
    if refill_rows:
        new_data = pd.concat(refill_rows, ignore_index=True)
        print(f"  📥 Adding {len(new_data)} products to data.csv")
        
        # Append to CSV
        if os.path.exists(CSV_FILE):
            existing = pd.read_csv(CSV_FILE).fillna("")
            combined = pd.concat([existing, new_data], ignore_index=True)
            combined = combined.drop_duplicates(subset=["Product Name", "Category"], keep="first")
        else:
            combined = new_data
        
        combined.to_csv(CSV_FILE, index=False)
        print(f"  ✅ data.csv updated ({len(combined)} total rows)")
    else:
        print("  ⚠️  No products to add")


def refill_trending():
    """Fetch trending ASINs and add to database."""
    print("\n📈 Fetching trending products...")
    try:
        trending = get_trending_asins()
        if trending:
            enrich_with_trending(trending)
            print(f"  ✅ Added {len(trending)} trending products to database")
        else:
            print("  ⚠️  No trending products found")
    except Exception as e:
        print(f"  ❌ Trending fetch failed: {e}")


# ── Automation Core ──────────────────────────────────────────────────────

def run_automation(max_pins: int = PINS_PER_RUN, category: str = None):
    """Main automation loop — post pins from data.csv."""
    import asyncio
    from browser import AsyncBrowser, safe_close_async
    
    print(f"\n{'='*55}")
    print(f"   🚀  STARTING AUTOMATION (max {max_pins} pins)")
    print(f"{'='*55}")
    
    if not os.path.exists(CSV_FILE):
        print(f"  ❌ {CSV_FILE} not found. Run 'refill' first.")
        return
    
    df = pd.read_csv(CSV_FILE).fillna("")
    
    # Filter by category if specified
    if category:
        df = df[df["Category"] == category]
    
    # Get pending (not pinned)
    pending = df[df["Status"].astype(str).str.strip().str.lower().isin(["", "pending"])]
    pending = pending.head(max_pins)
    
    if pending.empty:
        print("  ✅ No pending pins to post")
        return
    
    print(f"  📋 Found {len(pending)} pending pins to process")
    
    async def _run():
        async with AsyncBrowser(headless=True) as browser:
            for idx, row in pending.iterrows():
                try:
                    product_name = row.get("Product Name", "Unknown")
                    print(f"\n  📌 [{idx+1}/{len(pending)}] {product_name}")
                    
                    # Generate pin
                    pin_path = generate_pin(row)
                    if not pin_path:
                        print(f"     ⚠️  Failed to generate pin")
                        continue
                    
                    # Post to Pinterest
                    result = await post_pin(browser, pin_path, row)
                    if result:
                        print(f"     ✅ Posted successfully")
                        # Update status
                        df.loc[idx, "Status"] = "pinned"
                        df.loc[idx, "Pinned_Date"] = datetime.now().isoformat()
                    else:
                        print(f"     ❌ Failed to post")
                        df.loc[idx, "Status"] = "failed"
                        
                except Exception as e:
                    print(f"     ❌ Error: {e}")
                    df.loc[idx, "Status"] = "error"
                
                # Rate limit
                if idx < len(pending) - 1:
                    await asyncio.sleep(SLEEP_BETWEEN_PINS)
            
            # Save updated CSV
            df.to_csv(CSV_FILE, index=False)
            print(f"\n  💾 Updated {CSV_FILE}")
    
    asyncio.run(_run())


# ── Schedule ──────────────────────────────────────────────────────────────

def run_schedule():
    """Run automation at optimal times throughout the day."""
    print("\n⏰ Schedule mode not fully implemented yet. Use 'run' for now.")
    run_automation()


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Pinterest Affiliate Bot")
    parser.add_argument(
        "command", 
        nargs="?", 
        default="run", 
        choices=["run", "refill", "stats", "schedule", "video", "crosspost", "bio", "seo", "trending", "health"],
        help="Command to run"
    )
    parser.add_argument("--count", type=int, help="Number of pins/products")
    parser.add_argument("--category", type=str, help="Filter by category")
    parser.add_argument("--platforms", type=str, default="instagram", help="Crosspost platforms (comma-separated)")
    parser.add_argument("--trending", action="store_true", help="Fetch trending before run")
    parser.add_argument("--health-only", action="store_true", help="Only run health server")
    args = parser.parse_args()
    
    # Handle health-only mode
    if args.health_only or args.command == "health":
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        runner = loop.run_until_complete(start_health_server())
        try:
            loop.run_forever()
        finally:
            loop.run_until_complete(runner.cleanup())
        return
    
    if args.command == "refill":
        refill_database(max_per_category=args.count or 5)
    elif args.command == "stats":
        show_stats()
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
        refill_trending()
        run_automation(max_pins=args.count or PINS_PER_RUN, category=args.category)
    else:  # run (default)
        if args.trending:
            refill_trending()
        run_automation(max_pins=args.count or PINS_PER_RUN, category=args.category)


if __name__ == "__main__":
    main()