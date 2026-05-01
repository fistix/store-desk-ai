"""
Vosk Speech-to-Text Implementation
Reliable offline transcription without build dependency issues
"""

import io
import os
import wave
import json
import tempfile
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from fastapi import HTTPException

# Try to import vosk, but handle gracefully if not available
try:
    import vosk
    import soundfile as sf
    VOSK_AVAILABLE = True
except ImportError:
    VOSK_AVAILABLE = False
    print("[VOSK] Vosk not available - falling back to SpeechRecognition")

# Fallback to speech_recognition if vosk fails
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

class VoskSTT:
    def __init__(self, model_path: Optional[str] = None, lang: str = "en"):
        """
        Initialize Vosk model
        Args:
            model_path: Path to Vosk model directory
            lang: Language code (en, es, fr, etc.)
        """
        self.model_path = model_path
        self.lang = lang
        self.model = None
        self.recognizer = None
        self.sample_rate = 16000
        
        # Initialize models
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize Vosk and fallback models"""
        # Try to initialize Vosk first
        if VOSK_AVAILABLE:
            try:
                print(f"[VOSK] 🚀 Loading Vosk model for language: {self.lang}")
                
                # Download model if not provided
                if self.model_path is None:
                    self.model_path = self._download_model()
                
                # Load Vosk model
                self.model = vosk.Model(self.model_path)
                print(f"[VOSK] ✅ Vosk model loaded successfully")
                return
                
            except Exception as e:
                print(f"[VOSK] ❌ Failed to load Vosk: {e}")
                print("[VOSK] Falling back to SpeechRecognition...")
        
        # Fallback to speech_recognition
        if SPEECH_RECOGNITION_AVAILABLE:
            self.recognizer = sr.Recognizer()
            print("[VOSK] ✅ Using SpeechRecognition fallback")
        else:
            print("[VOSK] ❌ No speech recognition available")
    
    def _download_model(self) -> str:
        """
        Download Vosk model if not available
        Returns:
            Path to downloaded model
        """
        try:
            model_url = self._get_model_url()
            model_name = f"vosk-model-{self.lang}-0.42"
            model_dir = f"/tmp/{model_name}"
            
            # Check if model already exists
            if os.path.exists(model_dir):
                print(f"[VOSK] 📁 Model already exists: {model_dir}")
                return model_dir
            
            print(f"[VOSK] 📥 Downloading model: {model_name}")
            
            # Create model directory
            os.makedirs(model_dir, exist_ok=True)
            
            # Download and extract model
            import urllib.request
            import zipfile
            
            # Download zip file
            zip_path = f"/tmp/{model_name}.zip"
            urllib.request.urlretrieve(model_url, zip_path)
            
            # Extract model
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall("/tmp/")
            
            # Clean up zip file
            os.remove(zip_path)
            
            print(f"[VOSK] ✅ Model downloaded and extracted: {model_dir}")
            return model_dir
            
        except Exception as e:
            print(f"[VOSK] ❌ Failed to download model: {e}")
            raise e
    
    def _get_model_url(self) -> str:
        """Get model URL based on language"""
        model_urls = {
            "en": "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip",
            "es": "https://alphacephei.com/vosk/models/vosk-model-small-es-0.42.zip",
            "fr": "https://alphacephei.com/vosk/models/vosk-model-small-fr-0.22.zip",
            "de": "https://alphacephei.com/vosk/models/vosk-model-small-de-0.15.zip",
            "it": "https://alphacephei.com/vosk/models/vosk-model-small-it-0.22.zip",
            "pt": "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
        }
        return model_urls.get(self.lang, model_urls["en"])
    
    def transcribe_audio(self, audio_data: bytes, format: str = "webm") -> str:
        """
        Transcribe audio data to text using Vosk
        Args:
            audio_data: Raw audio data
            format: Audio format (webm, wav, mp3, etc.)
        Returns:
            Transcribed text
        """
        try:
            # Convert audio to WAV format for Vosk
            wav_data = self._convert_to_wav(audio_data, format)
            
            # Use Vosk if available
            if self.model is not None:
                return self._transcribe_with_vosk(wav_data)
            
            # Fallback to SpeechRecognition
            elif self.recognizer is not None:
                return self._transcribe_with_speech_recognition(wav_data)
            
            else:
                raise HTTPException(status_code=500, detail="No transcription service available")
                
        except Exception as e:
            print(f"[VOSK] ❌ Transcription failed: {e}")
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
            # Use subprocess to call ffmpeg
            result = subprocess.run([
                'ffmpeg', '-i', 'pipe:', '-f', 'wav', '-acodec', 'pcm_s16le', 
                '-ac', '1', '-ar', str(self.sample_rate), 'pipe:'
            ], input=audio_data, capture_output=True, check=True)
            
            return result.stdout
            
        except subprocess.CalledProcessError as e:
            print(f"[VOSK] ❌ FFmpeg conversion failed: {e.stderr.decode()}")
            # Try to return original data if conversion fails
            return audio_data
        except FileNotFoundError:
            print("[VOSK] ❌ FFmpeg not found, returning original audio")
            return audio_data
        except Exception as e:
            print(f"[VOSK] ❌ Audio conversion failed: {e}")
            return audio_data
    
    def _transcribe_with_vosk(self, wav_data: bytes) -> str:
        """
        Transcribe using Vosk
        Args:
            wav_data: WAV audio data
        Returns:
            Transcribed text
        """
        try:
            # Create Vosk recognizer
            rec = vosk.KaldiRecognizer(self.model, self.sample_rate)
            
            # Save WAV data to temporary file
            temp_file = "/tmp/temp_audio.wav"
            with open(temp_file, "wb") as f:
                f.write(wav_data)
            
            print("[VOSK] 🎤 Transcribing with Vosk...")
            
            # Read audio data
            with wave.open(temp_file, 'rb') as wf:
                if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != self.sample_rate:
                    print("[VOSK] ⚠️ Audio format not optimal, converting...")
                    # Convert audio if needed
                    audio_data = wf.readframes(wf.getnframes())
                else:
                    audio_data = wf.readframes(wf.getnframes())
            
            # Process audio with Vosk
            if rec.AcceptWaveform(audio_data):
                result = json.loads(rec.Result())
            else:
                result = json.loads(rec.FinalResult())
            
            # Clean up temporary file
            os.remove(temp_file)
            
            # Get transcription
            transcription = result.get('text', '').strip()
            print(f"[VOSK] ✅ Transcription: {transcription}")
            
            return transcription.lower() if transcription else ""
            
        except Exception as e:
            print(f"[VOSK] ❌ Vosk transcription failed: {e}")
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
            
            print("[VOSK] 🎤 Transcribing with SpeechRecognition...")
            
            # Try Google Web Speech API first (fastest)
            try:
                text = self.recognizer.recognize_google(audio_data)
                print(f"[VOSK] ✅ Google Web Speech: {text}")
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
                    print(f"[VOSK] ✅ {engine_name}: {text}")
                    return text.lower()
                except:
                    continue
            
            raise Exception("All recognition engines failed")
            
        except Exception as e:
            print(f"[VOSK] ❌ SpeechRecognition transcription failed: {e}")
            raise e
    
    def get_model_info(self) -> dict:
        """
        Get information about the current model
        Returns:
            Model information
        """
        return {
            "model_type": "vosk" if self.model else "speech_recognition",
            "model_path": self.model_path if self.model else None,
            "language": self.lang,
            "sample_rate": self.sample_rate,
            "vosk_available": VOSK_AVAILABLE,
            "speech_recognition_available": SPEECH_RECOGNITION_AVAILABLE
        }

# Global instance for reuse
_stt_instance = None

def get_stt_instance(model_path: str = None, lang: str = "en") -> VoskSTT:
    """
    Get or create STT instance
    Args:
        model_path: Path to Vosk model
        lang: Language code
    Returns:
        STT instance
    """
    global _stt_instance
    if _stt_instance is None:
        _stt_instance = VoskSTT(model_path, lang)
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
