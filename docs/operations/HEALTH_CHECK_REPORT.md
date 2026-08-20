# JARVIS AUTOMATION SYSTEM - HEALTH CHECK REPORT

**Generated:** 2026-08-20 11:15:00 IST
**Check Type:** Scheduled Cron Health Check
**Previous Check:** 2026-08-20 10:45:00 IST

---

## SUMMARY: 6/8 CRITICAL, 1/8 WARNING, 1/8 HEALTHY

| Component | Status | Trend |
|-----------|--------|-------|
| 1. Database (PostgreSQL) | 🔴 CRITICAL | ↔ Same (Docker not installed in WSL) |
| 2. Ollama (LLM Service) | 🟡 WARNING | ↔ Same (1 model: llama3.2:latest - 24s cold load) |
| 3. Alert Manager | 🔴 CRITICAL | ↔ Same (email: bad credentials - needs App Password) |
| 4. Job Automation | 🔴 CRITICAL | ↔ Same (0 applies, all sessions expired) |
| 5. Scheduler / Cron | 🔴 CRITICAL | ↔ Same (cron not installed, python3 missing in WSL) |
| 6. Disk Space | 🟢 HEALTHY | ↔ Stable (43%) |
| 7. Docker Services | 🔴 CRITICAL | ↔ Same (not installed in WSL) |
| 8. Portal Credentials | 🔴 CRITICAL | ↓ All sessions expired |

---

## 1. DATABASE (PostgreSQL)          [CRITICAL ✗]

| Check | Status |
|-------|--------|
| DATABASE_URL | NOT SET |
| Docker Container | NOT RUNNING (Docker not installed in WSL) |
| Docker Compose | Defined but not deployed |
| pg_isready | NOT AVAILABLE |
| psycopg2 | Installed in Python env |
| Init Scripts | ✓ Present at `/home/venu/Proposals/Jarvis/init-scripts/01-init.sql` |

**Impact:** All automation services depending on PostgreSQL will fail:
- Job tracking & metrics
- Event bus (cross-automation communication)
- Alert history persistence
- Interview prep bot
- Pinterest analytics

**Action Required:**
1. Install Docker in WSL: `sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin`
2. Start Docker service: `sudo service docker start`
3. Add user to docker group: `sudo usermod -aG docker $USER` (requires re-login)
4. Deploy PostgreSQL: `docker compose -f /home/venu/Proposals/Jarvis/docker-compose.yml up -d postgres`
5. Set `DATABASE_URL=postgresql://jarvis:***@localhost:5432/jarvis` in environment
6. Run init scripts (auto-run via docker-entrypoint-initdb.d)
7. Verify: `pg_isready -h localhost -p 5432 -U jarvis -d jarvis`

---

## 2. OLLAMA (LLM Service)           [WARNING ⚠]

| Check | Status |
|-------|--------|
| Binary Installed | Windows Ollama running (version 0.32.14) |
| API Endpoint | RESPONDING on port 11434 (from WSL via port forwarding) |
| Models Loaded | **1 model: llama3.2:latest (Q4_K_M, 2.0GB)** |
| Models Available | qwen2.5-coder:3b, phi4-mini, gemma2:2b, nomic-embed-text (need pull) |
| **Cold Load Time** | **~24 seconds** (causes alert false positives) |
| OLLAMA_HOST env | **BROKEN** - not set in WSL environment |

**Impact:** AI features available but slow on cold start:
- ✅ Code generation / selector analysis (when model loaded)
- ✅ Basic reasoning / writing (when model loaded)
- ❌ Embeddings / semantic search (nomic-embed-text missing)
- ❌ Fast model switching for different tasks

**Root Cause of Alert False Positive:**
- Alert check uses 5-second timeout (`requests.get(..., timeout=5)`)
- Cold model load takes ~24 seconds on first request after idle
- This triggers false "Ollama Unavailable" alerts

**Action Required:**
1. Fix OLLAMA_HOST: `export OLLAMA_HOST=http://localhost:11434` (add to ~/.bashrc)
2. Pull embeddings model: `ollama pull nomic-embed-text`
3. Increase alert check timeout to 30s in `alert_triggers.py` line 253
4. Consider keeping model warm with periodic requests (cron every 10 min)
5. Verify: `curl http://localhost:11434/api/tags`

---

## 3. ALERT MANAGER                  [CRITICAL ✗]

| Check | Status |
|-------|--------|
| Config File (alert.env) | ✓ EXISTS at `/home/venu/.jarvis/.secrets/alert.env` |
| Email Config | SMTP credentials present (Gmail) |
| Webhook Config | DISABLED (commented out) |
| ntfy Config | NOT CONFIGURED |
| **Enabled Channels** | **EMAIL ENABLED but BROKEN** (535 BadCredentials) |
| AlertManager Load Test | ✓ Loads OK (`AlertManager loads OK`) |
| Email Auth Test | ✗ FAILS (535 BadCredentials - needs App Password) |

**Impact:** NO ALERTS WILL BE DELIVERED
- Job automation failure alerts
- Database connection alerts
- Scheduler health alerts
- Disk space alerts
- Ollama availability alerts
- Portal session expiry alerts

**Root Cause:**
- Gmail requires an **App Password**, not the account password. The current `EMAIL_PASSWORD=Venureddy@123` is the account password, not an App Password.
- Webhook URL is disabled/commented out.
- ntfy.sh topic not configured.
- AlertManager convenience functions don't pass config_path correctly (creates new instance without config)

**Action Required:**
1. Generate Gmail App Password: Google Account → Security → 2-Step Verification → App Passwords
2. Update `EMAIL_PASSWORD` in `/home/venu/.jarvis/.secrets/alert.env` with the App Password
3. Set real webhook URL or keep webhook disabled
4. Configure ntfy.sh topic for mobile push notifications (free, no auth needed)
5. Fix AlertManager convenience functions to accept config_path
6. Test: `ALERT_CONFIG_PATH=/home/venu/.jarvis/.secrets/alert.env python -c "from automations.alert_manager import AlertManager; am=AlertManager(config_path='/home/venu/.jarvis/.secrets/alert.env'); am.send_alert('Test', 'Health check', 'info')"`

---

## 4. JOB AUTOMATION                 [CRITICAL ✗]

| Check | Status |
|-------|--------|
| Directory | ✓ `/home/venu/Proposals/Jarvis/automations/job-automation` |
| .env Config | Present with 4 portal credentials |
| Portal Sessions | **ALL 4 EXPIRED** (naukri: 370B, internshala: 2334B, indeed: 30B, foundit: 30B) |
| Recent Runs | 2026-08-20: 0 applications, 2 portals need relogin (naukri, internshala) |
| Applied Jobs | 83 tracked (mostly dummy/test data) |
| Daily Limit | 20 per portal |
| Headless Mode | ENABLED |
| Zero Apply Tracker | ✓ EXISTS: `{"consecutive_zero": 2, "last_date": "2026-08-19"}` |
| naukri_headless_error.png | 712 KB (debug artifact - needs investigation) |

**Portal Session Details:**
- naukri.json (370 bytes) ⚠ MINIMAL - needs re-login
- internshala.json (2334 bytes) ⚠ MINIMAL - needs re-login
- indeed.json (30 bytes) ✗ EMPTY - needs re-login
- foundit.json (30 bytes) ✗ EMPTY - needs re-login

**Recent Run Log (2026-08-18 last run):**
- Alert triggers executed
- **Job Apply Count alert triggered** (0 applications for 2 consecutive runs)
- **PostgreSQL Connection alert triggered**
- **Scheduler Health alert triggered**
- **Ollama Availability alert triggered** (false positive - cold load timeout)
- Email alert failed (bad credentials)

**Impact:** JOB APPLICATIONS NOT WORKING
- All portals require fresh authentication
- No real applications in recent runs
- naukri_headless_error.png (712 KB) indicates headless browser issues
- 2 consecutive zero-apply runs triggers critical alert

**Action Required:**
1. Re-authenticate all 4 portals (Naukri, Internshala, Indeed, Foundit)
2. Run manual test: `cd /home/venu/Proposals/Jarvis/automations/job-automation && python run.py --portal naukri --headful`
3. Verify session files are > 1KB after login
4. Check naukri_headless_error.png for debugging clues
5. Consider running in non-headless mode for initial login
6. **FIX NEEDED:** `alert_triggers.py` line 107 references `run_pipeline.py` (should be `run.py`)

---

## 5. SCHEDULER / CRON               [CRITICAL ✗]

| Check | Status |
|-------|--------|
| Cron Installed | NO (not in PATH) |
| Cron Service | NOT RUNNING |
| Crontab | NOT AVAILABLE (cron not installed) |
| Scheduler Log | ✓ EXISTS at `/home/venu/Proposals/Jarvis/automations/jarvis_cron.log` |
| Scheduler Script | ✓ EXISTS at `/home/venu/Proposals/Jarvis/jarvis_scheduler.sh` |
| System Cron | Not installed |
| **python3** | **NOT FOUND** in WSL (only `python` available via Windows Apps) |

**Alert Trigger Status:** ✗ TRIGGERED - "Scheduler Health" alert fired (cron not installed, python3 not found, log stale >30 min)

**Scheduler Log Last Entry:** 2026-08-18 05:48:15 (2 days ago)
- Script fails at line 28: `python3: command not found` (but current script uses `python`)

**Impact:** NO AUTOMATED RUNS
- Job automation not running on schedule
- Alert triggers not checking periodically
- No periodic health monitoring
- Pinterest automation not scheduled
- Scheduler script fails due to `python3` command not found in WSL

**Action Required:**
1. Install cron: `sudo apt-get install -y cron`
2. Start cron service: `sudo service cron start`
3. Install python3 in WSL: `sudo apt-get install -y python3` (or create symlink: `sudo ln -s /usr/bin/python /usr/bin/python3`)
4. Create crontab entry for periodic runs
5. Verify: `crontab -l && tail -f /home/venu/Proposals/Jarvis/automations/jarvis_cron.log`

---

## 6. DISK SPACE                     [HEALTHY ✓]

| Metric | Value |
|--------|-------|
| Usage | 43% (Stable) |
| Total | 276 GB |
| Used | 118 GB |
| Free | 159 GB |
| Warning Threshold | 85% |
| Critical Threshold | 95% |

**Trend:** Usage **stable at 43%** - safely below warning threshold

**Impact:** Safe margin from warning threshold (85%)

**Action Required:** Monitor - no immediate action needed

---

## 7. DOCKER SERVICES                [CRITICAL ✗]

| Check | Status |
|-------|--------|
| Docker Installed | NO (WSL) - Windows Docker Desktop available |
| Docker Compose | `/home/venu/Proposals/Jarvis/docker-compose.yml` ✓ DEFINED |
| Services Defined | 5 (postgres, job-automation, pinterest, model-router, gpu-exporter) + staging profile |
| Containers Running | 0 |
| Healthchecks | All defined but not executing |

**Impact:** NO CONTAINERIZED SERVICES OPERATIONAL

**Action Required:**
1. Install Docker in WSL: `sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin`
2. Start Docker: `sudo service docker start`
3. Add user to docker group: `sudo usermod -aG docker $USER` (requires re-login)
4. Start core: `docker compose -f /home/venu/Proposals/Jarvis/docker-compose.yml up -d postgres`
5. Start job-automation: `docker compose up -d job-automation`
6. Verify healthchecks: `docker ps` (check STATUS column)

---

## 8. PORTAL CREDENTIALS             [CRITICAL ✗]

| Portal | Email Configured | Session Status |
|--------|------------------|----------------|
| Naukri | ✓ | EXPIRED (370B - minimal cookies) |
| Internshala | ✓ | EXPIRED (2334B - minimal cookies) |
| Indeed | ✓ | EXPIRED (30B - empty) |
| Foundit | ✓ | EXPIRED (30B - empty) |

- Passwords: Present in `.env` (masked in display)
- SMTP Email: Configured (Gmail: pvgreddy3@gmail.com) - but needs App Password
- Webhook: Disabled
- Note: Credentials appear valid but **ALL sessions need refresh**

---

## ALERT TRIGGERS STATUS (from alert_triggers.py)

| Check | Triggered | Details |
|-------|-----------|---------|
| Job Apply Count | ✅ YES | 0 applications for 2 consecutive runs (2026-08-19, 2026-08-20) |
| PostgreSQL Connection | ✅ YES | Docker not running, port 5432 closed |
| Scheduler Health | ✅ YES | Cron not installed, python3 not found, log stale >30 min |
| Disk Space | ❌ NO | 43% < 85% threshold |
| Ollama Availability | ✅ YES | **FALSE POSITIVE** - 24s cold load exceeds 5s timeout |
| Portal Sessions | ❌ NO | Check only warns for >7 days old (sessions from Aug 16) |

---

## RECOMMENDED ACTION PLAN (Priority Order)

### 1. [IMMEDIATE] Install Docker & Start PostgreSQL
```bash
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin
sudo service docker start
sudo usermod -aG docker $USER
# Re-login or: newgrp docker
docker compose -f /home/venu/Proposals/Jarvis/docker-compose.yml up -d postgres
export DATABASE_URL=postgresql://jarvis:***@localhost:5432/jarvis
```

### 2. [IMMEDIATE] Fix Ollama Timeout & Pull Embeddings Model
```bash
# Fix OLLAMA_HOST in environment
export OLLAMA_HOST=http://localhost:11434
# Pull embeddings model
ollama pull nomic-embed-text
# Verify
curl http://localhost:11434/api/tags
```
**Code Fix:** Edit `alert_triggers.py` line 253: change `timeout=5` to `timeout=30`

### 3. [IMMEDIATE] Fix Alert Manager - Email Credentials
- Generate Gmail App Password (not account password)
- Update `EMAIL_PASSWORD` in `/home/venu/.jarvis/.secrets/alert.env` with the App Password
- Set real webhook URL or keep webhook disabled
- Fix AlertManager convenience functions to accept config_path
- Test: `ALERT_CONFIG_PATH=/home/venu/.jarvis/.secrets/alert.env python -c "from automations.alert_manager import AlertManager; am=AlertManager(config_path='/home/venu/.jarvis/.secrets/alert.env'); am.send_alert('Test', 'Health check', 'info')"`

### 4. [HIGH] Install Cron, python3 & Set Up Scheduler
```bash
sudo apt-get install -y cron python3
sudo service cron start
# Create crontab entry
crontab -l
```

### 5. [HIGH] Re-authenticate Job Portals
- Run manual login for all 4 portals
- Verify session files are substantial (>1KB)
- Test one application end-to-end
- Fix naukri headless issue (check naukri_headless_error.png)

### 6. [HIGH] Deploy Job-Automation Container
```bash
docker compose -f /home/venu/Proposals/Jarvis/docker-compose.yml up -d job-automation
# Verify healthcheck endpoint at :8080/healthz
```

### 7. [MEDIUM] Deploy Remaining Services as Needed
- pinterest
- model-router

### 8. [LOW] Clean Up Debug Artifacts
- naukri_headless_error.png (712 KB - likely debug artifact)

---

## FIXES NEEDED IN CODE

### alert_triggers.py
- **Line 107:** Fix reference from `run_pipeline.py` to `run.py`
- **Line 253:** Change `timeout=5` to `timeout=30` for Ollama check (cold load takes ~24s)
- **Lines 151, 152, 185, 186, 218, 242, 317, 318, 320, 340, 341, 344:** Replace `systemctl` commands with WSL-compatible equivalents (use `service` or direct process checks)
- **Line 161-168:** Handle `pg_isready` not found gracefully (already partially done)
- **Environment:** Fix `OLLAMA_HOST` from `0.0.0.0` to `http://localhost:11434`

### alert_manager.py
- **Lines 330-349:** Convenience functions (`send_info`, `send_warning`, `send_critical`) create `AlertManager()` without `config_path` - fix to pass config_path or use singleton from `get_alert_manager()` with proper config
- **Lines 74-81:** Config parsing works but convenience functions don't use it

### jarvis_scheduler.sh
- **Line 28:** Uses `python -m automations.alert_triggers` which works, but cron runs in WSL context where python3 may not exist

### alert.env
- Update `EMAIL_PASSWORD` to App Password (currently account password)

---

## NEXT HEALTH CHECK RECOMMENDED: After completing items 1-6

---

## SYSTEM INFO
- **OS:** WSL Ubuntu on Windows
- **Python:** 3.9.9 (available as `python` via Windows, not `python3` in WSL)
- **Project Root:** `/home/venu/Proposals/Jarvis`
- **Secrets:** `/home/venu/.jarvis/.secrets/` (Windows path: `D:/Programs/Git/home/venu/.jarvis/.secrets/`)
- **Last Full Run:** 2026-08-18 (alert triggers via manual check)
- **Report Generator:** Cron job via Hermes Agent