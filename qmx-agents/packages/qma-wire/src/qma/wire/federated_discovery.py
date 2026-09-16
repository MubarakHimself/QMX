"""Federated discovery hit DTO — KnowledgeHit | ArtifactHit only (CT-40; FR-RES-07).

COMP-QMA-WIRE owns the frozen federated hit shape as an additive CT-40 family.
No new CT number is minted. ``hit_class: strats``, ``qml_candidate``, and
cite-copy ``artifact_ref`` as an Artifact-rail hit are refused (DEC-0389,
DEC-0412; UX-DR2).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

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
    "FEDERATED_HIT_CLASSES",
    "FEDERATED_HIT_CONTRACT",
    "FEDERATED_HIT_DTO_OWNER",
    "FEDERATED_HIT_NEW_CT_MINTED",
    "FEDERATED_HIT_SCHEMA",
    "FEDERATED_HIT_SCHEMA_FILE",
    "FEDERATED_HIT_SCHEMA_NAME",
    "HIT_CLASS_ARTIFACT",
    "HIT_CLASS_KNOWLEDGE",
    "REFUSED_HIT_CLASSES",
    "ArtifactHit",
    "FederatedHit",
    "KnowledgeHit",
    "library_kind_to_artifact_hit_kind",
    "parse_federated_hit",
    "refuse_cite_copy_artifact_rail",
    "refuse_qml_candidate_hit",
    "refuse_strats_hit_class",
    "validate_federated_hit",
]


FEDERATED_HIT_DTO_OWNER: Final[str] = "COMP-QMA-WIRE"
FEDERATED_HIT_CONTRACT: Final[str] = "CT-40"
FEDERATED_HIT_NEW_CT_MINTED: Final[bool] = False
FEDERATED_HIT_SCHEMA: Final[str] = "qma.wire.federated_hit.v1"
FEDERATED_HIT_SCHEMA_NAME: Final[str] = "federated_hit"
FEDERATED_HIT_SCHEMA_FILE: Final[str] = "federated_hit.v1.schema.json"

HIT_CLASS_KNOWLEDGE: Final[str] = "knowledge"
HIT_CLASS_ARTIFACT: Final[str] = "artifact"
FEDERATED_HIT_CLASSES: Final[frozenset[str]] = frozenset(
    {HIT_CLASS_KNOWLEDGE, HIT_CLASS_ARTIFACT}
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
ARTIFACT_QUERY_HIT_TAGS: Final[frozenset[str]] = frozenset(
    {"saved-view", "analysis.published"}
)

ARTIFACT_HIT_KINDS: Final[frozenset[str]] = frozenset(
    ARTIFACT_ROSTER_KINDS | ARTIFACT_QUERY_HIT_TAGS
)

REFUSED_HIT_CLASSES: Final[frozenset[str]] = frozenset(
    {"strats", "qml_candidate", "qml-candidate", "QmlCandidateHit"}
)

_REFUSED_TYPE_NAMES: Final[frozenset[str]] = frozenset(
    {"QmlCandidateHit", "qml_candidate", "StratsHit", "strats"}
)

_FORBIDDEN_ARTIFACT_KEYS: Final[frozenset[str]] = frozenset({"artifact_ref"})

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
        "hit_class strats is refused; federated discovery admits only knowledge "
        "and artifact (DEC-0412; FR-RES-07; DEC-0389)",
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
        "research surface, never a third federated hit class (DEC-0412; FR-RES-07)",
        hit_class="qml_candidate",
        decision="DEC-0412",
        dead=True,
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
    return _policy(
        "hit_class",
        "federated discovery hits are exactly KnowledgeHit or ArtifactHit; no "
        "other hit_class is admitted (FR-RES-07; DEC-0389; DEC-0412)",
        given=folded,
        legal=sorted(FEDERATED_HIT_CLASSES),
    )


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


type FederatedHit = KnowledgeHit | ArtifactHit


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
    if not isinstance(value, Mapping):
        type_name = type(value).__name__
        if type_name in _REFUSED_TYPE_NAMES:
            if "strats" in type_name.casefold():
                return refuse_strats_hit_class(given=type_name)
            return refuse_qml_candidate_hit(given=type_name)
        return _invalid(
            "hit",
            "a federated hit is a KnowledgeHit or ArtifactHit mapping (CT-40; FR-RES-07)",
            given=repr(type_name),
        )

    body = cast("Mapping[str, object]", value)
    if "type" in body and isinstance(body["type"], str):
        type_token = body["type"]
        if type_token in _REFUSED_TYPE_NAMES or type_token.casefold() in {
            "qmlcandidatehit",
            "qml_candidate",
            "stratshit",
        }:
            if "strats" in type_token.casefold():
                return refuse_strats_hit_class(given=type_token)
            return refuse_qml_candidate_hit(given=type_token)

    hit_class = body.get("hit_class")
    if not isinstance(hit_class, str) or hit_class.strip() == "":
        return _invalid(
            "hit_class",
            "federated hit requires hit_class knowledge | artifact (FR-RES-07)",
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
    return _refuse_hit_class(token)


def validate_federated_hit(payload: object) -> Result[FederatedHit]:
    """Validate ``payload`` against the named qma-wire schema, then the DTO."""
    from qma.wire.schemas import validate_instance  # noqa: PLC0415

    checked = validate_instance(payload, FEDERATED_HIT_SCHEMA_NAME)
    if is_refusal(checked):
        return checked
    return parse_federated_hit(checked.value)
