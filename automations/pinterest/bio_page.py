"""
Bio Link Page Generator — Creates a "Linktree-style" page for affiliate links.

Why this matters:
- TikTok bio: 1 clickable link
- Instagram bio: 1 clickable link
- YouTube bio: 1 clickable link

Instead of picking ONE product link, we host a small page with our
latest picks. Each pin/video rotates which products show there.

How it works:
1. Pull pending products from data.csv
2. Generate a beautiful static HTML page with affiliate links
3. Save as `bio/index.html`
4. Host for FREE on: GitHub Pages, Netlify, Vercel, Cloudflare Pages
5. Put the hosted URL in your TikTok / Instagram / YouTube bio

When a video goes viral → viewers click bio → land on this page →
see rotating top picks → click → Amazon with our tag → $$$$$

Alternatively, the page is also mobile-responsive and works offline
if user just opens it straight.
"""

import os
import shutil
import html
import datetime
from typing import List, Dict

import pandas as pd
from database import get_products_df, save_products_df


OUT_DIR = "bio"
TEMPLATE_FILE = os.path.join(OUT_DIR, "index.html")


# ── HTML Template ────────────────────────────────────────────────────────

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<meta name="description" content="{description}">
<script>
  const params = new URLSearchParams(window.location.search);
  const asin = params.get('asin');
  if (asin) {{
    window.location.replace(`https://www.amazon.com/dp/${{asin}}?tag={amazon_tag}`);
  }}
</script>
<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🛍️</text></svg>">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    min-height: 100vh;
    padding: 20px;
    color: #1a202c;
  }}
  .container {{
    max-width: 480px;
    margin: 0 auto;
  }}
  .header {{
    text-align: center;
    color: white;
    padding: 30px 20px;
    margin-bottom: 25px;
  }}
  .avatar {{
    width: 90px;
    height: 90px;
    border-radius: 50%;
    background: linear-gradient(135deg, #FFB4A2 0%, #FF9A8B 100%);
    margin: 0 auto 15px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 45px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.25);
  }}
  h1 {{ font-size: 24px; font-weight: 800; margin-bottom: 4px; }}
  .tagline {{ font-size: 14px; opacity: 0.9; }}
  .section-title {{
    color: white;
    text-align: center;
    margin: 0 auto 15px;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-weight: 700;
    opacity: 0.95;
  }}
  .links {{
    display: flex;
    flex-direction: column;
    gap: 14px;
  }}
  .link-card {{
    background: white;
    border-radius: 18px;
    padding: 18px 20px;
    display: flex;
    align-items: center;
    gap: 15px;
    text-decoration: none;
    color: inherit;
    box-shadow: 0 8px 20px rgba(0,0,0,0.10);
    transition: transform 0.2s, box-shadow 0.2s;
    cursor: pointer;
  }}
  .link-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 14px 30px rgba(0,0,0,0.16);
  }}
  .emoji {{
    font-size: 30px;
    flex-shrink: 0;
  }}
  .link-text {{
    flex-grow: 1;
  }}
  .link-name {{
    font-weight: 700;
    font-size: 15px;
    color: #1a202c;
    margin-bottom: 2px;
  }}
  .link-sub {{
    font-size: 12px;
    color: #718096;
  }}
  .arrow {{
    color: #cbd5e0;
    font-size: 22px;
  }}
  .badge {{
    display: inline-block;
    background: linear-gradient(90deg, #ff6b6b 0%, #ee5a52 100%);
    color: white;
    padding: 2px 8px;
    border-radius: 6px;
    font-size: 10px;
    font-weight: 700;
    margin-left: 6px;
    text-transform: uppercase;
  }}
  .footer {{
    text-align: center;
    color: rgba(255,255,255,0.85);
    margin-top: 30px;
    padding: 20px;
    font-size: 12px;
  }}
  .footer a {{ color: white; text-decoration: underline; }}
  .feature-banner {{
    background: linear-gradient(135deg, #ffd89b 0%, #19547b 100%);
    color: white;
    padding: 18px;
    border-radius: 16px;
    margin-bottom: 22px;
    text-align: center;
    box-shadow: 0 8px 20px rgba(0,0,0,0.15);
  }}
  .feature-banner h2 {{ font-size: 17px; margin-bottom: 4px; }}
  .feature-banner p {{ font-size: 13px; opacity: 0.95; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <div class="avatar">🛍️</div>
    <h1>{title}</h1>
    <p class="tagline">{tagline}</p>
  </div>

  <div class="feature-banner">
    <h2>🔥 Today's Top Student Picks</h2>
    <p>Updated {today_date} · Click any to shop</p>
  </div>

  <h3 class="section-title">Top Picks</h3>
  <div class="links">
    {link_cards}
  </div>

  <h3 class="section-title" style="margin-top: 25px;">Follow Me</h3>
  <div class="links">
    <a class="link-card" href="{pinterest_url}" target="_blank">
      <span class="emoji">📌</span>
      <div class="link-text">
        <div class="link-name">Pinterest</div>
        <div class="link-sub">Saved ideas, boards & pins</div>
      </div>
      <span class="arrow">›</span>
    </a>
    {social_cards}
  </div>

  <div class="footer">
    <p>As an Amazon Associate, I earn from qualifying purchases.</p>
    <p style="margin-top: 8px;">© {year} {title}</p>
  </div>
</div>
</body>
</html>
"""


CATEGORY_EMOJI = {
    "tech": "💻",
    "dorm_decor": "🛏️",
    "study_supplies": "📚",
    "self_care": "🧴",
    "kitchen": "🍳",
    "fashion": "👕",
    "default": "🛍️",
}


def _emoji_for(category: str) -> str:
    return CATEGORY_EMOJI.get(category.lower(), CATEGORY_EMOJI["default"])


def _truncate(text: str, length: int = 50) -> str:
    text = str(text).strip()
    if len(text) <= length:
        return text
    return text[:length].rstrip() + "…"


def _render_link_cards(products: List[Dict]) -> str:
    """Build the HTML cards for each product."""
    cards = []
    for i, p in enumerate(products):
        emoji = _emoji_for(p.get("category", "default"))
        name = _truncate(p.get("name", "Product"), 48)
        sub_price = p.get("price", "").strip()
        badge = ""
        if i == 0:
            badge = '<span class="badge">Top Pick</span>'

        cards.append(
            f'''
    <a class="link-card" href="{html.escape(p["affiliate_link"])}" target="_blank" rel="noopener">
      <span class="emoji">{emoji}</span>
      <div class="link-text">
        <div class="link-name">{html.escape(name)}{badge}</div>
        <div class="link-sub">{html.escape(sub_price) if sub_price else "View on Amazon"}</div>
      </div>
      <span class="arrow">›</span>
    </a>'''
        )
    return "\n".join(cards)


def _render_social_cards() -> str:
    cards = []
    # Instagram support removed — Pinterest-only bot
    return "\n".join(cards)


def generate_bio_page(
    csv_path: str = "data.csv",
    max_products: int = 8,
    title: str = "Student Deal Finds",
    tagline: str = "Daily picks for students · All Amazon finds",
    description: str = "Top trending Amazon finds curated for college students and grads on a budget.",
    pinterest_url: str = "https://pinterest.com",
) -> str:
    """
    Generate the bio link page HTML from data.csv (pending products).

    Args:
        csv_path: Path to data.csv
        max_products: How many products to show
        title: Title of the page
        tagline: Subtitle
        description: Meta description

    Returns:
        Path to generated HTML file
    """
    if not os.path.exists(csv_path):
        print(f"  ⚠️  {csv_path} not found — empty page generated")
        products = []
    else:
        df = get_products_df()
        df = df.fillna("")
        # Pick products that have not been pinned yet, prefer those with images
        pending = df[
            df["Status"].astype(str).str.strip().str.lower().isin(["", "pending"])
        ].copy()

        products = []
        amazon_tag_match = "tag=" + os.getenv("AMAZON_AFFILIATE_TAG", "venue")
        for _, row in pending.iterrows():
            link = str(row.get("Affiliate Link", "")).strip()
            if not link or amazon_tag_match not in link:
                # include if tag matches anyway
                if "tag=" not in link:
                    continue
            products.append(
                {
                    "name": row.get("Product Name", ""),
                    "affiliate_link": link,
                    "category": row.get("Category", "default"),
                    "price": row.get("Price", ""),
                }
            )
            if len(products) >= max_products:
                break

    if not products:
        # Fallback: any available product from CSV
        if not df.empty:
            for _, row in df.iterrows():
                link = str(row.get("Affiliate Link", "")).strip()
                if "tag=" in link:
                    products.append(
                        {
                            "name": row.get("Product Name", ""),
                            "affiliate_link": link,
                            "category": row.get("Category", "default"),
                            "price": row.get("Price", ""),
                        }
                    )
                    if len(products) >= max_products:
                        break

    os.makedirs(OUT_DIR, exist_ok=True)

    amazon_tag = os.getenv("AMAZON_TAG", "venu080d-21")
    html_content = HTML_TEMPLATE.format(
        title=html.escape(title),
        tagline=html.escape(tagline),
        description=html.escape(description),
        pinterest_url=pinterest_url,
        link_cards=_render_link_cards(products),
        social_cards=_render_social_cards(),
        today_date=datetime.date.today().strftime("%B %d"),
        year=datetime.date.today().year,
        amazon_tag=amazon_tag,
    )

    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        f.write(html_content)

    print(f"  ✅ Bio page generated: {TEMPLATE_FILE} ({len(products)} products)")
    return TEMPLATE_FILE


# ── CLI mode ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    out = generate_bio_page(
        csv_path="data.csv",
        max_products=int(sys.argv[1]) if len(sys.argv) > 1 else 8,
    )
    print(f"\n📄 Page saved to: {out}")
    print(f"   Open in browser to preview")
    print(f"   Or serve free by uploading to: github.io, netlify.com, or surge.sh")
