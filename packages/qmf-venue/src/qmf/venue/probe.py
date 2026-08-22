"""The cTrader capability probe — the first-connection verification suite (Story 8.1).

`COMP-QMF-VENUE`'s earliest work unit: connect to a cTrader demo venue with only
qmf-core nouns and an operator-approved demo-credential *reference*, run the named
verify-or-refuse checks against the real API through a throwaway transport over the
pinned Spotware proto release tag, and record every measured fact and verdict into a
per-(VenueId, account) venue-observation profile — so venue feasibility is proven
against the real wire before any port contract is built on paper (FR-022, FR-026,
SC-02, AR-45; DEC-0135, DEC-0138).

The probe **stands alone** (AR-45): it depends on no port contract, no connection
manager, and no Epic 3 journal. It reads its raw samples through the injected
:class:`ProbeTransport` seam and returns its recorded profile directly, so it can run
as the earliest factory work unit. In production the transport is a throwaway wire
client; in tests it is a fixture that contacts no host. The probe imports only
``qmf-core`` (default-deny, L30/DEC-0120).

The five checks (CT-18 verification suite; DEC-0135, DEC-0138):

* **spot-timestamp-unit** — assert the undocumented spot-event timestamp unit is
  milliseconds *by magnitude*, against a plausibility band derived from the injected
  clock (never a hardcoded epoch). Unasserted → spot evidence stays unavailable.
* **daily-boundary** — measure the venue's D1 rollover from trendbar timestamps per
  broker. The 17:00-New-York claim is demoted evidence and is **never hardcoded**
  (AR-46, DEC-0135); an unmeasured boundary leaves venue daily bars ungoverned.
* **bar-basis** — reconcile trendbar OHLC against the transport's declared-quote-side
  tick history. The BID basis is **never hardcoded** (AR-46, DEC-0135); the verified
  quote side is whatever the reconciled tick sample declares. A mismatch refuses bars.
* **pip-formula** — validate ``pip_size == 10**-pip_position`` exactly. A failure
  refuses metadata-derived parameters.
* **money-exponent** — require the account's ``money_digits`` exponent. Absent → the
  money decode stays unavailable; never a default to 2 (DEC-0135).

Every measured value is exact — scaled integers or :class:`~qmf.core.ExactRational` —
so no binary float ever touches the money path (CT-01; DEC-0105). A credential appears
only by its reference id; no live host is contacted and no order is ever submitted
(FR-025, AR-37, SC-02; DEC-0136).

Stdlib + qmf-core only. Frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core import (
    Account,
    Clock,
    ExactRational,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    TypedRefusal,
    VenueId,
    is_refusal,
)
from qmf.venue.observation import (
    MeasuredFact,
    ProbeCheck,
    ProbeVerdict,
    VenueObservationProfile,
    evidence_class_for,
)

__all__ = [
    "AccountMoneyRecord",
    "CapabilityProbe",
    "Finding",
    "FindingsNote",
    "ProbeReport",
    "ProbeTransport",
    "SpotSample",
    "SymbolMetadataRecord",
    "Tick",
    "TickHistorySample",
    "Trendbar",
    "TrendbarSample",
    "UpstreamAssumption",
]

# A spot-event timestamp is milliseconds by magnitude when it sits within this
# multiplicative band of the injected wall clock expressed in ms. Seconds are ~1000x
# smaller and microseconds ~1000x larger, so a band of 8 separates the three units
# cleanly without ever hardcoding an epoch. Not a registry value — a discrimination
# margin stated at its point of use.
_MS_MAGNITUDE_FACTOR: Final[int] = 8

# The venue's D1 boundary is confirmed only when at least this many daily bars agree on
# one UTC minute-of-day; a single bar cannot distinguish a real boundary from a fluke.
_MIN_DAILY_BARS: Final[int] = 2

# Minutes in a day — the modulus that turns a trendbar's minutes-since-epoch stamp into
# its UTC minute-of-day boundary.
_MINUTES_PER_DAY: Final[int] = 24 * 60


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a probe construction returns."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unsupported(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unsupported capability`` refusal a proto-tag mismatch returns."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context=context,
    )


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


# --- raw wire samples (foreign evidence, stored verbatim) -------------------


@dataclass(frozen=True, slots=True)
class SpotSample:
    """Raw spot-event timestamps in the venue's undocumented unit (DEC-0135).

    ``raw_timestamps`` are the verbatim wire timestamps whose unit the probe must
    assert; ``received_at`` is the mandatory local receive instant (the Open API
    exposes no server clock).
    """

    raw_timestamps: tuple[int, ...]
    received_at: Instant


@dataclass(frozen=True, slots=True)
class Trendbar:
    """One decoded trendbar: its minutes-since-epoch anchor and absolute OHLC in the
    venue's wire price scale (integers, never floats; DEC-0135, DEC-0141)."""

    utc_timestamp_in_minutes: int
    open_wire: int
    high_wire: int
    low_wire: int
    close_wire: int


@dataclass(frozen=True, slots=True)
class TrendbarSample:
    """A sample of D1 trendbars plus the mandatory receive instant (DEC-0135)."""

    bars: tuple[Trendbar, ...]
    received_at: Instant


@dataclass(frozen=True, slots=True)
class Tick:
    """One BID/ASK-selected historical tick: its minute anchor and wire price."""

    utc_timestamp_in_minutes: int
    price_wire: int


@dataclass(frozen=True, slots=True)
class TickHistorySample:
    """BID/ASK-selectable tick history (DEC-0135).

    ``quote_type`` is the venue-selected quote side the transport requested (an opaque
    token, e.g. the wire's own bid/ask selector); the probe records it verbatim as the
    verified basis on a reconciliation match — the BID basis is never hardcoded.
    """

    quote_type: str
    ticks: tuple[Tick, ...]
    received_at: Instant


@dataclass(frozen=True, slots=True)
class SymbolMetadataRecord:
    """The full symbol metadata a price decode needs (DEC-0135, DEC-0141).

    A light symbol list carries no scaling metadata, so the full record is required.
    ``declared_pip_size`` is the venue-declared pip size as an exact rational, validated
    against ``10**-pip_position``.
    """

    symbol: str
    digits: int
    pip_position: int
    declared_pip_size: ExactRational
    received_at: Instant


@dataclass(frozen=True, slots=True)
class AccountMoneyRecord:
    """The account's money-scaling record (DEC-0135).

    ``money_digits`` is the ``moneyDigits`` exponent governing money decode; ``None``
    means the venue omitted it — an absent exponent is never defaulted to 2.
    """

    money_digits: int | None
    received_at: Instant


# --- the throwaway transport seam -------------------------------------------


@runtime_checkable
class ProbeTransport(Protocol):
    """The read-only throwaway transport the probe measures through (DEC-0135, DEC-0141).

    A definitions-only seam injected at construction: in production a throwaway wire
    client speaking the pinned Spotware proto release tag; in tests a fixture that
    contacts no host. It exposes **only** fetches — the probe never submits an order —
    and each returns value-or-refusal, so an unavailable sample is a typed refusal the
    probe records as ``unverified`` rather than an exception.
    """

    @property
    def proto_release_tag(self) -> int:  # pragma: no cover - protocol seam
        """The Spotware ``openapi-proto-messages`` integer release tag this transport
        speaks; a mismatch with the pinned artifact mints a re-verification (DEC-0141)."""
        ...

    def fetch_spot_sample(self) -> Result[SpotSample]:  # pragma: no cover - protocol seam
        """Fetch a sample of raw spot events (value-or-refusal)."""
        ...

    def fetch_trendbar_sample(self) -> Result[TrendbarSample]:  # pragma: no cover - protocol seam
        """Fetch a sample of D1 trendbars (value-or-refusal)."""
        ...

    def fetch_tick_history_sample(
        self,
    ) -> Result[TickHistorySample]:  # pragma: no cover - protocol seam
        """Fetch a BID/ASK-selected tick-history sample (value-or-refusal)."""
        ...

    def fetch_symbol_metadata(
        self,
    ) -> Result[SymbolMetadataRecord]:  # pragma: no cover - protocol seam
        """Fetch the full symbol metadata record (value-or-refusal)."""
        ...

    def fetch_account_money_record(
        self,
    ) -> Result[AccountMoneyRecord]:  # pragma: no cover - protocol seam
        """Fetch the account money-scaling record (value-or-refusal)."""
        ...


# --- upstream assumptions and the findings note -----------------------------


@dataclass(frozen=True, slots=True)
class UpstreamAssumption:
    """A recorded upstream claim the probe's findings test against (SC-02; DEC-0135).

    ``key`` names the probe check the claim concerns (a :class:`ProbeCheck` value),
    ``claimed_value`` the claim in the check's own measured-summary form, and
    ``source_note`` its provenance (e.g. a demoted 2013-forum-grade claim). Passed in
    as data — the demoted 17:00-New-York and BID claims live here, never hardcoded in
    the probe — so a measured fact that contradicts one is surfaced for amendment.
    """

    key: str
    claimed_value: str
    source_note: str

    @classmethod
    def try_create(
        cls, key: object, claimed_value: object, source_note: object
    ) -> Result[UpstreamAssumption]:
        """Validate and build an :class:`UpstreamAssumption`, returning value-or-refusal."""
        key_token = _clean_str(key)
        if key_token is None:
            return _invalid(
                "key", "an upstream assumption names a non-empty check key", given=repr(key)
            )
        claim = claimed_value if isinstance(claimed_value, str) else None
        if claim is None:
            return _invalid(
                "claimed_value",
                "an upstream assumption carries its claim as a string",
                given=repr(claimed_value),
            )
        note = _clean_str(source_note)
        if note is None:
            return _invalid(
                "source_note",
                "an upstream assumption records its provenance note",
                given=repr(source_note),
            )
        return Ok(cls(key=key_token, claimed_value=claim, source_note=note))


@dataclass(frozen=True, slots=True)
class Finding:
    """One line of the findings note: a measured fact weighed against a claim (SC-02).

    ``contradicts`` is ``True`` only when a *verified* measured fact disagrees with the
    upstream assumption — the amendment trigger. An unverified or refused check cannot
    contradict a claim, but it is still surfaced (``contradicts`` false) so the claim
    stays open for amendment.
    """

    check: ProbeCheck | None
    assumption_key: str
    claimed_value: str
    measured_summary: str
    contradicts: bool
    detail: str


@dataclass(frozen=True, slots=True)
class FindingsNote:
    """The probe's findings note: every assumption weighed, contradictions surfaced."""

    findings: tuple[Finding, ...] = ()

    def contradictions(self) -> tuple[Finding, ...]:
        """The findings whose verified measurement contradicts an upstream assumption."""
        return tuple(finding for finding in self.findings if finding.contradicts)


@dataclass(frozen=True, slots=True)
class ProbeReport:
    """The probe's output: the recorded profile plus the findings note (SC-02).

    ``proto_release_tag`` records the pinned Spotware release tag the run measured
    against, so a later tag change is a visible re-verification trigger (DEC-0141).
    """

    profile: VenueObservationProfile
    findings: FindingsNote
    proto_release_tag: int


# --- the probe --------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CapabilityProbe:
    """The first-connection capability probe (Story 8.1; AR-45, DEC-0135, DEC-0138).

    Built through :meth:`try_create` from qmf-core nouns, an injected :class:`Clock`,
    an injected :class:`ProbeTransport`, and a demo-credential *reference*. :meth:`run`
    executes the five verify-or-refuse checks, records each into a fresh
    venue-observation profile, and returns the profile plus a findings note. It holds a
    :class:`~qmf.core.SecretRef` (a reference), never a :class:`~qmf.core.SecretValue`,
    so no credential value can be rendered; and it exposes no submit path, so no order
    is ever placed (FR-025, AR-37; DEC-0136).
    """

    clock: Clock
    transport: ProbeTransport
    venue_id: VenueId
    account: Account
    credential_ref: SecretRef
    proto_release_tag: int
    session_epoch: str
    upstream_assumptions: tuple[UpstreamAssumption, ...] = ()

    @classmethod
    def try_create(
        cls,
        clock: object,
        transport: object,
        venue_id: object,
        account: object,
        credential_ref: object,
        proto_release_tag: object,
        session_epoch: object,
        upstream_assumptions: object = None,
    ) -> Result[CapabilityProbe]:
        """Validate the wiring and build a :class:`CapabilityProbe`, value-or-refusal.

        A malformed noun, a non-:class:`Clock` / non-:class:`ProbeTransport` seam, an
        account that does not belong to the venue, a non-positive proto tag, a blank
        session epoch, or a credential that is not a bare :class:`~qmf.core.SecretRef`
        is an ``invalid input`` refusal. A transport whose proto release tag differs
        from the pinned artifact is an ``unsupported capability`` refusal — a tag change
        mints a new capability declaration plus re-verification (DEC-0141).
        """
        if not isinstance(clock, Clock):
            return _invalid(
                "clock", "the probe reads time through an injected Clock seam", given=repr(clock)
            )
        if not isinstance(transport, ProbeTransport):
            return _invalid(
                "transport",
                "the probe measures through an injected ProbeTransport seam",
                given=repr(transport),
            )
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid("venue_id", "the probe targets a valid VenueId", given=repr(venue_id))
        if not isinstance(account, Account):
            return _invalid("account", "the probe targets a valid Account", given=repr(account))
        if account.venue != venue_id:
            return _invalid(
                "account",
                "the account does not belong to the targeted venue",
                venue=venue_id.value,
                account_venue=account.venue.value,
            )
        if not isinstance(credential_ref, SecretRef) or credential_ref.value.strip() == "":
            return _invalid(
                "credential_ref",
                "the probe holds a SecretRef (a reference), never a credential value (DEC-0136)",
                given=repr(credential_ref),
            )
        if (
            isinstance(proto_release_tag, bool)
            or not isinstance(proto_release_tag, int)
            or proto_release_tag <= 0
        ):
            return _invalid(
                "proto_release_tag",
                "the pinned Spotware proto release tag is a positive integer, injected "
                "never hardcoded",
                given=repr(proto_release_tag),
            )
        epoch = _clean_str(session_epoch)
        if epoch is None:
            return _invalid(
                "session_epoch",
                "a session-epoch id (distinct from the boot epoch) is a non-empty token",
                given=repr(session_epoch),
            )
        assumptions = _coerce_assumptions(upstream_assumptions)
        if is_refusal(assumptions):
            return assumptions
        if transport.proto_release_tag != proto_release_tag:
            return _unsupported(
                "proto_release_tag",
                "the transport speaks a different Spotware proto release tag than the pinned "
                "artifact; a tag change mints a new capability declaration plus re-verification",
                pinned=proto_release_tag,
                transport=transport.proto_release_tag,
            )
        return Ok(
            cls(
                clock=clock,
                transport=transport,
                venue_id=venue_id,
                account=account,
                credential_ref=credential_ref,
                proto_release_tag=proto_release_tag,
                session_epoch=epoch,
                upstream_assumptions=assumptions.value,
            )
        )

    def run(self) -> ProbeReport:
        """Run the verification suite and return the recorded profile plus findings.

        Reads the injected clock once for the run instant (the plausibility base for the
        spot-timestamp assertion and the receive-time fallback when a sample is
        unavailable), executes the five checks in order, records each fact into the
        profile with its supersedes edge, and weighs every upstream assumption. The run
        itself always completes — a check that cannot pass is recorded ``unverified`` or
        ``refused``, never raised and never defaulted.
        """
        run_instant = self.clock.wall_now()
        facts = (
            self._check_spot_timestamp_unit(run_instant),
            self._check_daily_boundary(run_instant),
            self._check_bar_basis(run_instant),
            self._check_pip_formula(run_instant),
            self._check_money_exponent(run_instant),
        )
        profile = VenueObservationProfile(venue_id=self.venue_id, account=self.account)
        for fact in facts:
            recorded = profile.with_fact(fact)
            # with_fact only refuses a non-MeasuredFact; every fact here is one, so the
            # success arm always holds (the refusal arm is unreachable by construction).
            if is_refusal(recorded):  # pragma: no cover - facts are always MeasuredFacts
                continue
            profile = recorded.value
        return ProbeReport(
            profile=profile,
            findings=self._findings(profile),
            proto_release_tag=self.proto_release_tag,
        )

    # -- fact construction ---------------------------------------------------

    def _fact(
        self,
        check: ProbeCheck,
        verdict: ProbeVerdict,
        received_at: Instant,
        *,
        measured: dict[str, object] | None = None,
        detail: str,
    ) -> MeasuredFact:
        """Build one measured fact under this probe's session epoch and credential
        reference (a reference id, never a value)."""
        return MeasuredFact(
            check=check,
            verdict=verdict,
            evidence_class=evidence_class_for(check),
            received_at=received_at,
            session_epoch=self.session_epoch,
            credential_ref_id=self.credential_ref.value,
            measured=measured if measured is not None else {},
            detail=detail,
        )

    # -- the five checks -----------------------------------------------------

    def _check_spot_timestamp_unit(self, run_instant: Instant) -> MeasuredFact:
        """Assert the spot-event timestamp unit is milliseconds by magnitude (DEC-0135).

        The plausibility band is derived from the injected clock's wall reading in ms,
        never a hardcoded epoch: a millisecond stamp sits within a small factor of it,
        while a seconds or microseconds stamp falls out of band. An unassertable unit is
        recorded ``unverified`` — spot evidence stays unavailable, never defaulted.
        """
        check = ProbeCheck.SPOT_TIMESTAMP_UNIT
        fetched = self.transport.fetch_spot_sample()
        if is_refusal(fetched):
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                run_instant,
                detail="spot sample unavailable; the timestamp unit could not be asserted",
            )
        sample = fetched.value
        wall_ms = run_instant.value_ns // 1_000_000
        if wall_ms <= 0 or not sample.raw_timestamps:
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                sample.received_at,
                detail="no spot timestamps to assert a magnitude against",
            )
        lower = wall_ms // _MS_MAGNITUDE_FACTOR
        upper = wall_ms * _MS_MAGNITUDE_FACTOR
        all_ms = all(lower <= stamp <= upper for stamp in sample.raw_timestamps)
        if all_ms:
            return self._fact(
                check,
                ProbeVerdict.VERIFIED,
                sample.received_at,
                measured={"unit": "milliseconds", "sample_size": len(sample.raw_timestamps)},
                detail="every spot timestamp sits in the millisecond magnitude band of the "
                "injected clock",
            )
        return self._fact(
            check,
            ProbeVerdict.UNVERIFIED,
            sample.received_at,
            detail="spot timestamps do not sit in the millisecond magnitude band; unit unasserted",
        )

    def _check_daily_boundary(self, run_instant: Instant) -> MeasuredFact:
        """Measure the venue's D1 rollover from trendbar timestamps (AR-46; DEC-0135).

        The boundary is the UTC minute-of-day the daily bars agree on. It is measured,
        never hardcoded — the demoted 17:00-New-York claim appears nowhere here. Fewer
        than the confirming number of bars, or bars that disagree, leave the boundary
        ``unverified`` and venue daily bars ungoverned.
        """
        check = ProbeCheck.DAILY_BOUNDARY
        fetched = self.transport.fetch_trendbar_sample()
        if is_refusal(fetched):
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                run_instant,
                detail="trendbar sample unavailable; the daily boundary could not be measured",
            )
        sample = fetched.value
        if len(sample.bars) < _MIN_DAILY_BARS:
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                sample.received_at,
                detail="too few daily bars to confirm a boundary; venue daily bars stay ungoverned",
            )
        minutes_of_day = {bar.utc_timestamp_in_minutes % _MINUTES_PER_DAY for bar in sample.bars}
        if len(minutes_of_day) != 1:
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                sample.received_at,
                detail="daily bars disagree on a UTC minute-of-day boundary; boundary unmeasured",
            )
        measured_minute = next(iter(minutes_of_day))
        return self._fact(
            check,
            ProbeVerdict.VERIFIED,
            sample.received_at,
            measured={"utc_minute_of_day": measured_minute, "bars": len(sample.bars)},
            detail="the venue's D1 boundary is measured per broker as one UTC minute-of-day",
        )

    def _check_bar_basis(self, run_instant: Instant) -> MeasuredFact:
        """Reconcile trendbar OHLC against the declared-quote-side ticks (AR-46; DEC-0135).

        The verified basis is whatever quote side the tick sample declares — the BID
        basis is never hardcoded. A per-period OHLC mismatch refuses bar evidence; no
        overlapping ticks leave the basis ``unverified``.
        """
        check = ProbeCheck.BAR_BASIS
        bars_result = self.transport.fetch_trendbar_sample()
        ticks_result = self.transport.fetch_tick_history_sample()
        if is_refusal(bars_result) or is_refusal(ticks_result):
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                run_instant,
                detail="trendbar or tick sample unavailable; the bar basis could not be reconciled",
            )
        bars = bars_result.value
        ticks = ticks_result.value
        reconciled = 0
        mismatched = 0
        for bar in bars.bars:
            derived = _ohlc_from_ticks(bar, ticks.ticks)
            if derived is None:
                continue
            if derived == (bar.open_wire, bar.high_wire, bar.low_wire, bar.close_wire):
                reconciled += 1
            else:
                mismatched += 1
        if mismatched > 0:
            return self._fact(
                check,
                ProbeVerdict.REFUSED,
                ticks.received_at,
                detail=f"trendbar OHLC disagrees with '{ticks.quote_type}' ticks; "
                "bar evidence refused",
            )
        if reconciled == 0:
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                ticks.received_at,
                detail="no overlapping ticks to reconcile a bar basis against",
            )
        return self._fact(
            check,
            ProbeVerdict.VERIFIED,
            ticks.received_at,
            measured={"quote_type": ticks.quote_type, "reconciled_bars": reconciled},
            detail=f"trendbar OHLC reconciles against '{ticks.quote_type}' ticks per broker",
        )

    def _check_pip_formula(self, run_instant: Instant) -> MeasuredFact:
        """Validate ``pip_size == 10**-pip_position`` exactly (DEC-0135).

        A failed validation refuses metadata-derived parameters; a negative pip position
        cannot be validated and is recorded ``unverified``.
        """
        check = ProbeCheck.PIP_FORMULA
        fetched = self.transport.fetch_symbol_metadata()
        if is_refusal(fetched):
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                run_instant,
                detail="symbol metadata unavailable; the pip formula could not be validated",
            )
        record = fetched.value
        if record.pip_position < 0:
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                record.received_at,
                detail="pip position is negative; the pip formula could not be validated",
            )
        expected = Fraction(1, 10**record.pip_position)
        if record.declared_pip_size.as_fraction() == expected:
            magnitude = record.declared_pip_size.as_fraction()
            return self._fact(
                check,
                ProbeVerdict.VERIFIED,
                record.received_at,
                measured={
                    "pip_position": record.pip_position,
                    "pip_size_num": magnitude.numerator,
                    "pip_size_den": magnitude.denominator,
                },
                detail="the declared pip size satisfies pip_size == 10**-pip_position",
            )
        return self._fact(
            check,
            ProbeVerdict.REFUSED,
            record.received_at,
            detail="the declared pip size fails pip_size == 10**-pip_position; "
            "metadata parameters refused",
        )

    def _check_money_exponent(self, run_instant: Instant) -> MeasuredFact:
        """Require the account's ``money_digits`` exponent (DEC-0135).

        An absent exponent is recorded ``unverified`` — the money decode stays
        unavailable and is never defaulted to 2.
        """
        check = ProbeCheck.MONEY_EXPONENT
        fetched = self.transport.fetch_account_money_record()
        if is_refusal(fetched):
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                run_instant,
                detail="account money record unavailable; the money exponent could not be read",
            )
        record = fetched.value
        if record.money_digits is None:
            return self._fact(
                check,
                ProbeVerdict.UNVERIFIED,
                record.received_at,
                detail="the account carries no money exponent; the money decode stays "
                "unavailable, never defaulted",
            )
        return self._fact(
            check,
            ProbeVerdict.VERIFIED,
            record.received_at,
            measured={"money_digits": record.money_digits},
            detail="the account's money exponent is present and recorded",
        )

    # -- findings ------------------------------------------------------------

    def _findings(self, profile: VenueObservationProfile) -> FindingsNote:
        """Weigh each upstream assumption against the recorded facts (SC-02).

        A verified measurement that disagrees with a claim is a contradiction surfaced
        for amendment; an unverified or refused check leaves the claim open.
        """
        findings: list[Finding] = []
        for assumption in self.upstream_assumptions:
            findings.append(_finding_for(assumption, profile))
        return FindingsNote(findings=tuple(findings))


# --- module-level helpers ---------------------------------------------------


def _finding_for(assumption: UpstreamAssumption, profile: VenueObservationProfile) -> Finding:
    """One findings line for an assumption weighed against the profile."""
    check = _coerce_check(assumption.key)
    if check is None:
        return Finding(
            check=None,
            assumption_key=assumption.key,
            claimed_value=assumption.claimed_value,
            measured_summary="",
            contradicts=False,
            detail="the assumption key names no probe check; nothing measured to weigh it against",
        )
    fact = profile.latest_for(check)
    if fact is None or fact.verdict is not ProbeVerdict.VERIFIED:
        verdict = fact.verdict.value if fact is not None else "unmeasured"
        return Finding(
            check=check,
            assumption_key=assumption.key,
            claimed_value=assumption.claimed_value,
            measured_summary="",
            contradicts=False,
            detail=f"the {check.value} check is {verdict}; the upstream claim stays open "
            "for amendment",
        )
    measured_summary = fact.summary()
    contradicts = measured_summary != assumption.claimed_value
    detail = (
        f"measured '{measured_summary}' contradicts the upstream claim "
        f"'{assumption.claimed_value}' ({assumption.source_note}); surfaced for amendment"
        if contradicts
        else f"measured '{measured_summary}' agrees with the upstream claim"
    )
    return Finding(
        check=check,
        assumption_key=assumption.key,
        claimed_value=assumption.claimed_value,
        measured_summary=measured_summary,
        contradicts=contradicts,
        detail=detail,
    )


def _coerce_check(value: str) -> ProbeCheck | None:
    """Resolve a check-key string to a :class:`ProbeCheck`, or ``None``."""
    try:
        return ProbeCheck(value)
    except ValueError:
        return None


def _coerce_assumptions(
    value: object,
) -> Result[tuple[UpstreamAssumption, ...]]:
    """Validate the optional upstream-assumptions sequence, returning value-or-refusal."""
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "upstream_assumptions",
            "upstream assumptions are a sequence of UpstreamAssumption",
            given=repr(value),
        )
    resolved: list[UpstreamAssumption] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, UpstreamAssumption):
            return _invalid(
                "upstream_assumptions",
                "each upstream assumption is an UpstreamAssumption value",
                index=index,
                given=repr(item),
            )
        resolved.append(item)
    return Ok(tuple(resolved))


def _ohlc_from_ticks(bar: Trendbar, ticks: tuple[Tick, ...]) -> tuple[int, int, int, int] | None:
    """Derive ``(open, high, low, close)`` from the ticks inside a bar's D1 period.

    Returns ``None`` when no tick falls in ``[anchor, anchor + one day)`` — the period
    cannot be reconciled. Ticks are ordered by their minute anchor (stable), so the
    first and last give open and close; the extremes give high and low.
    """
    start = bar.utc_timestamp_in_minutes
    end = start + _MINUTES_PER_DAY
    inside = [tick for tick in ticks if start <= tick.utc_timestamp_in_minutes < end]
    if not inside:
        return None
    ordered = sorted(inside, key=lambda tick: tick.utc_timestamp_in_minutes)
    prices = [tick.price_wire for tick in ordered]
    return (prices[0], max(prices), min(prices), prices[-1])
