"""CT-04 — the typed refusal envelope (COMP-QMF-CORE).

Every public qmf-core operation either succeeds or RETURNS a ``TypedRefusal``
value across the package boundary; it never raises to signal a domain failure.
Exceptions stay reserved for programmer error and never carry a refusal across a
boundary. A refusal names a ``category`` (one of exactly seven), carries
machine-readable ``context``, and answers ``retryability``
(``yes | no | after-condition``), so callers and agents branch on structure,
never on error prose (CT-04; DEC-0109, DEC-0112).

This module also establishes the value-construction pattern every qmf-core value
type follows (Money, Instrument, and the rest, in later stories):

* an **unchecked constructor** — the frozen dataclass itself — for trusted
  internal use where the caller already holds valid parts; and
* a validating **``try_create``** factory that returns ``Result[T]`` — either the
  built value wrapped in ``Ok``, or a ``TypedRefusal`` explaining the rejection.

``Result[T] = Ok[T] | TypedRefusal`` keeps the two arms distinguishable even when
``T`` is itself a ``TypedRefusal`` (as it is for ``TypedRefusal.try_create``),
which a bare ``T | TypedRefusal`` union could not.

Stdlib only (DEC-0104). Generics are spelled with ``TypeVar``/``Generic`` rather
than PEP 695 syntax so the workspace lints under its ruff target while running on
CPython 3.14.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Generic, TypeAlias, TypeIs, TypeVar

__all__ = [
    "Ok",
    "RefusalCategory",
    "Result",
    "Retryability",
    "TypedRefusal",
    "is_ok",
    "is_refusal",
]

T = TypeVar("T")
EnumT = TypeVar("EnumT", bound=StrEnum)


class RefusalCategory(StrEnum):
    """The seven refusal categories (CT-04 ``enums.category``; DEC-0109).

    Values are the canonical spaced strings pinned by CT-04. Categories are
    addable in a later contract format version, never redefined.
    """

    INVALID_INPUT = "invalid input"
    UNSUPPORTED_CAPABILITY = "unsupported capability"
    UNAVAILABLE_DEPENDENCY = "unavailable dependency"
    STALE_EVIDENCE = "stale evidence"
    POLICY_REJECTION = "policy rejection"
    TRANSIENT_VENUE_FAILURE = "transient venue failure"
    STORAGE_FAILURE = "storage failure"


class Retryability(StrEnum):
    """Whether, and when, a refused operation may be retried (CT-04
    ``enums.retryability``; DEC-0109)."""

    YES = "yes"
    NO = "no"
    AFTER_CONDITION = "after-condition"


# One shared immutable empty context. `context` is always present and never
# null; when a caller supplies none, this stands in (CT-04 nullability).
_EMPTY_CONTEXT: Final[Mapping[str, object]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class Ok(Generic[T]):
    """The success arm of a value-or-refusal ``Result``: the constructed value.

    A one-field wrapper, not the value itself, so ``Ok[T]`` and ``TypedRefusal``
    stay distinguishable in ``Result[T]`` even when ``T`` is a ``TypedRefusal``.
    """

    value: T


@dataclass(frozen=True, slots=True)
class TypedRefusal:
    """A typed failure value, RETURNED (never raised) across a public boundary.

    Fields follow CT-04 exactly: ``category`` (one of the seven), ``retryability``
    (``yes | no | after-condition``), machine-readable ``context`` (present,
    possibly empty, never null), and ``after_condition_descriptor`` (present only
    when ``retryability = after-condition``; the descriptor's field-level shape is
    deliberately unpinned pending later specification).

    The dataclass constructor is the **unchecked** path for trusted internal use.
    ``try_create`` is the **validating** path: it enforces the enums and the
    after-condition pairing rule and returns value-or-refusal.
    """

    category: RefusalCategory
    retryability: Retryability
    context: Mapping[str, object] = _EMPTY_CONTEXT
    after_condition_descriptor: str | None = None

    def __post_init__(self) -> None:
        # Snapshot context into a read-only mapping: the refusal value is
        # immutable, and a later mutation of a caller's dict can never reach
        # back into a stored refusal.
        object.__setattr__(self, "context", MappingProxyType(dict(self.context)))

    @classmethod
    def try_create(
        cls,
        category: RefusalCategory | str,
        retryability: Retryability | str,
        *,
        context: Mapping[str, object] | None = None,
        after_condition_descriptor: str | None = None,
    ) -> Result[TypedRefusal]:
        """Validate and build a ``TypedRefusal``, returning value-or-refusal.

        A category or retryability outside the pinned enums, a missing
        after-condition descriptor when ``retryability = after-condition``, or a
        descriptor supplied for any other retryability, each yields an
        ``invalid input`` refusal (returned, never raised) whose ``context``
        names the offending field.
        """
        resolved_category = _coerce(RefusalCategory, category)
        if resolved_category is None:
            return cls(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "category",
                    "given": str(category),
                    "allowed": [member.value for member in RefusalCategory],
                },
            )

        resolved_retryability = _coerce(Retryability, retryability)
        if resolved_retryability is None:
            return cls(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "retryability",
                    "given": str(retryability),
                    "allowed": [member.value for member in Retryability],
                },
            )

        needs_descriptor = resolved_retryability is Retryability.AFTER_CONDITION
        has_descriptor = after_condition_descriptor is not None
        if needs_descriptor and not has_descriptor:
            return cls(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "after_condition_descriptor",
                    "reason": "required when retryability is after-condition",
                },
            )
        if has_descriptor and not needs_descriptor:
            return cls(
                category=RefusalCategory.INVALID_INPUT,
                retryability=Retryability.NO,
                context={
                    "field": "after_condition_descriptor",
                    "reason": "present only when retryability is after-condition",
                },
            )

        return Ok(
            cls(
                category=resolved_category,
                retryability=resolved_retryability,
                context=context if context is not None else _EMPTY_CONTEXT,
                after_condition_descriptor=after_condition_descriptor,
            )
        )


Result: TypeAlias = Ok[T] | TypedRefusal
"""A value-or-refusal: the success arm ``Ok[T]`` or a ``TypedRefusal``."""


def _coerce(enum_cls: type[EnumT], value: EnumT | str) -> EnumT | None:
    """Return the enum member for ``value``, or ``None`` if it names none."""
    if isinstance(value, enum_cls):
        return value
    try:
        return enum_cls(value)
    except ValueError:
        return None


def is_ok(result: Result[T]) -> TypeIs[Ok[T]]:
    """True when ``result`` is the success arm; narrows to ``Ok[T]``."""
    return isinstance(result, Ok)


def is_refusal(result: Result[T]) -> TypeIs[TypedRefusal]:
    """True when ``result`` is the refusal arm; narrows to ``TypedRefusal``."""
    return isinstance(result, TypedRefusal)
