"""
career_pages.py — Indian tech company careers scraper (cold-discovery)

Fetches open roles from Greenhouse, Lever, and custom-career-page
companies curated for MCA-freshers or early-career Python/Django/AI roles.

Cross-references new jobs against the existing portal DB (jobs.db)
to surface only NET NEW jobs you haven't already seen via Naukri/LinkedIn/etc.

Output:
  - print report to stdout
  - JSON dump to output/career_pages/jobs_YYYYMMDD.json
  - append to output/career_pages/new_jobs.jsonl (deltas only)
  - Email-only summary delivery (Telegram removed 2026-06-16)

Usage:
  python career_pages.py                          # run all known platforms
  python career_pages.py --platforms greenhouse   # only Greenhouse
  python career_pages.py --companies cred,meesho  # explicit subset
  python career_pages.py --city bangalore          # filter to a city

Companies seeded (auto-update this list as you discover others):
  Greenhouse: postman, groww, slice, phonepe, zscaler, linkedin (+ more to add)
  Lever:      cred, meesho
  Custom:     razorpay (Playwright), swiggy, zomato, flipkart, ola, mpl,
              google, microsoft, amazon  (browser-mode jobs.json fetch)
"""
import argparse
import hashlib
import json
import sqlite3
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ── Project setup ──────────────────────────────────────────────────────────────

PROJ_DIR = Path(__file__).resolve().parent          # scripts/
JOB_AUTO_DIR = PROJ_DIR.parent                       # job-automation/
DB_PATH = JOB_AUTO_DIR / "output" / "jobs.db"
OUT_DIR = JOB_AUTO_DIR / "output" / "career_pages"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Read email creds from main .env
ENV_FILE = PROJ_DIR / ".env"  # scripts/.env — may or may not exist
JOB_ENV = JOB_AUTO_DIR / ".env"
if JOB_ENV.exists():
    for line in JOB_ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            import os
            os.environ.setdefault(k.strip(), v.strip().strip('"'))

TIMEOUT_S = 12

CACHE_DIR = OUT_DIR / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
CACHE_EXPIRE_S = 3600 * 12  # 12 hours


def fetch_json_with_cache(url: str, timeout: int = TIMEOUT_S) -> dict:
    """Fetch JSON from URL, caching to disk for 12 hours."""
    cache_key = hashlib.md5(url.encode('utf-8')).hexdigest()
    cache_file = CACHE_DIR / f"{cache_key}.json"

    if cache_file.exists():
        if time.time() - cache_file.stat().st_mtime < CACHE_EXPIRE_S:
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass  # Fallback to network if cache is corrupted

    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (career-pages-bot/1.0)",
        "Accept": "application/json",
    })
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = json.loads(r.read())

    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass

    return data


# ── Company catalog ────────────────────────────────────────────────────────────
# Format: company_name → {"platform": "greenhouse"|"lever"|"custom",
#                          "board": "...", "careers_url": "...",
#                          "hq": "City", "tags": ["..."]}

CATALOG = {
    # Greenhouse
    "postman":       {"platform": "greenhouse", "board": "postman",        "hq": "Bangalore", "tags": ["api","popular"]},
    "groww":         {"platform": "greenhouse", "board": "groww",          "hq": "Bangalore", "tags": ["fintech","popular"]},
    "slice":         {"platform": "greenhouse", "board": "slice",          "hq": "Bangalore", "tags": ["fintech"]},
    "phonepe":       {"platform": "greenhouse", "board": "phonepe",        "hq": "Bangalore", "tags": ["fintech","popular"]},
    "zscaler":       {"platform": "greenhouse", "board": "zscaler",        "hq": "Bangalore", "tags": ["security"]},
    "linkedin":      {"platform": "greenhouse", "board": "linkedin",       "hq": "Bangalore", "tags": ["popular"]},

    # Lever
    "cred":          {"platform": "lever",      "board": "cred",           "hq": "Bangalore", "tags": ["fintech","popular"]},
    "meesho":        {"platform": "lever",      "board": "meesho",         "hq": "Bangalore", "tags": ["ecom"]},

    # Custom (browser) — placeholder list. Add as needed.
    "razorpay":      {"platform": "custom", "careers_url": "https://razorpay.com/jobs/",         "hq": "Bangalore", "tags": ["fintech","popular"]},
    "swiggy":        {"platform": "custom", "careers_url": "https://careers.swiggy.com/",        "hq": "Bangalore", "tags": ["delivery","popular"]},
    "zomato":        {"platform": "custom", "careers_url": "https://www.zomato.com/careers",      "hq": "Gurgaon",   "tags": ["delivery","popular"]},
    "flipkart":      {"platform": "custom", "careers_url": "https://www.flipkartcareers.com/",    "hq": "Bangalore", "tags": ["ecom","popular"]},
    "ola":           {"platform": "custom", "careers_url": "https://www.olacabs.com/careers",     "hq": "Bangalore", "tags": ["mobility"]},
    "google":        {"platform": "custom", "careers_url": "https://careers.google.com/",         "hq": "Bangalore", "tags": ["popular"]},
    "microsoft":     {"platform": "custom", "careers_url": "https://careers.microsoft.com/",      "hq": "Hyderabad", "tags": ["popular"]},
    "amazon":        {"platform": "custom", "careers_url": "https://www.amazon.jobs/en/",          "hq": "Bangalore", "tags": ["popular"]},
    "razorpay-cap":   {"platform": "custom", "careers_url": "https://www.razorpay.com/careers/",   "hq": "Bangalore", "tags": ["fintech"]},
}

# ── Fetchers ─────────────────────────────────────────────────────────────────

def fetch_greenhouse(board: str) -> list:
    """Fetch jobs from Greenhouse public board API.

    Use ?content=true to include full description text so our
    relevance scorer can see python/django/intern keywords beyond
    just the title.
    """
    url = f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"
    try:
        data = fetch_json_with_cache(url)
        jobs = []
        for j in data.get("jobs", []):
            # Greenhouse returns content as HTML with HTML entities (< etc.)
            raw_content = j.get("content") or ""
            if raw_content:
                import html
                import re
                # 1. Decode HTML entities (< → <)
                content = html.unescape(raw_content)
                # 2. Strip tags
                content = re.sub(r"<[^>]+>", " ", content)
                # 3. Collapse whitespace
                content = re.sub(r"\s+", " ", content).strip()
            else:
                content = ""
            jobs.append({
                "id": f"gh_{board}_{j['id']}",
                "title": j.get("title", ""),
                "company": board,
                "location": (j.get("location") or {}).get("name", ""),
                "url": j.get("absolute_url", ""),
                "updated_at": j.get("updated_at", ""),
                "platform": "greenhouse",
                "raw": {"description": content[:1200]},
            })
        return jobs
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []  # board not found — silently skip
        raise


def _extract_lever_description(body) -> str:
    """Lever stores job descriptions in `lists` (array of {text, content} dicts).

    Concatenate all `content` fields, stripped of HTML, into a single string.
    """
    parts = []
    for section in body.get("lists") or []:
        title = section.get("text", "")
        content = section.get("content") or ""
        # Strip tags + collapse whitespace
        import re
        content = re.sub(r"<[^>]+>", " ", content)
        content = re.sub(r"\s+", " ", content).strip()
        if title or content:
            parts.append(f"{title}\n{content}".strip())
    return "\n\n".join(parts)[:1500]


def fetch_lever(board: str) -> list:
    """Fetch jobs from Lever public postings API.

    Uses 2-phase: bulk listing + per-job detail fetch for descriptions,
    because bulk endpoint doesn't include descriptions.
    """
    url = f"https://api.lever.co/v0/postings/{board}?mode=json"
    try:
        data = fetch_json_with_cache(url)
        if not isinstance(data, list):
            return []

        # Phase 2: enrich with descriptions (per-job fetch keeps total
        # time under 30s for boards with <50 jobs)
        enriched = []
        for j in data:
            cats = j.get("categories") or {}
            loc = cats.get("location") or ""
            commit = cats.get("commitment") or ""
            loc_display = f"{loc} ({commit})" if commit else loc
            item = {
                "id": f"lever_{board}_{j.get('id','')}",
                "title": j.get("text", ""),
                "company": board,
                "location": loc_display,
                "url": j.get("hostedUrl") or j.get("applyUrl") or "",
                "updated_at": str(j.get("createdAt", "")),
                "platform": "lever",
                "raw": {"description": ""},
            }
            # Try per-job fetch for description (board=cred has 5 jobs OK,
            # meesho has 47 — about 30s total). Skip if too-many-jobs board.
            if len(data) <= 50:
                try:
                    jid = j.get("id")
                    body = fetch_json_with_cache(
                        f"https://api.lever.co/v0/postings/{board}/{jid}",
                        timeout=8,
                    )
                    item["raw"]["description"] = _extract_lever_description(body)
                except Exception:
                    pass  # bulk-only; keep going
            enriched.append(item)
        return enriched
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return []
        raise

def fetch_custom(company: str, url: str) -> list:
    """Fetch jobs from a custom careers page.

    Returns an empty list for now — custom sites need Playwright/HTML
    parsing per-site. Skeleton included so catalogs can be extended.
    """
    # Could use Playwright for SPA-rendered pages, or HTML-parsing for
    # static sites. Each company may need its own parser.
    return []


# ── DB cross-reference ────────────────────────────────────────────────────────

def init_jobs_db():
    """Create the jobs table mirror for delta-detection if not exists."""
    if not DB_PATH.exists():
        return None
    try:
        conn = sqlite3.connect(str(DB_PATH))
        conn.execute("""
            CREATE TABLE IF NOT EXISTS seen_jobs (
                id TEXT PRIMARY KEY,
                first_seen TEXT NOT NULL
            )
        """)
        conn.commit()
        return conn
    except sqlite3.OperationalError as e:
        print(f"  ⚠ could not open jobs.db: {e}")
        return None


def get_seen_ids(conn) -> set:
    if not conn:
        return set()
    cur = conn.execute("SELECT id FROM seen_jobs")
    return {row[0] for row in cur.fetchall()}


def mark_seen(conn, new_ids: list):
    if not conn or not new_ids:
        return
    now = datetime.now(timezone.utc).isoformat()
    conn.executemany(
        "INSERT OR IGNORE INTO seen_jobs (id, first_seen) VALUES (?, ?)",
        [(jid, now) for jid in new_ids],
    )
    conn.commit()


# ── Runner ───────────────────────────────────────────────────────────────────

GREENHOUSE_KEYWORDS = [
    "python", "django", "flask", "fastapi", "rest api", "graphql",
    "software engineer", "sde", "backend", "back-end", "frontend", "front-end",
    "full stack", "fullstack", "developer",
    "machine learning", "ml engineer", "data scientist", "data engineer",
    "android", "kotlin", "flutter", "java developer", " android ",
    "intern", "internship", "fresher", "graduate trainee", "entry level",
    "ai engineer", "mlops", "computer vision", "deep learning",
]

# Roles that look senior/PM/HR — even if keyword math says yes, we skip them
# IMPORTANT: matched against the TITLE only (descriptions can mention
# management hierarchy without the role itself being senior).
NEGATIVE_TITLES = [
    "head of ", "vp ", "vice president", "head -",
    "principal engineer", "principal ",          # except Senior Principal which stays
    " staff engineer",
    "senior manager", " sr manager",
    "brand associate", "associate director",
    "talent acquisition",  # recruiter role
    "growth associate", "marketing associate", "regional head",
    "deputy manager", "assistant manager",
    "executive assistant", "chief of staff", "consultant",
    "category manager", "cluster head",
    "core engineering manager", "engineering manager",
    " finance ",  # accounting-ish
    " hr ", "human resources",
    " brand ", " sales ", "marketing manager",
    "operations manager", " finance manager",
    " legal ", "controllership",
    "editor and animator",  # creative
    # Note: NOT including ["manager"] alone; many legit early jobs end with
    # "Engineering Manager" which we WANT to surface for context (with
    # other negative matches cutting most non-tech).
]


def relevance_score(job: dict) -> int:
    """Score 0-10 how well a job matches MCA-freshers + Python/AI/Django.

    Strict two-stage gate:
      1. TITLE must contain ≥1 engineering keyword (TITLE_HITS) AND not
         be in NEGATIVE_TITLES (manager/HR/etc).
      2. For intern/fresher titles specifically, ALSO must contain a tech
         role word (to filter 'Content Intern', 'Marketing Intern').
      3. Otherwise, body adds context.
    """
    title = job.get("title", "").lower().strip()
    desc  = job.get("raw", {}).get("description", "").lower() if job.get("raw") else ""

    # 1a. Auto-reject senior/non-tech titles
    for bad in NEGATIVE_TITLES:
        if bad in title:
            return 0

    # 1b. Title must contain at least one engineering role word
    TECH_TITLE_HITS = [
        "engineer", "developer", "sde", "sdet",
        "data scientist", "data analyst", "data engineer",
        "ml ", " ai ", "ai engineer", "mlops",
        "android", "kotlin",
        "python", "django", "flask", "fastapi",
        "frontend", "backend", "full stack", "fullstack", "back-end", "front-end",
        "ios", "mobile", "devops", "sre",
    ]
    if not any(kw in title for kw in TECH_TITLE_HITS):
        return 0

    # 2. Intern/fresher/graduate roles — guard against non-tech intern titles
    is_early_career = any(kw in title for kw in (
        "intern", "internship", "fresher", "graduate trainee",
    ))
    if is_early_career and not any(kw in title for kw in TECH_TITLE_HITS):
        return 0  # "Marketing Intern" etc.

    # 3. Score from description+title
    blob = title + " " + desc
    score = 0
    for kw in GREENHOUSE_KEYWORDS:
        if kw in blob:
            score += 1
    for kw in ("python", "django"):
        if kw in blob:
            score += 2
    # Mild bonus for fresher/intern intent (not 3, just 1)
    if any(kw in title for kw in ("intern", "internship", "fresher", "entry level", "graduate")):
        score += 1
    return min(10, score)


def purge_low_score(jobs, threshold=2):
    """Drop jobs that mention none of our target skills."""
    return [j for j in jobs if relevance_score(j) >= threshold]


def main():
    ap = argparse.ArgumentParser(description="Career-pages job scraper")
    ap.add_argument("--platforms", default="greenhouse,lever,custom",
                    help="Comma-separated: greenhouse,lever,custom (default: all)")
    ap.add_argument("--companies", default=None,
                    help="Comma-separated subset of company names (otherwise all)")
    ap.add_argument("--city", default=None,
                    help="Filter to jobs in this city")
    ap.add_argument("--threshold", type=int, default=2,
                    help="Min relevance score to keep (default 2)")
    ap.add_argument("--all", action="store_true",
                    help="Include jobs with score 0 (skip relevance filter)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Skip DB persistence")
    args = ap.parse_args()

    platforms = [p.strip().lower() for p in args.platforms.split(",")]
    companies = (
        [c.strip().lower() for c in args.companies.split(",")]
        if args.companies else None
    )

    target = {
        name: cfg for name, cfg in CATALOG.items()
        if cfg["platform"] in platforms
        and (not companies or name in companies)
        and (not args.city or cfg.get("hq", "").lower() == args.city.lower())
    }
    print(f"📋 target: {len(target)} companies across {platforms}")
    print(f"   city filter: {args.city or '(none)'}")
    print(f"   score threshold: {'all' if args.all else args.threshold}\n")

    if not target:
        print("  No matching companies. Adjust --platforms / --companies / --city.")
        return 1

    # Connect DB once for dedupe
    conn = None if args.dry_run else init_jobs_db()
    seen_ids = get_seen_ids(conn) if conn else set()

    # Fetch all
    all_jobs = []
    stats = {"greenhouse": 0, "lever": 0, "custom": 0, "errors": []}

    for name, cfg in target.items():
        platform = cfg["platform"]
        try:
            if platform == "greenhouse":
                jobs = fetch_greenhouse(cfg["board"])
                stats["greenhouse"] += len(jobs)
            elif platform == "lever":
                jobs = fetch_lever(cfg["board"])
                stats["lever"] += len(jobs)
            elif platform == "custom":
                jobs = fetch_custom(name, cfg["careers_url"])
                stats["custom"] += len(jobs)
            else:
                jobs = []
            # Annotate with HQ + tags
            for j in jobs:
                j["hq"] = cfg.get("hq", "")
                j["tags"] = cfg.get("tags", [])
            all_jobs.extend(jobs)
            status = "✅" if jobs else "—"
            print(f"  {status} {name:<14} ({platform:<10}) {len(jobs):>3} jobs")
        except Exception as e:
            stats["errors"].append(f"{name}: {type(e).__name__}: {e}")
            print(f"  ❌ {name:<14} {type(e).__name__}: {e}")

    # Filter by score
    if args.all:
        kept = all_jobs
    else:
        kept = purge_low_score(all_jobs, threshold=args.threshold)
        # Diagnostic: how scores distribute?
        scored = [(relevance_score(j), j["title"][:50], j["platform"]) for j in all_jobs]
        scored.sort(reverse=True)
        print(f"\n  Score distribution (top 10):")
        for s, title, plat in scored[:10]:
            print(f"    [{s}] {title}  ({plat})")
        medium = [s for s, _, _ in scored if 1 <= s < args.threshold]
        if medium:
            print(f"  ... {len(medium)} jobs scored 1-{args.threshold-1} (would-be-shown at lower threshold)")

    # Filter by city
    if args.city:
        kept = [j for j in kept if args.city.lower() in j.get("location", "").lower()]
        # (already filtered at company level too; this catches intra-company multi-city roles)

    # Dedupe against seen
    new_jobs = [j for j in kept if j["id"] not in seen_ids]
    repeat_jobs = [j for j in kept if j["id"] in seen_ids]

    print()
    print("=" * 64)
    print(f"📥 Fetched:               {len(all_jobs):>4}")
    print(f"   green house / lever / custom: {stats['greenhouse']} / {stats['lever']} / {stats['custom']}")
    print(f"   (errors: {len(stats['errors'])})")
    print(f"✨ After relevance filter: {len(kept):>4}")
    print(f"🆕 Net new (not seen):     {len(new_jobs):>4}")
    print(f"🔁 Already seen:          {len(repeat_jobs):>4}")
    print("=" * 64)

    if new_jobs:
        print(f"\n📋 Top {min(20, len(new_jobs))} NEW jobs (by relevance):")
        ranked = sorted(new_jobs, key=lambda j: -relevance_score(j))
        for j in ranked[:20]:
            score = relevance_score(j)
            print(f"\n  [{score}] {j['title']}")
            print(f"      @ {j['company']:<14} | {j.get('location','?')}")
            print(f"      {j['url']}")
            if j.get("hq"):
                print(f"      HQ: {j['hq']}  | platform: {j['platform']}")
            tags = ", ".join(j.get("tags", []))
            if tags:
                print(f"      tags: {tags}")

    # Persist
    today = datetime.now().strftime("%Y%m%d")
    snap = OUT_DIR / f"jobs_{today}.json"
    snap.write_text(json.dumps({
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "stats": stats,
        "total_jobs": len(all_jobs),
        "relevant_jobs": len(kept),
        "new_jobs_count": len(new_jobs),
        "results": [j for j in kept],
    }, indent=2, ensure_ascii=False), encoding="utf-8")

    if new_jobs:
        with open(OUT_DIR / "new_jobs.jsonl", "a", encoding="utf-8") as f:
            for j in new_jobs:
                f.write(json.dumps({
                    **j,
                    "first_seen_at": datetime.now(timezone.utc).isoformat(),
                }) + "\n")

    if conn and new_jobs:
        mark_seen(conn, [j["id"] for j in new_jobs])
        print(f"\n  💾 {len(new_jobs)} new IDs recorded in jobs.db seen_jobs table")

    if stats["errors"]:
        print(f"\n⚠️ {len(stats['errors'])} errors:")
        for e in stats["errors"]:
            print(f"  {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
