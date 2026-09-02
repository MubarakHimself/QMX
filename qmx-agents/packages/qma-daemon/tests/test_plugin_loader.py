"""Story 48.1 — Validate PluginManifest and activate scoped contributions (FR-Q68)."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from qma.core.plugins import ManifestError, PluginContext, parse_plugin_manifest
from qma.core.ports.memory import MemoryCandidate
from qma.core.ports.model import DeploymentRecord
from qma.core.vocabulary.enums import ModelClass, PrincipalClass
from qma.daemon.plugins import (
    FILE_WATCHER_ENABLED,
    LOAD_PHASES,
    DaemonPluginContext,
    PluginLoader,
)
from qma.daemon.plugins.loader import check_qma_api_compatible
from qmf.core import Ok, Result, is_ok, is_refusal

LOADER_SRC = (
    Path(__file__).resolve().parents[1] / "src" / "qma" / "daemon" / "plugins" / "loader.py"
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


def _activate_research(ctx: PluginContext) -> None:
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_memory_provider("research", _MemoryStub())
    ctx.register_tool("search", {"name": "search"})
    ctx.declare_credential_ref("models", "cred://models/openai")


def test_load_phases_order_and_no_file_watcher() -> None:
    assert LOAD_PHASES == (
        "manifest_validation",
        "qma_api_compatibility",
        "permissions",
        "dependencies",
        "migrations",
        "topological_activation",
        "publication",
    )
    assert FILE_WATCHER_ENABLED is False
    loader = PluginLoader()
    assert loader.file_watcher_enabled is False
    text = LOADER_SRC.read_text(encoding="utf-8")
    assert "watchdog" not in text.casefold()
    assert "FileSystemEvent" not in text
    assert "add_watcher" not in text


def test_install_activates_scoped_contributions_and_publishes() -> None:
    loader = PluginLoader(permission_allowlist=frozenset())
    result = loader.install(_manifest(), activator=_activate_research)
    assert is_ok(result)
    loaded = result.value
    assert loaded.phases_completed == LOAD_PHASES
    snap = loaded.context.snapshot()
    assert ("MemoryProvider", "research") in snap["singletons"]
    assert ("tool", "research-corpus:search") in snap["multis"]
    assert str(loaded.context.credential_ref("models")) == "cred://models/openai"
    assert not hasattr(loaded.context, "secret")
    published = {row.qualified_id or row.point for row in loaded.published}
    assert "MemoryProvider" in published
    assert "research-corpus:search" in published


def test_unload_closes_lifo_and_removes_all_contributions() -> None:
    loader = PluginLoader()
    order: list[str] = []

    def activate(ctx: PluginContext) -> None:
        assert isinstance(ctx, DaemonPluginContext)
        ctx.register_tool("a", {"name": "a"})
        ctx.register_tool("b", {"name": "b"})

        def mark_b() -> None:
            order.append("b")

        def mark_a() -> None:
            order.append("a")

        # Markers sit above the registration disposers; LIFO closes markers first.
        ctx.exit_stack.push(mark_b)
        ctx.exit_stack.push(mark_a)

    assert is_ok(
        loader.install(
            _manifest(
                contributions=[
                    {"point": "tool", "local_id": "a"},
                    {"point": "tool", "local_id": "b"},
                ]
            ),
            activator=activate,
        )
    )
    assert loader.get("research-corpus") is not None
    count = loader.unload("research-corpus")
    assert count >= 2
    assert order == ["a", "b"]
    assert loader.get("research-corpus") is None
    assert loader.published_contributions() == ()


def test_unique_plugin_id_and_duplicate_singleton_refused() -> None:
    loader = PluginLoader()
    assert is_ok(loader.install(_manifest(), activator=_activate_research))
    again = loader.install(_manifest(), activator=_activate_research)
    assert is_refusal(again)
    assert again.context["field"] == "id"

    other = PluginLoader()
    assert is_ok(other.install(_manifest(), activator=_activate_research))

    def collide(ctx: PluginContext) -> None:
        assert isinstance(ctx, DaemonPluginContext)
        ctx.register_memory_provider("research", _MemoryStub())

    collided = other.install(
        _manifest(
            id="research-memory",
            entrypoint="research_memory.activate",
            contributions=[{"point": "MemoryProvider", "scope_key": "desk"}],
        ),
        activator=collide,
    )
    assert is_refusal(collided)
    assert "MemoryProvider" in str(collided.context["reason"])


def test_machine_principal_refused_and_operator_reload_explicit() -> None:
    loader = PluginLoader()
    machine = loader.install(
        _manifest(),
        activator=_activate_research,
        principal=PrincipalClass.MACHINE,
    )
    assert is_refusal(machine)
    assert machine.context.get("command") == "plugin.install"

    assert is_ok(loader.install(_manifest(), activator=_activate_research))
    reloaded = loader.reload(_manifest(), activator=_activate_research)
    assert is_ok(reloaded)
    assert reloaded.value.manifest.id == "research-corpus"


def test_qma_api_incompatible_and_permissions_refused() -> None:
    check_qma_api_compatible(">=0.1.0,<1.0.0", "0.1.0")
    with pytest.raises(Exception, match="incompatible"):
        check_qma_api_compatible(">=1.0.0,<2.0.0", "0.1.0")

    loader = PluginLoader(permission_allowlist=frozenset({"read"}))
    refused = loader.install(
        _manifest(permissions=["write_ledger"]),
        activator=_activate_research,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "plugin.permissions"


def test_missing_dependency_refused() -> None:
    loader = PluginLoader()
    refused = loader.install(
        _manifest(dependencies=["analysis-backtest"]),
        activator=_activate_research,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "dependencies"


def test_money_path_act_and_openrouter_refused_at_registration() -> None:
    loader = PluginLoader()

    def money(ctx: PluginContext) -> None:
        ctx.register_tool("order", {"name": "submit_order", "acts": ("submit_order",)})

    refused = loader.install(
        _manifest(contributions=[{"point": "tool", "local_id": "order"}]),
        activator=money,
    )
    assert is_refusal(refused)
    assert "money-path" in str(refused.context["reason"])

    def openrouter(ctx: PluginContext) -> None:
        ctx.register_model_deployment(
            "route",
            DeploymentRecord(
                deployment_id="research-corpus:route",
                model_class=ModelClass.WORKHORSE_GENERAL,
                adapter="openrouter",
                context_tokens=8_000,
            ),
        )

    refused_or = loader.install(
        _manifest(contributions=[{"point": "model_deployment", "local_id": "route"}]),
        activator=openrouter,
    )
    assert is_refusal(refused_or)
    assert "OpenRouter" in str(refused_or.context["reason"])


def test_operator_assigned_fields_refused_at_load() -> None:
    with pytest.raises(ManifestError, match="model_family"):
        parse_plugin_manifest(_manifest(model_family="opus"))
    with pytest.raises(ManifestError, match="tool_adapter_binding"):
        parse_plugin_manifest(
            _manifest(tool_adapter_binding={"desk": "research", "role": "researcher"})
        )


def test_contribution_types_imported_from_core_not_daemon() -> None:
    import qma.core.plugins as core_plugins

    assert core_plugins.PluginManifest.__module__.startswith("qma.core")
    assert core_plugins.PluginContext.__module__.startswith("qma.core")
    assert DaemonPluginContext.__module__.startswith("qma.daemon")
    # Plugin authors receive the protocol, never the daemon class, from core.
    assert inspect.isclass(core_plugins.PluginContext) or hasattr(
        core_plugins.PluginContext, "__protocol_attrs__"
    )


def test_empty_collections_never_null_on_manifest() -> None:
    manifest = parse_plugin_manifest(
        {
            "id": "dev-factory",
            "version": "0.1.0",
            "qma_api": "0.1.0",
            "desk": "dev",
            "entrypoint": "dev_factory.activate",
        }
    )
    assert manifest.dependencies == ()
    assert manifest.contributions == ()
    assert manifest.permissions == ()
    assert manifest.migrations == ()
    assert manifest.rollback is None


def test_reference_usage_example_runs() -> None:
    import runpy

    path = Path(__file__).resolve().parents[1] / "examples" / "plugin_loader_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
