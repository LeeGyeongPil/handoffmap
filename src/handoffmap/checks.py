"""Flow warnings: things that usually mean a loop or a runaway fan-out."""

from __future__ import annotations

from collections import Counter

from .model import Edge, FlowWarning, ParallelGroup


def find_warnings(
    edges: list[Edge],
    parallel: list[ParallelGroup],
    repeat_threshold: int = 3,
    max_parallel: int = 8,
) -> list[FlowWarning]:
    """Return ``repeated-delegation`` and ``wide-parallel`` warnings."""
    warnings: list[FlowWarning] = []

    pairs = Counter((e.caller, e.callee) for e in edges if e.kind != "root")
    for (caller, callee), count in pairs.items():
        if count >= repeat_threshold:
            warnings.append(
                FlowWarning(
                    "repeated-delegation",
                    f"{caller} -> {callee} happened {count} times (threshold {repeat_threshold}); "
                    "check for a loop or a missing stop condition",
                )
            )

    for group in parallel:
        if len(group.members) > max_parallel:
            warnings.append(
                FlowWarning(
                    "wide-parallel",
                    f"{group.agent} ran {len(group.members)} activities at once (limit {max_parallel})",
                )
            )
    return warnings
