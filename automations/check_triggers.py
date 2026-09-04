#!/usr/bin/env python3
import sys, os, logging
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from alert_manager import AlertManager, send_warning, send_critical, send_info

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_postgresql():
    try:
        import psycopg2
        host = os.getenv('JARVIS_DB_HOST', 'localhost')
        port = int(os.getenv('JARVIS_DB_PORT', 5432))
        user = os.getenv('JARVIS_DB_USER', 'postgres')
        password = os.getenv('JARVIS_DB_PASS', 'postgres')
        database = os.getenv('JARVIS_DB_NAME', 'jarvis')
        conn = psycopg2.connect(host=host, port=port, user=user, password=password, database=database, connect_timeout=5)
        conn.close()
        return True, 'PostgreSQL is online'
    except ImportError:
        return False, 'psycopg2 not installed'
    except Exception as e:
        return False, f'PostgreSQL connection failed: {e}'

def check_ollama():
    try:
        import urllib.request, json
        # Ollama runs on WSL host (localhost:11434), not host.docker.internal
        req = urllib.request.Request('http://localhost:11434/api/tags')
        with urllib.request.urlopen(req, timeout=5) as response:
            data = json.load(response)
            models = data.get('models', [])
            return True, f'Ollama online with {len(models)} models'
    except Exception as e:
        return False, f'Ollama connection failed: {e}'

def check_disk():
    try:
        import shutil
        total, used, free = shutil.disk_usage('/home/venu/Proposals/Jarvis')
        free_gb = free / (1024**3)
        if free_gb < 1:
            return False, f'Low disk space: {free_gb:.1f} GB free'
        elif free_gb < 5:
            return False, f'Disk space warning: {free_gb:.1f} GB free'
        return True, f'Disk space OK: {free_gb:.1f} GB free'
    except Exception as e:
        return False, f'Disk check failed: {e}'

def check_memory():
    try:
        with open('/proc/meminfo') as f:
            meminfo = {}
            for line in f:
                if ':' in line:
                    key, val = line.split(':', 1)
                    meminfo[key.strip()] = int(val.strip().split()[0])
        total_kb = meminfo.get('MemTotal', 0)
        available_kb = meminfo.get('MemAvailable', meminfo.get('MemFree', 0))
        if total_kb == 0:
            return False, 'Could not read memory info'
        available_gb = available_kb / (1024**2)
        pct = (available_kb / total_kb) * 100
        if pct < 10:
            return False, f'Critical memory: {available_gb:.1f} GB free ({pct:.0f}%)'
        elif pct < 20:
            return False, f'Low memory warning: {available_gb:.1f} GB free ({pct:.0f}%)'
        return True, f'Memory OK: {available_gb:.1f} GB free ({pct:.0f}%)'
    except Exception as e:
        return False, f'Memory check failed: {e}'

logger.info('Starting JARVIS alert triggers check')
checks = [
    ('PostgreSQL', check_postgresql, 'critical'),
    ('Ollama', check_ollama, 'critical'),
    ('Disk Space', check_disk, 'warning'),
    ('Memory', check_memory, 'warning'),
]
triggered = []
for name, check_func, severity in checks:
    try:
        ok, message = check_func()
        if not ok:
            logger.warning(f'Alert triggered: {name} - {message}')
            alert_key = f'health_{name.lower().replace(" ", "_")}'
            if severity == 'critical':
                send_critical(f'JARVIS: {name} Issue', message, alert_key)
            else:
                send_warning(f'JARVIS: {name} Warning', message, alert_key)
            triggered.append(name)
        else:
            logger.debug(f'Check passed: {name} - {message}')
    except Exception as e:
        logger.error(f'Error checking {name}: {e}')
        alert_key = f'health_{name.lower().replace(" ", "_")}_error'
        send_critical(f'JARVIS: {name} Check Error', f'Health check failed: {e}', alert_key)
        triggered.append(f'{name} (check error)')

if triggered:
    logger.info(f'Alert check complete. Triggered: {", ".join(triggered)}')
else:
    logger.info('Alert check complete. All systems healthy.')
sys.exit(0 if len(triggered) == 0 else 1)
