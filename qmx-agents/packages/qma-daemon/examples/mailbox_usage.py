"""L27 reference usage: durable Quant Mailbox Envelope records and WakePolicy."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.vocabulary.enums import DeliveryState, MessageKind
from qma.daemon.bus import MailboxStore
from qma.daemon.ledgers import TaskLedgerStore
from qmf.core import DataDrivenClock, Instant, is_ok, is_refusal


def main() -> None:
    minted = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    assert is_ok(minted)
    peer = ActorId.mint(DeskSlug.RESEARCH, "beta")
    assert is_ok(peer)
    sender = Quant(
        actor_id=minted.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="Quant alpha",
    )
    recipient = Quant(
        actor_id=peer.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="beta",
        role=RoleName.RESEARCHER,
        name="Quant beta",
    )

    ledgers = TaskLedgerStore()
    store = MailboxStore(_task_ledgers=ledgers)
    assert is_ok(store.open_for_quant(sender))
    assert is_ok(store.open_for_quant(recipient))
    assert store.external_relay is False

    notify = store.send(
        {
            "msg_id": "msg-notify",
            "from": sender.actor_id.value,
            "to": recipient.actor_id.value,
            "kind": "notify",
            "correlation_id": "corr-notify",
            "body": "status ping",
            "priority": 0,
        }
    )
    assert is_ok(notify)
    assert notify.value.state is DeliveryState.QUEUED
    assert is_ok(store.deliver("msg-notify"))
    assert is_ok(store.ack(recipient, "msg-notify"))

    handoff = store.send(
        {
            "msg_id": "msg-handoff",
            "from": sender.actor_id.value,
            "to": recipient.actor_id.value,
            "kind": "handoff",
            "correlation_id": "corr-handoff",
            "body": "please continue",
            "priority": 1,
            "mission_ref": "mission-1",
        }
    )
    assert is_ok(handoff)
    assert handoff.value.envelope.kind is MessageKind.HANDOFF
    assert store.handoff_is_work("msg-handoff") is False
    written = store.realize_handoff_as_task("msg-handoff", task_id="task-1")
    assert is_ok(written)
    assert store.handoff_is_work("msg-handoff") is True
    assert ledgers.get("task-1") is not None

    missing = ActorId.mint(DeskSlug.RESEARCH, "gone")
    assert is_ok(missing)
    dead = store.send(
        {
            "msg_id": "msg-dead",
            "from": sender.actor_id.value,
            "to": missing.value,
            "kind": "question",
            "correlation_id": "corr-dead",
            "body": "are you there?",
            "priority": 0,
        }
    )
    assert is_ok(dead)
    assert dead.value.state is DeliveryState.DEAD_LETTER
    assert is_refusal(store.send({"msg_id": "x"}, external_relay=True))

    zone = "America/New_York"
    night = datetime(2024, 1, 15, 3, 0, tzinfo=ZoneInfo(zone))
    morning = datetime(2024, 1, 15, 6, 0, tzinfo=ZoneInfo(zone))
    night_ns = int(night.timestamp()) * 1_000_000_000
    morning_ns = int(morning.timestamp()) * 1_000_000_000
    clock = DataDrivenClock(
        boot_epoch_id="wake-example",
        wall_instants=(
            Instant(value_ns=night_ns),
            Instant(value_ns=morning_ns),
            *(Instant(value_ns=morning_ns) for _ in range(8)),
        ),
        monotonic_ns=tuple(i * 1_000 for i in range(10)),
    )
    waking = MailboxStore(_clock=clock)
    assert is_ok(waking.open_for_quant(sender))
    assert is_ok(waking.open_for_quant(recipient))
    authored = waking.write_wake_policy(
        recipient,
        {
            "wake_conditions": ["any"],
            "quiet_hours": {"start": "22:00", "end": "06:00", "iana_zone": zone},
            "max_wakes_per_window": 4,
        },
        principal_class="operator",
    )
    assert is_ok(authored)
    assert authored.value.wake_policy is not None
    assert is_refusal(
        waking.write_wake_policy(
            recipient,
            {"wake_conditions": ["notify"]},
            principal_class="operator",
            source="model",
        )
    )
    ping = waking.send(
        {
            "msg_id": "msg-night",
            "from": sender.actor_id.value,
            "to": recipient.actor_id.value,
            "kind": "notify",
            "correlation_id": "corr-night",
            "body": "overnight ping",
            "priority": 0,
            "created_at": night_ns,
        }
    )
    assert is_ok(ping)
    deferred = waking.deliver("msg-night")
    assert is_ok(deferred)
    assert deferred.value.state is DeliveryState.DEFERRED
    assert is_ok(waking.ack(recipient, "msg-night"))
    assert is_ok(waking.evaluate_routine_fire(recipient, at=Instant(value_ns=night_ns)))
    fired = waking.fire_due_wakes(at=Instant(value_ns=morning_ns))
    assert is_ok(fired)
    assert fired.value[0].state is DeliveryState.WOKE


if __name__ == "__main__":
    main()
