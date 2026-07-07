"""
imap_scanner.py — Zero-Leakage Email Monitor
Securely connects to Gmail, scans for unread recruiter emails, and summarizes them via local Ollama.
"""

import os
import sys
import email
from email.header import decode_header
from email.message import EmailMessage
import imaplib
import time
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent))

from dotenv import load_dotenv

# Import the existing policy layer to use local Ollama
try:
    from policy import call_llm
except ImportError:
    call_llm = None

from alert_router import send_alert

# Load env vars
dotenv_path = BASE_DIR.parent / "job-automation" / ".env"
load_dotenv(dotenv_path)

GMAIL_ADDRESS = os.getenv("GMAIL_ADDRESS", "")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")

# Keywords to flag recruiter emails
KEYWORDS = ["interview", "application", "resume", "offer", "recruiter", "shortlist", "assessment", "hire"]

def clean_text(text):
    return text.replace("\r", "").replace("\n", " ").strip()

PROCESSED_EMAILS_FILE = BASE_DIR / "processed_emails.json"

def load_processed_emails():
    if PROCESSED_EMAILS_FILE.exists():
        with open(PROCESSED_EMAILS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_processed_emails(processed_set):
    with open(PROCESSED_EMAILS_FILE, "w") as f:
        json.dump(list(processed_set), f)

def decode_mime_words(s):
    if not s:
        return ""
    decoded = decode_header(s)
    res = ""
    for b, enc in decoded:
        if isinstance(b, bytes):
            res += b.decode(enc or "utf-8", errors="replace")
        else:
            res += b
    return res

def analyze_email_with_llm(subject, body):
    """Uses local Ollama to summarize and assign urgency to the email."""
    if not call_llm:
        return {"summary": "Local LLM policy module missing.", "urgency": "Medium"}
    
    prompt = f"""
    You are an AI assistant processing job-related emails locally for privacy.
    Analyze this email and provide a JSON response with three keys:
    "summary": A 1-2 sentence summary of the email.
    "urgency": "High", "Medium", or "Low" (High for interviews/offers/assessments, Medium for rejections/updates, Low for generic marketing).
    "suggested_reply": A professional, courteous reply draft from the applicant (Venu Gopal Reddy). If it's a rejection, a polite thank you. If it's an interview request, express availability. If marketing, leave it blank.
    
    Subject: {subject}
    Body snippet: {body[:1500]}
    """
    
    # Using call_llm wrapper from policy.py
    try:
        response_text = call_llm("phi4-mini:latest", prompt)
        
        # Super simple JSON extraction
        import json
        import re
        
        # Try to find JSON block
        json_match = re.search(r'```json(.*?)```', response_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(1).strip())
        else:
            try:
                data = json.loads(response_text)
            except:
                data = {"summary": response_text.strip()[:200] + "...", "urgency": "Medium", "suggested_reply": ""}
                
        return data
    except Exception as e:
        print(f"LLM Error: {e}")
        return {"summary": "Failed to analyze with LLM.", "urgency": "Low", "suggested_reply": ""}

def create_gmail_draft(mail_conn, original_msg, suggested_reply):
    """Creates a draft reply in the Gmail Drafts folder."""
    if not suggested_reply:
        return
        
    try:
        reply_msg = EmailMessage()
        
        orig_subject = decode_mime_words(original_msg.get("Subject", ""))
        if not orig_subject.lower().startswith("re:"):
            reply_msg["Subject"] = "Re: " + orig_subject
        else:
            reply_msg["Subject"] = orig_subject
            
        reply_msg["From"] = GMAIL_ADDRESS
        reply_msg["To"] = original_msg.get("Reply-To", original_msg.get("From"))
        
        if original_msg.get("Message-ID"):
            reply_msg["In-Reply-To"] = original_msg.get("Message-ID")
            reply_msg["References"] = original_msg.get("References", "") + " " + original_msg.get("Message-ID")
            
        reply_msg.set_content(suggested_reply)
        
        # Append to Drafts
        # Note: Depending on the locale, the drafts folder might be '[Gmail]/Drafts' or just 'Drafts'
        mail_conn.append('"[Gmail]/Drafts"', '\\Draft', imaplib.Time2Internaldate(time.time()), reply_msg.as_bytes())
        print("📝 Draft reply saved to Gmail Drafts folder.")
    except Exception as e:
        print(f"⚠️ Failed to create draft: {e}")


def check_inbox():
    if not GMAIL_ADDRESS or not GMAIL_APP_PASS:
        print("⚠️ Email credentials not configured.")
        return

    print("📧 Connecting to Gmail securely...")
    processed_emails = load_processed_emails()
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_ADDRESS, GMAIL_APP_PASS)
        mail.select("inbox")

        # Search for UNSEEN emails
        status, messages = mail.search(None, "UNSEEN")
        
        if status != "OK":
            print("No new messages found.")
            return
            
        email_ids = messages[0].split()
        print(f"📬 Found {len(email_ids)} unread emails.")

        for e_id in email_ids:
            status, msg_data = mail.fetch(e_id, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    msg_id = msg.get("Message-ID", "").strip()
                    
                    if msg_id and msg_id in processed_emails:
                        continue
                        
                    subject = decode_mime_words(msg.get("Subject"))
                    sender = decode_mime_words(msg.get("From"))
                    
                    # Quick Keyword Filter
                    is_relevant = any(k in subject.lower() for k in KEYWORDS)
                    
                    if not is_relevant:
                        if msg_id:
                            processed_emails.add(msg_id)
                        continue
                        
                    print(f"\n🔍 Relevant Email Detected: {subject} from {sender}")
                    
                    # Extract body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            content_type = part.get_content_type()
                            if content_type == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode()
                                    break
                                except:
                                    pass
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode()
                        except:
                            pass
                            
                    # Analyze locally
                    print("🧠 Analyzing via local LLM...")
                    analysis = analyze_email_with_llm(subject, body)
                    
                    # Create Draft
                    if analysis.get("suggested_reply"):
                        create_gmail_draft(mail, msg, analysis["suggested_reply"])
                    
                    # Alert
                    send_alert(
                        source="Gmail",
                        subject=subject,
                        summary=analysis.get("summary", "No summary available."),
                        urgency=analysis.get("urgency", "Medium"),
                        link="https://mail.google.com/"
                    )
                    
                    # We leave it unread so the user sees it in their inbox!
                    # Mark it as processed in our local database so we don't alert again.
                    if msg_id:
                        processed_emails.add(msg_id)
                        save_processed_emails(processed_emails)

        mail.close()
        mail.logout()
        print("✅ Email scan complete.")
        
    except Exception as e:
        print(f"❌ IMAP Error: {e}")

if __name__ == "__main__":
    check_inbox()
