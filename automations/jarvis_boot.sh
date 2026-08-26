#!/bin/bash

# ==============================================================================
# JARVIS MASTER BOOT SCRIPT
# This script is called by StartJarvis.vbs on Windows startup.
# It runs as 'root' in WSL to start system services, then drops to 'venu' 
# for user-level applications.
# ==============================================================================

echo "Starting Jarvis Background Services..."

# 1. Start system services (runs as root)
service cron start
service postgresql start

# Give services a moment to spin up before starting Node/Python apps
sleep 3

# Start local LLM (Ollama)
su - venu -c "nohup /usr/local/bin/ollama serve > /dev/null 2>&1 &"

# 2. Start Next.js dashboard (runs as venu)
su - venu -c "pm2 resurrect"  # Restores jarvis-dashboard and any other PM2 processes

# 3. Start Email Listener (runs as venu)
# 3. Systemd Services (runs as root)
service jarvis-email-monitor start 2>/dev/null
service buzz-jarvis-interview-listener start 2>/dev/null

# 4. Start n8n Workflow Automation (runs as venu)
su - venu -c "nohup /usr/local/bin/n8n start > /dev/null 2>&1 &"

# 5. Start Streamlit Mission Control Dashboard (runs as venu)
su - venu -c "cd /home/venu/Proposals/Jarvis && nohup /home/venu/miniconda3/bin/streamlit run automations/dashboard/jarvis_ui.py --server.port 8501 --server.headless true > /tmp/streamlit.log 2>&1 &"

echo "Jarvis is fully online."
