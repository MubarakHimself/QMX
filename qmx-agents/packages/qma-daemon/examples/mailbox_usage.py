"""L27 reference usage: durable Quant Mailbox Envelope records."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.core.vocabulary.enums import DeliveryState, MessageKind
from qma.daemon.bus import MailboxStore
from qma.daemon.ledgers import TaskLedgerStore
from qmf.core import is_ok, is_refusal


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


if __name__ == "__main__":
    main()
