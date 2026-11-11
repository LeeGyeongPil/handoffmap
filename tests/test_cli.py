"""AC-7, AC-8, AC-10: CLI output, explain, exit codes, no message content."""

from __future__ import annotations

import json
import subprocess
import sys

import pytest

import handoffmap
from handoffmap.cli import FORMATS, SAMPLES, main

from conftest import FIXTURES, sample_path


def test_default_markdown_report(capsys):
    assert main(["--sample", "pydantic-ai"]) == 0
    out = capsys.readouterr().out
    for needle in ("```mermaid", "par", "| agent |", "orchestrator", "262", "mock"):
        assert needle in out


def test_json_output_schema(capsys):
    assert main(["--sample", "pydantic-ai", "--format", "json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert {"agents", "edges", "parallel", "warnings"} <= set(data)
    assert [e["kind"] for e in data["edges"]] == ["root", "as_tool", "as_tool"]
    assert data["totals"]["input_tokens"] == 262
    assert data["parallel"][0]["agent"] == "orchestrator"


def test_explain_shows_convention_and_ignored_wrapper(capsys):
    assert main(["--sample", "openinference", "--explain"]) == 0
    out = capsys.readouterr().out
    for needle in ("openinference", "17 spans", "Agent workflow", "handoff", "as_tool via summarize"):
        assert needle in out


def test_explain_goes_to_stderr_for_json(capsys):
    assert main(["--sample", "openinference", "--format", "json", "--explain"]) == 0
    captured = capsys.readouterr()
    json.loads(captured.out)  # stdout stays pure JSON
    assert "convention: openinference" in captured.err


def test_exit_codes(tmp_path, capsys):
    not_otlp = tmp_path / "x.json"
    not_otlp.write_text('{"hello": 1}', encoding="utf-8")
    assert main([str(not_otlp)]) == 2
    assert "not an OTLP trace" in capsys.readouterr().err

    assert main([str(tmp_path / "missing.json")]) == 2
    assert "file not found" in capsys.readouterr().err

    # a valid OTLP trace without any agent span
    (trace,) = handoffmap.load(FIXTURES / "synthetic_loop.otlp.json")
    data = json.loads((FIXTURES / "synthetic_loop.otlp.json").read_text(encoding="utf-8"))
    spans = data["resourceSpans"][0]["scopeSpans"][0]["spans"]
    data["resourceSpans"][0]["scopeSpans"][0]["spans"] = [s for s in spans if "invoke_agent" not in s["name"]]
    no_agents = tmp_path / "no-agents.json"
    no_agents.write_text(json.dumps(data), encoding="utf-8")
    assert main([str(no_agents)]) == 1
    assert "no agent spans" in capsys.readouterr().err

    assert main(["--sample", "pydantic-ai", "--trace", "ffff"]) == 2
    assert "no trace id starts with" in capsys.readouterr().err


def test_argument_errors_exit_2():
    with pytest.raises(SystemExit) as e:
        main([])
    assert e.value.code == 2
    with pytest.raises(SystemExit) as e:
        main(["--sample", "pydantic-ai", "--max-parallel", "0"])
    assert e.value.code == 2


def test_output_file_and_trace_selection(tmp_path, capsys):
    out = tmp_path / "flow.md"
    assert main(["--sample", "pydantic-ai", "-o", str(out)]) == 0
    assert capsys.readouterr().out == ""
    assert "sequenceDiagram" in out.read_text(encoding="utf-8")
    trace_id = handoffmap.load(sample_path("pydantic-ai"))[0].trace_id
    assert main(["--sample", "pydantic-ai", "--trace", trace_id[:6], "--format", "table"]) == 0


def test_multi_trace_file(tmp_path, capsys):
    both = tmp_path / "both.jsonl"
    texts = [json.dumps(json.loads(sample_path(n).read_text(encoding="utf-8"))) for n in ("pydantic-ai", "openinference")]
    both.write_text("\n".join(texts), encoding="utf-8")
    assert main([str(both), "--format", "json"]) == 0
    assert len(json.loads(capsys.readouterr().out)["traces"]) == 2


def _message_strings(path):
    """Every prompt/response text recorded in a sample (the things that must never be printed)."""
    texts = set()
    for trace in handoffmap.load(path):
        for span in trace.spans:
            for key in ("gen_ai.input.messages", "gen_ai.output.messages", "pydantic_ai.all_messages", "input.value", "output.value"):
                value = span.attributes.get(key)
                if isinstance(value, str) and len(value) > 8:
                    texts.add(value)
    return texts


@pytest.mark.parametrize("sample", sorted(SAMPLES))
@pytest.mark.parametrize("fmt", FORMATS)
def test_no_message_content_in_any_format(sample, fmt, capsys):
    secrets = _message_strings(sample_path(sample))
    assert secrets  # the sample really contains message attributes, so this test can fail
    assert main(["--sample", sample, "--format", fmt, "--explain"]) == 0
    captured = capsys.readouterr()
    shown = captured.out + captured.err
    for text in secrets:
        assert text not in shown


def test_python_dash_m_runs():
    proc = subprocess.run(
        [sys.executable, "-m", "handoffmap", "--sample", "pydantic-ai", "--format", "mermaid"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0 and proc.stdout.startswith("sequenceDiagram")
