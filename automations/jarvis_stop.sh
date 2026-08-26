#!/bin/bash
# ==============================================================================
# 🛑 JARVIS MASTER SHUTDOWN SCRIPT (Stop EVERYTHING)
# Safely stops all dashboards, listeners, AI servers, daemons, and flushes RAM.
# ==============================================================================

echo "======================================================"
echo "         🛑 SHUTTING DOWN JARVIS SYSTEM"
echo "======================================================"

# 1. Stop Next.js Dashboard & PM2 Apps
echo "▶ [1/6] Stopping Next.js Dashboard & PM2 processes..."
su - venu -c "pm2 stop all 2>/dev/null" || true
pkill -f "next-server" 2>/dev/null || true
pkill -f "next" 2>/dev/null || true

# 2. Stop 24/7 Automation Listeners & Python Pipelines
echo "▶ [2/6] Stopping Background Python Automations..."
pkill -f "email_listener.py" 2>/dev/null || true
pkill -f "email_monitor.py" 2>/dev/null || true
pkill -f "run_pipeline.py" 2>/dev/null || true
pkill -f "auto_applier.py" 2>/dev/null || true
pkill -f "followup_bot.py" 2>/dev/null || true
pkill -f "cleanup_bot.py" 2>/dev/null || true
pkill -f "linkedin-outreach" 2>/dev/null || true
pkill -f "streamlit" 2>/dev/null || true
pkill -f "n8n" 2>/dev/null || true

# 3. Stop Local AI Engine (Ollama)
echo "▶ [3/6] Stopping Local AI Engine (Ollama)..."
pkill -f "ollama serve" 2>/dev/null || true

# 4. Stop System Daemons (Cron & PostgreSQL)
echo "▶ [4/6] Stopping System Services (Cron & PostgreSQL)..."
service cron stop 2>/dev/null || true
service postgresql stop 2>/dev/null || true

# 5. Stop Docker Containers & Daemon
echo "▶ [5/6] Stopping Docker & Containers..."
docker stop $(docker ps -q) 2>/dev/null || true
service docker stop 2>/dev/null || true

# 6. Flush and Reclaim All Linux RAM Cache
echo "▶ [6/6] Flushing Memory Caches (RAM Reclamation)..."
echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true

echo ""
echo "======================================================"
echo "  ✅ ALL JARVIS PROCESSES & DAEMONS ARE FULLY STOPPED!"
echo "======================================================"
echo "  💾 Current WSL Memory Status:"
free -h
echo "======================================================"
