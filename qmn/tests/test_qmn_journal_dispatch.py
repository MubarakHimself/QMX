"""Story 26.13 / QMX-F069 — journal-before-dispatch happens-before gate."""

from __future__ import annotations

from types import MappingProxyType
from typing import TypeVar

from qmf.core import RefusalCategory, Result, is_ok, is_refusal, unpersistable
from qmn.config import apply_settings_edit
from qmn.journal_dispatch import (
    BEST_EFFORT_PATH_PERMITTED,
    EFFECT_KINDS,
    LOG_ONLY_PATH_PERMITTED,
    CallableDispatcher,
    HappensBeforeTrace,
    LogLineSink,
    RecordingEffectDispatcher,
    RecordingJournalSink,
    WriteBoundary,
    enact_activation,
    enact_command,
    enact_control,
    enact_promotion,
    enact_protection,
    enact_settings,
    enact_treasury,
    journal_before_effect,
)
from qmn.observability.logging import LOGS_ARE_NOT_JOURNALS, log_record_is_journal_evidence

T = TypeVar("T")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def test_success_journals_before_dispatch_for_every_effect_kind() -> None:
    assert EFFECT_KINDS == (
        "command",
        "control",
        "protection",
        "promotion",
        "activation",
        "treasury",
        "settings",
    )
    enactors = {
        "command": enact_command,
        "control": enact_control,
        "protection": enact_protection,
        "promotion": enact_promotion,
        "activation": enact_activation,
        "treasury": enact_treasury,
        "settings": enact_settings,
    }
    for kind, enact in enactors.items():
        trace = HappensBeforeTrace()
        journal = RecordingJournalSink(trace)
        dispatcher = RecordingEffectDispatcher(trace)
        receipt = _ok(
            enact(
                {"id": f"{kind}-1"},
                journal=journal,
                dispatcher=dispatcher,
            )
        )
        assert trace.as_tuple() == ("journal", "dispatch")
        assert receipt.dispatched is True
        assert receipt.kind == kind
        assert receipt.steps == ("journal", "dispatch")
        assert len(journal.appended) == 1
        assert len(dispatcher.calls) == 1
        assert dispatcher.calls[0]["kind"] == kind


def test_storage_failure_never_reaches_dispatcher() -> None:
    trace = HappensBeforeTrace()
    journal = RecordingJournalSink(trace, fail=True)
    dispatcher = RecordingEffectDispatcher(trace)
    refused = _refusal(
        journal_before_effect(
            kind="command",
            payload={"kind": "command", "id": "c-fail"},
            journal=journal,
            dispatcher=dispatcher,
        )
    )
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert refused.context["failure_id"] == "storage.journal_before_dispatch"
    assert refused.context["blocks_entries"] is True
    assert refused.context["blocks_exits"] is False
    assert trace.as_tuple() == ("journal",)
    assert dispatcher.calls == []
    assert journal.appended == []


def test_partial_write_is_storage_failure_and_blocks_entries() -> None:
    trace = HappensBeforeTrace()
    journal = RecordingJournalSink(trace, partial=True)
    dispatcher = RecordingEffectDispatcher(trace)
    refused = _refusal(
        enact_control(
            {"id": "ctl-partial"},
            journal=journal,
            dispatcher=dispatcher,
            boundary=WriteBoundary.ORDERED_WITH_RECOVERY,
        )
    )
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert refused.context["failure_id"] == "storage.partial_write"
    assert refused.context["blocks_entries"] is True
    assert refused.context["blocks_exits"] is False
    assert trace.as_tuple() == ("journal",)
    assert dispatcher.calls == []
    assert len(journal.appended) == 1


def test_log_only_path_cannot_pass() -> None:
    assert LOG_ONLY_PATH_PERMITTED is False
    assert LOGS_ARE_NOT_JOURNALS is True
    assert log_record_is_journal_evidence() is False
    dispatcher = RecordingEffectDispatcher()
    refused = _refusal(
        journal_before_effect(
            kind="settings",
            payload={"kind": "settings", "variable": "clock_drift_warn"},
            journal="a-log-line",
            dispatcher=dispatcher,
        )
    )
    assert refused.context["failure_id"] == "storage.log_only_path"
    assert refused.context["log_only_permitted"] is False
    assert refused.context["log_record_is_journal_evidence"] is False
    assert dispatcher.calls == []

    log_sink = LogLineSink()
    log_sink.info("pretend this is the journal")
    refused_log = _refusal(
        enact_promotion(
            {"promotion_card_fp1": "fp1"},
            journal=log_sink,
            dispatcher=dispatcher,
        )
    )
    assert refused_log.context["failure_id"] == "storage.log_only_path"
    assert dispatcher.calls == []


def test_best_effort_path_cannot_pass() -> None:
    assert BEST_EFFORT_PATH_PERMITTED is False
    trace = HappensBeforeTrace()
    journal = RecordingJournalSink(trace, best_effort=True)
    dispatcher = RecordingEffectDispatcher(trace)
    refused = _refusal(
        journal_before_effect(
            kind="treasury",
            payload={"kind": "treasury", "act": "sweep"},
            journal=journal,
            dispatcher=dispatcher,
            best_effort=True,
        )
    )
    assert refused.context["failure_id"] == "storage.best_effort_path"
    assert refused.context["best_effort_permitted"] is False
    assert dispatcher.calls == []
    assert trace.as_tuple() == ()


def test_unknown_kind_and_boundary_refuse() -> None:
    journal = RecordingJournalSink()
    dispatcher = RecordingEffectDispatcher()
    kind = _refusal(
        journal_before_effect(
            kind="flatten",
            payload={"kind": "flatten"},
            journal=journal,
            dispatcher=dispatcher,
        )
    )
    assert kind.context["field"] == "kind"
    boundary = _refusal(
        journal_before_effect(
            kind="command",
            payload={"kind": "command"},
            journal=journal,
            dispatcher=dispatcher,
            boundary="best-effort",
        )
    )
    assert boundary.context["field"] == "boundary"


def test_callable_dispatcher_records_happens_before() -> None:
    from qmf.core import Ok

    trace = HappensBeforeTrace()
    journal = RecordingJournalSink(trace)
    seen: list[object] = []

    def apply(payload: object) -> Result[object]:
        seen.append(payload)
        return Ok(MappingProxyType({"applied": True}))

    dispatcher = CallableDispatcher(apply, trace=trace)
    receipt = _ok(
        enact_activation(
            {"transition_fp1": "fp-act"},
            journal=journal,
            dispatcher=dispatcher,
        )
    )
    assert trace.as_tuple() == ("journal", "dispatch")
    assert receipt.dispatcher_result == MappingProxyType({"applied": True})
    assert seen


def test_apply_settings_edit_journals_before_config_change() -> None:
    trace = HappensBeforeTrace()
    journal = RecordingJournalSink(trace)
    applied: list[str] = []

    from qmf.core import Ok

    def apply(payload: object) -> Result[object]:
        assert isinstance(payload, dict) or hasattr(payload, "get")
        applied.append(str(payload["variable"]))
        return Ok(MappingProxyType({"applied": True, "variable": payload["variable"]}))

    receipt = _ok(
        apply_settings_edit(
            journal=journal,
            dispatcher=CallableDispatcher(apply, trace=trace),
            variable="clock_drift_warn",
            operator_signature="op-sig-settings",
        )
    )
    assert trace.as_tuple() == ("journal", "dispatch")
    assert applied == ["clock_drift_warn"]
    assert receipt.dispatched is True

    blocked = _refusal(
        apply_settings_edit(
            journal=RecordingJournalSink(fail=True),
            dispatcher=CallableDispatcher(apply),
            variable="clock_drift_warn",
            operator_signature="op-sig-settings",
        )
    )
    assert blocked.category is RefusalCategory.STORAGE_FAILURE
    assert applied == ["clock_drift_warn"]


def test_injected_unpersistable_is_not_enough_without_ordering() -> None:
    """QMX-F069: passing the failure in is not the proof; order is observed."""
    # The qmf-risk helper that takes journal_result=unpersistable(...) cannot
    # witness happens-before. This gate records call order on both sides.
    trace = HappensBeforeTrace()
    journal = RecordingJournalSink(trace)
    journal.fail = True
    dispatcher = RecordingEffectDispatcher(trace)
    refused = _refusal(
        enact_protection(
            {"action_kind": "flatten"},
            journal=journal,
            dispatcher=dispatcher,
        )
    )
    assert is_refusal(unpersistable("disk full"))
    assert refused.category is RefusalCategory.STORAGE_FAILURE
    assert "dispatch" not in trace.as_tuple()
    assert dispatcher.calls == []
