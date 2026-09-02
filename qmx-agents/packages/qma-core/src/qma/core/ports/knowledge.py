"""KnowledgeSource port — singleton per ``source_id`` (CT-44; AD-1, AD-19).

Definitions only. Knowledge is a read-only, provenance-carrying corpus. Search is
literal and locator-based (grep-class); ranking, embeddings and hybrid indexing
stay Deferred GAP-0073. ``evidence_confidence`` is six corpus-owned dimensions —
never scalarized, never derived from Memory's ``admission_confidence``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Protocol, cast, runtime_checkable
from uuid import uuid4

from qma.core.content import tree_digest
from qma.core.refusals import ProvenanceShapeMismatch
from qmf.core import Ok, Result
from qmf.core.fingerprint import Fingerprint, fingerprint_bytes
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_refusal

__all__ = [
    "CITATION_MANDATORY_FIELDS",
    "EVIDENCE_CONFIDENCE_DIMENSION_COUNT",
    "GAP_0073_KNOWLEDGE_HYBRID_INDEXING",
    "KNOWLEDGE_QUERY_SURFACE",
    "KNOWLEDGE_SOURCE_KINDS",
    "KNOWLEDGE_SOURCE_OPERATIONS",
    "PROVENANCE_MANDATORY_FIELDS",
    "Citation",
    "CorpusSnapshot",
    "KnowledgeSource",
    "Provenance",
    "build_corpus_snapshot",
    "literal_search",
    "parse_citation",
    "parse_confidence_dimensions",
    "parse_evidence_confidence",
    "parse_provenance",
    "refuse_evidence_confidence_scalarization",
    "refuse_hybrid_knowledge_indexing",
    "refuse_knowledge_write_back",
    "validate_evidence_confidence_shape",
]


KNOWLEDGE_SOURCE_OPERATIONS: Final[frozenset[str]] = frozenset(
    {"snapshot", "search", "retrieve", "cite"}
)

# Desk-agnostic Tool Registry query surface (CT-44; DEC-0318).
KNOWLEDGE_QUERY_SURFACE: Final[frozenset[str]] = frozenset(
    {"search", "retrieve", "cite"}
)

EVIDENCE_CONFIDENCE_DIMENSION_COUNT: Final[int] = 6

GAP_0073_KNOWLEDGE_HYBRID_INDEXING: Final[str] = "GAP-0073"

# Closed-and-addable source kinds (AD-19 research; qmx_report is re-entry only).
KNOWLEDGE_SOURCE_KINDS: Final[frozenset[str]] = frozenset(
    {
        "plain_file_library",
        "paper",
        "video_transcript",
        "web_research",
        "broker_doc",
        "code_repo",
        "book",
        "market_microstructure_lit",
        "qmx_report",
    }
)

PROVENANCE_MANDATORY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "source_ref",
        "snapshot_ref",
        "locator",
        "evidence_label",
        "evidence_confidence",
    }
)

CITATION_MANDATORY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "source_ref",
        "snapshot_ref",
        "locator",
        "evidence_label",
        "evidence_confidence",
        "artifact_ref",
    }
)


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


def refuse_hybrid_knowledge_indexing(**extra: object) -> TypedRefusal:
    """Ranked / semantic / hybrid retrieval is Deferred GAP-0073 (DEC-0343)."""
    return _policy(
        "retrieval",
        "ranked, semantic or hybrid knowledge indexing is Deferred GAP-0073; "
        "v1 ships literal and locator-based search only (CT-44; FR-Q65; DEC-0343)",
        gap=GAP_0073_KNOWLEDGE_HYBRID_INDEXING,
        deferred=True,
        **extra,
    )


def refuse_evidence_confidence_scalarization(**extra: object) -> TypedRefusal:
    """Six evidence_confidence dimensions are never averaged or scalarized."""
    return _policy(
        "evidence_confidence",
        "evidence_confidence is exactly six corpus-owned dimensions stored and "
        "surfaced verbatim; never averaged, compared across sources or "
        "scalarized into one number (CT-44; FR-Q65; DEC-0318)",
        **extra,
    )


def refuse_knowledge_write_back(**extra: object) -> TypedRefusal:
    """Knowledge sources are read-only; QMX never writes the library."""
    return _policy(
        "write",
        "KnowledgeSource is read-only; QMX adapts to the library and never "
        "writes back, imposes folders/fields or hardcodes layout "
        "(CT-44; FR-Q65; DEC-0318)",
        **extra,
    )


def parse_confidence_dimensions(value: object) -> Result[tuple[str, ...]]:
    """Parse exactly six non-empty dimension keys fixed for a source_id."""
    if isinstance(value, str):
        return _invalid(
            "confidence_dimensions",
            "confidence_dimensions is a sequence of exactly six keys (CT-44; DEC-0318)",
            given=repr(value),
        )
    if not isinstance(value, Sequence):
        return _invalid(
            "confidence_dimensions",
            "confidence_dimensions is a sequence of exactly six keys (CT-44; DEC-0318)",
            given=repr(type(value).__name__),
        )
    keys: list[str] = []
    for item in cast("Sequence[object]", value):
        if not isinstance(item, str) or item.strip() == "":
            return _invalid(
                "confidence_dimensions",
                "each confidence dimension key is a non-empty string (CT-44)",
                given=repr(item),
            )
        key = item.strip()
        if key in keys:
            return _invalid(
                "confidence_dimensions",
                "confidence_dimensions keys must be unique (CT-44; DEC-0318)",
                duplicate=key,
            )
        keys.append(key)
    if len(keys) != EVIDENCE_CONFIDENCE_DIMENSION_COUNT:
        return _invalid(
            "confidence_dimensions",
            "confidence_dimensions declares exactly six keys fixed for the "
            "source_id life (CT-44; DEC-0318)",
            given_count=len(keys),
            expected_count=EVIDENCE_CONFIDENCE_DIMENSION_COUNT,
        )
    return Ok(tuple(keys))


def parse_evidence_confidence(
    value: object,
    *,
    declared_keys: Sequence[str],
    source_id: str,
) -> Result[Mapping[str, object]]:
    """Validate evidence_confidence against the source's declared six keys."""
    shape = validate_evidence_confidence_shape(
        value,
        declared_keys=declared_keys,
        source_id=source_id,
    )
    if is_refusal(shape):
        return shape
    body = cast("Mapping[str, object]", value)
    return Ok(MappingProxyType({key: body[key] for key in declared_keys}))


def validate_evidence_confidence_shape(
    value: object,
    *,
    declared_keys: Sequence[str],
    source_id: str,
) -> Result[None]:
    """Return ``ProvenanceShapeMismatch`` when key set or count differs."""
    expected = tuple(declared_keys)
    if len(expected) != EVIDENCE_CONFIDENCE_DIMENSION_COUNT:
        return _invalid(
            "confidence_dimensions",
            "source declaration must carry exactly six confidence_dimensions "
            "(CT-44; DEC-0318)",
            source_id=source_id,
            given_count=len(expected),
        )
    if not isinstance(value, Mapping):
        return ProvenanceShapeMismatch.of(
            source_id=source_id,
            expected_keys=expected,
            given_keys=(),
        )
    body = cast("Mapping[str, object]", value)
    given = tuple(sorted(str(key) for key in body.keys()))
    expected_sorted = tuple(sorted(expected))
    if given != expected_sorted or len(body) != EVIDENCE_CONFIDENCE_DIMENSION_COUNT:
        return ProvenanceShapeMismatch.of(
            source_id=source_id,
            expected_keys=expected,
            given_keys=tuple(str(key) for key in body.keys()),
        )
    return Ok(None)


def _parse_nonempty_str(value: object, field: str) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            field,
            f"{field} is a mandatory non-empty string (CT-44; DEC-0318)",
            given=repr(value),
        )
    return Ok(value.strip())


@dataclass(frozen=True, slots=True)
class CorpusSnapshot:
    """Content-addressed corpus snapshot (CT-44; AD-19).

    ``id`` is ``fp1`` over the canonical manifest of per-file ``fp1`` digests.
    """

    id: str
    source_id: str
    file_digests: Mapping[str, str]
    created_at: int | None = None
    supersedes: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.file_digests, MappingProxyType):
            object.__setattr__(
                self,
                "file_digests",
                MappingProxyType(dict(self.file_digests)),
            )

    @property
    def snapshot_ref(self) -> str:
        return self.id

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "source_id": self.source_id,
            "file_digests": dict(self.file_digests),
        }
        if self.created_at is not None:
            payload["created_at"] = self.created_at
        if self.supersedes is not None:
            payload["supersedes"] = self.supersedes
        return MappingProxyType(payload)


def build_corpus_snapshot(
    *,
    source_id: object,
    file_bytes: object,
    created_at: int | None = None,
    supersedes: str | None = None,
) -> Result[CorpusSnapshot]:
    """Build a CorpusSnapshot whose id is the tree digest of per-file digests."""
    if not isinstance(source_id, str) or source_id.strip() == "":
        return _invalid(
            "source_id",
            "source_id is a non-empty string (CT-44; AD-1)",
            given=repr(source_id),
        )
    if not isinstance(file_bytes, Mapping):
        return _invalid(
            "file_bytes",
            "file_bytes maps relative path to bytes (CT-44)",
            given=repr(type(file_bytes).__name__),
        )
    digests: dict[str, str] = {}
    for raw_path, raw_payload in cast("Mapping[object, object]", file_bytes).items():
        if not isinstance(raw_path, str) or raw_path.strip() == "":
            return _invalid(
                "path",
                "snapshot file paths are non-empty relative strings (CT-44)",
                given=repr(raw_path),
            )
        if not isinstance(raw_payload, bytes):
            return _invalid(
                "content",
                "snapshot file content is bytes (CT-44)",
                path=raw_path,
                given=repr(type(raw_payload).__name__),
            )
        digests[raw_path.strip().replace("\\", "/")] = fingerprint_bytes(raw_payload).value
    tree = tree_digest(digests)
    if is_refusal(tree):
        return tree
    return Ok(
        CorpusSnapshot(
            id=tree.value.value,
            source_id=source_id.strip(),
            file_digests=digests,
            created_at=created_at,
            supersedes=supersedes,
        )
    )


def literal_search(
    file_bytes: Mapping[str, bytes],
    query: object,
    *,
    encoding: str = "utf-8",
) -> Result[tuple[str, ...]]:
    """Grep-class literal search over file bytes — no ranking, no embedding."""
    if not isinstance(query, str) or query == "":
        return _invalid(
            "query",
            "search query is a non-empty literal string (CT-44; FR-Q65)",
            given=repr(query),
        )
    needle = query.encode(encoding)
    hits: list[str] = []
    for path in sorted(file_bytes):
        payload = file_bytes[path]
        if needle in payload:
            hits.append(path)
            continue
        try:
            text = payload.decode(encoding)
        except UnicodeDecodeError:
            continue
        if query in text:
            hits.append(path)
    return Ok(tuple(hits))


@dataclass(frozen=True, slots=True)
class Provenance:
    """Citation provenance — retained verbatim, never scalarized (CT-44)."""

    source_ref: str
    snapshot_ref: str
    locator: str
    evidence_label: str
    evidence_confidence: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_confidence, MappingProxyType):
            object.__setattr__(
                self,
                "evidence_confidence",
                MappingProxyType(dict(self.evidence_confidence)),
            )

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_ref": self.source_ref,
                "snapshot_ref": self.snapshot_ref,
                "locator": self.locator,
                "evidence_label": self.evidence_label,
                "evidence_confidence": dict(self.evidence_confidence),
            }
        )


@dataclass(frozen=True, slots=True)
class Citation:
    """Retained citation resolving against a copied artifact (CT-44; AD-19)."""

    source_ref: str
    snapshot_ref: str
    locator: str
    evidence_label: str
    evidence_confidence: Mapping[str, object]
    artifact_ref: str
    id: str = field(default_factory=lambda: str(uuid4()))
    authored_by: str | None = None
    content_fp1: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.evidence_confidence, MappingProxyType):
            object.__setattr__(
                self,
                "evidence_confidence",
                MappingProxyType(dict(self.evidence_confidence)),
            )

    @property
    def provenance(self) -> Provenance:
        return Provenance(
            source_ref=self.source_ref,
            snapshot_ref=self.snapshot_ref,
            locator=self.locator,
            evidence_label=self.evidence_label,
            evidence_confidence=self.evidence_confidence,
        )

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "id": self.id,
            "source_ref": self.source_ref,
            "snapshot_ref": self.snapshot_ref,
            "locator": self.locator,
            "evidence_label": self.evidence_label,
            "evidence_confidence": dict(self.evidence_confidence),
            "artifact_ref": self.artifact_ref,
        }
        if self.authored_by is not None:
            payload["authored_by"] = self.authored_by
        if self.content_fp1 is not None:
            payload["content_fp1"] = self.content_fp1
        return MappingProxyType(payload)


def parse_provenance(
    value: object,
    *,
    declared_keys: Sequence[str],
    source_id: str,
) -> Result[Provenance]:
    """Parse Provenance and enforce evidence_confidence shape."""
    if isinstance(value, Provenance):
        shape = validate_evidence_confidence_shape(
            value.evidence_confidence,
            declared_keys=declared_keys,
            source_id=source_id,
        )
        if is_refusal(shape):
            return shape
        return Ok(value)
    if not isinstance(value, Mapping):
        return _invalid(
            "provenance",
            "provenance is a mapping (CT-44; DEC-0318)",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[str, object]", value)
    missing = sorted(field for field in PROVENANCE_MANDATORY_FIELDS if field not in body)
    if missing:
        return _invalid(
            "provenance",
            "provenance requires source_ref, snapshot_ref, locator, "
            "evidence_label and evidence_confidence (CT-44; DEC-0318)",
            missing=missing,
        )
    source_ref = _parse_nonempty_str(body.get("source_ref"), "source_ref")
    if is_refusal(source_ref):
        return source_ref
    snapshot_ref = _parse_nonempty_str(body.get("snapshot_ref"), "snapshot_ref")
    if is_refusal(snapshot_ref):
        return snapshot_ref
    locator = _parse_nonempty_str(body.get("locator"), "locator")
    if is_refusal(locator):
        return locator
    label = _parse_nonempty_str(body.get("evidence_label"), "evidence_label")
    if is_refusal(label):
        return label
    confidence = parse_evidence_confidence(
        body.get("evidence_confidence"),
        declared_keys=declared_keys,
        source_id=source_id,
    )
    if is_refusal(confidence):
        return confidence
    return Ok(
        Provenance(
            source_ref=source_ref.value,
            snapshot_ref=snapshot_ref.value,
            locator=locator.value,
            evidence_label=label.value,
            evidence_confidence=confidence.value,
        )
    )


def parse_citation(
    value: object,
    *,
    declared_keys: Sequence[str],
    source_id: str,
) -> Result[Citation]:
    """Parse a Citation retaining provenance fields verbatim."""
    if isinstance(value, Citation):
        shape = validate_evidence_confidence_shape(
            value.evidence_confidence,
            declared_keys=declared_keys,
            source_id=source_id,
        )
        if is_refusal(shape):
            return shape
        return Ok(value)
    if not isinstance(value, Mapping):
        return _invalid(
            "citation",
            "a Citation is a mapping (CT-44; DEC-0318)",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[str, object]", value)
    missing = sorted(field for field in CITATION_MANDATORY_FIELDS if field not in body)
    if missing:
        return _invalid(
            "citation",
            "Citation requires source_ref, snapshot_ref, locator, "
            "evidence_label, evidence_confidence and artifact_ref (CT-44)",
            missing=missing,
        )
    provenance = parse_provenance(
        {
            "source_ref": body.get("source_ref"),
            "snapshot_ref": body.get("snapshot_ref"),
            "locator": body.get("locator"),
            "evidence_label": body.get("evidence_label"),
            "evidence_confidence": body.get("evidence_confidence"),
        },
        declared_keys=declared_keys,
        source_id=source_id,
    )
    if is_refusal(provenance):
        return provenance
    artifact = _parse_nonempty_str(body.get("artifact_ref"), "artifact_ref")
    if is_refusal(artifact):
        return artifact
    citation_id = body.get("id")
    if citation_id is None:
        resolved_id = str(uuid4())
    elif isinstance(citation_id, str) and citation_id.strip() != "":
        resolved_id = citation_id.strip()
    else:
        return _invalid(
            "id",
            "id is a non-empty string when present (CT-44)",
            given=repr(citation_id),
        )
    authored_by: str | None = None
    if "authored_by" in body and body.get("authored_by") is not None:
        authored = _parse_nonempty_str(body.get("authored_by"), "authored_by")
        if is_refusal(authored):
            return authored
        authored_by = authored.value
    content_fp1: str | None = None
    if "content_fp1" in body and body.get("content_fp1") is not None:
        fp = _parse_nonempty_str(body.get("content_fp1"), "content_fp1")
        if is_refusal(fp):
            return fp
        parsed_fp = Fingerprint.try_create(fp.value)
        if is_refusal(parsed_fp):
            return parsed_fp
        content_fp1 = parsed_fp.value.value
    return Ok(
        Citation(
            id=resolved_id,
            source_ref=provenance.value.source_ref,
            snapshot_ref=provenance.value.snapshot_ref,
            locator=provenance.value.locator,
            evidence_label=provenance.value.evidence_label,
            evidence_confidence=provenance.value.evidence_confidence,
            artifact_ref=artifact.value,
            authored_by=authored_by,
            content_fp1=content_fp1,
        )
    )


@runtime_checkable
class KnowledgeSource(Protocol):
    """Definitions-only KnowledgeSource seam; one adapter per source_id.

    Cardinality: singleton, scope key ``source_id`` (see ``PORT_CONTRACTS``).
    Query surface: snapshot, search, retrieve. ``cite`` is daemon-owned because
    it copies retained bytes through ``before_artifact_register``.
    """

    @property
    def source_id(self) -> str:
        """AD-1 singleton scope key."""
        ...

    @property
    def kind(self) -> str:
        """Declared source kind; qmx_report is re-entry only, never write-back."""
        ...

    @property
    def confidence_dimensions(self) -> tuple[str, ...]:
        """Exactly six evidence_confidence keys fixed for this source_id."""
        ...

    def snapshot(self) -> Result[CorpusSnapshot]:
        """Return a content-addressed CorpusSnapshot with per-file digests."""
        ...

    def search(self, snapshot: CorpusSnapshot, query: str) -> Result[tuple[str, ...]]:
        """Literal / locator-based search — grep-class, no ranking, no embedding."""
        ...

    def retrieve(self, snapshot: CorpusSnapshot, locator: str) -> Result[bytes]:
        """Return bytes at ``locator`` within the pinned snapshot view."""
        ...
