from pydantic import BaseModel
from typing import Optional

class FusionEbsRequest(BaseModel):
    action: str              # 'generate', 'format', or 'debug'
    prompt: Optional[str] = ""
    code: Optional[str] = ""
    system_type: str        # 'Fusion' or 'EBS'
    model: str

class FusionEbsResponse(BaseModel):
    code: str
    explanation: str

class ChatRequest(BaseModel):
    message: str
    system_type: str
    current_code: Optional[str] = ""
    model: str

class ChatResponse(BaseModel):
    reply: str