"""CT-17 — evidence class as identity, knowledge-time consumption, the structure result
label, and the governed-evidence citation law (COMP-QMF-STRUCTURE).

Story 9.1 minted the object and Story 9.2 pinned the append-only lifecycle. Story 9.3
makes **evidence class and knowledge time first-class identity** and governs how a
structure object becomes governed evidence, so unconfirmed or look-ahead structure can
never leak into confirmed evidence (CT-17; DEC-0129, DEC-0131, DEC-0110).

**Evidence class is identity and a label part; the confirmed read refuses, never filters
(FM-4).** Evidence class (``confirmed | unconfirmed | provisional``) is already an identity
field of :class:`~qmf.structure.StructureObject` and a named part of the CT-05 result
label. :func:`read_confirmed` is the governed read requesting confirmed evidence: it
returns every row only when they are **all** confirmed, and **refuses** the moment it sees
an unconfirmed or provisional row — a ``policy rejection``, **never a silent filter** — so a
consumer can never quietly drop the rows it should have refused (DEC-0129, DEC-0131). An
unconfirmed output links to its confirmed successor through the Story 9.2 ``confirmed-as``
edge (:class:`~qmf.structure.ConfirmationRecord`), so the refusal is recoverable: the
caller follows that edge to the confirmed artifact.

**Knowledge-time consumption vs the causality test (DEC-0106).** A decision at instant
``T`` may consume evidence whose ``confirmed-at`` is **at or before** ``T`` — equality is
consumption, not look-ahead (:func:`may_consume`). The refuse-at-equal rule governs
**causality tests between derived artifacts**, not consumption: :func:`causally_precedes`
delegates to qmf-core's :func:`~qmf.core.compare_causal`, which **refuses** equal instants
as concurrent (they never tie-break). The two rules are deliberately different and each is
exposed under its own name so a caller never conflates them.

**The structure result label (DEC-0110, DEC-0131).** :func:`structure_result_label` builds
the CT-05 :class:`~qmf.core.ResultLabel` for a minted object: its producer contract
identity is the **configured family** fingerprint (family identity + confirmation rule +
exact-rational parameters — distinct from the format version so two configurations can
never share a label), plus the contract format version, the input fingerprints, the
evidence time range, the object's evidence class, and the world. Because the input
fingerprints are part of the label, **an object computed on a revised input receives a
different label by construction** — a new fingerprinted input flows straight into a new
computation identity — rather than silently changing under a stable label. ``world =
simulated`` is reserved-unusable in V1: routing it into governed evidence is a ``policy
rejection`` (CT-05; DEC-0110, GAP-0048).

**The governed-evidence citation law (AC #5; DEC-0129, DEC-0119).** Live in-memory use
persists nothing. But any object **cited by a journal event or a result label becomes
governed evidence by that act** and must be persisted (:func:`evaluate_citation`). Scanners
run ungoverned and **promote only confirmed objects** (:func:`promote_scanned`) — an
unconfirmed or provisional scan hit is refused, never promoted. The full
look-ahead/causality registration gate (CT-08) stays deferred to the backtesting sitting
(GAP-0016, DEC-0121); the in-component emission invariant (Story 9.1) is the interim guard,
**not** that gate — nothing here closes GAP-0016.

Default-deny holds: this module imports **only** ``qmf.core`` (every ``fp1`` fingerprint is
computed there, nowhere else). It returns fingerprintable content and typed values, never
stamped records; the composition root holds the ``WriterId`` and mints the CT-06 records and
CT-13 journal events that make an object governed evidence (DEC-0120, DEC-0129). Public
value types are frozen dataclasses, the row seam is a ``typing.Protocol``, and every
operation succeeds or RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain failure is
never raised across the boundary (DEC-0101, DEC-0109, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol, cast, runtime_checkable

from qmf.core import (
    EvidenceClass,
    Instant,
    Interval,
    Ok,
    RefusalCategory,
    Result,
    ResultLabel,
    Retryability,
    TemporalOrder,
    TypedRefusal,
    World,
    compare_causal,
    fingerprint,
    is_refusal,
)
from qmf.structure.objects import (
    CONTRACT_FORMAT_VERSION,
    StructureObject,
)

__all__ = [
    "CitationKind",
    "EvidenceRow",
    "GovernanceVerdict",
    "causally_precedes",
    "evaluate_citation",
    "may_consume",
    "promote_scanned",
    "read_confirmed",
    "structure_result_label",
]


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a provenance operation returns.

    ``retryability`` is ``no`` — a malformed row, a non-``Instant`` knowledge time, or a
    non-``Interval`` evidence range is a caller/wiring mistake, not a transient condition —
    and ``context`` always names the offending ``field`` and a human-legible ``reason``
    (returned, never raised; CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal a governed provenance rule returns (FM-4).

    A confirmed read over an unconfirmed row, a look-ahead consumption, a ``simulated``-world
    label, or a scanner promoting a non-confirmed object is not *malformed* — it is a
    well-formed request the governance law **declines** — so it is a policy rejection, never
    a silent filter. ``retryability`` is ``no``: the request succeeds only once the caller
    changes what it asks for (follow the ``confirmed-as`` edge, wait for confirmation, choose
    a usable world), which is a different request, not a retry of this one.
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


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


# --- FM-4: evidence class is identity; the confirmed read refuses -----------


@runtime_checkable
class EvidenceRow(Protocol):
    """The ``typing.Protocol`` seam a governed evidence row exposes (CT-17; DEC-0129,
    DEC-0131).

    A row carries an :class:`~qmf.core.EvidenceClass` as identity. Both a minted
    :class:`~qmf.structure.StructureObject` and a CT-05 :class:`~qmf.core.ResultLabel`
    satisfy this seam — evidence class is a declared identity field of the one and a named
    part of the other — so :func:`read_confirmed` governs either without importing beyond
    ``qmf-core``. It is a structural seam, not a closed hierarchy.
    """

    @property
    def evidence_class(self) -> EvidenceClass:  # pragma: no cover - protocol seam
        """The row's evidence class — a declared identity field / label part."""
        ...


def _row_evidence_class(row: EvidenceRow) -> object:
    """Return a row's ``evidence_class`` as ``object`` on purpose (see :func:`read_confirmed`).

    A ``runtime_checkable`` Protocol's isinstance proves the member EXISTS but never its
    type, so a structurally-valid :class:`EvidenceRow` may still hand back a non-
    :class:`~qmf.core.EvidenceClass` value — widening to ``object`` here keeps the isinstance
    guard on the result real, not redundant.
    """
    return row.evidence_class


def read_confirmed(rows: object) -> Result[tuple[EvidenceRow, ...]]:
    """The governed read requesting confirmed evidence (FM-4; DEC-0129, DEC-0131).

    Returns every row **only** when they are all ``confirmed``; the moment it sees an
    ``unconfirmed`` or ``provisional`` row it RETURNS a ``policy rejection`` naming that
    row's index and class — **never a silent filter**. A consumer that requested confirmed
    evidence therefore can never quietly drop the rows it should have refused; it follows the
    unconfirmed row's ``confirmed-as`` edge to the confirmed successor and retries.

    ``rows`` is a sequence of :class:`EvidenceRow` (a bare string is not a sequence of rows,
    and an element without a valid :class:`~qmf.core.EvidenceClass` is an ``invalid input``
    refusal). An empty read is legal and returns the empty tuple.
    """
    if isinstance(rows, (str, bytes)) or not isinstance(rows, Sequence):
        return _invalid(
            "rows",
            "a confirmed read takes a sequence of evidence rows (a bare string is not a "
            "sequence of rows)",
            given=repr(rows),
        )
    resolved: list[EvidenceRow] = []
    for index, row in enumerate(cast("Sequence[object]", rows)):
        if not isinstance(row, EvidenceRow):
            return _invalid(
                "rows",
                "each row exposes an evidence_class identity field (a StructureObject or a "
                "ResultLabel)",
                index=index,
                given=repr(row),
            )
        row_class = _row_evidence_class(row)
        if not isinstance(row_class, EvidenceClass):
            return _invalid(
                "rows",
                "a row's evidence_class is an EvidenceClass member",
                index=index,
                given=repr(row_class),
            )
        if row_class is not EvidenceClass.CONFIRMED:
            return _policy(
                "rows",
                "a read requesting confirmed evidence refuses an unconfirmed or provisional "
                "row (FM-4) rather than filtering it out silently; follow the row's "
                "confirmed-as edge to its confirmed successor",
                index=index,
                evidence_class=row_class.value,
            )
        resolved.append(row)
    return Ok(tuple(resolved))


# --- AC #2: knowledge-time consumption vs the causality test ----------------


def may_consume(confirmed_at: object, *, at: object) -> Result[Instant]:
    """Whether a decision at ``at`` may consume evidence confirmed at ``confirmed_at``
    (CT-17; DEC-0129, DEC-0106).

    A decision at instant ``T`` may consume evidence with ``confirmed-at <= T`` — **equality
    is consumption, not look-ahead**. Returns ``Ok(confirmed_at)`` when consumable; a
    ``policy rejection`` when ``confirmed_at`` follows ``T`` (consuming it would be
    look-ahead). This is the **consumption** rule; the distinct refuse-at-equal rule for
    causality tests between derived artifacts is :func:`causally_precedes`.
    """
    if not isinstance(confirmed_at, Instant):
        return _invalid(
            "confirmed_at",
            "the evidence's confirmed-at is an Instant (int64 UTC ns)",
            given=repr(confirmed_at),
        )
    if not isinstance(at, Instant):
        return _invalid("at", "the decision instant T is an Instant (int64 UTC ns)", given=repr(at))
    if confirmed_at.value_ns > at.value_ns:
        return _policy(
            "confirmed_at",
            "a decision at T may consume only evidence with confirmed-at <= T; this "
            "evidence's confirmed-at follows T, so consuming it would be look-ahead "
            "(equality is consumption, not look-ahead)",
            confirmed_at=confirmed_at.value_ns,
            at=at.value_ns,
        )
    return Ok(confirmed_at)


def causally_precedes(earlier: object, *, later: object) -> Result[bool]:
    """The causality test between two derived artifacts: refuse-at-equal (CT-17;
    DEC-0129, DEC-0106).

    Returns ``Ok(True)`` when ``earlier`` is strictly before ``later``, ``Ok(False)`` when
    it is strictly after, and — delegating to qmf-core's :func:`~qmf.core.compare_causal` —
    a ``policy rejection`` when the two instants are **equal**: equal instants are concurrent
    and causality never tie-breaks. This is deliberately **stricter** than
    :func:`may_consume`, where equality *is* consumption; refuse-at-equal governs causality
    tests between derived artifacts, not consumption.
    """
    order = compare_causal(earlier, later)
    if is_refusal(order):
        return order
    return Ok(order.value is TemporalOrder.BEFORE)


# --- AC #4: the structure result label --------------------------------------


def _configured_producer_content(obj: StructureObject) -> dict[str, object]:
    """The canonical ``fp1`` content of the **configured family** — the result label's
    producer contract identity (CT-05, CT-17; DEC-0110, DEC-0131).

    The producer is the family **as configured**: its identity + version + geometry, its
    declared confirmation rule, and its exact-rational parameters — but **not** the
    per-observation anchor span, observed-at, or evidence class, which belong to the specific
    run, not the producer. Two objects of the same family with the same parameters share this
    producer identity and are then distinguished in the label by their inputs, evidence
    range, class, and world; two different parameterizations never share it.
    """
    return {
        "class": "configured-structure-family",
        "family": obj.family.fp1_identity(),
        "parameters": {name: value.fp1_identity() for name, value in obj.parameters.items()},
        "confirmation_rule": obj.confirmation_rule.fp1_identity(),
        "format_version": CONTRACT_FORMAT_VERSION,
    }


def structure_result_label(
    obj: object,
    *,
    world: object,
    input_fingerprints: object = (),
    evidence_time_range: object = None,
) -> Result[ResultLabel]:
    """Build the CT-05 result label for a minted structure object (AC #4; DEC-0110,
    DEC-0131).

    The label carries the **configured family** fingerprint (producer contract identity),
    the contract format version, the ``input_fingerprints`` of every identity-bearing input
    consumed, the ``evidence_time_range``, the object's ``evidence_class``, and the
    ``world``. Because the input fingerprints are part of the label, **an object computed on
    a revised input receives a different label** — a new fingerprinted input flows into a new
    computation identity — rather than silently changing under a stable label.

    ``obj`` is a :class:`~qmf.structure.StructureObject`; ``world`` a
    :class:`~qmf.core.World` (``simulated`` is reserved-unusable in V1 — routing it into
    governed evidence is a ``policy rejection``, GAP-0048); ``input_fingerprints`` an
    order-significant sequence of :class:`~qmf.core.Fingerprint`\\ s (empty is legal for an
    a-priori/standing object that consumed no dated input); and ``evidence_time_range`` a
    half-open :class:`~qmf.core.Interval`, defaulting to the object's anchor span when
    omitted. Returns the label or a CT-04 refusal.
    """
    if not isinstance(obj, StructureObject):
        return _invalid(
            "obj", "a structure result label is built for a StructureObject", given=repr(obj)
        )
    resolved_world = _coerce_world(world)
    if resolved_world is None:
        return _invalid(
            "world",
            "world is one of the closed set",
            given=repr(world),
            allowed=[member.value for member in World],
        )
    if resolved_world is World.SIMULATED:
        return _policy(
            "world",
            "world = simulated is reserved-unusable in V1; routing it into governed evidence "
            "is refused until the backtesting sitting defines simulated-time typing "
            "(GAP-0048)",
        )
    if evidence_time_range is None:
        derived = Interval.try_create(obj.anchor.start, obj.anchor.end)
        if is_refusal(derived):  # pragma: no cover - the anchor guarantees start <= end
            return derived
        evidence_range: Interval = derived.value
    elif isinstance(evidence_time_range, Interval):
        evidence_range = evidence_time_range
    else:
        return _invalid(
            "evidence_time_range",
            "the evidence time range is a half-open Interval over int64 UTC ns, or None to "
            "default to the object's anchor span",
            given=repr(evidence_time_range),
        )
    producer = fingerprint(_configured_producer_content(obj))
    if is_refusal(producer):  # pragma: no cover - producer content is canonical by construction
        return producer
    return ResultLabel.try_create(
        producer.value,
        CONTRACT_FORMAT_VERSION,
        input_fingerprints,
        evidence_range,
        obj.evidence_class,
        resolved_world,
    )


# --- AC #5: the governed-evidence citation law ------------------------------


class CitationKind(StrEnum):
    """How a structure object is used, which decides whether it becomes governed evidence
    (CT-17; DEC-0129, DEC-0119).

    * ``in-memory`` — a live, in-memory use that persists nothing.
    * ``journal-event`` — the object is cited by a CT-13 journal event.
    * ``result-label`` — the object is cited by a CT-05 result label.

    A citation by a journal event or a result label makes the object governed evidence **by
    that act** and it must be persisted; an in-memory use does not.
    """

    IN_MEMORY = "in-memory"
    JOURNAL_EVENT = "journal-event"
    RESULT_LABEL = "result-label"


@dataclass(frozen=True, slots=True)
class GovernanceVerdict:
    """Whether a use of a structure object makes it governed evidence (CT-17; DEC-0129,
    DEC-0119).

    ``citation`` is how the object was used; ``governed`` is whether that use makes it
    governed evidence; ``must_persist`` is whether it must be persisted (identical to
    ``governed`` — becoming governed evidence *is* the persistence obligation). It is a
    read-time verdict computed from the citation, never a stored field of any object.
    """

    citation: CitationKind
    governed: bool
    must_persist: bool


def evaluate_citation(citation: object) -> Result[GovernanceVerdict]:
    """Evaluate whether a use of a structure object makes it governed evidence (AC #5;
    DEC-0129, DEC-0119).

    The law binds governed evidence only: an ``in-memory`` use persists nothing, but any
    object cited by a ``journal-event`` or a ``result-label`` **becomes governed evidence by
    that act** and must be persisted (its fingerprint-bearing content is stamped by the
    composition root). Returns the :class:`GovernanceVerdict`, or an ``invalid input``
    refusal for an unknown citation kind.
    """
    if isinstance(citation, CitationKind):
        kind = citation
    elif isinstance(citation, str):
        try:
            kind = CitationKind(citation)
        except ValueError:
            return _invalid(
                "citation",
                "the citation kind is one of the closed set",
                given=repr(citation),
                allowed=[member.value for member in CitationKind],
            )
    else:
        return _invalid(
            "citation",
            "the citation kind is a CitationKind (or its string value)",
            given=repr(citation),
        )
    governed = kind is not CitationKind.IN_MEMORY
    return Ok(GovernanceVerdict(citation=kind, governed=governed, must_persist=governed))


def promote_scanned(obj: object) -> Result[StructureObject]:
    """Promote a scanned object into governed evidence — confirmed only (AC #5; FM-4;
    DEC-0129).

    Scanners run **ungoverned** and promote **only confirmed objects**: an object whose
    evidence class is ``unconfirmed`` or ``provisional`` is RETURNED as a ``policy
    rejection`` — never promoted, never silently upgraded. A confirmed object is returned
    unchanged, so a caller can write ``obj = promote_scanned(hit).value`` at the promotion
    boundary. Promotion does not itself persist anything: it is the confirmed-only gate a
    scanner passes an object through before the composition root cites and persists it.
    """
    if not isinstance(obj, StructureObject):
        return _invalid("obj", "a scanner promotes a StructureObject", given=repr(obj))
    if obj.evidence_class is not EvidenceClass.CONFIRMED:
        return _policy(
            "evidence_class",
            "a scanner promotes only confirmed objects into governed evidence; an "
            "unconfirmed or provisional scan hit is not promoted (FM-4)",
            evidence_class=obj.evidence_class.value,
        )
    return Ok(obj)
