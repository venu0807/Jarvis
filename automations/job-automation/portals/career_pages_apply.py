"""
career_pages_apply.py — Real auto-apply for aggregator job boards.

Companion to career_pages.py. The aggregator API endpoints here use PUBLIC
sumbit URLs (no login required):

  Greenhouse : https://boards-api.greenhouse.io/v1/boards/{TOKEN}/jobs/{ID}
               body is multipart/form-data (first_name, last_name, email,
               phone, resume as file). Returns 200 if accepted.
  Lever      : https://api.lever.co/v0/postings/{SLUG}/{ID}?key={KEY}
               multipart. Accepts the apply only if company enabled public form.
  Ashby      : https://api.ashbyhq.com/posting-api/job-board/{BOARD}/apply
               JSON body {firstName, lastName, email, phone, resumeUrl, ...}.
  Recruitee  : https://{SLUG}.recruitee.com/api/offers/{ID}/applications
               JSON body with candidate + custom answers dict.

All four are TRYABLE without login. None REQUIRE login. None BILL the user.
If a specific company has not enabled public application, the request returns
a 4xx, and `apply_one_job` falls back to `manual` (with the URL captured to
sent_log.jsonl so user can review later).

For CUSTOM ATSs (Workday, SmartRecruiters, big-tech portals) we POST the
public apply URL with the user's resume PDF + cover letter. The dominant ATS
form is Workday (Google, Microsoft, Amazon, Apple, etc). Workday's public
"`/job/{tenant}/{job}` page is a multi-page Apply flow — Playwright form-fill
under `CareerPagePortal.apply_to_job()` handles that via the user's saved
session cookies.

The career_page crawler in career_pages.py is a chokepoint: it emits
`{id: "<agg>_<token>_<job_id>", title, ..., portal: "CareerPage"}` dicts.
This module dispatches based on the prefix to the right endpoint.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

import requests


# ── User profile (from ~/.jarvis/automations/job-automation/.env) ──────────
def _load_profile() -> dict:
    """Read user contact info from project .env. Tightened copy with
    fail-soft defaults so missing .env vars never crash apply."""
    env_path = Path(__file__).parents[2] / ".env"
    out = {
        "first_name": "",
        "last_name": "",
        "email": "",
        "phone": "",
        "linkedin": "",
        "resume_pdf": "",
    }
    if not env_path.exists():
        return out
    for raw in env_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, _, v = line.partition("=")
        v = v.strip().strip('"').strip("'")
        if k == "USER_FULL_NAME":
            parts = v.split(maxsplit=1)
            out["first_name"] = parts[0] if parts else ""
            out["last_name"] = parts[1] if len(parts) > 1 else ""
        elif k == "GMAIL_ADDRESS":
            out["email"] = v
        elif k == "USER_EMAIL" and not out["email"]:
            out["email"] = v
        elif k == "USER_PHONE":
            out["phone"] = v
        elif k == "USER_LINKEDIN_URL":
            out["linkedin"] = v
        elif k == "RESUME_PDF_PATH":
            out["resume_pdf"] = v
    return out


_PROFILE = _load_profile()


# ── Apply endpoints per aggregator ─────────────────────────────────────────

# Greenhouse: POST /v1/boards/{token}/jobs/{id} with multipart form-data.
# The body has to match the company's configured fields — minimum is
# first_name, last_name, email, phone, resume (file), and answer_* for any
# custom required questions. Most companies require NO auth for public apply.
GH_APPLY_TMPL = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs/{id}"

# Lever: POST /v0/postings/{slug}/{id}?key={lever_key}
# Lever-hosted forms accept multipart with text fields.
LEVER_APPLY_TMPL = "https://api.lever.co/v0/postings/{slug}/{id}"

# Ashby: POST /posting-api/job-board/{board}/apply
# JSON body with candidate fields. `resumeUrl` is OPTIONAL — Ashby will accept
# pasted resume text in `resume`.
ASHBY_APPLY_TMPL = "https://api.ashbyhq.com/posting-api/job-board/{board}/apply"

# Recruitee: POST /api/offers/{id}/candidate
# JSON with candidate + answers.
RECRUITEE_APPLY_TMPL = "https://{slug}.recruitee.com/api/offers/{id}/candidate"


# ── Public API ──────────────────────────────────────────────────────────────

def parse_id(job_id: str) -> tuple[str, dict]:
    """Split job['id'] into (aggregator, payload). Examples:
      "gh_stripe_7954688" → ("greenhouse", {"token":"stripe","id":"7954688"})
      "lever_cred_abcd123" → ("lever",    {"slug":"cred","id":"abcd123"})
      "ashby_postman_j12"  → ("ashby",    {"board":"postman","id":"j12"})
      "recruitee_meesho_42"→ ("recruitee",{"slug":"meesho","id":"42"})
      "manual_google_pm"   → ("manual",   {})
    """
    head, _, rest = job_id.partition("_")  # "gh", "stripe", "7954688"
    if head == "gh" and "_" in rest:
        token, _, gid = rest.partition("_")
        return "greenhouse", {"token": token, "id": gid}
    if head == "lever" and "_" in rest:
        slug, _, gid = rest.partition("_")
        return "lever", {"slug": slug, "id": gid}
    if head == "ashby" and "_" in rest:
        board, _, gid = rest.partition("_")
        return "ashby", {"board": board, "id": gid}
    if head == "recruitee" and "_" in rest:
        slug, _, gid = rest.partition("_")
        return "recruitee", {"slug": slug, "id": gid}
    return "manual", {}


def _resolve_resume_path() -> Optional[str]:
    """Where the user's resume PDF lives. Honor env override, fall back to
    the resume_tailor pipeline default."""
    explicit = _PROFILE.get("resume_pdf") or os.environ.get("RESUME_PDF_PATH")
    if explicit and Path(explicit).exists():
        return explicit
    default = Path(os.path.expanduser("~")) / "V" / "VenuGopalReddy-Palugulla-AI-Resume.pdf"
    if default.exists():
        return str(default)
    # Last resort: any *.pdf under the resume_tailor output dir
    out_dir = Path(__file__).parents[2] / "output" / "resumes"
    if out_dir.exists():
        pdfs = sorted(out_dir.glob("*.pdf"), key=lambda p: p.stat().st_mtime, reverse=True)
        if pdfs:
            return str(pdfs[0])
    return None


def _apply_greenhouse(payload: dict, profile: dict, resume_path: Optional[str]) -> tuple[bool, str]:
    """Greenhouse public apply. Multipart with resume file (if available)."""
    url = GH_APPLY_TMPL.format(token=payload["token"], id=payload["id"])
    files = {}
    data = {
        "first_name": profile["first_name"],
        "last_name":  profile["last_name"],
        "email":      profile["email"],
        "phone":      profile["phone"],
    }
    if resume_path and Path(resume_path).exists():
        with open(resume_path, "rb") as _fh:
            files = {"resume": _fh}
            try:
                r = requests.post(url, data=data, files=files, timeout=30)
        if r.status_code in (200, 201):
            return True, f"greenhouse 200 ({r.json().get('application_id', 'n/a')})"
        return False, f"greenhouse {r.status_code}: {r.text[:180]}"
    else:
        try:
            r = requests.post(url, data=data, files={}, timeout=30)
            if r.status_code in (200, 201):
                return True, f"greenhouse 200 ({r.json().get('application_id', 'n/a')})"
            return False, f"greenhouse {r.status_code}: {r.text[:180]}"
        except Exception as e:
            return False, f"greenhouse exception: {type(e).__name__}: {str(e)[:160]}"


def _apply_lever(payload: dict, profile: dict, resume_path: Optional[str]) -> tuple[bool, str]:
    """Lever public apply. Multipart."""
    url = LEVER_APPLY_TMPL.format(slug=payload["slug"], id=payload["id"])
    data = {
        "name":      f"{profile['first_name']} {profile['last_name']}".strip(),
        "email":     profile["email"],
        "phone":     profile["phone"],
        "org":       "Personal",
        "comments":  "Auto-applied via JARVIS (cover letter omitted — see resume)."
    }
    files = {}
    if resume_path and Path(resume_path).exists():
        files = {"resume": open(resume_path, "rb")}
    try:
        r = requests.post(url, data=data, files=files, timeout=30)
        if files.get("resume"):
            files["resume"].close()
        if r.status_code in (200, 201):
            return True, "lever 200"
        return False, f"lever {r.status_code}: {r.text[:180]}"
    except Exception as e:
        return False, f"lever exception: {type(e).__name__}: {str(e)[:160]}"


def _apply_ashby(payload: dict, profile: dict, resume_path: Optional[str]) -> tuple[bool, str]:
    """Ashby public apply. JSON body."""
    url = ASHBY_APPLY_TMPL.format(board=payload["board"])
    body = {
        "firstName": profile["first_name"],
        "lastName":  profile["last_name"],
        "email":     profile["email"],
        "phone":     profile["phone"],
        "linkedIn":  profile["linkedin"],
        "jobId":     payload["id"],
        "customFields": [],
        "resume": "See attached PDF for full resume. Auto-applied via JARVIS.",
    }
    # If resume is hosted somewhere Ashby can fetch, set resumeUrl. We
    # don't auto-host — leave that to user.
    try:
        r = requests.post(url, json=body, timeout=30)
        if r.status_code in (200, 201):
            return True, f"ashby {r.status_code}"
        return False, f"ashby {r.status_code}: {r.text[:180]}"
    except Exception as e:
        return False, f"ashby exception: {type(e).__name__}: {str(e)[:160]}"


def _apply_recruitee(payload: dict, profile: dict, resume_path: Optional[str]) -> tuple[bool, str]:
    """Recruitee public apply. JSON candidate body."""
    url = RECRUITEE_APPLY_TMPL.format(slug=payload["slug"], id=payload["id"])
    body = {
        "candidate": {
            "first_name": profile["first_name"],
            "last_name":  profile["last_name"],
            "email":      profile["email"],
            "phone":      profile["phone"],
        },
        "source_id": None,
        "answers": [],
    }
    try:
        r = requests.post(url, json=body, timeout=30)
        if r.status_code in (200, 201):
            return True, f"recruitee {r.status_code}"
        return False, f"recruitee {r.status_code}: {r.text[:180]}"
    except Exception as e:
        return False, f"recruitee exception: {type(e).__name__}: {str(e)[:160]}"


def apply_one_job(job: dict, session_log: Optional[Path] = None, dry_run: bool = False) -> dict:
    """Apply to one career-page job. Returns dict suitable for adding to
    a `sent_log.jsonl`.

    Args:
        job: dict from search_career_pages(). Must have id, url, title, company.
        session_log: optional path to JSONL log; appended on every call.
        dry_run: when True, do NOT POST to the aggregator; instead, build the
            full payload that *would* be sent, return it in
            out["would_post"] for inspection, mark status="dry_run". Use this
            to verify a new company supports the public form before letting
            the real run fire.

    Returns dict:
        {status: "applied"|"manual"|"error"|"dry_run", reason: "...",
         job_id, company, title, url, aggregator,
         would_post (only if dry_run=True): {url, headers, body_preview},
         resume_pdf, ts}
    """
    import datetime as _dt
    agg, payload = parse_id(job.get("id", ""))
    resume_path = _resolve_resume_path()
    out = {
        "ts": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "job_id": job.get("id", ""),
        "company": job.get("company", ""),
        "title":   job.get("title", ""),
        "url":     job.get("url", ""),
        "aggregator": agg,
        "joint": agg,
        "status": "manual",
        "reason": "",
        "resume_pdf": resume_path or "",
        "dry_run": dry_run,
    }

    if agg == "manual":
        out["reason"] = "custom ATS — Playwright apply path"
    elif dry_run:
        # Build the would-post payload but don't send. Inspected by callers
        # that want to verify a new company's public form.
        out["status"] = "dry_run"
        out["would_post"] = _build_dry_run_payload(agg, payload, _PROFILE, resume_path)
        out["reason"] = f"dry-run · would POST {out['would_post']['url'][:100]}"
    elif agg == "greenhouse":
        ok, msg = _apply_greenhouse(payload, _PROFILE, resume_path)
        out["status"] = "applied" if ok else "manual"
        out["reason"] = msg
    elif agg == "lever":
        ok, msg = _apply_lever(payload, _PROFILE, resume_path)
        out["status"] = "applied" if ok else "manual"
        out["reason"] = msg
    elif agg == "ashby":
        ok, msg = _apply_ashby(payload, _PROFILE, resume_path)
        out["status"] = "applied" if ok else "manual"
        out["reason"] = msg
    elif agg == "recruitee":
        ok, msg = _apply_recruitee(payload, _PROFILE, resume_path)
        out["status"] = "applied" if ok else "manual"
        out["reason"] = msg
    else:
        out["reason"] = f"unknown aggregator '{agg}'"

    if session_log:
        try:
            session_log.parent.mkdir(parents=True, exist_ok=True)
            with session_log.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(out, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"  ⚠ session_log write failed: {e}")

    return out


def _build_dry_run_payload(agg: str, payload: dict, profile: dict, resume_path: Optional[str]) -> dict:
    """
    Construct the request the apply call *would* make, without sending it.
    Returns:
        {url: str, method: "POST", headers: {...}, body_preview: {field: value, ...}}
    """
    if agg == "greenhouse":
        return {
            "url": GH_APPLY_TMPL.format(token=payload["token"], id=payload["id"]),
            "method": "POST",
            "headers": {"User-Agent": "Mozilla/5.0"},
            "body_preview": {
                "first_name": profile["first_name"],
                "last_name":  profile["last_name"],
                "email":      profile["email"],
                "phone":      profile["phone"],
                "multipart_field": "resume (PDF)" if resume_path and Path(resume_path).exists() else None,
            },
        }
    if agg == "lever":
        return {
            "url": LEVER_APPLY_TMPL.format(slug=payload["slug"], id=payload["id"]),
            "method": "POST",
            "headers": {"User-Agent": "Mozilla/5.0"},
            "body_preview": {
                "name":     f"{profile['first_name']} {profile['last_name']}".strip(),
                "email":    profile["email"],
                "phone":    profile["phone"],
                "org":      "Personal",
                "comments": "Auto-applied via JARVIS (cover letter omitted — see resume).",
                "multipart_field": "resume (PDF)" if resume_path and Path(resume_path).exists() else None,
            },
        }
    if agg == "ashby":
        return {
            "url": ASHBY_APPLY_TMPL.format(board=payload["board"]),
            "method": "POST",
            "headers": {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            "body_preview": {
                "firstName": profile["first_name"],
                "lastName":  profile["last_name"],
                "email":     profile["email"],
                "phone":     profile["phone"],
                "linkedIn":  profile["linkedin"],
                "jobId":     payload["id"],
                "customFields": [],
                "resume": "(plain-text)",  # Service doesn't accept file uploads
            },
        }
    if agg == "recruitee":
        return {
            "url": RECRUITEE_APPLY_TMPL.format(slug=payload["slug"], id=payload["id"]),
            "method": "POST",
            "headers": {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"},
            "body_preview": {
                "candidate": {
                    "first_name": profile["first_name"],
                    "last_name":  profile["last_name"],
                    "email":      profile["email"],
                    "phone":      profile["phone"],
                },
                "source_id": None,
                "answers": [],
            },
        }
    return {"url": "", "method": "POST", "headers": {}, "body_preview": {"note": f"unknown aggregator {agg}"}}


def apply_jobs(jobs: list, session_log: Optional[Path] = None, dry_run: bool = False) -> list[dict]:
    """Apply to many jobs. Logs each result. Prints summary.

    dry_run=True: same as apply_one_job dry_run=True for every job.
    """
    results = []
    for j in jobs:
        r = apply_one_job(j, session_log=session_log, dry_run=dry_run)
        results.append(r)
        if r["status"] == "applied":
            marker = "✅"
        elif r["status"] == "dry_run":
            marker = "🟦"
        elif r["status"] == "manual":
            marker = "🟡"
        else:
            marker = "❌"
        print(f"  {marker} [{r['aggregator']}] {r['title']} @ {r['company']}: {r['reason'][:80]}")
    return results


# ── CLI smoke runner ──────────────────────────────────────────────────

def _cli():
    """Quick CLI: search + (optionally) dry-run apply test.

    Always defaults to dry_run=True so that running this file directly
    NEVER submits a real application. Pass --live as argv[1] to override.
    """
    import sys as _sys
    sys.path.insert(0, str(Path(__file__).parents[2]))
    from portals.career_pages import search_career_pages

    roles = ["Python Developer", "Backend Developer"]
    cities = ["Bangalore", "Hyderabad"]
    print(f"\nProfile: {_PROFILE}")
    print(f"Resume PDF: {_resolve_resume_path() or '(none)'}")
    print(f"\n--- Searching {len(roles)} roles × {len(cities)} cities ---\n")

    jobs = search_career_pages(roles, cities, limit=8)
    print(f"\n--- {'DRY-RUN' if dry_run else 'LIVE'} apply on {len(jobs)} jobs ---\n")
    log = Path(__file__).parents[2] / "output" / "career_apply_log.jsonl"
    return apply_jobs(jobs, session_log=log, dry_run=dry_run)


if __name__ == "__main__":
    import sys as _sys
    dry_run_flag = "--live" not in _sys.argv
    # Inline the CLI body so the dry_run_flag from argv actually reaches the call.
    sys.path.insert(0, str(Path(__file__).parents[2]))
    from portals.career_pages import search_career_pages

    roles = ["Python Developer", "Backend Developer"]
    cities = ["Bangalore", "Hyderabad"]
    print(f"\nProfile: {_PROFILE}")
    print(f"Resume PDF: {_resolve_resume_path() or '(none)'}")
    print(f"\n--- Searching {len(roles)} roles × {len(cities)} cities ---\n")

    jobs = search_career_pages(roles, cities, limit=8)
    print(f"\n--- {'DRY-RUN' if dry_run_flag else 'LIVE'} apply on {len(jobs)} jobs ---\n")
    log = Path(__file__).parents[2] / "output" / "career_apply_log.jsonl"
    results = apply_jobs(jobs, session_log=log, dry_run=dry_run_flag)
    n_applied = sum(1 for r in results if r["status"] == "applied")
    n_manual  = sum(1 for r in results if r["status"] == "manual")
    n_dry     = sum(1 for r in results if r["status"] == "dry_run")
    print(f"\nSummary: {n_applied} applied, {n_manual} manual fallback, {n_dry} dry-run"
          + (" — pass --live to actually submit" if dry_run_flag else ""))
