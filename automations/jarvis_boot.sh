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

# 3. Systemd / Service Listeners
service jarvis-email-monitor start 2>/dev/null || true
service buzz-jarvis-interview-listener start 2>/dev/null || true

# 4. Start n8n Workflow Automation (runs as venu)
su - venu -c "nohup /usr/local/bin/n8n start > /dev/null 2>&1 &"

# 5. Start Streamlit Mission Control Dashboard (runs as venu)
su - venu -c "cd /home/venu/Proposals/Jarvis && nohup python3 -m streamlit run automations/dashboard/jarvis_ui.py --server.port 8501 --server.headless true > /tmp/streamlit.log 2>&1 &"

# 6. Run catch-up scheduler for any tasks missed during downtime
su - venu -c "python3 /home/venu/scripts/catchup_scheduler.py >> /home/venu/Proposals/Jarvis/logs/catchup.log 2>&1 &"

echo "Jarvis is fully online."
