"""Story 10.4 — the binding chain, identity trinity, and bind-time check (COMP-QMF-RISK).

A **Book binding record** is the dated, append-only deployment that couples a Book
instance to a BMS instance on one account at one venue (AD-29; DEC-0143, DEC-0158):

* the risk domain is the **binding tuple** ``(BookInstanceId, BmsInstanceId, VenueId,
  AccountId, world)`` — aligned with AD-27's ``(VenueId, account)`` command stream and
  never coarser, so a protective action never arbitrates across streams and one venue's
  ``UNKNOWN`` never freezes another. ``role`` is deliberately **not** in the tuple: it
  rides the per-intent execution-target record, so a paper excursion or a benched seat
  never re-mints the binding. A Bot binds exactly one Book, a Book binds exactly one BMS
  at a time (:class:`BookBindingLog` enforces it — re-binding mints a new record with a
  ``supersedes`` edge), and one BMS per account serves many Books (AC1);
* the **identity trinity** is minted apart: a **Book version** is the CT-22 template
  ``fp1`` (:class:`~qmf.risk.templates.BookDefinition.fingerprint`); a **Book instance**
  is an operator-minted deployment record (:class:`BookInstance`) carrying an opaque
  :class:`BookInstanceId`; and a **binding epoch** is the binding record's own
  fingerprint (:meth:`BookBindingRecord.fingerprint`) — populations cite fingerprints,
  never intervals. A binding record fingerprinting equal to an existing one is an
  ``invalid input`` refusal, never a silent idempotent accept (AC2). ``BmsInstanceId``
  is **content-derived** ``fp1(BMS definition fingerprint, AccountId, VenueId, world)``
  (:meth:`BmsInstanceId.derive`);
* every binding carries a mandatory, complete per-counter **state_carry** declaration
  (:class:`StateCarry`: ``ledger``, ``cycle``, ``budget``, ``bench_counter``,
  ``exposure`` — each ``carry | reset``); ``carry`` is legal only under an accompanying
  human-signed ``carries-ledger`` edge (:class:`SignedLedgerEdge`), while a
  ``continues-performance`` edge (:class:`ContinuesPerformanceEdge`) asserts a track
  record and moves no money — neither edge is inferred from the other (AC3);
* the **bind-time capability check** (:func:`bind_time_capability_check`) resolves the
  fixed list against CT-18's declaration and the venue-observation profile
  (:class:`VenueBindingProfile`) — required venue capabilities, settlement currency
  matching the Book's ``accounting_currency``, the shared-flatten signature where
  netted, a present SQS baseline for every sensor the Book's doors read, a live-path
  rung baseline, and a non-contradicting control-rank table — and any shortfall refuses
  at **bind time, never at trade time** (AC4). A settlement currency not matching the
  Book's ``accounting_currency`` (non-USD in V1) is a ``policy rejection`` — no rate
  source is ratified and a silent conversion is the one error no report shows (AC5). A
  second Book on a netting account whose live bindings may trade an overlapping
  instrument set is an ``unsupported capability`` refusal unless the operator signs the
  shared-flatten limitation, an identity field of the binding; one Book per netted
  account is the confirmed default (AC6).

qmf-risk imports **only** ``qmf-core`` (default-deny, L30/DEC-0120): the CT-18 venue
capability declaration and venue-observation profile are qmf-venue artifacts, so this
module consumes them through :class:`VenueBindingProfile` — the bind-time projection the
composition root builds from CT-18, never a redefinition of it. Nothing imports
``qmf.risk``. Ratified ``defined-unwired`` surface: no live binding, order, mode
transition, or flatten is authorized by this code — records reach ``qmf-registry`` only
through the composition root under the injected-sink pattern (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core import (
    Fingerprint,
    Instant,
    Ok,
    Result,
    TypedRefusal,
    VenueId,
    World,
    fingerprint,
    is_refusal,
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
from qmf.risk.control_rank import ControlActionKind, ControlRankTable
from qmf.risk.numeraire import validate_accounting_currency

__all__ = [
    "STATE_CARRY_COUNTERS",
    "BindingLineageEdgeKind",
    "BindingState",
    "BmsInstanceId",
    "BookBindingLog",
    "BookBindingRecord",
    "BookBindingRequirements",
    "BookInstance",
    "BookInstanceId",
    "CapabilityCheckResult",
    "ContinuesPerformanceEdge",
    "PairingRecord",
    "PositionModel",
    "SignedLedgerEdge",
    "StateCarry",
    "StateCarryChoice",
    "StateCarryCounter",
    "VenueBindingProfile",
    "bind_time_capability_check",
    "check_rank_table_non_contradiction",
]

# This module's own contract format version stamped into fp1 identity content; its
# meaning never mutates — an incompatible change mints the next version (L15).
_BINDING_FORMAT_VERSION = 1


# --- vocabularies ------------------------------------------------------------


class PositionModel(StrEnum):
    """The venue's per-account position model, read at bind time (CT-18; DEC-0143).

    ``NETTING`` — the venue holds one position per instrument at account level, so a
    Book-scoped flatten mechanically closes another Book's exposure. ``HEDGING`` — the
    venue holds positions per binding. Read from the venue-observation profile before
    the shared-flatten check (AC6).
    """

    NETTING = "netting"
    HEDGING = "hedging"


class StateCarryChoice(StrEnum):
    """What a per-counter state carries across a new binding epoch (AD-29; DEC-0143).

    ``CARRY`` — the counter's running state crosses the new binding, legal **only**
    under an accompanying human-signed ``carries-ledger`` edge. ``RESET`` — the counter
    starts fresh at the new epoch. What carries is **declared, never inferred** (AC3).
    """

    CARRY = "carry"
    RESET = "reset"


class StateCarryCounter(StrEnum):
    """The five per-counter carry declarations every binding must make (AD-29; DEC-0143).

    Each of ``ledger``, ``cycle``, ``budget``, ``bench_counter``, and ``exposure``
    carries exactly one :class:`StateCarryChoice`; the declaration is mandatory and
    complete — an absent or partial declaration is ``invalid input`` (AC3).
    """

    LEDGER = "ledger"
    CYCLE = "cycle"
    BUDGET = "budget"
    BENCH_COUNTER = "bench_counter"
    EXPOSURE = "exposure"


# The five counters in canonical order — every state_carry declaration is complete
# over exactly this set (DEC-0143).
STATE_CARRY_COUNTERS: Final[tuple[StateCarryCounter, ...]] = (
    StateCarryCounter.LEDGER,
    StateCarryCounter.CYCLE,
    StateCarryCounter.BUDGET,
    StateCarryCounter.BENCH_COUNTER,
    StateCarryCounter.EXPOSURE,
)


class BindingLineageEdgeKind(StrEnum):
    """The lineage edge kinds a binding names (CT-07; DEC-0143, DEC-0158).

    ``CARRIES_LEDGER`` — a human-signed edge that **moves money** and gates any
    ``carry`` counter. ``CONTINUES_PERFORMANCE`` — asserts a track record and **moves no
    money**. ``SUPERSEDES`` — the prior binding a re-bind replaces (linear, dated).
    Neither the carries-ledger nor the continues-performance edge is inferred from the
    other (AC3).
    """

    CARRIES_LEDGER = "carries-ledger"
    CONTINUES_PERFORMANCE = "continues-performance"
    SUPERSEDES = "supersedes"


class BindingState(StrEnum):
    """The binding-state vocabulary, enumerated apart (CT-28; DEC-0150, DEC-0149).

    A binding is ``live``, ``paper``, or ``stood-down`` — the *current* state is a
    read-time fold under AD-36's fold contract, **not a stored mutable field on the
    record**. It is one of three vocabularies never interchanged: binding state here,
    Book mode ``LIVE | PAPER`` (CT-24), and seat state ``active | benched``
    (CT-29/AD-41). This enum exists so the vocabulary is nameable; the fold itself is
    node/later-story territory.
    """

    LIVE = "live"
    PAPER = "paper"
    STOOD_DOWN = "stood-down"


# --- the identity trinity ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class BookInstanceId:
    """An opaque, operator-minted Book-instance token (AD-29; DEC-0143).

    Distinct from a content-derived ``BmsInstanceId``: two copies of one Book version on
    one account are distinct **by mint**, so the id is operator-supplied and opaque, and
    two instances never merge. Stored verbatim, never parsed.
    """

    value: str

    @classmethod
    def try_create(cls, value: object) -> Result[BookInstanceId]:
        """Validate and build a :class:`BookInstanceId`, value-or-refusal."""
        token = clean_str(value)
        if token is None:
            return invalid(
                "value",
                "a BookInstanceId is a non-empty opaque operator-minted token; two copies of "
                "one Book version on one account are distinct by mint",
                given=repr(value),
            )
        return Ok(cls(token))


@dataclass(frozen=True, slots=True)
class BookInstance:
    """An operator-minted Book-instance deployment record (AD-29; DEC-0143).

    The **Book instance** leg of the identity trinity: version fingerprint + ``AccountId``
    + ``VenueId`` + ``world`` + the operator's mint occurrence + a creation sequence,
    carrying an opaque :class:`BookInstanceId`. Two copies of one version on one account
    differ by ``(mint_occurrence, creation_sequence)`` and by their distinct opaque ids,
    and are never merged. Distinct from a Book *version* (the CT-22 template ``fp1``).
    """

    instance_id: BookInstanceId
    book_definition_fingerprint: Fingerprint
    account_id: str
    venue_id: VenueId
    world: World
    mint_occurrence: str
    creation_sequence: int

    @classmethod
    def try_create(
        cls,
        instance_id: object,
        book_definition_fingerprint: object,
        account_id: object,
        venue_id: object,
        world: object,
        mint_occurrence: object,
        creation_sequence: object,
    ) -> Result[BookInstance]:
        """Validate and build a :class:`BookInstance`, value-or-refusal.

        The ``instance_id`` is an operator-minted :class:`BookInstanceId`; the
        ``book_definition_fingerprint`` is the CT-22 Book VERSION ``fp1``; ``account_id``
        and ``mint_occurrence`` are non-blank tokens; ``venue_id`` a :class:`~qmf.core.VenueId`;
        ``world`` a :class:`~qmf.core.World`; and ``creation_sequence`` a non-negative
        integer (a bool is not a sequence).
        """
        if not isinstance(instance_id, BookInstanceId):
            return invalid(
                "instance_id",
                "a Book instance carries an operator-minted BookInstanceId",
                given=repr(instance_id),
            )
        if not isinstance(book_definition_fingerprint, Fingerprint):
            return invalid(
                "book_definition_fingerprint",
                "a Book instance cites the CT-22 Book VERSION by fingerprint, never a version "
                "string",
                given=repr(book_definition_fingerprint),
            )
        account = clean_str(account_id)
        if account is None:
            return invalid(
                "account_id", "a Book instance names an account id", given=repr(account_id)
            )
        if not isinstance(venue_id, VenueId):
            return invalid("venue_id", "a Book instance names a VenueId", given=repr(venue_id))
        resolved_world = coerce_enum(World, world)
        if resolved_world is None:
            return invalid(
                "world",
                "a Book instance declares its world (live on the live path)",
                given=repr(world),
                allowed=[member.value for member in World],
            )
        occurrence = clean_str(mint_occurrence)
        if occurrence is None:
            return invalid(
                "mint_occurrence",
                "a Book instance records the operator's mint occurrence",
                given=repr(mint_occurrence),
            )
        if isinstance(creation_sequence, bool) or not isinstance(creation_sequence, int):
            return invalid(
                "creation_sequence",
                "a Book instance carries an integer creation sequence",
                given=repr(creation_sequence),
            )
        if creation_sequence < 0:
            return invalid(
                "creation_sequence",
                "a creation sequence is a non-negative integer",
                given=repr(creation_sequence),
            )
        return Ok(
            cls(
                instance_id=instance_id,
                book_definition_fingerprint=book_definition_fingerprint,
                account_id=account,
                venue_id=venue_id,
                world=resolved_world,
                mint_occurrence=occurrence,
                creation_sequence=creation_sequence,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the deployment record."""
        return {
            "class": "book-instance",
            "instance_id": self.instance_id.value,
            "book_definition_fingerprint": self.book_definition_fingerprint.value,
            "account_id": self.account_id,
            "venue_id": self.venue_id.value,
            "world": self.world.value,
            "mint_occurrence": self.mint_occurrence,
            "creation_sequence": self.creation_sequence,
            "format_version": _BINDING_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class BmsInstanceId:
    """A content-derived BMS-instance token — ``fp1(bms fp, account, venue, world)``.

    Unlike an operator-minted :class:`BookInstanceId`, a ``BmsInstanceId`` is **content
    -derived** (:meth:`derive`): a BMS re-version mints a new id for every Book bound to
    it, and the operator can see it coming. Stored as the ``fp1`` string it derives to.
    """

    value: str

    @classmethod
    def derive(
        cls,
        bms_definition_fingerprint: object,
        account_id: object,
        venue_id: object,
        world: object,
    ) -> Result[BmsInstanceId]:
        """Derive the content ``fp1(BMS definition fingerprint, AccountId, VenueId, world)``.

        The BMS definition fingerprint is the CT-27 BMS VERSION ``fp1``; the rest are the
        account, venue, and world the instance deploys on. Any malformed part is
        ``invalid input``; the derived id is the ``fp1`` over the canonical content.
        """
        if not isinstance(bms_definition_fingerprint, Fingerprint):
            return invalid(
                "bms_definition_fingerprint",
                "a BmsInstanceId derives from the CT-27 BMS VERSION fingerprint",
                given=repr(bms_definition_fingerprint),
            )
        account = clean_str(account_id)
        if account is None:
            return invalid(
                "account_id", "a BmsInstanceId derives from an account id", given=repr(account_id)
            )
        if not isinstance(venue_id, VenueId):
            return invalid(
                "venue_id", "a BmsInstanceId derives from a VenueId", given=repr(venue_id)
            )
        resolved_world = coerce_enum(World, world)
        if resolved_world is None:
            return invalid(
                "world",
                "a BmsInstanceId derives from the deployment world",
                given=repr(world),
                allowed=[member.value for member in World],
            )
        derived = fingerprint(
            {
                "class": "bms-instance-id",
                "bms_definition_fingerprint": bms_definition_fingerprint.value,
                "account_id": account,
                "venue_id": venue_id.value,
                "world": resolved_world.value,
                "format_version": _BINDING_FORMAT_VERSION,
            }
        )
        if is_refusal(derived):
            return derived
        return Ok(cls(derived.value.value))


# --- state_carry and the lineage edges ---------------------------------------


@dataclass(frozen=True, slots=True)
class StateCarry:
    """The mandatory, complete per-counter carry declaration (AD-29; DEC-0143, DEC-0158).

    A declaration over **all five** counters (:data:`STATE_CARRY_COUNTERS`), each a
    :class:`StateCarryChoice`. Absent or partial is ``invalid input``. A ``carry`` on any
    counter is legal only where the binding carries a human-signed ``carries-ledger``
    edge (enforced by :meth:`BookBindingRecord.try_create`), so what carries is declared,
    never inferred.
    """

    per_counter: Mapping[StateCarryCounter, StateCarryChoice]

    def __post_init__(self) -> None:
        object.__setattr__(self, "per_counter", MappingProxyType(dict(self.per_counter)))

    @classmethod
    def try_create(cls, per_counter: object) -> Result[StateCarry]:
        """Validate and build a :class:`StateCarry` over exactly the five counters.

        ``per_counter`` is a mapping of :class:`StateCarryCounter` (or its string name)
        to :class:`StateCarryChoice` (or ``carry``/``reset``). Every counter must be
        present exactly once; a missing, unknown, or duplicate counter, or an
        unrecognised choice, is ``invalid input``.
        """
        if not isinstance(per_counter, Mapping):
            return invalid(
                "per_counter",
                "state_carry is a per-counter mapping of carry|reset over the five counters",
                given=type_name(per_counter),
            )
        source = cast("Mapping[object, object]", per_counter)
        resolved: dict[StateCarryCounter, StateCarryChoice] = {}
        for raw_counter, raw_choice in source.items():
            counter = coerce_enum(StateCarryCounter, raw_counter)
            if counter is None:
                return invalid(
                    "per_counter",
                    "an unknown state_carry counter",
                    given=repr(raw_counter),
                    allowed=[member.value for member in STATE_CARRY_COUNTERS],
                )
            choice = coerce_enum(StateCarryChoice, raw_choice)
            if choice is None:
                return invalid(
                    "per_counter",
                    "a counter's carry declaration is carry|reset",
                    counter=counter.value,
                    given=repr(raw_choice),
                )
            resolved[counter] = choice
        missing = [c.value for c in STATE_CARRY_COUNTERS if c not in resolved]
        if missing:
            return invalid(
                "per_counter",
                "the state_carry declaration is mandatory and complete over all five counters",
                missing=missing,
            )
        return Ok(cls(per_counter=resolved))

    def choice_for(self, counter: StateCarryCounter) -> StateCarryChoice:
        """The declared choice for one counter (present by construction)."""
        return self.per_counter[counter]

    def carried_counters(self) -> frozenset[StateCarryCounter]:
        """The counters declared ``carry`` — non-empty implies a signed edge is required."""
        return frozenset(
            c for c, choice in self.per_counter.items() if choice is StateCarryChoice.CARRY
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — counters in canonical order."""
        return {
            "class": "state-carry",
            "per_counter": {c.value: self.per_counter[c].value for c in STATE_CARRY_COUNTERS},
            "format_version": _BINDING_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class SignedLedgerEdge:
    """The human-signed ``carries-ledger`` edge — moves money, gates any carry (DEC-0158).

    Carries the ``signer_identity``, the injected ``signed_at`` :class:`~qmf.core.Instant`
    (never a clock read below the composition root), and the prior binding whose ledger
    carries. Its presence is what makes a ``carry`` counter legal; it asserts nothing
    about comparability, and is never inferred from a ``continues-performance`` edge.
    """

    signer_identity: str
    signed_at: Instant
    from_binding_fingerprint: Fingerprint

    @classmethod
    def try_create(
        cls, signer_identity: object, signed_at: object, from_binding_fingerprint: object
    ) -> Result[SignedLedgerEdge]:
        """Validate and build a :class:`SignedLedgerEdge`, value-or-refusal."""
        signer = clean_str(signer_identity)
        if signer is None:
            return invalid(
                "signer_identity",
                "a carries-ledger edge is human-signed; the signer identity is a non-empty token",
                given=repr(signer_identity),
            )
        if not isinstance(signed_at, Instant):
            return invalid(
                "signed_at",
                "a carries-ledger edge is dated with an injected Instant (never a clock read)",
                given=repr(signed_at),
            )
        if not isinstance(from_binding_fingerprint, Fingerprint):
            return invalid(
                "from_binding_fingerprint",
                "a carries-ledger edge names the prior binding whose ledger carries, by "
                "fingerprint",
                given=repr(from_binding_fingerprint),
            )
        return Ok(
            cls(
                signer_identity=signer,
                signed_at=signed_at,
                from_binding_fingerprint=from_binding_fingerprint,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the signed edge."""
        return {
            "class": "binding-lineage-edge",
            "kind": BindingLineageEdgeKind.CARRIES_LEDGER.value,
            "signer_identity": self.signer_identity,
            "signed_at": self.signed_at.fp1_identity(),
            "from_binding_fingerprint": self.from_binding_fingerprint.value,
            "format_version": _BINDING_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ContinuesPerformanceEdge:
    """The ``continues-performance`` edge — asserts a track record, moves no money.

    Carries the prior binding whose track record continues. It asserts comparability and
    moves no money, so it never gates a ``carry`` and is never inferred from a
    ``carries-ledger`` edge — the two are independent (AC3; DEC-0158).
    """

    from_binding_fingerprint: Fingerprint

    @classmethod
    def try_create(cls, from_binding_fingerprint: object) -> Result[ContinuesPerformanceEdge]:
        """Validate and build a :class:`ContinuesPerformanceEdge`, value-or-refusal."""
        if not isinstance(from_binding_fingerprint, Fingerprint):
            return invalid(
                "from_binding_fingerprint",
                "a continues-performance edge names the prior binding whose track record "
                "continues, by fingerprint",
                given=repr(from_binding_fingerprint),
            )
        return Ok(cls(from_binding_fingerprint=from_binding_fingerprint))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the edge."""
        return {
            "class": "binding-lineage-edge",
            "kind": BindingLineageEdgeKind.CONTINUES_PERFORMANCE.value,
            "from_binding_fingerprint": self.from_binding_fingerprint.value,
            "format_version": _BINDING_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class PairingRecord:
    """The typed link from a live BMS instance to its paired demo BMS instance (DEC-0149).

    So the pair is visible as one operational unit: the paper flip is an operator-ratified
    dated change of the Book→BMS binding, minting a new binding epoch, never a new Book.
    Carries the live and paired :class:`BmsInstanceId` values and the paired account id.
    """

    live_bms_instance_id: BmsInstanceId
    paired_bms_instance_id: BmsInstanceId
    paired_account_id: str

    @classmethod
    def try_create(
        cls,
        live_bms_instance_id: object,
        paired_bms_instance_id: object,
        paired_account_id: object,
    ) -> Result[PairingRecord]:
        """Validate and build a :class:`PairingRecord`, value-or-refusal."""
        if not isinstance(live_bms_instance_id, BmsInstanceId):
            return invalid(
                "live_bms_instance_id",
                "a pairing record links a live BmsInstanceId",
                given=repr(live_bms_instance_id),
            )
        if not isinstance(paired_bms_instance_id, BmsInstanceId):
            return invalid(
                "paired_bms_instance_id",
                "a pairing record links a paired BmsInstanceId",
                given=repr(paired_bms_instance_id),
            )
        account = clean_str(paired_account_id)
        if account is None:
            return invalid(
                "paired_account_id",
                "a pairing record names the paired demo account id",
                given=repr(paired_account_id),
            )
        return Ok(
            cls(
                live_bms_instance_id=live_bms_instance_id,
                paired_bms_instance_id=paired_bms_instance_id,
                paired_account_id=account,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for the pairing record."""
        return {
            "class": "binding-pairing-record",
            "live_bms_instance_id": self.live_bms_instance_id.value,
            "paired_bms_instance_id": self.paired_bms_instance_id.value,
            "paired_account_id": self.paired_account_id,
            "format_version": _BINDING_FORMAT_VERSION,
        }


# --- the bind-time capability check ------------------------------------------


def _coerce_token_set(field: str, value: object) -> frozenset[str] | TypedRefusal:
    """Resolve a collection of non-blank opaque tokens to a frozenset, or a refusal.

    An empty collection is legal (an empty set). A non-collection, or an item that is not
    a non-blank string, is ``invalid input``.
    """
    given = type_name(value)
    if isinstance(value, (str, bytes, Mapping)) or not isinstance(value, Iterable):
        return invalid(field, "a set of tokens is a collection of non-empty strings", given=given)
    resolved: set[str] = set()
    for item in cast("Iterable[object]", value):
        token = clean_str(item)
        if token is None:
            return invalid(field, "each token is a non-empty string", given=repr(item))
        resolved.add(token)
    return frozenset(resolved)


@dataclass(frozen=True, slots=True)
class VenueBindingProfile:
    """The bind-time projection of CT-18 the capability check consumes (CT-18; DEC-0143).

    Built at the composition root from the venue's **static capability declaration** and
    its per-``(VenueId, account)`` **venue-observation profile** — never a redefinition of
    CT-18 (qmf-risk imports only qmf-core). Carries the declared capability tokens the
    venue supports, the measured-at-connection ``position_model`` (``None`` = unmeasured),
    and the measured-at-connection ``settlement_currency`` (``None`` = unmeasured); an
    unmeasured field the check needs is an ``unavailable dependency`` at bind time.
    """

    declared_capabilities: frozenset[str]
    position_model: PositionModel | None
    settlement_currency: str | None

    @classmethod
    def try_create(
        cls,
        declared_capabilities: object,
        position_model: object,
        settlement_currency: object,
    ) -> Result[VenueBindingProfile]:
        """Validate and build a :class:`VenueBindingProfile`, value-or-refusal.

        ``declared_capabilities`` is a collection of non-blank capability tokens (possibly
        empty); ``position_model`` is a :class:`PositionModel` or ``None`` (unmeasured);
        ``settlement_currency`` is a non-blank currency tag or ``None`` (unmeasured). A
        blank settlement currency or an unrecognised position model is ``invalid input``
        — distinct from the honest ``None`` of an unmeasured fact.
        """
        capabilities = _coerce_token_set("declared_capabilities", declared_capabilities)
        if isinstance(capabilities, TypedRefusal):
            return capabilities
        resolved_model: PositionModel | None
        if position_model is None:
            resolved_model = None
        else:
            resolved_model = coerce_enum(PositionModel, position_model)
            if resolved_model is None:
                return invalid(
                    "position_model",
                    "the position model is netting|hedging, or None when unmeasured",
                    given=repr(position_model),
                )
        resolved_currency: str | None
        if settlement_currency is None:
            resolved_currency = None
        else:
            resolved_currency = clean_str(settlement_currency)
            if resolved_currency is None:
                return invalid(
                    "settlement_currency",
                    "the settlement currency is a non-empty tag, or None when unmeasured",
                    given=repr(settlement_currency),
                )
        return Ok(
            cls(
                declared_capabilities=capabilities,
                position_model=resolved_model,
                settlement_currency=resolved_currency,
            )
        )


@dataclass(frozen=True, slots=True)
class BookBindingRequirements:
    """What the Book requires at bind, derived from its CT-22 definition (DEC-0143, DEC-0144).

    Built at the composition root from the Book definition: the ``accounting_currency``
    (USD in V1), the ``required_venue_capabilities`` the venue must declare, the sensor
    ids whose SQS baselines the Book's doors read, and the Book's ``control_policy`` ranks
    (which must not contradict the BMS rank table). The bind-time check resolves each
    against the venue profile and the deployment facts (AC4).
    """

    accounting_currency: str
    required_venue_capabilities: frozenset[str]
    required_sensor_ids: frozenset[str]
    control_policy_ranks: Mapping[ControlActionKind, int]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "control_policy_ranks", MappingProxyType(dict(self.control_policy_ranks))
        )

    @classmethod
    def try_create(
        cls,
        accounting_currency: object,
        required_venue_capabilities: object,
        required_sensor_ids: object,
        control_policy_ranks: object,
    ) -> Result[BookBindingRequirements]:
        """Validate and build a :class:`BookBindingRequirements`, value-or-refusal.

        ``accounting_currency`` runs the numeraire law (USD in V1, else ``policy
        rejection``); the two token sets are collections of non-blank tokens (possibly
        empty); ``control_policy_ranks`` is a mapping of :class:`ControlActionKind` to a
        non-negative integer rank (possibly empty — a Book need not declare ranks).
        """
        currency = validate_accounting_currency(accounting_currency)
        if is_refusal(currency):
            return currency
        capabilities = _coerce_token_set("required_venue_capabilities", required_venue_capabilities)
        if isinstance(capabilities, TypedRefusal):
            return capabilities
        sensors = _coerce_token_set("required_sensor_ids", required_sensor_ids)
        if isinstance(sensors, TypedRefusal):
            return sensors
        ranks = _coerce_control_policy_ranks(control_policy_ranks)
        if isinstance(ranks, TypedRefusal):
            return ranks
        return Ok(
            cls(
                accounting_currency=currency.value,
                required_venue_capabilities=capabilities,
                required_sensor_ids=sensors,
                control_policy_ranks=ranks,
            )
        )


def _coerce_control_policy_ranks(
    value: object,
) -> dict[ControlActionKind, int] | TypedRefusal:
    """Resolve a Book control_policy rank mapping, or a refusal (empty is legal)."""
    if not isinstance(value, Mapping):
        return invalid(
            "control_policy_ranks",
            "a Book control_policy declares a mapping of control-action kind to rank",
            given=type_name(value),
        )
    source = cast("Mapping[object, object]", value)
    resolved: dict[ControlActionKind, int] = {}
    for raw_kind, raw_rank in source.items():
        kind = coerce_enum(ControlActionKind, raw_kind)
        if kind is None:
            return invalid(
                "control_policy_ranks",
                "a control_policy rank names a control-action kind from the closed CT-30 set",
                given=repr(raw_kind),
            )
        if isinstance(raw_rank, bool) or not isinstance(raw_rank, int):
            return invalid(
                "control_policy_ranks",
                "a rank is an integer",
                kind=kind.value,
                given=repr(raw_rank),
            )
        if raw_rank < 0:
            return invalid(
                "control_policy_ranks",
                "a rank is a non-negative integer",
                kind=kind.value,
                given=repr(raw_rank),
            )
        resolved[kind] = raw_rank
    return resolved


def check_rank_table_non_contradiction(
    control_policy_ranks: object, bms_rank_table: object
) -> Result[None]:
    """The Book's control_policy must not contradict the BMS rank table (AD-37; DEC-0151).

    The rank table is BMS-declared, one per command stream; a Book whose ``control_policy``
    ranks a kind the BMS table omits, or ranks it differently, is a contradiction and an
    ``unsupported capability`` refusal at bind time. A Book that ranks nothing contradicts
    nothing. Accepts the raw ``control_policy_ranks`` mapping and a :class:`ControlRankTable`.
    """
    ranks = _coerce_control_policy_ranks(control_policy_ranks)
    if isinstance(ranks, TypedRefusal):
        return ranks
    if not isinstance(bms_rank_table, ControlRankTable):
        return invalid(
            "bms_rank_table",
            "the non-contradiction check reads a BMS-declared ControlRankTable",
            given=repr(bms_rank_table),
        )
    bms_ranks = bms_rank_table.ranks_by_kind()
    for kind, rank in ranks.items():
        bms_rank = bms_ranks.get(kind)
        if bms_rank is None:
            return unsupported(
                "control_policy_ranks",
                "the Book's control_policy ranks a control-action kind absent from the "
                "BMS-declared rank table; the table is one per command stream",
                control_action_kind=kind.value,
            )
        if bms_rank != rank:
            return unsupported(
                "control_policy_ranks",
                "the Book's control_policy rank contradicts the BMS-declared rank table; a "
                "contradiction refuses at bind time",
                control_action_kind=kind.value,
                book_rank=rank,
                bms_rank=bms_rank,
            )
    return Ok(None)


@dataclass(frozen=True, slots=True)
class CapabilityCheckResult:
    """The recorded outcome of the bind-time capability check (CT-28; DEC-0143).

    An identity field of the binding: it records the resolved position model, the matched
    settlement currency, the satisfied capabilities, the applied shared-flatten signature
    (present where a netted account with an overlapping live instrument set required it),
    the satisfied sensor baselines, the live-path rung baseline, and that the rank table
    was not contradicted. Constructing one means the fixed list was satisfied — a shortfall
    returns a refusal instead, at bind time and never at trade time.
    """

    position_model: PositionModel
    settlement_currency: str
    satisfied_capabilities: frozenset[str]
    shared_flatten_signature: str | None
    satisfied_sensor_baselines: frozenset[str]
    live_path_rung_baseline_present: bool
    rank_table_non_contradicted: bool

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — sets emitted sorted."""
        content: dict[str, object] = {
            "class": "capability-check-result",
            "position_model": self.position_model.value,
            "settlement_currency": self.settlement_currency,
            "satisfied_capabilities": sorted(self.satisfied_capabilities),
            "satisfied_sensor_baselines": sorted(self.satisfied_sensor_baselines),
            "live_path_rung_baseline_present": self.live_path_rung_baseline_present,
            "rank_table_non_contradicted": self.rank_table_non_contradicted,
            "format_version": _BINDING_FORMAT_VERSION,
        }
        if self.shared_flatten_signature is not None:
            content["shared_flatten_signature"] = self.shared_flatten_signature
        return content


def bind_time_capability_check(
    *,
    requirements: object,
    profile: object,
    bms_rank_table: object,
    sensor_baselines_present: object,
    live_path_rung_baseline_present: object,
    is_second_book_on_account: object,
    overlapping_instrument_set: object,
    shared_flatten_signature: object = None,
) -> Result[CapabilityCheckResult]:
    """Resolve the fixed bind-time capability list; any shortfall refuses (AC4, AC5, AC6).

    The list, in order, against CT-18's declaration and the venue-observation profile:

    1. **required venue capabilities** — the Book's ``required_venue_capabilities`` are a
       subset of the venue's declared capabilities, else ``unsupported capability``;
    2. **settlement currency** — the venue's measured settlement currency matches the
       Book's ``accounting_currency`` (USD in V1); unmeasured is ``unavailable dependency``
       and a mismatch (non-USD) is a ``policy rejection`` — no rate source is ratified and
       a silent conversion is the one error no report shows (AC5);
    3. **shared-flatten signature where netted** — on a ``netting`` account where this is a
       second Book whose live bindings may trade an overlapping instrument set, the
       operator's shared-flatten signature must be present, else ``unsupported capability``
       (one Book per netted account is the default); an unmeasured position model is
       ``unavailable dependency`` (AC6);
    4. **SQS baseline present** — a present baseline for every sensor the Book's doors read,
       else ``unavailable dependency``;
    5. **live-path rung baseline** — recorded on this deployment, else ``unavailable
       dependency``;
    6. **non-contradicted rank table** — the Book's ``control_policy`` does not contradict
       the BMS-declared rank table, else ``unsupported capability``.

    Every shortfall is returned at **bind time, never at trade time**. On success a
    :class:`CapabilityCheckResult` records the satisfied list — an identity field of the
    binding.
    """
    if not isinstance(requirements, BookBindingRequirements):
        return invalid(
            "requirements",
            "the bind-time check reads a validated BookBindingRequirements",
            given=repr(requirements),
        )
    if not isinstance(profile, VenueBindingProfile):
        return invalid(
            "profile",
            "the bind-time check reads a VenueBindingProfile (the CT-18 projection)",
            given=repr(profile),
        )
    if not isinstance(bms_rank_table, ControlRankTable):
        return invalid(
            "bms_rank_table",
            "the bind-time check reads the BMS-declared ControlRankTable",
            given=repr(bms_rank_table),
        )
    for name, flag in (
        ("live_path_rung_baseline_present", live_path_rung_baseline_present),
        ("is_second_book_on_account", is_second_book_on_account),
        ("overlapping_instrument_set", overlapping_instrument_set),
    ):
        if not isinstance(flag, bool):
            return invalid(name, "a bind-time flag is a bool", given=repr(flag))

    # 1. required venue capabilities
    missing_caps = requirements.required_venue_capabilities - profile.declared_capabilities
    if missing_caps:
        return unsupported(
            "required_venue_capabilities",
            "the venue does not declare a capability the Book requires; the shortfall refuses "
            "at bind time, never at trade time",
            missing=sorted(missing_caps),
        )

    # 2. settlement currency matches the Book's accounting_currency
    settlement_currency = profile.settlement_currency
    if settlement_currency is None:
        return unavailable(
            "settlement_currency",
            "the account settlement currency is not measured yet; it rides the venue-observation "
            "profile and refuses at bind time until measured",
        )
    if settlement_currency != requirements.accounting_currency:
        return policy(
            "settlement_currency",
            "the account settlement currency does not match the Book's accounting_currency; no "
            "rate source is ratified and a silent conversion is the one error no report shows",
            settlement_currency=settlement_currency,
            accounting_currency=requirements.accounting_currency,
        )

    # 3. shared-flatten signature where netted (AC6)
    position_model = profile.position_model
    if position_model is None:
        return unavailable(
            "position_model",
            "the venue position model is not measured yet; the shared-flatten resolution needs "
            "it and refuses at bind time until measured",
        )
    resolved_signature = clean_str(shared_flatten_signature)
    netted_overlap = (
        position_model is PositionModel.NETTING
        and is_second_book_on_account
        and overlapping_instrument_set
    )
    if netted_overlap and resolved_signature is None:
        return unsupported(
            "shared_flatten_signature",
            "a second Book on a netting account whose live bindings may trade an overlapping "
            "instrument set needs the operator's signed shared-flatten limitation; one Book per "
            "netted account is the default",
        )

    # 4. SQS baseline present for every sensor the Book's doors read
    baselines = _coerce_token_set("sensor_baselines_present", sensor_baselines_present)
    if isinstance(baselines, TypedRefusal):
        return baselines
    missing_baselines = requirements.required_sensor_ids - baselines
    if missing_baselines:
        return unavailable(
            "sensor_baselines_present",
            "a live binding needs a present SQS baseline artifact for every sensor the Book's "
            "doors read; a missing baseline refuses at bind time",
            missing=sorted(missing_baselines),
        )

    # 5. live-path rung baseline recorded on this deployment
    if not live_path_rung_baseline_present:
        return unavailable(
            "live_path_rung_baseline_present",
            "a live binding needs a recorded live-path rung baseline on this deployment's "
            "declared (OS, CPU-class) tuple; its absence refuses at bind time",
        )

    # 6. the Book's control_policy does not contradict the BMS rank table
    non_contradiction = check_rank_table_non_contradiction(
        requirements.control_policy_ranks, bms_rank_table
    )
    if is_refusal(non_contradiction):
        return non_contradiction

    return Ok(
        CapabilityCheckResult(
            position_model=position_model,
            settlement_currency=settlement_currency,
            satisfied_capabilities=requirements.required_venue_capabilities,
            shared_flatten_signature=resolved_signature if netted_overlap else None,
            satisfied_sensor_baselines=requirements.required_sensor_ids,
            live_path_rung_baseline_present=True,
            rank_table_non_contradicted=True,
        )
    )


# --- the binding record ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class BookBindingRecord:
    """One dated, append-only Book binding record — the deployment (CT-28; DEC-0143).

    The risk domain is the tuple ``(BookInstanceId, BmsInstanceId, VenueId, AccountId,
    world)`` (:meth:`tuple_identity`), aligned with the ``(VenueId, account)`` command
    stream (:meth:`command_stream`). The record's own fingerprint (:meth:`fingerprint`) is
    the binding **epoch** cited by CT-32 populations and AD-41 folds. ``role`` is absent by
    construction — it rides the execution-target record. ``binding_state`` is a read-time
    fold, not a stored field. A ``carry`` counter is legal only with a
    :class:`SignedLedgerEdge` — enforced by :meth:`try_create`.
    """

    book_instance_id: BookInstanceId
    bms_instance_id: BmsInstanceId
    venue_id: VenueId
    account_id: str
    world: World
    book_definition_fingerprint: Fingerprint
    bms_definition_fingerprint: Fingerprint
    state_carry: StateCarry
    capability_check_result: CapabilityCheckResult
    shared_flatten_signature: str | None = None
    carries_ledger_edge: SignedLedgerEdge | None = None
    continues_performance_edge: ContinuesPerformanceEdge | None = None
    pairing_record: PairingRecord | None = None
    supersedes: Fingerprint | None = None

    @classmethod
    def try_create(
        cls,
        book_instance_id: object,
        bms_instance_id: object,
        venue_id: object,
        account_id: object,
        world: object,
        book_definition_fingerprint: object,
        bms_definition_fingerprint: object,
        state_carry: object,
        capability_check_result: object,
        *,
        carries_ledger_edge: object = None,
        continues_performance_edge: object = None,
        pairing_record: object = None,
        supersedes: object = None,
    ) -> Result[BookBindingRecord]:
        """Validate and build a :class:`BookBindingRecord`, value-or-refusal.

        Enforces the tuple types, the mandatory ``state_carry`` and passed
        ``capability_check_result``, and the **carry-requires-a-signed-edge** invariant: a
        ``carry`` on any counter without an accompanying :class:`SignedLedgerEdge` is
        ``invalid input``. The shared-flatten signature is taken from the capability-check
        result (it is applied there), so the record can never disagree with the check. The
        two lineage edges are independent — neither is inferred from the other.
        """
        if not isinstance(book_instance_id, BookInstanceId):
            return invalid(
                "book_instance_id",
                "the tuple carries a BookInstanceId",
                given=repr(book_instance_id),
            )
        if not isinstance(bms_instance_id, BmsInstanceId):
            return invalid(
                "bms_instance_id", "the tuple carries a BmsInstanceId", given=repr(bms_instance_id)
            )
        if not isinstance(venue_id, VenueId):
            return invalid("venue_id", "the tuple carries a VenueId", given=repr(venue_id))
        account = clean_str(account_id)
        if account is None:
            return invalid("account_id", "the tuple carries an account id", given=repr(account_id))
        resolved_world = coerce_enum(World, world)
        if resolved_world is None:
            return invalid(
                "world",
                "the tuple carries a world (live on the live path)",
                given=repr(world),
                allowed=[member.value for member in World],
            )
        if not isinstance(book_definition_fingerprint, Fingerprint):
            return invalid(
                "book_definition_fingerprint",
                "a binding cites the CT-22 Book VERSION by fingerprint",
                given=repr(book_definition_fingerprint),
            )
        if not isinstance(bms_definition_fingerprint, Fingerprint):
            return invalid(
                "bms_definition_fingerprint",
                "a binding cites the CT-27 BMS VERSION by fingerprint",
                given=repr(bms_definition_fingerprint),
            )
        if not isinstance(state_carry, StateCarry):
            return invalid(
                "state_carry",
                "a binding carries a mandatory, complete StateCarry declaration",
                given=repr(state_carry),
            )
        if not isinstance(capability_check_result, CapabilityCheckResult):
            return invalid(
                "capability_check_result",
                "a binding carries the recorded bind-time CapabilityCheckResult",
                given=repr(capability_check_result),
            )
        edge = _optional(carries_ledger_edge, SignedLedgerEdge, "carries_ledger_edge")
        if isinstance(edge, TypedRefusal):
            return edge
        continues = _optional(
            continues_performance_edge, ContinuesPerformanceEdge, "continues_performance_edge"
        )
        if isinstance(continues, TypedRefusal):
            return continues
        pairing = _optional(pairing_record, PairingRecord, "pairing_record")
        if isinstance(pairing, TypedRefusal):
            return pairing
        superseded = _optional(supersedes, Fingerprint, "supersedes")
        if isinstance(superseded, TypedRefusal):
            return superseded
        if state_carry.carried_counters() and edge is None:
            return invalid(
                "state_carry",
                "a carry counter is legal only under an accompanying human-signed carries-ledger "
                "edge; what carries is declared, never inferred, and never read off an edge's "
                "mere presence",
                carried=[
                    c.value for c in sorted(state_carry.carried_counters(), key=lambda k: k.value)
                ],
            )
        return Ok(
            cls(
                book_instance_id=book_instance_id,
                bms_instance_id=bms_instance_id,
                venue_id=venue_id,
                account_id=account,
                world=resolved_world,
                book_definition_fingerprint=book_definition_fingerprint,
                bms_definition_fingerprint=bms_definition_fingerprint,
                state_carry=state_carry,
                capability_check_result=capability_check_result,
                shared_flatten_signature=capability_check_result.shared_flatten_signature,
                carries_ledger_edge=edge,
                continues_performance_edge=continues,
                pairing_record=pairing,
                supersedes=superseded,
            )
        )

    def command_stream(self) -> tuple[VenueId, str]:
        """The ``(VenueId, account)`` command stream this binding aligns with, never coarser."""
        return (self.venue_id, self.account_id)

    def tuple_identity(self) -> dict[str, object]:
        """The binding TUPLE ``(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)``.

        The risk domain — never coarser than the command stream, and ``role`` deliberately
        absent (it rides the execution-target record). Distinct from the full-record
        fingerprint (the epoch).
        """
        return {
            "class": "book-binding-tuple",
            "book_instance_id": self.book_instance_id.value,
            "bms_instance_id": self.bms_instance_id.value,
            "venue_id": self.venue_id.value,
            "account_id": self.account_id,
            "world": self.world.value,
        }

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the full binding record.

        Optional edges, the pairing record, the shared-flatten signature, and the
        ``supersedes`` reference are included only when present (null is prohibited in
        identity content), so two records differing only by a present edge fingerprint
        apart.
        """
        content: dict[str, object] = {
            "class": "book-binding-record",
            "book_instance_id": self.book_instance_id.value,
            "bms_instance_id": self.bms_instance_id.value,
            "venue_id": self.venue_id.value,
            "account_id": self.account_id,
            "world": self.world.value,
            "book_definition_fingerprint": self.book_definition_fingerprint.value,
            "bms_definition_fingerprint": self.bms_definition_fingerprint.value,
            "state_carry": self.state_carry.fp1_identity(),
            "capability_check_result": self.capability_check_result.fp1_identity(),
            "format_version": _BINDING_FORMAT_VERSION,
        }
        if self.shared_flatten_signature is not None:
            content["shared_flatten_signature"] = self.shared_flatten_signature
        if self.carries_ledger_edge is not None:
            content["carries_ledger_edge"] = self.carries_ledger_edge.fp1_identity()
        if self.continues_performance_edge is not None:
            content["continues_performance_edge"] = self.continues_performance_edge.fp1_identity()
        if self.pairing_record is not None:
            content["pairing_record"] = self.pairing_record.fp1_identity()
        if self.supersedes is not None:
            content["supersedes"] = self.supersedes.value
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """The binding EPOCH — the ``fp1`` over the full canonical binding content (DEC-0143)."""
        return fingerprint(self.fp1_identity())


_OptionalT = TypeVar("_OptionalT")


def _optional(
    value: object, expected: type[_OptionalT], field: str
) -> _OptionalT | TypedRefusal | None:
    """Return ``None`` for an omitted optional, the value if it is ``expected``, else refuse."""
    if value is None:
        return None
    if not isinstance(value, expected):
        return invalid(
            field, f"an optional {field} is a {expected.__name__} when present", given=repr(value)
        )
    return value


# --- the append-only binding log (mint guard) --------------------------------


class BookBindingLog:
    """An append-only, in-memory guard over binding minting (CT-28; DEC-0143).

    A pure reference structure — **not** the platform's store; the governed binding
    records live in ``qmf-registry`` and reach it only through the composition root
    (DEC-0158). It enforces two ratified invariants at mint:

    * **epoch uniqueness (AC2):** a binding record fingerprinting equal to an existing one
      is an ``invalid input`` refusal, never AD-10's silent idempotent accept — that path
      is for byte-identical re-writes of the same work, not a second pot of money;
    * **one BMS at a time per Book instance (AC1):** a Book binds exactly one BMS at a
      time, so a second live binding for a Book instance must carry a ``supersedes`` edge
      naming that Book's current live binding — re-binding mints a new record that
      supersedes the prior; a concurrent second binding without it is refused.

    Many different Book instances binding one account share one BMS instance freely (one
    BMS per account serves many Books).
    """

    def __init__(self) -> None:
        self._by_fingerprint: dict[str, BookBindingRecord] = {}
        self._order: list[Fingerprint] = []
        self._superseded: set[str] = set()
        # BookInstanceId value -> the current live (non-superseded) binding fingerprint.
        self._live_by_book: dict[str, str] = {}

    def mint(self, record: object) -> Result[Fingerprint]:
        """Append a new binding record, enforcing epoch uniqueness and one-BMS-at-a-time.

        Returns the minted binding epoch (the record's fingerprint). An equal-fingerprint
        re-mint is ``invalid input`` (AC2); a dangling ``supersedes`` is ``unavailable
        dependency``; a ``supersedes`` naming another Book instance's binding, an already
        -superseded binding, or not the current live binding is ``invalid input``; and a
        second live binding for a Book instance without a ``supersedes`` edge is ``invalid
        input`` (AC1).
        """
        if not isinstance(record, BookBindingRecord):
            return invalid("record", "the log mints a BookBindingRecord", given=repr(record))
        epoch = record.fingerprint()
        if is_refusal(epoch):
            return epoch
        fp_value = epoch.value.value
        if fp_value in self._by_fingerprint:
            return invalid(
                "record",
                "a binding record fingerprinting equal to an existing one is refused, never a "
                "silent idempotent accept; two copies of one Book version on one account are "
                "distinct by mint and never merged",
                binding_fingerprint=fp_value,
            )
        book_key = record.book_instance_id.value
        if record.supersedes is not None:
            prior_value = record.supersedes.value
            prior = self._by_fingerprint.get(prior_value)
            if prior is None:
                return unavailable(
                    "supersedes",
                    "a superseding binding must name an existing prior binding; a supersedes edge "
                    "never dangles",
                    given=prior_value,
                )
            if prior.book_instance_id.value != book_key:
                return invalid(
                    "supersedes",
                    "a binding may supersede only the same Book instance's prior binding",
                    book_instance_id=book_key,
                    prior_book_instance_id=prior.book_instance_id.value,
                )
            if prior_value in self._superseded:
                return invalid(
                    "supersedes",
                    "the named prior binding is already superseded; the version graph is "
                    "append-only and a binding is superseded at most once",
                    given=prior_value,
                )
            if self._live_by_book.get(book_key) != prior_value:
                return invalid(
                    "supersedes",
                    "a re-bind must supersede the Book instance's current live binding",
                    given=prior_value,
                    current=self._live_by_book.get(book_key),
                )
        elif book_key in self._live_by_book:
            return invalid(
                "record",
                "a Book binds exactly one BMS at a time; a second live binding for a Book "
                "instance must supersede its current live binding (re-binding mints a supersedes "
                "edge)",
                book_instance_id=book_key,
                current=self._live_by_book[book_key],
            )
        self._by_fingerprint[fp_value] = record
        self._order.append(epoch.value)
        if record.supersedes is not None:
            self._superseded.add(record.supersedes.value)
        self._live_by_book[book_key] = fp_value
        return Ok(epoch.value)

    def is_present(self, fingerprint_value: object) -> bool:
        """True when this fingerprint names a minted binding record."""
        return (
            isinstance(fingerprint_value, Fingerprint)
            and fingerprint_value.value in self._by_fingerprint
        )

    def is_superseded(self, fingerprint_value: object) -> bool:
        """True when this binding has been superseded by a later re-bind."""
        return (
            isinstance(fingerprint_value, Fingerprint)
            and fingerprint_value.value in self._superseded
        )

    def live_binding_for(self, book_instance_id: object) -> Fingerprint | None:
        """The current live (non-superseded) binding for a Book instance, or ``None``."""
        if not isinstance(book_instance_id, BookInstanceId):
            return None
        fp_value = self._live_by_book.get(book_instance_id.value)
        if fp_value is None:
            return None
        return Fingerprint(value=fp_value)

    def bindings(self) -> tuple[Fingerprint, ...]:
        """Every minted binding epoch, in mint order (append-only)."""
        return tuple(self._order)
