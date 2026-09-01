"""Daemon-side RLM ``host_request`` acceptor (AD-14; FR-Q52).

The RLM kernel reaches the host only through the typed ``qma-wire``
``host_request`` family. Each verb maps to one daemon-owned primitive and
runs that primitive's ``before_*`` hook. Unmapped verbs return
``UnknownHostRequest``. Async spawn returns a durable ``JobHandle`` under
``registry:rlm.depth_cap``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qma.core.control.runtime import (
    DEFERRED_RUNTIME_EXCLUSIONS,
    RLM_DEPTH_CAP_REGISTRY_KEY,
    RLM_HOST_TRANSPORT,
    RLM_KERNEL_PLACEMENT,
)
from qma.core.ontology import ActorId, Quant
from qma.core.plugins.hooks import HookResult, HookSource
from qma.core.ports.jobs import JobHandle
from qma.core.vocabulary.enums import HookResultDecision, JobHandleState
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.journal.variables import GovernedVariableRegistry
from qma.wire.envelope import parse_scope_path
from qma.wire.host_request import (
    HOST_REQUEST_BRIDGE_TRANSPORT,
    HostRequestEmission,
    assert_no_alternate_rlm_transport,
    emit_host_request,
    enforce_spawn_depth,
    resolve_host_request,
)
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "BLOCKING_BEFORE_DECISIONS",
    "HostRequestAcceptance",
    "HostRequestGateway",
]


BLOCKING_BEFORE_DECISIONS: Final[frozenset[HookResultDecision]] = frozenset(
    {
        HookResultDecision.DENY,
        HookResultDecision.DEFER,
        HookResultDecision.ASK,
        HookResultDecision.BLOCK_STOP,
    }
)


def _parse_owner(owner: ActorId | Quant | str) -> Result[ActorId]:
    if isinstance(owner, ActorId):
        return Ok(owner)
    if isinstance(owner, Quant):
        return Ok(owner.actor_id)
    return ActorId.try_create(owner)


def _task_id_from_scope(scope_path: object) -> Result[str]:
    try:
        path = parse_scope_path(scope_path)
    except ValueError as exc:
        return invalid_input("scope_path", str(exc))
    for segment in path:
        if segment.kind == "task":
            return Ok(segment.id)
    return invalid_input(
        "scope_path",
        "host_request scope_path must include the Task segment (AD-14)",
    )


@dataclass(frozen=True, slots=True)
class HostRequestAcceptance:
    """Daemon outcome of one RLM host call over qma-wire."""

    emission: HostRequestEmission
    before_result: HookResult
    job_handle: JobHandle | None = None
    kernel_placement: str = RLM_KERNEL_PLACEMENT
    host_transport: str = RLM_HOST_TRANSPORT

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "verb": self.emission.mapping.verb,
            "daemon_primitive": self.emission.mapping.daemon_primitive,
            "before_hook": self.emission.mapping.before_hook,
            "before_decision": self.before_result.decision.value,
            "host_transport": self.host_transport,
            "kernel_placement": self.kernel_placement,
            "channel": "qma-wire",
        }
        if self.job_handle is not None:
            payload["job_handle"] = dict(self.job_handle.to_payload())
        return MappingProxyType(payload)


class HostRequestGateway:
    """Accept RLM kernel host calls as qma-wire commands/queries (FR-Q52)."""

    def __init__(
        self,
        *,
        hooks: HookRegistry | None = None,
        jobs: JobHandleService | None = None,
        variables: GovernedVariableRegistry | None = None,
    ) -> None:
        self._hooks = hooks if hooks is not None else HookRegistry()
        self._jobs = jobs if jobs is not None else JobHandleService()
        self._variables = (
            variables if variables is not None else GovernedVariableRegistry.with_builtins()
        )

    @property
    def hooks(self) -> HookRegistry:
        return self._hooks

    @property
    def jobs(self) -> JobHandleService:
        return self._jobs

    @property
    def depth_cap_key(self) -> str:
        return RLM_DEPTH_CAP_REGISTRY_KEY

    def depth_cap(self) -> Result[int]:
        """Read ``registry:rlm.depth_cap``; never copy a spine constant."""
        raw = self._variables.get_value("rlm.depth_cap")
        if is_refusal(raw):
            return raw
        value = raw.value
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            return invalid_input(
                "depth_cap",
                "registry:rlm.depth_cap must be a non-negative int",
                registry_key=RLM_DEPTH_CAP_REGISTRY_KEY,
                given=repr(value),
            )
        return Ok(value)

    def accept(
        self,
        *,
        verb: object,
        scope_path: object,
        correlation_id: object,
        producer_id: object,
        id: object,
        v: object,
        owner: ActorId | Quant | str,
        args: object = None,
        transport: object = HOST_REQUEST_BRIDGE_TRANSPORT,
        current_spawn_depth: object = 0,
        job_id: object = None,
        job_state: object = JobHandleState.QUEUED.value,
        in_daemon_process: bool = False,
        kernel_placement: str = RLM_KERNEL_PLACEMENT,
    ) -> Result[HostRequestAcceptance]:
        """Admit one RLM host call onto the daemon-owned primitive.

        The kernel is not in the daemon process. Alternate transports and
        unmapped verbs are refused. Depth above the registered cap cites
        deferred GAP-0080 rather than raising the cap.
        """
        if in_daemon_process:
            return policy_rejection(
                "rlm_kernel",
                "the RLM kernel is a persistent Python interpreter inside the "
                "worker's Docker container, never the daemon process (DEC-0303)",
                placement=RLM_KERNEL_PLACEMENT,
            )
        if kernel_placement != RLM_KERNEL_PLACEMENT:
            return policy_rejection(
                "rlm_kernel",
                "RLM kernel placement is the worker Docker container (AD-14)",
                given=kernel_placement,
                sanctioned=RLM_KERNEL_PLACEMENT,
            )
        transport_check = assert_no_alternate_rlm_transport(transport)
        if is_refusal(transport_check):
            return transport_check

        resolved = resolve_host_request(verb)
        if is_refusal(resolved):
            return resolved
        mapping = resolved.value

        cap = self.depth_cap()
        if is_refusal(cap):
            return cap
        if mapping.returns_job_handle:
            depth = enforce_spawn_depth(current_spawn_depth, depth_cap=cap.value)
            if is_refusal(depth):
                return policy_rejection(
                    "spawn_depth",
                    "RLM spawn depth exceeds registry:rlm.depth_cap; raising "
                    "the cap is deferred (GAP-0080)",
                    current_depth=current_spawn_depth,
                    depth_cap=cap.value,
                    registry_key=RLM_DEPTH_CAP_REGISTRY_KEY,
                    gap="GAP-0080",
                    gap_status=DEFERRED_RUNTIME_EXCLUSIONS["GAP-0080"],
                )

        emission = emit_host_request(
            verb=verb,
            scope_path=scope_path,
            correlation_id=correlation_id,
            producer_id=producer_id,
            id=id,
            v=v,
            args=args,
            transport=transport,
            current_spawn_depth=current_spawn_depth,
            depth_cap=cap.value,
            job_id=job_id,
            job_state=job_state,
        )
        if is_refusal(emission):
            return emission

        before = self._hooks.dispatch(
            mapping.before_hook,
            payload={
                "family": "host_request",
                "verb": mapping.verb,
                "daemon_primitive": mapping.daemon_primitive,
            },
            source=HookSource.PLUGIN,
            correlation_id=correlation_id if isinstance(correlation_id, str) else None,
        )
        if is_refusal(before):
            return before
        if before.value.decision in BLOCKING_BEFORE_DECISIONS:
            return policy_rejection(
                "before_hook",
                "host_request primitive before_* hook blocked the call (AD-10, AD-14)",
                verb=mapping.verb,
                before_hook=mapping.before_hook,
                decision=before.value.decision.value,
            )

        handle: JobHandle | None = None
        if mapping.returns_job_handle:
            parsed_owner = _parse_owner(owner)
            if is_refusal(parsed_owner):
                return parsed_owner
            task = _task_id_from_scope(scope_path)
            if is_refusal(task):
                return task
            async_result = emission.value.async_result
            durable_id = (
                async_result.job_handle.job_id
                if async_result is not None
                else (job_id if isinstance(job_id, str) else f"job:{id}")
            )
            submitted = self._jobs.submit(
                owner=parsed_owner.value,
                task_id=task.value,
                job_id=durable_id,
                correlation_id=correlation_id if isinstance(correlation_id, str) else "",
            )
            if is_refusal(submitted):
                return submitted
            handle = submitted.value

        return Ok(
            HostRequestAcceptance(
                emission=emission.value,
                before_result=before.value,
                job_handle=handle,
            )
        )
