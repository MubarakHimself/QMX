"""Epic 18 · L1 — targeted properties and clock regression.

T18-P1  injected-clock reproducibility            (RQ-CLOCK / FIND-001) — EXPECTED FAIL
T18-P2  download idempotence                       (RQ8)     hypothesis
T18-P3  provider money-path exact-integer crossing (RQ6/RQ23) hypothesis
T18-P4  licence-gate totality / fail-closed        (RQ14)    hypothesis
T18-P5  verify determinism                         (RQ27)
T18-P6  gap-check determinism + calendar version   (RQ31)
"""

from __future__ import annotations

import tempfile
from datetime import datetime, timezone
from pathlib import Path

from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from qmf.core.refusal import Ok, TypedRefusal, is_ok, is_refusal
from qmf.data.dukascopy import LicenseTag

from _e18 import (
    NS,
    ControlledCalendar,
    FakeAdapter,
    calendar_identity,
    download_resources,
    instrument,
    ok,
    provider_record,
    raw_observation_fingerprints,
    scan_raw_observations,
    store_at,
)

from qmb.data.convert import CONVERSION_BOUNDARY, provider_price_to_exact
from qmb.data.download import download, parse_download_request, resolve_end_ns
from qmb.data.gap_check import gap_check
from qmb.data.licensing import (
    AuthorityKind,
    SourceWindowRef,
    VenueLicensePolicy,
    admit_governed_evidence,
)
from qmb.data.verify import verify


# =============================================================================
# T18-P1 — FIND-001: the reproducible-window (18.1 AC2) requires an injected clock
# =============================================================================
def _next_midnight_ns(clock: datetime) -> int:
    from datetime import timedelta

    tomorrow = datetime(clock.year, clock.month, clock.day, tzinfo=timezone.utc) + timedelta(days=1)
    return int(tomorrow.timestamp() * 1_000_000_000)


def test_t18_p1_resolve_end_can_honor_injected_clock() -> None:
    """Falsifiability anchor: the frontier helper CAN take an injected clock —
    so the requirement is satisfiable and the wiring test below is a real defect,
    not an impossible ask."""
    fixed = datetime(2021, 1, 1, tzinfo=timezone.utc)
    got = resolve_end_ns(None, now=fixed)
    assert is_ok(got)
    assert got.value == _next_midnight_ns(fixed)


def test_t18_p1_download_threads_injected_clock_FIND001() -> None:
    """``data download`` must derive ``end``-defaults-to-today from an injected
    clock so the window is reproducible (18.1 AC2, FR-002/AR-16, DEC-0106).

    FC-14 selects the ``now`` key because no ratified authority names the
    injection key; the other guessed keys from the original finding are removed.
    """
    fixed = datetime(2024, 1, 1, tzinfo=timezone.utc)
    expected = _next_midnight_ns(fixed)
    resources = {
        "venue": "dukascopy",
        "symbol": "EURUSD",
        "start_ns": NS,
        "destination": "rooms",
        "now": fixed,
    }
    parsed = parse_download_request(resources)
    assert is_ok(parsed), parsed
    assert parsed.value.end_ns == expected, (
        "end-defaults-to-today did not derive from the injected clock — the window "
        "is non-reproducible (FIND-001: ambient datetime.now() at download.py:127)"
    )


# =============================================================================
# T18-P2 — idempotence: a second identical download writes zero duplicates (RQ8)
# =============================================================================
@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    count=st.integers(min_value=1, max_value=6),
    revision=st.sampled_from(["r1", "rev-A", "2024-01"]),
)
def test_t18_p2_download_idempotent(count: int, revision: str) -> None:
    with tempfile.TemporaryDirectory() as d:
        dest = Path(d) / "rooms"
        records = tuple(
            provider_record(f"EURUSD#{NS + i}", NS + i, revision=revision) for i in range(count)
        )
        res1 = download(
            download_resources(dest, revision=revision),
            adapter=FakeAdapter(records),
            store=store_at(dest),
        )
        assert is_ok(res1), res1
        fps1 = raw_observation_fingerprints(store_at(dest))
        assert len(fps1) == count

        # Second identical run over the overlapping window.
        res2 = download(
            download_resources(dest, revision=revision),
            adapter=FakeAdapter(records),
            store=store_at(dest),
        )
        assert is_ok(res2), res2
        fps2 = raw_observation_fingerprints(store_at(dest))
        # Observed through the store: no duplicate CT-10 observation was written.
        assert fps2 == fps1, "second identical download duplicated CT-10 observations (RQ8)"


# =============================================================================
# T18-P3 — money-path: provider price crosses the named AD-22 boundary as an
#          EXACT scaled integer; a non-numeric price is refused (RQ6/RQ23)
# =============================================================================
@given(verbatim=st.integers(min_value=-10_000_000, max_value=10_000_000), scale=st.integers(0, 9))
def test_t18_p3_int_price_passes_through_exact(verbatim: int, scale: int) -> None:
    got = provider_price_to_exact(verbatim, instrument=instrument(), scale=scale)
    assert is_ok(got)
    money = got.value
    assert isinstance(money.verbatim, int) and not isinstance(money.verbatim, bool)
    assert money.verbatim == verbatim and money.scale == scale


@given(
    value=st.floats(min_value=0.00001, max_value=100000.0, allow_nan=False, allow_infinity=False),
    scale=st.integers(0, 6),
)
def test_t18_p3_float_price_crosses_as_exact_integer(value: float, scale: int) -> None:
    got = provider_price_to_exact(value, instrument=instrument(), scale=scale)
    if is_refusal(got):
        # A refusal is acceptable (out-of-range), but never a silent float leak.
        return
    money = got.value
    assert isinstance(money.verbatim, int) and not isinstance(money.verbatim, bool)
    assert isinstance(money.scale, int)


@given(bad=st.text(min_size=1).filter(lambda s: not s.strip().lstrip("-").isdigit()))
def test_t18_p3_non_numeric_price_refused(bad: str) -> None:
    got = provider_price_to_exact(bad, instrument=instrument(), scale=5)
    assert is_refusal(got), f"a non-numeric provider price must be refused, got {got!r}"
    assert got.context.get("boundary") == CONVERSION_BOUNDARY


# =============================================================================
# T18-P4 — licence-gate totality: total function to pass/refuse; blank ⇒ unknown
#          ⇒ block; grant tags pass only with a matching policy (RQ14)
# =============================================================================
_GRANTING = {LicenseTag.INTERNAL_ONLY, LicenseTag.REDISTRIBUTION_OK}


@settings(max_examples=60, deadline=None)
@given(
    tag=st.sampled_from([t.value for t in LicenseTag] + ["", "junk", "  ", "Redistribution-OK"]),
    supply_policy=st.booleans(),
)
def test_t18_p4_license_gate_is_total_and_fails_closed(tag: str, supply_policy: bool) -> None:
    from qmb.data.licensing import resolve_license_tag

    resolved = resolve_license_tag(tag if tag != "" else None)
    policies = None
    if supply_policy:
        policies = {
            "dukascopy-fx": VenueLicensePolicy(
                "dukascopy-fx", resolved, "AUTH", AuthorityKind.OPERATOR_RULING
            )
        }
    window = SourceWindowRef("dukascopy-fx", "EURUSD", NS, NS + 10, license_tag=tag or None)
    result = admit_governed_evidence(window, policies=policies)
    # Totality: always exactly one of the two Result arms — never a raise.
    assert isinstance(result, (Ok, TypedRefusal))
    if resolved in _GRANTING and supply_policy:
        assert is_ok(result), f"a granting tag with its policy must pass, got {result!r}"
    else:
        # denied / unknown / blank / junk, or a granting tag without authority:
        assert is_refusal(result), f"non-granting / unauthorised must fail closed, got {result!r}"
        assert result.category.value == "policy rejection"
    # No adapter-inferred grant: a blank never resolves to a granting tag.
    assert resolve_license_tag(None) is LicenseTag.UNKNOWN


# =============================================================================
# T18-P5 — verify determinism: same immutable window ⇒ same verdict (RQ27)
# =============================================================================
def _verify_ticks() -> list[dict[str, object]]:
    return [{"t_ns": NS + i, "bid": 110_000 + i, "ask": 110_020 + i} for i in range(5)]


def _verdict_core(mapping: dict[str, object]) -> dict[str, object]:
    # The data-quality verdict, excluding the journal stream POSITION (which is a
    # storage cursor, not part of the reproducible verdict).
    return {k: v for k, v in mapping.items() if k not in {"journal_sequence"}}


def test_t18_p5_verify_reproduces_verdict() -> None:
    with tempfile.TemporaryDirectory() as d1, tempfile.TemporaryDirectory() as d2:
        base = {
            "archive": "a",
            "venue": "dukascopy",
            "symbol": "EURUSD",
            "start_ns": NS,
            "end_ns": NS + 100,
            "side": "both",
            "ticks": _verify_ticks(),
            "world": "replay",
            "correlation_id": "corr-1",
        }
        r1 = verify({**base, "archive": d1}, store=store_at(Path(d1)))
        r2 = verify({**base, "archive": d2}, store=store_at(Path(d2)))
        assert is_ok(r1) and is_ok(r2), (r1, r2)
        assert _verdict_core(r1.value.as_mapping()) == _verdict_core(r2.value.as_mapping())
        assert r1.value.verdict == "pass"


# =============================================================================
# T18-P6 — gap-check determinism + recorded calendar version (RQ31)
# =============================================================================
def test_t18_p6_gap_check_deterministic_and_records_version() -> None:
    identity = calendar_identity(version="v7")
    cal = ControlledCalendar(identity=identity, open_spans=((NS, NS + 10),))
    rows = [{"t_ns": NS}, {"t_ns": NS + 3}, {"t_ns": NS + 7}]
    req = {
        "archive": "a",
        "venue": "dukascopy",
        "symbol": "EURUSD",
        "start_ns": NS,
        "end_ns": NS + 10,
        "side": "both",
        "bar_step_ns": 1,
        "rows": rows,
        "world": "replay",
    }
    with tempfile.TemporaryDirectory() as d:
        r1 = gap_check({**req, "archive": d}, store=store_at(Path(d)), calendar=cal)
        r2 = gap_check({**req, "archive": d}, store=store_at(Path(d)), calendar=cal)
    assert is_ok(r1) and is_ok(r2), (r1, r2)
    assert r1.value.as_mapping()["gaps"] == r2.value.as_mapping()["gaps"]
    assert r1.value.calendar["rule_set_version"] == "v7"
