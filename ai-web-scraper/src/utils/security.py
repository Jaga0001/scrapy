"""
Security utilities for data protection and encryption.

This module provides comprehensive security utilities including encryption,
secure storage, input validation, and data protection mechanisms.
"""

import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa, padding
import base64
import json

from src.utils.logger import get_logger

logger = get_logger(__name__)


class EncryptionManager:
    """
    Manages encryption and decryption operations for sensitive data.
    
    This class provides symmetric and asymmetric encryption capabilities
    for protecting sensitive configuration data and scraped content.
    """
    
    def __init__(self, master_key: Optional[str] = None):
        """
        Initialize encryption manager.
        
        Args:
            master_key: Master encryption key (will be generated if not provided)
        """
        self.master_key = master_key or self._get_or_create_master_key()
        self._fernet = None
        self._private_key = None
        self._public_key = None
    
    def _get_or_create_master_key(self) -> str:
        """
        Get or create master encryption key from environment.
        
        Returns:
            str: Master encryption key
        """
        key = os.getenv("ENCRYPTION_MASTER_KEY")
        if not key:
            # Generate new key and warn about persistence
            key = Fernet.generate_key().decode()
            logger.warning(
                "No ENCRYPTION_MASTER_KEY found in environment. "
                "Generated temporary key - data will not be recoverable after restart!"
            )
        return key
    
    def _get_fernet(self) -> Fernet:
        """
        Get or create Fernet cipher instance.
        
        Returns:
            Fernet: Fernet cipher instance
        """
        if self._fernet is None:
            try:
                # Use master key directly if it's already a valid Fernet key
                self._fernet = Fernet(self.master_key.encode())
            except Exception:
                # Derive key from master key using PBKDF2
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'scraper_salt_2024',  # Fixed salt for consistency
                    iterations=100000,
                )
                key = base64.urlsafe_b64encode(kdf.derive(self.master_key.encode()))
                self._fernet = Fernet(key)
        
        return self._fernet
    
    def encrypt_string(self, plaintext: str) -> str:
        """
        Encrypt a string using symmetric encryption.
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            str: Base64-encoded encrypted string
        """
        try:
            fernet = self._get_fernet()
            encrypted_bytes = fernet.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encrypt string: {e}")
            raise
    
    def decrypt_string(self, encrypted_text: str) -> str:
        """
        Decrypt a string using symmetric encryption.
        
        Args:
            encrypted_text: Base64-encoded encrypted string
            
        Returns:
            str: Decrypted plaintext string
        """
        try:
            fernet = self._get_fernet()
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_text.encode('utf-8'))
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to decrypt string: {e}")
            raise
    
    def encrypt_dict(self, data: Dict[str, Any]) -> str:
        """
        Encrypt a dictionary as JSON.
        
        Args:
            data: Dictionary to encrypt
            
        Returns:
            str: Base64-encoded encrypted JSON string
        """
        try:
            json_str = json.dumps(data, sort_keys=True)
            return self.encrypt_string(json_str)
        except Exception as e:
            logger.error(f"Failed to encrypt dictionary: {e}")
            raise
    
    def decrypt_dict(self, encrypted_text: str) -> Dict[str, Any]:
        """
        Decrypt a dictionary from encrypted JSON.
        
        Args:
            encrypted_text: Base64-encoded encrypted JSON string
            
        Returns:
            Dict[str, Any]: Decrypted dictionary
        """
        try:
            json_str = self.decrypt_string(encrypted_text)
            return json.loads(json_str)
        except Exception as e:
            logger.error(f"Failed to decrypt dictionary: {e}")
            raise
    
    def hash_data(self, data: str, salt: Optional[str] = None) -> str:
        """
        Create a secure hash of data.
        
        Args:
            data: Data to hash
            salt: Optional salt (will be generated if not provided)
            
        Returns:
            str: Hex-encoded hash with salt
        """
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Combine data and salt
        salted_data = f"{data}{salt}".encode('utf-8')
        
        # Create hash
        hash_obj = hashlib.sha256(salted_data)
        hash_hex = hash_obj.hexdigest()
        
        # Return hash with salt
        return f"{hash_hex}:{salt}"
    
    def verify_hash(self, data: str, hash_with_salt: str) -> bool:
        """
        Verify data against a hash.
        
        Args:
            data: Original data to verify
            hash_with_salt: Hash with salt from hash_data()
            
        Returns:
            bool: True if data matches hash
        """
        try:
            hash_hex, salt = hash_with_salt.split(':', 1)
            expected_hash = self.hash_data(data, salt)
            return hmac.compare_digest(expected_hash, hash_with_salt)
        except Exception as e:
            logger.error(f"Failed to verify hash: {e}")
            return False


class SecureConfigManager:
    """
    Manages secure storage and retrieval of configuration data.
    
    This class provides encrypted storage for sensitive configuration
    data such as API keys, database credentials, and other secrets.
    """
    
    def __init__(self, encryption_manager: EncryptionManager):
        """
        Initialize secure config manager.
        
        Args:
            encryption_manager: Encryption manager instance
        """
        self.encryption_manager = encryption_manager
        self._config_cache = {}
        self._config_file = os.getenv("SECURE_CONFIG_FILE", "config/secure_config.enc")
    
    def store_config(self, key: str, value: Any, encrypt: bool = True) -> None:
        """
        Store configuration value securely.
        
        Args:
            key: Configuration key
            value: Configuration value
            encrypt: Whether to encrypt the value
        """
        try:
            # Load existing config
            config = self._load_config_file()
            
            # Store value (encrypted if requested)
            if encrypt and isinstance(value, (str, dict)):
                if isinstance(value, str):
                    config[key] = {
                        "value": self.encryption_manager.encrypt_string(value),
                        "encrypted": True,
                        "type": "string"
                    }
                else:
                    config[key] = {
                        "value": self.encryption_manager.encrypt_dict(value),
                        "encrypted": True,
                        "type": "dict"
                    }
            else:
                config[key] = {
                    "value": value,
                    "encrypted": False,
                    "type": type(value).__name__
                }
            
            # Save config
            self._save_config_file(config)
            
            # Update cache
            self._config_cache[key] = value
            
            logger.info(f"Stored secure config: {key}")
            
        except Exception as e:
            logger.error(f"Failed to store secure config {key}: {e}")
            raise
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """
        Retrieve configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Any: Configuration value
        """
        try:
            # Check cache first
            if key in self._config_cache:
                return self._config_cache[key]
            
            # Load from file
            config = self._load_config_file()
            
            if key not in config:
                return default
            
            entry = config[key]
            
            # Decrypt if necessary
            if entry.get("encrypted", False):
                if entry["type"] == "string":
                    value = self.encryption_manager.decrypt_string(entry["value"])
                elif entry["type"] == "dict":
                    value = self.encryption_manager.decrypt_dict(entry["value"])
                else:
                    value = entry["value"]
            else:
                value = entry["value"]
            
            # Cache the decrypted value
            self._config_cache[key] = value
            
            return value
            
        except Exception as e:
            logger.error(f"Failed to get secure config {key}: {e}")
            return default
    
    def delete_config(self, key: str) -> bool:
        """
        Delete configuration value.
        
        Args:
            key: Configuration key to delete
            
        Returns:
            bool: True if deleted successfully
        """
        try:
            # Load existing config
            config = self._load_config_file()
            
            if key in config:
                del config[key]
                self._save_config_file(config)
                
                # Remove from cache
                if key in self._config_cache:
                    del self._config_cache[key]
                
                logger.info(f"Deleted secure config: {key}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to delete secure config {key}: {e}")
            return False
    
    def list_config_keys(self) -> List[str]:
        """
        List all configuration keys.
        
        Returns:
            List[str]: List of configuration keys
        """
        try:
            config = self._load_config_file()
            return list(config.keys())
        except Exception as e:
            logger.error(f"Failed to list config keys: {e}")
            return []
    
    def _load_config_file(self) -> Dict[str, Any]:
        """
        Load configuration from encrypted file.
        
        Returns:
            Dict[str, Any]: Configuration dictionary
        """
        try:
            if not os.path.exists(self._config_file):
                return {}
            
            with open(self._config_file, 'r') as f:
                encrypted_content = f.read()
            
            if not encrypted_content.strip():
                return {}
            
            # Decrypt the entire config file
            decrypted_content = self.encryption_manager.decrypt_string(encrypted_content)
            return json.loads(decrypted_content)
            
        except Exception as e:
            logger.error(f"Failed to load config file: {e}")
            return {}
    
    def _save_config_file(self, config: Dict[str, Any]) -> None:
        """
        Save configuration to encrypted file.
        
        Args:
            config: Configuration dictionary to save
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self._config_file), exist_ok=True)
            
            # Encrypt entire config
            json_content = json.dumps(config, indent=2)
            encrypted_content = self.encryption_manager.encrypt_string(json_content)
            
            # Write to file
            with open(self._config_file, 'w') as f:
                f.write(encrypted_content)
            
            # Set restrictive permissions
            os.chmod(self._config_file, 0o600)
            
        except Exception as e:
            logger.error(f"Failed to save config file: {e}")
            raise


class DataProtectionManager:
    """
    Manages data protection policies and encryption for scraped content.
    
    This class handles encryption of sensitive scraped data and implements
    data retention policies with automated cleanup.
    """
    
    def __init__(self, encryption_manager: EncryptionManager):
        """
        Initialize data protection manager.
        
        Args:
            encryption_manager: Encryption manager instance
        """
        self.encryption_manager = encryption_manager
        self.retention_policies = self._load_retention_policies()
    
    def encrypt_scraped_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Encrypt sensitive fields in scraped content.
        
        Args:
            content: Scraped content dictionary
            
        Returns:
            Dict[str, Any]: Content with sensitive fields encrypted
        """
        try:
            # Define sensitive field patterns
            sensitive_patterns = [
                'email', 'phone', 'address', 'ssn', 'credit_card',
                'password', 'token', 'key', 'secret', 'api_key'
            ]
            
            encrypted_content = content.copy()
            
            # Recursively encrypt sensitive fields
            self._encrypt_sensitive_fields(encrypted_content, sensitive_patterns)
            
            return encrypted_content
            
        except Exception as e:
            logger.error(f"Failed to encrypt scraped content: {e}")
            return content
    
    def decrypt_scraped_content(self, encrypted_content: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt sensitive fields in scraped content.
        
        Args:
            encrypted_content: Content with encrypted sensitive fields
            
        Returns:
            Dict[str, Any]: Content with sensitive fields decrypted
        """
        try:
            decrypted_content = encrypted_content.copy()
            
            # Recursively decrypt encrypted fields
            self._decrypt_encrypted_fields(decrypted_content)
            
            return decrypted_content
            
        except Exception as e:
            logger.error(f"Failed to decrypt scraped content: {e}")
            return encrypted_content
    
    def _encrypt_sensitive_fields(self, data: Any, sensitive_patterns: List[str]) -> None:
        """
        Recursively encrypt sensitive fields in data structure.
        
        Args:
            data: Data structure to process
            sensitive_patterns: List of sensitive field patterns
        """
        if isinstance(data, dict):
            for key, value in data.items():
                if isinstance(value, str) and self._is_sensitive_field(key, sensitive_patterns):
                    # Encrypt sensitive string values
                    data[key] = {
                        "_encrypted": True,
                        "_value": self.encryption_manager.encrypt_string(value)
                    }
                elif isinstance(value, (dict, list)):
                    # Recursively process nested structures
                    self._encrypt_sensitive_fields(value, sensitive_patterns)
        
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._encrypt_sensitive_fields(item, sensitive_patterns)
    
    def _decrypt_encrypted_fields(self, data: Any) -> None:
        """
        Recursively decrypt encrypted fields in data structure.
        
        Args:
            data: Data structure to process
        """
        if isinstance(data, dict):
            keys_to_update = []
            
            for key, value in data.items():
                if isinstance(value, dict) and value.get("_encrypted"):
                    # Decrypt encrypted field
                    try:
                        decrypted_value = self.encryption_manager.decrypt_string(value["_value"])
                        keys_to_update.append((key, decrypted_value))
                    except Exception as e:
                        logger.error(f"Failed to decrypt field {key}: {e}")
                elif isinstance(value, (dict, list)):
                    # Recursively process nested structures
                    self._decrypt_encrypted_fields(value)
            
            # Update decrypted fields
            for key, decrypted_value in keys_to_update:
                data[key] = decrypted_value
        
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, (dict, list)):
                    self._decrypt_encrypted_fields(item)
    
    def _is_sensitive_field(self, field_name: str, patterns: List[str]) -> bool:
        """
        Check if a field name matches sensitive patterns.
        
        Args:
            field_name: Field name to check
            patterns: List of sensitive patterns
            
        Returns:
            bool: True if field is considered sensitive
        """
        field_lower = field_name.lower()
        return any(pattern in field_lower for pattern in patterns)
    
    def _load_retention_policies(self) -> Dict[str, timedelta]:
        """
        Load data retention policies from configuration.
        
        Returns:
            Dict[str, timedelta]: Retention policies by data type
        """
        return {
            "scraped_data": timedelta(days=int(os.getenv("RETENTION_SCRAPED_DATA_DAYS", "365"))),
            "job_logs": timedelta(days=int(os.getenv("RETENTION_JOB_LOGS_DAYS", "90"))),
            "system_metrics": timedelta(days=int(os.getenv("RETENTION_SYSTEM_METRICS_DAYS", "30"))),
            "performance_metrics": timedelta(days=int(os.getenv("RETENTION_PERFORMANCE_METRICS_DAYS", "30"))),
            "health_checks": timedelta(days=int(os.getenv("RETENTION_HEALTH_CHECKS_DAYS", "7"))),
            "alerts": timedelta(days=int(os.getenv("RETENTION_ALERTS_DAYS", "180"))),
            "user_sessions": timedelta(days=int(os.getenv("RETENTION_USER_SESSIONS_DAYS", "30")))
        }
    
    def get_retention_policy(self, data_type: str) -> timedelta:
        """
        Get retention policy for a data type.
        
        Args:
            data_type: Type of data
            
        Returns:
            timedelta: Retention period
        """
        return self.retention_policies.get(data_type, timedelta(days=365))
    
    def should_retain_data(self, data_type: str, created_at: datetime) -> bool:
        """
        Check if data should be retained based on retention policy.
        
        Args:
            data_type: Type of data
            created_at: When the data was created
            
        Returns:
            bool: True if data should be retained
        """
        retention_period = self.get_retention_policy(data_type)
        cutoff_date = datetime.utcnow() - retention_period
        return created_at > cutoff_date


# Global instances
encryption_manager = EncryptionManager()
secure_config_manager = SecureConfigManager(encryption_manager)
data_protection_manager = DataProtectionManager(encryption_manager)