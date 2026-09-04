import imaplib
import email
from email.header import decode_header
import sqlite3
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
import re
try:
    from telegram_notifier import notify_interview, notify_rejection
    _TG = True
except ImportError:
    _TG = False

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '.env'))

GMAIL_USER = os.getenv('GMAIL_USER')
GMAIL_PASS = os.getenv('GMAIL_APP_PASSWORD')
DB_PATH = os.path.join(os.path.dirname(__file__), 'output', 'jobs.db')

def get_companies():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        companies = conn.execute("SELECT id, company FROM jobs WHERE status != 'rejected'").fetchall()
        conn.close()
        return companies
    except Exception as e:
        print(f"Error fetching companies: {e}")
        return []

def extract_status(subject, body):
    subject = subject.lower()
    body = body.lower()
    
    rejection_keywords = ["unfortunately", "not moving forward", "other candidates", "regret to inform", "not selected"]
    interview_keywords = ["interview", "schedule a call", "next steps", "availability", "time to chat", "google meet", "zoom"]
    action_keywords = ["complete this form", "assessment", "questionnaire", "coding challenge"]

    # Check for rejections first
    if any(k in subject for k in ["update on your application", "status of your application"]) and any(k in body for k in rejection_keywords):
        return "rejected"
    if any(k in body for k in rejection_keywords):
        return "rejected"
    
    # Check for interviews
    if any(k in subject or k in body for k in interview_keywords):
        return "interview"
        
    if any(k in body for k in action_keywords):
        return "action_required"
        
    return "update_received"

def process_emails():
    if not GMAIL_USER or not GMAIL_PASS:
        print("Missing GMAIL_USER or GMAIL_APP_PASSWORD in .env")
        return

    print(f"[{datetime.now()}] Connecting to Gmail IMAP...")
    
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")

        # Search for emails in the last 3 days
        date = (datetime.now() - timedelta(days=3)).strftime("%d-%b-%Y")
        status, messages = mail.search(None, f'(SINCE "{date}")')
        
        if status != "OK":
            print("Failed to search emails.")
            return

        email_ids = messages[0].split()
        if not email_ids:
            print("No recent emails found.")
            return

        companies = get_companies()
        company_names = {c['company'].lower(): c['id'] for c in companies if c['company']}

        conn = sqlite3.connect(DB_PATH)
        
        for e_id in email_ids:
            res, msg_data = mail.fetch(e_id, '(RFC822)')
            if res != "OK":
                continue
                
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Decode Subject
                    subject, encoding = decode_header(msg["Subject"])[0]
                    if isinstance(subject, bytes):
                        try:
                            subject = subject.decode(encoding if encoding else 'utf-8')
                        except:
                            subject = str(subject)
                    
                    sender = msg.get("From", "")
                    
                    # Extract Body
                    body = ""
                    if msg.is_multipart():
                        for part in msg.walk():
                            if part.get_content_type() == "text/plain":
                                try:
                                    body = part.get_payload(decode=True).decode()
                                except:
                                    pass
                                break
                    else:
                        try:
                            body = msg.get_payload(decode=True).decode()
                        except:
                            pass
                            
                    snippet = body[:200].replace('\n', ' ') + "..." if body else ""
                    
                    # Check if email is from a known company
                    matched_company = None
                    matched_job_id = None
                    
                    sender_lower = sender.lower()
                    for c_name, j_id in company_names.items():
                        # very naive matching: company name in sender address or name
                        if len(c_name) > 3 and c_name in sender_lower:
                            matched_company = c_name
                            matched_job_id = j_id
                            break
                            
                    if matched_company:
                        # Check if already processed
                        exists = conn.execute("SELECT 1 FROM job_communications WHERE email_subject = ? AND company = ?", (subject, matched_company)).fetchone()
                        if not exists:
                            status_inferred = extract_status(subject, body)
                            print(f"Match found! Company: {matched_company}, Status: {status_inferred}")
                            
                            conn.execute("""
                                INSERT INTO job_communications (job_id, company, email_subject, email_snippet, inferred_status, timestamp)
                                VALUES (?, ?, ?, ?, ?, ?)
                            """, (matched_job_id, matched_company, subject, snippet, status_inferred, datetime.now().isoformat()))
                            conn.commit()

                            # === TELEGRAM ALERT ===
                            if _TG:
                                if status_inferred == "interview":
                                    notify_interview(matched_company, subject, snippet)
                                elif status_inferred == "rejected":
                                    notify_rejection(matched_company, subject)

        conn.close()
        mail.logout()
        print(f"[{datetime.now()}] IMAP Sync complete.")
        
    except Exception as e:
        print(f"IMAP Error: {e}")

if __name__ == "__main__":
    while True:
        process_emails()
        # Sleep for 15 minutes
        time.sleep(900)
