"""Roster-driven multi-account / multi-broker runtime keys (Story 25.19 / TN-22).

Composition/config surface only: every runtime object is keyed by the ratified
tuples — never a singleton venue or account (DEC-0207). Adding a broker is a
roster row plus ``VenueClientPort`` selection by ``(world, VenueId)`` and a
safe-point restart; core node logic does not change. Sensing-only entries are
a legal compiled state (no Book, BMS, or command sequencer). Netting
attribution declarations are proved jointly exhaustive and disjoint at compose.
Protective pacing reserve is planned per connection so entry work cannot
consume it; one stream's UNKNOWN never freezes another.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Account,
    AccountRole,
    Fingerprint,
    Ok,
    Result,
    VenueId,
    World,
    is_refusal,
)
from qmf.core.fingerprint import fingerprint

from qmn.config._refuse import clean_token, invalid, policy, unsupported
from qmn.venue import VenueClientSelection, select_venue_client, venue_command_stream

__all__ = [
    "ADDING_BROKER_REQUIRES_CORE_CODE_CHANGE",
    "HAS_DEFAULT_VENUE_ACCOUNT_SINGLETON",
    "ROSTER_SURFACE",
    "STATE_CARRY_COUNTERS",
    "AccountBindingDecl",
    "BindingRuntimeKey",
    "BookBindingDecl",
    "CommandStreamPlan",
    "CommandStreamRuntimeKey",
    "ConnectionRuntimeKey",
    "PacerBucketPlan",
    "PositionModelDecl",
    "RosterRuntimeComposition",
    "SensingOnlyDecl",
    "SensingOnlyPlan",
    "StateCarryChoice",
    "ThrottleScope",
    "compose_roster_runtime",
    "streams_independent",
    "writer_streams_from_composition",
]

ROSTER_SURFACE: Final[str] = "qmn.config.roster"
# Extensibility law: a second broker is another VenueId row + port selection.
ADDING_BROKER_REQUIRES_CORE_CODE_CHANGE: Final[bool] = False
# Compose never invents a default venue/account (TN-22).
HAS_DEFAULT_VENUE_ACCOUNT_SINGLETON: Final[bool] = False

STATE_CARRY_COUNTERS: Final[tuple[str, ...]] = (
    "ledger",
    "cycle",
    "budget",
    "bench_counter",
    "exposure",
)

_ENVIRONMENTS: Final[frozenset[str]] = frozenset({"demo", "live"})
_THROTTLE_SCOPES: Final[frozenset[str]] = frozenset({"connection", "account", "binding"})


class ThrottleScope(StrEnum):
    """CT-18 ``throttle_scope`` — pacer bucket ownership (DEC-0207)."""

    CONNECTION = "connection"
    ACCOUNT = "account"
    BINDING = "binding"


class PositionModelDecl(StrEnum):
    """Measured CT-18 position model declared on the roster row for compose."""

    NETTING = "netting"
    HEDGING = "hedging"


class StateCarryChoice(StrEnum):
    """Per-counter carry | reset on every minted binding (DEC-0207/DEC-0210)."""

    CARRY = "carry"
    RESET = "reset"


@dataclass(frozen=True, slots=True)
class BookBindingDecl:
    """One Book binding eligibility row on an account binding (roster only)."""

    binding_id: str
    book_definition_fp1: str
    instruments: frozenset[str]
    attribution_instruments: frozenset[str] | None = None
    shared_flatten_signature: str | None = None

    def identity(self) -> dict[str, object]:
        body: dict[str, object] = {
            "binding_id": self.binding_id,
            "book_definition_fp1": self.book_definition_fp1,
            "instruments": sorted(self.instruments),
        }
        if self.attribution_instruments is not None:
            body["attribution_instruments"] = sorted(self.attribution_instruments)
        if self.shared_flatten_signature is not None:
            body["shared_flatten_signature"] = self.shared_flatten_signature
        return body


@dataclass(frozen=True, slots=True)
class AccountBindingDecl:
    """Operable roster row: ``(VenueId, AccountId, role, world)`` + Book/BMS."""

    venue_id: str
    account_id: str
    role: AccountRole
    world: World
    environment: str
    credential_reference: str
    credential_sharing: str
    bms_definition_fp1: str
    bms_instance_id: str
    book_bindings: tuple[BookBindingDecl, ...]
    state_carry: Mapping[str, StateCarryChoice]
    throttle_scope: ThrottleScope
    position_model: PositionModelDecl
    opaque_metric_id: str
    carries_ledger_signature: str | None = None

    def identity(self) -> dict[str, object]:
        body: dict[str, object] = {
            "kind": "account_binding",
            "venue_id": self.venue_id,
            "account_id": self.account_id,
            "role": self.role.value,
            "world": self.world.value,
            "environment": self.environment,
            "credential_reference": self.credential_reference,
            "credential_sharing": self.credential_sharing,
            "bms_definition_fp1": self.bms_definition_fp1,
            "bms_instance_id": self.bms_instance_id,
            "book_bindings": [b.identity() for b in self.book_bindings],
            "state_carry": {k: v.value for k, v in sorted(self.state_carry.items())},
            "throttle_scope": self.throttle_scope.value,
            "position_model": self.position_model.value,
            "opaque_metric_id": self.opaque_metric_id,
        }
        if self.carries_ledger_signature is not None:
            body["carries_ledger_signature"] = self.carries_ledger_signature
        return body


@dataclass(frozen=True, slots=True)
class SensingOnlyDecl:
    """Sensing-only roster row: connection opens; no Book/BMS/sequencer."""

    venue_id: str
    environment: str
    account_id: str
    credential_reference: str
    opaque_metric_id: str
    world: World = World.LIVE

    def identity(self) -> dict[str, object]:
        return {
            "kind": "sensing_only",
            "venue_id": self.venue_id,
            "environment": self.environment,
            "account_id": self.account_id,
            "credential_reference": self.credential_reference,
            "opaque_metric_id": self.opaque_metric_id,
            "world": self.world.value,
        }


@dataclass(frozen=True, slots=True)
class ConnectionRuntimeKey:
    """Connection key ``(venue, environment)`` — one per pair the roster names."""

    venue_id: str
    environment: str

    @property
    def token(self) -> str:
        return f"{self.venue_id}:{self.environment}"


@dataclass(frozen=True, slots=True)
class CommandStreamRuntimeKey:
    """Command-stream key ``(VenueId, account)`` — never a singleton."""

    venue_id: str
    account_id: str

    @property
    def token(self) -> str:
        # Match qmf-venue's ``venue_command_stream`` join (``::``).
        return f"{self.venue_id}::{self.account_id}"


@dataclass(frozen=True, slots=True)
class BindingRuntimeKey:
    """AD-29 binding tuple ``(Book, BMS, VenueId, AccountId, world)``."""

    book_instance_id: str
    bms_instance_id: str
    venue_id: str
    account_id: str
    world: World

    @property
    def token(self) -> str:
        return (
            f"{self.book_instance_id}|{self.bms_instance_id}|"
            f"{self.venue_id}:{self.account_id}|{self.world.value}"
        )


@dataclass(frozen=True, slots=True)
class PacerBucketPlan:
    """Connection-owned pacer with isolated protective reserve (TN-22).

    The command stream admits through this bucket and never holds one of its own.
    ``protective_reserve_capacity`` is unavailable to entry work.
    """

    connection: ConnectionRuntimeKey
    throttle_scope: ThrottleScope
    protective_reserve_capacity: int
    owned_by_connection: bool = True
    entry_may_consume_reserve: bool = False


@dataclass(frozen=True, slots=True)
class CommandStreamPlan:
    """One operable command stream composed from an account binding."""

    stream: CommandStreamRuntimeKey
    connection: ConnectionRuntimeKey
    writer_role: str
    writer_stream: str
    risk_writer_stream: str
    adapter_writer_stream: str
    bindings: tuple[BindingRuntimeKey, ...]
    port_selection: VenueClientSelection
    pacer: PacerBucketPlan
    opens_sequencer: bool = True
    has_unknown_block: bool = True
    carries_pacer_bucket: bool = False


@dataclass(frozen=True, slots=True)
class SensingOnlyPlan:
    """Compiled sensing-only state — legal, not an incomplete binding."""

    connection: ConnectionRuntimeKey
    venue_id: str
    account_id: str
    credential_reference: str
    port_selection: VenueClientSelection
    opaque_metric_id: str
    may_record_observations: bool = True
    may_serve_observations: bool = True
    opens_sequencer: bool = False
    has_book_binding: bool = False
    has_bms_instance: bool = False
    has_command_stream: bool = False
    resolves_execution_target: bool = False
    admits_promotion: bool = False
    admits_live_intent: bool = False


@dataclass(frozen=True, slots=True)
class RosterRuntimeComposition:
    """Sealed roster-derived runtime keys for one compose epoch (TN-22)."""

    account_bindings: tuple[AccountBindingDecl, ...]
    sensing_only: tuple[SensingOnlyDecl, ...]
    connections: tuple[ConnectionRuntimeKey, ...]
    command_streams: tuple[CommandStreamPlan, ...]
    sensing_plans: tuple[SensingOnlyPlan, ...]
    binding_keys: tuple[BindingRuntimeKey, ...]
    pacer_buckets: tuple[PacerBucketPlan, ...]
    port_selections: tuple[VenueClientSelection, ...]
    composition_fp: Fingerprint
    sealed: bool = True

    def identity(self) -> dict[str, object]:
        return {
            "class": "roster-runtime-composition",
            "surface": ROSTER_SURFACE,
            "has_default_venue_account_singleton": HAS_DEFAULT_VENUE_ACCOUNT_SINGLETON,
            "adding_broker_requires_core_code_change": (ADDING_BROKER_REQUIRES_CORE_CODE_CHANGE),
            "account_bindings": [b.identity() for b in self.account_bindings],
            "sensing_only": [s.identity() for s in self.sensing_only],
            "connections": [c.token for c in self.connections],
            "command_streams": [p.stream.token for p in self.command_streams],
            "binding_keys": [k.token for k in self.binding_keys],
            "pacer_buckets": [
                {
                    "connection": p.connection.token,
                    "throttle_scope": p.throttle_scope.value,
                    "protective_reserve_capacity": p.protective_reserve_capacity,
                    "entry_may_consume_reserve": p.entry_may_consume_reserve,
                }
                for p in self.pacer_buckets
            ],
            "port_selections": [
                {
                    "world": s.world.value,
                    "venue_id": s.venue_id.value,
                    "kind": s.kind.value,
                }
                for s in self.port_selections
            ],
            "sensing_plans": [
                {
                    "connection": p.connection.token,
                    "opens_sequencer": p.opens_sequencer,
                    "has_book_binding": p.has_book_binding,
                    "has_command_stream": p.has_command_stream,
                }
                for p in self.sensing_plans
            ],
        }


def compose_roster_runtime(
    *,
    account_bindings: object = (),
    sensing_only: object = (),
    protective_reserve_capacity: object,
) -> Result[RosterRuntimeComposition]:
    """Compose sealed multi-account/multi-broker runtime keys from the roster.

    Refuses a default venue/account singleton, incomplete sensing-only rows that
    smuggle Book/BMS/sequencer authority, missing or overlapping netting
    attribution, and blank protective reserve. Success seals WriterId stream
    names and connection pacer plans before use.
    """
    if HAS_DEFAULT_VENUE_ACCOUNT_SINGLETON:  # pragma: no cover - pinned False
        return policy(
            "roster",
            "default venue/account singleton is refused; every key comes from the roster",
        )

    reserve = _as_non_negative_int(protective_reserve_capacity, "protective_reserve_capacity")
    if is_refusal(reserve):
        return reserve

    bindings_raw = _as_sequence(account_bindings, "account_bindings")
    if is_refusal(bindings_raw):
        return bindings_raw
    sensing_raw = _as_sequence(sensing_only, "sensing_only")
    if is_refusal(sensing_raw):
        return sensing_raw

    if not bindings_raw.value and not sensing_raw.value:
        return invalid(
            "roster",
            "roster must declare at least one account binding or sensing-only entry",
        )

    parsed_bindings: list[AccountBindingDecl] = []
    for index, raw in enumerate(bindings_raw.value):
        parsed = _parse_account_binding(raw, index=index)
        if is_refusal(parsed):
            return parsed
        parsed_bindings.append(parsed.value)

    parsed_sensing: list[SensingOnlyDecl] = []
    for index, raw in enumerate(sensing_raw.value):
        parsed = _parse_sensing_only(raw, index=index)
        if is_refusal(parsed):
            return parsed
        parsed_sensing.append(parsed.value)

    # Duplicate operable (venue, account) rows refuse — one command stream each.
    seen_streams: set[str] = set()
    for binding in parsed_bindings:
        key = f"{binding.venue_id}::{binding.account_id}"
        if key in seen_streams:
            return invalid(
                "account_bindings",
                "duplicate (VenueId, account) account binding refused",
                stream=key,
            )
        seen_streams.add(key)

    # Sensing-only may name the same account as a future live binding, but must
    # not collide with an operable command stream already composed this epoch.
    for sensing in parsed_sensing:
        key = f"{sensing.venue_id}::{sensing.account_id}"
        if key in seen_streams:
            return policy(
                "sensing_only",
                "sensing-only entry collides with an operable command stream; "
                "sensing-only is a legal compiled state without a sequencer, not "
                "a second stream on the same (VenueId, account)",
                stream=key,
            )

    netting = _prove_netting_attribution(parsed_bindings)
    if is_refusal(netting):
        return netting

    connections: dict[str, ConnectionRuntimeKey] = {}
    pacers: dict[str, PacerBucketPlan] = {}
    streams: list[CommandStreamPlan] = []
    binding_keys: list[BindingRuntimeKey] = []
    port_selections: dict[str, VenueClientSelection] = {}
    sensing_plans: list[SensingOnlyPlan] = []

    for binding in parsed_bindings:
        venue = VenueId.try_create(binding.venue_id)
        if is_refusal(venue):
            return venue
        account = Account.try_create(binding.account_id, venue.value, binding.role)
        if is_refusal(account):
            return account

        conn = ConnectionRuntimeKey(venue_id=binding.venue_id, environment=binding.environment)
        connections[conn.token] = conn
        if conn.token not in pacers:
            pacers[conn.token] = PacerBucketPlan(
                connection=conn,
                throttle_scope=binding.throttle_scope,
                protective_reserve_capacity=reserve.value,
            )
        elif pacers[conn.token].throttle_scope is not binding.throttle_scope:
            return invalid(
                "throttle_scope",
                "all bindings on one (venue, environment) connection must declare "
                "the same CT-18 throttle_scope",
                connection=conn.token,
            )

        selection = select_venue_client(binding.world, venue.value)
        if is_refusal(selection):
            return selection
        port_key = f"{selection.value.world.value}|{selection.value.venue_id.value}"
        port_selections[port_key] = selection.value

        stream_key = CommandStreamRuntimeKey(
            venue_id=binding.venue_id, account_id=binding.account_id
        )
        canonical = venue_command_stream(venue.value, account.value)
        if canonical != stream_key.token:
            return policy(
                "command_stream",
                "composed stream token must match venue_command_stream",
                composed=stream_key.token,
                canonical=canonical,
            )

        binding_tuple: list[BindingRuntimeKey] = []
        for book in binding.book_bindings:
            key = BindingRuntimeKey(
                book_instance_id=book.binding_id,
                bms_instance_id=binding.bms_instance_id,
                venue_id=binding.venue_id,
                account_id=binding.account_id,
                world=binding.world,
            )
            binding_tuple.append(key)
            binding_keys.append(key)

        streams.append(
            CommandStreamPlan(
                stream=stream_key,
                connection=conn,
                writer_role="command",
                writer_stream=stream_key.token,
                risk_writer_stream=f"risk:{stream_key.token}",
                adapter_writer_stream=f"adapter:{stream_key.token}",
                bindings=tuple(binding_tuple),
                port_selection=selection.value,
                pacer=pacers[conn.token],
            )
        )

    for sensing in parsed_sensing:
        venue = VenueId.try_create(sensing.venue_id)
        if is_refusal(venue):
            return venue
        conn = ConnectionRuntimeKey(venue_id=sensing.venue_id, environment=sensing.environment)
        connections[conn.token] = conn
        selection = select_venue_client(sensing.world, venue.value)
        if is_refusal(selection):
            return selection
        port_key = f"{selection.value.world.value}|{selection.value.venue_id.value}"
        port_selections[port_key] = selection.value
        sensing_plans.append(
            SensingOnlyPlan(
                connection=conn,
                venue_id=sensing.venue_id,
                account_id=sensing.account_id,
                credential_reference=sensing.credential_reference,
                port_selection=selection.value,
                opaque_metric_id=sensing.opaque_metric_id,
            )
        )

    provisional = RosterRuntimeComposition(
        account_bindings=tuple(parsed_bindings),
        sensing_only=tuple(parsed_sensing),
        connections=tuple(sorted(connections.values(), key=lambda c: c.token)),
        command_streams=tuple(streams),
        sensing_plans=tuple(sensing_plans),
        binding_keys=tuple(binding_keys),
        pacer_buckets=tuple(sorted(pacers.values(), key=lambda p: p.connection.token)),
        port_selections=tuple(
            sorted(
                port_selections.values(),
                key=lambda s: (s.world.value, s.venue_id.value),
            )
        ),
        composition_fp=Fingerprint(value="fp1:sha256:" + ("0" * 64)),
        sealed=True,
    )
    fp = fingerprint(provisional.identity())
    if is_refusal(fp):
        return fp
    return Ok(
        RosterRuntimeComposition(
            account_bindings=provisional.account_bindings,
            sensing_only=provisional.sensing_only,
            connections=provisional.connections,
            command_streams=provisional.command_streams,
            sensing_plans=provisional.sensing_plans,
            binding_keys=provisional.binding_keys,
            pacer_buckets=provisional.pacer_buckets,
            port_selections=provisional.port_selections,
            composition_fp=fp.value,
            sealed=True,
        )
    )


def writer_streams_from_composition(
    composition: object,
) -> Result[tuple[tuple[str, str], ...]]:
    """Derive Compose ``(role, stream)`` WriterId pairs from a sealed roster.

    Sensing-only entries mint no command-stream WriterId. Operable streams mint
    command, adapter, and risk writers — sealed before use at the boot ceremony.
    """
    if not isinstance(composition, RosterRuntimeComposition):
        return invalid(
            "composition",
            "writer streams derive from a sealed RosterRuntimeComposition",
            given=type(composition).__name__,
        )
    if not composition.sealed:
        return policy(
            "composition",
            "WriterIds are allocated only from a sealed roster composition",
        )
    pairs: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for plan in composition.command_streams:
        for role, stream in (
            (plan.writer_role, plan.writer_stream),
            ("adapter", plan.adapter_writer_stream),
            ("risk", plan.risk_writer_stream),
        ):
            key = (role, stream)
            if key in seen:
                return policy(
                    "writer_streams",
                    "composed WriterId (role, stream) pairs must be pairwise distinct",
                    colliding=list(key),
                )
            seen.add(key)
            pairs.append(key)
    return Ok(tuple(pairs))


def streams_independent(left: object, right: object) -> Result[bool]:
    """True when two command-stream keys are distinct (UNKNOWN does not cross)."""
    left_key = _as_stream_key(left, "left")
    if is_refusal(left_key):
        return left_key
    right_key = _as_stream_key(right, "right")
    if is_refusal(right_key):
        return right_key
    return Ok(left_key.value.token != right_key.value.token)


# --- parsers / proofs --------------------------------------------------------


def _parse_account_binding(raw: object, *, index: int) -> Result[AccountBindingDecl]:
    if not isinstance(raw, AccountBindingDecl):
        if not isinstance(raw, Mapping):
            return invalid(
                "account_bindings",
                "each account binding is an AccountBindingDecl or mapping",
                index=index,
                given=type(raw).__name__,
            )
        body = cast("Mapping[str, object]", raw)
        venue_id = clean_token(body.get("venue_id"))
        account_id = clean_token(body.get("account_id"))
        role = _coerce_role(body.get("role"))
        world = _coerce_world(body.get("world"))
        environment = clean_token(body.get("environment"))
        credential_reference = clean_token(body.get("credential_reference"))
        credential_sharing = clean_token(body.get("credential_sharing"))
        bms_fp = clean_token(body.get("bms_definition_fp1"))
        bms_instance = clean_token(body.get("bms_instance_id"))
        opaque = clean_token(body.get("opaque_metric_id"))
        throttle = _coerce_throttle(body.get("throttle_scope"))
        position = _coerce_position_model(body.get("position_model"))
        if (
            venue_id is None
            or account_id is None
            or role is None
            or world is None
            or environment is None
            or credential_reference is None
            or credential_sharing is None
            or bms_fp is None
            or bms_instance is None
            or opaque is None
            or throttle is None
            or position is None
        ):
            return invalid(
                "account_bindings",
                "account binding requires venue_id, account_id, role, world, "
                "environment, credential_reference, credential_sharing, "
                "bms_definition_fp1, bms_instance_id, opaque_metric_id, "
                "throttle_scope, and position_model",
                index=index,
            )
        if environment not in _ENVIRONMENTS:
            return invalid(
                "environment",
                "roster environment is demo | live",
                index=index,
                given=environment,
            )
        books_raw = body.get("book_bindings")
        books = _parse_book_bindings(books_raw, index=index)
        if is_refusal(books):
            return books
        carry = _parse_state_carry(body.get("state_carry"), index=index)
        if is_refusal(carry):
            return carry
        carries_sig = body.get("carries_ledger_signature")
        sig_token: str | None
        if carries_sig is None:
            sig_token = None
        else:
            sig_token = clean_token(carries_sig)
            if sig_token is None:
                return invalid(
                    "carries_ledger_signature",
                    "carries-ledger signature is a non-blank token when supplied",
                    index=index,
                )
        if any(v is StateCarryChoice.CARRY for v in carry.value.values()) and (sig_token is None):
            return invalid(
                "carries_ledger_signature",
                "state_carry carry requires a human-signed carries-ledger signature",
                index=index,
            )
        raw = AccountBindingDecl(
            venue_id=venue_id,
            account_id=account_id,
            role=role,
            world=world,
            environment=environment,
            credential_reference=credential_reference,
            credential_sharing=credential_sharing,
            bms_definition_fp1=bms_fp,
            bms_instance_id=bms_instance,
            book_bindings=books.value,
            state_carry=carry.value,
            throttle_scope=throttle,
            position_model=position,
            opaque_metric_id=opaque,
            carries_ledger_signature=sig_token,
        )

    binding = raw
    if binding.environment not in _ENVIRONMENTS:
        return invalid(
            "environment",
            "roster environment is demo | live",
            index=index,
            given=binding.environment,
        )
    if not binding.book_bindings:
        return invalid(
            "book_bindings",
            "an operable account binding declares at least one Book binding; "
            "sensing-only is the legal path with none",
            index=index,
        )
    if set(binding.state_carry) != set(STATE_CARRY_COUNTERS):
        return invalid(
            "state_carry",
            "state_carry must declare every counter exactly once",
            index=index,
            required=list(STATE_CARRY_COUNTERS),
            given=sorted(binding.state_carry),
        )
    if any(v is StateCarryChoice.CARRY for v in binding.state_carry.values()) and (
        binding.carries_ledger_signature is None
    ):
        return invalid(
            "carries_ledger_signature",
            "state_carry carry requires a human-signed carries-ledger signature",
            index=index,
        )
    # Refuse smuggling sensing-only markers onto an operable binding.
    return Ok(binding)


def _parse_book_bindings(raw: object, *, index: int) -> Result[tuple[BookBindingDecl, ...]]:
    seq = _as_sequence(raw, "book_bindings")
    if is_refusal(seq):
        return seq
    books: list[BookBindingDecl] = []
    seen_ids: set[str] = set()
    for book_index, item in enumerate(seq.value):
        if isinstance(item, BookBindingDecl):
            book = item
        elif isinstance(item, Mapping):
            body = cast("Mapping[str, object]", item)
            binding_id = clean_token(body.get("binding_id"))
            book_fp = clean_token(body.get("book_definition_fp1"))
            instruments = _as_token_set(body.get("instruments"), "instruments")
            if is_refusal(instruments):
                return instruments
            if binding_id is None or book_fp is None:
                return invalid(
                    "book_bindings",
                    "book binding requires binding_id and book_definition_fp1",
                    index=index,
                    book_index=book_index,
                )
            attrib_raw = body.get("attribution_instruments")
            attrib: frozenset[str] | None
            if attrib_raw is None:
                attrib = None
            else:
                attrib_set = _as_token_set(attrib_raw, "attribution_instruments")
                if is_refusal(attrib_set):
                    return attrib_set
                attrib = attrib_set.value
            sig = body.get("shared_flatten_signature")
            sig_token: str | None
            if sig is None:
                sig_token = None
            else:
                sig_token = clean_token(sig)
                if sig_token is None:
                    return invalid(
                        "shared_flatten_signature",
                        "shared-flatten signature is a non-blank token when supplied",
                        index=index,
                        book_index=book_index,
                    )
            book = BookBindingDecl(
                binding_id=binding_id,
                book_definition_fp1=book_fp,
                instruments=instruments.value,
                attribution_instruments=attrib,
                shared_flatten_signature=sig_token,
            )
        else:
            return invalid(
                "book_bindings",
                "each book binding is a BookBindingDecl or mapping",
                index=index,
                book_index=book_index,
                given=type(item).__name__,
            )
        if book.binding_id in seen_ids:
            return invalid(
                "binding_id",
                "book binding ids on one account must be unique",
                index=index,
                binding_id=book.binding_id,
            )
        seen_ids.add(book.binding_id)
        if not book.instruments:
            return invalid(
                "instruments",
                "a Book binding declares a non-empty instrument set",
                index=index,
                binding_id=book.binding_id,
            )
        books.append(book)
    return Ok(tuple(books))


def _parse_sensing_only(raw: object, *, index: int) -> Result[SensingOnlyDecl]:
    if isinstance(raw, SensingOnlyDecl):
        sensing = raw
    elif isinstance(raw, Mapping):
        body = cast("Mapping[str, object]", raw)
        # Sensing-only must not smuggle Book/BMS/sequencer fields.
        forbidden = {
            "book_bindings",
            "bms_definition_fp1",
            "bms_instance_id",
            "state_carry",
            "opens_sequencer",
            "execution_target",
            "position_model",
            "throttle_scope",
        }
        present = sorted(k for k in forbidden if k in body)
        if present:
            return policy(
                "sensing_only",
                "sensing-only is a legal compiled state with no Book binding, "
                "BMS instance, or command stream; refuse operable fields",
                index=index,
                forbidden_fields=present,
            )
        venue_id = clean_token(body.get("venue_id"))
        environment = clean_token(body.get("environment"))
        account_id = clean_token(body.get("account_id"))
        credential_reference = clean_token(body.get("credential_reference"))
        opaque = clean_token(body.get("opaque_metric_id"))
        world = _coerce_world(body.get("world", World.LIVE))
        if (
            venue_id is None
            or environment is None
            or account_id is None
            or credential_reference is None
            or opaque is None
            or world is None
        ):
            return invalid(
                "sensing_only",
                "sensing-only requires venue_id, environment, account_id, "
                "credential_reference, and opaque_metric_id",
                index=index,
            )
        sensing = SensingOnlyDecl(
            venue_id=venue_id,
            environment=environment,
            account_id=account_id,
            credential_reference=credential_reference,
            opaque_metric_id=opaque,
            world=world,
        )
    else:
        return invalid(
            "sensing_only",
            "each sensing-only entry is a SensingOnlyDecl or mapping",
            index=index,
            given=type(raw).__name__,
        )
    if sensing.environment not in _ENVIRONMENTS:
        return invalid(
            "environment",
            "roster environment is demo | live",
            index=index,
            given=sensing.environment,
        )
    return Ok(sensing)


def _parse_state_carry(raw: object, *, index: int) -> Result[Mapping[str, StateCarryChoice]]:
    if not isinstance(raw, Mapping):
        return invalid(
            "state_carry",
            "state_carry is a mapping of the five counters to carry|reset",
            index=index,
            given=type(raw).__name__,
        )
    body = cast("Mapping[str, object]", raw)
    resolved: dict[str, StateCarryChoice] = {}
    for name in STATE_CARRY_COUNTERS:
        if name not in body:
            return invalid(
                "state_carry",
                "state_carry must declare every counter; absence is invalid input",
                index=index,
                missing=name,
            )
        choice = _coerce_carry(body[name])
        if choice is None:
            return invalid(
                "state_carry",
                "each state_carry counter is carry | reset",
                index=index,
                counter=name,
                given=repr(body[name]),
            )
        resolved[name] = choice
    extra = sorted(set(body) - set(STATE_CARRY_COUNTERS))
    if extra:
        return invalid(
            "state_carry",
            "unknown state_carry counters refused",
            index=index,
            unknown=extra,
        )
    return Ok(MappingProxyType(resolved))


def _prove_netting_attribution(
    bindings: Sequence[AccountBindingDecl],
) -> Result[None]:
    """Prove attribution declarations are a partition on each netted account."""
    by_account: dict[str, list[AccountBindingDecl]] = {}
    for binding in bindings:
        key = f"{binding.venue_id}::{binding.account_id}"
        by_account.setdefault(key, []).append(binding)

    for account_key, group in by_account.items():
        # One operable row per (venue, account) after duplicate check — still
        # prove across that row's Book bindings.
        for binding in group:
            if binding.position_model is not PositionModelDecl.NETTING:
                continue
            books = binding.book_bindings
            # Mandatory attribution declaration on every Book of a netted account.
            for book in books:
                if book.attribution_instruments is None:
                    return policy(
                        "attribution_instruments",
                        "where CT-18 declares netting, the fill-to-virtual-position "
                        "attribution declaration is mandatory; absence is a bind-time "
                        "policy rejection",
                        account=account_key,
                        binding_id=book.binding_id,
                    )
                if not book.attribution_instruments:
                    return invalid(
                        "attribution_instruments",
                        "netting attribution declaration must name a non-empty instrument set",
                        account=account_key,
                        binding_id=book.binding_id,
                    )
                # Attribution instruments must be a subset of the Book's instruments.
                if not book.attribution_instruments <= book.instruments:
                    return invalid(
                        "attribution_instruments",
                        "attribution instruments must be a subset of the Book's "
                        "declared instruments",
                        account=account_key,
                        binding_id=book.binding_id,
                    )

            # Shared-flatten signature for second Book with overlap.
            if len(books) > 1:
                for i, left in enumerate(books):
                    for right in books[i + 1 :]:
                        overlap = left.instruments & right.instruments
                        if overlap and (
                            left.shared_flatten_signature is None
                            or right.shared_flatten_signature is None
                        ):
                            return unsupported(
                                "shared_flatten_signature",
                                "a second Book on a netting account whose live "
                                "bindings may trade an overlapping instrument set "
                                "needs the operator's signed shared-flatten "
                                "limitation; one Book per netted account is the "
                                "V1 default",
                                account=account_key,
                                overlapping=sorted(overlap),
                            )

            # Partition proof: jointly exhaustive and disjoint over the union.
            covered: set[str] = set()
            for book in books:
                attrib = book.attribution_instruments
                if attrib is None:
                    continue  # already refused above
                overlap = covered & attrib
                if overlap:
                    return invalid(
                        "attribution_instruments",
                        "netting attribution declarations on one account must be "
                        "jointly disjoint; overlap is an invalid input refusal at "
                        "compose, never a trade-time discovery",
                        account=account_key,
                        overlapping=sorted(overlap),
                        binding_id=book.binding_id,
                    )
                covered |= attrib
            universe: set[str] = set()
            for book in books:
                universe |= book.instruments
            missing = universe - covered
            if missing:
                return invalid(
                    "attribution_instruments",
                    "netting attribution declarations on one account must be "
                    "jointly exhaustive over every instrument the bindings may "
                    "trade; gaps are an invalid input refusal at compose",
                    account=account_key,
                    missing=sorted(missing),
                )
    return Ok(None)


def _as_stream_key(raw: object, field: str) -> Result[CommandStreamRuntimeKey]:
    if isinstance(raw, CommandStreamRuntimeKey):
        return Ok(raw)
    if isinstance(raw, CommandStreamPlan):
        return Ok(raw.stream)
    if isinstance(raw, Mapping):
        body = cast("Mapping[str, object]", raw)
        venue_id = clean_token(body.get("venue_id"))
        account_id = clean_token(body.get("account_id"))
        if venue_id is None or account_id is None:
            return invalid(
                field,
                "stream key requires venue_id and account_id",
            )
        return Ok(CommandStreamRuntimeKey(venue_id=venue_id, account_id=account_id))
    return invalid(
        field,
        "stream key is a CommandStreamRuntimeKey, CommandStreamPlan, or mapping",
        given=type(raw).__name__,
    )


def _as_sequence(raw: object, field: str) -> Result[tuple[object, ...]]:
    if raw is None:
        return Ok(())
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        return invalid(
            field,
            f"{field} is a sequence of roster rows",
            given=type(raw).__name__,
        )
    return Ok(tuple(cast("Sequence[object]", raw)))


def _as_token_set(raw: object, field: str) -> Result[frozenset[str]]:
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        return invalid(field, f"{field} is a sequence of non-blank tokens")
    tokens: set[str] = set()
    for item in cast("Sequence[object]", raw):
        token = clean_token(item)
        if token is None:
            return invalid(field, f"{field} entries are non-blank tokens")
        tokens.add(token)
    return Ok(frozenset(tokens))


def _as_non_negative_int(raw: object, field: str) -> Result[int]:
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        return invalid(
            field,
            f"registry:{field} is a non-negative count; blank/invented values refuse",
            given=repr(raw),
        )
    return Ok(raw)


def _coerce_role(value: object) -> AccountRole | None:
    if isinstance(value, AccountRole):
        return value
    if isinstance(value, str):
        try:
            return AccountRole(value.strip())
        except ValueError:
            return None
    return None


def _coerce_world(value: object) -> World | None:
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value.strip())
        except ValueError:
            return None
    return None


def _coerce_throttle(value: object) -> ThrottleScope | None:
    if isinstance(value, ThrottleScope):
        return value
    token = clean_token(value)
    if token is None or token not in _THROTTLE_SCOPES:
        return None
    return ThrottleScope(token)


def _coerce_position_model(value: object) -> PositionModelDecl | None:
    if isinstance(value, PositionModelDecl):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return PositionModelDecl(token)
    except ValueError:
        return None


def _coerce_carry(value: object) -> StateCarryChoice | None:
    if isinstance(value, StateCarryChoice):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return StateCarryChoice(token)
    except ValueError:
        return None
