"""Message tables (English / Korean) and language selection for the human-readable output.

All user-facing wording lives in :data:`MESSAGES`. Machine output (``--format json`` and
``--format mermaid``), edge kinds, warning codes and convention names are data and are
never translated.

The Python API defaults to English no matter what the environment says; only the CLI
passes the language it resolved with :func:`resolve_lang`.
"""

from __future__ import annotations

import os
from collections.abc import Mapping

LANGS = ("en", "ko")
DEFAULT_LANG = "en"
ENV_VAR = "HANDOFFMAP_LANG"

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        # --- CLI help ---
        "cli.description": "Fold an OTLP agent trace (OTel GenAI / OpenInference) into a Mermaid sequence diagram "
        "and a per-agent table. Reads OTLP JSON or JSONL; needs no server.",
        "cli.help.file": "OTLP JSON or JSONL trace file",
        "cli.help.sample": "use a built-in practice trace (made with mock models)",
        "cli.help.format": "output format (default: md)",
        "cli.help.explain": "show the detected convention and why each edge got its kind",
        "cli.help.trace": "only this trace (full id or unique prefix)",
        "cli.help.max_parallel": "wide-parallel warning above N concurrent activities (default 8)",
        "cli.help.repeat_threshold": "repeated-delegation warning at N identical delegations (default 3)",
        "cli.help.no_tools": "hide plain tool calls in the diagram",
        "cli.help.output": "write to a file instead of stdout",
        "cli.help.lang": "output language: en or ko (default: HANDOFFMAP_LANG, then LC_ALL/LC_MESSAGES/LANG, else en)",
        "cli.help.version": "show the version and exit",
        # --- CLI errors and notes ---
        "cli.err.not_whole": "{text!r} is not a whole number",
        "cli.err.min_one": "must be 1 or more",
        "cli.err.one_of": "give exactly one of FILE or --sample NAME",
        "cli.err.no_trace": "no trace id starts with {prefix!r} in the input",
        "cli.err.cannot_write": "cannot write {path}: {error}",
        "cli.sample_note": "_Sample trace: recorded from practice (mock) models, so token counts and timings are made up._",
        # --- parse / analyze errors ---
        "err.id_type": "not an OTLP trace: span/trace id must be a string, got {type}",
        "err.id_encoding": "not an OTLP trace: id {raw!r} is neither hex nor base64",
        "err.no_resource_spans": "not an OTLP trace: expected a JSON object with a 'resourceSpans' list",
        "err.span_no_ids": "not an OTLP trace: a span has no traceId/spanId",
        "err.invalid_json": "not an OTLP trace: invalid JSON ({msg}, line {line})",
        "err.empty": "not an OTLP trace: the input is empty",
        "err.no_spans": "not an OTLP trace: no spans found",
        "err.file_not_found": "file not found: {path}",
        "err.cannot_read": "cannot read {path}: {error}",
        "err.no_agent_spans": "no agent spans found in trace {trace_id} ({count} spans). "
        "Expected spans with gen_ai.operation.name=invoke_agent (OTel GenAI) or "
        "openinference.span.kind=AGENT with an agent.name (OpenInference).",
        # --- warnings (human-readable output only; JSON keeps the English text) ---
        "warn.repeated-delegation": "{caller} -> {callee} happened {count} times (threshold {threshold}); "
        "check for a loop or a missing stop condition",
        "warn.wide-parallel": "{agent} ran {count} activities at once (limit {limit})",
        # --- markdown report ---
        "md.heading": "## Agent flow: trace {trace} ({convention}, {spans} spans)",
        "md.agents": "### Agents",
        "md.footnote": "_Tokens are summed from LLM spans only. `time` is the wall time of each run, "
        "including work it delegated. `–` means the trace does not contain the value._",
        "md.warnings": "### Warnings",
        # --- table ---
        "table.agent": "agent",
        "table.runs": "runs",
        "table.llm_calls": "LLM calls",
        "table.tools": "tools",
        "table.input_tokens": "input tokens",
        "table.output_tokens": "output tokens",
        "table.cost": "cost",
        "table.time": "time",
        "table.total": "total",
        # --- --explain ---
        "why.root": "no agent above it and no handoff source: it started the run",
        "why.call": "agent span nested inside the caller, no tool span in between",
        "why.as_tool": "a tool span sits between the caller and this agent (agent used as a tool)",
        "why.handoff": "no agent ancestor; the span is a sibling and names its predecessor (graph.node.parent_id)",
        "ex.none": "(none)",
        "ex.via": " via {via}",
        "ex.trace": "trace: {trace}",
        "ex.convention": "convention: {convention}",
        "ex.size": "size: {spans} spans, {runs} agent runs, {agents} agents",
        "ex.agents": "agents: {names}",
        "ex.edges": "edges:",
        "ex.ignored": "ignored wrappers (AGENT span without agent.name, not counted as agents): {shown}",
        "ex.ignored_none": "ignored wrappers: none",
        "ex.unknown_ops": "unknown gen_ai.operation.name values (passed through): {names}",
        "ex.tokens_none": "tokens: none of the LLM spans carry token counts",
        "ex.tokens": "tokens: {input} in / {output} out (summed from LLM spans only)",
        "ex.reported": "agent spans report {input} in / {output} out (cross-check only, never added to the totals)",
        # --- argparse built-ins ---
        "argparse.usage": "usage: ",
        "argparse.options": "options",
        "argparse.positional": "positional arguments",
        "argparse.help": "show this help message and exit",
        "argparse.error_fmt": "%(prog)s: error: %(message)s\n",
        "argparse.argument_fmt": "argument %(argument_name)s: %(message)s",
        "argparse.invalid_choice": "invalid choice: %(value)r (choose from %(choices)s)",
        "argparse.invalid_choice_hint": "invalid choice: %(value)r, maybe you meant %(closest)r? "
        "(choose from %(choices)s)",
        "argparse.invalid_value": "invalid %(type)s value: %(value)r",
        "argparse.expected_one": "expected one argument",
        "argparse.unrecognized": "unrecognized arguments: %s",
        "argparse.required": "the following arguments are required: %s",
        "argparse.default": " (default: %(default)s)",
        "argparse.unexpected_option": "unexpected option string: %s",
        "argparse.ambiguous": "ambiguous option: %(option)s could match %(matches)s",
        "argparse.not_allowed": "not allowed with argument %s",
    },
    "ko": {
        "cli.description": "OTLP 에이전트 트레이스(OTel GenAI / OpenInference)를 Mermaid 시퀀스 다이어그램과 "
        "에이전트별 표로 정리합니다. OTLP JSON 또는 JSONL 을 읽으며 서버가 필요 없습니다.",
        "cli.help.file": "OTLP JSON 또는 JSONL 트레이스 파일",
        "cli.help.sample": "내장 연습용 트레이스를 사용합니다(목 모델로 만든 것)",
        "cli.help.format": "출력 형식(기본값: md)",
        "cli.help.explain": "감지한 규약과 각 엣지의 종류가 정해진 이유를 보여 줍니다",
        "cli.help.trace": "이 트레이스만 처리합니다(전체 ID 또는 고유한 앞부분)",
        "cli.help.max_parallel": "동시 활동이 N개를 넘으면 넓은 병렬 경고를 냅니다(기본값 8)",
        "cli.help.repeat_threshold": "같은 위임이 N번 반복되면 반복 위임 경고를 냅니다(기본값 3)",
        "cli.help.no_tools": "다이어그램에서 일반 도구 호출을 숨깁니다",
        "cli.help.output": "표준 출력 대신 파일에 씁니다",
        "cli.help.lang": "출력 언어: en 또는 ko (기본값: HANDOFFMAP_LANG, 그다음 LC_ALL/LC_MESSAGES/LANG, 없으면 en)",
        "cli.help.version": "버전을 표시하고 종료합니다",
        "cli.err.not_whole": "{text!r} 는 정수가 아닙니다",
        "cli.err.min_one": "1 이상이어야 합니다",
        "cli.err.one_of": "FILE 과 --sample NAME 중 정확히 하나만 지정하십시오",
        "cli.err.no_trace": "입력에 {prefix!r} 로 시작하는 트레이스 ID 가 없습니다",
        "cli.err.cannot_write": "{path} 에 쓸 수 없습니다: {error}",
        "cli.sample_note": "_샘플 트레이스: 연습용(목) 모델로 기록한 것이므로 토큰 수와 시간은 임의의 값입니다._",
        "err.id_type": "OTLP 트레이스가 아닙니다: span/trace ID 는 문자열이어야 하는데 {type} 입니다",
        "err.id_encoding": "OTLP 트레이스가 아닙니다: ID {raw!r} 가 16진수도 base64 도 아닙니다",
        "err.no_resource_spans": "OTLP 트레이스가 아닙니다: 'resourceSpans' 목록을 가진 JSON 객체가 필요합니다",
        "err.span_no_ids": "OTLP 트레이스가 아닙니다: traceId/spanId 가 없는 스팬이 있습니다",
        "err.invalid_json": "OTLP 트레이스가 아닙니다: JSON 이 올바르지 않습니다({msg}, {line}번째 줄)",
        "err.empty": "OTLP 트레이스가 아닙니다: 입력이 비어 있습니다",
        "err.no_spans": "OTLP 트레이스가 아닙니다: 스팬을 찾지 못했습니다",
        "err.file_not_found": "파일을 찾을 수 없습니다: {path}",
        "err.cannot_read": "{path} 을(를) 읽을 수 없습니다: {error}",
        "err.no_agent_spans": "트레이스 {trace_id} 에서 에이전트 스팬을 찾지 못했습니다(스팬 {count}개). "
        "gen_ai.operation.name=invoke_agent (OTel GenAI) 또는 "
        "agent.name 이 있는 openinference.span.kind=AGENT (OpenInference) 스팬이 필요합니다.",
        "warn.repeated-delegation": "{caller} -> {callee} 가 {count}번 발생했습니다(기준 {threshold}번). "
        "반복 루프이거나 종료 조건이 빠져 있지 않은지 확인하십시오",
        "warn.wide-parallel": "{agent} 가 {count}개의 활동을 동시에 실행했습니다(상한 {limit})",
        "md.heading": "## 에이전트 흐름: 트레이스 {trace} ({convention}, 스팬 {spans}개)",
        "md.agents": "### 에이전트",
        "md.footnote": "_토큰은 LLM 스팬에서만 합산합니다. `시간` 은 각 실행의 벽시계 시간이며 "
        "위임한 작업을 포함합니다. `–` 는 트레이스에 해당 값이 없다는 뜻입니다._",
        "md.warnings": "### 경고",
        "table.agent": "에이전트",
        "table.runs": "실행",
        "table.llm_calls": "LLM 호출",
        "table.tools": "도구",
        "table.input_tokens": "입력 토큰",
        "table.output_tokens": "출력 토큰",
        "table.cost": "비용",
        "table.time": "시간",
        "table.total": "합계",
        "why.root": "위에 에이전트가 없고 핸드오프 출처도 없습니다. 실행을 시작한 에이전트입니다",
        "why.call": "호출자 안에 중첩된 에이전트 스팬이며 사이에 도구 스팬이 없습니다",
        "why.as_tool": "호출자와 이 에이전트 사이에 도구 스팬이 있습니다(에이전트를 도구로 사용)",
        "why.handoff": "상위 에이전트가 없고, 스팬이 형제 관계이며 이전 에이전트를 명시합니다(graph.node.parent_id)",
        "ex.none": "(없음)",
        "ex.via": " 경유 {via}",
        "ex.trace": "트레이스: {trace}",
        "ex.convention": "규약: {convention}",
        "ex.size": "규모: 스팬 {spans}개, 에이전트 실행 {runs}회, 에이전트 {agents}개",
        "ex.agents": "에이전트: {names}",
        "ex.edges": "엣지:",
        "ex.ignored": "무시한 래퍼(agent.name 이 없는 AGENT 스팬, 에이전트로 세지 않음): {shown}",
        "ex.ignored_none": "무시한 래퍼: 없음",
        "ex.unknown_ops": "알 수 없는 gen_ai.operation.name 값(그대로 통과): {names}",
        "ex.tokens_none": "토큰: 토큰 수를 가진 LLM 스팬이 없습니다",
        "ex.tokens": "토큰: 입력 {input} / 출력 {output} (LLM 스팬에서만 합산)",
        "ex.reported": "에이전트 스팬 보고값: 입력 {input} / 출력 {output} (교차 확인용이며 합계에는 더하지 않음)",
        "argparse.usage": "사용법: ",
        "argparse.options": "옵션",
        "argparse.positional": "위치 인자",
        "argparse.help": "도움말을 표시하고 종료합니다",
        "argparse.error_fmt": "%(prog)s: 오류: %(message)s\n",
        "argparse.argument_fmt": "인자 %(argument_name)s: %(message)s",
        "argparse.invalid_choice": "잘못된 선택입니다: %(value)r (선택 가능: %(choices)s)",
        "argparse.invalid_choice_hint": "잘못된 선택입니다: %(value)r, %(closest)r 를 의도하셨습니까? "
        "(선택 가능: %(choices)s)",
        "argparse.invalid_value": "%(type)s 값이 올바르지 않습니다: %(value)r",
        "argparse.expected_one": "인자가 하나 필요합니다",
        "argparse.unrecognized": "인식할 수 없는 인자입니다: %s",
        "argparse.required": "다음 인자가 필요합니다: %s",
        "argparse.default": " (기본값: %(default)s)",
        "argparse.unexpected_option": "예상하지 못한 옵션 문자열입니다: %s",
        "argparse.ambiguous": "모호한 옵션입니다: %(option)s 는 %(matches)s 와 일치할 수 있습니다",
        "argparse.not_allowed": "다음 인자와 함께 쓸 수 없습니다: %s",
    },
}

# argparse's own English msgid -> our table key (see ``argparse_translator``)
_ARGPARSE_IDS = {
    "usage: ": "argparse.usage",
    "options": "argparse.options",
    "positional arguments": "argparse.positional",
    "show this help message and exit": "argparse.help",
    "%(prog)s: error: %(message)s\n": "argparse.error_fmt",
    "argument %(argument_name)s: %(message)s": "argparse.argument_fmt",
    "invalid choice: %(value)r (choose from %(choices)s)": "argparse.invalid_choice",
    "invalid choice: %(value)r, maybe you meant %(closest)r? (choose from %(choices)s)": "argparse.invalid_choice_hint",
    "invalid %(type)s value: %(value)r": "argparse.invalid_value",
    "expected one argument": "argparse.expected_one",
    "unrecognized arguments: %s": "argparse.unrecognized",
    "the following arguments are required: %s": "argparse.required",
    " (default: %(default)s)": "argparse.default",
    "unexpected option string: %s": "argparse.unexpected_option",
    "ambiguous option: %(option)s could match %(matches)s": "argparse.ambiguous",
    "not allowed with argument %s": "argparse.not_allowed",
}


def t(lang: str, key: str, **params: object) -> str:
    """Return the message ``key`` in ``lang`` (unknown languages fall back to English)."""
    table = MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])
    text = table.get(key) or MESSAGES[DEFAULT_LANG][key]
    return text.format(**params) if params else text


def lang_from_locale(value: str | None) -> str | None:
    """Map a locale string such as ``ko_KR.UTF-8`` to ``ko``; empty means "not set"."""
    if not value:
        return None
    return "ko" if value.strip().lower().startswith("ko") else DEFAULT_LANG


def resolve_lang(cli_value: str | None = None, env: Mapping[str, str] | None = None) -> str:
    """Pick the output language: ``--lang`` > ``HANDOFFMAP_LANG`` > ``LC_ALL`` > ``LC_MESSAGES`` > ``LANG``.

    Anything that is not Korean resolves to English. An unknown ``--lang`` value is ignored
    here (argparse rejects it separately), so the error message can still be localized.
    """
    environ = os.environ if env is None else env
    if cli_value in LANGS:
        return str(cli_value)
    explicit = environ.get(ENV_VAR, "").strip().lower()
    if explicit in LANGS:
        return explicit
    for name in ("LC_ALL", "LC_MESSAGES", "LANG"):
        found = lang_from_locale(environ.get(name))
        if found:
            return found
    return DEFAULT_LANG


def argparse_translator(lang: str):
    """Return a gettext-like function that renders argparse's built-in messages in ``lang``."""

    def translate(msgid: str) -> str:
        key = _ARGPARSE_IDS.get(msgid)
        if key is None:
            return msgid
        return MESSAGES.get(lang, MESSAGES[DEFAULT_LANG])[key]

    return translate
