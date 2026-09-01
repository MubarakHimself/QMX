"""Protective demotions and market-risk paper blocks (TN-9; Story 26.5).

Capital/authority controls (benched seat, kill-line stand-down) route to the
paired demo target while the Book may stay LIVE. Market-risk controls
(protection windows, dead zones, KSA kill switch) block paper and live entries
alike. A silent paper outage raises the same alarm class as a live outage
(AD-35; DEC-0149, DEC-0194).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Ok, Result, TypedRefusal, is_refusal
from qmf.risk.paper import (
    ActiveControl,
    BookMode,
    ExecutionResolution,
    SeatState,
    TriggerDisposition,
)

from qmn.paper._refuse import clean_token, invalid, policy
from qmn.paper.routing import resolve_book_execution_target

__all__ = [
    "CAPITAL_AUTHORITY_DEMOTION_KINDS",
    "LIVE_OUTAGE_ALARM_CLASS",
    "MARKET_RISK_BLOCK_KINDS",
    "PAPER_OUTAGE_ALARM_CLASS",
    "MarketRiskBlockKind",
    "PaperOutageAlarm",
    "ProtectiveDemotionKind",
    "active_control_for_demotion",
    "active_control_for_market_risk",
    "raise_paper_outage_alarm",
    "route_protective_demotion",
]


# Same push class a live stream outage uses (DEC-0149 / metrics-and-alerts).
LIVE_OUTAGE_ALARM_CLASS: Final[str] = "silent-degradation"
PAPER_OUTAGE_ALARM_CLASS: Final[str] = LIVE_OUTAGE_ALARM_CLASS


class ProtectiveDemotionKind(StrEnum):
    """Capital/authority demotions that route to paper (AD-35).

    Distinct from market-risk blocks. A benched seat or kill-line stand-down
    keeps evidence flowing on the paired demo target; the Book itself may stay
    LIVE.
    """

    BENCHED_SEAT = "benched-seat"
    KILL_LINE_STAND_DOWN = "kill-line-stand-down"


class MarketRiskBlockKind(StrEnum):
    """Market-risk controls that block paper exactly as live (AD-35)."""

    PROTECTION_WINDOW = "protection-window"
    DEAD_ZONE = "dead-zone"
    KILL_SWITCH = "kill-switch"
    KSA_MARKET_RISK = "ksa-market-risk"


CAPITAL_AUTHORITY_DEMOTION_KINDS: Final[frozenset[ProtectiveDemotionKind]] = frozenset(
    ProtectiveDemotionKind
)
MARKET_RISK_BLOCK_KINDS: Final[frozenset[MarketRiskBlockKind]] = frozenset(MarketRiskBlockKind)


@dataclass(frozen=True, slots=True)
class PaperOutageAlarm:
    """Alarm raised for a blocked or silent paper stream (DEC-0149).

    Severity matches the live outage class — a silent paper outage corrupts
    every decay verdict computed after it.
    """

    alarm_class: str
    binding_epoch: str
    paper_account_id: str
    cause: str
    matches_live_class: bool = True

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "alarm_class": self.alarm_class,
                "binding_epoch": self.binding_epoch,
                "cause": self.cause,
                "matches_live_class": self.matches_live_class,
                "paper_account_id": self.paper_account_id,
            }
        )


def active_control_for_demotion(
    kind: object,
    *,
    control_id: object = None,
) -> Result[ActiveControl]:
    """Mint a ``routes-to-paper`` active control for a capital/authority demotion."""
    resolved = _coerce_demotion_kind(kind)
    if not isinstance(resolved, ProtectiveDemotionKind):
        return resolved
    token = clean_token(control_id) if control_id is not None else resolved.value
    if token is None:
        return invalid(
            "control_id",
            "an active control names a non-empty control id",
            given=repr(control_id),
        )
    return ActiveControl.try_create(token, TriggerDisposition.ROUTES_TO_PAPER)


def active_control_for_market_risk(
    kind: object,
    *,
    control_id: object = None,
) -> Result[ActiveControl]:
    """Mint a ``blocks-paper`` active control for a market-risk window/KSA."""
    resolved = _coerce_market_risk_kind(kind)
    if not isinstance(resolved, MarketRiskBlockKind):
        return resolved
    token = clean_token(control_id) if control_id is not None else resolved.value
    if token is None:
        return invalid(
            "control_id",
            "an active control names a non-empty control id",
            given=repr(control_id),
        )
    return ActiveControl.try_create(token, TriggerDisposition.BLOCKS_PAPER)


def route_protective_demotion(
    *,
    kind: object,
    live_target: object,
    paper_target: object,
    book_mode: object = BookMode.LIVE,
    seat_state: object = None,
    extra_controls: object = (),
) -> Result[ExecutionResolution]:
    """Route a capital/authority demotion to the paired demo target.

    Benched-seat demotions set seat state ``benched``; kill-line demotions add a
    ``routes-to-paper`` control while the Book may remain LIVE. Market-risk
    controls in ``extra_controls`` still dominate and block both modes.
    """
    resolved = _coerce_demotion_kind(kind)
    if not isinstance(resolved, ProtectiveDemotionKind):
        return resolved

    if seat_state is None:
        seat: object = (
            SeatState.BENCHED
            if resolved is ProtectiveDemotionKind.BENCHED_SEAT
            else SeatState.ACTIVE
        )
    else:
        seat = seat_state

    controls_result = _coerce_controls(extra_controls)
    if not isinstance(controls_result, tuple):
        return controls_result
    controls = list(controls_result)

    if resolved is ProtectiveDemotionKind.KILL_LINE_STAND_DOWN:
        demotion = active_control_for_demotion(resolved)
        if is_refusal(demotion):
            return demotion
        controls.append(demotion.value)

    return resolve_book_execution_target(
        book_mode=book_mode,
        seat_state=seat,
        active_controls=tuple(controls),
        live_target=live_target,
        paper_target=paper_target,
    )


def raise_paper_outage_alarm(
    *,
    binding_epoch: object,
    paper_account_id: object,
    cause: object,
) -> Result[PaperOutageAlarm]:
    """Raise the live outage alarm class for a silent/blocked paper stream."""
    if isinstance(binding_epoch, Fingerprint):
        epoch = binding_epoch.value
    else:
        epoch_token = clean_token(binding_epoch)
        if epoch_token is None:
            return invalid(
                "binding_epoch",
                "a paper outage alarm cites the binding epoch",
                given=repr(binding_epoch),
            )
        epoch = epoch_token
    account = clean_token(paper_account_id)
    if account is None:
        return invalid(
            "paper_account_id",
            "a paper outage alarm names the paired demo account",
            given=repr(paper_account_id),
        )
    reason = clean_token(cause)
    if reason is None:
        return invalid(
            "cause",
            "a paper outage alarm names the outage cause "
            "(blocked-stream|unresolved-unknown|silent-outage)",
            given=repr(cause),
        )
    if PAPER_OUTAGE_ALARM_CLASS != LIVE_OUTAGE_ALARM_CLASS:
        return policy(
            "alarm_class",
            "paper outage must raise the live alarm class",
            paper=PAPER_OUTAGE_ALARM_CLASS,
            live=LIVE_OUTAGE_ALARM_CLASS,
        )
    return Ok(
        PaperOutageAlarm(
            alarm_class=PAPER_OUTAGE_ALARM_CLASS,
            binding_epoch=epoch,
            paper_account_id=account,
            cause=reason,
            matches_live_class=True,
        )
    )


def _coerce_demotion_kind(kind: object) -> ProtectiveDemotionKind | TypedRefusal:
    if isinstance(kind, ProtectiveDemotionKind):
        return kind
    if isinstance(kind, str):
        try:
            return ProtectiveDemotionKind(kind)
        except ValueError:
            return invalid(
                "kind",
                "protective demotion is benched-seat|kill-line-stand-down",
                given=repr(kind),
                allowed=[m.value for m in ProtectiveDemotionKind],
            )
    return invalid(
        "kind",
        "protective demotion is benched-seat|kill-line-stand-down",
        given=repr(kind),
    )


def _coerce_market_risk_kind(kind: object) -> MarketRiskBlockKind | TypedRefusal:
    if isinstance(kind, MarketRiskBlockKind):
        return kind
    if isinstance(kind, str):
        try:
            return MarketRiskBlockKind(kind)
        except ValueError:
            return invalid(
                "kind",
                "market-risk block is protection-window|dead-zone|kill-switch|ksa-market-risk",
                given=repr(kind),
                allowed=[m.value for m in MarketRiskBlockKind],
            )
    return invalid(
        "kind",
        "market-risk block is protection-window|dead-zone|kill-switch|ksa-market-risk",
        given=repr(kind),
    )


def _coerce_controls(value: object) -> tuple[ActiveControl, ...] | TypedRefusal:
    if isinstance(value, ActiveControl):
        return (value,)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        items: list[ActiveControl] = []
        for item in cast("Sequence[object]", value):
            if not isinstance(item, ActiveControl):
                return invalid(
                    "extra_controls",
                    "extra controls are ActiveControl values",
                    given=repr(item),
                )
            items.append(item)
        return tuple(items)
    return invalid(
        "extra_controls",
        "extra controls are a collection of ActiveControl values",
        given=repr(value),
    )
