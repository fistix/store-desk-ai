import ffmpeg
import os
import numpy as np
# STT temporarily disabled - whisper not installed
# try:
#     from faster_whisper import WhisperModel
#     FASTER_WHISPER_AVAILABLE = True
# except ImportError:
#     FASTER_WHISPER_AVAILABLE = False
#     import whisper
from config.settings import settings
from fastapi import HTTPException
import io

# Model will be loaded once on service startup and kept in memory
model = None
model_type = None

def load_whisper_model():
    global model, model_type
    # STT temporarily disabled
    print("STT functionality temporarily disabled - whisper not installed")
    model = None
    model_type = None
    return

async def transcribe_audio(audio_bytes: bytes) -> str:
    # STT temporarily disabled
    raise HTTPException(status_code=503, detail="Speech-to-text service temporarily disabled")
