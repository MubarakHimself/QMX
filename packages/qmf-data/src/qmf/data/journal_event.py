"""CT-13 JournalEvent value — evidence encoding, fp1-identified.

Split from :mod:`qmf.data.journal` so the public module stays under the Skylos
god-file limits. Callers keep importing :class:`JournalEvent` from
:mod:`qmf.data.journal`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import cast

from qmf.core import (
    DisplayTime,
    Fingerprint,
    Instant,
    Ok,
    OrderingKey,
    Result,
    World,
    WriterId,
    fingerprint,
    is_ok,
    is_refusal,
    render_utc_iso8601,
)
from qmf.data.journal_build import (
    identity_content,
    resolve_event_core,
    resolve_event_extras,
)
from qmf.data.journal_types import (
    CONTRACT_FORMAT_VERSION,
    EMPTY_PAYLOAD,
    DecisionOutcome,
    JournalEventType,
    coerce_fingerprint,
    freeze_value,
    writer_identity,
)
from qmf.data.store.refusals import invalid_input

__all__ = ["JournalEvent"]


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
    payload: Mapping[str, object] = field(default=EMPTY_PAYLOAD)
    outcome: DecisionOutcome | None = None
    correlation_id: str | None = None
    display_time: DisplayTime | None = None

    def __post_init__(self) -> None:
        # Deep-freeze the payload so a later mutation of the caller's dict — or of a
        # nested dict/list inside it — can never reach back into this frozen event.
        object.__setattr__(self, "payload", freeze_value(self.payload))

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
        core = resolve_event_core(event_type, writer, sequence, instant, world)
        if is_refusal(core):
            return core
        extras = resolve_event_extras(
            payload, outcome, correlation_id, display_time, core.value[0]
        )
        if is_refusal(extras):
            return extras
        return _mint_journal_event(cls, core.value, extras.value)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content; its fingerprint equals
        :attr:`fingerprint`. ``correlation_id`` and ``display_time`` are excluded (AC4)."""
        return identity_content(
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
            "writer": writer_identity(self.writer),
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
        stored_fp = coerce_fingerprint(mapping.get("fingerprint"))
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


def _mint_journal_event(
    cls: type[JournalEvent],
    core: tuple[JournalEventType, WriterId, int, Instant, World],
    extras: tuple[Mapping[str, object], DecisionOutcome | None, str | None, DisplayTime | None],
) -> Result[JournalEvent]:
    """Fingerprint identity content and construct the frozen event."""
    event_type, writer, sequence, instant, world = core
    payload, outcome, correlation_id, display_time = extras
    content = identity_content(
        event_type=event_type,
        writer=writer,
        sequence=sequence,
        instant=instant,
        world=world,
        payload=payload,
        outcome=outcome,
    )
    fp = fingerprint(content)
    if is_refusal(fp):
        return fp
    return Ok(
        cls(
            event_type=event_type,
            writer=writer,
            sequence=sequence,
            instant=instant,
            world=world,
            fingerprint=fp.value,
            payload=payload,
            outcome=outcome,
            correlation_id=correlation_id,
            display_time=display_time,
        )
    )


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
    return EMPTY_PAYLOAD


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
