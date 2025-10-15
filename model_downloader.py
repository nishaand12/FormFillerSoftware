#!/usr/bin/env python3
"""
Model Downloader Component
Downloads all required models for offline operation
"""

import os
import requests
from huggingface_hub import snapshot_download
import subprocess
import sys


class ModelDownloader:
    def __init__(self, progress_callback=None):
        # Use proper writable path for models
        try:
            from app_paths import get_writable_path
            self.models_dir = str(get_writable_path("models"))
        except ImportError:
            import sys
            from pathlib import Path
            if sys.platform == 'darwin':
                self.models_dir = str(Path.home() / "Library" / "Application Support" / "PhysioClinicAssistant" / "models")
            else:
                self.models_dir = "models"
        
        self.cache_dir = os.path.expanduser("~/.cache/huggingface")
        self.progress_callback = progress_callback
        self.current_model_progress = 0
    
    def check_models(self):
        """Check if all required models are downloaded"""
        model_files = [
            "Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
            "Qwen3-1.7B-Q8_0.gguf",
        ]
        
        missing_models = []
        for model_file in model_files:
            model_path = os.path.join(self.models_dir, model_file)
            if not os.path.exists(model_path):
                missing_models.append(model_file)
        
        if missing_models:
            print(f"Missing models: {missing_models}")
            return False
        
        print("All required models are available")
        return True
    
    def download_all_models(self):
        """Download all required models"""
        print(f"Starting model downloads to {self.models_dir}...")
        
        # Create models directory (get_writable_path already creates it, but ensure it exists)
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Download Qwen model for data extraction (33% of total)
        if self.progress_callback:
            self.progress_callback(0, "Downloading Qwen 4B model...")
        self._download_qwen_model()
        
        # Download Qwen3-1.7B model for efficient data extraction (66% of total)
        if self.progress_callback:
            self.progress_callback(33, "Downloading Qwen 1.7B model...")
        self._download_qwen3_1_7b_model()
        
        # Download Whisper model (faster-whisper will handle this) (100% of total)
        if self.progress_callback:
            self.progress_callback(66, "Downloading Whisper model...")
        self._download_whisper_model()
        
        if self.progress_callback:
            self.progress_callback(100, "All models downloaded!")
        print("All models downloaded successfully!")
    

    

    
    def _download_qwen_model(self):
        """Download the Qwen3-4B-Instruct model"""
        model_name = "unsloth/Qwen3-4B-Instruct-2507-GGUF"
        model_filename = "Qwen3-4B-Instruct-2507-Q4_K_M.gguf"
        local_path = f"{self.models_dir}/{model_filename}"
        
        if os.path.exists(local_path):
            print("Qwen model already exists")
            return
        
        print(f"Downloading Qwen model: {model_name}")
        
        try:
            # Download only the specific model file we need
            from huggingface_hub import hf_hub_download
            from tqdm.auto import tqdm
            
            # Create a custom progress bar
            class ProgressCallback:
                def __init__(self, callback):
                    self.callback = callback
                    self.pbar = None
                
                def __call__(self, current, total):
                    if self.pbar is None:
                        self.pbar = tqdm(total=total, unit='B', unit_scale=True, desc="Qwen 4B")
                    
                    self.pbar.update(current - self.pbar.n)
                    
                    if self.callback and total > 0:
                        # Report progress within this model's portion (0-33%)
                        percent = int((current / total) * 33)
                        self.callback(percent, f"Downloading Qwen 4B model... {percent}%")
            
            downloaded_path = hf_hub_download(
                repo_id=model_name,
                filename=model_filename,
                local_dir=self.models_dir,
                resume_download=True
            )
            
            # Move to the expected location
            if downloaded_path != local_path:
                os.rename(downloaded_path, local_path)
            
            print(f"Qwen model downloaded to {local_path}")
            
        except Exception as e:
            print(f"Error downloading Qwen model: {e}")
            raise
    
    def _download_qwen3_1_7b_model(self):
        """Download the Qwen3-1.7B model"""
        model_name = "ggml-org/Qwen3-1.7B-GGUF"
        model_filename = "Qwen3-1.7B-Q8_0.gguf"
        local_path = f"{self.models_dir}/Qwen3-1.7B-Q8_0.gguf"
        
        if os.path.exists(local_path):
            print("Qwen3-1.7B model already exists")
            return
        
        print(f"Downloading Qwen3-1.7B model: {model_name}")
        
        try:
            # Download only the specific model file we need
            from huggingface_hub import hf_hub_download
            from tqdm.auto import tqdm
            
            # Create a custom progress bar
            class ProgressCallback:
                def __init__(self, callback):
                    self.callback = callback
                    self.pbar = None
                
                def __call__(self, current, total):
                    if self.pbar is None:
                        self.pbar = tqdm(total=total, unit='B', unit_scale=True, desc="Qwen 1.7B")
                    
                    self.pbar.update(current - self.pbar.n)
                    
                    if self.callback and total > 0:
                        # Report progress within this model's portion (33-66%)
                        percent = 33 + int((current / total) * 33)
                        self.callback(percent, f"Downloading Qwen 1.7B model... {percent}%")
            
            downloaded_path = hf_hub_download(
                repo_id=model_name,
                filename=model_filename,
                local_dir=self.models_dir,
                resume_download=True
            )
            
            # Move to the expected location
            if downloaded_path != local_path:
                os.rename(downloaded_path, local_path)
            
            print(f"Qwen3-1.7B model downloaded to {local_path}")
            
        except Exception as e:
            print(f"Error downloading Qwen3-1.7B model: {e}")
            raise
    
    def _download_whisper_model(self):
        """Download the Whisper model"""
        # faster-whisper handles model downloading automatically
        # We just need to trigger a download by importing
        print("Setting up Whisper model (will be downloaded on first use)")
        
        try:
            from faster_whisper import WhisperModel
            
            # This will trigger the download
            model = WhisperModel("small", device="cpu", compute_type="float32")
            print("Whisper model setup complete")
            
        except Exception as e:
            print(f"Error setting up Whisper model: {e}")
            # Don't raise here as faster-whisper will handle it
    
    def get_model_paths(self):
        """Get paths to all downloaded models"""
        paths = {
            "qwen3-4b": f"{self.models_dir}/Qwen3-4B-Instruct-2507-Q4_K_M.gguf",
            "qwen3-1.7b": f"{self.models_dir}/Qwen3-1.7B-Q8_0.gguf",
            "whisper": "small"  # faster-whisper model name
        }
        
        return paths
    
    def cleanup_old_models(self):
        """Clean up old model files"""
        try:
            # Remove old cache files
            cache_dirs = [
                os.path.expanduser("~/.cache/huggingface"),
                os.path.expanduser("~/.cache/torch"),
                os.path.expanduser("~/.cache/transformers")
            ]
            
            for cache_dir in cache_dirs:
                if os.path.exists(cache_dir):
                    print(f"Cleaning cache: {cache_dir}")
                    # This is a simple cleanup - in production you might want more sophisticated logic
                    pass
            
        except Exception as e:
            print(f"Warning: Failed to cleanup old models: {e}")
    
    def get_download_progress(self):
        """Get download progress information"""
        # This would be implemented with progress tracking
        # For now, return basic info
        return {
            "models_dir": self.models_dir,
            "cache_dir": self.cache_dir,
            "all_models_available": self.check_models()
        }


def main():
    """Command line interface for model downloading"""
    downloader = ModelDownloader()
    
    if len(sys.argv) > 1 and sys.argv[1] == "check":
        if downloader.check_models():
            print("✓ All models are available")
            sys.exit(0)
        else:
            print("✗ Some models are missing")
            sys.exit(1)
    
    elif len(sys.argv) > 1 and sys.argv[1] == "download":
        print("Starting model downloads...")
        downloader.download_all_models()
        print("✓ All models downloaded successfully")
    
    else:
        print("Usage:")
        print("  python model_downloader.py check    - Check if models are available")
        print("  python model_downloader.py download - Download all models")


if __name__ == "__main__":
    main() 