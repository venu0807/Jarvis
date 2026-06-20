import os
import time
import random
import pandas as pd
from bs4 import BeautifulSoup
from jarvis_browser import SyncBrowser
from amazon_scraper import scrape_amazon

CSV_FILE = "data.csv"
USER_DATA_DIR = os.path.join(os.environ.get("LOCALAPPDATA", "C:\\Users\\Venu\\AppData\\Local"), "AmazonBot")

def get_pinterest_trends():
    print('Launching Stealth Browser to scrape Pinterest Trends...')
    keywords = []
    with SyncBrowser(headless=True) as browser:
        context = browser.new_context()
        page = context.new_page()
        try:
            page.goto('https://trends.pinterest.com/', timeout=60000)
            print("  o~Z Waiting for trends to load...")
            time.sleep(5)
            
            text_content = page.content()
            soup = BeautifulSoup(text_content, 'html.parser')
            texts = soup.get_text(separator='\n').split('\n')
            
            for t in texts:
                t = t.strip()
                # Filter out UI text, short words, and countries
                ignore_list = ['Region', 'Trends', 'Log in', 'Sign up', 'Learn more', 'Beta', 'View the full list', 'Any questions?']
                if len(t) > 5 and len(t) < 40 and t not in ignore_list and '%' not in t and '(' not in t:
                    keywords.append(t)
        except Exception as e:
            print(f"  s,?  Error fetching trends: {e}")
            
    # Deduplicate and remove common false positives
    unique_keywords = list(set(keywords))
    # Usually the top trends are listed first. Pick 5 random ones to test.
    if unique_keywords:
        random.shuffle(unique_keywords)
        return unique_keywords[:5]
    return ["dorm room aesthetic", "summer fashion"]

if __name__ == "__main__":
    print('Starting Pinterest Trends Extension...')
    trends = get_pinterest_trends()
    print(f'\n Found Live Trends: {trends}')
    
    # Format these into NICHES format for amazon scraper
    niches = []
    for trend in trends:
        niches.append({
            "query": trend,
            "board": "Trending Now",
            "category": "trends",
            "tags": "#trending #amazonfinds #pinteresttrends"
        })
    
    print('\n Sending trends to Amazon Scraper to find matching products...')
    scrape_amazon(niches)
    print('\n SUCCESS! Trends have been successfully appended to data.csv!\n  Your scheduled Pinterest bot will naturally pick these up during its next run!')
