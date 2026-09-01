"""Compile ``registry:ksa_effect_matrix`` cells — shape only, no values (Story 26.1).

Each cell declares one CT-30 effect from ``suspend_new | drain | flatten``, a typed
subject scope, one closed AD-36 satisfaction predicate, and
``routes-to-paper | blocks-paper``. Blank or provisional-evidence cells block
``role = live`` and soak as declared. This module supplies **no** matrix numeric
or severity-mapping values — the operator ratifies cell contents before soak
(GAP-0050; FTR-07; AR-87; DEC-0192, DEC-0231, DEC-0237).
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

from qmf.core import Ok, Result, is_refusal
from qmf.risk.control_action import SatisfactionPredicate, SubjectScope
from qmf.risk.control_rank import ControlActionKind

from qmn.protection._refuse import clean_token, invalid, policy
from qmn.protection.ksa import (
    KSA_LEVELS,
    KSA_TRIGGER_CLASSES,
    KsaLevel,
    KsaTriggerClass,
    PaperDisposition,
    paper_disposition_for,
)

__all__ = [
    "EFFECT_MATRIX_BLANK_EFFECTS",
    "KSA_EFFECT_KINDS",
    "KSA_EFFECT_MATRIX_REGISTRY_KEY",
    "VALUE_STATUSES",
    "VALUE_STATUS_BLANK",
    "VALUE_STATUS_PROVISIONAL",
    "VALUE_STATUS_RATIFIED",
    "CompiledEffectMatrix",
    "KsaEffectMatrixCell",
    "ValueStatus",
    "cell_blocks_role_live",
    "cell_blocks_soak",
    "compile_effect_matrix",
    "compile_ksa_effect_cell",
    "matrix_blocks_role_live",
    "matrix_blocks_soak",
    "matrix_supplies_no_default_values",
]

KSA_EFFECT_MATRIX_REGISTRY_KEY: Final[str] = "ksa_effect_matrix"

# Effects a matrix cell may declare — resume is never a matrix effect (CT-30).
KSA_EFFECT_KINDS: Final[frozenset[ControlActionKind]] = frozenset(
    {
        ControlActionKind.SUSPEND_NEW,
        ControlActionKind.DRAIN,
        ControlActionKind.FLATTEN,
    }
)

VALUE_STATUS_BLANK: Final[str] = "blank"
VALUE_STATUS_PROVISIONAL: Final[str] = "provisional-evidence"
VALUE_STATUS_RATIFIED: Final[str] = "ratified"
VALUE_STATUSES: Final[frozenset[str]] = frozenset(
    {VALUE_STATUS_BLANK, VALUE_STATUS_PROVISIONAL, VALUE_STATUS_RATIFIED}
)

# Registry blank_effect for ksa_effect_matrix (DEC-0256).
EFFECT_MATRIX_BLANK_EFFECTS: Final[tuple[str, ...]] = ("blocks-role-live", "blocks-soak")

ValueStatus = Literal["blank", "provisional-evidence", "ratified"]

# Predicate defaults pinned by AD-36 — cells may restate them, never weaken them.
_REQUIRED_PREDICATE: Final[Mapping[ControlActionKind, SatisfactionPredicate]] = MappingProxyType(
    {
        ControlActionKind.SUSPEND_NEW: SatisfactionPredicate.NEVER_AUTO,
        ControlActionKind.DRAIN: SatisfactionPredicate.NEVER_AUTO,
        ControlActionKind.FLATTEN: SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT,
    }
)


@dataclass(frozen=True, slots=True)
class KsaEffectMatrixCell:
    """One compiled ``(trigger, level)`` severity-policy cell (TN-7).

    Carries shape only: CT-30 effect, typed scope, satisfaction predicate, and
    paper disposition. No numeric threshold or donor default lives here.
    """

    trigger_class: KsaTriggerClass
    level: KsaLevel
    effect: ControlActionKind
    subject_scope: SubjectScope
    satisfaction_predicate: SatisfactionPredicate
    paper_disposition: PaperDisposition
    value_status: ValueStatus

    def fp1_identity(self) -> dict[str, object]:
        """Pinned identity content for one matrix cell (no numeric payload)."""
        return {
            "class": "ksa-effect-matrix-cell",
            "trigger_class": self.trigger_class.value,
            "level": self.level.value,
            "effect": self.effect.value,
            "subject_scope": self.subject_scope.value,
            "satisfaction_predicate": self.satisfaction_predicate.value,
            "paper_disposition": self.paper_disposition.value,
            "value_status": self.value_status,
            "registry_key": KSA_EFFECT_MATRIX_REGISTRY_KEY,
        }


@dataclass(frozen=True, slots=True)
class CompiledEffectMatrix:
    """Compiled matrix artifact — cells optional; blank status is first-class."""

    value_status: ValueStatus
    cells: tuple[KsaEffectMatrixCell, ...]
    blank_effect: tuple[str, ...] = EFFECT_MATRIX_BLANK_EFFECTS

    @property
    def blocks_role_live(self) -> bool:
        """Blank or provisional matrix blocks ``role = live``."""
        return matrix_blocks_role_live(self)

    @property
    def blocks_soak(self) -> bool:
        """Blank or provisional matrix blocks soak."""
        return matrix_blocks_soak(self)


def matrix_supplies_no_default_values() -> bool:
    """FTR-07 / GAP-0050: this package ships no matrix cell values."""
    return True


def compile_ksa_effect_cell(
    *,
    trigger_class: object,
    level: object,
    effect: object,
    subject_scope: object,
    satisfaction_predicate: object,
    paper_disposition: object = None,
    value_status: object,
) -> Result[KsaEffectMatrixCell]:
    """Compile one matrix cell — shape validation only; no invented values."""
    status = _coerce_value_status(value_status)
    if is_refusal(status):
        return status
    if status.value == VALUE_STATUS_BLANK:
        return invalid(
            "value_status",
            "a blank matrix cell cannot be compiled into an executable effect; "
            "blank cells block role=live and soak as declared",
            value_status=status.value,
            blank_effect=list(EFFECT_MATRIX_BLANK_EFFECTS),
        )

    trigger = _coerce_trigger(trigger_class)
    if is_refusal(trigger):
        return trigger
    resolved_level = _coerce_level(level)
    if is_refusal(resolved_level):
        return resolved_level
    resolved_effect = _coerce_effect(effect)
    if is_refusal(resolved_effect):
        return resolved_effect
    resolved_scope = _coerce_subject_scope(subject_scope)
    if is_refusal(resolved_scope):
        return resolved_scope
    resolved_predicate = _coerce_predicate(satisfaction_predicate)
    if is_refusal(resolved_predicate):
        return resolved_predicate

    required = _REQUIRED_PREDICATE[resolved_effect.value]
    if (
        resolved_effect.value
        in {
            ControlActionKind.SUSPEND_NEW,
            ControlActionKind.DRAIN,
        }
        and resolved_predicate.value is not SatisfactionPredicate.NEVER_AUTO
    ):
        return invalid(
            "satisfaction_predicate",
            "suspend_new and drain are never-auto by rule — a cell may not weaken them",
            effect=resolved_effect.value.value,
            given=resolved_predicate.value.value,
            required=required.value,
        )
    if resolved_effect.value is ControlActionKind.FLATTEN and resolved_predicate.value not in {
        SatisfactionPredicate.SCOPE_FLAT_AT_RECONCILED_VERDICT,
        SatisfactionPredicate.NO_PENDING_ORDERS_AT_RECONCILED_VERDICT,
    }:
        return invalid(
            "satisfaction_predicate",
            "flatten cells declare scope-flat-at-reconciled-verdict or "
            "no-pending-orders-at-reconciled-verdict; never-auto is reserved for "
            "human-only clears",
            given=resolved_predicate.value.value,
        )

    disposition = _resolve_disposition(trigger.value, paper_disposition)
    if is_refusal(disposition):
        return disposition

    if status.value == VALUE_STATUS_PROVISIONAL:
        # Compilable for paper; still live/soak blocking until countersigned.
        pass

    return Ok(
        KsaEffectMatrixCell(
            trigger_class=trigger.value,
            level=resolved_level.value,
            effect=resolved_effect.value,
            subject_scope=resolved_scope.value,
            satisfaction_predicate=resolved_predicate.value,
            paper_disposition=disposition.value,
            value_status=status.value,  # type: ignore[arg-type]
        )
    )


def compile_effect_matrix(
    *,
    value_status: object,
    cells: Sequence[Mapping[str, object]] | Iterable[Mapping[str, object]] | None = None,
) -> Result[CompiledEffectMatrix]:
    """Compile the matrix artifact from value-status plus optional cell maps.

    A blank or empty provisional matrix is a valid compiled artifact that blocks
    live and soak. Ratified status requires at least one successfully compiled
    cell. No donor/default cell values are invented here (FTR-07).
    """
    status = _coerce_value_status(value_status)
    if is_refusal(status):
        return status

    raw_cells: list[Mapping[str, object]] = []
    if cells is not None:
        for item in cells:
            if not isinstance(item, Mapping):
                return invalid(
                    "cells",
                    "each matrix cell declaration is a mapping",
                    given=repr(item),
                )
            raw_cells.append(item)

    if status.value == VALUE_STATUS_BLANK:
        if raw_cells:
            return policy(
                "value_status",
                "a blank ksa_effect_matrix carries no cells — operator ratifies values "
                "before soak (GAP-0050); this story supplies none",
                cell_count=len(raw_cells),
            )
        return Ok(
            CompiledEffectMatrix(value_status=VALUE_STATUS_BLANK, cells=())  # type: ignore[arg-type]
        )

    compiled: list[KsaEffectMatrixCell] = []
    for item in raw_cells:
        cell = compile_ksa_effect_cell(
            trigger_class=item.get("trigger_class"),
            level=item.get("level"),
            effect=item.get("effect"),
            subject_scope=item.get("subject_scope"),
            satisfaction_predicate=item.get("satisfaction_predicate"),
            paper_disposition=item.get("paper_disposition"),
            value_status=item.get("value_status", status.value),
        )
        if is_refusal(cell):
            return cell
        compiled.append(cell.value)

    if status.value == VALUE_STATUS_RATIFIED and not compiled:
        return invalid(
            "cells",
            "a ratified ksa_effect_matrix requires compiled cells; blank cells are not "
            "ratified values",
        )

    return Ok(
        CompiledEffectMatrix(
            value_status=status.value,  # type: ignore[arg-type]
            cells=tuple(compiled),
        )
    )


def cell_blocks_role_live(cell: KsaEffectMatrixCell | ValueStatus | str) -> bool:
    """True when a cell or status blocks ``role = live``."""
    status = _status_of(cell)
    return status in {VALUE_STATUS_BLANK, VALUE_STATUS_PROVISIONAL}


def cell_blocks_soak(cell: KsaEffectMatrixCell | ValueStatus | str) -> bool:
    """True when a cell or status blocks soak (pre-soak ratification)."""
    status = _status_of(cell)
    return status in {VALUE_STATUS_BLANK, VALUE_STATUS_PROVISIONAL}


def matrix_blocks_role_live(matrix: CompiledEffectMatrix) -> bool:
    """Blank or provisional matrix (or any such cell) blocks live role."""
    if matrix.value_status in {VALUE_STATUS_BLANK, VALUE_STATUS_PROVISIONAL}:
        return True
    return any(cell_blocks_role_live(cell) for cell in matrix.cells)


def matrix_blocks_soak(matrix: CompiledEffectMatrix) -> bool:
    """Blank or provisional matrix (or any such cell) blocks soak."""
    if matrix.value_status in {VALUE_STATUS_BLANK, VALUE_STATUS_PROVISIONAL}:
        return True
    return any(cell_blocks_soak(cell) for cell in matrix.cells)


def _status_of(cell: KsaEffectMatrixCell | ValueStatus | str) -> str:
    if isinstance(cell, KsaEffectMatrixCell):
        return cell.value_status
    return str(cell)


def _coerce_value_status(value: object) -> Result[str]:
    token = clean_token(value) if isinstance(value, str) else None
    if token is None or token not in VALUE_STATUSES:
        return invalid(
            "value_status",
            "ksa_effect_matrix value-status is blank|provisional-evidence|ratified",
            given=repr(value),
            allowed=sorted(VALUE_STATUSES),
        )
    return Ok(token)


def _coerce_trigger(value: object) -> Result[KsaTriggerClass]:
    if isinstance(value, KsaTriggerClass):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(KsaTriggerClass(value))
        except ValueError:
            pass
    return invalid(
        "trigger_class",
        "matrix cells name a registered KSA trigger class",
        given=repr(value),
        allowed=[t.value for t in KSA_TRIGGER_CLASSES],
    )


def _coerce_level(value: object) -> Result[KsaLevel]:
    if isinstance(value, KsaLevel):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(KsaLevel(value))
        except ValueError:
            pass
    return invalid(
        "level",
        "matrix cells name a fixed KSA level GREEN|YELLOW|ORANGE|RED|BLACK",
        given=repr(value),
        allowed=[level.value for level in KSA_LEVELS],
    )


def _coerce_effect(value: object) -> Result[ControlActionKind]:
    if isinstance(value, ControlActionKind):
        kind = value
    elif isinstance(value, str):
        try:
            kind = ControlActionKind(value)
        except ValueError:
            return invalid(
                "effect",
                "matrix cell effect is one CT-30 kind from suspend_new|drain|flatten",
                given=repr(value),
                allowed=[k.value for k in KSA_EFFECT_KINDS],
            )
    else:
        return invalid(
            "effect",
            "matrix cell effect is one CT-30 kind from suspend_new|drain|flatten",
            given=repr(value),
            allowed=[k.value for k in KSA_EFFECT_KINDS],
        )
    if kind not in KSA_EFFECT_KINDS:
        return invalid(
            "effect",
            "resume is never a matrix cell effect; cells declare suspend_new|drain|flatten",
            given=kind.value,
            allowed=[k.value for k in KSA_EFFECT_KINDS],
        )
    return Ok(kind)


def _coerce_subject_scope(value: object) -> Result[SubjectScope]:
    if isinstance(value, SubjectScope):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(SubjectScope(value))
        except ValueError:
            pass
    return invalid(
        "subject_scope",
        "matrix cells declare a typed CT-30 subject scope",
        given=repr(value),
        allowed=[s.value for s in SubjectScope],
    )


def _coerce_predicate(value: object) -> Result[SatisfactionPredicate]:
    if isinstance(value, SatisfactionPredicate):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(SatisfactionPredicate(value))
        except ValueError:
            pass
    return invalid(
        "satisfaction_predicate",
        "matrix cells declare one closed AD-36 satisfaction predicate",
        given=repr(value),
        allowed=[p.value for p in SatisfactionPredicate],
    )


def _resolve_disposition(
    trigger: KsaTriggerClass,
    paper_disposition: object,
) -> Result[PaperDisposition]:
    fixed = paper_disposition_for(trigger)
    if is_refusal(fixed):
        return fixed
    if paper_disposition is None:
        return Ok(fixed.value)
    if isinstance(paper_disposition, PaperDisposition):
        declared = paper_disposition
    elif isinstance(paper_disposition, str):
        try:
            declared = PaperDisposition(paper_disposition)
        except ValueError:
            return invalid(
                "paper_disposition",
                "paper disposition is routes-to-paper|blocks-paper",
                given=repr(paper_disposition),
            )
    else:
        return invalid(
            "paper_disposition",
            "paper disposition is routes-to-paper|blocks-paper",
            given=repr(paper_disposition),
        )
    if declared is not fixed.value:
        return invalid(
            "paper_disposition",
            "KSA trigger paper disposition is fixed by AD-35 invariant, not author choice",
            trigger_class=trigger.value,
            given=declared.value,
            required=fixed.value.value,
        )
    return Ok(declared)
