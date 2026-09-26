"""Compose-time Layer-1 admission over the assembled runtime risk graph.

Story 26.11 / QMX-F067 / D010 / AD-32. Valid individual BMS, Book, binding,
seat, paired-target, window, priority, and capability records still collapse
into an invalid population. Compose checks cardinalities, referential
integrity, total unique rank, declared scopes, netting partitions,
one-BMS-per-account/many-Books, one-Book-per-bot, and one active paper target
together and refuses before Seal.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core import AccountRole, Ok, Result, TypedRefusal, World, is_refusal
from qmf.risk.control_rank import ControlRankTable
from qmf.risk.control_window import RATIFIED_WINDOW_KINDS, WindowKind

from qmn.config.roster import RosterRuntimeComposition
from qmn.host._refuse import clean_token, invalid, policy, unavailable
from qmn.ledger.attribution import (
    AttributionDeclaration,
    PositionModelKind,
    prove_attribution_partition,
)
from qmn.paper.routing import NODE_PAPER_ACCOUNT_ROLE
from qmn.protection.dispatch import require_total_unique_rank_table

__all__ = [
    "LAYER1_CHECKS",
    "MISMATCH_REFUSES_BEFORE_SEAL",
    "RISK_POPULATION_SURFACE",
    "CapabilityRecord",
    "Layer1PopulationProof",
    "PairedTargetRecord",
    "PopulationBindingRecord",
    "PopulationBmsRecord",
    "PopulationBookRecord",
    "PriorityRecord",
    "RuntimeRiskGraph",
    "ScopeRecord",
    "SeatRecord",
    "WindowRecord",
    "admit_runtime_risk_population",
]

RISK_POPULATION_SURFACE: Final[str] = "qmn.host.risk_population"
MISMATCH_REFUSES_BEFORE_SEAL: Final[bool] = True

LAYER1_CHECKS: Final[tuple[str, ...]] = (
    "cardinalities",
    "referential_integrity",
    "total_unique_rank",
    "declared_scopes",
    "netting_partitions",
    "one_bms_per_account_many_books",
    "one_book_per_bot",
    "one_active_paper_target",
)

_T = TypeVar("_T")


def _failure(refusal: TypedRefusal, *, failure_id: str) -> TypedRefusal:
    """Stamp a Compose failure id onto a typed refusal."""
    context = dict(refusal.context)
    context.setdefault("failure_id", failure_id)
    context.setdefault("refuses_before_seal", True)
    return TypedRefusal(
        category=refusal.category,
        retryability=refusal.retryability,
        context=context,
    )


def _as_record_tuple(
    value: object, field: str, expected: type[_T]
) -> Result[tuple[_T, ...]]:
    if value is None:
        return Ok(())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            field,
            f"{field} is a sequence of {expected.__name__}",
            given=type(value).__name__,
            failure_id="compose.risk_population",
        )
    typed: list[_T] = []
    for item in cast("Sequence[object]", value):
        if not isinstance(item, expected):
            return invalid(
                field,
                f"each {field} item is a {expected.__name__}",
                given=type(item).__name__,
                failure_id="compose.risk_population",
            )
        typed.append(item)
    return Ok(tuple(typed))


@dataclass(frozen=True, slots=True)
class PopulationBmsRecord:
    """One BMS instance serving one (venue, account)."""

    bms_instance_id: str
    venue_id: str
    account_id: str
    definition_fp1: str

    @classmethod
    def try_create(
        cls,
        *,
        bms_instance_id: object,
        venue_id: object,
        account_id: object,
        definition_fp1: object,
    ) -> Result[PopulationBmsRecord]:
        bms = clean_token(bms_instance_id)
        venue = clean_token(venue_id)
        account = clean_token(account_id)
        definition = clean_token(definition_fp1)
        if bms is None or venue is None or account is None or definition is None:
            return invalid(
                "bms",
                "a BMS record names bms_instance_id, venue_id, account_id, and "
                "definition_fp1",
                failure_id="compose.risk_population.referential_integrity",
            )
        return Ok(
            cls(
                bms_instance_id=bms,
                venue_id=venue,
                account_id=account,
                definition_fp1=definition,
            )
        )


@dataclass(frozen=True, slots=True)
class PopulationBookRecord:
    """One Book instance bound to exactly one BMS."""

    book_instance_id: str
    bms_instance_id: str
    definition_fp1: str

    @classmethod
    def try_create(
        cls,
        *,
        book_instance_id: object,
        bms_instance_id: object,
        definition_fp1: object,
    ) -> Result[PopulationBookRecord]:
        book = clean_token(book_instance_id)
        bms = clean_token(bms_instance_id)
        definition = clean_token(definition_fp1)
        if book is None or bms is None or definition is None:
            return invalid(
                "book",
                "a Book record names book_instance_id, bms_instance_id, and "
                "definition_fp1",
                failure_id="compose.risk_population.referential_integrity",
            )
        return Ok(
            cls(
                book_instance_id=book,
                bms_instance_id=bms,
                definition_fp1=definition,
            )
        )


@dataclass(frozen=True, slots=True)
class PopulationBindingRecord:
    """One Book/BMS binding on a (venue, account) command stream."""

    binding_id: str
    book_instance_id: str
    bms_instance_id: str
    venue_id: str
    account_id: str
    role: AccountRole
    world: World
    environment: str
    position_model: str
    instruments: frozenset[str]
    attribution_instruments: frozenset[str] | None = None
    shared_flatten_signature: str | None = None

    @property
    def stream_key(self) -> str:
        return f"{self.venue_id}::{self.account_id}"

    @classmethod
    def try_create(
        cls,
        *,
        binding_id: object,
        book_instance_id: object,
        bms_instance_id: object,
        venue_id: object,
        account_id: object,
        role: object,
        world: object,
        environment: object,
        position_model: object,
        instruments: object,
        attribution_instruments: object = None,
        shared_flatten_signature: object = None,
    ) -> Result[PopulationBindingRecord]:
        binding = clean_token(binding_id)
        book = clean_token(book_instance_id)
        bms = clean_token(bms_instance_id)
        venue = clean_token(venue_id)
        account = clean_token(account_id)
        env = clean_token(environment)
        model = clean_token(position_model)
        if (
            binding is None
            or book is None
            or bms is None
            or venue is None
            or account is None
            or env is None
            or model is None
        ):
            return invalid(
                "binding",
                "a binding record names binding, book, BMS, venue, account, "
                "environment, and position_model",
                failure_id="compose.risk_population.referential_integrity",
            )
        if not isinstance(role, AccountRole):
            return invalid(
                "role",
                "a binding role is an AccountRole",
                given=repr(role),
                failure_id="compose.risk_population.referential_integrity",
            )
        if not isinstance(world, World):
            return invalid(
                "world",
                "a binding world is a World",
                given=repr(world),
                failure_id="compose.risk_population.referential_integrity",
            )
        if model not in {PositionModelKind.NETTING.value, PositionModelKind.HEDGING.value}:
            return invalid(
                "position_model",
                "position model is netting|hedging",
                given=model,
                failure_id="compose.risk_population.netting_partitions",
            )
        inst = _token_set(instruments, "instruments")
        if is_refusal(inst):
            return inst
        attrib: frozenset[str] | None
        if attribution_instruments is None:
            attrib = None
        else:
            attrib_set = _token_set(attribution_instruments, "attribution_instruments")
            if is_refusal(attrib_set):
                return attrib_set
            attrib = attrib_set.value
        sig = None
        if shared_flatten_signature is not None:
            sig = clean_token(shared_flatten_signature)
            if sig is None:
                return invalid(
                    "shared_flatten_signature",
                    "shared-flatten signature is a non-blank token when supplied",
                    failure_id="compose.risk_population.netting_partitions",
                )
        return Ok(
            cls(
                binding_id=binding,
                book_instance_id=book,
                bms_instance_id=bms,
                venue_id=venue,
                account_id=account,
                role=role,
                world=world,
                environment=env,
                position_model=model,
                instruments=inst.value,
                attribution_instruments=attrib,
                shared_flatten_signature=sig,
            )
        )


def _token_set(value: object, field: str) -> Result[frozenset[str]]:
    if not isinstance(value, (set, frozenset, list, tuple)):
        return invalid(
            field,
            f"{field} is a set of instrument tokens",
            given=type(value).__name__,
            failure_id="compose.risk_population",
        )
    tokens: list[str] = []
    for item in cast("Iterable[object]", value):
        token = clean_token(item)
        if token is None:
            return invalid(
                field,
                f"{field} members are non-blank tokens",
                given=repr(item),
                failure_id="compose.risk_population",
            )
        tokens.append(token)
    return Ok(frozenset(tokens))


@dataclass(frozen=True, slots=True)
class SeatRecord:
    """One governed seat: a bot bound to exactly one Book via one binding."""

    seat_id: str
    bot_id: str
    book_instance_id: str
    binding_id: str

    @classmethod
    def try_create(
        cls,
        *,
        seat_id: object,
        bot_id: object,
        book_instance_id: object,
        binding_id: object,
    ) -> Result[SeatRecord]:
        seat = clean_token(seat_id)
        bot = clean_token(bot_id)
        book = clean_token(book_instance_id)
        binding = clean_token(binding_id)
        if seat is None or bot is None or book is None or binding is None:
            return invalid(
                "seat",
                "a seat names seat_id, bot_id, book_instance_id, and binding_id",
                failure_id="compose.risk_population.referential_integrity",
            )
        return Ok(
            cls(
                seat_id=seat,
                bot_id=bot,
                book_instance_id=book,
                binding_id=binding,
            )
        )


@dataclass(frozen=True, slots=True)
class PairedTargetRecord:
    """One active paper-routing target for a live binding."""

    live_binding_id: str
    paper_account_id: str
    paper_role: AccountRole
    paper_bms_instance_id: str

    @classmethod
    def try_create(
        cls,
        *,
        live_binding_id: object,
        paper_account_id: object,
        paper_role: object,
        paper_bms_instance_id: object,
    ) -> Result[PairedTargetRecord]:
        live = clean_token(live_binding_id)
        paper = clean_token(paper_account_id)
        paper_bms = clean_token(paper_bms_instance_id)
        if live is None or paper is None or paper_bms is None:
            return invalid(
                "paired_target",
                "a paired target names the live binding, demo account, and "
                "paper BMS instance",
                failure_id="compose.risk_population.one_active_paper_target",
            )
        if not isinstance(paper_role, AccountRole):
            return invalid(
                "paper_role",
                "the paper target role is an AccountRole",
                given=repr(paper_role),
                failure_id="compose.risk_population.one_active_paper_target",
            )
        return Ok(
            cls(
                live_binding_id=live,
                paper_account_id=paper,
                paper_role=paper_role,
                paper_bms_instance_id=paper_bms,
            )
        )


@dataclass(frozen=True, slots=True)
class WindowRecord:
    """One required protection window declared on a binding."""

    window_id: str
    kind: str
    binding_id: str

    @classmethod
    def try_create(
        cls,
        *,
        window_id: object,
        kind: object,
        binding_id: object,
    ) -> Result[WindowRecord]:
        window = clean_token(window_id)
        kind_token = clean_token(kind)
        binding = clean_token(binding_id)
        if window is None or kind_token is None or binding is None:
            return invalid(
                "window",
                "a window record names window_id, kind, and binding_id",
                failure_id="compose.risk_population.referential_integrity",
            )
        allowed = {member.value for member in RATIFIED_WINDOW_KINDS}
        if kind_token not in allowed:
            return invalid(
                "kind",
                "window kind is news|daily_dead_zone|session_handover_buffer",
                given=kind_token,
                allowed=sorted(allowed),
                failure_id="compose.risk_population.referential_integrity",
            )
        return Ok(cls(window_id=window, kind=kind_token, binding_id=binding))


@dataclass(frozen=True, slots=True)
class PriorityRecord:
    """BMS-declared AD-37 rank table for one (venue, account) stream."""

    venue_id: str
    account_id: str
    rank_table: ControlRankTable

    @property
    def stream_key(self) -> str:
        return f"{self.venue_id}::{self.account_id}"

    @classmethod
    def try_create(
        cls,
        *,
        venue_id: object,
        account_id: object,
        rank_table: object,
    ) -> Result[PriorityRecord]:
        venue = clean_token(venue_id)
        account = clean_token(account_id)
        if venue is None or account is None:
            return invalid(
                "priority",
                "a priority record names venue_id and account_id",
                failure_id="compose.risk_population.total_unique_rank",
            )
        table = require_total_unique_rank_table(rank_table)
        if is_refusal(table):
            context = dict(table.context)
            context["failure_id"] = "compose.risk_population.total_unique_rank"
            return type(table)(
                category=table.category,
                retryability=table.retryability,
                context=context,
            )
        return Ok(cls(venue_id=venue, account_id=account, rank_table=table.value))


@dataclass(frozen=True, slots=True)
class CapabilityRecord:
    """Bind-time capability check material for one binding."""

    binding_id: str
    required: frozenset[str]
    declared: frozenset[str]

    @classmethod
    def try_create(
        cls,
        *,
        binding_id: object,
        required: object,
        declared: object,
    ) -> Result[CapabilityRecord]:
        binding = clean_token(binding_id)
        if binding is None:
            return invalid(
                "capability",
                "a capability record names a binding_id",
                failure_id="compose.risk_population.referential_integrity",
            )
        req = _token_set(required, "required")
        if is_refusal(req):
            return req
        decl = _token_set(declared, "declared")
        if is_refusal(decl):
            return decl
        return Ok(cls(binding_id=binding, required=req.value, declared=decl.value))


@dataclass(frozen=True, slots=True)
class ScopeRecord:
    """Declared KSA/control enforcement scope: global or one command stream."""

    kind: str
    venue_id: str | None = None
    account_id: str | None = None

    @property
    def token(self) -> str:
        if self.kind == "global":
            return "global"
        return f"stream:{self.venue_id}::{self.account_id}"

    @property
    def stream_key(self) -> str | None:
        if self.kind != "stream" or self.venue_id is None or self.account_id is None:
            return None
        return f"{self.venue_id}::{self.account_id}"

    @classmethod
    def try_create(
        cls,
        *,
        kind: object,
        venue_id: object = None,
        account_id: object = None,
    ) -> Result[ScopeRecord]:
        scope_kind = clean_token(kind)
        if scope_kind not in {"global", "stream"}:
            return invalid(
                "scope",
                "a declared scope is global or stream",
                given=repr(kind),
                failure_id="compose.risk_population.declared_scopes",
            )
        if scope_kind == "global":
            return Ok(cls(kind="global"))
        venue = clean_token(venue_id)
        account = clean_token(account_id)
        if venue is None or account is None:
            return invalid(
                "scope",
                "a stream scope names venue_id and account_id",
                failure_id="compose.risk_population.declared_scopes",
            )
        return Ok(cls(kind="stream", venue_id=venue, account_id=account))


@dataclass(frozen=True, slots=True)
class RuntimeRiskGraph:
    """Assembled Compose-time risk population (QMX-F067)."""

    bms: tuple[PopulationBmsRecord, ...]
    books: tuple[PopulationBookRecord, ...]
    bindings: tuple[PopulationBindingRecord, ...]
    seats: tuple[SeatRecord, ...]
    paired_targets: tuple[PairedTargetRecord, ...]
    windows: tuple[WindowRecord, ...]
    priorities: tuple[PriorityRecord, ...]
    capabilities: tuple[CapabilityRecord, ...]
    scopes: tuple[ScopeRecord, ...]
    roster: RosterRuntimeComposition | None = None

    @classmethod
    def try_create(
        cls,
        *,
        bms: object = (),
        books: object = (),
        bindings: object = (),
        seats: object = (),
        paired_targets: object = (),
        windows: object = (),
        priorities: object = (),
        capabilities: object = (),
        scopes: object = (),
        roster: object = None,
    ) -> Result[RuntimeRiskGraph]:
        parsed_bms = _as_record_tuple(bms, "bms", PopulationBmsRecord)
        if is_refusal(parsed_bms):
            return parsed_bms
        parsed_books = _as_record_tuple(books, "books", PopulationBookRecord)
        if is_refusal(parsed_books):
            return parsed_books
        parsed_bindings = _as_record_tuple(
            bindings, "bindings", PopulationBindingRecord
        )
        if is_refusal(parsed_bindings):
            return parsed_bindings
        parsed_seats = _as_record_tuple(seats, "seats", SeatRecord)
        if is_refusal(parsed_seats):
            return parsed_seats
        parsed_targets = _as_record_tuple(
            paired_targets, "paired_targets", PairedTargetRecord
        )
        if is_refusal(parsed_targets):
            return parsed_targets
        parsed_windows = _as_record_tuple(windows, "windows", WindowRecord)
        if is_refusal(parsed_windows):
            return parsed_windows
        parsed_priorities = _as_record_tuple(
            priorities, "priorities", PriorityRecord
        )
        if is_refusal(parsed_priorities):
            return parsed_priorities
        parsed_caps = _as_record_tuple(
            capabilities, "capabilities", CapabilityRecord
        )
        if is_refusal(parsed_caps):
            return parsed_caps
        parsed_scopes = _as_record_tuple(scopes, "scopes", ScopeRecord)
        if is_refusal(parsed_scopes):
            return parsed_scopes
        roster_value: RosterRuntimeComposition | None
        if roster is None:
            roster_value = None
        elif isinstance(roster, RosterRuntimeComposition):
            roster_value = roster
        else:
            return invalid(
                "roster",
                "roster is a RosterRuntimeComposition when supplied",
                given=type(roster).__name__,
                failure_id="compose.risk_population",
            )
        return Ok(
            cls(
                bms=parsed_bms.value,
                books=parsed_books.value,
                bindings=parsed_bindings.value,
                seats=parsed_seats.value,
                paired_targets=parsed_targets.value,
                windows=parsed_windows.value,
                priorities=parsed_priorities.value,
                capabilities=parsed_caps.value,
                scopes=parsed_scopes.value,
                roster=roster_value,
            )
        )


@dataclass(frozen=True, slots=True)
class Layer1PopulationProof:
    """Proof that Compose admitted the assembled risk graph together."""

    checks_run: tuple[str, ...]
    binding_ids: tuple[str, ...]
    book_ids: tuple[str, ...]
    bms_ids: tuple[str, ...]
    bot_ids: tuple[str, ...]
    stream_keys: tuple[str, ...]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_ids": self.binding_ids,
                "bms_ids": self.bms_ids,
                "book_ids": self.book_ids,
                "bot_ids": self.bot_ids,
                "checks_run": self.checks_run,
                "mismatch_refuses_before_seal": MISMATCH_REFUSES_BEFORE_SEAL,
                "stream_keys": self.stream_keys,
                "surface": RISK_POPULATION_SURFACE,
            }
        )


def admit_runtime_risk_population(graph: object) -> Result[Layer1PopulationProof]:
    """Run every Layer-1 population check together; mismatch refuses before Seal."""
    if not isinstance(graph, RuntimeRiskGraph):
        return invalid(
            "risk_population",
            "Compose Layer-1 admission reads a RuntimeRiskGraph",
            given=type(graph).__name__,
            failure_id="compose.risk_population",
        )

    referential = _check_referential_integrity(graph)
    if is_refusal(referential):
        return _failure(referential, failure_id="compose.risk_population.referential_integrity")

    ranks = _check_total_unique_rank(graph)
    if is_refusal(ranks):
        return _failure(ranks, failure_id="compose.risk_population.total_unique_rank")

    scopes = _check_declared_scopes(graph)
    if is_refusal(scopes):
        return _failure(scopes, failure_id="compose.risk_population.declared_scopes")

    netting = _check_netting_partitions(graph)
    if is_refusal(netting):
        return _failure(netting, failure_id="compose.risk_population.netting_partitions")

    bms_card = _check_one_bms_per_account_many_books(graph)
    if is_refusal(bms_card):
        return _failure(
            bms_card, failure_id="compose.risk_population.one_bms_per_account"
        )

    book_card = _check_one_book_per_bot(graph)
    if is_refusal(book_card):
        return _failure(book_card, failure_id="compose.risk_population.one_book_per_bot")

    paper_card = _check_one_active_paper_target(graph)
    if is_refusal(paper_card):
        return _failure(
            paper_card, failure_id="compose.risk_population.one_active_paper_target"
        )

    roster = _check_roster_alignment(graph)
    if is_refusal(roster):
        return _failure(roster, failure_id="compose.risk_population.cardinalities")

    streams = tuple(sorted({row.stream_key for row in graph.bindings}))
    return Ok(
        Layer1PopulationProof(
            checks_run=LAYER1_CHECKS,
            binding_ids=tuple(row.binding_id for row in graph.bindings),
            book_ids=tuple(row.book_instance_id for row in graph.books),
            bms_ids=tuple(row.bms_instance_id for row in graph.bms),
            bot_ids=tuple(sorted({row.bot_id for row in graph.seats})),
            stream_keys=streams,
        )
    )


def _check_referential_integrity(graph: RuntimeRiskGraph) -> Result[None]:
    bms_ids = {row.bms_instance_id: row for row in graph.bms}
    if len(bms_ids) != len(graph.bms):
        return invalid(
            "bms",
            "BMS instance ids are unique in the assembled population",
            failure_id="compose.risk_population.referential_integrity",
        )
    book_ids = {row.book_instance_id: row for row in graph.books}
    if len(book_ids) != len(graph.books):
        return invalid(
            "books",
            "Book instance ids are unique in the assembled population",
            failure_id="compose.risk_population.referential_integrity",
        )
    binding_ids = {row.binding_id: row for row in graph.bindings}
    if len(binding_ids) != len(graph.bindings):
        return invalid(
            "bindings",
            "binding ids are unique in the assembled population",
            failure_id="compose.risk_population.referential_integrity",
        )
    seat_ids = {row.seat_id for row in graph.seats}
    if len(seat_ids) != len(graph.seats):
        return invalid(
            "seats",
            "seat ids are unique in the assembled population",
            failure_id="compose.risk_population.referential_integrity",
        )

    for book in graph.books:
        if book.bms_instance_id not in bms_ids:
            return unavailable(
                "book",
                "a Book must cite an assembled BMS instance",
                book_instance_id=book.book_instance_id,
                bms_instance_id=book.bms_instance_id,
                failure_id="compose.risk_population.referential_integrity",
            )
        bms = bms_ids[book.bms_instance_id]
        if book.bms_instance_id != bms.bms_instance_id:
            return invalid(
                "book",
                "Book/BMS referential integrity failed",
                failure_id="compose.risk_population.referential_integrity",
            )

    for binding in graph.bindings:
        if binding.book_instance_id not in book_ids:
            return unavailable(
                "binding",
                "a binding must cite an assembled Book instance",
                binding_id=binding.binding_id,
                book_instance_id=binding.book_instance_id,
                failure_id="compose.risk_population.referential_integrity",
            )
        if binding.bms_instance_id not in bms_ids:
            return unavailable(
                "binding",
                "a binding must cite an assembled BMS instance",
                binding_id=binding.binding_id,
                bms_instance_id=binding.bms_instance_id,
                failure_id="compose.risk_population.referential_integrity",
            )
        book = book_ids[binding.book_instance_id]
        if book.bms_instance_id != binding.bms_instance_id:
            return invalid(
                "binding",
                "a binding's BMS must equal the cited Book's BMS",
                binding_id=binding.binding_id,
                failure_id="compose.risk_population.referential_integrity",
            )
        bms = bms_ids[binding.bms_instance_id]
        if bms.venue_id != binding.venue_id or bms.account_id != binding.account_id:
            return invalid(
                "binding",
                "a binding's (venue, account) must equal its BMS account",
                binding_id=binding.binding_id,
                failure_id="compose.risk_population.referential_integrity",
            )

    for seat in graph.seats:
        binding = binding_ids.get(seat.binding_id)
        if binding is None:
            return unavailable(
                "seat",
                "a seat must cite an assembled binding",
                seat_id=seat.seat_id,
                binding_id=seat.binding_id,
                failure_id="compose.risk_population.referential_integrity",
            )
        if seat.book_instance_id != binding.book_instance_id:
            return invalid(
                "seat",
                "a seat's Book must equal the cited binding's Book",
                seat_id=seat.seat_id,
                failure_id="compose.risk_population.referential_integrity",
            )
        if seat.book_instance_id not in book_ids:
            return unavailable(
                "seat",
                "a seat must cite an assembled Book instance",
                seat_id=seat.seat_id,
                book_instance_id=seat.book_instance_id,
                failure_id="compose.risk_population.referential_integrity",
            )

    for window in graph.windows:
        if window.binding_id not in binding_ids:
            return unavailable(
                "window",
                "a window must cite an assembled binding",
                window_id=window.window_id,
                binding_id=window.binding_id,
                failure_id="compose.risk_population.referential_integrity",
            )

    seen_window: set[tuple[str, str]] = set()
    for window in graph.windows:
        key = (window.binding_id, window.kind)
        if key in seen_window:
            return invalid(
                "window",
                "one window kind per binding; duplicate kinds collapse the population",
                binding_id=window.binding_id,
                kind=window.kind,
                failure_id="compose.risk_population.cardinalities",
            )
        seen_window.add(key)

    required_kinds = {member.value for member in WindowKind}
    bindings_with_windows = {window.binding_id for window in graph.windows}
    for binding_id in bindings_with_windows:
        present = {
            window.kind for window in graph.windows if window.binding_id == binding_id
        }
        missing = required_kinds - present
        if missing:
            return invalid(
                "window",
                "required window kinds news, daily_dead_zone, and "
                "session_handover_buffer are declared together per binding",
                binding_id=binding_id,
                missing=sorted(missing),
                failure_id="compose.risk_population.cardinalities",
            )

    cap_by_binding: dict[str, CapabilityRecord] = {}
    for cap in graph.capabilities:
        if cap.binding_id in cap_by_binding:
            return invalid(
                "capabilities",
                "one capability record per binding",
                binding_id=cap.binding_id,
                failure_id="compose.risk_population.cardinalities",
            )
        cap_by_binding[cap.binding_id] = cap
        if cap.binding_id not in binding_ids:
            return unavailable(
                "capability",
                "a capability record must cite an assembled binding",
                binding_id=cap.binding_id,
                failure_id="compose.risk_population.referential_integrity",
            )
        missing_caps = cap.required - cap.declared
        if missing_caps:
            return unavailable(
                "capability",
                "declared venue capabilities must cover the binding's required set",
                binding_id=cap.binding_id,
                missing=sorted(missing_caps),
                failure_id="compose.risk_population.referential_integrity",
            )
    for binding in graph.bindings:
        if binding.binding_id not in cap_by_binding:
            return unavailable(
                "capability",
                "every binding carries a capability record at Compose",
                binding_id=binding.binding_id,
                failure_id="compose.risk_population.referential_integrity",
            )
    return Ok(None)


def _check_total_unique_rank(graph: RuntimeRiskGraph) -> Result[None]:
    streams = {row.stream_key for row in graph.bindings}
    seen: dict[str, PriorityRecord] = {}
    for row in graph.priorities:
        table = require_total_unique_rank_table(row.rank_table)
        if is_refusal(table):
            return table
        if row.stream_key in seen:
            return invalid(
                "priority",
                "one BMS rank table per (VenueId, account) command stream",
                stream=row.stream_key,
                failure_id="compose.risk_population.total_unique_rank",
            )
        seen[row.stream_key] = row
        if row.stream_key not in streams:
            return unavailable(
                "priority",
                "a rank table must name an assembled command stream",
                stream=row.stream_key,
                failure_id="compose.risk_population.total_unique_rank",
            )
    for stream in streams:
        if stream not in seen:
            return unavailable(
                "priority",
                "every assembled command stream carries a total unique rank table",
                stream=stream,
                failure_id="compose.risk_population.total_unique_rank",
            )
    return Ok(None)


def _check_declared_scopes(graph: RuntimeRiskGraph) -> Result[None]:
    streams = {row.stream_key for row in graph.bindings}
    has_global = False
    declared_streams: set[str] = set()
    for scope in graph.scopes:
        if scope.kind == "global":
            has_global = True
            continue
        key = scope.stream_key
        if key is None or key not in streams:
            return unavailable(
                "scope",
                "a stream scope must name an assembled (VenueId, account) stream",
                scope=scope.token,
                failure_id="compose.risk_population.declared_scopes",
            )
        if key in declared_streams:
            return invalid(
                "scope",
                "one declared stream scope per command stream",
                stream=key,
                failure_id="compose.risk_population.declared_scopes",
            )
        declared_streams.add(key)
    if streams and not has_global:
        missing = streams - declared_streams
        if missing:
            return unavailable(
                "scope",
                "every command stream is covered by a declared stream scope or "
                "the global scope",
                missing=sorted(missing),
                failure_id="compose.risk_population.declared_scopes",
            )
    return Ok(None)


def _check_netting_partitions(graph: RuntimeRiskGraph) -> Result[None]:
    by_account: dict[str, list[PopulationBindingRecord]] = {}
    for binding in graph.bindings:
        by_account.setdefault(binding.stream_key, []).append(binding)
    for account_key, rows in by_account.items():
        models = {row.position_model for row in rows}
        if len(models) != 1:
            return invalid(
                "position_model",
                "every binding on one account declares the same position model",
                account=account_key,
                models=sorted(models),
                failure_id="compose.risk_population.netting_partitions",
            )
        model = next(iter(models))
        declarations = tuple(
            AttributionDeclaration(
                binding_id=row.binding_id,
                instruments=row.instruments,
                attribution_instruments=row.attribution_instruments,
                shared_flatten_signature=row.shared_flatten_signature,
            )
            for row in rows
        )
        proved = prove_attribution_partition(
            account_key=account_key,
            position_model=model,
            declarations=declarations,
        )
        if is_refusal(proved):
            return proved
    return Ok(None)


def _check_one_bms_per_account_many_books(graph: RuntimeRiskGraph) -> Result[None]:
    account_to_bms: dict[str, str] = {}
    bms_to_account: dict[str, str] = {}
    for bms in graph.bms:
        account = f"{bms.venue_id}::{bms.account_id}"
        prior = account_to_bms.get(account)
        if prior is not None and prior != bms.bms_instance_id:
            return invalid(
                "bms",
                "one BMS instance per account; a second BMS on the same account "
                "is refused",
                account=account,
                existing=prior,
                extra=bms.bms_instance_id,
                failure_id="compose.risk_population.one_bms_per_account",
            )
        other = bms_to_account.get(bms.bms_instance_id)
        if other is not None and other != account:
            return invalid(
                "bms",
                "one BMS instance is not reused across accounts",
                bms_instance_id=bms.bms_instance_id,
                accounts=sorted({other, account}),
                failure_id="compose.risk_population.one_bms_per_account",
            )
        account_to_bms[account] = bms.bms_instance_id
        bms_to_account[bms.bms_instance_id] = account

    books_by_bms: dict[str, set[str]] = {}
    for book in graph.books:
        books_by_bms.setdefault(book.bms_instance_id, set()).add(book.book_instance_id)
        if book.bms_instance_id not in bms_to_account:
            return unavailable(
                "book",
                "a Book binds a BMS present in the assembled population",
                book_instance_id=book.book_instance_id,
                failure_id="compose.risk_population.one_bms_per_account",
            )

    for binding in graph.bindings:
        account = binding.stream_key
        expected = account_to_bms.get(account)
        if expected is None:
            return unavailable(
                "binding",
                "a binding's account must have an assembled BMS",
                binding_id=binding.binding_id,
                failure_id="compose.risk_population.one_bms_per_account",
            )
        if binding.bms_instance_id != expected:
            return invalid(
                "binding",
                "one BMS per account serves many Books; a binding may not name "
                "a second BMS on that account",
                binding_id=binding.binding_id,
                account=account,
                expected=expected,
                given=binding.bms_instance_id,
                failure_id="compose.risk_population.one_bms_per_account",
            )
    return Ok(None)


def _check_one_book_per_bot(graph: RuntimeRiskGraph) -> Result[None]:
    bot_to_book: dict[str, str] = {}
    for seat in graph.seats:
        prior = bot_to_book.get(seat.bot_id)
        if prior is not None and prior != seat.book_instance_id:
            return invalid(
                "seat",
                "a Bot binds exactly one Book; two Books for one bot refuse "
                "the assembled population",
                bot_id=seat.bot_id,
                books=sorted({prior, seat.book_instance_id}),
                failure_id="compose.risk_population.one_book_per_bot",
            )
        bot_to_book[seat.bot_id] = seat.book_instance_id
    return Ok(None)


def _check_one_active_paper_target(graph: RuntimeRiskGraph) -> Result[None]:
    binding_ids = {row.binding_id: row for row in graph.bindings}
    seen: dict[str, PairedTargetRecord] = {}
    for target in graph.paired_targets:
        live = binding_ids.get(target.live_binding_id)
        if live is None:
            return unavailable(
                "paired_target",
                "a paper target must cite an assembled live binding",
                live_binding_id=target.live_binding_id,
                failure_id="compose.risk_population.one_active_paper_target",
            )
        if target.live_binding_id in seen:
            return invalid(
                "paired_target",
                "one active paper-routing target exists per binding; two "
                "destinations is how an order fires twice",
                live_binding_id=target.live_binding_id,
                failure_id="compose.risk_population.one_active_paper_target",
            )
        if target.paper_role is not NODE_PAPER_ACCOUNT_ROLE:
            return policy(
                "paper_role",
                "V1 node paper routing uses role demo only",
                given=target.paper_role.value,
                required=NODE_PAPER_ACCOUNT_ROLE.value,
                failure_id="compose.risk_population.one_active_paper_target",
            )
        if target.paper_bms_instance_id == live.bms_instance_id:
            return invalid(
                "paper_bms_instance_id",
                "the paired demo target carries its own BMS, never the live BMS",
                live_binding_id=target.live_binding_id,
                failure_id="compose.risk_population.one_active_paper_target",
            )
        seen[target.live_binding_id] = target
    return Ok(None)


def _check_roster_alignment(graph: RuntimeRiskGraph) -> Result[None]:
    if graph.roster is None:
        return Ok(None)
    roster_keys = {key.token for key in graph.roster.binding_keys}
    for binding in graph.bindings:
        token = (
            f"{binding.book_instance_id}|{binding.bms_instance_id}|"
            f"{binding.venue_id}:{binding.account_id}|{binding.world.value}"
        )
        if token not in roster_keys:
            return invalid(
                "roster",
                "every assembled binding must appear on the sealed roster",
                binding_id=binding.binding_id,
                failure_id="compose.risk_population.cardinalities",
            )
    graph_tokens = {
        (
            f"{binding.book_instance_id}|{binding.bms_instance_id}|"
            f"{binding.venue_id}:{binding.account_id}|{binding.world.value}"
        )
        for binding in graph.bindings
    }
    extra = roster_keys - graph_tokens
    if extra:
        return invalid(
            "roster",
            "every roster Book binding is present in the assembled risk graph",
            missing=sorted(extra),
            failure_id="compose.risk_population.cardinalities",
        )
    return Ok(None)
