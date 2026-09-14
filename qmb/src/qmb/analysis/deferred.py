"""Deferred workbench refusals owned by COMP-QMB (Story 35.5).

F07 synthetic portfolio combination stays deferred: neither analysis.project
nor analysis.rerun implements combining two bots' equity/trade streams
(FR-W21, AR-W06, DEC-0273). L20 still forbids gating live money on
replay-world verdicts (FR-W28, DEC-0162).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from qmf.core.fingerprint import World
from qmf.core.refusal import TypedRefusal

from qmb._refuse import clean_token, policy

__all__ = [
    "F07_FEATURE",
    "F07_FIELDS",
    "refuse_live_money_gating",
    "refuse_synthetic_portfolio",
]

F07_FEATURE: Final[str] = "F07"
F07_FIELDS: Final[tuple[str, ...]] = (
    "combine",
    "combination",
    "combine_bots",
    "combine_equity",
    "equity_streams",
    "f07",
    "portfolio",
    "portfolio_combination",
    "synthetic_combination",
    "synthetic_portfolio",
)
_F07_SET: Final[frozenset[str]] = frozenset(F07_FIELDS)
_FALSE_TOKENS: Final[frozenset[str]] = frozenset({"0", "false", "no"})


def refuse_synthetic_portfolio(
    extra: Mapping[str, object] | None = None,
    **fields: object,
) -> TypedRefusal | None:
    """Refuse F07 synthetic portfolio combination as deferred (FR-W21, AR-W06)."""
    merged: dict[str, object] = {}
    if extra is not None:
        merged.update(dict(extra))
    merged.update(fields)
    listed = _requested_field(merged, F07_FIELDS)
    if listed is None:
        for name, value in merged.items():
            if _is_requested(value) and _fold(name) in _F07_SET:
                listed = name
                break
    if listed is None:
        return None
    return policy(
        listed,
        "F07 synthetic portfolio combination is deferred; neither analysis.project "
        "nor analysis.rerun implements combining two bots' equity/trade streams "
        "(FR-W21, AR-W06, DEC-0273)",
        deferred=True,
        feature=F07_FEATURE,
        implements_project=False,
        implements_rerun=False,
        mints_ct32=False,
    )


def refuse_live_money_gating(
    *,
    gating_live: object,
    world: str | None,
) -> TypedRefusal | None:
    """L20: replay-world verdicts cannot gate live money (FR-W28, DEC-0162)."""
    if not _is_requested(gating_live):
        return None
    folded_world = (world or World.REPLAY.value).casefold()
    if folded_world == World.LIVE.value:
        return None
    return policy(
        "world",
        "L20 forbids gating live money on replay-world verdicts; a projection "
        "saved view inherits the source world and never confirms, and a readout "
        "mints no confirmation label (FR-W28, DEC-0162)",
        world=folded_world,
        confirmed=False,
        law="L20",
        b4_role=None,
        is_admission_evidence=False,
    )


def _requested_field(fields: Mapping[str, object], names: tuple[str, ...]) -> str | None:
    for name in names:
        if _is_requested(fields.get(name)):
            return name
    return None


def _is_requested(value: object) -> bool:
    if value is None or value is False:
        return False
    token = clean_token(value)
    return not (token is not None and _fold(token) in _FALSE_TOKENS)


def _fold(token: str) -> str:
    return token.strip().replace("-", "_").replace(" ", "_").casefold()
