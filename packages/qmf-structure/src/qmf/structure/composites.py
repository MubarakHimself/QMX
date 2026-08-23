"""CT-17 — composite structure objects over governed children (COMP-QMF-STRUCTURE).

A composite is **its own artifact** whose children are other governed objects — indicator
results, structure objects, calendar windows — each referenced by ``fp1`` fingerprint. It is
how CT-17 expresses cluster objects over tolerance-grouped extremes, ordered multi-phase
calendar composites, multi-BarSpec nests, cross-instrument divergence objects, and a-priori
price grids: each is a composite whose children are the constituent objects (DEC-0129,
DEC-0131, DEC-0115).

**Instants are the maximum over the children (DEC-0129, DEC-0131).** A composite's
``observed_at`` is the maximum of its children's ``observed_at`` and its ``confirmed_at`` the
maximum of theirs — never earlier than any child (you cannot observe the whole before its
last part, nor confirm it before its last part confirms). A composite has a ``confirmed_at``
only when **every** child is confirmed; until then it is unconfirmed. Its
confirmation-delay bound is the **sum** of its children's bounds, and is unbounded when any
child is unbounded — feeding the split embargo width exactly as a leaf family's bound does.

**Children are order-significant by default (DEC-0129, DEC-0115).** ``ordered = True`` (the
default) makes child order identity-bearing — an ordered multi-phase calendar composite means
its phases in sequence. A family declares a collection **unordered** explicitly
(``ordered = False``), and then the children fingerprint canonically regardless of the order
they were supplied, so the same set is one artifact however it is assembled.

**Lineage is the input-fingerprint set, not a new edge kind (DEC-0114, DEC-0131).** A
composite's lineage to its children is carried by its children fingerprints entering its
result label's input fingerprints (:meth:`CompositeObject.input_fingerprints`) — CT-17 mints
no "composes" edge, and this package never invents one outside the ratified CT-07 vocabulary.

Default-deny holds: this module imports **only** ``qmf.core`` and the sibling
``qmf.structure`` value types. Every ``fp1`` is computed in qmf-core; the composite returns
fingerprintable content, never a stamped record. Public value types are frozen dataclasses,
and every operation succeeds or RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain
failure is never raised across the boundary (DEC-0101, DEC-0109, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from qmf.core import (
    EvidenceClass,
    ExactRational,
    Fingerprint,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    fingerprint,
    is_ok,
)
from qmf.structure.objects import (
    CONTRACT_FORMAT_VERSION,
    ConfirmationRule,
    FamilyIdentity,
)

__all__ = [
    "CompositeChild",
    "CompositeObject",
]


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a composite operation returns (CT-04; DEC-0109)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _coerce_evidence_class(value: object) -> EvidenceClass | None:
    """Resolve ``value`` to an :class:`~qmf.core.EvidenceClass` member, or ``None``."""
    if isinstance(value, EvidenceClass):
        return value
    if isinstance(value, str):
        try:
            return EvidenceClass(value)
        except ValueError:
            return None
    return None


def _coerce_parameters(value: object) -> dict[str, ExactRational] | TypedRefusal:
    """Resolve the exact-rational parameter set, or refuse (exact rationals only; DEC-0105)."""
    if not isinstance(value, Mapping):
        return _invalid(
            "parameters",
            "the parameter set is a name->ExactRational mapping (exact rationals only)",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[object, object]", value)
    out: dict[str, ExactRational] = {}
    for key, item in mapping.items():
        if not isinstance(key, str) or key.strip() == "":
            return _invalid(
                "parameters", "each parameter name is a non-empty string", given=repr(key)
            )
        if not isinstance(item, ExactRational):
            return _invalid(
                "parameters",
                "each parameter value is an ExactRational (never a binary float)",
                name=key,
                given=repr(item),
            )
        out[key] = item
    return out


@dataclass(frozen=True, slots=True)
class CompositeChild:
    """One child of a composite, referenced by fingerprint with its lifecycle instants (CT-17;
    DEC-0129, DEC-0131).

    ``ref`` is the child's ``fp1`` fingerprint (a structure object, an indicator result, a
    calendar window — any governed kind); ``observed_at`` its knowledge time; ``confirmed_at``
    its confirmation instant, absent until it is confirmed; and ``confirmation_delay_bound`` its
    declared bound (``None`` = unbounded). The composite folds these into its own derived
    instants — it never re-derives a child from its fingerprint.
    """

    ref: Fingerprint
    observed_at: Instant
    confirmed_at: Instant | None
    confirmation_delay_bound: int | None

    @classmethod
    def try_create(
        cls,
        ref: object,
        observed_at: object,
        *,
        confirmed_at: object = None,
        confirmation_delay_bound: object = None,
    ) -> Result[CompositeChild]:
        """Validate and build a :class:`CompositeChild`, returning value-or-refusal."""
        resolved_ref = _coerce_fingerprint(ref)
        if resolved_ref is None:
            return _invalid(
                "ref", "a composite child is referenced by an fp1 fingerprint", given=repr(ref)
            )
        if not isinstance(observed_at, Instant):
            return _invalid(
                "observed_at", "a child observed-at is an Instant", given=repr(observed_at)
            )
        confirmed: Instant | None = None
        if confirmed_at is not None:
            if not isinstance(confirmed_at, Instant):
                return _invalid(
                    "confirmed_at",
                    "a child confirmed-at is an Instant when present",
                    given=repr(confirmed_at),
                )
            if confirmed_at.value_ns < observed_at.value_ns:
                return _invalid(
                    "confirmed_at",
                    "a child is confirmed at or after it is observed",
                    observed_at=observed_at.value_ns,
                    confirmed_at=confirmed_at.value_ns,
                )
            confirmed = confirmed_at
        bound = confirmation_delay_bound
        if bound is not None and (
            isinstance(bound, bool) or not isinstance(bound, int) or bound < 0
        ):
            return _invalid(
                "confirmation_delay_bound",
                "a child confirmation-delay bound is a non-negative integer, or None for unbounded",
                given=repr(confirmation_delay_bound),
            )
        return Ok(
            cls(
                ref=resolved_ref,
                observed_at=observed_at,
                confirmed_at=confirmed,
                confirmation_delay_bound=bound,
            )
        )


@dataclass(frozen=True, slots=True)
class CompositeObject:
    """A composite structure object over governed children (CT-17; DEC-0129, DEC-0131,
    DEC-0115).

    Its ``observed_at`` and ``confirmed_at`` are the maxima over its children (``confirmed_at``
    is absent until every child is confirmed), and its ``confirmation_delay_bound`` is the sum
    of its children's bounds (``None`` when any child is unbounded). ``ordered`` makes child
    order identity-bearing; an unordered composite fingerprints its children canonically. Every
    field is identity-bearing and the object is never mutated.
    """

    family: FamilyIdentity
    confirmation_rule: ConfirmationRule
    children: tuple[Fingerprint, ...]
    ordered: bool
    observed_at: Instant
    confirmed_at: Instant | None
    confirmation_delay_bound: int | None
    evidence_class: EvidenceClass
    parameters: Mapping[str, ExactRational]

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    @classmethod
    def try_create(
        cls,
        *,
        family: object,
        confirmation_rule: object,
        children: object,
        evidence_class: object,
        ordered: object = True,
        parameters: object = None,
    ) -> Result[CompositeObject]:
        """Build a composite from its children, deriving its instants, returning value-or-refusal.

        ``family`` and ``confirmation_rule`` are the composite's own identity;  ``children`` a
        non-empty sequence of :class:`CompositeChild`; ``evidence_class`` one of the closed set;
        ``ordered`` a bool (order-significant by default); ``parameters`` an optional
        name->:class:`~qmf.core.ExactRational` map. ``observed_at`` / ``confirmed_at`` /
        ``confirmation_delay_bound`` are **derived** from the children, never supplied.
        """
        if not isinstance(family, FamilyIdentity):
            return _invalid("family", "a composite carries a FamilyIdentity", given=repr(family))
        if not isinstance(confirmation_rule, ConfirmationRule):
            return _invalid(
                "confirmation_rule",
                "a composite declares a ConfirmationRule",
                given=repr(confirmation_rule),
            )
        if not isinstance(ordered, bool):
            return _invalid("ordered", "the order-significance flag is a bool", given=repr(ordered))
        if isinstance(children, (str, bytes)) or not isinstance(children, Sequence):
            return _invalid(
                "children", "children are a sequence of CompositeChild", given=repr(children)
            )
        resolved_children = cast("Sequence[object]", children)
        if len(resolved_children) == 0:
            return _invalid("children", "a composite holds one or more children")
        child_list: list[CompositeChild] = []
        for index, child in enumerate(resolved_children):
            if not isinstance(child, CompositeChild):
                return _invalid(
                    "children", "each child is a CompositeChild", index=index, given=repr(child)
                )
            child_list.append(child)
        resolved_class = _coerce_evidence_class(evidence_class)
        if resolved_class is None:
            return _invalid(
                "evidence_class",
                "the evidence class is one of the closed set",
                given=repr(evidence_class),
                allowed=[member.value for member in EvidenceClass],
            )
        resolved_parameters = _coerce_parameters({} if parameters is None else parameters)
        if isinstance(resolved_parameters, TypedRefusal):
            return resolved_parameters

        observed_at = max((child.observed_at for child in child_list), key=lambda i: i.value_ns)
        all_confirmed = all(child.confirmed_at is not None for child in child_list)
        confirmed_at: Instant | None = None
        if all_confirmed:
            confirmed_instants = [
                child.confirmed_at for child in child_list if child.confirmed_at is not None
            ]
            confirmed_at = max(confirmed_instants, key=lambda i: i.value_ns)
        any_unbounded = any(child.confirmation_delay_bound is None for child in child_list)
        confirmation_delay_bound: int | None = None
        if not any_unbounded:
            confirmation_delay_bound = sum(
                child.confirmation_delay_bound
                for child in child_list
                if child.confirmation_delay_bound is not None
            )

        return Ok(
            cls(
                family=family,
                confirmation_rule=confirmation_rule,
                children=tuple(child.ref for child in child_list),
                ordered=ordered,
                observed_at=observed_at,
                confirmed_at=confirmed_at,
                confirmation_delay_bound=confirmation_delay_bound,
                evidence_class=resolved_class,
                parameters=resolved_parameters,
            )
        )

    def input_fingerprints(self) -> tuple[Fingerprint, ...]:
        """The children's fingerprints — the composite's lineage as its result-label inputs.

        Order-preserved for an ordered composite; canonically sorted for an unordered one, so
        an unordered set's lineage is stable however it was assembled.
        """
        if self.ordered:
            return self.children
        return tuple(sorted(self.children, key=lambda fp: fp.value))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — every part is identity.

        An unordered composite lists its children sorted so member order cannot change its
        fingerprint; an ordered one preserves the given sequence. ``None`` never enters identity
        (fp1 prohibits null): an absent ``confirmed_at`` is an omitted key, and an unbounded
        delay is the explicit ``confirmation_delay: "unbounded"`` token.
        """
        child_refs = [fp.value for fp in self.input_fingerprints()]
        content: dict[str, object] = {
            "class": "composite-structure-object",
            "family": self.family.fp1_identity(),
            "confirmation_rule": self.confirmation_rule.fp1_identity(),
            "ordered": self.ordered,
            "children": child_refs,
            "observed_at": self.observed_at.value_ns,
            "evidence_class": self.evidence_class.value,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.confirmed_at is not None:
            content["confirmed_at"] = self.confirmed_at.value_ns
        if self.confirmation_delay_bound is None:
            content["confirmation_delay"] = "unbounded"
        else:
            content["confirmation_delay_bound"] = self.confirmation_delay_bound
        if self.parameters:
            content["parameters"] = {
                name: value.fp1_identity() for name, value in self.parameters.items()
            }
        return content

    def content_fingerprint(self) -> Result[Fingerprint]:
        """The composite's ``fp1`` fingerprint, computed in qmf-core (DEC-0108)."""
        return fingerprint(self.fp1_identity())
