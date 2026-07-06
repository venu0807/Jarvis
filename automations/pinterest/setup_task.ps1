$TaskName = "PinterestBot"
$Action = New-ScheduledTaskAction -Execute "wsl.exe" -Argument "-d Ubuntu -u venu bash -c '/home/venu/Proposals/Jarvis/automations/pinterest/run_bot_silent.sh'"
$Trigger = New-ScheduledTaskTrigger -Daily -At 9am
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable

# Try to register the task, running whether user is logged on or not
# To do this silently we need highest privileges and a system account or user account with stored password.
# Since we can't easily store the user's password in this script, we'll run it as the current user, but it will only run when logged in.
Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Runs the Pinterest Affiliate Bot daily" -Force

Write-Host "Task '$TaskName' has been created successfully."
Write-Host "It is scheduled to run daily at 9:00 AM."
Write-Host "You can change the schedule in the Windows Task Scheduler app."
