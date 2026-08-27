"""Epic 1 — L1 property / invariant tests (hypothesis): R-001 & R-002 (E1-P01..P05).

Run with a declared (derandomized) seed and the injected clock only. No generated
result validates trading edge (DEC-0054). Authorities: CT-01 FM-4 & DEC-0154
(R-001), CT-04 & DEC-0109 (R-002), CT-05 & DEC-0108/0158. Source is read-only.

Requires hypothesis: run with `uv run --with hypothesis pytest ...`.
"""

from __future__ import annotations

from fractions import Fraction

from hypothesis import given, settings
from hypothesis import strategies as st
from qmf.core.chrono import (
    CalendarIdentity,
    CivilDate,
    Duration,
    Instant,
    Interval,
    MonotonicReading,
    OrderingKey,
    SessionWindow,
    TradingDate,
    WriterId,
    compare_causal,
    render_utc_iso8601,
    verify_tzdb_pin,
)
from qmf.core.exact import (
    MAX_SCALE,
    ExactRational,
    Money,
    Price,
    PriceDelta,
    Quantity,
    UnitKind,
    ValueFactor,
)
from qmf.core.fingerprint import (
    Fingerprint,
    ResultLabel,
    canonical_bytes,
    fingerprint,
    governed_namespace,
    reconcile_write,
)
from qmf.core.identity import Account, DatedRecord, Instrument, Venue, VenueId
from qmf.core.refusal import Ok, RefusalCategory, TypedRefusal, is_ok, is_refusal
from qmf.core.secret import SecretRef, SecretValue

SEVEN_CATEGORIES = {c for c in RefusalCategory}


def _ok(result: object) -> object:
    assert is_ok(result), f"expected Ok, got {result!r}"
    return result.value


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return _ok(Instrument.try_create(_ok(VenueId.try_create("VEN-1")), symbol))


# junk of correct arity — any Python object; try_create params are typed `object`,
# so a domain-invalid value must RETURN a refusal, never raise (R-002).
_JUNK = st.one_of(
    st.none(),
    st.booleans(),
    st.integers(),
    st.integers(min_value=-(2**80), max_value=2**80),
    st.floats(allow_nan=True, allow_infinity=True),
    st.text(max_size=8),
    st.lists(st.integers(), max_size=3),
    st.dictionaries(st.text(max_size=3), st.integers(), max_size=3),
)


# E1-P01 — R-001: mixed-tag arithmetic ALWAYS refuses --------------------------
@settings(derandomize=True, deadline=None, max_examples=150)
@given(
    cur_a=st.text(min_size=1, max_size=4).filter(lambda s: s.strip() != ""),
    cur_b=st.text(min_size=1, max_size=4).filter(lambda s: s.strip() != ""),
    v1=st.integers(min_value=-10_000, max_value=10_000),
    v2=st.integers(min_value=-10_000, max_value=10_000),
    scale=st.integers(min_value=0, max_value=6),
)
def test_e1_p01_mixed_tag_arithmetic_always_refuses(
    cur_a: str, cur_b: str, v1: int, v2: int, scale: int
) -> None:
    """R-001 (CT-01 FM-4, DEC-0154): mixed unit-kind/currency/unit/instrument
    arithmetic ALWAYS refuses — never a silent cross-tag coercion, rescale, or round;
    the refusal category is always from the CT-04 vocabulary (never a raise)."""
    m_a = _ok(Money.try_create(v1, cur_a, scale))
    m_b = _ok(Money.try_create(v2, cur_b, scale))
    if cur_a != cur_b:
        for result in (m_a.add(m_b), m_a.subtract(m_b)):
            assert is_refusal(result)
            assert result.category in SEVEN_CATEGORIES

    # Cross-type operands always refuse.
    q = _ok(Quantity.try_create(v2, "lot", scale))
    assert is_refusal(m_a.add(q))
    assert is_refusal(m_a.add(v2))  # bare int is not a Money

    # A Price adds only a PriceDelta (a vector), never another Price.
    instr = _instrument()
    p1 = _ok(Price.try_create(v1, instr, scale))
    p2 = _ok(Price.try_create(v2, instr, scale))
    assert is_refusal(p1.add(p2))

    # Differently-instrumented delta never combines.
    d_here = _ok(PriceDelta.try_create(v1, instr, scale))
    d_other = _ok(PriceDelta.try_create(v2, _instrument("GBPUSD"), scale))
    assert is_refusal(d_here.add(d_other))
    assert is_refusal(d_here.subtract(d_other))


# E1-P02 — R-001 companion: mixed-scale = promote-or-refuse --------------------
@settings(derandomize=True, deadline=None, max_examples=200)
@given(
    v1=st.integers(min_value=-10_000, max_value=10_000),
    v2=st.integers(min_value=-10_000, max_value=10_000),
    s1=st.integers(min_value=0, max_value=12),
    s2=st.integers(min_value=0, max_value=12),
)
def test_e1_p02_mixed_scale_same_currency_is_exact_never_silent_round(
    v1: int, v2: int, s1: int, s2: int
) -> None:
    """R-001 companion (CT-01 FM-4): same-currency mixed-scale addition auto-promotes
    to the finer scale and the result is the mathematically EXACT sum — there is no
    silent rounding path (the result rational equals the exact operand sum)."""
    a = _ok(Money.try_create(v1, "USD", s1))
    b = _ok(Money.try_create(v2, "USD", s2))
    total = a.add(b)
    assert is_ok(total)
    assert total.value.scale == max(s1, s2)
    assert total.value.as_fraction() == a.as_fraction() + b.as_fraction()
    # subtraction likewise exact
    diff = a.subtract(b)
    assert is_ok(diff)
    assert diff.value.as_fraction() == a.as_fraction() - b.as_fraction()


# E1-P03 — R-002: no public callable raises across the boundary ----------------
@settings(derandomize=True, deadline=None, max_examples=250)
@given(data=st.data())
def test_e1_p03_no_public_callable_raises_across_boundary(data: st.DataObject) -> None:
    """R-002 (CT-04, DEC-0109): every public qmf.core callable, driven with valid AND
    invalid domain inputs at the correct arity, returns a value or a TypedRefusal — it
    never raises across the boundary (exceptions are reserved for programmer error,
    which correct-arity/`object`-typed params exclude)."""
    callables: list[tuple[str, object, int]] = [
        ("TypedRefusal.try_create", TypedRefusal.try_create, 2),
        ("VenueId.try_create", VenueId.try_create, 1),
        ("Instrument.try_create", Instrument.try_create, 2),
        ("Venue.try_create", Venue.try_create, 1),
        ("Account.try_create", Account.try_create, 3),
        ("DatedRecord.try_create", DatedRecord.try_create, 3),
        ("Money.try_create", Money.try_create, 3),
        ("Price.try_create", Price.try_create, 3),
        ("Quantity.try_create", Quantity.try_create, 3),
        ("PriceDelta.try_create", PriceDelta.try_create, 3),
        ("ExactRational.try_create", ExactRational.try_create, 3),
        ("ValueFactor.try_create", ValueFactor.try_create, 4),
        ("Instant.try_create", Instant.try_create, 1),
        ("Duration.try_create", Duration.try_create, 1),
        ("Interval.try_create", Interval.try_create, 2),
        ("CivilDate.try_create", CivilDate.try_create, 3),
        ("CalendarIdentity.try_create", CalendarIdentity.try_create, 3),
        ("TradingDate.try_create", TradingDate.try_create, 2),
        ("MonotonicReading.try_create", MonotonicReading.try_create, 2),
        ("WriterId.try_create", WriterId.try_create, 4),
        ("OrderingKey.try_create", OrderingKey.try_create, 3),
        ("SessionWindow.try_create", SessionWindow.try_create, 3),
        ("Fingerprint.try_create", Fingerprint.try_create, 1),
        ("ResultLabel.try_create", ResultLabel.try_create, 6),
        ("SecretRef.try_create", SecretRef.try_create, 1),
        ("SecretValue.try_create", SecretValue.try_create, 2),
        ("compare_causal", compare_causal, 2),
        ("verify_tzdb_pin", verify_tzdb_pin, 2),
        ("render_utc_iso8601", render_utc_iso8601, 1),
        ("fingerprint", fingerprint, 1),
        ("canonical_bytes", canonical_bytes, 1),
        ("governed_namespace", governed_namespace, 1),
        ("reconcile_write", reconcile_write, 3),
    ]
    for name, fn, arity in callables:
        args = [data.draw(_JUNK) for _ in range(arity)]
        try:
            result = fn(*args)
        except Exception as exc:  # noqa: BLE001 - any raise is the finding
            raise AssertionError(
                f"{name} raised {type(exc).__name__} across the boundary "
                f"for domain-invalid input {args!r}: {exc}"
            ) from exc
        assert isinstance(result, (Ok, TypedRefusal)), (
            f"{name} returned a non-Result {type(result).__name__} for {args!r}"
        )


# E1-P04 — float in identity content always refuses ----------------------------
@settings(derandomize=True, deadline=None, max_examples=150)
@given(
    f=st.floats(allow_nan=True, allow_infinity=True),
    key=st.text(min_size=1, max_size=5).filter(lambda s: s.strip() != ""),
    i=st.integers(),
)
def test_e1_p04_float_in_identity_always_refuses(f: float, key: str, i: int) -> None:
    """CT-05 / DEC-0108: a float injected anywhere in identity content makes
    fingerprinting refuse; no path hashes float bytes."""
    assert is_refusal(fingerprint({key: f}))
    assert is_refusal(fingerprint([i, f]))
    assert is_refusal(fingerprint({key: {"nested": [i, f]}}))
    assert is_refusal(canonical_bytes({key: f}))


# E1-P05 — fp1 canonical-form equality -----------------------------------------
@settings(derandomize=True, deadline=None, max_examples=200)
@given(
    n=st.integers(min_value=-10_000, max_value=10_000),
    d=st.integers(min_value=1, max_value=10_000),
    k=st.integers(min_value=1, max_value=50),
    v=st.integers(min_value=-10_000, max_value=10_000),
    s=st.integers(min_value=0, max_value=10),
    extra=st.integers(min_value=0, max_value=10),
)
def test_e1_p05_fp1_canonical_form_equality(
    n: int, d: int, k: int, v: int, s: int, extra: int
) -> None:
    """CT-01 canonical form / CT-05 / DEC-0158: semantically equal values produce the
    SAME fp1 by construction — 6/4 vs 3/2 (common factor), and one amount stored at two
    scales."""
    assert s + extra <= MAX_SCALE
    # rationals differing only by a common factor share a fingerprint
    r1 = _ok(ExactRational.try_create(n, d, UnitKind.DIMENSIONLESS_RATIO))
    r2 = _ok(ExactRational.try_create(n * k, d * k, UnitKind.DIMENSIONLESS_RATIO))
    assert _ok(fingerprint(r1)).value == _ok(fingerprint(r2)).value

    # one money amount stored at two scales shares a fingerprint
    m1 = _ok(Money.try_create(v, "USD", s))
    m2 = _ok(Money.try_create(v * (10**extra), "USD", s + extra))
    assert m1.as_fraction() == m2.as_fraction()  # same value
    assert _ok(fingerprint(m1)).value == _ok(fingerprint(m2)).value
