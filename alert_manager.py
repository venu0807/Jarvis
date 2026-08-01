import sys
import json
import os
import datetime

ALERT_FILE = "/home/venu/Proposals/Jarvis/logs/alerts.json"

def add_alert(job_name, error_msg):
    alerts = []
    if os.path.exists(ALERT_FILE):
        try:
            with open(ALERT_FILE, 'r') as f:
                alerts = json.load(f)
        except Exception:
            pass
    
    alerts.append({
        "job": job_name,
        "time": str(datetime.datetime.now()),
        "message": error_msg
    })
    
    with open(ALERT_FILE, 'w') as f:
        json.dump(alerts, f, indent=4)
    print(f"Logged alert for {job_name}")
    
    try:
        import urllib.request
        webhook_url = "http://localhost:5678/webhook/jarvis-alerts"
        payload = {
            "urgency": "high",
            "subject": f"Jarvis Alert: {job_name}",
            "summary": error_msg
        }
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=data, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"Failed to send webhook: {e}")

def clear_alerts():
    with open(ALERT_FILE, 'w') as f:
        json.dump([], f, indent=4)
    print("Cleared all alerts")

if __name__ == "__main__":
    if len(sys.argv) >= 2:
        if sys.argv[1] == "add" and len(sys.argv) >= 4:
            add_alert(sys.argv[2], sys.argv[3])
        elif sys.argv[1] == "clear":
            clear_alerts()
        else:
            print("Invalid command")
    else:
        print("Usage: python3 alert_manager.py add <job> <msg> | clear")
