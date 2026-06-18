$TaskName = "Jarvis_InterviewPrepBot_Listener"
$ScriptPath = "D:\Proposals\Jarvis\automations\interview_scheduler_prep_bot\run_listener_hidden.vbs"

$Action = New-ScheduledTaskAction -Execute "wscript.exe" -Argument """$ScriptPath""" -WorkingDirectory "D:\Proposals\Jarvis\automations\interview_scheduler_prep_bot"
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -Hidden

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "Jarvis Interview Prep Bot Background Listener" -Force

Write-Host "✅ Registered scheduled task: $TaskName to run continuously on Startup"
Write-Host "You can verify in Task Scheduler or by running: schtasks /query /TN $TaskName"
