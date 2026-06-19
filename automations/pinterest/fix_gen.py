import re
with open('generator.py', 'r', encoding='utf-8') as f:
    content = f.read()

new_func = '''def generate_closeup_pin(product_name: str, image_url: str, output_filename: str, price: str = None, tags: str = None) -> str:
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
    
    single_feature = "⭐⭐⭐⭐⭐ 4.8 Rating"
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
'''

# Regex to replace the function
content = re.sub(r'def generate_closeup_pin.*?return output_path\n', new_func, content, flags=re.DOTALL)
with open('generator.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('DONE')
