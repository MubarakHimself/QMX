"""Named analysis methods owned by COMP-QMB (DEC-0273).

Story 35.1 ships ``analysis.project``: a projection saved view over one cited
CT-32 and its CT-29 stream. Story 35.2 refuses forbidden axes as path-dependent
and homes the view (ungoverned return value; governed-without-QMA sidecar).
``analysis.rerun`` is Story 35.3.
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

__all__ = [
    "ANALYSIS_PROJECT_CLASS",
    "ANALYSIS_PROJECT_IS_LIBRARY_OBJECT",
    "ANALYSIS_PROJECT_MINTS_CT32",
    "ANALYSIS_PROJECT_MINTS_EXPERIMENT_SPEC",
    "ANALYSIS_PROJECT_OCCUPANCY",
    "ANALYSIS_PROJECT_OPENS_SQLITE",
    "CLAIM_CLASS_PROJECTION",
    "FORBIDDEN_PROJECTION_AXES",
    "METHOD_PROJECTION",
    "PERMITTED_PREDICATE_KEYS",
    "PROJECTION_HOMES",
    "PROJECTION_SIDECAR_FILENAME",
    "ProjectionView",
    "analysis_project_identity",
    "apply_projection_predicate",
    "cite_projection",
    "project",
]
