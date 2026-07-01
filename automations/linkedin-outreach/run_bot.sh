#!/bin/bash
echo "=============================================="
echo "Starting LinkedIn Outreach Bot Scheduled Run..."
echo "=============================================="

cd "$(dirname "$0")"

# Execute natively using python3
python3 -u main.py
