#!/usr/bin/env python3
"""
Summarizer Component
Uses Qwen model via llama_cpp_python for physiotherapy-specific summaries
"""

import os
import re
from llama_cpp import Llama


class Summarizer:
    def __init__(self):
        self.llama_model = None
        self.max_length = 2048
        self.chunk_size = 1500  # Characters per chunk
        
    def _load_model(self):
        """Load the Qwen model for summarization"""
        if self.llama_model is None:
            # Use proper writable path for models
            try:
                from app_paths import get_writable_path
                model_path = str(get_writable_path("models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf"))
            except ImportError:
                import sys
                from pathlib import Path
                if sys.platform == 'darwin':
                    model_path = str(Path.home() / "Library" / "Application Support" / "PhysioClinicAssistant" / "models" / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf")
                else:
                    model_path = str(Path.home() / ".local" / "share" / "PhysioClinicAssistant" / "models" / "Qwen3-4B-Instruct-2507-Q4_K_M.gguf")
            
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Qwen model not found at {model_path}")
            
            try:
                print("Loading Qwen model for summarization...")
                self.llama_model = Llama(
                    model_path=model_path,
                    n_ctx=2048,
                    n_threads=1,  # Single thread to prevent OpenMP conflicts
                    n_gpu_layers=0,  # CPU only for compatibility
                    verbose=False
                )
                print("Qwen model loaded successfully for summarization")
            except Exception as e:
                print(f"Warning: Failed to load Qwen model for summarization: {e}")
                raise
    
    def _chunk_text(self, text, max_chars=1500):
        """Split text into chunks that fit within character limit"""
        # Simple sentence-based chunking
        sentences = re.split(r'[.!?]+', text)
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
                
            # Check if adding this sentence would exceed the limit
            test_chunk = current_chunk + " " + sentence if current_chunk else sentence
            
            if len(test_chunk) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence
                else:
                    # Single sentence is too long, truncate it
                    chunks.append(sentence[:max_chars])
            else:
                current_chunk = test_chunk
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def _summarize_chunk(self, chunk):
        """Summarize a single chunk of text using Qwen"""
        try:
            # Create a prompt for summarization
            prompt = f"""<|im_start|>system
You are a helpful assistant that creates concise summaries of medical conversations and physiotherapy appointments. Focus on key medical information, symptoms, treatments, and recommendations.
<|im_end|>
<|im_start|>user
Please summarize the following physiotherapy appointment transcript in a clear, professional manner:

{chunk}
<|im_end|>
<|im_start|>assistant
"""
            
            # Generate summary
            response = self.llama_model(
                prompt,
                max_tokens=300,
                temperature=0.3,
                stop=["<|im_end|>", "\n\n"],
                echo=False
            )
            
            summary = response['choices'][0]['text'].strip()
            return summary
            
        except Exception as e:
            print(f"Warning: Failed to summarize chunk: {e}")
            return chunk[:200] + "..."  # Return truncated chunk as fallback
    
    def summarize(self, transcript_path, appointment_id):
        """Generate physiotherapy-specific summary from transcript"""
        try:
            # Load model if needed
            self._load_model()
            
            # Read transcript
            with open(transcript_path, 'r', encoding='utf-8') as f:
                transcript_text = f.read()
            
            if not transcript_text.strip():
                raise ValueError("Transcript is empty")
            
            # Create summaries directory
            os.makedirs("summaries", exist_ok=True)
            
            # Split transcript into chunks
            chunks = self._chunk_text(transcript_text, self.chunk_size)
            
            print(f"Processing {len(chunks)} chunks for summarization...")
            
            # Summarize each chunk
            chunk_summaries = []
            for i, chunk in enumerate(chunks):
                print(f"Summarizing chunk {i+1}/{len(chunks)}...")
                print(f"Chunk length: {len(chunk)} characters")
                summary = self._summarize_chunk(chunk)
                print(f"Summary length: {len(summary)} characters")
                chunk_summaries.append(summary)
            
            # Combine chunk summaries
            combined_summary = " ".join(chunk_summaries)
            
            # Create final physiotherapy-specific summary
            final_prompt = f"""<|im_start|>system
You are a physiotherapy assistant. Create a comprehensive, professional summary of a physiotherapy appointment focusing on:
- Patient symptoms and complaints
- Mechanism of injury (if applicable)
- Assessment findings
- Treatment provided
- Functional limitations
- Recommendations and next steps

Format the summary in a clear, structured manner suitable for medical documentation.
<|im_end|>
<|im_start|>user
Create a comprehensive physiotherapy appointment summary from this information:

{combined_summary}
<|im_end|>
<|im_start|>assistant
"""
            
            # Generate final summary
            final_response = self.llama_model(
                final_prompt,
                max_tokens=500,
                temperature=0.2,
                stop=["<|im_end|>", "\n\n"],
                echo=False
            )
            
            final_summary = final_response['choices'][0]['text'].strip()
            
            # Save summary to provided output path
            if output_path is None:
                raise ValueError("output_path is required for summarization")
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            summary_path = output_path
            with open(summary_path, 'w', encoding='utf-8') as f:
                f.write("PHYSIOTHERAPY APPOINTMENT SUMMARY\n")
                f.write("=" * 50 + "\n\n")
                f.write(final_summary)
                f.write("\n\n" + "=" * 50 + "\n")
                f.write("Generated from transcript using Qwen AI summarization\n")
            
            print(f"Summary saved to {summary_path}")
            return summary_path
            
        except Exception as e:
            error_msg = f"Summarization failed: {str(e)}"
            print(error_msg)
            
            # Save error summary to provided output path if available
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"SUMMARIZATION ERROR: {error_msg}\n\n")
                    f.write("Please check the transcript and try again.")
            
            raise RuntimeError(error_msg)
    
    def get_summary(self, summary_path):
        """Get summary from a specific path"""
        if os.path.exists(summary_path):
            with open(summary_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None 