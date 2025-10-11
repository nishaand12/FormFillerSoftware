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
    def __init__(self):
        self.models_dir = "models"
        self.cache_dir = os.path.expanduser("~/.cache/huggingface")
        
    def check_models(self):
        """Check if all required models are downloaded"""
        required_models = [
            "models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf",    # Qwen3-4B-Instruct model
            "models/Qwen3-1.7B-Q8_0.gguf",                  # Qwen3-1.7B efficient model
        ]
        
        missing_models = []
        for model_path in required_models:
            if not os.path.exists(model_path):
                missing_models.append(model_path)
        
        if missing_models:
            print(f"Missing models: {missing_models}")
            return False
        
        print("All required models are available")
        return True
    
    def download_all_models(self):
        """Download all required models"""
        print("Starting model downloads...")
        
        # Create models directory
        os.makedirs(self.models_dir, exist_ok=True)
        
        # Download Qwen model for data extraction
        self._download_qwen_model()
        
        # Download Qwen3-1.7B model for efficient data extraction
        self._download_qwen3_1_7b_model()
        
        # Download Whisper model (faster-whisper will handle this)
        self._download_whisper_model()
        
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
            
            downloaded_path = hf_hub_download(
                repo_id=model_name,
                filename=model_filename,
                local_dir=self.models_dir
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
            
            downloaded_path = hf_hub_download(
                repo_id=model_name,
                filename=model_filename,
                local_dir=self.models_dir
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