#!/usr/bin/env python3
"""
Physiotherapy Clinic Application
Main entry point for the desktop application
"""

# Set OpenMP environment variables to prevent runtime conflicts
import os
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import time
from datetime import datetime
import json
import subprocess
import sys
import shutil
import atexit
import signal
from typing import Dict, Any

# Import multiprocessing for cleanup
import multiprocessing
import multiprocessing.resource_tracker

from pvrecorder_recorder import PvRecorderAudioRecorder
from transcriber import Transcriber
from wsib_data_extractor import WSIBDataExtractor
from wsib_form_filler import WSIBFormFiller
from model_downloader import ModelDownloader

from database_manager import DatabaseManager
from encrypted_database_manager import EncryptedDatabaseManager
from audited_database_manager import AuditedDatabaseManager
from encryption_gui import EncryptionManagementGUI
from settings_gui import SettingsGUI
from appointment_history_gui import AppointmentHistoryGUI
from cleanup_manager import CleanupManager, CleanupGUI
from data_management_gui import DataManagementGUI
from background_processor import BackgroundProcessor
from background_processor_gui import BackgroundProcessorGUI
from model_manager import model_manager
from stored_data_editor import StoredFormFieldsEditor

# Import authentication components
from auth import AuthManager, SubscriptionChecker, show_login_dialog
from auth.network_manager import NetworkManager, OfflineIndicator


def cleanup_multiprocessing_resources():
    """Clean up multiprocessing resources to prevent semaphore leaks"""
    try:
        print("🧹 Cleaning up multiprocessing resources...")
        
        # Import multiprocessing here to avoid import issues
        import multiprocessing
        import multiprocessing.resource_tracker
        
        # Clean up any remaining multiprocessing resources
        if hasattr(multiprocessing.resource_tracker, '_CLEANUP_CALLS'):
            for cleanup_call in multiprocessing.resource_tracker._CLEANUP_CALLS:
                try:
                    cleanup_call()
                except:
                    pass
        
        # Force cleanup of resource tracker
        if hasattr(multiprocessing.resource_tracker, '_REGISTRY'):
            multiprocessing.resource_tracker._REGISTRY.clear()
        
        # Additional cleanup for macOS
        if sys.platform == 'darwin':
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clean up any remaining semaphores
            try:
                import multiprocessing.synchronize
                # This is a more aggressive cleanup for macOS
                for obj in gc.get_objects():
                    if hasattr(obj, '_semlock'):
                        try:
                            del obj
                        except:
                            pass
            except:
                pass
                
        print("✅ Multiprocessing cleanup completed")
            
    except Exception as e:
        print(f"Warning: Error during multiprocessing cleanup: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    print(f"🔄 Received signal {signum}, cleaning up...")
    cleanup_multiprocessing_resources()
    
    # Force exit to prevent hanging
    os._exit(0)


# Register cleanup functions
atexit.register(cleanup_multiprocessing_resources)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Additional signal handlers for macOS
if sys.platform == 'darwin':
    signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGUSR2, signal_handler)

# Set multiprocessing start method to prevent issues
if sys.platform == 'darwin':
    multiprocessing.set_start_method('spawn', force=True)


class PhysioApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Form Filler")
        self.root.geometry("1000x800")
        self.root.minsize(900, 700)
        
        # Set application icon and name for macOS
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "static", "logo.png")
            if os.path.exists(icon_path):
                # Load and set the icon
                icon_image = tk.PhotoImage(file=icon_path)
                self.root.iconphoto(True, icon_image)
                # Keep a reference to prevent garbage collection
                self.root.icon_image = icon_image
                print("✅ Application icon set successfully")
            else:
                print(f"⚠️  Icon file not found at: {icon_path}")
        except Exception as e:
            print(f"⚠️  Could not set application icon: {e}")
        
        # Set macOS application name in menu bar
        if sys.platform == 'darwin':
            try:
                # This sets the application name in the macOS menu bar
                self.root.createcommand('tk::mac::ReopenApplication', lambda: self.root.lift())
                self.root.createcommand('tk::mac::Quit', lambda: self.root.quit())
                
                # Set the application name using tkinter's macOS-specific method
                self.root.tk.call('tk', 'appname', 'Form Filler')
                print("✅ macOS application name set to 'Form Filler'")
            except Exception as e:
                print(f"⚠️  Could not set macOS application name: {e}")
        
        # Initialize authentication components
        self.auth_manager = AuthManager()
        self.subscription_checker = SubscriptionChecker(self.auth_manager)
        self.network_manager = NetworkManager(self.auth_manager, self.subscription_checker)
        self.offline_indicator = OfflineIndicator(self.network_manager)
        
        # Initialize database and managers with audit logging
        self.db_manager = AuditedDatabaseManager()
        self.cleanup_manager = CleanupManager(self.db_manager)
        
        # Initialize background processor
        self.background_processor = BackgroundProcessor(self.db_manager, self.auth_manager, max_workers=2)
        
        # Initialize components
        self.recorder = PvRecorderAudioRecorder()
        self.transcriber = Transcriber()
        # Model selection - can be changed via settings
        self.current_model_type = "qwen3-4b"  # Default to 4B model for better accuracy
        self.wsib_data_extractor = WSIBDataExtractor(model_type=self.current_model_type)
        self.wsib_form_filler = WSIBFormFiller()
        self.model_downloader = ModelDownloader()

        
        # Initialize GUI components
        try:
            self.settings_gui = SettingsGUI(self.root, self.db_manager)
            print("✅ Settings GUI initialized")
        except Exception as e:
            print(f"❌ Error initializing Settings GUI: {e}")
            self.settings_gui = None
            
        try:
            self.appointment_history_gui = AppointmentHistoryGUI(self.root, self.db_manager, self.auth_manager)
            print("✅ Appointment History GUI initialized")
        except Exception as e:
            print(f"❌ Error initializing Appointment History GUI: {e}")
            self.appointment_history_gui = None
            
        try:
            self.cleanup_gui = CleanupGUI(self.root, self.cleanup_manager)
            print("✅ Cleanup GUI initialized")
        except Exception as e:
            print(f"❌ Error initializing Cleanup GUI: {e}")
            self.cleanup_gui = None
            
        try:
            self.data_management_gui = DataManagementGUI(self.root, self.db_manager)
            print("✅ Data Management GUI initialized")
        except Exception as e:
            print(f"❌ Error initializing Data Management GUI: {e}")
            self.data_management_gui = None
            
        try:
            self.encryption_gui = EncryptionManagementGUI(self.root, self.db_manager)
            print("✅ Encryption Management GUI initialized")
        except Exception as e:
            print(f"❌ Error initializing Encryption Management GUI: {e}")
            self.encryption_gui = None
            
        try:
            self.stored_form_fields_editor = StoredFormFieldsEditor(self.root)
            print("✅ Stored Form Fields Editor initialized")
        except Exception as e:
            print(f"❌ Error initializing Stored Form Fields Editor: {e}")
            self.stored_form_fields_editor = None
        
        # State variables
        self.is_recording = False
        self.is_processing = False
        self.current_appointment_id = None
        
        # Track background threads for cleanup
        self.background_threads = []
        self.forms_to_fill = {'wsib': False, 'ocf18': False, 'ocf23': False}

        
        # Create directories
        self.create_directories()
        
        # Start automatic cleanup
        self.cleanup_manager.start_automatic_cleanup()
        
        # Start network monitoring
        self.start_network_monitoring()
        
        # Setup GUI
        self.setup_gui()
        
        # Bind cleanup on window close
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Register cleanup on exit
        atexit.register(self.cleanup_on_exit)
    
    def cleanup_on_exit(self):
        """Cleanup resources when application exits"""
        try:
            print("🧹 Starting application cleanup...")
            
            # Stop background threads
            if hasattr(self, 'cleanup_manager'):
                self.cleanup_manager.stop_automatic_cleanup()
                print("✅ Cleanup manager stopped")
                
            if hasattr(self, 'background_processor'):
                self.background_processor.cleanup()
                print("✅ Background processor cleaned up")
                
            # Clean up shared ModelManager
            model_manager.cleanup()
            print("✅ Shared ModelManager cleaned up")
            
            # Clean up network manager
            if hasattr(self, 'network_manager'):
                self.network_manager.cleanup()
                print("✅ Network manager cleaned up")
                
            if hasattr(self, 'wsib_data_extractor'):
                self.wsib_data_extractor.cleanup()
                print("✅ WSIB data extractor cleaned up")
                
            # Stop any active recording
            if hasattr(self, 'is_recording') and self.is_recording:
                try:
                    self.stop_recording()
                    print("✅ Recording stopped")
                except:
                    pass
                    
            # Clean up model resources
            if hasattr(self, 'transcriber'):
                self.transcriber.cleanup()
                print("✅ Transcriber cleaned up")
            
            # Clean up background threads
            self.cleanup_background_threads()
                
            print("✅ Application cleanup completed")
            
        except Exception as e:
            print(f"Error during cleanup: {e}")
    
    def cleanup_background_threads(self):
        """Clean up all background threads"""
        try:
            print("🧹 Cleaning up background threads...")
            
            # Wait for threads to finish (with timeout)
            for thread in self.background_threads:
                if thread.is_alive():
                    print(f"🔄 Waiting for thread {thread.name} to finish...")
                    thread.join(timeout=2.0)  # Wait up to 2 seconds
                    
                    if thread.is_alive():
                        print(f"⚠️  Thread {thread.name} did not finish, marking as daemon")
                        thread.daemon = True
            
            # Clear the list
            self.background_threads.clear()
            print("✅ Background threads cleaned up")
            
        except Exception as e:
            print(f"Warning: Error cleaning up background threads: {e}")
    
    def load_today_appointments(self):
        """Load and display today's appointments"""
        try:
            # Clear existing items
            for item in self.today_tree.get_children():
                self.today_tree.delete(item)
            
            # Get today's date
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Get current user ID for audit logging
            user_id = self.auth_manager.get_user_id() or "system"
            
            # Get appointments for today
            appointments = self.db_manager.get_appointments_by_date(today, user_id)
            
            if not appointments:
                # Show "no appointments" message
                self.today_tree.insert('', 'end', values=(
                    "No appointments today",
                    "",
                    ""
                ))
            else:
                for appointment in appointments:
                    # Get processing status
                    status = self.get_appointment_status(appointment['appointment_id'])
                    
                    # Insert into treeview
                    self.today_tree.insert('', 'end', values=(
                        appointment['patient_name'],
                        appointment.get('appointment_type', 'Initial Assessment'),
                        status
                    ), tags=(appointment['appointment_id'],))
            
            # Disable action buttons when no appointment is selected
            self.disable_action_buttons()
            
        except Exception as e:
            print(f"Warning: Could not load today's appointments: {e}")
    
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
    
    def view_appointment_folder(self, appointment_id: int):
        """Open the appointment folder"""
        try:
            user_id = self.auth_manager.get_required_user_id()
            appointment = self.db_manager.get_appointment(appointment_id, user_id)
            if appointment and 'folder_path' in appointment:
                folder_path = appointment['folder_path']
                if os.path.exists(folder_path):
                    if sys.platform == "darwin":  # macOS
                        subprocess.run(["open", folder_path])
                    elif sys.platform == "win32":  # Windows
                        subprocess.run(["explorer", folder_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", folder_path])
                else:
                    messagebox.showwarning("Warning", f"Folder not found: {folder_path}")
            else:
                messagebox.showwarning("Warning", "Appointment not found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open folder: {str(e)}")
    
    def view_appointment_transcript(self, appointment_id: int):
        """View the appointment transcript"""
        try:
            user_id = self.auth_manager.get_required_user_id()
            appointment = self.db_manager.get_appointment(appointment_id, user_id)
            if appointment and 'folder_path' in appointment:
                transcript_path = os.path.join(appointment['folder_path'], "transcript.txt")
                if os.path.exists(transcript_path):
                    if sys.platform == "darwin":  # macOS
                        subprocess.run(["open", transcript_path])
                    elif sys.platform == "win32":  # Windows
                        subprocess.run(["notepad", transcript_path])
                    else:  # Linux
                        subprocess.run(["xdg-open", transcript_path])
                else:
                    messagebox.showwarning("Warning", "Transcript not found")
            else:
                messagebox.showwarning("Warning", "Appointment not found")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open transcript: {str(e)}")
    
    def on_appointment_select(self, event):
        """Handle appointment selection in the today's appointments table"""
        try:
            selection = self.today_tree.selection()
            if selection:
                # Get the selected appointment ID
                item = selection[0]
                tags = self.today_tree.item(item, "tags")
                
                # Check if tags exist and are not empty
                if tags and len(tags) > 0:
                    appointment_id = tags[0]
                    
                    # Enable action buttons
                    self.enable_action_buttons()
                    
                    # Store the selected appointment ID
                    self.selected_appointment_id = appointment_id
                else:
                    # No valid appointment ID (e.g., "No appointments today" item)
                    self.disable_action_buttons()
                    self.selected_appointment_id = None
            else:
                # No selection, disable buttons
                self.disable_action_buttons()
                self.selected_appointment_id = None
                
        except Exception as e:
            print(f"Error handling appointment selection: {e}")
            self.disable_action_buttons()
    
    def enable_action_buttons(self):
        """Enable action buttons for selected appointment"""
        self.view_folder_btn.config(state="normal")
        self.view_transcript_btn.config(state="normal")
        self.view_forms_btn.config(state="normal")
    
    def disable_action_buttons(self):
        """Disable action buttons when no appointment is selected"""
        self.view_folder_btn.config(state="disabled")
        self.view_transcript_btn.config(state="disabled")
        self.view_forms_btn.config(state="disabled")
    
    def view_selected_appointment_folder(self):
        """Open the selected appointment folder"""
        if hasattr(self, 'selected_appointment_id') and self.selected_appointment_id:
            self.view_appointment_folder(self.selected_appointment_id)
        else:
            messagebox.showwarning("Warning", "Please select an appointment first")
    
    def view_selected_appointment_transcript(self):
        """View the selected appointment transcript"""
        if hasattr(self, 'selected_appointment_id') and self.selected_appointment_id:
            self.view_appointment_transcript(self.selected_appointment_id)
        else:
            messagebox.showwarning("Warning", "Please select an appointment first")
    
    def view_selected_appointment_forms(self):
        """View the selected appointment forms"""
        if hasattr(self, 'selected_appointment_id') and self.selected_appointment_id:
            try:
                user_id = self.auth_manager.get_required_user_id()
                appointment = self.db_manager.get_appointment(self.selected_appointment_id, user_id)
                if appointment and 'folder_path' in appointment:
                    folder_path = appointment['folder_path']
                    
                    # Check for available forms
                    forms_found = []
                    
                    # Check for WSIB form
                    wsib_path = os.path.join(folder_path, "wsib_form.pdf")
                    if os.path.exists(wsib_path):
                        forms_found.append(("WSIB FAF", wsib_path))
                    
                    # Check for OCF-18 form
                    ocf18_path = os.path.join(folder_path, "ocf18_form.pdf")
                    if os.path.exists(ocf18_path):
                        forms_found.append(("FSRA OCF-18", ocf18_path))
                    
                    # Check for OCF-23 form
                    ocf23_path = os.path.join(folder_path, "ocf23_form.pdf")
                    if os.path.exists(ocf23_path):
                        forms_found.append(("FSRA OCF-23", ocf23_path))
                    
                    if forms_found:
                        # Open the first available form
                        form_name, form_path = forms_found[0]
                        if sys.platform == "darwin":  # macOS
                            subprocess.run(["open", form_path])
                        elif sys.platform == "win32":  # Windows
                            subprocess.run(["start", form_path], shell=True)
                        else:  # Linux
                            subprocess.run(["xdg-open", form_path])
                    else:
                        messagebox.showinfo("Info", "No forms found for this appointment")
                else:
                    messagebox.showwarning("Warning", "Appointment not found")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to open forms: {str(e)}")
        else:
            messagebox.showwarning("Warning", "Please select an appointment first")
    
    def on_closing(self):
        """Handle application shutdown"""
        try:
            print("🔄 Application shutdown initiated...")
            
            # Stop recording if active
            if self.is_recording:
                print("🛑 Stopping active recording...")
                self.stop_recording()
            
            # Clean up model resources
            try:
                print("🧹 Cleaning up model resources...")
                self.transcriber.cleanup()
                self.wsib_data_extractor.cleanup()
                print("✅ Model resources cleaned up")
            except Exception as e:
                print(f"Warning: Error cleaning up models: {e}")
            
            # Clean up multiprocessing resources
            print("🧹 Cleaning up multiprocessing resources...")
            cleanup_multiprocessing_resources()
            
            # Force final cleanup
            try:
                import gc
                gc.collect()
                print("✅ Final garbage collection completed")
            except:
                pass
            
            print("✅ Shutdown cleanup completed")
            
            # Destroy the window
            self.root.destroy()
            
        except Exception as e:
            print(f"Error during shutdown: {e}")
            self.root.destroy()
    
    def create_directories(self):
        """Create necessary directories if they don't exist"""
        # Import path helper
        try:
            from app_paths import get_writable_path, get_log_path, get_temp_path
            
            # Create writable directories in proper locations
            # config/ is read-only from bundle, don't create
            get_writable_path("data")  # ~/Library/Application Support/PhysioClinicAssistant/data
            get_writable_path("models")  # ~/Library/Application Support/PhysioClinicAssistant/models
            get_log_path()  # ~/Library/Logs/PhysioClinicAssistant
            get_temp_path()  # /tmp/PhysioClinicAssistant
            
            print("✅ Created necessary writable directories in proper locations")
        except Exception as e:
            print(f"Warning: Could not create directories: {e}")
            # Fallback for development
            directories = ['data', 'models', 'logs', 'temp']
            for directory in directories:
                try:
                    os.makedirs(directory, exist_ok=True)
                except OSError:
                    pass  # Ignore if we can't create (bundled app)
    
    def check_models(self):
        """Check if required models are downloaded"""
        try:
            print("Checking models...")
            self.root.update()
            
            if not self.model_downloader.check_models():
                response = messagebox.askyesno(
                    "Models Not Found", 
                    "Required models are not downloaded. Download now? (This may take several minutes)"
                )
                if response:
                    self.download_models()
                else:
                    messagebox.showwarning(
                        "Warning", 
                        "Models are required for transcription and processing. Please download them later."
                    )
            else:
                print("Models ready")
        except Exception as e:
            messagebox.showerror("Error", f"Error checking models: {str(e)}")
            print("Error checking models")
    
    def download_models(self):
        """Download required models"""
        try:
            print("Downloading models...")
            self.root.update()
            
            # Run download in separate thread
            download_thread = threading.Thread(target=self._download_models_thread)
            download_thread.daemon = True
            download_thread.start()
            
            # Track thread for cleanup
            self.background_threads.append(download_thread)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error starting model download: {str(e)}")
            print("Error downloading models")
    
    def _download_models_thread(self):
        """Download models in background thread"""
        try:
            self.model_downloader.download_all_models()
            self.root.after(0, lambda: print("Models downloaded successfully"))
            self.root.after(0, lambda: messagebox.showinfo("Success", "Models downloaded successfully!"))
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Error", f"Error downloading models: {str(e)}"))
            self.root.after(0, lambda: print("Error downloading models"))
    
    def refresh_audio_devices(self):
        """Refresh the list of available audio devices"""
        try:
            # Check if GUI components exist
            if not hasattr(self, 'device_combo') or not hasattr(self, 'device_var'):
                print("⚠️  GUI components not ready, skipping audio device refresh")
                return
            
            devices = self.recorder.get_available_devices()
            device_names = [device for device in devices]
            
            # Update the combobox
            self.device_combo['values'] = device_names
            
            # Set default device (first available)
            if device_names and not self.device_var.get():
                self.device_var.set(device_names[0])
                print(f"✅ Selected default audio device: {device_names[0]}")
            
            print(f"Found {len(device_names)} audio devices:")
            for i, device in enumerate(device_names):
                print(f"  {i}: {device}")
                
        except Exception as e:
            print(f"Warning: Could not refresh audio devices: {e}")
            if hasattr(self, 'device_combo') and hasattr(self, 'device_var'):
                self.device_combo['values'] = ["Default Device"]
                self.device_var.set("Default Device")
    
    def get_selected_device_index(self):
        """Get the index of the selected audio device"""
        try:
            devices = self.recorder.get_available_devices()
            selected_device = self.device_var.get()
            
            for i, device in enumerate(devices):
                if device == selected_device:
                    return i
            
            # If device not found, return default (-1)
            return -1
            
        except Exception as e:
            print(f"Warning: Could not get device index: {e}")
            return -1
    
    def setup_gui(self):
        """Setup the main GUI"""
        # Create menu bar
        self.create_menu_bar()
        
        # Create main canvas and scrollbar
        self.main_canvas = tk.Canvas(self.root)
        self.main_scrollbar = ttk.Scrollbar(self.root, orient="vertical", command=self.main_canvas.yview)
        self.scrollable_main_frame = ttk.Frame(self.main_canvas)
        
        self.scrollable_main_frame.bind(
            "<Configure>",
            lambda e: self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        )
        
        self.main_canvas.create_window((0, 0), window=self.scrollable_main_frame, anchor="nw")
        self.main_canvas.configure(yscrollcommand=self.main_scrollbar.set)
        
        # Pack canvas and scrollbar
        self.main_canvas.grid(row=0, column=0, sticky="nsew")
        self.main_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind mousewheel to canvas
        self.main_canvas.bind("<MouseWheel>", self._on_main_mousewheel)
        
        # Main frame
        main_frame = ttk.Frame(self.scrollable_main_frame, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Title
        title_label = ttk.Label(main_frame, text="Form Filler", 
                               font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=3, pady=(0, 20))
        
        # Appointment Information
        info_frame = ttk.LabelFrame(main_frame, text="Appointment Information", padding="10")
        info_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Patient name
        ttk.Label(info_frame, text="Patient Name:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.patient_name_var = tk.StringVar()
        self.patient_name_entry = ttk.Entry(info_frame, textvariable=self.patient_name_var, width=30)
        self.patient_name_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 20))
        
        # Appointment type
        ttk.Label(info_frame, text="Type:").grid(row=0, column=2, sticky=tk.W, padx=(0, 10))
        self.appointment_type_var = tk.StringVar(value="Initial Assessment")
        self.appointment_type_combo = ttk.Combobox(info_frame, textvariable=self.appointment_type_var, 
                                                  values=["Initial Assessment", "Follow-Up Treatment", "Follow-Up Assessment", "Other"], width=20)
        self.appointment_type_combo.grid(row=0, column=3, sticky=(tk.W, tk.E))
        
        # Model Selection
        model_frame = ttk.LabelFrame(info_frame, text="AI Model Selection", padding="5")
        model_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        
        ttk.Label(model_frame, text="Data Extraction Model:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.model_type_var = tk.StringVar(value="4B-Larger Model")
        self.model_type_combo = ttk.Combobox(model_frame, textvariable=self.model_type_var, 
                                           values=["4B-Larger Model", "1.7B-Smaller Model"], state="readonly", width=18)
        self.model_type_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        self.model_type_combo.bind("<<ComboboxSelected>>", self.on_model_type_changed)
        
        # Model info label
        self.model_info_label = ttk.Label(model_frame, text="4B: Higher accuracy, ~4GB RAM | 1.7B: Faster, ~2GB RAM", 
                                        font=("Arial", 8), foreground="gray")
        self.model_info_label.grid(row=0, column=2, sticky=tk.W, padx=(10, 0))
        
        # Form Selection
        form_frame = ttk.LabelFrame(info_frame, text="Forms to Generate", padding="5")
        form_frame.grid(row=2, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(10, 0))
        
        self.wsib_form_var = tk.BooleanVar(value=False)
        self.ocf18_form_var = tk.BooleanVar(value=False)
        self.ocf23_form_var = tk.BooleanVar(value=False)
        
        ttk.Checkbutton(form_frame, text="WSIB FAF", variable=self.wsib_form_var).grid(row=0, column=0, padx=(0, 20))
        ttk.Checkbutton(form_frame, text="FSRA OCF-18", variable=self.ocf18_form_var).grid(row=0, column=1, padx=(0, 20))
        ttk.Checkbutton(form_frame, text="FSRA OCF-23", variable=self.ocf23_form_var).grid(row=0, column=2)
        

        
        # Input Methods
        input_frame = ttk.LabelFrame(main_frame, text="Input Methods", padding="10")
        input_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Recording Controls
        recording_frame = ttk.LabelFrame(input_frame, text="Live Recording", padding="10")
        recording_frame.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Device selection
        device_frame = ttk.Frame(recording_frame)
        device_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(device_frame, text="Audio Device:").grid(row=0, column=0, sticky=tk.W, padx=(0, 10))
        self.device_var = tk.StringVar()
        self.device_combo = ttk.Combobox(device_frame, textvariable=self.device_var, width=40, state="readonly")
        self.device_combo.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 10))
        
        self.refresh_devices_button = ttk.Button(device_frame, text="Refresh", 
                                               command=self.refresh_audio_devices)
        self.refresh_devices_button.grid(row=0, column=2)
        
        # Configure device frame grid weights
        device_frame.columnconfigure(1, weight=1)
        
        # Recording buttons
        button_frame = ttk.Frame(recording_frame)
        button_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E))
        
        self.record_button = ttk.Button(button_frame, text="Start Recording", 
                                       command=self.start_recording)
        self.record_button.grid(row=0, column=0, padx=(0, 10))
        
        self.stop_button = ttk.Button(button_frame, text="Stop Recording", 
                                     command=self.stop_recording, state="disabled")
        self.stop_button.grid(row=0, column=1, padx=(0, 10))
        
        self.timer_label = ttk.Label(button_frame, text="00:00")
        self.timer_label.grid(row=0, column=2, padx=(20, 0))
        
        # Configure recording frame grid weights
        recording_frame.columnconfigure(0, weight=1)
        
        # File Upload Controls
        upload_frame = ttk.LabelFrame(input_frame, text="Upload Audio File", padding="10")
        upload_frame.grid(row=0, column=1, sticky=(tk.W, tk.E))
        
        self.upload_button = ttk.Button(upload_frame, text="Upload Audio File", 
                                       command=self.upload_audio_file)
        self.upload_button.grid(row=0, column=0, padx=(0, 10))
        
        self.upload_label = ttk.Label(upload_frame, text="No file selected")
        self.upload_label.grid(row=0, column=1, padx=(10, 0))
        
        # Configure grid weights for input frame
        input_frame.columnconfigure(0, weight=1)
        input_frame.columnconfigure(1, weight=1)
        
        # Today's Appointments
        today_frame = ttk.LabelFrame(main_frame, text="Today's Appointments", padding="10")
        today_frame.grid(row=3, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Header frame (empty now, just for spacing)
        today_header = ttk.Frame(today_frame)
        today_header.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Create treeview for today's appointments
        self.today_tree = ttk.Treeview(today_frame, columns=("Patient", "Type", "Status"), show="headings", height=4)
        
        # Configure columns
        self.today_tree.heading("Patient", text="Patient Name")
        self.today_tree.heading("Type", text="Type")
        self.today_tree.heading("Status", text="Status")
        
        # Set column widths
        self.today_tree.column("Patient", width=200)
        self.today_tree.column("Type", width=150)
        self.today_tree.column("Status", width=120)
        
        # Add scrollbar
        today_scrollbar = ttk.Scrollbar(today_frame, orient="vertical", command=self.today_tree.yview)
        self.today_tree.configure(yscrollcommand=today_scrollbar.set)
        
        # Grid the treeview and scrollbar
        self.today_tree.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        today_scrollbar.grid(row=1, column=1, sticky=(tk.N, tk.S))
        
        # Configure grid weights
        today_frame.columnconfigure(0, weight=1)
        today_frame.rowconfigure(1, weight=1)
        
        # Actions frame below the table
        actions_frame = ttk.LabelFrame(today_frame, text="Appointment Actions", padding="10")
        actions_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        
        # Action buttons (initially disabled)
        self.view_folder_btn = ttk.Button(actions_frame, text="Open Appointment Folder", 
                                        command=self.view_selected_appointment_folder, state="disabled")
        self.view_folder_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.view_transcript_btn = ttk.Button(actions_frame, text="View Transcript", 
                                            command=self.view_selected_appointment_transcript, state="disabled")
        self.view_transcript_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.view_forms_btn = ttk.Button(actions_frame, text="View Forms", 
                                       command=self.view_selected_appointment_forms, state="disabled")
        self.view_forms_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Refresh button
        ttk.Button(actions_frame, text="Refresh", command=self.load_today_appointments).pack(side=tk.RIGHT)
        
        # Bind selection event
        self.today_tree.bind('<<TreeviewSelect>>', self.on_appointment_select)
        
        

        
        # Add management buttons for easy access
        management_frame = ttk.LabelFrame(main_frame, text="Management Tools", padding="10")
        management_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 20))
        
        # Management buttons in one row
        ttk.Button(management_frame, text="Settings", command=self.show_settings).grid(row=0, column=0, padx=(0, 10), pady=2)
        ttk.Button(management_frame, text="Appointment History", command=self.show_appointment_history).grid(row=0, column=1, padx=(0, 10), pady=2)
        ttk.Button(management_frame, text="File Cleanup", command=self.show_cleanup_manager).grid(row=0, column=2, padx=(0, 10), pady=2)
        ttk.Button(management_frame, text="Data Management", command=self.show_data_management).grid(row=0, column=3, padx=(0, 10), pady=2)
        ttk.Button(management_frame, text="Stored Form Fields", command=self.show_stored_form_fields_editor).grid(row=0, column=4, padx=(0, 10), pady=2)
        
        # Background Processor Monitor
        if hasattr(self, 'background_processor_gui') and self.background_processor_gui:
            processor_frame = ttk.LabelFrame(main_frame, text="Background Processing", padding="5")
            processor_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 20))
            
            # Add the background processor GUI to this frame
            self.background_processor_gui.main_frame.pack_forget()  # Remove from its original parent
            self.background_processor_gui.main_frame.master = processor_frame  # Change parent
            self.background_processor_gui.main_frame.pack(fill="both", expand=True)
        
        # Configure grid weights
        main_frame.rowconfigure(4, weight=1)
        if hasattr(self, 'background_processor_gui') and self.background_processor_gui:
            main_frame.rowconfigure(7, weight=1)
        
        # Initialize audio devices after GUI is set up
        self.refresh_audio_devices()
        
        # Load today's appointments
        self.load_today_appointments()
    
    def create_menu_bar(self):
        """Create the application menu bar"""
        try:
            menubar = tk.Menu(self.root)
            self.root.config(menu=menubar)
            print("✅ Menu bar created successfully")
            
            # macOS-specific menu bar fixes
            if sys.platform == 'darwin':
                # Force menu bar to be visible
                self.root.update_idletasks()
                self.root.update()
                
                # Add a small delay to ensure menu bar appears
                self.root.after(100, self._ensure_menu_visible)
            
            # File menu
            file_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="File", menu=file_menu)

            file_menu.add_separator()
            file_menu.add_command(label="Exit", command=self.root.quit)
            
            # Add a visible menu item to help with debugging
            file_menu.add_separator()
            
            # Account menu
            account_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Account", menu=account_menu)
            account_menu.add_command(label="Subscription Status", command=self.show_subscription_status)
            account_menu.add_command(label="Account Settings", command=self.show_account_settings)
            account_menu.add_separator()
            account_menu.add_command(label="Logout", command=self.logout_user)
            
            # Appointments menu
            appointment_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Appointments", menu=appointment_menu)
            appointment_menu.add_command(label="Appointment History", command=self.show_appointment_history)
            
            # Tools menu
            tools_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Tools", menu=tools_menu)
            tools_menu.add_command(label="Settings", command=self.show_settings)
            tools_menu.add_command(label="Stored Form Fields", command=self.show_stored_form_fields_editor)
            tools_menu.add_command(label="File Cleanup", command=self.show_cleanup_manager)
            tools_menu.add_command(label="Data Management", command=self.show_data_management)
            tools_menu.add_command(label="Encryption Management", command=self.show_encryption_management)
            tools_menu.add_separator()
            tools_menu.add_command(label="Check Models", command=self.check_models)
            tools_menu.add_command(label="Download Models", command=self.download_models)
            
            # Help menu
            help_menu = tk.Menu(menubar, tearoff=0)
            menubar.add_cascade(label="Help", menu=help_menu)
            help_menu.add_command(label="About", command=self.show_about)
            
            # Admin menu (only show for administrators)
            try:
                # Check if current user is admin (you can customize this logic)
                user_email = self.auth_manager.get_user_email()
                if user_email and self._is_admin_user(user_email):
                    admin_menu = tk.Menu(menubar, tearoff=0)
                    menubar.add_cascade(label="Admin", menu=admin_menu)
                    admin_menu.add_command(label="Log Viewer", command=self.show_admin_log_viewer)
            except Exception as e:
                print(f"Warning: Could not setup admin menu: {e}")
                
        except Exception as e:
            print(f"❌ Error creating menu bar: {e}")
            return
    
    def show_appointment_history(self):
        """Show appointment history window"""
        if self.appointment_history_gui:
            self.appointment_history_gui.show_appointment_history()
        else:
            messagebox.showerror("Error", "Appointment history is not available")
    
    def show_settings(self):
        """Show settings window"""
        if self.settings_gui:
            self.settings_gui.show_settings()
        else:
            messagebox.showerror("Error", "Settings are not available")
    
    def show_cleanup_manager(self):
        """Show cleanup manager window"""
        if self.cleanup_gui:
            self.cleanup_gui.show_cleanup_manager()
        else:
            messagebox.showerror("Error", "Cleanup manager is not available")
    
    def show_data_management(self):
        """Show data management window"""
        if self.data_management_gui:
            self.data_management_gui.show_data_management()
        else:
            messagebox.showerror("Error", "Data management is not available")
    
    def show_encryption_management(self):
        """Show encryption management window"""
        if self.encryption_gui:
            self.encryption_gui.show_encryption_manager()
        else:
            messagebox.showerror("Error", "Encryption management is not available")
    
    def show_stored_form_fields_editor(self):
        """Show stored form fields editor window"""
        if self.stored_form_fields_editor:
            self.stored_form_fields_editor.show_editor()
        else:
            messagebox.showerror("Error", "Stored form fields editor is not available")
    
    def _ensure_menu_visible(self):
        """Ensure menu bar is visible on macOS"""
        try:
            # Force window to front and update
            self.root.lift()
            self.root.focus_force()
            self.root.update()
            print("✅ Menu visibility check completed")
        except Exception as e:
            print(f"Warning: Could not ensure menu visibility: {e}")
    
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", 
                          "Form Filler\n\n"
                          "Version 2.0\n"
                          "A comprehensive tool for recording, transcribing, and processing "
                          "physiotherapy appointments with automatic form generation.\n\n"
                          "Features:\n"
                          "• Audio recording and transcription\n"
                          "• Patient management\n"
                          "• Automatic form generation\n"
                          "• File cleanup and retention management\n"
                          "• Secure user authentication\n"
                          "• Subscription management")
    
    def show_subscription_status(self):
        """Show subscription status dialog"""
        try:
            # Get subscription information
            sub_info = self.subscription_checker.get_subscription_info()
            
            # Create status window
            status_window = tk.Toplevel(self.root)
            status_window.title("Subscription Status")
            status_window.geometry("400x300")
            status_window.resizable(False, False)
            
            # Center the window
            status_window.transient(self.root)
            status_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(status_window, padding="20")
            main_frame.pack(fill="both", expand=True)
            
            # Title
            title_label = ttk.Label(main_frame, text="Subscription Status", 
                                   font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 20))
            
            # User info
            user_email = self.auth_manager.get_user_email()
            if user_email:
                ttk.Label(main_frame, text=f"Account: {user_email}", 
                         font=("Arial", 10, "bold")).pack(pady=(0, 10))
            
            # Status info
            status_frame = ttk.LabelFrame(main_frame, text="Current Status", padding="10")
            status_frame.pack(fill="x", pady=(0, 10))
            
            status_text = f"Plan: {sub_info['plan'].title()}\n"
            status_text += f"Status: {sub_info['status'].title()}\n"
            status_text += f"Message: {sub_info['message']}\n"
            status_text += f"Online: {'Yes' if sub_info['is_online'] else 'No'}"
            
            ttk.Label(status_frame, text=status_text, justify="left").pack(anchor="w")
            
            # Features info
            if sub_info['features']:
                features_frame = ttk.LabelFrame(main_frame, text="Available Features", padding="10")
                features_frame.pack(fill="x", pady=(0, 10))
                
                features_text = "\n".join([f"• {feature.replace('_', ' ').title()}" for feature in sub_info['features']])
                ttk.Label(features_frame, text=features_text, justify="left").pack(anchor="w")
            
            # Close button
            ttk.Button(main_frame, text="Close", command=status_window.destroy).pack(pady=(20, 0))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show subscription status: {e}")
    
    def show_account_settings(self):
        """Show account settings dialog"""
        try:
            # Create settings window
            settings_window = tk.Toplevel(self.root)
            settings_window.title("Account Settings")
            settings_window.geometry("500x400")
            settings_window.resizable(False, False)
            
            # Center the window
            settings_window.transient(self.root)
            settings_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(settings_window, padding="20")
            main_frame.pack(fill="both", expand=True)
            
            # Title
            title_label = ttk.Label(main_frame, text="Account Settings", 
                                   font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 20))
            
            # User info
            user_info = self.auth_manager.get_auth_info()
            
            info_frame = ttk.LabelFrame(main_frame, text="Account Information", padding="10")
            info_frame.pack(fill="x", pady=(0, 20))
            
            info_text = f"Email: {user_info.get('user_email', 'Not available')}\n"
            info_text += f"User ID: {user_info.get('user_id', 'Not available')}\n"
            info_text += f"Status: {user_info.get('status', 'Unknown').title()}\n"
            info_text += f"Online: {'Yes' if user_info.get('is_online') else 'No'}\n"
            info_text += f"Token Cached: {'Yes' if user_info.get('has_cached_token') else 'No'}"
            
            ttk.Label(info_frame, text=info_text, justify="left").pack(anchor="w")
            
            # Actions frame
            actions_frame = ttk.LabelFrame(main_frame, text="Actions", padding="10")
            actions_frame.pack(fill="x", pady=(0, 20))
            
            # Refresh subscription button
            ttk.Button(actions_frame, text="Refresh Subscription Status", 
                      command=self.refresh_subscription).pack(pady=(0, 10))
            
            # Clear cache button
            ttk.Button(actions_frame, text="Clear Authentication Cache", 
                      command=self.clear_auth_cache).pack(pady=(0, 10))
            
            # Network info button
            ttk.Button(actions_frame, text="Network Information", 
                      command=self.show_network_info).pack(pady=(0, 10))
            
            # Close button
            ttk.Button(main_frame, text="Close", command=settings_window.destroy).pack(pady=(20, 0))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show account settings: {e}")
    
    def logout_user(self):
        """Logout the current user"""
        try:
            # Confirm logout
            result = messagebox.askyesno("Confirm Logout", 
                                       "Are you sure you want to logout?\n\n"
                                       "You will need to log in again to use the application.")
            
            if result:
                # Perform logout
                if self.auth_manager.logout_user():
                    messagebox.showinfo("Logged Out", "You have been successfully logged out.")
                    # Close the application
                    self.root.quit()
                else:
                    messagebox.showerror("Error", "Failed to logout properly.")
                    
        except Exception as e:
            messagebox.showerror("Error", f"Failed to logout: {e}")
    
    def refresh_subscription(self):
        """Refresh subscription status"""
        try:
            status, message = self.subscription_checker.check_subscription_status(force_online=True)
            messagebox.showinfo("Subscription Status", f"Status: {status.title()}\nMessage: {message}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh subscription: {e}")
    
    def clear_auth_cache(self):
        """Clear authentication cache"""
        try:
            result = messagebox.askyesno("Clear Cache", 
                                       "Are you sure you want to clear the authentication cache?\n\n"
                                       "You will need to log in again.")
            
            if result:
                self.auth_manager.local_storage.clear_all_cache()
                messagebox.showinfo("Cache Cleared", "Authentication cache has been cleared.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear cache: {e}")
    
    def update_auth_status_display(self):
        """Update authentication status display in the main GUI"""
        try:
            # This method can be called to update any auth status indicators
            # For now, we'll just check if user is authenticated
            if not self.auth_manager.is_authenticated():
                messagebox.showwarning("Authentication Required", 
                                     "Your session has expired. Please log in again.")
                self.root.quit()
        except Exception as e:
            print(f"Error updating auth status: {e}")
    
    def start_network_monitoring(self):
        """Start network monitoring and set up callbacks"""
        try:
            # Set up network status change callback
            self.network_manager.set_status_change_callback(self.on_network_status_change)
            
            # Start network monitoring
            if self.network_manager.start_monitoring(check_interval=3600):
                print("✅ Network monitoring started")
            else:
                print("⚠️  Failed to start network monitoring")
            
            # Start background subscription checking
            if self.network_manager.start_background_checking(interval_hours=1):
                print("✅ Background subscription checking started")
            else:
                print("⚠️  Failed to start background checking")
                
        except Exception as e:
            print(f"Error starting network monitoring: {e}")
    
    def on_network_status_change(self, is_online: bool):
        """Handle network status changes"""
        try:
            # Update offline indicator
            self.offline_indicator.update_status(is_online)
            
            # Update GUI in main thread
            self.root.after(0, self._update_network_status_display, is_online)
            
        except Exception as e:
            print(f"Error handling network status change: {e}")
    
    
    def _update_network_status_display(self, is_online: bool):
        """Update network status display in GUI"""
        try:
            # Check if network status components exist
            if not hasattr(self, 'network_status_var') or not hasattr(self, 'network_status_label'):
                return  # GUI not fully initialized yet
                
            if is_online:
                self.network_status_var.set("Online")
                self.network_status_label.config(foreground="green")
            else:
                offline_info = self.offline_indicator.get_offline_info()
                self.network_status_var.set(offline_info['message'])
                self.network_status_label.config(foreground="orange")
                
        except Exception as e:
            print(f"Error updating network status display: {e}")
    
    def get_network_info(self) -> Dict[str, Any]:
        """Get comprehensive network information"""
        try:
            network_status = self.network_manager.get_network_status()
            offline_info = self.offline_indicator.get_offline_info()
            auth_offline_info = self.auth_manager.get_offline_access_info()
            sub_offline_info = self.subscription_checker.get_offline_subscription_info()
            
            return {
                'network': network_status,
                'offline_indicator': offline_info,
                'auth_offline': auth_offline_info,
                'subscription_offline': sub_offline_info
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def show_network_info(self):
        """Show network information dialog"""
        try:
            # Get network information
            network_info = self.get_network_info()
            
            # Create info window
            info_window = tk.Toplevel(self.root)
            info_window.title("Network Information")
            info_window.geometry("600x500")
            info_window.resizable(False, False)
            
            # Center the window
            info_window.transient(self.root)
            info_window.grab_set()
            
            # Main frame
            main_frame = ttk.Frame(info_window, padding="20")
            main_frame.pack(fill="both", expand=True)
            
            # Title
            title_label = ttk.Label(main_frame, text="Network & Offline Information", 
                                   font=("Arial", 16, "bold"))
            title_label.pack(pady=(0, 20))
            
            # Network Status
            network_frame = ttk.LabelFrame(main_frame, text="Network Status", padding="10")
            network_frame.pack(fill="x", pady=(0, 10))
            
            network_data = network_info.get('network', {})
            network_text = f"Online: {'Yes' if network_data.get('is_online') else 'No'}\n"
            network_text += f"Monitoring: {'Yes' if network_data.get('is_monitoring') else 'No'}\n"
            network_text += f"Last Check: {network_data.get('last_check', 'Never')}\n"
            network_text += f"Check Interval: {network_data.get('check_interval', 'N/A')} seconds"
            
            ttk.Label(network_frame, text=network_text, justify="left").pack(anchor="w")
            
            # Offline Indicator
            offline_frame = ttk.LabelFrame(main_frame, text="Offline Status", padding="10")
            offline_frame.pack(fill="x", pady=(0, 10))
            
            offline_data = network_info.get('offline_indicator', {})
            offline_text = f"Offline Mode: {'Yes' if offline_data.get('is_offline') else 'No'}\n"
            offline_text += f"Status: {offline_data.get('message', 'Unknown')}"
            
            if offline_data.get('duration'):
                duration_hours = offline_data['duration'] / 3600
                offline_text += f"\nDuration: {duration_hours:.1f} hours"
            
            ttk.Label(offline_frame, text=offline_text, justify="left").pack(anchor="w")
            
            # Authentication Offline
            auth_frame = ttk.LabelFrame(main_frame, text="Authentication Offline Access", padding="10")
            auth_frame.pack(fill="x", pady=(0, 10))
            
            auth_data = network_info.get('auth_offline', {})
            auth_text = f"Can Access Offline: {'Yes' if auth_data.get('can_access_offline') else 'No'}\n"
            auth_text += f"Days Remaining: {auth_data.get('days_remaining', 0)}\n"
            auth_text += f"Status: {auth_data.get('message', 'Unknown')}"
            
            ttk.Label(auth_frame, text=auth_text, justify="left").pack(anchor="w")
            
            # Subscription Offline
            sub_frame = ttk.LabelFrame(main_frame, text="Subscription Offline Access", padding="10")
            sub_frame.pack(fill="x", pady=(0, 20))
            
            sub_data = network_info.get('subscription_offline', {})
            sub_text = f"Plan: {sub_data.get('plan', 'Unknown').title()}\n"
            sub_text += f"Status: {sub_data.get('status', 'Unknown').title()}\n"
            sub_text += f"Can Access Offline: {'Yes' if sub_data.get('can_access_offline') else 'No'}\n"
            sub_text += f"Days Remaining: {sub_data.get('days_remaining', 0)}\n"
            sub_text += f"Message: {sub_data.get('message', 'Unknown')}"
            
            ttk.Label(sub_frame, text=sub_text, justify="left").pack(anchor="w")
            
            # Close button
            ttk.Button(main_frame, text="Close", command=info_window.destroy).pack(pady=(20, 0))
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show network information: {e}")
    
    def _is_admin_user(self, email: str) -> bool:
        """Check if user is an administrator"""
        # Define admin emails - you can customize this list
        admin_emails = [
            "ceteasystems@gmail.com",
            "nishaan.dulay@gmail.com",
            # Add more admin emails as needed
        ]
        return email.lower() in admin_emails
    
    def show_admin_log_viewer(self):
        """Show the administrative log viewer"""
        try:
            import subprocess
            import sys
            
            # Launch the admin log viewer in a separate process
            subprocess.Popen([sys.executable, "admin_log_viewer.py"])
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open log viewer: {e}")
    

    def generate_appointment_id(self):
        """Generate timestamp-based appointment ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def upload_audio_file(self):
        """Upload an audio file for processing"""
        # Validate inputs
        patient_name = self.patient_name_var.get().strip()
        if not patient_name:
            messagebox.showerror("Error", "Please enter a patient name")
            return
        
        # Generate appointment ID
        appointment_id = self.generate_appointment_id()
        self.current_appointment_id = appointment_id
        
        # Get form selection
        self.forms_to_fill['wsib'] = self.wsib_form_var.get()
        self.forms_to_fill['ocf18'] = self.ocf18_form_var.get()
        self.forms_to_fill['ocf23'] = self.ocf23_form_var.get()
        
        # File dialog for audio files
        file_types = [
            ("Audio files", "*.wav *.mp3 *.m4a *.aac *.flac *.ogg"),
            ("WAV files", "*.wav"),
            ("MP3 files", "*.mp3"),
            ("M4A files", "*.m4a"),
            ("All files", "*.*")
        ]
        
        file_path = filedialog.askopenfilename(
            title="Select Audio File",
            filetypes=file_types
        )
        
        if file_path:
            try:
                # Copy file to temporary location
                filename = os.path.basename(file_path)
                new_filename = f"{appointment_id}_{filename}"
                
                # Use proper temp directory
                try:
                    from app_paths import get_temp_path
                    temp_dir = str(get_temp_path())
                except ImportError:
                    temp_dir = "temp"
                    os.makedirs(temp_dir, exist_ok=True)
                
                recording_path = os.path.join(temp_dir, new_filename)
                
                shutil.copy2(file_path, recording_path)
                
                # Update GUI
                self.upload_label.config(text=f"Uploaded: {filename}")
                print("Processing uploaded file...")
                print("Transcribing audio...")
                
                # Get current form selection from GUI
                forms_to_fill = {
                    'wsib': self.wsib_form_var.get(),
                    'ocf18': self.ocf18_form_var.get(),
                    'ocf23': self.ocf23_form_var.get()
                }
                
                # Add job to background processor
                job_id = self.background_processor.add_job(
                    appointment_id=appointment_id,
                    recording_path=recording_path,
                    patient_name=self.patient_name_var.get().strip(),
                    appointment_type=self.appointment_type_var.get(),
                    appointment_notes="",  # Notes field removed
                    forms_to_fill=forms_to_fill
                )
                
                print(f"✅ Uploaded file queued for processing with job ID: {job_id}")
                
                # Provide user feedback about what will happen
                if any(forms_to_fill.values()):
                    selected_forms = [form for form, selected in forms_to_fill.items() if selected]
                    form_names = {
                        'wsib': 'WSIB FAF',
                        'ocf18': 'FSRA OCF-18',
                        'ocf23': 'FSRA OCF-23'
                    }
                    form_list = ', '.join([form_names[form] for form in selected_forms])
                    print(f"File queued - will transcribe and generate: {form_list}")
                else:
                    print("File queued - will transcribe only (no forms selected)")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to upload file: {str(e)}")
                print("Upload failed")
    
    def start_recording(self):
        """Start audio recording"""
        if self.is_recording:
            return
        
        # Validate inputs
        patient_name = self.patient_name_var.get().strip()
        if not patient_name:
            messagebox.showerror("Error", "Please enter a patient name")
            return
        
        # Get form selection
        self.forms_to_fill['wsib'] = self.wsib_form_var.get()
        self.forms_to_fill['ocf18'] = self.ocf18_form_var.get()
        self.forms_to_fill['ocf23'] = self.ocf23_form_var.get()
        
        # Generate appointment ID
        appointment_id = self.generate_appointment_id()
        self.current_appointment_id = appointment_id
        
        try:
            # Get selected device index
            device_index = self.get_selected_device_index()
            
            # Start recording with selected device
            self.recorder.start_recording(appointment_id, device_index)
            self.is_recording = True
            
            # Update GUI
            self.record_button.config(state="disabled")
            self.stop_button.config(state="normal")
            print("Recording...")
            
            # Start timer
            self.start_timer()
            
            # Refresh today's appointments to show the new recording
            self.load_today_appointments()
            
            # Clear selection to reset action buttons
            self.today_tree.selection_remove(self.today_tree.selection())
            self.disable_action_buttons()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to start recording: {str(e)}")
            print("Recording failed")
    
    def stop_recording(self):
        """Stop audio recording and start background processing"""
        if not self.is_recording:
            return
        
        try:
            # Stop recording
            recording_path = self.recorder.stop_recording()
            self.is_recording = False
            
            # Update GUI
            self.record_button.config(state="normal")
            self.stop_button.config(state="disabled")
            print("Processing queued...")
            
            # Get current form selection from GUI
            forms_to_fill = {
                'wsib': self.wsib_form_var.get(),
                'ocf18': self.ocf18_form_var.get(),
                'ocf23': self.ocf23_form_var.get()
            }
            
            # Add job to background processor
            job_id = self.background_processor.add_job(
                appointment_id=self.current_appointment_id,
                recording_path=recording_path,
                patient_name=self.patient_name_var.get().strip(),
                appointment_type=self.appointment_type_var.get(),
                appointment_notes="",  # Notes field removed
                forms_to_fill=forms_to_fill
            )
            
            print(f"✅ Recording queued for processing with job ID: {job_id}")
            
            # Provide user feedback about what will happen
            if any(forms_to_fill.values()):
                selected_forms = [form for form, selected in forms_to_fill.items() if selected]
                form_names = {
                    'wsib': 'WSIB FAF',
                    'ocf18': 'FSRA OCF-18',
                    'ocf23': 'FSRA OCF-23'
                }
                form_list = ', '.join([form_names[form] for form in selected_forms])
                print(f"Recording queued - will transcribe and generate: {form_list}")
            else:
                print("Recording queued - will transcribe only (no forms selected)")
            
            # Clear form and reset for next recording
            self.clear_form_for_next_recording()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to stop recording: {str(e)}")
            print("Recording stop failed")
    
    def on_model_type_changed(self, event=None):
        """Handle model type selection change"""
        display_name = self.model_type_var.get()
        
        # Map display names to actual model types
        model_mapping = {
            "4B-Larger Model": "qwen3-4b",
            "1.7B-Smaller Model": "qwen3-1.7b"
        }
        
        new_model_type = model_mapping.get(display_name, "qwen3-4b")
        
        if new_model_type != self.current_model_type:
            print(f"🔄 Switching from {self.current_model_type} to {display_name} ({new_model_type}) model")
            self.current_model_type = new_model_type
            
            # Update the data extractor with new model type
            self.wsib_data_extractor = WSIBDataExtractor(model_type=new_model_type)
            
            # Update the background processor model type
            if hasattr(self, 'background_processor') and self.background_processor:
                self.background_processor.update_model_type(new_model_type)
            
            # Update status with display name
            print(f"Model switched to {display_name}")
            print(f"✅ Model switched to {display_name} ({new_model_type})")
    
    def clear_form_for_next_recording(self):
        """Clear the form for the next recording"""
        # Clear patient information
        self.patient_name_var.set("")
        self.appointment_type_var.set("Initial Assessment")
        
        # Clear form selection
        self.wsib_form_var.set(False)
        self.ocf18_form_var.set(False)
        self.ocf23_form_var.set(False)
        
        # Reset current appointment ID
        self.current_appointment_id = None
        
        # Refresh today's appointments
        self.load_today_appointments()
        
        # Clear selection to reset action buttons
        self.today_tree.selection_remove(self.today_tree.selection())
        self.disable_action_buttons()
        
    def _on_main_mousewheel(self, event):
        """Handle mousewheel scrolling in main window"""
        self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def start_timer(self):
        """Start the recording timer"""
        if self.is_recording:
            elapsed = time.time() - self.recorder.start_time
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            self.timer_label.config(text=f"{minutes:02d}:{seconds:02d}")
            self.root.after(1000, self.start_timer)


def is_first_run() -> bool:
    """Check if this is the first time the app is running"""
    try:
        from app_paths import get_writable_path
        marker_file = get_writable_path(".first_run_complete")
        return not marker_file.exists()
    except:
        return False


def run_first_run_setup(root) -> bool:
    """Run first-time setup: download models and configure app"""
    try:
        # Create setup dialog
        setup_window = tk.Toplevel(root)
        setup_window.title("First Time Setup")
        setup_window.geometry("600x400")
        setup_window.resizable(False, False)
        setup_window.transient(root)
        setup_window.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(setup_window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Welcome to Physio Clinic Assistant!", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Info text
        info_text = (
            "This is your first time running the application.\n\n"
            "We need to download AI models (~4.3 GB) for transcription and data extraction.\n"
            "This is a one-time download and may take 10-15 minutes depending on your connection.\n\n"
            "The app will download:\n"
            "• Whisper model for transcription (~1.5 GB)\n"
            "• Qwen models for data extraction (~2.8 GB)\n\n"
            "Models will be saved to:\n"
            "~/Library/Application Support/PhysioClinicAssistant/models/"
        )
        info_label = ttk.Label(main_frame, text=info_text, justify="left", wraplength=550)
        info_label.pack(pady=(0, 20))
        
        # Progress frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill="x", pady=(0, 20))
        
        status_var = tk.StringVar(value="Ready to download")
        status_label = ttk.Label(progress_frame, textvariable=status_var)
        status_label.pack()
        
        progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        progress.pack(fill="x", pady=(10, 0))
        
        # Download flag
        download_complete = {'success': False}
        
        def start_download():
            """Start model download in background thread"""
            download_btn.config(state="disabled")
            skip_btn.config(state="disabled")
            progress.start()
            status_var.set("Downloading models... This may take 10-15 minutes")
            
            def download_thread():
                try:
                    from model_downloader import ModelDownloader
                    downloader = ModelDownloader()
                    
                    # Download all models
                    status_var.set("Downloading models... Please wait...")
                    downloader.download_all_models()
                    
                    # Complete setup
                    root.after(0, lambda: status_var.set("Finalizing setup..."))
                    root.after(0, progress.stop)
                    
                    # Complete setup in main thread
                    root.after(100, lambda: complete_setup())
                    
                except Exception as e:
                    root.after(0, lambda: status_var.set(f"Error: {e}"))
                    root.after(0, progress.stop)
                    root.after(0, lambda: messagebox.showerror("Download Failed", 
                        f"Failed to download models: {e}\n\nYou can try downloading later from the Tools menu."))
                    download_complete['success'] = False
                    root.after(500, setup_window.destroy)
            
            def complete_setup():
                """Complete first-run setup"""
                # Mark first run as complete
                try:
                    from app_paths import get_writable_path
                    marker_file = get_writable_path(".first_run_complete")
                    marker_file.write_text("Setup completed successfully")
                except:
                    pass
                
                download_complete['success'] = True
                status_var.set("Setup complete! You can now start recording.")
                setup_window.after(1500, setup_window.destroy)
            
            thread = threading.Thread(target=download_thread, daemon=True)
            thread.start()
        
        def skip_download():
            """Skip download and mark for later"""
            result = messagebox.askyesno(
                "Skip Download?",
                "Models are required for transcription and form filling.\n\n"
                "Without models, you won't be able to process appointments.\n\n"
                "You can download them later from Tools > Download Models.\n\n"
                "Skip download for now?"
            )
            if result:
                download_complete['success'] = True
                setup_window.destroy()
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack()
        
        download_btn = ttk.Button(button_frame, text="Download Now", command=start_download)
        download_btn.pack(side="left", padx=5)
        
        skip_btn = ttk.Button(button_frame, text="Skip for Now", command=skip_download)
        skip_btn.pack(side="left", padx=5)
        
        # Wait for window to close
        setup_window.wait_window()
        
        return download_complete['success']
        
    except Exception as e:
        print(f"Error in first run setup: {e}")
        messagebox.showerror("Setup Error", f"First run setup failed: {e}")
        return False


def main():
    """Main entry point with authentication check"""
    root = tk.Tk()
    
    # Check authentication before starting the main app
    auth_manager = AuthManager()
    auth_status = auth_manager.check_auth_status()
    
    if auth_status == 'unauthenticated':
        # Show login dialog
        def on_login_success():
            # Login successful, check subscription before starting the main app
            subscription_checker = SubscriptionChecker(auth_manager)
            status, message = subscription_checker.check_subscription_status(force_online=True)
            
            if status in ['expired', 'cancelled', 'past_due']:
                messagebox.showerror(
                    "Subscription Expired",
                    "Your subscription has expired. Please contact ceteasystems@gmail.com to renew your subscription."
                )
                root.quit()
                return
            
            # Check if first run and download models if needed
            if is_first_run():
                if not run_first_run_setup(root):
                    root.quit()
                    return
            
            # Subscription valid and setup complete, start the main app
            app = PhysioApp(root)
            # Don't call mainloop here - it's already running
        
        login_gui = show_login_dialog(root, on_login_success)
        root.mainloop()  # Start the main loop for login dialog
        
    elif auth_status in ['authenticated', 'expired']:
        # User is authenticated or has cached auth, check subscription
        subscription_checker = SubscriptionChecker(auth_manager)
        status, message = subscription_checker.check_subscription_status()
        
        if status in ['expired', 'cancelled', 'past_due']:
            messagebox.showerror(
                "Subscription Expired",
                "Your subscription has expired. Please contact ceteasystems@gmail.com to renew your subscription."
            )
            root.quit()
        else:
            # Check if first run and download models if needed
            if is_first_run():
                if not run_first_run_setup(root):
                    root.quit()
                    return
            
            # Subscription valid and setup complete, start the main app
            app = PhysioApp(root)
        
        # If expired, show warning but allow offline access
        if auth_status == 'expired':
            messagebox.showwarning("Session Expired", 
                                 "Your authentication session has expired.\n"
                                 "Some features may be limited until you reconnect to the internet.")
        
        root.mainloop()
        
    else:
        # Other status (error, etc.)
        messagebox.showerror("Authentication Error", 
                           f"Authentication check failed with status: {auth_status}\n"
                           "Please restart the application.")
        root.quit()


if __name__ == "__main__":
    # Critical: freeze_support() must be called first in frozen PyInstaller apps
    # to prevent duplicate app instances when multiprocessing spawns child processes
    multiprocessing.freeze_support()
    
    main() 