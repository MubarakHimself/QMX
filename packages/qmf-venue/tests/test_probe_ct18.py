"""Story 8.1 tests — the cTrader capability probe and its venue-observation profile.

Fixture-driven throughout: the transport is a canned :class:`ProbeTransport` that
contacts no host, and time is the pure ``DataDrivenClock``. These pin every
acceptance criterion — the five verify-or-refuse checks recording measured facts and
verdicts into a per-(VenueId, account) profile; the daily boundary and trendbar basis
measured per broker and never hardcoded; unverified/refused checks leaving their
evidence class unavailable rather than defaulting; credentials appearing only by
reference id with no host contacted and no order submitted; and a findings note
surfacing contradictions with upstream assumptions (FR-022, FR-025, FR-026, SC-02,
AR-45, AR-46; DEC-0135, DEC-0136, DEC-0138).
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import (
    Account,
    AccountRole,
    CalendarIdentity,
    DataDrivenClock,
    ExactRational,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    SecretValue,
    TypedRefusal,
    UnitKind,
    VenueId,
    is_ok,
    is_refusal,
)
from qmf.venue import (
    CapabilityProbe,
    MeasuredFact,
    ProbeCheck,
    ProbeReport,
    ProbeTransport,
    ProbeVerdict,
    UpstreamAssumption,
    VenueEvidenceClass,
    VenueObservationProfile,
)
from qmf.venue.observation import evidence_class_for
from qmf.venue.probe import (
    AccountMoneyRecord,
    SpotSample,
    SymbolMetadataRecord,
    Tick,
    TickHistorySample,
    Trendbar,
    TrendbarSample,
)

T = TypeVar("T")

# A recent-era wall reading: ~1.724e18 ns is well inside the int64 instant range, and
# its millisecond form ~1.724e12 is the magnitude band the spot assertion tests.
_WALL_NS = 1_724_000_000 * 1_000_000_000
_WALL_MS = _WALL_NS // 1_000_000
_PROTO_TAG = 91
_BOOT_EPOCH = "boot-epoch-A"
_SESSION_EPOCH = "session-epoch-1"
_CRED_REF_ID = "sref-71a4c9e2d8b305"


def _ok(result: Result[T]) -> T:
    assert is_ok(result)
    return result.value


def _venue() -> VenueId:
    return _ok(VenueId.try_create("venue-ctrader-demo"))


def _account(venue: VenueId | None = None) -> Account:
    anchor = venue if venue is not None else _venue()
    return _ok(Account.try_create("acct-001", anchor, AccountRole.DEMO))


def _secret_ref() -> SecretRef:
    return _ok(SecretRef.try_create(_CRED_REF_ID))


def _instant(value_ns: int) -> Instant:
    return _ok(Instant.try_create(value_ns))


def _clock(*, wall_ns: int = _WALL_NS, boot: str = _BOOT_EPOCH) -> DataDrivenClock:
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=[_instant(wall_ns)], monotonic_ns=[])


def _pip_size(num: int, den: int) -> ExactRational:
    return _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))


# A D1 boundary at UTC minute-of-day 0 — deliberately NOT the demoted 17:00-New-York
# claim, proving the boundary is measured from the data, never hardcoded.
_DAY1_ANCHOR = 28_800_000  # minutes since epoch; 28_800_000 % 1440 == 0
_DAY2_ANCHOR = _DAY1_ANCHOR + 1440  # next day, same UTC minute-of-day


def _green_trendbars() -> TrendbarSample:
    # bar1 reconciles against the ticks below; bar2 shares the same UTC minute-of-day.
    bar1 = Trendbar(
        utc_timestamp_in_minutes=_DAY1_ANCHOR,
        open_wire=100_000,
        high_wire=130_000,
        low_wire=90_000,
        close_wire=110_000,
    )
    bar2 = Trendbar(
        utc_timestamp_in_minutes=_DAY2_ANCHOR,
        open_wire=111_000,
        high_wire=140_000,
        low_wire=95_000,
        close_wire=120_000,
    )
    return TrendbarSample(bars=(bar1, bar2), received_at=_instant(_WALL_NS + 1))


def _green_ticks() -> TickHistorySample:
    ticks = (
        Tick(utc_timestamp_in_minutes=_DAY1_ANCHOR + 1, price_wire=100_000),
        Tick(utc_timestamp_in_minutes=_DAY1_ANCHOR + 2, price_wire=130_000),
        Tick(utc_timestamp_in_minutes=_DAY1_ANCHOR + 3, price_wire=90_000),
        Tick(utc_timestamp_in_minutes=_DAY1_ANCHOR + 4, price_wire=110_000),
    )
    return TickHistorySample(quote_type="bid", ticks=ticks, received_at=_instant(_WALL_NS + 2))


def _green_spot() -> SpotSample:
    return SpotSample(
        raw_timestamps=(_WALL_MS + 123, _WALL_MS + 456),
        received_at=_instant(_WALL_NS + 3),
    )


def _green_symbol() -> SymbolMetadataRecord:
    return SymbolMetadataRecord(
        symbol="EURUSD",
        digits=5,
        pip_position=4,
        declared_pip_size=_pip_size(1, 10_000),
        received_at=_instant(_WALL_NS + 4),
    )


def _green_money() -> AccountMoneyRecord:
    return AccountMoneyRecord(money_digits=2, received_at=_instant(_WALL_NS + 5))


class _FixtureTransport:
    """A canned :class:`ProbeTransport` that contacts no host and records its calls.

    Each fetch returns a pre-wired ``Result``; the call log proves the probe only ever
    reads (fetches) and never submits.
    """

    def __init__(
        self,
        *,
        proto_release_tag: int = _PROTO_TAG,
        spot: Result[SpotSample] | None = None,
        trendbars: Result[TrendbarSample] | None = None,
        ticks: Result[TickHistorySample] | None = None,
        symbol: Result[SymbolMetadataRecord] | None = None,
        money: Result[AccountMoneyRecord] | None = None,
    ) -> None:
        self._proto = proto_release_tag
        self._spot: Result[SpotSample] = spot if spot is not None else Ok(_green_spot())
        self._trendbars: Result[TrendbarSample] = (
            trendbars if trendbars is not None else Ok(_green_trendbars())
        )
        self._ticks: Result[TickHistorySample] = ticks if ticks is not None else Ok(_green_ticks())
        self._symbol: Result[SymbolMetadataRecord] = (
            symbol if symbol is not None else Ok(_green_symbol())
        )
        self._money: Result[AccountMoneyRecord] = money if money is not None else Ok(_green_money())
        self.calls: list[str] = []

    @property
    def proto_release_tag(self) -> int:
        return self._proto

    def fetch_spot_sample(self) -> Result[SpotSample]:
        self.calls.append("fetch_spot_sample")
        return self._spot

    def fetch_trendbar_sample(self) -> Result[TrendbarSample]:
        self.calls.append("fetch_trendbar_sample")
        return self._trendbars

    def fetch_tick_history_sample(self) -> Result[TickHistorySample]:
        self.calls.append("fetch_tick_history_sample")
        return self._ticks

    def fetch_symbol_metadata(self) -> Result[SymbolMetadataRecord]:
        self.calls.append("fetch_symbol_metadata")
        return self._symbol

    def fetch_account_money_record(self) -> Result[AccountMoneyRecord]:
        self.calls.append("fetch_account_money_record")
        return self._money


def _refusal(category: RefusalCategory) -> TypedRefusal:
    """A bare typed refusal standing in for an unavailable transport fetch."""
    return TypedRefusal(category=category, retryability=Retryability.NO)


def _probe(
    transport: ProbeTransport | None = None,
    *,
    clock: DataDrivenClock | None = None,
    assumptions: tuple[UpstreamAssumption, ...] = (),
) -> CapabilityProbe:
    return _ok(
        CapabilityProbe.try_create(
            clock if clock is not None else _clock(),
            transport if transport is not None else _FixtureTransport(),
            _venue(),
            _account(),
            _secret_ref(),
            _PROTO_TAG,
            _SESSION_EPOCH,
            assumptions,
        )
    )


# --- the happy-path run -----------------------------------------------------


def test_run_records_all_five_checks_verified() -> None:
    report = _ok(_probe().run())
    assert isinstance(report, ProbeReport)
    assert report.proto_release_tag == _PROTO_TAG
    verdicts = {fact.check: fact.verdict for fact in report.profile.facts}
    assert verdicts == {
        ProbeCheck.SPOT_TIMESTAMP_UNIT: ProbeVerdict.VERIFIED,
        ProbeCheck.DAILY_BOUNDARY: ProbeVerdict.VERIFIED,
        ProbeCheck.BAR_BASIS: ProbeVerdict.VERIFIED,
        ProbeCheck.PIP_FORMULA: ProbeVerdict.VERIFIED,
        ProbeCheck.MONEY_EXPONENT: ProbeVerdict.VERIFIED,
    }


def test_run_profile_is_keyed_per_venue_and_account() -> None:
    report = _ok(_probe().run())
    assert report.profile.venue_id == _venue()
    assert report.profile.account == _account()


def test_verified_checks_make_every_evidence_class_available() -> None:
    profile = _ok(_probe().run()).profile
    for evidence_class in VenueEvidenceClass:
        assert _ok(profile.require_evidence(evidence_class)) is True


def test_each_fact_records_a_receive_instant_and_session_epoch() -> None:
    # Receive-time recording is mandatory (no server clock), and the session epoch is
    # distinct from the boot epoch (DEC-0135, DEC-0137).
    for fact in _ok(_probe().run()).profile.facts:
        assert isinstance(fact.received_at, Instant)
        assert fact.session_epoch == _SESSION_EPOCH
        assert fact.session_epoch != _BOOT_EPOCH


def test_daily_boundary_is_measured_not_the_hardcoded_ny_claim() -> None:
    fact = _ok(_probe().run()).profile.latest_for(ProbeCheck.DAILY_BOUNDARY)
    assert fact is not None
    assert fact.verdict is ProbeVerdict.VERIFIED
    assert fact.measured["utc_minute_of_day"] == 0  # measured from data, not 17:00 NY


def test_bar_basis_records_the_declared_quote_side_not_hardcoded_bid() -> None:
    fact = _ok(_probe().run()).profile.latest_for(ProbeCheck.BAR_BASIS)
    assert fact is not None
    assert fact.verdict is ProbeVerdict.VERIFIED
    # The verified basis is whatever quote side the tick sample declared.
    assert fact.measured["quote_type"] == "bid"
    assert fact.measured["reconciled_bars"] == 1


def test_pip_formula_records_the_validated_exact_pip_size() -> None:
    fact = _ok(_probe().run()).profile.latest_for(ProbeCheck.PIP_FORMULA)
    assert fact is not None
    assert fact.verdict is ProbeVerdict.VERIFIED
    assert fact.measured["pip_position"] == 4
    assert fact.measured["pip_size_num"] == 1
    assert fact.measured["pip_size_den"] == 10_000


def test_money_exponent_records_the_present_exponent() -> None:
    fact = _ok(_probe().run()).profile.latest_for(ProbeCheck.MONEY_EXPONENT)
    assert fact is not None
    assert fact.measured["money_digits"] == 2


# --- standing alone, credentials, no submission -----------------------------


def test_probe_holds_a_reference_never_a_value() -> None:
    probe = _probe()
    assert isinstance(probe.credential_ref, SecretRef)
    assert not isinstance(probe.credential_ref, SecretValue)


def test_facts_carry_only_the_credential_reference_id() -> None:
    for fact in _ok(_probe().run()).profile.facts:
        assert fact.credential_ref_id == _CRED_REF_ID


def test_transport_is_read_only_no_submit_path_exists() -> None:
    transport = _FixtureTransport()
    probe = _probe(transport)
    _ok(probe.run())
    assert transport.calls  # the probe measured
    assert all(name.startswith("fetch_") for name in transport.calls)
    # No submit/order surface exists on either the seam or the probe.
    assert not hasattr(ProbeTransport, "submit")
    assert not hasattr(CapabilityProbe, "place_order")
    assert not hasattr(CapabilityProbe, "submit")


def test_probe_needs_no_port_contract_or_journal_to_run() -> None:
    # It runs with only qmf-core nouns, a clock, and the throwaway transport (AR-45).
    report = _ok(_probe().run())
    assert len(report.profile.facts) == 5


def test_run_propagates_an_unavailable_refusal_when_the_clock_is_spent() -> None:
    # OR-03 / CT-04 (DEC-0109): run() reads the injected clock once for its anchor
    # instant. When the replay clock is spent (an under-provisioned script), wall_now()
    # returns an `unavailable dependency` refusal and run() PROPAGATES it -- returned,
    # never raised -- because the probe then has no anchor instant to record any fact.
    # The refusal CATEGORY is asserted, not the message prose.
    spent_clock = DataDrivenClock(boot_epoch_id=_BOOT_EPOCH, wall_instants=[], monotonic_ns=[])
    result = _probe(clock=spent_clock).run()
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


# --- the verify-or-refuse degraded paths ------------------------------------


def test_spot_unit_unasserted_leaves_spot_evidence_unavailable() -> None:
    # Second-scale timestamps fall out of the millisecond magnitude band.
    spot = Ok(SpotSample(raw_timestamps=(1_724_000_000, 1_724_000_100), received_at=_instant(1)))
    profile = _ok(_probe(_FixtureTransport(spot=spot)).run()).profile
    fact = profile.latest_for(ProbeCheck.SPOT_TIMESTAMP_UNIT)
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED
    assert fact.measured == {}  # no value defaulted
    refusal = profile.require_evidence(VenueEvidenceClass.SPOT)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_spot_empty_sample_is_unverified() -> None:
    spot = Ok(SpotSample(raw_timestamps=(), received_at=_instant(1)))
    fact = _ok(_probe(_FixtureTransport(spot=spot)).run()).profile.latest_for(
        ProbeCheck.SPOT_TIMESTAMP_UNIT
    )
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


def test_spot_degenerate_clock_is_unverified() -> None:
    # A wall reading of zero cannot anchor a magnitude band, even with timestamps.
    probe = _probe(clock=_clock(wall_ns=0))
    fact = _ok(probe.run()).profile.latest_for(ProbeCheck.SPOT_TIMESTAMP_UNIT)
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


def test_spot_sample_unavailable_is_unverified() -> None:
    spot: Result[SpotSample] = _refusal(RefusalCategory.TRANSIENT_VENUE_FAILURE)
    fact = _ok(_probe(_FixtureTransport(spot=spot)).run()).profile.latest_for(
        ProbeCheck.SPOT_TIMESTAMP_UNIT
    )
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


def test_daily_boundary_too_few_bars_is_unverified_and_ungoverned() -> None:
    one_bar = Ok(
        TrendbarSample(
            bars=(
                Trendbar(
                    utc_timestamp_in_minutes=_DAY1_ANCHOR,
                    open_wire=1,
                    high_wire=1,
                    low_wire=1,
                    close_wire=1,
                ),
            ),
            received_at=_instant(_WALL_NS + 1),
        )
    )
    profile = _ok(_probe(_FixtureTransport(trendbars=one_bar)).run()).profile
    fact = profile.latest_for(ProbeCheck.DAILY_BOUNDARY)
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED
    refusal = profile.require_evidence(VenueEvidenceClass.VENUE_DAILY_BARS)
    assert is_refusal(refusal)


def test_daily_boundary_inconsistent_bars_is_unverified() -> None:
    bars = Ok(
        TrendbarSample(
            bars=(
                Trendbar(
                    utc_timestamp_in_minutes=_DAY1_ANCHOR,
                    open_wire=1,
                    high_wire=1,
                    low_wire=1,
                    close_wire=1,
                ),
                Trendbar(
                    utc_timestamp_in_minutes=_DAY1_ANCHOR + 1441,  # +1 day +1 min: disagrees
                    open_wire=1,
                    high_wire=1,
                    low_wire=1,
                    close_wire=1,
                ),
            ),
            received_at=_instant(_WALL_NS + 1),
        )
    )
    fact = _ok(_probe(_FixtureTransport(trendbars=bars)).run()).profile.latest_for(
        ProbeCheck.DAILY_BOUNDARY
    )
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


def test_daily_boundary_sample_unavailable_is_unverified() -> None:
    trendbars: Result[TrendbarSample] = _refusal(RefusalCategory.TRANSIENT_VENUE_FAILURE)
    fact = _ok(_probe(_FixtureTransport(trendbars=trendbars)).run()).profile.latest_for(
        ProbeCheck.DAILY_BOUNDARY
    )
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


def test_bar_basis_mismatch_refuses_bar_evidence() -> None:
    # Trendbar OHLC that the ticks do not reproduce.
    bad_bars = Ok(
        TrendbarSample(
            bars=(
                Trendbar(
                    utc_timestamp_in_minutes=_DAY1_ANCHOR,
                    open_wire=999_999,
                    high_wire=999_999,
                    low_wire=999_999,
                    close_wire=999_999,
                ),
                Trendbar(
                    utc_timestamp_in_minutes=_DAY2_ANCHOR,
                    open_wire=1,
                    high_wire=1,
                    low_wire=1,
                    close_wire=1,
                ),
            ),
            received_at=_instant(_WALL_NS + 1),
        )
    )
    profile = _ok(_probe(_FixtureTransport(trendbars=bad_bars)).run()).profile
    fact = profile.latest_for(ProbeCheck.BAR_BASIS)
    assert fact is not None
    assert fact.verdict is ProbeVerdict.REFUSED
    refusal = profile.require_evidence(VenueEvidenceClass.BAR)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_bar_basis_no_overlapping_ticks_is_unverified() -> None:
    far_ticks = Ok(
        TickHistorySample(
            quote_type="bid",
            ticks=(Tick(utc_timestamp_in_minutes=1, price_wire=100_000),),
            received_at=_instant(_WALL_NS + 2),
        )
    )
    fact = _ok(_probe(_FixtureTransport(ticks=far_ticks)).run()).profile.latest_for(
        ProbeCheck.BAR_BASIS
    )
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


def test_bar_basis_tick_sample_unavailable_is_unverified() -> None:
    ticks: Result[TickHistorySample] = _refusal(RefusalCategory.TRANSIENT_VENUE_FAILURE)
    fact = _ok(_probe(_FixtureTransport(ticks=ticks)).run()).profile.latest_for(
        ProbeCheck.BAR_BASIS
    )
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


def test_pip_formula_mismatch_refuses_metadata_parameters() -> None:
    bad_symbol = Ok(
        SymbolMetadataRecord(
            symbol="EURUSD",
            digits=5,
            pip_position=4,
            declared_pip_size=_pip_size(1, 1_000),  # not 10**-4
            received_at=_instant(_WALL_NS + 4),
        )
    )
    profile = _ok(_probe(_FixtureTransport(symbol=bad_symbol)).run()).profile
    fact = profile.latest_for(ProbeCheck.PIP_FORMULA)
    assert fact is not None
    assert fact.verdict is ProbeVerdict.REFUSED
    refusal = profile.require_evidence(VenueEvidenceClass.METADATA_DERIVED_PARAMETERS)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_pip_formula_negative_position_is_unverified() -> None:
    odd_symbol = Ok(
        SymbolMetadataRecord(
            symbol="EURUSD",
            digits=5,
            pip_position=-1,
            declared_pip_size=_pip_size(1, 10),
            received_at=_instant(_WALL_NS + 4),
        )
    )
    fact = _ok(_probe(_FixtureTransport(symbol=odd_symbol)).run()).profile.latest_for(
        ProbeCheck.PIP_FORMULA
    )
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


def test_pip_formula_symbol_unavailable_is_unverified() -> None:
    symbol: Result[SymbolMetadataRecord] = _refusal(RefusalCategory.UNAVAILABLE_DEPENDENCY)
    fact = _ok(_probe(_FixtureTransport(symbol=symbol)).run()).profile.latest_for(
        ProbeCheck.PIP_FORMULA
    )
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


def test_absent_money_exponent_is_unverified_never_defaulted() -> None:
    no_money = Ok(AccountMoneyRecord(money_digits=None, received_at=_instant(_WALL_NS + 5)))
    profile = _ok(_probe(_FixtureTransport(money=no_money)).run()).profile
    fact = profile.latest_for(ProbeCheck.MONEY_EXPONENT)
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED
    assert "money_digits" not in fact.measured  # never defaulted to 2
    refusal = profile.require_evidence(VenueEvidenceClass.MONEY_DECODE)
    assert is_refusal(refusal)


def test_money_record_unavailable_is_unverified() -> None:
    money: Result[AccountMoneyRecord] = _refusal(RefusalCategory.UNAVAILABLE_DEPENDENCY)
    fact = _ok(_probe(_FixtureTransport(money=money)).run()).profile.latest_for(
        ProbeCheck.MONEY_EXPONENT
    )
    assert fact is not None
    assert fact.verdict is ProbeVerdict.UNVERIFIED


# --- the findings note ------------------------------------------------------


def test_findings_surface_a_contradiction_with_an_upstream_assumption() -> None:
    claim = _ok(
        UpstreamAssumption.try_create(
            "daily-boundary",
            "bars=2;utc_minute_of_day=1020",  # the demoted 17:00-NY claim, passed as data
            "2013-forum-grade, demoted DEC-0135",
        )
    )
    report = _ok(_probe(assumptions=(claim,)).run())
    contradictions = report.findings.contradictions()
    assert len(contradictions) == 1
    assert contradictions[0].check is ProbeCheck.DAILY_BOUNDARY
    assert contradictions[0].contradicts is True


def test_findings_agree_when_measurement_matches_claim() -> None:
    claim = _ok(
        UpstreamAssumption.try_create(
            "daily-boundary", "bars=2;utc_minute_of_day=0", "measured elsewhere"
        )
    )
    report = _ok(_probe(assumptions=(claim,)).run())
    assert report.findings.contradictions() == ()
    assert report.findings.findings[0].contradicts is False


def test_findings_leave_an_unverified_check_open_for_amendment() -> None:
    no_money = Ok(AccountMoneyRecord(money_digits=None, received_at=_instant(_WALL_NS + 5)))
    claim = _ok(
        UpstreamAssumption.try_create("money-exponent", "money_digits=2", "assumed default")
    )
    report = _ok(_probe(_FixtureTransport(money=no_money), assumptions=(claim,)).run())
    finding = report.findings.findings[0]
    assert finding.check is ProbeCheck.MONEY_EXPONENT
    assert finding.contradicts is False
    assert "amendment" in finding.detail


def test_findings_flag_an_assumption_key_that_names_no_check() -> None:
    claim = _ok(UpstreamAssumption.try_create("not-a-check", "whatever", "note"))
    report = _ok(_probe(assumptions=(claim,)).run())
    finding = report.findings.findings[0]
    assert finding.check is None
    assert finding.contradicts is False


def test_report_with_no_assumptions_has_no_findings() -> None:
    report = _ok(_probe().run())
    assert report.findings.findings == ()


# --- UpstreamAssumption construction ----------------------------------------


def test_upstream_assumption_validates_its_parts() -> None:
    assert is_refusal(UpstreamAssumption.try_create("", "v", "note"))
    assert is_refusal(UpstreamAssumption.try_create("k", 123, "note"))
    assert is_refusal(UpstreamAssumption.try_create("k", "v", ""))
    built = _ok(UpstreamAssumption.try_create("daily-boundary", "v", "note"))
    assert built.key == "daily-boundary"


# --- probe construction refusals --------------------------------------------


def test_probe_try_create_rejects_a_bad_clock() -> None:
    assert is_refusal(
        CapabilityProbe.try_create(
            object(),
            _FixtureTransport(),
            _venue(),
            _account(),
            _secret_ref(),
            _PROTO_TAG,
            _SESSION_EPOCH,
        )
    )


def test_probe_try_create_rejects_a_bad_transport() -> None:
    assert is_refusal(
        CapabilityProbe.try_create(
            _clock(),
            object(),
            _venue(),
            _account(),
            _secret_ref(),
            _PROTO_TAG,
            _SESSION_EPOCH,
        )
    )


def test_probe_try_create_rejects_a_bad_venue_and_account() -> None:
    assert is_refusal(
        CapabilityProbe.try_create(
            _clock(),
            _FixtureTransport(),
            object(),
            _account(),
            _secret_ref(),
            _PROTO_TAG,
            _SESSION_EPOCH,
        )
    )
    assert is_refusal(
        CapabilityProbe.try_create(
            _clock(),
            _FixtureTransport(),
            _venue(),
            object(),
            _secret_ref(),
            _PROTO_TAG,
            _SESSION_EPOCH,
        )
    )


def test_probe_try_create_rejects_account_of_a_different_venue() -> None:
    other_venue = _ok(VenueId.try_create("venue-other"))
    foreign_account = _account(other_venue)
    assert is_refusal(
        CapabilityProbe.try_create(
            _clock(),
            _FixtureTransport(),
            _venue(),
            foreign_account,
            _secret_ref(),
            _PROTO_TAG,
            _SESSION_EPOCH,
        )
    )


def test_probe_try_create_rejects_a_non_secret_ref_credential() -> None:
    result = CapabilityProbe.try_create(
        _clock(),
        _FixtureTransport(),
        _venue(),
        _account(),
        "a-bare-string",
        _PROTO_TAG,
        _SESSION_EPOCH,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_probe_try_create_rejects_a_bad_proto_tag() -> None:
    for tag in (0, -1, True, "91"):
        assert is_refusal(
            CapabilityProbe.try_create(
                _clock(),
                _FixtureTransport(),
                _venue(),
                _account(),
                _secret_ref(),
                tag,
                _SESSION_EPOCH,
            )
        )


def test_probe_try_create_rejects_a_blank_session_epoch() -> None:
    assert is_refusal(
        CapabilityProbe.try_create(
            _clock(),
            _FixtureTransport(),
            _venue(),
            _account(),
            _secret_ref(),
            _PROTO_TAG,
            "   ",
        )
    )


def test_probe_try_create_rejects_bad_upstream_assumptions() -> None:
    assert is_refusal(
        CapabilityProbe.try_create(
            _clock(),
            _FixtureTransport(),
            _venue(),
            _account(),
            _secret_ref(),
            _PROTO_TAG,
            _SESSION_EPOCH,
            "not-a-sequence",
        )
    )
    assert is_refusal(
        CapabilityProbe.try_create(
            _clock(),
            _FixtureTransport(),
            _venue(),
            _account(),
            _secret_ref(),
            _PROTO_TAG,
            _SESSION_EPOCH,
            [object()],
        )
    )


def test_probe_accepts_none_upstream_assumptions() -> None:
    probe = _ok(
        CapabilityProbe.try_create(
            _clock(),
            _FixtureTransport(),
            _venue(),
            _account(),
            _secret_ref(),
            _PROTO_TAG,
            _SESSION_EPOCH,
            None,
        )
    )
    assert probe.upstream_assumptions == ()


def test_probe_try_create_refuses_a_proto_tag_mismatch() -> None:
    result = CapabilityProbe.try_create(
        _clock(),
        _FixtureTransport(proto_release_tag=90),
        _venue(),
        _account(),
        _secret_ref(),
        _PROTO_TAG,
        _SESSION_EPOCH,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- the venue-observation profile itself -----------------------------------


def test_profile_try_create_validates_its_key() -> None:
    assert is_refusal(VenueObservationProfile.try_create(object(), _account()))
    assert is_refusal(VenueObservationProfile.try_create(_venue(), object()))
    other = _account(_ok(VenueId.try_create("venue-other")))
    assert is_refusal(VenueObservationProfile.try_create(_venue(), other))
    assert is_ok(VenueObservationProfile.try_create(_venue(), _account()))


def _fact(check: ProbeCheck, verdict: ProbeVerdict, **measured: object) -> MeasuredFact:
    return _ok(
        MeasuredFact.try_create(
            check,
            verdict,
            _instant(_WALL_NS),
            _SESSION_EPOCH,
            _CRED_REF_ID,
            measured=measured,
        )
    )


def test_with_fact_appends_and_wires_the_supersedes_edge() -> None:
    profile = _ok(VenueObservationProfile.try_create(_venue(), _account()))
    first = _fact(ProbeCheck.DAILY_BOUNDARY, ProbeVerdict.UNVERIFIED)
    profile = _ok(profile.with_fact(first))
    assert profile.facts[0].supersedes is None
    second = _fact(ProbeCheck.DAILY_BOUNDARY, ProbeVerdict.VERIFIED, utc_minute_of_day=0)
    profile = _ok(profile.with_fact(second))
    assert len(profile.facts) == 2
    assert profile.facts[1].supersedes == 0  # supersedes the first same-check fact
    assert len(profile.facts_for(ProbeCheck.DAILY_BOUNDARY)) == 2
    latest = profile.latest_for(ProbeCheck.DAILY_BOUNDARY)
    assert latest is not None and latest.verdict is ProbeVerdict.VERIFIED


def test_with_fact_rejects_a_non_fact() -> None:
    profile = _ok(VenueObservationProfile.try_create(_venue(), _account()))
    assert is_refusal(profile.with_fact(object()))


def test_latest_for_returns_none_when_unrecorded() -> None:
    profile = _ok(VenueObservationProfile.try_create(_venue(), _account()))
    assert profile.latest_for(ProbeCheck.BAR_BASIS) is None


def test_require_evidence_is_unavailable_when_no_fact_governs_the_class() -> None:
    profile = _ok(VenueObservationProfile.try_create(_venue(), _account()))
    refusal = profile.require_evidence(VenueEvidenceClass.SPOT)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_require_evidence_accepts_a_string_class_and_rejects_a_bad_one() -> None:
    profile = _ok(_probe().run()).profile
    assert _ok(profile.require_evidence("spot")) is True
    assert is_refusal(profile.require_evidence("not-a-class"))
    assert is_refusal(profile.require_evidence(123))


def test_evidence_class_for_maps_every_check() -> None:
    assert evidence_class_for(ProbeCheck.SPOT_TIMESTAMP_UNIT) is VenueEvidenceClass.SPOT
    assert evidence_class_for(ProbeCheck.DAILY_BOUNDARY) is VenueEvidenceClass.VENUE_DAILY_BARS
    assert evidence_class_for(ProbeCheck.BAR_BASIS) is VenueEvidenceClass.BAR
    assert (
        evidence_class_for(ProbeCheck.PIP_FORMULA) is VenueEvidenceClass.METADATA_DERIVED_PARAMETERS
    )
    assert evidence_class_for(ProbeCheck.MONEY_EXPONENT) is VenueEvidenceClass.MONEY_DECODE


# --- MeasuredFact -----------------------------------------------------------


def test_measured_fact_try_create_validates_every_part() -> None:
    good = _instant(_WALL_NS)
    assert is_refusal(
        MeasuredFact.try_create("nope", ProbeVerdict.VERIFIED, good, _SESSION_EPOCH, _CRED_REF_ID)
    )
    assert is_refusal(
        MeasuredFact.try_create(ProbeCheck.BAR_BASIS, "nope", good, _SESSION_EPOCH, _CRED_REF_ID)
    )
    assert is_refusal(
        MeasuredFact.try_create(
            ProbeCheck.BAR_BASIS, ProbeVerdict.VERIFIED, object(), _SESSION_EPOCH, _CRED_REF_ID
        )
    )
    assert is_refusal(
        MeasuredFact.try_create(
            ProbeCheck.BAR_BASIS, ProbeVerdict.VERIFIED, good, "  ", _CRED_REF_ID
        )
    )
    assert is_refusal(
        MeasuredFact.try_create(
            ProbeCheck.BAR_BASIS, ProbeVerdict.VERIFIED, good, _SESSION_EPOCH, ""
        )
    )


def test_measured_fact_try_create_derives_the_evidence_class() -> None:
    fact = _ok(
        MeasuredFact.try_create(
            "bar-basis", "verified", _instant(_WALL_NS), _SESSION_EPOCH, _CRED_REF_ID
        )
    )
    assert fact.evidence_class is VenueEvidenceClass.BAR
    assert fact.available is True


def test_measured_fact_summary_is_key_sorted() -> None:
    fact = _fact(ProbeCheck.PIP_FORMULA, ProbeVerdict.VERIFIED, pip_size_num=1, pip_position=4)
    assert fact.summary() == "pip_position=4;pip_size_num=1"


def test_measured_fact_snapshots_its_measured_payload() -> None:
    source: dict[str, object] = {"k": 1}
    fact = MeasuredFact.try_create(
        ProbeCheck.MONEY_EXPONENT,
        ProbeVerdict.VERIFIED,
        _instant(_WALL_NS),
        _SESSION_EPOCH,
        _CRED_REF_ID,
        measured=source,
    )
    built = _ok(fact)
    source["k"] = 999
    assert built.measured["k"] == 1


def test_measured_fact_deep_freezes_a_nested_sequence() -> None:
    source: dict[str, object] = {"samples": [1, 2, 3]}
    built = _ok(
        MeasuredFact.try_create(
            ProbeCheck.SPOT_TIMESTAMP_UNIT,
            ProbeVerdict.VERIFIED,
            _instant(_WALL_NS),
            _SESSION_EPOCH,
            _CRED_REF_ID,
            measured=source,
        )
    )
    # A nested list is frozen to a tuple, so the caller's list cannot mutate the fact.
    assert built.measured["samples"] == (1, 2, 3)


# --- minting the venue-scoped calendar identity -----------------------------


def test_mint_daily_calendar_identity_from_a_verified_boundary() -> None:
    profile = _ok(_probe().run()).profile
    minted = profile.mint_daily_boundary_calendar("v1", "2024a")
    identity = _ok(minted)
    assert isinstance(identity, CalendarIdentity)
    assert identity.rule_set == "venue-daily::venue-ctrader-demo::utc_minute_of_day=0"
    assert "17:00" not in identity.rule_set  # never the demoted NY claim
    assert identity.rule_set_version == "v1"
    assert identity.tzdata_version == "2024a"


def test_mint_daily_calendar_identity_refuses_without_a_verified_boundary() -> None:
    profile = _ok(VenueObservationProfile.try_create(_venue(), _account()))
    refusal = profile.mint_daily_boundary_calendar("v1", "2024a")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_mint_daily_calendar_identity_passes_through_a_bad_version() -> None:
    profile = _ok(_probe().run()).profile
    assert is_refusal(profile.mint_daily_boundary_calendar("", "2024a"))
