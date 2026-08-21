#!/usr/bin/env python3
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
from typing import Union, Optional

# Configure UTF-8 encoding for standard output and error to avoid UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent))
sys.path.append(str(BASE_DIR.parent.parent))

from dotenv import load_dotenv
from browser import AsyncBrowser, safe_close_async

# Active portals (4, post 2026-08-11 cut: removed cutshort/freshersworld/
# wellfound/career_pages/workday — re-login burden + aggregator auth-less
# niches not worth the maintenance). Re-enabling a cut portal: restore the
# module + re-add to CREDS/portal_map.
from portals import (NaukriPortal, InternshalaPortal, IndeedPortal,
                     FounditPortal)
from db_logger import save_jobs_to_db
from event_bus import get_bus  # Cross-automation event bus
from alert_manager import send_alert, send_info, send_warning, send_critical  # Alerting

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

# ── Config ────────────────────────────────────────────────────────────────────
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "20"))   # max applies per portal
HEADLESS    = os.getenv("HEADLESS", "false").lower() == "true"

# Concurrency control: max 2 portals running simultaneously to limit browser contexts
PORTAL_SEMAPHORE = asyncio.Semaphore(int(os.getenv("MAX_CONCURRENT_PORTALS", "2")))

ROLES = [
    "Python Developer",
    "Django Developer",
    "Backend Developer",
    "Full Stack Python Developer",
    "AI ML Engineer",
    "Software Developer Python",
    "Junior Full-Stack AI Engineer",
    "Junior ML Engineer (Applied)",
    "Junior Automation Engineer (Python-Focused)",
    "Junior DevOps Engineer (MLOps-Lean)",
    "Junior Backend Engineer (AI-Enabled Services)",
    "Junior Data Analyst",
    "Business Analyst (Data-Focused)",
    "Operations Analyst",
    "Marketing Analyst (Product-Focused)",
    "Data Analyst – SQL / ETL Focus",
]

SKILL_BASED_ROLES = [
    "Python Django Developer",
    "Django Developer",
    "Backend Developer (Python)",
    "Frontend Developer (React)",
    "React Developer",
    "Full Stack Developer (Python/React)",
    "Machine Learning Engineer",
    "AI Engineer",
    "Deep Learning Engineer",
    "Database Developer",
    "SQL Developer",
    "Backend Developer (SQL)",
    "DevOps Engineer",
    "CI/CD Engineer",
    "Platform Engineer",
    "Automation Engineer",
    "QA Automation Engineer",
    "Python Automation Developer",
    "Data Analyst",
    "Business Analyst",
    "SQL Analyst",
]
ROLES.extend(SKILL_BASED_ROLES)
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
# Use WSL-compatible path for session directory
HOME_DIR = Path(os.getenv("JARVIS_HOME", Path.home()))
SESSION_DIR = HOME_DIR / ".jarvis" / "automations" / "job-automation" / ".sessions"
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

def build_summary(all_results: list, needs_relogin: Optional[list] = None) -> dict:
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
                # PID alive?
                try:
                    os.kill(int(prior_pid), 0)
                    print(f"⛔ Another pipeline run is active (pid {prior_pid}). Exiting to avoid clobbering today's summary.")
                    return False
                except (ProcessLookupError, PermissionError, ValueError):
                    pass  # stale lock from a dead process — take it over
        lock_path.write_text(str(os.getpid()))
        return True
    except Exception as e:
        print(f"⚠️  Lock check failed ({e}) — proceeding without lock")
        return True


async def _run_single_portal_impl(name: str, cls, browser_mgr: AsyncBrowser) -> tuple[str, list, bool]:
    """Implementation of single portal run (without semaphore)."""
    session_file = SESSION_DIR / f"{name}.json"
    if session_file.exists():
        print(f"\n💾 {name}: loading saved session from {session_file.name}")
    context = await browser_mgr.new_context_with_session(session_file)
    try:
        results, session_ok = await run_portal(name, cls, context)
        await browser_mgr.save_session(context, session_file)
        return name, results, session_ok
    except Exception as e:
        print(f"\n❌ {name} portal crashed: {e}")
        traceback.print_exc()
        return name, [], False
    finally:
        await safe_close_async(context)


async def _run_single_portal(name: str, cls, browser_mgr: AsyncBrowser) -> tuple[str, list, bool]:
    """Run one portal and return (name, results, session_ok)."""
    # Use semaphore to limit concurrent portals
    async with PORTAL_SEMAPHORE:
        return await _run_single_portal_impl(name, cls, browser_mgr)


async def main():
    if not _acquire_run_lock():
        return

    # Parse arguments inside main() to avoid module-level execution on import
    parser = argparse.ArgumentParser(description="Auto-apply to jobs across portals")
    parser.add_argument("--portal", choices=["naukri", "internshala", "indeed", "foundit"], help="Run only one portal")
    parser.add_argument("--headful", action="store_true", help="Run with visible browser (overrides HEADLESS)")
    args = parser.parse_args()

    today = datetime.date.today().isoformat()

    # [Staff Engineer Refactor]: Removed global mutation of HEADLESS. Passed explicitly.
    is_headless = HEADLESS
    if args.headful:
        is_headless = False

    mode_str = "headless" if is_headless else "visible browser"
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════════╗
║   🦞 OpenClaw Auto-Apply Engine                 ║
║   Venu Gopal Reddy                               ║
║   Date:  {today}                                 ║
║   Limit: {DAILY_LIMIT}/portal/day                ║
║   Mode:  {mode_str}                              ║
╚══════════════════════════════════════════════════════════════════════════════════╝
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

    async def _run_single_portal(name: str, cls, browser_mgr: AsyncBrowser) -> tuple[str, list, bool]:
        """Run one portal and return (name, results, session_ok)."""
        # Use semaphore to limit concurrent portals
        async with PORTAL_SEMAPHORE:
            return await _run_single_portal_impl(name, cls, browser_mgr)

    async with AsyncBrowser(headless=is_headless) as browser_mgr:
        # Run all portals in parallel using asyncio.gather
        tasks = [
            _run_single_portal(name, cls, browser_mgr)
            for name, cls in portal_map.items()
        ]
        portal_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in portal_results:
            if isinstance(result, Exception):
                print(f"\n❌ Portal task raised: {result}")
                continue
            name, results, session_ok = result
            all_results.extend(results)
            if not session_ok:
                needs_relogin.append(name)

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

    # 🔗 Cross-automation triggers: publish job.applied events
    try:
        bus = get_bus()
        for applied_job in summary.get("applied", []):
            bus.publish(
                channel="job-automation",
                event_type="job.applied",
                payload={
                    "job_title": applied_job["title"],
                    "company": applied_job["company"],
                    "portal": applied_job["portal"],
                    "url": applied_job["url"],
                    "date": summary["date"],
                }
            )
        print(f"📡 Published {len(summary.get('applied', []))} job.applied events")
    except Exception as e:
        print(f"⚠️  Could not publish events: {e}")

    # Check for zero-apply alerts
    await check_and_alert_zero_applies(summary)

    t = summary["totals"]
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════════════════╗
║   ✅ Auto-Apply Complete!                        ║
║   Auto-applied:   {str(t['applied']).ljust(5)} jobs                  ║
║   Apply manually: {str(t['manual_total']).ljust(5)} jobs (links in email)   ║
║   Errors:         {str(t['errors']).ljust(5)}                        ║
╚═════════════════════════════════════════════════════════════════════════════════════╝
""")

    # Print per-portal stats
    if summary["portal_counts"]:
        print("📈 Auto-applied by portal:")
        for pname, count in summary["portal_counts"].items():
            print(f"   {pname}: {count}")

    return summary


# Track consecutive zero-apply runs for alerting
ZERO_APPLY_TRACKER = Path(__file__).parent / "output" / ".zero_apply_tracker.json"


async def check_and_alert_zero_applies(summary: dict):
    """Check for consecutive zero-apply runs and alert if needed."""
    applied_count = summary["totals"].get("applied", 0)
    manual_count = summary["totals"].get("manual_total", 0)
    total_actionable = applied_count + manual_count

    # Load tracker
    tracker = {"consecutive_zero": 0, "last_date": None}
    if ZERO_APPLY_TRACKER.exists():
        try:
            tracker = json.loads(ZERO_APPLY_TRACKER.read_text())
        except:
            pass

    today = summary["date"]

    if total_actionable == 0:
        if tracker["last_date"] == today:
            # Already counted today
            pass
        else:
            tracker["consecutive_zero"] += 1
            tracker["last_date"] = today
    else:
        tracker["consecutive_zero"] = 0
        tracker["last_date"] = today

    # Save tracker
    ZERO_APPLY_TRACKER.parent.mkdir(parents=True, exist_ok=True)
    ZERO_APPLY_TRACKER.write_text(json.dumps(tracker, indent=2))

    # Alert if 2+ consecutive zero-apply runs
        if tracker["consecutive_zero"] >= 2:
            send_warning(
                "Job Automation: Zero Applications",
                f"Job automation has had {tracker['consecutive_zero']} consecutive runs "
                f"with zero applications. Check portal sessions and credentials.",
                "job-automation",
                consecutive_zero=tracker["consecutive_zero"],
                date=today
            )


if __name__ == "__main__":
    asyncio.run(main())