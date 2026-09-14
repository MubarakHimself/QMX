"""Library kinds as a projection over existing fp1 records (Story 34.1).

Library is not a package and not a new COMP. Kind owner stays
``COMP-QMF-REGISTRY``. Shared objects are exactly the existing kinds cited by
``fp1`` (FR-W17, DEC-0271). Logic source-manifests ride CT-33. QMA staging,
handles, Graph Templates, Skills, Routines, saved views, publications, derived
datasets, STRATS, and Project/Workspace names are not Library kinds (FR-W18,
UX-DR2, DEC-0284).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qmf.core.refusal import Ok, Result, TypedRefusal

from qmb._refuse import clean_token, invalid, policy

__all__ = [
    "COMP_LIB_MINTED",
    "KIND_OWNER",
    "LIBRARY_KINDS",
    "LIBRARY_KINDS_CLASS",
    "LIBRARY_KINDS_OCCUPANCY",
    "LIBRARY_KIND_NAMES",
    "LIBRARY_MINTS_CT32",
    "LIBRARY_MINTS_EXPERIMENT_SPEC",
    "LOGIC_SOURCE_MANIFEST_CITES",
    "NOT_LIBRARY_KIND_NAMES",
    "QMX_LIBRARY_PACKAGE",
    "STRATS_CORPUS",
    "LibraryKind",
    "LibraryKindRoster",
    "enumerate_library_kinds",
    "library_kinds_identity",
    "register_library_kind",
]

KIND_OWNER: Final[str] = "COMP-QMF-REGISTRY"
LIBRARY_KINDS_CLASS: Final[str] = "qmb-library-kind-roster"
LIBRARY_KINDS_OCCUPANCY: Final[str] = "query"
LIBRARY_MINTS_CT32: Final[bool] = False
LIBRARY_MINTS_EXPERIMENT_SPEC: Final[bool] = False
COMP_LIB_MINTED: Final[bool] = False
QMX_LIBRARY_PACKAGE: Final[bool] = False
LOGIC_SOURCE_MANIFEST_CITES: Final[str] = "CT-33"
STRATS_CORPUS: Final[str] = "KnowledgeSource"
_LANE_COORDINATED: Final[str] = "coordinated"
_LANE_GOVERNED: Final[str] = "governed"
_LANE_UNGOVERNED: Final[str] = "ungoverned"
_LEGAL_LANES: Final[frozenset[str]] = frozenset(
    {_LANE_COORDINATED, _LANE_GOVERNED, _LANE_UNGOVERNED}
)


@dataclass(frozen=True, slots=True)
class LibraryKind:
    """One existing fp1 kind the Library projection may cite."""

    kind: str
    contract: str
    coordinated_lane_only: bool = False

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing Library-kind fields. Package SemVer is omitted."""
        return {
            "contract": self.contract,
            "coordinated_lane_only": self.coordinated_lane_only,
            "kind": self.kind,
            "owner": KIND_OWNER,
        }


LIBRARY_KINDS: Final[tuple[LibraryKind, ...]] = (
    LibraryKind(kind="bot-definition", contract="CT-33"),
    LibraryKind(kind="confluence", contract="CT-34"),
    LibraryKind(kind="strategy-family", contract="CT-06"),
    LibraryKind(kind="book-definition", contract="CT-22"),
    LibraryKind(kind="bms-definition", contract="CT-27"),
    LibraryKind(kind="book-binding", contract="CT-28"),
    LibraryKind(kind="split-manifest", contract="CT-12"),
    LibraryKind(kind="source-observation", contract="CT-10"),
    LibraryKind(kind="performance-result", contract="CT-32"),
    LibraryKind(
        kind="experiment-spec",
        contract="CT-47",
        coordinated_lane_only=True,
    ),
)
LIBRARY_KIND_NAMES: Final[tuple[str, ...]] = tuple(item.kind for item in LIBRARY_KINDS)
_BY_KIND: Final[Mapping[str, LibraryKind]] = MappingProxyType(
    {item.kind: item for item in LIBRARY_KINDS}
)

NOT_LIBRARY_KIND_NAMES: Final[tuple[str, ...]] = (
    "staging",
    "refinement-proposal",
    "job-handle",
    "graph-template",
    "skill",
    "routine",
    "saved-view",
    "analysis-publication",
    "derived-dataset",
    "strats",
    "logic-source-manifest",
    "project",
    "workspace",
    "qmx-library",
    "comp-lib",
)

_KIND_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "bot": "bot-definition",
        "bot-definition": "bot-definition",
        "ct-33": "bot-definition",
        "ct33": "bot-definition",
        "confluence": "confluence",
        "ct-34": "confluence",
        "ct34": "confluence",
        "strategy-family": "strategy-family",
        "strategyfamily": "strategy-family",
        "book": "book-definition",
        "book-definition": "book-definition",
        "ct-22": "book-definition",
        "ct22": "book-definition",
        "bms": "bms-definition",
        "bms-definition": "bms-definition",
        "ct-27": "bms-definition",
        "ct27": "bms-definition",
        "binding": "book-binding",
        "book-binding": "book-binding",
        "ct-28": "book-binding",
        "ct28": "book-binding",
        "split": "split-manifest",
        "split-manifest": "split-manifest",
        "ct-12": "split-manifest",
        "ct12": "split-manifest",
        "observation": "source-observation",
        "observation-window": "source-observation",
        "source-observation": "source-observation",
        "ct-10": "source-observation",
        "ct10": "source-observation",
        "result": "performance-result",
        "performance-result": "performance-result",
        "ct-32": "performance-result",
        "ct32": "performance-result",
        "experimentspec": "experiment-spec",
        "experiment-spec": "experiment-spec",
        "ct-47": "experiment-spec",
        "ct47": "experiment-spec",
    }
)

_REFUSED_ALIASES: Final[Mapping[str, str]] = MappingProxyType(
    {
        "staging": "staging",
        "qma-staging": "staging",
        "refinement-proposal": "refinement-proposal",
        "refinementproposal": "refinement-proposal",
        "refinement-proposals": "refinement-proposal",
        "job-handle": "job-handle",
        "jobhandle": "job-handle",
        "job-handles": "job-handle",
        "graph-template": "graph-template",
        "graphtemplate": "graph-template",
        "graph-templates": "graph-template",
        "skill": "skill",
        "skills": "skill",
        "routine": "routine",
        "routines": "routine",
        "saved-view": "saved-view",
        "savedview": "saved-view",
        "saved-views": "saved-view",
        "analysis-publication": "analysis-publication",
        "analysis.published": "analysis-publication",
        "analysis-published": "analysis-publication",
        "derived-dataset": "derived-dataset",
        "deriveddataset": "derived-dataset",
        "qmb-derived-dataset": "derived-dataset",
        "strats": "strats",
        "logic-source-manifest": "logic-source-manifest",
        "source-manifest": "logic-source-manifest",
        "logic-manifest": "logic-source-manifest",
        "project": "project",
        "workspace": "workspace",
        "qmx-library": "qmx-library",
        "comp-lib": "comp-lib",
        "comp-lib-qmx": "comp-lib",
    }
)


@dataclass(frozen=True, slots=True)
class LibraryKindRoster:
    """Closed Library kind list. Occupancy is a query; no new COMP is minted."""

    kinds: tuple[LibraryKind, ...] = LIBRARY_KINDS
    occupancy: str = LIBRARY_KINDS_OCCUPANCY
    owner: str = KIND_OWNER
    mints_ct32: bool = False
    mints_experiment_spec: bool = False
    mints_comp_lib: bool = False
    qmx_library_package: bool = False

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing roster fields. Package SemVer is omitted."""
        return {
            "class": LIBRARY_KINDS_CLASS,
            "command": "library.kinds",
            "comp_lib_minted": COMP_LIB_MINTED,
            "kinds": [item.fp1_identity() for item in self.kinds],
            "logic_source_manifest_cites": LOGIC_SOURCE_MANIFEST_CITES,
            "mints_ct32": False,
            "mints_experiment_spec": False,
            "occupancy": LIBRARY_KINDS_OCCUPANCY,
            "owner": KIND_OWNER,
            "qmx_library_package": QMX_LIBRARY_PACKAGE,
            "refused": list(NOT_LIBRARY_KIND_NAMES),
            "strats_corpus": STRATS_CORPUS,
        }


def library_kinds_identity() -> dict[str, object]:
    """Identity-bearing Library-projection fields."""
    return enumerate_library_kinds().fp1_identity()


def enumerate_library_kinds() -> LibraryKindRoster:
    """Return the closed fp1 kind list. ExperimentSpec is coordinated-only."""
    return LibraryKindRoster()


def register_library_kind(
    kind: object,
    *,
    lane: object = None,
    present_as_registry: object = False,
    mint_registry_kind: object = False,
    mint_package: object = False,
) -> Result[LibraryKind]:
    """Admit an existing Library kind as a projection member; refuse anything else.

    Does not mint a registry kind, a ``COMP-LIB`` / ``qmx-library`` package, or
    a QMA staging read. A later UI must not present refused names as registry
    records (FR-W18, UX-DR2).
    """
    if _truthy(mint_package) or _canonical_refused(kind) in {"qmx-library", "comp-lib"}:
        return _refuse_package(kind)
    if _truthy(mint_registry_kind):
        return policy(
            "mint_registry_kind",
            "Library kinds are the existing fp1 list owned by COMP-QMF-REGISTRY; "
            "this projection mints no registry kind (FR-W17, FR-W01, DEC-0271)",
            is_library_kind=False,
            mints_registry_kind=False,
            owner=KIND_OWNER,
            present_as_registry=False,
        )
    token = clean_token(kind)
    if token is None:
        return invalid(
            "kind",
            "a Library kind is a non-blank existing fp1 kind token",
            given=repr(kind),
            owner=KIND_OWNER,
        )
    refused = _canonical_refused(token)
    if refused is not None:
        return _refuse_not_library(refused, present_as_registry=present_as_registry)
    canonical = _canonical_library(token)
    if canonical is None:
        return _refuse_not_library(token, present_as_registry=present_as_registry)
    member = _BY_KIND[canonical]
    resolved_lane = _coerce_lane(lane)
    if isinstance(resolved_lane, TypedRefusal):
        return resolved_lane
    if member.coordinated_lane_only and resolved_lane in {_LANE_GOVERNED, _LANE_UNGOVERNED}:
        return policy(
            "lane",
            "CT-47 ExperimentSpec is a Library kind on the coordinated lane only "
            "(FR-W17, DEC-0271)",
            kind=member.kind,
            contract=member.contract,
            coordinated_lane_only=True,
            is_library_kind=False,
            present_as_registry=False,
            owner=KIND_OWNER,
        )
    return Ok(member)


def _canonical_library(token: str) -> str | None:
    folded = _fold(token)
    aliased = _KIND_ALIASES.get(folded)
    if aliased in _BY_KIND:
        return aliased
    if token in _BY_KIND:
        return token
    return None


def _canonical_refused(kind: object) -> str | None:
    token = clean_token(kind)
    if token is None:
        return None
    folded = _fold(token)
    if folded in _REFUSED_ALIASES:
        return _REFUSED_ALIASES[folded]
    if token in NOT_LIBRARY_KIND_NAMES:
        return token
    return None


def _refuse_not_library(kind: str, *, present_as_registry: object) -> TypedRefusal:
    _ = present_as_registry
    if kind == "strats":
        return policy(
            "kind",
            "STRATS remains a KnowledgeSource corpus (QMA AD-19) and writes no "
            "registry kinds (FR-W18, DEC-0271)",
            kind=kind,
            is_library_kind=False,
            present_as_registry=False,
            strats_corpus=STRATS_CORPUS,
            writes_registry_kinds=False,
            owner=KIND_OWNER,
        )
    if kind == "logic-source-manifest":
        return policy(
            "kind",
            "logic source-manifests are cited from CT-33, not a separate Library "
            "kind (FR-W17, DEC-0271, UX-DR1)",
            kind=kind,
            is_library_kind=False,
            present_as_registry=False,
            cites=LOGIC_SOURCE_MANIFEST_CITES,
            owner=KIND_OWNER,
        )
    if kind in {"project", "workspace"}:
        return policy(
            "kind",
            "there is no Project kind and no Workspace kind; display names remain "
            "aliases (FR-W16, FR-W18, DEC-0284)",
            kind=kind,
            is_library_kind=False,
            present_as_registry=False,
            display_alias=True,
            owner=KIND_OWNER,
        )
    return policy(
        "kind",
        "not a Library kind; a later UI must not present this as a registry "
        "record (FR-W18, UX-DR2, DEC-0271)",
        kind=kind,
        is_library_kind=False,
        present_as_registry=False,
        owner=KIND_OWNER,
        legal=list(LIBRARY_KIND_NAMES),
    )


def _refuse_package(kind: object) -> TypedRefusal:
    return policy(
        "kind",
        "there is no COMP-LIB / qmx-library package; kind owner remains "
        "COMP-QMF-REGISTRY (FR-W01, DEC-0271)",
        given=repr(kind),
        is_library_kind=False,
        mints_comp_lib=False,
        present_as_registry=False,
        qmx_library_package=False,
        owner=KIND_OWNER,
    )


def _coerce_lane(lane: object) -> str | TypedRefusal | None:
    if lane is None:
        return None
    token = clean_token(lane)
    if token is None:
        return invalid(
            "lane",
            "lane is ungoverned, governed, or coordinated when supplied",
            given=repr(lane),
        )
    folded = _fold(token)
    if folded not in _LEGAL_LANES:
        return invalid(
            "lane",
            "lane is ungoverned, governed, or coordinated when supplied",
            given=token,
            legal=sorted(_LEGAL_LANES),
        )
    return folded


def _fold(token: str) -> str:
    return token.casefold().replace("_", "-").replace(" ", "-")


def _truthy(value: object) -> bool:
    if value is None or value is False:
        return False
    return not (isinstance(value, str) and value.strip() == "")
