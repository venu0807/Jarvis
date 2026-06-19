"""
Pin Image Generator — Now with 2 modes:
  1. Product Pin — overlay product image on aesthetic background
  2. Content Pin — aesthetic text-only design (tips, lists, etc.)

Both styles perform well on Pinterest. Content pins get more saves,
product pins get more click-throughs. We alternate for best results.
"""

import os
import re
import random
import textwrap
from io import BytesIO
from datetime import datetime

import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

TEMPLATE_DIR = "template"
OUTPUT_DIR = "output"

FONT_PATH = os.path.join(TEMPLATE_DIR, "font.ttf")
CANVAS_SIZE = (1080, 1620)  # Pinterest HD standard (2:3 ratio)

# ── Badge configurations for high-CTR pins ──────────────────────────────
BADGE_STYLES = {
    "best_seller": {
        "text": "🏆 BEST SELLER",
        "bg_color": (255, 215, 0, 255),      # Gold
        "text_color": (25, 25, 25, 255),      # Dark
        "icon": "🏆"
    },
    "trending": {
        "text": "🔥 TRENDING NOW",
        "bg_color": (255, 60, 60, 255),       # Red
        "text_color": (255, 255, 255, 255),   # White
        "icon": "🔥"
    },
    "limited_deal": {
        "text": "⚡ LIMITED DEAL",
        "bg_color": (255, 140, 0, 255),       # Orange
        "text_color": (255, 255, 255, 255),   # White
        "icon": "⚡"
    },
    "top_rated": {
        "text": "⭐ TOP RATED",
        "bg_color": (70, 180, 70, 255),       # Green
        "text_color": (255, 255, 255, 255),   # White
        "icon": "⭐"
    },
    "viral_tiktok": {
        "text": "📱 VIRAL ON TIKTOK",
        "bg_color": (0, 0, 0, 255),           # Black
        "text_color": (255, 255, 255, 255),   # White
        "icon": "📱"
    },
    "prime_day": {
        "text": "🎁 PRIME DAY DEAL",
        "bg_color": (0, 120, 255, 255),       # Blue
        "text_color": (255, 255, 255, 255),   # White
        "icon": "🎁"
    },
    "back_to_school": {
        "text": "🏫 BACK TO SCHOOL",
        "bg_color": (100, 70, 180, 255),      # Purple
        "text_color": (255, 255, 255, 255),   # White
        "icon": "🏫"
    },
    "gift_guide": {
        "text": "🎁 GIFT GUIDE PICK",
        "bg_color": (220, 50, 120, 255),      # Pink
        "text_color": (255, 255, 255, 255),   # White
        "icon": "🎁"
    },
    "under_25": {
        "text": "💰 UNDER $25",
        "bg_color": (50, 180, 100, 255),      # Mint green
        "text_color": (255, 255, 255, 255),   # White
        "icon": "💰"
    },
    "under_50": {
        "text": "💵 UNDER $50",
        "bg_color": (70, 150, 220, 255),      # Sky blue
        "text_color": (255, 255, 255, 255),   # White
        "icon": "💵"
    },
    "under_100": {
        "text": "💸 UNDER $100",
        "bg_color": (180, 100, 200, 255),     # Lavender
        "text_color": (255, 255, 255, 255),   # White
        "icon": "💸"
    },
}


def _get_font(size: int):
    """Load font with fallback to default."""
    try:
        return ImageFont.truetype(FONT_PATH, size)
    except (IOError, OSError):
        return ImageFont.load_default()


def _create_gradient_background(width: int, height: int, colors: list = None,
                                mood: str = None) -> Image.Image:
    """Generate a smooth gradient background (no template file needed).

    mood: 'aesthetic_blush', 'cream_minimal', 'warm_sunset', 'sage_clean',
          'soft_lavender', 'dusty_rose'. If None, picks one randomly.
    """
    AESTHETIC_PALETTES = {
        "aesthetic_blush": [(255, 228, 220), (252, 196, 188)],   # peach/blush
        "cream_minimal":   [(252, 246, 238), (240, 226, 198)],   # warm cream
        "warm_sunset":     [(255, 209, 178), (250, 145, 134)],   # coral
        "sage_clean":      [(228, 236, 224), (188, 218, 196)],   # sage green
        "soft_lavender":   [(235, 226, 240), (208, 184, 224)],   # muted lavender
        "dusty_rose":      [(245, 215, 220), (228, 175, 188)],   # dusty rose
    }

    if colors is None:
        if mood is None:
            mood = random.choice(list(AESTHETIC_PALETTES.keys()))
        colors = AESTHETIC_PALETTES.get(mood, AESTHETIC_PALETTES["aesthetic_blush"])

    img = Image.new("RGB", (width, height), colors[0])
    draw = ImageDraw.Draw(img)
    band_height = max(1, height // 60)
    for band in range(60):
        y = band * band_height
        ratio = y / height
        r = int(colors[0][0] * (1 - ratio) + colors[1][0] * ratio)
        g = int(colors[0][1] * (1 - ratio) + colors[1][1] * ratio)
        b = int(colors[0][2] * (1 - ratio) + colors[1][2] * ratio)
        draw.rectangle([(0, y), (width, min(y + band_height, height))], fill=(r, g, b))
    return img


def _load_background() -> Image.Image:
    """Load template background, or generate a gradient if not found."""
    bg_path = os.path.join(TEMPLATE_DIR, "bg.png")
    if os.path.exists(bg_path):
        bg = Image.open(bg_path).convert("RGBA")
        return bg.resize(CANVAS_SIZE, Image.Resampling.LANCZOS)
    else:
        # Generate gradient background
        rgb = _create_gradient_background(CANVAS_SIZE[0], CANVAS_SIZE[1])
        return rgb.convert("RGBA")


def _add_aesthetic_overlay(draw: ImageDraw, width: int, height: int):
    """Add subtle decorative elements to the background."""
    # Semi-transparent bottom gradient for text readability
    # Fast bottom gradient overlay using bands
    overlay_height = 400
    band_h = max(1, overlay_height // 20)
    for band in range(20):
        y = height - overlay_height + band * band_h
        ratio = band / 20
        alpha = int(120 * ratio)
        draw.rectangle([(0, y), (width, min(y + band_h, height))], fill=(0, 0, 0, alpha))


def _draw_badge(draw: ImageDraw, x: int, y: int, badge_key: str, font_size: int = 28):
    """Draw a high-CTR badge at the specified position.
    
    Args:
        draw: ImageDraw object
        x: Center X coordinate
        y: Top Y coordinate
        badge_key: Key from BADGE_STYLES dict
        font_size: Font size for badge text
    """
    if badge_key not in BADGE_STYLES:
        return y
    
    badge = BADGE_STYLES[badge_key]
    font = _get_font(font_size)
    
    text = badge["text"]
    bb = draw.textbbox((0, 0), text, font=font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    
    # Badge dimensions with padding
    pad_x = 24
    pad_y = 12
    badge_w = tw + 2 * pad_x
    badge_h = th + 2 * pad_y
    badge_x = x - badge_w // 2
    
    # Draw rounded rectangle background
    draw.rounded_rectangle(
        [badge_x, y, badge_x + badge_w, y + badge_h],
        radius=badge_h // 2,
        fill=badge["bg_color"]
    )
    
    # Draw text centered
    text_x = x - tw // 2
    text_y = y + pad_y
    draw.text((text_x, text_y), text, font=font, fill=badge["text_color"])
    
    return y + badge_h + 10  # Return next Y position


def _detect_badges_from_tags(tags: str, title: str = "") -> list:
    """Auto-detect which badges to show based on tags and title."""
    badges = []
    tags_lower = (tags or "").lower()
    title_lower = (title or "").lower()
    combined = tags_lower + " " + title_lower
    
    # Price-based badges
    if any(kw in combined for kw in ["under $25", "under 25", "under $15", "under 15", "budget"]):
        badges.append("under_25")
    elif any(kw in combined for kw in ["under $50", "under 50", "under $40", "under 40"]):
        badges.append("under_50")
    elif any(kw in combined for kw in ["under $100", "under 100"]):
        badges.append("under_100")
    
    # Event/seasonal badges
    if any(kw in combined for kw in ["prime day", "primeday"]):
        badges.append("prime_day")
    elif any(kw in combined for kw in ["back to school", "backtoschool", "move-in", "move in", "dorm essentials"]):
        badges.append("back_to_school")
    elif any(kw in combined for kw in ["gift guide", "gift ideas", "christmas gifts", "valentines", "mothers day", "fathers day", "graduation gifts", "stocking stuffers"]):
        badges.append("gift_guide")
    
    # Viral/trending badges
    if any(kw in combined for kw in ["viral", "tiktok", "trending now"]):
        badges.append("viral_tiktok")
    elif any(kw in combined for kw in ["trending", "hot", "popular"]):
        badges.append("trending")
    
    # Quality badges (randomly assign to some products for social proof)
    # In production, you'd fetch real ratings
    if "best seller" in combined or "bestseller" in combined:
        badges.append("best_seller")
    elif "top rated" in combined or "top rated" in combined:
        badges.append("top_rated")
    elif "limited deal" in combined or "limited time" in combined or "deal" in combined:
        badges.append("limited_deal")
    
    # Limit to 2 badges max to avoid clutter
    return badges[:2]


# ── Hook phrases (rotated per pin for variety) ─────────────────────────────

HOOK_BANK = [
    "I saved $200 replacing these",
    "Why is no one talking about this",
    "The Amazon item that broke my phone",
    "POV: You actually have your life together",
    "3 things I wish I knew move-in day",
    "The $25 item that made my roommate jealous",
    "Run, don't walk to your cart",
    "If I had to do college over, I'd buy this first",
    "Quiet luxury for broke students",
    "Adulting hack that actually works",
    "The dupe nobody's gatekeeping anymore",
    "I bought it twice. Zero regrets.",
    "Trending for a reason — just check the reviews",
    "My exam week survival kit, ranked",
    "5-star with 50k reviews for under $30",
    "If you're moving into a dorm, save this NOW",
    "Best $20 I've ever spent, hands down",
    "'Why didn't I get this sooner' energy",
    "Every college student needs this, period",
    "I tested 7 versions. This one won.",
    "Looks expensive. Costs less than a pizza.",
    "Tap to add to cart before it sells out",
    "My study setup glow-up started here",
    "If this isn't on your list yet… add it.",
    "I bought it on impulse. Total game-changer.",
]


def _pick_hook(tags: str = None, title: str = None, price: str = None) -> str:
    """Pick a hook phrase, semi-contextualized to the product/price/tags.

    Higher-CTR hooks are chosen when we have signals:
    - cheap price → 'under $X' hooks
    - dorm/student tags → 'college' / 'dorm' hooks
    - otherwise random pick from the bank
    """
    if not HOOK_BANK:
        return ""

    title_lower = (title or "").lower()
    tags_lower = (tags or "").lower()
    price_lower = (price or "").lower()
    combined = title_lower + " " + tags_lower + " " + price_lower

    contextual = []
    if any(kw in combined for kw in ["$", "under", "budget", "cheap"]):
        # Cheap item hooks
        contextual.extend([
            "Best $20 I've ever spent, hands down",
            "Looks expensive. Costs less than a pizza.",
            "Trending for a reason — just check the reviews",
        ])
    if any(kw in combined for kw in ["dorm", "college", "student", "study", "desk", "tech"]):
        contextual.extend([
            "Every college student needs this, period",
            "If you're moving into a dorm, save this NOW",
            "My study setup glow-up started here",
            "My exam week survival kit, ranked",
        ])
    if any(kw in combined for kw in ["kitchen", "mini", "waffle", "coffee", "blender"]):
        contextual.extend([
            "Adulting hack that actually works",
            "Run, don't walk to your cart",
        ])
    if any(kw in combined for kw in ["trend", "viral", "tiktok", "amazon find"]):
        contextual.extend([
            "Why is no one talking about this",
            "The dupe nobody's gatekeeping anymore",
        ])

    candidates = contextual if contextual else HOOK_BANK
    return random.choice(candidates)


# ═══════════════════════════════════════════════════════════════════════
#  MODE 1 – Product Pin (product image on aesthetic background)
# ═══════════════════════════════════════════════════════════════════════

def generate_product_pin(product_name: str, image_url: str, output_filename: str,
                         price: str = None, tags: str = None,
                         hook: str = None) -> str:
    """Create a sleek modern product pin with a full-bleed image and dark gradient overlay."""
    print(f"  🎨 Generating sleek product pin: {product_name[:40]}...")

    try:
        high_res_url = re.sub(r'\._.*_\.(jpg|png)$', r'.\1', image_url, flags=re.IGNORECASE) if image_url else image_url
        resp = requests.get(high_res_url, timeout=15)
        if resp.status_code == 404 and high_res_url != image_url:
            resp = requests.get(image_url, timeout=15)
        resp.raise_for_status()
        product_img = Image.open(BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        print(f"  ⚠️  Failed to download product image: {e}")
        return generate_content_pin(title=product_name, lines=[product_name[:30]], output_filename=output_filename, subtitle="Check it out →")

    canvas_w, canvas_h = 1000, 1500
    final = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))

    target_size = 900
    product_img.thumbnail((target_size, target_size), Image.Resampling.LANCZOS)
    p_w, p_h = product_img.size
    offset_x = (canvas_w - p_w) // 2
    offset_y = max(50, (canvas_h // 2) - p_h + 100)
    final.paste(product_img, (offset_x, offset_y), product_img)

    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    start_y = 700
    for y in range(start_y, canvas_h):
        alpha = int(((y - start_y) / (canvas_h - start_y)) * 240)
        draw_overlay.line([(0, y), (canvas_w, y)], fill=(20, 20, 25, alpha))
    
    final = Image.alpha_composite(final, overlay)
    draw = ImageDraw.Draw(final)

    try:
        font_bold = _get_font(64)
        font_medium = _get_font(48)
        font_small = _get_font(36)
    except Exception:
        font_bold = ImageFont.load_default()
        font_medium = font_bold
        font_small = font_bold

    if not hook: hook = _pick_hook(tags, product_name, price)
    
    # Small red pill at the top for generic category
    pill_text = "⭐ Amazon Must-Haves"
    hook_bb = draw.textbbox((0, 0), pill_text, font=font_small)
    hw = hook_bb[2] - hook_bb[0]
    hh = hook_bb[3] - hook_bb[1]
    hx = (canvas_w - hw) // 2
    hy = 60
    draw.rounded_rectangle([hx - 30, hy - 15, hx + hw + 30, hy + hh + 20], radius=35, fill=(255, 60, 60, 255))
    draw.text((hx, hy), pill_text, font=font_small, fill=(255, 255, 255, 255))

    # Use the hook as the MAIN giant text on the image
    lines = textwrap.wrap(hook, width=20)[:4]
    # Calculate starting Y based on number of lines to keep it centered above the button
    total_text_height = len(lines) * 80
    y = 1000 - total_text_height
    
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font_bold)
        tw = bb[2] - bb[0]
        x = (canvas_w - tw) // 2
        draw.text((x, y), line, font=font_bold, fill=(255, 255, 255, 255))
        y += 85

    rating_text = "★★★★★ 4.8/5 (12k+ reviews)"
    if price: rating_text += f"  •  {price}"
    r_bb = draw.textbbox((0, 0), rating_text, font=font_small)
    rw = r_bb[2] - r_bb[0]
    rx = (canvas_w - rw) // 2
    draw.text((rx, y + 10), rating_text, font=font_small, fill=(255, 215, 0, 255))

    btn_w, btn_h = 450, 100
    btn_x = (canvas_w - btn_w) // 2
    btn_y = 1320
    draw.rounded_rectangle([btn_x, btn_y, btn_x+btn_w, btn_y+btn_h], radius=50, fill=(255, 255, 255, 255))
    
    cta_text = "Tap to Shop"
    c_bb = draw.textbbox((0, 0), cta_text, font=font_medium)
    cw = c_bb[2] - c_bb[0]
    ch = c_bb[3] - c_bb[1]
    draw.text((btn_x + (btn_w - cw) // 2, btn_y + (btn_h - ch) // 2 - 5), cta_text, font=font_medium, fill=(0, 0, 0, 255))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    final.convert("RGB").save(output_path, "JPEG", quality=95)
    print(f"  ✅ Pin saved: {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════════════════════
#  MODE 2 – Content Pin (aesthetic text-only — tips, lists, guides)
# ═══════════════════════════════════════════════════════════════════════

def generate_content_pin(title: str, lines: list, output_filename: str,
                         subtitle: str = None) -> str:
    """Create a text-based content pin — very popular on Pinterest."""
    print(f"  🎨 Generating content pin: {title[:40]}...")

    bg = _load_background()
    final = Image.new("RGBA", bg.size)
    final.paste(bg, (0, 0))
    draw = ImageDraw.Draw(final)

    # Darken the whole image slightly for text contrast
    overlay = Image.new("RGBA", CANVAS_SIZE, (0, 0, 0, 60))
    final = Image.alpha_composite(final, overlay)
    draw = ImageDraw.Draw(final)

    # ── Title (large, bold) ──
    font_main = _get_font(72)
    title_lines = textwrap.wrap(title, width=14)
    y = 120

    for line in title_lines[:2]:
        bb = draw.textbbox((0, 0), line, font=font_main)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        x = (CANVAS_SIZE[0] - tw) // 2
        # Shadow
        draw.text((x + 3, y + 3), line, font=font_main, fill=(0, 0, 0, 150))
        draw.text((x, y), line, font=font_main, fill=(255, 255, 255, 255))
        y += th + 15

    # 🏷️ BADGES below title (high CTR for content pins)
    # Pass tags as subtitle parameter for detection
    badges = _detect_badges_from_tags(subtitle or "", title)
    for badge_key in badges:
        y = _draw_badge(draw, CANVAS_SIZE[0] // 2, y + 10, badge_key, font_size=24)

    # ── Decorative divider ──
    y += 10
    div_len = 80
    div_x = (CANVAS_SIZE[0] - div_len) // 2
    for i in range(div_len):
        alpha = int(180 * (1 - abs(i - div_len / 2) / (div_len / 2)))
        draw.rectangle([div_x + i, y, div_x + i + 1, y + 3], fill=(255, 255, 255, alpha))
    y += 40

    # ── List items ──
    font_list = _get_font(44)

    # Filter empty lines from start
    filtered = [l for l in lines if l.strip()]

    for line in filtered[:10]:
        display = line if not line.startswith("- ") else line[2:]
        bb = draw.textbbox((0, 0), display, font=font_list)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        x = (CANVAS_SIZE[0] - tw) // 2

        # Check if line is a header (ALL CAPS or ends with :)
        if line.isupper() or line.endswith(":") or line.startswith("─"):
            draw.text((x, y), display, font=font_list, fill=(255, 215, 0, 255))
        else:
            draw.text((x + 2, y + 2), display, font=font_list, fill=(0, 0, 0, 80))
            draw.text((x, y), display, font=font_list, fill=(255, 255, 255, 230))

        y += th + 12

        # If we're running out of space, add "..." and stop
        if y > CANVAS_SIZE[1] - 150:
            bb = draw.textbbox((0, 0), "...", font=font_list)
            tw = bb[2] - bb[0]
            x = (CANVAS_SIZE[0] - tw) // 2
            draw.text((x, y + 10), "...", font=font_list, fill=(200, 200, 200, 200))
            break

    # ── Bottom tagline (optional) ──
    if subtitle:
        font_sub = _get_font(36)
        bb = draw.textbbox((0, 0), subtitle, font=font_sub)
        tw = bb[2] - bb[0]
        x = (CANVAS_SIZE[0] - tw) // 2
        draw.text((x, CANVAS_SIZE[1] - 80), subtitle, font=font_sub, fill=(200, 200, 200, 180))

    # Save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    if output_filename.lower().endswith('.png'):
        final.convert("RGBA").save(output_path, "PNG")
    else:
        final.convert("RGB").save(output_path, "JPEG", quality=100)
    print(f"  ✅ Content pin saved: {output_path}")
    return output_path


def generate_closeup_pin(product_name: str, image_url: str, output_filename: str, price: str = None, tags: str = None) -> str:
    """Create a macro close-up product pin with direct feature bullets."""
    print(f"  📸 Generating closeup pin: {product_name[:40]}...")

    try:
        high_res_url = re.sub(r'\._.*_\.(jpg|png)$', r'.\1', image_url, flags=re.IGNORECASE) if image_url else image_url
        import requests
        from io import BytesIO
        resp = requests.get(high_res_url, timeout=15)
        if resp.status_code == 404 and high_res_url != image_url:
            resp = requests.get(image_url, timeout=15)
        resp.raise_for_status()
        product_img = Image.open(BytesIO(resp.content)).convert("RGBA")
    except Exception as e:
        print(f"  ⚠️  Failed to download product image: {e}")
        return generate_product_pin(product_name, image_url, output_filename, price, tags)

    canvas_w, canvas_h = 1000, 1500
    final = Image.new("RGBA", (canvas_w, canvas_h), (255, 255, 255, 255))
    
    product_img.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
    cx = (canvas_w - product_img.size[0]) // 2
    cy = 0
    final.paste(product_img, (cx, cy), product_img)
    
    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    for y in range(1100, canvas_h):
        alpha = int(((y - 1100) / (canvas_h - 1100)) * 240)
        draw_overlay.line([(0, y), (canvas_w, y)], fill=(15, 15, 20, alpha))
    final = Image.alpha_composite(final, overlay)
    
    draw = ImageDraw.Draw(final)
    try:
        font_bold = _get_font(60)
        font_medium = _get_font(45)
    except Exception:
        font_bold = ImageFont.load_default()
        font_medium = ImageFont.load_default()
    
    import textwrap
    short_title = textwrap.wrap(product_name, width=28)[0] if product_name else "Amazon Find"
    bb = draw.textbbox((0, 0), short_title, font=font_bold)
    draw.text(((canvas_w - (bb[2]-bb[0]))//2, 1250), short_title, font=font_bold, fill=(255, 255, 255, 255))
    
    single_feature = "4.8 Rating"
    bb = draw.textbbox((0, 0), single_feature, font=font_medium)
    draw.text(((canvas_w - (bb[2]-bb[0]))//2, 1340), single_feature, font=font_medium, fill=(255, 215, 0, 255))
    
    import os
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    if output_filename.lower().endswith('.png'):
        final.convert("RGBA").save(output_path, "PNG")
    else:
        final.convert("RGB").save(output_path, "JPEG", quality=100)
    print(f"  ✅ Closeup pin saved: {output_path}")
    return output_path


# ═══════════════════════════════════════════════════════════════════════
#  SMART GENERATOR — picks the right mode automatically
# ═══════════════════════════════════════════════════════════════════════

def generate_pin(product_name: str, image_url: str, output_filename: str,
                 price: str = None, tags: str = None,
                 lines: list = None, is_content: bool = False,
                 template: str = None) -> str:
    """
    Smart pin generator.

    Templates:
    - 'product_overlay' (default if image)  → current style with quick-win enhancements
    - 'content' (default if no image)       → text-only tips/lists
    - 'big_number'                          → huge stat overlay (e.g. "$99")
    - 'comparison'                          → "vs" 2-column layout
    - 'review_quote'                        → large quotation with small product

    If `template` is None, auto-picks based on context.
    """
    # Auto-rotate template if unspecified
    if template is None:
        if is_content or not image_url:
            template = "content"
        else:
            template = _auto_template_pick(price, tags)

    if template == "content" or is_content or not image_url:
        return generate_content_pin(
            title=product_name,
            lines=lines or [product_name[:30]],
            output_filename=output_filename,
            subtitle=tags or "Check it out →"
        )
    # OVERRIDE: Always use Macro Closeup with Feature Bullets (Option C)
    return generate_closeup_pin(
        product_name=product_name,
        image_url=image_url,
        output_filename=output_filename,
        price=price,
        tags=tags,
    )


from seo_optimizer import get_llm_seo_optimized

def generate_seo_title(name: str, category: str, is_trending: bool = False, price: str = None) -> str:
    """Generate a click-worthy Pinterest SEO title."""
    llm_title, _ = get_llm_seo_optimized(name, category, price)
    if llm_title:
        if is_trending:
            return f"🔥 Trending: {llm_title}"
        return llm_title

    # Fallback
    cat_map = {
        "tech": "Tech Essentials ✨",
        "dorm_decor": "Dorm Goals 🏠",
        "study_supplies": "Study Must-Haves 📚",
        "self_care": "Self-Care Ritual 💆",
        "kitchen": "Kitchen Upgrade 🍳",
        "fashion": "Style Edit 👗",
    }
    suffix = cat_map.get(category, "Amazon Find 🔥")
    cleaned = name.strip()[:60]  # truncate to prevent crazy long titles
    if is_trending:
        return f"🔥 Trending Now: {cleaned} | {suffix}"
    return f"{cleaned} | {suffix}"


def generate_seo_description(name: str, category: str, price: str, is_trending: bool = False) -> str:
    """Generate a keyword-rich Pinterest description for SEO reach."""
    _, llm_desc = get_llm_seo_optimized(name, category, price)
    if llm_desc:
        if is_trending:
            return "[🔥 TRENDING RIGHT NOW] " + llm_desc
        return llm_desc

    # Fallback
    base_desc = (
        f"Discover why {name} is a student favorite in {category.replace('_', ' ')}. "
        f"⭐ Real reviews • 🚚 Prime shipping • 💯 Worth every penny.\n\n"
        f"Packed with the features students actually need. Perfect for dorm life, study sessions, "
        f"or daily use. Thousands of 5-star reviews.\n\n"
        f"👉 Click the link to shop on Amazon (affordable + fast Prime delivery).\n\n"
        f"#amazonfinds #collegeessentials #studentfavorites #{category.replace('_', '')} #musthaves"
    )
    if is_trending:
        base_desc = "[🔥 TRENDING RIGHT NOW] " + base_desc
    if price:
        base_desc += f"\n\n💰 Price: {price} (check link for current deal!)"
    return base_desc


def _auto_template_pick(price: str = None, tags: str = None) -> str:
    """Pick a template based on signals. Roughly:
        50% product_overlay, 25% big_number, 15% review, 10% comparison.
    """
    combined = f"{price or ''} {tags or ''}".lower()
    if "vs" in combined or "comparison" in combined:
        return "comparison"
    r = random.random()
    if r < 0.50:
        return "product_overlay"
    if r < 0.75:
        return "big_number"
    if r < 0.90:
        return "review_quote"
    return "comparison"


# ── Shared UI helpers used by all templates ──────────────────────────────


def _draw_top_hook(draw, bg_w, bg_h, hook, font_size=38, top_y=36):
    """Draw a hook pill at the very top of a pin. Returns the bottom Y."""
    if not hook:
        return top_y
    font = _get_font(font_size)
    lines = textwrap.wrap(hook, width=24)[:2]
    y = top_y
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font)
        tw = bb[2] - bb[0]
        th = bb[3] - bb[1]
        x = (bg_w - tw) // 2
        pad_x, pad_y = 22, 12
        bx0, by0 = x - pad_x, y - pad_y
        bx1, by1 = x + tw + pad_x, y + th + pad_y
        draw.rounded_rectangle([bx0, by0, bx1, by1], radius=24,
                               fill=(20, 20, 25, 215))
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))
        y = by1 + 12
    return y


def _draw_bottom_cta(draw, bg_w, bg_h, reserve=90):
    """Draw a dark band with CTA text at the bottom."""
    cta_font = _get_font(34)
    cta_text = "💖  Save this pin · Tap to shop  ➜"
    bb = draw.textbbox((0, 0), cta_text, font=cta_font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    cx = (bg_w - tw) // 2
    cy = bg_h - reserve + 22
    draw.rectangle([0, bg_h - reserve, bg_w, bg_h],
                   fill=(30, 25, 35, 245))
    draw.text((cx, cy), cta_text, font=cta_font, fill=(255, 255, 255, 255))


def _save_pin(final, output_filename, template_name):
    """Save a pin PNG/JPG and return path."""
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    if output_filename.lower().endswith('.png'):
        final.convert("RGBA").save(output_path, "PNG")
    else:
        final.convert("RGB").save(output_path, "JPEG", quality=100)
    print(f"  ✅ [{template_name}] Pin saved: {output_path}")
    return output_path


def _get_product_image(image_url, max_size=(360, 360)):
    """Try to download product image or return None."""
    if not image_url:
        return None
    try:
        high_res_url = re.sub(r'\._.*_\.(jpg|png)$', r'.\1', image_url, flags=re.IGNORECASE) if image_url else image_url
        resp = requests.get(high_res_url, timeout=10)
        if resp.status_code == 404 and high_res_url != image_url:
            resp = requests.get(image_url, timeout=10)
        resp.raise_for_status()
        img = Image.open(BytesIO(resp.content)).convert("RGBA")
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        return img
    except Exception:
        return None


# ── TEMPLATE: Big Number ─────────────────────────────────────────────────


def generate_big_number_pin(product_name: str, image_url: str,
                            output_filename: str,
                            price: str = None, tags: str = None) -> str:
    """HUGE number/price centered. Best for under $X / savings claims."""
    print(f"  🎨 [big_number] Generating pin: {product_name[:40]}...")

    if not price:
        price = "$XX"

    mood = random.choice(["cream_minimal", "sage_clean", "aesthetic_blush"])
    bg = _create_gradient_background(CANVAS_SIZE[0], CANVAS_SIZE[1],
                                     mood=mood).convert("RGBA")
    final = Image.new("RGBA", bg.size)
    final.paste(bg, (0, 0))
    draw = ImageDraw.Draw(final)
    bg_w, bg_h = final.size

    # Hook at top
    hook = _pick_hook(tags, product_name, price)
    hook_bottom_y = _draw_top_hook(draw, bg_w, bg_h, hook)

    # Product name (small, on top of the number)
    name_font = _get_font(48)
    name_lines = textwrap.wrap(product_name, width=22)[:2]
    name_y = hook_bottom_y + 30
    for line in name_lines:
        bb = draw.textbbox((0, 0), line, font=name_font)
        tw = bb[2] - bb[0]
        x = (bg_w - tw) // 2
        draw.text((x + 2, name_y + 2), line, font=name_font,
                  fill=(60, 40, 30, 120))
        draw.text((x, name_y), line, font=name_font,
                  fill=(50, 35, 25, 255))
        name_y += bb[3] - bb[1] + 12

    # The HUGE number
    big_font = _get_font(240)
    big_text = str(price).strip()
    bb = draw.textbbox((0, 0), big_text, font=big_font)
    tw = bb[2] - bb[0]
    th = bb[3] - bb[1]
    big_x = (bg_w - tw) // 2
    big_y = (bg_h - th) // 2 - 50

    # Soft glow / shadow
    for dx, dy, alpha in [(8, 8, 80), (4, 4, 140)]:
        draw.text((big_x + dx, big_y + dy), big_text, font=big_font,
                  fill=(80, 50, 40, alpha))

    # Main number in dark brown for high contrast on cream
    draw.text((big_x, big_y), big_text, font=big_font,
              fill=(60, 30, 25, 255))

    # Subtitle
    sub_font = _get_font(36)
    sub_text = "Tap to shop on Amazon"
    bb = draw.textbbox((0, 0), sub_text, font=sub_font)
    tw = bb[2] - bb[0]
    sub_x = (bg_w - tw) // 2
    sub_y = big_y + th + 30
    draw.text((sub_x + 2, sub_y + 2), sub_text, font=sub_font,
              fill=(60, 40, 30, 120))
    draw.text((sub_x, sub_y), sub_text, font=sub_font,
              fill=(60, 40, 30, 255))

    _draw_bottom_cta(draw, bg_w, bg_h)
    return _save_pin(final, output_filename, "big_number")


# ── TEMPLATE: Comparison ("Old vs New") ──────────────────────────────────


def generate_comparison_pin(product_name: str, image_url: str,
                            output_filename: str,
                            price: str = None, tags: str = None) -> str:
    """Two-column "old way vs new way" layout.

    Left column  → generic/old version (smaller, monochrome)
    Right column → this product (highlighted)
    """
    print(f"  🎨 [comparison] Generating pin: {product_name[:40]}...")

    mood = random.choice(["cream_minimal", "soft_lavender", "warm_sunset"])
    bg = _create_gradient_background(CANVAS_SIZE[0], CANVAS_SIZE[1],
                                     mood=mood).convert("RGBA")
    final = Image.new("RGBA", bg.size)
    final.paste(bg, (0, 0))
    draw = ImageDraw.Draw(final)
    bg_w, bg_h = final.size

    # Hook
    hook = _pick_hook(tags, product_name, price)
    hook_bottom_y = _draw_top_hook(draw, bg_w, bg_h, hook)

    # Title
    title = product_name
    title_font = _get_font(56)
    tl = textwrap.wrap(title, width=18)[:2]
    ty = hook_bottom_y + 20
    for line in tl:
        bb = draw.textbbox((0, 0), line, font=title_font)
        tw = bb[2] - bb[0]
        x = (bg_w - tw) // 2
        draw.text((x, ty), line, font=title_font,
                  fill=(45, 35, 70, 255))
        ty += bb[3] - bb[1] + 8

    # Two columns setup
    col_top = ty + 30
    col_bot = bg_h - 130
    col_h = col_bot - col_top
    half_w = bg_w // 2
    pad = 20

    # ── LEFT: "OLD" (faded box with X) ──
    left_x0, left_x1 = pad, half_w - 5
    draw.rounded_rectangle(
        [left_x0, col_top, left_x1, col_bot], radius=24,
        fill=(255, 255, 255, 130)
    )
    old_label_font = _get_font(36)
    old_label = "💸 the old way"
    bb = draw.textbbox((0, 0), old_label, font=old_label_font)
    tw = bb[2] - bb[0]
    draw.text(((left_x0 + left_x1 - tw) // 2, col_top + 18),
              old_label, font=old_label_font, fill=(120, 90, 80, 255))

    # "❌ Generic stuff"
    old_list = ["• overpay", "• bad quality", "• wastes time"]
    old_font = _get_font(34)
    y = col_top + 80
    for line in old_list:
        bb = draw.textbbox((0, 0), line, font=old_font)
        tw = bb[2] - bb[0]
        draw.text(((left_x0 + left_x1 - tw) // 2, y),
                  line, font=old_font, fill=(80, 60, 70, 230))
        y += 50

    # ── RIGHT: "NEW" (highlighted box + product photo) ──
    right_x0, right_x1 = half_w + 5, bg_w - pad
    draw.rounded_rectangle(
        [right_x0, col_top, right_x1, col_bot], radius=24,
        fill=(255, 240, 245, 235)
    )
    # Highlight border
    border_color = (200, 70, 100, 255)
    draw.rounded_rectangle(
        [right_x0 + 4, col_top + 4, right_x1 - 4, col_bot - 4], radius=20,
        outline=border_color, width=4
    )

    new_label = "✨ this way"
    bb = draw.textbbox((0, 0), new_label, font=old_label_font)
    tw = bb[2] - bb[0]
    draw.text(((right_x0 + right_x1 - tw) // 2, col_top + 18),
              new_label, font=old_label_font, fill=(200, 70, 100, 255))

    # Product image (small) inside right column
    if image_url:
        img = _get_product_image(image_url, max_size=(280, 280))
        if img:
            pw, ph = img.size
            offset = ((right_x0 + right_x1 - pw) // 2, col_top + 80)
            final.paste(img, offset, mask=img)

    # Price subtitle
    if price:
        price_font = _get_font(36)
        ptext = str(price)
        bb = draw.textbbox((0, 0), ptext, font=price_font)
        tw = bb[2] - bb[0]
        py = col_bot - 60
        draw.text(((right_x0 + right_x1 - tw) // 2, py),
                  ptext, font=price_font, fill=(45, 35, 70, 255))

    _draw_bottom_cta(draw, bg_w, bg_h)
    return _save_pin(final, output_filename, "comparison")


# ── TEMPLATE: Review Quote ───────────────────────────────────────────────


def generate_review_quote_pin(product_name: str, image_url: str,
                              output_filename: str,
                              price: str = None, tags: str = None) -> str:
    """Large quotation testimonial style. Best for trust-building.

    Layout:
        [hook pill]
        [huge quote line 1]
        [huge quote line 2]
        [— attribution + product small at bottom]
    """
    print(f"  🎨 [review_quote] Generating pin: {product_name[:40]}...")

    # Pull a believable review fragment
    REVIEW_BANK = [
        ("honestly", "a total game-changer"),
        ("I use it", "every. single. day."),
        ("best $20", "I've ever spent"),
        ("my roommate", "is jealous"),
        ("it's so good", "I bought it twice"),
        ("lives up to", "the hype, period"),
        ("finally a product", "that actually works"),
        ("I was skeptical", "but now I'm in love"),
        ("worth every", "single penny"),
        ("if you're hesitating", "just buy it"),
        ("saved me", "so much time"),
        ("my life is", "10x easier now"),
    ]
    quote_a, quote_b = random.choice(REVIEW_BANK)

    mood = random.choice(["warm_sunset", "dusty_rose", "cream_minimal"])
    bg = _create_gradient_background(CANVAS_SIZE[0], CANVAS_SIZE[1],
                                     mood=mood).convert("RGBA")
    final = Image.new("RGBA", bg.size)
    final.paste(bg, (0, 0))
    draw = ImageDraw.Draw(final)
    bg_w, bg_h = final.size

    # Hook at top
    hook = _pick_hook(tags, product_name, price)
    hook_bottom_y = _draw_top_hook(draw, bg_w, bg_h, hook)

    # Huge quotation marks behind text
    quote_font = _get_font(280)
    quote_glyph = '"'
    bb = draw.textbbox((0, 0), quote_glyph, font=quote_font)
    qw = bb[2] - bb[0]
    qh = bb[3] - bb[1]
    draw.text(((bg_w - qw) // 2 - 20, hook_bottom_y - 30), quote_glyph,
              font=quote_font, fill=(180, 100, 110, 100))

    # Quote line 1 (big)
    line1_font = _get_font(100)
    bb = draw.textbbox((0, 0), quote_a, font=line1_font)
    tw = bb[2] - bb[0]
    y1 = hook_bottom_y + 200
    x = (bg_w - tw) // 2
    draw.text((x + 3, y1 + 3), quote_a, font=line1_font,
              fill=(80, 50, 60, 150))
    draw.text((x, y1), quote_a, font=line1_font,
              fill=(80, 50, 60, 255))

    # Quote line 2 (italic-feeling — same font, different color, optional bold)
    line2_font = _get_font(100)
    bb = draw.textbbox((0, 0), quote_b, font=line2_font)
    tw = bb[2] - bb[0]
    y2 = y1 + 110
    x = (bg_w - tw) // 2
    draw.text((x + 3, y2 + 3), quote_b, font=line2_font,
              fill=(180, 70, 90, 150))
    draw.text((x, y2), quote_b, font=line2_font,
              fill=(180, 70, 90, 255))

    # Attribution: — product name
    attr_font = _get_font(40)
    attr_text = f"— {product_name[:40]}"
    if price:
        attr_text += f"  ·  {price}"
    bb = draw.textbbox((0, 0), attr_text, font=attr_font)
    tw = bb[2] - bb[0]
    ay = bg_h - 180
    x = (bg_w - tw) // 2
    draw.text((x, ay), attr_text, font=attr_font,
              fill=(60, 50, 50, 230))

    # Small product image in bottom-left (optional)
    if image_url:
        img = _get_product_image(image_url, max_size=(180, 180))
        if img:
            pw, ph = img.size
            offset = (40, bg_h - 200)
            # White rounded backing
            draw.rounded_rectangle(
                [offset[0] - 10, offset[1] - 10,
                 offset[0] + pw + 10, offset[1] + ph + 10],
                radius=18, fill=(255, 255, 255, 200)
            )
            final.paste(img, offset, mask=img)

    _draw_bottom_cta(draw, bg_w, bg_h)
    return _save_pin(final, output_filename, "review_quote")


if __name__ == "__main__":
    print("GENERATOR TEST")
    print("=" * 40)

    # Test product pin
    generate_pin(
        "Sony WH-1000XM4 Wireless Noise Canceling Headphones",
        "https://m.media-amazon.com/images/I/71o8Q5XJS5L._AC_SL1500_.jpg",
        "test_product_pin.jpg",
        price="$298"
    )

    # Test content pin
    generate_pin(
        "10 STUDY TIPS THAT ACTUALLY WORK",
        "",
        "test_content_pin.jpg",
        is_content=True,
        lines=[
            "1. Pomodoro method",
            "2. Active recall practice",
            "3. Teach someone else",
            "4. No phone zone 📵",
            "5. Music without lyrics",
            "6. Handwrite your notes",
            "7. Explain concepts out loud",
            "8. Take real breaks",
            "9. Sleep at least 7 hours",
            "10. Reward yourself!"
        ]
    )

    print(f"\n✅ Test pins generated in '{OUTPUT_DIR}/'")
