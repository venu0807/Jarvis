#!/bin/bash
cd /home/venu/Proposals/Jarvis/automations/pinterest
source venv/bin/activate
export USE_OBSCURA=0
# Run python main.py silently using a virtual framebuffer
xvfb-run -a python main.py run >> /home/venu/Proposals/Jarvis/automations/pinterest/logs/cron.log 2>&1
