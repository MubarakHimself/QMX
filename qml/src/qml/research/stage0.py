"""Stage 0 research-candidate types on QML's own format ladder (Story 50.1).

Public ``qml.research`` surface — not a QMA type, not a CT-*, not a host-private
schema. ``RESEARCH_FORMAT_VERSION`` is independent of QL-7 / QL-8. Stage 0 never
sizes, never emits CT-23 intents, never becomes a Book/node seat, and is never
cited by governed evidence. Composition identifier is ``graph`` (Boolean /
temporal / lifecycle). No I/O, threads, or process spawn (hosts persist).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid, policy, unavailable

__all__ = [
    "F_LABELS",
    "F_SLOTS",
    "GRAPH_MEANING_KINDS",
    "GRAPH_PLANE",
    "HYPOTHESIS_CLASSES",
    "HYPOTHESIS_ORIGINS",
    "RESEARCH_CONTRACT_CLASS",
    "RESEARCH_FORMAT_VERSION",
    "RESEARCH_KNOWN_FORMAT_VERSIONS",
    "RESEARCH_LADDER",
    "STAGE0_CITED_BY_GOVERNED_EVIDENCE",
    "STAGE0_EMITS_CT23",
    "STAGE0_IS_BOOK_SEAT",
    "STAGE0_NEVER_SIZES",
    "STAGE0_SURFACES",
    "DictionaryCite",
    "EvidenceClaim",
    "Graph",
    "Hypothesis",
    "RoleBinding",
    "admit_research_format_version",
    "mint_hypothesis",
    "refuse_stage0_governed_citation",
    "refuse_stage0_intent_emit",
    "refuse_stage0_seat",
    "refuse_stage0_sizing",
    "research_contract_identity",
    "restore_hypothesis",
]

# QML-local AD-5 second ladder. Not QL-7 protocol / QL-8 conformance (DEC-0395).
RESEARCH_CONTRACT_CLASS: Final[str] = "qml-research-hypothesis"
RESEARCH_FORMAT_VERSION: Final[int] = 1
RESEARCH_KNOWN_FORMAT_VERSIONS: Final[frozenset[int]] = frozenset({RESEARCH_FORMAT_VERSION})
RESEARCH_LADDER: Final[str] = "qml-ad5-research"

GRAPH_PLANE: Final[str] = "hypothesis"
GRAPH_MEANING_KINDS: Final[frozenset[str]] = frozenset({"boolean", "temporal", "lifecycle"})

HYPOTHESIS_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "entry_hypothesis",
        "fragment",
        "descriptive_pattern",
        "composite",
        "complete",
    }
)
HYPOTHESIS_ORIGINS: Final[frozenset[str]] = frozenset(
    {
        "idea",
        "chart",
        "journal",
        "seed_package",
    }
)
F_SLOTS: Final[tuple[str, ...]] = (
    "invalidation",
    "stop",
    "targets",
    "exit",
    "management",
)
F_LABELS: Final[frozenset[str]] = frozenset(
    {
        "source_defined",
        "external_policy",
        "deliberately_open",
        "unresolved",
    }
)

# Honesty envelope — Stage 0 is non-executable mill surface (AD-15, AD-20).
STAGE0_NEVER_SIZES: Final[bool] = True
STAGE0_EMITS_CT23: Final[bool] = False
STAGE0_IS_BOOK_SEAT: Final[bool] = False
STAGE0_CITED_BY_GOVERNED_EVIDENCE: Final[bool] = False

STAGE0_SURFACES: Final[tuple[str, ...]] = (
    "dictionary_cites",
    "role_bindings",
    "graph",
    "evidence",
    "unknowns",
    "f_labels",
    "h_labels",
    "class",
)

_EMPTY_F: Final[Mapping[str, str]] = MappingProxyType({})
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


@dataclass(frozen=True, slots=True)
class DictionaryCite:
    """Seed or caller locator for a role-neutral dictionary entry.

    Identity remains ``(file_path, id)``. Not a registry row.
    """

    file_path: str
    id: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType({"file_path": self.file_path, "id": self.id})


@dataclass(frozen=True, slots=True)
class RoleBinding:
    """What job a dictionary cite does in this candidate (open Stage 0 roles)."""

    cite: DictionaryCite
    role: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "cite": dict(self.cite.to_payload()),
                "role": self.role,
            }
        )


@dataclass(frozen=True, slots=True)
class Graph:
    """Boolean / temporal / lifecycle composition as meaning — never an executor."""

    operators: tuple[str, ...] = ()
    meaning: tuple[str, ...] = ()
    plane: str = GRAPH_PLANE

    def __post_init__(self) -> None:
        object.__setattr__(self, "operators", tuple(self.operators))
        object.__setattr__(self, "meaning", tuple(self.meaning))

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "operators": list(self.operators),
                "meaning": list(self.meaning),
                "plane": self.plane,
            }
        )


@dataclass(frozen=True, slots=True)
class EvidenceClaim:
    """Source-faithful claim mapping. Not CT-32 measured evidence."""

    claim: str
    locator: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        body: dict[str, object] = {"claim": self.claim}
        if self.locator is not None:
            body["locator"] = self.locator
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class Hypothesis:
    """Stage 0 research candidate. Not a registry kind and not a Library object.

    May start from an idea, chart, journal, or seed package. Occurrence facts
    (writer / created-at / snapshot_ref) never live on this type.
    """

    hypothesis_class: str
    origin: str
    dictionary_cites: tuple[DictionaryCite, ...] = ()
    role_bindings: tuple[RoleBinding, ...] = ()
    graph: Graph = Graph()
    evidence: tuple[EvidenceClaim, ...] = ()
    unknowns: tuple[str, ...] = ()
    f_labels: Mapping[str, str] = _EMPTY_F
    h_labels: Mapping[str, str] = _EMPTY_F
    title: str | None = None
    package_id: str | None = None
    contract_format_version: int = RESEARCH_FORMAT_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "dictionary_cites", tuple(self.dictionary_cites))
        object.__setattr__(self, "role_bindings", tuple(self.role_bindings))
        object.__setattr__(self, "evidence", tuple(self.evidence))
        object.__setattr__(self, "unknowns", tuple(self.unknowns))
        object.__setattr__(self, _FIELD_F_LABELS, MappingProxyType(dict(self.f_labels)))
        object.__setattr__(self, _FIELD_H_LABELS, MappingProxyType(dict(self.h_labels)))

    def canonical_body(self) -> dict[str, object]:
        """Canonical Stage 0 JSON content (sorted keys at fingerprint time).

        Locators and meaning only — not host markdown, not occurrence facts.
        """
        body: dict[str, object] = {
            "class": self.hypothesis_class,
            "dictionary_cites": [dict(item.to_payload()) for item in self.dictionary_cites],
            "evidence": [dict(item.to_payload()) for item in self.evidence],
            _FIELD_F_LABELS: {slot: self.f_labels[slot] for slot in sorted(self.f_labels)},
            "graph": dict(self.graph.to_payload()),
            _FIELD_H_LABELS: {key: self.h_labels[key] for key in sorted(self.h_labels)},
            "origin": self.origin,
            "role_bindings": [dict(item.to_payload()) for item in self.role_bindings],
            "unknowns": list(self.unknowns),
        }
        if self.package_id is not None:
            body["package_id"] = self.package_id
        if self.title is not None:
            body["title"] = self.title
        return body


def research_contract_identity() -> dict[str, object]:
    """Canonical identity of the research format ladder. No CT number, no SemVer."""
    return {
        "class": RESEARCH_CONTRACT_CLASS,
        "contract_format_version": RESEARCH_FORMAT_VERSION,
        "ladder": RESEARCH_LADDER,
        "surfaces": list(STAGE0_SURFACES),
    }


def admit_research_format_version(value: object) -> Result[int]:
    """Admit a known research format version; unknown is unavailable dependency."""
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            _FIELD_VERSION,
            "a research format version is a positive integer; package SemVer never enters",
            given=repr(value),
        )
    if value < 1:
        return invalid(
            _FIELD_VERSION,
            "a research format version is a positive integer ordinal",
            given=repr(value),
        )
    if value not in RESEARCH_KNOWN_FORMAT_VERSIONS:
        return unavailable(
            _FIELD_VERSION,
            "an unknown RESEARCH_FORMAT_VERSION on restore is an unavailable "
            "dependency; additive optional fields require a version bump "
            "(AD-21; DEC-0401)",
            given=value,
            supported=RESEARCH_FORMAT_VERSION,
            ladder=RESEARCH_LADDER,
        )
    return Ok(value)


def refuse_stage0_sizing(candidate: object = None) -> Result[None]:
    """Stage 0 never sizes (AD-15)."""
    _ = candidate
    return policy(
        "sizing",
        "Stage 0 never sizes; sizing stays Book/risk authority",
        never_sizes=STAGE0_NEVER_SIZES,
        sizes=False,
    )


def refuse_stage0_intent_emit(candidate: object = None) -> Result[None]:
    """Stage 0 never emits CT-23 intents (AD-15)."""
    _ = candidate
    return policy(
        "intents",
        "Stage 0 never emits CT-23 intents",
        emits_ct23=STAGE0_EMITS_CT23,
        ct23=False,
    )


def refuse_stage0_seat(candidate: object = None) -> Result[None]:
    """Stage 0 never becomes a Book/node seat (AD-15)."""
    _ = candidate
    return policy(
        "seat",
        "Stage 0 never becomes a Book/node seat; seats cite Bot fp1 only",
        is_book_seat=STAGE0_IS_BOOK_SEAT,
        seat=False,
    )


def refuse_stage0_governed_citation(candidate: object = None) -> Result[None]:
    """Stage 0 is never cited by governed evidence (AD-15)."""
    _ = candidate
    return policy(
        "governed_evidence",
        "Stage 0 is never cited by governed evidence; CT-32 / seats cite Bot fp1 only",
        cited_by_governed_evidence=STAGE0_CITED_BY_GOVERNED_EVIDENCE,
        governed_evidence=False,
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
    version = admit_research_format_version(contract_format_version)
    if is_refusal(version):
        return version
    class_token = _admit_class(hypothesis_class)
    if is_refusal(class_token):
        return class_token
    origin_token = _admit_origin(origin)
    if is_refusal(origin_token):
        return origin_token
    cites = _admit_cites(dictionary_cites)
    if is_refusal(cites):
        return cites
    bindings = _admit_bindings(role_bindings)
    if is_refusal(bindings):
        return bindings
    graph_value = _admit_graph(graph)
    if is_refusal(graph_value):
        return graph_value
    claims = _admit_evidence(evidence)
    if is_refusal(claims):
        return claims
    unknown_tokens = _admit_string_tuple(unknowns, field="unknowns")
    if is_refusal(unknown_tokens):
        return unknown_tokens
    f_map = _admit_label_map(f_labels, field=_FIELD_F_LABELS, allowed=F_LABELS)
    if is_refusal(f_map):
        return f_map
    h_map = _admit_label_map(h_labels, field=_FIELD_H_LABELS, allowed=None)
    if is_refusal(h_map):
        return h_map
    title_token = _optional_string(title, field="title")
    if is_refusal(title_token):
        return title_token
    package_token = _optional_string(package_id, field="package_id")
    if is_refusal(package_token):
        return package_token
    return Ok(
        Hypothesis(
            hypothesis_class=class_token.value,
            origin=origin_token.value,
            dictionary_cites=cites.value,
            role_bindings=bindings.value,
            graph=graph_value.value,
            evidence=claims.value,
            unknowns=unknown_tokens.value,
            f_labels=f_map.value,
            h_labels=h_map.value,
            title=title_token.value,
            package_id=package_token.value,
            contract_format_version=version.value,
        )
    )


def restore_hypothesis(payload: object) -> Result[Hypothesis]:
    """Restore a Stage 0 hypothesis envelope. Unknown format → unavailable dependency."""
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
    class_token = mapping.get("class")
    if class_token != RESEARCH_CONTRACT_CLASS:
        return invalid(
            "class",
            "Stage 0 restore expects class qml-research-hypothesis",
            given=repr(class_token),
        )
    version = admit_research_format_version(mapping.get(_FIELD_VERSION))
    if is_refusal(version):
        return version
    raw_body = mapping.get("body")
    if not isinstance(raw_body, Mapping):
        return invalid(
            "body",
            "Stage 0 body is canonical JSON locators and meaning",
            given=type(raw_body).__name__,
        )
    body = cast("Mapping[str, object]", raw_body)
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
        contract_format_version=version.value,
    )


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


def _admit_cites(value: object) -> Result[tuple[DictionaryCite, ...]]:
    if value is None:
        return Ok(())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "dictionary_cites",
            "dictionary cites are a sequence of {file_path, id} locators",
            given=type(value).__name__,
        )
    out: list[DictionaryCite] = []
    for item in value:
        cite = _admit_cite(item)
        if is_refusal(cite):
            return cite
        out.append(cite.value)
    return Ok(tuple(out))


def _admit_cite(value: object) -> Result[DictionaryCite]:
    if isinstance(value, DictionaryCite):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "dictionary_cites",
            "a dictionary cite is {file_path, id}",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
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


def _admit_bindings(value: object) -> Result[tuple[RoleBinding, ...]]:
    if value is None:
        return Ok(())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "role_bindings",
            "role bindings are a sequence of {cite, role}",
            given=type(value).__name__,
        )
    out: list[RoleBinding] = []
    for item in value:
        binding = _admit_binding(item)
        if is_refusal(binding):
            return binding
        out.append(binding.value)
    return Ok(tuple(out))


def _admit_binding(value: object) -> Result[RoleBinding]:
    if isinstance(value, RoleBinding):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "role_bindings",
            "a role binding is {cite, role}",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
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


def _admit_graph(value: object) -> Result[Graph]:
    if value is None:
        return Ok(Graph())
    if isinstance(value, Graph):
        checked = _validate_graph(value)
        if is_refusal(checked):
            return checked
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "graph",
            "graph is Boolean/temporal/lifecycle meaning",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
    if "confluence" in mapping or "Confluence" in mapping:
        return invalid(
            "graph",
            "Stage 0 composition field/type is graph; Confluence stays CT-34",
            given="confluence",
        )
    operators = _admit_string_tuple(mapping.get("operators", ()), field="operators")
    if is_refusal(operators):
        return operators
    meaning = _admit_string_tuple(mapping.get("meaning", ()), field="meaning")
    if is_refusal(meaning):
        return meaning
    for token in meaning.value:
        if token not in GRAPH_MEANING_KINDS:
            return invalid(
                "meaning",
                "graph meaning kinds are boolean, temporal, and lifecycle",
                given=token,
                allowed=tuple(sorted(GRAPH_MEANING_KINDS)),
            )
    plane = mapping.get("plane", GRAPH_PLANE)
    if not isinstance(plane, str) or plane.strip() == "":
        return invalid("plane", "graph plane is the hypothesis plane", given=repr(plane))
    if plane.casefold().strip() != GRAPH_PLANE:
        return invalid(
            "plane",
            "Boolean/temporal operators stay on the hypothesis plane as graph meaning",
            given=plane,
        )
    return Ok(
        Graph(
            operators=operators.value,
            meaning=meaning.value,
            plane=GRAPH_PLANE,
        )
    )


def _validate_graph(graph: Graph) -> Result[None]:
    for token in graph.meaning:
        if token not in GRAPH_MEANING_KINDS:
            return invalid(
                "meaning",
                "graph meaning kinds are boolean, temporal, and lifecycle",
                given=token,
            )
    if graph.plane != GRAPH_PLANE:
        return invalid("plane", "graph plane is the hypothesis plane", given=graph.plane)
    return Ok(None)


def _admit_evidence(value: object) -> Result[tuple[EvidenceClaim, ...]]:
    if value is None:
        return Ok(())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "evidence",
            "evidence is a sequence of source-faithful claims (not CT-32)",
            given=type(value).__name__,
        )
    out: list[EvidenceClaim] = []
    for item in value:
        claim = _admit_claim(item)
        if is_refusal(claim):
            return claim
        out.append(claim.value)
    return Ok(tuple(out))


def _admit_claim(value: object) -> Result[EvidenceClaim]:
    if isinstance(value, EvidenceClaim):
        return Ok(value)
    if isinstance(value, str):
        if value.strip() == "":
            return invalid("evidence", "an evidence claim is non-empty text", given=repr(value))
        return Ok(EvidenceClaim(claim=value.strip()))
    if not isinstance(value, Mapping):
        return invalid(
            "evidence",
            "an evidence claim is text or {claim, locator?}",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
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


def _admit_string_tuple(value: object, *, field: str) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, str):
        token = value.strip()
        return Ok((token,) if token else ())
    if not isinstance(value, Sequence) or isinstance(value, (bytes, bytearray)):
        return invalid(field, f"{field} is a sequence of strings", given=type(value).__name__)
    out: list[str] = []
    for item in value:
        if not isinstance(item, str) or item.strip() == "":
            return invalid(field, f"{field} entries are non-empty strings", given=repr(item))
        out.append(item.strip())
    return Ok(tuple(out))


def _admit_label_map(
    value: object,
    *,
    field: str,
    allowed: frozenset[str] | None,
) -> Result[Mapping[str, str]]:
    if value is None:
        return Ok(_EMPTY_F)
    if not isinstance(value, Mapping):
        return invalid(field, f"{field} is a string-to-string map", given=type(value).__name__)
    out: dict[str, str] = {}
    for raw_key, raw_label in cast("Mapping[object, object]", value).items():
        if not isinstance(raw_key, str) or raw_key.strip() == "":
            return invalid(field, f"{field} keys are non-empty strings", given=repr(raw_key))
        if not isinstance(raw_label, str) or raw_label.strip() == "":
            return invalid(field, f"{field} values are non-empty strings", given=repr(raw_label))
        key = raw_key.casefold().strip()
        label = raw_label.casefold().strip()
        if allowed is not None and label not in allowed:
            return invalid(field, f"{field} labels are the Stage 0 closed set", given=label)
        out[key] = label
    return Ok(MappingProxyType(out))


def _optional_string(value: object, *, field: str) -> Result[str | None]:
    if value is None:
        return Ok(None)
    if not isinstance(value, str) or value.strip() == "":
        return invalid(field, f"{field} is a non-empty string when present", given=repr(value))
    return Ok(value.strip())
