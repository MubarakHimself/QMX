"""Plugin loader — validate manifests and activate scoped contributions (FR-Q68; CT-42).

Load order for explicit install / enable / reload:
manifest validation → qma_api compatibility → permissions → dependencies →
migrations → topological activation → publication over the wire surface.

Reload is an explicit operator command. There is no file watcher and no
reactive remount. Contribution types are imported from ``qma-core``; this
module implements the daemon-owned loader only. Migrations (FR-Q69) run the
five-step path with an ``fp1`` journal checkpoint; forward-only upgrades take
a recorded ``operator`` confirmation.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, Literal, cast

from qma.core.plugins.context import Disposer, PluginContext
from qma.core.plugins.manifest import (
    ManifestError,
    PluginManifest,
    parse_plugin_manifest,
    validate_migration_rollback_contract,
)
from qma.core.ports.cardinality import Cardinality
from qma.core.ports.permissions import check_plugin_permissions_at_load
from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.plugins.context import DaemonPluginContext, PluginContextError
from qma.daemon.plugins.exit_stack import PluginExitStack
from qma.daemon.plugins.migrations import (
    DisableReceipt,
    ForwardOnlyConfirmation,
    InstallPreflightResult,
    PluginMigrationReport,
    PluginMigrationRunner,
    rollback_mode_for_manifest,
)
from qma.wire.principals import authorize_wire_command, parse_principal_class
from qmf.core import Ok, Result, is_ok
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

if TYPE_CHECKING:
    from qma.daemon.journal.authoritative import AuthoritativeJournal

__all__ = [
    "FILE_WATCHER_ENABLED",
    "LOAD_PHASES",
    "LoadedPlugin",
    "PluginActivator",
    "PluginLoadError",
    "PluginLoader",
    "PublishedContribution",
    "check_qma_api_compatible",
    "topological_plugin_order",
]

LoadCommand = Literal["plugin.install", "plugin.enable", "plugin.reload"]
PluginActivator = Callable[[PluginContext], None]

# Explicit-command only — never a file watcher or reactive remount (AD-21).
FILE_WATCHER_ENABLED: Final[bool] = False

LOAD_PHASES: Final[tuple[str, ...]] = (
    "manifest_validation",
    "qma_api_compatibility",
    "permissions",
    "dependencies",
    "migrations",
    "topological_activation",
    "publication",
)

_SEMVER: Final[re.Pattern[str]] = re.compile(
    r"\A(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z"
)
_RANGE_CLAUSE: Final[re.Pattern[str]] = re.compile(
    r"\A\s*(>=|<=|>|<|==|=)?\s*"
    r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\s*\Z"
)


class PluginLoadError(ValueError):
    """Hard load refusal naming the offending plugin and field."""

    def __init__(
        self, message: str, *, plugin_id: str | None = None, field: str | None = None
    ) -> None:
        super().__init__(message)
        self.plugin_id = plugin_id
        self.field = field


def _version_tuple(value: str) -> tuple[int, int, int]:
    core = value.split("+", 1)[0].split("-", 1)[0]
    major_s, minor_s, patch_s = core.split(".")
    return int(major_s), int(minor_s), int(patch_s)


def check_qma_api_compatible(required: str, daemon_version: str) -> None:
    """Accept a comma-separated qma_api range against the daemon API version.

    Compatibility is additive-only within a major (CT-42; DEC-0320).
    """
    if not required.strip():
        raise PluginLoadError("qma_api is required as a non-empty string", field="qma_api")
    if _SEMVER.match(daemon_version) is None:
        raise PluginLoadError(
            f"daemon qma_api version must be semver; got {daemon_version!r}",
            field="qma_api",
        )
    daemon = _version_tuple(daemon_version)
    clauses = [part.strip() for part in required.split(",") if part.strip()]
    if not clauses:
        raise PluginLoadError(
            f"qma_api range is empty; got {required!r}",
            field="qma_api",
        )
    for clause in clauses:
        match = _RANGE_CLAUSE.match(clause)
        if match is None:
            # Bare exact version without operator.
            if _SEMVER.match(clause) is None:
                raise PluginLoadError(
                    f"qma_api clause is not a semver range; got {clause!r}",
                    field="qma_api",
                )
            if _version_tuple(clause) != daemon:
                raise PluginLoadError(
                    f"qma_api {required!r} is incompatible with daemon {daemon_version!r}",
                    field="qma_api",
                )
            continue
        op = match.group(1) or "=="
        if op == "=":
            op = "=="
        bound = (int(match.group(2)), int(match.group(3)), int(match.group(4)))
        ok = {
            ">=": daemon >= bound,
            "<=": daemon <= bound,
            ">": daemon > bound,
            "<": daemon < bound,
            "==": daemon == bound,
        }[op]
        if not ok:
            raise PluginLoadError(
                f"qma_api {required!r} is incompatible with daemon {daemon_version!r}",
                field="qma_api",
            )


def topological_plugin_order(manifests: Sequence[PluginManifest]) -> tuple[str, ...]:
    """Return plugin ids in dependency order; refuse cycles and missing edges."""
    by_id = {manifest.id: manifest for manifest in manifests}
    if len(by_id) != len(manifests):
        raise PluginLoadError("duplicate plugin id in activation set", field="id")
    temporary: set[str] = set()
    permanent: set[str] = set()
    order: list[str] = []

    def visit(plugin_id: str) -> None:
        if plugin_id in permanent:
            return
        if plugin_id in temporary:
            raise PluginLoadError(
                f"dependency cycle involving plugin {plugin_id!r}",
                plugin_id=plugin_id,
                field="dependencies",
            )
        if plugin_id not in by_id:
            raise PluginLoadError(
                f"missing dependency {plugin_id!r}",
                plugin_id=plugin_id,
                field="dependencies",
            )
        temporary.add(plugin_id)
        for dep in by_id[plugin_id].dependencies:
            visit(dep)
        temporary.remove(plugin_id)
        permanent.add(plugin_id)
        order.append(plugin_id)

    for plugin_id in by_id:
        visit(plugin_id)
    return tuple(order)


@dataclass(frozen=True, slots=True)
class PublishedContribution:
    """One contribution published for clients over the qma-wire surface."""

    plugin_id: str
    point: str
    cardinality: str
    qualified_id: str | None = None
    scope_key: str | None = None
    scope_value: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "plugin_id": self.plugin_id,
            "point": self.point,
            "cardinality": self.cardinality,
        }
        if self.qualified_id is not None:
            payload["qualified_id"] = self.qualified_id
        if self.scope_key is not None:
            payload["scope_key"] = self.scope_key
        if self.scope_value is not None:
            payload["scope_value"] = self.scope_value
        return MappingProxyType(payload)


@dataclass
class LoadedPlugin:
    """One activated plugin scope held by the loader."""

    manifest: PluginManifest
    context: DaemonPluginContext
    exit_stack: PluginExitStack
    published: tuple[PublishedContribution, ...] = ()
    phases_completed: tuple[str, ...] = ()
    migration_report: PluginMigrationReport | None = None
    data_intact: bool = True


@dataclass
class PluginLoader:
    """Daemon-owned loader for first-party desk plugins (AD-21; FR-Q68/FR-Q69)."""

    daemon_qma_api: str = "0.1.0"
    permission_allowlist: frozenset[str] = frozenset()
    migrations: PluginMigrationRunner = field(default_factory=PluginMigrationRunner)
    journal: AuthoritativeJournal | None = None
    migration_source_root: Path | None = None
    migration_destination_root: Path | None = None
    _loaded: dict[str, LoadedPlugin] = field(default_factory=dict[str, LoadedPlugin], init=False)
    _singleton_owners: dict[tuple[str, str], str] = field(
        default_factory=dict[tuple[str, str], str], init=False
    )
    _multi_owners: dict[tuple[str, str], str] = field(
        default_factory=dict[tuple[str, str], str], init=False
    )
    _published: list[PublishedContribution] = field(
        default_factory=list[PublishedContribution], init=False
    )
    _disabled_data_intact: set[str] = field(default_factory=set[str], init=False)

    @property
    def file_watcher_enabled(self) -> bool:
        """Reload is explicit only — always False (AD-21; FR-Q68)."""
        return FILE_WATCHER_ENABLED

    @property
    def load_phases(self) -> tuple[str, ...]:
        return LOAD_PHASES

    def loaded_ids(self) -> tuple[str, ...]:
        return tuple(self._loaded)

    def get(self, plugin_id: str) -> LoadedPlugin | None:
        return self._loaded.get(plugin_id)

    def published_contributions(self) -> tuple[PublishedContribution, ...]:
        return tuple(self._published)

    def _refuse(self, field_name: str, reason: str, **extra: object) -> TypedRefusal:
        return policy_rejection(field_name, reason, **extra)

    def _require_operator(self, command: LoadCommand, principal: object) -> Result[PrincipalClass]:
        parsed = parse_principal_class(principal)
        if not is_ok(parsed):
            return parsed
        authorized = authorize_wire_command(command, parsed.value, args={})
        if not is_ok(authorized):
            return authorized
        return Ok(parsed.value)

    def _check_permissions(self, manifest: PluginManifest) -> Result[frozenset[str]]:
        return check_plugin_permissions_at_load(
            manifest.permissions,
            allowed=self.permission_allowlist,
            plugin_id=manifest.id,
        )

    def _check_dependencies(
        self,
        manifest: PluginManifest,
        *,
        available: frozenset[str] | None = None,
    ) -> None:
        known = self._loaded.keys() if available is None else available
        missing = [dep for dep in manifest.dependencies if dep not in known]
        if missing:
            raise PluginLoadError(
                f"missing dependencies {missing!r} for plugin {manifest.id!r}",
                plugin_id=manifest.id,
                field="dependencies",
            )

    def _migrations_phase(self, manifest: PluginManifest) -> None:
        """Validate the rollback contract; execution happens in ``_execute_migrations``."""
        try:
            validate_migration_rollback_contract(manifest.migrations, manifest.rollback)
        except ManifestError as exc:
            raise PluginLoadError(
                str(exc),
                plugin_id=manifest.id,
                field="migrations",
            ) from exc
        confirmed = self.migrations.has_forward_only_confirmation(manifest.id)
        if manifest.rollback == "forward_only" and not confirmed:
            raise PluginLoadError(
                "forward-only upgrade requires operator confirmation in this session "
                f"(plugin_id={manifest.id!r})",
                plugin_id=manifest.id,
                field="forward_only_confirmation",
            )

    def install_preflight(self, raw: Mapping[str, object]) -> Result[InstallPreflightResult]:
        """Install-command preflight query — returns rollback mode over qma-wire."""
        return self.migrations.install_preflight(raw)

    def confirm_forward_only(
        self,
        *,
        plugin_id: str,
        correlation_id: object,
        principal: object = PrincipalClass.OPERATOR,
    ) -> Result[ForwardOnlyConfirmation]:
        """Record operator confirmation for a forward-only upgrade (FR-Q69)."""
        return self.migrations.confirm_forward_only(
            plugin_id=plugin_id,
            correlation_id=correlation_id,
            principal=principal,
            journal=self.journal,
        )

    def _execute_migrations(
        self,
        manifest: PluginManifest,
        *,
        correlation_id: object,
    ) -> Result[PluginMigrationReport | None]:
        if not manifest.migrations:
            return Ok(None)
        if self.migration_source_root is None or self.migration_destination_root is None:
            return policy_rejection(
                "migrations",
                "plugin migrations require distinct source and destination roots "
                "(documented restore path; FR-Q69; AD-27)",
                plugin_id=manifest.id,
            )
        migrated = self.migrations.run_plugin_migrations(
            manifest,
            source_root=self.migration_source_root,
            destination_root=self.migration_destination_root,
            correlation_id=correlation_id,
            journal=self.journal,
            require_confirmation=True,
        )
        if not is_ok(migrated):
            return cast(Result[PluginMigrationReport | None], migrated)
        report: PluginMigrationReport | None = migrated.value
        return Ok(report)

    def _claim_bindings(self, context: DaemonPluginContext) -> list[Disposer]:
        """Claim daemon-wide singleton/multi keys; return claim disposers."""
        claims: list[Disposer] = []
        snap = context.snapshot()
        singletons = cast_mapping(snap["singletons"])
        multis = cast_mapping(snap["multis"])

        for key, _value in singletons.items():
            port, scope_value = key
            existing = self._singleton_owners.get(key)
            if existing is not None and existing != context.plugin_id:
                raise PluginLoadError(
                    f"duplicate singleton binding for {port} key {scope_value!r} "
                    f"owned by {existing!r} and {context.plugin_id!r}",
                    plugin_id=context.plugin_id,
                    field=port,
                )
            self._singleton_owners[key] = context.plugin_id

            def drop_singleton(
                owned: tuple[str, str] = key,
                owner: str = context.plugin_id,
            ) -> None:
                if self._singleton_owners.get(owned) == owner:
                    self._singleton_owners.pop(owned, None)

            claims.append(context.exit_stack.push(drop_singleton))

        for key, _value in multis.items():
            point, qualified = key
            existing = self._multi_owners.get(key)
            if existing is not None and existing != context.plugin_id:
                raise PluginLoadError(
                    f"duplicate multi contribution {qualified!r} for point {point!r} "
                    f"owned by {existing!r} and {context.plugin_id!r}",
                    plugin_id=context.plugin_id,
                    field=point,
                )
            self._multi_owners[key] = context.plugin_id

            def drop_multi(
                owned: tuple[str, str] = key,
                owner: str = context.plugin_id,
            ) -> None:
                if self._multi_owners.get(owned) == owner:
                    self._multi_owners.pop(owned, None)

            claims.append(context.exit_stack.push(drop_multi))

        return claims

    def _publish(self, context: DaemonPluginContext) -> tuple[PublishedContribution, ...]:
        snap = context.snapshot()
        published: list[PublishedContribution] = []
        for key, _value in cast_mapping(snap["singletons"]).items():
            port, scope_value = key
            scope_key = {
                "MemoryProvider": "desk",
                "KnowledgeSource": "source_id",
                "ExecutionEnvironment": "kind",
                "ComputeProvider": "kind",
                "ContextCompiler": "daemon",
            }.get(port)
            row = PublishedContribution(
                plugin_id=context.plugin_id,
                point=port,
                cardinality=Cardinality.SINGLETON.value,
                scope_key=scope_key,
                scope_value=scope_value,
            )
            published.append(row)
            self._published.append(row)
        for key, _value in cast_mapping(snap["multis"]).items():
            point, qualified = key
            row = PublishedContribution(
                plugin_id=context.plugin_id,
                point=point,
                cardinality=Cardinality.MULTI.value,
                qualified_id=qualified,
            )
            published.append(row)
            self._published.append(row)
        return tuple(published)

    def _drop_published(self, plugin_id: str) -> None:
        self._published = [row for row in self._published if row.plugin_id != plugin_id]

    def _activate(
        self,
        manifest: PluginManifest,
        activator: PluginActivator,
        *,
        migration_report: PluginMigrationReport | None = None,
    ) -> LoadedPlugin:
        if manifest.id in self._loaded:
            raise PluginLoadError(
                f"plugin id {manifest.id!r} is not unique daemon-wide",
                plugin_id=manifest.id,
                field="id",
            )
        exit_stack = PluginExitStack(manifest.id)
        context = DaemonPluginContext(manifest.id, exit_stack=exit_stack)
        phases: list[str] = [
            "manifest_validation",
            "qma_api_compatibility",
            "permissions",
            "dependencies",
            "migrations",
        ]
        try:
            activator(context)
            self._claim_bindings(context)
            phases.append("topological_activation")
            published = self._publish(context)
            phases.append("publication")
        except (PluginContextError, PluginLoadError, ManifestError) as exc:
            exit_stack.close()
            self._drop_published(manifest.id)
            if isinstance(exc, PluginLoadError):
                raise
            raise PluginLoadError(
                str(exc),
                plugin_id=manifest.id,
                field=getattr(exc, "field", "contributions"),
            ) from exc
        except Exception as exc:
            exit_stack.close()
            self._drop_published(manifest.id)
            raise PluginLoadError(
                f"activation failed for {manifest.id!r}: {exc}",
                plugin_id=manifest.id,
                field="entrypoint",
            ) from exc

        loaded = LoadedPlugin(
            manifest=manifest,
            context=context,
            exit_stack=exit_stack,
            published=published,
            phases_completed=tuple(phases),
            migration_report=migration_report,
            data_intact=True,
        )
        self._loaded[manifest.id] = loaded
        return loaded

    def _load_with_migrations(
        self,
        raw: Mapping[str, object],
        *,
        activator: PluginActivator,
        correlation_id: object,
    ) -> Result[LoadedPlugin]:
        prepared = self._validate_manifest_phases(raw)
        if not is_ok(prepared):
            return prepared
        migrated = self._execute_migrations(prepared.value, correlation_id=correlation_id)
        if not is_ok(migrated):
            return migrated
        try:
            loaded = self._activate(
                prepared.value,
                activator,
                migration_report=migrated.value,
            )
        except PluginLoadError as exc:
            return self._refuse(
                exc.field or "activation",
                str(exc),
                plugin_id=exc.plugin_id,
            )
        return Ok(loaded)

    def _validate_manifest_phases(
        self,
        raw: Mapping[str, object],
        *,
        check_dependencies: bool = True,
        available_dependencies: frozenset[str] | None = None,
    ) -> Result[PluginManifest]:
        try:
            manifest = parse_plugin_manifest(raw)
        except ManifestError as exc:
            return invalid_input(
                "manifest",
                str(exc),
                plugin_id=raw.get("id"),
            )
        try:
            check_qma_api_compatible(manifest.qma_api, self.daemon_qma_api)
        except PluginLoadError as exc:
            return self._refuse(
                "qma_api",
                str(exc),
                plugin_id=manifest.id,
                daemon_qma_api=self.daemon_qma_api,
            )
        perms = self._check_permissions(manifest)
        if not is_ok(perms):
            return perms
        try:
            if check_dependencies:
                self._check_dependencies(manifest, available=available_dependencies)
            self._migrations_phase(manifest)
        except PluginLoadError as exc:
            return self._refuse(
                exc.field or "dependencies",
                str(exc),
                plugin_id=exc.plugin_id or manifest.id,
            )
        return Ok(manifest)

    def install(
        self,
        raw: Mapping[str, object],
        *,
        activator: PluginActivator,
        principal: object = PrincipalClass.OPERATOR,
        correlation_id: object = "plugin-install",
    ) -> Result[LoadedPlugin]:
        """Operator-principal install following the closed load-phase order."""
        gated = self._require_operator("plugin.install", principal)
        if not is_ok(gated):
            return gated
        return self._load_with_migrations(
            raw, activator=activator, correlation_id=correlation_id
        )

    def enable(
        self,
        raw: Mapping[str, object],
        *,
        activator: PluginActivator,
        principal: object = PrincipalClass.OPERATOR,
        correlation_id: object = "plugin-enable",
    ) -> Result[LoadedPlugin]:
        """Operator-principal enable — same load order as install (FR-Q68)."""
        gated = self._require_operator("plugin.enable", principal)
        if not is_ok(gated):
            return gated
        return self._load_with_migrations(
            raw, activator=activator, correlation_id=correlation_id
        )

    def reload(
        self,
        raw: Mapping[str, object],
        *,
        activator: PluginActivator,
        principal: object = PrincipalClass.OPERATOR,
        correlation_id: object = "plugin-reload",
    ) -> Result[LoadedPlugin]:
        """Explicit reload — no file watcher, no reactive remount (AD-21)."""
        if self.file_watcher_enabled:
            return TypedRefusal(
                category=RefusalCategory.POLICY_REJECTION,
                retryability=Retryability.NO,
                context={
                    "field": "file_watcher",
                    "reason": "plugin reload must not use a file watcher (AD-21; FR-Q68)",
                },
            )
        gated = self._require_operator("plugin.reload", principal)
        if not is_ok(gated):
            return gated
        plugin_id = raw.get("id")
        if isinstance(plugin_id, str) and plugin_id in self._loaded:
            self.unload(plugin_id)
        return self._load_with_migrations(
            raw, activator=activator, correlation_id=correlation_id
        )

    def unload(self, plugin_id: str) -> int:
        """Close the plugin scope LIFO and remove every published contribution."""
        loaded = self._loaded.pop(plugin_id, None)
        if loaded is None:
            return 0
        count = loaded.exit_stack.close()
        self._drop_published(plugin_id)
        return count

    def disable(
        self,
        plugin_id: str,
        *,
        principal: object = PrincipalClass.OPERATOR,
    ) -> Result[DisableReceipt]:
        """Disable a plugin: dispose scope, keep data intact; never roll back forward-only."""
        gated = self._require_operator("plugin.enable", principal)
        if not is_ok(gated):
            return gated
        loaded = self.get(plugin_id)
        if loaded is not None and rollback_mode_for_manifest(loaded.manifest) == "forward_only":
            self._disabled_data_intact.add(plugin_id)
        self.unload(plugin_id)
        return self.migrations.disable_forward_only(plugin_id)

    def rollback_plugin(self, plugin_id: str) -> Result[object]:
        """Refuse rollback for forward-only plugins (FR-Q69; CT-42)."""
        loaded = self.get(plugin_id)
        forward_only = plugin_id in self._disabled_data_intact
        if loaded is not None:
            forward_only = forward_only or (
                rollback_mode_for_manifest(loaded.manifest) == "forward_only"
            )
        if forward_only:
            return self.migrations.refuse_forward_only_rollback(plugin_id)
        return policy_rejection(
            "rollback",
            "plugin rollback of reversible migrations uses declared downs under "
            "the restore path, not disable (FR-Q69)",
            plugin_id=plugin_id,
        )

    def activate_roster(
        self,
        manifests: Sequence[Mapping[str, object]],
        *,
        activators: Mapping[str, PluginActivator],
        principal: object = PrincipalClass.OPERATOR,
        correlation_id: object = "plugin-roster",
    ) -> Result[tuple[LoadedPlugin, ...]]:
        """Validate and topologically activate a set of manifests."""
        gated = self._require_operator("plugin.install", principal)
        if not is_ok(gated):
            return gated
        roster_ids = {
            str(raw["id"]) for raw in manifests if isinstance(raw.get("id"), str) and raw.get("id")
        }
        available = frozenset(self._loaded) | frozenset(roster_ids)
        parsed: list[PluginManifest] = []
        for raw in manifests:
            prepared = self._validate_manifest_phases(
                raw,
                check_dependencies=True,
                available_dependencies=available,
            )
            if not is_ok(prepared):
                return prepared
            parsed.append(prepared.value)
        try:
            order = topological_plugin_order(parsed)
        except PluginLoadError as exc:
            return self._refuse(
                exc.field or "dependencies",
                str(exc),
                plugin_id=exc.plugin_id,
            )
        by_id = {manifest.id: manifest for manifest in parsed}
        loaded_rows: list[LoadedPlugin] = []
        for plugin_id in order:
            activator = activators.get(plugin_id)
            if activator is None:
                for row in reversed(loaded_rows):
                    self.unload(row.manifest.id)
                return self._refuse(
                    "entrypoint",
                    f"no activator provided for plugin {plugin_id!r}",
                    plugin_id=plugin_id,
                )
            migrated = self._execute_migrations(
                by_id[plugin_id], correlation_id=f"{correlation_id}:{plugin_id}"
            )
            if not is_ok(migrated):
                for row in reversed(loaded_rows):
                    self.unload(row.manifest.id)
                return migrated
            try:
                loaded_rows.append(
                    self._activate(
                        by_id[plugin_id],
                        activator,
                        migration_report=migrated.value,
                    )
                )
            except PluginLoadError as exc:
                for row in reversed(loaded_rows):
                    self.unload(row.manifest.id)
                return self._refuse(
                    exc.field or "activation",
                    str(exc),
                    plugin_id=exc.plugin_id,
                )
        return Ok(tuple(loaded_rows))


def cast_mapping(value: object) -> dict[tuple[str, str], object]:
    if not isinstance(value, Mapping):
        return {}
    raw = cast(Mapping[object, object], value)
    typed: dict[tuple[str, str], object] = {}
    for key, item in raw.items():
        typed[cast_pair(key)] = item
    return typed


def cast_pair(value: object) -> tuple[str, str]:
    if isinstance(value, tuple):
        pair = cast(tuple[object, ...], value)
        if len(pair) == 2 and isinstance(pair[0], str) and isinstance(pair[1], str):
            return pair[0], pair[1]
    msg = f"expected (str, str) binding key; got {value!r}"
    raise PluginLoadError(msg, field="contributions")
