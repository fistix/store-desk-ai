import uvicorn
from fastapi import FastAPI
from core.gateway import router as gateway_router
from core.stt import load_whisper_model
from config.settings import settings

app = FastAPI(
    title="StoreDesk AI Microservice",
    description="AI microservice for dropshipping client store management."
)

@app.on_event("startup")
async def startup_event():
    print("Starting up StoreDesk AI service...")
    # Load Whisper model on startup
    load_whisper_model()
    print("StoreDesk AI service started.")

app.include_router(gateway_router)

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.PORT,
        reload=settings.ENVIRONMENT == "development"
    )
