"""Use handoffmap from Python: load a trace file, analyze it, print edges and the table.

    uv run python examples/api_demo.py
"""

import handoffmap

trace = handoffmap.load("src/handoffmap/samples/pydantic_ai_v5.otlp.json")[0]
flow = handoffmap.analyze(trace)
for e in flow.edges:
    print(e.caller, "->", e.callee, e.kind, e.via)
print(handoffmap.render_table(flow))
