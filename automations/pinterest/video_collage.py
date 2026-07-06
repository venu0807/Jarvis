import os
from PIL import Image
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

from moviepy.editor import ImageClip, concatenate_videoclips

def generate_flash_collage(image_paths: list, output_path: str, fps: int = 30, duration_per_image: float = 1.5) -> str:
    """
    Takes a list of static generated pins and creates a fast-paced collage video.
    Returns the output_path of the generated .mp4 file.
    """
    try:
        clips = []
        for img_path in image_paths:
            if not os.path.exists(img_path):
                print(f"  ⚠️ Skipping missing image: {img_path}")
                continue
            
            # Load the clip, set duration, and ensure it fits Pinterest dimensions (1000x1500)
            clip = ImageClip(img_path).set_duration(duration_per_image).resize(width=1000, height=1500)
            clips.append(clip)
            
        if not clips:
            raise ValueError("No valid images provided for collage.")

        print(f"  🎬 Stitching {len(clips)} images into a fast collage...")
        
        # Concatenate them using "compose" to handle any slight size variations gracefully
        final_clip = concatenate_videoclips(clips, method="compose")
        final_clip.write_videofile(output_path, fps=fps, codec='libx264', audio=False, logger=None)
        
        final_clip.close()
        for c in clips:
            c.close()
            
        return output_path
    except Exception as e:
        print(f"  ⚠️  Collage Video Generation Failed: {e}")
        # Fallback to the first image in the list if video generation fails
        return image_paths[0] if image_paths else None
