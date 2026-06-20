@echo off
echo ==========================================
echo Starting All Jarvis Automations Sequence
echo ==========================================

echo.
echo [1/3] Running Pinterest Automation...
cd /d "D:\Proposals\Jarvis\automations\pinterest"
call venv\Scripts\python.exe -m main --count 15

echo.
echo [2/3] Running LinkedIn Outreach...
cd /d "D:\Proposals\Jarvis\automations\linkedin-outreach"
call run_bot.bat

echo.
echo [3/3] Running Job Automation...
cd /d "D:\Proposals\Jarvis\automations\job-automation"
call run_bot.bat

echo.
echo ==========================================
echo All Automations Completed!
echo ==========================================
