# Runbook: Portal Session Expired

## Overview
Job portal sessions (cookies/auth tokens) expire periodically, causing automation failures. Manual re-login is required to restore functionality.

## Symptoms
- Job automation shows 0 applications despite running
- Portal-specific errors in logs (e.g., "Login required", "Session invalid", "Authentication failed")
- Automation continues to run but fails to extract job data or submit applications
- No new job applications recorded in metrics database
- Alert triggered: "Job automation: 0 applies for 2+ consecutive runs" or individual portal errors

## Impact
- No new job applications being submitted
- Missed opportunities for relevant job postings
- Wasted automation runs consuming resources
- Potential delay in job search progress

## Immediate Actions
1. **Identify affected portals**:
   - Check `/home/venu/Proposals/Jarvis/automations/job-automation/logs/` for recent logs
   - Look for portal-specific error messages
   - Check which portals show 0 applies in the last 2-3 runs

2. **Manual re-login procedure for each portal**:
   
   **LinkedIn**:
   ```bash
   cd /home/venu/Proposals/Jarvis/automations/linkedin-outreach
   python3 -c "
   from linkedin_bot import LinkedInBot
   bot = LinkedInBot()
   bot.login()  # This will open browser for manual login
   print('LinkedIn login completed')
   "
   ```
   
   **Naukri.com**:
   ```bash
   cd /home/venu/Proposals/Jarvis/automations/job-automation
   python3 -c "
   from naukri_scraper import NaukriScraper
   scraper = NaukriScraper()
   scraper.login()  # Manual login required
   print('Naukri login completed')
   "
   ```
   
   **Indeed.com**:
   ```bash
   cd /home/venu/Proposals/Jarvis/automations/job-automation
   python3 -c "
   from indeed_scraper import IndeedScraper
   scraper = IndeedScraper()
   scraper.login()  # Manual login required
   print('Indeed login completed')
   "
   ```
   
   **Foundit.in** (formerly Monster India):
   ```bash
   cd /home/venu/Proposals/Jarvis/automations/job-automation
   python3 -c "
   from foundit_scraper import FounditScraper
   scraper = FounditScraper()
   scraper.login()  # Manual login required
   print('Foundit login completed')
   "
   ```
   
   **Internshala**:
   ```bash
   cd /home/venu/Proposals/Jarvis/automations/job-automation
   python3 -c "
   from internshala_scraper import InternshalaScraper
   scraper = InternshalaScraper()
   scraper.login()  # Manual login required
   print('Internshala login completed')
   "
   ```

3. **Verify login success**:
   - After manual login, run a test cycle: `cd /home/venu/Proposals/Jarvis/automations/job-automation && python3 run_pipeline.py --test`
   - Check logs for successful job extraction and application attempts
   - Verify that applies count increases in subsequent runs

4. **Update stored credentials** (if using saved sessions):
   - Delete old session files: `rm -rf /home/venu/Proposals/Jarvis/automations/*/.sessions/*`
   - The automation will create new session files after successful manual login

## Verification
- Check that subsequent automation runs show non-zero apply counts
- Verify new entries in `/home/venu/Proposals/Jarvis/automations/job-automation/output/`
- Confirm alert triggers clear (no more "zero applies" alerts)
- Monitor for 1-2 cycles to ensure stability

## Prevention
- Enable Telegram alerts for zero-applies detection
- Consider implementing automated session refresh where portals allow it
- Store credentials in password manager (1Password/Vault) with auto-rotation
- Schedule monthly manual login reminders via calendar

## Escalation
If manual login doesn't resolve the issue:
1. Check if portal has changed its login mechanism (CAPTCHA, 2FA, etc.)
2. Review portal's terms of service for automation restrictions
3. Consider using official APIs where available (LinkedIn API, Indeed Publisher API)
4. Review browser automation logs for detailed error messages
5. Contact portal support if this appears to be a false positive block

## References
- Portal-specific automation code: `/home/venu/Proposals/Jarvis/automations/job-automation/`
- Session storage: `/home/venu/Proposals/Jarvis/automations/*/.sessions/`
- Alert triggers: `/home/venu/Proposals/Jarvis/automations/alert_triggers.py`