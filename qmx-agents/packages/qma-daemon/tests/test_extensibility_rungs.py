"""Story 32.3 — daemon binds rungs 1–3; rung 4 stays GAP-0081."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.plugins import PluginContext
from qma.core.ports.extensibility import PUBLIC_EXTENSION_RUNGS
from qma.core.refusals import (
    ExtensionSurfaceRefused,
    NoCodeAuthoringRefused,
    UiContributionDeferred,
)
from qma.daemon.plugins import (
    EXCLUDED_CONTRIBUTION_POINTS,
    DaemonPluginContext,
    ExtensionSurface,
    PluginLoader,
    plugin_context_mints_ui_view,
)
from qmf.core import is_ok, is_refusal


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "research-corpus",
        "version": "0.1.0",
        "qma_api": ">=0.1.0,<1.0.0",
        "desk": "research",
        "entrypoint": "research_corpus.activate",
        "dependencies": [],
        "contributions": [{"point": "tool", "local_id": "search"}],
        "permissions": [],
        "migrations": [],
    }
    base.update(overrides)
    return base


def _activate(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("search", {"name": "search"})


def test_daemon_enumerates_rungs_one_through_three() -> None:
    surface = ExtensionSurface()
    assert surface.public_rungs() == PUBLIC_EXTENSION_RUNGS
    public = surface.enumerate_public()
    assert tuple(spec.number for spec in public) == (1, 2, 3)
    for number in PUBLIC_EXTENSION_RUNGS:
        admitted = surface.admit(number)
        assert is_ok(admitted)
        assert admitted.value.binds is True
    assert surface.plugin_vocabulary_is_qma_scoped() is True


def test_ui_widget_registration_is_gap_0081_and_context_has_no_ui_view() -> None:
    surface = ExtensionSurface()
    ctx = DaemonPluginContext("research-corpus")
    assert plugin_context_mints_ui_view(ctx) is False
    assert surface.context_has_ui_view(ctx) is False
    assert surface.ui_view_minted() is False
    assert not hasattr(ctx, "register_ui_view")
    refused = surface.register_ui_widget(plugin_id="research-corpus", local_id="panel")
    assert is_refusal(refused)
    assert UiContributionDeferred.matches(refused)
    assert refused.context["gap"] == "GAP-0081"
    assert EXCLUDED_CONTRIBUTION_POINTS["ui_view"] == "GAP-0081"
    rung4 = surface.admit(4)
    assert is_refusal(rung4)
    assert UiContributionDeferred.matches(rung4)


def test_loader_refuses_ui_view_as_named_gap_0081_variant() -> None:
    loader = PluginLoader()
    refused = loader.install(
        _manifest(contributions=[{"point": "ui_view", "local_id": "panel"}]),
        activator=_activate,
    )
    assert is_refusal(refused)
    assert UiContributionDeferred.matches(refused)
    assert refused.context["contribution_point"] == "ui_view"
    assert refused.context["gap"] == "GAP-0081"
    assert refused.context["ui_view_minted"] is False


def test_no_code_and_qmb_plugin_and_roster_kind_are_refused() -> None:
    surface = ExtensionSurface()
    no_code = surface.admit_no_code(".qml")
    assert is_refusal(no_code)
    assert NoCodeAuthoringRefused.matches(no_code)
    assert no_code.context["logic_path"] == "ordinary_python"
    presented = surface.admit("random_condition_editor")
    assert is_refusal(presented)
    assert NoCodeAuthoringRefused.matches(presented)
    qmb = surface.label_qmb_module("qmb.doors.cli")
    assert is_refusal(qmb)
    assert ExtensionSurfaceRefused.matches(qmb)
    assert surface.work_environment_roster_kind() is None
    roster = surface.mint_work_environment_roster_kind()
    assert is_refusal(roster)
    assert roster.context["reason"] == "work_environment_roster_kind"


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "extensibility_rungs_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
