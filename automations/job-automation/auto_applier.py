"""
auto_applier.py — Job application orchestrator
Flow: login all portals ONCE → search jobs → auto-apply → collect manual/skipped
Uses portal's own saved resume/profile — no file uploads.
Sessions persist via Playwright storage_state so login is skipped on future runs.
"""
import asyncio
import argparse
import datetime
import json
import os
import sys
import traceback
from pathlib import Path

# Configure UTF-8 encoding for standard output and error to avoid UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent))
sys.path.append(str(BASE_DIR.parent.parent))

from dotenv import load_dotenv
from jarvis_browser import AsyncBrowser, safe_close_async

# Active portals (4, post 2026-08-11 cut: removed cutshort/freshersworld/
# wellfound/career_pages/workday — re-login burden + aggregator auth-less
# niches not worth the maintenance). Re-enabling a cut portal: restore the
# module + re-add to CREDS/portal_map.
from portals import (NaukriPortal, InternshalaPortal, IndeedPortal,
                     FounditPortal)
from db_logger import save_jobs_to_db

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

# ── Config ────────────────────────────────────────────────────────────────────
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "20"))   # max applies per portal
HEADLESS    = os.getenv("HEADLESS", "false").lower() == "true"

ROLES = [
    "Python Developer",
    "Django Developer",
    "Backend Developer",
    "Full Stack Python Developer",
    "AI ML Engineer",
    "Software Developer Python",
]

# Dynamically add internship variations for all roles
intern_roles = [r.replace("Developer", "").replace("Engineer", "").strip() + " Intern" for r in ROLES]
intern_roles = list(set([r for r in intern_roles if r])) # Deduplicate
ROLES.extend(intern_roles)

CITIES = [
    "Gurugram", "Noida", "Greater Noida", "Delhi", "Hyderabad", "Bangalore",
]

CREDS = {
    "naukri":        {"email": os.getenv("NAUKRI_EMAIL", ""),        "password": os.getenv("NAUKRI_PASSWORD", "")},
    "internshala":   {"email": os.getenv("INTERNSHALA_EMAIL", ""),  "password": os.getenv("INTERNSHALA_PASSWORD", "")},
    "indeed":        {"email": os.getenv("INDEED_EMAIL", ""),        "password": os.getenv("INDEED_PASSWORD", "")},
    "foundit":       {"email": os.getenv("FOUNDIT_EMAIL", ""),       "password": os.getenv("FOUNDIT_PASSWORD", "")},
}

BASE_DIR    = Path(__file__).parent
SESSION_DIR = BASE_DIR / ".sessions"
LOG_DIR     = BASE_DIR / "output" / "logs"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
APPLIED_LOG = LOG_DIR / "applied_jobs.json"

# ── Applied job tracker ───────────────────────────────────────────────────────

def load_applied() -> set:
    try:
        if APPLIED_LOG.exists():
            return set(json.loads(APPLIED_LOG.read_text()))
    except:
        pass
    return set()


def save_applied(new_ids: set):
    existing = load_applied()
    merged = existing | new_ids
    APPLIED_LOG.write_text(json.dumps(list(merged), indent=2))


# ── Portal runner ─────────────────────────────────────────────────────────────

async def run_portal(portal_name: str, portal_cls, context) -> tuple[list, bool]:
    """Run one portal. Returns (results, session_ok).

    session_ok=False means the saved auth session was rejected/expired and
    the portal is skipped (0 applies). The caller surfaces this so a stale
    session gets a one-time manual re-login instead of silently returning 0.
    """
    cred = CREDS[portal_name]
    if not cred["email"] or not cred["password"]:
        print(f"\n⚠️  {portal_name}: credentials not set in .env — skipping")
        return [], False

    portal  = portal_cls(email=cred["email"], password=cred["password"])
    page    = await context.new_page()

    print(f"\n{'='*54}\n🌐 Portal: {portal.name}\n{'='*54}")

    try:
        # ── Login (uses saved session if valid) ───────────────────────────────────
        logged_in = await portal.login(page)
        if not logged_in:
            print(f"  ⚠️  {portal_name}: session rejected — needs a one-time manual re-login")
            return [], False

        # ── Live search + apply ───────────────────────────────────────────────────
        # All 9 portals implement search_and_apply(page, roles, cities,
        # daily_limit, applied_today). Naukri additionally takes context= for
        # page-recovery on crash; the others don't. (Previously this was 6
        # copy-pasted branches + a scraped-jobs fallback that was dead in the
        # daily run because `jobs` was always empty without --job-file.)
        #
        applied_today = load_applied()
        if portal_name == "naukri":
            results = await portal.search_and_apply(
                page, ROLES, CITIES, DAILY_LIMIT, applied_today,
                context=context
            )
        else:
            results = await portal.search_and_apply(
                page, ROLES, CITIES, DAILY_LIMIT, applied_today
            )
        save_applied({r.job["id"] for r in results if r.status == "applied"})
        return results, True

    finally:
        try:
            await page.close()
        except:
            pass



# ── Summary builder ───────────────────────────────────────────────────────────

def build_summary(all_results: list, needs_relogin: list | None = None) -> dict:
    applied  = [r for r in all_results if r.status == "applied"]
    manual   = [r for r in all_results if r.status == "manual"]
    skipped  = [r for r in all_results if r.status == "skipped"]
    errors   = [r for r in all_results if r.status == "error"]

    # Per-portal counts
    portal_counts: dict = {}
    for r in applied:
        p = r.job.get("portal", "unknown")
        portal_counts[p] = portal_counts.get(p, 0) + 1

    # Build applied list
    applied_list = [
        {
            "title":   r.job["title"],
            "company": r.job["company"],
            "portal":  r.job.get("portal", ""),
            "url":     r.job.get("url", ""),
        }
        for r in applied
    ]

    # Manual + skipped → all need human attention
    # resume_pdf will be filled in by run_pipeline.py after tailoring
    manual_list = [
        {
            "title":      r.job["title"],
            "company":    r.job["company"],
            "portal":     r.job.get("portal", ""),
            "url":        r.job.get("url", ""),
            "location":   r.job.get("location", ""),
            "reason":     r.reason,
            "resume_pdf": "",  # filled by run_pipeline.py
        }
        for r in manual
    ] + [
        {
            "title":      r.job["title"],
            "company":    r.job["company"],
            "portal":     r.job.get("portal", ""),
            "url":        r.job.get("url", ""),
            "location":   r.job.get("location", ""),
            "reason":     r.reason or "Skipped",
            "resume_pdf": "",
        }
        for r in skipped if r.reason and "Already applied" not in r.reason and "Redirected after apply" not in r.reason
    ]

    return {
        "date":          datetime.date.today().isoformat(),
        "portal_counts": portal_counts,
        "applied":       applied_list,
        "manual":        manual_list,
        "needs_relogin": needs_relogin or [],
        "totals": {
            "applied":             len(applied),
            "manual":              len(manual),
            "skipped":             len(skipped),
            "errors":              len(errors),
            "manual_total":        len(manual_list),
        },
        # Keep raw results for resume tailoring (job dicts)
        "_manual_jobs": [
            {"job": r.job, "reason": r.reason}
            for r in manual
        ],
        "_skipped_jobs": [
            {"job": r.job, "reason": "No Easy Apply — apply directly on portal"}
            for r in skipped
        ],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def _acquire_run_lock() -> bool:
    """Prevent overlapping pipeline runs. Stale-lock tolerant: if the PID
    in the lockfile is no longer alive, the lock is considered free."""
    lock_path = Path(__file__).parent / "output" / ".pipeline.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if lock_path.exists():
            prior_pid = lock_path.read_text().strip()
            if prior_pid.isdigit() and prior_pid != str(os.getpid()):
                try:
                    os.kill(int(prior_pid), 0)
                    # verify it's actually our python process, not a reused PID
                    try:
                        cmdline = Path(f"/proc/{prior_pid}/comm").read_text().strip()
                        if "python" not in cmdline.lower():
                            raise ProcessLookupError("PID reused by non-python process")
                    except FileNotFoundError:
                        pass
                    print(f"⛔ Another pipeline run is active (pid {prior_pid}). Exiting to avoid clobbering today's summary.")
                    return False
                except (ProcessLookupError, PermissionError, ValueError):
                    pass  # stale lock from a dead process — take it over
        lock_path.write_text(str(os.getpid()))
        return True
    except Exception as e:
        print(f"⚠️  Lock check failed ({e}) — proceeding without lock")
        return True


async def main():
    if not _acquire_run_lock():
        return
    parser = argparse.ArgumentParser(description="OpenClaw Auto-Apply Engine")
    parser.add_argument("--portal",   help="Run one portal only: naukri|internshala|indeed|foundit")
    parser.add_argument("--headful",  action="store_true", help="Run with a visible browser (overrides HEADLESS=.env)")
    args = parser.parse_args()

    today = datetime.date.today().isoformat()

    # [Staff Engineer Refactor]: Removed global mutation of HEADLESS. Passed explicitly.
    is_headless = HEADLESS
    if args.headful:
        is_headless = False
        
    mode_str = "headless" if is_headless else "visible browser"
    print(f"""
╔══════════════════════════════════════════════════╗
║   🦞 OpenClaw Auto-Apply Engine                 ║
║   Venu Gopal Reddy                               ║
║   Date:  {today}                                 ║
║   Limit: {DAILY_LIMIT}/portal/day                ║
║   Mode:  {mode_str}                              ║
╚══════════════════════════════════════════════════╝
""")

    portal_map = {
        "naukri":        NaukriPortal,
        "internshala":   InternshalaPortal,
        "indeed":        IndeedPortal,
        "foundit":       FounditPortal,
    }
    if args.portal:
        if args.portal not in portal_map:
            print(f"❌ Unknown portal '{args.portal}'. Choose: {', '.join(portal_map)}")
            return
        portal_map = {args.portal: portal_map[args.portal]}

    all_results: list = []
    needs_relogin: list = []

    async with AsyncBrowser(headless=is_headless) as browser_mgr:
        for name, cls in portal_map.items():
            session_file = SESSION_DIR / f"{name}.json"
            if session_file.exists():
                print(f"\n💾 {name}: loading saved session from {session_file.name}")

            context = None
            try:
                context = await browser_mgr.new_context_with_session(session_file)
                results, session_ok = await run_portal(name, cls, context)
                all_results.extend(results)
                if not session_ok:
                    needs_relogin.append(name)
                
                # Save results immediately to DB after each portal
                try:
                    save_jobs_to_db(results)
                except Exception as dbe:
                    print(f"  ⚠️ Could not save {name} jobs to DB: {dbe}")

                await browser_mgr.save_session(context, session_file)
            except Exception as e:
                print(f"\n❌ {name} portal error: {e}")
            finally:
                if context:
                    await safe_close_async(context)

    # Save all scraped jobs to the SQLite Database (for Interview Prep Bot)
    try:
        save_jobs_to_db(all_results)
    except Exception as dbe:
        print(f"\n⚠️  Could not save to local database: {dbe}")

    # Build and save summary
    summary  = build_summary(all_results, needs_relogin)
    log_path = LOG_DIR / f"applications_{today}.json"

    # Don't overwrite a non-empty same-day summary with an all-empty one.
    # A crashed/early-exit run produces zeros and would otherwise wipe
    # results already recorded by an earlier, successful run today.
    new_total = summary["totals"].get("applied", 0) + summary["totals"].get("manual", 0)
    try:
        if not new_total and log_path.exists():
            existing = json.loads(log_path.read_text(encoding="utf-8"))
            old_total = (existing.get("totals", {}).get("applied", 0)
                         + existing.get("totals", {}).get("manual", 0))
            if old_total:
                print(f"\n⚠️  This run found 0 jobs but applications_{today}.json already has "
                      f"{old_total} results — KEEPING existing summary instead of overwriting.")
                return summary
    except (json.JSONDecodeError, OSError):
        pass

    log_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n📊 Summary saved → {log_path}")

    t = summary["totals"]
    print(f"""
╔══════════════════════════════════════════════════╗
║   ✅ Auto-Apply Complete!                        ║
║   Auto-applied:   {str(t['applied']).ljust(5)} jobs                  ║
║   Apply manually: {str(t['manual_total']).ljust(5)} jobs (links in email)   ║
║   Errors:         {str(t['errors']).ljust(5)}                        ║
╚══════════════════════════════════════════════════╝
""")

    # Print per-portal stats
    if summary["portal_counts"]:
        print("📈 Auto-applied by portal:")
        for pname, count in summary["portal_counts"].items():
            print(f"   {pname}: {count}")

    return summary


if __name__ == "__main__":
    asyncio.run(main())
