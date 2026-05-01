"""
OpenAI Whisper Speech-to-Text Implementation
Stable version without AV library dependency issues
"""

import io
import os
import wave
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from config.settings import settings
from fastapi import HTTPException

# Try to import openai-whisper, but handle gracefully if not available
try:
    import whisper
    OPENAI_WHISPER_AVAILABLE = True
except ImportError:
    OPENAI_WHISPER_AVAILABLE = False
    print("[WHISPER] OpenAI Whisper not available - falling back to SpeechRecognition")

# Fallback to speech_recognition if whisper fails
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

class OpenAIWhisperSTT:
    def __init__(self, model_size: str = "base"):
        """
        Initialize OpenAI Whisper model
        Args:
            model_size: Model size (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self.model = None
        self.recognizer = None
        self.sample_rate = 16000
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize OpenAI Whisper and fallback models"""
        # Try to initialize OpenAI Whisper first
        if OPENAI_WHISPER_AVAILABLE:
            try:
                print(f"[WHISPER] 🚀 Loading OpenAI Whisper model: {self.model_size}")
                self.model = whisper.load_model(self.model_size)
                print(f"[WHISPER] ✅ OpenAI Whisper model loaded successfully")
                return
                
            except Exception as e:
                print(f"[WHISPER] ❌ Failed to load OpenAI Whisper: {e}")
                print("[WHISPER] Falling back to SpeechRecognition...")
        
        # Fallback to speech_recognition
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
            print("[WHISPER] ✅ Using SpeechRecognition fallback")
        else:
            print("[WHISPER] ❌ No speech recognition available")
    
    def transcribe_audio(self, audio_data: bytes, format: str = "webm") -> str:
        """
        Transcribe audio data to text using OpenAI Whisper
        Args:
            audio_data: Raw audio data
            format: Audio format (webm, wav, mp3, etc.)
        Returns:
            Transcribed text
        """
        try:
            # Convert audio to WAV format for Whisper
            wav_data = self._convert_to_wav(audio_data, format)
            
            # Use OpenAI Whisper if available
            if self.model is not None:
                return self._transcribe_with_whisper(wav_data)
            
            # Fallback to SpeechRecognition
            elif self.recognizer is not None:
                return self._transcribe_with_speech_recognition(wav_data)
            
            else:
                raise HTTPException(status_code=500, detail="No transcription service available")
                
        except Exception as e:
            print(f"[WHISPER] ❌ Transcription failed: {e}")
            raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
    
    def _convert_to_wav(self, audio_data: bytes, input_format: str) -> bytes:
        """
        Convert audio data to WAV format using subprocess ffmpeg
        Args:
            audio_data: Raw audio data
            input_format: Input audio format
        Returns:
            WAV audio data
        """
        try:
            import subprocess
            
            # Use subprocess to call ffmpeg (more reliable than ffmpeg-python)
            result = subprocess.run([
                'ffmpeg', '-i', 'pipe:', '-f', 'wav', '-acodec', 'pcm_s16le', 
                '-ac', '1', '-ar', str(self.sample_rate), 'pipe:'
            ], input=audio_data, capture_output=True, check=True)
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            print(f"[WHISPER] ❌ FFmpeg conversion failed: {e.stderr.decode()}")
            # Try to return original data if conversion fails
            return audio_data
        except FileNotFoundError:
            print("[WHISPER] ❌ FFmpeg not found, returning original audio")
            return audio_data
        except Exception as e:
            print(f"[WHISPER] ❌ Audio conversion failed: {e}")
            return audio_data
    
    def _transcribe_with_whisper(self, wav_data: bytes) -> str:
        """
        Transcribe using OpenAI Whisper
        Args:
            wav_data: WAV audio data
        Returns:
            Transcribed text
        """
        try:
            # Save WAV data to temporary file
            temp_file = "/tmp/temp_audio.wav"
            with open(temp_file, "wb") as f:
                f.write(wav_data)
            
            print("[WHISPER] 🎤 Transcribing with OpenAI Whisper...")
            
            # Transcribe with Whisper
            result = self.model.transcribe(
                temp_file,
                language="en",  # Specify language for faster processing
                fp16=False     # Use FP32 for better compatibility
            )
            
            # Clean up temporary file
            os.remove(temp_file)
            
            # Get transcription
            transcription = result["text"].strip().lower()
            print(f"[WHISPER] ✅ Transcription: {transcription}")
            
            return transcription
            
        except Exception as e:
            print(f"[WHISPER] ❌ OpenAI Whisper transcription failed: {e}")
            # Clean up temporary file if it exists
            if os.path.exists("/tmp/temp_audio.wav"):
                os.remove("/tmp/temp_audio.wav")
            raise e
    
    def _transcribe_with_speech_recognition(self, wav_data: bytes) -> str:
        """
        Fallback transcription using SpeechRecognition
        Args:
            wav_data: WAV audio data
        Returns:
            Transcribed text
        """
        try:
            # Create audio file from bytes
            audio_file = io.BytesIO(wav_data)
            
            with wave.open(audio_file, 'rb') as wf:
                audio_data = sr.AudioData(
                    wf.readframes(wf.getnframes()),
                    sample_rate=wf.getframerate(),
                    sample_width=wf.getsampwidth()
                )
            
            print("[WHISPER] 🎤 Transcribing with SpeechRecognition...")
            
            # Try Google Web Speech API first (fastest)
            try:
                text = self.recognizer.recognize_google(audio_data)
                print(f"[WHISPER] ✅ Google Web Speech: {text}")
                return text.lower()
            except:
                pass
            
            # Try other engines as fallback
            engines = [
                ("Sphinx", self.recognizer.recognize_sphinx),
                ("Whisper", self.recognizer.recognize_whisper)
            ]
            
            for engine_name, engine_func in engines:
                try:
                    text = engine_func(audio_data)
                    print(f"[WHISPER] ✅ {engine_name}: {text}")
                    return text.lower()
                except:
                    continue
            
            raise Exception("All recognition engines failed")
            
        except Exception as e:
            print(f"[WHISPER] ❌ SpeechRecognition transcription failed: {e}")
            raise e
    
    def get_model_info(self) -> dict:
        """
        Get information about the current model
        Returns:
            Model information
        """
        return {
            "model_type": "openai_whisper" if self.model else "speech_recognition",
            "model_size": self.model_size if self.model else None,
            "sample_rate": self.sample_rate,
            "openai_whisper_available": OPENAI_WHISPER_AVAILABLE,
            "speech_recognition_available": SPEECH_RECOGNITION_AVAILABLE
        }

# Global instance for reuse
_stt_instance = None

def get_stt_instance(model_size: str = "base") -> OpenAIWhisperSTT:
    """
    Get or create STT instance
    Args:
        model_size: Model size for OpenAI Whisper
    Returns:
        STT instance
    """
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = OpenAIWhisperSTT(model_size)
    return _stt_instance

def transcribe_audio(audio_data: bytes, format: str = "webm") -> str:
    """
    Convenience function for transcription
    Args:
        audio_data: Raw audio data
        format: Audio format
    Returns:
        Transcribed text
    """
    stt = get_stt_instance()
    return stt.transcribe_audio(audio_data, format)
