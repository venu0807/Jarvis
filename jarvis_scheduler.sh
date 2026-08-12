#!/bin/bash
PATH="$HOME/bin:$PATH"
# ==============================================================================
# JARVIS BASH STATE-TRACKER SCHEDULER
# Runs every 15 minutes via cron. Checks if jobs missed their target time 
# because the laptop was asleep, and catches up instantly.
# ==============================================================================

LOG_FILE="/home/venu/Proposals/Jarvis/logs/jarvis_scheduler.log"
mkdir -p /home/venu/Proposals/Jarvis/logs

# Windows toast when PowerShell is reachable from WSL; no-op otherwise
notify_win() {
    local PS="/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    if [ -x "$PS" ]; then
        "$PS" -ExecutionPolicy Bypass -File "\\wsl.localhost\Ubuntu\home\venu\Proposals\Jarvis\scripts\windows_toast.ps1" -Title "Jarvis OS" -Message "$1" >/dev/null 2>&1
    fi
}

echo "[$(date)] Scheduler poll triggered..." >> "$LOG_FILE"

# Wait for network connectivity (max 60 seconds) to prevent Wake-Up failures
max_wait=60
waited=0
while ! ping -c 1 -W 2 8.8.8.8 &> /dev/null; do
    if [ "$waited" -ge "$max_wait" ]; then
        echo "[$(date)] ⚠️ Network timeout after ${max_wait}s. Proceeding anyway..." >> "$LOG_FILE"
        break
    fi
    sleep 5
    waited=$((waited + 5))
done

# ------------------------------------------------------------------------------
# Daily Job Checker
# ------------------------------------------------------------------------------
check_daily() {
    JOB_ID=$1
    TARGET_HOUR=$2
    COMMAND=$3
    ALLOWED_DAYS=${4:-"1234567"} # 1=Mon, 7=Sun

    CURRENT_HOUR=$(date +%H)
    CURRENT_DATE=$(date +%Y-%m-%d)
    CURRENT_DOW=$(date +%u)

    # Check if today is an allowed day of the week
    if [[ ! "$ALLOWED_DAYS" == *"$CURRENT_DOW"* ]]; then
        return
    fi

    # Check if we have reached or passed the target hour
    # (10# forces base-10 to prevent octal errors like '08')
    if [ $((10#$CURRENT_HOUR)) -ge $((10#$TARGET_HOUR)) ]; then
        STATE_FILE="/home/venu/Proposals/Jarvis/logs/.state_$JOB_ID"
        LAST_RUN=$(cat "$STATE_FILE" 2>/dev/null || echo "never")
        
        if [ "$LAST_RUN" != "$CURRENT_DATE" ]; then
            echo "$CURRENT_DATE" > "$STATE_FILE"
            echo "[$(date)] 🚀 CATCH-UP TRIGGER: Running $JOB_ID..." >> "$LOG_FILE"
            ( 
                START_TIME=$(date +%s)
                if eval "$COMMAND"; then
                    END_TIME=$(date +%s)
                    DURATION=$((END_TIME - START_TIME))
                    python3 /home/venu/Proposals/Jarvis/telemetry.py "$JOB_ID" "SUCCESS" "$DURATION"
                    notify_win "✅ Automation Completed: $JOB_ID"
                else
                    END_TIME=$(date +%s)
                    DURATION=$((END_TIME - START_TIME))
                    python3 /home/venu/Proposals/Jarvis/telemetry.py "$JOB_ID" "FAILURE" "$DURATION"
                    python3 /home/venu/Proposals/Jarvis/alert_manager.py add "$JOB_ID" "Failed to execute successfully"
                fi 
            )
        fi
    fi
}

# ------------------------------------------------------------------------------
# Interval Job Checker
# ------------------------------------------------------------------------------
check_interval() {
    JOB_ID=$1
    INTERVAL_HOURS=$2
    COMMAND=$3

    CURRENT_TIMESTAMP=$(date +%s)
    STATE_FILE="/home/venu/Proposals/Jarvis/logs/.state_$JOB_ID"
    LAST_RUN=$(cat "$STATE_FILE" 2>/dev/null || echo "0")
    
    DIFF=$((CURRENT_TIMESTAMP - LAST_RUN))
    INTERVAL_SEC=$((INTERVAL_HOURS * 3600))
    
    if [ "$DIFF" -ge "$INTERVAL_SEC" ]; then
        echo "$CURRENT_TIMESTAMP" > "$STATE_FILE"
        echo "[$(date)] 🚀 INTERVAL TRIGGER: Running $JOB_ID..." >> "$LOG_FILE"
        ( 
            START_TIME=$(date +%s)
            if eval "$COMMAND"; then
                END_TIME=$(date +%s)
                DURATION=$((END_TIME - START_TIME))
                python3 /home/venu/Proposals/Jarvis/telemetry.py "$JOB_ID" "SUCCESS" "$DURATION"
                notify_win "✅ Automation Completed: $JOB_ID"
            else
                END_TIME=$(date +%s)
                DURATION=$((END_TIME - START_TIME))
                python3 /home/venu/Proposals/Jarvis/telemetry.py "$JOB_ID" "FAILURE" "$DURATION"
                python3 /home/venu/Proposals/Jarvis/alert_manager.py add "$JOB_ID" "Failed to execute successfully"
            fi 
        )
    fi
}

# ==============================================================================
# REGISTERED AUTOMATIONS (12 TOTAL)
# ==============================================================================

# 1. Micro-Learning (Daily 6:00 AM)
check_daily "micro_learning" "06" "cd /home/venu/Proposals/Jarvis/automations/micro-learning && /home/venu/miniconda3/bin/python3 generator.py >> /home/venu/Proposals/Jarvis/logs/learning_cron.log 2>&1"

# 2. Morning Report (Daily 9:00 AM)
check_daily "morning_report" "09" "cd /home/venu/Proposals/Jarvis && /home/venu/miniconda3/bin/python3 daily_report.py --mode morning >> /home/venu/Proposals/Jarvis/logs/cron.log 2>&1"

# 3. Job Automation Pipeline (Daily 9:15 AM)
check_daily "job_pipeline" "09" "cd /home/venu/Proposals/Jarvis/automations/job-automation && xvfb-run -a /home/venu/miniconda3/bin/python3 run_pipeline.py >> /home/venu/Proposals/Jarvis/automations/jarvis_cron.log 2>&1"

# 4. Evening Report (Daily 10:00 AM)
check_daily "evening_report" "10" "cd /home/venu/Proposals/Jarvis && /home/venu/miniconda3/bin/python3 daily_report.py --mode evening >> /home/venu/Proposals/Jarvis/logs/cron.log 2>&1"

# 5. Pinterest Auto-Publisher (Daily 10:30 AM)
check_daily "pinterest_publisher" "10" "cd /home/venu/Proposals/Jarvis/automations/pinterest && xvfb-run -a /home/venu/Proposals/Jarvis/automations/pinterest/venv/bin/python3 main.py --count 10 >> /home/venu/Proposals/Jarvis/logs/publisher_cron.log 2>&1"

# 6. LinkedIn Outreach (Daily 11:00 AM)
check_daily "linkedin_outreach" "11" "cd /home/venu/Proposals/Jarvis/automations/linkedin-outreach && ./run_bot.sh >> /home/venu/Proposals/Jarvis/logs/linkedin_cron.log 2>&1"

# 7. B2B Lead Gen (Daily 12:00 PM)
check_daily "b2b_lead_gen" "12" "cd /home/venu/Proposals/Jarvis/automations/b2b-lead-gen && xvfb-run -a /home/venu/miniconda3/bin/python3 lead_scraper.py >> /home/venu/Proposals/Jarvis/logs/b2b_cron.log 2>&1"

# 8. E-commerce AI Avatar (Daily 1:00 PM)
check_daily "ecommerce_bot" "13" "cd /home/venu/Proposals/Jarvis/automations/ecommerce && /home/venu/miniconda3/bin/python3 ai_avatar_workflow.py >> /home/venu/Proposals/Jarvis/logs/ecommerce_cron.log 2>&1"

# 9. Interview Scheduler & Prep (Daily 2:00 PM)
check_daily "interview_prep" "14" "cd /home/venu/Proposals/Jarvis/automations/interview_scheduler_prep_bot && /home/venu/miniconda3/bin/python3 email_listener.py >> /home/venu/Proposals/Jarvis/logs/interview_cron.log 2>&1"

# 10. Daily Life Tracker (Daily 8:00 PM)
check_daily "daily_life" "20" "cd /home/venu/Proposals/Jarvis/automations/daily-life && /home/venu/miniconda3/bin/python3 finance_tracker.py >> /home/venu/Proposals/Jarvis/logs/daily_life_cron.log 2>&1"

# 11. Ghost Networker (Every 2 Hours)
check_interval "ghost_networker" "2" "cd /home/venu/Proposals/Jarvis/automations/ghost-networker && /home/venu/miniconda3/bin/python3 monitor.py >> /home/venu/Proposals/Jarvis/logs/ghost_cron.log 2>&1"

# 12. Inbox Monitor (Every 1 Hour)
check_interval "inbox_monitor" "1" "cd /home/venu/Proposals/Jarvis/automations/inbox-monitor && /home/venu/miniconda3/bin/python3 imap_scanner.py >> /home/venu/Proposals/Jarvis/logs/inbox_cron.log 2>&1"

echo "[$(date)] Scheduler poll finished." >> "$LOG_FILE"
