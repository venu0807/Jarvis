"""calendar_manager.py — Generate standard .ics calendar invite and alert for interviews."""

import os
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent.parent / "job-automation" / "output" / "interviews"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def add_interview_to_calendar(company_name: str, date_time_str: str, duration_minutes: int = 45):
    """
    Creates an iCalendar (.ics) invite file for the scheduled interview
    and dispatches a Telegram notification.
    """
    print(f"📅 Creating calendar invite for {company_name} at {date_time_str}...")
    
    # Try parsing date time
    try:
        dt = datetime.datetime.fromisoformat(date_time_str)
    except Exception:
        try:
            dt = datetime.datetime.strptime(date_time_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            dt = datetime.datetime.now() + datetime.timedelta(days=1)
            
    dt_end = dt + datetime.timedelta(minutes=duration_minutes)
    
    dt_stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dt_start_str = dt.strftime("%Y%m%dT%H%M%S")
    dt_end_str = dt_end.strftime("%Y%m%dT%H%M%S")
    
    safe_company = "".join(c for c in company_name if c.isalnum() or c in (" ", "-", "_")).strip()
    ics_file = OUTPUT_DIR / f"Interview_{safe_company}_{dt.strftime('%Y%m%d')}.ics"
    
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//JARVIS AI//Interview Scheduler//EN
CALSCALE:GREGORIAN
METHOD:REQUEST
BEGIN:VEVENT
UID:jarvis-interview-{safe_company}-{dt_start_str}@jarvis.local
DTSTAMP:{dt_stamp}
DTSTART:{dt_start_str}
DTEND:{dt_end_str}
SUMMARY:Interview: {company_name}
DESCRIPTION:Scheduled interview with {company_name}. Prepared by JARVIS AI Assistant.
STATUS:CONFIRMED
BEGIN:VALARM
TRIGGER:-PT15M
ACTION:DISPLAY
DESCRIPTION:Interview Reminder: {company_name} in 15 minutes
END:VALARM
END:VEVENT
END:VCALENDAR
"""
    ics_file.write_text(ics_content)
    print(f"✅ Calendar invite saved: {ics_file}")
    
    # Push alert to Telegram if configured
    try:
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "job-automation"))
        from telegram_notifier import notify
        notify(
            f"Interview Scheduled: {company_name}",
            f"📅 <b>Time:</b> {dt.strftime('%A, %d %B %Y at %I:%M %p')}\n📁 <b>Invite:</b> <code>{ics_file.name}</code>",
            "🎉"
        )
    except Exception as e:
        print(f"Note: Telegram alert skipped: {e}")
        
    return str(ics_file)

if __name__ == "__main__":
    add_interview_to_calendar("Acme Corp", datetime.datetime.now().isoformat())
