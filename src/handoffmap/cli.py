"""Command line interface.

Exit codes: 0 ok, 1 no agent spans in the trace, 2 bad input (not OTLP, missing file, bad option).
"""

from __future__ import annotations

import argparse
import json
import sys
from importlib import resources
from pathlib import Path

from . import __version__
from .errors import HandoffmapError, NoAgentSpansError, NotOtlpError
from .model import Flow, Trace
from .normalize import analyze
from .otlp import load, parse
from .render.explain import render_explain
from .render.jsonout import to_dict
from .render.markdown import render_markdown
from .render.mermaid import render_mermaid
from .render.table import render_table

SAMPLES = {
    "pydantic-ai": "pydantic_ai_v5.otlp.json",
    "pydantic-ai-v2": "pydantic_ai_v2.otlp.json",
    "pydantic-ai-v6": "pydantic_ai_v6.otlp.json",
    "openinference": "openinference_agents.otlp.json",
}
FORMATS = ("md", "mermaid", "table", "json")


def _positive(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{text!r} is not a whole number") from None
    if value < 1:
        raise argparse.ArgumentTypeError("must be 1 or more")
    return value


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="handoffmap",
        description="Fold an OTLP agent trace (OTel GenAI / OpenInference) into a Mermaid sequence diagram "
        "and a per-agent table. Reads OTLP JSON or JSONL; needs no server.",
    )
    p.add_argument("file", nargs="?", help="OTLP JSON or JSONL trace file")
    p.add_argument("--sample", choices=sorted(SAMPLES), help="use a built-in practice trace (made with mock models)")
    p.add_argument("--format", "-f", choices=FORMATS, default="md", help="output format (default: md)")
    p.add_argument("--explain", action="store_true", help="show the detected convention and why each edge got its kind")
    p.add_argument("--trace", metavar="TRACE_ID", help="only this trace (full id or unique prefix)")
    p.add_argument("--max-parallel", type=_positive, default=8, metavar="N", help="wide-parallel warning above N concurrent activities (default 8)")
    p.add_argument("--repeat-threshold", type=_positive, default=3, metavar="N", help="repeated-delegation warning at N identical delegations (default 3)")
    p.add_argument("--no-tools", action="store_true", help="hide plain tool calls in the diagram")
    p.add_argument("-o", "--output", metavar="OUT", help="write to a file instead of stdout")
    p.add_argument("--version", action="version", version=f"handoffmap {__version__}")
    return p


def _load_traces(args: argparse.Namespace) -> list[Trace]:
    if args.sample:
        text = resources.files("handoffmap").joinpath("samples", SAMPLES[args.sample]).read_text(encoding="utf-8")
        traces = parse(text)
    else:
        traces = load(args.file)
    if args.trace:
        traces = [t for t in traces if t.trace_id.startswith(args.trace.lower())]
        if not traces:
            raise NotOtlpError(f"no trace id starts with {args.trace!r} in the input")
    return traces


def _analyze_all(traces: list[Trace], args: argparse.Namespace) -> list[Flow]:
    flows: list[Flow] = []
    last_error: NoAgentSpansError | None = None
    for trace in traces:
        try:
            flows.append(analyze(trace, repeat_threshold=args.repeat_threshold, max_parallel=args.max_parallel))
        except NoAgentSpansError as exc:
            last_error = exc  # other traces in the file may still have agents
    if not flows:
        assert last_error is not None
        raise last_error
    return flows


def _render(flows: list[Flow], args: argparse.Namespace) -> tuple[str, str]:
    """Return (report, explain) text."""
    show_tools = not args.no_tools
    explain = "".join(render_explain(f) + ("\n" if len(flows) > 1 else "") for f in flows) if args.explain else ""
    if args.format == "json":
        payload = [to_dict(f) for f in flows]
        report = json.dumps(payload[0] if len(payload) == 1 else {"traces": payload}, indent=2, ensure_ascii=False) + "\n"
    elif args.format == "mermaid":
        report = "\n".join(render_mermaid(f, show_tools=show_tools) for f in flows)
    elif args.format == "table":
        report = "\n".join(render_table(f) for f in flows)
    else:
        report = "\n".join(render_markdown(f, show_tools=show_tools, heading=True) for f in flows)
    if args.sample and args.format == "md":
        report += "\n_Sample trace: recorded from practice (mock) models, so token counts and timings are made up._\n"
    return report, explain


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")  # the table uses an en dash; C locales would choke
    parser = build_parser()
    args = parser.parse_args(argv)
    if bool(args.file) == bool(args.sample):
        parser.error("give exactly one of FILE or --sample NAME")

    try:
        flows = _analyze_all(_load_traces(args), args)
        report, explain = _render(flows, args)
    except HandoffmapError as exc:
        print(f"handoffmap: {exc}", file=sys.stderr)
        return exc.exit_code

    # explain goes before the report for md/table; to stderr for mermaid/json so stdout stays machine-readable
    if explain and args.format in ("mermaid", "json"):
        print(explain, file=sys.stderr, end="")
        explain = ""
    text = (explain + "\n" if explain else "") + report
    if args.output:
        try:
            Path(args.output).write_text(text, encoding="utf-8")
        except OSError as exc:
            print(f"handoffmap: cannot write {args.output}: {exc}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(text)
    return 0
