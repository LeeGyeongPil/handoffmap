"""Fold a span tree into an agent-level flow.

The idea: an agent run is a span the adapter calls ``agent``. For every run we
walk up the parent chain until we meet another agent run. What lies on the way
decides the edge kind:

* ``as_tool``  - a tool span sits between them (the sub-agent runs inside a tool);
* ``call``     - nothing in between (nested agent span, no tool);
* ``handoff``  - no agent ancestor, but the adapter says which agent handed over
  (OpenInference ``graph.node.parent_id``): the new agent is a *sibling* span;
* ``root``     - nobody started it.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .adapters import Classified, classify
from .checks import find_warnings
from .errors import NoAgentSpansError
from .model import AgentRun, Edge, Flow, Member, ParallelGroup, Span, ToolCall, Trace
from .usage import collect_stats


@dataclass
class _Context:
    spans: dict[str, Span]
    info: dict[str, Classified]
    runs: dict[str, AgentRun]

    def owner_of(self, span: Span) -> tuple[AgentRun | None, list[Span]]:
        """Nearest agent run above ``span`` and the spans passed on the way up.

        If the parent chain is broken (a parent span was never exported) we fall
        back to the narrowest agent run whose time window contains the span.
        """
        chain: list[Span] = []
        seen = {span.span_id}
        current = span
        while current.parent_id is not None:
            parent = self.spans.get(current.parent_id)
            if parent is None or parent.span_id in seen:
                return self._owner_by_time(span), chain  # chain is broken
            if parent.span_id in self.runs:
                return self.runs[parent.span_id], chain
            chain.append(parent)
            seen.add(parent.span_id)
            current = parent
        return None, chain

    def _owner_by_time(self, span: Span) -> AgentRun | None:
        best: AgentRun | None = None
        for run in self.runs.values():
            if run.run_id == span.span_id:
                continue
            if run.start_ns <= span.start_ns and span.end_ns <= run.end_ns:
                if best is None or (run.end_ns - run.start_ns) < (best.end_ns - best.start_ns):
                    best = run
        return best


def _detect_convention(info: dict[str, Classified]) -> str:
    found = {c.convention for c in info.values()}
    if len(found) == 1:
        return next(iter(found))
    return "mixed" if found else "unknown"


def _pick_handoff_source(ctx: _Context, run: AgentRun, source_name: str) -> AgentRun | None:
    """The run named ``source_name`` that most plausibly handed over to ``run``."""
    candidates = [r for r in ctx.runs.values() if r.name == source_name and r.run_id != run.run_id]
    if not candidates:
        return None
    earlier = [r for r in candidates if r.start_ns <= run.start_ns]
    pool = earlier or candidates
    return max(pool, key=lambda r: r.start_ns)


def _parallel_groups(runs: dict[str, AgentRun], edges: list[Edge], tools: list[ToolCall]) -> list[ParallelGroup]:
    """Group activities of one run whose [start, end) windows overlap."""
    groups: list[ParallelGroup] = []
    for run in sorted(runs.values(), key=lambda r: r.start_ns):
        members = [
            Member("agent", e.callee, e.start_ns, e.end_ns, e.callee_run)
            for e in edges
            if e.caller_run == run.run_id and e.kind in ("call", "as_tool")
        ]
        members += [
            Member("tool", t.name, t.start_ns, t.end_ns, t.span_id)
            for t in tools
            if t.run_id == run.run_id and not t.wraps_agent
        ]
        members.sort(key=lambda m: (m.start_ns, m.end_ns))
        cluster: list[Member] = []
        cluster_end = 0
        for m in members:
            if cluster and m.start_ns < cluster_end:  # half-open: touching is not overlapping
                cluster.append(m)
                cluster_end = max(cluster_end, m.end_ns)
                continue
            if len(cluster) > 1:
                groups.append(ParallelGroup(run.run_id, run.name, cluster))
            cluster, cluster_end = [m], m.end_ns
        if len(cluster) > 1:
            groups.append(ParallelGroup(run.run_id, run.name, cluster))
    return groups


def analyze(trace: Trace, *, repeat_threshold: int = 3, max_parallel: int = 8) -> Flow:
    """Turn one trace into a :class:`~handoffmap.model.Flow`.

    Raises :class:`~handoffmap.errors.NoAgentSpansError` if the trace has no agent spans.
    """
    if repeat_threshold < 1 or max_parallel < 1:
        raise ValueError("repeat_threshold and max_parallel must be >= 1")

    unknown: set[str] = set()
    spans = {s.span_id: s for s in trace.spans}
    info: dict[str, Classified] = {}
    for s in trace.spans:
        c = classify(s, unknown)
        if c is not None:
            info[s.span_id] = c

    runs = {
        sid: AgentRun(sid, c.name, spans[sid].start_ns, spans[sid].end_ns)
        for sid, c in info.items()
        if c.role == "agent"
    }
    if not runs:
        raise NoAgentSpansError(
            f"no agent spans found in trace {trace.trace_id} ({len(trace.spans)} spans). "
            "Expected spans with gen_ai.operation.name=invoke_agent (OTel GenAI) or "
            "openinference.span.kind=AGENT with an agent.name (OpenInference)."
        )
    ctx = _Context(spans, info, runs)

    edges: list[Edge] = []
    wrapper_tools: set[str] = set()
    for run in sorted(runs.values(), key=lambda r: (r.start_ns, r.end_ns)):
        caller, chain = ctx.owner_of(spans[run.run_id])
        tool_spans = [
            s for s in chain if info.get(s.span_id) and info[s.span_id].role == "tool" and not info[s.span_id].handoff_marker
        ]
        if caller is not None:
            if tool_spans:
                via = tool_spans[-1]  # the tool closest to the caller
                wrapper_tools.add(via.span_id)
                kind, via_name = "as_tool", info[via.span_id].name
            else:
                kind, via_name = "call", None
            edges.append(Edge(kind, caller.name, run.name, caller.run_id, run.run_id, via_name, run.start_ns, run.end_ns))
            continue
        source_name = info[run.run_id].handoff_from
        source = _pick_handoff_source(ctx, run, source_name) if source_name else None
        if source is not None:
            edges.append(Edge("handoff", source.name, run.name, source.run_id, run.run_id, None, run.start_ns, run.end_ns))
        else:
            edges.append(Edge("root", None, run.name, None, run.run_id, None, run.start_ns, run.end_ns))

    tools: list[ToolCall] = []
    for sid, c in info.items():
        if c.role != "tool" or c.handoff_marker:
            continue
        owner, _ = ctx.owner_of(spans[sid])
        if owner is None:
            continue
        s = spans[sid]
        tools.append(ToolCall(owner.run_id, owner.name, c.name, sid, s.start_ns, s.end_ns, sid in wrapper_tools))
    tools.sort(key=lambda t: t.start_ns)

    llm_by_run: dict[str, list[Classified]] = {}
    for sid, c in info.items():
        if c.role == "llm":
            owner, _ = ctx.owner_of(spans[sid])
            if owner is not None:
                llm_by_run.setdefault(owner.run_id, []).append(c)

    parallel = _parallel_groups(runs, edges, tools)
    agents = collect_stats(runs, tools, llm_by_run)
    warnings = find_warnings(edges, parallel, repeat_threshold, max_parallel)

    reported = [c.reported_usage for c in info.values() if c.role == "agent" and c.reported_usage]
    reported_total = (sum(r[0] for r in reported), sum(r[1] for r in reported)) if reported else None

    return Flow(
        trace_id=trace.trace_id,
        convention=_detect_convention(info),
        span_count=len(trace.spans),
        runs=runs,
        edges=edges,
        tools=tools,
        parallel=parallel,
        agents=agents,
        warnings=warnings,
        ignored=[c.name for c in info.values() if c.role == "ignored"],
        unknown_operations=sorted(unknown),
        reported_usage=reported_total,
    )
