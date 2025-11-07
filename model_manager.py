#!/usr/bin/env python3
"""
Singleton Model Manager for Thread-Safe Model Access
Provides centralized, thread-safe access to the Qwen model for all workers
"""

import os
import threading
import time
import logging
from typing import Optional, Dict, Any

from runtime.hardware_profile import (
    get_hardware_profile,
    get_llama_runtime_config,
)
from telemetry import log_event
from inference_worker import InferenceWorkerController, ProcessRequest


class ModelManager:
    """
    Singleton model manager that provides thread-safe access to the Qwen model.
    Ensures only one thread can access the model at a time while maintaining
    efficient job processing through the queue system.
    """
    
    _instance = None
    _lock = threading.Lock()
    _model_lock = threading.RLock()  # Reentrant lock for model access
    
    def __new__(cls):
        """Ensure only one instance exists (singleton pattern)"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        """Initialize the model manager (only called once)"""
        if self._initialized:
            return
            
        self._model_type = None
        self._model_path = None
        self._is_loading = False
        self._load_error = None
        self._last_used = 0
        self._access_count = 0
        self._runtime_config = None
        self._hardware_profile = get_hardware_profile()
        
        # Setup logging
        self.setup_logging()
        self._worker = InferenceWorkerController(self.logger)
        
        # Mark as initialized
        self._initialized = True
        self.logger.info(
            "ModelManager singleton initialized on %s (%s cores, %.2f GB RAM, Metal=%s)",
            self._hardware_profile.architecture,
            self._hardware_profile.physical_cores,
            self._hardware_profile.memory_gb,
            self._hardware_profile.metal_available,
        )
    
    def setup_logging(self):
        """Setup logging for the model manager"""
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)
    
    def _load_model(self, model_type: str) -> bool:
        """
        Load the specified model type. Thread-safe loading.
        
        Args:
            model_type: Type of model to load
            
        Returns:
            True if model loaded successfully, False otherwise
        """
        # Prevent multiple simultaneous loading attempts
        if self._is_loading:
            self.logger.info("Model loading already in progress, waiting...")
            while self._is_loading:
                time.sleep(0.1)
            return self._model_type == model_type and self._load_error is None

        self._is_loading = True
        self._load_error = None
        
        try:
            self.logger.info(f"Loading {model_type} model...")

            # Determine model path using proper writable location
            try:
                from app_paths import get_writable_path
                if model_type == "qwen3-4b":
                    model_path = str(get_writable_path("models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"))
                elif model_type == "qwen3-1.7b":
                    model_path = str(get_writable_path("models/Qwen3-1.7B-Q8_0.gguf"))
                else:
                    model_path = str(get_writable_path("models/mistral-7b-instruct-v0.1.Q4_K_M.gguf"))
            except ImportError:
                # Fallback
                import sys
                from pathlib import Path as PathLib
                if sys.platform == 'darwin':
                    models_dir = PathLib.home() / "Library" / "Application Support" / "PhysioClinicAssistant" / "models"
                else:
                    models_dir = PathLib.home() / ".local" / "share" / "PhysioClinicAssistant" / "models"
                
                if model_type == "qwen3-4b":
                    model_path = str(models_dir / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf")
                elif model_type == "qwen3-1.7b":
                    model_path = str(models_dir / "Qwen3-1.7B-Q8_0.gguf")
                else:
                    model_path = str(models_dir / "mistral-7b-instruct-v0.1.Q4_K_M.gguf")
            
            # Check if model file exists
            if not os.path.exists(model_path):
                error_msg = f"Model file not found at {model_path}"
                self.logger.error(error_msg)
                self._load_error = error_msg
                return False
            
            runtime_cfg = get_llama_runtime_config(model_type)
            self._runtime_config = runtime_cfg
            self.logger.info(
                "Using runtime config: n_ctx=%s n_threads=%s n_gpu_layers=%s max_tokens=%s",
                runtime_cfg.n_ctx,
                runtime_cfg.n_threads,
                runtime_cfg.n_gpu_layers,
                runtime_cfg.max_tokens,
            )

            result = self._worker.ensure_model(
                model_type,
                model_path,
                runtime_cfg,
            )
            if not result.get("success"):
                self._load_error = result.get("error", "Unknown worker load failure")
                self.logger.error("Worker failed to load model: %s", self._load_error)
                log_event("model_load", {
                    "model_type": model_type,
                    "success": False,
                    "error": self._load_error,
                })
                return False

            self._model_type = model_type
            self._model_path = model_path
            
            self.logger.info(f"{model_type} model loaded successfully from {model_path}")
            log_event("model_load", {
                "model_type": model_type,
                "success": True,
                "n_ctx": runtime_cfg.n_ctx,
                "n_threads": runtime_cfg.n_threads,
                "n_gpu_layers": runtime_cfg.n_gpu_layers,
            })
            return True
            
        except Exception as e:
            error_msg = f"Failed to load {model_type} model: {str(e)}"
            self.logger.error(error_msg)
            self._load_error = error_msg
            return False
            
        finally:
            self._is_loading = False
    
    def process_prompt(self, prompt: str, model_type: str = "qwen3-4b", 
                      max_tokens: Optional[int] = None, temperature: float = 0.1, 
                      stop_sequences: list = None) -> Dict[str, Any]:
        """
        Process a prompt using the shared model. Thread-safe inference.
        
        Args:
            prompt: The prompt to process
            model_type: Type of model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            stop_sequences: Sequences to stop generation
            
        Returns:
            Model response dictionary or error information
        """
        if stop_sequences is None:
            stop_sequences = ["Transcript:", "Rules:"]
        
        with self._model_lock:
            if not self._load_model(model_type):
                return {
                    'success': False,
                    'error': f"Model not available: {self._load_error or 'Unknown error'}"
                }

            runtime_cfg = get_llama_runtime_config(
                model_type,
                transcript_chars=len(prompt),
                requested_max_tokens=max_tokens,
            )

            request = ProcessRequest(
                model_type=model_type,
                prompt=prompt,
                max_tokens=runtime_cfg.max_tokens,
                temperature=temperature,
                stop_sequences=stop_sequences,
            )

            start_time = time.time()
            try:
                self.logger.info(
                    "Processing prompt with %s model (max_tokens=%s)",
                    model_type,
                    runtime_cfg.max_tokens,
                )
                response = self._worker.process_prompt(request)
                duration_ms = int((time.time() - start_time) * 1000)
                self._last_used = time.time()
                self._access_count += 1

                if not response.get('success'):
                    log_event("model_inference", {
                        "model_type": model_type,
                        "success": False,
                        "duration_ms": duration_ms,
                        "error": response.get('error'),
                        "max_tokens": runtime_cfg.max_tokens,
                    })
                    return {
                        'success': False,
                        'error': response.get('error', 'Unknown inference error')
                    }

                log_event("model_inference", {
                    "model_type": model_type,
                    "success": True,
                    "duration_ms": duration_ms,
                    "max_tokens": runtime_cfg.max_tokens,
                })

                return {
                    'success': True,
                    'response': response.get('response'),
                    'text': response.get('text', "")
                }
            except TimeoutError as exc:
                self.logger.error("Inference timed out: %s", exc)
                self._worker.shutdown()
                self._worker = InferenceWorkerController(self.logger)
                log_event("model_inference", {
                    "model_type": model_type,
                    "success": False,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "error": "timeout",
                })
                return {
                    'success': False,
                    'error': f"Inference timeout: {exc}"
                }
            except Exception as e:
                error_msg = f"Model inference failed: {str(e)}"
                self.logger.error(error_msg)
                log_event("model_inference", {
                    "model_type": model_type,
                    "success": False,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "error": str(e),
                })
                return {
                    'success': False,
                    'error': error_msg
                }
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model state"""
        with self._model_lock:
            return {
                'model_type': self._model_type,
                'model_path': self._model_path,
                'is_loaded': self._model_type is not None and self._load_error is None,
                'is_loading': self._is_loading,
                'load_error': self._load_error,
                'last_used': self._last_used,
                'access_count': self._access_count,
                'memory_usage_mb': self._get_memory_usage()
            }
    
    def _get_memory_usage(self) -> float:
        """Estimate memory usage of the model in MB"""
        if self._model_type == "qwen3-4b":
            return 4096.0
        if self._model_type == "qwen3-1.7b":
            return 2048.0
        if self._model_type:
            return 2048.0
        return 0.0
    
    def reload_model(self, model_type: str = None) -> bool:
        """
        Reload the model. Useful for recovery after errors.
        
        Args:
            model_type: Type of model to reload (uses current if None)
            
        Returns:
            True if reload successful, False otherwise
        """
        with self._model_lock:
            if model_type is None:
                model_type = self._model_type or "qwen3-4b"
            
            self.logger.info(f"Reloading {model_type} model...")

            self._worker.reload_model()

            self._model_type = None
            self._model_path = None
            self._load_error = None

            return self._load_model(model_type)
    
    def cleanup(self):
        """Clean up the model and resources"""
        with self._model_lock:
            self.logger.info("Cleaning up ModelManager...")
            self._worker.shutdown()
            self._model_type = None
            self._model_path = None
            self._load_error = None
            self._is_loading = False
            self._runtime_config = None
            self._worker = InferenceWorkerController(self.logger)
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the model manager
        
        Returns:
            Health status information
        """
        with self._model_lock:
            try:
                healthy = self._worker.health_check()

                if healthy:
                    return {
                        'status': 'healthy',
                        'model_type': self._model_type,
                        'access_count': self._access_count,
                        'last_used': self._last_used
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'reason': 'Worker not ready',
                        'load_error': self._load_error
                    }
                    
            except Exception as e:
                return {
                    'status': 'unhealthy',
                    'reason': f'Health check failed: {str(e)}',
                    'load_error': self._load_error
                }


# Global instance for easy access
model_manager = ModelManager()
