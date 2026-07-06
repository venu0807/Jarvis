import os
from google import genai
from google.genai import types

def test_gemini_image():
    # Use the user's provided API key
    api_key = "AQ.Ab8RN6Lxt03KUu3PUM4d3zB7dyTi9gezbqymPJRER6baoXZ8Eg"
    
    print("🚀 Initializing Gemini Client...")
    client = genai.Client(api_key=api_key)

    prompt = (
        "A highly viral, futuristic infographic poster for a smartwatch. "
        "The smartwatch has a glowing neon interface and health trackers visible on the screen. "
        "Include text overlays showing 'Smart Features' and a '$49' price tag. "
        "Cinematic lighting, photorealistic, 8k resolution, dramatic dark background."
    )
    
    print(f"🎨 Generating image with prompt: {prompt}")
    
    try:
        # Generate the image using Imagen 3 (the Nano Banana engine)
        response = client.models.generate_images(
            model='imagen-3.0-generate-002',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
                output_mime_type='image/jpeg',
                aspect_ratio='3:4' # Pinterest aspect ratio
            )
        )
        
        output_path = "/mnt/c/Users/Venu/.gemini/antigravity-ide/brain/4b852682-1a1a-435a-b1ed-d025b90d2ffe/test_gemini_output.jpg"
        response.generated_images[0].image.save(output_path)
        print(f"✅ Successfully generated and saved to {output_path}")
        
    except Exception as e:
        print(f"❌ Error generating image: {e}")

if __name__ == "__main__":
    test_gemini_image()
