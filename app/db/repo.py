import uuid
from typing import Optional, Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from app.db.models import Conversation, ConversationMessage


def ensure_conversation(db: Session, conversation_id: uuid.UUID) -> Conversation:
    conversation = db.get(Conversation, conversation_id)
    if conversation is None:
        conversation = Conversation(conversation_id=conversation_id)
        db.add(conversation)
        db.commit()
        db.refresh(conversation)
    return conversation

def append_message(
        db: Session,
        conversation_id: uuid.UUID,
        role: str,
        content: str,
        *, 
        tool_name: Optional[str] = None,
        trace: Optional[dict] = None,
        ref_request_id: Optional[uuid.UUID] = None,
        ref_case_id: Optional[uuid.UUID] = None,
) -> ConversationMessage:
    message = ConversationMessage(
        conversation_id=conversation_id,
        role=role,
        content=content,
        tool_name=tool_name,
        trace=trace,
        ref_request_id=ref_request_id,
        ref_case_id=ref_case_id,
    )
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


def get_transcript(db:Session, conversation_id: uuid.UUID) -> Sequence[ConversationMessage]:
    stmt = (
        select(ConversationMessage)
        .where(ConversationMessage.conversation_id == conversation_id)
        .order_by(ConversationMessage.created_at.asc())
    )
    return db.execute(stmt).scalars().all()