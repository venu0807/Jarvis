import os
from PIL import Image
import PIL.Image
if not hasattr(PIL.Image, 'ANTIALIAS'):
    PIL.Image.ANTIALIAS = PIL.Image.Resampling.LANCZOS

# Try to import moviepy, but provide a fallback if not available
try:
    # Try the modern moviepy 2.x import structure
    try:
        from moviepy.video.VideoClip import ImageClip
        from moviepy.video.compositing.concatenate import concatenate_videoclips
        MOVIEPY_AVAILABLE = True
    except ImportError:
        # Fallback to older moviepy 1.x import structure
        from moviepy.editor import ImageClip, concatenate_videoclips
        MOVIEPY_AVAILABLE = True
except ImportError as e:
    MOVIEPY_AVAILABLE = False
    # Create dummy classes/functions to avoid NameError
    class ImageClip:
        def __init__(self, *args, **kwargs):
            pass
        def set_duration(self, *args, **kwargs):
            return self
        def resize(self, *args, **kwargs):
            return self
        def close(self):
            pass
    def concatenate_videoclips(*args, **kwargs):
        return ImageClip()
    print(f"Warning: moviepy not available ({e}). Video collage generation will be disabled.")

def generate_flash_collage(image_paths: list, output_path: str, fps: int = 30, duration_per_image: float = 1.5) -> str:
    """
    Takes a list of static generated pins and creates a fast-paced collage video.
    Returns the output_path of the generated .mp4 file.
    """
    if not MOVIEPY_AVAILABLE:
        print("  ⚠️  Video collage generation skipped (moviepy not available)")
        # Return the first image as fallback
        return image_paths[0] if image_paths and len(image_paths) > 0 else None
        
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