"""Leaf Stage 0 field admitters (cites, graph, evidence, labels)."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import Final, TypeVar, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid
from qml.research.stage0 import (
    GRAPH_MEANING_KINDS,
    GRAPH_PLANE,
    DictionaryCite,
    EvidenceClaim,
    Graph,
    RoleBinding,
)

__all__ = [
    "admit_bindings",
    "admit_cites",
    "admit_evidence",
    "admit_graph",
    "admit_label_map",
    "admit_string_tuple",
    "optional_string",
]

T = TypeVar("T")

_EMPTY_F: Final[Mapping[str, str]] = MappingProxyType({})
_FIELD_EVIDENCE: Final[str] = "evidence"
_FIELD_MEANING: Final[str] = "meaning"
_FIELD_PLANE: Final[str] = "plane"
_FIELD_GRAPH: Final[str] = "graph"
_MAPPING_STR_OBJECT = Mapping[str, object]
_MEANING_REASON: Final[str] = "graph meaning kinds are boolean, temporal, and lifecycle"
_PLANE_REASON: Final[str] = "graph plane is the hypothesis plane"


def admit_cites(value: object) -> Result[tuple[DictionaryCite, ...]]:
    return _admit_sequence(
        value,
        field="dictionary_cites",
        reason="dictionary cites are a sequence of {file_path, id} locators",
        admit_one=_admit_cite,
    )


def admit_bindings(value: object) -> Result[tuple[RoleBinding, ...]]:
    return _admit_sequence(
        value,
        field="role_bindings",
        reason="role bindings are a sequence of {cite, role}",
        admit_one=_admit_binding,
    )


def admit_evidence(value: object) -> Result[tuple[EvidenceClaim, ...]]:
    return _admit_sequence(
        value,
        field=_FIELD_EVIDENCE,
        reason="evidence is a sequence of source-faithful claims (not CT-32)",
        admit_one=_admit_claim,
    )


def admit_graph(value: object) -> Result[Graph]:
    if value is None:
        return Ok(Graph())
    if isinstance(value, Graph):
        return _checked_graph(value)
    if isinstance(value, Mapping):
        return _admit_graph_mapping(cast(_MAPPING_STR_OBJECT, value))
    return invalid(
        _FIELD_GRAPH,
        "graph is Boolean/temporal/lifecycle meaning",
        given=type(value).__name__,
    )


def admit_string_tuple(value: object, *, field: str) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, str):
        token = value.strip()
        return Ok((token,) if token else ())
    return _admit_string_sequence(value, field=field)


def admit_label_map(
    value: object,
    *,
    field: str,
    allowed: frozenset[str] | None,
) -> Result[Mapping[str, str]]:
    if value is None:
        return Ok(_EMPTY_F)
    if not isinstance(value, Mapping):
        return invalid(field, f"{field} is a string-to-string map", given=type(value).__name__)
    built = _build_label_map(
        cast("Mapping[object, object]", value),
        field=field,
        allowed=allowed,
    )
    if is_refusal(built):
        return built
    return Ok(MappingProxyType(built.value))


def optional_string(value: object, *, field: str) -> Result[str | None]:
    if value is None:
        return Ok(None)
    if not isinstance(value, str) or value.strip() == "":
        return invalid(field, f"{field} is a non-empty string when present", given=repr(value))
    return Ok(value.strip())


def _admit_string_sequence(value: object, *, field: str) -> Result[tuple[str, ...]]:
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return invalid(field, f"{field} is a sequence of strings", given=type(value).__name__)
    out: list[str] = []
    for item in cast("Sequence[object]", value):
        if not isinstance(item, str) or item.strip() == "":
            return invalid(field, f"{field} entries are non-empty strings", given=repr(item))
        out.append(item.strip())
    return Ok(tuple(out))


def _admit_sequence(
    value: object,
    *,
    field: str,
    reason: str,
    admit_one: Callable[[object], Result[T]],
) -> Result[tuple[T, ...]]:
    if value is None:
        return Ok(())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(field, reason, given=type(value).__name__)
    out: list[T] = []
    for item in cast("Sequence[object]", value):
        admitted = admit_one(item)
        if is_refusal(admitted):
            return admitted
        out.append(admitted.value)
    return Ok(tuple(out))


def _admit_cite(value: object) -> Result[DictionaryCite]:
    if isinstance(value, DictionaryCite):
        return Ok(value)
    if isinstance(value, Mapping):
        return _admit_cite_mapping(cast(_MAPPING_STR_OBJECT, value))
    return invalid(
        "dictionary_cites",
        "a dictionary cite is {file_path, id}",
        given=type(value).__name__,
    )


def _admit_cite_mapping(mapping: _MAPPING_STR_OBJECT) -> Result[DictionaryCite]:
    path = mapping.get("file_path")
    entry_id = mapping.get("id")
    if not isinstance(path, str) or path.strip() == "":
        return invalid(
            "file_path",
            "dictionary cite file_path is a non-empty string",
            given=repr(path),
        )
    if not isinstance(entry_id, str) or entry_id.strip() == "":
        return invalid(
            "id",
            "dictionary cite id is a non-empty string",
            given=repr(entry_id),
        )
    return Ok(DictionaryCite(file_path=path.replace("\\", "/").strip(), id=entry_id.strip()))


def _admit_binding(value: object) -> Result[RoleBinding]:
    if isinstance(value, RoleBinding):
        return Ok(value)
    if isinstance(value, Mapping):
        return _admit_binding_mapping(cast(_MAPPING_STR_OBJECT, value))
    return invalid(
        "role_bindings",
        "a role binding is {cite, role}",
        given=type(value).__name__,
    )


def _admit_binding_mapping(mapping: _MAPPING_STR_OBJECT) -> Result[RoleBinding]:
    cite = _admit_cite(mapping.get("cite"))
    if is_refusal(cite):
        return cite
    role = mapping.get("role")
    if not isinstance(role, str) or role.strip() == "":
        return invalid(
            "role",
            "Stage 0 role bindings keep open eligible roles; role is a non-empty string",
            given=repr(role),
        )
    return Ok(RoleBinding(cite=cite.value, role=role.casefold().strip()))


def _admit_graph_mapping(mapping: _MAPPING_STR_OBJECT) -> Result[Graph]:
    if "confluence" in mapping or "Confluence" in mapping:
        return invalid(
            _FIELD_GRAPH,
            "Stage 0 composition field/type is graph; Confluence stays CT-34",
            given="confluence",
        )
    parts = _admit_graph_parts(mapping)
    if is_refusal(parts):
        return parts
    operators, meaning = parts.value
    return Ok(Graph(operators=operators, meaning=meaning, plane=GRAPH_PLANE))


def _admit_graph_parts(
    mapping: _MAPPING_STR_OBJECT,
) -> Result[tuple[tuple[str, ...], tuple[str, ...]]]:
    operators = admit_string_tuple(mapping.get("operators", ()), field="operators")
    if is_refusal(operators):
        return operators
    meaning_plane = _admit_meaning_and_plane(mapping)
    if is_refusal(meaning_plane):
        return meaning_plane
    meaning, _plane = meaning_plane.value
    return Ok((operators.value, meaning))


def _admit_meaning_and_plane(
    mapping: _MAPPING_STR_OBJECT,
) -> Result[tuple[tuple[str, ...], str]]:
    meaning = _admit_checked_meaning(mapping.get(_FIELD_MEANING, ()))
    if is_refusal(meaning):
        return meaning
    plane = _admit_plane(mapping.get(_FIELD_PLANE, GRAPH_PLANE))
    if is_refusal(plane):
        return plane
    return Ok((meaning.value, plane.value))


def _admit_checked_meaning(value: object) -> Result[tuple[str, ...]]:
    meaning = admit_string_tuple(value, field=_FIELD_MEANING)
    if is_refusal(meaning):
        return meaning
    checked = _validate_meaning_tokens(meaning.value)
    if is_refusal(checked):
        return checked
    return Ok(meaning.value)


def _validate_meaning_tokens(tokens: tuple[str, ...]) -> Result[None]:
    for token in tokens:
        if token not in GRAPH_MEANING_KINDS:
            return invalid(
                _FIELD_MEANING,
                _MEANING_REASON,
                given=token,
                allowed=tuple(sorted(GRAPH_MEANING_KINDS)),
            )
    return Ok(None)


def _admit_plane(plane: object) -> Result[str]:
    if not isinstance(plane, str) or plane.strip() == "":
        return invalid(_FIELD_PLANE, _PLANE_REASON, given=repr(plane))
    if plane.casefold().strip() != GRAPH_PLANE:
        return invalid(
            _FIELD_PLANE,
            "Boolean/temporal operators stay on the hypothesis plane as graph meaning",
            given=plane,
        )
    return Ok(GRAPH_PLANE)


def _checked_graph(graph: Graph) -> Result[Graph]:
    checked = _validate_graph(graph)
    if is_refusal(checked):
        return checked
    return Ok(graph)


def _validate_graph(graph: Graph) -> Result[None]:
    for token in graph.meaning:
        if token not in GRAPH_MEANING_KINDS:
            return invalid(_FIELD_MEANING, _MEANING_REASON, given=token)
    if graph.plane != GRAPH_PLANE:
        return invalid(_FIELD_PLANE, _PLANE_REASON, given=graph.plane)
    return Ok(None)


def _admit_claim(value: object) -> Result[EvidenceClaim]:
    if isinstance(value, EvidenceClaim):
        return Ok(value)
    if isinstance(value, str):
        return _admit_claim_text(value)
    if isinstance(value, Mapping):
        return _admit_claim_mapping(cast(_MAPPING_STR_OBJECT, value))
    return invalid(
        _FIELD_EVIDENCE,
        "an evidence claim is text or {claim, locator?}",
        given=type(value).__name__,
    )


def _admit_claim_text(value: str) -> Result[EvidenceClaim]:
    if value.strip() == "":
        return invalid(_FIELD_EVIDENCE, "an evidence claim is non-empty text", given=repr(value))
    return Ok(EvidenceClaim(claim=value.strip()))


def _admit_claim_mapping(mapping: _MAPPING_STR_OBJECT) -> Result[EvidenceClaim]:
    claim = mapping.get("claim")
    if not isinstance(claim, str) or claim.strip() == "":
        return invalid("claim", "an evidence claim is non-empty text", given=repr(claim))
    locator = mapping.get("locator")
    if locator is not None and (not isinstance(locator, str) or locator.strip() == ""):
        return invalid(
            "locator",
            "evidence locator is a non-empty string when present",
            given=repr(locator),
        )
    return Ok(
        EvidenceClaim(
            claim=claim.strip(),
            locator=locator.strip() if isinstance(locator, str) else None,
        )
    )


def _build_label_map(
    value: Mapping[object, object],
    *,
    field: str,
    allowed: frozenset[str] | None,
) -> Result[dict[str, str]]:
    out: dict[str, str] = {}
    for raw_key, raw_label in value.items():
        entry = _admit_label_entry(raw_key, raw_label, field=field, allowed=allowed)
        if is_refusal(entry):
            return entry
        key, label = entry.value
        out[key] = label
    return Ok(out)


def _admit_label_entry(
    raw_key: object,
    raw_label: object,
    *,
    field: str,
    allowed: frozenset[str] | None,
) -> Result[tuple[str, str]]:
    if not isinstance(raw_key, str) or raw_key.strip() == "":
        return invalid(field, f"{field} keys are non-empty strings", given=repr(raw_key))
    if not isinstance(raw_label, str) or raw_label.strip() == "":
        return invalid(field, f"{field} values are non-empty strings", given=repr(raw_label))
    label = raw_label.casefold().strip()
    if allowed is not None and label not in allowed:
        return invalid(field, f"{field} labels are the Stage 0 closed set", given=label)
    return Ok((raw_key.casefold().strip(), label))
