"""Shared helpers: fixture paths and small loaders.

Importing this module pins the output language to English (before handoffmap is used), so the
English-wording assertions pass under any locale, with pytest or unittest alike.
"""

from __future__ import annotations

import os

os.environ["HANDOFFMAP_LANG"] = "en"  # must stay above the handoffmap imports

from pathlib import Path  # noqa: E402

import handoffmap  # noqa: E402
from handoffmap.cli import SAMPLES  # noqa: E402

FIXTURES = Path(__file__).parent / "fixtures"
SAMPLES_DIR = Path(handoffmap.__file__).parent / "samples"


def sample_path(name: str) -> Path:
    return SAMPLES_DIR / SAMPLES[name]


def flow_of(path: Path, **kwargs):
    traces = handoffmap.load(path)
    assert len(traces) == 1
    return handoffmap.analyze(traces[0], **kwargs)


def edge_keys(flow):
    return [e.key() for e in flow.edges]
