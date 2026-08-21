# JARVIS Alert Trigger Report — Current Status

**Generated:** 2026-08-20 11:50 IST
**Check Run:** Automated cron job execution of `alert_triggers.py`

---

## 🔴 CRITICAL ALERTS TRIGGERED

### 1. Job Automation: Zero Applications (CRITICAL)
**Alert Key:** `job_zero_applies`

**Status:** ✅ **TRIGGERED** — 4 consecutive runs with 0 applications

**Evidence:**
- **2026-08-20:** `applications_2026-08-20.json` → `totals.applied: 0`, `needs_relogin: ["naukri", "internshala"]`
- **2026-08-19:** `applications_2026-08-19.json` → `totals.applied: 0`, all 4 portals need relogin
- **2026-08-17:** `applications_2026-08-17.json` → `totals.applied: 0`, all 4 portals need relogin
- **2026-08-16:** `applications_2026-08-16.json` → `totals.applied: 0`, all 4 portals need relogin

**Root Cause:** Portal sessions expired (naukri, internshala). The `needs_relogin` array in latest log shows 2 portals. Indeed and Foundit may have been skipped or not checked. Session files in `.sessions/` are from Aug 16 (4 days ago).

**Immediate Actions Required:**
1. Re-authenticate job portals:
   ```bash
   cd /home/venu/Proposals/Jarvis/automations/job-automation
   python run_pipeline.py --headful
   ```
2. Check session files in `.sessions/` directory
3. Update cookies/tokens for Naukri and Internshala specifically

---

### 2. PostgreSQL Connection Failed (CRITICAL)
**Alert Key:** `postgres_connection`

**Status:** ✅ **TRIGGERED** — PostgreSQL not running

**Evidence:**
- No Docker container (Docker not installed/available in WSL)
- No PostgreSQL systemd service running
- TCP socket connection to localhost:5432 fails (connection refused)
- `psql` command not found — PostgreSQL not installed natively

**Root Cause:** PostgreSQL was previously running in Docker but Docker has been removed. No native PostgreSQL installation or service configured.

**Immediate Actions Required:**
1. Install and start PostgreSQL natively on WSL:
   ```bash
   sudo apt update && sudo apt install -y postgresql postgresql-contrib
   sudo service postgresql start
   sudo -u postgres psql -c "CREATE DATABASE jarvis;"
   sudo -u postgres psql -c "CREATE USER jarvis WITH PASSWORD 'jarvis';"
   sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE jarvis TO jarvis;"
   ```
2. Or reinstall Docker and use docker-compose:
   ```bash
   cd /home/venu/Proposals/Jarvis && docker compose up -d postgres
   ```
3. Verify connection:
   ```bash
   PGPASSWORD=jarvis psql -h localhost -U jarvis -d jarvis -c "SELECT 1;"
   ```

---

### 3. Email Alerting: Authentication Failed (CRITICAL)
**Alert Key:** `email_alerting`

**Status:** ✅ **TRIGGERED** — Gmail SMTP authentication failing

**Evidence:**
```
535 5.7.8 Username and Password not accepted
```

**Root Cause:** `/home/venu/.jarvis/.secrets/alert.env` contains regular Gmail password instead of App Password:
```
EMAIL_PASSWORD=Venureddy@123
```

**Immediate Actions Required:**
1. Generate Gmail App Password: https://myaccount.google.com/apppasswords
2. Update `/home/venu/.jarvis/.secrets/alert.env`:
   ```
   EMAIL_PASSWORD=<your-actual-app-password>
   ```
3. Test:
   ```bash
   python -m automations.alert_manager "Test" "Test message" "info"
   ```

---

### 4. Scheduler Health Check (CRITICAL)
**Alert Key:** `scheduler_stale`

**Status:** ✅ **TRIGGERED** — Scheduler log not updated in >30 minutes (last run: 2026-08-18, 2+ days ago)

**Evidence:**
- Cron daemon not installed (`cron` package not installed)
- No crontab configured (`crontab -l` → command not found)
- Scheduler log exists: `/home/venu/Proposals/Jarvis/automations/jarvis_cron.log` but last updated **Aug 18** (2 days ago)
- Scheduler script has `python3: command not found` error in logs

**Root Cause:** Two issues:
1. **Cron not installed** — `cron` package missing from WSL
2. **Scheduler script uses `python3`** which doesn't exist in WSL (only `python`)

**Immediate Actions Required:**
1. Install and configure cron:
   ```bash
   sudo apt update && sudo apt install -y cron
   sudo service cron start
   # Add crontab entries for 6 AM, 10 AM, 2 PM runs
   crontab -e
   ```
2. Fix scheduler script to use `python` instead of `python3`:
   ```bash
   sed -i 's/python3/python/g' /home/venu/Proposals/Jarvis/jarvis_scheduler.sh
   ```
3. Or use systemd timers as alternative

---

## 🟢 CHECKS PASSING (OK)

### 5. Disk Space
**Alert Key:** `disk_space`

**Status:** ✅ **OK** — 43% used (well under 85% threshold)

**Evidence:**
- `/` filesystem: 276G total, 118G used, 159G free (43%)

---

### 6. Ollama Availability
**Alert Key:** `ollama_unavailable`

**Status:** ✅ **OK** — API responding with models loaded

**Evidence:**
- `curl http://localhost:11434/api/tags` returns 200 OK
- Models loaded: `llama3.2:latest` (Q4_K_M, 2.0 GB)

---

### 7. Portal Sessions
**Alert Key:** `portal_sessions_old`

**Status:** ℹ️ **INFO** — Session files are 4 days old (not >7 days yet)

**Evidence:** Session files in `.sessions/` are from Aug 16. While not >7 days old, `needs_relogin` in application logs indicates functional expiration for Naukri and Internshala.

---

## 📋 SUMMARY TABLE

| Check | Status | Severity | Action Required |
|-------|--------|----------|-----------------|
| Job Apply Count | 🔴 **FAIL** | Critical | Re-authenticate Naukri & Internshala portals |
| PostgreSQL | 🔴 **FAIL** | Critical | Install/start PostgreSQL (native or Docker) |
| Email Alerts | 🔴 **FAIL** | Critical | Set real Gmail App Password in `alert.env` |
| Scheduler Health | 🔴 **FAIL** | Critical | Install cron, fix scheduler script |
| Disk Space | ✅ **PASS** | - | None |
| Ollama | ✅ **PASS** | - | None |
| Portal Sessions | ℹ️ **INFO** | Info | Same as Job Apply Count |

---

## 🎯 RECOMMENDED FIX ORDER (Sequential Sprint)

1. **Fix Email Alerts** → Set real Gmail App Password in `alert.env`
2. **Fix PostgreSQL** → Install PostgreSQL natively on WSL (since Docker removed)
3. **Fix Job Automation** → Re-authenticate Naukri & Internshala portals (run with `--headful`)
4. **Fix Scheduler** → Install cron, configure crontab, fix `python3` → `python` in scheduler script

---

## 📁 KEY FILES & COMMANDS

| Component | Path / Command |
|-----------|----------------|
| Alert Triggers | `/home/venu/Proposals/Jarvis/automations/alert_triggers.py` |
| Alert Manager | `/home/venu/Proposals/Jarvis/automations/alert_manager.py` |
| Alert Config | `/home/venu/.jarvis/.secrets/alert.env` |
| Job Logs | `/home/venu/Proposals/Jarvis/automations/job-automation/output/logs/` |
| Scheduler Log | `/home/venu/Proposals/Jarvis/automations/jarvis_cron.log` |
| Scheduler Script | `/home/venu/Proposals/Jarvis/jarvis_scheduler.sh` |
| Docker Compose | `/home/venu/Proposals/Jarvis/docker-compose.yml` |
| Re-auth Job Portals | `cd /home/venu/Proposals/Jarvis/automations/job-automation && python run_pipeline.py --headful` |
| Start Postgres (native) | `sudo apt install postgresql && sudo service postgresql start` |
| Test Email | `python -m automations.alert_manager "Test" "Test message" "info"` |
| Install Cron | `sudo apt update && sudo apt install -y cron && sudo service cron start` |
| Fix Scheduler Script | `sed -i 's/python3/python/g' /home/venu/Proposals/Jarvis/jarvis_scheduler.sh` |

---

## 📊 DETAILED CHECK RESULTS

### Job Apply Count Check
```python
check_job_apply_count() → True (ALERT TRIGGERED)
```
- Scans last 5 application log files
- Counts consecutive runs with `totals.applied == 0`
- 4 consecutive zero-apply runs found (≥2 threshold)
- Latest run (Aug 20): `needs_relogin: ["naukri", "internshala"]`

### PostgreSQL Check
```python
check_postgres_connection() → True (ALERT TRIGGERED)
```
- TCP socket connection to localhost:5432
- Connection refused (no service listening on port 5432)
- No native PostgreSQL installation (`psql` not found)
- No Docker available

### Scheduler Health Check
```python
check_scheduler_health() → True (ALERT TRIGGERED)
```
- Checks for `SCHEDULER_LOG` existence and mtime < 30 min
- Log file exists but last modified **2026-08-18 05:48** (2+ days ago)
- Cron not installed, no crontab, scheduler effectively dead
- Scheduler script uses `python3` which doesn't exist in WSL

### Disk Space Check
```python
check_disk_space() → False (OK)
```
- `psutil.disk_usage('/')` → 43% used

### Ollama Availability Check
```python
check_ollama_availability() → False (OK)
```
- HTTP GET `http://localhost:11434/api/tags` → 200 OK
- Models: `llama3.2:latest` (Q4_K_M)

### Portal Sessions Check
```python
check_portal_sessions() → False (OK - no files >7 days)
```
- Checks session files in `.sessions/`, `.linkedin_sessions/`, etc.
- Current session files are recent (4 days old)
- But `needs_relogin` in application logs indicates functional expiration

---

*Report generated by JARVIS Alert Trigger System*