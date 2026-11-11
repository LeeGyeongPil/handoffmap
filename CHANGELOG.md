# Changelog

All notable changes to this project are documented here.
The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

## [0.1.0] - 2026-11-11

### Added
- OTLP JSON and JSONL loader (hex or base64 ids, integer or `SPAN_KIND_*` kinds), split by trace id.
- Adapters for OTel GenAI (`gen_ai.operation.name`) and OpenInference (`openinference.span.kind`).
- Agent-level normalization: `root`, `call`, `as_tool` and `handoff` edges, per-run instances, parallel groups from time overlap.
- Per-agent LLM calls, tool calls, tokens (summed at LLM spans only), cost (`llm.cost.total`) and time.
- Output formats `md`, `mermaid`, `table`, `json`; `--explain`; `--trace`; `--no-tools`; `-o`.
- Warnings `repeated-delegation` and `wide-parallel`.
- Built-in practice samples recorded with mock models, and `examples/` scripts to make your own.
- Python API: `load`, `parse`, `analyze`, `render_mermaid`, `render_table`, `render_markdown`, `to_dict`.
