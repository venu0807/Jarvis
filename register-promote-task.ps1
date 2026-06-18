$action = New-ScheduledTaskAction `
    -Execute 'powershell.exe' `
    -Argument '-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "D:\Venu\jarvis\promote-junction.ps1"'

$trigger = New-ScheduledTaskTrigger -AtLogOn

try {
    Register-ScheduledTask -TaskName 'PromoteJarvisJunction' -Action $action -Trigger $trigger -Description 'Move C:\Users\Venu\.jarvis -> D:\Venu\jarvis as NTFS junction. Runs once at logon.' | Out-Null
    Write-Host 'Registered OK'
} catch {
    Write-Host ('Register error: ' + $_.Exception.Message)
}

# Verify
Write-Host ''
Write-Host '=== Task verification ==='
Get-ScheduledTask -TaskName 'PromoteJarvisJunction' -ErrorAction SilentlyContinue |
    Select-Object TaskName, State | Format-Table -AutoSize
