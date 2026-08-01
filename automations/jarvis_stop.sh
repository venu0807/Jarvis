#!/bin/bash

# ==============================================================================
# JARVIS MASTER SHUTDOWN SCRIPT
# Safely stops all background daemons and processes started by jarvis_boot.sh
# ==============================================================================

echo "🛑 Initiating Jarvis Shutdown Sequence..."

# 1. Stop Cron (halts all scheduled tasks)
echo "[1/4] Stopping Cron Scheduler..."
service cron stop

# 2. Stop PostgreSQL Database
echo "[2/4] Stopping Native Database..."
service postgresql stop

# 3. Stop Next.js Dashboard, Streamlit, Ollama, and n8n
echo "[3/4] Stopping Web Interfaces and AI Models..."
pkill -f "next" 2>/dev/null || true
pkill -f "streamlit" 2>/dev/null || true
pkill -f "ollama serve" 2>/dev/null || true
pkill -f "npm start" 2>/dev/null || true
pkill -f "n8n start" 2>/dev/null || true

# 4. Stop Email Listener
echo "[4/4] Stopping Background Email Listener..."
pkill -f "email_listener.py" 2>/dev/null || true

echo "✅ Jarvis has been completely shut down."
