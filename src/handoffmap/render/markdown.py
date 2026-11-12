"""The default report: Mermaid diagram + agent table + warnings."""

from __future__ import annotations

from ..i18n import t
from ..model import Flow
from .mermaid import render_mermaid
from .table import render_table


def render_markdown(flow: Flow, *, show_tools: bool = True, heading: bool = True, lang: str = "en") -> str:
    """Render the full report; ``lang`` (``en`` default, or ``ko``) only changes the prose, not the diagram."""
    parts: list[str] = []
    if heading:
        parts.append(
            t(lang, "md.heading", trace=flow.trace_id[:8], convention=flow.convention, spans=flow.span_count) + "\n"
        )
    parts.append("```mermaid\n" + render_mermaid(flow, show_tools=show_tools) + "```\n")
    parts.append(t(lang, "md.agents") + "\n")
    parts.append(render_table(flow, lang=lang))
    parts.append(t(lang, "md.footnote") + "\n")
    if flow.warnings:
        parts.append(t(lang, "md.warnings") + "\n")
        lines = []
        for w in flow.warnings:
            # warnings built by find_warnings carry args; a hand-made one falls back to its English message
            message = t(lang, f"warn.{w.code}", **w.args) if w.args else w.message
            lines.append(f"- **{w.code}**: {message}")
        parts.append("\n".join(lines) + "\n")
    return "\n".join(parts)
