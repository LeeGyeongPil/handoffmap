"""Mermaid ``sequenceDiagram`` output.

Mermaid is picky about names: participants get plain aliases (``a1``, ``a2``)
and the real name goes after ``as``; ``#``, ``;``, ``<`` and ``>`` in any text
are written as Mermaid entity codes (``#59;``).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..model import Edge, Flow, ParallelGroup, ToolCall

_SPECIAL = re.compile(r"[#;<>]")


def escape(text: str) -> str:
    """Make ``text`` safe for a Mermaid message or participant label."""
    text = re.sub(r"\s+", " ", text).strip()
    return _SPECIAL.sub(lambda m: f"#{ord(m.group())};", text)


def _ms(value_ms: float) -> str:
    return f"{value_ms:.1f} ms"


@dataclass
class _Act:
    """One thing an agent run did: start a sub-agent/handoff (edge) or call a tool."""

    ref: str  # callee run id (edge) or tool span id (tool)
    start_ns: int
    edge: Edge | None = None
    tool: ToolCall | None = None


def render_mermaid(flow: Flow, *, show_tools: bool = True) -> str:
    """Render the flow as a Mermaid sequence diagram (no code fence)."""
    alias: dict[str, str] = {}
    for run in sorted(flow.runs.values(), key=lambda r: (r.start_ns, r.end_ns)):
        alias.setdefault(run.name, f"a{len(alias) + 1}")

    lines = ["sequenceDiagram"]
    for name, a in alias.items():
        lines.append(f"    participant {a} as {escape(name)}")

    # what each agent run did, in time order
    acts_by_run: dict[str, list[_Act]] = {}
    for e in flow.edges:
        if e.caller_run is not None:
            acts_by_run.setdefault(e.caller_run, []).append(_Act(e.callee_run, e.start_ns, edge=e))
    if show_tools:
        for t in flow.tools:
            if not t.wraps_agent:  # the sub-agent's own edge already shows this call
                acts_by_run.setdefault(t.run_id, []).append(_Act(t.span_id, t.start_ns, tool=t))
    for acts in acts_by_run.values():
        acts.sort(key=lambda a: a.start_ns)

    groups_by_run: dict[str, list[ParallelGroup]] = {}
    for g in flow.parallel:
        groups_by_run.setdefault(g.run_id, []).append(g)

    visited: set[str] = set()  # a run is drawn once, even if the data has a handoff cycle

    def act_line(act: _Act, indent: str) -> str:
        if act.tool is not None:
            t = act.tool
            a = alias[t.agent]
            return f"{indent}{a}->>{a}: {escape('tool ' + t.name)} ({_ms((t.end_ns - t.start_ns) / 1e6)})"
        e = act.edge
        assert e is not None
        src, dst = alias[e.caller or ""], alias[e.callee]
        if e.kind == "handoff":
            return f"{indent}{src}-){dst}: handoff ({_ms(e.duration_ms)})"  # -) = async, control does not come back
        label = f"as_tool via {e.via}" if e.kind == "as_tool" and e.via else e.kind
        return f"{indent}{src}->>{dst}: {escape(label)} ({_ms(e.duration_ms)})"

    def emit_act(act: _Act, indent: str) -> None:
        lines.append(act_line(act, indent))
        if act.edge is not None:
            emit_run(act.edge.callee_run, indent)

    def emit_run(run_id: str, indent: str) -> None:
        if run_id in visited:
            return
        visited.add(run_id)
        acts = acts_by_run.get(run_id, [])
        by_ref = {a.ref: a for a in acts}
        group_of: dict[str, list[_Act]] = {}
        for g in groups_by_run.get(run_id, []):
            branches = [by_ref[m.ref] for m in g.members if m.ref in by_ref]
            if len(branches) > 1:  # with --no-tools a group can shrink to one branch: then no par
                for b in branches:
                    group_of[b.ref] = branches

        drawn: set[str] = set()
        for act in acts:
            branches = group_of.get(act.ref)
            if branches is None:
                emit_act(act, indent)
            elif act.ref not in drawn:
                lines.append(f"{indent}par concurrent")
                for i, b in enumerate(branches):
                    if i:
                        lines.append(f"{indent}and")
                    emit_act(b, indent + "    ")
                    drawn.add(b.ref)
                lines.append(f"{indent}end")

    for e in flow.edges:
        if e.kind == "root":
            lines.append(f"    Note over {alias[e.callee]}: start")
            emit_run(e.callee_run, "    ")
    return "\n".join(lines) + "\n"
