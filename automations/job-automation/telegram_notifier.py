#!/usr/bin/env python3
"""
telegram_notifier.py — Instant Telegram alerts for JARVIS.

Usage:
    from telegram_notifier import notify, notify_interview, notify_daily_summary

Uses TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the job-automation .env
"""
import os
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load from job-automation .env (has the Telegram credentials)
_ENV = Path(__file__).parent / ".env"
if _ENV.exists():
    load_dotenv(_ENV)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID")
API_URL   = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"


def _send(text: str, parse_mode: str = "HTML") -> bool:
    """Low-level send. Returns True on success."""
    if not BOT_TOKEN or not CHAT_ID:
        print("⚠️  Telegram not configured (missing BOT_TOKEN or CHAT_ID)")
        return False
    try:
        r = requests.post(API_URL, json={
            "chat_id": CHAT_ID,
            "text": text,
            "parse_mode": parse_mode,
            "disable_web_page_preview": True
        }, timeout=10)
        if r.status_code != 200:
            print(f"⚠️  Telegram API error {r.status_code}: {r.text}")
            return False
        return True
    except Exception as e:
        print(f"⚠️  Telegram send failed: {e}")
        return False


def notify(title: str, message: str, emoji: str = "🤖") -> bool:
    """Generic notification."""
    now = datetime.now().strftime("%H:%M")
    text = f"{emoji} <b>{title}</b>\n{message}\n<i>{now}</i>"
    return _send(text)


def notify_interview(company: str, subject: str, snippet: str = "") -> bool:
    """🎉 Interview detected alert."""
    msg = (
        f"🎉 <b>INTERVIEW DETECTED!</b>\n\n"
        f"🏢 <b>Company:</b> {company}\n"
        f"📧 <b>Subject:</b> {subject}\n"
    )
    if snippet:
        msg += f"💬 <i>{snippet[:200]}</i>\n"
    msg += f"\n<i>Detected at {datetime.now().strftime('%H:%M on %d %b')}</i>"
    return _send(msg)


def notify_rejection(company: str, subject: str) -> bool:
    """😔 Rejection detected alert."""
    msg = (
        f"😔 <b>Rejection from {company}</b>\n"
        f"📧 {subject}\n"
        f"<i>{datetime.now().strftime('%d %b %H:%M')}</i>"
    )
    return _send(msg)


def notify_daily_summary(applied: int, skipped: int, errors: int, portals: dict) -> bool:
    """📊 Daily run summary."""
    portal_lines = "\n".join(
        f"  • {p}: {c} applied" for p, c in sorted(portals.items(), key=lambda x: -x[1])
    )
    msg = (
        f"📊 <b>JARVIS Daily Report — {datetime.now().strftime('%d %b %Y')}</b>\n\n"
        f"✅ Applied: <b>{applied}</b>\n"
        f"⏭️ Skipped: {skipped}\n"
        f"❌ Errors: {errors}\n\n"
        f"<b>By Portal:</b>\n{portal_lines if portal_lines else '  No applications today'}\n"
    )
    return _send(msg)


def notify_crash(automation: str, error: str) -> bool:
    """🚨 Crash alert."""
    msg = (
        f"🚨 <b>AUTOMATION CRASH</b>\n\n"
        f"⚙️ <b>Module:</b> {automation}\n"
        f"❌ <b>Error:</b> <code>{error[:300]}</code>\n"
        f"<i>{datetime.now().strftime('%H:%M on %d %b')}</i>"
    )
    return _send(msg)


def notify_followup_sent(company: str, email: str) -> bool:
    """📤 Follow-up email sent."""
    msg = (
        f"📤 <b>Follow-up Sent</b>\n"
        f"🏢 {company}\n"
        f"📧 {email}\n"
        f"<i>{datetime.now().strftime('%d %b %H:%M')}</i>"
    )
    return _send(msg)


if __name__ == "__main__":
    # Quick test
    print("Testing Telegram notifier...")
    ok = notify("JARVIS Online", "All systems operational. This is a test message.", "🤖")
    print("✅ Sent!" if ok else "❌ Failed — check BOT_TOKEN and CHAT_ID in .env")
