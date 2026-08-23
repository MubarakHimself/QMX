"""Private CT-04 refusal builders for the qml scaffold.

Every public qml operation returns ``Result[T] = Ok[T] | TypedRefusal``; domain
failure is never raised across the boundary (CT-04; DEC-0109). Not re-exported.
"""

from __future__ import annotations

from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = ["clean_token", "invalid", "policy", "unsupported"]


def clean_token(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    Presence-only: the returned token is the caller's string unchanged — never
    stripped, cased, or parsed (AD-9 opaque-token discipline).
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _build(category: RefusalCategory, field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(category=category, retryability=Retryability.NO, context=context)


def invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``invalid input`` refusal — a malformed value part, a caller mistake."""
    return _build(RefusalCategory.INVALID_INPUT, field, reason, **extra)


def policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """A ``policy rejection`` refusal — both conformance layers must pass to mint."""
    return _build(RefusalCategory.POLICY_REJECTION, field, reason, **extra)


def unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``unsupported capability`` refusal — an unknown format version or kind."""
    return _build(RefusalCategory.UNSUPPORTED_CAPABILITY, field, reason, **extra)
