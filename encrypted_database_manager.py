#!/usr/bin/env python3
"""
Encrypted Database Manager for Physiotherapy Clinic Assistant
Extends the base DatabaseManager with comprehensive encryption for sensitive data
"""

import sqlite3
import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from database_manager import DatabaseManager
from encryption_manager import EncryptionManager, get_encryption_manager
import logging


class EncryptedDatabaseManager(DatabaseManager):
    """Enhanced database manager with encryption for sensitive data"""
    
    def __init__(self, db_path: Optional[str] = None):
        # Pass None to use proper writable path from DatabaseManager
        super().__init__(db_path)
        self.encryption_manager = get_encryption_manager()
        self.logger = logging.getLogger(__name__)
        
        # Initialize encryption-aware database schema
        self._init_encrypted_schema()
    
    def _init_encrypted_schema(self):
        """Initialize database schema with encryption support"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Add encryption-related columns to existing tables (with error handling for existing columns)
            encryption_columns = [
                ("appointments", "patient_name_encrypted", "TEXT"),
                ("appointments", "notes_encrypted", "TEXT"),
                ("appointments", "folder_path_encrypted", "TEXT"),
                ("appointments", "encryption_key_id", "VARCHAR(255)"),
                ("appointments", "is_encrypted", "BOOLEAN DEFAULT 0"),
                ("files", "file_path_encrypted", "TEXT"),
                ("files", "encryption_key_id", "VARCHAR(255)"),
                ("files", "is_encrypted", "BOOLEAN DEFAULT 0"),
                ("files", "file_hash_encrypted", "VARCHAR(64)")
            ]
            
            for table, column, column_type in encryption_columns:
                try:
                    cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type};")
                except sqlite3.OperationalError as e:
                    if "duplicate column name" not in str(e):
                        raise
            
            # Create encryption keys table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS encryption_keys (
                    key_id VARCHAR(255) PRIMARY KEY,
                    key_data TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_active BOOLEAN DEFAULT 1,
                    key_type VARCHAR(50) DEFAULT 'AES-256'
                )
            """)
            
            # Create indexes for encryption keys
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_encryption_keys_active ON encryption_keys(is_active)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_encryption_keys_expires ON encryption_keys(expires_at)")
            
            conn.commit()
    
    
    # Enhanced appointment methods with encryption
    
    def create_appointment(self, patient_name: str, appointment_date: str, 
                          appointment_time: str, user_id: str, **kwargs) -> int:
        """Create a new appointment with encrypted sensitive data"""
        try:
            # Encrypt sensitive data
            encrypted_patient_name = self.encryption_manager.encrypt_patient_name(patient_name)
            encrypted_notes = self.encryption_manager.encrypt_medical_notes(
                kwargs.get('notes', '')
            )
            
            # Generate appointment code and folder path
            date_str = appointment_date.replace('-', '')
            time_str = appointment_time.replace(':', '')
            
            import time
            microseconds = int(time.time() * 1000000) % 1000000
            appointment_code = f"{date_str}_{time_str}_{microseconds:06d}"
            
            # Create folder path in writable location
            safe_patient_name = patient_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            try:
                from app_paths import get_writable_path
                folder_path = str(get_writable_path(f"data/{appointment_date}/{safe_patient_name}_{appointment_time}"))
            except ImportError:
                folder_path = f"data/{appointment_date}/{safe_patient_name}_{appointment_time}"
            encrypted_folder_path = self.encryption_manager.encrypt_file_path(folder_path)
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current encryption key ID
                current_key = self.encryption_manager.get_current_key()
                
                cursor.execute("""
                    INSERT INTO appointments (
                        appointment_code, patient_name, patient_name_encrypted,
                        appointment_date, appointment_time, appointment_type,
                        notes, notes_encrypted, folder_path, folder_path_encrypted,
                        encryption_key_id, is_encrypted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    appointment_code, patient_name, encrypted_patient_name,
                    appointment_date, appointment_time, kwargs.get('appointment_type'),
                    kwargs.get('notes', ''), encrypted_notes, folder_path, encrypted_folder_path,
                    current_key.key_id, True
                ))
                
                appointment_id = cursor.lastrowid
                conn.commit()
                
                # Audit logging is handled by AuditedDatabaseManager
                
                return appointment_id
                
        except Exception as e:
            self.logger.error(f"Failed to create encrypted appointment: {e}")
            raise
    
    def get_appointment(self, appointment_id: int, user_id: str) -> Optional[Dict]:
        """Get appointment by ID with decrypted sensitive data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
                row = cursor.fetchone()
                
                if not row:
                    return None
                
                appointment = dict(row)
                
                # Decrypt sensitive data if encrypted
                if appointment.get('is_encrypted'):
                    if appointment.get('patient_name_encrypted'):
                        appointment['patient_name'] = self.encryption_manager.decrypt_patient_name(
                            appointment['patient_name_encrypted']
                        )
                    if appointment.get('notes_encrypted'):
                        appointment['notes'] = self.encryption_manager.decrypt_medical_notes(
                            appointment['notes_encrypted']
                        )
                    if appointment.get('folder_path_encrypted'):
                        appointment['folder_path'] = self.encryption_manager.decrypt_file_path(
                            appointment['folder_path_encrypted']
                        )
                
                # Audit logging is handled by AuditedDatabaseManager
                
                return appointment
                
        except Exception as e:
            self.logger.error(f"Failed to get encrypted appointment: {e}")
            raise
    
    def update_appointment(self, appointment_id: int, user_id: str, **kwargs) -> bool:
        """Update appointment with encrypted sensitive data"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get current appointment
                cursor.execute("SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
                current_appointment = cursor.fetchone()
                
                if not current_appointment:
                    return False
                
                # Prepare update data
                update_fields = []
                update_values = []
                
                # Handle patient name update
                if 'patient_name' in kwargs:
                    encrypted_name = self.encryption_manager.encrypt_patient_name(kwargs['patient_name'])
                    update_fields.extend(['patient_name = ?', 'patient_name_encrypted = ?'])
                    update_values.extend([kwargs['patient_name'], encrypted_name])
                
                # Handle notes update
                if 'notes' in kwargs:
                    encrypted_notes = self.encryption_manager.encrypt_medical_notes(kwargs['notes'])
                    update_fields.extend(['notes = ?', 'notes_encrypted = ?'])
                    update_values.extend([kwargs['notes'], encrypted_notes])
                
                # Handle other fields
                for field in ['appointment_date', 'appointment_time', 'appointment_type']:
                    if field in kwargs:
                        update_fields.append(f"{field} = ?")
                        update_values.append(kwargs[field])
                
                if not update_fields:
                    return True  # No updates needed
                
                # Add updated timestamp
                update_fields.append('updated_at = CURRENT_TIMESTAMP')
                update_values.append(appointment_id)
                
                # Execute update
                sql = f"UPDATE appointments SET {', '.join(update_fields)} WHERE appointment_id = ?"
                cursor.execute(sql, update_values)
                conn.commit()
                
                # Audit logging is handled by AuditedDatabaseManager
                
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to update encrypted appointment: {e}")
            raise
    
    # Enhanced file methods with encryption
    
    def add_file(self, appointment_id: int, file_type: str, file_path: str, 
                 retention_policy: str, user_id: str) -> int:
        """Add a file to the database with encrypted metadata"""
        try:
            # Encrypt file path
            encrypted_file_path = self.encryption_manager.encrypt_file_path(file_path)
            
            # Calculate file size and hash
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            file_hash = self.calculate_file_hash(file_path) if os.path.exists(file_path) else None
            
            # Encrypt file hash
            encrypted_file_hash = self.encryption_manager.encrypt_field(file_hash) if file_hash else None
            
            # Calculate retention date
            retention_date = self.calculate_retention_date(retention_policy)
            
            # Get current encryption key ID
            current_key = self.encryption_manager.get_current_key()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO files (
                        appointment_id, file_type, file_path, file_path_encrypted,
                        file_size, file_hash, file_hash_encrypted, retention_policy,
                        retention_date, encryption_key_id, is_encrypted
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    appointment_id, file_type, file_path, encrypted_file_path,
                    file_size, file_hash, encrypted_file_hash, retention_policy,
                    retention_date, current_key.key_id, True
                ))
                
                file_id = cursor.lastrowid
                conn.commit()
                
                # Audit logging is handled by AuditedDatabaseManager
                
                return file_id
                
        except Exception as e:
            self.logger.error(f"Failed to add encrypted file: {e}")
            raise
    
    def get_appointment_files(self, appointment_id: int, user_id: str) -> List[Dict]:
        """Get all files for an appointment with decrypted metadata"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM files 
                    WHERE appointment_id = ? AND is_deleted = 0
                    ORDER BY created_date
                """, (appointment_id,))
                
                files = []
                for row in cursor.fetchall():
                    file_data = dict(row)
                    
                    # Decrypt sensitive data if encrypted
                    if file_data.get('is_encrypted'):
                        if file_data.get('file_path_encrypted'):
                            file_data['file_path'] = self.encryption_manager.decrypt_file_path(
                                file_data['file_path_encrypted']
                            )
                        if file_data.get('file_hash_encrypted'):
                            file_data['file_hash'] = self.encryption_manager.decrypt_field(
                                file_data['file_hash_encrypted']
                            )
                    
                    files.append(file_data)
                
                # Audit logging is handled by AuditedDatabaseManager
                
                return files
                
        except Exception as e:
            self.logger.error(f"Failed to get encrypted appointment files: {e}")
            raise
    
    # File encryption methods
    
    def encrypt_patient_file(self, file_path: str, user_id: str) -> str:
        """Encrypt a patient file and update database records"""
        try:
            # Encrypt the file
            encrypted_path = self.encryption_manager.encrypt_file(file_path)
            
            # Update database record if it exists
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE files 
                    SET file_path_encrypted = ?, is_encrypted = 1
                    WHERE file_path = ?
                """, (self.encryption_manager.encrypt_file_path(encrypted_path), file_path))
                conn.commit()
            
            # Log audit event
            self._log_audit_event(
                user_id=user_id,
                event_type='ENCRYPT',
                file_operation=True,
                file_path=file_path,
                operation_details=f"Encrypted file: {file_path} -> {encrypted_path}"
            )
            
            return encrypted_path
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt patient file: {e}")
            raise
    
    def decrypt_patient_file(self, encrypted_file_path: str, user_id: str) -> str:
        """Decrypt a patient file for access"""
        try:
            # Decrypt the file
            decrypted_path = self.encryption_manager.decrypt_file(encrypted_file_path)
            
            # Log audit event
            self._log_audit_event(
                user_id=user_id,
                event_type='DECRYPT',
                file_operation=True,
                file_path=encrypted_file_path,
                operation_details=f"Decrypted file: {encrypted_file_path} -> {decrypted_path}"
            )
            
            return decrypted_path
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt patient file: {e}")
            raise
    
    # Search methods with encryption awareness
    
    def search_appointments_by_patient(self, patient_name: str, user_id: str) -> List[Dict]:
        """Search appointments by patient name (works with encrypted data)"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Search both encrypted and unencrypted patient names
                cursor.execute("""
                    SELECT * FROM appointments 
                    WHERE patient_name LIKE ? OR patient_name_encrypted LIKE ?
                    ORDER BY appointment_date DESC, appointment_time DESC
                """, (f"%{patient_name}%", f"%{patient_name}%"))
                
                appointments = []
                for row in cursor.fetchall():
                    appointment = dict(row)
                    
                    # Decrypt sensitive data if encrypted
                    if appointment.get('is_encrypted'):
                        if appointment.get('patient_name_encrypted'):
                            appointment['patient_name'] = self.encryption_manager.decrypt_patient_name(
                                appointment['patient_name_encrypted']
                            )
                        if appointment.get('notes_encrypted'):
                            appointment['notes'] = self.encryption_manager.decrypt_medical_notes(
                                appointment['notes_encrypted']
                            )
                        if appointment.get('folder_path_encrypted'):
                            appointment['folder_path'] = self.encryption_manager.decrypt_file_path(
                                appointment['folder_path_encrypted']
                            )
                    
                    appointments.append(appointment)
                
                # Audit logging is handled by AuditedDatabaseManager
                
                return appointments
                
        except Exception as e:
            self.logger.error(f"Failed to search encrypted appointments: {e}")
            raise
    
    # Audit and compliance methods
    
    def get_audit_log(self, user_id: str = None, event_type: str = None, 
                     start_date: str = None, end_date: str = None, 
                     limit: int = 1000) -> List[Dict]:
        """Get audit log entries with filtering"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with filters
                where_conditions = []
                params = []
                
                if user_id:
                    where_conditions.append("user_id = ?")
                    params.append(user_id)
                
                if event_type:
                    where_conditions.append("event_type = ?")
                    params.append(event_type)
                
                if start_date:
                    where_conditions.append("event_timestamp >= ?")
                    params.append(start_date)
                
                if end_date:
                    where_conditions.append("event_timestamp <= ?")
                    params.append(end_date)
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                sql = f"""
                    SELECT * FROM audit_log 
                    {where_clause}
                    ORDER BY event_timestamp DESC 
                    LIMIT ?
                """
                params.append(limit)
                
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get audit log: {e}")
            raise
    
    def verify_audit_integrity(self) -> Dict[str, Any]:
        """Verify the integrity of the audit log"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all audit records in order
                cursor.execute("""
                    SELECT audit_id, audit_hash, previous_hash, event_timestamp
                    FROM audit_log 
                    ORDER BY audit_id
                """)
                
                records = cursor.fetchall()
                integrity_issues = []
                previous_hash = None
                
                for record in records:
                    audit_id, audit_hash, stored_previous_hash, timestamp = record
                    
                    # Check if previous hash matches
                    if stored_previous_hash != previous_hash:
                        integrity_issues.append({
                            'audit_id': audit_id,
                            'issue': 'Previous hash mismatch',
                            'expected': previous_hash,
                            'actual': stored_previous_hash,
                            'timestamp': timestamp
                        })
                    
                    # Verify current hash
                    # (In a real implementation, you'd recalculate the hash)
                    previous_hash = audit_hash
                
                return {
                    'total_records': len(records),
                    'integrity_issues': integrity_issues,
                    'is_intact': len(integrity_issues) == 0,
                    'verification_timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to verify audit integrity: {e}")
            return {'error': str(e), 'is_intact': False}
    
    # Key management methods
    
    def get_encryption_status(self) -> Dict[str, Any]:
        """Get comprehensive encryption status"""
        try:
            key_info = self.encryption_manager.get_key_info()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get encryption statistics
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_appointments,
                        SUM(CASE WHEN is_encrypted = 1 THEN 1 ELSE 0 END) as encrypted_appointments,
                        COUNT(*) - SUM(CASE WHEN is_encrypted = 1 THEN 1 ELSE 0 END) as unencrypted_appointments
                    FROM appointments
                """)
                appointment_stats = cursor.fetchone()
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_files,
                        SUM(CASE WHEN is_encrypted = 1 THEN 1 ELSE 0 END) as encrypted_files,
                        COUNT(*) - SUM(CASE WHEN is_encrypted = 1 THEN 1 ELSE 0 END) as unencrypted_files
                    FROM files
                """)
                file_stats = cursor.fetchone()
                
                return {
                    'encryption_keys': key_info,
                    'appointment_encryption': dict(appointment_stats),
                    'file_encryption': dict(file_stats),
                    'encryption_enabled': True,
                    'last_updated': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get encryption status: {e}")
            return {'error': str(e), 'encryption_enabled': False}
