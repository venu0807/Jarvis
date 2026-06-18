# JARVIS Automation Control - PowerShell version
# Usage:
#   .\jarvis_control.ps1 status
#   .\jarvis_control.ps1 start
#   .\jarvis_control.ps1 stop
#   .\jarvis_control.ps1 run <name>
#   .\jarvis_control.ps1 log <name>

param(
    [Parameter(Position=0)]
    [string]$Action = "menu",

    [Parameter(Position=1)]
    [string]$Name
)

$tasks = @(
    @{Name="PinterestBot_Morning";    Alias="pinterest-morning"; Schedule="08:00 AM daily"},
    @{Name="PinterestBot_Lunch";      Alias="pinterest-lunch";   Schedule="12:30 PM daily"},
    @{Name="PinterestBot_Evening";    Alias="pinterest-evening"; Schedule="08:00 PM daily"},
    @{Name="JobAutomation_Daily";     Alias="job-automation";    Schedule="09:00 AM daily"},
    @{Name="DailyReport_Morning";     Alias="daily-morning";     Schedule="09:00 AM daily"},
    @{Name="DailyReport_Evening";     Alias="daily-evening";     Schedule="06:00 PM daily"},
    @{Name="LinkedInBot_Daily";       Alias="linkedin";          Schedule="10:00 AM daily"},
    @{Name="InterviewEmailListener";  Alias="interview";         Schedule="at logon (hidden)"},
    @{Name="PromoteJarvisJunction";   Alias="junction";          Schedule="at logon"}
)

function Resolve-TaskName {
    param([string]$Alias)
    $t = $tasks | Where-Object { $_.Alias -eq $Alias -or $_.Name -eq $Alias } | Select-Object -First 1
    if ($t) { return $t.Name } else { return $null }
}

function Show-Menu {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "   JARVIS AUTOMATION CONTROL PANEL" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Yellow
    Write-Host "  status                         - Show all tasks and their state"
    Write-Host "  start                          - Enable all scheduled tasks"
    Write-Host "  stop                           - Disable all scheduled tasks"
    Write-Host "  run <name>                     - Run an automation NOW"
    Write-Host "  log <name>                     - Show recent log entries"
    Write-Host ""
}

if ($Action -eq "menu") {
    Show-Menu
    Write-Host "Examples:" -ForegroundColor Green
    Write-Host "  .\jarvis_control.ps1 status"
    Write-Host "  .\jarvis_control.ps1 stop"
    Write-Host "  .\jarvis_control.ps1 run pinterest-morning"
    Write-Host "  .\jarvis_control.ps1 log job-automation"
    Read-Host "Press Enter to exit"
    exit
}

if ($Action -eq "status") {
    Write-Host ""
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "   AUTOMATION STATUS" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan

    foreach ($t in $tasks) {
        $info = Get-ScheduledTask -TaskName $t.Name -ErrorAction SilentlyContinue
        if ($info) {
            $runStatus = (Get-ScheduledTaskInfo -TaskName $t.Name -ErrorAction SilentlyContinue)
            $state = if ($info.State -eq "Ready") { "[ON]" } else { "[OFF]" }
            $stateColor = if ($info.State -eq "Ready") { "Green" } else { "Red" }
            $nextRun = if ($runStatus.NextRunTime) { $runStatus.NextRunTime.ToString("yyyy-MM-dd HH:mm") } else { "N/A (trigger-based)" }

            Write-Host ""
            Write-Host "$($state) $($t.Alias)" -ForegroundColor $stateColor -NoNewline
            Write-Host "  →  $($t.Name)"
            Write-Host "    Schedule:  $($t.Schedule)"
            Write-Host "    Next run:  $nextRun"
            Write-Host "    Last run:  $(if($runStatus.LastRunTime){$runStatus.LastRunTime.ToString('yyyy-MM-dd HH:mm')}else{'never'})"
            Write-Host "    Result:    $(if($runStatus.LastTaskResult){$runStatus.LastTaskResult}else{'—'})"
        } else {
            Write-Host ""
            Write-Host "[---] $($t.Alias)  →  $($t.Name)" -ForegroundColor Yellow
            Write-Host "    (task not registered)"
        }
    }
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit
}

if ($Action -in @("start","enable","on")) {
    Write-Host "Enabling all automation tasks..." -ForegroundColor Green
    foreach ($t in $tasks) {
        try {
            Enable-ScheduledTask -TaskName $t.Name -ErrorAction Stop | Out-Null
            Write-Host "  [OK] $($t.Alias)" -ForegroundColor Green
        } catch {
            Write-Host "  [FAIL] $($t.Alias) — $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit
}

if ($Action -in @("stop","disable","off")) {
    Write-Host "Disabling all automation tasks (schedule paused)..." -ForegroundColor Yellow
    foreach ($t in $tasks) {
        try {
            Disable-ScheduledTask -TaskName $t.Name -ErrorAction Stop | Out-Null
            Write-Host "  [OK] $($t.Alias)" -ForegroundColor Yellow
        } catch {
            Write-Host "  [FAIL] $($t.Alias) — $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit
}

if ($Action -eq "run") {
    if (-not $Name) {
        Write-Host "Usage: .\jarvis_control.ps1 run <name>" -ForegroundColor Red
        Write-Host "Names: pinterest-morning, pinterest-lunch, pinterest-evening, job-automation,"
        Write-Host "       daily-morning, daily-evening, linkedin, interview, junction"
        Read-Host "Press Enter to exit"
        exit 1
    }
    $taskName = Resolve-TaskName -Alias $Name
    if (-not $taskName) {
        Write-Host "Unknown automation: $Name" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "Starting $Name (task: $taskName)..." -ForegroundColor Green
    try {
        Start-ScheduledTask -TaskName $taskName -ErrorAction Stop
        Write-Host "  [OK] Started." -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    }
    Read-Host "Press Enter to exit"
    exit
}

if ($Action -eq "log") {
    if (-not $Name) {
        Write-Host "Usage: .\jarvis_control.ps1 log <name>" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    $logMap = @{
        "pinterest-morning" = "D:\Proposals\Jarvis\automations\pinterest\logs\pinterest_bot_$(Get-Date -Format 'yyyyMMdd').log"
        "pinterest-lunch"   = "D:\Proposals\Jarvis\automations\pinterest\logs\pinterest_bot_$(Get-Date -Format 'yyyyMMdd').log"
        "pinterest-evening" = "D:\Proposals\Jarvis\automations\pinterest\logs\pinterest_bot_$(Get-Date -Format 'yyyyMMdd').log"
        "job-automation"    = "D:\Proposals\Jarvis\automations\job-automation\output\logs\job_pipeline.log"
        "daily-morning"     = "D:\Proposals\Jarvis\logs\daily_report.log"
        "daily-evening"     = "D:\Proposals\Jarvis\logs\daily_report.log"
        "linkedin"          = "D:\Proposals\Jarvis\automations\linkedin-outreach\sent_log.jsonl"
    }
    $logPath = $logMap[$Name]
    if (-not $logPath) {
        Write-Host "No log path mapped for $Name" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    if (-not (Test-Path $logPath)) {
        Write-Host "No log file at: $logPath" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "================================================================================" -ForegroundColor Cyan
    Write-Host "   RECENT LOG: $Name" -ForegroundColor Cyan
    Write-Host "   File: $logPath" -ForegroundColor Cyan
    Write-Host "================================================================================" -ForegroundColor Cyan
    Get-Content $logPath -Tail 25
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit
}

Show-Menu
