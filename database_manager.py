#!/usr/bin/env python3
"""
Database Manager for Physiotherapy Clinic Assistant
Handles SQLite database operations for patient data, appointments, and file management
"""

import sqlite3
import os
import sys
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import shutil
import zipfile
import tempfile
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import secrets

# Import path helper for proper writable locations
try:
    from app_paths import get_database_path
except ImportError:
    # Fallback if app_paths not available
    def get_database_path() -> Path:
        """Fallback function for getting database path"""
        app_name = "PhysioClinicAssistant"
        if sys.platform == 'darwin':
            base_path = Path.home() / "Library" / "Application Support" / app_name
        else:
            base_path = Path.home() / ".local" / "share" / app_name
        base_path.mkdir(parents=True, exist_ok=True)
        data_dir = base_path / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "clinic_data.db"


class DatabaseManager:
    def __init__(self, db_path: Optional[str] = None):
        """Initialize database manager"""
        # Use proper writable database path
        if db_path is None:
            self.db_path = str(get_database_path())
        else:
            self.db_path = db_path
        self.ensure_data_directory()
        self.init_database()
        self.load_default_settings()
    
    def ensure_data_directory(self):
        """Ensure data directory exists"""
        directory = os.path.dirname(self.db_path)
        if directory:  # Only create directory if there is a path
            os.makedirs(directory, exist_ok=True)
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn
    
    def init_database(self):
        """Initialize database with all tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create tables
            cursor.executescript("""
                -- 1. APPOINTMENTS TABLE (appointment-centric)
                CREATE TABLE IF NOT EXISTS appointments (
                    appointment_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    appointment_code VARCHAR(50) UNIQUE NOT NULL,
                    patient_name VARCHAR(100) NOT NULL,
                    appointment_date DATE NOT NULL,
                    appointment_time TIME NOT NULL,
                    appointment_type VARCHAR(50),
                    notes TEXT,
                    folder_path VARCHAR(500) NOT NULL,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- 3. FILES TABLE
                CREATE TABLE IF NOT EXISTS files (
                    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    appointment_id INTEGER NOT NULL,
                    file_type VARCHAR(20) NOT NULL,
                    file_path VARCHAR(500) NOT NULL,
                    file_size INTEGER,
                    file_hash VARCHAR(64),
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retention_policy VARCHAR(20) NOT NULL,
                    retention_date DATE NOT NULL,
                    is_deleted BOOLEAN DEFAULT 0,
                    deletion_date TIMESTAMP,
                    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
                );

                -- 4. PROCESSING_STATUS TABLE
                CREATE TABLE IF NOT EXISTS processing_status (
                    status_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    appointment_id INTEGER NOT NULL,
                    step_name VARCHAR(50) NOT NULL,
                    status VARCHAR(20) NOT NULL,
                    start_time TIMESTAMP,
                    end_time TIMESTAMP,
                    error_message TEXT,
                    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (appointment_id) REFERENCES appointments(appointment_id)
                );

                -- 5. SETTINGS TABLE
                CREATE TABLE IF NOT EXISTS settings (
                    setting_key VARCHAR(100) PRIMARY KEY,
                    setting_value TEXT,
                    setting_type VARCHAR(20) DEFAULT 'string',
                    description TEXT,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );

                -- 6. CLEANUP_LOG TABLE
                CREATE TABLE IF NOT EXISTS cleanup_log (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    cleanup_type VARCHAR(50) NOT NULL,
                    files_deleted INTEGER DEFAULT 0,
                    space_freed INTEGER DEFAULT 0,
                    retention_policy VARCHAR(20),
                    cleanup_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                );
            """)
            
            # Create indexes
            cursor.executescript("""
                CREATE INDEX IF NOT EXISTS idx_appointments_patient_date 
                ON appointments(patient_name, appointment_date);
                
                CREATE INDEX IF NOT EXISTS idx_appointments_code 
                ON appointments(appointment_code);
                
                CREATE INDEX IF NOT EXISTS idx_appointments_date 
                ON appointments(appointment_date);
                
                CREATE INDEX IF NOT EXISTS idx_files_appointment_type 
                ON files(appointment_id, file_type);
                
                CREATE INDEX IF NOT EXISTS idx_files_retention_date 
                ON files(retention_date) WHERE is_deleted = 0;
                
                CREATE INDEX IF NOT EXISTS idx_files_policy 
                ON files(retention_policy, retention_date) WHERE is_deleted = 0;
                
                CREATE INDEX IF NOT EXISTS idx_processing_status_appointment 
                ON processing_status(appointment_id, step_name);
                

            """)
            
            # Create views
            cursor.executescript("""
                CREATE VIEW IF NOT EXISTS files_for_cleanup AS
                SELECT 
                    f.file_id,
                    f.appointment_id,
                    f.file_type,
                    f.file_path,
                    f.retention_policy,
                    f.retention_date,
                    a.appointment_code,
                    a.patient_name
                FROM files f
                JOIN appointments a ON f.appointment_id = a.appointment_id
                WHERE f.is_deleted = 0 
                AND f.retention_date <= date('now');

                CREATE VIEW IF NOT EXISTS appointment_summary AS
                SELECT 
                    a.appointment_id,
                    a.appointment_code,
                    a.appointment_date,
                    a.appointment_time,
                    a.patient_name,
                    a.appointment_type,
                    COUNT(CASE WHEN f.file_type = 'recording' THEN 1 END) as has_recording,
                    COUNT(CASE WHEN f.file_type = 'transcript' THEN 1 END) as has_transcript,
                    COUNT(CASE WHEN f.file_type = 'wsib_form' THEN 1 END) as has_wsib_form,
                    COUNT(CASE WHEN f.file_type = 'ocf18_form' THEN 1 END) as has_ocf18_form,
                    COUNT(CASE WHEN f.file_type = 'ocf23_form' THEN 1 END) as has_ocf23_form,
                    SUM(f.file_size) as total_size
                FROM appointments a
                LEFT JOIN files f ON a.appointment_id = f.appointment_id AND f.is_deleted = 0
                GROUP BY a.appointment_id;
            """)
            
            conn.commit()
    
    def load_default_settings(self):
        """Load default application settings"""
        default_settings = {
            'audio_retention_days': ('14', 'integer', 'How long to keep audio recordings'),
            'text_retention_days': ('30', 'integer', 'How long to keep text files'),
            'auto_cleanup_enabled': ('true', 'boolean', 'Enable automatic file cleanup'),
            'max_recording_duration': ('1800', 'integer', 'Max recording time in seconds'),
            'audio_quality': ('high', 'string', 'Audio recording quality setting'),

            'cleanup_frequency_hours': ('24', 'integer', 'How often to run cleanup (hours)'),
            'max_storage_gb': ('10', 'integer', 'Maximum storage usage in GB'),
            'backup_enabled': ('false', 'boolean', 'Enable local backup of data')
        }
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            for key, (value, value_type, description) in default_settings.items():
                cursor.execute("""
                    INSERT OR IGNORE INTO settings (setting_key, setting_value, setting_type, description)
                    VALUES (?, ?, ?, ?)
                """, (key, value, value_type, description))
            conn.commit()
    
    # Appointment Management Methods (appointment-centric)
    def create_appointment(self, patient_name: str, appointment_date: str, appointment_time: str, user_id: str, **kwargs) -> int:
        """Create a new appointment and return appointment_id"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Generate appointment code and folder path
            date_str = appointment_date.replace('-', '')
            time_str = appointment_time.replace(':', '')
            
            # Add microseconds to ensure uniqueness
            import time
            microseconds = int(time.time() * 1000000) % 1000000  # Get microseconds
            appointment_code = f"{date_str}_{time_str}_{microseconds:06d}"
            
            # Create folder path in writable location: ~/Library/Application Support/.../data/YYYY-MM-DD/PatientName_HHMMSS/
            safe_patient_name = patient_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
            try:
                from app_paths import get_writable_path
                folder_path = str(get_writable_path(f"data/{appointment_date}/{safe_patient_name}_{appointment_time}"))
            except ImportError:
                folder_path = f"data/{appointment_date}/{safe_patient_name}_{appointment_time}"
            
            cursor.execute("""
                INSERT INTO appointments (appointment_code, patient_name, appointment_date, appointment_time, 
                                        appointment_type, notes, folder_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (appointment_code, patient_name, appointment_date, appointment_time,
                  kwargs.get('appointment_type'), kwargs.get('notes'), folder_path))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_appointment(self, appointment_id: int) -> Optional[Dict]:
        """Get appointment by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM appointments WHERE appointment_id = ?", (appointment_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_appointments_by_date(self, date: str) -> List[Dict]:
        """Get all appointments for a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM appointments 
                WHERE appointment_date = ? 
                ORDER BY appointment_time ASC
            """, (date,))
            return [dict(row) for row in cursor.fetchall()]
    
    def search_appointments_by_patient(self, patient_name: str) -> List[Dict]:
        """Search appointments by patient name"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM appointments 
                WHERE patient_name LIKE ? 
                ORDER BY appointment_date DESC, appointment_time DESC
            """, (f"%{patient_name}%",))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_appointments(self, limit: int = 10) -> List[Dict]:
        """Get recent appointments"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM appointments 
                ORDER BY appointment_date DESC, appointment_time DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def ensure_date_folder_exists(self, appointment_date: str) -> str:
        """Ensure the date folder exists and return the path"""
        try:
            from app_paths import get_writable_path
            date_folder = str(get_writable_path(f"data/{appointment_date}"))
        except ImportError:
            date_folder = f"data/{appointment_date}"
            os.makedirs(date_folder, exist_ok=True)
        return date_folder
    
    def get_date_folders(self) -> List[str]:
        """Get all date folders that exist"""
        if not os.path.exists("data"):
            return []
        
        date_folders = []
        for item in os.listdir("data"):
            item_path = os.path.join("data", item)
            if os.path.isdir(item_path) and len(item) == 10 and item.count('-') == 2:  # YYYY-MM-DD format
                date_folders.append(item)
        
        return sorted(date_folders, reverse=True)  # Most recent first
    
    def get_appointments_by_date_folder(self, date_folder: str) -> List[Dict]:
        """Get all appointments for a specific date folder"""
        return self.get_appointments_by_date(date_folder)
    
    def cleanup_empty_date_folders(self):
        """Remove empty date folders and patient folders"""
        if not os.path.exists("data"):
            return
        
        for item in os.listdir("data"):
            item_path = os.path.join("data", item)
            if os.path.isdir(item_path) and item != "clinic_data.db":
                # First, clean up empty patient folders within this date folder
                self._cleanup_empty_patient_folders(item_path)
                
                # Then check if the date folder itself is empty
                if not os.listdir(item_path):
                    try:
                        os.rmdir(item_path)
                        print(f"Removed empty date folder: {item_path}")
                    except Exception as e:
                        print(f"Could not remove folder {item_path}: {e}")
    
    def _cleanup_empty_patient_folders(self, date_folder_path: str):
        """Remove empty patient folders within a date folder"""
        removed_folders = []
        
        if not os.path.exists(date_folder_path):
            return removed_folders
        
        for patient_folder in os.listdir(date_folder_path):
            patient_folder_path = os.path.join(date_folder_path, patient_folder)
            if os.path.isdir(patient_folder_path):
                # Check if patient folder is empty
                if not os.listdir(patient_folder_path):
                    try:
                        os.rmdir(patient_folder_path)
                        removed_folders.append(patient_folder_path)
                        print(f"Removed empty patient folder: {patient_folder_path}")
                    except Exception as e:
                        print(f"Could not remove patient folder {patient_folder_path}: {e}")
        
        return removed_folders
    
    def cleanup_all_empty_folders(self) -> Dict:
        """Clean up all empty folders in the data directory"""
        try:
            removed_folders = []
            
            if not os.path.exists("data"):
                return {'success': True, 'removed_folders': removed_folders, 'message': 'No data directory found'}
            
            # Clean up all date folders
            for item in os.listdir("data"):
                item_path = os.path.join("data", item)
                if os.path.isdir(item_path) and item != "clinic_data.db":
                    # First, clean up empty patient folders within this date folder
                    patient_folders_removed = self._cleanup_empty_patient_folders(item_path)
                    removed_folders.extend(patient_folders_removed)
                    
                    # Then check if the date folder itself is empty
                    if not os.listdir(item_path):
                        try:
                            os.rmdir(item_path)
                            removed_folders.append(item_path)
                            print(f"Removed empty date folder: {item_path}")
                        except Exception as e:
                            print(f"Could not remove folder {item_path}: {e}")
            
            return {
                'success': True,
                'removed_folders': removed_folders,
                'count': len(removed_folders),
                'message': f'Cleaned up {len(removed_folders)} empty folders'
            }
            
        except Exception as e:
            return {'success': False, 'error': f"Cleanup failed: {str(e)}"}
    
    # File Management Methods
    def add_file(self, appointment_id: int, file_type: str, file_path: str, retention_policy: str, user_id: str) -> int:
        """Add a file to the database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Calculate file size and hash
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            file_hash = self.calculate_file_hash(file_path) if os.path.exists(file_path) else None
            
            # Calculate retention date
            retention_date = self.calculate_retention_date(retention_policy)
            
            cursor.execute("""
                INSERT INTO files (appointment_id, file_type, file_path, file_size, file_hash, 
                                 retention_policy, retention_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (appointment_id, file_type, file_path, file_size, file_hash, 
                  retention_policy, retention_date))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_appointment_files(self, appointment_id: int) -> List[Dict]:
        """Get all files for an appointment"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM files 
                WHERE appointment_id = ? AND is_deleted = 0
                ORDER BY created_date
            """, (appointment_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    def calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of file"""
        if not os.path.exists(file_path):
            return None
        
        hash_sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    
    def calculate_retention_date(self, policy: str) -> str:
        """Calculate retention date based on policy"""
        today = datetime.now()
        
        if policy == '2_weeks':
            return (today + timedelta(days=14)).strftime('%Y-%m-%d')
        elif policy == '1_month':
            return (today + timedelta(days=30)).strftime('%Y-%m-%d')
        elif policy == 'long_term':
            return (today + timedelta(days=730)).strftime('%Y-%m-%d')  # 2 years
        else:
            return (today + timedelta(days=30)).strftime('%Y-%m-%d')  # Default 1 month
    
    # Processing Status Methods
    def update_processing_status(self, appointment_id: int, step_name: str, status: str, 
                                error_message: str = None):
        """Update processing status for an appointment step"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if status == 'processing':
                cursor.execute("""
                    INSERT OR REPLACE INTO processing_status 
                    (appointment_id, step_name, status, start_time)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (appointment_id, step_name, status))
            else:
                cursor.execute("""
                    UPDATE processing_status 
                    SET status = ?, end_time = CURRENT_TIMESTAMP, error_message = ?
                    WHERE appointment_id = ? AND step_name = ?
                """, (status, error_message, appointment_id, step_name))
            
            conn.commit()
    
    def get_processing_status(self, appointment_id: int) -> List[Dict]:
        """Get processing status for an appointment"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM processing_status 
                WHERE appointment_id = ?
                ORDER BY created_date
            """, (appointment_id,))
            return [dict(row) for row in cursor.fetchall()]
    
    # Settings Methods
    def get_setting(self, key: str, default=None):
        """Get a setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT setting_value, setting_type FROM settings WHERE setting_key = ?", (key,))
            row = cursor.fetchone()
            
            if not row:
                return default
            
            value, value_type = row
            
            # Convert based on type
            if value_type == 'integer':
                return int(value)
            elif value_type == 'boolean':
                return value.lower() == 'true'
            elif value_type == 'json':
                return json.loads(value)
            else:
                return value
    
    def set_setting(self, key: str, value, value_type: str = 'string'):
        """Set a setting value"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert value to string for storage
            if value_type == 'json':
                value_str = json.dumps(value)
            else:
                value_str = str(value)
            
            cursor.execute("""
                INSERT OR REPLACE INTO settings (setting_key, setting_value, setting_type, last_updated)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, value_str, value_type))
            
            conn.commit()
    
    # Cleanup Methods
    def cleanup_expired_files(self) -> Dict:
        """Clean up files based on retention policies"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get files that need cleanup
            cursor.execute("""
                SELECT file_id, file_path, file_type, retention_policy, file_size
                FROM files 
                WHERE retention_date <= date('now') AND is_deleted = 0
            """)
            
            files_to_delete = cursor.fetchall()
            files_deleted = 0
            space_freed = 0
            
            for file_row in files_to_delete:
                file_id, file_path, file_type, retention_policy, file_size = file_row
                
                try:
                    # Delete physical file
                    if os.path.exists(file_path):
                        os.remove(file_path)
                        files_deleted += 1
                        space_freed += file_size or 0
                    
                    # Mark as deleted in database
                    cursor.execute("""
                        UPDATE files 
                        SET is_deleted = 1, deletion_date = CURRENT_TIMESTAMP
                        WHERE file_id = ?
                    """, (file_id,))
                    
                except Exception as e:
                    print(f"Error deleting file {file_path}: {e}")
            
            # Log cleanup
            if files_deleted > 0:
                cursor.execute("""
                    INSERT INTO cleanup_log (cleanup_type, files_deleted, space_freed, details)
                    VALUES (?, ?, ?, ?)
                """, ('automatic', files_deleted, space_freed, f"Cleaned up {files_deleted} files"))
            
            conn.commit()
            
            return {
                'files_deleted': files_deleted,
                'space_freed': space_freed,
                'details': f"Cleaned up {files_deleted} files, freed {space_freed} bytes"
            }
    
    def get_storage_stats(self) -> Dict:
        """Get storage statistics"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total files and size
            cursor.execute("""
                SELECT COUNT(*) as total_files, SUM(file_size) as total_size
                FROM files WHERE is_deleted = 0
            """)
            stats = cursor.fetchone()
            
            # Files by type
            cursor.execute("""
                SELECT file_type, COUNT(*) as count, SUM(file_size) as size
                FROM files WHERE is_deleted = 0
                GROUP BY file_type
            """)
            by_type = {row['file_type']: {'count': row['count'], 'size': row['size']} 
                      for row in cursor.fetchall()}
            
            # Files expiring soon
            cursor.execute("""
                SELECT COUNT(*) as expiring_soon
                FROM files 
                WHERE retention_date <= date('now', '+7 days') AND is_deleted = 0
            """)
            expiring_soon = cursor.fetchone()['expiring_soon']
            
            return {
                'total_files': stats['total_files'] or 0,
                'total_size': stats['total_size'] or 0,
                'by_type': by_type,
                'expiring_soon': expiring_soon
            }
    
    # Search and Browse Methods
    def search_appointments(self, query: str = None, date_from: str = None, 
                           date_to: str = None) -> List[Dict]:
        """Search appointments with filters"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            sql = """
                SELECT * FROM appointments WHERE 1=1
            """
            params = []
            
            if query:
                sql += " AND (patient_name LIKE ? OR appointment_code LIKE ?)"
                params.extend([f"%{query}%", f"%{query}%"])
            
            if date_from:
                sql += " AND appointment_date >= ?"
                params.append(date_from)
            
            if date_to:
                sql += " AND appointment_date <= ?"
                params.append(date_to)
            
            sql += " ORDER BY appointment_date DESC, appointment_time DESC"
            
            cursor.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]
    
    # Data Management and Security Methods
    def _derive_key_from_password(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from password using PBKDF2"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(password.encode()))
    
    def _validate_password_strength(self, password: str) -> Tuple[bool, str]:
        """Validate password strength for backup encryption"""
        if len(password) < 12:
            return False, "Password must be at least 12 characters long"
        
        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
        
        if not (has_upper and has_lower and has_digit and has_special):
            return False, "Password must contain uppercase, lowercase, numbers, and special characters"
        
        return True, "Password is strong"
    
    def create_encrypted_backup(self, password: str, backup_type: str = "full") -> Dict:
        """Create encrypted backup of all patient data"""
        # Validate password strength
        is_valid, message = self._validate_password_strength(password)
        if not is_valid:
            return {'success': False, 'error': message}
        
        try:
            # Create backup directory
            backup_dir = "backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"{timestamp}_{backup_type}.encrypted.zip"
            backup_path = os.path.join(backup_dir, backup_filename)
            
            # Generate salt and derive key
            salt = secrets.token_bytes(32)
            key = self._derive_key_from_password(password, salt)
            fernet = Fernet(key)
            
            # Create temporary directory for backup
            with tempfile.TemporaryDirectory() as temp_dir:
                # Export database
                db_backup_path = os.path.join(temp_dir, "clinic_data.db")
                shutil.copy2(self.db_path, db_backup_path)
                
                # Copy patient data files
                data_backup_dir = os.path.join(temp_dir, "data")
                if os.path.exists("data"):
                    shutil.copytree("data", data_backup_dir, dirs_exist_ok=True)
                    # Remove the database file from data copy (already backed up separately)
                    if os.path.exists(os.path.join(data_backup_dir, "clinic_data.db")):
                        os.remove(os.path.join(data_backup_dir, "clinic_data.db"))
                
                # Create metadata
                metadata = {
                    'backup_type': backup_type,
                    'timestamp': timestamp,
                    'database_path': self.db_path,
                    'salt': base64.b64encode(salt).decode(),
                    'created_by': 'PhysioApp',
                    'version': '1.0'
                }
                
                # Get data summary for metadata
                stats = self.get_storage_stats()
                metadata.update({
                    'total_files': stats['total_files'],
                    'total_size': stats['total_size'],
                    'appointment_count': len(self.get_recent_appointments(limit=10000))
                })
                
                # Save metadata
                metadata_path = os.path.join(temp_dir, "backup_metadata.json")
                with open(metadata_path, 'w') as f:
                    json.dump(metadata, f, indent=2)
                
                # Create encrypted zip file
                with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for root, dirs, files in os.walk(temp_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, temp_dir)
                            
                            # Read file content
                            with open(file_path, 'rb') as f:
                                file_content = f.read()
                            
                            # Encrypt file content
                            encrypted_content = fernet.encrypt(file_content)
                            
                            # Add encrypted file to zip
                            zipf.writestr(arcname, encrypted_content)
            
            # Log backup creation
            self._log_backup_operation('create', backup_filename, backup_type)
            
            return {
                'success': True,
                'backup_path': backup_path,
                'backup_filename': backup_filename,
                'metadata': metadata
            }
            
        except Exception as e:
            return {'success': False, 'error': f"Backup creation failed: {str(e)}"}
    
    def restore_from_encrypted_backup(self, backup_path: str, password: str) -> Dict:
        """Restore data from encrypted backup"""
        try:
            if not os.path.exists(backup_path):
                return {'success': False, 'error': 'Backup file not found'}
            
            # Extract metadata first to get salt
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                if 'backup_metadata.json' not in zipf.namelist():
                    return {'success': False, 'error': 'Invalid backup file - missing metadata'}
                
                # Read and decrypt metadata
                encrypted_metadata = zipf.read('backup_metadata.json')
                
                # Try to decrypt metadata to get salt
                try:
                    # First try with provided password to get salt from metadata
                    temp_salt = secrets.token_bytes(32)  # Temporary salt for metadata decryption
                    temp_key = self._derive_key_from_password(password, temp_salt)
                    temp_fernet = Fernet(temp_key)
                    
                    # This will likely fail, but we need to extract salt from backup
                    # For now, we'll use a different approach - store salt in filename or use a known method
                    return {'success': False, 'error': 'Backup restoration requires salt extraction - feature in development'}
                    
                except Exception:
                    return {'success': False, 'error': 'Invalid password or corrupted backup file'}
            
        except Exception as e:
            return {'success': False, 'error': f"Restore failed: {str(e)}"}
    
    def get_data_summary(self) -> Dict:
        """Get comprehensive summary of all patient data"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get appointment statistics
            cursor.execute("SELECT COUNT(*) as total_appointments FROM appointments")
            total_appointments = cursor.fetchone()['total_appointments']
            
            # Get file statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_files,
                    SUM(file_size) as total_size,
                    COUNT(DISTINCT appointment_id) as appointments_with_files
                FROM files WHERE is_deleted = 0
            """)
            file_stats = cursor.fetchone()
            
            # Get date range
            cursor.execute("""
                SELECT 
                    MIN(appointment_date) as earliest_date,
                    MAX(appointment_date) as latest_date
                FROM appointments
            """)
            date_range = cursor.fetchone()
            
            # Get files by type
            cursor.execute("""
                SELECT file_type, COUNT(*) as count, SUM(file_size) as size
                FROM files WHERE is_deleted = 0
                GROUP BY file_type
            """)
            files_by_type = {row['file_type']: {'count': row['count'], 'size': row['size']} 
                           for row in cursor.fetchall()}
            
            # Get age distribution
            cursor.execute("""
                SELECT 
                    COUNT(CASE WHEN appointment_date <= date('now', '-14 days') THEN 1 END) as older_than_2_weeks,
                    COUNT(CASE WHEN appointment_date <= date('now', '-30 days') THEN 1 END) as older_than_1_month,
                    COUNT(CASE WHEN appointment_date <= date('now', '-90 days') THEN 1 END) as older_than_3_months
                FROM appointments
            """)
            age_distribution = cursor.fetchone()
            
            return {
                'total_appointments': total_appointments,
                'total_files': file_stats['total_files'] or 0,
                'total_size': file_stats['total_size'] or 0,
                'appointments_with_files': file_stats['appointments_with_files'] or 0,
                'earliest_date': date_range['earliest_date'],
                'latest_date': date_range['latest_date'],
                'files_by_type': files_by_type,
                'age_distribution': dict(age_distribution)
            }
    
    def clear_all_patient_data(self, create_backup: bool = True, backup_password: str = None) -> Dict:
        """Clear all patient data with optional encrypted backup"""
        try:
            # Create backup if requested
            backup_info = None
            if create_backup:
                if not backup_password:
                    return {'success': False, 'error': 'Backup password required for data clearing'}
                
                backup_result = self.create_encrypted_backup(backup_password, "full")
                if not backup_result['success']:
                    return backup_result
                backup_info = backup_result
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get counts before deletion for logging
                cursor.execute("SELECT COUNT(*) as count FROM appointments")
                appointment_count = cursor.fetchone()['count']
                
                cursor.execute("SELECT COUNT(*) as count, SUM(file_size) as size FROM files WHERE is_deleted = 0")
                file_stats = cursor.fetchone()
                file_count = file_stats['count'] or 0
                total_size = file_stats['size'] or 0
                
                # Delete all patient data
                cursor.execute("DELETE FROM processing_status")
                cursor.execute("DELETE FROM files")
                cursor.execute("DELETE FROM appointments")
                
                # Delete all physical files
                if os.path.exists("data"):
                    for item in os.listdir("data"):
                        item_path = os.path.join("data", item)
                        if os.path.isdir(item_path) and item != "clinic_data.db":
                            shutil.rmtree(item_path)
                
                conn.commit()
                
                # Log the operation
                self._log_cleanup_operation('clear_all', file_count, total_size, 
                                          f"Cleared {appointment_count} appointments, {file_count} files")
                
                return {
                    'success': True,
                    'appointments_deleted': appointment_count,
                    'files_deleted': file_count,
                    'space_freed': total_size,
                    'backup_info': backup_info
                }
                
        except Exception as e:
            return {'success': False, 'error': f"Data clearing failed: {str(e)}"}
    
    def archive_old_data(self, days_threshold: int = 14) -> Dict:
        """Archive data older than specified days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_threshold)).strftime('%Y-%m-%d')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get appointments to archive
                cursor.execute("""
                    SELECT appointment_id, appointment_date, patient_name, appointment_time, folder_path
                    FROM appointments 
                    WHERE appointment_date <= ?
                """, (cutoff_date,))
                
                appointments_to_archive = cursor.fetchall()
                
                if not appointments_to_archive:
                    return {'success': True, 'archived_count': 0, 'archived_size': 0, 'cutoff_date': cutoff_date, 'message': 'No data to archive'}
                
                # Create archive directory in proper writable location
                try:
                    from app_paths import get_writable_path
                    archive_dir = str(get_writable_path("data/archived"))
                except ImportError:
                    import sys
                    if sys.platform == 'darwin':
                        archive_dir = str(Path.home() / "Library" / "Application Support" / "PhysioClinicAssistant" / "data" / "archived")
                    else:
                        archive_dir = str(Path.home() / ".local" / "share" / "PhysioClinicAssistant" / "data" / "archived")
                    os.makedirs(archive_dir, exist_ok=True)
                
                archived_count = 0
                archived_size = 0
                
                for appointment in appointments_to_archive:
                    appointment_id, appointment_date, patient_name, appointment_time, folder_path = appointment
                    
                    # Get files for this appointment
                    cursor.execute("""
                        SELECT file_id, file_path, file_size
                        FROM files 
                        WHERE appointment_id = ? AND is_deleted = 0
                    """, (appointment_id,))
                    
                    files = cursor.fetchall()
                    
                    if files:
                        # Create archived folder structure
                        safe_patient_name = patient_name.replace(' ', '_').replace('/', '_').replace('\\', '_')
                        archived_folder = os.path.join(archive_dir, appointment_date, f"{safe_patient_name}_{appointment_time}")
                        os.makedirs(archived_folder, exist_ok=True)
                        
                        # Move files to archive
                        for file_row in files:
                            file_id, file_path, file_size = file_row
                            
                            if os.path.exists(file_path):
                                # Create archived file path
                                filename = os.path.basename(file_path)
                                archived_file_path = os.path.join(archived_folder, filename)
                                
                                # Move file
                                shutil.move(file_path, archived_file_path)
                                
                                # Update file path in database
                                cursor.execute("""
                                    UPDATE files 
                                    SET file_path = ?, retention_policy = 'archived'
                                    WHERE file_id = ?
                                """, (archived_file_path, file_id))
                                
                                archived_count += 1
                                archived_size += file_size or 0
                        
                        # Mark appointment as archived
                        cursor.execute("""
                            UPDATE appointments 
                            SET notes = COALESCE(notes || '\n', '') || 'ARCHIVED on ' || datetime('now')
                            WHERE appointment_id = ?
                        """, (appointment_id,))
                
                conn.commit()
                
                # Log the operation
                self._log_cleanup_operation('archive', archived_count, archived_size, 
                                          f"Archived data older than {days_threshold} days")
                
                return {
                    'success': True,
                    'archived_count': archived_count,
                    'archived_size': archived_size,
                    'cutoff_date': cutoff_date
                }
                
        except Exception as e:
            return {'success': False, 'error': f"Archive operation failed: {str(e)}"}
    
    def delete_old_data(self, days_threshold: int = 30) -> Dict:
        """Delete data older than specified days"""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days_threshold)).strftime('%Y-%m-%d')
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get appointments to delete
                cursor.execute("""
                    SELECT appointment_id, folder_path
                    FROM appointments 
                    WHERE appointment_date <= ?
                """, (cutoff_date,))
                
                appointments_to_delete = cursor.fetchall()
                
                if not appointments_to_delete:
                    return {'success': True, 'deleted_appointments': 0, 'deleted_files': 0, 'deleted_size': 0, 'cutoff_date': cutoff_date, 'message': 'No data to delete'}
                
                deleted_files = 0
                deleted_size = 0
                deleted_appointments = 0
                
                for appointment in appointments_to_delete:
                    appointment_id, folder_path = appointment
                    
                    # Get files for this appointment
                    cursor.execute("""
                        SELECT file_id, file_path, file_size
                        FROM files 
                        WHERE appointment_id = ?
                    """, (appointment_id,))
                    
                    files = cursor.fetchall()
                    
                    # Delete physical files
                    for file_row in files:
                        file_id, file_path, file_size = file_row
                        
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                deleted_files += 1
                                deleted_size += file_size or 0
                            except Exception as e:
                                print(f"Warning: Could not delete file {file_path}: {e}")
                    
                    # Delete database records
                    cursor.execute("DELETE FROM processing_status WHERE appointment_id = ?", (appointment_id,))
                    cursor.execute("DELETE FROM files WHERE appointment_id = ?", (appointment_id,))
                    cursor.execute("DELETE FROM appointments WHERE appointment_id = ?", (appointment_id,))
                    
                    deleted_appointments += 1
                
                # Clean up empty folders
                self.cleanup_empty_date_folders()
                
                conn.commit()
                
                # Log the operation
                self._log_cleanup_operation('delete_old', deleted_files, deleted_size, 
                                          f"Deleted {deleted_appointments} appointments older than {days_threshold} days")
                
                return {
                    'success': True,
                    'deleted_appointments': deleted_appointments,
                    'deleted_files': deleted_files,
                    'deleted_size': deleted_size,
                    'cutoff_date': cutoff_date
                }
                
        except Exception as e:
            return {'success': False, 'error': f"Delete operation failed: {str(e)}"}
    
    def clear_data_by_date_range(self, start_date: str, end_date: str) -> Dict:
        """Clear data within a specific date range"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get appointments in date range
                cursor.execute("""
                    SELECT appointment_id, folder_path
                    FROM appointments 
                    WHERE appointment_date BETWEEN ? AND ?
                """, (start_date, end_date))
                
                appointments_in_range = cursor.fetchall()
                
                if not appointments_in_range:
                    return {'success': True, 'deleted_appointments': 0, 'deleted_files': 0, 'deleted_size': 0, 'date_range': f"{start_date} to {end_date}", 'message': 'No data in specified date range'}
                
                deleted_files = 0
                deleted_size = 0
                deleted_appointments = 0
                
                for appointment in appointments_in_range:
                    appointment_id, folder_path = appointment
                    
                    # Get files for this appointment
                    cursor.execute("""
                        SELECT file_id, file_path, file_size
                        FROM files 
                        WHERE appointment_id = ?
                    """, (appointment_id,))
                    
                    files = cursor.fetchall()
                    
                    # Delete physical files
                    for file_row in files:
                        file_id, file_path, file_size = file_row
                        
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                deleted_files += 1
                                deleted_size += file_size or 0
                            except Exception as e:
                                print(f"Warning: Could not delete file {file_path}: {e}")
                    
                    # Delete database records
                    cursor.execute("DELETE FROM processing_status WHERE appointment_id = ?", (appointment_id,))
                    cursor.execute("DELETE FROM files WHERE appointment_id = ?", (appointment_id,))
                    cursor.execute("DELETE FROM appointments WHERE appointment_id = ?", (appointment_id,))
                    
                    deleted_appointments += 1
                
                # Clean up empty folders
                self.cleanup_empty_date_folders()
                
                conn.commit()
                
                # Log the operation
                self._log_cleanup_operation('date_range', deleted_files, deleted_size, 
                                          f"Deleted {deleted_appointments} appointments from {start_date} to {end_date}")
                
                return {
                    'success': True,
                    'deleted_appointments': deleted_appointments,
                    'deleted_files': deleted_files,
                    'deleted_size': deleted_size,
                    'date_range': f"{start_date} to {end_date}"
                }
                
        except Exception as e:
            return {'success': False, 'error': f"Date range clearing failed: {str(e)}"}
    
    def clear_patient_data(self, patient_name: str) -> Dict:
        """Clear all data for a specific patient"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get appointments for this patient
                cursor.execute("""
                    SELECT appointment_id, folder_path
                    FROM appointments 
                    WHERE patient_name LIKE ?
                """, (f"%{patient_name}%",))
                
                patient_appointments = cursor.fetchall()
                
                if not patient_appointments:
                    return {'success': True, 'deleted_appointments': 0, 'deleted_files': 0, 'deleted_size': 0, 'patient_name': patient_name, 'message': f'No data found for patient: {patient_name}'}
                
                deleted_files = 0
                deleted_size = 0
                deleted_appointments = 0
                
                for appointment in patient_appointments:
                    appointment_id, folder_path = appointment
                    
                    # Get files for this appointment
                    cursor.execute("""
                        SELECT file_id, file_path, file_size
                        FROM files 
                        WHERE appointment_id = ?
                    """, (appointment_id,))
                    
                    files = cursor.fetchall()
                    
                    # Delete physical files
                    for file_row in files:
                        file_id, file_path, file_size = file_row
                        
                        if os.path.exists(file_path):
                            try:
                                os.remove(file_path)
                                deleted_files += 1
                                deleted_size += file_size or 0
                            except Exception as e:
                                print(f"Warning: Could not delete file {file_path}: {e}")
                    
                    # Delete database records
                    cursor.execute("DELETE FROM processing_status WHERE appointment_id = ?", (appointment_id,))
                    cursor.execute("DELETE FROM files WHERE appointment_id = ?", (appointment_id,))
                    cursor.execute("DELETE FROM appointments WHERE appointment_id = ?", (appointment_id,))
                    
                    deleted_appointments += 1
                
                # Clean up empty folders
                self.cleanup_empty_date_folders()
                
                conn.commit()
                
                # Log the operation
                self._log_cleanup_operation('patient', deleted_files, deleted_size, 
                                          f"Deleted {deleted_appointments} appointments for patient: {patient_name}")
                
                return {
                    'success': True,
                    'deleted_appointments': deleted_appointments,
                    'deleted_files': deleted_files,
                    'deleted_size': deleted_size,
                    'patient_name': patient_name
                }
                
        except Exception as e:
            return {'success': False, 'error': f"Patient data clearing failed: {str(e)}"}
    
    def _log_backup_operation(self, operation: str, backup_filename: str, backup_type: str):
        """Log backup operations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cleanup_log (cleanup_type, files_deleted, space_freed, details)
                VALUES (?, ?, ?, ?)
            """, (f"backup_{operation}", 0, 0, f"Backup {operation}: {backup_filename} ({backup_type})"))
            conn.commit()
    
    def _log_cleanup_operation(self, operation_type: str, files_deleted: int, space_freed: int, details: str):
        """Log cleanup operations"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO cleanup_log (cleanup_type, files_deleted, space_freed, details)
                VALUES (?, ?, ?, ?)
            """, (operation_type, files_deleted, space_freed, details))
            conn.commit()
