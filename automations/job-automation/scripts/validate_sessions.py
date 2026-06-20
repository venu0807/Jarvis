"""
scripts/validate_sessions.py — Read-only session health check for all portals.
Loads each portal's saved Playwright storage_state, opens its homepage, and
reports whether the existing cookies are still valid.

Does NOT type into the page. Does NOT solve CAPTCHAs.
Safe to run anytime as a watchdog.
"""
import asyncio
from pathlib import Path
import sys

PROJ_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJ_DIR))
sys.path.insert(0, str(PROJ_DIR.parent.parent))

if sys.stdout.encoding != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
if sys.stderr.encoding != "utf-8":
    sys.stderr.reconfigure(encoding="utf-8")

from jarvis_browser import AsyncBrowser

SESS_DIR = PROJ_DIR / ".sessions"

# Portals to check: name → (homepage_to_navigate, login_check_selectors, url_marker, body_login_keywords, body_logout_keywords)
# - body_login_keywords: if not present, treat as logged-out
# - body_logout_keywords: if present, definitely logged-in (e.g. "Logout" link in footer)
PORTALS = [
    # Naukri: Akamai blocks our UA → can't tell without going to /mnjuser/profile directly
    ("naukri",        "https://www.naukri.com/mnjuser/profile",
                     [".nI-gNb-drawer__bars", ".user-name", "[class*='loggedIn']", "a[href*='/mnjuser/profile']"],
                     "profile",
                     ["my profile", "resume", "applied jobs"],
                     ["logout", "sign out"]),
    # Internshala: title says "Search Internships..." — must look for "Dashboard" or "logout"
    ("internshala",   "https://internshala.com",
                     [".profile-pic", ".student-profile", "a[href*='/logout']", "a[href*='/student/dashboard']", ".chat-icon-container", "#profile-dropdown"],
                     "dashboard",
                     ["dashboard", "my applications", "saved internships", "messages"],
                     ["logout", "sign out"]),
    # Cut 2026-06-15: linkedin, glassdoor, unstop — see scripts/apply_portal_cuts.py
    ("indeed",        "https://in.indeed.com",
                     ["a[href*='myjobs']", "button[aria-label*='Account']", "[data-testid='IndeedHeader']"],
                     None,
                     ["my jobs"],
                     ["sign out"]),
    # Foundit: also Akamai-blocked. Better detection later.
    ("foundit",       "https://www.foundit.in/seeker/profile",
                     ["div.header-profile-icon", "a[href*='dashboard']", "[class*='seekerName']"],
                     "profile",
                     ["my profile", "applied jobs", "recommended"],
                     ["logout", "sign out"]),
    ("cutshort",      "https://cutshort.io",
                     [".sidebar", ".user-avatar", "header", ".nav-links", "[data-nav]"],
                     None,
                     ["recommended jobs", "applied", "recommended"],
                     ["logout", "sign out"]),
    # Freshersworld: title is the public homepage; look for "My Profile" link
    ("freshersworld", "https://www.freshersworld.com",
                     [".user-profile", ".user-name", "a[href*='my-profile']", "a[href*='logout']", "a[href*='user/profile']"],
                     None,
                     ["my profile", "applied jobs", "shortlisted"],
                     ["logout", "sign out"]),
    ("wellfound",     "https://wellfound.com",
                     [".user-nav", "[data-user]", "a[href*='/profile']", ".user-menu"],
                     None,
                     ["my profile", "applications", "saved jobs"],
                     ["logout", "sign out"]),
]


async def check_one(browser_mgr, name, url, sel_list, url_marker, login_kws, logout_kws):
    sess_path = SESS_DIR / f"{name}.json"
    if not sess_path.exists():
        return name, "❌ NO_SESSION", "session file missing"

    ctx = await browser_mgr.new_context(sess_path)
    page = await ctx.new_page()
    body_text = ""
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(3500)

        # Capture page text once
        try:
            body_text = (await page.evaluate("() => document.body ? document.body.innerText.toLowerCase() : ''"))[:8000]
        except Exception:
            body_text = ""

        # Dump HTML for debugging
        try:
            debug_dir = PROJ_DIR / "scratch" / "session_check"
            debug_dir.mkdir(parents=True, exist_ok=True)
            html = await page.content()
            (debug_dir / f"{name}.html").write_text(html, encoding="utf-8")
        except:
            pass

        # First: logout keywords are STRONG signal — definitely logged in
        for kw in logout_kws or []:
            if kw in body_text:
                return name, "✅ VALID", f"logout keyword: '{kw}'"

        # Second: login-required keywords — if present, definitely logged in
        for kw in login_kws or []:
            if kw in body_text:
                return name, "✅ VALID", f"member keyword: '{kw}'"

        # Negative: if page is dominated by login-page signals (above the fold),
        # treat as expired. Tight pair-matching to avoid navbar false-positives.
        body_top = body_text[:800]
        if not any(k in body_top for k in (login_kws or [])):
            expired_pairs = [
                ["sign in", "create account"],
                ["log in", "create account"],
                ["sign in", "register"],
            ]
            for pair in expired_pairs:
                if all(p in body_top for p in pair):
                    return name, "🔴 EXPIRED", f"login pair '{pair}' above fold"

        # Third: URL marker
        if url_marker and url_marker in page.url:
            return name, "✅ VALID", f"URL marker: {url_marker}"

        # Fourth: visible selectors
        for sel in sel_list:
            try:
                if await page.locator(sel).first.is_visible(timeout=500):
                    return name, "✅ VALID", f"selector: {sel[:30]}"
            except Exception:
                continue

        # Fifth: explicit login page redirect
        if any(x in page.url for x in ["/login", "/auth", "/signin", "signup", "checkpoint", "/session/new", "/user/sign_in"]):
            return name, "🔴 EXPIRED", f"redirected to {page.url[:60]}"

        # Sixth: "Access Denied" / blank title → bot-blocked or something weird
        if "access denied" in body_text or "you don't have permission" in body_text:
            return name, "🟡 BLOCKED", "blocked by bot protection (Akamai/CDN)"

        return name, "🟡 UNCERTAIN", f"{page.url[:50]} | body[:120]={body_text[:120]!r}"
    except Exception as e:
        return name, "❌ ERROR", str(e)[:80]
    finally:
        try:
            await page.close()
        except:
            pass
        try:
            await ctx.close()
        except:
            pass


async def main():
    print(f"=== Session Health Check — {len(PORTALS)} portals ===\n")
    async with AsyncBrowser(headless=True) as browser_mgr:
        results = []
        for entry in PORTALS:
            name, url, sel, marker, login_kws, logout_kws = entry
            res = await check_one(browser_mgr, name, url, sel, marker, login_kws, logout_kws)
            results.append(res)
            mark, status, detail = res
            print(f"  {status:<14} {mark:<14} {detail}")

    print()
    valid = sum(1 for _, s, _ in results if "VALID" in s)
    expired = sum(1 for _, s, _ in results if "EXPIRED" in s)
    no_session = sum(1 for _, s, _ in results if "NO_SESSION" in s)
    blocked = sum(1 for _, s, _ in results if "BLOCKED" in s)
    uncertain = sum(1 for _, s, _ in results if "UNCERTAIN" in s)
    print(f"Summary: {valid} valid, {expired} expired, {no_session} no session, {blocked} blocked, {uncertain} uncertain")
    if expired or no_session:
        print("\nTo fix expired/missing sessions:")
        print("  python scripts/headful_reauth.py")
    if blocked:
        print("\nBlocked portals — Akamai is rejecting our headless User-Agent.")
        print("Sessions are likely fine in cookies; will work in normal pipeline run.")
        print("If pipeline runs also fail with 'Access Denied', retry headful: scripts/headful_reauth.py")


if __name__ == "__main__":
    asyncio.run(main())
