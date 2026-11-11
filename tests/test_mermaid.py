"""AC-6: the Mermaid output is structurally valid and escapes awkward names."""

from __future__ import annotations

import re

import pytest

import handoffmap
from handoffmap.render.mermaid import escape

from conftest import FIXTURES, flow_of, sample_path

ENTITY = re.compile(r"#\d+;")


def _diagram(path, **kwargs):
    return handoffmap.render_mermaid(flow_of(path), **kwargs)


def _all_diagrams():
    paths = [sample_path(n) for n in ("pydantic-ai", "pydantic-ai-v2", "pydantic-ai-v6", "openinference")]
    return paths + [FIXTURES / "synthetic_genai_call.otlp.json", FIXTURES / "synthetic_loop.otlp.json"]


@pytest.mark.parametrize("path", _all_diagrams(), ids=lambda p: p.name)
def test_sequence_diagram_structure(path):
    text = _diagram(path)
    lines = text.splitlines()
    assert lines[0] == "sequenceDiagram"
    for line in lines[1:]:
        assert re.match(r"^\s+(participant a\d+ as .+|Note over a\d+: start|par concurrent|and|end|a\d+(->>|-\))a\d+: .+)$", line), line
    # par / end are balanced and never nested wrongly
    depth = 0
    for line in lines:
        word = line.strip().split(" ")[0]
        depth += word == "par"
        depth -= word == "end"
        assert depth >= 0
    assert depth == 0
    # every alias used in a message is declared
    declared = set(re.findall(r"participant (a\d+) as", text))
    used = set(re.findall(r"\b(a\d+)(?:->>|-\)|:)", text))
    assert used <= declared


def test_handoff_uses_async_arrow_and_par_block_appears():
    oi = _diagram(sample_path("openinference"))
    assert re.search(r"a1-\)a2: handoff", oi)
    assert "->>a3: as_tool via summarize" in oi
    v5 = _diagram(sample_path("pydantic-ai"))
    assert v5.count("par concurrent") == 1 and v5.count("\nand\n") == 0 and "    and\n" in v5


def test_no_tools_drops_tool_lines_and_single_branch_par():
    text = _diagram(sample_path("openinference"), show_tools=False)
    assert "tool lookup" not in text
    assert "par " not in text  # the group shrank to one branch


def test_participant_alias_escapes_special_chars():
    text = _diagram(FIXTURES / "synthetic_genai_call.otlp.json")
    participants = re.findall(r"^\s+participant (\S+) as (.*)$", text, re.M)
    assert [a for a, _ in participants] == ["a1", "a2", "a3"]
    assert all(re.fullmatch(r"a\d+", a) for a, _ in participants)
    assert participants[0][1] == "billing-agent (v2)"  # hyphen, space and parentheses are fine after `as`
    assert participants[2][1] == "audit#60;log#62;"
    # message lines: no raw ; or # outside of entity codes
    for line in text.splitlines():
        if "->>" in line or "-)" in line:
            message = line.split(": ", 1)[1]
            assert ";" not in ENTITY.sub("", message) and "#" not in ENTITY.sub("", message), line
    assert "lookup#59; ticket #35;5" in text


@pytest.mark.parametrize(
    "raw, expected",
    [("a;b", "a#59;b"), ("#1", "#35;1"), ("<x>", "#60;x#62;"), ("a\nb", "a b"), ("plain-name (v2)", "plain-name (v2)")],
)
def test_escape(raw, expected):
    assert escape(raw) == expected
