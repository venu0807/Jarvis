"""
alert_router.py — Centralizes notifications for the Inbox Monitor module.
Sends payloads to the N8N webhook securely.
"""

import os
import sys
import requests
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent))

from dotenv import load_dotenv

# Try to load the central job-automation env for N8N_WEBHOOK_URL
dotenv_path = BASE_DIR.parent / "job-automation" / ".env"
load_dotenv(dotenv_path)

N8N_WEBHOOK_URL = os.getenv("N8N_ALERT_WEBHOOK_URL", "")

def send_alert(source: str, subject: str, summary: str, urgency: str = "Low", link: str = ""):
    """
    Sends an alert payload to N8N.
    """
    if not N8N_WEBHOOK_URL:
        print(f"⚠️ N8N_WEBHOOK_URL not configured. Cannot send alert: {subject}")
        return

    payload = {
        "event_type": "inbox_alert",
        "source": source,
        "subject": subject,
        "summary": summary,
        "urgency": urgency,
        "link": link
    }

    try:
        res = requests.post(N8N_WEBHOOK_URL, json=payload, timeout=5)
        if res.status_code in (200, 201):
            print(f"✅ Alert sent successfully to N8N: [{urgency}] {subject}")
        else:
            print(f"❌ Failed to send alert. Status {res.status_code}: {res.text}")
    except Exception as e:
        print(f"❌ Error sending alert to N8N: {e}")

if __name__ == "__main__":
    # Quick test
    send_alert("Test Source", "Test Alert", "This is a test from the alert router.", "Low", "https://example.com")
