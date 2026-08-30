"""
Daily Email Report (morning + evening)
=====================================
Sends a snapshot of job-hunt progress to pvgreddy3@gmail.com twice daily:

  --mode morning  → 9 AM IST: today's plan, recruiter mail overnight, intel, follow-ups due
  --mode evening  → 6 PM IST: today's applied, fresh jobs landed, weekly progress bar, follow-ups tomorrow

Reads JARVIS_HOME / OPENCLAW_HOME from registry. No bot, no live polling.
"""
import argparse
import os
import json
import sqlite3
import subprocess
import smtplib
import sys
from datetime import datetime, date, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import format_datetime
from pathlib import Path

# === Load .env (registry env vars + the JARVIS .env file) ===
JARVIS_HOME = Path(os.environ.get("JARVIS_HOME", Path.home() / ".jarvis"))
OPENCLAW_HOME = Path(os.environ.get("OPENCLAW_HOME", str(JARVIS_HOME)))
JOBAUTO_DIR = OPENCLAW_HOME / "automations" / "job-automation"
ENV_FILE = JOBAUTO_DIR / ".env"
SCRIPTS_DIR = Path(os.environ.get(
    "OPENCLAW_BRAIN_SCRIPTS",
    r"C:\Users\Venu\AppData\Local\hermes\skills\productivity\openclaw-jobhunt-brain\scripts",
))

_DB_PATH = JOBAUTO_DIR / "output" / "jobs.db"

if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip().strip('"').strip("'")


# === Helpers ===
def fmt_lakh(n):
    """123456 -> '1.23L'."""
    if n is None:
        return "-"
    if n >= 100000:
        return f"{n/100000:.2f}L"
    if n >= 1000:
        return f"{n/1000:.1f}K"
    return str(n)


def query_db(sql, params=()):
    if not _DB_PATH.exists():
        return []
    try:
        con = sqlite3.connect(str(_DB_PATH))
        con.row_factory = sqlite3.Row
        cur = con.execute(sql, params)
        rows = [dict(r) for r in cur.fetchall()]
        con.close()
        return rows
    except Exception as e:
        return [{"__error": str(e)}]


def run_script(name, args=None, timeout=60):
    """Run a python script and return stdout (truncated)."""
    try:
        cmd = [sys.executable, str(SCRIPTS_DIR / name)]
        if args:
            cmd.extend(args)
        env = os.environ.copy()
        env["OPENCLAW_HOME"] = str(OPENCLAW_HOME)
        env["JARVIS_HOME"] = str(JARVIS_HOME)
        result = subprocess.run(
            cmd, capture_output=True, text=True, env=env, timeout=timeout, cwd=str(SCRIPTS_DIR)
        )
        return (result.stdout or "").strip()
    except subprocess.TimeoutExpired:
        return f"⏱️ {name} timed out"
    except Exception as e:
        return f"❌ {name}: {e}"


# === Sections ===
def section_pipeline():
    total = query_db("SELECT COUNT(*) as n FROM jobs")[0].get("n", 0) if query_db("SELECT name FROM sqlite_master WHERE type='table' AND name='jobs'") else 0
    seen = 0
    if query_db("SELECT name FROM sqlite_master WHERE type='table' AND name='seen_jobs'"):
        seen = query_db("SELECT COUNT(*) as n FROM seen_jobs")[0].get("n", 0)
    applied = query_db("SELECT COUNT(*) as n FROM jobs WHERE status='applied' OR applied=1")
    applied_n = applied[0].get("n", 0) if applied else 0
    stale = applied_n  # crude: all applied since we don't track freshness
    out = run_script("pipeline_tracker.py", ["--daily"], timeout=30)
    return {
        "total": total,
        "seen": seen,
        "applied": applied_n,
        "raw": out[:1500] if out else "(pipeline_tracker returned nothing)",
    }


def section_recruiter():
    """Check for recruiter emails since last report (last 12h)."""
    # fallback: just count from log
    log_path = Path.home() / "AppData" / "Local" / "hermes" / "jobhunt" / "detections_log.json"
    if not log_path.exists():
        return {"count": 0, "items": []}
    try:
        log = json.loads(log_path.read_text(encoding="utf-8"))
        cutoff = (datetime.now() - timedelta(hours=12)).timestamp()
        items = []
        for entry in log:
            ts = entry.get("ts", 0)
            if ts >= cutoff:
                items.append(entry)
        return {"count": len(items), "items": items[-10:]}
    except Exception as e:
        return {"count": -1, "items": [], "error": str(e)}


def section_company_intel():
    out = run_script("company_intel.py", ["--daily"], timeout=45)
    return {"raw": out[:1500] if out else "(no intel feed)"}


def section_followups():
    out = run_script("followup_engine.py", [], timeout=45)
    return {"raw": out[:1500] if out else "(no followups due)"}


def section_dashboard():
    out = run_script("daily_dashboard.py", [], timeout=45)
    return {"raw": out[:1500] if out else "(dashboard empty)"}


# === Stager for morning vs evening ===
def build_morning():
    pipe = section_pipeline()
    rec = section_recruiter()
    intel = section_company_intel()
    follow = section_followups()
    dash = section_dashboard()

    html_parts = [
        "<html><body style='font-family: -apple-system, sans-serif; max-width: 720px; margin: 0 auto;'>",
        "<h1 style='color: #1F4E79;'>☀️ Morning Job-Hunt Brief</h1>",
        f"<p style='color:#666'>{datetime.now().strftime('%A, %d %B %Y — %H:%M IST')}</p>",
        "<hr>",
        "<h2>📊 Current Pipeline</h2>",
        f"<ul><li><b>Total jobs:</b> {pipe['total']}</li>"
        f"<li><b>Applied:</b> {pipe['applied']}</li>"
        f"<li><b>Seen (queued):</b> {pipe['seen']}</li></ul>",
        "<details><summary>Pipeline details</summary><pre style='background:#f4f4f4; padding:8px;'>"
        + escape(pipe['raw'])[:1500] + "</pre></details>",
        "<h2>📧 Recruiter Activity (last 12h)</h2>",
    ]
    if rec['count'] == 0:
        html_parts.append("<p style='color:#888'>No recruiter replies overnight. Quiet night.</p>")
    else:
        html_parts.append(f"<p><b>{rec['count']} activity</b></p>")
        for it in rec['items']:
            html_parts.append(f"<p style='margin-left:8px'>• {escape(str(it))[:200]}</p>")

    html_parts.append("<h2>🏢 Top Companies Hiring in Your Stack</h2>")
    html_parts.append(f"<pre style='background:#f4f4f4; padding:8px;'>{escape(intel['raw'])[:1500]}</pre>")

    html_parts.append("<h2>🔔 Follow-ups Due Today</h2>")
    html_parts.append(f"<pre style='background:#f4f4f4; padding:8px;'>{escape(follow['raw'])[:1500]}</pre>")

    html_parts.append("<h2>📋 Daily Dashboard Snapshot</h2>")
    html_parts.append(f"<pre style='background:#f4f4f4; padding:8px;'>{escape(dash['raw'])[:1500]}</pre>")

    html_parts.append("</body></html>")
    subject = f"☀️ Morning Brief — {datetime.now().strftime('%d %b %Y')} — {pipe['applied']} applied, {rec['count']} recruiter"
    return subject, "\n".join(html_parts)


def build_evening():
    pipe = section_pipeline()
    rec = section_recruiter()
    dash = section_dashboard()

    # Get today's applied count by querying jobs.db
    today = date.today().isoformat()
    today_applied = query_db(
        "SELECT COUNT(*) as n FROM jobs WHERE DATE(applied_at) = ?", (today,)
    )
    today_n = today_applied[0].get("n", 0) if today_applied else 0

    html_parts = [
        "<html><body style='font-family: -apple-system, sans-serif; max-width: 720px; margin: 0 auto;'>",
        "<h1 style='color: #7B1FA2;'>🌆 Evening Progress Summary</h1>",
        f"<p style='color:#666'>{datetime.now().strftime('%A, %d %B %Y — %H:%M IST')}</p>",
        "<hr>",
        "<h2>📈 Today's Progress</h2>",
        f"<ul><li><b>Applied today:</b> {today_n}</li>"
        f"<li><b>Total applied:</b> {pipe['applied']}</li>"
        f"<li><b>Total in pipeline:</b> {pipe['total']}</li></ul>",
        "<h2>📧 Today's Recruiter Activity</h2>",
    ]
    if rec['count'] == 0:
        html_parts.append("<p style='color:#888'>No recruiter mail today.</p>")
    else:
        html_parts.append(f"<p><b>{rec['count']} activity</b></p>")
        for it in rec['items']:
            html_parts.append(f"<p style='margin-left:8px'>• {escape(str(it))[:200]}</p>")

    html_parts.append("<h2>📋 Full Daily Dashboard</h2>")
    html_parts.append(f"<pre style='background:#f4f4f4; padding:8px;'>{escape(dash['raw'])[:2500]}</pre>")

    html_parts.append("<h2>🎯 Tomorrow's Plan</h2>")
    html_parts.append("<p>Pipeline tracker has already queued tomorrow's top 3 picks. "
                     "Have your cover letter snippets ready.</p>")
    html_parts.append("</body></html>")
    subject = f"🌆 Evening Report — {datetime.now().strftime('%d %b %Y')} — {today_n} applied today"
    return subject, "\n".join(html_parts)


def escape(s):
    return s.replace("&", "&").replace("<", "<").replace(">", ">")


# === Email sender ===
def send_email(subject, html_body):
    addr = os.environ.get("GMAIL_ADDRESS")
    pw = os.environ.get("GMAIL_APP_PASS")
    if not addr or not pw:
        print("❌ GMAIL_ADDRESS / GMAIL_APP_PASS missing in env")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = addr
    msg["To"] = addr
    msg["Date"] = format_datetime(datetime.now(timezone.utc))

    # Plain fallback
    plain = html_body.replace("<br>", "\n").replace("</p>", "\n")
    for tag in ["<html>", "<body>", "</body>", "</html>",
                "<h1>", "</h1>", "<h2>", "</h2>", "<h3>", "</h3>",
                "<ul>", "</ul>", "<ol>", "</ol>", "<li>", "</li>",
                "<details>", "</details>", "<summary>", "</summary>"]:
        plain = plain.replace(tag, "")
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as server:
            server.login(addr, pw)
            server.send_message(msg)
        print(f"✅ Sent: {subject}")
        return True
    except Exception as e:
        print(f"❌ Send failed: {e}")
        return False


# === Main ===
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["morning", "evening"], required=True)
    args = parser.parse_args()

    if args.mode == "morning":
        subject, html = build_morning()
    else:
        subject, html = build_evening()

    # Log what we're about to send
    log_path = JARVIS_HOME / "logs" / "daily_report.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"\n[{datetime.now().isoformat()}] {args.mode.upper()} | {subject} | "
                f"{'OK' if send_email(subject, html) else 'FAIL'}\n")


if __name__ == "__main__":
    main()
