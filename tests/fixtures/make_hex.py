"""Convert the protobuf-JSON sample (base64 ids, SPAN_KIND_* names) into the OTLP/JSON
spec form (hex ids, integer kinds). Run once; the output is committed.

    python tests/fixtures/make_hex.py
"""

import base64
import json
from pathlib import Path

HERE = Path(__file__).parent
SRC = HERE.parent.parent / "src" / "handoffmap" / "samples" / "pydantic_ai_v5.otlp.json"
DST = HERE / "pydantic_ai_v5.hex.otlp.json"
KINDS = {"SPAN_KIND_INTERNAL": 1, "SPAN_KIND_SERVER": 2, "SPAN_KIND_CLIENT": 3, "SPAN_KIND_PRODUCER": 4, "SPAN_KIND_CONSUMER": 5}


def to_hex(value: str) -> str:
    return base64.b64decode(value).hex()


def main() -> None:
    data = json.loads(SRC.read_text(encoding="utf-8"))
    for rs in data["resourceSpans"]:
        for ss in rs["scopeSpans"]:
            for span in ss["spans"]:
                span["traceId"] = to_hex(span["traceId"])
                span["spanId"] = to_hex(span["spanId"])
                if span.get("parentSpanId"):
                    span["parentSpanId"] = to_hex(span["parentSpanId"])
                span["kind"] = KINDS[span["kind"]]
    DST.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
