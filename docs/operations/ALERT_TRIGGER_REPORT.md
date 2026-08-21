# JARVIS Alert Trigger Report

**Generated:** 2026-08-18 05:33:00 IST  
**Check Run:** Manual execution of `alert_triggers.py`

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

### 2. Scheduler Health: Log Missing (CRITICAL)
**Alert Key:** `scheduler_missing`

**Status:** ✅ **TRIGGERED** - Scheduler log file not found

**Evidence:**
- `/home/venu/Proposals/Jarvis/automations/jarvis_cron.log` does not exist
- `crontab` not installed in WSL
- `jarvis_scheduler.sh` exists but not running periodically

**Root Cause:** No cron/systemd timer configured to run the scheduler

**Immediate Actions Required:**
1. Install cron in WSL: `sudo apt update && sudo apt install -y cron`
2. Add cron job to run scheduler every 5-15 minutes:
   ```bash
   crontab -e
   # Add: */5 * * * * /home/venu/Proposals/Jarvis/jarvis_scheduler.sh
   ```
3. Or use systemd timer for better reliability

---

## 🟡 WARNING ALERTS TRIGGERED

### 3. Ollama Availability (WARNING)
**Alert Key:** `ollama_unavailable`

**Status:** ⚠️ **PARTIAL** - API responding but no models loaded

**Evidence:**
- `curl http://localhost:11434/api/tags` → `{"models":[]}` (empty)
- `ollama` command not found in WSL
- Ollama likely running on Windows host (Docker Desktop exposes port 11434)

**Root Cause:** Ollama not installed in WSL; no models pulled

**Immediate Actions Required:**
1. Install Ollama in WSL: `curl -fsSL https://ollama.com/install.sh | sh`
2. Pull required models:
   ```bash
   ollama pull llama3.2:3b
   ollama pull qwen2.5-coder:3b
   ollama pull nomic-embed-text
   ```
3. Or configure job automation to use Windows-host Ollama via `host.docker.internal:11434`

---

## 🔵 INFO ALERTS (Not Triggered / OK)

### 4. PostgreSQL Connection
**Alert Key:** `postgres_connection`

**Status:** ✅ **OK** - Container running and healthy

**Evidence:**
- Docker container `jarvis-postgres` status: `Up 3 hours (healthy)`
- Healthcheck: `pg_isready -U jarvis -d jarvis` passing
- Port 5432 exposed on 0.0.0.0:5432

**Note:** Alert triggers shows error because `pg_isready` and `psql` not installed in WSL, but container is healthy. The check should use Docker to verify.

### 5. Disk Space
**Alert Key:** `disk_space`

**Status:** ✅ **OK** - 69% used (well under 85% threshold)

**Evidence:**
- `/` filesystem: 276G total, 189G used, 88G free (69%)

### 6. Portal Sessions
**Alert Key:** `portal_sessions_old`

**Status:** ℹ️ **INFO** - Would trigger if sessions >7 days old (same as job alert above)

---

## 📧 EMAIL ALERTING STATUS: **BROKEN**

**Problem:** Gmail SMTP authentication failing
```
535 5.7.8 Username and Password not accepted
```

**Root Cause:** `alert.env` contains placeholder password:
```
EMAIL_PASSWORD=YOUR_GMAIL_APP_PASSWORD_HERE
```

**Required Fix:**
1. Generate Gmail App Password: https://myaccount.google.com/apppasswords
2. Update `/home/venu/.jarvis/.secrets/alert.env`:
   ```
   EMAIL_PASSWORD=<your-actual-app-password>
   ```
3. Test: `python -m automations.alert_manager "Test" "Test message" "info"`

---

## 📋 SUMMARY TABLE

| Check | Status | Severity | Action Required |
|-------|--------|----------|-----------------|
| Job Apply Count | 🔴 **FAIL** | Critical | Re-authenticate all 4 portals |
| Scheduler Health | 🔴 **FAIL** | Critical | Install cron, add scheduler job |
| PostgreSQL | ✅ **PASS** | - | (Container healthy, WSL tools missing) |
| Disk Space | ✅ **PASS** | - | None |
| Ollama | 🟡 **WARN** | Warning | Install Ollama in WSL + pull models |
| Email Alerts | 🔴 **BROKEN** | Critical | Set real Gmail App Password |
| Portal Sessions | ℹ️ **INFO** | Info | Same as Job Apply Count |

---

## 🎯 RECOMMENDED FIX ORDER (Sequential Sprint)

1. **Fix Email Alerts** → Set real Gmail App Password in `alert.env`
2. **Fix Scheduler** → Install cron, add `jarvis_scheduler.sh` to crontab
3. **Fix Job Automation** → Re-authenticate all portals (naukri, internshala, indeed, foundit)
4. **Fix Ollama** → Install in WSL, pull required models
5. **Verify PostgreSQL Check** → Update `alert_triggers.py` to use Docker for PG check

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