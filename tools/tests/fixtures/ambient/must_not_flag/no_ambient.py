"""MUST NOT FLAG: ordinary deterministic logic with no ambient nondeterminism."""

from __future__ import annotations


def add_ns(instant_ns: int, duration_ns: int) -> int:
    return instant_ns + duration_ns


def choose(flag: bool, left: int, right: int) -> int:
    return left if flag else right
