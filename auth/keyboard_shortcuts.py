"""
Keyboard Shortcuts System
Provides keyboard shortcuts and accessibility features for the authentication system
"""

import tkinter as tk
from tkinter import ttk
from typing import Dict, Callable, Optional, List
from enum import Enum


class ShortcutAction(Enum):
    """Available shortcut actions"""
    LOGIN = "login"
    REGISTER = "register"
    FORGOT_PASSWORD = "forgot_password"
    SWITCH_TO_LOGIN = "switch_to_login"
    SWITCH_TO_REGISTER = "switch_to_register"
    SWITCH_TO_FORGOT = "switch_to_forgot"
    CLEAR_FORM = "clear_form"
    FOCUS_EMAIL = "focus_email"
    FOCUS_PASSWORD = "focus_password"
    FOCUS_NAME = "focus_name"
    FOCUS_CLINIC = "focus_clinic"
    FOCUS_CONFIRM_PASSWORD = "focus_confirm_password"
    TOGGLE_PASSWORD_VISIBILITY = "toggle_password_visibility"
    CANCEL = "cancel"
    HELP = "help"


class KeyboardShortcuts:
    """Manages keyboard shortcuts for the authentication system"""
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.shortcuts: Dict[str, ShortcutAction] = {}
        self.action_handlers: Dict[ShortcutAction, Callable] = {}
        self.focus_widgets: Dict[str, tk.Widget] = {}
        
        self._setup_default_shortcuts()
        self._bind_shortcuts()
    
    def _setup_default_shortcuts(self):
        """Setup default keyboard shortcuts"""
        self.shortcuts = {
            # Navigation shortcuts
            '<Control-l>': ShortcutAction.SWITCH_TO_LOGIN,
            '<Control-r>': ShortcutAction.SWITCH_TO_REGISTER,
            '<Control-f>': ShortcutAction.SWITCH_TO_FORGOT,
            '<Escape>': ShortcutAction.CANCEL,
            '<F1>': ShortcutAction.HELP,
            
            # Form shortcuts
            '<Control-Return>': ShortcutAction.LOGIN,
            '<Control-Shift-Return>': ShortcutAction.REGISTER,
            '<Control-Delete>': ShortcutAction.CLEAR_FORM,
            
            # Focus shortcuts
            '<Alt-e>': ShortcutAction.FOCUS_EMAIL,
            '<Alt-p>': ShortcutAction.FOCUS_PASSWORD,
            '<Alt-n>': ShortcutAction.FOCUS_NAME,
            '<Alt-c>': ShortcutAction.FOCUS_CLINIC,
            '<Alt-d>': ShortcutAction.FOCUS_CONFIRM_PASSWORD,
            
            # Utility shortcuts
            '<Control-h>': ShortcutAction.TOGGLE_PASSWORD_VISIBILITY,
            '<Control-Shift-F>': ShortcutAction.FORGOT_PASSWORD,
        }
    
    def _bind_shortcuts(self):
        """Bind keyboard shortcuts to the parent widget"""
        for key_sequence, action in self.shortcuts.items():
            self.parent.bind(key_sequence, lambda e, a=action: self._handle_shortcut(a))
        
        # Bind global shortcuts
        self.parent.bind_all('<Control-KeyPress>', self._handle_ctrl_shortcuts)
        self.parent.bind_all('<Alt-KeyPress>', self._handle_alt_shortcuts)
    
    def _handle_shortcut(self, action: ShortcutAction):
        """Handle a keyboard shortcut action"""
        if action in self.action_handlers:
            try:
                self.action_handlers[action]()
            except Exception as e:
                print(f"Error handling shortcut {action}: {e}")
    
    def _handle_ctrl_shortcuts(self, event):
        """Handle Ctrl+key shortcuts"""
        key = event.keysym.lower()
        
        if key == 'l':
            self._handle_shortcut(ShortcutAction.SWITCH_TO_LOGIN)
        elif key == 'r':
            self._handle_shortcut(ShortcutAction.SWITCH_TO_REGISTER)
        elif key == 'f':
            self._handle_shortcut(ShortcutAction.SWITCH_TO_FORGOT)
        elif key == 'h':
            self._handle_shortcut(ShortcutAction.TOGGLE_PASSWORD_VISIBILITY)
        elif key == 'return':
            self._handle_shortcut(ShortcutAction.LOGIN)
    
    def _handle_alt_shortcuts(self, event):
        """Handle Alt+key shortcuts"""
        key = event.keysym.lower()
        
        if key == 'e':
            self._handle_shortcut(ShortcutAction.FOCUS_EMAIL)
        elif key == 'p':
            self._handle_shortcut(ShortcutAction.FOCUS_PASSWORD)
        elif key == 'n':
            self._handle_shortcut(ShortcutAction.FOCUS_NAME)
        elif key == 'c':
            self._handle_shortcut(ShortcutAction.FOCUS_CLINIC)
        elif key == 'd':
            self._handle_shortcut(ShortcutAction.FOCUS_CONFIRM_PASSWORD)
    
    def register_action_handler(self, action: ShortcutAction, handler: Callable):
        """Register a handler for a specific action"""
        self.action_handlers[action] = handler
    
    def register_focus_widget(self, widget_name: str, widget: tk.Widget):
        """Register a widget for focus shortcuts"""
        self.focus_widgets[widget_name] = widget
    
    def focus_widget(self, widget_name: str):
        """Focus a specific widget"""
        if widget_name in self.focus_widgets:
            try:
                self.focus_widgets[widget_name].focus_set()
            except tk.TclError:
                pass  # Widget might be destroyed
    
    def get_shortcut_help(self) -> List[Dict[str, str]]:
        """Get help information for all shortcuts"""
        help_info = []
        
        shortcut_descriptions = {
            ShortcutAction.SWITCH_TO_LOGIN: "Switch to login form",
            ShortcutAction.SWITCH_TO_REGISTER: "Switch to registration form",
            ShortcutAction.SWITCH_TO_FORGOT: "Switch to forgot password form",
            ShortcutAction.LOGIN: "Submit login form",
            ShortcutAction.REGISTER: "Submit registration form",
            ShortcutAction.FORGOT_PASSWORD: "Submit forgot password form",
            ShortcutAction.CLEAR_FORM: "Clear current form",
            ShortcutAction.FOCUS_EMAIL: "Focus email field",
            ShortcutAction.FOCUS_PASSWORD: "Focus password field",
            ShortcutAction.FOCUS_NAME: "Focus name field",
            ShortcutAction.FOCUS_CLINIC: "Focus clinic field",
            ShortcutAction.FOCUS_CONFIRM_PASSWORD: "Focus confirm password field",
            ShortcutAction.TOGGLE_PASSWORD_VISIBILITY: "Toggle password visibility",
            ShortcutAction.CANCEL: "Cancel/Close dialog",
            ShortcutAction.HELP: "Show help"
        }
        
        for key_sequence, action in self.shortcuts.items():
            if action in shortcut_descriptions:
                help_info.append({
                    'shortcut': key_sequence,
                    'action': action.value,
                    'description': shortcut_descriptions[action]
                })
        
        return help_info
    
    def show_shortcut_help(self):
        """Show a help dialog with all shortcuts"""
        help_window = tk.Toplevel(self.parent)
        help_window.title("Keyboard Shortcuts")
        help_window.geometry("500x400")
        help_window.resizable(False, False)
        
        # Center the window
        help_window.transient(self.parent)
        help_window.grab_set()
        
        # Create main frame
        main_frame = ttk.Frame(help_window, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="Keyboard Shortcuts",
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(0, 20))
        
        # Create scrollable frame for shortcuts
        canvas = tk.Canvas(main_frame)
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Add shortcuts
        help_info = self.get_shortcut_help()
        
        for i, shortcut_info in enumerate(help_info):
            # Create frame for each shortcut
            shortcut_frame = ttk.Frame(scrollable_frame)
            shortcut_frame.pack(fill="x", pady=2)
            
            # Shortcut key
            key_label = ttk.Label(
                shortcut_frame,
                text=shortcut_info['shortcut'],
                font=("Courier", 10, "bold"),
                foreground="#007ACC",
                width=20
            )
            key_label.pack(side="left", padx=(0, 10))
            
            # Description
            desc_label = ttk.Label(
                shortcut_frame,
                text=shortcut_info['description'],
                font=("Arial", 10)
            )
            desc_label.pack(side="left", fill="x", expand=True)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Close button
        close_button = ttk.Button(
            main_frame,
            text="Close",
            command=help_window.destroy
        )
        close_button.pack(pady=(20, 0))
        
        # Focus the help window
        help_window.focus_set()
    
    def cleanup(self):
        """Clean up keyboard shortcuts"""
        try:
            self.parent.unbind_all('<Control-KeyPress>')
            self.parent.unbind_all('<Alt-KeyPress>')
        except tk.TclError:
            pass  # Widget might be destroyed


class AccessibilityManager:
    """Manages accessibility features for the authentication system"""
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.high_contrast = False
        self.large_fonts = False
        self.screen_reader_mode = False
        
        self._setup_accessibility_features()
    
    def _setup_accessibility_features(self):
        """Setup accessibility features"""
        # Bind accessibility shortcuts
        self.parent.bind('<Control-Shift-h>', lambda e: self.toggle_high_contrast())
        self.parent.bind('<Control-Shift-l>', lambda e: self.toggle_large_fonts())
        self.parent.bind('<Control-Shift-s>', lambda e: self.toggle_screen_reader_mode())
    
    def toggle_high_contrast(self):
        """Toggle high contrast mode"""
        self.high_contrast = not self.high_contrast
        self._apply_accessibility_settings()
    
    def toggle_large_fonts(self):
        """Toggle large font mode"""
        self.large_fonts = not self.large_fonts
        self._apply_accessibility_settings()
    
    def toggle_screen_reader_mode(self):
        """Toggle screen reader mode"""
        self.screen_reader_mode = not self.screen_reader_mode
        self._apply_accessibility_settings()
    
    def _apply_accessibility_settings(self):
        """Apply accessibility settings to widgets"""
        # This would need to be implemented based on the specific widgets
        # For now, we'll just store the settings
        pass
    
    def get_accessibility_settings(self) -> Dict[str, bool]:
        """Get current accessibility settings"""
        return {
            'high_contrast': self.high_contrast,
            'large_fonts': self.large_fonts,
            'screen_reader_mode': self.screen_reader_mode
        }
    
    def set_accessibility_settings(self, settings: Dict[str, bool]):
        """Set accessibility settings"""
        self.high_contrast = settings.get('high_contrast', False)
        self.large_fonts = settings.get('large_fonts', False)
        self.screen_reader_mode = settings.get('screen_reader_mode', False)
        self._apply_accessibility_settings()
