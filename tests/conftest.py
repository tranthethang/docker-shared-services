"""Shared pytest fixtures. bin/ stays on sys.path until the package move in P1."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
_BIN = REPO_ROOT / "bin"
if str(_BIN) not in sys.path:
    sys.path.insert(0, str(_BIN))


@pytest.fixture
def repo_root() -> Path:
    return REPO_ROOT
