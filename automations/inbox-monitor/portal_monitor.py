"""
portal_monitor.py — Inbox Monitor for Job Portals
Logs into job portals securely via existing cookies and checks for new/unread recruiter messages.
If found, it pulls the text, uses Ollama to summarize, and routes it to N8N.
"""

import os
import sys
import asyncio
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.append(str(BASE_DIR.parent))

# Import from job-automation for the browser
try:
    sys.path.append(str(BASE_DIR.parent / "job-automation"))
    from jarvis_browser import AsyncBrowser, safe_close_async
except ImportError:
    print("❌ Failed to import AsyncBrowser from job-automation")
    sys.exit(1)

from alert_router import send_alert
from imap_scanner import analyze_email_with_llm

async def monitor_linkedin(browser):
    print("🔗 Checking LinkedIn Messages...")
    try:
        page = await browser.new_page()
        await page.goto("https://www.linkedin.com/messaging/")
        await page.wait_for_timeout(4000)
        
        # Look for unread message indicators (the unread dot)
        unread_conversations = await page.query_selector_all(".msg-conversation-card__unread-count")
        
        if not unread_conversations:
            print("No unread LinkedIn messages.")
            await page.close()
            return
            
        print(f"📬 Found {len(unread_conversations)} unread conversations on LinkedIn!")
        
        for unread in unread_conversations:
            # Click the conversation
            await unread.click()
            await page.wait_for_timeout(2000)
            
            # Extract the sender name
            sender_elem = await page.query_selector("h2.msg-entity-lockup__entity-title")
            sender = await sender_elem.inner_text() if sender_elem else "LinkedIn Recruiter"
            
            # Extract the last few messages in the thread
            msg_elems = await page.query_selector_all(".msg-s-event-listitem__body")
            msgs_text = []
            for m in msg_elems[-3:]: # Get last 3 messages to give context
                msgs_text.append(await m.inner_text())
            
            full_thread = "\\n".join(msgs_text)
            
            # Analyze
            print(f"🧠 Analyzing message from {sender}...")
            analysis = analyze_email_with_llm("LinkedIn Message", full_thread)
            
            # Alert
            send_alert(
                source="LinkedIn",
                subject=f"Message from {sender}",
                summary=analysis.get("summary", "No summary available."),
                urgency=analysis.get("urgency", "Medium"),
                link="https://www.linkedin.com/messaging/"
            )
            
        await page.close()
    except Exception as e:
        print(f"❌ LinkedIn monitor failed: {e}")

async def monitor_naukri(browser):
    print("👔 Checking Naukri Messages...")
    try:
        page = await browser.new_page()
        # Naukri's inbox is at /mnjuser/inbox
        await page.goto("https://www.naukri.com/mnjuser/inbox")
        await page.wait_for_timeout(4000)
        
        # Check for unread indicators (Naukri usually has a bold class for unread)
        unread_msgs = await page.query_selector_all(".unread")
        
        if not unread_msgs:
            print("No unread Naukri messages.")
            await page.close()
            return
            
        print(f"📬 Found {len(unread_msgs)} unread messages on Naukri!")
        # Similar extraction logic could go here. For now we just alert that there are unread messages.
        send_alert(
            source="Naukri",
            subject=f"{len(unread_msgs)} Unread Messages",
            summary="You have new recruiter messages waiting on Naukri.",
            urgency="High",
            link="https://www.naukri.com/mnjuser/inbox"
        )
        
        await page.close()
    except Exception as e:
        print(f"❌ Naukri monitor failed: {e}")

async def monitor_portals():
    print("🚀 Starting Portal Inbox Monitor...")
    
    sessions_dir = BASE_DIR.parent / "job-automation" / ".sessions"
    
    # Check LinkedIn
    linkedin_session = sessions_dir / "linkedin.json"
    if linkedin_session.exists():
        browser = AsyncBrowser(headless=True, session_file=str(linkedin_session))
        await browser.start()
        await monitor_linkedin(browser)
        await safe_close_async(browser)
        
    # Check Naukri
    naukri_session = sessions_dir / "naukri.json"
    if naukri_session.exists():
        browser = AsyncBrowser(headless=True, session_file=str(naukri_session))
        await browser.start()
        await monitor_naukri(browser)
        await safe_close_async(browser)
        
    print("✅ Portal Monitoring Complete.")

if __name__ == "__main__":
    asyncio.run(monitor_portals())
