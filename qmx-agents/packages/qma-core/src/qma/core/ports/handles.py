"""Daemon-resolved evidence handles (CT-47; AD-14; DEC-0313; FR-Q53).

Six closed kinds owned by ``qma-core``. A handle is a reference: contents never
enter a context window. ``TradeLogHandle`` and ``MarketDataHandle`` address
recorded, closed, read-only evidence only. ``StrategyHandle`` may create only
content-addressed ``dev``-zone candidates with a QMA-owned origin.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qma.core.vocabulary.enums import HandleKind
from qma.core.vocabulary.handles import (
    CLOSED_HANDLE_KINDS,
    MONEY_PATH_RELEVANT_FIELDS,
    QMA_OWNED_CANDIDATE_ORIGIN,
    READ_ONLY_EVIDENCE_HANDLE_KINDS,
    STRATEGY_CANDIDATE_ZONE,
    is_forbidden_live_money_path_target,
    is_handle_kind_contribution_point,
    normalize_handle_target,
    refuse_plugin_handle_kind_extension,
)
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "MONEY_PATH_FIELD_DIFF_SCHEMA",
    "EvidenceHandle",
    "FieldLevelDiff",
    "FieldLevelDiffEntry",
    "StrategyCandidate",
    "context_entries_for_handles",
    "money_path_field_is_set",
    "parse_evidence_handle",
    "refuse_plugin_handle_kind_extension",
    "touched_money_path_fields",
    "unset_money_path_fills",
]


MONEY_PATH_FIELD_DIFF_SCHEMA: Final[str] = "qma.wire.money_path_field_diff.v1"
_EMPTY_BODY: Final[Mapping[str, object]] = MappingProxyType({})


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


def money_path_field_is_set(body: Mapping[str, object], field: str) -> bool:
    """True when ``field`` is present on ``body`` with a non-null value."""
    return field in body and body[field] is not None


def unset_money_path_fills(
    ancestor: Mapping[str, object] | None,
    proposed: Mapping[str, object],
) -> tuple[str, ...]:
    """Money-path fields the candidate would mint where the ancestor has none."""
    prior: Mapping[str, object] = ancestor if ancestor is not None else _EMPTY_BODY
    filled = [
        field
        for field in sorted(MONEY_PATH_RELEVANT_FIELDS)
        if money_path_field_is_set(proposed, field) and not money_path_field_is_set(prior, field)
    ]
    return tuple(filled)


def touched_money_path_fields(
    ancestor: Mapping[str, object] | None,
    proposed: Mapping[str, object],
) -> tuple[str, ...]:
    """Existing money-path fields whose proposed value differs from the ancestor."""
    prior: Mapping[str, object] = ancestor if ancestor is not None else _EMPTY_BODY
    touched: list[str] = []
    for field in sorted(MONEY_PATH_RELEVANT_FIELDS):
        if not money_path_field_is_set(prior, field):
            continue
        if not money_path_field_is_set(proposed, field):
            continue
        if proposed[field] != prior[field]:
            touched.append(field)
    return tuple(touched)


@dataclass(frozen=True, slots=True)
class EvidenceHandle:
    """Daemon-resolved reference. Contents never live on the handle."""

    kind: HandleKind
    handle_id: str
    evidence_ref: str
    recorded: bool = True
    closed: bool = True
    read_only: bool = True
    writable: bool = False
    live: bool = False
    target: str | None = None
    contents: None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "contents", None)

    @property
    def contents_in_context(self) -> bool:
        return False

    def context_entry(self) -> Mapping[str, object]:
        """Reference-only payload for a context window. Never includes contents."""
        return MappingProxyType(
            {
                "kind": self.kind.value,
                "handle_id": self.handle_id,
                "evidence_ref": self.evidence_ref,
                "contents": None,
                "contents_in_context": False,
            }
        )

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind.value,
            "handle_id": self.handle_id,
            "evidence_ref": self.evidence_ref,
            "recorded": self.recorded,
            "closed": self.closed,
            "read_only": self.read_only,
            "writable": self.writable,
            "live": self.live,
            "contents": None,
            "contents_in_context": False,
        }
        if self.target is not None:
            payload["target"] = self.target
        return MappingProxyType(payload)

    @classmethod
    def try_create(
        cls,
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
        if is_handle_kind_contribution_point(kind):
            return refuse_plugin_handle_kind_extension(kind)
        try:
            resolved_kind = kind if isinstance(kind, HandleKind) else parse_closed(HandleKind, kind)
        except VocabularyError as exc:
            return _invalid("kind", str(exc), given=repr(kind))
        if resolved_kind not in CLOSED_HANDLE_KINDS:
            return refuse_plugin_handle_kind_extension(kind)
        if not isinstance(handle_id, str) or handle_id.strip() == "":
            return _invalid("handle_id", "EvidenceHandle requires a durable handle id")
        if not isinstance(evidence_ref, str) or evidence_ref.strip() == "":
            return _invalid("evidence_ref", "EvidenceHandle requires an evidence reference")
        if contents is not None:
            return _policy(
                "contents",
                "a handle is a daemon-resolved reference whose contents never "
                "enter a context window (AD-14; DEC-0313; FR-Q53)",
            )
        if writable is True or live is True:
            return _policy(
                "live",
                "no handle may address a live or writable money-path record "
                "(AD-14; DEC-0313; FR-Q53)",
                writable=writable,
                live=live,
            )
        token = normalize_handle_target(target)
        if is_forbidden_live_money_path_target(target):
            return _policy(
                "target",
                "no handle for an open order, open position, binding, Book, seat, "
                "BMS record, control action, kill switch, or venue session may be "
                "minted (CT-47; SCN-0014; FR-Q53)",
                target=token,
            )
        rec = bool(recorded)
        clo = bool(closed)
        ro = bool(read_only)
        if resolved_kind in READ_ONLY_EVIDENCE_HANDLE_KINDS and (not rec or not clo or not ro):
            return _policy(
                "evidence_state",
                f"{resolved_kind.value} addresses recorded, closed, read-only "
                "evidence only (CT-47; FR-Q53)",
                recorded=rec,
                closed=clo,
                read_only=ro,
            )
        return Ok(
            cls(
                kind=resolved_kind,
                handle_id=handle_id.strip(),
                evidence_ref=evidence_ref.strip(),
                recorded=rec,
                closed=clo,
                read_only=ro,
                writable=False,
                live=False,
                target=token,
                contents=None,
            )
        )

    @classmethod
    def from_payload(cls, payload: Mapping[str, object]) -> Result[EvidenceHandle]:
        return cls.try_create(
            kind=payload.get("kind"),
            handle_id=payload.get("handle_id"),
            evidence_ref=payload.get("evidence_ref"),
            recorded=payload.get("recorded", True),
            closed=payload.get("closed", True),
            read_only=payload.get("read_only", True),
            writable=payload.get("writable", False),
            live=payload.get("live", False),
            target=payload.get("target"),
            contents=payload.get("contents"),
        )


def parse_evidence_handle(**fields: object) -> Result[EvidenceHandle]:
    """Result-returning EvidenceHandle constructor (CT-47; FR-Q53)."""
    return EvidenceHandle.try_create(
        kind=fields.get("kind"),
        handle_id=fields.get("handle_id"),
        evidence_ref=fields.get("evidence_ref"),
        recorded=fields.get("recorded", True),
        closed=fields.get("closed", True),
        read_only=fields.get("read_only", True),
        writable=fields.get("writable", False),
        live=fields.get("live", False),
        target=fields.get("target"),
        contents=fields.get("contents"),
    )


def context_entries_for_handles(
    handles: Sequence[EvidenceHandle],
) -> tuple[Mapping[str, object], ...]:
    """Compile handle references for a context window. Contents stay out."""
    return tuple(handle.context_entry() for handle in handles)


@dataclass(frozen=True, slots=True)
class FieldLevelDiffEntry:
    """One money-path field compared against its ancestor."""

    path: str
    ancestor: object
    proposed: object

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "path": self.path,
                "ancestor": self.ancestor,
                "proposed": self.proposed,
            }
        )


@dataclass(frozen=True, slots=True)
class FieldLevelDiff:
    """Named ``qma-wire`` field-level diff for a money_path_relevant candidate."""

    schema: str
    candidate_ref: str
    predecessor_ref: str
    fields: tuple[FieldLevelDiffEntry, ...]

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "schema": self.schema,
                "candidate_ref": self.candidate_ref,
                "predecessor_ref": self.predecessor_ref,
                "fields": [entry.to_payload() for entry in self.fields],
            }
        )

    @property
    def paths(self) -> frozenset[str]:
        return frozenset(entry.path for entry in self.fields)

    @classmethod
    def try_create(
        cls,
        *,
        schema: object,
        candidate_ref: object,
        predecessor_ref: object,
        fields: object,
    ) -> Result[FieldLevelDiff]:
        if schema != MONEY_PATH_FIELD_DIFF_SCHEMA:
            return _invalid(
                "schema",
                "money_path_relevant field-level diff must use the named "
                f"{MONEY_PATH_FIELD_DIFF_SCHEMA} qma-wire schema (CT-47; FR-Q53)",
                given=repr(schema),
            )
        if not isinstance(candidate_ref, str) or candidate_ref.strip() == "":
            return _invalid("candidate_ref", "field-level diff requires candidate_ref")
        if not isinstance(predecessor_ref, str) or predecessor_ref.strip() == "":
            return _invalid("predecessor_ref", "field-level diff requires predecessor_ref")
        if not isinstance(fields, Sequence) or isinstance(fields, (str, bytes)):
            return _invalid("fields", "field-level diff fields must be an array")
        parsed: list[FieldLevelDiffEntry] = []
        seen: set[str] = set()
        for item in cast("Sequence[object]", fields):
            if not isinstance(item, Mapping):
                return _invalid("fields", "each field-level diff entry is an object")
            body = cast("Mapping[str, object]", item)
            path = body.get("path")
            if not isinstance(path, str) or path not in MONEY_PATH_RELEVANT_FIELDS:
                return _invalid(
                    "path",
                    "field-level diff paths are exactly the money_path_relevant "
                    "fields risk, sizing, exit, protection, binding, priority",
                    given=repr(path),
                )
            if path in seen:
                return _invalid("path", "field-level diff paths must be unique", path=path)
            if "ancestor" not in body or body["ancestor"] is None:
                return _policy(
                    "ancestor",
                    "QMA never mints a value for a money-path field where the "
                    "ancestor carries none (DEC-0313; FR-Q53)",
                    path=path,
                )
            seen.add(path)
            parsed.append(
                FieldLevelDiffEntry(
                    path=path,
                    ancestor=body["ancestor"],
                    proposed=body.get("proposed"),
                )
            )
        if not parsed:
            return _invalid(
                "fields",
                "a money_path_relevant field-level diff names at least one field",
            )
        return Ok(
            cls(
                schema=MONEY_PATH_FIELD_DIFF_SCHEMA,
                candidate_ref=candidate_ref.strip(),
                predecessor_ref=predecessor_ref.strip(),
                fields=tuple(parsed),
            )
        )


@dataclass(frozen=True, slots=True)
class StrategyCandidate:
    """Content-addressed StrategyHandle candidate in the existing ``dev`` zone."""

    origin: str
    zone: str
    payload_fp1: str
    stable_id: str
    handle_id: str
    money_path_relevant: bool
    touched_fields: tuple[str, ...] = ()
    lineage_predecessor: str | None = None

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "origin": self.origin,
            "zone": self.zone,
            "payload_fp1": self.payload_fp1,
            "stable_id": self.stable_id,
            "handle_id": self.handle_id,
            "money_path_relevant": self.money_path_relevant,
            "touched_fields": list(self.touched_fields),
        }
        if self.lineage_predecessor is not None:
            payload["lineage_predecessor"] = self.lineage_predecessor
        return MappingProxyType(payload)

    @classmethod
    def try_create(
        cls,
        *,
        origin: object,
        zone: object,
        payload_fp1: object,
        stable_id: object,
        handle_id: object,
        money_path_relevant: object,
        touched_fields: object = (),
        lineage_predecessor: object = None,
    ) -> Result[StrategyCandidate]:
        if origin != QMA_OWNED_CANDIDATE_ORIGIN:
            return _policy(
                "origin",
                "StrategyHandle candidates carry a QMA-owned origin (DEC-0313; FR-Q53)",
                given=repr(origin),
            )
        if zone != STRATEGY_CANDIDATE_ZONE:
            return _policy(
                "zone",
                "StrategyHandle writes only the existing parent-registry dev zone "
                "and mints no zone value (AD-3; DEC-0313; FR-Q53)",
                given=repr(zone),
            )
        if not isinstance(payload_fp1, str) or not payload_fp1.startswith("fp1:"):
            return _invalid("payload_fp1", "candidate identity is an fp1 content address")
        if not isinstance(stable_id, str) or stable_id.strip() == "":
            return _invalid("stable_id", "candidate requires a stable id")
        if not isinstance(handle_id, str) or handle_id.strip() == "":
            return _invalid("handle_id", "candidate requires the minting StrategyHandle id")
        if not isinstance(money_path_relevant, bool):
            return _invalid("money_path_relevant", "money_path_relevant is a boolean flag")
        if lineage_predecessor is not None and not isinstance(lineage_predecessor, str):
            return _invalid("lineage_predecessor", "lineage predecessor is an fp1 string")
        if lineage_predecessor == "":
            return _invalid("lineage_predecessor", "lineage predecessor is an fp1 string")
        fields: tuple[str, ...]
        if touched_fields is None:
            fields = ()
        elif isinstance(touched_fields, Sequence) and not isinstance(touched_fields, (str, bytes)):
            parsed_fields: list[str] = []
            for item in cast("Sequence[object]", touched_fields):
                if not isinstance(item, str) or item not in MONEY_PATH_RELEVANT_FIELDS:
                    return _invalid(
                        "touched_fields",
                        "touched fields are the closed money_path_relevant set",
                        given=repr(item),
                    )
                parsed_fields.append(item)
            fields = tuple(parsed_fields)
        else:
            return _invalid("touched_fields", "touched_fields is a sequence of field names")
        if money_path_relevant and not fields:
            return _invalid(
                "touched_fields",
                "a money_path_relevant candidate records the exact touched fields",
            )
        if not money_path_relevant and fields:
            return _invalid(
                "money_path_relevant",
                "touched money-path fields require money_path_relevant at creation",
            )
        return Ok(
            cls(
                origin=QMA_OWNED_CANDIDATE_ORIGIN,
                zone=STRATEGY_CANDIDATE_ZONE,
                payload_fp1=payload_fp1,
                stable_id=stable_id.strip(),
                handle_id=handle_id.strip(),
                money_path_relevant=money_path_relevant,
                touched_fields=fields,
                lineage_predecessor=lineage_predecessor,
            )
        )
