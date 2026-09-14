"""L27 reference usage: extensibility rungs 1–3 bind; rung 4 is GAP-0081."""

from __future__ import annotations

from qma.core.ports.extensibility import PUBLIC_EXTENSION_RUNGS, RUNG_1_CONFIGURABLE_FLAG
from qma.core.refusals import (
    ExtensionSurfaceRefused,
    NoCodeAuthoringRefused,
    UiContributionDeferred,
)
from qma.daemon.plugins import DaemonPluginContext, ExtensionSurface, PluginLoader
from qmf.core import is_ok, is_refusal


def _activate(ctx: object) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_tool("search", {"name": "search"})


def main() -> None:
    surface = ExtensionSurface()
    assert surface.public_rungs() == PUBLIC_EXTENSION_RUNGS
    rungs = surface.enumerate_public()
    assert rungs[0].to_payload()["flag"] == RUNG_1_CONFIGURABLE_FLAG
    assert is_ok(surface.admit(1))
    assert is_ok(surface.admit(2))
    assert is_ok(surface.admit(3))

    rung4 = surface.admit(4)
    assert is_refusal(rung4)
    assert UiContributionDeferred.matches(rung4)
    widget = surface.register_ui_widget(plugin_id="research-corpus", local_id="panel")
    assert is_refusal(widget)
    assert UiContributionDeferred.matches(widget)
    ctx = DaemonPluginContext("research-corpus")
    assert surface.context_has_ui_view(ctx) is False

    no_code = surface.admit_no_code("qml_revival")
    assert is_refusal(no_code)
    assert NoCodeAuthoringRefused.matches(no_code)
    qmb = surface.label_qmb_module("qmb")
    assert is_refusal(qmb)
    assert ExtensionSurfaceRefused.matches(qmb)
    roster = surface.mint_work_environment_roster_kind()
    assert is_refusal(roster)
    assert ExtensionSurfaceRefused.matches(roster)

    loader = PluginLoader()
    refused = loader.install(
        {
            "id": "research-corpus",
            "version": "0.1.0",
            "qma_api": ">=0.1.0,<1.0.0",
            "desk": "research",
            "entrypoint": "research_corpus.activate",
            "contributions": [{"point": "ui_view", "local_id": "panel"}],
        },
        activator=_activate,
    )
    assert is_refusal(refused)
    assert UiContributionDeferred.matches(refused)


if __name__ == "__main__":
    main()
