"""
User Onboarding System
Provides guided onboarding experience for new users
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List, Optional, Callable
from enum import Enum
import json
import os
from pathlib import Path


class OnboardingStep(Enum):
    """Onboarding steps"""
    WELCOME = "welcome"
    ACCOUNT_SETUP = "account_setup"
    PREFERENCES = "preferences"
    TUTORIAL = "tutorial"
    COMPLETE = "complete"


class OnboardingManager:
    """Manages user onboarding flow"""
    
    def __init__(self, parent_widget, auth_manager):
        self.parent = parent_widget
        self.auth_manager = auth_manager
        self.current_step = OnboardingStep.WELCOME
        self.onboarding_data = {}
        self.step_handlers = {}
        self.completion_callback: Optional[Callable] = None
        
        # Onboarding state file
        self.state_file = Path("auth/cache/onboarding_state.json")
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        
        self._setup_step_handlers()
    
    def _setup_step_handlers(self):
        """Setup handlers for each onboarding step"""
        self.step_handlers = {
            OnboardingStep.WELCOME: self._show_welcome_step,
            OnboardingStep.ACCOUNT_SETUP: self._show_account_setup_step,
            OnboardingStep.PREFERENCES: self._show_preferences_step,
            OnboardingStep.TUTORIAL: self._show_tutorial_step,
            OnboardingStep.COMPLETE: self._show_complete_step
        }
    
    def start_onboarding(self, completion_callback: Optional[Callable] = None):
        """Start the onboarding process"""
        self.completion_callback = completion_callback
        self.current_step = OnboardingStep.WELCOME
        self._show_current_step()
    
    def _show_current_step(self):
        """Show the current onboarding step"""
        if self.current_step in self.step_handlers:
            self.step_handlers[self.current_step]()
    
    def _show_welcome_step(self):
        """Show welcome step"""
        self._create_onboarding_window("Welcome to Physio Assistant", self._render_welcome_content)
    
    def _show_account_setup_step(self):
        """Show account setup step"""
        self._create_onboarding_window("Account Setup", self._render_account_setup_content)
    
    def _show_preferences_step(self):
        """Show preferences step"""
        self._create_onboarding_window("Preferences", self._render_preferences_content)
    
    def _show_tutorial_step(self):
        """Show tutorial step"""
        self._create_onboarding_window("Quick Tutorial", self._render_tutorial_content)
    
    def _show_complete_step(self):
        """Show completion step"""
        self._create_onboarding_window("Setup Complete", self._render_complete_content)
    
    def _create_onboarding_window(self, title: str, content_renderer: Callable):
        """Create onboarding window"""
        # Close existing onboarding window if any
        if hasattr(self, 'onboarding_window') and self.onboarding_window:
            self.onboarding_window.destroy()
        
        # Create new window
        self.onboarding_window = tk.Toplevel(self.parent)
        self.onboarding_window.title(title)
        self.onboarding_window.geometry("600x500")
        self.onboarding_window.resizable(False, False)
        
        # Center the window
        self.onboarding_window.transient(self.parent)
        self.onboarding_window.grab_set()
        
        # Create main frame
        main_frame = ttk.Frame(self.onboarding_window, padding="30")
        main_frame.pack(fill="both", expand=True)
        
        # Render content
        content_renderer(main_frame)
    
    def _render_welcome_content(self, parent):
        """Render welcome step content"""
        # Welcome message
        welcome_label = ttk.Label(
            parent,
            text="Welcome to Physio Assistant!",
            font=("Arial", 20, "bold")
        )
        welcome_label.pack(pady=(0, 20))
        
        # Description
        desc_text = """
Thank you for choosing Physio Assistant for your clinic management needs.

This quick setup will help you:
• Configure your account preferences
• Set up your clinic information
• Learn about key features
• Get started with your first patient

Let's begin!
        """
        
        desc_label = ttk.Label(
            parent,
            text=desc_text.strip(),
            font=("Arial", 12),
            justify="left"
        )
        desc_label.pack(pady=(0, 30))
        
        # Features list
        features_frame = ttk.LabelFrame(parent, text="What you'll get:", padding="15")
        features_frame.pack(fill="x", pady=(0, 30))
        
        features = [
            "✓ Secure patient data management",
            "✓ Offline access capability",
            "✓ Appointment scheduling",
            "✓ Treatment tracking",
            "✓ Report generation"
        ]
        
        for feature in features:
            feature_label = ttk.Label(
                features_frame,
                text=feature,
                font=("Arial", 11)
            )
            feature_label.pack(anchor="w", pady=2)
        
        # Navigation buttons
        self._add_navigation_buttons(parent, show_back=False)
    
    def _render_account_setup_content(self, parent):
        """Render account setup step content"""
        # Title
        title_label = ttk.Label(
            parent,
            text="Account Setup",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_label = ttk.Label(
            parent,
            text="Let's set up your account preferences and clinic information.",
            font=("Arial", 12)
        )
        desc_label.pack(pady=(0, 20))
        
        # Account info frame
        account_frame = ttk.LabelFrame(parent, text="Account Information", padding="15")
        account_frame.pack(fill="x", pady=(0, 20))
        
        # User info (if available)
        if self.auth_manager.current_user:
            user_info = self.auth_manager.current_user
            email_label = ttk.Label(
                account_frame,
                text=f"Email: {user_info.get('email', 'N/A')}",
                font=("Arial", 11)
            )
            email_label.pack(anchor="w")
            
            user_id_label = ttk.Label(
                account_frame,
                text=f"User ID: {user_info.get('user_id', 'N/A')[:8]}...",
                font=("Arial", 11)
            )
            user_id_label.pack(anchor="w")
        
        # Clinic preferences
        clinic_frame = ttk.LabelFrame(parent, text="Clinic Preferences", padding="15")
        clinic_frame.pack(fill="x", pady=(0, 20))
        
        # Time zone selection
        ttk.Label(clinic_frame, text="Time Zone:").pack(anchor="w")
        timezone_var = tk.StringVar(value="UTC")
        timezone_combo = ttk.Combobox(
            clinic_frame,
            textvariable=timezone_var,
            values=["UTC", "EST", "PST", "CST", "MST"],
            state="readonly"
        )
        timezone_combo.pack(fill="x", pady=(0, 10))
        
        # Language selection
        ttk.Label(clinic_frame, text="Language:").pack(anchor="w")
        language_var = tk.StringVar(value="English")
        language_combo = ttk.Combobox(
            clinic_frame,
            textvariable=language_var,
            values=["English", "Spanish", "French", "German"],
            state="readonly"
        )
        language_combo.pack(fill="x")
        
        # Store preferences
        self.onboarding_data['timezone'] = timezone_var
        self.onboarding_data['language'] = language_var
        
        # Navigation buttons
        self._add_navigation_buttons(parent)
    
    def _render_preferences_content(self, parent):
        """Render preferences step content"""
        # Title
        title_label = ttk.Label(
            parent,
            text="Preferences",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_label = ttk.Label(
            parent,
            text="Configure your application preferences.",
            font=("Arial", 12)
        )
        desc_label.pack(pady=(0, 20))
        
        # Preferences frame
        prefs_frame = ttk.LabelFrame(parent, text="Application Settings", padding="15")
        prefs_frame.pack(fill="x", pady=(0, 20))
        
        # Auto-save preference
        auto_save_var = tk.BooleanVar(value=True)
        auto_save_check = ttk.Checkbutton(
            prefs_frame,
            text="Enable auto-save for patient data",
            variable=auto_save_var
        )
        auto_save_check.pack(anchor="w", pady=2)
        
        # Notifications preference
        notifications_var = tk.BooleanVar(value=True)
        notifications_check = ttk.Checkbutton(
            prefs_frame,
            text="Enable desktop notifications",
            variable=notifications_var
        )
        notifications_check.pack(anchor="w", pady=2)
        
        # Offline mode preference
        offline_var = tk.BooleanVar(value=True)
        offline_check = ttk.Checkbutton(
            prefs_frame,
            text="Enable offline mode",
            variable=offline_var
        )
        offline_check.pack(anchor="w", pady=2)
        
        # Store preferences
        self.onboarding_data['auto_save'] = auto_save_var
        self.onboarding_data['notifications'] = notifications_var
        self.onboarding_data['offline_mode'] = offline_var
        
        # Navigation buttons
        self._add_navigation_buttons(parent)
    
    def _render_tutorial_content(self, parent):
        """Render tutorial step content"""
        # Title
        title_label = ttk.Label(
            parent,
            text="Quick Tutorial",
            font=("Arial", 18, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Description
        desc_label = ttk.Label(
            parent,
            text="Here are some key features to get you started:",
            font=("Arial", 12)
        )
        desc_label.pack(pady=(0, 20))
        
        # Tutorial content
        tutorial_frame = ttk.Frame(parent)
        tutorial_frame.pack(fill="both", expand=True)
        
        # Create scrollable content
        canvas = tk.Canvas(tutorial_frame)
        scrollbar = ttk.Scrollbar(tutorial_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Tutorial steps
        tutorial_steps = [
            {
                "title": "1. Adding Patients",
                "description": "Click 'Add Patient' to create new patient records. Fill in basic information and medical history.",
                "icon": "👥"
            },
            {
                "title": "2. Scheduling Appointments",
                "description": "Use the calendar view to schedule appointments. Drag and drop to reschedule.",
                "icon": "📅"
            },
            {
                "title": "3. Treatment Tracking",
                "description": "Record treatment sessions, exercises, and progress notes for each patient.",
                "icon": "📝"
            },
            {
                "title": "4. Reports & Analytics",
                "description": "Generate reports and view analytics to track patient progress and clinic performance.",
                "icon": "📊"
            },
            {
                "title": "5. Offline Access",
                "description": "Work offline with full functionality. Data syncs when you're back online.",
                "icon": "🔌"
            }
        ]
        
        for step in tutorial_steps:
            step_frame = ttk.Frame(scrollable_frame)
            step_frame.pack(fill="x", pady=10)
            
            # Icon and title
            header_frame = ttk.Frame(step_frame)
            header_frame.pack(fill="x")
            
            icon_label = ttk.Label(header_frame, text=step["icon"], font=("Arial", 16))
            icon_label.pack(side="left", padx=(0, 10))
            
            title_label = ttk.Label(
                header_frame,
                text=step["title"],
                font=("Arial", 12, "bold")
            )
            title_label.pack(side="left")
            
            # Description
            desc_label = ttk.Label(
                step_frame,
                text=step["description"],
                font=("Arial", 11),
                wraplength=500
            )
            desc_label.pack(anchor="w", padx=(30, 0))
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Navigation buttons
        self._add_navigation_buttons(parent)
    
    def _render_complete_content(self, parent):
        """Render completion step content"""
        # Title
        title_label = ttk.Label(
            parent,
            text="Setup Complete!",
            font=("Arial", 20, "bold"),
            foreground="#4CAF50"
        )
        title_label.pack(pady=(0, 20))
        
        # Success message
        success_label = ttk.Label(
            parent,
            text="🎉 Congratulations! You're all set up and ready to use Physio Assistant.",
            font=("Arial", 14)
        )
        success_label.pack(pady=(0, 20))
        
        # Next steps
        next_steps_frame = ttk.LabelFrame(parent, text="Next Steps", padding="15")
        next_steps_frame.pack(fill="x", pady=(0, 20))
        
        next_steps = [
            "• Add your first patient",
            "• Schedule an appointment",
            "• Explore the dashboard",
            "• Check out the help section"
        ]
        
        for step in next_steps:
            step_label = ttk.Label(
                next_steps_frame,
                text=step,
                font=("Arial", 11)
            )
            step_label.pack(anchor="w", pady=2)
        
        # Save onboarding completion
        self._save_onboarding_completion()
        
        # Navigation buttons
        self._add_navigation_buttons(parent, show_next=False, next_text="Get Started")
    
    def _add_navigation_buttons(self, parent, show_back=True, show_next=True, next_text="Next"):
        """Add navigation buttons to the onboarding window"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=(20, 0))
        
        # Back button
        if show_back:
            back_button = ttk.Button(
                button_frame,
                text="Back",
                command=self._go_back
            )
            back_button.pack(side="left")
        
        # Spacer
        ttk.Frame(button_frame).pack(side="left", fill="x", expand=True)
        
        # Next/Complete button
        if show_next:
            next_button = ttk.Button(
                button_frame,
                text=next_text,
                command=self._go_next,
                style="Accent.TButton"
            )
            next_button.pack(side="right")
        else:
            complete_button = ttk.Button(
                button_frame,
                text=next_text,
                command=self._complete_onboarding,
                style="Accent.TButton"
            )
            complete_button.pack(side="right")
    
    def _go_back(self):
        """Go to previous step"""
        steps = list(OnboardingStep)
        current_index = steps.index(self.current_step)
        
        if current_index > 0:
            self.current_step = steps[current_index - 1]
            self._show_current_step()
    
    def _go_next(self):
        """Go to next step"""
        steps = list(OnboardingStep)
        current_index = steps.index(self.current_step)
        
        if current_index < len(steps) - 1:
            self.current_step = steps[current_index + 1]
            self._show_current_step()
    
    def _complete_onboarding(self):
        """Complete onboarding process"""
        self._save_onboarding_completion()
        
        if self.onboarding_window:
            self.onboarding_window.destroy()
            self.onboarding_window = None
        
        if self.completion_callback:
            self.completion_callback()
    
    def _save_onboarding_completion(self):
        """Save onboarding completion status"""
        try:
            completion_data = {
                'completed': True,
                'completed_at': str(tk.datetime.datetime.now()),
                'preferences': {
                    'timezone': self.onboarding_data.get('timezone', {}).get(),
                    'language': self.onboarding_data.get('language', {}).get(),
                    'auto_save': self.onboarding_data.get('auto_save', {}).get(),
                    'notifications': self.onboarding_data.get('notifications', {}).get(),
                    'offline_mode': self.onboarding_data.get('offline_mode', {}).get()
                }
            }
            
            with open(self.state_file, 'w') as f:
                json.dump(completion_data, f, indent=2)
                
        except Exception as e:
            print(f"Failed to save onboarding completion: {e}")
    
    def is_onboarding_completed(self) -> bool:
        """Check if onboarding has been completed"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('completed', False)
        except Exception:
            pass
        
        return False
    
    def reset_onboarding(self):
        """Reset onboarding status"""
        try:
            if self.state_file.exists():
                self.state_file.unlink()
        except Exception as e:
            print(f"Failed to reset onboarding: {e}")
    
    def get_onboarding_preferences(self) -> Dict:
        """Get saved onboarding preferences"""
        try:
            if self.state_file.exists():
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
                    return data.get('preferences', {})
        except Exception:
            pass
        
        return {}
