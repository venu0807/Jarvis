#!/bin/bash

# ==============================================================================
# JARVIS HEAVY SHUTDOWN SCRIPT
# Safely stops ONLY the heavy RAM/CPU consumers (Docker, Next.js)
# Leaves cron and email listeners running in the background!
# ==============================================================================

echo "🛑 Initiating Heavy Engine Shutdown Sequence..."

# 1. Stop PostgreSQL Database
echo "[1/2] Stopping Native PostgreSQL Database..."
service postgresql stop

# 2. Stop Next.js Dashboard, Streamlit & n8n
echo "[2/2] Stopping Dashboards and n8n Workflow Engine..."
pkill -f "next" 2>/dev/null || true
pkill -f "streamlit" 2>/dev/null || true
pkill -f "npm start" 2>/dev/null || true
pkill -f "n8n start" 2>/dev/null || true

echo "✅ Heavy services stopped. (Core brain & Email listeners are still running!)"
