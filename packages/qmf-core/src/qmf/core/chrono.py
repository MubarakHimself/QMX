"""CT-02 — exact time, calendars, and the injected Clock (COMP-QMF-CORE).

The time vocabulary every QMF package shares, defined here in ``qmf-core`` and
nowhere else. Time is **exact and machine-move-proof**: every stored timestamp is
an :class:`Instant` — an ``int64`` count of UTC nanoseconds since the Unix epoch,
POSIX no-leap-second — so results stay identical across server moves, DST shifts,
tzdata updates, and clock corrections (CT-02; DEC-0106).

Five things this module pins down:

**Exact instants and checked arithmetic.** An :class:`Instant` is a whole ``int64``
nanosecond count; the representable range 1677 through 2262 *is* the ``int64``
range, so validation is a range check. All nanosecond arithmetic is checked —
overflow is an ``invalid input`` typed refusal, **never a silent wrap** (FM-2).
Instant ``0`` is a valid instant; an absent time is an absent field (``Instant |
None`` left ``None``), **never** an ``Instant(0)`` sentinel.

**Civil date vs trading date.** :class:`CivilDate` and :class:`TradingDate` are
distinct types. A :class:`TradingDate` carries its :class:`CalendarIdentity` (rule
set + version + tzdata version) **in-band**; equality holds only within one
calendar identity and cross-calendar comparison is a typed refusal (FM-3). A
:class:`TradingDate` is **never** derived by formatting an instant and is **never**
a causality proxy — causality compares :class:`Instant`\\ s only, via
:func:`compare_causal`, which refuses at equal instants rather than tie-break.

**Wall vs monotonic, behind an injected Clock.** Clock access is the core-defined
:class:`Clock` :class:`typing.Protocol` seam, injected at the composition root (a
real clock in production, a :class:`DataDrivenClock` in replay); nothing below the
root reads the system clock. Wall and monotonic kinds are **type-separated**: a
wall reading is an :class:`Instant`, a monotonic reading is a
:class:`MonotonicReading` — an opaque, boot-scoped diagnostic that is never an
Instant, never rendered as a time, and excluded from identity (AR-16).

**Calendars ship outside core.** ``qmf-core`` embeds **no** market-hours calendar
rule set. Calendars ship as separate versioned extensions (the forex extension is
Epic 4) that force ``TZPATH`` to their pinned tzdata and verify at import that the
resolved tzdb equals the pin — :func:`verify_tzdb_pin` is that seam, refusing
``unavailable dependency`` on a mismatch (FM-5). Only the rule set plus tzdata
version enter fingerprints; local / ISO-8601 time is display-only, always
labelled (:class:`DisplayTime`), and excluded from identity.

**Per-writer ordering with no causal meaning.** :class:`WriterId` is a first-class
core noun minted per ``(machine, role, stream)`` with a boot/epoch id. Every record
stream carries a per-writer strictly-increasing sequence (:class:`WriterSequencer`),
and ``(instant, writer, sequence)`` — an :class:`OrderingKey` — is a
replay-determinism ordering device with **no causal meaning**.

Every value type follows the one CT-04 construction pattern: an **unchecked
constructor** (the frozen dataclass) for trusted internal use, plus a validating
:meth:`try_create` factory returning ``Result[T] = Ok[T] | TypedRefusal`` (CT-04;
DEC-0109). Stdlib only (DEC-0104). Frozen, immutable values throughout (DEC-0101,
DEC-0113).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from enum import StrEnum
from typing import Final, Protocol, runtime_checkable

from qmf.core.refusal import Ok, RefusalCategory, Result, Retryability, TypedRefusal

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "CalendarIdentity",
    "CivilDate",
    "Clock",
    "ClockKind",
    "DataDrivenClock",
    "DisplayTime",
    "Duration",
    "Instant",
    "Interval",
    "MonotonicReading",
    "OrderingKey",
    "SessionWindow",
    "TemporalOrder",
    "TradingDate",
    "WriterId",
    "WriterSequencer",
    "compare_causal",
    "render_utc_iso8601",
    "verify_tzdb_pin",
]

# Every serialized CT-02 artifact stamps this integer contract format version; its
# meaning never mutates — an incompatible change mints the next version plus a
# migration note (DEC-0103; versioning-from-birth L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1

# The representable instant range 1677 through 2262 IS the signed int64 nanosecond
# range, stated once (CT-02; DEC-0106). A Duration is a signed int64 nanosecond
# quantity over the same bounds.
_INT64_MIN: Final[int] = -(2**63)
_INT64_MAX: Final[int] = 2**63 - 1

# The Unix epoch as a timezone-aware UTC datetime, used only for display rendering
# (never to read the system clock).
_EPOCH_UTC: Final[datetime] = datetime(1970, 1, 1, tzinfo=timezone.utc)
_NANOS_PER_SECOND: Final[int] = 1_000_000_000


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a time factory returns.

    ``retryability`` is ``no`` — a malformed instant, a nanosecond-arithmetic
    overflow, or a cross-calendar comparison is a caller mistake, not a transient
    condition — and ``context`` always names the offending ``field`` and a
    human-legible ``reason`` (returned, never raised; CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unavailable(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unavailable dependency`` refusal a seam returns when a required
    dependency is not present: the tzdb-pin mismatch (CT-02; FM-5) and the
    data-driven clock's exhausted script (OR-03; CT-04, DEC-0109). ``retryability``
    is ``no`` — a spent replay script or a mismatched pin is not transient — and
    ``context`` names the missing dependency (returned, never raised)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal :func:`compare_causal` returns at
    equal instants: the causality model's policy is that concurrent events are
    never tie-broken (CT-02; DEC-0106)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


# --- validation helpers -----------------------------------------------------


def _as_int64(value: object) -> int | None:
    """Return ``value`` as a genuine ``int`` within the signed ``int64`` range,
    or ``None``.

    A ``bool`` (an ``int`` subclass) is rejected, and a value outside the ``int64``
    bounds — which are exactly the representable instant range 1677 through 2262 —
    is rejected too. Returning the narrowed value lets a factory hand a typed
    ``int`` to its frozen constructor.
    """
    if isinstance(value, bool):
        return None
    if not isinstance(value, int):
        return None
    if value < _INT64_MIN or value > _INT64_MAX:
        return None
    return value


def _checked_int64(value: int) -> int | None:
    """Return ``value`` if it fits the signed ``int64`` range, else ``None``.

    The overflow guard behind every nanosecond arithmetic operation: an out-of-range
    result is refused, never wrapped (FM-2). The input is already a Python ``int``
    (unbounded), so only the range is in question.
    """
    if value < _INT64_MIN or value > _INT64_MAX:
        return None
    return value


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    Identity tokens (machine, role, stream, calendar rule set, tzdata version, a
    session/display zone label) are opaque: the returned token is the caller's
    string unchanged — never stripped, cased, or parsed.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


# --- clock kinds ------------------------------------------------------------


class ClockKind(StrEnum):
    """The two clock kinds (CT-02 ``enums.clock_kind``; DEC-0106).

    The kinds are **type-separated**, not merely tagged: a wall reading is an
    :class:`Instant`, a monotonic reading is a :class:`MonotonicReading`, and the
    type system — not this label — is what stops a monotonic reading from ever
    standing in for an instant. The label exists so each kind names itself.
    """

    WALL = "wall"
    MONOTONIC = "monotonic"


class TemporalOrder(StrEnum):
    """The result of an order comparison (CT-02).

    :meth:`TradingDate.compare` returns all three; :func:`compare_causal` returns
    only ``BEFORE`` / ``AFTER`` — it **refuses** rather than return ``EQUAL``,
    because equal instants are concurrent and causality never tie-breaks.
    """

    BEFORE = "before"
    EQUAL = "equal"
    AFTER = "after"


# --- instants, durations, intervals -----------------------------------------


@dataclass(frozen=True, slots=True)
class Instant:
    """An exact wall-clock timestamp: an ``int64`` count of UTC nanoseconds since
    the Unix epoch, POSIX no-leap-second (CT-02; DEC-0106).

    Instant ``0`` is a valid instant (the epoch), never a sentinel for absent — an
    absent time is a ``None`` field, not an ``Instant(0)``. All arithmetic is
    checked: :meth:`add_duration` and :meth:`difference` refuse on overflow rather
    than wrap (FM-2). Causality compares Instants only (:func:`compare_causal`).
    """

    value_ns: int

    @property
    def kind(self) -> ClockKind:
        """The wall clock kind; an Instant is always a wall reading (DEC-0106)."""
        return ClockKind.WALL

    @classmethod
    def try_create(cls, value_ns: object) -> Result[Instant]:
        """Validate and build an :class:`Instant`, returning value-or-refusal.

        A non-integer, a ``bool``, or a value outside the ``int64`` (1677–2262)
        range is an ``invalid input`` refusal (FM-2); ``0`` is accepted.
        """
        checked = _as_int64(value_ns)
        if checked is None:
            return _invalid(
                "value_ns",
                "an instant is an int64 UTC-nanosecond count in the representable "
                "range 1677 through 2262; a non-integer, a bool, or an out-of-range "
                "value is refused, never wrapped (FM-2)",
                given=repr(value_ns),
            )
        return Ok(cls(value_ns=checked))

    def add_duration(self, duration: object) -> Result[Instant]:
        """Advance this instant by a :class:`Duration`, refusing on overflow.

        Nanosecond overflow is an ``invalid input`` refusal, never a wrap (FM-2).
        """
        if not isinstance(duration, Duration):
            return _invalid(
                "duration",
                "an instant advances only by a Duration",
                given=repr(duration),
            )
        checked = _checked_int64(self.value_ns + duration.value_ns)
        if checked is None:
            return _invalid(
                "value_ns",
                "nanosecond arithmetic overflowed the int64 range; refused, never wrapped (FM-2)",
                instant=self.value_ns,
                duration=duration.value_ns,
            )
        return Ok(Instant(value_ns=checked))

    def difference(self, earlier: object) -> Result[Duration]:
        """The signed :class:`Duration` from ``earlier`` to this instant.

        This span is **evidence**, not an elapsed-time measurement — a duration
        derived from two wall instants must never be read as latency, timeout, or
        cadence (those are measured monotonically). Overflow is refused (FM-2).
        """
        if not isinstance(earlier, Instant):
            return _invalid(
                "earlier",
                "an instant difference is taken against another Instant",
                given=repr(earlier),
            )
        checked = _checked_int64(self.value_ns - earlier.value_ns)
        if checked is None:
            return _invalid(
                "value_ns",
                "nanosecond arithmetic overflowed the int64 range; refused, never wrapped (FM-2)",
                left=self.value_ns,
                right=earlier.value_ns,
            )
        return Ok(Duration(value_ns=checked))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this instant.

        An instant is an integer identity numeric — its nanosecond count is its
        identity (CT-02; DEC-0108).
        """
        return {
            "class": "instant",
            "value_ns": self.value_ns,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class Duration:
    """A signed ``int64`` quantity of nanoseconds: clock-agnostic and freely
    storable (CT-02; DEC-0106).

    The restriction is on **operations**, not on the value: a duration used for
    latency, timeout, cooldown, or cadence must be measured monotonically
    (:meth:`MonotonicReading.elapsed_since`), while a duration derived from two
    wall instants (:meth:`Instant.difference`) is an evidence span, never elapsed
    time. Arithmetic is checked (FM-2).
    """

    value_ns: int

    @classmethod
    def try_create(cls, value_ns: object) -> Result[Duration]:
        """Validate and build a :class:`Duration`, returning value-or-refusal."""
        checked = _as_int64(value_ns)
        if checked is None:
            return _invalid(
                "value_ns",
                "a duration is a signed int64 nanosecond quantity; a non-integer, a "
                "bool, or an out-of-range value is refused",
                given=repr(value_ns),
            )
        return Ok(cls(value_ns=checked))

    def add(self, other: object) -> Result[Duration]:
        """Add another :class:`Duration`, refusing on overflow (FM-2)."""
        return self._combine(other, subtract=False)

    def subtract(self, other: object) -> Result[Duration]:
        """Subtract another :class:`Duration`, refusing on overflow (FM-2)."""
        return self._combine(other, subtract=True)

    def _combine(self, other: object, *, subtract: bool) -> Result[Duration]:
        if not isinstance(other, Duration):
            return _invalid("other", "an operand must be a Duration value", given=repr(other))
        raw = self.value_ns - other.value_ns if subtract else self.value_ns + other.value_ns
        checked = _checked_int64(raw)
        if checked is None:
            return _invalid(
                "value_ns",
                "nanosecond arithmetic overflowed the int64 range; refused, never wrapped (FM-2)",
                left=self.value_ns,
                right=other.value_ns,
            )
        return Ok(Duration(value_ns=checked))

    def negate(self) -> Result[Duration]:
        """The signed negation, refusing on overflow — ``-int64_min`` has no int64
        counterpart, so it is refused rather than wrapped (FM-2)."""
        checked = _checked_int64(-self.value_ns)
        if checked is None:
            return _invalid(
                "value_ns",
                "negation overflowed the int64 range (int64 min has no positive "
                "counterpart); refused, never wrapped (FM-2)",
                given=self.value_ns,
            )
        return Ok(Duration(value_ns=checked))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this duration."""
        return {
            "class": "duration",
            "value_ns": self.value_ns,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class Interval:
    """A half-open ``[start, end)`` span of :class:`Instant`\\ s (CT-02; DEC-0106).

    ``start`` may equal ``end`` (an empty interval containing nothing); ``start``
    after ``end`` is refused. :meth:`contains` and :meth:`overlaps` read the
    half-open convention: the start is included, the end is excluded.
    """

    start: Instant
    end: Instant

    @classmethod
    def try_create(cls, start: object, end: object) -> Result[Interval]:
        """Validate and build an :class:`Interval`, returning value-or-refusal.

        Both bounds must be :class:`Instant`\\ s and ``start`` must not fall after
        ``end`` (an equal pair is the empty interval).
        """
        if not isinstance(start, Instant):
            return _invalid("start", "an interval start must be an Instant", given=repr(start))
        if not isinstance(end, Instant):
            return _invalid("end", "an interval end must be an Instant", given=repr(end))
        if start.value_ns > end.value_ns:
            return _invalid(
                "start",
                "a half-open interval requires start <= end",
                start=start.value_ns,
                end=end.value_ns,
            )
        return Ok(cls(start=start, end=end))

    def contains(self, instant: object) -> Result[bool]:
        """Whether ``instant`` lies in ``[start, end)`` (start included, end
        excluded)."""
        if not isinstance(instant, Instant):
            return _invalid("instant", "containment tests an Instant", given=repr(instant))
        return Ok(self.start.value_ns <= instant.value_ns < self.end.value_ns)

    def overlaps(self, other: object) -> Result[bool]:
        """Whether this interval and ``other`` share any instant (half-open)."""
        if not isinstance(other, Interval):
            return _invalid("other", "overlap tests another Interval", given=repr(other))
        return Ok(
            self.start.value_ns < other.end.value_ns and other.start.value_ns < self.end.value_ns
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this interval."""
        return {
            "class": "interval",
            "start_ns": self.start.value_ns,
            "end_ns": self.end.value_ns,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- civil and trading dates ------------------------------------------------


@dataclass(frozen=True, slots=True)
class CivilDate:
    """A calendar-agnostic civil date (CT-02; DEC-0106).

    A civil label — year, month, day — **distinct** from :class:`TradingDate`: it
    carries no calendar identity and is never a trading-day value on its own. It is
    validated as a real calendar date and rendered display-only via
    :meth:`isoformat`.
    """

    year: int
    month: int
    day: int

    @classmethod
    def try_create(cls, year: object, month: object, day: object) -> Result[CivilDate]:
        """Validate and build a :class:`CivilDate`, returning value-or-refusal.

        The parts must be integers forming a real calendar date; anything else is
        an ``invalid input`` refusal.
        """
        if isinstance(year, bool) or not isinstance(year, int):
            return _invalid("year", "a civil date year must be an integer", given=repr(year))
        if isinstance(month, bool) or not isinstance(month, int):
            return _invalid("month", "a civil date month must be an integer", given=repr(month))
        if isinstance(day, bool) or not isinstance(day, int):
            return _invalid("day", "a civil date day must be an integer", given=repr(day))
        try:
            date(year, month, day)
        except (ValueError, OverflowError):
            return _invalid(
                "date",
                "the parts must form a real calendar date",
                year=year,
                month=month,
                day=day,
            )
        return Ok(cls(year=year, month=month, day=day))

    def ordinal(self) -> tuple[int, int, int]:
        """The ``(year, month, day)`` sort key for same-domain civil ordering."""
        return (self.year, self.month, self.day)

    def isoformat(self) -> str:
        """The ISO-8601 civil-date string (display-only, excluded from identity)."""
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"


@dataclass(frozen=True, slots=True)
class CalendarIdentity:
    """A calendar's identity: the rule set plus the tzdata version (CT-02;
    DEC-0106, DEC-0108).

    Identity is the **rule set** (for example ``forex-17NY``), its
    ``rule_set_version`` (for example ``v3``), and the pinned ``tzdata_version`` —
    separate from any binding to venues or accounts. Only these parts enter
    fingerprints, so a venue change that does not change the rule set does not
    change derived-artifact identity. ``qmf-core`` embeds no rule set; the rules
    themselves ship in a versioned calendar extension.
    """

    rule_set: str
    rule_set_version: str
    tzdata_version: str

    @classmethod
    def try_create(
        cls, rule_set: object, rule_set_version: object, tzdata_version: object
    ) -> Result[CalendarIdentity]:
        """Validate and build a :class:`CalendarIdentity`, returning value-or-refusal."""
        name = _clean_str(rule_set)
        if name is None:
            return _invalid(
                "rule_set",
                "a calendar rule set is a non-empty identity token, e.g. forex-17NY",
                given=repr(rule_set),
            )
        version = _clean_str(rule_set_version)
        if version is None:
            return _invalid(
                "rule_set_version",
                "a calendar carries a non-empty rule-set version, e.g. v3",
                given=repr(rule_set_version),
            )
        tzdata = _clean_str(tzdata_version)
        if tzdata is None:
            return _invalid(
                "tzdata_version",
                "a calendar pins a non-empty tzdata version; it enters fingerprints",
                given=repr(tzdata_version),
            )
        return Ok(cls(rule_set=name, rule_set_version=version, tzdata_version=tzdata))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — rule set + tzdata only."""
        return {
            "class": "calendar-identity",
            "rule_set": self.rule_set,
            "rule_set_version": self.rule_set_version,
            "tzdata_version": self.tzdata_version,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class TradingDate:
    """A trading date carrying its :class:`CalendarIdentity` in-band (CT-02;
    DEC-0106).

    Equality holds **only within one calendar identity**; :meth:`compare` refuses a
    cross-calendar comparison (FM-3). A trading date is **never** derived by
    formatting an instant — there is deliberately no ``from_instant`` — and is
    **never** a causality proxy; causality compares :class:`Instant`\\ s only. The
    ``date_value`` is the civil label of the trading day under this calendar's
    rollover rule, supplied by the calendar extension, not computed here.
    """

    calendar: CalendarIdentity
    date_value: CivilDate

    @classmethod
    def try_create(cls, calendar: object, date_value: object) -> Result[TradingDate]:
        """Validate and build a :class:`TradingDate`, returning value-or-refusal."""
        if not isinstance(calendar, CalendarIdentity):
            return _invalid(
                "calendar",
                "a trading date carries a CalendarIdentity (rule set + version + tzdata) in-band",
                given=repr(calendar),
            )
        if not isinstance(date_value, CivilDate):
            return _invalid(
                "date_value",
                "a trading date's value is a CivilDate supplied by the calendar rule, "
                "never derived by formatting an instant",
                given=repr(date_value),
            )
        return Ok(cls(calendar=calendar, date_value=date_value))

    def compare(self, other: object) -> Result[TemporalOrder]:
        """Order this trading date against ``other`` within one calendar identity.

        Two trading dates of **different** calendar identities are incomparable — a
        cross-calendar comparison is an ``invalid input`` refusal (FM-3), never a
        silent answer. Within one calendar the comparison reads the civil date.
        """
        if not isinstance(other, TradingDate):
            return _invalid(
                "other", "a trading date compares to another TradingDate", given=repr(other)
            )
        if other.calendar != self.calendar:
            return _invalid(
                "calendar",
                "trading dates of different calendar identities are incomparable (FM-3)",
                left=repr(self.calendar),
                right=repr(other.calendar),
            )
        left = self.date_value.ordinal()
        right = other.date_value.ordinal()
        if left < right:
            return Ok(TemporalOrder.BEFORE)
        if left > right:
            return Ok(TemporalOrder.AFTER)
        return Ok(TemporalOrder.EQUAL)

    def equals(self, other: object) -> Result[bool]:
        """Whether two trading dates are equal within one calendar identity.

        Cross-calendar equality is a typed refusal, not ``False`` (FM-3).
        """
        comparison = self.compare(other)
        if isinstance(comparison, TypedRefusal):
            return comparison
        return Ok(comparison.value is TemporalOrder.EQUAL)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — calendar identity + date."""
        return {
            "class": "trading-date",
            "calendar": self.calendar.fp1_identity(),
            "date_value": self.date_value.isoformat(),
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- monotonic readings and the Clock seam ----------------------------------


@dataclass(frozen=True, slots=True)
class MonotonicReading:
    """An opaque, boot-scoped monotonic diagnostic (CT-02; DEC-0106).

    A monotonic reading is **never an Instant** and never a timestamp: it carries
    its ``boot_epoch_id`` so it is compared only within one boot on one machine,
    is excluded from identity, and is never rendered as a time. Its only arithmetic
    is :meth:`elapsed_since`, which yields an elapsed :class:`Duration` — the
    measurement latency, timeout, cooldown, and cadence must use.
    """

    value_ns: int
    boot_epoch_id: str

    @property
    def kind(self) -> ClockKind:
        """The monotonic clock kind (DEC-0106)."""
        return ClockKind.MONOTONIC

    @classmethod
    def try_create(cls, value_ns: object, boot_epoch_id: object) -> Result[MonotonicReading]:
        """Validate and build a :class:`MonotonicReading`, returning value-or-refusal."""
        checked = _as_int64(value_ns)
        if checked is None:
            return _invalid(
                "value_ns",
                "a monotonic reading is a signed int64 nanosecond counter value",
                given=repr(value_ns),
            )
        boot = _clean_str(boot_epoch_id)
        if boot is None:
            return _invalid(
                "boot_epoch_id",
                "a monotonic reading is boot-scoped; it carries a non-empty boot/epoch id",
                given=repr(boot_epoch_id),
            )
        return Ok(cls(value_ns=checked, boot_epoch_id=boot))

    def elapsed_since(self, earlier: object) -> Result[Duration]:
        """The elapsed :class:`Duration` from ``earlier`` to this reading.

        Both readings must share a ``boot_epoch_id`` — a cross-boot (or
        cross-machine) comparison is refused, never differenced, because a
        monotonic counter has no meaning across boots (CT-02; DEC-0106). Overflow
        is refused (FM-2).
        """
        if not isinstance(earlier, MonotonicReading):
            return _invalid(
                "earlier",
                "an elapsed measurement is taken against another MonotonicReading",
                given=repr(earlier),
            )
        if earlier.boot_epoch_id != self.boot_epoch_id:
            return _invalid(
                "boot_epoch_id",
                "monotonic readings are never compared across boots or machines",
                left=self.boot_epoch_id,
                right=earlier.boot_epoch_id,
            )
        checked = _checked_int64(self.value_ns - earlier.value_ns)
        if checked is None:
            return _invalid(
                "value_ns",
                "monotonic subtraction overflowed the int64 range; refused, never wrapped (FM-2)",
                left=self.value_ns,
                right=earlier.value_ns,
            )
        return Ok(Duration(value_ns=checked))


@runtime_checkable
class Clock(Protocol):
    """The core-defined clock seam, injected at the composition root (CT-02;
    DEC-0022, DEC-0106).

    A definitions-only :class:`typing.Protocol`: the composition root injects the
    real clock in production and a :class:`DataDrivenClock` in replay, and **nothing
    below the root reads the system clock** (AR-16). ``boot_epoch_id`` scopes the
    monotonic readings this clock hands out. Wall and monotonic access are
    type-separated by return type: :meth:`wall_now` returns a ``Result[Instant]``,
    :meth:`monotonic_now` a ``Result[MonotonicReading]``. Reading is **value-or-refusal**
    across this seam like every other qmf-core boundary (CT-04; DEC-0109): a real
    clock returns ``Ok`` unconditionally, while a :class:`DataDrivenClock` returns an
    ``unavailable dependency`` refusal once its script is spent — the clock seam never
    raises a domain failure (OR-03).
    """

    boot_epoch_id: str

    def wall_now(self) -> Result[Instant]:  # pragma: no cover - protocol seam
        """The current wall-clock instant (UTC nanoseconds), value-or-refusal."""
        ...

    def monotonic_now(self) -> Result[MonotonicReading]:  # pragma: no cover - protocol seam
        """The current monotonic reading (a boot-scoped diagnostic), value-or-refusal."""
        ...


class DataDrivenClock:
    """A pure, data-driven :class:`Clock` for replay and tests (CT-02; DEC-0106).

    It reads **no** system clock: it replays a scripted, ordered sequence of wall
    :class:`Instant`\\ s and monotonic nanosecond readings, so replay is
    deterministic and nothing below the composition root touches the system clock.
    Exhausting the script — wiring that under-provisioned the replay — is an
    ``unavailable dependency`` typed refusal, **returned never raised**: value-or-refusal
    holds even at the clock seam (OR-03; CT-04, DEC-0109). Each successful read yields
    an ``Ok`` and advances the cursor by exactly one.
    """

    def __init__(
        self,
        *,
        boot_epoch_id: str,
        wall_instants: Sequence[Instant],
        monotonic_ns: Sequence[int],
    ) -> None:
        self.boot_epoch_id: str = boot_epoch_id
        self._wall: tuple[Instant, ...] = tuple(wall_instants)
        self._monotonic: tuple[int, ...] = tuple(monotonic_ns)
        self._wall_cursor: int = 0
        self._monotonic_cursor: int = 0

    def wall_now(self) -> Result[Instant]:
        """Return the next scripted wall instant, or an ``unavailable dependency``
        refusal once the script is spent (OR-03; CT-04, DEC-0109).

        Exhaustion fires at EXACTLY ``cursor == len(script)`` — the ``>= len`` guard,
        the script consumed rather than under-read by one — and the refusal names the
        boundary (cursor, script length) in ``context``, never a pinned prose message
        (CT-02; DEC-0106). Each success advances the cursor by exactly one."""
        if self._wall_cursor >= len(self._wall):
            return _unavailable(
                "wall_instants",
                "the data-driven clock consumed every scripted wall instant; the "
                "replay was under-provisioned (OR-03)",
                cursor=self._wall_cursor,
                script_length=len(self._wall),
            )
        reading = self._wall[self._wall_cursor]
        self._wall_cursor += 1
        return Ok(reading)

    def monotonic_now(self) -> Result[MonotonicReading]:
        """Return the next scripted monotonic reading, or an ``unavailable dependency``
        refusal once the script is spent (OR-03; CT-04, DEC-0109).

        Exhaustion fires at EXACTLY ``cursor == len(script)`` via the ``>= len`` guard;
        the refusal names the boundary (cursor, script length), never a pinned prose
        message. Each success advances the cursor by exactly one (CT-02; DEC-0106)."""
        if self._monotonic_cursor >= len(self._monotonic):
            return _unavailable(
                "monotonic_ns",
                "the data-driven clock consumed every scripted monotonic reading; the "
                "replay was under-provisioned (OR-03)",
                cursor=self._monotonic_cursor,
                script_length=len(self._monotonic),
            )
        value = self._monotonic[self._monotonic_cursor]
        self._monotonic_cursor += 1
        return Ok(MonotonicReading(value_ns=value, boot_epoch_id=self.boot_epoch_id))


# --- writers, sequences, and ordering keys ----------------------------------


@dataclass(frozen=True, slots=True)
class WriterId:
    """A first-class writer identity minted per ``(machine, role, stream)`` with a
    boot/epoch id (CT-02; DEC-0106).

    Stable and durable: a restart is visible through a new ``boot_epoch_id`` without
    changing the ``(machine, role, stream)`` writer identity. A writer id is part
    of an :class:`OrderingKey` — a replay-determinism ordering device — never a
    causal signal.
    """

    machine: str
    role: str
    stream: str
    boot_epoch_id: str

    @classmethod
    def try_create(
        cls, machine: object, role: object, stream: object, boot_epoch_id: object
    ) -> Result[WriterId]:
        """Validate and build a :class:`WriterId`, returning value-or-refusal."""
        machine_token = _clean_str(machine)
        if machine_token is None:
            return _invalid("machine", "a writer id names a non-empty machine", given=repr(machine))
        role_token = _clean_str(role)
        if role_token is None:
            return _invalid("role", "a writer id names a non-empty role", given=repr(role))
        stream_token = _clean_str(stream)
        if stream_token is None:
            return _invalid("stream", "a writer id names a non-empty stream", given=repr(stream))
        boot_token = _clean_str(boot_epoch_id)
        if boot_token is None:
            return _invalid(
                "boot_epoch_id",
                "a writer id carries a non-empty boot/epoch id so restarts are visible",
                given=repr(boot_epoch_id),
            )
        return Ok(
            cls(
                machine=machine_token,
                role=role_token,
                stream=stream_token,
                boot_epoch_id=boot_token,
            )
        )

    def order_tuple(self) -> tuple[str, str, str, str]:
        """The deterministic tie-break key for replay ordering (no causal meaning)."""
        return (self.machine, self.role, self.stream, self.boot_epoch_id)


@dataclass(frozen=True, slots=True)
class OrderingKey:
    """The ``(instant, writer, sequence)`` ordering key (CT-02; DEC-0106, DEC-0108).

    A **replay-determinism** total order with **no causal meaning**: it is never a
    primary or dedup key (a stored record's identity is its ``fp1`` fingerprint) and
    is never used to decide causality (causality compares instants only, via
    :func:`compare_causal`). The ``sequence`` is per-writer strictly increasing and
    is minted by a :class:`WriterSequencer`.
    """

    instant: Instant
    writer: WriterId
    sequence: int

    @classmethod
    def try_create(cls, instant: object, writer: object, sequence: object) -> Result[OrderingKey]:
        """Validate and build an :class:`OrderingKey`, returning value-or-refusal."""
        if not isinstance(instant, Instant):
            return _invalid("instant", "an ordering key carries an Instant", given=repr(instant))
        if not isinstance(writer, WriterId):
            return _invalid("writer", "an ordering key carries a WriterId", given=repr(writer))
        checked = _as_int64(sequence)
        if checked is None or checked < 0:
            return _invalid(
                "sequence",
                "a sequence is a non-negative int64 counter value",
                given=repr(sequence),
            )
        return Ok(cls(instant=instant, writer=writer, sequence=checked))

    def precedes(self, other: object) -> Result[bool]:
        """Whether this key sorts before ``other`` in the total replay order.

        The order is ``(instant, writer, sequence)`` lexicographically — a
        deterministic tie-break for replay, carrying no causal meaning.
        """
        if not isinstance(other, OrderingKey):
            return _invalid("other", "ordering compares another OrderingKey", given=repr(other))
        mine = (self.instant.value_ns, self.writer.order_tuple(), self.sequence)
        theirs = (other.instant.value_ns, other.writer.order_tuple(), other.sequence)
        return Ok(mine < theirs)


class WriterSequencer:
    """Mints a per-writer strictly-increasing sequence (CT-02; DEC-0106).

    Each :meth:`mint` pairs a caller-supplied :class:`Instant` (read through the
    injected :class:`Clock`, never the system clock) with the next sequence value
    for this writer, yielding an :class:`OrderingKey`. The sequence strictly
    increases by construction; it orders a record stream for replay and carries no
    causal meaning.
    """

    def __init__(self, writer: WriterId, *, start: int = 0) -> None:
        self._writer: WriterId = writer
        self._next: int = start

    @property
    def writer(self) -> WriterId:
        """The writer this sequencer mints keys for."""
        return self._writer

    @property
    def next_sequence(self) -> int:
        """The sequence value the next :meth:`mint` will use."""
        return self._next

    def mint(self, instant: Instant) -> OrderingKey:
        """Mint the next :class:`OrderingKey`, advancing the strictly-increasing
        sequence."""
        key = OrderingKey(instant=instant, writer=self._writer, sequence=self._next)
        self._next += 1
        return key


# --- session windows --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SessionWindow:
    """A named open period drawn from a session schedule (CT-02; DEC-0106).

    A half-open ``[open, close)`` span of :class:`Instant`\\ s with a display zone
    label. The session schedule that produces windows is calendar-extension data,
    never assumed constant by any consumer; ``qmf-core`` only defines the value.
    """

    open_instant: Instant
    close_instant: Instant
    zone: str

    @classmethod
    def try_create(
        cls, open_instant: object, close_instant: object, zone: object
    ) -> Result[SessionWindow]:
        """Validate and build a :class:`SessionWindow`, returning value-or-refusal."""
        if not isinstance(open_instant, Instant):
            return _invalid(
                "open_instant", "a session opens at an Instant", given=repr(open_instant)
            )
        if not isinstance(close_instant, Instant):
            return _invalid(
                "close_instant", "a session closes at an Instant", given=repr(close_instant)
            )
        if open_instant.value_ns > close_instant.value_ns:
            return _invalid(
                "open_instant",
                "a session window requires open <= close",
                open=open_instant.value_ns,
                close=close_instant.value_ns,
            )
        label = _clean_str(zone)
        if label is None:
            return _invalid(
                "zone",
                "a session window carries a non-empty display zone label",
                given=repr(zone),
            )
        return Ok(cls(open_instant=open_instant, close_instant=close_instant, zone=label))

    def contains(self, instant: object) -> Result[bool]:
        """Whether ``instant`` lies in ``[open, close)`` (open included, close
        excluded)."""
        if not isinstance(instant, Instant):
            return _invalid("instant", "containment tests an Instant", given=repr(instant))
        return Ok(self.open_instant.value_ns <= instant.value_ns < self.close_instant.value_ns)


# --- display rendering (never identity) -------------------------------------


@dataclass(frozen=True, slots=True)
class DisplayTime:
    """A labelled, display-only rendering of an instant (CT-02; DEC-0106, DEC-0108).

    Local / ISO-8601 time is display-only, **always labelled** with its zone, and
    **excluded from identity** — a :class:`DisplayTime` has deliberately no
    ``fp1_identity``. Identity is the underlying :class:`Instant`'s nanosecond
    count, never this text.
    """

    text: str
    zone: str


def render_utc_iso8601(instant: object) -> Result[DisplayTime]:
    """Render an :class:`Instant` as a labelled UTC ISO-8601 :class:`DisplayTime`.

    UTC (``Z``) is the only zone ``qmf-core`` can render without a tz rule set;
    non-UTC display needs a calendar extension's pinned tzdata. The result is
    display-only and excluded from identity (CT-02; DEC-0106).
    """
    if not isinstance(instant, Instant):
        return _invalid("instant", "rendering takes an Instant", given=repr(instant))
    seconds, nanos = divmod(instant.value_ns, _NANOS_PER_SECOND)
    moment = _EPOCH_UTC + timedelta(seconds=seconds)
    text = (
        f"{moment.year:04d}-{moment.month:02d}-{moment.day:02d}"
        f"T{moment.hour:02d}:{moment.minute:02d}:{moment.second:02d}"
        f".{nanos:09d}Z"
    )
    return Ok(DisplayTime(text=text, zone="UTC"))


# --- causality --------------------------------------------------------------


def compare_causal(earlier: object, later: object) -> Result[TemporalOrder]:
    """Compare two :class:`Instant`\\ s for causal order (CT-02; DEC-0106).

    Causality compares **instants only** — never the ``(instant, writer, sequence)``
    ordering key. At equal instants the two events are concurrent and the
    comparison **refuses** (a ``policy rejection``) rather than tie-break: the
    ordering key exists for replay determinism, not causal meaning.
    """
    if not isinstance(earlier, Instant):
        return _invalid("earlier", "causal comparison takes an Instant", given=repr(earlier))
    if not isinstance(later, Instant):
        return _invalid("later", "causal comparison takes an Instant", given=repr(later))
    if earlier.value_ns < later.value_ns:
        return Ok(TemporalOrder.BEFORE)
    if earlier.value_ns > later.value_ns:
        return Ok(TemporalOrder.AFTER)
    return _policy(
        "instant",
        "equal instants are concurrent; causality does not tie-break — the "
        "(instant, writer, sequence) ordering key carries no causal meaning",
        instant=earlier.value_ns,
    )


# --- tzdata pin verification seam -------------------------------------------


def verify_tzdb_pin(pinned_version: object, resolved_version: object) -> Result[str]:
    """The tzdb-pin verification seam a calendar extension calls at import (CT-02;
    FM-5).

    After the extension forces ``TZPATH`` to its pinned tzdata package, it passes
    the pinned version and the actually-resolved tzdb version here. When they match
    the pinned version is returned; a mismatch is an ``unavailable dependency``
    refusal, so a fingerprint never attests a tzdb that was not the one used.
    ``qmf-core`` embeds no tzdata and reads no environment — the extension resolves
    both versions and this seam only compares them.
    """
    pinned = _clean_str(pinned_version)
    if pinned is None:
        return _invalid(
            "pinned_version",
            "the pinned tzdata version is a non-empty IANA tzdb version string",
            given=repr(pinned_version),
        )
    resolved = _clean_str(resolved_version)
    if resolved is None:
        return _invalid(
            "resolved_version",
            "the resolved tzdata version is a non-empty IANA tzdb version string",
            given=repr(resolved_version),
        )
    if resolved != pinned:
        return _unavailable(
            "tzdata_version",
            "the resolved tzdb version does not equal the extension's pin; a "
            "fingerprint must never attest a tzdb that was not used (FM-5)",
            pinned=pinned,
            resolved=resolved,
        )
    return Ok(pinned)
