#!/usr/bin/env python3
"""
Stored Form Fields Editor for Physiotherapy Clinic Assistant
Provides interface for editing stored professional data for all form types
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import json
import os
from typing import Dict, Any, List, Optional


class StoredFormFieldsEditor:
    """Stored Form Fields editor for managing professional information"""
    
    def __init__(self, parent, config_dir: Optional[str] = None):
        self.parent = parent
        
        # Use proper resource path for config files (read-only from bundle)
        if config_dir is None:
            try:
                from app_paths import get_resource_path
                self.config_dir = str(get_resource_path("config"))
            except ImportError:
                import sys
                from pathlib import Path
                if getattr(sys, '_MEIPASS', None):
                    self.config_dir = str(Path(sys._MEIPASS) / "config")
                else:
                    self.config_dir = "config"
        else:
            self.config_dir = config_dir
        
        self.editor_window = None
        
        # Form configurations
        self.form_configs = {
            'wsib': {
                'name': 'WSIB FAF',
                'stored_data_file': 'wsib_stored_data.json',
                'field_types_file': 'wsib_field_types.json',
                'sections': ['health_professional_info', 'clinic_info']
            },
            'ocf18': {
                'name': 'FSRA OCF-18',
                'stored_data_file': 'ocf18_stored_data.json',
                'field_types_file': 'ocf18_field_types.json',
                'sections': ['clinic_info', 'health_provider_info', 'professional_info']
            },
            'ocf23': {
                'name': 'FSRA OCF-23',
                'stored_data_file': 'ocf23_stored_data.json',
                'field_types_file': 'ocf23_field_types_simplified.json',
                'sections': ['clinic_info', 'health_professional_info', 'cover_page']
            }
        }
        
        # Load current data
        self.current_data = {}
        self.field_types = {}
        self.load_all_data()
    
    def show_editor(self):
        """Show the stored data editor window"""
        if self.editor_window:
            self.editor_window.lift()
            return
        
        self.editor_window = tk.Toplevel(self.parent)
        self.editor_window.title("Stored Form Fields - Professional Information")
        self.editor_window.geometry("1200x800")
        self.editor_window.resizable(True, True)
        
        # Center the window
        self.editor_window.transient(self.parent)
        self.editor_window.grab_set()
        
        self.create_widgets()
        self.load_all_data()
        
        # Handle window close
        self.editor_window.protocol("WM_DELETE_WINDOW", self.close_editor)
    
    def create_widgets(self):
        """Create the main editor widgets"""
        # Main frame
        main_frame = ttk.Frame(self.editor_window, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.editor_window.columnconfigure(0, weight=1)
        self.editor_window.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Title and description
        title_frame = ttk.Frame(main_frame)
        title_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        title_label = ttk.Label(title_frame, text="📋 Stored Form Fields", 
                               font=("Arial", 16, "bold"))
        title_label.pack(side=tk.LEFT)
        
        desc_label = ttk.Label(title_frame, 
                              text="Edit default data that will be automatically filled in forms",
                              font=("Arial", 10), foreground="gray")
        desc_label.pack(side=tk.RIGHT)
        
        # Form selection
        form_frame = ttk.LabelFrame(main_frame, text="Select Form Type", padding="10")
        form_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Form selection buttons
        self.form_var = tk.StringVar(value="wsib")
        form_buttons_frame = ttk.Frame(form_frame)
        form_buttons_frame.pack(fill=tk.X, pady=(0, 10))
        
        for form_key, config in self.form_configs.items():
            btn = ttk.Radiobutton(form_buttons_frame, text=config['name'], 
                                variable=self.form_var, value=form_key,
                                command=self.on_form_selection_change)
            btn.pack(anchor=tk.W, pady=2)
        
        # Section selection
        section_frame = ttk.LabelFrame(form_frame, text="Select Section", padding="10")
        section_frame.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
        
        self.section_var = tk.StringVar()
        self.section_listbox = tk.Listbox(section_frame, height=8)
        self.section_listbox.pack(fill=tk.BOTH, expand=True)
        self.section_listbox.bind('<<ListboxSelect>>', self.on_section_selection_change)
        
        # Add scrollbar for section list
        section_scrollbar = ttk.Scrollbar(section_frame, orient="vertical", command=self.section_listbox.yview)
        self.section_listbox.configure(yscrollcommand=section_scrollbar.set)
        section_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Data editing area
        edit_frame = ttk.LabelFrame(main_frame, text="Edit Data", padding="10")
        edit_frame.grid(row=1, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Create scrollable frame for data editing
        canvas = tk.Canvas(edit_frame)
        scrollbar = ttk.Scrollbar(edit_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Control buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 0))
        
        ttk.Button(button_frame, text="💾 Save Changes", 
                  command=self.save_changes).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="❌ Cancel", 
                  command=self.close_editor).pack(side=tk.RIGHT)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, 
                               font=("Arial", 9), foreground="gray")
        status_label.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Initialize form selection
        self.on_form_selection_change()
    
    def load_all_data(self):
        """Load all stored data and field types"""
        for form_key, config in self.form_configs.items():
            # Load stored data
            stored_data_path = os.path.join(self.config_dir, config['stored_data_file'])
            if os.path.exists(stored_data_path):
                try:
                    with open(stored_data_path, 'r') as f:
                        self.current_data[form_key] = json.load(f)
                except Exception as e:
                    print(f"Error loading {config['stored_data_file']}: {e}")
                    self.current_data[form_key] = {}
            else:
                self.current_data[form_key] = {}
            
            # Load field types
            field_types_path = os.path.join(self.config_dir, config['field_types_file'])
            if os.path.exists(field_types_path):
                try:
                    with open(field_types_path, 'r') as f:
                        data = json.load(f)
                        self.field_types[form_key] = data.get('field_types', {})
                except Exception as e:
                    print(f"Error loading {config['field_types_file']}: {e}")
                    self.field_types[form_key] = {}
            else:
                self.field_types[form_key] = {}
    
    def on_form_selection_change(self):
        """Handle form selection change"""
        form_key = self.form_var.get()
        config = self.form_configs[form_key]
        
        # Update section list
        self.section_listbox.delete(0, tk.END)
        for section in config['sections']:
            self.section_listbox.insert(tk.END, section.replace('_', ' ').title())
        
        # Clear data editing area
        self.clear_data_editing_area()
        
        # Update status
        self.status_var.set(f"Selected: {config['name']}")
    
    def on_section_selection_change(self, event):
        """Handle section selection change"""
        selection = self.section_listbox.curselection()
        if not selection:
            return
        
        form_key = self.form_var.get()
        section_index = selection[0]
        section_name = self.form_configs[form_key]['sections'][section_index]
        
        # Clear previous data editing widgets
        self.clear_data_editing_area()
        
        # Load section data
        self.load_section_data(form_key, section_name)
    
    def clear_data_editing_area(self):
        """Clear the data editing area"""
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
    
    def load_section_data(self, form_key: str, section_name: str):
        """Load and display section data for editing"""
        # Get section data
        section_data = self.current_data.get(form_key, {}).get(section_name, {})
        field_types = self.field_types.get(form_key, {})
        
        if not section_data:
            # Show empty section message
            empty_label = ttk.Label(self.scrollable_frame, 
                                   text=f"No data found for {section_name.replace('_', ' ').title()}",
                                   font=("Arial", 12), foreground="gray")
            empty_label.pack(pady=20)
            return
        
        # Create section title
        title_label = ttk.Label(self.scrollable_frame, 
                               text=f"{section_name.replace('_', ' ').title()} Data",
                               font=("Arial", 14, "bold"))
        title_label.pack(anchor=tk.W, pady=(0, 15))
        
        # Create form fields
        self.field_widgets = {}
        row = 0
        
        for field_name, field_value in section_data.items():
            # Create field frame
            field_frame = ttk.Frame(self.scrollable_frame)
            field_frame.pack(fill=tk.X, pady=5)
            
            # Field label
            label_text = field_name.replace('_', ' ').title()
            field_label = ttk.Label(field_frame, text=label_text, width=25)
            field_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
            
            # Field type
            field_type = field_types.get(field_name, 'text')
            
            # Create appropriate widget based on field type
            if field_type == 'checkbox':
                widget = ttk.Checkbutton(field_frame)
                widget.grid(row=0, column=1, sticky=tk.W)
                if field_value:
                    widget.state(['selected'])
            elif field_type == 'radio_group':
                # For radio groups, create a combobox with common options
                widget = ttk.Combobox(field_frame, width=30)
                widget.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
                # Add common radio group options
                widget['values'] = ['Yes', 'No', 'N/A', 'Other']
                if field_value:
                    widget.set(field_value)
            elif field_type in ['phone', 'email', 'postal_code']:
                widget = ttk.Entry(field_frame, width=30)
                widget.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
                if field_value:
                    widget.insert(0, str(field_value))
            else:  # text, date, number, etc.
                widget = ttk.Entry(field_frame, width=30)
                widget.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
                if field_value:
                    widget.insert(0, str(field_value))
            
            # Field type indicator
            type_label = ttk.Label(field_frame, text=f"({field_type})", 
                                  font=("Arial", 8), foreground="gray")
            type_label.grid(row=0, column=2, sticky=tk.W, padx=(5, 0))
            
            # Store widget reference
            self.field_widgets[field_name] = {
                'widget': widget,
                'type': field_type,
                'section': section_name
            }
            
            # Configure grid weights
            field_frame.columnconfigure(1, weight=1)
            row += 1
        
        # Add new field button
        new_field_frame = ttk.Frame(self.scrollable_frame)
        new_field_frame.pack(fill=tk.X, pady=(20, 0))
        
        ttk.Button(new_field_frame, text="➕ Add New Field", 
                  command=lambda: self.add_new_field(form_key, section_name)).pack(side=tk.LEFT)
    
    def add_new_field(self, form_key: str, section_name: str):
        """Add a new field to the section"""
        # Get field name
        field_name = simpledialog.askstring("New Field", "Enter field name:")
        if not field_name:
            return
        
        # Get field type
        field_type = simpledialog.askstring("Field Type", 
                                          "Enter field type (text, checkbox, phone, email, etc.):")
        if not field_type:
            field_type = 'text'
        
        # Add to current data
        if section_name not in self.current_data[form_key]:
            self.current_data[form_key][section_name] = {}
        
        self.current_data[form_key][section_name][field_name] = ""
        
        # Reload section data
        self.load_section_data(form_key, section_name)
        
        self.status_var.set(f"Added new field: {field_name}")
    
    def save_changes(self):
        """Save all changes to the stored data files"""
        try:
            # Collect data from widgets
            for field_name, field_info in self.field_widgets.items():
                widget = field_info['widget']
                field_type = field_info['type']
                section_name = field_info['section']
                form_key = self.form_var.get()
                
                # Get value based on widget type
                if field_type == 'checkbox':
                    value = widget.instate(['selected'])
                elif isinstance(widget, ttk.Combobox):
                    value = widget.get()
                else:  # Entry widget
                    value = widget.get()
                
                # Update current data
                if section_name not in self.current_data[form_key]:
                    self.current_data[form_key][section_name] = {}
                
                self.current_data[form_key][section_name][field_name] = value
            
            # Save to file
            form_key = self.form_var.get()
            config = self.form_configs[form_key]
            stored_data_path = os.path.join(self.config_dir, config['stored_data_file'])
            
            with open(stored_data_path, 'w') as f:
                json.dump(self.current_data[form_key], f, indent=2)
            
            self.status_var.set(f"✅ Saved changes to {config['name']}")
            messagebox.showinfo("Success", f"Changes saved successfully to {config['stored_data_file']}")
            
        except Exception as e:
            error_msg = f"Error saving changes: {str(e)}"
            self.status_var.set(f"❌ {error_msg}")
            messagebox.showerror("Error", error_msg)
    
    def close_editor(self):
        """Close the editor window"""
        if self.editor_window:
            self.editor_window.destroy()
            self.editor_window = None
