"""Node-config surface (TN-18): resolved artifact home, no runtime folds.

Compilation applies roster → BMS → Book → node-defaults with value-status rows.
There is no invocation or operator-CLI override layer (DEC-0203, DEC-0211).
"""

from __future__ import annotations

from typing import Final

from qmn.config.compiler import (
    COMPILE_LAYERS,
    HAS_INVOCATION_OVERRIDE_LAYER,
    NODE_CONFIG_ARTIFACT_NAME,
    NODE_CONFIG_CLASS,
    NODE_CONFIG_FORMAT_VERSION,
    RUNTIME_FOLD_KEYS,
    VALUE_STATUS_BLANK,
    VALUE_STATUS_PROVISIONAL,
    VALUE_STATUS_RATIFIED,
    VALUE_STATUSES,
    ResolvedNodeConfig,
    ResolvedValueRow,
    compile_layers,
    compile_node_config,
    is_secret_ref_key,
)
from qmn.config.countersign import countersign_value_status
from qmn.config.gating import (
    blank_effect_coverage,
    live_role_blocked_by,
    provisional_live_gates_like_blank,
)
from qmn.config.registry_catalog import (
    COMPONENT_COUNTS,
    EXPECTED_BLANK_EFFECT_COUNTS,
    EXPECTED_ROW_COUNT,
    LIVENESS_HEARTBEAT_NAMES,
    RETIRED_DEAD_MANS_SWITCH_NAMES,
    VALUE_STATUS_REQUIRED_ROWS,
    rows_by_name,
)
from qmn.config.toolkit import config_explain, config_init, config_validate, explain_rows

CONFIG_SURFACE: Final[str] = "qmn.config"

__all__ = [
    "COMPILE_LAYERS",
    "COMPONENT_COUNTS",
    "CONFIG_SURFACE",
    "EXPECTED_BLANK_EFFECT_COUNTS",
    "EXPECTED_ROW_COUNT",
    "HAS_INVOCATION_OVERRIDE_LAYER",
    "LIVENESS_HEARTBEAT_NAMES",
    "NODE_CONFIG_ARTIFACT_NAME",
    "NODE_CONFIG_CLASS",
    "NODE_CONFIG_FORMAT_VERSION",
    "RETIRED_DEAD_MANS_SWITCH_NAMES",
    "RUNTIME_FOLD_KEYS",
    "VALUE_STATUSES",
    "VALUE_STATUS_BLANK",
    "VALUE_STATUS_PROVISIONAL",
    "VALUE_STATUS_RATIFIED",
    "VALUE_STATUS_REQUIRED_ROWS",
    "ResolvedNodeConfig",
    "ResolvedValueRow",
    "blank_effect_coverage",
    "compile_layers",
    "compile_node_config",
    "config_explain",
    "config_init",
    "config_validate",
    "countersign_value_status",
    "explain_rows",
    "is_secret_ref_key",
    "live_role_blocked_by",
    "provisional_live_gates_like_blank",
    "rows_by_name",
]
