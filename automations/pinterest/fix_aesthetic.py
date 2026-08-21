with open('/home/venu/Proposals/Jarvis/automations/pinterest/aesthetic_blender.py', 'r') as f:
    content = f.read()

old = """        # Avoid multiprocessing fork deadlocks by using subprocess to spawn a fresh python interpreter
        # Properly escape paths for Windows in the subprocess command - use forward slashes and raw strings
        safe_temp = temp_path.replace('\\\\', '\\\\\\\\')
        safe_output = output_path.replace('\\\\', '\\\\\\\\')
        script = f"from aesthetic_blender import _run_playwright_standalone; _run_playwright_standalone(r'{safe_temp}', r'{safe_output}')"
        result = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)"""

new = """        # Avoid multiprocessing fork deadlocks by using subprocess to spawn a fresh python interpreter
        # Use forward slashes to avoid Windows path unicode escape issues (\\U in \\Users)
        safe_temp = temp_path.replace('\\\\', '/')
        safe_output = output_path.replace('\\\\', '/')
        script = f"from aesthetic_blender import _run_playwright_standalone; _run_playwright_standalone('{safe_temp}', '{safe_output}')"
        result = subprocess.run([sys.executable, "-c", script], check=True, capture_output=True, text=True)"""

if old in content:
    content = content.replace(old, new)
    with open('/home/venu/Proposals/Jarvis/automations/pinterest/aesthetic_blender.py', 'w') as f:
        f.write(content)
    print("File updated successfully")
else:
    print("Old text not found!")