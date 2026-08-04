import json
import requests
import sys

OLLAMA_API_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "phi4-mini"

def generate_linkedin_post(stories):
    prompt = "You are a top-tier tech influencer on LinkedIn. Write a highly engaging, viral LinkedIn post summarizing the following top tech news stories. Use emojis, keep it professional but exciting, and ask a question at the end to drive engagement.\n\n"
    for idx, story in enumerate(stories, 1):
        prompt += f"{idx}. {story['title']} - {story['url']}\n"
    
    payload = {
        "model": MODEL_NAME,
        "prompt": prompt,
        "stream": False
    }
    
    print(f"Sending prompt to local Ollama ({MODEL_NAME})...")
    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get('response', '')
    except Exception as e:
        print(f"Failed to connect to Ollama: {e}")
        sys.exit(1)

if __name__ == "__main__":
    try:
        with open('scraped_news.json', 'r') as f:
            stories = json.load(f)
    except FileNotFoundError:
        print("scraped_news.json not found. Run scraper.py first.")
        sys.exit(1)
        
    post_content = generate_linkedin_post(stories)
    print("\n--- GENERATED POST ---")
    print(post_content)
    print("----------------------\n")
    
    with open('post.txt', 'w', encoding='utf-8') as f:
        f.write(post_content)
    
    print("Post saved to post.txt")
