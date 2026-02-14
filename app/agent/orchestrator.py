import uuid

from sqlalchemy.orm import Session

from app.agent.intent import Intent, detect_intent
from app.agent.trace import TraceStep
from app.db.repo import add_message, commit_and_refresh, ensure_conversation
from datetime import datetime

def run_agent_turn(db: Session, conversation_id: uuid.UUID, message: str) -> dict:
    """
    Executes a single agent turn as ONE database transaction:
      - ensure conversation exists
      - append USER message
      - append TOOL intent_update message (trace step 0)
      - append ASSISTANT message (with full trace)
      - commit once (atomic)
    """
    request_id = uuid.uuid4()

    try:
        # Begin transaction scope (SQLAlchemy session manages this)
        convo = ensure_conversation(db, conversation_id)
        convo.updated_at = datetime.utcnow()  # touch convo to update timestamp

        # Persist USER message (no commit)
        add_message(db, conversation_id, "USER", message)

        intent_res = detect_intent(message)

        # Trace step 0: intent update (mandatory)
        t0 = TraceStep(
            step=0,
            kind="INTENT_UPDATE",
            summary=f"intent={intent_res.intent.value}",
            tool="intent_update",
            tool_input={"intent": intent_res.intent.value, "case_id": intent_res.case_id},
        )

        # Persist TOOL message (no commit)
        add_message(
            db,
            conversation_id,
            "TOOL",
            "intent_update",
            tool_name="intent_update",
            trace=t0.to_dict(),
        )

        # Canned responses for now (no OpenAI, no /screen yet)
        if intent_res.intent == Intent.LIST_CASES:
            assistant = "Listing cases is wired next; DB + endpoint are up."
        elif intent_res.intent == Intent.OPEN_CASE:
            assistant = f"Open case requested. case_id={intent_res.case_id or 'missing'} (wiring next)."
        elif intent_res.intent == Intent.EXPLAIN_LAST:
            assistant = "I can explain once we have a screening snapshot (wiring next)."
        elif intent_res.intent == Intent.HELP:
            assistant = "You can say: 'Screen <name>', 'List cases', 'Open case <id>', or 'Explain last'."
        else:
            assistant = "Got it. I will run screening now (wiring /screen next)."

        t1 = TraceStep(step=1, kind="RESPONSE", summary="assistant_message_returned")
        full_trace = [t0.to_dict(), t1.to_dict()]

        # Persist ASSISTANT message with full trace (no commit)
        add_message(
            db,
            conversation_id,
            "ASSISTANT",
            assistant,
            trace={"trace": full_trace},
        )

        # Single atomic commit
        commit_and_refresh(db, convo)

    except Exception:
        db.rollback()
        raise

    return {
        "request_id": str(request_id),
        "conversation_id": str(conversation_id),
        "assistant_message": assistant,
        "trace": full_trace,
        "final_state": {"intent": intent_res.intent.value, "case_id": intent_res.case_id},
    }