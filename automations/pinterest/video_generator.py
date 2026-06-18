"""
Video Generator — Convert pin images to short vertical videos for TikTok / Reels.

Why videos instead of just images?
- TikTok & Reels algorithms heavily favor video content
- Reach (impressions) per video >> image
- Same product, 3x the platforms = 3x the traffic

What it does:
- Takes a pin image (1000x1500 JPG) 
- Converts to 9:16 vertical format (1080x1920)
- Adds motion (Ken Burns zoom/pan effect)
- Adds animated text overlay (e.g., product name fading in)
- Exports MP4 (TikTok/Reels compatible)
"""

import os
import random
import textwrap
from typing import Optional

from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy import (
    ImageClip,
    TextClip,
    CompositeVideoClip,
    VideoFileClip,
    AudioClip,
)
import numpy as np

TEMPLATE_DIR = "template"
OUTPUT_DIR = "output"
VIDEO_DIR = os.path.join(OUTPUT_DIR, "videos")
os.makedirs(VIDEO_DIR, exist_ok=True)

CANVAS_SIZE = (1080, 1920)  # TikTok / Reels vertical
FONTS = {
    "bold": os.path.join(TEMPLATE_DIR, "font.ttf"),
    "regular": os.path.join(TEMPLATE_DIR, "font.ttf"),
}


# ── Helpers ───────────────────────────────────────────────────────────────


def _load_font(size: int, bold: bool = False):
    """Load a font with safe fallback."""
    path = FONTS["bold"] if bold else FONTS["regular"]
    if not os.path.exists(path):
        return ImageFont.load_default()
    try:
        return ImageFont.truetype(path, size)
    except Exception:
        return ImageFont.load_default()


def _pil_to_moviepy_frame(pil_img: Image.Image) -> np.ndarray:
    """Convert PIL image to numpy array (rgb)."""
    if pil_img.mode != "RGB":
        pil_img = pil_img.convert("RGB")
    return np.array(pil_img)


def _make_blurred_bg(pil_img: Image.Image) -> Image.Image:
    """Create a blurred/darkened background behind the product for letterboxing."""
    img = pil_img.convert("RGB")
    img = img.resize(CANVAS_SIZE, Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(radius=40))
    # Darken slightly
    overlay = Image.new("RGB", CANVAS_SIZE, (0, 0, 0))
    img = Image.blend(img, overlay, 0.4)
    return img


def _place_pin_centered(pin_img: Image.Image, bg: Image.Image) -> Image.Image:
    """Place the pin (1000x1500 or whatever) centered on the vertical canvas."""
    pin_w, pin_h = pin_img.size
    canvas_w, canvas_h = CANVAS_SIZE

    # Resize pin to fit nicely (leave 100px padding top/bottom)
    max_h = int(canvas_h * 0.85)
    max_w = int(canvas_w * 0.95)

    scale = min(max_w / pin_w, max_h / pin_h)
    new_w, new_h = int(pin_w * scale), int(pin_h * scale)
    pin_resized = pin_img.convert("RGB").resize((new_w, new_h), Image.LANCZOS)

    # Center
    x = (canvas_w - new_w) // 2
    y = (canvas_h - new_h) // 2

    bg.paste(pin_resized, (x, y))
    return bg


def _add_text_overlay(
    text: str,
    size: tuple = (1000, 240),
    fill=(255, 255, 255),
    bg=(255, 60, 60, 200),
    font_size: int = 56,
    bold: bool = True,
    lines: int = 2,
) -> Image.Image:
    """Create a text box that can be composited as overlay."""
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font = _load_font(font_size, bold=bold)
    wrapped = textwrap.wrap(text, width=22)[:lines]

    line_h = font_size + 10
    total_h = line_h * len(wrapped)

    y_start = (size[1] - total_h) // 2

    # Draw rounded rectangle background
    pad = 20
    rect_y0 = y_start - pad
    rect_y1 = y_start + total_h + pad
    rect_x0 = pad
    rect_x1 = size[0] - pad

    try:
        draw.rounded_rectangle(
            (rect_x0, rect_y0, rect_x1, rect_y1),
            radius=20,
            fill=bg,
        )
    except Exception:
        draw.rectangle((rect_x0, rect_y0, rect_x1, rect_y1), fill=bg)

    for i, line in enumerate(wrapped):
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (size[0] - w) // 2
        y = y_start + i * line_h
        draw.text((x, y), line, font=font, fill=fill)

    return img


# ── Main API ─────────────────────────────────────────────────────────────


def generate_video(
    pin_image_path: str,
    product_name: str,
    output_filename: Optional[str] = None,
    price: str = "",
    tags: str = "",
    duration: int = 8,
    zoom_start: float = 1.0,
    zoom_end: float = 1.10,
    fade_duration: float = 0.6,
) -> str:
    """
    Convert a pin image to a TikTok/Reels-ready vertical video.

    The video features:
    - Vertical 1080x1920 format
    - Subtle Ken Burns zoom (1.0 → 1.10) across duration
    - Animated text overlay showing product name + price
    - Dark blur background behind the pin for letterboxing
    - Fade in/out at start/end

    Args:
        pin_image_path: Path to the pin image (.jpg/.png)
        product_name: Name to display as animated overlay
        output_filename: Output MP4 path (auto-generated if None)
        price: Optional price tag (e.g. "$49.99")
        tags: Hashtags for the description (used in caption, not image)
        duration: Video length in seconds (default 8, range 5-30)
        zoom_start: Starting zoom factor (1.0 = no zoom)
        zoom_end: Ending zoom factor (1.10 = slight zoom-in)
        fade_duration: Fade in/out duration in seconds

    Returns:
        Path to the generated .mp4 file
    """
    if not os.path.exists(pin_image_path):
        raise FileNotFoundError(f"Pin image not found: {pin_image_path}")

    if output_filename is None:
        base = os.path.splitext(os.path.basename(pin_image_path))[0]
        output_filename = os.path.join(VIDEO_DIR, f"{base}.mp4")

    # 1. Load + prepare the pin
    pin_img = Image.open(pin_image_path)
    if pin_img.mode != "RGB":
        pin_img = pin_img.convert("RGB")

    bg = _make_blurred_bg(pin_img)
    final_frame = _place_pin_centered(pin_img, bg)

    # Save a temp still for moviepy
    tmp_still = os.path.join(OUTPUT_DIR, f"_tmp_{os.path.basename(output_filename)}.png")
    final_frame.save(tmp_still, "PNG")

    # 2. Build video clip with Ken Burns (zoom + pan)
    base_clip = ImageClip(tmp_still).with_duration(duration)

    if zoom_start != zoom_end:
        # Pre-render trimmed/zoomed versions using a time index
        # (moviepy 2.x: use resized via lambda with frame manipulation)
        from moviepy import vfx
        # Apply a simple zoom via resizing effect
        base_clip = base_clip.with_effects(
            [vfx.Resize(lambda t: zoom_start + (zoom_end - zoom_start) * (t / duration))]
        )

    # 3. Build text overlay as a separate clip (bottom = price bar)
    overlay_text = product_name
    if price:
        overlay_text = f"{product_name}  •  {price}"

    overlay_pil = _add_text_overlay(
        text=overlay_text,
        size=CANVAS_SIZE,
        fill=(255, 255, 255, 255),
        bg=(180, 30, 50, 220),
        font_size=54,
        bold=True,
        lines=2,
    )
    overlay_path = os.path.join(
        OUTPUT_DIR, f"_overlay_{os.path.basename(output_filename)}.png"
    )
    overlay_pil.save(overlay_path, "PNG")

    # 2b. Build a fade-in clip for overlay
    fade_frames = max(1, int(fade_duration * 24))

    overlay_clip = (
        ImageClip(overlay_path)
        .with_duration(duration)
        .with_position(("center", 1700))
        .with_start(fade_duration)
    )

    # 4. Top hook text ("Must-have for students" or similar)
    hook = "🔥 THIS IS A STUDENT MUST-HAVE"
    hook_pil = _add_text_overlay(
        text=hook,
        size=CANVAS_SIZE,
        fill=(255, 255, 255, 255),
        bg=(0, 0, 0, 170),
        font_size=42,
        bold=True,
        lines=1,
    )
    hook_path = os.path.join(
        OUTPUT_DIR, f"_hook_{os.path.basename(output_filename)}.png"
    )
    hook_pil.save(hook_path, "PNG")

    hook_clip = (
        ImageClip(hook_path)
        .with_duration(duration)
        .with_position(("center", 100))
        .with_start(0)
    )

    # 5. Composite + fade in/out
    from moviepy import vfx
    final = CompositeVideoClip(
        [base_clip, overlay_clip, hook_clip],
        size=CANVAS_SIZE,
    )
    final = final.with_effects(
        [vfx.CrossFadeIn(fade_duration), vfx.CrossFadeOut(fade_duration)]
    )

    # 6. Write output
    final.write_videofile(
        output_filename,
        fps=24,
        codec="libx264",
        audio=False,
        logger=None,
        threads=2,
    )

    # Cleanup temps
    for p in (tmp_still, overlay_path, hook_path):
        try:
            os.remove(p)
        except OSError:
            pass

    return output_filename


def generate_caption(
    product_name: str,
    affiliate_url: str,
    tags: str = "",
    platform: str = "tiktok",
    price: str = "",
) -> str:
    """
    Generate a caption/description for TikTok or Reels.
    Includes hashtags + affiliate link in bio mention.
    """
    # Build hashtags from tags + platform-specific ones
    tag_list = []
    if tags:
        tag_list.extend([t.strip().lstrip("#") for t in tags.split() if t.strip()])
    tag_list.extend(
        [
            "amazonfinds",
            "collegefinds",
            "studentessentials",
            "amazonmusthaves",
            "studenthacks",
            "shopwithme",
            "affordable",
        ]
    )
    # Instagram-specific tags removed — Pinterest-only bot

    # Dedup
    seen = set()
    deduped_tags = []
    for t in tag_list:
        t_clean = t.strip().lstrip("#").lower().replace(" ", "")
        if t_clean and t_clean not in seen:
            seen.add(t_clean)
            deduped_tags.append(t_clean)

    hashtags_str = " ".join(f"#{t}" for t in deduped_tags[:18])

    hook_line = "🔥 POI: this is a viral student must-have"
    name_line = f"{product_name}"
    if price:
        name_line += f" — {price}"
    desc_line = "Link in bio 👆 (Amazon Associates affiliate link)"

    parts = [
        hook_line,
        name_line,
        "",
        desc_line,
        "",
        hashtags_str,
    ]
    return "\n".join(parts).strip()


# ── CLI mode ─────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3:
        print("Usage: video_generator.py <pin_image> <product_name> [price]")
        sys.exit(1)

    img = sys.argv[1]
    name = sys.argv[2]
    price = sys.argv[3] if len(sys.argv) > 3 else ""

    out = generate_video(img, name, price=price, tags="")
    print(f"\n✅ Video saved: {out}")
    print(f"   Size: {os.path.getsize(out)} bytes")
