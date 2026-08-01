#!/bin/bash
echo "=============================================="
echo "Starting LinkedIn Outreach Bot Scheduled Run..."
echo "=============================================="

cd "$(dirname "$0")"

# Execute natively using python3
/home/venu/miniconda3/bin/python3 -u main.py
