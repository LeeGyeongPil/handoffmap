"""``--explain``: show which convention was detected and why each edge got its kind."""

from __future__ import annotations

from collections import Counter

from ..model import Edge, Flow

_WHY = {
    "root": "no agent above it and no handoff source: it started the run",
    "call": "agent span nested inside the caller, no tool span in between",
    "as_tool": "a tool span sits between the caller and this agent (agent used as a tool)",
    "handoff": "no agent ancestor; the span is a sibling and names its predecessor (graph.node.parent_id)",
}


def _edge_line(e: Edge) -> str:
    src = e.caller or "(none)"
    extra = f" via {e.via}" if e.via else ""
    return f"  {src} -> {e.callee}: {e.kind}{extra}  [{_WHY[e.kind]}]"


def render_explain(flow: Flow) -> str:
    lines = [
        f"trace: {flow.trace_id}",
        f"convention: {flow.convention}",
        f"size: {flow.span_count} spans, {len(flow.runs)} agent runs, {len(flow.agents)} agents",
        "agents: " + ", ".join(a.name for a in flow.agents),
        "edges:",
    ]
    lines += [_edge_line(e) for e in flow.edges]
    if flow.ignored:
        counts = Counter(flow.ignored)
        shown = ", ".join(f"'{name}' x{n}" for name, n in counts.items())
        lines.append(f"ignored wrappers (AGENT span without agent.name, not counted as agents): {shown}")
    else:
        lines.append("ignored wrappers: none")
    if flow.unknown_operations:
        lines.append("unknown gen_ai.operation.name values (passed through): " + ", ".join(flow.unknown_operations))
    t = flow.totals
    if t.input_tokens is None and t.output_tokens is None:
        lines.append("tokens: none of the LLM spans carry token counts")
    else:
        lines.append(f"tokens: {t.input_tokens or 0} in / {t.output_tokens or 0} out (summed from LLM spans only)")
    if flow.reported_usage is not None:
        lines.append(
            f"agent spans report {flow.reported_usage[0]} in / {flow.reported_usage[1]} out "
            "(cross-check only, never added to the totals)"
        )
    return "\n".join(lines) + "\n"
