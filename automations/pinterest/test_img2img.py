import os
import base64
import requests
import sys

def test_img2img(img_path, out_path):
    api_key = os.environ.get("NVIDIA_API_KEY")
    if not api_key:
        print("Error: NVIDIA_API_KEY environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    url = "https://ai.api.nvidia.com/v1/genai/stabilityai/stable-diffusion-xl-base-1.0"
    # wait, sd-xl image-to-image requires a different endpoint or payload
    # Let's try the requests way for NIM.
    
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # NIM stable-diffusion-xl payload
    payload = {
        "text_prompts": [
            {
                "text": "A beautiful aesthetic lifestyle photograph of this product on a wooden desk. cozy ambient lighting, 8k resolution, photorealistic",
                "weight": 1
            }
        ],
        "init_image": img_b64,
        "image_strength": 0.5,
        "cfg_scale": 7,
        "samples": 1,
        "steps": 30
    }

    print("Sending request...")
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        data = response.json()
        if 'artifacts' in data:
            out_b64 = data['artifacts'][0]['base64']
            with open(out_path, "wb") as f:
                f.write(base64.b64decode(out_b64))
            print(f"Saved to {out_path}")
        else:
            print("Failed:", data)
    else:
        print("HTTP Error:", response.status_code, response.text)

if __name__ == "__main__":
    test_img2img(sys.argv[1], sys.argv[2])
