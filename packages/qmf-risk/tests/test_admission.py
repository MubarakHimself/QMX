"""Story 10.3 AC1/AC5 — three-layer admission and the worked-example recompute.

Verifies the strictly-three ordered layers ending in the operator's signature with no
trial/probation/paper-performance gate, the Layer-1 machine linters (unit-kind
coverage, worked-example recompute by invoking the cited producer contracts, and
control-rank uniqueness), the Layer-2 demo/paper shakedown with its two prerequisites,
the Layer-3 assembled page + signature, and the admit() ordered composition
(CT-22, CT-27; DEC-0146, DEC-0116).
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
    Retryability,
    TypedRefusal,
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
    AdmissionPage,
    AdmittedBinding,
    CallableProducer,
    Layer1Result,
    Layer2Result,
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
    AdmissionBar,
    AdmissionRequirement,
    Comparison,
    EvidenceRequirements,
    RuledThreshold,
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

_LOSS_RUNWAY_ID = "FORM-loss-runway"
_PRA_ID = "FORM-position-risk-amount"
_INSTANT = Instant(value_ns=1_700_000_000_000_000_000)


# --- builders ----------------------------------------------------------------


def _var_money(name: str, minor: int) -> TemplateVariable:
    result = TemplateVariable.try_create(
        name,
        UnitKind.MONEY,
        Money(value=minor, currency="USD", scale=2),
        UiEditability.UI_EDITABLE,
        AdmissionImpact.RESIGN,
    )
    assert is_ok(result)
    return result.value


def _section(name: str, *variables: TemplateVariable) -> TemplateSection:
    result = TemplateSection.try_create(name, {v.name: v for v in variables})
    assert is_ok(result)
    return result.value


def _book() -> BookDefinition:
    result = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION,
        "USD",
        {"money_rules": _section("money_rules", _var_money("loss_floor", 800_000))},
    )
    assert is_ok(result)
    return result.value


def _bms() -> BmsDefinition:
    result = BmsDefinition.try_create(
        BMS_CONTRACT_FORMAT_VERSION,
        {"charter": _section("charter", _var_money("reserve", 1_000))},
    )
    assert is_ok(result)
    return result.value


def _evidence(role: AccountRole = AccountRole.LIVE) -> EvidenceRequirements:
    result = EvidenceRequirements.try_create(World.LIVE, role, Duration(value_ns=1_000), {})
    assert is_ok(result)
    return result.value


def _bar(role: AccountRole = AccountRole.LIVE) -> AdmissionBar:
    threshold = RuledThreshold.try_create(
        ExactRational(numerator=3, denominator=2, unit_kind=UnitKind.DIMENSIONLESS_RATIO)
    )
    assert is_ok(threshold)
    req = AdmissionRequirement.try_create(
        "sharpe",
        UnitKind.DIMENSIONLESS_RATIO,
        Comparison.AT_LEAST,
        threshold.value,
        _evidence(role),
        0,
    )
    assert is_ok(req)
    bar = AdmissionBar.try_create([req.value])
    assert is_ok(bar)
    return bar.value


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


def _fingerprint(definition: BookDefinition | BmsDefinition) -> Fingerprint:
    result = definition.fingerprint()
    assert is_ok(result)
    return result.value


# --- AC1: exactly three ordered layers, no fourth gate -----------------------


def test_exactly_three_ordered_layers() -> None:
    assert ADMISSION_LAYERS == (
        AdmissionLayer.LAYER_1_LINTERS,
        AdmissionLayer.LAYER_2_SHAKEDOWN,
        AdmissionLayer.LAYER_3_SIGNATURE,
    )
    assert len(ADMISSION_LAYERS) == 3


def test_forbidden_gates_are_policy_rejections() -> None:
    assert {
        "trial-period",
        "probation-window",
        "paper-performance-gate",
    } == FORBIDDEN_ADMISSION_GATES
    for gate in (*FORBIDDEN_ADMISSION_GATES, "some-other-loop", None):
        refusal = reject_forbidden_admission_gate(gate)
        assert refusal.category is RefusalCategory.POLICY_REJECTION


# --- AC5: worked-example recompute via the cited producer seam ----------------


def test_reference_producer_recomputes_loss_runway_worked_example() -> None:
    example = _worked_examples()[_LOSS_RUNWAY_ID]
    result = recompute_worked_example(example, LOSS_RUNWAY_PRODUCER)
    assert is_ok(result)
    assert result.value.fp1_identity() == example.expected_output.fp1_identity()


def test_reference_sizing_producer_recomputes_position_risk_amount() -> None:
    example = _worked_examples()[_PRA_ID]
    result = recompute_worked_example(example, sizing_producer(2))
    assert is_ok(result)
    assert result.value.fp1_identity() == example.expected_output.fp1_identity()


def test_recompute_uses_producer_output_not_local_arithmetic() -> None:
    # A producer that returns the WRONG value makes the check fail — proving the linter
    # uses the producer's output, never a second local implementation of the formula.
    def _wrong(_inputs: Mapping[str, VariableValue]) -> Result[VariableValue]:
        value: VariableValue = Money(value=1, currency="USD", scale=2)
        return Ok(value)

    example = _worked_examples()[_LOSS_RUNWAY_ID]
    result = recompute_worked_example(example, CallableProducer(recompute_fn=_wrong))
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_recompute_propagates_producer_refusal() -> None:
    def _refuser(_inputs: Mapping[str, VariableValue]) -> Result[VariableValue]:
        return TypedRefusal(
            category=RefusalCategory.UNAVAILABLE_DEPENDENCY, retryability=Retryability.NO
        )

    example = _worked_examples()[_LOSS_RUNWAY_ID]
    result = recompute_worked_example(example, CallableProducer(recompute_fn=_refuser))
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_recompute_refuses_non_worked_example_and_non_producer() -> None:
    example = _worked_examples()[_LOSS_RUNWAY_ID]
    assert is_refusal(recompute_worked_example("not-a-worked-example", LOSS_RUNWAY_PRODUCER))
    assert is_refusal(recompute_worked_example(example, 42))


def test_check_worked_examples_passes_with_cited_producers() -> None:
    assert is_ok(check_worked_examples(_worked_examples(), _producers()))


def test_check_worked_examples_missing_producer_is_unavailable_dependency() -> None:
    # AC5: the linter recomputes by invoking the cited producer, never by local
    # arithmetic — a worked example without an injected producer cannot be recomputed.
    result = check_worked_examples(_worked_examples(), {_LOSS_RUNWAY_ID: LOSS_RUNWAY_PRODUCER})
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_check_worked_examples_mismatch_is_invalid_input() -> None:
    def _wrong(_inputs: Mapping[str, VariableValue]) -> Result[VariableValue]:
        value: VariableValue = Money(value=1, currency="USD", scale=2)
        return Ok(value)

    examples = {_LOSS_RUNWAY_ID: _worked_examples()[_LOSS_RUNWAY_ID]}
    producers = {_LOSS_RUNWAY_ID: CallableProducer(recompute_fn=_wrong)}
    result = check_worked_examples(examples, producers)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_check_worked_examples_refuses_bad_mappings() -> None:
    assert is_refusal(check_worked_examples([1, 2], _producers()))
    assert is_refusal(check_worked_examples(_worked_examples(), [1, 2]))
    assert is_refusal(
        check_worked_examples({"": _worked_examples()[_LOSS_RUNWAY_ID]}, _producers())
    )
    assert is_refusal(check_worked_examples({_LOSS_RUNWAY_ID: "x"}, _producers()))
    assert is_refusal(check_worked_examples(_worked_examples(), {"": LOSS_RUNWAY_PRODUCER}))
    assert is_refusal(check_worked_examples(_worked_examples(), {_LOSS_RUNWAY_ID: 42}))


# --- AC5: Layer 1 linters (coverage, worked examples, control ranks) ---------


def test_layer1_passes_for_a_clean_book() -> None:
    result = run_layer1_linters(_book(), _bar(), _rank_table(), _worked_examples(), _producers())
    assert is_ok(result)
    assert result.value.is_bms is False
    assert result.value.definition_fingerprint.value == _fingerprint(_book()).value


def test_layer1_reports_is_bms_for_a_bms_definition() -> None:
    result = run_layer1_linters(_bms(), _bar(), _rank_table(), _worked_examples(), _producers())
    assert is_ok(result)
    assert result.value.is_bms is True


def test_layer1_refuses_non_definition_and_non_bar() -> None:
    assert is_refusal(
        run_layer1_linters("not-a-book", _bar(), _rank_table(), _worked_examples(), _producers())
    )
    assert is_refusal(
        run_layer1_linters(_book(), "not-a-bar", _rank_table(), _worked_examples(), _producers())
    )


def test_layer1_unit_kind_coverage_catches_a_mismatched_variable() -> None:
    # A variable built through the raw constructor (bypassing try_create) whose value
    # unit-kind disagrees with its declared unit-kind is caught by the Layer-1 coverage
    # linter (AC5) — a count where a money value stands.
    bad = TemplateVariable(
        name="bad",
        unit_kind=UnitKind.COUNT,
        value=Money(value=100, currency="USD", scale=2),
        ui_editable=UiEditability.UI_EDITABLE,
        admission_impact=AdmissionImpact.NONE,
    )
    section = TemplateSection.try_create("charter", {"bad": bad})
    assert is_ok(section)
    book = BookDefinition.try_create(
        BOOK_CONTRACT_FORMAT_VERSION, "USD", {"charter": section.value}
    )
    assert is_ok(book)
    result = run_layer1_linters(book.value, _bar(), _rank_table(), _worked_examples(), _producers())
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_layer1_propagates_control_rank_duplicate() -> None:
    dup_rows = [
        ControlRankRow(control_action_kind=ControlActionKind.FLATTEN, rank=1),
        ControlRankRow(control_action_kind=ControlActionKind.DRAIN, rank=1),
    ]
    result = run_layer1_linters(_book(), _bar(), dup_rows, _worked_examples(), _producers())
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_layer1_propagates_worked_example_failure() -> None:
    result = run_layer1_linters(
        _book(), _bar(), _rank_table(), _worked_examples(), {_LOSS_RUNWAY_ID: LOSS_RUNWAY_PRODUCER}
    )
    assert is_refusal(result)


# --- AC4: no paper role gates a live binding at Layer 1 ----------------------


def test_layer1_gating_live_refuses_paper_role_bar() -> None:
    paper_bar = _bar(role=AccountRole.PAPER_VALIDATION)
    result = run_layer1_linters(
        _book(), paper_bar, _rank_table(), _worked_examples(), _producers(), gates_live_binding=True
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_layer1_gating_live_passes_live_role_bar() -> None:
    result = run_layer1_linters(
        _book(), _bar(), _rank_table(), _worked_examples(), _producers(), gates_live_binding=True
    )
    assert is_ok(result)


# --- AC1: Layer 2 technical shakedown ----------------------------------------


def test_layer2_passes_on_a_demo_binding_with_prerequisites() -> None:
    result = run_layer2_shakedown("binding-1", AccountRole.DEMO, True, True)
    assert is_ok(result)
    assert result.value.shakedown_role is AccountRole.DEMO


def test_layer2_refuses_a_live_shakedown() -> None:
    result = run_layer2_shakedown("binding-1", AccountRole.LIVE, True, True)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_layer2_refuses_blank_binding_and_bad_role() -> None:
    assert is_refusal(run_layer2_shakedown("  ", AccountRole.DEMO, True, True))
    assert is_refusal(run_layer2_shakedown("binding-1", "not-a-role", True, True))


def test_layer2_missing_prerequisites_are_unavailable_dependency() -> None:
    no_rung = run_layer2_shakedown("binding-1", AccountRole.DEMO, False, True)
    assert is_refusal(no_rung)
    assert no_rung.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    no_sensor = run_layer2_shakedown("binding-1", AccountRole.PAPER_VALIDATION, True, False)
    assert is_refusal(no_sensor)
    assert no_sensor.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_layer2_refuses_non_bool_prerequisites() -> None:
    assert is_refusal(run_layer2_shakedown("binding-1", AccountRole.DEMO, "yes", True))
    assert is_refusal(run_layer2_shakedown("binding-1", AccountRole.DEMO, True, "yes"))


# --- AC1: Layer 3 assembled page + signature ---------------------------------


def _layer1() -> Layer1Result:
    result = run_layer1_linters(_book(), _bar(), _rank_table(), _worked_examples(), _producers())
    assert is_ok(result)
    return result.value


def _layer2(binding: str = "binding-1") -> Layer2Result:
    result = run_layer2_shakedown(binding, AccountRole.DEMO, True, True)
    assert is_ok(result)
    return result.value


def test_assemble_page_carries_both_proofs_and_fingerprints() -> None:
    layer1 = _layer1()
    result = assemble_admission_page(
        layer1,
        _layer2(),
        "binding-1",
        _fingerprint(_bms()),
        layer1.definition_fingerprint,
        "Admit Book v1 to demo binding.",
    )
    assert is_ok(result)
    assert result.value.binding_identity == "binding-1"


def test_assemble_page_refuses_bad_proofs_and_mismatches() -> None:
    layer1 = _layer1()
    bms_fp = _fingerprint(_bms())
    # non-Layer1Result / non-Layer2Result
    assert is_refusal(
        assemble_admission_page(
            "x", _layer2(), "binding-1", bms_fp, layer1.definition_fingerprint, "s"
        )
    )
    assert is_refusal(
        assemble_admission_page(
            layer1, "x", "binding-1", bms_fp, layer1.definition_fingerprint, "s"
        )
    )
    # binding identity mismatch with the shaken-down binding
    assert is_refusal(
        assemble_admission_page(
            layer1, _layer2("binding-1"), "other", bms_fp, layer1.definition_fingerprint, "s"
        )
    )
    # blank binding identity
    assert is_refusal(
        assemble_admission_page(layer1, _layer2(), "  ", bms_fp, layer1.definition_fingerprint, "s")
    )
    # bad bms fingerprint / bad definition fingerprint
    assert is_refusal(
        assemble_admission_page(
            layer1, _layer2(), "binding-1", "not-a-fp", layer1.definition_fingerprint, "s"
        )
    )
    assert is_refusal(
        assemble_admission_page(layer1, _layer2(), "binding-1", bms_fp, "not-a-fp", "s")
    )


def test_assemble_page_refuses_superseded_template_fingerprint() -> None:
    # A definition fingerprint that differs from the one Layer 1 linted is refused, so a
    # signature can never attest a superseded template.
    layer1 = _layer1()
    other_fp = _fingerprint(_bms())  # a different template's fingerprint
    result = assemble_admission_page(
        layer1, _layer2(), "binding-1", _fingerprint(_bms()), other_fp, "summary"
    )
    assert is_refusal(result)


def test_assemble_page_refuses_blank_summary() -> None:
    layer1 = _layer1()
    result = assemble_admission_page(
        layer1, _layer2(), "binding-1", _fingerprint(_bms()), layer1.definition_fingerprint, "   "
    )
    assert is_refusal(result)


def _page() -> AdmissionPage:
    layer1 = _layer1()
    result = assemble_admission_page(
        layer1,
        _layer2(),
        "binding-1",
        _fingerprint(_bms()),
        layer1.definition_fingerprint,
        "Admit Book v1.",
    )
    assert is_ok(result)
    return result.value


def test_sign_admission_admits_with_a_human_signature() -> None:
    result = sign_admission(_page(), "operator", _INSTANT)
    assert is_ok(result)
    assert isinstance(result.value, AdmittedBinding)
    assert result.value.signature.signer_identity == "operator"


def test_sign_admission_refuses_bad_inputs() -> None:
    assert is_refusal(sign_admission("not-a-page", "operator", _INSTANT))
    assert is_refusal(sign_admission(_page(), "   ", _INSTANT))
    assert is_refusal(sign_admission(_page(), "operator", 123))


# --- AC1: admit() composes the three layers in order -------------------------


def _admit(**overrides: object) -> Result[AdmittedBinding]:
    kwargs: dict[str, object] = {
        "binding_identity": "binding-1",
        "shakedown_role": AccountRole.DEMO,
        "live_path_rung_baseline_present": True,
        "sensor_baselines_present": True,
        "bms_fingerprint": _fingerprint(_bms()),
        "plain_words_summary": "Admit Book v1 to a demo binding.",
        "signer_identity": "operator",
        "signed_at": _INSTANT,
        "gates_live_binding": False,
    }
    kwargs.update(overrides)
    return admit(_book(), _bar(), _rank_table(), _worked_examples(), _producers(), **kwargs)  # type: ignore[arg-type]


def test_admit_full_happy_path_ends_in_a_signature() -> None:
    result = _admit()
    assert is_ok(result)
    assert isinstance(result.value, AdmittedBinding)
    assert result.value.page.binding_identity == "binding-1"


def test_admit_short_circuits_on_layer1() -> None:
    result = admit(
        "not-a-book",
        _bar(),
        _rank_table(),
        _worked_examples(),
        _producers(),
        binding_identity="binding-1",
        shakedown_role=AccountRole.DEMO,
        live_path_rung_baseline_present=True,
        sensor_baselines_present=True,
        bms_fingerprint=_fingerprint(_bms()),
        plain_words_summary="s",
        signer_identity="operator",
        signed_at=_INSTANT,
    )
    assert is_refusal(result)


def test_admit_short_circuits_on_layer2() -> None:
    result = _admit(shakedown_role=AccountRole.LIVE)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


def test_admit_short_circuits_on_page_assembly() -> None:
    result = _admit(bms_fingerprint="not-a-fingerprint")
    assert is_refusal(result)


def test_admit_short_circuits_on_signature() -> None:
    result = _admit(signer_identity="   ")
    assert is_refusal(result)


def test_admit_gating_live_refuses_paper_role_bar() -> None:
    result = admit(
        _book(),
        _bar(role=AccountRole.PAPER_VALIDATION),
        _rank_table(),
        _worked_examples(),
        _producers(),
        binding_identity="binding-1",
        shakedown_role=AccountRole.DEMO,
        live_path_rung_baseline_present=True,
        sensor_baselines_present=True,
        bms_fingerprint=_fingerprint(_bms()),
        plain_words_summary="s",
        signer_identity="operator",
        signed_at=_INSTANT,
        gates_live_binding=True,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION


# --- fp1 identity coverage of the layer/page/signature records ---------------


def test_result_records_expose_fp1_identity() -> None:
    admitted = _admit()
    assert is_ok(admitted)
    binding = admitted.value
    assert binding.fp1_identity()["class"] == "admitted-binding"
    assert binding.page.fp1_identity()["class"] == "admission-page"
    assert binding.page.layer1.fp1_identity()["class"] == "admission-layer1-result"
    assert binding.page.layer2.fp1_identity()["class"] == "admission-layer2-result"
    assert binding.signature.fp1_identity()["class"] == "operator-signature"
