"""Command line interface.

Exit codes: 0 ok, 1 no agent spans in the trace, 2 bad input (not OTLP, missing file, bad option).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from importlib import resources
from pathlib import Path

from . import __version__
from .errors import HandoffmapError, NoAgentSpansError, NotOtlpError
from .i18n import LANGS, argparse_translator, resolve_lang, t
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


def _positive_for(lang: str):
    """Return an argparse ``type=`` function whose error messages are in ``lang``."""

    def _positive(text: str) -> int:
        try:
            value = int(text)
        except ValueError:
            raise argparse.ArgumentTypeError(t(lang, "cli.err.not_whole", text=text)) from None
        if value < 1:
            raise argparse.ArgumentTypeError(t(lang, "cli.err.min_one"))
        return value

    return _positive


def _peek_lang(argv: list[str]) -> str:
    """Read only ``--lang`` from argv first, so help and parse errors can already be localized."""
    peek = argparse.ArgumentParser(add_help=False, allow_abbrev=False)
    peek.add_argument("--lang")
    known, _rest = peek.parse_known_args(argv)
    return resolve_lang(known.lang)


@contextmanager
def _argparse_in(lang: str) -> Iterator[None]:
    """Render argparse's built-in messages (usage, choices errors, ...) in ``lang`` while parsing."""
    original = argparse._  # type: ignore[attr-defined]
    argparse._ = argparse_translator(lang)  # type: ignore[attr-defined]
    try:
        yield
    finally:
        argparse._ = original  # type: ignore[attr-defined]


def build_parser(lang: str = "en") -> argparse.ArgumentParser:
    """Build the argument parser with help text in ``lang`` (``en`` or ``ko``)."""
    positive = _positive_for(lang)
    p = argparse.ArgumentParser(prog="handoffmap", description=t(lang, "cli.description"), add_help=False)
    p.add_argument("-h", "--help", action="help", help=t(lang, "argparse.help"))
    p.add_argument("file", nargs="?", help=t(lang, "cli.help.file"))
    p.add_argument("--sample", choices=sorted(SAMPLES), help=t(lang, "cli.help.sample"))
    p.add_argument("--format", "-f", choices=FORMATS, default="md", help=t(lang, "cli.help.format"))
    p.add_argument("--explain", action="store_true", help=t(lang, "cli.help.explain"))
    p.add_argument("--trace", metavar="TRACE_ID", help=t(lang, "cli.help.trace"))
    p.add_argument("--max-parallel", type=positive, default=8, metavar="N", help=t(lang, "cli.help.max_parallel"))
    p.add_argument("--repeat-threshold", type=positive, default=3, metavar="N", help=t(lang, "cli.help.repeat_threshold"))
    p.add_argument("--no-tools", action="store_true", help=t(lang, "cli.help.no_tools"))
    p.add_argument("-o", "--output", metavar="OUT", help=t(lang, "cli.help.output"))
    p.add_argument("--lang", choices=LANGS, metavar="{en,ko}", help=t(lang, "cli.help.lang"))
    p.add_argument("--version", action="version", version=f"handoffmap {__version__}", help=t(lang, "cli.help.version"))
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
            raise NotOtlpError("cli.err.no_trace", prefix=args.trace)
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


def _render(flows: list[Flow], args: argparse.Namespace, lang: str) -> tuple[str, str]:
    """Return (report, explain) text. ``json`` and ``mermaid`` ignore ``lang`` (machine output)."""
    show_tools = not args.no_tools
    explain = (
        "".join(render_explain(f, lang) + ("\n" if len(flows) > 1 else "") for f in flows) if args.explain else ""
    )
    if args.format == "json":
        payload = [to_dict(f) for f in flows]
        report = json.dumps(payload[0] if len(payload) == 1 else {"traces": payload}, indent=2, ensure_ascii=False) + "\n"
    elif args.format == "mermaid":
        report = "\n".join(render_mermaid(f, show_tools=show_tools) for f in flows)
    elif args.format == "table":
        report = "\n".join(render_table(f, lang=lang) for f in flows)
    else:
        report = "\n".join(render_markdown(f, show_tools=show_tools, heading=True, lang=lang) for f in flows)
    if args.sample and args.format == "md":
        report += "\n" + t(lang, "cli.sample_note") + "\n"
    return report, explain


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")  # the table uses an en dash; C locales would choke
    raw_args = sys.argv[1:] if argv is None else list(argv)
    lang = _peek_lang(raw_args)  # --lang > HANDOFFMAP_LANG > LC_ALL/LC_MESSAGES/LANG > en
    with _argparse_in(lang):  # the parser must be built inside: argparse looks up some titles at construction
        parser = build_parser(lang)
        args = parser.parse_args(raw_args)
        if bool(args.file) == bool(args.sample):
            parser.error(t(lang, "cli.err.one_of"))

    try:
        flows = _analyze_all(_load_traces(args), args)
        report, explain = _render(flows, args, lang)
    except HandoffmapError as exc:
        print(f"handoffmap: {exc.localized(lang)}", file=sys.stderr)
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
            print(f"handoffmap: {t(lang, 'cli.err.cannot_write', path=args.output, error=exc)}", file=sys.stderr)
            return 2
    else:
        sys.stdout.write(text)
    return 0
