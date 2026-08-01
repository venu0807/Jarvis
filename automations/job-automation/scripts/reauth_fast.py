"""
Quick headful reauth for Foundit + Naukri — no input prompt, auto-opens browser.
Run: python scripts/reauth_fast.py
"""
import asyncio, sys
from pathlib import Path

PROJ_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ_DIR))
sys.path.insert(0, str(PROJ_DIR.parent.parent))

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

from jarvis_browser import AsyncBrowser, safe_close_async
from dotenv import load_dotenv
import os
load_dotenv(PROJ_DIR / ".env")

from portals import FounditPortal, NaukriPortal

PORTALS = [
    ("foundit", FounditPortal, os.getenv("GMAIL_ADDRESS", ""), os.getenv("FOUNDIT_PASSWORD", "")),
    ("naukri",  NaukriPortal,  os.getenv("NAUKRI_EMAIL", ""),  os.getenv("NAUKRI_PASSWORD", "")),
]

async def login_one(browser_mgr, name, cls, email, password):
    print(f"\n{'='*60}\n🌐 {name.upper()} — opening browser window\n{'='*60}")
    if not password:
        print(f"  ❌ {name}: password missing in .env — skipping")
        return False

    session_path = PROJ_DIR / ".sessions" / f"{name}.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)

    if session_path.exists():
        backup = session_path.with_suffix(".json.pre-reauth")
        session_path.rename(backup)

    context = await browser_mgr.new_context_with_session(session_path)
    page = await context.new_page()
    portal = cls(email=email, password=password)

    print(f"  👉 Solve CAPTCHA/OTP for {name} in the browser window")
    print(f"     Script waits up to 3 min then saves session")

    ok = False
    try:
        ok = await portal.login(page)
    except Exception as e:
        print(f"  ⚠️  {name}: login raised {e}")

    if ok:
        print(f"  ✅ {name}: logged in — saving session")
        await context.storage_state(path=str(session_path))
        await context.close()
    else:
        print(f"  ❌ {name}: login failed — session NOT saved")

    await safe_close_async(context)
    return ok

async def main():
    print(f"\n{'='*56}\n🔐 Headful Reauth: foundit, naukri\n{'='*56}")
    async with AsyncBrowser(headless=False) as browser_mgr:
        for name, cls, email, password in PORTALS:
            await login_one(browser_mgr, name, cls, email, password)

    print(f"\n{'='*56}")
    print("✅ Done! Now run: python auto_applier.py --headful --portal foundit")
    print("   or:   python auto_applier.py --headful --portal naukri")

if __name__ == "__main__":
    asyncio.run(main())
