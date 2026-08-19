"""
secrets_manager.py — Secrets rotation and management for JARVIS automations.

Supports:
- 1Password CLI (op) for secret storage and rotation
- HashiCorp Vault for enterprise secret management
- Local encrypted storage (age/GPG) as fallback
- Environment variable injection
- Audit logging
"""

import os
import json
import subprocess
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import hashlib
import base64
import secrets
import string

logger = logging.getLogger(__name__)


class SecretsManager:
    def __init__(self, backend: str = "local"):
        """
        Initialize secrets manager
        
        Args:
            backend: "local", "1password", or "vault"
        """
        self.backend = backend
        self.secrets_dir = Path(os.path.expanduser("~/.jarvis/.secrets"))
        self.secrets_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log = self.secrets_dir / "audit.log"
        
        # Backend-specific initialization
        if backend == "1password":
            self._check_1password()
        elif backend == "vault":
            self._check_vault()
        elif backend == "local":
            self._check_local()
        else:
            raise ValueError(f"Unsupported backend: {backend}")
            
    def _check_1password(self):
        """Verify 1Password CLI is available and logged in"""
        try:
            result = subprocess.run(["op", "account", "get"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                logger.warning("1Password CLI not logged in. Run 'op signin'")
        except FileNotFoundError:
            logger.error("1Password CLI not found. Install from https://1password.com/downloads/")
            
    def _check_vault(self):
        """Verify Vault CLI is available and logged in"""
        try:
            result = subprocess.run(["vault", "status"], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode != 0:
                logger.warning("Vault not logged in. Run 'vault login'")
        except FileNotFoundError:
            logger.error("Vault CLI not found. Install from https://developer.hashicorp.com/vault/downloads")
            
    def _check_local(self):
        """Verify local encryption tools are available"""
        self.age_available = self._check_age()
        self.gpg_available = self._check_gpg()
        
        if not self.age_available and not self.gpg_available:
            logger.warning("Neither age nor GPG available for local encryption")
            
    def _check_age(self) -> bool:
        """Check if age is available"""
        try:
            subprocess.run(["age", "--version"], 
                          capture_output=True, timeout=5)
            return True
        except:
            return False
            
    def _check_gpg(self) -> bool:
        """Check if GPG is available"""
        try:
            subprocess.run(["gpg", "--version"], 
                          capture_output=True, timeout=5)
            return True
        except:
            return False
            
    def _audit(self, action: str, secret_name: str, success: bool = True, details: str = ""):
        """Log audit entry"""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "secret": secret_name,
            "success": success,
            "details": details,
            "user": os.getenv("USER", "unknown")
        }
        
        try:
            with open(self.audit_log, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            logger.error(f"Failed to write audit log: {e}")
            
    def get_secret(self, name: str, version: str = None) -> Optional[str]:
        """
        Retrieve a secret from the configured backend
        
        Args:
            name: Secret name/identifier
            version: Version (for backends that support it)
            
        Returns:
            Secret value or None if not found
        """
        try:
            if self.backend == "1password":
                return self._get_from_1password(name, version)
            elif self.backend == "vault":
                return self._get_from_vault(name, version)
            else:  # local
                return self._get_from_local(name)
        except Exception as e:
            logger.error(f"Failed to get secret '{name}': {e}")
            self._audit("get", name, False, str(e))
            return None
            
    def _get_from_1password(self, name: str, version: str = None) -> Optional[str]:
        """Get secret from 1Password"""
        cmd = ["op", "item", "get", name, "--fields", "password", "--format", "json"]
        if version:
            cmd.extend(["--version", version])
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            self._audit("get", name, True)
            return data
        else:
            logger.error(f"1Password get failed: {result.stderr}")
            self._audit("get", name, False, result.stderr)
            return None
            
    def _get_from_vault(self, name: str, version: str = None) -> Optional[str]:
        """Get secret from HashiCorp Vault"""
        # Assume secrets are stored at secret/data/jarvis/<name>
        path = f"secret/data/jarvis/{name}"
        if version:
            path += f"?version={version}"
            
        cmd = ["vault", "kv", "get", "-format=json", path]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            data = json.loads(result.stdout)
            # Extract the actual secret value from Vault's response format
            secret_data = data.get("data", {}).get("data", {})
            # Return the password field or first value if no password field
            self._audit("get", name, True)
            return secret_data.get("password") or list(secret_data.values())[0] if secret_data else None
        else:
            logger.error(f"Vault get failed: {result.stderr}")
            self._audit("get", name, False, result.stderr)
            return None
            
    def _get_from_local(self, name: str) -> Optional[str]:
        """Get secret from local encrypted storage"""
        secret_file = self.secrets_dir / f"{name}.enc"
        if not secret_file.exists():
            # Try unencrypted fallback (for backward compatibility)
            secret_file = self.secrets_dir / name
            if not secret_file.exists():
                logger.error(f"Secret file not found: {name}")
                self._audit("get", name, False, "File not found")
                return None
                
        # If it's a .enc file, decrypt it
        if secret_file.suffix == ".enc":
            return self._decrypt_file(secret_file)
        else:
            # Read plaintext (backward compatibility)
            with open(secret_file, 'r') as f:
                secret = f.read().strip()
            self._audit("get", name, True)
            return secret
            
    def _decrypt_file(self, filepath: Path) -> Optional[str]:
        """Decrypt a file using age or GPG"""
        # Try age first
        if self.age_available:
            try:
                # Find age identity file
                age_identity = self.secrets_dir / "age.key"
                if age_identity.exists():
                    cmd = ["age", "--decrypt", "-i", str(age_identity), str(filepath)]
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        return result.stdout.strip()
            except Exception as e:
                logger.error(f"Age decryption failed: {e}")
                
        # Fallback to GPG
        if self.gpg_available:
            try:
                cmd = ["gpg", "--decrypt", str(filepath)]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    return result.stdout.strip()
            except Exception as e:
                logger.error(f"GPG decryption failed: {e}")
                
        logger.error(f"Failed to decrypt {filepath}: no working decryption method")
        self._audit("decrypt", filepath.name, False, "Decryption failed")
        return None
        
    def set_secret(self, name: str, value: str, version_comment: str = None) -> bool:
        """
        Store a secret in the configured backend
        
        Args:
            name: Secret name/identifier
            value: Secret value to store
            version_comment: Optional comment for version tracking
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.backend == "1password":
                return self._set_to_1password(name, value, version_comment)
            elif self.backend == "vault":
                return self._set_to_vault(name, value, version_comment)
            else:  # local
                return self._set_to_local(name, value)
        except Exception as e:
            logger.error(f"Failed to set secret '{name}': {e}")
            self._audit("set", name, False, str(e))
            return False
            
    def _set_to_1password(self, name: str, value: str, version_comment: str = None) -> bool:
        """Store secret in 1Password"""
        # Create or update item
        # This is simplified - in practice you'd need to handle item creation vs update
        item_data = {
            "title": f"jarvis-{name}",
            "category": "SECRETS",
            "fields": [
                {"id": "password", "purpose": "PASSWORD", "value": value}
            ]
        }
        if version_comment:
            item_data["notes"] = version_comment
            
        # Check if item exists first
        list_cmd = ["op", "item", "list", "--categories", "SECRETS", "--format", "json"]
        list_result = subprocess.run(list_cmd, capture_output=True, text=True, timeout=10)
        
        item_exists = False
        item_uuid = None
        if list_result.returncode == 0:
            items = json.loads(list_result.stdout)
            for item in items:
                if item.get("title") == f"jarvis-{name}":
                    item_exists = True
                    item_uuid = item.get("uuid")
                    break
                    
        if item_exists and item_uuid:
            # Update existing item
            cmd = ["op", "item", "edit", item_uuid] + \
                  [f"fields.password={value}"]
            if version_comment:
                cmd.append(f"notes={version_comment}")
        else:
            # Create new item
            cmd = ["op", "item", "create", 
                   f"title=jarvis-{name}",
                   f"category=SECRETS",
                   f"fields.password={value}"]
            if version_comment:
                cmd.append(f"notes={version_comment}")
                
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            self._audit("set", name, True, f"Backend: 1password, Version comment: {version_comment}")
            return True
        else:
            logger.error(f"1Password set failed: {result.stderr}")
            self._audit("set", name, False, result.stderr)
            return False
            
    def _set_to_vault(self, name: str, value: str, version_comment: str = None) -> bool:
        """Store secret in HashiCorp Vault"""
        # Store at secret/data/jarvis/<name>
        data = {"password": value}
        if version_comment:
            data["version_comment"] = version_comment
            data["updated_at"] = datetime.now().isoformat()
            
        cmd = ["vault", "kv", "put", f"secret/data/jarvis/{name}", 
               f"password={value}"]
        if version_comment:
            cmd.append(f"version_comment={version_comment}")
            
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            self._audit("set", name, True, f"Backend: vault, Version comment: {version_comment}")
            return True
        else:
            logger.error(f"Vault set failed: {result.stderr}")
            self._audit("set", name, False, result.stderr)
            return False
            
    def _set_to_local(self, name: str, value: str) -> bool:
        """Store secret in local encrypted storage"""
        secret_file = self.secrets_dir / f"{name}.enc"
        
        # Encrypt the value
        encrypted_data = self._encrypt_data(value)
        if encrypted_data is None:
            logger.error("Failed to encrypt secret data")
            self._audit("set", name, False, "Encryption failed")
            return False
            
        # Write encrypted data
        try:
            with open(secret_file, 'wb') as f:
                f.write(encrypted_data)
            self._audit("set", name, True, f"Backend: local, File: {secret_file.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to write secret file: {e}")
            self._audit("set", name, False, str(e))
            return False
            
    def _encrypt_data(self, data: str) -> Optional[bytes]:
        """Encrypt data using age or GPG"""
        # Try age first
        if self.age_available:
            try:
                # Find or create age identity
                age_identity = self.secrets_dir / "age.key"
                if not age_identity.exists():
                    # Generate new key pair
                    result = subprocess.run(["age-keygen"], 
                                          capture_output=True, text=True, timeout=10)
                    if result.returncode == 0:
                        # Extract the public key (for encryption) and save private key
                        lines = result.stdout.strip().split('\n')
                        if len(lines) >= 2:
                            # Age keygen outputs: public key line, then private key line
                            # Actually, age-keygen outputs the private key to stdout
                            # We need to extract the public key from it
                            private_key = lines[0]
                            # For now, we'll just use a simple approach - in prod you'd manage keys properly
                            with open(age_identity, 'w') as f:
                                f.write(private_key)
                            # Set restrictive permissions
                            age_identity.chmod(0o600)
                            
                # For encryption, we need the recipient (public key)
                # This is simplified - in practice you'd manage a key pair properly
                # For now, we'll use symmetric encryption with age if possible, or fallback to GPG
                # Actually, age doesn't do symmetric encryption by default
                # Let's use GPG for symmetric encryption which is simpler for this use case
                raise NotImplementedError("Age encryption needs proper key management")
            except Exception as e:
                logger.error(f"Age encryption setup failed: {e}")
                
        # Fallback to GPG symmetric encryption
        if self.gpg_available:
            try:
                # Use GPG symmetric encryption with a passphrase
                # In practice, you'd want to use a key file or agent
                # For simplicity, we'll use a passphrase from environment or generate one
                passphrase = os.getenv("JARVIS_SECRET_PASSPHRASE")
                if not passphrase:
                    # Generate a random passphrase and store it securely
                    # This is not ideal - in production you'd use a proper key management system
                    passphrase = base64.urlsafe_b64encode(os.urandom(32)).decode('ascii')
                    # Store it in a file with restrictive permissions
                    passphrase_file = self.secrets_dir / ".passphrase"
                    with open(passphrase_file, 'w') as f:
                        f.write(passphrase)
                    passphrase_file.chmod(0o600)
                    logger.warning("Generated temporary passphrase for secret encryption")
                    
                cmd = ["gpg", "--symmetric", "--cipher-algo", "AES256",
                       "--batch", "--yes", "--passphrase-fd", "0"]
                result = subprocess.run(cmd, input=passphrase + "\n" + data, 
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # GPG outputs binary data
                    return result.stdout.encode('latin-1') if isinstance(result.stdout, str) else result.stdout
                else:
                    logger.error(f"GPG encryption failed: {result.stderr}")
            except Exception as e:
                logger.error(f"GPG encryption failed: {e}")
                
        logger.error("No encryption method available")
        return None
        
    def rotate_secret(self, name: str, generator: callable = None) -> bool:
        """
        Rotate a secret by generating a new value and storing it
        
        Args:
            name: Secret name to rotate
            generator: Optional function to generate new secret value.
                      If None, uses default alphanumeric generator
            
        Returns:
            True if rotation successful, False otherwise
        """
        if generator is None:
            # Default generator: 32-character alphanumeric
            generator = lambda: ''.join(
                secrets.choice(string.ascii_letters + string.digits) 
                for _ in range(32)
            )
            
        try:
            # Generate new secret
            new_value = generator()
            
            # Store the new secret
            if self.set_secret(name, new_value, f"Rotated by JARVIS at {datetime.now().isoformat()}"):
                logger.info(f"Successfully rotated secret: {name}")
                self._audit("rotate", name, True)
                return True
            else:
                logger.error(f"Failed to store new value for secret: {name}")
                self._audit("rotate", name, False, "Failed to store new value")
                return False
        except Exception as e:
            logger.error(f"Secret rotation failed for '{name}': {e}")
            self._audit("rotate", name, False, str(e))
            return False
            
    def list_secrets(self) -> List[str]:
        """List available secrets"""
        try:
            if self.backend == "local":
                # List .enc files and plaintext files (for backward compatibility)
                enc_files = [f.stem for f in self.secrets_dir.glob("*.enc")]
                plain_files = [f.stem for f in self.secrets_dir.glob("*") 
                             if not f.name.startswith('.') and f.is_file() and f.suffix != '.enc']
                return list(set(enc_files + plain_files))
            elif self.backend == "1password":
                # List items in the vault
                result = subprocess.run(["op", "item", "list", "--categories", "SECRETS", "--format", "json"],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    items = json.loads(result.stdout)
                    return [item.get("title").replace("jarvis-", "") for item in items 
                           if item.get("title", "").startswith("jarvis-")]
                return []
            elif self.backend == "vault":
                # List secrets at the path
                result = subprocess.run(["vault", "kv", "list", "secret/data/jarvis/"],
                                      capture_output=True, text=True, timeout=10)
                if result.returncode == 0:
                    # Vault returns a weird format - lines starting with - 
                    lines = result.stdout.strip().split('\n')
                    secrets = []
                    for line in lines:
                        if line.startswith('- '):
                            secrets.append(line[2:].strip())
                    return secrets
                return []
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []
            

# Convenience functions for backward compatibility
def get_secret(name: str) -> Optional[str]:
    """Get secret using default local backend"""
    manager = SecretsManager("local")
    return manager.get_secret(name)


def set_secret(name: str, value: str) -> bool:
    """Set secret using default local backend"""
    manager = SecretsManager("local")
    return manager.set_secret(name, value)


def rotate_secret(name: str) -> bool:
    """Rotate secret using default local backend"""
    manager = SecretsManager("local")
    return manager.rotate_secret(name)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python secrets_manager.py <command> [args]")
        print("Commands: get <name>, set <name> <value>, rotate <name>, list")
        sys.exit(1)
        
    command = sys.argv[1]
    manager = SecretsManager("local")
    
    if command == "get":
        if len(sys.argv) < 3:
            print("Usage: python secrets_manager.py get <name>")
            sys.exit(1)
        name = sys.argv[2]
        value = manager.get_secret(name)
        if value is not None:
            print(value)
        else:
            print(f"Secret '{name}' not found", file=sys.stderr)
            sys.exit(1)
            
    elif command == "set":
        if len(sys.argv) < 4:
            print("Usage: python secrets_manager.py set <name> <value>")
            sys.exit(1)
        name = sys.argv[2]
        value = sys.argv[3]
        if manager.set_secret(name, value):
            print(f"Secret '{name}' set successfully")
        else:
            print(f"Failed to set secret '{name}'", file=sys.stderr)
            sys.exit(1)
            
    elif command == "rotate":
        if len(sys.argv) < 3:
            print("Usage: python secrets_manager.py rotate <name>")
            sys.exit(1)
        name = sys.argv[2]
        if manager.rotate_secret(name):
            print(f"Secret '{name}' rotated successfully")
        else:
            print(f"Failed to rotate secret '{name}'", file=sys.stderr)
            sys.exit(1)
            
    elif command == "list":
        secrets = manager.list_secrets()
        if secrets:
            for secret in sorted(secrets):
                print(secret)
        else:
            print("No secrets found")
            
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)