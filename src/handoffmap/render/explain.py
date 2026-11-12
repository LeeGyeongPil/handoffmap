"""``--explain``: show which convention was detected and why each edge got its kind."""

from __future__ import annotations

from collections import Counter

from ..i18n import t
from ..model import Edge, Flow


def _edge_line(e: Edge, lang: str) -> str:
    src = e.caller or t(lang, "ex.none")
    extra = t(lang, "ex.via", via=e.via) if e.via else ""
    return f"  {src} -> {e.callee}: {e.kind}{extra}  [{t(lang, 'why.' + e.kind)}]"


def render_explain(flow: Flow, lang: str = "en") -> str:
    """Describe the detection result; ``lang`` is ``en`` (default) or ``ko``."""
    lines = [
        t(lang, "ex.trace", trace=flow.trace_id),
        t(lang, "ex.convention", convention=flow.convention),
        t(lang, "ex.size", spans=flow.span_count, runs=len(flow.runs), agents=len(flow.agents)),
        t(lang, "ex.agents", names=", ".join(a.name for a in flow.agents)),
        t(lang, "ex.edges"),
    ]
    lines += [_edge_line(e, lang) for e in flow.edges]
    if flow.ignored:
        counts = Counter(flow.ignored)
        shown = ", ".join(f"'{name}' x{n}" for name, n in counts.items())
        lines.append(t(lang, "ex.ignored", shown=shown))
    else:
        lines.append(t(lang, "ex.ignored_none"))
    if flow.unknown_operations:
        lines.append(t(lang, "ex.unknown_ops", names=", ".join(flow.unknown_operations)))
    tot = flow.totals
    if tot.input_tokens is None and tot.output_tokens is None:
        lines.append(t(lang, "ex.tokens_none"))
    else:
        lines.append(t(lang, "ex.tokens", input=tot.input_tokens or 0, output=tot.output_tokens or 0))
    if flow.reported_usage is not None:
        lines.append(t(lang, "ex.reported", input=flow.reported_usage[0], output=flow.reported_usage[1]))
    return "\n".join(lines) + "\n"
