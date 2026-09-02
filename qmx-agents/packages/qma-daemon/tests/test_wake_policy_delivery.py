"""Story 46.5 — evaluate Quant WakePolicy at delivery time (FR-Q61; CT-48)."""

from __future__ import annotations

import runpy
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.ontology.wake_policy import (
    MAX_WAKES_PER_WINDOW_REGISTRY_KEY,
    QUANT_WRITE_COMMAND,
    QUIET_HOURS_REGISTRY_KEY,
    WAKE_POLICY_EDITABILITY,
    WAKE_POLICY_HOME,
    WAKE_POLICY_SCOPE,
    QuietHours,
    WakePolicy,
)
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary.enums import DeliveryState, MessageKind, VariableEditability, VariableScope
from qma.daemon.bus import MailboxStore
from qma.daemon.scheduler import (
    evaluate_delivery_wake,
    next_quiet_hours_end,
    routine_fire_suppressed_by_quiet_hours,
    running_agent_paused_by_quiet_hours,
)
from qmf.core import DataDrivenClock, Instant, is_ok, is_refusal

_ZONE = "America/New_York"


def _actor(desk: DeskSlug, slug: str) -> ActorId:
    minted = ActorId.mint(desk, slug)
    assert is_ok(minted)
    return minted.value


def _quant(*, slug: str = "lead", lead: bool = True) -> Quant:
    return Quant(
        actor_id=_actor(DeskSlug.RESEARCH, slug),
        desk=DeskSlug.RESEARCH,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
        lead=lead,
    )


def _ns(year: int, month: int, day: int, hour: int, minute: int, zone: str = _ZONE) -> int:
    dt = datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(zone))
    return int(dt.timestamp()) * 1_000_000_000


def _clock(*values_ns: int) -> DataDrivenClock:
    seed = values_ns if values_ns else (1_700_000_000_000_000_000,)
    walls = tuple(Instant(value_ns=item) for item in seed)
    walls = walls + tuple(Instant(value_ns=seed[-1]) for _ in range(64))
    monos = tuple(i * 1_000 for i in range(len(walls)))
    return DataDrivenClock(boot_epoch_id="wake-policy", wall_instants=walls, monotonic_ns=monos)


def _policy_body(**overrides: object) -> dict[str, object]:
    body: dict[str, object] = {
        "wake_conditions": ["any"],
        "quiet_hours": {"start": "22:00", "end": "06:00", "iana_zone": _ZONE},
        "max_wakes_per_window": 2,
    }
    body.update(overrides)
    return body


def _send_body(
    sender: Quant,
    recipient: Quant,
    *,
    msg_id: str,
    kind: str = "notify",
    **extra: object,
) -> dict[str, object]:
    body: dict[str, object] = {
        "msg_id": msg_id,
        "from": sender.actor_id.value,
        "to": recipient.actor_id.value,
        "kind": kind,
        "correlation_id": f"corr-{msg_id}",
        "body": "hello",
        "priority": 1,
        "created_at": 1_700_000_000_000_000_000,
    }
    body.update(extra)
    return body


def _open_with_policy(
    *,
    clock: DataDrivenClock,
    policy: dict[str, object] | None = None,
) -> tuple[MailboxStore, Quant, Quant]:
    store = MailboxStore(_clock=clock)
    sender = _quant(slug="alpha", lead=False)
    recipient = _quant(slug="beta", lead=False)
    assert is_ok(store.open_for_quant(sender))
    assert is_ok(store.open_for_quant(recipient))
    written = store.write_wake_policy(
        recipient,
        policy if policy is not None else _policy_body(),
        principal_class="operator",
    )
    assert is_ok(written)
    return store, sender, recipient


def test_operator_write_is_ui_editable_quant_scoped_and_model_refused() -> None:
    store = MailboxStore(_clock=_clock())
    recipient = _quant(slug="beta", lead=False)
    assert is_ok(store.open_for_quant(recipient))
    written = store.write_wake_policy(
        recipient,
        _policy_body(),
        principal_class="operator",
        source="operator",
    )
    assert is_ok(written)
    policy = written.value.wake_policy
    assert policy is not None
    assert policy.scope is WAKE_POLICY_SCOPE is VariableScope.QUANT
    assert policy.editability is WAKE_POLICY_EDITABILITY is VariableEditability.UI_EDITABLE
    assert policy.home == WAKE_POLICY_HOME
    assert policy.quiet_hours is not None
    assert policy.quiet_hours.registry_key == QUIET_HOURS_REGISTRY_KEY
    payload = policy.to_payload()
    assert payload["max_wakes_per_window_registry_key"] == MAX_WAKES_PER_WINDOW_REGISTRY_KEY

    machine = store.write_wake_policy(
        recipient,
        _policy_body(max_wakes_per_window=99),
        principal_class="machine",
    )
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)
    assert machine.context["command"] == QUANT_WRITE_COMMAND

    model = store.write_wake_policy(
        recipient,
        _policy_body(max_wakes_per_window=99),
        principal_class="operator",
        source="model",
    )
    assert is_refusal(model)
    assert "no model" in str(model.context.get("reason", "")).lower()

    stored = store.quant_for(recipient)
    assert stored is not None
    assert stored.wake_policy is not None
    assert stored.wake_policy.max_wakes_per_window == 2


def test_open_for_quant_cannot_override_stored_policy() -> None:
    store = MailboxStore(_clock=_clock())
    recipient = _quant(slug="beta", lead=False)
    assert is_ok(store.open_for_quant(recipient))
    assert is_ok(store.write_wake_policy(recipient, _policy_body(), principal_class="operator"))
    sneak = recipient.with_wake_policy(None)
    # re-open with a blank policy keeps the operator-authored one
    again = store.open_for_quant(sneak)
    assert is_ok(again)
    kept = store.quant_for(recipient)
    assert kept is not None
    assert kept.wake_policy is not None
    other = WakePolicy(wake_conditions=frozenset({"status"}))
    refused = store.open_for_quant(recipient.with_wake_policy(other))
    assert is_refusal(refused)


def test_quiet_hours_defer_wake_but_delivery_and_ack_proceed() -> None:
    inside = _ns(2024, 1, 15, 3, 0)
    end = _ns(2024, 1, 15, 6, 0)
    store, sender, recipient = _open_with_policy(clock=_clock(inside, end))
    sent = store.send(_send_body(sender, recipient, msg_id="msg-night"))
    assert is_ok(sent)
    delivered = store.deliver("msg-night")
    assert is_ok(delivered)
    assert delivered.value.state is DeliveryState.DEFERRED
    assert delivered.value.wake_at == end
    acked = store.ack(recipient, "msg-night")
    assert is_ok(acked)
    assert acked.value.ack_cursor == "msg-night"
    record = store.record_for("msg-night")
    assert record is not None
    assert record.acked is True
    assert record.state is DeliveryState.DEFERRED

    fired = store.fire_due_wakes(at=Instant(value_ns=end))
    assert is_ok(fired)
    assert len(fired.value) == 1
    assert fired.value[0].state is DeliveryState.WOKE
    woke = store.record_for("msg-night")
    assert woke is not None
    assert woke.state is DeliveryState.WOKE


def test_outside_quiet_hours_wakes_when_conditions_match() -> None:
    noon = _ns(2024, 1, 15, 12, 0)
    store, sender, recipient = _open_with_policy(clock=_clock(noon))
    sent = store.send(_send_body(sender, recipient, msg_id="msg-day", kind="notify"))
    assert is_ok(sent)
    delivered = store.deliver("msg-day")
    assert is_ok(delivered)
    assert delivered.value.state is DeliveryState.WOKE


def test_unauthored_policy_delivers_without_invented_wake() -> None:
    store = MailboxStore(_clock=_clock())
    sender = _quant(slug="alpha", lead=False)
    recipient = _quant(slug="beta", lead=False)
    store.open_for_quant(sender)
    store.open_for_quant(recipient)
    assert recipient.wake_policy is None
    sent = store.send(_send_body(sender, recipient, msg_id="msg-plain"))
    assert is_ok(sent)
    delivered = store.deliver("msg-plain")
    assert is_ok(delivered)
    assert delivered.value.state is DeliveryState.DELIVERED


def test_routine_running_agent_and_approval_reply_are_not_suppressed() -> None:
    inside = _ns(2024, 1, 15, 3, 0)
    store, sender, recipient = _open_with_policy(clock=_clock(inside, inside, inside))
    at = Instant(value_ns=inside)
    owned = store.quant_for(recipient)
    assert owned is not None
    policy = owned.wake_policy
    suppressed = routine_fire_suppressed_by_quiet_hours(policy, at=at)
    assert is_ok(suppressed)
    assert suppressed.value is False
    may_fire = store.evaluate_routine_fire(recipient, at=at)
    assert is_ok(may_fire)
    assert may_fire.value is True

    store.mark_agent_running(recipient, "agent-1")
    paused = store.pause_running_agent(recipient, at=at)
    assert is_ok(paused)
    assert paused.value is False
    still_paused = running_agent_paused_by_quiet_hours(policy, at=at)
    assert is_ok(still_paused)
    assert still_paused.value is False

    ask = store.send(_send_body(sender, recipient, msg_id="msg-ask", kind="approval_request"))
    assert is_ok(ask)
    reply = store.send(
        _send_body(
            sender,
            recipient,
            msg_id="msg-reply",
            kind="reply",
            reply_to_ref="msg-ask",
        )
    )
    assert is_ok(reply)
    delivered = store.deliver("msg-reply")
    assert is_ok(delivered)
    assert delivered.value.state is not DeliveryState.DEFERRED
    assert delivered.value.state is DeliveryState.WOKE
    answered = store.answer_approval("msg-ask")
    assert is_ok(answered)


def test_wake_cap_does_not_rewrite_operator_policy() -> None:
    noon = _ns(2024, 1, 15, 12, 0)
    store, sender, recipient = _open_with_policy(
        clock=_clock(noon, noon, noon, noon),
        policy=_policy_body(max_wakes_per_window=1),
    )
    first = store.send(_send_body(sender, recipient, msg_id="msg-a"))
    second = store.send(_send_body(sender, recipient, msg_id="msg-b"))
    assert is_ok(first) and is_ok(second)
    woke = store.deliver("msg-a")
    capped = store.deliver("msg-b")
    assert is_ok(woke) and is_ok(capped)
    assert woke.value.state is DeliveryState.WOKE
    assert capped.value.state is DeliveryState.DELIVERED
    owned = store.quant_for(recipient)
    assert owned is not None
    stored = owned.wake_policy
    assert stored is not None
    assert stored.max_wakes_per_window == 1
    hijack = store.write_wake_policy(
        recipient,
        _policy_body(max_wakes_per_window=99),
        principal_class="operator",
        source="model",
    )
    assert is_refusal(hijack)
    after = store.quant_for(recipient)
    assert after is not None
    assert after.wake_policy == stored


def test_evaluate_delivery_wake_is_deterministic() -> None:
    policy = WakePolicy(
        wake_conditions=frozenset({"any"}),
        quiet_hours=QuietHours(
            start_minute=22 * 60,
            end_minute=6 * 60,
            iana_zone=_ZONE,
        ),
        max_wakes_per_window=5,
    )
    inside = Instant(value_ns=_ns(2024, 1, 15, 23, 0))
    first = evaluate_delivery_wake(
        policy,
        kind=MessageKind.NOTIFY,
        at=inside,
        wakes_in_window=0,
    )
    second = evaluate_delivery_wake(
        policy,
        kind=MessageKind.NOTIFY,
        at=inside,
        wakes_in_window=0,
    )
    assert is_ok(first) and is_ok(second)
    assert first.value == second.value
    assert first.value.state is DeliveryState.DEFERRED
    quiet = policy.quiet_hours
    assert quiet is not None
    end = next_quiet_hours_end(quiet, inside)
    assert is_ok(end)
    assert first.value.wake_at == end.value.value_ns
    assert first.value.quiet_hours_key == QUIET_HOURS_REGISTRY_KEY
    assert first.value.max_wakes_key == MAX_WAKES_PER_WINDOW_REGISTRY_KEY


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "mailbox_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
