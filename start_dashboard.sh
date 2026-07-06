#!/bin/bash
# =============================================================================
# JARVIS Dashboard Launcher
# =============================================================================

# Move to the project root
cd "$(dirname "$(realpath "$0")")"

echo "Starting Jarvis Memory Engine (Ollama) in the background..."
# Start ollama serve in the background and redirect output so it's silent
nohup ollama serve > /dev/null 2>&1 &
OLLAMA_PID=$!
echo "Ollama is booting up... (PID: $OLLAMA_PID)"

echo "Starting n8n Automation Engine in the background..."
# Source nvm so we use the WSL node environment instead of Windows Node
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

nohup npx n8n start > /dev/null 2>&1 &
N8N_PID=$!
echo "n8n is booting up... (PID: $N8N_PID)"

sleep 3

echo "Starting the Jarvis Command Center..."
# Activate the environment
source automations/pinterest/venv/bin/activate

# Run streamlit
streamlit run automations/dashboard/jarvis_ui.py --server.port 8501 --server.headless true

# When streamlit exits (e.g. user presses Ctrl+C), kill background processes to clean up
kill $OLLAMA_PID
kill $N8N_PID
echo "Jarvis safely shut down."
