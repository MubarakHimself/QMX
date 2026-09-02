"""MemoryProvider port — per-desk singleton (CT-43; AD-1, AD-18).

Definitions only. QMA builds no memory engine in-house: every memory concern
enters through this port. ``admission_confidence`` is a gate output the daemon
computes deterministically; a ``propose`` call carrying it is refused. External
backends stay Deferred GAP-0072. A candidate is admitted, never promoted.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Protocol, cast, runtime_checkable
from uuid import uuid4

from qma.core.vocabulary.enums import MemoryValidationState
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "GAP_0072_EXTERNAL_MEMORY_BACKEND",
    "MEMORY_CANDIDATE_MANDATORY_FIELDS",
    "MEMORY_PROVIDER_OPERATIONS",
    "MEMORY_PROVIDER_OPTIONAL_OFF",
    "MEMORY_VALIDATION_STATE_VALUES",
    "NO_PROMOTE_OPERATION",
    "MemoryCandidate",
    "MemoryProvider",
    "compute_admission_confidence",
    "parse_memory_candidate",
    "parse_memory_validation_state",
    "refuse_external_memory_backend",
    "refuse_memory_promote",
    "refuse_propose_with_admission_confidence",
    "stage_unbound_memory_edit",
]


MEMORY_PROVIDER_OPERATIONS: Final[frozenset[str]] = frozenset(
    {
        "propose",
        "admit",
        "recall",
        "get",
        "list",
        "history",
        "supersede",
        "invalidate",
        "expire",
        "scopes",
    }
)

# ``reflect`` is optional and off in v1 — cognition is QMA's (DEC-0317).
MEMORY_PROVIDER_OPTIONAL_OFF: Final[frozenset[str]] = frozenset({"reflect"})

NO_PROMOTE_OPERATION: Final[bool] = True

GAP_0072_EXTERNAL_MEMORY_BACKEND: Final[str] = "GAP-0072"

MEMORY_CANDIDATE_MANDATORY_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "provenance",
        "supporting_artifacts",
        "scope",
        "proposer",
        "occurrence_time",
    }
)

MEMORY_VALIDATION_STATE_VALUES: Final[frozenset[str]] = frozenset(
    member.value for member in MemoryValidationState
)

_PROPOSE_FORBIDDEN_FIELDS: Final[frozenset[str]] = frozenset({"admission_confidence"})


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


def refuse_propose_with_admission_confidence(**extra: object) -> TypedRefusal:
    """``admission_confidence`` is gate output — never agent input (DEC-0317)."""
    return _invalid(
        "admission_confidence",
        "admission_confidence is computed deterministically by the daemon "
        "admission gate from provenance, supporting artifacts, corroboration "
        "count and validation history; a propose call carrying it is refused "
        "(CT-43; FR-Q64; DEC-0317)",
        **extra,
    )


def refuse_memory_promote(**extra: object) -> TypedRefusal:
    """Memory candidates are admitted; promote never applies (DEC-0345)."""
    return _policy(
        "operation",
        "MemoryProvider has no promote operation; a memory candidate is "
        "admitted, never promoted (CT-43; FR-Q64; DEC-0345)",
        act="promote",
        **extra,
    )


def refuse_external_memory_backend(**extra: object) -> TypedRefusal:
    """External memory backends are Deferred GAP-0072 (DEC-0342)."""
    return _policy(
        "backend",
        "selecting or implementing an external memory backend is Deferred "
        "GAP-0072; v1 ships the MemoryProvider port and NoMemoryProvider only "
        "(CT-43; FR-Q64; DEC-0342)",
        gap=GAP_0072_EXTERNAL_MEMORY_BACKEND,
        deferred=True,
        **extra,
    )


def parse_memory_validation_state(value: object) -> Result[MemoryValidationState]:
    """Parse the closed seven-value validation_state vocabulary (CT-43)."""
    try:
        return Ok(parse_closed(MemoryValidationState, value))
    except VocabularyError:
        return _invalid(
            "validation_state",
            "validation_state is exactly proposed, validated, admitted, "
            "superseded, invalidated, expired, or contradicted (CT-43; DEC-0317)",
            given=repr(value),
            allowed=sorted(MEMORY_VALIDATION_STATE_VALUES),
        )


def compute_admission_confidence(
    *,
    provenance: Mapping[str, object],
    supporting_artifacts: Sequence[str],
    corroboration_count: int,
    validation_history: Sequence[str],
) -> float:
    """Deterministic gate scalar in ``[0.0, 1.0]`` (CT-43; DEC-0317).

    Pure function of evidence inputs only — never of a proposer-supplied
    confidence. Identical inputs always yield the identical rounded scalar.
    """
    score = 0.0
    if provenance:
        score += 0.25
    score += min(0.35, 0.07 * len(tuple(supporting_artifacts)))
    score += min(0.25, 0.05 * max(0, int(corroboration_count)))
    score += min(0.15, 0.03 * len(tuple(validation_history)))
    return round(min(1.0, max(0.0, score)), 6)


def _parse_provenance(value: object) -> Result[Mapping[str, object]]:
    if not isinstance(value, Mapping):
        return _invalid(
            "provenance",
            "provenance is a mandatory mapping describing source and derivation (CT-43; DEC-0317)",
            given=repr(type(value).__name__),
        )
    return Ok(MappingProxyType(dict(cast("Mapping[str, object]", value))))


def _parse_supporting_artifacts(value: object) -> Result[tuple[str, ...]]:
    if value is None:
        return _invalid(
            "supporting_artifacts",
            "supporting_artifacts is a declared sequence (may be empty), never "
            "null (CT-43; DEC-0317)",
        )
    if isinstance(value, str):
        if value.strip() == "":
            return _invalid(
                "supporting_artifacts",
                "artifact refs are non-empty strings (CT-43; DEC-0317)",
            )
        return Ok((value.strip(),))
    if isinstance(value, (list, tuple)):
        parsed: list[str] = []
        for item in cast("list[object] | tuple[object, ...]", value):
            if not isinstance(item, str) or item.strip() == "":
                return _invalid(
                    "supporting_artifacts",
                    "artifact refs are non-empty strings (CT-43; DEC-0317)",
                    given=repr(item),
                )
            parsed.append(item.strip())
        return Ok(tuple(parsed))
    return _invalid(
        "supporting_artifacts",
        "supporting_artifacts is a reference string or sequence of refs (CT-43; DEC-0317)",
        given=repr(type(value).__name__),
    )


def _parse_nonempty_str(value: object, field: str) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            field,
            f"{field} is a mandatory non-empty string (CT-43; DEC-0317)",
            given=repr(value),
        )
    return Ok(value.strip())


def _parse_occurrence_time(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid(
            "occurrence_time",
            "occurrence_time is a mandatory integer instant (CT-43; DEC-0317)",
            given=repr(value),
        )
    return Ok(value)


def _parse_optional_supersession(
    entry: Mapping[str, object],
) -> Result[str | None]:
    if "supersession" not in entry:
        return Ok(None)
    value = entry.get("supersession")
    if value is None:
        return _invalid(
            "supersession",
            "supersession is omitted as an absent key when unused, never null (CT-43; DEC-0317)",
        )
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            "supersession",
            "supersession is a non-empty memory ref when present (CT-43; DEC-0317)",
            given=repr(value),
        )
    return Ok(value.strip())


def _parse_content(value: object) -> Result[Mapping[str, object]]:
    if value is None:
        return Ok(MappingProxyType({}))
    if not isinstance(value, Mapping):
        return _invalid(
            "content",
            "content is a mapping when present (CT-43)",
            given=repr(type(value).__name__),
        )
    return Ok(MappingProxyType(dict(cast("Mapping[str, object]", value))))


@dataclass(frozen=True, slots=True)
class MemoryCandidate:
    """One memory candidate record (CT-43; AD-18; DEC-0317).

    ``admission_confidence`` is absent on propose input and present only after
    the daemon admission gate stamps it. Supersession is an omitted key when
    unused, never a null.
    """

    provenance: Mapping[str, object]
    supporting_artifacts: tuple[str, ...]
    scope: str
    proposer: str
    occurrence_time: int
    validation_state: MemoryValidationState = MemoryValidationState.PROPOSED
    id: str = field(default_factory=lambda: str(uuid4()))
    content: Mapping[str, object] = field(default_factory=dict[str, object])
    admission_confidence: float | None = None
    supersession: str | None = None
    corroboration_count: int = 0
    validation_history: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.provenance, MappingProxyType):
            object.__setattr__(self, "provenance", MappingProxyType(dict(self.provenance)))
        if not isinstance(self.content, MappingProxyType):
            object.__setattr__(self, "content", MappingProxyType(dict(self.content)))
        object.__setattr__(self, "supporting_artifacts", tuple(self.supporting_artifacts))
        object.__setattr__(self, "validation_history", tuple(self.validation_history))
        if self.corroboration_count < 0:
            msg = "corroboration_count must be >= 0 (CT-43)"
            raise VocabularyError(msg)
        if self.admission_confidence is not None and not (
            0.0 <= float(self.admission_confidence) <= 1.0
        ):
            msg = "admission_confidence must be in [0.0, 1.0] when set (CT-43)"
            raise VocabularyError(msg)

    def with_admission(
        self,
        confidence: float,
        *,
        state: MemoryValidationState = MemoryValidationState.ADMITTED,
    ) -> MemoryCandidate:
        """Return a copy stamped by the admission gate — never by a proposer."""
        history = (
            *self.validation_history,
            self.validation_state.value,
            state.value,
        )
        return MemoryCandidate(
            id=self.id,
            provenance=self.provenance,
            supporting_artifacts=self.supporting_artifacts,
            scope=self.scope,
            proposer=self.proposer,
            occurrence_time=self.occurrence_time,
            validation_state=state,
            content=self.content,
            admission_confidence=confidence,
            supersession=self.supersession,
            corroboration_count=self.corroboration_count,
            validation_history=history,
        )

    def to_payload(self, *, include_admission_confidence: bool = True) -> Mapping[str, object]:
        """JSON-native candidate payload.

        When ``include_admission_confidence`` is false the field is omitted so the
        payload is safe for a ``propose`` call.
        """
        payload: dict[str, object] = {
            "id": self.id,
            "provenance": dict(self.provenance),
            "supporting_artifacts": list(self.supporting_artifacts),
            "scope": self.scope,
            "proposer": self.proposer,
            "occurrence_time": self.occurrence_time,
            "validation_state": self.validation_state.value,
            "content": dict(self.content),
            "corroboration_count": self.corroboration_count,
            "validation_history": list(self.validation_history),
        }
        if self.supersession is not None:
            payload["supersession"] = self.supersession
        if include_admission_confidence and self.admission_confidence is not None:
            payload["admission_confidence"] = self.admission_confidence
        return MappingProxyType(payload)


def parse_memory_candidate(
    value: object,
    *,
    for_propose: bool = False,
) -> Result[MemoryCandidate]:
    """Validate a MemoryCandidate against CT-43.

    When ``for_propose`` is true, the presence of ``admission_confidence`` is
    refused — that scalar is gate output only.
    """
    if isinstance(value, MemoryCandidate):
        if for_propose and value.admission_confidence is not None:
            return refuse_propose_with_admission_confidence(
                given=value.admission_confidence,
            )
        return Ok(value)
    if not isinstance(value, Mapping):
        return _invalid(
            "candidate",
            "a MemoryCandidate is a mapping (CT-43; DEC-0317)",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[str, object]", value)
    if for_propose and "admission_confidence" in body:
        return refuse_propose_with_admission_confidence(given=body.get("admission_confidence"))

    missing = sorted(field for field in MEMORY_CANDIDATE_MANDATORY_FIELDS if field not in body)
    if missing:
        return _invalid(
            "candidate",
            "MemoryCandidate requires provenance, supporting_artifacts, scope, "
            "proposer and occurrence_time (CT-43; DEC-0317)",
            missing=missing,
        )

    provenance = _parse_provenance(body.get("provenance"))
    if not isinstance(provenance, Ok):
        return provenance
    artifacts = _parse_supporting_artifacts(body.get("supporting_artifacts"))
    if not isinstance(artifacts, Ok):
        return artifacts
    scope = _parse_nonempty_str(body.get("scope"), "scope")
    if not isinstance(scope, Ok):
        return scope
    proposer = _parse_nonempty_str(body.get("proposer"), "proposer")
    if not isinstance(proposer, Ok):
        return proposer
    occurrence = _parse_occurrence_time(body.get("occurrence_time"))
    if not isinstance(occurrence, Ok):
        return occurrence
    supersession = _parse_optional_supersession(body)
    if not isinstance(supersession, Ok):
        return supersession
    content = _parse_content(body.get("content"))
    if not isinstance(content, Ok):
        return content

    state_raw = body.get("validation_state", MemoryValidationState.PROPOSED.value)
    state = parse_memory_validation_state(state_raw)
    if not isinstance(state, Ok):
        return state

    candidate_id = body.get("id")
    if candidate_id is None:
        resolved_id = str(uuid4())
    elif isinstance(candidate_id, str) and candidate_id.strip() != "":
        resolved_id = candidate_id.strip()
    else:
        return _invalid(
            "id",
            "id is a non-empty string when present (CT-43)",
            given=repr(candidate_id),
        )

    corr_raw = body.get("corroboration_count", len(artifacts.value))
    if isinstance(corr_raw, bool) or not isinstance(corr_raw, int) or corr_raw < 0:
        return _invalid(
            "corroboration_count",
            "corroboration_count is a non-negative integer (CT-43)",
            given=repr(corr_raw),
        )

    history_raw = body.get("validation_history", ())
    if isinstance(history_raw, str):
        history = (history_raw,)
    elif isinstance(history_raw, (list, tuple)):
        history = tuple(
            str(item) for item in cast("list[object] | tuple[object, ...]", history_raw)
        )
    else:
        return _invalid(
            "validation_history",
            "validation_history is a sequence of state tokens (CT-43)",
            given=repr(type(history_raw).__name__),
        )

    confidence: float | None = None
    if "admission_confidence" in body and not for_propose:
        conf_raw = body.get("admission_confidence")
        if isinstance(conf_raw, bool) or not isinstance(conf_raw, (int, float)):
            return _invalid(
                "admission_confidence",
                "admission_confidence is a scalar in [0.0, 1.0] (CT-43)",
                given=repr(conf_raw),
            )
        confidence = float(conf_raw)
        if not 0.0 <= confidence <= 1.0:
            return _invalid(
                "admission_confidence",
                "admission_confidence is a scalar in [0.0, 1.0] (CT-43)",
                given=confidence,
            )

    return Ok(
        MemoryCandidate(
            id=resolved_id,
            provenance=provenance.value,
            supporting_artifacts=artifacts.value,
            scope=scope.value,
            proposer=proposer.value,
            occurrence_time=occurrence.value,
            validation_state=state.value,
            content=content.value,
            admission_confidence=confidence,
            supersession=supersession.value,
            corroboration_count=corr_raw,
            validation_history=history,
        )
    )


def stage_unbound_memory_edit(candidate: MemoryCandidate) -> Mapping[str, object]:
    """Wrap an unbound-desk candidate as one RefinementProposal ``memory`` edit.

    Staging only — not memory. Used while no MemoryProvider is bound for the
    desk (CT-43; DEC-0317, DEC-0321).
    """
    payload = dict(candidate.to_payload(include_admission_confidence=False))
    return MappingProxyType(
        {
            "kind": "memory",
            "operation": "create",
            "id": candidate.id,
            "content": payload,
        }
    )


@runtime_checkable
class MemoryProvider(Protocol):
    """Definitions-only MemoryProvider seam; daemon binds one provider per desk.

    Cardinality: singleton, scope key ``desk`` (see ``PORT_CONTRACTS``).
    Operation surface: propose, admit, recall, get, list, history, supersede,
    invalidate, expire, scopes. ``reflect`` is optional and off. There is no
    ``promote`` operation.
    """

    def propose(self, candidate: MemoryCandidate) -> Result[MemoryCandidate]:
        """Accept a candidate for admission consideration."""
        ...

    def admit(self, candidate: MemoryCandidate) -> Result[MemoryCandidate]:
        """Persist an admitted candidate into provider-owned storage."""
        ...

    def recall(self, scope: str, token_budget: int) -> Result[tuple[MemoryCandidate, ...]]:
        """Return admitted memory fitting the caller token budget."""
        ...

    def get(self, memory_id: str) -> Result[MemoryCandidate]:
        """Fetch one admitted memory by id."""
        ...

    def list(self, scope: str) -> Result[tuple[MemoryCandidate, ...]]:
        """Enumerate admitted memory in a scope."""
        ...

    def history(self, memory_id: str) -> Result[tuple[MemoryCandidate, ...]]:
        """Return supersession history for a memory id."""
        ...

    def supersede(self, memory_id: str, successor: MemoryCandidate) -> Result[MemoryCandidate]:
        """Mark ``memory_id`` superseded by ``successor``."""
        ...

    def invalidate(self, memory_id: str) -> Result[MemoryCandidate]:
        """Move a memory to ``invalidated``."""
        ...

    def expire(self, memory_id: str) -> Result[MemoryCandidate]:
        """Move a memory to ``expired``."""
        ...

    def scopes(self) -> Result[tuple[str, ...]]:
        """Enumerate scopes the provider serves."""
        ...
