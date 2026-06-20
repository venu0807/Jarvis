@echo off
echo ==============================================
echo Starting Job Automation Bot Scheduled Run...
echo ==============================================
cd /d "%~dp0"

@REM Try specific Python 3.9 first, fallback to system Python
if exist "D:\Programs\Python39\python.exe" (
    "D:\Programs\Python39\python.exe" -u run_pipeline.py
) else (
    python -u run_pipeline.py
)

pause
