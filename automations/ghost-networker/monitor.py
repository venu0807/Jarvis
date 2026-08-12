import os
import sys
import json
import time
import requests
from datetime import datetime, timezone, timedelta
from pathlib import Path
try:
    from defusedxml import ElementTree as ET  # XXE/billion-laughs safe
except ImportError:
    import xml.etree.ElementTree as ET

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


def _parse_github_date(updated_str: str):
    """GitHub .atom 'updated' field switched format ~2026. Older entries:
    '2026-07-06T12:00:00Z'. Current: '2026-08-10 16:15:16 UTC'. Parse both.
    Returns tz-aware datetime or None."""
    if not updated_str:
        return None
    try:
        return datetime.fromisoformat(updated_str.replace("Z", "+00:00"))
    except ValueError:
        pass
    try:
        return datetime.strptime(updated_str, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=timezone.utc)
    except ValueError:
        return None

try:
    from shared_utils import log_metric, retry, atomic_write_text
except ImportError:
    sys.path.append(str(Path(__file__).parent.parent))
    from shared_utils import log_metric, retry, atomic_write_text

@retry(max_attempts=3, delay=2.0, backoff=2.0, exceptions=(requests.RequestException, ET.ParseError))
def _atom_fetch(username: str) -> str:
    res = requests.get(f"https://github.com/{username}.atom", timeout=15)
    res.raise_for_status()
    return res.text


def fetch_github_activity(username: str):
    print(f"📡 Fetching GitHub activity for {username}...")
    try:
        xml_text = _atom_fetch(username)
        root = ET.fromstring(xml_text)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        recent_events = []
        now = datetime.now(timezone.utc)

        for entry in root.findall('atom:entry', ns)[:5]:
            title = entry.find('atom:title', ns).text
            link = entry.find('atom:link', ns).attrib.get('href', '')
            updated_str = entry.find('atom:updated', ns).text
            
            # GitHub atom feeds used to emit ISO 8601 "2026-07-06T12:00:00Z"; they
            # now emit "2026-08-10 16:15:16 UTC". Try both before giving up — and
            # DO NOT silently swallow parse failures, or the bot looks "no activity".
            updated_dt = _parse_github_date(updated_str)
            if updated_dt is None:
                print(f"  ⚠️ {username}: unparsable feed date {updated_str!r}")
                continue
            hours_ago = (now - updated_dt).total_seconds() / 3600

            # Only check events from the last 24 hours
            if hours_ago < 24:
                recent_events.append({
                    'title': title,
                    'link': link,
                    'time_ago': f"{int(hours_ago)}h ago"
                })
                
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

SEEN_FILE = Path(__file__).parent / ".seen_events.json"


def _load_seen() -> set:
    try:
        if SEEN_FILE.exists():
            return set(json.loads(SEEN_FILE.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        pass
    return set()


def _save_seen(seen: set):
    atomic_write_text(str(SEEN_FILE), json.dumps(sorted(seen), indent=2))


def main():
    print("👻 Starting Ghost Networker...")
    if not TARGETS_FILE.exists():
        print("  ❌ targets.json not found.")
        return

    with open(TARGETS_FILE, "r") as f:
        config = json.load(f)

    github_targets = config.get("github_targets", [])
    seen = _load_seen()

    for username in github_targets:
        events = fetch_github_activity(username)
        if not events:
            print(f"  No recent activity for {username}.")
            continue

        new_events = [e for e in events if e["link"] not in seen]
        if not new_events:
            print(f"  {username}: no NEW events (all already evaluated).")
            continue

        for event in new_events:
            # Pre-filter: only ask the LLM if the event type looks somewhat interesting
            # (e.g. Issues, PullRequests, Comments). Ignore simple WatchEvents (Starring) to save GPU time.
            if "starred" in event['title'].lower() or "forked" in event['title'].lower():
                continue

            evaluate_opportunity(event, username)
            seen.add(event["link"])

    _save_seen(seen)

if __name__ == "__main__":
    main()
