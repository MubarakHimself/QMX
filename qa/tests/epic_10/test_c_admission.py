"""Epic 10 independent audit — Cluster C (Story 10.3).

Three ordered admission layers ending in the operator's signature, the admission
bar grammar, no composite score, blank-blocks-live-money, no-paper-role-gates-live,
the cited-producer worked-example recompute, unit-kind coverage (R-001), and
control-rank uniqueness. Authored from Story 10.3 ACs, CT-22, CT-27, CT-30.

Planned IDs: C1-C10.
"""

from __future__ import annotations

from collections.abc import Mapping

from qmf.core import (
    AccountRole,
    Duration,
    ExactRational,
    Fingerprint,
    Instant,
    Money,
    Ok,
    RefusalCategory,
    Result,
    RoundingMode,
    UnitKind,
    World,
    is_ok,
    is_refusal,
)
from qmf.risk.admission import (
    ADMISSION_LAYERS,
    FORBIDDEN_ADMISSION_GATES,
    LOSS_RUNWAY_PRODUCER,
    AdmissionLayer,
    AdmittedBinding,
    CallableProducer,
    admit,
    check_worked_examples,
    recompute_worked_example,
    reject_forbidden_admission_gate,
    run_layer1_linters,
    run_layer2_shakedown,
    sizing_producer,
)
from qmf.risk.admission_bar import (
    AdmissionBar,
    AdmissionRequirement,
    Comparison,
    ComparisonRule,
    EvidenceRequirements,
    PendingSlot,
    RequirementVerdict,
    RuledThreshold,
    TieDisposition,
    check_live_binding_admissible,
    check_no_paper_role_gates_live,
    evaluate_requirement,
    reject_bar_aggregate,
)
from qmf.risk.control_rank import ControlActionKind, ControlRankRow, ControlRankTable
from qmf.risk.dimensional import LADDER_FORMULAS, WorkedExample
from qmf.risk.grammar import (
    AdmissionImpact,
    TemplateSection,
    TemplateVariable,
    UiEditability,
    VariableValue,
)
from qmf.risk.templates import (
    BMS_CONTRACT_FORMAT_VERSION,
    BOOK_CONTRACT_FORMAT_VERSION,
    BmsDefinition,
    BookDefinition,
)

_INSTANT = Instant(value_ns=1_700_000_000_000_000_000)
_LOSS_RUNWAY_ID = "FORM-loss-runway"
_PRA_ID = "FORM-position-risk-amount"


def _var_money(name: str, minor: int) -> TemplateVariable:
    result = TemplateVariable.try_create(
        name, UnitKind.MONEY, Money(value=minor, currency="USD", scale=2),
        UiEditability.UI_EDITABLE, AdmissionImpact.RESIGN,
    )
    assert is_ok(result)
    return result.value


def _section(name: str, *variables: TemplateVariable) -> TemplateSection:
    result = TemplateSection.try_create(name, {v.name: v for v in variables})
    assert is_ok(result)
    return result.value


def _book() -> BookDefinition:
    result = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD",
        {"money_rules": _section("money_rules", _var_money("loss_floor", 800_000))},
    )
    assert is_ok(result)
    return result.value


def _bms() -> BmsDefinition:
    result = BmsDefinition.try_create(
        BMS_CONTRACT_FORMAT_VERSION, {"charter": _section("charter", _var_money("reserve", 1_000))}
    )
    assert is_ok(result)
    return result.value


def _bms_fp() -> Fingerprint:
    result = _bms().fingerprint()
    assert is_ok(result)
    return result.value


def _evidence(role: AccountRole = AccountRole.LIVE) -> EvidenceRequirements:
    result = EvidenceRequirements.try_create(World.LIVE, role, Duration(value_ns=1_000), {})
    assert is_ok(result)
    return result.value


def _bar(*, role: AccountRole = AccountRole.LIVE, blank: bool = False) -> AdmissionBar:
    if blank:
        slot = PendingSlot.try_create("GAP-0049")
        assert is_ok(slot)
        threshold: object = _blank_threshold()
    else:
        ruled = RuledThreshold.try_create(
            ExactRational(numerator=3, denominator=2, unit_kind=UnitKind.DIMENSIONLESS_RATIO)
        )
        assert is_ok(ruled)
        threshold = ruled.value
    req = AdmissionRequirement.try_create(
        "sharpe", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, threshold, _evidence(role), 0
    )
    assert is_ok(req)
    bar = AdmissionBar.try_create([req.value])
    assert is_ok(bar)
    return bar.value


def _blank_threshold():
    from qmf.risk.grammar import NotYetRuled

    result = NotYetRuled.try_create("GAP-0048")
    assert is_ok(result)
    return result.value


def _rank_table() -> ControlRankTable:
    rows = [
        ControlRankRow(control_action_kind=ControlActionKind.FLATTEN, rank=0),
        ControlRankRow(control_action_kind=ControlActionKind.DRAIN, rank=1),
        ControlRankRow(control_action_kind=ControlActionKind.SUSPEND_NEW, rank=2),
        ControlRankRow(control_action_kind=ControlActionKind.RESUME, rank=3),
    ]
    result = ControlRankTable.try_create(rows)
    assert is_ok(result)
    return result.value


def _worked_examples() -> dict[str, WorkedExample]:
    out: dict[str, WorkedExample] = {}
    for formula in LADDER_FORMULAS:
        example = formula.worked_example
        if example is not None and formula.formula_id in {_LOSS_RUNWAY_ID, _PRA_ID}:
            out[formula.formula_id] = example
    return out


def _producers() -> dict[str, CallableProducer]:
    return {_LOSS_RUNWAY_ID: LOSS_RUNWAY_PRODUCER, _PRA_ID: sizing_producer(2)}


def _admit(**overrides: object) -> Result[AdmittedBinding]:
    kwargs: dict[str, object] = {
        "binding_identity": "binding-1",
        "shakedown_role": AccountRole.DEMO,
        "live_path_rung_baseline_present": True,
        "sensor_baselines_present": True,
        "bms_fingerprint": _bms_fp(),
        "plain_words_summary": "Admit Book v1 to a demo binding.",
        "signer_identity": "operator",
        "signed_at": _INSTANT,
        "gates_live_binding": False,
    }
    kwargs.update(overrides)
    return admit(_book(), _bar(), _rank_table(), _worked_examples(), _producers(), **kwargs)  # type: ignore[arg-type]


# --- C1: strictly three ordered layers ending in a signature -----------------


def test_C1_admission_is_three_ordered_layers_ending_in_a_signature() -> None:
    assert ADMISSION_LAYERS == (
        AdmissionLayer.LAYER_1_LINTERS,
        AdmissionLayer.LAYER_2_SHAKEDOWN,
        AdmissionLayer.LAYER_3_SIGNATURE,
    )
    result = _admit()
    assert is_ok(result)
    binding = result.value
    assert isinstance(binding, AdmittedBinding)
    # Layer 3 is a signature on a page carrying binding identity and the BMS fingerprint.
    assert binding.page.binding_identity == "binding-1"
    assert binding.signature.signer_identity == "operator"
    # The ordering gates upward: a Layer-1 failure short-circuits before Layer 2/3.
    assert is_refusal(admit(
        "not-a-book", _bar(), _rank_table(), _worked_examples(), _producers(),
        binding_identity="b", shakedown_role=AccountRole.DEMO,
        live_path_rung_baseline_present=True, sensor_baselines_present=True,
        bms_fingerprint=_bms_fp(), plain_words_summary="s", signer_identity="op", signed_at=_INSTANT,
    ))


# --- C2: no trial period / probation window / paper-performance gate ----------


def test_C2_no_trial_probation_or_paper_performance_gate() -> None:
    assert {"trial-period", "probation-window", "paper-performance-gate"} == FORBIDDEN_ADMISSION_GATES
    for gate in (*FORBIDDEN_ADMISSION_GATES, "some-other-loop"):
        refusal = reject_forbidden_admission_gate(gate)
        assert refusal.category is RefusalCategory.POLICY_REJECTION
    # There is no fourth admission layer beyond the three.
    assert len(ADMISSION_LAYERS) == 3


# --- C3: the admission-bar requirement grammar -------------------------------


def test_C3_admission_requirement_carries_the_four_declared_parts() -> None:
    # comparison is one of exactly three members
    assert {c.value for c in Comparison} == {"at-least", "at-most", "within-band"}
    ruled = RuledThreshold.try_create(
        ExactRational(numerator=3, denominator=2, unit_kind=UnitKind.DIMENSIONLESS_RATIO)
    )
    assert is_ok(ruled)
    req = AdmissionRequirement.try_create(
        "sharpe", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, ruled.value, _evidence(), 0
    )
    assert is_ok(req)
    assert req.value.measure_identity == "sharpe"
    assert req.value.unit is UnitKind.DIMENSIONLESS_RATIO
    assert req.value.comparison is Comparison.AT_LEAST
    assert req.value.is_blank is False
    # The threshold key is ALWAYS present: a not-yet-ruled blank is a legal threshold.
    blank_req = AdmissionRequirement.try_create(
        "sharpe", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, _blank_threshold(), _evidence(), 0
    )
    assert is_ok(blank_req)
    assert blank_req.value.is_blank is True
    # A missing threshold (None) is refused — the key is mandatory.
    assert is_refusal(AdmissionRequirement.try_create(
        "sharpe", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, None, _evidence(), 0
    ))


# --- C4: no composite score / rating / tier band / weighted aggregate --------


def test_C4_no_composite_may_express_a_bar() -> None:
    for bad in ("weighted-aggregate", "composite-score", "tier-band", "rating"):
        result = AdmissionRequirement.try_create(
            "m", UnitKind.DIMENSIONLESS_RATIO, bad,
            RuledThreshold(bound=ExactRational(numerator=1, denominator=1, unit_kind=UnitKind.DIMENSIONLESS_RATIO)),
            _evidence(), 0,
        )
        assert is_refusal(result)
    for construct in ("composite-score", "weighted-aggregate", "tier-band", "rating"):
        assert reject_bar_aggregate(construct).category is RefusalCategory.POLICY_REJECTION


# --- C5: blank blocks live money, binds non-live freely ----------------------


def test_C5_blank_bar_blocks_live_binds_non_live_freely() -> None:
    blank_bar = _bar(blank=True)
    live = check_live_binding_admissible(blank_bar, AccountRole.LIVE)
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION
    for role in (AccountRole.DEMO, AccountRole.PAPER_VALIDATION, AccountRole.PAPER_BENCHED):
        assert is_ok(check_live_binding_admissible(blank_bar, role))
    # A fully-ruled bar admits a live binding.
    assert is_ok(check_live_binding_admissible(_bar(), AccountRole.LIVE))


# --- C6: a paper-role bar gating a live binding -> policy rejection at Layer 1 -


def test_C6_paper_role_bar_gating_live_is_refused_at_layer1() -> None:
    paper_bar = _bar(role=AccountRole.PAPER_VALIDATION)
    direct = check_no_paper_role_gates_live(paper_bar, AccountRole.LIVE)
    assert is_refusal(direct)
    assert direct.category is RefusalCategory.POLICY_REJECTION
    # And Layer 1 itself refuses when gating a live binding with a paper-role bar.
    layer1 = run_layer1_linters(
        _book(), paper_bar, _rank_table(), _worked_examples(), _producers(), gates_live_binding=True
    )
    assert is_refusal(layer1)
    assert layer1.category is RefusalCategory.POLICY_REJECTION


# --- C7: worked examples recomputed via the cited producer, not local math ----


def test_C7_worked_examples_recompute_via_cited_producer_only() -> None:
    # The reference producers reproduce the declared outputs.
    assert is_ok(check_worked_examples(_worked_examples(), _producers()))
    # A producer returning a WRONG value makes the check fail -> the linter uses the
    # producer's output, never a second local implementation of the formula.
    def _wrong(_inputs: Mapping[str, VariableValue]) -> Result[VariableValue]:
        value: VariableValue = Money(value=1, currency="USD", scale=2)
        return Ok(value)

    example = _worked_examples()[_LOSS_RUNWAY_ID]
    mismatch = recompute_worked_example(example, CallableProducer(recompute_fn=_wrong))
    assert is_refusal(mismatch)
    assert mismatch.category is RefusalCategory.INVALID_INPUT
    # A worked example with NO injected producer cannot be recomputed (never local math).
    missing = check_worked_examples(_worked_examples(), {_LOSS_RUNWAY_ID: LOSS_RUNWAY_PRODUCER})
    assert is_refusal(missing)
    assert missing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


# --- C8 [R-001]: unit-kind coverage enforced at Layer 1 ----------------------


def test_C8_layer1_enforces_unit_kind_coverage() -> None:
    # A variable whose value unit-kind disagrees with its declared unit-kind (built via
    # the raw constructor to bypass try_create) is caught by the Layer-1 coverage linter.
    bad = TemplateVariable(
        name="bad", unit_kind=UnitKind.COUNT, value=Money(value=100, currency="USD", scale=2),
        ui_editable=UiEditability.UI_EDITABLE, admission_impact=AdmissionImpact.NONE,
    )
    section = TemplateSection.try_create("charter", {"bad": bad})
    assert is_ok(section)
    book = BookDefinition.try_create(BOOK_CONTRACT_FORMAT_VERSION, "USD", {"charter": section.value})
    assert is_ok(book)
    result = run_layer1_linters(book.value, _bar(), _rank_table(), _worked_examples(), _producers())
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


# --- C9 [CT-30]: two control-action kinds sharing a rank -> invalid input -----


def test_C9_two_kinds_sharing_a_rank_is_invalid_input() -> None:
    dup = [
        ControlRankRow(control_action_kind=ControlActionKind.FLATTEN, rank=1),
        ControlRankRow(control_action_kind=ControlActionKind.DRAIN, rank=1),
    ]
    result = ControlRankTable.try_create(dup)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    # And Layer 1 propagates the duplicate-rank refusal.
    layer1 = run_layer1_linters(_book(), _bar(), dup, _worked_examples(), _producers())
    assert is_refusal(layer1)


# --- C10: a float measure needs a declared comparison rule -------------------


def test_C10_float_measure_needs_a_declared_comparison_rule() -> None:
    ruled = RuledThreshold.try_create(
        ExactRational(numerator=3, denominator=2, unit_kind=UnitKind.DIMENSIONLESS_RATIO)
    )
    assert is_ok(ruled)
    no_rule = AdmissionRequirement.try_create(
        "sharpe", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, ruled.value, _evidence(), 0
    )
    assert is_ok(no_rule)
    # A float measure without a declared comparison rule is an invalid-input refusal.
    undeclared = evaluate_requirement(no_rule.value, 1.6)
    assert is_refusal(undeclared)
    assert undeclared.category is RefusalCategory.INVALID_INPUT
    # With a declared rule (scale, rounding, tie) the crossing is allowed.
    rule = ComparisonRule.try_create(2, RoundingMode.HALF_UP, TieDisposition.PASS_ON_TIE)
    assert is_ok(rule)
    with_rule = AdmissionRequirement.try_create(
        "sharpe", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, ruled.value, _evidence(), 0, rule.value
    )
    assert is_ok(with_rule)
    verdict = evaluate_requirement(with_rule.value, 1.6)
    assert is_ok(verdict)
    assert verdict.value is RequirementVerdict.PASS
