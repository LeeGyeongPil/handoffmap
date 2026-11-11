"""Read OTLP JSON / JSONL trace exports into :class:`~handoffmap.model.Trace` objects.

Two id encodings exist in the wild:

* protobuf-JSON (what ``MessageToDict`` writes): ids are base64 strings, span
  kinds are names such as ``SPAN_KIND_CLIENT``;
* the OTLP/JSON spec (Collector ``file`` exporter, JS SDK): ids are hex, kinds
  are integers.

Both are accepted and normalized to lowercase hex ids and integer kinds.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from pathlib import Path
from typing import Any

from .errors import NotOtlpError
from .model import Span, Trace

_HEX_ID = re.compile(r"^(?:[0-9a-fA-F]{16}|[0-9a-fA-F]{32})$")
_KINDS = {
    "SPAN_KIND_UNSPECIFIED": 0,
    "SPAN_KIND_INTERNAL": 1,
    "SPAN_KIND_SERVER": 2,
    "SPAN_KIND_CLIENT": 3,
    "SPAN_KIND_PRODUCER": 4,
    "SPAN_KIND_CONSUMER": 5,
}


def normalize_id(raw: Any) -> str | None:
    """Return a lowercase hex id, or None for a missing/all-zero id."""
    if raw is None or raw == "":
        return None
    if not isinstance(raw, str):
        raise NotOtlpError(f"not an OTLP trace: span/trace id must be a string, got {type(raw).__name__}")
    if _HEX_ID.match(raw):
        hex_id = raw.lower()
    else:
        try:
            hex_id = base64.b64decode(raw, validate=True).hex()
        except (binascii.Error, ValueError) as exc:
            raise NotOtlpError(f"not an OTLP trace: id {raw!r} is neither hex nor base64") from exc
    if set(hex_id) == {"0"}:
        return None
    return hex_id


def _decode_value(value: Any) -> Any:
    """Decode an OTLP AnyValue (``{"stringValue": ...}`` and friends) to a Python value."""
    if not isinstance(value, dict):
        return value
    if "stringValue" in value:
        return value["stringValue"]
    if "intValue" in value:
        try:
            return int(value["intValue"])  # int64 is a JSON string in protobuf-JSON
        except (TypeError, ValueError):
            return value["intValue"]
    if "doubleValue" in value:
        return value["doubleValue"]
    if "boolValue" in value:
        return value["boolValue"]
    if "arrayValue" in value:
        return [_decode_value(v) for v in value["arrayValue"].get("values", [])]
    if "kvlistValue" in value:
        return _decode_attrs(value["kvlistValue"].get("values", []))
    if "bytesValue" in value:
        return value["bytesValue"]
    return None


def _decode_attrs(items: Any) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for item in items or []:
        if isinstance(item, dict) and "key" in item:
            out[item["key"]] = _decode_value(item.get("value"))
    return out


def _kind(raw: Any) -> int:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        if raw in _KINDS:
            return _KINDS[raw]
        if raw.isdigit():
            return int(raw)
    return 0


def _int(raw: Any) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return 0


def _spans_of_request(request: Any) -> list[Span]:
    if not isinstance(request, dict) or not isinstance(request.get("resourceSpans"), list):
        raise NotOtlpError("not an OTLP trace: expected a JSON object with a 'resourceSpans' list")
    spans: list[Span] = []
    for resource_spans in request["resourceSpans"]:
        # older exporters use instrumentationLibrarySpans instead of scopeSpans
        scope_list = resource_spans.get("scopeSpans") or resource_spans.get("instrumentationLibrarySpans") or []
        for scope_spans in scope_list:
            scope = scope_spans.get("scope") or scope_spans.get("instrumentationLibrary") or {}
            for raw in scope_spans.get("spans", []):
                trace_id = normalize_id(raw.get("traceId"))
                span_id = normalize_id(raw.get("spanId"))
                if trace_id is None or span_id is None:
                    raise NotOtlpError("not an OTLP trace: a span has no traceId/spanId")
                spans.append(
                    Span(
                        trace_id=trace_id,
                        span_id=span_id,
                        parent_id=normalize_id(raw.get("parentSpanId")),
                        name=str(raw.get("name", "")),
                        kind=_kind(raw.get("kind")),
                        start_ns=_int(raw.get("startTimeUnixNano")),
                        end_ns=_int(raw.get("endTimeUnixNano")),
                        attributes=_decode_attrs(raw.get("attributes")),
                        scope=str(scope.get("name", "")),
                    )
                )
    return spans


def parse(text: str) -> list[Trace]:
    """Parse OTLP JSON (one request) or JSONL (one request per line) text."""
    requests: list[Any]
    try:
        requests = [json.loads(text)]
    except json.JSONDecodeError as whole_error:
        lines = [ln for ln in text.splitlines() if ln.strip()]
        try:
            requests = [json.loads(ln) for ln in lines]
        except json.JSONDecodeError:
            raise NotOtlpError(f"not an OTLP trace: invalid JSON ({whole_error.msg}, line {whole_error.lineno})") from None
        if not requests:
            raise NotOtlpError("not an OTLP trace: the input is empty") from None

    traces: dict[str, Trace] = {}
    for request in requests:
        for span in _spans_of_request(request):
            traces.setdefault(span.trace_id, Trace(span.trace_id)).spans.append(span)
    if not traces:
        raise NotOtlpError("not an OTLP trace: no spans found")
    return list(traces.values())


def load(path: str | Path) -> list[Trace]:
    """Read an OTLP JSON or JSONL file and return one :class:`Trace` per trace id."""
    p = Path(path)
    try:
        text = p.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise NotOtlpError(f"file not found: {p}") from None
    except (OSError, UnicodeDecodeError) as exc:
        raise NotOtlpError(f"cannot read {p}: {exc}") from None
    return parse(text)
