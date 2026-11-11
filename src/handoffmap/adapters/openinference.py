"""OpenInference conventions (``openinference.span.kind`` based)."""

from __future__ import annotations

from ..model import Span
from . import OPENINFERENCE, Classified, as_float, as_int


def classify(span: Span) -> Classified | None:
    attrs = span.attributes
    kind = str(attrs.get("openinference.span.kind", "")).upper()

    if kind == "AGENT":
        name = attrs.get("agent.name") or attrs.get("graph.node.id")
        if not name:
            # e.g. the OpenAI Agents SDK "Agent workflow" wrapper: an AGENT span with no agent behind it
            return Classified(role="ignored", convention=OPENINFERENCE, name=span.name)
        parent = attrs.get("graph.node.parent_id")
        return Classified(
            role="agent",
            convention=OPENINFERENCE,
            name=str(name),
            handoff_from=str(parent) if parent else None,
        )

    if kind == "TOOL":
        name = attrs.get("tool.name") or span.name or "tool"
        # The Agents SDK records a handoff as a TOOL span named "handoff to <agent>".
        marker = span.name.lower().startswith("handoff to ")
        return Classified(role="tool", convention=OPENINFERENCE, name=str(name), handoff_marker=marker)

    if kind == "LLM":
        return Classified(
            role="llm",
            convention=OPENINFERENCE,
            input_tokens=as_int(attrs.get("llm.token_count.prompt")),
            output_tokens=as_int(attrs.get("llm.token_count.completion")),
            cost=as_float(attrs.get("llm.cost.total")),
        )
    return None
