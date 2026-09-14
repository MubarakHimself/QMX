"""Story 32.3 — extensibility rungs 1–3 bind; rung 4 stays GAP-0081."""

from __future__ import annotations

from pathlib import Path

from qma.core.plugins import DESK_PLUGIN_PACK_IDS, PluginContext
from qma.core.plugins.context import PluginContext as PluginContextProtocol
from qma.core.ports.cardinality import MULTI_CONTRIBUTION_POINTS, RETIRED_CONTRIBUTION_POINTS
from qma.core.ports.extensibility import (
    DEFERRED_EXTENSION_RUNG,
    GAP_0081_UI_CONTRIBUTION,
    LOGIC_PATH_RUNG,
    NO_CODE_AUTHORING_REQUESTS,
    PLUGIN_VOCABULARY_SCOPE,
    PUBLIC_EXTENSION_RUNGS,
    QMA_UI_CONTRACT_PACKAGE,
    QMA_UI_CONTRACT_STATUS,
    QMB_MODULE_IS_PLUGIN,
    RUNG_1_CONFIGURABLE_FLAG,
    RUNG_1_LAW,
    RUNG_3_CONTRIBUTIONS,
    UI_VIEW_CONTRIBUTION_POINT,
    WORK_ENVIRONMENT_ROSTER,
    WORK_ENVIRONMENT_ROSTER_KIND,
    ExtensionRung,
    admit_extension_rung,
    enumerate_public_extension_rungs,
    is_no_code_authoring_request,
    is_public_extension_rung,
    is_ui_contribution_point,
    logic_path_is_ordinary_python,
    mint_work_environment_roster_kind,
    parse_extension_rung,
    plugin_vocabulary_is_qma_scoped,
    refuse_no_code_authoring,
    refuse_qmb_plugin_label,
    refuse_ui_contribution,
    register_ui_widget_contribution,
    ui_view_contribution_point_minted,
)
from qma.core.refusals import (
    ExtensionSurfaceRefused,
    NoCodeAuthoringRefused,
    UiContributionDeferred,
)
from qma.core.vocabulary.enums import VariableEditability
from qmf.core import is_ok, is_refusal

AGENTS_ROOT = Path(__file__).resolve().parents[3]
UI_CONTRACT_ROOT = AGENTS_ROOT / "packages" / "qma-ui-contract"
WORKSPACE_TOML = AGENTS_ROOT / "pyproject.toml"


def test_public_surface_is_exactly_three_rungs() -> None:
    assert PUBLIC_EXTENSION_RUNGS == (1, 2, 3)
    rungs = enumerate_public_extension_rungs()
    assert tuple(spec.number for spec in rungs) == PUBLIC_EXTENSION_RUNGS
    assert all(spec.binds for spec in rungs)
    assert DEFERRED_EXTENSION_RUNG not in PUBLIC_EXTENSION_RUNGS
    assert is_public_extension_rung(4) is False

    first, second, third = rungs
    assert first.name is ExtensionRung.CONFIG_VARIABLES
    assert first.surface == "ui-editable config variables on templates"
    assert first.to_payload()["flag"] == RUNG_1_CONFIGURABLE_FLAG
    assert first.to_payload()["law"] == RUNG_1_LAW
    assert first.to_payload()["configurable"] is True
    assert first.to_payload()["editability"] == VariableEditability.UI_EDITABLE.value

    assert second.name is ExtensionRung.ORDINARY_PYTHON
    assert second.surface == "ordinary Python logic plus QMB ports/adapters"
    assert second.to_payload()["logic"] == "ordinary_python"
    assert second.to_payload()["host"] == ("qmb_ports", "qmb_adapters")

    assert third.name is ExtensionRung.QMA_PACKS
    assert third.surface == "QMA plugins, skills, graph templates, and desk packs"
    assert third.to_payload()["contributions"] == list(RUNG_3_CONTRIBUTIONS)
    assert third.to_payload()["plugin_scope"] == PLUGIN_VOCABULARY_SCOPE
    assert third.to_payload()["desk_packs"] == list(DESK_PLUGIN_PACK_IDS)


def test_rungs_one_through_three_admit() -> None:
    for number in PUBLIC_EXTENSION_RUNGS:
        admitted = admit_extension_rung(number)
        assert is_ok(admitted)
        assert admitted.value.number == number
        assert admitted.value.binds is True
    named = admit_extension_rung("ordinary_python")
    assert is_ok(named)
    assert named.value.number == 2


def test_rung_four_is_gap_0081_and_does_not_mint_ui_view() -> None:
    assert DEFERRED_EXTENSION_RUNG == 4
    assert GAP_0081_UI_CONTRIBUTION["gap"] == "GAP-0081"
    assert GAP_0081_UI_CONTRIBUTION["status"] == "deferred"
    assert GAP_0081_UI_CONTRIBUTION["package"] == QMA_UI_CONTRACT_PACKAGE
    assert QMA_UI_CONTRACT_STATUS == "stub"
    refused = admit_extension_rung(4)
    assert is_refusal(refused)
    assert UiContributionDeferred.matches(refused)
    assert refused.context["gap"] == "GAP-0081"
    assert refused.context["gap_status"] == "deferred"
    assert refused.context["ui_view_minted"] is False
    assert ui_view_contribution_point_minted() is False
    assert UI_VIEW_CONTRIBUTION_POINT in RETIRED_CONTRIBUTION_POINTS
    assert UI_VIEW_CONTRIBUTION_POINT not in MULTI_CONTRIBUTION_POINTS
    assert "ui_view" not in PluginContextProtocol.__dict__
    assert not hasattr(PluginContext, "register_ui_view")


def test_ui_widget_contribution_is_refused_as_gap_0081() -> None:
    widget = register_ui_widget_contribution(
        plugin_id="research-corpus",
        local_id="panel",
        point="ui_view",
    )
    assert is_refusal(widget)
    assert UiContributionDeferred.matches(widget)
    assert widget.context["contribution_point"] == "ui_view"
    assert widget.context["plugin_id"] == "research-corpus"
    assert widget.context["package"] == "qma-ui-contract"
    for point in ("ui_view", "ui_package", "ui_extension", "ui_widget"):
        assert is_ui_contribution_point(point)
        refused = refuse_ui_contribution(point)
        assert UiContributionDeferred.matches(refused)
        assert refused.context["gap"] == "GAP-0081"


def test_qma_ui_contract_remains_a_stub() -> None:
    assert (UI_CONTRACT_ROOT / "STUB.md").is_file()
    assert not (UI_CONTRACT_ROOT / "pyproject.toml").exists()
    assert not (UI_CONTRACT_ROOT / "src").exists()
    text = WORKSPACE_TOML.read_text(encoding="utf-8")
    assert 'members = ["packages/qma-core", "packages/qma-wire", "packages/qma-daemon"]' in text
    assert "qma-ui-contract" in text
    assert "GAP-0081" in text


def test_no_code_authoring_is_refused_ordinary_python_remains_logic_path() -> None:
    assert LOGIC_PATH_RUNG == 2
    assert logic_path_is_ordinary_python() is True
    requests = (
        "sq_building_block_dsl",
        "SQ-style",
        "building-block-dsl",
        "RandomCondition",
        "random_condition_editor",
        ".qml",
        "qml_revival",
    )
    for request in requests:
        assert is_no_code_authoring_request(request)
        refused = refuse_no_code_authoring(request)
        assert is_refusal(refused)
        assert NoCodeAuthoringRefused.matches(refused)
        assert refused.context["logic_path"] == "ordinary_python"
        assert refused.context["logic_rung"] == 2
    presented = admit_extension_rung("qml_revival")
    assert is_refusal(presented)
    logic = admit_extension_rung(2)
    assert is_ok(logic)
    assert logic.value.name is ExtensionRung.ORDINARY_PYTHON


def test_plugin_vocabulary_stays_qma_scoped_qmb_module_is_not_a_plugin() -> None:
    assert plugin_vocabulary_is_qma_scoped() is True
    assert PLUGIN_VOCABULARY_SCOPE == "qma"
    assert QMB_MODULE_IS_PLUGIN is False
    rung3 = admit_extension_rung(3)
    assert is_ok(rung3)
    assert rung3.value.to_payload()["plugin_scope"] == "qma"
    assert rung3.value.to_payload()["qmb_module_is_plugin"] is False
    for module in ("qmb", "qmb.doors", "qmb.doors.cli", "qmb.orchestrator"):
        refused = refuse_qmb_plugin_label(module)
        assert is_refusal(refused)
        assert ExtensionSurfaceRefused.matches(refused)
        assert refused.context["reason"] == "qmb_plugin_vocabulary"
        assert refused.context["plugin_scope"] == "qma"
    other = refuse_qmb_plugin_label("analysis-backtest")
    assert is_ok(other)


def test_work_environment_roster_is_not_minted() -> None:
    assert WORK_ENVIRONMENT_ROSTER_KIND is None
    assert WORK_ENVIRONMENT_ROSTER["kind"] is None
    assert WORK_ENVIRONMENT_ROSTER["status"] == "later_ui_alias"
    assert WORK_ENVIRONMENT_ROSTER["over"] == "fingerprints"
    assert WORK_ENVIRONMENT_ROSTER["minted"] is False
    refused = mint_work_environment_roster_kind()
    assert is_refusal(refused)
    assert ExtensionSurfaceRefused.matches(refused)
    assert refused.context["reason"] == "work_environment_roster_kind"
    assert refused.context["kind"] is None
    assert refused.context["nfr"] == "NFR-W06 A2"
    assert refused.context["fr"] == "FR-W16"


def test_undeclared_rung_and_parse() -> None:
    parsed = parse_extension_rung("rung_1")
    assert is_ok(parsed)
    assert parsed.value.number == 1
    unknown = admit_extension_rung(5)
    assert is_refusal(unknown)
    assert ExtensionSurfaceRefused.matches(unknown)
    assert unknown.context["reason"] == "undeclared_rung"
    assert is_refusal(parse_extension_rung("not_a_rung"))
    assert NO_CODE_AUTHORING_REQUESTS
