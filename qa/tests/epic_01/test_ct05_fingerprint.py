"""Epic 1 — CT-05 canonical serializer, fp1, result label, worlds (Story 1.6,
fingerprint.py). L1 unit.

Independent, requirements-derived assertions (E1-U47..U56). Authored from CT-05
(docs/contracts/ct-05-version-fingerprint.yaml), FM-6/FM-7, epics.md Story 1.6.
Source code is read-only evidence.
"""

from __future__ import annotations

import re

from qmf.core.chrono import Instant, Interval
from qmf.core.exact import Money
from qmf.core.fingerprint import (
    LIVE_EVIDENCE_NAMESPACE,
    EvidenceClass,
    Fingerprint,
    ResultLabel,
    World,
    WriteOutcome,
    canonical_bytes,
    fingerprint,
    governed_namespace,
    reconcile_write,
)
from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok, is_refusal

FP1_RE = re.compile(r"\Afp1:sha256:[0-9a-f]{64}\Z")


def _ok(result: Result[object]) -> object:
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def _refusal(result: Result[object]) -> TypedRefusal:
    assert is_refusal(result), f"expected a TypedRefusal, got {result!r}"
    return result


def _fp(value: object) -> str:
    return _ok(fingerprint(value)).value


def _sample_label(*, producer: str, world: World = World.LIVE) -> ResultLabel:
    time_range = _ok(Interval.try_create(_ok(Instant.try_create(0)), _ok(Instant.try_create(1000))))
    return _ok(
        ResultLabel.try_create(
            producer,
            1,
            [_fp({"input": "a"})],
            time_range,
            EvidenceClass.CONFIRMED,
            world,
        )
    )


# E1-U47 -----------------------------------------------------------------------
def test_e1_u47_fp1_emits_self_describing_form() -> None:
    """CT-05: fp1 emits the form fp1:sha256:<lowercase-hex>."""
    value = _fp({"class": "thing", "k": 1})
    assert FP1_RE.match(value), value


# E1-U48 -----------------------------------------------------------------------
def test_e1_u48_float_in_identity_content_refused() -> None:
    """CT-05 / DEC-0108: a float anywhere in identity content -> refusal (never a hash
    of float bytes)."""
    assert _refusal(fingerprint(1.5)).category is RefusalCategory.INVALID_INPUT
    assert is_refusal(fingerprint({"price": 1.5}))
    assert is_refusal(fingerprint({"nested": {"x": [1, 2.0]}}))
    assert is_refusal(canonical_bytes({"price": 1.5}))


# E1-U49 -----------------------------------------------------------------------
def test_e1_u49_null_prohibited_absent_is_omitted_key() -> None:
    """CT-05 / DEC-0108: null is prohibited — an absent value is an omitted key, never
    serialized as null."""
    assert is_refusal(fingerprint({"k": None}))
    assert is_refusal(canonical_bytes({"a": {"b": None}}))
    assert is_refusal(canonical_bytes([1, None, 3]))
    # Omitting the key entirely is fine.
    assert is_ok(fingerprint({"a": 1}))


# E1-U50 -----------------------------------------------------------------------
def test_e1_u50_canonical_bytes_sorted_nfc_order_significant() -> None:
    """CT-05 / DEC-0108: canonical bytes — keys sorted lexicographically at every
    depth, no insignificant whitespace, NFC-normalized strings, order-significant
    arrays."""
    # keys sorted, compact separators
    assert _ok(canonical_bytes({"b": 1, "a": 2})) == b'{"a":2,"b":1}'
    # sort at every depth
    assert _ok(canonical_bytes({"z": {"b": 1, "a": 2}})) == b'{"z":{"a":2,"b":1}}'
    # NFC normalization: precomposed vs decomposed produce identical bytes
    assert _ok(canonical_bytes({"k": "é"})) == _ok(canonical_bytes({"k": "é"}))
    # arrays are order-significant
    assert _ok(canonical_bytes([1, 2])) != _ok(canonical_bytes([2, 1]))


# E1-U51 -----------------------------------------------------------------------
def test_e1_u51_equal_semantic_equal_fp1_single_diff_differs() -> None:
    """CT-05: equal semantic input -> equal fp1; a single differing identity field ->
    different fp1."""
    m1 = _ok(Money.try_create(150, "USD", 2))  # 1.50
    m2 = _ok(Money.try_create(15000, "USD", 4))  # 1.5000, same value
    assert _fp(m1) == _fp(m2)
    m3 = _ok(Money.try_create(151, "USD", 2))  # differs by one field
    assert _fp(m1) != _fp(m3)


# E1-U52 -----------------------------------------------------------------------
def test_e1_u52_idempotent_silent_true_collision_refused_and_alarmed() -> None:
    """CT-05 FM-6 / DEC-0108: a byte-identical re-write is accepted silently; a true
    collision (same hash, differing bytes) is refused AND alarmed, never overwritten."""
    fp = _ok(Fingerprint.try_create(_fp({"k": "v"})))
    # unseen -> stored
    assert _ok(reconcile_write(fp, b"content", None)) is WriteOutcome.STORED
    # byte-identical re-write -> idempotent (silent Ok)
    assert _ok(reconcile_write(fp, b"content", b"content")) is WriteOutcome.IDEMPOTENT
    # differing bytes under the same hash -> refused + alarmed
    collision = _refusal(reconcile_write(fp, b"content", b"different"))
    assert collision.category is RefusalCategory.POLICY_REJECTION
    assert collision.context.get("alarm") is True


# E1-U53 -----------------------------------------------------------------------
def test_e1_u53_result_label_identity_parts_occurrence_outside_identity() -> None:
    """CT-05 / DEC-0110: the ResultLabel identity parts ARE its identity; the
    occurrence record sits outside identity."""
    producer = _fp({"producer": "EMA", "period": 20})
    label = _sample_label(producer=producer)
    assert label.producer_contract_identity.value == producer
    assert label.producer_contract_format_version == 1
    assert label.evidence_class is EvidenceClass.CONFIRMED
    assert label.world is World.LIVE
    # computation identity is content-derived, and equals the label's fp1.
    assert label.computation_identity.value == _fp(label)
    # OccurrenceRecord deliberately carries no fp1_identity (outside identity).
    from qmf.core.fingerprint import OccurrenceRecord

    assert not hasattr(OccurrenceRecord, "fp1_identity")


# E1-U54 -----------------------------------------------------------------------
def test_e1_u54_world_simulated_into_governed_evidence_is_policy_rejection() -> None:
    """CT-05 FM-7 / GAP-0048: world=simulated into governed evidence -> policy
    rejection refusal; world is one of live | replay | simulated."""
    assert {w.value for w in World} == {"live", "replay", "simulated"}
    r = _refusal(governed_namespace(World.SIMULATED))
    assert r.category is RefusalCategory.POLICY_REJECTION
    assert r.context.get("gap") == "GAP-0048"


# E1-U55 -----------------------------------------------------------------------
def test_e1_u55_non_live_world_never_writes_live_namespace() -> None:
    """CT-05 / DEC-0110: a non-live world never writes the live evidence namespace
    (storage separation, not identity alone)."""
    assert _ok(governed_namespace(World.LIVE)) == LIVE_EVIDENCE_NAMESPACE
    replay_ns = _ok(governed_namespace(World.REPLAY))
    assert replay_ns != LIVE_EVIDENCE_NAMESPACE
    assert replay_ns == "replay"


# E1-U56 -----------------------------------------------------------------------
def test_e1_u56_producer_identity_distinguishes_producers() -> None:
    """CT-05 / DEC-0131: producer contract identity distinguishes producers — EMA(20)
    and SMA(20) can never share a result label."""
    ema = _sample_label(producer=_fp({"producer": "EMA", "period": 20}))
    sma = _sample_label(producer=_fp({"producer": "SMA", "period": 20}))
    assert ema.producer_contract_identity != sma.producer_contract_identity
    assert ema.computation_identity != sma.computation_identity
