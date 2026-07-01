#!/bin/bash
echo "=========================================="
echo "Starting All Jarvis Automations Sequence"
echo "=========================================="

echo ""
echo "[1/3] Running Pinterest Automation..."
cd ~/Proposals/Jarvis/automations/pinterest
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    python main.py --count 15
    deactivate
else
    python3 main.py --count 15
fi

echo ""
echo "[2/3] Running LinkedIn Outreach..."
cd ~/Proposals/Jarvis/automations/linkedin-outreach
./run_bot.sh

echo ""
echo "[3/3] Running Job Automation..."
cd ~/Proposals/Jarvis/automations/job-automation
./run_bot.sh

echo ""
echo "=========================================="
echo "All Automations Completed!"
echo "=========================================="
