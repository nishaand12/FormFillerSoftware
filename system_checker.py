#!/usr/bin/env python3
"""
System Requirements Checker for Physiotherapy Clinic Assistant
Validates system requirements before installation and startup
"""

import os
import sys
import platform
import shutil
import subprocess
import psutil
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Tuple, Optional
import json
from pathlib import Path


class SystemChecker:
    """Comprehensive system requirements checker"""
    
    def __init__(self):
        self.requirements = {
            'python_version': (3, 8),
            'min_ram_gb': 8,
            'min_disk_gb': 10,
            'required_libraries': [
                'tkinter',
                'numpy',
                'scipy',
                'sounddevice',
                'pvrecorder',
                'faster_whisper',
                'llama_cpp_python',
                'cryptography',
                'supabase',
                'requests',
                'pillow',
                'reportlab',
                'pdfrw'
            ]
        }
        
        self.results = {
            'python_version': False,
            'ram': False,
            'disk_space': False,
            'audio_devices': False,
            'libraries': False,
            'permissions': False,
            'overall': False
        }
        
        self.errors = []
        self.warnings = []
    
    def check_python_version(self) -> Tuple[bool, str]:
        """Check if Python version meets requirements"""
        try:
            current_version = sys.version_info[:2]
            required_version = self.requirements['python_version']
            
            if current_version >= required_version:
                self.results['python_version'] = True
                return True, f"{current_version[0]}.{current_version[1]} ✓"
            else:
                error_msg = f"{required_version[0]}.{required_version[1]}+ required, found {current_version[0]}.{current_version[1]}"
                self.errors.append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error checking Python version: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def check_ram(self) -> Tuple[bool, str]:
        """Check available RAM"""
        try:
            memory = psutil.virtual_memory()
            total_gb = memory.total / (1024**3)
            available_gb = memory.available / (1024**3)
            required_gb = self.requirements['min_ram_gb']
            
            if total_gb >= required_gb:
                self.results['ram'] = True
                return True, f"{total_gb:.1f}GB total, {available_gb:.1f}GB available ✓"
            else:
                error_msg = f"Minimum {required_gb}GB required, found {total_gb:.1f}GB"
                self.errors.append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error checking RAM: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def check_disk_space(self) -> Tuple[bool, str]:
        """Check available disk space"""
        try:
            disk_usage = psutil.disk_usage('/')
            free_gb = disk_usage.free / (1024**3)
            total_gb = disk_usage.total / (1024**3)
            required_gb = self.requirements['min_disk_gb']
            
            if free_gb >= required_gb:
                self.results['disk_space'] = True
                return True, f"{free_gb:.1f}GB free of {total_gb:.1f}GB ✓"
            else:
                error_msg = f"Minimum {required_gb}GB free space required, found {free_gb:.1f}GB"
                self.errors.append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error checking disk space: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def check_audio_devices(self) -> Tuple[bool, str]:
        """Check for available audio devices"""
        try:
            import sounddevice as sd
            
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            
            if input_devices:
                self.results['audio_devices'] = True
                return True, f"{len(input_devices)} input device(s) found ✓"
            else:
                error_msg = "No audio input devices found"
                self.errors.append(error_msg)
                return False, error_msg
                
        except ImportError:
            # sounddevice not installed yet, that's okay
            self.results['audio_devices'] = True
            return True, "Audio device check skipped (sounddevice not installed) ✓"
        except Exception as e:
            error_msg = f"Error checking audio devices: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def check_libraries(self) -> Tuple[bool, str]:
        """Check if required libraries are available"""
        try:
            missing_libraries = []
            available_libraries = []
            
            for library in self.requirements['required_libraries']:
                try:
                    if library == 'tkinter':
                        import tkinter
                    elif library == 'numpy':
                        import numpy
                    elif library == 'scipy':
                        import scipy
                    elif library == 'sounddevice':
                        import sounddevice
                    elif library == 'pvrecorder':
                        import pvrecorder
                    elif library == 'faster_whisper':
                        import faster_whisper
                    elif library == 'llama_cpp_python':
                        import llama_cpp
                    elif library == 'cryptography':
                        import cryptography
                    elif library == 'supabase':
                        import supabase
                    elif library == 'requests':
                        import requests
                    elif library == 'pillow':
                        import PIL
                    elif library == 'reportlab':
                        import reportlab
                    elif library == 'pdfrw':
                        import pdfrw
                    
                    available_libraries.append(library)
                    
                except ImportError:
                    missing_libraries.append(library)
            
            if not missing_libraries:
                self.results['libraries'] = True
                return True, f"All {len(available_libraries)} required Python packages available ✓"
            else:
                error_msg = f"Missing packages: {', '.join(missing_libraries)}"
                self.errors.append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error checking libraries: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def check_permissions(self) -> Tuple[bool, str]:
        """Check system permissions"""
        try:
            permission_issues = []
            
            # Check write permissions in current directory
            try:
                test_file = Path("test_permissions.tmp")
                test_file.write_text("test")
                test_file.unlink()
            except Exception:
                permission_issues.append("Write permission in current directory")
            
            # Check audio permissions (macOS)
            if platform.system() == "Darwin":
                try:
                    import sounddevice as sd
                    sd.query_devices()
                except Exception:
                    permission_issues.append("Microphone access permission")
            
            # Check network access
            try:
                import requests
                requests.get("https://www.google.com", timeout=5)
            except Exception:
                permission_issues.append("Network access")
            
            if not permission_issues:
                self.results['permissions'] = True
                return True, "Permissions: All required permissions available ✓"
            else:
                warning_msg = f"Permission issues: {', '.join(permission_issues)}"
                self.warnings.append(warning_msg)
                return False, warning_msg
                
        except Exception as e:
            error_msg = f"Error checking permissions: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def check_system_libraries(self) -> Tuple[bool, str]:
        """Check for required system libraries"""
        try:
            missing_system_libs = []
            
            # Check for required system libraries based on platform
            if platform.system() == "Darwin":  # macOS
                # Check for Xcode Command Line Tools
                try:
                    subprocess.run(["xcode-select", "--print-path"], check=True, capture_output=True)
                except (subprocess.CalledProcessError, FileNotFoundError):
                    missing_system_libs.append("Xcode Command Line Tools")
            
            elif platform.system() == "Windows":
                # Check for Visual C++ Redistributable
                try:
                    import winreg
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64")
                    winreg.CloseKey(key)
                except:
                    missing_system_libs.append("Visual C++ Redistributable")
            
            elif platform.system() == "Linux":
                # Check for required system packages
                required_packages = ["libasound2-dev", "portaudio19-dev", "libsndfile1"]
                for package in required_packages:
                    try:
                        subprocess.run(["dpkg", "-l", package], check=True, capture_output=True)
                    except subprocess.CalledProcessError:
                        missing_system_libs.append(package)
            
            if not missing_system_libs:
                return True, "System libraries: All required system libraries available ✓"
            else:
                warning_msg = f"Missing system libraries: {', '.join(missing_system_libs)}"
                self.warnings.append(warning_msg)
                return False, warning_msg
                
        except Exception as e:
            warning_msg = f"Error checking system libraries: {e}"
            self.warnings.append(warning_msg)
            return False, warning_msg
    
    def run_all_checks(self) -> Dict:
        """Run all system checks"""
        print("🔍 Running system requirements check...")
        print("=" * 50)
        
        checks = [
            ("Python Version", self.check_python_version),
            ("Memory (RAM)", self.check_ram),
            ("Disk Space", self.check_disk_space),
            ("Audio Devices", self.check_audio_devices),
            ("Python Packages", self.check_libraries),
        ]
        
        results = {}
        for check_name, check_func in checks:
            print(f"\n{check_name}:")
            try:
                success, message = check_func()
                results[check_name] = {'success': success, 'message': message}
                print(f"  {message}")
            except Exception as e:
                error_msg = f"Check failed: {e}"
                results[check_name] = {'success': False, 'message': error_msg}
                print(f"  ❌ {error_msg}")
                self.errors.append(error_msg)
        
        # Determine overall result
        critical_checks = ['python_version', 'ram', 'disk_space', 'libraries']
        critical_passed = all(self.results.get(check, False) for check in critical_checks)
        
        self.results['overall'] = critical_passed
        
        print("\n" + "=" * 50)
        if critical_passed:
            print("✅ System requirements check PASSED")
            if self.warnings:
                print(f"⚠️  {len(self.warnings)} warning(s) found")
        else:
            print("❌ System requirements check FAILED")
            print(f"❌ {len(self.errors)} error(s) found")
        
        return {
            'overall_success': critical_passed,
            'results': results,
            'errors': self.errors,
            'warnings': self.warnings
        }
    
    def get_system_info(self) -> Dict:
        """Get comprehensive system information"""
        try:
            return {
                'platform': {
                    'system': platform.system(),
                    'release': platform.release(),
                    'version': platform.version(),
                    'machine': platform.machine(),
                    'processor': platform.processor(),
                    'architecture': platform.architecture(),
                },
                'python': {
                    'version': sys.version,
                    'executable': sys.executable,
                    'path': sys.path,
                },
                'hardware': {
                    'cpu_count': psutil.cpu_count(),
                    'memory_total': psutil.virtual_memory().total,
                    'memory_available': psutil.virtual_memory().available,
                    'disk_total': psutil.disk_usage('/').total,
                    'disk_free': psutil.disk_usage('/').free,
                },
                'environment': {
                    'path': os.environ.get('PATH', ''),
                    'pythonpath': os.environ.get('PYTHONPATH', ''),
                    'home': os.environ.get('HOME', ''),
                    'user': os.environ.get('USER', ''),
                }
            }
        except Exception as e:
            return {'error': f"Error getting system info: {e}"}


class SystemCheckerGUI:
    """GUI for system requirements checker"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("System Requirements Checker")
        self.root.geometry("600x500")
        self.root.resizable(False, False)
        
        self.checker = SystemChecker()
        self.setup_gui()
    
    def setup_gui(self):
        """Setup the GUI"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Physiotherapy Clinic Assistant", 
                               font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(main_frame, text="System Requirements Checker", 
                                  font=("Arial", 12))
        subtitle_label.pack(pady=(0, 20))
        
        # Check button
        self.check_button = ttk.Button(main_frame, text="Check System Requirements", 
                                      command=self.run_checks)
        self.check_button.pack(pady=(0, 20))
        
        # Results frame
        self.results_frame = ttk.LabelFrame(main_frame, text="Check Results", padding="10")
        self.results_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Results text
        self.results_text = tk.Text(self.results_frame, height=15, wrap="word")
        scrollbar = ttk.Scrollbar(self.results_frame, orient="vertical", command=self.results_text.yview)
        self.results_text.configure(yscrollcommand=scrollbar.set)
        
        self.results_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x")
        
        # Save report button
        self.save_button = ttk.Button(buttons_frame, text="Save Report", 
                                     command=self.save_report, state="disabled")
        self.save_button.pack(side="left", padx=(0, 10))
        
        # Close button
        ttk.Button(buttons_frame, text="Close", command=self.root.quit).pack(side="right")
    
    def run_checks(self):
        """Run system checks and display results"""
        self.check_button.config(state="disabled")
        self.results_text.delete(1.0, tk.END)
        self.results_text.insert(tk.END, "Running system checks...\n")
        self.root.update()
        
        try:
            # Run checks
            results = self.checker.run_all_checks()
            
            # Display results
            self.results_text.delete(1.0, tk.END)
            
            if results['overall_success']:
                self.results_text.insert(tk.END, "✅ System requirements check PASSED\n\n")
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
            
            # Enable save button
            self.save_button.config(state="normal")
            
        except Exception as e:
            self.results_text.insert(tk.END, f"Error running checks: {e}\n")
        finally:
            self.check_button.config(state="normal")
    
    def save_report(self):
        """Save system check report"""
        try:
            from tkinter import filedialog
            
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Save System Check Report"
            )
            
            if filename:
                with open(filename, 'w') as f:
                    f.write("Physiotherapy Clinic Assistant - System Check Report\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(self.results_text.get(1.0, tk.END))
                
                messagebox.showinfo("Success", f"Report saved to {filename}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save report: {e}")
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()


def main():
    """Main function"""
    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        # Run GUI version
        app = SystemCheckerGUI()
        app.run()
    else:
        # Run command line version
        checker = SystemChecker()
        results = checker.run_all_checks()
        
        if not results['overall_success']:
            sys.exit(1)


if __name__ == "__main__":
    main()
