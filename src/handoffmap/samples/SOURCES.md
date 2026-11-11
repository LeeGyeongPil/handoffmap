# Built-in sample traces

All four were recorded on 2026-11-11 with **mock models** (no network, no API key), so token counts and timings are practice values.

| File | Made with |
|---|---|
| `pydantic_ai_v2.otlp.json`, `pydantic_ai_v5.otlp.json`, `pydantic_ai_v6.otlp.json` | pydantic-ai-slim 2.67.0, `FunctionModel`, instrumentation `version=2/5/6`; see `examples/make_pydantic_trace.py` |
| `openinference_agents.otlp.json` | openai-agents 0.24.0 `ScriptedModel`, openinference-instrumentation-openai-agents 2.7.1; see `examples/make_openai_agents_trace.py` |

They use the protobuf-JSON form (base64 ids, `SPAN_KIND_*` names). Prompt/response text in them is mock text; handoffmap never prints it.
