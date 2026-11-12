"""Language selection (en / ko): message tables, priority order, localized output, machine output unchanged."""

from __future__ import annotations

import re

import pytest

import handoffmap
from handoffmap import i18n
from handoffmap.cli import main
from helpers import FIXTURES, flow_of, sample_path

HANGUL = re.compile(r"[가-힣]")
# polite-formal endings (합니다체) that every Korean sentence in the tables must use; clauses ending a
# noun phrase or a label are allowed, but the polite-casual "요" ending is not.
HAE_YO = re.compile(r"[해세예어아이]요(?=[\s.,)\]]|$)")


def run(capsys, *argv):
    code = main(list(argv))
    captured = capsys.readouterr()
    return code, captured.out, captured.err


def test_message_tables_have_identical_keys():
    assert set(i18n.MESSAGES["en"]) == set(i18n.MESSAGES["ko"])


def test_placeholders_match_between_languages():
    field = re.compile(r"\{(\w+)[^}]*\}|%\((\w+)\)|%s")
    for key, en in i18n.MESSAGES["en"].items():
        ko = i18n.MESSAGES["ko"][key]
        assert sorted(map(str, field.findall(en))) == sorted(map(str, field.findall(ko))), key


def test_korean_messages_use_one_politeness_level():
    for key, text in i18n.MESSAGES["ko"].items():
        assert not HAE_YO.search(text), f"{key}: haeyo-style ending in {text!r}"


@pytest.mark.parametrize(
    ("cli", "env", "expected"),
    [
        ("ko", {"HANDOFFMAP_LANG": "en"}, "ko"),  # --lang beats everything
        ("en", {"HANDOFFMAP_LANG": "ko", "LANG": "ko_KR.UTF-8"}, "en"),
        (None, {"HANDOFFMAP_LANG": "ko", "LC_ALL": "en_US.UTF-8"}, "ko"),  # env var beats locale
        (None, {"LC_ALL": "ko_KR.UTF-8", "LC_MESSAGES": "en_US", "LANG": "en_US"}, "ko"),
        (None, {"LC_MESSAGES": "ko_KR.UTF-8", "LANG": "en_US.UTF-8"}, "ko"),
        (None, {"LANG": "ko_KR.UTF-8"}, "ko"),
        (None, {"LC_ALL": "en_US.UTF-8", "LANG": "ko_KR.UTF-8"}, "en"),  # LC_ALL outranks LANG
        (None, {"LANG": "fr_FR.UTF-8"}, "en"),
        (None, {"LC_ALL": "", "LANG": "ko_KR.UTF-8"}, "ko"),  # empty means not set
        (None, {}, "en"),
        ("xx", {"LANG": "ko_KR.UTF-8"}, "ko"),  # unknown --lang is ignored here; argparse rejects it
    ],
)
def test_resolve_lang_priority(cli, env, expected):
    assert i18n.resolve_lang(cli, env) == expected


def test_lang_option_switches_markdown(capsys):
    code, out, _ = run(capsys, "--sample", "pydantic-ai", "--lang", "ko")
    assert code == 0
    assert "## 에이전트 흐름: 트레이스" in out
    assert "| 에이전트 | 실행 | LLM 호출 | 도구 | 입력 토큰 | 출력 토큰 | 시간 |" in out
    assert "### 에이전트" in out
    assert "_토큰은 LLM 스팬에서만 합산합니다." in out
    assert "_샘플 트레이스" in out
    assert "## Agent flow" not in out


def test_english_is_unchanged_by_lang_en(capsys):
    _, default, _ = run(capsys, "--sample", "pydantic-ai")
    _, explicit, _ = run(capsys, "--sample", "pydantic-ai", "--lang", "en")
    assert default == explicit
    assert "## Agent flow: trace" in default and not HANGUL.search(default.split("```mermaid")[0])


def test_env_var_and_locale_choose_language(capsys, monkeypatch):
    monkeypatch.setenv("HANDOFFMAP_LANG", "ko")
    assert "### 에이전트" in run(capsys, "--sample", "pydantic-ai")[1]
    monkeypatch.setenv("HANDOFFMAP_LANG", "en")
    monkeypatch.setenv("LANG", "ko_KR.UTF-8")
    assert "### Agents" in run(capsys, "--sample", "pydantic-ai")[1]
    monkeypatch.delenv("HANDOFFMAP_LANG")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    assert "### 에이전트" in run(capsys, "--sample", "pydantic-ai")[1]
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    assert "### Agents" in run(capsys, "--sample", "pydantic-ai")[1]


def test_help_is_localized(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--help", "--lang", "ko"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    for needle in ("사용법: ", "위치 인자", "옵션", "도움말을 표시하고 종료합니다", "출력 언어", "서버가 필요 없습니다"):
        assert needle in out
    assert "show this help" not in out and "positional arguments" not in out


def test_help_english_by_default_and_fr_locale(capsys, monkeypatch):
    monkeypatch.setenv("HANDOFFMAP_LANG", "en")
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "show this help message and exit" in capsys.readouterr().out
    monkeypatch.delenv("HANDOFFMAP_LANG")
    monkeypatch.setenv("LANG", "fr_FR.UTF-8")
    monkeypatch.delenv("LC_ALL", raising=False)
    monkeypatch.delenv("LC_MESSAGES", raising=False)
    with pytest.raises(SystemExit):
        main(["--help"])
    assert "usage: " in capsys.readouterr().out


def test_argparse_errors_are_localized(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--sample", "nope", "--lang", "ko"])
    assert exc.value.code == 2
    err = capsys.readouterr().err
    assert "오류" in err and "잘못된 선택입니다" in err

    with pytest.raises(SystemExit):
        main(["--sample", "pydantic-ai", "--max-parallel", "0", "--lang", "ko"])
    assert "1 이상이어야 합니다" in capsys.readouterr().err

    with pytest.raises(SystemExit):
        main(["--sample", "pydantic-ai", "--max-parallel", "x", "--lang", "ko"])
    assert "정수가 아닙니다" in capsys.readouterr().err

    with pytest.raises(SystemExit):
        main(["--lang", "ko"])
    assert "정확히 하나만" in capsys.readouterr().err

    with pytest.raises(SystemExit):
        main(["--sample", "pydantic-ai", "--bogus", "--lang", "ko"])
    assert "인식할 수 없는 인자입니다" in capsys.readouterr().err


def test_bad_lang_value_is_rejected_in_english_or_env_language(capsys):
    with pytest.raises(SystemExit) as exc:
        main(["--sample", "pydantic-ai", "--lang", "fr"])
    assert exc.value.code == 2
    assert "invalid choice" in capsys.readouterr().err


def test_runtime_errors_are_localized_with_same_exit_codes(capsys, tmp_path):
    code, _, err = run(capsys, str(tmp_path / "missing.json"), "--lang", "ko")
    assert code == 2 and err.startswith("handoffmap: 파일을 찾을 수 없습니다")

    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    code, _, err = run(capsys, str(bad), "--lang", "ko")
    assert code == 2 and "OTLP 트레이스가 아닙니다" in err

    code, _, err = run(capsys, "--sample", "pydantic-ai", "--trace", "zzzz", "--lang", "ko")
    assert code == 2 and "로 시작하는 트레이스 ID" in err

    # a trace with no agent spans -> exit 1
    code, _, err = run(capsys, str(FIXTURES / "synthetic_genai_call.otlp.json"), "--lang", "ko")
    if code == 1:
        assert "에이전트 스팬을 찾지 못했습니다" in err

    code, _, err = run(capsys, "--sample", "pydantic-ai", "-o", str(tmp_path / "nodir" / "x.md"), "--lang", "ko")
    assert code == 2 and "에 쓸 수 없습니다" in err


def test_no_agent_spans_message_in_both_languages(capsys, tmp_path):
    # a valid OTLP span that is not an agent span
    span = (
        '{"resourceSpans":[{"scopeSpans":[{"spans":[{"traceId":"0123456789abcdef0123456789abcdef",'
        '"spanId":"0123456789abcdef","name":"x","startTimeUnixNano":"1","endTimeUnixNano":"2"}]}]}]}'
    )
    p = tmp_path / "noagent.json"
    p.write_text(span, encoding="utf-8")
    code, _, err = run(capsys, str(p), "--lang", "ko")
    assert code == 1 and "에이전트 스팬을 찾지 못했습니다" in err
    code, _, err = run(capsys, str(p), "--lang", "en")
    assert code == 1 and "no agent spans found" in err


def test_explain_and_table_in_korean(capsys):
    code, out, _ = run(capsys, "--sample", "pydantic-ai", "--explain", "--lang", "ko")
    assert code == 0
    for needle in ("트레이스: ", "규약: otel-genai", "엣지:", "[호출자와 이 에이전트 사이에 도구 스팬이"):
        assert needle in out
    assert "as_tool 경유 ask_researcher" in out

    code, out, _ = run(capsys, "--sample", "pydantic-ai", "--format", "table", "--lang", "ko")
    assert out.startswith("| 에이전트 |")


def test_warning_text_localized_in_md_but_not_in_json(capsys):
    path = FIXTURES / "synthetic_loop.otlp.json"
    code, ko, _ = run(capsys, str(path), "--lang", "ko")
    assert code == 0
    assert "### 경고" in ko and "번 발생했습니다" in ko and "**repeated-delegation**" in ko
    _, en, _ = run(capsys, str(path), "--lang", "en")
    assert "### Warnings" in en and "times (threshold" in en
    _, ko_json, _ = run(capsys, str(path), "--format", "json", "--lang", "ko")
    assert "times (threshold" in ko_json and "발생" not in ko_json


@pytest.mark.parametrize("fmt", ["json", "mermaid"])
@pytest.mark.parametrize("target", [("--sample", "pydantic-ai"), (str(FIXTURES / "synthetic_loop.otlp.json"),)])
def test_machine_formats_identical_across_languages(capsys, fmt, target):
    _, en, _ = run(capsys, *target, "--format", fmt, "--lang", "en")
    _, ko, _ = run(capsys, *target, "--format", fmt, "--lang", "ko")
    assert en == ko and en


def test_api_default_is_english_even_with_korean_env(monkeypatch):
    monkeypatch.setenv("HANDOFFMAP_LANG", "ko")
    monkeypatch.setenv("LANG", "ko_KR.UTF-8")
    flow = flow_of(sample_path("pydantic-ai"))
    assert "### Agents" in handoffmap.render_markdown(flow)
    assert handoffmap.render_table(flow).startswith("| agent |")
    assert "### 에이전트" in handoffmap.render_markdown(flow, lang="ko")


def test_exception_str_is_english_and_localizable():
    with pytest.raises(handoffmap.NotOtlpError) as exc:
        handoffmap.parse("")
    assert str(exc.value) == "not an OTLP trace: the input is empty"
    assert exc.value.localized("ko") == "OTLP 트레이스가 아닙니다: 입력이 비어 있습니다"


@pytest.mark.parametrize("fmt", ["md", "table"])
def test_korean_total_row_is_translated_english_keeps_total(capsys, fmt):
    ko = run(capsys, "--sample", "pydantic-ai", "--format", fmt, "--lang", "ko")[1]
    en = run(capsys, "--sample", "pydantic-ai", "--format", fmt, "--lang", "en")[1]
    assert "| **합계** |" in ko
    assert "**total**" not in ko
    assert "| **total** |" in en


def test_korean_prose_has_no_english_labels(capsys):
    # headers, total label and footnote words must not leak through in Korean (identifiers excluded)
    out = run(capsys, "--sample", "pydantic-ai", "--explain", "--lang", "ko")[1]
    prose = out.split("```mermaid")[0] + out.split("```")[-1]
    for label in ("total", "runs", "LLM calls", "tools", "input tokens", "output tokens", "agent |"):
        assert label not in prose, label


def test_render_explain_is_exported():
    assert handoffmap.render_explain is not None
    assert "render_explain" in handoffmap.__all__

