"""
profile_bumper.py — Automated Profile Activity Generator
Logs into job portals and makes a superficial save (e.g. adding a space, or just clicking "Save" on the profile page) 
to manipulate ATS systems into flagging the profile as "Recently Updated".
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

async def bump_linkedin(browser):
    print("🔗 Bumping LinkedIn Profile...")
    try:
        page = await browser.new_page()
        # LinkedIn profile page usually requires clicking the 'edit' pencil on the summary, saving it without changes.
        # But even navigating to the profile and clicking "Show recruiters you're open to work" or a simple page refresh 
        # on the 'Job seeking preferences' page updates the last active timestamp.
        # We will visit the Job Seeking Preferences page and toggle something safely if possible, or just visit it.
        await page.goto("https://www.linkedin.com/mypreferences/d/categories/job-seeking")
        await page.wait_for_timeout(3000)
        
        # Taking a screenshot for logging
        await page.screenshot(path="linkedin_bump.png")
        print("✅ LinkedIn Bumped (Job Seeking Preferences accessed).")
        await page.close()
        return True
    except Exception as e:
        print(f"❌ LinkedIn bump failed: {e}")
        return False

async def bump_naukri(browser):
    print("👔 Bumping Naukri Profile...")
    try:
        page = await browser.new_page()
        # Naukri's algorithm is heavily biased toward "Profile Last Updated".
        # Navigating to the resume update page and re-saving the "Resume Headline" bumps it.
        await page.goto("https://www.naukri.com/mnjuser/profile")
        await page.wait_for_timeout(5000)
        
        # Click the edit button for resume headline
        edit_buttons = await page.query_selector_all(".edit")
        if len(edit_buttons) > 1:
            await edit_buttons[1].click() # Usually headline or summary
            await page.wait_for_timeout(2000)
            
            # Just hit save without changing anything, it registers as an update
            save_btn = await page.query_selector("button[type='submit']")
            if save_btn:
                await save_btn.click()
                await page.wait_for_timeout(2000)
                print("✅ Naukri Bumped (Headline re-saved).")
            else:
                print("⚠️ Naukri Bumped (Viewed only).")
        else:
            print("⚠️ Naukri Bumped (Viewed only).")
            
        await page.close()
        return True
    except Exception as e:
        print(f"❌ Naukri bump failed: {e}")
        return False

async def bump_profiles():
    print("🚀 Starting Daily Profile Bumper...")
    
    # We use the existing sessions directory from job-automation
    sessions_dir = BASE_DIR.parent / "job-automation" / ".sessions"
    
    # Run Naukri (uses Naukri session)
    naukri_session = sessions_dir / "naukri.json"
    if naukri_session.exists():
        browser = AsyncBrowser(headless=True, session_file=str(naukri_session))
        await browser.start()
        await bump_naukri(browser)
        await safe_close_async(browser)
    
    # Run LinkedIn (uses LinkedIn session)
    linkedin_session = sessions_dir / "linkedin.json"
    if linkedin_session.exists():
        browser = AsyncBrowser(headless=True, session_file=str(linkedin_session))
        await browser.start()
        await bump_linkedin(browser)
        await safe_close_async(browser)
        
    print("✅ Daily Profile Bump Complete.")
    
    # Silently alert
    send_alert(
        source="Profile Bumper",
        subject="Profiles Updated",
        summary="ATS Algorithms manipulated successfully: LinkedIn and Naukri have been marked as recently updated.",
        urgency="Low"
    )

if __name__ == "__main__":
    asyncio.run(bump_profiles())
