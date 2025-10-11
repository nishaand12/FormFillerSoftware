#!/usr/bin/env python3
"""
Data Management GUI for Physiotherapy Clinic Assistant
Provides secure data clearing and management capabilities with encryption
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, timedelta
from typing import Dict, List
from database_manager import DatabaseManager


class DataManagementGUI:
    def __init__(self, parent, db_manager: DatabaseManager):
        self.parent = parent
        self.db_manager = db_manager
        self.data_window = None
        
    def show_data_management(self):
        """Show the data management window"""
        if self.data_window:
            self.data_window.lift()
            return
        
        self.data_window = tk.Toplevel(self.parent)
        self.data_window.title("Data Management - Patient Data Security")
        self.data_window.geometry("1000x800")
        self.data_window.resizable(True, True)
        
        # Center the window
        self.data_window.transient(self.parent)
        self.data_window.grab_set()
        
        self.create_widgets()
        self.load_data_summary()
        
        # Handle window close
        self.data_window.protocol("WM_DELETE_WINDOW", self.close_data_management)
    
    def create_widgets(self):
        """Create the data management widgets"""
        # Main frame
        main_frame = ttk.Frame(self.data_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.data_window.columnconfigure(0, weight=1)
        self.data_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title with warning
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        title_label = ttk.Label(title_frame, text="⚠️ PATIENT DATA MANAGEMENT", 
                               font=("Arial", 16, "bold"), foreground="red")
        title_label.pack(side=tk.LEFT)
        
        warning_label = ttk.Label(title_frame, 
                                 text="Sensitive patient health data - All operations are logged and require confirmation",
                                 font=("Arial", 10), foreground="orange")
        warning_label.pack(side=tk.RIGHT)
        
        # Create notebook for different management options
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Data Overview Tab
        self.create_overview_tab()
        
        # Clear All Data Tab
        self.create_clear_all_tab()
        
        # Time-Based Management Tab
        self.create_time_based_tab()
        
        # Selective Management Tab
        self.create_selective_tab()
        
        # Backup Management Tab
        self.create_backup_tab()
    
    def create_overview_tab(self):
        """Create data overview tab"""
        overview_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(overview_frame, text="Data Overview")
        
        # Data summary
        summary_frame = ttk.LabelFrame(overview_frame, text="Current Data Summary", padding="10")
        summary_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Summary labels
        self.total_appointments_var = tk.StringVar()
        self.total_files_var = tk.StringVar()
        self.total_size_var = tk.StringVar()
        self.date_range_var = tk.StringVar()
        self.age_distribution_var = tk.StringVar()
        
        ttk.Label(summary_frame, text="Total Appointments:").grid(row=0, column=0, sticky=tk.W, pady=5)
        ttk.Label(summary_frame, textvariable=self.total_appointments_var, font=("Arial", 10, "bold")).grid(row=0, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(summary_frame, text="Total Files:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(summary_frame, textvariable=self.total_files_var, font=("Arial", 10, "bold")).grid(row=1, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(summary_frame, text="Total Size:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(summary_frame, textvariable=self.total_size_var, font=("Arial", 10, "bold")).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(summary_frame, text="Date Range:").grid(row=3, column=0, sticky=tk.W, pady=5)
        ttk.Label(summary_frame, textvariable=self.date_range_var, font=("Arial", 10, "bold")).grid(row=3, column=1, sticky=tk.W, pady=5)
        
        ttk.Label(summary_frame, text="Age Distribution:").grid(row=4, column=0, sticky=tk.W, pady=5)
        ttk.Label(summary_frame, textvariable=self.age_distribution_var, font=("Arial", 10, "bold")).grid(row=4, column=1, sticky=tk.W, pady=5)
        
        # Refresh button
        refresh_button = ttk.Button(summary_frame, text="Refresh Data", command=self.load_data_summary)
        refresh_button.grid(row=5, column=0, pady=20)
        
        # Cleanup empty folders button
        cleanup_folders_button = ttk.Button(summary_frame, text="Clean Empty Folders", command=self.cleanup_empty_folders)
        cleanup_folders_button.grid(row=5, column=1, pady=20)
    
    def create_clear_all_tab(self):
        """Create clear all data tab"""
        clear_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(clear_frame, text="Clear All Data")
        
        # Warning section
        warning_frame = ttk.LabelFrame(clear_frame, text="⚠️ DANGER ZONE", padding="10")
        warning_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        warning_text = """This will permanently delete ALL patient data including:
• All appointments and patient records
• All audio recordings, transcripts, and forms
• All processing status and file metadata

This action CANNOT be undone!"""
        
        ttk.Label(warning_frame, text=warning_text, font=("Arial", 10), foreground="red").pack()
        
        # Backup section
        backup_frame = ttk.LabelFrame(clear_frame, text="Backup Requirements", padding="10")
        backup_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        self.create_backup_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(backup_frame, text="Create encrypted backup before clearing", 
                       variable=self.create_backup_var).pack(anchor=tk.W)
        
        # Password section
        password_frame = ttk.Frame(backup_frame)
        password_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Label(password_frame, text="Backup Password:").pack(side=tk.LEFT)
        self.backup_password_var = tk.StringVar()
        self.password_entry = ttk.Entry(password_frame, textvariable=self.backup_password_var, 
                                       show="*", width=30)
        self.password_entry.pack(side=tk.LEFT, padx=(10, 0))
        
        # Clear button
        clear_button = ttk.Button(clear_frame, text="🗑️ CLEAR ALL PATIENT DATA", 
                                 command=self.clear_all_data, style="Danger.TButton")
        clear_button.grid(row=2, column=0, pady=20)
        
        # Configure danger button style
        style = ttk.Style()
        style.configure("Danger.TButton", foreground="white", background="red")
    
    def create_time_based_tab(self):
        """Create time-based management tab"""
        time_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(time_frame, text="Time-Based Management")
        
        # Archive section
        archive_frame = ttk.LabelFrame(time_frame, text="Archive Old Data", padding="10")
        archive_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(archive_frame, text="Archive data older than:").pack(anchor=tk.W)
        
        archive_days_frame = ttk.Frame(archive_frame)
        archive_days_frame.pack(fill=tk.X, pady=5)
        
        self.archive_days_var = tk.IntVar(value=14)
        ttk.Spinbox(archive_days_frame, from_=7, to=365, textvariable=self.archive_days_var, 
                   width=10).pack(side=tk.LEFT)
        ttk.Label(archive_days_frame, text="days").pack(side=tk.LEFT, padx=(5, 0))
        
        archive_button = ttk.Button(archive_frame, text="📦 Archive Old Data", 
                                   command=self.archive_old_data)
        archive_button.pack(pady=10)
        
        # Delete section
        delete_frame = ttk.LabelFrame(time_frame, text="Delete Old Data", padding="10")
        delete_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(delete_frame, text="Delete data older than:").pack(anchor=tk.W)
        
        delete_days_frame = ttk.Frame(delete_frame)
        delete_days_frame.pack(fill=tk.X, pady=5)
        
        self.delete_days_var = tk.IntVar(value=30)
        ttk.Spinbox(delete_days_frame, from_=14, to=365, textvariable=self.delete_days_var, 
                   width=10).pack(side=tk.LEFT)
        ttk.Label(delete_days_frame, text="days").pack(side=tk.LEFT, padx=(5, 0))
        
        delete_button = ttk.Button(delete_frame, text="🗑️ Delete Old Data", 
                                  command=self.delete_old_data)
        delete_button.pack(pady=10)
    
    def create_selective_tab(self):
        """Create selective management tab"""
        selective_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(selective_frame, text="Selective Management")
        
        # Date range section
        date_frame = ttk.LabelFrame(selective_frame, text="Clear by Date Range", padding="10")
        date_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(date_frame, text="From:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.start_date_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.start_date_var, width=15).grid(row=0, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        ttk.Label(date_frame, text="(YYYY-MM-DD)").grid(row=0, column=2, sticky=tk.W, pady=5, padx=(5, 0))
        
        ttk.Label(date_frame, text="To:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.end_date_var = tk.StringVar()
        ttk.Entry(date_frame, textvariable=self.end_date_var, width=15).grid(row=1, column=1, sticky=tk.W, pady=5, padx=(5, 0))
        ttk.Label(date_frame, text="(YYYY-MM-DD)").grid(row=1, column=2, sticky=tk.W, pady=5, padx=(5, 0))
        
        date_clear_button = ttk.Button(date_frame, text="🗑️ Clear Date Range", 
                                      command=self.clear_by_date_range)
        date_clear_button.grid(row=2, column=0, columnspan=3, pady=10)
        
        # Patient section
        patient_frame = ttk.LabelFrame(selective_frame, text="Clear by Patient", padding="10")
        patient_frame.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(patient_frame, text="Patient Name:").pack(anchor=tk.W)
        self.patient_name_var = tk.StringVar()
        ttk.Entry(patient_frame, textvariable=self.patient_name_var, width=30).pack(fill=tk.X, pady=5)
        
        patient_clear_button = ttk.Button(patient_frame, text="🗑️ Clear Patient Data", 
                                         command=self.clear_patient_data)
        patient_clear_button.pack(pady=10)
    
    def create_backup_tab(self):
        """Create backup management tab"""
        backup_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(backup_frame, text="Backup Management")
        
        # Create backup section
        create_backup_frame = ttk.LabelFrame(backup_frame, text="Create Encrypted Backup", padding="10")
        create_backup_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(create_backup_frame, text="Backup Password:").pack(anchor=tk.W)
        self.backup_create_password_var = tk.StringVar()
        ttk.Entry(create_backup_frame, textvariable=self.backup_create_password_var, 
                 show="*", width=30).pack(fill=tk.X, pady=5)
        
        create_backup_button = ttk.Button(create_backup_frame, text="💾 Create Backup", 
                                         command=self.create_backup)
        create_backup_button.pack(pady=10)
        
        # Backup status
        self.backup_status_var = tk.StringVar()
        ttk.Label(backup_frame, textvariable=self.backup_status_var, font=("Arial", 10)).grid(row=1, column=0, pady=10)
    
    def load_data_summary(self):
        """Load and display data summary"""
        try:
            summary = self.db_manager.get_data_summary()
            
            self.total_appointments_var.set(str(summary['total_appointments']))
            self.total_files_var.set(str(summary['total_files']))
            
            # Format size
            total_size = summary['total_size']
            if total_size > 1024 * 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024 * 1024):.2f} GB"
            elif total_size > 1024 * 1024:
                size_str = f"{total_size / (1024 * 1024):.2f} MB"
            elif total_size > 1024:
                size_str = f"{total_size / 1024:.2f} KB"
            else:
                size_str = f"{total_size} B"
            
            self.total_size_var.set(size_str)
            
            # Date range
            if summary['earliest_date'] and summary['latest_date']:
                self.date_range_var.set(f"{summary['earliest_date']} to {summary['latest_date']}")
            else:
                self.date_range_var.set("No data")
            
            # Age distribution
            age_dist = summary['age_distribution']
            age_str = f"2+ weeks: {age_dist['older_than_2_weeks']}, 1+ month: {age_dist['older_than_1_month']}, 3+ months: {age_dist['older_than_3_months']}"
            self.age_distribution_var.set(age_str)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load data summary: {str(e)}")
    
    def clear_all_data(self):
        """Clear all patient data with confirmation"""
        # Multiple confirmations required
        if not messagebox.askyesno("Confirm Clear All", 
                                  "⚠️ WARNING: This will permanently delete ALL patient data!\n\n"
                                  "This action CANNOT be undone!\n\n"
                                  "Are you sure you want to continue?"):
            return
        
        # Password confirmation
        if self.create_backup_var.get():
            password = self.backup_password_var.get()
            if not password:
                messagebox.showerror("Error", "Backup password is required")
                return
            
            # Validate password strength
            is_valid, message = self.db_manager._validate_password_strength(password)
            if not is_valid:
                messagebox.showerror("Password Error", message)
                return
        
        # Final confirmation with text input
        confirmation = simpledialog.askstring("Final Confirmation", 
                                            "Type 'DELETE ALL PATIENT DATA' to confirm:")
        if confirmation != "DELETE ALL PATIENT DATA":
            messagebox.showinfo("Cancelled", "Operation cancelled")
            return
        
        try:
            # Show progress
            progress_window = tk.Toplevel(self.data_window)
            progress_window.title("Clearing Data...")
            progress_window.geometry("300x100")
            progress_window.transient(self.data_window)
            progress_window.grab_set()
            
            progress_label = ttk.Label(progress_window, text="Clearing all patient data...")
            progress_label.pack(pady=20)
            
            # Perform the operation
            result = self.db_manager.clear_all_patient_data(
                create_backup=self.create_backup_var.get(),
                backup_password=self.backup_password_var.get() if self.create_backup_var.get() else None
            )
            
            progress_window.destroy()
            
            if result['success']:
                messagebox.showinfo("Success", 
                                  f"Data cleared successfully!\n\n"
                                  f"Appointments deleted: {result['appointments_deleted']}\n"
                                  f"Files deleted: {result['files_deleted']}\n"
                                  f"Space freed: {result['space_freed']} bytes")
                
                if result.get('backup_info'):
                    messagebox.showinfo("Backup Created", 
                                      f"Encrypted backup created: {result['backup_info']['backup_filename']}")
                
                # Refresh data summary
                self.load_data_summary()
            else:
                messagebox.showerror("Error", f"Failed to clear data: {result['error']}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def archive_old_data(self):
        """Archive old data"""
        days = self.archive_days_var.get()
        
        if not messagebox.askyesno("Confirm Archive", 
                                  f"Archive all data older than {days} days?\n\n"
                                  "This will move files to an archived folder."):
            return
        
        try:
            result = self.db_manager.archive_old_data(days)
            
            if result['success']:
                messagebox.showinfo("Success", 
                                  f"Archive completed!\n\n"
                                  f"Files archived: {result['archived_count']}\n"
                                  f"Size archived: {result['archived_size']} bytes\n"
                                  f"Cutoff date: {result['cutoff_date']}")
                self.load_data_summary()
            else:
                messagebox.showerror("Error", f"Archive failed: {result['error']}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def delete_old_data(self):
        """Delete old data"""
        days = self.delete_days_var.get()
        
        if not messagebox.askyesno("Confirm Delete", 
                                  f"⚠️ WARNING: Permanently delete all data older than {days} days?\n\n"
                                  "This action CANNOT be undone!"):
            return
        
        try:
            result = self.db_manager.delete_old_data(days)
            
            if result['success']:
                messagebox.showinfo("Success", 
                                  f"Delete completed!\n\n"
                                  f"Appointments deleted: {result['deleted_appointments']}\n"
                                  f"Files deleted: {result['deleted_files']}\n"
                                  f"Size freed: {result['deleted_size']} bytes\n"
                                  f"Cutoff date: {result['cutoff_date']}")
                self.load_data_summary()
            else:
                messagebox.showerror("Error", f"Delete failed: {result['error']}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def clear_by_date_range(self):
        """Clear data by date range"""
        start_date = self.start_date_var.get()
        end_date = self.end_date_var.get()
        
        if not start_date or not end_date:
            messagebox.showerror("Error", "Please enter both start and end dates")
            return
        
        if not messagebox.askyesno("Confirm Date Range Clear", 
                                  f"⚠️ WARNING: Permanently delete all data from {start_date} to {end_date}?\n\n"
                                  "This action CANNOT be undone!"):
            return
        
        try:
            result = self.db_manager.clear_data_by_date_range(start_date, end_date)
            
            if result['success']:
                messagebox.showinfo("Success", 
                                  f"Date range clear completed!\n\n"
                                  f"Appointments deleted: {result['deleted_appointments']}\n"
                                  f"Files deleted: {result['deleted_files']}\n"
                                  f"Size freed: {result['deleted_size']} bytes")
                self.load_data_summary()
            else:
                messagebox.showerror("Error", f"Date range clear failed: {result['error']}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def clear_patient_data(self):
        """Clear data for specific patient"""
        patient_name = self.patient_name_var.get()
        
        if not patient_name:
            messagebox.showerror("Error", "Please enter a patient name")
            return
        
        if not messagebox.askyesno("Confirm Patient Clear", 
                                  f"⚠️ WARNING: Permanently delete all data for patient '{patient_name}'?\n\n"
                                  "This action CANNOT be undone!"):
            return
        
        try:
            result = self.db_manager.clear_patient_data(patient_name)
            
            if result['success']:
                messagebox.showinfo("Success", 
                                  f"Patient data clear completed!\n\n"
                                  f"Appointments deleted: {result['deleted_appointments']}\n"
                                  f"Files deleted: {result['deleted_files']}\n"
                                  f"Size freed: {result['deleted_size']} bytes")
                self.load_data_summary()
            else:
                messagebox.showerror("Error", f"Patient data clear failed: {result['error']}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def create_backup(self):
        """Create encrypted backup"""
        password = self.backup_create_password_var.get()
        
        if not password:
            messagebox.showerror("Error", "Please enter a backup password")
            return
        
        # Validate password strength
        is_valid, message = self.db_manager._validate_password_strength(password)
        if not is_valid:
            messagebox.showerror("Password Error", message)
            return
        
        try:
            result = self.db_manager.create_encrypted_backup(password, "manual")
            
            if result['success']:
                self.backup_status_var.set(f"✅ Backup created: {result['backup_filename']}")
                messagebox.showinfo("Success", 
                                  f"Encrypted backup created successfully!\n\n"
                                  f"Backup file: {result['backup_filename']}\n"
                                  f"Location: {result['backup_path']}")
            else:
                self.backup_status_var.set(f"❌ Backup failed: {result['error']}")
                messagebox.showerror("Error", f"Backup creation failed: {result['error']}")
                
        except Exception as e:
            self.backup_status_var.set(f"❌ Backup error: {str(e)}")
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def cleanup_empty_folders(self):
        """Clean up empty folders"""
        if not messagebox.askyesno("Confirm Cleanup", 
                                  "Clean up all empty patient and date folders?\n\n"
                                  "This will remove any empty folders left behind after file deletions."):
            return
        
        try:
            result = self.db_manager.cleanup_all_empty_folders()
            
            if result['success']:
                messagebox.showinfo("Success", 
                                  f"Empty folders cleanup completed!\n\n"
                                  f"Folders removed: {result['count']}\n"
                                  f"Message: {result['message']}")
                self.load_data_summary()
            else:
                messagebox.showerror("Error", f"Cleanup failed: {result['error']}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Unexpected error: {str(e)}")
    
    def close_data_management(self):
        """Close the data management window"""
        if self.data_window:
            self.data_window.destroy()
            self.data_window = None
