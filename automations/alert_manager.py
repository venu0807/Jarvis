"""alert_manager.py — Centralized alerting for JARVIS automations.

Supports:
- Email (SMTP)
- Webhook (generic HTTP)
- Rate limiting & deduplication
- Severity levels: info, warning, critical
"""

import os
import json
import smtplib
import requests
import logging
import hashlib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, config_path: str = None):
        # Handle WSL/Windows path differences - use env var with sensible defaults
        # Try multiple locations for the config file
        if config_path is None:
            config_path = os.getenv("ALERT_CONFIG_PATH")
        if config_path is None:
            # Try WSL native path first
            wsl_path = os.path.expanduser("~/.jarvis/.secrets/alert.env")
            # Try Windows junction path
            win_path = r"C:\Users\Venu\.jarvis\.secrets\alert.env"
            # Try WSL mount path
            mount_path = "/mnt/c/Users/Venu/.jarvis/.secrets/alert.env"
            
            for p in [wsl_path, win_path, mount_path]:
                if Path(p).exists():
                    config_path = p
                    break
            else:
                config_path = wsl_path  # default fallback
        
        self.config_path = config_path
        self.config = self._load_config()
        self.alert_history = self._load_history()
        self.dedup_window = timedelta(minutes=self.config.get("dedup_window_minutes", 60))

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from .env file"""
        config = {
            "rate_limit": {"max_per_hour": 10, "max_per_day": 50},
            "dedup_window_minutes": 60,
            "channels": {
                "email": {"enabled": False, "smtp_server": "", "smtp_port": 587,
                         "username": "", "password": "", "from_addr": "", "to_addrs": []},
                "webhook": {"enabled": False, "url": "", "headers": {}},
                "ntfy": {"enabled": False, "topic": "", "server": "https://ntfy.sh", "priority": "default", "tags": []}
            }
        }

        env_path = Path(self.config_path)
        if env_path.exists():
            with open(env_path) as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        key, value = line.split("=", 1)
                        config[key.lower()] = value.strip('"')

        # Parse nested configs
        if "email_smtp_server" in config:
            config["channels"]["email"]["enabled"] = True
            config["channels"]["email"]["smtp_server"] = config.pop("email_smtp_server")
            config["channels"]["email"]["smtp_port"] = int(config.pop("email_smtp_port", "587"))
            config["channels"]["email"]["username"] = config.pop("email_username", "")
            config["channels"]["email"]["password"] = config.pop("email_password", "")
            config["channels"]["email"]["from_addr"] = config.pop("email_from_addr", "")
            config["channels"]["email"]["to_addrs"] = config.pop("email_to_addrs", "").split(",")

        if "webhook_url" in config:
            config["channels"]["webhook"]["enabled"] = True
            config["channels"]["webhook"]["url"] = config.pop("webhook_url")

        return config

    def _load_history(self) -> List[Dict]:
        """Load alert history from file"""
        history_path = os.getenv("ALERT_HISTORY_PATH")
        if history_path is None:
            # Try multiple locations
            wsl_path = os.path.expanduser("~/.jarvis/.alerts_history.json")
            win_path = r"C:\Users\Venu\.jarvis\.alerts_history.json"
            mount_path = "/mnt/c/Users/Venu/.jarvis/.alerts_history.json"
            
            for p in [wsl_path, win_path, mount_path]:
                if Path(p).exists():
                    history_path = p
                    break
            else:
                history_path = wsl_path
        
        history_file = Path(history_path)
        if history_file.exists():
            try:
                with open(history_file) as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_history(self):
        """Save alert history to file"""
        history_path = os.getenv("ALERT_HISTORY_PATH", os.path.expanduser("~/.jarvis/.alerts_history.json"))
        history_file = Path(history_path)
        history_file.parent.mkdir(parents=True, exist_ok=True)
        # Keep only last 1000 alerts
        if len(self.alert_history) > 1000:
            self.alert_history = self.alert_history[-1000:]
        with open(history_file, 'w') as f:
            json.dump(self.alert_history, f, indent=2)

    def _is_rate_limited(self) -> bool:
        """Check if we're rate limited"""
        now = datetime.now()
        hour_ago = now - timedelta(hours=1)
        day_ago = now - timedelta(days=1)

        recent_hour = [a for a in self.alert_history
                      if datetime.fromisoformat(a["timestamp"]) > hour_ago]
        recent_day = [a for a in self.alert_history
                     if datetime.fromisoformat(a["timestamp"]) > day_ago]

        if len(recent_hour) >= self.config["rate_limit"]["max_per_hour"]:
            logger.warning(f"Rate limit exceeded: {len(recent_hour)} alerts in last hour")
            return True
        if len(recent_day) >= self.config["rate_limit"]["max_per_day"]:
            logger.warning(f"Daily rate limit exceeded: {len(recent_day)} alerts in last day")
            return True
        return False

    def _is_duplicate(self, alert_key: str) -> bool:
        """Check if alert is duplicate within dedup window"""
        cutoff = datetime.now() - self.dedup_window
        for alert in reversed(self.alert_history):
            if alert.get("key") == alert_key:
                if datetime.fromisoformat(alert["timestamp"]) > cutoff:
                    return True
                break  # Older alerts don't matter
        return False

    def send_alert(self, title: str, message: str, severity: str = "info",
                   alert_key: str = None, channels: List[str] = None) -> bool:
        """
        Send alert via configured channels

        Args:
            title: Alert title
            message: Alert message body
            severity: info, warning, critical
            alert_key: Unique key for deduplication (optional)
            channels: List of channel names to use (None = all enabled)
        """
        # Rate limiting
        if self._is_rate_limited():
            logger.error("Alert suppressed due to rate limiting")
            return False

        # Deduplication
        if alert_key:
            if self._is_duplicate(alert_key):
                logger.debug(f"Alert suppressed as duplicate: {alert_key}")
                return False

        # Determine channels to use
        if channels is None:
            channels = [name for name, config in self.config["channels"].items()
                       if config.get("enabled", False)]
        else:
            channels = [c for c in channels if self.config["channels"].get(c, {}).get("enabled", False)]

        if not channels:
            logger.warning("No enabled channels for alert")
            return False

        # Prepare alert record
        alert_record = {
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": message,
            "severity": severity,
            "key": alert_key or hashlib.md5(f"{title}{message}".encode()).hexdigest()[:8]
        }

        # Send via each channel
        success = False
        for channel in channels:
            try:
                if channel == "email":
                    if self._send_email(title, message, severity):
                        success = True
                elif channel == "webhook":
                    if self._send_webhook(title, message, severity):
                        success = True
                elif channel == "ntfy":
                    if self._send_ntfy(title, message, severity):
                        success = True
            except Exception as e:
                logger.error(f"Failed to send alert via {channel}: {e}")

        if success:
            self.alert_history.append(alert_record)
            self._save_history()
            logger.info(f"Alert sent: {title}")
            return True
        else:
            logger.error("Failed to send alert via any channel")
            return False

    def _send_email(self, title: str, message: str, severity: str) -> bool:
        """Send alert via email"""
        config = self.config["channels"]["email"]
        if not config.get("enabled"):
            return False

        msg = MIMEMultipart()
        msg["From"] = config["from_addr"]
        msg["To"] = ", ".join(config["to_addrs"])
        msg["Subject"] = f"[{severity.upper()}] JARVIS Alert: {title}"

        body = f"""JARVIS Automation Alert

Severity: {severity.upper()}
Title: {title}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Message:
{message}

---
This is an automated message from JARVIS Job Automation System.
"""
        msg.attach(MIMEText(body, "plain"))

        try:
            server = smtplib.SMTP(config["smtp_server"], config["smtp_port"])
            server.starttls()
            server.login(config["username"], config["password"])
            text = msg.as_string()
            server.sendmail(config["from_addr"], config["to_addrs"], text)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"Email alert failed: {e}")
            return False

    def _send_webhook(self, title: str, message: str, severity: str) -> bool:
        """Send alert via generic webhook"""
        config = self.config["channels"]["webhook"]
        if not config.get("enabled"):
            return False

        payload = {
            "timestamp": datetime.now().isoformat(),
            "title": title,
            "message": message,
            "severity": severity,
            "source": "JARVIS"
        }

        try:
            resp = requests.post(
                config["url"],
                json=payload,
                headers=config.get("headers", {}),
                timeout=10
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Webhook alert failed: {e}")
            return False

    def _send_ntfy(self, title: str, message: str, severity: str) -> bool:
        """Send alert via ntfy.sh"""
        config = self.config["channels"]["ntfy"]
        if not config.get("enabled"):
            return False
        
        topic = config.get("topic", "jarvis-alerts")
        server = config.get("server", "https://ntfy.sh")
        priority = config.get("priority", "default")
        tags = config.get("tags", [])
        
        # Set priority based on severity
        priority_map = {"info": "default", "warning": "high", "critical": "urgent"}
        priority = priority_map.get(severity, priority)
        
        # Build tags
        alert_tags = tags + [severity, "jarvis"]
        
        headers = {
            "Title": title,
            "Priority": priority,
            "Tags": ",".join(alert_tags),
        }
        
        # Add deep link action
        alert_id = hashlib.md5(f"{title}{message}".encode()).hexdigest()[:8]
        deep_link = f"jarvis://alert/{alert_id}"
        headers["Actions"] = f'view,{deep_link},View Details'
        
        try:
            resp = requests.post(
                f"{server}/{topic}",
                data=message,
                headers=headers,
                timeout=10
            )
            resp.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"ntfy.sh alert failed: {e}")
            return False


# Convenience functions
def send_alert(title: str, message: str, severity: str = "info",
               alert_key: str = None, channels: List[str] = None) -> bool:
    """Send alert using default alert manager"""
    manager = AlertManager()
    return manager.send_alert(title, message, severity, alert_key, channels)


def send_info(title: str, message: str, alert_key: str = None) -> bool:
    """Send info alert"""
    return send_alert(title, message, "info", alert_key)


def send_warning(title: str, message: str, alert_key: str = None) -> bool:
    """Send warning alert"""
    return send_alert(title, message, "warning", alert_key)


def send_critical(title: str, message: str, alert_key: str = None) -> bool:
    """Send critical alert"""
    return send_alert(title, message, "critical", alert_key)


def get_alert_manager():
    """Return a singleton AlertManager instance."""
    return AlertManager()


def alert_critical(title: str, message: str, alert_key: str = None, **kwargs) -> bool:
    """Send critical alert via the default manager."""
    return send_critical(title, message, alert_key)


def alert_warning(title: str, message: str, alert_key: str = None, **kwargs) -> bool:
    """Send warning alert via the default manager."""
    return send_warning(title, message, alert_key)


def alert_info(title: str, message: str, alert_key: str = None, **kwargs) -> bool:
    """Send info alert via the default manager."""
    return send_info(title, message, alert_key)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 3:
        print("Usage: python alert_manager.py <title> <message> [severity]")
        sys.exit(1)

    title = sys.argv[1]
    message = sys.argv[2]
    severity = sys.argv[3] if len(sys.argv) > 3 else "info"

    success = send_alert(title, message, severity)
    sys.exit(0 if success else 1)