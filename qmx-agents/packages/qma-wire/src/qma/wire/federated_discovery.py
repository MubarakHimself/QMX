"""Federated discovery hit DTO — KnowledgeHit | ArtifactHit | ContributionHit.

COMP-QMA-WIRE owns the frozen federated hit shape as an additive CT-40 family
format mint (Story 53.1; FR-WF-01..03, FR-WF-13). No new CT number is minted
(do not mint CT-52). ``hit_class: strats``, ``qml_candidate``, hypothesis kinds,
and cite-copy ``artifact_ref`` as an Artifact-rail hit are refused (DEC-0389
named-amended by DEC-0449; DEC-0412 stays dead; UX-DR2). ``view:*`` is not a
ContributionHit (GAP-0081). KnowledgeHit display aliases must not say
``hypothesis`` or ``research candidate``; viewing cited seed does not mint
``research_ref`` (Story 52.3; FR-RES-25). ContributionHit identity is the live
``published_contributions()`` tuple and is never fp1, never a registry kind,
and never ``ArtifactHit.kind`` (DEC-0415; SCN-0018).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qma.core.ports.cardinality import (
    MULTI_CONTRIBUTION_POINTS,
    PortError,
    validate_contribution_point,
)
from qma.core.ports.extensibility import (
    UI_CONTRIBUTION_POINTS,
    UI_VIEW_CONTRIBUTION_POINT,
    is_ui_contribution_point,
)
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_refusal,
)

__all__ = [
    "ARTIFACT_HIT_KINDS",
    "ARTIFACT_QUERY_HIT_TAGS",
    "ARTIFACT_ROSTER_KINDS",
    "CONTRIBUTION_AVAILABILITY",
    "CONTRIBUTION_HIT_POINTS",
    "CONTRIBUTION_HIT_WIRED_AT_INSPECT_SHA",
    "FEDERATED_HIT_CLASSES",
    "FEDERATED_HIT_CONTRACT",
    "FEDERATED_HIT_DTO_OWNER",
    "FEDERATED_HIT_INSPECT_SHA",
    "FEDERATED_HIT_NEW_CT_MINTED",
    "FEDERATED_HIT_REFUSED_CT",
    "FEDERATED_HIT_SCHEMA",
    "FEDERATED_HIT_SCHEMA_FILE",
    "FEDERATED_HIT_SCHEMA_NAME",
    "HIT_CLASS_ARTIFACT",
    "HIT_CLASS_CONTRIBUTION",
    "HIT_CLASS_KNOWLEDGE",
    "HYPOTHESIS_LISTING_SURFACE",
    "KNOWLEDGE_HIT_ALLOWED_DISPLAY_ALIASES",
    "KNOWLEDGE_HIT_FORBIDDEN_DISPLAY_TOKENS",
    "REFUSED_HIT_CLASSES",
    "VIEWING_CITED_SEED_MINTS_RESEARCH_REF",
    "ArtifactHit",
    "ContributionHit",
    "FederatedHit",
    "KnowledgeHit",
    "library_kind_to_artifact_hit_kind",
    "parse_federated_hit",
    "refuse_cite_copy_artifact_rail",
    "refuse_contribution_fp1_identity",
    "refuse_hypothesis_hit_class",
    "refuse_knowledge_hit_display_alias",
    "refuse_qml_candidate_hit",
    "refuse_strats_hit_class",
    "refuse_view_contribution_hit",
    "resolve_knowledge_hit_display_alias",
    "validate_federated_hit",
    "viewing_cited_seed_mints_research_ref",
]


FEDERATED_HIT_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
FEDERATED_HIT_CONTRACT: Final[str] = "CT-40"
FEDERATED_HIT_NEW_CT_MINTED: Final[bool] = False
FEDERATED_HIT_REFUSED_CT: Final[str] = "CT-52"
FEDERATED_HIT_SCHEMA: Final[str] = "qma.wire.federated_hit.v1"
FEDERATED_HIT_SCHEMA_NAME: Final[str] = "federated_hit"
FEDERATED_HIT_SCHEMA_FILE: Final[str] = "federated_hit.v1.schema.json"
# Inspect SHA honesty (DEC-0450; SCN-0018 Branch D): ContributionHit was not a
# wired federated class at integration@270e992. This story mints the third class.
FEDERATED_HIT_INSPECT_SHA: Final[str] = "270e992"
CONTRIBUTION_HIT_WIRED_AT_INSPECT_SHA: Final[bool] = False

HIT_CLASS_KNOWLEDGE: Final[str] = "knowledge"
HIT_CLASS_ARTIFACT: Final[str] = "artifact"
HIT_CLASS_CONTRIBUTION: Final[str] = "contribution"
FEDERATED_HIT_CLASSES: Final[frozenset[str]] = frozenset(
    {HIT_CLASS_KNOWLEDGE, HIT_CLASS_ARTIFACT, HIT_CLASS_CONTRIBUTION}
)
HYPOTHESIS_LISTING_SURFACE: Final[str] = "qml.research"
CONTRIBUTION_HIT_POINTS: Final[frozenset[str]] = MULTI_CONTRIBUTION_POINTS
CONTRIBUTION_AVAILABILITY: Final[frozenset[str]] = frozenset(
    {"enabled", "disabled", "unavailable", "tombstone"}
)

# Workbench AD-3 Library kind roster (Story 34.1). Listed here so qma-wire does
# not import COMP-QMB; kinds stay closed-and-addable on the wire DTO.
ARTIFACT_ROSTER_KINDS: Final[frozenset[str]] = frozenset(
    {
        "bot-definition",
        "confluence",
        "strategy-family",
        "book-definition",
        "bms-definition",
        "book-binding",
        "split-manifest",
        "source-observation",
        "performance-result",
        "experiment-spec",
    }
)

# Closed query-hit tags — live tokens; not registry kinds (FR-RES-07; FR-W19).
ARTIFACT_QUERY_HIT_TAGS: Final[frozenset[str]] = frozenset({"saved-view", "analysis.published"})

ARTIFACT_HIT_KINDS: Final[frozenset[str]] = frozenset(
    ARTIFACT_ROSTER_KINDS | ARTIFACT_QUERY_HIT_TAGS
)

REFUSED_HIT_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "strats",
        "qml_candidate",
        "qml-candidate",
        "QmlCandidateHit",
        "hypothesis",
        "HypothesisHit",
    }
)

# UX-DR2: KnowledgeHit rendering aliases must never imply a Stage 0 hypothesis.
KNOWLEDGE_HIT_FORBIDDEN_DISPLAY_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "hypothesis",
        "research candidate",
        "research_candidate",
        "research-candidate",
        "qml_candidate",
        "qml-candidate",
        "entry_hypothesis",
    }
)

# Safe Knowledge-rail labels only — seed cites, never mill identity nouns.
KNOWLEDGE_HIT_ALLOWED_DISPLAY_ALIASES: Final[frozenset[str]] = frozenset(
    {
        "knowledge",
        "seed",
        "seed cite",
        "seed corpus",
        "cite",
        "citation",
        "dictionary entry",
        "locator",
    }
)

VIEWING_CITED_SEED_MINTS_RESEARCH_REF: Final[bool] = False

_REFUSED_TYPE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "QmlCandidateHit",
        "qml_candidate",
        "StratsHit",
        "strats",
        "HypothesisHit",
        "hypothesis",
    }
)

_FORBIDDEN_ARTIFACT_KEYS: Final[frozenset[str]] = frozenset({"artifact_ref"})

# Contribution identity is the published tuple — never Artifact/Knowledge rails.
_FORBIDDEN_CONTRIBUTION_IDENTITY_KEYS: Final[frozenset[str]] = frozenset(
    {
        "fp1",
        "kind",
        "artifact_ref",
        "source_ref",
        "snapshot_ref",
        "locator",
        "research_ref",
    }
)

_HYPOTHESIS_KIND_TOKENS: Final[frozenset[str]] = frozenset(
    {
        "hypothesis",
        "entry_hypothesis",
        "entry-hypothesis",
        "qml-research-hypothesis",
        "qml_research_hypothesis",
        "research_candidate",
        "research-candidate",
        "research candidate",
        "qml_candidate",
        "qml-candidate",
    }
)

_VIEW_POINT_TOKENS: Final[frozenset[str]] = (
    frozenset({"view", "views", "ui_view", "ui-view", "ui_view_contribution"})
    | UI_CONTRIBUTION_POINTS
)

# QMB library.search citation kinds → frozen ArtifactHit query-hit tags.
_LIBRARY_KIND_TO_ARTIFACT_HIT: Final[Mapping[str, str]] = MappingProxyType(
    {
        "analysis-publication": "analysis.published",
        "analysis.published": "analysis.published",
        "analysis-published": "analysis.published",
        "saved-view": "saved-view",
        "savedview": "saved-view",
    }
)


def library_kind_to_artifact_hit_kind(kind: str) -> str:
    """Map a QMB ``library.search`` kind token onto the frozen ArtifactHit kind."""
    token = kind.strip()
    mapped = _LIBRARY_KIND_TO_ARTIFACT_HIT.get(token)
    if mapped is not None:
        return mapped
    folded = token.casefold().replace("_", "-")
    mapped = _LIBRARY_KIND_TO_ARTIFACT_HIT.get(folded)
    if mapped is not None:
        return mapped
    return token


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


def refuse_strats_hit_class(**extra: object) -> TypedRefusal:
    """``hit_class: strats`` stays dead (DEC-0412; AR-RES-05)."""
    return _policy(
        "hit_class",
        "hit_class strats is refused; federated discovery admits knowledge, "
        "artifact, and contribution (DEC-0412; FR-RES-07; DEC-0449)",
        hit_class="strats",
        decision="DEC-0412",
        dead=True,
        **extra,
    )


def refuse_qml_candidate_hit(**extra: object) -> TypedRefusal:
    """``QmlCandidateHit`` / ``qml_candidate`` is not a federated hit class."""
    return _policy(
        "hit_class",
        "qml_candidate / QmlCandidateHit is refused; hypotheses stay on the QML "
        "research surface, never a federated hit class (DEC-0412; FR-RES-07; "
        "DEC-0449)",
        hit_class="qml_candidate",
        decision="DEC-0412",
        dead=True,
        listing_surface=HYPOTHESIS_LISTING_SURFACE,
        **extra,
    )


def refuse_hypothesis_hit_class(**extra: object) -> TypedRefusal:
    """Hypothesis kinds stay on ``qml.research`` (Story 52.3; DEC-0412)."""
    field = str(extra.pop("field", "hit_class"))
    return _policy(
        field,
        "hypothesis kinds stay on qml.research; they are not a federated hit "
        "class (DEC-0412; Story 52.3; DEC-0449)",
        hit_class="hypothesis",
        decision="DEC-0412",
        dead=True,
        listing_surface=HYPOTHESIS_LISTING_SURFACE,
        **extra,
    )


def refuse_view_contribution_hit(**extra: object) -> TypedRefusal:
    """``view:*`` / ``ui_view`` is not a ContributionHit (GAP-0081; AD-17)."""
    field = str(extra.pop("field", "point"))
    return _policy(
        field,
        "view:* is a wire DTO only until GAP-0081; it is not a plugin "
        "contribution point and not a ContributionHit (AD-17; GAP-0081)",
        gap="GAP-0081",
        ui_view_minted=False,
        contribution_point=UI_VIEW_CONTRIBUTION_POINT,
        **extra,
    )


def refuse_contribution_fp1_identity(**extra: object) -> TypedRefusal:
    """Contribution identity is never fp1 / registry kind / ArtifactHit.kind."""
    field = str(extra.pop("field", "identity"))
    return _policy(
        field,
        "ContributionHit identity is the live published_contributions() tuple "
        "and is never fp1, never a registry kind, and never ArtifactHit.kind "
        "(DEC-0415; FR-WF-03; SCN-0018)",
        decision="DEC-0415",
        **extra,
    )


def refuse_cite_copy_artifact_rail(**extra: object) -> TypedRefusal:
    """Cite-copy ``artifact_ref`` is not an Artifact-rail discovery hit (AD-9)."""
    return _policy(
        "artifact_ref",
        "cite-copy artifact_ref on a Citation is not an Artifact-rail hit; "
        "durable Knowledge detail still requires a Citation after cite "
        "(AD-9; FR-RES-07; DEC-0389)",
        **extra,
    )


def refuse_knowledge_hit_display_alias(**extra: object) -> TypedRefusal:
    """Refuse KnowledgeHit labels that say hypothesis / research candidate."""
    return _policy(
        "display_alias",
        "KnowledgeHit display aliases must not say 'hypothesis' or "
        "'research candidate'; seed cites stay on the Knowledge rail "
        "(UX-DR2; FR-RES-07; DEC-0389)",
        forbidden=sorted(KNOWLEDGE_HIT_FORBIDDEN_DISPLAY_TOKENS),
        allowed=sorted(KNOWLEDGE_HIT_ALLOWED_DISPLAY_ALIASES),
        **extra,
    )


def viewing_cited_seed_mints_research_ref() -> bool:
    """Viewing cited seed is not a save and never mints ``research_ref``."""
    return VIEWING_CITED_SEED_MINTS_RESEARCH_REF


def resolve_knowledge_hit_display_alias(alias: object) -> Result[str]:
    """Admit a KnowledgeHit render alias; refuse mill-identity nouns (UX-DR2)."""
    if not isinstance(alias, str) or alias.strip() == "":
        return _invalid(
            "display_alias",
            "KnowledgeHit display alias is a non-empty string (UX-DR2)",
            given=repr(alias),
        )
    token = alias.strip()
    folded = token.casefold().replace("_", " ").replace("-", " ")
    compact = folded.replace(" ", "")
    for forbidden in KNOWLEDGE_HIT_FORBIDDEN_DISPLAY_TOKENS:
        forbid_fold = forbidden.casefold().replace("_", " ").replace("-", " ")
        if folded == forbid_fold or compact == forbid_fold.replace(" ", ""):
            return refuse_knowledge_hit_display_alias(given=token, matched=forbidden)
        if forbid_fold in folded:
            return refuse_knowledge_hit_display_alias(given=token, matched=forbidden)
    if folded not in {item.casefold() for item in KNOWLEDGE_HIT_ALLOWED_DISPLAY_ALIASES}:
        return refuse_knowledge_hit_display_alias(given=token, matched="unknown")
    # Preserve the canonical spelling from the closed allow-list.
    for allowed in KNOWLEDGE_HIT_ALLOWED_DISPLAY_ALIASES:
        if allowed.casefold() == folded:
            return Ok(allowed)
    return Ok(token)


def _parse_nonempty_str(value: object, field: str) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            field,
            f"{field} is a non-empty string on the federated hit DTO (CT-40; FR-RES-07)",
            given=repr(value),
        )
    return Ok(value.strip())


def _parse_fp1(value: object) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return _invalid(
            "fp1",
            "ArtifactHit.fp1 is an fp1:sha256:<hex> fingerprint (CT-40; FR-RES-07)",
            given=repr(value),
        )
    return parsed


def _refuse_hit_class(token: str) -> TypedRefusal:
    folded = token.strip()
    lower = folded.casefold().replace("_", "-")
    if folded == "strats" or lower == "strats":
        return refuse_strats_hit_class(given=folded)
    if folded in {"qml_candidate", "QmlCandidateHit"} or lower in {
        "qml-candidate",
        "qmlcandidatehit",
    }:
        return refuse_qml_candidate_hit(given=folded)
    if folded in {"hypothesis", "HypothesisHit"} or lower in {
        "hypothesis",
        "hypothesishit",
        "entry-hypothesis",
        "entry_hypothesis",
    }:
        return refuse_hypothesis_hit_class(given=folded)
    if lower.startswith("view") or lower in {item.casefold() for item in _VIEW_POINT_TOKENS}:
        return refuse_view_contribution_hit(field="hit_class", given=folded)
    return _policy(
        "hit_class",
        "federated discovery hits are exactly KnowledgeHit, ArtifactHit, or "
        "ContributionHit; no other hit_class is admitted (FR-WF-01; DEC-0449; "
        "DEC-0412)",
        given=folded,
        legal=sorted(FEDERATED_HIT_CLASSES),
    )


def _looks_like_fp1(value: str) -> bool:
    return value.strip().casefold().startswith("fp1:")


def _is_view_contribution_point(token: str) -> bool:
    folded = token.strip().casefold().replace("_", "-")
    if folded.startswith("view:") or folded.startswith("view/"):
        return True
    if folded in {item.casefold().replace("_", "-") for item in _VIEW_POINT_TOKENS}:
        return True
    return is_ui_contribution_point(token) or is_ui_contribution_point(token.strip())


def _parse_availability_revision(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(
            "availability_revision",
            "ContributionHit.availability_revision is a non-negative integer (CT-40; FR-WF-02)",
            given=repr(value),
        )
    if value < 0:
        return _invalid(
            "availability_revision",
            "ContributionHit.availability_revision is a non-negative integer (CT-40; FR-WF-02)",
            given=value,
        )
    return Ok(value)


def _parse_contribution_point(value: object) -> Result[str]:
    parsed = _parse_nonempty_str(value, "point")
    if is_refusal(parsed):
        return parsed
    token = parsed.value
    folded = token.casefold().replace("_", "-")
    if folded in {item.casefold().replace("_", "-") for item in _HYPOTHESIS_KIND_TOKENS}:
        return refuse_hypothesis_hit_class(field="point", given=token)
    if _is_view_contribution_point(token):
        return refuse_view_contribution_hit(given=token, point=token)
    try:
        return Ok(validate_contribution_point(token))
    except PortError:
        return _policy(
            "point",
            "ContributionHit.point is one of the eight multi contribution "
            "points; view:* / ui_view is GAP-0081 and not a ContributionHit "
            "(AD-2; GAP-0081; FR-WF-02)",
            given=token,
            legal=sorted(CONTRIBUTION_HIT_POINTS),
            gap="GAP-0081",
        )


def _parse_contribution_id_field(value: object, field: str) -> Result[str]:
    parsed = _parse_nonempty_str(value, field)
    if is_refusal(parsed):
        return parsed
    token = parsed.value
    if _looks_like_fp1(token):
        return refuse_contribution_fp1_identity(field=field, given=token)
    return Ok(token)


def _parse_availability(value: object) -> Result[str]:
    parsed = _parse_nonempty_str(value, "availability")
    if is_refusal(parsed):
        return parsed
    token = parsed.value
    if token not in CONTRIBUTION_AVAILABILITY:
        return _policy(
            "availability",
            "ContributionHit.availability is enabled | disabled | unavailable | "
            "tombstone (CT-40; FR-WF-02)",
            given=token,
            legal=sorted(CONTRIBUTION_AVAILABILITY),
        )
    return Ok(token)


@dataclass(frozen=True, slots=True)
class KnowledgeHit:
    """Knowledge-rail federated hit (CT-44 cite handles; CT-40 wire DTO)."""

    source_ref: str
    snapshot_ref: str
    locator: str
    hit_class: str = HIT_CLASS_KNOWLEDGE

    @classmethod
    def try_create(
        cls,
        *,
        source_ref: object,
        snapshot_ref: object,
        locator: object,
        hit_class: object = HIT_CLASS_KNOWLEDGE,
    ) -> Result[KnowledgeHit]:
        """Validate a KnowledgeHit. Refuses non-knowledge hit_class values."""
        if hit_class != HIT_CLASS_KNOWLEDGE:
            if isinstance(hit_class, str):
                return _refuse_hit_class(hit_class)
            return _invalid(
                "hit_class",
                "KnowledgeHit.hit_class is exactly 'knowledge'",
                given=repr(hit_class),
            )
        source = _parse_nonempty_str(source_ref, "source_ref")
        if is_refusal(source):
            return source
        snapshot = _parse_nonempty_str(snapshot_ref, "snapshot_ref")
        if is_refusal(snapshot):
            return snapshot
        loc = _parse_nonempty_str(locator, "locator")
        if is_refusal(loc):
            return loc
        return Ok(
            cls(
                hit_class=HIT_CLASS_KNOWLEDGE,
                source_ref=source.value,
                snapshot_ref=snapshot.value,
                locator=loc.value,
            )
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "hit_class": self.hit_class,
                "locator": self.locator,
                "snapshot_ref": self.snapshot_ref,
                "source_ref": self.source_ref,
            }
        )


@dataclass(frozen=True, slots=True)
class ArtifactHit:
    """Artifact-rail federated hit (Workbench AD-3 roster or query-hit tags)."""

    fp1: Fingerprint
    kind: str
    hit_class: str = HIT_CLASS_ARTIFACT

    @classmethod
    def try_create(
        cls,
        *,
        fp1: object,
        kind: object,
        hit_class: object = HIT_CLASS_ARTIFACT,
        artifact_ref: object = None,
    ) -> Result[ArtifactHit]:
        """Validate an ArtifactHit. Refuses cite-copy artifact_ref and bad kinds."""
        if artifact_ref is not None:
            return refuse_cite_copy_artifact_rail(given=repr(artifact_ref))
        if hit_class != HIT_CLASS_ARTIFACT:
            if isinstance(hit_class, str):
                return _refuse_hit_class(hit_class)
            return _invalid(
                "hit_class",
                "ArtifactHit.hit_class is exactly 'artifact'",
                given=repr(hit_class),
            )
        fingerprint = _parse_fp1(fp1)
        if is_refusal(fingerprint):
            return fingerprint
        kind_token = _parse_nonempty_str(kind, "kind")
        if is_refusal(kind_token):
            return kind_token
        if kind_token.value not in ARTIFACT_HIT_KINDS:
            if kind_token.value == "strats":
                return refuse_strats_hit_class(field="kind", given=kind_token.value)
            return _policy(
                "kind",
                "ArtifactHit.kind is a Workbench AD-3 roster kind or closed "
                "query-hit tag saved-view | analysis.published (not registry "
                "kinds for the tags) (FR-RES-07; DEC-0389)",
                given=kind_token.value,
                legal=sorted(ARTIFACT_HIT_KINDS),
            )
        return Ok(
            cls(
                hit_class=HIT_CLASS_ARTIFACT,
                fp1=fingerprint.value,
                kind=kind_token.value,
            )
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "fp1": self.fp1.value,
                "hit_class": self.hit_class,
                "kind": self.kind,
            }
        )


@dataclass(frozen=True, slots=True)
class ContributionHit:
    """Live published-contribution federated hit (CT-40 format mint; FR-WF-02).

    Identity is the ``published_contributions()`` tuple, never fp1, never a
    registry kind, and never ``ArtifactHit.kind`` (DEC-0415; SCN-0018).
    """

    plugin_id: str
    point: str
    qualified_id: str
    package_id: str
    package_version: str
    availability_revision: int
    availability: str
    hit_class: str = HIT_CLASS_CONTRIBUTION

    @classmethod
    def try_create(
        cls,
        *,
        plugin_id: object,
        point: object,
        qualified_id: object,
        package_id: object,
        package_version: object,
        availability_revision: object,
        availability: object,
        hit_class: object = HIT_CLASS_CONTRIBUTION,
        fp1: object = None,
        kind: object = None,
        artifact_ref: object = None,
        **extra: object,
    ) -> Result[ContributionHit]:
        """Validate a ContributionHit. Refuses fp1 / kind / view:* identity."""
        if fp1 is not None:
            return refuse_contribution_fp1_identity(field="fp1", given=repr(fp1))
        if kind is not None:
            return refuse_contribution_fp1_identity(field="kind", given=repr(kind))
        if artifact_ref is not None:
            return refuse_cite_copy_artifact_rail(given=repr(artifact_ref))
        stolen = sorted(key for key in extra if key in _FORBIDDEN_CONTRIBUTION_IDENTITY_KEYS)
        if stolen:
            return refuse_contribution_fp1_identity(fields=stolen, given=stolen)
        if hit_class != HIT_CLASS_CONTRIBUTION:
            if isinstance(hit_class, str):
                return _refuse_hit_class(hit_class)
            return _invalid(
                "hit_class",
                "ContributionHit.hit_class is exactly 'contribution'",
                given=repr(hit_class),
            )
        plugin = _parse_contribution_id_field(plugin_id, "plugin_id")
        if is_refusal(plugin):
            return plugin
        point_token = _parse_contribution_point(point)
        if is_refusal(point_token):
            return point_token
        qualified = _parse_contribution_id_field(qualified_id, "qualified_id")
        if is_refusal(qualified):
            return qualified
        package = _parse_contribution_id_field(package_id, "package_id")
        if is_refusal(package):
            return package
        version = _parse_contribution_id_field(package_version, "package_version")
        if is_refusal(version):
            return version
        revision = _parse_availability_revision(availability_revision)
        if is_refusal(revision):
            return revision
        avail = _parse_availability(availability)
        if is_refusal(avail):
            return avail
        return Ok(
            cls(
                hit_class=HIT_CLASS_CONTRIBUTION,
                plugin_id=plugin.value,
                point=point_token.value,
                qualified_id=qualified.value,
                package_id=package.value,
                package_version=version.value,
                availability_revision=revision.value,
                availability=avail.value,
            )
        )

    def published_identity(self) -> tuple[str, str, str, str, str, int, str]:
        """Live ``published_contributions()`` tuple — never fp1."""
        return (
            self.plugin_id,
            self.point,
            self.qualified_id,
            self.package_id,
            self.package_version,
            self.availability_revision,
            self.availability,
        )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "availability": self.availability,
                "availability_revision": self.availability_revision,
                "hit_class": self.hit_class,
                "package_id": self.package_id,
                "package_version": self.package_version,
                "plugin_id": self.plugin_id,
                "point": self.point,
                "qualified_id": self.qualified_id,
            }
        )


type FederatedHit = KnowledgeHit | ArtifactHit | ContributionHit


def _widen_knowledge(result: Result[KnowledgeHit]) -> Result[FederatedHit]:
    """Re-box a KnowledgeHit Result as the federated union (Ok is invariant)."""
    if is_refusal(result):
        return result
    hit: FederatedHit = result.value
    return Ok(hit)


def _widen_artifact(result: Result[ArtifactHit]) -> Result[FederatedHit]:
    """Re-box an ArtifactHit Result as the federated union (Ok is invariant)."""
    if is_refusal(result):
        return result
    hit: FederatedHit = result.value
    return Ok(hit)


def _widen_contribution(result: Result[ContributionHit]) -> Result[FederatedHit]:
    """Re-box a ContributionHit Result as the federated union (Ok is invariant)."""
    if is_refusal(result):
        return result
    hit: FederatedHit = result.value
    return Ok(hit)


def parse_federated_hit(value: object) -> Result[FederatedHit]:
    """Parse a frozen federated hit; refuse every other hit_class or shape."""
    if isinstance(value, KnowledgeHit):
        return _widen_knowledge(
            KnowledgeHit.try_create(
                source_ref=value.source_ref,
                snapshot_ref=value.snapshot_ref,
                locator=value.locator,
                hit_class=value.hit_class,
            )
        )
    if isinstance(value, ArtifactHit):
        return _widen_artifact(
            ArtifactHit.try_create(
                fp1=value.fp1,
                kind=value.kind,
                hit_class=value.hit_class,
            )
        )
    if isinstance(value, ContributionHit):
        return _widen_contribution(
            ContributionHit.try_create(
                plugin_id=value.plugin_id,
                point=value.point,
                qualified_id=value.qualified_id,
                package_id=value.package_id,
                package_version=value.package_version,
                availability_revision=value.availability_revision,
                availability=value.availability,
                hit_class=value.hit_class,
            )
        )
    if not isinstance(value, Mapping):
        type_name = type(value).__name__
        if type_name in _REFUSED_TYPE_NAMES:
            if "strats" in type_name.casefold():
                return refuse_strats_hit_class(given=type_name)
            if "hypothesis" in type_name.casefold():
                return refuse_hypothesis_hit_class(given=type_name)
            return refuse_qml_candidate_hit(given=type_name)
        return _invalid(
            "hit",
            "a federated hit is a KnowledgeHit, ArtifactHit, or ContributionHit "
            "mapping (CT-40; FR-WF-01)",
            given=repr(type_name),
        )

    body = cast("Mapping[str, object]", value)
    if "type" in body and isinstance(body["type"], str):
        type_token = body["type"]
        folded_type = type_token.casefold().replace("_", "")
        if type_token in _REFUSED_TYPE_NAMES or folded_type in {
            "qmlcandidatehit",
            "qmlcandidate",
            "stratshit",
            "hypothesishit",
        }:
            if "strats" in type_token.casefold():
                return refuse_strats_hit_class(given=type_token)
            if "hypothesis" in type_token.casefold():
                return refuse_hypothesis_hit_class(given=type_token)
            return refuse_qml_candidate_hit(given=type_token)

    hit_class = body.get("hit_class")
    if not isinstance(hit_class, str) or hit_class.strip() == "":
        return _invalid(
            "hit_class",
            "federated hit requires hit_class knowledge | artifact | contribution (FR-WF-01)",
            given=repr(hit_class),
        )
    token = hit_class.strip()
    if token == HIT_CLASS_KNOWLEDGE:
        if any(key in body for key in _FORBIDDEN_ARTIFACT_KEYS):
            # artifact_ref on a Knowledge payload is cite-copy detail, not a
            # second rail; discovery DTO omits it (AD-9).
            return refuse_cite_copy_artifact_rail(
                hit_class=token,
                given=repr(body.get("artifact_ref")),
            )
        return _widen_knowledge(
            KnowledgeHit.try_create(
                source_ref=body.get("source_ref"),
                snapshot_ref=body.get("snapshot_ref"),
                locator=body.get("locator"),
                hit_class=token,
            )
        )
    if token == HIT_CLASS_ARTIFACT:
        if any(key in body for key in _FORBIDDEN_ARTIFACT_KEYS):
            return refuse_cite_copy_artifact_rail(
                hit_class=token,
                given=repr(body.get("artifact_ref")),
            )
        return _widen_artifact(
            ArtifactHit.try_create(
                fp1=body.get("fp1"),
                kind=body.get("kind"),
                hit_class=token,
            )
        )
    if token == HIT_CLASS_CONTRIBUTION:
        stolen = sorted(key for key in _FORBIDDEN_CONTRIBUTION_IDENTITY_KEYS if key in body)
        if stolen:
            return refuse_contribution_fp1_identity(
                hit_class=token,
                fields=stolen,
                given=stolen,
            )
        return _widen_contribution(
            ContributionHit.try_create(
                plugin_id=body.get("plugin_id"),
                point=body.get("point"),
                qualified_id=body.get("qualified_id"),
                package_id=body.get("package_id"),
                package_version=body.get("package_version"),
                availability_revision=body.get("availability_revision"),
                availability=body.get("availability"),
                hit_class=token,
            )
        )
    return _refuse_hit_class(token)


def validate_federated_hit(payload: object) -> Result[FederatedHit]:
    """Validate ``payload`` against the named qma-wire schema, then the DTO."""
    from qma.wire.schemas import validate_instance  # noqa: PLC0415

    checked = validate_instance(payload, FEDERATED_HIT_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_federated_hit(checked.value)
