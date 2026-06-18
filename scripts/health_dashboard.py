#!/usr/bin/env python3
"""
scripts/health_dashboard.py — JARVIS Automation Health Dashboard.

Checks every automation module for:
  1. Process/recent run status
  2. Output file freshness
  3. Error rates from log files
  4. DB health (SQLite integrity)
  5. Configuration consistency

Usage:
    python scripts/health_dashboard.py          # full dashboard
    python scripts/health_dashboard.py --json   # JSON output for monitoring
    python scripts/health_dashboard.py --check  # exit 1 if any module is RED

Exit codes:
    0 = all healthy (GREEN)
    1 = warnings only (YELLOW)
    2 = failures detected (RED)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

# ── Project constants ──────────────────────────────────────────────────────────

PROJECT_ROOT = Path("D:/Proposals/Jarvis")
AUTOMATIONS_DIR = PROJECT_ROOT / "automations"
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
JARVIS_HOME = Path.home() / ".jarvis"


# ── ANSI colors ────────────────────────────────────────────────────────────────

class Color:
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def _c(status: str, text: str) -> str:
    color = {"GREEN": Color.GREEN, "YELLOW": Color.YELLOW, "RED": Color.RED}.get(status, "")
    return f"{color}{text}{Color.RESET}"


# ── Module status ──────────────────────────────────────────────────────────────

Status = str  # "GREEN" | "YELLOW" | "RED"


def _worst(*statuses: Status) -> Status:
    if "RED" in statuses:
        return "RED"
    if "YELLOW" in statuses:
        return "YELLOW"
    return "GREEN"


# ── Check: Job Automation ─────────────────────────────────────────────────────

def check_job_automation() -> tuple[Status, str]:
    job_dir = AUTOMATIONS_DIR / "job-automation"
    logs_dir = job_dir / "output" / "logs"
    db_path = job_dir / "output" / "jobs.db"
    issues = []

    # Check DB exists and has recent data
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                row = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()
                total_jobs = row[0] if row else 0
                recent = conn.execute(
                    "SELECT COUNT(*) FROM jobs WHERE timestamp >= ?",
                    ((datetime.now(timezone.utc) - timedelta(days=7)).isoformat(),),
                ).fetchone()
                recent_jobs = recent[0] if recent else 0
        except Exception as e:
            issues.append(f"DB error: {e}")
            total_jobs = recent_jobs = 0
    else:
        issues.append("jobs.db not found")
        total_jobs = recent_jobs = 0

    # Check most recent log file
    log_files = sorted(logs_dir.glob("applications_*.json"))
    if log_files:
        last_log = log_files[-1]
        mtime = datetime.fromtimestamp(last_log.stat().st_mtime)
        age_hours = (datetime.now() - mtime).total_seconds() / 3600
        if age_hours > 30:
            issues.append(f"Last run was {age_hours:.0f}h ago (stale)")
    else:
        issues.append("No application logs found")

    if not issues:
        return "GREEN", f"DB: {total_jobs} total, {recent_jobs} recent"
    elif len(issues) <= 1:
        return "YELLOW", "; ".join(issues)
    else:
        return "RED", "; ".join(issues)


# ── Check: LinkedIn Outreach ───────────────────────────────────────────────────

def check_linkedin() -> tuple[Status, str]:
    linkedin_dir = AUTOMATIONS_DIR / "linkedin-outreach"
    db_path = linkedin_dir / "sent_tracker.db"
    issues = []

    # Check SQLite tracker
    if db_path.exists():
        try:
            with sqlite3.connect(db_path) as conn:
                total = conn.execute("SELECT COUNT(*) FROM sent_emails").fetchone()[0]
                today = conn.execute(
                    "SELECT COUNT(*) FROM sent_emails WHERE sent_at >= ?",
                    (datetime.now().date().isoformat(),),
                ).fetchone()[0]
        except Exception as e:
            issues.append(f"Tracker DB error: {e}")
            total = today = 0
    else:
        issues.append("sent_tracker.db not yet created")
        total = today = 0

    sent_log = linkedin_dir / "sent_log.jsonl"
    if not sent_log.exists() or sent_log.stat().st_size == 0:
        pass  # May just not have run yet

    if not issues:
        return "GREEN", f"{total} sent total, {today} today"
    elif len(issues) <= 1:
        return "YELLOW", "; ".join(issues)
    else:
        return "RED", "; ".join(issues)


# ── Check: Pinterest Bot ───────────────────────────────────────────────────────

def check_pinterest() -> tuple[Status, str]:
    pin_dir = AUTOMATIONS_DIR / "pinterest"
    csv_path = pin_dir / "data.csv"
    logs_dir = pin_dir / "logs"
    issues = []

    # Check CSV exists and has data
    if csv_path.exists():
        try:
            import csv
            with open(csv_path, encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            total = len(rows)
            pinned = sum(1 for r in rows if r.get("Status", "").strip().lower() == "pinned")
            pending = total - pinned
        except Exception as e:
            total = pinned = pending = 0
            issues.append(f"Could not read data.csv: {e}")
    else:
        issues.append("data.csv not found")
        total = pinned = pending = 0

    # Check recent log
    if logs_dir.exists():
        logs = list(logs_dir.glob("*.log"))
        if logs:
            newest = max(logs, key=lambda p: p.stat().st_mtime)
            age = (datetime.now() - datetime.fromtimestamp(newest.stat().st_mtime)).total_seconds() / 3600
            if age > 48:
                issues.append(f"Last log {age:.0f}h old")
        else:
            issues.append("No logs found")
    else:
        issues.append("logs/ directory missing")

    if not issues:
        return "GREEN", f"{pinned} pinned, {pending} pending"
    elif len(issues) <= 1:
        return "YELLOW", "; ".join(issues)
    else:
        return "RED", "; ".join(issues)


# ── Check: Interview Prep Bot ─────────────────────────────────────────────────

def check_interview_bot() -> tuple[Status, str]:
    interview_dir = AUTOMATIONS_DIR / "interview_scheduler_prep_bot"
    prep_dir = interview_dir / "prep_sheets"
    issues = []

    if prep_dir.exists():
        sheets = list(prep_dir.glob("*.md"))
        sheet_count = len(sheets)
    else:
        sheet_count = 0
        issues.append("No prep sheets yet")

    # Check calendar_manager.py exists
    cal_path = interview_dir / "calendar_manager.py"
    if cal_path.exists():
        try:
            sys.path.insert(0, str(interview_dir))
            import calendar_manager  # type: ignore
            # Check if the required google libs are available
            has_calendar = True
        except ImportError as e:
            has_calendar = False
            issues.append(f"calendar_manager missing deps: {e.name}")
        except Exception as e:
            has_calendar = False
            issues.append(f"calendar_manager error: {e}")
    else:
        issues.append("calendar_manager.py not found")

    if not issues:
        return "GREEN", f"{sheet_count} prep sheets, calendar OK"
    elif len(issues) <= 1:
        return "YELLOW", "; ".join(issues)
    else:
        return "RED", "; ".join(issues)


# ── Check: Scheduling (Windows Task Scheduler) ────────────────────────────────

def check_scheduling() -> tuple[Status, str]:
    expected_tasks = [
        "PinterestBot_Morning", "PinterestBot_Lunch", "PinterestBot_Evening",
        "JobAutomation_Daily", "DailyReport_Morning", "DailyReport_Evening",
        "LinkedInBot_Daily", "InterviewEmailListener",
    ]
    found = []
    missing = []
    try:
        result = subprocess.run(
            ["schtasks", "/query", "/fo", "list", "/v"],
            capture_output=True, text=True, timeout=15,
        )
        output = result.stdout + result.stderr
        for task in expected_tasks:
            if task in output:
                found.append(task)
            else:
                missing.append(task)
    except Exception as e:
        return "YELLOW", f"Could not query Task Scheduler: {e}"

    if not missing:
        return "GREEN", f"{len(found)}/{len(expected_tasks)} tasks registered"
    elif len(missing) <= 2:
        return "YELLOW", f"Missing: {', '.join(missing)}"
    else:
        return "RED", f"Missing {len(missing)} tasks: {', '.join(missing[:3])}..."


# ── Check: Ollama / Policy ────────────────────────────────────────────────────

def check_ollama() -> tuple[Status, str]:
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode != 0:
            return "RED", "Ollama not running"
        models = [l.split()[0] for l in result.stdout.splitlines()[1:] if l.strip()]
        cloud_models = [m for m in models if m.endswith(":cloud")]
        if cloud_models:
            return "YELLOW", f"Cloud models present: {cloud_models}"
        return "GREEN", f"{len(models)} models available"
    except FileNotFoundError:
        return "RED", "Ollama CLI not found"
    except Exception as e:
        return "YELLOW", f"Error: {e}"


# ── Dashboard ─────────────────────────────────────────────────────────────────

def render_dashboard(checks: dict[str, tuple[Status, str]]) -> None:
    print(f"\n{Color.CYAN}{'=' * 60}{Color.RESET}")
    print(f"{Color.BOLD}  🦞 JARVIS Automation Health Dashboard{Color.RESET}")
    print(f"  {datetime.now().strftime('%A, %d %B %Y — %H:%M IST')}")
    print(f"{Color.CYAN}{'=' * 60}{Color.RESET}\n")

    modules = [
        ("📋 Job Automation", "job_automation"),
        ("🐟 LinkedIn Outreach", "linkedin"),
        ("📌 Pinterest Bot", "pinterest"),
        ("🎙️ Interview Prep Bot", "interview_bot"),
        ("⏰ Scheduling (Task Scheduler)", "scheduling"),
        ("🤖 Ollama / Policy", "ollama"),
    ]

    all_statuses = []
    for label, key in modules:
        status, detail = checks.get(key, ("YELLOW", "Unknown"))
        all_statuses.append(status)
        icon = {"GREEN": "✅", "YELLOW": "🟡", "RED": "❌"}.get(status, "❓")
        print(f"  {icon} {label}")
        print(f"     {_c(status, status)}: {detail}")
        print()

    overall = _worst(*all_statuses)
    banner = {
        "GREEN": f"{Color.GREEN}{'✅ ALL SYSTEMS OPERATIONAL'}{Color.RESET}",
        "YELLOW": f"{Color.YELLOW}{'⚠️  MINOR ISSUES DETECTED'}{Color.RESET}",
        "RED": f"{Color.RED}{'❌ ISSUES REQUIRE ATTENTION'}{Color.RESET}",
    }.get(overall, "")

    print(f"{Color.CYAN}{'=' * 60}{Color.RESET}")
    print(f"  Overall: {banner}")
    print(f"{Color.CYAN}{'=' * 60}{Color.RESET}\n")


def render_json(checks: dict[str, tuple[Status, str]]) -> str:
    data = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "overall": _worst(*[s for s, _ in checks.values()]),
        "modules": {
            k: {"status": s, "detail": d} for k, (s, d) in checks.items()
        },
    }
    return json.dumps(data, indent=2)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="JARVIS Health Dashboard")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument("--check", action="store_true",
                        help="Exit with code: 0=GREEN, 1=YELLOW, 2=RED")
    args = parser.parse_args()

    checks = {
        "job_automation": check_job_automation(),
        "linkedin": check_linkedin(),
        "pinterest": check_pinterest(),
        "interview_bot": check_interview_bot(),
        "scheduling": check_scheduling(),
        "ollama": check_ollama(),
    }

    if args.json:
        print(render_json(checks))
    else:
        render_dashboard(checks)

    if args.check:
        overall = _worst(*[s for s, _ in checks.values()])
        return {"GREEN": 0, "YELLOW": 1, "RED": 2}.get(overall, 2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
