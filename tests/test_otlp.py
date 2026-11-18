"""AC-1: loader accepts base64/hex ids, kind names/ints, and splits JSONL by trace."""

from __future__ import annotations

import copy
import json
import re

import pytest

import handoffmap
from handoffmap.errors import NotOtlpError
from handoffmap.otlp import normalize_id, parse

from helpers import FIXTURES, sample_path


def _shape(trace):
    ids = {s.span_id for s in trace.spans}
    parents = {s.span_id: s.parent_id for s in trace.spans}
    kinds = {s.span_id: s.kind for s in trace.spans}
    return ids, parents, kinds


def test_hex_and_base64_ids_are_equivalent():
    (b64,) = handoffmap.load(sample_path("pydantic-ai"))
    (hexed,) = handoffmap.load(FIXTURES / "pydantic_ai_v5.hex.otlp.json")
    assert len(b64.spans) == len(hexed.spans) == 11
    ids, parents, kinds = _shape(b64)
    assert all(re.fullmatch(r"[0-9a-f]{16}", i) for i in ids)
    assert b64.trace_id == hexed.trace_id and re.fullmatch(r"[0-9a-f]{32}", b64.trace_id)
    assert _shape(hexed) == (ids, parents, kinds)  # same ids, same parents, same integer kinds


def test_jsonl_splits_traces(tmp_path):
    one = sample_path("pydantic-ai").read_text(encoding="utf-8")
    two = sample_path("openinference").read_text(encoding="utf-8")
    # JSONL: one compact request per line
    import json

    jsonl = "\n".join(json.dumps(json.loads(t)) for t in (one, two)) + "\n"
    path = tmp_path / "both.jsonl"
    path.write_text(jsonl, encoding="utf-8")
    traces = handoffmap.load(path)
    assert [len(t.spans) for t in traces] == [11, 17]
    assert len({t.trace_id for t in traces}) == 2


def test_same_trace_across_requests_is_merged():
    text = sample_path("pydantic-ai").read_text(encoding="utf-8")
    import json

    line = json.dumps(json.loads(text))
    traces = parse(line + "\n" + line)
    assert len(traces) == 1  # same trace id twice -> one trace (spans repeated, still one trace)


def test_int_value_string_and_number():
    from handoffmap.otlp import _decode_value

    assert _decode_value({"intValue": "42"}) == 42
    assert _decode_value({"intValue": 42}) == 42
    assert _decode_value({"arrayValue": {"values": [{"stringValue": "a"}]}}) == ["a"]


@pytest.mark.parametrize("raw, expected", [("AA==", None), ("", None), (None, None), ("0" * 16, None)])
def test_missing_or_zero_ids_become_none(raw, expected):
    assert normalize_id(raw) is expected


def test_bad_id_has_helpful_error():
    with pytest.raises(NotOtlpError, match="neither hex nor base64"):
        normalize_id("not an id!")


@pytest.mark.parametrize("text", ["", "{}", "[]", '{"resourceSpans": 3}', "plain text", '{"resourceSpans": []}'])
def test_not_otlp_inputs_raise(text):
    with pytest.raises(NotOtlpError, match="not an OTLP trace"):
        parse(text)


def test_missing_file_is_input_error(tmp_path):
    with pytest.raises(NotOtlpError, match="file not found"):
        handoffmap.load(tmp_path / "nope.json")


_GOOD_SPAN = {"traceId": "0" * 31 + "1", "spanId": "0" * 15 + "1", "name": "x"}


@pytest.mark.parametrize(
    "payload",
    [
        {"resourceSpans": [1]},
        {"resourceSpans": [{"scopeSpans": [1]}]},
        {"resourceSpans": [{"scopeSpans": [{"spans": [1]}]}]},
        {"resourceSpans": [{"scopeSpans": [{"spans": None}]}]},
        {"resourceSpans": [{"scopeSpans": None}]},
        {"resourceSpans": [{"scopeSpans": {"spans": []}}]},
    ],
)
def test_malformed_structure_is_not_otlp(payload, tmp_path, capsys):
    import json

    from handoffmap.cli import main

    with pytest.raises(NotOtlpError):
        parse(json.dumps(payload))
    path = tmp_path / "bad.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert main([str(path)]) == 2
    assert "not an OTLP trace" in capsys.readouterr().err


@pytest.mark.parametrize(
    "payload",
    [
        {"resourceSpans": []},
        {"resourceSpans": [{}]},
        {"resourceSpans": [{"scopeSpans": []}]},
        {"resourceSpans": [{"instrumentationLibrarySpans": []}]},
        {"resourceSpans": [{"scopeSpans": [{}]}]},
        {"resourceSpans": [{"scopeSpans": [{"spans": []}]}]},
        {"resourceSpans": [{"scopeSpans": [], "instrumentationLibrarySpans": []}]},
    ],
)
def test_empty_or_missing_lists_stay_valid(payload):
    import json

    from handoffmap.otlp import _spans_of_request

    # structurally valid (no NotOtlpError about structure), just no spans
    assert _spans_of_request(payload) == []


@pytest.mark.parametrize(
    "payload",
    [
        {"resourceSpans": [1]},
        {"resourceSpans": [{"scopeSpans": [1]}]},
        {"resourceSpans": [{"instrumentationLibrarySpans": [1]}]},
        {"resourceSpans": [{"scopeSpans": [{"spans": [1]}]}]},
        {"resourceSpans": [{"scopeSpans": [{"spans": None}]}]},
        {"resourceSpans": [{"scopeSpans": None}]},
    ],
)
def test_korean_structure_errors_have_no_english_fragments(payload):
    import json

    with pytest.raises(NotOtlpError) as info:
        parse(json.dumps(payload))
    ko = info.value.localized("ko")
    assert ko.startswith("OTLP 트레이스가 아닙니다")
    for word in ("must be", "an object", "a list", "item"):
        assert word not in ko


def test_null_array_value_does_not_raise():
    import json

    span = dict(_GOOD_SPAN)
    span["attributes"] = [
        {"key": "a", "value": {"arrayValue": None}},
        {"key": "k", "value": {"kvlistValue": None}},
        {"key": "ok", "value": {"stringValue": "v"}},
    ]
    payload = {"resourceSpans": [{"scopeSpans": [{"spans": [span]}]}]}
    (trace,) = parse(json.dumps(payload))
    attrs = trace.spans[0].attributes
    assert attrs == {"a": [], "k": {}, "ok": "v"}


# --- scopeSpans / instrumentationLibrarySpans choice (Q-3) -------------------

_AGENT_SPAN = {
    "traceId": "0" * 31 + "1",
    "spanId": "0" * 15 + "1",
    "name": "invoke_agent a",
    "attributes": [
        {"key": "gen_ai.operation.name", "value": {"stringValue": "invoke_agent"}},
        {"key": "gen_ai.agent.name", "value": {"stringValue": "a"}},
    ],
}
_ID_A = "0" * 15 + "1"
_ID_B = "0" * 15 + "2"


def _agent(span_id: str) -> dict:
    span = copy.deepcopy(_AGENT_SPAN)
    span["spanId"] = span_id
    return span


def _old_rule_span_ids(payload: dict) -> list[str]:
    """The 0.2.0 choice, kept as an oracle: scopeSpans if truthy, else instrumentationLibrarySpans."""
    ids = []
    for resource in payload["resourceSpans"]:
        for scope_spans in resource.get("scopeSpans") or resource.get("instrumentationLibrarySpans") or []:
            ids += [raw["spanId"] for raw in scope_spans.get("spans", [])]
    return ids


@pytest.mark.parametrize(
    "resources, expected",
    [
        # Q-3: an empty scopeSpans list must not hide spans kept under the older name
        ([{"scopeSpans": [], "instrumentationLibrarySpans": [{"spans": [_agent(_ID_A)]}]}], [_ID_A]),
        # ...also when another resource is fine (spans were silently dropped there)
        (
            [
                {"scopeSpans": [{"spans": [_agent(_ID_A)]}]},
                {"scopeSpans": [], "instrumentationLibrarySpans": [{"spans": [_agent(_ID_B)]}]},
            ],
            [_ID_A, _ID_B],
        ),
        ([{"instrumentationLibrarySpans": [{"spans": [_agent(_ID_A)]}]}], [_ID_A]),
        ([{"scopeSpans": [{"spans": [_agent(_ID_A)]}]}], [_ID_A]),
        ([{"scopeSpans": [{"spans": [_agent(_ID_A)]}]}, {"scopeSpans": []}], [_ID_A]),
        # a non-empty scopeSpans wins; the older name is not read at all (as in 0.2.0)
        (
            [{"scopeSpans": [{"spans": [_agent(_ID_A)]}], "instrumentationLibrarySpans": [{"spans": [_agent(_ID_B)]}]}],
            [_ID_A],
        ),
        ([{"scopeSpans": [{"spans": [_agent(_ID_A)]}], "instrumentationLibrarySpans": None}], [_ID_A]),
    ],
)
def test_scope_list_choice_matches_previous_release(resources, expected):
    payload = {"resourceSpans": resources}
    (trace,) = parse(json.dumps(payload))
    got = [s.span_id for s in trace.spans]
    assert got == expected
    assert got == _old_rule_span_ids(payload)  # same spans as the 0.2.0 loader picked


def test_empty_scope_spans_fallback_through_cli(tmp_path, capsys):
    from handoffmap.cli import main

    payload = {"resourceSpans": [{"scopeSpans": [], "instrumentationLibrarySpans": [{"spans": [_agent(_ID_A)]}]}]}
    path = tmp_path / "old.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    assert main(["--format", "json", str(path)]) == 0  # not exit 2 "no spans found"
    data = json.loads(capsys.readouterr().out)
    assert [a["name"] for a in data["agents"]] == ["a"]


@pytest.mark.parametrize(
    "resource, key",
    [
        # once the older name is used, it gets the same structure checks as scopeSpans
        ({"scopeSpans": [], "instrumentationLibrarySpans": None}, "instrumentationLibrarySpans"),
        ({"instrumentationLibrarySpans": None}, "instrumentationLibrarySpans"),
        ({"scopeSpans": [], "instrumentationLibrarySpans": {"spans": []}}, "instrumentationLibrarySpans"),
        ({"scopeSpans": [], "instrumentationLibrarySpans": [1]}, "instrumentationLibrarySpans"),
        # null is "not a list", not "empty" (fix_scope AC-1): reported, never skipped silently
        ({"scopeSpans": None, "instrumentationLibrarySpans": [{"spans": [_agent(_ID_A)]}]}, "scopeSpans"),
    ],
)
def test_fallback_list_structure_errors(resource, key, tmp_path, capsys):
    from handoffmap.cli import main

    text = json.dumps({"resourceSpans": [resource]})
    with pytest.raises(NotOtlpError) as info:
        parse(text)
    assert f"'{key}'" in str(info.value)
    ko = info.value.localized("ko")
    assert ko.startswith("OTLP 트레이스가 아닙니다") and f"'{key}'" in ko
    for word in ("must be", "an object", "a list", "item"):
        assert word not in ko
    path = tmp_path / "bad.json"
    path.write_text(text, encoding="utf-8")
    for lang, prefix in (("en", "handoffmap: not an OTLP trace"), ("ko", "handoffmap: OTLP 트레이스가 아닙니다")):
        assert main(["--lang", lang, str(path)]) == 2
        err = capsys.readouterr().err
        assert err.startswith(prefix) and len(err.strip().splitlines()) == 1


@pytest.mark.parametrize(
    "scope_spans, expected",
    [
        ({"scope": {"name": "new"}, "instrumentationLibrary": {"name": "old"}}, "new"),
        ({"scope": {}, "instrumentationLibrary": {"name": "old"}}, "old"),
        ({"scope": None, "instrumentationLibrary": {"name": "old"}}, "old"),
        ({"scope": "x", "instrumentationLibrary": {"name": "old"}}, "old"),
        ({"instrumentationLibrary": {"name": "old"}}, "old"),
        ({"scope": "x"}, ""),
        ({}, ""),
    ],
)
def test_scope_name_falls_back_to_instrumentation_library(scope_spans, expected):
    block = dict(scope_spans, spans=[_agent(_ID_A)])
    (trace,) = parse(json.dumps({"resourceSpans": [{"scopeSpans": [block]}]}))
    assert trace.spans[0].scope == expected
