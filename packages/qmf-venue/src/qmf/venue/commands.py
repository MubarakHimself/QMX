"""Five typed command kinds under the four-outcome law (Story 8.5; CT-19).

`COMP-QMF-VENUE` defines the venue-neutral **command contract** on qmf-core nouns: a
caller submits one of exactly **five** typed command kinds — ``place_order``,
``cancel_order``, ``close_position``, ``close_all``, and ``amend_protection`` (the fifth,
minted through AD-27's own explicit-later-mint clause) — over the ``(VenueId, account)``
command stream, and every well-formed submission resolves to exactly one of **four**
outcomes — ``accepted-by-venue``, ``rejected-by-venue``, ``denied-locally``, or
``UNKNOWN`` — with uncertainty recorded as an explicit state, never assumed, retried,
flattened, or invented (CT-19; DEC-0137, DEC-0140, DEC-0148).

The law this module encodes:

* **Five kinds, typed per kind, no free-form payload** (:class:`CommandKind`,
  :class:`Command`). Each kind carries only its own typed fields on qmf-core value types
  (exact prices/quantities per the foreign-value boundary, identity per the minting
  discipline); kinds are addable, never redefined. A general ``amend_order`` and a
  *fractional or partial* close arrive only by an explicit later mint — never through a
  payload — so a V1 partial exit is an ``unsupported capability`` refusal, and
  ``amend_protection`` is never widened into a general amend (CT-19; DEC-0137, DEC-0148).
* **The four-outcome law** (:class:`SubmissionOutcome`, :class:`CommandOutcomeResolver`).
  A well-formed submission resolves to exactly one of the four; ``denied-locally`` is an
  **outcome, never a refusal** (typed refusals are reserved for a malformed command, an
  undeclared capability, and a blocked stream), and every outcome mints an observation
  record (:class:`CommandObservation`) and a journal event (:class:`JournalEvent`). A
  transport error, timeout, or disconnect yields ``UNKNOWN`` — a **state, not an error**
  — and a venue-returned error resolves ``rejected-by-venue`` **only** where the CT-18
  error table declares that class; a timeout is never read as a rejection (DEC-0137).
* **Command identity is the command record's fp1** — the ``(VenueId, account)`` stream
  qualification, the session epoch, and the caller's opaque ordering ordinal, plus the
  kind and its typed parameters. Where the CT-18 mapping into the venue client-id field
  is not injective-and-total, a durable :class:`CommandIdBinding` persists through the
  injected :class:`~qmf.core.RecordSink` **before** submission; re-presenting the same
  command is an idempotent accept, and differing content under a reused identity is
  refused and alarmed (:class:`CommandIdBindingRegistry`; CT-19, DEC-0137, DEC-0138).
* **``amend_protection`` is risk-non-increasing per protection side**
  (:class:`ProtectionAmendment`): a stop-side change may not increase the loss-direction
  distance measured against the frozen ``original_risk_distance``, and the contract-level
  check binds the **stop side only** — the target side is governed by the Book's declared
  envelope, not the risk test (CT-19; DEC-0148, DEC-0154, DEC-0158).
* **A compound command's outcome is the meet of its children** (:class:`CompoundCommand`,
  :func:`meet_outcomes`): any child ``UNKNOWN`` makes the parent ``UNKNOWN``, any child
  non-success makes the parent ``partially-executed`` — a named outcome that is **never a
  success** (CT-19; DEC-0137, DEC-0140).

This module holds the **shape and the law**, never a broker fact or a policy value: the
submission deadline is a declared, application-injected parameter under do-not-default,
and no retry/pool/throttle constant lives here (DEC-0137). It reads no clock — every
instant and elapsed measurement is injected — and no binary float touches the money path
(DEC-0105, DEC-0106). It imports only ``qmf-core`` and the sibling capability module;
nothing imports ``qmf-venue`` (default-deny, L30/DEC-0120). Frozen, immutable values
throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, TypeVar, cast

from qmf.core import (
    Account,
    Duration,
    Fingerprint,
    Instant,
    Ok,
    Price,
    PriceDelta,
    Quantity,
    RecordSink,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    VenueId,
    fingerprint,
    is_refusal,
)
from qmf.venue.capabilities import (
    CapabilityDeclaration,
    CapabilityFieldName,
    CloseScope,
    SubmissionOutcomeClass,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "FOUR_OUTCOME_LAW",
    "BindingOutcome",
    "Command",
    "CommandIdBinding",
    "CommandIdBindingRegistry",
    "CommandKind",
    "CommandObservation",
    "CommandOutcomeResolver",
    "CompoundChild",
    "CompoundCommand",
    "JournalEvent",
    "OrderParameters",
    "OrderType",
    "ProtectionAmendment",
    "ProtectionSide",
    "SubmissionOutcome",
    "SubmissionResult",
    "TimeInForce",
    "UnknownTrigger",
    "command_id_mapping_is_injective_total",
    "derive_child_identity",
    "is_success",
    "journal_event_type",
    "meet_outcomes",
]

# Every serialized CT-19 artifact stamps this integer contract format version; its
# meaning never mutates — an incompatible change mints the next version (DEC-0103;
# versioning-from-birth L15). CT-19 is at format version 1.
CONTRACT_FORMAT_VERSION: Final[int] = 1

_EnumT = TypeVar("_EnumT", bound=StrEnum)


# --- the command vocabulary -------------------------------------------------


class CommandKind(StrEnum):
    """The five typed command kinds (CT-19 ``command kind``; DEC-0137, DEC-0148).

    Exactly these five and no more; the set is **addable, never redefined**. A general
    ``amend_order`` (price, size, expiry) and a partial close arrive only by an explicit
    later mint — never through a payload — and ``amend_protection`` is never widened into
    a general amend. A command is exactly one kind, typed per kind on qmf-core nouns.
    """

    PLACE_ORDER = "place_order"
    CANCEL_ORDER = "cancel_order"
    CLOSE_POSITION = "close_position"
    CLOSE_ALL = "close_all"
    AMEND_PROTECTION = "amend_protection"


class OrderType(StrEnum):
    """The QMF-owned order-type vocabulary (CT-19; DEC-0137, DEC-0138).

    Addable, never redefined. Each adapter declares its supported subset in CT-18;
    invoking an undeclared order type is an ``unsupported capability`` refusal at the
    capability layer, never emulated here.
    """

    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop-limit"


class TimeInForce(StrEnum):
    """The QMF-owned time-in-force vocabulary (CT-19; DEC-0137).

    Addable, never redefined; the adapter's supported subset is declared in CT-18. The
    member set is a reasonable order-parameter vocabulary, not a spine-pinned closed
    contract enum.
    """

    GOOD_TILL_CANCEL = "good-till-cancel"
    IMMEDIATE_OR_CANCEL = "immediate-or-cancel"
    FILL_OR_KILL = "fill-or-kill"
    GOOD_TILL_DATE = "good-till-date"
    DAY = "day"


class ProtectionSide(StrEnum):
    """The protection side an ``amend_protection`` change addresses (CT-19; DEC-0148).

    The risk-non-increasing contract-level check binds the ``STOP`` side only — measured
    against the frozen ``original_risk_distance``; a ``TARGET``-side change is governed by
    the Book's declared envelope, not the risk test.
    """

    STOP = "stop"
    TARGET = "target"


class SubmissionOutcome(StrEnum):
    """The four-outcome law plus the compound-only ``partially-executed`` (CT-19).

    A single well-formed submission resolves to exactly one of the four members of
    :data:`FOUR_OUTCOME_LAW` — ``ACCEPTED_BY_VENUE``, ``REJECTED_BY_VENUE``,
    ``DENIED_LOCALLY``, or ``UNKNOWN``. ``DENIED_LOCALLY`` is an **outcome, never a
    refusal**, and ``UNKNOWN`` is a **state, never an error**. ``PARTIALLY_EXECUTED`` is
    a **compound-parent-only** outcome — never a single-submission outcome and **never a
    success** — minted by the meet of a compound command's children (DEC-0137, DEC-0140).
    """

    ACCEPTED_BY_VENUE = "accepted-by-venue"
    REJECTED_BY_VENUE = "rejected-by-venue"
    DENIED_LOCALLY = "denied-locally"
    UNKNOWN = "UNKNOWN"
    PARTIALLY_EXECUTED = "partially-executed"


# The four outcomes a single well-formed submission may resolve to — the four-outcome
# law. ``PARTIALLY_EXECUTED`` is deliberately excluded: it is a compound-parent outcome
# only, so a single submission never resolves to it (DEC-0137, DEC-0140).
FOUR_OUTCOME_LAW: Final[frozenset[SubmissionOutcome]] = frozenset(
    {
        SubmissionOutcome.ACCEPTED_BY_VENUE,
        SubmissionOutcome.REJECTED_BY_VENUE,
        SubmissionOutcome.DENIED_LOCALLY,
        SubmissionOutcome.UNKNOWN,
    }
)


def is_success(outcome: object) -> bool:
    """Whether ``outcome`` is the one success outcome — ``accepted-by-venue`` (CT-19).

    Only ``ACCEPTED_BY_VENUE`` is a success. ``rejected-by-venue``, ``denied-locally``,
    ``UNKNOWN``, and the compound-only ``partially-executed`` are each **never a success**
    (DEC-0137).
    """
    return outcome is SubmissionOutcome.ACCEPTED_BY_VENUE


class UnknownTrigger(StrEnum):
    """Why a submission resolved to ``UNKNOWN`` — a transport-level trigger (CT-19).

    An ``UNKNOWN`` minted on the transport path carries exactly one of these; a timeout is
    **never read as a rejection**, and no component retries, assumes an outcome, or invents
    a terminal state on ``UNKNOWN`` (DEC-0137).
    """

    TIMEOUT = "timeout"
    TRANSPORT_ERROR = "transport-error"
    DISCONNECT = "disconnect"


# --- refusal builders -------------------------------------------------------


def _invalid(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a malformed command returns (CT-04; DEC-0109)."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _unsupported(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unsupported capability`` refusal an undeclared kind, an unsupported
    parameter, or a fractional/partial close returns (FM-4; DEC-0137, DEC-0148)."""
    context: dict[str, object] = {"field": field_name, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context=context,
    )


def _collision(field_name: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` **alarm** a true command-id collision returns.

    Differing content under a reused venue client-id identity is a true collision; it is
    refused and **alarmed**, never overwritten — mirroring qmf-core's FM-6 collision guard
    (CT-19; DEC-0137, DEC-0108).
    """
    context: dict[str, object] = {"field": field_name, "reason": reason, "alarm": True}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


# --- validation helpers -----------------------------------------------------


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


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _as_ordinal(value: object) -> int | None:
    """Return ``value`` as a non-negative ``int`` ordinal, or ``None``.

    A ``bool`` (an int subclass) and a binary ``float`` are both rejected — an ordering
    ordinal is an integer count, never a float on any path (DEC-0105).
    """
    if isinstance(value, bool):
        return None
    if not isinstance(value, int) or value < 0:
        return None
    return value


def _instruments_agree(*values: Price | PriceDelta | None) -> bool:
    """Whether every present price/delta value names the same instrument.

    A command's price-like parameters must be quoted for one instrument; a mismatch is a
    malformed command. Absent (``None``) values are ignored.
    """
    present = [value for value in values if value is not None]
    if len(present) <= 1:
        return True
    anchor = present[0].instrument
    return all(value.instrument == anchor for value in present[1:])


def _stream_qualification_content(venue_id: VenueId, account: Account) -> dict[str, object]:
    """The canonical fp1 fragment for a ``(VenueId, account)`` command stream (CT-19).

    The stream qualification is part of command identity: the venue id plus the full
    account identity (id and role), so a command can never share identity across streams.
    """
    return {
        "venue_id": venue_id.value,
        "account_id": account.account_id,
        "account_role": account.role.value,
    }


# --- typed per-kind payloads ------------------------------------------------


@dataclass(frozen=True, slots=True)
class OrderParameters:
    """The typed parameters of a ``place_order`` command (CT-19; DEC-0137, DEC-0138).

    Order type and time-in-force are QMF-owned vocabulary; the ``quantity`` is an exact
    :class:`~qmf.core.Quantity` (a binary float on the money path is refused); ``limit_price``
    and ``stop_price`` are exact :class:`~qmf.core.Price` levels present per order type; and
    ``protective_stop_distance`` is an optional entry-relative :class:`~qmf.core.PriceDelta`
    (the declared placement path for MARKET orders on the cTrader-platform profile). A
    kind-inappropriate price is an omitted field, never a null.
    """

    order_type: OrderType
    time_in_force: TimeInForce
    quantity: Quantity
    limit_price: Price | None = None
    stop_price: Price | None = None
    protective_stop_distance: PriceDelta | None = None

    @classmethod
    def try_create(
        cls,
        order_type: object,
        time_in_force: object,
        quantity: object,
        *,
        limit_price: object = None,
        stop_price: object = None,
        protective_stop_distance: object = None,
    ) -> Result[OrderParameters]:
        """Validate and build :class:`OrderParameters`, returning value-or-refusal.

        The order type and time-in-force must name their vocabularies; the quantity must
        be a strictly-positive exact :class:`~qmf.core.Quantity`; and the price presence
        must match the order type — a ``limit``/``stop-limit`` requires a limit price, a
        ``stop``/``stop-limit`` requires a stop price, and a ``market`` carries neither.
        Every present price and delta must name the same instrument (CT-01; DEC-0105).
        """
        resolved_type = _coerce(OrderType, order_type)
        if resolved_type is None:
            return _invalid(
                "order_type",
                "an order type is one of market | limit | stop | stop-limit",
                given=repr(order_type),
                allowed=[member.value for member in OrderType],
            )
        resolved_tif = _coerce(TimeInForce, time_in_force)
        if resolved_tif is None:
            return _invalid(
                "time_in_force",
                "a time-in-force names the QMF-owned vocabulary",
                given=repr(time_in_force),
                allowed=[member.value for member in TimeInForce],
            )
        if not isinstance(quantity, Quantity):
            return _invalid(
                "quantity",
                "an order quantity is an exact qmf-core Quantity; a binary float on the "
                "money path is refused (FM-1)",
                given=repr(quantity),
            )
        if quantity.as_fraction() <= 0:
            return _invalid(
                "quantity",
                "an order quantity is strictly positive",
                given=str(quantity.as_fraction()),
            )
        limit = _optional_price(limit_price)
        if isinstance(limit, TypedRefusal):
            return limit
        stop = _optional_price(stop_price)
        if isinstance(stop, TypedRefusal):
            return stop
        protective = _optional_delta(protective_stop_distance)
        if isinstance(protective, TypedRefusal):
            return protective
        presence = _validate_price_presence(resolved_type, limit, stop)
        if presence is not None:
            return presence
        if not _instruments_agree(limit, stop, protective):
            return _invalid(
                "instrument",
                "every price and protective distance on one order must name the same instrument",
            )
        return Ok(
            cls(
                order_type=resolved_type,
                time_in_force=resolved_tif,
                quantity=quantity,
                limit_price=limit,
                stop_price=stop,
                protective_stop_distance=protective,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical fp1 identity content — parameters, present prices only
        (an absent price is an omitted key, never a null; DEC-0108)."""
        content: dict[str, object] = {
            "class": "order-parameters",
            "order_type": self.order_type.value,
            "time_in_force": self.time_in_force.value,
            "quantity": self.quantity.fp1_identity(),
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.limit_price is not None:
            content["limit_price"] = self.limit_price.fp1_identity()
        if self.stop_price is not None:
            content["stop_price"] = self.stop_price.fp1_identity()
        if self.protective_stop_distance is not None:
            content["protective_stop_distance"] = self.protective_stop_distance.fp1_identity()
        return content


def _optional_price(value: object) -> Price | TypedRefusal | None:
    """Resolve an optional :class:`~qmf.core.Price`: ``None`` stays ``None``, a
    non-``Price`` is refused (a float would have been refused at Price construction)."""
    if value is None:
        return None
    if not isinstance(value, Price):
        return _invalid("price", "a price parameter is an exact qmf-core Price", given=repr(value))
    return value


def _optional_delta(value: object) -> PriceDelta | TypedRefusal | None:
    """Resolve an optional :class:`~qmf.core.PriceDelta`; a non-``PriceDelta`` is refused."""
    if value is None:
        return None
    if not isinstance(value, PriceDelta):
        return _invalid(
            "protective_stop_distance",
            "an entry-relative protective distance is an exact qmf-core PriceDelta",
            given=repr(value),
        )
    return value


def _validate_price_presence(
    order_type: OrderType, limit: Price | None, stop: Price | None
) -> TypedRefusal | None:
    """Validate that price presence matches the order type (CT-19; DEC-0137)."""
    needs_limit = order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT)
    needs_stop = order_type in (OrderType.STOP, OrderType.STOP_LIMIT)
    if needs_limit and limit is None:
        return _invalid("limit_price", "a limit or stop-limit order requires a limit price")
    if not needs_limit and limit is not None:
        return _invalid(
            "limit_price",
            "only a limit or stop-limit order carries a limit price",
            order_type=order_type.value,
        )
    if needs_stop and stop is None:
        return _invalid("stop_price", "a stop or stop-limit order requires a stop price")
    if not needs_stop and stop is not None:
        return _invalid(
            "stop_price",
            "only a stop or stop-limit order carries a stop price",
            order_type=order_type.value,
        )
    return None


@dataclass(frozen=True, slots=True)
class ProtectionAmendment:
    """The typed change of an ``amend_protection`` command (CT-19; DEC-0148, DEC-0158).

    A protection amendment is constrained at contract level to **risk-non-increasing**
    changes **per protection side**. ``new_distance`` is the entry-relative
    :class:`~qmf.core.PriceDelta` the amended protection sits at, derived from the declared
    ``reference_price`` (the plan, never read back as the observed fill). For the ``STOP``
    side the ``original_risk_distance`` is the frozen loss-direction distance the new stop
    may **not exceed**; for the ``TARGET`` side there is no risk test — the Book's declared
    envelope governs it — so ``original_risk_distance`` must be absent. It is never emulated
    by cancel-then-place and never widened into a general amend (DEC-0148).
    """

    protection_side: ProtectionSide
    new_distance: PriceDelta
    reference_price: Price
    original_risk_distance: PriceDelta | None = None

    @classmethod
    def try_create(
        cls,
        protection_side: object,
        new_distance: object,
        reference_price: object,
        *,
        original_risk_distance: object = None,
    ) -> Result[ProtectionAmendment]:
        """Validate and build a :class:`ProtectionAmendment`, returning value-or-refusal.

        The ``STOP`` side requires the frozen ``original_risk_distance`` and refuses a
        **risk-increasing** change — the new loss-direction distance may not exceed it. The
        ``TARGET`` side refuses an ``original_risk_distance`` (the risk test binds the stop
        side only). Every price and delta must name one instrument (CT-19; DEC-0148).
        """
        resolved_side = _coerce(ProtectionSide, protection_side)
        if resolved_side is None:
            return _invalid(
                "protection_side",
                "a protection side is one of stop | target",
                given=repr(protection_side),
                allowed=[member.value for member in ProtectionSide],
            )
        if not isinstance(new_distance, PriceDelta):
            return _invalid(
                "new_distance",
                "the amended protection distance is an exact qmf-core PriceDelta",
                given=repr(new_distance),
            )
        if not isinstance(reference_price, Price):
            return _invalid(
                "reference_price",
                "the declared reference price a relative distance derives from is an exact "
                "qmf-core Price",
                given=repr(reference_price),
            )
        if not _instruments_agree(reference_price, new_distance):
            return _invalid(
                "instrument",
                "the reference price and the amended distance must name the same instrument",
            )
        original = _resolve_original_risk_distance(
            resolved_side, original_risk_distance, new_distance
        )
        if isinstance(original, TypedRefusal):
            return original
        return Ok(
            cls(
                protection_side=resolved_side,
                new_distance=new_distance,
                reference_price=reference_price,
                original_risk_distance=original,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical fp1 identity content — side, distance, reference, and
        (stop side only) the frozen original risk distance (DEC-0108)."""
        content: dict[str, object] = {
            "class": "protection-amendment",
            "protection_side": self.protection_side.value,
            "new_distance": self.new_distance.fp1_identity(),
            "reference_price": self.reference_price.fp1_identity(),
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.original_risk_distance is not None:
            content["original_risk_distance"] = self.original_risk_distance.fp1_identity()
        return content


def _resolve_original_risk_distance(
    side: ProtectionSide, original_risk_distance: object, new_distance: PriceDelta
) -> PriceDelta | TypedRefusal | None:
    """Apply the per-side risk rule to ``amend_protection`` (CT-19; DEC-0148, DEC-0154).

    ``STOP``: the frozen ``original_risk_distance`` is required, must name the amendment's
    instrument, and the new loss-direction distance may not exceed it (risk-non-increasing).
    ``TARGET``: an ``original_risk_distance`` is refused — the risk test binds the stop side
    only, and the target side is governed by the Book's declared envelope.
    """
    if side is ProtectionSide.TARGET:
        if original_risk_distance is not None:
            return _invalid(
                "original_risk_distance",
                "original_risk_distance is a stop-side field; a target-side change is governed "
                "by the Book's declared envelope, not the contract-level risk test",
            )
        return None
    # Stop side: the risk-non-increasing check binds here, against the frozen original.
    if not isinstance(original_risk_distance, PriceDelta):
        return _invalid(
            "original_risk_distance",
            "a stop-side amendment is checked against the frozen original_risk_distance (an "
            "exact qmf-core PriceDelta)",
            given=repr(original_risk_distance),
        )
    if original_risk_distance.instrument != new_distance.instrument:
        return _invalid(
            "original_risk_distance",
            "the frozen original_risk_distance and the new distance must name the same instrument",
        )
    if abs(new_distance.as_fraction()) > abs(original_risk_distance.as_fraction()):
        return _invalid(
            "new_distance",
            "a stop-side amendment must be risk-non-increasing: the new loss-direction distance "
            "may not exceed the frozen original_risk_distance",
            new_distance=str(new_distance.as_fraction()),
            original_risk_distance=str(original_risk_distance.as_fraction()),
        )
    return original_risk_distance


# --- the command record -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class Command:
    """One typed venue command whose fp1 is its identity (CT-19; DEC-0137, DEC-0148).

    Built through a **per-kind factory** — :meth:`place_order`, :meth:`cancel_order`,
    :meth:`close_position`, :meth:`close_all`, :meth:`amend_protection` — each of which
    validates and sets only that kind's typed fields; every kind-inappropriate field stays
    ``None`` (an omitted key in identity, never a null). Command identity is the record's
    :meth:`fingerprint` over the stream qualification, session epoch, ordering ordinal,
    kind, and typed parameters — there is no free-form payload.
    """

    kind: CommandKind
    venue_id: VenueId
    account: Account
    session_epoch: str
    ordering_ordinal: int
    order_parameters: OrderParameters | None = None
    close_scope: CloseScope | None = None
    subject_reference: str | None = None
    protection_amendment: ProtectionAmendment | None = None

    # -- shared identity validation ------------------------------------------

    @staticmethod
    def _validate_stream(
        venue_id: object, account: object, session_epoch: object, ordering_ordinal: object
    ) -> tuple[VenueId, Account, str, int] | TypedRefusal:
        """Validate the identity-bearing stream qualification shared by every kind."""
        if not isinstance(venue_id, VenueId) or venue_id.value.strip() == "":
            return _invalid("venue_id", "a command targets a valid VenueId", given=repr(venue_id))
        if not isinstance(account, Account):
            return _invalid("account", "a command targets a valid Account", given=repr(account))
        if account.venue != venue_id:
            return _invalid(
                "account",
                "the account does not belong to this venue; the (VenueId, account) command "
                "stream would name a binding that cannot exist",
                venue=venue_id.value,
                account_venue=account.venue.value,
            )
        epoch = _clean_str(session_epoch)
        if epoch is None:
            return _invalid(
                "session_epoch",
                "a session-epoch id (distinct from the boot epoch) is a non-empty token",
                given=repr(session_epoch),
            )
        ordinal = _as_ordinal(ordering_ordinal)
        if ordinal is None:
            return _invalid(
                "ordering_ordinal",
                "the caller's ordering ordinal is a non-negative integer; the node owns the "
                "sequencer and QMF carries the field",
                given=repr(ordering_ordinal),
            )
        return venue_id, account, epoch, ordinal

    # -- per-kind factories --------------------------------------------------

    @classmethod
    def place_order(
        cls,
        venue_id: object,
        account: object,
        session_epoch: object,
        ordering_ordinal: object,
        order_parameters: object,
    ) -> Result[Command]:
        """Build a ``place_order`` command carrying typed :class:`OrderParameters`."""
        stream = cls._validate_stream(venue_id, account, session_epoch, ordering_ordinal)
        if isinstance(stream, TypedRefusal):
            return stream
        resolved_venue, resolved_account, epoch, ordinal = stream
        if not isinstance(order_parameters, OrderParameters):
            return _invalid(
                "order_parameters",
                "place_order carries typed OrderParameters, never a free-form payload",
                given=repr(order_parameters),
            )
        return Ok(
            cls(
                kind=CommandKind.PLACE_ORDER,
                venue_id=resolved_venue,
                account=resolved_account,
                session_epoch=epoch,
                ordering_ordinal=ordinal,
                order_parameters=order_parameters,
            )
        )

    @classmethod
    def cancel_order(
        cls,
        venue_id: object,
        account: object,
        session_epoch: object,
        ordering_ordinal: object,
        subject_reference: object,
    ) -> Result[Command]:
        """Build a ``cancel_order`` command naming the order it cancels."""
        stream = cls._validate_stream(venue_id, account, session_epoch, ordering_ordinal)
        if isinstance(stream, TypedRefusal):
            return stream
        resolved_venue, resolved_account, epoch, ordinal = stream
        subject = _clean_str(subject_reference)
        if subject is None:
            return _invalid(
                "subject_reference",
                "cancel_order names the pending order it cancels by an opaque reference",
                given=repr(subject_reference),
            )
        return Ok(
            cls(
                kind=CommandKind.CANCEL_ORDER,
                venue_id=resolved_venue,
                account=resolved_account,
                session_epoch=epoch,
                ordering_ordinal=ordinal,
                subject_reference=subject,
            )
        )

    @classmethod
    def close_position(
        cls,
        venue_id: object,
        account: object,
        session_epoch: object,
        ordering_ordinal: object,
        close_scope: object,
        subject_reference: object,
        *,
        partial_quantity: object = None,
    ) -> Result[Command]:
        """Build a ``close_position`` command over a required typed scope.

        A fractional or partial close is an ``unsupported capability`` refusal — no command
        kind expresses a fractional close, so a V1 partial exit (emulable only by
        close-then-replace, the unprotected window forbidden) is refused, never expressed
        through a payload (AR-44; DEC-0137, DEC-0147, DEC-0148).
        """
        return cls._build_close(
            CommandKind.CLOSE_POSITION,
            venue_id,
            account,
            session_epoch,
            ordering_ordinal,
            close_scope,
            subject_reference,
            partial_quantity,
        )

    @classmethod
    def close_all(
        cls,
        venue_id: object,
        account: object,
        session_epoch: object,
        ordering_ordinal: object,
        close_scope: object,
        subject_reference: object,
        *,
        partial_quantity: object = None,
    ) -> Result[Command]:
        """Build a ``close_all`` command over a required typed scope.

        As with :meth:`close_position`, a fractional or partial close is an
        ``unsupported capability`` refusal, never emulated and never expressed as a payload.
        """
        return cls._build_close(
            CommandKind.CLOSE_ALL,
            venue_id,
            account,
            session_epoch,
            ordering_ordinal,
            close_scope,
            subject_reference,
            partial_quantity,
        )

    @classmethod
    def _build_close(
        cls,
        kind: CommandKind,
        venue_id: object,
        account: object,
        session_epoch: object,
        ordering_ordinal: object,
        close_scope: object,
        subject_reference: object,
        partial_quantity: object,
    ) -> Result[Command]:
        """Shared validation for ``close_position`` and ``close_all`` (CT-19; DEC-0137)."""
        if partial_quantity is not None:
            return _unsupported(
                "partial_quantity",
                "a fractional or partial close is unsupported in V1; a close is whole-scope "
                "only — a partial exit is emulable only by close-then-replace (the unprotected "
                "window forbidden) and is refused, never widened into a fractional close",
                kind=kind.value,
            )
        stream = cls._validate_stream(venue_id, account, session_epoch, ordering_ordinal)
        if isinstance(stream, TypedRefusal):
            return stream
        resolved_venue, resolved_account, epoch, ordinal = stream
        scope = _coerce(CloseScope, close_scope)
        if scope is None:
            return _invalid(
                "close_scope",
                "a close carries a required typed scope: account | account-binding | "
                "instrument-within-binding",
                given=repr(close_scope),
                allowed=[member.value for member in CloseScope],
            )
        subject = _clean_str(subject_reference)
        if subject is None:
            return _invalid(
                "subject_reference",
                "a close names its subject (position or scope target) by an opaque reference",
                given=repr(subject_reference),
            )
        return Ok(
            cls(
                kind=kind,
                venue_id=resolved_venue,
                account=resolved_account,
                session_epoch=epoch,
                ordering_ordinal=ordinal,
                close_scope=scope,
                subject_reference=subject,
            )
        )

    @classmethod
    def amend_protection(
        cls,
        venue_id: object,
        account: object,
        session_epoch: object,
        ordering_ordinal: object,
        protection_amendment: object,
        subject_reference: object,
    ) -> Result[Command]:
        """Build an ``amend_protection`` command carrying a typed :class:`ProtectionAmendment`.

        The risk-non-increasing per-side constraint is enforced when the
        :class:`ProtectionAmendment` itself is built; this factory carries it under the
        command identity discipline with its subject reference (the position or pending order
        the CT-20 subject-terminal resolution reads), so a stop filling mid-amend is a named
        outcome, never a stream-blocking UNKNOWN (DEC-0148).
        """
        stream = cls._validate_stream(venue_id, account, session_epoch, ordering_ordinal)
        if isinstance(stream, TypedRefusal):
            return stream
        resolved_venue, resolved_account, epoch, ordinal = stream
        if not isinstance(protection_amendment, ProtectionAmendment):
            return _invalid(
                "protection_amendment",
                "amend_protection carries a typed ProtectionAmendment (risk-non-increasing per "
                "side), never a free-form payload and never a general amend_order",
                given=repr(protection_amendment),
            )
        subject = _clean_str(subject_reference)
        if subject is None:
            return _invalid(
                "subject_reference",
                "amend_protection names its subject (position or pending order) by an opaque "
                "reference read by the CT-20 subject-terminal resolution",
                given=repr(subject_reference),
            )
        return Ok(
            cls(
                kind=CommandKind.AMEND_PROTECTION,
                venue_id=resolved_venue,
                account=resolved_account,
                session_epoch=epoch,
                ordering_ordinal=ordinal,
                subject_reference=subject,
                protection_amendment=protection_amendment,
            )
        )

    # -- identity ------------------------------------------------------------

    @property
    def command_stream(self) -> dict[str, object]:
        """The ``(VenueId, account)`` stream qualification content this command runs on."""
        return _stream_qualification_content(self.venue_id, self.account)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical fp1 identity content — the command record's identity.

        Identity-bearing over the stream qualification, session epoch, ordering ordinal,
        kind, and the kind's typed parameters; a kind-inappropriate field is an omitted key,
        never a null (CT-19; DEC-0108, DEC-0137).
        """
        content: dict[str, object] = {
            "class": "venue-command",
            "command_kind": self.kind.value,
            "stream_qualification": _stream_qualification_content(self.venue_id, self.account),
            "session_epoch": self.session_epoch,
            "ordering_ordinal": self.ordering_ordinal,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.order_parameters is not None:
            content["order_parameters"] = self.order_parameters.fp1_identity()
        if self.close_scope is not None:
            content["close_scope"] = self.close_scope.value
        if self.subject_reference is not None:
            content["subject_reference"] = self.subject_reference
        if self.protection_amendment is not None:
            content["protection_amendment"] = self.protection_amendment.fp1_identity()
        return content

    def fingerprint(self) -> Result[Fingerprint]:
        """The command's identity-bearing fp1 fingerprint, returning value-or-refusal.

        The command's identity **is** this fp1 — a venue-native id is never sufficient alone
        (CT-19; DEC-0137). Re-fingerprinting the same command yields the same identity;
        differing content yields a different identity.
        """
        return fingerprint(self)


# --- outcome records --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CommandObservation:
    """The observation record minted for one submission outcome (CT-19, CT-20; DEC-0137).

    Every outcome — ``denied-locally`` included — mints one of these. It is
    **occurrence/provenance only**: the receive instant, monotonic elapsed measurement,
    submission deadline, and correlation are occurrence/display-only and never identity
    content, so this record deliberately exposes no ``fp1_identity``. An ``UNKNOWN`` minted
    on the transport path carries its ``trigger``, the ``monotonic_elapsed`` measurement,
    the ``receive_instant``, and the ``submission_deadline`` in force (a declared,
    application-injected parameter under do-not-default); a venue-error path carries the
    ``venue_code``, and a ``denied-locally`` path carries the ``local_reason`` (DEC-0137).
    """

    command_fp1: Fingerprint
    kind: CommandKind
    outcome: SubmissionOutcome
    receive_instant: Instant
    unknown_trigger: UnknownTrigger | None = None
    monotonic_elapsed: Duration | None = None
    submission_deadline: Instant | None = None
    venue_code: str | None = None
    local_reason: str | None = None
    detail: str = ""


def journal_event_type(kind: CommandKind, outcome: SubmissionOutcome) -> str:
    """The journal event type for a ``(command kind, outcome)`` pair (CT-20; DEC-0137).

    The deterministic ``(command kind x outcome) -> journal event type`` mapping under the
    cardinality law — exactly one journal event per outcome.
    """
    return f"command.{kind.value}.{outcome.value}"


@dataclass(frozen=True, slots=True)
class JournalEvent:
    """The journal event minted for one submission outcome (CT-13, CT-20; DEC-0137).

    Exactly one journal event per outcome (the cardinality law). ``event_type`` is the
    deterministic ``(command kind x outcome) -> journal event type`` mapping.
    """

    command_fp1: Fingerprint
    kind: CommandKind
    outcome: SubmissionOutcome
    event_type: str

    @classmethod
    def for_outcome(
        cls, command_fp1: Fingerprint, kind: CommandKind, outcome: SubmissionOutcome
    ) -> JournalEvent:
        """Mint the journal event for a resolved outcome (one per outcome)."""
        return cls(
            command_fp1=command_fp1,
            kind=kind,
            outcome=outcome,
            event_type=journal_event_type(kind, outcome),
        )


@dataclass(frozen=True, slots=True)
class SubmissionResult:
    """The resolution of one well-formed submission (CT-19; DEC-0137, DEC-0140).

    Carries the resolved four-outcome-law ``outcome`` plus the observation record and
    journal event it minted — every outcome mints exactly one of each.
    """

    command_fp1: Fingerprint
    kind: CommandKind
    outcome: SubmissionOutcome
    observation: CommandObservation
    journal_event: JournalEvent


# --- the four-outcome resolver ----------------------------------------------


@dataclass(frozen=True, slots=True)
class CommandOutcomeResolver:
    """Resolves a well-formed submission to exactly one of the four outcomes (CT-19).

    Holds the static :class:`~qmf.venue.capabilities.CapabilityDeclaration` whose pinned
    CT-18 error table decides whether a venue-returned error reads as ``rejected-by-venue``.
    Every entry point mints an observation record and a journal event, and ``denied-locally``
    is an **outcome, never a refusal** (DEC-0137, DEC-0138).
    """

    declaration: CapabilityDeclaration

    @classmethod
    def try_create(cls, declaration: object) -> Result[CommandOutcomeResolver]:
        """Validate and build a :class:`CommandOutcomeResolver`, returning value-or-refusal."""
        if not isinstance(declaration, CapabilityDeclaration):
            return _invalid(
                "declaration",
                "the resolver reads the pinned CT-18 error table from a CapabilityDeclaration",
                given=repr(declaration),
            )
        return Ok(cls(declaration=declaration))

    def accepted(self, command: object, *, receive_instant: object) -> Result[SubmissionResult]:
        """Resolve a submission the venue accepted → ``accepted-by-venue`` (CT-19)."""
        prepared = _prepare(command, receive_instant)
        if isinstance(prepared, TypedRefusal):
            return prepared
        resolved_command, fp, instant = prepared
        observation = CommandObservation(
            command_fp1=fp,
            kind=resolved_command.kind,
            outcome=SubmissionOutcome.ACCEPTED_BY_VENUE,
            receive_instant=instant,
            detail="the venue acknowledged the submission",
        )
        return _result(fp, resolved_command.kind, SubmissionOutcome.ACCEPTED_BY_VENUE, observation)

    def denied_locally(
        self, command: object, *, reason: object, receive_instant: object
    ) -> Result[SubmissionResult]:
        """Resolve a submission a local policy denied → ``denied-locally`` (CT-19).

        ``denied-locally`` is an **outcome, never a refusal**: it mints an observation and a
        journal event exactly like any other outcome, and the command was never submitted to
        the venue (DEC-0137).
        """
        prepared = _prepare(command, receive_instant)
        if isinstance(prepared, TypedRefusal):
            return prepared
        resolved_command, fp, instant = prepared
        local_reason = _clean_str(reason)
        if local_reason is None:
            return _invalid(
                "reason",
                "a local denial records its reason as a non-empty string",
                given=repr(reason),
            )
        observation = CommandObservation(
            command_fp1=fp,
            kind=resolved_command.kind,
            outcome=SubmissionOutcome.DENIED_LOCALLY,
            receive_instant=instant,
            local_reason=local_reason,
            detail="denied locally before submission; an outcome, never a refusal",
        )
        return _result(fp, resolved_command.kind, SubmissionOutcome.DENIED_LOCALLY, observation)

    def venue_error(
        self, command: object, *, venue_code: object, receive_instant: object
    ) -> Result[SubmissionResult]:
        """Resolve a venue-returned error through the pinned CT-18 error table (CT-19).

        A venue code reads as ``rejected-by-venue`` **only** where a pinned error-map row
        declares that class; every other code — including every unmapped one, under the
        fail-closed default — resolves ``UNKNOWN``, a state never an error. A timeout is
        never routed here (it is a transport trigger), so a timeout is never read as a
        rejection (DEC-0137, DEC-0138).
        """
        prepared = _prepare(command, receive_instant)
        if isinstance(prepared, TypedRefusal):
            return prepared
        resolved_command, fp, instant = prepared
        code = _clean_str(venue_code)
        if code is None:
            return _invalid(
                "venue_code", "a venue error carries a non-empty venue code", given=repr(venue_code)
            )
        resolution = self.declaration.resolve_error(code, resolved_command.kind.value)
        if is_refusal(resolution):
            return resolution
        outcome = (
            SubmissionOutcome.REJECTED_BY_VENUE
            if resolution.value.outcome_class is SubmissionOutcomeClass.REJECTED_BY_VENUE
            else SubmissionOutcome.UNKNOWN
        )
        observation = CommandObservation(
            command_fp1=fp,
            kind=resolved_command.kind,
            outcome=outcome,
            receive_instant=instant,
            venue_code=code,
            detail=resolution.value.detail,
        )
        return _result(fp, resolved_command.kind, outcome, observation)

    def transport_unknown(
        self,
        command: object,
        *,
        trigger: object,
        monotonic_elapsed: object,
        receive_instant: object,
        submission_deadline: object,
    ) -> Result[SubmissionResult]:
        """Resolve a lost-certainty submission → ``UNKNOWN``, a state not an error (CT-19).

        A transport error, timeout, or disconnect before a final outcome mints an explicit
        ``UNKNOWN`` observation carrying its ``trigger``, the monotonic elapsed measurement,
        the wall receive instant, and the ``submission_deadline`` in force — a declared,
        application-injected parameter under do-not-default (its value is never QMF's, so it
        is a mandatory argument here, never defaulted). No component retries, assumes an
        outcome, flattens, or invents a terminal state (DEC-0137).
        """
        prepared = _prepare(command, receive_instant)
        if isinstance(prepared, TypedRefusal):
            return prepared
        resolved_command, fp, instant = prepared
        resolved_trigger = _coerce(UnknownTrigger, trigger)
        if resolved_trigger is None:
            return _invalid(
                "trigger",
                "an UNKNOWN trigger is one of timeout | transport-error | disconnect",
                given=repr(trigger),
                allowed=[member.value for member in UnknownTrigger],
            )
        if not isinstance(monotonic_elapsed, Duration):
            return _invalid(
                "monotonic_elapsed",
                "the elapsed measurement backing an UNKNOWN is a boot-scoped monotonic Duration, "
                "never a wall-computed span",
                given=repr(monotonic_elapsed),
            )
        if not isinstance(submission_deadline, Instant):
            return _invalid(
                "submission_deadline",
                "the submission deadline in force is a declared application-injected Instant "
                "under do-not-default; its existence is mandatory and its value is never QMF's",
                given=repr(submission_deadline),
            )
        observation = CommandObservation(
            command_fp1=fp,
            kind=resolved_command.kind,
            outcome=SubmissionOutcome.UNKNOWN,
            receive_instant=instant,
            unknown_trigger=resolved_trigger,
            monotonic_elapsed=monotonic_elapsed,
            submission_deadline=submission_deadline,
            detail="lost transport certainty before a final outcome; UNKNOWN is a state",
        )
        return _result(fp, resolved_command.kind, SubmissionOutcome.UNKNOWN, observation)


def _prepare(
    command: object, receive_instant: object
) -> tuple[Command, Fingerprint, Instant] | TypedRefusal:
    """Validate a submission's command and receive instant, returning the fp1 (CT-19)."""
    if not isinstance(command, Command):
        return _invalid("command", "an outcome resolves a typed Command", given=repr(command))
    if not isinstance(receive_instant, Instant):
        return _invalid(
            "receive_instant",
            "recording a wall receive instant is mandatory on every outcome observation",
            given=repr(receive_instant),
        )
    fp = command.fingerprint()
    if is_refusal(fp):  # pragma: no cover - a validly constructed command always fingerprints
        return fp
    return command, fp.value, receive_instant


def _result(
    command_fp1: Fingerprint,
    kind: CommandKind,
    outcome: SubmissionOutcome,
    observation: CommandObservation,
) -> Result[SubmissionResult]:
    """Assemble the submission result with its one observation and one journal event."""
    return Ok(
        SubmissionResult(
            command_fp1=command_fp1,
            kind=kind,
            outcome=outcome,
            observation=observation,
            journal_event=JournalEvent.for_outcome(command_fp1, kind, outcome),
        )
    )


# --- command identity binding -----------------------------------------------


def command_id_mapping_is_injective_total(declaration: object) -> Result[bool]:
    """Read whether the CT-18 command-id mapping is injective-and-total (CT-19; DEC-0138).

    Reads the static ``command_id_mapping`` capability's ``injective_total`` flag. When the
    mapping into the venue client-id field is injective-and-total the venue client id suffices
    alone; otherwise a durable command-id-binding record must persist before submission. A
    measured-at-connection or malformed declaration surfaces its own refusal.
    """
    if not isinstance(declaration, CapabilityDeclaration):
        return _invalid(
            "declaration",
            "the command-id mapping is declared on a CapabilityDeclaration",
            given=repr(declaration),
        )
    value = declaration.static_value(CapabilityFieldName.COMMAND_ID_MAPPING)
    if is_refusal(value):
        return value
    mapping = value.value
    if not isinstance(mapping, Mapping):
        return _invalid(
            "command_id_mapping",
            "the command_id_mapping capability declares a mapping with an injective_total flag",
            given=repr(mapping),
        )
    flag = cast("Mapping[str, object]", mapping).get("injective_total")
    if not isinstance(flag, bool):
        return _invalid(
            "injective_total",
            "the command_id_mapping declares injective_total as a boolean",
            given=repr(flag),
        )
    return Ok(flag)


class BindingOutcome(StrEnum):
    """The outcome of preparing a command-id binding before submission (CT-19; DEC-0137)."""

    MAPPING_INJECTIVE_TOTAL = "mapping-injective-total"
    BOUND = "bound"
    IDEMPOTENT = "idempotent"


@dataclass(frozen=True, slots=True)
class CommandIdBinding:
    """A durable ``(venue client id, command fp1, account, session epoch)`` binding (CT-19).

    Persisted through the injected :class:`~qmf.core.RecordSink` **before** submission when
    the CT-18 mapping into the venue client-id field is not injective-and-total, so the local
    side can detect a reused venue client id carrying differing content (DEC-0137, DEC-0138).
    """

    venue_client_id: str
    command_fp1: Fingerprint
    account_id: str
    session_epoch: str

    def fp1_identity(self) -> dict[str, object]:
        """The binding's canonical identity content (CT-19; DEC-0108)."""
        return {
            "class": "command-id-binding",
            "venue_client_id": self.venue_client_id,
            "command_fp1": self.command_fp1.value,
            "account_id": self.account_id,
            "session_epoch": self.session_epoch,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


class CommandIdBindingRegistry:
    """Durable command-id bindings with idempotency and collision detection (CT-19).

    Constructed through :meth:`try_create` from a composition-root-injected
    :class:`~qmf.core.RecordSink`. When the CT-18 mapping is **not** injective-and-total,
    :meth:`bind_before_submission` persists a :class:`CommandIdBinding` through the sink
    **before** submission; a storage failure is surfaced (never swallowed) and the command is
    not submitted. Re-presenting the same command (same fp1) under the same venue client id is
    an **idempotent accept**; differing content (a different fp1) under a reused venue client
    id is a **true collision** — refused and alarmed, never overwritten. Idempotency and
    collision tests run against the full local fingerprint, never the venue-side id (DEC-0137,
    DEC-0138).

    Deliberately not a frozen value: it owns the mutable binding table for its stream, following
    one-writer-per-stream (DEC-0113).
    """

    __slots__ = ("_bindings", "_record_sink")

    _record_sink: RecordSink[object]
    _bindings: dict[str, CommandIdBinding]

    def __init__(self, record_sink: RecordSink[object]) -> None:
        # Unchecked trusted-internal constructor; callers use try_create.
        self._record_sink = record_sink
        self._bindings = {}

    @classmethod
    def try_create(cls, record_sink: object) -> Result[CommandIdBindingRegistry]:
        """Validate the injected sink and build a registry, returning value-or-refusal."""
        if not isinstance(record_sink, RecordSink):
            return _invalid(
                "record_sink",
                "the composition root injects a RecordSink for durable command-id bindings",
                given=repr(record_sink),
            )
        return Ok(cls(cast("RecordSink[object]", record_sink)))

    def binding_for(self, venue_client_id: object) -> CommandIdBinding | None:
        """The durable binding recorded for a venue client id, or ``None`` (a safe read)."""
        if not isinstance(venue_client_id, str):
            return None
        return self._bindings.get(venue_client_id)

    def bind_before_submission(
        self, command: object, *, venue_client_id: object, injective_total: object
    ) -> Result[BindingOutcome]:
        """Prepare the durable command-id binding a submission needs (CT-19; DEC-0137).

        When ``injective_total`` is ``True`` the venue client id suffices alone and no binding
        is persisted — :data:`BindingOutcome.MAPPING_INJECTIVE_TOTAL`. Otherwise a durable
        binding is required before submission: an unseen venue client id persists a
        :class:`CommandIdBinding` through the injected sink (a storage failure is surfaced and
        the command is **not** submitted) and returns :data:`BindingOutcome.BOUND`; the same
        command re-presented returns :data:`BindingOutcome.IDEMPOTENT`; and differing content
        under a reused venue client id is refused and **alarmed** as a true collision.
        """
        if not isinstance(command, Command):
            return _invalid(
                "command", "a binding is prepared for a typed Command", given=repr(command)
            )
        if not isinstance(injective_total, bool):
            return _invalid(
                "injective_total",
                "the CT-18 mapping's injective-and-total flag is a boolean the caller resolves",
                given=repr(injective_total),
            )
        if injective_total:
            return Ok(BindingOutcome.MAPPING_INJECTIVE_TOTAL)
        client_id = _clean_str(venue_client_id)
        if client_id is None:
            return _invalid(
                "venue_client_id",
                "a non-injective mapping binds through the venue client-id field, a token",
                given=repr(venue_client_id),
            )
        fp = command.fingerprint()
        if is_refusal(fp):  # pragma: no cover - a validly constructed command always fingerprints
            return fp
        command_fp1 = fp.value
        existing = self._bindings.get(client_id)
        if existing is not None:
            if existing.command_fp1 == command_fp1:
                return Ok(BindingOutcome.IDEMPOTENT)
            return _collision(
                "command_id_binding",
                "differing content under a reused venue client-id identity is a true collision; "
                "refused and alarmed, never overwritten (idempotency runs against the full local "
                "fingerprint, never the venue-side id)",
                venue_client_id=client_id,
                existing_command_fp1=existing.command_fp1.value,
                presented_command_fp1=command_fp1.value,
            )
        binding = CommandIdBinding(
            venue_client_id=client_id,
            command_fp1=command_fp1,
            account_id=command.account.account_id,
            session_epoch=command.session_epoch,
        )
        persisted = self._record_sink.write(binding)
        if is_refusal(persisted):
            # The durable binding did not land, so the command is NOT submitted; the failure
            # is surfaced, never swallowed (block-on-unpersistable; AR-47, FM-2).
            return persisted
        self._bindings[client_id] = binding
        return Ok(BindingOutcome.BOUND)


# --- compound commands ------------------------------------------------------


def derive_child_identity(parent_fp1: object, ordinal: object) -> Result[Fingerprint]:
    """Derive a compound child's identity from ``parent fp1 + declared ordinal`` (CT-19).

    Each child of a compound command carries a derived identity so it is individually
    observation- and journal-bearing, distinct from its siblings and its parent (DEC-0137).
    """
    if not isinstance(parent_fp1, Fingerprint):
        return _invalid(
            "parent_fp1",
            "a compound child derives from the parent command's fp1",
            given=repr(parent_fp1),
        )
    resolved_ordinal = _as_ordinal(ordinal)
    if resolved_ordinal is None:
        return _invalid(
            "ordinal",
            "a compound child carries a non-negative declared ordinal",
            given=repr(ordinal),
        )
    return fingerprint(
        {
            "class": "compound-child",
            "parent_fp1": parent_fp1.value,
            "ordinal": resolved_ordinal,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
    )


def meet_outcomes(child_outcomes: object) -> Result[SubmissionOutcome]:
    """The meet of a compound command's child outcomes (CT-19; DEC-0137, DEC-0140).

    Given the resolved outcomes of a compound command's children (each a single-submission
    four-outcome-law outcome), the parent's outcome is the **meet**: any child ``UNKNOWN``
    makes the parent ``UNKNOWN``; otherwise, if any child is a non-success
    (``rejected-by-venue`` or ``denied-locally``) the parent is ``partially-executed`` — a
    named outcome that is **never a success**; and only when every child is
    ``accepted-by-venue`` is the parent ``accepted-by-venue``. An empty set of children, or a
    child that is not a single-submission outcome, is an ``invalid input`` refusal.
    """
    if isinstance(child_outcomes, (str, bytes)) or not isinstance(child_outcomes, Sequence):
        return _invalid(
            "child_outcomes",
            "a compound outcome is the meet of a sequence of child outcomes",
            given=repr(child_outcomes),
        )
    outcomes = cast("Sequence[object]", child_outcomes)
    if len(outcomes) == 0:
        return _invalid("child_outcomes", "a compound command has at least one child outcome")
    resolved: list[SubmissionOutcome] = []
    for index, item in enumerate(outcomes):
        outcome = _coerce(SubmissionOutcome, item)
        if outcome is None or outcome not in FOUR_OUTCOME_LAW:
            return _invalid(
                "child_outcomes",
                "each child is a single-submission four-outcome-law outcome",
                index=index,
                given=repr(item),
                allowed=[member.value for member in FOUR_OUTCOME_LAW],
            )
        resolved.append(outcome)
    if any(outcome is SubmissionOutcome.UNKNOWN for outcome in resolved):
        return Ok(SubmissionOutcome.UNKNOWN)
    if all(outcome is SubmissionOutcome.ACCEPTED_BY_VENUE for outcome in resolved):
        return Ok(SubmissionOutcome.ACCEPTED_BY_VENUE)
    return Ok(SubmissionOutcome.PARTIALLY_EXECUTED)


@dataclass(frozen=True, slots=True)
class CompoundChild:
    """One child of a compound command: its declared ordinal and derived identity (CT-19)."""

    ordinal: int
    identity: Fingerprint


@dataclass(frozen=True, slots=True)
class CompoundCommand:
    """A command fanning out to N venue submissions (CT-19; DEC-0137, DEC-0140).

    Each child carries a **derived identity** (parent fp1 + declared ordinal) and is
    individually observation- and journal-bearing; the parent's outcome is the **meet** of
    its children (:meth:`parent_outcome`). Built through :meth:`fan_out` from a parent
    :class:`Command` and the declared child ordinals.
    """

    parent_fp1: Fingerprint
    children: tuple[CompoundChild, ...]

    @classmethod
    def fan_out(cls, parent: object, ordinals: object) -> Result[CompoundCommand]:
        """Build a compound command from a parent command and its child ordinals (CT-19).

        The parent must be a typed :class:`Command`; ``ordinals`` a sequence of at least two
        distinct non-negative integers (a fan-out is to more than one submission). Each child
        identity is derived from the parent fp1 and its ordinal.
        """
        if not isinstance(parent, Command):
            return _invalid(
                "parent", "a compound command fans out from a typed Command", given=repr(parent)
            )
        parent_fp = parent.fingerprint()
        if is_refusal(parent_fp):  # pragma: no cover - a valid command always fingerprints
            return parent_fp
        if isinstance(ordinals, (str, bytes)) or not isinstance(ordinals, Sequence):
            return _invalid(
                "ordinals",
                "the child ordinals are a sequence of non-negative integers",
                given=repr(ordinals),
            )
        ordinal_seq = cast("Sequence[object]", ordinals)
        if len(ordinal_seq) < 2:
            return _invalid(
                "ordinals",
                "a compound command fans out to at least two submissions; a single submission is "
                "not compound",
                count=len(ordinal_seq),
            )
        seen: set[int] = set()
        children: list[CompoundChild] = []
        for item in ordinal_seq:
            resolved_ordinal = _as_ordinal(item)
            if resolved_ordinal is None:
                return _invalid(
                    "ordinals", "each child ordinal is a non-negative integer", given=repr(item)
                )
            if resolved_ordinal in seen:
                return _invalid(
                    "ordinals",
                    "child ordinals are distinct within one fan-out",
                    ordinal=resolved_ordinal,
                )
            seen.add(resolved_ordinal)
            identity = derive_child_identity(parent_fp.value, resolved_ordinal)
            if is_refusal(identity):  # pragma: no cover - validated ordinal always derives
                return identity
            children.append(CompoundChild(ordinal=resolved_ordinal, identity=identity.value))
        return Ok(cls(parent_fp1=parent_fp.value, children=tuple(children)))

    def parent_outcome(self, child_outcomes: object) -> Result[SubmissionOutcome]:
        """The parent's outcome — the meet of its children (CT-19; DEC-0137).

        The child outcomes must be one per child, in child order; the meet then applies
        (any child ``UNKNOWN`` → ``UNKNOWN``; any non-success → ``partially-executed``; all
        accepted → ``accepted-by-venue``).
        """
        if isinstance(child_outcomes, (str, bytes)) or not isinstance(child_outcomes, Sequence):
            return _invalid(
                "child_outcomes",
                "the parent outcome is the meet of one outcome per child",
                given=repr(child_outcomes),
            )
        outcomes = cast("Sequence[object]", child_outcomes)
        if len(outcomes) != len(self.children):
            return _invalid(
                "child_outcomes",
                "a compound command's parent outcome needs exactly one outcome per child",
                children=len(self.children),
                given=len(outcomes),
            )
        return meet_outcomes(outcomes)
