"""L3 acceptance — Story 19.3: suppression and veto accounting.

Requirements R14-R17. Tallies fold ONLY the run's own CT-13 journal streams,
keyed by (authority, reason) and by door; quiet runs still emit explicit zero
keys; an unresolvable authority/reason is a typed refusal, never bucketed.
"""

from __future__ import annotations

import pytest

from conftest import config, journal_event, mint_args, ok

from qmf.core.exact import UnitKind
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, is_refusal
from qmf.data.journal import DecisionOutcome, JournalEventType
from qmf.risk.control_action import AuthorityKind
from qmb.results.accounting import (
    SUPPRESSION_REASON_CLASSES,
    TALLY_FIELD_GROUP,
    TALLY_UNIT_KIND,
    VETO_DOOR_IDENTITIES,
    assemble_suppression_and_veto_accounting,
)
from qmb.results.ct32 import mint_run_performance_result
from qmb.results.measures import MEASURE_IDENTITIES


# --- A11: tallies fold ONLY the run's own CT-13 journal streams [R14] P1 -----


def test_a11_tallies_count_journal_events_by_authority_reason_and_door() -> None:
    events = (
        journal_event(sequence=0, outcome=DecisionOutcome.REFUSED_BY_DOOR,
                      payload={"refusing_door": "control-window"}),
        journal_event(sequence=1, outcome=DecisionOutcome.REFUSED_BY_DOOR,
                      payload={"refusing_door": "control-window"}),
        journal_event(sequence=2, outcome=DecisionOutcome.REFUSED_BY_DOOR,
                      payload={"refusing_door": "sqs"}),
        journal_event(sequence=3, outcome=DecisionOutcome.SUPPRESSED,
                      payload={"suppressing_authority": AuthorityKind.OPERATOR.value,
                               "reason_class": "conflict-higher-rank-wins"}),
        journal_event(sequence=4, outcome=DecisionOutcome.AUTHORIZED, payload={"bot": "b1"}),
    )
    suppressions, vetoes = ok(assemble_suppression_and_veto_accounting(events))
    by_supp = {(row.authority, row.reason_class): row.count for row in suppressions}
    by_veto = {row.door_identity: row.count for row in vetoes}

    assert by_veto["control-window"] == 2
    assert by_veto["sqs"] == 1
    assert by_veto["bench"] == 0  # a door that never fired is still an explicit key
    assert by_supp[(AuthorityKind.OPERATOR, "conflict-higher-rank-wins")] == 1
    # an AUTHORIZED decision is not a suppression
    assert by_supp[(AuthorityKind.OPERATOR, "collapse-same-mechanical-command")] == 0


def test_a11_a_parallel_bespoke_log_cannot_move_the_tally() -> None:
    # Counter-case: a non-CT-13 log (plain dicts) is refused, so a tally can never
    # be sourced from a parallel bespoke log.
    bespoke = ({"authority": "operator", "reason": "x", "count": 5},)
    refused = assemble_suppression_and_veto_accounting(bespoke)
    assert is_refusal(refused)
    assert refused.context["field"] == "journal_events"


def test_a11_a_cross_world_event_is_refused() -> None:
    live = journal_event(sequence=0, outcome=DecisionOutcome.REFUSED_BY_DOOR,
                         payload={"refusing_door": "sqs"}, world=World.LIVE)
    refused = assemble_suppression_and_veto_accounting((live,), world=World.REPLAY)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "world"


# --- A12: quiet run emits explicit zero keys, never omitted [R15] P1 ---------


def test_a12_quiet_run_emits_full_roster_at_zero() -> None:
    suppressions, vetoes = ok(assemble_suppression_and_veto_accounting())
    expected_supp = {
        (authority.value, reason)
        for authority in AuthorityKind
        for reason in SUPPRESSION_REASON_CLASSES
    }
    assert {(r.authority.value, r.reason_class) for r in suppressions} == expected_supp
    assert {r.door_identity for r in vetoes} == set(VETO_DOOR_IDENTITIES)
    assert all(r.count == 0 for r in suppressions)
    assert all(r.count == 0 for r in vetoes)


# --- A13: counts carry `count`; distinct field group from measures [R16] P1 --


def test_a13_counts_are_count_kind_and_a_distinct_field_group() -> None:
    suppressions, vetoes = ok(assemble_suppression_and_veto_accounting())
    assert TALLY_UNIT_KIND is UnitKind.COUNT
    assert TALLY_FIELD_GROUP == "control-accounting"
    for row in (*suppressions, *vetoes):
        assert row.fp1_identity()["unit_kind"] == UnitKind.COUNT.value
    # the control tallies are never folded into the returns/trade measure set
    joined = " ".join(MEASURE_IDENTITIES)
    assert "suppression" not in joined and "veto" not in joined


def test_a13_artifact_keeps_tallies_separate_from_measure_set() -> None:
    artifact = ok(mint_run_performance_result(**mint_args(config())))
    body = artifact.fp1_identity()
    assert "measure_set" in body
    assert "suppression_accounting" in body
    assert "veto_accounting" in body
    measure_ids = {row["measure_identity"] for row in body["measure_set"]}
    assert not any("veto" in m or "suppress" in m for m in measure_ids)


# --- A14: unresolvable authority/reason is a typed refusal [R17] P1 ----------


def test_a14_unresolvable_authority_is_refused_not_bucketed() -> None:
    bad = journal_event(outcome=DecisionOutcome.SUPPRESSED,
                        payload={"suppressing_authority": "kill-switch", "reason_class": "x"})
    refused = assemble_suppression_and_veto_accounting((bad,))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "suppressing_authority"


def test_a14_missing_reason_class_is_refused_not_bucketed() -> None:
    missing = journal_event(outcome=DecisionOutcome.SUPPRESSED,
                            payload={"suppressing_authority": AuthorityKind.OPERATOR.value})
    refused = assemble_suppression_and_veto_accounting((missing,))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "reason_class"


def test_a14_unresolvable_door_is_refused_not_dropped() -> None:
    # RE-POINTED to Epic 19's own door folder (was a probe of
    # qmf.data.journal.JournalEvent.try_create — another epic's constructor law).
    # A present-but-unrostered refusing-door, outside the ratified
    # VETO_DOOR_IDENTITIES spine roster (AD-36/DEC-0150), is a typed refusal on
    # the accounting surface — never silently bucketed into a brand-new tally key.
    unrostered = journal_event(
        outcome=DecisionOutcome.REFUSED_BY_DOOR, payload={"refusing_door": "mystery-door"}
    )
    refused = assemble_suppression_and_veto_accounting((unrostered,))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "refusing_door"
    assert "mystery-door" not in VETO_DOOR_IDENTITIES


def test_a14_unrostered_reason_class_is_refused_not_bucketed() -> None:
    # The sibling hole one level over: a resolvable authority carrying a
    # present-but-unrostered reason class, outside the closed
    # SUPPRESSION_REASON_CLASSES roster (DEC-0151), is a typed refusal — never
    # folded into a brand-new tally key. AC19.3 names "authority OR reason".
    unrostered = journal_event(
        outcome=DecisionOutcome.SUPPRESSED,
        payload={
            "suppressing_authority": AuthorityKind.OPERATOR.value,
            "reason_class": "mystery-reason",
        },
    )
    refused = assemble_suppression_and_veto_accounting((unrostered,))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "reason_class"
    assert "mystery-reason" not in SUPPRESSION_REASON_CLASSES


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
