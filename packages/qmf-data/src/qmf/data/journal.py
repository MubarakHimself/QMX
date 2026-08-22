"""CT-13 — the durable journal-event vocabulary, owned by COMP-QMF-DATA (AC1-AC4).

The value vocabulary of the durable journal: a state change recorded as **evidence
encoding** — an ``int64`` UTC-nanosecond instant plus an AD-8
:class:`~qmf.core.WriterId` plus a strictly-increasing per-writer sequence — one of
exactly **seven ratified event types**. This module pins the vocabulary; the
:mod:`qmf.data.journal_producer` boundary appends it through the Story 3.1 store seam
and enforces the gapless-sequence and block-on-unpersistable discipline.

Four things this module pins down.

**Seven event types, addable but never redefined (AC1; DEC-0119, DEC-0116).**
:class:`JournalEventType` is the closed V1 set — decision, order, fill, risk
transition, promotion, data quality, control action. It is a ``StrEnum``, so a later
version may **add** a type; the seven existing meanings never change. A record whose
type is outside the set never becomes a journal event (an ``invalid input`` refusal).
QMF's own wired producers are qmf-data itself (data quality, control action).

**The decision event's mandatory closed outcome (AC3; DEC-0158, DEC-0150).** A
``decision`` event carries a mandatory :class:`DecisionOutcome` — ``authorized |
refused-by-door | suppressed`` — with the refusing-door or suppressing-authority
reference in its payload, so a projection (the legacy ``veto_ledger`` included)
selects on that **declared field**, never on key presence (:func:`select_decisions`,
:func:`veto_ledger`). A non-decision event carries no outcome; a decision event
without one does not build.

**fp1 identity, with correlation_id and display_time excluded (AC4; DEC-0112,
DEC-0108).** A journal event's identity is its ``fp1`` fingerprint, computed by the
single ``qmf-core`` implementation over :meth:`JournalEvent.fp1_identity`. Two
declared parts are **excluded from identity by this explicit versioned declaration**
(:data:`CORRELATION_ID_EXCLUDED_FROM_FP1`): ``correlation_id`` — a linking annotation
that still propagates across package boundaries — and the optional ``display_time``, a
display-only ISO-8601-with-Z rendering. Journals are evidence encoding (int64 UTC ns +
writer + sequence); operator/diagnostic logs are the ISO-8601-Z display, a distinct
thing (:meth:`JournalEvent.render_display_time`).

**Cross-stream causal linkage rides only typed edge records (AC4; DEC-0119,
DEC-0114).** ``(instant, writer, sequence)`` is a replay-determinism
:class:`~qmf.core.OrderingKey` with **no causal meaning** — causality never rides a
timestamp or the ordering key. Causal linkage across streams is a
:class:`CausalEdge`, an AD-16 typed edge record referencing two events by their ``fp1``
fingerprints (the CT-07 lineage-edge shape qmf-data emits as a value; DEC-0120).

A detected sequence gap **signals loss and is surfaced** (:func:`detect_sequence_gaps`)
— never swallowed. Stdlib + qmf-core (fp1 comes only from qmf-core); frozen, immutable
values throughout.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    DisplayTime,
    Fingerprint,
    Instant,
    Ok,
    OrderingKey,
    Result,
    Retryability,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
    render_utc_iso8601,
)
from qmf.data.store.refusals import invalid_input, storage_failure

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "CORRELATION_ID_EXCLUDED_FROM_FP1",
    "DISPLAY_TIME_EXCLUDED_FROM_FP1",
    "CausalEdge",
    "DecisionOutcome",
    "JournalEvent",
    "JournalEventType",
    "detect_sequence_gaps",
    "select_decisions",
    "veto_ledger",
]

# CT-13 carries its own integer contract format version, stamped into every journal
# artifact; its meaning never mutates — an incompatible change mints the next version
# plus a migration note (DEC-0103; versioning-from-birth L15). CT-13's own, not CT-05's.
CONTRACT_FORMAT_VERSION: Final[int] = 1

# The explicit, versioned declaration that correlation_id is a linking annotation
# EXCLUDED from fp1 identity (DEC-0112, DEC-0108). It is a named design choice recorded
# at source — never an implementer's per-call judgment — so two events differing only in
# correlation_id share one identity, while the annotation still propagates in the stored
# row and across package boundaries.
CORRELATION_ID_EXCLUDED_FROM_FP1: Final[bool] = True

# The optional display_time (ISO-8601-with-Z) is display-only and likewise excluded from
# identity — journals store the int64-ns instant, logs render the display time (DEC-0112).
DISPLAY_TIME_EXCLUDED_FROM_FP1: Final[bool] = True

# One shared immutable empty payload; an event always carries a present mapping, never a
# null (the same idiom qmf-core's SinkAck detail uses).
_EMPTY_PAYLOAD: Final[Mapping[str, object]] = MappingProxyType({})


class JournalEventType(StrEnum):
    """The seven ratified journal event types (CT-13 ``registry:journal_event_types``).

    A ``StrEnum`` so a later contract version may **add** a type; the seven V1 meanings
    are fixed and never redefined (DEC-0119). QMF's own wired producers are qmf-data
    (``DATA_QUALITY``, ``CONTROL_ACTION``); the other five are produced by qmf-registry
    (promotion), qmf-venue (order, fill), and qmf-risk (decision, risk transition,
    control action) through the core-defined ``JournalSink`` injected at the composition
    root (DEC-0116, DEC-0138, DEC-0145).
    """

    DECISION = "decision"
    ORDER = "order"
    FILL = "fill"
    RISK_TRANSITION = "risk transition"
    PROMOTION = "promotion"
    DATA_QUALITY = "data quality"
    CONTROL_ACTION = "control action"


class DecisionOutcome(StrEnum):
    """The mandatory closed outcome of a ``decision`` event (CT-13; DEC-0158, DEC-0150).

    Every decision event declares exactly one: ``AUTHORIZED`` (the act was permitted),
    ``REFUSED_BY_DOOR`` (a door refused it — the refusing-door reference rides the
    payload), or ``SUPPRESSED`` (a higher authority discarded an already-authorized act
    at arbitration — the suppressing-authority reference rides the payload). A projection
    selects on this declared field, never on key presence.
    """

    AUTHORIZED = "authorized"
    REFUSED_BY_DOOR = "refused-by-door"
    SUPPRESSED = "suppressed"


# The payload key a refused-by-door / suppressed decision carries its reference under.
_REFUSING_DOOR_KEY: Final[str] = "refusing_door"
_SUPPRESSING_AUTHORITY_KEY: Final[str] = "suppressing_authority"


def _coerce_world(value: object) -> World | None:
    """Resolve ``value`` to a :class:`~qmf.core.World` member, or ``None``."""
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def _as_instant(value: object) -> Instant | None:
    """Resolve ``value`` to an :class:`~qmf.core.Instant`, or ``None``.

    Accepts an :class:`~qmf.core.Instant` or an int64 UTC-nanosecond count (built through
    ``Instant.try_create`` so the range check is qmf-core's, never restated here).
    """
    if isinstance(value, Instant):
        return value
    built = Instant.try_create(value)
    return built.value if is_ok(built) else None


def _coerce_event_type(value: object) -> JournalEventType | None:
    """Resolve ``value`` to a :class:`JournalEventType`, or ``None`` (outside the seven)."""
    if isinstance(value, JournalEventType):
        return value
    if isinstance(value, str):
        try:
            return JournalEventType(value)
        except ValueError:
            return None
    return None


def _coerce_decision_outcome(value: object) -> DecisionOutcome | None:
    """Resolve ``value`` to a :class:`DecisionOutcome`, or ``None``."""
    if isinstance(value, DecisionOutcome):
        return value
    if isinstance(value, str):
        try:
            return DecisionOutcome(value)
        except ValueError:
            return None
    return None


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    return parsed.value if is_ok(parsed) else None


def _freeze(value: object) -> object:
    """Recursively snapshot ``value`` into a shared-safe, read-only form.

    A ``Mapping`` becomes a :class:`~types.MappingProxyType` over frozen values and a
    list/tuple becomes a tuple, so a nested container reached through the caller's dict
    can never mutate the frozen event's payload (the same idiom qmf-core's SinkAck uses).
    """
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return MappingProxyType({key: _freeze(item) for key, item in mapping.items()})
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return tuple(_freeze(item) for item in sequence)
    return value


def _writer_identity(writer: WriterId) -> dict[str, object]:
    """The writer's identity content — :class:`~qmf.core.WriterId` exposes no
    ``fp1_identity``, so its ``(machine, role, stream, boot_epoch_id)`` parts are folded
    in explicitly and consistently (the same shape the CT-10 boundary uses)."""
    return {
        "machine": writer.machine,
        "role": writer.role,
        "stream": writer.stream,
        "boot_epoch_id": writer.boot_epoch_id,
    }


def _validate_decision_payload(
    event_type: JournalEventType, outcome: DecisionOutcome | None, payload: Mapping[str, object]
) -> Result[DecisionOutcome | None]:
    """Enforce the decision-event outcome law (AC3; DEC-0158, DEC-0150).

    A ``decision`` event MUST carry a :class:`DecisionOutcome`, and a refused-by-door /
    suppressed decision MUST carry its refusing-door / suppressing-authority reference in
    the payload (a non-empty string), so a projection selects on the declared field with a
    resolvable reference. Any other event type MUST NOT carry an outcome. Returns the
    validated outcome (or ``None``), or an ``invalid input`` refusal.
    """
    if event_type is not JournalEventType.DECISION:
        if outcome is not None:
            return invalid_input(
                "outcome",
                "only a decision event carries an outcome; a non-decision event must not",
                event_type=event_type.value,
            )
        return Ok(None)
    if outcome is None:
        return invalid_input(
            "outcome",
            "a decision event carries a mandatory closed outcome: "
            "authorized | refused-by-door | suppressed (DEC-0158)",
        )
    if outcome is DecisionOutcome.REFUSED_BY_DOOR and not _has_reference(
        payload, _REFUSING_DOOR_KEY
    ):
        return invalid_input(
            "refusing_door",
            "a refused-by-door decision carries the refusing-door reference in its payload "
            "so a projection resolves who refused, never on key presence (DEC-0158)",
        )
    if outcome is DecisionOutcome.SUPPRESSED and not _has_reference(
        payload, _SUPPRESSING_AUTHORITY_KEY
    ):
        return invalid_input(
            "suppressing_authority",
            "a suppressed decision carries the suppressing-authority reference in its "
            "payload so a projection resolves who suppressed it (DEC-0150)",
        )
    return Ok(outcome)


def _has_reference(payload: Mapping[str, object], key: str) -> bool:
    """Whether ``payload`` carries a non-blank string reference under ``key``."""
    value = payload.get(key)
    return isinstance(value, str) and value.strip() != ""


def _identity_content(
    *,
    event_type: JournalEventType,
    writer: WriterId,
    sequence: int,
    instant: Instant,
    world: World,
    payload: Mapping[str, object],
    outcome: DecisionOutcome | None,
) -> dict[str, object]:
    """The event's canonical ``fp1`` identity content — the parts that ARE its identity.

    Built identically by :meth:`JournalEvent.try_create` (to compute the fingerprint) and
    :meth:`JournalEvent.fp1_identity` (so a read-back re-fingerprints to the same value).
    ``correlation_id`` and ``display_time`` are **deliberately excluded** (the versioned
    declaration above); the instant is folded in as its int64-ns identity, and the outcome
    is present only for a decision event.
    """
    content: dict[str, object] = {
        "class": "journal-event",
        "event_type": event_type.value,
        "writer": _writer_identity(writer),
        "sequence": sequence,
        "instant": instant.fp1_identity(),
        "world": world.value,
        "payload": dict(payload),
        "format_version": CONTRACT_FORMAT_VERSION,
    }
    if outcome is not None:
        content["outcome"] = outcome.value
    return content


@dataclass(frozen=True, slots=True)
class JournalEvent:
    """One durable journal event — evidence encoding, fp1-identified (AC1, AC3, AC4).

    Its ``fingerprint`` is its identity, computed by the single ``qmf-core``
    implementation over :meth:`fp1_identity`. The identity is the ``event_type``, the
    ``writer`` ``(machine, role, stream, boot_epoch_id)``, the strictly-increasing
    ``sequence``, the int64-ns ``instant``, the ``world``, the event-type ``payload``,
    and — for a decision event — the ``outcome``. ``correlation_id`` and ``display_time``
    are carried but **excluded from identity** (:data:`CORRELATION_ID_EXCLUDED_FROM_FP1`,
    :data:`DISPLAY_TIME_EXCLUDED_FROM_FP1`).

    ``(instant, writer, sequence)`` is a replay-ordering :class:`~qmf.core.OrderingKey`
    with no causal meaning (:meth:`ordering_key`); causal linkage across streams is a
    :class:`CausalEdge`, never a timestamp or the ordering key. The frozen constructor is
    the trusted-internal path; :meth:`try_create` is the validating factory, and
    :meth:`from_row` re-verifies the fingerprint so a tampered row never reads back valid.
    """

    event_type: JournalEventType
    writer: WriterId
    sequence: int
    instant: Instant
    world: World
    fingerprint: Fingerprint
    payload: Mapping[str, object] = field(default=_EMPTY_PAYLOAD)
    outcome: DecisionOutcome | None = None
    correlation_id: str | None = None
    display_time: DisplayTime | None = None

    def __post_init__(self) -> None:
        # Deep-freeze the payload so a later mutation of the caller's dict — or of a
        # nested dict/list inside it — can never reach back into this frozen event.
        object.__setattr__(self, "payload", _freeze(self.payload))

    @classmethod
    def try_create(
        cls,
        *,
        event_type: object,
        writer: object,
        sequence: object,
        instant: object,
        world: object,
        payload: Mapping[str, object] | None = None,
        outcome: object | None = None,
        correlation_id: object | None = None,
        display_time: object | None = None,
    ) -> Result[JournalEvent]:
        """Validate the parts, compute the ``fp1`` identity, and build the event (AC1, AC3).

        ``event_type`` must be one of the seven :class:`JournalEventType` values (a type
        outside the set is an ``invalid input`` refusal — the enum is addable, never
        redefined). ``writer`` is a :class:`~qmf.core.WriterId`; ``sequence`` a
        non-negative integer; ``instant`` an :class:`~qmf.core.Instant` or int64 UTC-ns
        count; ``world`` a :class:`~qmf.core.World` (or its string). A decision event
        requires a closed :class:`DecisionOutcome` plus its reference; any other event
        must omit the outcome (AC3). ``correlation_id`` and ``display_time`` are optional
        and excluded from identity. The fingerprint is **not** supplied — it is computed
        by ``qmf-core`` over the identity content (a binary float or null in the payload
        is refused there), so identity is minted nowhere else.
        """
        resolved_type = _coerce_event_type(event_type)
        if resolved_type is None:
            return invalid_input(
                "event_type",
                "a journal event is one of exactly seven types: decision, order, fill, "
                "risk transition, promotion, data quality, control action (DEC-0119)",
                given=repr(event_type),
                allowed=[member.value for member in JournalEventType],
            )
        if not isinstance(writer, WriterId):
            return invalid_input(
                "writer",
                "a journal event is written under an AD-8 WriterId with its boot/epoch id",
                given=repr(writer),
            )
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            return invalid_input(
                "sequence",
                "sequence is a per-writer non-negative strictly-increasing integer, "
                "gapless per (writer, boot-epoch) (DEC-0119)",
                given=repr(sequence),
            )
        resolved_instant = _as_instant(instant)
        if resolved_instant is None:
            return invalid_input(
                "instant",
                "the event instant is an Instant or int64 UTC-nanosecond count (evidence "
                "encoding, never an ISO-8601 display string)",
                given=repr(instant),
            )
        resolved_world = _coerce_world(world)
        if resolved_world is None:
            return invalid_input(
                "world",
                "world is one of the closed set live | replay | simulated",
                given=repr(world),
            )
        resolved_outcome_input = _resolve_outcome(outcome)
        if is_refusal(resolved_outcome_input):
            return resolved_outcome_input
        resolved_display = _resolve_display_time(display_time)
        if is_refusal(resolved_display):
            return resolved_display
        clean_correlation = _resolve_correlation_id(correlation_id)
        if is_refusal(clean_correlation):
            return clean_correlation

        resolved_payload: Mapping[str, object] = payload if payload is not None else _EMPTY_PAYLOAD
        checked_outcome = _validate_decision_payload(
            resolved_type, resolved_outcome_input.value, resolved_payload
        )
        if is_refusal(checked_outcome):
            return checked_outcome

        content = _identity_content(
            event_type=resolved_type,
            writer=writer,
            sequence=sequence,
            instant=resolved_instant,
            world=resolved_world,
            payload=resolved_payload,
            outcome=checked_outcome.value,
        )
        fp = fingerprint(content)
        if is_refusal(fp):
            return fp
        return Ok(
            cls(
                event_type=resolved_type,
                writer=writer,
                sequence=sequence,
                instant=resolved_instant,
                world=resolved_world,
                fingerprint=fp.value,
                payload=resolved_payload,
                outcome=checked_outcome.value,
                correlation_id=clean_correlation.value,
                display_time=resolved_display.value,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content; its fingerprint equals
        :attr:`fingerprint`. ``correlation_id`` and ``display_time`` are excluded (AC4)."""
        return _identity_content(
            event_type=self.event_type,
            writer=self.writer,
            sequence=self.sequence,
            instant=self.instant,
            world=self.world,
            payload=self.payload,
            outcome=self.outcome,
        )

    def ordering_key(self) -> OrderingKey:
        """The ``(instant, writer, sequence)`` replay-ordering key — **no causal meaning**.

        A replay-determinism total order (:class:`~qmf.core.OrderingKey`), never a primary
        or dedup key (identity is the fingerprint) and never a causal signal — causality
        compares instants only, and cross-stream causal linkage is a :class:`CausalEdge`.
        """
        return OrderingKey(instant=self.instant, writer=self.writer, sequence=self.sequence)

    def render_display_time(self) -> Result[DisplayTime]:
        """The event's instant rendered as a labelled UTC ISO-8601 :class:`DisplayTime`.

        Journals store the int64-ns ``instant`` as evidence; an operator/diagnostic log
        renders THIS display time (ISO-8601 with an explicit Z) — a distinct, display-only
        thing excluded from identity (AC4; DEC-0112). Rendering routes through ``qmf-core``.
        """
        return render_utc_iso8601(self.instant)

    def to_row(self) -> dict[str, object]:
        """A flat, JSON-native serialization for the journal stream (AC4).

        Carries every identity field plus the event's own ``fingerprint`` (so a governed
        reader has the identity without recomputing), and — when present — the
        non-identity ``correlation_id`` and ``display_time`` (stored and propagated, never
        folded into identity). The instant is stored as int64 UTC ns. All values are
        ``int`` / ``str`` / nested ``dict`` / ``list``, so the row canonicalizes and
        round-trips exactly through :meth:`from_row`.
        """
        row: dict[str, object] = {
            "event_type": self.event_type.value,
            "writer": _writer_identity(self.writer),
            "sequence": self.sequence,
            "instant_ns": self.instant.value_ns,
            "world": self.world.value,
            "payload": dict(self.payload),
            "fingerprint": self.fingerprint.value,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.outcome is not None:
            row["outcome"] = self.outcome.value
        if self.correlation_id is not None:
            row["correlation_id"] = self.correlation_id
        if self.display_time is not None:
            row["display_time"] = {"text": self.display_time.text, "zone": self.display_time.zone}
        return row

    @classmethod
    def from_row(cls, row: object) -> Result[JournalEvent]:
        """Reconstruct an event from a persisted :meth:`to_row` row, verifying its ``fp1``.

        Rebuilds the value through :meth:`try_create` (so a malformed row is an ``invalid
        input`` refusal exactly as at admission) and then checks the recomputed fingerprint
        equals the row's stored ``fingerprint`` — a mismatch means the stored evidence was
        corrupted or tampered and is refused, never returned as valid (DEC-0108). The
        excluded ``correlation_id`` / ``display_time`` read back from the row but never
        affect the identity check.
        """
        if not isinstance(row, Mapping):
            return invalid_input("row", "a persisted journal row is a mapping", given=repr(row))
        mapping = cast("Mapping[str, object]", row)
        stored_fp = _coerce_fingerprint(mapping.get("fingerprint"))
        if stored_fp is None:
            return invalid_input(
                "fingerprint",
                "a persisted journal row carries its fp1:sha256:<hex> fingerprint",
                given=repr(mapping.get("fingerprint")),
            )
        built = cls.try_create(
            event_type=mapping.get("event_type"),
            writer=_row_writer(mapping.get("writer")),
            sequence=mapping.get("sequence"),
            instant=mapping.get("instant_ns"),
            world=mapping.get("world"),
            payload=_row_payload(mapping.get("payload")),
            outcome=mapping.get("outcome"),
            correlation_id=mapping.get("correlation_id"),
            display_time=_row_display_time(mapping.get("display_time")),
        )
        if is_refusal(built):
            return built
        if built.value.fingerprint.value != stored_fp.value:
            return invalid_input(
                "fingerprint",
                "the stored row does not re-fingerprint to its recorded fp1; the evidence "
                "is corrupt or tampered and is refused rather than read back as valid",
                stored=stored_fp.value,
                recomputed=built.value.fingerprint.value,
            )
        return built


# --- optional-part resolvers (used by try_create) ---------------------------


def _resolve_outcome(value: object | None) -> Result[DecisionOutcome | None]:
    """Resolve the optional decision outcome: ``None``, a member, or a refusal."""
    if value is None:
        return Ok(None)
    resolved = _coerce_decision_outcome(value)
    if resolved is None:
        return invalid_input(
            "outcome",
            "a decision outcome is one of the closed set authorized | refused-by-door | suppressed",
            given=repr(value),
            allowed=[member.value for member in DecisionOutcome],
        )
    return Ok(resolved)


def _resolve_display_time(value: object | None) -> Result[DisplayTime | None]:
    """Resolve the optional display time: ``None``, a :class:`~qmf.core.DisplayTime`,
    or a refusal. Excluded from identity, so it never affects the fingerprint."""
    if value is None:
        return Ok(None)
    if isinstance(value, DisplayTime):
        return Ok(value)
    return invalid_input(
        "display_time",
        "display_time is an optional qmf-core DisplayTime (ISO-8601-Z, display-only); it "
        "is excluded from identity (DEC-0112)",
        given=repr(value),
    )


def _resolve_correlation_id(value: object | None) -> Result[str | None]:
    """Resolve the optional correlation_id: ``None`` or a non-blank string, else refuse.

    Excluded from fp1 identity by the versioned declaration, but still validated as a
    clean token so it round-trips and propagates without ambiguity (DEC-0112, DEC-0108).
    """
    if value is None:
        return Ok(None)
    if isinstance(value, str) and value.strip() != "":
        return Ok(value)
    return invalid_input(
        "correlation_id",
        "correlation_id, when present, is a non-blank linking annotation (or omitted); it "
        "is excluded from fp1 identity but propagated across boundaries (DEC-0112)",
        given=repr(value),
    )


# --- row-reconstruction helpers (used by from_row) --------------------------


def _row_writer(value: object) -> object:
    """Rebuild a :class:`~qmf.core.WriterId` from a persisted ``writer`` sub-mapping.

    Returns the built ``WriterId`` on success, or the offending value unchanged so
    :meth:`JournalEvent.try_create` surfaces the one ``invalid input`` refusal (this
    helper never invents a refusal of its own).
    """
    if not isinstance(value, Mapping):
        return value
    block = cast("Mapping[str, object]", value)
    built = WriterId.try_create(
        block.get("machine"),
        block.get("role"),
        block.get("stream"),
        block.get("boot_epoch_id"),
    )
    return built.value if is_ok(built) else block


def _row_payload(value: object) -> Mapping[str, object]:
    """The persisted payload as a mapping (an absent payload reads back as empty)."""
    if isinstance(value, Mapping):
        return cast("Mapping[str, object]", value)
    return _EMPTY_PAYLOAD


def _row_display_time(value: object) -> object:
    """Rebuild a :class:`~qmf.core.DisplayTime` from a persisted ``display_time`` block.

    Returns the built value, ``None`` when absent, or the offending value unchanged so
    :meth:`JournalEvent.try_create` surfaces the one refusal.
    """
    if value is None:
        return None
    if not isinstance(value, Mapping):
        return value
    block = cast("Mapping[str, object]", value)
    text = block.get("text")
    zone = block.get("zone")
    if isinstance(text, str) and isinstance(zone, str):
        return DisplayTime(text=text, zone=zone)
    return block


# --- cross-stream causal linkage (typed edge records) -----------------------


@dataclass(frozen=True, slots=True)
class CausalEdge:
    """A cross-stream causal link as an AD-16 typed edge record (AC4; DEC-0114, DEC-0120).

    Causal linkage across journal streams rides **only** typed edge records — never a
    timestamp and never the ``(instant, writer, sequence)`` ordering key. An edge names its
    ``edge_type`` (a CT-07 lineage-edge type, e.g. ``enacts``, ``supersedes``,
    ``occurrence-of``), references its two endpoints by their ``fp1`` fingerprints
    (``from_ref`` the accruing/derived endpoint, ``to_ref`` the referenced one), and is
    written under a single :class:`~qmf.core.WriterId`. qmf-data emits this as a value the
    application routes to qmf-registry's lineage-edge stream (DEC-0120); it never rewrites
    a record in place.
    """

    edge_type: str
    from_ref: Fingerprint
    to_ref: Fingerprint
    writer: WriterId

    @classmethod
    def try_create(
        cls, *, edge_type: object, from_ref: object, to_ref: object, writer: object
    ) -> Result[CausalEdge]:
        """Validate and build a :class:`CausalEdge`, returning value-or-refusal.

        ``edge_type`` is a non-blank CT-07 edge-type token; ``from_ref`` and ``to_ref``
        are :class:`~qmf.core.Fingerprint`\\ s (or ``fp1:sha256:<hex>`` strings) — an edge
        references records by their fp1, never a mutable or minted id; ``writer`` is the
        single edge-stream :class:`~qmf.core.WriterId`.
        """
        if not isinstance(edge_type, str) or edge_type.strip() == "":
            return invalid_input(
                "edge_type",
                "a causal edge names a non-blank CT-07 edge type (e.g. enacts, supersedes, "
                "occurrence-of)",
                given=repr(edge_type),
            )
        resolved_from = _coerce_fingerprint(from_ref)
        if resolved_from is None:
            return invalid_input(
                "from_ref",
                "a causal edge references its endpoints by fp1:sha256:<hex>, never a "
                "timestamp or the ordering key (DEC-0114, DEC-0108)",
                given=repr(from_ref),
            )
        resolved_to = _coerce_fingerprint(to_ref)
        if resolved_to is None:
            return invalid_input(
                "to_ref",
                "a causal edge references its endpoints by fp1:sha256:<hex>, never a "
                "timestamp or the ordering key (DEC-0114, DEC-0108)",
                given=repr(to_ref),
            )
        if not isinstance(writer, WriterId):
            return invalid_input(
                "writer",
                "a causal edge stream has exactly one holding WriterId (DEC-0113)",
                given=repr(writer),
            )
        return Ok(
            cls(
                edge_type=edge_type,
                from_ref=resolved_from,
                to_ref=resolved_to,
                writer=writer,
            )
        )

    @classmethod
    def link(cls, edge_type: object, from_event: object, to_event: object) -> Result[CausalEdge]:
        """Build the causal edge linking two :class:`JournalEvent`\\ s by their ``fp1``.

        The edge references ``from_event.fingerprint`` and ``to_event.fingerprint`` — the
        identity fp1s (which exclude ``correlation_id``), so a causal link never rides a
        correlation annotation, a timestamp, or the ordering key. The edge is written under
        ``from_event``'s writer. A non-event argument is an ``invalid input`` refusal.
        """
        if not isinstance(from_event, JournalEvent):
            return invalid_input(
                "from_event", "a causal link is from a JournalEvent", given=repr(from_event)
            )
        if not isinstance(to_event, JournalEvent):
            return invalid_input(
                "to_event", "a causal link is to a JournalEvent", given=repr(to_event)
            )
        return cls.try_create(
            edge_type=edge_type,
            from_ref=from_event.fingerprint,
            to_ref=to_event.fingerprint,
            writer=from_event.writer,
        )

    def to_row(self) -> dict[str, object]:
        """The CT-07-shaped typed edge record, JSON-native for a pinned-JSONL edge stream."""
        return {
            "edge_type": self.edge_type,
            "from_ref": self.from_ref.value,
            "to_ref": self.to_ref.value,
            "writer": _writer_identity(self.writer),
            "contract_format_version": CONTRACT_FORMAT_VERSION,
        }


# --- gap detection and decision projections ---------------------------------


def detect_sequence_gaps(
    events: Iterable[JournalEvent], *, expected_start: int = 0
) -> Result[None]:
    """Scan a stream's events for a per-``(writer, boot-epoch)`` sequence gap (AC2).

    A stream's sequence is strictly increasing and **gapless** per ``(writer,
    boot-epoch)``; a detected gap **signals loss and is surfaced** — a ``storage failure``
    refusal (retryability ``no``: a lost event will not reappear on a re-read), never a
    silent success. Events are grouped by ``(machine, role, stream, boot_epoch_id)`` and
    each group must run contiguously from ``expected_start`` (the ``WriterSequencer`` start,
    ``0`` by default) with no missing value and no duplicate. Returns ``Ok(None)`` when
    every group is gapless.
    """
    per_writer: dict[tuple[str, str, str, str], list[int]] = {}
    for event in events:
        key = (
            event.writer.machine,
            event.writer.role,
            event.writer.stream,
            event.writer.boot_epoch_id,
        )
        per_writer.setdefault(key, []).append(event.sequence)
    for key, sequences in per_writer.items():
        ordered = sorted(sequences)
        expected = expected_start
        for found in ordered:
            if found == expected:
                expected += 1
                continue
            signal = "duplicate" if found < expected else "gap"
            return storage_failure(
                f"a {signal} in the journal sequence signals loss for writer "
                f"(machine={key[0]}, role={key[1]}, stream={key[2]}, boot_epoch={key[3]}): "
                f"expected sequence {expected}, found {found}; the stream is gapless per "
                "(writer, boot-epoch) and the loss is surfaced, never swallowed (DEC-0119)",
                retryability=Retryability.NO,
                context={
                    "signal": "loss",
                    "kind": signal,
                    "machine": key[0],
                    "role": key[1],
                    "stream": key[2],
                    "boot_epoch": key[3],
                    "expected_sequence": expected,
                    "found_sequence": found,
                },
            )
    return Ok(None)


def select_decisions(
    events: Iterable[JournalEvent], *, outcome: DecisionOutcome | None = None
) -> list[JournalEvent]:
    """Select ``decision`` events, optionally by their declared ``outcome`` (AC3).

    Selection is on the **declared** ``event_type`` and ``outcome`` fields, never on key
    presence (DEC-0158, DEC-0150): a projection filtering ``outcome=refused-by-door`` reads
    the closed field every decision event carries, so it can never silently miss a decision
    that lacks some ad-hoc key. With ``outcome=None`` every decision event is returned.
    """
    decisions = [event for event in events if event.event_type is JournalEventType.DECISION]
    if outcome is None:
        return decisions
    return [event for event in decisions if event.outcome is outcome]


def veto_ledger(events: Iterable[JournalEvent]) -> list[JournalEvent]:
    """The legacy ``veto_ledger`` projection — decisions ``refused-by-door`` (AC3).

    The legacy ``veto_ledger`` survives as a projection **name** only; it selects on the
    decision event's declared ``outcome = refused-by-door`` field, never on key presence
    (DEC-0158). The full projection surface — entity journals and the CT-25 legacy-stream
    mapping table — lands in Story 3.6; this is the decision-outcome selector Story 3.5 owns.
    """
    return select_decisions(events, outcome=DecisionOutcome.REFUSED_BY_DOOR)
