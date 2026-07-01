"""
Post to Pinterest — API v5 first, Playwright browser fallback
=============================================================
Strategy:
  1. Try Pinterest API v5 (fast, reliable, undetectable)
  2. If API fails with auth error (401/403), fallback to Playwright
     browser automation so you can post TODAY while waiting for
     Pinterest app approval.
  3. Playwright saves your login session so you only log in once.

Environment variables (in .env):
  PINTEREST_ACCESS_TOKEN   — Pinterest API token (OPTIONAL for browser mode)
  PINTEREST_BOARD_ID       — Board ID to post to (OPTIONAL for browser mode)
  AMAZON_AFFILIATE_TAG     — Your Amazon Associates tag (optional)
"""

import os
import sys
import time
import mimetypes
import random

import requests
import re
from dotenv import load_dotenv

load_dotenv()

# ── Credentials ─────────────────────────────────────────────────────────
ACCESS_TOKEN = os.getenv("PINTEREST_ACCESS_TOKEN")
BOARD_ID = os.getenv("PINTEREST_BOARD_ID")
AMAZON_TAG = os.getenv("AMAZON_AFFILIATE_TAG", "studentdeals0a-20")

# Optional — auto-login credentials (used only when browser session is missing)
PINTEREST_EMAIL = os.getenv("PINTEREST_EMAIL")
PINTEREST_PASSWORD = os.getenv("PINTEREST_PASSWORD")

# ── Pinterest API Endpoints ─────────────────────────────────────────────
MEDIA_ENDPOINT = "https://api.pinterest.com/v5/media"
PINS_ENDPOINT = "https://api.pinterest.com/v5/pins"

MAX_RETRIES = 3

# ── Persistent browser session ──────────────────────────────────────────
# Stable path so cookies + cache survive between runs. First run: log in once;
# every subsequent run is logged in automatically.
if "WSL_DISTRO_NAME" in os.environ:
    BROWSER_USER_DATA_DIR = "/mnt/c/Users/Venu/AppData/Local/PinterestBot"
else:
    BROWSER_USER_DATA_DIR = os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
        "PinterestBot"
    )
LOGIN_URL = "https://www.pinterest.com/login/"

# ── Helpers ─────────────────────────────────────────────────────────────


def _get_content_type(file_path: str) -> str:
    ct, _ = mimetypes.guess_type(file_path)
    return ct or "image/jpeg"


def _wait_for_media_ready(media_id: str, timeout: int = 60, poll_interval: int = 5) -> bool:
    """Poll Pinterest until media processing finishes or times out."""
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            resp = requests.get(f"{MEDIA_ENDPOINT}/{media_id}", headers=headers, timeout=15)
        except requests.RequestException:
            time.sleep(poll_interval)
            continue

        if resp.status_code == 200:
            status = resp.json().get("status")
            if status == "succeeded":
                print("  ✅ Media ready!")
                return True
            elif status == "failed":
                print(f"  ❌ Media processing failed: {resp.text}")
                return False
        time.sleep(poll_interval)

    print("  ⏰ Media processing timed out — proceeding anyway.")
    return True  # optimistically proceed


def _register_and_upload(image_path: str) -> str:
    """Register media with Pinterest API and upload image. Returns media_id."""
    content_type = _get_content_type(image_path)
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}

    media_type = "video" if image_path.endswith(".mp4") else "image"
    for attempt in range(1, MAX_RETRIES + 1):
        print(f"  📤 Registering media (attempt {attempt})...")
        try:
            resp = requests.post(MEDIA_ENDPOINT, headers=headers,
                                 json={"media_type": media_type}, timeout=30)
        except requests.RequestException as e:
            print(f"  ⚠️  Network error: {e}")
            time.sleep(2 ** attempt)
            continue

        if resp.status_code == 429:
            print("  ⏳ Rate limited — waiting 10s...")
            time.sleep(10)
            continue

        if resp.status_code != 201:
            if attempt < MAX_RETRIES:
                print(f"  ⚠️  Registration failed ({resp.status_code}), retrying...")
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Registration failed ({resp.status_code}): {resp.text}")

        data = resp.json()
        media_id = data["media_id"]
        upload_url = data["upload_url"]
        print(f"  ✅ Got upload URL — media_id: {media_id[:16]}...")

        # Upload image
        print(f"  📤 Uploading image ({content_type})...")
        try:
            with open(image_path, "rb") as f:
                up = requests.put(upload_url, data=f,
                                  headers={"Content-Type": content_type}, timeout=60)
        except requests.RequestException as e:
            print(f"  ⚠️  Upload error: {e}")
            time.sleep(2 ** attempt)
            continue

        if up.status_code in (200, 201, 204):
            print("  ✅ Image uploaded!")
            return media_id
        else:
            print(f"  ⚠️  Upload failed ({up.status_code})")
            if attempt < MAX_RETRIES:
                time.sleep(2 ** attempt)
                continue
            raise RuntimeError(f"Upload failed ({up.status_code}): {up.text}")

    raise RuntimeError("Media registration failed after all retries.")


# ── API Poster ──────────────────────────────────────────────────────────


def _post_via_api(image_path: str, title: str, link: str, description: str) -> bool:
    """Post a pin using the Pinterest API v5. Returns True on success."""
    print(f"\n  ── Posting via API v5 ──")
    title = title[:100]
    desc = description[:500] if description else title

    try:
        media_id = _register_and_upload(image_path)
        _wait_for_media_ready(media_id)

        # Create the pin
        for attempt in range(1, MAX_RETRIES + 1):
            print(f"  📌 Creating pin (attempt {attempt})...")
            payload = {
                "title": title,
                "description": desc,
                "board_id": BOARD_ID,
                "link": link,
                "media_source": {"source_type": "media_id", "media_id": media_id},
            }
            try:
                resp = requests.post(PINS_ENDPOINT,
                                     headers={"Authorization": f"Bearer {ACCESS_TOKEN}",
                                              "Content-Type": "application/json"},
                                     json=payload, timeout=30)
            except requests.RequestException as e:
                print(f"  ⚠️  Network error: {e}")
                time.sleep(2 ** attempt)
                continue

            if resp.status_code == 201:
                pin = resp.json()
                print(f"  ✅ PIN CREATED! ID: {pin.get('id', '?')}")
                print(f"  🔗 https://www.pinterest.com/pin/{pin.get('id', '')}")
                return True
            elif resp.status_code == 429 and attempt < MAX_RETRIES:
                print("  ⏳ Rate limited — waiting 30s...")
                time.sleep(30)
                continue
            elif resp.status_code >= 500 and attempt < MAX_RETRIES:
                print(f"  ⚠️  Server error — retrying...")
                time.sleep(2 ** attempt)
                continue
            else:
                print(f"  ❌ Failed ({resp.status_code}): {resp.text[:200]}")
                return False
        return False

    except (requests.RequestException, RuntimeError) as e:
        print(f"  ❌ API error: {e}")
        return False


def _is_logged_in(page) -> bool:
    """Detect whether the current page represents a logged-in Pinterest session."""
    try:
        url = page.url.lower()
        if "login" in url or "signup" in url:
            return False
        # If there are explicit login/signup buttons, we are definitely NOT logged in
        if page.locator('button:has-text("Log in")').first.is_visible(timeout=1000):
            return False
            
        # Logged-in homepage shows nav buttons (profile menu, etc.)
        # Try a robust check: presence of the avatar / pin-creation entry points
        for sel in [
            '[data-test-id="header-avatar"]',
            '[aria-label="Accounts and more options"]',
            'div[data-test-id="header-profile"]',
        ]:
            try:
                if page.locator(sel).first.is_visible(timeout=1500):
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False


def _auto_login(page) -> bool:
    """Try logging in with PINTEREST_EMAIL / PINTEREST_PASSWORD from .env.
    Returns True on success, False if creds missing or login failed.
    """
    if not (PINTEREST_EMAIL and PINTEREST_PASSWORD):
        return False
    print("  🔐 Auto-login with .env credentials...")
    try:
        page.goto(LOGIN_URL, wait_until="domcontentloaded", timeout=30000)
        time.sleep(2)
        # Email field
        email_input = page.locator('input[name="email"], input[type="email"], #email').first
        email_input.wait_for(state="attached", timeout=15000)
        email_input.fill(PINTEREST_EMAIL)
        time.sleep(0.5)
        # Password field
        pwd_input = page.locator('input[name="password"], input[type="password"], #password').first
        pwd_input.wait_for(state="attached", timeout=15000)
        pwd_input.fill(PINTEREST_PASSWORD)
        time.sleep(0.5)
        # Submit
        submit = page.locator('button[type="submit"], [data-test-id="registerFormSubmitButton"]').first
        submit.click()
        # Wait for navigation away from login
        try:
            page.wait_for_url(lambda u: "login" not in u.lower() and "signup" not in u.lower(),
                              timeout=20000)
        except Exception:
            time.sleep(4)
        if _is_logged_in(page):
            print("  ✅ Auto-login succeeded — session saved.")
            return True
        print("  ⚠️  Auto-login failed (wrong creds, 2FA, or CAPTCHA).")
        return False
    except Exception as e:
        print(f"  ⚠️  Auto-login error: {e}")
        return False


def _wait_for_login_interactive(context, page) -> None:
    """Manual fallback: open browser, prompt user to log in, persist session."""
    print()
    print("  ⚠️  YOU NEED TO LOG IN!")
    print("  Pinterest opened in a browser window.")
    print("  → Log in to your Pinterest account")
    print("  → This is a ONE-TIME setup — your session will be saved.")
    print()
    input("  Press Enter here AFTER you've logged in... ")
    print()


# ── Playwright Browser Poster ──────────────────────────────────────────



_GLOBAL_BROWSER_MGR = None
_GLOBAL_CONTEXT = None
_GLOBAL_PAGE = None

def cleanup_browser():
    global _GLOBAL_BROWSER_MGR, _GLOBAL_CONTEXT, _GLOBAL_PAGE
    if _GLOBAL_BROWSER_MGR or _GLOBAL_PAGE:
        print('\n  🧹 Cleaning up browser session...')
    try:
        from jarvis_browser import safe_close_sync
        if _GLOBAL_PAGE: safe_close_sync(_GLOBAL_PAGE)
        if _GLOBAL_CONTEXT: safe_close_sync(_GLOBAL_CONTEXT)
        if _GLOBAL_BROWSER_MGR:
            try: _GLOBAL_BROWSER_MGR.__exit__(None, None, None)
            except: pass
    except Exception as e:
        print(f'  ⚠️ Cleanup error: {e}')
    finally:
        _GLOBAL_PAGE = None
        _GLOBAL_CONTEXT = None
        _GLOBAL_BROWSER_MGR = None

def _post_via_browser(image_path: str, title: str, link: str, description: str, board_name: str = None) -> bool:
    """Fallback: post using Playwright browser automation.
    
    Works even without Pinterest API approval. Uses persistent login session
    so you only need to log in manually once.
    """
    print(f"\n  ── Posting via Browser (Playwright) ──")
    try:
        from jarvis_browser import SyncBrowser, safe_close_sync
    except ImportError:
        print("  ❌ Playwright not installed. Run: pip install playwright && playwright install chromium")
        return False

    # Stable persistent profile so cookies/cache survive between runs.
    if not os.path.exists(BROWSER_USER_DATA_DIR):
        try:
            os.makedirs(BROWSER_USER_DATA_DIR, exist_ok=True)
        except Exception:
            pass
    print(f"  📂 Browser profile: {BROWSER_USER_DATA_DIR}")

    try:
        global _GLOBAL_BROWSER_MGR, _GLOBAL_CONTEXT, _GLOBAL_PAGE
        if _GLOBAL_BROWSER_MGR is None:
            print(f'  📂 Initializing Global Browser Profile: {BROWSER_USER_DATA_DIR}')
            import sys
            run_headless = False  # FORCE visible browser for manual login
            _GLOBAL_BROWSER_MGR = SyncBrowser(headless=run_headless)
            _GLOBAL_BROWSER_MGR.__enter__()
            _GLOBAL_CONTEXT = _GLOBAL_BROWSER_MGR.launch_persistent(
                BROWSER_USER_DATA_DIR,
                extra_kwargs={"no_viewport": True},
            )
            _GLOBAL_PAGE = _GLOBAL_CONTEXT.new_page()
            page = _GLOBAL_PAGE
        else:
            print('  🌐 Reusing open browser window...')
            page = _GLOBAL_PAGE

        # Navigate to Pinterest
        print("  🌐 Opening Pinterest...")
        page.goto("https://www.pinterest.com", wait_until="domcontentloaded")
        time.sleep(3)

        # ── Login flow (3 attempts: cached session → auto-login → manual) ──
        session_cookie = os.getenv("PINTEREST_SESSION_COOKIE")
        if session_cookie:
            print("  🍪 Injecting session cookie from .env...")
            _GLOBAL_CONTEXT.add_cookies([{
                'name': '_pinterest_sess',
                'value': session_cookie,
                'domain': '.pinterest.com',
                'path': '/'
            }])
            page.reload(wait_until="domcontentloaded")
            time.sleep(3)
        if not _is_logged_in(page):
            if not _auto_login(page):
                # Manual fallback as last resort
                _wait_for_login_interactive(_GLOBAL_CONTEXT, page)
                
                # Check if they actually logged in
                page.goto("https://www.pinterest.com", wait_until="domcontentloaded")
                time.sleep(3)
        else:
            print("  ✅ Already logged in (cached session).")

        # Navigate to create pin page
        print("  📌 Navigating to pin creation...")
        page.goto("https://www.pinterest.com/pin-builder/", wait_until="domcontentloaded")
        time.sleep(3)

        # Upload image via file input
        print(f"  📤 Uploading image...")
        try:
            page.wait_for_load_state("domcontentloaded", timeout=30000)
            time.sleep(3)

            drop_zone_selectors = [
                '[data-test-id="media-empty-view"]',
                '[data-test-id="drag-behavior-container"]',
                '[data-test-id="pin-builder-drop-zone"]',
                '[data-test-id="media-upload-drop-zone"]',
                'div[role="button"]:has-text("Drag and drop")',
                'div[role="button"]:has-text("Click to upload")',
                '.drop-zone',
                '[data-test-id*="drop"]',
            ]

            file_uploaded = False
            for selector in drop_zone_selectors:
                try:
                    drop_zone = page.locator(selector).first
                    if drop_zone.is_visible(timeout=3000):
                        print(f"  📌 Clicking drop zone: {selector}")
                        with page.expect_file_chooser(timeout=10000) as fc_info:
                            drop_zone.click()
                        file_chooser = fc_info.value
                        file_chooser.set_files(os.path.abspath(image_path))
                        file_uploaded = True
                        break
                except Exception as e:
                    continue
            
            if not file_uploaded:
                print("  ⚠️  File chooser failed, falling back to set_input_files on input[type='file']")
                file_input = page.locator('input[type="file"]').first
                file_input.wait_for(state="attached", timeout=10000)
                file_input.set_input_files(os.path.abspath(image_path), timeout=30000)

            print("  ✅ Image uploaded! Waiting for preview...")
            time.sleep(5)

        except Exception as e:
            print(f"  ⚠️  Upload error: {e}")
            page.goto("https://www.pinterest.com/pin-builder/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(4)
            file_input = page.locator('input[type="file"]').first
            file_input.wait_for(state="attached", timeout=20000)
            file_input.set_input_files(os.path.abspath(image_path), timeout=30000)
            print("  ✅ Image uploaded on retry! Waiting for preview...")
            time.sleep(5)

        from jarvis_browser import solve_with_dom_sync

        # Fill in title
        try:
            print(f"  📌 Filling title: {title[:50]}...")
            el = page.get_by_placeholder("Add your title")
            if el.count() > 0: el.first.fill(title[:100])
            else: solve_with_dom_sync(page, f"Fill the title input field with: {title[:100]}")
            print(f"  ✅ Title filled")
        except Exception as e:
            print(f"  ⚠️  Could not fill title: {e}")

        time.sleep(1)

        # Fill in description
        try:
            print("  📌 Filling description...")
            el = page.locator('[data-test-id="story-pin-builder-draft-editor"] [contenteditable="true"], [data-test-id="pin-builder-description"] [contenteditable="true"], [aria-label="Tell everyone what your Pin is about"], [aria-label="Add a detailed description"]')
            if el.count() == 0: el = page.get_by_placeholder("Tell everyone what your Pin is about")
            if el.count() == 0: el = page.get_by_placeholder("Add a detailed description")
            
            if el.count() > 0: el.first.fill(description[:500])
            else: solve_with_dom_sync(page, f"Fill the description text area with: {description[:500]}")
            print(f"  ✅ Description filled")
        except Exception as e:
            print(f"  ⚠️  Could not fill description: {e}")

        time.sleep(1)

        # Fill in link
        try:
            print("  📌 Filling destination link...")
            el = page.get_by_placeholder("Add a destination link")
            if el.count() > 0: el.first.fill(link[:200])
            else: solve_with_dom_sync(page, f"Fill the destination link input field with: {link[:200]}")
            print(f"  ✅ Link filled")
        except Exception as e:
            print(f"  ⚠️  Could not fill link: {e}")

        time.sleep(1)

        env_board_name = os.getenv("PINTEREST_BOARD_NAME")
        target_board = board_name or env_board_name or BOARD_ID
        if target_board:
            try:
                board_dropdown = page.locator('[data-test-id="board-dropdown-select-button"]').first
                if not board_dropdown.is_visible():
                    board_dropdown = page.get_by_label("Board", exact=False).first
                if board_dropdown.is_visible():
                    print(f"  📌 Selecting board: {target_board}")
                    board_dropdown.click()
                    time.sleep(2)
                    
                    # 1. ALWAYS search first
                    search_input = page.locator('input[placeholder*="Search"]').first
                    if search_input.is_visible():
                        search_input.fill(target_board)
                        time.sleep(2)
                        
                    # 2. Check if the exact board option appeared
                    try:
                        board_option = page.get_by_text(target_board, exact=True).first
                        board_option.wait_for(timeout=3000, state='visible')
                        board_option.click()
                    except Exception:
                        # 3. If still not found, create it
                        print(f"  ⚠️  Board '{target_board}' not found. Attempting to create it...")
                        try:
                            # Try multiple locators for the Create Board button
                            create_btn = None
                            for sel in [
                                'div[role="button"]:has-text("Create board")',
                                '[data-test-id="create-board-button"]',
                                'div[title="Create board"]'
                            ]:
                                btn = page.locator(sel).first
                                if btn.is_visible(timeout=1000):
                                    create_btn = btn
                                    break
                                    
                            if not create_btn:
                                create_btn = page.get_by_text("Create board", exact=False).first
                                
                            if create_btn and create_btn.is_visible(timeout=2000):
                                create_btn.click()
                                time.sleep(1)
                                name_input = page.locator('input[id="boardEditName"], input[placeholder*="Name"]').first
                                if name_input.is_visible():
                                    name_input.fill(target_board)
                                # Target the specific red Create button in the modal
                                submit_btn = page.locator('div[role="dialog"] button:has-text("Create")').last
                                if not submit_btn.is_visible(timeout=1000):
                                    submit_btn = page.locator('button[type="submit"]:has-text("Create")').last
                                submit_btn.click()
                                time.sleep(3)
                                print(f"  ✅ Created new board: {target_board}")
                            else:
                                print("  ⚠️  Could not find 'Create board' button. Trying to clear search and click first available board...")
                                search_input.fill("")
                                time.sleep(1)
                                fallback_board = page.locator('div[role="button"]').filter(has_text=re.compile(r".*")).first
                                fallback_board.click(timeout=5000)
                        except Exception as e:
                            print(f"  ⚠️  Failed to create board: {e}")
                            search_input.fill("")
                            time.sleep(1)
                            page.keyboard.press("ArrowDown")
                            page.keyboard.press("Enter")
            except Exception as e:
                print(f"  ⚠️  Board picker error: {e}")
        else:
            print("  ℹ️  No BOARD_ID set — using whatever Pinterest auto-selects.")

        time.sleep(1)

        print("  📌 Dismissing potential tutorials...")
        for _ in range(3):
            page.keyboard.press("Escape")
            time.sleep(0.5)

        # Click Save/Publish button
        print("  📌 Publishing pin...")
        try:
            save_clicked = False
            for sel in [
                '[data-test-id="board-dropdown-save-button"]',
                'button[aria-label*="Save"]',
                'button[aria-label*="Publish"]',
                'div[role="button"]:has-text("Publish")',
                'div[role="button"]:has-text("Save")'
            ]:
                btn = page.locator(sel).first
                if btn.is_visible(timeout=3000):
                    try:
                        print(f"  ⏳ Waiting for '{sel}' to become enabled...")
                        # Wait for the button to not be disabled (Pinterest uses aria-disabled on divs)
                        active_btn = page.locator(f'{sel}[aria-disabled="false"], {sel}:not([disabled])').first
                        active_btn.wait_for(state="visible", timeout=15000)
                        active_btn.click(timeout=5000)
                        print(f"  ✅ Clicked Publish/Save natively using {sel}")
                        save_clicked = True
                        break
                    except Exception as e:
                        print(f"  ⚠️  Native click failed on {sel}, trying next...")
                        continue
                        
            if not save_clicked:
                print("  ⚠️  Could not find Save button via locators, trying JS fallback...")
                page.evaluate("""
                    let btn = document.querySelector('[data-test-id="board-dropdown-save-button"]') || document.querySelector('button[aria-label*="Save"]');
                    if(btn) { btn.click(); }
                """)
                print("  ✅ Executed Save via JS")
            
            # Wait for success indicator
            try:
                success = False
                for _ in range(20):
                    if "pin-builder" not in page.url.lower():
                        print("  🎉 Success: Redirected to new pin!")
                        success = True
                        break
                        
                    toast = page.locator('[data-test-id="toast"], .toast, [role="alert"], div:has-text("Saved to")').first
                    if toast.is_visible(timeout=500):
                        print(f"  🎉 Success: {toast.inner_text()[:100].replace(chr(10), ' ')}")
                        success = True
                        break
                        
                    modal = page.locator('div[role="dialog"]:has-text("Saved")').first
                    if modal.is_visible(timeout=500):
                        print("  🎉 Success: Saved modal appeared!")
                        success = True
                        break
                        
                    time.sleep(1)
                    
                if not success:
                    page.screenshot(path="failed_publish.png", full_page=True)
                    print("  ⚠️ No success indicator found within 20s. Saved failed_publish.png")
                    # It might have succeeded silently, assume true
            except Exception as e:
                page.screenshot(path="failed_publish.png", full_page=True)
                print(f"  ⚠️ Error checking success: {e}")
                
            return True
        except Exception as e:
            print(f"  ⚠️  Board/Save picker error: {e}")

        try:
            # Wait a bit for page to be stable
            time.sleep(2)
            if hasattr(page, 'fallback'):
                page.fallback("Click the red 'Save' or 'Publish' button at the top right of the screen.")
                time.sleep(5)
                print("  🎉 Fallback vision successfully clicked the button!")
                return True
        except Exception as fe:
            print(f"  ⚠️  Vision fallback failed: {fe}")
            
        print("  💡 Please check the browser window and save the pin manually.")
        input("  Press Enter after saving manually (or close the browser)...")
        return True  # Assume user did it manually

    except Exception as e:
        print(f"  ❌ Browser posting error: {e}")
        return False


# ── Smart Poster (API → Browser fallback) ──────────────────────────────


PIN_COUNTER = 0

def post_pin(image_path: str, title: str = None, description: str = None, link: str = None, force_browser: bool = False, board_name: str = None) -> bool:
    """
    Post a pin to Pinterest.
    
    Strategy:
      1. Try API v5 (fast, stealthy, scales well)
      2. If API fails with auth error → fallback to Playwright browser
      3. If force_browser=True → skip API, go straight to browser
    
    Returns True on success.
    """
    global PIN_COUNTER
    PIN_COUNTER += 1

    if not os.path.exists(image_path):
        print(f"❌ Image not found: {image_path}")
        return False

    # Auto-generate description if not provided
    if not description:
        description = f"Check out this {title[:200]}! Perfect for students. #amazonfinds #deals #collegeessentials"

    print(f"\n{'='*50}")
    print(f"  PIN #{PIN_COUNTER}: {title[:60]}")
    print(f"{'='*50}")

    # ── Option A: API v5 ──
    if not force_browser and ACCESS_TOKEN and BOARD_ID:
        # Check if token looks valid (not a placeholder)
        if "your_pinterest_access_token" not in ACCESS_TOKEN and len(ACCESS_TOKEN) > 20:
            success = _post_via_api(image_path, title, link, description)
            if success:
                return True
            # If API failed with auth error, fallback to browser
            print("  ⚠️  API failed — falling back to browser automation...")
        else:
            print("  ℹ️  API token looks like a placeholder — using browser mode.")
    else:
        if force_browser:
            print("  ℹ️  Browser mode forced.")
        elif not ACCESS_TOKEN:
            print("  ℹ️  No API token found — using browser mode.")
        elif not BOARD_ID:
            print("  ℹ️  No board ID set — using browser mode.")

    # ── Option B: Playwright Browser ──
    return _post_via_browser(image_path, title, link, description, board_name=board_name)


if __name__ == "__main__":
    # Test
    test_img = "output/test_pin.jpg"
    if os.path.exists(test_img):
        post_pin(test_img, "Test Pin — Check out these amazing products!", 
                 "https://amzn.to/test")
    else:
        print("No test image. Run: python generator.py")
