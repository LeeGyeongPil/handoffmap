"""Shared helpers: fixture paths and small loaders."""

from __future__ import annotations

from pathlib import Path

import pytest

import handoffmap
from handoffmap.cli import SAMPLES

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


@pytest.fixture
def v5_path() -> Path:
    return sample_path("pydantic-ai")
