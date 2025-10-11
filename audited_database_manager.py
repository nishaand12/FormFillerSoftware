#!/usr/bin/env python3
"""
Audited Database Manager for Physiotherapy Clinic Assistant
Extends the encrypted database manager with comprehensive audit logging and soft deletes
"""

import os
import json
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from encrypted_database_manager import EncryptedDatabaseManager
from audit_manager import AuditManager, AuditEventType, get_audit_manager


class AuditedDatabaseManager(EncryptedDatabaseManager):
    """Enhanced database manager with comprehensive audit logging and soft deletes"""
    
    def __init__(self, db_path: str = "data/clinic_data.db"):
        super().__init__(db_path)
        self.audit_manager = get_audit_manager()
        self.logger = logging.getLogger(__name__)
        
        # Initialize audit-aware database schema
        self._init_audited_schema()
    
    def _init_audited_schema(self):
        """Initialize database schema with audit support and soft deletes"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Add soft delete columns to existing tables (with error handling for existing columns)
            try:
                cursor.execute("ALTER TABLE appointments ADD COLUMN is_deleted BOOLEAN DEFAULT 0;")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
            
            try:
                cursor.execute("ALTER TABLE appointments ADD COLUMN deleted_at TIMESTAMP;")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
            
            try:
                cursor.execute("ALTER TABLE appointments ADD COLUMN deleted_by VARCHAR(255);")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
            
            try:
                cursor.execute("ALTER TABLE appointments ADD COLUMN updated_at TIMESTAMP;")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
            
            try:
                cursor.execute("ALTER TABLE appointments ADD COLUMN updated_by VARCHAR(255);")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
            
            # Add soft delete columns to files table (with error handling for existing columns)
            try:
                cursor.execute("ALTER TABLE files ADD COLUMN deleted_at TIMESTAMP;")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
            
            try:
                cursor.execute("ALTER TABLE files ADD COLUMN deleted_by VARCHAR(255);")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
            
            try:
                cursor.execute("ALTER TABLE files ADD COLUMN updated_at TIMESTAMP;")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
            
            try:
                cursor.execute("ALTER TABLE files ADD COLUMN updated_by VARCHAR(255);")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e):
                    raise
            
            # Create version history table for tracking changes
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS appointment_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    appointment_id INTEGER NOT NULL,
                    version_number INTEGER NOT NULL,
                    patient_name TEXT,
                    patient_name_encrypted TEXT,
                    appointment_date DATE,
                    appointment_time TIME,
                    appointment_type VARCHAR(50),
                    notes TEXT,
                    notes_encrypted TEXT,
                    folder_path TEXT,
                    folder_path_encrypted TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(255),
                    change_reason TEXT,
                    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
                );
            """)
            
            # Create version history table for files
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_versions (
                    version_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_id INTEGER NOT NULL,
                    version_number INTEGER NOT NULL,
                    appointment_id INTEGER,
                    file_type VARCHAR(20),
                    file_path TEXT,
                    file_path_encrypted TEXT,
                    file_size INTEGER,
                    file_hash VARCHAR(64),
                    file_hash_encrypted VARCHAR(64),
                    retention_policy VARCHAR(20),
                    retention_date DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_by VARCHAR(255),
                    change_reason TEXT,
                    FOREIGN KEY (file_id) REFERENCES files(file_id)
                );
            """)
            
            # Create indexes for version tables
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_appointment_versions_appointment_id 
                ON appointment_versions(appointment_id);
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_file_versions_file_id 
                ON file_versions(file_id);
            """)
            
            # Create triggers for automatic versioning
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS appointment_version_trigger
                AFTER UPDATE ON appointments
                FOR EACH ROW
                WHEN NEW.is_deleted = 0
                BEGIN
                    INSERT INTO appointment_versions (
                        appointment_id, version_number, patient_name, patient_name_encrypted,
                        appointment_date, appointment_time, appointment_type, notes, notes_encrypted,
                        folder_path, folder_path_encrypted, created_by, change_reason
                    ) VALUES (
                        NEW.appointment_id,
                        (SELECT COALESCE(MAX(version_number), 0) + 1 FROM appointment_versions WHERE appointment_id = NEW.appointment_id),
                        OLD.patient_name, OLD.patient_name_encrypted,
                        OLD.appointment_date, OLD.appointment_time, OLD.appointment_type,
                        OLD.notes, OLD.notes_encrypted, OLD.folder_path, OLD.folder_path_encrypted,
                        NEW.updated_by, 'Automatic versioning on update'
                    );
                END;
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS file_version_trigger
                AFTER UPDATE ON files
                FOR EACH ROW
                WHEN NEW.is_deleted = 0
                BEGIN
                    INSERT INTO file_versions (
                        file_id, version_number, appointment_id, file_type, file_path, file_path_encrypted,
                        file_size, file_hash, file_hash_encrypted, retention_policy, retention_date,
                        created_by, change_reason
                    ) VALUES (
                        NEW.file_id,
                        (SELECT COALESCE(MAX(version_number), 0) + 1 FROM file_versions WHERE file_id = NEW.file_id),
                        OLD.appointment_id, OLD.file_type, OLD.file_path, OLD.file_path_encrypted,
                        OLD.file_size, OLD.file_hash, OLD.file_hash_encrypted,
                        OLD.retention_policy, OLD.retention_date,
                        NEW.updated_by, 'Automatic versioning on update'
                    );
                END;
            """)
            
            conn.commit()
    
    def _get_user_context(self, user_id: str) -> Dict[str, Any]:
        """Get user context for audit logging"""
        try:
            # Try to get current user from auth manager if available
            session_id = None
            ip_address = None
            user_agent = None
            
            # Check if we can get session info from the main app
            # This is a simplified approach - in a real app, you'd pass the auth manager
            # or get this from a global context
            return {
                'user_id': user_id,
                'session_id': session_id,
                'ip_address': ip_address,
                'user_agent': user_agent
            }
        except Exception as e:
            self.logger.warning(f"Could not get full user context: {e}")
            return {
                'user_id': user_id,
                'session_id': None,
                'ip_address': None,
                'user_agent': None
            }
    
    def _log_database_operation(self, user_id: str, event_type: AuditEventType, 
                               table_name: str, record_id: str, 
                               before_data: Optional[Dict] = None, 
                               after_data: Optional[Dict] = None):
        """Log database operation to audit trail"""
        try:
            context = self._get_user_context(user_id)
            self.audit_manager.log_database_operation(
                user_id=user_id,
                event_type=event_type,
                table_name=table_name,
                record_id=record_id,
                before_data=before_data,
                after_data=after_data,
                session_id=context.get('session_id'),
                ip_address=context.get('ip_address'),
                user_agent=context.get('user_agent')
            )
        except Exception as e:
            self.logger.error(f"Failed to log database operation: {e}")
    
    def _log_file_operation(self, user_id: str, event_type: AuditEventType, 
                           file_path: str, file_hash: Optional[str] = None,
                           operation_details: Optional[Dict] = None):
        """Log file operation to audit trail"""
        try:
            context = self._get_user_context(user_id)
            self.audit_manager.log_file_operation(
                user_id=user_id,
                event_type=event_type,
                file_path=file_path,
                file_hash=file_hash,
                operation_details=operation_details,
                session_id=context.get('session_id'),
                ip_address=context.get('ip_address'),
                user_agent=context.get('user_agent')
            )
        except Exception as e:
            self.logger.error(f"Failed to log file operation: {e}")
    
    def _log_audit_event(self, user_id: str, event_type: str, 
                        operation_details: Optional[Dict] = None, **kwargs):
        """Log general audit event"""
        try:
            context = self._get_user_context(user_id)
            self.audit_manager.log_audit_event(
                user_id=user_id,
                event_type=event_type,
                operation_details=operation_details,
                session_id=context.get('session_id'),
                ip_address=context.get('ip_address'),
                user_agent=context.get('user_agent'),
                **kwargs
            )
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
    
    # Enhanced appointment methods with audit logging and soft deletes
    
    def create_appointment(self, patient_name: str, appointment_date: str, 
                          appointment_time: str, user_id: str, **kwargs) -> int:
        """Create a new appointment with audit logging"""
        try:
            # Get current appointment data before creation (for audit)
            before_data = None
            
            # Create the appointment using parent method
            appointment_id = super().create_appointment(
                patient_name, appointment_date, appointment_time, user_id, **kwargs
            )
            
            # Get created appointment data for audit
            appointment = self.get_appointment(appointment_id, user_id)
            after_data = {
                'appointment_id': appointment_id,
                'patient_name': patient_name,
                'appointment_date': appointment_date,
                'appointment_time': appointment_time,
                'appointment_type': kwargs.get('appointment_type'),
                'notes': kwargs.get('notes', '')
            }
            
            # Log audit event
            self._log_database_operation(
                user_id=user_id,
                event_type=AuditEventType.CREATE,
                table_name='appointments',
                record_id=str(appointment_id),
                before_data=before_data,
                after_data=after_data
            )
            
            return appointment_id
            
        except Exception as e:
            self.logger.error(f"Failed to create audited appointment: {e}")
            raise
    
    def get_appointment(self, appointment_id: int, user_id: str) -> Optional[Dict]:
        """Get appointment by ID with audit logging"""
        try:
            # Get appointment using parent method
            appointment = super().get_appointment(appointment_id, user_id)
            
            if appointment:
                # Log read access
                self._log_database_operation(
                    user_id=user_id,
                    event_type=AuditEventType.READ,
                    table_name='appointments',
                    record_id=str(appointment_id),
                    before_data=None,
                    after_data={'patient_name': appointment.get('patient_name', 'Unknown')}
                )
            
            return appointment
            
        except Exception as e:
            self.logger.error(f"Failed to get audited appointment: {e}")
            raise
    
    def get_appointments_by_date(self, date: str, user_id: str = None) -> List[Dict]:
        """Get appointments by date with audit logging"""
        try:
            # Get appointments using parent method
            appointments = super().get_appointments_by_date(date)
            
            # Log access to appointments
            if user_id:
                self._log_database_operation(
                    user_id=user_id,
                    event_type=AuditEventType.READ,
                    table_name='appointments',
                    record_id='date_search',
                    before_data=None,
                    after_data={'date': date, 'count': len(appointments)}
                )
            
            return appointments
            
        except Exception as e:
            self.logger.error(f"Failed to get audited appointments by date: {e}")
            raise
    
    def update_appointment(self, appointment_id: int, user_id: str, **kwargs) -> bool:
        """Update appointment with audit logging and versioning"""
        try:
            # Get current appointment data before update
            current_appointment = self.get_appointment(appointment_id, user_id)
            if not current_appointment:
                return False
            
            before_data = {
                'patient_name': current_appointment.get('patient_name'),
                'appointment_date': current_appointment.get('appointment_date'),
                'appointment_time': current_appointment.get('appointment_time'),
                'appointment_type': current_appointment.get('appointment_type'),
                'notes': current_appointment.get('notes')
            }
            
            # Update using parent method
            success = super().update_appointment(appointment_id, user_id, **kwargs)
            
            if success:
                # Update audit fields
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE appointments 
                        SET updated_at = CURRENT_TIMESTAMP, updated_by = ?
                        WHERE appointment_id = ?
                    """, (user_id, appointment_id))
                    conn.commit()
                
                # Get updated appointment data
                updated_appointment = self.get_appointment(appointment_id, user_id)
                after_data = {
                    'patient_name': updated_appointment.get('patient_name'),
                    'appointment_date': updated_appointment.get('appointment_date'),
                    'appointment_time': updated_appointment.get('appointment_time'),
                    'appointment_type': updated_appointment.get('appointment_type'),
                    'notes': updated_appointment.get('notes')
                }
                
                # Log audit event
                self._log_database_operation(
                    user_id=user_id,
                    event_type=AuditEventType.UPDATE,
                    table_name='appointments',
                    record_id=str(appointment_id),
                    before_data=before_data,
                    after_data=after_data
                )
            
            return success
            
        except Exception as e:
            self.logger.error(f"Failed to update audited appointment: {e}")
            raise
    
    def soft_delete_appointment(self, appointment_id: int, user_id: str, 
                               reason: str = "Soft deleted by user") -> bool:
        """Soft delete an appointment (mark as deleted but keep in database)"""
        try:
            # Get current appointment data
            appointment = self.get_appointment(appointment_id, user_id)
            if not appointment:
                return False
            
            before_data = {
                'patient_name': appointment.get('patient_name'),
                'appointment_date': appointment.get('appointment_date'),
                'appointment_time': appointment.get('appointment_time'),
                'is_deleted': False
            }
            
            # Mark as deleted
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE appointments 
                    SET is_deleted = 1, deleted_at = CURRENT_TIMESTAMP, deleted_by = ?
                    WHERE appointment_id = ?
                """, (user_id, appointment_id))
                conn.commit()
            
            after_data = {
                'patient_name': appointment.get('patient_name'),
                'appointment_date': appointment.get('appointment_date'),
                'appointment_time': appointment.get('appointment_time'),
                'is_deleted': True,
                'deleted_at': datetime.now().isoformat(),
                'deleted_by': user_id
            }
            
            # Log audit event
            self._log_database_operation(
                user_id=user_id,
                event_type=AuditEventType.SOFT_DELETE,
                table_name='appointments',
                record_id=str(appointment_id),
                before_data=before_data,
                after_data=after_data
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to soft delete appointment: {e}")
            raise
    
    def restore_appointment(self, appointment_id: int, user_id: str) -> bool:
        """Restore a soft-deleted appointment"""
        try:
            # Check if appointment exists and is deleted
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM appointments WHERE appointment_id = ? AND is_deleted = 1
                """, (appointment_id,))
                appointment = cursor.fetchone()
                
                if not appointment:
                    return False
                
                # Restore appointment
                cursor.execute("""
                    UPDATE appointments 
                    SET is_deleted = 0, deleted_at = NULL, deleted_by = NULL,
                        updated_at = CURRENT_TIMESTAMP, updated_by = ?
                    WHERE appointment_id = ?
                """, (user_id, appointment_id))
                conn.commit()
            
            # Log audit event
            self._log_database_operation(
                user_id=user_id,
                event_type=AuditEventType.UPDATE,
                table_name='appointments',
                record_id=str(appointment_id),
                before_data={'is_deleted': True},
                after_data={'is_deleted': False, 'restored_by': user_id}
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to restore appointment: {e}")
            raise
    
    def hard_delete_appointment(self, appointment_id: int, user_id: str, 
                               reason: str = "Hard deleted by user") -> bool:
        """Hard delete an appointment (permanently remove from database)"""
        try:
            # Get current appointment data before deletion
            appointment = self.get_appointment(appointment_id, user_id)
            if not appointment:
                return False
            
            before_data = {
                'patient_name': appointment.get('patient_name'),
                'appointment_date': appointment.get('appointment_date'),
                'appointment_time': appointment.get('appointment_time'),
                'appointment_id': appointment_id
            }
            
            # Delete related records first
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Delete file records
                cursor.execute("DELETE FROM files WHERE appointment_id = ?", (appointment_id,))
                
                # Delete processing status records
                cursor.execute("DELETE FROM processing_status WHERE appointment_id = ?", (appointment_id,))
                
                # Delete version history
                cursor.execute("DELETE FROM appointment_versions WHERE appointment_id = ?", (appointment_id,))
                
                # Delete the appointment
                cursor.execute("DELETE FROM appointments WHERE appointment_id = ?", (appointment_id,))
                
                conn.commit()
            
            # Log audit event
            self._log_database_operation(
                user_id=user_id,
                event_type=AuditEventType.DELETE,
                table_name='appointments',
                record_id=str(appointment_id),
                before_data=before_data,
                after_data=None
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to hard delete appointment: {e}")
            raise
    
    # Enhanced file methods with audit logging
    
    def add_file(self, appointment_id: int, file_type: str, file_path: str, 
                 retention_policy: str, user_id: str) -> int:
        """Add a file with audit logging"""
        try:
            # Add file using parent method
            file_id = super().add_file(appointment_id, file_type, file_path, retention_policy, user_id)
            
            # Calculate file hash for audit
            file_hash = self.calculate_file_hash(file_path) if os.path.exists(file_path) else None
            
            # Log file operation
            self._log_file_operation(
                user_id=user_id,
                event_type=AuditEventType.CREATE,
                file_path=file_path,
                file_hash=file_hash,
                operation_details={
                    'file_id': file_id,
                    'appointment_id': appointment_id,
                    'file_type': file_type,
                    'retention_policy': retention_policy
                }
            )
            
            return file_id
            
        except Exception as e:
            self.logger.error(f"Failed to add audited file: {e}")
            raise
    
    def get_appointment_files(self, appointment_id: int, user_id: str) -> List[Dict]:
        """Get appointment files with audit logging"""
        try:
            # Get files using parent method
            files = super().get_appointment_files(appointment_id, user_id)
            
            # Log file access
            for file_record in files:
                self._log_file_operation(
                    user_id=user_id,
                    event_type=AuditEventType.FILE_ACCESS,
                    file_path=file_record.get('file_path', ''),
                    file_hash=file_record.get('file_hash'),
                    operation_details={
                        'file_id': file_record.get('file_id'),
                        'appointment_id': appointment_id,
                        'file_type': file_record.get('file_type')
                    }
                )
            
            return files
            
        except Exception as e:
            self.logger.error(f"Failed to get audited appointment files: {e}")
            raise
    
    def delete_file(self, file_id: int, user_id: str, 
                   reason: str = "Deleted by user") -> bool:
        """
        Delete a file (defaults to hard delete to free up disk space)
        
        This method removes the physical file and database record while
        preserving the audit trail. This is the recommended method for
        file deletion to prevent disk space issues.
        
        Args:
            file_id: ID of the file to delete
            user_id: ID of the user performing the deletion
            reason: Reason for deletion
        
        Returns:
            bool: True if deletion was successful
        """
        return self.hard_delete_file(file_id, user_id, reason)
    
    def soft_delete_file(self, file_id: int, user_id: str, 
                        reason: str = "Soft deleted by user") -> bool:
        """
        Soft delete a file record (deprecated - use delete_file instead)
        
        Note: For files, we recommend using delete_file (hard delete) to free up disk space
        while preserving audit logs. This method is kept for compatibility.
        """
        self.logger.warning("soft_delete_file is deprecated for files. Use delete_file instead.")
        return self.hard_delete_file(file_id, user_id, reason)
    
    def hard_delete_file(self, file_id: int, user_id: str, 
                        reason: str = "Hard deleted by user") -> bool:
        """Hard delete a file record and physical file"""
        try:
            # Get current file data
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
                file_record = cursor.fetchone()
                
                if not file_record:
                    return False
                
                before_data = dict(file_record)
                file_path = file_record['file_path']
                
                # Delete physical file if it exists
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        self._log_file_operation(
                            user_id=user_id,
                            event_type=AuditEventType.FILE_DELETE,
                            file_path=file_path,
                            operation_details={'reason': reason}
                        )
                    except Exception as e:
                        self.logger.warning(f"Failed to delete physical file {file_path}: {e}")
                
                # Delete version history
                cursor.execute("DELETE FROM file_versions WHERE file_id = ?", (file_id,))
                
                # Delete file record
                cursor.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
                
                conn.commit()
            
            # Log audit event
            self._log_database_operation(
                user_id=user_id,
                event_type=AuditEventType.DELETE,
                table_name='files',
                record_id=str(file_id),
                before_data=before_data,
                after_data=None
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to hard delete file: {e}")
            raise
    
    # Version history methods
    
    def get_appointment_version_history(self, appointment_id: int, user_id: str) -> List[Dict]:
        """Get version history for an appointment"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM appointment_versions 
                    WHERE appointment_id = ? 
                    ORDER BY version_number DESC
                """, (appointment_id,))
                
                versions = [dict(row) for row in cursor.fetchall()]
                
                # Log access to version history
                self._log_database_operation(
                    user_id=user_id,
                    event_type=AuditEventType.READ,
                    table_name='appointment_versions',
                    record_id=str(appointment_id),
                    before_data=None,
                    after_data={'version_count': len(versions)}
                )
                
                return versions
                
        except Exception as e:
            self.logger.error(f"Failed to get appointment version history: {e}")
            raise
    
    def get_file_version_history(self, file_id: int, user_id: str) -> List[Dict]:
        """Get version history for a file"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM file_versions 
                    WHERE file_id = ? 
                    ORDER BY version_number DESC
                """, (file_id,))
                
                versions = [dict(row) for row in cursor.fetchall()]
                
                # Log access to version history
                self._log_database_operation(
                    user_id=user_id,
                    event_type=AuditEventType.READ,
                    table_name='file_versions',
                    record_id=str(file_id),
                    before_data=None,
                    after_data={'version_count': len(versions)}
                )
                
                return versions
                
        except Exception as e:
            self.logger.error(f"Failed to get file version history: {e}")
            raise
    
    # Audit and compliance methods
    
    def get_audit_log(self, **kwargs) -> List[Dict]:
        """Get audit log entries"""
        return self.audit_manager.get_audit_log(**kwargs)
    
    def verify_audit_integrity(self) -> Dict[str, Any]:
        """Verify audit log integrity"""
        return self.audit_manager.verify_audit_integrity()
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """Get audit statistics"""
        return self.audit_manager.get_audit_statistics()
    
    def export_audit_log(self, output_path: str, **kwargs) -> Dict[str, Any]:
        """Export audit log"""
        return self.audit_manager.export_audit_log(output_path, **kwargs)
    
    def cleanup_old_audit_logs(self) -> Dict[str, Any]:
        """Clean up old audit logs"""
        return self.audit_manager.cleanup_old_audit_logs()
    
    def cleanup_old_files(self, retention_years: int = 7, user_id: str = "system") -> Dict[str, Any]:
        """
        Clean up old files while preserving audit logs
        
        This method removes physical files and their database records for files
        older than the retention period, but preserves the audit trail.
        
        Args:
            retention_years: Number of years to retain files (default: 7)
            user_id: User ID for audit logging (default: "system")
        
        Returns:
            Dict containing cleanup results
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_years * 365)
            files_cleaned = 0
            files_failed = 0
            total_size_freed = 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get files older than retention period
                cursor.execute("""
                    SELECT file_id, file_path, file_size, appointment_id, created_date
                    FROM files 
                    WHERE created_date < ? AND is_deleted = 0
                """, (cutoff_date.isoformat(),))
                
                old_files = cursor.fetchall()
                
                for file_record in old_files:
                    file_id = file_record['file_id']
                    file_path = file_record['file_path']
                    file_size = file_record['file_size'] or 0
                    
                    try:
                        # Log the cleanup operation before deletion
                        self._log_file_operation(
                            user_id=user_id,
                            event_type=AuditEventType.FILE_DELETE,
                            file_path=file_path,
                            operation_details={
                                'reason': f'Cleanup: file older than {retention_years} years',
                                'retention_policy': f'{retention_years} years',
                                'file_age_days': (datetime.now() - datetime.fromisoformat(file_record['created_date'])).days
                            }
                        )
                        
                        # Delete physical file if it exists
                        if os.path.exists(file_path):
                            os.remove(file_path)
                            total_size_freed += file_size
                        
                        # Delete file record from database
                        cursor.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
                        
                        # Delete associated version history
                        cursor.execute("DELETE FROM file_versions WHERE file_id = ?", (file_id,))
                        
                        files_cleaned += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to cleanup file {file_path}: {e}")
                        files_failed += 1
                
                conn.commit()
            
            # Log the cleanup operation
            self._log_audit_event(
                user_id=user_id,
                event_type=AuditEventType.SYSTEM_EVENT,
                operation_details={
                    'operation': 'file_cleanup',
                    'retention_years': retention_years,
                    'files_cleaned': files_cleaned,
                    'files_failed': files_failed,
                    'total_size_freed_bytes': total_size_freed,
                    'cutoff_date': cutoff_date.isoformat()
                }
            )
            
            return {
                'success': True,
                'files_cleaned': files_cleaned,
                'files_failed': files_failed,
                'total_size_freed_bytes': total_size_freed,
                'retention_years': retention_years,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old files: {e}")
            return {
                'success': False,
                'error': str(e),
                'files_cleaned': 0,
                'files_failed': 0,
                'total_size_freed_bytes': 0
            }
    
    def cleanup_old_appointments(self, retention_years: int = 7, user_id: str = "system") -> Dict[str, Any]:
        """
        Clean up old soft-deleted appointments while preserving audit logs
        
        This method removes soft-deleted appointments older than the retention period,
        but preserves the audit trail.
        
        Args:
            retention_years: Number of years to retain soft-deleted appointments (default: 7)
            user_id: User ID for audit logging (default: "system")
        
        Returns:
            Dict containing cleanup results
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_years * 365)
            appointments_cleaned = 0
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get soft-deleted appointments older than retention period
                cursor.execute("""
                    SELECT appointment_id, patient_name, deleted_at
                    FROM appointments 
                    WHERE is_deleted = 1 AND deleted_at < ?
                """, (cutoff_date.isoformat(),))
                
                old_appointments = cursor.fetchall()
                
                for appointment_record in old_appointments:
                    appointment_id = appointment_record['appointment_id']
                    
                    try:
                        # Log the cleanup operation before deletion
                        self._log_database_operation(
                            user_id=user_id,
                            event_type=AuditEventType.HARD_DELETE,
                            table_name='appointments',
                            record_id=str(appointment_id),
                            operation_details={
                                'reason': f'Cleanup: soft-deleted appointment older than {retention_years} years',
                                'retention_policy': f'{retention_years} years',
                                'patient_name': appointment_record['patient_name']
                            }
                        )
                        
                        # Delete appointment record from database
                        cursor.execute("DELETE FROM appointments WHERE appointment_id = ?", (appointment_id,))
                        
                        # Delete associated version history
                        cursor.execute("DELETE FROM appointment_versions WHERE appointment_id = ?", (appointment_id,))
                        
                        appointments_cleaned += 1
                        
                    except Exception as e:
                        self.logger.error(f"Failed to cleanup appointment {appointment_id}: {e}")
                
                conn.commit()
            
            # Log the cleanup operation
            self._log_audit_event(
                user_id=user_id,
                event_type=AuditEventType.SYSTEM_EVENT,
                operation_details={
                    'operation': 'appointment_cleanup',
                    'retention_years': retention_years,
                    'appointments_cleaned': appointments_cleaned,
                    'cutoff_date': cutoff_date.isoformat()
                }
            )
            
            return {
                'success': True,
                'appointments_cleaned': appointments_cleaned,
                'retention_years': retention_years,
                'cutoff_date': cutoff_date.isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to cleanup old appointments: {e}")
            return {
                'success': False,
                'error': str(e),
                'appointments_cleaned': 0
            }
    
    def comprehensive_cleanup(self, retention_years: int = 7, user_id: str = "system") -> Dict[str, Any]:
        """
        Perform comprehensive cleanup of old data while preserving audit logs
        
        This method cleans up:
        - Old files (physical files and database records)
        - Old soft-deleted appointments
        - Old audit logs (with backup)
        
        Args:
            retention_years: Number of years to retain data (default: 7)
            user_id: User ID for audit logging (default: "system")
        
        Returns:
            Dict containing comprehensive cleanup results
        """
        try:
            # Perform all cleanup operations
            file_cleanup = self.cleanup_old_files(retention_years, user_id)
            appointment_cleanup = self.cleanup_old_appointments(retention_years, user_id)
            audit_cleanup = self.cleanup_old_audit_logs()
            
            # Log comprehensive cleanup operation
            self._log_audit_event(
                user_id=user_id,
                event_type=AuditEventType.SYSTEM_EVENT,
                operation_details={
                    'operation': 'comprehensive_cleanup',
                    'retention_years': retention_years,
                    'file_cleanup': file_cleanup,
                    'appointment_cleanup': appointment_cleanup,
                    'audit_cleanup': audit_cleanup
                }
            )
            
            return {
                'success': True,
                'retention_years': retention_years,
                'file_cleanup': file_cleanup,
                'appointment_cleanup': appointment_cleanup,
                'audit_cleanup': audit_cleanup,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Failed to perform comprehensive cleanup: {e}")
            return {
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    # Search methods that respect soft deletes
    
    def search_appointments_by_patient(self, patient_name: str, user_id: str, 
                                     include_deleted: bool = False) -> List[Dict]:
        """Search appointments by patient name, optionally including deleted ones"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build query with soft delete filter
                if include_deleted:
                    where_clause = "WHERE (patient_name LIKE ? OR patient_name_encrypted LIKE ?)"
                    params = [f"%{patient_name}%", f"%{patient_name}%"]
                else:
                    where_clause = "WHERE (patient_name LIKE ? OR patient_name_encrypted LIKE ?) AND is_deleted = 0"
                    params = [f"%{patient_name}%", f"%{patient_name}%"]
                
                cursor.execute(f"""
                    SELECT * FROM appointments 
                    {where_clause}
                    ORDER BY appointment_date DESC, appointment_time DESC
                """, params)
                
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
                
                # Log search operation
                self._log_database_operation(
                    user_id=user_id,
                    event_type=AuditEventType.READ,
                    table_name='appointments',
                    record_id='search',
                    before_data=None,
                    after_data={
                        'search_term': patient_name,
                        'results_count': len(appointments),
                        'include_deleted': include_deleted
                    }
                )
                
                return appointments
                
        except Exception as e:
            self.logger.error(f"Failed to search audited appointments: {e}")
            raise
