"""Backtesting Service — analysis-backtest plugin daemon half (CT-47; FR-Q55).

Agent → QMA backtest tool → this service → ``qmb`` CLI/MCP door → QMB.
Places exactly one ``qmb`` job per ExecutionEnvironment. Holds no scheduling
authority, no parallelism, and no durable backtest state. QMB keeps those.
The door is a runtime interaction: this module never imports the ``qmb``
package and never places the compute leg through the Compute Router.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from qma.core.ontology import ActorId
from qma.core.ports.jobs import JobHandle
from qma.core.ports.qmb import (
    ANALYSIS_BACKTEST_PLUGIN_ID,
    QMB_BACKTEST_TOOL_ID,
    QMB_BACKTEST_TOOL_LOCAL_ID,
    QMB_CLI_PROGRAM,
    QMB_OWNED_CONCERNS,
    QMB_ROUTE,
    QMB_WORLD_REPLAY,
    QmbBacktestRequest,
    QmbDoorInvocation,
    QmbDoorKind,
    QmbDoorReceipt,
    QmbDoorTransport,
    admit_qmb_job,
    build_qmb_door_invocation,
    environment_kind_from_ref,
    parse_qmb_backtest_request,
    qmb_backtest_tool_record,
    refuse_qmb_import_edge,
    refuse_qmb_owned_concern,
    release_qmb_job,
)
from qma.core.ports.tools import ToolKind, ToolRecord
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import JobHandleState
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.envs.registry import ExecutionEnvironmentRegistry
from qma.daemon.plugins.context import DaemonPluginContext, PluginContextError
from qma.daemon.tools.registry import ToolRegistry
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "BacktestingService",
    "QmbPlacement",
    "RecordingQmbDoorTransport",
]


def _job_id_for(request: QmbBacktestRequest) -> str:
    return f"qmb:{request.occupancy_key}:{request.task_id}"


@dataclass
class RecordingQmbDoorTransport:
    """Runtime QMB door. Records CLI/MCP invocations and never imports ``qmb``."""

    _invocations: list[QmbDoorInvocation] = field(default_factory=list[QmbDoorInvocation])

    @property
    def invocations(self) -> tuple[QmbDoorInvocation, ...]:
        return tuple(self._invocations)

    def submit(self, invocation: QmbDoorInvocation) -> Result[QmbDoorReceipt]:
        if invocation.import_edge or invocation.program != QMB_CLI_PROGRAM:
            return refuse_qmb_import_edge(given=invocation.program)
        payload = dict(invocation.payload)
        if payload.get("import_edge") is True:
            return refuse_qmb_import_edge()
        job_id = payload.get("job_id")
        environment_ref = payload.get("environment_ref")
        occupancy_key = payload.get("occupancy_key")
        if not isinstance(job_id, str) or not job_id:
            return invalid_input("job_id", "QMB door invocation requires a job id")
        if not isinstance(environment_ref, str) or not environment_ref:
            return invalid_input("environment_ref", "QMB door invocation requires environment_ref")
        if not isinstance(occupancy_key, str) or not occupancy_key:
            occupancy_key = environment_ref
        self._invocations.append(invocation)
        return Ok(
            QmbDoorReceipt(
                job_id=job_id,
                environment_ref=environment_ref,
                occupancy_key=occupancy_key,
                door=invocation.kind,
                program=invocation.program,
                argv=invocation.argv,
                world=QMB_WORLD_REPLAY,
                route=QMB_ROUTE,
                import_edge=False,
            )
        )


@dataclass(frozen=True, slots=True)
class QmbPlacement:
    """One placed ``qmb`` job: QMA JobHandle plus the runtime door receipt."""

    handle: JobHandle
    request: QmbBacktestRequest
    invocation: QmbDoorInvocation
    receipt: QmbDoorReceipt
    tool_id: str = QMB_BACKTEST_TOOL_ID
    plugin_id: str = ANALYSIS_BACKTEST_PLUGIN_ID
    route: tuple[str, ...] = QMB_ROUTE

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "job_id": self.handle.job_id,
                "state": self.handle.state.value,
                "tool_id": self.tool_id,
                "plugin_id": self.plugin_id,
                "route": list(self.route),
                "occupancy_key": self.request.occupancy_key,
                "environment_ref": self.request.environment_ref,
                "world": self.request.world,
                "door": self.request.door.value,
                "program": self.invocation.program,
                "argv": list(self.invocation.argv),
                "import_edge": False,
                "compute_router_used": False,
                "qma_re_specifies": False,
                "request": dict(self.request.to_payload()),
                "receipt": dict(self.receipt.to_payload()),
            }
        )


class BacktestingService:
    """``analysis-backtest`` daemon half: one Tool Registry entry, one ``qmb`` door."""

    def __init__(
        self,
        *,
        tools: ToolRegistry | None = None,
        jobs: JobHandleService | None = None,
        environments: ExecutionEnvironmentRegistry | None = None,
        transport: QmbDoorTransport | None = None,
    ) -> None:
        self._jobs = jobs if jobs is not None else JobHandleService()
        self._tools = tools if tools is not None else ToolRegistry()
        self._environments = (
            environments if environments is not None else self._jobs.router.environments
        )
        self._transport: QmbDoorTransport = (
            transport if transport is not None else RecordingQmbDoorTransport()
        )
        self._occupancy: dict[str, str] = {}

    @property
    def plugin_id(self) -> str:
        return ANALYSIS_BACKTEST_PLUGIN_ID

    @property
    def tool_id(self) -> str:
        return QMB_BACKTEST_TOOL_ID

    @property
    def route(self) -> tuple[str, ...]:
        return QMB_ROUTE

    @property
    def tools(self) -> ToolRegistry:
        return self._tools

    @property
    def jobs(self) -> JobHandleService:
        return self._jobs

    @property
    def environments(self) -> ExecutionEnvironmentRegistry:
        return self._environments

    @property
    def transport(self) -> QmbDoorTransport:
        return self._transport

    @property
    def scheduling_authority(self) -> None:
        return None

    @property
    def parallelism(self) -> None:
        return None

    @property
    def backtest_state(self) -> None:
        return None

    def catalog_backtest_tools(self) -> tuple[ToolRecord, ...]:
        return tuple(tool for tool in self._tools.catalog() if tool.kind is ToolKind.BACKTEST)

    def install(
        self,
        *,
        context: DaemonPluginContext | None = None,
    ) -> Result[ToolRecord]:
        """Register the one analysis-backtest Tool Registry entry."""
        if context is not None and context.plugin_id != ANALYSIS_BACKTEST_PLUGIN_ID:
            return invalid_input(
                "plugin_id",
                "the Backtesting Service is the analysis-backtest plugin's daemon half",
                given=context.plugin_id,
            )
        existing = self._tools.get(QMB_BACKTEST_TOOL_ID)
        if existing is not None:
            if (
                existing.kind is ToolKind.BACKTEST
                and existing.plugin_id == ANALYSIS_BACKTEST_PLUGIN_ID
            ):
                return Ok(existing)
            return invalid_input(
                "tool_id",
                "analysis-backtest already has a non-door tool at the QMB id",
                given=QMB_BACKTEST_TOOL_ID,
            )
        record = qmb_backtest_tool_record()
        registered = self._tools.register_tool(record)
        if is_refusal(registered):
            return registered
        if context is not None:
            snap = context.snapshot()
            already = ("tool", QMB_BACKTEST_TOOL_ID) in snap["multis"]
            if not already:
                try:
                    context.register_tool(
                        QMB_BACKTEST_TOOL_LOCAL_ID,
                        {
                            **dict(record.schema),
                            "name": QMB_BACKTEST_TOOL_LOCAL_ID,
                            "acts": tuple(sorted(record.acts)),
                        },
                    )
                except PluginContextError as exc:
                    return invalid_input("tool", str(exc), plugin_id=ANALYSIS_BACKTEST_PLUGIN_ID)
        return Ok(record)

    def invoke(
        self,
        tool_id: str,
        *,
        owner: ActorId | str,
        task_id: str,
        environment_ref: str,
        experiment_spec_fp1: str,
        evidence_ref: str,
        world: str = QMB_WORLD_REPLAY,
        door: QmbDoorKind | str = QmbDoorKind.CLI,
        extra: Mapping[str, object] | None = None,
    ) -> Result[QmbPlacement]:
        """Agent → QMA backtest tool → Backtesting Service."""
        if tool_id != QMB_BACKTEST_TOOL_ID:
            return invalid_input(
                "tool_id",
                "the Backtesting Service exposes one Tool Registry entry "
                f"{QMB_BACKTEST_TOOL_ID} (CT-47; FR-Q55)",
                given=tool_id,
            )
        parsed = parse_qmb_backtest_request(
            owner=owner,
            task_id=task_id,
            environment_ref=environment_ref,
            experiment_spec_fp1=experiment_spec_fp1,
            evidence_ref=evidence_ref,
            world=world,
            door=door,
            tool_id=tool_id,
            extra=extra,
        )
        if is_refusal(parsed):
            return parsed
        return self.submit(parsed.value)

    def submit(self, request: QmbBacktestRequest) -> Result[QmbPlacement]:
        """Place one ``qmb`` job in an eligible environment through the QMB door."""
        if self._tools.get(QMB_BACKTEST_TOOL_ID) is None:
            installed = self.install()
            if is_refusal(installed):
                return installed
        self._release_terminal()
        kind = request.occupancy_key
        if self._environments.get(kind) is None and self._environments.declaration(kind) is None:
            return NoEnvironment.of(kind=kind, reason="kind_unbound")
        admitted = admit_qmb_job(
            self._occupancy,
            occupancy_key=kind,
            job_id=_job_id_for(request),
        )
        if is_refusal(admitted):
            return admitted
        job_id = _job_id_for(request)
        minted = self._jobs.submit(
            owner=request.owner,
            task_id=request.task_id,
            job_id=job_id,
        )
        if is_refusal(minted):
            return minted
        if self._jobs.router.lease_for(request.task_id) is not None:
            return policy_rejection(
                "compute_router",
                "the Backtesting Service's compute leg is QMB's own, not QMA's "
                "Compute Router (CT-47; DEC-0316; FR-Q55)",
                task_id=request.task_id,
            )
        invocation = build_qmb_door_invocation(request, job_id=minted.value.job_id)
        if is_refusal(invocation):
            self._occupancy = release_qmb_job(
                admitted.value,
                occupancy_key=kind,
                job_id=job_id,
            )
            return invocation
        receipt = self._transport.submit(invocation.value)
        if is_refusal(receipt):
            self._occupancy = release_qmb_job(
                admitted.value,
                occupancy_key=kind,
                job_id=job_id,
            )
            return receipt
        self._occupancy = admitted.value
        return Ok(
            QmbPlacement(
                handle=minted.value,
                request=request,
                invocation=invocation.value,
                receipt=receipt.value,
            )
        )

    def occupying_job(self, environment_ref: str) -> str | None:
        parsed = environment_kind_from_ref(environment_ref)
        key = parsed.value if is_ok(parsed) else environment_ref
        self._release_terminal()
        return self._occupancy.get(key)

    def observe_outcome(
        self,
        job_id: str,
        state: JobHandleState | str,
    ) -> Result[JobHandle]:
        """Record a known QMB-owned outcome onto the QMA JobHandle and free occupancy."""
        handle = self._jobs.handle_for(job_id)
        if handle is None:
            return invalid_input("job_id", "unknown qmb job", given=job_id)
        if handle.state is JobHandleState.QUEUED:
            started = self._jobs.start(job_id)
            if is_refusal(started):
                return started
        completed = self._jobs.complete(job_id, state)
        if is_refusal(completed):
            return completed
        self._release_terminal()
        return completed

    def import_qmb_package(self) -> Result[None]:
        """There is no import edge. Calling this is always a policy rejection."""
        return refuse_qmb_import_edge()

    def set_parallelism(self, workers: int) -> Result[None]:
        _ = workers
        return refuse_qmb_owned_concern(concern="intra_node_parallelism")

    def append_run_ledger(self, entry: Mapping[str, object]) -> Result[None]:
        _ = entry
        return refuse_qmb_owned_concern(concern="run_ledger")

    def store_artifact(self, artifact: Mapping[str, object]) -> Result[None]:
        _ = artifact
        return refuse_qmb_owned_concern(concern="artifact_contract")

    def qmb_owned_concerns(self) -> frozenset[str]:
        return QMB_OWNED_CONCERNS

    def _release_terminal(self) -> None:
        remaining: dict[str, str] = {}
        for key, job_id in self._occupancy.items():
            handle = self._jobs.handle_for(job_id)
            if handle is None or not handle.is_terminal:
                remaining[key] = job_id
        self._occupancy = remaining
