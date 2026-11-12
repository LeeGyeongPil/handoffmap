"""Per-agent Markdown table."""

from __future__ import annotations

from ..i18n import t
from ..model import AgentStats, Flow

DASH = "–"  # shown when a value is not in the trace


def _cell(text: str) -> str:
    # `|` would split the cell; `<`/`>` would be read as HTML by Markdown renderers
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")


def _tokens(value: int | None) -> str:
    return DASH if value is None else str(value)


def _row(a: AgentStats, with_cost: bool, bold: bool = False, label: str | None = None) -> str:
    shown = a.name if label is None else label  # the totals row gets a translated label
    name = f"**{_cell(shown)}**" if bold else _cell(shown)
    cells = [name, str(a.runs), str(a.llm_calls), str(a.tool_calls), _tokens(a.input_tokens), _tokens(a.output_tokens)]
    if with_cost:
        cells.append(DASH if a.cost is None else f"{a.cost:.6f}".rstrip("0").rstrip("."))
    cells.append(f"{a.duration_ms:.1f} ms")
    return "| " + " | ".join(cells) + " |"


def render_table(flow: Flow, lang: str = "en") -> str:
    """Render one row per agent name plus a total row (when there is more than one agent)."""
    with_cost = any(a.cost is not None for a in flow.agents)
    keys = ["agent", "runs", "llm_calls", "tools", "input_tokens", "output_tokens"]
    if with_cost:
        keys.append("cost")
    keys.append("time")
    headers = [t(lang, f"table.{k}") for k in keys]
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] + ["---:"] * (len(headers) - 1)) + "|",
    ]
    lines += [_row(a, with_cost) for a in flow.agents]
    if len(flow.agents) > 1:
        lines.append(_row(flow.totals, with_cost, bold=True, label=t(lang, "table.total")))
    return "\n".join(lines) + "\n"
