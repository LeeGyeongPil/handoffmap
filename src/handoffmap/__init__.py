"""handoffmap: fold OTLP agent traces into a Mermaid flow and a per-agent table."""

from __future__ import annotations

from .errors import HandoffmapError, NoAgentSpansError, NotOtlpError
from .model import (
    AgentRun,
    AgentStats,
    Edge,
    Flow,
    FlowWarning,
    Member,
    ParallelGroup,
    Span,
    ToolCall,
    Trace,
)
from .normalize import analyze
from .otlp import load, parse
from .render.jsonout import to_dict
from .render.explain import render_explain
from .render.markdown import render_markdown
from .render.mermaid import render_mermaid
from .render.table import render_table

__version__ = "0.2.0"

__all__ = [
    "AgentRun",
    "AgentStats",
    "Edge",
    "Flow",
    "FlowWarning",
    "HandoffmapError",
    "Member",
    "NoAgentSpansError",
    "NotOtlpError",
    "ParallelGroup",
    "Span",
    "ToolCall",
    "Trace",
    "analyze",
    "load",
    "parse",
    "render_explain",
    "render_markdown",
    "render_mermaid",
    "render_table",
    "to_dict",
]
