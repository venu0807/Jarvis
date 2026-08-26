#!/usr/bin/env python3
"""
email_listener.py — Enhanced 24/7 Real-Time Interview & Assessment Detection Daemon.
Monitors Gmail for recruiter emails, extracts details via Ollama, creates calendar invites,
and generates AI Interview Prep Cheat Sheets.
"""

import imaplib
import email
from email.header import decode_header
import os
import sys
import re
import time
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
JARVIS_HOME = BASE_DIR.parent.parent
ENV_PATH = BASE_DIR / ".env"
PROCESSED_FILE = BASE_DIR / "processed_emails.json"

load_dotenv(ENV_PATH)

if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
if str(JARVIS_HOME) not in sys.path:
    sys.path.insert(0, str(JARVIS_HOME))

from calendar_manager import add_interview_to_calendar
from prep_generator import generate_prep_sheet
from policy import call_llm

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")


def get_processed_ids() -> set:
    if PROCESSED_FILE.exists():
        try:
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except:
            return set()
    return set()


def save_processed_id(eid: str):
    processed = get_processed_ids()
    processed.add(eid)
    try:
        with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
            json.dump(list(processed), f, indent=2)
    except Exception as e:
        print(f"⚠️ Error saving processed ID: {e}")


def extract_email_text(msg) -> tuple[str, str, str, str]:
    """Extract decoded subject, sender, date, and clean body text (handling text/html)."""
    subj = msg.get("Subject", "")
    decoded_subject = ""
    for p, enc in decode_header(subj):
        if isinstance(p, bytes):
            decoded_subject += p.decode(enc or "utf-8", errors="ignore")
        else:
            decoded_subject += str(p)

    sender = msg.get("From", "")
    date_hdr = msg.get("Date", "")

    body = ""
    if msg.is_multipart():
        for bp in msg.walk():
            ctype = bp.get_content_type()
            if ctype in ["text/plain", "text/html"]:
                pl = bp.get_payload(decode=True)
                if pl:
                    raw_text = pl.decode("utf-8", errors="replace")
                    if ctype == "text/html":
                        clean = re.sub(r'<[^>]+>', ' ', raw_text)
                        clean = re.sub(r'\s+', ' ', clean).strip()
                        body += clean + "\n"
                    else:
                        body += raw_text + "\n"
    else:
        pl = msg.get_payload(decode=True)
        if pl:
            raw_text = pl.decode("utf-8", errors="replace")
            clean = re.sub(r'<[^>]+>', ' ', raw_text)
            body = re.sub(r'\s+', ' ', clean).strip()

    return decoded_subject.strip(), sender.strip(), date_hdr.strip(), body.strip()


def parse_interview_with_llm(subject: str, sender: str, body: str) -> dict:
    """Uses local LLM to extract company, role, date/time and confirm if it's an interview/test invitation."""
    prompt = f"""You are an AI recruiter assistant.
Analyze this email and determine if it is an interview invitation, coding assessment/test, screening call, or recruiter discussion.

Subject: {subject}
From: {sender}
Email Body Snippet:
{body[:2000]}

If it IS an interview, assessment, or recruiter meeting, extract:
- "is_interview": true
- "company_name": "Name of the company"
- "job_role": "Role (e.g. Python Developer, Full Stack Intern)"
- "date_time": "Date and Time (e.g. 2026-08-27 15:00 or ISO format, or 'TBD')"
- "meeting_link": "URL to Google Meet / Teams / Zoom / Assessment link if present, else ''"

If it is just a newsletter, generic rejection, job alert, or marketing email, return:
{{"is_interview": false, "company_name": "", "job_role": "", "date_time": "", "meeting_link": ""}}

Output strictly valid JSON with no markdown and no other text:
"""
    try:
        res = call_llm(
            prompt=prompt,
            mode="run",
            force="local",
            pii_acknowledged=True,
            task_label="parse_interview_email"
        )
        text = (res.text or "").strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        data = json.loads(text)
        return data
    except Exception as e:
        print(f"  ⚠️ LLM parsing error: {e}")
        return {"is_interview": False}


def check_and_process_emails():
    if not GMAIL_USER or not GMAIL_PASS:
        print("❌ GMAIL_USER or GMAIL_APP_PASSWORD missing in .env")
        return

    print("📬 Checking for new interview & assessment emails...")
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        processed = get_processed_ids()
        since_date = (datetime.now() - timedelta(days=7)).strftime("%d-%b-%Y")
        
        status, messages = mail.search(None, f'(SINCE "{since_date}")')
        if status != "OK" or not messages[0]:
            print("📭 No emails found in date range.")
            mail.logout()
            return

        eids = messages[0].split()
        for eid_bytes in reversed(eids):
            eid = eid_bytes.decode()
            if eid in processed:
                continue

            try:
                res, msg_data = mail.fetch(eid_bytes, '(RFC822)')
                for part in msg_data:
                    if isinstance(part, tuple):
                        msg = email.message_from_bytes(part[1])
                        subj, sender, date_hdr, body = extract_email_text(msg)

                        combined = f"{subj} {body}".lower()
                        keywords = [
                            "interview", "shortlist", "assessment", "discussion", "coding test",
                            "hiring process", "screening", "technical round", "video call",
                            "google meet", "teams.microsoft", "zoom.us", "hackerrank", "glider",
                            "test link", "invitation for", "online assessment", "uncodemy", "next steps"
                        ]

                        if any(k in combined for k in keywords):
                            print(f"\n🎯 [Email #{eid}] Evaluating: '{subj}' from {sender}")
                            parsed = parse_interview_with_llm(subj, sender, body)
                            
                            if parsed.get("is_interview") and parsed.get("company_name"):
                                comp = parsed["company_name"]
                                dt = parsed.get("date_time", "Upcoming")
                                role = parsed.get("job_role", "Developer")
                                print(f"🎉 INTERVIEW/TEST DETECTED: {comp} ({role}) at {dt}")

                                # 1. Create Calendar Event (.ics)
                                try:
                                    add_interview_to_calendar(comp, dt)
                                except Exception as ce:
                                    print(f"  ⚠️ Calendar error: {ce}")

                                # 2. Generate AI Prep Sheet
                                try:
                                    prep_path = generate_prep_sheet(comp, dt)
                                    print(f"  📄 AI Prep Sheet generated: {prep_path}")
                                except Exception as pe:
                                    print(f"  ⚠️ Prep generation error: {pe}")

                            save_processed_id(eid)
                        else:
                            save_processed_id(eid)
            except Exception as ex:
                print(f"⚠️ Error checking email #{eid}: {ex}")

        mail.logout()
        print("✅ Finished checking emails.")
    except Exception as e:
        print(f"❌ IMAP listener error: {e}")


def main_daemon_loop():
    print("🚀 JARVIS Interview & Prep Listener Daemon Starting...")
    while True:
        try:
            check_and_process_emails()
        except Exception as e:
            print(f"❌ Daemon loop error: {e}")
        
        # Sleep 5 minutes between active IMAP polling checks
        time.sleep(300)


if __name__ == "__main__":
    main_daemon_loop()
