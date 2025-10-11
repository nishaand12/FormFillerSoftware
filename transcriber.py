#!/usr/bin/env python3
"""
Transcriber Component
Uses faster-whisper for offline transcription
"""

import os
from faster_whisper import WhisperModel
from pydub import AudioSegment
import tempfile


class Transcriber:
    def __init__(self):
        self.model = None
        self.model_size = "small"
        self.compute_type = "float32"  # Explicitly use float32 for consistent performance and to avoid conversion warnings
        
    def _load_model(self):
        """Load the Whisper model if not already loaded"""
        if self.model is None:
            print("Loading Whisper model...")
            self.model = WhisperModel(
                self.model_size,
                device="cpu",  # Use CPU for better compatibility
                compute_type=self.compute_type,
                cpu_threads=1  # Limit CPU threads to reduce OpenMP conflicts
            )
            print("Whisper model loaded successfully")
    
    def cleanup(self):
        """Clean up resources to prevent memory leaks"""
        try:
            if self.model is not None:
                # Force garbage collection of the model
                del self.model
                self.model = None
                print("Whisper model cleaned up")
        except Exception as e:
            print(f"Warning: Error cleaning up transcriber: {e}")
    
    def _prepare_audio(self, audio_path):
        """Prepare audio for transcription - ensure 16kHz mono WAV"""
        try:
            # Load audio with pydub
            audio = AudioSegment.from_wav(audio_path)
            
            # Convert to mono if stereo
            if audio.channels > 1:
                audio = audio.set_channels(1)
            
            # Convert to 16kHz if different sample rate
            if audio.frame_rate != 16000:
                audio = audio.set_frame_rate(16000)
            
            # Create temporary file for processed audio
            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            # Export processed audio
            audio.export(temp_path, format="wav")
            
            return temp_path
            
        except Exception as e:
            print(f"Warning: Could not prepare audio, using original: {e}")
            return audio_path
    
    def transcribe(self, audio_path, appointment_id, output_path=None):
        """Transcribe audio file and save transcript"""
        try:
            # Load model if needed
            self._load_model()
            
            # Prepare audio
            processed_audio_path = self._prepare_audio(audio_path)
            
            # Determine output path
            if output_path is None:
                raise ValueError("output_path is required for transcription")
            else:
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                transcript_path = output_path
            
            # Transcribe
            print(f"Transcribing {audio_path}...")
            segments, info = self.model.transcribe(
                processed_audio_path,
                language="en",
                beam_size=5,
                best_of=5
            )
            
            # Combine all segments
            transcript_text = ""
            for segment in segments:
                transcript_text += segment.text + " "
            
            # Clean up transcript
            transcript_text = transcript_text.strip()
            
            # Save transcript
            with open(transcript_path, 'w', encoding='utf-8') as f:
                f.write(transcript_text)
            
            print(f"Transcript saved to {transcript_path}")
            
            # Clean up temporary file if created
            if processed_audio_path != audio_path:
                try:
                    os.unlink(processed_audio_path)
                except:
                    pass
            
            return transcript_path
            
        except Exception as e:
            error_msg = f"Transcription failed: {str(e)}"
            print(error_msg)
            
            # Save error transcript to provided output path if available
            if output_path:
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"TRANSCRIPTION ERROR: {error_msg}\n\n")
                    f.write("Please check the audio file and try again.")
            
            raise RuntimeError(error_msg)
    
    def get_transcript(self, transcript_path):
        """Get transcript from a specific path"""
        if os.path.exists(transcript_path):
            with open(transcript_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None 