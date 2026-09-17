"""Stage 0 mint/restore admission (split from ``stage0`` for Skylos quality).

Pure in-process validation only — no filesystem I/O, threads, or process spawn.
Leaf field admitters live in ``_admit_fields``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, TypeAlias, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid
from qml.research._admit_fields import (
    admit_bindings,
    admit_cites,
    admit_evidence,
    admit_graph,
    admit_label_map,
    admit_string_tuple,
    optional_string,
)
from qml.research.stage0 import (
    F_LABELS,
    HYPOTHESIS_CLASSES,
    HYPOTHESIS_ORIGINS,
    RESEARCH_CONTRACT_CLASS,
    RESEARCH_FORMAT_VERSION,
    DictionaryCite,
    EvidenceClaim,
    Graph,
    Hypothesis,
    RoleBinding,
    admit_research_format_version,
)

__all__ = ["mint_hypothesis", "restore_hypothesis"]

_FIELD_CLASS: Final[str] = "class"
_FIELD_ORIGIN: Final[str] = "origin"
_FIELD_EVIDENCE: Final[str] = "evidence"
_FIELD_UNKNOWNS: Final[str] = "unknowns"
_FIELD_F_LABELS: Final[str] = "f_labels"
_FIELD_H_LABELS: Final[str] = "h_labels"
_FIELD_VERSION: Final[str] = "contract_format_version"
_FIELD_TITLE: Final[str] = "title"
_FIELD_PACKAGE: Final[str] = "package_id"
_OPTIONAL_FIELD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "dictionary_cites",
        "role_bindings",
        "graph",
        _FIELD_EVIDENCE,
        _FIELD_UNKNOWNS,
        _FIELD_F_LABELS,
        _FIELD_H_LABELS,
        _FIELD_TITLE,
        _FIELD_PACKAGE,
    }
)
_OCCURRENCE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "occurrence",
        "writer",
        "created_at",
        "snapshot_ref",
        "research_ref",
    }
)
_CLASS_REASON: Final[str] = "class is Stage 0 taxonomy"
_ORIGIN_REASON: Final[str] = (
    "a hypothesis may start from idea, chart, journal, or seed_package"
)
_HypothesisParts: TypeAlias = tuple[
    str,
    str,
    tuple[DictionaryCite, ...],
    tuple[RoleBinding, ...],
    Graph,
    tuple[EvidenceClaim, ...],
    tuple[str, ...],
    Mapping[str, str],
    Mapping[str, str],
    str | None,
    str | None,
    int,
]


def mint_hypothesis(
    *,
    hypothesis_class: object,
    origin: object,
    contract_format_version: object = RESEARCH_FORMAT_VERSION,
    **fields: object,
) -> Result[Hypothesis]:
    """Mint a Stage 0 hypothesis from authoring fields (source-agnostic mill)."""
    unknown = sorted(key for key in fields if key not in _OPTIONAL_FIELD_KEYS)
    if unknown:
        return invalid(
            unknown[0],
            "Stage 0 mint fields are the closed optional authoring set",
            given=unknown,
        )
    parts = _admit_hypothesis_parts(
        hypothesis_class=hypothesis_class,
        origin=origin,
        contract_format_version=contract_format_version,
        fields=fields,
    )
    if is_refusal(parts):
        return parts
    return Ok(_build_hypothesis(parts.value))


def restore_hypothesis(payload: object) -> Result[Hypothesis]:
    """Restore a Stage 0 hypothesis envelope. Unknown format → unavailable dependency."""
    admitted = _admit_restore_envelope(payload)
    if is_refusal(admitted):
        return admitted
    version, body = admitted.value
    return mint_hypothesis(
        hypothesis_class=body.get(_FIELD_CLASS),
        origin=body.get(_FIELD_ORIGIN),
        dictionary_cites=body.get("dictionary_cites", ()),
        role_bindings=body.get("role_bindings", ()),
        graph=body.get("graph"),
        evidence=body.get(_FIELD_EVIDENCE, ()),
        unknowns=body.get(_FIELD_UNKNOWNS, ()),
        f_labels=body.get(_FIELD_F_LABELS),
        h_labels=body.get(_FIELD_H_LABELS),
        title=body.get(_FIELD_TITLE),
        package_id=body.get(_FIELD_PACKAGE),
        contract_format_version=version,
    )


def _build_hypothesis(parts: _HypothesisParts) -> Hypothesis:
    (
        hypothesis_class_token,
        origin_token,
        cites,
        bindings,
        graph_value,
        claims,
        unknown_tokens,
        f_map,
        h_map,
        title_token,
        package_token,
        version,
    ) = parts
    return Hypothesis(
        hypothesis_class=hypothesis_class_token,
        origin=origin_token,
        dictionary_cites=cites,
        role_bindings=bindings,
        graph=graph_value,
        evidence=claims,
        unknowns=unknown_tokens,
        f_labels=f_map,
        h_labels=h_map,
        title=title_token,
        package_id=package_token,
        contract_format_version=version,
    )


def _admit_hypothesis_parts(
    *,
    hypothesis_class: object,
    origin: object,
    contract_format_version: object,
    fields: Mapping[str, object],
) -> Result[_HypothesisParts]:
    core = _admit_core_fields(hypothesis_class, origin, contract_format_version)
    if is_refusal(core):
        return core
    surfaces = _admit_surface_fields(fields)
    if is_refusal(surfaces):
        return surfaces
    labels = _admit_label_fields(fields)
    if is_refusal(labels):
        return labels
    class_token, origin_token, version = core.value
    cites, bindings, graph_value, claims, unknown_tokens = surfaces.value
    f_map, h_map, title_token, package_token = labels.value
    return Ok(
        (
            class_token,
            origin_token,
            cites,
            bindings,
            graph_value,
            claims,
            unknown_tokens,
            f_map,
            h_map,
            title_token,
            package_token,
            version,
        )
    )


def _admit_core_fields(
    hypothesis_class: object,
    origin: object,
    contract_format_version: object,
) -> Result[tuple[str, str, int]]:
    version = admit_research_format_version(contract_format_version)
    if is_refusal(version):
        return version
    class_token = _admit_class(hypothesis_class)
    if is_refusal(class_token):
        return class_token
    origin_token = _admit_origin(origin)
    if is_refusal(origin_token):
        return origin_token
    return Ok((class_token.value, origin_token.value, version.value))


def _admit_surface_fields(
    fields: Mapping[str, object],
) -> Result[
    tuple[
        tuple[DictionaryCite, ...],
        tuple[RoleBinding, ...],
        Graph,
        tuple[EvidenceClaim, ...],
        tuple[str, ...],
    ]
]:
    cites = admit_cites(fields.get("dictionary_cites", ()))
    if is_refusal(cites):
        return cites
    tail = _admit_surface_tail(fields)
    if is_refusal(tail):
        return tail
    bindings, graph_value, claims, unknown_tokens = tail.value
    return Ok((cites.value, bindings, graph_value, claims, unknown_tokens))


def _admit_surface_tail(
    fields: Mapping[str, object],
) -> Result[
    tuple[
        tuple[RoleBinding, ...],
        Graph,
        tuple[EvidenceClaim, ...],
        tuple[str, ...],
    ]
]:
    bindings = admit_bindings(fields.get("role_bindings", ()))
    if is_refusal(bindings):
        return bindings
    graph_value = admit_graph(fields.get("graph"))
    if is_refusal(graph_value):
        return graph_value
    claims_unknowns = _admit_claims_and_unknowns(fields)
    if is_refusal(claims_unknowns):
        return claims_unknowns
    claims, unknown_tokens = claims_unknowns.value
    return Ok((bindings.value, graph_value.value, claims, unknown_tokens))


def _admit_claims_and_unknowns(
    fields: Mapping[str, object],
) -> Result[tuple[tuple[EvidenceClaim, ...], tuple[str, ...]]]:
    claims = admit_evidence(fields.get(_FIELD_EVIDENCE, ()))
    if is_refusal(claims):
        return claims
    unknown_tokens = admit_string_tuple(
        fields.get(_FIELD_UNKNOWNS, ()),
        field=_FIELD_UNKNOWNS,
    )
    if is_refusal(unknown_tokens):
        return unknown_tokens
    return Ok((claims.value, unknown_tokens.value))


def _admit_label_fields(
    fields: Mapping[str, object],
) -> Result[tuple[Mapping[str, str], Mapping[str, str], str | None, str | None]]:
    f_map = admit_label_map(fields.get(_FIELD_F_LABELS), field=_FIELD_F_LABELS, allowed=F_LABELS)
    if is_refusal(f_map):
        return f_map
    h_map = admit_label_map(fields.get(_FIELD_H_LABELS), field=_FIELD_H_LABELS, allowed=None)
    if is_refusal(h_map):
        return h_map
    optional = _admit_optional_identity(fields)
    if is_refusal(optional):
        return optional
    title_token, package_token = optional.value
    return Ok((f_map.value, h_map.value, title_token, package_token))


def _admit_optional_identity(
    fields: Mapping[str, object],
) -> Result[tuple[str | None, str | None]]:
    title_token = optional_string(fields.get(_FIELD_TITLE), field=_FIELD_TITLE)
    if is_refusal(title_token):
        return title_token
    package_token = optional_string(fields.get(_FIELD_PACKAGE), field=_FIELD_PACKAGE)
    if is_refusal(package_token):
        return package_token
    return Ok((title_token.value, package_token.value))


def _admit_restore_envelope(
    payload: object,
) -> Result[tuple[int, Mapping[str, object]]]:
    header = _admit_restore_header(payload)
    if is_refusal(header):
        return header
    version, mapping = header.value
    raw_body = mapping.get("body")
    if not isinstance(raw_body, Mapping):
        return invalid(
            "body",
            "Stage 0 body is canonical JSON locators and meaning",
            given=type(raw_body).__name__,
        )
    return Ok((version, cast("Mapping[str, object]", raw_body)))


def _admit_restore_header(
    payload: object,
) -> Result[tuple[int, Mapping[str, object]]]:
    mapping = _as_restore_mapping(payload)
    if is_refusal(mapping):
        return mapping
    checked = _check_restore_mapping(mapping.value)
    if is_refusal(checked):
        return checked
    version = admit_research_format_version(mapping.value.get(_FIELD_VERSION))
    if is_refusal(version):
        return version
    return Ok((version.value, mapping.value))


def _check_restore_mapping(mapping: Mapping[str, object]) -> Result[None]:
    banned = _refuse_occurrence_keys(mapping)
    if is_refusal(banned):
        return banned
    if mapping.get(_FIELD_CLASS) == RESEARCH_CONTRACT_CLASS:
        return Ok(None)
    return invalid(
        _FIELD_CLASS,
        "Stage 0 restore expects class qml-research-hypothesis",
        given=repr(mapping.get(_FIELD_CLASS)),
    )


def _as_restore_mapping(payload: object) -> Result[Mapping[str, object]]:
    if isinstance(payload, Mapping):
        return Ok(cast("Mapping[str, object]", payload))
    return invalid(
        "payload",
        "a Stage 0 restore payload is a mapping with class, format version, and body",
        given=type(payload).__name__,
    )


def _refuse_occurrence_keys(mapping: Mapping[str, object]) -> Result[None]:
    for banned in _OCCURRENCE_KEYS:
        if banned in mapping and banned != "research_ref":
            return invalid(
                banned,
                "occurrence / writer / created-at / seed snapshot_ref are excluded "
                "from Stage 0 identity content",
                given=repr(mapping.get(banned)),
            )
    return Ok(None)


def _admit_class(value: object) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return invalid(_FIELD_CLASS, _CLASS_REASON, given=repr(value))
    token = value.casefold().strip()
    if token not in HYPOTHESIS_CLASSES:
        return invalid(_FIELD_CLASS, _CLASS_REASON, given=token)
    return Ok(token)


def _admit_origin(value: object) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return invalid(_FIELD_ORIGIN, _ORIGIN_REASON, given=repr(value))
    token = value.casefold().strip()
    if token not in HYPOTHESIS_ORIGINS:
        return invalid(
            _FIELD_ORIGIN,
            _ORIGIN_REASON,
            given=token,
            allowed=tuple(sorted(HYPOTHESIS_ORIGINS)),
        )
    return Ok(token)
