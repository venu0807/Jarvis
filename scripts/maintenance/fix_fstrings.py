import re

with open("alert_triggers.py", "r") as f:
    content = f.read()

# Add NL constant if not present
if "NL = " not in content:
    content = content.replace(
        "last_alerts = {}",
        "last_alerts = {}\n\n# Newline constant for f-strings (Python 3.12+ doesn't allow backslashes in f-string expressions)\nNL = \"\\n\""
    )

# Replace \n with {NL} inside f-strings
# Pattern: f"..." containing \n
# We'll do a more careful replacement

# Replace \n\n with {NL}{NL} in f-strings (double quotes)
content = re.sub(r'(f"[^"]*)\\\\n\\\\n', r'\1{NL}{NL}', content)
# Replace \n with {NL} in f-strings (double quotes)
content = re.sub(r'(f"[^"]*)\\\\n', r'\1{NL}', content)

# Also handle single quotes
content = re.sub(r"(f'[^']*)\\\\n\\\\n", r"\1{NL}{NL}", content)
content = re.sub(r"(f'[^']*)\\\\n", r"\1{NL}", content)

with open("alert_triggers.py", "w") as f:
    f.write(content)

print("Fixed")