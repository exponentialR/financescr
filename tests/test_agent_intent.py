import unittest

from app.agent.intent import Intent, detect_intent


class IntentDetectionTests(unittest.TestCase):
    def test_detects_list_cases_phrases(self) -> None:
        self.assertEqual(detect_intent("please list cases").intent, Intent.LIST_CASES)
        self.assertEqual(detect_intent("show cases for me").intent, Intent.LIST_CASES)

    def test_detects_open_case_and_extracts_uuid(self) -> None:
        case_id = "123e4567-e89b-12d3-a456-426614174000"
        result = detect_intent(f"open case {case_id}")
        self.assertEqual(result.intent, Intent.OPEN_CASE)
        self.assertEqual(result.case_id, case_id)

    def test_detects_open_case_without_uuid(self) -> None:
        result = detect_intent("open case please")
        self.assertEqual(result.intent, Intent.OPEN_CASE)
        self.assertIsNone(result.case_id)

    def test_detects_explain_intent(self) -> None:
        self.assertEqual(detect_intent("why was this flagged").intent, Intent.EXPLAIN_LAST)
        self.assertEqual(detect_intent("explain last decision").intent, Intent.EXPLAIN_LAST)

    def test_detects_help_intent(self) -> None:
        self.assertEqual(detect_intent("help").intent, Intent.HELP)
        self.assertEqual(detect_intent("?").intent, Intent.HELP)

    def test_defaults_to_screen_subject(self) -> None:
        self.assertEqual(detect_intent("screen john doe").intent, Intent.SCREEN_SUBJECT)
