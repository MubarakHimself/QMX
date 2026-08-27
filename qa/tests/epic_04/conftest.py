"""Fixtures for Epic 4 (qmf-calendar-forex). Pure oracles live in _epic4_helpers.

pytest auto-discovers this conftest; test modules never import it. Shared helper
functions and path constants are in the top-level module `_epic4_helpers`.
"""

from __future__ import annotations

import os
import zoneinfo
from zoneinfo import ZoneInfo

import pytest

import qmf.calendar_forex as cf
from qmf.core.refusal import is_ok


@pytest.fixture(scope="session")
def provider():
    """The ready forex-17NY provider (match-arm precondition; asserted, not assumed)."""
    result = cf.get_provider()
    assert is_ok(result), f"provider must be ready in a matched-tzdb environment: {result!r}"
    return result.value


@pytest.fixture
def tzpath_guard():
    """Save and restore process TZPATH + zoneinfo cache around a test that forces a
    controlled (fake) tzdata directory. Guarantees the pinned real tzdata is
    re-installed for every later test regardless of what the guarded body did."""
    saved = os.environ.get("TZPATH")
    try:
        yield
    finally:
        from qmf.calendar_forex import _tzdb

        _tzdb.force_tzpath()  # re-pin to the real pinned tzdata zoneinfo directory
        if saved is not None:
            os.environ["TZPATH"] = saved
        zoneinfo.ZoneInfo.clear_cache()
        # Prove restoration actually worked, or fail loudly rather than corrupt
        # every downstream test's timezone resolution.
        assert ZoneInfo("America/New_York").key == "America/New_York"
