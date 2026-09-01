"""TN-18 node-config compiler: one fingerprinted resolved artifact.

Fixed precedence roster → BMS → Book → node defaults. No invocation or
runtime-override layer (DEC-0203, DEC-0223). Every ``value_status_required``
row carries ``blank | provisional-evidence | ratified`` on the artifact, never
in the registry (DEC-0254). The compiler refuses runtime folds, unknown keys,
registry value reads, secret values, and invented KSA/latency numbers (FTR-07).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal, cast

from qmf.core.fingerprint import Fingerprint, canonical_bytes, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal
from qmf.core.secret import SecretValue

from qmn.config._refuse import clean_token, invalid, policy
from qmn.config.registry_catalog import (
    BLANK_EFFECT_BOOT,
    BLANK_EFFECT_LIVE,
    BLANK_EFFECT_SOAK,
    EXPECTED_ROW_COUNT,
    LIVENESS_HEARTBEAT_NAMES,
    RETIRED_DEAD_MANS_SWITCH_NAMES,
    VALUE_STATUS_REQUIRED_ROWS,
    RegistryRowSchema,
    rows_by_name,
)

__all__ = [
    "COMPILE_LAYERS",
    "HAS_INVOCATION_OVERRIDE_LAYER",
    "NODE_CONFIG_ARTIFACT_NAME",
    "NODE_CONFIG_CLASS",
    "NODE_CONFIG_FORMAT_VERSION",
    "NODE_CONFIG_FORMAT_VERSION_1",
    "NODE_CONFIG_KNOWN_FORMAT_VERSIONS",
    "RUNTIME_FOLD_KEYS",
    "SECRET_REF_SUFFIXES",
    "VALUE_STATUSES",
    "VALUE_STATUS_BLANK",
    "VALUE_STATUS_PROVISIONAL",
    "VALUE_STATUS_RATIFIED",
    "ResolvedNodeConfig",
    "ResolvedValueRow",
    "compile_layers",
    "compile_node_config",
    "is_secret_ref_key",
    "layers_identity",
    "refuse_unknown_compile_layer",
    "validate_registry_row_schema",
]

COMPILE_LAYERS: Final[tuple[str, ...]] = (
    "roster",
    "bms",
    "book",
    "node_defaults",
)
HAS_INVOCATION_OVERRIDE_LAYER: Final[bool] = False

NODE_CONFIG_CLASS: Final[str] = "resolved-node-config"
NODE_CONFIG_FORMAT_VERSION_1: Final[int] = 1
NODE_CONFIG_FORMAT_VERSION: Final[int] = NODE_CONFIG_FORMAT_VERSION_1
NODE_CONFIG_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset(
    {NODE_CONFIG_FORMAT_VERSION_1}
)
NODE_CONFIG_ARTIFACT_NAME: Final[str] = "node-config.json"

VALUE_STATUS_BLANK: Final[str] = "blank"
VALUE_STATUS_PROVISIONAL: Final[str] = "provisional-evidence"
VALUE_STATUS_RATIFIED: Final[str] = "ratified"
VALUE_STATUSES: Final[frozenset[str]] = frozenset(
    {VALUE_STATUS_BLANK, VALUE_STATUS_PROVISIONAL, VALUE_STATUS_RATIFIED}
)

# Read-time folds over journals — never config keys (DEC-0203, DEC-0223).
RUNTIME_FOLD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "book_mode",
        "binding_state",
        "seat_state",
        "standing_intents",
        "standing_intent",
        "ksa_level",
        "bench_count",
        "bench_counts",
        "exposure",
        "exposures",
        "budget",
        "budgets",
        "period_loss_budget",
        "loss_runway",
    }
)

SECRET_REF_SUFFIXES: Final[tuple[str, ...]] = (
    "_token_reference",
    "_secret_reference",
    "_credential_reference",
)

_EMPTY_MAP: Final[Mapping[str, object]] = MappingProxyType({})
ValueStatus = Literal["blank", "provisional-evidence", "ratified"]


def compile_layers() -> tuple[str, ...]:
    """Fixed compile layers; never an invocation/runtime override layer."""
    return COMPILE_LAYERS


def layers_identity() -> dict[str, object]:
    """Identity-bearing compiler fields. Package SemVer is omitted."""
    return {
        "has_invocation_override_layer": HAS_INVOCATION_OVERRIDE_LAYER,
        "layer_precedence": COMPILE_LAYERS,
    }


def refuse_unknown_compile_layer(name: object) -> Result[str]:
    """Refuse any layer name outside the fixed four-layer precedence (FR-071)."""
    token = clean_token(name)
    if token is None:
        return invalid("layer", "a compile layer is a non-blank token", given=repr(name))
    if token not in COMPILE_LAYERS:
        return invalid(
            "layer",
            "unknown compile layer; only roster → bms → book → node_defaults are admitted "
            "and no invocation layer exists",
            given=token,
            allowed=list(COMPILE_LAYERS),
        )
    if token in {"invocation", "runtime", "cli", "flags"}:
        return invalid(
            "layer",
            "invocation/runtime override layers are refused (DEC-0203)",
            given=token,
        )
    return Ok(token)


def validate_registry_row_schema(row: object) -> Result[RegistryRowSchema]:
    """Refuse a catalog row missing unit/owner/status-bearing schema fields (FR-071)."""
    if not isinstance(row, Mapping):
        return invalid(
            "registry_row",
            "a registry schema row is a mapping",
            given=type(row).__name__,
        )
    body = cast("Mapping[str, object]", row)
    name = clean_token(body.get("name"))
    if name is None:
        return invalid("name", "registry row name is a non-blank token")
    owner = clean_token(body.get("owner_scope"))
    if owner is None:
        return invalid(
            name,
            "registry-schema gate refuses a row missing owner_scope",
        )
    if "units" not in body:
        return invalid(
            name,
            "registry-schema gate refuses a row missing unit_kind/units",
        )
    if body.get("configurable") is not True:
        return invalid(
            name,
            "value_status_required rows are configurable; hard-coded node values are refused",
        )
    blank_effect = body.get("blank_effect")
    if not isinstance(blank_effect, (tuple, list)):
        return invalid(
            name,
            "registry-schema gate refuses a row missing blank_effect status tags",
        )
    component = clean_token(body.get("component"))
    if component is None:
        return invalid(name, "registry row component is a non-blank token")
    type_token = clean_token(body.get("type"))
    if type_token is None:
        return invalid(name, "registry row type is a non-blank token")
    units_raw = body.get("units")
    units: str | None
    if units_raw is None:
        units = None
    else:
        units = clean_token(units_raw)
        if units is None:
            return invalid(name, "units is None or a non-blank token")
    effects = cast("Sequence[object]", blank_effect)
    schema: RegistryRowSchema = {
        "name": name,
        "component": component,
        "owner_scope": owner,
        "units": units,
        "type": type_token,
        "blank_effect": tuple(str(item) for item in effects),
        "configurable": True,
    }
    return Ok(schema)


def is_secret_ref_key(name: str) -> bool:
    """True when the variable stores a CT-21 secret reference, never a value."""
    return any(name.endswith(suffix) for suffix in SECRET_REF_SUFFIXES)


@dataclass(frozen=True, slots=True)
class ResolvedValueRow:
    """One resolved value plus its value-status on the node-config artifact."""

    name: str
    value_status: str
    source_layer: str | None
    owner_scope: str
    unit_kind: str | None
    blank_effect: tuple[str, ...]
    component: str
    configurable: bool
    value: object | None = None
    evidence_fp1: Fingerprint | None = None
    admission_impact: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "blank_effect", tuple(self.blank_effect))

    @property
    def is_blank(self) -> bool:
        return self.value_status == VALUE_STATUS_BLANK

    @property
    def blocks_boot(self) -> bool:
        return BLANK_EFFECT_BOOT in self.blank_effect and self.is_blank

    @property
    def blocks_role_live(self) -> bool:
        """Blank or provisional live-gating behaves like blank (DEC-0231)."""
        if BLANK_EFFECT_LIVE not in self.blank_effect:
            return False
        return self.value_status in {VALUE_STATUS_BLANK, VALUE_STATUS_PROVISIONAL}

    @property
    def blocks_soak(self) -> bool:
        """Soak requires at least provisional-evidence (DEC-0203)."""
        if BLANK_EFFECT_SOAK not in self.blank_effect:
            return False
        return self.value_status == VALUE_STATUS_BLANK

    def explain_value(self) -> object | str:
        """Renderable value; secret refs stay reference ids, never secret values."""
        if self.is_blank:
            return "<blank>"
        if is_secret_ref_key(self.name):
            return self.value if isinstance(self.value, str) else "<secret-ref>"
        return self.value

    def identity_entry(self) -> dict[str, object]:
        """fp1 identity for this row. Nulls and secret-ref values are omitted."""
        entry: dict[str, object] = {
            "blank_effect": list(self.blank_effect),
            "component": self.component,
            "configurable": self.configurable,
            "name": self.name,
            "owner_scope": self.owner_scope,
            "value_status": self.value_status,
        }
        if self.unit_kind is not None:
            entry["unit_kind"] = self.unit_kind
        if self.source_layer is not None:
            entry["source_layer"] = self.source_layer
        if self.admission_impact is not None:
            entry["admission_impact"] = self.admission_impact
        if self.evidence_fp1 is not None:
            entry["evidence_fp1"] = self.evidence_fp1.value
        if (
            not self.is_blank
            and self.value is not None
            and not is_secret_ref_key(self.name)
        ):
            entry["value"] = self.value
        elif not self.is_blank and is_secret_ref_key(self.name):
            # Presence only — the reference id is occurrence/display (CT-21).
            entry["secret_ref_present"] = True
        return entry


@dataclass(frozen=True, slots=True)
class ResolvedNodeConfig:
    """One fully-resolved, read-only, fingerprinted node-config (TN-18)."""

    format_version: int
    config_version: int
    rows: Mapping[str, ResolvedValueRow]
    fingerprint: Fingerprint
    roster_identity: Mapping[str, object] = _EMPTY_MAP
    branches_from: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "rows", MappingProxyType(dict(self.rows)))
        object.__setattr__(
            self, "roster_identity", MappingProxyType(dict(self.roster_identity))
        )

    def fp1_identity(self) -> dict[str, object]:
        """Identity content for ``fp1``. Display aliases and secrets omitted."""
        row_entries = [self.rows[name].identity_entry() for name in sorted(self.rows)]
        identity: dict[str, object] = {
            "class": NODE_CONFIG_CLASS,
            "config_version": self.config_version,
            "format_version": self.format_version,
            "layer_precedence": list(COMPILE_LAYERS),
            "rows": row_entries,
        }
        if self.roster_identity:
            identity["roster_identity"] = dict(self.roster_identity)
        if self.branches_from is not None:
            identity["branches_from"] = self.branches_from
        return identity

    def artifact_bytes(self) -> Result[bytes]:
        """Canonical bytes of the identity artifact."""
        return canonical_bytes(self.fp1_identity())

    def boot_blocking_rows(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, row in self.rows.items() if row.blocks_boot))

    def live_blocking_rows(self) -> tuple[str, ...]:
        return tuple(
            sorted(name for name, row in self.rows.items() if row.blocks_role_live)
        )

    def soak_blocking_rows(self) -> tuple[str, ...]:
        return tuple(sorted(name for name, row in self.rows.items() if row.blocks_soak))

    def may_boot(self) -> bool:
        return not self.boot_blocking_rows()

    def may_bind_role_live(self) -> bool:
        return not self.live_blocking_rows()

    def may_start_soak(self) -> bool:
        return not self.soak_blocking_rows()


def compile_node_config(
    *,
    roster: object = None,
    bms: object = None,
    book: object = None,
    node_defaults: object = None,
    roster_identity: object = None,
    config_version: int = 1,
    branches_from: int | None = None,
) -> Result[ResolvedNodeConfig]:
    """Compile one resolved node-config from the four fixed layers.

    Layer maps are ``name -> {value, value_status[, evidence_fp1]}``. A missing
    ``value_status_required`` name resolves as blank. Unknown keys, runtime
    folds, retired dead-man's-switch names, secret values, and multi-status
    collisions refuse. Values are never read from the registry.
    """
    if HAS_INVOCATION_OVERRIDE_LAYER:  # pragma: no cover - pinned False
        return invalid(
            "invocation",
            "the node has no invocation/runtime override layer (DEC-0203)",
        )
    if config_version < 1:
        return invalid(
            "config_version",
            "config_version is a positive integer ordinal",
            given=config_version,
        )

    parsed_layers: list[tuple[str, Mapping[str, object]]] = []
    for name, raw in (
        ("node_defaults", node_defaults),
        ("book", book),
        ("bms", bms),
        ("roster", roster),
    ):
        layer = _as_layer(raw, name)
        if is_refusal(layer):
            return layer
        parsed_layers.append((name, layer.value))

    catalog = rows_by_name()
    if len(catalog) != EXPECTED_ROW_COUNT:
        return invalid(
            "registry_catalog",
            "value_status_required catalog must contain exactly 71 rows",
            given=len(catalog),
        )

    for _layer_name, layer_map in parsed_layers:
        refused = _refuse_layer_keys(layer_map, catalog)
        if refused is not None:
            return refused

    identity = _as_roster_identity(roster_identity)
    if is_refusal(identity):
        return identity

    resolved: dict[str, ResolvedValueRow] = {}
    for schema in VALUE_STATUS_REQUIRED_ROWS:
        row = _resolve_row(schema, parsed_layers)
        if is_refusal(row):
            return row
        resolved[schema["name"]] = row.value

    return _finish(
        rows=resolved,
        roster_identity=identity.value,
        config_version=config_version,
        branches_from=branches_from,
    )


def _finish(
    *,
    rows: Mapping[str, ResolvedValueRow],
    roster_identity: Mapping[str, object],
    config_version: int,
    branches_from: int | None,
) -> Result[ResolvedNodeConfig]:
    provisional = ResolvedNodeConfig(
        format_version=NODE_CONFIG_FORMAT_VERSION,
        config_version=config_version,
        rows=rows,
        fingerprint=Fingerprint(value="fp1:sha256:" + ("0" * 64)),
        roster_identity=roster_identity,
        branches_from=branches_from,
    )
    fp = fingerprint(provisional.fp1_identity())
    if is_refusal(fp):
        return fp
    return Ok(
        ResolvedNodeConfig(
            format_version=NODE_CONFIG_FORMAT_VERSION,
            config_version=config_version,
            rows=rows,
            fingerprint=fp.value,
            roster_identity=roster_identity,
            branches_from=branches_from,
        )
    )


def _resolve_row(
    schema: RegistryRowSchema,
    layers_low_to_high: Sequence[tuple[str, Mapping[str, object]]],
) -> Result[ResolvedValueRow]:
    name = schema["name"]
    chosen_layer: str | None = None
    chosen_entry: Mapping[str, object] | None = None
    for layer_name, layer_map in layers_low_to_high:
        if name in layer_map:
            chosen_layer = layer_name
            raw_entry = layer_map[name]
            if not isinstance(raw_entry, Mapping):
                return invalid(
                    name,
                    "a layer entry is a mapping with value and value_status",
                    given=repr(type(raw_entry).__name__),
                )
            chosen_entry = cast("Mapping[str, object]", raw_entry)

    if chosen_entry is None:
        return Ok(
            ResolvedValueRow(
                name=name,
                value=None,
                value_status=VALUE_STATUS_BLANK,
                source_layer=None,
                owner_scope=schema["owner_scope"],
                unit_kind=schema["units"],
                blank_effect=tuple(schema["blank_effect"]),
                component=schema["component"],
                configurable=schema["configurable"],
            )
        )

    status = clean_token(chosen_entry.get("value_status"))
    if status not in VALUE_STATUSES:
        return invalid(
            name,
            "value_status is blank | provisional-evidence | ratified",
            given=repr(chosen_entry.get("value_status")),
        )
    if "value" not in chosen_entry and status != VALUE_STATUS_BLANK:
        return invalid(
            name,
            "a non-blank value_status requires a value field",
            value_status=status,
        )
    if status == VALUE_STATUS_BLANK:
        if chosen_entry.get("value") is not None:
            return invalid(
                name,
                "a blank value_status omits value (null is never stored)",
            )
        return Ok(
            ResolvedValueRow(
                name=name,
                value=None,
                value_status=VALUE_STATUS_BLANK,
                source_layer=chosen_layer,
                owner_scope=schema["owner_scope"],
                unit_kind=schema["units"],
                blank_effect=tuple(schema["blank_effect"]),
                component=schema["component"],
                configurable=schema["configurable"],
            )
        )

    value = chosen_entry.get("value")
    if value is None:
        return invalid(
            name,
            "null is prohibited; omit the value or use value_status blank",
        )
    if isinstance(value, SecretValue):
        return policy(
            name,
            "secret values never enter the node-config artifact (CT-21)",
        )
    if isinstance(value, float):
        return invalid(
            name,
            "binary floating point is banned on the money/config path",
            given=repr(value),
        )

    evidence: Fingerprint | None = None
    if status == VALUE_STATUS_PROVISIONAL:
        raw_evidence = chosen_entry.get("evidence_fp1")
        if raw_evidence is None:
            return invalid(
                name,
                "provisional-evidence requires evidence_fp1 citation",
            )
        parsed = _as_fingerprint(raw_evidence, "evidence_fp1")
        if is_refusal(parsed):
            return parsed
        evidence = parsed.value
    elif "evidence_fp1" in chosen_entry:
        parsed = _as_fingerprint(chosen_entry.get("evidence_fp1"), "evidence_fp1")
        if is_refusal(parsed):
            return parsed
        evidence = parsed.value

    return Ok(
        ResolvedValueRow(
            name=name,
            value=value,
            value_status=status,
            source_layer=chosen_layer,
            owner_scope=schema["owner_scope"],
            unit_kind=schema["units"],
            blank_effect=tuple(schema["blank_effect"]),
            component=schema["component"],
            configurable=schema["configurable"],
            evidence_fp1=evidence,
        )
    )


def _refuse_layer_keys(
    layer_map: Mapping[str, object],
    catalog: Mapping[str, RegistryRowSchema],
) -> TypedRefusal | None:
    for key in layer_map:
        if key in RETIRED_DEAD_MANS_SWITCH_NAMES:
            return invalid(
                key,
                "dead_mans_switch_* names are retired; use liveness_heartbeat_* "
                "(DEC-0261)",
                required=sorted(LIVENESS_HEARTBEAT_NAMES),
            )
        if key in RUNTIME_FOLD_KEYS:
            return invalid(
                key,
                "runtime folds do not enter the node-config artifact (DEC-0223)",
            )
        if key not in catalog:
            return invalid(
                key,
                "compiler refuses any key with no value_status_required registry "
                "declaration; values are never read from the registry",
            )
    return None


def _as_layer(raw: object, field: str) -> Result[Mapping[str, object]]:
    if raw is None:
        return Ok({})
    if not isinstance(raw, Mapping):
        return invalid(
            field,
            "a config layer is a name->entry mapping",
            given=repr(type(raw).__name__),
        )
    return Ok(cast("Mapping[str, object]", raw))


def _as_roster_identity(raw: object) -> Result[Mapping[str, object]]:
    if raw is None:
        return Ok({})
    if not isinstance(raw, Mapping):
        return invalid(
            "roster_identity",
            "roster identity is a mapping of eligibility/identity fields",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    for key, value in body.items():
        if value is None:
            return invalid(
                "roster_identity",
                "null is prohibited in identity content; omit the key instead",
                key=key,
            )
        if isinstance(value, SecretValue):
            return policy(
                "roster_identity",
                "secret values never enter roster identity (CT-21)",
                key=key,
            )
        if isinstance(value, float):
            return invalid(
                "roster_identity",
                "binary floating point is banned in roster identity",
                key=key,
            )
    return Ok(body)


def _as_fingerprint(raw: object, field: str) -> Result[Fingerprint]:
    if isinstance(raw, Fingerprint):
        return Ok(raw)
    return Fingerprint.try_create(raw)
