#!/usr/bin/env python3
"""
Encryption Migration Script for Physiotherapy Clinic Assistant
Migrates existing unencrypted data to encrypted format
"""

import os
import sys
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from database_manager import DatabaseManager
from encrypted_database_manager import EncryptedDatabaseManager
from file_encryption_service import FileEncryptionService
from encryption_manager import get_encryption_manager


class EncryptionMigration:
    """Handles migration of existing data to encrypted format"""
    
    def __init__(self, db_path: str = "data/clinic_data.db"):
        self.db_path = db_path
        self.old_db_manager = DatabaseManager(db_path)
        self.new_db_manager = EncryptedDatabaseManager(db_path)
        self.encryption_service = FileEncryptionService(self.new_db_manager)
        self.encryption_manager = get_encryption_manager()
        
        # Setup logging with rotation
        from logging.handlers import RotatingFileHandler
        
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler with rotation (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            'logs/encryption_migration.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def check_migration_status(self) -> Dict[str, Any]:
        """Check the current migration status"""
        try:
            with self.new_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if encryption schema exists
                cursor.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='audit_log'
                """)
                has_audit_table = cursor.fetchone() is not None
                
                # Check encryption status
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_appointments,
                        SUM(CASE WHEN is_encrypted = 1 THEN 1 ELSE 0 END) as encrypted_appointments,
                        SUM(CASE WHEN is_encrypted = 0 OR is_encrypted IS NULL THEN 1 ELSE 0 END) as unencrypted_appointments
                    FROM appointments
                """)
                appointment_stats = cursor.fetchone()
                
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_files,
                        SUM(CASE WHEN is_encrypted = 1 THEN 1 ELSE 0 END) as encrypted_files,
                        SUM(CASE WHEN is_encrypted = 0 OR is_encrypted IS NULL THEN 1 ELSE 0 END) as unencrypted_files
                    FROM files
                """)
                file_stats = cursor.fetchone()
                
                return {
                    'migration_ready': has_audit_table,
                    'appointments': dict(appointment_stats),
                    'files': dict(file_stats),
                    'encryption_keys': self.encryption_manager.get_key_info(),
                    'timestamp': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to check migration status: {e}")
            return {'error': str(e)}
    
    def migrate_appointments(self, user_id: str = "migration_user") -> Dict[str, Any]:
        """Migrate appointments to encrypted format"""
        try:
            self.logger.info("Starting appointment migration...")
            
            # Get all appointments from old format
            with self.old_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM appointments")
                old_appointments = cursor.fetchall()
            
            results = {
                'success': True,
                'total_appointments': len(old_appointments),
                'migrated_appointments': 0,
                'failed_appointments': 0,
                'details': []
            }
            
            for appointment in old_appointments:
                try:
                    appointment_data = dict(appointment)
                    
                    # Create new encrypted appointment
                    new_appointment_id = self.new_db_manager.create_appointment(
                        patient_name=appointment_data['patient_name'],
                        appointment_date=appointment_data['appointment_date'],
                        appointment_time=appointment_data['appointment_time'],
                        user_id=user_id,
                        appointment_type=appointment_data.get('appointment_type'),
                        notes=appointment_data.get('notes', '')
                    )
                    
                    results['migrated_appointments'] += 1
                    results['details'].append({
                        'old_id': appointment_data['appointment_id'],
                        'new_id': new_appointment_id,
                        'patient_name': appointment_data['patient_name'],
                        'status': 'migrated'
                    })
                    
                    self.logger.info(f"Migrated appointment: {appointment_data['patient_name']}")
                    
                except Exception as e:
                    results['failed_appointments'] += 1
                    results['details'].append({
                        'old_id': appointment_data['appointment_id'],
                        'patient_name': appointment_data['patient_name'],
                        'status': 'failed',
                        'error': str(e)
                    })
                    self.logger.error(f"Failed to migrate appointment {appointment_data['appointment_id']}: {e}")
            
            # Update overall success
            if results['failed_appointments'] > 0:
                results['success'] = False
                results['message'] = f"Migrated {results['migrated_appointments']} appointments, {results['failed_appointments']} failed"
            else:
                results['message'] = f"Successfully migrated {results['migrated_appointments']} appointments"
            
            self.logger.info(f"Appointment migration completed: {results['message']}")
            return results
            
        except Exception as e:
            self.logger.error(f"Appointment migration failed: {e}")
            return {
                'success': False,
                'message': f'Appointment migration failed: {str(e)}',
                'total_appointments': 0,
                'migrated_appointments': 0,
                'failed_appointments': 0
            }
    
    def migrate_files(self, user_id: str = "migration_user", batch_size: int = 50) -> Dict[str, Any]:
        """Migrate files to encrypted format"""
        try:
            self.logger.info("Starting file migration...")
            
            # Get all files from old format
            with self.old_db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT f.*, a.patient_name 
                    FROM files f
                    JOIN appointments a ON f.appointment_id = a.appointment_id
                    WHERE f.is_deleted = 0
                """)
                old_files = cursor.fetchall()
            
            results = {
                'success': True,
                'total_files': len(old_files),
                'migrated_files': 0,
                'failed_files': 0,
                'skipped_files': 0,
                'details': []
            }
            
            # Process files in batches
            for i in range(0, len(old_files), batch_size):
                batch = old_files[i:i + batch_size]
                self.logger.info(f"Processing file batch {i//batch_size + 1}/{(len(old_files) + batch_size - 1)//batch_size}")
                
                for file_record in batch:
                    try:
                        file_data = dict(file_record)
                        file_path = file_data['file_path']
                        
                        # Check if file exists
                        if not os.path.exists(file_path):
                            results['skipped_files'] += 1
                            results['details'].append({
                                'file_id': file_data['file_id'],
                                'file_path': file_path,
                                'status': 'skipped',
                                'reason': 'File not found'
                            })
                            continue
                        
                        # Find corresponding new appointment
                        # This is a simplified approach - in practice, you'd need better mapping
                        new_appointments = self.new_db_manager.search_appointments_by_patient(
                            file_data['patient_name'], user_id
                        )
                        
                        if not new_appointments:
                            results['skipped_files'] += 1
                            results['details'].append({
                                'file_id': file_data['file_id'],
                                'file_path': file_path,
                                'status': 'skipped',
                                'reason': 'No corresponding appointment found'
                            })
                            continue
                        
                        # Use the first matching appointment
                        new_appointment = new_appointments[0]
                        
                        # Add file to new database
                        new_file_id = self.new_db_manager.add_file(
                            appointment_id=new_appointment['appointment_id'],
                            file_type=file_data['file_type'],
                            file_path=file_path,
                            retention_policy=file_data['retention_policy'],
                            user_id=user_id
                        )
                        
                        # Encrypt the file
                        encrypt_result = self.encryption_service.encrypt_patient_file(
                            file_path, user_id, new_appointment['appointment_id']
                        )
                        
                        if encrypt_result['success']:
                            results['migrated_files'] += 1
                            results['details'].append({
                                'old_file_id': file_data['file_id'],
                                'new_file_id': new_file_id,
                                'file_path': file_path,
                                'encrypted_path': encrypt_result['encrypted_path'],
                                'status': 'migrated'
                            })
                        else:
                            results['failed_files'] += 1
                            results['details'].append({
                                'old_file_id': file_data['file_id'],
                                'file_path': file_path,
                                'status': 'failed',
                                'error': encrypt_result['message']
                            })
                        
                    except Exception as e:
                        results['failed_files'] += 1
                        results['details'].append({
                            'old_file_id': file_data['file_id'],
                            'file_path': file_data['file_path'],
                            'status': 'failed',
                            'error': str(e)
                        })
                        self.logger.error(f"Failed to migrate file {file_data['file_id']}: {e}")
            
            # Update overall success
            if results['failed_files'] > 0:
                results['success'] = False
                results['message'] = f"Migrated {results['migrated_files']} files, {results['failed_files']} failed, {results['skipped_files']} skipped"
            else:
                results['message'] = f"Successfully migrated {results['migrated_files']} files, {results['skipped_files']} skipped"
            
            self.logger.info(f"File migration completed: {results['message']}")
            return results
            
        except Exception as e:
            self.logger.error(f"File migration failed: {e}")
            return {
                'success': False,
                'message': f'File migration failed: {str(e)}',
                'total_files': 0,
                'migrated_files': 0,
                'failed_files': 0
            }
    
    def create_migration_backup(self, backup_path: str) -> Dict[str, Any]:
        """Create a backup before migration"""
        try:
            self.logger.info(f"Creating migration backup: {backup_path}")
            
            # Create backup directory
            backup_dir = Path(backup_path)
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup database
            import shutil
            db_backup_path = backup_dir / "clinic_data_backup.db"
            shutil.copy2(self.db_path, db_backup_path)
            
            # Backup data directory
            data_backup_path = backup_dir / "data_backup"
            if os.path.exists("data"):
                shutil.copytree("data", data_backup_path, dirs_exist_ok=True)
                # Remove the database file from data backup
                if (data_backup_path / "clinic_data.db").exists():
                    (data_backup_path / "clinic_data.db").unlink()
            
            # Create backup metadata
            backup_metadata = {
                'backup_created': datetime.now().isoformat(),
                'database_path': self.db_path,
                'backup_type': 'migration_backup',
                'version': '1.0'
            }
            
            with open(backup_dir / "backup_metadata.json", 'w') as f:
                json.dump(backup_metadata, f, indent=2)
            
            self.logger.info(f"Migration backup created: {backup_path}")
            return {
                'success': True,
                'message': f'Migration backup created: {backup_path}',
                'backup_path': str(backup_dir),
                'database_backup': str(db_backup_path),
                'data_backup': str(data_backup_path)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to create migration backup: {e}")
            return {
                'success': False,
                'message': f'Backup creation failed: {str(e)}'
            }
    
    def run_full_migration(self, user_id: str = "migration_user", 
                          create_backup: bool = True) -> Dict[str, Any]:
        """Run the complete migration process"""
        try:
            self.logger.info("Starting full encryption migration...")
            
            migration_results = {
                'success': True,
                'started_at': datetime.now().isoformat(),
                'backup_created': False,
                'appointments_migrated': False,
                'files_migrated': False,
                'details': {}
            }
            
            # Step 1: Create backup if requested
            if create_backup:
                backup_result = self.create_migration_backup(f"migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
                migration_results['backup_created'] = backup_result['success']
                migration_results['details']['backup'] = backup_result
                
                if not backup_result['success']:
                    migration_results['success'] = False
                    migration_results['message'] = 'Migration aborted: Backup creation failed'
                    return migration_results
            
            # Step 2: Migrate appointments
            appointment_result = self.migrate_appointments(user_id)
            migration_results['appointments_migrated'] = appointment_result['success']
            migration_results['details']['appointments'] = appointment_result
            
            if not appointment_result['success']:
                migration_results['success'] = False
                migration_results['message'] = 'Migration failed: Appointment migration failed'
                return migration_results
            
            # Step 3: Migrate files
            file_result = self.migrate_files(user_id)
            migration_results['files_migrated'] = file_result['success']
            migration_results['details']['files'] = file_result
            
            if not file_result['success']:
                migration_results['success'] = False
                migration_results['message'] = 'Migration failed: File migration failed'
                return migration_results
            
            # Step 4: Verify migration
            verification_result = self.verify_migration()
            migration_results['details']['verification'] = verification_result
            
            migration_results['completed_at'] = datetime.now().isoformat()
            migration_results['message'] = 'Migration completed successfully'
            
            self.logger.info("Full encryption migration completed successfully")
            return migration_results
            
        except Exception as e:
            self.logger.error(f"Full migration failed: {e}")
            return {
                'success': False,
                'message': f'Full migration failed: {str(e)}',
                'started_at': datetime.now().isoformat(),
                'completed_at': datetime.now().isoformat()
            }
    
    def verify_migration(self) -> Dict[str, Any]:
        """Verify that migration was successful"""
        try:
            # Check encryption status
            encryption_status = self.new_db_manager.get_encryption_status()
            
            # Check audit log
            audit_log = self.new_db_manager.get_audit_log(limit=10)
            
            # Verify file encryption
            file_encryption_status = self.encryption_service.get_encryption_status()
            
            return {
                'success': True,
                'encryption_status': encryption_status,
                'audit_log_entries': len(audit_log),
                'file_encryption_status': file_encryption_status,
                'verification_timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Migration verification failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def main():
    """Main migration script"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Encryption Migration Script')
    parser.add_argument('--action', choices=['check', 'migrate', 'backup'], 
                       default='check', help='Action to perform')
    parser.add_argument('--user-id', default='migration_user', 
                       help='User ID for migration')
    parser.add_argument('--backup', action='store_true', 
                       help='Create backup before migration')
    parser.add_argument('--db-path', default='data/clinic_data.db', 
                       help='Database path')
    
    args = parser.parse_args()
    
    # Initialize migration
    migration = EncryptionMigration(args.db_path)
    
    if args.action == 'check':
        # Check migration status
        status = migration.check_migration_status()
        print(json.dumps(status, indent=2))
        
    elif args.action == 'backup':
        # Create backup
        backup_result = migration.create_migration_backup(
            f"migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        print(json.dumps(backup_result, indent=2))
        
    elif args.action == 'migrate':
        # Run full migration
        migration_result = migration.run_full_migration(
            user_id=args.user_id,
            create_backup=args.backup
        )
        print(json.dumps(migration_result, indent=2))


if __name__ == '__main__':
    main()
