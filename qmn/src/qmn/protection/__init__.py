"""Protection surface (TN-7/TN-8): scoped KSA fold and effect-matrix compile.

Story 26.1 lands the monotone KSA severity fold, operator-only ``resume``, and
``registry:ksa_effect_matrix`` cell compilation. Matrix **values** stay
operator-owned (GAP-0050 / FTR-07) — blank or provisional cells block live and
soak as declared. Story 26.2 fills the ranked control dispatcher.
"""

from __future__ import annotations

from typing import Final

from qmn.protection.effect_matrix import (
    EFFECT_MATRIX_BLANK_EFFECTS,
    KSA_EFFECT_KINDS,
    KSA_EFFECT_MATRIX_REGISTRY_KEY,
    VALUE_STATUS_BLANK,
    VALUE_STATUS_PROVISIONAL,
    VALUE_STATUS_RATIFIED,
    VALUE_STATUSES,
    CompiledEffectMatrix,
    KsaEffectMatrixCell,
    cell_blocks_role_live,
    cell_blocks_soak,
    compile_effect_matrix,
    compile_ksa_effect_cell,
    matrix_blocks_role_live,
    matrix_blocks_soak,
    matrix_supplies_no_default_values,
)
from qmn.protection.ksa import (
    AUTO_DEESCALATION_EVENTS,
    KSA_LEVELS,
    KSA_TRIGGER_CLASSES,
    LEVEL_RANK,
    OPERATOR_AUTHORITY,
    PAPER_DISPOSITION_BY_TRIGGER,
    KsaEnforcementScope,
    KsaEscalationRecord,
    KsaLevel,
    KsaTriggerClass,
    LevelEpoch,
    PaperDisposition,
    ResumeRecord,
    effective_ksa_level,
    fold_ksa_level,
    ksa_levels,
    ksa_trigger_classes,
    mint_escalation,
    mint_level_epoch,
    paper_disposition_for,
    resume,
    scope_covers_stream,
    stream_blocked_by_escalation,
)

__all__ = [
    "AUTO_DEESCALATION_EVENTS",
    "EFFECT_MATRIX_BLANK_EFFECTS",
    "KSA_EFFECT_KINDS",
    "KSA_EFFECT_MATRIX_REGISTRY_KEY",
    "KSA_LEVELS",
    "KSA_TRIGGER_CLASSES",
    "LEVEL_RANK",
    "OPERATOR_AUTHORITY",
    "PAPER_DISPOSITION_BY_TRIGGER",
    "PROTECTION_SURFACE",
    "VALUE_STATUSES",
    "VALUE_STATUS_BLANK",
    "VALUE_STATUS_PROVISIONAL",
    "VALUE_STATUS_RATIFIED",
    "CompiledEffectMatrix",
    "KsaEffectMatrixCell",
    "KsaEnforcementScope",
    "KsaEscalationRecord",
    "KsaLevel",
    "KsaTriggerClass",
    "LevelEpoch",
    "PaperDisposition",
    "ResumeRecord",
    "cell_blocks_role_live",
    "cell_blocks_soak",
    "compile_effect_matrix",
    "compile_ksa_effect_cell",
    "effective_ksa_level",
    "fold_ksa_level",
    "ksa_levels",
    "ksa_trigger_classes",
    "matrix_blocks_role_live",
    "matrix_blocks_soak",
    "matrix_supplies_no_default_values",
    "mint_escalation",
    "mint_level_epoch",
    "paper_disposition_for",
    "resume",
    "scope_covers_stream",
    "stream_blocked_by_escalation",
]

PROTECTION_SURFACE: Final[str] = "qmn.protection"
