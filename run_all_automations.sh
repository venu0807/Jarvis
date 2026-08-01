#!/bin/bash
echo "=========================================="
echo "Starting All Jarvis Automations Sequence"
echo "=========================================="

echo ""
echo "[1/4] Running Pinterest Automation..."
cd ~/Proposals/Jarvis/automations/pinterest
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    xvfb-run -a python main.py --count 15
    deactivate
else
    xvfb-run -a /home/venu/miniconda3/bin/python3 main.py --count 15
fi

echo ""
echo "[2/4] Running LinkedIn Outreach..."
cd ~/Proposals/Jarvis/automations/linkedin-outreach
./run_bot.sh

echo ""
echo "[3/4] Running Job Automation..."
cd ~/Proposals/Jarvis/automations/job-automation
./run_bot.sh

echo ""
echo "[4/4] Running B2B Lead Gen (Zero-Capital Agent)..."
cd ~/Proposals/Jarvis/automations/b2b-lead-gen
# Point the scraper to your free OmniRoute setup
export ANTHROPIC_BASE_URL="http://localhost:20128/v1"
export ANTHROPIC_API_KEY="sk-omniroute"
# This URL can be changed to scrape any directory (dentists, real estate, etc.)
xvfb-run -a /home/venu/miniconda3/bin/python3 lead_scraper.py "https://www.yellowpages.com/search?search_terms=dentist&geo_location_terms=San+Francisco%2C+CA"

echo ""
echo "=========================================="
echo "All Automations Completed!"
echo "=========================================="
