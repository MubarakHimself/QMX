"""Reference usage — the CT-10 bitemporal source-observation boundary (COMP-QMF-DATA).

Executable::

    python packages/qmf-data/examples/source_observation_usage.py

Shows the five things Story 3.2 pins down:

1. A bitemporal observation carries event-time AND known-at, a source orthogonal to
   VenueId, a revision, an AD-8 WriterId + sequence, its world, and an fp1 identity
   computed only by qmf-core (AC1).
2. A foreign timestamp and foreign money ride along verbatim — zone/offset/resolution
   and the source's scaled integer are stored unrewritten, never silently converted or
   rescaled (AC2).
3. A later correction of the same provider-native occurrence (a new revision) is a
   DISTINCT artifact with its own fp1 carrying correction_of; the original evidence is
   preserved and the correction never masquerades as it (AC3).
4. A record missing a bitemporal field does not enter governed evidence — an invalid
   input refusal (AC4/FM-1).
5. Writing world=simulated, and reading evidence from a different world than the caller
   declares, are each a policy rejection (AC5).
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import TypeVar

from qmf.core import Result, World, WriterId, is_ok, is_refusal
from qmf.data import (
    EvidenceStore,
    ForeignMoney,
    ForeignTimestamp,
    SourceObservation,
    SourceObservationBoundary,
)

T = TypeVar("T")

_EVENT_NS = 1_700_000_000_000_000_000
_KNOWN_NS = 1_700_000_001_000_000_000
_RECEIVE_NS = 1_700_000_002_000_000_000


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a call we require to succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def _require(condition: object, what: str) -> None:
    """A real check (not a bare ``assert``, which ``-O`` strips) for a demonstrated fact."""
    if not condition:
        raise AssertionError(f"expected {what}")


def _writer() -> WriterId:
    return _unwrap(WriterId.try_create("node-a", "ingest", "dukascopy", "boot-1"), "writer")


def _original() -> SourceObservation:
    """An original tick observation with verbatim foreign timestamp and money."""
    ts = _unwrap(
        ForeignTimestamp.try_create("2026-08-21T12:00:00.123", "Europe/Zurich", "+02:00", "millis"),
        "foreign timestamp",
    )
    money = _unwrap(ForeignMoney.try_create(110250, 5), "foreign money")
    return _unwrap(
        SourceObservation.try_create(
            event_time=_EVENT_NS,
            known_at=_KNOWN_NS,
            source="dukascopy",
            source_native_id="EURUSD#42",
            revision="r1",
            receive_wall_time=_RECEIVE_NS,
            writer=_writer(),
            sequence=0,
            world=World.LIVE,
            foreign_timestamp=ts,
            foreign_money=money,
        ),
        "original observation",
    )


def bitemporal_identity(observation: SourceObservation) -> str:
    """The observation carries both times and an fp1 identity from qmf-core."""
    _require(observation.event_time.value_ns == _EVENT_NS, "event-time preserved")
    _require(observation.known_at.value_ns == _KNOWN_NS, "known-at preserved")
    _require(observation.fingerprint.recipe == "fp1", "fp1 identity from qmf-core")
    return observation.fingerprint.value


def verbatim_foreign_evidence(
    boundary: SourceObservationBoundary, observation: SourceObservation
) -> None:
    """Foreign timestamp and money round-trip verbatim — no rewrite, no rescale."""
    receipt = _unwrap(boundary.admit(observation), "admit original")
    read = _unwrap(
        boundary.read(receipt.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE),
        "read original",
    )
    _require(read.foreign_timestamp is not None, "foreign timestamp present")
    _require(
        read.foreign_timestamp is not None
        and read.foreign_timestamp.verbatim == "2026-08-21T12:00:00.123",
        "foreign timestamp stored verbatim",
    )
    _require(
        read.foreign_money is not None
        and read.foreign_money.verbatim == 110250
        and read.foreign_money.scale == 5,
        "foreign money stored verbatim at the source scale",
    )


def correction_is_distinct(
    boundary: SourceObservationBoundary, original: SourceObservation
) -> tuple[str, str]:
    """A correction is a distinct artifact carrying correction_of; the original stands."""
    original_receipt = _unwrap(boundary.admit(original), "re-admit original (idempotent)")
    correction = _unwrap(
        SourceObservation.try_create(
            event_time=_EVENT_NS,
            known_at=1_700_000_099_000_000_000,
            source="dukascopy",
            source_native_id="EURUSD#42",
            revision="r2",
            receive_wall_time=1_700_000_100_000_000_000,
            writer=_writer(),
            sequence=1,
            world=World.LIVE,
            foreign_money=_unwrap(ForeignMoney.try_create(110255, 5), "corrected money"),
            correction_of=original.fingerprint,
        ),
        "correction observation",
    )
    correction_receipt = _unwrap(boundary.admit(correction), "admit correction")
    _require(correction_receipt.is_correction, "correction flagged")
    _require(
        correction_receipt.correction_of is not None
        and correction_receipt.correction_of.value == original.fingerprint.value,
        "correction_of points at the original fp1",
    )
    _require(
        correction_receipt.observation_fingerprint.value != original.fingerprint.value,
        "correction has its own distinct fp1",
    )
    still = _unwrap(
        boundary.read(
            original_receipt.archive.fingerprint, in_world=World.LIVE, for_world=World.LIVE
        ),
        "original still readable",
    )
    _require(still.revision == "r1", "original evidence preserved unchanged")
    return original.fingerprint.value, correction_receipt.observation_fingerprint.value


def incomplete_is_refused() -> str:
    """A record missing known-at does not enter governed evidence (FM-1)."""
    refused = SourceObservation.try_create(
        event_time=_EVENT_NS,
        known_at=None,
        source="dukascopy",
        source_native_id="EURUSD#42",
        revision="r1",
        receive_wall_time=_RECEIVE_NS,
        writer=_writer(),
        sequence=0,
        world=World.LIVE,
    )
    _require(is_refusal(refused), "incomplete record refused")
    return refused.category.value if is_refusal(refused) else "unexpected-ok"


def world_gates(
    boundary: SourceObservationBoundary, receipt_fingerprint: object
) -> tuple[str, str]:
    """world=simulated write and a cross-world read are each a policy rejection."""
    simulated = _unwrap(
        SourceObservation.try_create(
            event_time=_EVENT_NS,
            known_at=_KNOWN_NS,
            source="dukascopy",
            source_native_id="EURUSD#99",
            revision="r1",
            receive_wall_time=_RECEIVE_NS,
            writer=_writer(),
            sequence=0,
            world=World.SIMULATED,
        ),
        "simulated observation value",
    )
    write_refusal = boundary.admit(simulated)
    _require(is_refusal(write_refusal), "simulated write refused")
    cross = boundary.read(receipt_fingerprint, in_world=World.LIVE, for_world=World.REPLAY)
    _require(is_refusal(cross), "cross-world read refused")
    return (
        write_refusal.category.value if is_refusal(write_refusal) else "unexpected-ok",
        cross.category.value if is_refusal(cross) else "unexpected-ok",
    )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="qmf-ct10-usage-") as tmp:
        store = EvidenceStore(Path(tmp))
        boundary = SourceObservationBoundary(store)
        original = _original()

        fingerprint = bitemporal_identity(original)
        print(f"bitemporal observation fp1: {fingerprint[:24]}...")

        verbatim_foreign_evidence(boundary, original)
        print("foreign timestamp and money: stored verbatim, no rescale")

        receipt = _unwrap(boundary.admit(original), "admit original for world gate")
        original_fp, correction_fp = correction_is_distinct(boundary, original)
        _require(original_fp != correction_fp, "original and correction differ")
        print("correction: distinct fp1 with correction_of; original preserved")

        refusal = incomplete_is_refused()
        print(f"incomplete observation: {refusal}")

        write_refusal, read_refusal = world_gates(boundary, receipt.archive.fingerprint)
        print(f"simulated write and cross-world read: {write_refusal}, {read_refusal}")


if __name__ == "__main__":
    main()
