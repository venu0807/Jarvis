import subprocess
cmd = [
    '/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe',
    '-WindowStyle',
    'Normal',
    '-Command',
    "Start-Process 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe' -ArgumentList '--remote-debugging-port=9222 --remote-allow-origins=* --user-data-dir=C:\\JarvisEdgeProfile'"
]
print("List format looks like:")
print(cmd)
