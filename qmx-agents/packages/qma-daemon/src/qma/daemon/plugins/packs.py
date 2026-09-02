"""First-party desk plugin pack roster (FR-Q71; FEAT-0046; CT-42).

Loads the five packs from ``qmx-agents/plugins/`` and activates them through
the core ``PluginManifest`` / ``PluginContext`` surface. Authors import
contribution types from ``qma-core``; this module never offers a daemon-private
registration path. ``analysis-backtest`` is the existing Backtesting Service
adapter: one ``qmb`` job per environment through the QMB door.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import cast

from qma.core.ontology.records import Agent, Subagent
from qma.core.plugins.manifest import PluginManifest, parse_plugin_manifest
from qma.core.plugins.packs import (
    ANALYSIS_BACKTEST_PLUGIN_ID,
    DESK_PLUGIN_PACK_DESKS,
    DESK_PLUGIN_PACK_IDS,
    MEMORY_CANDIDATES_ARE_ADMITTED,
    PACK_ENTRYPOINT,
    PROMOTE_IS_HUMAN_OUTSIDE_QMA,
    REFINEMENT_PROPOSALS_ARE_APPLIED,
    require_desk_plugin_pack_id,
)
from qma.core.ports.cardinality import Cardinality
from qma.core.ports.knowledge import KnowledgeSource
from qma.core.ports.memory import MemoryProvider, refuse_memory_promote
from qma.core.ports.qmb import QMB_BACKTEST_TOOL_ID, QMB_OWNED_CONCERNS
from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.backtest.service import BacktestingService
from qma.daemon.capabilities.spawn import SpawnRequest, spawn_agent
from qma.daemon.knowledge import KnowledgeSourceRegistry
from qma.daemon.memory import MemoryAdmissionGate
from qma.daemon.plugins.loader import (
    LoadedPlugin,
    PluginActivator,
    PluginLoader,
    PluginLoadError,
)
from qma.daemon.staging.proposal import ProposalGate
from qma.daemon.taskgraph.compiler import GraphTemplateCatalog, MissionCompiler
from qma.daemon.taskgraph.records import GraphTemplate
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "ANALYSIS_BACKTEST_PLUGIN_ID",
    "DESK_PLUGIN_PACK_DESKS",
    "DESK_PLUGIN_PACK_IDS",
    "MEMORY_CANDIDATES_ARE_ADMITTED",
    "PACK_ENTRYPOINT",
    "PROMOTE_IS_HUMAN_OUTSIDE_QMA",
    "QMB_OWNED_CONCERNS",
    "REFINEMENT_PROPOSALS_ARE_APPLIED",
    "DeskPluginRoster",
    "default_plugins_root",
    "load_pack_activator",
    "load_pack_manifest_raw",
]


def default_plugins_root() -> Path:
    """Resolve ``qmx-agents/plugins`` from this module or a parent walk."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "plugins"
        if (candidate / "research-corpus" / "manifest.json").is_file():
            return candidate
    return here.parents[6] / "plugins"


def load_pack_manifest_raw(plugin_root: Path) -> dict[str, object]:
    """Read one pack ``manifest.json`` as a mapping."""
    path = plugin_root / "manifest.json"
    if not path.is_file():
        raise PluginLoadError(
            f"desk pack manifest missing at {path}",
            plugin_id=plugin_root.name,
            field="manifest",
        )
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise PluginLoadError(
            f"manifest must be a JSON object; got {type(loaded).__name__}",
            plugin_id=plugin_root.name,
            field="manifest",
        )
    return cast(dict[str, object], loaded)


def load_pack_activator(plugin_root: Path, entrypoint: str) -> PluginActivator:
    """Import ``activate`` from the pack tree without a ``qma.daemon`` edge."""
    if ":" not in entrypoint:
        raise PluginLoadError(
            f"entrypoint must be module:function; got {entrypoint!r}",
            plugin_id=plugin_root.name,
            field="entrypoint",
        )
    module_rel, func_name = entrypoint.split(":", 1)
    if not module_rel or not func_name:
        raise PluginLoadError(
            f"entrypoint must be module:function; got {entrypoint!r}",
            plugin_id=plugin_root.name,
            field="entrypoint",
        )
    path = plugin_root.joinpath(*module_rel.split(".")).with_suffix(".py")
    if not path.is_file():
        raise PluginLoadError(
            f"entrypoint module not found at {path}",
            plugin_id=plugin_root.name,
            field="entrypoint",
        )
    module_name = f"qma_desk_pack_{plugin_root.name}_{module_rel.replace('.', '_')}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise PluginLoadError(
            f"cannot load entrypoint {entrypoint!r}",
            plugin_id=plugin_root.name,
            field="entrypoint",
        )
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    activator = getattr(module, func_name, None)
    if not callable(activator):
        raise PluginLoadError(
            f"entrypoint {entrypoint!r} is not callable",
            plugin_id=plugin_root.name,
            field="entrypoint",
        )
    return cast(PluginActivator, activator)


def _graph_template_from_mapping(payload: Mapping[str, object]) -> GraphTemplate:
    nodes_raw = payload.get("nodes", ())
    edges_raw = payload.get("edges", ())
    nodes: tuple[Mapping[str, object], ...]
    edges: tuple[Mapping[str, object], ...]
    if isinstance(nodes_raw, Sequence) and not isinstance(nodes_raw, (str, bytes)):
        nodes = tuple(
            dict(cast(Mapping[str, object], item))
            for item in cast(Sequence[object], nodes_raw)
            if isinstance(item, Mapping)
        )
    else:
        nodes = ()
    if isinstance(edges_raw, Sequence) and not isinstance(edges_raw, (str, bytes)):
        edges = tuple(
            dict(cast(Mapping[str, object], item))
            for item in cast(Sequence[object], edges_raw)
            if isinstance(item, Mapping)
        )
    else:
        edges = ()
    qualified = payload.get("qualified_id")
    version = payload.get("version")
    if not isinstance(qualified, str) or not isinstance(version, str):
        msg = "graph_template requires qualified_id and version"
        raise PluginLoadError(msg, field="graph_template")
    return GraphTemplate(qualified_id=qualified, version=version, nodes=nodes, edges=edges)


class DeskPluginRoster:
    """Five first-party desk packs registered through the core contribution surface."""

    def __init__(
        self,
        *,
        plugins_root: Path | None = None,
        loader: PluginLoader | None = None,
        backtesting: BacktestingService | None = None,
    ) -> None:
        self.plugins_root = plugins_root if plugins_root is not None else default_plugins_root()
        self.loader = loader if loader is not None else PluginLoader()
        self.backtesting = backtesting if backtesting is not None else BacktestingService()
        self.templates = GraphTemplateCatalog()
        self.compiler = MissionCompiler(templates=self.templates)
        self.memory = MemoryAdmissionGate()
        self.knowledge = KnowledgeSourceRegistry()
        self.proposals = ProposalGate()

    @property
    def pack_ids(self) -> tuple[str, ...]:
        return DESK_PLUGIN_PACK_IDS

    def raw_manifests(self) -> tuple[dict[str, object], ...]:
        """Load the five pack manifests in roster order."""
        rows: list[dict[str, object]] = []
        present = sorted(path.name for path in self.plugins_root.iterdir() if path.is_dir())
        expected = sorted(DESK_PLUGIN_PACK_IDS)
        if present != expected:
            raise PluginLoadError(
                f"desk-pack roster must be {expected}; found {present}",
                field="id",
            )
        for plugin_id in DESK_PLUGIN_PACK_IDS:
            require_desk_plugin_pack_id(plugin_id)
            raw = load_pack_manifest_raw(self.plugins_root / plugin_id)
            if raw.get("id") != plugin_id:
                raise PluginLoadError(
                    f"manifest id {raw.get('id')!r} does not match directory {plugin_id!r}",
                    plugin_id=plugin_id,
                    field="id",
                )
            desk = DESK_PLUGIN_PACK_DESKS[plugin_id]
            if raw.get("desk") != desk:
                raise PluginLoadError(
                    f"manifest desk {raw.get('desk')!r} must be {desk!r}",
                    plugin_id=plugin_id,
                    field="desk",
                )
            rows.append(raw)
        return tuple(rows)

    def parsed_manifests(self) -> tuple[PluginManifest, ...]:
        return tuple(parse_plugin_manifest(raw) for raw in self.raw_manifests())

    def activators(self) -> dict[str, PluginActivator]:
        loaded: dict[str, PluginActivator] = {}
        for manifest in self.parsed_manifests():
            loaded[manifest.id] = load_pack_activator(
                self.plugins_root / manifest.id,
                manifest.entrypoint,
            )
        return loaded

    def activate(
        self,
        *,
        principal: object = PrincipalClass.OPERATOR,
        correlation_id: object = "desk-pack-roster",
    ) -> Result[tuple[LoadedPlugin, ...]]:
        """Activate every pack through ``PluginLoader`` (core contribution surface)."""
        try:
            raw = self.raw_manifests()
            acts = self.activators()
        except (PluginLoadError, OSError, json.JSONDecodeError, ValueError) as exc:
            plugin_id = getattr(exc, "plugin_id", None)
            field = getattr(exc, "field", "manifest")
            return invalid_input(
                str(field) if isinstance(field, str) else "manifest",
                str(exc),
                plugin_id=plugin_id,
            )
        activated = self.loader.activate_roster(
            raw,
            activators=acts,
            principal=principal,
            correlation_id=correlation_id,
        )
        if not is_ok(activated):
            return activated
        ingested = self._ingest_activated(activated.value)
        if is_refusal(ingested):
            for row in reversed(activated.value):
                self.loader.unload(row.manifest.id)
            return ingested
        return Ok(activated.value)

    def _ingest_activated(self, loaded: Sequence[LoadedPlugin]) -> Result[None]:
        for row in loaded:
            declared = self._assert_declared_registered(row)
            if is_refusal(declared):
                return declared
            templates = self._ingest_graph_templates(row)
            if is_refusal(templates):
                return templates
            bound = self._bind_singletons(row)
            if is_refusal(bound):
                return bound
        analysis = self.loader.get(ANALYSIS_BACKTEST_PLUGIN_ID)
        if analysis is None:
            return invalid_input(
                "analysis-backtest",
                "analysis-backtest must be activated as the Backtesting Service adapter",
            )
        installed = self.backtesting.install(context=analysis.context)
        if is_refusal(installed):
            return installed
        if installed.value.tool_id != QMB_BACKTEST_TOOL_ID:
            return invalid_input("tool_id", "analysis-backtest exposes one qmb tool")
        return Ok(None)

    def _assert_declared_registered(self, loaded: LoadedPlugin) -> Result[None]:
        snap = loaded.context.snapshot()
        singletons = cast(Mapping[object, object], snap["singletons"])
        multis = cast(Mapping[object, object], snap["multis"])
        for decl in loaded.manifest.contributions:
            if decl.cardinality is Cardinality.SINGLETON:
                found = any(
                    isinstance(key, tuple)
                    and len(cast(tuple[object, ...], key)) == 2
                    and cast(tuple[object, ...], key)[0] == decl.point
                    for key in singletons
                )
                if not found:
                    return invalid_input(
                        decl.point,
                        "declared singleton was not registered through PluginContext",
                        plugin_id=loaded.manifest.id,
                    )
            elif decl.local_id is not None:
                key = (decl.point, f"{loaded.manifest.id}:{decl.local_id}")
                if key not in multis:
                    return invalid_input(
                        decl.point,
                        "declared multi contribution was not registered through PluginContext",
                        plugin_id=loaded.manifest.id,
                        local_id=decl.local_id,
                    )
        return Ok(None)

    def _ingest_graph_templates(self, loaded: LoadedPlugin) -> Result[None]:
        snap = loaded.context.snapshot()
        multis = cast(Mapping[object, object], snap["multis"])
        for key, value in multis.items():
            if not isinstance(key, tuple):
                continue
            pair = cast(tuple[object, ...], key)
            if len(pair) != 2 or pair[0] != "graph_template":
                continue
            if not isinstance(value, Mapping):
                return invalid_input(
                    "graph_template",
                    "graph_template contribution must be a mapping",
                    plugin_id=loaded.manifest.id,
                )
            mapping = cast(Mapping[str, object], value)
            if mapping.get("stateless") is not True or mapping.get("runtime_state") is not None:
                return policy_rejection(
                    "graph_template",
                    "Graph Template remains an authored, versioned, stateless definition "
                    "(FR-Q71; AD-13)",
                    plugin_id=loaded.manifest.id,
                    qualified_id=mapping.get("qualified_id"),
                )
            try:
                template = _graph_template_from_mapping(mapping)
            except (PluginLoadError, ValueError, TypeError) as exc:
                return invalid_input("graph_template", str(exc), plugin_id=loaded.manifest.id)
            registered = self.templates.register(template)
            if is_refusal(registered):
                return registered
        return Ok(None)

    def _bind_singletons(self, loaded: LoadedPlugin) -> Result[None]:
        snap = loaded.context.snapshot()
        singletons = cast(Mapping[object, object], snap["singletons"])
        for key, value in singletons.items():
            if not isinstance(key, tuple):
                continue
            pair = cast(tuple[object, ...], key)
            if len(pair) != 2:
                continue
            port, scope_value = pair
            if port == "MemoryProvider" and isinstance(scope_value, str):
                bound = self.memory.bind(
                    scope_value,
                    cast(MemoryProvider, value),
                    plugin_id=loaded.manifest.id,
                )
                if is_refusal(bound):
                    return bound
            if port == "KnowledgeSource" and isinstance(scope_value, str):
                bound_k = self.knowledge.bind(
                    scope_value,
                    cast(KnowledgeSource, value),
                    plugin_id=loaded.manifest.id,
                )
                if is_refusal(bound_k):
                    return bound_k
        return Ok(None)

    def published_tool_ids(self) -> frozenset[str]:
        return frozenset(
            row.qualified_id
            for row in self.loader.published_contributions()
            if row.point == "tool" and row.qualified_id is not None
        )

    def spawn_constrained(
        self,
        request: SpawnRequest,
    ) -> Result[Agent | Subagent]:
        """Spawn with the pack contribution set as the Agent-spawn ceiling."""
        published = self.published_tool_ids()
        requested_pack = {
            tool_id
            for tool_id in request.role_base.tool_ids
            if tool_id.split(":", 1)[0] in DESK_PLUGIN_PACK_IDS
        }
        extras = sorted(requested_pack - published)
        if extras:
            return policy_rejection(
                "effective_capabilities",
                "Agent spawn may not grant a desk-pack tool that was not published "
                "through PluginContext (FR-Q71; AD-16)",
                extras=extras,
            )
        return spawn_agent(request)

    def refuse_promote(self, *, surface: str = "artifact") -> Result[None]:
        """Promote is a human live-zone act outside QMA (DEC-0345)."""
        if surface == "memory":
            return refuse_memory_promote()
        return self.proposals.promote_refused("outside-qma")

    def snapshot(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "pack_ids": list(DESK_PLUGIN_PACK_IDS),
                "desks": dict(DESK_PLUGIN_PACK_DESKS),
                "loaded": list(self.loader.loaded_ids()),
                "published": [
                    dict(row.to_payload()) for row in self.loader.published_contributions()
                ],
                "qmb_tool_id": QMB_BACKTEST_TOOL_ID,
                "scheduling_authority": self.backtesting.scheduling_authority,
                "parallelism": self.backtesting.parallelism,
                "backtest_state": self.backtesting.backtest_state,
                "qmb_owned": sorted(QMB_OWNED_CONCERNS),
                "memory_candidates_admitted": MEMORY_CANDIDATES_ARE_ADMITTED,
                "refinement_proposals_applied": REFINEMENT_PROPOSALS_ARE_APPLIED,
                "promote_is_human_outside_qma": PROMOTE_IS_HUMAN_OUTSIDE_QMA,
            }
        )
