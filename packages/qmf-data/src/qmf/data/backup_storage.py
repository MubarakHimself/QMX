"""CT-14 storage-failure remap helpers for off-machine copy/restore."""

from __future__ import annotations

from qmf.core import Retryability, TypedRefusal, fingerprint_bytes, unpersistable


def fp1_of(payload: bytes) -> str:
    """The self-describing fp1 string for ciphertext bytes."""
    return fingerprint_bytes(payload).value


def remapped_adapter_context(refusal: TypedRefusal, *, copy_version: int) -> dict[str, object]:
    """Remap a miswired adapter's refusal context for the CT-14 storage-failure remap (AC4; R-007).

    The adapter returned a non-``storage failure`` category; AC4 remaps it to a *returned*
    ``storage failure`` at this boundary. The adapter's own ``reason`` context key — which
    every qmf refusal builder (``policy_rejection`` / ``invalid_input`` / ``unpersistable``)
    sets unconditionally — is namespaced to ``adapter_reason`` so it never collides with the
    reserved ``reason`` key :func:`qmf.core.unpersistable` sets from its own argument. Handing
    that reserved key through would be refused as a programmer error and *raise* across the
    boundary, which R-007/DEC-0109 forbids.
    """
    remapped: dict[str, object] = dict(refusal.context)
    adapter_reason = remapped.pop("reason", None)
    if adapter_reason is not None:
        remapped["adapter_reason"] = adapter_reason
    remapped["signal"] = "storage-refused"
    remapped["adapter_category"] = refusal.category.value
    remapped["copy_version"] = copy_version
    return remapped


def storage_failure(reason: str, *, retryable: bool, context: dict[str, object]) -> TypedRefusal:
    """Build a CT-04 ``storage failure`` refusal for a CT-14 boundary fault (AC4)."""
    return unpersistable(
        reason,
        retryability=Retryability.YES if retryable else Retryability.NO,
        context=context,
    )
