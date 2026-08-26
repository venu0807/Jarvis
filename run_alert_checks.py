import sys
sys.path.insert(0, '/home/venu/Proposals/Jarvis')
from automations.alert_triggers import run_checks

triggered = run_checks()
print(f'Triggered alerts: {triggered}')
sys.exit(0 if not triggered else 1)