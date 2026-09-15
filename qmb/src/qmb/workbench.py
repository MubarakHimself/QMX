"""Door-derived workbench lanes (DEC-0270 / SCN-0015 / Story 36.4).

Lane comes from which door was called, never a caller-declared field.
QMB ledger lines stamp ``workbench_lane=governed`` for every orchestrator
spawn, including those QMA placed. Coordinated lives only on the Experiment
Ledger. Ungoverned ``qmb.run()`` writes nothing.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import Ok, Result, TypedRefusal
from qmf.risk.performance import PerformanceResult

from qmb._refuse import policy
from qmb.ledger.line import (
    WORKBENCH_LANE_COORDINATED,
    WORKBENCH_LANE_GOVERNED,
    WORKBENCH_LANE_UNGOVERNED,
    WORKBENCH_LANES,
)
from qmb.registryread.library import KIND_OWNER, LibraryKind, register_library_kind

__all__ = [
    "CALLER_DECLARED_LANE_FIELDS",
    "L33_GRADUATION_IS_THIS_SPAWN",
    "L33_GRADUATION_IS_WORKBENCH_LANE",
    "QMB_LEDGER_WORKBENCH_LANE",
    "WORKBENCH_LANES",
    "WORKBENCH_LANE_COORDINATED",
    "WORKBENCH_LANE_GOVERNED",
    "WORKBENCH_LANE_UNGOVERNED",
    "DoorDerivedLabels",
    "admit_library_object",
    "door_derived_labels",
    "graduate_ungoverned_via_spawn",
    "refuse_caller_declared_lane_fields",
    "ungoverned_run_identity",
]

CALLER_DECLARED_LANE_FIELDS: Final[frozenset[str]] = frozenset(
    {"analysis_method", "lane", "workbench_lane"}
)
QMB_LEDGER_WORKBENCH_LANE: Final[str] = WORKBENCH_LANE_GOVERNED
L33_GRADUATION_IS_THIS_SPAWN: Final[bool] = False
L33_GRADUATION_IS_WORKBENCH_LANE: Final[bool] = False
_CT32_CLASSES: Final[frozenset[str]] = frozenset({"performance-result", "ct-32", "ct32"})


@dataclass(frozen=True, slots=True)
class DoorDerivedLabels:
    """Two honest labels on two objects. Never one collapsed field."""

    door: str
    qmb_ledger_workbench_lane: str | None
    experiment_ledger_workbench_lane: str | None
    writes_qmb_ledger: bool
    writes_ct32_registry_record: bool
    mints_experiment_spec: bool
    is_library_object: bool
    l33_graduation_is_this_spawn: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "door": self.door,
                "experiment_ledger_workbench_lane": self.experiment_ledger_workbench_lane,
                "is_library_object": self.is_library_object,
                "l33_graduation_is_this_spawn": self.l33_graduation_is_this_spawn,
                "mints_experiment_spec": self.mints_experiment_spec,
                "qmb_ledger_workbench_lane": self.qmb_ledger_workbench_lane,
                "writes_ct32_registry_record": self.writes_ct32_registry_record,
                "writes_qmb_ledger": self.writes_qmb_ledger,
            }
        )


def door_derived_labels(
    *,
    ct47: object = False,
    orchestrator: object = False,
    lane: object = None,
    workbench_lane: object = None,
    analysis_method: object = None,
) -> Result[DoorDerivedLabels]:
    """Select the lane from the door. Caller-declared flags are refused."""
    blocked = refuse_caller_declared_lane_fields(
        lane=lane,
        workbench_lane=workbench_lane,
        analysis_method=analysis_method,
    )
    if blocked is not None:
        return blocked
    if ct47 is True:
        return Ok(
            DoorDerivedLabels(
                door=WORKBENCH_LANE_COORDINATED,
                qmb_ledger_workbench_lane=WORKBENCH_LANE_GOVERNED,
                experiment_ledger_workbench_lane=WORKBENCH_LANE_COORDINATED,
                writes_qmb_ledger=True,
                writes_ct32_registry_record=True,
                mints_experiment_spec=False,
                is_library_object=True,
            )
        )
    if orchestrator is True:
        return Ok(
            DoorDerivedLabels(
                door=WORKBENCH_LANE_GOVERNED,
                qmb_ledger_workbench_lane=WORKBENCH_LANE_GOVERNED,
                experiment_ledger_workbench_lane=None,
                writes_qmb_ledger=True,
                writes_ct32_registry_record=True,
                mints_experiment_spec=False,
                is_library_object=True,
            )
        )
    return Ok(
        DoorDerivedLabels(
            door=WORKBENCH_LANE_UNGOVERNED,
            qmb_ledger_workbench_lane=None,
            experiment_ledger_workbench_lane=None,
            writes_qmb_ledger=False,
            writes_ct32_registry_record=False,
            mints_experiment_spec=False,
            is_library_object=False,
        )
    )


def ungoverned_run_identity() -> dict[str, object]:
    """Identity of the ungoverned ``qmb.run()`` door. Not ``loop_identity``."""
    return {
        "door": WORKBENCH_LANE_UNGOVERNED,
        "experiment_ledger_workbench_lane": None,
        "is_library_object": False,
        "l33_graduation_is_this_spawn": L33_GRADUATION_IS_THIS_SPAWN,
        "l33_graduation_is_workbench_lane": L33_GRADUATION_IS_WORKBENCH_LANE,
        "mints_experiment_spec": False,
        "qmb_ledger_workbench_lane": None,
        "writes_ct32_registry_record": False,
        "writes_qmb_ledger": False,
    }


def refuse_caller_declared_lane_fields(
    extra: Mapping[str, object] | None = None,
    **fields: object,
) -> TypedRefusal | None:
    """Refuse payload / CT-32 / B-4 lane flags. Door selection is not a field."""
    present: list[str] = []
    if extra is not None:
        present.extend(key for key in CALLER_DECLARED_LANE_FIELDS if key in extra)
    for key, value in fields.items():
        if key in CALLER_DECLARED_LANE_FIELDS and value is not None:
            present.append(key)
    if not present:
        return None
    return policy(
        present[0],
        "lane is derived from which door is called, never a caller-declared "
        "flag on the payload, CT-32, or B-4; extending CT-32 or B-4 is a spine "
        "amendment, not a connect fix (FR-W03; FR-W07; DEC-0270)",
        given=present,
        spine_amendment=True,
        qmb_ledger_workbench_lane=WORKBENCH_LANE_GOVERNED,
        experiment_ledger_workbench_lane=WORKBENCH_LANE_COORDINATED,
    )


def graduate_ungoverned_via_spawn(*_args: object, **_kwargs: object) -> Result[None]:
    """L33 is two-artifact registration, not this orchestrator spawn."""
    return policy(
        "graduation",
        "L33 graduation is a separate two-artifact registration act, not an "
        "orchestrator spawn and not a workbench_lane (FR-W04; DEC-0270)",
        is_this_spawn=L33_GRADUATION_IS_THIS_SPAWN,
        is_workbench_lane=L33_GRADUATION_IS_WORKBENCH_LANE,
    )


def admit_library_object(
    value: object,
    *,
    registry_record: object = False,
) -> Result[LibraryKind]:
    """Cite a Library kind. A returned CT-32-shaped value is not a Library object."""
    if registry_record is True:
        return register_library_kind("CT-32")
    if _is_ct32_shaped(value):
        return policy(
            "library",
            "a returned CT-32-shaped value is not a Library object; Library "
            "cites registry records, never an ungoverned run() return "
            "(FR-W04; SCN-0015; DEC-0270)",
            is_library_object=False,
            writes_ct32_registry_record=False,
            owner=KIND_OWNER,
        )
    return policy(
        "library",
        "Library cites existing fp1 registry records; an ungoverned return is "
        "not a Library object (FR-W04; DEC-0271)",
        is_library_object=False,
        owner=KIND_OWNER,
        given=repr(type(value).__name__),
    )


def _is_ct32_shaped(value: object) -> bool:
    if isinstance(value, PerformanceResult):
        return True
    if isinstance(value, Mapping):
        body = cast("Mapping[str, object]", value)
        token = body.get("class")
        if isinstance(token, str) and token.strip().casefold() in _CT32_CLASSES:
            return True
        return "ct32_fingerprint" in body or "performance_result" in body
    result = getattr(value, "performance_result", None)
    if result is not None:
        return True
    identity = getattr(value, "fp1_identity", None)
    if callable(identity):
        payload = identity()
        if isinstance(payload, Mapping):
            body = cast("Mapping[str, object]", payload)
            token = body.get("class")
            if isinstance(token, str) and token.strip().casefold() in _CT32_CLASSES:
                return True
    return False
