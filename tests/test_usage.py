"""AC-5: tokens are summed once, at LLM spans."""

from __future__ import annotations

from handoffmap.render.table import render_table

from conftest import flow_of, sample_path


def test_tokens_summed_only_at_llm_spans():
    flow = flow_of(sample_path("pydantic-ai"))
    by_name = {a.name: a for a in flow.agents}
    got = {n: (a.input_tokens, a.output_tokens, a.llm_calls, a.tool_calls) for n, a in by_name.items()}
    assert got == {
        "orchestrator": (106, 21, 2, 2),
        "researcher": (105, 11, 2, 1),
        "writer": (51, 1, 1, 0),
    }
    total = flow.totals
    assert (total.input_tokens, total.output_tokens) == (262, 33)  # not 524: agent-span usage is not added
    assert flow.reported_usage is not None  # agent spans do carry usage attributes; kept for --explain only


def test_missing_tokens_render_dash():
    flow = flow_of(sample_path("openinference"))
    assert flow.totals.input_tokens is None
    table = render_table(flow)
    for line in table.splitlines()[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        assert cells[4] == "–" and cells[5] == "–"


def test_openinference_token_and_cost_attributes():
    import handoffmap

    (trace,) = handoffmap.load(sample_path("openinference"))
    for s in trace.spans:
        if s.attributes.get("openinference.span.kind") == "LLM":
            s.attributes.update({"llm.token_count.prompt": 7, "llm.token_count.completion": 3, "llm.cost.total": 0.5})
    flow = handoffmap.analyze(trace)
    total = flow.totals
    assert (total.input_tokens, total.output_tokens) == (28, 12)  # 4 LLM spans
    assert total.cost == 2.0
    assert "| cost |" in render_table(flow)
