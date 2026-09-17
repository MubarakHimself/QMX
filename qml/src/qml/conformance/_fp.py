"""Shared fp1 coercion for conformance registration / mill admit."""

from __future__ import annotations

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid

__all__ = ["coerce_fp1"]


def coerce_fp1(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return invalid(
            field,
            "a Bot citation or research artifact is referenced by fp1:sha256:<hex>",
            given=repr(value),
        )
    return parsed
