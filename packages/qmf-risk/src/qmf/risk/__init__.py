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

Story 10.5 lands paper as a dated binding-epoch change — the CT-24 Book-mode /
binding-transition stream (FR-029, FR-033, FR-035; CT-24; DEC-0149):

* :mod:`qmf.risk.paper` — the three never-interchanged vocabularies
  (:class:`~qmf.risk.paper.BookMode` ``LIVE|PAPER``, :class:`~qmf.risk.paper.SeatState`
  ``active|benched``, and the binding state) with
  :func:`~qmf.risk.paper.validate_book_mode` refusing a seat/binding-state word in the
  mode field; the CT-24 :class:`~qmf.risk.paper.BindingTransitionRecord` and the
  :class:`~qmf.risk.paper.BindingTransitionStream` whose
  :meth:`~qmf.risk.paper.BindingTransitionStream.current_mode` is the read-time
  most-restrictive fold (:class:`~qmf.risk.paper.ModeFoldResult`); the routing-separated
  :func:`~qmf.risk.paper.resolve_execution_target` over
  (:class:`~qmf.risk.paper.BookMode`, :class:`~qmf.risk.paper.SeatState`,
  :class:`~qmf.risk.paper.ActiveControl` set) into a single
  :class:`~qmf.risk.paper.ExecutionTarget` /
  :class:`~qmf.risk.paper.ExecutionResolution`; the one-active-target-per-binding
  :class:`~qmf.risk.paper.PaperTargetLog`; frozen paper money as the
  :class:`~qmf.risk.paper.PaperEpochRecord` / :class:`~qmf.risk.paper.PaperEpochLog` with
  :func:`~qmf.risk.paper.reset_paper_epoch` and the money-boundary guard
  :func:`~qmf.risk.paper.reject_paper_pnl_to_treasury`; and the return-to-live asymmetry
  :func:`~qmf.risk.paper.authorize_return_to_live` /
  :func:`~qmf.risk.paper.mint_return_to_live_transition`.

Story 10.6 lands the CT-23 risk-evaluation door — Book-resolved sizing and
risk-monotonic intents (FR-028, FR-032; CT-23; DEC-0147, DEC-0177, DEC-0185):

* :mod:`qmf.risk.door` — the one inbound bot-to-Book door carrying exactly two typed
  families (:class:`~qmf.risk.door.IntentFamily`) plus declared evidence slots
  (:class:`~qmf.risk.door.EvidenceSlot`, :class:`~qmf.risk.door.CitedEvidence`) and
  nothing else, with an inbound ``requested_r`` an ``invalid input`` refusal because the
  bot may not size (:func:`~qmf.risk.door.reject_inbound_requested_r`,
  :class:`~qmf.risk.door.RiskEvaluationRequest`); the :class:`~qmf.risk.door.EntryIntent`
  with its advisory ``proposed_r`` and typed :class:`~qmf.risk.door.ReasonCode`, whose
  declared full-loss price is **derived at the Book door** by the per-family
  :class:`~qmf.risk.door.ExitLogicRef` (:func:`~qmf.risk.door.derive_full_loss_price_at_door`,
  :func:`~qmf.risk.door.admit_entry_intent` stamping the Book-resolved values onto a frozen
  :class:`~qmf.risk.door.AdmittedEntry`); the :class:`~qmf.risk.door.ExitIntent` V1 kinds
  (:class:`~qmf.risk.door.ExitKind`) with ``close_partial`` an ``unsupported capability``
  refusal (:func:`~qmf.risk.door.reject_close_partial`) and a
  :class:`~qmf.risk.door.TightenProtectiveStop` naming a direction and a bound never a
  price; the four :class:`~qmf.risk.door.RiskMonotonicViolation` policy rejections
  (:func:`~qmf.risk.door.check_stop_not_widened`,
  :func:`~qmf.risk.door.check_target_within_envelope`,
  :func:`~qmf.risk.door.check_no_reopen`, :func:`~qmf.risk.door.check_no_size_increase`);
  and the ExitLogicRef mode registry (:data:`~qmf.risk.door.EXIT_LOGIC_MODE_REGISTRY`,
  :data:`~qmf.risk.door.ADOPT_BOT_ADVISORY_STOP_MODE`) whose adopt-the-bot's-advisory-stop
  mode is an ``unavailable dependency`` refusal while CT-23 sits at
  :data:`~qmf.risk.door.CT23_ACTIVE_FORMAT_VERSION` (format 1)
  (:func:`~qmf.risk.door.check_exit_logic_mode_available`), with forward-compatible
  parsing (:func:`~qmf.risk.door.parse_inbound_intent`) that keeps format-1 artifacts
  readable forever and never breaks on an unknown optional field.

Story 10.7 lands CT-29 exit records, close reasons, whole-trade attribution, and the
bench fold (FR-032; CT-29; DEC-0155, DEC-0147):

* :mod:`qmf.risk.exit_record` — exactly one immutable
  :class:`~qmf.risk.exit_record.ExitRecord` per virtual (Book) position close carrying
  frozen ``original_risk_distance`` / ``original_risk_amount``, fill references,
  ``realized_pnl``, identity-bearing :class:`~qmf.risk.exit_record.CostComponent` set,
  a single-sourced :meth:`~qmf.risk.exit_record.ExitRecord.realized_r` (derived display
  never a second division), the :class:`~qmf.risk.exit_record.CloseReason` taxonomy
  (``kill_line_flat`` minted apart from ``protection_forced_flat``) with mechanism and
  :class:`~qmf.risk.exit_record.CloseOutcome` as separate fields, closing authority plus
  arbitration/venue reference, and account-binding role; whole-trade attribution
  (:func:`~qmf.risk.exit_record.attribute_whole_trade`,
  :func:`~qmf.risk.exit_record.partition_by_close_reason`); the read-time bench fold
  (:func:`~qmf.risk.exit_record.fold_bench`,
  :func:`~qmf.risk.exit_record.classify_bench_disposition`) over the
  :class:`~qmf.risk.exit_record.ExitRecordStream` bounded by the binding epoch;
  recording-precedes-interpretation
  (:func:`~qmf.risk.exit_record.check_recording_precedes_interpretation`); and the V1
  move-to-breakeven ratchet (:func:`~qmf.risk.exit_record.check_move_to_breakeven_ratchet`).

Story 10.8 lands CT-30 control actions — exit-preservation, kill switch vs kill line,
and same-tick rank arbitration (FR-033; CT-30; DEC-0150, DEC-0151):

* :mod:`qmf.risk.control_action` — the bounded
  :class:`~qmf.risk.control_action.ControlActionRecord` vocabulary
  (``suspend_new|drain|flatten|resume``) with
  :class:`~qmf.risk.control_action.AuthorityKind`,
  :class:`~qmf.risk.control_action.SubjectScope`, and
  :class:`~qmf.risk.control_action.SatisfactionPredicate`; the exit-preservation
  invariant (:func:`~qmf.risk.control_action.check_exit_preservation`,
  :func:`~qmf.risk.control_action.reject_blanket_command_pipe_block`); pinned scope
  resolution (:func:`~qmf.risk.control_action.resolve_subject_scope`); standing-intent
  journal-before-dispatch and the read-time fold
  (:func:`~qmf.risk.control_action.journal_before_dispatch`,
  :func:`~qmf.risk.control_action.fold_standing_intents`,
  :func:`~qmf.risk.control_action.reevaluate_standing_intent`);
  :class:`~qmf.risk.control_action.KillSwitch` vs
  :class:`~qmf.risk.control_action.KillLine` named apart; same-tick arbitration
  (:func:`~qmf.risk.control_action.arbitrate_same_tick`); and closed flatten authority
  (:func:`~qmf.risk.control_action.check_flatten_authority`).

Story 10.9 lands CT-31 protection windows — entries-only, instrument-scoped,
fail-closed (FR-033; CT-31; DEC-0152, DEC-0157):

* :mod:`qmf.risk.control_window` — one control-window contract for
  :class:`~qmf.risk.control_window.WindowKind` ``news|daily_dead_zone|
  session_handover_buffer`` with mandatory
  :class:`~qmf.risk.control_window.AnchorSide` on handover buffers; the
  :class:`~qmf.risk.control_window.ControlWindowRecord` as two instants plus
  resolved scope, reason class, format version, and optional
  :class:`~qmf.risk.control_window.FeedQuadruple`; declared
  :class:`~qmf.risk.control_window.CurrencyExposureRecord` scope
  (:func:`~qmf.risk.control_window.resolve_instrument_scope`,
  :func:`~qmf.risk.control_window.reject_symbol_currency_parse`); entries-only
  live-and-paper blocking
  (:func:`~qmf.risk.control_window.check_window_blocks_act`,
  :func:`~qmf.risk.control_window.evaluate_entry_under_windows`); the
  widen-never-shrink read-time fold
  (:func:`~qmf.risk.control_window.fold_effective_window`); fail-closed
  (:func:`~qmf.risk.control_window.fail_closed_on_uncertainty`); veto-path
  journaling (:func:`~qmf.risk.control_window.mint_veto_decision`); and
  :class:`~qmf.risk.control_window.WindowForcedFlatPolicy` (V1 declares none).
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
from qmf.risk.control_action import (
    ACTION_CLOSE_REASON_MAPPING,
    ADAPTER_SELF_FLATTEN_KINDS,
    COMPOSING_KIND_PAIRS,
    CT30_CONTRACT_FORMAT_VERSION,
    CT30_SCOPE_RESOLUTION_TABLE_VERSION,
    FLATTEN_AUTHORITIES,
    MONEY_BOUNDARIES_LEAVE_POSITIONS,
    NEVER_AUTO_KINDS,
    PROTECTION_WEIGHT,
    RISK_REDUCING_ACTS,
    ArbitrationDisposition,
    ArbitrationOutcome,
    AuthorityKind,
    CommandStreamKey,
    ControlActionRecord,
    ControlActionStream,
    EnforcementScope,
    KillLine,
    KillSwitch,
    MoneyBoundaryKind,
    PendingControlAction,
    ReconciliationVerdict,
    RiskReducingAct,
    SatisfactionPredicate,
    ScopeResolution,
    StandingIntentFold,
    StandingIntentStatus,
    SubjectScope,
    SuppressedControlAction,
    arbitrate_same_tick,
    check_exit_preservation,
    check_flatten_authority,
    close_reason_for,
    default_satisfaction_predicate,
    evaluate_satisfaction,
    fold_standing_intents,
    journal_before_dispatch,
    mint_control_action,
    mint_kill_line_breach,
    mint_kill_switch_action,
    reevaluate_standing_intent,
    reject_blanket_command_pipe_block,
    reject_money_boundary_flatten,
    resolve_subject_scope,
)
from qmf.risk.control_rank import (
    ControlActionKind,
    ControlRankRow,
    ControlRankTable,
    check_control_rank_uniqueness,
)
from qmf.risk.control_window import (
    CT31_CONTRACT_FORMAT_VERSION,
    DAILY_DEAD_ZONE_WIDTH_VARIABLE,
    NEWS_BLACKOUT_AFTER_VARIABLE,
    NEWS_BLACKOUT_BEFORE_VARIABLE,
    PROTECTION_WINDOW_VARIABLE_NAMES,
    RATIFIED_WINDOW_KINDS,
    SESSION_HANDOVER_BUFFER_ANCHOR_VARIABLE,
    SESSION_HANDOVER_BUFFER_WIDTH_VARIABLE,
    WINDOW_EFFECT,
    WINDOW_FORCED_FLAT_ARBITRATION_RANK,
    WINDOW_FORCED_FLAT_VARIABLE,
    WINDOW_TRIGGER_DISPOSITION,
    AnchorSide,
    ControlWindowRecord,
    ControlWindowRevisionLog,
    CurrencyExposureRecord,
    EffectiveWindow,
    FailClosedCause,
    FeedQuadruple,
    ProposedWindowAct,
    ResolvedInstrumentScope,
    ScopeResolutionDisposition,
    StandingExemptionRecord,
    VetoDecisionRecord,
    WindowBounds,
    WindowEffect,
    WindowEvaluation,
    WindowForcedFlatPolicy,
    WindowKind,
    append_window_revision,
    check_window_blocks_act,
    evaluate_entry_under_windows,
    fail_closed_on_uncertainty,
    fold_effective_window,
    instrument_in_scope,
    mint_control_window,
    mint_veto_decision,
    reject_click_exemption,
    reject_live_skip,
    reject_symbol_currency_parse,
    resolve_instrument_scope,
    window_in_force_at,
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
from qmf.risk.door import (
    ADOPT_BOT_ADVISORY_STOP_MODE,
    ADOPT_BOT_ADVISORY_STOP_MODE_ID,
    CT23_ACTIVE_FORMAT_VERSION,
    CT23_ADVISORY_STOP_FORMAT_VERSION,
    CT23_KNOWN_FORMAT_VERSIONS,
    EXIT_LOGIC_MODE_REGISTRY,
    AdmittedEntry,
    CitedEvidence,
    EntryIntent,
    EvidenceSlot,
    ExitIntent,
    ExitKind,
    ExitLogicMode,
    ExitLogicModule,
    ExitLogicRef,
    IntentFamily,
    ReasonCode,
    RiskEvaluationRequest,
    RiskMonotonicViolation,
    StopMoveDirection,
    TightenProtectiveStop,
    admit_entry_intent,
    check_exit_logic_mode_available,
    check_no_reopen,
    check_no_size_increase,
    check_stop_not_widened,
    check_target_within_envelope,
    derive_full_loss_price_at_door,
    evaluate_exit_intent,
    parse_inbound_intent,
    refuse_no_full_loss_price,
    reject_close_partial,
    reject_inbound_requested_r,
    reject_risk_monotonic_violation,
)
from qmf.risk.exit_record import (
    CLOSE_REASON_EVIDENCE_MAPPING,
    CT29_CONTRACT_FORMAT_VERSION,
    QUALIFYING_LOSS_THRESHOLD_VARIABLE,
    VENUE_AUTHORED_CLOSE_REASONS,
    AttributionReport,
    BenchDisposition,
    BenchFoldResult,
    CloseOutcome,
    CloseReason,
    ClosingAuthority,
    CostComponent,
    ExitRecord,
    ExitRecordStream,
    ExitResultLabel,
    TradeAttribution,
    attribute_whole_trade,
    check_move_to_breakeven_ratchet,
    check_recording_precedes_interpretation,
    classify_bench_disposition,
    fold_bench,
    mint_exit_record,
    partition_by_close_reason,
    realized_r_of,
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
from qmf.risk.paper import (
    ActiveControl,
    BindingTransitionRecord,
    BindingTransitionStream,
    BookMode,
    ClearingCause,
    ExecutionResolution,
    ExecutionTarget,
    ModeFoldResult,
    PaperEpochLog,
    PaperEpochRecord,
    PaperTargetLog,
    PaperTargetRecord,
    ReturnMechanism,
    ReturnToLiveOutcome,
    RoutingOutcome,
    SeatState,
    TreasuryBoundaryKind,
    TriggerDisposition,
    TriggerKind,
    authorize_return_to_live,
    mint_return_to_live_transition,
    reject_paper_pnl_to_treasury,
    reset_paper_epoch,
    resolve_execution_target,
    validate_book_mode,
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
    "ACTION_CLOSE_REASON_MAPPING",
    "ADAPTER_SELF_FLATTEN_KINDS",
    "ADMISSION_LAYERS",
    "ADOPT_BOT_ADVISORY_STOP_MODE",
    "ADOPT_BOT_ADVISORY_STOP_MODE_ID",
    "BENCH_THRESHOLD_VARIABLE",
    "BMS_CONTRACT_FORMAT_VERSION",
    "BMS_SECTIONS",
    "BOOK_CONTRACT_FORMAT_VERSION",
    "BOOK_LIMIT_UNIT_KINDS",
    "BOOK_SECTIONS",
    "BREAKEVEN",
    "CLOSE_REASON_EVIDENCE_MAPPING",
    "COMPOSING_KIND_PAIRS",
    "CT23_ACTIVE_FORMAT_VERSION",
    "CT23_ADVISORY_STOP_FORMAT_VERSION",
    "CT23_KNOWN_FORMAT_VERSIONS",
    "CT29_CONTRACT_FORMAT_VERSION",
    "CT30_CONTRACT_FORMAT_VERSION",
    "CT30_SCOPE_RESOLUTION_TABLE_VERSION",
    "CT31_CONTRACT_FORMAT_VERSION",
    "DAILY_DEAD_ZONE_WIDTH_VARIABLE",
    "EXIT_LOGIC_MODE_REGISTRY",
    "FLATTEN_AUTHORITIES",
    "FORBIDDEN_ADMISSION_GATES",
    "FORM_0006",
    "FULL_ORIGINAL_LOSS",
    "LADDER_FORMULAS",
    "LEASH_B_SPLIT_UNIT_KINDS",
    "LOSS_RUNWAY_PRODUCER",
    "MONEY_BOUNDARIES_LEAVE_POSITIONS",
    "MONEY_RULES_UNIT_KINDS",
    "NEVER_AUTO_KINDS",
    "NEWS_BLACKOUT_AFTER_VARIABLE",
    "NEWS_BLACKOUT_BEFORE_VARIABLE",
    "PAPER_ACCOUNT_ROLES",
    "PROTECTION_WEIGHT",
    "PROTECTION_WINDOW_VARIABLE_NAMES",
    "QUALIFYING_LOSS_THRESHOLD_VARIABLE",
    "RATIFIED_WINDOW_KINDS",
    "RISK_REDUCING_ACTS",
    "SEAT_LOSS_RUN_ALLOWANCE_VARIABLE",
    "SEAT_R_CEILING_CONSTRAINT",
    "SESSION_HANDOVER_BUFFER_ANCHOR_VARIABLE",
    "SESSION_HANDOVER_BUFFER_WIDTH_VARIABLE",
    "STATE_CARRY_COUNTERS",
    "V1_NUMERAIRE",
    "VENUE_AUTHORED_CLOSE_REASONS",
    "WINDOW_EFFECT",
    "WINDOW_FORCED_FLAT_ARBITRATION_RANK",
    "WINDOW_FORCED_FLAT_VARIABLE",
    "WINDOW_TRIGGER_DISPOSITION",
    "ActiveControl",
    "AdmissionBar",
    "AdmissionImpact",
    "AdmissionLayer",
    "AdmissionPage",
    "AdmissionRequirement",
    "AdmittedBinding",
    "AdmittedEntry",
    "AnchorSide",
    "ArbitrationDisposition",
    "ArbitrationOutcome",
    "AttributionReport",
    "AuthorityGrade",
    "AuthorityKind",
    "Band",
    "BenchDisposition",
    "BenchFoldResult",
    "BinOp",
    "BindingLineageEdgeKind",
    "BindingState",
    "BindingTransitionRecord",
    "BindingTransitionStream",
    "BmsDefinition",
    "BmsInstanceId",
    "BookBindingLog",
    "BookBindingRecord",
    "BookBindingRequirements",
    "BookDefinition",
    "BookInstance",
    "BookInstanceId",
    "BookMode",
    "CallableProducer",
    "CapabilityCheckResult",
    "CitedEvidence",
    "ClearingCause",
    "CloseOutcome",
    "CloseReason",
    "ClosingAuthority",
    "CommandStreamKey",
    "Comparison",
    "ComparisonOp",
    "ComparisonRule",
    "ConstraintSpec",
    "ContinuesPerformanceEdge",
    "ControlActionKind",
    "ControlActionRecord",
    "ControlActionStream",
    "ControlRankRow",
    "ControlRankTable",
    "ControlWindowRecord",
    "ControlWindowRevisionLog",
    "CostComponent",
    "CurrencyExposureRecord",
    "CurrentPointer",
    "Direction",
    "EffectiveWindow",
    "EnforcementScope",
    "EntryIntent",
    "EvidenceRequirements",
    "EvidenceSlot",
    "ExecutionResolution",
    "ExecutionTarget",
    "ExitIntent",
    "ExitKind",
    "ExitLogicMode",
    "ExitLogicModule",
    "ExitLogicRef",
    "ExitRecord",
    "ExitRecordStream",
    "ExitResultLabel",
    "FailClosedCause",
    "FeedQuadruple",
    "FormulaOp",
    "FormulaSpec",
    "IntentFamily",
    "KillLine",
    "KillSwitch",
    "Layer1Result",
    "Layer2Result",
    "ModeFoldResult",
    "MoneyBoundaryKind",
    "NotYetRuled",
    "OperatorSignature",
    "PairingRecord",
    "PaperEpochLog",
    "PaperEpochRecord",
    "PaperTargetLog",
    "PaperTargetRecord",
    "PendingControlAction",
    "PendingSlot",
    "PositionModel",
    "ProducerContract",
    "ProposedWindowAct",
    "RFaces",
    "ReasonCode",
    "ReconciliationVerdict",
    "Ref",
    "RequirementVerdict",
    "ResolvedInstrumentScope",
    "ReturnMechanism",
    "ReturnToLiveOutcome",
    "RiskEvaluationRequest",
    "RiskMonotonicViolation",
    "RiskReducingAct",
    "RoutingOutcome",
    "RuledThreshold",
    "SatisfactionPredicate",
    "ScopeResolution",
    "ScopeResolutionDisposition",
    "SeatState",
    "SignedLedgerEdge",
    "SourceLayer",
    "StandingExemptionRecord",
    "StandingIntentFold",
    "StandingIntentStatus",
    "StateCarry",
    "StateCarryChoice",
    "StateCarryCounter",
    "StopMoveDirection",
    "SubjectScope",
    "SuppressedControlAction",
    "TemplateSection",
    "TemplateVariable",
    "TemplateVersionGraph",
    "Threshold",
    "TieDisposition",
    "TightenProtectiveStop",
    "TradeAttribution",
    "TreasuryBoundaryKind",
    "TriggerDisposition",
    "TriggerKind",
    "UiEditability",
    "VariableDiff",
    "VariableEvidence",
    "VenueBindingProfile",
    "VersionEdgeKind",
    "VetoDecisionRecord",
    "WindowBounds",
    "WindowEffect",
    "WindowEvaluation",
    "WindowForcedFlatPolicy",
    "WindowKind",
    "WorkedExample",
    "__version__",
    "admit",
    "admit_entry_intent",
    "admit_entry_r_faces",
    "append_window_revision",
    "arbitrate_same_tick",
    "assemble_admission_page",
    "attribute_whole_trade",
    "authorize_return_to_live",
    "average_r_multiple",
    "bar_is_blank",
    "bind_time_capability_check",
    "check_b_split",
    "check_constraint",
    "check_control_rank_uniqueness",
    "check_exit_logic_mode_available",
    "check_exit_preservation",
    "check_flatten_authority",
    "check_formula",
    "check_live_binding_admissible",
    "check_move_to_breakeven_ratchet",
    "check_no_paper_role_gates_live",
    "check_no_reopen",
    "check_no_scale_in",
    "check_no_size_increase",
    "check_rank_table_non_contradiction",
    "check_recording_precedes_interpretation",
    "check_seat_r_ceiling",
    "check_stop_not_widened",
    "check_target_within_envelope",
    "check_window_blocks_act",
    "check_worked_examples",
    "classify_bench_disposition",
    "close_reason_for",
    "default_satisfaction_predicate",
    "derive_full_loss_price_at_door",
    "derive_original_risk_distance",
    "derive_unit_kind",
    "diff_variable_maps",
    "evaluate_bar",
    "evaluate_entry_under_windows",
    "evaluate_exit_intent",
    "evaluate_requirement",
    "evaluate_satisfaction",
    "fail_closed_on_uncertainty",
    "fold_bench",
    "fold_effective_window",
    "fold_standing_intents",
    "instrument_in_scope",
    "is_paper_role",
    "journal_before_dispatch",
    "mint_control_action",
    "mint_control_window",
    "mint_exit_record",
    "mint_kill_line_breach",
    "mint_kill_switch_action",
    "mint_return_to_live_transition",
    "mint_veto_decision",
    "money_to_r",
    "parse_inbound_intent",
    "partition_by_close_reason",
    "r_to_money",
    "realized_r_of",
    "recompute_worked_example",
    "reconcile_loss_floor",
    "reevaluate_standing_intent",
    "refuse_no_full_loss_price",
    "reject_bar_aggregate",
    "reject_blanket_command_pipe_block",
    "reject_click_exemption",
    "reject_close_partial",
    "reject_forbidden_admission_gate",
    "reject_inbound_requested_r",
    "reject_live_skip",
    "reject_money_boundary_flatten",
    "reject_paper_pnl_to_treasury",
    "reject_risk_monotonic_violation",
    "reject_symbol_currency_parse",
    "reset_paper_epoch",
    "resolve_execution_target",
    "resolve_instrument_scope",
    "resolve_subject_scope",
    "run_layer1_linters",
    "run_layer2_shakedown",
    "sign_admission",
    "sizing_producer",
    "validate_accounting_currency",
    "validate_book_limit",
    "validate_book_mode",
    "validate_money_rules",
    "value_unit_kind",
    "window_in_force_at",
]

# Roster SemVer, in lockstep across the seven roster packages (0.x until the
# V1 blueprint ships). Display-only provenance — never part of fp1 identity.
__version__ = "0.1.0"
