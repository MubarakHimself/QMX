"""Story 40.6 — default-deny parent surfaces and capability barrier constants."""

from __future__ import annotations

from pathlib import Path

import pytest
from qma.core.barriers import (
    CAPABILITY_LADDER,
    MONEY_PATH_DENIAL_NOT_LIFTABLE_BY,
    MONEY_PATH_DENIED_ACTS,
    MONEY_PATH_DENY_LIST,
    PERMITTED_PARENT_SURFACES,
    PROHIBITED_RECORD_FAMILIES,
    QMA_CORE_ALLOWED_DEPS,
    QMA_DAEMON_ALLOWED_DEPS,
    QMA_MINTED_MONEY_PATH_VALUES,
    QMA_MINTED_PROMOTION_COMMAND,
    QMA_WIRE_ALLOWED_DEPS,
    SOLE_PERMITTED_PARENT_WRITE,
    CapabilityError,
    CapabilityRung,
    DependencyBoundaryError,
    MoneyPathAct,
    MoneyPathDeniedAct,
    MoneyPathDenyError,
    ParentLibrary,
    ParentSurfaceError,
    ParentSurfaceKind,
    ProhibitedMutation,
    ProhibitedRecordFamily,
    assert_deny_list_not_widenable,
    assert_ladder_is_code_declared,
    assert_no_qmf_venue_import,
    assert_no_zone_transition,
    assert_package_deps_within,
    assert_record_family_immutable,
    capability_rung_rank,
    is_money_path_act_denied,
    is_parent_surface_permitted,
    match_money_path_act,
    parse_capability_rung,
    refuse_money_path_permission,
    refuse_money_path_registration,
    refuse_parent_money_path_write,
    refuse_unlisted_parent_surface,
    refuse_zone_transition_surface,
)
from qma.core.refusals import ProhibitedMoneyPathTool
from qmf.core import is_refusal

AGENTS_ROOT = Path(__file__).resolve().parents[3]
CORE_PKG = AGENTS_ROOT / "packages" / "qma-core"
WIRE_PKG = AGENTS_ROOT / "packages" / "qma-wire"
DAEMON_PKG = AGENTS_ROOT / "packages" / "qma-daemon"
PLUGINS_ROOT = AGENTS_ROOT / "plugins"


def test_qma_core_depends_only_on_qmf_core() -> None:
    assert frozenset({"qmf-core"}) == QMA_CORE_ALLOWED_DEPS
    assert_package_deps_within("qma-core", CORE_PKG / "pyproject.toml")


def test_qma_wire_depends_only_on_core_and_qmf_core() -> None:
    assert frozenset({"qma-core", "qmf-core"}) == QMA_WIRE_ALLOWED_DEPS
    assert_package_deps_within("qma-wire", WIRE_PKG / "pyproject.toml")


def test_daemon_deps_limited_to_declared_parent_set() -> None:
    assert (
        frozenset(
            {
                "qma-core",
                "qma-wire",
                "qmf-core",
                "qmf-registry",
                "qmf-data",
                "qmf-risk",
                "tzdata",
            }
        )
        == QMA_DAEMON_ALLOWED_DEPS
    )
    assert_package_deps_within("qma-daemon", DAEMON_PKG / "pyproject.toml")
    # Venue must never appear in the daemon allowlist or pyproject.
    text = (DAEMON_PKG / "pyproject.toml").read_text(encoding="utf-8")
    assert "qmf-venue" not in text


def test_no_qma_tree_imports_qmf_venue() -> None:
    assert_no_qmf_venue_import(CORE_PKG / "src")
    assert_no_qmf_venue_import(WIRE_PKG / "src")
    assert_no_qmf_venue_import(DAEMON_PKG / "src")
    assert_no_qmf_venue_import(PLUGINS_ROOT)
    for pack in PLUGINS_ROOT.iterdir():
        if pack.is_dir():
            assert_no_qmf_venue_import(pack)


def test_permitted_parent_surfaces_default_deny() -> None:
    assert (ParentLibrary.QMF_REGISTRY, ParentSurfaceKind.VALUE_TYPE) in (PERMITTED_PARENT_SURFACES)
    assert (ParentLibrary.QMF_REGISTRY, ParentSurfaceKind.TYPED_REFUSAL) in (
        PERMITTED_PARENT_SURFACES
    )
    assert (ParentLibrary.QMF_REGISTRY, ParentSurfaceKind.PURE_CALCULATION) in (
        PERMITTED_PARENT_SURFACES
    )
    assert (ParentLibrary.QMF_REGISTRY, ParentSurfaceKind.DEV_ZONE_CANDIDATE_WRITE) in (
        PERMITTED_PARENT_SURFACES
    )
    assert (ParentLibrary.QMF_RISK, ParentSurfaceKind.VALUE_TYPE) in PERMITTED_PARENT_SURFACES
    assert (ParentLibrary.QMF_RISK, ParentSurfaceKind.TYPED_REFUSAL) in PERMITTED_PARENT_SURFACES
    assert (ParentLibrary.QMF_RISK, ParentSurfaceKind.PURE_CALCULATION) in (
        PERMITTED_PARENT_SURFACES
    )
    # qmf-risk has no write surface.
    assert (
        ParentLibrary.QMF_RISK,
        ParentSurfaceKind.DEV_ZONE_CANDIDATE_WRITE,
    ) not in PERMITTED_PARENT_SURFACES
    assert is_parent_surface_permitted("qmf-registry", "value_type")
    assert not is_parent_surface_permitted("qmf-risk", "dev_zone_candidate_write")
    with pytest.raises(ParentSurfaceError, match="default-deny"):
        refuse_unlisted_parent_surface(
            ParentLibrary.QMF_RISK,
            ParentSurfaceKind.DEV_ZONE_CANDIDATE_WRITE,
        )
    with pytest.raises(ParentSurfaceError, match="not a parent surface kind"):
        refuse_unlisted_parent_surface("qmf-registry", "zone_transition")


@pytest.mark.parametrize(
    "family",
    list(ProhibitedRecordFamily),
)
@pytest.mark.parametrize(
    "mutation",
    list(ProhibitedMutation),
)
def test_prohibited_record_families_immutable(
    family: ProhibitedRecordFamily,
    mutation: ProhibitedMutation,
) -> None:
    assert family in PROHIBITED_RECORD_FAMILIES
    with pytest.raises(ParentSurfaceError, match="cannot"):
        assert_record_family_immutable(family, mutation)


def test_zone_transition_surfaces_uncallable() -> None:
    with pytest.raises(ParentSurfaceError, match="zone-transition"):
        assert_no_zone_transition()


def test_capability_ladder_six_ordered_rungs_code_declared() -> None:
    assert_ladder_is_code_declared()
    assert CAPABILITY_LADDER == (
        CapabilityRung.API_OR_STRUCTURED_TOOL,
        CapabilityRung.CLI,
        CapabilityRung.CONTAINERIZED_PROGRAM,
        CapabilityRung.BROWSER_AUTOMATION,
        CapabilityRung.VISUAL_BROWSER_OR_COMPUTER_USE,
        CapabilityRung.PERSISTENT_REMOTE_DESKTOP,
    )
    assert [r.value for r in CAPABILITY_LADDER] == [
        "api_or_structured_tool",
        "cli",
        "containerized_program",
        "browser_automation",
        "visual_browser_or_computer_use",
        "persistent_remote_desktop",
    ]
    assert capability_rung_rank(CapabilityRung.CLI) == 1
    assert parse_capability_rung("browser_automation") is CapabilityRung.BROWSER_AUTOMATION
    with pytest.raises(CapabilityError):
        parse_capability_rung("settings_override")


def test_money_path_deny_list_refuses_acts_at_registration() -> None:
    assert (
        frozenset(
            {
                MoneyPathAct.ORDER,
                MoneyPathAct.POSITION,
                MoneyPathAct.PROTECTION,
                MoneyPathAct.SIZING,
                MoneyPathAct.BINDING,
                MoneyPathAct.MODE,
                MoneyPathAct.CONTROL,
                MoneyPathAct.ZONE_TRANSITION,
                MoneyPathAct.PROMOTION,
            }
        )
        == MONEY_PATH_DENY_LIST
    )
    for act in MoneyPathAct:
        assert is_money_path_act_denied(act)
        refusal = refuse_money_path_registration(
            tool_id=f"trading:{act.value}",
            act=act,
            plugin_id="trading-readonly",
        )
        assert isinstance(refusal, ProhibitedMoneyPathTool)
        assert ProhibitedMoneyPathTool.matches(refusal)
        assert refusal.context["tool_id"] == f"trading:{act.value}"
        assert refusal.context["matched_act"] == act.value
        assert refusal.context["plugin_id"] == "trading-readonly"


def test_money_path_deny_list_cannot_be_widened() -> None:
    assert_deny_list_not_widenable()
    assert_deny_list_not_widenable(set(MoneyPathAct))
    # Narrowing (subset) is not widening.
    assert_deny_list_not_widenable({MoneyPathAct.ORDER, MoneyPathAct.POSITION})
    with pytest.raises(MoneyPathDenyError, match="cannot be widened"):
        assert_deny_list_not_widenable({"order", "invented_execution_act"})
    with pytest.raises(MoneyPathDenyError, match="cannot be widened"):
        assert_deny_list_not_widenable({"paper_only_order"})


@pytest.mark.parametrize(
    ("act", "matched"),
    [
        ("submit_order", "submit_order"),
        ("amend_order", "amend_order"),
        ("cancel_order", "cancel_order"),
        ("replace_order", "replace_order"),
        ("place_order", "submit_order"),
        ("open_position", "open_position"),
        ("close_position", "close_position"),
        ("reduce_position", "reduce_position"),
        ("hedge_position", "hedge_position"),
        ("set_protection", "set_protection"),
        ("amend_protection", "amend_protection"),
        ("size", "size"),
        ("resize", "resize"),
        ("mint_sizing_decision", "mint_sizing_decision"),
        ("create_binding", "create_binding"),
        ("amend_binding", "amend_binding"),
        ("activate_binding", "activate_binding"),
        ("stand_down_binding", "stand_down_binding"),
        ("delete_binding", "delete_binding"),
        ("set_book_mode", "set_book_mode"),
        ("set_seat_state", "set_seat_state"),
        ("set_book_parameter", "set_book_parameter"),
        ("set_bms_parameter", "set_bms_parameter"),
        ("set_priority_rank", "set_priority_rank"),
        ("set_capital_floor", "set_capital_floor"),
        ("arm_kill_switch", "arm_kill_switch"),
        ("disarm_kill_switch", "disarm_kill_switch"),
        ("change_kill_switch", "change_kill_switch"),
        ("change_control_action", "change_control_action"),
        ("zone_transition", "zone_transition"),
        ("paper_only_submit_order", "submit_order"),
        ("paper_only_order", "order"),
        ("submit an order", "submit_order"),
    ],
)
def test_act_level_deny_list_matches_enumerated_verbs(act: str, matched: str) -> None:
    assert is_money_path_act_denied(act)
    assert match_money_path_act(act) == matched


def test_act_level_deny_list_does_not_match_read_and_calculate() -> None:
    for allowed in (
        "read",
        "read_positions",
        "fetch_bars",
        "risk_calculate",
        "search",
        "summarize",
    ):
        assert not is_money_path_act_denied(allowed)
        assert match_money_path_act(allowed) is None


def test_denied_act_vocabulary_is_code_declared() -> None:
    assert frozenset(MoneyPathDeniedAct) == MONEY_PATH_DENIED_ACTS
    assert QMA_MINTED_PROMOTION_COMMAND is None
    assert QMA_MINTED_MONEY_PATH_VALUES == ()
    assert "check_fn" in MONEY_PATH_DENIAL_NOT_LIFTABLE_BY
    assert "role" in MONEY_PATH_DENIAL_NOT_LIFTABLE_BY
    assert SOLE_PERMITTED_PARENT_WRITE == (
        ParentLibrary.QMF_REGISTRY,
        ParentSurfaceKind.DEV_ZONE_CANDIDATE_WRITE,
    )


def test_permission_cannot_lift_money_path_denial() -> None:
    refusal = refuse_money_path_permission(
        tool_id="trading:place_order",
        act="submit_order",
        plugin_id="trading-readonly",
        via="role",
    )
    assert isinstance(refusal, ProhibitedMoneyPathTool)
    assert refusal.context["matched_act"] == "submit_order"
    assert refusal.context["via"] == "role"


def test_parent_money_path_write_returns_typed_refusal() -> None:
    for family in ProhibitedRecordFamily:
        refusal = refuse_parent_money_path_write(family)
        assert is_refusal(refusal)
        assert refusal.context["family"] == family.value
    zone = refuse_zone_transition_surface()
    assert is_refusal(zone)
    assert zone.context["field"] == "zone_transition"


def test_dependency_boundary_rejects_extras() -> None:
    with pytest.raises(DependencyBoundaryError):
        # Point at wire pyproject while asserting core allowlist — extras expected.
        assert_package_deps_within("qma-core", WIRE_PKG / "pyproject.toml")
