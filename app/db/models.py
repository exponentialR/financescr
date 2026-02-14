import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, DateTime, Float, ForeignKey, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class Conversation(Base):
    __tablename__ = "conversations"

    conversation_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow,  nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="ACTIVE")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    messages: Mapped[list["ConversationMessage"]] = relationship(
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ConversationMessage.created_at"
    )
    __table_args__ = (
        Index("ix_conversation_updated_at", "updated_at"),
    )

class ConversationMessage(Base):
    __tablename__ = "conversation_messages"
    message_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id : Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.conversation_id", ondelete="CASCADE"), nullable=False)
    created_at : Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False) # for User | Assistant | Tool
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tool_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    trace_json: Mapped[Optional[dict]] = mapped_column("trace", JSONB, default=dict, nullable=True)
    ref_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    ref_case_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    conversation: Mapped["Conversation"] = relationship(back_populates="messages")
    __table_args__ = (
        Index("ix_conversation_messages_conversation_id_created_at", "conversation_id", "created_at"), 
        )