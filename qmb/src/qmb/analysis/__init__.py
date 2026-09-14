"""Named analysis methods owned by COMP-QMB (DEC-0273).

Story 35.1 ships ``analysis.project``: a projection saved view over one cited
CT-32 and its CT-29 stream. Story 35.2 refuses forbidden axes as path-dependent
and homes the view (ungoverned return value; governed-without-QMA sidecar).
Story 35.3 ships ``analysis.rerun``: a new governed QMB run whose canonical
artifact is a new CT-32.
"""

from __future__ import annotations

from qmb.analysis.project import (
    ANALYSIS_PROJECT_CLASS,
    ANALYSIS_PROJECT_IS_LIBRARY_OBJECT,
    ANALYSIS_PROJECT_MINTS_CT32,
    ANALYSIS_PROJECT_MINTS_EXPERIMENT_SPEC,
    ANALYSIS_PROJECT_OCCUPANCY,
    ANALYSIS_PROJECT_OPENS_SQLITE,
    CLAIM_CLASS_PROJECTION,
    FORBIDDEN_PROJECTION_AXES,
    METHOD_PROJECTION,
    PERMITTED_PREDICATE_KEYS,
    PROJECTION_HOMES,
    PROJECTION_SIDECAR_FILENAME,
    ProjectionView,
    analysis_project_identity,
    apply_projection_predicate,
    cite_projection,
    project,
)
from qmb.analysis.rerun import (
    ANALYSIS_RERUN_CLASS,
    ANALYSIS_RERUN_MINTS_CT32,
    ANALYSIS_RERUN_MINTS_EXPERIMENT_SPEC,
    ANALYSIS_RERUN_OCCUPANCY,
    METHOD_RERUN,
    WORKBENCH_LANE_GOVERNED,
    RerunOutcome,
    analysis_rerun_identity,
    rerun,
)

__all__ = [
    "ANALYSIS_PROJECT_CLASS",
    "ANALYSIS_PROJECT_IS_LIBRARY_OBJECT",
    "ANALYSIS_PROJECT_MINTS_CT32",
    "ANALYSIS_PROJECT_MINTS_EXPERIMENT_SPEC",
    "ANALYSIS_PROJECT_OCCUPANCY",
    "ANALYSIS_PROJECT_OPENS_SQLITE",
    "ANALYSIS_RERUN_CLASS",
    "ANALYSIS_RERUN_MINTS_CT32",
    "ANALYSIS_RERUN_MINTS_EXPERIMENT_SPEC",
    "ANALYSIS_RERUN_OCCUPANCY",
    "CLAIM_CLASS_PROJECTION",
    "FORBIDDEN_PROJECTION_AXES",
    "METHOD_PROJECTION",
    "METHOD_RERUN",
    "PERMITTED_PREDICATE_KEYS",
    "PROJECTION_HOMES",
    "PROJECTION_SIDECAR_FILENAME",
    "WORKBENCH_LANE_GOVERNED",
    "ProjectionView",
    "RerunOutcome",
    "analysis_project_identity",
    "analysis_rerun_identity",
    "apply_projection_predicate",
    "cite_projection",
    "project",
    "rerun",
]
