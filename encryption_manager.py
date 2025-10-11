#!/usr/bin/env python3
"""
Encryption Manager for Physiotherapy Clinic Assistant
Handles comprehensive data encryption including field-level and file encryption
with automatic key rotation and secure key management
"""

import os
import json
import base64
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Union
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.backends import default_backend
import logging


class EncryptionKey:
    """Represents an encryption key with metadata"""
    
    def __init__(self, key_id: str, key_data: bytes, created_at: datetime, 
                 expires_at: datetime, key_type: str = "AES-256"):
        self.key_id = key_id
        self.key_data = key_data
        self.created_at = created_at
        self.expires_at = expires_at
        self.key_type = key_type
        self.is_active = True
    
    def is_expired(self) -> bool:
        """Check if key is expired"""
        return datetime.now() > self.expires_at
    
    def days_until_expiry(self) -> int:
        """Get days until key expires"""
        return (self.expires_at - datetime.now()).days
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            'key_id': self.key_id,
            'key_data': base64.b64encode(self.key_data).decode(),
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'key_type': self.key_type,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EncryptionKey':
        """Create from dictionary"""
        key = cls(
            key_id=data['key_id'],
            key_data=base64.b64decode(data['key_data']),
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            key_type=data.get('key_type', 'AES-256')
        )
        key.is_active = data.get('is_active', True)
        return key


class EncryptionManager:
    """Comprehensive encryption manager for all data types"""
    
    def __init__(self, db_path: str = "data/clinic_data.db", 
                 key_storage_path: str = "data/encryption_keys.json"):
        self.db_path = db_path
        self.key_storage_path = Path(key_storage_path)
        self.key_rotation_days = 180  # 180 days as requested
        self.logger = logging.getLogger(__name__)
        
        # Ensure key storage directory exists
        self.key_storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Load or create encryption keys
        self.keys: Dict[str, EncryptionKey] = {}
        self.current_key_id: Optional[str] = None
        self.master_key: Optional[bytes] = None
        
        self._load_keys()
        self._check_key_rotation()
    
    def _load_keys(self) -> None:
        """Load encryption keys from storage"""
        try:
            if self.key_storage_path.exists():
                with open(self.key_storage_path, 'r') as f:
                    key_data = json.load(f)
                
                for key_id, key_info in key_data.get('keys', {}).items():
                    self.keys[key_id] = EncryptionKey.from_dict(key_info)
                
                self.current_key_id = key_data.get('current_key_id')
                
                # Load master key if available
                if 'master_key' in key_data:
                    self.master_key = base64.b64decode(key_data['master_key'])
            
            # If no keys exist, create initial key
            if not self.keys:
                self._create_initial_key()
                
        except Exception as e:
            self.logger.error(f"Failed to load encryption keys: {e}")
            self._create_initial_key()
    
    def _save_keys(self) -> None:
        """Save encryption keys to storage"""
        try:
            key_data = {
                'keys': {key_id: key.to_dict() for key_id, key in self.keys.items()},
                'current_key_id': self.current_key_id,
                'master_key': base64.b64encode(self.master_key).decode() if self.master_key else None,
                'last_updated': datetime.now().isoformat()
            }
            
            # Create temporary file first, then rename for atomic operation
            temp_path = self.key_storage_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(key_data, f, indent=2)
            
            temp_path.replace(self.key_storage_path)
            
            # Set restrictive permissions
            os.chmod(self.key_storage_path, 0o600)
            
        except Exception as e:
            self.logger.error(f"Failed to save encryption keys: {e}")
            raise
    
    def _create_initial_key(self) -> None:
        """Create initial encryption key"""
        key_id = f"key_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # Generate a proper 32-byte key for AES-256
        key_data = secrets.token_bytes(32)
        created_at = datetime.now()
        expires_at = created_at + timedelta(days=self.key_rotation_days)
        
        self.keys[key_id] = EncryptionKey(key_id, key_data, created_at, expires_at)
        self.current_key_id = key_id
        
        # Generate master key for key derivation
        self.master_key = secrets.token_bytes(32)
        
        self._save_keys()
        self.logger.info(f"Created initial encryption key: {key_id}")
    
    def _check_key_rotation(self) -> None:
        """Check if key rotation is needed"""
        if not self.current_key_id or self.current_key_id not in self.keys:
            return
        
        current_key = self.keys[self.current_key_id]
        
        # Rotate if key expires within 30 days
        if current_key.days_until_expiry() <= 30:
            self._rotate_key()
    
    def _rotate_key(self) -> None:
        """Create new encryption key and mark old one as inactive"""
        try:
            # Create new key
            new_key_id = f"key_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            new_key_data = secrets.token_bytes(32)  # 32 bytes for AES-256
            created_at = datetime.now()
            expires_at = created_at + timedelta(days=self.key_rotation_days)
            
            new_key = EncryptionKey(new_key_id, new_key_data, created_at, expires_at)
            self.keys[new_key_id] = new_key
            
            # Mark old key as inactive
            if self.current_key_id:
                self.keys[self.current_key_id].is_active = False
            
            self.current_key_id = new_key_id
            self._save_keys()
            
            self.logger.info(f"Rotated encryption key: {new_key_id}")
            
            # TODO: Implement data re-encryption with new key
            # This would be a background process to re-encrypt existing data
            
        except Exception as e:
            self.logger.error(f"Failed to rotate encryption key: {e}")
            raise
    
    def get_current_key(self) -> EncryptionKey:
        """Get the current active encryption key"""
        if not self.current_key_id or self.current_key_id not in self.keys:
            raise Exception("No active encryption key available")
        
        key = self.keys[self.current_key_id]
        if not key.is_active or key.is_expired():
            raise Exception("Current encryption key is not active or expired")
        
        return key
    
    def derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return kdf.derive(password.encode())
    
    # Field-level encryption methods (AES-256-GCM)
    
    def encrypt_field(self, data: str, key_id: Optional[str] = None) -> str:
        """Encrypt a field using AES-256-GCM"""
        if not data:
            return data
        
        try:
            key = self.get_current_key() if not key_id else self.keys[key_id]
            
            # Generate random nonce
            nonce = secrets.token_bytes(12)  # 96 bits for GCM
            
            # Create cipher
            cipher = AESGCM(key.key_data)
            
            # Encrypt data
            encrypted_data = cipher.encrypt(nonce, data.encode('utf-8'), None)
            
            # Combine nonce + encrypted data + key_id
            combined = nonce + encrypted_data
            if key_id:
                combined += key_id.encode('utf-8')
            
            # Return base64 encoded result
            return base64.b64encode(combined).decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt field: {e}")
            raise
    
    def decrypt_field(self, encrypted_data: str) -> str:
        """Decrypt a field using AES-256-GCM"""
        if not encrypted_data:
            return encrypted_data
        
        try:
            # Decode base64
            combined = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Extract nonce (first 12 bytes)
            nonce = combined[:12]
            
            # Extract encrypted data (remaining bytes minus key_id if present)
            # Check if key_id is appended (look for key_ prefix)
            encrypted_part = combined[12:]
            key_id = None
            
            # Try to extract key_id from end
            if len(encrypted_part) > 20:  # Minimum key_id length
                # Look for key_ pattern at the end
                for i in range(len(encrypted_part) - 20, len(encrypted_part)):
                    if encrypted_part[i:i+4] == b'key_':
                        key_id = encrypted_part[i:].decode('utf-8')
                        encrypted_part = encrypted_part[:i]
                        break
            
            # Use specified key or current key
            if key_id and key_id in self.keys:
                key = self.keys[key_id]
            else:
                key = self.get_current_key()
            
            # Create cipher
            cipher = AESGCM(key.key_data)
            
            # Decrypt data
            decrypted_data = cipher.decrypt(nonce, encrypted_part, None)
            
            return decrypted_data.decode('utf-8')
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt field: {e}")
            raise
    
    # File encryption methods (AES-256-CBC)
    
    def encrypt_file(self, file_path: str, output_path: Optional[str] = None) -> str:
        """Encrypt a file using AES-256-CBC"""
        try:
            key = self.get_current_key()
            
            # Read file data
            with open(file_path, 'rb') as f:
                file_data = f.read()
            
            # Generate random IV
            iv = secrets.token_bytes(16)  # 128 bits for CBC
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key.key_data),
                modes.CBC(iv),
                backend=default_backend()
            )
            encryptor = cipher.encryptor()
            
            # Pad data to block size (16 bytes for AES)
            padding_length = 16 - (len(file_data) % 16)
            padded_data = file_data + bytes([padding_length] * padding_length)
            
            # Encrypt data
            encrypted_data = encryptor.update(padded_data) + encryptor.finalize()
            
            # Combine IV + encrypted data + key_id
            combined = iv + encrypted_data + key.key_id.encode('utf-8')
            
            # Determine output path
            if not output_path:
                output_path = file_path + '.enc'
            
            # Write encrypted file
            with open(output_path, 'wb') as f:
                f.write(combined)
            
            self.logger.info(f"Encrypted file: {file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt file {file_path}: {e}")
            raise
    
    def decrypt_file(self, encrypted_file_path: str, output_path: Optional[str] = None) -> str:
        """Decrypt a file using AES-256-CBC"""
        try:
            # Read encrypted file
            with open(encrypted_file_path, 'rb') as f:
                combined_data = f.read()
            
            # Extract IV (first 16 bytes)
            iv = combined_data[:16]
            
            # Extract key_id from end
            key_id = None
            encrypted_data = combined_data[16:]
            
            # Look for key_id at the end
            for i in range(len(encrypted_data) - 20, len(encrypted_data)):
                if encrypted_data[i:i+4] == b'key_':
                    key_id = encrypted_data[i:].decode('utf-8')
                    encrypted_data = encrypted_data[:i]
                    break
            
            # Use specified key or current key
            if key_id and key_id in self.keys:
                key = self.keys[key_id]
            else:
                key = self.get_current_key()
            
            # Create cipher
            cipher = Cipher(
                algorithms.AES(key.key_data),
                modes.CBC(iv),
                backend=default_backend()
            )
            decryptor = cipher.decryptor()
            
            # Decrypt data
            decrypted_data = decryptor.update(encrypted_data) + decryptor.finalize()
            
            # Remove padding
            padding_length = decrypted_data[-1]
            decrypted_data = decrypted_data[:-padding_length]
            
            # Determine output path
            if not output_path:
                if encrypted_file_path.endswith('.enc'):
                    output_path = encrypted_file_path[:-4]
                else:
                    output_path = encrypted_file_path + '.dec'
            
            # Write decrypted file
            with open(output_path, 'wb') as f:
                f.write(decrypted_data)
            
            self.logger.info(f"Decrypted file: {encrypted_file_path} -> {output_path}")
            return output_path
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt file {encrypted_file_path}: {e}")
            raise
    
    # Database integration methods
    
    def encrypt_patient_name(self, patient_name: str) -> str:
        """Encrypt patient name for database storage"""
        return self.encrypt_field(patient_name)
    
    def decrypt_patient_name(self, encrypted_name: str) -> str:
        """Decrypt patient name from database"""
        return self.decrypt_field(encrypted_name)
    
    def encrypt_medical_notes(self, notes: str) -> str:
        """Encrypt medical notes for database storage"""
        return self.encrypt_field(notes)
    
    def decrypt_medical_notes(self, encrypted_notes: str) -> str:
        """Decrypt medical notes from database"""
        return self.decrypt_field(encrypted_notes)
    
    def encrypt_file_path(self, file_path: str) -> str:
        """Encrypt file path containing patient information"""
        return self.encrypt_field(file_path)
    
    def decrypt_file_path(self, encrypted_path: str) -> str:
        """Decrypt file path from database"""
        return self.decrypt_field(encrypted_path)
    
    # Key management methods
    
    def get_key_info(self) -> Dict[str, Any]:
        """Get information about encryption keys"""
        return {
            'current_key_id': self.current_key_id,
            'total_keys': len(self.keys),
            'active_keys': len([k for k in self.keys.values() if k.is_active]),
            'key_rotation_days': self.key_rotation_days,
            'keys': {
                key_id: {
                    'created_at': key.created_at.isoformat(),
                    'expires_at': key.expires_at.isoformat(),
                    'is_active': key.is_active,
                    'days_until_expiry': key.days_until_expiry()
                }
                for key_id, key in self.keys.items()
            }
        }
    
    def force_key_rotation(self) -> str:
        """Force immediate key rotation"""
        self._rotate_key()
        return self.current_key_id
    
    def backup_keys(self, backup_path: str, password: str) -> bool:
        """Create encrypted backup of encryption keys"""
        try:
            # Validate password strength
            if len(password) < 12:
                raise ValueError("Backup password must be at least 12 characters")
            
            # Create backup data
            backup_data = {
                'keys': {key_id: key.to_dict() for key_id, key in self.keys.items()},
                'current_key_id': self.current_key_id,
                'backup_created': datetime.now().isoformat(),
                'version': '1.0'
            }
            
            # Generate salt and derive key
            salt = secrets.token_bytes(32)
            derived_key = self.derive_key_from_password(password, salt)
            # Convert to Fernet-compatible key
            fernet_key = base64.urlsafe_b64encode(derived_key)
            fernet = Fernet(fernet_key)
            
            # Encrypt backup data
            encrypted_data = fernet.encrypt(json.dumps(backup_data).encode())
            
            # Write backup file
            with open(backup_path, 'wb') as f:
                f.write(salt + encrypted_data)
            
            self.logger.info(f"Created key backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to backup keys: {e}")
            return False
    
    def restore_keys(self, backup_path: str, password: str) -> bool:
        """Restore encryption keys from backup"""
        try:
            if not os.path.exists(backup_path):
                raise FileNotFoundError("Backup file not found")
            
            # Read backup file
            with open(backup_path, 'rb') as f:
                data = f.read()
            
            # Extract salt and encrypted data
            salt = data[:32]
            encrypted_data = data[32:]
            
            # Derive key and decrypt
            derived_key = self.derive_key_from_password(password, salt)
            # Convert to Fernet-compatible key
            fernet_key = base64.urlsafe_b64encode(derived_key)
            fernet = Fernet(fernet_key)
            decrypted_data = fernet.decrypt(encrypted_data)
            
            # Parse backup data
            backup_data = json.loads(decrypted_data.decode())
            
            # Restore keys
            self.keys = {}
            for key_id, key_info in backup_data['keys'].items():
                self.keys[key_id] = EncryptionKey.from_dict(key_info)
            
            self.current_key_id = backup_data['current_key_id']
            self._save_keys()
            
            self.logger.info(f"Restored keys from backup: {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore keys: {e}")
            return False


# Utility functions for easy integration

def get_encryption_manager() -> EncryptionManager:
    """Get singleton encryption manager instance"""
    if not hasattr(get_encryption_manager, '_instance'):
        get_encryption_manager._instance = EncryptionManager()
    return get_encryption_manager._instance


def encrypt_sensitive_data(data: str, data_type: str = "field") -> str:
    """Convenience function to encrypt sensitive data"""
    manager = get_encryption_manager()
    
    if data_type == "field":
        return manager.encrypt_field(data)
    elif data_type == "patient_name":
        return manager.encrypt_patient_name(data)
    elif data_type == "medical_notes":
        return manager.encrypt_medical_notes(data)
    elif data_type == "file_path":
        return manager.encrypt_file_path(data)
    else:
        return manager.encrypt_field(data)


def decrypt_sensitive_data(encrypted_data: str, data_type: str = "field") -> str:
    """Convenience function to decrypt sensitive data"""
    manager = get_encryption_manager()
    
    if data_type == "field":
        return manager.decrypt_field(encrypted_data)
    elif data_type == "patient_name":
        return manager.decrypt_patient_name(encrypted_data)
    elif data_type == "medical_notes":
        return manager.decrypt_medical_notes(encrypted_data)
    elif data_type == "file_path":
        return manager.decrypt_file_path(encrypted_data)
    else:
        return manager.decrypt_field(encrypted_data)
