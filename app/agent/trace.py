from dataclasses import dataclass, asdict
from typing import Any, Optional

@dataclass
class TraceStep:
    step: int
    kind: str  # INTENT_UPDATE | ASK_USER | TOOL_CALL | TOOL_RESULT | RESPONSE
    summary: Optional[str] = None
    tool: Optional[str] = None
    tool_input: Optional[dict[str, Any]] = None
    tool_output_ref: Optional[dict[str, Any]] = None
    latency_ms: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        # drop None values to keep logs/DB tidy
        return {k: v for k, v in d.items() if v is not None}