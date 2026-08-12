"""capture_session.py — manually log into a portal in a visible browser, save session.

Opens the portal on the real display (NOT xvfb), waits for YOU to log in
(handle captcha/2FA/OTP yourself), then saves the storage_state to
.sessions/<portal>.json so the auto-applier reuses it.

    python capture_session.py <portal>

<portal>: naukri|internshala|indeed|foundit|cutshort|freshersworld|wellfound

The browser closes as soon as the page navigates away from the login page
after you sign in — or press Enter here to capture immediately.
"""
import asyncio
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
SESSION_DIR = BASE_DIR / ".sessions"

VALID = {"naukri", "internshala", "indeed", "foundit"}

PORTAL_URL = {
    "naukri": "https://www.naukri.com",
    "internshala": "https://internshala.com/login/student",
    "indeed": "https://in.indeed.com",
    "foundit": "https://www.foundit.in",
}

LOGIN_MARKERS = [
    "logout", "sign out", "/logout", "account", "dashboard",
    "my applications", "applied", "profile", "recommendation",
]


def _looks_logged_in(url: str) -> bool:
    u = url.lower()
    return any(m in u for m in LOGIN_MARKERS)


async def main() -> int:
    portal = sys.argv[1] if len(sys.argv) > 1 else ""
    if portal not in VALID:
        print(f"Unknown portal '{portal}'. Valid: {', '.join(sorted(VALID))}")
        return 1

    from playwright.async_api import async_playwright

    url = PORTAL_URL[portal]
    print(f"\n🌐 Opening {portal} → {url}")
    print("   Log in in the browser window (handle captcha/OTP manually).")
    print("   The session saves automatically once login completes.\n")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=False,
            # include_user_name_version avoided; chromium picks up fonts/display
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            locale="en-IN",
        )
        page = await context.new_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)

        print("⏳ Waiting for you to log in (up to 5 min)…")
        captured = False
        for _ in range(300):  # 5 min
            await asyncio.sleep(1)
            try:
                cur = page.url
            except Exception:
                cur = ""
            if _looks_logged_in(cur):
                await asyncio.sleep(3)  # let post-login redirect settle
                SESSION_DIR.mkdir(parents=True, exist_ok=True)
                state = await context.storage_state(path=str(SESSION_DIR / f"{portal}.json"))
                print(f"✅ Saved session → {SESSION_DIR / f'{portal}.json'}")
                captured = True
                break

        if not captured:
            print("No login detected in 5 min — press Enter in the terminal to capture anyway, or Ctrl-C to abort.")
            await asyncio.to_thread(input)
            SESSION_DIR.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(SESSION_DIR / f"{portal}.json"))
            print(f"✅ Saved session (manual capture) → {SESSION_DIR / f'{portal}.json'}")

        await browser.close()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
