"""Stage 0 research-candidate types on QML's own format ladder (Story 50.1).

Public ``qml.research`` surface — not a QMA type, not a CT-*, not a host-private
schema. ``RESEARCH_FORMAT_VERSION`` is independent of QL-7 / QL-8. Stage 0 never
sizes, never emits CT-23 intents, never becomes a Book/node seat, and is never
cited by governed evidence. Composition identifier is ``graph`` (Boolean /
temporal / lifecycle). No I/O, threads, or process spawn (hosts persist).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core.fingerprint import Fingerprint, canonical_bytes, fingerprint
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
    "SavedHypothesis",
    "admit_research_format_version",
    "fingerprint_hypothesis",
    "hypothesis_canonical_bytes",
    "hypothesis_identity_payload",
    "mint_hypothesis",
    "refuse_stage0_governed_citation",
    "refuse_stage0_intent_emit",
    "refuse_stage0_seat",
    "refuse_stage0_sizing",
    "research_contract_identity",
    "restore_hypothesis",
    "save_authored_hypothesis",
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
_FIELD_HYPOTHESIS: Final[str] = "hypothesis"
_FIELD_VERSION: Final[str] = "contract_format_version"


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

    def identity_payload(self) -> dict[str, object]:
        """Fingerprint preimage. Occurrence / writer / created-at / snapshot_ref omitted."""
        return hypothesis_identity_payload(self)

    def fingerprint_content(self) -> Result[Fingerprint]:
        """``research_ref`` as fp1-shaped ``fp1:sha256:<hex>`` via qmf-core only."""
        return fingerprint_hypothesis(self)


def research_contract_identity() -> dict[str, object]:
    """Canonical identity of the research format ladder. No CT number, no SemVer."""
    return {
        "class": RESEARCH_CONTRACT_CLASS,
        "contract_format_version": RESEARCH_FORMAT_VERSION,
        "ladder": RESEARCH_LADDER,
        "surfaces": list(STAGE0_SURFACES),
    }


def hypothesis_identity_payload(hypothesis: Hypothesis) -> dict[str, object]:
    """Exact ``research_ref`` preimage (AD-21). Not a registry kind body."""
    return {
        "class": RESEARCH_CONTRACT_CLASS,
        "contract_format_version": hypothesis.contract_format_version,
        "body": hypothesis.canonical_body(),
    }


def _require_hypothesis(hypothesis: object, reason: str) -> Result[Hypothesis]:
    if isinstance(hypothesis, Hypothesis):
        return Ok(hypothesis)
    return invalid(_FIELD_HYPOTHESIS, reason, given=type(hypothesis).__name__)


def hypothesis_canonical_bytes(hypothesis: object) -> Result[bytes]:
    """Canonical JSON bytes of the identity preimage (sorted keys; CT-05)."""
    admitted = _require_hypothesis(
        hypothesis,
        "canonical research bytes are computed over a Stage 0 Hypothesis",
    )
    if is_refusal(admitted):
        return admitted
    return canonical_bytes(hypothesis_identity_payload(admitted.value))


def fingerprint_hypothesis(hypothesis: object) -> Result[Fingerprint]:
    """Compute ``research_ref`` = qmf-core fingerprint of the Stage 0 preimage.

    Value is fp1-shaped (``fp1:sha256:<hex>``). Not a qmf-registry kind, not an
    Artifact-rail hit, and not a ``research:sha256:`` dialect (DEC-0401).
    """
    admitted = _require_hypothesis(
        hypothesis,
        "research_ref fingerprints a Stage 0 Hypothesis after explicit save; "
        "a LAYOUT-DEMO projection is not a save",
    )
    if is_refusal(admitted):
        return admitted
    return fingerprint(hypothesis_identity_payload(admitted.value))


@dataclass(frozen=True, slots=True)
class SavedHypothesis:
    """Canonical bytes + ``research_ref`` from an explicit authoring save.

    Pure return value — hosts persist under ``research_root``. Viewing cited seed
    never produces this type.
    """

    canonical_bytes: bytes
    research_ref: Fingerprint


def save_authored_hypothesis(hypothesis: object) -> Result[SavedHypothesis]:
    """Explicit Stage 0 save: return canonical bytes and ``research_ref`` (no I/O)."""
    admitted = _require_hypothesis(
        hypothesis,
        "explicit save returns canonical bytes for a Stage 0 Hypothesis",
    )
    if is_refusal(admitted):
        return admitted
    return _save_admitted_hypothesis(admitted.value)


def _save_admitted_hypothesis(hypothesis: Hypothesis) -> Result[SavedHypothesis]:
    canonical = hypothesis_canonical_bytes(hypothesis)
    if is_refusal(canonical):
        return canonical
    ref = fingerprint_hypothesis(hypothesis)
    if is_refusal(ref):
        return ref
    return Ok(SavedHypothesis(canonical_bytes=canonical.value, research_ref=ref.value))


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


# Admission helpers + mint/restore live in ``_admit`` to keep this module under
# the Skylos god-file / cyclomatic thresholds; public names stay here.
from qml.research._admit import mint_hypothesis, restore_hypothesis  # noqa: E402
