"""Named analysis methods owned by COMP-QMB (DEC-0273).

Story 35.1 ships ``analysis.project``: a projection saved view over one cited
CT-32 and its CT-29 stream. Story 35.2 refuses forbidden axes as path-dependent
and homes the view (ungoverned return value; governed-without-QMA sidecar).
Story 35.3 ships ``analysis.rerun``: a new governed QMB run whose canonical
artifact is a new CT-32.
Story 35.4 ships complete Book/BMS ``dev``-zone candidates; evaluation is
``analysis.rerun`` citing that fingerprint.
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
from qmb.analysis.variants import (
    ANALYSIS_VARIANT_CLASS,
    BOOK_BMS_MINT_SURFACE,
    BOOK_BMS_SHAPE_OWNER,
    MONEY_PATH_FIELD_DIFF_SCHEMA,
    MONEY_PATH_RELEVANT_FIELDS,
    QMA_CANDIDATE_ORIGIN,
    VARIANT_ZONE,
    BookBmsVariant,
    book_bms_variant_identity,
    evaluate_book_bms_variant,
    register_book_bms_variant,
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
    "ANALYSIS_VARIANT_CLASS",
    "BOOK_BMS_MINT_SURFACE",
    "BOOK_BMS_SHAPE_OWNER",
    "CLAIM_CLASS_PROJECTION",
    "FORBIDDEN_PROJECTION_AXES",
    "METHOD_PROJECTION",
    "METHOD_RERUN",
    "MONEY_PATH_FIELD_DIFF_SCHEMA",
    "MONEY_PATH_RELEVANT_FIELDS",
    "PERMITTED_PREDICATE_KEYS",
    "PROJECTION_HOMES",
    "PROJECTION_SIDECAR_FILENAME",
    "QMA_CANDIDATE_ORIGIN",
    "VARIANT_ZONE",
    "WORKBENCH_LANE_GOVERNED",
    "BookBmsVariant",
    "ProjectionView",
    "RerunOutcome",
    "analysis_project_identity",
    "analysis_rerun_identity",
    "apply_projection_predicate",
    "book_bms_variant_identity",
    "cite_projection",
    "evaluate_book_bms_variant",
    "project",
    "register_book_bms_variant",
    "rerun",
]
