"""Story 10.3 AC2/AC3/AC4/AC6 — the admission bar and blank-blocks-live money.

Verifies the requirement grammar (opaque measure_identity, mandatory unit, the
three-member comparison, the ruled|not-yet-ruled threshold union with the key always
present, evidence requirements, the declared float→exact comparison rule), that no
composite score may express a bar, blank-blocks-live money, no-paper-role-gates-live,
and the analytic→exact comparison boundary (CT-22, CT-27; DEC-0146).
"""

from __future__ import annotations

from qmf.core import (
    AccountRole,
    Duration,
    ExactRational,
    Money,
    RefusalCategory,
    RoundingMode,
    UnitKind,
    World,
    is_ok,
    is_refusal,
)
from qmf.risk.admission_bar import (
    AdmissionBar,
    AdmissionRequirement,
    Band,
    Comparison,
    ComparisonRule,
    EvidenceRequirements,
    PendingSlot,
    RequirementVerdict,
    RuledThreshold,
    TieDisposition,
    bar_is_blank,
    check_live_binding_admissible,
    check_no_paper_role_gates_live,
    evaluate_bar,
    evaluate_requirement,
    is_paper_role,
    reject_bar_aggregate,
)
from qmf.risk.grammar import NotYetRuled

# --- builders ----------------------------------------------------------------


def _er(num: int, den: int, kind: UnitKind = UnitKind.DIMENSIONLESS_RATIO) -> ExactRational:
    result = ExactRational.try_create(num, den, kind)
    assert is_ok(result)
    return result.value


def _blank(gap: str = "GAP-0048") -> NotYetRuled:
    result = NotYetRuled.try_create(gap)
    assert is_ok(result)
    return result.value


def _verdict(req: AdmissionRequirement, measure: object) -> RequirementVerdict:
    result = evaluate_requirement(req, measure)
    assert is_ok(result)
    return result.value


def _evidence(
    role: AccountRole = AccountRole.LIVE, world: World = World.LIVE
) -> EvidenceRequirements:
    result = EvidenceRequirements.try_create(world, role, Duration(value_ns=86_400_000_000_000), {})
    assert is_ok(result)
    return result.value


def _requirement(
    measure_identity: str = "sharpe",
    *,
    comparison: Comparison = Comparison.AT_LEAST,
    threshold: object = None,
    unit: UnitKind = UnitKind.DIMENSIONLESS_RATIO,
    evidence: EvidenceRequirements | None = None,
    display_ordinal: int = 0,
    comparison_rule: ComparisonRule | None = None,
) -> AdmissionRequirement:
    if threshold is None:
        ruled = RuledThreshold.try_create(_er(3, 2, unit))
        assert is_ok(ruled)
        threshold = ruled.value
    result = AdmissionRequirement.try_create(
        measure_identity,
        unit,
        comparison,
        threshold,
        evidence if evidence is not None else _evidence(),
        display_ordinal,
        comparison_rule,
    )
    assert is_ok(result)
    return result.value


# --- Comparison / TieDisposition / RequirementVerdict ------------------------


def test_comparison_is_exactly_three_members() -> None:
    assert {c.value for c in Comparison} == {"at-least", "at-most", "within-band"}


def test_tie_and_verdict_members() -> None:
    assert {t.value for t in TieDisposition} == {"pass-on-tie", "fail-on-tie"}
    assert {v.value for v in RequirementVerdict} == {"pass", "fail", "not-yet-ruled"}


# --- Band --------------------------------------------------------------------


def test_band_builds_and_reports_unit_kind() -> None:
    result = Band.try_create(_er(1, 1), _er(2, 1))
    assert is_ok(result)
    assert result.value.unit_kind is UnitKind.DIMENSIONLESS_RATIO


def test_band_refuses_non_exact_bounds() -> None:
    assert is_refusal(Band.try_create(1.0, _er(2, 1)))
    assert is_refusal(Band.try_create(_er(1, 1), 2.0))


def test_band_refuses_mismatched_unit_kinds() -> None:
    result = Band.try_create(_er(1, 1, UnitKind.R_MULTIPLE), _er(2, 1, UnitKind.COUNT))
    assert is_refusal(result)


def test_band_refuses_non_ascending_bounds() -> None:
    assert is_refusal(Band.try_create(_er(2, 1), _er(2, 1)))
    assert is_refusal(Band.try_create(_er(3, 1), _er(2, 1)))


# --- RuledThreshold ----------------------------------------------------------


def test_ruled_threshold_scalar_and_band() -> None:
    scalar = RuledThreshold.try_create(_er(3, 2))
    assert is_ok(scalar)
    assert scalar.value.unit_kind is UnitKind.DIMENSIONLESS_RATIO
    band = Band.try_create(_er(1, 1), _er(2, 1))
    assert is_ok(band)
    assert is_ok(RuledThreshold.try_create(band.value))


def test_ruled_threshold_refuses_float_and_blank() -> None:
    assert is_refusal(RuledThreshold.try_create(1.5))
    assert is_refusal(RuledThreshold.try_create(_blank()))


# --- ComparisonRule ----------------------------------------------------------


def test_comparison_rule_builds() -> None:
    result = ComparisonRule.try_create(2, RoundingMode.HALF_UP, TieDisposition.PASS_ON_TIE)
    assert is_ok(result)
    assert result.value.target_scale == 2


def test_comparison_rule_refuses_bad_scale() -> None:
    assert is_refusal(
        ComparisonRule.try_create(True, RoundingMode.HALF_UP, TieDisposition.PASS_ON_TIE)
    )
    assert is_refusal(
        ComparisonRule.try_create(-1, RoundingMode.HALF_UP, TieDisposition.PASS_ON_TIE)
    )
    assert is_refusal(
        ComparisonRule.try_create(999, RoundingMode.HALF_UP, TieDisposition.PASS_ON_TIE)
    )
    assert is_refusal(
        ComparisonRule.try_create("2", RoundingMode.HALF_UP, TieDisposition.PASS_ON_TIE)
    )


def test_comparison_rule_refuses_bad_mode_and_tie() -> None:
    assert is_refusal(ComparisonRule.try_create(2, "sideways", TieDisposition.PASS_ON_TIE))
    assert is_refusal(ComparisonRule.try_create(2, RoundingMode.HALF_UP, "flip-a-coin"))


# --- EvidenceRequirements ----------------------------------------------------


def test_evidence_requirements_builds_and_flags_format2_fields() -> None:
    result = EvidenceRequirements.try_create(
        World.LIVE,
        AccountRole.LIVE,
        Duration(value_ns=1_000),
        {"CT-32": 1},
        registered_conformant_bot_cite=True,
        canonical_assignment_evidence=True,
        contract_format_version=2,
    )
    assert is_ok(result)
    assert result.value.registered_conformant_bot_cite is True
    assert result.value.canonical_assignment_evidence is True
    assert result.value.required_producer_contract_format_versions["CT-32"] == 1
    identity = result.value.fp1_identity()
    assert identity["registered_conformant_bot_cite"] is True
    assert identity["canonical_assignment_evidence"] is True


def test_format_1_evidence_identity_omits_format2_fields() -> None:
    result = EvidenceRequirements.try_create(
        World.LIVE,
        AccountRole.LIVE,
        Duration(value_ns=1_000),
        {},
        contract_format_version=1,
    )
    assert is_ok(result)
    identity = result.value.fp1_identity()
    assert "registered_conformant_bot_cite" not in identity
    assert "canonical_assignment_evidence" not in identity


def test_format_1_evidence_cannot_carry_format2_flags() -> None:
    dur = Duration(value_ns=1)
    assert is_refusal(
        EvidenceRequirements.try_create(
            World.LIVE,
            AccountRole.LIVE,
            dur,
            {},
            registered_conformant_bot_cite=True,
            contract_format_version=1,
        )
    )
    assert is_refusal(
        EvidenceRequirements.try_create(
            World.LIVE,
            AccountRole.LIVE,
            dur,
            {},
            canonical_assignment_evidence=True,
            contract_format_version=1,
        )
    )


def test_evidence_requirements_names_paper_role() -> None:
    live = _evidence(role=AccountRole.LIVE)
    paper = _evidence(role=AccountRole.PAPER_VALIDATION)
    assert live.names_paper_role is False
    assert paper.names_paper_role is True


def test_evidence_requirements_refusals() -> None:
    dur = Duration(value_ns=1)
    assert is_refusal(EvidenceRequirements.try_create("nowhere", AccountRole.LIVE, dur, {}))
    assert is_refusal(EvidenceRequirements.try_create(World.LIVE, "nobody", dur, {}))
    assert is_refusal(EvidenceRequirements.try_create(World.LIVE, AccountRole.LIVE, 123, {}))
    assert is_refusal(EvidenceRequirements.try_create(World.LIVE, AccountRole.LIVE, dur, [1, 2]))
    assert is_refusal(EvidenceRequirements.try_create(World.LIVE, AccountRole.LIVE, dur, {"": 1}))
    assert is_refusal(
        EvidenceRequirements.try_create(World.LIVE, AccountRole.LIVE, dur, {"CT-32": True})
    )
    assert is_refusal(
        EvidenceRequirements.try_create(
            World.LIVE, AccountRole.LIVE, dur, {}, registered_conformant_bot_cite="yes"
        )
    )
    assert is_refusal(
        EvidenceRequirements.try_create(
            World.LIVE, AccountRole.LIVE, dur, {}, canonical_assignment_evidence="yes"
        )
    )
    assert is_refusal(
        EvidenceRequirements.try_create(
            World.LIVE, AccountRole.LIVE, dur, {}, contract_format_version=99
        )
    )
    assert is_refusal(
        EvidenceRequirements.try_create(
            World.LIVE, AccountRole.LIVE, dur, {}, contract_format_version=True
        )
    )


# --- AdmissionRequirement grammar (AC2) --------------------------------------


def test_requirement_builds_with_ruled_scalar() -> None:
    req = _requirement()
    assert req.measure_identity == "sharpe"
    assert req.unit is UnitKind.DIMENSIONLESS_RATIO
    assert req.comparison is Comparison.AT_LEAST
    assert req.is_blank is False


def test_requirement_accepts_not_yet_ruled_threshold_key_always_present() -> None:
    req = _requirement(threshold=_blank())
    assert req.is_blank is True


def test_requirement_refuses_blank_measure_identity() -> None:
    result = AdmissionRequirement.try_create(
        "  ",
        UnitKind.DIMENSIONLESS_RATIO,
        Comparison.AT_LEAST,
        RuledThreshold(bound=_er(1, 1)),
        _evidence(),
        0,
    )
    assert is_refusal(result)


def test_requirement_refuses_missing_unit() -> None:
    result = AdmissionRequirement.try_create(
        "m", "not-a-unit", Comparison.AT_LEAST, RuledThreshold(bound=_er(1, 1)), _evidence(), 0
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_requirement_refuses_composite_comparison_no_composite_score() -> None:
    # AC2: no composite score, rating, tier band, or weighted aggregate may express a bar —
    # the comparison set is closed to the three pass/fail members.
    for bad in ("weighted-aggregate", "composite-score", "tier-band", "rating"):
        result = AdmissionRequirement.try_create(
            "m", UnitKind.DIMENSIONLESS_RATIO, bad, RuledThreshold(bound=_er(1, 1)), _evidence(), 0
        )
        assert is_refusal(result)


def test_requirement_within_band_needs_band_bound() -> None:
    scalar = RuledThreshold.try_create(_er(1, 1))
    assert is_ok(scalar)
    result = AdmissionRequirement.try_create(
        "m", UnitKind.DIMENSIONLESS_RATIO, Comparison.WITHIN_BAND, scalar.value, _evidence(), 0
    )
    assert is_refusal(result)


def test_requirement_scalar_comparison_rejects_band_bound() -> None:
    band = Band.try_create(_er(1, 1), _er(2, 1))
    assert is_ok(band)
    ruled = RuledThreshold.try_create(band.value)
    assert is_ok(ruled)
    result = AdmissionRequirement.try_create(
        "m", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, ruled.value, _evidence(), 0
    )
    assert is_refusal(result)


def test_requirement_threshold_unit_kind_must_match_declared() -> None:
    ruled = RuledThreshold.try_create(_er(1, 1, UnitKind.R_MULTIPLE))
    assert is_ok(ruled)
    result = AdmissionRequirement.try_create(
        "m", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, ruled.value, _evidence(), 0
    )
    assert is_refusal(result)


def test_requirement_refuses_none_threshold_key_always_present() -> None:
    result = AdmissionRequirement.try_create(
        "m", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, None, _evidence(), 0
    )
    assert is_refusal(result)


def test_requirement_refuses_non_threshold_object() -> None:
    result = AdmissionRequirement.try_create(
        "m", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, "1.5", _evidence(), 0
    )
    assert is_refusal(result)


def test_requirement_refuses_bad_display_ordinal_and_evidence_and_rule() -> None:
    ruled = RuledThreshold(bound=_er(1, 1))
    assert is_refusal(
        AdmissionRequirement.try_create(
            "m", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, ruled, _evidence(), -1
        )
    )
    assert is_refusal(
        AdmissionRequirement.try_create(
            "m", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, ruled, _evidence(), True
        )
    )
    assert is_refusal(
        AdmissionRequirement.try_create(
            "m", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, ruled, "evidence", 0
        )
    )
    assert is_refusal(
        AdmissionRequirement.try_create(
            "m", UnitKind.DIMENSIONLESS_RATIO, Comparison.AT_LEAST, ruled, _evidence(), 0, "rule"
        )
    )


# --- AdmissionBar (AC2 set, canonical order) ---------------------------------


def test_bar_orders_requirements_canonically_by_measure_identity() -> None:
    a = _requirement("alpha")
    z = _requirement("zulu")
    m = _requirement("mike")
    forward = AdmissionBar.try_create([a, m, z])
    reverse = AdmissionBar.try_create([z, m, a])
    assert is_ok(forward)
    assert is_ok(reverse)
    assert [r.measure_identity for r in forward.value.requirements] == ["alpha", "mike", "zulu"]
    # canonical order gives the same identity regardless of declaration order
    assert forward.value.fp1_identity() == reverse.value.fp1_identity()


def test_bar_refuses_duplicate_measure_identity() -> None:
    result = AdmissionBar.try_create([_requirement("dup"), _requirement("dup")])
    assert is_refusal(result)


def test_bar_refuses_non_collection_and_non_requirement() -> None:
    assert is_refusal(AdmissionBar.try_create(42))
    assert is_refusal(AdmissionBar.try_create("nope"))
    assert is_refusal(AdmissionBar.try_create([_requirement(), "x"]))
    assert is_refusal(AdmissionBar.try_create([_requirement()], pending_slots=7))
    assert is_refusal(AdmissionBar.try_create([_requirement()], pending_slots=["x"]))


def test_bar_by_identity_view() -> None:
    bar = AdmissionBar.try_create([_requirement("a"), _requirement("b")])
    assert is_ok(bar)
    view = bar.value.by_identity()
    assert set(view) == {"a", "b"}


def test_bar_is_blank_via_not_yet_ruled_and_pending_slot() -> None:
    ruled_bar = AdmissionBar.try_create([_requirement("a")])
    assert is_ok(ruled_bar)
    assert ruled_bar.value.is_blank is False
    blank_threshold_bar = AdmissionBar.try_create([_requirement("a", threshold=_blank())])
    assert is_ok(blank_threshold_bar)
    assert blank_threshold_bar.value.is_blank is True
    slot = PendingSlot.try_create("GAP-0049")
    assert is_ok(slot)
    pending_bar = AdmissionBar.try_create([_requirement("a")], pending_slots=[slot.value])
    assert is_ok(pending_bar)
    assert pending_bar.value.is_blank is True
    assert bar_is_blank(pending_bar.value) is True
    assert bar_is_blank("not-a-bar") is False


def test_pending_slot_refuses_blank_ref() -> None:
    assert is_refusal(PendingSlot.try_create("  "))
    assert is_refusal(PendingSlot.try_create(None))


# --- reject_bar_aggregate (AC2 first-class prohibition) ----------------------


def test_reject_bar_aggregate_is_a_policy_rejection() -> None:
    for construct in ("composite-score", "weighted-aggregate", "tier-band", "rating", None):
        refusal = reject_bar_aggregate(construct)
        assert refusal.category is RefusalCategory.POLICY_REJECTION


# --- blank blocks live money (AC3) -------------------------------------------


def test_blank_bar_blocks_live_binding_but_binds_non_live_freely() -> None:
    blank_bar = AdmissionBar.try_create([_requirement("a", threshold=_blank())])
    assert is_ok(blank_bar)
    live = check_live_binding_admissible(blank_bar.value, AccountRole.LIVE)
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION
    for role in (AccountRole.DEMO, AccountRole.PAPER_VALIDATION, AccountRole.PAPER_BENCHED):
        assert is_ok(check_live_binding_admissible(blank_bar.value, role))


def test_non_blank_bar_admits_live_binding() -> None:
    bar = AdmissionBar.try_create([_requirement("a")])
    assert is_ok(bar)
    assert is_ok(check_live_binding_admissible(bar.value, AccountRole.LIVE))


def test_pending_slot_bar_blocks_live() -> None:
    slot = PendingSlot.try_create("GAP-0048")
    assert is_ok(slot)
    bar = AdmissionBar.try_create([_requirement("a")], pending_slots=[slot.value])
    assert is_ok(bar)
    assert is_refusal(check_live_binding_admissible(bar.value, AccountRole.LIVE))


def test_check_live_binding_refuses_bad_inputs() -> None:
    bar = AdmissionBar.try_create([_requirement("a")])
    assert is_ok(bar)
    assert is_refusal(check_live_binding_admissible("not-a-bar", AccountRole.LIVE))
    assert is_refusal(check_live_binding_admissible(bar.value, "not-a-role"))


# --- no paper role gates live money (AC4) ------------------------------------


def test_paper_role_gating_live_binding_is_policy_rejection() -> None:
    paper_req = _requirement("a", evidence=_evidence(role=AccountRole.PAPER_VALIDATION))
    bar = AdmissionBar.try_create([paper_req])
    assert is_ok(bar)
    refusal = check_no_paper_role_gates_live(bar.value, AccountRole.LIVE)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.POLICY_REJECTION


def test_paper_role_is_fine_for_non_live_binding() -> None:
    paper_req = _requirement("a", evidence=_evidence(role=AccountRole.PAPER_BENCHED))
    bar = AdmissionBar.try_create([paper_req])
    assert is_ok(bar)
    assert is_ok(check_no_paper_role_gates_live(bar.value, AccountRole.DEMO))
    assert is_ok(check_no_paper_role_gates_live(bar.value, AccountRole.PAPER_VALIDATION))


def test_live_role_evidence_admits_live_binding() -> None:
    bar = AdmissionBar.try_create([_requirement("a", evidence=_evidence(role=AccountRole.LIVE))])
    assert is_ok(bar)
    assert is_ok(check_no_paper_role_gates_live(bar.value, AccountRole.LIVE))


def test_check_no_paper_role_refuses_bad_inputs() -> None:
    bar = AdmissionBar.try_create([_requirement("a")])
    assert is_ok(bar)
    assert is_refusal(check_no_paper_role_gates_live("not-a-bar", AccountRole.LIVE))
    assert is_refusal(check_no_paper_role_gates_live(bar.value, "not-a-role"))


def test_is_paper_role_helper() -> None:
    assert is_paper_role(AccountRole.PAPER_VALIDATION) is True
    assert is_paper_role(AccountRole.PAPER_BENCHED) is True
    assert is_paper_role(AccountRole.LIVE) is False
    assert is_paper_role("nonsense") is False


# --- evaluate_requirement: exact measures ------------------------------------


def test_evaluate_exact_at_least_pass_fail_tie() -> None:
    req = _requirement(comparison=Comparison.AT_LEAST)  # threshold 3/2
    above = evaluate_requirement(req, _er(2, 1))
    assert is_ok(above)
    assert above.value is RequirementVerdict.PASS
    below = evaluate_requirement(req, _er(1, 1))
    assert is_ok(below)
    assert below.value is RequirementVerdict.FAIL
    tie = evaluate_requirement(req, _er(3, 2))
    assert is_ok(tie)
    assert tie.value is RequirementVerdict.PASS  # no rule => boundary-inclusive default


def test_evaluate_exact_at_most() -> None:
    req = _requirement(comparison=Comparison.AT_MOST)  # threshold 3/2
    assert _verdict(req, _er(1, 1)) is RequirementVerdict.PASS
    assert _verdict(req, _er(2, 1)) is RequirementVerdict.FAIL
    assert _verdict(req, _er(3, 2)) is RequirementVerdict.PASS


def test_evaluate_within_band_interior_edge_outside() -> None:
    band = Band.try_create(_er(1, 1), _er(3, 1))
    assert is_ok(band)
    ruled = RuledThreshold.try_create(band.value)
    assert is_ok(ruled)
    req = _requirement(comparison=Comparison.WITHIN_BAND, threshold=ruled.value)
    assert _verdict(req, _er(2, 1)) is RequirementVerdict.PASS
    assert _verdict(req, _er(1, 1)) is RequirementVerdict.PASS
    assert _verdict(req, _er(3, 1)) is RequirementVerdict.PASS
    assert _verdict(req, _er(5, 1)) is RequirementVerdict.FAIL


def test_evaluate_exact_measure_unit_mismatch_refused() -> None:
    req = _requirement()  # unit dimensionless-ratio
    result = evaluate_requirement(req, _er(2, 1, UnitKind.R_MULTIPLE))
    assert is_refusal(result)


def test_evaluate_blank_requirement_is_not_yet_ruled() -> None:
    req = _requirement(threshold=_blank())
    result = evaluate_requirement(req, _er(2, 1))
    assert is_ok(result)
    assert result.value is RequirementVerdict.NOT_YET_RULED


def test_evaluate_refuses_bool_and_non_requirement() -> None:
    req = _requirement()
    assert is_refusal(evaluate_requirement(req, True))
    assert is_refusal(evaluate_requirement("not-a-requirement", _er(1, 1)))


def test_evaluate_refuses_non_measure_object() -> None:
    req = _requirement()
    assert is_refusal(evaluate_requirement(req, "1.5"))


# --- evaluate_requirement: float measures cross analytic->exact (AC6) --------


def test_float_measure_needs_declared_comparison_rule() -> None:
    req = _requirement()  # no comparison_rule
    result = evaluate_requirement(req, 1.6)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT


def test_float_measure_crosses_under_declared_rule() -> None:
    rule = ComparisonRule.try_create(2, RoundingMode.HALF_UP, TieDisposition.PASS_ON_TIE)
    assert is_ok(rule)
    req = _requirement(comparison=Comparison.AT_LEAST, comparison_rule=rule.value)  # threshold 1.5
    # 1.499 rounds HALF_UP at 2 places to 1.50 => tie => PASS
    assert _verdict(req, 1.499) is RequirementVerdict.PASS
    # 1.494 rounds to 1.49 => below => FAIL
    assert _verdict(req, 1.494) is RequirementVerdict.FAIL
    # 1.6 => 1.60 => above => PASS
    assert _verdict(req, 1.6) is RequirementVerdict.PASS


def test_float_tie_disposition_fail_on_tie() -> None:
    rule = ComparisonRule.try_create(2, RoundingMode.HALF_UP, TieDisposition.FAIL_ON_TIE)
    assert is_ok(rule)
    req = _requirement(comparison=Comparison.AT_LEAST, comparison_rule=rule.value)  # threshold 1.5
    tie = evaluate_requirement(req, 1.5)
    assert is_ok(tie)
    assert tie.value is RequirementVerdict.FAIL


def test_float_measure_must_be_finite() -> None:
    rule = ComparisonRule.try_create(2, RoundingMode.HALF_UP, TieDisposition.PASS_ON_TIE)
    assert is_ok(rule)
    req = _requirement(comparison_rule=rule.value)
    assert is_refusal(evaluate_requirement(req, float("nan")))
    assert is_refusal(evaluate_requirement(req, float("inf")))


# --- evaluate_bar: per-requirement verdicts, never a composite score (AC2) ---


def test_evaluate_bar_returns_per_requirement_verdicts() -> None:
    a = _requirement("a", comparison=Comparison.AT_LEAST)  # threshold 3/2
    b = _requirement("b", comparison=Comparison.AT_MOST)  # threshold 3/2
    blank = _requirement("c", threshold=_blank())
    bar = AdmissionBar.try_create([a, b, blank])
    assert is_ok(bar)
    verdicts = evaluate_bar(bar.value, {"a": _er(2, 1), "b": _er(1, 1)})
    assert is_ok(verdicts)
    assert verdicts.value["a"] is RequirementVerdict.PASS
    assert verdicts.value["b"] is RequirementVerdict.PASS
    assert verdicts.value["c"] is RequirementVerdict.NOT_YET_RULED


def test_evaluate_bar_ruled_requirement_needs_its_measure() -> None:
    bar = AdmissionBar.try_create([_requirement("a")])
    assert is_ok(bar)
    result = evaluate_bar(bar.value, {})
    assert is_refusal(result)


def test_evaluate_bar_propagates_requirement_refusal() -> None:
    bar = AdmissionBar.try_create([_requirement("a")])  # no comparison_rule
    assert is_ok(bar)
    result = evaluate_bar(bar.value, {"a": 1.6})  # float without a rule
    assert is_refusal(result)


def test_evaluate_bar_refuses_bad_inputs() -> None:
    bar = AdmissionBar.try_create([_requirement("a")])
    assert is_ok(bar)
    assert is_refusal(evaluate_bar("not-a-bar", {}))
    assert is_refusal(evaluate_bar(bar.value, [("a", 1)]))


# --- fp1 identity contains the declared parts --------------------------------


def test_requirement_fp1_carries_comparison_rule_when_present() -> None:
    rule = ComparisonRule.try_create(2, RoundingMode.HALF_UP, TieDisposition.PASS_ON_TIE)
    assert is_ok(rule)
    with_rule = _requirement(comparison_rule=rule.value)
    without_rule = _requirement()
    assert "comparison_rule" in with_rule.fp1_identity()
    assert "comparison_rule" not in without_rule.fp1_identity()


def test_money_unit_requirement_evaluates_exact_money_measure() -> None:
    # An exact (non-float) money-unit measure compares directly, no crossing needed.
    threshold = RuledThreshold.try_create(_er(10_000, 1, UnitKind.MONEY))
    assert is_ok(threshold)
    req = AdmissionRequirement.try_create(
        "min_capital",
        UnitKind.MONEY,
        Comparison.AT_LEAST,
        threshold.value,
        _evidence(),
        0,
    )
    assert is_ok(req)
    measure = Money(value=1_500_000, currency="USD", scale=2)  # 15000.00
    verdict = evaluate_requirement(req.value, measure)
    assert is_ok(verdict)
    assert verdict.value is RequirementVerdict.PASS
