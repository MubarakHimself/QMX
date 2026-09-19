"""Versioned public-operation descriptor (Workflows AD-3; CONTRACTS §1; RC-16).

Every public operation publishes the complete field catalogue. Cardinality is
two fields ``one`` | ``many``. Collection mapping is not on this descriptor
(AD-5). This surface did not exist as wired product at inspect SHA 270e992 /
580b49a (DEC-0450; GAP-0096). No new CT is minted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qma.core.vocabulary.enums import (
    DoorAdapter,
    EffectClass,
    EmptyPolicy,
    LifecycleVerb,
    OperationCardinality,
    OperationPlacement,
    OutputShape,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "ERROR_REFUSAL_FAMILY",
    "FORBIDDEN_DESCRIPTOR_FIELDS",
    "FORBIDDEN_OPERATOR_CLI_ADAPTERS",
    "OPERATION_DESCRIPTOR_CONTRACT",
    "OPERATION_DESCRIPTOR_FIELDS",
    "OPERATION_DESCRIPTOR_INSPECT_SHAS",
    "OPERATION_DESCRIPTOR_NEW_CT_MINTED",
    "OPERATION_DESCRIPTOR_OWNER",
    "OPERATION_DESCRIPTOR_WIRED_AT_INSPECT_SHA",
    "OPERATOR_CLI_ADAPTER",
    "REQUIRED_REFUSAL_CODES",
    "ErrorRefusalShape",
    "OperationConfiguration",
    "OperationDescriptor",
    "ResourceNeeds",
    "SupportedDoor",
    "parse_operation_descriptor",
    "publish_operation_descriptor",
]


OPERATION_DESCRIPTOR_OWNER: Final[str] = "COMP-QMA-CORE"
OPERATION_DESCRIPTOR_CONTRACT: Final[str] = "CONTRACTS §1"
OPERATION_DESCRIPTOR_INSPECT_SHAS: Final[tuple[str, ...]] = ("270e992", "580b49a")
OPERATION_DESCRIPTOR_WIRED_AT_INSPECT_SHA: Final[bool] = False
OPERATION_DESCRIPTOR_NEW_CT_MINTED: Final[bool] = False
ERROR_REFUSAL_FAMILY: Final[str] = "CT-04"
OPERATOR_CLI_ADAPTER: Final[str] = DoorAdapter.QMB_CLI.value
OPERATOR_CLI_OWNERS: Final[frozenset[str]] = frozenset({"COMP-QMB"})
FORBIDDEN_OPERATOR_CLI_ADAPTERS: Final[frozenset[str]] = frozenset({"qma-cli", "qmn-cli"})

OPERATION_DESCRIPTOR_FIELDS: Final[tuple[str, ...]] = (
    "op_id",
    "owner",
    "version",
    "input_schema",
    "output_shape",
    "input_cardinality",
    "output_cardinality",
    "empty_policy",
    "configuration",
    "declared_operation_dependencies",
    "resource_needs",
    "documentation_refs",
    "validation_class",
    "units",
    "compatibility",
    "effect_class",
    "permission_requests",
    "placement",
    "error_refusal_shape",
    "progress",
    "lifecycle_verbs",
    "supported_doors",
)
FORBIDDEN_DESCRIPTOR_FIELDS: Final[frozenset[str]] = frozenset({"cardinality", "mapping"})
REQUIRED_REFUSAL_CODES: Final[frozenset[str]] = frozenset(
    {
        "INVALID_INPUT",
        "UNAVAILABLE",
        "UNSUPPORTED_DOOR",
        "STALE_OBSERVATION",
        "GRANT_MISMATCH",
    }
)
_RESOURCE_NEED_KEYS: Final[frozenset[str]] = frozenset(
    {"occupancy", "memory_class", "requires_environment"}
)
_CONFIGURATION_KEYS: Final[frozenset[str]] = frozenset(
    {"defaults", "required_keys", "optional_keys"}
)
_ERROR_SHAPE_KEYS: Final[frozenset[str]] = frozenset({"family", "codes"})


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _parse_enum[EnumT: StrEnum](enum_type: type[EnumT], field: str, value: object) -> Result[EnumT]:
    try:
        return Ok(parse_closed(enum_type, value))
    except VocabularyError as exc:
        return _invalid(field, str(exc), given=repr(value))


def _require_str(field: str, value: object, *, allow_empty: bool = False) -> Result[str]:
    if not isinstance(value, str):
        return _invalid(field, f"{field} must be a string", given=repr(value))
    if not allow_empty and value.strip() == "":
        return _invalid(field, f"{field} must be a non-empty string")
    return Ok(value if allow_empty else value.strip())


def _require_str_tuple(field: str, value: object) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, str) or not isinstance(value, Sequence):
        return _invalid(field, f"{field} must be a sequence of strings")
    items: list[str] = []
    for item in cast("Sequence[object]", value):
        if not isinstance(item, str) or item.strip() == "":
            return _invalid(field, f"{field} entries must be non-empty strings", given=repr(item))
        items.append(item)
    return Ok(tuple(items))


def _as_mapping(field: str, value: object) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return _invalid(field, f"{field} must be an object")
    mapping = cast("Mapping[object, object]", value)
    return Ok({str(key): item for key, item in mapping.items()})


@dataclass(frozen=True, slots=True)
class OperationConfiguration:
    """Descriptor configuration: defaults plus required/optional keys."""

    defaults: Mapping[str, object]
    required_keys: tuple[str, ...]
    optional_keys: tuple[str, ...]

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "defaults": dict(self.defaults),
                "required_keys": list(self.required_keys),
                "optional_keys": list(self.optional_keys),
            }
        )


@dataclass(frozen=True, slots=True)
class ResourceNeeds:
    """Declared occupancy, memory class, and environment need."""

    occupancy: str
    memory_class: str
    requires_environment: bool

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "occupancy": self.occupancy,
                "memory_class": self.memory_class,
                "requires_environment": self.requires_environment,
            }
        )


@dataclass(frozen=True, slots=True)
class ErrorRefusalShape:
    """CT-04 refusal family plus the required code catalogue."""

    family: str
    codes: tuple[str, ...]

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType({"family": self.family, "codes": list(self.codes)})


@dataclass(frozen=True, slots=True)
class SupportedDoor:
    """One adapter/door pair recorded on an operation descriptor."""

    adapter: DoorAdapter
    door: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType({"adapter": self.adapter.value, "door": self.door})


@dataclass(frozen=True, slots=True)
class OperationDescriptor:
    """Complete versioned public-operation descriptor (CONTRACTS §1)."""

    op_id: str
    owner: str
    version: int
    input_schema: str
    output_shape: OutputShape
    input_cardinality: OperationCardinality
    output_cardinality: OperationCardinality
    empty_policy: EmptyPolicy
    configuration: OperationConfiguration
    declared_operation_dependencies: tuple[str, ...]
    resource_needs: ResourceNeeds
    documentation_refs: tuple[str, ...]
    validation_class: str
    units: str | None
    compatibility: Mapping[str, str]
    effect_class: EffectClass
    permission_requests: tuple[str, ...]
    placement: OperationPlacement
    error_refusal_shape: ErrorRefusalShape
    progress: bool
    lifecycle_verbs: tuple[LifecycleVerb, ...]
    supported_doors: tuple[SupportedDoor, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "compatibility", MappingProxyType(dict(self.compatibility)))

    @property
    def door_key(self) -> tuple[str, int]:
        """Normative door-matrix key: ``op_id`` + ``version``, never owner."""
        return (self.op_id, self.version)

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "op_id": self.op_id,
            "owner": self.owner,
            "version": self.version,
            "input_schema": self.input_schema,
            "output_shape": self.output_shape.value,
            "input_cardinality": self.input_cardinality.value,
            "output_cardinality": self.output_cardinality.value,
            "empty_policy": self.empty_policy.value,
            "configuration": dict(self.configuration.to_payload()),
            "declared_operation_dependencies": list(self.declared_operation_dependencies),
            "resource_needs": dict(self.resource_needs.to_payload()),
            "documentation_refs": list(self.documentation_refs),
            "validation_class": self.validation_class,
            "units": self.units,
            "compatibility": dict(self.compatibility),
            "effect_class": self.effect_class.value,
            "permission_requests": list(self.permission_requests),
            "placement": self.placement.value,
            "error_refusal_shape": dict(self.error_refusal_shape.to_payload()),
            "progress": self.progress,
            "lifecycle_verbs": [verb.value for verb in self.lifecycle_verbs],
            "supported_doors": [dict(door.to_payload()) for door in self.supported_doors],
        }
        return MappingProxyType(payload)

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> Result[OperationDescriptor]:
        return parse_operation_descriptor(payload)

    @classmethod
    def try_create(cls, **fields: object) -> Result[OperationDescriptor]:
        return parse_operation_descriptor(fields)


def parse_operation_descriptor(payload: object) -> Result[OperationDescriptor]:
    """Parse a complete CONTRACTS §1 descriptor; refuse fragments and merges."""
    if not isinstance(payload, Mapping):
        return _invalid("descriptor", "operation descriptor must be an object")
    mapping = cast("Mapping[object, object]", payload)
    body = {str(key): value for key, value in mapping.items()}
    for forbidden in FORBIDDEN_DESCRIPTOR_FIELDS:
        if forbidden in body:
            if forbidden == "cardinality":
                return _invalid(
                    "cardinality",
                    "input_cardinality and output_cardinality are separate "
                    "one|many fields; a merged cardinality field is refused "
                    "(FR-WF-15; RC-16)",
                )
            return _invalid(
                "mapping",
                "collection mapping is not on the operation descriptor (AD-5; FR-WF-15)",
            )
    missing = [field for field in OPERATION_DESCRIPTOR_FIELDS if field not in body]
    if missing:
        return _invalid(
            "descriptor",
            "CONTRACTS §1 field catalogue is incomplete (RC-16; FR-WF-14)",
            missing=missing,
        )

    op_id = _require_str("op_id", body["op_id"])
    if not isinstance(op_id, Ok):
        return op_id
    owner = _require_str("owner", body["owner"])
    if not isinstance(owner, Ok):
        return owner
    if not owner.value.startswith("COMP-"):
        return _invalid("owner", "owner must be a COMP-* id", given=owner.value)
    version_raw = body["version"]
    if not isinstance(version_raw, int) or isinstance(version_raw, bool) or version_raw < 1:
        return _invalid("version", "version must be a positive integer", given=repr(version_raw))
    input_schema = _require_str("input_schema", body["input_schema"])
    if not isinstance(input_schema, Ok):
        return input_schema
    output_shape = _parse_enum(OutputShape, "output_shape", body["output_shape"])
    if not isinstance(output_shape, Ok):
        return output_shape
    input_cardinality = _parse_enum(
        OperationCardinality, "input_cardinality", body["input_cardinality"]
    )
    if not isinstance(input_cardinality, Ok):
        return input_cardinality
    output_cardinality = _parse_enum(
        OperationCardinality, "output_cardinality", body["output_cardinality"]
    )
    if not isinstance(output_cardinality, Ok):
        return output_cardinality
    empty_policy = _parse_enum(EmptyPolicy, "empty_policy", body["empty_policy"])
    if not isinstance(empty_policy, Ok):
        return empty_policy
    configuration = _parse_configuration(body["configuration"])
    if not isinstance(configuration, Ok):
        return configuration
    dependencies = _require_str_tuple(
        "declared_operation_dependencies", body["declared_operation_dependencies"]
    )
    if not isinstance(dependencies, Ok):
        return dependencies
    resource_needs = _parse_resource_needs(body["resource_needs"])
    if not isinstance(resource_needs, Ok):
        return resource_needs
    documentation_refs = _require_str_tuple("documentation_refs", body["documentation_refs"])
    if not isinstance(documentation_refs, Ok):
        return documentation_refs
    validation_class = _require_str("validation_class", body["validation_class"])
    if not isinstance(validation_class, Ok):
        return validation_class
    units_raw = body["units"]
    if units_raw is None:
        units: str | None = None
    elif isinstance(units_raw, str) and units_raw.strip():
        units = units_raw.strip()
    else:
        return _invalid("units", "units must be a string or null", given=repr(units_raw))
    compatibility = _parse_compatibility(body["compatibility"])
    if not isinstance(compatibility, Ok):
        return compatibility
    effect_class = _parse_enum(EffectClass, "effect_class", body["effect_class"])
    if not isinstance(effect_class, Ok):
        return effect_class
    permission_requests = _require_str_tuple("permission_requests", body["permission_requests"])
    if not isinstance(permission_requests, Ok):
        return permission_requests
    placement = _parse_enum(OperationPlacement, "placement", body["placement"])
    if not isinstance(placement, Ok):
        return placement
    error_shape = _parse_error_refusal_shape(body["error_refusal_shape"])
    if not isinstance(error_shape, Ok):
        return error_shape
    progress_raw = body["progress"]
    if not isinstance(progress_raw, bool):
        return _invalid("progress", "progress must be a boolean", given=repr(progress_raw))
    lifecycle_verbs = _parse_lifecycle_verbs(body["lifecycle_verbs"])
    if not isinstance(lifecycle_verbs, Ok):
        return lifecycle_verbs
    supported_doors = _parse_supported_doors(
        body["supported_doors"], owner=owner.value, op_id=op_id.value
    )
    if not isinstance(supported_doors, Ok):
        return supported_doors
    return Ok(
        OperationDescriptor(
            op_id=op_id.value,
            owner=owner.value,
            version=version_raw,
            input_schema=input_schema.value,
            output_shape=output_shape.value,
            input_cardinality=input_cardinality.value,
            output_cardinality=output_cardinality.value,
            empty_policy=empty_policy.value,
            configuration=configuration.value,
            declared_operation_dependencies=dependencies.value,
            resource_needs=resource_needs.value,
            documentation_refs=documentation_refs.value,
            validation_class=validation_class.value,
            units=units,
            compatibility=compatibility.value,
            effect_class=effect_class.value,
            permission_requests=permission_requests.value,
            placement=placement.value,
            error_refusal_shape=error_shape.value,
            progress=progress_raw,
            lifecycle_verbs=lifecycle_verbs.value,
            supported_doors=supported_doors.value,
        )
    )


def publish_operation_descriptor(payload: object) -> Result[OperationDescriptor]:
    """Publish a public operation by validating the complete descriptor."""
    return parse_operation_descriptor(payload)


def _parse_configuration(raw: object) -> Result[OperationConfiguration]:
    mapped = _as_mapping("configuration", raw)
    if not isinstance(mapped, Ok):
        return mapped
    body = mapped.value
    extra = set(body) - _CONFIGURATION_KEYS
    if extra:
        return _invalid("configuration", "unknown configuration keys", extra=sorted(extra))
    for key in ("defaults", "required_keys", "optional_keys"):
        if key not in body:
            return _invalid("configuration", f"configuration.{key} is required")
    defaults_mapped = _as_mapping("configuration.defaults", body["defaults"])
    if not isinstance(defaults_mapped, Ok):
        return defaults_mapped
    required = _require_str_tuple("configuration.required_keys", body["required_keys"])
    if not isinstance(required, Ok):
        return required
    optional = _require_str_tuple("configuration.optional_keys", body["optional_keys"])
    if not isinstance(optional, Ok):
        return optional
    overlap = set(required.value) & set(optional.value)
    if overlap:
        return _invalid(
            "configuration",
            "required_keys and optional_keys must not overlap",
            overlap=sorted(overlap),
        )
    return Ok(
        OperationConfiguration(
            defaults=MappingProxyType(defaults_mapped.value),
            required_keys=required.value,
            optional_keys=optional.value,
        )
    )


def _parse_resource_needs(raw: object) -> Result[ResourceNeeds]:
    mapped = _as_mapping("resource_needs", raw)
    if not isinstance(mapped, Ok):
        return mapped
    body = mapped.value
    extra = set(body) - _RESOURCE_NEED_KEYS
    if extra:
        return _invalid("resource_needs", "unknown resource_needs keys", extra=sorted(extra))
    occupancy = _require_str("resource_needs.occupancy", body.get("occupancy"))
    if not isinstance(occupancy, Ok):
        return occupancy
    memory_class = _require_str("resource_needs.memory_class", body.get("memory_class"))
    if not isinstance(memory_class, Ok):
        return memory_class
    requires = body.get("requires_environment")
    if not isinstance(requires, bool):
        return _invalid(
            "resource_needs.requires_environment",
            "requires_environment must be a boolean",
            given=repr(requires),
        )
    return Ok(
        ResourceNeeds(
            occupancy=occupancy.value,
            memory_class=memory_class.value,
            requires_environment=requires,
        )
    )


def _parse_compatibility(raw: object) -> Result[Mapping[str, str]]:
    mapped = _as_mapping("compatibility", raw)
    if not isinstance(mapped, Ok):
        return mapped
    items: dict[str, str] = {}
    for key, value in mapped.value.items():
        if not key.strip():
            return _invalid("compatibility", "compatibility keys must be non-empty")
        if not isinstance(value, str) or value.strip() == "":
            return _invalid(
                "compatibility",
                "compatibility values must be non-empty strings",
                key=key,
            )
        items[key] = value
    return Ok(MappingProxyType(items))


def _parse_error_refusal_shape(raw: object) -> Result[ErrorRefusalShape]:
    mapped = _as_mapping("error_refusal_shape", raw)
    if not isinstance(mapped, Ok):
        return mapped
    body = mapped.value
    extra = set(body) - _ERROR_SHAPE_KEYS
    if extra:
        return _invalid(
            "error_refusal_shape", "unknown error_refusal_shape keys", extra=sorted(extra)
        )
    family = _require_str("error_refusal_shape.family", body.get("family"))
    if not isinstance(family, Ok):
        return family
    if family.value != ERROR_REFUSAL_FAMILY:
        return _invalid(
            "error_refusal_shape.family",
            "error_refusal_shape.family is CT-04; do not mint a new CT",
            given=family.value,
        )
    codes = _require_str_tuple("error_refusal_shape.codes", body.get("codes"))
    if not isinstance(codes, Ok):
        return codes
    missing = REQUIRED_REFUSAL_CODES - set(codes.value)
    if missing:
        return _invalid(
            "error_refusal_shape.codes",
            "codes must include INVALID_INPUT, UNAVAILABLE, UNSUPPORTED_DOOR, "
            "STALE_OBSERVATION, GRANT_MISMATCH (FR-WF-16)",
            missing=sorted(missing),
        )
    return Ok(ErrorRefusalShape(family=family.value, codes=codes.value))


def _parse_lifecycle_verbs(raw: object) -> Result[tuple[LifecycleVerb, ...]]:
    if isinstance(raw, str) or not isinstance(raw, Sequence):
        return _invalid("lifecycle_verbs", "lifecycle_verbs must be a sequence")
    verbs: list[LifecycleVerb] = []
    seen: set[LifecycleVerb] = set()
    for item in cast("Sequence[object]", raw):
        parsed = _parse_enum(LifecycleVerb, "lifecycle_verbs", item)
        if not isinstance(parsed, Ok):
            return parsed
        if parsed.value not in seen:
            verbs.append(parsed.value)
            seen.add(parsed.value)
    if not verbs:
        return _invalid("lifecycle_verbs", "lifecycle_verbs must not be empty")
    return Ok(tuple(verbs))


def _parse_supported_doors(
    raw: object, *, owner: str, op_id: str
) -> Result[tuple[SupportedDoor, ...]]:
    if isinstance(raw, str) or not isinstance(raw, Sequence):
        return _invalid("supported_doors", "supported_doors must be a sequence of {adapter, door}")
    doors: list[SupportedDoor] = []
    seen: set[tuple[str, str]] = set()
    for item in cast("Sequence[object]", raw):
        if not isinstance(item, Mapping):
            return _invalid(
                "supported_doors",
                "each supported door must be {adapter, door}",
                given=repr(item),
            )
        body = {str(key): value for key, value in cast("Mapping[object, object]", item).items()}
        adapter_raw = body.get("adapter")
        if isinstance(adapter_raw, str) and adapter_raw in FORBIDDEN_OPERATOR_CLI_ADAPTERS:
            return _policy(
                "supported_doors",
                "QMB remains the only operator CLI; QMA and QMN ship no operator CLI "
                "(FR-WF-26; RC-17)",
                adapter=adapter_raw,
                op_id=op_id,
                owner=owner,
            )
        adapter = _parse_enum(DoorAdapter, "supported_doors.adapter", adapter_raw)
        if not isinstance(adapter, Ok):
            return adapter
        door = _require_str("supported_doors.door", body.get("door"))
        if not isinstance(door, Ok):
            return door
        if adapter.value is DoorAdapter.QMB_CLI and owner not in OPERATOR_CLI_OWNERS:
            return _policy(
                "supported_doors",
                "QMB remains the only operator CLI; non-QMB owners cannot advertise "
                "qmb-cli (FR-WF-26; RC-17)",
                adapter=adapter.value.value,
                owner=owner,
                op_id=op_id,
            )
        key = (adapter.value.value, door.value)
        if key in seen:
            return _invalid(
                "supported_doors", "duplicate supported door", door=key[1], adapter=key[0]
            )
        seen.add(key)
        doors.append(SupportedDoor(adapter=adapter.value, door=door.value))
    if not doors:
        return _invalid("supported_doors", "supported_doors must not be empty")
    return Ok(tuple(doors))
