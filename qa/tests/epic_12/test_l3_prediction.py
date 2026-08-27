"""L3 — prediction-linter contract against an INJECTED CT-28 binding context.

QML never imports qmf-venue; the binding context is a test-owned fixture.

- E12-L3-07 (P0): the four pinned checks (a footprint, b exit-subset, c family-resolves, d streams). (Story 12.6)
- E12-L3-08 (P1): zero-exit-kind Book admits an entry-only bot; (c)/(d) failures at bind time. (FM-7/8/9)
- E12-L3-11 (P1): a blank footprint_requirement passes registration but blocks LIVE binding. (FM-11/12)
"""

from __future__ import annotations

import _world as w
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.identity import AccountRole
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.admission_bar import Comparison, RuledThreshold
from qmf.risk.door import ExitKind, ExitLogicRef
from qmf.risk.exit_policy import ExitPolicy
from qmf.risk.footprint_requirements import (
    FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING,
    FootprintRequirement,
    FootprintRequirements,
    check_footprint_requirements_live_binding,
)
from qml.conformance import lint_prediction

_VENUE_CAPS = frozenset({"trading", "time-interval"})


def _exit_ref() -> ExitLogicRef:
    return w.unwrap(ExitLogicRef.try_create("static-protective-stop"), "exit ref")


def _exit_policy(
    *, family: str = w.FAMILY, permitted: tuple[ExitKind, ...] = (ExitKind.CLOSE_FULL,)
) -> ExitPolicy:
    return w.unwrap(
        ExitPolicy.try_create({family: _exit_ref()}, list(permitted), "required"), "exit policy"
    )


def test_e12_l3_07_all_four_checks_pass_on_a_compatible_binding() -> None:
    """A compatible CT-28 context passes all four pinned checks (a)(b)(c)(d)."""
    d = w.build_world()["declaration"]
    verdict = lint_prediction(
        d,
        exit_policy=_exit_policy(),
        footprint_requirements=(),  # empty requirements are satisfied (a)
        venue_capabilities=_VENUE_CAPS,
        account_role=AccountRole.DEMO,
    )
    assert is_ok(verdict), verdict
    assert verdict.value.checks == (
        "footprint_satisfies_requirements",
        "exit_intent_subset",
        "family_resolves_exit_policy",
        "stream_set_within_venue_capabilities",
    )


def test_e12_l3_07_footprint_requirement_unsatisfied_fails() -> None:
    """(a) A ruled footprint_requirement the footprint cannot meet is a policy rejection."""
    d = w.build_world()["declaration"]
    threshold = w.unwrap(
        RuledThreshold.try_create(ExactRational.try_create(5, 1, UnitKind.COUNT).value),
        "threshold",
    )
    requirement = w.unwrap(
        FootprintRequirement.try_create(
            "stream_set", "stream_set", UnitKind.COUNT, Comparison.AT_LEAST, threshold, 0
        ),
        "requirement",
    )
    requirements = w.unwrap(FootprintRequirements.try_create([requirement]), "requirements")
    refusal = lint_prediction(
        d,
        exit_policy=_exit_policy(),
        footprint_requirements=requirements,  # demands >= 5 streams; footprint has 1
        venue_capabilities=_VENUE_CAPS,
        account_role=AccountRole.DEMO,
    )
    assert is_refusal(refusal)
    assert refusal.context.get("field") == "footprint_requirements"


def test_e12_l3_07_exit_kind_not_in_book_policy_fails() -> None:
    """(b) A bot permitted-exit kind outside the Book's exit_policy is a policy rejection."""
    d = w.build_world(permitted=("tighten_protective_stop",))["declaration"]
    refusal = lint_prediction(
        d,
        exit_policy=_exit_policy(permitted=(ExitKind.CLOSE_FULL,)),  # book allows only close_full
        footprint_requirements=(),
        venue_capabilities=_VENUE_CAPS,
        account_role=AccountRole.DEMO,
    )
    assert is_refusal(refusal)
    assert refusal.context.get("field") == "permitted_exit_intents"


def test_e12_l3_08_zero_exit_kind_book_admits_entry_only_bot() -> None:
    """A Book that declares zero permitted exit kinds admits an entry-only bot (entry is never gated)."""
    d = w.build_world(permitted=())["declaration"]  # entry-only bot
    policy = w.unwrap(ExitPolicy.try_create({w.FAMILY: _exit_ref()}, [], "optional"), "policy")
    verdict = lint_prediction(
        d,
        exit_policy=policy,
        footprint_requirements=(),
        venue_capabilities=_VENUE_CAPS,
        account_role=AccountRole.DEMO,
    )
    assert is_ok(verdict), verdict


def test_e12_l3_08_family_resolves_nothing_fails() -> None:
    """(c) A family that resolves neither an explicit entry nor a catch-all is a policy rejection."""
    d = w.build_world()["declaration"]  # family 'trend-follow'
    policy = w.unwrap(
        ExitPolicy.try_create({"a-different-family": _exit_ref()}, [ExitKind.CLOSE_FULL], "required"),
        "policy",
    )
    refusal = lint_prediction(
        d,
        exit_policy=policy,
        footprint_requirements=(),
        venue_capabilities=_VENUE_CAPS,
        account_role=AccountRole.DEMO,
    )
    assert is_refusal(refusal)
    assert refusal.context.get("field") == "exit_policy"


def test_e12_l3_08_stream_set_exceeding_venue_capabilities_fails() -> None:
    """(d) A stream set exceeding the binding's declared venue capabilities fails at bind time."""
    d = w.build_world()["declaration"]
    refusal = lint_prediction(
        d,
        exit_policy=_exit_policy(),
        footprint_requirements=(),
        venue_capabilities=frozenset({"trading"}),  # missing 'time-interval'
        account_role=AccountRole.DEMO,
    )
    assert is_refusal(refusal)
    assert refusal.context.get("field") == "venue_capabilities"
    assert refusal.context.get("bind_time") is True


def test_e12_l3_11_blank_requirement_passes_registration_blocks_live() -> None:
    """A blank footprint_requirement registers/binds non-live, but LIVE binding is refused."""
    d = w.build_world()["declaration"]
    blank = FORMAT_1_FOOTPRINT_REQUIREMENTS_PENDING  # the reserved pending(GAP-0047) blank

    # Non-live (demo) binding passes.
    demo = lint_prediction(
        d,
        exit_policy=_exit_policy(),
        footprint_requirements=blank,
        venue_capabilities=_VENUE_CAPS,
        account_role=AccountRole.DEMO,
    )
    assert is_ok(demo)
    assert demo.value.live_binding_blocked is True

    # Live binding is a policy rejection while the requirement is blank.
    live = lint_prediction(
        d,
        exit_policy=_exit_policy(),
        footprint_requirements=blank,
        venue_capabilities=_VENUE_CAPS,
        account_role=AccountRole.LIVE,
    )
    assert is_refusal(live)
    assert live.category is RefusalCategory.POLICY_REJECTION

    # The same blank-blocks-live rule directly on the CT-22 surface.
    assert is_ok(check_footprint_requirements_live_binding(blank, AccountRole.DEMO))
    assert is_refusal(check_footprint_requirements_live_binding(blank, AccountRole.LIVE))


def test_e12_l3_11_requirement_set_shape_is_format_2_only() -> None:
    """The footprint_requirements requirement-set shape lands only via the CT-22 format-2 mint."""
    format_1 = FootprintRequirements.try_create((), contract_format_version=1)
    assert is_refusal(format_1)
    assert format_1.category is RefusalCategory.UNSUPPORTED_CAPABILITY
