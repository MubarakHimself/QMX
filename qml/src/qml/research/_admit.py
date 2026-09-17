"""Stage 0 mint/restore admission (split from ``stage0`` for Skylos quality).

Pure in-process validation only — no filesystem I/O, threads, or process spawn.
Leaf field admitters live in ``_admit_fields``.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

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
    Hypothesis,
    admit_research_format_version,
)

__all__ = ["mint_hypothesis", "restore_hypothesis"]

_FIELD_F_LABELS: Final[str] = "f_labels"
_FIELD_H_LABELS: Final[str] = "h_labels"
_FIELD_VERSION: Final[str] = "contract_format_version"
_OCCURRENCE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "occurrence",
        "writer",
        "created_at",
        "snapshot_ref",
        "research_ref",
    }
)


def mint_hypothesis(
    *,
    hypothesis_class: object,
    origin: object,
    dictionary_cites: object = (),
    role_bindings: object = (),
    graph: object = None,
    evidence: object = (),
    unknowns: object = (),
    f_labels: object = None,
    h_labels: object = None,
    title: object = None,
    package_id: object = None,
    contract_format_version: object = RESEARCH_FORMAT_VERSION,
) -> Result[Hypothesis]:
    """Mint a Stage 0 hypothesis from authoring fields (source-agnostic mill)."""
    parts = _admit_hypothesis_parts(
        hypothesis_class=hypothesis_class,
        origin=origin,
        dictionary_cites=dictionary_cites,
        role_bindings=role_bindings,
        graph=graph,
        evidence=evidence,
        unknowns=unknowns,
        f_labels=f_labels,
        h_labels=h_labels,
        title=title,
        package_id=package_id,
        contract_format_version=contract_format_version,
    )
    if is_refusal(parts):
        return parts
    return Ok(Hypothesis(**parts.value))


def restore_hypothesis(payload: object) -> Result[Hypothesis]:
    """Restore a Stage 0 hypothesis envelope. Unknown format → unavailable dependency."""
    admitted = _admit_restore_envelope(payload)
    if is_refusal(admitted):
        return admitted
    version, body = admitted.value
    return mint_hypothesis(
        hypothesis_class=body.get("class"),
        origin=body.get("origin"),
        dictionary_cites=body.get("dictionary_cites", ()),
        role_bindings=body.get("role_bindings", ()),
        graph=body.get("graph"),
        evidence=body.get("evidence", ()),
        unknowns=body.get("unknowns", ()),
        f_labels=body.get(_FIELD_F_LABELS),
        h_labels=body.get(_FIELD_H_LABELS),
        title=body.get("title"),
        package_id=body.get("package_id"),
        contract_format_version=version,
    )


def _admit_hypothesis_parts(
    *,
    hypothesis_class: object,
    origin: object,
    dictionary_cites: object,
    role_bindings: object,
    graph: object,
    evidence: object,
    unknowns: object,
    f_labels: object,
    h_labels: object,
    title: object,
    package_id: object,
    contract_format_version: object,
) -> Result[dict[str, object]]:
    core = _admit_core_fields(hypothesis_class, origin, contract_format_version)
    if is_refusal(core):
        return core
    surfaces = _admit_surface_fields(
        dictionary_cites, role_bindings, graph, evidence, unknowns
    )
    if is_refusal(surfaces):
        return surfaces
    labels = _admit_label_fields(f_labels, h_labels, title, package_id)
    if is_refusal(labels):
        return labels
    return Ok({**core.value, **surfaces.value, **labels.value})


def _admit_core_fields(
    hypothesis_class: object,
    origin: object,
    contract_format_version: object,
) -> Result[dict[str, object]]:
    version = admit_research_format_version(contract_format_version)
    if is_refusal(version):
        return version
    class_token = _admit_class(hypothesis_class)
    if is_refusal(class_token):
        return class_token
    origin_token = _admit_origin(origin)
    if is_refusal(origin_token):
        return origin_token
    return Ok(
        {
            "hypothesis_class": class_token.value,
            "origin": origin_token.value,
            "contract_format_version": version.value,
        }
    )


def _admit_surface_fields(
    dictionary_cites: object,
    role_bindings: object,
    graph: object,
    evidence: object,
    unknowns: object,
) -> Result[dict[str, object]]:
    cites = admit_cites(dictionary_cites)
    if is_refusal(cites):
        return cites
    bindings = admit_bindings(role_bindings)
    if is_refusal(bindings):
        return bindings
    graph_value = admit_graph(graph)
    if is_refusal(graph_value):
        return graph_value
    claims = admit_evidence(evidence)
    if is_refusal(claims):
        return claims
    unknown_tokens = admit_string_tuple(unknowns, field="unknowns")
    if is_refusal(unknown_tokens):
        return unknown_tokens
    return Ok(
        {
            "dictionary_cites": cites.value,
            "role_bindings": bindings.value,
            "graph": graph_value.value,
            "evidence": claims.value,
            "unknowns": unknown_tokens.value,
        }
    )


def _admit_label_fields(
    f_labels: object,
    h_labels: object,
    title: object,
    package_id: object,
) -> Result[dict[str, object]]:
    f_map = admit_label_map(f_labels, field=_FIELD_F_LABELS, allowed=F_LABELS)
    if is_refusal(f_map):
        return f_map
    h_map = admit_label_map(h_labels, field=_FIELD_H_LABELS, allowed=None)
    if is_refusal(h_map):
        return h_map
    title_token = optional_string(title, field="title")
    if is_refusal(title_token):
        return title_token
    package_token = optional_string(package_id, field="package_id")
    if is_refusal(package_token):
        return package_token
    return Ok(
        {
            "f_labels": f_map.value,
            "h_labels": h_map.value,
            "title": title_token.value,
            "package_id": package_token.value,
        }
    )


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
    if not isinstance(payload, Mapping):
        return invalid(
            "payload",
            "a Stage 0 restore payload is a mapping with class, format version, and body",
            given=type(payload).__name__,
        )
    mapping = cast("Mapping[str, object]", payload)
    for banned in _OCCURRENCE_KEYS:
        if banned in mapping and banned != "research_ref":
            return invalid(
                banned,
                "occurrence / writer / created-at / seed snapshot_ref are excluded "
                "from Stage 0 identity content",
                given=repr(mapping.get(banned)),
            )
    if mapping.get("class") != RESEARCH_CONTRACT_CLASS:
        return invalid(
            "class",
            "Stage 0 restore expects class qml-research-hypothesis",
            given=repr(mapping.get("class")),
        )
    version = admit_research_format_version(mapping.get(_FIELD_VERSION))
    if is_refusal(version):
        return version
    return Ok((version.value, mapping))


def _admit_class(value: object) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return invalid("class", "class is Stage 0 taxonomy", given=repr(value))
    token = value.casefold().strip()
    if token not in HYPOTHESIS_CLASSES:
        return invalid("class", "class is Stage 0 taxonomy", given=token)
    return Ok(token)


def _admit_origin(value: object) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return invalid(
            "origin",
            "a hypothesis may start from idea, chart, journal, or seed_package",
            given=repr(value),
        )
    token = value.casefold().strip()
    if token not in HYPOTHESIS_ORIGINS:
        return invalid(
            "origin",
            "a hypothesis may start from idea, chart, journal, or seed_package",
            given=token,
            allowed=tuple(sorted(HYPOTHESIS_ORIGINS)),
        )
    return Ok(token)
