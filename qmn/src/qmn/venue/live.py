"""Live cTrader :class:`~qmn.venue.port.VenueClientPort` (Story 24.3, Story 31.2, Story 31.4).

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

Production ``open_session`` drives the node's injected
:class:`~qmf.venue.connection.ConnectionManager` through ``connect_open_api``
on that same loop (Open API port 5035, injected proto tag, opaque
:class:`~qmf.core.SecretRef` only). The client never constructs a loop or a
second manager. Tagged smoke against ``demo.ctraderapi.com`` stays extra.

Story 31.3: :meth:`LiveCTraderClient.encode_command` translates a CT-19
``Command`` onto the qmf-venue ProtoOA encode symbols. This module does not
import generated proto modules or compile proto messages.

Story 31.4: :meth:`LiveCTraderClient.submit` hands a ready well-formed
``Command`` to that encode path. The Story 24.3 sensing-only refusal is gone
for every CT-19 kind the bound CT-18 declaration supports. Session closed or
capabilities unverified stay ``unavailable dependency`` — submit does not
encode or open a socket to skip readiness. An omitted kind is the remaining
single-kind unsupported-capability submit. Unprotected ``place_order`` is
refused before encode. No command is retried after wire handoff; UNKNOWN is a
state; timeout is not reject.
"""

from __future__ import annotations

import asyncio
import ssl
from collections.abc import Awaitable, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, cast

from qmf.core import (
    Account,
    Clock,
    Fingerprint,
    Instant,
    MonotonicReading,
    Ok,
    Quantity,
    RefusalCategory,
    Result,
    Retryability,
    SecretRef,
    SecretValue,
    TypedRefusal,
    VenueId,
    World,
    is_ok,
    is_refusal,
)
from qmf.venue.capabilities import ErrorMap, ErrorMapResolution
from qmf.venue.commands import (
    Command,
    CommandKind,
    CommandObservation,
    CompoundCommand,
    JournalEvent,
    SubmissionOutcome,
    SubmissionResult,
    UnknownTrigger,
)
from qmf.venue.connection import (
    CTRADER_OPEN_API_PORT,
    AccountBinding,
    ConnectionManager,
)
from qmf.venue.ctrader import (
    MARKET_DATA_WIRE_SCALE_EXPONENT,
    decode_execution_price,
    decode_market_data_price,
    decode_money,
    decode_timestamp,
)
from qmf.venue.encode import (
    EncodedCommand,
    encode_amend_protection,
    encode_cancel_order,
    encode_close_all,
    encode_close_position,
    encode_place_order,
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

from qmn.order.protection import require_venue_resident_protective_stop
from qmn.venue.conformance import (
    compound_command_acceptance_blocked,
    declared_command_kinds,
    omitted_command_kind_refusal,
    protective_stop_forms_from_verification,
    submit_not_ready_refusal,
)
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
    and sink set and push wire frames through :meth:`receive`. Production
    compositions inject the node's :class:`~qmf.venue.connection.ConnectionManager`,
    loop, Open API host, and proto tag so :meth:`open_session` can call
    ``connect_open_api``. Automatic command retry is impossible — there is no
    retry path.
    """

    _world: World
    _venue_id: VenueId
    _clock: Clock
    _error_map: ErrorMap
    _session_epoch: str
    _connection_manager: ConnectionManager | None = None
    _recorder: EventRecorder | None = None
    _intake: _LiveIntake | None = None
    _event_loop: asyncio.AbstractEventLoop | None = None
    _open_api_host: str | None = None
    _proto_tag: int | None = None
    _open_api_port: int = CTRADER_OPEN_API_PORT
    _ssl_context: ssl.SSLContext | None = None
    _server_hostname: str | None = None
    _credential_ref: SecretRef | None = None
    _account: Account | None = None
    _account_binding: AccountBinding | None = None
    _session_open: bool = False
    _opened_open_api: bool = False
    _capabilities_verified: bool = False
    _verification: VenueFactVerification | None = None
    _observations: list[dict[str, object]] = field(default_factory=list[dict[str, object]])
    _commands_retried: int = 0
    _compiled: object | None = None
    _ctid_trader_account_id: int | None = None
    _symbol_id: int | None = None
    _trade_side: str | None = None
    _volume: object | None = None
    _handed_off: dict[str, SubmissionResult] = field(default_factory=dict[str, SubmissionResult])

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
        event_loop: object = None,
        open_api_host: object = None,
        proto_tag: object = None,
        open_api_port: object = CTRADER_OPEN_API_PORT,
        ssl_context: object = None,
        server_hostname: object = None,
        credential_ref: object = None,
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
        loop = _coerce_event_loop(event_loop)
        if is_refusal(loop):
            return loop
        host = _coerce_optional_host(open_api_host)
        if is_refusal(host):
            return host
        tag = _coerce_optional_proto_tag(proto_tag)
        if is_refusal(tag):
            return tag
        port = _coerce_open_api_port(open_api_port)
        if is_refusal(port):
            return port
        tls = _coerce_optional_ssl_context(ssl_context)
        if is_refusal(tls):
            return tls
        hostname = _coerce_optional_host(server_hostname, field_name="server_hostname")
        if is_refusal(hostname):
            return hostname
        cred = _coerce_optional_credential_ref(credential_ref)
        if is_refusal(cred):
            return cred
        production_host = host.value
        if production_host is not None:
            if cm is None:
                return _invalid(
                    "connection_manager",
                    "production Open API connect uses the node's injected "
                    "ConnectionManager; LiveCTraderClient never constructs one",
                )
            if loop.value is None:
                return _invalid(
                    "event_loop",
                    "production Open API connect requires the node's injected "
                    "asyncio loop; LiveCTraderClient never creates one",
                )
            if tag.value is None:
                return _invalid(
                    "proto_tag",
                    "the Spotware proto release tag is a positive integer injected "
                    "from registry:venue_protocol_artifact",
                    given=repr(proto_tag),
                )
        if cred.value is not None and cm is None:
            return _invalid(
                "connection_manager",
                "credential session open uses the node's injected ConnectionManager; "
                "LiveCTraderClient never constructs one",
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
                _event_loop=loop.value,
                _open_api_host=production_host,
                _proto_tag=tag.value,
                _open_api_port=port.value,
                _ssl_context=tls.value,
                _server_hostname=hostname.value,
                _credential_ref=cred.value,
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
        secret = self._open_secret_session(account)
        if is_refusal(secret):
            return secret
        if self._open_api_host is not None:
            connected = self._connect_open_api()
            if is_refusal(connected):
                self._rollback_secret_session()
                return connected
        self._account = account
        self._session_open = True
        return Ok(True)

    def close_session(self) -> Result[bool]:
        if self._opened_open_api:
            cm = self._connection_manager
            if cm is not None and cm.transport_open:
                closed = self._drive_on_node_loop(cm.close_transport())
                if is_refusal(closed):
                    return closed
            self._opened_open_api = False
        rolled = self._rollback_secret_session()
        if is_refusal(rolled):
            return rolled
        self._session_open = False
        self._account = None
        self._capabilities_verified = False
        self._handed_off.clear()
        return Ok(True)

    def _open_secret_session(self, account: Account) -> Result[bool]:
        """Hold the credential by opaque reference in the injected manager (CT-21)."""
        if self._credential_ref is None:
            return Ok(True)
        cm = self._connection_manager
        if cm is None:
            return _invalid(
                "connection_manager",
                "credential session open uses the node's injected ConnectionManager; "
                "LiveCTraderClient never constructs one",
            )
        binding = AccountBinding.try_create(
            self._venue_id, account, self._world, self._credential_ref
        )
        if is_refusal(binding):
            return binding
        opened = cm.open_session(binding.value)
        if is_refusal(opened):
            return opened
        self._account_binding = binding.value
        return Ok(True)

    def _rollback_secret_session(self) -> Result[bool]:
        cm = self._connection_manager
        binding = self._account_binding
        self._account_binding = None
        if cm is None or binding is None:
            return Ok(True)
        if not cm.holds_secret(binding.secret_ref):
            return Ok(True)
        closed = cm.close_session(binding.secret_ref)
        if is_refusal(closed):
            return closed
        return Ok(True)

    def _connect_open_api(self) -> Result[bool]:
        """Production caller of :meth:`ConnectionManager.connect_open_api` (DEC-0265)."""
        cm = self._connection_manager
        host = self._open_api_host
        tag = self._proto_tag
        if cm is None:
            return _invalid(
                "connection_manager",
                "production Open API connect uses the node's injected "
                "ConnectionManager; LiveCTraderClient never constructs one",
            )
        if host is None:
            return _invalid(
                "open_api_host",
                "Open API host is a non-blank deployment host reference",
            )
        if tag is None:
            return _invalid(
                "proto_tag",
                "the Spotware proto release tag is a positive integer injected from "
                "registry:venue_protocol_artifact",
            )
        connected = self._drive_on_node_loop(
            cm.connect_open_api(
                host,
                proto_tag=tag,
                port=self._open_api_port,
                ssl_context=self._ssl_context,
                server_hostname=self._server_hostname,
            )
        )
        if is_refusal(connected):
            return connected
        self._opened_open_api = True
        return connected

    def _drive_on_node_loop(self, awaitable: object) -> Result[bool]:
        """Run one ConnectionManager coroutine on the injected loop.

        The venue edge may drive the node's single loop; it never creates a
        second loop (DEC-0243).
        """
        loop = self._event_loop
        if loop is None:
            _close_awaitable(awaitable)
            return _loop_required()
        if loop.is_running():
            _close_awaitable(awaitable)
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "event_loop",
                    "reason": "open_session drives connect_open_api on the node's "
                    "injected loop; a second loop is refused",
                },
            )
        return loop.run_until_complete(cast("Awaitable[Result[bool]]", awaitable))

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

    def bind_encode_context(
        self,
        *,
        compiled: object,
        ctid_trader_account_id: object,
        symbol_id: object = None,
        trade_side: object = None,
        volume: object = None,
    ) -> Result[bool]:
        """Inject Story 31.3 encode inputs. This client never compiles proto."""
        if compiled is None:
            return _invalid(
                "compiled",
                "encode consumes an in-house CompiledProto; LiveCTraderClient never compiles proto",
            )
        if isinstance(ctid_trader_account_id, bool) or not isinstance(ctid_trader_account_id, int):
            return _invalid(
                "ctid_trader_account_id",
                "a venue-native identifier is a non-negative exact integer",
                given=repr(ctid_trader_account_id),
            )
        if ctid_trader_account_id < 1:
            return _invalid(
                "ctid_trader_account_id",
                "a venue-native identifier is a non-negative exact integer",
                given=repr(ctid_trader_account_id),
            )
        resolved_symbol: int | None
        if symbol_id is None:
            resolved_symbol = None
        elif isinstance(symbol_id, bool) or not isinstance(symbol_id, int) or symbol_id < 1:
            return _invalid(
                "symbol_id",
                "a venue-native identifier is a non-negative exact integer",
                given=repr(symbol_id),
            )
        else:
            resolved_symbol = symbol_id
        resolved_side: str | None
        if trade_side is None:
            resolved_side = None
        elif not isinstance(trade_side, str) or trade_side.strip().lower() not in {
            "buy",
            "sell",
        }:
            return _invalid(
                "trade_side",
                "place_order encodes ProtoOA tradeSide buy | sell",
                given=repr(trade_side),
            )
        else:
            resolved_side = trade_side.strip().lower()
        if volume is not None and not isinstance(volume, Quantity):
            return _invalid(
                "volume",
                "close volume is an exact qmf-core Quantity; a binary float is refused",
                given=repr(volume),
            )
        self._compiled = compiled
        self._ctid_trader_account_id = ctid_trader_account_id
        self._symbol_id = resolved_symbol
        self._trade_side = resolved_side
        self._volume = volume
        return Ok(True)

    def encode_command(
        self,
        command: object,
        *,
        compiled: object,
        declaration: object,
        ctid_trader_account_id: object,
        symbol_id: object = None,
        trade_side: object = None,
        volume: object = None,
        client_msg_id: object = None,
    ) -> Result[EncodedCommand]:
        """Translate a CT-19 ``Command`` onto qmf-venue ProtoOA encode symbols.

        Does not compile proto or import generated modules. A
        :class:`~qmf.venue.commands.CompoundCommand` keeps the FTR-02
        unsupported-capability block (GAP-0059).
        """
        if isinstance(command, CompoundCommand):
            return compound_command_acceptance_blocked()
        if not isinstance(command, Command):
            return _invalid(
                "command",
                "encode requires a CT-19 Command",
                given=type(command).__name__,
            )
        if command.kind is CommandKind.PLACE_ORDER:
            return encode_place_order(
                command,
                compiled=compiled,
                declaration=declaration,
                ctid_trader_account_id=ctid_trader_account_id,
                symbol_id=symbol_id,
                trade_side=trade_side,
                client_msg_id=client_msg_id,
            )
        if command.kind is CommandKind.CANCEL_ORDER:
            return encode_cancel_order(
                command,
                compiled=compiled,
                declaration=declaration,
                ctid_trader_account_id=ctid_trader_account_id,
                client_msg_id=client_msg_id,
            )
        if command.kind is CommandKind.CLOSE_POSITION:
            return encode_close_position(
                command,
                compiled=compiled,
                declaration=declaration,
                ctid_trader_account_id=ctid_trader_account_id,
                volume=volume,
                client_msg_id=client_msg_id,
            )
        if command.kind is CommandKind.CLOSE_ALL:
            return encode_close_all(
                command,
                compiled=compiled,
                declaration=declaration,
                ctid_trader_account_id=ctid_trader_account_id,
                symbol_id=symbol_id,
                client_msg_id=client_msg_id,
            )
        return encode_amend_protection(
            command,
            compiled=compiled,
            declaration=declaration,
            ctid_trader_account_id=ctid_trader_account_id,
            client_msg_id=client_msg_id,
        )

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
            return submit_not_ready_refusal()
        verification = self._verification
        if verification is None:
            return submit_not_ready_refusal()
        stop = require_venue_resident_protective_stop(
            command,
            forms_per_order_type=protective_stop_forms_from_verification(verification),
        )
        if is_refusal(stop):
            return stop
        declared = declared_command_kinds(verification.declaration)
        if is_refusal(declared):
            return declared
        if command.kind.value not in declared.value:
            return omitted_command_kind_refusal(command.kind, declared.value)
        fp = command.fingerprint()
        if is_refusal(fp):
            return fp
        prior = self._handed_off.get(fp.value.value)
        if prior is not None:
            return Ok(prior)
        wall = self._clock.wall_now()
        if is_refusal(wall):
            return wall
        encoded = self.encode_command(
            command,
            compiled=self._compiled,
            declaration=verification.declaration,
            ctid_trader_account_id=self._ctid_trader_account_id,
            symbol_id=self._symbol_id,
            trade_side=self._trade_side,
            volume=self._volume,
        )
        if is_refusal(encoded):
            return encoded
        trigger = self._send_encoded_once(encoded.value)
        result = _unknown_after_encode(command, fp.value, wall.value, trigger=trigger)
        self._observations.append(
            {
                "kind": "encode-handoff",
                "command_kind": command.kind.value,
                "payload_type": encoded.value.payload_type,
                "client_msg_id": encoded.value.client_msg_id,
                "auto_retry": False,
                "encoded": True,
                "socket_opened": self._opened_open_api,
                "outcome": result.outcome.value,
                "unknown_trigger": None if trigger is None else trigger.value,
            }
        )
        self._handed_off[fp.value.value] = result
        return Ok(result)

    def _send_encoded_once(self, encoded: EncodedCommand) -> UnknownTrigger | None:
        """Transmit at most once on an already-open socket. Never opens one."""
        cm = self._connection_manager
        if cm is None or not self._opened_open_api or not cm.transport_open:
            return None
        sent = self._drive_on_node_loop(cm.send_framed(encoded.envelope))
        if is_ok(sent):
            return None
        reason = str(sent.context.get("trigger", ""))
        if reason == UnknownTrigger.DISCONNECT.value:
            return UnknownTrigger.DISCONNECT
        if reason == UnknownTrigger.TIMEOUT.value:
            return UnknownTrigger.TIMEOUT
        return UnknownTrigger.TRANSPORT_ERROR

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


def _unknown_after_encode(
    command: Command,
    fp: Fingerprint,
    receive_instant: Instant,
    *,
    trigger: UnknownTrigger | None,
) -> SubmissionResult:
    """UNKNOWN is a state after encode-handoff; timeout is never a reject."""
    observation = CommandObservation(
        command_fp1=fp,
        kind=command.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        receive_instant=receive_instant,
        unknown_trigger=trigger,
        detail=(
            "encode-handoff completed; UNKNOWN is a state; timeout is not reject; "
            "no command is retried after handoff"
        ),
    )
    return SubmissionResult(
        command_fp1=fp,
        kind=command.kind,
        outcome=SubmissionOutcome.UNKNOWN,
        observation=observation,
        journal_event=JournalEvent.for_outcome(fp, command.kind, SubmissionOutcome.UNKNOWN),
    )


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _loop_required() -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.AFTER_CONDITION,
        context={
            "field": "event_loop",
            "reason": "connect_open_api requires the node's injected asyncio loop; "
            "LiveCTraderClient never creates one",
        },
        after_condition_descriptor="run on the node's injected asyncio loop",
    )


def _close_awaitable(awaitable: object) -> None:
    closer = getattr(awaitable, "close", None)
    if callable(closer):
        closer()


def _coerce_event_loop(value: object) -> Result[asyncio.AbstractEventLoop | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, asyncio.AbstractEventLoop):
        return Ok(value)
    return _invalid(
        "event_loop",
        "production Open API connect requires the node's injected asyncio loop; "
        "LiveCTraderClient never creates one",
        given=type(value).__name__,
    )


def _coerce_optional_host(
    value: object, *, field_name: str = "open_api_host"
) -> Result[str | None]:
    if value is None:
        return Ok(None)
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            field_name,
            "Open API host is a non-blank deployment host reference",
            given=repr(value),
        )
    return Ok(value)


def _coerce_optional_proto_tag(value: object) -> Result[int | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return _invalid(
            "proto_tag",
            "the Spotware proto release tag is a positive integer injected from "
            "registry:venue_protocol_artifact",
            given=repr(value),
        )
    return Ok(value)


def _coerce_open_api_port(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 65535:
        return _invalid(
            "open_api_port",
            "Open API port is a TCP port in 1..65535",
            given=repr(value),
        )
    return Ok(value)


def _coerce_optional_ssl_context(value: object) -> Result[ssl.SSLContext | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, ssl.SSLContext):
        return Ok(value)
    return _invalid(
        "ssl_context",
        "when supplied, ssl_context must be an ssl.SSLContext",
        given=type(value).__name__,
    )


def _coerce_optional_credential_ref(value: object) -> Result[SecretRef | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, SecretValue):
        return _invalid(
            "credential_ref",
            "the live client passes an opaque SecretRef; ConnectionManager is the "
            "sole in-memory value holder",
            given=type(value).__name__,
        )
    if not isinstance(value, SecretRef):
        return _invalid(
            "credential_ref",
            "the live client passes an opaque SecretRef; ConnectionManager is the "
            "sole in-memory value holder",
            given=type(value).__name__,
        )
    return Ok(value)


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
