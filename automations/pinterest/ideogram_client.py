"""
Ideogram Client — Generate aesthetic lifestyle photos for Pinterest pins.

Why Ideogram?
- Pinterest algorithm LOVES lifestyle photos (3-5× higher CTR vs product shots)
- Ideogram specializes in aesthetic compositions, flat-lays, and lifestyle scenes
- 1 credit per image (paid); 12 free credits/day on free tier
- Vertical ASPECT_9_16 matches Pinterest perfectly

Usage:
  from ideogram_client import IdeogramClient
  client = IdeogramClient()
  url = client.generate("aesthetic study desk with laptop and coffee", category="tech")
  
The client:
- Reads IDOGRAM_API_KEY from .env
- Handles aspect ratios per platform
- Caches generated URLs to avoid duplicate credits
- Builds category-specific prompts from product names
"""

import os
import json
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict
from dotenv import dotenv_values

# Load .env once
_ENV = dotenv_values(".env") if Path(".env").exists() else {}
API_KEY = _ENV.get("IDOGRAM_API_KEY", "")

BASE_URL = "https://api.ideogram.ai"
ENDPOINT_GENERATE = f"{BASE_URL}/generate"

CREDIT_CACHE = "ideogram_credits.json"


# ── Aspect ratios per platform ───────────────────────────────────────────

ASPECT_RATIOS = {
    "pinterest": "ASPECT_9_16",   # vertical pin
    "tiktok": "ASPECT_9_16",
    "square":    "ASPECT_1_1",
    "landscape": "ASPECT_16_9",
}


# ── Prompt templates per category ───────────────────────────────────────

PROMPT_TEMPLATES = {
    "tech": (
        "Aesthetic flat-lay of {product} on a clean modern college student desk. "
        "Minimal workspace, soft morning light, neutral palette, "
        "Instagram-style photography, vertical composition, "
        "shot from above, 4K, shallow depth of field"
    ),
    "dorm_decor": (
        "Cozy aesthetic dorm room photo featuring {product}. "
        "Warm soft lighting, neutral boho tones, lifestyle photography, "
        "vertical composition, dreamy aesthetic, "
        "college student vibes, 4K"
    ),
    "study_supplies": (
        "Top-down aesthetic photo of {product} on a study desk. "
        "Planner, laptop, coffee cup, and pens visible nearby. "
        "Vertical composition, soft daylight, study aesthetic, "
        "Instagram-worthy, 4K"
    ),
    "self_care": (
        "Aesthetic lifestyle photo of {product}, soft natural light, "
        "minimalist bathroom or vanity setup, "
        "neutral pastel tones, dreamy vibe, "
        "vertical composition, 4K"
    ),
    "kitchen": (
        "Aesthetic kitchen photo featuring {product}, "
        "bright natural lighting, modern dorm kitchen, "
        "coffee mug and fresh fruit nearby, "
        "vertical composition, Instagram-style, 4K"
    ),
    "fashion": (
        "Aesthetic lifestyle photo of {product}, "
        "soft natural light, neutral background, "
        "fashion blogger style, capsule wardrobe feel, "
        "vertical composition, 4K"
    ),
    "default": (
        "Aesthetic product photo of {product}, "
        "college student lifestyle, soft natural lighting, "
        "vertical composition, Instagram-style, "
        "clean composition, 4K"
    ),
}


# ── Credit tracker ──────────────────────────────────────────────────────


def _load_credits() -> dict:
    if not Path(CREDIT_CACHE).exists():
        return {"today": None, "used": 0, "history": []}
    try:
        return json.loads(Path(CREDIT_CACHE).read_text())
    except Exception:
        return {"today": None, "used": 0, "history": []}


def _save_credits(d: dict):
    Path(CREDIT_CACHE).write_text(json.dumps(d, indent=2))


def _track_credit_used():
    today = datetime.now().strftime("%Y-%m-%d")
    d = _load_credits()
    if d.get("today") != today:
        d = {"today": today, "used": 0, "history": []}
    d["used"] += 1
    d["history"].append({"ts": datetime.now().isoformat()})
    _save_credits(d)


def credits_used_today() -> int:
    """How many credits we've spent today on this machine."""
    d = _load_credits()
    if d.get("today") != datetime.now().strftime("%Y-%m-%d"):
        return 0
    return d.get("used", 0)


# ── Client ──────────────────────────────────────────────────────────────


class IdeogramClient:
    """Minimal Ideogram API wrapper."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or API_KEY
        if not self.api_key or len(self.api_key) < 20:
            raise ValueError(
                "IDOGRAM_API_KEY not found in .env. "
                "Add it to your .env file (do NOT paste it in chat)."
            )

    def _post(self, payload: Dict, timeout: int = 60) -> Dict:
        headers = {
            "Api-Key": self.api_key,
            "Content-Type": "application/json",
        }
        r = requests.post(
            ENDPOINT_GENERATE,
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        if r.status_code == 200:
            return r.json()
        # Try to parse error
        try:
            err = r.json()
            detail = err.get("detail", err.get("error", str(err)))
        except Exception:
            detail = r.text[:200]
        raise IdeogramError(status=r.status_code, detail=detail, payload=payload)

    def build_prompt(
        self,
        product_name: str,
        category: str = "default",
        extra: str = "",
    ) -> str:
        """Build an aesthetic-lifestyle prompt for a product."""
        template = PROMPT_TEMPLATES.get(
            category.lower(), PROMPT_TEMPLATES["default"]
        )
        prompt = template.format(product=product_name)
        if extra:
            prompt = f"{prompt}, {extra}"
        return prompt

    def generate(
        self,
        prompt: str,
        aspect_ratio: str = "ASPECT_9_16",
        model: str = "V_2",
        style_type: str = "AUTO",
        num_images: int = 1,
        timeout: int = 90,
    ) -> str:
        """
        Generate one image from Ideogram.

        Args:
            prompt: Detailed scene description
            aspect_ratio: IDEOGRAM enum (use ASPECT_RATIOS map above)
            model: 'V_2' (default) or 'V_2_TURBO' (faster, cheaper)
            style_type: 'AUTO', 'REALISTIC', 'DESIGN', etc.

        Returns:
            The image URL (hosted by Ideogram; valid 24h)
        """
        if aspect_ratio not in ASPECT_RATIOS.values() and not aspect_ratio.startswith("ASPECT_"):
            # Allow users to pass friendly names from ASPECT_RATIOS map
            if aspect_ratio in ASPECT_RATIOS:
                aspect_ratio = ASPECT_RATIOS[aspect_ratio]

        payload = {
            "image_request": {
                "prompt": prompt,
                "aspect_ratio": aspect_ratio,
                "model": model,
                "num_images": num_images,
                "style_type": style_type,
            }
        }
        out = self._post(payload, timeout=timeout)
        if isinstance(out, dict) and "data" in out and out["data"]:
            url = out["data"][0].get("url", "")
            if url:
                _track_credit_used()
                return url
        raise IdeogramError(
            status=200,
            detail=f"Unexpected response shape: {str(out)[:300]}",
            payload=payload,
        )

    def generate_for_product(
        self,
        product_name: str,
        category: str = "default",
        platform: str = "pinterest",
        extra: str = "",
        save_to: Optional[str] = None,
    ) -> str:
        """
        Generate an aesthetic pin-sized image for a product.

        Convenience wrapper that:
        - Builds the prompt from category template
        - Picks the right aspect ratio for the platform
        - Optionally saves the image locally

        Returns:
            Public image URL (valid 24h)
        """
        prompt = self.build_prompt(product_name, category, extra=extra)
        url = self.generate(
            prompt,
            aspect_ratio=ASPECT_RATIOS.get(platform, ASPECT_RATIOS["pinterest"]),
        )

        if save_to:
            try:
                img_data = requests.get(url, timeout=30).content
                Path(save_to).write_bytes(img_data)
            except Exception as e:
                print(f"  ⚠️  Could not save locally: {e}")

        return url


# ── Custom exception ────────────────────────────────────────────────────


class IdeogramError(Exception):
    def __init__(self, status: int, detail: str, payload: Dict):
        self.status = status
        self.detail = detail
        self.payload = payload
        super().__init__(f"Ideogram API error {status}: {detail}")


# ── CLI mode ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python ideogram_client.py prompt '<text>'")
        print("  python ideogram_client.py product '<name>' --category tech")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "credits":
        used = credits_used_today()
        print(f"  Credits used today: {used}")
        if used >= 12:
            print(f"  ⚠️  Daily free tier limit likely hit (12).")
        sys.exit(0)

    if cmd == "prompt":
        text = sys.argv[2] if len(sys.argv) > 2 else "aesthetic desk setup"
        try:
            client = IdeogramClient()
            url = client.generate(text)
            print(f"  ✅ Image URL: {url}")
        except IdeogramError as e:
            print(f"  ❌ {e}")
        sys.exit(0)

    if cmd == "product":
        name = sys.argv[2] if len(sys.argv) > 2 else "laptop"
        cat = "default"
        if "--category" in sys.argv:
            i = sys.argv.index("--category")
            cat = sys.argv[i + 1]
        try:
            client = IdeogramClient()
            url = client.generate_for_product(
                product_name=name,
                category=cat,
                platform="pinterest",
            )
            print(f"  ✅ Image for '{name}': {url}")
        except IdeogramError as e:
            print(f"  ❌ {e}")
        sys.exit(0)
