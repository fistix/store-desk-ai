import hmac
import hashlib
import logging
import time
from fastapi import Request, HTTPException, Header
from config.settings import settings

logger = logging.getLogger(__name__)

async def verify_hmac(request: Request, x_hmac_signature: str = Header(None), x_timestamp: str = Header(None)):
    if not x_hmac_signature or not x_timestamp:
        raise HTTPException(status_code=401, detail="Missing auth headers")

    # Replay attack prevention: Reject if timestamp is older than 30 seconds
    try:
        request_time = int(x_timestamp)
        if abs(time.time() - request_time) > 30:
            raise HTTPException(status_code=401, detail="Request expired")
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid timestamp")

    # Recompute HMAC-SHA256
    body = await request.body()
    message = x_timestamp.encode() + body
    computed_signature = hmac.new(
        settings.HMAC_SECRET.encode(),
        message,
        hashlib.sha256
    ).hexdigest()

    if not hmac.compare_digest(computed_signature, x_hmac_signature):
        logger.warning("Rejected request with invalid HMAC signature")
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    return True
