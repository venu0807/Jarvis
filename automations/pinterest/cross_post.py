"""
Multi-Platform Orchestrator — Glue that ties it all together.

Pipeline:
  data.csv (pending) 
    → generate_videos (one MP4 per product)
    → post to TikTok (browser automation)
    → post to Instagram Reels (browser automation)  
    → update bio_page (auto-regenerate HTML)
    → mark Status="Pinned" in CSV (with platform tags)

Use cases:
- "Cross-post everything I posted to Pinterest to TikTok + Reels"
- "Add TikTok/Reels posting to the scheduled run"
- "Batch cross-post N items"

This is the missing layer between Pinterest (which we already have)
and the new video-first platforms.
"""

import os
import sys
import time
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

from generator import generate_pin
from video_generator import generate_video, generate_caption
from bio_page import generate_bio_page


CSV_FILE = "data.csv"
VIDEO_DIR = "output/videos"
POST_LOG = "post_log.json"

DAILY_LIMITS = {
    "pinterest": 20,
}


# ── Helpers ───────────────────────────────────────────────────────────────


def _load_post_log() -> dict:
    if os.path.exists(POST_LOG):
        try:
            with open(POST_LOG) as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def _save_post_log(log: dict):
    with open(POST_LOG, "w") as f:
        json.dump(log, f, indent=2)


def _today_key() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _count_today_posts(platform: str) -> int:
    log = _load_post_log()
    today = _today_key()
    return log.get(today, {}).get(platform, 0)


def _record_post(platform: str, product_name: str):
    log = _load_post_log()
    today = _today_key()
    if today not in log:
        log[today] = {}
    log[today][platform] = log[today].get(platform, 0) + 1
    log[today]["history"] = log[today].get("history", [])
    log[today]["history"].append(
        {
            "platform": platform,
            "product": product_name[:100],
            "ts": datetime.now().isoformat(),
        }
    )
    _save_post_log(log)


def _get_pending(max_count: int, category: Optional[str] = None) -> pd.DataFrame:
    """Get pending products from CSV."""
    if not os.path.exists(CSV_FILE):
        return pd.DataFrame()
    df = pd.read_csv(CSV_FILE, dtype={"Status": str})
    df = df.fillna("")
    pending = df[
        df["Status"].astype(str).str.strip().str.lower().isin(["", "pending"])
    ].copy()
    if category:
        pending = pending[pending["Category"].astype(str).str.lower() == category.lower()]
    return pending.head(max_count)


def _mark_pinned(name: str, platform_tag: str = "TT+PI"):
    """Mark product as Pinned in CSV."""
    if not os.path.exists(CSV_FILE):
        return
    df = pd.read_csv(CSV_FILE, dtype={"Status": str})
    df = df.fillna("")
    # Match by product name (case-insensitive)
    mask = (
        df["Product Name"]
        .astype(str)
        .str.strip()
        .str.lower()
        .eq(name.strip().lower())
    )
    if mask.any():
        df.loc[mask, "Status"] = f"Pinned-{platform_tag}"
        df.to_csv(CSV_FILE, index=False)
        print(f"  📝 Marked '{name[:50]}' as Pinned-{platform_tag}")


# ── Pipeline ─────────────────────────────────────────────────────────────


def _build_video_for_row(row: pd.Series) -> Optional[str]:
    """Generate a video for a CSV row. Returns path or None."""
    name = str(row.get("Product Name", "")).strip()
    if not name:
        return None
    # Prefer SEO Title for the overlay text (better CTR, keyword-rich)
    seo_title = str(row.get("SEO Title", "")).strip()
    display_name = seo_title if seo_title else name
    price = str(row.get("Price", "")).strip()
    tags = str(row.get("Tags", "")).strip()
    image_url = str(row.get("Image URL", "")).strip()
    pin_type = str(row.get("Pin Type", "product")).strip()
    pin_template = str(row.get("Pin_Template", "")).strip()

    # First, generate the pin image (consistent visual brand across Pinterest + video)
    pin_filename = f"pin_xp_{abs(hash(display_name))}.jpg"
    try:
        pin_path = generate_pin(
            product_name=display_name,
            image_url=image_url,
            output_filename=pin_filename,
            price=price,
            tags=tags,
            is_content=(pin_type.lower() == "content"),
            template=pin_template or None,  # None == auto-pick
        )
    except Exception as e:
        print(f"  ⚠️  Image generate failed: {e}")
        # Fallback: use cached pin if available
        pin_path = None

    if not pin_path or not os.path.exists(pin_path):
        # Try existing pin
        for f in os.listdir("output"):
            if f.endswith(".jpg") and not f.startswith("_"):
                pin_path = os.path.join("output", f)
                break

    if not pin_path or not os.path.exists(pin_path):
        print(f"  ⚠️  No image for {name[:40]}, skipping video")
        return None

    # Convert to video — uses SEO title for the hook + price overlay
    vid_filename = os.path.join(VIDEO_DIR, f"{os.path.splitext(os.path.basename(pin_path))[0]}.mp4")
    try:
        out = generate_video(
            pin_image_path=pin_path,
            product_name=display_name,
            output_filename=vid_filename,
            price=price,
            tags=tags,
            duration=8,
        )
        return out
    except Exception as e:
        print(f"  ⚠️  Video generate failed: {e}")
        return None


def _post_to_platforms(
    row: pd.Series,
    video_path: str,
    affiliate_link: str,
    platforms: List[str],
    bio_link: str,
):
    """Post a single video to all requested platforms."""
    name = str(row.get("Product Name", "")).strip()
    price = str(row.get("Price", "")).strip()
    tags = str(row.get("Tags", "")).strip()

    posted_to = []
    failed = []

    # Build caption for Instagram only — uses SEO Title for richer hook
    seo_title = str(row.get("SEO Title", "")).strip()
    display_name = seo_title if seo_title else name
    captions = {
        platform: generate_caption(
            product_name=display_name,
            affiliate_url=affiliate_link,
            tags=tags,
            platform=platform,
            price=price,
        )
        for platform in platforms
    }

    if "instagram" in platforms:
        # Instagram support removed — Pinterest-only bot
        pass

    # Update CSV
    platform_tag = "+".join([p.upper()[:2] for p in posted_to]) or "FAILED"
    if posted_to:
        _mark_pinned(name, platform_tag)

    return posted_to, failed


# ── Public API ────────────────────────────────────────────────────────────


def cross_post(
    count: int = 3,
    platforms: List[str] = ("tiktok", "pinterest"),
    category: Optional[str] = None,
    refresh_bio: bool = True,
    headless: bool = False,
):
    """
    Cross-post products from data.csv to multiple platforms.

    Pipeline:
    1. Pick pending products (defaults to 3)
    2. Generate MP4 videos from pin images
    3. Post to each platform
    4. Regenerate bio link page
    5. Update CSV

    Args:
        count: How many products to process
        platforms: List of ("tiktok", "pinterest")
        category: Optional category filter
        refresh_bio: Whether to regenerate the bio link page
        headless: Run browser automation headless (True) or visible (False)
    """
    print("\n" + "=" * 60)
    print(f"   🌐  CROSS-POST ORCHESTRATOR")
    print(f"   Platforms: {', '.join(platforms)}")
    print(f"   Count: {count} | Category: {category or 'all'}")
    print("=" * 60)

    pending = _get_pending(count, category)
    if pending.empty:
        print("\n  ⚠️  No pending products found. Run 'python main.py refill' first.")
        return

    print(f"\n  📋 Found {len(pending)} pending products")

    bio_link = os.getenv(
        "BIO_LINK_URL", "https://yourname.github.io/bio/"
    )

    results = {"failed": 0}

    for idx, (_, row) in enumerate(pending.iterrows(), 1):
        name = str(row.get("Product Name", "")).strip()
        link = str(row.get("Affiliate Link", "")).strip()

        print(f"\n{'─' * 60}")
        print(f"  [{idx}/{len(pending)}] {name[:60]}")
        print(f"{'─' * 60}")

        video = _build_video_for_row(row)
        if not video:
            print(f"  ⚠️  Skipping — no video generated")
            results["failed"] += 1
            continue

        posted, failed = _post_to_platforms(
            row=row,
            video_path=video,
            affiliate_link=link,
            platforms=list(platforms),
            bio_link=bio_link,
        )

        if "instagram" in posted:
            # Instagram support removed
            pass
        if posted == [] and failed:
            results["failed"] += 1

        # Delay between products to avoid spam flags
        if idx < len(pending):
            wait = 30
            print(f"  ⏳ Cooldown {wait}s (next product)...")
            time.sleep(wait)

    # Refresh bio page
    if refresh_bio:
        print(f"\n{'─' * 60}")
        print("  🔄 Regenerating bio link page...")
        try:
            generate_bio_page(csv_path=CSV_FILE, max_products=8)
            print(f"     → Bio page shows today's top picks")
            print(f"     → Upload to: github.io, netlify.com, or surge.sh")
        except Exception as e:
            print(f"  ⚠️  Bio page generation failed: {e}")

    # Final summary
    print(f"\n{'=' * 60}")
    print(f"   📊 CROSS-POST COMPLETE")
    print(f"{'=' * 60}")
    print(f"   ├── TikTok:   {results.get('tt', 0)} posted")
    print(f"   ├── Failures:   {results['failed']}")
    print(f"   └── Daily Limits: TT {DAILY_LIMITS['tiktok']}/day")
    print(f"\n   💰 Link in bio: {bio_link}")
    print(f"   {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)


# ── CLI mode ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cross-post orchestrator")
    parser.add_argument("--count", type=int, default=3)
    parser.add_argument("--platforms", type=str, default="instagram",
                        help="CSV: pinterest (default) or pinterest,tiktok")
    parser.add_argument("--category", type=str, default=None)
    args = parser.parse_args()

    platforms = [p.strip().lower() for p in args.platforms.split(",") if p.strip()]
    cross_post(
        count=args.count,
        platforms=platforms,
        category=args.category,
    )
