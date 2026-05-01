from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import base64
from core.stt import transcribe_audio

router = APIRouter(prefix="/api", tags=["voice-to-text"])

class VoiceToTextRequest(BaseModel):
    audioBase64: str

class VoiceToTextResponse(BaseModel):
    text: str
    success: bool
    error: str = None

@router.post("/voice-to-text", response_model=VoiceToTextResponse)
async def voice_to_text(request: VoiceToTextRequest):
    """
    Convert voice audio to text using Vosk STT
    """
    try:
        # Decode base64 audio
        audio_bytes = base64.b64decode(request.audioBase64)
        print(f"[VOICE-TO-TEXT] Audio length: {len(audio_bytes)} bytes")
        
        # Transcribe audio
        text = await transcribe_audio(audio_bytes)
        
        print(f"[VOICE-TO-TEXT] Transcribed: '{text}'")
        return VoiceToTextResponse(
            text=text,
            success=True
        )
        
    except Exception as e:
        print(f"[VOICE-TO-TEXT] Error: {str(e)}")
        return VoiceToTextResponse(
            text="",
            success=False,
            error=str(e)
        )
