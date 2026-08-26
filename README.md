# 🦞 JARVIS — AI-Powered Career Automation & Command Center

[![Jarvis CI](https://github.com/venu0807/Jarvis/actions/workflows/ci.yml/badge.svg)](https://github.com/venu0807/Jarvis/actions/workflows/ci.yml)
[![Next.js](https://img.shields.io/badge/Next.js-16.2.10-black?style=flat&logo=next.js)](https://nextjs.org/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.14-blue?style=flat&logo=python)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-Browser%20Automation-45ba4b?style=flat&logo=playwright)](https://playwright.dev/)
[![Ollama](https://img.shields.io/badge/Ollama-Local%20AI%20(qwen2.5--coder)-purple?style=flat&logo=ollama)](https://ollama.ai/)
[![Database](https://img.shields.io/badge/Storage-PostgreSQL%20%7C%20SQLite-336791?style=flat&logo=postgresql)](https://postgresql.org/)

**JARVIS** is an autonomous, local-first automation orchestrator and career management platform. Running entirely inside **Ubuntu WSL2** with hardware-accelerated local AI inference, JARVIS automates job discovery, intelligent multi-portal applications, direct recruiter cold outreach, and interview preparation.

---

## ⚡ Key Modules & Capabilities

### 1. 💼 Unified 4-Portal + Manual Job Tracker
- **Multi-Portal Engine**: Autonomous scraping and application execution across **Naukri**, **Indeed**, **Internshala**, and **Foundit (Monster)**.
- **Smart Manual URL Importer**: Paste any job link into the dashboard (`🔗 + Add Job by URL`); JARVIS uses regex slug decomposition and local AI to parse the company, title, location, and experience even behind anti-bot login walls.
- **Dynamic Portal Filtering & CSV Export**: Interactive filter chips (`All`, `Naukri`, `Indeed`, `Internshala`, `Foundit`, `Manual`) and 1-click **`📥 Export CSV`** downloads.

### 2. 🎯 Autonomous Interview Prep & Notes Hub
- **24/7 Email Daemon**: Real-time Gmail IMAP listener parsing interview invitations across a 7-day rolling lookback window.
- **Calendar & Cheat Sheet Synthesis**: Automatically generates `.ics` calendar entries and produces structured interview prep notes (company background, tech stack expectations, common DSA/system questions) rendered in a dual-column dashboard viewer.

### 3. 📬 Recruiter Cold Outreach Engine
- **Direct-to-Recruiter Routing**: Scrapes hiring posts and extracts recruiter/HR emails (`hr@...`, `recruiter@...`) while eliminating unwanted self-notifications.
- **Contextual Cold Emailing**: Generates customized emails tailored for **Fresher / MCA 2026** candidates highlighting relevant portfolio projects and skills.

### 4. 🖥️ Full-Stack Next.js Command Center
- **Modern Glassmorphic UI**: Real-time KPI tiles, portal distribution metrics, active process indicators, and instant local search.
- **Daily Upskill & AI Chat**: Integrated coding interview prompts and real-time local chat assistance.

### 5. 🛡️ Zero-Leak Local AI Architecture
- **100% Local Inference**: Powered by local Ollama (`qwen2.5-coder:3b`) without recurring API fees or data leakage risks.
- **Resilient Process Orchestration**: Background services managed via **PM2** and **systemd**, with crontab lockfile safety.

---

## 📂 Architecture & Directory Structure

```
/home/venu/Proposals/Jarvis/
├── .github/workflows/ci.yml          # GitHub Actions CI pipeline (Python & Next.js builds)
├── automations/
│   ├── dashboard-nextjs/             # Full-Stack Next.js 16 Web Command Center
│   │   ├── src/app/                  # App Router pages and API routes
│   │   │   ├── api/interviews/       # Interview preparation & cheat sheet API
│   │   │   ├── api/jobs/             # 4-Portal Job tracker API
│   │   │   ├── api/jobs/manual-add/  # Smart URL parser & local AI deconstructor
│   │   │   ├── api/outreach/         # Recruiter cold email tracking API
│   │   │   └── page.tsx              # Main dashboard interface
│   │   └── package.json
│   │
│   ├── job-automation/               # 🎯 Multi-Portal Auto-Applier Suite
│   │   ├── portals/                  # Portal handlers (Naukri, Indeed, Internshala, Foundit)
│   │   ├── auto_applier.py           # Core form-filler and application dispatcher
│   │   ├── run_pipeline.py           # Automated pipeline orchestrator
│   │   ├── db_logger.py              # SQLite & PostgreSQL dual database logger
│   │   └── output/jobs.db            # Persistent job application SQLite database
│   │
│   ├── interview_scheduler_prep_bot/ # 📅 Email Listener & Prep Generator
│   │   ├── email_listener.py         # 24/7 Gmail IMAP scheduler
│   │   ├── prep_generator.py         # AI interview notes synthesizer
│   │   └── calendar_manager.py       # .ics calendar event generator
│   │
│   ├── linkedin-outreach/            # 💼 Recruiter Cold Outreach Suite
│   │   ├── main.py                   # Discovery, extraction, and dispatch orchestrator
│   │   ├── composer.py               # Local AI cold email drafter
│   │   ├── templates.py              # Candidate project and background templates
│   │   └── mailer.py                 # Resilient SMTP delivery handler
│   │
│   ├── pinterest/                    # 📌 Content automation & marketing suite
│   ├── alert_manager.py              # Desktop, ntfy, and email notification router
│   ├── jarvis_boot.sh                # System boot & service startup script
│   └── secrets_manager.py            # Local credential and environment isolation
│
├── grafana/                          # Grafana observability dashboards & datasources
├── health_check_wsl.sh               # Ecosystem diagnostic & health audit script
└── README.md
```

---

## 🚀 Quick Start & Operations

### 1. Dashboard Web UI
```bash
# Start or inspect the Next.js Dashboard via PM2
pm2 status
pm2 restart jarvis-dashboard

# Access in your browser:
http://localhost:3001
```

### 2. Interview Scheduler Service
```bash
# Verify the 24/7 background email listener daemon
systemctl --user status buzz-jarvis-interview-listener.service
```

### 3. Running Job Automation Pipeline
```bash
# Run multi-portal discovery and application pipeline
python3 automations/job-automation/run_pipeline.py
```

### 4. Recruiter Cold Outreach
```bash
# Execute LinkedIn recruiter cold outreach
python3 automations/linkedin-outreach/main.py
```

### 5. Running Health Diagnostics
```bash
# Run comprehensive ecosystem verification
./health_check_wsl.sh
```

---

## 🛡️ Security & Privacy

- **Zero External LLM Calls**: All AI synthesis routes to local Ollama endpoints.
- **Strict Git Hygiene**: Session state files, browser storage states, SQLite WAL files, and credentials are protected under `.gitignore`.
- **Safe SMTP Delivery**: Rate-limited cold email dispatch to prevent inbox flagging.

---

## 📄 License
Private — Personal Automation and Career Acceleration Infrastructure.
