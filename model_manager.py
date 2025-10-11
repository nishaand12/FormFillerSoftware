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
from llama_cpp import Llama


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
            
        self._model = None
        self._model_type = None
        self._model_path = None
        self._is_loading = False
        self._load_error = None
        self._last_used = 0
        self._access_count = 0
        
        # Setup logging
        self.setup_logging()
        
        # Mark as initialized
        self._initialized = True
        self.logger.info("ModelManager singleton initialized")
    
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
    
    def get_model(self, model_type: str = "qwen3-4b") -> Optional[Llama]:
        """
        Get the shared model instance. Thread-safe and lazy-loading.
        
        Args:
            model_type: Type of model to load ("qwen3-4b", "qwen3-1.7b", "tinyllama", etc.)
            
        Returns:
            Llama model instance or None if loading failed
        """
        with self._model_lock:
            # Check if we need to load a different model type
            if self._model is None or self._model_type != model_type:
                if not self._load_model(model_type):
                    return None
            
            # Update access tracking
            self._last_used = time.time()
            self._access_count += 1
            
            return self._model
    
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
            # Wait for loading to complete
            while self._is_loading:
                time.sleep(0.1)
            return self._model is not None and self._model_type == model_type
        
        self._is_loading = True
        self._load_error = None
        
        try:
            self.logger.info(f"Loading {model_type} model...")
            
            # Clean up existing model if switching types
            if self._model is not None and self._model_type != model_type:
                self.logger.info(f"Switching from {self._model_type} to {model_type} model")
                try:
                    del self._model
                    self._model = None
                    self.logger.info("Previous model cleaned up successfully")
                except Exception as e:
                    self.logger.warning(f"Error cleaning up previous model: {e}")
            
            # Determine model path
            if model_type == "qwen3-4b":
                model_path = "models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
            elif model_type == "qwen3-1.7b":
                model_path = "models/Qwen3-1.7B-Q8_0.gguf"
            else:
                model_path = "models/mistral-7b-instruct-v0.1.Q4_K_M.gguf"
            
            # Check if model file exists
            if not os.path.exists(model_path):
                error_msg = f"Model file not found at {model_path}"
                self.logger.error(error_msg)
                self._load_error = error_msg
                return False
            
            # Load the model
            self._model = Llama(
                model_path=model_path,
                n_ctx=2048,
                n_threads=1,  # Single thread to prevent conflicts
                n_gpu_layers=0,  # CPU only for compatibility
                verbose=False
            )
            
            self._model_type = model_type
            self._model_path = model_path
            
            self.logger.info(f"{model_type} model loaded successfully from {model_path}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to load {model_type} model: {str(e)}"
            self.logger.error(error_msg)
            self._load_error = error_msg
            self._model = None
            return False
            
        finally:
            self._is_loading = False
    
    def process_prompt(self, prompt: str, model_type: str = "qwen3-4b", 
                      max_tokens: int = 1024, temperature: float = 0.1, 
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
            try:
                # Get the model
                model = self.get_model(model_type)
                if model is None:
                    return {
                        'success': False,
                        'error': f"Model not available: {self._load_error or 'Unknown error'}"
                    }
                
                # Process the prompt
                self.logger.info(f"Processing prompt with {model_type} model...")
                response = model(
                    prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop=stop_sequences
                )
                
                return {
                    'success': True,
                    'response': response,
                    'text': response['choices'][0]['text'].strip() if response['choices'] else ""
                }
                
            except Exception as e:
                error_msg = f"Model inference failed: {str(e)}"
                self.logger.error(error_msg)
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
                'is_loaded': self._model is not None,
                'is_loading': self._is_loading,
                'load_error': self._load_error,
                'last_used': self._last_used,
                'access_count': self._access_count,
                'memory_usage_mb': self._get_memory_usage() if self._model else 0
            }
    
    def _get_memory_usage(self) -> float:
        """Estimate memory usage of the model in MB"""
        try:
            if self._model and hasattr(self._model, '_model'):
                # Rough estimate based on model size
                if self._model_type == "qwen3-4b":
                    return 4096.0  # ~4GB for Qwen3-4B
                elif self._model_type == "qwen3-1.7b":
                    return 2048.0  # ~2GB for Qwen3-1.7B
                else:
                    return 2048.0  # Default estimate
        except:
            pass
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
                model_type = self._model_type or "qwen"
            
            self.logger.info(f"Reloading {model_type} model...")
            
            # Clean up existing model
            if self._model is not None:
                try:
                    del self._model
                    self._model = None
                except:
                    pass
            
            # Reset state
            self._model_type = None
            self._model_path = None
            self._load_error = None
            
            # Load new model
            return self._load_model(model_type)
    
    def cleanup(self):
        """Clean up the model and resources"""
        with self._model_lock:
            self.logger.info("Cleaning up ModelManager...")
            
            if self._model is not None:
                try:
                    del self._model
                    self._model = None
                    self.logger.info("Model cleaned up successfully")
                except Exception as e:
                    self.logger.warning(f"Error during model cleanup: {e}")
            
            self._model_type = None
            self._model_path = None
            self._load_error = None
            self._is_loading = False
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform a health check on the model manager
        
        Returns:
            Health status information
        """
        with self._model_lock:
            try:
                if self._model is None:
                    return {
                        'status': 'unhealthy',
                        'reason': 'No model loaded',
                        'load_error': self._load_error
                    }
                
                # Try a simple inference to test model health
                test_prompt = "Hello"
                response = self._model(test_prompt, max_tokens=5, temperature=0.1)
                
                if response and 'choices' in response:
                    return {
                        'status': 'healthy',
                        'model_type': self._model_type,
                        'access_count': self._access_count,
                        'last_used': self._last_used
                    }
                else:
                    return {
                        'status': 'unhealthy',
                        'reason': 'Model inference failed',
                        'response': response
                    }
                    
            except Exception as e:
                return {
                    'status': 'unhealthy',
                    'reason': f'Health check failed: {str(e)}',
                    'load_error': self._load_error
                }


# Global instance for easy access
model_manager = ModelManager()
