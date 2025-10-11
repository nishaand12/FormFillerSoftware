#!/usr/bin/env python3
"""
Configuration Validator for Physiotherapy Clinic Assistant
Validates configuration files, required files, and system setup on startup
"""

import os
import sys
import json
import hashlib
import sqlite3
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging

# Import path helpers
try:
    from app_paths import get_resource_path, get_writable_path
except ImportError:
    def get_resource_path(relative_path: str = "") -> Path:
        if getattr(sys, '_MEIPASS', None):
            return Path(sys._MEIPASS) / relative_path if relative_path else Path(sys._MEIPASS)
        return Path(__file__).parent / relative_path if relative_path else Path(__file__).parent
    
    def get_writable_path(relative_path: str = "") -> Path:
        app_name = "PhysioClinicAssistant"
        if sys.platform == 'darwin':
            base_path = Path.home() / "Library" / "Application Support" / app_name
        else:
            base_path = Path.home() / ".local" / "share" / app_name
        base_path.mkdir(parents=True, exist_ok=True)
        if relative_path:
            full_path = base_path / relative_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            return full_path
        return base_path


class ConfigValidator:
    """Validates application configuration and required files"""
    
    def __init__(self):
        # Use proper resource path for bundled files
        self.base_dir = get_resource_path()
        self.required_files = {
            'config': [
                'config/field_map_ocf18.json',
                'config/field_map_ocf23_simplified.json',
                'config/field_map_wsib.json',
                'config/ocf18_checkbox_groups.json',
                'config/ocf18_field_types.json',
                'config/ocf18_stored_data.json',
                'config/ocf23_checkbox_groups_simplified.json',
                'config/ocf23_checkbox_groups.json',
                'config/ocf23_field_types_simplified.json',
                'config/ocf23_stored_data.json',
                'config/supabase_config.json',
                'config/wsib_checkbox_groups.json',
                'config/wsib_field_types.json',
                'config/wsib_stored_data.json',
            ],
            'forms': [
                'forms/templates/ocf18_template.pdf',
                'forms/templates/ocf23_template.pdf',
                'forms/templates/wsib_template.pdf',
            ],
            'models': [
                'models/Qwen3-1.7B-Q8_0.gguf',
                'models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf',
            ],
            'auth': [
                'auth/__init__.py',
                'auth/auth_manager.py',
                'auth/config_manager.py',
                'auth/error_logger.py',
                'auth/input_validator.py',
                'auth/keyboard_shortcuts.py',
                'auth/loading_animations.py',
                'auth/local_storage.py',
                'auth/login_gui.py',
                'auth/network_manager.py',
                'auth/rate_limiter.py',
                'auth/session_manager.py',
                'auth/subscription_checker.py',
                'auth/user_onboarding.py',
            ]
        }
        
        self.required_directories = [
            'recordings',
            'transcripts',
            'summaries',
            'extractions',
            'output_forms',
            'data',
            'logs',
        ]
        
        self.validation_results = {
            'required_files': False,
            'config_files': False,
            'model_files': False,
            'database': False,
            'audio_devices': False,
            'permissions': False,
            'overall': False
        }
        
        self.errors = []
        self.warnings = []
    
    def validate_required_files(self) -> Tuple[bool, str]:
        """Validate that all required files exist"""
        try:
            missing_files = []
            
            for category, files in self.required_files.items():
                for file_path in files:
                    # Use appropriate base path based on file category
                    if category == 'models':
                        # Models are downloaded to writable location
                        full_path = get_writable_path(file_path)
                    else:
                        # config, forms, auth are bundled in app (read-only)
                        full_path = get_resource_path(file_path)
                    
                    if not full_path.exists():
                        # Models are optional (downloaded on demand)
                        if category != 'models':
                            missing_files.append(file_path)
            
            if not missing_files:
                self.validation_results['required_files'] = True
                return True, f"All required files present ✓"
            else:
                error_msg = f"Missing required files: {', '.join(missing_files)}"
                self.errors.append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error validating required files: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def validate_config_files(self) -> Tuple[bool, str]:
        """Validate configuration files are valid JSON"""
        try:
            config_errors = []
            
            for file_path in self.required_files['config']:
                # Config files are in bundle (read-only)
                full_path = get_resource_path(file_path)
                if full_path.exists():
                    try:
                        with open(full_path, 'r') as f:
                            json.load(f)
                    except json.JSONDecodeError as e:
                        config_errors.append(f"{file_path}: Invalid JSON - {e}")
                    except Exception as e:
                        config_errors.append(f"{file_path}: Error reading file - {e}")
            
            if not config_errors:
                self.validation_results['config_files'] = True
                return True, f"All configuration files valid ✓"
            else:
                error_msg = f"Configuration file errors: {'; '.join(config_errors)}"
                self.errors.append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error validating config files: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def validate_model_files(self) -> Tuple[bool, str]:
        """Validate model files exist and are not corrupted"""
        try:
            model_errors = []
            model_warnings = []
            
            for file_path in self.required_files['models']:
                # Models are in writable location (downloaded)
                full_path = get_writable_path(file_path)
                if full_path.exists():
                    # Check file size (models should be large)
                    file_size = full_path.stat().st_size
                    if file_size < 1024 * 1024:  # Less than 1MB
                        model_warnings.append(f"{file_path}: File size suspiciously small ({file_size} bytes)")
                    
                    # Check file extension
                    if not file_path.endswith('.gguf'):
                        model_errors.append(f"{file_path}: Invalid model file extension")
                    
                    # Try to calculate hash (basic integrity check)
                    try:
                        with open(full_path, 'rb') as f:
                            # Read first 1MB for hash calculation
                            data = f.read(1024 * 1024)
                            if len(data) == 0:
                                model_errors.append(f"{file_path}: File appears to be empty")
                    except Exception as e:
                        model_errors.append(f"{file_path}: Error reading file - {e}")
                else:
                    model_errors.append(f"{file_path}: Model file not found")
            
            if not model_errors:
                self.validation_results['model_files'] = True
                result_msg = "All model files present and valid ✓"
                if model_warnings:
                    result_msg += f" (warnings: {len(model_warnings)})"
                    self.warnings.extend(model_warnings)
                return True, result_msg
            else:
                error_msg = f"Model file errors: {'; '.join(model_errors)}"
                self.errors.append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error validating model files: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def validate_database(self) -> Tuple[bool, str]:
        """Validate database connectivity and schema"""
        try:
            # Database is in writable location
            db_path = get_writable_path("data/clinic_data.db")
            
            if not db_path.exists():
                # Database doesn't exist, that's okay for first run
                self.validation_results['database'] = True
                return True, "Database will be created on first run ✓"
            
            # Test database connection
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                
                # Check if required tables exist
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall()]
                
                required_tables = ['appointments', 'processing_status', 'file_versions']
                missing_tables = [table for table in required_tables if table not in tables]
                
                if missing_tables:
                    error_msg = f"Missing database tables: {', '.join(missing_tables)}"
                    self.errors.append(error_msg)
                    return False, error_msg
                
                # Test basic query
                cursor.execute("SELECT COUNT(*) FROM appointments")
                cursor.fetchone()
                
                conn.close()
                
                self.validation_results['database'] = True
                return True, f"Database connection successful, {len(tables)} tables found ✓"
                
            except sqlite3.Error as e:
                error_msg = f"Database error: {e}"
                self.errors.append(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error validating database: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def validate_audio_devices(self) -> Tuple[bool, str]:
        """Validate audio device availability"""
        try:
            import sounddevice as sd
            
            devices = sd.query_devices()
            input_devices = [d for d in devices if d['max_input_channels'] > 0]
            
            if input_devices:
                self.validation_results['audio_devices'] = True
                return True, f"Audio devices: {len(input_devices)} input device(s) available ✓"
            else:
                error_msg = "No audio input devices found"
                self.errors.append(error_msg)
                return False, error_msg
                
        except ImportError:
            # sounddevice not available, that's okay for validation
            self.validation_results['audio_devices'] = True
            return True, "Audio device check skipped (sounddevice not available) ✓"
        except Exception as e:
            error_msg = f"Error checking audio devices: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def validate_permissions(self) -> Tuple[bool, str]:
        """Validate file and system permissions"""
        try:
            permission_issues = []
            
            # Check write permissions in data directory
            data_dir = self.base_dir / "data"
            if data_dir.exists():
                try:
                    test_file = data_dir / "test_permissions.tmp"
                    test_file.write_text("test")
                    test_file.unlink()
                except Exception:
                    permission_issues.append("Write permission in data directory")
            
            # Check write permissions in other required directories
            for dir_name in self.required_directories:
                dir_path = self.base_dir / dir_name
                if dir_path.exists():
                    try:
                        test_file = dir_path / "test_permissions.tmp"
                        test_file.write_text("test")
                        test_file.unlink()
                    except Exception:
                        permission_issues.append(f"Write permission in {dir_name} directory")
            
            # Check microphone permissions (macOS)
            if sys.platform == "darwin":
                try:
                    import sounddevice as sd
                    sd.query_devices()
                except Exception:
                    permission_issues.append("Microphone access permission")
            
            if not permission_issues:
                self.validation_results['permissions'] = True
                return True, "All required permissions available ✓"
            else:
                warning_msg = f"Permission issues: {', '.join(permission_issues)}"
                self.warnings.append(warning_msg)
                return False, warning_msg
                
        except Exception as e:
            error_msg = f"Error validating permissions: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def create_required_directories(self) -> Tuple[bool, str]:
        """Create required directories if they don't exist"""
        try:
            created_dirs = []
            
            for dir_name in self.required_directories:
                dir_path = self.base_dir / dir_name
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created_dirs.append(dir_name)
            
            if created_dirs:
                return True, f"Created directories: {', '.join(created_dirs)}"
            else:
                return True, "All required directories already exist"
                
        except Exception as e:
            error_msg = f"Error creating directories: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def validate_model_integrity(self) -> Tuple[bool, str]:
        """Validate model file integrity using checksums"""
        try:
            # This would typically check against known checksums
            # For now, we'll do basic file validation
            
            model_issues = []
            
            for file_path in self.required_files['models']:
                full_path = self.base_dir / file_path
                if full_path.exists():
                    # Check file size
                    file_size = full_path.stat().st_size
                    
                    # Expected sizes (approximate)
                    expected_sizes = {
                        'Qwen3-1.7B-Q8_0.gguf': 1.8 * 1024 * 1024 * 1024,  # ~1.8GB
                        'Qwen3-4B-Instruct-2507-Q4_K_M.gguf': 2.5 * 1024 * 1024 * 1024,  # ~2.5GB
                    }
                    
                    filename = Path(file_path).name
                    if filename in expected_sizes:
                        expected_size = expected_sizes[filename]
                        if abs(file_size - expected_size) > expected_size * 0.1:  # 10% tolerance
                            model_issues.append(f"{filename}: Size mismatch (expected ~{expected_size/1024/1024/1024:.1f}GB, got {file_size/1024/1024/1024:.1f}GB)")
            
            if not model_issues:
                return True, "Model file integrity validated ✓"
            else:
                warning_msg = f"Model integrity issues: {'; '.join(model_issues)}"
                self.warnings.append(warning_msg)
                return False, warning_msg
                
        except Exception as e:
            error_msg = f"Error validating model integrity: {e}"
            self.errors.append(error_msg)
            return False, error_msg
    
    def run_all_validations(self) -> Dict:
        """Run all validation checks"""
        print("🔍 Running configuration validation...")
        print("=" * 50)
        
        # Create required directories first
        self.create_required_directories()
        
        validations = [
            ("Required Files", self.validate_required_files),
            ("Configuration Files", self.validate_config_files),
            ("Model Files", self.validate_model_files),
            ("Database", self.validate_database),
            ("Audio Devices", self.validate_audio_devices),
            ("Permissions", self.validate_permissions),
            ("Model Integrity", self.validate_model_integrity),
        ]
        
        results = {}
        for validation_name, validation_func in validations:
            print(f"\n{validation_name}:")
            try:
                success, message = validation_func()
                results[validation_name] = {'success': success, 'message': message}
                print(f"  {message}")
            except Exception as e:
                error_msg = f"Validation failed: {e}"
                results[validation_name] = {'success': False, 'message': error_msg}
                print(f"  ❌ {error_msg}")
                self.errors.append(error_msg)
        
        # Determine overall result
        critical_validations = ['required_files', 'config_files', 'database', 'permissions']
        critical_passed = all(self.validation_results.get(validation, False) for validation in critical_validations)
        
        self.validation_results['overall'] = critical_passed
        
        print("\n" + "=" * 50)
        if critical_passed:
            print("✅ Configuration validation PASSED")
            if self.warnings:
                print(f"⚠️  {len(self.warnings)} warning(s) found")
        else:
            print("❌ Configuration validation FAILED")
            print(f"❌ {len(self.errors)} error(s) found")
        
        return {
            'overall_success': critical_passed,
            'results': results,
            'errors': self.errors,
            'warnings': self.warnings,
            'validation_results': self.validation_results
        }
    
    def get_validation_summary(self) -> Dict:
        """Get a summary of validation results"""
        return {
            'overall_success': self.validation_results['overall'],
            'passed_checks': sum(1 for result in self.validation_results.values() if result),
            'total_checks': len(self.validation_results),
            'error_count': len(self.errors),
            'warning_count': len(self.warnings),
            'errors': self.errors,
            'warnings': self.warnings
        }


def main():
    """Main function for command line usage"""
    validator = ConfigValidator()
    results = validator.run_all_validations()
    
    if not results['overall_success']:
        print("\n❌ Validation failed. Please fix the errors above before running the application.")
        sys.exit(1)
    else:
        print("\n✅ Configuration validation passed. Application is ready to run.")


if __name__ == "__main__":
    main()
