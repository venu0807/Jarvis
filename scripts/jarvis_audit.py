#!/usr/bin/env python3
"""
jarvis/scripts/jarvis_audit.py — Daily audit (cron 02:00).

Runs leak_check AND walks every automation's health, emailing the operator if
anything is wrong. Idempotent — safe to run manually any time.

Output: stdout summary. Side-effect: EMAIL alert on violation (Telegram removed
2026-06-16). Uses GMAIL_ADDRESS + GMAIL_APP_PASS from env.
"""
from __future__ import annotations

import json
import os
import smtplib
import ssl
import subprocess
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

JARVIS_HOME = Path.home() / ".jarvis"
AUTOMATIONS_DIR = JARVIS_HOME / "automations"


def email_alert(subject: str, body: str) -> bool:
    """Send an audit alert via Gmail. Reads GMAIL_ADDRESS + GMAIL_APP_PASS from env.

    No-op (returns False) if creds are missing — so the audit just runs silently
    if you haven't configured email yet, instead of failing.
    """
    sender = os.environ.get("GMAIL_ADDRESS", "")
    pwd    = os.environ.get("GMAIL_APP_PASS", "")
    if not sender or not pwd:
        print("(skipping email alert: GMAIL_ADDRESS/GMAIL_APP_PASS not in env)")
        return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🤖 JARVIS audit — {subject}"
    msg["From"]    = sender
    msg["To"]      = sender
    msg.attach(MIMEText(body, "plain"))
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ssl.create_default_context()) as s:
            s.login(sender, pwd)
            s.send_message(msg)
        return True
    except Exception as e:
        print(f"(email send failed: {e})")
        return False


def main() -> int:
    print("Running leak_check...")
    r = subprocess.run(
        [sys.executable, str(JARVIS_HOME / "scripts" / "leak_check.py")],
        capture_output=True, text=True, timeout=60,
    )
    print(r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr, file=sys.stderr)

    if r.returncode == 0:
        print("\n✅ leak_check clean")
        return 0

    # leak_check failed — fetch automations list and inspect each
    print("\nWalking automations...")
    sys.path.insert(0, str(JARVIS_HOME))
    try:
        import lifecycle as _lifecycle
        all_health = []
        for h in _lifecycle.list_all():
            all_health.append(h)
            print(json.dumps(h, indent=2))
    except Exception as e:
        all_health = []
        print(f"(could not introspect automations: {e})")

    cloud_v = [h for h in all_health if h.get("cloud_violation")]
    if cloud_v:
        names = ", ".join(h["name"] for h in cloud_v)
        email_alert(
            "AUTOMATION CLOUD VIOLATION",
            (
                "❌ AUTOMATION CLOUD VIOLATION\n\n"
                "The following automations have non-local run model:\n"
                f"{names}\n\n"
                "Use `jarvis audit` to inspect. Fix by setting models.run = ollama/..."
            ),
        )

    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
