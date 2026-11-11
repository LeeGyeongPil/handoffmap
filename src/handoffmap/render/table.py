"""Per-agent Markdown table."""

from __future__ import annotations

from ..model import AgentStats, Flow

DASH = "–"  # shown when a value is not in the trace


def _cell(text: str) -> str:
    # `|` would split the cell; `<`/`>` would be read as HTML by Markdown renderers
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;").replace("\n", " ")


def _tokens(value: int | None) -> str:
    return DASH if value is None else str(value)


def _row(a: AgentStats, with_cost: bool, bold: bool = False) -> str:
    name = f"**{_cell(a.name)}**" if bold else _cell(a.name)
    cells = [name, str(a.runs), str(a.llm_calls), str(a.tool_calls), _tokens(a.input_tokens), _tokens(a.output_tokens)]
    if with_cost:
        cells.append(DASH if a.cost is None else f"{a.cost:.6f}".rstrip("0").rstrip("."))
    cells.append(f"{a.duration_ms:.1f} ms")
    return "| " + " | ".join(cells) + " |"


def render_table(flow: Flow) -> str:
    """Render one row per agent name plus a total row (when there is more than one agent)."""
    with_cost = any(a.cost is not None for a in flow.agents)
    headers = ["agent", "runs", "LLM calls", "tools", "input tokens", "output tokens"]
    if with_cost:
        headers.append("cost")
    headers.append("time")
    lines = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join(["---"] + ["---:"] * (len(headers) - 1)) + "|",
    ]
    lines += [_row(a, with_cost) for a in flow.agents]
    if len(flow.agents) > 1:
        lines.append(_row(flow.totals, with_cost, bold=True))
    return "\n".join(lines) + "\n"
