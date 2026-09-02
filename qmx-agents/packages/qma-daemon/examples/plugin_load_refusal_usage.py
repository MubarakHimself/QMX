"""L27 reference usage: load refusal preserves daemon continuity (FR-Q70)."""

from __future__ import annotations

from qma.core.plugins import PluginContext
from qma.daemon.plugins import (
    CUT_PLUGIN_SURFACES,
    DAEMON_PLUGIN_RENDERS,
    EXCLUDED_CONTRIBUTION_POINTS,
    FIRST_PARTY_TRUST_MODE,
    GAP_0077_STATUS,
    GAP_0081_STATUS,
    PEER_INTEGRATION_BOUNDARY,
    DaemonContinuitySnapshot,
    DaemonPluginContext,
    PluginLoader,
    PluginStartupAbort,
    RequiredSingletonBinding,
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


def main() -> None:
    continuity = DaemonContinuitySnapshot(
        daemon_running=True,
        dispatch_leases=("dispatch:task-1",),
        environment_leases=("env:docker:slot-1",),
        running_tasks=("task-1",),
        pending_evidence_appends=("evidence:pending-1",),
    )
    loader = PluginLoader(continuity=continuity)

    assert FIRST_PARTY_TRUST_MODE == "first_party_only"
    assert "marketplace" in CUT_PLUGIN_SURFACES
    assert PEER_INTEGRATION_BOUNDARY == "qma_wire_only"
    assert DAEMON_PLUGIN_RENDERS is False
    assert GAP_0077_STATUS == "deferred"
    assert GAP_0081_STATUS == "deferred"
    assert EXCLUDED_CONTRIBUTION_POINTS["threading_node"] == "GAP-0077"
    assert EXCLUDED_CONTRIBUTION_POINTS["ui_view"] == "GAP-0081"

    # Runtime install failure → typed refusal; continuity markers intact.
    refused = loader.install(
        _manifest(dependencies=["analysis-backtest"]),
        activator=_activate,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "dependencies"
    assert refused.context["startup"] is False
    assert refused.context["continuity_intact"] is True
    assert refused.context["dispatch_leases"] == continuity.dispatch_leases
    assert refused.context["running_tasks"] == continuity.running_tasks
    assert refused.context["pending_evidence_appends"] == continuity.pending_evidence_appends

    # Startup surface aborts naming the offending unit — never silent pending.
    abort: PluginStartupAbort | None = None
    try:
        loader.startup_activate_roster(
            [_manifest(dependencies=["analysis-backtest"])],
            activators={"research-corpus": _activate},
            required_singletons=(
                RequiredSingletonBinding(
                    port="MemoryProvider",
                    key="research",
                    requiring_unit="role:researcher",
                ),
            ),
        )
    except PluginStartupAbort as exc:
        abort = exc
    assert abort is not None
    assert abort.field in {"dependencies", "required_singleton"}
    assert abort.named_fields()["startup"] is True

    # Happy path still loads after a refused command.
    ok = loader.install(_manifest(), activator=_activate)
    assert is_ok(ok)
    assert loader.get("research-corpus") is not None
    loader.unload("research-corpus")


if __name__ == "__main__":
    main()
