import unittest

from app.agent.trace import TraceStep


class TraceStepTests(unittest.TestCase):
    def test_to_dict_drops_none_fields(self) -> None:
        step = TraceStep(step=0, kind="INTENT_UPDATE", summary="intent=HELP")
        out = step.to_dict()

        self.assertEqual(out, {"step": 0, "kind": "INTENT_UPDATE", "summary": "intent=HELP"})

    def test_to_dict_keeps_non_none_fields(self) -> None:
        step = TraceStep(
            step=1,
            kind="TOOL_CALL",
            tool="intent_update",
            tool_input={"intent": "LIST_CASES"},
            latency_ms=8,
        )
        out = step.to_dict()

        self.assertEqual(out["step"], 1)
        self.assertEqual(out["kind"], "TOOL_CALL")
        self.assertEqual(out["tool"], "intent_update")
        self.assertEqual(out["tool_input"], {"intent": "LIST_CASES"})
        self.assertEqual(out["latency_ms"], 8)
