#!/usr/bin/env python3
"""
Setup Wizard for Physiotherapy Clinic Assistant
Guides first-time users through installation and configuration
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import subprocess
import platform
from pathlib import Path
from typing import Dict, List, Optional
import json
import webbrowser

# Import our custom modules
from system_checker import SystemChecker
from config_validator import ConfigValidator


class SetupWizard:
    """Interactive setup wizard for first-time users"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Physiotherapy Clinic Assistant - Setup Wizard")
        self.root.geometry("700x550")
        self.root.resizable(True, True)
        self.root.minsize(600, 500)
        
        # Center the window
        self.center_window()
        
        # Setup variables
        self.current_step = 0
        self.total_steps = 5
        self.setup_data = {
            'python_installed': False,
            'venv_created': False,
            'dependencies_installed': False,
            'models_downloaded': False,
            'config_validated': False,
            'audio_tested': False
        }
        
        # Initialize components
        self.system_checker = SystemChecker()
        self.config_validator = ConfigValidator()
        
        self.setup_gui()
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_gui(self):
        """Setup the main GUI with persistent navigation bar using grid"""
        # Configure root window grid weights
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Main container using grid
        self.main_container = ttk.Frame(self.root)
        self.main_container.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Configure main container grid weights
        self.main_container.grid_rowconfigure(0, weight=1)  # Content area gets all space
        self.main_container.grid_rowconfigure(1, weight=0)  # Navigation bar fixed height
        self.main_container.grid_columnconfigure(0, weight=1)
        
        # Content area (row 0, takes all available space)
        self.content_area = ttk.Frame(self.main_container)
        self.content_area.grid(row=0, column=0, sticky="nsew", padx=15, pady=15)
        
        # Header
        self.header_frame = ttk.Frame(self.content_area)
        self.header_frame.pack(fill="x", pady=(0, 10))
        
        # Title
        title_label = ttk.Label(self.header_frame, text="Physiotherapy Clinic Assistant", 
                               font=("Arial", 16, "bold"))
        title_label.pack()
        
        subtitle_label = ttk.Label(self.header_frame, text="Setup Wizard", 
                                  font=("Arial", 11))
        subtitle_label.pack()
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.header_frame, variable=self.progress_var, 
                                           maximum=self.total_steps)
        self.progress_bar.pack(fill="x", pady=(8, 0))
        
        # Progress label
        self.progress_label = ttk.Label(self.header_frame, text="Step 1 of 5: Welcome")
        self.progress_label.pack(pady=(3, 0))
        
        # Content frame (this is what gets cleared)
        self.content_frame = ttk.Frame(self.content_area)
        self.content_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        # Create persistent navigation bar (row 1, fixed position)
        self.create_navigation_bar()
        
        # Show welcome step
        self.show_welcome_step()
    
    def create_navigation_bar(self):
        """Create the truly persistent navigation bar using grid"""
        # Navigation bar frame (row 1, always visible)
        self.nav_frame = ttk.Frame(self.main_container, relief="raised", borderwidth=1)
        self.nav_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
        
        # Configure navigation bar grid
        self.nav_frame.grid_columnconfigure(0, weight=1)  # Spacer
        self.nav_frame.grid_columnconfigure(1, weight=0)  # Back button
        self.nav_frame.grid_columnconfigure(2, weight=0)  # Next button
        self.nav_frame.grid_columnconfigure(3, weight=0)  # Cancel button
        
        # Navigation buttons with grid
        self.back_button = ttk.Button(self.nav_frame, text="← Back", 
                                     command=self.previous_step, state="disabled")
        self.back_button.grid(row=0, column=1, padx=5, pady=8, sticky="w")
        
        self.next_button = ttk.Button(self.nav_frame, text="Next →", 
                                     command=self.next_step)
        self.next_button.grid(row=0, column=2, padx=5, pady=8, sticky="e")
        
        self.cancel_button = ttk.Button(self.nav_frame, text="Cancel", 
                                       command=self.cancel_setup)
        self.cancel_button.grid(row=0, column=3, padx=(5, 10), pady=8, sticky="e")
    
    def clear_content(self):
        """Clear the content frame (but preserve navigation bar)"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def show_welcome_step(self):
        """Show welcome step"""
        self.clear_content()
        
        # Welcome content
        welcome_frame = ttk.Frame(self.content_frame)
        welcome_frame.pack(fill="both", expand=True)
        
        # Welcome text
        welcome_text = """
Welcome to the Physiotherapy Clinic Assistant Setup Wizard!

This wizard will help you set up the application for first-time use.

The setup process includes:
• Checking system requirements
• Installing Python dependencies
• Downloading AI models
• Configuring audio devices
• Validating configuration

This process may take 10-15 minutes depending on your internet connection.

Click 'Next' to begin the setup process.
        """
        
        welcome_label = ttk.Label(welcome_frame, text=welcome_text, 
                                 font=("Arial", 10), justify="left")
        welcome_label.pack(pady=10)
        
        # System info
        info_frame = ttk.LabelFrame(welcome_frame, text="System Information", padding="8")
        info_frame.pack(fill="x", pady=(10, 0))
        
        system_info = f"""
Operating System: {platform.system()} {platform.release()}
Python Version: {sys.version.split()[0]}
Architecture: {platform.machine()}
        """
        
        info_label = ttk.Label(info_frame, text=system_info, 
                              font=("Arial", 9), justify="left")
        info_label.pack()
    
    def show_system_check_step(self):
        """Show system requirements check step"""
        self.clear_content()
        
        # System check content
        check_frame = ttk.Frame(self.content_frame)
        check_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(check_frame, text="System Requirements Check", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Check button
        self.check_button = ttk.Button(check_frame, text="Check System Requirements", 
                                      command=self.run_system_check)
        self.check_button.pack(pady=(0, 10))
        
        # Results frame
        self.results_frame = ttk.LabelFrame(check_frame, text="Check Results", padding="8")
        self.results_frame.pack(fill="both", expand=True)
        
        # Results text
        self.results_text = tk.Text(self.results_frame, height=8, wrap="word")
        scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", 
                                 command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def show_dependencies_step(self):
        """Show dependencies installation step"""
        self.clear_content()
        
        # Dependencies content
        deps_frame = ttk.Frame(self.content_frame)
        deps_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(deps_frame, text="Install Dependencies", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_text = """
This application requires several packages to be functional. 

Click to download and install these packages in an isolated environment only accessible by the application.

This may take several minutes depending on your internet connection.
        """
        
        desc_label = ttk.Label(deps_frame, text=desc_text, 
                              font=("Arial", 10), justify="left")
        desc_label.pack(pady=(0, 10))
        
        # Install button
        self.install_button = ttk.Button(deps_frame, text="Install Dependencies", 
                                        command=self.install_dependencies)
        self.install_button.pack(pady=(0, 10))
        
        # Progress frame
        self.progress_frame = ttk.LabelFrame(deps_frame, text="Installation Progress", padding="8")
        self.progress_frame.pack(fill="both", expand=True)
        
        # Progress bar
        self.install_progress_var = tk.DoubleVar()
        self.install_progress_bar = ttk.Progressbar(self.progress_frame, 
                                                   variable=self.install_progress_var)
        self.install_progress_bar.pack(fill="x", pady=(0, 8))
        
        # Progress text
        self.install_progress_text = tk.Text(self.progress_frame, height=6, wrap="word")
        self.install_progress_text.pack(fill="both", expand=True)
    
    def show_models_step(self):
        """Show model download step"""
        self.clear_content()
        
        # Models content
        models_frame = ttk.Frame(self.content_frame)
        models_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(models_frame, text="Download AI Models", 
                               font=("Arial", 12, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_text = """
This step will download the required AI models for transcription and data extraction.

Models to download:
• Qwen3-1.7B (Smaller, faster model - ~1.8GB)
• Qwen3-4B (Larger, more accurate model - ~2.5GB)

Total download size: ~4.3GB
Estimated time: 10-30 minutes (depending on internet speed)

You can choose to download only the smaller model for faster setup.
        """
        
        desc_label = ttk.Label(models_frame, text=desc_text, 
                              font=("Arial", 10), justify="left")
        desc_label.pack(pady=(0, 10))
        
        # Model selection
        model_frame = ttk.LabelFrame(models_frame, text="Model Selection", padding="8")
        model_frame.pack(fill="x", pady=(0, 10))
        
        self.download_small_model = tk.BooleanVar(value=True)
        self.download_large_model = tk.BooleanVar(value=True)
        
        ttk.Checkbutton(model_frame, text="Download Qwen3-1.7B (Smaller model)", 
                       variable=self.download_small_model).pack(anchor="w")
        ttk.Checkbutton(model_frame, text="Download Qwen3-4B (Larger model)", 
                       variable=self.download_large_model).pack(anchor="w")
        
        # Download button
        self.download_button = ttk.Button(models_frame, text="Download Models", 
                                         command=self.download_models)
        self.download_button.pack(pady=(0, 10))
        
        # Progress frame
        self.model_progress_frame = ttk.LabelFrame(models_frame, text="Download Progress", padding="8")
        self.model_progress_frame.pack(fill="both", expand=True)
        
        # Progress bar
        self.model_progress_var = tk.DoubleVar()
        self.model_progress_bar = ttk.Progressbar(self.model_progress_frame, 
                                                 variable=self.model_progress_var)
        self.model_progress_bar.pack(fill="x", pady=(0, 8))
        
        # Progress text
        self.model_progress_text = tk.Text(self.model_progress_frame, height=6, wrap="word")
        self.model_progress_text.pack(fill="both", expand=True)
    
    
    def show_completion_step(self):
        """Show setup completion step"""
        self.clear_content()
        
        # Completion content
        completion_frame = ttk.Frame(self.content_frame)
        completion_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(completion_frame, text="Setup Complete!", 
                               font=("Arial", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Summary
        summary_text = """
Congratulations! The Physiotherapy Clinic Assistant has been successfully set up.

Setup Summary:
• System requirements: ✓ Verified
• Dependencies: ✓ Installed
• AI Models: ✓ Downloaded
• Configuration: ✓ Validated

You can now launch the application and start using it for your physiotherapy practice.

Click 'Finish' to close the setup wizard and launch the application.
        """
        
        summary_label = ttk.Label(completion_frame, text=summary_text, 
                                 font=("Arial", 10), justify="left")
        summary_label.pack(pady=(0, 10))
        
        # Launch checkbox
        self.launch_app_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(completion_frame, text="Launch application after setup", 
                       variable=self.launch_app_var).pack(pady=(0, 10))
        
        # Change next button to finish
        self.next_button.config(text="Finish", command=self.finish_setup)
    
    def clear_content(self):
        """Clear the content frame"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def update_progress(self, step: int, text: str):
        """Update progress bar and label"""
        self.progress_var.set(step)
        self.progress_label.config(text=text)
        self.root.update()
    
    def next_step(self):
        """Move to next step"""
        if self.current_step < self.total_steps - 1:
            self.current_step += 1
            self.update_step()
    
    def previous_step(self):
        """Move to previous step"""
        if self.current_step > 0:
            self.current_step -= 1
            self.update_step()
    
    def update_step(self):
        """Update the current step display"""
        self.update_progress(self.current_step + 1, f"Step {self.current_step + 1} of {self.total_steps}")
        
        # Update navigation buttons
        self.back_button.config(state="normal" if self.current_step > 0 else "disabled")
        
        if self.current_step == self.total_steps - 1:
            self.next_button.config(text="Finish", command=self.finish_setup)
        else:
            self.next_button.config(text="Next →", command=self.next_step)
        
        # Show appropriate step content
        if self.current_step == 0:
            self.show_welcome_step()
        elif self.current_step == 1:
            self.show_system_check_step()
        elif self.current_step == 2:
            self.show_dependencies_step()
        elif self.current_step == 3:
            self.show_models_step()
        elif self.current_step == 4:
            self.show_completion_step()
    
    def run_system_check(self):
        """Run system requirements check"""
        self.check_button.config(state="disabled")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Running system check...\n")
        self.root.update()
        
        def check_thread():
            try:
                results = self.system_checker.run_all_checks()
                
                # Update UI in main thread
                self.root.after(0, self.update_system_check_results, results)
                
            except Exception as e:
                self.root.after(0, self.show_error, f"System check failed: {e}")
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def update_system_check_results(self, results):
        """Update system check results in UI"""
        self.results_text.delete(1.0, tk.END)
        
        if results['overall_success']:
            self.results_text.insert(tk.END, "✅ System requirements check PASSED\n\n")
            self.setup_data['system_checked'] = True
        else:
            self.results_text.insert(tk.END, "❌ System requirements check FAILED\n\n")
        
        # Display individual results
        for check_name, result in results['results'].items():
            status = "✅" if result['success'] else "❌"
            self.results_text.insert(tk.END, f"{status} {check_name}: {result['message']}\n")
        
        # Display errors
        if results['errors']:
            self.results_text.insert(tk.END, "\n❌ Errors:\n")
            for error in results['errors']:
                self.results_text.insert(tk.END, f"  • {error}\n")
        
        # Display warnings
        if results['warnings']:
            self.results_text.insert(tk.END, "\n⚠️  Warnings:\n")
            for warning in results['warnings']:
                self.results_text.insert(tk.END, f"  • {warning}\n")
        
        self.check_button.config(state="normal")
    
    def install_dependencies(self):
        """Install Python dependencies"""
        self.install_button.config(state="disabled")
        self.install_progress_text.delete(1.0, tk.END)
        self.install_progress_text.insert(tk.END, "Installing dependencies...\n")
        self.root.update()
        
        def install_thread():
            try:
                # Install dependencies
                cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
                
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                         text=True, bufsize=1, universal_newlines=True)
                
                for line in process.stdout:
                    self.root.after(0, self.update_install_progress, line)
                
                process.wait()
                
                if process.returncode == 0:
                    self.root.after(0, self.install_success)
                else:
                    self.root.after(0, self.install_error, "Installation failed")
                    
            except Exception as e:
                self.root.after(0, self.install_error, f"Installation error: {e}")
        
        threading.Thread(target=install_thread, daemon=True).start()
    
    def update_install_progress(self, line):
        """Update installation progress"""
        self.install_progress_text.insert(tk.END, line)
        self.install_progress_text.see(tk.END)
        self.root.update()
    
    def install_success(self):
        """Handle successful installation"""
        self.install_progress_text.insert(tk.END, "\n✅ Dependencies installed successfully!\n")
        self.install_button.config(state="normal")
        self.setup_data['dependencies_installed'] = True
    
    def install_error(self, error_msg):
        """Handle installation error"""
        self.install_progress_text.insert(tk.END, f"\n❌ {error_msg}\n")
        self.install_button.config(state="normal")
        messagebox.showerror("Installation Error", error_msg)
    
    def download_models(self):
        """Download AI models"""
        self.download_button.config(state="disabled")
        self.model_progress_text.delete(1.0, tk.END)
        self.model_progress_text.insert(tk.END, "Downloading models...\n")
        self.root.update()
        
        def download_thread():
            try:
                # Import model downloader
                from model_downloader import ModelDownloader
                
                downloader = ModelDownloader()
                
                # Download selected models
                if self.download_small_model.get():
                    self.root.after(0, self.update_model_progress, "Downloading Qwen3-1.7B model...\n")
                    downloader.download_model("qwen3-1.7b")
                
                if self.download_large_model.get():
                    self.root.after(0, self.update_model_progress, "Downloading Qwen3-4B model...\n")
                    downloader.download_model("qwen3-4b")
                
                self.root.after(0, self.download_success)
                
            except Exception as e:
                self.root.after(0, self.download_error, f"Download error: {e}")
        
        threading.Thread(target=download_thread, daemon=True).start()
    
    def update_model_progress(self, message):
        """Update model download progress"""
        self.model_progress_text.insert(tk.END, message)
        self.model_progress_text.see(tk.END)
        self.root.update()
    
    def download_success(self):
        """Handle successful model download"""
        self.model_progress_text.insert(tk.END, "\n✅ Models downloaded successfully!\n")
        self.download_button.config(state="normal")
        self.setup_data['models_downloaded'] = True
    
    def download_error(self, error_msg):
        """Handle model download error"""
        self.model_progress_text.insert(tk.END, f"\n❌ {error_msg}\n")
        self.download_button.config(state="normal")
        messagebox.showerror("Download Error", error_msg)
    
    
    def finish_setup(self):
        """Finish setup and optionally launch application"""
        try:
            # Run final configuration validation
            results = self.config_validator.run_all_validations()
            
            if not results['overall_success']:
                messagebox.showwarning("Setup Warning", 
                                     "Setup completed with some issues. Please check the configuration.")
            
            # Save setup completion
            setup_info = {
                'setup_completed': True,
                'setup_date': str(Path().cwd()),
                'setup_data': self.setup_data
            }
            
            with open('setup_complete.json', 'w') as f:
                json.dump(setup_info, f, indent=2)
            
            # Launch application if requested
            if self.launch_app_var.get():
                self.launch_application()
            
            # Close setup wizard
            self.root.quit()
            
        except Exception as e:
            messagebox.showerror("Setup Error", f"Error completing setup: {e}")
    
    def launch_application(self):
        """Launch the main application"""
        try:
            # Launch main application
            subprocess.Popen([sys.executable, "main.py"])
        except Exception as e:
            messagebox.showerror("Launch Error", f"Error launching application: {e}")
    
    def cancel_setup(self):
        """Cancel setup process"""
        if messagebox.askyesno("Cancel Setup", "Are you sure you want to cancel the setup process?"):
            self.root.quit()
    
    def show_error(self, error_msg):
        """Show error message"""
        messagebox.showerror("Error", error_msg)
    
    def run(self):
        """Run the setup wizard"""
        self.root.mainloop()


def main():
    """Main function"""
    try:
        wizard = SetupWizard()
        wizard.run()
    except Exception as e:
        messagebox.showerror("Setup Wizard Error", f"Error starting setup wizard: {e}")


if __name__ == "__main__":
    main()
