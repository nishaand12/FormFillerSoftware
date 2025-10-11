"""
Loading Animations and UI Feedback System
Provides smooth loading animations and visual feedback for user interactions
"""

import tkinter as tk
from tkinter import ttk
import threading
import time
from typing import Callable, Optional


class LoadingAnimation:
    """Animated loading indicator"""
    
    def __init__(self, parent_widget, animation_type: str = "spinner"):
        self.parent = parent_widget
        self.animation_type = animation_type
        self.is_running = False
        self.animation_thread = None
        self.widgets = {}
        
        self._create_animation_widgets()
    
    def _create_animation_widgets(self):
        """Create animation widgets based on type"""
        if self.animation_type == "spinner":
            self._create_spinner()
        elif self.animation_type == "dots":
            self._create_dots()
        elif self.animation_type == "pulse":
            self._create_pulse()
    
    def _create_spinner(self):
        """Create spinning loading indicator"""
        try:
            bg_color = self.parent.cget('bg')
        except tk.TclError:
            bg_color = 'white'
            
        self.spinner_frame = tk.Frame(self.parent, bg=bg_color)
        self.spinner_frame.pack(expand=True, fill='both')
        
        # Create canvas for spinner
        self.spinner_canvas = tk.Canvas(
            self.spinner_frame, 
            width=40, 
            height=40, 
            bg=bg_color,
            highlightthickness=0
        )
        self.spinner_canvas.pack(expand=True)
        
        # Create spinner circle
        self.spinner_canvas.create_oval(5, 5, 35, 35, outline="", fill="")
        
        self.widgets = {
            'frame': self.spinner_frame,
            'canvas': self.spinner_canvas
        }
    
    def _create_dots(self):
        """Create animated dots loading indicator"""
        try:
            bg_color = self.parent.cget('bg')
        except tk.TclError:
            bg_color = 'white'
            
        self.dots_frame = tk.Frame(self.parent, bg=bg_color)
        self.dots_frame.pack(expand=True, fill='both')
        
        # Create three dots
        self.dots = []
        for i in range(3):
            dot = tk.Label(
                self.dots_frame,
                text="●",
                font=("Arial", 16),
                fg="#007ACC",
                bg=bg_color
            )
            dot.pack(side=tk.LEFT, padx=2)
            self.dots.append(dot)
        
        self.widgets = {
            'frame': self.dots_frame,
            'dots': self.dots
        }
    
    def _create_pulse(self):
        """Create pulsing loading indicator"""
        try:
            bg_color = self.parent.cget('bg')
        except tk.TclError:
            bg_color = 'white'
            
        self.pulse_frame = tk.Frame(self.parent, bg=bg_color)
        self.pulse_frame.pack(expand=True, fill='both')
        
        # Create pulsing circle
        self.pulse_canvas = tk.Canvas(
            self.pulse_frame,
            width=40,
            height=40,
            bg=bg_color,
            highlightthickness=0
        )
        self.pulse_canvas.pack(expand=True)
        
        self.pulse_circle = self.pulse_canvas.create_oval(
            20, 20, 20, 20, 
            fill="#007ACC", 
            outline=""
        )
        
        self.widgets = {
            'frame': self.pulse_frame,
            'canvas': self.pulse_canvas,
            'circle': self.pulse_circle
        }
    
    def start(self):
        """Start the loading animation"""
        if self.is_running:
            return
        
        self.is_running = True
        self.animation_thread = threading.Thread(target=self._animate, daemon=True)
        self.animation_thread.start()
    
    def stop(self):
        """Stop the loading animation"""
        self.is_running = False
        if self.animation_thread:
            self.animation_thread.join(timeout=0.1)
    
    def _animate(self):
        """Animation loop"""
        if self.animation_type == "spinner":
            self._animate_spinner()
        elif self.animation_type == "dots":
            self._animate_dots()
        elif self.animation_type == "pulse":
            self._animate_pulse()
    
    def _animate_spinner(self):
        """Animate spinner"""
        angle = 0
        while self.is_running:
            try:
                self.spinner_canvas.delete("all")
                
                # Draw spinner arc
                self.spinner_canvas.create_arc(
                    5, 5, 35, 35,
                    start=angle,
                    extent=270,
                    outline="#007ACC",
                    width=3,
                    style="arc"
                )
                
                angle = (angle + 10) % 360
                time.sleep(0.05)
            except tk.TclError:
                # Widget destroyed
                break
    
    def _animate_dots(self):
        """Animate dots"""
        dot_states = [0, 0, 0]  # 0 = normal, 1 = highlighted
        while self.is_running:
            try:
                for i, dot in enumerate(self.dots):
                    if dot_states[i]:
                        dot.config(fg="#007ACC", font=("Arial", 18))
                    else:
                        dot.config(fg="#CCCCCC", font=("Arial", 16))
                
                # Rotate states
                dot_states = dot_states[1:] + [dot_states[0]]
                time.sleep(0.3)
            except tk.TclError:
                break
    
    def _animate_pulse(self):
        """Animate pulse"""
        size = 5
        growing = True
        while self.is_running:
            try:
                self.pulse_canvas.delete("all")
                
                # Draw pulsing circle
                self.pulse_canvas.create_oval(
                    20 - size, 20 - size, 20 + size, 20 + size,
                    fill="#007ACC",
                    outline=""
                )
                
                if growing:
                    size += 1
                    if size >= 15:
                        growing = False
                else:
                    size -= 1
                    if size <= 5:
                        growing = True
                
                time.sleep(0.1)
            except tk.TclError:
                break
    
    def destroy(self):
        """Destroy the animation widgets"""
        self.stop()
        if 'frame' in self.widgets:
            self.widgets['frame'].destroy()


class ProgressIndicator:
    """Progress bar with percentage and status text"""
    
    def __init__(self, parent_widget, width: int = 300, height: int = 20):
        self.parent = parent_widget
        self.width = width
        self.height = height
        
        self._create_widgets()
    
    def _create_widgets(self):
        """Create progress indicator widgets"""
        self.frame = tk.Frame(self.parent, bg=self.parent.cget('bg'))
        self.frame.pack(expand=True, fill='both')
        
        # Progress bar
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(
            self.frame,
            variable=self.progress_var,
            maximum=100,
            length=self.width,
            mode='determinate'
        )
        self.progress_bar.pack(pady=10)
        
        # Status text
        self.status_var = tk.StringVar(value="Ready")
        self.status_label = tk.Label(
            self.frame,
            textvariable=self.status_var,
            font=("Arial", 10),
            fg="#666666",
            bg=self.parent.cget('bg')
        )
        self.status_label.pack()
        
        # Percentage text
        self.percentage_var = tk.StringVar(value="0%")
        self.percentage_label = tk.Label(
            self.frame,
            textvariable=self.percentage_var,
            font=("Arial", 10, "bold"),
            fg="#007ACC",
            bg=self.parent.cget('bg')
        )
        self.percentage_label.pack()
    
    def set_progress(self, value: float, status: str = ""):
        """Set progress value and status"""
        self.progress_var.set(value)
        self.percentage_var.set(f"{int(value)}%")
        if status:
            self.status_var.set(status)
    
    def set_status(self, status: str):
        """Set status text only"""
        self.status_var.set(status)
    
    def reset(self):
        """Reset progress indicator"""
        self.progress_var.set(0)
        self.percentage_var.set("0%")
        self.status_var.set("Ready")
    
    def destroy(self):
        """Destroy the progress indicator"""
        self.frame.destroy()


class StatusOverlay:
    """Overlay status message on top of existing widgets"""
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.overlay = None
        self.is_visible = False
    
    def show(self, message: str, message_type: str = "info", duration: int = 3000):
        """
        Show status overlay
        
        Args:
            message: Message to display
            message_type: Type of message (info, success, warning, error)
            duration: Duration in milliseconds (0 = permanent)
        """
        self.hide()  # Hide any existing overlay
        
        # Create overlay frame
        self.overlay = tk.Frame(
            self.parent,
            bg=self._get_bg_color(message_type),
            relief="solid",
            borderwidth=1
        )
        
        # Position overlay
        self.overlay.place(relx=0.5, rely=0.1, anchor="center")
        
        # Create message label
        message_label = tk.Label(
            self.overlay,
            text=message,
            font=("Arial", 10, "bold"),
            fg=self._get_fg_color(message_type),
            bg=self._get_bg_color(message_type),
            wraplength=300
        )
        message_label.pack(padx=20, pady=10)
        
        self.is_visible = True
        
        # Auto-hide if duration specified
        if duration > 0:
            self.parent.after(duration, self.hide)
    
    def hide(self):
        """Hide status overlay"""
        if self.overlay and self.is_visible:
            self.overlay.destroy()
            self.overlay = None
            self.is_visible = False
    
    def _get_bg_color(self, message_type: str) -> str:
        """Get background color for message type"""
        colors = {
            "info": "#E3F2FD",
            "success": "#E8F5E8",
            "warning": "#FFF3E0",
            "error": "#FFEBEE"
        }
        return colors.get(message_type, colors["info"])
    
    def _get_fg_color(self, message_type: str) -> str:
        """Get foreground color for message type"""
        colors = {
            "info": "#1976D2",
            "success": "#388E3C",
            "warning": "#F57C00",
            "error": "#D32F2F"
        }
        return colors.get(message_type, colors["info"])


class LoadingManager:
    """Manages loading states across the application"""
    
    def __init__(self, parent_widget):
        self.parent = parent_widget
        self.current_loading = None
        self.status_overlay = StatusOverlay(parent_widget)
    
    def show_loading(self, message: str = "Loading...", animation_type: str = "spinner"):
        """Show loading animation with message"""
        self.hide_loading()
        
        # Create loading frame
        loading_frame = tk.Frame(self.parent, bg=self.parent.cget('bg'))
        loading_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Create loading animation
        animation = LoadingAnimation(loading_frame, animation_type)
        animation.start()
        
        # Create message label
        message_label = tk.Label(
            loading_frame,
            text=message,
            font=("Arial", 12),
            fg="#666666",
            bg=self.parent.cget('bg')
        )
        message_label.pack(pady=(10, 0))
        
        self.current_loading = {
            'frame': loading_frame,
            'animation': animation,
            'message_label': message_label
        }
    
    def hide_loading(self):
        """Hide current loading animation"""
        if self.current_loading:
            self.current_loading['animation'].destroy()
            self.current_loading['frame'].destroy()
            self.current_loading = None
    
    def show_progress(self, message: str = "Processing..."):
        """Show progress indicator"""
        self.hide_loading()
        
        # Create progress frame
        progress_frame = tk.Frame(self.parent, bg=self.parent.cget('bg'))
        progress_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Create progress indicator
        progress = ProgressIndicator(progress_frame)
        progress.set_status(message)
        
        self.current_loading = {
            'frame': progress_frame,
            'progress': progress
        }
    
    def update_progress(self, value: float, status: str = ""):
        """Update progress value"""
        if self.current_loading and 'progress' in self.current_loading:
            self.current_loading['progress'].set_progress(value, status)
    
    def show_status(self, message: str, message_type: str = "info", duration: int = 3000):
        """Show status overlay message"""
        self.status_overlay.show(message, message_type, duration)
    
    def show_success(self, message: str, duration: int = 2000):
        """Show success message"""
        self.show_status(message, "success", duration)
    
    def show_error(self, message: str, duration: int = 5000):
        """Show error message"""
        self.show_status(message, "error", duration)
    
    def show_warning(self, message: str, duration: int = 4000):
        """Show warning message"""
        self.show_status(message, "warning", duration)
    
    def show_info(self, message: str, duration: int = 3000):
        """Show info message"""
        self.show_status(message, "info", duration)
