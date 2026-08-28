"""Story 19.3 — suppression and veto accounting from CT-13 journals."""

from __future__ import annotations

from typing import TypeVar

from qmb.config import ResolvedRunConfig
from qmb.doors import api
from qmb.results import (
    MEASURE_IDENTITIES,
    SUPPRESSION_REASON_CLASSES,
    TALLY_FIELD_GROUP,
    TALLY_UNIT_KIND,
    VETO_DOOR_IDENTITIES,
    assemble_suppression_and_veto_accounting,
    mint_run_performance_result,
    result_identity,
)
from qmb.runloop import STREAM_SET_KEY, SilentSliceHandler, SliceObservation, run
from qmf.core.chrono import Instant, WriterId
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.data.journal import DecisionOutcome, JournalEvent, JournalEventType
from qmf.risk.control_action import AuthorityKind
from qmf.risk.performance import SuppressionCount, VetoCount

import qmb

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _writer() -> WriterId:
    return _ok(WriterId.try_create("qmb-replay", "risk", "decisions", "boot-1"))


def _event(
    *,
    event_type: object = JournalEventType.DECISION,
    sequence: int = 0,
    payload: dict[str, object] | None = None,
    outcome: object | None = None,
    world: object = World.REPLAY,
) -> JournalEvent:
    return _ok(
        JournalEvent.try_create(
            event_type=event_type,
            writer=_writer(),
            sequence=sequence,
            instant=_NS + sequence,
            world=world,
            payload=payload,
            outcome=outcome,
        )
    )


def _config() -> ResolvedRunConfig:
    stamp = _ok(fingerprint({"n": "accounting-cfg"}))
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def _obs(stream_id: str = "eurusd", ns: int = _NS) -> SliceObservation:
    return _ok(SliceObservation.try_create(stream_id, _instant(ns), True))


def test_quiet_run_emits_explicit_zero_keys_never_omitted() -> None:
    suppressions, vetoes = _ok(assemble_suppression_and_veto_accounting())
    expected_suppression = {
        (authority.value, reason)
        for authority in AuthorityKind
        for reason in SUPPRESSION_REASON_CLASSES
    }
    assert {(row.authority.value, row.reason_class) for row in suppressions} == expected_suppression
    assert {row.door_identity for row in vetoes} == set(VETO_DOOR_IDENTITIES)
    assert all(row.count == 0 for row in suppressions)
    assert all(row.count == 0 for row in vetoes)
    assert all(row.fp1_identity()["unit_kind"] == UnitKind.COUNT.value for row in suppressions)
    assert all(row.fp1_identity()["unit_kind"] == UnitKind.COUNT.value for row in vetoes)
    outcome = _ok(run(slices=((_obs(),),), config=_config(), handler=SilentSliceHandler()))
    artifact = outcome.performance_result
    assert artifact is not None
    assert {(row.authority.value, row.reason_class) for row in artifact.suppression_accounting} == (
        expected_suppression
    )
    assert {row.door_identity for row in artifact.veto_accounting} == set(VETO_DOOR_IDENTITIES)
    assert all(row.count == 0 for row in artifact.suppression_accounting)
    assert all(row.count == 0 for row in artifact.veto_accounting)


def test_tallies_fold_only_ct13_journals_and_stay_off_measure_set() -> None:
    veto = _event(
        sequence=0,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        payload={"refusing_door": "control-window"},
    )
    veto_again = _event(
        sequence=1,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        payload={"refusing_door": "control-window"},
    )
    extra_door = _event(
        sequence=2,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        payload={"refusing_door": "budget"},
    )
    suppressed = _event(
        sequence=3,
        outcome=DecisionOutcome.SUPPRESSED,
        payload={
            "suppressing_authority": AuthorityKind.OPERATOR.value,
            "reason_class": "conflict-higher-rank-wins",
        },
    )
    extra_reason = _event(
        sequence=4,
        outcome=DecisionOutcome.SUPPRESSED,
        payload={
            "suppressing_authority": AuthorityKind.BOOK_POLICY.value,
            "reason_class": "collapse-same-mechanical-command",
        },
    )
    control = _event(
        event_type=JournalEventType.CONTROL_ACTION,
        sequence=5,
        payload={
            "subtype": "suppressed",
            "authority_kind": AuthorityKind.PROTECTION_AUTHORITY.value,
            "reason_class": "collapse-same-mechanical-command",
        },
    )
    authorized = _event(sequence=6, outcome=DecisionOutcome.AUTHORIZED, payload={"bot": "b1"})
    suppressions, vetoes = _ok(
        assemble_suppression_and_veto_accounting(
            ((veto, veto_again, extra_door), (suppressed, extra_reason, control, authorized))
        )
    )
    by_suppression = {(row.authority, row.reason_class): row.count for row in suppressions}
    by_veto = {row.door_identity: row.count for row in vetoes}
    assert by_suppression[(AuthorityKind.OPERATOR, "conflict-higher-rank-wins")] == 1
    assert by_suppression[(AuthorityKind.BOOK_POLICY, "collapse-same-mechanical-command")] == 1
    protection = (AuthorityKind.PROTECTION_AUTHORITY, "collapse-same-mechanical-command")
    assert by_suppression[protection] == 1
    assert by_suppression[(AuthorityKind.OPERATOR, "collapse-same-mechanical-command")] == 0
    assert by_veto["control-window"] == 2
    assert by_veto["budget"] == 1
    assert by_veto["sqs"] == 0
    assert "budget" in VETO_DOOR_IDENTITIES
    minted = _ok(
        mint_run_performance_result(
            _config(),
            evidence_range=_ok(run(slices=((_obs(),),), stream_set=("eurusd",))).evidence_range,
            stream_order=("eurusd",),
            slice_count=1,
            filled_count=0,
            resting_count=0,
            data_points_processed=1,
            outcome_identity={"class": "event-slice-loop-outcome"},
            journal_events=(veto, extra_door, suppressed),
        )
    )
    assert TALLY_FIELD_GROUP == "control-accounting"
    assert TALLY_UNIT_KIND is UnitKind.COUNT
    assert result_identity()["tally_field_group"] == TALLY_FIELD_GROUP
    assert result_identity()["tally_unit_kind"] == UnitKind.COUNT.value
    measure_ids = [row.measure_identity for row in minted.measure_set]
    assert measure_ids == list(MEASURE_IDENTITIES)
    assert "suppression" not in " ".join(measure_ids)
    assert "veto" not in " ".join(measure_ids)
    assert all(
        row.fp1_identity()["unit_kind"] == UnitKind.COUNT.value
        for row in minted.suppression_accounting
    )
    assert all(
        row.fp1_identity()["unit_kind"] == UnitKind.COUNT.value for row in minted.veto_accounting
    )


def test_unresolvable_authority_or_reason_is_typed_refusal_never_bucketed() -> None:
    bad_authority = _event(
        outcome=DecisionOutcome.SUPPRESSED,
        payload={"suppressing_authority": "kill-switch", "reason_class": "kill_switch"},
    )
    refused_authority = assemble_suppression_and_veto_accounting((bad_authority,))
    assert is_refusal(refused_authority)
    assert refused_authority.category is RefusalCategory.INVALID_INPUT
    assert refused_authority.context["field"] == "suppressing_authority"
    missing_reason = _event(
        sequence=1,
        outcome=DecisionOutcome.SUPPRESSED,
        payload={"suppressing_authority": AuthorityKind.OPERATOR.value},
    )
    refused_reason = assemble_suppression_and_veto_accounting((missing_reason,))
    assert is_refusal(refused_reason)
    assert refused_reason.category is RefusalCategory.INVALID_INPUT
    assert refused_reason.context["field"] == "reason_class"
    parallel = assemble_suppression_and_veto_accounting(
        ({"authority": "operator", "reason": "other", "count": 1},)
    )
    assert is_refusal(parallel)
    assert parallel.category is RefusalCategory.INVALID_INPUT
    assert parallel.context["field"] == "journal_events"
    live = _event(
        sequence=2,
        outcome=DecisionOutcome.REFUSED_BY_DOOR,
        payload={"refusing_door": "sqs"},
        world=World.LIVE,
    )
    crossed = assemble_suppression_and_veto_accounting((live,), world=World.REPLAY)
    assert is_refusal(crossed)
    assert crossed.category is RefusalCategory.POLICY_REJECTION
    assert crossed.context["field"] == "world"
    minted = mint_run_performance_result(
        _config(),
        evidence_range=_ok(run(slices=((_obs(),),), stream_set=("eurusd",))).evidence_range,
        stream_order=("eurusd",),
        slice_count=1,
        filled_count=0,
        resting_count=0,
        data_points_processed=1,
        outcome_identity={"class": "event-slice-loop-outcome"},
        journal_events=(bad_authority,),
    )
    assert is_refusal(minted)
    assert minted.category is RefusalCategory.INVALID_INPUT


def test_door_exports_the_accounting_surface() -> None:
    assert api.assemble_suppression_and_veto_accounting is (
        qmb.assemble_suppression_and_veto_accounting
    )
    assert api.VETO_DOOR_IDENTITIES == VETO_DOOR_IDENTITIES
    assert api.SUPPRESSION_REASON_CLASSES == SUPPRESSION_REASON_CLASSES
    assert api.TALLY_UNIT_KIND is TALLY_UNIT_KIND
    assert api.TALLY_FIELD_GROUP == TALLY_FIELD_GROUP
    assert api.SuppressionCount is SuppressionCount
    assert api.VetoCount is VetoCount
    assert api.SuppressionCount is qmb.SuppressionCount
    assert api.VetoCount is qmb.VetoCount
