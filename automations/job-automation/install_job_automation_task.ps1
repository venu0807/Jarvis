$TaskName = "Jarvis_JobAutomation_Daily"
$PythonPaths = @(
    "D:\Programs\Python39\python.exe",
    "D:\Programs\Miniconda3\python.exe",
    (Get-Command python.exe -ErrorAction SilentlyContinue).Source
)

$ScriptPath = "D:\Proposals\Jarvis\automations\job-automation\run_pipeline.py"
$TriggerTime = "09:00"

# Pick first available Python
$PythonPath = $null
foreach ($p in $PythonPaths) {
    if ($p -and (Test-Path $p)) {
        $PythonPath = $p
        break
    }
}
if (-not $PythonPath) {
    Write-Host "❌ No Python interpreter found. Edit PythonPath in this script." -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $PythonPath" -ForegroundColor Cyan

$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument """$ScriptPath""" -WorkingDirectory "D:\Proposals\Jarvis\automations\job-automation"
$Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Daily Jarvis Job Automation Pipeline" -Force

Write-Host "✅ Registered scheduled task: $TaskName to run daily at $TriggerTime" -ForegroundColor Green
Write-Host "You can verify in Task Scheduler or by running: schtasks /query /TN $TaskName"
