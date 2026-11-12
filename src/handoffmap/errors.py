"""Exceptions raised by handoffmap. The CLI maps them to exit codes."""

from __future__ import annotations

from .i18n import MESSAGES, t


class HandoffmapError(Exception):
    """Base class for all handoffmap errors.

    Built from a message key of :mod:`handoffmap.i18n` plus its parameters. ``str(exc)`` is
    always English; the CLI calls :meth:`localized` to show the user's language.
    """

    exit_code = 2

    def __init__(self, key: str, **params: object) -> None:
        self.key = key
        self.params = params
        # a key that is not in the table is treated as a plain English message
        super().__init__(t("en", key, **params) if key in MESSAGES["en"] else key)

    def localized(self, lang: str) -> str:
        """Return the message in ``lang`` (``en`` or ``ko``)."""
        return t(lang, self.key, **self.params) if self.key in MESSAGES["en"] else str(self)


class NotOtlpError(HandoffmapError):
    """The input is not an OTLP trace export (exit code 2)."""

    exit_code = 2


class NoAgentSpansError(HandoffmapError):
    """The trace has no agent spans, so there is no flow to draw (exit code 1)."""

    exit_code = 1
