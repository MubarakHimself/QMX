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
    "BMS_CONTRACT_FORMAT_VERSION",
    "BMS_SECTIONS",
    "BOOK_CONTRACT_FORMAT_VERSION",
    "BOOK_LIMIT_UNIT_KINDS",
    "BOOK_SECTIONS",
    "FORM_0006",
    "LADDER_FORMULAS",
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
    "FormulaOp",
    "FormulaSpec",
    "NotYetRuled",
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
    "check_constraint",
    "check_formula",
    "derive_unit_kind",
    "diff_variable_maps",
    "validate_accounting_currency",
    "validate_book_limit",
    "value_unit_kind",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
