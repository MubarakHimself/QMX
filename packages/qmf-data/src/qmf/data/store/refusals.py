"""Typed-refusal builders for the qmf-data store seam (CT-04 categories).

Every public store operation returns value-or-refusal; a physical failure is
**translated to a typed refusal at the boundary**, never raised across a package
seam (AC4; DEC-0109). These helpers build the three refusal categories the store
surfaces — ``invalid input``, ``policy rejection``, and ``storage failure`` — from
``qmf-core``'s CT-04 vocabulary, so the store never invents a category and never
raises a domain failure. ``storage failure`` reuses ``qmf.core.unpersistable`` so a
store outage carries the same block-on-unpersistable retryability shape a sink does.

Stdlib + qmf-core only; the engine libraries never reach this module.
"""

from __future__ import annotations

from collections.abc import Mapping

from qmf.core import (
    RefusalCategory,
    Retryability,
    TypedRefusal,
    unpersistable,
)
from qmf.data.store.engines import StoreEngineError

__all__ = [
    "invalid_input",
    "policy_rejection",
    "storage_failure",
    "translate_engine_failure",
]


def invalid_input(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build an ``invalid input`` refusal (retryability ``no``).

    A malformed argument — a fingerprint that does not parse, a row that is not a
    mapping, a fingerprint that does not match the presented bytes — is a caller
    mistake, not a transient condition; ``context`` names the offending ``field``.
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def policy_rejection(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build a ``policy rejection`` refusal (retryability ``no``).

    A cross-world read, a ``world = simulated`` write, and a second writer reaching
    for a held stream are governance refusals — the store is structurally forbidden
    from proceeding, not merely unable to (DEC-0110, DEC-0113, DEC-0117).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def storage_failure(
    reason: str,
    *,
    retryability: Retryability = Retryability.YES,
    context: Mapping[str, object] | None = None,
) -> TypedRefusal:
    """Build a ``storage failure`` refusal for a translated engine exception (AC4).

    The engine (the store library) raised; the boundary catches it and returns this
    instead of propagating it across the package seam, and never reports persistence
    success. A transient outage is retryable (``yes``); a corrupt or truncated store
    is not (``no``). ``reason`` is register-facing plain language for the operator.
    """
    return unpersistable(
        reason, retryability=retryability, context=dict(context) if context else None
    )


def translate_engine_failure(exc: StoreEngineError) -> TypedRefusal:
    """Translate a normalized engine exception to a ``storage failure`` refusal (AC4).

    The one place a caught :class:`~qmf.data.store.engines.StoreEngineError` becomes a
    typed refusal: a transient outage is retryable, a corrupt/truncated store is not,
    and the failing engine plus its detail ride the machine-readable context. Every
    boundary funnels its ``except StoreEngineError`` here, so no engine exception ever
    crosses a package seam and no persistence success is reported on failure.
    """
    return storage_failure(
        exc.reason,
        retryability=Retryability.YES if exc.retryable else Retryability.NO,
        context={"engine": exc.engine, **exc.detail},
    )
