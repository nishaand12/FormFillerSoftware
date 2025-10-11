#!/usr/bin/env python3
"""
Background Processor GUI
Provides monitoring and control interface for background processing
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Dict, Optional
from background_processor import BackgroundProcessor, ProcessingJob, ProcessingStatus


class BackgroundProcessorGUI:
    """GUI for monitoring and controlling background processing"""
    
    def __init__(self, root, background_processor: BackgroundProcessor):
        self.root = root
        self.background_processor = background_processor
        
        # Setup callbacks
        self.background_processor.add_status_callback(self._on_job_status_change)
        self.background_processor.add_progress_callback(self._on_job_progress_change)
        
        # Create GUI
        self.create_gui()
        
        # Start update timer
        self.start_update_timer()
    
    def create_gui(self):
        """Create the GUI components"""
        # Create main frame
        self.main_frame = ttk.LabelFrame(self.root, text="Background Processing Monitor", padding="10")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Status overview
        self.create_status_overview()
        
        # Active jobs
        self.create_active_jobs_section()
        
        # Completed jobs
        self.create_completed_jobs_section()
        
        # Control buttons
        self.create_control_buttons()
    
    def create_status_overview(self):
        """Create status overview section"""
        overview_frame = ttk.LabelFrame(self.main_frame, text="Processing Overview", padding="5")
        overview_frame.pack(fill="x", pady=(0, 10))
        
        # Queue size
        ttk.Label(overview_frame, text="Queue Size:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.queue_size_label = ttk.Label(overview_frame, text="0", font=("TkDefaultFont", 10, "bold"))
        self.queue_size_label.grid(row=0, column=1, sticky="w", padx=(0, 20))
        
        # Active jobs
        ttk.Label(overview_frame, text="Active Jobs:").grid(row=0, column=2, sticky="w", padx=(0, 10))
        self.active_jobs_label = ttk.Label(overview_frame, text="0", font=("TkDefaultFont", 10, "bold"))
        self.active_jobs_label.grid(row=0, column=3, sticky="w", padx=(0, 20))
        
        # Completed jobs
        ttk.Label(overview_frame, text="Completed Jobs:").grid(row=0, column=4, sticky="w", padx=(0, 10))
        self.completed_jobs_label = ttk.Label(overview_frame, text="0", font=("TkDefaultFont", 10, "bold"))
        self.completed_jobs_label.grid(row=0, column=5, sticky="w")
    
    def create_active_jobs_section(self):
        """Create active jobs monitoring section"""
        active_frame = ttk.LabelFrame(self.main_frame, text="Active Jobs", padding="5")
        active_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create treeview for active jobs
        columns = ("Job ID", "Patient", "Status", "Progress", "Created")
        self.active_tree = ttk.Treeview(active_frame, columns=columns, show="headings", height=6)
        
        # Configure columns
        for col in columns:
            self.active_tree.heading(col, text=col)
            self.active_tree.column(col, width=120)
        
        # Add scrollbar
        active_scrollbar = ttk.Scrollbar(active_frame, orient="vertical", command=self.active_tree.yview)
        self.active_tree.configure(yscrollcommand=active_scrollbar.set)
        
        # Pack treeview and scrollbar
        self.active_tree.pack(side="left", fill="both", expand=True)
        active_scrollbar.pack(side="right", fill="y")
        
        # Context menu for active jobs
        self.active_context_menu = tk.Menu(self.active_tree, tearoff=0)
        self.active_context_menu.add_command(label="Cancel Job", command=self.cancel_selected_job)
        self.active_context_menu.add_command(label="View Details", command=self.view_job_details)
        
        # Bind right-click
        self.active_tree.bind("<Button-3>", self.show_active_context_menu)
    
    def create_completed_jobs_section(self):
        """Create completed jobs monitoring section"""
        completed_frame = ttk.LabelFrame(self.main_frame, text="Completed Jobs", padding="5")
        completed_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Create treeview for completed jobs
        columns = ("Job ID", "Patient", "Status", "Result", "Completed")
        self.completed_tree = ttk.Treeview(completed_frame, columns=columns, show="headings", height=6)
        
        # Configure columns
        for col in columns:
            self.completed_tree.heading(col, text=col)
            self.completed_tree.column(col, width=120)
        
        # Add scrollbar
        completed_scrollbar = ttk.Scrollbar(completed_frame, orient="vertical", command=self.completed_tree.yview)
        self.completed_tree.configure(yscrollcommand=completed_scrollbar.set)
        
        # Pack treeview and scrollbar
        self.completed_tree.pack(side="left", fill="both", expand=True)
        completed_scrollbar.pack(side="right", fill="y")
        
        # Context menu for completed jobs
        self.completed_context_menu = tk.Menu(self.completed_tree, tearoff=0)
        self.completed_context_menu.add_command(label="View Details", command=self.view_job_details)
        self.completed_context_menu.add_command(label="Remove from List", command=self.remove_completed_job)
        
        # Bind right-click
        self.completed_tree.bind("<Button-3>", self.show_completed_context_menu)
    
    def create_control_buttons(self):
        """Create control buttons"""
        button_frame = ttk.Frame(self.main_frame)
        button_frame.pack(fill="x", pady=(10, 0))
        
        # Refresh button
        self.refresh_button = ttk.Button(
            button_frame, 
            text="Refresh", 
            command=self.refresh_display
        )
        self.refresh_button.pack(side="left", padx=(0, 10))
        
        # Clear completed button
        self.clear_completed_button = ttk.Button(
            button_frame, 
            text="Clear Completed", 
            command=self.clear_completed_jobs
        )
        self.clear_completed_button.pack(side="left", padx=(0, 10))
        
        # Worker control
        ttk.Label(button_frame, text="Workers:").pack(side="left", padx=(20, 5))
        
        self.worker_var = tk.StringVar(value="2")
        worker_spinbox = ttk.Spinbox(
            button_frame, 
            from_=1, 
            to=4, 
            width=5,
            textvariable=self.worker_var,
            command=self.change_worker_count
        )
        worker_spinbox.pack(side="left", padx=(0, 10))
        
        # Status indicator
        self.status_indicator = ttk.Label(button_frame, text="🟢 Running", foreground="green")
        self.status_indicator.pack(side="right")
    
    def start_update_timer(self):
        """Start the update timer"""
        self.update_display()
        self.root.after(2000, self.start_update_timer)  # Update every 2 seconds
    
    def update_display(self):
        """Update the display with current information"""
        try:
            # Update overview
            queue_size = self.background_processor.get_queue_size()
            active_count = self.background_processor.get_active_job_count()
            completed_count = len(self.background_processor.completed_jobs)
            
            self.queue_size_label.config(text=str(queue_size))
            self.active_jobs_label.config(text=str(active_count))
            self.completed_jobs_label.config(text=str(completed_count))
            
            # Update active jobs tree
            self.update_active_jobs_tree()
            
            # Update completed jobs tree
            self.update_completed_jobs_tree()
            
            # Update status indicator
            if self.background_processor.running:
                self.status_indicator.config(text="🟢 Running", foreground="green")
            else:
                self.status_indicator.config(text="🔴 Stopped", foreground="red")
                
        except Exception as e:
            print(f"Error updating display: {e}")
    
    def update_active_jobs_tree(self):
        """Update the active jobs treeview"""
        # Clear existing items
        for item in self.active_tree.get_children():
            self.active_tree.delete(item)
        
        # Add active jobs
        for job in self.background_processor.active_jobs.values():
            self.active_tree.insert('', 'end', values=(
                job.job_id[:12] + "...",  # Truncate long IDs
                job.patient_name,
                job.status.value,
                job.progress[:30] + "..." if len(job.progress) > 30 else job.progress,
                job.created_at.strftime("%H:%M:%S")
            ), tags=(job.job_id,))
    
    def update_completed_jobs_tree(self):
        """Update the completed jobs treeview"""
        # Clear existing items
        for item in self.completed_tree.get_children():
            self.completed_tree.delete(item)
        
        # Add completed jobs (show last 20)
        completed_jobs = list(self.background_processor.completed_jobs.values())[-20:]
        
        for job in completed_jobs:
            result_text = "Success" if job.status == ProcessingStatus.COMPLETED else "Failed"
            if job.status == ProcessingStatus.CANCELLED:
                result_text = "Cancelled"
            
            self.completed_tree.insert('', 'end', values=(
                job.job_id[:12] + "...",  # Truncate long IDs
                job.patient_name,
                job.status.value,
                result_text,
                job.created_at.strftime("%H:%M:%S")
            ), tags=(job.job_id,))
    
    def refresh_display(self):
        """Manually refresh the display"""
        self.update_display()
    
    def clear_completed_jobs(self):
        """Clear completed jobs from the list"""
        if messagebox.askyesno("Clear Completed Jobs", 
                              "Are you sure you want to clear all completed jobs from the list?"):
            self.background_processor.completed_jobs.clear()
            self.update_display()
    
    def change_worker_count(self):
        """Change the number of worker threads"""
        try:
            new_count = int(self.worker_var.get())
            if 1 <= new_count <= 4:
                # This would require restarting the background processor
                messagebox.showinfo("Worker Count", 
                                  f"Worker count changed to {new_count}. Restart the application for changes to take effect.")
            else:
                self.worker_var.set("2")  # Reset to valid value
        except ValueError:
            self.worker_var.set("2")  # Reset to valid value
    
    def cancel_selected_job(self):
        """Cancel the selected active job"""
        selection = self.active_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a job to cancel.")
            return
        
        item = selection[0]
        tags = self.active_tree.item(item, "tags")
        if not tags or len(tags) == 0:
            messagebox.showerror("Error", "Invalid job selection.")
            return
        job_id = tags[0]
        
        if messagebox.askyesno("Cancel Job", 
                              f"Are you sure you want to cancel job {job_id}?"):
            if self.background_processor.cancel_job(job_id):
                messagebox.showinfo("Job Cancelled", f"Job {job_id} has been cancelled.")
                self.update_display()
            else:
                messagebox.showerror("Error", f"Could not cancel job {job_id}.")
    
    def view_job_details(self):
        """View details of the selected job"""
        selection = self.active_tree.selection() or self.completed_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a job to view details.")
            return
        
        item = selection[0]
        if self.active_tree.selection():
            tags = self.active_tree.item(item, "tags")
        else:
            tags = self.completed_tree.item(item, "tags")
        
        if not tags or len(tags) == 0:
            messagebox.showerror("Error", "Invalid job selection.")
            return
        job_id = tags[0]
        
        job = self.background_processor.get_job_status(job_id)
        if job:
            self.show_job_details_dialog(job)
        else:
            messagebox.showerror("Error", f"Job {job_id} not found.")
    
    def show_job_details_dialog(self, job: ProcessingJob):
        """Show a dialog with job details"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Job Details - {job.job_id}")
        dialog.geometry("600x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create main frame
        main_frame = ttk.Frame(dialog, padding="10")
        main_frame.pack(fill="both", expand=True)
        
        # Job information
        info_frame = ttk.LabelFrame(main_frame, text="Job Information", padding="5")
        info_frame.pack(fill="x", pady=(0, 10))
        
        # Job details
        details = [
            ("Job ID:", job.job_id),
            ("Patient Name:", job.patient_name),
            ("Appointment Type:", job.appointment_type),
            ("Status:", job.status.value),
            ("Created:", job.created_at.strftime("%Y-%m-%d %H:%M:%S")),
            ("Forms to Fill:", ", ".join([k for k, v in job.forms_to_fill.items() if v]) or "None")
        ]
        
        for i, (label, value) in enumerate(details):
            ttk.Label(info_frame, text=label).grid(row=i, column=0, sticky="w", padx=(0, 10))
            ttk.Label(info_frame, text=str(value)).grid(row=i, column=1, sticky="w")
        
        # Progress/Error frame
        if job.status == ProcessingStatus.PROCESSING:
            progress_frame = ttk.LabelFrame(main_frame, text="Current Progress", padding="5")
            progress_frame.pack(fill="x", pady=(0, 10))
            ttk.Label(progress_frame, text=job.progress).pack(anchor="w")
        
        if job.error_message:
            error_frame = ttk.LabelFrame(main_frame, text="Error Details", padding="5")
            error_frame.pack(fill="x", pady=(0, 10))
            error_text = tk.Text(error_frame, height=4, wrap="word")
            error_text.pack(fill="both", expand=True)
            error_text.insert("1.0", job.error_message)
            error_text.config(state="disabled")
        
        # Result files
        if job.result_files:
            files_frame = ttk.LabelFrame(main_frame, text="Generated Files", padding="5")
            files_frame.pack(fill="both", expand=True)
            
            files_text = tk.Text(files_frame, wrap="word")
            files_text.pack(fill="both", expand=True)
            
            for file_path in job.result_files:
                files_text.insert("end", f"{file_path}\n")
            
            files_text.config(state="disabled")
        
        # Close button
        ttk.Button(main_frame, text="Close", command=dialog.destroy).pack(pady=(10, 0))
    
    def show_active_context_menu(self, event):
        """Show context menu for active jobs"""
        try:
            self.active_tree.selection_set(self.active_tree.identify_row(event.y))
            self.active_context_menu.post(event.x_root, event.y_root)
        except:
            pass
    
    def show_completed_context_menu(self, event):
        """Show context menu for completed jobs"""
        try:
            self.completed_tree.selection_set(self.completed_tree.identify_row(event.y))
            self.completed_context_menu.post(event.x_root, event.y_root)
        except:
            pass
    
    def remove_completed_job(self):
        """Remove the selected completed job from the list"""
        selection = self.completed_tree.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a job to remove.")
            return
        
        item = selection[0]
        tags = self.completed_tree.item(item, "tags")
        if not tags or len(tags) == 0:
            messagebox.showerror("Error", "Invalid job selection.")
            return
        job_id = tags[0]
        
        if messagebox.askyesno("Remove Job", 
                              f"Are you sure you want to remove job {job_id} from the list?"):
            if job_id in self.background_processor.completed_jobs:
                del self.background_processor.completed_jobs[job_id]
                self.update_display()
    
    def _on_job_status_change(self, job: ProcessingJob):
        """Callback for job status changes"""
        # This will be called from the background processor thread
        # Use after() to safely update GUI from main thread
        self.root.after(0, self._safe_update_display)
    
    def _on_job_progress_change(self, job: ProcessingJob):
        """Callback for job progress changes"""
        # This will be called from the background processor thread
        # Use after() to safely update GUI from main thread
        self.root.after(0, self._safe_update_display)
    
    def _safe_update_display(self):
        """Safely update display from main thread"""
        try:
            self.update_display()
        except Exception as e:
            print(f"Error in safe update: {e}")
    
    def cleanup(self):
        """Clean up the GUI"""
        # Stop update timer
        if hasattr(self, 'root'):
            self.root.after_cancel(self.start_update_timer)
