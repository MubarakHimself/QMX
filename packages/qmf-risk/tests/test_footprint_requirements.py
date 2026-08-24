"""Story 11.7 — CT-22 format-2 footprint_requirements requirement-set shape."""

from __future__ import annotations

from qmf.core import AccountRole, ExactRational, RefusalCategory, UnitKind, is_ok, is_refusal
from qmf.risk.admission_bar import Band, Comparison, RuledThreshold
from qmf.risk.footprint_requirements import (
    FOOTPRINT_REQUIREMENTS_CONTRACT_FORMAT_VERSION,
    FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING,
    FootprintFieldKind,
    FootprintRequirement,
    FootprintRequirements,
    check_footprint_requirements_live_binding,
)
from qmf.risk.grammar import NotYetRuled
from qmf.risk.migrations import THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS


def _blank(gap: str = "GAP-0048") -> NotYetRuled:
    result = NotYetRuled.try_create(gap)
    assert is_ok(result)
    return result.value


def _er(num: int, den: int, kind: UnitKind = UnitKind.COUNT) -> ExactRational:
    result = ExactRational.try_create(num, den, kind)
    assert is_ok(result)
    return result.value


def _req(
    field_identity: str = "producers.sma",
    *,
    field_kind: FootprintFieldKind = FootprintFieldKind.PRODUCER_BINDINGS,
    comparison: Comparison = Comparison.AT_LEAST,
    threshold: object | None = None,
    unit: UnitKind = UnitKind.COUNT,
    display_ordinal: int = 0,
) -> FootprintRequirement:
    if threshold is None:
        threshold = _blank()
    result = FootprintRequirement.try_create(
        field_kind, field_identity, unit, comparison, threshold, display_ordinal
    )
    assert is_ok(result)
    return result.value


def test_format_1_pending_slot_is_gap_0047() -> None:
    assert FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING.ref == "GAP-0047"
    assert FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING.fp1_identity()["class"] == "pending-slot"


def test_requirement_set_shape_is_format_2_only() -> None:
    assert FOOTPRINT_REQUIREMENTS_CONTRACT_FORMAT_VERSION == 2
    assert is_refusal(FootprintRequirements.try_create((), contract_format_version=1))
    assert is_refusal(FootprintRequirements.try_create((), contract_format_version=True))
    empty = FootprintRequirements.try_create(())
    assert is_ok(empty)
    assert empty.value.is_blank is False


def test_field_kinds_are_the_three_ct33_loci() -> None:
    assert {member.value for member in FootprintFieldKind} == {
        "stream_set",
        "calendars",
        "producer_bindings",
    }


def test_blank_requirement_blocks_live_and_binds_non_live() -> None:
    req = _req(threshold=_blank("GAP-0048"))
    bar = FootprintRequirements.try_create([req])
    assert is_ok(bar)
    assert bar.value.is_blank is True
    live = check_footprint_requirements_live_binding(bar.value, AccountRole.LIVE)
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION
    reason = str(live.context["reason"])
    assert THRESHOLD_GAPS_BEHIND_NEW_ADMISSION_BAR_FIELDS[0] in reason
    for role in (AccountRole.DEMO, AccountRole.PAPER_VALIDATION, AccountRole.PAPER_BENCHED):
        assert is_ok(check_footprint_requirements_live_binding(bar.value, role))


def test_format_1_pending_slot_blocks_live() -> None:
    live = check_footprint_requirements_live_binding(
        FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING, AccountRole.LIVE
    )
    assert is_refusal(live)
    assert is_ok(
        check_footprint_requirements_live_binding(
            FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING, AccountRole.DEMO
        )
    )


def test_ruled_requirement_admits_live() -> None:
    ruled = RuledThreshold.try_create(_er(1, 1))
    assert is_ok(ruled)
    req = _req(threshold=ruled.value)
    bar = FootprintRequirements.try_create([req])
    assert is_ok(bar)
    assert bar.value.is_blank is False
    assert is_ok(check_footprint_requirements_live_binding(bar.value, AccountRole.LIVE))


def test_canonical_order_by_field_identity() -> None:
    a = _req("alpha")
    z = _req("zulu")
    forward = FootprintRequirements.try_create([z, a])
    reverse = FootprintRequirements.try_create([a, z])
    assert is_ok(forward)
    assert is_ok(reverse)
    assert [r.field_identity for r in forward.value.requirements] == ["alpha", "zulu"]
    assert forward.value.fp1_identity() == reverse.value.fp1_identity()


def test_duplicate_field_identity_is_invalid() -> None:
    assert is_refusal(FootprintRequirements.try_create([_req("dup"), _req("dup")]))


def test_requirement_refusals() -> None:
    ruled = RuledThreshold.try_create(_er(1, 1))
    assert is_ok(ruled)
    assert is_refusal(
        FootprintRequirement.try_create(
            "not-a-kind", "id", UnitKind.COUNT, Comparison.AT_LEAST, ruled.value, 0
        )
    )
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET, "  ", UnitKind.COUNT, Comparison.AT_LEAST, ruled.value, 0
        )
    )
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET, "id", "nope", Comparison.AT_LEAST, ruled.value, 0
        )
    )
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET, "id", UnitKind.COUNT, "weighted", ruled.value, 0
        )
    )
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET, "id", UnitKind.COUNT, Comparison.AT_LEAST, None, 0
        )
    )
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET,
            "id",
            UnitKind.COUNT,
            Comparison.AT_LEAST,
            ruled.value,
            -1,
        )
    )
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET,
            "id",
            UnitKind.COUNT,
            Comparison.AT_LEAST,
            ruled.value,
            True,
        )
    )
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET, "id", UnitKind.COUNT, Comparison.AT_LEAST, "1.5", 0
        )
    )


def test_within_band_needs_band() -> None:
    scalar = RuledThreshold.try_create(_er(1, 1))
    assert is_ok(scalar)
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.CALENDARS,
            "calendars.forex",
            UnitKind.COUNT,
            Comparison.WITHIN_BAND,
            scalar.value,
            0,
        )
    )
    band = Band.try_create(_er(1, 1), _er(3, 1))
    assert is_ok(band)
    ruled = RuledThreshold.try_create(band.value)
    assert is_ok(ruled)
    assert is_ok(
        FootprintRequirement.try_create(
            FootprintFieldKind.CALENDARS,
            "calendars.forex",
            UnitKind.COUNT,
            Comparison.WITHIN_BAND,
            ruled.value,
            0,
        )
    )


def test_scalar_comparison_rejects_band() -> None:
    band = Band.try_create(_er(1, 1), _er(3, 1))
    assert is_ok(band)
    ruled = RuledThreshold.try_create(band.value)
    assert is_ok(ruled)
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET,
            "stream.trading",
            UnitKind.COUNT,
            Comparison.AT_LEAST,
            ruled.value,
            0,
        )
    )


def test_threshold_unit_must_match() -> None:
    ruled = RuledThreshold.try_create(_er(1, 1, UnitKind.R_MULTIPLE))
    assert is_ok(ruled)
    assert is_refusal(
        FootprintRequirement.try_create(
            FootprintFieldKind.STREAM_SET,
            "stream.trading",
            UnitKind.COUNT,
            Comparison.AT_LEAST,
            ruled.value,
            0,
        )
    )


def test_collection_and_check_refusals() -> None:
    assert is_refusal(FootprintRequirements.try_create("nope"))
    assert is_refusal(FootprintRequirements.try_create([_req(), "x"]))
    assert is_refusal(check_footprint_requirements_live_binding("nope", AccountRole.LIVE))
    bar = FootprintRequirements.try_create([_req()])
    assert is_ok(bar)
    assert is_refusal(check_footprint_requirements_live_binding(bar.value, "not-a-role"))
    view = bar.value.by_identity()
    assert "producers.sma" in view


def test_gap_0049_blank_also_blocks_live() -> None:
    req = _req("other", threshold=_blank("GAP-0049"))
    bar = FootprintRequirements.try_create([req])
    assert is_ok(bar)
    assert is_refusal(check_footprint_requirements_live_binding(bar.value, AccountRole.LIVE))
