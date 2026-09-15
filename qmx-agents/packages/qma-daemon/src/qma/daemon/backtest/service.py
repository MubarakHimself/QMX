"""Backtesting Service — analysis-backtest plugin daemon half (CT-47; FR-Q55).

Agent → QMA backtest tool → this service → ``qmb`` CLI/MCP door → QMB.
Places exactly one ``qmb`` job per ExecutionEnvironment. Holds no scheduling
authority, no parallelism, and no durable backtest state. QMB keeps those.
The door is a runtime interaction: this module never imports the ``qmb``
package and never places the compute leg through the Compute Router.
Production placement is ``CliQmbDoorTransport``. ``RecordingQmbDoorTransport``
records without spawning and is not a working integration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

from qma.core.ontology import ActorId
from qma.core.ports.cancel_authority import (
    COORDINATED_CANCEL_AUTHORITY,
    RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT,
    is_unauthorized_cancel_writer,
    refuse_unauthorized_cancel,
)
from qma.core.ports.experiments import (
    EXPERIMENT_LEDGER_WORKBENCH_LANE,
    QMB_LEDGER_WORKBENCH_LANE,
    coordinated_run_labels,
    refuse_caller_declared_lane_fields,
)
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
from qma.daemon.backtest.cli import CliQmbDoorTransport
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.envs.registry import ExecutionEnvironmentRegistry
from qma.daemon.experiments.service import ExperimentSpecService
from qma.daemon.plugins.context import DaemonPluginContext, PluginContextError
from qma.daemon.taskgraph.records import DispatchLease
from qma.daemon.tools.registry import ToolRegistry
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "BacktestingService",
    "CliQmbDoorTransport",
    "QmbPlacement",
    "RecordingQmbDoorTransport",
]


def _job_id_for(request: QmbBacktestRequest) -> str:
    return f"qmb:{request.occupancy_key}:{request.task_id}"


@dataclass
class RecordingQmbDoorTransport:
    """Non-production recorder. Does not spawn ``qmb`` and is not the working door.

    Tests that claim the QMA→QMB door works must spawn ``qmb`` or the documented
    CLI test double via ``CliQmbDoorTransport``. ``JobHandle.cancel`` still
    enters ``cancelled`` on the QMA handle; mapping that cancel onto a live
    ``qmb`` abort is Story 36.5.
    """

    production: Literal[False] = False
    spawns_qmb_process: Literal[False] = False
    maps_cancel_to_qmb_abort: Literal[False] = RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT
    _invocations: list[QmbDoorInvocation] = field(default_factory=list[QmbDoorInvocation])
    _abort_invocations: list[str] = field(default_factory=list[str])

    @property
    def invocations(self) -> tuple[QmbDoorInvocation, ...]:
        return tuple(self._invocations)

    @property
    def abort_invocations(self) -> tuple[str, ...]:
        return tuple(self._abort_invocations)

    def abort(self, job_id: str) -> Result[None]:
        """Live qmb abort is Epic 36. Recording door records nothing."""
        return policy_rejection(
            "qmb_abort",
            "mapping JobHandle.cancel onto a live qmb abort is Epic 36, "
            "not Story 32.2 (AR-W04; FR-W08)",
            job_id=job_id,
            transport="RecordingQmbDoorTransport",
            maps_cancel_to_qmb_abort=self.maps_cancel_to_qmb_abort,
        )

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
    qmb_ledger_workbench_lane: str = QMB_LEDGER_WORKBENCH_LANE
    experiment_ledger_workbench_lane: str = EXPERIMENT_LEDGER_WORKBENCH_LANE

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
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
            "qmb_ledger_workbench_lane": self.qmb_ledger_workbench_lane,
            "experiment_ledger_workbench_lane": self.experiment_ledger_workbench_lane,
            "request": dict(self.request.to_payload()),
            "receipt": dict(self.receipt.to_payload()),
            "labels": dict(coordinated_run_labels()),
        }
        return MappingProxyType(payload)


class BacktestingService:
    """``analysis-backtest`` daemon half: one Tool Registry entry, one ``qmb`` door."""

    def __init__(
        self,
        *,
        tools: ToolRegistry | None = None,
        jobs: JobHandleService | None = None,
        environments: ExecutionEnvironmentRegistry | None = None,
        transport: QmbDoorTransport | None = None,
        experiments: ExperimentSpecService | None = None,
    ) -> None:
        self._jobs = jobs if jobs is not None else JobHandleService()
        self._tools = tools if tools is not None else ToolRegistry()
        self._environments = (
            environments if environments is not None else self._jobs.router.environments
        )
        self._transport: QmbDoorTransport = (
            transport if transport is not None else CliQmbDoorTransport()
        )
        self._experiments = experiments
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
    def experiments(self) -> ExperimentSpecService | None:
        return self._experiments

    def bind_experiments(self, experiments: ExperimentSpecService) -> None:
        """Attach ExperimentSpec product truth for coordinated placement."""
        self._experiments = experiments

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
        dispatch_lease: DispatchLease | None = None,
        model_deployment_ref: object = None,
        qmb_ledger_ref: object = None,
        ct32_ref: object = None,
        analysis_method: object = None,
        lane: object = None,
        workbench_lane: object = None,
    ) -> Result[QmbPlacement]:
        """Agent → QMA backtest tool → Backtesting Service."""
        if tool_id != QMB_BACKTEST_TOOL_ID:
            return invalid_input(
                "tool_id",
                "the Backtesting Service exposes one Tool Registry entry "
                f"{QMB_BACKTEST_TOOL_ID} (CT-47; FR-Q55)",
                given=tool_id,
            )
        declared = refuse_caller_declared_lane_fields(
            extra,
            analysis_method=analysis_method,
            lane=lane,
            workbench_lane=workbench_lane,
        )
        if declared is not None:
            return declared
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
            analysis_method=analysis_method,
            lane=lane,
            workbench_lane=workbench_lane,
        )
        if is_refusal(parsed):
            return parsed
        return self.submit(
            parsed.value,
            dispatch_lease=dispatch_lease,
            model_deployment_ref=model_deployment_ref,
            qmb_ledger_ref=qmb_ledger_ref,
            ct32_ref=ct32_ref,
        )

    def submit(
        self,
        request: QmbBacktestRequest,
        *,
        dispatch_lease: DispatchLease | None = None,
        model_deployment_ref: object = None,
        qmb_ledger_ref: object = None,
        ct32_ref: object = None,
    ) -> Result[QmbPlacement]:
        """Place one ``qmb`` job in an eligible environment through the QMB door."""
        if self._experiments is not None:
            resolved = self._experiments.resolve(request.experiment_spec_fp1)
            if is_refusal(resolved):
                return invalid_input(
                    "experiment_spec_fp1",
                    "coordinated placement requires a registered ExperimentSpec "
                    "(FR-W06; DEC-0270)",
                    spec_fp1=request.experiment_spec_fp1,
                )
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
        if self._experiments is not None and dispatch_lease is not None:
            recorded = self._experiments.record_coordinated_run(
                spec_fp1=request.experiment_spec_fp1,
                dispatch_lease=dispatch_lease,
                model_deployment_ref=model_deployment_ref,
                qmb_ledger_ref=qmb_ledger_ref,
                ct32_ref=ct32_ref,
            )
            if is_refusal(recorded):
                return recorded
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
        completed = self._jobs.complete(job_id, state, writer="qmb_outcome")
        if is_refusal(completed):
            return completed
        self._release_terminal()
        return completed

    def cancel(
        self,
        job_id: str,
        *,
        writer: str = COORDINATED_CANCEL_AUTHORITY,
    ) -> Result[JobHandle]:
        """JobHandle.cancel only. Live qmb abort mapping is Story 36.5."""
        cancelled = self._jobs.cancel(job_id, writer=writer)
        if is_refusal(cancelled):
            return cancelled
        self._release_terminal()
        return cancelled

    @property
    def maps_cancel_to_qmb_abort(self) -> bool:
        return bool(getattr(self._transport, "maps_cancel_to_qmb_abort", False))

    def import_qmb_package(self) -> Result[None]:
        """There is no import edge. Calling this is always a policy rejection."""
        return refuse_qmb_import_edge()

    def set_parallelism(self, workers: int) -> Result[None]:
        _ = workers
        return refuse_qmb_owned_concern(concern="intra_node_parallelism")

    def append_run_ledger(
        self,
        entry: Mapping[str, object],
        *,
        writer: str = "daemon",
    ) -> Result[None]:
        if is_unauthorized_cancel_writer(writer):
            return refuse_unauthorized_cancel(writer=writer, surface="qmb_ledger")
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
