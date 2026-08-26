#!/usr/bin/env python3
"""
followup_bot.py — 7-day auto followup on unanswered job applications.

Logic:
  - Find all jobs with status='applied', applied >= 7 days ago
  - That have NO entry in job_communications
  - That have NOT already had a followup sent (tracked in followups table)
  - Send a polite follow-up email via Gmail SMTP
  - Record in followups table

Run daily via cron: 0 8 * * * python3 followup_bot.py
"""
import os
import sqlite3
import smtplib
import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent
load_dotenv(BASE_DIR / ".env")

DB_PATH       = BASE_DIR / "output" / "jobs.db"
GMAIL_USER    = os.getenv("GMAIL_USER") or os.getenv("GMAIL_ADDRESS")
GMAIL_PASS    = os.getenv("GMAIL_APP_PASSWORD")
USER_NAME     = os.getenv("USER_SHORT_NAME", "Venu Gopal Reddy")
USER_EMAIL    = os.getenv("USER_EMAIL", "pvgreddy3@gmail.com")
USER_LINKEDIN = os.getenv("USER_LINKEDIN_URL", "")
USER_PORTFOLIO= os.getenv("USER_PORTFOLIO_URL", "")
FOLLOWUP_DAYS = int(os.getenv("FOLLOWUP_DAYS", "7"))


FOLLOWUP_TEMPLATE = """\
Dear Hiring Team,

I hope this message finds you well. I am writing to follow up on my application for the {title} position at {company}, which I submitted approximately {days} days ago.

I remain very enthusiastic about the opportunity to contribute to {company} and believe my background in AI/ML and full-stack development would be a strong fit for this role.

I would love the chance to discuss how my skills align with your team's goals. Please let me know if there is any additional information I can provide.

Thank you for your time and consideration.

Best regards,
{name}
{email}
LinkedIn: {linkedin}
Portfolio: {portfolio}
"""


def init_followups_table(conn):
    conn.execute("""
        CREATE TABLE IF NOT EXISTS followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id TEXT NOT NULL,
            company TEXT,
            sent_at TEXT NOT NULL,
            status TEXT DEFAULT 'sent'
        )
    """)
    conn.commit()


def get_followup_candidates(conn) -> list:
    cutoff = (datetime.datetime.now() - datetime.timedelta(days=FOLLOWUP_DAYS)).isoformat()
    rows = conn.execute("""
        SELECT j.id, j.title, j.company, j.url, j.timestamp
        FROM jobs j
        WHERE j.status = 'applied'
          AND j.timestamp <= ?
          AND j.company IS NOT NULL AND j.company != ''
          AND NOT EXISTS (
              SELECT 1 FROM job_communications jc WHERE jc.job_id = j.id
          )
          AND NOT EXISTS (
              SELECT 1 FROM followups f WHERE f.job_id = j.id
          )
        ORDER BY j.timestamp ASC
        LIMIT 10
    """, (cutoff,)).fetchall()
    return [dict(r) for r in rows]


def send_followup_email(job: dict) -> bool:
    if not GMAIL_USER or not GMAIL_PASS:
        print(f"⚠️  GMAIL credentials not set — skipping email for {job['company']}")
        return False

    days_ago = (datetime.datetime.now() - datetime.datetime.fromisoformat(job["timestamp"])).days

    body = FOLLOWUP_TEMPLATE.format(
        title=job["title"],
        company=job["company"],
        days=days_ago,
        name=USER_NAME,
        email=USER_EMAIL,
        linkedin=USER_LINKEDIN,
        portfolio=USER_PORTFOLIO,
    )

    msg = MIMEMultipart()
    msg["From"] = GMAIL_USER
    msg["To"] = GMAIL_USER  # Send to yourself — can't get recruiter email from job listing
    msg["Subject"] = f"Following Up: {job['title']} Application — {job['company']}"
    msg["Reply-To"] = USER_EMAIL
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(GMAIL_USER, GMAIL_PASS)
            smtp.send_message(msg)
        print(f"✅ Follow-up sent for {job['company']} ({job['title']})")
        return True
    except Exception as e:
        print(f"❌ Failed to send follow-up for {job['company']}: {e}")
        return False


def record_followup(conn, job: dict):
    conn.execute("""
        INSERT INTO followups (job_id, company, sent_at, status)
        VALUES (?, ?, ?, 'sent')
    """, (job["id"], job["company"], datetime.datetime.now().isoformat()))
    conn.commit()


def main():
    print(f"[{datetime.datetime.now()}] Starting 7-day follow-up bot...")

    if not DB_PATH.exists():
        print(f"❌ DB not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    init_followups_table(conn)

    candidates = get_followup_candidates(conn)
    print(f"📋 Found {len(candidates)} applications due for follow-up")

    sent = 0
    for job in candidates:
        print(f"  → {job['company']}: {job['title']}")
        if send_followup_email(job):
            record_followup(conn, job)
            sent += 1

            # Telegram notification
            try:
                import sys
                sys.path.insert(0, str(BASE_DIR))
                from telegram_notifier import notify_followup_sent
                notify_followup_sent(job["company"], job.get("url", ""))
            except Exception:
                pass

    conn.close()
    print(f"✅ Done. Sent {sent}/{len(candidates)} follow-up emails.")


if __name__ == "__main__":
    main()
