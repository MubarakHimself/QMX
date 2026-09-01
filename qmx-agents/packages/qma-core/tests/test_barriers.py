"""Story 40.6 — default-deny parent surfaces and capability barrier constants."""

from __future__ import annotations

from pathlib import Path

import pytest
from qma.core.barriers import (
    CAPABILITY_LADDER,
    MONEY_PATH_DENY_LIST,
    PERMITTED_PARENT_SURFACES,
    PROHIBITED_RECORD_FAMILIES,
    QMA_CORE_ALLOWED_DEPS,
    QMA_DAEMON_ALLOWED_DEPS,
    QMA_WIRE_ALLOWED_DEPS,
    CapabilityError,
    CapabilityRung,
    DependencyBoundaryError,
    MoneyPathAct,
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
    parse_capability_rung,
    refuse_money_path_registration,
    refuse_unlisted_parent_surface,
)
from qma.core.refusals import ProhibitedMoneyPathTool

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


def test_dependency_boundary_rejects_extras() -> None:
    with pytest.raises(DependencyBoundaryError):
        # Point at wire pyproject while asserting core allowlist — extras expected.
        assert_package_deps_within("qma-core", WIRE_PKG / "pyproject.toml")
