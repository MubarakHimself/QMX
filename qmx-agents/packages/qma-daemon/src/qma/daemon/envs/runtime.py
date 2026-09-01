"""Dialogue Runtime and Analysis RLM Runtime (AD-14; FR-Q52).

Both implementations share the daemon-owned loop-and-state contract. Dialogue
serves every desk. RLM v1 is Analysis-desk only: a persistent Python interpreter
inside the worker Docker container, reaching the host over ``qma-wire``
``host_request``. Attachment is client state; the durable Session record carries
execution-model and autonomy only.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final

from qma.core.control.runtime import (
    ANALYSIS_NOTEBOOK_TOOL_ID,
    CLIENT_SESSION_AXIS,
    DEFERRED_RUNTIME_EXCLUSIONS,
    DIALOGUE_RUNTIME_DESKS,
    DURABLE_SESSION_AXES,
    HOSTED_NOTEBOOK_SERVICES,
    LOOP_AND_STATE_CONTRACT,
    LOOP_AND_STATE_SURFACES,
    RLM_DEPTH_CAP_REGISTRY_KEY,
    RLM_HOST_TRANSPORT,
    RLM_KERNEL_INTERPRETER,
    RLM_KERNEL_PLACEMENT,
    RLM_RUNTIME_DESK,
    available_execution_models,
    durable_session_payload,
    is_analysis_desk,
    mint_durable_session,
    parse_session_attachment,
    select_execution_model,
)
from qma.core.ontology import ActorId, DeskSlug, Quant, Session
from qma.core.plugins.hooks import HookSource
from qma.core.ports.tools import ToolKind, ToolRecord, default_rung_for_kind
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    ExecutionModel,
    SessionAttachment,
    SessionAutonomy,
)
from qma.daemon.envs.host_bridge import HostRequestAcceptance, HostRequestGateway
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.envs.registry import ExecutionEnvironmentRegistry
from qma.daemon.envs.router import ComputeRouter
from qma.daemon.hooks.registry import HookRegistry
from qma.daemon.journal.variables import GovernedVariableRegistry
from qma.daemon.tools.registry import ToolRegistry
from qmf.core import Ok, Result, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "DIALOGUE_RUNTIME",
    "RLM_RUNTIME",
    "ClientSessionAttachment",
    "RlmKernel",
    "RuntimeSelection",
    "RuntimeService",
]


_NOTEBOOK_SCHEMA: Final[Mapping[str, object]] = MappingProxyType(
    {
        "name": "analysis_notebook",
        "provider": "in-house",
        "worker": "analysis",
        "hosted": False,
    }
)


@dataclass(frozen=True, slots=True)
class RuntimeSelection:
    """One implementation of the shared loop-and-state contract."""

    execution_model: ExecutionModel
    desks: frozenset[str]
    kernel_placement: str | None = None
    kernel_interpreter: str | None = None
    host_transport: str | None = None
    contract: str = LOOP_AND_STATE_CONTRACT
    surfaces: tuple[str, ...] = LOOP_AND_STATE_SURFACES

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "execution_model": self.execution_model.value,
            "contract": self.contract,
            "surfaces": list(self.surfaces),
            "desks": sorted(self.desks),
        }
        if self.kernel_placement is not None:
            payload["kernel_placement"] = self.kernel_placement
        if self.kernel_interpreter is not None:
            payload["kernel_interpreter"] = self.kernel_interpreter
        if self.host_transport is not None:
            payload["host_transport"] = self.host_transport
        return MappingProxyType(payload)


DIALOGUE_RUNTIME: Final[RuntimeSelection] = RuntimeSelection(
    execution_model=ExecutionModel.DIALOGUE,
    desks=DIALOGUE_RUNTIME_DESKS,
)
RLM_RUNTIME: Final[RuntimeSelection] = RuntimeSelection(
    execution_model=ExecutionModel.RLM,
    desks=frozenset({RLM_RUNTIME_DESK.value}),
    kernel_placement=RLM_KERNEL_PLACEMENT,
    kernel_interpreter=RLM_KERNEL_INTERPRETER,
    host_transport=RLM_HOST_TRANSPORT,
)


@dataclass(frozen=True, slots=True)
class RlmKernel:
    """Persistent Python interpreter inside the Analysis worker container."""

    session_id: str
    worker_slot: str
    interpreter: str = RLM_KERNEL_INTERPRETER
    placement: str = RLM_KERNEL_PLACEMENT
    host_transport: str = RLM_HOST_TRANSPORT
    environment_kind: str = ExecutionEnvironmentKind.DOCKER.value
    in_daemon_process: bool = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "session_id": self.session_id,
                "worker_slot": self.worker_slot,
                "interpreter": self.interpreter,
                "placement": self.placement,
                "host_transport": self.host_transport,
                "environment_kind": self.environment_kind,
                "in_daemon_process": False,
            }
        )


@dataclass(frozen=True, slots=True)
class ClientSessionAttachment:
    """Client-only attachment. Never written to the durable Session store."""

    session_id: str
    state: SessionAttachment

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "session_id": self.session_id,
                CLIENT_SESSION_AXIS: self.state.value,
                "durable": False,
            }
        )


@dataclass
class RuntimeService:
    """Daemon façade for Dialogue / RLM selection, sessions, kernel, notebook."""

    def __init__(
        self,
        *,
        hooks: HookRegistry | None = None,
        jobs: JobHandleService | None = None,
        tools: ToolRegistry | None = None,
        variables: GovernedVariableRegistry | None = None,
        environments: ExecutionEnvironmentRegistry | None = None,
        router: ComputeRouter | None = None,
    ) -> None:
        self._hooks = hooks if hooks is not None else HookRegistry()
        self._jobs = jobs if jobs is not None else JobHandleService()
        self._tools = tools if tools is not None else ToolRegistry()
        self._variables = (
            variables if variables is not None else GovernedVariableRegistry.with_builtins()
        )
        self._environments = (
            environments if environments is not None else ExecutionEnvironmentRegistry()
        )
        self._router = (
            router if router is not None else ComputeRouter(environments=self._environments)
        )
        if jobs is None:
            self._jobs = JobHandleService(router=self._router)
        self._bridge = HostRequestGateway(
            hooks=self._hooks,
            jobs=self._jobs,
            variables=self._variables,
        )
        self._sessions: dict[str, Session] = {}
        self._attachments: dict[str, SessionAttachment] = {}
        self._kernels: dict[str, RlmKernel] = {}

    @property
    def contract(self) -> str:
        return LOOP_AND_STATE_CONTRACT

    @property
    def surfaces(self) -> tuple[str, ...]:
        return LOOP_AND_STATE_SURFACES

    @property
    def dialogue(self) -> RuntimeSelection:
        return DIALOGUE_RUNTIME

    @property
    def rlm(self) -> RuntimeSelection:
        return RLM_RUNTIME

    @property
    def depth_cap_key(self) -> str:
        return RLM_DEPTH_CAP_REGISTRY_KEY

    @property
    def hooks(self) -> HookRegistry:
        return self._hooks

    @property
    def jobs(self) -> JobHandleService:
        return self._jobs

    @property
    def tools(self) -> ToolRegistry:
        return self._tools

    @property
    def bridge(self) -> HostRequestGateway:
        return self._bridge

    @property
    def deferred_exclusions(self) -> Mapping[str, str]:
        return DEFERRED_RUNTIME_EXCLUSIONS

    def available_models(self, desk: object) -> frozenset[ExecutionModel]:
        return available_execution_models(desk)

    def select(
        self,
        desk: object,
        requested: object = None,
    ) -> Result[RuntimeSelection]:
        """Select Dialogue (every desk) or RLM (Analysis only). Same contract."""
        chosen = select_execution_model(desk, requested)
        if is_refusal(chosen):
            return chosen
        selected = DIALOGUE_RUNTIME if chosen.value is ExecutionModel.DIALOGUE else RLM_RUNTIME
        if (
            selected.contract != DIALOGUE_RUNTIME.contract
            or selected.surfaces != RLM_RUNTIME.surfaces
        ):
            return policy_rejection(
                "runtime",
                "Dialogue and RLM must share the daemon-owned loop-and-state contract",
            )
        return Ok(selected)

    def open_session(
        self,
        *,
        session_id: str,
        owner: ActorId | Quant | str,
        desk: object | None = None,
        requested_model: object = None,
        autonomy: object = SessionAutonomy.INTERACTIVE,
        attach_client: bool = True,
    ) -> Result[Session]:
        """Open a durable Session; attachment stays on the client."""
        resolved_desk: object
        if desk is not None:
            resolved_desk = desk
        elif isinstance(owner, Quant):
            resolved_desk = owner.desk
        else:
            return invalid_input("desk", "open_session requires a desk")
        selected = self.select(resolved_desk, requested_model)
        if is_refusal(selected):
            return selected
        minted = mint_durable_session(
            session_id=session_id,
            owner=owner,
            execution_model=selected.value.execution_model,
            autonomy=autonomy,
        )
        if is_refusal(minted):
            return minted
        before = self._hooks.dispatch(
            "before_session_start",
            payload={"session_id": session_id, "desk": _desk_token(resolved_desk)},
            source=HookSource.MISSION,
        )
        if is_refusal(before):
            return before
        session = minted.value
        self._sessions[session.id] = session
        if attach_client:
            self._attachments[session.id] = SessionAttachment.ATTACHED
        else:
            self._attachments[session.id] = SessionAttachment.DETACHED
        after = self._hooks.dispatch(
            "after_session_start",
            payload={"session_id": session.id},
            source=HookSource.MISSION,
        )
        if is_refusal(after):
            return after
        return Ok(session)

    def session(self, session_id: str) -> Session | None:
        return self._sessions.get(session_id)

    def client_attachment(self, session_id: str) -> ClientSessionAttachment | None:
        state = self._attachments.get(session_id)
        if state is None:
            return None
        return ClientSessionAttachment(session_id=session_id, state=state)

    def attach_client(self, session_id: str) -> Result[ClientSessionAttachment]:
        if session_id not in self._sessions:
            return invalid_input("session_id", "unknown Session", given=session_id)
        self._attachments[session_id] = SessionAttachment.ATTACHED
        return Ok(ClientSessionAttachment(session_id=session_id, state=SessionAttachment.ATTACHED))

    def detach_client(self, session_id: str) -> Result[ClientSessionAttachment]:
        """Detach is client state — the durable Session and work continue."""
        if session_id not in self._sessions:
            return invalid_input("session_id", "unknown Session", given=session_id)
        self._attachments[session_id] = SessionAttachment.DETACHED
        return Ok(ClientSessionAttachment(session_id=session_id, state=SessionAttachment.DETACHED))

    def persist_session(self, session_id: str) -> Result[Mapping[str, object]]:
        """Durable snapshot: execution-model and autonomy, never attachment."""
        session = self._sessions.get(session_id)
        if session is None:
            return invalid_input("session_id", "unknown Session", given=session_id)
        payload = durable_session_payload(session)
        if CLIENT_SESSION_AXIS in payload:
            return policy_rejection(
                "attachment",
                "durable Session snapshot must not carry attachment (AD-14)",
            )
        for axis in DURABLE_SESSION_AXES:
            if axis not in payload:
                return invalid_input("session", f"missing durable axis {axis}")
        return Ok(payload)

    def restore_session(self, payload: Mapping[str, object]) -> Result[Session]:
        """Reload a durable Session. Attachment in the payload is refused."""
        minted = mint_durable_session(
            session_id=payload.get("id"),
            owner=payload.get("owner"),
            execution_model=payload.get("execution_model"),
            autonomy=payload.get("autonomy"),
            payload=payload,
        )
        if is_refusal(minted):
            return minted
        self._sessions[minted.value.id] = minted.value
        # Closing a client is harmless: restore does not revive attachment.
        self._attachments.pop(minted.value.id, None)
        return Ok(minted.value)

    def start_rlm_kernel(
        self,
        *,
        session_id: str,
        task_id: str,
        in_daemon_process: bool = False,
        placement: str = RLM_KERNEL_PLACEMENT,
        environment_kind: object = ExecutionEnvironmentKind.DOCKER,
        measure_performance_envelope: bool = False,
        sandbox_vendor: str | None = None,
        browser_stack: str | None = None,
    ) -> Result[RlmKernel]:
        """Start the persistent Python interpreter in the worker container."""
        deferred = self._refuse_deferred(
            measure_performance_envelope=measure_performance_envelope,
            sandbox_vendor=sandbox_vendor,
            browser_stack=browser_stack,
            environment_kind=environment_kind,
        )
        if deferred is not None:
            return deferred
        if in_daemon_process:
            return policy_rejection(
                "rlm_kernel",
                "the RLM kernel is a persistent Python interpreter inside the "
                "worker's Docker container, never the daemon process (DEC-0303)",
                placement=RLM_KERNEL_PLACEMENT,
            )
        if placement != RLM_KERNEL_PLACEMENT:
            return policy_rejection(
                "rlm_kernel",
                "RLM kernel placement is the worker Docker container",
                given=placement,
                sanctioned=RLM_KERNEL_PLACEMENT,
            )
        session = self._sessions.get(session_id)
        if session is None:
            return invalid_input("session_id", "RLM kernel requires an open Session")
        if session.execution_model is not ExecutionModel.RLM:
            return policy_rejection(
                "execution_model",
                "RLM kernel starts only for an RLM Runtime session",
                execution_model=session.execution_model.value,
            )
        kind_token = (
            environment_kind.value
            if isinstance(environment_kind, ExecutionEnvironmentKind)
            else str(environment_kind)
        )
        if kind_token != ExecutionEnvironmentKind.DOCKER.value:
            return policy_rejection(
                "environment_kind",
                "the RLM kernel runs inside the worker's Docker container (AD-14)",
                given=repr(environment_kind),
            )
        placed = self._router.place_job(
            task_id=task_id,
            kind=ExecutionEnvironmentKind.DOCKER,
        )
        if is_refusal(placed):
            return placed
        if not placed.value.granted or placed.value.lease is None:
            return policy_rejection(
                "environment_lease",
                "RLM kernel start requires a granted docker environment_lease",
                task_id=task_id,
            )
        kernel = RlmKernel(
            session_id=session_id,
            worker_slot=placed.value.lease.slot_id,
            interpreter=RLM_KERNEL_INTERPRETER,
            placement=RLM_KERNEL_PLACEMENT,
            host_transport=RLM_HOST_TRANSPORT,
            environment_kind=ExecutionEnvironmentKind.DOCKER.value,
            in_daemon_process=False,
        )
        self._kernels[session_id] = kernel
        return Ok(kernel)

    def kernel_for(self, session_id: str) -> RlmKernel | None:
        return self._kernels.get(session_id)

    def accept_host_request(
        self,
        *,
        session_id: str,
        verb: object,
        scope_path: object,
        correlation_id: object,
        producer_id: object,
        id: object,
        v: object,
        owner: ActorId | Quant | str,
        args: object = None,
        transport: object = RLM_HOST_TRANSPORT,
        current_spawn_depth: object = 0,
        job_id: object = None,
        in_daemon_process: bool = False,
    ) -> Result[HostRequestAcceptance]:
        """Accept an RLM host call over qma-wire; never a second channel."""
        session = self._sessions.get(session_id)
        if session is None:
            return invalid_input("session_id", "host_request requires an open Session")
        if session.execution_model is not ExecutionModel.RLM:
            return policy_rejection(
                "execution_model",
                "host_request is the RLM kernel bridge; Dialogue Runtime does "
                "not issue host_request (AD-14)",
                execution_model=session.execution_model.value,
            )
        kernel = self._kernels.get(session_id)
        if kernel is None:
            return policy_rejection(
                "rlm_kernel",
                "host_request requires a started RLM kernel in the worker container",
                session_id=session_id,
            )
        return self._bridge.accept(
            verb=verb,
            scope_path=scope_path,
            correlation_id=correlation_id,
            producer_id=producer_id,
            id=id,
            v=v,
            owner=owner,
            args=args,
            transport=transport,
            current_spawn_depth=current_spawn_depth,
            job_id=job_id,
            in_daemon_process=in_daemon_process,
            kernel_placement=kernel.placement,
        )

    def register_analysis_notebook(
        self,
        *,
        provider: str | None = None,
    ) -> Result[str]:
        """In-house notebook Tool Registry entry on the Analysis worker."""
        if provider is not None:
            token = provider.strip().casefold().replace(" ", "_")
            if token in HOSTED_NOTEBOOK_SERVICES:
                return policy_rejection(
                    "notebook",
                    "the Analysis interactive notebook is provided in-house on "
                    "the Analysis worker and its RLM kernel; hosted notebook "
                    "services are refused (AD-14; DEC-0313)",
                    provider=provider,
                    in_house_tool=ANALYSIS_NOTEBOOK_TOOL_ID,
                )
        existing = self._tools.get(ANALYSIS_NOTEBOOK_TOOL_ID)
        if existing is not None:
            return Ok(existing.tool_id)
        record = ToolRecord(
            tool_id=ANALYSIS_NOTEBOOK_TOOL_ID,
            kind=ToolKind.NATIVE,
            capability_rung=default_rung_for_kind(ToolKind.NATIVE),
            schema=dict(_NOTEBOOK_SCHEMA),
            acts=frozenset({"notebook"}),
            tags=frozenset({"in-house", "analysis", "notebook"}),
            requires_environment_kind=ExecutionEnvironmentKind.DOCKER.value,
        )
        return self._tools.register_tool(record)

    def notebook_entry(self) -> ToolRecord | None:
        return self._tools.get(ANALYSIS_NOTEBOOK_TOOL_ID)

    def depth_cap(self) -> Result[int]:
        return self._bridge.depth_cap()

    def parse_attachment(self, value: object) -> Result[SessionAttachment]:
        return parse_session_attachment(value)

    def _refuse_deferred(
        self,
        *,
        measure_performance_envelope: bool,
        sandbox_vendor: str | None,
        browser_stack: str | None,
        environment_kind: object,
    ) -> Result[RlmKernel] | None:
        if measure_performance_envelope:
            return policy_rejection(
                "rlm_performance_envelope",
                DEFERRED_RUNTIME_EXCLUSIONS["GAP-0076"],
                gap="GAP-0076",
                gap_status="deferred",
            )
        if sandbox_vendor:
            return policy_rejection(
                "sandbox_vendor",
                DEFERRED_RUNTIME_EXCLUSIONS["GAP-0075"],
                gap="GAP-0075",
                gap_status="deferred",
                vendor=sandbox_vendor,
            )
        if browser_stack:
            return policy_rejection(
                "browser_stack",
                DEFERRED_RUNTIME_EXCLUSIONS["GAP-0078"],
                gap="GAP-0078",
                gap_status="deferred",
                stack=browser_stack,
            )
        kind_token = (
            environment_kind.value
            if isinstance(environment_kind, ExecutionEnvironmentKind)
            else environment_kind
        )
        if kind_token == ExecutionEnvironmentKind.REMOTE_CONTAINER.value:
            return policy_rejection(
                "environment_kind",
                DEFERRED_RUNTIME_EXCLUSIONS["GAP-0075"],
                gap="GAP-0075",
                gap_status="deferred",
                kind=kind_token,
            )
        if kind_token == ExecutionEnvironmentKind.BROWSER.value:
            return policy_rejection(
                "environment_kind",
                DEFERRED_RUNTIME_EXCLUSIONS["GAP-0078"],
                gap="GAP-0078",
                gap_status="deferred",
                kind=kind_token,
            )
        return None


def _desk_token(desk: object) -> str:
    if isinstance(desk, DeskSlug):
        return desk.value
    if is_analysis_desk(desk) and isinstance(desk, str):
        return desk
    if isinstance(desk, str):
        return desk
    return repr(desk)
