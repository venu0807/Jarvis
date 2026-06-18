"""
scripts/headful_reauth.py — One-time CAPTCHA solver for foundit/Glassdoor/Indeed/Unstop/Internshala/Wellfound
- Run ONCE on your machine. Browser stays open for each portal.
- You solve CAPTCHA/login in the browser window. Scripts auto-continue after ~60-120s.
- Sessions saved to .sessions/{portal}.json — future headless cron runs work for weeks.

Usage:
    python scripts/headful_reauth.py                                       # all 6 portals in sequence
    python scripts/headful_reauth.py --only indeed                         # just Indeed
    python scripts/headful_reauth.py --skip internshala,wellfound          # run all except those

Note (2026-06-15): linkedin, glassdoor, unstop cut from the active flow.
Re-add via `scripts/apply_portal_cuts.py --restore <name>` if needed.
"""
import asyncio
import argparse
import sys
from pathlib import Path

# Project root = parent of scripts/
PROJ_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ_DIR))

# UTF-8 for Windows console
if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

from jarvis_browser import AsyncBrowser, safe_close_async
from dotenv import load_dotenv
import os

load_dotenv(PROJ_DIR / ".env")

# Import active portals. Cut 2026-06-15: GlassdoorPortal + UnstopPortal (low
# ROI). LinkedIn e.g. handling for /checkpoint already in LinkedInPortal —
# no longer imported here.
from portals import (
    FounditPortal,
    IndeedPortal,
    CutshortPortal,
    IntersahalaPortal,
    FreshersworldPortal,
    WellfoundPortal,
)

_GMAIL = os.getenv("GMAIL_ADDRESS", "")

PORTALS = [
    ("foundit",       FounditPortal,       _GMAIL, os.getenv("FOUNDIT_PASSWORD",       "")),
    ("indeed",        IndeedPortal,        _GMAIL, os.getenv("INDEED_PASSWORD",        "")),
    ("internshala",   IntersahalaPortal,   _GMAIL, os.getenv("INTERNSHALA_PASSWORD",   "")),
    ("cutshort",      CutshortPortal,      _GMAIL, os.getenv("CUTSHORT_PASSWORD",      "")),
    ("freshersworld", FreshersworldPortal, _GMAIL, os.getenv("FRESHERSWORLD_PASSWORD", "")),
    ("wellfound",     WellfoundPortal,     _GMAIL, os.getenv("WELLFOUND_PASSWORD",     "")),
]


async def login_one(browser_mgr, name, cls, email, password):
    """Drive one portal's login in headful mode. Save session after success."""
    print(f"\n{'='*60}\n🌐 {name.upper()} — opening browser window\n{'='*60}")

    if not password:
        print(f"  ❌ {name}: password missing in .env — skipping")
        return False

    session_path = PROJ_DIR / ".sessions" / f"{name}.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)

    context = await browser_mgr.new_context_with_session(session_path)
    page    = await context.new_page()
    portal  = cls(email=email, password=password)

    # Delete any old session first so login() actually runs the full flow
    # (otherwise _is_logged_in() returns True on the stale cookie and skips CAPTCHA solve)
    if session_path.exists():
        backup = session_path.with_suffix(".json.pre-reauth")
        try:
            session_path.rename(backup)
            print(f"  ♻️  Old session backed up → {backup.name}")
        except Exception:
            pass

    print(f"\n  👉 ACTION: A browser window is open on the {name} website.")
    print(f"     - Solve any CAPTCHA / OTP / email-link that appears")
    print(f"     - The script detects when you're logged in and moves on")
    print(f"     - You have up to 3 minutes per portal")

    # Hand-off: the portal's login() will WAIT 60-120s for manual solve
    ok = False
    try:
        ok = await portal.login(page)
    except Exception as e:
        print(f"  ⚠️  {name}: login raised {e}")

    if ok:
        print(f"  ✅ {name}: logged in — saving session to {session_path.name}")
        try:
            await context.storage_state(path=str(session_path))
            print(f"  💾 Session saved ({session_path.stat().st_size} bytes)")
        except Exception as se:
            print(f"  ❌ Could not save session: {se}")
    else:
        print(f"  ❌ {name}: login did not succeed")
        print(f"     (You can re-run this script to retry just {name})")

    # Close BEFORE next portal — clean state
    await safe_close_async(context)

    return ok


async def main():
    parser = argparse.ArgumentParser(description="One-time CAPTCHA solver for portals")
    parser.add_argument("--only",
                        help="Comma-separated subset to run (foundit,indeed,internshala,cutshort,freshersworld,wellfound)")
    parser.add_argument("--skip",
                        help="Comma-separated subset to skip (foundit,indeed,internshala,cutshort,freshersworld,wellfound)")

    only_set = set((args.only  or "").split(",")) - {""}
    skip_set = set((args.skip  or "").split(",")) - {""}

    selected = [(n, c, e, p) for (n, c, e, p) in PORTALS
                if (not only_set or n in only_set)
                and (not skip_set or n not in skip_set)]

    if not selected:
        print("No portals selected. Use --only/--skip (comma-separated) or no args for all 6.")
        print("Available:", ", ".join(n for n, *_ in PORTALS))
        return

    print(f"""
╔══════════════════════════════════════════════════╗
║   🔐 HEADFUL CAPTCHA SOLVER                      ║
║   {len(selected)} portal(s): {', '.join(n for n,*_ in selected)}
║   Browser stays visible — solve CAPTCHA in window ║
║   Sessions save → future cron runs are headless   ║
╚══════════════════════════════════════════════════╝
""")
    input("  Press ENTER to launch browser... ")

    results = {}
    async with AsyncBrowser(headless=False) as browser_mgr:
        for name, cls, email, password in selected:
            results[name] = await login_one(browser_mgr, name, cls, email, password)

    # Final report
    print(f"\n\n{'='*60}")
    print(f"📊 Final Results:")
    for name, ok in results.items():
        mark = "✅" if ok else "❌"
        print(f"   {mark} {name}")
    succ = sum(1 for v in results.values() if v)
    print(f"\n  {succ}/{len(results)} portals re-authenticated")
    if succ == len(results):
        print("\n  🎉 All done — future pipeline runs can be headless!")
    else:
        print(f"\n  ⚠️  Failed portals can be retried: python {Path(__file__).name} --only <portal>")


if __name__ == "__main__":
    asyncio.run(main())
