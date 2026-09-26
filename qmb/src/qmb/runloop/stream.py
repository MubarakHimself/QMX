"""Shared tick-stream leases and cutover ack (Story 59.1).

AD-28 / FR-WF-67 / FR-WF-68 / J17 / RC-10: two consumers of one tick
subscription. Cancelling one lease leaves the other running. ``refcount`` is
derived from live leases. Cutover requires a barrier plus ``cutover-ack``.
Replay provenance cannot authorize a live command. A stream subscription is
not trading permission. COMP-QMB wraps the protocol; no sixth COMP; GAP-0081
chrome is not filled.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import clean_token, invalid, policy, unsupported

__all__ = [
    "STREAM_BACKPRESSURE_POLICIES",
    "STREAM_CONTROL_KINDS",
    "STREAM_DATA_KIND",
    "STREAM_GAP_0081_CHROME",
    "STREAM_IS_TRADING_PERMISSION",
    "STREAM_PHASES",
    "STREAM_PROTOCOL",
    "STREAM_RECORD_CLASSES",
    "STREAM_REFCOUNT_DERIVED",
    "STREAM_SUBSCRIPTION_FIELDS",
    "STREAM_WRAP_OWNER",
    "StreamControlEvent",
    "StreamCursor",
    "StreamDataEvent",
    "StreamLease",
    "StreamSubscription",
    "ack_stream_cutover",
    "authorize_live_command",
    "begin_stream_cutover",
    "cancel_stream_lease",
    "emit_stream_control",
    "emit_stream_data",
    "live_stream_leases",
    "record_stream_subscription",
    "refuse_subscription_as_trading_permission",
    "shared_feed_consumers",
    "stream_protocol_identity",
]

STREAM_WRAP_OWNER: Final[str] = "COMP-QMB"
STREAM_PROTOCOL: Final[str] = "AD-28"
STREAM_PHASES: Final[tuple[str, ...]] = ("replay", "cutover", "live")
STREAM_BACKPRESSURE_POLICIES: Final[tuple[str, ...]] = (
    "block",
    "disconnect",
    "spill-with-evidence",
)
STREAM_CONTROL_KINDS: Final[tuple[str, ...]] = (
    "gap",
    "duplicate",
    "late",
    "heartbeat",
    "loss",
    "cutover-ack",
    "lease-expire",
)
STREAM_DATA_KIND: Final[str] = "data"
STREAM_RECORD_CLASSES: Final[tuple[str, ...]] = (
    "StreamSubscription",
    "StreamDataEvent",
    "StreamControlEvent",
)
STREAM_SUBSCRIPTION_FIELDS: Final[tuple[str, ...]] = (
    "sub_id",
    "channel",
    "source_id",
    "venue_id",
    "epoch",
    "sequence_domain",
    "phase",
    "cutover_watermark",
    "cursor",
    "cursor_durable",
    "backpressure_policy",
    "leases",
    "refcount",
)
STREAM_REFCOUNT_DERIVED: Final[bool] = True
STREAM_IS_TRADING_PERMISSION: Final[bool] = False
STREAM_GAP_0081_CHROME: Final[bool] = False
_PHASE_REPLAY: Final[str] = "replay"
_PHASE_CUTOVER: Final[str] = "cutover"
_PHASE_LIVE: Final[str] = "live"
_CHROME_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "chrome",
        "qma-ui-contract",
        "qma_ui_contract",
        "ui_view",
        "ui_widget",
        "view",
        "view:*",
    }
)
_SIXTH_COMP_FIELDS: Final[frozenset[str]] = frozenset(
    {"comp", "comp_id", "component", "component_id"}
)
_TRADING_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "grants_live",
        "live_command",
        "trading_grant",
        "trading_permission",
        "venue_command",
    }
)
_PROVIDER_VENUE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "provider",
        "provider_as_venue",
        "provider_venue",
        "source_as_venue",
        "venue_as_source",
    }
)
_RECORD_REASON: Final[str] = (
    "StreamSubscription records sub_id, channel, source_id (provider), optional "
    "venue_id (never the same field), epoch, sequence_domain, phase replay | "
    "cutover | live, cutover_watermark, durable cursor, backpressure_policy "
    "block | disconnect | spill-with-evidence, and lease identities with expiry "
    "(FR-WF-67; RC-10)"
)
_SPLIT_REASON: Final[str] = (
    "records split into StreamSubscription, StreamDataEvent, and control events "
    "gap | duplicate | late | heartbeat | loss | cutover-ack | lease-expire "
    "(FR-WF-67; FR-WF-68)"
)
_REFCOUNT_REASON: Final[str] = (
    "refcount is derived from live (non-expired) leases — never a bare "
    "independently written counter (FR-WF-67; RC-10)"
)
_SOURCE_VENUE_REASON: Final[str] = (
    "source_id is provider and venue_id is venue or null; they are never the "
    "same field (FR-WF-67; J17)"
)
_CANCEL_REASON: Final[str] = (
    "cancelling one consumer releases its lease; a shared feed stays until live "
    "leases are empty (FR-WF-67; J17)"
)
_CUTOVER_REASON: Final[str] = (
    "cutover requires barrier + cutover-ack before live; missing watermark "
    "holds/refuses in cutover (FR-WF-68; J17)"
)
_REPLAY_LIVE_REASON: Final[str] = (
    "replay provenance cannot authorize a live command (FR-WF-68; AD-28)"
)
_NOT_PERMISSION_REASON: Final[str] = (
    "a stream subscription is not trading permission (FR-WF-68; J17)"
)
_CHROME_REASON: Final[str] = "GAP-0081 chrome is not filled; view:* remains an AD-17 wire DTO only"
_SIXTH_COMP_REASON: Final[str] = (
    "stream protocol is wrapped by COMP-QMB; a sixth COMP is not minted (NFR-WF-01)"
)


def stream_protocol_identity() -> dict[str, object]:
    """Identity-bearing stream-protocol schema. Package SemVer is omitted."""
    return {
        "stream_backpressure_policies": STREAM_BACKPRESSURE_POLICIES,
        "stream_control_kinds": STREAM_CONTROL_KINDS,
        "stream_data_kind": STREAM_DATA_KIND,
        "stream_gap_0081_chrome": STREAM_GAP_0081_CHROME,
        "stream_is_trading_permission": STREAM_IS_TRADING_PERMISSION,
        "stream_phases": STREAM_PHASES,
        "stream_protocol": STREAM_PROTOCOL,
        "stream_record_classes": STREAM_RECORD_CLASSES,
        "stream_refcount_derived": STREAM_REFCOUNT_DERIVED,
        "stream_subscription_fields": STREAM_SUBSCRIPTION_FIELDS,
        "stream_wrap_owner": STREAM_WRAP_OWNER,
    }


@dataclass(frozen=True, slots=True)
class StreamCursor:
    """Epoch-scoped sequence cursor. Sequences are not comparable across epochs."""

    epoch: int
    sequence: int

    def as_record(self) -> dict[str, object]:
        """Contract cursor object."""
        return {"epoch": self.epoch, "sequence": self.sequence}

    def at_or_before(self, other: StreamCursor) -> bool:
        """True when this cursor is at-or-before ``other`` in the same epoch."""
        return self.epoch == other.epoch and self.sequence <= other.sequence

    def after(self, other: StreamCursor) -> bool:
        """True when this cursor is strictly after ``other`` in the same epoch."""
        return self.epoch == other.epoch and self.sequence > other.sequence


@dataclass(frozen=True, slots=True)
class StreamLease:
    """One consumer lease on a shared subscription. Expiry drops the lease."""

    lease_id: str
    consumer_id: str
    expires_at: Instant
    renewed_at: Instant

    def is_live(self, now: Instant) -> bool:
        """Live when ``now`` is strictly before expiry."""
        return now.value_ns < self.expires_at.value_ns

    def as_record(self) -> dict[str, object]:
        """Lease identity with expiry."""
        return {
            "consumer_id": self.consumer_id,
            "expires_at": self.expires_at.value_ns,
            "lease_id": self.lease_id,
            "renewed_at": self.renewed_at.value_ns,
        }


@dataclass(frozen=True, slots=True)
class StreamSubscription:
    """Shared tick subscription. ``refcount`` is derived, never independently written."""

    sub_id: str
    channel: str
    source_id: str
    venue_id: str | None
    epoch: int
    sequence_domain: str
    phase: str
    cutover_watermark: StreamCursor | None
    cursor: StreamCursor
    cursor_durable: bool
    buffer_bound: int
    backpressure_policy: str
    shared: bool
    leases: tuple[StreamLease, ...]
    refcount: int
    as_of: Instant

    def as_record(self) -> dict[str, object]:
        """Recorded subscription fields. ``refcount`` is the derived live-lease count."""
        watermark: dict[str, object] | None = None
        if self.cutover_watermark is not None:
            watermark = self.cutover_watermark.as_record()
        return {
            "backpressure_policy": self.backpressure_policy,
            "buffer_bound": self.buffer_bound,
            "channel": self.channel,
            "cursor": self.cursor.as_record(),
            "cursor_durable": self.cursor_durable,
            "cutover_watermark": watermark,
            "epoch": self.epoch,
            "leases": [lease.as_record() for lease in self.leases],
            "phase": self.phase,
            "refcount": self.refcount,
            "sequence_domain": self.sequence_domain,
            "shared": self.shared,
            "source_id": self.source_id,
            "sub_id": self.sub_id,
            "venue_id": self.venue_id,
        }

    def feed_alive(self, now: Instant) -> bool:
        """Shared upstream stays until live leases are empty."""
        return bool(live_stream_leases(self, now))


@dataclass(frozen=True, slots=True)
class StreamDataEvent:
    """One data event on a subscription. Distinct from subscription state."""

    event_kind: str
    sub_id: str
    epoch: int
    sequence: int
    event_time: Instant
    receive_time: Instant
    phase: str
    payload_ref: str

    def as_record(self) -> dict[str, object]:
        """Recorded data event. ``event_kind`` is always ``data``."""
        return {
            "epoch": self.epoch,
            "event_kind": self.event_kind,
            "event_time": self.event_time.value_ns,
            "payload_ref": self.payload_ref,
            "phase": self.phase,
            "receive_time": self.receive_time.value_ns,
            "sequence": self.sequence,
            "sub_id": self.sub_id,
        }


@dataclass(frozen=True, slots=True)
class StreamControlEvent:
    """Typed control/evidence event. Closed ``event_kind`` vocabulary."""

    event_kind: str
    sub_id: str
    epoch: int
    detected_at: Instant
    from_sequence: int | None = None
    to_sequence: int | None = None
    watermark: StreamCursor | None = None
    lease_id: str | None = None

    def as_record(self) -> dict[str, object]:
        """Recorded control event. Kind is one of :data:`STREAM_CONTROL_KINDS`."""
        body: dict[str, object] = {
            "detected_at": self.detected_at.value_ns,
            "epoch": self.epoch,
            "event_kind": self.event_kind,
            "sub_id": self.sub_id,
        }
        if self.from_sequence is not None:
            body["from_sequence"] = self.from_sequence
        if self.to_sequence is not None:
            body["to_sequence"] = self.to_sequence
        if self.watermark is not None:
            body["watermark"] = self.watermark.as_record()
        if self.lease_id is not None:
            body["lease_id"] = self.lease_id
        return body


def live_stream_leases(subscription: StreamSubscription, now: Instant) -> tuple[StreamLease, ...]:
    """Leases that have not expired at ``now``."""
    return tuple(lease for lease in subscription.leases if lease.is_live(now))


def shared_feed_consumers(subscription: StreamSubscription, now: Instant) -> tuple[str, ...]:
    """Consumer ids still attached to the shared feed."""
    return tuple(lease.consumer_id for lease in live_stream_leases(subscription, now))


def record_stream_subscription(payload: object, *, as_of: object) -> Result[StreamSubscription]:
    """Record a shared tick subscription. ``refcount`` is derived from live leases."""
    now = _parse_instant(as_of, "as_of")
    if is_refusal(now):
        return now
    if isinstance(payload, StreamSubscription):
        return Ok(_with_leases(payload, payload.leases, now.value))
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "a StreamSubscription is a key->value mapping",
            given=repr(type(payload).__name__),
        )
    body = cast("Mapping[str, object]", payload)
    blocked = _refuse_forbidden_payload(body)
    if blocked is not None:
        return blocked
    sub_id = clean_token(body.get("sub_id"))
    if sub_id is None:
        return invalid("sub_id", _RECORD_REASON)
    channel = clean_token(body.get("channel"))
    if channel is None:
        return invalid("channel", _RECORD_REASON)
    source_id = clean_token(body.get("source_id"))
    if source_id is None:
        return invalid("source_id", _RECORD_REASON)
    venue_raw = body.get("venue_id")
    venue_id: str | None
    if venue_raw is None:
        venue_id = None
    else:
        venue_id = clean_token(venue_raw)
        if venue_id is None:
            return invalid("venue_id", _SOURCE_VENUE_REASON, given=repr(venue_raw))
        if venue_id == source_id:
            return invalid("venue_id", _SOURCE_VENUE_REASON, source_id=source_id)
    epoch = _non_negative_int(body.get("epoch"), "epoch")
    if is_refusal(epoch):
        return epoch
    domain = clean_token(body.get("sequence_domain"))
    if domain is None:
        return invalid("sequence_domain", _RECORD_REASON)
    phase = clean_token(body.get("phase"))
    if phase is None or phase not in STREAM_PHASES:
        return invalid("phase", _RECORD_REASON, given=repr(body.get("phase")))
    if phase == _PHASE_LIVE:
        return policy("phase", _CUTOVER_REASON, given=phase)
    watermark = _parse_optional_cursor(body.get("cutover_watermark"), "cutover_watermark")
    if is_refusal(watermark):
        return watermark
    cursor = _parse_cursor(body.get("cursor"), "cursor")
    if is_refusal(cursor):
        return cursor
    durable = body.get("cursor_durable", True)
    if not isinstance(durable, bool):
        return invalid("cursor_durable", "cursor_durable is a boolean", given=repr(durable))
    bound = _positive_int(body.get("buffer_bound", 1), "buffer_bound")
    if is_refusal(bound):
        return bound
    policy_token = clean_token(body.get("backpressure_policy"))
    if policy_token is None or policy_token not in STREAM_BACKPRESSURE_POLICIES:
        return invalid(
            "backpressure_policy",
            _RECORD_REASON,
            given=repr(body.get("backpressure_policy")),
        )
    shared = body.get("shared", True)
    if not isinstance(shared, bool):
        return invalid("shared", "shared is a boolean", given=repr(shared))
    leases = _parse_leases(body.get("leases"))
    if is_refusal(leases):
        return leases
    live = tuple(lease for lease in leases.value if lease.is_live(now.value))
    derived = len(live)
    supplied = body.get("refcount")
    if supplied is not None:
        parsed_count = _non_negative_int(supplied, "refcount")
        if is_refusal(parsed_count):
            return parsed_count
        if parsed_count.value != derived:
            return invalid("refcount", _REFCOUNT_REASON, derived=derived, given=supplied)
    return Ok(
        StreamSubscription(
            sub_id=sub_id,
            channel=channel,
            source_id=source_id,
            venue_id=venue_id,
            epoch=epoch.value,
            sequence_domain=domain,
            phase=phase,
            cutover_watermark=watermark.value,
            cursor=cursor.value,
            cursor_durable=durable,
            buffer_bound=bound.value,
            backpressure_policy=policy_token,
            shared=shared,
            leases=leases.value,
            refcount=derived,
            as_of=now.value,
        )
    )


def cancel_stream_lease(
    subscription: StreamSubscription,
    *,
    lease_id: object,
    as_of: object,
) -> Result[StreamSubscription]:
    """Release one lease. Other live consumers keep the shared feed."""
    now = _parse_instant(as_of, "as_of")
    if is_refusal(now):
        return now
    token = clean_token(lease_id)
    if token is None:
        return invalid("lease_id", _CANCEL_REASON, given=repr(lease_id))
    remaining: list[StreamLease] = []
    found = False
    for lease in subscription.leases:
        if lease.lease_id == token:
            found = True
            continue
        remaining.append(lease)
    if not found:
        return invalid("lease_id", _CANCEL_REASON, given=token)
    return Ok(_with_leases(subscription, tuple(remaining), now.value))


def begin_stream_cutover(subscription: StreamSubscription) -> Result[StreamSubscription]:
    """Enter cutover. Live still requires ``cutover-ack``. Missing watermark holds."""
    if subscription.phase == _PHASE_LIVE:
        return policy("phase", _CUTOVER_REASON, given=subscription.phase)
    if subscription.phase == _PHASE_CUTOVER:
        return Ok(subscription)
    return Ok(_with_phase(subscription, _PHASE_CUTOVER))


def ack_stream_cutover(
    subscription: StreamSubscription,
    *,
    watermark: object,
    acked_at: object,
) -> Result[tuple[StreamSubscription, StreamControlEvent]]:
    """Barrier ack. Missing or mismatched watermark refuses and stays in cutover."""
    when = _parse_instant(acked_at, "acked_at")
    if is_refusal(when):
        return when
    parsed = _parse_cursor(watermark, "watermark")
    if is_refusal(parsed):
        return parsed
    if subscription.phase != _PHASE_CUTOVER:
        return policy("phase", _CUTOVER_REASON, given=subscription.phase)
    if subscription.cutover_watermark is None:
        return policy("cutover_watermark", _CUTOVER_REASON)
    if parsed.value != subscription.cutover_watermark:
        return policy(
            "watermark",
            _CUTOVER_REASON,
            given=parsed.value.as_record(),
        )
    if not (
        subscription.cursor.epoch == subscription.cutover_watermark.epoch
        and subscription.cursor.sequence >= subscription.cutover_watermark.sequence
    ):
        return policy("cursor", _CUTOVER_REASON)
    live = _with_phase(subscription, _PHASE_LIVE)
    event = StreamControlEvent(
        event_kind="cutover-ack",
        sub_id=subscription.sub_id,
        epoch=subscription.epoch,
        detected_at=when.value,
        watermark=parsed.value,
    )
    return Ok((live, event))


def emit_stream_data(
    subscription: StreamSubscription,
    *,
    sequence: object,
    event_time: object,
    receive_time: object,
    payload_ref: object,
) -> Result[StreamDataEvent]:
    """Emit one data event. Shared feed delivery is a function of live leases."""
    if not subscription.feed_alive(subscription.as_of):
        return policy("leases", _CANCEL_REASON)
    seq = _non_negative_int(sequence, "sequence")
    if is_refusal(seq):
        return seq
    event_at = _parse_instant(event_time, "event_time")
    if is_refusal(event_at):
        return event_at
    receive_at = _parse_instant(receive_time, "receive_time")
    if is_refusal(receive_at):
        return receive_at
    payload = clean_token(payload_ref)
    if payload is None:
        return invalid("payload_ref", _SPLIT_REASON, given=repr(payload_ref))
    cursor = StreamCursor(epoch=subscription.epoch, sequence=seq.value)
    return Ok(
        StreamDataEvent(
            event_kind=STREAM_DATA_KIND,
            sub_id=subscription.sub_id,
            epoch=subscription.epoch,
            sequence=seq.value,
            event_time=event_at.value,
            receive_time=receive_at.value,
            phase=_classify_phase(subscription, cursor),
            payload_ref=payload,
        )
    )


def emit_stream_control(
    subscription: StreamSubscription,
    *,
    event_kind: object,
    detected_at: object,
    from_sequence: object = None,
    to_sequence: object = None,
    watermark: object = None,
    lease_id: object = None,
) -> Result[StreamControlEvent]:
    """Emit a typed control/evidence event. ``cutover-ack`` does not change phase."""
    kind = clean_token(event_kind)
    if kind is None or kind not in STREAM_CONTROL_KINDS:
        return invalid("event_kind", _SPLIT_REASON, given=repr(event_kind))
    when = _parse_instant(detected_at, "detected_at")
    if is_refusal(when):
        return when
    from_seq: int | None = None
    if from_sequence is not None:
        parsed_from = _non_negative_int(from_sequence, "from_sequence")
        if is_refusal(parsed_from):
            return parsed_from
        from_seq = parsed_from.value
    to_seq: int | None = None
    if to_sequence is not None:
        parsed_to = _non_negative_int(to_sequence, "to_sequence")
        if is_refusal(parsed_to):
            return parsed_to
        to_seq = parsed_to.value
    mark: StreamCursor | None = None
    if watermark is not None:
        parsed_mark = _parse_cursor(watermark, "watermark")
        if is_refusal(parsed_mark):
            return parsed_mark
        mark = parsed_mark.value
    lease_token: str | None = None
    if lease_id is not None:
        lease_token = clean_token(lease_id)
        if lease_token is None:
            return invalid("lease_id", _SPLIT_REASON, given=repr(lease_id))
    return Ok(
        StreamControlEvent(
            event_kind=kind,
            sub_id=subscription.sub_id,
            epoch=subscription.epoch,
            detected_at=when.value,
            from_sequence=from_seq,
            to_sequence=to_seq,
            watermark=mark,
            lease_id=lease_token,
        )
    )


def authorize_live_command(
    subscription: StreamSubscription,
    *,
    provenance_phase: object,
) -> Result[bool]:
    """Authorize a live command. Replay provenance cannot; cutover is not live."""
    phase = clean_token(provenance_phase)
    if phase is None or phase not in STREAM_PHASES:
        return invalid("provenance_phase", _REPLAY_LIVE_REASON, given=repr(provenance_phase))
    if _PHASE_REPLAY in (phase, subscription.phase):
        return policy("provenance_phase", _REPLAY_LIVE_REASON, phase=phase)
    if phase != _PHASE_LIVE or subscription.phase != _PHASE_LIVE:
        return policy("phase", _CUTOVER_REASON, phase=subscription.phase, provenance=phase)
    return Ok(True)


def refuse_subscription_as_trading_permission(
    subscription: StreamSubscription,
) -> TypedRefusal:
    """A stream subscription is never trading permission."""
    return policy(
        "stream_subscription",
        _NOT_PERMISSION_REASON,
        sub_id=subscription.sub_id,
        trading_permission=STREAM_IS_TRADING_PERMISSION,
    )


def _classify_phase(subscription: StreamSubscription, cursor: StreamCursor) -> str:
    watermark = subscription.cutover_watermark
    if watermark is None or cursor.at_or_before(watermark):
        return _PHASE_REPLAY
    if subscription.phase == _PHASE_LIVE:
        return _PHASE_LIVE
    return subscription.phase


def _with_leases(
    subscription: StreamSubscription,
    leases: tuple[StreamLease, ...],
    as_of: Instant,
) -> StreamSubscription:
    live = tuple(lease for lease in leases if lease.is_live(as_of))
    return StreamSubscription(
        sub_id=subscription.sub_id,
        channel=subscription.channel,
        source_id=subscription.source_id,
        venue_id=subscription.venue_id,
        epoch=subscription.epoch,
        sequence_domain=subscription.sequence_domain,
        phase=subscription.phase,
        cutover_watermark=subscription.cutover_watermark,
        cursor=subscription.cursor,
        cursor_durable=subscription.cursor_durable,
        buffer_bound=subscription.buffer_bound,
        backpressure_policy=subscription.backpressure_policy,
        shared=subscription.shared,
        leases=leases,
        refcount=len(live),
        as_of=as_of,
    )


def _with_phase(subscription: StreamSubscription, phase: str) -> StreamSubscription:
    return StreamSubscription(
        sub_id=subscription.sub_id,
        channel=subscription.channel,
        source_id=subscription.source_id,
        venue_id=subscription.venue_id,
        epoch=subscription.epoch,
        sequence_domain=subscription.sequence_domain,
        phase=phase,
        cutover_watermark=subscription.cutover_watermark,
        cursor=subscription.cursor,
        cursor_durable=subscription.cursor_durable,
        buffer_bound=subscription.buffer_bound,
        backpressure_policy=subscription.backpressure_policy,
        shared=subscription.shared,
        leases=subscription.leases,
        refcount=subscription.refcount,
        as_of=subscription.as_of,
    )


def _refuse_forbidden_payload(body: Mapping[str, object]) -> TypedRefusal | None:
    for key in _CHROME_FIELDS:
        if key in body:
            return unsupported(key, _CHROME_REASON, gap="GAP-0081")
    for key in _SIXTH_COMP_FIELDS:
        token = clean_token(body.get(key))
        if token is None:
            continue
        if token != STREAM_WRAP_OWNER:
            return unsupported(key, _SIXTH_COMP_REASON, given=token)
    for key in _TRADING_FIELDS:
        if key in body and body.get(key) not in (None, False):
            return policy(key, _NOT_PERMISSION_REASON)
    for key in _PROVIDER_VENUE_FIELDS:
        if key in body:
            return invalid(key, _SOURCE_VENUE_REASON)
    event_kind = clean_token(body.get("event_kind"))
    if event_kind == STREAM_DATA_KIND:
        return invalid("event_kind", _SPLIT_REASON)
    if event_kind in STREAM_CONTROL_KINDS:
        return invalid("event_kind", _SPLIT_REASON)
    return None


def _parse_leases(value: object) -> Result[tuple[StreamLease, ...]]:
    if not isinstance(value, (list, tuple)):
        return invalid(
            "leases",
            "leases are a sequence of lease identities with expiry",
            given=repr(type(value).__name__),
        )
    sequence = cast("Sequence[object]", value)
    if len(sequence) < 1:
        return invalid("leases", _RECORD_REASON)
    out: list[StreamLease] = []
    seen_lease: set[str] = set()
    seen_consumer: set[str] = set()
    for index, item in enumerate(sequence):
        parsed = _parse_lease(item, index)
        if is_refusal(parsed):
            return parsed
        lease = parsed.value
        if lease.lease_id in seen_lease:
            return invalid("lease_id", "lease identities are unique", lease_id=lease.lease_id)
        if lease.consumer_id in seen_consumer:
            return invalid(
                "consumer_id",
                "each live consumer holds one lease",
                consumer_id=lease.consumer_id,
            )
        seen_lease.add(lease.lease_id)
        seen_consumer.add(lease.consumer_id)
        out.append(lease)
    return Ok(tuple(out))


def _parse_lease(value: object, index: int) -> Result[StreamLease]:
    if not isinstance(value, Mapping):
        return invalid("leases", "each lease is a mapping of identity plus expiry", index=index)
    body = cast("Mapping[str, object]", value)
    lease_id = clean_token(body.get("lease_id"))
    if lease_id is None:
        return invalid("lease_id", _RECORD_REASON, index=index)
    consumer_id = clean_token(body.get("consumer_id"))
    if consumer_id is None:
        return invalid("consumer_id", _RECORD_REASON, index=index)
    expires = _parse_instant(body.get("expires_at"), "expires_at")
    if is_refusal(expires):
        return expires
    renewed = _parse_instant(body.get("renewed_at"), "renewed_at")
    if is_refusal(renewed):
        return renewed
    if not (renewed.value.value_ns <= expires.value.value_ns):
        return invalid("expires_at", "lease expiry is at-or-after renewed_at", index=index)
    return Ok(
        StreamLease(
            lease_id=lease_id,
            consumer_id=consumer_id,
            expires_at=expires.value,
            renewed_at=renewed.value,
        )
    )


def _parse_optional_cursor(value: object, field: str) -> Result[StreamCursor | None]:
    if value is None:
        return Ok(None)
    parsed = _parse_cursor(value, field)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value)


def _parse_cursor(value: object, field: str) -> Result[StreamCursor]:
    if isinstance(value, StreamCursor):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(field, "a cursor is {epoch, sequence}", given=repr(type(value).__name__))
    body = cast("Mapping[str, object]", value)
    epoch = _non_negative_int(body.get("epoch"), field)
    if is_refusal(epoch):
        return epoch
    sequence = _non_negative_int(body.get("sequence"), field)
    if is_refusal(sequence):
        return sequence
    return Ok(StreamCursor(epoch=epoch.value, sequence=sequence.value))


def _parse_instant(value: object, field: str) -> Result[Instant]:
    if isinstance(value, Instant):
        return Ok(value)
    created = Instant.try_create(value)
    if is_refusal(created):
        return invalid(
            field,
            "an instant is an int64 UTC-nanosecond count",
            given=repr(value),
        )
    return created


def _positive_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return invalid(field, "a positive int is required", given=repr(value))
    return Ok(value)


def _non_negative_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, "a non-negative int is required", given=repr(value))
    return Ok(value)
