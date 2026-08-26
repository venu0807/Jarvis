import requests
import hashlib
import re

title = '🚨 PostgreSQL Connection Failed'
message = 'This is a test of JARVIS PostgreSQL alert with emoji 🚨 in title'
severity = 'critical'

priority_map = {'info': 'default', 'warning': 'high', 'critical': 'urgent'}
priority = priority_map.get(severity, 'default')
tags = ['critical', 'jarvis']
alert_id = hashlib.md5(f'{title}{message}'.encode()).hexdigest()[:8]
deep_link = f'jarvis://alert/{alert_id}'

safe_title = title.encode('ascii', 'ignore').decode('ascii').strip()
if not safe_title:
    safe_title = JARVIS
