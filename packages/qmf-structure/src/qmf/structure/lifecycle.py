"""CT-17 — the append-only lifecycle: confirmation, invalidation, interaction, and the
read-time state fold (COMP-QMF-STRUCTURE).

A minted :class:`~qmf.structure.StructureObject` is a **fact about the market at a time**
and is **never mutated afterward** (Story 9.1). Its state evolves **only** by appending
separate, typed, immutable lifecycle records — never by rewriting the object or an edge
(CT-17; DEC-0129, DEC-0114). This module (Story 9.2) pins down that append-only lifecycle
and the read-time resolution rule that turns a record stream into "current state".

**Three append-only lifecycle records, each an identity-bearing fact (DEC-0129,
DEC-0114).** :class:`ConfirmationRecord`, :class:`InvalidationRecord`, and
:class:`InteractionRecord` are separate frozen record kinds. Each references the object
**by its ``fp1`` fingerprint** and carries **its own instant as an identity field of its
own record** — so two confirmations of one object at two instants are two distinct facts
with two distinct fingerprints. An interaction additionally carries the price it occurred
at and the family-declared interaction measure; a confirmation may carry the ``confirmed
-as`` target of a distinct confirmed successor. Interaction records are the only permitted
way an object's state evolves: there is no in-place edit anywhere in this module.

**The read-time fold — "still valid at T" is never a stored field (DEC-0129).**
:func:`resolve_state` folds an object's append-only record stream to a knowledge time
``T`` per CT-17's read-resolution rule: a record participates only when its instant is at
or before ``T`` (equality is consumption, not look-ahead; DEC-0106), and the returned
:class:`ResolvedState` — ``confirmed``, ``invalidated``, ``still_valid``, the interaction
history — is **computed on read, never stored** on any object. The object carries no
``still_valid`` field by construction.

**No overwrite; a refit is a new artifact (FM-3; DEC-0129, DEC-0114).** :func:`refit`
mints a **new** :class:`~qmf.structure.StructureObject` with its anchors frozen at the new
fit and emits a ``supersedes`` :class:`LifecycleEdge` from the new object to the prior
one. The lineage keeps the **first** observed-at (:attr:`Refit.first_observed_at`); the
prior object and all earlier records are untouched immutable evidence. A correction is
never an in-place edit.

**Admission is a design-time gate (FM-2; DEC-0129, DEC-0132, DEC-0133).**
:func:`admit_to_governed_library` admits a family to the governed library only when its
confirmation rule states "confirmed the moment X happens" — the decidable proxy is a
present, non-blank descriptor; clock-confirmed (degenerate) confirmation is legal. An
imprecise concept produces no :class:`~qmf.structure.ConfirmationRule` and so is never
admitted; it stays freely usable in the ungoverned research lane.

**Invalidation never cascades automatically (DEC-0129, DEC-0114).** :func:`resolve_state`
folds one object's own records and never follows lineage. A family may declare an
:class:`InvalidationPredicate` referencing a parent's lifecycle facts, and a reader may
call :func:`resolve_cascade` to compute cascade **at read time** from that predicate over
the parent's resolved state — an explicit, opt-in, reader-driven derivation, never an
automatic side effect of a parent's invalidation.

Default-deny holds: this module imports **only** ``qmf.core`` (every ``fp1`` fingerprint
is computed there, nowhere else). Records and edges are returned as **fingerprintable
content**, never stamped records — they carry no ``WriterId`` and no per-writer sequence;
the composition root mints the CT-06 records and CT-07 edges (DEC-0120, DEC-0129). Public
value types are frozen dataclasses, the family/predicate seams are ``typing.Protocol``s,
and every operation succeeds or RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain
failure is never raised across the boundary (DEC-0101, DEC-0109, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast, runtime_checkable

from qmf.core import (
    ExactRational,
    Fingerprint,
    Instant,
    Ok,
    Price,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.structure.objects import (
    CONTRACT_FORMAT_VERSION,
    ConfirmationRule,
    DeclaredFamily,
    StructureFamily,
    StructureObject,
)

__all__ = [
    "CascadeResolution",
    "ConfirmationRecord",
    "InteractionRecord",
    "InvalidationPredicate",
    "InvalidationRecord",
    "LifecycleEdge",
    "LifecycleEdgeKind",
    "LifecycleRecord",
    "Refit",
    "ResolvedState",
    "admit_to_governed_library",
    "refit",
    "resolve_cascade",
    "resolve_state",
]


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a lifecycle operation returns (FM-1).

    ``retryability`` is ``no`` — a malformed reference, a record whose instant precedes
    the object's observation, or a foreign record folded into the wrong object's stream is
    a caller/wiring mistake, not a transient condition — and ``context`` always names the
    offending ``field`` and a human-legible ``reason`` (returned, never raised; CT-04;
    DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal the FM-2 admission gate returns (CT-17;
    DEC-0129, DEC-0132).

    A concept whose confirmation rule cannot state "confirmed the moment X happens" is not
    *malformed* — it is a well-formed thing the governed library declines to admit — so it
    is a policy rejection, and the concept stays freely usable in the ungoverned research
    lane (FM-2). ``retryability`` is ``no``: admission succeeds only once the rule is
    stated precisely, which is a new family, not a retry of this one.
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


# --- coercion helpers -------------------------------------------------------


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string,
    or ``None`` — parsing goes through qmf-core, never a local hash. A record references
    its object by an ``fp1`` fingerprint; a mutable or minted id is never a reference."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None`` (a
    family-declared interaction measure name is opaque — never stripped, cased, or
    parsed)."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _as_confirmation_rule(value: object) -> ConfirmationRule | None:
    """Return ``value`` if it is a :class:`~qmf.structure.ConfirmationRule`, else ``None``.

    Takes ``object`` on purpose: a ``runtime_checkable`` Protocol's isinstance proves a
    member EXISTS but never its type, so a structurally-valid :class:`StructureFamily` may
    still hand back the wrong type — this check is real, not redundant.
    """
    return value if isinstance(value, ConfirmationRule) else None


def _predicate_result(
    predicate: InvalidationPredicate,
    *,
    parent: ResolvedState,
    child: ResolvedState,
    at: Instant,
) -> object:
    """Call a family's invalidation predicate, returning its result as ``object``.

    The declared return is ``object`` on purpose: the :class:`InvalidationPredicate` seam
    is duck-typed (``runtime_checkable``), so a predicate may return a non-``bool`` at
    runtime — :func:`resolve_cascade` guards that with a real ``isinstance`` check the
    ``object`` return keeps meaningful.
    """
    return predicate.cascades(parent=parent, child=child, at=at)


# --- the lifecycle edge intent ----------------------------------------------


class LifecycleEdgeKind(StrEnum):
    """The CT-17 lifecycle subset of the CT-07 lineage edge vocabulary (DEC-0131,
    DEC-0114).

    The values are the canonical hyphenated strings CT-07 pins, so an edge round-trips
    through its string form.

    * ``confirmation`` / ``invalidation`` / ``interaction`` — an edge from the lifecycle
      record to the object whose ``fp1`` it references.
    * ``confirmed-as`` — an edge from an unconfirmed object to its confirmed successor.
    * ``supersedes`` — an edge from a refit's new artifact to the object it supersedes.

    This is deliberately a *subset*: qmf-structure never mints venue, risk, or promotion
    edges. The composition root stamps these intents into full CT-07 edges (adding the
    ``WriterId``); qmf-structure only names the kind and the two ``fp1`` endpoints.
    """

    CONFIRMATION = "confirmation"
    INVALIDATION = "invalidation"
    INTERACTION = "interaction"
    CONFIRMED_AS = "confirmed-as"
    SUPERSEDES = "supersedes"


@dataclass(frozen=True, slots=True)
class LifecycleEdge:
    """A CT-17 lifecycle lineage-edge *intent*: fingerprintable content, never a stamped
    edge (CT-17, CT-07; DEC-0131, DEC-0114, DEC-0120).

    ``kind`` is a :class:`LifecycleEdgeKind`; ``from_ref`` is the accruing/derived
    endpoint (the lifecycle record, or the refit's new artifact) and ``to_ref`` the
    referenced endpoint (the object, or the superseded/confirmed successor) — both
    :class:`~qmf.core.Fingerprint`\\ s, never a mutable or minted id. It carries **no**
    ``WriterId``: the composition root holds the writer and the gapless per-(writer, kind)
    sequence and mints the full CT-07 :class:`~qmf.registry.LineageEdge`; this library only
    describes the edge to be minted. Its fingerprint is **derived** from its content.
    """

    kind: LifecycleEdgeKind
    from_ref: Fingerprint
    to_ref: Fingerprint

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this lifecycle edge intent.

        The ``class`` tag keeps this intent's fingerprint disjoint from the composition
        root's stamped CT-07 edge (which additionally carries the writer), so the two are
        never confused: the library's content and the stamped record are distinct
        artifacts by construction.
        """
        return {
            "class": "structure-lifecycle-edge",
            "kind": self.kind.value,
            "from_ref": self.from_ref.value,
            "to_ref": self.to_ref.value,
            "format_version": CONTRACT_FORMAT_VERSION,
        }

    def content_fingerprint(self) -> Result[Fingerprint]:
        """The edge intent's ``fp1`` fingerprint, computed in qmf-core (DEC-0108)."""
        return fingerprint(self.fp1_identity())


# --- the append-only lifecycle records --------------------------------------


@dataclass(frozen=True, slots=True)
class ConfirmationRecord:
    """An append-only confirmation fact: the object was confirmed at ``at`` (CT-17;
    DEC-0129, DEC-0131, DEC-0114).

    ``object_ref`` is the confirmed object's ``fp1`` fingerprint; ``at`` is the
    confirmation instant and is an **identity field of this record**. ``confirmed_as`` is
    the optional ``fp1`` of a *distinct* confirmed successor object — present only when the
    confirmation supersedes an earlier unconfirmed output with a new confirmed artifact
    (the ``confirmed-as`` edge target), absent otherwise. The record is immutable and
    carries no writer or sequence; the composition root mints the CT-06 record.
    """

    object_ref: Fingerprint
    at: Instant
    confirmed_as: Fingerprint | None

    @classmethod
    def try_create(
        cls, object_ref: object, at: object, *, confirmed_as: object = None
    ) -> Result[ConfirmationRecord]:
        """Validate and build a :class:`ConfirmationRecord`, returning value-or-refusal.

        ``object_ref`` must be an ``fp1`` fingerprint (or its string), ``at`` an
        :class:`~qmf.core.Instant`, and ``confirmed_as`` — if present — an ``fp1``
        fingerprint of a successor *distinct* from ``object_ref`` (a confirmed-as edge
        cannot point an object at itself).
        """
        ref = _coerce_fingerprint(object_ref)
        if ref is None:
            return _invalid(
                "object_ref",
                "a confirmation record references its object by an fp1 fingerprint",
                given=repr(object_ref),
            )
        if not isinstance(at, Instant):
            return _invalid(
                "at",
                "a confirmation instant is an Instant and is an identity field of the record",
                given=repr(at),
            )
        successor: Fingerprint | None = None
        if confirmed_as is not None:
            successor = _coerce_fingerprint(confirmed_as)
            if successor is None:
                return _invalid(
                    "confirmed_as",
                    "the confirmed-as target is an fp1 fingerprint of the confirmed successor",
                    given=repr(confirmed_as),
                )
            if successor == ref:
                return _invalid(
                    "confirmed_as",
                    "a confirmed-as edge cannot point an object at itself; the successor "
                    "is a distinct confirmed artifact",
                    object_ref=ref.value,
                )
        return Ok(cls(object_ref=ref, at=at, confirmed_as=successor))

    @property
    def edge_kind(self) -> LifecycleEdgeKind:
        """The lineage edge kind this record accrues — ``confirmation``."""
        return LifecycleEdgeKind.CONFIRMATION

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — every part is identity.

        ``confirmed_as`` is included **only** when present: ``None`` never enters identity
        content (fp1 prohibits null; an absent value is an omitted key), so a plain
        confirmation and a confirmation-with-successor fingerprint differently.
        """
        content: dict[str, object] = {
            "class": "confirmation-record",
            "object_ref": self.object_ref.value,
            "at": self.at.value_ns,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.confirmed_as is not None:
            content["confirmed_as"] = self.confirmed_as.value
        return content

    def content_fingerprint(self) -> Result[Fingerprint]:
        """The record's ``fp1`` fingerprint, computed in qmf-core (DEC-0108)."""
        return fingerprint(self.fp1_identity())

    def lineage_edges(self) -> Result[tuple[LifecycleEdge, ...]]:
        """The CT-07 edge intents this record accrues (fingerprintable content).

        Always a ``confirmation`` edge from this record to its object; plus, when
        ``confirmed_as`` is present, a ``confirmed-as`` edge from the (unconfirmed) object
        to its confirmed successor. Returns value-or-refusal — a refusal here signals an
        upstream programmer bug, as the identity content is canonical by construction.
        """
        record_fp = self.content_fingerprint()
        if is_refusal(record_fp):  # pragma: no cover - identity is canonical by construction
            return record_fp
        edges: list[LifecycleEdge] = [
            LifecycleEdge(
                kind=LifecycleEdgeKind.CONFIRMATION,
                from_ref=record_fp.value,
                to_ref=self.object_ref,
            )
        ]
        if self.confirmed_as is not None:
            edges.append(
                LifecycleEdge(
                    kind=LifecycleEdgeKind.CONFIRMED_AS,
                    from_ref=self.object_ref,
                    to_ref=self.confirmed_as,
                )
            )
        return Ok(tuple(edges))


@dataclass(frozen=True, slots=True)
class InvalidationRecord:
    """An append-only invalidation fact: the object was detected invalid at ``at`` (CT-17;
    DEC-0129, DEC-0114).

    ``object_ref`` is the object's ``fp1`` fingerprint and ``at`` is the **detection
    instant** — known-at, an identity field of this record, never a placeholder. An object
    may be invalidated whether or not it was ever confirmed. The record is immutable and
    carries no writer or sequence.
    """

    object_ref: Fingerprint
    at: Instant

    @classmethod
    def try_create(cls, object_ref: object, at: object) -> Result[InvalidationRecord]:
        """Validate and build an :class:`InvalidationRecord`, returning value-or-refusal."""
        ref = _coerce_fingerprint(object_ref)
        if ref is None:
            return _invalid(
                "object_ref",
                "an invalidation record references its object by an fp1 fingerprint",
                given=repr(object_ref),
            )
        if not isinstance(at, Instant):
            return _invalid(
                "at",
                "an invalidation detection instant is an Instant and is an identity field "
                "of the record",
                given=repr(at),
            )
        return Ok(cls(object_ref=ref, at=at))

    @property
    def edge_kind(self) -> LifecycleEdgeKind:
        """The lineage edge kind this record accrues — ``invalidation``."""
        return LifecycleEdgeKind.INVALIDATION

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — every part is identity."""
        return {
            "class": "invalidation-record",
            "object_ref": self.object_ref.value,
            "at": self.at.value_ns,
            "format_version": CONTRACT_FORMAT_VERSION,
        }

    def content_fingerprint(self) -> Result[Fingerprint]:
        """The record's ``fp1`` fingerprint, computed in qmf-core (DEC-0108)."""
        return fingerprint(self.fp1_identity())

    def lineage_edge(self) -> Result[LifecycleEdge]:
        """The ``invalidation`` CT-07 edge intent from this record to its object."""
        record_fp = self.content_fingerprint()
        if is_refusal(record_fp):  # pragma: no cover - identity is canonical by construction
            return record_fp
        return Ok(
            LifecycleEdge(
                kind=LifecycleEdgeKind.INVALIDATION,
                from_ref=record_fp.value,
                to_ref=self.object_ref,
            )
        )


@dataclass(frozen=True, slots=True)
class InteractionRecord:
    """An append-only interaction fact — the only permitted way an object's state evolves
    (CT-17; DEC-0129, DEC-0114).

    ``object_ref`` is the object's ``fp1`` fingerprint; ``at`` is the interaction instant
    (an identity field of this record); ``price`` is the exact :class:`~qmf.core.Price` the
    interaction occurred at; and ``measure`` (an opaque, family-declared name) plus
    ``magnitude`` (an exact :class:`~qmf.core.ExactRational`) carry the family-declared
    interaction measure. No binary float ever reaches the money path — the price is a
    scaled integer and the magnitude an exact rational. The record is immutable and
    carries no writer or sequence.
    """

    object_ref: Fingerprint
    at: Instant
    price: Price
    measure: str
    magnitude: ExactRational

    @classmethod
    def try_create(
        cls, object_ref: object, at: object, price: object, measure: object, magnitude: object
    ) -> Result[InteractionRecord]:
        """Validate and build an :class:`InteractionRecord`, returning value-or-refusal.

        ``object_ref`` is an ``fp1`` fingerprint, ``at`` an :class:`~qmf.core.Instant`,
        ``price`` a :class:`~qmf.core.Price` (a scaled integer, never a binary float),
        ``measure`` a non-blank family-declared measure name, and ``magnitude`` an
        :class:`~qmf.core.ExactRational` (exact rationals only on the money path).
        """
        ref = _coerce_fingerprint(object_ref)
        if ref is None:
            return _invalid(
                "object_ref",
                "an interaction record references its object by an fp1 fingerprint",
                given=repr(object_ref),
            )
        if not isinstance(at, Instant):
            return _invalid(
                "at",
                "an interaction instant is an Instant and is an identity field of the record",
                given=repr(at),
            )
        if not isinstance(price, Price):
            return _invalid(
                "price",
                "an interaction price is an exact Price (a scaled integer; a binary float "
                "never enters the money path)",
                given=repr(price),
            )
        name = _clean_str(measure)
        if name is None:
            return _invalid(
                "measure",
                "the family-declared interaction measure name is a non-empty opaque token",
                given=repr(measure),
            )
        if not isinstance(magnitude, ExactRational):
            return _invalid(
                "magnitude",
                "the interaction measure magnitude is an ExactRational (exact rationals "
                "only, never a binary float on the money path)",
                given=repr(magnitude),
            )
        return Ok(cls(object_ref=ref, at=at, price=price, measure=name, magnitude=magnitude))

    @property
    def edge_kind(self) -> LifecycleEdgeKind:
        """The lineage edge kind this record accrues — ``interaction``."""
        return LifecycleEdgeKind.INTERACTION

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — every part is identity."""
        return {
            "class": "interaction-record",
            "object_ref": self.object_ref.value,
            "at": self.at.value_ns,
            "price": self.price.fp1_identity(),
            "measure": self.measure,
            "magnitude": self.magnitude.fp1_identity(),
            "format_version": CONTRACT_FORMAT_VERSION,
        }

    def content_fingerprint(self) -> Result[Fingerprint]:
        """The record's ``fp1`` fingerprint, computed in qmf-core (DEC-0108)."""
        return fingerprint(self.fp1_identity())

    def lineage_edge(self) -> Result[LifecycleEdge]:
        """The ``interaction`` CT-07 edge intent from this record to its object."""
        record_fp = self.content_fingerprint()
        if is_refusal(record_fp):  # pragma: no cover - identity is canonical by construction
            return record_fp
        return Ok(
            LifecycleEdge(
                kind=LifecycleEdgeKind.INTERACTION,
                from_ref=record_fp.value,
                to_ref=self.object_ref,
            )
        )


# The append-only lifecycle record kinds a reader folds into current state.
LifecycleRecord = ConfirmationRecord | InvalidationRecord | InteractionRecord


# --- the read-time state fold -----------------------------------------------


@dataclass(frozen=True, slots=True)
class ResolvedState:
    """The state of a structure object resolved **at read time** to a knowledge time
    (CT-17; DEC-0129).

    This is the value :func:`resolve_state` computes on read — it is **never a stored
    field** of any object. ``as_of`` is the knowledge time ``T`` it was resolved to;
    ``exists`` is whether the object was observed by ``T``; ``confirmed`` /
    ``confirmed_at`` reflect the earliest confirmation at or before ``T``; ``invalidated``
    / ``invalidated_at`` the earliest invalidation at or before ``T``; ``still_valid`` is
    ``exists and not invalidated`` (an observed object not yet invalidated by ``T``); and
    ``interactions`` is the object's interaction history at or before ``T``, in instant
    order. Nothing here follows lineage — cascade is a separate, opt-in read
    (:func:`resolve_cascade`).
    """

    object_ref: Fingerprint
    as_of: Instant
    exists: bool
    confirmed: bool
    confirmed_at: Instant | None
    invalidated: bool
    invalidated_at: Instant | None
    still_valid: bool
    interactions: tuple[InteractionRecord, ...]


def _coerce_records(value: object) -> tuple[LifecycleRecord, ...] | TypedRefusal:
    """Resolve the record stream to a tuple of lifecycle records, or refuse.

    A bare string or bytes is refused — it is not a sequence of records — and every
    element must be one of the three lifecycle record kinds. An empty stream is legal (an
    object with no lifecycle yet).
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "records",
            "the record stream is a sequence of lifecycle records (a bare string is not a "
            "sequence of records)",
            given=repr(value),
        )
    resolved: list[LifecycleRecord] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, (ConfirmationRecord, InvalidationRecord, InteractionRecord)):
            return _invalid(
                "records",
                "each element is a ConfirmationRecord, InvalidationRecord, or InteractionRecord",
                index=index,
                given=repr(item),
            )
        resolved.append(item)
    return tuple(resolved)


def resolve_state(obj: object, records: object, *, at: object) -> Result[ResolvedState]:
    """Fold an object's append-only record stream to a knowledge time, returning
    value-or-refusal (CT-17's read-resolution rule; DEC-0129, DEC-0106).

    ``obj`` is the :class:`~qmf.structure.StructureObject`; ``records`` its append-only
    stream of :class:`ConfirmationRecord` / :class:`InvalidationRecord` /
    :class:`InteractionRecord`; and ``at`` the knowledge time ``T`` (an
    :class:`~qmf.core.Instant`). Only records whose instant is **at or before** ``T``
    participate — equality is consumption, not look-ahead — so a read at an earlier ``T``
    can never see a later lifecycle fact.

    Every record must reference **this** object's ``fp1`` (a foreign record folded into the
    wrong object's stream is an ``invalid input`` refusal) and every record's instant must
    be at or after the object's ``observed_at`` (a lifecycle fact before the object was
    observed is causally impossible — the interim look-ahead guard, FM-1). The returned
    :class:`ResolvedState` is computed here and **never stored**: "still valid at T" is a
    read-time fold, not a field.
    """
    if not isinstance(obj, StructureObject):
        return _invalid("obj", "the state fold resolves a StructureObject", given=repr(obj))
    if not isinstance(at, Instant):
        return _invalid("at", "the knowledge time T is an Instant", given=repr(at))
    object_fp = obj.content_fingerprint()
    if is_refusal(object_fp):  # pragma: no cover - identity is canonical by construction
        return object_fp
    ref = object_fp.value
    resolved_records = _coerce_records(records)
    if isinstance(resolved_records, TypedRefusal):
        return resolved_records

    for index, record in enumerate(resolved_records):
        if record.object_ref != ref:
            return _invalid(
                "records",
                "a record in the stream references a different object; a fold is over one "
                "object's own edge stream",
                index=index,
                object_ref=ref,
                record_ref=record.object_ref.value,
            )
        if record.at.value_ns < obj.observed_at.value_ns:
            return _invalid(
                "records",
                "a lifecycle record's instant precedes the object's observed_at; a "
                "lifecycle fact is never earlier than the observation it accrues to (FM-1)",
                index=index,
                observed_at=obj.observed_at.value_ns,
                record_at=record.at.value_ns,
            )

    horizon = at.value_ns
    confirmations: list[Instant] = []
    invalidations: list[Instant] = []
    interactions: list[InteractionRecord] = []
    for record in resolved_records:
        if record.at.value_ns > horizon:
            continue  # not yet known at T — the look-ahead-safe read
        if isinstance(record, ConfirmationRecord):
            confirmations.append(record.at)
        elif isinstance(record, InvalidationRecord):
            invalidations.append(record.at)
        else:
            interactions.append(record)

    exists = obj.observed_at.value_ns <= horizon
    confirmed_at = min(confirmations, key=lambda i: i.value_ns) if confirmations else None
    invalidated_at = min(invalidations, key=lambda i: i.value_ns) if invalidations else None
    ordered_interactions = tuple(sorted(interactions, key=lambda r: r.at.value_ns))
    return Ok(
        ResolvedState(
            object_ref=object_fp.value,
            as_of=at,
            exists=exists,
            confirmed=confirmed_at is not None,
            confirmed_at=confirmed_at,
            invalidated=invalidated_at is not None,
            invalidated_at=invalidated_at,
            still_valid=exists and invalidated_at is None,
            interactions=ordered_interactions,
        )
    )


# --- refit: a new artifact with a supersedes edge (FM-3) --------------------


@dataclass(frozen=True, slots=True)
class Refit:
    """The result of a refit: a new artifact plus its ``supersedes`` edge intent (CT-17,
    FM-3; DEC-0129, DEC-0114).

    ``superseding`` is the newly-minted :class:`~qmf.structure.StructureObject`, its
    anchors frozen at the new fit; ``superseded_ref`` is the prior object's ``fp1``;
    ``supersedes_edge`` is the ``supersedes`` :class:`LifecycleEdge` intent from the new
    object to the prior one; and ``first_observed_at`` is the lineage's **first**
    observed-at, kept across the chain (never rewritten). The prior object and every
    earlier record are untouched immutable evidence — a refit appends, never overwrites.
    """

    superseding: StructureObject
    superseded_ref: Fingerprint
    supersedes_edge: LifecycleEdge
    first_observed_at: Instant


def refit(
    prior: object,
    *,
    anchor: object,
    observed_at: object,
    parameters: object = None,
    evidence_class: object = None,
    consumed_input_times: object = (),
    first_observed_at: object = None,
) -> Result[Refit]:
    """Refit a prior object: mint a new artifact and emit a ``supersedes`` edge (FM-3;
    DEC-0129, DEC-0114).

    A correction, refit, or state change that would overwrite an object or an edge is
    prohibited: this instead mints a **new** :class:`~qmf.structure.StructureObject` of the
    **same family** as ``prior`` (identity + version + confirmation rule carried over),
    with its ``anchor`` frozen at the new fit and its own ``observed_at`` — the new mint
    runs the full emission invariant (FM-1). ``parameters`` and ``evidence_class`` default
    to the prior object's when omitted. The new observed-at must be at or after the prior
    object's observed-at (a refit is observed no earlier than what it supersedes), and
    ``first_observed_at`` (defaulting to the prior object's) is the lineage's first
    observed-at, which must not follow the new fit. The prior object stays untouched —
    earlier evidence remains.
    """
    if not isinstance(prior, StructureObject):
        return _invalid("prior", "a refit supersedes a prior StructureObject", given=repr(prior))
    if not isinstance(observed_at, Instant):
        return _invalid(
            "observed_at", "the refit's observed_at is an Instant", given=repr(observed_at)
        )
    if observed_at.value_ns < prior.observed_at.value_ns:
        return _invalid(
            "observed_at",
            "a refit is observed no earlier than the object it supersedes; the prior "
            "observed_at is retained as earlier evidence, never rewritten",
            prior_observed_at=prior.observed_at.value_ns,
            refit_observed_at=observed_at.value_ns,
        )
    origin = prior.observed_at if first_observed_at is None else first_observed_at
    if not isinstance(origin, Instant):
        return _invalid(
            "first_observed_at",
            "the lineage's first observed_at is an Instant",
            given=repr(first_observed_at),
        )
    if origin.value_ns > observed_at.value_ns:
        return _invalid(
            "first_observed_at",
            "the lineage's first observed_at cannot follow the refit it heads",
            first_observed_at=origin.value_ns,
            refit_observed_at=observed_at.value_ns,
        )

    prior_fp = prior.content_fingerprint()
    if is_refusal(prior_fp):  # pragma: no cover - identity is canonical by construction
        return prior_fp

    family = _rebuild_family(prior.family, prior.confirmation_rule)
    if isinstance(family, TypedRefusal):  # pragma: no cover - prior parts are valid by construction
        return family
    minted = StructureObject.try_create(
        family,
        prior.parameters if parameters is None else parameters,
        anchor,
        observed_at,
        prior.evidence_class if evidence_class is None else evidence_class,
        consumed_input_times=consumed_input_times,
    )
    if is_refusal(minted):
        return minted
    new_fp = minted.value.content_fingerprint()
    if is_refusal(new_fp):  # pragma: no cover - identity is canonical by construction
        return new_fp
    if new_fp.value == prior_fp.value:
        return _invalid(
            "anchor",
            "a refit must differ from the object it supersedes; an identical fit is the "
            "same fact, not a new artifact (change the anchor, parameters, or observed_at)",
            object_ref=prior_fp.value,
        )
    edge = LifecycleEdge(
        kind=LifecycleEdgeKind.SUPERSEDES,
        from_ref=new_fp.value,
        to_ref=prior_fp.value,
    )
    return Ok(
        Refit(
            superseding=minted.value,
            superseded_ref=prior_fp.value,
            supersedes_edge=edge,
            first_observed_at=origin,
        )
    )


def _rebuild_family(identity: object, rule: object) -> DeclaredFamily | TypedRefusal:
    """Rebuild the prior object's family from its identity and confirmation rule.

    A :class:`~qmf.structure.StructureObject` carries its family's identity and rule as
    fields; a refit is the same family, so the reference :class:`DeclaredFamily` is
    reconstructed from them to mint the superseding artifact.
    """
    built = DeclaredFamily.try_create(identity, rule)
    if is_refusal(built):  # pragma: no cover - prior object parts are valid by construction
        return built
    return built.value


# --- FM-2: admission to the governed library --------------------------------


def admit_to_governed_library(family: object) -> Result[StructureFamily]:
    """Admit a family to the governed library, or refuse it into the research lane (FM-2;
    DEC-0129, DEC-0132, DEC-0133).

    A family ships into the governed library only when its confirmation rule states
    "confirmed the moment X happens" with X knowable at that instant. The decidable proxy
    is a **present, non-blank descriptor**; clock-confirmed (degenerate) confirmation is
    legal (a non-blank descriptor with ``clock_confirmed = True``). An imprecise concept
    produces no :class:`~qmf.structure.ConfirmationRule` in the first place — so it is
    never even offered here — and stays **freely usable in the ungoverned research lane**;
    a family hand-built with a blank descriptor is turned away as a ``policy rejection``,
    not admitted. No seed candidate is privileged over an operator-authored family.

    Returns the family unchanged on admission, so a caller can write
    ``family = admit_to_governed_library(candidate).value`` at the governed boundary.
    """
    if not isinstance(family, StructureFamily):
        return _invalid(
            "family",
            "admission takes a StructureFamily (an identity and a confirmation rule)",
            given=repr(family),
        )
    rule = _as_confirmation_rule(family.confirmation_rule)
    if rule is None:
        return _invalid(
            "family",
            "the family's confirmation_rule is a ConfirmationRule",
            given=repr(family.confirmation_rule),
        )
    if _clean_str(rule.descriptor) is None:
        return _policy(
            "confirmation_rule",
            "a family is admitted to the governed library only when its confirmation rule "
            "states 'confirmed the moment X happens' with X knowable at that instant; an "
            "imprecise concept stays freely usable in the ungoverned research lane (FM-2)",
        )
    return Ok(family)


# --- AC #4: read-time cascade, never automatic ------------------------------


@runtime_checkable
class InvalidationPredicate(Protocol):
    """The ``typing.Protocol`` seam a family's invalidation predicate implements (CT-17;
    DEC-0129, DEC-0114).

    A family may declare an invalidation predicate that references a **parent's lifecycle
    facts** (its resolved state). Invalidation **never cascades automatically**: a reader
    who wants cascade calls :func:`resolve_cascade`, which evaluates this predicate at read
    time over the parent's :class:`ResolvedState`. Returning ``True`` means the child is
    cascade-invalidated at the read time ``at``; ``False`` leaves the child's own resolved
    state authoritative.
    """

    def cascades(
        self, *, parent: ResolvedState, child: ResolvedState, at: Instant
    ) -> bool:  # pragma: no cover - protocol seam
        """Whether the parent's lifecycle facts invalidate the child at knowledge time
        ``at``."""
        ...


@dataclass(frozen=True, slots=True)
class CascadeResolution:
    """A child's validity resolved **at read time**, optionally with parent cascade
    applied (CT-17; DEC-0129).

    ``still_valid_before_cascade`` is the child's own :attr:`ResolvedState.still_valid`
    (from its own append-only records); ``cascade_invalidated`` is whether the family's
    declared :class:`InvalidationPredicate` fired over the parent's lifecycle facts at
    ``as_of``; and ``still_valid`` is ``still_valid_before_cascade and not
    cascade_invalidated``. Cascade is computed here on read — it is never stored, and never
    an automatic side effect of the parent's invalidation.
    """

    child_ref: Fingerprint
    as_of: Instant
    still_valid_before_cascade: bool
    cascade_invalidated: bool
    still_valid: bool


def resolve_cascade(
    child_state: object, parent_state: object, predicate: object, *, at: object
) -> Result[CascadeResolution]:
    """Compute a child's cascade at read time from a predicate over the parent's lifecycle
    facts, returning value-or-refusal (CT-17; DEC-0129, DEC-0114).

    Invalidation never cascades automatically: this is the **explicit, opt-in, reader
    -driven** derivation. ``child_state`` and ``parent_state`` are :class:`ResolvedState`
    values (each already folded to a knowledge time by :func:`resolve_state`);
    ``predicate`` is the family's :class:`InvalidationPredicate`; and ``at`` is the read
    time ``T``. The predicate is evaluated over the parent's lifecycle facts, and the child
    is cascade-invalidated only if it fires. The child's own records are never mutated and
    its own :func:`resolve_state` result is unchanged — cascade is layered on top at read
    time.
    """
    if not isinstance(child_state, ResolvedState):
        return _invalid(
            "child_state", "cascade resolves a child ResolvedState", given=repr(child_state)
        )
    if not isinstance(parent_state, ResolvedState):
        return _invalid(
            "parent_state", "cascade reads a parent ResolvedState", given=repr(parent_state)
        )
    if not isinstance(at, Instant):
        return _invalid("at", "the read time T is an Instant", given=repr(at))
    if not isinstance(predicate, InvalidationPredicate):
        return _invalid(
            "predicate",
            "a family's invalidation predicate implements the InvalidationPredicate seam "
            "(a cascades(*, parent, child, at) method)",
            given=repr(predicate),
        )
    fired = _predicate_result(predicate, parent=parent_state, child=child_state, at=at)
    if not isinstance(fired, bool):
        return _invalid(
            "predicate",
            "an invalidation predicate returns a bool (whether the parent's lifecycle "
            "facts invalidate the child at T)",
            given=repr(fired),
        )
    return Ok(
        CascadeResolution(
            child_ref=child_state.object_ref,
            as_of=at,
            still_valid_before_cascade=child_state.still_valid,
            cascade_invalidated=fired,
            still_valid=child_state.still_valid and not fired,
        )
    )
