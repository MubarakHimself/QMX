"""Story 40.3 — seven runtime ports and plugin contribution surface."""

from __future__ import annotations

from pathlib import Path

import pytest
from qma.core import plugins as plugins_api
from qma.core import ports as ports_api
from qma.core.plugins import (
    BoundaryError,
    HandleKind,
    HookResult,
    HookSource,
    ManifestError,
    PluginContext,
    PluginManifest,
    assert_core_definitions_only,
    assert_no_daemon_import,
    build_hook_event,
    build_hook_result,
    parse_credential_ref,
    parse_plugin_manifest,
)
from qma.core.ports import (
    MULTI_CONTRIBUTION_POINTS,
    PORT_CONTRACTS,
    RUNTIME_PORT_TYPES,
    Cardinality,
    ComputeProvider,
    ContextCompiler,
    ExecutionEnvironment,
    KnowledgeSource,
    MemoryProvider,
    ModelDeployment,
    PortError,
    ToolAdapter,
    has_qma_wire_schema,
    qualified_contribution_id,
    require_singleton_scope_key,
    validate_contribution_point,
    validate_multi_contribution_key,
)
from qma.core.vocabulary.enums import HookResultDecision
from qma.core.vocabulary.registry import VocabularyError

CORE_SRC = Path(__file__).resolve().parents[1] / "src" / "qma" / "core"
PLUGINS_ROOT = Path(__file__).resolve().parents[3] / "plugins"


def test_exactly_seven_runtime_ports_with_cardinality() -> None:
    assert len(PORT_CONTRACTS) == 7
    assert len(RUNTIME_PORT_TYPES) == 7
    names = [contract.name for contract in PORT_CONTRACTS]
    assert names == [
        "MemoryProvider",
        "ModelDeployment",
        "ExecutionEnvironment",
        "KnowledgeSource",
        "ToolAdapter",
        "ComputeProvider",
        "ContextCompiler",
    ]
    by_name = {c.name: c for c in PORT_CONTRACTS}
    assert by_name["MemoryProvider"].cardinality is Cardinality.SINGLETON
    assert by_name["MemoryProvider"].scope_key == "desk"
    assert by_name["KnowledgeSource"].scope_key == "source_id"
    assert by_name["ExecutionEnvironment"].scope_key == "kind"
    assert by_name["ComputeProvider"].scope_key == "kind"
    assert by_name["ContextCompiler"].scope_key == "daemon"
    assert by_name["ContextCompiler"].replaceable_default is True
    assert by_name["ModelDeployment"].cardinality is Cardinality.MULTI
    assert by_name["ToolAdapter"].cardinality is Cardinality.MULTI

    assert (
        MemoryProvider,
        ModelDeployment,
        ExecutionEnvironment,
        KnowledgeSource,
        ToolAdapter,
        ComputeProvider,
        ContextCompiler,
    ) == RUNTIME_PORT_TYPES


def test_singleton_without_scope_key_rejected() -> None:
    with pytest.raises(PortError, match="without explicit scope key"):
        require_singleton_scope_key("MemoryProvider", None)
    with pytest.raises(PortError, match="without explicit scope key"):
        require_singleton_scope_key("ContextCompiler", "")
    with pytest.raises(PortError, match="requires scope key"):
        require_singleton_scope_key("KnowledgeSource", "desk")
    assert require_singleton_scope_key("ExecutionEnvironment", "kind") == "kind"


def test_multi_contribution_points_and_keys() -> None:
    assert {
        "tool",
        "tool_adapter",
        "hook",
        "skill",
        "graph_template",
        "model_deployment",
        "toolset",
        "worker_template",
    } == MULTI_CONTRIBUTION_POINTS
    assert qualified_contribution_id("research-corpus", "search") == ("research-corpus:search")
    assert validate_multi_contribution_key("dev-factory:build") == (
        "dev-factory",
        "build",
    )
    with pytest.raises(PortError):
        validate_multi_contribution_key("nope")
    with pytest.raises(PortError):
        qualified_contribution_id("bad:id", "x")


def test_undeclared_ui_and_schemaless_contribution_rejected() -> None:
    for point in MULTI_CONTRIBUTION_POINTS:
        assert has_qma_wire_schema(point)
        assert validate_contribution_point(point) == point
    with pytest.raises(PortError, match="undeclared or retired"):
        validate_contribution_point("ui_view")
    with pytest.raises(PortError, match="undeclared or retired"):
        validate_contribution_point("command")
    with pytest.raises(PortError, match="not one of the eight"):
        validate_contribution_point("invented_point")
    assert not has_qma_wire_schema("ui_view")


def test_plugin_surface_imports_from_core_plugins() -> None:
    assert plugins_api.PluginManifest is PluginManifest
    assert plugins_api.PluginContext is PluginContext
    assert plugins_api.HookEvent.__name__ == "HookEvent"
    assert plugins_api.HookResult is HookResult
    assert plugins_api.HandleKind is HandleKind
    ref = parse_credential_ref("cred://models/openai")
    assert str(ref) == "cred://models/openai"
    with pytest.raises(plugins_api.CredentialRefError):
        parse_credential_ref("secret=literally-a-value")


def test_hook_event_and_result_builders() -> None:
    event = build_hook_event("before_tool", source=HookSource.PLUGIN, payload={"a": 1})
    assert event.phase.value == "before"
    result = build_hook_result(HookResultDecision.DENY, reason="blocked")
    assert result.decision is HookResultDecision.DENY
    with pytest.raises(VocabularyError):
        build_hook_result("observe", updated_input={"x": 1})


def test_parse_plugin_manifest_valid_and_invalid() -> None:
    manifest = parse_plugin_manifest(
        {
            "id": "research-corpus",
            "version": "0.1.0",
            "qma_api": ">=0.1.0,<1.0.0",
            "desk": "research",
            "entrypoint": "research_corpus.activate",
            "dependencies": [],
            "contributions": [
                {
                    "point": "MemoryProvider",
                    "scope_key": "desk",
                },
                {"point": "tool", "local_id": "search"},
            ],
            "permissions": [],
            "migrations": [],
        }
    )
    assert isinstance(manifest, PluginManifest)
    assert len(manifest.contributions) == 2
    assert manifest.contributions[0].cardinality is Cardinality.SINGLETON
    assert manifest.contributions[1].local_id == "search"

    with pytest.raises(ManifestError, match="without explicit scope key"):
        parse_plugin_manifest(
            {
                "id": "research-corpus",
                "version": "0.1.0",
                "qma_api": ">=0.1.0,<1.0.0",
                "desk": "research",
                "entrypoint": "research_corpus.activate",
                "contributions": [{"point": "MemoryProvider"}],
            }
        )
    with pytest.raises(ManifestError, match="ui_view"):
        parse_plugin_manifest(
            {
                "id": "research-corpus",
                "version": "0.1.0",
                "qma_api": ">=0.1.0,<1.0.0",
                "desk": "research",
                "entrypoint": "research_corpus.activate",
                "contributions": [{"point": "ui_view", "local_id": "panel"}],
            }
        )


def test_core_definitions_only_and_desk_packages_ban_daemon() -> None:
    assert_core_definitions_only(CORE_SRC)
    assert_no_daemon_import(PLUGINS_ROOT)

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        bad = Path(tmp) / "bad_plugin.py"
        bad.write_text("import qma.daemon\n", encoding="utf-8")
        with pytest.raises(BoundaryError, match="must not import qma-daemon"):
            assert_no_daemon_import(Path(tmp))

        writer_root = Path(tmp) / "writer_tree"
        writer_root.mkdir()
        writer = writer_root / "writer.py"
        writer.write_text("def f():\n    open('x', 'w')\n", encoding="utf-8")
        with pytest.raises(BoundaryError, match="definitions only"):
            assert_core_definitions_only(writer_root)


def test_ports_package_exports() -> None:
    assert ports_api.MemoryProvider is MemoryProvider
    assert "ContextCompiler" in {c.name for c in ports_api.PORT_CONTRACTS}
