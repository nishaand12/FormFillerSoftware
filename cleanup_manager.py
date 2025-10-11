#!/usr/bin/env python3
"""
Cleanup Manager for Physiotherapy Clinic Assistant
Handles automatic and manual file cleanup based on retention policies
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List
from database_manager import DatabaseManager


class CleanupManager:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.cleanup_thread = None
        self.is_running = False
        self.last_cleanup = None
        
    def start_automatic_cleanup(self):
        """Start automatic cleanup in background thread"""
        if self.is_running:
            return
        
        self.is_running = True
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        print("Automatic cleanup started")
    
    def stop_automatic_cleanup(self):
        """Stop automatic cleanup"""
        self.is_running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        print("Automatic cleanup stopped")
    
    def _cleanup_loop(self):
        """Main cleanup loop"""
        while self.is_running:
            try:
                # Check if cleanup is enabled
                if not self.db_manager.get_setting('auto_cleanup_enabled', True):
                    time.sleep(60)  # Check every minute
                    continue
                
                # Get cleanup frequency
                frequency_hours = self.db_manager.get_setting('cleanup_frequency_hours', 24)
                
                # Check if it's time for cleanup
                if self.last_cleanup is None or \
                   datetime.now() - self.last_cleanup > timedelta(hours=frequency_hours):
                    
                    print(f"Running automatic cleanup at {datetime.now()}")
                    result = self.db_manager.cleanup_expired_files()
                    
                    if result['files_deleted'] > 0:
                        print(f"Cleanup completed: {result['details']}")
                    
                    self.last_cleanup = datetime.now()
                
                # Sleep for 1 hour before checking again
                time.sleep(3600)
                
            except Exception as e:
                print(f"Error in cleanup loop: {e}")
                time.sleep(300)  # Wait 5 minutes before retrying
    
    def run_manual_cleanup(self) -> Dict:
        """Run manual cleanup and return results"""
        try:
            print("Running manual cleanup...")
            result = self.db_manager.cleanup_expired_files()
            
            # Clean up empty date folders
            try:
                self.db_manager.cleanup_empty_date_folders()
            except Exception as e:
                print(f"Warning: Could not cleanup empty date folders: {e}")
            
            self.last_cleanup = datetime.now()
            return result
        except Exception as e:
            print(f"Error in manual cleanup: {e}")
            return {'files_deleted': 0, 'space_freed': 0, 'details': f"Error: {str(e)}"}
    
    def get_cleanup_preview(self) -> List[Dict]:
        """Get list of files that would be cleaned up"""
        try:
            with self.db_manager.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT f.file_id, f.file_path, f.file_type, f.retention_policy, 
                           f.file_size, f.retention_date, a.appointment_code,
                           a.patient_name
                    FROM files f
                    JOIN appointments a ON f.appointment_id = a.appointment_id
                    WHERE f.retention_date <= date('now') AND f.is_deleted = 0
                    ORDER BY f.retention_date
                """)
                
                files = []
                for row in cursor.fetchall():
                    files.append({
                        'file_id': row['file_id'],
                        'file_path': row['file_path'],
                        'file_type': row['file_type'],
                        'retention_policy': row['retention_policy'],
                        'file_size': row['file_size'],
                        'retention_date': row['retention_date'],
                        'appointment_code': row['appointment_code'],
                        'patient_name': row['patient_name']
                    })
                
                return files
        except Exception as e:
            print(f"Error getting cleanup preview: {e}")
            return []


class CleanupGUI:
    def __init__(self, parent, cleanup_manager: CleanupManager):
        self.parent = parent
        self.cleanup_manager = cleanup_manager
        self.cleanup_window = None
        
    def show_cleanup_manager(self):
        """Show the cleanup management window"""
        if self.cleanup_window:
            self.cleanup_window.lift()
            return
        
        self.cleanup_window = tk.Toplevel(self.parent)
        self.cleanup_window.title("File Cleanup Manager")
        self.cleanup_window.geometry("900x700")
        self.cleanup_window.resizable(True, True)
        
        # Center the window
        self.cleanup_window.transient(self.parent)
        self.cleanup_window.grab_set()
        
        self.create_widgets()
        self.load_cleanup_info()
        
        # Handle window close
        self.cleanup_window.protocol("WM_DELETE_WINDOW", self.close_cleanup_manager)
    
    def create_widgets(self):
        """Create the cleanup management widgets"""
        # Main frame
        main_frame = ttk.Frame(self.cleanup_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.cleanup_window.columnconfigure(0, weight=1)
        self.cleanup_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="File Cleanup Manager", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, pady=(0, 20))
        
        # Status frame
        status_frame = ttk.LabelFrame(main_frame, text="Cleanup Status", padding="10")
        status_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Status information
        row = 0
        ttk.Label(status_frame, text="Automatic Cleanup:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.auto_cleanup_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.auto_cleanup_var, font=("Arial", 10, "bold")).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        ttk.Label(status_frame, text="Last Cleanup:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.last_cleanup_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.last_cleanup_var).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        ttk.Label(status_frame, text="Next Cleanup:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.next_cleanup_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.next_cleanup_var).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Storage stats
        ttk.Label(status_frame, text="Total Storage:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.total_storage_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.total_storage_var).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        ttk.Label(status_frame, text="Files Expiring Soon:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.expiring_soon_var = tk.StringVar()
        ttk.Label(status_frame, textvariable=self.expiring_soon_var).grid(row=row, column=1, sticky=tk.W, pady=5)
        row += 1
        
        # Files to cleanup frame
        files_frame = ttk.LabelFrame(main_frame, text="Files Ready for Cleanup", padding="10")
        files_frame.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        files_frame.columnconfigure(0, weight=1)
        files_frame.rowconfigure(0, weight=1)
        
        # Files treeview
        columns = ('patient', 'appointment', 'type', 'size', 'retention_date', 'policy')
        self.files_tree = ttk.Treeview(files_frame, columns=columns, show='headings', height=15)
        
        # Define headings
        self.files_tree.heading('patient', text='Patient')
        self.files_tree.heading('appointment', text='Appointment')
        self.files_tree.heading('type', text='File Type')
        self.files_tree.heading('size', text='Size')
        self.files_tree.heading('retention_date', text='Retention Date')
        self.files_tree.heading('policy', text='Policy')
        
        # Define columns
        self.files_tree.column('patient', width=150)
        self.files_tree.column('appointment', width=150)
        self.files_tree.column('type', width=100)
        self.files_tree.column('size', width=80)
        self.files_tree.column('retention_date', width=120)
        self.files_tree.column('policy', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(files_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=scrollbar.set)
        
        self.files_tree.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=3, column=0, pady=(20, 0))
        
        # Buttons
        refresh_button = ttk.Button(buttons_frame, text="Refresh", command=self.load_cleanup_info)
        refresh_button.pack(side=tk.LEFT, padx=(0, 10))
        
        preview_button = ttk.Button(buttons_frame, text="Preview Cleanup", command=self.preview_cleanup)
        preview_button.pack(side=tk.LEFT, padx=(0, 10))
        
        cleanup_button = ttk.Button(buttons_frame, text="Run Cleanup", command=self.run_cleanup)
        cleanup_button.pack(side=tk.LEFT, padx=(0, 10))
        
        close_button = ttk.Button(buttons_frame, text="Close", command=self.close_cleanup_manager)
        close_button.pack(side=tk.RIGHT)
    
    def load_cleanup_info(self):
        """Load cleanup status and file information"""
        try:
            # Get automatic cleanup status
            auto_cleanup_enabled = self.cleanup_manager.db_manager.get_setting('auto_cleanup_enabled', True)
            self.auto_cleanup_var.set("Enabled" if auto_cleanup_enabled else "Disabled")
            
            # Get last cleanup time
            if self.cleanup_manager.last_cleanup:
                last_cleanup_str = self.cleanup_manager.last_cleanup.strftime('%Y-%m-%d %H:%M:%S')
            else:
                last_cleanup_str = "Never"
            self.last_cleanup_var.set(last_cleanup_str)
            
            # Calculate next cleanup time
            frequency_hours = self.cleanup_manager.db_manager.get_setting('cleanup_frequency_hours', 24)
            if self.cleanup_manager.last_cleanup:
                next_cleanup = self.cleanup_manager.last_cleanup + timedelta(hours=frequency_hours)
                next_cleanup_str = next_cleanup.strftime('%Y-%m-%d %H:%M:%S')
            else:
                next_cleanup_str = "Unknown"
            self.next_cleanup_var.set(next_cleanup_str)
            
            # Get storage statistics
            stats = self.cleanup_manager.db_manager.get_storage_stats()
            
            # Format total storage
            total_size = stats['total_size'] or 0
            if total_size > 1024 * 1024 * 1024:
                storage_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
            elif total_size > 1024 * 1024:
                storage_str = f"{total_size / (1024 * 1024):.2f} MB"
            elif total_size > 1024:
                storage_str = f"{total_size / 1024:.2f} KB"
            else:
                storage_str = f"{total_size} B"
            
            self.total_storage_var.set(f"{stats['total_files']} files, {storage_str}")
            self.expiring_soon_var.set(str(stats['expiring_soon']))
            
            # Load files ready for cleanup
            self.load_cleanup_files()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load cleanup information: {str(e)}")
    
    def load_cleanup_files(self):
        """Load files that are ready for cleanup"""
        # Clear existing items
        for item in self.files_tree.get_children():
            self.files_tree.delete(item)
        
        # Get files ready for cleanup
        files = self.cleanup_manager.get_cleanup_preview()
        
        for file in files:
            # Format file size
            size = file['file_size'] or 0
            if size > 1024 * 1024:
                size_str = f"{size / (1024 * 1024):.1f} MB"
            elif size > 1024:
                size_str = f"{size / 1024:.1f} KB"
            else:
                size_str = f"{size} B"
            
            # Insert into treeview
            self.files_tree.insert('', 'end', values=(
                file['patient_name'],
                file['appointment_code'],
                file['file_type'],
                size_str,
                file['retention_date'],
                file['retention_policy']
            ))
    
    def preview_cleanup(self):
        """Show preview of what would be cleaned up"""
        files = self.cleanup_manager.get_cleanup_preview()
        
        if not files:
            messagebox.showinfo("Preview", "No files are ready for cleanup.")
            return
        
        # Calculate total size
        total_size = sum(f['file_size'] or 0 for f in files)
        if total_size > 1024 * 1024 * 1024:
            size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
        elif total_size > 1024 * 1024:
            size_str = f"{total_size / (1024 * 1024):.2f} MB"
        elif total_size > 1024:
            size_str = f"{total_size / 1024:.2f} KB"
        else:
            size_str = f"{total_size} B"
        
        # Group by file type
        by_type = {}
        for file in files:
            file_type = file['file_type']
            if file_type not in by_type:
                by_type[file_type] = {'count': 0, 'size': 0}
            by_type[file_type]['count'] += 1
            by_type[file_type]['size'] += file['file_size'] or 0
        
        # Create preview message
        message = f"Cleanup Preview:\n\n"
        message += f"Total files to delete: {len(files)}\n"
        message += f"Total space to free: {size_str}\n\n"
        message += "Files by type:\n"
        
        for file_type, info in by_type.items():
            if info['size'] > 1024 * 1024:
                type_size = f"{info['size'] / (1024 * 1024):.1f} MB"
            elif info['size'] > 1024:
                type_size = f"{info['size'] / 1024:.1f} KB"
            else:
                type_size = f"{info['size']} B"
            message += f"  {file_type}: {info['count']} files ({type_size})\n"
        
        message += f"\nThis action cannot be undone. Continue?"
        
        if messagebox.askyesno("Cleanup Preview", message):
            self.run_cleanup()
    
    def run_cleanup(self):
        """Run the cleanup operation"""
        files = self.cleanup_manager.get_cleanup_preview()
        
        if not files:
            messagebox.showinfo("Cleanup", "No files are ready for cleanup.")
            return
        
        # Confirm cleanup
        result = messagebox.askyesno("Confirm Cleanup", 
                                   f"Are you sure you want to delete {len(files)} files?\n\nThis action cannot be undone.")
        if not result:
            return
        
        try:
            # Run cleanup
            cleanup_result = self.cleanup_manager.run_manual_cleanup()
            
            # Show results
            if cleanup_result['files_deleted'] > 0:
                space_freed = cleanup_result['space_freed']
                if space_freed > 1024 * 1024 * 1024:
                    space_str = f"{space_freed / (1024 * 1024 * 1024):.2f} GB"
                elif space_freed > 1024 * 1024:
                    space_str = f"{space_freed / (1024 * 1024):.2f} MB"
                elif space_freed > 1024:
                    space_str = f"{space_freed / 1024:.2f} KB"
                else:
                    space_str = f"{space_freed} B"
                
                messagebox.showinfo("Cleanup Complete", 
                                  f"Cleanup completed successfully!\n\n"
                                  f"Files deleted: {cleanup_result['files_deleted']}\n"
                                  f"Space freed: {space_str}")
            else:
                messagebox.showinfo("Cleanup Complete", "No files were deleted.")
            
            # Refresh the display
            self.load_cleanup_info()
            
        except Exception as e:
            messagebox.showerror("Error", f"Cleanup failed: {str(e)}")
    
    def close_cleanup_manager(self):
        """Close the cleanup management window"""
        if self.cleanup_window:
            self.cleanup_window.destroy()
            self.cleanup_window = None
