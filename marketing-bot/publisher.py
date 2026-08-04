import sys
import requests

N8N_WEBHOOK_URL = "http://localhost:5678/webhook/linkedin-publisher"

def publish_to_n8n(post_content):
    print(f"Sending post to n8n webhook: {N8N_WEBHOOK_URL}")
    payload = {
        "text": post_content
    }
    try:
        response = requests.post(N8N_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print("Successfully triggered n8n workflow!")
    except Exception as e:
        print(f"Failed to send to n8n: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        with open('post.txt', 'r', encoding='utf-8') as f:
            post_content = f.read()
    except FileNotFoundError:
        print("post.txt not found. Run llm_summarizer.py first.")
        sys.exit(1)
        
    publish_to_n8n(post_content)
