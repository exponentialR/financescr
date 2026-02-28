import uuid
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.schemas import AgentChatRequest, AgentChatResponse
from app.agent.orchestrator import run_agent_turn
from app.db.session import get_db
from app.fincrime.schemas import ScreenRequest, ScreenResponse
from app.fincrime.service import screen


from app.api.schemas import ConversationReplayResponse, TranscriptMessage
from app.db.repo import get_transcript

router = APIRouter()

# @router.get("/health")
# def health():
#     return {"status": "ok"}

@router.post("/agent/chat", response_model=AgentChatResponse)
def agent_chat(req: AgentChatRequest, db: Session = Depends(get_db)):
    try:
        cid = uuid.UUID(req.conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="conversation_id must be a UUID")

    out = run_agent_turn(db, cid, req.message)
    return out


@router.get("/agent/conversations/{conversation_id}", response_model=ConversationReplayResponse)
def replay_conversation(conversation_id: str, db: Session = Depends(get_db)):
    try:
        cid = uuid.UUID(conversation_id)
    except ValueError:
        raise HTTPException(status_code=422, detail="conversation_id must be a UUID")

    msgs = get_transcript(db, cid)
    return {
        "conversation_id": str(cid),
        "messages": [
            TranscriptMessage(
                created_at=m.created_at,
                role=m.role,
                content=m.content,
                tool_name=m.tool_name,
                trace=m.trace,
            )
            for m in msgs
        ],
    }

@router.post("/screen", response_model=ScreenResponse)
def post_screen(req: ScreenRequest) -> ScreenResponse:
    """FinCrime screening endpoint (Phase 1 stub; deterministic contract)."""
    return screen(req)