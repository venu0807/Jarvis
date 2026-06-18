@echo off
REM ============================================================
REM Multi-Platform Bot — Task Scheduler Uninstaller (Run as Admin)
REM ============================================================

echo.
echo ============================================================
echo    Removing All Multi-Platform Bot Scheduled Tasks
echo ============================================================
echo.

net session >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Must be run as Administrator!
    pause
    exit /b 1
)

echo  Removing PinterestBot_Morning...
schtasks /delete /tn "PinterestBot_Morning" /f
echo  Removing PinterestBot_Lunch...
schtasks /delete /tn "PinterestBot_Lunch" /f
echo  Removing PinterestBot_Evening...
schtasks /delete /tn "PinterestBot_Evening" /f
echo  Removing CrossPostBot_Night...
schtasks /delete /tn "CrossPostBot_Night" /f
echo  Removing BioRefreshBot_Morning...
schtasks /delete /tn "BioRefreshBot_Morning" /f

echo.
echo  [DONE] All scheduled tasks removed.
pause
