"""Shared fixtures for the qmf-data store tests."""

from __future__ import annotations

from pathlib import Path

import pytest
from qmf.data.store import EvidenceStore


@pytest.fixture
def store(tmp_path: Path) -> EvidenceStore:
    """A real filesystem-backed store with a small rotation size for the tests."""
    return EvidenceStore(tmp_path / "store", rotation_bytes=256)
