"""mailer.py — Send email via SMTP with optional resume attachment."""

import os
import smtplib
import ssl
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
from urllib.parse import quote


def send_email(to_address, subject, body, attachment_path=None):
    """Send an email using SMTP. Returns True on success."""
    smtp_host    = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port    = int(os.environ.get("SMTP_PORT", "465"))
    smtp_user    = os.environ.get("SMTP_USER")
    smtp_pass    = os.environ.get("SMTP_APP_PASSWORD")

    if not smtp_user or not smtp_pass:
        print("  ❌ SMTP credentials not set.")
        return False

    msg = MIMEMultipart()
    msg["From"]    = smtp_user
    msg["To"]      = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    if attachment_path and os.path.exists(attachment_path):
        try:
            filename = os.path.basename(attachment_path)
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            try:
                filename.encode("ascii")
                cd = f'attachment; filename="{filename}"'
            except UnicodeEncodeError:
                cd = f"attachment; filename*=utf-8''{quote(filename)}"
            part.add_header("Content-Disposition", cd)
            msg.attach(part)
        except Exception as e:
            print(f"  ⚠ could not attach resume: {e} — sending text only")
    elif attachment_path:
        print(f"  ℹ attachment file not found at {attachment_path} — sending clean cold email without attachment")

    try:
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30, context=ssl.create_default_context()) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        return True

    except smtplib.SMTPAuthenticationError:
        print("  ❌ SMTP auth failed (bad username/password/app-password?).")
        return False
    except Exception as e:
        print(f"  ❌ SMTP error: {e}")
        return False
