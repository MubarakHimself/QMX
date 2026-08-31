"""Shared helpers for QMA typed-refusal variants of the qmf-core base (CT-04)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import ClassVar, Self

from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = ["QmaRefusal", "variant_name"]


class QmaRefusal(TypedRefusal):
    """Named QMA refusal variant — subclass of ``TypedRefusal``, never raised.

    Subclasses set ``VARIANT``, ``CATEGORY``, and ``RETRYABILITY``. Construction
    goes through ``create`` so every public failure returns a structured CT-04
    value (FR-Q05; DEC-0302).
    """

    VARIANT: ClassVar[str]
    CATEGORY: ClassVar[RefusalCategory]
    RETRYABILITY: ClassVar[Retryability] = Retryability.NO

    @classmethod
    def create(
        cls,
        *,
        context: Mapping[str, object] | None = None,
        after_condition_descriptor: str | None = None,
    ) -> Self:
        """Build this variant with ``variant`` stamped into context."""
        payload: dict[str, object] = {"variant": cls.VARIANT}
        if context:
            payload.update(dict(context))
        return cls(
            category=cls.CATEGORY,
            retryability=cls.RETRYABILITY,
            context=payload,
            after_condition_descriptor=after_condition_descriptor,
        )

    @classmethod
    def matches(cls, refusal: TypedRefusal) -> bool:
        """True when ``refusal`` is this variant (by type or context stamp)."""
        if isinstance(refusal, cls):
            return True
        return refusal.context.get("variant") == cls.VARIANT


def variant_name(refusal: TypedRefusal) -> str | None:
    """Return the QMA variant name stamped on a refusal, if any."""
    value = refusal.context.get("variant")
    return value if isinstance(value, str) else None
