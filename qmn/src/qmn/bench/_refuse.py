"""Private CT-04 refusal builders for qmn.bench."""

from __future__ import annotations

from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = ["invalid", "policy"]


def _build(category: RefusalCategory, field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(category=category, retryability=Retryability.NO, context=context)


def invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``invalid input`` refusal."""
    return _build(RefusalCategory.INVALID_INPUT, field, reason, **extra)


def policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """A ``policy rejection`` refusal."""
    return _build(RefusalCategory.POLICY_REJECTION, field, reason, **extra)
