"""Private CT-04 refusal builders for the qmb scaffold.

Every public qmb operation returns ``Result[T] = Ok[T] | TypedRefusal``; domain
failure is never raised across the boundary (CT-04; DEC-0109). Not re-exported.
"""

from __future__ import annotations

from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = ["clean_token", "invalid", "policy", "stale", "unavailable", "unsupported"]


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
    """A ``policy rejection`` refusal — a governed-evidence or world-policy miss."""
    return _build(RefusalCategory.POLICY_REJECTION, field, reason, **extra)


def unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``unsupported capability`` refusal — a door or format not in V1."""
    return _build(RefusalCategory.UNSUPPORTED_CAPABILITY, field, reason, **extra)


def unavailable(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``unavailable dependency`` refusal — a cited backend or fragment is missing."""
    return _build(RefusalCategory.UNAVAILABLE_DEPENDENCY, field, reason, **extra)


def stale(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An AD-11 ``stale evidence`` refusal — a superseded registry ref (B-15, FM-7).

    Returned, never raised. Severity is the caller's ``registry:qmb_stale_evidence_severity``
    token carried in ``context`` — that row is UI-editable and has no spine value.
    """
    return _build(RefusalCategory.STALE_EVIDENCE, field, reason, **extra)
