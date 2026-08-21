with open('/home/venu/Proposals/Jarvis/automations/alert_triggers.py', 'r') as f:
    lines = f.readlines()

# Find the start of check_ollama_availability function
start_idx = None
for i, line in enumerate(lines):
    if 'def check_ollama_availability():' in line:
        start_idx = i
        break

# Find the start of check_portal_sessions function (end of check_ollama_availability)
end_idx = None
for i in range(start_idx + 1, len(lines)):
    if 'def check_portal_sessions():' in lines[i]:
        end_idx = i
        break

print(f"Function spans lines {start_idx+1} to {end_idx}")

# Replace the entire function
new_function = '''def check_ollama_availability():
    """Alert if Ollama is unavailable"""
    try:
        # Try to connect to Ollama API
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=5)

        if response.status_code != 200:
            if should_alert("ollama_unavailable"):
                send_warning(
                    title="\u26a0\ufe0f Ollama Unavailable",
                    message=(
                        "Ollama API is not responding correctly.{NL}{NL}"
                        f"Status code: {response.status_code}{NL}"
                        f"Response: {response.text[:200] if response.text else 'No response'}{NL}"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                        "Impact:{NL}"
                        "- AI job classification will fail{NL}"
                        "- Cover letter generation disabled{NL}"
                        "- Resume tailoring unavailable{NL}"
                        "- Interview preparation affected{NL}{NL}"
                        "Immediate actions:{NL}"
                        "1. Check Ollama service: systemctl --user status ollama{NL}"
                        "2. Restart Ollama: systemctl --user restart ollama{NL}"
                        "3. Verify it's running: curl http://localhost:11434/api/tags{NL}"
                        "4. Check logs: journalctl --user -u ollama{NL}"
                        "5. Pull a model to test: ollama pull llama3.2"
                    ),
                    alert_key="ollama_unavailable"
                )
                return True
        else:
            # Clear alert if it was previously firing
            if "ollama_unavailable" in last_alerts:
                del last_alerts["ollama_unavailable"]
    except Exception as e:
        if should_alert("ollama_unavailable"):
            send_warning(
                title="\u26a0\ufe0f Ollama Unavailable",
                message=(
                    "Cannot connect to Ollama API.{NL}{NL}"
                    f"Error: {str(e)}{NL}"
                    f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{NL}{NL}"
                    "This usually means Ollama is not running.{NL}{NL}"
                    "Immediate actions:{NL}"
                    "1. Start Ollama: systemctl --user start ollama{NL}"
                    "2. Enable at startup: systemctl --user enable ollama{NL}"
                    "3. Verify installation: which ollama{NL}"
                    "4. Pull a test model: ollama pull llama3.2{NL}"
                    "5. Check if port 11434 is listening: ss -tlnp | grep 11434"
                ),
                alert_key="ollama_unavailable"
            )
            return True
    return False

'''

new_lines = lines[:start_idx] + [new_function] + lines[end_idx:]

with open('/home/venu/Proposals/Jarvis/automations/alert_triggers.py', 'w') as f:
    f.writelines(new_lines)

print("Function replaced successfully")