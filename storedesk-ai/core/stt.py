"""
Speech-to-Text with Vosk
Uses reliable Vosk for offline transcription without build issues
"""

from core.vosk_stt import transcribe_audio, get_stt_instance
from fastapi import HTTPException

# Re-export functions for backward compatibility
__all__ = ['transcribe_audio', 'get_stt_instance']

# Initialize on import
print("[STT] 🚀 Initializing Vosk STT...")
try:
    stt_instance = get_stt_instance()  # Use default English model
    model_info = stt_instance.get_model_info()
    print(f"[STT] ✅ STT initialized: {model_info['model_type']} (lang: {model_info['language']})")
except Exception as e:
    print(f"[STT] ❌ Failed to initialize STT: {e}")
    stt_instance = None

def load_whisper_model():
    """Legacy function for backward compatibility"""
    print("[STT] 🔄 Using Vosk - legacy load_whisper_model called")

async def transcribe_audio(audio_bytes: bytes, format: str = "webm") -> str:
    """
    Transcribe audio using Vosk with fallback
    Args:
        audio_bytes: Raw audio data
        format: Audio format (webm, wav, mp3, etc.)
    Returns:
        Transcribed text
    """
    if stt_instance is None:
        raise HTTPException(status_code=503, detail="Speech-to-text not available")
    
    try:
        return stt_instance.transcribe_audio(audio_bytes, format)
    except Exception as e:
        print(f"[STT] ❌ Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
