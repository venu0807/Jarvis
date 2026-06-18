"""
scripts/onboard_card.py — One-time cheatsheet: email-only delivery.
Telegram delivery removed 2026-06-16 (entire script is now email + print only).

Sends a permanent automation cheatsheet that lists every auto-delivered cron,
every script that can be run from the PC, and the troubleshooting quickref.
The original Telegram card has been retired along with the rest of the bot.

Usage:
  python scripts/onboard_card.py --print      # print card to console (default if no --email)
  python scripts/onboard_card.py --email      # email the card as a one-shot
"""
import argparse
import os
import smtplib
import ssl
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

PROJ_DIR = Path(__file__).resolve().parent.parent
JOBAUTO = Path.home() / ".jarvis" / "automations" / "job-automation"

CARD = r"""🧰 *VENU'S AUTOMATION OS — MASTER CHEATSHEET*
_Email-only since 2026-06-16 — Telegram channel retired. Save this in your inbox._

═══════════════════════════════════════════════
🎯 _PIPELINE COMMANDS_ (job automation state)
═══════════════════════════════════════════════
These used to live in Telegram — now in the daily email / on your PC:

portaldata      — Today's #applied / #manual per portal  (output/applications_*.json)
portalstats 7   — Apply% over last 7 days                 (scripts/weekly_compare.py)
validate        — Cookie health for all 10 portals        (validate_sessions.py)
reauth          — How to refresh expired sessions on PC   (scripts/headful_reauth.py)
runpipeline     — Trigger full pipeline NOW               (python run_pipeline.py)
schedule        — Next 5 cron runs + status               (openclaw list)
sessions        — Quick cookie age table                  (validate_sessions.py)

═══════════════════════════════════════════════
📚 _STUDY_ (SM-2 spaced repetition, daily at 8 PM)
═══════════════════════════════════════════════
study           — Today's card queue
review <id> 0-3 — Grade (0=forgot, 1=hard, 2=good, 3=easy)
stats           — Your accuracy + card counts
forgot          — Cards you got wrong this week

═══════════════════════════════════════════════
💼 _INTERVIEW PIPELINE_
═══════════════════════════════════════════════
pipeline        — Funnel applied → viewed → R1 → R2 → offer
pending         — 5+ day silent applications needing follow-up
company         — Top 5 companies to target today
interview       — Pre-interview brief + question bank
selfintro       — Your 60-second pitch

═══════════════════════════════════════════════
⏰ _AUTO-DELIVERED EVERY DAY_ (email + cron)
═══════════════════════════════════════════════
8:00 PM   📚  Daily study questions (email)
9:00 AM   📧  Job-apply pipeline summary   (Gmail — run_pipeline.py)
9:15 AM   🏠  Dashboard summary            (email)
9:30 AM   🏢  Company intel                (email)
9:30 AM   📞  Follow-up check              (email)
Every 5m  🛑  (Telegram command processor — RETIRED 2026-06-16)
Every 30m 📧  Recruiter reply detector     (auto-moves pipeline)

═══════════════════════════════════════════════
🛠 _FROM YOUR PC_ (one-terminal commands)
═══════════════════════════════════════════════
cd D:\Proposals\Jarvis\automations\job-automation

python scripts\headful_reauth.py             # Refresh ALL session cookies (browser opens, you solve CAPTCHA)
python scripts\headful_reauth.py --only indeed,internshala
python scripts\headful_reauth.py --skip cutshort,freshersworld
python validate_sessions.py                   # Read-only cookie health
python scripts\weekly_compare.py             # Pre vs post portal stats
python scripts\onboard_card.py --print       # Re-print this card
python auto_applier.py --portal career_pages # Aggregator auto-apply: Greenhouse/Lever/Ashby/Recruitee
python run_pipeline.py                       # Full pipeline (apply + tailor + email)

═══════════════════════════════════════════════
🚨 _TROUBLESHOOTING CHEATSHEET_
═══════════════════════════════════════════════

? "No /portaldata today"  → Pipeline didn't run; check Task Scheduler cron
? "Portal → 0% apply"     → run validate_sessions.py → headful_reauth.py
? "Pipeline stuck at N"   → Already returns "skipped" (doesn't pollute manual)
? "No email report"       → Check GMAIL_APP_PASS in .env; check logs/

═══════════════════════════════════════════════
🛡 _SAFEGUARD AI_ (Android project, run on PC)
═══════════════════════════════════════════════
python D:/Proposals/SafeguardAI/__check__.py  # Pre-demo health check
"""


def _load_gmail_creds():
    """Read GMAIL_ADDRESS + GMAIL_APP_PASS from ~/.jarvis/automations/job-automation/.env."""
    sender, app_pass = "", ""
    env_file = JOBAUTO / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("GMAIL_ADDRESS="):
                sender = line.split("=", 1)[1].strip().strip('"').strip("'")
            elif line.startswith("GMAIL_APP_PASS="):
                app_pass = line.split("=", 1)[1].strip().strip('"').strip("'")
    return sender, app_pass


def send_email(card_text: str) -> bool:
    """Send the cheatsheet as email via Gmail."""
    sender, app_pass = _load_gmail_creds()
    if not sender or not app_pass:
        print("  ❌ GMAIL_ADDRESS or GMAIL_APP_PASS not in .env")
        return False

    # Convert markdown-ish to readable HTML
    html_body = (
        "<pre style='font-family: -apple-system,Segoe UI,sans-serif; "
        "white-space:pre-wrap; font-size:13px;'>"
        + card_text.replace("&", "&").replace("<", "<").replace(">", ">")
        + "</pre>"
    )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = "🧰 Venu's Automation OS — Master Cheatsheet"
    msg["From"]    = sender
    msg["To"]      = sender  # self-mail
    msg.attach(MIMEText(card_text, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
            s.login(sender, app_pass)
            s.send_message(msg)
        print(f"  ✅ emailed to {sender}")
        return True
    except Exception as e:
        print(f"  ❌ email failed: {e}")
        return False


def main():
    ap = argparse.ArgumentParser(description="One-time automation cheatsheet (email-only).")
    ap.add_argument("--email", action="store_true", help="Email the cheatsheet")
    ap.add_argument("--print", action="store_true", help="Print to console only")
    args = ap.parse_args()

    if args.print or not args.email:
        print(CARD)
        if not args.email:
            print("\n(Add --email to also deliver this card to your inbox.)")
        return

    print(f"Emailing cheatsheet...")
    send_email(CARD)


if __name__ == "__main__":
    main()
