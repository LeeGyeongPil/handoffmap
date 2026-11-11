"""The default report: Mermaid diagram + agent table + warnings."""

from __future__ import annotations

from ..model import Flow
from .mermaid import render_mermaid
from .table import render_table


def render_markdown(flow: Flow, *, show_tools: bool = True, heading: bool = True) -> str:
    parts: list[str] = []
    if heading:
        parts.append(f"## Agent flow: trace {flow.trace_id[:8]} ({flow.convention}, {flow.span_count} spans)\n")
    parts.append("```mermaid\n" + render_mermaid(flow, show_tools=show_tools) + "```\n")
    parts.append("### Agents\n")
    parts.append(render_table(flow))
    parts.append(
        "_Tokens are summed from LLM spans only. `time` is the wall time of each run, "
        "including work it delegated. `–` means the trace does not contain the value._\n"
    )
    if flow.warnings:
        parts.append("### Warnings\n")
        parts.append("\n".join(f"- **{w.code}**: {w.message}" for w in flow.warnings) + "\n")
    return "\n".join(parts)
