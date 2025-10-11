#!/usr/bin/env python3
"""
macOS Installer for Physiotherapy Clinic Assistant
Creates a seamless installation experience for Mac users
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import shutil
from pathlib import Path
import json
import threading
import time


class MacInstaller:
    """macOS installer with setup wizard integration"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Physiotherapy Clinic Assistant - Installer")
        self.root.geometry("700x550")
        self.root.resizable(True, True)
        self.root.minsize(600, 500)
        
        # Center the window
        self.center_window()
        
        # Installation paths
        self.app_name = "PhysioClinicAssistant"
        self.app_path = Path("/Applications") / f"{self.app_name}.app"
        self.temp_path = Path("/tmp") / f"{self.app_name}_installer"
        self.drag_target_path = Path.home() / "Desktop" / f"{self.app_name}.app"
        
        # Installation state
        self.installation_complete = False
        self.setup_wizard_launched = False
        self.current_step = 0
        self.total_steps = 4
        
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
        """Setup the installer GUI with truly persistent navigation bar using grid"""
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
        
        # App icon (placeholder) - smaller
        icon_label = ttk.Label(self.header_frame, text="🏥", font=("Arial", 36))
        icon_label.pack()
        
        # Title
        title_label = ttk.Label(self.header_frame, text="Physiotherapy Clinic Assistant", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(5, 3))
        
        subtitle_label = ttk.Label(self.header_frame, text="Installation Wizard", 
                                  font=("Arial", 11))
        subtitle_label.pack()
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(self.header_frame, variable=self.progress_var, 
                                           maximum=self.total_steps)
        self.progress_bar.pack(fill="x", pady=(8, 0))
        
        # Progress label
        self.progress_label = ttk.Label(self.header_frame, text="Step 1 of 4: Welcome")
        self.progress_label.pack(pady=(3, 0))
        
        # Content frame (this is what gets cleared)
        self.content_frame = ttk.Frame(self.content_area)
        self.content_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        # Create persistent navigation bar (row 1, fixed position)
        self.create_navigation_bar()
        
        # Show first step
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
                                       command=self.cancel_installation)
        self.cancel_button.grid(row=0, column=3, padx=(5, 10), pady=8, sticky="e")
    
    def clear_content(self):
        """Clear the content frame (but preserve buttons frame)"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def update_progress(self, step: int, text: str):
        """Update progress bar and label"""
        self.progress_var.set(step + 1)
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
        # Update navigation buttons
        self.back_button.config(state="normal" if self.current_step > 0 else "disabled")
        
        if self.current_step == self.total_steps - 1:
            self.next_button.config(text="Install", command=self.start_installation)
        else:
            self.next_button.config(text="Next →", command=self.next_step)
        
        # Show appropriate step content
        if self.current_step == 0:
            self.show_welcome_step()
        elif self.current_step == 1:
            self.show_requirements_step()
        elif self.current_step == 2:
            self.show_instructions_step()
        elif self.current_step == 3:
            self.show_ready_step()
    
    def show_welcome_step(self):
        """Show welcome step"""
        self.clear_content()
        self.update_progress(self.current_step, f"Step {self.current_step + 1} of {self.total_steps}: Welcome")
        
        welcome_frame = ttk.Frame(self.content_frame)
        welcome_frame.pack(fill="both", expand=True)
        
        welcome_text = """
Welcome to the Physiotherapy Clinic Assistant installer!

This installer will guide you through:
• System requirements verification
• Application installation
• Initial setup and configuration

The installation process is completely automated and will take just a few minutes.
        """
        
        welcome_label = ttk.Label(welcome_frame, text=welcome_text, 
                                 font=("Arial", 10), justify="left")
        welcome_label.pack(pady=10)
    
    def show_requirements_step(self):
        """Show system requirements step"""
        self.clear_content()
        self.update_progress(self.current_step, f"Step {self.current_step + 1} of {self.total_steps}: System Requirements")
        
        requirements_frame = ttk.Frame(self.content_frame)
        requirements_frame.pack(fill="both", expand=True)
        
        # System requirements
        req_frame = ttk.LabelFrame(requirements_frame, text="System Requirements", padding="10")
        req_frame.pack(fill="x", pady=(0, 10))
        
        requirements_text = """
✓ macOS 10.15 (Catalina) or later
✓ 8GB RAM minimum (16GB recommended)
✓ 10GB free disk space
✓ Microphone access
✓ Internet connection (for initial setup)
        """
        
        requirements_label = ttk.Label(req_frame, text=requirements_text, 
                                      font=("Arial", 9), justify="left")
        requirements_label.pack()
        
        # Check button
        self.check_button = ttk.Button(requirements_frame, text="Check System Requirements", 
                                      command=self.check_system_requirements)
        self.check_button.pack(pady=(0, 10))
        
        # Results frame
        self.results_frame = ttk.LabelFrame(requirements_frame, text="Check Results", padding="8")
        self.results_frame.pack(fill="both", expand=True)
        
        # Results text
        self.results_text = tk.Text(self.results_frame, height=6, wrap="word")
        self.results_text.pack(fill="both", expand=True)
    
    def show_instructions_step(self):
        """Show installation instructions step"""
        self.clear_content()
        self.update_progress(self.current_step, f"Step {self.current_step + 1} of {self.total_steps}: Installation Instructions")
        
        instructions_frame = ttk.Frame(self.content_frame)
        instructions_frame.pack(fill="both", expand=True)
        
        instructions_text = f"""
Installation Process:

1. The {self.app_name} app will be placed on your Desktop
2. Drag the app to your Applications folder
3. The setup wizard will launch automatically
4. Follow the setup wizard to complete installation

This follows the standard Mac installation process.

The setup wizard will:
• Install Python dependencies
• Download AI models (~4.3GB)
• Test audio devices
• Configure the application
        """
        
        instructions_label = ttk.Label(instructions_frame, text=instructions_text, 
                                      font=("Arial", 10), justify="left")
        instructions_label.pack(pady=10)
    
    def show_ready_step(self):
        """Show ready to install step"""
        self.clear_content()
        self.update_progress(self.current_step, f"Step {self.current_step + 1} of {self.total_steps}: Ready to Install")
        
        ready_frame = ttk.Frame(self.content_frame)
        ready_frame.pack(fill="both", expand=True)
        
        ready_text = f"""
Ready to install {self.app_name}!

Click 'Install' to begin the installation process.

The installer will:
• Place the app on your Desktop
• Set up all required components
• Launch the setup wizard for configuration

This process typically takes 2-3 minutes.
        """
        
        ready_label = ttk.Label(ready_frame, text=ready_text, 
                               font=("Arial", 10), justify="left")
        ready_label.pack(pady=10)
    
    def start_installation(self):
        """Start the installation process"""
        # Check if app is already installed
        if self.app_path.exists():
            result = messagebox.askyesno("Application Already Installed", 
                                       f"{self.app_name} is already installed.\n\n"
                                       "Do you want to reinstall it?")
            if not result:
                return
        
        # Switch to installation progress view
        self.show_installation_progress()
        
        # Start installation in background thread
        installation_thread = threading.Thread(target=self.install_application, daemon=True)
        installation_thread.start()
    
    def show_installation_progress(self):
        """Show installation progress view"""
        self.clear_content()
        
        # Hide navigation bar during installation using grid_remove
        self.nav_frame.grid_remove()
        
        # Create progress frame
        progress_frame = ttk.LabelFrame(self.content_frame, text="Installation Progress", padding="15")
        progress_frame.pack(fill="both", expand=True)
        
        # Progress bar
        self.install_progress_var = tk.DoubleVar()
        self.install_progress_bar = ttk.Progressbar(progress_frame, variable=self.install_progress_var)
        self.install_progress_bar.pack(fill="x", pady=(0, 10))
        
        # Progress text
        self.install_progress_text = tk.Text(progress_frame, height=12, wrap="word")
        self.install_progress_text.pack(fill="both", expand=True)
        
        # Add cancel button
        cancel_frame = ttk.Frame(self.content_frame)
        cancel_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(cancel_frame, text="Cancel Installation", 
                  command=self.cancel_installation).pack(side="right")
    
    def install_application(self):
        """Install the application"""
        try:
            self.update_install_progress(0, "Starting installation...")
            
            # Step 1: Check system requirements
            self.update_install_progress(10, "Checking system requirements...")
            if not self.check_system_requirements_sync():
                self.installation_error("System requirements not met")
                return
            
            # Step 2: Create temporary directory
            self.update_install_progress(20, "Preparing installation...")
            self.temp_path.mkdir(exist_ok=True)
            
            # Step 3: Copy application bundle
            self.update_install_progress(30, "Installing application...")
            if not self.install_app_bundle():
                self.installation_error("Failed to install application bundle")
                return
            
            # Step 4: Set permissions
            self.update_install_progress(50, "Setting permissions...")
            self.set_permissions()
            
            # Step 5: Create launch script
            self.update_install_progress(70, "Configuring application...")
            self.create_launch_script()
            
            # Step 6: Finalize installation
            self.update_install_progress(90, "Finalizing installation...")
            self.finalize_installation()
            
            # Step 7: Launch setup wizard
            self.update_install_progress(100, "Installation complete!")
            self.installation_complete = True
            
            # Launch setup wizard
            self.root.after(1000, self.launch_setup_wizard)
            
        except Exception as e:
            self.installation_error(f"Installation failed: {e}")
    
    def check_system_requirements_sync(self) -> bool:
        """Synchronous system requirements check for installation"""
        try:
            import platform
            import shutil
            
            # Check macOS version
            mac_version = platform.mac_ver()[0]
            if mac_version < "10.15":
                self.update_install_progress(0, f"❌ macOS 10.15+ required, found {mac_version}")
                return False
            
            # Check available disk space
            free_space = shutil.disk_usage("/").free
            required_space = 10 * 1024 * 1024 * 1024  # 10GB
            
            if free_space < required_space:
                self.update_install_progress(0, f"❌ 10GB free space required, found {free_space / (1024**3):.1f}GB")
                return False
            
            self.update_install_progress(15, "✅ System requirements met")
            return True
            
        except Exception as e:
            self.update_install_progress(0, f"❌ Error checking requirements: {e}")
            return False
    
    def check_system_requirements(self):
        """Check if system meets requirements"""
        self.check_button.config(state="disabled")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Checking system requirements...\n")
        self.root.update()
        
        def check_thread():
            try:
                results = []
                
                # Check macOS version
                import platform
                mac_version = platform.mac_ver()[0]
                if mac_version >= "10.15":
                    results.append("✅ macOS version: " + mac_version)
                else:
                    results.append(f"❌ macOS 10.15+ required, found {mac_version}")
                
                # Check available disk space
                import shutil
                free_space = shutil.disk_usage("/").free
                required_space = 10 * 1024 * 1024 * 1024  # 10GB
                
                if free_space >= required_space:
                    results.append(f"✅ Free disk space: {free_space / (1024**3):.1f}GB")
                else:
                    results.append(f"❌ 10GB free space required, found {free_space / (1024**3):.1f}GB")
                
                # Check Python version
                python_version = sys.version.split()[0]
                results.append(f"✅ Python version: {python_version}")
                
                # Update UI in main thread
                self.root.after(0, self.update_system_check_results, results)
                
            except Exception as e:
                self.root.after(0, self.show_system_check_error, f"Error checking requirements: {e}")
        
        threading.Thread(target=check_thread, daemon=True).start()
    
    def update_system_check_results(self, results):
        """Update system check results in UI"""
        self.results_text.delete(1.0, tk.END)
        
        all_passed = True
        for result in results:
            self.results_text.insert(tk.END, result + "\n")
            if result.startswith("❌"):
                all_passed = False
        
        if all_passed:
            self.results_text.insert(tk.END, "\n✅ All system requirements met!")
        else:
            self.results_text.insert(tk.END, "\n❌ Some requirements not met. Please address the issues above.")
        
        self.check_button.config(state="normal")
    
    def show_system_check_error(self, error_msg):
        """Show system check error"""
        self.results_text.insert(tk.END, f"\n❌ {error_msg}\n")
        self.check_button.config(state="normal")
    
    def install_app_bundle(self) -> bool:
        """Place the application bundle on Desktop for user to drag"""
        try:
            # Find the app bundle - check multiple locations
            # 1. Try bundled resources directory (PyInstaller)
            if getattr(sys, '_MEIPASS', None):
                base_dir = Path(sys._MEIPASS)
            else:
                # 2. Try directory where installer is located
                base_dir = Path(__file__).parent.absolute()
            
            app_bundle = None
            
            # Look for .app bundle in base directory
            for item in base_dir.iterdir():
                if item.is_dir() and item.suffix == ".app" and self.app_name in item.name:
                    app_bundle = item
                    break
            
            # If not found, try current working directory as fallback
            if not app_bundle:
                for item in Path.cwd().iterdir():
                    if item.is_dir() and item.suffix == ".app" and self.app_name in item.name:
                        app_bundle = item
                        break
            
            if not app_bundle:
                self.update_progress(30, f"❌ Application bundle not found in {base_dir}")
                return False
            
            # Remove existing app from Desktop if it exists
            if self.drag_target_path.exists():
                shutil.rmtree(self.drag_target_path)
            
            # Copy to Desktop for user to drag
            shutil.copytree(app_bundle, self.drag_target_path)
            
            self.update_install_progress(40, "✅ Application placed on Desktop - ready to drag to Applications")
            return True
            
        except Exception as e:
            self.update_install_progress(30, f"❌ Installation error: {e}")
            return False
    
    def set_permissions(self):
        """Set proper permissions for the application"""
        try:
            # Make the app executable
            app_executable = self.drag_target_path / "Contents" / "MacOS" / self.app_name
            if app_executable.exists():
                os.chmod(app_executable, 0o755)
            
            self.update_install_progress(60, "✅ Permissions set")
            
        except Exception as e:
            self.update_install_progress(50, f"⚠️  Permission warning: {e}")
    
    def create_launch_script(self):
        """Create a launch script that runs the setup wizard"""
        try:
            # Create a launch script that will run the setup wizard
            launch_script = self.drag_target_path / "Contents" / "Resources" / "launch_setup.py"
            
            script_content = '''#!/usr/bin/env python3
"""
Launch script for Physiotherapy Clinic Assistant
Runs setup wizard on first launch
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Main launch function"""
    try:
        # Check if setup has been completed
        setup_file = Path.home() / ".physio_clinic_assistant" / "setup_complete.json"
        
        if not setup_file.exists():
            # First launch - run setup wizard
            setup_wizard_path = Path(__file__).parent / "setup_wizard.py"
            if setup_wizard_path.exists():
                subprocess.run([sys.executable, str(setup_wizard_path)])
            else:
                # Fallback to main application
                main_app_path = Path(__file__).parent / "main.py"
                if main_app_path.exists():
                    subprocess.run([sys.executable, str(main_app_path)])
        else:
            # Setup completed - launch main application
            main_app_path = Path(__file__).parent / "main.py"
            if main_app_path.exists():
                subprocess.run([sys.executable, str(main_app_path)])
                
    except Exception as e:
        print(f"Launch error: {e}")
        # Fallback to main application
        try:
            main_app_path = Path(__file__).parent / "main.py"
            if main_app_path.exists():
                subprocess.run([sys.executable, str(main_app_path)])
        except:
            pass

if __name__ == "__main__":
    main()
'''
            
            with open(launch_script, 'w') as f:
                f.write(script_content)
            
            os.chmod(launch_script, 0o755)
            
            self.update_install_progress(80, "✅ Launch script created")
            
        except Exception as e:
            self.update_install_progress(70, f"⚠️  Launch script warning: {e}")
    
    def finalize_installation(self):
        """Finalize the installation"""
        try:
            # Create application support directory
            app_support = Path.home() / "Library" / "Application Support" / self.app_name
            app_support.mkdir(parents=True, exist_ok=True)
            
            # Create configuration directory
            config_dir = app_support / "config"
            config_dir.mkdir(exist_ok=True)
            
            # Create data directory
            data_dir = app_support / "data"
            data_dir.mkdir(exist_ok=True)
            
            # Create models directory
            models_dir = app_support / "models"
            models_dir.mkdir(exist_ok=True)
            
            # Create recordings directory
            recordings_dir = app_support / "recordings"
            recordings_dir.mkdir(exist_ok=True)
            
            # Create transcripts directory
            transcripts_dir = app_support / "transcripts"
            transcripts_dir.mkdir(exist_ok=True)
            
            # Create output forms directory
            output_forms_dir = app_support / "output_forms"
            output_forms_dir.mkdir(exist_ok=True)
            
            # Clean up temporary directory
            if self.temp_path.exists():
                shutil.rmtree(self.temp_path)
            
            self.update_install_progress(90, "✅ Installation finalized")
            
        except Exception as e:
            self.update_install_progress(90, f"⚠️  Finalization warning: {e}")
    
    def launch_setup_wizard(self):
        """Launch the setup wizard"""
        try:
            if self.setup_wizard_launched:
                return
            
            self.setup_wizard_launched = True
            
            # Update progress
            self.install_progress_text.insert(tk.END, "\n🚀 Launching setup wizard...\n")
            self.install_progress_text.see(tk.END)
            self.root.update()
            
            # Launch setup wizard
            setup_wizard_path = self.drag_target_path / "Contents" / "Resources" / "setup_wizard.py"
            if setup_wizard_path.exists():
                subprocess.Popen([sys.executable, str(setup_wizard_path)])
            else:
                # Fallback to main application
                main_app_path = self.drag_target_path / "Contents" / "Resources" / "main.py"
                if main_app_path.exists():
                    subprocess.Popen([sys.executable, str(main_app_path)])
            
            # Show completion message
            self.install_progress_text.insert(tk.END, "\n✅ App placed on Desktop!\n")
            self.install_progress_text.insert(tk.END, f"Now drag {self.app_name}.app to your Applications folder.\n")
            self.install_progress_text.insert(tk.END, "The setup wizard will launch automatically when you first run the app.\n")
            self.install_progress_text.see(tk.END)
            
            # Update button
            self.install_button.config(text="App Ready on Desktop", state="disabled")
            
            # Add close button
            close_button = ttk.Button(self.progress_frame, text="Close Installer", 
                                    command=self.root.quit)
            close_button.pack(pady=(10, 0))
            
        except Exception as e:
            self.installation_error(f"Failed to launch setup wizard: {e}")
    
    def update_install_progress(self, value: int, message: str):
        """Update installation progress bar and text"""
        self.install_progress_var.set(value)
        self.install_progress_text.insert(tk.END, f"{message}\n")
        self.install_progress_text.see(tk.END)
        self.root.update()
    
    def installation_error(self, error_msg: str):
        """Handle installation error"""
        self.install_progress_text.insert(tk.END, f"\n❌ {error_msg}\n")
        self.install_progress_text.see(tk.END)
        
        # Add retry button
        retry_frame = ttk.Frame(self.content_frame)
        retry_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(retry_frame, text="Retry Installation", 
                  command=self.retry_installation).pack(side="right")
    
    def retry_installation(self):
        """Retry the installation"""
        # Reset state
        self.installation_complete = False
        self.setup_wizard_launched = False
        
        # Go back to ready step
        self.current_step = 3
        self.show_ready_step()
        
        # Show navigation bar again using grid
        self.nav_frame.grid(row=1, column=0, sticky="ew", padx=0, pady=0)
    
    def cancel_installation(self):
        """Cancel the installation"""
        if messagebox.askyesno("Cancel Installation", 
                              "Are you sure you want to cancel the installation?"):
            self.root.quit()
    
    def run(self):
        """Run the installer"""
        self.root.mainloop()


def main():
    """Main function"""
    try:
        installer = MacInstaller()
        installer.run()
    except Exception as e:
        messagebox.showerror("Installer Error", f"Error starting installer: {e}")


if __name__ == "__main__":
    main()
