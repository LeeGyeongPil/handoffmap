"""AC-9: flow warnings and run instances."""

from __future__ import annotations

from conftest import FIXTURES, flow_of, sample_path


def test_repeated_delegation_warning():
    flow = flow_of(FIXTURES / "synthetic_loop.otlp.json")
    warnings = [w for w in flow.warnings if w.code == "repeated-delegation"]
    assert len(warnings) == 1
    assert "planner -> coder" in warnings[0].message and "3 times" in warnings[0].message
    coder = next(a for a in flow.agents if a.name == "coder")
    assert coder.runs == 3  # three instances, not one merged point
    assert len([r for r in flow.runs.values() if r.name == "coder"]) == 3


def test_repeat_threshold_is_configurable():
    flow = flow_of(FIXTURES / "synthetic_loop.otlp.json", repeat_threshold=4)
    assert flow.warnings == []


def test_wide_parallel_warning():
    assert flow_of(sample_path("pydantic-ai")).warnings == []
    flow = flow_of(sample_path("pydantic-ai"), max_parallel=1)
    assert [w.code for w in flow.warnings] == ["wide-parallel"]
