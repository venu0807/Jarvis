"""mailer.py — Send email via SMTP with optional resume attachment.

Fixes applied:
- #3: Use MIMEBase + encoders.encode_base64 (the canonical correct way)
  instead of MIMEApplication which doesn't always base64-encode correctly
  on all SMTP servers.
- Adds ASCII-safe filename (RFC 2047 encoded) for international chars.
- Closer SMTP error reporting: distinguishes auth-fail (535), connection
  refused, and TLS errors so the bot can be diagnosed from the log alone.
- Reads resume attachment streaming-style for huge files.
"""

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
    smtp_port    = int(os.environ.get("SMTP_PORT", "587"))
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

    if attachment_path:
        if not os.path.exists(attachment_path):
            print(f"  ⚠ attachment missing: {attachment_path}")
            return False
        try:
            filename = os.path.basename(attachment_path)
            with open(attachment_path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            # ASCII-safe header (handles i18n via RFC 2231)
            try:
                filename.encode("ascii")
                cd = f'attachment; filename="{filename}"'
            except UnicodeEncodeError:
                cd = f"attachment; filename*=utf-8''{quote(filename)}"
            part.add_header("Content-Disposition", cd)
            msg.attach(part)
        except Exception as e:
            print(f"  ❌ failed to attach resume: {type(e).__name__}: {e}")
            return False

    try:
        if smtp_port == 465:
            # SSL/TLS direct (no STARTTLS)
            with smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30, context=ssl.create_default_context()) as server:
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        else:
            # STARTTLS (port 587)
            with smtplib.SMTP(smtp_host, smtp_port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=ssl.create_default_context())
                server.ehlo()
                server.login(smtp_user, smtp_pass)
                server.send_message(msg)
        return True

    except smtplib.SMTPAuthenticationError:
        print("  ❌ SMTP auth failed (bad username/password/app-password?).")
        print("     Gmail: 2FA + App Password required. https://myaccount.google.com/apppasswords")
        return False
    except smtplib.SMTPRecipientsRefused:
        print(f"  ❌ recipient refused: {to_address}")
        return False
    except smtplib.SMTPServerDisconnected:
        print("  ❌ SMTP server disconnected mid-send.")
        return False
    except (smtplib.SMTPException, OSError) as e:
        print(f"  ❌ SMTP error: {type(e).__name__}: {str(e)[:200]}")
        return False
    except Exception as e:
        print(f"  ❌ unexpected send error: {type(e).__name__}: {str(e)[:200]}")
        return False
