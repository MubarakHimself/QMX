"""Private CT-04 refusal builders for qmn.data (TN-13 / Story 27.2)."""

from __future__ import annotations

from collections.abc import Mapping

from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "clean_token",
    "invalid",
    "policy",
    "storage",
    "transient",
    "unavailable",
    "unsupported",
]


def clean_token(value: object) -> str | None:
    """Return ``value`` when it is a non-blank string; else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    return None


def _build(
    category: RefusalCategory,
    field: str,
    reason: str,
    extra: Mapping[str, object],
    *,
    retryability: Retryability = Retryability.NO,
    after_condition_descriptor: str | None = None,
) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(dict(extra))
    return TypedRefusal(
        category=category,
        retryability=retryability,
        context=context,
        after_condition_descriptor=after_condition_descriptor,
    )


def invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``invalid input`` refusal."""
    return _build(RefusalCategory.INVALID_INPUT, field, reason, extra)


def storage(
    field: str,
    reason: str,
    *,
    retryability: Retryability = Retryability.YES,
    after_condition_descriptor: str | None = None,
    **extra: object,
) -> TypedRefusal:
    """A ``storage failure`` refusal (unreachable bucket / rclone / corrupt copy)."""
    return _build(
        RefusalCategory.STORAGE_FAILURE,
        field,
        reason,
        extra,
        retryability=retryability,
        after_condition_descriptor=after_condition_descriptor,
    )


def policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """A ``policy rejection`` refusal."""
    return _build(RefusalCategory.POLICY_REJECTION, field, reason, extra)


def unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    """An ``unsupported capability`` refusal."""
    return _build(RefusalCategory.UNSUPPORTED_CAPABILITY, field, reason, extra)


def unavailable(
    field: str,
    reason: str,
    *,
    retryability: Retryability = Retryability.NO,
    after_condition_descriptor: str | None = None,
    **extra: object,
) -> TypedRefusal:
    """An ``unavailable dependency`` refusal."""
    return _build(
        RefusalCategory.UNAVAILABLE_DEPENDENCY,
        field,
        reason,
        extra,
        retryability=retryability,
        after_condition_descriptor=after_condition_descriptor,
    )


def transient(
    field: str,
    reason: str,
    *,
    retryability: Retryability = Retryability.NO,
    **extra: object,
) -> TypedRefusal:
    """A ``transient venue failure`` (rate-limit / block). Default: do not retry."""
    return _build(
        RefusalCategory.TRANSIENT_VENUE_FAILURE,
        field,
        reason,
        extra,
        retryability=retryability,
    )
