"""Handle-kind money-path constraints (AD-14; DEC-0313)."""

from __future__ import annotations

from typing import Final

from qma.core.vocabulary.enums import HandleKind
from qma.core.vocabulary.registry import VocabularyError, parse_closed

__all__ = [
    "MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS",
    "READ_ONLY_EVIDENCE_HANDLE_KINDS",
    "assert_handle_kind_not_money_path",
]

# No handle kind in the closed set identifies a live or writable money-path
# record. This frozenset is intentionally empty and stays empty: inventing a
# live-order or open-position handle is a spine amendment, not a local extension.
MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS: Final[frozenset[HandleKind]] = frozenset()

READ_ONLY_EVIDENCE_HANDLE_KINDS: Final[frozenset[HandleKind]] = frozenset(
    {HandleKind.TRADE_LOG_HANDLE, HandleKind.MARKET_DATA_HANDLE}
)


def assert_handle_kind_not_money_path(kind: HandleKind | str) -> HandleKind:
    """Refuse any handle kind that would address live/writable money-path state."""
    resolved = parse_closed(HandleKind, kind)
    if resolved in MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS:
        raise VocabularyError(
            f"{resolved.value!r} must not identify a live or writable money-path record"
        )
    return resolved
