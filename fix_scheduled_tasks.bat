@echo off
echo ==========================================
echo Fixing Jarvis Scheduled Tasks Paths...
echo ==========================================

REM Check for Admin privileges
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Please right-click this file and select "Run as administrator".
    pause
    exit /b 1
)

powershell -Command "$ErrorActionPreference = 'Stop'; function Fix-Task { param([string]$TaskName, [string]$Execute, [string]$Argument, [string]$WorkingDirectory); $task = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue; if ($task) { Write-Host 'Fixing' $TaskName'...'; $action = New-ScheduledTaskAction -Execute $Execute -Argument $Argument -WorkingDirectory $WorkingDirectory; Set-ScheduledTask -TaskName $TaskName -Action $action | Out-Null; Write-Host '  -> Fixed!' -ForegroundColor Green } }; Unregister-ScheduledTask -TaskName 'PinterestBot_Lunch' -Confirm:$false -ErrorAction SilentlyContinue; Unregister-ScheduledTask -TaskName 'PinterestBot_Evening' -Confirm:$false -ErrorAction SilentlyContinue; Write-Host 'Removed Lunch and Evening Pinterest tasks.'; $P_Exec = 'powershell.exe'; $P_Arg = '-WindowStyle Hidden -Command ""& ''D:\Proposals\Jarvis\automations\pinterest\venv\Scripts\python.exe'' -m main --count 15""'; $P_Dir = 'D:\Proposals\Jarvis\automations\pinterest'; Fix-Task 'PinterestBot_Morning' $P_Exec $P_Arg $P_Dir; $L_Exec = 'powershell.exe'; $L_Arg = '-WindowStyle Hidden -Command ""& ''D:\Proposals\Jarvis\automations\linkedin-outreach\run_bot.bat'' >> cron.log 2>&1""'; $L_Dir = 'D:\Proposals\Jarvis\automations\linkedin-outreach'; Fix-Task 'LinkedInBot_Daily' $L_Exec $L_Arg $L_Dir; $J_Exec = 'powershell.exe'; $J_Arg = '-WindowStyle Hidden -Command ""& ''D:\Programs\Python39\python.exe'' run_pipeline.py""'; $J_Dir = 'D:\Proposals\Jarvis\automations\job-automation'; Fix-Task 'JobAutomation_Daily' $J_Exec $J_Arg $J_Dir; Write-Host '`nAll scheduled tasks have been clustered to 8 AM - 10 AM and set to MINIMIZED/HIDDEN!' -ForegroundColor Cyan"

echo.
echo Fix complete. Press any key to exit.
pause
