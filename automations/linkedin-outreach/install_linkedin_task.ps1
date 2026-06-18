$TaskName = "Jarvis_LinkedInOutreach_Daily"
$ScriptPath = "D:\Proposals\Jarvis\automations\linkedin-outreach\run_bot.bat"
$TriggerTime = "10:00"

if (-not (Test-Path $ScriptPath)) {
    Write-Host "❌ Script not found: $ScriptPath" -ForegroundColor Red
    exit 1
}

$Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c ""$ScriptPath""" -WorkingDirectory "D:\Proposals\Jarvis\automations\linkedin-outreach"
$Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Daily Jarvis LinkedIn Outreach" -Force

Write-Host "✅ Registered scheduled task: $TaskName to run daily at $TriggerTime" -ForegroundColor Green
Write-Host "You can verify in Task Scheduler or by running: schtasks /query /TN $TaskName"
