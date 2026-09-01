"""Story 40.3 — daemon implements PluginContext; core stays definitions-only."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from qma.core.plugins import PluginContext, build_hook_event, build_hook_result
from qma.core.plugins.hooks import HookSource
from qma.core.ports.handles import EvidenceHandle
from qma.core.vocabulary.enums import HookResultDecision
from qma.daemon.plugins import DaemonPluginContext


class _MemoryStub:
    """Structural MemoryProvider stand-in for registration tests."""


class _CompilerStub:
    """Structural ContextCompiler stand-in."""

    def compile_context(self, handles: Sequence[EvidenceHandle]) -> Mapping[str, object]:
        _ = handles
        return {"handles": [], "contents_in_context": False}


def test_daemon_context_conforms_to_plugin_context_protocol() -> None:
    ctx = DaemonPluginContext("research-corpus")
    assert isinstance(ctx, PluginContext)
    ctx.declare_credential_ref("models", "cred://models/openai")
    ref = ctx.credential_ref("models")
    assert str(ref) == "cred://models/openai"
    # No resolved secret attribute exists on the context.
    assert not hasattr(ctx, "secret")
    assert not hasattr(ctx, "resolved_secret")
    assert not hasattr(ctx, "password")


def test_singleton_and_multi_registration_with_disposers() -> None:
    ctx = DaemonPluginContext("research-corpus")
    dispose_mem = ctx.register_memory_provider("research", _MemoryStub())
    dispose_tool = ctx.register_tool("search", {"name": "search"})
    snap = ctx.snapshot()
    assert ("MemoryProvider", "research") in snap["singletons"]
    assert ("tool", "research-corpus:search") in snap["multis"]

    dispose_tool()
    snap = ctx.snapshot()
    assert ("tool", "research-corpus:search") not in snap["multis"]
    dispose_mem()
    snap = ctx.snapshot()
    assert ("MemoryProvider", "research") not in snap["singletons"]


def test_context_compiler_replaceable_default_binding() -> None:
    ctx = DaemonPluginContext("analysis-backtest")
    dispose = ctx.register_context_compiler(_CompilerStub())
    assert ctx.snapshot()["context_compiler_bound"] is True
    dispose()
    assert ctx.snapshot()["context_compiler_bound"] is False


def test_hook_registration_callable() -> None:
    ctx = DaemonPluginContext("dev-factory")

    def handler(event: Any) -> Any:
        _ = event
        return build_hook_result(HookResultDecision.OBSERVE, reason="seen")

    dispose = ctx.register_hook("lint", handler)
    event = build_hook_event("before_tool", source=HookSource.PLUGIN)
    registered = ctx.snapshot()["multis"][("hook", "dev-factory:lint")]
    result = registered(event)
    assert result.decision is HookResultDecision.OBSERVE
    dispose()
