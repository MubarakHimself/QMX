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

Story 10.3 lands three-layer admission, the admission bar, and blank-blocks-live
money (FR-027, FR-035; CT-22, CT-27; DEC-0146):

* :mod:`qmf.risk.admission_bar` — the admission-bar requirement grammar
  (:class:`~qmf.risk.admission_bar.AdmissionRequirement`: an opaque ``measure_identity``,
  a mandatory unit, a :class:`~qmf.risk.admission_bar.Comparison`, a threshold
  discriminated union :class:`~qmf.risk.admission_bar.RuledThreshold` |
  :class:`~qmf.risk.grammar.NotYetRuled` with the key always present, and
  :class:`~qmf.risk.admission_bar.EvidenceRequirements`), the
  :class:`~qmf.risk.admission_bar.AdmissionBar` set with **no composite score**
  (:func:`~qmf.risk.admission_bar.reject_bar_aggregate`,
  :func:`~qmf.risk.admission_bar.evaluate_bar` returning a per-requirement verdict),
  blank-blocks-live (:func:`~qmf.risk.admission_bar.check_live_binding_admissible`),
  no-paper-role-gates-live (:func:`~qmf.risk.admission_bar.check_no_paper_role_gates_live`),
  and the declared float→exact comparison rule
  (:class:`~qmf.risk.admission_bar.ComparisonRule`,
  :func:`~qmf.risk.admission_bar.evaluate_requirement`);
* :mod:`qmf.risk.control_rank` — the BMS-declared
  :class:`~qmf.risk.control_rank.ControlRankTable` and its total-order/uniqueness law
  (:func:`~qmf.risk.control_rank.check_control_rank_uniqueness`: two control-action
  kinds sharing a rank is ``invalid input``);
* :mod:`qmf.risk.admission` — the three ordered layers
  (:data:`~qmf.risk.admission.ADMISSION_LAYERS`,
  :func:`~qmf.risk.admission.run_layer1_linters`,
  :func:`~qmf.risk.admission.run_layer2_shakedown`,
  :func:`~qmf.risk.admission.assemble_admission_page`,
  :func:`~qmf.risk.admission.sign_admission`, :func:`~qmf.risk.admission.admit`) with
  no trial period, probation window, or paper-performance gate
  (:func:`~qmf.risk.admission.reject_forbidden_admission_gate`), and the worked-example
  recompute over the cited-producer seam (:class:`~qmf.risk.admission.ProducerContract`,
  :func:`~qmf.risk.admission.check_worked_examples`).

Story 10.4 lands the binding chain, the identity trinity, and the bind-time capability
check (FR-031, FR-027; CT-28, CT-27; DEC-0143, DEC-0158):

* :mod:`qmf.risk.binding` — the :class:`~qmf.risk.binding.BookBindingRecord` on the
  tuple ``(BookInstanceId, BmsInstanceId, VenueId, AccountId, world)`` with ``role``
  deliberately absent, its full-record fingerprint the binding **epoch**; the identity
  trinity (a Book version fingerprint, the operator-minted
  :class:`~qmf.risk.binding.BookInstance` / :class:`~qmf.risk.binding.BookInstanceId`,
  and the content-derived :class:`~qmf.risk.binding.BmsInstanceId`); the mandatory
  complete per-counter :class:`~qmf.risk.binding.StateCarry` with its
  ``carry``-requires-:class:`~qmf.risk.binding.SignedLedgerEdge` invariant and the
  independent :class:`~qmf.risk.binding.ContinuesPerformanceEdge`; the
  :func:`~qmf.risk.binding.bind_time_capability_check` over the CT-18 projection
  (:class:`~qmf.risk.binding.VenueBindingProfile`,
  :class:`~qmf.risk.binding.BookBindingRequirements`) with the settlement-currency
  policy rejection and the netted-account shared-flatten refusal; the
  :func:`~qmf.risk.binding.check_rank_table_non_contradiction`; and the append-only
  :class:`~qmf.risk.binding.BookBindingLog` guarding epoch uniqueness and
  one-BMS-at-a-time.
"""

from __future__ import annotations

from qmf.risk.admission import (
    ADMISSION_LAYERS,
    FORBIDDEN_ADMISSION_GATES,
    LOSS_RUNWAY_PRODUCER,
    AdmissionLayer,
    AdmissionPage,
    AdmittedBinding,
    CallableProducer,
    Layer1Result,
    Layer2Result,
    OperatorSignature,
    ProducerContract,
    admit,
    assemble_admission_page,
    check_worked_examples,
    recompute_worked_example,
    reject_forbidden_admission_gate,
    run_layer1_linters,
    run_layer2_shakedown,
    sign_admission,
    sizing_producer,
)
from qmf.risk.admission_bar import (
    PAPER_ACCOUNT_ROLES,
    AdmissionBar,
    AdmissionRequirement,
    Band,
    Comparison,
    ComparisonRule,
    EvidenceRequirements,
    PendingSlot,
    RequirementVerdict,
    RuledThreshold,
    Threshold,
    TieDisposition,
    bar_is_blank,
    check_live_binding_admissible,
    check_no_paper_role_gates_live,
    evaluate_bar,
    evaluate_requirement,
    is_paper_role,
    reject_bar_aggregate,
)
from qmf.risk.binding import (
    STATE_CARRY_COUNTERS,
    BindingLineageEdgeKind,
    BindingState,
    BmsInstanceId,
    BookBindingLog,
    BookBindingRecord,
    BookBindingRequirements,
    BookInstance,
    BookInstanceId,
    CapabilityCheckResult,
    ContinuesPerformanceEdge,
    PairingRecord,
    PositionModel,
    SignedLedgerEdge,
    StateCarry,
    StateCarryChoice,
    StateCarryCounter,
    VenueBindingProfile,
    bind_time_capability_check,
    check_rank_table_non_contradiction,
)
from qmf.risk.control_rank import (
    ControlActionKind,
    ControlRankRow,
    ControlRankTable,
    check_control_rank_uniqueness,
)
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
    "ADMISSION_LAYERS",
    "BENCH_THRESHOLD_VARIABLE",
    "BMS_CONTRACT_FORMAT_VERSION",
    "BMS_SECTIONS",
    "BOOK_CONTRACT_FORMAT_VERSION",
    "BOOK_LIMIT_UNIT_KINDS",
    "BOOK_SECTIONS",
    "BREAKEVEN",
    "FORBIDDEN_ADMISSION_GATES",
    "FORM_0006",
    "FULL_ORIGINAL_LOSS",
    "LADDER_FORMULAS",
    "LEASH_B_SPLIT_UNIT_KINDS",
    "LOSS_RUNWAY_PRODUCER",
    "MONEY_RULES_UNIT_KINDS",
    "PAPER_ACCOUNT_ROLES",
    "SEAT_LOSS_RUN_ALLOWANCE_VARIABLE",
    "SEAT_R_CEILING_CONSTRAINT",
    "STATE_CARRY_COUNTERS",
    "V1_NUMERAIRE",
    "AdmissionBar",
    "AdmissionImpact",
    "AdmissionLayer",
    "AdmissionPage",
    "AdmissionRequirement",
    "AdmittedBinding",
    "AuthorityGrade",
    "Band",
    "BinOp",
    "BindingLineageEdgeKind",
    "BindingState",
    "BmsDefinition",
    "BmsInstanceId",
    "BookBindingLog",
    "BookBindingRecord",
    "BookBindingRequirements",
    "BookDefinition",
    "BookInstance",
    "BookInstanceId",
    "CallableProducer",
    "CapabilityCheckResult",
    "Comparison",
    "ComparisonOp",
    "ComparisonRule",
    "ConstraintSpec",
    "ContinuesPerformanceEdge",
    "ControlActionKind",
    "ControlRankRow",
    "ControlRankTable",
    "CurrentPointer",
    "Direction",
    "EvidenceRequirements",
    "FormulaOp",
    "FormulaSpec",
    "Layer1Result",
    "Layer2Result",
    "NotYetRuled",
    "OperatorSignature",
    "PairingRecord",
    "PendingSlot",
    "PositionModel",
    "ProducerContract",
    "RFaces",
    "Ref",
    "RequirementVerdict",
    "RuledThreshold",
    "SignedLedgerEdge",
    "SourceLayer",
    "StateCarry",
    "StateCarryChoice",
    "StateCarryCounter",
    "TemplateSection",
    "TemplateVariable",
    "TemplateVersionGraph",
    "Threshold",
    "TieDisposition",
    "UiEditability",
    "VariableDiff",
    "VariableEvidence",
    "VenueBindingProfile",
    "VersionEdgeKind",
    "WorkedExample",
    "__version__",
    "admit",
    "admit_entry_r_faces",
    "assemble_admission_page",
    "average_r_multiple",
    "bar_is_blank",
    "bind_time_capability_check",
    "check_b_split",
    "check_constraint",
    "check_control_rank_uniqueness",
    "check_formula",
    "check_live_binding_admissible",
    "check_no_paper_role_gates_live",
    "check_no_scale_in",
    "check_rank_table_non_contradiction",
    "check_seat_r_ceiling",
    "check_worked_examples",
    "derive_original_risk_distance",
    "derive_unit_kind",
    "diff_variable_maps",
    "evaluate_bar",
    "evaluate_requirement",
    "is_paper_role",
    "money_to_r",
    "r_to_money",
    "recompute_worked_example",
    "reconcile_loss_floor",
    "reject_bar_aggregate",
    "reject_forbidden_admission_gate",
    "run_layer1_linters",
    "run_layer2_shakedown",
    "sign_admission",
    "sizing_producer",
    "validate_accounting_currency",
    "validate_book_limit",
    "validate_money_rules",
    "value_unit_kind",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
