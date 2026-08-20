import re

with open("/home/venu/Proposals/Jarvis/automations/alert_triggers.py", "r") as f:
    content = f.read()

# Fix the NL line - replace any malformed NL definition
content = re.sub(r'NL = ".*?"', 'NL = "\\n"', content, flags=re.DOTALL)

with open("/home/venu/Proposals/Jarvis/automations/alert_triggers.py", "w") as f:
    f.write(content)

print("Fixed")