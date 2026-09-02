"""Story 28.6 — named QA-debt closure matrix and the permanent battery."""

from __future__ import annotations

import json
from dataclasses import replace
from typing import TypeVar

from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmn.host import (
    FACTORY_GATES,
    FOUNDATION_DEBT_IDS,
    MUTATION_MONEY_PATH_MODULES,
    MUTMUT_IS_FACTORY_GATE,
    NODE_QA_DEBT_IDS,
    PERMANENT_BATTERY_ITEMS,
    QA_DEBT_MATRIX_CLASS,
    QA_DEBT_MATRIX_SURFACE,
    ZERO_CLASSIFIED_MUTANT_FAILS_CLOSED,
    QaDebtGateInputs,
    evaluate_mutation_verdict,
    refuse_foundation_reclassified,
    refuse_inherited_or_implicit,
    refuse_missing_qa_debt_link,
    refuse_zero_classified_mutants,
    run_paper_milestone_qa_debt_gate,
)
from qmn.host.qa_debt_matrix import NODE_QA_DEBT_ROWS, workspace_root

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def test_surface_markers_pin_factory_gates_and_foundation() -> None:
    assert QA_DEBT_MATRIX_SURFACE == "qmn.host.qa_debt_matrix"
    assert QA_DEBT_MATRIX_CLASS == "paper-milestone-qa-debt-closure-matrix"
    assert MUTMUT_IS_FACTORY_GATE is False
    assert ZERO_CLASSIFIED_MUTANT_FAILS_CLOSED is True
    assert FACTORY_GATES == ("ruff", "pyright-strict", "pytest")
    assert "mutmut" not in FACTORY_GATES
    assert NODE_QA_DEBT_IDS == (
        "QMX-F045",
        "QMX-F046",
        "QMX-F062",
        "QMX-F063",
        "QMX-F064",
        "QMX-F067",
        "QMX-F068",
        "QMX-F069",
        "QMX-F102",
        "D008",
        "D010",
        "E15-F01",
        "E15-F02",
        "E15-F03",
        "E7-R28",
        "E9-F04",
        "E12-F01",
        "E12-F04",
        "E12-F05",
    )
    assert "QMX-F030" in FOUNDATION_DEBT_IDS
    assert "QMX-F085" in FOUNDATION_DEBT_IDS
    assert "E11-F04" in FOUNDATION_DEBT_IDS
    assert set(FOUNDATION_DEBT_IDS).isdisjoint(NODE_QA_DEBT_IDS)


def test_production_matrix_links_every_named_id() -> None:
    report = _ok(run_paper_milestone_qa_debt_gate())
    assert report.ok is True
    assert tuple(row.debt_id for row in report.rows) == NODE_QA_DEBT_IDS
    assert report.mutmut_is_factory_gate is False
    assert report.factory_gates == FACTORY_GATES
    assert report.foundation_debt == FOUNDATION_DEBT_IDS
    by_id = {row.debt_id: row for row in report.rows}
    for debt_id, row in by_id.items():
        assert row.inherited is False, debt_id
        assert row.implicit is False, debt_id
        assert row.status in {"closed", "linked"}, debt_id
        assert row.story, debt_id
        assert row.evidence, debt_id
        for relative in row.evidence:
            path = workspace_root().joinpath(*relative.split("/"))
            assert path.exists(), relative
    e9 = by_id["E9-F04"]
    assert e9.status == "closed"
    assert e9.closure_owner == "28.7"
    assert e9.story == "28.7"
    for debt_id, row in by_id.items():
        assert row.status == "closed", debt_id


def test_matrix_is_machine_readable_json() -> None:
    report = _ok(run_paper_milestone_qa_debt_gate())
    payload = json.loads(report.to_json())
    assert payload["class"] == QA_DEBT_MATRIX_CLASS
    assert payload["ok"] is True
    assert payload["debt_ids"] == list(NODE_QA_DEBT_IDS)
    assert payload["fingerprint"] == report.fingerprint.value
    assert payload["mutmut_is_factory_gate"] is False
    assert payload["mutation"]["zero_classified_fails_closed"] is True
    assert payload["mutation"]["ran_in_factory"] is False
    assert payload["mutation"]["status"] == "configured"
    mapped = dict(report.as_mapping())
    assert mapped["fingerprint"] == report.fingerprint.value
    round_trip = json.loads(json.dumps(mapped, sort_keys=True))
    assert round_trip["rows"][0]["debt_id"] == "QMX-F045"


def test_identical_inputs_fingerprint_identically() -> None:
    first = _ok(run_paper_milestone_qa_debt_gate())
    second = _ok(run_paper_milestone_qa_debt_gate())
    assert first.fingerprint == second.fingerprint


def test_missing_link_fails_rather_than_inheriting() -> None:
    rows = tuple(
        replace(row, evidence=()) if row.debt_id == "QMX-F045" else row for row in NODE_QA_DEBT_ROWS
    )
    refused = _refusal(run_paper_milestone_qa_debt_gate(QaDebtGateInputs(rows=rows)))
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "qa_debt.missing_link"
    assert refused.context["debt_id"] == "QMX-F045"
    dropped = tuple(row for row in NODE_QA_DEBT_ROWS if row.debt_id != "D008")
    missing = _refusal(run_paper_milestone_qa_debt_gate(QaDebtGateInputs(rows=dropped)))
    assert missing.context["failure_id"] == "qa_debt.missing_link"
    assert missing.context["missing"] == ("D008",)
    explicit = refuse_missing_qa_debt_link()
    assert explicit.context["failure_id"] == "qa_debt.missing_link"


def test_inherited_or_implicit_coverage_is_refused() -> None:
    inherited = _refusal(run_paper_milestone_qa_debt_gate(QaDebtGateInputs(mark_inherited=True)))
    assert inherited.context["failure_id"] == "qa_debt.inherited_or_implicit"
    implicit = _refusal(run_paper_milestone_qa_debt_gate(QaDebtGateInputs(mark_implicit=True)))
    assert implicit.context["failure_id"] == "qa_debt.inherited_or_implicit"
    rows = tuple(
        replace(row, inherited=True) if row.debt_id == "QMX-F062" else row
        for row in NODE_QA_DEBT_ROWS
    )
    row_flag = _refusal(run_paper_milestone_qa_debt_gate(QaDebtGateInputs(rows=rows)))
    assert row_flag.context["failure_id"] == "qa_debt.inherited_or_implicit"
    status = tuple(
        replace(row, status="inherited") if row.debt_id == "QMX-F063" else row
        for row in NODE_QA_DEBT_ROWS
    )
    status_flag = _refusal(run_paper_milestone_qa_debt_gate(QaDebtGateInputs(rows=status)))
    assert status_flag.context["failure_id"] == "qa_debt.inherited_or_implicit"
    assert refuse_inherited_or_implicit().context["failure_id"] == "qa_debt.inherited_or_implicit"


def test_foundation_debt_is_not_reclassified() -> None:
    refused = _refusal(
        run_paper_milestone_qa_debt_gate(QaDebtGateInputs(reclassify_foundation=True))
    )
    assert refused.context["failure_id"] == "qa_debt.foundation_reclassified"
    extra = (
        *NODE_QA_DEBT_ROWS,
        replace(NODE_QA_DEBT_ROWS[0], debt_id="QMX-F030", story="1.x"),
    )
    reclass = _refusal(run_paper_milestone_qa_debt_gate(QaDebtGateInputs(rows=extra)))
    assert reclass.context["failure_id"] == "qa_debt.foundation_reclassified"
    assert refuse_foundation_reclassified().context["failure_id"] == (
        "qa_debt.foundation_reclassified"
    )


def test_permanent_battery_evidence_exists_and_excludes_mutmut() -> None:
    report = _ok(run_paper_milestone_qa_debt_gate())
    names = tuple(item.name for item in report.battery)
    assert names == tuple(item.name for item in PERMANENT_BATTERY_ITEMS)
    for required in (
        "ruff",
        "pyright-strict",
        "pytest",
        "coverage",
        "isolated-contract-suites",
        "secret-scan",
        "money-path-scan",
        "ambient-scan",
        "isolated-build",
        "mock-data-scan",
        "skylos-iac",
        "vulture",
        "qa-requirements-first",
        "ubuntu-24.04",
        "systemd-check-mode",
        "conformance",
        "replay",
        "failure-register",
        "scenario-gates",
    ):
        assert required in names
    factory = {item.name for item in report.battery if item.factory_gate}
    assert factory == set(FACTORY_GATES)
    assert "mutmut" not in names
    for item in report.battery:
        for relative in item.evidence:
            path = workspace_root().joinpath(*relative.split("/"))
            assert path.exists(), relative


def test_mutation_roster_covers_money_path_and_fails_closed_on_zero() -> None:
    report = _ok(run_paper_milestone_qa_debt_gate())
    assert dict(report.mutation.modules) == dict(MUTATION_MONEY_PATH_MODULES)
    assert set(MUTATION_MONEY_PATH_MODULES) == {
        "door_wiring",
        "command_mint",
        "equity_derivation",
        "drift_decomposition",
        "sizing",
        "virtual_ledger_folds",
    }
    for relative in MUTATION_MONEY_PATH_MODULES.values():
        assert workspace_root().joinpath(*relative.split("/")).is_file(), relative
    zero = _refusal(
        run_paper_milestone_qa_debt_gate(QaDebtGateInputs(mutation_killed=0, mutation_survived=0))
    )
    assert zero.context["failure_id"] == "qa_debt.mutation_zero"
    assert refuse_zero_classified_mutants().context["failure_id"] == "qa_debt.mutation_zero"
    untriaged = _refusal(
        run_paper_milestone_qa_debt_gate(QaDebtGateInputs(mutation_killed=10, mutation_survived=2))
    )
    assert untriaged.context["failure_id"] == "qa_debt.mutation_untriaged"
    triaged = _ok(
        run_paper_milestone_qa_debt_gate(
            QaDebtGateInputs(
                mutation_killed=10,
                mutation_survived=2,
                triaged_survivors=("surv-1", "surv-2"),
            )
        )
    )
    assert triaged.mutation.status == "pass"
    assert triaged.mutation.ran_in_factory is False
    direct = _ok(
        evaluate_mutation_verdict(
            classified_killed=4,
            classified_survived=1,
            triaged_survivors=("surv-1",),
        )
    )
    assert direct == "pass"
    closed = _refusal(evaluate_mutation_verdict(classified_killed=0, classified_survived=0))
    assert closed.context["failure_id"] == "qa_debt.mutation_zero"
