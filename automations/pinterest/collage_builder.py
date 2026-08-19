"""
Collage builder for Pinterest automation
Creates image collages from multiple product images
"""

import os
import random
from PIL import Image

def generate_collage_pin(image_urls, title, category, output_path):
    """
    Generate a collage pin from multiple images
    
    Args:
        image_urls: List of image URLs or file paths
        title: Title for the collage
        category: Product category
        output_path: Where to save the collage image
        
    Returns:
        str: Path to the generated collage image
    """
    try:
        print(f"🎨 Generating collage pin: {title[:30]}...")
        
        # Create a blank canvas (Pinterest standard 2:3 ratio)
        canvas_width, canvas_height = 1000, 1500
        collage = Image.new('RGB', (canvas_width, canvas_height), color='white')
        
        # Load and resize images
        images = []
        for i, img_url in enumerate(image_urls[:4]):  # Max 4 images for collage
            try:
                # Handle both local file paths and URLs
                if img_url.startswith('http'):
                    # In a real implementation, we'd download the image
                    # For now, create a placeholder colored image
                    img = Image.new('RGB', (300, 300), color=(
                        random.randint(100, 255),
                        random.randint(100, 255), 
                        random.randint(100, 255)
                    ))
                else:
                    # Local file path
                    if os.path.exists(img_url):
                        img = Image.open(img_url).convert('RGB')
                    else:
                        # File doesn't exist, create placeholder
                        img = Image.new('RGB', (300, 300), color=(
                            random.randint(100, 255),
                            random.randint(100, 255), 
                            random.randint(100, 255)
                        ))
                
                # Resize image to fit in collage quadrant
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                images.append(img)
            except Exception as e:
                print(f"  ⚠️  Could not load image {img_url}: {e}")
                # Create a placeholder image
                img = Image.new('RGB', (300, 300), color=(
                    random.randint(100, 255),
                    random.randint(100, 255), 
                    random.randint(100, 255)
                ))
                img.thumbnail((400, 400), Image.Resampling.LANCZOS)
                images.append(img)
        
        if not images:
            print("  ❌ No valid images for collage")
            return None
            
        # Arrange images in a grid
        # 2x2 grid for 4 images, adjust for fewer
        if len(images) == 1:
            # Single image centered
            x_offset = (canvas_width - images[0].width) // 2
            y_offset = (canvas_height - images[0].height) // 2
            collage.paste(images[0], (x_offset, y_offset))
        elif len(images) == 2:
            # Side by side
            x_offset = (canvas_width - images[0].width - images[1].width) // 3
            y_offset = (canvas_height - max(img.height for img in images)) // 2
            collage.paste(images[0], (x_offset, y_offset))
            collage.paste(images[1], (x_offset + images[0].width + x_offset, y_offset))
        elif len(images) == 3:
            # Two on top, one on bottom
            top_width = images[0].width + images[1].width + 20  # 20px spacing
            x_offset = (canvas_width - top_width) // 2
            y_offset = 100
            collage.paste(images[0], (x_offset, y_offset))
            collage.paste(images[1], (x_offset + images[0].width + 20, y_offset))
            
            # Bottom image centered
            x_offset = (canvas_width - images[2].width) // 2
            y_offset = 100 + images[0].height + 20
            collage.paste(images[2], (x_offset, y_offset))
        else:
            # 2x2 grid for 4 images
            margin = 50
            cell_width = (canvas_width - 2 * margin) // 2
            cell_height = (canvas_height - 2 * margin) // 2
            
            for idx, img in enumerate(images[:4]):
                row = idx // 2
                col = idx % 2
                x_offset = margin + col * cell_width + (cell_width - img.width) // 2
                y_offset = margin + row * cell_height + (cell_height - img.height) // 2
                collage.paste(img, (x_offset, y_offset))
        
        # Add title overlay (semi-transparent background for text readability)
        from PIL import ImageDraw, ImageFont
        draw = ImageDraw.Draw(collage)
        
        # Dark overlay at bottom for text
        overlay_height = 200
        overlay = Image.new('RGB', (canvas_width, overlay_height), color=(0, 0, 0))
        overlay.putalpha(128)  # Semi-transparent
        collage.paste(overlay, (0, canvas_height - overlay_height), overlay)
        
        # Add title text
        try:
            # Try to use a nice font, fall back to default
            font = ImageFont.truetype("arial.ttf", 36)
        except IOError:
            font = ImageFont.load_default()
            
        # Wrap title text
        words = title.split()
        lines = []
        current_line = []
        for word in words:
            test_line = ' '.join(current_line + [word])
            # Approximate text width check
            if len(test_line) * 20 < canvas_width - 40:  # Rough estimate
                current_line.append(word)
            else:
                lines.append(' '.join(current_line))
                current_line = [word]
        if current_line:
            lines.append(' '.join(current_line))
        
        # Draw lines
        y_offset = canvas_height - overlay_height + 20
        line_height = 40
        for line in lines[:3]:  # Max 3 lines
            text_width = draw.textlength(line, font=font) if hasattr(draw, 'textlength') else len(line) * 20
            x_offset = (canvas_width - text_width) // 2
            draw.text((x_offset, y_offset), line, fill=(255, 255, 255), font=font)
            y_offset += line_height
        
        # Save the collage
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        collage.save(output_path, "JPEG", quality=95)
        print(f"  ✅ Collage saved: {output_path}")
        return output_path
        
    except Exception as e:
        print(f"  ❌ Collage generation failed: {e}")
        return None