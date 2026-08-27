"""Epic 1 — L2 contract conformance (E1-C01..C12): CT-01..CT-05 round-trip +
boundary suites, version-stamp, and isolated/consumer-surface conformance.

Authored from the CT-* contracts and DEC-0100/0102/0103. Source is read-only.
"""

from __future__ import annotations

import qmf.core as core
from qmf.core.chrono import (
    CONTRACT_FORMAT_VERSION as CT02_VERSION,
)
from qmf.core.chrono import (
    CalendarIdentity,
    CivilDate,
    Duration,
    Instant,
    Interval,
    MonotonicReading,
    TradingDate,
)
from qmf.core.exact import (
    CONTRACT_FORMAT_VERSION as CT01_VERSION,
)
from qmf.core.exact import (
    ExactRational,
    Money,
    Price,
    PriceDelta,
    Quantity,
    UnitKind,
    ValueFactor,
)
from qmf.core.fingerprint import (
    CONTRACT_FORMAT_VERSION as CT05_VERSION,
)
from qmf.core.fingerprint import (
    EvidenceClass,
    Fingerprint,
    ResultLabel,
    World,
    canonical_bytes,
    fingerprint,
)
from qmf.core.identity import Account, AccountRole, DatedRecord, Instrument, VenueId
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_ok, is_refusal


def _ok(result: object) -> object:
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def _instrument() -> Instrument:
    return _ok(Instrument.try_create(_ok(VenueId.try_create("VEN-1")), "EURUSD"))


def _fp(value: object) -> str:
    return _ok(fingerprint(value)).value


# E1-C01 — CT-01 round-trip ----------------------------------------------------
def test_e1_c01_ct01_scaled_integer_round_trip_semantic_equality() -> None:
    money = _ok(Money.try_create(150, "USD", 2))
    assert (money.value, money.currency, money.scale) == (150, "USD", 2)
    qty = _ok(Quantity.try_create(3, "lot", 0))
    assert (qty.value, qty.unit, qty.scale) == (3, "lot", 0)
    price = _ok(Price.try_create(110000, _instrument(), 5))
    assert (price.value, price.scale) == (110000, 5)
    # canonical encode is deterministic (same value -> same bytes across calls)
    assert _ok(canonical_bytes(money)) == _ok(canonical_bytes(money))


# E1-C02 — CT-01 boundary suite ------------------------------------------------
def test_e1_c02_ct01_boundary_suite() -> None:
    assert {m.value for m in UnitKind} >= {"money(currency)", "r-multiple", "instant"}
    # null / invalid unit-kind
    assert is_refusal(ExactRational.try_create(1, 2, None))
    assert is_refusal(ExactRational.try_create(1, 2, "bogus"))
    # scale range
    assert is_refusal(Money.try_create(1, "USD", -1))
    assert is_refusal(Money.try_create(1, "USD", 10**9))
    # nullability of required parts
    assert is_refusal(Money.try_create(None, "USD", 2))
    assert is_refusal(Money.try_create(1, None, 2))
    # malformed payload (float on money path)
    assert is_refusal(Money.try_create(1.0, "USD", 2))
    # zero denominator
    assert is_refusal(ExactRational.try_create(1, 0, UnitKind.COUNT))


# E1-C03 — CT-02 round-trip ----------------------------------------------------
def test_e1_c03_ct02_round_trip() -> None:
    assert _ok(Instant.try_create(123)).value_ns == 123
    assert _ok(Duration.try_create(-9)).value_ns == -9
    start, end = _ok(Instant.try_create(10)), _ok(Instant.try_create(20))
    iv = _ok(Interval.try_create(start, end))
    assert (iv.start.value_ns, iv.end.value_ns) == (10, 20)
    cal = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"))
    civ = _ok(CivilDate.try_create(2026, 1, 2))
    td = _ok(TradingDate.try_create(cal, civ))
    assert td.calendar == cal
    assert td.date_value == civ


# E1-C04 — CT-02 boundary suite ------------------------------------------------
def test_e1_c04_ct02_boundary_suite() -> None:
    int64_max = 2**63 - 1
    assert _ok(Instant.try_create(int64_max)).value_ns == int64_max
    assert is_refusal(Instant.try_create(int64_max + 1))  # range 1677-2262
    # in-band calendar identity on a trading date
    cal = _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025a"))
    civ = _ok(CivilDate.try_create(2026, 1, 2))
    td = _ok(TradingDate.try_create(cal, civ))
    assert td.calendar.rule_set == "forex-17NY"
    # wall/monotonic separation
    mono = _ok(MonotonicReading.try_create(5, "boot-1"))
    assert not isinstance(mono, Instant)
    # malformed
    assert is_refusal(Instant.try_create("not-an-int"))
    assert is_refusal(CivilDate.try_create(2026, 13, 40))


# E1-C05 — CT-03 round-trip ----------------------------------------------------
def test_e1_c05_ct03_round_trip() -> None:
    venue = _ok(VenueId.try_create("VEN-1"))
    instrument = _ok(Instrument.try_create(venue, "EUR/USD"))
    assert instrument.venue == venue
    assert instrument.symbol == "EUR/USD"
    record = _ok(DatedRecord.try_create(venue, "2026-01-02", {"asset_class": "forex"}))
    assert record.target == venue
    assert record.effective_date == "2026-01-02"
    assert record.content["asset_class"] == "forex"


# E1-C06 — CT-03 boundary suite ------------------------------------------------
def test_e1_c06_ct03_boundary_suite() -> None:
    assert {r.value for r in AccountRole} == {
        "live",
        "demo",
        "paper-validation",
        "paper-benched",
        "prop-firm",
    }
    venue = _ok(VenueId.try_create("VEN-1"))
    assert is_refusal(Account.try_create("ACC", venue, "not-a-role"))
    # symbol opacity: stored verbatim, never parsed/normalized
    assert _ok(Instrument.try_create(venue, "  spaced-inside  ")).symbol == "  spaced-inside  "
    # nullability
    assert is_refusal(Instrument.try_create(None, "EURUSD"))


# E1-C07 — CT-04 round-trip ----------------------------------------------------
def test_e1_c07_ct04_round_trip() -> None:
    built = _ok(
        TypedRefusal.try_create(
            RefusalCategory.STALE_EVIDENCE,
            Retryability.YES,
            context={"field": "evidence", "reason": "expired"},
        )
    )
    assert built.category is RefusalCategory.STALE_EVIDENCE
    assert built.retryability is Retryability.YES
    assert built.context["field"] == "evidence"


# E1-C08 — CT-04 boundary suite ------------------------------------------------
def test_e1_c08_ct04_boundary_suite() -> None:
    for category in RefusalCategory:
        assert is_ok(TypedRefusal.try_create(category, Retryability.NO))
    for retry in Retryability:
        if retry is Retryability.AFTER_CONDITION:
            assert is_ok(
                TypedRefusal.try_create(
                    RefusalCategory.TRANSIENT_VENUE_FAILURE, retry, after_condition_descriptor="ok"
                )
            )
        else:
            assert is_ok(TypedRefusal.try_create(RefusalCategory.INVALID_INPUT, retry))
    # after-condition presence rule (both arms)
    assert is_refusal(
        TypedRefusal.try_create(RefusalCategory.TRANSIENT_VENUE_FAILURE, Retryability.AFTER_CONDITION)
    )
    assert is_refusal(
        TypedRefusal.try_create(
            RefusalCategory.INVALID_INPUT, Retryability.NO, after_condition_descriptor="stray"
        )
    )
    # eighth category not representable
    assert is_refusal(TypedRefusal.try_create("eighth", Retryability.NO))


# E1-C09 — CT-05 round-trip ----------------------------------------------------
def test_e1_c09_ct05_round_trip() -> None:
    string = _fp({"k": "v"})
    fp = _ok(Fingerprint.try_create(string))
    assert fp.value == string
    assert fp.recipe == "fp1"
    assert fp.algorithm == "sha256"
    assert len(fp.digest) == 64
    time_range = _ok(Interval.try_create(_ok(Instant.try_create(0)), _ok(Instant.try_create(9))))
    label = _ok(
        ResultLabel.try_create(
            _fp({"p": 1}), 1, [_fp({"i": 1})], time_range, EvidenceClass.CONFIRMED, World.LIVE
        )
    )
    assert label.world is World.LIVE
    assert label.evidence_class is EvidenceClass.CONFIRMED


# E1-C10 — CT-05 boundary suite ------------------------------------------------
def test_e1_c10_ct05_boundary_suite() -> None:
    # recipe determinism
    assert _fp({"a": 1, "b": 2}) == _fp({"b": 2, "a": 1})
    # float refused, null omitted
    assert is_refusal(fingerprint({"x": 1.0}))
    assert is_refusal(fingerprint({"x": None}))
    # world enum closed set
    assert {w.value for w in World} == {"live", "replay", "simulated"}
    # collision split
    from qmf.core.fingerprint import WriteOutcome, reconcile_write

    fp = _ok(Fingerprint.try_create(_fp({"k": "v"})))
    assert _ok(reconcile_write(fp, b"x", b"x")) is WriteOutcome.IDEMPOTENT
    assert is_refusal(reconcile_write(fp, b"x", b"y"))


# E1-C11 — version-from-birth: format version 1 --------------------------------
def test_e1_c11_every_serialized_artifact_stamps_format_version_1() -> None:
    """DEC-0103: every serialized CT-01/02/05 identity artifact stamps integer format
    version = 1. (CT-03 core nouns carry their stamp via the qmf-registry record —
    Epic 2 — and when embedded in a CT-01/CT-05 artifact that stamps it.)"""
    assert CT01_VERSION == 1
    assert CT02_VERSION == 1
    assert CT05_VERSION == 1
    instrument = _instrument()
    artifacts = [
        _ok(Money.try_create(1, "USD", 2)),
        _ok(Price.try_create(1, instrument, 2)),
        _ok(Quantity.try_create(1, "lot", 0)),
        _ok(PriceDelta.try_create(1, instrument, 2)),
        _ok(ExactRational.try_create(1, 2, UnitKind.COUNT)),
        _ok(ValueFactor.try_create(1, 2, instrument, "USD")),
        _ok(Instant.try_create(0)),
        _ok(Duration.try_create(0)),
        _ok(Interval.try_create(_ok(Instant.try_create(0)), _ok(Instant.try_create(1)))),
        _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025a")),
    ]
    for artifact in artifacts:
        assert artifact.fp1_identity()["format_version"] == 1, artifact


# E1-C12 — consumer/owner surface (isolated per-package env proxy) -------------
def test_e1_c12_contract_surface_consumable_through_public_entrypoint() -> None:
    """DEC-0100/0102: the CT-01..CT-05 surface is consumable through the single public
    entrypoint qmf.core (owner + a consumer that imports only the public API, never a
    private internal). True isolated-env execution is the CI tier-2 concern; this
    proxies the consumer-stub half."""
    consumer_surface = {
        "Money",
        "Price",
        "Quantity",
        "Instant",
        "Duration",
        "Interval",
        "TradingDate",
        "Instrument",
        "VenueId",
        "Account",
        "TypedRefusal",
        "Fingerprint",
        "ResultLabel",
        "World",
        "fingerprint",
        "canonical_bytes",
    }
    for name in consumer_surface:
        assert name in core.__all__, f"{name} is not on the public consumer entrypoint"
        assert hasattr(core, name)
