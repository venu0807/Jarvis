import requests
from bs4 import BeautifulSoup
import json
import re

def get_trending_keywords():
    """
    Scrapes Pinterest's Ideas page to find what categories/topics are currently trending.
    """
    print("🔍 Scanning Pinterest for today's top trending niches...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    try:
        # Pinterest Today/Ideas page contains curated trending topics
        response = requests.get("https://www.pinterest.com/ideas/", headers=headers, timeout=15)
        if response.status_code != 200:
            print("⚠️ Failed to fetch Pinterest ideas. Falling back to default trends.")
            return ["college dorm decor", "study desk aesthetic", "kitchen gadgets"]
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract all text that looks like a category/topic
        # Pinterest usually wraps topics in specific h2/h3 tags or specific div classes
        topics = set()
        
        # Look for category links
        for a in soup.find_all('a', href=True):
            if '/ideas/' in a['href'] and len(a['href'].split('/')) > 3:
                topic = a['href'].split('/')[-2].replace('-', ' ')
                if len(topic) > 3 and not any(c.isdigit() for c in topic):
                    topics.add(topic.lower())
                    
        # Also look for any large headers
        for h in soup.find_all(['h2', 'h3']):
            text = h.get_text().strip().lower()
            if 3 < len(text) < 40 and not any(c.isdigit() for c in text):
                topics.add(text)
                
        # Clean up and filter to high-converting physical product niches if possible
        valid_trends = []
        for t in topics:
            if t not in ['home', 'explore', 'ideas', 'pinterest', 'log in', 'sign up', 'about', 'business', "what's new on pinterest", "loading today's picks...", "browse by category"]:
                valid_trends.append(t)
                
        if not valid_trends:
            # Fallback topics if parsing fails
            return ["dorm room aesthetic", "study desk setup", "viral kitchen gadgets", "korean skincare"]
            
        print(f"✅ Found {len(valid_trends)} trending niches on Pinterest!")
        return list(valid_trends)[:15]
        
    except Exception as e:
        print(f"⚠️ Error scraping Pinterest: {e}")
        return ["dorm room aesthetic", "study desk setup", "viral kitchen gadgets"]

if __name__ == '__main__':
    trends = get_trending_keywords()
    print("Live Trends:", trends)
