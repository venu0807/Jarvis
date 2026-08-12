"""
notifier.py — Send job report via Gmail (email-only)
Reads from the application log (output/logs/applications_YYYY-MM-DD.json)
Reports: auto-applied count by portal, manual jobs with PDF links

Notice: Telegram notifications removed 2026-06-16. Email is the single
notification channel. See ../README.md for the rationale.
"""
import json
import argparse
import datetime
import smtplib
import os
import sys
import requests

# Configure UTF-8 encoding for standard output and error to avoid UnicodeEncodeError on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

GMAIL_ADDRESS  = os.getenv("GMAIL_ADDRESS",  "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
NOTIFY_EMAIL   = os.getenv("NOTIFY_EMAIL", GMAIL_ADDRESS)  # recipient; defaults to sender (self-mail)
N8N_WEBHOOK_URL = os.getenv("N8N_JOB_WEBHOOK_URL", "")


# ── Email builder ─────────────────────────────────────────────────────────────

def build_html(summary: dict) -> str:
    t = summary["totals"]
    today = summary["date"]
    portal_counts = summary.get("portal_counts", {})

    # Per-portal stats rows
    portal_rows = "".join(
        f"<tr><td style='padding:6px 12px'>{p}</td>"
        f"<td style='padding:6px 12px;text-align:center'><b>{c}</b></td></tr>"
        for p, c in portal_counts.items()
    ) or "<tr><td colspan='2' style='padding:6px;color:#888'>No auto-applies today</td></tr>"

    # Auto-applied jobs table
    applied_rows = "".join(
        f"<tr>"
        f"<td style='padding:6px 8px'>{j['title']}</td>"
        f"<td style='padding:6px 8px'>{j['company']}</td>"
        f"<td style='padding:6px 8px'>{j['portal']}</td>"
        f"</tr>"
        for j in summary.get("applied", [])
    ) or "<tr><td colspan='3' style='padding:8px;color:#888;font-style:italic'>None auto-applied today</td></tr>"

    # Manual jobs table
    manual_rows = ""
    for j in summary.get("manual", []):
        apply_link = f"<a href='{j['url']}' style='color:#1a73e8;font-weight:bold'>Apply →</a>" if j.get("url") else "—"
        reason = j.get("reason", "") or ""
        manual_rows += (
            f"<tr>"
            f"<td style='padding:6px 8px'>{j['title']}</td>"
            f"<td style='padding:6px 8px'>{j['company']}</td>"
            f"<td style='padding:6px 8px'>{j['portal']}</td>"
            f"<td style='padding:6px 8px'>{reason}</td>"
            f"<td style='padding:6px 8px'>{apply_link}</td>"
            f"</tr>"
        )
    if not manual_rows:
        manual_rows = "<tr><td colspan='6' style='padding:8px;color:#888;font-style:italic'>None</td></tr>"

    # Re-login required banner — stale session means a portal applied 0 jobs
    relogin = summary.get("needs_relogin", []) or []
    relogin_banner = ""
    if relogin:
        ports = ", ".join(relogin)
        relogin_banner = f"""
<div style='background:#fce4ec;border:1px solid #e57373;border-radius:8px;padding:14px 18px;margin:16px 0;'>
  <b style='color:#c62828'>⚠️ Log back in to: {ports}</b>
  <div style='color:#7c2d2d;font-size:13px;margin-top:4px'>
    These portals' saved sessions expired, so they were skipped (0 applies).
    Open each once in a normal browser and log in, then tomorrow's run will pick them up.
  </div>
</div>"""

    return f"""<html>
<body style='font-family:Arial,sans-serif;max-width:750px;margin:auto;padding:20px;color:#222'>

<h2 style='color:#1a3c6e;border-bottom:2px solid #1a3c6e;padding-bottom:8px'>
  🎯 Job Application Report — {today}
</h2>

<!-- Stats cards -->
<table cellpadding='0' cellspacing='12' style='width:100%;margin:16px 0'>
<tr>
  <td style='padding:18px;background:#e8f5e9;border-radius:10px;text-align:center;width:33%'>
    <div style='font-size:40px;font-weight:bold;color:#1D9E75'>{t['applied']}</div>
    <div style='color:#0F6E56;font-size:12px;margin-top:4px'>✅ Auto-applied</div>
  </td>
  <td style='padding:18px;background:#fff8e1;border-radius:10px;text-align:center;width:33%'>
    <div style='font-size:40px;font-weight:bold;color:#BA7517'>{t['manual_total']}</div>
    <div style='color:#854F0B;font-size:12px;margin-top:4px'>📋 Apply manually</div>
  </td>
  <td style='padding:18px;background:#fce4ec;border-radius:10px;text-align:center;width:33%'>
    <div style='font-size:40px;font-weight:bold;color:#c62828'>{t['errors']}</div>
    <div style='color:#b71c1c;font-size:12px;margin-top:4px'>❌ Errors</div>
  </td>
</tr>
</table>

<!-- Per-portal breakdown -->
<h3 style='color:#1a3c6e;margin-top:24px'>📈 Auto-Applied by Portal</h3>
<table border='1' cellpadding='0' cellspacing='0'
       style='border-collapse:collapse;width:280px;font-size:13px'>
  <tr style='background:#e8eaf6'>
    <th style='padding:8px 12px;text-align:left'>Portal</th>
    <th style='padding:8px 12px;text-align:center'>Applied</th>
  </tr>
  {portal_rows}
</table>

<!-- Auto-applied jobs -->
<h3 style='color:#1D9E75;margin-top:24px'>✅ Auto-Applied — No Action Needed</h3>
<table border='1' cellpadding='0' cellspacing='0'
       style='border-collapse:collapse;width:100%;font-size:13px'>
  <tr style='background:#e8f5e9'>
    <th style='padding:6px 8px'>Role</th>
    <th style='padding:6px 8px'>Company</th>
    <th style='padding:6px 8px'>Portal</th>
  </tr>
  {applied_rows}
</table>

<!-- Manual jobs -->
<h3 style='color:#BA7517;margin-top:24px'>📋 Apply These Manually — One Click Each</h3>
<table border='1' cellpadding='0' cellspacing='0'
       style='border-collapse:collapse;width:100%;font-size:13px'>
  <tr style='background:#fff8e1'>
    <th style='padding:6px 8px'>Role</th>
    <th style='padding:6px 8px'>Company</th>
    <th style='padding:6px 8px'>Portal</th>
    <th style='padding:6px 8px'>Reason</th>
    <th style='padding:6px 8px'>Link</th>
  </tr>
  {manual_rows}
</table>

{relogin_banner}

<p style='color:#aaa;font-size:11px;margin-top:28px'>
  🦞 Job Pipeline — Email-only notifications
</p>
</body></html>"""


def build_plain(summary: dict) -> str:
    t = summary["totals"]
    portal_counts = summary.get("portal_counts", {})

    applied_lines = "\n".join(
        f"  • {j['title']} @ {j['company']} ({j['portal']})"
        for j in summary.get("applied", [])
    ) or "  None"

    manual_lines = "\n".join(
        f"  • {j['title']} @ {j['company']} ({j['portal']})\n"
        f"    Reason: {j.get('reason', '')}\n"
        f"    Apply: {j.get('url','')}"
        for j in summary.get("manual", [])
    ) or "  None"

    portals = "\n".join(f"  {p}: {c}" for p, c in portal_counts.items()) or "  None"

    return f"""Job Application Report — {summary['date']}
Auto-applied:   {t['applied']} | Manual needed: {t['manual_total']} | Errors: {t['errors']}

Per-portal auto-applied:
{portals}

AUTO-APPLIED (no action needed):
{applied_lines}

APPLY MANUALLY (one click each):
{manual_lines}

— Job Pipeline · Email-only notifications
"""


# ── Senders ───────────────────────────────────────────────────────────────────

def send_email(summary: dict):
    if not GMAIL_APP_PASS:
        print("  ⚠️  GMAIL_APP_PASS not set — skipping email")
        return
    if not GMAIL_ADDRESS:
        print("  ⚠️  GMAIL_ADDRESS not set — skipping email")
        return
    try:
        t = summary["totals"]
        subject = (
            f"🎯 {t['applied']} auto-applied | "
            f"{t['manual_total']} manual | "
            f"{summary['date']}"
        )
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = GMAIL_ADDRESS
        msg["To"]      = NOTIFY_EMAIL or GMAIL_ADDRESS
        msg.attach(MIMEText(build_plain(summary), "plain"))
        msg.attach(MIMEText(build_html(summary),  "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
            s.sendmail(GMAIL_ADDRESS, [NOTIFY_EMAIL] if NOTIFY_EMAIL else [GMAIL_ADDRESS], msg.as_string())
        print(f"  📧 Email sent to {NOTIFY_EMAIL or GMAIL_ADDRESS}")
    except Exception as e:
        print(f"  ❌ Email error: {e}")
def send_n8n_webhook(summary: dict):
    if not N8N_WEBHOOK_URL:
        return
    try:
        payload = {
            "date": summary["date"],
            "totals": summary["totals"],
            "portal_counts": summary.get("portal_counts", {}),
            "text_report": build_plain(summary)
        }
        res = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
        if res.status_code in (200, 201):
            print(f"  🚀 N8N Webhook sent to {N8N_WEBHOOK_URL}")
        else:
            print(f"  ❌ N8N Webhook failed with status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"  ❌ N8N Webhook error: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def notify(summary: dict):
    """Send all notifications (Email & N8N Webhooks)."""
    print("\n📬 Sending notifications...")
    send_email(summary)
    send_n8n_webhook(summary)
    print("✅ Notifications sent!")


def main():
    parser = argparse.ArgumentParser(description="Send job application notifications (email only)")
    parser.add_argument("--log-file", required=True, help="Path to applications_YYYY-MM-DD.json")
    args = parser.parse_args()

    with open(args.log_file, encoding="utf-8") as f:
        summary = json.load(f)

    print(f"\n📊 Report date: {summary['date']}")
    print(f"   Auto-applied: {summary['totals']['applied']}")
    print(f"   Manual:       {summary['totals']['manual_total']}")
    notify(summary)


if __name__ == "__main__":
    main()
