"""CT-40 additive ``selected_refs`` kind ``instance_id`` (Story 60.2; DEC-0463).

Closed kinds are parent AD-8 (Story 55.1) plus ``instance_id``. Layout JSON,
positions, widgets, and json-render trees remain refused. Inspect SHA
``34c148b`` had the parent AD-8 set and lacked ``instance_id``. No new CT.
DEC-0463 is a dated follow-up of DEC-0421; DEC-0421 is not superseded.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "ADR_0024_DECISION_REWRITTEN",
    "DEC_0421_SUPERSEDED_BY",
    "DEC_0463_FOLLOWS_DEC_0421",
    "FORBIDDEN_SELECTED_REF_KEYS",
    "INSTANCE_ID_KIND",
    "INSTANCE_ID_KIND_EXISTED_AT_INSPECT_SHA",
    "PARENT_AD8_SELECTED_REF_KINDS",
    "SELECTED_REF_CONTRACT",
    "SELECTED_REF_DTO_OWNER",
    "SELECTED_REF_INSPECT_SHA",
    "SELECTED_REF_KINDS",
    "SELECTED_REF_NEW_CT_MINTED",
    "SELECTED_REF_PARENT_KINDS_EXISTED_AT_INSPECT_SHA",
    "SELECTED_REF_REFUSED_CT",
    "SELECTED_REF_SCHEMA",
    "SELECTED_REF_SCHEMA_FILE",
    "SELECTED_REF_SCHEMA_NAME",
    "SelectedRef",
    "claim_instance_id_selected_ref_kind_at_inspect_sha",
    "parse_selected_ref",
    "parse_selected_refs",
    "parse_wire_selected_ref",
    "refuse_layout_widget_json_render_ref",
    "validate_selected_ref",
]


SELECTED_REF_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
SELECTED_REF_CONTRACT: Final[str] = "CT-40"
SELECTED_REF_NEW_CT_MINTED: Final[bool] = False
SELECTED_REF_REFUSED_CT: Final[str] = "CT-52"
SELECTED_REF_SCHEMA: Final[str] = "qma.wire.selected_ref.v1"
SELECTED_REF_SCHEMA_NAME: Final[str] = "selected_ref"
SELECTED_REF_SCHEMA_FILE: Final[str] = "selected_ref.v1.schema.json"
SELECTED_REF_INSPECT_SHA: Final[str] = "34c148b"
INSTANCE_ID_KIND: Final[str] = "instance_id"
INSTANCE_ID_KIND_EXISTED_AT_INSPECT_SHA: Final[bool] = False
SELECTED_REF_PARENT_KINDS_EXISTED_AT_INSPECT_SHA: Final[bool] = True
DEC_0463_FOLLOWS_DEC_0421: Final[str] = "DEC-0463"
DEC_0421_SUPERSEDED_BY: Final[None] = None
ADR_0024_DECISION_REWRITTEN: Final[bool] = False
PARENT_AD8_SELECTED_REF_KINDS: Final[frozenset[str]] = frozenset(
    {
        "artifact",
        "research_ref",
        "contribution",
        "template",
        "dataset",
        "run",
        "attempt",
        "node_ids",
    }
)
SELECTED_REF_KINDS: Final[frozenset[str]] = PARENT_AD8_SELECTED_REF_KINDS | {INSTANCE_ID_KIND}
FORBIDDEN_SELECTED_REF_KEYS: Final[frozenset[str]] = frozenset(
    {
        "board_layout",
        "json-render",
        "json_render",
        "layout",
        "positions",
        "tree",
        "widget",
        "widgets",
    }
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


def refuse_layout_widget_json_render_ref(**extra: object) -> TypedRefusal:
    """Layout JSON, positions, widgets, and json-render trees stay refused."""
    extra.setdefault("allowed", sorted(SELECTED_REF_KINDS))
    extra.setdefault("inspect_sha", SELECTED_REF_INSPECT_SHA)
    return _invalid(
        str(extra.pop("field", "selected_refs")),
        "layout JSON, positions, widgets, and json-render trees are refused "
        "(FR-WF-31; AD-4; DEC-0463)",
        **extra,
    )


def claim_instance_id_selected_ref_kind_at_inspect_sha(existed: object) -> Result[bool]:
    """Claiming kind ``instance_id`` existed at ``34c148b`` fails Story 60.2."""
    if existed is True or existed == "true":
        return _policy(
            "selected_refs.kind",
            "selected_refs kind instance_id did not exist at inspect SHA 34c148b "
            "(DEC-0465; NFR-PG-04; SCN-0023 Branch D)",
            existed_at_inspect_sha=False,
            inspect_sha=SELECTED_REF_INSPECT_SHA,
            parent_kinds=sorted(PARENT_AD8_SELECTED_REF_KINDS),
        )
    if existed is not False:
        return _invalid(
            "existed_at_inspect_sha",
            "inspect-SHA claim is a boolean",
            given=repr(existed),
        )
    return Ok(False)


def _require_str(field: str, value: object) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(field, f"{field} must be a non-empty string", given=repr(value))
    return Ok(value.strip())


def _as_mapping(field: str, value: object) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return _invalid(field, f"{field} must be an object")
    mapping = cast("Mapping[object, object]", value)
    out: dict[str, object] = {}
    for key, item in mapping.items():
        if not isinstance(key, str):
            return _invalid(field, f"{field} keys must be strings")
        if item is None:
            return _invalid(
                field,
                "null is prohibited; omit absent optional keys (fp1)",
                key=key,
            )
        out[key] = item
    return Ok(out)


@dataclass(frozen=True, slots=True)
class SelectedRef:
    """Typed selected ref. Layout JSON, widgets, and positions are refused."""

    kind: str
    id: str
    extra: Mapping[str, object] = field(default_factory=dict[str, object])

    def __post_init__(self) -> None:
        object.__setattr__(self, "extra", MappingProxyType(dict(self.extra)))

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {"id": self.id, "kind": self.kind}
        payload.update(dict(self.extra))
        return MappingProxyType(payload)


def parse_selected_ref(value: object) -> Result[SelectedRef]:
    mapped = _as_mapping("selected_refs", value)
    if is_refusal(mapped):
        return mapped
    body = mapped.value
    stolen = sorted(key for key in body if key.casefold() in FORBIDDEN_SELECTED_REF_KEYS)
    if stolen:
        return refuse_layout_widget_json_render_ref(forbidden=stolen)
    kind = _require_str("selected_refs.kind", body.get("kind"))
    if is_refusal(kind):
        return kind
    if kind.value not in SELECTED_REF_KINDS:
        return _invalid(
            "selected_refs.kind",
            "selected_refs kind is not in the closed AD-8 set plus instance_id",
            given=kind.value,
            allowed=sorted(SELECTED_REF_KINDS),
        )
    ident = body.get("id")
    extra = {key: item for key, item in body.items() if key not in {"kind", "id"}}
    if kind.value == "contribution" and ident is None:
        qualified = _require_str("selected_refs.qualified_id", extra.get("qualified_id"))
        if is_refusal(qualified):
            return qualified
        version = _require_str("selected_refs.package_version", extra.get("package_version"))
        if is_refusal(version):
            return version
        ident = f"{qualified.value}@{version.value}"
    if kind.value == "template" and ident is None:
        qualified = _require_str("selected_refs.qualified_id", extra.get("qualified_id"))
        if is_refusal(qualified):
            return qualified
        version = _require_str("selected_refs.version", extra.get("version"))
        if is_refusal(version):
            return version
        ident = f"{qualified.value}@{version.value}"
    parsed_id = _require_str("selected_refs.id", ident)
    if is_refusal(parsed_id):
        return parsed_id
    return Ok(SelectedRef(kind=kind.value, id=parsed_id.value, extra=extra))


def parse_selected_refs(value: object) -> Result[tuple[SelectedRef, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid("selected_refs", "selected_refs is an array of typed refs")
    collected: list[SelectedRef] = []
    for raw in cast("Sequence[object]", value):
        parsed = parse_selected_ref(raw)
        if is_refusal(parsed):
            return parsed
        collected.append(parsed.value)
    return Ok(tuple(collected))


def parse_wire_selected_ref(value: object) -> Result[SelectedRef]:
    """Parse one CT-40 selected ref. Kind ``instance_id`` is legal after Story 60.2."""
    if isinstance(value, SelectedRef):
        return Ok(value)
    return parse_selected_ref(value)


def validate_selected_ref(value: object) -> Result[SelectedRef]:
    """Schema-then-DTO validation for the additive CT-40 selected ref."""
    from qma.wire.schemas import validate_instance  # noqa: PLC0415

    if isinstance(value, SelectedRef):
        payload = dict(value.to_payload())
    elif isinstance(value, Mapping):
        payload = dict(cast("Mapping[str, object]", value))
    else:
        return parse_wire_selected_ref(value)
    checked = validate_instance(payload, SELECTED_REF_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_wire_selected_ref(checked.value)
