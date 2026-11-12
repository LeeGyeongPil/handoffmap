"""Flow warnings: things that usually mean a loop or a runaway fan-out."""

from __future__ import annotations

from collections import Counter

from .i18n import t
from .model import Edge, FlowWarning, ParallelGroup


def find_warnings(
    edges: list[Edge],
    parallel: list[ParallelGroup],
    repeat_threshold: int = 3,
    max_parallel: int = 8,
) -> list[FlowWarning]:
    """Return ``repeated-delegation`` and ``wide-parallel`` warnings.

    ``message`` is English; ``args`` lets the renderers rebuild it in another language.
    """
    warnings: list[FlowWarning] = []

    pairs = Counter((e.caller, e.callee) for e in edges if e.kind != "root")
    for (caller, callee), count in pairs.items():
        if count >= repeat_threshold:
            args = {"caller": caller, "callee": callee, "count": count, "threshold": repeat_threshold}
            warnings.append(FlowWarning("repeated-delegation", t("en", "warn.repeated-delegation", **args), args))

    for group in parallel:
        if len(group.members) > max_parallel:
            args = {"agent": group.agent, "count": len(group.members), "limit": max_parallel}
            warnings.append(FlowWarning("wide-parallel", t("en", "warn.wide-parallel", **args), args))
    return warnings
