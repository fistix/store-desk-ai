from pydantic import BaseModel
from typing import List, Optional

class UserContext(BaseModel):
    user_id: str
    tenant_id: str
    connector_id: str
    selected_product_ids: Optional[List[str]] = []

class AssistRequest(BaseModel):
    sessionId: str
    message: Optional[str] = None
    audioBase64: Optional[str] = None
    inputType: str # "text" or "audio"
    context: Optional[dict] = None
