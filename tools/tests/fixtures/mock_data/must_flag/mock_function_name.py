"""MUST FLAG: a mock_ function shipped outside a test tree."""

from __future__ import annotations


def mock_price_feed() -> list[int]:
    return [1, 2, 3]
