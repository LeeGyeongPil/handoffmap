"""AC-1: loader accepts base64/hex ids, kind names/ints, and splits JSONL by trace."""

from __future__ import annotations

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
