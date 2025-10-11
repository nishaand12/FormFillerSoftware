#!/usr/bin/env python3
"""
Audio Recorder Component using pvrecorder
Handles 30-minute WAV recording for physiotherapy appointments
Uses pvrecorder for better audio quality and reduced noise
"""

import pvrecorder
import wave
import numpy as np
import os
import time
from pydub import AudioSegment
from pydub.utils import make_chunks


class PvRecorderAudioRecorder:
    def __init__(self):
        self.sample_rate = 16000  # 16 kHz - optimal for speech recognition
        self.channels = 1  # Mono - better for speech, reduces noise
        self.frame_length = 512  # Frame length for pvrecorder
        self.recording = False
        self.audio_data = []
        self.start_time = None
        self.output_path = None
        self.recorder = None
        
    def start_recording(self, appointment_id, device_index=-1):
        """Start recording audio using pvrecorder"""
        if self.recording:
            raise RuntimeError("Already recording")
        
        # Set output path to temporary location in proper writable directory
        try:
            from app_paths import get_temp_path
            temp_dir = str(get_temp_path())
        except ImportError:
            import sys
            from pathlib import Path
            if sys.platform == 'darwin':
                temp_dir = f"/tmp/PhysioClinicAssistant"
                Path(temp_dir).mkdir(parents=True, exist_ok=True)
            else:
                temp_dir = "temp"
                os.makedirs(temp_dir, exist_ok=True)
        
        self.output_path = os.path.join(temp_dir, f"{appointment_id}.wav")
        
        # Initialize recording
        self.recording = True
        self.audio_data = []
        self.start_time = time.time()
        
        # Initialize pvrecorder
        # Note: On first run, this will trigger macOS permission dialog
        try:
            self.recorder = pvrecorder.PvRecorder(
                frame_length=self.frame_length,
                device_index=device_index,  # Use specified device or default
                buffered_frames_count=50
            )
            self.recorder.start()
            
            # Verify we can actually read audio (permission check)
            # This is critical - without permission, read() returns zeros
            print(f"🔍 Testing microphone access...")
            test_frames_count = 0
            test_has_audio = False
            for i in range(5):  # Try reading a few frames
                try:
                    test_frame = self.recorder.read()
                    if test_frame is not None and len(test_frame) > 0:
                        test_frames_count += 1
                        # Check if frame has non-zero audio data
                        frame_array = np.array(test_frame, dtype=np.int16)
                        if np.any(frame_array != 0):
                            test_has_audio = True
                        print(f"  Test frame {i+1}: {len(test_frame)} samples, max amplitude: {np.max(np.abs(frame_array))}")
                except Exception as e:
                    print(f"  Test frame {i+1}: Error - {e}")
                    break
            
            if test_frames_count == 0:
                # Could not read any frames - likely permission issue
                self.recorder.stop()
                self.recorder.delete()
                self.recorder = None
                self.recording = False
                raise RuntimeError(
                    "Microphone access denied or unavailable.\n\n"
                    "If you just saw a permission dialog, please:\n"
                    "1. Click 'OK' or 'Allow'\n"
                    "2. Try recording again\n\n"
                    "If no dialog appeared:\n"
                    "1. Open System Preferences > Privacy & Security > Microphone\n"
                    "2. Find and enable 'PhysioClinicAssistant'\n"
                    "3. Restart this application\n\n"
                    "Note: You may need to move the app to /Applications folder."
                )
            
            print(f"✅ Started recording to {self.output_path} using device index {device_index}")
            print(f"✓ Microphone permission verified - {test_frames_count} test frames read")
            if not test_has_audio:
                print(f"⚠️  WARNING: Test frames contain only silence/zeros - speak into microphone!")
            
            # Start continuous recording in a separate thread
            import threading
            self.recording_thread = threading.Thread(target=self._continuous_recording, daemon=True)
            self.recording_thread.start()
            
        except RuntimeError:
            # Re-raise our custom permission errors
            raise
        except Exception as e:
            self.recording = False
            error_msg = str(e).lower()
            
            # Check for permission-related errors
            if "permission" in error_msg or "denied" in error_msg or "authorized" in error_msg:
                raise RuntimeError(
                    "Microphone permission not granted.\n\n"
                    "Please:\n"
                    "1. Open System Preferences > Privacy & Security > Microphone\n"
                    "2. Enable access for 'PhysioClinicAssistant'\n"
                    "3. Restart this application\n\n"
                    f"Technical details: {e}"
                )
            else:
                raise RuntimeError(f"Failed to start recording: {e}")
    
    def _continuous_recording(self):
        """Continuously record audio data"""
        print(f"🎙️  Recording thread started")
        chunk_count = 0
        while self.recording:
            try:
                self._record_audio_chunk()
                chunk_count += 1
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage
            except Exception as e:
                print(f"❌ Error in continuous recording after {chunk_count} chunks: {e}")
                import traceback
                traceback.print_exc()
                break
        print(f"🛑 Recording thread stopped after collecting {chunk_count} chunks, audio_data has {len(self.audio_data)} chunks")
    
    def _record_audio_chunk(self):
        """Record a chunk of audio data"""
        if self.recording and self.recorder:
            try:
                # Get audio frame from pvrecorder
                audio_frame = self.recorder.read()
                if audio_frame is not None and len(audio_frame) > 0:
                    # Convert to numpy array and append
                    audio_chunk = np.array(audio_frame, dtype=np.int16)
                    self.audio_data.append(audio_chunk)
                    
                    # Debug: Print recording progress every 100 chunks
                    if len(self.audio_data) % 100 == 0:
                        max_amplitude = np.max(np.abs(audio_chunk))
                        print(f"📊 Recording progress: {len(self.audio_data)} chunks collected, last chunk max amplitude: {max_amplitude}")
                else:
                    print(f"⚠️  Received None or empty audio frame")
            except Exception as e:
                print(f"❌ Error reading audio frame: {e}")
                import traceback
                traceback.print_exc()
    
    def stop_recording(self):
        """Stop recording and save the audio file"""
        if not self.recording:
            raise RuntimeError("Not currently recording")
        
        print(f"🛑 Stopping recording...")
        
        # Stop recording
        self.recording = False
        
        # Wait for recording thread to finish
        if hasattr(self, 'recording_thread') and self.recording_thread.is_alive():
            print(f"⏳ Waiting for recording thread to finish...")
            self.recording_thread.join(timeout=2)  # Wait up to 2 seconds
        
        if self.recorder:
            self.recorder.stop()
            self.recorder.delete()
            self.recorder = None
        
        print(f"📊 Total audio chunks collected: {len(self.audio_data)}")
        
        # Combine all audio chunks
        if self.audio_data:
            try:
                # Concatenate all audio chunks
                combined_audio = np.concatenate(self.audio_data, axis=0)
                
                print(f"📊 Combined audio: {len(combined_audio)} samples ({len(combined_audio)/self.sample_rate:.2f} seconds)")
                print(f"📊 Audio range: min={np.min(combined_audio)}, max={np.max(combined_audio)}, non-zero samples={np.count_nonzero(combined_audio)}")
                
                # Save as WAV file
                self._save_wav_file(combined_audio)
                
                print(f"✅ Recording saved to {self.output_path}")
                
                # Verify file was written
                import os
                if os.path.exists(self.output_path):
                    file_size = os.path.getsize(self.output_path)
                    print(f"✅ File verified: {file_size} bytes")
                else:
                    print(f"❌ WARNING: File not found at {self.output_path}")
                
                return self.output_path
            except Exception as e:
                print(f"❌ Failed to save recording: {e}")
                import traceback
                traceback.print_exc()
                raise RuntimeError(f"Failed to save recording: {e}")
        else:
            print(f"❌ No audio data recorded - audio_data list is empty!")
            raise RuntimeError("No audio data recorded")
    
    def _save_wav_file(self, audio_data):
        """Save audio data as WAV file"""
        with wave.open(self.output_path, 'wb') as wav_file:
            # Set parameters
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit audio
            wav_file.setframerate(self.sample_rate)
            
            # Write audio data
            wav_file.writeframes(audio_data.tobytes())
    
    def record_for_duration(self, appointment_id, duration_seconds=1800, device_index=-1):
        """Record for a specific duration (default 30 minutes)"""
        self.start_recording(appointment_id, device_index)
        
        try:
            print(f"Recording for {duration_seconds} seconds...")
            start_time = time.time()
            
            while time.time() - start_time < duration_seconds and self.recording:
                self._record_audio_chunk()
                time.sleep(0.01)  # Small delay to prevent excessive CPU usage
                
        except KeyboardInterrupt:
            print("\nRecording interrupted by user")
        finally:
            self.stop_recording()
    
    def _compress_audio(self):
        """Compress the audio file to save space (optional)"""
        try:
            # Load the WAV file
            audio = AudioSegment.from_wav(self.output_path)
            
            # Compress to reduce file size (reduce quality after transcription)
            compressed_audio = audio.set_frame_rate(8000).set_channels(1)
            
            # Save compressed version
            compressed_path = self.output_path.replace('.wav', '_compressed.wav')
            compressed_audio.export(compressed_path, format="wav", parameters=["-q:a", "3"])
            
            # Replace original with compressed version
            os.remove(self.output_path)
            os.rename(compressed_path, self.output_path)
            
            print(f"Audio compressed and saved to {self.output_path}")
            
        except Exception as e:
            print(f"Warning: Failed to compress audio: {e}")
            # Keep original file if compression fails
    
    def get_recording_duration(self):
        """Get the current recording duration in seconds"""
        if self.start_time and self.recording:
            return time.time() - self.start_time
        return 0
    
    def is_recording(self):
        """Check if currently recording"""
        return self.recording
    
    def get_available_devices(self):
        """Get list of available audio devices"""
        try:
            return pvrecorder.PvRecorder.get_available_devices()
        except Exception as e:
            print(f"Warning: Could not get available devices: {e}")
            return []


# Example usage and testing
if __name__ == "__main__":
    # Test the recorder
    recorder = PvRecorderAudioRecorder()
    
    # Show available devices
    devices = recorder.get_available_devices()
    print("Available audio devices:")
    for i, device in enumerate(devices):
        print(f"  {i}: {device}")
    
    # Test recording for 5 seconds
    print("\nTesting recording for 5 seconds...")
    try:
        recorder.record_for_duration("test_recording", 5)
        print("Test recording completed successfully!")
    except Exception as e:
        print(f"Test recording failed: {e}")
