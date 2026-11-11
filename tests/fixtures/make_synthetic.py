"""Write the two hand-made (not recorded) fixtures. Run once; the output is committed.

    python tests/fixtures/make_synthetic.py

* synthetic_genai_call.otlp.json - spec-style hex ids, a nested ``invoke_agent`` with no tool
  in between (``call``), an agent whose parent span was never exported (broken chain), and
  names with spaces, hyphens, parentheses, ``;`` and ``#``.
* synthetic_loop.otlp.json - planner delegates to coder three times (loop smell).
"""

import json
from pathlib import Path

HERE = Path(__file__).parent
MS = 1_000_000
T0 = 1_800_000_000_000_000_000


def attr(key, value):
    if isinstance(value, int):
        return {"key": key, "value": {"intValue": str(value)}}
    return {"key": key, "value": {"stringValue": value}}


def span(trace, sid, parent, name, start_ms, end_ms, attrs, kind=1):
    s = {
        "traceId": trace,
        "spanId": sid,
        "name": name,
        "kind": kind,
        "startTimeUnixNano": str(T0 + start_ms * MS),
        "endTimeUnixNano": str(T0 + end_ms * MS),
        "attributes": [attr(k, v) for k, v in attrs.items()],
    }
    if parent:
        s["parentSpanId"] = parent
    return s


def agent(trace, sid, parent, name, start, end):
    return span(trace, sid, parent, f"invoke_agent {name}", start, end,
                {"gen_ai.operation.name": "invoke_agent", "gen_ai.agent.name": name})


def tool(trace, sid, parent, name, start, end):
    return span(trace, sid, parent, f"execute_tool {name}", start, end,
                {"gen_ai.operation.name": "execute_tool", "gen_ai.tool.name": name})


def llm(trace, sid, parent, start, end, tokens_in, tokens_out):
    return span(trace, sid, parent, "chat demo-model", start, end,
                {"gen_ai.operation.name": "chat", "gen_ai.usage.input_tokens": tokens_in, "gen_ai.usage.output_tokens": tokens_out},
                kind=3)


def request(spans):
    return {"resourceSpans": [{"resource": {"attributes": [attr("service.name", "synthetic")]},
                               "scopeSpans": [{"scope": {"name": "handmade"}, "spans": spans}]}]}


def genai_call():
    t = "a1" * 16
    spans = [
        agent(t, "0000000000000001", None, "billing-agent (v2)", 0, 100),
        llm(t, "0000000000000002", "0000000000000001", 1, 10, 10, 2),
        tool(t, "0000000000000003", "0000000000000001", "lookup; ticket #5", 12, 30),
        # nested agent, no tool in between -> call
        agent(t, "0000000000000004", "0000000000000001", "refund helper", 35, 60),
        llm(t, "0000000000000005", "0000000000000004", 36, 50, 20, 4),
        # parent 00000000000000ff was never exported: the chain is broken, time containment finds billing-agent
        agent(t, "0000000000000006", "00000000000000ff", "audit<log>", 65, 90),
        llm(t, "0000000000000007", "0000000000000006", 66, 80, 5, 1),
    ]
    return request(spans)


def loop():
    t = "b2" * 16
    spans = [agent(t, "0000000000000001", None, "planner", 0, 200)]
    for i in range(3):
        base = 10 + i * 60
        wrap, run, call = 0x10 + i * 4, 0x11 + i * 4, 0x12 + i * 4
        spans.append(tool(t, f"{wrap:016x}", "0000000000000001", "delegate_to_coder", base, base + 50))
        spans.append(agent(t, f"{run:016x}", f"{wrap:016x}", "coder", base + 1, base + 49))
        spans.append(llm(t, f"{call:016x}", f"{run:016x}", base + 2, base + 20, 30, 10))
    return request(spans)


def main():
    (HERE / "synthetic_genai_call.otlp.json").write_text(json.dumps(genai_call(), indent=1) + "\n")
    (HERE / "synthetic_loop.otlp.json").write_text(json.dumps(loop(), indent=1) + "\n")


if __name__ == "__main__":
    main()
