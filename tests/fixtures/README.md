# Test fixtures

| File | Origin |
|---|---|
| `../../src/handoffmap/samples/pydantic_ai_v{2,5,6}.otlp.json` | **Recorded** with Pydantic AI 2.67.0 (instrumentation versions 2, 5, 6) and a `FunctionModel` mock model. 11 spans each. Message text is mock text. |
| `../../src/handoffmap/samples/openinference_agents.otlp.json` | **Recorded** with openai-agents 0.24.0 `ScriptedModel` (mock) and openinference-instrumentation-openai-agents 2.7.1. 17 spans. |
| `pydantic_ai_v5.hex.otlp.json` | **Derived**: the v5 sample with hex ids and integer span kinds (`make_hex.py`). |
| `synthetic_genai_call.otlp.json` | **Hand-made, not recorded** (`make_synthetic.py`), following the OTel GenAI agent-span attribute tables. Covers `call`, a broken parent chain, and special characters in names. |
| `synthetic_loop.otlp.json` | **Hand-made, not recorded** (`make_synthetic.py`). planner delegates to coder three times. |

No fixture contains real prompts, keys, or local paths.
