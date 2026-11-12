"""AC-2, AC-3, AC-4: agent detection, edge kinds, parallel groups."""

from __future__ import annotations

import pytest

import handoffmap

from helpers import FIXTURES, edge_keys, flow_of, sample_path

PYDANTIC_EDGES = [
    (None, "orchestrator", "root"),
    ("orchestrator", "researcher", "as_tool"),
    ("orchestrator", "writer", "as_tool"),
]


@pytest.mark.parametrize("name", ["pydantic-ai-v2", "pydantic-ai", "pydantic-ai-v6"])
def test_pydantic_ai_v2_v5_v6_same_edges(name):
    # v2 names the span "agent run" / "running tool"; v5 and v6 say "invoke_agent X" / "execute_tool X".
    flow = flow_of(sample_path(name))
    assert flow.convention == "otel-genai"
    assert edge_keys(flow) == PYDANTIC_EDGES


def test_openinference_handoff_and_as_tool():
    flow = flow_of(sample_path("openinference"))
    assert flow.convention == "openinference"
    assert {r.name for r in flow.runs.values()} == {"triage", "billing", "summarizer"}
    assert edge_keys(flow) == [
        (None, "triage", "root"),
        ("triage", "billing", "handoff"),
        ("billing", "summarizer", "as_tool"),
    ]
    assert [e.via for e in flow.edges] == [None, None, "summarize"]
    # the unnamed "Agent workflow" AGENT wrapper is reported as ignored, not counted
    assert flow.ignored == ["Agent workflow"]


def test_handoff_tool_marker_is_not_a_tool_call():
    flow = flow_of(sample_path("openinference"))
    assert "handoff to billing" not in {t.name for t in flow.tools}
    assert {t.name for t in flow.tools} == {"lookup", "summarize"}


def test_parallel_groups():
    v5 = flow_of(sample_path("pydantic-ai"))
    assert [(g.agent, {m.label for m in g.members}) for g in v5.parallel] == [
        ("orchestrator", {"agent:researcher", "agent:writer"})
    ]
    oi = flow_of(sample_path("openinference"))
    assert [(g.agent, {m.label for m in g.members}) for g in oi.parallel] == [
        ("billing", {"tool:lookup", "agent:summarizer"})
    ]


def test_touching_windows_are_not_parallel():
    # synthetic call fixture: lookup 12-30 ms, refund helper 35-60, audit 65-90 -> sequential
    flow = flow_of(FIXTURES / "synthetic_genai_call.otlp.json")
    assert flow.parallel == []


def test_synthetic_call_edge():
    flow = flow_of(FIXTURES / "synthetic_genai_call.otlp.json")
    keys = edge_keys(flow)
    assert (None, "billing-agent (v2)", "root") in keys
    assert ("billing-agent (v2)", "refund helper", "call") in keys
    # the parent span of "audit<log>" was never exported: found by time containment
    assert ("billing-agent (v2)", "audit<log>", "call") in keys


def test_no_agent_spans_error_is_actionable():
    (trace,) = handoffmap.load(FIXTURES / "synthetic_genai_call.otlp.json")
    trace.spans = [s for s in trace.spans if s.attributes.get("gen_ai.operation.name") != "invoke_agent"]
    with pytest.raises(handoffmap.NoAgentSpansError, match="no agent spans"):
        handoffmap.analyze(trace)


def test_analyze_rejects_bad_options():
    (trace,) = handoffmap.load(sample_path("pydantic-ai"))
    with pytest.raises(ValueError, match=">= 1"):
        handoffmap.analyze(trace, max_parallel=0)


def test_unknown_operation_is_passed_through_and_listed():
    (trace,) = handoffmap.load(FIXTURES / "synthetic_genai_call.otlp.json")
    extra = handoffmap.Span(trace.trace_id, "00000000000000aa", None, "plan x", 1, 0, 1, {"gen_ai.operation.name": "plan"})
    trace.spans.append(extra)
    flow = handoffmap.analyze(trace)
    assert flow.unknown_operations == ["plan"]
