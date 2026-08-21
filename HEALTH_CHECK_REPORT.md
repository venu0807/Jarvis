# JARVIS Automation System - Health Check Report

**Generated:** 2026-08-21 16:05:00 IST  
**Environment:** WSL Ubuntu on Windows 11 (Acer Aspire A715-51G, 12th Gen i5-1240P, 8GB RAM, GTX 1650 4GB VRAM)  
**Canonical Repo:** `/home/venu/Proposals/Jarvis/`

---

## 📊 Executive Summary

| Component | Status | Details |
|-----------|--------|---------|
| **PostgreSQL** | ❌ **DOWN** | Not running (no native process, Docker not available) |
| **Ollama** | ❌ **DOWN** | API not accessible at `http://localhost:11434` |
| **Email Alerts** | ❌ **FAILING** | Gmail App Password invalid (535 auth error) |
| **ntfy.sh Alerts** | ⚠️ **ENABLED BUT UNTESTED** | Config in alert.env, but alert_config.json has all channels disabled |
| **Scheduler/Cron** | ❌ **NOT CONFIGURED** | Cron not installed, no user crontab |
| **Python Environment** | ❌ **BROKEN** | Using Windows Python, python3 not in WSL, missing key packages |
| **Disk Space** | ✅ **HEALTHY** | 178 GB free (36% used on D:/Programs/Git mount) |
| **WSL Config** | ✅ **CONFIGURED** | memory=7GB, swap=4GB, processors=12 |
| **Docker** | ❌ **NOT AVAILABLE** | Docker CLI not in WSL PATH |
| **Job Automation** | ⚠️ **CODE READY, INFRA MISSING** | run.py fixed, but PostgreSQL/Ollama down |
| **Pinterest Automation** | ⚠️ **CODE READY, INFRA MISSING** | main.py exists, .venv exists but packages not installed |

**Overall Health: 🔴 CRITICAL - Core infrastructure non-functional**

---

## 🔍 Detailed Findings

### 1. PostgreSQL Database - ❌ DOWN
- **Expected:** PostgreSQL 16 on port 5432 (native or Docker)
- **Actual:** No PostgreSQL processes found, Docker not available in WSL
- **Impact:** Job tracking, event bus, metrics collection, all automations relying on DB will fail
- **Alert Status:** `PostgreSQL Connection` alert firing every check (see alert_triggers.log)
- **Fix Required:** Install native PostgreSQL:
  ```bash
  sudo apt update && sudo apt install -y postgresql postgresql-contrib
  sudo -u postgres psql -c "CREATE USER jarvis WITH PASSWORD 'jarvis';"
  sudo -u postgres psql -c "CREATE DATABASE jarvis OWNER jarvis;"
  sudo systemctl enable postgresql && sudo systemctl start postgresql
  ```

### 2. Ollama LLM Service - ❌ DOWN
- **API Status:** ❌ Not accessible at `http://localhost:11434/api/tags`
- **Expected Models (5):** llama3.2:3b, phi4-mini, qwen2.5-coder:3b, gemma2:2b, nomic-embed-text
- **Impact:** Model router cannot route tasks; all LLM-dependent automations fail
- **Fix Required:** 
  1. Install Ollama in WSL: `curl -fsSL https://ollama.com/install.sh | sh`
  2. Start Ollama service: `ollama serve &` or configure systemd
  3. Pull models:
     ```bash
     ollama pull qwen2.5-coder:3b
     ollama pull llama3.2:3b
     ollama pull nomic-embed-text
     ollama pull phi4:mini
     ollama pull gemma2:2b
     ```

### 3. Email Alerting - ❌ FAILING
- **Error:** `535 5.7.8 Username and Password not accepted` (Gmail SMTP)
- **Credentials Location:** `/mnt/c/Users/Venu/.jarvis/.secrets/alert.env`
- **Config Issue:** `alert_config.json` has `"email": {"enabled": false}` but alert_manager.py reads from alert.env
- **Root Cause:** Gmail password `Venureddy@123` is the regular password, not an App Password
- **Fix Required:** 
  1. Generate Gmail App Password at https://myaccount.google.com/apppasswords
  2. Update alert.env with correct App Password
  3. Enable email in alert_config.json: `"enabled": true`

### 4. ntfy.sh Alerting - ⚠️ ENABLED BUT UNTESTED
- **Status:** `NTFY_ENABLED=true` in alert.env with topic `jarvis-alerts`
- **Issue:** alert_config.json has all channels disabled, but alert_manager.py parses ntfy from .env directly
- **Potential:** Should work as fallback since no credentials needed
- **Verification Needed:** Test with `curl -d "test" https://ntfy.sh/jarvis-alerts`

### 5. Scheduler/Cron - ❌ NOT CONFIGURED
- **Cron Package:** Not installed (`cron` command not found)
- **Scheduler Script:** `/home/venu/Proposals/Jarvis/scripts/jarvis_scheduler.sh` exists but not scheduled
- **Expected Schedule (from memory):**
  - 05:45 - Prewarm Job Automation (15 min)
  - 06:00 - Job Automation
  - 09:45 - Prewarm LinkedIn Outreach (15 min)
  - 10:00 - LinkedIn Outreach
  - 13:45 - Prewarm Pinterest (15 min)
  - 14:00 - Pinterest Automation
  - 22:00 - WSL Shutdown for RAM recovery
- **Alert Status:** `Scheduler Health` alert firing (log file missing or stale)
- **Fix Required:** 
  ```bash
  sudo apt update && sudo apt install -y cron
  sudo service cron start
  crontab -e
  # Add the schedule above with proper paths
  ```

### 6. Python Environment - ❌ BROKEN
- **Active Python:** Windows Python at `D:\Programs\Hermes\hermes-agent\venv\Scripts\python` (3.11.15)
- **WSL Python:** Not installed (`/usr/bin/python3` missing)
- **Virtual Envs:** Windows-style `.venv` in pinterest/ (Scripts/ not bin/)
- **Missing Critical Packages:** `asyncpg`, `fastapi`, `uvicorn`, `pydantic`, `httpx`, `playwright`, `structlog`, `psutil`
- **Impact:** Cannot run automations natively in WSL
- **Fix Required:** 
  ```bash
  sudo apt update && sudo apt install -y python3 python3-pip python3-venv
  cd /home/venu/Proposals/Jarvis/automations/job-automation
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  pip install asyncpg structlog aiohttp httpx fastapi uvicorn pydantic psutil playwright
  playwright install chromium
  ```

### 7. Job Automation - ⚠️ CODE READY, INFRA MISSING
- **Entry Point:** `automations/job-automation/run.py` - Fixed manual argument parsing for `--headless/--headful`
- **Health Endpoint:** `/healthz` on port 8080 (checks Ollama, DB, Model Router)
- **Portals:** Naukri, Internshala, Indeed, Foundit (credentials in .env)
- **Parallel Runner:** Semaphore=2 concurrent portals
- **Browser Pool:** Context pooling for 5-10x faster execution
- **Dependencies:** PostgreSQL, Ollama, Model Router - all currently down
- **Last Run Evidence:** `naukri_headless_error.png` exists (Aug 21 14:32)

### 8. Pinterest Automation - ⚠️ CODE READY, INFRA MISSING
- **Main Entry:** `automations/pinterest/main.py`
- **Credentials:** Pinterest access token, email, session cookie in .env
- **Dependencies:** PostgreSQL, Ollama - both down
- **Virtual Env:** Exists at `.venv/` but packages not installed (Windows-style)

---

## 🚨 Active Alerts (from alert_triggers.log - Last run: 2026-08-21 14:35)

| Alert | Status | Last Triggered |
|-------|--------|----------------|
| Job Apply Count | 🔴 FIRING | 2026-08-21 14:35 |
| PostgreSQL Connection | 🔴 FIRING | 2026-08-21 14:35 |
| Scheduler Health | 🔴 FIRING | 2026-08-21 14:35 |
| Email Delivery | 🔴 FAILING | Every run (auth error) |

**Note:** All alerts fail to deliver because no channels are enabled in alert_config.json and email credentials are invalid.

---

## 🔧 Immediate Action Plan

### Priority 1: Critical Infrastructure (Do First)
1. **Install Native PostgreSQL**
   ```bash
   sudo apt update && sudo apt install -y postgresql postgresql-contrib
   sudo -u postgres psql -c "CREATE USER jarvis WITH PASSWORD 'jarvis';"
   sudo -u postgres psql -c "CREATE DATABASE jarvis OWNER jarvis;"
   sudo systemctl enable postgresql && sudo systemctl start postgresql
   ```

2. **Install & Start Ollama**
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ollama serve &
   # Wait for startup, then:
   ollama pull qwen2.5-coder:3b
   ollama pull llama3.2:3b
   ollama pull nomic-embed-text
   ollama pull phi4:mini
   ollama pull gemma2:2b
   ```

3. **Fix Gmail App Password**
   - Generate at: https://myaccount.google.com/apppasswords
   - Update `/mnt/c/Users/Venu/.jarvis/.secrets/alert.env`
   - Enable email in `alert_config.json`: `"enabled": true`

### Priority 2: Enable Scheduling
4. **Install Cron & Crontab**
   ```bash
   sudo apt update && sudo apt install -y cron
   sudo service cron start
   
   crontab -e
   # Add:
   # 45 5 * * * /home/venu/Proposals/Jarvis/scripts/prewarm.sh job-automation 15
   # 0 6 * * * cd /home/venu/Proposals/Jarvis/automations/job-automation && /home/venu/Proposals/Jarvis/automations/job-automation/.venv/bin/python run.py
   # 45 9 * * * /home/venu/Proposals/Jarvis/scripts/prewarm.sh linkedin-outreach 15
   # 0 10 * * * cd /home/venu/Proposals/Jarvis/automations/linkedin-outreach && python main.py
   # 45 13 * * * /home/venu/Proposals/Jarvis/scripts/prewarm.sh pinterest 15
   # 0 14 * * * cd /home/venu/Proposals/Jarvis/automations/pinterest && /home/venu/Proposals/Jarvis/automations/pinterest/.venv/bin/python main.py
   # 0 22 * * * wsl.exe --shutdown
   ```

### Priority 3: Python Environment
5. **Install WSL Python & Packages**
   ```bash
   sudo apt update && sudo apt install -y python3 python3-pip python3-venv
   
   # Job Automation
   cd /home/venu/Proposals/Jarvis/automations/job-automation
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   pip install asyncpg structlog aiohttp httpx fastapi uvicorn pydantic psutil playwright
   playwright install chromium
   
   # Pinterest
   cd /home/venu/Proposals/Jarvis/automations/pinterest
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

### Priority 4: Alerting Configuration
6. **Fix Alert Channels**
   - Update `alert_config.json` to enable email and ntfy channels
   - Test: `python -m automations.alert_triggers`
   - Test ntfy: `curl -d "test" https://ntfy.sh/jarvis-alerts`

---

## 📝 Configuration Files Status

| File | Status | Notes |
|------|--------|-------|
| `automations/job-automation/.env` | ✅ Exists | Real credentials (gitignored) |
| `automations/job-automation/.env.example` | ✅ Exists | REPLACE_ME placeholders |
| `automations/pinterest/.env` | ✅ Exists | Real credentials + API keys |
| `automations/pinterest/.env.example` | ✅ Exists | REPLACE_ME placeholders |
| `~/.jarvis/.secrets/alert.env` | ⚠️ Exists | Windows path only, email password invalid |
| `alert_config.json` | ⚠️ Exists | All channels disabled, legacy Telegram config |
| `docker-compose.yml` | ✅ Exists | Complete stack definition (Docker not available) |
| `.wslconfig` | ✅ Exists | Windows path, 7GB/4GB/12CPU |

---

## 🔐 Security Notes

- **SECURITY ISSUE:** `.env` files in `automations/*/` contain real portal credentials (Naukri, Internshala, Indeed, Foundit passwords)
- **Status:** Files are `.gitignored` and not tracked, but local files have original passwords
- **Action Needed:** Rotate passwords on all 4 portals + update local .env files
- **Alert.env:** Contains Gmail password (needs App Password rotation)

---

## 📈 Historical Context

- **Previous Architecture:** Full Docker Compose stack with PostgreSQL, Ollama (systemd), Grafana/Prometheus/AlertManager
- **Recent Changes:** 
  - Moved away from Docker due to caching/argument parsing issues
  - Removed Telegram integration, email-only alerting
  - Added skill-based job searches to auto_applier.py
  - Native WSL runs preferred over Docker containers
- **Current State:** Infrastructure dismantled, code ready but runtime missing

---

## ✅ Verification Checklist (Post-Fix)

- [ ] `systemctl status postgresql` shows active
- [ ] `curl http://localhost:11434/api/tags` returns 5 models
- [ ] `ollama list` shows all 5 models
- [ ] `curl http://localhost:8080/healthz` returns `{"status":"healthy",...}` (after starting job automation)
- [ ] `crontab -l` shows 6+ scheduled jobs
- [ ] Email alert test: `python -m automations.alert_triggers` sends email
- [ ] ntfy.sh test: `curl -d "test" https://ntfy.sh/jarvis-alerts` works
- [ ] `df -h /home/venu` shows >10% free
- [ ] `free -h` shows WSL memory ~5-7GB available

---

*Report generated by automated health check cron job*