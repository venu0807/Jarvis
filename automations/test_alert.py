#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.expanduser("~/Proposals/Jarvis"))

from automations.alert_manager import AlertManager

m = AlertManager()
result = m.send_alert('Test Title', 'Test message body', 'info', alert_key='test123')
print('Result:', result)
