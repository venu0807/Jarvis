"""
run_pipeline.py — Master pipeline for job automation
Flow:
  1. Auto-apply on all portals using live search (login ONCE, sessions persist)
  2. Tailor resumes for manual/skipped jobs only
  3. Send Email summary (email-only — Telegram removed 2026-06-16)

Scheduled at 8:00 AM IST daily via OpenClaw cron.
Run manually: python run_pipeline.py
"""
import asyncio
import datetime
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

# Configure UTF-8 encoding for standard output and error to avoid UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
from shared_utils import setup_logging

BASE_DIR   = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

log = setup_logging("pipeline", log_dir=BASE_DIR / "output"/ "logs")

TODAY    = datetime.date.today().isoformat()
JOB_FILE = BASE_DIR / "output" / f"jobs_{TODAY}.json"
LOG_FILE = BASE_DIR / "output" / "logs" / f"applications_{TODAY}.json"


# ── Subprocess runner ─────────────────────────────────────────────────────────

def run(cmd: list, label: str) -> bool:
    print(f"\n{'='*56}\n▶ {label}\n{'='*56}")
    result = subprocess.run(cmd, text=True, cwd=str(BASE_DIR))
    ok = result.returncode == 0
    if not ok:
        print(f"❌ {label} failed (exit code {result.returncode})")
    return ok


# ── Step 3: Resume tailoring (manual jobs only) ───────────────────────────────

def tailor_manual_resumes(summary: dict) -> dict:
    """
    For every job in summary['_manual_jobs'] and summary['_skipped_jobs'],
    tailor a resume and attach the PDF path to summary['manual'].
    """
    from resume_tailor import tailor_and_save

    manual_raw   = summary.get("_manual_jobs",   [])
    skipped_raw  = summary.get("_skipped_jobs",  [])
    all_manual   = manual_raw + skipped_raw

    if not all_manual:
        print("  ℹ️  No manual/skipped jobs — skipping resume tailoring")
        return summary

    print(f"\n  📄 Tailoring {len(all_manual)} resumes for manual/skipped jobs...")

    # Build a mapping from (title, company) → PDF path
    pdf_map: dict = {}
    for entry in all_manual:
        job = entry["job"]
        try:
            result = tailor_and_save(job)
            key = (job["title"].lower(), job["company"].lower())
            pdf_map[key] = result["resume_pdf"]
        except Exception as e:
            print(f"     ⚠️  Tailor error [{job['title']}]: {e}")

    # Attach PDF paths to the manual list in summary
    updated_manual = []
    for m in summary.get("manual", []):
        key = (m["title"].lower(), m["company"].lower())
        m["resume_pdf"] = pdf_map.get(key, "")
        updated_manual.append(m)
    summary["manual"] = updated_manual

    print(f"  ✅ {len(pdf_map)} resumes tailored")
    return summary


# ── Step 0: Cleanup ───────────────────────────────────────────────────────────

def cleanup_old_files():
    """Deletes files in the output folder older than 168 hours (7 days).
    Also cleans up old .sessions files (>30 days) to prevent stale cookie bloat.
    """
    import time
    log.info("Cleaning up old output files (>168 hours)")
    output_dir = BASE_DIR / "output"
    if output_dir.exists():
        cutoff_time = time.time() - (168 * 3600)
        deleted_count = 0

        # Files that should NEVER be deleted
        safelist = ["jobs.db", "applied_jobs.json"]

        for root, dirs, files in os.walk(output_dir):
            for file in files:
                if file in safelist:
                    continue
                file_path = Path(root) / file
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        deleted_count += 1
                    except Exception as e:
                        print(f"     ⚠️  Failed to delete {file}: {e}")

        log.info("Deleted %d old output files", deleted_count)

    # ── Clean old .sessions files (>30 days) ──────────────────────────────
    sessions_dir = BASE_DIR / ".sessions"
    if sessions_dir.exists():
        session_cutoff = time.time() - (30 * 24 * 3600)
        purged = 0
        for sess_file in sessions_dir.glob("*.json"):
            if sess_file.stat().st_mtime < session_cutoff:
                try:
                    backup = sess_file.with_suffix(".json.stale")
                    sess_file.rename(backup)  # rename instead of delete — safe to revert
                    purged += 1
                    print(f"     🗑️  Stale session archived: {sess_file.name} → {backup.name}")
                except Exception as e:
                    print(f"     ⚠️  Failed to archive stale session {sess_file.name}: {e}")
        if purged:
            log.info("Archived %d stale session files (>30 days)", purged)


def check_failure_rates(days_back: int = 7, threshold: float = 0.5) -> list:
    """
    Scans the last N days of application logs and flags any portal whose
    manual/error rate exceeds the threshold (e.g. 50% = likely UI change).
    Returns a list of alert dicts.
    """
    import datetime
    alerts = []
    log_dir = BASE_DIR / "output" / "logs"
    if not log_dir.exists():
        return alerts

    today = datetime.date.today()

    for i in range(days_back):
        date_str = (today - datetime.timedelta(days=i)).isoformat()
        log_path = log_dir / f"applications_{date_str}.json"
        if not log_path.exists():
            continue
        try:
            data = json.loads(log_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        # Build per-portal stats from applied + manual lists
        all_entries = []
        for item in data.get("applied", []):
            all_entries.append((item.get("portal", "unknown"), "applied"))
        for item in data.get("manual", []):
            all_entries.append((item.get("portal", "unknown"), "manual"))

        per_portal = {}
        for portal_name, status in all_entries:
            if portal_name not in per_portal:
                per_portal[portal_name] = {"total": 0, "manual": 0}
            per_portal[portal_name]["total"] += 1
            if status == "manual":
                per_portal[portal_name]["manual"] += 1

        for portal_name, stats in per_portal.items():
            if stats["total"] == 0:
                continue
            manual_ratio = stats["manual"] / stats["total"]
            if manual_ratio >= threshold:
                alerts.append({
                    "portal": portal_name,
                    "date": date_str,
                    "total": stats["total"],
                    "manual": stats["manual"],
                    "ratio": round(manual_ratio, 2),
                    "message": f"{portal_name}: {stats['manual']}/{stats['total']} jobs manual ({manual_ratio:.0%}) — possible UI/DOM change",
                })

    return alerts


# ── Main pipeline ─────────────────────────────────────────────────────────────

def main():
    print(f"""
╔══════════════════════════════════════════════════════╗
║   🦞 OpenClaw Full Job Pipeline                     ║
║   Job Automation Pipeline                            ║
║   Date:  {TODAY}                                     ║
║   Steps: Live Search & Apply → Tailor → Notify       ║
╚══════════════════════════════════════════════════════╝
""")

    # Run cleanup first
    cleanup_old_files()

    # ── Pre-flight: check failure rates from recent runs ────────────────────
    log.info("Checking failure rate trends (last 7 days)")
    alerts = check_failure_rates(days_back=7, threshold=0.5)
    if alerts:
        log.warning("Found %d portal(s) with high manual/error rates", len(alerts))
        for alert in alerts:
            log.warning("  %s", alert['message'])
        log.warning("Review these portals' DOM selectors for UI changes.")
    else:
        log.info("No portals exceeding 50%% manual/error rate in last 7 days.")

    # ── Step 1: Auto-apply (login ONCE, sessions persist) ─────────────────────
    log.info("Step 1/3 — Auto-applying (all portals, live search)")
    try:
        # Import and run async main directly (avoids subprocess overhead)
        import auto_applier
        summary = asyncio.run(auto_applier.main())
    except Exception as e:
        print(f"⚠️  Auto-apply had errors: {e}")
        # Load the saved summary
        if LOG_FILE.exists():
            with open(LOG_FILE, encoding="utf-8") as f:
                summary = json.load(f)
        else:
            summary = {"date": TODAY, "applied": [], "manual": [], "portal_counts": {},
                       "totals": {"applied": 0, "manual_total": 0, "errors": 0},
                       "_manual_jobs": [], "_skipped_jobs": []}

    # ── Step 2: Tailor resumes for manual/skipped jobs only ───────────────────
    log.info("Step 2/3 — Tailoring resumes for manual jobs")
    summary = tailor_manual_resumes(summary)

    # Save enriched summary (with PDF paths)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    LOG_FILE.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("Application log updated → %s", LOG_FILE.name)

    # ── Step 3: Send notifications (email-only) ─────────────────────────────────
    log.info("Step 3/3 — Sending email summary")
    from notifier import notify
    notify(summary)

    # ── Final summary ─────────────────────────────────────────────────────────
    t = summary["totals"]
    print(f"""
╔══════════════════════════════════════════════════════╗
║   ✅ Pipeline Complete!                              ║
║   Auto-applied:   {str(t['applied']).ljust(5)} jobs                    ║
║   Apply manually: {str(t['manual_total']).ljust(5)} jobs (email + PDF ready)  ║
║   Errors:         {str(t['errors']).ljust(5)}                          ║
║                                                      ║
║   📧  {os.getenv('GMAIL_ADDRESS', 'No Email')}                               ║
║   📁  output/resumes/                                ║
╚══════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    main()
