"""Story 46.3 — Quant/Experiment Ledgers and desk views (FR-Q59)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.content import content_address
from qma.core.ontology import ActorId, Agent, DeskSlug, Quant, RoleName
from qma.core.ports.experiments import ExperimentSpec
from qma.core.ports.ledgers import QuantLedgerLease
from qma.core.vocabulary.enums import QuantLedgerEntryKind
from qma.daemon.experiments import ExperimentSpecService
from qma.daemon.ledgers import (
    DESK_LEDGER_VIEW_FOLD_ID,
    GAP_0082_DEFERRED,
    QUANT_LEDGER_DECLARED_KINDS,
    DeskLedgerViews,
    ExperimentLedgerStore,
    QuantLedgerStore,
    TaskLedgerStore,
    refuse_fourth_ledger_store,
)
from qma.daemon.taskgraph.records import DispatchLease
from qmf.core import is_ok, is_refusal


def _actor(desk: DeskSlug, slug: str) -> ActorId:
    minted = ActorId.mint(desk, slug)
    assert is_ok(minted)
    return minted.value


def _quant(*, slug: str = "lead", lead: bool = True, desk: DeskSlug = DeskSlug.RESEARCH) -> Quant:
    return Quant(
        actor_id=_actor(desk, slug),
        desk=desk,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
        lead=lead,
    )


def _agent(quant: Quant, agent_id: str) -> Agent:
    return Agent(id=agent_id, owner=quant.actor_id, session_id="session-1")


def _lease(quant: Quant, holder: str) -> QuantLedgerLease:
    return QuantLedgerLease(owner=quant.actor_id, holder_agent_id=holder)


def _entry(quant: Quant, *, agent: str, kind: str = "standing_decision") -> dict[str, object]:
    return {
        "kind": kind,
        "authored_by": {"agent": agent, "quant": quant.actor_id.value},
        "model_deployment_ref": "deploy:workhorse",
        "body": {"note": kind},
    }


def _dispatch(quant: Quant, *, task_id: str, holder: str) -> DispatchLease:
    return DispatchLease(
        task_id=task_id,
        holder_agent_id=holder,
        mission_id="mission-1",
        owner=quant.actor_id,
    )


def _spec() -> ExperimentSpec:
    addressed = content_address({"label": "desk-view-cfg"})
    assert is_ok(addressed)
    created = ExperimentSpec.try_create(
        data_ref="data:eurusd",
        environment_ref="env:docker",
        seed=7,
        model_and_harness_version={"model": "analyst-v1", "harness": "qmb-1"},
        cost_assumptions={"spread_usd_cents": 10},
        resolved_config_ref=addressed.value.value,
    )
    assert is_ok(created)
    return created.value


def test_quant_ledger_opens_only_for_lead_flag_with_declared_schema() -> None:
    store = QuantLedgerStore()
    lead = _quant(lead=True)
    opened = store.open_for_quant(lead)
    assert is_ok(opened)
    payload = opened.value.to_payload()
    assert payload["store"] == "quant_ledger"
    assert payload["declared_kinds"] == sorted(QUANT_LEDGER_DECLARED_KINDS)
    assert QuantLedgerEntryKind.MISSION_OPENED.value in QUANT_LEDGER_DECLARED_KINDS
    follower = _quant(slug="follower", lead=False)
    refused = store.open_for_quant(follower)
    assert is_refusal(refused)
    assert refused.context["field"] == "lead_flag"
    assert store.get(follower) is None


def test_only_one_quant_ledger_lease_holder_may_append_at_a_time() -> None:
    store = QuantLedgerStore()
    lead = _quant()
    assert is_ok(store.open_for_quant(lead))
    first = _lease(lead, "agent-a")
    granted = store.grant(first, agent=_agent(lead, "agent-a"))
    assert is_ok(granted)
    recorded = store.append(_entry(lead, agent="agent-a"), lease=first)
    assert is_ok(recorded)
    assert recorded.value.entries[0]["kind"] == "standing_decision"
    outsider = store.append(
        _entry(lead, agent="agent-b"),
        lease=_lease(lead, "agent-b"),
    )
    assert is_refusal(outsider)
    assert outsider.context["field"] == "quant_ledger_lease"
    replaced = store.grant(_lease(lead, "agent-b"), agent=_agent(lead, "agent-b"))
    assert is_ok(replaced)
    stale = store.append(_entry(lead, agent="agent-a"), lease=first)
    assert is_refusal(stale)
    second = store.append(
        _entry(lead, agent="agent-b", kind="delegation"),
        lease=_lease(lead, "agent-b"),
    )
    assert is_ok(second)
    kinds = [entry["kind"] for entry in second.value.entries]
    assert kinds == ["standing_decision", "delegation"]
    other_quant = store.grant(
        QuantLedgerLease(owner=_actor(DeskSlug.RESEARCH, "other"), holder_agent_id="agent-a")
    )
    assert is_refusal(other_quant)


def test_lead_flag_move_retains_existing_ledger_and_does_not_open_successor() -> None:
    store = QuantLedgerStore()
    current = _quant(slug="lead", lead=True)
    successor = _quant(slug="next", lead=False)
    opened = store.open_for_quant(current)
    assert is_ok(opened)
    lease = _lease(current, "agent-a")
    store.grant(lease)
    store.append(_entry(current, agent="agent-a", kind="mission_opened"), lease=lease)
    moved = store.move_lead_flag(current=current, successor=successor)
    assert is_ok(moved)
    assert moved.value.previous.lead is False
    assert moved.value.successor.lead is True
    assert moved.value.successor_ledger_opened is False
    retained = store.get(current.actor_id.value)
    assert retained is not None
    assert retained.ledger_ref == opened.value.ledger_ref
    assert len(retained.entries) == 1
    assert store.get(successor.actor_id.value) is None
    # Successor may open later while they hold the flag; the move itself did not.
    later = store.open_for_quant(moved.value.successor)
    assert is_ok(later)
    assert later.value.ledger_ref != retained.ledger_ref


def test_experiment_owns_one_ledger_authored_only_by_registering_task_holder() -> None:
    quant = _quant(desk=DeskSlug.ANALYSIS, slug="notebook")
    store = ExperimentLedgerStore()
    service = ExperimentSpecService(ledgers=store)
    lease = _dispatch(quant, task_id="task-exp-1", holder="agent-analyst-1")
    registered = service.register(
        _spec(),
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
    )
    assert is_ok(registered)
    first = registered.value.ledger
    again = store.open_for_experiment(
        experiment_id=first.experiment_id,
        owner=quant.actor_id,
        registering_lease=_dispatch(quant, task_id="task-exp-2", holder="agent-other"),
    )
    assert again is first
    appended = service.append_evidence(
        spec_fp1=first.experiment_id,
        dispatch_lease=lease,
        model_deployment_ref="deploy:analyst-v1",
        body={"note": "baseline"},
    )
    assert is_ok(appended)
    assert appended.value.entries[0].authored_by == "agent-analyst-1"
    other = service.append_evidence(
        spec_fp1=first.experiment_id,
        dispatch_lease=_dispatch(quant, task_id="task-exp-2", holder="agent-other"),
        model_deployment_ref="deploy:other",
        body={"note": "second author"},
    )
    assert is_refusal(other)
    assert other.context["field"] == "dispatch_lease"


def test_desk_views_fold_three_stores_and_create_no_fourth() -> None:
    lead = _quant()
    tasks = TaskLedgerStore()
    quants = QuantLedgerStore()
    experiments = ExperimentLedgerStore()
    views = DeskLedgerViews(
        task_ledgers=tasks,
        quant_ledgers=quants,
        experiment_ledgers=experiments,
    )
    views.remember_quant(lead)

    dispatch = _dispatch(lead, task_id="task-1", holder="agent-a")
    tasks.open_for_task("task-1", owner=lead.actor_id)
    tasks.grant(dispatch)
    assert is_ok(
        tasks.append(
            {
                "kind": "progress",
                "authored_by": {"agent": "agent-a", "quant": lead.actor_id.value},
                "model_deployment_ref": "deploy:workhorse",
            },
            lease=dispatch,
        )
    )

    assert is_ok(quants.open_for_quant(lead))
    qlease = _lease(lead, "agent-a")
    quants.grant(qlease)
    assert is_ok(quants.append(_entry(lead, agent="agent-a", kind="escalation"), lease=qlease))

    service = ExperimentSpecService(ledgers=experiments)
    registered = service.register(
        _spec(),
        dispatch_lease=dispatch,
        model_deployment_ref="deploy:workhorse",
    )
    assert is_ok(registered)
    assert is_ok(
        service.append_evidence(
            spec_fp1=registered.value.spec.spec_fp1,
            dispatch_lease=dispatch,
            model_deployment_ref="deploy:workhorse",
            body={"note": "notebook"},
        )
    )

    folded = views.derive(DeskSlug.RESEARCH)
    assert is_ok(folded)
    view = folded.value
    assert view.is_store is False
    assert view.fold_id == DESK_LEDGER_VIEW_FOLD_ID
    stores = {row.store for row in view.rows}
    assert stores == {"task_ledger", "quant_ledger", "experiment_ledger"}
    seqs = [row.journal_seq for row in view.rows]
    assert seqs == sorted(seqs)
    payload = view.to_payload()
    assert payload["is_store"] is False
    assert payload["ordering_key"] == "journal_seq"
    assert payload["source_stream"] == "ledger.appended"
    assert payload["gap_0082"] == "deferred"

    fourth = views.declare_store("research_ledger")
    assert is_refusal(fourth)
    assert fourth.context["field"] == "store"
    also = refuse_fourth_ledger_store("mission_ledger")
    assert is_refusal(also)
    report = views.mission_report("mission-1")
    assert is_refusal(report)
    assert report.context["gap"] == GAP_0082_DEFERRED
    via_flag = views.derive(DeskSlug.RESEARCH, mission_report=True)
    assert is_refusal(via_flag)
    trading = views.derive(DeskSlug.TRADING)
    assert is_ok(trading)
    assert trading.value.rows == ()


def test_reference_usage_example_runs() -> None:
    path = (
        Path(__file__).resolve().parents[1] / "examples" / "quant_experiment_desk_ledger_usage.py"
    )
    namespace = runpy.run_path(str(path))
    namespace["main"]()
