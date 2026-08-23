"""The cTrader adapter — ratified venue facts as per-broker configuration (Story 8.8).

`COMP-QMF-VENUE`'s first adapter (`COMP-CTRADER`): the cTrader Open API reached from
Python, behind the venue-neutral port the sibling modules define. This module honors the
**ratified venue facts as standing obligations** while treating the daily boundary, the
trendbar price basis, and broker identity as **per-broker / deployment configuration** —
so cTrader is adapter #1 with *no broker-specific behavior baked into code* and the
platform stays venue-blind above the port (FR-026, AR-42, AR-46; DEC-0135, DEC-0139).

The cTrader-**platform** facts are documentation-grade and ratified (DEC-0135), so they
are the adapter's standing obligations, named here at their point of use and cited — they
are neither registry values nor the demoted claims:

* Inbound decode (the named money-path conversion boundary; DEC-0105, DEC-0141): per-field
  Unix-ms UTC timestamps with **mandatory receive-time recording** — no server clock
  exists on the Open API (:func:`decode_timestamp`); market-data prices are uint64 in the
  **1/100000** wire scale, stored verbatim as an exact scaled integer
  (:func:`decode_market_data_price`); execution prices are **raw doubles** that cross
  AD-7's named boundary at receipt to a scaled integer at the instrument's declared digits
  under a declared rounding mode, the raw float kept only as provenance
  (:func:`decode_execution_price`); and a ``moneyDigits`` exponent governs the **nine**
  money-bearing messages (:data:`MONEY_BEARING_MESSAGES`), an **absent** exponent refusing
  that message's money decode, never a default to 2 (:func:`decode_money`).
* Connection limits (:class:`RatePacer`, :func:`tick_span_within_cap`): 50 requests/second
  non-historical plus 5/second historical **per connection**, the safe **10-second**
  heartbeat bound, and the **one-week** historical tick-span cap; demo and live are
  separate hosts requiring **two** simultaneous connections (:class:`SessionTopology`).
* Token lifecycle and session duties (:class:`TokenLifecycle`, :data:`SESSION_DUTIES`,
  :class:`SessionRecovery`): a ~30-day access token, a never-expiring refresh token (the
  crown-jewel secret) with cTID re-authorization the invalidation anchor; heartbeat, token
  refresh, reconnect, gap replay, and verification monitors are **declared schedulable
  duties the application's scheduler drives**, and session recovery **never resubmits a
  command** — an in-flight command on disconnect becomes ``UNKNOWN`` (a state) (FR-025).

The measure-per-broker facts are **never hardcoded** (AR-46, DEC-0135): the 17:00-New-York
daily boundary and the BID-derived trendbar basis are demoted 2013-forum-grade claims, so
:class:`CTraderBrokerConfiguration` reads each from the per-``(VenueId, account)``
venue-observation profile (Story 8.1/8.4), verify-or-refuse, and never encodes ``17:00`` or
``BID`` in code. Broker identity is deployment configuration: only opaque ``VenueId`` /
``AccountId`` identity and account bindings are held, and **no broker is named** (DEC-0139).

Stdlib + qmf-core + the sibling venue modules only; nothing imports ``qmf-venue`` (default
-deny, L30/DEC-0120). No binary float touches the money path except through a qmf-core
``from_float`` boundary with a declared rounding mode (CT-01; DEC-0105). Frozen, immutable
values throughout, save the deliberately-stateful :class:`RatePacer` that owns transient
per-connection pacing state (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import ClassVar, Final, TypeVar, cast

from qmf.core import (
    Account,
    CalendarIdentity,
    Instant,
    Instrument,
    Money,
    MonotonicReading,
    Ok,
    Price,
    RefusalCategory,
    Result,
    Retryability,
    RoundingMode,
    TypedRefusal,
    VenueId,
    is_refusal,
)
from qmf.venue.capabilities import CapabilityFieldName
from qmf.venue.commands import SubmissionOutcome, UnknownTrigger
from qmf.venue.observation import (
    ProbeCheck,
    ProbeVerdict,
    VenueEvidenceClass,
    VenueObservationProfile,
)

__all__ = [
    "ACCESS_TOKEN_LIFETIME_CLASS",
    "HEARTBEAT_BOUND_SECONDS",
    "HISTORICAL_RATE_LIMIT_PER_SECOND",
    "HISTORICAL_TICK_SPAN_CAP_MS",
    "INVALIDATION_ANCHOR",
    "MARKET_DATA_WIRE_SCALE_EXPONENT",
    "MONEY_BEARING_MESSAGES",
    "NON_HISTORICAL_RATE_LIMIT_PER_SECOND",
    "REFRESH_TOKEN_LIFETIME_CLASS",
    "SESSION_DUTIES",
    "CTraderAdapter",
    "CTraderBrokerConfiguration",
    "ConnectionEndpoint",
    "DecodedExecutionPrice",
    "DecodedTimestamp",
    "InFlightResolution",
    "RatePacer",
    "RequestClass",
    "SchedulableDuty",
    "SessionDuty",
    "SessionRecovery",
    "SessionTopology",
    "TimestampUnit",
    "TokenLifecycle",
    "VenueEnvironment",
    "decode_execution_price",
    "decode_market_data_price",
    "decode_money",
    "decode_timestamp",
    "tick_span_within_cap",
]

_EnumT = TypeVar("_EnumT", bound=StrEnum)


# --- cTrader-platform documentation-grade facts (DEC-0135) ------------------
#
# These are the ratified cTrader-**platform** venue facts — standing obligations, neither
# registry values nor the demoted per-broker claims (the daily boundary and trendbar basis
# live in the venue-observation profile, never here). Named at their point of use and cited.

# Market-data prices are uint64 in the 1/100000 wire scale — an exact scale-5 integer, the
# declared foreign integer scale stored verbatim (never a /100000 binary-float divide).
MARKET_DATA_WIRE_SCALE_EXPONENT: Final[int] = 5

# Per-connection request-rate ceilings (documentation-grade; DEC-0135). The adapter paces
# itself at or below these; the pacing/backoff CADENCE is a node value (do-not-default).
NON_HISTORICAL_RATE_LIMIT_PER_SECOND: Final[int] = 50
HISTORICAL_RATE_LIMIT_PER_SECOND: Final[int] = 5

# The heartbeat is adopted at the safe 10-second bound (the tighter of the contradicting
# primary sources wins; DEC-0135). The declared inactivity BOUND, not a node cadence.
HEARTBEAT_BOUND_SECONDS: Final[int] = 10

# The documented historical tick-span cap: one week, runtime-enforced as venue error 35.
HISTORICAL_TICK_SPAN_CAP_MS: Final[int] = 7 * 24 * 60 * 60 * 1_000

# The nine money-bearing messages a ``moneyDigits`` exponent governs (DEC-0135, DEC-0141);
# an absent exponent refuses that message's money decode. A closed, addable-never-redefined
# set — a money decode outside these messages is not a moneyDigits decode.
MONEY_BEARING_MESSAGES: Final[frozenset[str]] = frozenset(
    {
        "ProtoOATrader",
        "ProtoOAPosition",
        "ProtoOADeal",
        "ProtoOAClosePositionDetail",
        "ProtoOADepositWithdraw",
        "ProtoOABonusDepositWithdraw",
        "ProtoOAExpectedMarginRes",
        "ProtoOAMarginChangedEvent",
        "ProtoOAGetPositionUnrealizedPnLRes",
    }
)

# The token lifecycle CLASS the adapter presents (CT-18 token_lifecycle_class; DEC-0135).
# The class is declared here; the secret VALUES live only in the connection manager (CT-21).
ACCESS_TOKEN_LIFETIME_CLASS: Final[str] = "approximately-30-day"  # noqa: S105 - a class label, not a secret
REFRESH_TOKEN_LIFETIME_CLASS: Final[str] = "never-expiring"  # noqa: S105 - a class label, not a secret
INVALIDATION_ANCHOR: Final[str] = "ctid-reauthorization"

_ONE_SECOND_NS: Final[int] = 1_000_000_000


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a decode or construction guard returns."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unavailable(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unavailable dependency`` refusal an absent required input returns."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context=context,
    )


def _transient(field_name: str, reason: str, after_condition: str, **extra: object) -> TypedRefusal:
    """Build the ``transient venue failure`` refusal the self-pacer returns over-ceiling.

    Retryable ``after-condition`` — the per-connection rate window regains capacity — never
    a command retry (command retry stays prohibited; DEC-0137).
    """
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.TRANSIENT_VENUE_FAILURE,
        retryability=Retryability.AFTER_CONDITION,
        context=context,
        after_condition_descriptor=after_condition,
    )


# --- helpers ----------------------------------------------------------------


def _coerce(enum_cls: type[_EnumT], value: object) -> _EnumT | None:
    """Return the enum member ``value`` names, or ``None`` if it names none."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return None
    return None


def _as_plain_int(value: object) -> int | None:
    """Return ``value`` as a genuine ``int`` (never a ``bool``), else ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    return None


def _require_instrument(value: object) -> Instrument | None:
    """Return ``value`` if it is a well-formed :class:`~qmf.core.Instrument`, else ``None``."""
    if (
        isinstance(value, Instrument)
        and value.symbol.strip() != ""
        and value.venue.value.strip() != ""
    ):
        return value
    return None


# --- inbound timestamps: per-field Unix-ms, receive-time mandatory ----------


class TimestampUnit(StrEnum):
    """The per-field wire unit of a cTrader timestamp (DEC-0135).

    Timestamps are Unix milliseconds UTC asserted **per field** — there is no global
    platform statement — with named epoch exceptions: trendbar ``utcTimestampInMinutes``
    is minutes, ``maintenanceEndTimestamp`` and the schedule seconds are seconds, and
    ``holidayDate`` is days since epoch. The set is addable, never redefined.
    """

    MILLISECONDS = "milliseconds"
    SECONDS = "seconds"
    MINUTES = "minutes"
    DAYS = "days"


# The exact nanosecond multiplier per wire unit — integer arithmetic only, so a foreign
# timestamp converts to an int64 UTC-nanosecond :class:`~qmf.core.Instant` with no float.
_UNIT_TO_NS: Final[Mapping[TimestampUnit, int]] = MappingProxyType(
    {
        TimestampUnit.MILLISECONDS: 1_000_000,
        TimestampUnit.SECONDS: 1_000_000_000,
        TimestampUnit.MINUTES: 60 * 1_000_000_000,
        TimestampUnit.DAYS: 24 * 60 * 60 * 1_000_000_000,
    }
)


@dataclass(frozen=True, slots=True)
class DecodedTimestamp:
    """A decoded cTrader timestamp plus the mandatory local receive instant (DEC-0135).

    ``instant`` is the wire value converted to a UTC-nanosecond :class:`~qmf.core.Instant`;
    ``raw_value`` and ``unit`` are the verbatim foreign evidence; ``received_at`` is the
    mandatory local receive instant — the Open API exposes **no server clock**, so
    recording a receive time is mandatory on every inbound field (AD-8; DEC-0135).
    """

    instant: Instant
    raw_value: int
    unit: TimestampUnit
    received_at: Instant


def decode_timestamp(
    raw_value: object, unit: object, received_at: object
) -> Result[DecodedTimestamp]:
    """Decode a per-field cTrader timestamp, recording the mandatory receive instant.

    The wire value is converted to a UTC-nanosecond :class:`~qmf.core.Instant` by its
    declared per-field unit (milliseconds by default; minutes/seconds/days for the named
    epoch exceptions). ``received_at`` is **mandatory** — no server clock exists on the
    Open API — so an absent or non-:class:`~qmf.core.Instant` receive time is refused, never
    defaulted. A non-integer wire value, an unknown unit, or an out-of-range instant is an
    ``invalid input`` refusal (DEC-0135, DEC-0106).
    """
    resolved_unit = _coerce(TimestampUnit, unit)
    if resolved_unit is None:
        return _invalid(
            "unit",
            "a cTrader timestamp carries a per-field unit; there is no global unit",
            given=repr(unit),
            allowed=[member.value for member in TimestampUnit],
        )
    raw = _as_plain_int(raw_value)
    if raw is None:
        return _invalid(
            "raw_value",
            "a cTrader timestamp is a foreign integer in its per-field unit",
            given=repr(raw_value),
        )
    if not isinstance(received_at, Instant):
        return _invalid(
            "received_at",
            "recording a local receive instant is mandatory; the Open API exposes no "
            "server clock (DEC-0135)",
            given=repr(received_at),
        )
    built = Instant.try_create(raw * _UNIT_TO_NS[resolved_unit])
    if is_refusal(built):
        return built
    return Ok(
        DecodedTimestamp(
            instant=built.value,
            raw_value=raw,
            unit=resolved_unit,
            received_at=received_at,
        )
    )


# --- the named money-path conversion boundary ------------------------------


def decode_market_data_price(wire_value: object, instrument: object) -> Result[Price]:
    """Decode a market-data wire price (uint64, 1/100000 scale) to an exact Price.

    Market-data prices are uint64 in the **1/100000** wire scale (DEC-0135): the declared
    foreign integer scale, stored verbatim as a scale-5 exact integer — never a binary
    ``/100000`` divide that would corrupt the money path. A non-integer or negative wire
    value (a uint64 is non-negative), or a malformed instrument, is an ``invalid input``
    refusal (CT-01; DEC-0105, DEC-0141).
    """
    value = _as_plain_int(wire_value)
    if value is None or value < 0:
        return _invalid(
            "wire_value",
            "a market-data wire price is a non-negative uint64 in the 1/100000 scale",
            given=repr(wire_value),
        )
    anchor = _require_instrument(instrument)
    if anchor is None:
        return _invalid(
            "instrument",
            "a market-data price is quoted for an instrument; a valid Instrument is required",
            given=repr(instrument),
        )
    return Price.try_create(value, anchor, MARKET_DATA_WIRE_SCALE_EXPONENT)


@dataclass(frozen=True, slots=True)
class DecodedExecutionPrice:
    """An execution price crossed to an exact Price, the raw double kept as provenance.

    Execution prices (position price, stop/target, deal execution price, conversion rates)
    arrive as **raw doubles** (DEC-0135). The double crosses AD-7's named money-path
    boundary at receipt to a scaled integer at the instrument's declared ``digits`` under a
    declared rounding mode; the raw float is retained **only as integrity-checked
    provenance** and is never the value a consumer reads (DEC-0141).
    """

    price: Price
    raw_double: float
    digits: int
    rounding: RoundingMode


def decode_execution_price(
    raw_double: object, instrument: object, digits: object, rounding: object
) -> Result[DecodedExecutionPrice]:
    """Cross a raw execution-price double to an exact Price at the named boundary.

    The raw double crosses AD-7's named boundary through :meth:`Price.from_float` at the
    instrument's declared ``digits`` scale under the caller-declared identity-bearing
    ``rounding`` mode — the sole sanctioned float crossing (CT-01; DEC-0105). The raw float
    is retained as provenance only. A non-float value, a non-integer digits, or an invalid
    rounding mode is refused; NaN and infinity cannot cross (delegated to ``from_float``).
    """
    if not isinstance(raw_double, float):
        return _invalid(
            "raw_double",
            "an execution price is a raw double crossing the named money-path boundary; "
            "an integer wire value uses its own decoder",
            given=repr(raw_double),
        )
    resolved_digits = _as_plain_int(digits)
    if resolved_digits is None or resolved_digits < 0:
        return _invalid(
            "digits",
            "the instrument's declared digits is a non-negative integer scale from the full "
            "symbol record",
            given=repr(digits),
        )
    resolved_rounding = _coerce(RoundingMode, rounding)
    if resolved_rounding is None:
        return _invalid(
            "rounding",
            "the money-path boundary requires a declared, identity-bearing rounding mode",
            given=repr(rounding),
            allowed=[member.value for member in RoundingMode],
        )
    anchor = _require_instrument(instrument)
    if anchor is None:
        return _invalid(
            "instrument",
            "an execution price is quoted for an instrument; a valid Instrument is required",
            given=repr(instrument),
        )
    crossed = Price.from_float(
        raw_double, instrument=anchor, scale=resolved_digits, rounding=resolved_rounding
    )
    if is_refusal(crossed):
        return crossed
    return Ok(
        DecodedExecutionPrice(
            price=crossed.value,
            raw_double=raw_double,
            digits=resolved_digits,
            rounding=resolved_rounding,
        )
    )


def decode_money(
    message: object, raw_units: object, currency: object, money_digits: object
) -> Result[Money]:
    """Decode a money-bearing message's amount under its ``moneyDigits`` exponent.

    Money on the **nine** money-bearing messages (:data:`MONEY_BEARING_MESSAGES`) is an
    integer scaled by a per-account ``moneyDigits`` exponent (DEC-0135). An **absent**
    exponent (``money_digits is None``) refuses that message's money decode — never a
    default to 2 — as an ``unavailable dependency``. A message outside the nine, a
    non-integer amount, a blank currency, or a non-integer exponent is refused. The result
    is an exact :class:`~qmf.core.Money` at the declared money scale (CT-01; DEC-0105).
    """
    if not isinstance(message, str) or message not in MONEY_BEARING_MESSAGES:
        return _invalid(
            "message",
            "a moneyDigits decode governs only the nine money-bearing messages",
            given=repr(message),
            allowed=sorted(MONEY_BEARING_MESSAGES),
        )
    if money_digits is None:
        return _unavailable(
            "money_digits",
            "the moneyDigits exponent is absent; this message's money decode is refused, "
            "never defaulted to 2 (DEC-0135)",
            message=message,
        )
    exponent = _as_plain_int(money_digits)
    if exponent is None or exponent < 0:
        return _invalid(
            "money_digits",
            "the moneyDigits exponent is a non-negative integer count of decimal places",
            given=repr(money_digits),
            message=message,
        )
    units = _as_plain_int(raw_units)
    if units is None:
        return _invalid(
            "raw_units",
            "a money-bearing amount is an exact integer scaled by moneyDigits; a binary "
            "float on the money path is refused",
            given=repr(raw_units),
            message=message,
        )
    return Money.try_create(units, currency, exponent)


# --- self-pacing: rate limits and the historical span cap -------------------


class RequestClass(StrEnum):
    """The rate-limit class a request is paced under (DEC-0135).

    cTrader rate-limits **per connection**: 50 requests/second non-historical plus a
    separate 5/second historical budget. Each request declares its class; the adapter
    declares its own conservative historical/non-historical classification.
    """

    NON_HISTORICAL = "non-historical"
    HISTORICAL = "historical"


_CEILINGS: Final[Mapping[RequestClass, int]] = MappingProxyType(
    {
        RequestClass.NON_HISTORICAL: NON_HISTORICAL_RATE_LIMIT_PER_SECOND,
        RequestClass.HISTORICAL: HISTORICAL_RATE_LIMIT_PER_SECOND,
    }
)


class RatePacer:
    """A per-connection self-pacer enforcing cTrader's request-rate ceilings (DEC-0135).

    The adapter paces itself at or below 50 requests/second non-historical plus 5/second
    historical, per connection, using a one-second sliding window over caller-supplied
    :class:`~qmf.core.MonotonicReading` stamps — it never reads an ambient clock (AR-16).
    Deliberately **not** a frozen value: like the connection manager it owns transient
    stateful pacing state (DEC-0113). A request at or above the class ceiling is a
    ``transient venue failure`` (retryable after-condition = the window regains capacity);
    the pacing cadence below the ceiling is a node value the caller drives, never held here.
    """

    __slots__ = ("_boot_epoch", "_windows")

    _boot_epoch: str | None
    _windows: dict[RequestClass, list[MonotonicReading]]

    def __init__(self) -> None:
        self._boot_epoch = None
        self._windows = {request_class: [] for request_class in RequestClass}

    @staticmethod
    def ceiling_for(request_class: object) -> Result[int]:
        """The per-connection per-second ceiling for a request class, value-or-refusal."""
        resolved = _coerce(RequestClass, request_class)
        if resolved is None:
            return _invalid(
                "request_class",
                "a request class is non-historical or historical",
                given=repr(request_class),
                allowed=[member.value for member in RequestClass],
            )
        return Ok(_CEILINGS[resolved])

    def admit(self, request_class: object, now: object) -> Result[bool]:
        """Admit or refuse a request against its per-connection one-second budget.

        Prunes the class window to the last second, then admits when the window holds fewer
        than the class ceiling — recording ``now`` — or refuses with a ``transient venue
        failure`` when the ceiling is reached. A :class:`~qmf.core.MonotonicReading` from a
        new boot resets every window (a monotonic counter has no meaning across boots).
        """
        resolved = _coerce(RequestClass, request_class)
        if resolved is None:
            return _invalid(
                "request_class",
                "a request class is non-historical or historical",
                given=repr(request_class),
                allowed=[member.value for member in RequestClass],
            )
        if not isinstance(now, MonotonicReading):
            return _invalid(
                "now",
                "self-pacing reads a caller-supplied MonotonicReading, never an ambient clock",
                given=repr(now),
            )
        if self._boot_epoch is None or now.boot_epoch_id != self._boot_epoch:
            # A new boot epoch resets every monotonic window — cross-boot deltas are meaningless.
            self._boot_epoch = now.boot_epoch_id
            for request_key in self._windows:
                self._windows[request_key] = []
        window = self._windows[resolved]
        kept: list[MonotonicReading] = []
        for reading in window:
            elapsed = now.elapsed_since(reading)
            # Same-boot readings never refuse; keep entries within the last one-second window.
            if not is_refusal(elapsed) and elapsed.value.value_ns < _ONE_SECOND_NS:
                kept.append(reading)
        ceiling = _CEILINGS[resolved]
        if len(kept) >= ceiling:
            self._windows[resolved] = kept
            return _transient(
                "rate_limit",
                "the per-connection request-rate ceiling is reached; the adapter paces itself "
                "rather than breach the venue limit",
                "the per-connection rate window regains capacity",
                request_class=resolved.value,
                ceiling_per_second=ceiling,
            )
        kept.append(now)
        self._windows[resolved] = kept
        return Ok(True)


def tick_span_within_cap(from_ms: object, to_ms: object) -> Result[bool]:
    """Enforce the documented one-week historical tick-span cap (DEC-0135).

    A historical tick request spanning more than one week is refused **before** submission
    — the venue enforces the same cap at runtime as error 35 — as an ``invalid input``
    refusal naming the cap, so the caller pages the request into weekly spans. A malformed
    or inverted span (``to`` before ``from``) is likewise refused (CT-15; DEC-0135).
    """
    start = _as_plain_int(from_ms)
    end = _as_plain_int(to_ms)
    if start is None or end is None:
        return _invalid(
            "span",
            "a historical tick span is a pair of Unix-ms integers",
            from_ms=repr(from_ms),
            to_ms=repr(to_ms),
        )
    if end < start:
        return _invalid("span", "the span end precedes its start", from_ms=start, to_ms=end)
    if end - start > HISTORICAL_TICK_SPAN_CAP_MS:
        return _invalid(
            "span",
            "the historical tick span exceeds the documented one-week cap; page it into "
            "weekly spans (venue error 35)",
            span_ms=end - start,
            cap_ms=HISTORICAL_TICK_SPAN_CAP_MS,
        )
    return Ok(True)


# --- session topology: two connections, demo and live separate hosts --------


class VenueEnvironment(StrEnum):
    """A cTrader environment served by its own host/connection (DEC-0135)."""

    DEMO = "demo"
    LIVE = "live"


@dataclass(frozen=True, slots=True)
class ConnectionEndpoint:
    """One environment's connection endpoint — an opaque deployment host reference.

    ``host_ref`` is an opaque deployment token (a host id, never a broker name): which
    broker fronts the platform is deployment configuration, so the endpoint names no broker
    (DEC-0139).
    """

    environment: VenueEnvironment
    host_ref: str


@dataclass(frozen=True, slots=True)
class SessionTopology:
    """The two-connection topology: demo and live are separate hosts (DEC-0135).

    Demo and live are separate hosts requiring **two simultaneous connections**, each
    serving one environment; the session topology follows this two-connection shape. Built
    through :meth:`try_create`, which requires exactly one demo and one live endpoint.
    """

    demo: ConnectionEndpoint
    live: ConnectionEndpoint

    #: Two simultaneous connections are required — one per environment (DEC-0135).
    required_connection_count: ClassVar[int] = 2

    @classmethod
    def try_create(cls, demo_host_ref: object, live_host_ref: object) -> Result[SessionTopology]:
        """Validate and build a :class:`SessionTopology`, returning value-or-refusal.

        Each host reference is an opaque non-blank deployment token that names no broker; a
        blank reference, or the same host serving both environments (demo and live are
        separate hosts), is an ``invalid input`` refusal (DEC-0135, DEC-0139).
        """
        demo = _clean_host(demo_host_ref)
        if demo is None:
            return _invalid(
                "demo_host_ref",
                "the demo endpoint is an opaque non-blank deployment host reference",
                given=repr(demo_host_ref),
            )
        live = _clean_host(live_host_ref)
        if live is None:
            return _invalid(
                "live_host_ref",
                "the live endpoint is an opaque non-blank deployment host reference",
                given=repr(live_host_ref),
            )
        if demo == live:
            return _invalid(
                "host_ref",
                "demo and live are separate hosts requiring two simultaneous connections; "
                "one host cannot serve both environments",
                host_ref=demo,
            )
        return Ok(
            cls(
                demo=ConnectionEndpoint(environment=VenueEnvironment.DEMO, host_ref=demo),
                live=ConnectionEndpoint(environment=VenueEnvironment.LIVE, host_ref=live),
            )
        )

    def endpoint_for(self, environment: object) -> Result[ConnectionEndpoint]:
        """The connection endpoint serving one environment, value-or-refusal."""
        resolved = _coerce(VenueEnvironment, environment)
        if resolved is None:
            return _invalid(
                "environment",
                "an environment is demo or live",
                given=repr(environment),
                allowed=[member.value for member in VenueEnvironment],
            )
        return Ok(self.demo if resolved is VenueEnvironment.DEMO else self.live)


def _clean_host(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank host reference, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


# --- token lifecycle --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class TokenLifecycle:
    """The declared cTrader token lifecycle class (CT-18 token_lifecycle_class; DEC-0135).

    A ~30-day access token, a never-expiring refresh token treated as the crown-jewel
    secret, and cTID re-authorization as the invalidation anchor. This declares the
    lifecycle *class*; the secret **values** live only in the connection manager through the
    injected ``SecretStore`` (CT-21; DEC-0136). A frozen constant surface — a caller reads
    :meth:`declared` rather than reconstructing the class.
    """

    access_token_class: str = ACCESS_TOKEN_LIFETIME_CLASS
    refresh_token_class: str = REFRESH_TOKEN_LIFETIME_CLASS
    invalidation_anchor: str = INVALIDATION_ANCHOR

    @classmethod
    def declared(cls) -> TokenLifecycle:
        """The ratified cTrader token lifecycle class (DEC-0135)."""
        return cls()


# --- session duties as schedulable work -------------------------------------


class SessionDuty(StrEnum):
    """A periodic session duty the application's scheduler drives (DEC-0141, FR-025).

    The adapter *defines* the work; the application *runs* it. Command retry is never a
    duty — retryability rides typed refusals, and session recovery never resubmits a
    command.
    """

    HEARTBEAT = "heartbeat"
    TOKEN_REFRESH = "token-refresh"  # noqa: S105 - a duty NAME, never a secret value
    RECONNECT = "reconnect"
    GAP_REPLAY = "gap-replay"
    VERIFICATION_MONITOR = "verification-monitor"


@dataclass(frozen=True, slots=True)
class SchedulableDuty:
    """One declared schedulable session duty (DEC-0141, FR-025).

    ``venue_bound_seconds`` is the venue-declared bound where one exists — only the
    heartbeat carries the 10-second inactivity bound; every other duty's cadence is a node
    value under do-not-default, so it declares ``None`` and the application supplies its
    schedule. The adapter defines the duty; the application's scheduler drives it.
    """

    duty: SessionDuty
    venue_bound_seconds: int | None = None

    @property
    def is_venue_bounded(self) -> bool:
        """Whether the duty carries a venue-declared bound (only the heartbeat does)."""
        return self.venue_bound_seconds is not None


# The declared set of schedulable session duties (DEC-0141). Heartbeat carries the venue's
# 10-second inactivity bound; every other cadence is node configuration, declared ``None``.
SESSION_DUTIES: Final[tuple[SchedulableDuty, ...]] = (
    SchedulableDuty(duty=SessionDuty.HEARTBEAT, venue_bound_seconds=HEARTBEAT_BOUND_SECONDS),
    SchedulableDuty(duty=SessionDuty.TOKEN_REFRESH),
    SchedulableDuty(duty=SessionDuty.RECONNECT),
    SchedulableDuty(duty=SessionDuty.GAP_REPLAY),
    SchedulableDuty(duty=SessionDuty.VERIFICATION_MONITOR),
)


@dataclass(frozen=True, slots=True)
class InFlightResolution:
    """How session recovery resolves one in-flight command — always ``UNKNOWN`` (DEC-0137).

    On disconnect an in-flight command's outcome is ``UNKNOWN`` (a **state**, never an
    error) carrying the ``disconnect`` trigger; recovery **never resubmits** it. The
    application later clears the block through an explicit ``resolve_unknown`` call.
    """

    command_id: str
    outcome: SubmissionOutcome
    trigger: UnknownTrigger


@dataclass(frozen=True, slots=True)
class SessionRecovery:
    """Connection-manager-owned session recovery that never resubmits a command (DEC-0137).

    Session recovery (connect, reconnect, heartbeat, token refresh, gap replay) is
    connection-manager policy, but it **never resubmits a command** and command retry is
    prohibited. On disconnect every in-flight command becomes ``UNKNOWN`` (a state), and
    recovered fills commit through evidence before a session reports healthy.
    """

    #: Session recovery never resubmits a command (DEC-0137). A structural invariant.
    resubmits_command: ClassVar[bool] = False

    def on_disconnect(
        self, in_flight_command_ids: object
    ) -> Result[tuple[InFlightResolution, ...]]:
        """Resolve every in-flight command to ``UNKNOWN`` on disconnect, never resubmitting.

        Each id maps to an :class:`InFlightResolution` of outcome ``UNKNOWN`` and trigger
        ``disconnect`` — a state, never a resubmission. A non-sequence of ids, or a blank
        id, is an ``invalid input`` refusal (CT-19; DEC-0137).
        """
        if isinstance(in_flight_command_ids, (str, bytes)) or not isinstance(
            in_flight_command_ids, Sequence
        ):
            return _invalid(
                "in_flight_command_ids",
                "recovery takes a sequence of in-flight command identities",
                given=repr(in_flight_command_ids),
            )
        resolutions: list[InFlightResolution] = []
        for index, command_id in enumerate(cast("Sequence[object]", in_flight_command_ids)):
            if not isinstance(command_id, str) or command_id.strip() == "":
                return _invalid(
                    "in_flight_command_ids",
                    "each in-flight command identity is a non-empty token",
                    index=index,
                    given=repr(command_id),
                )
            resolutions.append(
                InFlightResolution(
                    command_id=command_id,
                    outcome=SubmissionOutcome.UNKNOWN,
                    trigger=UnknownTrigger.DISCONNECT,
                )
            )
        return Ok(tuple(resolutions))


# --- per-broker configuration: measured facts, never hardcoded --------------


@dataclass(frozen=True, slots=True)
class CTraderBrokerConfiguration:
    """Per-broker configuration read from the venue-observation profile (DEC-0135, DEC-0139).

    The daily-bar boundary and the trendbar price basis are demoted 2013-forum-grade claims
    (17:00-New-York and BID), so they are **never hardcoded**: this configuration reads each
    from the per-``(VenueId, account)`` :class:`~qmf.venue.observation.VenueObservationProfile`
    the first-connection suite records, verify-or-refuse, re-verified by a continuous
    monitor. Which broker fronts the platform is deployment configuration — only opaque
    ``VenueId`` / ``AccountId`` identity is held and **no broker is named** (DEC-0139).
    """

    venue_id: VenueId
    account: Account
    profile: VenueObservationProfile

    @classmethod
    def try_create(
        cls, venue_id: object, account: object, profile: object
    ) -> Result[CTraderBrokerConfiguration]:
        """Validate and build a :class:`CTraderBrokerConfiguration`, value-or-refusal.

        The account must belong to the venue and the profile must be the profile for this
        exact ``(VenueId, account)`` — a mismatched profile would read another broker's
        measured facts. A malformed noun or a mismatch is an ``invalid input`` refusal
        (CT-03, CT-18; DEC-0107, DEC-0139).
        """
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid(
                "venue_id",
                "per-broker configuration is keyed by a valid VenueId",
                given=repr(venue_id),
            )
        if not isinstance(account, Account):
            return _invalid(
                "account",
                "per-broker configuration is keyed by a valid Account",
                given=repr(account),
            )
        if account.venue != venue_id:
            return _invalid(
                "account",
                "the account does not belong to this venue; the (VenueId, account) key would "
                "name a binding that cannot exist",
                venue=venue_id.value,
                account_venue=account.venue.value,
            )
        if not isinstance(profile, VenueObservationProfile):
            return _invalid(
                "profile",
                "per-broker configuration reads the per-(VenueId, account) venue-observation "
                "profile",
                given=repr(profile),
            )
        if profile.venue_id != venue_id or profile.account != account:
            return _invalid(
                "profile",
                "the venue-observation profile is for a different (VenueId, account) than this "
                "configuration",
                config_venue=venue_id.value,
                profile_venue=profile.venue_id.value,
            )
        return Ok(cls(venue_id=venue_id, account=account, profile=profile))

    def require_daily_boundary(self) -> Result[bool]:
        """Verify-or-refuse gate over the venue daily-bar boundary (FM-6; DEC-0135).

        Delegates to the profile: an unmeasured or unverified daily boundary leaves venue
        daily bars ungoverned (an ``unavailable dependency`` refusal), never a hardcoded
        17:00-New-York assumption.
        """
        return self.profile.require_evidence(VenueEvidenceClass.VENUE_DAILY_BARS)

    def daily_boundary_calendar(
        self, rule_set_version: object, tzdata_version: object
    ) -> Result[CalendarIdentity]:
        """Mint the venue-scoped market-hours calendar for the measured D1 boundary.

        Verify-or-refuse and **never hardcoded**: only a verified measured boundary mints an
        identity, and the identity encodes the measured UTC minute-of-day, never the demoted
        17:00-New-York claim (delegates to the profile; DEC-0135, DEC-0141).
        """
        return self.profile.mint_daily_boundary_calendar(rule_set_version, tzdata_version)

    def trendbar_price_basis(self) -> Result[str]:
        """The measured trendbar price basis (the verified quote side), verify-or-refuse.

        Reads the verified ``bar-basis`` fact's measured quote side from the profile — the
        BID basis is a demoted claim and is **never hardcoded**. An unverified or absent
        bar-basis check refuses metadata-derived bar evidence rather than returning a
        default; a verified fact returns whatever quote side the reconciliation established
        (DEC-0135).
        """
        gate = self.profile.require_evidence(VenueEvidenceClass.BAR)
        if is_refusal(gate):
            return gate
        fact = self.profile.latest_for(ProbeCheck.BAR_BASIS)
        # A verified BAR evidence class always has a latest verified bar-basis fact; the guard
        # is defensive against a hand-built profile that split the two.
        if fact is None or fact.verdict is not ProbeVerdict.VERIFIED:  # pragma: no cover
            return _unavailable(
                "trendbar_price_basis",
                "the bar-basis check is unverified; the trendbar price basis is refused, never "
                "defaulted to BID",
            )
        basis = fact.measured.get("quote_type")
        # A verified bar-basis fact always carries its quote side; guard defends a hand-built one.
        if not isinstance(basis, str) or basis.strip() == "":  # pragma: no cover
            return _unavailable(
                "trendbar_price_basis",
                "the verified bar-basis fact records no quote side",
            )
        return Ok(basis)

    def deployment_identity(self) -> Mapping[str, str]:
        """The opaque deployment identity — ``VenueId`` / ``AccountId`` only, no broker named.

        Which broker fronts the platform is deployment configuration; this returns only the
        opaque identity tokens, so the platform stays venue-blind above the port (DEC-0139).
        """
        return MappingProxyType(
            {"venue_id": self.venue_id.value, "account_id": self.account.account_id}
        )


# --- the cTrader adapter facade ---------------------------------------------


@dataclass(frozen=True, slots=True)
class CTraderAdapter:
    """cTrader as adapter #1 behind the venue-neutral port (DEC-0135, DEC-0138, DEC-0139).

    A thin assembly binding the per-broker configuration, the two-connection session
    topology, and the declared token lifecycle. It honors the cTrader-platform venue facts
    as standing obligations (exposed as static capability-declaration data through
    :meth:`static_capability_facts`, and as the module's decoders, self-pacer, and declared
    session duties) while the daily boundary, the trendbar basis, and broker identity stay
    per-broker / deployment configuration on the :class:`CTraderBrokerConfiguration`. No
    broker is named and nothing venue-shaped leaks above the port.
    """

    broker_config: CTraderBrokerConfiguration
    topology: SessionTopology
    token_lifecycle: TokenLifecycle = TokenLifecycle()

    @classmethod
    def try_create(
        cls, broker_config: object, topology: object, token_lifecycle: object = None
    ) -> Result[CTraderAdapter]:
        """Validate the wiring and build a :class:`CTraderAdapter`, value-or-refusal.

        The broker configuration and the session topology are required; the token lifecycle
        defaults to the ratified declared class when the caller passes ``None``. A malformed
        component is an ``invalid input`` refusal (DEC-0135, DEC-0139).
        """
        if not isinstance(broker_config, CTraderBrokerConfiguration):
            return _invalid(
                "broker_config",
                "the adapter binds a CTraderBrokerConfiguration",
                given=repr(broker_config),
            )
        if not isinstance(topology, SessionTopology):
            return _invalid(
                "topology",
                "the adapter binds a two-connection SessionTopology",
                given=repr(topology),
            )
        if token_lifecycle is None:
            lifecycle = TokenLifecycle.declared()
        elif isinstance(token_lifecycle, TokenLifecycle):
            lifecycle = token_lifecycle
        else:
            return _invalid(
                "token_lifecycle",
                "the token lifecycle is a declared TokenLifecycle class or None for the default",
                given=repr(token_lifecycle),
            )
        return Ok(cls(broker_config=broker_config, topology=topology, token_lifecycle=lifecycle))

    @property
    def session_duties(self) -> tuple[SchedulableDuty, ...]:
        """The declared schedulable session duties the application's scheduler drives."""
        return SESSION_DUTIES

    @property
    def recovery(self) -> SessionRecovery:
        """The session-recovery policy — never resubmits a command (DEC-0137)."""
        return SessionRecovery()

    @staticmethod
    def new_pacer() -> RatePacer:
        """A fresh per-connection self-pacer enforcing the venue rate ceilings."""
        return RatePacer()

    @staticmethod
    def static_capability_facts() -> Mapping[CapabilityFieldName, object]:
        """The cTrader-platform static capability facts the composition root wires (DEC-0135).

        The documentation-grade venue facts that are static declaration data (never the
        measured per-broker facts and never a broker name): the per-connection rate limits,
        the historical span cap and paging model, the token lifecycle class, and the
        server-clock availability (none — receive-time recording is mandatory). Returned as
        fp1-clean JSON-native values keyed by their CT-18 roster field, so the composition
        root builds a :class:`~qmf.venue.capabilities.CapabilityDeclaration` from data, with
        no broker-specific behavior baked into code (DEC-0138, DEC-0139).
        """
        return MappingProxyType(
            {
                CapabilityFieldName.RATE_LIMITS: MappingProxyType(
                    {
                        "non_historical_per_second": NON_HISTORICAL_RATE_LIMIT_PER_SECOND,
                        "historical_per_second": HISTORICAL_RATE_LIMIT_PER_SECOND,
                        "scope": "connection",
                    }
                ),
                CapabilityFieldName.SPAN_CAPS_AND_PAGING: MappingProxyType(
                    {
                        "historical_tick_span_cap_ms": HISTORICAL_TICK_SPAN_CAP_MS,
                        "tick_encoding": "newest-first-delta",
                        "paging": "hasMore",
                    }
                ),
                CapabilityFieldName.TOKEN_LIFECYCLE_CLASS: MappingProxyType(
                    {
                        "access_token": ACCESS_TOKEN_LIFETIME_CLASS,
                        "refresh_token": REFRESH_TOKEN_LIFETIME_CLASS,
                        "invalidation_anchor": INVALIDATION_ANCHOR,
                    }
                ),
                CapabilityFieldName.SERVER_CLOCK_AVAILABILITY: False,
            }
        )
