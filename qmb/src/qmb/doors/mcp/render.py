"""MCP-door rendering of CT-04 typed refusals (AR-58).

When this door ships, JSON-RPC ``error.data`` carries the refusal union
verbatim — the same category / context / retryability object the CLI writes
to stderr. The scaffold pins that shape now; invocation still refuses.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import cast

from qmf.core.refusal import TypedRefusal

__all__ = ["error_data", "render_error"]


def error_data(refusal: TypedRefusal) -> dict[str, object]:
    """The refusal union as a JSON-native object (category, context, retryability)."""
    payload: dict[str, object] = {
        "category": refusal.category.value,
        "context": _jsonable(refusal.context),
        "retryability": refusal.retryability.value,
    }
    descriptor = refusal.after_condition_descriptor
    if descriptor is not None:
        payload["after_condition_descriptor"] = descriptor
    return payload


def render_error(refusal: TypedRefusal) -> dict[str, object]:
    """JSON-RPC error object whose ``data`` is the refusal union verbatim."""
    return {"data": error_data(refusal)}


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
