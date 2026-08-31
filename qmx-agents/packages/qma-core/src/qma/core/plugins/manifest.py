"""PluginManifest and contribution declarations (CT-42; AD-1, AD-21)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, cast

from qma.core.ontology.desks import DESK_PREFIX_TOKENS
from qma.core.ports.cardinality import (
    PORT_CONTRACT_BY_NAME,
    Cardinality,
    PortError,
    require_singleton_scope_key,
    validate_contribution_point,
)

__all__ = [
    "DESK_PREFIX_TOKENS",
    "ContributionDecl",
    "ManifestError",
    "PluginManifest",
    "PluginRosterEntry",
    "parse_plugin_manifest",
]

RollbackMode = Literal["forward_only"]


class ManifestError(ValueError):
    """Raised when a PluginManifest violates CT-42 / AD-1 constraints."""


@dataclass(frozen=True, slots=True)
class ContributionDecl:
    """One declared contribution on a PluginManifest."""

    point: str
    cardinality: Cardinality
    scope_key: str | None = None
    local_id: str | None = None


@dataclass(frozen=True, slots=True)
class PluginManifest:
    """Declarative plugin package identity and contribution surface."""

    id: str
    version: str
    qma_api: str
    desk: str
    entrypoint: str
    dependencies: tuple[str, ...] = ()
    contributions: tuple[ContributionDecl, ...] = ()
    permissions: tuple[str, ...] = ()
    migrations: tuple[Mapping[str, object], ...] = ()
    rollback: RollbackMode | None = None


@dataclass(frozen=True, slots=True)
class PluginRosterEntry:
    """Daemon startup roster entry — configuration, never a contribution."""

    plugin_id: str
    version: str
    enabled: bool


def _parse_contribution(raw: Mapping[str, object], *, plugin_id: str) -> ContributionDecl:
    point = raw.get("point")
    if not isinstance(point, str):
        raise ManifestError(f"contribution point must be a string; got {point!r}")

    # Singleton port bindings use the port type name; multi points use the eight names.
    if point in PORT_CONTRACT_BY_NAME:
        contract = PORT_CONTRACT_BY_NAME[point]
        if contract.cardinality is Cardinality.SINGLETON:
            scope_key = raw.get("scope_key")
            if not isinstance(scope_key, str) and scope_key is not None:
                raise ManifestError(f"scope_key must be a string; got {scope_key!r}")
            try:
                require_singleton_scope_key(point, scope_key)
            except PortError as exc:
                raise ManifestError(str(exc)) from exc
            return ContributionDecl(
                point=point,
                cardinality=Cardinality.SINGLETON,
                scope_key=contract.scope_key,
            )
        # Multi ports (ModelDeployment, ToolAdapter) contribute under their multi names.
        raise ManifestError(
            f"{point} registers as multi contribution "
            f"{'model_deployment' if point == 'ModelDeployment' else 'tool_adapter'}"
        )

    try:
        validate_contribution_point(point)
    except PortError as exc:
        raise ManifestError(str(exc)) from exc

    local_id = raw.get("local_id")
    if not isinstance(local_id, str) or not local_id:
        raise ManifestError(
            f"multi contribution {point!r} on plugin {plugin_id!r} requires local_id"
        )
    if ":" in local_id:
        raise ManifestError(f"local_id must not contain ':'; got {local_id!r}")
    return ContributionDecl(
        point=point,
        cardinality=Cardinality.MULTI,
        local_id=local_id,
    )


def parse_plugin_manifest(raw: Mapping[str, object]) -> PluginManifest:
    """Validate and materialize a PluginManifest mapping."""
    plugin_id = raw.get("id")
    version = raw.get("version")
    qma_api = raw.get("qma_api")
    desk = raw.get("desk")
    entrypoint = raw.get("entrypoint")
    if not isinstance(plugin_id, str) or not plugin_id:
        raise ManifestError("id is required as a non-empty string")
    if not isinstance(version, str) or not version:
        raise ManifestError("version is required as a non-empty string")
    if not isinstance(qma_api, str) or not qma_api:
        raise ManifestError("qma_api is required as a non-empty string")
    if not isinstance(desk, str) or not desk:
        raise ManifestError("desk is required as a non-empty string")
    if desk not in DESK_PREFIX_TOKENS:
        raise ManifestError(f"desk must be one of {sorted(DESK_PREFIX_TOKENS)}; got {desk!r}")
    if entrypoint is None:
        raise ManifestError("entrypoint is required")
    if not isinstance(entrypoint, str) or not entrypoint:
        raise ManifestError(f"entrypoint must be a non-empty string; got {entrypoint!r}")

    # Operator-assigned fields may not appear on the load-time manifest (AD-15/16).
    for forbidden in ("model_family", "tool_adapter_binding"):
        if forbidden in raw:
            raise ManifestError(
                f"manifest for {plugin_id!r} declares operator-assigned field {forbidden!r}"
            )

    deps_raw = raw.get("dependencies", ())
    contribs_raw = raw.get("contributions", ())
    perms_raw = raw.get("permissions", ())
    migrations_raw = raw.get("migrations", ())
    if not isinstance(deps_raw, Sequence) or isinstance(deps_raw, (str, bytes)):
        raise ManifestError("dependencies must be a sequence")
    if not isinstance(contribs_raw, Sequence) or isinstance(contribs_raw, (str, bytes)):
        raise ManifestError("contributions must be a sequence")
    if not isinstance(perms_raw, Sequence) or isinstance(perms_raw, (str, bytes)):
        raise ManifestError("permissions must be a sequence")
    if not isinstance(migrations_raw, Sequence) or isinstance(migrations_raw, (str, bytes)):
        raise ManifestError("migrations must be a sequence")

    deps_items = cast(Sequence[object], deps_raw)
    perms_items = cast(Sequence[object], perms_raw)
    contrib_items = cast(Sequence[object], contribs_raw)
    migration_items = cast(Sequence[object], migrations_raw)

    dependencies = tuple(str(item) for item in deps_items)
    permissions = tuple(str(item) for item in perms_items)
    contributions: list[ContributionDecl] = []
    for item in contrib_items:
        if not isinstance(item, Mapping):
            raise ManifestError("each contribution must be a mapping")
        raw_map = cast(Mapping[object, object], item)
        contrib_map: dict[str, object] = {str(k): v for k, v in raw_map.items()}
        contributions.append(_parse_contribution(contrib_map, plugin_id=plugin_id))

    migrations: list[Mapping[str, object]] = []
    for item in migration_items:
        if not isinstance(item, Mapping):
            raise ManifestError("each migration must be a mapping")
        raw_map = cast(Mapping[object, object], item)
        migrations.append({str(k): v for k, v in raw_map.items()})

    rollback_raw = raw.get("rollback")
    rollback: RollbackMode | None
    if rollback_raw is None:
        rollback = None
    elif rollback_raw == "forward_only":
        rollback = "forward_only"
    else:
        raise ManifestError(f"rollback must be 'forward_only' or omitted; got {rollback_raw!r}")

    return PluginManifest(
        id=plugin_id,
        version=version,
        qma_api=qma_api,
        desk=desk,
        entrypoint=entrypoint,
        dependencies=dependencies,
        contributions=tuple(contributions),
        permissions=permissions,
        migrations=tuple(migrations),
        rollback=rollback,
    )
