"""OTel GenAI semantic conventions (``gen_ai.operation.name`` based)."""

from __future__ import annotations

from ..model import Span
from . import GENAI, Classified, as_int

LLM_OPERATIONS = {"chat", "text_completion", "generate_content"}
# Operations the conventions define that carry no agent/tool/LLM role here.
OTHER_KNOWN_OPERATIONS = {"create_agent", "invoke_workflow", "embeddings", "retrieval"}


def _strip_prefix(name: str, prefix: str) -> str:
    return name[len(prefix) :].strip() if name.startswith(prefix) else name


def classify(span: Span, unknown_operations: set[str] | None = None) -> Classified | None:
    attrs = span.attributes
    operation = attrs.get("gen_ai.operation.name")

    if operation == "invoke_agent":
        name = (
            attrs.get("gen_ai.agent.name")
            or attrs.get("agent_name")  # Pydantic AI also sets this non-standard key
            or _strip_prefix(span.name, "invoke_agent")
            or attrs.get("gen_ai.agent.id")
            or "agent"
        )
        reported = _reported_usage(attrs)
        return Classified(role="agent", convention=GENAI, name=str(name), reported_usage=reported)

    if operation == "execute_tool":
        name = attrs.get("gen_ai.tool.name") or _strip_prefix(span.name, "execute_tool") or "tool"
        return Classified(role="tool", convention=GENAI, name=str(name))

    if operation in LLM_OPERATIONS:
        return Classified(
            role="llm",
            convention=GENAI,
            input_tokens=as_int(attrs.get("gen_ai.usage.input_tokens")),
            output_tokens=as_int(attrs.get("gen_ai.usage.output_tokens")),
        )

    if operation not in OTHER_KNOWN_OPERATIONS and unknown_operations is not None:
        unknown_operations.add(str(operation))
    return None


def _reported_usage(attrs: dict) -> tuple[int, int] | None:
    """Usage attributes on an agent span. Used only as a cross-check, never summed."""
    for prefix in ("gen_ai.aggregated_usage", "gen_ai.usage"):
        i = as_int(attrs.get(f"{prefix}.input_tokens"))
        o = as_int(attrs.get(f"{prefix}.output_tokens"))
        if i is not None or o is not None:
            return (i or 0, o or 0)
    return None
