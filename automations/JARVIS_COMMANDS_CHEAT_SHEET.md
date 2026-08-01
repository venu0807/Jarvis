# 🚀 Jarvis Complete Command Cheat Sheet

Here is the master list of every automation we have built and the exact terminal commands to run them. Save this file for your reference!

All commands assume you are running inside your Ubuntu WSL terminal.

---

### 1. The Master Job Hunter Pipeline
*Scrapes career portals, auto-applies to jobs, tailors pixel-perfect PDF resumes for manual applications, and emails you a summary.*
```bash
cd ~/Proposals/Jarvis/automations/job-automation
python3 run_pipeline.py
```

### 2. The AI Mock Interviewer
*Connects to your local database of applied jobs, picks one at random, and drops you into a brutal, interactive terminal interview with an AI hiring manager to test your skills.*
```bash
cd ~/Proposals/Jarvis/automations/job-automation
python3 mock_interviewer.py
```

### 3. The Inbox Monitor & Cheatsheet Generator
*Securely scans your Gmail for recruiter messages, summarizes them using local Ollama, generates PDF Interview Cheatsheets for high-urgency emails, and pushes live NTFY alerts to your phone.*
```bash
cd ~/Proposals/Jarvis/automations/inbox-monitor
python3 imap_scanner.py
```

### 4. The 24/7 Ghost Protocol (Full Autopilot)
*Installs silent background cron jobs so you never have to run the scripts above manually again. The Inbox Monitor will run every 15 minutes, and the Job Hunter will run daily at 9:00 AM.*
```bash
cd ~/Proposals/Jarvis/automations
./ghost_protocol.sh
```

> **⚠️ WSL Reboot Warning:** 
> Because you are on Windows, the Linux background scheduler (`cron`) does not start automatically when you turn your PC on. 
> Every time you restart your computer, you must run this single command to wake Jarvis up:
> ```bash
> sudo service cron start
> ```
