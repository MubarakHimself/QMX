"""Qualifying-loss bench fold at the node (TN-24e; SCN-0011; Story 26.7).

Persisted CT-29 exits fold under ``realized_r <= -q`` into exactly
``qualifying_loss_exit | scratch-or-partial-loss | breakeven``. Breakevens never
count under any ``q`` and are reported as their own clustering metric; scratches
and partials count only where the declared family ``q`` reaches them. The fold
boundary is the binding epoch. Stale exit persistence refuses the next same-seat
intent. A threshold crossing benches the seat and routes it to the paired demo
target while the Book stays LIVE (FR-077; DEC-0155, DEC-0209).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core import ExactRational, Fingerprint, Ok, Result, UnitKind, is_refusal
from qmf.risk.exit_record import (
    QUALIFYING_LOSS_THRESHOLD_VARIABLE,
    BenchDisposition,
    BenchFoldResult,
    check_recording_precedes_interpretation,
    classify_bench_disposition,
    fold_bench,
)
from qmf.risk.paper import BookMode, ExecutionResolution, ExecutionTarget, SeatState
from qmf.risk.sizing import BENCH_THRESHOLD_VARIABLE

from qmn.capital._refuse import invalid, policy
from qmn.paper.demotion import ProtectiveDemotionKind, route_protective_demotion

__all__ = [
    "BENCH_CONSECUTIVE_LOSS_THRESHOLD_REGISTRY_KEY",
    "BENCH_DISPOSITIONS",
    "BENCH_FOLD_FIXTURE",
    "QUALIFYING_LOSS_THRESHOLD_REGISTRY_KEY",
    "BenchCrossingEffect",
    "BenchFoldReport",
    "apply_bench_crossing",
    "evaluate_qualifying_loss_bench",
    "refuse_stale_exit_before_intent",
]


# Fixture binding for SCN-0011 (docs/lenses/testing/fixtures-and-scenarios.md).
BENCH_FOLD_FIXTURE: Final[str] = "qmn/bench-fold"

QUALIFYING_LOSS_THRESHOLD_REGISTRY_KEY: Final[str] = QUALIFYING_LOSS_THRESHOLD_VARIABLE
BENCH_CONSECUTIVE_LOSS_THRESHOLD_REGISTRY_KEY: Final[str] = BENCH_THRESHOLD_VARIABLE

BENCH_DISPOSITIONS: Final[frozenset[str]] = frozenset(
    {
        BenchDisposition.QUALIFYING_LOSS_EXIT.value,
        BenchDisposition.SCRATCH_OR_PARTIAL_LOSS.value,
        BenchDisposition.BREAKEVEN.value,
    }
)


@dataclass(frozen=True, slots=True)
class BenchFoldReport:
    """Node-facing bench fold with clustering and disposition vocabulary."""

    fold: BenchFoldResult
    dispositions_closed: frozenset[str]
    breakeven_clustering_count: int
    binding_epoch: Fingerprint
    q_registry_key: str = QUALIFYING_LOSS_THRESHOLD_REGISTRY_KEY
    threshold_registry_key: str = BENCH_CONSECUTIVE_LOSS_THRESHOLD_REGISTRY_KEY

    @property
    def threshold_crossed(self) -> bool:
        return self.fold.threshold_crossed

    @property
    def qualifying_loss_count(self) -> int:
        return self.fold.qualifying_loss_count

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_epoch": self.binding_epoch.value,
                "breakeven_clustering_count": self.breakeven_clustering_count,
                "dispositions_closed": sorted(self.dispositions_closed),
                "q_registry_key": self.q_registry_key,
                "qualifying_loss_count": self.qualifying_loss_count,
                "threshold_crossed": self.threshold_crossed,
                "threshold_registry_key": self.threshold_registry_key,
            }
        )


@dataclass(frozen=True, slots=True)
class BenchCrossingEffect:
    """Seat benched → paper route; Book stays LIVE (SCN-0011)."""

    report: BenchFoldReport
    seat_state: SeatState
    book_mode: BookMode
    routing: ExecutionResolution

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "book_mode": self.book_mode.value,
                "report": self.report.as_mapping(),
                "routing": self.routing.fp1_identity(),
                "seat_state": self.seat_state.value,
            }
        )


def evaluate_qualifying_loss_bench(
    records: object,
    *,
    binding_epoch: object,
    q: object,
    threshold: object,
    as_of: object = None,
) -> Result[BenchFoldReport]:
    """Read-time qualifying-loss fold bounded by the binding epoch (SCN-0011).

    Every exit classifies into exactly the closed three dispositions. Breakevens
    never increment the qualifying-loss count under any ``q``.
    """
    if not isinstance(binding_epoch, Fingerprint):
        return invalid(
            "binding_epoch",
            "the bench fold is bounded by the binding epoch",
            given=repr(binding_epoch),
        )
    if not isinstance(q, ExactRational) or q.unit_kind is not UnitKind.R_MULTIPLE:
        return invalid(
            QUALIFYING_LOSS_THRESHOLD_REGISTRY_KEY,
            "qualifying_loss_threshold q is a positive r-multiple ExactRational — "
            "per-family UI-editable, never a spine constant",
            given=repr(q),
        )
    folded = fold_bench(
        records,
        binding_epoch=binding_epoch,
        q=q,
        threshold=threshold,
        as_of=as_of,
    )
    if is_refusal(folded):
        return folded

    # Prove every considered exit uses exactly the closed disposition vocabulary.
    observed = {d.value for d in folded.value.dispositions}
    if not observed.issubset(BENCH_DISPOSITIONS | {BenchDisposition.GAIN.value}):
        return policy(
            "dispositions",
            "every exit uses exactly qualifying_loss_exit | scratch-or-partial-loss | "
            "breakeven (gains are recorded apart and never bench)",
            observed=sorted(observed),
            required=sorted(BENCH_DISPOSITIONS),
        )

    # Breakevens never count toward the qualifying fold under any q.
    for record, disposition in zip(
        folded.value.considered, folded.value.dispositions, strict=True
    ):
        if disposition is BenchDisposition.BREAKEVEN:
            continue
        classified = classify_bench_disposition(record, q=q)
        if is_refusal(classified):
            return classified
        if classified.value is BenchDisposition.BREAKEVEN:
            return policy(
                "breakeven",
                "a stamped breakeven never counts under any q",
            )

    return Ok(
        BenchFoldReport(
            fold=folded.value,
            dispositions_closed=BENCH_DISPOSITIONS,
            breakeven_clustering_count=folded.value.breakeven_count,
            binding_epoch=binding_epoch,
        )
    )


def apply_bench_crossing(
    report: object,
    *,
    live_target: object,
    paper_target: object,
    book_mode: object = BookMode.LIVE,
) -> Result[BenchCrossingEffect]:
    """Bench the seat and route to paper while the Book stays LIVE."""
    if not isinstance(report, BenchFoldReport):
        return invalid(
            "report",
            "apply_bench_crossing reads a BenchFoldReport",
            given=repr(report),
        )
    if not report.threshold_crossed:
        return policy(
            "report",
            "apply_bench_crossing requires the qualifying-loss threshold to be crossed",
            qualifying_loss_count=report.qualifying_loss_count,
            threshold=report.fold.threshold,
        )
    if not isinstance(live_target, ExecutionTarget) or not isinstance(paper_target, ExecutionTarget):
        return invalid(
            "execution_target",
            "bench routing reads typed live and paper ExecutionTargets",
        )
    resolved_mode = BookMode.LIVE
    if isinstance(book_mode, BookMode):
        resolved_mode = book_mode
    elif isinstance(book_mode, str):
        try:
            resolved_mode = BookMode(book_mode)
        except ValueError:
            return invalid(
                "book_mode",
                "Book mode is LIVE|PAPER; BENCHED is a seat word only",
                given=repr(book_mode),
            )

    routing_r = route_protective_demotion(
        kind=ProtectiveDemotionKind.BENCHED_SEAT,
        live_target=live_target,
        paper_target=paper_target,
        book_mode=resolved_mode,
        seat_state=SeatState.BENCHED,
    )
    if is_refusal(routing_r):
        return routing_r

    return Ok(
        BenchCrossingEffect(
            report=report,
            seat_state=SeatState.BENCHED,
            book_mode=resolved_mode,
            routing=routing_r.value,
        )
    )


def refuse_stale_exit_before_intent(
    *,
    closing_exit_record: object,
    persisted: object,
    journaled: object,
) -> Result[None]:
    """Recording precedes interpretation — stale exit refuses the next intent."""
    return check_recording_precedes_interpretation(
        closing_exit_record=closing_exit_record,
        persisted=persisted,
        journaled=journaled,
    )
