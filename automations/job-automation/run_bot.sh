#!/bin/bash
echo "=============================================="
echo "Starting Job Automation Bot Scheduled Run..."
echo "=============================================="

cd "$(dirname "$0")"

# Execute natively using python3
python3 -u run_pipeline.py
