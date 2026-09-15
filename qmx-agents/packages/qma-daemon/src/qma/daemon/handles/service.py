"""Daemon-resolved evidence handles and candidate writes (CT-47; FR-Q53).

The daemon mints and resolves the six closed ``qma-core`` handle kinds. Contents
never enter a context window. ``StrategyHandle`` may only reference an already-
fingerprinted registry record and register those bytes as a ``dev``-zone
candidate with a QMA origin and a CT-07 predecessor edge — no CT-33/CT-34
assembly, no promotion, no zone transition.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qma.core.barriers.parent_surfaces import refuse_zone_transition_surface
from qma.core.content import content_address
from qma.core.ports.context import ContextCompiler
from qma.core.ports.handles import (
    MONEY_PATH_FIELD_DIFF_SCHEMA,
    STRATEGY_HANDLE_LINEAGE_EDGE_TYPE,
    EvidenceHandle,
    FieldLevelDiff,
    StrategyCandidate,
    parse_evidence_handle,
    parse_registry_record_fp1,
    parse_strategy_record_reference,
    refuse_strategy_handle_assembly,
    touched_money_path_fields,
    unset_money_path_fills,
)
from qma.core.vocabulary.enums import HandleKind, MessageKind
from qma.core.vocabulary.handles import (
    QMA_OWNED_CANDIDATE_ORIGIN,
    STRATEGY_CANDIDATE_ZONE,
    refuse_plugin_handle_kind_extension,
)
from qma.daemon.context.compiler import DefaultContextCompiler
from qma.daemon.tools.parent_writes import DEV_ZONE, ParentSurfaceGate
from qma.wire.money_path_diff import validate_money_path_field_diff
from qmf.core import Ok, Result, WriterId, is_refusal
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection
from qmf.registry import EdgeLog, LineageEdge

__all__ = ["CandidateApprovalRequest", "EvidenceHandleService"]


PROMOTION_COMMAND: Final[None] = None


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class CandidateApprovalRequest:
    """``approval_request`` emission for a StrategyHandle candidate."""

    kind: str
    candidate_ref: str
    money_path_relevant: bool
    payload: Mapping[str, object]
    schema: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", MappingProxyType(dict(self.payload)))
        if self.kind != MessageKind.APPROVAL_REQUEST.value:
            msg = "candidate approval kind must be approval_request (CT-48; FR-Q53)"
            raise ValueError(msg)


class EvidenceHandleService:
    """Daemon mint/resolve/write surface for the closed handle vocabulary."""

    def __init__(
        self,
        *,
        parent: ParentSurfaceGate | None = None,
        compiler: ContextCompiler | None = None,
    ) -> None:
        self._parent = parent if parent is not None else ParentSurfaceGate()
        self._compiler = compiler if compiler is not None else DefaultContextCompiler()
        self._handles: dict[str, EvidenceHandle] = {}
        self._candidates: dict[str, StrategyCandidate] = {}
        self._bodies: dict[str, Mapping[str, object]] = {}
        self._ancestors: dict[str, Mapping[str, object]] = {}
        self._approvals: list[CandidateApprovalRequest] = []
        writer = WriterId.try_create("qma-daemon", "authoring", "strategy-handle", "boot-1")
        if is_refusal(writer):
            msg = "strategy-handle lineage writer id must construct"
            raise RuntimeError(msg)
        self._edges = EdgeLog(writer.value)
        self._lineage: dict[str, LineageEdge] = {}

    @property
    def minted_promotion_command(self) -> None:
        """QMA mints no promotion command (L17; DEC-0345; FR-Q53)."""
        return PROMOTION_COMMAND

    def mint(
        self,
        *,
        kind: object,
        handle_id: object,
        evidence_ref: object,
        recorded: object = True,
        closed: object = True,
        read_only: object = True,
        writable: object = False,
        live: object = False,
        target: object = None,
        contents: object = None,
    ) -> Result[EvidenceHandle]:
        """Mint one closed handle kind. Plugins cannot add kinds."""
        created = parse_evidence_handle(
            kind=kind,
            handle_id=handle_id,
            evidence_ref=evidence_ref,
            recorded=recorded,
            closed=closed,
            read_only=read_only,
            writable=writable,
            live=live,
            target=target,
            contents=contents,
        )
        if is_refusal(created):
            return created
        handle = created.value
        self._handles[handle.handle_id] = handle
        return Ok(handle)

    def resolve(self, handle_id: object) -> Result[EvidenceHandle]:
        """Resolve a handle to its reference. Contents are never returned."""
        if not isinstance(handle_id, str) or handle_id.strip() == "":
            return invalid_input("handle_id", "resolve requires a handle id")
        handle = self._handles.get(handle_id.strip())
        if handle is None:
            return invalid_input(
                "handle_id",
                "unknown evidence handle",
                handle_id=handle_id,
            )
        return Ok(handle)

    def compile_context(
        self, handle_ids: Sequence[str] | None = None
    ) -> Result[Mapping[str, object]]:
        """Build a context window of handle references only."""
        selected: list[EvidenceHandle]
        if handle_ids is None:
            selected = list(self._handles.values())
        else:
            selected = []
            for handle_id in handle_ids:
                resolved = self.resolve(handle_id)
                if is_refusal(resolved):
                    return resolved
                selected.append(resolved.value)
        compiled = self._compiler.compile_context(selected)
        if compiled.get("contents_in_context") is True:
            return _policy(
                "contents_in_context",
                "handle contents never enter a context window (AD-14; FR-Q53)",
            )
        raw_handles = compiled.get("handles", ())
        for entry in cast("Sequence[object]", raw_handles):
            if not isinstance(entry, Mapping):
                continue
            mapping = cast("Mapping[str, object]", entry)
            if mapping.get("contents") is not None:
                return _policy(
                    "contents",
                    "handle contents never enter a context window (AD-14; FR-Q53)",
                )
        return Ok(compiled)

    def register_plugin_handle_kind(self, kind: object) -> TypedRefusal:
        """Plugins never extend the closed handle-kind vocabulary."""
        return refuse_plugin_handle_kind_extension(kind)

    def reference_registry_record(
        self,
        *,
        handle_id: object,
        record_fp1: object,
    ) -> Result[EvidenceHandle]:
        """Point StrategyHandle at an already-fingerprinted registry record."""
        referenced = parse_strategy_record_reference(
            handle_id=handle_id,
            record_fp1=record_fp1,
        )
        if is_refusal(referenced):
            return referenced
        handle = referenced.value
        self._handles[handle.handle_id] = handle
        return Ok(handle)

    def register_fingerprinted_record(
        self,
        *,
        handle_id: object,
        record_fp1: object,
        proposed: Mapping[str, object] | None = None,
        ancestor: Mapping[str, object] | None = None,
        lineage_predecessor: str | None = None,
        origin: str = QMA_OWNED_CANDIDATE_ORIGIN,
        zone: str = STRATEGY_CANDIDATE_ZONE,
        summary: str | None = None,
    ) -> Result[StrategyCandidate]:
        """Register already-fingerprinted bytes as a ``dev``-zone candidate."""
        parsed = parse_registry_record_fp1(record_fp1)
        if is_refusal(parsed):
            return parsed
        blocked = refuse_strategy_handle_assembly(proposed)
        if blocked is not None:
            return blocked
        predecessor = lineage_predecessor if lineage_predecessor is not None else parsed.value
        return self._commit_strategy_candidate(
            handle_id=handle_id,
            origin=origin,
            zone=zone,
            ancestor=ancestor,
            proposed=proposed,
            lineage_predecessor=predecessor,
            summary=summary,
            record_fp1=parsed.value,
        )

    def create_strategy_candidate(
        self,
        *,
        handle_id: object,
        proposed: Mapping[str, object],
        ancestor: Mapping[str, object] | None = None,
        lineage_predecessor: str | None = None,
        origin: str = QMA_OWNED_CANDIDATE_ORIGIN,
        zone: str = STRATEGY_CANDIDATE_ZONE,
        summary: str | None = None,
    ) -> Result[StrategyCandidate]:
        """Write a content-addressed ``dev``-zone candidate from StrategyHandle."""
        blocked = refuse_strategy_handle_assembly(proposed)
        if blocked is not None:
            return blocked
        return self._commit_strategy_candidate(
            handle_id=handle_id,
            origin=origin,
            zone=zone,
            ancestor=ancestor,
            proposed=proposed,
            lineage_predecessor=lineage_predecessor,
            summary=summary,
            record_fp1=None,
        )

    def candidate_lineage_edge(self, candidate_ref: str) -> LineageEdge | None:
        """CT-07 predecessor edge stamped for a StrategyHandle candidate."""
        return self._lineage.get(candidate_ref)

    def _require_strategy_handle(self, handle_id: object) -> Result[EvidenceHandle]:
        resolved = self.resolve(handle_id)
        if is_refusal(resolved):
            return resolved
        handle = resolved.value
        if handle.kind is not HandleKind.STRATEGY_HANDLE:
            return policy_rejection(
                "kind",
                "only StrategyHandle may create a candidate artifact (CT-47; FR-Q53)",
                kind=handle.kind.value,
            )
        return Ok(handle)

    def _stamp_predecessor_edge(self, from_ref: str, to_ref: str) -> Result[LineageEdge]:
        appended = self._edges.append(
            edge_type=STRATEGY_HANDLE_LINEAGE_EDGE_TYPE,
            from_ref=from_ref,
            to_ref=to_ref,
        )
        if is_refusal(appended):
            return appended
        edge = appended.value.edge
        self._lineage[from_ref] = edge
        return Ok(edge)

    def _commit_strategy_candidate(
        self,
        *,
        handle_id: object,
        origin: str,
        zone: str,
        ancestor: Mapping[str, object] | None,
        proposed: Mapping[str, object] | None,
        lineage_predecessor: str | None,
        summary: str | None,
        record_fp1: str | None,
    ) -> Result[StrategyCandidate]:
        handle_result = self._require_strategy_handle(handle_id)
        if is_refusal(handle_result):
            return handle_result
        handle = handle_result.value
        if zone != DEV_ZONE:
            return self._parent.attempt_zone_transition()
        if origin != QMA_OWNED_CANDIDATE_ORIGIN:
            return policy_rejection(
                "origin",
                "StrategyHandle candidates carry a QMA-owned origin (DEC-0313; FR-Q53)",
                given=origin,
            )
        body: Mapping[str, object] = proposed if proposed is not None else MappingProxyType({})
        fills = unset_money_path_fills(ancestor, body)
        if fills:
            return _policy(
                "money_path_field",
                "QMA never mints a value for a money-path field where the "
                "ancestor carries none (DEC-0313; FR-Q53)",
                fields=list(fills),
            )
        touched = touched_money_path_fields(ancestor, body)
        money_path_relevant = bool(touched)
        if money_path_relevant and ancestor is None and lineage_predecessor is None:
            return _policy(
                "lineage_predecessor",
                "a money_path_relevant candidate requires a predecessor artifact "
                "to diff against (CT-47; FR-Q53)",
            )
        predecessor = lineage_predecessor
        if predecessor is None and ancestor is not None:
            ancestor_fp = content_address(dict(ancestor))
            if is_refusal(ancestor_fp):
                return ancestor_fp
            predecessor = ancestor_fp.value.value
        payload: dict[str, object] = {
            "kind": "strategy_candidate",
            "handle_id": handle.handle_id,
            "money_path_relevant": money_path_relevant,
            "touched_fields": list(touched),
        }
        if record_fp1 is not None:
            payload["record_fp1"] = record_fp1
        elif proposed is not None:
            addressed = content_address(dict(proposed))
            if is_refusal(addressed):
                return addressed
            payload["body_fp1"] = addressed.value.value
        else:
            return invalid_input(
                "record_fp1",
                "StrategyHandle registers already-fingerprinted registry bytes",
            )
        written = self._parent.write_dev_zone_candidate(
            payload,
            origin=origin,
            summary=summary,
            lineage_predecessor=predecessor,
            zone=zone,
        )
        if is_refusal(written):
            return written
        stored = written.value
        candidate = StrategyCandidate.try_create(
            origin=stored.origin,
            zone=stored.zone,
            payload_fp1=stored.payload_fp1,
            stable_id=stored.stable_id,
            handle_id=handle.handle_id,
            money_path_relevant=money_path_relevant,
            touched_fields=touched,
            lineage_predecessor=stored.lineage_predecessor,
            record_fp1=record_fp1,
        )
        if is_refusal(candidate):
            return candidate
        record = candidate.value
        self._candidates[record.payload_fp1] = record
        if proposed is not None:
            self._bodies[record.payload_fp1] = MappingProxyType(dict(proposed))
        if ancestor is not None:
            self._ancestors[record.payload_fp1] = MappingProxyType(dict(ancestor))
        if predecessor is not None:
            stamped = self._stamp_predecessor_edge(record.payload_fp1, predecessor)
            if is_refusal(stamped):
                return stamped
        return Ok(record)

    def emit_approval_request(
        self,
        *,
        candidate_ref: object,
        field_diff: Mapping[str, object] | None = None,
    ) -> Result[CandidateApprovalRequest]:
        """Emit approval_request. money_path_relevant requires the named schema."""
        if not isinstance(candidate_ref, str) or candidate_ref.strip() == "":
            return invalid_input("candidate_ref", "approval_request requires candidate_ref")
        candidate = self._candidates.get(candidate_ref.strip())
        if candidate is None:
            return invalid_input(
                "candidate_ref",
                "unknown strategy candidate",
                candidate_ref=candidate_ref,
            )
        if candidate.money_path_relevant:
            if field_diff is None:
                return _policy(
                    "field_diff",
                    "a money_path_relevant candidate refuses approval_request "
                    "unless the payload carries the named qma-wire field-level "
                    "diff of exactly the touched fields (CT-47; FR-Q53)",
                )
            checked = validate_money_path_field_diff(field_diff)
            if is_refusal(checked):
                return checked
            diff: FieldLevelDiff = checked.value
            if diff.candidate_ref != candidate.payload_fp1:
                return _policy(
                    "candidate_ref",
                    "field-level diff candidate_ref must match the candidate",
                )
            if (
                candidate.lineage_predecessor is not None
                and diff.predecessor_ref != candidate.lineage_predecessor
            ):
                return _policy(
                    "predecessor_ref",
                    "field-level diff predecessor_ref must match the lineage edge",
                )
            if diff.paths != frozenset(candidate.touched_fields):
                return _policy(
                    "fields",
                    "field-level diff must name exactly the touched money-path "
                    "fields (CT-47; FR-Q53)",
                    expected=list(candidate.touched_fields),
                    given=sorted(diff.paths),
                )
            ancestor = self._ancestors.get(candidate.payload_fp1)
            if ancestor is not None:
                for entry in diff.fields:
                    if ancestor.get(entry.path) != entry.ancestor:
                        return _policy(
                            "ancestor",
                            "field-level diff ancestor values must match the "
                            "predecessor artifact (DEC-0313; FR-Q53)",
                            path=entry.path,
                        )
            request = CandidateApprovalRequest(
                kind=MessageKind.APPROVAL_REQUEST.value,
                candidate_ref=candidate.payload_fp1,
                money_path_relevant=True,
                schema=MONEY_PATH_FIELD_DIFF_SCHEMA,
                payload=diff.to_payload(),
            )
        else:
            request = CandidateApprovalRequest(
                kind=MessageKind.APPROVAL_REQUEST.value,
                candidate_ref=candidate.payload_fp1,
                money_path_relevant=False,
                schema=None,
                payload={"candidate_ref": candidate.payload_fp1},
            )
        self._approvals.append(request)
        return Ok(request)

    def promote(self, candidate_ref: object) -> TypedRefusal:
        """Promotion is a human live-zone act outside QMA (L17; FR-Q53)."""
        _ = candidate_ref
        return refuse_zone_transition_surface()

    def transition_zone(self, *, zone: object = "live") -> TypedRefusal:
        """StrategyHandle mints no zone-transition command (AD-3; FR-Q53)."""
        _ = zone
        return self._parent.attempt_zone_transition()

    def candidate_body(self, candidate_ref: str) -> Mapping[str, object] | None:
        """Stored proposed body — never compiled into a context window."""
        return self._bodies.get(candidate_ref)
