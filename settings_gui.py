#!/usr/bin/env python3
"""
Settings GUI for Physiotherapy Clinic Assistant
Provides a user-friendly interface for managing application settings
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, Any
from database_manager import DatabaseManager


class SettingsGUI:
    def __init__(self, parent, db_manager: DatabaseManager):
        self.parent = parent
        self.db_manager = db_manager
        self.settings_window = None
        self.settings_vars = {}
        
    def show_settings(self):
        """Show the settings window"""
        if self.settings_window:
            self.settings_window.lift()
            return
        
        self.settings_window = tk.Toplevel(self.parent)
        self.settings_window.title("Application Settings")
        self.settings_window.geometry("600x700")
        self.settings_window.resizable(True, True)
        
        # Center the window
        self.settings_window.transient(self.parent)
        self.settings_window.grab_set()
        
        self.create_widgets()
        self.load_settings()
        
        # Handle window close
        self.settings_window.protocol("WM_DELETE_WINDOW", self.close_settings)
    
    def create_widgets(self):
        """Create the settings widgets"""
        # Main frame
        main_frame = ttk.Frame(self.settings_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.settings_window.columnconfigure(0, weight=1)
        self.settings_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Application Settings", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Create notebook for different setting categories
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
        
        # General settings tab
        general_frame = ttk.Frame(notebook, padding="10")
        notebook.add(general_frame, text="General")
        self.create_general_settings(general_frame)
        
        # File management tab
        files_frame = ttk.Frame(notebook, padding="10")
        notebook.add(files_frame, text="File Management")
        self.create_file_settings(files_frame)
        
        # Recording settings tab
        recording_frame = ttk.Frame(notebook, padding="10")
        notebook.add(recording_frame, text="Recording")
        self.create_recording_settings(recording_frame)
        
        # Patient settings tab
        patient_frame = ttk.Frame(notebook, padding="10")
        notebook.add(patient_frame, text="Patients")
        self.create_patient_settings(patient_frame)
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.grid(row=2, column=0, columnspan=3, pady=(20, 0))
        
        # Save button
        save_button = ttk.Button(buttons_frame, text="Save Settings", 
                                command=self.save_settings)
        save_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Reset button
        reset_button = ttk.Button(buttons_frame, text="Reset to Defaults", 
                                 command=self.reset_settings)
        reset_button.pack(side=tk.LEFT, padx=(0, 10))
        
        # Close button
        close_button = ttk.Button(buttons_frame, text="Close", 
                                 command=self.close_settings)
        close_button.pack(side=tk.LEFT)
        
        # Configure main frame grid weights
        main_frame.rowconfigure(1, weight=1)
    
    def create_general_settings(self, parent):
        """Create general settings widgets"""
        row = 0
        
        # Auto cleanup enabled
        ttk.Label(parent, text="Enable Automatic Cleanup:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.settings_vars['auto_cleanup_enabled'] = tk.BooleanVar()
        auto_cleanup_check = ttk.Checkbutton(parent, variable=self.settings_vars['auto_cleanup_enabled'])
        auto_cleanup_check.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(parent, text="Automatically delete old files based on retention policies").grid(row=row, column=2, sticky=tk.W, pady=5)
        row += 1
        
        # Cleanup frequency
        ttk.Label(parent, text="Cleanup Frequency (hours):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.settings_vars['cleanup_frequency_hours'] = tk.StringVar()
        cleanup_freq_entry = ttk.Entry(parent, textvariable=self.settings_vars['cleanup_frequency_hours'], width=10)
        cleanup_freq_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(parent, text="How often to run automatic cleanup").grid(row=row, column=2, sticky=tk.W, pady=5)
        row += 1
        
        # Max storage
        ttk.Label(parent, text="Maximum Storage (GB):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.settings_vars['max_storage_gb'] = tk.StringVar()
        max_storage_entry = ttk.Entry(parent, textvariable=self.settings_vars['max_storage_gb'], width=10)
        max_storage_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(parent, text="Maximum storage usage before cleanup").grid(row=row, column=2, sticky=tk.W, pady=5)
        row += 1
        
        # Backup enabled
        ttk.Label(parent, text="Enable Local Backup:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.settings_vars['backup_enabled'] = tk.BooleanVar()
        backup_check = ttk.Checkbutton(parent, variable=self.settings_vars['backup_enabled'])
        backup_check.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(parent, text="Create local backups of patient data").grid(row=row, column=2, sticky=tk.W, pady=5)
        row += 1
    
    def create_file_settings(self, parent):
        """Create file management settings widgets"""
        row = 0
        
        # Audio retention
        ttk.Label(parent, text="Audio Retention (days):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.settings_vars['audio_retention_days'] = tk.StringVar()
        audio_retention_entry = ttk.Entry(parent, textvariable=self.settings_vars['audio_retention_days'], width=10)
        audio_retention_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(parent, text="How long to keep audio recordings").grid(row=row, column=2, sticky=tk.W, pady=5)
        row += 1
        
        # Text retention
        ttk.Label(parent, text="Text Retention (days):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.settings_vars['text_retention_days'] = tk.StringVar()
        text_retention_entry = ttk.Entry(parent, textvariable=self.settings_vars['text_retention_days'], width=10)
        text_retention_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(parent, text="How long to keep text files (transcripts, extractions)").grid(row=row, column=2, sticky=tk.W, pady=5)
        row += 1
        
    
    def create_recording_settings(self, parent):
        """Create recording settings widgets"""
        row = 0
        
        # Max recording duration
        ttk.Label(parent, text="Max Recording Duration (seconds):").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.settings_vars['max_recording_duration'] = tk.StringVar()
        max_duration_entry = ttk.Entry(parent, textvariable=self.settings_vars['max_recording_duration'], width=10)
        max_duration_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(parent, text="Maximum recording time per session").grid(row=row, column=2, sticky=tk.W, pady=5)
        row += 1
        
        # Audio quality
        ttk.Label(parent, text="Audio Quality:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.settings_vars['audio_quality'] = tk.StringVar()
        quality_combo = ttk.Combobox(parent, textvariable=self.settings_vars['audio_quality'], 
                                   values=['low', 'medium', 'high'], width=10, state='readonly')
        quality_combo.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(parent, text="Audio recording quality setting").grid(row=row, column=2, sticky=tk.W, pady=5)
        row += 1
    
    def create_patient_settings(self, parent):
        """Create patient management settings widgets"""
        row = 0
        
        # Patient code prefix
        ttk.Label(parent, text="Patient Code Prefix:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.settings_vars['patient_code_prefix'] = tk.StringVar()
        prefix_entry = ttk.Entry(parent, textvariable=self.settings_vars['patient_code_prefix'], width=10)
        prefix_entry.grid(row=row, column=1, sticky=tk.W, pady=5)
        ttk.Label(parent, text="Prefix for automatically generated patient codes").grid(row=row, column=2, sticky=tk.W, pady=5)
        row += 1
    
    def load_settings(self):
        """Load current settings from database"""
        # Load all settings
        settings_to_load = [
            'auto_cleanup_enabled', 'cleanup_frequency_hours', 'max_storage_gb', 'backup_enabled',
            'audio_retention_days', 'text_retention_days', 'max_recording_duration', 'audio_quality',
            'patient_code_prefix'
        ]
        
        for setting in settings_to_load:
            value = self.db_manager.get_setting(setting)
            if setting in self.settings_vars:
                if isinstance(value, bool):
                    self.settings_vars[setting].set(value)
                else:
                    self.settings_vars[setting].set(str(value) if value is not None else '')
        
    
    def save_settings(self):
        """Save settings to database"""
        try:
            # Save individual settings
            for key, var in self.settings_vars.items():
                value = var.get()
                
                # Convert to appropriate type
                if key in ['auto_cleanup_enabled', 'backup_enabled']:
                    self.db_manager.set_setting(key, value, 'boolean')
                elif key in ['cleanup_frequency_hours', 'max_storage_gb', 'audio_retention_days', 
                           'text_retention_days', 'max_recording_duration']:
                    self.db_manager.set_setting(key, int(value), 'integer')
                else:
                    self.db_manager.set_setting(key, value, 'string')
            
            messagebox.showinfo("Success", "Settings saved successfully!")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save settings: {str(e)}")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Reset Settings", 
                              "Are you sure you want to reset all settings to their default values?"):
            try:
                # Reload default settings
                self.db_manager.load_default_settings()
                # Reload the GUI
                self.load_settings()
                messagebox.showinfo("Success", "Settings reset to defaults!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to reset settings: {str(e)}")
    
    def close_settings(self):
        """Close the settings window"""
        if self.settings_window:
            self.settings_window.destroy()
            self.settings_window = None
