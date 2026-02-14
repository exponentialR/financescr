import uuid
import unittest
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.api.routes import agent_chat, replay_conversation
from app.api.schemas import AgentChatRequest, TranscriptMessage


class AgentRouteTests(unittest.TestCase):
    def test_agent_chat_rejects_invalid_conversation_id(self) -> None:
        req = AgentChatRequest(conversation_id="not-a-uuid", message="hello")

        with patch("app.api.routes.run_agent_turn") as run_mock:
            with self.assertRaises(HTTPException) as ctx:
                agent_chat(req, db=MagicMock())

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "conversation_id must be a UUID")
        run_mock.assert_not_called()

    def test_agent_chat_calls_orchestrator_on_valid_input(self) -> None:
        conversation_id = uuid.uuid4()
        req = AgentChatRequest(conversation_id=str(conversation_id), message="help")
        db = MagicMock()
        expected = {
            "request_id": str(uuid.uuid4()),
            "conversation_id": str(conversation_id),
            "assistant_message": "ok",
            "trace": [],
            "final_state": {},
        }

        with patch("app.api.routes.run_agent_turn", return_value=expected) as run_mock:
            out = agent_chat(req, db=db)

        self.assertEqual(out, expected)
        run_mock.assert_called_once_with(db, conversation_id, "help")

    def test_replay_conversation_rejects_invalid_conversation_id(self) -> None:
        with patch("app.api.routes.get_transcript") as transcript_mock:
            with self.assertRaises(HTTPException) as ctx:
                replay_conversation("bad-id", db=MagicMock())

        self.assertEqual(ctx.exception.status_code, 422)
        self.assertEqual(ctx.exception.detail, "conversation_id must be a UUID")
        transcript_mock.assert_not_called()

    def test_replay_conversation_maps_transcript_messages(self) -> None:
        conversation_id = uuid.uuid4()
        db = MagicMock()
        msgs = [
            SimpleNamespace(
                created_at=datetime(2026, 2, 14, 10, 0, 0),
                role="USER",
                content="hello",
                tool_name=None,
                trace=None,
            ),
            SimpleNamespace(
                created_at=datetime(2026, 2, 14, 10, 0, 1),
                role="ASSISTANT",
                content="hi",
                tool_name=None,
                trace={"trace": [{"step": 0}]},
            ),
        ]

        with patch("app.api.routes.get_transcript", return_value=msgs) as transcript_mock:
            out = replay_conversation(str(conversation_id), db=db)

        transcript_mock.assert_called_once_with(db, conversation_id)
        self.assertEqual(out["conversation_id"], str(conversation_id))
        self.assertEqual(len(out["messages"]), 2)
        self.assertIsInstance(out["messages"][0], TranscriptMessage)
        self.assertEqual(out["messages"][0].role, "USER")
        self.assertEqual(out["messages"][1].trace, {"trace": [{"step": 0}]})
