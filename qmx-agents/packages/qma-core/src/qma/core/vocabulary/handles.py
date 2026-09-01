"""Handle-kind money-path constraints (AD-14; DEC-0313; FR-Q53).

Handle kinds are a closed-and-addable ``qma-core`` vocabulary. Plugins never
extend it. No kind addresses a live or writable money-path record.
"""

from __future__ import annotations

from typing import Final

from qma.core.vocabulary.enums import HandleKind
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "CLOSED_HANDLE_KINDS",
    "FORBIDDEN_LIVE_MONEY_PATH_HANDLE_TARGETS",
    "HANDLE_KIND_CONTRIBUTION_POINTS",
    "MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS",
    "MONEY_PATH_RELEVANT_FIELDS",
    "QMA_OWNED_CANDIDATE_ORIGIN",
    "READ_ONLY_EVIDENCE_HANDLE_KINDS",
    "STRATEGY_CANDIDATE_ZONE",
    "assert_handle_kind_not_money_path",
    "is_forbidden_live_money_path_target",
    "is_handle_kind_contribution_point",
    "normalize_handle_target",
    "refuse_plugin_handle_kind_extension",
]


# No handle kind in the closed set identifies a live or writable money-path
# record. This frozenset is intentionally empty and stays empty: inventing a
# live-order or open-position handle is a spine amendment, not a local extension.
MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS: Final[frozenset[HandleKind]] = frozenset()

READ_ONLY_EVIDENCE_HANDLE_KINDS: Final[frozenset[HandleKind]] = frozenset(
    {HandleKind.TRADE_LOG_HANDLE, HandleKind.MARKET_DATA_HANDLE}
)

CLOSED_HANDLE_KINDS: Final[frozenset[HandleKind]] = frozenset(HandleKind)

# Contribution-point names a plugin might use to try to mint a new handle kind.
HANDLE_KIND_CONTRIBUTION_POINTS: Final[frozenset[str]] = frozenset(
    {"handle_kind", "handle", "HandleKind"}
)

# QMA-owned origin every StrategyHandle candidate carries (DEC-0313).
QMA_OWNED_CANDIDATE_ORIGIN: Final[str] = "qma"

# Parent registry's existing zone only — StrategyHandle mints no zone value.
STRATEGY_CANDIDATE_ZONE: Final[str] = "dev"

# Candidate fields that flag money_path_relevant (AD-14; DEC-0313).
MONEY_PATH_RELEVANT_FIELDS: Final[frozenset[str]] = frozenset(
    {"risk", "sizing", "exit", "protection", "binding", "priority"}
)

# Live/writable money-path nouns that may never be a handle target (CT-47).
FORBIDDEN_LIVE_MONEY_PATH_HANDLE_TARGETS: Final[frozenset[str]] = frozenset(
    {
        "open_order",
        "open_position",
        "binding",
        "book",
        "seat",
        "bms",
        "bms_record",
        "control_action",
        "kill_switch",
        "venue_session",
        "order",
        "position",
    }
)


def normalize_handle_target(target: object) -> str | None:
    """Lower-snake a handle target token; empty becomes ``None``."""
    if target is None:
        return None
    if not isinstance(target, str):
        return None
    token = target.strip().casefold().replace("-", "_").replace(" ", "_")
    while "__" in token:
        token = token.replace("__", "_")
    token = token.strip("_")
    return token or None


def is_forbidden_live_money_path_target(target: object) -> bool:
    """True when ``target`` names a live or writable money-path record."""
    token = normalize_handle_target(target)
    return token is not None and token in FORBIDDEN_LIVE_MONEY_PATH_HANDLE_TARGETS


def is_handle_kind_contribution_point(point: object) -> bool:
    """True when ``point`` would extend the closed handle-kind vocabulary."""
    return isinstance(point, str) and point in HANDLE_KIND_CONTRIBUTION_POINTS


def assert_handle_kind_not_money_path(kind: HandleKind | str) -> HandleKind:
    """Refuse any handle kind that would address live/writable money-path state."""
    resolved = parse_closed(HandleKind, kind)
    if resolved in MONEY_PATH_LIVE_WRITABLE_HANDLE_KINDS:
        raise VocabularyError(
            f"{resolved.value!r} must not identify a live or writable money-path record"
        )
    return resolved


def refuse_plugin_handle_kind_extension(kind: object) -> TypedRefusal:
    """Typed refusal: plugins never extend the closed handle-kind vocabulary."""
    given = kind.value if isinstance(kind, HandleKind) else kind
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context={
            "field": "handle_kind",
            "reason": (
                "handle kinds are a closed qma-core vocabulary extended only in "
                "that registry and never by a plugin (AD-14; DEC-0313; FR-Q53)"
            ),
            "given": repr(given),
        },
    )
