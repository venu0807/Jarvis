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
import random
import sys
from pathlib import Path

# Configure UTF-8 encoding for standard output and error to avoid UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from jarvis_browser import AsyncBrowser, safe_close_async

# Active portals (8 total, post 2026-06-15 cut).
# Career pages over took the linkedin/glassdoor-apply share: aggregator
# JSON APIs (Greenhouse/Lever/Ashby/Recruitee) auto-apply for free, and
# the catalog covers ~10k companies custom-ATS placeholders included.
# Re-enabling a cut portal: rerun scripts/apply_portal_cuts.py --restore <name>
# (kept as a noop harness if the cut script is removed; restoration is manual).
from portals import (NaukriPortal, IntersahalaPortal, IndeedPortal,
                     FounditPortal, CutshortPortal,
                     FreshersworldPortal, WellfoundPortal, CareerPagePortal, WorkdayPortal)
from portals.base import ApplicationResult
from db_logger import save_jobs_to_db

# ── Load .env ─────────────────────────────────────────────────────────────────
load_dotenv(Path(__file__).parent / ".env")

# ── Config ────────────────────────────────────────────────────────────────────
DAILY_LIMIT = int(os.getenv("DAILY_LIMIT", "15"))   # max applies per portal
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
    "Delhi", "Noida", "Greater Noida",
    "Gurugram", "Hyderabad", "Bangalore",
]

CREDS = {
    "naukri":        {"email": os.getenv("NAUKRI_EMAIL", ""),        "password": os.getenv("NAUKRI_PASSWORD", "")},
    "internshala":   {"email": os.getenv("INTERNSHALA_EMAIL", ""),  "password": os.getenv("INTERNSHALA_PASSWORD", "")},
    "indeed":        {"email": os.getenv("INDEED_EMAIL", ""),        "password": os.getenv("INDEED_PASSWORD", "")},
    "foundit":       {"email": os.getenv("FOUNDIT_EMAIL", ""),       "password": os.getenv("FOUNDIT_PASSWORD", "")},
    "cutshort":      {"email": os.getenv("CUTSHORT_EMAIL", os.getenv("GMAIL_ADDRESS", "")),       "password": os.getenv("CUTSHORT_PASSWORD", "")},
    "freshersworld": {"email": os.getenv("FRESHERSWORLD_EMAIL", os.getenv("GMAIL_ADDRESS", "")), "password": os.getenv("FRESHERSWORLD_PASSWORD", "")},
    "wellfound":     {"email": os.getenv("WELLFOUND_EMAIL", os.getenv("GMAIL_ADDRESS", "")),    "password": os.getenv("WELLFOUND_PASSWORD", "")},
    "career_pages":  {"email": os.getenv("GMAIL_ADDRESS", ""),       "password": ""},  # aggregator APIs are public
    "workday":       {"email": "",       "password": ""},  # public search, no auth needed
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

async def run_portal(portal_name: str, portal_cls, jobs: list, context) -> list:
    cred = CREDS[portal_name]
    # Skip credential check for portals that don't need auth (Workday, CareerPages)
    if portal_name not in ("workday", "career_pages"):
        if not cred["email"] or not cred["password"]:
            print(f"\n⚠️  {portal_name}: credentials not set in .env — skipping")
            return []

    portal  = portal_cls(email=cred["email"], password=cred["password"])
    page    = await context.new_page()
    results = []

    print(f"\n{'='*54}\n🌐 Portal: {portal.name}\n{'='*54}")

    try:
        # ── Login (uses saved session if valid) ───────────────────────────────────
        logged_in = await portal.login(page)
        if not logged_in:
            return []

        # ── Naukri: Playwright-based search after login ───────────────────────────
        if portal_name == "naukri":
            applied_today = load_applied()
            naukri_results = await portal.search_and_apply(page, ROLES, CITIES, DAILY_LIMIT, applied_today, context=context)
            save_applied({r.job["id"] for r in naukri_results if r.status == "applied"})
            return naukri_results

        # ── Indeed: Playwright-based search after login ───────────────────────────
        if portal_name == "indeed":
            applied_today = load_applied()
            indeed_results = await portal.search_and_apply(page, ROLES, CITIES, DAILY_LIMIT, applied_today)
            save_applied({r.job["id"] for r in indeed_results if r.status == "applied"})
            return indeed_results

        # ── Internshala: Playwright-based search after login ──────────────────────
        if portal_name == "internshala":
            applied_today = load_applied()
            internshala_results = await portal.search_and_apply(page, ROLES, CITIES, DAILY_LIMIT, applied_today)
            save_applied({r.job["id"] for r in internshala_results if r.status == "applied"})
            return internshala_results

        # ── CareerPages: company career pages (aggregator JSON APIs) ──────────────
        if portal_name == "career_pages":
            applied_today = load_applied()
            career_results = await portal.search_and_apply(page, ROLES, CITIES, DAILY_LIMIT, applied_today)
            save_applied({r.job["id"] for r in career_results if r.status == "applied"})
            return career_results

        # ── Foundit: Playwright-based search after login ──────────────────────────
        if portal_name == "foundit":
            applied_today = load_applied()
            foundit_results = await portal.search_and_apply(page, ROLES, CITIES, DAILY_LIMIT, applied_today)
            save_applied({r.job["id"] for r in foundit_results if r.status == "applied"})
            return foundit_results

        # ── Workday: public search + Playwright apply ─────────────────────────────
        if portal_name == "workday":
            applied_today = load_applied()
            workday_results = await portal.search_and_apply(page, ROLES, CITIES, DAILY_LIMIT, applied_today)
            save_applied({r.job["id"] for r in workday_results if r.status == "applied"})
            return workday_results

        # ── Other portals: use scraped jobs list ──────────────────────────────────
        applied_today  = load_applied()
        applied_count  = 0
        portal_jobs    = [j for j in jobs if j.get("portal", "").lower() == portal_name.lower()]
        print(f"  📋 {len(portal_jobs)} scraped jobs for {portal.name}")

        for job in portal_jobs:
            if applied_count >= DAILY_LIMIT:
                print(f"  ✋ Daily limit of {DAILY_LIMIT} reached for {portal.name}")
                break
            if job["id"] in applied_today:
                print(f"  ⏭️  Already applied: {job['title']} @ {job['company']}")
                continue

            print(f"\n  → {job['title']} @ {job['company']} ({job['location']})")
            result = await portal.apply_to_job(page, job)
            results.append(result)

            if result.status == "applied":
                applied_count += 1
                applied_today.add(job["id"])
                save_applied({job["id"]})
            elif result.status == "manual":
                print(f"     📋 Manual: {result.reason}")
            elif result.status == "skipped":
                print(f"     ⏭️  Skipped: {result.reason}")
            elif result.status == "error":
                print(f"     ❌ Error: {result.reason}")

            await asyncio.sleep(random.uniform(4, 8))

        return results

    finally:
        try:
            await page.close()
        except:
            pass



# ── Summary builder ───────────────────────────────────────────────────────────

def build_summary(all_results: list) -> dict:
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

async def main():
    parser = argparse.ArgumentParser(description="OpenClaw Auto-Apply Engine")
    parser.add_argument("--job-file", help="Path to scraped jobs JSON (optional — skips scraping)")
    parser.add_argument("--portal",   help="Run one portal only: naukri|internshala|indeed|foundit|cutshort|freshersworld|wellfound|career_pages|workday")
    parser.add_argument("--headful",  action="store_true", help="Run with a visible browser (overrides HEADLESS=.env)")
    args = parser.parse_args()

    jobs: list = []
    if args.job_file:
        job_path = Path(args.job_file)
        if job_path.exists():
            jobs = json.loads(job_path.read_text(encoding="utf-8"))
            print(f"\n📋 Loaded {len(jobs)} scraped jobs from {job_path.name}")

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
        "internshala":   IntersahalaPortal,
        "indeed":        IndeedPortal,
        "foundit":       FounditPortal,
        "cutshort":      CutshortPortal,
        "freshersworld": FreshersworldPortal,
        "wellfound":     WellfoundPortal,
        "career_pages":  CareerPagePortal,
        "workday":       WorkdayPortal,
    }
    if args.portal:
        if args.portal not in portal_map:
            print(f"❌ Unknown portal '{args.portal}'. Choose: {', '.join(portal_map)}")
            return
        portal_map = {args.portal: portal_map[args.portal]}

    all_results: list = []

    async with AsyncBrowser(headless=is_headless) as browser_mgr:
        for name, cls in portal_map.items():
            session_file = SESSION_DIR / f"{name}.json"
            if session_file.exists():
                print(f"\n💾 {name}: loading saved session from {session_file.name}")
            context = await browser_mgr.new_context_with_session(session_file)

            try:
                results = await run_portal(name, cls, jobs, context)
                all_results.extend(results)
                await browser_mgr.save_session(context, session_file)
            except Exception as e:
                print(f"\n❌ {name} portal crashed: {e}")
            finally:
                await safe_close_async(context)

    # Save all scraped jobs to the SQLite Database (for Interview Prep Bot)
    try:
        save_jobs_to_db(all_results)
    except Exception as dbe:
        print(f"\n⚠️  Could not save to local database: {dbe}")

    # Build and save summary
    summary  = build_summary(all_results)
    log_path = LOG_DIR / f"applications_{today}.json"
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


async def main_with_jobs(jobs: list) -> dict:
    """
    Called directly by run_pipeline.py with pre-scraped jobs.
    Returns the summary dict (so run_pipeline can do resume tailoring before notifying).
    """
    import sys
    # Inject --job-file equivalent by temporarily writing to a temp file
    today = datetime.date.today().isoformat()
    tmp_path = BASE_DIR / "output" / f"jobs_{today}.json"
    tmp_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path.write_text(json.dumps(jobs, ensure_ascii=False), encoding="utf-8")

    # Patch sys.argv so argparse in main() picks up the job file
    old_argv = sys.argv[:]
    sys.argv = [sys.argv[0], "--job-file", str(tmp_path)]
    try:
        result = await _run(jobs)
    finally:
        sys.argv = old_argv
    return result


async def _run(jobs: list, is_headless: bool = HEADLESS) -> dict:
    """Core apply logic used by both main() and main_with_jobs()."""
    today = datetime.date.today().isoformat()
    print(f"""
╔══════════════════════════════════════════════════╗
║   🦞 OpenClaw Auto-Apply Engine                  ║
║   {os.getenv('USER_FULL_NAME', 'User Name').ljust(46)} ║
║   Date:  {today}                       ║
║   Limit: {DAILY_LIMIT}/portal/day                        ║
╚══════════════════════════════════════════════════╝
""")

    portal_map = {
        "naukri":        NaukriPortal,
        "internshala":   IntersahalaPortal,
        "indeed":        IndeedPortal,
        "foundit":       FounditPortal,
        "cutshort":      CutshortPortal,
        "freshersworld": FreshersworldPortal,
        "wellfound":     WellfoundPortal,
        "career_pages":  CareerPagePortal,
        "workday":       WorkdayPortal,
    }

    all_results: list = []

    async with AsyncBrowser(headless=is_headless) as browser_mgr:
        for name, cls in portal_map.items():
            session_file = SESSION_DIR / f"{name}.json"
            if session_file.exists():
                print(f"\n💾 {name}: loading saved session")
            context = await browser_mgr.new_context_with_session(session_file)
            try:
                results = await run_portal(name, cls, jobs, context)
                all_results.extend(results)
                await browser_mgr.save_session(context, session_file)
            except Exception as e:
                print(f"\n❌ {name} portal crashed: {e}")
            finally:
                await safe_close_async(context)

    # Save all scraped jobs to the SQLite Database (for Interview Prep Bot)
    try:
        save_jobs_to_db(all_results)
    except Exception as dbe:
        print(f"\n⚠️  Could not save to local database: {dbe}")

    summary = build_summary(all_results)
    log_path = LOG_DIR / f"applications_{today}.json"
    log_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\n📊 Summary saved → {log_path}")

    t = summary["totals"]
    print(f"""
╔══════════════════════════════════════════════════╗
║   Auto-Apply Results:                            ║
║   Auto-applied:   {str(t['applied']).ljust(5)} jobs                  ║
║   Apply manually: {str(t['manual_total']).ljust(5)} jobs                  ║
║   Errors:         {str(t['errors']).ljust(5)}                        ║
╚══════════════════════════════════════════════════╝
""")
    return summary


if __name__ == "__main__":
    asyncio.run(main())
