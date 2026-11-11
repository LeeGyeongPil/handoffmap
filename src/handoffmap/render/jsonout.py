"""Stable JSON output. Only names, ids, timings and counts: never message content."""

from __future__ import annotations

from typing import Any

from ..model import AgentStats, Flow


def _agent(a: AgentStats) -> dict[str, Any]:
    return {
        "name": a.name,
        "runs": a.runs,
        "llm_calls": a.llm_calls,
        "tool_calls": a.tool_calls,
        "input_tokens": a.input_tokens,
        "output_tokens": a.output_tokens,
        "cost": a.cost,
        "duration_ms": round(a.duration_ms, 3),
    }


def to_dict(flow: Flow) -> dict[str, Any]:
    """Convert a flow to plain dicts/lists (``json.dumps``-able)."""
    t0 = min((r.start_ns for r in flow.runs.values()), default=0)
    return {
        "trace_id": flow.trace_id,
        "convention": flow.convention,
        "span_count": flow.span_count,
        "agents": [_agent(a) for a in flow.agents],
        "totals": _agent(flow.totals),
        "edges": [
            {
                "kind": e.kind,
                "from": e.caller,
                "to": e.callee,
                "via": e.via,
                "start_ms": round((e.start_ns - t0) / 1e6, 3),
                "duration_ms": round(e.duration_ms, 3),
            }
            for e in flow.edges
        ],
        "parallel": [
            {
                "agent": g.agent,
                "members": [
                    {"kind": m.kind, "name": m.name, "duration_ms": round((m.end_ns - m.start_ns) / 1e6, 3)}
                    for m in g.members
                ],
            }
            for g in flow.parallel
        ],
        "warnings": [{"code": w.code, "message": w.message} for w in flow.warnings],
    }
