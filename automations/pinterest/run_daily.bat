@echo off
REM ============================================
REM  Pinterest Affiliate Bot — Daily Run
REM ============================================
REM Runs automatically. Schedule via Windows Task Scheduler.
REM
REM Schedule it like this:
REM   schtasks /create /tn "PinterestBot" /tr "C:\Users\Venu\.jarvis\automations\pinterest\run_daily.bat" /sc daily /st 07:00
REM ============================================

REM Canonical project home (consolidated 2026-06-14). Was D:\Proposals\pinterest.
cd /d "d:\Proposals\Jarvis\automations\pinterest"

REM ── Activate virtual environment (if exists) ──
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
)

REM ── Set log file ──
set LOG_FILE=logs\%DATE:~-4,4%-%DATE:~-10,2%-%DATE:~-7,2%_run.log
if not exist logs mkdir logs

echo [%DATE% %TIME%] Starting Pinterest Bot... >> %LOG_FILE%

REM ── Step 1: Refill CSV with new products ──
echo [%DATE% %TIME%] Step 1/3: Refilling product database... >> %LOG_FILE%
python main.py refill >> %LOG_FILE% 2>&1

REM ── Step 2: Post pending pins ──
echo [%DATE% %TIME%] Step 2/3: Posting pins... >> %LOG_FILE%
python main.py run >> %LOG_FILE% 2>&1

REM ── Step 3: Show stats ──
echo [%DATE% %TIME%] Step 3/3: Summary... >> %LOG_FILE%
python main.py stats >> %LOG_FILE% 2>&1

echo [%DATE% %TIME%] Done! >> %LOG_FILE%
echo. >> %LOG_FILE%

REM ── Show latest stats in terminal ──
python main.py stats

pause
