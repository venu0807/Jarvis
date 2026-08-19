#!/usr/bin/env python3
"""
secrets_rotation.py -- Automated secret rotation for JARVIS automations.
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime, timedelta
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.expanduser("~/Proposals/Jarvis"))

from automations.secrets_manager import SecretsManager
from automations.alert_manager import send_warning, send_info

logger = logging.getLogger(__name__)

# Configuration
SECRETS_DIR = Path(os.path.expanduser("~/.jarvis/.secrets"))
CONFIG_FILE = SECRETS_DIR / "rotation_config.json"
LOG_FILE = SECRETS_DIR / "rotation.log"
STATE_FILE = SECRETS_DIR / "rotation_state.json"

# Default rotation policy (in days)
DEFAULT_POLICY = {
    "naukri_password": 90,
    "internshala_password": 90,
    "indeed_password": 90,
    "foundit_password": 90,
    "linkedin_password": 60,
    "github_token": 90,
    "gmail_app_password": 60,
    "jarvis_db_password": 180,
    "email_smtp_password": 180,
    "telegram_bot_token": 365,  # Annual rotation
    "webhook_secret": 180,
    "api_key_openai": 90,
    "api_key_anthropic": 90,
}

def load_config() -> Dict[str, int]:
    """Load rotation policy from config file"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE) as f:
                config = json.load(f)
                # Merge with defaults, giving priority to config
                policy = DEFAULT_POLICY.copy()
                policy.update(config)
                return policy
        except Exception as e:
            logger.error(f"Failed to load rotation config: {e}")
            return DEFAULT_POLICY.copy()
    return DEFAULT_POLICY.copy()

def save_config(config: Dict[str, int]):
    """Save rotation policy to config file"""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save rotation config: {e}")

def load_state() -> Dict[str, str]:
    """Load rotation state (last rotation times)"""
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load rotation state: {e}")
    return {}

def save_state(state: Dict[str, str]):
    """Save rotation state"""
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save rotation state: {e}")

def setup_logging():
    """Setup logging configuration"""
    SECRETS_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE),
            logging.StreamHandler(sys.stdout)
        ]
    )

def should_rotate(secret_name: str, policy: Dict[str, int], state: Dict[str, str]) -> bool:
    """Check if a secret should be rotated based on policy and last rotation date"""
    if secret_name not in policy:
        return False
        
    rotation_days = policy[secret_name]
    if secret_name not in state:
        # Never rotated before - rotate it
        return True
        
    try:
        last_rotated = datetime.fromisoformat(state[secret_name])
        days_since = (datetime.now() - last_rotated).days
        return days_since >= rotation_days
    except Exception as e:
        logger.error(f"Error parsing last rotation date for {secret_name}: {e}")
        return True  # Rotate on error to be safe

def rotate_secret_if_needed(secret_name: str, policy: Dict[str, int], state: Dict[str, str]) -> bool:
    """Rotate a single secret if needed"""
    if not should_rotate(secret_name, policy, state):
        return False
        
    logger.info(f"Checking secret: {secret_name} (policy: {policy[secret_name]} days)")
    
    manager = SecretsManager("local")
    
    # Generate new secret based on type
    new_value = None
    if "password" in secret_name.lower():
        # Generate strong password
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
        new_value = ''.join(secrets.choice(alphabet) for _ in range(32))
    elif "token" in secret_name.lower() or "key" in secret_name.lower():
        # Generate API key style token
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        new_value = ''.join(secrets.choice(alphabet) for _ in range(32))
    elif "github" in secret_name.lower():
        # GitHub tokens have specific format (though we can't generate valid ones)
        # This is just for storage - real GitHub tokens need to be generated via GitHub UI
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        new_value = 'ghp_' + ''.join(secrets.choice(alphabet) for _ in range(36))
    else:
        # Default alphanumeric
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        new_value = ''.join(secrets.choice(alphabet) for _ in range(32))
    
    if new_value is None:
        logger.error(f"Could not generate new value for {secret_name}")
        return False
        
    # Store the new secret
    if manager.set_secret(secret_name, new_value, f"Automatically rotated by JARVIS on {datetime.now().isoformat()}"):
        # Update state
        state[secret_name] = datetime.now().isoformat()
        save_state(state)
        logger.info(f"Successfully rotated secret: {secret_name}")
        
        # Send notification
        send_info(
            title="���������🔐 Secret Rotated",
            message=f"The following secret has been automatically rotated:\n\n"
                    f"Secret: {secret_name}\n"
                    f"Rotation policy: {policy[secret_name]} days\n"
                    f"Next rotation due: {(datetime.now() + timedelta(days=policy[secret_name])).strftime('%Y-%m-%d')}\n\n"
                    f"������⚠������️  IMPORTANT: You must update this secret in the corresponding service/portal!\n\n"
                    f"Services that may need updating:\n"
                    f"- Job portal websites (for passwords)\n"
                    f"- GitHub (for tokens)\n"
                    f"- Email providers (for app passwords)\n"
                    f"- Database credentials\n"
                    f"- API services\n\n"
                    f"Check {SECRETS_DIR} for the new value if needed.",
            alert_key=f"secret_rotated_{secret_name}"
        )
        return True
    else:
        logger.error(f"Failed to store new value for secret: {secret_name}")
        return False

def main():
    parser = argparse.ArgumentParser(description="JARVIS Secret Rotation Tool")
    parser.add_argument("--check", action="store_true", 
                       help="Check which secrets need rotation (don't rotate)")
    parser.add_argument("--rotate", action="store_true",
                       help="Rotate secrets that are due for rotation")
    parser.add_argument("--list", action="store_true",
                       help="List all configured secrets and their policies")
    parser.add_argument("--force", nargs="+", metavar="SECRET",
                       help="Force rotation of specific secret(s)")
    parser.add_argument("--policy", nargs=2, metavar=("SECRET", "DAYS"),
                       action="append", help="Set rotation policy for a secret")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    setup_logging()
    
    # Load configuration and state
    policy = load_config()
    state = load_state()
    
    # Apply any policy overrides from command line
    if args.policy:
        for secret, days_str in args.policy:
            try:
                days = int(days_str)
                policy[secret] = days
                logger.info(f"Set policy for {secret}: {days} days")
            except ValueError:
                logger.error(f"Invalid days value for {secret}: {days_str}")
    
    # Save updated policy
    save_config(policy)
    
    if args.list:
        print("���������������������🔐 JARVIS Secret Rotation Configuration\n")
        print(f"{'Secret':<30} {'Policy (days)':<15} {'Last Rotated':<20} {'Status'}")
        print("-" * 80)
        
        for secret in sorted(policy.keys()):
            days = policy[secret]
            last_rotated = state.get(secret, "Never")
            if last_rotated != "Never":
                try:
                    last_date = datetime.fromisoformat(last_rotated)
                    last_rotated = last_date.strftime('%Y-%m-%d')
                    days_since = (datetime.now() - last_date).days
                    status = f"Due in {max(0, days - days_since)} days" if days_since < days else "OVERDUE"
                except:
                    status = "Invalid date"
            else:
                status = "NEVER ROTATED"
            print(f"{secret:<30} {days:<15} {last_rotated:<20} {status}")
        return 0
        
    if args.check:
        print("���������������������🔍 Checking for secrets due for rotation...\n")
        to_rotate = []
        for secret in policy:
            if should_rotate(secret, policy, state):
                to_rotate.append(secret)
                
        if to_rotate:
            print(f"The following {len(to_rotate)} secret(s) are due for rotation:")
            for secret in to_rotate:
                days = policy[secret]
                last_rotated = state.get(secret, "Never")
                if last_rotated != "Never":
                    try:
                        last_date = datetime.fromisoformat(last_rotated)
                        days_since = (datetime.now() - last_date).days
                        print(f"  • {secret} (last rotated {days_since} days ago, policy: {days} days)")
                    except:
                        print(f"  • {secret} (policy: {days} days)")
                else:
                    print(f"  • {secret} (never rotated, policy: {days} days)")
            print("\nRun with --rotate to rotate these secrets.")
        else:
            print("��������������✅ All secrets are within their rotation policy.")
        return 0
        
    if args.force:
        logger.info(f"Force rotating {len(args.force)} secret(s): {', '.join(args.force)}")
        rotated_count = 0
        for secret in args.force:
            if secret in policy:
                if rotate_secret_if_needed(secret, policy, state):
                    rotated_count += 1
            else:
                logger.warning(f"Secret '{secret}' not in policy. Adding it with default 90-day policy.")
                policy[secret] = 90
                if rotate_secret_if_needed(secret, policy, state):
                    rotated_count += 1
        save_config(policy)
        save_state(state)
        logger.info(f"Force rotation complete. Rotated {rotated_count}/{len(args.force)} secrets.")
        return 0 if rotated_count == len(args.force) else 1
        
    if args.rotate or (not args.check and not args.list and not args.force):
        # Default behavior: rotate due secrets
        logger.info("Starting secret rotation check...")
        rotated_count = 0
        checked_count = 0
        
        for secret in policy:
            checked_count += 1
            if rotate_secret_if_needed(secret, policy, state):
                rotated_count += 1
                
        logger.info(f"Rotation check complete. Checked: {checked_count}, Rotated: {rotated_count}")
        
        if rotated_count > 0:
            # Send summary alert
            send_info(
                title="���������🔐 Secret Rotation Summary",
                message=f"Automatic secret rotation completed.\n\n"
                        f"Secrets checked: {checked_count}\n"
                        f"Secrets rotated: {rotated_count}\n"
                        f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"The following secret(s) were rotated:\n" +
                        "\n".join([f"  • {s}" for s in state.keys() if datetime.fromisoformat(state[s]).date() == datetime.now().date()]) +
                        f"\n\n������⚠������️  Remember to update these secrets in their respective services/portals!\n"
                        f"Check {SECRETS_DIR} for current values if needed.",
                alert_key="secret_rotation_summary"
            )
        return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())