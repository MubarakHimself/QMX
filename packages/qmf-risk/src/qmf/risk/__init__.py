"""qmf.risk — the Book/BMS template grammar, dimensional law, and numeraire.

Roster edge module of the QMF V1 uv workspace: it defines the risk contract
surface on ``qmf-core`` nouns, imports **only** ``qmf-core``, and is imported by
nothing — the default-deny dependency direction (L30/DEC-0120) holds by
construction. Every contract here is ratified ``defined-unwired``: records reach
the registry and ``qmf-data`` only through the application composition root, and no
live binding, order, mode transition, or flatten is authorized by this code
(AR-06; DEC-0158).

Story 10.1 lands the first work unit — the template grammar, the dimensional law,
and the USD numeraire that CT-22 (the Book definition) and CT-27 (the BMS
definition) are built from (FR-035; DEC-0144, DEC-0154, DEC-0157):

* :mod:`qmf.risk.grammar` — the four-part template variable
  (:class:`~qmf.risk.grammar.TemplateVariable`: a closed-vocabulary unit-kind, an
  exact-rational/scaled-integer value or a :class:`~qmf.risk.grammar.NotYetRuled`
  blank, a :class:`~qmf.risk.grammar.UiEditability` flag, an
  :class:`~qmf.risk.grammar.AdmissionImpact`) with attached
  :class:`~qmf.risk.grammar.VariableEvidence` that is never a ratified constant, and
  the :class:`~qmf.risk.grammar.TemplateSection`;
* :mod:`qmf.risk.dimensional` — the symbolic dimensional checker
  (:func:`~qmf.risk.dimensional.check_formula`), the ratified sizing-ladder
  formulas with executable worked examples, and the dead
  :data:`~qmf.risk.dimensional.FORM_0006` retained as the permanent negative test;
* :mod:`qmf.risk.numeraire` — the USD :data:`~qmf.risk.numeraire.V1_NUMERAIRE`, the
  ``accounting_currency`` law, and the Book-limit unit law (lots refuse);
* :mod:`qmf.risk.versioning` — git-logic-without-git version graphs
  (:class:`~qmf.risk.versioning.TemplateVersionGraph`) and the derivable
  :func:`~qmf.risk.versioning.diff_variable_maps`;
* :mod:`qmf.risk.templates` — the :class:`~qmf.risk.templates.BookDefinition`
  (CT-22) and :class:`~qmf.risk.templates.BmsDefinition` (CT-27) containers with
  their ``fp1`` identity.

Story 10.2 lands R's three typed faces, the units-only sizing shape, and the
full-loss-price law (FR-028; CT-22, CT-23; DEC-0154):

* :mod:`qmf.risk.r_faces` — the frozen-at-admission money-bearing R faces
  (:class:`~qmf.risk.r_faces.RFaces`: ``original_risk_distance`` +
  ``original_risk_amount``, with the realized ``r_multiple`` derived never stored),
  the :data:`~qmf.risk.r_faces.FULL_ORIGINAL_LOSS`/:data:`~qmf.risk.r_faces.BREAKEVEN`
  anchors, the full-loss-price law
  (:func:`~qmf.risk.r_faces.derive_original_risk_distance`,
  :func:`~qmf.risk.r_faces.admit_entry_r_faces` sizing the amount through a venue
  value-factor), the no-scale-in guard (:func:`~qmf.risk.r_faces.check_no_scale_in`),
  and the Money↔R crossing over a named rate
  (:func:`~qmf.risk.r_faces.r_to_money`, :func:`~qmf.risk.r_faces.money_to_r`,
  :func:`~qmf.risk.r_faces.average_r_multiple`);
* :mod:`qmf.risk.sizing` — the units-only ``money_rules`` shape
  (:data:`~qmf.risk.sizing.MONEY_RULES_UNIT_KINDS`,
  :func:`~qmf.risk.sizing.validate_money_rules`), the B-split
  (:func:`~qmf.risk.sizing.check_b_split`), the pure-R
  ``seat_r_ceiling ≤ seat_loss_run_allowance`` value bound
  (:func:`~qmf.risk.sizing.check_seat_r_ceiling`), and the one-floor law
  (:func:`~qmf.risk.sizing.reconcile_loss_floor`).
"""

from __future__ import annotations

from qmf.risk.dimensional import (
    FORM_0006,
    LADDER_FORMULAS,
    SEAT_R_CEILING_CONSTRAINT,
    BinOp,
    ComparisonOp,
    ConstraintSpec,
    FormulaOp,
    FormulaSpec,
    Ref,
    WorkedExample,
    check_constraint,
    check_formula,
    derive_unit_kind,
)
from qmf.risk.grammar import (
    AdmissionImpact,
    AuthorityGrade,
    NotYetRuled,
    SourceLayer,
    TemplateSection,
    TemplateVariable,
    UiEditability,
    VariableEvidence,
    value_unit_kind,
)
from qmf.risk.numeraire import (
    BOOK_LIMIT_UNIT_KINDS,
    V1_NUMERAIRE,
    validate_accounting_currency,
    validate_book_limit,
)
from qmf.risk.r_faces import (
    BREAKEVEN,
    FULL_ORIGINAL_LOSS,
    Direction,
    RFaces,
    admit_entry_r_faces,
    average_r_multiple,
    check_no_scale_in,
    derive_original_risk_distance,
    money_to_r,
    r_to_money,
)
from qmf.risk.sizing import (
    BENCH_THRESHOLD_VARIABLE,
    LEASH_B_SPLIT_UNIT_KINDS,
    MONEY_RULES_UNIT_KINDS,
    SEAT_LOSS_RUN_ALLOWANCE_VARIABLE,
    check_b_split,
    check_seat_r_ceiling,
    reconcile_loss_floor,
    validate_money_rules,
)
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BMS_SECTIONS,
    BOOK_CONTRACT_FORMAT_VERSION,
    BOOK_SECTIONS,
    BmsDefinition,
    BookDefinition,
)
from qmf.risk.versioning import (
    CurrentPointer,
    TemplateVersionGraph,
    VariableDiff,
    VersionEdgeKind,
    diff_variable_maps,
)

__all__ = [
    "BENCH_THRESHOLD_VARIABLE",
    "BMS_CONTRACT_FORMAT_VERSION",
    "BMS_SECTIONS",
    "BOOK_CONTRACT_FORMAT_VERSION",
    "BOOK_LIMIT_UNIT_KINDS",
    "BOOK_SECTIONS",
    "BREAKEVEN",
    "FORM_0006",
    "FULL_ORIGINAL_LOSS",
    "LADDER_FORMULAS",
    "LEASH_B_SPLIT_UNIT_KINDS",
    "MONEY_RULES_UNIT_KINDS",
    "SEAT_LOSS_RUN_ALLOWANCE_VARIABLE",
    "SEAT_R_CEILING_CONSTRAINT",
    "V1_NUMERAIRE",
    "AdmissionImpact",
    "AuthorityGrade",
    "BinOp",
    "BmsDefinition",
    "BookDefinition",
    "ComparisonOp",
    "ConstraintSpec",
    "CurrentPointer",
    "Direction",
    "FormulaOp",
    "FormulaSpec",
    "NotYetRuled",
    "RFaces",
    "Ref",
    "SourceLayer",
    "TemplateSection",
    "TemplateVariable",
    "TemplateVersionGraph",
    "UiEditability",
    "VariableDiff",
    "VariableEvidence",
    "VersionEdgeKind",
    "WorkedExample",
    "__version__",
    "admit_entry_r_faces",
    "average_r_multiple",
    "check_b_split",
    "check_constraint",
    "check_formula",
    "check_no_scale_in",
    "check_seat_r_ceiling",
    "derive_original_risk_distance",
    "derive_unit_kind",
    "diff_variable_maps",
    "money_to_r",
    "r_to_money",
    "reconcile_loss_floor",
    "validate_accounting_currency",
    "validate_book_limit",
    "validate_money_rules",
    "value_unit_kind",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
