"""pytest fixtures. The helpers (and the English language pin) live in helpers.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from helpers import sample_path


@pytest.fixture
def v5_path() -> Path:
    return sample_path("pydantic-ai")
