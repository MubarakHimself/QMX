"""Private CT-04 refusal builders for qmn.host.

Domain failure is returned, never raised across the composition-root surface.
"""

from __future__ import annotations

from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = ["clean_token", "invalid", "policy", "unavailable", "unsupported"]


def clean_token(value: object) -> str | None:
    """Return ``value`` when it is a non-blank string; else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


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


def unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``unsupported capability`` refusal."""
    return _build(RefusalCategory.UNSUPPORTED_CAPABILITY, field, reason, **extra)


def unavailable(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``unavailable dependency`` refusal."""
    return _build(RefusalCategory.UNAVAILABLE_DEPENDENCY, field, reason, **extra)
