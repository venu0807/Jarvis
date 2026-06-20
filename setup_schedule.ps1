$Action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument '-WindowStyle Hidden -File "D:\Proposals\Jarvis\run_all_automations.bat"'
$Trigger = New-ScheduledTaskTrigger -Daily -At 8:00AM
Register-ScheduledTask -TaskName 'Jarvis_Daily_Automations' -Action $Action -Trigger $Trigger -Description 'Runs Pinterest, LinkedIn, and Job automations sequentially' -Force
