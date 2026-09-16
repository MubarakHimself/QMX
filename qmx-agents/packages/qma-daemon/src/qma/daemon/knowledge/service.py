"""KnowledgeSource registry, retained citations and copy gate (CT-44; FR-Q65).

Exactly one read-only adapter binds a ``source_id``. A Mission or browse session
pins exactly one ``snapshot_ref`` before retrieve/cite. ``cite`` copies pinned
bytes into the artifact store through ``before_artifact_register``. Retrieval
against an uncopied snapshot returns ``StaleSnapshot``. Unpinned live-tree reads
are a typed refusal. ``evidence_confidence`` stays distinct from Memory's
``admission_confidence``. GAP-0073 stays Deferred.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final
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
    literal_search,
    parse_evidence_confidence,
    parse_provenance,
    refuse_evidence_confidence_scalarization,
    refuse_hybrid_knowledge_indexing,
    refuse_knowledge_write_back,
    refuse_unpinned_live_tree,
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
    "UNSCORED_CONFIDENCE_VALUE",
    "ArtifactCopy",
    "CiteOutcome",
    "KnowledgeService",
    "KnowledgeSourceRegistry",
    "MissionSnapshotPin",
    "SessionSnapshotPin",
    "SourceBinding",
    "unscored_evidence_confidence",
]


_BLOCKING_BEFORE: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.BLOCK_STOP,
    }
)

# First-slice default when a locator carries no corpus-authored scores (FR-RES-21).
UNSCORED_CONFIDENCE_VALUE: Final[str] = "unscored"

# ATX kebab heading (`## slug` or `## slug — Title`). Not a corpus schema.
_HEADING_ID: Final[re.Pattern[str]] = re.compile(
    r"^##\s+([a-z0-9]+(?:-[a-z0-9]+)*)(?:\s+[\u2014\u2013-].*)?\s*$"
)


def unscored_evidence_confidence(declared_keys: Sequence[str]) -> dict[str, str]:
    """Six declared keys, each ``unscored`` — never a QMA-computed scalar."""
    return dict.fromkeys(declared_keys, UNSCORED_CONFIDENCE_VALUE)


def _heading_ids(payload: bytes) -> frozenset[str]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError:
        return frozenset()
    found: set[str] = set()
    for line in text.splitlines():
        match = _HEADING_ID.match(line)
        if match is not None:
            found.add(match.group(1))
    return frozenset(found)


def _normalize_locator(locator: str) -> str:
    return locator.strip().replace("\\", "/")


def _search_locators(
    files: Mapping[str, bytes],
    query: str,
) -> Result[tuple[str, ...]]:
    """Literal grep plus heading locators ``file_path#id`` (FR-RES-03, FR-RES-05)."""
    text = _normalize_locator(query)
    if "#" in text:
        path, _, fragment = text.partition("#")
        if path not in files:
            return Ok(())
        if fragment == "":
            return Ok((path,))
        payload = files[path]
        if fragment.encode("utf-8") in payload or fragment in _heading_ids(payload):
            return Ok((f"{path}#{fragment}",))
        return Ok(())
    grepped = literal_search(files, query)
    if is_refusal(grepped):
        return grepped
    locators: list[str] = list(grepped.value)
    seen = set(locators)
    for path in sorted(files):
        if query in _heading_ids(files[path]):
            loc = f"{path}#{query}"
            if loc not in seen:
                locators.append(loc)
                seen.add(loc)
    return Ok(tuple(locators))


def _resolve_file_locator(
    files: Mapping[str, bytes],
    locator: str,
    *,
    snapshot_ref: str,
) -> Result[tuple[str, str]]:
    """Resolve ``path``, ``path#id``, or unique slug to ``(file_path, stored_locator)``.

    Colliding heading slugs require ``(file_path, id)`` (FR-RES-05; DEC-0385).
    Fragments are stripped for byte lookup; the stored locator keeps them.
    """
    loc = _normalize_locator(locator)
    path, sep, fragment = loc.partition("#")
    if path in files:
        stored = loc if sep and fragment else path
        return Ok((path, stored))
    if sep:
        return invalid_input(
            "locator",
            "locator is not present in the pinned CorpusSnapshot (CT-44)",
            locator=path,
            snapshot_ref=snapshot_ref,
        )
    matches = [candidate for candidate in sorted(files) if path in _heading_ids(files[candidate])]
    if len(matches) == 1:
        return Ok((matches[0], f"{matches[0]}#{path}"))
    if len(matches) > 1:
        return invalid_input(
            "locator",
            "colliding slugs require (file_path, id) (FR-RES-05; DEC-0385)",
            slug=path,
            id=path,
            file_path=tuple(matches),
            snapshot_ref=snapshot_ref,
        )
    return invalid_input(
        "locator",
        "locator is not present in the pinned CorpusSnapshot (CT-44)",
        locator=loc,
        snapshot_ref=snapshot_ref,
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


@dataclass(frozen=True, slots=True)
class SessionSnapshotPin:
    """Browse-session pinned snapshot_ref with recorded re-pin lineage."""

    session_id: str
    source_id: str
    snapshot_ref: str
    previous_snapshot_ref: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "session_id": self.session_id,
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
                "adapter must declare exactly six confidence_dimensions (CT-44; DEC-0318)",
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
    than live library bytes. Retrieve/cite require a pinned ``snapshot_ref``;
    unpinned live-tree reads are refused. When the caller omits
    ``evidence_confidence`` and the locator has no corpus-authored scores,
    Provenance emits the six declared keys as ``unscored``.
    """

    registry: KnowledgeSourceRegistry = field(default_factory=KnowledgeSourceRegistry)
    hooks: HookRegistry | None = None
    _artifacts: dict[str, ArtifactCopy] = field(default_factory=dict[str, ArtifactCopy])
    _copied_snapshots: set[str] = field(default_factory=set[str])
    _snapshot_chain: dict[str, list[str]] = field(default_factory=dict[str, list[str]])
    _snapshots: dict[str, CorpusSnapshot] = field(default_factory=dict[str, CorpusSnapshot])
    _snapshot_bytes: dict[str, dict[str, bytes]] = field(
        default_factory=dict[str, dict[str, bytes]]
    )
    _mission_pins: dict[tuple[str, str], MissionSnapshotPin] = field(
        default_factory=dict[tuple[str, str], MissionSnapshotPin]
    )
    _session_pins: dict[tuple[str, str], SessionSnapshotPin] = field(
        default_factory=dict[tuple[str, str], SessionSnapshotPin]
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
        return self._retain_now(binding.value, snapped.value)

    def search(
        self,
        source_id: object,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
        query: object,
        *,
        mode: str = "literal",
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
        resolved = self._require_pinned_snapshot(binding.value, snapshot)
        if is_refusal(resolved):
            return resolved
        files = self._snapshot_bytes.get(resolved.value.id)
        if files is None:
            return StaleSnapshot.of(snapshot_ref=resolved.value.id)
        return _search_locators(files, query)

    def cite(
        self,
        source_id: object,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
        locator: object,
        *,
        evidence_label: object,
        authored_by: object,
        evidence_confidence: object | None = None,
    ) -> Result[CiteOutcome]:
        """Copy cited bytes through before_artifact_register and return Citation.

        When ``evidence_confidence`` is omitted and the locator has no
        corpus-authored scores, the six declared keys emit ``unscored``.
        """
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
        supplied = evidence_confidence
        if supplied is None:
            supplied = unscored_evidence_confidence(dims)
        confidence = parse_evidence_confidence(
            supplied,
            declared_keys=dims,
            source_id=binding.value.source_id,
        )
        if is_refusal(confidence):
            return confidence

        resolved = self._require_pinned_snapshot(binding.value, snapshot)
        if is_refusal(resolved):
            return resolved
        snap = resolved.value
        files = self._snapshot_bytes.get(snap.id)
        if files is None:
            return StaleSnapshot.of(snapshot_ref=snap.id)
        addressed = _resolve_file_locator(files, locator, snapshot_ref=snap.id)
        if is_refusal(addressed):
            return addressed
        path, stored_locator = addressed.value
        content_bytes = files[path]

        content_fp = fingerprint_bytes(content_bytes).value
        artifact_ref = f"artifact://knowledge/{snap.id}/{content_fp}"
        copy = ArtifactCopy(
            artifact_ref=artifact_ref,
            snapshot_ref=snap.id,
            locator=stored_locator,
            content_fp1=content_fp,
            authored_by=authored_by.strip(),
            content=content_bytes,
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
        resolved = self._require_pinned_snapshot(binding.value, snapshot)
        if is_refusal(resolved):
            return resolved
        snap = resolved.value
        files = self._snapshot_bytes.get(snap.id)
        if files is None:
            return StaleSnapshot.of(snapshot_ref=snap.id)
        addressed = _resolve_file_locator(files, locator, snapshot_ref=snap.id)
        if is_refusal(addressed):
            return addressed
        path, _stored = addressed.value
        for artifact in self._artifacts.values():
            if artifact.snapshot_ref == snap.id and artifact.locator.split("#", 1)[0] == path:
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
        resolved = self._pin_target(binding.value, snapshot)
        if is_refusal(resolved):
            return resolved
        key = (mission_id.strip(), binding.value.source_id)
        previous = self._mission_pins.get(key)
        if previous is not None and previous.snapshot_ref == resolved.value.id:
            return Ok(previous)
        pin = MissionSnapshotPin(
            mission_id=mission_id.strip(),
            source_id=binding.value.source_id,
            snapshot_ref=resolved.value.id,
            previous_snapshot_ref=None if previous is None else previous.snapshot_ref,
        )
        self._mission_pins[key] = pin
        return Ok(pin)

    def pin_session_snapshot(
        self,
        session_id: object,
        source_id: object,
        snapshot: CorpusSnapshot | Mapping[str, object] | str | None = None,
    ) -> Result[SessionSnapshotPin]:
        """Pin one snapshot_ref for a browse session; re-pinning is recorded.

        When ``snapshot`` is omitted, snapshot the live tree first then pin.
        """
        if not isinstance(session_id, str) or session_id.strip() == "":
            return invalid_input(
                "session_id",
                "session pin requires a non-empty session_id (CT-44; FR-RES-21)",
                given=repr(session_id),
            )
        binding = self._require_binding(source_id)
        if is_refusal(binding):
            return binding
        target: CorpusSnapshot | Mapping[str, object] | str
        if snapshot is None:
            snapped = self.snapshot(binding.value.source_id)
            if is_refusal(snapped):
                return snapped
            target = snapped.value
        else:
            target = snapshot
        resolved = self._pin_target(binding.value, target)
        if is_refusal(resolved):
            return resolved
        key = (session_id.strip(), binding.value.source_id)
        previous = self._session_pins.get(key)
        if previous is not None and previous.snapshot_ref == resolved.value.id:
            return Ok(previous)
        pin = SessionSnapshotPin(
            session_id=session_id.strip(),
            source_id=binding.value.source_id,
            snapshot_ref=resolved.value.id,
            previous_snapshot_ref=None if previous is None else previous.snapshot_ref,
        )
        self._session_pins[key] = pin
        return Ok(pin)

    def mission_pin(self, mission_id: str, source_id: str) -> MissionSnapshotPin | None:
        return self._mission_pins.get((mission_id.strip(), source_id.strip()))

    def session_pin(self, session_id: str, source_id: str) -> SessionSnapshotPin | None:
        return self._session_pins.get((session_id.strip(), source_id.strip()))

    def browse_retrieve(
        self,
        source_id: object,
        locator: object,
        *,
        session_id: object,
    ) -> Result[bytes]:
        """Pin a session snapshot_ref if needed, then retrieve against that pin."""
        pin = self._ensure_session_pin(session_id, source_id)
        if is_refusal(pin):
            return pin
        return self.retrieve(source_id, pin.value.snapshot_ref, locator)

    def browse_cite(
        self,
        source_id: object,
        locator: object,
        *,
        session_id: object,
        evidence_label: object,
        authored_by: object,
        evidence_confidence: object | None = None,
    ) -> Result[CiteOutcome]:
        """Pin a session snapshot_ref if needed, then cite against that pin."""
        pin = self._ensure_session_pin(session_id, source_id)
        if is_refusal(pin):
            return pin
        return self.cite(
            source_id,
            pin.value.snapshot_ref,
            locator,
            evidence_label=evidence_label,
            evidence_confidence=evidence_confidence,
            authored_by=authored_by,
        )

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

    def refuse_unpinned_live_tree(self, **extra: object) -> Result[None]:
        return refuse_unpinned_live_tree(**extra)

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

    def _snapshot_ref_of(
        self,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
    ) -> Result[str]:
        if isinstance(snapshot, CorpusSnapshot):
            return Ok(snapshot.id)
        if isinstance(snapshot, str):
            if snapshot.strip() == "":
                return invalid_input(
                    "snapshot_ref",
                    "snapshot_ref is a non-empty content-addressed id (CT-44)",
                    given=repr(snapshot),
                )
            return Ok(snapshot.strip())
        snap_id = snapshot.get("id")
        if not isinstance(snap_id, str) or snap_id.strip() == "":
            return invalid_input(
                "snapshot",
                "snapshot mapping requires id (CT-44)",
                given=repr(snapshot),
            )
        return Ok(snap_id.strip())

    def _lookup_recorded(
        self,
        binding: SourceBinding,
        snapshot_ref: str,
    ) -> CorpusSnapshot | None:
        stored = self._snapshots.get(snapshot_ref)
        if stored is None or stored.source_id != binding.source_id:
            return None
        return stored

    def _require_pinned_snapshot(
        self,
        binding: SourceBinding,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
    ) -> Result[CorpusSnapshot]:
        """Resolve a snapshot_ref that was already pinned or snapshotted.

        Does not read the live tree. Unrecorded refs are an unpinned refusal.
        Recorded refs whose bytes were not retained are ``StaleSnapshot``.
        """
        if isinstance(snapshot, CorpusSnapshot) and snapshot.source_id != binding.source_id:
            return invalid_input(
                "snapshot",
                "CorpusSnapshot source_id must match the bound source (CT-44; FR-Q65)",
                snapshot_source_id=snapshot.source_id,
                source_id=binding.source_id,
            )
        parsed = self._snapshot_ref_of(snapshot)
        if is_refusal(parsed):
            return parsed
        snapshot_ref = parsed.value
        stored = self._lookup_recorded(binding, snapshot_ref)
        if stored is not None:
            if snapshot_ref not in self._snapshot_bytes:
                return StaleSnapshot.of(snapshot_ref=snapshot_ref)
            return Ok(stored)
        chain = self._snapshot_chain.get(binding.source_id, [])
        if snapshot_ref in chain:
            return StaleSnapshot.of(snapshot_ref=snapshot_ref)
        return refuse_unpinned_live_tree(
            source_id=binding.source_id,
            snapshot_ref=snapshot_ref,
        )

    def _pin_target(
        self,
        binding: SourceBinding,
        snapshot: CorpusSnapshot | Mapping[str, object] | str,
    ) -> Result[CorpusSnapshot]:
        """Record a pin target. Explicit pin may retain matching adapter bytes."""
        recorded = self._require_pinned_snapshot(binding, snapshot)
        if not is_refusal(recorded):
            return recorded
        if not isinstance(snapshot, CorpusSnapshot):
            return recorded
        if StaleSnapshot.matches(recorded):
            return recorded
        return self._retain_now(binding, snapshot)

    def _retain_now(
        self,
        binding: SourceBinding,
        snapshot: CorpusSnapshot,
    ) -> Result[CorpusSnapshot]:
        """Copy snapshot bytes from the adapter now; never substitute later live files."""
        if snapshot.source_id != binding.source_id:
            return invalid_input(
                "snapshot",
                "CorpusSnapshot source_id must match the bound source (CT-44; FR-Q65)",
                snapshot_source_id=snapshot.source_id,
                source_id=binding.source_id,
            )
        existing = self._lookup_recorded(binding, snapshot.id)
        if existing is not None and snapshot.id in self._snapshot_bytes:
            return Ok(existing)
        files: dict[str, bytes] = {}
        for path in snapshot.file_digests:
            got = binding.source.retrieve(snapshot, path)
            if is_refusal(got):
                return StaleSnapshot.of(snapshot_ref=snapshot.id)
            files[path] = got.value
        recorded = self._record_snapshot(binding.source_id, snapshot)
        self._snapshot_bytes[recorded.id] = files
        self._snapshots[recorded.id] = recorded
        return Ok(recorded)

    def _ensure_session_pin(
        self,
        session_id: object,
        source_id: object,
    ) -> Result[SessionSnapshotPin]:
        if not isinstance(session_id, str) or session_id.strip() == "":
            return invalid_input(
                "session_id",
                "session pin requires a non-empty session_id (CT-44; FR-RES-21)",
                given=repr(session_id),
            )
        binding = self._require_binding(source_id)
        if is_refusal(binding):
            return binding
        existing = self._session_pins.get((session_id.strip(), binding.value.source_id))
        if existing is not None:
            return Ok(existing)
        return self.pin_session_snapshot(session_id, source_id)

    def _record_snapshot(self, source_id: str, snapshot: CorpusSnapshot) -> CorpusSnapshot:
        chain = self._snapshot_chain.setdefault(source_id, [])
        stored = self._snapshots.get(snapshot.id)
        if snapshot.id in chain:
            return stored if stored is not None else snapshot
        supersedes = chain[-1] if chain else None
        recorded = CorpusSnapshot(
            id=snapshot.id,
            source_id=snapshot.source_id,
            file_digests=snapshot.file_digests,
            created_at=snapshot.created_at,
            supersedes=supersedes,
        )
        chain.append(recorded.id)
        self._snapshots[recorded.id] = recorded
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
