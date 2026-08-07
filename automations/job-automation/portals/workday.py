"""
portals/workday.py — Workday ATS scraper + auto-apply.

Workday powers ~30% of Fortune 500 career sites (Cisco, Intel, IBM, Oracle,
Walmart, Target, etc.). It uses a TWO-STAGE model:

  Stage 1 (search): public POST endpoint returns open jobs, no auth needed.
        POST https://{tenant}.{subdomain}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs
        Body:  {"limit": 20, "offset": 0, "searchText": "Python", "appliedFacets": {}}
        Returns: {"total": 2000, "jobPostings": [{title, locationsText, externalPath, ...}]}

  Stage 2 (apply): full Playwright form-fill. Workday apply pages are ~5-step:
        account create → resume upload → questions → review → submit.
        We use Playwright + AngularJS selectors + headless mode.

Why this is in portals/, not just a util:
- companies.json holds the Workday tenants, parallel to your existing Greenhouse entries
- auto_applier.py --portal workday dispatches to it (name unified to match other
  portals)
- Returns standard ApplicationResult like every other portal — keeps the contract

Fallback if Workday blocks or 403s:
- Mark the job "manual" with the public URL → user's email summary lists it for
  one-click apply (same fallback pattern as Greenhouse 4xx)
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional, List

import requests

from .profile import _PROFILE, resolve_resume_path as _resolve_resume_path


# ── Public Workday tenant catalog (verified live, returns HTTP 200) ────────────
# Add more only after confirming the tenant + subdomain + site path via:
#   1. Visit company's careers page
#   2. Note the redirected URL: https://{tenant}.{sub}.myworkdayjobs.com/en-US/{site}
#   3. POST to /wday/cxs/{tenant}/{site}/jobs with {"limit": 20, "appliedFacets": {}}
#
# Format: (tenant_slug, subdomain, careers_site_path, display_name)
WORKDAY_TENANTS: List[dict] = [
    # VERIFIED LIVE — confirmed HTTP 200 + total > 0 jobs (tested 2026-06-18)
    {"key": "target", "tenant": "target", "sub": "wd5", "site": "TargetCareers",
     "name": "Target", "verified": "2026-06-18, 200 OK, 2000 jobs"},

    # KNOWN LIVE TENANTS — endpoint reachable but returned 422 (site path uncertain).
    # To enable each, open the careers page manually and note the path segment
    # between /en-US/ and /jobs.
    # {"key": "accenture",  "tenant": "accentureglobal", "sub": "wd103", "site": "...", "name": "Accenture"},
    # {"key": "paypal",     "tenant": "paypal",          "sub": "wd12",  "site": "...", "name": "PayPal"},
    # {"key": "dell",       "tenant": "dell",            "sub": "wd5",   "site": "...", "name": "Dell"},
    # {"key": "walmart",    "tenant": "wal",             "sub": "wd5",   "site": "...", "name": "Walmart"},
    # {"key": "cisco",      "tenant": "cisco",           "sub": "wd5",   "site": "...", "name": "Cisco"},
    # {"key": "ibm",        "tenant": "ibm",             "sub": "wd5",   "site": "...", "name": "IBM"},
    # {"key": "oracle",     "tenant": "oracle",          "sub": "wd5",   "site": "...", "name": "Oracle"},
    # {"key": "intel",      "tenant": "intel",           "sub": "wd5",   "site": "...", "name": "Intel"},
    # {"key": "vmware",     "tenant": "vmware",          "sub": "wd5",   "site": "...", "name": "VMware"},
]

# ── Endpoints ─────────────────────────────────────────────────────────────────

APPLY_BASE_URL = "https://{tenant}.{sub}.myworkdayjobs.com/en-US/{site}{path}"
SEARCH_URL     = "https://{tenant}.{sub}.myworkdayjobs.com/wday/cxs/{tenant}/{site}/jobs"


# ── Stage 1: search (no auth) ───────────────────────────────────────────────

def search_jobs(tenant: dict, role_keywords: List[str], cities: List[str], limit: int = 20) -> List[dict]:
    """Hit Workday's public search endpoint with role/city filters. No login.
    Returns list of standard {id, title, company, location, url, description, portal} dicts.
    """
    url = SEARCH_URL.format(
        tenant=tenant["tenant"], sub=tenant["sub"], site=tenant["site"]
    )
    try:
        payload = {
            "limit":      min(limit * 2, 20),  # Workday API rejects limit > 20
            "offset":     0,
            "appliedFacets": {},
        }
        r = requests.post(url, json=payload, timeout=20,
                          headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
        if r.status_code != 200:
            print(f"  ⚠ Workday search {tenant['key']}: HTTP {r.status_code}")
            return []
        data = r.json()
    except Exception as e:
        print(f"  ⚠ Workday search {tenant['key']}: {type(e).__name__}: {str(e)[:80]}")
        return []

    out = []
    role_pat = _compile_role_patterns(role_keywords)
    for raw in data.get("jobPostings", []):
        title   = raw.get("title", "")
        loc_txt = raw.get("locationsText", "")
        path    = raw.get("externalPath", "")

        if not _role_match(title, role_pat):
            continue
        if cities and not any(c.lower() in loc_txt.lower() for c in cities):
            continue

        full_url = APPLY_BASE_URL.format(tenant=tenant["tenant"], sub=tenant["sub"],
                                          site=tenant["site"], path=path)
        out.append({
            "id":          f"wd_{tenant['key']}_{raw.get('bulletFields', [''])[0] if raw.get('bulletFields') else path.split('/')[-1]}",
            "title":       title,
            "company":     tenant["name"],
            "location":    loc_txt,
            "url":         full_url,
            "apply_url":   full_url + "/apply",
            "description": "",
            "portal":      "Workday",
            "_tenant":     tenant["key"],
            "_externalPath": path,
        })
        if len(out) >= limit:
            break
    return out


def search_all_workday(roles: List[str], cities: List[str], limit: int = 20) -> List[dict]:
    """Search across every Workday tenant in WORKDAY_TENANTS."""
    all_jobs: List[dict] = []
    for tenant in WORKDAY_TENANTS:
        print(f"  → Workday: {tenant['name']}")
        jobs = search_jobs(tenant, roles, cities, limit=limit)
        print(f"     {len(jobs)} jobs pass filter")
        all_jobs.extend(jobs)
        if len(all_jobs) >= limit * 2:
            break
    return all_jobs


# ── Stage 2: apply (Playwright form fill) ────────────────────────────────────

def apply_to_job(job: dict, profile: dict, resume_pdf: Optional[str],
                 headless: bool = True, context=None) -> tuple[bool, str]:
    """Playwright-driven Workday application form fill.
    Returns (success: bool, reason: str).
    Profile dict: {first_name, last_name, email, phone, linkedin}.
    context: optional pre-launched persistent BrowserContext. When given, a
    page is opened on it and no new browser is launched (shared-browser mode
    used by _apply_workday_run). Otherwise a fresh browser is launched for
    standalone/CLI use.
    """
    try:
        from jarvis_browser import SyncBrowser, safe_close_sync
    except ImportError:
        return False, "playwright not installed — pip install playwright && playwright install chromium"

    apply_url = job.get("apply_url") or job.get("url", "")
    if not apply_url:
        return False, "no apply_url on job dict"
    if not apply_url.endswith("/apply"):
        apply_url = apply_url.rstrip("/") + "/apply"

    if context is not None:
        # Shared-browser mode: reuse the caller's persistent context.
        page = context.new_page()
        try:
            return _run_apply_flow(page, apply_url, profile, resume_pdf)
        finally:
            safe_close_sync(page)

    with SyncBrowser(headless=headless) as browser_mgr:
        try:
            browser = browser_mgr.launch_persistent(
                user_data_dir=str(Path.home() / ".jarvis" / "wd_browser" / job.get("_tenant", "tmp")),
                extra_kwargs={"viewport": {"width": 1280, "height": 900}},
            )
        except Exception as e:
            return False, f"launch_persistent_context failed: {type(e).__name__}: {str(e)[:120]}"

        page = browser.new_page()
        try:
            return _run_apply_flow(page, apply_url, profile, resume_pdf)
        finally:
            safe_close_sync(page)


def _run_apply_flow(page, apply_url: str, profile: dict, resume_pdf: Optional[str]) -> tuple[bool, str]:
    """The 6-stage Workday form-fill on an already-open page."""
    try:
        page.goto(apply_url, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(3000)

        # Click "Apply" if there's an intermediate page
        try:
            apply_btn = page.get_by_role("button", name=re.compile(r"Apply", re.I)).first
            if apply_btn.is_visible(timeout=5000):
                apply_btn.click()
                page.wait_for_timeout(3000)
        except Exception:
            pass

        # Stage 1: account creation
        handled_account = _try_fill_account(page, profile)
        if handled_account == "captcha":
            return False, "captcha encountered — manual apply required"

        # Stage 2: resume upload
        if resume_pdf and Path(resume_pdf).exists():
            uploaded = _try_upload_resume(page, resume_pdf)
            if not uploaded:
                print(f"  ⚠ resume upload failed — continuing (Workday allows skip + paste)")

        # Stage 3: my information (contact info)
        _try_fill_my_info(page, profile)

        # Stage 4: my experience
        _try_fill_experience(page, profile)

        # Stage 5: voluntary disclosures + EEO
        _try_skip_voluntary(page)

        # Stage 6: review then submit
        submitted = _try_submit(page)
        return submitted, "submitted" if submitted else "submit button not found"
    except Exception as e:
        return False, f"exception in apply flow: {type(e).__name__}: {str(e)[:120]}"


# ── Form-fill helpers (best-effort — Workday UIs differ per tenant) ─────────

def _try_fill_account(page, profile: dict) -> str:
    """If 'Sign in' / 'Apply with LinkedIn' / 'Use my last application' buttons
    appear, take the manual path. Returns 'captcha' if CAPTCHA detected.
    """
    if "captcha" in page.content().lower() or "i am human" in page.content().lower():
        return "captcha"
    # Try "Apply Manually"
    try:
        btn = page.get_by_role("button", name=re.compile(r"apply manually|create account|new application", re.I)).first
        if btn.is_visible(timeout=4000):
            btn.click()
            page.wait_for_timeout(2000)
    except Exception:
        pass
    return "ok"


def _try_upload_resume(page, resume_pdf: str) -> bool:
    """Find the file input (often via drag-drop or 'Upload Resume' link)
    and call set_input_files()."""
    try:
        file_input = page.locator('input[type="file"]').first
        file_input.set_input_files(resume_pdf, timeout=15000)
        page.wait_for_timeout(2000)
        return True
    except Exception as e:
        # Try drag-drop zone → triggers click on a hidden file input
        try:
            drop = page.locator('[data-automation-id*="drop"]').first
            drop.click(timeout=8000)
            page.wait_for_timeout(1500)
            file_input = page.locator('input[type="file"]').first
            file_input.set_input_files(resume_pdf, timeout=15000)
            return True
        except Exception:
            return False


def _try_fill_my_info(page, profile: dict) -> None:
    """Best-effort fill of First Name / Last Name / Phone / Email fields."""
    # First name — Workday typically uses data-automation-id="nameSection.firstName"
    field_map = [
        ("nameSection.firstName",     profile.get("first_name", "")),
        ("nameSection.lastName",      profile.get("last_name", "")),
        ("email",                     profile.get("email", "")),
        ("phoneNumber",               profile.get("phone", "").replace(" ", "").replace("-", "")),
        ("linkedin",                  profile.get("linkedin", "") or ""),
    ]
    for fragment, value in field_map:
        if not value:
            continue
        try:
            el = page.locator(f'[data-automation-id*="{fragment}"]').first
            if el.is_visible(timeout=2000):
                el.click()
                el.fill(value)
                page.wait_for_timeout(300)
        except Exception:
            continue
    return None


def _try_fill_experience(page, profile: dict) -> None:
    """Workday 'My Experience' page usually asks 'Years of relevant experience'
    as a select. We pick the largest option (most realistic for a job applicant)."""
    try:
        sel = page.locator('[data-automation-id*="yearsOfExperience"]').first
        if sel.is_visible(timeout=3000):
            options = sel.locator("option").all_text_contents()
            if options:
                # Use 1-2 yrs as a junior/applicant value if "Fresher" or 0-1 exists
                # Otherwise pick "2-4" or first non-zero option
                best = next((o for o in options if "1" in o and ("1" in o.split("-")[0] or o.lower().startswith("1"))), None) or options[0]
                sel.select_option(label=best)
                page.wait_for_timeout(500)
    except Exception:
        pass
    return None


def _try_skip_voluntary(page) -> None:
    """Voluntary disclosures (gender/race/veteran) — click 'Decline to Self-Identify'
    if present, to avoid biasing the application."""
    try:
        btn = page.get_by_role("button", name=re.compile(r"decline", re.I)).first
        if btn.is_visible(timeout=3000):
            btn.click()
            page.wait_for_timeout(1500)
    except Exception:
        pass
    return None


def _try_submit(page) -> bool:
    """Final step — 'Submit' button. Clicks if found. Returns True if visible."""
    try:
        submit = page.get_by_role("button", name=re.compile(r"^submit$", re.I)).first
        if submit.is_visible(timeout=5000):
            submit.click()
            page.wait_for_timeout(4000)
            return True
    except Exception:
        return False
    return False


# ── Helpers ───────────────────────────────────────────────────────────────────

def _compile_role_patterns(role_keywords: List[str]) -> list:
    """Convert role strings to a list of lowercase word matches."""
    out = []
    for k in role_keywords:
        for word in k.lower().split():
            if len(word) > 2:
                out.append(word)
    return out or ["python", "developer", "engineer"]


def _role_match(title: str, patterns: list) -> bool:
    t = title.lower()
    return any(p in t for p in patterns)


# ── CLI smoke runner ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    roles  = sys.argv[1].split(",") if len(sys.argv) > 1 else ["Python Developer"]
    cities = sys.argv[2].split(",") if len(sys.argv) > 2 else ["Bangalore", "Hyderabad"]

    print(f"=== WORKDAY SEARCH ===")
    print(f"Roles:  {roles}")
    print(f"Cities: {cities}\n")

    jobs = search_all_workday(roles, cities, limit=5)
    print(f"\n=== TOTAL: {len(jobs)} jobs across {len(WORKDAY_TENANTS)} Workday tenants ===\n")
    for j in jobs[:15]:
        print(f"   • [{j['company']:15}] {j['title'][:55]:55}")
        print(f"     {j['location'][:55]:55}")
        print(f"     {j['url'][:80]}")
        print()


# ── Base-portal wrapper (so auto_applier.py can `from portals import WorkdayPortal`) ─

class WorkdayPortal:
    """Wraps the search_all_workday + apply_to_job helpers into the same
    interface as every other Portal (login → search_and_apply → close)."""
    name = "Workday"

    def __init__(self, email: str = "", password: str = ""):
        # No login needed for search. Apply uses saved browser session.
        self.email = email
        self.password = password

    async def login(self, page) -> bool:
        # Public POST is unauthenticated — always returns True for search.
        return True

    async def search_and_apply(self, page, roles, cities, daily_limit, applied_today, **kwargs):
        """Public search + Playwright apply, capped to daily_limit per company.

        One shared persistent browser context for the whole run instead of one
        full Chromium launch per job (was ~1-3s + ~150MB per job). Workday
        apply is an unauthenticated public form, so a single profile is fine.
        """
        import asyncio
        from .base import ApplicationResult
        loop = asyncio.get_running_loop()
        # Run the search synchronously in a thread → returns list of jobs
        jobs = await loop.run_in_executor(
            None,
            lambda: search_all_workday(roles, cities, limit=max(20, daily_limit * 2))
        )
        # Tag portal for dashboard
        for j in jobs:
            j["portal"] = "Workday"
        # Optional LLM fit filter — must run here (async), not inside the sync
        # executor below.
        job_filter = kwargs.get("job_filter")
        if job_filter is not None:
            jobs = [j for j in jobs if await job_filter(j)]
        # Apply each — one browser launch, one thread (SyncBrowser is not
        # thread-safe, so the whole apply loop runs inside a single executor call).
        # Honor HEADLESS env (default headless for cron; set false to watch it).
        headless = os.getenv("HEADLESS", "true").lower() == "true"
        results = await loop.run_in_executor(
            None,
            lambda: _apply_workday_run(jobs, _PROFILE, _resolve_resume_path(), daily_limit, headless)
        )
        return results


def _apply_workday_run(jobs: list, profile: dict, resume_pdf: Optional[str],
                       daily_limit: int, headless: bool = True) -> list:
    """Apply to every job with one shared persistent browser session."""
    from .base import ApplicationResult
    from jarvis_browser import SyncBrowser

    per_company: dict = {}
    results: list = []
    with SyncBrowser(headless=headless) as browser_mgr:
        ctx = browser_mgr.launch_persistent(
            user_data_dir=str(Path.home() / ".jarvis" / "wd_browser"),
            extra_kwargs={"viewport": {"width": 1280, "height": 900}},
        )
        for j in jobs:
            tenant = j.get("_tenant", "?")
            per_company.setdefault(tenant, 0)
            if per_company[tenant] >= daily_limit:
                continue
            success, msg = apply_to_job(j, profile, resume_pdf, context=ctx)
            per_company[tenant] += 1
            results.append(ApplicationResult(
                job=j,
                status="applied" if success else "manual",
                reason=msg,
            ))
    return results
