"""Unit tests for the CT-10 value types (Story 3.2).

Covers the bitemporal :class:`SourceObservation` and its verbatim
:class:`ForeignTimestamp` / :class:`ForeignMoney` blocks: the identity computed by
qmf-core, the completeness law (FM-1), verbatim foreign evidence (AC2), the
``to_row`` / ``from_row`` round-trip with fp1 re-verification, and the
correction linkage (AC3).
"""

from __future__ import annotations

from qmf.core import (
    Fingerprint,
    Instant,
    MonotonicReading,
    RefusalCategory,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.data.observation import (
    CONTRACT_FORMAT_VERSION,
    ForeignMoney,
    ForeignTimestamp,
    SourceObservation,
)

_EVENT_NS = 1_700_000_000_000_000_000
_KNOWN_NS = 1_700_000_001_000_000_000
_RECEIVE_NS = 1_700_000_002_000_000_000


def _writer() -> WriterId:
    built = WriterId.try_create("node-a", "ingest", "dukascopy", "boot-1")
    assert is_ok(built)
    return built.value


def _observation(**overrides: object) -> SourceObservation:
    parts: dict[str, object] = {
        "event_time": _EVENT_NS,
        "known_at": _KNOWN_NS,
        "source": "dukascopy",
        "source_native_id": "EURUSD#42",
        "revision": "r1",
        "receive_wall_time": _RECEIVE_NS,
        "writer": _writer(),
        "sequence": 0,
        "world": World.LIVE,
    }
    parts.update(overrides)
    built = SourceObservation.try_create(**parts)  # type: ignore[arg-type]
    assert is_ok(built), built
    return built.value


# --- ForeignTimestamp -------------------------------------------------------


def test_foreign_timestamp_valid_and_identity() -> None:
    built = ForeignTimestamp.try_create("2026-08-21T12:00:00.123", "Europe/Zurich", "+02:00", "ms")
    assert is_ok(built)
    identity = built.value.fp1_identity()
    assert identity["verbatim"] == "2026-08-21T12:00:00.123"
    assert identity["zone"] == "Europe/Zurich"
    assert identity["offset"] == "+02:00"
    assert identity["resolution"] == "ms"
    assert identity["format_version"] == CONTRACT_FORMAT_VERSION


def test_foreign_timestamp_rejects_each_blank_field() -> None:
    for verbatim, zone, offset, resolution, field in [
        ("", "z", "o", "r", "foreign_timestamp.verbatim"),
        ("v", "  ", "o", "r", "foreign_timestamp.zone"),
        ("v", "z", "", "r", "foreign_timestamp.offset"),
        ("v", "z", "o", None, "foreign_timestamp.resolution"),
    ]:
        refused = ForeignTimestamp.try_create(verbatim, zone, offset, resolution)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.INVALID_INPUT
        assert refused.context["field"] == field


# --- ForeignMoney -----------------------------------------------------------


def test_foreign_money_valid_and_identity() -> None:
    built = ForeignMoney.try_create(110250, 5)
    assert is_ok(built)
    assert built.value.verbatim == 110250
    assert built.value.scale == 5
    assert built.value.fp1_identity()["verbatim"] == 110250


def test_foreign_money_accepts_zero_scale() -> None:
    built = ForeignMoney.try_create(-42, 0)
    assert is_ok(built)
    assert built.value.scale == 0


def test_foreign_money_rejects_float_and_bool_verbatim() -> None:
    for bad in (110250.0, True):
        refused = ForeignMoney.try_create(bad, 5)
        assert is_refusal(refused)
        assert refused.context["field"] == "foreign_money.verbatim"


def test_foreign_money_rejects_bad_scale() -> None:
    for bad in (-1, 2.0, True):
        refused = ForeignMoney.try_create(100, bad)
        assert is_refusal(refused)
        assert refused.context["field"] == "foreign_money.scale"


# --- SourceObservation identity + qmf-core ----------------------------------


def test_identity_is_computed_by_qmf_core() -> None:
    observation = _observation()
    assert isinstance(observation.fingerprint, Fingerprint)
    recomputed = fingerprint(observation.fp1_identity())
    assert is_ok(recomputed)
    assert recomputed.value.value == observation.fingerprint.value


def test_times_accept_int_or_instant_equivalently() -> None:
    from_int = _observation(event_time=_EVENT_NS)
    instant = Instant.try_create(_EVENT_NS)
    assert is_ok(instant)
    from_instant = _observation(event_time=instant.value)
    assert from_int.fingerprint.value == from_instant.fingerprint.value


def test_world_accepts_enum_or_string() -> None:
    assert (
        _observation(world="live").fingerprint.value
        == _observation(world=World.LIVE).fingerprint.value
    )


def test_is_correction_property() -> None:
    original = _observation()
    assert not original.is_correction
    correction = _observation(revision="r2", correction_of=original.fingerprint)
    assert correction.is_correction
    assert correction.fingerprint.value != original.fingerprint.value


def test_correction_of_accepts_fingerprint_string() -> None:
    original = _observation()
    correction = _observation(revision="r2", correction_of=original.fingerprint.value)
    assert correction.correction_of is not None
    assert correction.correction_of.value == original.fingerprint.value


def test_foreign_blocks_enter_identity_when_present() -> None:
    ts = ForeignTimestamp.try_create("t", "z", "o", "ms")
    money = ForeignMoney.try_create(1, 2)
    assert is_ok(ts)
    assert is_ok(money)
    bare = _observation()
    with_foreign = _observation(foreign_timestamp=ts.value, foreign_money=money.value)
    assert with_foreign.fingerprint.value != bare.fingerprint.value
    assert "foreign_timestamp" in with_foreign.fp1_identity()
    assert "foreign_money" in with_foreign.fp1_identity()


def test_diagnostic_is_excluded_from_identity_and_not_persisted() -> None:
    reading = MonotonicReading.try_create(999, "boot-1")
    assert is_ok(reading)
    bare = _observation()
    with_diag = _observation(receive_monotonic_diagnostic=reading.value)
    # Excluded from identity: same fingerprint.
    assert with_diag.fingerprint.value == bare.fingerprint.value
    assert with_diag.receive_monotonic_diagnostic is not None
    # Not persisted: the row omits it.
    assert "receive_monotonic_diagnostic" not in with_diag.to_row()


# --- SourceObservation completeness (FM-1) ----------------------------------


def test_missing_required_field_is_invalid_input() -> None:
    cases: list[tuple[dict[str, object], str]] = [
        ({"event_time": None}, "event_time"),
        ({"known_at": None}, "known_at"),
        ({"source": "  "}, "source"),
        ({"source_native_id": ""}, "source_native_id"),
        ({"revision": None}, "revision"),
        ({"receive_wall_time": "nope"}, "receive_wall_time"),
        ({"writer": "not-a-writer"}, "writer"),
        ({"sequence": -1}, "sequence"),
        ({"sequence": True}, "sequence"),
        ({"world": "elsewhere"}, "world"),
        ({"world": 123}, "world"),
    ]
    for override, field in cases:
        parts: dict[str, object] = {
            "event_time": _EVENT_NS,
            "known_at": _KNOWN_NS,
            "source": "dukascopy",
            "source_native_id": "EURUSD#42",
            "revision": "r1",
            "receive_wall_time": _RECEIVE_NS,
            "writer": _writer(),
            "sequence": 0,
            "world": World.LIVE,
        }
        parts.update(override)
        refused = SourceObservation.try_create(**parts)  # type: ignore[arg-type]
        assert is_refusal(refused), (field, refused)
        assert refused.category is RefusalCategory.INVALID_INPUT
        assert refused.context["field"] == field


def test_wrong_typed_optionals_are_refused() -> None:
    assert is_refusal(_try(foreign_timestamp="not-a-block"))
    assert is_refusal(_try(foreign_money="not-a-block"))
    # An Instant is the wrong type for the monotonic diagnostic (a MonotonicReading).
    assert is_refusal(_try(receive_monotonic_diagnostic=Instant(value_ns=1)))
    assert is_refusal(_try(correction_of="not-a-fingerprint"))


def _try(**overrides: object):  # type: ignore[no-untyped-def]
    parts: dict[str, object] = {
        "event_time": _EVENT_NS,
        "known_at": _KNOWN_NS,
        "source": "dukascopy",
        "source_native_id": "EURUSD#42",
        "revision": "r1",
        "receive_wall_time": _RECEIVE_NS,
        "writer": _writer(),
        "sequence": 0,
        "world": World.LIVE,
    }
    parts.update(overrides)
    return SourceObservation.try_create(**parts)  # type: ignore[arg-type]


# --- to_row / from_row round-trip -------------------------------------------


def test_row_round_trip_preserves_everything_and_reverifies_fp1() -> None:
    ts = ForeignTimestamp.try_create("t", "z", "o", "ms")
    money = ForeignMoney.try_create(110250, 5)
    assert is_ok(ts)
    assert is_ok(money)
    original = _observation()
    observation = _observation(
        revision="r2",
        foreign_timestamp=ts.value,
        foreign_money=money.value,
        correction_of=original.fingerprint,
    )
    row = observation.to_row()
    assert row["fingerprint"] == observation.fingerprint.value
    back = SourceObservation.from_row(row)
    assert is_ok(back)
    assert back.value.fingerprint.value == observation.fingerprint.value
    assert back.value.foreign_timestamp is not None
    assert back.value.foreign_timestamp.verbatim == "t"
    assert back.value.foreign_money is not None
    assert back.value.foreign_money.verbatim == 110250
    assert back.value.correction_of is not None
    assert back.value.correction_of.value == original.fingerprint.value


def test_from_row_rejects_non_mapping() -> None:
    refused = SourceObservation.from_row(["not", "a", "mapping"])
    assert is_refusal(refused)
    assert refused.context["field"] == "row"


def test_from_row_rejects_missing_fingerprint() -> None:
    row = _observation().to_row()
    del row["fingerprint"]
    refused = SourceObservation.from_row(row)
    assert is_refusal(refused)
    assert refused.context["field"] == "fingerprint"


def test_from_row_rejects_tampered_content() -> None:
    row = _observation().to_row()
    # Keep the recorded fingerprint but change the payload: the recomputed fp1 no longer
    # matches, so the corrupt row is refused, never read back as valid.
    row["revision"] = "tampered"
    refused = SourceObservation.from_row(row)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "fingerprint"
    assert "recomputed" in refused.context


def test_from_row_rejects_malformed_writer_submapping() -> None:
    row = _observation().to_row()
    row["writer"] = {"machine": "", "role": "r", "stream": "s", "boot_epoch_id": "b"}
    refused = SourceObservation.from_row(row)
    assert is_refusal(refused)
    assert refused.context["field"] == "writer"


def test_from_row_rejects_non_mapping_writer() -> None:
    row = _observation().to_row()
    row["writer"] = "flat-writer"
    refused = SourceObservation.from_row(row)
    assert is_refusal(refused)
    assert refused.context["field"] == "writer"


def test_from_row_rejects_non_mapping_foreign_blocks() -> None:
    row = _observation().to_row()
    row["foreign_timestamp"] = "flat"
    refused = SourceObservation.from_row(row)
    assert is_refusal(refused)
    assert refused.context["field"] == "foreign_timestamp"

    row2 = _observation().to_row()
    row2["foreign_money"] = "flat"
    refused2 = SourceObservation.from_row(row2)
    assert is_refusal(refused2)
    assert refused2.context["field"] == "foreign_money"


def test_from_row_rejects_malformed_foreign_money_values() -> None:
    row = _observation(foreign_money=ForeignMoney.try_create(1, 2).value).to_row()  # type: ignore[union-attr]
    row["foreign_money"] = {"verbatim": 1.5, "scale": 2}
    refused = SourceObservation.from_row(row)
    assert is_refusal(refused)
    assert refused.context["field"] == "foreign_money.verbatim"
