#!/usr/bin/env python3
"""
Audit Manager for Physiotherapy Clinic Assistant
Handles immutable audit logging with cryptographic integrity
"""

import os
import json
import hashlib
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Union
from enum import Enum
from pathlib import Path


class AuditEventType(Enum):
    """Types of audit events"""
    CREATE = "CREATE"
    READ = "READ"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    SOFT_DELETE = "SOFT_DELETE"
    EXPORT = "EXPORT"
    LOGIN = "LOGIN"
    LOGOUT = "LOGOUT"
    ENCRYPT = "ENCRYPT"
    DECRYPT = "DECRYPT"
    FILE_ACCESS = "FILE_ACCESS"
    FILE_DELETE = "FILE_DELETE"
    KEY_ROTATION = "KEY_ROTATION"
    BACKUP_CREATE = "BACKUP_CREATE"
    BACKUP_RESTORE = "BACKUP_RESTORE"
    MIGRATION = "MIGRATION"
    SYSTEM_EVENT = "SYSTEM_EVENT"


class AuditManager:
    """Manages immutable audit logging with cryptographic integrity"""
    
    def __init__(self, db_path: Optional[str] = None):
        # Use proper writable database path
        if db_path is None:
            try:
                from app_paths import get_database_path
                self.db_path = str(get_database_path())
            except ImportError:
                import sys
                if sys.platform == 'darwin':
                    app_support = Path.home() / "Library" / "Application Support" / "PhysioClinicAssistant"
                    self.db_path = str(app_support / "data" / "clinic_data.db")
                else:
                    self.db_path = str(Path.home() / ".local" / "share" / "PhysioClinicAssistant" / "data" / "clinic_data.db")
        else:
            self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.retention_years = 7  # Configurable retention period
        
        # Initialize audit system
        self._init_audit_system()
    
    def _init_audit_system(self):
        """Initialize the audit system and create audit log table"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Create audit log table with comprehensive schema
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS audit_log (
                        audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
                        event_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_id VARCHAR(255) NOT NULL,
                        session_id VARCHAR(255),
                        event_type VARCHAR(50) NOT NULL,
                        table_name VARCHAR(100),
                        record_id VARCHAR(255),
                        operation_details TEXT,
                        ip_address VARCHAR(45),
                        user_agent TEXT,
                        file_operation BOOLEAN DEFAULT 0,
                        file_path VARCHAR(500),
                        file_hash VARCHAR(64),
                        previous_hash VARCHAR(64),
                        audit_hash VARCHAR(64) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                
                # Create indexes for performance
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_log_user_id 
                    ON audit_log(user_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp 
                    ON audit_log(event_timestamp)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_log_event_type 
                    ON audit_log(event_type)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_log_table_name 
                    ON audit_log(table_name)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_log_record_id 
                    ON audit_log(record_id)
                """)
                
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_audit_log_audit_hash 
                    ON audit_log(audit_hash)
                """)
                
                # Create view for recent audit events
                cursor.execute("""
                    CREATE VIEW IF NOT EXISTS recent_audit_events AS
                    SELECT 
                        audit_id,
                        event_timestamp,
                        user_id,
                        event_type,
                        table_name,
                        record_id,
                        operation_details,
                        file_operation,
                        file_path
                    FROM audit_log
                    WHERE event_timestamp >= datetime('now', '-30 days')
                    ORDER BY event_timestamp DESC
                """)
                
                conn.commit()
                self.logger.info("Audit system initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize audit system: {e}")
            raise
    
    def get_connection(self):
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _get_previous_audit_hash(self) -> Optional[str]:
        """Get the hash of the most recent audit record"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT audit_hash FROM audit_log 
                    ORDER BY audit_id DESC LIMIT 1
                """)
                result = cursor.fetchone()
                return result['audit_hash'] if result else None
        except Exception as e:
            self.logger.error(f"Failed to get previous audit hash: {e}")
            return None
    
    def _calculate_audit_hash(self, audit_data: Dict[str, Any]) -> str:
        """Calculate cryptographic hash for audit record integrity"""
        try:
            # Create a deterministic string from audit data
            hash_data = {
                'audit_id': audit_data.get('audit_id'),
                'event_timestamp': audit_data.get('event_timestamp'),
                'user_id': audit_data.get('user_id'),
                'session_id': audit_data.get('session_id'),
                'event_type': audit_data.get('event_type'),
                'table_name': audit_data.get('table_name'),
                'record_id': audit_data.get('record_id'),
                'operation_details': audit_data.get('operation_details'),
                'ip_address': audit_data.get('ip_address'),
                'user_agent': audit_data.get('user_agent'),
                'file_operation': audit_data.get('file_operation'),
                'file_path': audit_data.get('file_path'),
                'file_hash': audit_data.get('file_hash'),
                'previous_hash': audit_data.get('previous_hash')
            }
            
            # Convert to JSON string with sorted keys for consistency
            hash_string = json.dumps(hash_data, sort_keys=True, separators=(',', ':'))
            
            # Calculate SHA-256 hash
            return hashlib.sha256(hash_string.encode('utf-8')).hexdigest()
            
        except Exception as e:
            self.logger.error(f"Failed to calculate audit hash: {e}")
            raise
    
    def log_audit_event(self, 
                       user_id: str,
                       event_type: Union[AuditEventType, str],
                       table_name: Optional[str] = None,
                       record_id: Optional[str] = None,
                       operation_details: Optional[Dict[str, Any]] = None,
                       session_id: Optional[str] = None,
                       ip_address: Optional[str] = None,
                       user_agent: Optional[str] = None,
                       file_operation: bool = False,
                       file_path: Optional[str] = None,
                       file_hash: Optional[str] = None) -> int:
        """
        Log an audit event with cryptographic integrity
        
        Args:
            user_id: ID of the user performing the action
            event_type: Type of event (AuditEventType enum or string)
            table_name: Database table name (if applicable)
            record_id: ID of the record being modified
            operation_details: Additional details about the operation
            session_id: User session ID
            ip_address: IP address of the user
            user_agent: User agent string
            file_operation: Whether this is a file operation
            file_path: Path to the file (if applicable)
            file_hash: Hash of the file (if applicable)
        
        Returns:
            int: The audit_id of the created record
        """
        try:
            # Convert event_type to string if it's an enum
            if isinstance(event_type, AuditEventType):
                event_type_str = event_type.value
            else:
                event_type_str = str(event_type)
            
            # Insert audit record with proper hash chain handling
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get the most recent audit hash within the transaction
                cursor.execute("""
                    SELECT audit_hash FROM audit_log 
                    ORDER BY audit_id DESC LIMIT 1
                """)
                result = cursor.fetchone()
                previous_hash = result['audit_hash'] if result else None
                
                # Prepare audit data
                audit_data = {
                    'user_id': user_id,
                    'session_id': session_id,
                    'event_type': event_type_str,
                    'table_name': table_name,
                    'record_id': record_id,
                    'operation_details': json.dumps(operation_details) if operation_details else None,
                    'ip_address': ip_address,
                    'user_agent': user_agent,
                    'file_operation': file_operation,
                    'file_path': file_path,
                    'file_hash': file_hash,
                    'previous_hash': previous_hash
                }
                
                # Calculate audit hash
                audit_hash = self._calculate_audit_hash(audit_data)
                audit_data['audit_hash'] = audit_hash
                
                # Insert audit record
                cursor.execute("""
                    INSERT INTO audit_log (
                        user_id, session_id, event_type, table_name, record_id,
                        operation_details, ip_address, user_agent, file_operation,
                        file_path, file_hash, previous_hash, audit_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    audit_data['user_id'], audit_data['session_id'], audit_data['event_type'],
                    audit_data['table_name'], audit_data['record_id'], audit_data['operation_details'],
                    audit_data['ip_address'], audit_data['user_agent'], audit_data['file_operation'],
                    audit_data['file_path'], audit_data['file_hash'], audit_data['previous_hash'],
                    audit_data['audit_hash']
                ))
                
                audit_id = cursor.lastrowid
                conn.commit()
                
                self.logger.debug(f"Audit event logged: {event_type_str} by {user_id} (ID: {audit_id})")
                return audit_id
                
        except Exception as e:
            self.logger.error(f"Failed to log audit event: {e}")
            raise
    
    def log_database_operation(self,
                              user_id: str,
                              event_type: Union[AuditEventType, str],
                              table_name: str,
                              record_id: str,
                              before_data: Optional[Dict[str, Any]] = None,
                              after_data: Optional[Dict[str, Any]] = None,
                              session_id: Optional[str] = None,
                              ip_address: Optional[str] = None,
                              user_agent: Optional[str] = None) -> int:
        """
        Log a database operation with before/after data
        
        Args:
            user_id: ID of the user performing the action
            event_type: Type of database operation
            table_name: Name of the database table
            record_id: ID of the record being modified
            before_data: Data before the operation (for UPDATE/DELETE)
            after_data: Data after the operation (for CREATE/UPDATE)
            session_id: User session ID
            ip_address: IP address of the user
            user_agent: User agent string
        
        Returns:
            int: The audit_id of the created record
        """
        operation_details = {}
        
        if before_data:
            operation_details['before'] = before_data
        if after_data:
            operation_details['after'] = after_data
        
        return self.log_audit_event(
            user_id=user_id,
            event_type=event_type,
            table_name=table_name,
            record_id=record_id,
            operation_details=operation_details,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_file_operation(self,
                          user_id: str,
                          event_type: Union[AuditEventType, str],
                          file_path: str,
                          file_hash: Optional[str] = None,
                          operation_details: Optional[Dict[str, Any]] = None,
                          session_id: Optional[str] = None,
                          ip_address: Optional[str] = None,
                          user_agent: Optional[str] = None) -> int:
        """
        Log a file operation
        
        Args:
            user_id: ID of the user performing the action
            event_type: Type of file operation
            file_path: Path to the file
            file_hash: Hash of the file (if applicable)
            operation_details: Additional details about the operation
            session_id: User session ID
            ip_address: IP address of the user
            user_agent: User agent string
        
        Returns:
            int: The audit_id of the created record
        """
        return self.log_audit_event(
            user_id=user_id,
            event_type=event_type,
            file_operation=True,
            file_path=file_path,
            file_hash=file_hash,
            operation_details=operation_details,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def log_authentication_event(self,
                                user_id: str,
                                event_type: Union[AuditEventType, str],
                                success: bool,
                                details: Optional[Dict[str, Any]] = None,
                                session_id: Optional[str] = None,
                                ip_address: Optional[str] = None,
                                user_agent: Optional[str] = None) -> int:
        """
        Log an authentication event
        
        Args:
            user_id: ID of the user (or attempted user)
            event_type: Type of authentication event
            success: Whether the authentication was successful
            details: Additional details about the event
            session_id: User session ID
            ip_address: IP address of the user
            user_agent: User agent string
        
        Returns:
            int: The audit_id of the created record
        """
        operation_details = {'success': success}
        if details:
            operation_details.update(details)
        
        return self.log_audit_event(
            user_id=user_id,
            event_type=event_type,
            operation_details=operation_details,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    
    def get_audit_log(self,
                     user_id: Optional[str] = None,
                     event_type: Optional[str] = None,
                     table_name: Optional[str] = None,
                     record_id: Optional[str] = None,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     file_operations_only: bool = False,
                     limit: int = 1000,
                     offset: int = 0) -> List[Dict[str, Any]]:
        """
        Retrieve audit log entries with filtering
        
        Args:
            user_id: Filter by user ID
            event_type: Filter by event type
            table_name: Filter by table name
            record_id: Filter by record ID
            start_date: Filter by start date (ISO format)
            end_date: Filter by end date (ISO format)
            file_operations_only: Only return file operations
            limit: Maximum number of records to return
            offset: Number of records to skip
        
        Returns:
            List of audit log entries
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Build WHERE clause
                where_conditions = []
                params = []
                
                if user_id:
                    where_conditions.append("user_id = ?")
                    params.append(user_id)
                
                if event_type:
                    where_conditions.append("event_type = ?")
                    params.append(event_type)
                
                if table_name:
                    where_conditions.append("table_name = ?")
                    params.append(table_name)
                
                if record_id:
                    where_conditions.append("record_id = ?")
                    params.append(record_id)
                
                if start_date:
                    where_conditions.append("event_timestamp >= ?")
                    params.append(start_date)
                
                if end_date:
                    where_conditions.append("event_timestamp <= ?")
                    params.append(end_date)
                
                if file_operations_only:
                    where_conditions.append("file_operation = 1")
                
                where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
                
                # Build query
                sql = f"""
                    SELECT * FROM audit_log 
                    {where_clause}
                    ORDER BY event_timestamp DESC, audit_id DESC
                    LIMIT ? OFFSET ?
                """
                params.extend([limit, offset])
                
                cursor.execute(sql, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            self.logger.error(f"Failed to get audit log: {e}")
            raise
    
    def verify_audit_integrity(self) -> Dict[str, Any]:
        """
        Verify the cryptographic integrity of the audit log
        
        Returns:
            Dict containing integrity verification results
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get all audit records in order
                cursor.execute("""
                    SELECT audit_id, audit_hash, previous_hash, event_timestamp, user_id, event_type,
                           table_name, record_id, operation_details
                    FROM audit_log 
                    ORDER BY audit_id
                """)
                
                records = cursor.fetchall()
                integrity_issues = []
                previous_hash = None
                hash_chain_broken = False
                
                for record in records:
                    audit_id, audit_hash, stored_previous_hash, timestamp, user_id, event_type, table_name, record_id, operation_details = record
                    
                    # Check if previous hash matches
                    if stored_previous_hash != previous_hash:
                        integrity_issues.append({
                            'audit_id': audit_id,
                            'issue': 'Previous hash mismatch',
                            'expected': previous_hash,
                            'actual': stored_previous_hash,
                            'timestamp': timestamp,
                            'user_id': user_id,
                            'event_type': event_type,
                            'severity': 'critical'
                        })
                        hash_chain_broken = True
                    
                    # Verify current hash format
                    if not audit_hash or len(audit_hash) != 64:
                        integrity_issues.append({
                            'audit_id': audit_id,
                            'issue': 'Invalid audit hash format',
                            'hash': audit_hash,
                            'timestamp': timestamp,
                            'user_id': user_id,
                            'event_type': event_type,
                            'severity': 'critical'
                        })
                        hash_chain_broken = True
                    
                    previous_hash = audit_hash
                
                # Check for suspicious patterns
                suspicious_patterns = self._detect_suspicious_patterns(records)
                integrity_issues.extend(suspicious_patterns)
                
                return {
                    'total_records': len(records),
                    'integrity_issues': integrity_issues,
                    'is_intact': len(integrity_issues) == 0 and not hash_chain_broken,
                    'hash_chain_broken': hash_chain_broken,
                    'critical_issues': len([i for i in integrity_issues if i.get('severity') == 'critical']),
                    'warning_issues': len([i for i in integrity_issues if i.get('severity') == 'warning']),
                    'verification_timestamp': datetime.now().isoformat(),
                    'retention_policy': f"{self.retention_years} years"
                }
                
        except Exception as e:
            self.logger.error(f"Failed to verify audit integrity: {e}")
            return {
                'error': str(e),
                'is_intact': False,
                'verification_timestamp': datetime.now().isoformat()
            }
    
    def _detect_suspicious_patterns(self, records: List) -> List[Dict[str, Any]]:
        """Detect suspicious patterns in audit records"""
        suspicious_issues = []
        
        try:
            # Check for rapid-fire events (potential automated attacks)
            rapid_events = []
            for i in range(1, len(records)):
                prev_time = datetime.fromisoformat(records[i-1][3].replace('Z', '+00:00'))
                curr_time = datetime.fromisoformat(records[i][3].replace('Z', '+00:00'))
                time_diff = (curr_time - prev_time).total_seconds()
                
                if time_diff < 1:  # Less than 1 second between events
                    rapid_events.append({
                        'audit_id': records[i][0],
                        'time_diff': time_diff,
                        'user_id': records[i][4],
                        'event_type': records[i][5]
                    })
            
            if len(rapid_events) > 10:  # More than 10 rapid events
                suspicious_issues.append({
                    'issue': 'Rapid-fire events detected',
                    'count': len(rapid_events),
                    'severity': 'warning',
                    'details': f"Found {len(rapid_events)} events with <1 second intervals"
                })
            
            # Check for unusual user activity patterns
            user_activity = {}
            for record in records:
                user_id = record[4]
                if user_id not in user_activity:
                    user_activity[user_id] = []
                user_activity[user_id].append(record)
            
            for user_id, user_records in user_activity.items():
                if len(user_records) > 1000:  # More than 1000 events from one user
                    suspicious_issues.append({
                        'issue': 'High volume user activity',
                        'user_id': user_id,
                        'event_count': len(user_records),
                        'severity': 'warning',
                        'details': f"User {user_id} has {len(user_records)} audit events"
                    })
            
            # Check for missing or null critical fields
            for record in records:
                if not record[4] or record[4] == '':  # Missing user_id
                    suspicious_issues.append({
                        'audit_id': record[0],
                        'issue': 'Missing user_id',
                        'severity': 'warning',
                        'timestamp': record[3]
                    })
                
                if not record[1] or record[1] == '':  # Missing audit_hash
                    suspicious_issues.append({
                        'audit_id': record[0],
                        'issue': 'Missing audit_hash',
                        'severity': 'critical',
                        'timestamp': record[3]
                    })
            
        except Exception as e:
            self.logger.warning(f"Error detecting suspicious patterns: {e}")
        
        return suspicious_issues
    
    def generate_integrity_report(self) -> Dict[str, Any]:
        """Generate a comprehensive integrity report"""
        try:
            integrity_result = self.verify_audit_integrity()
            stats = self.get_audit_statistics()
            retention_info = self.get_retention_policy_info()
            
            return {
                'report_generated_at': datetime.now().isoformat(),
                'integrity_check': integrity_result,
                'statistics': stats,
                'retention_policy': retention_info,
                'recommendations': self._generate_recommendations(integrity_result, stats)
            }
            
        except Exception as e:
            self.logger.error(f"Failed to generate integrity report: {e}")
            return {'error': str(e)}
    
    def _generate_recommendations(self, integrity_result: Dict, stats: Dict) -> List[str]:
        """Generate recommendations based on audit analysis"""
        recommendations = []
        
        if not integrity_result.get('is_intact', True):
            recommendations.append("CRITICAL: Audit log integrity compromised. Immediate investigation required.")
        
        if integrity_result.get('critical_issues', 0) > 0:
            recommendations.append(f"URGENT: {integrity_result['critical_issues']} critical integrity issues found.")
        
        if integrity_result.get('warning_issues', 0) > 10:
            recommendations.append("WARNING: High number of integrity warnings. Review audit log quality.")
        
        if stats.get('total_records', 0) > 100000:
            recommendations.append("INFO: Large audit log size. Consider archiving old records.")
        
        if not recommendations:
            recommendations.append("AUDIT LOG STATUS: All integrity checks passed. No issues detected.")
        
        return recommendations
    
    def cleanup_old_audit_logs(self, retention_years: int = None) -> Dict[str, Any]:
        """
        Clean up audit logs older than retention period
        
        Args:
            retention_years: Override default retention period
        
        Returns:
            Dict containing cleanup results
        """
        try:
            # Use provided retention period or default
            years = retention_years or self.retention_years
            cutoff_date = (datetime.now() - timedelta(days=years * 365)).isoformat()
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Count records to be deleted
                cursor.execute("""
                    SELECT COUNT(*) as count FROM audit_log 
                    WHERE event_timestamp < ?
                """, (cutoff_date,))
                
                count_result = cursor.fetchone()
                records_to_delete = count_result['count'] if count_result else 0
                
                if records_to_delete > 0:
                    # Create backup before deletion (optional)
                    backup_result = self._create_audit_backup_before_cleanup(cutoff_date)
                    
                    # Delete old records
                    cursor.execute("""
                        DELETE FROM audit_log 
                        WHERE event_timestamp < ?
                    """, (cutoff_date,))
                    
                    conn.commit()
                    
                    self.logger.info(f"Cleaned up {records_to_delete} old audit log records")
                    
                    return {
                        'success': True,
                        'records_deleted': records_to_delete,
                        'cutoff_date': cutoff_date,
                        'retention_years': years,
                        'backup_created': backup_result.get('success', False),
                        'backup_path': backup_result.get('backup_path'),
                        'message': f"Deleted {records_to_delete} audit records older than {years} years"
                    }
                else:
                    return {
                        'success': True,
                        'records_deleted': 0,
                        'cutoff_date': cutoff_date,
                        'retention_years': years,
                        'message': 'No old audit records to clean up'
                    }
                
        except Exception as e:
            self.logger.error(f"Failed to cleanup old audit logs: {e}")
            return {
                'success': False,
                'error': str(e),
                'records_deleted': 0
            }
    
    def _create_audit_backup_before_cleanup(self, cutoff_date: str) -> Dict[str, Any]:
        """Create backup of audit logs before cleanup"""
        try:
            import tempfile
            import json
            from pathlib import Path
            
            # Create backup directory
            backup_dir = Path("audit_backups")
            backup_dir.mkdir(exist_ok=True)
            
            # Generate backup filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"audit_backup_{timestamp}.json"
            backup_path = backup_dir / backup_filename
            
            # Get audit records to be deleted
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT * FROM audit_log 
                    WHERE event_timestamp < ?
                    ORDER BY event_timestamp
                """, (cutoff_date,))
                
                records = [dict(row) for row in cursor.fetchall()]
            
            # Save to backup file
            with open(backup_path, 'w') as f:
                json.dump({
                    'backup_info': {
                        'created_at': datetime.now().isoformat(),
                        'cutoff_date': cutoff_date,
                        'record_count': len(records),
                        'retention_years': self.retention_years
                    },
                    'audit_records': records
                }, f, indent=2, default=str)
            
            return {
                'success': True,
                'backup_path': str(backup_path),
                'record_count': len(records)
            }
            
        except Exception as e:
            self.logger.warning(f"Failed to create audit backup: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_retention_policy_info(self) -> Dict[str, Any]:
        """Get information about the current retention policy"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get date range of audit logs
                cursor.execute("""
                    SELECT 
                        MIN(event_timestamp) as earliest,
                        MAX(event_timestamp) as latest,
                        COUNT(*) as total_records
                    FROM audit_log
                """)
                
                date_info = cursor.fetchone()
                
                # Calculate records that would be deleted
                cutoff_date = (datetime.now() - timedelta(days=self.retention_years * 365)).isoformat()
                cursor.execute("""
                    SELECT COUNT(*) as count FROM audit_log 
                    WHERE event_timestamp < ?
                """, (cutoff_date,))
                
                old_records = cursor.fetchone()['count']
                
                return {
                    'retention_years': self.retention_years,
                    'cutoff_date': cutoff_date,
                    'total_records': date_info['total_records'],
                    'old_records_to_delete': old_records,
                    'earliest_record': date_info['earliest'],
                    'latest_record': date_info['latest'],
                    'records_to_keep': date_info['total_records'] - old_records
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get retention policy info: {e}")
            return {'error': str(e)}
    
    def set_retention_policy(self, retention_years: int) -> Dict[str, Any]:
        """Set the audit log retention policy"""
        try:
            if retention_years < 1:
                return {
                    'success': False,
                    'error': 'Retention period must be at least 1 year'
                }
            
            if retention_years > 10:
                return {
                    'success': False,
                    'error': 'Retention period cannot exceed 10 years'
                }
            
            old_retention = self.retention_years
            self.retention_years = retention_years
            
            # Log the policy change
            self.log_audit_event(
                user_id="system",
                event_type=AuditEventType.SYSTEM_EVENT,
                operation_details={
                    'action': 'retention_policy_changed',
                    'old_retention_years': old_retention,
                    'new_retention_years': retention_years
                }
            )
            
            return {
                'success': True,
                'old_retention_years': old_retention,
                'new_retention_years': retention_years,
                'message': f"Retention policy updated to {retention_years} years"
            }
            
        except Exception as e:
            self.logger.error(f"Failed to set retention policy: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_audit_statistics(self) -> Dict[str, Any]:
        """
        Get audit log statistics
        
        Returns:
            Dict containing audit statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Total records
                cursor.execute("SELECT COUNT(*) as total FROM audit_log")
                total_records = cursor.fetchone()['total']
                
                # Records by event type
                cursor.execute("""
                    SELECT event_type, COUNT(*) as count 
                    FROM audit_log 
                    GROUP BY event_type 
                    ORDER BY count DESC
                """)
                by_event_type = {row['event_type']: row['count'] for row in cursor.fetchall()}
                
                # Records by user
                cursor.execute("""
                    SELECT user_id, COUNT(*) as count 
                    FROM audit_log 
                    GROUP BY user_id 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                by_user = {row['user_id']: row['count'] for row in cursor.fetchall()}
                
                # File operations
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM audit_log 
                    WHERE file_operation = 1
                """)
                file_operations = cursor.fetchone()['count']
                
                # Recent activity (last 24 hours)
                cursor.execute("""
                    SELECT COUNT(*) as count 
                    FROM audit_log 
                    WHERE event_timestamp >= datetime('now', '-1 day')
                """)
                recent_activity = cursor.fetchone()['count']
                
                # Date range
                cursor.execute("""
                    SELECT 
                        MIN(event_timestamp) as earliest,
                        MAX(event_timestamp) as latest
                    FROM audit_log
                """)
                date_range = cursor.fetchone()
                
                return {
                    'total_records': total_records,
                    'by_event_type': by_event_type,
                    'by_user': by_user,
                    'file_operations': file_operations,
                    'recent_activity_24h': recent_activity,
                    'date_range': {
                        'earliest': date_range['earliest'],
                        'latest': date_range['latest']
                    },
                    'retention_policy': f"{self.retention_years} years",
                    'generated_at': datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Failed to get audit statistics: {e}")
            return {'error': str(e)}
    
    def export_audit_log(self,
                        output_path: str,
                        user_id: Optional[str] = None,
                        event_type: Optional[str] = None,
                        start_date: Optional[str] = None,
                        end_date: Optional[str] = None,
                        format: str = 'json') -> Dict[str, Any]:
        """
        Export audit log to file
        
        Args:
            output_path: Path to output file
            user_id: Filter by user ID
            event_type: Filter by event type
            start_date: Filter by start date
            end_date: Filter by end date
            format: Export format ('json' or 'csv')
        
        Returns:
            Dict containing export results
        """
        try:
            # Get audit data
            audit_data = self.get_audit_log(
                user_id=user_id,
                event_type=event_type,
                start_date=start_date,
                end_date=end_date,
                limit=100000  # Large limit for export
            )
            
            if format.lower() == 'json':
                with open(output_path, 'w') as f:
                    json.dump(audit_data, f, indent=2, default=str)
            elif format.lower() == 'csv':
                import csv
                if audit_data:
                    with open(output_path, 'w', newline='') as f:
                        writer = csv.DictWriter(f, fieldnames=audit_data[0].keys())
                        writer.writeheader()
                        writer.writerows(audit_data)
            else:
                raise ValueError(f"Unsupported format: {format}")
            
            return {
                'success': True,
                'records_exported': len(audit_data),
                'output_path': output_path,
                'format': format
            }
            
        except Exception as e:
            self.logger.error(f"Failed to export audit log: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Convenience functions for easy integration

def get_audit_manager() -> AuditManager:
    """Get singleton audit manager instance"""
    if not hasattr(get_audit_manager, '_instance'):
        get_audit_manager._instance = AuditManager()
    return get_audit_manager._instance


def log_audit_event(user_id: str, event_type: Union[AuditEventType, str], **kwargs) -> int:
    """Convenience function to log an audit event"""
    manager = get_audit_manager()
    return manager.log_audit_event(user_id, event_type, **kwargs)


def log_database_operation(user_id: str, event_type: Union[AuditEventType, str], 
                          table_name: str, record_id: str, **kwargs) -> int:
    """Convenience function to log a database operation"""
    manager = get_audit_manager()
    return manager.log_database_operation(user_id, event_type, table_name, record_id, **kwargs)


def log_file_operation(user_id: str, event_type: Union[AuditEventType, str], 
                      file_path: str, **kwargs) -> int:
    """Convenience function to log a file operation"""
    manager = get_audit_manager()
    return manager.log_file_operation(user_id, event_type, file_path, **kwargs)
