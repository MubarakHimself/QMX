"""Node-config surface (TN-18): resolved artifact home, no runtime folds.

Compilation applies roster → BMS → Book → node-defaults with value-status rows.
There is no invocation or operator-CLI override layer (DEC-0203, DEC-0211).
Story 25.19 / TN-22 composes roster-driven multi-account and multi-broker
runtime keys from eligibility rows — never a venue/account singleton.
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
    refuse_unknown_compile_layer,
    validate_registry_row_schema,
)
from qmn.config.countersign import apply_settings_edit, countersign_value_status
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
from qmn.config.roster import (
    ADDING_BROKER_REQUIRES_CORE_CODE_CHANGE,
    HAS_DEFAULT_VENUE_ACCOUNT_SINGLETON,
    ROSTER_SURFACE,
    STATE_CARRY_COUNTERS,
    AccountBindingDecl,
    BindingRuntimeKey,
    BookBindingDecl,
    CommandStreamPlan,
    CommandStreamRuntimeKey,
    ConnectionRuntimeKey,
    PacerBucketPlan,
    PositionModelDecl,
    RosterRuntimeComposition,
    SensingOnlyDecl,
    SensingOnlyPlan,
    StateCarryChoice,
    ThrottleScope,
    compose_roster_runtime,
    streams_independent,
    writer_streams_from_composition,
)
from qmn.config.toolkit import config_explain, config_init, config_validate, explain_rows

CONFIG_SURFACE: Final[str] = "qmn.config"

__all__ = [
    "ADDING_BROKER_REQUIRES_CORE_CODE_CHANGE",
    "COMPILE_LAYERS",
    "COMPONENT_COUNTS",
    "CONFIG_SURFACE",
    "EXPECTED_BLANK_EFFECT_COUNTS",
    "EXPECTED_ROW_COUNT",
    "HAS_DEFAULT_VENUE_ACCOUNT_SINGLETON",
    "HAS_INVOCATION_OVERRIDE_LAYER",
    "LIVENESS_HEARTBEAT_NAMES",
    "NODE_CONFIG_ARTIFACT_NAME",
    "NODE_CONFIG_CLASS",
    "NODE_CONFIG_FORMAT_VERSION",
    "RETIRED_DEAD_MANS_SWITCH_NAMES",
    "ROSTER_SURFACE",
    "RUNTIME_FOLD_KEYS",
    "STATE_CARRY_COUNTERS",
    "VALUE_STATUSES",
    "VALUE_STATUS_BLANK",
    "VALUE_STATUS_PROVISIONAL",
    "VALUE_STATUS_RATIFIED",
    "VALUE_STATUS_REQUIRED_ROWS",
    "AccountBindingDecl",
    "BindingRuntimeKey",
    "BookBindingDecl",
    "CommandStreamPlan",
    "CommandStreamRuntimeKey",
    "ConnectionRuntimeKey",
    "PacerBucketPlan",
    "PositionModelDecl",
    "ResolvedNodeConfig",
    "ResolvedValueRow",
    "RosterRuntimeComposition",
    "SensingOnlyDecl",
    "SensingOnlyPlan",
    "StateCarryChoice",
    "ThrottleScope",
    "apply_settings_edit",
    "blank_effect_coverage",
    "compile_layers",
    "compile_node_config",
    "compose_roster_runtime",
    "config_explain",
    "config_init",
    "config_validate",
    "countersign_value_status",
    "explain_rows",
    "is_secret_ref_key",
    "live_role_blocked_by",
    "provisional_live_gates_like_blank",
    "refuse_unknown_compile_layer",
    "rows_by_name",
    "streams_independent",
    "validate_registry_row_schema",
    "writer_streams_from_composition",
]
