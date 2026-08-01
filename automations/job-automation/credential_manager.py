"""
Secure Credential Manager for Jarvis
Uses python-dotenv for local dev, system keyring for production.
NEVER hardcodes or logs credentials.
"""
import os
import sys
from pathlib import Path
from typing import Optional, List
try:
    import keyring
    KEYRING_AVAILABLE = True
except ImportError:
    KEYRING_AVAILABLE = False

try:
    from dotenv import load_dotenv
    DOTENV_AVAILABLE = True
except ImportError:
    DOTENV_AVAILABLE = False


class CredentialManager:
    """Manages credentials securely - no plaintext in code or logs."""

    SERVICE_NAME = "jarvis-automation"

    # Required credential keys for different modules
    REQUIRED_JOB_AUTOMATION = [
        "NAUKRI_EMAIL", "NAUKRI_PASSWORD",
        "INTERNSHALA_EMAIL", "INTERNSHALA_PASSWORD",
        "LINKEDIN_EMAIL", "LINKEDIN_PASSWORD",
        "INDEED_EMAIL", "INDEED_PASSWORD",
        "FOUNDIT_EMAIL", "FOUNDIT_PASSWORD",
        "CUTSHORT_EMAIL", "CUTSHORT_PASSWORD",
        "FRESHERSWORLD_EMAIL", "FRESHERSWORLD_PASSWORD",
        "WELLFOUND_EMAIL", "WELLFOUND_PASSWORD",
    ]

    REQUIRED_NOTIFICATIONS = [
        "GMAIL_ADDRESS", "GMAIL_APP_PASS",
        "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID",
    ]

    REQUIRED_PERSONAL = [
        "USERNAME", "USER_FULL_NAME", "USER_EMAIL",
        "USER_PHONE", "USER_LOCATION", "USER_UNIVERSITY",
        "USER_UNDERGRAD_UNIVERSITY",
        "USER_GITHUB_URL", "USER_LINKEDIN_URL", "USER_PORTFOLIO_URL",
        "USER_PROJECT_1_NAME", "USER_PROJECT_1_ROLE", "USER_PROJECT_1_URL",
    ]

    OPTIONAL = [
        "USER_FULL_NAME_UPPER", "USER_SHORT_NAME",
        "DAILY_LIMIT", "HEADLESS", "OLLAMA_MODEL",
        "N8N_JOB_WEBHOOK_URL", "N8N_ALERT_WEBHOOK_URL",
        "PLAYWRIGHT_BROWSERS_PATH",
    ]

    def __init__(self):
        self._cache = {}
        self._loaded = False

    def _load_env_file(self, base_dir: Path):
        """Load .env file for local development only."""
        if not self._loaded and DOTENV_AVAILABLE:
            env_path = base_dir / ".env"
            if env_path.exists():
                load_dotenv(env_path)
            self._loaded = True

    def get(self, key: str, base_dir: Path = None, default: str = None) -> Optional[str]:
        """
        Get credential value. Priority: keyring > env var > .env file > default.
        Does NOT log the value.
        """
        if key in self._cache:
            return self._cache[key]

        # 1. Try keyring (most secure - for production)
        if KEYRING_AVAILABLE:
            try:
                value = keyring.get_password(self.SERVICE_NAME, key)
                if value:
                    self._cache[key] = value
                    return value
            except Exception:
                pass  # Fall through to env

        # 2. Try environment variable
        value = os.getenv(key)
        if value:
            self._cache[key] = value
            return value

        # 3. Try .env file (local dev only)
        if base_dir:
            self._load_env_file(base_dir)
            value = os.getenv(key)
            if value:
                self._cache[key] = value
                return value

        # 4. Return default
        return default

    def get_portal_credentials(self, portal: str, base_dir: Path = None) -> tuple:
        """Get email and password for a job portal."""
        email = self.get(f"{portal.upper()}_EMAIL", base_dir)
        password = self.get(f"{portal.upper()}_PASSWORD", base_dir)
        return email, password

    def get_all_portal_credentials(self, base_dir: Path = None) -> dict:
        """Get credentials for all 9 portals."""
        portals = [
            "NAUKRI", "INTERNSHALA", "LINKEDIN", "INDEED",
            "FOUNDIT", "CUTSHORT", "FRESHERSWORLD", "WELLFOUND",
        ]
        creds = {}
        for portal in portals:
            email, password = self.get_portal_credentials(portal, base_dir)
            if email and password:
                creds[portal.lower()] = {"email": email, "password": password}
        return creds

    def get_notification_credentials(self, base_dir: Path = None) -> dict:
        """Get notification service credentials."""
        return {
            "gmail_address": self.get("GMAIL_ADDRESS", base_dir),
            "gmail_app_pass": self.get("GMAIL_APP_PASS", base_dir),
            "telegram_bot_token": self.get("TELEGRAM_BOT_TOKEN", base_dir),
            "telegram_chat_id": self.get("TELEGRAM_CHAT_ID", base_dir),
        }

    def get_personal_details(self, base_dir: Path = None) -> dict:
        """Get personal details for resume/profile filling."""
        details = {}
        for key in self.REQUIRED_PERSONAL + self.OPTIONAL:
            value = self.get(key, base_dir)
            if value:
                details[key.lower()] = value
        return details

    def set_keyring(self, key: str, value: str) -> bool:
        """Store credential in system keyring (production use)."""
        if not KEYRING_AVAILABLE:
            return False
        try:
            keyring.set_password(self.SERVICE_NAME, key, value)
            self._cache[key] = value
            return True
        except Exception:
            return False

    def set_multiple_keyring(self, creds: dict) -> int:
        """Store multiple credentials in keyring."""
        count = 0
        for key, value in creds.items():
            if self.set_keyring(key, value):
                count += 1
        return count

    def validate_required(self, required_keys: List[str], base_dir: Path = None) -> tuple:
        """Check if all required credentials are available. Returns (valid, missing_list)."""
        missing = []
        for key in required_keys:
            if not self.get(key, base_dir):
                missing.append(key)
        return len(missing) == 0, missing


# Global instance
_credential_manager = None

def get_credential_manager() -> CredentialManager:
    """Get global credential manager instance."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager

def validate_credentials(required_keys: List[str], base_dir: Path = None) -> bool:
    """Validate required credentials are available. Logs warnings for missing."""
    manager = get_credential_manager()
    valid, missing = manager.validate_required(required_keys, base_dir)
    if not valid:
        import logging
        log = logging.getLogger("credential_manager")
        log.warning("Missing required credentials: %s", missing)
        log.warning("Set them via: keyring set jarvis-automation <KEY> <VALUE> or in .env file")
    return valid

# Export required lists for other modules
REQUIRED_JOB_AUTOMATION = CredentialManager.REQUIRED_JOB_AUTOMATION
REQUIRED_NOTIFICATIONS = CredentialManager.REQUIRED_NOTIFICATIONS
REQUIRED_PERSONAL = CredentialManager.REQUIRED_PERSONAL