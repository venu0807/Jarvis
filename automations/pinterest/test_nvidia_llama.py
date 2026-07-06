import os
from openai import OpenAI

def test_nvidia_llama():
    api_key = "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"
    
    print("🚀 Initializing NVIDIA NIM Client...")
    client = OpenAI(
        base_url="https://integrate.api.nvidia.com/v1",
        api_key=api_key
    )

    try:
        response = client.chat.completions.create(
            model="meta/llama-3.1-8b-instruct",
            messages=[{"role": "user", "content": "Hello!"}]
        )
        print("✅ Success! Response:")
        print(response.choices[0].message.content)
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_nvidia_llama()
