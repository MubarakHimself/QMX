"""Shared internal helpers for the ``qmf.risk`` contract modules (private).

These are the refusal builders and the enum coercion used across the CT-22 /
CT-27 template grammar, the dimensional law, the USD numeraire, and the
git-logic version graph. They are deliberately private — never re-exported — the
same way ``qmf.core``'s per-module ``_invalid`` builders are internal to their
module. Every refusal is a ``qmf-core`` :class:`~qmf.core.TypedRefusal` value,
RETURNED never raised, so a caller branches on structure and never on prose
(CT-04; DEC-0109). Imports only ``qmf-core`` — the default-deny dependency
direction holds by construction (L30/DEC-0120).
"""

from __future__ import annotations

from enum import StrEnum
from typing import TypeVar

from qmf.core import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "clean_str",
    "coerce_enum",
    "invalid",
    "policy",
    "stale",
    "type_name",
    "unavailable",
    "unsupported",
]


def type_name(value: object) -> str:
    """The runtime type name of ``value`` — a stable label for a refusal context.

    Takes ``object`` so a caller may pass an already-narrowed union without the type
    name becoming partially unknown; the returned string is the concrete class name.
    """
    return type(value).__name__


_EnumT = TypeVar("_EnumT", bound=StrEnum)


def coerce_enum(enum_cls: type[_EnumT], value: object) -> _EnumT | None:
    """Return the ``enum_cls`` member ``value`` names, or ``None`` if it names none.

    Accepts an existing member or its exact string value; ``None`` in, ``None``
    out, so a caller can tell a *missing* enum from an *unrecognised* one and
    return the right refusal (a missing required flag is still ``invalid input``).
    """
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return None
    return None


def clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    Names, gap references, and currency tags are opaque tokens stored unchanged —
    never stripped, cased, or parsed.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _build(category: RefusalCategory, field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(category=category, retryability=Retryability.NO, context=context)


def invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``invalid input`` refusal — a malformed value part, a caller mistake.

    A variable missing its unit-kind, value, ui-editable flag, or admission
    impact; a binary float on the money path; a non-unique or unresolvable part —
    each is a caller mistake, not a transient condition, so ``retryability`` is
    ``no`` (CT-22, CT-27; DEC-0144).
    """
    return _build(RefusalCategory.INVALID_INPUT, field, reason, **extra)


def policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """A ``policy rejection`` refusal — well-formed but forbidden by a rule.

    A non-USD accounting currency, a lots-denominated Book limit, or a notional
    limit needing an unratified conversion is well-formed yet refused by policy,
    never silently converted (AD-40; DEC-0154).
    """
    return _build(RefusalCategory.POLICY_REJECTION, field, reason, **extra)


def unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``unsupported capability`` refusal — e.g. an unknown contract format
    version, never a best-effort read (DEC-0144)."""
    return _build(RefusalCategory.UNSUPPORTED_CAPABILITY, field, reason, **extra)


def unavailable(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``unavailable dependency`` refusal — a required peer version node is
    absent from the graph, never fabricated (DEC-0144)."""
    return _build(RefusalCategory.UNAVAILABLE_DEPENDENCY, field, reason, **extra)


def stale(field: str, reason: str, **extra: object) -> TypedRefusal:
    """A ``stale evidence`` refusal — a later same-seat intent before the closing
    exit record is persisted and journaled (CT-29; DEC-0155)."""
    return _build(RefusalCategory.STALE_EVIDENCE, field, reason, **extra)
