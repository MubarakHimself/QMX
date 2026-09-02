"""Story 48.3 — Preserve daemon continuity across plugin load refusal (FR-Q70)."""

from __future__ import annotations

from pathlib import Path

import pytest
from qma.core.plugins import PluginContext
from qma.core.ports.memory import MemoryCandidate
from qma.daemon.plugins import (
    CUT_PLUGIN_SURFACES,
    DAEMON_PLUGIN_RENDERS,
    EXCLUDED_CONTRIBUTION_POINTS,
    FIRST_PARTY_TRUST_MODE,
    GAP_0077_STATUS,
    GAP_0081_STATUS,
    PEER_INTEGRATION_BOUNDARY,
    SHARED_PROCESS_MEMORY_AS_INTEGRATION,
    ContinuityLedger,
    DaemonContinuitySnapshot,
    DaemonPluginContext,
    PluginLoader,
    PluginStartupAbort,
    RequiredSingletonBinding,
    assert_peer_integration_boundary,
    assess_plugin_trust,
    excluded_contribution_refusal,
)
from qmf.core import Ok, Result, is_ok, is_refusal

LOADER_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "plugins" / "loader.py"
)
REFUSAL_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "plugins" / "load_refusal.py"
)


class _MemoryStub:
    def propose(self, candidate: MemoryCandidate) -> Result[MemoryCandidate]:
        return Ok(candidate)

    def admit(self, candidate: MemoryCandidate) -> Result[MemoryCandidate]:
        return Ok(candidate)

    def recall(self, scope: str, token_budget: int) -> Result[tuple[MemoryCandidate, ...]]:
        _ = scope, token_budget
        return Ok(())

    def get(self, memory_id: str) -> Result[MemoryCandidate]:
        _ = memory_id
        raise KeyError(memory_id)

    def list(self, scope: str) -> Result[tuple[MemoryCandidate, ...]]:
        _ = scope
        return Ok(())

    def history(self, memory_id: str) -> Result[tuple[MemoryCandidate, ...]]:
        _ = memory_id
        return Ok(())

    def supersede(self, memory_id: str, successor: MemoryCandidate) -> Result[MemoryCandidate]:
        _ = memory_id
        return Ok(successor)

    def invalidate(self, memory_id: str) -> Result[MemoryCandidate]:
        _ = memory_id
        raise KeyError(memory_id)

    def expire(self, memory_id: str) -> Result[MemoryCandidate]:
        _ = memory_id
        raise KeyError(memory_id)

    def scopes(self) -> Result[tuple[str, ...]]:
        return Ok(())


def _manifest(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "id": "research-corpus",
        "version": "0.1.0",
        "qma_api": ">=0.1.0,<1.0.0",
        "desk": "research",
        "entrypoint": "research_corpus.activate",
        "dependencies": [],
        "contributions": [
            {"point": "MemoryProvider", "scope_key": "desk"},
            {"point": "tool", "local_id": "search"},
        ],
        "permissions": [],
        "migrations": [],
    }
    base.update(overrides)
    return base


def _activate(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_memory_provider("research", _MemoryStub())
    ctx.register_tool("search", {"name": "search"})


def _continuity() -> DaemonContinuitySnapshot:
    return DaemonContinuitySnapshot(
        daemon_running=True,
        dispatch_leases=("dispatch:task-1",),
        environment_leases=("env:docker:slot-1",),
        running_tasks=("task-1", "task-2"),
        pending_evidence_appends=("evidence:pending-1",),
    )


def test_startup_abort_names_missing_dependency() -> None:
    loader = PluginLoader(continuity=_continuity())
    with pytest.raises(PluginStartupAbort) as raised:
        loader.startup_activate_roster(
            [_manifest(dependencies=["analysis-backtest"])],
            activators={"research-corpus": _activate},
        )
    abort = raised.value
    assert abort.plugin_id == "research-corpus"
    assert abort.field == "dependencies"
    assert "analysis-backtest" in str(abort)
    named = abort.named_fields()
    assert named["startup"] is True
    assert named["field"] == "dependencies"


def test_startup_abort_names_duplicate_singleton_port_key_and_plugins() -> None:
    loader = PluginLoader(continuity=_continuity())
    assert is_ok(loader.install(_manifest(), activator=_activate))

    def collide(ctx: PluginContext) -> None:
        assert isinstance(ctx, DaemonPluginContext)
        ctx.register_memory_provider("research", _MemoryStub())

    with pytest.raises(PluginStartupAbort) as raised:
        loader.startup_activate_roster(
            [
                _manifest(
                    id="research-memory",
                    entrypoint="research_memory.activate",
                    contributions=[{"point": "MemoryProvider", "scope_key": "desk"}],
                )
            ],
            activators={"research-memory": collide},
        )
    abort = raised.value
    assert abort.port == "MemoryProvider"
    assert abort.key == "research"
    assert abort.conflicting_plugin_ids == ("research-corpus", "research-memory")
    assert abort.field == "MemoryProvider"


def test_startup_abort_on_required_unbound_singleton() -> None:
    loader = PluginLoader(continuity=_continuity())

    def activate_tools_only(ctx: PluginContext) -> None:
        assert isinstance(ctx, DaemonPluginContext)
        ctx.register_tool("search", {"name": "search"})

    with pytest.raises(PluginStartupAbort) as raised:
        loader.startup_activate_roster(
            [
                _manifest(
                    contributions=[
                        {"point": "tool", "local_id": "search"},
                    ]
                )
            ],
            activators={"research-corpus": activate_tools_only},
            required_singletons=(
                RequiredSingletonBinding(
                    port="MemoryProvider",
                    key="research",
                    requiring_unit="role:researcher",
                ),
            ),
        )
    abort = raised.value
    assert abort.field == "required_singleton"
    assert abort.port == "MemoryProvider"
    assert abort.key == "research"
    assert abort.plugin_id == "role:researcher"


def test_startup_abort_forward_only_without_confirmation(tmp_path: Path) -> None:
    source = tmp_path / "src"
    dest = tmp_path / "dst"
    source.mkdir()
    dest.mkdir()
    loader = PluginLoader(
        continuity=_continuity(),
        migration_source_root=source,
        migration_destination_root=dest,
    )

    def activate_search(ctx: PluginContext) -> None:
        assert isinstance(ctx, DaemonPluginContext)
        ctx.register_tool("search", {"name": "search"})

    with pytest.raises(PluginStartupAbort) as raised:
        loader.startup_activate_roster(
            [
                _manifest(
                    contributions=[{"point": "tool", "local_id": "search"}],
                    migrations=[{"id": "m1", "up": {"rewrite": True}}],
                    rollback="forward_only",
                )
            ],
            activators={"research-corpus": activate_search},
        )
    assert raised.value.field == "forward_only_confirmation"


def test_runtime_load_refusal_preserves_daemon_continuity() -> None:
    ledger = ContinuityLedger(
        daemon_running=True,
        dispatch_leases=["dispatch:task-1"],
        environment_leases=["env:docker:slot-1"],
        running_tasks=["task-1"],
        pending_evidence_appends=["evidence:pending-1"],
    )
    before = ledger.snapshot()
    loader = PluginLoader(continuity=before)

    order: list[str] = []

    def failing_activate(ctx: PluginContext) -> None:
        assert isinstance(ctx, DaemonPluginContext)
        ctx.register_tool("a", {"name": "a"})

        def mark() -> None:
            order.append("disposed")

        ctx.exit_stack.push(mark)
        raise RuntimeError("boom during activation")

    refused = loader.install(
        _manifest(contributions=[{"point": "tool", "local_id": "a"}]),
        activator=failing_activate,
    )
    assert is_refusal(refused)
    assert refused.context["startup"] is False
    assert refused.context["load_surface"] == "runtime_command"
    assert refused.context["continuity_intact"] is True
    assert refused.context["daemon_running"] is True
    assert refused.context["dispatch_leases"] == ("dispatch:task-1",)
    assert refused.context["environment_leases"] == ("env:docker:slot-1",)
    assert refused.context["running_tasks"] == ("task-1",)
    assert refused.context["pending_evidence_appends"] == ("evidence:pending-1",)
    assert loader.get("research-corpus") is None
    assert order == ["disposed"]
    after = ledger.snapshot()
    assert before.intact_after(after)


def test_runtime_duplicate_multi_names_conflicting_ids_and_keeps_leases() -> None:
    continuity = _continuity()
    loader = PluginLoader(continuity=continuity)

    def activate_search(ctx: PluginContext) -> None:
        assert isinstance(ctx, DaemonPluginContext)
        ctx.register_tool("search", {"name": "search"})

    assert is_ok(
        loader.install(
            _manifest(contributions=[{"point": "tool", "local_id": "search"}]),
            activator=activate_search,
        )
    )
    # Force a multi collision by claiming the same qualified id from another plugin.
    multi_owners = loader.debug_multi_owners_for_tests()
    multi_owners[("tool", "research-alt:search")] = "research-corpus"

    def collide(ctx: PluginContext) -> None:
        assert isinstance(ctx, DaemonPluginContext)
        ctx.register_tool("search", {"name": "search"})

    refused = loader.install(
        _manifest(
            id="research-alt",
            entrypoint="research_alt.activate",
            contributions=[{"point": "tool", "local_id": "search"}],
        ),
        activator=collide,
    )
    assert is_refusal(refused)
    assert refused.context["port"] == "tool"
    assert refused.context["key"] == "research-alt:search"
    assert refused.context["conflicting_plugin_ids"] == ("research-corpus", "research-alt")
    assert refused.context["continuity_intact"] is True
    assert refused.context["dispatch_leases"] == continuity.dispatch_leases
    assert loader.get("research-corpus") is not None
    assert loader.get("research-alt") is None


def test_failed_reload_keeps_live_scope_and_continuity() -> None:
    continuity = _continuity()
    loader = PluginLoader(continuity=continuity)

    def activate_search(ctx: PluginContext) -> None:
        assert isinstance(ctx, DaemonPluginContext)
        ctx.register_tool("search", {"name": "search"})

    assert is_ok(
        loader.install(
            _manifest(contributions=[{"point": "tool", "local_id": "search"}]),
            activator=activate_search,
        )
    )
    live = loader.get("research-corpus")
    assert live is not None

    def boom(_ctx: PluginContext) -> None:
        raise RuntimeError("reload boom")

    refused = loader.reload(
        _manifest(contributions=[{"point": "tool", "local_id": "search"}]),
        activator=boom,
    )
    assert is_refusal(refused)
    assert refused.context["continuity_intact"] is True
    assert refused.context["dispatch_leases"] == continuity.dispatch_leases
    kept = loader.get("research-corpus")
    assert kept is live
    assert any(
        row.qualified_id == "research-corpus:search" for row in loader.published_contributions()
    )


def test_first_party_only_refuses_cut_surfaces() -> None:
    assert FIRST_PARTY_TRUST_MODE == "first_party_only"
    assert "marketplace" in CUT_PLUGIN_SURFACES
    assert "trust_tier" in CUT_PLUGIN_SURFACES
    assert "capability_solver" in CUT_PLUGIN_SURFACES
    ok = assess_plugin_trust()
    assert is_ok(ok)
    refused = assess_plugin_trust(trust_mode="third_party")
    assert is_refusal(refused)
    loader = PluginLoader(continuity=_continuity())
    market = loader.install(
        _manifest(marketplace={"url": "https://example.invalid"}),
        activator=_activate,
    )
    assert is_refusal(market)
    assert market.context["field"] == "marketplace"


def test_peer_boundary_wire_only_daemon_does_not_render() -> None:
    assert PEER_INTEGRATION_BOUNDARY == "qma_wire_only"
    assert DAEMON_PLUGIN_RENDERS is False
    assert SHARED_PROCESS_MEMORY_AS_INTEGRATION is False
    assert is_ok(assert_peer_integration_boundary())
    refused = assert_peer_integration_boundary(peer_channel="shared_memory")
    assert is_refusal(refused)
    loader = PluginLoader(continuity=_continuity())
    render = loader.install(_manifest(daemon_renders=True), activator=_activate)
    assert is_refusal(render)
    assert render.context["field"] == "daemon_plugin_render"


def test_gap_0077_and_0081_remain_explicit_exclusions() -> None:
    assert GAP_0077_STATUS == "deferred"
    assert GAP_0081_STATUS == "deferred"
    assert EXCLUDED_CONTRIBUTION_POINTS["threading_node"] == "GAP-0077"
    assert EXCLUDED_CONTRIBUTION_POINTS["ui_view"] == "GAP-0081"
    assert "GAP-0077" in REFUSAL_SRC.read_text(encoding="utf-8")
    assert "GAP-0081" in REFUSAL_SRC.read_text(encoding="utf-8")
    # Gaps stay deferred — never marked answered/closed in this story.
    assert "answered" not in REFUSAL_SRC.read_text(encoding="utf-8").casefold()

    threading = excluded_contribution_refusal("threading_node")
    assert is_refusal(threading)
    assert threading.context["gap"] == "GAP-0077"
    assert threading.context["gap_status"] == "deferred"

    ui = excluded_contribution_refusal("ui_view")
    assert is_refusal(ui)
    assert ui.context["gap"] == "GAP-0081"

    loader = PluginLoader(continuity=_continuity())
    refused = loader.install(
        _manifest(contributions=[{"point": "threading_node", "local_id": "node"}]),
        activator=_activate,
    )
    assert is_refusal(refused)
    assert refused.context.get("gap") == "GAP-0077"


def test_missing_dependency_is_load_failure_not_pending() -> None:
    loader = PluginLoader(continuity=_continuity())
    refused = loader.install(
        _manifest(dependencies=["analysis-backtest"]),
        activator=_activate,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "dependencies"
    assert "pending" not in str(refused.context["reason"]).casefold()
    text = LOADER_SRC.read_text(encoding="utf-8")
    assert "never a silent pending state" in text or "Never returns a silent pending state" in text


def test_reference_usage_example_runs() -> None:
    import runpy

    path = Path(__file__).resolve().parents[1] / "examples" / "plugin_load_refusal_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
