"""Daemon binding of the public extension ladder (DEC-0280; FR-W37).

Rungs 1–3 bind. Rung 4 / ``ui_view`` is refused as GAP-0081. The daemon
plugin context does not grow a UI contribution method. Work-environment
roster kind is not minted here.
"""

from __future__ import annotations

from collections.abc import Mapping

from qma.core.plugins.context import PluginContext
from qma.core.ports.extensibility import (
    DEFERRED_EXTENSION_RUNG,
    PUBLIC_EXTENSION_RUNGS,
    WORK_ENVIRONMENT_ROSTER_KIND,
    ExtensionRung,
    ExtensionRungSpec,
    admit_extension_rung,
    enumerate_public_extension_rungs,
    mint_work_environment_roster_kind,
    plugin_vocabulary_is_qma_scoped,
    refuse_no_code_authoring,
    refuse_qmb_plugin_label,
    register_ui_widget_contribution,
    ui_view_contribution_point_minted,
)
from qma.core.refusals import (
    ExtensionSurfaceRefused,
    NoCodeAuthoringRefused,
    UiContributionDeferred,
)
from qma.daemon.plugins.context import DaemonPluginContext
from qmf.core import Result

__all__ = [
    "ExtensionSurface",
    "plugin_context_mints_ui_view",
]


def plugin_context_mints_ui_view(ctx: object) -> bool:
    """True only if a UI contribution method exists — it must not."""
    return hasattr(ctx, "register_ui_view")


class ExtensionSurface:
    """Daemon-facing ladder. Definitions live in ``qma-core``."""

    def enumerate_public(self) -> tuple[ExtensionRungSpec, ...]:
        return enumerate_public_extension_rungs()

    def admit(self, rung: ExtensionRung | int | str) -> Result[ExtensionRungSpec]:
        return admit_extension_rung(rung)

    def register_ui_widget(
        self,
        *,
        plugin_id: str,
        local_id: str,
        view: Mapping[str, object] | None = None,
    ) -> UiContributionDeferred:
        _ = view
        return register_ui_widget_contribution(plugin_id=plugin_id, local_id=local_id)

    def admit_no_code(self, request: object) -> NoCodeAuthoringRefused:
        return refuse_no_code_authoring(request)

    def label_qmb_module(self, module: object) -> Result[str]:
        return refuse_qmb_plugin_label(module)

    def mint_work_environment_roster_kind(self) -> ExtensionSurfaceRefused:
        return mint_work_environment_roster_kind()

    def context_has_ui_view(self, ctx: PluginContext | DaemonPluginContext) -> bool:
        return plugin_context_mints_ui_view(ctx)

    def ui_view_minted(self) -> bool:
        return ui_view_contribution_point_minted()

    def plugin_vocabulary_is_qma_scoped(self) -> bool:
        return plugin_vocabulary_is_qma_scoped()

    def work_environment_roster_kind(self) -> None:
        return WORK_ENVIRONMENT_ROSTER_KIND

    def deferred_rung(self) -> int:
        return DEFERRED_EXTENSION_RUNG

    def public_rungs(self) -> tuple[int, int, int]:
        return PUBLIC_EXTENSION_RUNGS
