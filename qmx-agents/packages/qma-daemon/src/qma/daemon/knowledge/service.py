"""KnowledgeSource registry, retained citations and copy gate (CT-44; FR-Q65).

Exactly one read-only adapter binds a ``source_id``. ``cite`` copies cited bytes
into the artifact store through ``before_artifact_register``. Retrieval against
an uncopied snapshot returns ``StaleSnapshot``. ``evidence_confidence`` stays
distinct from Memory's ``admission_confidence``. GAP-0073 stays Deferred.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal, cast
from uuid import uuid4

from qma.core.plugins.hooks import HookResult, HookSource, build_hook_result
from qma.core.ports.knowledge import (
    GAP_0073_KNOWLEDGE_HYBRID_INDEXING,
    KNOWLEDGE_QUERY_SURFACE,
    KNOWLEDGE_SOURCE_OPERATIONS,
    Citation,
    CorpusSnapshot,
    KnowledgeSource,
    Provenance,
    parse_evidence_confidence,
    parse_provenance,
    refuse_evidence_confidence_scalarization,
    refuse_hybrid_knowledge_indexing,
    refuse_knowledge_write_back,
)
from qma.core.refusals import StaleSnapshot
from qma.core.vocabulary.enums import HookResultDecision, HookVerb
from qma.daemon.hooks.registry import HookRegistry, event_names_for_verb
from qmf.core import Ok, Result, is_refusal
from qmf.core.fingerprint import fingerprint_bytes
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "GAP_0073_KNOWLEDGE_HYBRID_INDEXING",
    "KNOWLEDGE_QUERY_SURFACE",
    "KNOWLEDGE_SOURCE_OPERATIONS",
    "ArtifactCopy",
    "CiteOutcome",
    "KnowledgeService",
    "KnowledgeSourceRegistry",
    "MissionSnapshotPin",
    "SourceBinding",
]


_BLOCKING_BEFORE: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.BLOCK_STOP,
    }
)


@dataclass(frozen=True, slots=True)
class SourceBinding:
    """One source_id → KnowledgeSource binding (singleton cardinality)."""

    source_id: str
    source: KnowledgeSource
    plugin_id: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source_id": self.source_id,
                "plugin_id": self.plugin_id,
                "kind": self.source.kind,
                "confidence_dimensions": list(self.source.confidence_dimensions),
                "operations": sorted(KNOWLEDGE_SOURCE_OPERATIONS),
                "query_surface": sorted(KNOWLEDGE_QUERY_SURFACE),
                "read_only": True,
                "impose_schema": False,
                "hybrid_indexing": False,
                "gap_0073": GAP_0073_KNOWLEDGE_HYBRID_INDEXING,
                "evidence_confidence_distinct_from_admission_confidence": True,
            }
        )


@dataclass(frozen=True, slots=True)
class ArtifactCopy:
    """Retained cited bytes registered through before_artifact_register."""

    artifact_ref: str
    snapshot_ref: str
    locator: str
    content_fp1: str
    authored_by: str
    content: bytes

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "artifact_ref": self.artifact_ref,
                "snapshot_ref": self.snapshot_ref,
                "locator": self.locator,
                "content_fp1": self.content_fp1,
                "authored_by": self.authored_by,
                "byte_length": len(self.content),
            }
        )


@dataclass(frozen=True, slots=True)
class CiteOutcome:
    """Result of a cite that retained bytes in the artifact store."""

    citation: Citation
    artifact: ArtifactCopy
    hook: HookResult | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "citation": dict(self.citation.to_payload()),
            "artifact": dict(self.artifact.to_payload()),
        }
        if self.hook is not None:
            payload["hook_decision"] = self.hook.decision.value
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class MissionSnapshotPin:
    """Mission-pinned snapshot_ref with recorded re-pin lineage."""

    mission_id: str
    source_id: str
    snapshot_ref: str
    previous_snapshot_ref: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "mission_id": self.mission_id,
            "source_id": self.source_id,
            "snapshot_ref": self.snapshot_ref,
            "re_pin": self.previous_snapshot_ref is not None,
        }
        if self.previous_snapshot_ref is not None:
            payload["previous_snapshot_ref"] = self.previous_snapshot_ref
        return MappingProxyType(payload)


class KnowledgeSourceRegistry:
    """In-memory singleton-per-source_id registry for KnowledgeSource.

    A second binding for the same source_id is a hard error naming both plugin
    ids. An unbound source_id is simply unavailable, not an error (AD-1).
    """

    def __init__(self) -> None:
        self._by_source: dict[str, SourceBinding] = {}

    def bind(
        self,
        source_id: str,
        source: KnowledgeSource,
        *,
        plugin_id: str | None = None,
    ) -> Result[SourceBinding]:
        if source_id.strip() == "":
            return invalid_input(
                "source_id",
                "KnowledgeSource is scoped per source_id; source_id is a "
                "non-empty string (CT-44; AD-1)",
                given=repr(source_id),
            )
        key = source_id.strip()
        if source.source_id.strip() != key:
            return invalid_input(
                "source_id",
                "adapter source_id must equal the registry binding key (CT-44; AD-1)",
                binding_source_id=key,
                adapter_source_id=source.source_id,
            )
        if key in self._by_source:
            existing = self._by_source[key]
            return policy_rejection(
                "KnowledgeSource",
                "exactly one KnowledgeSource adapter may bind a source_id; a "
                "second binding is a hard error naming both plugin ids "
                "(CT-44; AD-1; FR-Q65)",
                source_id=key,
                existing_plugin_id=existing.plugin_id,
                incoming_plugin_id=plugin_id,
            )
        dims = source.confidence_dimensions
        if len(dims) != 6:
            return invalid_input(
                "confidence_dimensions",
                "adapter must declare exactly six confidence_dimensions "
                "(CT-44; DEC-0318)",
                source_id=key,
                given_count=len(dims),
            )
        binding = SourceBinding(source_id=key, source=source, plugin_id=plugin_id)
        self._by_source[key] = binding
        return Ok(binding)

    def unbind(self, source_id: str) -> None:
        self._by_source.pop(source_id.strip(), None)

    def get(self, source_id: str) -> SourceBinding | None:
        return self._by_source.get(source_id.strip())

    def is_bound(self, source_id: str) -> bool:
        return self.get(source_id) is not None

    def source_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_source))


@dataclass
class KnowledgeService:
    """Daemon knowledge surface: snapshot, search, cite, retained retrieve.

    ``cite`` always copies through ``before_artifact_register``. ``retrieve``
    against a snapshot with no retained copy returns ``StaleSnapshot`` rather
    than live library bytes.
    """

    registry: KnowledgeSourceRegistry = field(default_factory=KnowledgeSourceRegistry)
    hooks: HookRegistry | None = None
    _artifacts: dict[str, ArtifactCopy] = field(default_factory=dict[str, ArtifactCopy])
    _copied_snapshots: set[str] = field(default_factory=set[str])
    _snapshot_chain: dict[str, list[str]] = field(
        default_factory=dict[str, list[str]]
    )
    _mission_pins: dict[tuple[str, str], MissionSnapshotPin] = field(
        default_factory=dict[tuple[str, str], MissionSnapshotPin]
    )

    def bind(
        self,
        source_id: str,
        source: KnowledgeSource,
        *,
        plugin_id: str | None = None,
    ) -> Result[SourceBinding]:
        return self.registry.bind(source_id, source, plugin_id=plugin_id)

    def snapshot(self, source_id: object) -> Result[CorpusSnapshot]:
        binding = self._require_binding(source_id)
        if is_refusal(binding):
            return binding
        snapped = binding.value.source.snapshot()
        if is_refusal(snapped):
            return snapped
        return Ok(self._record_snapshot(binding.value.source_id, snapped.value))

    def search(
        self,
        source_id: object,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
        query: object,
        *,
        mode: Literal["literal", "hybrid", "semantic", "ranked"] = "literal",
    ) -> Result[tuple[str, ...]]:
        if mode != "literal":
            return refuse_hybrid_knowledge_indexing(mode=mode)
        binding = self._require_binding(source_id)
        if is_refusal(binding):
            return binding
        if not isinstance(query, str):
            return invalid_input(
                "query",
                "search query is a non-empty literal string (CT-44; FR-Q65)",
                given=repr(query),
            )
        resolved = self._resolve_snapshot(binding.value, snapshot)
        if is_refusal(resolved):
            return resolved
        return binding.value.source.search(resolved.value, query)

    def cite(
        self,
        source_id: object,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
        locator: object,
        *,
        evidence_label: object,
        evidence_confidence: object,
        authored_by: object,
    ) -> Result[CiteOutcome]:
        """Copy cited bytes through before_artifact_register and return Citation."""
        binding = self._require_binding(source_id)
        if is_refusal(binding):
            return binding
        if not isinstance(locator, str) or locator.strip() == "":
            return invalid_input(
                "locator",
                "cite requires a non-empty locator (CT-44; FR-Q65)",
                given=repr(locator),
            )
        if not isinstance(authored_by, str) or authored_by.strip() == "":
            return invalid_input(
                "authored_by",
                "cite sets authored_by to the citing Agent (CT-44; AD-10; FR-Q65)",
                given=repr(authored_by),
            )
        if not isinstance(evidence_label, str) or evidence_label.strip() == "":
            return invalid_input(
                "evidence_label",
                "evidence_label is an opaque corpus-authored string retained "
                "verbatim (CT-44; DEC-0318)",
                given=repr(evidence_label),
            )
        dims = binding.value.source.confidence_dimensions
        confidence = parse_evidence_confidence(
            evidence_confidence,
            declared_keys=dims,
            source_id=binding.value.source_id,
        )
        if is_refusal(confidence):
            return confidence

        resolved = self._resolve_snapshot(binding.value, snapshot)
        if is_refusal(resolved):
            return resolved
        snap = resolved.value
        content = binding.value.source.retrieve(snap, locator.strip())
        if is_refusal(content):
            return content

        content_fp = fingerprint_bytes(content.value).value
        artifact_ref = f"artifact://knowledge/{snap.id}/{content_fp}"
        copy = ArtifactCopy(
            artifact_ref=artifact_ref,
            snapshot_ref=snap.id,
            locator=locator.strip().replace("\\", "/"),
            content_fp1=content_fp,
            authored_by=authored_by.strip(),
            content=content.value,
        )
        hook = self._before_artifact_register(copy)
        if is_refusal(hook):
            return hook
        gate = hook.value
        if gate.decision in _BLOCKING_BEFORE:
            before, _after = event_names_for_verb(HookVerb.ARTIFACT_REGISTER)
            return policy_rejection(
                before,
                f"{before} resolved to {gate.decision.value}; citation bytes "
                "not retained (CT-44; AD-10; FR-Q65)",
                given=gate.reason or gate.decision.value,
            )

        self._artifacts[artifact_ref] = copy
        self._copied_snapshots.add(snap.id)
        self._after_artifact_register(copy)

        citation = Citation(
            id=str(uuid4()),
            source_ref=binding.value.source_id,
            snapshot_ref=snap.id,
            locator=copy.locator,
            evidence_label=evidence_label.strip(),
            evidence_confidence=confidence.value,
            artifact_ref=artifact_ref,
            authored_by=copy.authored_by,
            content_fp1=content_fp,
        )
        return Ok(CiteOutcome(citation=citation, artifact=copy, hook=gate))

    def retrieve(
        self,
        source_id: object,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
        locator: object,
    ) -> Result[bytes]:
        """Resolve against retained copies only — never silent live substitution."""
        binding = self._require_binding(source_id)
        if is_refusal(binding):
            return binding
        if not isinstance(locator, str) or locator.strip() == "":
            return invalid_input(
                "locator",
                "retrieve requires a non-empty locator (CT-44; FR-Q65)",
                given=repr(locator),
            )
        resolved = self._resolve_snapshot(binding.value, snapshot)
        if is_refusal(resolved):
            return resolved
        snap = resolved.value
        if snap.id not in self._copied_snapshots:
            return StaleSnapshot.of(snapshot_ref=snap.id)
        loc = locator.strip().replace("\\", "/")
        for artifact in self._artifacts.values():
            if artifact.snapshot_ref == snap.id and artifact.locator.split("#", 1)[
                0
            ] == loc.split("#", 1)[0]:
                return Ok(artifact.content)
        return StaleSnapshot.of(snapshot_ref=snap.id)

    def resolve_citation(self, citation: Citation) -> Result[bytes]:
        """Resolve a Citation against its retained artifact copy."""
        copy = self._artifacts.get(citation.artifact_ref)
        if copy is None:
            return StaleSnapshot.of(snapshot_ref=citation.snapshot_ref)
        return Ok(copy.content)

    def pin_mission_snapshot(
        self,
        mission_id: object,
        source_id: object,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
    ) -> Result[MissionSnapshotPin]:
        """Pin one snapshot_ref for a Mission; re-pinning is a recorded act."""
        if not isinstance(mission_id, str) or mission_id.strip() == "":
            return invalid_input(
                "mission_id",
                "Mission pin requires a non-empty mission_id (CT-44; FR-Q65)",
                given=repr(mission_id),
            )
        binding = self._require_binding(source_id)
        if is_refusal(binding):
            return binding
        resolved = self._resolve_snapshot(binding.value, snapshot)
        if is_refusal(resolved):
            return resolved
        key = (mission_id.strip(), binding.value.source_id)
        previous = self._mission_pins.get(key)
        pin = MissionSnapshotPin(
            mission_id=mission_id.strip(),
            source_id=binding.value.source_id,
            snapshot_ref=resolved.value.id,
            previous_snapshot_ref=None if previous is None else previous.snapshot_ref,
        )
        self._mission_pins[key] = pin
        return Ok(pin)

    def supersedes_chain(self, source_id: object) -> Result[tuple[str, ...]]:
        """Linear supersedes chain of snapshots for one source."""
        binding = self._require_binding(source_id)
        if is_refusal(binding):
            return binding
        chain = self._snapshot_chain.get(binding.value.source_id, [])
        return Ok(tuple(chain))

    def validate_provenance(
        self,
        source_id: object,
        provenance: Provenance | Mapping[str, object],
    ) -> Result[Provenance]:
        binding = self._require_binding(source_id)
        if is_refusal(binding):
            return binding
        dims = binding.value.source.confidence_dimensions
        return parse_provenance(
            provenance,
            declared_keys=dims,
            source_id=binding.value.source_id,
        )

    def refuse_hybrid_indexing(self, **extra: object) -> Result[None]:
        return refuse_hybrid_knowledge_indexing(**extra)

    def refuse_scalarize_evidence_confidence(self, **extra: object) -> Result[None]:
        return refuse_evidence_confidence_scalarization(**extra)

    def refuse_write_back(self, **extra: object) -> Result[None]:
        return refuse_knowledge_write_back(**extra)

    def retained_artifact(self, artifact_ref: str) -> ArtifactCopy | None:
        return self._artifacts.get(artifact_ref)

    def _require_binding(self, source_id: object) -> Result[SourceBinding]:
        if not isinstance(source_id, str) or source_id.strip() == "":
            return invalid_input(
                "source_id",
                "KnowledgeSource operations name a source_id (CT-44; AD-1)",
                given=repr(source_id),
            )
        binding = self.registry.get(source_id)
        if binding is None:
            return policy_rejection(
                "source_id",
                "no KnowledgeSource adapter is bound for source_id; unbound "
                "sources are unavailable (CT-44; AD-1; FR-Q65)",
                source_id=source_id.strip(),
            )
        return Ok(binding)

    def _resolve_snapshot(
        self,
        binding: SourceBinding,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
    ) -> Result[CorpusSnapshot]:
        if isinstance(snapshot, CorpusSnapshot):
            if snapshot.source_id != binding.source_id:
                return invalid_input(
                    "snapshot",
                    "CorpusSnapshot source_id must match the bound source "
                    "(CT-44; FR-Q65)",
                    snapshot_source_id=snapshot.source_id,
                    source_id=binding.source_id,
                )
            return Ok(snapshot)
        if isinstance(snapshot, str):
            if snapshot.strip() == "":
                return invalid_input(
                    "snapshot_ref",
                    "snapshot_ref is a non-empty content-addressed id (CT-44)",
                    given=repr(snapshot),
                )
            # Re-snapshot and accept only when the live tree still matches.
            live = binding.source.snapshot()
            if is_refusal(live):
                return live
            recorded = self._record_snapshot(binding.source_id, live.value)
            if recorded.id != snapshot.strip():
                # Allow resolving a previously recorded snapshot id only when
                # the chain knows it — still require retained copies for retrieve.
                chain = self._snapshot_chain.get(binding.source_id, [])
                if snapshot.strip() not in chain:
                    return invalid_input(
                        "snapshot_ref",
                        "unknown snapshot_ref for source_id (CT-44; FR-Q65)",
                        snapshot_ref=snapshot.strip(),
                        source_id=binding.source_id,
                    )
                return Ok(
                    CorpusSnapshot(
                        id=snapshot.strip(),
                        source_id=binding.source_id,
                        file_digests=dict(recorded.file_digests),
                    )
                )
            return Ok(recorded)
        snap_id = snapshot.get("id")
        digests_raw = snapshot.get("file_digests")
        if not isinstance(snap_id, str) or snap_id.strip() == "":
            return invalid_input(
                "snapshot",
                "snapshot mapping requires id (CT-44)",
                given=repr(snapshot),
            )
        if not isinstance(digests_raw, Mapping):
            return invalid_input(
                "file_digests",
                "snapshot mapping requires file_digests (CT-44)",
            )
        file_digests: dict[str, str] = {}
        for raw_key, raw_value in cast("Mapping[object, object]", digests_raw).items():
            if not isinstance(raw_key, str) or not isinstance(raw_value, str):
                return invalid_input(
                    "file_digests",
                    "file_digests maps path string to fp1 string (CT-44)",
                    given=repr((raw_key, raw_value)),
                )
            file_digests[raw_key] = raw_value
        created_raw = snapshot.get("created_at")
        created_at = created_raw if isinstance(created_raw, int) else None
        supersedes_raw = snapshot.get("supersedes")
        supersedes = (
            supersedes_raw.strip()
            if isinstance(supersedes_raw, str) and supersedes_raw.strip() != ""
            else None
        )
        return Ok(
            CorpusSnapshot(
                id=snap_id.strip(),
                source_id=binding.source_id,
                file_digests=file_digests,
                created_at=created_at,
                supersedes=supersedes,
            )
        )

    def _record_snapshot(self, source_id: str, snapshot: CorpusSnapshot) -> CorpusSnapshot:
        chain = self._snapshot_chain.setdefault(source_id, [])
        if snapshot.id in chain:
            return snapshot
        supersedes = chain[-1] if chain else None
        recorded = CorpusSnapshot(
            id=snapshot.id,
            source_id=snapshot.source_id,
            file_digests=snapshot.file_digests,
            created_at=snapshot.created_at,
            supersedes=supersedes,
        )
        chain.append(recorded.id)
        return recorded

    def _before_artifact_register(self, copy: ArtifactCopy) -> Result[HookResult]:
        if self.hooks is None:
            return Ok(build_hook_result(HookResultDecision.ALLOW, reason="no_hook_registry"))
        before, _after = event_names_for_verb(HookVerb.ARTIFACT_REGISTER)
        payload = dict(copy.to_payload())
        payload["kind"] = "knowledge_citation_copy"
        result = self.hooks.dispatch(
            before,
            payload=payload,
            source=HookSource.MISSION,
        )
        if is_refusal(result):
            return result
        return Ok(result.value)

    def _after_artifact_register(self, copy: ArtifactCopy) -> None:
        if self.hooks is None:
            return
        _before, after = event_names_for_verb(HookVerb.ARTIFACT_REGISTER)
        payload = dict(copy.to_payload())
        payload["kind"] = "knowledge_citation_copy"
        self.hooks.dispatch(
            after,
            payload=payload,
            source=HookSource.MISSION,
        )
