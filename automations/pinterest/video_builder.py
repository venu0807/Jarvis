import os
from PIL import Image
import imageio
import numpy as np

def generate_video_pin(image_path: str, output_path: str, duration_sec: int = 5, fps: int = 30) -> str:
    """
    Takes a static generated pin and creates a slow-zoom video pin encoded in H.264.
    Returns the output_path of the generated .mp4 file.
    """
    try:
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Source image not found: {image_path}")

        # Read image using Pillow
        img = Image.open(image_path).convert("RGB")
        width, height = img.size
        
        total_frames = duration_sec * fps
        zoom_factor = 1.0
        max_zoom = 1.10
        zoom_step = (max_zoom - 1.0) / total_frames

        writer = imageio.get_writer(output_path, fps=fps, codec='libx264', format='FFMPEG')
        
        for i in range(total_frames):
            # Calculate zoom
            h_zoomed = int(height / zoom_factor)
            w_zoomed = int(width / zoom_factor)

            y1 = (height - h_zoomed) // 2
            y2 = y1 + h_zoomed
            x1 = (width - w_zoomed) // 2
            x2 = x1 + w_zoomed

            # Crop and resize
            cropped = img.crop((x1, y1, x2, y2))
            frame = cropped.resize((width, height), Image.Resampling.LANCZOS)
            
            # Convert to numpy array for imageio
            writer.append_data(np.array(frame))
            
            zoom_factor += zoom_step

        writer.close()
        return output_path
    except Exception as e:
        print(f"  ⚠️  Video Generation Failed: {e}")
        return image_path  # Fallback to static image path
