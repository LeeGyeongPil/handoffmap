# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "pydantic-ai-slim==2.67.0",
#   "opentelemetry-sdk==1.45.2",
#   "opentelemetry-exporter-otlp-proto-common==1.45.2",
# ]
# ///
"""Make a multi-agent trace with Pydantic AI and a mock model (no network, no API key).

    uv run examples/make_pydantic_trace.py trace.json
    handoffmap trace.json

An orchestrator calls two sub-agents as tools, in parallel. The output is a
protobuf-JSON OTLP file (base64 ids), which handoffmap reads.
"""

import asyncio
import json
import sys

from google.protobuf.json_format import MessageToDict
from opentelemetry.exporter.otlp.proto.common.trace_encoder import encode_spans
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic_ai import Agent, RunContext
from pydantic_ai.messages import ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from pydantic_ai.models.instrumented import InstrumentationSettings


# Mock models: the replies are scripted, so the run is deterministic and free.
def orchestrator_fn(messages, info: AgentInfo):
    if len(messages) == 1:  # first turn: ask both sub-agents at once
        return ModelResponse(parts=[ToolCallPart("ask_researcher", {"q": "otel"}), ToolCallPart("ask_writer", {"q": "draft"})])
    return ModelResponse(parts=[TextPart("done")])


def researcher_fn(messages, info: AgentInfo):
    if len(messages) == 1:
        return ModelResponse(parts=[ToolCallPart("search", {"term": "genai"})])
    return ModelResponse(parts=[TextPart("found")])


def writer_fn(messages, info: AgentInfo):
    return ModelResponse(parts=[TextPart("written")])


async def main(out_path: str) -> None:
    exporter = InMemorySpanExporter()
    provider = TracerProvider(resource=Resource.create({"service.name": "handoffmap-example"}))
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    # version=5 is the instrumentation format handoffmap's built-in sample uses
    Agent.instrument_all(InstrumentationSettings(tracer_provider=provider, version=5))

    researcher = Agent(FunctionModel(researcher_fn, model_name="mock-small"), name="researcher")
    writer = Agent(FunctionModel(writer_fn, model_name="mock-small"), name="writer")
    orchestrator = Agent(FunctionModel(orchestrator_fn, model_name="mock-large"), name="orchestrator")

    @researcher.tool_plain
    async def search(term: str) -> str:
        await asyncio.sleep(0.05)
        return f"result for {term}"

    @orchestrator.tool
    async def ask_researcher(ctx: RunContext, q: str) -> str:
        return (await researcher.run(q, usage=ctx.usage)).output

    @orchestrator.tool
    async def ask_writer(ctx: RunContext, q: str) -> str:
        await asyncio.sleep(0.02)
        return (await writer.run(q, usage=ctx.usage)).output

    await orchestrator.run("plan it")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(MessageToDict(encode_spans(exporter.get_finished_spans())), f, indent=1)
    print(f"wrote {out_path}")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "trace.json"))
