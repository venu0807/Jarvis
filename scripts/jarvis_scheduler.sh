#!/bin/bash
# jarvis_scheduler.sh - JARVIS Automation Scheduler Wrapper
# This script runs the various JARVIS automation tasks on schedule

set -e

JARVIS_HOME="/home/venu/Proposals/Jarvis"
LOG_FILE="$JARVIS_HOME/automations/jarvis_cron.log"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

log "=== JARVIS Scheduler Started ==="

# Load environment variables
if [ -f "$JARVIS_HOME/automations/job-automation/.env" ]; then
    export $(grep -v '^#' "$JARVIS_HOME/automations/job-automation/.env" | xargs)
fi

# Run alert triggers check
log "Running alert triggers check..."
cd "$JARVIS_HOME"
if python -m automations.alert_triggers 2>&1 | tee -a "$LOG_FILE"; then
    log "Alert triggers check completed"
else
    log "Alert triggers check failed with exit code $?"
fi

# Run job automation (if not running in container)
# Uncomment the following lines to run job automation directly via cron
# log "Running job automation..."
# cd "$JARVIS_HOME/automations/job-automation"
# if python run.py 2>&1 | tee -a "$LOG_FILE"; then
#     log "Job automation completed"
# else
#     log "Job automation failed with exit code $?"
# fi

log "=== JARVIS Scheduler Completed ==="