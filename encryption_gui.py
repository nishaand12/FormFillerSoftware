#!/usr/bin/env python3
"""
Encryption Management GUI for Physiotherapy Clinic Assistant
Provides user interface for managing encryption settings and monitoring encryption status
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from encrypted_database_manager import EncryptedDatabaseManager
from file_encryption_service import FileEncryptionService
from encryption_manager import get_encryption_manager
from encryption_migration import EncryptionMigration


class EncryptionManagementGUI:
    """GUI for managing encryption settings and monitoring"""
    
    def __init__(self, parent, db_manager: EncryptedDatabaseManager):
        self.parent = parent
        self.db_manager = db_manager
        self.encryption_service = FileEncryptionService(db_manager)
        self.encryption_manager = get_encryption_manager()
        self.migration = EncryptionMigration()
        
        self.encryption_window = None
        self.status_vars = {}
        
    def show_encryption_manager(self):
        """Show the encryption management window"""
        if self.encryption_window:
            self.encryption_window.lift()
            return
        
        self.encryption_window = tk.Toplevel(self.parent)
        self.encryption_window.title("Encryption Management")
        self.encryption_window.geometry("1000x800")
        self.encryption_window.resizable(True, True)
        
        # Center the window
        self.encryption_window.transient(self.parent)
        self.encryption_window.grab_set()
        
        self.create_widgets()
        self.load_encryption_status()
        
        # Handle window close
        self.encryption_window.protocol("WM_DELETE_WINDOW", self.close_encryption_manager)
    
    def create_widgets(self):
        """Create the encryption management widgets"""
        # Main frame with notebook
        main_frame = ttk.Frame(self.encryption_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.encryption_window.columnconfigure(0, weight=1)
        self.encryption_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Status tab
        self.create_status_tab()
        
        # Key management tab
        self.create_key_management_tab()
        
        # File encryption tab
        self.create_file_encryption_tab()
        
        # Migration tab
        self.create_migration_tab()
        
        # Audit tab
        self.create_audit_tab()
    
    def create_status_tab(self):
        """Create the encryption status tab"""
        status_frame = ttk.Frame(self.notebook)
        self.notebook.add(status_frame, text="Encryption Status")
        
        # Title
        title_label = ttk.Label(status_frame, text="Encryption Status Overview", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Status information frame
        info_frame = ttk.LabelFrame(status_frame, text="Encryption Status", padding="10")
        info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Status variables
        self.status_vars = {
            'encryption_enabled': tk.StringVar(),
            'current_key_id': tk.StringVar(),
            'key_expiry': tk.StringVar(),
            'total_appointments': tk.StringVar(),
            'encrypted_appointments': tk.StringVar(),
            'total_files': tk.StringVar(),
            'encrypted_files': tk.StringVar(),
            'encryption_rate': tk.StringVar()
        }
        
        # Status labels
        row = 0
        for label_text, var_name in [
            ("Encryption Status:", 'encryption_enabled'),
            ("Current Key ID:", 'current_key_id'),
            ("Key Expires:", 'key_expiry'),
            ("Total Appointments:", 'total_appointments'),
            ("Encrypted Appointments:", 'encrypted_appointments'),
            ("Total Files:", 'total_files'),
            ("Encrypted Files:", 'encrypted_files'),
            ("Encryption Rate:", 'encryption_rate')
        ]:
            ttk.Label(info_frame, text=label_text).grid(row=row, column=0, sticky=tk.W, pady=5)
            ttk.Label(info_frame, textvariable=self.status_vars[var_name], 
                     font=("Arial", 10, "bold")).grid(row=row, column=1, sticky=tk.W, pady=5)
            row += 1
        
        # File type encryption status
        file_type_frame = ttk.LabelFrame(status_frame, text="File Type Encryption Status", padding="10")
        file_type_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # File type treeview
        columns = ('type', 'total', 'encrypted', 'unencrypted', 'rate')
        self.file_type_tree = ttk.Treeview(file_type_frame, columns=columns, show='headings', height=8)
        
        self.file_type_tree.heading('type', text='File Type')
        self.file_type_tree.heading('total', text='Total')
        self.file_type_tree.heading('encrypted', text='Encrypted')
        self.file_type_tree.heading('unencrypted', text='Unencrypted')
        self.file_type_tree.heading('rate', text='Encryption Rate')
        
        self.file_type_tree.column('type', width=100)
        self.file_type_tree.column('total', width=80)
        self.file_type_tree.column('encrypted', width=80)
        self.file_type_tree.column('unencrypted', width=80)
        self.file_type_tree.column('rate', width=100)
        
        self.file_type_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Buttons
        button_frame = ttk.Frame(status_frame)
        button_frame.grid(row=3, column=0, pady=(20, 0))
        
        refresh_button = ttk.Button(button_frame, text="Refresh Status", 
                                  command=self.load_encryption_status)
        refresh_button.pack(side=tk.LEFT, padx=(0, 10))
        
        close_button = ttk.Button(button_frame, text="Close", 
                                 command=self.close_encryption_manager)
        close_button.pack(side=tk.RIGHT)
    
    def create_key_management_tab(self):
        """Create the key management tab"""
        key_frame = ttk.Frame(self.notebook)
        self.notebook.add(key_frame, text="Key Management")
        
        # Title
        title_label = ttk.Label(key_frame, text="Encryption Key Management", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Key information frame
        key_info_frame = ttk.LabelFrame(key_frame, text="Current Key Information", padding="10")
        key_info_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Key info variables
        self.key_vars = {
            'current_key_id': tk.StringVar(),
            'key_created': tk.StringVar(),
            'key_expires': tk.StringVar(),
            'days_remaining': tk.StringVar(),
            'key_type': tk.StringVar()
        }
        
        row = 0
        for label_text, var_name in [
            ("Current Key ID:", 'current_key_id'),
            ("Key Created:", 'key_created'),
            ("Key Expires:", 'key_expires'),
            ("Days Remaining:", 'days_remaining'),
            ("Key Type:", 'key_type')
        ]:
            ttk.Label(key_info_frame, text=label_text).grid(row=row, column=0, sticky=tk.W, pady=5)
            ttk.Label(key_info_frame, textvariable=self.key_vars[var_name]).grid(row=row, column=1, sticky=tk.W, pady=5)
            row += 1
        
        # Key history frame
        history_frame = ttk.LabelFrame(key_frame, text="Key History", padding="10")
        history_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # Key history treeview
        key_columns = ('key_id', 'created', 'expires', 'active', 'days_remaining')
        self.key_history_tree = ttk.Treeview(history_frame, columns=key_columns, show='headings', height=6)
        
        self.key_history_tree.heading('key_id', text='Key ID')
        self.key_history_tree.heading('created', text='Created')
        self.key_history_tree.heading('expires', text='Expires')
        self.key_history_tree.heading('active', text='Active')
        self.key_history_tree.heading('days_remaining', text='Days Remaining')
        
        self.key_history_tree.column('key_id', width=150)
        self.key_history_tree.column('created', width=120)
        self.key_history_tree.column('expires', width=120)
        self.key_history_tree.column('active', width=80)
        self.key_history_tree.column('days_remaining', width=100)
        
        self.key_history_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Key management buttons
        key_button_frame = ttk.Frame(key_frame)
        key_button_frame.grid(row=3, column=0, pady=(20, 0))
        
        rotate_key_button = ttk.Button(key_button_frame, text="Force Key Rotation", 
                                      command=self.force_key_rotation)
        rotate_key_button.pack(side=tk.LEFT, padx=(0, 10))
        
        backup_keys_button = ttk.Button(key_button_frame, text="Backup Keys", 
                                       command=self.backup_encryption_keys)
        backup_keys_button.pack(side=tk.LEFT, padx=(0, 10))
        
        restore_keys_button = ttk.Button(key_button_frame, text="Restore Keys", 
                                        command=self.restore_encryption_keys)
        restore_keys_button.pack(side=tk.LEFT, padx=(0, 10))
    
    def create_file_encryption_tab(self):
        """Create the file encryption tab"""
        file_frame = ttk.Frame(self.notebook)
        self.notebook.add(file_frame, text="File Encryption")
        
        # Title
        title_label = ttk.Label(file_frame, text="File Encryption Management", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # File encryption controls
        controls_frame = ttk.LabelFrame(file_frame, text="File Encryption Controls", padding="10")
        controls_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Encrypt all files button
        encrypt_all_button = ttk.Button(controls_frame, text="Encrypt All Unencrypted Files", 
                                       command=self.encrypt_all_files)
        encrypt_all_button.grid(row=0, column=0, padx=(0, 10), pady=5)
        
        # Decrypt files button
        decrypt_button = ttk.Button(controls_frame, text="Decrypt Files for Access", 
                                    command=self.decrypt_files_for_access)
        decrypt_button.grid(row=0, column=1, padx=(0, 10), pady=5)
        
        # Cleanup temp files button
        cleanup_button = ttk.Button(controls_frame, text="Cleanup Temporary Files", 
                                   command=self.cleanup_temp_files)
        cleanup_button.grid(row=0, column=2, pady=5)
        
        # File encryption status
        file_status_frame = ttk.LabelFrame(file_frame, text="File Encryption Status", padding="10")
        file_status_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # File status treeview
        file_columns = ('type', 'total', 'encrypted', 'unencrypted', 'rate')
        self.file_status_tree = ttk.Treeview(file_status_frame, columns=file_columns, show='headings', height=8)
        
        self.file_status_tree.heading('type', text='File Type')
        self.file_status_tree.heading('total', text='Total')
        self.file_status_tree.heading('encrypted', text='Encrypted')
        self.file_status_tree.heading('unencrypted', text='Unencrypted')
        self.file_status_tree.heading('rate', text='Encryption Rate')
        
        self.file_status_tree.column('type', width=100)
        self.file_status_tree.column('total', width=80)
        self.file_status_tree.column('encrypted', width=80)
        self.file_status_tree.column('unencrypted', width=80)
        self.file_status_tree.column('rate', width=100)
        
        self.file_status_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
    
    def create_migration_tab(self):
        """Create the migration tab"""
        migration_frame = ttk.Frame(self.notebook)
        self.notebook.add(migration_frame, text="Data Migration")
        
        # Title
        title_label = ttk.Label(migration_frame, text="Data Migration to Encryption", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Migration status
        status_frame = ttk.LabelFrame(migration_frame, text="Migration Status", padding="10")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.migration_vars = {
            'migration_ready': tk.StringVar(),
            'total_appointments': tk.StringVar(),
            'encrypted_appointments': tk.StringVar(),
            'total_files': tk.StringVar(),
            'encrypted_files': tk.StringVar()
        }
        
        row = 0
        for label_text, var_name in [
            ("Migration Ready:", 'migration_ready'),
            ("Total Appointments:", 'total_appointments'),
            ("Encrypted Appointments:", 'encrypted_appointments'),
            ("Total Files:", 'total_files'),
            ("Encrypted Files:", 'encrypted_files')
        ]:
            ttk.Label(status_frame, text=label_text).grid(row=row, column=0, sticky=tk.W, pady=5)
            ttk.Label(status_frame, textvariable=self.migration_vars[var_name]).grid(row=row, column=1, sticky=tk.W, pady=5)
            row += 1
        
        # Migration controls
        controls_frame = ttk.LabelFrame(migration_frame, text="Migration Controls", padding="10")
        controls_frame.grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Migration buttons
        check_migration_button = ttk.Button(controls_frame, text="Check Migration Status", 
                                           command=self.check_migration_status)
        check_migration_button.grid(row=0, column=0, padx=(0, 10), pady=5)
        
        create_backup_button = ttk.Button(controls_frame, text="Create Migration Backup", 
                                         command=self.create_migration_backup)
        create_backup_button.grid(row=0, column=1, padx=(0, 10), pady=5)
        
        run_migration_button = ttk.Button(controls_frame, text="Run Full Migration", 
                                         command=self.run_full_migration)
        run_migration_button.grid(row=0, column=2, pady=5)
        
        # Migration progress
        progress_frame = ttk.LabelFrame(migration_frame, text="Migration Progress", padding="10")
        progress_frame.grid(row=3, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.migration_progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.migration_progress.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=5)
        
        self.migration_status_var = tk.StringVar(value="Ready")
        ttk.Label(progress_frame, textvariable=self.migration_status_var).grid(row=1, column=0, pady=5)
    
    def create_audit_tab(self):
        """Create the audit log tab"""
        audit_frame = ttk.Frame(self.notebook)
        self.notebook.add(audit_frame, text="Audit Log")
        
        # Title
        title_label = ttk.Label(audit_frame, text="Audit Log Viewer", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Audit log controls
        controls_frame = ttk.LabelFrame(audit_frame, text="Audit Log Controls", padding="10")
        controls_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Filter controls
        ttk.Label(controls_frame, text="Event Type:").grid(row=0, column=0, padx=(0, 5))
        self.event_type_var = tk.StringVar()
        event_type_combo = ttk.Combobox(controls_frame, textvariable=self.event_type_var, 
                                       values=['ALL', 'CREATE', 'READ', 'UPDATE', 'DELETE', 'ENCRYPT', 'DECRYPT'])
        event_type_combo.grid(row=0, column=1, padx=(0, 10))
        event_type_combo.set('ALL')
        
        ttk.Label(controls_frame, text="Limit:").grid(row=0, column=2, padx=(10, 5))
        self.limit_var = tk.StringVar(value="100")
        limit_entry = ttk.Entry(controls_frame, textvariable=self.limit_var, width=10)
        limit_entry.grid(row=0, column=3, padx=(0, 10))
        
        refresh_audit_button = ttk.Button(controls_frame, text="Refresh Audit Log", 
                                         command=self.load_audit_log)
        refresh_audit_button.grid(row=0, column=4, padx=(0, 10))
        
        verify_integrity_button = ttk.Button(controls_frame, text="Verify Integrity", 
                                            command=self.verify_audit_integrity)
        verify_integrity_button.grid(row=0, column=5)
        
        # Audit log display
        log_frame = ttk.LabelFrame(audit_frame, text="Audit Log Entries", padding="10")
        log_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Audit log treeview
        audit_columns = ('timestamp', 'user_id', 'event_type', 'table_name', 'record_id', 'details')
        self.audit_tree = ttk.Treeview(log_frame, columns=audit_columns, show='headings', height=15)
        
        self.audit_tree.heading('timestamp', text='Timestamp')
        self.audit_tree.heading('user_id', text='User ID')
        self.audit_tree.heading('event_type', text='Event Type')
        self.audit_tree.heading('table_name', text='Table')
        self.audit_tree.heading('record_id', text='Record ID')
        self.audit_tree.heading('details', text='Details')
        
        self.audit_tree.column('timestamp', width=150)
        self.audit_tree.column('user_id', width=100)
        self.audit_tree.column('event_type', width=80)
        self.audit_tree.column('table_name', width=100)
        self.audit_tree.column('record_id', width=100)
        self.audit_tree.column('details', width=200)
        
        # Scrollbar for audit tree
        audit_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.audit_tree.yview)
        self.audit_tree.configure(yscrollcommand=audit_scrollbar.set)
        
        self.audit_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        audit_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
    
    def load_encryption_status(self):
        """Load and display encryption status"""
        try:
            # Get encryption status
            status = self.db_manager.get_encryption_status()
            
            # Update status variables
            self.status_vars['encryption_enabled'].set("Enabled" if status.get('encryption_enabled') else "Disabled")
            self.status_vars['current_key_id'].set(status.get('encryption_keys', {}).get('current_key_id', 'N/A'))
            
            # Calculate key expiry
            keys = status.get('encryption_keys', {}).get('keys', {})
            current_key_id = status.get('encryption_keys', {}).get('current_key_id')
            if current_key_id and current_key_id in keys:
                key_info = keys[current_key_id]
                self.status_vars['key_expiry'].set(key_info.get('expires_at', 'N/A'))
                self.status_vars['key_expiry'].set(f"{key_info.get('days_until_expiry', 0)} days")
            
            # Update appointment and file statistics
            appointment_stats = status.get('appointment_encryption', {})
            self.status_vars['total_appointments'].set(appointment_stats.get('total_appointments', 0))
            self.status_vars['encrypted_appointments'].set(appointment_stats.get('encrypted_appointments', 0))
            
            file_stats = status.get('file_encryption', {})
            self.status_vars['total_files'].set(file_stats.get('total_files', 0))
            self.status_vars['encrypted_files'].set(file_stats.get('encrypted_files', 0))
            
            # Calculate encryption rate
            total_appointments = appointment_stats.get('total_appointments', 0)
            encrypted_appointments = appointment_stats.get('encrypted_appointments', 0)
            if total_appointments > 0:
                rate = (encrypted_appointments / total_appointments) * 100
                self.status_vars['encryption_rate'].set(f"{rate:.1f}%")
            else:
                self.status_vars['encryption_rate'].set("N/A")
            
            # Load file type encryption status
            self.load_file_type_status()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load encryption status: {str(e)}")
    
    def load_file_type_status(self):
        """Load file type encryption status"""
        try:
            # Clear existing items
            for item in self.file_type_tree.get_children():
                self.file_type_tree.delete(item)
            
            # Get file encryption status
            file_status = self.encryption_service.get_encryption_status()
            
            # Add file type statistics
            for file_type, stats in file_status.get('by_type', {}).items():
                rate = stats.get('encryption_rate', 0)
                self.file_type_tree.insert('', 'end', values=(
                    file_type,
                    stats.get('total', 0),
                    stats.get('encrypted', 0),
                    stats.get('unencrypted', 0),
                    f"{rate:.1f}%"
                ))
            
        except Exception as e:
            print(f"Failed to load file type status: {e}")
    
    def force_key_rotation(self):
        """Force immediate key rotation"""
        try:
            if messagebox.askyesno("Confirm Key Rotation", 
                                 "Are you sure you want to force key rotation?\n\nThis will create a new encryption key."):
                new_key_id = self.encryption_manager.force_key_rotation()
                messagebox.showinfo("Success", f"Key rotation completed. New key ID: {new_key_id}")
                self.load_encryption_status()
        except Exception as e:
            messagebox.showerror("Error", f"Key rotation failed: {str(e)}")
    
    def backup_encryption_keys(self):
        """Backup encryption keys"""
        try:
            backup_path = filedialog.asksaveasfilename(
                title="Save Key Backup",
                defaultextension=".keybackup",
                filetypes=[("Key Backup Files", "*.keybackup"), ("All Files", "*.*")]
            )
            
            if backup_path:
                password = tk.simpledialog.askstring("Backup Password", 
                                                   "Enter password for key backup (min 12 characters):",
                                                   show='*')
                if password and len(password) >= 12:
                    success = self.encryption_manager.backup_keys(backup_path, password)
                    if success:
                        messagebox.showinfo("Success", f"Keys backed up to: {backup_path}")
                    else:
                        messagebox.showerror("Error", "Key backup failed")
                else:
                    messagebox.showerror("Error", "Password must be at least 12 characters")
        except Exception as e:
            messagebox.showerror("Error", f"Key backup failed: {str(e)}")
    
    def restore_encryption_keys(self):
        """Restore encryption keys from backup"""
        try:
            backup_path = filedialog.askopenfilename(
                title="Select Key Backup",
                filetypes=[("Key Backup Files", "*.keybackup"), ("All Files", "*.*")]
            )
            
            if backup_path:
                password = tk.simpledialog.askstring("Backup Password", 
                                                   "Enter password for key backup:",
                                                   show='*')
                if password:
                    success = self.encryption_manager.restore_keys(backup_path, password)
                    if success:
                        messagebox.showinfo("Success", "Keys restored successfully")
                        self.load_encryption_status()
                    else:
                        messagebox.showerror("Error", "Key restore failed")
        except Exception as e:
            messagebox.showerror("Error", f"Key restore failed: {str(e)}")
    
    def encrypt_all_files(self):
        """Encrypt all unencrypted files"""
        try:
            if messagebox.askyesno("Confirm Encryption", 
                                 "Are you sure you want to encrypt all unencrypted files?\n\nThis may take some time."):
                
                def encrypt_worker():
                    try:
                        result = self.encryption_service.bulk_encrypt_unencrypted_files("admin", limit=1000)
                        
                        # Update UI in main thread
                        self.encryption_window.after(0, lambda: self._encrypt_complete(result))
                    except Exception as e:
                        self.encryption_window.after(0, lambda: messagebox.showerror("Error", f"Encryption failed: {str(e)}"))
                
                # Start encryption in background thread
                threading.Thread(target=encrypt_worker, daemon=True).start()
                messagebox.showinfo("Info", "File encryption started in background. Check status tab for progress.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start encryption: {str(e)}")
    
    def _encrypt_complete(self, result):
        """Handle encryption completion"""
        if result['success']:
            messagebox.showinfo("Success", f"Encryption completed: {result['message']}")
        else:
            messagebox.showerror("Error", f"Encryption failed: {result['message']}")
        
        self.load_encryption_status()
    
    def decrypt_files_for_access(self):
        """Decrypt files for temporary access"""
        try:
            # This would typically be called when user wants to access files
            messagebox.showinfo("Info", "File decryption is handled automatically when accessing files.")
        except Exception as e:
            messagebox.showerror("Error", f"Decryption failed: {str(e)}")
    
    def cleanup_temp_files(self):
        """Clean up temporary decrypted files"""
        try:
            result = self.encryption_service.cleanup_temp_files()
            if result['success']:
                messagebox.showinfo("Success", f"Cleanup completed: {result['message']}")
            else:
                messagebox.showerror("Error", f"Cleanup failed: {result['message']}")
        except Exception as e:
            messagebox.showerror("Error", f"Cleanup failed: {str(e)}")
    
    def check_migration_status(self):
        """Check migration status"""
        try:
            status = self.migration.check_migration_status()
            
            # Update migration variables
            self.migration_vars['migration_ready'].set("Yes" if status.get('migration_ready') else "No")
            self.migration_vars['total_appointments'].set(status.get('appointments', {}).get('total_appointments', 0))
            self.migration_vars['encrypted_appointments'].set(status.get('appointments', {}).get('encrypted_appointments', 0))
            self.migration_vars['total_files'].set(status.get('files', {}).get('total_files', 0))
            self.migration_vars['encrypted_files'].set(status.get('files', {}).get('encrypted_files', 0))
            
            messagebox.showinfo("Migration Status", f"Migration ready: {status.get('migration_ready', False)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to check migration status: {str(e)}")
    
    def create_migration_backup(self):
        """Create migration backup"""
        try:
            backup_path = f"migration_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            result = self.migration.create_migration_backup(backup_path)
            
            if result['success']:
                messagebox.showinfo("Success", f"Migration backup created: {result['backup_path']}")
            else:
                messagebox.showerror("Error", f"Backup creation failed: {result['message']}")
        except Exception as e:
            messagebox.showerror("Error", f"Backup creation failed: {str(e)}")
    
    def run_full_migration(self):
        """Run full migration"""
        try:
            if messagebox.askyesno("Confirm Migration", 
                                 "Are you sure you want to run full migration?\n\nThis will encrypt all existing data."):
                
                def migration_worker():
                    try:
                        self.migration_progress.start()
                        self.migration_status_var.set("Running migration...")
                        
                        result = self.migration.run_full_migration(create_backup=True)
                        
                        # Update UI in main thread
                        self.encryption_window.after(0, lambda: self._migration_complete(result))
                    except Exception as e:
                        self.encryption_window.after(0, lambda: self._migration_error(str(e)))
                
                # Start migration in background thread
                threading.Thread(target=migration_worker, daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start migration: {str(e)}")
    
    def _migration_complete(self, result):
        """Handle migration completion"""
        self.migration_progress.stop()
        
        if result['success']:
            self.migration_status_var.set("Migration completed successfully")
            messagebox.showinfo("Success", f"Migration completed: {result['message']}")
        else:
            self.migration_status_var.set("Migration failed")
            messagebox.showerror("Error", f"Migration failed: {result['message']}")
        
        self.check_migration_status()
    
    def _migration_error(self, error):
        """Handle migration error"""
        self.migration_progress.stop()
        self.migration_status_var.set("Migration failed")
        messagebox.showerror("Error", f"Migration failed: {error}")
    
    def load_audit_log(self):
        """Load audit log entries"""
        try:
            # Clear existing items
            for item in self.audit_tree.get_children():
                self.audit_tree.delete(item)
            
            # Get filter parameters
            event_type = self.event_type_var.get()
            limit = int(self.limit_var.get()) if self.limit_var.get().isdigit() else 100
            
            # Get audit log entries
            entries = self.db_manager.get_audit_log(
                event_type=event_type if event_type != 'ALL' else None,
                limit=limit
            )
            
            # Add entries to tree
            for entry in entries:
                self.audit_tree.insert('', 'end', values=(
                    entry.get('event_timestamp', ''),
                    entry.get('user_id', ''),
                    entry.get('event_type', ''),
                    entry.get('table_name', ''),
                    entry.get('record_id', ''),
                    entry.get('operation_details', '')
                ))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load audit log: {str(e)}")
    
    def verify_audit_integrity(self):
        """Verify audit log integrity"""
        try:
            result = self.db_manager.verify_audit_integrity()
            
            if result['is_intact']:
                messagebox.showinfo("Integrity Check", "Audit log integrity verified successfully")
            else:
                issues = result.get('integrity_issues', [])
                messagebox.showwarning("Integrity Issues", 
                                     f"Found {len(issues)} integrity issues in audit log")
        except Exception as e:
            messagebox.showerror("Error", f"Integrity verification failed: {str(e)}")
    
    def close_encryption_manager(self):
        """Close the encryption management window"""
        if self.encryption_window:
            self.encryption_window.destroy()
            self.encryption_window = None
