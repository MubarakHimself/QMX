"""Executable CT-05 contract test, owned by qmf-core.

Verifies the single canonical serializer and fp1 fingerprint, the result label with
its content-derived computation identity, the occurrence record sitting outside
identity, the world enum and its policy (simulated refused, non-live never writes
the live namespace), the FM-6 idempotent/collision guard, and the two version
ladders (CT-05; DEC-0108, DEC-0110, DEC-0131, DEC-0158). Written to exercise the
public ``qmf.core.fingerprint`` surface at and beyond the 80% floor.
"""

from __future__ import annotations

import hashlib
import json
import unicodedata
from fractions import Fraction
from typing import TypeVar

import qmf.core
from qmf.core.chrono import Instant, Interval, WriterId
from qmf.core.exact import Money, Price
from qmf.core.fingerprint import (
    CONTRACT_FORMAT_VERSION,
    LIVE_EVIDENCE_NAMESPACE,
    EvidenceClass,
    Fingerprint,
    GovernedEvidenceLedger,
    OccurrenceRecord,
    ResultLabel,
    World,
    WriteOutcome,
    canonical_bytes,
    fingerprint,
    governed_namespace,
    reconcile_write,
)
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Result, Retryability, is_ok, is_refusal

T = TypeVar("T")


# --- helpers ----------------------------------------------------------------


def _ok(result: Result[T]) -> T:
    """Unwrap a success arm, asserting it constructed (narrows via is_ok)."""
    assert is_ok(result), result
    return result.value


def _instrument() -> Instrument:
    venue = _ok(VenueId.try_create("venue-1"))
    return _ok(Instrument.try_create(venue, "EURUSD"))


def _money(value: int, currency: str = "USD", scale: int = 2) -> Money:
    return _ok(Money.try_create(value, currency, scale))


def _bytes(payload: object) -> bytes:
    return _ok(canonical_bytes(payload))


def _fp(payload: object) -> Fingerprint:
    return _ok(fingerprint(payload))


def _instant(value_ns: int) -> Instant:
    return _ok(Instant.try_create(value_ns))


def _interval(start_ns: int = 1_000_000_000, end_ns: int = 2_000_000_000) -> Interval:
    return _ok(Interval.try_create(_instant(start_ns), _instant(end_ns)))


def _writer() -> WriterId:
    return _ok(WriterId.try_create("node-a", "producer", "sma", "boot-1"))


def _label_result(**overrides: object) -> Result[ResultLabel]:
    parts: dict[str, object] = {
        "producer_contract_identity": _fp({"producer": "sma-20"}),
        "producer_contract_format_version": 1,
        "input_fingerprints": [_fp({"bar": "EURUSD-1m"})],
        "evidence_time_range": _interval(),
        "evidence_class": EvidenceClass.CONFIRMED,
        "world": World.LIVE,
    }
    parts.update(overrides)
    return ResultLabel.try_create(**parts)


def _label(**overrides: object) -> ResultLabel:
    return _ok(_label_result(**overrides))


# --- the canonical serializer -----------------------------------------------


def test_serializer_sorts_keys_and_strips_whitespace() -> None:
    assert _bytes({"b": 1, "a": {"d": 4, "c": 3}}) == b'{"a":{"c":3,"d":4},"b":1}'


def test_serializer_is_key_order_independent() -> None:
    assert canonical_bytes({"x": 1, "y": 2}) == canonical_bytes({"y": 2, "x": 1})


def test_serializer_is_utf8_json() -> None:
    body = _bytes({"symbol": "eé"})
    assert isinstance(body, bytes)
    assert json.loads(body.decode("utf-8")) == {"symbol": "eé"}


def test_serializer_nfc_normalizes_strings() -> None:
    composed = "café"  # é as U+00E9
    decomposed = "café"  # e + combining acute U+0301
    assert composed != decomposed
    assert canonical_bytes(composed) == canonical_bytes(decomposed)


def test_serializer_nfc_normalizes_keys() -> None:
    assert canonical_bytes({"café": 1}) == canonical_bytes({"café": 1})


def test_serializer_refuses_two_keys_that_normalize_together() -> None:
    result = canonical_bytes({"café": 1, "café": 2})
    assert is_refusal(result)
    assert result.context["field"] == "key"


def test_serializer_arrays_are_order_significant() -> None:
    assert canonical_bytes([1, 2, 3]) != canonical_bytes([3, 2, 1])


def test_serializer_accepts_tuple_as_array() -> None:
    assert canonical_bytes((1, 2, 3)) == canonical_bytes([1, 2, 3])


def test_serializer_bool_is_json_true_false_not_int() -> None:
    assert _bytes({"flag": True}) == b'{"flag":true}'
    assert canonical_bytes(True) != canonical_bytes(1)


def test_serializer_refuses_float_in_identity() -> None:
    result = canonical_bytes({"weight": 1.5})
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.retryability is Retryability.NO


def test_serializer_refuses_top_level_float() -> None:
    assert is_refusal(canonical_bytes(3.14))


def test_serializer_refuses_null_value() -> None:
    result = canonical_bytes({"note": None})
    assert is_refusal(result)
    assert result.context["key"] == "note"


def test_serializer_refuses_null_in_array() -> None:
    assert is_refusal(canonical_bytes([1, None, 3]))


def test_serializer_refuses_nested_unsupported_in_array() -> None:
    # A non-null but uncanonicalizable element propagates its refusal out of the array.
    assert is_refusal(canonical_bytes([1, 2.5]))


def test_serializer_refuses_top_level_null() -> None:
    assert is_refusal(canonical_bytes(None))


def test_serializer_refuses_non_string_key() -> None:
    result = canonical_bytes({1: "one"})
    assert is_refusal(result)
    assert result.context["field"] == "key"


def test_serializer_refuses_bool_key() -> None:
    assert is_refusal(canonical_bytes({True: "x"}))


def test_serializer_refuses_unsupported_type() -> None:
    result = canonical_bytes({"blob": b"raw"})
    assert is_refusal(result)
    assert result.context["field"] == "value"


def test_serializer_refuses_fraction_forcing_canonical_form() -> None:
    assert is_refusal(canonical_bytes({"ratio": Fraction(1, 3)}))


def test_serializer_accepts_empty_object_and_array() -> None:
    assert _bytes({}) == b"{}"
    assert _bytes([]) == b"[]"


def test_serializer_resolves_value_types_via_fp1_identity() -> None:
    money = _money(250)
    assert _bytes(money) == _bytes(money.fp1_identity())


# --- the fp1 fingerprint ----------------------------------------------------


def test_fingerprint_emitted_form() -> None:
    fp = _fp({"a": 1})
    assert fp.value.startswith("fp1:sha256:")
    assert fp.recipe == "fp1"
    assert fp.algorithm == "sha256"
    assert len(fp.digest) == 64


def test_fingerprint_matches_sha256_of_canonical_bytes() -> None:
    payload = {"a": 1, "b": [2, 3]}
    assert _fp(payload).digest == hashlib.sha256(_bytes(payload)).hexdigest()


def test_fingerprint_propagates_serializer_refusal() -> None:
    assert is_refusal(fingerprint({"weight": 1.5}))


def test_equal_value_equal_fingerprint_across_scales() -> None:
    assert _fp(_money(250, scale=2)) == _fp(_money(25000, scale=4))


def test_price_and_money_of_equal_magnitude_differ_by_class() -> None:
    money = _money(15000, scale=5)
    price = _ok(Price.try_create(15000, _instrument(), 5))
    assert _fp(money) != _fp(price)


# --- Fingerprint parsing ----------------------------------------------------


def test_fingerprint_try_create_roundtrips() -> None:
    original = _fp({"x": 1})
    assert _ok(Fingerprint.try_create(original.value)) == original


def test_fingerprint_try_create_rejects_non_string() -> None:
    assert is_refusal(Fingerprint.try_create(123))


def test_fingerprint_try_create_rejects_wrong_shape() -> None:
    assert is_refusal(Fingerprint.try_create("fp1:sha256"))


def test_fingerprint_try_create_rejects_wrong_recipe() -> None:
    assert is_refusal(Fingerprint.try_create("fp2:sha256:" + "a" * 64))


def test_fingerprint_try_create_rejects_wrong_algorithm() -> None:
    assert is_refusal(Fingerprint.try_create("fp1:sha512:" + "a" * 64))


def test_fingerprint_try_create_rejects_bad_digest() -> None:
    assert is_refusal(Fingerprint.try_create("fp1:sha256:XYZ"))
    assert is_refusal(Fingerprint.try_create("fp1:sha256:" + "A" * 64))  # uppercase


# --- the result label -------------------------------------------------------


def test_label_parts_are_its_identity() -> None:
    label = _label()
    assert label.computation_identity == _fp(label.fp1_identity())


def test_label_computation_identity_dedups_identical_work() -> None:
    assert _label().computation_identity == _label().computation_identity


def test_label_identity_changes_with_any_part() -> None:
    base = _label().computation_identity
    assert _label(world=World.REPLAY).computation_identity != base
    assert _label(evidence_class=EvidenceClass.PROVISIONAL).computation_identity != base
    assert _label(producer_contract_format_version=2).computation_identity != base


def test_label_fp1_identity_omits_computation_identity() -> None:
    # computation identity is derived FROM the parts, never re-folded in (no cycle).
    assert "computation_identity" not in _label().fp1_identity()


def test_label_accepts_fingerprint_strings() -> None:
    label = _label(
        producer_contract_identity=_fp({"producer": "x"}).value,
        input_fingerprints=[_fp({"in": "y"}).value],
        evidence_class="confirmed",
        world="live",
    )
    assert isinstance(label, ResultLabel)


def test_label_accepts_empty_inputs() -> None:
    assert _label(input_fingerprints=[]).input_fingerprints == ()


def test_label_input_fingerprints_are_order_significant() -> None:
    a = _fp({"a": 1})
    b = _fp({"b": 2})
    forward = _label(input_fingerprints=[a, b]).computation_identity
    reverse = _label(input_fingerprints=[b, a]).computation_identity
    assert forward != reverse


def test_label_refuses_bad_producer_identity() -> None:
    result = _label_result(producer_contract_identity="not-a-fingerprint")
    assert is_refusal(result)
    assert result.context["field"] == "producer_contract_identity"


def test_label_refuses_non_positive_format_version() -> None:
    assert is_refusal(_label_result(producer_contract_format_version=0))


def test_label_refuses_bool_format_version() -> None:
    assert is_refusal(_label_result(producer_contract_format_version=True))


def test_label_refuses_non_sequence_inputs() -> None:
    result = _label_result(input_fingerprints="fp1:sha256:" + "a" * 64)
    assert is_refusal(result)
    assert result.context["field"] == "input_fingerprints"


def test_label_refuses_bad_input_element() -> None:
    result = _label_result(input_fingerprints=["nope"])
    assert is_refusal(result)
    assert result.context["index"] == 0


def test_label_refuses_non_interval_range() -> None:
    assert is_refusal(_label_result(evidence_time_range="2024-01-01"))


def test_label_refuses_bad_evidence_class() -> None:
    assert is_refusal(_label_result(evidence_class="gospel"))


def test_label_refuses_bad_world() -> None:
    assert is_refusal(_label_result(world="dreamt"))


def test_label_refuses_non_string_non_enum_world() -> None:
    assert is_refusal(_label_result(world=123))


def test_label_refuses_non_string_non_enum_evidence_class() -> None:
    assert is_refusal(_label_result(evidence_class=123))


# --- occurrence sits outside identity ---------------------------------------


def test_occurrence_record_builds() -> None:
    record = _ok(OccurrenceRecord.try_create(_instant(1_600_000_000_000_000_000), _writer()))
    assert isinstance(record, OccurrenceRecord)


def test_occurrence_record_refuses_bad_parts() -> None:
    assert is_refusal(OccurrenceRecord.try_create("now", _writer()))
    assert is_refusal(OccurrenceRecord.try_create(_instant(0), "me"))


def test_occurrence_record_is_not_fingerprintable() -> None:
    record = _ok(OccurrenceRecord.try_create(_instant(0), _writer()))
    # No fp1_identity: an occurrence can never leak into identity.
    assert is_refusal(fingerprint(record))


# --- worlds and the storage-separation policy -------------------------------


def test_world_enum_is_the_closed_set() -> None:
    assert {member.value for member in World} == {"live", "replay", "simulated"}


def test_evidence_class_enum_is_the_closed_set() -> None:
    assert {member.value for member in EvidenceClass} == {
        "confirmed",
        "unconfirmed",
        "provisional",
    }


def test_simulated_into_governed_evidence_is_policy_rejection() -> None:
    result = governed_namespace(World.SIMULATED)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context["gap"] == "GAP-0048"


def test_non_live_world_never_resolves_to_live_namespace() -> None:
    assert _ok(governed_namespace(World.LIVE)) == LIVE_EVIDENCE_NAMESPACE
    assert _ok(governed_namespace(World.REPLAY)) != LIVE_EVIDENCE_NAMESPACE


def test_governed_namespace_refuses_unknown_world() -> None:
    assert is_refusal(governed_namespace("holodeck"))


# --- FM-6 idempotent / collision guard --------------------------------------


def test_reconcile_first_write_is_stored() -> None:
    assert _ok(reconcile_write(_fp({"x": 1}), _bytes({"x": 1}), None)) is WriteOutcome.STORED


def test_reconcile_identical_rewrite_is_idempotent() -> None:
    body = _bytes({"x": 1})
    assert _ok(reconcile_write(_fp({"x": 1}), body, body)) is WriteOutcome.IDEMPOTENT


def test_reconcile_true_collision_is_refused_and_alarmed() -> None:
    result = reconcile_write(_fp({"x": 1}), _bytes({"x": 1}), b"different-bytes")
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context["alarm"] is True
    assert result.context["notification_tier"] == "alarm"


def test_reconcile_rejects_bad_arguments() -> None:
    body = _bytes({"x": 1})
    fp = _fp({"x": 1})
    assert is_refusal(reconcile_write("not-fp", body, None))
    assert is_refusal(reconcile_write(fp, "not-bytes", None))
    assert is_refusal(reconcile_write(fp, body, "not-bytes"))


def test_ledger_write_then_idempotent_rewrite() -> None:
    ledger = GovernedEvidenceLedger()
    content = {"result": "x", "n": 1}
    first = _ok(ledger.write(content, world=World.LIVE))
    assert first.outcome is WriteOutcome.STORED
    assert first.namespace == LIVE_EVIDENCE_NAMESPACE
    assert _ok(ledger.write(content, world=World.LIVE)).outcome is WriteOutcome.IDEMPOTENT


def test_ledger_collision_is_refused_never_overwritten() -> None:
    ledger = GovernedEvidenceLedger()
    first = _ok(ledger.write({"n": 1}, world=World.LIVE))
    collision = ledger.admit(first.fingerprint, b"tampered", namespace=first.namespace)
    assert is_refusal(collision)
    # The stored bytes are untouched: the original re-writes idempotently.
    assert _ok(ledger.write({"n": 1}, world=World.LIVE)).outcome is WriteOutcome.IDEMPOTENT


def test_ledger_routes_worlds_to_separate_namespaces() -> None:
    ledger = GovernedEvidenceLedger()
    live = _ok(ledger.write({"n": 1}, world=World.LIVE))
    replay = _ok(ledger.write({"n": 1}, world=World.REPLAY))
    assert live.namespace == LIVE_EVIDENCE_NAMESPACE
    assert replay.namespace != LIVE_EVIDENCE_NAMESPACE
    # Same content, different worlds — one fingerprint, two independent namespaces.
    assert live.fingerprint == replay.fingerprint


def test_ledger_write_simulated_is_refused() -> None:
    assert is_refusal(GovernedEvidenceLedger().write({"n": 1}, world=World.SIMULATED))


def test_ledger_write_propagates_serializer_refusal() -> None:
    assert is_refusal(GovernedEvidenceLedger().write({"weight": 1.5}, world=World.LIVE))


def test_ledger_admit_rejects_bad_arguments() -> None:
    ledger = GovernedEvidenceLedger()
    fp = _fp({"x": 1})
    body = _bytes({"x": 1})
    assert is_refusal(ledger.admit("not-fp", body, namespace="live"))
    assert is_refusal(ledger.admit(fp, "not-bytes", namespace="live"))
    assert is_refusal(ledger.admit(fp, body, namespace="  "))


def test_ledger_admit_refuses_fingerprint_bytes_mismatch() -> None:
    # Regression (M8): admit fingerprints the presented bytes and refuses a
    # mismatch (invalid input) before storing — the fingerprint of A presented
    # with the bytes of B is a caller bug, not a content-addressed write.
    ledger = GovernedEvidenceLedger()
    fp_a = _fp({"n": 1})
    bytes_b = _bytes({"n": 2})
    result = ledger.admit(fp_a, bytes_b, namespace=LIVE_EVIDENCE_NAMESPACE)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context["field"] == "fp"
    # It is refused as invalid input, never as a collision alarm.
    assert result.context.get("alarm") is not True


def test_ledger_admit_mismatch_never_manufactures_a_false_collision() -> None:
    # Regression (M8): the refused mismatch stores nothing, so the NEXT correct
    # write under that fingerprint is a clean first store — not a spurious 'true
    # collision' alarm, the one signal that must never be noise (FM-6).
    ledger = GovernedEvidenceLedger()
    fp_a = _fp({"n": 1})
    bytes_b = _bytes({"n": 2})
    assert is_refusal(ledger.admit(fp_a, bytes_b, namespace=LIVE_EVIDENCE_NAMESPACE))
    receipt = _ok(ledger.write({"n": 1}, world=World.LIVE))
    assert receipt.outcome is WriteOutcome.STORED
    assert receipt.fingerprint == fp_a


def test_ledger_admit_accepts_matching_fingerprint_and_bytes() -> None:
    # The positive counterpart: a write whose fingerprint matches its bytes is
    # admitted and stored.
    ledger = GovernedEvidenceLedger()
    content = {"n": 1}
    receipt = _ok(ledger.admit(_fp(content), _bytes(content), namespace=LIVE_EVIDENCE_NAMESPACE))
    assert receipt.outcome is WriteOutcome.STORED


def test_ledger_write_label_uses_label_world_and_identity() -> None:
    ledger = GovernedEvidenceLedger()
    label = _label(world=World.LIVE)
    receipt = _ok(ledger.write_label(label))
    assert receipt.namespace == LIVE_EVIDENCE_NAMESPACE
    # The content-addressed key is the label's own computation identity.
    assert receipt.fingerprint == label.computation_identity


def test_ledger_write_label_simulated_is_refused() -> None:
    assert is_refusal(GovernedEvidenceLedger().write_label(_label(world=World.SIMULATED)))


def test_ledger_write_label_rejects_non_label() -> None:
    assert is_refusal(GovernedEvidenceLedger().write_label({"not": "a-label"}))


# --- the two version ladders ------------------------------------------------


def test_contract_format_version_is_stamped_in_identity() -> None:
    assert CONTRACT_FORMAT_VERSION == 1
    assert _label().fp1_identity()["format_version"] == CONTRACT_FORMAT_VERSION


def test_package_semver_never_enters_identity() -> None:
    assert qmf.core.__version__.encode("utf-8") not in _bytes({"artifact": "x"})


def test_serializer_output_is_deterministic_json() -> None:
    body = _bytes({"z": 1, "a": {"n": 2}})
    assert body == json.dumps(
        {"a": {"n": 2}, "z": 1}, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    assert unicodedata.is_normalized("NFC", body.decode("utf-8"))
