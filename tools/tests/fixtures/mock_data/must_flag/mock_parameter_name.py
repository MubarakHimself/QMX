"""MUST FLAG: a mock_ parameter threaded through shipped code."""

from __future__ import annotations


def build_session(mock_clock: object) -> object:
    return mock_clock
