"""scraper.py — Scrape LinkedIn for recent job posts.

Fixes applied:
- #2: Use the persistent-context API correctly — `launch_persistent_context`
  returns a context; pages are accessed via `context.pages[0]` or
  `context.new_page()` (synchronous Playwright supports both now).
- #6: Polling-based checkpoint wait (5s × up to 36 = 180s) instead of a flat
  60s sleep. SMS-OTP checkpoints need >60s; we now wait up to 3 min.
- Rate-limit humanisation: random sleep between scroll + extraction so we
  don't look like a 1 Hz bot.
"""

import os
import random
import urllib.parse
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
from jarvis_browser import SyncBrowser

TIMEOUT_MS = 60_000
HUMAN_MIN_SLEEP = 2.0
HUMAN_MAX_SLEEP = 5.0
CHECKPOINT_MAX_WAIT_S = 180      # SMS/email OTPs can take 2-3 min
CHECKPOINT_POLL_S = 5


def _wait_for_checkpoint(page, max_wait_s: int = CHECKPOINT_MAX_WAIT_S) -> bool:
    """Poll until LinkedIn checkpoint URL clears. Returns True when cleared."""
    waited = 0
    while waited < max_wait_s:
        url = page.url
        # URLs that mean "still on a challenge": /checkpoint, /challenge, /authwall
        if not any(seg in url for seg in ("/checkpoint", "/challenge", "/authwall")):
            return True
        page.wait_for_timeout(CHECKPOINT_POLL_S * 1000)
        waited += CHECKPOINT_POLL_S
        print(f"  ⏳ checkpoint still active, {waited}/{max_wait_s}s...")
    print("  ⚠ checkpoint wait timed out")
    return False

def scrape_recruiter_profile(profile_url: str) -> str:
    """Uses Playwright to navigate to a recruiter's profile and extract their About section and recent activity."""
    if not profile_url or "linkedin.com/in/" not in profile_url:
        return ""
        
    print(f"  🕵️ Scraping recruiter profile: {profile_url}")
    user_data_dir = os.path.join(os.getcwd(), "playwright_profile")
    
    bio_text = ""
    try:
        with SyncBrowser(headless=False) as browser_mgr:
            context = browser_mgr.launch_persistent(user_data_dir)
            page = context.pages[0] if context.pages else context.new_page()
            
            page.goto(profile_url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            page.wait_for_timeout(random.randint(3000, 5000))
            
            if any(seg in page.url for seg in ("/checkpoint", "/challenge", "/authwall")):
                print("  ⚠ Checkpoint hit while scraping profile. Skipping to avoid lock.")
                return ""
                
            # Scroll to load sections
            page.evaluate("window.scrollBy(0, 800)")
            page.wait_for_timeout(2000)
            
            # Try to grab the "About" section
            about_section = page.query_selector('div#about ~ div .display-flex')
            if about_section:
                bio_text += "ABOUT ME:\n" + about_section.inner_text().strip() + "\n\n"
                
            # Try to grab recent activity
            activity_section = page.query_selector_all('div.feed-shared-update-v2')
            if activity_section:
                bio_text += "RECENT POSTS:\n"
                for act in activity_section[:2]:
                    bio_text += act.inner_text().strip() + "\n---\n"
                    
            print(f"  ✅ Extracted {len(bio_text)} chars of bio/activity.")
            return bio_text
    except Exception as e:
        print(f"  ⚠ Failed to scrape profile: {e}")
        return ""


def scrape_linkedin_posts(job_role):
    """Scrape LinkedIn for recent job posts based on keywords."""
    username = os.environ.get("LINKEDIN_USERNAME")
    password = os.environ.get("LINKEDIN_PASSWORD")

    posts_data = []
    user_data_dir = os.path.join(os.getcwd(), "playwright_profile")

    try:
        with SyncBrowser(headless=False) as browser_mgr:
            print("Launching browser with persistent context...")
            context = browser_mgr.launch_persistent(user_data_dir)

            # Pickup existing page from the persistent profile
            # (no fresh sign-in needed when cookies are still valid),
            # else create one.
            if context.pages:
                page = context.pages[0]
            else:
                page = context.new_page()

            print("Navigating to LinkedIn feed...")
            try:
                page.goto("https://www.linkedin.com/feed/", wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                page.wait_for_timeout(3000)
            except Exception as e:
                print(f"  ⚠ feed load slow: {e}")

            # If we are redirected to login, perform login
            if "login" in page.url or "signup" in page.url or "session/new" in page.url:
                print("Not logged in. Attempting login...")
                if username and password:
                    try:
                        page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=TIMEOUT_MS)
                        if page.locator("id=username").count() > 0:
                            page.fill("id=username", username, timeout=10000)
                            page.fill("id=password", password, timeout=10000)
                        else:
                            page.fill("id=session_key", username, timeout=10000)
                            page.fill("id=session_password", password, timeout=10000)
                        page.click("button[type='submit']")
                        # Wait for the redirect away from /login
                        page.wait_for_url(lambda u: "login" not in u, timeout=30000)
                    except Exception as e:
                        print(f"Automated login failed or interrupted: {e}")
                        print("Please login manually in the browser window...")
                        page.wait_for_timeout(90000)
                else:
                    print("No credentials provided in .env, please login manually.")
                    page.wait_for_timeout(90000)

            # Fixed #6 — polling-based checkpoint wait (was a flat 60s sleep)
            if any(seg in page.url for seg in ("/checkpoint", "/challenge", "/authwall")):
                print("Security checkpoint detected. Please complete it manually.")
                if not _wait_for_checkpoint(page):
                    print("Could not clear checkpoint within timeout — aborting scrape.")
                    context.close()
                    return posts_data

            keywords = f'"{job_role}"'
            encoded_keywords = urllib.parse.quote(keywords)
            search_url = f"https://www.linkedin.com/search/results/content/?keywords={encoded_keywords}&sortBy=%22date_posted%22"

            print(f"Navigating to search results for: {job_role}...")
            try:
                page.goto(search_url, wait_until="domcontentloaded", timeout=TIMEOUT_MS)
            except Exception as e:
                print(f"  ⚠ search load slow: {e}")
            # Humanise: random delay instead of a fixed 5s
            page.wait_for_timeout(random.randint(3000, 6000))

            # Scroll down to ensure posts load (humanised)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            # Multiple small scrolls look more human than one big one
            for _ in range(random.randint(2, 4)):
                page.evaluate(f"window.scrollBy(0, {random.randint(250, 600)})")
                page.wait_for_timeout(random.randint(800, 1500))

            try:
                page.wait_for_selector("main#workspace, div.search-results-container", timeout=15000)
            except Exception:
                print("Timed out waiting for posts to load. Page might be slow or empty.")

            post_elements = page.query_selector_all('div[role="listitem"]')
            if not post_elements:
                post_elements = page.query_selector_all(
                    "div[data-urn^='urn:li:activity:'], li.reusable-search__result-container"
                )

            print(f"Found {len(post_elements)} posts on the page.")

            # Cap at 8 per role (was hardcoded [:5]) — still safe but a bit more headroom
            max_posts = int(os.environ.get("MAX_POSTS_PER_ROLE", "8"))
            for idx, post in enumerate(post_elements[:max_posts]):
                # Humanise the per-post delay
                page.wait_for_timeout(int(random.randint(1500, 3500)))
                try:
                    raw_text = post.inner_text()
                    if not raw_text.strip():
                        continue
                    # Backoff every 3 posts to look more human
                    if idx > 0 and idx % 3 == 0:
                        page.wait_for_timeout(int(random.randint(4000, 9000)))

                    lines = [line.strip() for line in raw_text.split('\n') if line.strip()]
                    if lines and lines[0] == "Feed post":
                        lines = lines[1:]
                    if len(lines) < 3:
                        continue

                    name = lines[0].split('•')[0].strip()
                    company_or_headline = lines[1]

                    text_start_idx = 2
                    for i, line in enumerate(lines[:5]):
                        if '•' in line and ('h' in line or 'm' in line or 'd' in line):
                            text_start_idx = i + 1
                            break

                    post_content = "\n".join(lines[text_start_idx:])
                    post_content = post_content.replace("Like\nComment\nRepost\nSend", "")

                    has_link = "http" in post_content or "www." in post_content
                    
                    profile_link = post.query_selector("a.app-aware-link")
                    profile_url = profile_link.get_attribute("href") if profile_link else ""
                    if profile_url and "?" in profile_url:
                        profile_url = profile_url.split("?")[0] # Clean tracking params

                    posts_data.append({
                        "text": post_content,
                        "name": name,
                        "company": company_or_headline,
                        "has_link": has_link,
                        "link": post_content,
                        "profile_url": profile_url,
                    })
                except Exception as e:
                    print(f"Error parsing a post: {e}")


    except Exception as e:
        if "TargetClosedError" in str(type(e)) or "closed" in str(e).lower():
            print("\n[!] ERROR: The browser window was closed manually!")
            print("    DO NOT close Chromium while the bot runs.\n")
        else:
            print(f"\n[!] An unexpected error occurred in Playwright: {e}\n")

    return posts_data
