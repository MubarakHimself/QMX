"""L27 reference usage: validate a PluginManifest and activate scoped contributions."""

from __future__ import annotations

from qma.core.plugins import PluginContext, parse_plugin_manifest
from qma.core.ports.memory import MemoryCandidate
from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.plugins import LOAD_PHASES, DaemonPluginContext, PluginLoader
from qmf.core import Ok, Result, is_ok, is_refusal


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


def _activate(ctx: PluginContext) -> None:
    # Contribution types come from qma-core; the daemon supplies the context.
    assert isinstance(ctx, DaemonPluginContext)
    ctx.register_memory_provider("research", _MemoryStub())
    ctx.register_tool("search", {"name": "search"})
    ctx.declare_credential_ref("models", "cred://models/openai")


def main() -> None:
    raw = {
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
    manifest = parse_plugin_manifest(raw)
    assert manifest.id == "research-corpus"
    assert manifest.dependencies == ()

    loader = PluginLoader()
    assert loader.file_watcher_enabled is False
    assert loader.load_phases == LOAD_PHASES

    machine = loader.install(raw, activator=_activate, principal=PrincipalClass.MACHINE)
    assert is_refusal(machine)

    installed = loader.install(raw, activator=_activate, principal=PrincipalClass.OPERATOR)
    assert is_ok(installed)
    loaded = installed.value
    assert loaded.phases_completed == LOAD_PHASES
    assert str(loaded.context.credential_ref("models")) == "cred://models/openai"
    assert ("tool", "research-corpus:search") in loaded.context.snapshot()["multis"]

    unloaded = loader.unload("research-corpus")
    assert unloaded >= 1
    assert loader.get("research-corpus") is None


if __name__ == "__main__":
    main()
