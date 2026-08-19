# JARVIS AUTOMATION SYSTEM - HEALTH CHECK REPORT

**Generated:** 2026-08-18 08:10:00 IST  
**Check Type:** Scheduled Cron Health Check

---

## SUMMARY: 5/8 CRITICAL, 2/8 WARNING, 1/8 HEALTHY

| Component | Status | Trend |
|-----------|--------|-------|
| 1. Database (PostgreSQL) | 🔴 CRITICAL | ↔ Same |
| 2. Ollama (LLM Service) | 🟡 WARNING | ↔ Same |
| 3. Alert Manager | 🔴 CRITICAL | ↔ Same |
| 4. Job Automation | 🟡 WARNING | ↔ Same |
| 5. Scheduler / Cron | 🔴 CRITICAL | ↔ Same |
| 6. Disk Space | 🟡 WARNING | ⚠ Worsening (81.4% → 82%) |
| 7. Docker Services | 🔴 CRITICAL | ↔ Same |
| 8. Portal Credentials | 🟢 HEALTHY | ↔ Same |

---

## 1. DATABASE (PostgreSQL)          [CRITICAL ✗]

| Check | Status |
|-------|--------|
| DATABASE_URL | NOT SET |
| Docker Container | NOT RUNNING (Docker not installed) |
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
| Binary Installed | NOT FOUND in PATH (but API responding from Windows host) |
| API Endpoint | RESPONDING on port 11434 (returns `{"models":[]}`) |
| Models Loaded | NONE (0 models) |
| Models Needed | At least one (llama3.2, codellama, mistral) |
| OLLAMA_HOST env | **BROKEN** - set to `0.0.0.0` (should be `http://localhost:11434`) |

**Impact:** ALL AI features disabled:
- Job classification & filtering
- Cover letter generation
- Resume tailoring
- Interview preparation
- Pinterest content generation
- SEO optimization

**Action Required:**
1. Fix OLLAMA_HOST: `export OLLAMA_HOST=http://localhost:11434` (add to ~/.bashrc)
2. Install Ollama in WSL or ensure Windows Ollama serves models: `curl -fsSL https://ollama.com/install.sh | sh`
3. Pull a model: `ollama pull llama3.2`
4. Verify: `curl http://localhost:11434/api/tags`
5. Configure `OLLAMA_HOST=http://host.docker.internal:11434` in docker-compose for container access

---

## 3. ALERT MANAGER                  [CRITICAL ✗]

| Check | Status |
|-------|--------|
| Config File (alert.env) | ✓ EXISTS at `/home/venu/.jarvis/.secrets/alert.env` |
| Email Config | SMTP credentials present (Gmail) |
| Webhook Config | DISABLED (commented out) |
| Telegram | REMOVED from alert.env (correct per previous cleanup) |
| **Enabled Channels** | **ENABLED but BROKEN** (email: bad credentials) |
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
- Telegram config correctly removed (per previous cleanup).

**Action Required:**
1. Generate Gmail App Password: Google Account → Security → 2-Step Verification → App Passwords
2. Update `EMAIL_PASSWORD` in `/home/venu/.jarvis/.secrets/alert.env` with the App Password
3. Set real webhook URL or keep webhook disabled
4. Test: `python -c "from automations.alert_manager import send_info; send_info('Test', 'Health check')"`

---

## 4. JOB AUTOMATION                 [WARNING ⚠]

| Check | Status |
|-------|--------|
| Directory | ✓ `/home/venu/Proposals/Jarvis/automations/job-automation` |
| .env Config | Present with 4 portal credentials |
| Portal Sessions | 4 files exist but 2 are minimal (30 bytes) |
| Recent Runs | 2026-08-17: 0 applied, 4 portals need re-login |
| Applied Jobs | 83 tracked (mostly dummy/test data) |
| Daily Limit | 20 per portal |
| Headless Mode | ENABLED |
| naukri_headless_error.png | 660 KB (debug artifact - needs investigation) |

**Portal Session Details:**
- naukri.json (370 bytes) ✓
- internshala.json (2334 bytes) ✓
- indeed.json (30 bytes) ✗ MINIMAL - needs re-login
- foundit.json (30 bytes) ✗ MINIMAL - needs re-login

**Recent Run Log (2026-08-17):**
```json
{
  "applied": 0,
  "needs_relogin": ["naukri", "internshala", "indeed", "foundit"],
  "portal_counts": {}
}
```

**Zero Apply Tracker:** `{"consecutive_zero": 1, "last_date": "2026-08-17"}` (threshold is 2)

**Alert Trigger Status:** ✗ TRIGGERED - "Job Apply Count" alert fired (0 applications for 2+ consecutive runs - triggered at 1 run due to cooldown logic)

**Impact:** JOB APPLICATIONS NOT WORKING
- All portals require fresh authentication
- No real applications in recent runs
- naukri_headless_error.png (660 KB) indicates headless browser issues

**Action Required:**
1. Re-authenticate all 4 portals (Naukri, Internshala, Indeed, Foundit)
2. Run manual test: `cd /home/venu/Proposals/Jarvis/automations/job-automation && python run.py --portal naukri --headful`
3. Verify session files are > 1KB after login
3. Check naukri_headless_error.png for debugging clues
4. Consider running in non-headless mode for initial login
5. **FIX NEEDED:** alert_triggers.py line 107 references `run_pipeline.py` (should be `run.py`)

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
| **python3** | **NOT FOUND** (only `python` available) |

**Alert Trigger Status:** ✗ TRIGGERED - "Scheduler Health" alert fired (cron not installed, log missing, python3 not found)

**Impact:** NO AUTOMATED RUNS
- Job automation not running on schedule
- Alert triggers not checking periodically
- No periodic health monitoring
- Pinterest automation not scheduled
- Scheduler script fails due to `python3` command not found

**Action Required:**
1. Install cron: `sudo apt-get install -y cron`
2. Start cron service: `sudo service cron start`
3. Install python3: `sudo apt-get install -y python3` (or create symlink: `sudo ln -s /usr/bin/python /usr/bin/python3`)
4. Create crontab entry for periodic runs
5. Verify: `crontab -l && tail -f /home/venu/Proposals/Jarvis/automations/jarvis_cron.log`

---

## 6. DISK SPACE                     [WARNING ⚠]

| Metric | Value |
|--------|-------|
| Usage | 82% (⚠ Worsening) |
| Total | 276 GB |
| Used | 225 GB |
| Free | 52 GB |
| Warning Threshold | 85% |
| Critical Threshold | 95% |

**Trend:** Usage increased from 81.4% → 82% (0.6% increase since last check) - approaching warning threshold

**Impact:** Approaching warning threshold (85%) - investigate growth if trend continues

**Action Required:** Monitor - investigate what's consuming space, consider cleanup if trend continues toward 85%

---

## 7. DOCKER SERVICES                [CRITICAL ✗]

| Check | Status |
|-------|--------|
| Docker Installed | NO (WSL) |
| Docker Compose | `/home/venu/Proposals/Jarvis/docker-compose.yml` ✓ DEFINED |
| Services Defined | 3 (postgres, job-automation, pinterest) |
| Containers Running | 0 |
| Healthchecks | All defined but not executing |

**Impact:** NO CONTAINERIZED SERVICES OPERATIONAL

**Action Required:**
1. Install Docker: `sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin`
2. Start Docker: `sudo service docker start`
3. Add user to docker group: `sudo usermod -aG docker $USER` (requires re-login)
4. Start core: `docker compose -f /home/venu/Proposals/Jarvis/docker-compose.yml up -d postgres`
5. Start job-automation: `docker compose up -d job-automation`
6. Verify healthchecks: `docker ps` (check STATUS column)

---

## 8. PORTAL CREDENTIALS             [HEALTHY ✓]

| Portal | Email Configured |
|--------|------------------|
| Naukri | ✓ |
| Internshala | ✓ |
| Indeed | ✓ |
| Foundit | ✓ |

- Passwords: Present in `.env` (masked in display)
- SMTP Email: Configured (Gmail: pvgreddy3@gmail.com)
- Webhook: Disabled
- Note: Credentials appear valid but sessions need refresh

---

## ALERT TRIGGERS STATUS (from alert_triggers.py)

| Check | Triggered | Details |
|-------|-----------|---------|
| Job Apply Count | ✅ YES | 0 applications for consecutive runs |
| PostgreSQL Connection | Not checked | Docker not running |
| Scheduler Health | ✅ YES | Cron not installed, log missing, python3 not found |
| Disk Space | ✅ NO | 82% < 85% threshold |
| Ollama Availability | ✅ YES | 0 models loaded |
| Portal Sessions | Likely YES | All sessions old/minimal |

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

### 2. [IMMEDIATE] Install Ollama & Pull Model
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull llama3.2
curl http://localhost:11434/api/tags
```

### 3. [IMMEDIATE] Fix Alert Manager - Email Credentials
- Generate Gmail App Password (not account password)
- Update `EMAIL_PASSWORD` in `/home/venu/.jarvis/.secrets/alert.env` with the App Password
- Set real webhook URL or keep webhook disabled
- Test: `python -c "from automations.alert_manager import send_info; send_info('Test', 'Health check')"`

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

### 8. [LOW] Clean Up Debug Artifacts
- naukri_headless_error.png (660 KB - likely debug artifact)
- Investigate disk space growth (0.6% increase since last check)

---

## FIXES NEEDED IN CODE

### alert_triggers.py
- **Line 107:** Fix reference from `run_pipeline.py` to `run.py`
- **Lines 151, 152, 185, 186, 218, 242, 317, 318, 320, 340, 341, 344:** Replace `systemctl` commands with WSL-compatible equivalents (use `service` or direct process checks)
- **Line 161-168:** Handle `pg_isready` not found gracefully (already partially done)
- **Environment:** Fix `OLLAMA_HOST` from `0.0.0.0` to `http://localhost:11434`

### jarvis_scheduler.sh
- **Line 28:** Change `python3` to `python` (python3 not installed, only python available)

### alert.env
- Update `EMAIL_PASSWORD` to App Password (currently account password)

---

## NEXT HEALTH CHECK RECOMMENDED: After completing items 1-6

---

## SYSTEM INFO
- **OS:** WSL Ubuntu on Windows
- **Python:** 3.11.15 (available as `python`, not `python3`)
- **Project Root:** `/home/venu/Proposals/Jarvis`
- **Secrets:** `/home/venu/.jarvis/.secrets/`
- **Last Full Run:** 2026-08-17 (job automation)
- **Report Generator:** Cron job via Hermes Agent