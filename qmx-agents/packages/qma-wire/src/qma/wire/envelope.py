"""Wire envelope frame and ``scope_path`` law (CT-40; AD-5; DEC-0304; FR-Q11).

Canonical JSON is produced through imported ``qmf-core`` ``fp1`` rules. Absent
optional fields are omitted keys, never null — except the
``correlation_missing`` evidence-append carve-out, which records a
daemon-minted lifecycle id under that annotation rather than dropping evidence.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qma.wire.vocabulary import parse_wire_type
from qmf.core.fingerprint import canonical_bytes
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "CORRELATION_MISSING_ANNOTATION",
    "JOURNAL_SEQ_FIELD",
    "SCOPE_KIND_ORDER",
    "ScopePathError",
    "ScopeSegment",
    "WireEnvelope",
    "WireEnvelopeError",
    "is_scope_prefix",
    "parse_scope_path",
]


SCOPE_KIND_ORDER: Final[tuple[str, ...]] = (
    "desk",
    "quant",
    "mission",
    "task",
    "session",
    "agent",
    "subagent",
)
_SCOPE_INDEX: Final[dict[str, int]] = {kind: idx for idx, kind in enumerate(SCOPE_KIND_ORDER)}

CORRELATION_MISSING_ANNOTATION: Final[str] = "correlation_missing"
JOURNAL_SEQ_FIELD: Final[str] = "journal_seq"


class ScopePathError(ValueError):
    """Raised when a ``scope_path`` violates the fixed ancestor order."""


class WireEnvelopeError(ValueError):
    """Raised when a wire envelope cannot be constructed or serialized."""


@dataclass(frozen=True, slots=True)
class ScopeSegment:
    """One ``{kind, id}`` segment of a ``scope_path``."""

    kind: str
    id: str

    def to_dict(self) -> dict[str, str]:
        return {"kind": self.kind, "id": self.id}


def parse_scope_path(value: object) -> tuple[ScopeSegment, ...]:
    """Validate and normalize a ``scope_path`` under the fixed kind order.

    Segments must appear only in desk → quant → mission → task → session →
    agent → subagent order, every existing ancestor present (no gaps), and each
    ``id`` a non-empty string. An empty path is allowed (daemon-global).
    """
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ScopePathError("scope_path must be an array of {kind, id} segments")
    segments: list[ScopeSegment] = []
    expected_index = 0
    for raw_obj in cast("Sequence[object]", value):
        kind: object
        seg_id: object
        if isinstance(raw_obj, ScopeSegment):
            kind, seg_id = raw_obj.kind, raw_obj.id
        elif isinstance(raw_obj, Mapping):
            raw_map = cast("Mapping[object, object]", raw_obj)
            kind, seg_id = raw_map.get("kind"), raw_map.get("id")
        else:
            raise ScopePathError(
                f"scope_path segment must be {{kind, id}}; got {type(raw_obj).__name__}"
            )
        if not isinstance(kind, str) or kind not in _SCOPE_INDEX:
            raise ScopePathError(f"scope_path kind must be one of {SCOPE_KIND_ORDER}; got {kind!r}")
        if not isinstance(seg_id, str) or seg_id.strip() == "":
            raise ScopePathError("scope_path id must be a non-empty string")
        index = _SCOPE_INDEX[kind]
        if index != expected_index:
            raise ScopePathError(
                f"scope_path ancestors must be contiguous from desk; "
                f"expected {SCOPE_KIND_ORDER[expected_index]!r} at position "
                f"{expected_index}, got {kind!r}"
            )
        segments.append(ScopeSegment(kind=kind, id=seg_id))
        expected_index = index + 1
    return tuple(segments)


def is_scope_prefix(
    candidate: Sequence[ScopeSegment | Mapping[str, str]],
    full: Sequence[ScopeSegment | Mapping[str, str]],
) -> bool:
    """Return True when ``candidate`` is a prefix of ``full`` (prefix filters only)."""
    left = parse_scope_path(candidate)
    right = parse_scope_path(full)
    if len(left) > len(right):
        return False
    return left == right[: len(left)]


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


@dataclass(frozen=True, slots=True)
class WireEnvelope:
    """The AD-5 wire envelope frame (never named bare ``Envelope``)."""

    v: str
    type: str
    id: str
    producer_id: str
    scope_path: tuple[ScopeSegment, ...]
    payload: Mapping[str, object]
    correlation_id: str | None = None
    seq: int | None = None
    correlation_missing: bool = False

    @classmethod
    def try_create(
        cls,
        *,
        v: object,
        type: object,
        id: object,
        producer_id: object,
        scope_path: object,
        payload: object,
        correlation_id: object = None,
        seq: object = None,
        correlation_missing: bool = False,
    ) -> Result[WireEnvelope]:
        """Build a validated envelope, returning value-or-refusal."""
        if not isinstance(v, str) or v.strip() == "":
            return _invalid("v", "v is a non-empty semver protocolVersion string")
        try:
            wire_type = parse_wire_type(type)
        except ValueError as exc:
            return _invalid("type", str(exc), given=repr(type))
        if not isinstance(id, str) or id.strip() == "":
            return _invalid("id", "id is a non-empty producer-minted string")
        if not isinstance(producer_id, str) or producer_id.strip() == "":
            return _invalid("producer_id", "producer_id is a non-empty stable identity")
        try:
            path = parse_scope_path(scope_path)
        except ScopePathError as exc:
            return _invalid("scope_path", str(exc))
        if not isinstance(payload, Mapping):
            return _invalid("payload", "payload must be an object")
        payload_map: dict[str, object] = {}
        for key_obj, value in cast("Mapping[object, object]", payload).items():
            if not isinstance(key_obj, str):
                return _invalid("payload", "payload keys must be strings")
            if value is None:
                return _invalid(
                    "payload",
                    "null is prohibited; omit absent optional keys (fp1)",
                )
            payload_map[key_obj] = value
        if JOURNAL_SEQ_FIELD in payload_map:
            return _invalid(
                JOURNAL_SEQ_FIELD,
                "journal_seq is never exposed on the wire and is never "
                "substituted for seq (DEC-0304)",
            )

        if correlation_id is None:
            return _invalid(
                "correlation_id",
                "correlation_id is required on wire records; the "
                "correlation_missing carve-out still carries a daemon-minted "
                "lifecycle id (DEC-0304)",
            )
        if not isinstance(correlation_id, str) or correlation_id.strip() == "":
            return _invalid(
                "correlation_id",
                "correlation_id must be a non-empty string when present",
            )

        resolved_seq: int | None
        if seq is None:
            resolved_seq = None
        elif isinstance(seq, bool) or not isinstance(seq, int) or seq < 0:
            return _invalid("seq", "seq is a non-negative integer projection index")
        else:
            if not path:
                return _invalid(
                    "seq",
                    "seq is the projection index of the final named scope; "
                    "scope_path must be non-empty when seq is present",
                )
            resolved_seq = seq

        frozen_payload: Mapping[str, object] = MappingProxyType(payload_map)
        return Ok(
            cls(
                v=v,
                type=wire_type,
                id=id,
                producer_id=producer_id,
                scope_path=path,
                payload=frozen_payload,
                correlation_id=correlation_id,
                seq=resolved_seq,
                correlation_missing=bool(correlation_missing),
            )
        )

    def to_dict(self) -> dict[str, object]:
        """Serialize to a JSON-native object; omit absent optional keys (never null)."""
        out: dict[str, object] = {
            "v": self.v,
            "type": self.type,
            "id": self.id,
            "producer_id": self.producer_id,
            "scope_path": [segment.to_dict() for segment in self.scope_path],
            "payload": dict(self.payload),
        }
        if self.correlation_id is not None:
            out["correlation_id"] = self.correlation_id
        if self.seq is not None:
            out["seq"] = self.seq
        if self.correlation_missing:
            out["correlation_missing"] = True
        if JOURNAL_SEQ_FIELD in out:
            raise WireEnvelopeError("journal_seq must never appear on the wire")
        return out

    def canonical_bytes(self) -> Result[bytes]:
        """Canonical JSON bytes under imported ``fp1`` rules."""
        return canonical_bytes(self.to_dict())

    @property
    def final_scope_kind(self) -> str | None:
        """Kind of the last ``scope_path`` segment — the referent of ``seq``."""
        if not self.scope_path:
            return None
        return self.scope_path[-1].kind
