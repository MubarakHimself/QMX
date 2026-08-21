"""Reference usage — CT-05 canonical serializer, fp1 fingerprint, result label,
and worlds (COMP-QMF-CORE).

Executable::

    python packages/qmf-core/examples/fingerprint_usage.py

Shows the six things CT-05 pins down:

1. One canonical serializer and one fp1 fingerprint (``fp1:sha256:<hex>``), living
   only in qmf-core — equal value implies equal fingerprint, so a Money stored at
   two scales shares one identity, and key insertion order never changes the bytes.
2. A binary float and a null are refused in identity content — identity numerics
   are integers, and an absent value is an omitted key, never a null.
3. A :class:`ResultLabel` whose parts ARE its identity, with a content-derived
   computation identity; the occurrence record sits outside identity, so the same
   label identity holds across two different occurrences.
4. ``world = simulated`` into governed evidence is a ``policy rejection`` refusal
   (reserved-unusable in V1), and a non-live world never resolves to the live
   evidence namespace.
5. A byte-identical re-write is accepted silently (idempotent); a true collision
   (same fp1 hash, differing bytes) is refused and alarmed, never overwritten.
6. Two version ladders: package SemVer is display-only and never enters identity,
   while every artifact stamps its own integer contract format version.
"""

from __future__ import annotations

from typing import TypeVar

import qmf.core
from qmf.core.chrono import Instant, Interval, WriterId
from qmf.core.exact import Money
from qmf.core.fingerprint import (
    LIVE_EVIDENCE_NAMESPACE,
    EvidenceClass,
    Fingerprint,
    GovernedEvidenceLedger,
    OccurrenceRecord,
    ResultLabel,
    World,
    canonical_bytes,
    fingerprint,
    governed_namespace,
)
from qmf.core.refusal import Result, TypedRefusal, is_ok

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    """Tiny demo helper: a construction we assert must succeed here."""
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def equal_value_equal_fingerprint() -> Fingerprint:
    """A Money stored at two scales shares one fingerprint by construction."""
    two_fifty_at_2 = _unwrap(Money.try_create(250, "USD", 2), "USD 2.50 @ scale 2")
    two_fifty_at_4 = _unwrap(Money.try_create(25000, "USD", 4), "USD 2.50 @ scale 4")
    fp_a = _unwrap(fingerprint(two_fifty_at_2), "fingerprint @ scale 2")
    fp_b = _unwrap(fingerprint(two_fifty_at_4), "fingerprint @ scale 4")
    assert fp_a == fp_b
    assert fp_a.value.startswith("fp1:sha256:")
    return fp_a


def serializer_is_order_independent() -> bytes:
    """Key insertion order never changes the canonical bytes."""
    one = _unwrap(canonical_bytes({"b": 2, "a": 1}), "bytes b,a")
    two = _unwrap(canonical_bytes({"a": 1, "b": 2}), "bytes a,b")
    assert one == two
    return one


def floats_and_nulls_are_refused() -> tuple[TypedRefusal, TypedRefusal]:
    """Identity content refuses a binary float and a null value."""
    float_refusal = canonical_bytes({"weight": 1.5})
    assert isinstance(float_refusal, TypedRefusal)
    null_refusal = canonical_bytes({"note": None})
    assert isinstance(null_refusal, TypedRefusal)
    return float_refusal, null_refusal


def label_identity_excludes_occurrence() -> tuple[ResultLabel, ResultLabel]:
    """The same label identity holds across two different occurrence records."""
    producer = _unwrap(fingerprint({"producer": "sma-20"}), "producer identity")
    input_fp = _unwrap(fingerprint({"bar": "EURUSD-1m"}), "input identity")
    start = _unwrap(Instant.try_create(1_600_000_000_000_000_000), "range start")
    end = _unwrap(Instant.try_create(1_600_000_060_000_000_000), "range end")
    span = _unwrap(Interval.try_create(start, end), "evidence range")

    label = _unwrap(
        ResultLabel.try_create(
            producer_contract_identity=producer,
            producer_contract_format_version=1,
            input_fingerprints=[input_fp],
            evidence_time_range=span,
            evidence_class=EvidenceClass.CONFIRMED,
            world=World.LIVE,
        ),
        "result label",
    )
    # An identically-built label dedups to the same computation identity even though
    # the two runs occurred at different times, on different machines.
    twin = _unwrap(
        ResultLabel.try_create(
            producer_contract_identity=producer,
            producer_contract_format_version=1,
            input_fingerprints=[input_fp],
            evidence_time_range=span,
            evidence_class=EvidenceClass.CONFIRMED,
            world=World.LIVE,
        ),
        "twin result label",
    )
    assert label.computation_identity == twin.computation_identity

    ran = _unwrap(Instant.try_create(1_600_000_070_000_000_000), "ran-at")
    writer = _unwrap(WriterId.try_create("node-a", "producer", "sma", "boot-1"), "writer")
    occurrence = _unwrap(OccurrenceRecord.try_create(ran, writer), "occurrence")
    # The occurrence is separate provenance — fingerprinting it is refused, so it can
    # never leak into identity.
    assert isinstance(fingerprint(occurrence), TypedRefusal)
    return label, twin


def simulated_is_refused_and_worlds_separate() -> TypedRefusal:
    """world=simulated is refused; a non-live world never reaches the live namespace."""
    simulated = governed_namespace(World.SIMULATED)
    assert isinstance(simulated, TypedRefusal)
    assert simulated.category.value == "policy rejection"

    replay_ns = _unwrap(governed_namespace(World.REPLAY), "replay namespace")
    live_ns = _unwrap(governed_namespace(World.LIVE), "live namespace")
    assert replay_ns != LIVE_EVIDENCE_NAMESPACE
    assert live_ns == LIVE_EVIDENCE_NAMESPACE
    return simulated


def idempotent_accept_but_collision_refused() -> TypedRefusal:
    """A byte-identical re-write is idempotent; a true collision is refused."""
    ledger = GovernedEvidenceLedger()
    content = {"result": "confirmed", "value": 42}
    first = _unwrap(ledger.write(content, world=World.LIVE), "first write")
    assert first.outcome.value == "stored"
    again = _unwrap(ledger.write(content, world=World.LIVE), "idempotent re-write")
    assert again.outcome.value == "idempotent"

    # Force a true collision: the same fp1 hash presented with differing bytes.
    collision = ledger.admit(first.fingerprint, b"tampered-bytes", namespace=first.namespace)
    assert isinstance(collision, TypedRefusal)
    assert collision.context["alarm"] is True
    return collision


def two_version_ladders() -> None:
    """Package SemVer never enters identity; the artifact stamps its format version."""
    fp = _unwrap(fingerprint({"artifact": "example"}), "artifact fingerprint")
    body = _unwrap(canonical_bytes({"artifact": "example"}), "artifact bytes")
    assert qmf.core.__version__.encode("utf-8") not in body
    assert fp.value.startswith("fp1:sha256:")


def main() -> None:
    fp = equal_value_equal_fingerprint()
    print(f"equal value, equal fingerprint: {fp.value[:19]}...")

    order_bytes = serializer_is_order_independent()
    print(f"serializer is key-order independent: {order_bytes.decode('utf-8')}")

    float_refusal, null_refusal = floats_and_nulls_are_refused()
    print(f"float refused in identity: {float_refusal.category.value}")
    print(f"null refused in identity: {null_refusal.category.value}")

    label, twin = label_identity_excludes_occurrence()
    print(f"label identity dedups across occurrences: {label == twin}")

    simulated = simulated_is_refused_and_worlds_separate()
    print(f"simulated into evidence refused: {simulated.category.value}")

    collision = idempotent_accept_but_collision_refused()
    print(f"true collision refused and alarmed: {collision.category.value}")

    two_version_ladders()
    print(f"package SemVer {qmf.core.__version__} stays out of identity")


if __name__ == "__main__":
    main()
