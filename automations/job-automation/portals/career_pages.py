"""
career_pages.py — Company career-page search across aggregator boards.

Architectural choices:
- Aggregator-first: Greenhouse / Lever / Ashby / Recruitee have PUBLIC JSON
  APIs (no scraping, no login, no rate limit). One HTTP GET = all open jobs at
  a company. Covers ~10,000 companies.
- Custom fallback: ATSs like Workday, SmartRecruiters, and big-tech career
  portals (Google, Microsoft, Apple, Amazon) need bespoke scraping via
  Playwright + custom selectors. See _CUSTOM_SCRAPERS dict.

Public API endpoints (zero auth needed):
- Greenhouse: https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
- Lever:     https://api.lever.co/v0/postings/{slug}?mode=json
- Ashby:     https://api.ashbyhq.com/posting-api/job-board/{boardToken}
- Recruitee: https://{slug}.recruitee.com/api/offers

Usage:
  from career_pages import CareerPagePortal
  portal = CareerPagePortal("stripe", "https://...")
  jobs = portal.search_jobs(["Python Developer"], ["Bangalore"], limit=20)
  # → list of standard {id, title, company, location, url, description, portal} dicts

Falls back to the working `LinkedInPortal.search_and_apply()` flow when called
from run_pipeline.py — but since most aggregator jobs DON'T auto-apply, this
returns "manual" status with the apply link mailed to FALLBACK_EMAIL.
"""

import os
import json
import re
import requests
from pathlib import Path
from typing import List, Dict, Optional


from .base import BasePortal, ApplicationResult, is_experienced_role


COMPANY_CATALOG = Path(__file__).parent.parent / "companies.json"


# Aggregator endpoints — no auth needed; rate limit generous (~1 req/sec)
GREENHOUSE_TMPL  = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs"
LEVER_TMPL       = "https://api.lever.co/v0/postings/{slug}?mode=json"
ASHBY_TMPL       = "https://api.ashbyhq.com/posting-api/job-board/{boardName}"
RECRUITEE_TMPL   = "https://{slug}.recruitee.com/api/offers"

# How long to cache each company's results (saves API calls if you re-run)
CACHE_DIR = Path(__file__).parent.parent / "output" / ".career_cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_TTL_S = 6 * 3600  # 6 hours


# ── Filtering helpers ──────────────────────────────────────────────────────────

# Map our role list to keyword slugs/matches used by aggregators
ROLE_KEYWORDS = {
    "Python Developer":      ["python", "django", "flask"],
    "Backend Developer":     ["backend", "python", "django", "flask"],
    "Django Developer":      ["django", "python"],
    "Full Stack Developer":  ["full stack", "fullstack"],
    "Full Stack Python Developer": ["python", "full stack", "django", "react"],
    "Full Stack AI Engineer":  ["ai", "ml", "python", "full stack"],
    "AI ML Engineer":        ["ai", "machine learning", "ml", "python"],
    "Machine Learning Engineer": ["ml", "machine learning", "python"],
    "AI Engineer":           ["ai", "python", "engineer"],
    "Software Developer Python": ["python", "django", "flask"],
    "Android Developer":     ["android", "kotlin", "mobile"],
    "Java Developer":        ["java", "backend"],
    "Software Engineer":     ["software", "engineer"],
    "SDE":                   ["software", "engineer", "sde"],
}

CITY_KEYWORDS = {
    "Gurugram":       ["gurgaon", "gurugram"],
    "Noida":          ["noida"],
    "Greater Noida":  ["greater noida"],
    "Delhi":          ["delhi", "new delhi"],
    "Hyderabad":      ["hyderabad", "telangana"],
    "Bangalore":      ["bangalore", "bengaluru"],
}


def _matches_role(title: str, target_role: str) -> bool:
    """Loose string match against aggregator job titles."""
    t = title.lower()
    needles = [target_role.lower()]
    if target_role in ROLE_KEYWORDS:
        needles = [k.lower() for k in ROLE_KEYWORDS[target_role]]
    for needle in needles:
        if needle in t:
            return True
    return False


def _matches_city(location: str, target_city: str) -> bool:
    """Check if a job's location string mentions the target city (or nearby)."""
    loc = location.lower() if location else ""
    needles = [target_city.lower()]
    if target_city in CITY_KEYWORDS:
        needles = [k.lower() for k in CITY_KEYWORDS[target_city]]
    return any(n in loc for n in needles)


# ── Aggregator fetchers ────────────────────────────────────────────────────────

def _load_company_catalog() -> dict:
    r"""Load C:\...\companies.json, return {key: {...metadata...}}."""
    if not COMPANY_CATALOG.exists():
        return {}
    try:
        return {k: v for k, v in json.loads(COMPANY_CATALOG.read_text(encoding="utf-8")).items()
                if not k.startswith("_")}
    except Exception:
        return {}


def _http_get(url: str, timeout: int = 20) -> Optional[object]:
    try:
        r = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0 job-hunt-bot"})
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ⚠ HTTP fail: {url[:80]}... ({type(e).__name__}: {str(e)[:120]})")
        return None


def _gh_jobs(token: str, roles: List[str], cities: List[str], limit: int) -> List[dict]:
    """Greenhouse: filter jobs by title + location."""
    data = _http_get(GREENHOUSE_TMPL.format(token=token))
    if not data:
        return []

    jobs = []
    for raw in data.get("jobs", []):
        title = raw.get("title", "")
        loc = (raw.get("location") or {}).get("name", "")
        # Apply role + city filters
        role_match = any(_matches_role(title, r) for r in roles)
        city_match = not cities or any(_matches_city(loc, c) for c in cities)
        if not role_match:
            continue
        if not city_match:
            continue

        # Reject if fresher/senior-mismatch
        if is_experienced_role(title, (raw.get("content") or "")[:500]):
            continue

        jobs.append({
            "id": f"gh_{token}_{raw.get('id', '')}",
            "title": title,
            "company": raw.get("departments", [{}])[0].get("name", "") if raw.get("departments") else "",
            "location": loc,
            "url": raw.get("absolute_url", ""),
            "description": (raw.get("content") or "")[:1000],
            "portal": "CareerPage",
        })
        if len(jobs) >= limit:
            break
    return jobs


def _lever_jobs(slug: str, roles: List[str], cities: List[str], limit: int) -> List[dict]:
    """Lever: same shape, different key names."""
    data = _http_get(LEVER_TMPL.format(slug=slug))
    if not data:
        return []

    jobs = []
    for raw in data:
        title = raw.get("text", "")
        loc = (raw.get("categories") or {}).get("location", "") or \
              (raw.get("workplaceType") or "")
        role_match = any(_matches_role(title, r) for r in roles)
        city_match = not cities or any(_matches_city(loc, c) for c in cities)
        if not (role_match and city_match):
            continue
        if is_experienced_role(title, ""):
            continue

        description = raw.get("descriptionPlain", "") or raw.get("description", "")
        jobs.append({
            "id": f"lever_{slug}_{raw.get('id', '')}",
            "title": title,
            "company": (raw.get("categories") or {}).get("team", "") or "",
            "location": loc,
            "url": raw.get("hostedUrl", "") or raw.get("applyUrl", ""),
            "description": description[:1000],
            "portal": "CareerPage",
        })
        if len(jobs) >= limit:
            break
    return jobs


def _ashby_jobs(board: str, roles: List[str], cities: List[str], limit: int) -> List[dict]:
    """Ashby."""
    data = _http_get(ASHBY_TMPL.format(boardName=board))
    if not data:
        return []

    jobs = []
    for raw in data.get("jobs", []):
        title = raw.get("title", "")
        loc = raw.get("location", "") or raw.get("locationName", "")
        if not any(_matches_role(title, r) for r in roles):
            continue
        if cities and not any(_matches_city(loc, c) for c in cities):
            continue
        if is_experienced_role(title, raw.get("descriptionPlain", "") or ""):
            continue

        jobs.append({
            "id": f"ashby_{board}_{raw.get('id', '')}",
            "title": title,
            "company": raw.get("department", "") or "",
            "location": loc,
            "url": raw.get("jobUrl", "") or raw.get("applyUrl", ""),
            "description": (raw.get("descriptionPlain") or "")[:1000],
            "portal": "CareerPage",
        })
        if len(jobs) >= limit:
            break
    return jobs


def _recruitee_jobs(slug: str, roles: List[str], cities: List[str], limit: int) -> List[dict]:
    """Recruitee (e.g. meesho.recruitee.co/api/offers)."""
    data = _http_get(RECRUITEE_TMPL.format(slug=slug))
    if not data:
        return []

    # Recruitee wraps offers under 'offers' key; field names: title, city, careers_url, description
    offers = data.get("offers", []) if isinstance(data, dict) else data
    jobs = []
    for raw in offers:
        title = raw.get("title", "")
        loc = raw.get("city", "")
        if not any(_matches_role(title, r) for r in roles):
            continue
        if cities and not any(_matches_city(loc, c) for c in cities):
            continue
        if is_experienced_role(title, raw.get("description", "") or ""):
            continue

        jobs.append({
            "id": f"recruitee_{slug}_{raw.get('id', '')}",
            "title": title,
            "company": slug.title(),
            "location": loc,
            "url": raw.get("careers_url") or raw.get("url") or "",
            "description": (raw.get("description") or "")[:1000],
            "portal": "CareerPage",
        })
        if len(jobs) >= limit:
            break
    return jobs


def _custom_jobs(entry: dict, roles: List[str], cities: List[str], limit: int) -> List[dict]:
    """For big-tech custom ATS without a public API. Requires Playwright.

    Currently returns a 'manual' set with the careers_url so the fallback
    emailer forwards it. We DO NOT auto-apply to Google/Microsoft etc — those
    require CAPTCHA and account auth.
    """
    name = entry.get("name", "?")
    careers_url = entry.get("url", "")
    if not careers_url:
        return []

    # Emit a single manual marker per company so it's actionable:
    # "Google has 3 Python roles open — go look yourself"
    return [{
        "id": f"manual_{name.lower().replace(' ', '_')}",
        "title": f"(manual check) {name} careers",
        "company": name,
        "location": "Any",
        "url": careers_url,
        "description": (
            f"Manual application suggested for {name}. "
            f"Visit {careers_url} to find+apply Python/Django/AI roles."
        ),
        "portal": "CareerPage",
        "_manual_only": True,
    }][:limit if limit else 1]


# ── Main entry-point: search across all configured companies ────────────────

def search_career_pages(roles, cities, limit: int = 25, custom_only: bool = False) -> List[dict]:
    """Search companies.json list and return matching jobs across aggregators.

    Args:
        roles: list of role names (e.g. ["Python Developer"])
        cities: list of cities (empty = all locations)
        limit:  max jobs to return across all companies
        custom_only: skip aggregators; only return big-tech "manual check" stubs

    Returns:
        list of dicts with id, title, company, location, url, description, portal.
        Same shape as scraped LinkedIn/internshala dicts so apply_to_job works.
    """
    catalog = _load_company_catalog()
    if not catalog:
        print("  ⚠ companies.json missing or empty — skipping career page search")
        return []

    all_jobs: List[dict] = []
    per_company_limit = max(2, limit // max(1, len(catalog)))

    for key, entry in catalog.items():
        if len(all_jobs) >= limit:
            break

        agg_type = entry.get("type", "")
        if agg_type in ("greenhouse", "lever", "ashby", "recruitee"):
            if custom_only:
                continue

            # Caching — repeat queries within 6h are free
            cache_path = CACHE_DIR / f"{key}.json"
            if cache_path.exists():
                age_s = cache_path.stat().st_mtime - 0  # crude; using mtime only
                if (Path(cache_path).stat().st_mtime + CACHE_TTL_S) >__import__("time").time():
                    cached = json.loads(cache_path.read_text(encoding="utf-8"))
                    print(f"  ↳ {entry.get('name','?'):18s} (cached) → {len(cached)} jobs")
                    all_jobs.extend(cached[:per_company_limit])
                    continue

            print(f"  ↳ {entry.get('name','?'):18s} [{agg_type}] querying...", end=" ")
            try:
                if agg_type == "greenhouse":
                    new = _gh_jobs(entry["token"], roles, cities, per_company_limit)
                elif agg_type == "lever":
                    new = _lever_jobs(_parse_lever_slug(entry["url"]), roles, cities, per_company_limit)
                elif agg_type == "ashby":
                    new = _ashby_jobs(_parse_ashby_slug(entry["url"]), roles, cities, per_company_limit)
                elif agg_type == "recruitee":
                    new = _recruitee_jobs(_parse_recruitee_slug(entry["url"]), roles, cities, per_company_limit)
                else:
                    new = []
            except Exception as e:
                print(f"  ⚠ {agg_type} failure for {key}: {e}")
                new = []

            print(f"{len(new)} jobs")
            try:
                cache_path.write_text(json.dumps(new), encoding="utf-8")
            except Exception:
                pass
            all_jobs.extend(new)

        elif agg_type == "custom":
            # For big-tech custom: return STUB ONLY with "manual application"
            stub = _custom_jobs(entry, roles, cities, per_company_limit)
            if stub:
                print(f"  ↳ {entry.get('name','?'):18s} [custom → manual check]")
                all_jobs.extend(stub)

    return all_jobs[:limit]


def _parse_lever_slug(url: str) -> str:
    """Extract company slug from a Lever URL like
    https://jobs.lever.co/netflix → 'netflix'."""
    m = re.search(r"lever\.co/([^/?]+)", url)
    return m.group(1) if m else ""


def _parse_ashby_slug(url: str) -> str:
    """Extract board name from Ashby URL like
    https://jobs.ashbyhq.com/postman → 'postman'."""
    m = re.search(r"ashbyhq\.com/([^/?]+)", url)
    return m.group(1) if m else ""


def _parse_recruitee_slug(url: str) -> str:
    """Extract the registrant from a Recruitee URL like
    https://meesho.recruitee.co → 'meesho' (subdomain, not full host).
    For deep subdomains like https://cred.club.recruitee.co we instead need
    the company's API_BASE field if present; otherwise we fall back to the
    last 2 labels (host portion) — Recruitee supports multi-label hosts but
    in practice most boards are 1- or 2-deep.
    """
    m = re.match(r"https?://([^/]+)", url)
    if not m:
        return ""
    host = m.group(1)
    if host.endswith(".recruitee.co") or host.endswith(".recruitee.com"):
        # strip the TLD+registrar, then strip ONLY the leftmost label
        # e.g. meesho.recruitee.co       -> meesho
        #      cred.club.recruitee.co     -> cred.club (we keep this and
        #                                     let the URL-formatter below
        #                                     try without dot)
        parts = host.split(".")
        # remove .co or .com from the end
        if parts[-1] in ("co", "com") and parts[-2] == "recruitee":
            sub = ".".join(parts[:-2])
            # take only the LEFT label so we don't form invalid subdomains
            return sub.split(".")[0] if "." in sub else sub
        return host
    return host


# ── Apply (job_status: 'manual' for most career-page roles) ───────────────────

class CareerPagePortal(BasePortal):
    """Adapts search_career_pages results to the portal interface.

    Apply flow (added 2026-06-15):
      1. Run `search_career_pages()` for fresh jobs.
      2. For each aggregator job (Greenhouse/Lever/Ashby/Recruitee), call
         `career_pages_apply.apply_one_job()`. The aggregator's public POST
         endpoint is hit directly with the user's profile + resume PDF.
      3. On 200/201 → `applied`. On any 4xx/5xx → `manual` (link mailed).
      4. Custom ATS jobs (Workday etc) → `manual` for now; Playwright form-fill
         hooks land in a future iteration.

    The result list mirrors `BasePortal.search_and_apply`'s contract so
    auto_applier.py can aggregate just like for naukri/indeed/etc.
    """

    name = "CareerPage"
    base_url = ""
    login_url = ""

    async def login(self, page) -> bool:
        # No login needed — aggregator APIs are public
        return True

    async def search_and_apply(self, page, roles, cities, daily_limit, applied_today, dry_run=False):
        """Pull fresh jobs from companies.json aggregators, then attempt
        real apply on each. Stores results in output/career_apply_log.jsonl.
        Returns list of ApplicationResult.

        dry_run=True: build the request payloads for every would-apply job but
            do NOT POST. Use this to audit a company's public-form schema
            before letting the live run submit.
        """
        # Import here to avoid circular at module load
        from .career_pages_apply import apply_one_job, _PROFILE
        from ..db_logger import save_jobs_to_db  # type: ignore

        log_path = Path(__file__).parent.parent / "output" / "career_apply_log.jsonl"

        # Pull fresh jobs (cached for 6h inside search_career_pages)
        jobs = search_career_pages(roles, cities, limit=daily_limit)

        results = []
        for j in jobs:
            if j.get("id") in applied_today:
                continue
            if j.get("_manual_only"):
                # Custom ATS — needs Playwright form-fill; defer to manual queue
                results.append(ApplicationResult(
                    job=j,
                    status="manual",
                    reason=f"custom ATS — apply via {j.get('url', '')[:60]}",
                ))
                continue

            # Real aggregator apply (or dry-run)
            apply_record = apply_one_job(j, session_log=log_path, dry_run=dry_run)
            # Persist job to DB regardless (so portal_performance can see it)
            try:
                save_jobs_to_db([j], source="career_pages")
            except Exception:
                pass

            # Map apply_record.status into ApplicationResult.status.
            # dry_run → "manual" so portal_performance treats these as not-yet-applied.
            mapped_status = "manual" if apply_record["status"] in ("dry_run",) else apply_record["status"]
            results.append(ApplicationResult(
                job=j,
                status=mapped_status,
                resume_pdf=apply_record.get("resume_pdf", ""),
                reason=f"aggregator={apply_record['aggregator']} · {apply_record['reason'][:120]}",
            ))

            # Tiny delay to be polite to aggregator endpoints
            import asyncio, random
            await asyncio.sleep(random.uniform(0.5, 1.5))

        return results

    def _company_keys(self):
        catalog = _load_company_catalog()
        return list(catalog.keys())


# ── CLI test runner ───────────────────────────────────────────────────────────

def _cli_test():
    """Quick CLI for testing: prints aggregators + jobs found in real-time."""
    print("=== career_pages.py CLI test ===\n")
    print(f"companies.json: {COMPANY_CATALOG}")
    print(f"Exists: {COMPANY_CATALOG.exists()}")
    if not COMPANY_CATALOG.exists():
        return

    catalog = _load_company_catalog()
    by_type: Dict[str, list] = {}
    for k, v in catalog.items():
        by_type.setdefault(v.get("type", "?"), []).append(k)
    for t, ks in by_type.items():
        print(f"  {t:14s} ({len(ks):>2} companies): {', '.join(ks[:5])}{'...' if len(ks)>5 else ''}")

    print("\n-- Live fetch of first 4 aggregator companies --")
    roles = ["Python Developer", "Backend Developer"]
    cities = ["Bangalore", "Hyderabad", "Delhi"]
    print(f"  Filter roles:  {roles}")
    print(f"  Filter cities: {cities}\n")

    jobs = search_career_pages(roles, cities, limit=15)
    print(f"\n  → {len(jobs)} total jobs across all companies")
    for j in jobs[:10]:
        marker = "🟡" if j.get("_manual_only") else "🟢"
        print(f"    {marker} [{j['portal']}] {j['title']} @ {j['company']} ({j['location']})")


if __name__ == "__main__":
    _cli_test()
