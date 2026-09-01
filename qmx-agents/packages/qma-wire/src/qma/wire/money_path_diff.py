"""Named field-level diff schema for money_path_relevant candidates (FR-Q53).

``qma.wire.money_path_field_diff.v1`` is the sole schema an ``approval_request``
for a money_path_relevant StrategyHandle candidate may carry. Validation lives
here so the daemon never invents a local schema name (CT-47; DEC-0313).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final

from qma.core.ports.handles import MONEY_PATH_FIELD_DIFF_SCHEMA, FieldLevelDiff
from qma.wire.schemas import validate_instance
from qmf.core import Result, is_ok

__all__ = [
    "MONEY_PATH_FIELD_DIFF_SCHEMA",
    "MONEY_PATH_FIELD_DIFF_SCHEMA_FILE",
    "MONEY_PATH_FIELD_DIFF_SCHEMA_NAME",
    "validate_money_path_field_diff",
]


MONEY_PATH_FIELD_DIFF_SCHEMA_NAME: Final[str] = "money_path_field_diff"
MONEY_PATH_FIELD_DIFF_SCHEMA_FILE: Final[str] = "money_path_field_diff.v1.schema.json"


def validate_money_path_field_diff(payload: object) -> Result[FieldLevelDiff]:
    """Validate ``payload`` against the named qma-wire schema, then the core type."""
    checked = validate_instance(payload, MONEY_PATH_FIELD_DIFF_SCHEMA_NAME)
    if not is_ok(checked):
        return checked
    body: Mapping[str, object] = checked.value
    return FieldLevelDiff.try_create(
        schema=body.get("schema", MONEY_PATH_FIELD_DIFF_SCHEMA),
        candidate_ref=body.get("candidate_ref"),
        predecessor_ref=body.get("predecessor_ref"),
        fields=body.get("fields"),
    )
