import requests
import hashlib

topic = 'jarvis-alerts'
server = 'https://ntfy.sh'
title = 'Test Alert'
message = 'Test message'
severity = 'info'

priority_map = {'info': 'default', 'warning': 'high', 'critical': 'urgent'}
priority = priority_map.get(severity, 'default')
tags = ['info', 'jarvis']
alert_id = hashlib.md5(f'{title}{message}'.encode()).hexdigest()[:8]
deep_link = f'jarvis://alert/{alert_id}'

headers = {
    'Title': title,
    'Priority': priority,
    'Tags': ','.join(tags),
    'Actions': f'view,{deep_link},View Details',
}

print('Headers:', headers)
try:
    resp = requests.post(
        f'{server}/{topic}',
        data=message.encode('utf-8'),
        headers=headers,
        timeout=10
    )
    print('Status:', resp.status_code)
    print('Response:', resp.text)
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
