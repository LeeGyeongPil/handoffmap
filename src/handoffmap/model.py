"""Plain dataclasses shared by the loader, the normalizer and the renderers."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

EdgeKind = Literal["root", "call", "as_tool", "handoff"]


@dataclass
class Span:
    """One OTLP span with normalized ids (lowercase hex) and decoded attributes."""

    trace_id: str
    span_id: str
    parent_id: str | None
    name: str
    kind: int
    start_ns: int
    end_ns: int
    attributes: dict[str, Any] = field(default_factory=dict)
    scope: str = ""


@dataclass
class Trace:
    """All spans that share one trace id, in the order they were read."""

    trace_id: str
    spans: list[Span] = field(default_factory=list)


@dataclass
class AgentRun:
    """One execution of an agent (an instance, not a name)."""

    run_id: str  # span id of the agent span
    name: str
    start_ns: int
    end_ns: int

    @property
    def duration_ms(self) -> float:
        return (self.end_ns - self.start_ns) / 1e6


@dataclass
class Edge:
    """Who started whom. ``caller`` is None for ``root``."""

    kind: EdgeKind
    caller: str | None
    callee: str
    caller_run: str | None
    callee_run: str
    via: str | None  # tool name for as_tool, graph parent for handoff
    start_ns: int
    end_ns: int

    @property
    def duration_ms(self) -> float:
        return (self.end_ns - self.start_ns) / 1e6

    def key(self) -> tuple[str | None, str, str]:
        return (self.caller, self.callee, self.kind)


@dataclass
class ToolCall:
    """A tool invocation owned by an agent run."""

    run_id: str
    agent: str
    name: str
    span_id: str
    start_ns: int
    end_ns: int
    wraps_agent: bool  # True when a sub-agent ran inside this tool (as_tool)


@dataclass
class Member:
    """One concurrent activity inside a parallel group."""

    kind: Literal["agent", "tool"]
    name: str
    start_ns: int
    end_ns: int
    ref: str  # callee run id (agent) or tool span id (tool)

    @property
    def label(self) -> str:
        return f"{self.kind}:{self.name}"


@dataclass
class ParallelGroup:
    run_id: str
    agent: str
    members: list[Member]

    @property
    def start_ns(self) -> int:
        return min(m.start_ns for m in self.members)


@dataclass
class AgentStats:
    name: str
    runs: int = 0
    llm_calls: int = 0
    tool_calls: int = 0
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost: float | None = None
    duration_ms: float = 0.0


@dataclass
class FlowWarning:
    code: str
    message: str  # English; the JSON output keeps it as is
    args: dict[str, Any] = field(default_factory=dict)  # values for the localized message ``warn.<code>``


@dataclass
class Flow:
    trace_id: str
    convention: str
    span_count: int
    runs: dict[str, AgentRun]
    edges: list[Edge]
    tools: list[ToolCall]
    parallel: list[ParallelGroup]
    agents: list[AgentStats]
    warnings: list[FlowWarning]
    ignored: list[str] = field(default_factory=list)  # wrapper spans not counted as agents
    unknown_operations: list[str] = field(default_factory=list)
    reported_usage: tuple[int, int] | None = None  # invoke_agent usage attrs, never summed into totals

    @property
    def totals(self) -> AgentStats:
        total = AgentStats(name="total")
        for a in self.agents:
            total.runs += a.runs
            total.llm_calls += a.llm_calls
            total.tool_calls += a.tool_calls
            total.duration_ms += a.duration_ms
            if a.input_tokens is not None:
                total.input_tokens = (total.input_tokens or 0) + a.input_tokens
            if a.output_tokens is not None:
                total.output_tokens = (total.output_tokens or 0) + a.output_tokens
            if a.cost is not None:
                total.cost = (total.cost or 0.0) + a.cost
        return total
