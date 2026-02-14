import uuid
import unittest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from app.agent.intent import Intent, IntentResult
from app.agent.orchestrator import run_agent_turn


class OrchestratorTests(unittest.TestCase):
    def test_run_agent_turn_persists_messages_and_returns_response(self) -> None:
        db = MagicMock()
        conversation_id = uuid.uuid4()
        request_id = uuid.uuid4()
        convo = SimpleNamespace(updated_at=None)

        with (
            patch("app.agent.orchestrator.ensure_conversation", return_value=convo) as ensure_mock,
            patch(
                "app.agent.orchestrator.detect_intent",
                return_value=IntentResult(Intent.LIST_CASES),
            ) as detect_mock,
            patch("app.agent.orchestrator.add_message") as add_message_mock,
            patch("app.agent.orchestrator.commit_and_refresh") as commit_mock,
            patch("app.agent.orchestrator.uuid.uuid4", return_value=request_id),
        ):
            out = run_agent_turn(db, conversation_id, "list cases")

        ensure_mock.assert_called_once_with(db, conversation_id)
        detect_mock.assert_called_once_with("list cases")
        self.assertEqual(add_message_mock.call_count, 3)
        commit_mock.assert_called_once_with(db, convo)
        db.rollback.assert_not_called()

        first_call = add_message_mock.call_args_list[0]
        second_call = add_message_mock.call_args_list[1]
        third_call = add_message_mock.call_args_list[2]

        self.assertEqual(first_call.args, (db, conversation_id, "USER", "list cases"))
        self.assertEqual(second_call.args, (db, conversation_id, "TOOL", "intent_update"))
        self.assertEqual(second_call.kwargs["tool_name"], "intent_update")
        self.assertEqual(second_call.kwargs["trace"]["kind"], "INTENT_UPDATE")
        self.assertEqual(third_call.args[0:3], (db, conversation_id, "ASSISTANT"))
        self.assertIn("trace", third_call.kwargs["trace"])

        self.assertEqual(out["request_id"], str(request_id))
        self.assertEqual(out["conversation_id"], str(conversation_id))
        self.assertEqual(
            out["assistant_message"],
            "Listing cases is wired next; DB + endpoint are up.",
        )
        self.assertEqual(out["final_state"], {"intent": "LIST_CASES", "case_id": None})
        self.assertEqual([step["kind"] for step in out["trace"]], ["INTENT_UPDATE", "RESPONSE"])
        self.assertIsNotNone(convo.updated_at)

    def test_run_agent_turn_rolls_back_and_reraises_on_error(self) -> None:
        db = MagicMock()
        conversation_id = uuid.uuid4()
        convo = SimpleNamespace(updated_at=None)

        with (
            patch("app.agent.orchestrator.ensure_conversation", return_value=convo),
            patch("app.agent.orchestrator.add_message", side_effect=RuntimeError("boom")),
            patch("app.agent.orchestrator.detect_intent") as detect_mock,
            patch("app.agent.orchestrator.commit_and_refresh") as commit_mock,
        ):
            with self.assertRaises(RuntimeError):
                run_agent_turn(db, conversation_id, "any message")

        db.rollback.assert_called_once()
        detect_mock.assert_not_called()
        commit_mock.assert_not_called()
