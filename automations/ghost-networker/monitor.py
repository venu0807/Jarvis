import os
import sys
import json
import time
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Route via JARVIS chokepoint
try:
    JARVIS_HOME = str(Path(__file__).resolve().parent.parent.parent)
    if JARVIS_HOME not in sys.path:
        sys.path.insert(0, JARVIS_HOME)
    from policy import call_llm   # type: ignore
except Exception as e:
    raise SystemExit(
        f"FATAL: ghost-networker cannot import ~/.jarvis/policy: {e!r}. "
    )

TARGETS_FILE = Path(__file__).parent / "targets.json"

try:
    from shared_utils import log_metric
except ImportError:
    sys.path.append(str(Path(__file__).parent.parent))
    from shared_utils import log_metric

def fetch_github_activity(username: str):
    print(f"📡 Fetching GitHub activity for {username}...")
    url = f"https://github.com/{username}.atom"
    try:
        res = requests.get(url, timeout=10)
        if res.status_code != 200:
            return []
            
        root = ET.fromstring(res.text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        recent_events = []
        now = datetime.now(timezone.utc)
        
        for entry in root.findall('atom:entry', ns)[:5]:
            title = entry.find('atom:title', ns).text
            link = entry.find('atom:link', ns).attrib.get('href', '')
            updated_str = entry.find('atom:updated', ns).text
            
            # GitHub atom feeds use ISO 8601 e.g. 2026-07-06T12:00:00Z
            try:
                updated_dt = datetime.strptime(updated_str, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
                hours_ago = (now - updated_dt).total_seconds() / 3600
                
                # Only check events from the last 24 hours
                if hours_ago < 24:
                    recent_events.append({
                        'title': title,
                        'link': link,
                        'time_ago': f"{int(hours_ago)}h ago"
                    })
            except Exception as parse_e:
                pass
                
        return recent_events
    except Exception as e:
        print(f"  ❌ Error fetching {username}: {e}")
        return []

def evaluate_opportunity(event: dict, username: str) -> bool:
    """Uses the local LLM to decide if this event is a networking opportunity."""
    prompt = f"""You are an elite Silicon Valley networking assistant.
    
A high-value tech leader ({username}) just posted this activity on GitHub {event['time_ago']}:
"{event['title']}"

Does this post represent a good networking opportunity where I could jump in and offer value? 
Good opportunities include:
- Opening an issue about a bug (I could fix it)
- Asking for help or recommendations
- Starting a new interesting repository (I could contribute)

Bad opportunities (ignore these):
- Forking a random repo
- Pushing routine commits
- Starring a repository

Respond with ONLY "YES" or "NO", followed by a one-sentence reason why.
"""
    try:
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="local",
            pii_acknowledged=False, # Just public GitHub data
            task_label="ghost_eval"
        )
        response = (result.text or "").strip().upper()
        
        if response.startswith("YES"):
            print(f"  🚨 OPPORTUNITY FOUND for {username}!")
            print(f"  Event: {event['title']}")
            print(f"  Link: {event['link']}")
            print(f"  AI Reason: {response}")
            
            # Log the metric
            log_metric("networking", "Opportunity Found", 1)
            
            return True
        else:
            print(f"  pass: {event['title']}")
            return False
    except Exception as e:
        print(f"  ⚠️ LLM evaluation failed: {e}")
        return False

def main():
    print("👻 Starting Ghost Networker...")
    if not TARGETS_FILE.exists():
        print("  ❌ targets.json not found.")
        return
        
    with open(TARGETS_FILE, "r") as f:
        config = json.load(f)
        
    github_targets = config.get("github_targets", [])
    
    for username in github_targets:
        events = fetch_github_activity(username)
        if not events:
            print(f"  No recent activity for {username}.")
            continue
            
        for event in events:
            # Pre-filter: only ask the LLM if the event type looks somewhat interesting
            # (e.g. Issues, PullRequests, Comments). Ignore simple WatchEvents (Starring) to save GPU time.
            if "starred" in event['title'].lower() or "forked" in event['title'].lower():
                continue
                
            evaluate_opportunity(event, username)

if __name__ == "__main__":
    main()
