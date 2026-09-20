"""Stories 59.3–59.4 — AD-25 fencing: UNKNOWN, stale restart, no unfill."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import replace
from typing import TypeVar, cast

from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok, is_refusal
from qmn.host.fencing import (
    FENCING_ACTIVATION,
    FENCING_AUTO_RETRY,
    FENCING_GAP_0058,
    FENCING_GAP_0100,
    FENCING_HAPPY_PATH,
    FENCING_ISSUER_ATC_SIMULATE,
    FENCING_ISSUER_VENUE,
    FENCING_OWNER,
    FENCING_PAYLOAD_FIELDS,
    FENCING_PROTOCOL,
    FENCING_RESIDUAL_DISPOSITIONS,
    FENCING_SEPARATE_DRAIN_CASES,
    FENCING_STATES,
    FENCING_TERMINAL_BRANCH,
    FENCING_TOKEN_UNIQUE_UNDER,
    SOFTWARE_ROLLBACK_CAN_UNFILL,
    UNKNOWN_BLOCKED_IS_TERMINAL,
    FencingAttempt,
    FencingRegistry,
    FencingState,
    fencing_machine_identity,
    record_fencing_payload,
    refuse_automatic_retry,
    refuse_gap_0058_single_machine,
    refuse_gap_0100_readiness_dashboard,
    refuse_merged_residual_positions,
    refuse_outstanding_positions,
    refuse_shared_account_concurrency,
    refuse_software_unfill,
    refuse_stale_predecessor_restart,
    refuse_unknown_commands_drain,
)

T = TypeVar("T")

_FROM_FP = "fp1:sha256:" + "ab" * 32
_TO_FP = "fp1:sha256:" + "cd" * 32
_THIRD_FP = "fp1:sha256:" + "ef" * 32
_QMB_TOKEN = "fp1:sha256:" + "11" * 32
_STALE_TOKEN = "fp1:sha256:" + "99" * 32


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _assert_invalid(result: Result[T], *, field: str | None = None) -> None:
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    if field is not None:
        assert result.context["field"] == field


def _assert_policy(result: Result[T], *, field: str | None = None) -> None:
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    if field is not None:
        assert result.context["field"] == field


def _refusal(result: Result[T]) -> TypedRefusal:
    assert is_refusal(result), result
    return result


def _payload(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "account_id": "acct:live-1",
        "activation": FENCING_ACTIVATION,
        "attempt_id": 1,
        "command_owner_epoch": 18,
        "composition_class": "book-bms",
        "from_composition_fp": _FROM_FP,
        "issuer": FENCING_ISSUER_VENUE,
        "machine_revision": 3,
        "orders_snapshot": [
            {
                "external_id": "ord:1",
                "snapshot_id": "snap:ord:1",
                "state": "working",
            }
        ],
        "positions_snapshot": [
            {
                "instrument": "EURUSD",
                "qty": "10000",
                "side": "buy",
                "snapshot_id": "snap:pos:1",
            }
        ],
        "predecessor_ack": False,
        "residual_disposition": "hold-manual",
        "role": "pm",
        "timeout": {
            "drain_deadline": "2026-09-19T13:30:00Z",
            "escalation": "operator-page",
        },
        "to_composition_fp": _TO_FP,
        "venue_kind": "CTRADER",
    }
    body.update(overrides)
    return body


def _walk_to_fenced(registry: FencingRegistry, start: object) -> FencingAttempt:
    attempt = _ok(registry.request_drain(start))
    attempt = _ok(registry.begin_drain(attempt))
    attempt = _ok(registry.attribute_residuals(attempt))
    attempt = _ok(registry.ack_predecessor(attempt))
    return _ok(registry.fenced_activate(attempt))


def _walk_happy(registry: FencingRegistry, start: object) -> FencingAttempt:
    attempt = _walk_to_fenced(registry, start)
    attempt = _ok(registry.activate(attempt))
    return _ok(registry.retire(attempt))


def _fill(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "deal_id": "deal:1",
        "fill_id": "fill:1",
        "instrument": "EURUSD",
        "qty": "10000",
        "side": "buy",
    }
    body.update(overrides)
    return body


def test_happy_path_one_command_owner_per_key() -> None:
    registry = FencingRegistry()
    idle = _ok(registry.start(_payload()))
    assert idle.state is FencingState.IDLE
    assert idle.state.value == FENCING_HAPPY_PATH[0]
    owner = registry.command_owner(idle.fence_key)
    assert owner is not None
    assert owner["writer"] == "predecessor"
    assert owner["composition_fp"] == _FROM_FP
    done = _walk_happy(registry, idle)
    assert done.state is FencingState.RETIRED
    assert done.predecessor_ack is True
    path = [
        FencingState.IDLE.value,
        FencingState.DRAIN_REQUESTED.value,
        FencingState.DRAINING.value,
        FencingState.RESIDUALS_ATTRIBUTED.value,
        FencingState.PREDECESSOR_ACKED.value,
        FencingState.FENCED_ACTIVATE.value,
        FencingState.ACTIVE.value,
        FencingState.RETIRED.value,
    ]
    assert path == list(FENCING_HAPPY_PATH)
    successor = registry.command_owner(idle.fence_key)
    assert successor is not None
    assert successor["writer"] == "predecessor"
    assert successor["composition_fp"] == _TO_FP
    assert successor["command_owner_epoch"] == 18
    second = registry.start(_payload(attempt_id=2, command_owner_epoch=19))
    assert is_ok(second)


def test_unknown_during_drain_is_terminal_and_blocks_predecessor_ack() -> None:
    registry = FencingRegistry()
    idle = _ok(registry.start(_payload()))
    draining = _ok(registry.begin_drain(_ok(registry.request_drain(idle))))
    blocked = _ok(
        registry.observe_unknown(
            draining,
            [{"external_id": "ord:1", "snapshot_id": "snap:ord:1", "state": "unknown"}],
        )
    )
    assert blocked.state is FencingState.UNKNOWN_BLOCKED
    assert blocked.unknown_blocked is True
    assert blocked.is_terminal is True
    assert UNKNOWN_BLOCKED_IS_TERMINAL is True
    assert blocked.predecessor_ack is False
    assert blocked.completion_evidence is not None
    evidence = dict(blocked.completion_evidence)
    assert evidence["branch"] == FENCING_TERMINAL_BRANCH == "unknown-blocked"
    assert evidence["terminal"] is True
    assert evidence["auto_retry"] is False is FENCING_AUTO_RETRY
    skipped = _refusal(registry.ack_predecessor(blocked))
    assert skipped.category is RefusalCategory.POLICY_REJECTION
    assert skipped.context["field"] == "unknown-blocked"
    assert skipped.context["terminal"] is True
    owner = registry.command_owner(idle.fence_key)
    assert owner is not None
    assert owner["writer"] == "predecessor"
    assert owner["composition_fp"] == _FROM_FP


def test_unknown_during_residual_attribution_is_terminal() -> None:
    registry = FencingRegistry()
    idle = _ok(registry.start(_payload()))
    attributed = _ok(
        registry.attribute_residuals(_ok(registry.begin_drain(_ok(registry.request_drain(idle)))))
    )
    blocked = _ok(
        registry.observe_unknown(
            attributed,
            [{"external_id": "ord:1", "snapshot_id": "snap:ord:1", "state": "unknown"}],
        )
    )
    assert blocked.state is FencingState.UNKNOWN_BLOCKED
    continued = registry.ack_predecessor(blocked)
    _assert_policy(continued, field="unknown-blocked")


def test_automatic_retry_and_dual_writer_cannot_open_second_owner() -> None:
    registry = FencingRegistry()
    first = _ok(registry.start(_payload()))
    dual = registry.start(_payload(attempt_id=2, command_owner_epoch=19))
    _assert_policy(dual, field="command_owner")
    draining = _ok(registry.begin_drain(_ok(registry.request_drain(first))))
    blocked = _ok(
        registry.observe_unknown(
            draining,
            [{"external_id": "ord:1", "snapshot_id": "snap:ord:1", "state": "unknown"}],
        )
    )
    retried = _refusal(registry.retry(blocked))
    assert retried.category is RefusalCategory.POLICY_REJECTION
    assert retried.context["field"] == "unknown-blocked"
    assert retried.context["auto_retry"] is False
    standalone = refuse_automatic_retry(blocked)
    assert is_refusal(standalone)
    assert standalone.context["auto_retry"] is False
    sneaky = registry.start(_payload(attempt_id=2, command_owner_epoch=19))
    _assert_policy(sneaky, field="unknown-blocked")
    owner = registry.command_owner(first.fence_key)
    assert owner is not None
    assert owner["composition_fp"] == _FROM_FP


def test_operator_reconcile_mints_new_attempt_and_epoch() -> None:
    registry = FencingRegistry()
    first = _ok(registry.start(_payload()))
    blocked = _ok(
        registry.observe_unknown(
            _ok(registry.begin_drain(_ok(registry.request_drain(first)))),
            [{"external_id": "ord:1", "snapshot_id": "snap:ord:1", "state": "unknown"}],
        )
    )
    immutable = dict(cast("Mapping[str, object]", blocked.completion_evidence))
    same_ids = registry.operator_reconcile(
        blocked,
        principal="operator",
        payload=_payload(),
    )
    _assert_policy(same_ids, field="attempt_id")
    same_epoch = registry.operator_reconcile(
        blocked,
        principal="operator",
        payload=_payload(attempt_id=2),
    )
    _assert_policy(same_epoch, field="command_owner_epoch")
    not_operator = registry.operator_reconcile(
        blocked,
        principal="host",
        payload=_payload(attempt_id=2, command_owner_epoch=19),
    )
    _assert_policy(not_operator, field="principal")
    nxt = _ok(
        registry.operator_reconcile(
            blocked,
            principal="operator",
            payload=_payload(attempt_id=2, command_owner_epoch=19),
        )
    )
    assert nxt.attempt_id == 2
    assert nxt.command_owner_epoch == 19
    assert nxt.state is FencingState.IDLE
    assert nxt.predecessor_attempt_id == blocked.attempt_id
    assert nxt.fencing_token != blocked.fencing_token
    assert dict(cast("Mapping[str, object]", blocked.completion_evidence)) == immutable
    owner = registry.command_owner(nxt.fence_key)
    assert owner is not None
    assert owner["writer"] == "predecessor"
    assert owner["composition_fp"] == _FROM_FP


def test_recorded_payload_fields_and_issuers() -> None:
    recorded = _ok(record_fencing_payload(_payload()))
    body = recorded.as_record()
    for field in FENCING_PAYLOAD_FIELDS:
        assert field in body
    assert body["issuer"] == FENCING_ISSUER_VENUE == FENCING_OWNER
    assert body["activation"] == FENCING_ACTIVATION
    assert body["residual_disposition"] in FENCING_RESIDUAL_DISPOSITIONS
    assert body["token_unique_under"] == list(FENCING_TOKEN_UNIQUE_UNDER)
    token = body["fencing_token"]
    assert isinstance(token, str)
    assert token.startswith("fp1:sha256:")
    positions = cast("list[object]", body["positions_snapshot"])
    first_pos = cast("Mapping[str, object]", positions[0])
    assert "snapshot_id" in first_pos
    orders = cast("list[object]", body["orders_snapshot"])
    first_ord = cast("Mapping[str, object]", orders[0])
    assert "snapshot_id" in first_ord
    schema = fencing_machine_identity()
    assert schema["fencing_protocol"] == FENCING_PROTOCOL == "AD-25"
    assert schema["fencing_owner"] == FENCING_OWNER
    assert schema["fencing_terminal_branch"] == FENCING_TERMINAL_BRANCH
    assert schema["fencing_auto_retry"] is False
    assert schema["fencing_gap_0100"] is False is FENCING_GAP_0100
    assert FENCING_TERMINAL_BRANCH in FENCING_STATES
    assert FENCING_TERMINAL_BRANCH not in FENCING_HAPPY_PATH
    atc = _ok(
        record_fencing_payload(
            _payload(
                composition_class="alternative",
                fencing_token=_QMB_TOKEN,
                issuer=FENCING_ISSUER_ATC_SIMULATE,
                venue_kind=None,
            )
        )
    )
    assert atc.issuer == FENCING_ISSUER_ATC_SIMULATE == "COMP-QMB"
    assert atc.fencing_token == _QMB_TOKEN
    assert atc.venue_kind is None
    _assert_invalid(
        record_fencing_payload(
            _payload(issuer=FENCING_ISSUER_ATC_SIMULATE, fencing_token=_QMB_TOKEN)
        ),
        field="venue_kind",
    )
    _assert_invalid(
        record_fencing_payload(_payload(issuer=FENCING_ISSUER_VENUE, venue_kind=None)),
        field="venue_kind",
    )
    live_atc = _ok(record_fencing_payload(_payload(composition_class="alternative")))
    assert live_atc.issuer == FENCING_ISSUER_VENUE
    assert live_atc.venue_kind == "CTRADER"


def test_gap_0100_readiness_dashboard_is_refused() -> None:
    chrome = _refusal(record_fencing_payload(_payload(readiness_dashboard=True)))
    assert chrome.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert chrome.context["field"] == "readiness_dashboard"
    assert chrome.context["gap"] == "GAP-0100"
    named = refuse_gap_0100_readiness_dashboard()
    assert named.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert named.context["gap"] == "GAP-0100"
    assert FENCING_PROTOCOL == "AD-25"
    assert FENCING_GAP_0100 is False


def test_stale_predecessor_restart_after_fenced_activate_is_refused() -> None:
    registry = FencingRegistry()
    first = _ok(registry.start(_payload()))
    done = _walk_happy(registry, first)
    assert done.state is FencingState.RETIRED
    nxt = _ok(
        registry.start(
            _payload(
                attempt_id=2,
                command_owner_epoch=19,
                from_composition_fp=_TO_FP,
                to_composition_fp=_THIRD_FP,
            )
        )
    )
    fenced = _walk_to_fenced(registry, nxt)
    assert fenced.state is FencingState.FENCED_ACTIVATE
    owner = registry.command_owner(fenced.fence_key)
    assert owner is not None
    assert owner["writer"] == "successor"
    assert owner["command_owner_epoch"] == 19
    assert owner["fencing_token"] != first.fencing_token
    stale_epoch = _refusal(
        registry.restart_predecessor(
            fenced.fence_key,
            command_owner_epoch=first.command_owner_epoch,
            fencing_token=first.fencing_token,
        )
    )
    assert stale_epoch.category is RefusalCategory.POLICY_REJECTION
    assert stale_epoch.context["field"] == "cas_guard"
    assert stale_epoch.context["expected_epoch"] == 19
    assert stale_epoch.context["presented_epoch"] == first.command_owner_epoch
    stale_token = _refusal(
        registry.restart_predecessor(
            fenced.fence_key,
            command_owner_epoch=19,
            fencing_token=first.fencing_token,
        )
    )
    _assert_policy(stale_token, field="cas_guard")
    presented = _refusal(registry.restart_predecessor(first))
    _assert_policy(presented, field="cas_guard")
    copied = _refusal(registry.restart_predecessor(fenced))
    _assert_policy(copied, field="stale_predecessor")
    still = registry.command_owner(fenced.fence_key)
    assert still is not None
    assert still["writer"] == "successor"
    assert still["command_owner_epoch"] == 19
    assert still["fencing_token"] == fenced.fencing_token


def test_cas_guards_refuse_mismatched_epoch_token() -> None:
    registry = FencingRegistry()
    idle = _ok(registry.start(_payload()))
    fenced = _walk_to_fenced(registry, idle)
    wrong_epoch = _refusal(registry.activate(replace(fenced, command_owner_epoch=17)))
    _assert_policy(wrong_epoch, field="cas_guard")
    wrong_token = _refusal(registry.activate(replace(fenced, fencing_token=_STALE_TOKEN)))
    _assert_policy(wrong_token, field="cas_guard")
    named = refuse_stale_predecessor_restart(
        expected_epoch=18,
        expected_token=fenced.fencing_token,
        presented_epoch=17,
        presented_token=_STALE_TOKEN,
    )
    assert named.category is RefusalCategory.POLICY_REJECTION
    assert named.context["field"] == "cas_guard"
    assert named.context["expected_epoch"] == 18
    assert named.context["presented_token"] == _STALE_TOKEN
    first_stale = _refusal(
        registry.restart_predecessor(
            fenced.fence_key,
            command_owner_epoch=17,
            fencing_token=_STALE_TOKEN,
        )
    )
    _assert_policy(first_stale, field="cas_guard")
    active = _ok(registry.activate(fenced))
    assert active.state is FencingState.ACTIVE


def test_software_rollback_cannot_unfill_new_owner_fill() -> None:
    registry = FencingRegistry()
    idle = _ok(registry.start(_payload()))
    too_early = registry.record_owner_fill(
        idle.fence_key,
        command_owner_epoch=idle.command_owner_epoch,
        fencing_token=idle.fencing_token,
        fill=_fill(),
    )
    _assert_policy(too_early, field="state")
    fenced = _walk_to_fenced(registry, idle)
    stale_fill = registry.record_owner_fill(
        fenced.fence_key,
        command_owner_epoch=17,
        fencing_token=_STALE_TOKEN,
        fill=_fill(),
    )
    _assert_policy(stale_fill, field="cas_guard")
    recorded = _ok(
        registry.record_owner_fill(
            fenced.fence_key,
            command_owner_epoch=fenced.command_owner_epoch,
            fencing_token=fenced.fencing_token,
            fill=_fill(),
        )
    )
    assert recorded.fill_id == "fill:1"
    assert recorded.as_record()["unfillable"] is True
    assert SOFTWARE_ROLLBACK_CAN_UNFILL is False
    again = _ok(
        registry.record_owner_fill(
            fenced.fence_key,
            command_owner_epoch=fenced.command_owner_epoch,
            fencing_token=fenced.fencing_token,
            fill=_fill(),
        )
    )
    assert again.fill_id == recorded.fill_id
    clash = registry.record_owner_fill(
        fenced.fence_key,
        command_owner_epoch=fenced.command_owner_epoch,
        fencing_token=fenced.fencing_token,
        fill=_fill(qty="1"),
    )
    _assert_policy(clash, field="fill_id")
    rolled = _refusal(registry.software_rollback(fenced.fence_key, fill_id="fill:1"))
    assert rolled.category is RefusalCategory.POLICY_REJECTION
    assert rolled.context["field"] == "software_rollback"
    assert rolled.context["unfill"] is False
    assert rolled.context["fill_id"] == "fill:1"
    named = refuse_software_unfill(recorded)
    assert named.context["unfill"] is False
    remaining = registry.owner_fills(fenced.fence_key)
    assert len(remaining) == 1
    assert remaining[0].fill_id == "fill:1"
    assert remaining[0].content["qty"] == "10000"


def test_drain_cases_stay_separate_and_gap_0058_is_refused() -> None:
    merged = _refusal(record_fencing_payload(_payload(residual_positions=True)))
    assert merged.category is RefusalCategory.POLICY_REJECTION
    assert merged.context["field"] == "residual_positions"
    assert merged.context["drain_cases"] == FENCING_SEPARATE_DRAIN_CASES
    named_merged = refuse_merged_residual_positions()
    assert named_merged.context["field"] == "residual_positions"
    outstanding = refuse_outstanding_positions()
    unknown = refuse_unknown_commands_drain()
    shared = refuse_shared_account_concurrency()
    fields = {
        outstanding.context["field"],
        unknown.context["field"],
        shared.context["field"],
    }
    assert fields == set(FENCING_SEPARATE_DRAIN_CASES)
    gap = _refusal(record_fencing_payload(_payload(single_machine_placement=True)))
    assert gap.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert gap.context["gap"] == "GAP-0058"
    named_gap = refuse_gap_0058_single_machine()
    assert named_gap.context["gap"] == "GAP-0058"
    assert FENCING_GAP_0058 is False
    schema = fencing_machine_identity()
    assert schema["fencing_gap_0058"] is False
    assert schema["software_rollback_can_unfill"] is False
    assert schema["fencing_separate_drain_cases"] == FENCING_SEPARATE_DRAIN_CASES
