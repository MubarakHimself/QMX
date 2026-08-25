"""CLI-door rendering of CT-04 typed refusals (AR-58).

The library RETURNS a refusal; this module encodes it as one JSON object for
stderr. The door never raises a typed refusal — programmer error stays an
exception on a different channel.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import cast

from qmf.core.refusal import TypedRefusal

__all__ = ["render_refusal"]


def render_refusal(refusal: TypedRefusal) -> str:
    """Encode a typed refusal as machine-readable JSON (category, context, retryability)."""
    payload: dict[str, object] = {
        "category": refusal.category.value,
        "context": _jsonable(refusal.context),
        "retryability": refusal.retryability.value,
    }
    descriptor = refusal.after_condition_descriptor
    if descriptor is not None:
        payload["after_condition_descriptor"] = descriptor
    return json.dumps(payload, ensure_ascii=False)


def _jsonable(value: object) -> object:
    """Turn refusal context into JSON-native dict/list/str/int/bool/null."""
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, (str, int)):
        return value
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return {str(key): _jsonable(item) for key, item in mapping.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        sequence = cast("Sequence[object]", value)
        return [_jsonable(item) for item in sequence]
    return str(value)
