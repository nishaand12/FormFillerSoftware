#!/usr/bin/env python3
"""
Background Processor for Asynchronous Audio Processing
Handles multiple recordings in parallel using a queue system
"""

import os
import time
import threading
import queue
import logging
from datetime import datetime
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum

# Import existing components
from transcriber import Transcriber
from wsib_data_extractor import WSIBDataExtractor
from wsib_form_filler import WSIBFormFiller
from ocf18_data_extractor import OCF18DataExtractor
from ocf18_form_filler import OCF18FormFiller
from ocf23_data_extractor import OCF23DataExtractor
from ocf23_form_filler import OCF23FormFiller
import json
from database_manager import DatabaseManager
from model_manager import model_manager


class ProcessingStatus(Enum):
    """Status of processing jobs"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProcessingJob:
    """Represents a processing job"""
    job_id: str
    appointment_id: str
    recording_path: str
    patient_name: str
    appointment_type: str
    appointment_notes: str
    forms_to_fill: Dict[str, bool]
    created_at: datetime
    status: ProcessingStatus = ProcessingStatus.PENDING
    progress: str = ""
    error_message: str = ""
    result_files: List[str] = None
    
    def __post_init__(self):
        if self.result_files is None:
            self.result_files = []


class BackgroundProcessor:
    """
    Background processor that handles multiple recordings asynchronously
    """
    
    def __init__(self, db_manager: DatabaseManager, auth_manager=None, max_workers: int = 2):
        self.db_manager = db_manager
        self.auth_manager = auth_manager
        self.max_workers = max_workers
        
        # Initialize components
        self.transcriber = Transcriber()
        self.extractor = WSIBDataExtractor(model_type="qwen3-4b")  # Default to 4B model
        self.form_filler = WSIBFormFiller()
        self.ocf18_extractor = OCF18DataExtractor(model_type="qwen3-4b")  # Default to 4B model
        self.ocf18_form_filler = OCF18FormFiller()
        self.ocf23_extractor = OCF23DataExtractor(model_type="qwen3-4b")  # Default to 4B model
        self.ocf23_form_filler = OCF23FormFiller()
        
        # Queue and worker management
        self.job_queue = queue.Queue()
        self.workers = []
        self.active_jobs: Dict[str, ProcessingJob] = {}
        self.completed_jobs: Dict[str, ProcessingJob] = {}
        
        # Threading control
        self.running = False
        self.shutdown_event = threading.Event()
        
        # Status callbacks
        self.status_callbacks: List[Callable] = []
        self.progress_callbacks: List[Callable] = []
        
        # Setup logging
        self.setup_logging()
        
        # Start worker threads
        self.start_workers()
    
    def setup_logging(self):
        """Setup logging for the background processor with rotation"""
        from logging.handlers import RotatingFileHandler
        
        # Create logger
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # File handler with rotation (10MB max, keep 5 backups)
        file_handler = RotatingFileHandler(
            'logs/background_processor.log',
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)
    
    def start_workers(self):
        """Start worker threads"""
        self.running = True
        self.shutdown_event.clear()
        
        for i in range(self.max_workers):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"ProcessorWorker-{i}",
                daemon=True
            )
            worker.start()
            self.workers.append(worker)
            self.logger.info(f"Started worker thread {i}")
    
    def stop_workers(self):
        """Stop all worker threads"""
        self.logger.info("Stopping worker threads...")
        self.running = False
        self.shutdown_event.set()
        
        # Wait for workers to finish
        for worker in self.workers:
            if worker.is_alive():
                worker.join(timeout=5.0)
                if worker.is_alive():
                    self.logger.warning(f"Worker {worker.name} did not stop gracefully")
        
        self.workers.clear()
        self.logger.info("All worker threads stopped")
    
    def _worker_loop(self):
        """Main worker loop that processes jobs from the queue"""
        while self.running and not self.shutdown_event.is_set():
            try:
                # Get job from queue with timeout
                job = self.job_queue.get(timeout=1.0)
                if job is None:  # Shutdown signal
                    break
                
                self.logger.info(f"Worker processing job: {job.job_id}")
                self._process_job(job)
                
                # Mark job as done
                self.job_queue.task_done()
                
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"Worker error: {e}")
                continue
    
    def add_job(self, appointment_id: str, recording_path: str, patient_name: str, 
                appointment_type: str, appointment_notes: str, forms_to_fill: Dict[str, bool]) -> str:
        """
        Add a new processing job to the queue
        
        Returns:
            str: Job ID for tracking
        """
        job_id = f"{appointment_id}_{int(time.time())}"
        
        job = ProcessingJob(
            job_id=job_id,
            appointment_id=appointment_id,
            recording_path=recording_path,
            patient_name=patient_name,
            appointment_type=appointment_type,
            appointment_notes=appointment_notes,
            forms_to_fill=forms_to_fill,
            created_at=datetime.now()
        )
        
        # Add to active jobs
        self.active_jobs[job_id] = job
        
        # Add to queue
        self.job_queue.put(job)
        
        self.logger.info(f"Added job {job_id} to queue. Queue size: {self.job_queue.qsize()}")
        
        # Notify status change
        self._notify_status_change(job)
        
        return job_id
    
    def _process_job(self, job: ProcessingJob):
        """Process a single job through all stages"""
        try:
            job.status = ProcessingStatus.PROCESSING
            self._notify_status_change(job)
            
            # Step 1: Create appointment in database
            self._update_progress(job, "Creating appointment in database...")
            db_appointment_id = self._create_appointment(job)
            
            # Step 2: Move recording to appointment folder
            self._update_progress(job, "Organizing files...")
            recording_path = self._organize_files(job, db_appointment_id)
            
            # Step 3: Transcribe audio (ALWAYS happens)
            self._update_progress(job, "Transcribing audio...")
            transcript_path = self._transcribe_audio(job, recording_path, db_appointment_id)
            
            # Check if any forms are selected for filling
            forms_selected = any(job.forms_to_fill.values())
            
            if forms_selected:
                # Process WSIB form if selected
                if job.forms_to_fill.get('wsib', False):
                    self._update_progress(job, "Extracting WSIB data from transcript...")
                    wsib_extraction_path = self._extract_wsib_data(job, transcript_path, db_appointment_id)

                    self._update_progress(job, "Filling WSIB forms...")
                    wsib_form_paths = self._fill_wsib_forms(job, wsib_extraction_path, db_appointment_id)
                    job.result_files.extend(wsib_form_paths)

                # Process OCF-18 form if selected
                if job.forms_to_fill.get('ocf18', False):
                    self._update_progress(job, "Extracting OCF-18 data from transcript...")
                    ocf18_extraction_path = self._extract_ocf18_data(job, transcript_path, db_appointment_id)

                    self._update_progress(job, "Filling OCF-18 form...")
                    ocf18_form_path = self._fill_ocf18_form(job, ocf18_extraction_path, db_appointment_id)
                    if ocf18_form_path:
                        job.result_files.append(ocf18_form_path)

                # Process OCF-23 form if selected
                if job.forms_to_fill.get('ocf23', False):
                    self._update_progress(job, "Extracting OCF-23 data from transcript...")
                    ocf23_extraction_path = self._extract_ocf23_data(job, transcript_path, db_appointment_id)

                    self._update_progress(job, "Filling OCF-23 form...")
                    ocf23_form_path = self._fill_ocf23_form(job, ocf23_extraction_path, db_appointment_id)
                    if ocf23_form_path:
                        job.result_files.append(ocf23_form_path)

                self._update_progress(job, "Processing completed successfully with forms")
            else:
                # No forms selected - skip extraction and form filling
                self._update_progress(job, "No forms selected - transcription completed")
                print(f"ℹ️  No forms selected for job {job.job_id} - skipping extraction and form filling")
            
            # Step 6: Mark as completed
            job.status = ProcessingStatus.COMPLETED
            
            # Move to completed jobs
            self.completed_jobs[job.job_id] = job
            del self.active_jobs[job.job_id]
            
            self.logger.info(f"Job {job.job_id} completed successfully")
            
        except Exception as e:
            self.logger.error(f"Job {job.job_id} failed: {e}")
            job.status = ProcessingStatus.FAILED
            job.error_message = str(e)
            self._update_progress(job, f"Error: {str(e)}")
            
            # Move to completed jobs (failed)
            self.completed_jobs[job.job_id] = job
            del self.active_jobs[job.job_id]
        
        finally:
            # Always notify status change
            self._notify_status_change(job)
    
    def _get_user_id(self) -> str:
        """Get the current user ID, raising an exception if not authenticated"""
        if not self.auth_manager:
            raise Exception("Authentication manager not available")
        return self.auth_manager.get_required_user_id()
    
    def update_model_type(self, model_type: str):
        """Update the model type for all extractors"""
        try:
            self.logger.info(f"Updating background processor model type to: {model_type}")
            
            # Update all extractors with new model type
            self.extractor = WSIBDataExtractor(model_type=model_type)
            self.ocf18_extractor = OCF18DataExtractor(model_type=model_type)
            self.ocf23_extractor = OCF23DataExtractor(model_type=model_type)
            
            self.logger.info(f"Background processor model type updated to: {model_type}")
            
        except Exception as e:
            self.logger.error(f"Failed to update background processor model type: {e}")
            raise
    
    def _create_appointment(self, job: ProcessingJob) -> int:
        """Create appointment in database"""
        try:
            # Generate current time automatically
            appointment_time = datetime.now().strftime('%H%M%S')
            appointment_date = datetime.now().strftime('%Y-%m-%d')
            
            # Get current user ID - this is required
            user_id = self._get_user_id()
            
            # Create appointment in database
            db_appointment_id = self.db_manager.create_appointment(
                patient_name=job.patient_name,
                appointment_date=appointment_date,
                appointment_time=appointment_time,
                appointment_type=job.appointment_type,
                notes=job.appointment_notes,
                user_id=user_id
            )
            
            # Update processing status
            self.db_manager.update_processing_status(db_appointment_id, "recording", "completed")
            
            return db_appointment_id
            
        except Exception as e:
            raise Exception(f"Failed to create appointment: {e}")
    
    def _organize_files(self, job: ProcessingJob, db_appointment_id: int) -> str:
        """Organize files into appointment folder"""
        try:
            # Get appointment information
            user_id = self._get_user_id()
            appointment = self.db_manager.get_appointment(db_appointment_id, user_id)
            appointment_folder = appointment['folder_path']
            
            # Ensure date folder exists
            appointment_date = datetime.now().strftime('%Y-%m-%d')
            self.db_manager.ensure_date_folder_exists(appointment_date)
            
            # Create appointment folder
            os.makedirs(appointment_folder, exist_ok=True)
            
            # Move recording to appointment folder
            new_recording_path = os.path.join(appointment_folder, "recording.wav")
            if os.path.exists(job.recording_path):
                import shutil
                shutil.move(job.recording_path, new_recording_path)
                recording_path = new_recording_path
            else:
                recording_path = job.recording_path
            
            # Add recording file to database
            self.db_manager.add_file(
                appointment_id=db_appointment_id,
                file_type="recording",
                file_path=recording_path,
                retention_policy="2_weeks",
                user_id=user_id
            )
            
            return recording_path
            
        except Exception as e:
            raise Exception(f"Failed to organize files: {e}")
    
    def _transcribe_audio(self, job: ProcessingJob, recording_path: str, db_appointment_id: int) -> str:
        """Transcribe audio file"""
        try:
            # Get appointment folder
            user_id = self._get_user_id()
            appointment = self.db_manager.get_appointment(db_appointment_id, user_id)
            appointment_folder = appointment['folder_path']
            
            # Update processing status
            self.db_manager.update_processing_status(db_appointment_id, "transcription", "processing")
            
            # Save transcript to appointment folder
            transcript_path = os.path.join(appointment_folder, "transcript.txt")
            self.transcriber.transcribe(recording_path, job.appointment_id, transcript_path)
            
            # Add transcript to database
            self.db_manager.add_file(
                appointment_id=db_appointment_id,
                file_type="transcript",
                file_path=transcript_path,
                retention_policy="1_month",
                user_id=user_id
            )
            
            # Update processing status
            self.db_manager.update_processing_status(db_appointment_id, "transcription", "completed")
            
            return transcript_path
            
        except Exception as e:
            raise Exception(f"Failed to transcribe audio: {e}")
    
    def _extract_wsib_data(self, job: ProcessingJob, transcript_path: str, db_appointment_id: int) -> str:
        """Extract WSIB data from transcript using Qwen model"""
        try:
            # Get appointment folder
            user_id = self._get_user_id()
            appointment = self.db_manager.get_appointment(db_appointment_id, user_id)
            appointment_folder = appointment['folder_path']
            
            # Update processing status
            self.db_manager.update_processing_status(db_appointment_id, "extraction", "processing")
            
            # Save extraction to appointment folder
            extraction_path = os.path.join(appointment_folder, "extraction.json")
            
            # Extract WSIB data using selected model
            extracted_data = self.extractor.extract_data(transcript_path, job.appointment_id, extraction_path)
            
            if not extracted_data:
                raise Exception("No WSIB data extracted from transcript")
            
            # Add extraction to database
            self.db_manager.add_file(
                appointment_id=db_appointment_id,
                file_type="extraction",
                file_path=extraction_path,
                retention_policy="1_month",
                user_id=user_id
            )
            
            # Update processing status
            self.db_manager.update_processing_status(db_appointment_id, "extraction", "completed")
            
            return extraction_path
            
        except Exception as e:
            raise Exception(f"Failed to extract WSIB data: {e}")
    
    def _fill_wsib_forms(self, job: ProcessingJob, extraction_path: str, db_appointment_id: int) -> List[str]:
        """Fill WSIB forms based on extracted data"""
        try:
            # Get appointment folder
            user_id = self._get_user_id()
            appointment = self.db_manager.get_appointment(db_appointment_id, user_id)
            appointment_folder = appointment['folder_path']
            
            # Update processing status
            self.db_manager.update_processing_status(db_appointment_id, "form_filling", "processing")
            
            form_paths = []
            
            # Fill WSIB form if requested
            if job.forms_to_fill.get('wsib', False):
                wsib_template = "forms/templates/wsib_faf_template.pdf"
                if not os.path.exists(wsib_template):
                    raise Exception(f"WSIB template not found at {wsib_template}")
                
                output_path = os.path.join(appointment_folder, "wsib_form.pdf")
                
                # Load the extraction data from the JSON file
                import json
                with open(extraction_path, 'r', encoding='utf-8') as f:
                    extraction_data = json.load(f)
                
                success = self.form_filler.fill_wsib_form(wsib_template, extraction_data, output_path)
                
                if success:
                    # Add form to database
                    self.db_manager.add_file(
                        appointment_id=db_appointment_id,
                        file_type="wsib_form",
                        file_path=output_path,
                        retention_policy="long_term",
                        user_id=user_id
                    )
                    form_paths.append(output_path)
                    print(f"✅ WSIB form filled successfully: {output_path}")
                else:
                    raise Exception("Failed to fill WSIB form")
            
            # Note: OCF-23 handled separately to avoid impacting WSIB flow
            
            # Update processing status
            if form_paths:
                self.db_manager.update_processing_status(db_appointment_id, "form_filling", "completed")
                print(f"✅ {len(form_paths)} forms filled successfully")
            else:
                # No forms were selected or filled
                self.db_manager.update_processing_status(db_appointment_id, "form_filling", "skipped")
                print("ℹ️  No forms were selected for filling")
            
            return form_paths
            
        except Exception as e:
            raise Exception(f"Failed to fill forms: {e}")

    def _extract_ocf23_data(self, job: ProcessingJob, transcript_path: str, db_appointment_id: int) -> str:
        """Extract OCF-23 data using the dedicated extractor"""
        try:
            user_id = self._get_user_id()
            appointment = self.db_manager.get_appointment(db_appointment_id, user_id)
            appointment_folder = appointment['folder_path']

            # Track OCF-23 extraction step
            self.db_manager.update_processing_status(db_appointment_id, "ocf23_extraction", "processing")

            extraction_path = os.path.join(appointment_folder, "ocf23_extraction.json")

            extracted_data = self.ocf23_extractor.extract_data(transcript_path, job.appointment_id, extraction_path)
            if not extracted_data:
                raise Exception("No OCF-23 data extracted from transcript")

            self.db_manager.add_file(
                appointment_id=db_appointment_id,
                file_type="ocf23_extraction",
                file_path=extraction_path,
                retention_policy="1_month",
                user_id=user_id
            )

            # Update OCF-23 extraction status to completed
            self.db_manager.update_processing_status(db_appointment_id, "ocf23_extraction", "completed")
            
            return extraction_path
        except Exception as e:
            raise Exception(f"Failed to extract OCF-23 data: {e}")

    def _fill_ocf23_form(self, job: ProcessingJob, ocf23_extraction_path: str, db_appointment_id: int) -> Optional[str]:
        """Fill OCF-23 form using the dedicated filler"""
        try:
            user_id = self._get_user_id()
            appointment = self.db_manager.get_appointment(db_appointment_id, user_id)
            appointment_folder = appointment['folder_path']

            ocf23_template = "forms/templates/fsra_ocf23_template.pdf"
            if not os.path.exists(ocf23_template):
                raise Exception(f"OCF-23 template not found at {ocf23_template}")

            with open(ocf23_extraction_path, 'r', encoding='utf-8') as f:
                ocf23_extraction = json.load(f)

            output_path = os.path.join(appointment_folder, "ocf23_form.pdf")
            success = self.ocf23_form_filler.fill_ocf23_form(ocf23_template, ocf23_extraction, output_path)

            if success:
                self.db_manager.add_file(
                    appointment_id=db_appointment_id,
                    file_type="ocf23_form",
                    file_path=output_path,
                    retention_policy="long_term",
                    user_id=user_id
                )
                
                # Update OCF-23 form filling status
                self.db_manager.update_processing_status(db_appointment_id, "ocf23_form_filling", "completed")
                
                print(f"✅ OCF-23 form filled successfully: {output_path}")
                return output_path
            else:
                raise Exception("Failed to fill OCF-23 form")
        except Exception as e:
            raise Exception(f"Failed to fill OCF-23 form: {e}")

    def _extract_ocf18_data(self, job: ProcessingJob, transcript_path: str, db_appointment_id: int) -> str:
        """Extract OCF-18 data using the dedicated extractor"""
        try:
            user_id = self._get_user_id()
            appointment = self.db_manager.get_appointment(db_appointment_id, user_id)
            appointment_folder = appointment['folder_path']

            # Track OCF-18 extraction step
            self.db_manager.update_processing_status(db_appointment_id, "ocf18_extraction", "processing")

            extraction_path = os.path.join(appointment_folder, "ocf18_extraction.json")

            extracted_data = self.ocf18_extractor.extract_data(transcript_path, job.appointment_id, extraction_path)
            if not extracted_data:
                raise Exception("No OCF-18 data extracted from transcript")

            self.db_manager.add_file(
                appointment_id=db_appointment_id,
                file_type="ocf18_extraction",
                file_path=extraction_path,
                retention_policy="1_month",
                user_id=user_id
            )

            # Update OCF-18 extraction status to completed
            self.db_manager.update_processing_status(db_appointment_id, "ocf18_extraction", "completed")

            return extraction_path
        except Exception as e:
            raise Exception(f"Failed to extract OCF-18 data: {e}")

    def _fill_ocf18_form(self, job: ProcessingJob, ocf18_extraction_path: str, db_appointment_id: int) -> Optional[str]:
        """Fill OCF-18 form using the dedicated filler"""
        try:
            user_id = self._get_user_id()
            appointment = self.db_manager.get_appointment(db_appointment_id, user_id)
            appointment_folder = appointment['folder_path']

            ocf18_template = "forms/templates/fsra_ocf18_template.pdf"
            if not os.path.exists(ocf18_template):
                raise Exception(f"OCF-18 template not found at {ocf18_template}")

            with open(ocf18_extraction_path, 'r', encoding='utf-8') as f:
                ocf18_extraction = json.load(f)

            output_path = os.path.join(appointment_folder, "ocf18_form.pdf")
            success = self.ocf18_form_filler.fill_ocf18_form(ocf18_template, ocf18_extraction, output_path)

            if success:
                self.db_manager.add_file(
                    appointment_id=db_appointment_id,
                    file_type="ocf18_form",
                    file_path=output_path,
                    retention_policy="long_term",
                    user_id=user_id
                )
                
                # Update OCF-18 form filling status
                self.db_manager.update_processing_status(db_appointment_id, "ocf18_form_filling", "completed")
                
                print(f"✅ OCF-18 form filled successfully: {output_path}")
                return output_path
            else:
                raise Exception("Failed to fill OCF-18 form")
        except Exception as e:
            raise Exception(f"Failed to fill OCF-18 form: {e}")
    
    def _update_progress(self, job: ProcessingJob, progress: str):
        """Update job progress and notify callbacks"""
        job.progress = progress
        self._notify_progress_change(job)
    
    def _notify_status_change(self, job: ProcessingJob):
        """Notify status change callbacks"""
        for callback in self.status_callbacks:
            try:
                callback(job)
            except Exception as e:
                self.logger.error(f"Status callback error: {e}")
    
    def _notify_progress_change(self, job: ProcessingJob):
        """Notify progress change callbacks"""
        for callback in self.progress_callbacks:
            try:
                callback(job)
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")
    
    def add_status_callback(self, callback: Callable):
        """Add a callback for status changes"""
        self.status_callbacks.append(callback)
    
    def add_progress_callback(self, callback: Callable):
        """Add a callback for progress changes"""
        self.progress_callbacks.append(callback)
    
    def get_job_status(self, job_id: str) -> Optional[ProcessingJob]:
        """Get the status of a specific job"""
        if job_id in self.active_jobs:
            return self.active_jobs[job_id]
        elif job_id in self.completed_jobs:
            return self.completed_jobs[job_id]
        return None
    
    def get_all_jobs(self) -> Dict[str, ProcessingJob]:
        """Get all jobs (active and completed)"""
        all_jobs = {}
        all_jobs.update(self.active_jobs)
        all_jobs.update(self.completed_jobs)
        return all_jobs
    
    def get_queue_size(self) -> int:
        """Get current queue size"""
        return self.job_queue.qsize()
    
    def get_active_job_count(self) -> int:
        """Get number of currently active jobs"""
        return len(self.active_jobs)
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job"""
        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            if job.status == ProcessingStatus.PENDING:
                job.status = ProcessingStatus.CANCELLED
                self.completed_jobs[job_id] = job
                del self.active_jobs[job_id]
                self._notify_status_change(job)
                return True
        return False
    
    def cleanup(self):
        """Clean up resources"""
        self.logger.info("Cleaning up background processor...")
        
        # Stop workers
        self.stop_workers()
        
        # Clean up components
        if hasattr(self, 'extractor'):
            self.extractor.cleanup()
        
        if hasattr(self, 'ocf18_extractor'):
            self.ocf18_extractor.cleanup()
        
        if hasattr(self, 'ocf23_extractor'):
            self.ocf23_extractor.cleanup()
        
        if hasattr(self, 'transcriber'):
            self.transcriber.cleanup()
        
        # Clean up shared ModelManager
        model_manager.cleanup()
        
        self.logger.info("Background processor cleanup completed")
