"""Live cTrader :class:`~qmn.venue.port.VenueClientPort` (Story 24.3).

Converts and records the broker stream exactly: verbatim wire evidence and the
CT-13 journal mapping land **before** interpretation, money/volume cross only
declared exact-integer scale boundaries, and receive-wall time stays distinct
from venue event time. A float without a declared rounding rule is refused.

FTR-01 leaves position/balance read-back mapping onto CT-13 unresolved — those
observation kinds are refused here and no eighth node-private journal type is
minted. Spots, trendbars-in-spots, depth, fills, and lifecycle keep going.

Unmapped venue error codes take the fail-closed alarmed
``transient / non-retryable / UNKNOWN`` posture with the raw code retained; the
client never retries a command automatically. Credential-free gates inject a
Clock and sink set; live-network conformance stays ``@pytest.mark.live``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import (
    Account,
    Clock,
    Instant,
    MonotonicReading,
    Ok,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    World,
    is_refusal,
)
from qmf.venue.capabilities import ErrorMap, ErrorMapResolution
from qmf.venue.commands import Command, CompoundCommand, SubmissionResult
from qmf.venue.connection import ConnectionManager
from qmf.venue.ctrader import (
    MARKET_DATA_WIRE_SCALE_EXPONENT,
    decode_execution_price,
    decode_market_data_price,
    decode_money,
    decode_timestamp,
)
from qmf.venue.events import (
    EventRecorder,
    InboundVenueEvent,
    ObservationKind,
    Reconciliation,
    ReconciliationVerdict,
    TransactionBoundary,
    VenueNativeIdentity,
)

from qmn.venue.conformance import compound_command_acceptance_blocked
from qmn.venue.port import VenueClientKind
from qmn.venue.verify import VenueFactVerification, ctrader_static_declaration

__all__ = [
    "CT13_SEVEN_EVENT_TYPES",
    "FTR01_BLOCKED_KINDS",
    "VOLUME_WIRE_SCALE_EXPONENT",
    "JournalMapping",
    "LiveCTraderClient",
    "WireKind",
    "ct13_journal_event_type",
    "decode_volume",
    "ftr01_position_balance_blocked",
]


class _LiveIntake(Protocol):
    """Duck-typed governed intake: persist then fold (Story 27.2)."""

    def record(self, **kwargs: object) -> Result[object]:
        """Record one inbound observation through the accumulator."""
        ...


# Volumes are cents everywhere on the wire (including lotSize; depth size ÷100)
# — exact scale-2 integers, never a binary-float divide (DEC-0135, DEC-0141).
VOLUME_WIRE_SCALE_EXPONENT: Final[int] = 2

# AD-21 / CT-13 closed seven — never an eighth node-private type (FTR-01).
CT13_SEVEN_EVENT_TYPES: Final[frozenset[str]] = frozenset(
    {
        "decision",
        "order",
        "fill",
        "risk transition",
        "promotion",
        "data quality",
        "control action",
    }
)

_FTR01_REFUSAL: Final[TypedRefusal] = TypedRefusal(
    category=RefusalCategory.UNSUPPORTED_CAPABILITY,
    retryability=Retryability.NO,
    context={
        "field": "observation_kind",
        "reason": "position/balance read-back mapping onto CT-13 remains unresolved "
        "(FTR-01); no eighth node-private journal type is minted",
        "ftr": "FTR-01",
        "blocked": ("position-readback", "balance-readback"),
    },
)


class WireKind(StrEnum):
    """Inbound live-stream kinds the Story 24.3 client accepts or refuses."""

    SPOT = "spot"
    TRENDBAR_IN_SPOT = "trendbar-in-spot"
    DEPTH = "depth"
    FILL = "fill"
    LIFECYCLE = "lifecycle"
    POSITION_READBACK = "position-readback"
    BALANCE_READBACK = "balance-readback"


FTR01_BLOCKED_KINDS: Final[frozenset[WireKind]] = frozenset(
    {WireKind.POSITION_READBACK, WireKind.BALANCE_READBACK}
)

# Lifecycle CT-20 observation kinds that journal as CT-13 ``order``.
_LIFECYCLE_OBS: Final[frozenset[ObservationKind]] = frozenset(
    {
        ObservationKind.SUBMISSION_ACKNOWLEDGEMENT,
        ObservationKind.CANCEL_ACKNOWLEDGEMENT,
        ObservationKind.EXPIRY,
        ObservationKind.CLOSE_BY_VENUE,
    }
)


def ftr01_position_balance_blocked() -> TypedRefusal:
    """Typed refusal every position/balance read-back path returns until FTR-01 lands."""
    return _FTR01_REFUSAL


def ct13_journal_event_type(kind: object) -> Result[str]:
    """Map an accepted wire/observation kind onto one of CT-13's seven event types.

    Position/balance read-backs are refused (FTR-01). Market-data kinds journal as
    ``data quality`` occurrence provenance for the intake mapping row — never a new
    type. Fills → ``fill``; lifecycle → ``order``.
    """
    wire = _coerce_wire(kind)
    if wire is not None:
        if wire in FTR01_BLOCKED_KINDS:
            return ftr01_position_balance_blocked()
        if wire in {WireKind.SPOT, WireKind.TRENDBAR_IN_SPOT, WireKind.DEPTH}:
            return Ok("data quality")
        if wire is WireKind.FILL:
            return Ok("fill")
        if wire is WireKind.LIFECYCLE:
            return Ok("order")
    obs = _coerce_obs(kind)
    if obs is ObservationKind.FILL:
        return Ok("fill")
    if obs in _LIFECYCLE_OBS:
        return Ok("order")
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context={
            "field": "kind",
            "reason": "ct13_journal_event_type requires an accepted WireKind or "
            "CT-20 lifecycle/fill ObservationKind",
            "given": repr(kind),
            "allowed_ct13": sorted(CT13_SEVEN_EVENT_TYPES),
        },
    )


def decode_volume(wire_value: object, *, unit: object = "lot") -> Result[Quantity]:
    """Decode a cTrader volume (cents) to an exact :class:`~qmf.core.Quantity`.

    Volumes are integer cents on the wire (DEC-0135). A binary float is refused —
    there is no float→volume crossing without a declared rounding rule, and this
    path declares none.
    """
    if isinstance(wire_value, float):
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "wire_value",
                "reason": "a volume float crossing without a declared rounding rule is "
                "refused; cTrader volumes are exact integer cents",
                "given": repr(wire_value),
                "scale": VOLUME_WIRE_SCALE_EXPONENT,
            },
        )
    if isinstance(wire_value, bool) or not isinstance(wire_value, int) or wire_value < 0:
        return TypedRefusal(
            category=RefusalCategory.INVALID_INPUT,
            retryability=Retryability.NO,
            context={
                "field": "wire_value",
                "reason": "a cTrader volume is a non-negative integer count of cents",
                "given": repr(wire_value),
            },
        )
    return Quantity.try_create(wire_value, unit, VOLUME_WIRE_SCALE_EXPONENT)


@dataclass(frozen=True, slots=True)
class JournalMapping:
    """The CT-13 journal mapping row persisted before interpretation (Story 24.3)."""

    event_type: str
    wire_kind: str
    receive_wall_time_ns: int
    venue_instant_ns: int | None
    native_id: str
    raw_code: str | None = None

    def as_mapping(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "event_type": self.event_type,
            "wire_kind": self.wire_kind,
            "receive_wall_time_ns": self.receive_wall_time_ns,
            "native_id": self.native_id,
            "format": "ct13-journal-mapping",
        }
        if self.venue_instant_ns is not None:
            payload["venue_instant_ns"] = self.venue_instant_ns
        if self.raw_code is not None:
            payload["raw_venue_code"] = self.raw_code
        return MappingProxyType(payload)


@dataclass
class LiveCTraderClient:
    """Live cTrader client composed around ``qmf-venue`` shapes (DEC-0196, DEC-0228).

    Network dial stays optional: credential-free tests inject a :class:`~qmf.core.Clock`
    and sink set and push wire frames through :meth:`receive`. Automatic command
    retry is impossible — there is no retry path.
    """

    _world: World
    _venue_id: VenueId
    _clock: Clock
    _error_map: ErrorMap
    _session_epoch: str
    _connection_manager: ConnectionManager | None = None
    _recorder: EventRecorder | None = None
    _intake: _LiveIntake | None = None
    _account: Account | None = None
    _session_open: bool = False
    _capabilities_verified: bool = False
    _verification: VenueFactVerification | None = None
    _observations: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    _commands_retried: int = 0

    @classmethod
    def try_create(
        cls,
        world: object,
        venue_id: object,
        *,
        clock: object,
        error_map: object,
        session_epoch: object = "session-epoch-1",
        connection_manager: object = None,
        recorder: object = None,
        intake: object = None,
    ) -> Result[LiveCTraderClient]:
        """Build a live client for ``(world, VenueId)`` with injected Clock/ErrorMap."""
        if not isinstance(world, World):
            return _invalid(
                "world", "live client is selected by (world, VenueId)", given=repr(world)
            )
        if world is World.REPLAY:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "world",
                    "reason": "replay compositions bind the replay VenueClientPort, "
                    "never the live cTrader client",
                    "world": world.value,
                },
            )
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid(
                "venue_id", "live client requires a valid VenueId", given=repr(venue_id)
            )
        if venue_id.value.startswith("conformance:"):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "venue_id",
                    "reason": "conformance: VenueId selects the FEAT-0023 double, "
                    "not the live cTrader client",
                    "venue_id": venue_id.value,
                },
            )
        if not isinstance(clock, Clock):
            return _invalid(
                "clock",
                "the composition root injects a Clock; the live client never reads "
                "the system clock",
                given=repr(clock),
            )
        if not isinstance(error_map, ErrorMap):
            return _invalid(
                "error_map",
                "the live client resolves venue codes against a pinned ErrorMap",
                given=repr(error_map),
            )
        if not isinstance(session_epoch, str) or session_epoch.strip() == "":
            return _invalid(
                "session_epoch",
                "a non-empty session-epoch id rides every observation",
                given=repr(session_epoch),
            )
        cm: ConnectionManager | None
        if connection_manager is None:
            cm = None
        elif isinstance(connection_manager, ConnectionManager):
            cm = connection_manager
        else:
            return _invalid(
                "connection_manager",
                "when supplied, connection_manager must be a ConnectionManager",
                given=repr(connection_manager),
            )
        rec: EventRecorder | None
        if recorder is None:
            rec = None
        elif isinstance(recorder, EventRecorder):
            rec = recorder
        else:
            return _invalid(
                "recorder",
                "when supplied, recorder must be an EventRecorder",
                given=repr(recorder),
            )
        bound_intake: _LiveIntake | None
        if intake is None:
            bound_intake = None
        elif callable(getattr(intake, "record", None)):
            bound_intake = cast("_LiveIntake", intake)
        else:
            return _invalid(
                "intake",
                "when supplied, intake is a GovernedLiveIntake (record method)",
                given=repr(type(intake).__name__),
            )
        return Ok(
            cls(
                _world=world,
                _venue_id=venue_id,
                _clock=clock,
                _error_map=error_map,
                _session_epoch=session_epoch.strip(),
                _connection_manager=cm,
                _recorder=rec,
                _intake=bound_intake,
            )
        )

    @property
    def kind(self) -> VenueClientKind:
        return VenueClientKind.CTRADER

    @property
    def venue_id(self) -> VenueId:
        return self._venue_id

    @property
    def world(self) -> World:
        return self._world

    @property
    def commands_retried(self) -> int:
        """Always zero — the live client never retries a command automatically."""
        return self._commands_retried

    @property
    def auto_retry_enabled(self) -> bool:
        return False

    @property
    def account(self) -> Account | None:
        """The open-session account, if any."""
        return self._account

    def open_session(self, account: object) -> Result[bool]:
        if not isinstance(account, Account):
            return _invalid("account", "open_session requires an Account", given=repr(account))
        if account.venue != self._venue_id:
            return _invalid(
                "account",
                "account does not belong to this VenueId",
                venue=self._venue_id.value,
                account_venue=account.venue.value,
            )
        self._account = account
        self._session_open = True
        return Ok(True)

    def close_session(self) -> Result[bool]:
        self._session_open = False
        self._account = None
        self._capabilities_verified = False
        return Ok(True)

    def verify_capabilities(self) -> Result[Mapping[str, object]]:
        """CT-18 readiness — static declaration present; measured profile from verifier.

        Credential-free path: callers that already verified via Story 24.2 may mark
        readiness through :meth:`accept_verification`. Without a measured profile this
        returns an unavailable-dependency refusal rather than inventing facts.
        """
        if not self._session_open or self._account is None:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "session",
                    "reason": "capability verification requires an open session",
                },
                after_condition_descriptor="open_session",
            )
        if self._verification is None:
            declaration = ctrader_static_declaration()
            if is_refusal(declaration):
                return declaration
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "measured_profile",
                    "reason": "live client requires an injected VenueFactVerification "
                    "(Story 24.2) before evidence-bearing decode; call "
                    "accept_verification with verified facts",
                    "static_declaration_present": True,
                },
                after_condition_descriptor="accept_verification",
            )
        if not self._verification.command_sequencer_open:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "command_sequencer",
                    "reason": "verified profile left the command sequencer closed",
                    "defects": {
                        key: value.value for key, value in self._verification.defects.items()
                    },
                },
            )
        self._capabilities_verified = True
        profile: dict[str, object] = {
            "verified": True,
            "static_declaration_present": True,
            "measured_at_connection": True,
            "profile_version": self._verification.profile_version,
            "command_sequencer_open": True,
            "market_data_recordable": self._verification.market_data_recordable,
            "proto_tag": 91,
        }
        self._observations.append({"kind": "capability-profile", "profile": dict(profile)})
        return Ok(profile)

    def accept_verification(self, verification: object) -> Result[bool]:
        """Bind a Story 24.2 :class:`VenueFactVerification` outcome into this client."""
        if not isinstance(verification, VenueFactVerification):
            return _invalid(
                "verification",
                "accept_verification requires a VenueFactVerification",
                given=repr(verification),
            )
        self._verification = verification
        return Ok(True)

    def submit(self, command: object) -> Result[SubmissionResult]:
        if isinstance(command, CompoundCommand):
            return compound_command_acceptance_blocked()
        if not isinstance(command, Command):
            return _invalid(
                "command",
                "submit requires a CT-19 Command",
                given=type(command).__name__,
            )
        if not self._session_open or not self._capabilities_verified:
            return TypedRefusal(
                category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
                retryability=Retryability.AFTER_CONDITION,
                context={
                    "field": "readiness",
                    "reason": "submit requires an open session and verified capabilities",
                },
                after_condition_descriptor="open_session then verify_capabilities",
            )
        # Story 24.3 senses and records; wire handoff of money-path commands waits
        # for the order-path stories. Never invent an accepted outcome or retry.
        return TypedRefusal(
            category=RefusalCategory.UNSUPPORTED_CAPABILITY,
            retryability=Retryability.NO,
            context={
                "field": "submit",
                "reason": "live command wire handoff is out of Story 24.3 scope; "
                "sensing/recording only — no automatic retry",
                "auto_retry": False,
                "commands_retried": self._commands_retried,
            },
        )

    def observations(self) -> Result[Sequence[Mapping[str, object]]]:
        return Ok(tuple(dict(item) for item in self._observations))

    def reconcile(self) -> Result[Reconciliation]:
        # Position/balance read-back mapping is FTR-01-blocked; reconciliation that
        # would journal those kinds as an eighth type is refused as unavailable.
        return TypedRefusal(
            category=RefusalCategory.UNSUPPORTED_CAPABILITY,
            retryability=Retryability.NO,
            context={
                "field": "reconcile",
                "reason": "on-demand reconciliation that surfaces position/balance "
                "read-backs stays blocked until FTR-01's CT-13 mapping annotation "
                "lands; no eighth journal type is minted",
                "ftr": "FTR-01",
                "verdict_vocabulary": [m.value for m in ReconciliationVerdict],
            },
        )

    def resolve_venue_error(
        self, venue_code: object, context: object
    ) -> Result[ErrorMapResolution]:
        """Decode a venue error against the pinned map; never auto-retry.

        An unmapped code yields the alarmed fail-closed default
        ``(transient venue failure, retryable = no, outcome = UNKNOWN)`` with the
        raw code retained on the resolution and on the observation buffer.
        """
        resolved = self._error_map.resolve(venue_code, context)
        if is_refusal(resolved):
            return resolved
        outcome = resolved.value
        # Hard law: unmapped → alarm + no retry; mapped retryability is never
        # turned into an automatic client retry either.
        if not outcome.mapped and (
            not outcome.alarm or outcome.retryability is not Retryability.NO
        ):
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "error_map",
                    "reason": "unmapped venue error must be alarmed transient/"
                    "non-retryable/UNKNOWN with raw code retained",
                    "venue_code": outcome.venue_code,
                    "alarm": outcome.alarm,
                    "retryability": outcome.retryability.value,
                },
            )
        self._observations.append(
            {
                "kind": "venue-error",
                "venue_code": outcome.venue_code,
                "context": outcome.context,
                "mapped": outcome.mapped,
                "alarm": outcome.alarm,
                "outcome_class": outcome.outcome_class.value,
                "refusal_category": outcome.refusal_category.value,
                "retryability": outcome.retryability.value,
                "auto_retry": False,
                "raw_code_retained": outcome.venue_code,
            }
        )
        return Ok(outcome)

    def receive(
        self,
        wire_kind: object,
        raw_payload: object,
        *,
        native_id: object,
        instrument: object = None,
        venue_time_raw: object = None,
        venue_time_unit: object = "milliseconds",
        revision: object = 0,
        lifecycle_kind: object = None,
        fill_price_wire: object = None,
        fill_price_is_execution_double: object = False,
        fill_digits: object = None,
        fill_rounding: object = None,
        fill_volume_wire: object = None,
        money_message: object = None,
        money_units: object = None,
        money_currency: object = None,
        money_digits: object = None,
        volume_wire: object = None,
        market_price_wire: object = None,
        depth_size_wire: object = None,
    ) -> Result[Mapping[str, object]]:
        """Ingest one wire frame: record verbatim + journal map, then decode.

        Order is mandatory: observation-sink emit and journal mapping append happen
        **before** scale conversion / interpretation. Position and balance
        read-backs refuse under FTR-01 without recording an eighth journal type.
        """
        kind = _coerce_wire(wire_kind)
        if kind is None:
            return _invalid(
                "wire_kind",
                "receive requires a WireKind",
                given=repr(wire_kind),
                allowed=[m.value for m in WireKind],
            )
        if kind in FTR01_BLOCKED_KINDS:
            return ftr01_position_balance_blocked()
        if not isinstance(raw_payload, Mapping):
            return _invalid(
                "raw_payload",
                "the raw payload is recorded verbatim as a present mapping",
                given=type(raw_payload).__name__,
            )
        if not isinstance(native_id, str) or native_id.strip() == "":
            return _invalid(
                "native_id",
                "every inbound frame carries a non-empty venue-native id",
                given=repr(native_id),
            )
        wall = self._clock.wall_now()
        if is_refusal(wall):
            return wall
        mono = self._clock.monotonic_now()
        if is_refusal(mono):
            return mono
        receive_wall = wall.value
        monotonic = mono.value

        journal_type = ct13_journal_event_type(kind)
        if is_refusal(journal_type):
            return journal_type
        if journal_type.value not in CT13_SEVEN_EVENT_TYPES:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "event_type",
                    "reason": "journal mapping must land on CT-13's closed seven; "
                    "an eighth type is refused",
                    "given": journal_type.value,
                },
            )

        # --- venue event time (optional; distinct from receive wall) ----------
        venue_instant: Instant | None = None
        if venue_time_raw is not None:
            decoded_ts = decode_timestamp(venue_time_raw, venue_time_unit, receive_wall)
            if is_refusal(decoded_ts):
                return decoded_ts
            venue_instant = decoded_ts.value.instant

        verbatim: dict[str, object] = {
            "kind": "verbatim-wire",
            "wire_kind": kind.value,
            "native_id": native_id.strip(),
            "raw_payload": dict(cast("Mapping[str, object]", raw_payload)),
            "receive_wall_time_ns": receive_wall.value_ns,
            "monotonic_ns": monotonic.value_ns,
            "boot_epoch": monotonic.boot_epoch_id,
            "session_epoch": self._session_epoch,
            "venue_instant_ns": venue_instant.value_ns if venue_instant is not None else None,
            "interpreted": False,
        }
        mapping = JournalMapping(
            event_type=journal_type.value,
            wire_kind=kind.value,
            receive_wall_time_ns=receive_wall.value_ns,
            venue_instant_ns=venue_instant.value_ns if venue_instant is not None else None,
            native_id=native_id.strip(),
        )

        # Record-before-interpret: accumulator (when bound) is the single first writer.
        persisted = self._persist_before_interpret(
            verbatim,
            mapping,
            kind=kind,
            native_id=native_id.strip(),
            receive_wall=receive_wall,
            venue_instant=venue_instant,
            revision=revision,
            instrument=instrument,
        )
        if is_refusal(persisted):
            return persisted

        decoded = self._interpret(
            kind=kind,
            raw_payload=cast("Mapping[str, object]", raw_payload),
            native_id=native_id.strip(),
            revision=revision,
            receive_wall=receive_wall,
            monotonic=monotonic,
            venue_instant=venue_instant,
            instrument=instrument,
            lifecycle_kind=lifecycle_kind,
            fill_price_wire=fill_price_wire,
            fill_price_is_execution_double=bool(fill_price_is_execution_double),
            fill_digits=fill_digits,
            fill_rounding=fill_rounding,
            fill_volume_wire=fill_volume_wire,
            money_message=money_message,
            money_units=money_units,
            money_currency=money_currency,
            money_digits=money_digits,
            volume_wire=volume_wire,
            market_price_wire=market_price_wire,
            depth_size_wire=depth_size_wire,
        )
        if is_refusal(decoded):
            return decoded

        record = decoded.value
        record["verbatim_recorded"] = True
        record["journal_mapping"] = dict(mapping.as_mapping())
        record["receive_wall_time_ns"] = receive_wall.value_ns
        record["venue_instant_ns"] = venue_instant.value_ns if venue_instant is not None else None
        record["times_retained_separately"] = True
        self._observations.append(dict(record))
        return Ok(MappingProxyType(dict(record)))

    def _persist_before_interpret(
        self,
        verbatim: Mapping[str, object],
        mapping: JournalMapping,
        *,
        kind: WireKind,
        native_id: str,
        receive_wall: Instant,
        venue_instant: Instant | None,
        revision: object,
        instrument: object,
    ) -> Result[bool]:
        """Emit verbatim wire + journal mapping before any scale conversion."""
        if self._intake is not None:
            stream_id = native_id
            symbol = getattr(instrument, "symbol", None)
            if isinstance(symbol, str) and symbol.strip() != "":
                stream_id = symbol.strip()
            recorded = self._intake.record(
                observation_id=native_id,
                stream_id=stream_id,
                receive_wall=receive_wall,
                payload=dict(verbatim),
                kind=kind.value,
                source="ctrader",
                source_native_id=native_id,
                revision=str(revision) if revision is not None else "0",
                event_time=venue_instant if venue_instant is not None else receive_wall,
                known_at=receive_wall,
                venue_instant=venue_instant,
                raw_payload=verbatim.get("raw_payload", verbatim),
            )
            if is_refusal(recorded):
                return recorded
            return Ok(True)
        if self._connection_manager is not None:
            obs = self._connection_manager.emit_command_observation(dict(verbatim))
            if is_refusal(obs):
                return obs
            journalled = self._connection_manager.append_command_journal(dict(mapping.as_mapping()))
            if is_refusal(journalled):
                return journalled
        else:
            # Credential-free / unit path: retain on the client buffer as the
            # record-before-interpret evidence trail (no ambient store).
            self._observations.append(
                {
                    "kind": "record-before-interpret",
                    "phase": "verbatim",
                    "payload": dict(verbatim),
                }
            )
            self._observations.append(
                {
                    "kind": "record-before-interpret",
                    "phase": "journal-mapping",
                    "payload": dict(mapping.as_mapping()),
                }
            )
        return Ok(True)

    def _interpret(
        self,
        *,
        kind: WireKind,
        raw_payload: Mapping[str, object],
        native_id: str,
        revision: object,
        receive_wall: Instant,
        monotonic: MonotonicReading,
        venue_instant: Instant | None,
        instrument: object,
        lifecycle_kind: object,
        fill_price_wire: object,
        fill_price_is_execution_double: bool,
        fill_digits: object,
        fill_rounding: object,
        fill_volume_wire: object,
        money_message: object,
        money_units: object,
        money_currency: object,
        money_digits: object,
        volume_wire: object,
        market_price_wire: object,
        depth_size_wire: object,
    ) -> Result[dict[str, object]]:
        """Scale conversion / typed decode — runs only after verbatim persist."""
        out: dict[str, object] = {
            "kind": kind.value,
            "native_id": native_id,
            "interpreted": True,
            "raw_payload": dict(raw_payload),
        }

        if market_price_wire is not None:
            if instrument is None:
                return _invalid(
                    "instrument",
                    "market-data price decode requires an Instrument",
                    given=repr(instrument),
                )
            price = decode_market_data_price(market_price_wire, instrument)
            if is_refusal(price):
                return price
            out["market_price"] = {
                "value": price.value.value,
                "scale": price.value.scale,
                "wire_scale": MARKET_DATA_WIRE_SCALE_EXPONENT,
            }

        vol_source = volume_wire if volume_wire is not None else depth_size_wire
        if vol_source is not None:
            qty = decode_volume(vol_source)
            if is_refusal(qty):
                return qty
            out["volume"] = {
                "value": qty.value.value,
                "scale": qty.value.scale,
                "unit": qty.value.unit,
                "wire_scale": VOLUME_WIRE_SCALE_EXPONENT,
            }

        if money_message is not None or money_units is not None:
            money = decode_money(money_message, money_units, money_currency, money_digits)
            if is_refusal(money):
                return money
            out["money"] = {
                "value": money.value.value,
                "scale": money.value.scale,
                "currency": money.value.currency,
            }

        if kind is WireKind.FILL:
            return self._interpret_fill(
                out=out,
                native_id=native_id,
                revision=revision,
                receive_wall=receive_wall,
                monotonic=monotonic,
                venue_instant=venue_instant,
                instrument=instrument,
                fill_price_wire=fill_price_wire,
                fill_price_is_execution_double=fill_price_is_execution_double,
                fill_digits=fill_digits,
                fill_rounding=fill_rounding,
                fill_volume_wire=fill_volume_wire,
            )

        if kind is WireKind.LIFECYCLE:
            return self._interpret_lifecycle(
                out=out,
                native_id=native_id,
                revision=revision,
                receive_wall=receive_wall,
                monotonic=monotonic,
                venue_instant=venue_instant,
                lifecycle_kind=lifecycle_kind,
            )

        # spots / trendbars-in-spots / depth — market-data only path
        return Ok(out)

    def _interpret_fill(
        self,
        *,
        out: dict[str, object],
        native_id: str,
        revision: object,
        receive_wall: Instant,
        monotonic: MonotonicReading,
        venue_instant: Instant | None,
        instrument: object,
        fill_price_wire: object,
        fill_price_is_execution_double: bool,
        fill_digits: object,
        fill_rounding: object,
        fill_volume_wire: object,
    ) -> Result[dict[str, object]]:
        if venue_instant is None:
            return _invalid(
                "venue_instant",
                "a fill requires a venue event time distinct from receive-wall provenance",
            )
        if instrument is None:
            return _invalid("instrument", "a fill price decode requires an Instrument")
        if fill_price_is_execution_double:
            if fill_rounding is None:
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "fill_rounding",
                        "reason": "a float crossing without a declared rounding rule "
                        "is refused at the venue money-path boundary",
                        "given": repr(fill_price_wire),
                    },
                )
            crossed = decode_execution_price(
                fill_price_wire, instrument, fill_digits, fill_rounding
            )
            if is_refusal(crossed):
                return crossed
            fill_price = crossed.value.price
            out["execution_price_raw_double"] = crossed.value.raw_double
            out["rounding"] = crossed.value.rounding.value
        else:
            if isinstance(fill_price_wire, float):
                return TypedRefusal(
                    category=RefusalCategory.INVALID_INPUT,
                    retryability=Retryability.NO,
                    context={
                        "field": "fill_price_wire",
                        "reason": "a float crossing without a declared rounding rule "
                        "is refused; set fill_price_is_execution_double with an "
                        "explicit RoundingMode",
                        "given": repr(fill_price_wire),
                    },
                )
            price = decode_market_data_price(fill_price_wire, instrument)
            if is_refusal(price):
                return price
            fill_price = price.value
        if fill_volume_wire is None:
            return _invalid("fill_volume_wire", "a fill requires an exact volume in cents")
        qty = decode_volume(fill_volume_wire)
        if is_refusal(qty):
            return qty
        identity = VenueNativeIdentity.try_create("ctrader", native_id, revision)
        if is_refusal(identity):
            return identity
        event = InboundVenueEvent.try_create(
            ObservationKind.FILL,
            identity.value,
            receive_wall,
            monotonic,
            self._session_epoch,
            out["raw_payload"],
            fill_price=fill_price,
            fill_quantity=qty.value,
            venue_instant=venue_instant,
            subject_native_id=native_id,
        )
        if is_refusal(event):
            return event
        if self._recorder is not None:
            recorded = self._recorder.record(
                event.value,
                registry_record={"kind": "fill", "native_id": native_id},
                boundary=TransactionBoundary.ORDERED_WITH_RECOVERY,
            )
            if is_refusal(recorded):
                return recorded
            out["multi_room_committed"] = recorded.value.committed
        out["observation_kind"] = ObservationKind.FILL.value
        out["fill_price"] = {"value": fill_price.value, "scale": fill_price.scale}
        out["fill_quantity"] = {
            "value": qty.value.value,
            "scale": qty.value.scale,
            "unit": qty.value.unit,
        }
        out["ct13_event_type"] = "fill"
        return Ok(out)

    def _interpret_lifecycle(
        self,
        *,
        out: dict[str, object],
        native_id: str,
        revision: object,
        receive_wall: Instant,
        monotonic: MonotonicReading,
        venue_instant: Instant | None,
        lifecycle_kind: object,
    ) -> Result[dict[str, object]]:
        obs = _coerce_obs(lifecycle_kind)
        if obs is None or obs not in _LIFECYCLE_OBS:
            return _invalid(
                "lifecycle_kind",
                "lifecycle frames require submission-acknowledgement | "
                "cancel-acknowledgement | expiry | close-by-venue",
                given=repr(lifecycle_kind),
                allowed=[m.value for m in _LIFECYCLE_OBS],
            )
        identity = VenueNativeIdentity.try_create("ctrader", native_id, revision)
        if is_refusal(identity):
            return identity
        event = InboundVenueEvent.try_create(
            obs,
            identity.value,
            receive_wall,
            monotonic,
            self._session_epoch,
            out["raw_payload"],
            venue_instant=venue_instant,
            subject_native_id=native_id,
        )
        if is_refusal(event):
            return event
        if self._recorder is not None:
            recorded = self._recorder.record(
                event.value,
                registry_record={"kind": "lifecycle", "native_id": native_id},
                boundary=TransactionBoundary.ORDERED_WITH_RECOVERY,
            )
            if is_refusal(recorded):
                return recorded
            out["multi_room_committed"] = recorded.value.committed
        out["observation_kind"] = obs.value
        out["ct13_event_type"] = "order"
        return Ok(out)


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _coerce_wire(value: object) -> WireKind | None:
    if isinstance(value, WireKind):
        return value
    if isinstance(value, str):
        try:
            return WireKind(value)
        except ValueError:
            return None
    return None


def _coerce_obs(value: object) -> ObservationKind | None:
    if isinstance(value, ObservationKind):
        return value
    if isinstance(value, str):
        try:
            return ObservationKind(value)
        except ValueError:
            return None
    return None
