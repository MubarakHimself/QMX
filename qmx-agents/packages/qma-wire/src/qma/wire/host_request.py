"""RLM kernel ``host_request`` bridge contract (AD-14; DEC-0313; FR-Q19).

Every host call the RLM kernel makes is a ``qma-wire`` command or query under
the Task's ``scope_path`` and ``correlation_id`` — never a second channel,
shared-process shortcut, or untyped host call. The verb set is closed-and-addable
here; each verb maps to exactly one daemon-owned primitive and names that
primitive's ``before_*`` hook. An unmapped verb returns ``UnknownHostRequest``.
Async spawn returns the AD-17 ``JobHandle`` contract (job id + closed state),
never a fabricated completion, under ``registry:rlm.depth_cap``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.refusals import UnknownHostRequest
from qma.core.vocabulary import HOOK_EVENT_NAMES, HookVerb, JobHandleState, parse_closed
from qma.wire.envelope import WireEnvelope, parse_scope_path
from qma.wire.vocabulary import MessageFamily
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
)

__all__ = [
    "ALTERNATE_RLM_TRANSPORTS",
    "HOST_REQUEST_BRIDGE_TRANSPORT",
    "HOST_REQUEST_OWNING_AD",
    "HOST_REQUEST_PRIMITIVE_MAP",
    "HOST_REQUEST_VERBS",
    "HOST_REQUEST_VOCABULARY_OWNER",
    "JOB_HANDLE_NONTERMINAL_STATES",
    "JOB_HANDLE_TERMINAL_STATES",
    "RLM_DEPTH_CAP_DEFAULT",
    "RLM_DEPTH_CAP_REGISTRY_KEY",
    "AsyncHostResult",
    "HostRequestEmission",
    "HostRequestMapping",
    "HostRequestVerbError",
    "JobHandleContract",
    "assert_no_alternate_rlm_transport",
    "emit_host_request",
    "enforce_spawn_depth",
    "example_host_request_payloads",
    "host_request_type_family",
    "host_request_wire_family",
    "parse_host_request_verb",
    "resolve_host_request",
]


HOST_REQUEST_VOCABULARY_OWNER: Final[str] = "qma-wire"
HOST_REQUEST_OWNING_AD: Final[str] = "AD-14"
HOST_REQUEST_BRIDGE_TRANSPORT: Final[str] = "qma-wire"
RLM_DEPTH_CAP_REGISTRY_KEY: Final[str] = "rlm.depth_cap"
RLM_DEPTH_CAP_DEFAULT: Final[int] = 2

# Alternate channels the bridge contract forbids (stdio host IPC, in-process
# shortcut, untyped RPC). The only sanctioned path is qma-wire command/query.
ALTERNATE_RLM_TRANSPORTS: Final[frozenset[str]] = frozenset(
    {
        "stdio_jsonl",
        "shared_process",
        "in_process_shortcut",
        "untyped_rpc",
        "direct_daemon_call",
    }
)

WireFamilyName = Literal["command", "query"]

JOB_HANDLE_TERMINAL_STATES: Final[frozenset[str]] = frozenset(
    {
        JobHandleState.DONE.value,
        JobHandleState.FAILED.value,
        JobHandleState.CANCELLED.value,
        JobHandleState.ABORTED.value,
    }
)
JOB_HANDLE_NONTERMINAL_STATES: Final[frozenset[str]] = frozenset(
    {
        JobHandleState.QUEUED.value,
        JobHandleState.RUNNING.value,
        JobHandleState.UNKNOWN.value,
    }
)


@dataclass(frozen=True, slots=True)
class HostRequestMapping:
    """One closed host_request verb → one daemon-owned primitive."""

    verb: str
    daemon_primitive: str
    before_hook: str
    wire_family: WireFamilyName
    returns_job_handle: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "verb": self.verb,
            "daemon_primitive": self.daemon_primitive,
            "before_hook": self.before_hook,
            "wire_family": self.wire_family,
            "returns_job_handle": self.returns_job_handle,
        }


def _map(
    verb: HookVerb,
    *,
    wire_family: WireFamilyName = "command",
    returns_job_handle: bool = False,
) -> HostRequestMapping:
    primitive = verb.value
    before = f"before_{primitive}"
    if before not in HOOK_EVENT_NAMES:
        raise RuntimeError(f"daemon primitive {primitive!r} lacks {before}")
    return HostRequestMapping(
        verb=primitive,
        daemon_primitive=primitive,
        before_hook=before,
        wire_family=wire_family,
        returns_job_handle=returns_job_handle,
    )


# Seed RLM bridge verbs: identity-mapped onto AD-10 daemon primitives.
# Async spawn returns JobHandle under registry:rlm.depth_cap (DEC-0313).
_SEED_MAPPINGS: Final[tuple[HostRequestMapping, ...]] = (
    _map(HookVerb.SUBAGENT_SPAWN, returns_job_handle=True),
    _map(HookVerb.ENV_CREATE, returns_job_handle=True),
    _map(HookVerb.MESSAGE_SEND),
    _map(HookVerb.TOOL),
    _map(HookVerb.LEDGER_APPEND),
    _map(HookVerb.ARTIFACT_REGISTER),
    _map(HookVerb.EXPERIMENT_REGISTER),
    _map(HookVerb.MEMORY_WRITE),
    # Read-path host call: still maps to one daemon primitive / before_* hook.
    _map(HookVerb.GRAPH_TRANSITION, wire_family="query"),
)

HOST_REQUEST_PRIMITIVE_MAP: Final[MappingProxyType[str, HostRequestMapping]] = MappingProxyType(
    {item.verb: item for item in _SEED_MAPPINGS}
)
HOST_REQUEST_VERBS: Final[frozenset[str]] = frozenset(HOST_REQUEST_PRIMITIVE_MAP)


class HostRequestVerbError(ValueError):
    """Raised when a host_request verb is not in the closed qma-wire set."""


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


def parse_host_request_verb(value: object) -> str:
    """Accept only a verb declared in the closed-and-addable qma-wire set."""
    if not isinstance(value, str) or not value:
        raise HostRequestVerbError(f"{value!r} is not a host_request verb")
    if value not in HOST_REQUEST_VERBS:
        raise HostRequestVerbError(
            f"{value!r} is not a member of the closed host_request verb set "
            f"(owner={HOST_REQUEST_VOCABULARY_OWNER})"
        )
    return value


def host_request_wire_family(verb: object) -> MessageFamily:
    """Return command/query transport family for a declared host_request verb."""
    name = parse_host_request_verb(verb)
    family = HOST_REQUEST_PRIMITIVE_MAP[name].wire_family
    return MessageFamily.COMMAND if family == "command" else MessageFamily.QUERY


def resolve_host_request(verb: object) -> Result[HostRequestMapping]:
    """Resolve a verb to its primitive mapping, or ``UnknownHostRequest``."""
    if not isinstance(verb, str) or not verb:
        return UnknownHostRequest.of(verb=repr(verb))
    mapping = HOST_REQUEST_PRIMITIVE_MAP.get(verb)
    if mapping is None:
        return UnknownHostRequest.of(verb=verb)
    return Ok(mapping)


def assert_no_alternate_rlm_transport(transport: object) -> Result[str]:
    """Refuse any RLM host path that is not the qma-wire bridge."""
    if not isinstance(transport, str) or not transport:
        return _invalid("transport", "transport must be a non-empty string")
    if transport in ALTERNATE_RLM_TRANSPORTS:
        return _policy(
            "transport",
            "RLM host calls use the qma-wire host_request bridge only; "
            "no second channel, shared-process shortcut, or untyped host call",
            given=transport,
            sanctioned=HOST_REQUEST_BRIDGE_TRANSPORT,
        )
    if transport != HOST_REQUEST_BRIDGE_TRANSPORT:
        return _policy(
            "transport",
            "RLM host transport must be qma-wire",
            given=transport,
            sanctioned=HOST_REQUEST_BRIDGE_TRANSPORT,
        )
    return Ok(HOST_REQUEST_BRIDGE_TRANSPORT)


def enforce_spawn_depth(
    current_depth: object,
    *,
    depth_cap: object = RLM_DEPTH_CAP_DEFAULT,
) -> Result[int]:
    """Enforce ``registry:rlm.depth_cap`` on async RLM spawn (default 2)."""
    if (
        not isinstance(depth_cap, int)
        or isinstance(depth_cap, bool)
        or depth_cap < 0
    ):
        return _invalid(
            "depth_cap",
            "depth_cap is a non-negative int from registry:rlm.depth_cap",
            registry_key=RLM_DEPTH_CAP_REGISTRY_KEY,
        )
    if (
        not isinstance(current_depth, int)
        or isinstance(current_depth, bool)
        or current_depth < 0
    ):
        return _invalid(
            "current_depth",
            "current_depth is a non-negative int spawn depth",
            registry_key=RLM_DEPTH_CAP_REGISTRY_KEY,
        )
    # Depth cap N permits depths 0..N-1 to spawn; depth N may not recurse.
    if current_depth >= depth_cap:
        return _policy(
            "spawn_depth",
            "RLM spawn depth exceeds registry:rlm.depth_cap",
            current_depth=current_depth,
            depth_cap=depth_cap,
            registry_key=RLM_DEPTH_CAP_REGISTRY_KEY,
        )
    return Ok(current_depth)


@dataclass(frozen=True, slots=True)
class JobHandleContract:
    """AD-17 JobHandle surface returned for async host_request spawn.

    Admission-only: state is non-terminal. Fabricated terminal completions are
    refused by construction.
    """

    job_id: str
    state: str
    correlation_id: str

    def to_dict(self) -> dict[str, object]:
        return {
            "job_id": self.job_id,
            "state": self.state,
            "correlation_id": self.correlation_id,
        }

    @classmethod
    def try_create(
        cls,
        *,
        job_id: object,
        state: object,
        correlation_id: object,
    ) -> Result[JobHandleContract]:
        if not isinstance(job_id, str) or job_id.strip() == "":
            return _invalid("job_id", "job_id is a non-empty durable id")
        try:
            resolved_state = parse_closed(JobHandleState, state)
        except ValueError as exc:
            return _invalid("state", str(exc), given=repr(state))
        if resolved_state.value in JOB_HANDLE_TERMINAL_STATES:
            return _policy(
                "state",
                "async host_request returns JobHandle admission state, "
                "never a fabricated terminal completion",
                state=resolved_state.value,
            )
        if not isinstance(correlation_id, str) or correlation_id.strip() == "":
            return _invalid(
                "correlation_id",
                "JobHandle copies the Task correlation_id verbatim",
            )
        return Ok(
            cls(
                job_id=job_id,
                state=resolved_state.value,
                correlation_id=correlation_id,
            )
        )


@dataclass(frozen=True, slots=True)
class AsyncHostResult:
    """Bridge return for an async host_request: JobHandle, not a completion."""

    job_handle: JobHandleContract
    before_hook: str
    daemon_primitive: str

    def to_dict(self) -> dict[str, object]:
        return {
            "job_handle": self.job_handle.to_dict(),
            "before_hook": self.before_hook,
            "daemon_primitive": self.daemon_primitive,
        }


@dataclass(frozen=True, slots=True)
class HostRequestEmission:
    """Typed host call ready for the wire under Task scope and correlation."""

    envelope: WireEnvelope
    mapping: HostRequestMapping
    async_result: AsyncHostResult | None = None

    @property
    def before_hook(self) -> str:
        return self.mapping.before_hook

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {
            "envelope": self.envelope.to_dict(),
            "mapping": self.mapping.to_dict(),
        }
        if self.async_result is not None:
            out["async_result"] = self.async_result.to_dict()
        return out


def emit_host_request(
    *,
    verb: object,
    scope_path: object,
    correlation_id: object,
    producer_id: object,
    id: object,
    v: object,
    args: object = None,
    transport: object = HOST_REQUEST_BRIDGE_TRANSPORT,
    current_spawn_depth: object = 0,
    depth_cap: object = RLM_DEPTH_CAP_DEFAULT,
    job_id: object = None,
    job_state: object = JobHandleState.QUEUED.value,
) -> Result[HostRequestEmission]:
    """Emit an RLM host call as a qma-wire command/query envelope.

    Unmapped verbs return ``UnknownHostRequest``. Async verbs return a
    ``JobHandleContract`` under ``registry:rlm.depth_cap`` rather than a
    fabricated completion.
    """
    transport_check = assert_no_alternate_rlm_transport(transport)
    if not isinstance(transport_check, Ok):
        return transport_check

    resolved = resolve_host_request(verb)
    if not isinstance(resolved, Ok):
        return resolved
    mapping = resolved.value

    if not isinstance(correlation_id, str) or correlation_id.strip() == "":
        return _invalid(
            "correlation_id",
            "host_request carries the Task correlation_id verbatim",
        )
    try:
        path = parse_scope_path(scope_path)
    except ValueError as exc:
        return _invalid("scope_path", str(exc))
    if not path:
        return _invalid(
            "scope_path",
            "host_request carries the Task scope_path (non-empty ancestor chain)",
        )
    # Task must be present so the call is Task-scoped (AD-14).
    kinds = {segment.kind for segment in path}
    if "task" not in kinds:
        return _invalid(
            "scope_path",
            "host_request scope_path must include the Task segment",
        )

    payload_args: dict[str, object]
    if args is None:
        payload_args = {}
    elif isinstance(args, Mapping):
        payload_args = {}
        for key_obj, value in cast("Mapping[object, object]", args).items():
            if not isinstance(key_obj, str):
                return _invalid("args", "args keys must be strings")
            if value is None:
                return _invalid("args", "null is prohibited; omit absent keys (fp1)")
            payload_args[key_obj] = value
    else:
        return _invalid("args", "args must be an object when present")

    payload: dict[str, object] = {
        "family": "host_request",
        "verb": mapping.verb,
        "daemon_primitive": mapping.daemon_primitive,
        "before_hook": mapping.before_hook,
        "wire_family": mapping.wire_family,
        "args": payload_args,
    }

    async_result: AsyncHostResult | None = None
    if mapping.returns_job_handle:
        depth_check = enforce_spawn_depth(current_spawn_depth, depth_cap=depth_cap)
        if not isinstance(depth_check, Ok):
            return depth_check
        if job_id is None:
            if not isinstance(id, str) or id.strip() == "":
                return _invalid("job_id", "async host_request requires a job_id or id")
            resolved_job_id: object = f"job:{id}"
        else:
            resolved_job_id = job_id
        handle = JobHandleContract.try_create(
            job_id=resolved_job_id,
            state=job_state,
            correlation_id=correlation_id,
        )
        if not isinstance(handle, Ok):
            return handle
        async_result = AsyncHostResult(
            job_handle=handle.value,
            before_hook=mapping.before_hook,
            daemon_primitive=mapping.daemon_primitive,
        )
        payload["returns_job_handle"] = True
        payload["job_handle"] = handle.value.to_dict()

    envelope = WireEnvelope.try_create(
        v=v,
        type=mapping.verb,
        id=id,
        producer_id=producer_id,
        scope_path=path,
        payload=payload,
        correlation_id=correlation_id,
    )
    if not isinstance(envelope, Ok):
        return envelope
    return Ok(
        HostRequestEmission(
            envelope=envelope.value,
            mapping=mapping,
            async_result=async_result,
        )
    )


def host_request_type_family(wire_type: str) -> MessageFamily | None:
    """Return command/query family when ``wire_type`` is a host_request verb."""
    mapping = HOST_REQUEST_PRIMITIVE_MAP.get(wire_type)
    if mapping is None:
        return None
    return MessageFamily.COMMAND if mapping.wire_family == "command" else MessageFamily.QUERY


def example_host_request_payloads() -> tuple[Mapping[str, object], ...]:
    """Conformance examples preserving family, mapping, and typed-refusal shape."""
    return (
        MappingProxyType(
            {
                "family": "host_request",
                "verb": "subagent_spawn",
                "daemon_primitive": "subagent_spawn",
                "before_hook": "before_subagent_spawn",
                "wire_family": "command",
                "returns_job_handle": True,
                "args": {"prompt": "aggregate variants"},
                "job_handle": {
                    "job_id": "job:spawn-1",
                    "state": "queued",
                    "correlation_id": "corr-task-1",
                },
            }
        ),
        MappingProxyType(
            {
                "family": "host_request",
                "verb": "graph_transition",
                "daemon_primitive": "graph_transition",
                "before_hook": "before_graph_transition",
                "wire_family": "query",
                "args": {"node_id": "n-1"},
            }
        ),
        MappingProxyType(
            {
                "family": "host_request",
                "refusal": {
                    "variant": "UnknownHostRequest",
                    "verb": "invented_spawn",
                },
            }
        ),
    )
