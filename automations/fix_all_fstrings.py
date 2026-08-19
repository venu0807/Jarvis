import re

with open('/home/venu/Proposals/Jarvis/automations/alert_triggers.py', 'r') as f:
    content = f.read()

# Fix all broken f-string concatenations
# Pattern: message=f"..." followed by multiple f"..." lines ending with a comma
# We need to wrap them in parentheses and use {NL} for newlines

# Fix 1: scheduler_missing block
old1 = '''message=f"JARVIS scheduler log file not found: {SCHEDULER_LOG}\n\n"
                            f"This suggests the cron scheduler may not be running.\n"
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                            f"Immediate actions:\n"
                            f"1. Check cron service: systemctl --user status cron\n"
                            f"2. Check crontab: crontab -l\n"
                            f"3. Restart scheduler: {JARVIS_HOME}/jarvis_scheduler.sh &\n"
                            f"4. Verify it's running: ps aux | grep jarvis_scheduler",'''

new1 = '''message=(
                            f"JARVIS scheduler log file not found: {SCHEDULER_LOG}{NL}{NL}"
                            "This suggests the cron scheduler may not be running.{NL}"
                            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                            "Immediate actions:{NL}"
                            "1. Check cron service: systemctl --user status cron{NL}"
                            "2. Check crontab: crontab -l{NL}"
                            f"3. Restart scheduler: {JARVIS_HOME}/jarvis_scheduler.sh &{NL}"
                            "4. Verify it's running: ps aux | grep jarvis_scheduler"
                        ),'''

content = content.replace(old1, new1)

# Fix 2: scheduler_stale block
old2 = '''message=f"JARVIS scheduler log has not been updated in >30 minutes.\n\n"
                                f"Last activity: {mtime.strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                                f"Log file: {SCHEDULER_LOG}\n\n"
                                f"This indicates the cron scheduler may have stopped.\n\n"
                                f"Immediate actions:\n"
                                f"1. Check scheduler process: ps aux | grep jarvis_scheduler\n"
                                f"2. Check cron logs: journalctl --user -u cron\n"
                                f"3. Restart scheduler: nohup {JARVIS_HOME}/jarvis_scheduler.sh &\n"
                                f"4. Verify crontab is installed: crontab -l\n"
                                f"5. Check for errors in scheduler script",'''

new2 = '''message=(
                                f"JARVIS scheduler log has not been updated in >30 minutes.{NL}{NL}"
                                f"Last activity: {mtime.strftime('%Y-%m-%d %H:%M:%S')}{NL}"
                                f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}"
                                f"Log file: {SCHEDULER_LOG}{NL}{NL}"
                                "This indicates the cron scheduler may have stopped.{NL}{NL}"
                                "Immediate actions:{NL}"
                                "1. Check scheduler process: ps aux | grep jarvis_scheduler{NL}"
                                "2. Check cron logs: journalctl --user -u cron{NL}"
                                f"3. Restart scheduler: nohup {JARVIS_HOME}/jarvis_scheduler.sh &{NL}"
                                "4. Verify crontab is installed: crontab -l{NL}"
                                "5. Check for errors in scheduler script"
                            ),'''

content = content.replace(old2, new2)

# Fix 3: disk_space block
old3 = '''message=(
                        f"Disk usage is critical: {percent_used:.1f}% used{NL}{NL}"
                        f"Total: {disk.total // (1024**3)} GB{NL}"
                        f"Used: {disk.used // (1024**3)} GB{NL}"
                        f"Free: {disk.free // (1024**3)} GB{NL}"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                        "Immediate actions:{NL}"
                        "1. Clean old backups: find /home/venu/backups -type f -mtime +30 -delete{NL}"
                        "2. Clear pip cache: pip cache purge{NL}"
                        "3. Clear npm cache: npm cache clean --force{NL}"
                        "4. Check large files: du -sh /* | sort -hr | head -10{NL}"
                        "5. Consider expanding disk space"
                    ),'''

# This one looks OK already - uses parentheses. Let me check if there's a broken version.
old3_broken = '''message=f"Disk usage is critical: {percent_used:.1f}% used\n\n"
                        f"Total: {disk.total // (1024**3)} GB\n"
                        f"Used: {disk.used // (1024**3)} GB\n"
                        f"Free: {disk.free // (1024**3)} GB\n"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        "Immediate actions:\n"
                        "1. Clean old backups: find /home/venu/backups -type f -mtime +30 -delete\n"
                        "2. Clear pip cache: pip cache purge\n"
                        "3. Clear npm cache: npm cache clean --force\n"
                        "4. Check large files: du -sh /* | sort -hr | head -10\n"
                        "5. Consider expanding disk space",'''

content = content.replace(old3_broken, new1)  # reuse new1 pattern but this is different
# Actually let me just fix it properly
new3 = '''message=(
                        f"Disk usage is critical: {percent_used:.1f}% used{NL}{NL}"
                        f"Total: {disk.total // (1024**3)} GB{NL}"
                        f"Used: {disk.used // (1024**3)} GB{NL}"
                        f"Free: {disk.free // (1024**3)} GB{NL}"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                        "Immediate actions:{NL}"
                        "1. Clean old backups: find /home/venu/backups -type f -mtime +30 -delete{NL}"
                        "2. Clear pip cache: pip cache purge{NL}"
                        "3. Clear npm cache: npm cache clean --force{NL}"
                        "4. Check large files: du -sh /* | sort -hr | head -10{NL}"
                        "5. Consider expanding disk space"
                    ),'''

content = content.replace(old3_broken, new3)

# Fix 4: ollama_unavailable block (status code version)
old4 = '''message=(
                        "Ollama API is not responding correctly.{NL}{NL}"
                        f"Status code: {response.status_code}{NL}"
                        f"Response: {response.text[:200] if response.text else 'No response'}{NL}"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                        "Impact:{NL}"
                        "- AI job classification will fail{NL}"
                        "- Cover letter generation disabled{NL}"
                        "- Resume tailoring unavailable{NL}"
                        "- Interview preparation affected{NL}{NL}"
                        "Immediate actions:{NL}"
                        "1. Check Ollama service: systemctl --user status ollama{NL}"
                        "2. Restart Ollama: systemctl --user restart ollama{NL}"
                        "3. Verify it's running: curl http://localhost:11434/api/tags{NL}"
                        "4. Check logs: journalctl --user -u ollama{NL}"
                        "5. Pull a model to test: ollama pull llama3.2"
                    ),'''

# This one looks OK too. Let me check for broken version.
old4_broken = '''message=f"Ollama API is not responding correctly.\n\n"
                        f"Status code: {response.status_code}\n"
                        f"Response: {response.text[:200] if response.text else 'No response'}\n"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        "Impact:\n"
                        "- AI job classification will fail\n"
                        "- Cover letter generation disabled\n"
                        "- Resume tailoring unavailable\n"
                        "- Interview preparation affected\n\n"
                        "Immediate actions:\n"
                        "1. Check Ollama service: systemctl --user status ollama\n"
                        "2. Restart Ollama: systemctl --user restart ollama\n"
                        "3. Verify it's running: curl http://localhost:11434/api/tags\n"
                        "4. Check logs: journalctl --user -u ollama\n"
                        "5. Pull a model to test: ollama pull llama3.2",'''

content = content.replace(old4_broken, old4)

# Fix 5: ollama_unavailable block (exception version)
old5_broken = '''message=f"Cannot connect to Ollama API.\n\n"
                    f"Error: {str(e)}\n"
                    f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    "This usually means Ollama is not running.\n\n"
                    "Immediate actions:\n"
                    "1. Start Ollama: systemctl --user start ollama\n"
                    "2. Enable at startup: systemctl --user enable ollama\n"
                    "3. Verify installation: which ollama\n"
                    "4. Pull a test model: ollama pull llama3.2\n"
                    "5. Check if port 11434 is listening: ss -tlnp | grep 11434",'''

new5 = '''message=(
                    "Cannot connect to Ollama API.{NL}{NL}"
                    f"Error: {str(e)}{NL}"
                    f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                    "This usually means Ollama is not running.{NL}{NL}"
                    "Immediate actions:{NL}"
                    "1. Start Ollama: systemctl --user start ollama{NL}"
                    "2. Enable at startup: systemctl --user enable ollama{NL}"
                    "3. Verify installation: which ollama{NL}"
                    "4. Pull a test model: ollama pull llama3.2{NL}"
                    "5. Check if port 11434 is listening: ss -tlnp | grep 11434"
                ),'''

content = content.replace(old5_broken, new5)

# Fix 6: portal_sessions_old block
old6_broken = '''message=(
                    "Some portal session files are older than 7 days.{NL}{NL}"
                    "Old sessions found:{NL}" + "\n".join(f"  - {s}" for s in old_sessions[:5]) +
                    (f"{NL}  - ... and {len(old_sessions)-5} more" if len(old_sessions) > 5 else "") +
                    f"{NL}{NL}Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                    "Note: This is informational. Actual expiration varies by portal.{NL}"
                    "Most portals require re-login every 1-7 days.{NL}{NL}"
                    "Recommended action:{NL}"
                    "Run manual login refresh for portals showing issues:{NL}"
                    '- LinkedIn: python3 -c "from automations.linkedin_outreach.linkedin_bot import LinkedInBot; b=LinkedInBot(); b.login()"{NL}'
                    "- Naukri: Similar process in job-automation{NL}"
                    "- Indeed: Check job-automation/indeed_scraper.py"
                ),'''

# This one looks complex but might be OK. Let me check for broken version.
old6_broken2 = '''message=(
                    "Some portal session files are older than 7 days.\n\n"
                    "Old sessions found:\n" + "\n".join(f"  - {s}" for s in old_sessions[:5]) +
                    (f"\n  - ... and {len(old_sessions)-5} more" if len(old_sessions) > 5 else "") +
                    f"\n\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    "Note: This is informational. Actual expiration varies by portal.\n"
                    "Most portals require re-login every 1-7 days.\n\n"
                    "Recommended action:\n"
                    "Run manual login refresh for portals showing issues:\n"
                    '- LinkedIn: python3 -c "from automations.linkedin_outreach.linkedin_bot import LinkedInBot; b=LinkedInBot(); b.login()"\n'
                    "- Naukri: Similar process in job-automation\n"
                    "- Indeed: Check job-automation/indeed_scraper.py"
                ),'''

content = content.replace(old6_broken2, old6_broken)

with open('/home/venu/Proposals/Jarvis/automations/alert_triggers.py', 'w') as f:
    f.write(content)

print('Fixed all broken f-string blocks')