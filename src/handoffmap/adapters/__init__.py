"""Convention adapters: decide what role a span plays (agent, tool, LLM call).

Each adapter looks at attributes only, never at the span name, because the
OTel GenAI conventions are still in development and frameworks name spans
differently (Pydantic AI instrumentation v2 says ``agent run``, v5 says
``invoke_agent orchestrator``).
"""

from __future__ import annotations

from dataclasses import dataclass

from ..model import Span

GENAI = "otel-genai"
OPENINFERENCE = "openinference"


@dataclass
class Classified:
    """What an adapter learned about one span."""

    role: str  # "agent" | "tool" | "llm" | "ignored"
    convention: str
    name: str = ""
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost: float | None = None
    handoff_marker: bool = False  # a tool span that only records "transfer to X"
    handoff_from: str | None = None  # OpenInference graph.node.parent_id
    reported_usage: tuple[int, int] | None = None  # usage attributes on an agent span


def classify(span: Span, unknown_operations: set[str] | None = None) -> Classified | None:
    """Classify a span, or return None if it is neither an agent, a tool nor an LLM call."""
    from . import genai, openinference

    if "gen_ai.operation.name" in span.attributes:
        result = genai.classify(span, unknown_operations)
        if result is not None or "openinference.span.kind" not in span.attributes:
            return result
    if "openinference.span.kind" in span.attributes:
        return openinference.classify(span)
    return None


def as_int(value: object) -> int | None:
    """Return value as int when it is a number (or numeric string), else None."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip().lstrip("-").isdigit():
        return int(value)
    return None


def as_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return None
    return None
