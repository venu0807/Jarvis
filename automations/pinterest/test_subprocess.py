import subprocess
import sys
import os

# Test the exact command being run
temp_path = r'C:\Users\Venu\AppData\Local\Temp\test.html'
output_path = r'output\test.png'

safe_temp = temp_path.replace('\\', '\\\\')
safe_output = output_path.replace('\\', '\\\\')
script = f"from aesthetic_blender import _run_playwright_standalone; _run_playwright_standalone(r'{safe_temp}', r'{safe_output}')"
print(f'Script: {script}')
result = subprocess.run([sys.executable, '-c', script], capture_output=True, text=True)
print(f'Return code: {result.returncode}')
print(f'Stdout: {result.stdout}')
print(f'Stderr: {result.stderr}')