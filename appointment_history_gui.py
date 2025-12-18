#!/usr/bin/env python3
"""
Appointment History GUI - Appointment-centric interface for managing appointments
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, timedelta
import os
import subprocess
import webbrowser
from typing import Optional, List, Dict, Any
import sys
import json
import re
from pathlib import Path

class AppointmentHistoryGUI:
    def __init__(self, root, db_manager, auth_manager):
        self.root = root
        self.db_manager = db_manager
        self.auth_manager = auth_manager
        self.window = None
        
    def show_appointment_history(self):
        """Show the appointment history window"""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            self.window.focus_force()
            return
            
        self.window = tk.Toplevel(self.root)
        self.window.title("Appointment History")
        self.window.geometry("1000x700")
        self.window.transient(self.root)
        self.window.grab_set()
        
        # Center the window
        self.window.update_idletasks()
        x = (self.window.winfo_screenwidth() // 2) - (1000 // 2)
        y = (self.window.winfo_screenheight() // 2) - (700 // 2)
        self.window.geometry(f"1000x700+{x}+{y}")
        
        self.create_widgets()
        self.load_appointments()
        
        # Bind close event
        self.window.protocol("WM_DELETE_WINDOW", self.close_appointment_history)
        
    def create_widgets(self):
        """Create the GUI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Appointment History", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Search and filter frame
        search_frame = ttk.LabelFrame(main_frame, text="Search & Filter", padding="10")
        search_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)
        
        # Search by patient name
        ttk.Label(search_frame, text="Patient Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.search_entry.bind('<KeyRelease>', self.on_search_change)
        
        # Date range
        ttk.Label(search_frame, text="From:").grid(row=0, column=2, sticky=tk.W, padx=(10, 5))
        self.date_from_var = tk.StringVar()
        self.date_from_entry = ttk.Entry(search_frame, textvariable=self.date_from_var, width=12)
        self.date_from_entry.grid(row=0, column=3, padx=(0, 5))
        
        ttk.Label(search_frame, text="To:").grid(row=0, column=4, sticky=tk.W, padx=(10, 5))
        self.date_to_var = tk.StringVar()
        self.date_to_entry = ttk.Entry(search_frame, textvariable=self.date_to_var, width=12)
        self.date_to_entry.grid(row=0, column=5, padx=(0, 10))
        
        # Search button
        ttk.Button(search_frame, text="Search", command=self.search_appointments).grid(row=0, column=6, padx=(0, 10))
        
        # Clear button
        ttk.Button(search_frame, text="Clear", command=self.clear_search).grid(row=0, column=7)
        
        # Quick date buttons
        quick_frame = ttk.Frame(search_frame)
        quick_frame.grid(row=1, column=0, columnspan=8, pady=(10, 0))
        
        ttk.Button(quick_frame, text="Today", command=lambda: self.set_date_range('today')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="Yesterday", command=lambda: self.set_date_range('yesterday')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="This Week", command=lambda: self.set_date_range('week')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="This Month", command=lambda: self.set_date_range('month')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="All", command=lambda: self.set_date_range('all')).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(quick_frame, text="Show Date Folders", command=self.show_date_folders).pack(side=tk.LEFT)
        
        # Appointments list frame
        list_frame = ttk.LabelFrame(main_frame, text="Appointments", padding="10")
        list_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(1, weight=1)
        
        # Treeview for appointments
        columns = ('Date', 'Time', 'Patient', 'Type', 'Status', 'Files')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=15)
        
        # Configure columns
        self.tree.heading('Date', text='Date')
        self.tree.heading('Time', text='Time')
        self.tree.heading('Patient', text='Patient Name')
        self.tree.heading('Type', text='Type')
        self.tree.heading('Status', text='Status')
        self.tree.heading('Files', text='Files')
        
        self.tree.column('Date', width=100)
        self.tree.column('Time', width=80)
        self.tree.column('Patient', width=150)
        self.tree.column('Type', width=100)
        self.tree.column('Status', width=100)
        self.tree.column('Files', width=100)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        self.tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Bind selection event
        self.tree.bind('<<TreeviewSelect>>', self.on_appointment_select)
        self.tree.bind('<Double-1>', self.on_appointment_double_click)
        
        # Action buttons frame
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=3, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(action_frame, text="View Transcript", command=self.view_transcript).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="View Form Data", command=self.view_form_data).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Open Forms", command=self.open_forms).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Open Folder", command=self.open_folder).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="View Details", command=self.view_details).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(action_frame, text="Refresh", command=self.load_appointments).pack(side=tk.LEFT, padx=(20, 5))
        ttk.Button(action_frame, text="Close", command=self.close_appointment_history).pack(side=tk.RIGHT)
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(main_frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(10, 0))
        
    def load_appointments(self):
        """Load appointments into the treeview"""
        try:
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Get recent appointments
            appointments = self.db_manager.get_recent_appointments(limit=50)
            
            for appointment in appointments:
                # Get file count for this appointment
                user_id = self.auth_manager.get_required_user_id()
                files = self.db_manager.get_appointment_files(appointment['appointment_id'], user_id)
                file_count = len(files) if files else 0
                
                # Get processing status
                status = self.get_appointment_status(appointment['appointment_id'])
                
                # Format time for display
                time_str = str(appointment['appointment_time'])
                if len(time_str) == 6:  # HHMMSS format
                    time_str = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                
                # Insert into treeview
                self.tree.insert('', 'end', values=(
                    appointment['appointment_date'],
                    time_str,
                    appointment['patient_name'],
                    appointment.get('appointment_type', 'Initial Assessment'),
                    status,
                    f"{file_count} files"
                ), tags=(appointment['appointment_id'],))
            
            self.status_var.set(f"Loaded {len(appointments)} appointments")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load appointments: {e}")
            self.status_var.set("Error loading appointments")
    
    def get_appointment_status(self, appointment_id: int) -> str:
        """Get the processing status for an appointment"""
        try:
            status = self.db_manager.get_processing_status(appointment_id)
            if not status:
                return "Queued"
            
            # Check for failed steps first
            failed_steps = [s for s in status if s['status'] == 'failed']
            if failed_steps:
                return "Failed"
            
            # Check transcription status
            transcription_steps = [s for s in status if s['step_name'] == 'transcription']
            if not transcription_steps:
                return "Queued"
            
            latest_transcription = max(transcription_steps, key=lambda x: x['created_date'])
            if latest_transcription['status'] != 'completed':
                if latest_transcription['status'] == 'processing':
                    return "Transcribing"
                else:
                    return "Queued"
            
            # Check extraction status (WSIB, OCF-18, OCF-23)
            extraction_steps = [s for s in status if s['step_name'] in ['extraction', 'ocf18_extraction', 'ocf23_extraction']]
            if extraction_steps:
                latest_extraction = max(extraction_steps, key=lambda x: x['created_date'])
                if latest_extraction['status'] == 'processing':
                    return "Extracting Data"
                elif latest_extraction['status'] != 'completed':
                    return "Queued"
            
            # Check form filling status (WSIB, OCF-18, OCF-23)
            form_filling_steps = [s for s in status if s['step_name'] in ['form_filling', 'ocf18_form_filling', 'ocf23_form_filling']]
            if form_filling_steps:
                latest_form_filling = max(form_filling_steps, key=lambda x: x['created_date'])
                if latest_form_filling['status'] == 'processing':
                    return "Filling Forms"
                elif latest_form_filling['status'] == 'completed':
                    return "Complete"
                elif latest_form_filling['status'] == 'skipped':
                    return "Complete"
                else:
                    return "Queued"
            
            # If we have completed extraction but no form filling steps, check if forms were skipped
            if extraction_steps and not form_filling_steps:
                # Check if any extraction was completed but no forms were selected
                completed_extractions = [s for s in extraction_steps if s['status'] == 'completed']
                if completed_extractions:
                    return "Complete"  # Extraction completed but no forms to fill
            
            # Default fallback
            return "Queued"
            
        except Exception as e:
            print(f"Error getting appointment status: {e}")
            return "Unknown"
    
    def search_appointments(self):
        """Search appointments based on current filters"""
        try:
            query = self.search_var.get().strip()
            date_from = self.date_from_var.get().strip()
            date_to = self.date_to_var.get().strip()
            
            # Clear existing items
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            # Search appointments
            appointments = self.db_manager.search_appointments(
                query=query if query else None,
                date_from=date_from if date_from else None,
                date_to=date_to if date_to else None
            )
            
            for appointment in appointments:
                # Get file count for this appointment
                user_id = self.auth_manager.get_required_user_id()
                files = self.db_manager.get_appointment_files(appointment['appointment_id'], user_id)
                file_count = len(files) if files else 0
                
                # Get processing status
                status = self.get_appointment_status(appointment['appointment_id'])
                
                # Format time for display
                time_str = str(appointment['appointment_time'])
                if len(time_str) == 6:  # HHMMSS format
                    time_str = f"{time_str[:2]}:{time_str[2:4]}:{time_str[4:6]}"
                
                # Insert into treeview
                self.tree.insert('', 'end', values=(
                    appointment['appointment_date'],
                    time_str,
                    appointment['patient_name'],
                    appointment.get('appointment_type', 'Initial Assessment'),
                    status,
                    f"{file_count} files"
                ), tags=(appointment['appointment_id'],))
            
            self.status_var.set(f"Found {len(appointments)} appointments")
            
        except Exception as e:
            messagebox.showerror("Error", f"Search failed: {e}")
            self.status_var.set("Search failed")
    
    def clear_search(self):
        """Clear search filters"""
        self.search_var.set("")
        self.date_from_var.set("")
        self.date_to_var.set("")
        self.load_appointments()
    
    def set_date_range(self, range_type: str):
        """Set date range for quick filtering"""
        today = datetime.now()
        
        if range_type == 'today':
            date_str = today.strftime('%Y-%m-%d')
            self.date_from_var.set(date_str)
            self.date_to_var.set(date_str)
        elif range_type == 'yesterday':
            yesterday = today - timedelta(days=1)
            date_str = yesterday.strftime('%Y-%m-%d')
            self.date_from_var.set(date_str)
            self.date_to_var.set(date_str)
        elif range_type == 'week':
            week_start = today - timedelta(days=today.weekday())
            self.date_from_var.set(week_start.strftime('%Y-%m-%d'))
            self.date_to_var.set(today.strftime('%Y-%m-%d'))
        elif range_type == 'month':
            month_start = today.replace(day=1)
            self.date_from_var.set(month_start.strftime('%Y-%m-%d'))
            self.date_to_var.set(today.strftime('%Y-%m-%d'))
        elif range_type == 'all':
            self.date_from_var.set("")
            self.date_to_var.set("")
        
        self.search_appointments()
    
    def on_search_change(self, event=None):
        """Handle search text changes"""
        # Auto-search after typing (with delay)
        self.window.after_cancel(getattr(self, '_search_after_id', None))
        self._search_after_id = self.window.after(500, self.search_appointments)
    
    def on_appointment_select(self, event=None):
        """Handle appointment selection"""
        selection = self.tree.selection()
        if selection:
            tags = self.tree.item(selection[0], 'tags')
            if tags and len(tags) > 0:
                appointment_id = tags[0]
                self.selected_appointment_id = appointment_id
            else:
                self.selected_appointment_id = None
    
    def on_appointment_double_click(self, event=None):
        """Handle appointment double-click"""
        self.view_details()
    
    def get_selected_appointment(self) -> Optional[Dict]:
        """Get the currently selected appointment"""
        selection = self.tree.selection()
        if not selection:
            return None
        
        tags = self.tree.item(selection[0], 'tags')
        if not tags or len(tags) == 0:
            return None
            
        appointment_id = tags[0]
        user_id = self.auth_manager.get_required_user_id()
        return self.db_manager.get_appointment(appointment_id, user_id)
    
    def view_transcript(self):
        """View the transcript for selected appointment"""
        appointment = self.get_selected_appointment()
        if not appointment:
            messagebox.showwarning("Warning", "Please select an appointment first")
            return
        
        # Find transcript file
        user_id = self.auth_manager.get_required_user_id()
        files = self.db_manager.get_appointment_files(appointment['appointment_id'], user_id)
        transcript_file = None
        for file in files:
            if file['file_type'] == 'transcript':
                transcript_file = file['file_path']
                break
        
        if not transcript_file or not os.path.exists(transcript_file):
            messagebox.showinfo("Info", "No transcript found for this appointment")
            return
        
        # Open transcript file
        try:
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', transcript_file])
            elif sys.platform == 'win32':  # Windows
                os.startfile(transcript_file)
            else:  # Linux
                subprocess.run(['xdg-open', transcript_file])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open transcript: {e}")
    
    def open_forms(self):
        """Open forms for selected appointment"""
        appointment = self.get_selected_appointment()
        if not appointment:
            messagebox.showwarning("Warning", "Please select an appointment first")
            return
        
        # Find form files
        user_id = self.auth_manager.get_required_user_id()
        files = self.db_manager.get_appointment_files(appointment['appointment_id'], user_id)
        form_files = [f for f in files if f['file_type'] in ['wsib_form', 'ocf18_form', 'ocf23_form']]
        
        if not form_files:
            messagebox.showinfo("Info", "No forms found for this appointment")
            return
        
        # Open form files
        for form_file in form_files:
            try:
                if os.path.exists(form_file['file_path']):
                    if sys.platform == 'darwin':  # macOS
                        subprocess.run(['open', form_file['file_path']])
                    elif sys.platform == 'win32':  # Windows
                        os.startfile(form_file['file_path'])
                    else:  # Linux
                        subprocess.run(['xdg-open', form_file['file_path']])
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open form: {e}")
    
    def open_folder(self):
        """Open the appointment folder"""
        appointment = self.get_selected_appointment()
        if not appointment:
            messagebox.showwarning("Warning", "Please select an appointment first")
            return
        
        folder_path = appointment['folder_path']
        if not os.path.exists(folder_path):
            messagebox.showinfo("Info", f"Folder not found: {folder_path}")
            return
        
        try:
            if sys.platform == 'darwin':  # macOS
                subprocess.run(['open', folder_path])
            elif sys.platform == 'win32':  # Windows
                os.startfile(folder_path)
            else:  # Linux
                subprocess.run(['xdg-open', folder_path])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {e}")
    
    def view_details(self):
        """View appointment details"""
        appointment = self.get_selected_appointment()
        if not appointment:
            messagebox.showwarning("Warning", "Please select an appointment first")
            return
        
        # Get files for this appointment
        user_id = self.auth_manager.get_required_user_id()
        files = self.db_manager.get_appointment_files(appointment['appointment_id'], user_id)
        status = self.db_manager.get_processing_status(appointment['appointment_id'])
        
        # Create details message
        details = f"""
Appointment Details:

Patient: {appointment['patient_name']}
Date: {appointment['appointment_date']}
Time: {appointment['appointment_time']}
Type: {appointment.get('appointment_type', 'Initial Assessment')}
Notes: {appointment.get('notes', 'None')}
Folder: {appointment['folder_path']}

Files ({len(files)}):
"""
        
        for file in files:
            details += f"• {file['file_type']}: {file['file_path']}\n"
        
        if status:
            details += "\nProcessing Status:\n"
            for step in status:
                details += f"• {step['step_name']}: {step['status']}\n"
        
        messagebox.showinfo("Appointment Details", details)
    
    def show_date_folders(self):
        """Show available date folders"""
        try:
            date_folders = self.db_manager.get_date_folders()
            
            if not date_folders:
                messagebox.showinfo("Date Folders", "No date folders found in the data directory.")
                return
            
            # Create a simple dialog to show date folders
            folder_window = tk.Toplevel(self.window)
            folder_window.title("Available Date Folders")
            folder_window.geometry("400x300")
            folder_window.transient(self.window)
            folder_window.grab_set()
            
            # Center the window
            folder_window.update_idletasks()
            x = (folder_window.winfo_screenwidth() // 2) - (400 // 2)
            y = (folder_window.winfo_screenheight() // 2) - (300 // 2)
            folder_window.geometry(f"400x300+{x}+{y}")
            
            # Create widgets
            main_frame = ttk.Frame(folder_window, padding="20")
            main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            
            ttk.Label(main_frame, text="Available Date Folders:", font=("Arial", 12, "bold")).grid(row=0, column=0, pady=(0, 10))
            
            # Create listbox for date folders
            listbox_frame = ttk.Frame(main_frame)
            listbox_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
            
            listbox = tk.Listbox(listbox_frame, height=10)
            scrollbar = ttk.Scrollbar(listbox_frame, orient=tk.VERTICAL, command=listbox.yview)
            listbox.configure(yscrollcommand=scrollbar.set)
            
            listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
            scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
            
            # Populate listbox
            for date_folder in date_folders:
                # Get appointment count for this date
                appointments = self.db_manager.get_appointments_by_date(date_folder)
                count = len(appointments)
                listbox.insert(tk.END, f"{date_folder} ({count} appointments)")
            
            # Button frame
            button_frame = ttk.Frame(main_frame)
            button_frame.grid(row=2, column=0, pady=(10, 0))
            
            ttk.Button(button_frame, text="View Appointments", 
                      command=lambda: self.view_date_appointments(listbox, folder_window)).pack(side=tk.LEFT, padx=(0, 10))
            ttk.Button(button_frame, text="Close", 
                      command=folder_window.destroy).pack(side=tk.LEFT)
            
            # Configure grid weights
            folder_window.columnconfigure(0, weight=1)
            folder_window.rowconfigure(0, weight=1)
            main_frame.columnconfigure(0, weight=1)
            main_frame.rowconfigure(1, weight=1)
            listbox_frame.columnconfigure(0, weight=1)
            listbox_frame.rowconfigure(0, weight=1)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show date folders: {e}")
    
    def view_date_appointments(self, listbox, folder_window):
        """View appointments for selected date"""
        try:
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a date folder first")
                return
            
            # Get selected date folder
            selected_text = listbox.get(selection[0])
            date_folder = selected_text.split(" (")[0]  # Extract date from "YYYY-MM-DD (X appointments)"
            
            # Set the date range to show appointments for this date
            self.date_from_var.set(date_folder)
            self.date_to_var.set(date_folder)
            
            # Search for appointments
            self.search_appointments()
            
            # Close the folder window
            folder_window.destroy()
            
            # Show message
            messagebox.showinfo("Success", f"Showing appointments for {date_folder}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to view appointments: {e}")
    
    def view_form_data(self):
        """View extracted form data for selected appointment"""
        appointment = self.get_selected_appointment()
        if not appointment:
            messagebox.showwarning("Warning", "Please select an appointment first")
            return
        
        self.view_form_data_for_appointment(appointment['appointment_id'])
    
    def view_form_data_for_appointment(self, appointment_id: str):
        """View extracted form data for a specific appointment ID"""
        # Get appointment from database
        user_id = self.auth_manager.get_required_user_id()
        appointment = self.db_manager.get_appointment(appointment_id, user_id)
        
        if not appointment:
            messagebox.showerror("Error", "Appointment not found")
            return
        
        # Get files for this appointment
        files = self.db_manager.get_appointment_files(appointment_id, user_id)
        
        # Determine form type
        form_type = self._determine_form_type(files, appointment.get('folder_path', ''))
        if not form_type:
            messagebox.showerror("Error", "Unable to determine form type for this appointment")
            return
        
        # Find extraction file
        extraction_file = None
        for file in files:
            if file['file_type'] in ['extraction', 'ocf18_extraction', 'ocf23_extraction']:
                extraction_file = file['file_path']
                break
        
        # Fallback: search folder for extraction files
        if not extraction_file and appointment.get('folder_path'):
            folder_path = appointment['folder_path']
            if os.path.exists(folder_path):
                for filename in os.listdir(folder_path):
                    if 'extraction' in filename.lower() and filename.endswith('.json'):
                        extraction_file = os.path.join(folder_path, filename)
                        break
        
        if not extraction_file or not os.path.exists(extraction_file):
            messagebox.showinfo("Info", "No form data found for this appointment")
            return
        
        # Load extraction data
        try:
            extraction_data = self._load_extraction_data(extraction_file)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to parse extraction file: {e}")
            return
        
        # Filter out metadata fields
        metadata_fields = {'appointment_id', 'extraction_timestamp', 'model_used', 'transcript_path'}
        form_data = {k: v for k, v in extraction_data.items() if k not in metadata_fields}
        
        if not form_data:
            messagebox.showinfo("Info", "No form data found in extraction file")
            return
        
        # Create form data window
        self._create_form_data_window(appointment, form_data, form_type)
    
    def _determine_form_type(self, files_list: List[Dict], appointment_folder_path: str) -> Optional[str]:
        """Determine form type from files list or folder search"""
        # Check database file_type first
        for file in files_list:
            file_type = file.get('file_type', '')
            if file_type == 'extraction':
                return 'wsib'
            elif file_type == 'ocf18_extraction':
                return 'ocf18'
            elif file_type == 'ocf23_extraction':
                return 'ocf23'
        
        # Fallback: search folder for extraction files
        if appointment_folder_path and os.path.exists(appointment_folder_path):
            for filename in os.listdir(appointment_folder_path):
                if 'extraction' in filename.lower():
                    filename_lower = filename.lower()
                    if 'ocf18' in filename_lower or 'ocf-18' in filename_lower:
                        return 'ocf18'
                    elif 'ocf23' in filename_lower or 'ocf-23' in filename_lower:
                        return 'ocf23'
                    elif 'wsib' in filename_lower:
                        return 'wsib'
        
        return None
    
    def _load_extraction_data(self, file_path: str) -> Dict[str, Any]:
        """Load and parse JSON extraction file"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Extraction file not found: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _get_readable_field_label(self, field_key: str, form_type: str) -> str:
        """Get readable field label using config -> prompt -> snake_case conversion"""
        # Try config files first
        try:
            from app_paths import get_resource_path
            
            if form_type == 'ocf18':
                field_map_path = get_resource_path("config/field_map_ocf18.json")
            elif form_type == 'ocf23':
                field_map_path = get_resource_path("config/field_map_ocf23_simplified.json")
            elif form_type == 'wsib':
                # WSIB might not have field descriptions in field_map, try anyway
                field_map_path = get_resource_path("config/field_map_wsib.json")
            else:
                field_map_path = None
            
            if field_map_path and os.path.exists(field_map_path):
                with open(field_map_path, 'r', encoding='utf-8') as f:
                    field_map = json.load(f)
                    if field_key in field_map:
                        return field_map[field_key]
        except Exception:
            pass
        
        # Try parsing from extractor prompts
        prompt_descriptions = self._parse_prompt_descriptions(form_type)
        if field_key in prompt_descriptions:
            return prompt_descriptions[field_key]
        
        # Final fallback: convert snake_case to readable text
        return self._snake_case_to_readable(field_key)
    
    def _snake_case_to_readable(self, field_key: str) -> str:
        """Convert snake_case field name to readable text"""
        # Handle special prefixes
        if field_key.startswith('part'):
            # Extract part number and rest
            parts = field_key.split('_', 1)
            if len(parts) == 2:
                part_num = parts[0].replace('part', 'Part ').upper()
                rest = parts[1].replace('_', ' ').title()
                return f"{part_num}: {rest}"
        
        # Replace underscores with spaces and title case
        readable = field_key.replace('_', ' ').title()
        
        # Fix common patterns
        readable = readable.replace('Ocf', 'OCF')
        readable = readable.replace('Wsib', 'WSIB')
        
        return readable
    
    def _parse_prompt_descriptions(self, form_type: str) -> Dict[str, str]:
        """Parse field descriptions from extractor prompt methods"""
        descriptions = {}
        
        try:
            if form_type == 'ocf18':
                from ocf18_data_extractor import OCF18DataExtractor
                extractor = OCF18DataExtractor()
                prompt = extractor._create_ocf18_prompt("")
            elif form_type == 'ocf23':
                from ocf23_data_extractor import OCF23DataExtractor
                extractor = OCF23DataExtractor()
                prompt = extractor._create_ocf23_prompt("")
            elif form_type == 'wsib':
                from wsib_data_extractor import WSIBDataExtractor
                extractor = WSIBDataExtractor()
                prompt = extractor._create_wsib_prompt("")
            else:
                return descriptions
            
            # Parse JSON-like structure from prompt
            # Look for patterns like: "field_name": "Description text"
            pattern = r'"([^"]+)":\s*"([^"]+)"'
            matches = re.findall(pattern, prompt)
            
            for field_key, description in matches:
                # Clean up description (remove parenthetical info)
                description = re.sub(r'\s*\([^)]*\)', '', description)
                description = description.strip()
                if description:
                    descriptions[field_key] = description
        
        except Exception as e:
            print(f"Warning: Could not parse prompt descriptions: {e}")
        
        return descriptions
    
    def _format_field_value(self, value: Any, field_key: str, form_type: str) -> str:
        """Format field value using checkbox mappings and other formatting"""
        if value is None:
            return ""
        
        # Load checkbox mappings
        checkbox_mappings = self._load_checkbox_mappings(form_type)
        
        # Check if this field has checkbox/option mappings
        if form_type == 'ocf18':
            # Check three_option_fields
            if 'three_option_fields' in checkbox_mappings:
                for field_name, field_config in checkbox_mappings['three_option_fields'].items():
                    if field_name == field_key and isinstance(value, str):
                        option_map = {'no': 'No', 'yes': 'Yes', 'unknown': 'Unknown'}
                        return option_map.get(value.lower(), value)
            
            # Check four_option_fields
            if 'four_option_fields' in checkbox_mappings:
                for field_name, field_config in checkbox_mappings['four_option_fields'].items():
                    if field_name == field_key and isinstance(value, str):
                        option_map = {
                            'not_employed': 'Not Employed',
                            'no': 'No',
                            'yes': 'Yes',
                            'unknown': 'Unknown'
                        }
                        return option_map.get(value.lower(), value)
            
            # Check yes_no_fields
            if 'yes_no_fields' in checkbox_mappings:
                if field_key in checkbox_mappings['yes_no_fields']:
                    if isinstance(value, bool):
                        return "Yes" if value else "No"
                    elif isinstance(value, str):
                        return "Yes" if value.lower() in ['true', 'yes', '1'] else "No"
        
        elif form_type == 'ocf23':
            # Check multiple_choice_fields
            if 'multiple_choice_fields' in checkbox_mappings:
                for field_name, field_config in checkbox_mappings['multiple_choice_fields'].items():
                    if field_name == field_key and isinstance(value, str):
                        # Map common values
                        value_lower = value.lower()
                        if value_lower == 'yes':
                            return 'Yes'
                        elif value_lower == 'no':
                            return 'No'
                        elif value_lower == 'unknown':
                            return 'Unknown'
                        return value
            
            # Check yes_no_fields
            if 'yes_no_fields' in checkbox_mappings:
                if field_key in checkbox_mappings['yes_no_fields']:
                    if isinstance(value, bool):
                        return "Yes" if value else "No"
                    elif isinstance(value, str):
                        return "Yes" if value.lower() in ['true', 'yes', '1'] else "No"
        
        elif form_type == 'wsib':
            # Check multiple_choice_fields
            if 'multiple_choice_fields' in checkbox_mappings:
                for field_name, field_config in checkbox_mappings['multiple_choice_fields'].items():
                    if field_name == field_key and isinstance(value, str):
                        # Map common values
                        value_lower = value.lower()
                        if value_lower == 'yes':
                            return 'Yes'
                        elif value_lower == 'no':
                            return 'No'
                        return value
            
            # Check yes_no_fields
            if 'yes_no_fields' in checkbox_mappings:
                if field_key in checkbox_mappings['yes_no_fields']:
                    if isinstance(value, bool):
                        return "Yes" if value else "No"
                    elif isinstance(value, str):
                        return "Yes" if value.lower() in ['true', 'yes', '1'] else "No"
        
        # Handle boolean values
        if isinstance(value, bool):
            return "Yes" if value else "No"
        
        # Return string representation
        return str(value)
    
    def _load_checkbox_mappings(self, form_type: str) -> Dict[str, Any]:
        """Load checkbox/option mappings from config files"""
        try:
            from app_paths import get_resource_path
            
            if form_type == 'ocf18':
                config_path = get_resource_path("config/ocf18_checkbox_groups.json")
            elif form_type == 'ocf23':
                config_path = get_resource_path("config/ocf23_checkbox_groups_simplified.json")
            elif form_type == 'wsib':
                config_path = get_resource_path("config/wsib_checkbox_groups.json")
            else:
                return {}
            
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Warning: Could not load checkbox mappings: {e}")
        
        return {}
    
    def _group_fields_by_section(self, fields_dict: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        """Group fields by section based on field name prefixes"""
        sections = {}
        
        for field_key, value in fields_dict.items():
            section_name = "Other Fields"
            
            # Determine section based on prefix
            if field_key.startswith('part6_'):
                section_name = "Part 6"
            elif field_key.startswith('part7_'):
                section_name = "Part 7"
            elif field_key.startswith('part8_'):
                section_name = "Part 8"
            elif field_key.startswith('part9_'):
                section_name = "Part 9"
            elif field_key.startswith('diagnosis_description_'):
                section_name = "Part 6 - Injury Descriptions"
            elif field_key.startswith('injury_sequelae_'):
                section_name = "Part 5 - Injury Descriptions"
            elif field_key.startswith('accident_'):
                section_name = "Accident Details"
            elif field_key.startswith('provider_'):
                section_name = "Provider Information"
            elif field_key.startswith('patient_'):
                section_name = "Patient Information"
            elif field_key.startswith('insurer_'):
                section_name = "Insurer Information"
            elif field_key.startswith('policy_holder_'):
                section_name = "Policy Holder Information"
            elif field_key.startswith('other_insurance_'):
                section_name = "Other Insurance Information"
            elif field_key.startswith('form_'):
                section_name = "Form Information"
            elif field_key.startswith('date_of_') or field_key == 'accident_date':
                section_name = "Dates"
            elif field_key.startswith('return_to_work') or field_key.startswith('recommendation_'):
                section_name = "Return to Work"
            elif field_key.startswith('walking_') or field_key.startswith('standing_') or \
                 field_key.startswith('sitting_') or field_key.startswith('lifting_') or \
                 field_key.startswith('stair_') or field_key.startswith('ladder_'):
                section_name = "Functional Abilities"
            elif field_key.startswith('restricted_') or field_key.startswith('ability_to_'):
                section_name = "Work Restrictions"
            elif field_key.startswith('minor_injury_') or field_key.startswith('supplementary_') or \
                 field_key.startswith('other_preapproved_'):
                section_name = "Treatment Plan"
            
            if section_name not in sections:
                sections[section_name] = {}
            sections[section_name][field_key] = value
        
        return sections
    
    def _create_form_data_window(self, appointment: Dict, form_data: Dict[str, Any], form_type: str):
        """Create and display the form data window"""
        # Create window
        data_window = tk.Toplevel(self.window)
        patient_name = appointment.get('patient_name', 'Unknown')
        data_window.title(f"Form Data - {patient_name}")
        data_window.geometry("900x700")
        data_window.transient(self.window)
        data_window.grab_set()
        
        # Center the window
        data_window.update_idletasks()
        x = (data_window.winfo_screenwidth() // 2) - (900 // 2)
        y = (data_window.winfo_screenheight() // 2) - (700 // 2)
        data_window.geometry(f"900x700+{x}+{y}")
        
        # Main frame
        main_frame = ttk.Frame(data_window, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Hide empty fields toggle
        hide_empty_var = tk.BooleanVar(value=False)
        toggle_frame = ttk.Frame(main_frame)
        toggle_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Create scrollable frame container
        scroll_container = ttk.Frame(main_frame)
        scroll_container.pack(fill=tk.BOTH, expand=True)
        
        # Create scrollable frame
        canvas = tk.Canvas(scroll_container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(scroll_container, orient=tk.VERTICAL, command=canvas.yview)
        canvas_frame = ttk.Frame(canvas)
        
        # Now create the checkbox with reference to canvas_frame
        ttk.Checkbutton(toggle_frame, text="Hide Empty Fields", variable=hide_empty_var,
                       command=lambda: self._refresh_form_data_display(canvas_frame, form_data, form_type, hide_empty_var.get(), data_window)).pack(side=tk.LEFT)
        
        canvas_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=canvas_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Group fields by section
        grouped_fields = self._group_fields_by_section(form_data)
        
        # Display fields
        self._display_grouped_fields(canvas_frame, grouped_fields, form_type, hide_empty_var.get(), data_window)
        
        # Close button
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        ttk.Button(button_frame, text="Close", command=data_window.destroy).pack(side=tk.RIGHT)
    
    def _display_grouped_fields(self, parent_frame: ttk.Frame, grouped_fields: Dict[str, Dict[str, Any]], 
                                form_type: str, hide_empty: bool, window: tk.Toplevel):
        """Display grouped fields in sections"""
        row = 0
        
        # Sort sections for consistent display
        section_order = [
            "Form Information", "Patient Information", "Provider Information", 
            "Insurer Information", "Policy Holder Information", "Other Insurance Information",
            "Part 5 - Injury Descriptions", "Part 6 - Injury Descriptions", "Part 6", "Part 7", 
            "Part 8", "Part 9", "Accident Details", "Dates", "Functional Abilities", 
            "Work Restrictions", "Return to Work", "Treatment Plan", "Other Fields"
        ]
        
        sections_to_display = [s for s in section_order if s in grouped_fields]
        sections_to_display.extend([s for s in grouped_fields.keys() if s not in sections_to_display])
        
        for section_name in sections_to_display:
            section_fields = grouped_fields[section_name]
            
            # Filter empty fields if hide_empty is True
            if hide_empty:
                section_fields = {k: v for k, v in section_fields.items() 
                                if v is not None and str(v).strip() != ''}
            
            if not section_fields:
                continue
            
            # Create section label frame
            section_frame = ttk.LabelFrame(parent_frame, text=section_name, padding="10")
            section_frame.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
            section_frame.columnconfigure(1, weight=1)
            
            field_row = 0
            for field_key, value in sorted(section_fields.items()):
                # Get readable label
                label_text = self._get_readable_field_label(field_key, form_type)
                
                # Format value
                formatted_value = self._format_field_value(value, field_key, form_type)
                
                # Field label
                label = ttk.Label(section_frame, text=label_text, anchor=tk.W)
                label.grid(row=field_row, column=0, sticky=tk.W, padx=(0, 10), pady=2)
                
                # Value frame (entry + copy button)
                value_frame = ttk.Frame(section_frame)
                value_frame.grid(row=field_row, column=1, sticky=(tk.W, tk.E), pady=2)
                value_frame.columnconfigure(0, weight=1)
                
                # Entry widget for value
                entry = ttk.Entry(value_frame, state='readonly', width=40)
                entry.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 5))
                
                # Set value (need to temporarily enable to set)
                entry.config(state='normal')
                entry.delete(0, tk.END)
                entry.insert(0, formatted_value)
                entry.config(state='readonly')
                
                # Copy button
                copy_btn = ttk.Button(value_frame, text="Copy", width=8,
                                     command=lambda v=formatted_value, w=window: self._copy_to_clipboard(w, v))
                copy_btn.grid(row=0, column=1)
                
                field_row += 1
            
            row += 1
    
    def _refresh_form_data_display(self, canvas_frame: ttk.Frame, form_data: Dict[str, Any], 
                                  form_type: str, hide_empty: bool, window: tk.Toplevel):
        """Refresh the form data display when toggle changes"""
        # Clear existing widgets
        for widget in canvas_frame.winfo_children():
            widget.destroy()
        
        # Regroup and redisplay
        grouped_fields = self._group_fields_by_section(form_data)
        self._display_grouped_fields(canvas_frame, grouped_fields, form_type, hide_empty, window)
    
    def _copy_to_clipboard(self, window: tk.Toplevel, value: str):
        """Copy value to clipboard"""
        window.clipboard_clear()
        window.clipboard_append(value)
    
    def close_appointment_history(self):
        """Close the appointment history window"""
        if self.window:
            self.window.destroy()
            self.window = None
