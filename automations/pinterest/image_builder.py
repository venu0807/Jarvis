import os
import textwrap
import requests
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont

# 4K Resolution 2:3 Pinterest Ratio
PIN_WIDTH = 2160
PIN_HEIGHT = 3240

BG_COLORS = {"default": "#F4F4F4", "tech": "#121212", "study_supplies": "#FFF9E6", "dorm_decor": "#FFEFF4", "kitchen": "#FFFFFF"}
TEXT_COLORS = {"default": "#2D2D2D", "tech": "#FFFFFF", "study_supplies": "#333333", "dorm_decor": "#333333", "kitchen": "#2D2D2D"}


def get_font(size: int, bold=False):
    """Load a system font that works on WSL/Ubuntu."""
    font_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arialbd.ttf" if bold else "C:\\Windows\\Fonts\\arial.ttf"
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()

def download_image(url: str) -> Image.Image:
    """Download an image from a URL or load from a local path."""
    if url.startswith("http"):
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        img = Image.open(BytesIO(response.content))
    else:
        img = Image.open(url)
    return img.convert("RGBA")

def generate_pinterest_pin(image_url: str, title: str, category: str, output_path: str, layout_style: str = "seo_full_bleed", price: str = None) -> str:
    """
    Downloads the raw product image and generates a highly-attractive 4K 2160x3240 Pin.
    Saves the generated pin to output_path.
    """
    try:
        # 1. Create Base Canvas
        canvas = Image.new("RGBA", (PIN_WIDTH, PIN_HEIGHT), "#FFFFFF")
        
        # 2. Download and Zoom/Crop Product Image to fill the ENTIRE canvas
        product_img = download_image(image_url)
        img_w, img_h = product_img.size
        canvas_ratio = PIN_WIDTH / PIN_HEIGHT
        img_ratio = img_w / img_h
        
        if img_ratio > canvas_ratio:
            new_h = PIN_HEIGHT
            new_w = int(new_h * img_ratio)
            product_img = product_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            left = (new_w - PIN_WIDTH) // 2
            product_img = product_img.crop((left, 0, left + PIN_WIDTH, PIN_HEIGHT))
        else:
            new_w = PIN_WIDTH
            new_h = int(new_w / img_ratio)
            product_img = product_img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            top = (new_h - PIN_HEIGHT) // 2
            product_img = product_img.crop((0, top, PIN_WIDTH, top + PIN_HEIGHT))
            
        if "A" in product_img.getbands():
            canvas.paste(product_img, (0, 0), product_img)
        else:
            canvas.paste(product_img, (0, 0))
            
        # 3. Create elegant dark gradient overlay at the bottom for text readability
        overlay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        gradient_start = PIN_HEIGHT - 1200
        for y in range(gradient_start, PIN_HEIGHT):
            # Alpha goes from 0 to 220
            alpha = int(220 * ((y - gradient_start) / (PIN_HEIGHT - gradient_start)))
            overlay_draw.line([(0, y), (PIN_WIDTH, y)], fill=(0, 0, 0, alpha))
            
        canvas = Image.alpha_composite(canvas, overlay)
        draw = ImageDraw.Draw(canvas)
        
        # 4. Add Large, Readable, Attractive Title
        # Clean up title: Amazon titles are often very long and messy
        clean_title = title.split(",")[0].split("-")[0].strip()
        if len(clean_title) > 60:
            clean_title = clean_title[:57] + "..."
            
        title_font = get_font(120, bold=True)
        wrapped_lines = textwrap.wrap(clean_title, width=28)
        
        text_y = PIN_HEIGHT - 600
        for line in wrapped_lines:
            # Drop shadow for extra pop
            draw.text((PIN_WIDTH//2 + 5, text_y + 5), line, font=title_font, fill=(0,0,0,180), anchor="mm")
            draw.text((PIN_WIDTH//2, text_y), line, font=title_font, fill="#FFFFFF", anchor="mm")
            text_y += 140
            
        # 5. Add "Shop Now" / Call to Action Button
        btn_width = 700
        btn_height = 180
        btn_x1 = (PIN_WIDTH - btn_width) // 2
        btn_y1 = PIN_HEIGHT - 250
        btn_x2 = btn_x1 + btn_width
        btn_y2 = btn_y1 + btn_height
        
        # Draw soft glowing button
        btn_color = "#E60023" # Pinterest Red
        draw.rounded_rectangle([btn_x1, btn_y1, btn_x2, btn_y2], radius=90, fill=btn_color)
        
        cta_font = get_font(80, bold=True)
        draw.text((PIN_WIDTH//2, btn_y1 + 90), "Click to Shop", font=cta_font, fill="#FFFFFF", anchor="mm")
        
        # 6. Price Sticker (Top Right)
        if price:
            # Draw a beautiful yellow circle sticker
            sticker_radius = 180
            sticker_x = PIN_WIDTH - sticker_radius * 2 - 80
            sticker_y = 80
            
            # Drop shadow for sticker
            draw.ellipse([sticker_x+10, sticker_y+10, sticker_x + sticker_radius*2 + 10, sticker_y + sticker_radius*2 + 10], fill=(0,0,0,100))
            # Yellow sticker
            draw.ellipse([sticker_x, sticker_y, sticker_x + sticker_radius*2, sticker_y + sticker_radius*2], fill="#FFD700")
            
            # Price Text
            price_font = get_font(110, bold=True)
            only_font = get_font(50, bold=True)
            
            # Center text in sticker
            center_x = sticker_x + sticker_radius
            center_y = sticker_y + sticker_radius
            
            draw.text((center_x, center_y - 40), "ONLY", font=only_font, fill="#000000", anchor="mm")
            draw.text((center_x, center_y + 30), price, font=price_font, fill="#E60023", anchor="mm")
            
        # 7. Save the image
        final_image = canvas.convert("RGB")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_image.save(output_path, format="PNG", quality=95)
        
        return output_path
        
    except Exception as e:
        print(f"  ⚠️  Image Generation Failed: {e}")
        return image_url

