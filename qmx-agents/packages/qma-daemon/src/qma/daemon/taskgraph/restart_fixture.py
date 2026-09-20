"""Story 59.2 — crash-restart fixture on the Story 57.2 outbox machine.

Completing A publishes the successor outbox row. A crash before B's dispatch
ack must replay that row (at-least-once dispatch). Receiver dedupe on
``logical_invocation_id`` is exactly-once logical acceptance against the
Story 54.2 / Epic 58 ``InvocationEnvelope``. A second logical B for the same
id is SCN-0021 Branch A and fails the fixture. Lost ``external-egress`` ack
stays ``unknown`` until reconcile and must not duplicate the side effect.
No new sqlite class.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qma.core.ontology import ActorId, DeskSlug, Goal, Quant, RoleName
from qma.core.operations import (
    ERROR_REFUSAL_FAMILY,
    REQUIRED_REFUSAL_CODES,
    EffectOutcome,
    OperationDescriptor,
    apply_effect_outcome,
    parse_operation_descriptor,
    public_operation_descriptors,
)
from qma.core.ports.execution import ExecutionEnvironmentDeclaration
from qma.core.refusals import BlindRetryRefused
from qma.core.vocabulary.enums import (
    ExecutionEnvironmentKind,
    JobHandleState,
    TaskMissionState,
)
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.plugins import research_corpus_plugin_load_config
from qma.daemon.process import DaemonProcess
from qma.daemon.taskgraph.compiler import (
    CompileRequest,
    CompileResult,
    GraphTemplateCatalog,
    MissionCompiler,
)
from qma.daemon.taskgraph.dispatcher import TaskGraphDispatcher
from qma.daemon.taskgraph.outbox import (
    OutboxAcceptanceState,
    OutboxTransportState,
    ReceiverAcceptance,
    TaskGraphOutboxRow,
    envelope_hash_for,
)
from qma.daemon.taskgraph.records import GraphTemplate
from qma.daemon.taskgraph.state import JobHandleEvidence
from qma.wire import (
    INVOCATION_ENVELOPE_IS_AUTHORITY,
    AuthoritativeStores,
    BoundInvocation,
    ContributionBinding,
    ContributionRecord,
    GrantRecord,
    InstanceRecord,
    InvocationEnvelope,
    compute_input_hash,
    public_call_in_process,
)
from qmf.core import Ok, Result, is_ok, is_refusal
from qmf.core.refusal import TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "EGRESS_FIXTURE_OP_ID",
    "OUTBOX_RESTART_FIXTURE_OWNER",
    "OUTBOX_RESTART_NEW_SQLITE_CLASS",
    "SECOND_LOGICAL_B_BRANCH",
    "ExternalEgressRestartReport",
    "OutboxRestartFixture",
    "OutboxRestartReport",
    "egress_fixture_descriptor",
    "envelope_for_outbox_row",
    "refuse_second_logical_b",
    "stores_for_envelope",
]


OUTBOX_RESTART_FIXTURE_OWNER: Final[str] = "COMP-QMA-DAEMON"
OUTBOX_RESTART_NEW_SQLITE_CLASS: Final[bool] = False
SECOND_LOGICAL_B_BRANCH: Final[str] = "A"
EGRESS_FIXTURE_OP_ID: Final[str] = "qma.fixture.export"
_CONTRIBUTION: Final[Mapping[str, str]] = MappingProxyType(
    {"qualified_id": "analysis-backtest:qmb", "package_version": "0.1.0"}
)
_PROJECT_INPUT: Final[Mapping[str, object]] = MappingProxyType({"run_fp1": "run-1"})
_EGRESS_INPUT: Final[Mapping[str, object]] = MappingProxyType({"export_ref": "export-1"})
_GRANT_ID: Final[str] = "grant:1"
_INSTANCE_ID: Final[str] = "inst:1"
_CALLER: Final[str] = "psess:caller"

_EGRESS_DESCRIPTOR_PAYLOAD: Final[Mapping[str, object]] = MappingProxyType(
    {
        "op_id": EGRESS_FIXTURE_OP_ID,
        "owner": "COMP-QMA",
        "version": 1,
        "input_schema": "qma.fixture.export.v1",
        "output_shape": "artifact_ref",
        "input_cardinality": "one",
        "output_cardinality": "one",
        "empty_policy": "refuse",
        "configuration": {
            "defaults": {},
            "required_keys": ["export_ref"],
            "optional_keys": [],
        },
        "declared_operation_dependencies": [],
        "resource_needs": {
            "occupancy": "query",
            "memory_class": "light",
            "requires_environment": False,
        },
        "documentation_refs": ["docs/scenarios/SCN-0021-outbox-jobhandle.md"],
        "validation_class": "schema+semantic",
        "units": None,
        "compatibility": {"qma-core": ">=0.1"},
        "effect_class": "external-egress",
        "permission_requests": ["library.export"],
        "placement": "worker",
        "error_refusal_shape": {
            "family": ERROR_REFUSAL_FAMILY,
            "codes": sorted(REQUIRED_REFUSAL_CODES),
        },
        "progress": False,
        "lifecycle_verbs": ["start", "query-state"],
        "supported_doors": [
            {"adapter": "library", "door": EGRESS_FIXTURE_OP_ID},
            {"adapter": "qma-wire", "door": "via CT-47"},
        ],
    }
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    return invalid_input(field, reason, **extra)


def refuse_second_logical_b(
    *,
    logical_invocation_id: object,
    count: object | None = None,
    **extra: object,
) -> TypedRefusal:
    """SCN-0021 Branch A — a second logical B for the same id fails the fixture."""
    extra.pop("field", None)
    reason = extra.pop(
        "reason",
        "second logical B for the same logical_invocation_id is forbidden "
        "(SCN-0021 Branch A; FR-WF-69)",
    )
    if count is not None:
        extra.setdefault("count", count)
    return policy_rejection(
        "logical_invocation_id",
        str(reason),
        branch=SECOND_LOGICAL_B_BRANCH,
        logical_invocation_id=logical_invocation_id,
        fixture_failed=True,
        **extra,
    )


def _descriptor_for(op_id: str, version: int) -> Result[OperationDescriptor]:
    if op_id == EGRESS_FIXTURE_OP_ID:
        return egress_fixture_descriptor()
    for item in public_operation_descriptors():
        if item.op_id == op_id and item.version == version:
            return Ok(item)
    return _invalid("op_id", "no public descriptor for successor target", op_id=op_id)


def egress_fixture_descriptor() -> Result[OperationDescriptor]:
    """Fixture-local ``external-egress`` descriptor; not a catalog mint."""
    return parse_operation_descriptor(dict(_EGRESS_DESCRIPTOR_PAYLOAD))


def envelope_for_outbox_row(
    row: TaskGraphOutboxRow,
    *,
    descriptor: OperationDescriptor,
    payload: Mapping[str, object],
    attempt_id: int = 1,
    effect_class: str | None = None,
    reconcile_policy: str = "query-then-decide",
) -> Result[InvocationEnvelope]:
    """Bind a Story 54.2 envelope to the outbox ``logical_invocation_id``."""
    hashed = compute_input_hash(dict(payload), descriptor=descriptor)
    if is_refusal(hashed):
        return hashed
    op_raw = row.target.get("op_id")
    version_raw = row.target.get("op_version")
    instance_raw = row.target.get("instance_id")
    revision_raw = row.target.get("config_revision")
    if not isinstance(op_raw, str) or not op_raw:
        return _invalid("target.op_id", "outbox target requires op_id")
    if not isinstance(version_raw, int) or isinstance(version_raw, bool):
        return _invalid("target.op_version", "outbox target requires op_version")
    if not isinstance(instance_raw, str) or not instance_raw:
        return _invalid("target.instance_id", "outbox target requires instance_id")
    if not isinstance(revision_raw, int) or isinstance(revision_raw, bool):
        return _invalid("target.config_revision", "outbox target requires config_revision")
    return InvocationEnvelope.try_create(
        logical_invocation_id=row.logical_invocation_id,
        attempt_id=attempt_id,
        op_id=op_raw,
        op_version=version_raw,
        contribution=dict(_CONTRIBUTION),
        instance_id=instance_raw,
        config_revision=revision_raw,
        caller_session_ref=_CALLER,
        grant_id=_GRANT_ID,
        effect_class=descriptor.effect_class.value if effect_class is None else effect_class,
        idempotency_key=f"idem:{row.logical_invocation_id}",
        reconcile_policy=reconcile_policy,
        input_hash=hashed.value,
        call_depth=0,
    )


def stores_for_envelope(
    envelope: InvocationEnvelope,
    descriptor: OperationDescriptor,
) -> Result[AuthoritativeStores]:
    """Authoritative stores the host compares on every hop (RC-03)."""
    grant = GrantRecord.try_create(
        grant_id=envelope.grant_id,
        principal="operator",
        audience=_CALLER,
        contribution=dict(envelope.contribution.to_payload()),
        instance_id=envelope.instance_id,
        config_revision=envelope.config_revision,
        op_id=envelope.op_id,
        op_version=envelope.op_version,
        effect_class=envelope.effect_class.value,
        parameter_ceiling={"allow_keys": list(descriptor.configuration.required_keys)},
        expires_at="2099-01-01T00:00:00Z",
    )
    if is_refusal(grant):
        return grant
    contribution = ContributionBinding(
        qualified_id=envelope.contribution.qualified_id,
        package_version=envelope.contribution.package_version,
    )
    record = ContributionRecord(
        qualified_id=contribution.qualified_id,
        package_version=contribution.package_version,
        availability="enabled",
    )
    instance = InstanceRecord(
        instance_id=envelope.instance_id,
        config_revision=envelope.config_revision,
    )
    return Ok(
        AuthoritativeStores(
            contributions={record.as_tuple(): record},
            descriptors={(descriptor.op_id, descriptor.version): descriptor},
            grants={grant.value.grant_id: grant.value},
            instances={(instance.instance_id, instance.config_revision): instance},
        )
    )


def _quant(*, slug: str) -> Result[Quant]:
    minted = ActorId.mint(DeskSlug.RESEARCH, slug)
    if is_refusal(minted):
        return minted
    return Ok(
        Quant(
            actor_id=minted.value,
            desk=DeskSlug.RESEARCH,
            quant_slug=slug,
            role=RoleName.RESEARCHER,
            name=f"Quant {slug}",
        )
    )


def _edge(src: str, dst: str) -> dict[str, object]:
    return {
        "from": src,
        "to": dst,
        "mapping": "one",
        "from_port": "data",
        "to_port": "data",
    }


def _template(*, op_id: str, op_version: int) -> GraphTemplate:
    successor_inputs: dict[str, object] = {
        "op_id": op_id,
        "op_version": op_version,
        "instance_id": _INSTANCE_ID,
    }
    return GraphTemplate(
        qualified_id="research-corpus:outbox-restart",
        version="1",
        nodes=(
            {"id": "prepare", "kind": "task", "intent": "prepare corpus"},
            {
                "id": "survey",
                "kind": "task",
                "intent": "survey coverage",
                "inputs": successor_inputs,
            },
        ),
        edges=(_edge("prepare", "survey"),),
    )


@dataclass(frozen=True, slots=True)
class OutboxRestartReport:
    """J27 crash-restart: at-least-once dispatch, exactly-once acceptance."""

    graph_run_id: str
    logical_invocation_id: str
    successor_node_id: str
    envelope: InvocationEnvelope
    bound: BoundInvocation
    first_acceptance: ReceiverAcceptance
    replay_acceptance: ReceiverAcceptance
    dispatch_attempts: int
    outbox_row_count: int
    envelope_hash: str

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "acceptance_replayed": self.replay_acceptance.replayed,
                "dispatch_attempts": self.dispatch_attempts,
                "envelope_is_authority": INVOCATION_ENVELOPE_IS_AUTHORITY,
                "envelope_logical_invocation_id": self.envelope.logical_invocation_id,
                "first_replayed": self.first_acceptance.replayed,
                "graph_run_id": self.graph_run_id,
                "logical_invocation_id": self.logical_invocation_id,
                "outbox_row_count": self.outbox_row_count,
                "receiver_acceptance_id": self.first_acceptance.receiver_acceptance_id,
                "successor_node_id": self.successor_node_id,
            }
        )


@dataclass(frozen=True, slots=True)
class ExternalEgressRestartReport:
    """J26 lost ack: unknown until reconcile; no duplicate side effect."""

    logical_invocation_id: str
    envelope: InvocationEnvelope
    first_outcome: EffectOutcome
    retry_outcome: EffectOutcome
    reconciled: EffectOutcome
    side_effect_count: int
    blind_retry: TypedRefusal

    def to_payload(self) -> Mapping[str, object]:
        first_state = self.first_outcome.handle_state
        retry_state = self.retry_outcome.handle_state
        return MappingProxyType(
            {
                "blind_retry_variant": self.blind_retry.context.get("code"),
                "first_handle_state": None if first_state is None else first_state.value,
                "logical_invocation_id": self.logical_invocation_id,
                "reconcile_disposition": self.reconciled.disposition,
                "retry_duplicated": self.retry_outcome.duplicated,
                "retry_handle_state": None if retry_state is None else retry_state.value,
                "side_effect_count": self.side_effect_count,
            }
        )


@dataclass
class OutboxRestartFixture:
    """Thin SCN-0021 fixture over the Story 57.2 sqlite outbox machine."""

    root: Path
    _side_effects: dict[str, list[dict[str, object]]] = field(
        default_factory=dict[str, list[dict[str, object]]], init=False
    )
    _dispatch_attempts: dict[str, int] = field(default_factory=dict[str, int], init=False)

    def __post_init__(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)

    @property
    def owner(self) -> str:
        return OUTBOX_RESTART_FIXTURE_OWNER

    @property
    def new_sqlite_class(self) -> bool:
        return OUTBOX_RESTART_NEW_SQLITE_CLASS

    def side_effects(self, logical_invocation_id: str) -> tuple[Mapping[str, object], ...]:
        return tuple(self._side_effects.get(logical_invocation_id, ()))

    def _compose(self, *, boot: str) -> Result[DaemonProcess]:
        seed = self.root / "seed-corpus"
        seed.mkdir(exist_ok=True)
        return DaemonProcess.compose(
            self.root,
            machine="outbox-restart-host",
            boot_epoch_id=boot,
            bind_port=0,
            plugin_load_configs=research_corpus_plugin_load_config(seed),
        )

    def _dispatcher(self, process: DaemonProcess) -> Result[TaskGraphDispatcher]:
        envs = ExecutionEnvironmentRegistry()
        registered = envs.register_declaration(
            ExecutionEnvironmentDeclaration.isolated(
                ExecutionEnvironmentKind.DOCKER,
                provider_ref="local-docker",
            )
        )
        if is_refusal(registered):
            return registered
        return Ok(TaskGraphDispatcher(environments=envs, durable=process.task_graphs))

    def _compile(
        self,
        *,
        slug: str,
        op_id: str,
        op_version: int,
    ) -> Result[CompileResult]:
        owner = _quant(slug=slug)
        if is_refusal(owner):
            return owner
        catalog = GraphTemplateCatalog()
        registered = catalog.register(_template(op_id=op_id, op_version=op_version))
        if is_refusal(registered):
            return registered
        compiler = MissionCompiler(
            templates=catalog,
            known_quant_actor_ids={owner.value.actor_id.value},
        )
        return compiler.compile(
            CompileRequest(
                goal=Goal(text="survey after prepare"),
                owner=owner.value,
                graph_template_ref="research-corpus:outbox-restart",
                intent="survey after prepare",
            )
        )

    def _complete_a(
        self,
        process: DaemonProcess,
        compiled: CompileResult,
    ) -> Result[tuple[TaskGraphDispatcher, TaskGraphOutboxRow, str]]:
        dispatcher = self._dispatcher(process)
        if is_refusal(dispatcher):
            return dispatcher
        dispatcher.value.materialize(compiled.task_graph, mission=compiled.mission)
        prepare = compiled.task_graph.ready_tasks()
        if not prepare:
            return _invalid("task", "compiled graph has no ready predecessor")
        dispatched = dispatcher.value.dispatch_task(
            task_id=prepare[0].id,
            holder_agent_id="agent-worker-1",
            environment_kind=ExecutionEnvironmentKind.DOCKER,
        )
        if is_refusal(dispatched):
            return dispatched
        applied = dispatcher.value.apply_job_handle_evidence(
            JobHandleEvidence(
                job_id="job-a",
                task_id=prepare[0].id,
                state=JobHandleState.DONE,
            )
        )
        if is_refusal(applied):
            return applied
        rows = process.task_graphs.outbox_rows(compiled.task_graph.id)
        if not rows:
            return policy_rejection(
                "outbox",
                "completing A cannot forget B; terminal A must publish an outbox row",
                graph_run_id=compiled.task_graph.id,
            )
        if len(rows) != 1:
            return refuse_second_logical_b(
                logical_invocation_id=rows[0].logical_invocation_id,
                count=len(rows),
            )
        survey = compiled.task_graph.task_for_node("survey")
        if survey is None:
            return _invalid("node_id", "compiled graph missing survey successor")
        return Ok((dispatcher.value, rows[0], survey.id))

    def _record_dispatch(self, bound: BoundInvocation, *, fire: bool) -> None:
        logical_id = bound.envelope.logical_invocation_id
        self._dispatch_attempts[logical_id] = self._dispatch_attempts.get(logical_id, 0) + 1
        if not fire:
            return
        bucket = self._side_effects.setdefault(logical_id, [])
        bucket.append({"order": "sent", "attempt": self._dispatch_attempts[logical_id]})

    def _invoke(
        self,
        envelope: InvocationEnvelope,
        payload: Mapping[str, object],
        stores: AuthoritativeStores,
        *,
        fire: bool,
    ) -> Result[BoundInvocation]:
        def execute(bound: BoundInvocation) -> None:
            self._record_dispatch(bound, fire=fire)

        bound = public_call_in_process(envelope, dict(payload), stores, execute=execute)
        if is_refusal(bound):
            return bound
        if bound.value.is_authority or INVOCATION_ENVELOPE_IS_AUTHORITY:
            return policy_rejection(
                "invocation_envelope",
                "InvocationEnvelope is bound request context, not authority",
            )
        return bound

    def _one_logical_b(
        self,
        process: DaemonProcess,
        *,
        graph_run_id: str,
        logical_invocation_id: str,
    ) -> Result[TaskGraphOutboxRow]:
        matching = tuple(
            row
            for row in process.task_graphs.outbox_rows(graph_run_id)
            if row.logical_invocation_id == logical_invocation_id
        )
        if not matching:
            return policy_rejection(
                "outbox",
                "completing A cannot forget B; restart must replay the unacked row",
                graph_run_id=graph_run_id,
                logical_invocation_id=logical_invocation_id,
            )
        if len(matching) != 1:
            return refuse_second_logical_b(
                logical_invocation_id=logical_invocation_id,
                count=len(matching),
            )
        return Ok(matching[0])

    def crash_then_replay(
        self,
        *,
        slug: str = "j27",
        boot: str = "boot-59-2-j27",
    ) -> Result[OutboxRestartReport]:
        """Crash between A-terminal+outbox and B dispatch ack, then replay."""
        compiled = self._compile(
            slug=slug,
            op_id="qmb.analysis.project",
            op_version=1,
        )
        if is_refusal(compiled):
            return compiled
        graph_id = compiled.value.task_graph.id
        process = self._compose(boot=f"{boot}-a")
        if is_refusal(process):
            return process
        logical_id = ""
        survey_id = ""
        envelope_hash = ""
        try:
            completed = self._complete_a(process.value, compiled.value)
            if is_refusal(completed):
                return completed
            _dispatcher, row, survey_id = completed.value
            if row.transport_state is not OutboxTransportState.PENDING:
                return policy_rejection(
                    "transport_state",
                    "crash window is before B dispatch ack",
                    transport_state=row.transport_state.value,
                )
            logical_id = row.logical_invocation_id
            hashed = envelope_hash_for(logical_invocation_id=logical_id, target=row.target)
            if is_refusal(hashed):
                return hashed
            envelope_hash = hashed.value
            if row.envelope_hash != envelope_hash:
                return policy_rejection(
                    "envelope_hash",
                    "outbox envelope_hash must match the persisted target",
                    stored=row.envelope_hash,
                    expected=envelope_hash,
                )
        finally:
            process.value.close()

        restarted = self._compose(boot=f"{boot}-b")
        if is_refusal(restarted):
            return restarted
        try:
            one = self._one_logical_b(
                restarted.value,
                graph_run_id=graph_id,
                logical_invocation_id=logical_id,
            )
            if is_refusal(one):
                return one
            pending = restarted.value.task_graphs.replayable_rows(graph_id)
            if len(pending) != 1:
                return refuse_second_logical_b(
                    logical_invocation_id=logical_id,
                    count=len(pending),
                    replayable=True,
                )
            restored = restarted.value.task_graphs.get(graph_id)
            if is_refusal(restored):
                return restored
            survey = restored.value.task_for_node("survey")
            if survey is None or survey.state is not TaskMissionState.READY:
                return policy_rejection(
                    "successor",
                    "restart must restore B ready with the outbox row",
                    graph_run_id=graph_id,
                )
            descriptor = _descriptor_for("qmb.analysis.project", 1)
            if is_refusal(descriptor):
                return descriptor
            envelope = envelope_for_outbox_row(
                one.value,
                descriptor=descriptor.value,
                payload=_PROJECT_INPUT,
                attempt_id=1,
            )
            if is_refusal(envelope):
                return envelope
            stores = stores_for_envelope(envelope.value, descriptor.value)
            if is_refusal(stores):
                return stores
            first_bound = self._invoke(
                envelope.value,
                _PROJECT_INPUT,
                stores.value,
                fire=True,
            )
            if is_refusal(first_bound):
                return first_bound
            replay_envelope = envelope_for_outbox_row(
                one.value,
                descriptor=descriptor.value,
                payload=_PROJECT_INPUT,
                attempt_id=2,
            )
            if is_refusal(replay_envelope):
                return replay_envelope
            second_bound = self._invoke(
                replay_envelope.value,
                _PROJECT_INPUT,
                stores.value,
                fire=True,
            )
            if is_refusal(second_bound):
                return second_bound
            dispatcher = self._dispatcher(restarted.value)
            if is_refusal(dispatcher):
                return dispatcher
            dispatcher.value.store.remember(restored.value)
            dispatched = dispatcher.value.dispatch_task(
                task_id=survey_id,
                holder_agent_id="agent-worker-2",
                environment_kind=ExecutionEnvironmentKind.DOCKER,
            )
            if is_refusal(dispatched):
                return dispatched
            first = restarted.value.task_graphs.accept_logical(
                logical_id, result={"node": "survey", "ok": True}
            )
            if is_refusal(first):
                return first
            if first.value.replayed:
                return refuse_second_logical_b(
                    logical_invocation_id=logical_id,
                    reason="first acceptance after restart must be the original B",
                )
            replayed = restarted.value.task_graphs.accept_logical(
                logical_id, result={"node": "survey", "ok": False}
            )
            if is_refusal(replayed):
                return replayed
            if not replayed.value.replayed:
                return refuse_second_logical_b(
                    logical_invocation_id=logical_id,
                    reason="receiver must return the prior durable result",
                )
            if replayed.value.receiver_acceptance_id != first.value.receiver_acceptance_id:
                return refuse_second_logical_b(
                    logical_invocation_id=logical_id,
                    reason="receiver_acceptance_id must be stable under replay",
                )
            still = self._one_logical_b(
                restarted.value,
                graph_run_id=graph_id,
                logical_invocation_id=logical_id,
            )
            if is_refusal(still):
                return still
            accepted_row = still.value
            if accepted_row.acceptance_state is not OutboxAcceptanceState.ACCEPTED:
                return policy_rejection(
                    "acceptance_state",
                    "B must be accepted exactly once logically",
                    acceptance_state=(
                        None
                        if accepted_row.acceptance_state is None
                        else accepted_row.acceptance_state.value
                    ),
                )
            if accepted_row.transport_state is not OutboxTransportState.DISPATCHED:
                return policy_rejection(
                    "transport_state",
                    "replay acks dispatch without minting a second logical B",
                    transport_state=accepted_row.transport_state.value,
                )
            return Ok(
                OutboxRestartReport(
                    graph_run_id=graph_id,
                    logical_invocation_id=logical_id,
                    successor_node_id="survey",
                    envelope=envelope.value,
                    bound=first_bound.value,
                    first_acceptance=first.value,
                    replay_acceptance=replayed.value,
                    dispatch_attempts=self._dispatch_attempts.get(logical_id, 0),
                    outbox_row_count=len(restarted.value.task_graphs.outbox_rows(graph_id)),
                    envelope_hash=envelope_hash,
                )
            )
        finally:
            restarted.value.close()

    def lost_egress_ack(
        self,
        *,
        slug: str = "j26",
        boot: str = "boot-59-2-j26",
    ) -> Result[ExternalEgressRestartReport]:
        """Lost ``external-egress`` ack stays unknown; retry must not duplicate."""
        compiled = self._compile(slug=slug, op_id=EGRESS_FIXTURE_OP_ID, op_version=1)
        if is_refusal(compiled):
            return compiled
        graph_id = compiled.value.task_graph.id
        process = self._compose(boot=f"{boot}-a")
        if is_refusal(process):
            return process
        logical_id = ""
        try:
            completed = self._complete_a(process.value, compiled.value)
            if is_refusal(completed):
                return completed
            _dispatcher, row, _survey_id = completed.value
            logical_id = row.logical_invocation_id
        finally:
            process.value.close()

        restarted = self._compose(boot=f"{boot}-b")
        if is_refusal(restarted):
            return restarted
        try:
            one = self._one_logical_b(
                restarted.value,
                graph_run_id=graph_id,
                logical_invocation_id=logical_id,
            )
            if is_refusal(one):
                return one
            descriptor = egress_fixture_descriptor()
            if is_refusal(descriptor):
                return descriptor
            envelope = envelope_for_outbox_row(
                one.value,
                descriptor=descriptor.value,
                payload=_EGRESS_INPUT,
                attempt_id=1,
                effect_class="external-egress",
                reconcile_policy="query-then-decide",
            )
            if is_refusal(envelope):
                return envelope
            stores = stores_for_envelope(envelope.value, descriptor.value)
            if is_refusal(stores):
                return stores
            first_outcome = apply_effect_outcome(
                effect_class="external-egress",
                reconcile_policy="query-then-decide",
                logical_invocation_id=logical_id,
                receipt=None,
                is_retry=False,
            )
            if is_refusal(first_outcome):
                return first_outcome
            if first_outcome.value.handle_state is not JobHandleState.UNKNOWN:
                return policy_rejection(
                    "handle_state",
                    "lost external-egress acknowledgement stays unknown until reconcile",
                    handle_state=(
                        None
                        if first_outcome.value.handle_state is None
                        else first_outcome.value.handle_state.value
                    ),
                )
            invoked = self._invoke(
                envelope.value,
                _EGRESS_INPUT,
                stores.value,
                fire=True,
            )
            if is_refusal(invoked):
                return invoked
            prior = {"order": "sent", "logical_invocation_id": logical_id}
            retry_envelope = envelope_for_outbox_row(
                one.value,
                descriptor=descriptor.value,
                payload=_EGRESS_INPUT,
                attempt_id=2,
                effect_class="external-egress",
                reconcile_policy="query-then-decide",
            )
            if is_refusal(retry_envelope):
                return retry_envelope
            retry_outcome = apply_effect_outcome(
                effect_class="external-egress",
                reconcile_policy="query-then-decide",
                logical_invocation_id=logical_id,
                receipt=None,
                prior_result=prior,
                is_retry=True,
            )
            if is_refusal(retry_outcome):
                return retry_outcome
            if retry_outcome.value.duplicated:
                return refuse_second_logical_b(
                    logical_invocation_id=logical_id,
                    reason="external-egress retry must not duplicate the side effect",
                )
            if retry_outcome.value.handle_state is not JobHandleState.UNKNOWN:
                return policy_rejection(
                    "handle_state",
                    "retry without receipt stays unknown until reconcile",
                    handle_state=(
                        None
                        if retry_outcome.value.handle_state is None
                        else retry_outcome.value.handle_state.value
                    ),
                )
            gated = self._invoke(
                retry_envelope.value,
                _EGRESS_INPUT,
                stores.value,
                fire=False,
            )
            if is_refusal(gated):
                return gated
            blind = apply_effect_outcome(
                effect_class="external-egress",
                reconcile_policy="query-then-decide",
                logical_invocation_id=logical_id,
                receipt=None,
                is_retry=True,
            )
            if is_ok(blind) or not isinstance(blind, BlindRetryRefused):
                return policy_rejection(
                    "effect_class",
                    "blind external-egress retry without receipt/reconcile is forbidden",
                    logical_invocation_id=logical_id,
                )
            reconciled = apply_effect_outcome(
                effect_class="external-egress",
                reconcile_policy="query-then-decide",
                logical_invocation_id=logical_id,
                receipt={"ack": "ok"},
                prior_result=prior,
                is_retry=True,
            )
            if is_refusal(reconciled):
                return reconciled
            side_effects = self.side_effects(logical_id)
            if len(side_effects) != 1:
                return refuse_second_logical_b(
                    logical_invocation_id=logical_id,
                    count=len(side_effects),
                    reason="external-egress side effect must fire once",
                )
            accepted = restarted.value.task_graphs.accept_logical(logical_id, result=dict(prior))
            if is_refusal(accepted):
                return accepted
            replayed = restarted.value.task_graphs.accept_logical(
                logical_id, result={"order": "duplicate"}
            )
            if is_refusal(replayed):
                return replayed
            if not replayed.value.replayed or dict(replayed.value.result) != dict(prior):
                return refuse_second_logical_b(
                    logical_invocation_id=logical_id,
                    reason="receiver replay must return the prior egress result",
                )
            return Ok(
                ExternalEgressRestartReport(
                    logical_invocation_id=logical_id,
                    envelope=envelope.value,
                    first_outcome=first_outcome.value,
                    retry_outcome=retry_outcome.value,
                    reconciled=reconciled.value,
                    side_effect_count=len(side_effects),
                    blind_retry=cast("TypedRefusal", blind),
                )
            )
        finally:
            restarted.value.close()
