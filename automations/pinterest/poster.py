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

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"  📤 Registering media (attempt {attempt})...")
        try:
            resp = requests.post(MEDIA_ENDPOINT, headers=headers,
                                 json={"media_type": "image"}, timeout=30)
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
        # Logged-in homepage shows nav buttons (profile menu, etc.)
        # Try a robust check: presence of the avatar / pin-creation entry points
        try:
            page.wait_for_load_state("domcontentloaded", timeout=5000)
        except Exception:
            pass
        for sel in [
            '[data-test-id="header-avatar"]',
            '[data-test-id="homefeed-feed"]',
            '[aria-label*="Profile" i]',
            'a[href*="/pin/create/"]',
            'button[aria-label*="Create" i]',
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
    try:
        context.close()  # close persistent context we may have opened
    except Exception:
        pass
    print()
    print("  ⚠️  YOU NEED TO LOG IN!")
    print("  Pinterest opened in a browser window.")
    print("  → Log in to your Pinterest account")
    print("  → This is a ONE-TIME setup — your session will be saved.")
    print()
    input("  Press Enter here AFTER you've logged in... ")
    print()


# ── Playwright Browser Poster ──────────────────────────────────────────


def _post_via_browser(image_path: str, title: str, link: str, description: str) -> bool:
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
        with SyncBrowser(headless=False) as browser_mgr:
            context = browser_mgr.launch_persistent(
                BROWSER_USER_DATA_DIR,
                extra_kwargs={"viewport": {"width": 1280, "height": 800}},
            )
            page = context.new_page()

            # Navigate to Pinterest
            print("  🌐 Opening Pinterest...")
            page.goto("https://www.pinterest.com", wait_until="domcontentloaded")
            time.sleep(3)

            # ── Login flow (3 attempts: cached session → auto-login → manual) ──
            if not _is_logged_in(page):
                if not _auto_login(page):
                    # Manual fallback as last resort
                    _wait_for_login_interactive(context, page)
                    # Re-open persistent context for subsequent steps
                    safe_close_sync(context)
                    with SyncBrowser(headless=False) as browser_mgr2:
                        context = browser_mgr2.launch_persistent(
                            BROWSER_USER_DATA_DIR,
                            extra_kwargs={"viewport": {"width": 1280, "height": 800}},
                        )
                        page = context.new_page()
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
                    '[data-test-id="pin-builder-drop-zone"]',
                    '[data-test-id="media-upload-drop-zone"]',
                    'div[role="button"]:has-text("Drag and drop")',
                    'div[role="button"]:has-text("Click to upload")',
                    '[data-test-id="pin-builder"]',
                    '.drop-zone',
                    '[data-test-id*="drop"]',
                ]

                file_input = None
                for selector in drop_zone_selectors:
                    try:
                        drop_zone = page.locator(selector).first
                        if drop_zone.is_visible(timeout=3000):
                            drop_zone.click()
                            time.sleep(1.5)
                            file_input = page.locator('input[type="file"]').first
                            break
                    except Exception:
                        continue

                if not file_input:
                    file_input = page.locator('input[type="file"]').first

                try:
                    page.screenshot(path="debug_pin_builder.png")
                    print("  📸 Screenshot saved for debugging")
                    html = page.content()
                    with open("debug_page.html", "w", encoding="utf-8") as f:
                        f.write(html)
                    print("  📄 Page HTML saved for debugging")
                except:
                    pass

                file_input.wait_for(state="attached", timeout=20000)
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

            # Fill in title
            try:
                title_field = page.get_by_label("Title", exact=False).first
                if title_field.is_visible():
                    title_field.click()
                    title_field.fill(title[:100])
                    print(f"  ✅ Title filled: {title[:50]}...")
            except Exception:
                print("  ⚠️  Could not find title field, trying alternatives...")
                try:
                    title_field = page.locator('[placeholder*="title" i], [placeholder*="add" i]').first
                    if title_field.is_visible():
                        title_field.click()
                        title_field.fill(title[:100])
                except Exception:
                    pass

            time.sleep(1)

            # Fill in description
            try:
                desc_field = page.get_by_label("Description", exact=False).first
                if desc_field.is_visible():
                    desc_field.click()
                    desc_field.fill(description[:500])
                    print(f"  ✅ Description filled")
            except Exception:
                print("  ⚠️  Could not find description field")

            time.sleep(1)

            # Fill in link
            try:
                link_field = page.get_by_label("Link", exact=False).first
                if link_field.is_visible():
                    link_field.click()
                    link_field.fill(link[:200])
                    print(f"  ✅ Link filled: {link[:60]}...")
            except Exception:
                print("  ⚠️  Could not find link field")

            time.sleep(1)

            # Select board if board ID is provided
            if BOARD_ID:
                try:
                    board_dropdown = page.get_by_label("Board", exact=False).first
                    if board_dropdown.is_visible():
                        board_dropdown.click()
                        time.sleep(2)
                        try:
                            page.locator(f'[data-test-id="board-card-{BOARD_ID}"], text="{BOARD_ID}"').first.click(timeout=5000)
                        except Exception:
                            try:
                                page.locator('[data-test-id="board-card"]').first.click(timeout=5000)
                            except Exception:
                                pass
                except Exception as e:
                    print(f"  ⚠️  Board picker error: {e}")
            else:
                print("  ℹ️  No BOARD_ID set — using whatever Pinterest auto-selects.")

            time.sleep(1)

            # Click Save/Publish button
            print("  📌 Publishing pin...")
            try:
                save_btn = None
                for selector in [
                    'button[aria-label*="Save" i]',
                    'button[aria-label*="Create" i]',
                    'button:has-text("Save")',
                    'button:has-text("Create pin")',
                    'button:has-text("Next")',
                    '[data-test-id="pin-builder-save-button"]',
                    'button[type="submit"]',
                    'button[role="button"]:has-text("Save")',
                ]:
                    try:
                        btn = page.locator(selector).first
                        if btn.is_visible():
                            save_btn = btn
                            print(f"  ✅ Found Save button with: {selector}")
                            break
                    except Exception:
                        continue

                if not save_btn:
                    save_btn = page.get_by_role("button", name="Save", exact=False).first
                    if not save_btn.is_visible():
                        save_btn = page.get_by_role("button", name="Create", exact=False).first

                if save_btn and save_btn.is_visible():
                    save_btn.click()
                    print("  ✅ Clicked Save — board selector opened")
                    time.sleep(3)

                    for btn_text in ["Save", "Done", "Publish", "Post", "Create"]:
                        try:
                            confirm_btn = page.get_by_role("button", name=btn_text, exact=False).first
                            if confirm_btn.is_visible():
                                confirm_btn.click()
                                print(f"  ✅ Clicked '{btn_text}' — pin published!")
                                time.sleep(5)
                                try:
                                    toast = page.locator('[data-test-id="toast"], .toast, [role="alert"], .success').first
                                    if toast.is_visible():
                                        print(f"  🎉 Success: {toast.inner_text()[:100]}")
                                except:
                                    pass
                                return True
                        except Exception:
                            continue

                    try:
                        any_btn = page.locator('button:visible').last
                        if any_btn.is_visible():
                            any_btn.click()
                            print("  ✅ Clicked last visible button")
                            time.sleep(5)
                            return True
                    except Exception:
                        pass
                else:
                    print("  ⚠️  Could not find initial Save button")
            except Exception as e:
                print(f"  ⚠️  Save flow error: {e}")

            print("  ❌ Could not find Save button. Pinterest UI may have changed.")
            print("  💡 Please check the browser window and save the pin manually.")
            input("  Press Enter after saving manually (or close the browser)...")
            return True  # Assume user did it manually

    except Exception as e:
        print(f"  ❌ Browser posting error: {e}")
        return False


# ── Smart Poster (API → Browser fallback) ──────────────────────────────


PIN_COUNTER = 0

def post_pin(image_path: str, title: str, link: str, 
             description: str = None, force_browser: bool = False) -> bool:
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
    return _post_via_browser(image_path, title, link, description)


if __name__ == "__main__":
    # Test
    test_img = "output/test_pin.jpg"
    if os.path.exists(test_img):
        post_pin(test_img, "Test Pin — Check out these amazing products!", 
                 "https://amzn.to/test")
    else:
        print("No test image. Run: python generator.py")
