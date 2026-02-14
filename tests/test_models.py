import unittest

from app.db.models import Base, Conversation, ConversationMessage


class ModelMappingTests(unittest.TestCase):
    def test_expected_tables_are_registered(self) -> None:
        self.assertIn("conversations", Base.metadata.tables)
        self.assertIn("conversation_messages", Base.metadata.tables)

    def test_conversation_table_has_expected_columns(self) -> None:
        columns = Conversation.__table__.columns
        expected = {
            "conversation_id",
            "created_at",
            "updated_at",
            "status",
            "metadata",
        }
        self.assertTrue(expected.issubset(set(columns.keys())))
        self.assertTrue(columns["conversation_id"].primary_key)

    def test_conversation_message_table_has_expected_columns(self) -> None:
        columns = ConversationMessage.__table__.columns
        expected = {
            "message_id",
            "conversation_id",
            "created_at",
            "role",
            "content",
            "tool_name",
            "trace",
            "ref_request_id",
            "ref_case_id",
        }
        self.assertTrue(expected.issubset(set(columns.keys())))
        self.assertTrue(columns["message_id"].primary_key)

    def test_indexes_match_model_expectations(self) -> None:
        conversation_indexes = {idx.name for idx in Conversation.__table__.indexes}
        message_indexes = {idx.name for idx in ConversationMessage.__table__.indexes}

        self.assertIn("ix_conversation_updated_at", conversation_indexes)
        self.assertIn(
            "ix_conversation_messages_conversation_id_created_at",
            message_indexes,
        )

    def test_message_foreign_key_targets_conversation_with_cascade_delete(self) -> None:
        foreign_keys = list(ConversationMessage.__table__.c.conversation_id.foreign_keys)
        self.assertEqual(len(foreign_keys), 1)
        self.assertEqual(foreign_keys[0].target_fullname, "conversations.conversation_id")
        self.assertEqual(foreign_keys[0].ondelete, "CASCADE")
