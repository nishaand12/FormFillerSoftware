"""
Login and Registration GUI for the Physiotherapy Clinic Assistant
Handles user authentication, registration, and subscription selection
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Callable, Optional, Tuple
from .auth_manager import AuthManager
from .subscription_checker import SubscriptionChecker


class LoginGUI:
    """Login and registration interface for the application"""
    
    def __init__(self, parent: tk.Tk, on_login_success: Callable = None):
        self.parent = parent
        self.on_login_success = on_login_success
        
        # Initialize authentication components
        self.auth_manager = AuthManager()
        self.subscription_checker = SubscriptionChecker(self.auth_manager)
        
        # GUI state
        self.current_mode = "login"  # "login", "register", "forgot_password"
        self.is_loading = False
        
        # Create main window
        self.window = tk.Toplevel(parent)
        self.window.title("Physiotherapy Clinic Assistant - Login")
        self.window.geometry("500x700")
        self.window.resizable(True, True)
        self.window.minsize(500, 600)
        
        # Center the window
        self.center_window()
        
        # Make window modal
        self.window.transient(parent)
        self.window.grab_set()
        
        # Create GUI elements
        self.create_widgets()
        
        # Bind window close event
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
    
    def center_window(self):
        """Center the login window on the screen"""
        self.window.update_idletasks()
        width = self.window.winfo_width()
        height = self.window.winfo_height()
        x = (self.window.winfo_screenwidth() // 2) - (width // 2)
        y = (self.window.winfo_screenheight() // 2) - (height // 2)
        self.window.geometry(f'{width}x{height}+{x}+{y}')
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Create main canvas and scrollbar
        self.canvas = tk.Canvas(self.window)
        self.scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")
        
        # Bind mousewheel to canvas
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        
        # Main container
        main_frame = ttk.Frame(self.scrollable_frame, padding="20")
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Physiotherapy Clinic Assistant", 
                               font=("Arial", 18, "bold"))
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(main_frame, text="Secure Patient Data Management", 
                                  font=("Arial", 12))
        subtitle_label.pack(pady=(0, 30))
        
        # Mode selection buttons
        self.create_mode_buttons(main_frame)
        
        # Form container
        self.form_frame = ttk.Frame(main_frame)
        self.form_frame.pack(fill="both", expand=True, pady=(20, 0))
        
        # Create forms
        self.create_login_form()
        self.create_registration_form()
        self.create_forgot_password_form()
        
        # Status bar
        self.status_frame = ttk.Frame(main_frame)
        self.status_frame.pack(fill="x", pady=(20, 0))
        
        self.status_label = ttk.Label(self.status_frame, text="Ready", 
                                     font=("Arial", 10), foreground="gray")
        self.status_label.pack()
        
        # Show login form by default
        self.show_login_form()
    
    def create_mode_buttons(self, parent):
        """Create mode selection buttons"""
        button_frame = ttk.Frame(parent)
        button_frame.pack(pady=(0, 10))
        
        self.login_btn = ttk.Button(button_frame, text="Login", 
                                   command=self.show_login_form)
        self.login_btn.pack(side="left", padx=(0, 10))
        
        self.register_btn = ttk.Button(button_frame, text="Register", 
                                      command=self.show_registration_form)
        self.register_btn.pack(side="left", padx=(0, 10))
        
        self.forgot_btn = ttk.Button(button_frame, text="Forgot Password?", 
                                    command=self.show_forgot_password_form)
        self.forgot_btn.pack(side="left")
    
    def create_login_form(self):
        """Create login form"""
        self.login_form = ttk.Frame(self.form_frame)
        
        # Email field
        ttk.Label(self.login_form, text="Email:").pack(anchor="w", pady=(0, 5))
        self.login_email_var = tk.StringVar()
        self.login_email_entry = ttk.Entry(self.login_form, textvariable=self.login_email_var, 
                                          width=40, font=("Arial", 11))
        self.login_email_entry.pack(pady=(0, 15))
        
        # Password field
        ttk.Label(self.login_form, text="Password:").pack(anchor="w", pady=(0, 5))
        self.login_password_var = tk.StringVar()
        self.login_password_entry = ttk.Entry(self.login_form, textvariable=self.login_password_var, 
                                             width=40, font=("Arial", 11), show="*")
        self.login_password_entry.pack(pady=(0, 20))
        
        # Login button
        self.login_submit_btn = ttk.Button(self.login_form, text="Login", 
                                          command=self.handle_login, style="Accent.TButton")
        self.login_submit_btn.pack(pady=(0, 10))
        
        # Bind Enter key
        self.login_password_entry.bind('<Return>', lambda e: self.handle_login())
    
    def create_registration_form(self):
        """Create registration form"""
        self.register_form = ttk.Frame(self.form_frame)
        
        # Full Name field
        ttk.Label(self.register_form, text="Full Name:").pack(anchor="w", pady=(0, 5))
        self.register_name_var = tk.StringVar()
        self.register_name_entry = ttk.Entry(self.register_form, textvariable=self.register_name_var, 
                                            width=40, font=("Arial", 11))
        self.register_name_entry.pack(pady=(0, 15))
        
        # Email field
        ttk.Label(self.register_form, text="Email:").pack(anchor="w", pady=(0, 5))
        self.register_email_var = tk.StringVar()
        self.register_email_entry = ttk.Entry(self.register_form, textvariable=self.register_email_var, 
                                             width=40, font=("Arial", 11))
        self.register_email_entry.pack(pady=(0, 15))
        
        # Clinic Name field
        ttk.Label(self.register_form, text="Clinic Name:").pack(anchor="w", pady=(0, 5))
        self.register_clinic_var = tk.StringVar()
        self.register_clinic_entry = ttk.Entry(self.register_form, textvariable=self.register_clinic_var, 
                                              width=40, font=("Arial", 11))
        self.register_clinic_entry.pack(pady=(0, 15))
        
        # Password field
        ttk.Label(self.register_form, text="Password:").pack(anchor="w", pady=(0, 5))
        self.register_password_var = tk.StringVar()
        self.register_password_entry = ttk.Entry(self.register_form, textvariable=self.register_password_var, 
                                                width=40, font=("Arial", 11), show="*")
        self.register_password_entry.pack(pady=(0, 15))
        
        # Confirm Password field
        ttk.Label(self.register_form, text="Confirm Password:").pack(anchor="w", pady=(0, 5))
        self.register_confirm_var = tk.StringVar()
        self.register_confirm_entry = ttk.Entry(self.register_form, textvariable=self.register_confirm_var, 
                                               width=40, font=("Arial", 11), show="*")
        self.register_confirm_entry.pack(pady=(0, 20))
        
        # Subscription selection
        self.create_subscription_selection()
        
        # Register button
        self.register_submit_btn = ttk.Button(self.register_form, text="Create Account", 
                                             command=self.handle_registration, style="Accent.TButton")
        self.register_submit_btn.pack(pady=(0, 10))
        
        # Bind Enter key
        self.register_confirm_entry.bind('<Return>', lambda e: self.handle_registration())
    
    def create_subscription_selection(self):
        """Create subscription selection interface"""
        # Subscription info frame
        sub_frame = ttk.LabelFrame(self.register_form, text="Subscription Plan", padding="10")
        sub_frame.pack(fill="x", pady=(0, 20))
        
        # Single subscription option (as requested)
        self.subscription_var = tk.StringVar(value="basic")
        
        # Premium plan option
        plan_frame = ttk.Frame(sub_frame)
        plan_frame.pack(fill="x")
        
        ttk.Radiobutton(plan_frame, text="Premium Plan", variable=self.subscription_var, 
                       value="premium").pack(anchor="w")
        
        # Plan details
        plan_details = ttk.Label(plan_frame, 
                                text="• Unlimited appointments\n• All form types\n• $25/month",
                                font=("Arial", 9), foreground="gray")
        plan_details.pack(anchor="w", padx=(20, 0), pady=(5, 0))
        
        # Trial info
        trial_info = ttk.Label(sub_frame, 
                              text="14-day free trial included with all plans",
                              font=("Arial", 9), foreground="blue")
        trial_info.pack(pady=(10, 0))
    
    def create_forgot_password_form(self):
        """Create forgot password form"""
        self.forgot_form = ttk.Frame(self.form_frame)
        
        # Instructions
        instructions = ttk.Label(self.forgot_form, 
                                text="Enter your email address and we'll send you a password reset link.",
                                font=("Arial", 10), foreground="gray")
        instructions.pack(pady=(0, 20))
        
        # Email field
        ttk.Label(self.forgot_form, text="Email:").pack(anchor="w", pady=(0, 5))
        self.forgot_email_var = tk.StringVar()
        self.forgot_email_entry = ttk.Entry(self.forgot_form, textvariable=self.forgot_email_var, 
                                           width=40, font=("Arial", 11))
        self.forgot_email_entry.pack(pady=(0, 20))
        
        # Reset button
        self.forgot_submit_btn = ttk.Button(self.forgot_form, text="Send Reset Link", 
                                           command=self.handle_forgot_password, style="Accent.TButton")
        self.forgot_submit_btn.pack(pady=(0, 10))
        
        # Back to login
        back_btn = ttk.Button(self.forgot_form, text="Back to Login", 
                             command=self.show_login_form)
        back_btn.pack()
        
        # Bind Enter key
        self.forgot_email_entry.bind('<Return>', lambda e: self.handle_forgot_password())
    
    def show_login_form(self):
        """Show login form"""
        self.current_mode = "login"
        self.hide_all_forms()
        self.login_form.pack(fill="both", expand=True)
        self.update_mode_buttons()
        self.login_email_entry.focus()
    
    def show_registration_form(self):
        """Show registration form"""
        self.current_mode = "register"
        self.hide_all_forms()
        self.register_form.pack(fill="both", expand=True)
        self.update_mode_buttons()
        self.register_name_entry.focus()
    
    def show_forgot_password_form(self):
        """Show forgot password form"""
        self.current_mode = "forgot_password"
        self.hide_all_forms()
        self.forgot_form.pack(fill="both", expand=True)
        self.update_mode_buttons()
        self.forgot_email_entry.focus()
    
    def hide_all_forms(self):
        """Hide all forms"""
        for form in [self.login_form, self.register_form, self.forgot_form]:
            form.pack_forget()
    
    def update_mode_buttons(self):
        """Update mode button states"""
        self.login_btn.config(state="normal")
        self.register_btn.config(state="normal")
        self.forgot_btn.config(state="normal")
        
        if self.current_mode == "login":
            self.login_btn.config(state="disabled")
        elif self.current_mode == "register":
            self.register_btn.config(state="disabled")
        elif self.current_mode == "forgot_password":
            self.forgot_btn.config(state="disabled")
    
    def set_loading_state(self, loading: bool):
        """Set loading state for all buttons"""
        self.is_loading = loading
        
        state = "disabled" if loading else "normal"
        
        self.login_submit_btn.config(state=state)
        self.register_submit_btn.config(state=state)
        self.forgot_submit_btn.config(state=state)
        
        if loading:
            self.status_label.config(text="Processing...", foreground="blue")
        else:
            self.status_label.config(text="Ready", foreground="gray")
    
    def validate_email(self, email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    def validate_password(self, password: str) -> Tuple[bool, str]:
        """Validate password strength"""
        if len(password) < 6:
            return False, "Password must be at least 6 characters long"
        
        if len(password) > 100:
            return False, "Password is too long"
        
        return True, "Password is valid"
    
    def handle_login(self):
        """Handle login form submission"""
        if self.is_loading:
            return
        
        # Get form data
        email = self.login_email_var.get().strip()
        password = self.login_password_var.get()
        
        # Validate inputs
        if not email:
            messagebox.showerror("Error", "Please enter your email address")
            self.login_email_entry.focus()
            return
        
        if not password:
            messagebox.showerror("Error", "Please enter your password")
            self.login_password_entry.focus()
            return
        
        if not self.validate_email(email):
            messagebox.showerror("Error", "Please enter a valid email address")
            self.login_email_entry.focus()
            return
        
        # Set loading state
        self.set_loading_state(True)
        
        # Run login in background thread
        thread = threading.Thread(target=self._login_thread, args=(email, password))
        thread.daemon = True
        thread.start()
    
    def _login_thread(self, email: str, password: str):
        """Login thread"""
        try:
            success, message = self.auth_manager.login_user(email, password)
            
            # Update UI in main thread
            self.window.after(0, self._handle_login_result, success, message)
            
        except Exception as e:
            self.window.after(0, self._handle_login_result, False, f"Login failed: {str(e)}")
    
    def _handle_login_result(self, success: bool, message: str):
        """Handle login result"""
        self.set_loading_state(False)
        
        if success:
            messagebox.showinfo("Success", message)
            self.window.destroy()
            if self.on_login_success:
                self.on_login_success()
        else:
            messagebox.showerror("Login Failed", message)
            self.login_password_var.set("")  # Clear password field
            self.login_password_entry.focus()
    
    def handle_registration(self):
        """Handle registration form submission"""
        if self.is_loading:
            return
        
        # Get form data
        full_name = self.register_name_var.get().strip()
        email = self.register_email_var.get().strip()
        clinic_name = self.register_clinic_var.get().strip()
        password = self.register_password_var.get()
        confirm_password = self.register_confirm_var.get()
        subscription_plan = self.subscription_var.get()
        
        # Basic validation
        if not full_name:
            messagebox.showerror("Registration Error", "Please enter your full name")
            self.register_name_entry.focus()
            return
        
        if not email:
            messagebox.showerror("Registration Error", "Please enter your email address")
            self.register_email_entry.focus()
            return
        
        if not clinic_name:
            messagebox.showerror("Registration Error", "Please enter your clinic name")
            self.register_clinic_entry.focus()
            return
        
        if not password:
            messagebox.showerror("Registration Error", "Please enter a password")
            self.register_password_entry.focus()
            return
        
        if password != confirm_password:
            messagebox.showerror("Registration Error", "Passwords do not match")
            self.register_confirm_entry.focus()
            return
        
        # Validate email format
        if not self.validate_email(email):
            messagebox.showerror("Registration Error", "Please enter a valid email address")
            self.register_email_entry.focus()
            return
        
        password_valid, password_msg = self.validate_password(password)
        if not password_valid:
            messagebox.showerror("Error", password_msg)
            self.register_password_entry.focus()
            return
        
        # Set loading state
        self.set_loading_state(True)
        
        # Run registration in background thread
        thread = threading.Thread(target=self._registration_thread, 
                                 args=(email, password, full_name, clinic_name, subscription_plan))
        thread.daemon = True
        thread.start()
    
    def _registration_thread(self, email: str, password: str, full_name: str, 
                           clinic_name: str, subscription_plan: str):
        """Registration thread"""
        try:
            success, message = self.auth_manager.register_user(email, password, full_name, clinic_name)
            
            # Update UI in main thread
            self.window.after(0, self._handle_registration_result, success, message)
            
        except Exception as e:
            self.window.after(0, self._handle_registration_result, False, f"Registration failed: {str(e)}")
    
    def _handle_registration_result(self, success: bool, message: str):
        """Handle registration result"""
        self.set_loading_state(False)
        
        if success:
            messagebox.showinfo("Success", message)
            # Clear form and switch to login
            self.clear_registration_form()
            self.show_login_form()
        else:
            messagebox.showerror("Registration Failed", message)
            self.register_password_var.set("")  # Clear password fields
            self.register_confirm_var.set("")
            self.register_password_entry.focus()
    
    def clear_registration_form(self):
        """Clear registration form fields"""
        self.register_name_var.set("")
        self.register_email_var.set("")
        self.register_clinic_var.set("")
        self.register_password_var.set("")
        self.register_confirm_var.set("")
    
    def handle_forgot_password(self):
        """Handle forgot password form submission"""
        if self.is_loading:
            return
        
        # Get form data
        email = self.forgot_email_var.get().strip()
        
        # Validate input
        if not email:
            messagebox.showerror("Error", "Please enter your email address")
            self.forgot_email_entry.focus()
            return
        
        if not self.validate_email(email):
            messagebox.showerror("Error", "Please enter a valid email address")
            self.forgot_email_entry.focus()
            return
        
        # Set loading state
        self.set_loading_state(True)
        
        # Run forgot password in background thread
        thread = threading.Thread(target=self._forgot_password_thread, args=(email,))
        thread.daemon = True
        thread.start()
    
    def _forgot_password_thread(self, email: str):
        """Forgot password thread"""
        try:
            # Use auth manager's reset password method
            success, message = self.auth_manager.reset_password(email)
            
            if success:
                message = f"{message}\n\nPlease check your email and click the link to reset your password."
            
            # Update UI in main thread
            self.window.after(0, self._handle_forgot_password_result, success, message)
            
        except Exception as e:
            self.window.after(0, self._handle_forgot_password_result, False, f"Failed to send reset email: {str(e)}")
    
    def _handle_forgot_password_result(self, success: bool, message: str):
        """Handle forgot password result"""
        self.set_loading_state(False)
        
        if success:
            messagebox.showinfo("Password Reset", message)
            self.forgot_email_var.set("")
            self.show_login_form()
        else:
            messagebox.showerror("Error", message)
            self.forgot_email_entry.focus()
    
    def _on_mousewheel(self, event):
        """Handle mousewheel scrolling"""
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    
    def on_close(self):
        """Handle window close"""
        if self.is_loading:
            messagebox.showwarning("Warning", "Please wait for the current operation to complete.")
            return
        
        # Close the application if login window is closed
        self.parent.quit()
    
    def show_login(self):
        """Show the login window (public method)"""
        self.window.deiconify()
        self.window.lift()
        self.window.focus_force()
        self.show_login_form()


def show_login_dialog(parent: tk.Tk, on_login_success: Callable = None) -> LoginGUI:
    """Show login dialog and return the LoginGUI instance"""
    return LoginGUI(parent, on_login_success)
