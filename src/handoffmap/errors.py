"""Exceptions raised by handoffmap. The CLI maps them to exit codes."""

from __future__ import annotations


class HandoffmapError(Exception):
    """Base class for all handoffmap errors."""

    exit_code = 2


class NotOtlpError(HandoffmapError):
    """The input is not an OTLP trace export (exit code 2)."""

    exit_code = 2


class NoAgentSpansError(HandoffmapError):
    """The trace has no agent spans, so there is no flow to draw (exit code 1)."""

    exit_code = 1
