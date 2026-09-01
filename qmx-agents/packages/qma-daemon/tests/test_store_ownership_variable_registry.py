"""Story 42.4 — store-class ownership and governed variable registry (FR-Q26, FR-Q36)."""

from __future__ import annotations

from pathlib import Path

import pytest
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary import (
    GovernedAct,
    GovernedActTarget,
    RefinementEditKind,
    VariableEditability,
    VariableScope,
    VocabularyError,
    validate_governed_act,
)
from qma.daemon import (
    AuthoritativeJournal,
    GovernedVariableRegistry,
    PersistenceSubstrate,
    ProposalGate,
    StoreOwnershipRegistry,
)
from qma.daemon.journal import (
    DURABLE_POSTURE_CLASSES,
    EIGHT_STORE_CLASSES,
    INVOCATION_ONLY_CLASSES,
    STORE_BACKUP_CADENCE_KEY,
    STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY,
    STORE_LIFECYCLE_KEYS,
    STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY,
    VARIABLE_SET_EVENT,
    PersistenceClass,
    VariableRow,
    cite_store_lifecycle_key,
    has_variable_edit_kind,
)
from qma.daemon.staging import (
    AGENT_DIRECT_DEFINITION_EXCEPTION,
    accept_definition_store_proposal,
    register_mission_scoped_hook_exception,
)
from qmf.core import (
    DataDrivenClock,
    Instant,
    RefusalCategory,
    is_ok,
    is_refusal,
)


def _test_clock(*, boot: str = "boot-42-4", n: int = 64) -> DataDrivenClock:
    base = 1_720_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(n))
    monos = tuple(i * 1_000 for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=monos)


def _open_journal(tmp_path: Path, *, boot: str = "boot-42-4") -> tuple[
    PersistenceSubstrate, AuthoritativeJournal
]:
    substrate_result = PersistenceSubstrate.open(
        tmp_path, machine="test-host", boot_epoch_id=boot
    )
    assert is_ok(substrate_result), substrate_result
    substrate = substrate_result.value
    journal_result = AuthoritativeJournal.bind(substrate, clock=_test_clock(boot=boot))
    assert is_ok(journal_result), journal_result
    return substrate, journal_result.value


# --- FR-Q26 store-class ownership -------------------------------------------------


def test_eight_store_classes_each_have_writer_crossing_retention() -> None:
    registry = StoreOwnershipRegistry()
    registered = registry.register_defaults()
    assert set(registered) == EIGHT_STORE_CLASSES
    assert EIGHT_STORE_CLASSES == {
        "journal",
        "ledger",
        "memory",
        "knowledge",
        "artifacts",
        "context",
        "telemetry",
        "staging",
    }
    complete = registry.assert_complete()
    assert is_ok(complete)
    for name, rule in complete.value.items():
        assert rule.writer
        assert rule.crossing_rule
        assert rule.retention_rule
        assert rule.store_class.value == name


def test_context_is_invocation_only_and_durable_posture_holds() -> None:
    registry = StoreOwnershipRegistry()
    registry.register_defaults()
    context = registry.get(PersistenceClass.CONTEXT.value)
    assert is_ok(context)
    assert context.value.is_invocation_only
    assert PersistenceClass.CONTEXT.value in INVOCATION_ONLY_CLASSES
    assert {
        "journal",
        "ledger",
        "artifacts",
        "staging",
        "ledger_quarantine",
    } <= DURABLE_POSTURE_CLASSES
    assert registry.ledger_quarantine_durable is True
    for name in ("journal", "ledger", "artifacts", "staging"):
        rule = registry.get(name)
        assert is_ok(rule)
        assert rule.value.is_durable


def test_unknown_store_class_refused() -> None:
    registry = StoreOwnershipRegistry()
    refused = registry.get("invented_store")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION


# --- FR-Q26 RefinementProposal boundary -------------------------------------------


def test_definition_store_change_enters_only_as_refinement_proposal() -> None:
    gate = ProposalGate()
    accepted = gate.accept(
        summary="narrow toolset",
        rationale="mission needs fewer tools",
        edits=[
            {
                "kind": "toolset",
                "operation": "update",
                "id": "research.readonly",
                "content": {"tools": ["market.read"]},
            }
        ],
        expected_outcome="toolset narrowed",
    )
    assert is_ok(accepted)
    assert accepted.value.state.value == "staged"
    assert accepted.value.edits[0].kind is RefinementEditKind.TOOLSET


def test_proposal_is_applied_never_promoted() -> None:
    gate = ProposalGate()
    accepted = gate.accept(
        summary="add skill",
        rationale="document a procedure",
        edits=[
            {
                "kind": "skill",
                "operation": "create",
                "id": "skill.review",
                "content": {"body": "review checklist"},
            }
        ],
        expected_outcome="skill available",
        proposal_id="prop-1",
    )
    assert is_ok(accepted)

    applied = gate.apply("prop-1", principal_class="operator")
    assert is_ok(applied)
    assert applied.value.state.value == "applied"
    assert applied.value.applied_snapshots is not None

    validate_governed_act(GovernedAct.APPLY, GovernedActTarget.REFINEMENT_PROPOSAL)
    with pytest.raises(VocabularyError):
        validate_governed_act(GovernedAct.PROMOTE, GovernedActTarget.REFINEMENT_PROPOSAL)
    promote = gate.promote_refused("prop-1")
    assert is_refusal(promote)
    assert "never promoted" in str(promote.context.get("reason", ""))


def test_machine_cannot_apply_proposal() -> None:
    gate = ProposalGate()
    accepted = gate.accept(
        summary="hook",
        rationale="observe",
        edits=[
            {
                "kind": "hook",
                "operation": "create",
                "id": "hook.observe",
                "content": {"phase": "before_tool"},
            }
        ],
        expected_outcome="hook staged",
        proposal_id="prop-machine",
    )
    assert is_ok(accepted)
    refused = gate.apply("prop-machine", principal_class="machine")
    assert is_refusal(refused)
    assert OperatorPrincipalRequired.matches(refused)


def test_sole_direct_agent_exception_is_mission_scoped_hook() -> None:
    ok = register_mission_scoped_hook_exception(
        mission_id="mission-1",
        template_id="tpl.observe_deny",
        observe_or_deny_only=True,
        via_hook=AGENT_DIRECT_DEFINITION_EXCEPTION,
    )
    assert is_ok(ok)
    assert ok.value["disposed_with"] == "mission"
    assert ok.value["durable_only_via"] == "refinement_proposal"

    bad_via = register_mission_scoped_hook_exception(
        mission_id="mission-1",
        template_id="tpl.observe_deny",
        observe_or_deny_only=True,
        via_hook="direct_definition_write",
    )
    assert is_refusal(bad_via)

    not_observe_deny = register_mission_scoped_hook_exception(
        mission_id="mission-1",
        template_id="tpl.mutate",
        observe_or_deny_only=False,
    )
    assert is_refusal(not_observe_deny)


def test_variable_edit_kind_refused_on_proposal() -> None:
    refused = accept_definition_store_proposal(
        summary="set var",
        rationale="no",
        edits=[{"kind": "variable", "operation": "update", "id": "hook.timeout_before"}],
        expected_outcome="blocked",
    )
    assert is_refusal(refused)
    assert "no variable edit kind" in str(refused.context.get("reason", ""))


# --- FR-Q36 variable registry -----------------------------------------------------


def test_builtin_rows_declare_scope_type_units_default_editability_home() -> None:
    registry = GovernedVariableRegistry.with_builtins()
    rows = registry.rows()
    assert "store.backup_cadence" in rows
    assert "quant.quiet_hours" in rows
    assert "rlm.depth_cap" in rows
    for row in rows.values():
        assert row.name
        assert row.owning_subsystem
        assert isinstance(row.scope, VariableScope)
        assert row.scope in VariableScope
        assert row.value_type
        assert row.editability in VariableEditability
        assert row.home
        assert "default" in row.to_dict()


def test_closed_variable_scope_vocabulary() -> None:
    registry = GovernedVariableRegistry()
    ok = registry.register(
        {
            "name": "plugin.example_cap",
            "owning_subsystem": "COMP-QMA-DAEMON",
            "scope": "plugin",
            "type": "count",
            "units": "count",
            "default": 1,
            "editability": "ui-editable",
            "home": "registry",
        }
    )
    assert is_ok(ok)
    bad = registry.register(
        {
            "name": "bad.scope",
            "owning_subsystem": "COMP-QMA-DAEMON",
            "scope": "deployment",
            "type": "count",
            "units": "count",
            "default": 1,
            "editability": "ui-editable",
            "home": "registry",
        }
    )
    assert is_refusal(bad)


def test_store_lifecycle_cited_by_registry_key_never_copied() -> None:
    assert STORE_LIFECYCLE_KEYS == {
        STORE_BACKUP_CADENCE_KEY,
        STORE_SAMPLE_RESTORE_TEST_CADENCE_KEY,
        STORE_FULL_RESTORE_REHEARSAL_CADENCE_KEY,
    }
    for key in STORE_LIFECYCLE_KEYS:
        cited = cite_store_lifecycle_key(key)
        assert is_ok(cited)
        assert cited.value == key
        assert cited.value.startswith("registry:")
    # Code must not embed the spine cadence value "nightly".
    import qma.daemon.journal.variables as variables_mod

    source = Path(variables_mod.__file__).read_text(encoding="utf-8")
    assert "nightly" not in source
    refused = cite_store_lifecycle_key("store.invented_cadence")
    assert is_refusal(refused)


def test_operator_variable_set_records_journal_event(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        registry = GovernedVariableRegistry.with_builtins()
        result = registry.variable_set(
            "rlm.depth_cap",
            1,
            principal_class="operator",
            journal=journal,
            scope_path=[{"kind": "desk", "id": "research"}],
        )
        assert is_ok(result)
        assert result.value.value == 1
        assert result.value.previous == 2
        assert result.value.journal.record.event == VARIABLE_SET_EVENT
        assert result.value.journal.record.journal_seq == 1

        rows = journal.read_all()
        assert is_ok(rows)
        assert rows.value[0]["event"] == "variable.set"
        assert rows.value[0]["payload"]["name"] == "rlm.depth_cap"
        assert rows.value[0]["payload"]["value"] == 1
    finally:
        journal.close()
        substrate.close()


def test_variable_set_refuses_uneditable_and_record_homed(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        registry = GovernedVariableRegistry.with_builtins()
        uneditable = registry.register(
            VariableRow(
                name="const.example",
                owning_subsystem="COMP-QMA-DAEMON",
                scope=VariableScope.GLOBAL,
                value_type="count",
                units="count",
                default=7,
                editability=VariableEditability.UNEDITABLE,
                home="registry",
            )
        )
        assert is_ok(uneditable)

        refused_uneditable = registry.variable_set(
            "const.example",
            9,
            principal_class="operator",
            journal=journal,
        )
        assert is_refusal(refused_uneditable)
        assert "uneditable" in str(refused_uneditable.context.get("reason", ""))

        refused_record = registry.variable_set(
            "quant.quiet_hours",
            "00:00-06:00",
            principal_class="operator",
            journal=journal,
        )
        assert is_refusal(refused_record)
        assert "record-homed" in str(refused_record.context.get("reason", ""))
    finally:
        journal.close()
        substrate.close()


def test_machine_and_agent_routes_cannot_set_variables(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        registry = GovernedVariableRegistry.with_builtins()
        machine = registry.variable_set(
            "rlm.depth_cap",
            1,
            principal_class="machine",
            journal=journal,
        )
        assert is_refusal(machine)
        assert OperatorPrincipalRequired.matches(machine)

        for via in ("agent", "hook", "role", "mission"):
            refused = registry.refuse_non_operator_route(
                "rlm.depth_cap",
                1,
                principal_class="machine",
                via=via,
            )
            assert is_refusal(refused)
            assert "no variable edit kind" in str(refused.context.get("reason", ""))

        assert has_variable_edit_kind() is False
        assert "variable" not in {kind.value for kind in RefinementEditKind}
    finally:
        journal.close()
        substrate.close()
