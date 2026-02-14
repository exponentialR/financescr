import re
from dataclasses import dataclass
from enum import Enum


class Intent(str, Enum):
    SCREEN_SUBJECT = "SCREEN_SUBJECT"
    LIST_CASES = "LIST_CASES"
    OPEN_CASE = "OPEN_CASE"
    EXPLAIN_LAST = "EXPLAIN_LAST"
    HELP = "HELP"


UUID_RE = re.compile(r"\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b")


@dataclass(frozen=True)
class IntentResult:
    intent: Intent
    case_id: str | None = None


def detect_intent(message: str) -> IntentResult:
    m = message.strip().lower()

    if "list cases" in m or "show cases" in m:
        return IntentResult(Intent.LIST_CASES)

    if "open case" in m:
        match = UUID_RE.search(message)
        return IntentResult(Intent.OPEN_CASE, case_id=match.group(0) if match else None)

    if "why" in m or "explain" in m:
        return IntentResult(Intent.EXPLAIN_LAST)

    if "help" in m or m == "?":
        return IntentResult(Intent.HELP)

    return IntentResult(Intent.SCREEN_SUBJECT)