"""In-process Python API door — thin re-export of the door library (TN-17).

The desktop backend consumes this in-process where co-located. Every shared
capability is ``is``-identical to ``qmn.doors.library``. No product UI and no
operator CLI.
"""

from __future__ import annotations

from typing import Final

from qmn.doors.library import (
    EVIDENCE_CAPABILITIES,
    EVIDENCE_CHANNEL_BUDGET_UNIT,
    LIBRARY_SURFACE,
    POWERS_CAPABILITIES,
    DoorRuntime,
    PowersEnactment,
    enact_power,
    library_capability_names,
    read_config_explanation,
    read_failure_detail,
    read_health,
    read_metrics,
    read_projections,
    read_status,
    stamp_evidence,
)

__all__ = [
    "API_DOOR",
    "EVIDENCE_CAPABILITIES",
    "EVIDENCE_CHANNEL_BUDGET_UNIT",
    "LIBRARY_SURFACE",
    "POWERS_CAPABILITIES",
    "DoorRuntime",
    "PowersEnactment",
    "api_door_name",
    "enact_power",
    "library_capability_names",
    "read_config_explanation",
    "read_failure_detail",
    "read_health",
    "read_metrics",
    "read_projections",
    "read_status",
    "stamp_evidence",
]

API_DOOR: Final[str] = "python_api"


def api_door_name() -> str:
    return API_DOOR
