#!/usr/bin/env python3
"""
File Encryption Service for Physiotherapy Clinic Assistant
Handles automatic encryption of patient files and manages encrypted file storage
"""

import os
import shutil
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from encryption_manager import get_encryption_manager
from encrypted_database_manager import EncryptedDatabaseManager


class FileEncryptionService:
    """Service for managing encrypted patient files"""
    
    def __init__(self, db_manager: EncryptedDatabaseManager):
        self.db_manager = db_manager
        self.encryption_manager = get_encryption_manager()
        self.logger = logging.getLogger(__name__)
        
        # File type encryption settings
        self.encryption_settings = {
            'audio': {
                'extensions': ['.wav', '.mp3', '.m4a', '.flac'],
                'algorithm': 'AES-256-CBC',
                'auto_encrypt': True
            },
            'transcript': {
                'extensions': ['.txt', '.doc', '.docx'],
                'algorithm': 'AES-256-CBC',
                'auto_encrypt': True
            },
            'extraction': {
                'extensions': ['.json', '.xml'],
                'algorithm': 'AES-256-CBC',
                'auto_encrypt': True
            },
            'form': {
                'extensions': ['.pdf'],
                'algorithm': 'AES-256-CBC',
                'auto_encrypt': True
            }
        }
    
    def should_encrypt_file(self, file_path: str) -> Tuple[bool, str]:
        """Determine if a file should be encrypted based on its type"""
        file_ext = Path(file_path).suffix.lower()
        
        for file_type, settings in self.encryption_settings.items():
            if file_ext in settings['extensions'] and settings['auto_encrypt']:
                return True, file_type
        
        return False, 'unknown'
    
    def encrypt_patient_file(self, file_path: str, user_id: str, 
                           appointment_id: Optional[int] = None) -> Dict[str, Any]:
        """Encrypt a patient file and update database records"""
        try:
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"File not found: {file_path}")
            
            # Check if file should be encrypted
            should_encrypt, file_type = self.should_encrypt_file(file_path)
            
            if not should_encrypt:
                return {
                    'success': False,
                    'message': f'File type {file_type} does not require encryption',
                    'file_path': file_path
                }
            
            # Create encrypted version
            encrypted_path = self.encryption_manager.encrypt_file(file_path)
            
            # Calculate file hashes
            original_hash = self._calculate_file_hash(file_path)
            encrypted_hash = self._calculate_file_hash(encrypted_path)
            
            # Update database if appointment_id provided
            if appointment_id:
                # Find existing file record
                files = self.db_manager.get_appointment_files(appointment_id, user_id)
                for file_record in files:
                    if file_record['file_path'] == file_path:
                        # Update the file record with encrypted path
                        with self.db_manager.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE files 
                                SET file_path_encrypted = ?, is_encrypted = 1,
                                    file_hash_encrypted = ?, encryption_key_id = ?
                                WHERE file_id = ?
                            """, (
                                self.encryption_manager.encrypt_file_path(encrypted_path),
                                self.encryption_manager.encrypt_field(encrypted_hash),
                                self.encryption_manager.get_current_key().key_id,
                                file_record['file_id']
                            ))
                            conn.commit()
                        break
            
            # Remove original file after successful encryption
            os.remove(file_path)
            
            self.logger.info(f"Encrypted file: {file_path} -> {encrypted_path}")
            
            return {
                'success': True,
                'message': f'File encrypted successfully',
                'original_path': file_path,
                'encrypted_path': encrypted_path,
                'file_type': file_type,
                'original_hash': original_hash,
                'encrypted_hash': encrypted_hash
            }
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt file {file_path}: {e}")
            return {
                'success': False,
                'message': f'Encryption failed: {str(e)}',
                'file_path': file_path
            }
    
    def decrypt_patient_file(self, encrypted_file_path: str, user_id: str, 
                           temporary: bool = True) -> Dict[str, Any]:
        """Decrypt a patient file for access"""
        try:
            if not os.path.exists(encrypted_file_path):
                raise FileNotFoundError(f"Encrypted file not found: {encrypted_file_path}")
            
            # Decrypt the file
            if temporary:
                # Create temporary decrypted file in proper writable location
                try:
                    from app_paths import get_temp_path
                    temp_dir = get_temp_path()
                except ImportError:
                    import sys
                    if sys.platform == 'darwin':
                        temp_dir = Path(f"/tmp/PhysioClinicAssistant")
                        temp_dir.mkdir(parents=True, exist_ok=True)
                    else:
                        temp_dir = Path("temp")
                        temp_dir.mkdir(exist_ok=True)
                
                temp_filename = f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(encrypted_file_path).name}"
                decrypted_path = temp_dir / temp_filename
            else:
                # Decrypt to original location
                if encrypted_file_path.endswith('.enc'):
                    decrypted_path = encrypted_file_path[:-4]
                else:
                    decrypted_path = encrypted_file_path + '.dec'
            
            decrypted_path = self.encryption_manager.decrypt_file(
                encrypted_file_path, str(decrypted_path)
            )
            
            self.logger.info(f"Decrypted file: {encrypted_file_path} -> {decrypted_path}")
            
            return {
                'success': True,
                'message': 'File decrypted successfully',
                'encrypted_path': encrypted_file_path,
                'decrypted_path': decrypted_path,
                'temporary': temporary
            }
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt file {encrypted_file_path}: {e}")
            return {
                'success': False,
                'message': f'Decryption failed: {str(e)}',
                'encrypted_path': encrypted_file_path
            }
    
    def encrypt_appointment_files(self, appointment_id: int, user_id: str) -> Dict[str, Any]:
        """Encrypt all files for a specific appointment"""
        try:
            # Get all files for the appointment
            files = self.db_manager.get_appointment_files(appointment_id, user_id)
            
            results = {
                'success': True,
                'total_files': len(files),
                'encrypted_files': 0,
                'skipped_files': 0,
                'failed_files': 0,
                'details': []
            }
            
            for file_record in files:
                file_path = file_record['file_path']
                
                # Skip if already encrypted
                if file_record.get('is_encrypted'):
                    results['skipped_files'] += 1
                    results['details'].append({
                        'file_path': file_path,
                        'status': 'skipped',
                        'message': 'Already encrypted'
                    })
                    continue
                
                # Encrypt the file
                encrypt_result = self.encrypt_patient_file(file_path, user_id, appointment_id)
                
                if encrypt_result['success']:
                    results['encrypted_files'] += 1
                    results['details'].append({
                        'file_path': file_path,
                        'status': 'encrypted',
                        'encrypted_path': encrypt_result['encrypted_path']
                    })
                else:
                    results['failed_files'] += 1
                    results['details'].append({
                        'file_path': file_path,
                        'status': 'failed',
                        'message': encrypt_result['message']
                    })
            
            # Update overall success status
            if results['failed_files'] > 0:
                results['success'] = False
                results['message'] = f"Encrypted {results['encrypted_files']} files, {results['failed_files']} failed"
            else:
                results['message'] = f"Successfully encrypted {results['encrypted_files']} files"
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt appointment files: {e}")
            return {
                'success': False,
                'message': f'Failed to encrypt appointment files: {str(e)}',
                'total_files': 0,
                'encrypted_files': 0,
                'failed_files': 0
            }
    
    def decrypt_appointment_files(self, appointment_id: int, user_id: str, 
                                temporary: bool = True) -> Dict[str, Any]:
        """Decrypt all files for a specific appointment"""
        try:
            # Get all encrypted files for the appointment
            files = self.db_manager.get_appointment_files(appointment_id, user_id)
            encrypted_files = [f for f in files if f.get('is_encrypted')]
            
            results = {
                'success': True,
                'total_files': len(encrypted_files),
                'decrypted_files': 0,
                'failed_files': 0,
                'details': [],
                'temp_directory': None
            }
            
            if temporary:
                # Create temporary directory for decrypted files in proper writable location
                try:
                    from app_paths import get_temp_path
                    temp_dir = get_temp_path(f"appointment_{appointment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                except ImportError:
                    import sys
                    if sys.platform == 'darwin':
                        temp_base = Path(f"/tmp/PhysioClinicAssistant/appointment_{appointment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                    else:
                        temp_base = Path(f"temp/appointment_{appointment_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                    temp_base.mkdir(parents=True, exist_ok=True)
                    temp_dir = temp_base
                results['temp_directory'] = str(temp_dir)
            
            for file_record in encrypted_files:
                encrypted_path = file_record['file_path']
                
                # Decrypt the file
                decrypt_result = self.decrypt_patient_file(encrypted_path, user_id, temporary)
                
                if decrypt_result['success']:
                    results['decrypted_files'] += 1
                    results['details'].append({
                        'encrypted_path': encrypted_path,
                        'decrypted_path': decrypt_result['decrypted_path'],
                        'status': 'decrypted'
                    })
                else:
                    results['failed_files'] += 1
                    results['details'].append({
                        'encrypted_path': encrypted_path,
                        'status': 'failed',
                        'message': decrypt_result['message']
                    })
            
            # Update overall success status
            if results['failed_files'] > 0:
                results['success'] = False
                results['message'] = f"Decrypted {results['decrypted_files']} files, {results['failed_files']} failed"
            else:
                results['message'] = f"Successfully decrypted {results['decrypted_files']} files"
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt appointment files: {e}")
            return {
                'success': False,
                'message': f'Failed to decrypt appointment files: {str(e)}',
                'total_files': 0,
                'decrypted_files': 0,
                'failed_files': 0
            }
    
    def cleanup_temp_files(self, temp_directory: str = None) -> Dict[str, Any]:
        """Clean up temporary decrypted files"""
        try:
            if temp_directory:
                # Clean specific directory
                if os.path.exists(temp_directory):
                    shutil.rmtree(temp_directory)
                    return {
                        'success': True,
                        'message': f'Cleaned up temporary directory: {temp_directory}',
                        'cleaned_files': 1
                    }
            else:
                # Clean all temp files older than 1 hour from proper temp location
                try:
                    from app_paths import get_temp_path
                    temp_dir = get_temp_path()
                except ImportError:
                    import sys
                    if sys.platform == 'darwin':
                        temp_dir = Path(f"/tmp/PhysioClinicAssistant")
                    else:
                        temp_dir = Path("temp")
                
                if not temp_dir.exists():
                    return {'success': True, 'message': 'No temp directory found', 'cleaned_files': 0}
                
                cleaned_count = 0
                current_time = datetime.now()
                
                for item in temp_dir.iterdir():
                    if item.is_file() or item.is_dir():
                        # Check if file/directory is older than 1 hour
                        file_time = datetime.fromtimestamp(item.stat().st_mtime)
                        if (current_time - file_time).total_seconds() > 3600:  # 1 hour
                            if item.is_dir():
                                shutil.rmtree(item)
                            else:
                                item.unlink()
                            cleaned_count += 1
                
                return {
                    'success': True,
                    'message': f'Cleaned up {cleaned_count} temporary files',
                    'cleaned_files': cleaned_count
                }
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup temp files: {e}")
            return {
                'success': False,
                'message': f'Cleanup failed: {str(e)}',
                'cleaned_files': 0
            }
    
    def get_encryption_status(self) -> Dict[str, Any]:
        """Get comprehensive file encryption status"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get file encryption statistics by type
                cursor.execute("""
                    SELECT 
                        file_type,
                        COUNT(*) as total_files,
                        SUM(CASE WHEN is_encrypted = 1 THEN 1 ELSE 0 END) as encrypted_files,
                        SUM(CASE WHEN is_encrypted = 0 THEN 1 ELSE 0 END) as unencrypted_files
                    FROM files 
                    WHERE is_deleted = 0
                    GROUP BY file_type
                """)
                
                file_stats = {}
                for row in cursor.fetchall():
                    file_stats[row['file_type']] = {
                        'total': row['total_files'],
                        'encrypted': row['encrypted_files'],
                        'unencrypted': row['unencrypted_files'],
                        'encryption_rate': (row['encrypted_files'] / row['total_files'] * 100) if row['total_files'] > 0 else 0
                    }
                
                # Get overall statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_files,
                        SUM(CASE WHEN is_encrypted = 1 THEN 1 ELSE 0 END) as encrypted_files,
                        SUM(CASE WHEN is_encrypted = 0 THEN 1 ELSE 0 END) as unencrypted_files
                    FROM files 
                    WHERE is_deleted = 0
                """)
                
                overall_stats = cursor.fetchone()
                
                return {
                    'overall': {
                        'total_files': overall_stats['total_files'],
                        'encrypted_files': overall_stats['encrypted_files'],
                        'unencrypted_files': overall_stats['unencrypted_files'],
                        'encryption_rate': (overall_stats['encrypted_files'] / overall_stats['total_files'] * 100) if overall_stats['total_files'] > 0 else 0
                    },
                    'by_type': file_stats,
                    'encryption_settings': self.encryption_settings,
                    'last_updated': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get encryption status: {e}")
            return {'error': str(e)}
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file"""
        import hashlib
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def bulk_encrypt_unencrypted_files(self, user_id: str, limit: int = 100) -> Dict[str, Any]:
        """Bulk encrypt all unencrypted files (for migration)"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get unencrypted files
                cursor.execute("""
                    SELECT f.file_id, f.file_path, f.appointment_id, a.patient_name
                    FROM files f
                    JOIN appointments a ON f.appointment_id = a.appointment_id
                    WHERE f.is_encrypted = 0 AND f.is_deleted = 0
                    LIMIT ?
                """, (limit,))
                
                unencrypted_files = cursor.fetchall()
                
                results = {
                    'success': True,
                    'total_files': len(unencrypted_files),
                    'encrypted_files': 0,
                    'failed_files': 0,
                    'details': []
                }
                
                for file_record in unencrypted_files:
                    file_id, file_path, appointment_id, patient_name = file_record
                    
                    # Check if file exists
                    if not os.path.exists(file_path):
                        results['failed_files'] += 1
                        results['details'].append({
                            'file_id': file_id,
                            'file_path': file_path,
                            'status': 'failed',
                            'message': 'File not found'
                        })
                        continue
                    
                    # Encrypt the file
                    encrypt_result = self.encrypt_patient_file(file_path, user_id, appointment_id)
                    
                    if encrypt_result['success']:
                        results['encrypted_files'] += 1
                        results['details'].append({
                            'file_id': file_id,
                            'file_path': file_path,
                            'patient_name': patient_name,
                            'status': 'encrypted',
                            'encrypted_path': encrypt_result['encrypted_path']
                        })
                    else:
                        results['failed_files'] += 1
                        results['details'].append({
                            'file_id': file_id,
                            'file_path': file_path,
                            'patient_name': patient_name,
                            'status': 'failed',
                            'message': encrypt_result['message']
                        })
                
                # Update overall success status
                if results['failed_files'] > 0:
                    results['success'] = False
                    results['message'] = f"Encrypted {results['encrypted_files']} files, {results['failed_files']} failed"
                else:
                    results['message'] = f"Successfully encrypted {results['encrypted_files']} files"
                
                return results
                
        except Exception as e:
            self.logger.error(f"Failed to bulk encrypt files: {e}")
            return {
                'success': False,
                'message': f'Bulk encryption failed: {str(e)}',
                'total_files': 0,
                'encrypted_files': 0,
                'failed_files': 0
            }
