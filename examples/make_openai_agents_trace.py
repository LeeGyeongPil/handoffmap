# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "openai-agents==0.24.0",
#   "openinference-instrumentation-openai-agents==2.7.1",
#   "opentelemetry-sdk==1.45.2",
#   "opentelemetry-exporter-otlp-proto-common==1.45.2",
# ]
# ///
"""Make a handoff + agent-as-tool trace with the OpenAI Agents SDK and a scripted mock model.

    uv run examples/make_openai_agents_trace.py trace.json
    handoffmap trace.json --explain

No network and no real API key: ``ScriptedModel`` replays fixed replies, and
only the OpenInference instrumentation records spans (the SDK's own trace upload is removed).
"""

import asyncio
import json
import os
import sys

os.environ.setdefault("OPENAI_API_KEY", "not-a-real-key")  # the SDK wants one to exist; no request is ever sent

from agents import Agent, Runner, function_tool, set_trace_processors
from agents.testing.model import ScriptedModel, assistant_message, function_call
from agents.usage import Usage
from google.protobuf.json_format import MessageToDict
from openinference.instrumentation.openai_agents import OpenAIAgentsInstrumentor
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@function_tool
def lookup(account: str) -> str:
    """Look up an account."""
    return f"account {account}: ok"


def usage(tokens_in: int, tokens_out: int) -> Usage:
    return Usage(requests=1, input_tokens=tokens_in, output_tokens=tokens_out, total_tokens=tokens_in + tokens_out)


async def main(out_path: str) -> None:
    set_trace_processors([])  # drop the default uploader to OpenAI's trace backend; only OpenInference records
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "handoffmap-example"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    OpenAIAgentsInstrumentor().instrument(tracer_provider=provider)

    summarizer = Agent(
        name="summarizer", instructions="summarize",
        model=ScriptedModel([{"output": [assistant_message("short summary")], "usage": usage(20, 5)}], emit_traces=True),
    )
    billing = Agent(
        name="billing", instructions="handle billing",
        model=ScriptedModel(
            [
                # one turn asks for a plain tool and an agent-as-tool at once
                {"output": [function_call("lookup", {"account": "A1"}, call_id="c1"),
                            function_call("summarize", {"input": "long text"}, call_id="c2")], "usage": usage(40, 10)},
                {"output": [assistant_message("billing done")], "usage": usage(60, 8)},
            ],
            emit_traces=True,
        ),
        tools=[lookup, summarizer.as_tool(tool_name="summarize", tool_description="summarize text")],
    )
    triage = Agent(
        name="triage", instructions="route",
        model=ScriptedModel([{"output": [function_call("transfer_to_billing", {}, call_id="h1")], "usage": usage(30, 4)}], emit_traces=True),
        handoffs=[billing],
    )

    await Runner.run(triage, "my bill is wrong")
    provider.force_flush()
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(MessageToDict(encode_spans(exporter.get_finished_spans())), f, indent=1)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "trace.json"))
