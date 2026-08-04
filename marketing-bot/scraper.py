import requests
import json
import sys

def get_top_stories(limit=3):
    print(f"Fetching top {limit} stories from HackerNews...")
    # Get top 500 story IDs
    response = requests.get('https://hacker-news.firebaseio.com/v0/topstories.json')
    if response.status_code != 200:
        print("Failed to fetch HN top stories.")
        sys.exit(1)
        
    story_ids = response.json()[:limit]
    
    stories = []
    for story_id in story_ids:
        story_res = requests.get(f'https://hacker-news.firebaseio.com/v0/item/{story_id}.json')
        if story_res.status_code == 200:
            story = story_res.json()
            stories.append({
                'title': story.get('title'),
                'url': story.get('url', f"https://news.ycombinator.com/item?id={story_id}"),
                'score': story.get('score')
            })
            
    return stories

if __name__ == "__main__":
    stories = get_top_stories()
    with open('scraped_news.json', 'w') as f:
        json.dump(stories, f, indent=2)
    print(f"Successfully scraped {len(stories)} stories and saved to scraped_news.json")
