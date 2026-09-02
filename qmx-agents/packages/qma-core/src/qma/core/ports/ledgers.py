"""Task Ledger entry schema and named leases (CT-51; AD-9; DEC-0308).

Definitions only. The daemon owns the Task Ledger store and persists every
entry through the wire. Append rights follow ``dispatch_lease``, distinct from
``environment_lease`` and ``quant_ledger_lease``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qma.core.ontology import ActorId
from qma.core.vocabulary.enums import LeaseKind, QuantLedgerEntryKind, TaskLedgerEntryKind
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "DAEMON_AUTHORED_ENTRY_KINDS",
    "HOOK_RETURNED_LEDGER_KIND",
    "LEDGER_ENTRY_OPTIONAL_REFS",
    "LEDGER_ENTRY_REQUIRED_FIELDS",
    "QUANT_LEDGER_ENTRY_REQUIRED_FIELDS",
    "QUANT_LEDGER_FORBIDDEN_TASK_KEYS",
    "SHARED_SEMANTIC_KEYS",
    "TASK_COMPLETED_FIELDS",
    "LedgerAuthor",
    "QuantLedgerEntry",
    "QuantLedgerLease",
    "TaskCompleted",
    "TaskLedgerEntry",
    "missing_task_completed_fields",
    "named_lease_kind",
    "parse_ledger_author",
    "parse_quant_ledger_entry",
    "parse_task_completed",
    "parse_task_ledger_entry",
    "stamp_hook_returned_ledger_entry",
]


LEDGER_ENTRY_REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "kind",
        "attempt_no",
        "authored_by",
        "recorded_at",
    }
)

QUANT_LEDGER_ENTRY_REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "id",
        "kind",
        "authored_by",
        "recorded_at",
    }
)

# Quant Ledger never restates or synthesizes another Task's ledger (DEC-0338).
QUANT_LEDGER_FORBIDDEN_TASK_KEYS: Final[frozenset[str]] = frozenset(
    {
        "task_ledger",
        "task_entries",
        "task_completed",
        "attempt_no",
    }
)

LEDGER_ENTRY_OPTIONAL_REFS: Final[frozenset[str]] = frozenset(
    {
        "trace_ref",
        "artifact_ref",
        "experiment_ref",
        "knowledge_ref",
    }
)

# Embedded objects under these keys would share semantics; entries carry *_ref.
SHARED_SEMANTIC_KEYS: Final[frozenset[str]] = frozenset(
    {
        "trace",
        "artifact",
        "experiment",
        "knowledge",
    }
)

TASK_COMPLETED_FIELDS: Final[tuple[str, ...]] = (
    "what_was_done",
    "what_changed",
    "evidence_and_artifact_refs",
    "unresolved_issues",
    "next_recommendation",
)

DAEMON_AUTHORED_ENTRY_KINDS: Final[frozenset[TaskLedgerEntryKind]] = frozenset(
    {
        TaskLedgerEntryKind.REASSIGNED,
        TaskLedgerEntryKind.UNKNOWN_TAIL,
    }
)

HOOK_RETURNED_LEDGER_KIND: Final[TaskLedgerEntryKind] = TaskLedgerEntryKind.LEDGER_ENTRY


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


def named_lease_kind(lease: object) -> Result[LeaseKind]:
    """Read the named lease token; refuse a bare or unknown lease (CT-51)."""
    token: object
    if isinstance(lease, QuantLedgerLease):
        return Ok(LeaseKind.QUANT_LEDGER_LEASE)
    if isinstance(lease, Mapping):
        token = cast("Mapping[str, object]", lease).get("lease")
    else:
        to_payload = getattr(lease, "to_payload", None)
        if callable(to_payload):
            payload = to_payload()
            if isinstance(payload, Mapping):
                token = cast("Mapping[str, object]", payload).get("lease")
            else:
                token = None
        else:
            token = lease
    try:
        return Ok(parse_closed(LeaseKind, token))
    except VocabularyError:
        return _invalid(
            "lease",
            "lease must be named dispatch_lease, environment_lease, or "
            "quant_ledger_lease — never bare (CT-51; DEC-0308)",
            given=repr(token),
        )


@dataclass(frozen=True, slots=True)
class QuantLedgerLease:
    """Per-Quant Quant Ledger append right, distinct from ``dispatch_lease``."""

    owner: ActorId
    holder_agent_id: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "lease": LeaseKind.QUANT_LEDGER_LEASE.value,
                "owner": self.owner.value,
                "holder_agent_id": self.holder_agent_id,
            }
        )


@dataclass(frozen=True, slots=True)
class QuantLedgerEntry:
    """One append-only Quant Ledger row (AD-9; FR-Q59)."""

    id: str
    kind: QuantLedgerEntryKind
    authored_by: LedgerAuthor
    recorded_at: int
    model_deployment_ref: str
    mission_ref: str | None = None
    body: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        if self.body is not None:
            object.__setattr__(self, "body", MappingProxyType(dict(self.body)))

    def to_payload(self) -> Mapping[str, object]:
        authored = self.authored_by.to_payload()
        payload: dict[str, object] = {
            "id": self.id,
            "kind": self.kind.value,
            "authored_by": authored if isinstance(authored, str) else dict(authored),
            "recorded_at": self.recorded_at,
            "model_deployment_ref": self.model_deployment_ref,
        }
        if self.mission_ref is not None:
            payload["mission_ref"] = self.mission_ref
        if self.body is not None:
            payload["body"] = dict(self.body)
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class LedgerAuthor:
    """Agent ref plus owning Quant ``ActorId``, or ``daemon`` (CT-51)."""

    agent_ref: str | None = None
    quant: ActorId | None = None
    daemon: bool = False

    def __post_init__(self) -> None:
        if self.daemon:
            if self.agent_ref is not None or self.quant is not None:
                msg = "daemon-authored entries name no agent and no Quant ActorId"
                raise ValueError(msg)
            return
        if self.agent_ref is None or self.quant is None:
            msg = "non-daemon authored_by requires an agent ref and Quant ActorId"
            raise ValueError(msg)

    def to_payload(self) -> str | Mapping[str, object]:
        if self.daemon:
            return "daemon"
        agent_ref = self.agent_ref
        quant = self.quant
        if agent_ref is None or quant is None:
            msg = "non-daemon authored_by requires an agent ref and Quant ActorId"
            raise ValueError(msg)
        return MappingProxyType({"agent": agent_ref, "quant": quant.value})


@dataclass(frozen=True, slots=True)
class TaskCompleted:
    """Five-field structured completion append (CT-51; DEC-0338)."""

    what_was_done: str
    what_changed: str
    evidence_and_artifact_refs: tuple[str, ...]
    unresolved_issues: str
    next_recommendation: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "what_was_done": self.what_was_done,
                "what_changed": self.what_changed,
                "evidence_and_artifact_refs": list(self.evidence_and_artifact_refs),
                "unresolved_issues": self.unresolved_issues,
                "next_recommendation": self.next_recommendation,
            }
        )


@dataclass(frozen=True, slots=True)
class TaskLedgerEntry:
    """One append-only Task Ledger row (CT-51; DEC-0308)."""

    id: str
    kind: TaskLedgerEntryKind
    attempt_no: int
    authored_by: LedgerAuthor
    recorded_at: int
    model_deployment_ref: str | None = None
    trace_ref: str | None = None
    artifact_ref: str | None = None
    experiment_ref: str | None = None
    knowledge_ref: str | None = None
    task_completed: TaskCompleted | None = None
    incomplete_task_completed: Mapping[str, object] | None = None
    previous_holder_agent_id: str | None = None
    holder_agent_id: str | None = None
    hook_registry_id: str | None = None
    last_acked_id: str | None = None

    def __post_init__(self) -> None:
        if self.incomplete_task_completed is not None:
            object.__setattr__(
                self,
                "incomplete_task_completed",
                MappingProxyType(dict(self.incomplete_task_completed)),
            )

    @property
    def task_completed_complete(self) -> bool:
        """True when a TaskCompleted entry carries all five fixed fields."""
        return self.task_completed is not None and not missing_task_completed_fields(
            self.task_completed.to_payload()
        )

    def to_payload(self) -> Mapping[str, object]:
        authored = self.authored_by.to_payload()
        payload: dict[str, object] = {
            "id": self.id,
            "kind": self.kind.value,
            "attempt_no": self.attempt_no,
            "authored_by": authored if isinstance(authored, str) else dict(authored),
            "recorded_at": self.recorded_at,
        }
        if self.model_deployment_ref is not None:
            payload["model_deployment_ref"] = self.model_deployment_ref
        if self.trace_ref is not None:
            payload["trace_ref"] = self.trace_ref
        if self.artifact_ref is not None:
            payload["artifact_ref"] = self.artifact_ref
        if self.experiment_ref is not None:
            payload["experiment_ref"] = self.experiment_ref
        if self.knowledge_ref is not None:
            payload["knowledge_ref"] = self.knowledge_ref
        if self.task_completed is not None:
            payload["task_completed"] = dict(self.task_completed.to_payload())
        elif self.incomplete_task_completed is not None:
            payload["task_completed"] = dict(self.incomplete_task_completed)
        if self.previous_holder_agent_id is not None:
            payload["previous_holder_agent_id"] = self.previous_holder_agent_id
        if self.holder_agent_id is not None:
            payload["holder_agent_id"] = self.holder_agent_id
        if self.hook_registry_id is not None:
            payload["hook_registry_id"] = self.hook_registry_id
        if self.last_acked_id is not None:
            payload["last_acked_id"] = self.last_acked_id
        return MappingProxyType(payload)


def parse_ledger_author(
    value: object,
    *,
    kind: TaskLedgerEntryKind,
) -> Result[LedgerAuthor]:
    """Parse ``authored_by``: Agent+Quant ActorId, or ``daemon`` on daemon kinds."""
    daemon_kind = kind in DAEMON_AUTHORED_ENTRY_KINDS
    if value == "daemon" or (
        isinstance(value, Mapping)
        and (
            cast("Mapping[str, object]", value).get("kind") == "daemon"
            or cast("Mapping[str, object]", value).get("agent") == "daemon"
        )
    ):
        if not daemon_kind and kind is not TaskLedgerEntryKind.LEDGER_ENTRY:
            return _invalid(
                "authored_by",
                "authored_by daemon is legal only on daemon-authored kinds and "
                "hook-returned ledger_entry (CT-51; DEC-0308)",
                kind=kind.value,
            )
        return Ok(LedgerAuthor(daemon=True))
    if daemon_kind:
        return _invalid(
            "authored_by",
            "daemon-authored reassigned and unknown_tail carry authored_by daemon "
            "and name no model deployment (CT-51; DEC-0308)",
            kind=kind.value,
        )
    if not isinstance(value, Mapping):
        return _invalid(
            "authored_by",
            "non-daemon authored_by is an agent ref plus the owning Quant ActorId "
            "(CT-51; DEC-0308)",
            given=repr(value),
        )
    body = cast("Mapping[str, object]", value)
    agent_ref = body.get("agent") or body.get("agent_id")
    quant_raw = body.get("quant") or body.get("actor_id")
    if not isinstance(agent_ref, str) or agent_ref.strip() == "":
        return _invalid(
            "authored_by",
            "non-daemon authored_by requires a non-empty agent ref (CT-51; DEC-0308)",
        )
    parsed_quant = ActorId.try_create(quant_raw)
    if not isinstance(parsed_quant, Ok):
        return _invalid(
            "authored_by",
            "non-daemon authored_by requires the owning Quant ActorId (CT-51; DEC-0308)",
            given=repr(quant_raw),
        )
    return Ok(LedgerAuthor(agent_ref=agent_ref.strip(), quant=parsed_quant.value))


def missing_task_completed_fields(value: object) -> tuple[str, ...]:
    """Return the TaskCompleted fields omitted from ``value`` (CT-51; FR-Q58).

    A missing key or a blank string counts as omitted. An empty evidence-ref
    list is present (no refs) rather than omitted.
    """
    if not isinstance(value, Mapping):
        return TASK_COMPLETED_FIELDS
    body = cast("Mapping[str, object]", value)
    missing: list[str] = []
    for field in TASK_COMPLETED_FIELDS:
        if field not in body:
            missing.append(field)
            continue
        item = body.get(field)
        if field == "evidence_and_artifact_refs":
            if item is None or (isinstance(item, str) and item.strip() == ""):
                missing.append(field)
            continue
        if not isinstance(item, str) or item.strip() == "":
            missing.append(field)
    return tuple(missing)


def stamp_hook_returned_ledger_entry(
    entry: Mapping[str, object],
    *,
    hook_registry_id: str,
) -> Mapping[str, object]:
    """Record a hook-returned ``ledger_entry`` as daemon + hook registry id."""
    stamped = dict(entry)
    stamped["kind"] = HOOK_RETURNED_LEDGER_KIND.value
    stamped["authored_by"] = "daemon"
    stamped["hook_registry_id"] = hook_registry_id.strip()
    stamped.pop("model_deployment_ref", None)
    return MappingProxyType(stamped)


def parse_task_completed(value: object) -> Result[TaskCompleted]:
    """Parse the five-field TaskCompleted structured append."""
    if not isinstance(value, Mapping):
        return _invalid(
            "task_completed",
            "task_completed is the five-field structured append (CT-51; DEC-0338)",
        )
    body = cast("Mapping[str, object]", value)
    missing = [field for field in TASK_COMPLETED_FIELDS if field not in body]
    if missing:
        return _invalid(
            "task_completed",
            "task_completed carries exactly five fixed fields (CT-51; DEC-0338)",
            missing=missing,
        )
    done = body.get("what_was_done")
    changed = body.get("what_changed")
    unresolved = body.get("unresolved_issues")
    next_step = body.get("next_recommendation")
    refs_raw = body.get("evidence_and_artifact_refs")
    if not isinstance(done, str) or not isinstance(changed, str):
        return _invalid("task_completed", "what_was_done and what_changed are strings")
    if not isinstance(unresolved, str) or not isinstance(next_step, str):
        return _invalid(
            "task_completed",
            "unresolved_issues and next_recommendation are strings",
        )
    if isinstance(refs_raw, str):
        refs = (refs_raw,)
    elif isinstance(refs_raw, (list, tuple)):
        parsed_refs: list[str] = []
        for item in cast("list[object] | tuple[object, ...]", refs_raw):
            if not isinstance(item, str) or item.strip() == "":
                return _invalid(
                    "evidence_and_artifact_refs",
                    "evidence and artifact refs are non-empty reference strings, "
                    "never shared semantics (CT-51; DEC-0308)",
                )
            parsed_refs.append(item)
        refs = tuple(parsed_refs)
    else:
        return _invalid(
            "evidence_and_artifact_refs",
            "evidence_and_artifact_refs is a reference string or list of refs",
        )
    return Ok(
        TaskCompleted(
            what_was_done=done,
            what_changed=changed,
            evidence_and_artifact_refs=refs,
            unresolved_issues=unresolved,
            next_recommendation=next_step,
        )
    )


def _parse_optional_ref(entry: Mapping[str, object], field: str) -> Result[str | None]:
    if field not in entry:
        return Ok(None)
    value = entry.get(field)
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            field,
            f"{field} is a reference string, never shared semantics (CT-51; DEC-0308)",
            given=repr(value),
        )
    return Ok(value.strip())


def parse_task_ledger_entry(value: object) -> Result[TaskLedgerEntry]:
    """Validate a Task Ledger entry for persistence (CT-51; FR-Q57)."""
    if not isinstance(value, Mapping):
        return _invalid("entry", "a Task Ledger entry is an object")
    entry = cast("Mapping[str, object]", value)
    overlap = SHARED_SEMANTIC_KEYS.intersection(entry.keys())
    if overlap:
        return _policy(
            "entry",
            "trace, artifact, experiment, and knowledge remain references "
            "(*_ref), never shared semantics (CT-51; DEC-0308)",
            given=sorted(overlap),
        )
    missing = [field for field in sorted(LEDGER_ENTRY_REQUIRED_FIELDS) if field not in entry]
    if missing:
        return _invalid(
            "entry",
            "every Task Ledger entry carries id, kind, attempt_no, authored_by, "
            "and recorded_at (CT-51; DEC-0308)",
            missing=missing,
        )
    entry_id = entry.get("id")
    if not isinstance(entry_id, str) or entry_id.strip() == "":
        return _invalid("id", "id is the entry's own stable identity, never a _ref")
    try:
        kind = parse_closed(TaskLedgerEntryKind, entry.get("kind"))
    except VocabularyError:
        return _invalid(
            "kind",
            "kind is a closed Task Ledger entry kind (CT-51; DEC-0308)",
            given=repr(entry.get("kind")),
        )
    attempt_no = entry.get("attempt_no")
    if not isinstance(attempt_no, int) or isinstance(attempt_no, bool) or attempt_no < 0:
        return _invalid("attempt_no", "attempt_no is a non-negative count (CT-51)")
    recorded_at = entry.get("recorded_at")
    if not isinstance(recorded_at, int) or isinstance(recorded_at, bool) or recorded_at < 0:
        return _invalid(
            "recorded_at",
            "recorded_at is the daemon-stamped UTC instant as int64 nanoseconds (CT-51; AD-6)",
        )
    author = parse_ledger_author(entry.get("authored_by"), kind=kind)
    if not isinstance(author, Ok):
        return author
    daemon_authored = author.value.daemon
    model_ref = entry.get("model_deployment_ref")
    if daemon_authored:
        if model_ref is not None:
            return _invalid(
                "model_deployment_ref",
                "daemon-authored entries name no model deployment (CT-51; DEC-0308)",
            )
        resolved_model: str | None = None
    else:
        if not isinstance(model_ref, str) or model_ref.strip() == "":
            return _invalid(
                "model_deployment_ref",
                "non-daemon entries carry the model deployment used (CT-51; DEC-0308)",
            )
        resolved_model = model_ref.strip()

    refs: dict[str, str | None] = {}
    for field in LEDGER_ENTRY_OPTIONAL_REFS:
        parsed_ref = _parse_optional_ref(entry, field)
        if not isinstance(parsed_ref, Ok):
            return parsed_ref
        refs[field] = parsed_ref.value

    completed: TaskCompleted | None = None
    incomplete_completed: Mapping[str, object] | None = None
    if kind is TaskLedgerEntryKind.TASK_COMPLETED:
        raw_completed = entry.get("task_completed")
        if isinstance(raw_completed, Mapping):
            completed_body = cast("Mapping[str, object]", raw_completed)
            parsed_completed = parse_task_completed(completed_body)
            if isinstance(parsed_completed, Ok):
                completed = parsed_completed.value
            else:
                # Persist the incomplete append; completion is refused separately.
                incomplete_completed = MappingProxyType(dict(completed_body))
        else:
            incomplete_completed = MappingProxyType({})
    elif "task_completed" in entry:
        return _invalid(
            "task_completed",
            "task_completed is present only on a TaskCompleted entry (CT-51)",
        )

    previous_holder = entry.get("previous_holder_agent_id")
    holder = entry.get("holder_agent_id")
    previous: str | None
    if previous_holder is None:
        previous = None
    elif isinstance(previous_holder, str) and previous_holder.strip():
        previous = previous_holder.strip()
    else:
        return _invalid("previous_holder_agent_id", "previous holder is a non-empty agent id")
    current_holder: str | None
    if holder is None:
        current_holder = None
    elif isinstance(holder, str) and holder.strip():
        current_holder = holder.strip()
    else:
        return _invalid("holder_agent_id", "holder_agent_id is a non-empty agent id")

    hook_registry_id_raw = entry.get("hook_registry_id")
    if hook_registry_id_raw is None and isinstance(entry.get("authored_by"), Mapping):
        hook_registry_id_raw = cast("Mapping[str, object]", entry.get("authored_by")).get(
            "hook_registry_id"
        )
    hook_registry_id: str | None
    if hook_registry_id_raw is None:
        hook_registry_id = None
    elif isinstance(hook_registry_id_raw, str) and hook_registry_id_raw.strip():
        hook_registry_id = hook_registry_id_raw.strip()
    else:
        return _invalid(
            "hook_registry_id",
            "hook_registry_id is a non-empty returning hook registry id (CT-51; FR-Q58)",
        )
    if kind is HOOK_RETURNED_LEDGER_KIND:
        if not daemon_authored:
            return _invalid(
                "authored_by",
                "a hook-returned ledger_entry is recorded with authored_by daemon "
                "plus the returning hook's registry id (CT-51; FR-Q58)",
            )
        if hook_registry_id is None:
            return _invalid(
                "hook_registry_id",
                "a hook-returned ledger_entry carries the returning hook's "
                "registry id (CT-51; FR-Q58)",
            )
    elif hook_registry_id is not None:
        return _invalid(
            "hook_registry_id",
            "hook_registry_id is only on a hook-returned ledger_entry (CT-51; FR-Q58)",
        )

    last_acked = entry.get("last_acked_id")
    last_acked_id: str | None
    if last_acked is None:
        last_acked_id = None
    elif isinstance(last_acked, str) and last_acked.strip():
        last_acked_id = last_acked.strip()
    else:
        return _invalid("last_acked_id", "last_acked_id is a non-empty id")

    return Ok(
        TaskLedgerEntry(
            id=entry_id.strip(),
            kind=kind,
            attempt_no=attempt_no,
            authored_by=author.value,
            recorded_at=recorded_at,
            model_deployment_ref=resolved_model,
            trace_ref=refs["trace_ref"],
            artifact_ref=refs["artifact_ref"],
            experiment_ref=refs["experiment_ref"],
            knowledge_ref=refs["knowledge_ref"],
            task_completed=completed,
            incomplete_task_completed=incomplete_completed,
            previous_holder_agent_id=previous,
            holder_agent_id=current_holder,
            hook_registry_id=hook_registry_id,
            last_acked_id=last_acked_id,
        )
    )


def parse_quant_ledger_entry(value: object) -> Result[QuantLedgerEntry]:
    """Validate a Quant Ledger entry against the declared desk-level schema."""
    if not isinstance(value, Mapping):
        return _invalid("entry", "a Quant Ledger entry is an object")
    entry = cast("Mapping[str, object]", value)
    overlap = QUANT_LEDGER_FORBIDDEN_TASK_KEYS.intersection(entry.keys())
    if overlap:
        return _policy(
            "entry",
            "the Quant Ledger never restates or synthesizes another Task's ledger "
            "(CT-51; DEC-0338; FR-Q59)",
            given=sorted(overlap),
        )
    missing = [field for field in sorted(QUANT_LEDGER_ENTRY_REQUIRED_FIELDS) if field not in entry]
    if missing:
        return _invalid(
            "entry",
            "every Quant Ledger entry carries id, kind, authored_by, and recorded_at "
            "(AD-9; FR-Q59)",
            missing=missing,
        )
    entry_id = entry.get("id")
    if not isinstance(entry_id, str) or entry_id.strip() == "":
        return _invalid("id", "id is the entry's own stable identity, never a _ref")
    try:
        kind = parse_closed(QuantLedgerEntryKind, entry.get("kind"))
    except VocabularyError:
        return _invalid(
            "kind",
            "kind is a declared Quant Ledger entry: mission_opened, mission_closed, "
            "delegation, escalation, or standing_decision (AD-9; FR-Q59)",
            given=repr(entry.get("kind")),
        )
    recorded_at = entry.get("recorded_at")
    if not isinstance(recorded_at, int) or isinstance(recorded_at, bool) or recorded_at < 0:
        return _invalid(
            "recorded_at",
            "recorded_at is the daemon-stamped UTC instant as int64 nanoseconds (AD-6)",
        )
    author = parse_ledger_author(entry.get("authored_by"), kind=TaskLedgerEntryKind.PROGRESS)
    if not isinstance(author, Ok):
        return author
    if author.value.daemon:
        return _invalid(
            "authored_by",
            "Quant Ledger entries are authored by an Agent of the owning Quant (AD-9; FR-Q59)",
        )
    model_ref = entry.get("model_deployment_ref")
    if not isinstance(model_ref, str) or model_ref.strip() == "":
        return _invalid(
            "model_deployment_ref",
            "Quant Ledger entries carry the model deployment used (AD-9; FR-Q59)",
        )
    mission_raw = entry.get("mission_ref")
    mission_ref: str | None
    if mission_raw is None:
        mission_ref = None
    elif isinstance(mission_raw, str) and mission_raw.strip():
        mission_ref = mission_raw.strip()
    else:
        return _invalid("mission_ref", "mission_ref is a non-empty reference string")
    body_raw = entry.get("body")
    body: Mapping[str, object] | None
    if body_raw is None:
        body = None
    elif isinstance(body_raw, Mapping):
        body = MappingProxyType(dict(cast("Mapping[str, object]", body_raw)))
    else:
        return _invalid("body", "body is an object when present")
    return Ok(
        QuantLedgerEntry(
            id=entry_id.strip(),
            kind=kind,
            authored_by=author.value,
            recorded_at=recorded_at,
            model_deployment_ref=model_ref.strip(),
            mission_ref=mission_ref,
            body=body,
        )
    )
