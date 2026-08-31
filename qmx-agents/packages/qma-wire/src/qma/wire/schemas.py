"""JSON Schema loaders and validators for wire families (CT-40; FR-Q13).

Schemas ship beside this package under ``schemas/`` and are the declarative
source for family shape. Validation is a focused Draft 2020-12 subset covering
the keywords used by the shipped schemas (stdlib only).
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Final, cast

from qma.wire.vocabulary import (
    WIRE_COMMANDS,
    WIRE_EVENTS,
    WIRE_QUERIES,
    MessageFamily,
    family_of,
    parse_wire_type,
)
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "SCHEMA_DIR",
    "SCHEMA_FILES",
    "SchemaValidationError",
    "family_schema_name",
    "load_schema",
    "validate_family_payload",
    "validate_instance",
    "validate_wire_envelope_dict",
]


SCHEMA_DIR: Final[Path] = Path(__file__).resolve().parents[3] / "schemas"

SCHEMA_FILES: Final[dict[str, str]] = {
    "envelope": "envelope.v1.schema.json",
    "command": "command.v1.schema.json",
    "query": "query.v1.schema.json",
    "event": "event.v1.schema.json",
    "initialize": "initialize.v1.schema.json",
    "host_request": "host_request.v1.schema.json",
}


class SchemaValidationError(ValueError):
    """Raised when an instance fails JSON Schema validation."""


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _as_object_map(value: object) -> dict[str, object] | None:
    if not isinstance(value, Mapping):
        return None
    out: dict[str, object] = {}
    for key, item in cast("Mapping[object, object]", value).items():
        if not isinstance(key, str):
            return None
        out[key] = item
    return out


def _as_object_list(value: object) -> list[object] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    return list(cast("Sequence[object]", value))


@lru_cache(maxsize=16)
def load_schema(name: str) -> dict[str, object]:
    """Load a shipped schema document by short name (``envelope``, ``command``, …)."""
    try:
        filename = SCHEMA_FILES[name]
    except KeyError as exc:
        raise SchemaValidationError(f"unknown schema {name!r}") from exc
    path = SCHEMA_DIR / filename
    if not path.is_file():
        raise SchemaValidationError(f"schema file missing: {path}")
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    mapped = _as_object_map(raw)
    if mapped is None:
        raise SchemaValidationError(f"schema root must be an object: {path}")
    return mapped


def family_schema_name(family: MessageFamily | str) -> str:
    """Map a message family to its schema short name."""
    resolved = family if isinstance(family, MessageFamily) else MessageFamily(family)
    return resolved.value


def _check_type(instance: object, expected: str, path: str) -> None:
    ok = False
    if expected == "object":
        ok = _as_object_map(instance) is not None
    elif expected == "array":
        ok = _as_object_list(instance) is not None
    elif expected == "string":
        ok = isinstance(instance, str)
    elif expected == "integer":
        ok = isinstance(instance, int) and not isinstance(instance, bool)
    elif expected == "number":
        ok = isinstance(instance, (int, float)) and not isinstance(instance, bool)
    elif expected == "boolean":
        ok = isinstance(instance, bool)
    elif expected == "null":
        ok = instance is None
    if not ok:
        type_name = type(instance).__name__
        raise SchemaValidationError(f"{path}: expected type {expected}, got {type_name}")


def _validate(instance: object, schema: Mapping[str, object], path: str = "$") -> None:
    if "const" in schema and instance != schema["const"]:
        raise SchemaValidationError(f"{path}: expected const {schema['const']!r}")
    if "enum" in schema:
        allowed = schema["enum"]
        if not isinstance(allowed, list) or instance not in allowed:
            raise SchemaValidationError(f"{path}: value not in enum")
    if "type" in schema:
        declared = schema["type"]
        if isinstance(declared, list):
            errors: list[str] = []
            for option_obj in cast("list[object]", declared):
                if not isinstance(option_obj, str):
                    continue
                try:
                    _check_type(instance, option_obj, path)
                    break
                except SchemaValidationError as exc:
                    errors.append(str(exc))
            else:
                raise SchemaValidationError(f"{path}: type mismatch ({'; '.join(errors)})")
        elif isinstance(declared, str):
            _check_type(instance, declared, path)
    if isinstance(instance, str) and "minLength" in schema:
        minimum = schema["minLength"]
        if isinstance(minimum, int) and len(instance) < minimum:
            raise SchemaValidationError(f"{path}: shorter than minLength {minimum}")
    if isinstance(instance, int) and not isinstance(instance, bool) and "minimum" in schema:
        minimum = schema["minimum"]
        if isinstance(minimum, (int, float)) and instance < minimum:
            raise SchemaValidationError(f"{path}: below minimum {minimum}")

    as_map = _as_object_map(instance)
    if as_map is not None:
        required = schema.get("required", [])
        if isinstance(required, list):
            for key_obj in cast("list[object]", required):
                if not isinstance(key_obj, str):
                    continue
                if key_obj not in as_map:
                    raise SchemaValidationError(f"{path}: missing required property {key_obj!r}")
        properties_raw = schema.get("properties")
        properties = _as_object_map(properties_raw) if properties_raw is not None else None
        if properties is not None:
            for key, value in as_map.items():
                child_schema = _as_object_map(properties.get(key))
                if child_schema is not None:
                    _validate(value, child_schema, f"{path}.{key}")
                elif schema.get("additionalProperties") is False:
                    raise SchemaValidationError(f"{path}: additional property {key!r} not allowed")
        elif schema.get("additionalProperties") is False and as_map:
            raise SchemaValidationError(f"{path}: additional properties not allowed")

    as_list = _as_object_list(instance)
    if as_list is not None:
        items = _as_object_map(schema.get("items"))
        if items is not None:
            for index, item in enumerate(as_list):
                _validate(item, items, f"{path}[{index}]")


def validate_instance(instance: object, schema_name: str) -> Result[Mapping[str, object]]:
    """Validate ``instance`` against a shipped schema; return the instance mapping."""
    schema = load_schema(schema_name)
    try:
        _validate(instance, schema)
    except SchemaValidationError as exc:
        return _invalid("schema", str(exc), schema=schema_name)
    mapped = _as_object_map(instance)
    if mapped is None:
        return _invalid("schema", "validated instance must be an object", schema=schema_name)
    return Ok(mapped)


def validate_wire_envelope_dict(instance: object) -> Result[Mapping[str, object]]:
    """Validate a wire-envelope object against ``envelope.v1.schema.json``."""
    checked = validate_instance(instance, "envelope")
    if not isinstance(checked, Ok):
        return checked
    data = checked.value
    try:
        parse_wire_type(data["type"])
    except ValueError as exc:
        return _invalid("type", str(exc))
    if "journal_seq" in data:
        return _invalid(
            "journal_seq",
            "journal_seq is never exposed on the wire and is never substituted for seq",
        )
    if "seq" in data and data["seq"] is None:
        return _invalid("seq", "absent optional seq must be omitted, never null")
    if "correlation_id" not in data and not data.get("correlation_missing"):
        return _invalid(
            "correlation_id",
            "correlation_id is required unless correlation_missing is set",
        )
    return Ok(data)


def validate_family_payload(wire_type: object, payload: object) -> Result[Mapping[str, object]]:
    """Validate a family payload object against that family's JSON Schema."""
    try:
        name = parse_wire_type(wire_type)
    except ValueError as exc:
        return _invalid("type", str(exc), given=repr(wire_type))
    family = family_of(name)
    schema_name = family_schema_name(family)
    mapped = _as_object_map(payload)
    if mapped is None:
        return _invalid("payload", "family payload must be an object")
    body: dict[str, object] = {"family": family.value, "name": name}
    if family is MessageFamily.EVENT:
        body["body"] = dict(mapped)
    else:
        body["args"] = dict(mapped)
    members = {
        MessageFamily.COMMAND: WIRE_COMMANDS,
        MessageFamily.QUERY: WIRE_QUERIES,
        MessageFamily.EVENT: WIRE_EVENTS,
    }[family]
    if name not in members:
        return _invalid("name", f"{name!r} is not a seed member of {family.value}")
    return validate_instance(body, schema_name)
