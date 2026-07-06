import os
import base64
from openai import OpenAI

def test_nvidia():
    api_key = "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"
    
    print("🚀 Initializing NVIDIA NIM Client...")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    prompt = (
        "A highly viral, futuristic infographic poster for a smartwatch. "
        "The smartwatch has a glowing neon interface and health trackers visible on the screen. "
        "Include text overlays showing 'Smart Features' and a '$49' price tag. "
        "Cinematic lighting, photorealistic, 8k resolution, dramatic dark background."
    )
    
    print(f"🎨 Generating image with prompt: {prompt}")
    
    try:
        response = client.images.generate(
            model="stabilityai/stable-diffusion-3-medium",
            prompt=prompt,
            size="1024x1024",
            response_format="b64_json"
        )
        
        b64_img = response.data[0].b64_json
        
        output_path = "C:\\Users\\Venu\\.gemini\\antigravity-ide\\brain\\4b852682-1a1a-435a-b1ed-d025b90d2ffe\\test_nvidia_output.jpg"
        with open(output_path, "wb") as f:
            f.write(base64.b64decode(b64_img))
            
        print(f"✅ Successfully generated and saved to {output_path}")
        
    except Exception as e:
        print(f"❌ Error generating image: {e}")

if __name__ == "__main__":
    test_nvidia()
