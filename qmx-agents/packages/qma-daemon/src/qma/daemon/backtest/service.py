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

import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Literal, cast

from qma.core.ontology import ActorId
from qma.core.ports.cancel_authority import (
    COORDINATED_CANCEL_AUTHORITY,
    RECORDING_DOOR_MAPS_CANCEL_TO_QMB_ABORT,
    authorize_qmb_ledger_aborted_writer,
    is_unauthorized_cancel_writer,
    refuse_unauthorized_cancel,
)
from qma.core.ports.experiments import (
    ANALYSIS_PUBLISHED_KIND,
    EXPERIMENT_LEDGER_WORKBENCH_LANE,
    QMB_LEDGER_WORKBENCH_LANE,
    coordinated_run_labels,
    refuse_caller_declared_lane_fields,
)
from qma.core.ports.jobs import JobHandle
from qma.core.ports.qmb import (
    ANALYSIS_BACKTEST_PLUGIN_ID,
    QMB_ABORTED_LEDGER_STATE,
    QMB_BACKTEST_TOOL_ID,
    QMB_BACKTEST_TOOL_LOCAL_ID,
    QMB_CLI_PROGRAM,
    QMB_OCCUPANCY_QUERY,
    QMB_OCCUPANCY_RUN,
    QMB_OPENS_DAEMON_SQLITE,
    QMB_OWNED_CONCERNS,
    QMB_PROCESS_PER_RUN_CHILD,
    QMB_ROUTE,
    QMB_WORLD_REPLAY,
    QmbAbortReceipt,
    QmbBacktestRequest,
    QmbDoorInvocation,
    QmbDoorKind,
    QmbDoorReceipt,
    QmbDoorTransport,
    admit_qmb_job,
    build_qmb_door_invocation,
    build_qmb_query_invocation,
    classify_qmb_door_occupancy,
    environment_kind_from_ref,
    occupancy_from_invocation,
    parse_qmb_backtest_request,
    qmb_backtest_tool_record,
    qmb_opens_daemon_sqlite,
    refuse_qmb_import_edge,
    refuse_qmb_owned_concern,
    refuse_query_ct32_or_successor,
    release_qmb_job,
)
from qma.core.ports.tools import ToolKind, ToolRecord
from qma.core.refusals import NoEnvironment
from qma.core.vocabulary.enums import JobHandleState
from qma.daemon.backtest.cli import CliQmbDoorTransport
from qma.daemon.envs.jobs import JobHandleService
from qma.daemon.envs.registry import ExecutionEnvironmentRegistry
from qma.daemon.experiments.service import ExperimentSpecService, PublishedProjection
from qma.daemon.plugins.context import DaemonPluginContext, PluginContextError
from qma.daemon.taskgraph.records import DispatchLease
from qma.daemon.tools.registry import ToolRegistry
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "BacktestingService",
    "CliQmbDoorTransport",
    "QmbPlacement",
    "QmbQueryPlacement",
    "RecordingQmbDoorTransport",
]


def _job_id_for(request: QmbBacktestRequest) -> str:
    return f"qmb:{request.occupancy_key}:{request.task_id}"


def _projection_view_from_stdout(
    stdout: str,
    extra: Mapping[str, object] | None,
) -> Result[dict[str, object]]:
    raw = stdout.strip()
    if not raw and extra is not None:
        candidate = extra.get("view")
        if isinstance(candidate, Mapping):
            mapping = cast("Mapping[object, object]", candidate)
            raw = json.dumps(
                {str(key): value for key, value in mapping.items()},
                separators=(",", ":"),
            )
    if not raw:
        return invalid_input(
            "stdout",
            "coordinated analysis.project waits for canonical saved-view JSON (FR-W24; Story 35.1)",
        )
    try:
        parsed_obj: object = json.loads(raw)
    except json.JSONDecodeError as exc:
        return invalid_input("stdout", "projection JSON is not parseable", error=str(exc))
    if not isinstance(parsed_obj, dict):
        return invalid_input("stdout", "projection JSON is an object")
    mapping = cast("dict[object, object]", parsed_obj)
    view: dict[str, object] = {str(key): value for key, value in mapping.items()}
    if view.get("method") != "projection":
        return invalid_input(
            "method",
            "a projection saved view has method=projection (FR-W24; DEC-0273)",
            given=repr(view.get("method")),
        )
    return Ok(view)


@dataclass
class RecordingQmbDoorTransport:
    """Non-production recorder. Does not spawn ``qmb`` and is not the working door.

    Tests that claim the QMA→QMB door works must spawn ``qmb`` or the documented
    CLI test double via ``CliQmbDoorTransport``. ``JobHandle.cancel`` still
    enters ``cancelled`` on the QMA handle. This recorder does not map that
    cancel onto a live ``qmb`` abort — ``CliQmbDoorTransport`` does.
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

    def abort(self, job_id: str) -> Result[QmbAbortReceipt]:
        """Recording door does not map cancel onto a live qmb abort."""
        return policy_rejection(
            "qmb_abort",
            "mapping JobHandle.cancel onto a live qmb abort is the production "
            "CLI door, not RecordingQmbDoorTransport (AR-W04; FR-W08; FR-W36)",
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
        classified = occupancy_from_invocation(invocation)
        stdout = ""
        if classified.occupancy == QMB_OCCUPANCY_QUERY:
            stdout = str(payload.get("stdout", ""))
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
                occupancy=classified.occupancy,
                mints_ct32=classified.mints_ct32,
                mints_experiment_spec=False,
                stdout=stdout,
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
            "occupancy": QMB_OCCUPANCY_RUN,
            "children_are_qma_jobs": False,
        }
        return MappingProxyType(payload)


@dataclass(frozen=True, slots=True)
class QmbQueryPlacement:
    """One placed QMB query: JobHandle for progress, no environment occupancy."""

    handle: JobHandle
    invocation: QmbDoorInvocation
    receipt: QmbDoorReceipt
    command: str
    occupancy: str = QMB_OCCUPANCY_QUERY
    mints_ct32: Literal[False] = False
    mints_experiment_spec: Literal[False] = False
    published: PublishedProjection | None = None
    tool_id: str = QMB_BACKTEST_TOOL_ID
    plugin_id: str = ANALYSIS_BACKTEST_PLUGIN_ID
    route: tuple[str, ...] = QMB_ROUTE

    def to_payload(self) -> Mapping[str, object]:
        payload: dict[str, object] = {
            "job_id": self.handle.job_id,
            "state": self.handle.state.value,
            "command": self.command,
            "occupancy": self.occupancy,
            "mints_ct32": self.mints_ct32,
            "mints_experiment_spec": self.mints_experiment_spec,
            "consumes_environment": False,
            "children_are_qma_jobs": False,
            "opens_daemon_sqlite": QMB_OPENS_DAEMON_SQLITE,
            "tool_id": self.tool_id,
            "plugin_id": self.plugin_id,
            "route": list(self.route),
            "program": self.invocation.program,
            "argv": list(self.invocation.argv),
            "stdout": self.receipt.stdout,
        }
        if self.published is not None:
            payload["published"] = dict(self.published.to_payload())
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
        artifact_root: Path | str | None = None,
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
        self._artifact_root = Path(artifact_root) if artifact_root is not None else None
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
                    "coordinated placement requires a registered ExperimentSpec (FR-W06; DEC-0270)",
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
            occupancy_class=QMB_OCCUPANCY_RUN,
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
        """JobHandle.cancel only. Production door maps it to QMB abort."""
        mapped = False
        abort_fn = getattr(self._transport, "abort", None)
        if self.maps_cancel_to_qmb_abort and callable(abort_fn):
            abort = cast("Callable[[str], Result[QmbAbortReceipt]]", abort_fn)
            aborted = abort(job_id)
            if is_refusal(aborted):
                return aborted
            mapped = True
        cancelled = self._jobs.cancel(job_id, writer=writer)
        if is_refusal(cancelled):
            return cancelled
        if mapped:
            self._jobs.record_progress(
                job_id,
                "qmb_abort",
                {
                    "mapped_from": COORDINATED_CANCEL_AUTHORITY,
                    "qmb_ledger_state": QMB_ABORTED_LEDGER_STATE,
                    "qmb_ledger_writer": "qmb",
                    "qma_writes_qmb_ledger": False,
                    "new_event_bus": False,
                },
            )
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
        role = entry.get("role", entry.get("state"))
        if role == QMB_ABORTED_LEDGER_STATE:
            authorized = authorize_qmb_ledger_aborted_writer(writer)
            if is_refusal(authorized):
                return authorized
        _ = entry
        return refuse_qmb_owned_concern(concern="run_ledger")

    def admit_process_per_run_child(
        self,
        occupancy_key: str,
        *,
        child_job_id: str,
    ) -> Result[dict[str, str]]:
        """QMB process-per-run children are not additional QMA jobs (FR-W11)."""
        return admit_qmb_job(
            self._occupancy,
            occupancy_key=occupancy_key,
            job_id=child_job_id,
            kind=QMB_PROCESS_PER_RUN_CHILD,
        )

    def qmb_opened_daemon_sqlite(self) -> bool:
        return qmb_opens_daemon_sqlite()

    def place_query(
        self,
        command: object,
        *,
        owner: ActorId | str,
        task_id: str,
        environment_ref: str,
        extra: Mapping[str, object] | None = None,
        dispatch_lease: DispatchLease | None = None,
        model_deployment_ref: object = None,
        persist_projection: bool = False,
        mint_ct32: object = None,
        successor: object = None,
        experiment_spec_fp1: str | None = None,
    ) -> Result[QmbQueryPlacement]:
        """Place a QMB query: no occupancy, no CT-32, no ExperimentSpec successor."""
        classified = classify_qmb_door_occupancy(command)
        if is_refusal(classified):
            return classified
        row = classified.value
        if row.occupancy != QMB_OCCUPANCY_QUERY:
            return invalid_input(
                "occupancy",
                "place_query places queries only; runs occupy the environment (FR-W11; DEC-0276)",
                command=row.command,
                occupancy=row.occupancy,
            )
        if mint_ct32 is not None and mint_ct32 is not False:
            return refuse_query_ct32_or_successor(command=row.command)
        if successor is not None and successor is not False:
            return refuse_query_ct32_or_successor(command=row.command)
        if persist_projection and row.command != "analysis.project":
            return invalid_input(
                "command",
                "coordinated analysis.published persistence is analysis.project only "
                "(FR-W24; DEC-0273)",
                command=row.command,
            )
        parsed_env = environment_kind_from_ref(environment_ref)
        if is_refusal(parsed_env):
            return parsed_env
        occupancy_key = parsed_env.value
        if (
            self._environments.get(occupancy_key) is None
            and self._environments.declaration(occupancy_key) is None
        ):
            return NoEnvironment.of(kind=occupancy_key, reason="kind_unbound")
        admitted = admit_qmb_job(
            self._occupancy,
            occupancy_key=occupancy_key,
            job_id=f"qmbq:{occupancy_key}:{task_id}",
            occupancy_class=QMB_OCCUPANCY_QUERY,
        )
        if is_refusal(admitted):
            return admitted
        job_id = f"qmbq:{occupancy_key}:{task_id}"
        minted = self._jobs.submit(
            owner=owner,
            task_id=task_id,
            job_id=job_id,
        )
        if is_refusal(minted):
            return minted
        invocation = build_qmb_query_invocation(
            job_id=minted.value.job_id,
            command=row.command,
            environment_ref=environment_ref,
            occupancy_key=occupancy_key,
            extra=extra,
        )
        if is_refusal(invocation):
            return invocation
        receipt = self._transport.submit(invocation.value)
        if is_refusal(receipt):
            return receipt
        started = self._jobs.start(job_id)
        if is_refusal(started):
            return started
        published: PublishedProjection | None = None
        if persist_projection:
            persisted = self._persist_projection_query(
                receipt=receipt.value,
                extra=extra,
                spec_fp1=experiment_spec_fp1,
                dispatch_lease=dispatch_lease,
                model_deployment_ref=model_deployment_ref,
            )
            if is_refusal(persisted):
                return persisted
            published = persisted.value
        completed = self._jobs.complete(job_id, JobHandleState.DONE, writer="qmb_outcome")
        if is_refusal(completed):
            return completed
        self._jobs.record_progress(
            job_id,
            "query",
            {
                "command": row.command,
                "occupancy": QMB_OCCUPANCY_QUERY,
                "mints_ct32": False,
                "mints_experiment_spec": False,
                "kind": ANALYSIS_PUBLISHED_KIND if published is not None else row.command,
                "new_event_bus": False,
            },
        )
        return Ok(
            QmbQueryPlacement(
                handle=completed.value,
                invocation=invocation.value,
                receipt=receipt.value,
                command=row.command,
                published=published,
            )
        )

    def _persist_projection_query(
        self,
        *,
        receipt: QmbDoorReceipt,
        extra: Mapping[str, object] | None,
        spec_fp1: str | None,
        dispatch_lease: DispatchLease | None,
        model_deployment_ref: object,
    ) -> Result[PublishedProjection]:
        if self._experiments is None:
            return invalid_input(
                "experiments",
                "coordinated analysis.project persistence requires ExperimentSpec "
                "product truth (FR-W24; Story 36.3)",
            )
        if dispatch_lease is None or not isinstance(spec_fp1, str) or spec_fp1.strip() == "":
            return invalid_input(
                "experiment_spec_fp1",
                "coordinated analysis.published cites a registered ExperimentSpec "
                "fp1 (FR-W24; DEC-0273)",
            )
        view = _projection_view_from_stdout(receipt.stdout, extra)
        if is_refusal(view):
            return view
        return self._experiments.persist_published_view(
            spec_fp1=spec_fp1.strip(),
            dispatch_lease=dispatch_lease,
            model_deployment_ref=model_deployment_ref,
            view=view.value,
            artifact_root=self._artifact_root,
        )

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
