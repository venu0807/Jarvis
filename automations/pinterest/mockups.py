import os
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import textwrap

OUTPUT_DIR = "C:/Users/Venu/.gemini/antigravity-ide/brain/5c1521e1-425e-4e62-9209-2d79d21434e8/"
IMAGE_URL = "https://m.media-amazon.com/images/I/61B5hIAmvdL.jpg"

print("Fetching original...")
resp = requests.get(IMAGE_URL)
original_img = Image.open(BytesIO(resp.content)).convert("RGBA")
original_img.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

def draw_hook_text(draw, canvas_w, canvas_h):
    try:
        font_bold = ImageFont.truetype("template/font.ttf", 64)
        font_small = ImageFont.truetype("template/font.ttf", 36)
    except Exception:
        font_bold = ImageFont.load_default()
        font_small = ImageFont.load_default()
        
    hook = "My exam week survival kit, ranked"
    lines = textwrap.wrap(hook, width=20)
    y = canvas_h - (len(lines)*80) - 150
    for line in lines:
        bb = draw.textbbox((0, 0), line, font=font_bold)
        x = (canvas_w - (bb[2]-bb[0])) // 2
        draw.text((x, y), line, font=font_bold, fill=(255,255,255,255))
        y += 85
        
    pill_text = "⭐ Amazon Must-Haves"
    bb = draw.textbbox((0, 0), pill_text, font=font_small)
    hx = (canvas_w - (bb[2]-bb[0])) // 2
    draw.rounded_rectangle([hx - 30, 45, hx + (bb[2]-bb[0]) + 30, 45 + (bb[3]-bb[1]) + 20], radius=35, fill=(255, 60, 60, 255))
    draw.text((hx, 60), pill_text, font=font_small, fill=(255, 255, 255, 255))

def generate_rembg_mockup():
    print("Generating Rembg mockup...")
    import rembg
    canvas_w, canvas_h = 1000, 1500
    final = Image.new("RGBA", (canvas_w, canvas_h))
    draw = ImageDraw.Draw(final)
    for y in range(canvas_h):
        r = int(10 + (20 * y / canvas_h))
        g = int(10 + (40 * y / canvas_h))
        b = int(25 + (60 * y / canvas_h))
        draw.line([(0, y), (canvas_w, y)], fill=(r, g, b, 255))
    
    cutout = rembg.remove(original_img)
    cutout.thumbnail((800, 800), Image.Resampling.LANCZOS)
    
    shadow = Image.new("RGBA", cutout.size, (0,0,0,0))
    s_draw = ImageDraw.Draw(shadow)
    s_draw.rectangle([0,0, cutout.size[0], cutout.size[1]], fill=(0,0,0,100))
    shadow = Image.composite(shadow, Image.new("RGBA", cutout.size), cutout)
    shadow = shadow.filter(ImageFilter.GaussianBlur(20))
    
    cx = (canvas_w - cutout.size[0]) // 2
    cy = 250
    final.paste(shadow, (cx+15, cy+25), shadow)
    final.paste(cutout, (cx, cy), cutout)
    
    draw_hook_text(draw, canvas_w, canvas_h)
    final.save(os.path.join(OUTPUT_DIR, "mockup_rembg.png"), "PNG")

def generate_review_mockup():
    print("Generating Review mockup...")
    canvas_w, canvas_h = 1000, 1500
    final = Image.new("RGBA", (canvas_w, canvas_h), (255,255,255,255))
    
    img = original_img.copy()
    img.thumbnail((900, 900), Image.Resampling.LANCZOS)
    cx = (canvas_w - img.size[0]) // 2
    cy = 150
    final.paste(img, (cx, cy), img)
    
    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    for y in range(600, canvas_h):
        alpha = int(((y - 600) / (canvas_h - 600)) * 240)
        draw_overlay.line([(0, y), (canvas_w, y)], fill=(20, 20, 25, alpha))
    final = Image.alpha_composite(final, overlay)
    
    draw = ImageDraw.Draw(final)
    draw_hook_text(draw, canvas_w, canvas_h)
    
    try: font_sub = ImageFont.truetype("template/font.ttf", 32)
    except: font_sub = ImageFont.load_default()
    review = "⭐⭐⭐⭐⭐\n\"The bass on these is absolutely insane!\""
    bx = 100
    by = cy + img.size[1] - 80
    draw.rounded_rectangle([bx, by, bx+800, by+120], radius=20, fill=(255, 255, 255, 240))
    draw.text((bx+30, by+20), review, font=font_sub, fill=(20, 20, 20, 255))
    
    final.save(os.path.join(OUTPUT_DIR, "mockup_review.png"), "PNG")

def generate_unsplash_mockup():
    print("Generating Unsplash mockup...")
    unsplash_url = "https://images.unsplash.com/photo-1497215728101-856f4ea42174?auto=format&fit=crop&w=1000&q=80"
    u_resp = requests.get(unsplash_url)
    bg = Image.open(BytesIO(u_resp.content)).convert("RGBA")
    bg = bg.resize((1000, 1500))
    bg = bg.filter(ImageFilter.GaussianBlur(15))
    
    overlay = Image.new("RGBA", (1000, 1500), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    for y in range(1500):
        draw_overlay.line([(0, y), (1000, y)], fill=(0, 0, 0, 100 + int(100*y/1500)))
    bg = Image.alpha_composite(bg, overlay)
    
    img = original_img.copy()
    img.thumbnail((700, 700), Image.Resampling.LANCZOS)
    cx = (1000 - img.size[0]) // 2
    cy = 200
    mask = Image.new("L", img.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([0,0, img.size[0], img.size[1]], radius=50, fill=255)
    bg.paste(img, (cx, cy), mask)
    
    draw = ImageDraw.Draw(bg)
    draw_hook_text(draw, 1000, 1500)
    bg.save(os.path.join(OUTPUT_DIR, "mockup_unsplash.png"), "PNG")

def generate_closeup_mockup():
    print("Generating Closeup mockup...")
    canvas_w, canvas_h = 1000, 1500
    final = Image.new("RGBA", (canvas_w, canvas_h), (255,255,255,255))
    
    img = original_img.copy()
    img.thumbnail((1400, 1400), Image.Resampling.LANCZOS)
    cx = (canvas_w - img.size[0]) // 2
    cy = 0
    final.paste(img, (cx, cy), img)
    
    overlay = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
    draw_overlay = ImageDraw.Draw(overlay)
    for y in range(500, canvas_h):
        alpha = int(((y - 500) / (canvas_h - 500)) * 255)
        draw_overlay.line([(0, y), (canvas_w, y)], fill=(15, 15, 20, alpha))
    final = Image.alpha_composite(final, overlay)
    
    draw = ImageDraw.Draw(final)
    try:
        font_bold = ImageFont.truetype("template/font.ttf", 72)
        font_medium = ImageFont.truetype("template/font.ttf", 52)
        font_sub = ImageFont.truetype("template/font.ttf", 42)
    except Exception:
        font_bold = ImageFont.load_default()
        font_medium = ImageFont.load_default()
        font_sub = ImageFont.load_default()
    
    title = "boAt Rockerz 255"
    bb = draw.textbbox((0, 0), title, font=font_bold)
    draw.text(((canvas_w - (bb[2]-bb[0]))//2, 850), title, font=font_bold, fill=(255, 215, 0, 255))
    
    features = [
        "✓ Magnetic Earbuds",
        "✓ 8 Hours Playback",
        "✓ Secure Neckband"
    ]
    y = 1000
    for f in features:
        bb = draw.textbbox((0, 0), f, font=font_medium)
        draw.text(((canvas_w - (bb[2]-bb[0]))//2, y), f, font=font_medium, fill=(255, 255, 255, 255))
        y += 85
        
    bb = draw.textbbox((0, 0), "Tap to Shop →", font=font_sub)
    tw = bb[2] - bb[0]
    btn_w, btn_h = tw + 80, 80
    btn_x = (canvas_w - btn_w) // 2
    btn_y = canvas_h - 150
    draw.rounded_rectangle([btn_x, btn_y, btn_x+btn_w, btn_y+btn_h], radius=40, fill=(255, 255, 255, 255))
    draw.text((btn_x + 40, btn_y + 15), "Tap to Shop →", font=font_sub, fill=(20, 20, 25, 255))
    
    final.save(os.path.join(OUTPUT_DIR, "mockup_closeup.png"), "PNG")

if __name__ == "__main__":
    generate_closeup_mockup()
    print("Done!")
