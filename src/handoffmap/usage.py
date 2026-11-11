"""Per-agent statistics.

Tokens are summed only at LLM spans (one span, one count). Attributes such as
``gen_ai.aggregated_usage.*`` on agent spans are totals of the same LLM calls;
adding them again would double count, so they are never summed.
"""

from __future__ import annotations

from .adapters import Classified
from .model import AgentRun, AgentStats, ToolCall


def collect_stats(
    runs: dict[str, AgentRun],
    tools: list[ToolCall],
    llm_by_run: dict[str, list[Classified]],
) -> list[AgentStats]:
    """Aggregate runs by agent name, in order of first appearance."""
    stats: dict[str, AgentStats] = {}
    for run in sorted(runs.values(), key=lambda r: (r.start_ns, r.end_ns)):
        s = stats.setdefault(run.name, AgentStats(name=run.name))
        s.runs += 1
        s.duration_ms += run.duration_ms
        for call in llm_by_run.get(run.run_id, []):
            s.llm_calls += 1
            if call.input_tokens is not None:
                s.input_tokens = (s.input_tokens or 0) + call.input_tokens
            if call.output_tokens is not None:
                s.output_tokens = (s.output_tokens or 0) + call.output_tokens
            if call.cost is not None:
                s.cost = (s.cost or 0.0) + call.cost
    for tool in tools:
        stats[tool.agent].tool_calls += 1
    return list(stats.values())
