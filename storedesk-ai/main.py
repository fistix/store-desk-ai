import logging

import uvicorn
from fastapi import FastAPI

from core.logging_config import configure_logging

configure_logging()

from core.gateway import router as gateway_router
from core.stt import load_whisper_model
from api.voice_to_text import router as voice_to_text_router
from config.settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="StoreDesk AI Microservice",
    description="AI microservice for dropshipping client store management."
)

@app.on_event("startup")
async def startup_event():
    logger.info("Starting up StoreDesk AI service...")
    # Load Whisper model on startup
    load_whisper_model()
    logger.info("StoreDesk AI service started.")

app.include_router(gateway_router)
app.include_router(voice_to_text_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
