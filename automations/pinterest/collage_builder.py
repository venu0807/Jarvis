import os
from PIL import Image, ImageDraw
import random
from image_builder import get_font, BG_COLORS, TEXT_COLORS, download_image

PIN_WIDTH = 1000
PIN_HEIGHT = 1500

def generate_collage_pin(image_urls: list, title: str, category: str, output_path: str) -> str:
    """
    Generates a 2x2 collage pin from exactly 4 image URLs.
    """
    try:
        bg_color = BG_COLORS.get(category, BG_COLORS["default"])
        text_color = TEXT_COLORS.get(category, TEXT_COLORS["default"])
        canvas = Image.new("RGBA", (PIN_WIDTH, PIN_HEIGHT), bg_color)
        
        # We need to create a 2x2 grid in the center
        # Grid area is say 800x800
        grid_size = 800
        cell_size = 380
        padding = 40
        start_x = (PIN_WIDTH - grid_size) // 2
        start_y = (PIN_HEIGHT - grid_size) // 2 + 50
        
        for idx, url in enumerate(image_urls[:4]):
            img = download_image(url)
            # Crop to square
            min_dim = min(img.width, img.height)
            left = (img.width - min_dim)/2
            top = (img.height - min_dim)/2
            img = img.crop((left, top, left + min_dim, top + min_dim))
            img = img.resize((cell_size, cell_size), Image.Resampling.LANCZOS)
            
            row = idx // 2
            col = idx % 2
            
            paste_x = int(start_x + col * (cell_size + padding))
            paste_y = int(start_y + row * (cell_size + padding))
            
            if "A" in img.getbands():
                canvas.paste(img, (paste_x, paste_y), img)
            else:
                canvas.paste(img, (paste_x, paste_y))
        
        # Add Text Overlay
        draw = ImageDraw.Draw(canvas)
        
        prefix_font = get_font(45)
        draw.text((PIN_WIDTH//2, 120), "✨ ULTIMATE STARTER PACK ✨", font=prefix_font, fill=text_color, anchor="mm")
        
        title_font = get_font(60)
        draw.text((PIN_WIDTH//2, 220), title, font=title_font, fill=text_color, anchor="mm")
        
        footer_font = get_font(35)
        draw.text((PIN_WIDTH//2, PIN_HEIGHT - 120), "Click to shop the full aesthetic! 🛍️", font=footer_font, fill=text_color, anchor="mm")
        
        final_image = canvas.convert("RGB")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        final_image.save(output_path, format="PNG", quality=95)
        
        return output_path
    except Exception as e:
        print(f"  ⚠️  Collage Generation Failed: {e}")
        return None
