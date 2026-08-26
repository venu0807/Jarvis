#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.expanduser("~/Proposals/Jarvis"))

# Test the ascii_safe function directly
def ascii_safe(s: str) -> str:
    return s.encode("ascii", "ignore").decode("ascii").strip()

title = "\U0001f6a8 Test Title"
safe_title = ascii_safe(title)
print(f"Original title: {repr(title)}")
print(f"Safe title: {repr(safe_title)}")

# Test with the actual alert manager
from automations.alert_manager import AlertManager
m = AlertManager()

# Check the config
print(f"Ntfy config: {m.config[\"channels\"][\"ntfy\"]}")

# Try to trace through _send_ntfy manually
config = m.config["channels"]["ntfy"]
topic = config.get("topic", "jarvis-alerts")
server = config.get("server", "https://ntfy.sh")
priority = config.get("priority", "default")
tags = config.get("tags", [])

priority_map = {"info": "default", "warning": "high", "critical": "urgent"}
priority = priority_map.get("info", priority)

alert_tags = tags + ["info", "jarvis"]
print(f"alert_tags: {alert_tags}")

safe_title = ascii_safe(title)
safe_priority = ascii_safe(priority)
safe_tags = ",".join(ascii_safe(t) for t in alert_tags)
import hashlib
alert_id = hashlib.md5(f"{title}Test message body".encode()).hexdigest()[:8]
deep_link = f"jarvis://alert/{alert_id}"
safe_actions = ascii_safe(f"view,{deep_link},View Details")

print(f"safe_title: {repr(safe_title)}")
print(f"safe_priority: {repr(safe_priority)}")
print(f"safe_tags: {repr(safe_tags)}")
print(f"safe_actions: {repr(safe_actions)}")

headers = {
    "Title": safe_title,
    "Priority": safe_priority,
    "Tags": safe_tags,
    "Actions": safe_actions,
}
print(f"headers: {headers}")

# Now test the actual request preparation
from requests.models import PreparedRequest
req = PreparedRequest()
req.prepare(
    method="POST",
    url=f"{server}/{topic}",
    data="Test message body".encode("utf-8"),
    headers={**headers, "Content-Type": "text/plain; charset=utf-8"},
)
print("Prepared request headers:")
for k, v in req.headers.items():
    print(f"  {k}: {repr(v)}")
