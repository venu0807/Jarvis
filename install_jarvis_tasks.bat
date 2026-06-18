@echo off
REM ============================================================
REM Install JARVIS automation scheduled tasks
REM Run as Administrator
REM ============================================================

set "JARVIS_HOME=D:\Proposals\Jarvis"
set "PYTHON39=D:\Programs\Python39\python.exe"

REM ── Job Automation ──
echo Installing JobAutomation_Daily (9:00 AM)...
schtasks /create /tn "JobAutomation_Daily" /tr "\"%PYTHON39%\" \"%JARVIS_HOME%\automations\job-automation\run_pipeline.py\"" /sc daily /st 09:00 /rl highest /f
if %errorlevel% equ 0 (echo   [OK]) else (echo   [FAILED])

REM ── Daily Report Morning ──
echo Installing DailyReport_Morning (9:00 AM)...
schtasks /create /tn "DailyReport_Morning" /tr "cmd /c \"%JARVIS_HOME%\automation-scripts\run_daily_report.bat --mode morning\"" /sc daily /st 09:00 /rl highest /f
if %errorlevel% equ 0 (echo   [OK]) else (echo   [FAILED])

REM ── Daily Report Evening ──
echo Installing DailyReport_Evening (6:00 PM)...
schtasks /create /tn "DailyReport_Evening" /tr "cmd /c \"%JARVIS_HOME%\automation-scripts\run_daily_report.bat --mode evening\"" /sc daily /st 18:00 /rl highest /f
if %errorlevel% equ 0 (echo   [OK]) else (echo   [FAILED])

REM ── LinkedIn Outreach ──
echo Installing LinkedInBot_Daily (10:00 AM)...
schtasks /create /tn "LinkedInBot_Daily" /tr "cmd /c \"%JARVIS_HOME%\automations\linkedin-outreach\run_bot.bat\"" /sc daily /st 10:00 /rl highest /f
if %errorlevel% equ 0 (echo   [OK]) else (echo   [FAILED])

REM ── Interview Email Listener ──
echo Installing InterviewEmailListener (at logon)...
schtasks /create /tn "InterviewEmailListener" /tr "wscript.exe \"%JARVIS_HOME%\automations\interview_scheduler_prep_bot\run_listener_hidden.vbs\"" /sc onlogon /rl highest /f
if %errorlevel% equ 0 (echo   [OK]) else (echo   [FAILED])

echo.
echo ============================================================
echo Installation complete.
echo ============================================================
echo.
echo Verify: schtasks /query /tn ^| findstr "Jarvis_\|JobAutomation\|DailyReport\|LinkedInBot\|Interview"
pause