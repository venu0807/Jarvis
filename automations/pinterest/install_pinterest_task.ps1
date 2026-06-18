$TaskConfigs = @(
    @{Name="Jarvis_Pinterest_Morning"; Trigger="07:00"; Args="morning"},
    @{Name="Jarvis_Pinterest_Lunch";   Trigger="12:00"; Args="lunch"},
    @{Name="Jarvis_Pinterest_Evening"; Trigger="19:00"; Args="evening"},
    @{Name="Jarvis_Pinterest_Night";   Trigger="23:00"; Args="night"}
)

$ScriptPath = "D:\Proposals\Jarvis\automations\pinterest\scheduled_runner.py"

# Try venv python first, then system python
$PythonCandidates = @(
    "D:\Proposals\Jarvis\automations\pinterest\venv\Scripts\python.exe",
    "D:\Programs\Python39\python.exe",
    (Get-Command python.exe -ErrorAction SilentlyContinue).Source
)
$PythonPath = $null
foreach ($p in $PythonCandidates) {
    if ($p -and (Test-Path $p)) {
        $PythonPath = $p
        break
    }
}

if (-not $PythonPath) {
    Write-Host "❌ Python not found. Edit PythonPath in this script." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path $ScriptPath)) {
    Write-Host "❌ Script not found: $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "Using Python: $PythonPath" -ForegroundColor Cyan

foreach ($cfg in $TaskConfigs) {
    $TaskName = $cfg.Name
    $TriggerTime = $cfg.Trigger
    $TaskArgs = $cfg.Args

    # Build argument string: script path followed by the task name
    $ArgString = '/c ""{0}" "{1}" {2} >> cron_{2}.log 2>&1"' -f $PythonPath, $ScriptPath, $TaskArgs

    $Action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument $ArgString -WorkingDirectory "D:\Proposals\Jarvis\automations\pinterest"
    $Trigger = New-ScheduledTaskTrigger -Daily -At $TriggerTime
    $Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden

    Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Daily Jarvis Pinterest Automation" -Force
    Write-Host "✅ Registered $TaskName to run at $TriggerTime" -ForegroundColor Green
}

Write-Host ""
Write-Host "All Pinterest tasks registered." -ForegroundColor Cyan
Write-Host "Daily schedule:"
Write-Host "  07:00 - Morning"
Write-Host "  12:00 - Lunch"
Write-Host "  19:00 - Evening"
Write-Host "  23:00 - Night"
