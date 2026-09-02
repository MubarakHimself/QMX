"""Private CT-04 refusal builders for ``qmn.replay`` (TN-21 / Story 27.7)."""

from __future__ import annotations

from collections.abc import Mapping

from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = ["clean_token", "invalid", "policy", "storage", "unavailable"]


def clean_token(value: object) -> str | None:
    """Return a stripped non-blank string, else ``None``."""
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


def policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """A ``policy rejection`` refusal."""
    return _build(RefusalCategory.POLICY_REJECTION, field, reason, extra)


def storage(
    field: str,
    reason: str,
    *,
    retryability: Retryability = Retryability.YES,
    after_condition_descriptor: str | None = None,
    **extra: object,
) -> TypedRefusal:
    """A ``storage failure`` refusal — unpersistable terminal ledger append."""
    return _build(
        RefusalCategory.STORAGE_FAILURE,
        field,
        reason,
        extra,
        retryability=retryability,
        after_condition_descriptor=after_condition_descriptor,
    )


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
