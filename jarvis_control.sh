#!/bin/bash
# =============================================================================
# JARVIS Automations Control Panel (Linux Edition)
# =============================================================================
# Easy way to run your automations natively in Linux.
#
# Usage:
#   ./jarvis_control.sh run <name>      Run a specific automation NOW
#   ./jarvis_control.sh log <name>      Show recent log entries
#
# Names:
#   pinterest / job-automation / linkedin / daily-report
# =============================================================================

if [ -z "$1" ]; then
    echo "================================================================================"
    echo "  JARVIS AUTOMATION CONTROL PANEL (LINUX)"
    echo "================================================================================"
    echo ""
    echo "Commands:"
    echo "  ./jarvis_control.sh run <name>      - Run a specific automation NOW"
    echo "  ./jarvis_control.sh log <name>      - Show recent log entries"
    echo ""
    echo "Automation names:"
    echo "  pinterest       - (Runs Pinterest bot interactive menu)"
    echo "  job-automation  - (Scrape + auto-apply)"
    echo "  linkedin        - (LinkedIn outreach)"
    echo "  daily-report    - (Runs the daily report script)"
    echo ""
    exit 0
fi

CMD=$1
NAME=$2

PROJECT_DIR="$(dirname "$(realpath "$0")")"

if [ "$CMD" = "run" ]; then
    if [ -z "$NAME" ]; then
        echo "Usage: ./jarvis_control.sh run <name>"
        echo "Names: pinterest, job-automation, linkedin, daily-report"
        exit 1
    fi
    
    echo "Running $NAME now..."
    case $NAME in
        "pinterest")
            cd "$PROJECT_DIR/automations/pinterest" && ./run_bot.sh
            ;;
        "job-automation")
            cd "$PROJECT_DIR/automations/job-automation" && ./run_bot.sh
            ;;
        "linkedin")
            cd "$PROJECT_DIR/automations/linkedin-outreach" && ./run_bot.sh
            ;;
        "daily-report")
            cd "$PROJECT_DIR" && python3 daily_report.py
            ;;
        *)
            echo "Unknown automation: $NAME"
            exit 1
            ;;
    esac
    exit 0
fi

if [ "$CMD" = "log" ]; then
    if [ -z "$NAME" ]; then
        echo "Usage: ./jarvis_control.sh log <name>"
        exit 1
    fi
    
    case $NAME in
        "pinterest")
            LOG_FILE=$(ls -t "$PROJECT_DIR/automations/pinterest/logs/"*.log 2>/dev/null | head -n 1)
            ;;
        "job-automation")
            LOG_FILE="$PROJECT_DIR/automations/job-automation/output/logs/job_pipeline.log"
            ;;
        "linkedin")
            LOG_FILE="$PROJECT_DIR/automations/linkedin-outreach/sent_log.jsonl"
            ;;
        "daily-report")
            LOG_FILE="$PROJECT_DIR/logs/daily_report.log"
            ;;
        *)
            echo "Unknown automation: $NAME"
            exit 1
            ;;
    esac
    
    if [ -z "$LOG_FILE" ] || [ ! -f "$LOG_FILE" ]; then
        echo "No log found for $NAME."
        exit 1
    fi
    
    echo "================================================================================"
    echo "  RECENT LOG: $NAME"
    echo "  File: $LOG_FILE"
    echo "================================================================================"
    tail -n 20 "$LOG_FILE"
    exit 0
fi

echo "Unknown command: $CMD"
echo "Try: ./jarvis_control.sh without arguments to see help."
exit 1
