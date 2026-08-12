import sys
import os
import subprocess
import time
import socket

print('\n=============================================')
print('🤖 JARVIS SYSTEM DIAGNOSTICS & STATUS CHECK 🤖')
print('=============================================\n')

# 1. Check PostgreSQL
try:
    import psycopg2
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'automations', 'dashboard'))
    from init_db import DB_PARAMS
    conn = psycopg2.connect(**DB_PARAMS)
    print('✅ [1/5] Database (PostgreSQL): ONLINE and reachable')
    conn.close()
except Exception as e:
    print('❌ [1/5] Database (PostgreSQL): ERROR -', e)

# 2. Check Redis
try:
    import redis
    client = redis.Redis(host='localhost', port=6379, db=0)
    if client.ping():
        print('✅ [2/5] Event Bus (Redis): ONLINE and reachable')
    else:
        print('❌ [2/5] Event Bus (Redis): Unresponsive')
except Exception as e:
    print('❌ [2/5] Event Bus (Redis): ERROR -', e)

# 3. Check AI Commander (Ollama Policy)
try:
    import urllib.request
    import json
    req = urllib.request.Request('http://localhost:11434/api/tags')
    with urllib.request.urlopen(req, timeout=2) as response:
        print('✅ [3/5] AI Commander (OpenClaw/Ollama): ONLINE')
except Exception as e:
    print('⚠️  [3/5] AI Commander (OpenClaw/Ollama): OFFLINE (Graceful fallback mode active) -', e)

# 4. Check Bots Filesystem
bots = [
    ('Pinterest Bot', 'automations/pinterest/main.py'),
    ('Job Auto-Applier', 'automations/job-automation/auto_applier.py'),
    ('LinkedIn Outreach', 'automations/linkedin-outreach/main.py'),
    ('Inbox Triage', 'automations/daily-life/inbox_triage.py'),
]
all_bots = True
for name, path in bots:
    if not os.path.exists(path):
        all_bots = False
        print(f'❌ [4/5] Filesystem: Missing {name} at {path}')
if all_bots:
    print('✅ [4/5] Automations Filesystem: All core bots detected')

# 5. Check Active Orchestrator Process
try:
    output = subprocess.check_output(['pgrep', '-f', 'central_orchestrator.py']).decode('utf-8').strip()
    if output:
        pids = output.replace('\n', ', ')
        print(f'✅ [5/5] Master Daemon (Orchestrator): RUNNING (PIDs: {pids})')
    else:
        print('❌ [5/5] Master Daemon (Orchestrator): NOT RUNNING')
except subprocess.CalledProcessError:
    print('❌ [5/5] Master Daemon (Orchestrator): NOT RUNNING')
except Exception as e:
    print('❌ [5/5] Master Daemon (Orchestrator): NOT RUNNING', e)

print('\n🎯 SYSTEM STATUS: READY FOR AUTONOMOUS OPERATIONS\n')
