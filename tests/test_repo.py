import uuid
import unittest
from unittest.mock import MagicMock, patch

from app.db.models import ConversationMessage
from app.db.repo import (
    add_message,
    commit_and_refresh,
    ensure_conversation,
    get_transcript_messages,
)


class RepoTests(unittest.TestCase):
    def test_ensure_conversation_returns_existing_row(self) -> None:
        db = MagicMock()
        conversation_id = uuid.uuid4()
        existing = object()
        db.get.return_value = existing

        out = ensure_conversation(db, conversation_id)

        self.assertIs(out, existing)
        db.add.assert_not_called()

    def test_ensure_conversation_creates_row_when_missing(self) -> None:
        db = MagicMock()
        conversation_id = uuid.uuid4()
        db.get.return_value = None

        out = ensure_conversation(db, conversation_id)

        self.assertEqual(out.conversation_id, conversation_id)
        db.add.assert_called_once_with(out)

    def test_add_message_adds_and_returns_message(self) -> None:
        db = MagicMock()
        conversation_id = uuid.uuid4()

        out = add_message(
            db,
            conversation_id,
            "TOOL",
            "intent_update",
            tool_name="intent_update",
            trace={"kind": "INTENT_UPDATE"},
        )

        self.assertIsInstance(out, ConversationMessage)
        self.assertEqual(out.conversation_id, conversation_id)
        self.assertEqual(out.role, "TOOL")
        self.assertEqual(out.content, "intent_update")
        self.assertEqual(out.tool_name, "intent_update")
        self.assertEqual(out.trace, {"kind": "INTENT_UPDATE"})
        db.add.assert_called_once_with(out)

    def test_commit_and_refresh_commits_and_refreshes_all_objects(self) -> None:
        db = MagicMock()
        obj1 = object()
        obj2 = object()

        commit_and_refresh(db, obj1, obj2)

        db.commit.assert_called_once()
        db.refresh.assert_any_call(obj1)
        db.refresh.assert_any_call(obj2)
        self.assertEqual(db.refresh.call_count, 2)

    def test_get_transcript_messages_returns_list(self) -> None:
        db = MagicMock()
        conversation_id = uuid.uuid4()
        items = ("a", "b")

        with patch("app.db.repo.get_transcript", return_value=items) as transcript_mock:
            out = get_transcript_messages(db, conversation_id)

        transcript_mock.assert_called_once_with(db, conversation_id)
        self.assertEqual(out, ["a", "b"])
