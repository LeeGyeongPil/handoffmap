# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "opentelemetry-sdk==1.45.2",
#   "opentelemetry-exporter-otlp-proto-common==1.45.2",
# ]
# ///
"""Save your own app's spans as an OTLP JSON file that handoffmap can read.

The Python SDK has no OTLP/JSON file exporter, so collect spans in memory and
encode them yourself. Copy the marked part into your app.

    uv run examples/save_otlp_json.py trace.json
"""

import json
import sys

from google.protobuf.json_format import MessageToDict
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# --- copy from here -------------------------------------------------------
exporter = InMemorySpanExporter()
provider = TracerProvider()
provider.add_span_processor(SimpleSpanProcessor(exporter))
# ... pass `provider` to your framework's instrumentation, then run your agents ...


def save(path: str) -> None:
    spans = exporter.get_finished_spans()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(MessageToDict(encode_spans(spans)), f)
# --- to here --------------------------------------------------------------


if __name__ == "__main__":
    # demo: one hand-made agent span so the file is not empty
    tracer = provider.get_tracer("demo")
    with tracer.start_as_current_span("invoke_agent demo", attributes={"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": "demo"}):
        pass
    out = sys.argv[1] if len(sys.argv) > 1 else "trace.json"
    save(out)
    print(f"wrote {out}; now run: handoffmap {out}")
