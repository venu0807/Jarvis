#!/bin/bash
# ============================================================
# Pinterest Affiliate Bot - Quick Run Commands
# ============================================================

PROJECT_DIR="$(dirname "$0")"

# Navigate to project dir to ensure venv works correctly
cd "$PROJECT_DIR"

if [ -f "venv/bin/activate" ]; then
    PYTHON_CMD="venv/bin/python"
else
    PYTHON_CMD="python3"
fi

RUNNER="scheduled_runner.py"

echo "Pinterest Affiliate Bot - Quick Commands"
echo "========================================"
echo ""
echo "1. Run once (20 pins)"
echo "2. Run once with trending refill"
echo "3. Run morning batch (20 pins)"
echo "4. Run lunch batch (15 pins)"
echo "5. Run evening batch (20 pins)"
echo "6. Run night batch (10 pins)"
echo "7. Weekly trending refill"
echo "8. Show stats"
echo "0. Exit"
echo ""

read -p "Enter choice [0-8]: " choice

case $choice in
    1)
        $PYTHON_CMD main.py --count 20
        ;;
    2)
        $PYTHON_CMD main.py refill-trending
        $PYTHON_CMD main.py --count 20
        ;;
    3)
        $PYTHON_CMD $RUNNER morning
        ;;
    4)
        $PYTHON_CMD $RUNNER lunch
        ;;
    5)
        $PYTHON_CMD $RUNNER evening
        ;;
    6)
        $PYTHON_CMD $RUNNER night
        ;;
    7)
        $PYTHON_CMD $RUNNER weekly-refill
        ;;
    8)
        $PYTHON_CMD main.py stats
        ;;
    0)
        exit 0
        ;;
    *)
        echo "Invalid choice"
        ;;
esac

echo ""
read -p "Press enter to continue..."
