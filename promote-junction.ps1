# Promote-Drive-Junction.ps1
# ─────────────────────────────────────────────────────────────────
# Run ONCE at next user logon to convert:
#     C:\Users\Venu\.jarvis  (789 MB stub)
# into:
#     C:\Users\Venu\.jarvis  →  D:\Venu\jarvis   (NTFS junction)
#
# Why this matters: it ensures absolute paths in older scripts/cron jobs
# still resolve correctly. Without the junction, anything still hard-coding
# "C:\Users\Venu\.jarvis\..." would break — even though new logic always
# uses $JARVIS_HOME = D:\Venu\jarvis.
#
# Safe to delete this script after one successful run.
# Use: schtasks /Run /Tn "PromoteJarvisJunction"
# ─────────────────────────────────────────────────────────────────

$src = 'C:\Users\Venu\.jarvis'
$dst = 'D:\Venu\jarvis'
$logFile = 'D:\Venu\jarvis\logs\promote-junction.log'

function Write-Log($msg) {
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $msg"
    Add-Content -Path $logFile -Value $line -Encoding utf8
    Write-Host $line
}

if (Test-Path -LiteralPath 'C:\Users\Venu\.jarvis' -PathType Container) {
    $item = Get-Item -LiteralPath 'C:\Users\Venu\.jarvis' -Force
    if ($item.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
        Write-Log "Junction already exists at $src — no action needed."
        exit 0
    }
    try {
        # Move data into D:\Venu\jarvis (idempotent — we already copied, but re-sync any recent delta)
        if (Test-Path $dst) {
            Write-Log "Mirror $src → $dst via robocopy…"
            $robocopy = Start-Process -FilePath 'robocopy.exe' -ArgumentList @(
                $src, $dst, '/MIR', '/R:2', '/W:2', '/MT:8'
            ) -NoNewWindow -Wait -PassThru
            Write-Log "robocopy exit: $($robocopy.ExitCode)"
        }
        # Delete the stub at C: (Hermes will be locked if still active; if so, abort gracefully)
        Write-Log "Removing $src…"
        Remove-Item -LiteralPath $src -Recurse -Force -ErrorAction Stop
        Write-Log "$src removed."
    } catch {
        Write-Log "ERROR removing $src: $($_.Exception.Message)"
        exit 1
    }
}

if (-not (Test-Path $src)) {
    Write-Log "Creating junction: $src → $dst"
    cmd.exe /c mklink /J "$src" "$dst"
    Write-Log "Junction created."
}
Write-Log "Done."
