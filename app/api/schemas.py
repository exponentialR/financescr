from typing import Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime

class AgentChatRequest(BaseModel):
    conversation_id : str = Field(..., description="Client-generated UUID")
    message: str
    context: dict[str, Any] = Field(default_factory=dict)

class AgentChatResponse(BaseModel):
    request_id: str
    conversation_id: str
    assistant_message: str
    trace: list[dict[str, Any]]
    final_state: dict[str, Any] = Field(default_factory=dict)

class TranscriptMessage(BaseModel):
    created_at: datetime
    role: str 
    content: str
    tool_name: Optional[str] = None
    trace: Optional[dict[str, Any]] = None

class ConversationReplayResponse(BaseModel):
    conversation_id: str
    messages: list[TranscriptMessage]