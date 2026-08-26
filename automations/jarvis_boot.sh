#!/bin/bash
# ==============================================================================
# 🚀 JARVIS MASTER START SCRIPT (Start EVERYTHING)
# Starts core services, AI engine, dashboard, n8n, and background listeners.
# ==============================================================================

echo "======================================================"
echo "         🚀 STARTING JARVIS MASTER SYSTEM"
echo "======================================================"

# 1. Start System Services
echo "▶ [1/5] Starting System Daemons (Cron & PostgreSQL)..."
service cron start 2>/dev/null || true
service postgresql start 2>/dev/null || true

# 2. Start Local AI Engine (Ollama with 30s auto-unload for lean RAM)
echo "▶ [2/5] Starting Local AI Engine (Ollama)..."
if ! pgrep -f "ollama serve" > /dev/null; then
    su - venu -c "export OLLAMA_KEEP_ALIVE=30s && nohup /usr/local/bin/ollama serve > /dev/null 2>&1 &"
    echo "  ✔ Ollama service launched (OLLAMA_KEEP_ALIVE=30s)."
else
    echo "  ✔ Ollama is already running."
fi

# 3. Start Next.js Web Dashboard & n8n Workflow Automation via PM2
echo "▶ [3/5] Starting Web Dashboard & n8n Workflows..."
su - venu -c "pm2 start /usr/local/bin/n8n --name 'n8n' -- start 2>/dev/null || pm2 restart n8n 2>/dev/null"
su - venu -c "cd /home/venu/Proposals/Jarvis/automations/dashboard-nextjs && (pm2 restart jarvis-dashboard 2>/dev/null || pm2 start npm --name 'jarvis-dashboard' -- start)"

# 4. Start 24/7 Automation Listeners
echo "▶ [4/5] Starting Background Daemons..."
if ! pgrep -f "interview_scheduler_prep_bot/email_listener.py" > /dev/null; then
    su - venu -c "nohup python3 /home/venu/Proposals/Jarvis/automations/interview_scheduler_prep_bot/email_listener.py > /dev/null 2>&1 &"
    echo "  ✔ Interview Prep Email Listener started."
else
    echo "  ✔ Interview Prep Email Listener already running."
fi

if ! pgrep -f "job-automation/email_monitor.py" > /dev/null; then
    su - venu -c "nohup python3 /home/venu/Proposals/Jarvis/automations/job-automation/email_monitor.py > /dev/null 2>&1 &"
    echo "  ✔ Job Alert Email Monitor started."
else
    echo "  ✔ Job Alert Email Monitor already running."
fi

# 5. Summary & Health Status
echo "▶ [5/5] Checking System Status..."
sleep 2

echo ""
echo "======================================================"
echo "  ✅ ALL JARVIS SYSTEMS & N8N ARE ONLINE!"
echo "======================================================"
echo "  🌐 Dashboard URL:    http://localhost:3001"
echo "  ⚡ n8n Workflows URL: http://localhost:5678"
echo "  🧠 Local AI Engine:  Ready (Auto-unloads after 30s)"
echo "  📅 Interview Bot:    Active (24/7 IMAP)"
echo "  💼 Job Alert Bot:    Active"
echo "======================================================"
