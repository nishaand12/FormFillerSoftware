#!/usr/bin/env python3
"""
Uninstaller for Physiotherapy Clinic Assistant
Provides complete removal of the application and all associated files
"""

import os
import sys
import shutil
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path
import subprocess


class Uninstaller:
    """Complete uninstaller for the application"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Physiotherapy Clinic Assistant - Uninstaller")
        self.root.geometry("500x400")
        self.root.resizable(False, False)
        
        # Center the window
        self.center_window()
        
        # Application info
        self.app_name = "PhysioClinicAssistant"
        self.app_path = Path("/Applications") / f"{self.app_name}.app"
        
        # Files and directories to remove
        self.files_to_remove = [
            # Application bundle
            self.app_path,
            
            # Application Support files
            Path.home() / "Library" / "Application Support" / self.app_name,
            
            # Preferences
            Path.home() / "Library" / "Preferences" / f"com.physioclinic.{self.app_name.lower()}.plist",
            
            # Caches
            Path.home() / "Library" / "Caches" / self.app_name,
            
            # Logs
            Path.home() / "Library" / "Logs" / self.app_name,
            
            # Saved Application State
            Path.home() / "Library" / "Saved Application State" / f"com.physioclinic.{self.app_name.lower()}.savedState",
            
            # User data (if in Documents)
            Path.home() / "Documents" / self.app_name,
            
            # Desktop shortcut (if exists)
            Path.home() / "Desktop" / f"{self.app_name}.app",
            
            # Hidden config directory
            Path.home() / f".{self.app_name.lower()}",
        ]
        
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
        """Setup the uninstaller GUI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="30")
        main_frame.pack(fill="both", expand=True)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill="x", pady=(0, 20))
        
        # Warning icon
        icon_label = ttk.Label(header_frame, text="⚠️", font=("Arial", 48))
        icon_label.pack()
        
        # Title
        title_label = ttk.Label(header_frame, text="Uninstall Physiotherapy Clinic Assistant", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(10, 5))
        
        # Content frame
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Warning text
        warning_text = """
This will completely remove the Physiotherapy Clinic Assistant and all associated files from your Mac.

The following will be removed:
• Application from Applications folder
• All user data and settings
• Configuration files
• Cache and log files
• Any saved preferences

This action cannot be undone.
        """
        
        warning_label = ttk.Label(content_frame, text=warning_text, 
                                 font=("Arial", 11), justify="left")
        warning_label.pack(pady=(0, 20))
        
        # Files to remove list
        files_frame = ttk.LabelFrame(content_frame, text="Files and Folders to Remove", padding="15")
        files_frame.pack(fill="both", expand=True)
        
        # Create scrollable text widget
        self.files_text = tk.Text(files_frame, height=8, wrap="word", state="disabled")
        scrollbar = ttk.Scrollbar(files_frame, orient="vertical", command=self.files_text.yview)
        self.files_text.configure(yscrollcommand=scrollbar.set)
        
        self.files_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Populate files list
        self.populate_files_list()
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x")
        
        # Uninstall button
        self.uninstall_button = ttk.Button(buttons_frame, text="Uninstall Application", 
                                          command=self.start_uninstall, 
                                          style="Accent.TButton")
        self.uninstall_button.pack(side="right", padx=(10, 0))
        
        # Cancel button
        ttk.Button(buttons_frame, text="Cancel", 
                  command=self.cancel_uninstall).pack(side="right")
        
        # Progress frame (initially hidden)
        self.progress_frame = ttk.LabelFrame(main_frame, text="Uninstall Progress", padding="15")
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.progress_frame, variable=self.progress_var)
        self.progress_bar.pack(fill="x", pady=(0, 10))
        
        # Progress text
        self.progress_text = tk.Text(self.progress_frame, height=6, wrap="word")
        self.progress_text.pack(fill="both", expand=True)
    
    def populate_files_list(self):
        """Populate the list of files to be removed"""
        self.files_text.config(state="normal")
        self.files_text.delete(1.0, tk.END)
        
        for file_path in self.files_to_remove:
            if file_path.exists():
                status = "✓ Will be removed"
                self.files_text.insert(tk.END, f"{status}: {file_path}\n")
            else:
                status = "○ Not found"
                self.files_text.insert(tk.END, f"{status}: {file_path}\n")
        
        self.files_text.config(state="disabled")
    
    def start_uninstall(self):
        """Start the uninstall process"""
        # Confirm uninstall
        result = messagebox.askyesno("Confirm Uninstall", 
                                   "Are you sure you want to completely remove the Physiotherapy Clinic Assistant?\n\n"
                                   "This action cannot be undone.")
        if not result:
            return
        
        # Hide main content and show progress
        self.uninstall_button.config(state="disabled")
        self.progress_frame.pack(fill="both", expand=True, pady=(20, 0))
        self.root.update()
        
        # Start uninstall in background thread
        import threading
        uninstall_thread = threading.Thread(target=self.uninstall_application, daemon=True)
        uninstall_thread.start()
    
    def uninstall_application(self):
        """Perform the uninstall"""
        try:
            total_files = len(self.files_to_remove)
            removed_count = 0
            
            self.update_progress(0, "Starting uninstall process...")
            
            for i, file_path in enumerate(self.files_to_remove):
                if file_path.exists():
                    try:
                        if file_path.is_dir():
                            shutil.rmtree(file_path)
                            self.update_progress(
                                (i + 1) / total_files * 100, 
                                f"Removed directory: {file_path}"
                            )
                        else:
                            file_path.unlink()
                            self.update_progress(
                                (i + 1) / total_files * 100, 
                                f"Removed file: {file_path}"
                            )
                        removed_count += 1
                    except Exception as e:
                        self.update_progress(
                            (i + 1) / total_files * 100, 
                            f"Warning: Could not remove {file_path}: {e}"
                        )
                else:
                    self.update_progress(
                        (i + 1) / total_files * 100, 
                        f"Skipped (not found): {file_path}"
                    )
            
            # Clear any remaining caches
            self.clear_system_caches()
            
            self.update_progress(100, f"Uninstall complete! Removed {removed_count} items.")
            
            # Show completion message
            self.progress_text.insert(tk.END, "\n✅ Uninstall completed successfully!\n")
            self.progress_text.insert(tk.END, "The Physiotherapy Clinic Assistant has been completely removed from your Mac.\n")
            self.progress_text.see(tk.END)
            
            # Update button
            self.uninstall_button.config(text="Uninstall Complete", state="disabled")
            
            # Add close button
            close_button = ttk.Button(self.progress_frame, text="Close Uninstaller", 
                                    command=self.root.quit)
            close_button.pack(pady=(10, 0))
            
        except Exception as e:
            self.uninstall_error(f"Uninstall failed: {e}")
    
    def clear_system_caches(self):
        """Clear system caches and rebuild Launch Services database"""
        try:
            self.update_progress(95, "Clearing system caches...")
            
            # Rebuild Launch Services database
            subprocess.run(["/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister", "-kill", "-r", "-domain", "local", "-domain", "system", "-domain", "user"], 
                          capture_output=True)
            
            self.update_progress(98, "System caches cleared")
            
        except Exception as e:
            self.update_progress(95, f"Warning: Could not clear system caches: {e}")
    
    def update_progress(self, value: int, message: str):
        """Update progress bar and text"""
        self.progress_var.set(value)
        self.progress_text.insert(tk.END, f"{message}\n")
        self.progress_text.see(tk.END)
        self.root.update()
    
    def uninstall_error(self, error_msg: str):
        """Handle uninstall error"""
        self.progress_text.insert(tk.END, f"\n❌ {error_msg}\n")
        self.progress_text.see(tk.END)
        self.uninstall_button.config(text="Uninstall Failed", state="disabled")
        
        # Add retry button
        retry_button = ttk.Button(self.progress_frame, text="Retry Uninstall", 
                                command=self.retry_uninstall)
        retry_button.pack(pady=(10, 0))
    
    def retry_uninstall(self):
        """Retry the uninstall"""
        # Reset state
        self.progress_var.set(0)
        self.progress_text.delete(1.0, tk.END)
        
        # Hide progress frame
        self.progress_frame.pack_forget()
        
        # Re-enable uninstall button
        self.uninstall_button.config(text="Uninstall Application", state="normal")
    
    def cancel_uninstall(self):
        """Cancel the uninstall"""
        self.root.quit()
    
    def run(self):
        """Run the uninstaller"""
        self.root.mainloop()


def main():
    """Main function"""
    try:
        uninstaller = Uninstaller()
        uninstaller.run()
    except Exception as e:
        messagebox.showerror("Uninstaller Error", f"Error starting uninstaller: {e}")


if __name__ == "__main__":
    main()
