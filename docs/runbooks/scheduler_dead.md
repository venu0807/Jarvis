# Runbook: Scheduler Dead (Cron Not Running)

## Overview
The JARVIS cron scheduler stops running, causing all scheduled automations to halt silently.

## Symptoms
- No new entries in `/home/venu/Proposals/Jarvis/jarvis_cron.log` for >30 minutes
- Scheduled automations (job automation at 9 AM, etc.) do not run
- Alert triggered: "Scheduler dead > 30 min" or "Cron job didn't run"
- `/health` endpoint may show stale data
- Telegram `/status` command shows old last run times
- No new log files generated in automation directories

## Impact
- All scheduled automations stop: job applications, inbox monitoring, etc.
- No new job applications submitted
- Inbox monitoring stops (no new email processing)
- Metrics collection halts
- Event bus stops processing
- System appears frozen but services may still be running

## Immediate Actions
1. **Check cron service status**:
   ```bash
   systemctl --user status cron
   ```

2. **Check if cron process is running**:
   ```bash
   ps aux | grep cron
   # Look for: /usr/sbin/cron -f
   ```

3. **Check crontab is loaded**:
   ```bash
   crontab -l
   # Should show Jarvis Ghost Protocol entries
   ```

4. **Check cron logs**:
   ```bash
   journalctl --user -u cron --since "1 hour ago"
   ```

5. **Manual test of scheduler**:
   ```bash
   # Check if scheduler script exists and is executable
   ls -la /home/venu/Proposals/Jarvis/jarvis_scheduler.sh
   
   # Run it manually in background to test
   nohup /home/venu/Proposals/Jarvis/jarvis_scheduler.sh &
   
   # Verify it's running
   ps aux | grep jarvis_scheduler
   ```

6. **Check for scheduler script errors**:
   ```bash
   /home/venu/Proposals/Jarvis/jarvis_scheduler.sh
   # See any error output
   ```

## Common Causes & Solutions

### 1. Cron Service Stopped
**Symptoms**: `systemctl --user status cron` shows inactive/dead
**Solution**:
```bash
systemctl --user start cron
systemctl --user enable cron  # Ensure starts on login
```

### 2. Cron Service Failed to Start
**Symptoms**: Service shows failed state in systemctl
**Solution**:
```bash
# Check logs for reason
journalctl --user -u cron -b

# Common fixes:
# - Fix crontab syntax errors: crontab -e
# - Fix permission issues on scheduler script
# - Fix environment variables missing in user context
```

### 3. Scheduler Script Hanging or Crashing
**Symptoms**: Cron runs but scheduler script doesn't complete
**Solution**:
```bash
# Test scheduler script directly
timeout 30 /home/venu/Proposals/Jarvis/jarvis_scheduler.sh

# Check if it's waiting for input or stuck in loop
# Look for infinite loops, missing exit conditions, or blocking calls

# Fix the script if needed, then restart cron
```

### 4. Environment Variables Missing
**Symptoms**: Scheduler runs but automations fail due to missing config
**Solution**:
- Cron runs in minimal environment
- Ensure scheduler script sources necessary env files
- Check that secrets are accessible to the cron user
- Verify paths are absolute (not relative)

### 5. Disk Full or Permission Issues
**Symptoms**: Scheduler starts but fails to write logs or execute
**Solution**:
- Check disk space: `df -h`
- Check permissions on log directories: `ls -la /home/venu/Proposals/Jarvis/automations/*/logs/`
- Clear old logs if needed

## Verification
1. Cron service active: `systemctl --user is-active cron`
2. Crontab loaded: `crontab -l` shows Jarvis entries
3. Scheduler process running: `ps aux | grep jarvis_scheduler`
4. Recent activity in cron log: `tail -n 5 /home/venu/Proposals/Jarvis/jarvis_cron.log` shows recent timestamps
5. New log files being generated in automation directories
6. Alert triggers clear (no more scheduler dead alerts)
7. Telegram `/status` command shows recent last run times
8. Automations run at their scheduled times (check next scheduled run)

## Prevention
- Monitor cron service health with alerts (already implemented)
- Set up service dependency: if cron fails, attempt restart automatically
- Log scheduler execution to separate file for easier debugging
- Use `systemd` timers instead of cron for more reliable scheduling (consider for future)
- Regularly test scheduler script manually
- Keep cron logs rotated to prevent disk space issues
- Document any environment variables needed by scheduler

## Troubleshooting Tips
1. **Check if it's a system-wide or user cron issue**:
   - User cron: `systemctl --user status cron`
   - System cron: `systemctl status cron` (less likely for JARVIS)

2. **Enable cron logging for more details**:
   - Edit `/etc/rsyslog.d/50-default.conf` to uncomment cron.log line
   - Restart rsyslog: `sudo systemctl restart rsyslog`
   - Check `/var/log/cron.log`

3. **Test scheduler environment**:
   ```bash
   # See what environment cron sees
   * * * * * env > /tmp/cron_env.txt 2>&1
   # Wait a minute, then check the file
   cat /tmp/cron_env.txt
   ```

4. **Check for common scheduler script issues**:
   - Missing shebang (`#!/usr/bin/env bash`)
   - Incorrect permissions (should be executable: `chmod +x`)
   - Syntax errors (run with `bash -n jarvis_scheduler.sh` to check)
   - Infinite loops without sleep
   - Blocking calls without timeout

## References
- JARVIS scheduler script: `/home/venu/Proposals/Jarvis/jarvis_scheduler.sh`
- Cron documentation: `man 5 crontab`
- Systemd user services: `man systemd.user`
- Jarvis Ghost Protocol: See comments in crontab for schedule details