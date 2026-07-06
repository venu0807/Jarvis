"""
Pinterest Session Cookie Auto-Renewal
=======================================
Detects when the _pinterest_sess cookie has expired and automatically
refreshes it by logging in with username/password, then updates the .env file.

This prevents zero-revenue days caused by silent bot failures.

Usage:
    python cookie_renewal.py          # Check and renew if expired
    python cookie_renewal.py --force  # Force renewal even if not expired
"""

import os
import sys
import time
import base64
from dotenv import load_dotenv, set_key

load_dotenv()

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

def is_cookie_valid() -> bool:
    """Check if the current session cookie is still valid by visiting Pinterest."""
    from playwright.sync_api import sync_playwright
    cookie = os.getenv("PINTEREST_SESSION_COOKIE", "")
    if not cookie:
        print("  ⚠️  No PINTEREST_SESSION_COOKIE found in .env")
        return False

    print("  🔍 Checking if session cookie is still valid...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            context.add_cookies([{
                "name": "_pinterest_sess",
                "value": cookie,
                "domain": ".pinterest.com",
                "path": "/"
            }])
            page = context.new_page()
            page.goto("https://www.pinterest.com", wait_until="domcontentloaded", timeout=30000)
            time.sleep(3)

            # Check if logged in (logged-in users have a profile menu)
            is_logged_in = page.locator('[data-test-id="header-profile"]').is_visible(timeout=5000)
            if not is_logged_in:
                # Secondary check — look for the login button
                has_login_btn = page.locator('a[href="/login/"]').is_visible(timeout=3000)
                is_logged_in = not has_login_btn

            browser.close()
            return is_logged_in
    except Exception as e:
        print(f"  ❌ Cookie check failed: {e}")
        return False


def renew_cookie() -> bool:
    """Log in with email/password and save the new session cookie to .env."""
    from playwright.sync_api import sync_playwright

    email = os.getenv("PINTEREST_EMAIL", "")
    password = os.getenv("PINTEREST_PASSWORD", "")

    if not email or not password:
        print("  ❌ PINTEREST_EMAIL or PINTEREST_PASSWORD missing from .env")
        return False

    print(f"  🔑 Logging in as {email} to renew session cookie...")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()
            page.goto("https://www.pinterest.com/login/", wait_until="domcontentloaded", timeout=30000)
            time.sleep(2)

            page.fill('input[id="email"]', email)
            time.sleep(0.5)
            page.fill('input[id="password"]', password)
            time.sleep(0.5)
            page.keyboard.press("Enter")
            time.sleep(5)

            # Wait for redirect to home
            page.wait_for_url("https://www.pinterest.com/", timeout=20000)
            time.sleep(2)

            # Extract the new session cookie
            cookies = context.cookies()
            sess_cookie = next((c for c in cookies if c["name"] == "_pinterest_sess"), None)

            if not sess_cookie:
                print("  ❌ Login succeeded but couldn't extract _pinterest_sess cookie")
                browser.close()
                return False

            new_cookie_value = sess_cookie["value"]
            browser.close()

            # Save back to .env
            set_key(ENV_PATH, "PINTEREST_SESSION_COOKIE", new_cookie_value)
            print("  ✅ Session cookie renewed and saved to .env!")
            print(f"  🔑 New cookie length: {len(new_cookie_value)} chars")
            return True

    except Exception as e:
        print(f"  ❌ Cookie renewal failed: {e}")
        return False


def check_and_renew(force: bool = False):
    """Main entry: check validity, renew if needed."""
    print("\n" + "=" * 50)
    print("  🍪 PINTEREST COOKIE AUTO-RENEWAL")
    print("=" * 50)

    if force:
        print("  🔁 Force renewal requested...")
        renew_cookie()
    elif is_cookie_valid():
        print("  ✅ Session cookie is valid — no renewal needed.")
    else:
        print("  ⚠️  Session cookie has EXPIRED. Renewing now...")
        success = renew_cookie()
        if not success:
            print("\n  ❌ CRITICAL: Auto-renewal failed!")
            print("  📋 Manual fix: Log into Pinterest in a browser, open DevTools")
            print("     (F12 → Application → Cookies → pinterest.com),")
            print("     copy the value of '_pinterest_sess', and paste it into")
            print("     your .env file as PINTEREST_SESSION_COOKIE=<value>")


if __name__ == "__main__":
    force = "--force" in sys.argv
    check_and_renew(force=force)
