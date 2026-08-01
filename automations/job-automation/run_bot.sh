#!/bin/bash
echo "=============================================="
echo "Starting Job Automation Bot Scheduled Run..."
echo "=============================================="

cd "$(dirname "$0")"

# Execute natively using miniconda python3
xvfb-run -a /home/venu/miniconda3/bin/python3 -u run_pipeline.py
