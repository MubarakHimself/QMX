"""Ops-toolkit config init / validate / explain (TN-18; AR-79).

Pure functions over the resolved artifact — no composition root, no doors, no
secret values printed or fingerprinted (CT-21).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qmn.config._refuse import invalid
from qmn.config.compiler import (
    COMPILE_LAYERS,
    NODE_CONFIG_CLASS,
    NODE_CONFIG_FORMAT_VERSION,
    NODE_CONFIG_KNOWN_FORMAT_VERSIONS,
    VALUE_STATUSES,
    ResolvedNodeConfig,
    ResolvedValueRow,
    compile_node_config,
    is_secret_ref_key,
)
from qmn.config.registry_catalog import EXPECTED_ROW_COUNT, VALUE_STATUS_REQUIRED_ROWS

__all__ = [
    "config_explain",
    "config_init",
    "config_validate",
    "explain_rows",
]

_SECRET_REF_DISPLAY: Final[str] = "<secret-ref>"  # noqa: S105 - display label, never a secret


def config_init(
    *,
    roster_identity: object = None,
) -> Result[ResolvedNodeConfig]:
    """Scaffold a blank resolved config: all 71 rows at ``value_status=blank``."""
    return compile_node_config(roster_identity=roster_identity, config_version=1)


def config_validate(config: object) -> Result[ResolvedNodeConfig]:
    """Validate a versioned resolved node-config artifact.

    Accepts a ``ResolvedNodeConfig`` or an identity mapping shaped like
    ``fp1_identity()``. Re-compiles from embedded row entries so schema and
    fingerprint stay consistent.
    """
    if isinstance(config, ResolvedNodeConfig):
        if len(config.rows) != EXPECTED_ROW_COUNT:
            return invalid(
                "rows",
                "resolved node-config carries exactly 71 value_status_required rows",
                given=len(config.rows),
            )
        if config.format_version not in NODE_CONFIG_KNOWN_FORMAT_VERSIONS:
            return invalid(
                "format_version",
                "unknown node-config format version is never best-effort read",
                given=config.format_version,
            )
        rebuilt = _recompile_from_rows(config)
        if is_refusal(rebuilt):
            return rebuilt
        if rebuilt.value.fingerprint.value != config.fingerprint.value:
            return invalid(
                "fingerprint",
                "artifact fingerprint does not match recomputed identity",
                given=config.fingerprint.value,
                expected=rebuilt.value.fingerprint.value,
            )
        return Ok(config)

    if not isinstance(config, Mapping):
        return invalid(
            "config",
            "config_validate accepts ResolvedNodeConfig or an identity mapping",
            given=repr(type(config).__name__),
        )
    body = cast("Mapping[str, object]", config)
    class_token = body.get("class")
    if class_token != NODE_CONFIG_CLASS:
        return invalid(
            "class",
            "a resolved node-config identity names class resolved-node-config",
            given=repr(class_token),
        )
    version = body.get("format_version")
    if not isinstance(version, int) or version not in NODE_CONFIG_KNOWN_FORMAT_VERSIONS:
        return invalid(
            "format_version",
            "unknown node-config format version is never best-effort read",
            given=repr(version),
        )
    rows_raw = body.get("rows")
    if not isinstance(rows_raw, Sequence) or isinstance(rows_raw, (str, bytes)):
        return invalid(
            "rows",
            "resolved node-config rows are a sequence of row identity entries",
        )
    layer_maps = _layer_maps_from_identity_rows(cast("Sequence[object]", rows_raw))
    if is_refusal(layer_maps):
        return layer_maps
    config_version = body.get("config_version", 1)
    if not isinstance(config_version, int) or config_version < 1:
        return invalid(
            "config_version",
            "config_version is a positive integer ordinal",
            given=repr(config_version),
        )
    roster_identity = body.get("roster_identity", {})
    branches_from = body.get("branches_from")
    if branches_from is not None and not isinstance(branches_from, int):
        return invalid(
            "branches_from",
            "branches_from is an integer config_version or omitted",
            given=repr(branches_from),
        )
    branches: int | None = branches_from if isinstance(branches_from, int) else None
    return compile_node_config(
        roster=layer_maps.value["roster"],
        bms=layer_maps.value["bms"],
        book=layer_maps.value["book"],
        node_defaults=layer_maps.value["node_defaults"],
        roster_identity=roster_identity,
        config_version=config_version,
        branches_from=branches,
    )


def config_explain(config: object) -> Result[dict[str, object]]:
    """Deterministic explain payload: missing rows, layer, owner, blank effects.

    Never prints a secret value — secret-ref keys render as reference ids or a
    placeholder (CT-21).
    """
    if not isinstance(config, ResolvedNodeConfig):
        return invalid(
            "config",
            "config_explain requires a ResolvedNodeConfig",
            given=repr(type(config).__name__),
        )
    validated = config_validate(config)
    if is_refusal(validated):
        return validated

    rows = explain_rows(config)
    payload: dict[str, object] = {
        "artifact_class": NODE_CONFIG_CLASS,
        "blank_rows": [r["name"] for r in rows if r["value_status"] == "blank"],
        "boot_blocking": list(config.boot_blocking_rows()),
        "config_version": config.config_version,
        "fingerprint": config.fingerprint.value,
        "format_version": NODE_CONFIG_FORMAT_VERSION,
        "layer_precedence": list(COMPILE_LAYERS),
        "live_blocking": list(config.live_blocking_rows()),
        "may_bind_role_live": config.may_bind_role_live(),
        "may_boot": config.may_boot(),
        "may_start_soak": config.may_start_soak(),
        "row_count": len(rows),
        "rows": rows,
        "soak_blocking": list(config.soak_blocking_rows()),
    }
    return Ok(payload)


def explain_rows(config: ResolvedNodeConfig) -> list[dict[str, object]]:
    """Stable, sorted row explain records — no secret values."""
    out: list[dict[str, object]] = []
    for name in sorted(config.rows):
        row = config.rows[name]
        out.append(_explain_one(row))
    return out


def _explain_one(row: ResolvedValueRow) -> dict[str, object]:
    record: dict[str, object] = {
        "admission_impact": row.admission_impact,
        "blank_effect": list(row.blank_effect),
        "component": row.component,
        "configurable": row.configurable,
        "name": row.name,
        "owner_scope": row.owner_scope,
        "source_layer": row.source_layer,
        "unit_kind": row.unit_kind,
        "value_status": row.value_status,
    }
    if row.is_blank:
        record["value"] = "<blank>"
    elif is_secret_ref_key(row.name):
        # Reference id is the safe handle; never a SecretValue plaintext.
        record["value"] = (
            row.value if isinstance(row.value, str) else _SECRET_REF_DISPLAY
        )
        record["secret_ref"] = True
    else:
        record["value"] = row.value
    if row.evidence_fp1 is not None:
        record["evidence_fp1"] = row.evidence_fp1.value
    return record


def _recompile_from_rows(config: ResolvedNodeConfig) -> Result[ResolvedNodeConfig]:
    layers: dict[str, dict[str, object]] = {
        "roster": {},
        "bms": {},
        "book": {},
        "node_defaults": {},
    }
    for name, row in config.rows.items():
        if row.value_status == "blank" or row.source_layer is None:
            continue
        entry: dict[str, object] = {"value_status": row.value_status}
        if row.value is not None:
            entry["value"] = row.value
        if row.evidence_fp1 is not None:
            entry["evidence_fp1"] = row.evidence_fp1.value
        layers[row.source_layer][name] = entry
    return compile_node_config(
        roster=layers["roster"],
        bms=layers["bms"],
        book=layers["book"],
        node_defaults=layers["node_defaults"],
        roster_identity=dict(config.roster_identity),
        config_version=config.config_version,
        branches_from=config.branches_from,
    )


def _layer_maps_from_identity_rows(
    rows: Sequence[object],
) -> Result[dict[str, dict[str, object]]]:
    catalog_names = {row["name"] for row in VALUE_STATUS_REQUIRED_ROWS}
    layers: dict[str, dict[str, object]] = {
        "roster": {},
        "bms": {},
        "book": {},
        "node_defaults": {},
    }
    seen: set[str] = set()
    for raw in rows:
        if not isinstance(raw, Mapping):
            return invalid(
                "rows",
                "each row identity entry is a mapping",
                given=repr(type(raw).__name__),
            )
        entry = cast("Mapping[str, object]", raw)
        name = entry.get("name")
        if not isinstance(name, str) or name not in catalog_names:
            return invalid(
                "rows",
                "row name must be a value_status_required registry key",
                given=repr(name),
            )
        if name in seen:
            return invalid("rows", "duplicate row name in identity", name=name)
        seen.add(name)
        status = entry.get("value_status")
        if status not in VALUE_STATUSES:
            return invalid(
                name,
                "value_status is blank | provisional-evidence | ratified",
                given=repr(status),
            )
        if status == "blank":
            continue
        source = entry.get("source_layer")
        if source not in COMPILE_LAYERS:
            return invalid(
                name,
                "source_layer must be one of the four compile layers",
                given=repr(source),
            )
        built: dict[str, object] = {"value_status": status}
        if "value" in entry:
            built["value"] = entry["value"]
        elif entry.get("secret_ref_present") is True:
            # Identity omitted the ref id; restore a stable opaque marker so
            # recompile keeps secret-ref presence without inventing a credential.
            built["value"] = "secret-ref:present"
        else:
            return invalid(
                name,
                "non-blank identity rows carry value or secret_ref_present",
            )
        if "evidence_fp1" in entry:
            built["evidence_fp1"] = entry["evidence_fp1"]
        layers[cast("str", source)][name] = built
    missing = catalog_names - seen
    if missing:
        return invalid(
            "rows",
            "identity is missing value_status_required rows",
            missing=sorted(missing)[:10],
            missing_count=len(missing),
        )
    return Ok(layers)
