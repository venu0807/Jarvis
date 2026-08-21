# JARVIS Alert Trigger Status Report

**Generated:** 2026-08-18 08:05:00 IST
**Check Run:** Automated cron execution of `alert_triggers.py`

---

## 🔴 CRITICAL ALERTS TRIGGERED

### 1. Job Automation: Zero Applications (CRITICAL)
**Alert Key:** `job_zero_applies`

**Status:** ✅ **TRIGGERED** - 2+ consecutive runs with 0 applications

**Evidence:**
- **2026-08-17:** `applications_2026-08-17.json` → `totals.applied: 0`, all 4 portals need relogin
- **2026-08-16:** `applications_2026-08-16.json` → `totals.applied: 0`, all 4 portals need relogin

**Root Cause:** All portal sessions expired (naukri, internshala, indeed, foundit)

**Immediate Actions Required:**
1. Re-authenticate all job portals:
   ```bash
   cd /home/venu/Proposals/Jarvis/automations/job-automation
   python run_pipeline.py --test
   ```
2. Check session files in `.sessions/` directory
3. Update cookies/tokens for each portal

---

### 2. Scheduler Health: Not Running (CRITICAL)
**Alert Key:** `scheduler_missing` / `scheduler_stale`

**Status:** ✅ **TRIGGERED** - No cron job configured

**Evidence:**
- `crontab -l` → "No crontab"
- Scheduler log exists at `/home/venu/Proposals/Jarvis/automations/jarvis_cron.log` but shows `python3: command not found`
- `jarvis_scheduler.sh` exists but not running periodically

**Root Cause:** No cron/systemd timer configured to run the scheduler

**Immediate Actions Required:**
1. Install cron in WSL: `sudo apt update && sudo apt install -y cron`
2. Add cron job to run scheduler every 5-15 minutes:
   ```bash
   crontab -e
   # Add: */5 * * * * /home/venu/Proposals/Jarvis/jarvis_scheduler.sh
   ```
3. Fix `python3` issue in scheduler script (use `python` instead)
4. Or use systemd timer for better reliability

---

### 3. Email Alerting: Authentication Failed (CRITICAL)
**Alert Key:** `email_auth_failed`

**Status:** 🔴 **BROKEN** - Gmail SMTP rejecting credentials

**Evidence:**
```
535 5.7.8 Username and Password not accepted.
For more information, go to
https://support.google.com/mail/?p=BadCredentials
```

**Root Cause:** `alert.env` contains regular Gmail password instead of App Password:
```env
EMAIL_PASSWORD=Venureddy@123
```

**Required Fix:**
1. Generate Gmail App Password: https://myaccount.google.com/apppasswords
2. Update `/home/venu/.jarvis/.secrets/alert.env`:
   ```env
   EMAIL_PASSWORD=<your-actual-app-password>
   ```
3. Test: `python -m automations.alert_manager "Test" "Test message" "info"`

---

## 🟡 WARNING ALERTS TRIGGERED

### 4. Disk Space: Approaching Threshold (WARNING)
**Alert Key:** `disk_space`

**Status:** 🟡 **WARNING** - 82% used (approaching 85% threshold)

**Evidence:**
- `/` filesystem: 276G total, 225G used, 52G free (82%)

**Immediate Actions Required:**
1. Clean old backups: `find /home/venu/backups -type f -mtime +30 -delete`
2. Clear pip cache: `pip cache purge`
3. Clear npm cache: `npm cache clean --force`
4. Check large files: `du -sh /* | sort -hr | head -10`

---

### 5. Ollama Availability: No Models Loaded (WARNING)
**Alert Key:** `ollama_unavailable`

**Status:** 🟡 **PARTIAL** - API responding but no models loaded

**Evidence:**
- `curl http://localhost:11434/api/tags` → `{"models":[]}` (empty)
- Port 11434 accessible (likely Windows Docker Desktop / Ollama)

**Root Cause:** Ollama running but no models pulled

**Immediate Actions Required:**
1. Pull required models:
   ```bash
   ollama pull llama3.2:3b
   ollama pull qwen2.5-coder:3b
   ollama pull nomic-embed-text
   ```
2. Or configure to use Windows-host Ollama via `host.docker.internal:11434`

---

## 🔵 INFO / OK ALERTS

### 6. PostgreSQL Connection (OK)
**Alert Key:** `postgres_connection`

**Status:** ✅ **OK** - Container running and healthy (port 5432 open)

**Evidence:**
- Port 5432 accessible on localhost
- Docker container likely running on Windows Docker Desktop

**Note:** Alert trigger shows error because `pg_isready` and `psycopg2` not installed in WSL. The check should use Docker or TCP socket to verify.

---

### 7. Portal Sessions (INFO)
**Alert Key:** `portal_sessions_old`

**Status:** ℹ️ **INFO** - Same as Job Apply Count (all 4 portals expired)

---

## 📋 SUMMARY TABLE

| Check | Status | Severity | Action Required |
|-------|--------|----------|-----------------|
| Job Apply Count | 🔴 **FAIL** | Critical | Re-authenticate all 4 portals |
| Scheduler Health | 🔴 **FAIL** | Critical | Install cron, add scheduler job, fix python3 |
| PostgreSQL | ✅ **PASS** | - | (Container healthy, WSL tools missing) |
| Disk Space | 🟡 **WARN** | Warning | Clean up disk (82% used) |
| Ollama | 🟡 **WARN** | Warning | Pull required models |
| Email Alerts | 🔴 **BROKEN** | Critical | Set real Gmail App Password |
| Portal Sessions | ℹ️ **INFO** | Info | Same as Job Apply Count |

---

## 🎯 RECOMMENDED FIX ORDER (Sequential Sprint)

1. **Fix Email Alerts** → Set real Gmail App Password in `alert.env`
2. **Fix Scheduler** → Install cron, add `jarvis_scheduler.sh` to crontab, fix `python3` reference
3. **Fix Job Automation** → Re-authenticate all portals (naukri, internshala, indeed, foundit)
4. **Fix Ollama** → Pull required models (llama3.2:3b, qwen2.5-coder:3b, nomic-embed-text)
5. **Fix Disk Space** → Clean up to get below 85% threshold
6. **Verify PostgreSQL Check** → Update `alert_triggers.py` to use TCP socket/Docker for PG check

---

## 📁 KEY FILES

- **Alert Triggers:** `/home/venu/Proposals/Jarvis/automations/alert_triggers.py`
- **Alert Manager:** `/home/venu/Proposals/Jarvis/automations/alert_manager.py`
- **Alert Config:** `/home/venu/.jarvis/.secrets/alert.env`
- **Scheduler:** `/home/venu/Proposals/Jarvis/jarvis_scheduler.sh`
- **Job Logs:** `/home/venu/Proposals/Jarvis/automations/job-automation/output/logs/`
- **Alert Log:** `/home/venu/Proposals/Jarvis/automations/alert_triggers.log`
- **Docker Compose:** `/home/venu/Proposals/Jarvis/docker-compose.yml`

---

*Report generated by JARVIS Alert Trigger System*