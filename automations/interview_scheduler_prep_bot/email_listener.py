import imaplib
import email
from email.header import decode_header
import os
import random
import sys
import time
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Route via JARVIS chokepoint.
try:
    # Resolve project root relative to this script — always correct.
    JARVIS_HOME = str(Path(__file__).resolve().parent.parent.parent)
    if JARVIS_HOME not in sys.path:
        sys.path.insert(0, JARVIS_HOME)
    from policy import call_llm   # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit(
        f"FATAL: email_listener cannot import ~/.jarvis/policy: {e!r}. "
        "Refusing direct ollama — strict-zero-leak requires policy audit log."
    )

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASS = os.getenv("GMAIL_APP_PASSWORD")

def parse_with_ollama(email_body: str) -> dict:
    """Uses local Ollama to parse Company Name and Interview Date/Time."""
    prompt = f"""
    You are an AI assistant. I will give you the text of an email.
    Extract the following two things:
    1. The Company Name that is scheduling the interview.
    2. The exact Date and Time of the interview (convert to ISO format YYYY-MM-DDTHH:MM:SS if possible).
    
    If it is NOT an interview email, return empty strings.
    Return strictly a JSON object: {{"company_name": "...", "date_time": "..."}}
    Do not output any other text, only the JSON.
    
    Email Text:
    {email_body[:1500]}
    """
    
    try:
        # Route via JARVIS policy. Emails may contain applicant name + DOB +
        # resume snippets; treat as PII-class even though local is already
        # the default model — the audit log is what we need.
        result = call_llm(
            prompt=prompt,
            mode="run",
            force="local",
            pii_acknowledged=True,
            task_label="parse_interview_email",
        )
        payload = result.text or ""
        return json.loads(payload)
    except Exception as e:
        print(f"Ollama parsing failed: {e}")

    return {"company_name": "", "date_time": ""}

def listen_for_interviews():
    if not GMAIL_USER or not GMAIL_PASS:
        print("❌ GMAIL_USER or GMAIL_APP_PASSWORD missing in .env")
        return
        
    print("⏳ Checking for interview emails on IMAP...")
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        # Search for unread emails containing "interview" (broader search)
        # Also include common variations used by recruiters
        search_criteria = '(OR UNSEEN UNSEEN) SUBJECT "interview"'  # Check unseen by default
        status, messages = mail.search(None, search_criteria)
        
        if status == "OK" and messages[0]:
            email_ids = messages[0].split()
            print(f"📬 Found {len(email_ids)} unread interview-related emails.")
            
            for eid in email_ids:
                try:
                    res, msg_data = mail.fetch(eid, '(RFC822)')
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            subject, encoding = decode_header(msg["Subject"])[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding if encoding else "utf-8")
                            
                            print(f"  → Processing Subject: {subject}")
                            
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    if part.get_content_type() == "text/plain":
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            body = payload.decode("utf-8", errors="replace")
                                            break
                            else:
                                payload = msg.get_payload(decode=True)
                                if payload:
                                    body = payload.decode("utf-8", errors="replace")
                            
                            if body:
                                parsed_data = parse_with_ollama(body)
                                print(f"  🤖 Ollama Parsed: {parsed_data}")
                                
                                if parsed_data.get("company_name") and parsed_data.get("date_time"):
                                    print(f"  📅 Sending to Calendar -> {parsed_data['company_name']} at {parsed_data['date_time']}")
                                    from calendar_manager import add_interview_to_calendar
                                    add_interview_to_calendar(parsed_data["company_name"], parsed_data["date_time"])
                except Exception as e:
                    print(f"  ⚠️  Error processing email {eid}: {e}")
                            
        else:
            print("📭 No new interview emails.")
            
        mail.logout()
    except imaplib.IMAP4.error as e:
        print(f"❌ IMAP Connection Error: {e}")
        print("   Check GMAIL_USER / GMAIL_APP_PASSWORD in .env")
        print("   Also ensure IMAP is enabled in Gmail settings")
    except Exception as e:
        print(f"❌ IMAP Error: {e}")

if __name__ == "__main__":
    print("🚀 Starting Email Listener...")
    print("📬 Checking for new interview emails...")
    listen_for_interviews()
    print("✅ Finished checking emails.")
