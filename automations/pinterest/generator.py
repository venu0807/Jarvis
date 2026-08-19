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

def generate_product_pin(product_name: str, image_url: str, output_filename: str,
                         price: str = None, tags: str = None,
                         hook: str = None) -> str:
    """Create a sleek modern product pin with a full-bleed image and dark gradient overlay."""
    print(f"  🎨 Generating sleek product pin: {product_name[:40]}...")

    try:
        high_res_url = re.sub(r'\._.*\.(jpg|png)$', r'.\1', image_url, flags=re.IGNORECASE) if image_url else image_url
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
            draw.text((CANVAS_SIZE[0] - tw) // 2, y, "...", font=font_list, fill=(255, 255, 255, 230))
            break

    # ── FOOTER (small text) ──
    y += 20
    font_footer = _get_font(28)
    footer_text = "Found this on Amazon →"
    f_bb = draw.textbbox((0, 0), footer_text, font=font_footer)
    fw = f_bb[2] - f_bb[0]
    fx = (CANVAS_SIZE[0] - fw) // 2
    draw.text((fx, y), footer_text, font=font_footer, fill=(255, 255, 255, 180))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, output_filename)
    final.convert("RGB").save(output_path, "JPEG", quality=95)
    print(f"  ✅ Pin saved: {output_path}")
    return output_path

def generate_pin(title: str, image_url: str, output_filename: str,
                 is_content: bool = False, lines: list = None,
                 tags: str = None, template: str = None,
                 price: str = None, description: str = None) -> str:
    """
    Main generation function that dispatches to the appropriate mode.
    
    Args:
        title: Pin title
        image_url: URL of product image (empty for content pins)
        output_filename: Name of output file
        is_content: True for content pin (text-only), False for product pin
        lines: List of text lines for content pins
        tags: Tags for badge detection
        template: Template name (not used in this implementation)
        price: Product price for badges
        description: Product description for badge detection
        
    Returns:
        str: Path to generated pin image
    """
    if is_content:
        return generate_content_pin(
            title=title,
            lines=lines or [],
            output_filename=output_filename,
            subtitle=description or tags
        )
    else:
        return generate_product_pin(
            product_name=title,
            image_url=image_url,
            output_filename=output_filename,
            price=price,
            tags=tags,
            hook=None  # Will be auto-picked
        )

# Local SEO functions (replacing the missing seo_optimizer import)
def generate_seo_title(name: str, category: str, is_trending: bool = False, price: str = None) -> str:
    """Generate a click-worthy Pinterest SEO title."""
    import random

    # High-converting psychological trigger prefixes
    prefixes = [
        "[AMAZON MUST-HAVE]",
        "[VIRAL FIND]",
        "[AESTHETIC UPGRADE]",
        "[GAME CHANGER]",
        "[GENIUS FIND]"
    ]
    prefix = random.choice(prefixes)

    # Simple SEO title generation (without LLM for reliability)
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
        return f"🔥 Trending Now: {prefix} {cleaned} | {suffix}"
    return f"{prefix} {cleaned} | {suffix}"

def generate_seo_description(name: str, category: str, price: str, is_trending: bool = False) -> str:
    """Generate a keyword-rich Pinterest description for SEO reach with aggressive CTAs."""
    # Aggressive Call-To-Action to drive outbound clicks
    cta_block = "\n\n👇 TAP THE IMAGE OR CLICK THE LINK TO SHOP THIS LOOK! 🛍️✨\n💬 Would you use this? Comment below!"

    # SEO-optimized description templates by category
    templates = {
        "tech": f"Upgrade your {name} game! This {category.replace('_', ' ')} essential is a must-have for students and professionals alike. {price} is a steal for the quality you get.",
        "dorm_decor": f"Transform your dorm room with this amazing {name}! Perfect for creating that aesthetic space you've been dreaming of. Only {price}!",
        "study_supplies": f"Boost your productivity with this {name}! A game-changing {category.replace('_', ' ')} tool that every student needs in their arsenal.",
        "self_care": f"Treat yourself to some well-deserved self-care with this {name}! Your mind and body will thank you. Only {price} for this essential.",
        "kitchen": f"Level up your cooking skills with this {name}! A {category.replace('_', ' ')} must-have that makes meal prep easier and more enjoyable.",
        "fashion": f"Stay on-trend with this stylish {name}! The perfect addition to your wardrobe that you'll reach for again and again. Only {price}!",
    }

    description = templates.get(category, f"Check out this amazing {name}! Perfect for anyone looking to upgrade their {category.replace('_', ' ')} setup. Only {price}!")

    if is_trending:
        description = f"🔥 TRENDING ALERT! {description} Don't miss out on this viral find!"

    description += cta_block
    return description

if __name__ == "__main__":
    # Test the generate_pin function
    print("Testing generate_pin function...")
    
    # Test product pin
    result1 = generate_pin(
        title="Test Product",
        image_url="https://example.com/image.jpg",
        output_filename="test_product.jpg",
        is_content=False,
        price="$29.99",
        tags="#test #product"
    )
    print(f"Product pin result: {result1}")
    
    # Test content pin
    result2 = generate_pin(
        title="Test Content Pin",
        image_url="",
        output_filename="test_content.jpg",
        is_content=True,
        lines=["Line 1", "Line 2", "Line 3"],
        tags="#test #content"
    )
    print(f"Content pin result: {result2}")