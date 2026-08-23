"""Story 10.9 — CT-31 control windows: entries-only, instrument-scoped, fail-closed.

One control-window contract for every no-trade band (AD-38; DEC-0152): news,
``daily_dead_zone``, and ``session_handover_buffer``. A window record carries two
instants (never an offset), a resolved instrument scope, a kind, a reason class, a
format version, and — where feed-derived — the external-fact quadruple
``(source, source-native event id, revision, known-at)``.

* :class:`WindowKind` / :class:`AnchorSide` — the ratified kinds and the mandatory
  handover anchor side (structure, not width);
* :class:`FeedQuadruple` / :class:`WindowBounds` / :class:`ControlWindowRecord` —
  the CT-31 record surface;
* :class:`CurrencyExposureRecord` / :func:`resolve_instrument_scope` — scope is
  declared never parsed; a missing exposure record is treated-as-affected;
* :func:`check_window_blocks_act` / :func:`evaluate_entry_under_windows` —
  entries-only, live and paper alike; never an exit, amendment, protection action,
  or observation;
* :func:`fold_effective_window` — widen-never-shrink forward-only read-time fold;
* :func:`fail_closed_on_uncertainty` — failed calendar refresh / unknown coverage /
  uncertain window blocks; no live skip button;
* :class:`WindowForcedFlatPolicy` — Book declaration entering arbitration as
  ``window_forced_flat`` (declaring none is the V1 posture);
* configurable UI-editable variable *names* with no spine value (DEC-0157).

qmf-risk imports **only** ``qmf-core`` (default-deny, L30/DEC-0120) and sibling
``qmf.risk`` modules; nothing imports ``qmf.risk``. Ratified ``defined-unwired``
surface — no live binding or order is authorized here (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    CalendarIdentity,
    Fingerprint,
    Instant,
    Instrument,
    Interval,
    Result,
    TypedRefusal,
    fingerprint,
    is_refusal,
)
from qmf.core import (
    Ok as _Ok,
)
from qmf.risk._common import (
    clean_str,
    coerce_enum,
    invalid,
    policy,
    type_name,
    unavailable,
    unsupported,
)
from qmf.risk.paper import BookMode, TriggerDisposition

__all__ = [
    "CT31_CONTRACT_FORMAT_VERSION",
    "DAILY_DEAD_ZONE_WIDTH_VARIABLE",
    "NEWS_BLACKOUT_AFTER_VARIABLE",
    "NEWS_BLACKOUT_BEFORE_VARIABLE",
    "PROTECTION_WINDOW_VARIABLE_NAMES",
    "RATIFIED_WINDOW_KINDS",
    "SESSION_HANDOVER_BUFFER_ANCHOR_VARIABLE",
    "SESSION_HANDOVER_BUFFER_WIDTH_VARIABLE",
    "WINDOW_EFFECT",
    "WINDOW_FORCED_FLAT_ARBITRATION_RANK",
    "WINDOW_FORCED_FLAT_VARIABLE",
    "WINDOW_TRIGGER_DISPOSITION",
    "AnchorSide",
    "ControlWindowRecord",
    "ControlWindowRevisionLog",
    "CurrencyExposureRecord",
    "EffectiveWindow",
    "FailClosedCause",
    "FeedQuadruple",
    "ProposedWindowAct",
    "ResolvedInstrumentScope",
    "ScopeResolutionDisposition",
    "StandingExemptionRecord",
    "VetoDecisionRecord",
    "WindowBounds",
    "WindowEffect",
    "WindowEvaluation",
    "WindowForcedFlatPolicy",
    "WindowKind",
    "append_window_revision",
    "check_window_blocks_act",
    "evaluate_entry_under_windows",
    "fail_closed_on_uncertainty",
    "fold_effective_window",
    "instrument_in_scope",
    "mint_control_window",
    "mint_veto_decision",
    "reject_click_exemption",
    "reject_live_skip",
    "reject_symbol_currency_parse",
    "resolve_instrument_scope",
    "window_in_force_at",
]

CT31_CONTRACT_FORMAT_VERSION: Final[int] = 1

# Configurable UI-editable variable names — recorded evidence, never spine values
# (DEC-0152, DEC-0157). Widths/anchors/buffers live in Book templates; this module
# never embeds a numeric default.
NEWS_BLACKOUT_BEFORE_VARIABLE: Final[str] = "news_blackout_before"
NEWS_BLACKOUT_AFTER_VARIABLE: Final[str] = "news_blackout_after"
DAILY_DEAD_ZONE_WIDTH_VARIABLE: Final[str] = "daily_dead_zone_width"
SESSION_HANDOVER_BUFFER_WIDTH_VARIABLE: Final[str] = "session_handover_buffer_width"
SESSION_HANDOVER_BUFFER_ANCHOR_VARIABLE: Final[str] = "session_handover_buffer_anchor"
WINDOW_FORCED_FLAT_VARIABLE: Final[str] = "window_forced_flat"

PROTECTION_WINDOW_VARIABLE_NAMES: Final[frozenset[str]] = frozenset(
    {
        NEWS_BLACKOUT_BEFORE_VARIABLE,
        NEWS_BLACKOUT_AFTER_VARIABLE,
        DAILY_DEAD_ZONE_WIDTH_VARIABLE,
        SESSION_HANDOVER_BUFFER_WIDTH_VARIABLE,
        SESSION_HANDOVER_BUFFER_ANCHOR_VARIABLE,
        WINDOW_FORCED_FLAT_VARIABLE,
    }
)

# Structural arbitration rung for a Book-declared window_forced_flat (AD-37/AD-38).
# Declaring none is the V1 posture — this constant names the rung, never a BMS value.
WINDOW_FORCED_FLAT_ARBITRATION_RANK: Final[int] = 2

# A protection window is a market-risk control: blocks paper exactly as live (DEC-0149).
WINDOW_TRIGGER_DISPOSITION: Final[TriggerDisposition] = TriggerDisposition.BLOCKS_PAPER


# --- closed vocabularies -----------------------------------------------------


class WindowKind(StrEnum):
    """Ratified control-window kinds — addable never redefined (DEC-0152).

    ``news`` — feed-derived no-trade band. ``daily_dead_zone`` — the daily band in
    which no session is meaningfully in the market. ``session_handover_buffer`` —
    the pause around a session handover (distinct from the daily dead zone). Every
    kind is calendar-derived and therefore absent for 24/7 markets.
    """

    NEWS = "news"
    DAILY_DEAD_ZONE = "daily_dead_zone"
    SESSION_HANDOVER_BUFFER = "session_handover_buffer"


RATIFIED_WINDOW_KINDS: Final[frozenset[WindowKind]] = frozenset(WindowKind)


class AnchorSide(StrEnum):
    """Mandatory ``session_handover_buffer`` anchor side — structure, not width.

    ``pre-close | post-open | both``. Without this field, "around a handover" yields
    two different windows from one calendar (DEC-0152).
    """

    PRE_CLOSE = "pre-close"
    POST_OPEN = "post-open"
    BOTH = "both"


class WindowEffect(StrEnum):
    """The only effect a window may have — entries-only (DEC-0152, DEC-0150)."""

    ENTRIES_ONLY = "entries-only"


WINDOW_EFFECT: Final[WindowEffect] = WindowEffect.ENTRIES_ONLY


class ProposedWindowAct(StrEnum):
    """Acts evaluated against a window — only ``entry`` is blocked (DEC-0152)."""

    ENTRY = "entry"
    EXIT = "exit"
    AMEND_PROTECTION = "amend_protection"
    PROTECTION_ACTION = "protection_action"
    RECORD_EVIDENCE = "record_evidence"


class FailClosedCause(StrEnum):
    """Fail-closed dispositions — no live skip button (DEC-0152)."""

    FAILED_CALENDAR_REFRESH = "failed_calendar_refresh"
    UNKNOWN_COVERAGE = "unknown_coverage"
    UNCERTAIN_WINDOW = "uncertain_window"


class ScopeResolutionDisposition(StrEnum):
    """How an instrument related to a window's exposure set (DEC-0152)."""

    IN_SCOPE = "in_scope"
    OUT_OF_SCOPE = "out_of_scope"
    TREATED_AS_AFFECTED_MISSING_EXPOSURE = "treated-as-affected-missing-exposure"


# --- feed quadruple and bounds -----------------------------------------------


@dataclass(frozen=True, slots=True)
class FeedQuadruple:
    """External-fact quadruple where a window derives from a feed (AD-19/AD-21).

    ``(source, source-native event id, revision, known-at)``. Absent for a purely
    calendar-derived window — the key is omitted, never null (DEC-0152).
    """

    source: str
    source_native_event_id: str
    revision: str
    known_at: Instant

    @classmethod
    def try_create(
        cls,
        source: object,
        source_native_event_id: object,
        revision: object,
        known_at: object,
    ) -> Result[FeedQuadruple]:
        """Validate and build a :class:`FeedQuadruple`, value-or-refusal."""
        src = clean_str(source)
        if src is None:
            return invalid(
                "source",
                "a feed-derived window names a non-empty opaque source",
                given=repr(source),
            )
        event_id = clean_str(source_native_event_id)
        if event_id is None:
            return invalid(
                "source_native_event_id",
                "a feed-derived window carries the provider's source-native event id",
                given=repr(source_native_event_id),
            )
        rev = clean_str(revision)
        if rev is None:
            return invalid(
                "revision",
                "a feed-derived window carries a non-empty revision token",
                given=repr(revision),
            )
        if not isinstance(known_at, Instant):
            return invalid(
                "known_at",
                "known-at is an Instant (int64 UTC ns); intake identity is AD-21",
                given=repr(known_at),
            )
        return _Ok(
            cls(
                source=src,
                source_native_event_id=event_id,
                revision=rev,
                known_at=known_at,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the feed quadruple."""
        return {
            "class": "feed-quadruple",
            "source": self.source,
            "source_native_event_id": self.source_native_event_id,
            "revision": self.revision,
            "known_at": self.known_at.fp1_identity(),
            "format_version": CT31_CONTRACT_FORMAT_VERSION,
        }

    def occurrence_key(self) -> tuple[str, str]:
        """Provider occurrence key ``(source, source-native id)`` — revisions append."""
        return (self.source, self.source_native_event_id)


@dataclass(frozen=True, slots=True)
class WindowBounds:
    """A window as two instants — never an offset (DEC-0152).

    Offsets stored instead of bounds would make a record's meaning depend on a
    policy version and break replay. Widths exist only as UI-editable configuration
    the operator sets between sessions; the record itself always carries instants.
    """

    start: Instant
    end: Instant

    @classmethod
    def try_create(cls, start: object, end: object) -> Result[WindowBounds]:
        """Validate and build :class:`WindowBounds` from two Instants."""
        if not isinstance(start, Instant):
            return invalid(
                "start",
                "a window bound start is an Instant (two instants, never an offset)",
                given=repr(start),
            )
        if not isinstance(end, Instant):
            return invalid(
                "end",
                "a window bound end is an Instant (two instants, never an offset)",
                given=repr(end),
            )
        if start.value_ns > end.value_ns:
            return invalid(
                "window_bounds",
                "window start must not fall after end",
                start=start.value_ns,
                end=end.value_ns,
            )
        return _Ok(cls(start=start, end=end))

    @classmethod
    def from_interval(cls, interval: object) -> Result[WindowBounds]:
        """Build bounds from a CT-02 :class:`~qmf.core.Interval`."""
        if not isinstance(interval, Interval):
            return invalid(
                "interval",
                "WindowBounds.from_interval reads a CT-02 Interval",
                given=repr(interval),
            )
        return cls.try_create(interval.start, interval.end)

    def as_interval(self) -> Result[Interval]:
        """The half-open CT-02 interval view of these bounds."""
        return Interval.try_create(self.start, self.end)

    def contains(self, instant: object) -> Result[bool]:
        """Whether ``instant`` lies in ``[start, end)``."""
        interval = self.as_interval()
        if is_refusal(interval):
            return interval
        return interval.value.contains(instant)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — two instant ns counts."""
        return {
            "class": "window-bounds",
            "start_ns": self.start.value_ns,
            "end_ns": self.end.value_ns,
            "format_version": CT31_CONTRACT_FORMAT_VERSION,
        }


# --- currency exposure and instrument scope ----------------------------------


@dataclass(frozen=True, slots=True)
class CurrencyExposureRecord:
    """Dated per-instrument currency-exposure metadata (AD-9; DEC-0152).

    A set of opaque currency tokens — venue-populated where metadata exists,
    operator-declarable and correctable otherwise. Reading a currency out of a
    symbol is prohibited; a missing record means treated-as-affected.
    """

    instrument: Instrument
    exposures: frozenset[str]
    as_of: Instant
    record_id: str

    @classmethod
    def try_create(
        cls,
        instrument: object,
        exposures: object,
        as_of: object,
        record_id: object,
    ) -> Result[CurrencyExposureRecord]:
        """Validate and build a :class:`CurrencyExposureRecord`, value-or-refusal."""
        if not isinstance(instrument, Instrument):
            return invalid(
                "instrument",
                "a currency-exposure record points at an Instrument identity",
                given=repr(instrument),
            )
        if not isinstance(as_of, Instant):
            return invalid(
                "as_of",
                "a currency-exposure record is dated with an Instant",
                given=repr(as_of),
            )
        rid = clean_str(record_id)
        if rid is None:
            return invalid(
                "record_id",
                "a currency-exposure record carries a non-empty opaque record id",
                given=repr(record_id),
            )
        tokens = _coerce_currency_set(exposures)
        if isinstance(tokens, TypedRefusal):
            return tokens
        return _Ok(
            cls(
                instrument=instrument,
                exposures=tokens,
                as_of=as_of,
                record_id=rid,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the exposure record."""
        return {
            "class": "currency-exposure-record",
            "instrument": {
                "venue": self.instrument.venue.value,
                "symbol": self.instrument.symbol,
            },
            "exposures": sorted(self.exposures),
            "as_of": self.as_of.fp1_identity(),
            "record_id": self.record_id,
            "format_version": CT31_CONTRACT_FORMAT_VERSION,
        }


def _coerce_currency_set(value: object) -> frozenset[str] | TypedRefusal:
    """Resolve an exposure set to opaque currency tokens, or a refusal."""
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "exposures",
            "currency exposures are a collection of opaque currency tokens",
            given=given,
        )
    tokens: set[str] = set()
    for item in cast("Iterable[object]", value):
        token = clean_str(item)
        if token is None:
            return invalid(
                "exposures",
                "each currency exposure is a non-empty opaque token; never parsed from a symbol",
                given=repr(item),
            )
        tokens.add(token)
    return frozenset(tokens)


def reject_symbol_currency_parse(symbol: object) -> Result[None]:
    """Refuse deriving currency scope by parsing a symbol (AD-9; DEC-0152).

    Instrument scope is declared through currency-exposure records. Any attempt to
    read a currency out of a venue symbol is a ``policy rejection``.
    """
    token = clean_str(symbol)
    if token is None:
        return invalid(
            "symbol",
            "symbol-parse rejection names the opaque venue symbol that must not be parsed",
            given=repr(symbol),
        )
    return policy(
        "instrument_scope",
        "reading a currency out of a symbol is prohibited; scope resolves through "
        "dated per-instrument currency-exposure records",
        symbol=token,
    )


@dataclass(frozen=True, slots=True)
class ResolvedInstrumentScope:
    """The resolved set of instruments a window affects (DEC-0152).

    Built from declared currency-exposure records — never from symbol parsing.
    Instruments whose exposure record is missing are listed separately as
    treated-as-affected so the absence can be journaled as data quality.
    """

    instruments: frozenset[Instrument]
    treated_as_affected_missing_exposure: frozenset[Instrument]
    affected_currencies: frozenset[str]

    def all_blocked(self) -> frozenset[Instrument]:
        """In-scope instruments union missing-exposure treated-as-affected."""
        return self.instruments | self.treated_as_affected_missing_exposure

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the resolved scope."""
        return {
            "class": "resolved-instrument-scope",
            "instruments": sorted(
                ({"venue": i.venue.value, "symbol": i.symbol} for i in self.instruments),
                key=lambda row: (row["venue"], row["symbol"]),
            ),
            "treated_as_affected_missing_exposure": sorted(
                (
                    {"venue": i.venue.value, "symbol": i.symbol}
                    for i in self.treated_as_affected_missing_exposure
                ),
                key=lambda row: (row["venue"], row["symbol"]),
            ),
            "affected_currencies": sorted(self.affected_currencies),
            "format_version": CT31_CONTRACT_FORMAT_VERSION,
        }


def resolve_instrument_scope(
    *,
    affected_currencies: object,
    candidate_instruments: object,
    exposure_records: object,
) -> Result[ResolvedInstrumentScope]:
    """Resolve window instrument scope through currency-exposure records (DEC-0152).

    An instrument whose exposures intersect ``affected_currencies`` is in scope. A
    candidate with no exposure record is **treated as affected** (blocked) and
    flagged for data-quality journaling — never silently passed. A multi-instrument
    bot is blocked only on the instruments this fold places in scope.
    """
    currencies = _coerce_currency_set(affected_currencies)
    if isinstance(currencies, TypedRefusal):
        return currencies
    if not currencies:
        return invalid(
            "affected_currencies",
            "scope resolution needs a non-empty set of opaque affected-currency tokens",
        )
    instruments = _coerce_instrument_set(candidate_instruments, field="candidate_instruments")
    if isinstance(instruments, TypedRefusal):
        return instruments
    records = _coerce_exposure_records(exposure_records)
    if isinstance(records, TypedRefusal):
        return records

    by_instrument: dict[tuple[str, str], CurrencyExposureRecord] = {
        (rec.instrument.venue.value, rec.instrument.symbol): rec for rec in records
    }
    in_scope: set[Instrument] = set()
    missing: set[Instrument] = set()
    for instrument in instruments:
        key = (instrument.venue.value, instrument.symbol)
        record = by_instrument.get(key)
        if record is None:
            missing.add(instrument)
            continue
        if record.exposures & currencies:
            in_scope.add(instrument)
    return _Ok(
        ResolvedInstrumentScope(
            instruments=frozenset(in_scope),
            treated_as_affected_missing_exposure=frozenset(missing),
            affected_currencies=currencies,
        )
    )


def _coerce_instrument_set(value: object, *, field: str) -> frozenset[Instrument] | TypedRefusal:
    """Resolve a collection of :class:`Instrument` values."""
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            field,
            "instrument scope is a collection of Instrument identities",
            given=given,
        )
    items: set[Instrument] = set()
    for item in cast("Iterable[object]", value):
        if not isinstance(item, Instrument):
            return invalid(field, "each scoped instrument is an Instrument", given=repr(item))
        items.add(item)
    return frozenset(items)


def _coerce_exposure_records(
    value: object,
) -> tuple[CurrencyExposureRecord, ...] | TypedRefusal:
    """Resolve a collection of currency-exposure records (empty is legal)."""
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "exposure_records",
            "exposure_records is a collection of CurrencyExposureRecord values",
            given=given,
        )
    items: list[CurrencyExposureRecord] = []
    for item in cast("Iterable[object]", value):
        if not isinstance(item, CurrencyExposureRecord):
            return invalid(
                "exposure_records",
                "each exposure record is a CurrencyExposureRecord",
                given=repr(item),
            )
        items.append(item)
    return tuple(items)


def instrument_in_scope(scope: object, instrument: object) -> Result[ScopeResolutionDisposition]:
    """Classify whether ``instrument`` is blocked by ``scope`` (DEC-0152)."""
    if not isinstance(scope, ResolvedInstrumentScope):
        return invalid(
            "scope",
            "instrument_in_scope reads a ResolvedInstrumentScope",
            given=repr(scope),
        )
    if not isinstance(instrument, Instrument):
        return invalid(
            "instrument",
            "instrument_in_scope reads an Instrument",
            given=repr(instrument),
        )
    if instrument in scope.treated_as_affected_missing_exposure:
        return _Ok(ScopeResolutionDisposition.TREATED_AS_AFFECTED_MISSING_EXPOSURE)
    if instrument in scope.instruments:
        return _Ok(ScopeResolutionDisposition.IN_SCOPE)
    return _Ok(ScopeResolutionDisposition.OUT_OF_SCOPE)


# --- the control-window record -----------------------------------------------


@dataclass(frozen=True, slots=True)
class ControlWindowRecord:
    """One CT-31 control-window record — a two-instant no-trade band (DEC-0152).

    Carries ``window_bounds`` (two instants), ``window_kind``, resolved
    ``instrument_scope``, ``reason_class``, ``format_version``, calendar identity,
    optional ``feed_quadruple`` (feed-derived only), optional ``anchor_side``
    (``session_handover_buffer`` only), and optional verbatim ``provider_impact_label``.
    The effective window at a decision instant is never stored — it is the
    widen-never-shrink read-time fold.
    """

    window_bounds: WindowBounds
    window_kind: WindowKind
    instrument_scope: ResolvedInstrumentScope
    reason_class: str
    calendar_identity: CalendarIdentity
    window_id: str
    feed_quadruple: FeedQuadruple | None = None
    anchor_side: AnchorSide | None = None
    provider_impact_label: str | None = None
    enabled_by_book: bool = True

    @classmethod
    def try_create(
        cls,
        window_bounds: object,
        window_kind: object,
        instrument_scope: object,
        reason_class: object,
        calendar_identity: object,
        window_id: object,
        *,
        feed_quadruple: object = None,
        anchor_side: object = None,
        provider_impact_label: object = None,
        enabled_by_book: object = True,
    ) -> Result[ControlWindowRecord]:
        """Validate and build a :class:`ControlWindowRecord`, value-or-refusal."""
        if not isinstance(window_bounds, WindowBounds):
            return invalid(
                "window_bounds",
                "a window carries two Instants as WindowBounds, never an offset",
                given=repr(window_bounds),
            )
        kind = coerce_enum(WindowKind, window_kind)
        if kind is None:
            return unsupported(
                "window_kind",
                "window kinds are addable never redefined; V1 ratifies "
                "news|daily_dead_zone|session_handover_buffer",
                given=repr(window_kind),
                allowed=[member.value for member in WindowKind],
            )
        if not isinstance(instrument_scope, ResolvedInstrumentScope):
            return invalid(
                "instrument_scope",
                "a window carries a ResolvedInstrumentScope declared through "
                "currency-exposure records",
                given=repr(instrument_scope),
            )
        reason = clean_str(reason_class)
        if reason is None:
            return invalid(
                "reason_class",
                "a window carries a typed reason class",
                given=repr(reason_class),
            )
        if not isinstance(calendar_identity, CalendarIdentity):
            return invalid(
                "calendar_identity",
                "every kind is calendar-derived — market-hours calendar identity + "
                "tzdata, never device or broker location",
                given=repr(calendar_identity),
            )
        wid = clean_str(window_id)
        if wid is None:
            return invalid(
                "window_id",
                "a window record carries a non-empty opaque window id",
                given=repr(window_id),
            )
        if not isinstance(enabled_by_book, bool):
            return invalid(
                "enabled_by_book",
                "a Book declares which kinds it enables as a boolean on the record",
                given=repr(enabled_by_book),
            )

        feed: FeedQuadruple | None = None
        if feed_quadruple is not None:
            if not isinstance(feed_quadruple, FeedQuadruple):
                return invalid(
                    "feed_quadruple",
                    "feed_quadruple is a FeedQuadruple when present; omitted for a "
                    "purely calendar-derived window (never null)",
                    given=repr(feed_quadruple),
                )
            feed = feed_quadruple

        resolved_anchor: AnchorSide | None = None
        if kind is WindowKind.SESSION_HANDOVER_BUFFER:
            resolved_anchor = coerce_enum(AnchorSide, anchor_side)
            if resolved_anchor is None:
                return invalid(
                    "anchor_side",
                    "session_handover_buffer declares its anchor side as a mandatory "
                    "field — pre-close|post-open|both",
                    given=repr(anchor_side),
                    allowed=[member.value for member in AnchorSide],
                )
        elif anchor_side is not None:
            return invalid(
                "anchor_side",
                "anchor_side is present only for session_handover_buffer; a "
                "kind-inappropriate field is an omitted key, never null",
                window_kind=kind.value,
                given=repr(anchor_side),
            )

        impact: str | None = None
        if provider_impact_label is not None:
            impact = clean_str(provider_impact_label)
            if impact is None:
                return invalid(
                    "provider_impact_label",
                    "provider impact labels are stored verbatim as non-empty tokens "
                    "when present; QMX mints no severity scale in V1",
                    given=repr(provider_impact_label),
                )

        return _Ok(
            cls(
                window_bounds=window_bounds,
                window_kind=kind,
                instrument_scope=instrument_scope,
                reason_class=reason,
                calendar_identity=calendar_identity,
                window_id=wid,
                feed_quadruple=feed,
                anchor_side=resolved_anchor,
                provider_impact_label=impact,
                enabled_by_book=enabled_by_book,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity — optional keys only when present."""
        content: dict[str, object] = {
            "class": "control-window-record",
            "window_id": self.window_id,
            "window_bounds": self.window_bounds.fp1_identity(),
            "window_kind": self.window_kind.value,
            "instrument_scope": self.instrument_scope.fp1_identity(),
            "reason_class": self.reason_class,
            "calendar_identity": self.calendar_identity.fp1_identity(),
            "effect": WINDOW_EFFECT.value,
            "enabled_by_book": self.enabled_by_book,
            "format_version": CT31_CONTRACT_FORMAT_VERSION,
        }
        if self.feed_quadruple is not None:
            content["feed_quadruple"] = self.feed_quadruple.fp1_identity()
        if self.anchor_side is not None:
            content["anchor_side"] = self.anchor_side.value
        if self.provider_impact_label is not None:
            content["provider_impact_label"] = self.provider_impact_label
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """The control-window record's ``fp1`` over its full canonical content."""
        return fingerprint(self.fp1_identity())


def mint_control_window(
    window_bounds: object,
    window_kind: object,
    instrument_scope: object,
    reason_class: object,
    calendar_identity: object,
    window_id: object,
    *,
    feed_quadruple: object = None,
    anchor_side: object = None,
    provider_impact_label: object = None,
    enabled_by_book: object = True,
) -> Result[ControlWindowRecord]:
    """Mint a CT-31 control-window record (DEC-0152)."""
    return ControlWindowRecord.try_create(
        window_bounds,
        window_kind,
        instrument_scope,
        reason_class,
        calendar_identity,
        window_id,
        feed_quadruple=feed_quadruple,
        anchor_side=anchor_side,
        provider_impact_label=provider_impact_label,
        enabled_by_book=enabled_by_book,
    )


def window_in_force_at(window: object, decision_at: object) -> Result[bool]:
    """Whether ``window``'s stored bounds contain ``decision_at`` and the Book enables it."""
    if not isinstance(window, ControlWindowRecord):
        return invalid(
            "window",
            "window_in_force_at reads a ControlWindowRecord",
            given=repr(window),
        )
    if not isinstance(decision_at, Instant):
        return invalid(
            "decision_at",
            "in-force tests an Instant decision time",
            given=repr(decision_at),
        )
    if not window.enabled_by_book:
        return _Ok(False)
    return window.window_bounds.contains(decision_at)


# --- entries-only effect -----------------------------------------------------


def check_window_blocks_act(*, proposed_act: object) -> Result[None]:
    """Enforce entries-only: a window may block only new entries (DEC-0152).

    Naming ``entry`` returns ``Ok(None)`` (the act *may* be blocked). Naming any
    other ratified act is a ``policy rejection`` — a window never blocks an exit,
    protection amendment, protection action, or observation.
    """
    resolved = coerce_enum(ProposedWindowAct, proposed_act)
    if resolved is None:
        return invalid(
            "proposed_act",
            "window effect reads a ProposedWindowAct",
            given=repr(proposed_act),
            allowed=[member.value for member in ProposedWindowAct],
        )
    if resolved is ProposedWindowAct.ENTRY:
        return _Ok(None)
    return policy(
        "proposed_act",
        "a window blocks new entries on in-scope instruments and nothing else — "
        "never an exit, a protection amendment, a protection action, or the "
        "recording of evidence",
        act=resolved.value,
        effect=WINDOW_EFFECT.value,
    )


@dataclass(frozen=True, slots=True)
class WindowEvaluation:
    """Outcome of evaluating a proposed entry against in-force windows (DEC-0152)."""

    blocked: bool
    controlling_window: ControlWindowRecord | None
    scope_disposition: ScopeResolutionDisposition | None
    book_mode: BookMode
    refuse_door: str
    data_quality_alarm: bool


def evaluate_entry_under_windows(
    *,
    instrument: object,
    book_mode: object,
    decision_at: object,
    windows: object,
    proposed_act: object = ProposedWindowAct.ENTRY,
) -> Result[WindowEvaluation]:
    """Evaluate a proposed act against windows in force (DEC-0152, DEC-0149).

    Live and paper entries alike are blocked on in-scope instruments. Non-entry
    acts are refused as a policy violation of the entries-only law (the caller
    must not ask a window to block them). A multi-instrument bot is blocked only
    on instruments this evaluation places in scope.
    """
    if not isinstance(instrument, Instrument):
        return invalid(
            "instrument",
            "entry evaluation is instrument-scoped",
            given=repr(instrument),
        )
    mode = coerce_enum(BookMode, book_mode)
    if mode is None:
        return invalid(
            "book_mode",
            "entry evaluation reads BookMode LIVE|PAPER — both are blocked alike",
            given=repr(book_mode),
            allowed=[member.value for member in BookMode],
        )
    if not isinstance(decision_at, Instant):
        return invalid(
            "decision_at",
            "entry evaluation is at an Instant decision time",
            given=repr(decision_at),
        )
    act_gate = check_window_blocks_act(proposed_act=proposed_act)
    if is_refusal(act_gate):
        return act_gate

    window_list = _coerce_windows(windows)
    if isinstance(window_list, TypedRefusal):
        return window_list

    for window in window_list:
        in_force = window_in_force_at(window, decision_at)
        if is_refusal(in_force):
            return in_force
        if not in_force.value:
            continue
        disposition = instrument_in_scope(window.instrument_scope, instrument)
        if is_refusal(disposition):
            return disposition
        if disposition.value is ScopeResolutionDisposition.OUT_OF_SCOPE:
            continue
        return _Ok(
            WindowEvaluation(
                blocked=True,
                controlling_window=window,
                scope_disposition=disposition.value,
                book_mode=mode,
                refuse_door="control-window",
                data_quality_alarm=(
                    disposition.value
                    is ScopeResolutionDisposition.TREATED_AS_AFFECTED_MISSING_EXPOSURE
                ),
            )
        )
    return _Ok(
        WindowEvaluation(
            blocked=False,
            controlling_window=None,
            scope_disposition=None,
            book_mode=mode,
            refuse_door="control-window",
            data_quality_alarm=False,
        )
    )


def _coerce_windows(value: object) -> tuple[ControlWindowRecord, ...] | TypedRefusal:
    """Resolve a collection of control-window records."""
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(
            "windows",
            "windows is a collection of ControlWindowRecord values",
            given=given,
        )
    items: list[ControlWindowRecord] = []
    for item in cast("Iterable[object]", value):
        if not isinstance(item, ControlWindowRecord):
            return invalid(
                "windows",
                "each window is a ControlWindowRecord",
                given=repr(item),
            )
        items.append(item)
    return tuple(items)


# --- widen-never-shrink fold -------------------------------------------------


@dataclass(frozen=True, slots=True)
class EffectiveWindow:
    """Read-time effective bounds at a decision instant — never a stored field.

    The union of every revision known at ``decision_at``, with passed bounds
    frozen (DEC-0152, DEC-0158).
    """

    window_id: str
    bounds: WindowBounds
    decision_at: Instant
    revision_count: int
    revisions_known: tuple[str, ...]

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the effective window."""
        return {
            "class": "effective-window",
            "window_id": self.window_id,
            "bounds": self.bounds.fp1_identity(),
            "decision_at": self.decision_at.fp1_identity(),
            "revision_count": self.revision_count,
            "revisions_known": list(self.revisions_known),
            "format_version": CT31_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ControlWindowRevisionLog:
    """Append-only revision log for one window occurrence (DEC-0152).

    Intake never refuses a revision (AD-21 keeps provider evidence verbatim).
    Enforcement is the read-time :func:`fold_effective_window`, never intake.
    """

    window_id: str
    revisions: tuple[ControlWindowRecord, ...] = ()

    def append(self, revision: object) -> Result[ControlWindowRevisionLog]:
        """Append a revision — intake never refuses a well-formed record."""
        return append_window_revision(self, revision)


def append_window_revision(log: object, revision: object) -> Result[ControlWindowRevisionLog]:
    """Append a window revision; intake never refuses on narrowing (DEC-0152).

    A later revision that would narrow is still recorded. The widen-never-shrink
    law is enforced only by :func:`fold_effective_window` at read time.
    """
    if not isinstance(log, ControlWindowRevisionLog):
        return invalid(
            "log",
            "append_window_revision reads a ControlWindowRevisionLog",
            given=repr(log),
        )
    if not isinstance(revision, ControlWindowRecord):
        return invalid(
            "revision",
            "a revision is a ControlWindowRecord",
            given=repr(revision),
        )
    if revision.window_id != log.window_id:
        return invalid(
            "window_id",
            "a revision must share the log's window_id",
            log_window_id=log.window_id,
            revision_window_id=revision.window_id,
        )
    return _Ok(
        ControlWindowRevisionLog(
            window_id=log.window_id,
            revisions=(*log.revisions, revision),
        )
    )


def fold_effective_window(revisions: object, *, decision_at: object) -> Result[EffectiveWindow]:
    """Widen-never-shrink read-time fold at ``decision_at`` (DEC-0152, DEC-0158).

    The effective window is the union of the bounds of every revision known at
    ``decision_at`` (feed ``known_at <= decision_at``, or always for calendar-only
    records), with any bound already passed frozen:

    * effective start = minimum start among known revisions;
    * effective end = maximum end among known revisions.

    A third revision narrowing below the first while the second was wider therefore
    resolves identically in every build — the union keeps the wider bounds. Intake
    never refuses; this fold is the sole enforcement point.
    """
    if not isinstance(decision_at, Instant):
        return invalid(
            "decision_at",
            "the effective-window fold is at an Instant decision time",
            given=repr(decision_at),
        )
    records = _coerce_windows(revisions)
    if isinstance(records, TypedRefusal):
        return records
    if not records:
        return invalid(
            "revisions",
            "the effective-window fold needs at least one ControlWindowRecord",
        )

    window_ids = {record.window_id for record in records}
    if len(window_ids) != 1:
        return invalid(
            "revisions",
            "the effective-window fold reads revisions of one window_id",
            window_ids=sorted(window_ids),
        )
    window_id = next(iter(window_ids))

    known: list[ControlWindowRecord] = []
    for record in records:
        if record.feed_quadruple is None:
            known.append(record)
            continue
        if record.feed_quadruple.known_at.value_ns <= decision_at.value_ns:
            known.append(record)
    if not known:
        return unavailable_known_at(decision_at)

    # Union of bounds; passed bounds are frozen by taking min start / max end over
    # every revision knowable at T — a later narrowing revision cannot shrink.
    start_ns = min(record.window_bounds.start.value_ns for record in known)
    end_ns = max(record.window_bounds.end.value_ns for record in known)

    # Freeze: a bound already passed at decision_at cannot be pulled past T in a
    # way that rewrites history — union already prevents narrowing; freeze the
    # start if it has elapsed under an earlier revision that had effect.
    passed_starts = [
        record.window_bounds.start.value_ns
        for record in known
        if record.window_bounds.start.value_ns <= decision_at.value_ns
    ]
    if passed_starts:
        # Once a start has passed, the effective start is the earliest passed start
        # (still widen-only: an earlier pull before T is still taken via min above).
        start_ns = min(start_ns, *passed_starts)

    start = Instant(value_ns=start_ns)
    end = Instant(value_ns=end_ns)
    bounds = WindowBounds.try_create(start, end)
    if is_refusal(bounds):
        return bounds

    revision_tokens: list[str] = []
    for record in known:
        if record.feed_quadruple is not None:
            revision_tokens.append(record.feed_quadruple.revision)
        else:
            revision_tokens.append(record.window_id)

    return _Ok(
        EffectiveWindow(
            window_id=window_id,
            bounds=bounds.value,
            decision_at=decision_at,
            revision_count=len(known),
            revisions_known=tuple(revision_tokens),
        )
    )


def unavailable_known_at(decision_at: Instant) -> TypedRefusal:
    """No revision was knowable at ``decision_at`` — fail closed via caller."""
    return unavailable(
        "revisions",
        "no window revision is knowable at the decision instant; fail closed",
        decision_at_ns=decision_at.value_ns,
    )


# --- fail closed / exemptions ------------------------------------------------


def fail_closed_on_uncertainty(*, cause: object) -> Result[None]:
    """Fail closed: uncertain coverage blocks; there is no live skip (DEC-0152).

    Returns a ``policy rejection`` naming the cause so the door blocks the entry.
    """
    resolved = coerce_enum(FailClosedCause, cause)
    if resolved is None:
        return invalid(
            "cause",
            "fail-closed reads a FailClosedCause",
            given=repr(cause),
            allowed=[member.value for member in FailClosedCause],
        )
    return policy(
        "fail_closed",
        "a failed calendar refresh, unknown coverage, or an uncertain window "
        "blocks; there is no live skip button — the operator's control is "
        "upstream configuration exercised between sessions",
        cause=resolved.value,
    )


def reject_live_skip() -> Result[None]:
    """Refuse a live skip button — fail-closed has no runtime override (DEC-0152)."""
    return policy(
        "live_skip",
        "there is no live skip button; fail-closed windows block until upstream "
        "configuration changes between sessions",
    )


@dataclass(frozen=True, slots=True)
class StandingExemptionRecord:
    """A dated fingerprinted per-instrument exemption — compile-time only (DEC-0152).

    Consumed at compile time, never a click. A runtime click attempt is refused by
    :func:`reject_click_exemption`.
    """

    instrument: Instrument
    exemption_id: str
    as_of: Instant
    content_fingerprint: Fingerprint

    @classmethod
    def try_create(
        cls,
        instrument: object,
        exemption_id: object,
        as_of: object,
        content_fingerprint: object,
    ) -> Result[StandingExemptionRecord]:
        """Validate and build a :class:`StandingExemptionRecord`, value-or-refusal."""
        if not isinstance(instrument, Instrument):
            return invalid(
                "instrument",
                "a standing exemption names an Instrument",
                given=repr(instrument),
            )
        eid = clean_str(exemption_id)
        if eid is None:
            return invalid(
                "exemption_id",
                "a standing exemption carries a non-empty opaque id",
                given=repr(exemption_id),
            )
        if not isinstance(as_of, Instant):
            return invalid(
                "as_of",
                "a standing exemption is a dated record",
                given=repr(as_of),
            )
        if not isinstance(content_fingerprint, Fingerprint):
            return invalid(
                "content_fingerprint",
                "a standing exemption is fingerprinted and consumed at compile time",
                given=repr(content_fingerprint),
            )
        return _Ok(
            cls(
                instrument=instrument,
                exemption_id=eid,
                as_of=as_of,
                content_fingerprint=content_fingerprint,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the exemption."""
        return {
            "class": "standing-exemption-record",
            "instrument": {
                "venue": self.instrument.venue.value,
                "symbol": self.instrument.symbol,
            },
            "exemption_id": self.exemption_id,
            "as_of": self.as_of.fp1_identity(),
            "content_fingerprint": self.content_fingerprint.value,
            "format_version": CT31_CONTRACT_FORMAT_VERSION,
        }


def reject_click_exemption() -> Result[None]:
    """Refuse a runtime click exemption — compile-time records only (DEC-0152)."""
    return policy(
        "exemption",
        "a standing per-instrument exemption is a dated fingerprinted record "
        "consumed at compile time, never a click",
    )


# --- veto-path decision record -----------------------------------------------


@dataclass(frozen=True, slots=True)
class VetoDecisionRecord:
    """A blocked decision on the veto path (DEC-0152, DEC-0150).

    Carries the refusing door, the would-have-been action fingerprint, and the
    controlling window's fingerprint so decay sensing keeps its data points
    without a trade being placed. A window is a door-class refusal, never a
    kill-switch level and never a suppression-path event.
    """

    refusing_door: str
    would_have_been_action_fp: Fingerprint
    controlling_window_fp: Fingerprint
    instrument: Instrument
    book_mode: BookMode
    decision_at: Instant
    reason_class: str

    @classmethod
    def try_create(
        cls,
        refusing_door: object,
        would_have_been_action_fp: object,
        controlling_window_fp: object,
        instrument: object,
        book_mode: object,
        decision_at: object,
        reason_class: object,
    ) -> Result[VetoDecisionRecord]:
        """Validate and build a :class:`VetoDecisionRecord`, value-or-refusal."""
        door = clean_str(refusing_door)
        if door is None:
            return invalid(
                "refusing_door",
                "a veto decision names the refusing door",
                given=repr(refusing_door),
            )
        if not isinstance(would_have_been_action_fp, Fingerprint):
            return invalid(
                "would_have_been_action_fp",
                "a veto decision carries the would-have-been action fingerprint",
                given=repr(would_have_been_action_fp),
            )
        if not isinstance(controlling_window_fp, Fingerprint):
            return invalid(
                "controlling_window_fp",
                "a veto decision carries the controlling window's fingerprint",
                given=repr(controlling_window_fp),
            )
        if not isinstance(instrument, Instrument):
            return invalid(
                "instrument",
                "a veto decision is instrument-scoped",
                given=repr(instrument),
            )
        mode = coerce_enum(BookMode, book_mode)
        if mode is None:
            return invalid(
                "book_mode",
                "a veto decision records BookMode LIVE|PAPER",
                given=repr(book_mode),
            )
        if not isinstance(decision_at, Instant):
            return invalid(
                "decision_at",
                "a veto decision is dated with an Instant",
                given=repr(decision_at),
            )
        reason = clean_str(reason_class)
        if reason is None:
            return invalid(
                "reason_class",
                "a veto decision carries a typed reason class",
                given=repr(reason_class),
            )
        return _Ok(
            cls(
                refusing_door=door,
                would_have_been_action_fp=would_have_been_action_fp,
                controlling_window_fp=controlling_window_fp,
                instrument=instrument,
                book_mode=mode,
                decision_at=decision_at,
                reason_class=reason,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the veto decision."""
        return {
            "class": "veto-decision-record",
            "refusing_door": self.refusing_door,
            "would_have_been_action_fp": self.would_have_been_action_fp.value,
            "controlling_window_fp": self.controlling_window_fp.value,
            "instrument": {
                "venue": self.instrument.venue.value,
                "symbol": self.instrument.symbol,
            },
            "book_mode": self.book_mode.value,
            "decision_at": self.decision_at.fp1_identity(),
            "reason_class": self.reason_class,
            "path": "veto",
            "format_version": CT31_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class WindowForcedFlatPolicy:
    """Whether a window may close open positions — Book declaration (DEC-0152).

    Enters AD-37 arbitration at rank :data:`WINDOW_FORCED_FLAT_ARBITRATION_RANK`
    as ``window_forced_flat``. Declaring none is the V1 posture — a window blocks
    new entries only and never closes a position by implicit effect.
    """

    declares_forced_flat: bool
    arbitration_rank: int = WINDOW_FORCED_FLAT_ARBITRATION_RANK

    @classmethod
    def try_create(
        cls,
        declares_forced_flat: object,
        *,
        arbitration_rank: object = WINDOW_FORCED_FLAT_ARBITRATION_RANK,
    ) -> Result[WindowForcedFlatPolicy]:
        """Validate and build a :class:`WindowForcedFlatPolicy`, value-or-refusal."""
        if not isinstance(declares_forced_flat, bool):
            return invalid(
                "declares_forced_flat",
                "window_forced_flat is a Book boolean declaration",
                given=repr(declares_forced_flat),
            )
        if (
            isinstance(arbitration_rank, bool)
            or not isinstance(arbitration_rank, int)
            or arbitration_rank < 0
        ):
            return invalid(
                "arbitration_rank",
                "window_forced_flat enters arbitration at a non-negative integer rank",
                given=repr(arbitration_rank),
            )
        return _Ok(
            cls(
                declares_forced_flat=declares_forced_flat,
                arbitration_rank=arbitration_rank,
            )
        )

    @classmethod
    def v1_default(cls) -> WindowForcedFlatPolicy:
        """V1 posture — declaring none; entries-only, no implicit flatten."""
        return cls(
            declares_forced_flat=False,
            arbitration_rank=WINDOW_FORCED_FLAT_ARBITRATION_RANK,
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the policy."""
        return {
            "class": "window-forced-flat-policy",
            "declares_forced_flat": self.declares_forced_flat,
            "arbitration_rank": self.arbitration_rank,
            "trigger_class": WINDOW_FORCED_FLAT_VARIABLE,
            "format_version": CT31_CONTRACT_FORMAT_VERSION,
        }


def mint_veto_decision(
    evaluation: object,
    *,
    instrument: object,
    would_have_been_action_fp: object,
    decision_at: object,
) -> Result[VetoDecisionRecord]:
    """Mint a veto-path decision from a blocking evaluation and the blocked instrument."""
    if not isinstance(evaluation, WindowEvaluation):
        return invalid(
            "evaluation",
            "mint_veto_decision reads a WindowEvaluation",
            given=repr(evaluation),
        )
    if not evaluation.blocked or evaluation.controlling_window is None:
        return invalid(
            "evaluation",
            "a veto decision is minted only for a blocked entry under a controlling window",
            blocked=evaluation.blocked,
        )
    if not isinstance(instrument, Instrument):
        return invalid(
            "instrument",
            "a veto decision names the blocked Instrument",
            given=repr(instrument),
        )
    window_fp = evaluation.controlling_window.fingerprint()
    if is_refusal(window_fp):
        return window_fp
    return VetoDecisionRecord.try_create(
        evaluation.refuse_door,
        would_have_been_action_fp,
        window_fp.value,
        instrument,
        evaluation.book_mode,
        decision_at,
        evaluation.controlling_window.reason_class,
    )
