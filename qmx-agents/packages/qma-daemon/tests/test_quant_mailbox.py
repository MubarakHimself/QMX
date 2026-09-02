"""Story 46.4 — durable Quant Mailbox Envelope records (FR-Q60; CT-48)."""

from __future__ import annotations

import runpy
from pathlib import Path

from qma.core.ontology import ActorId, Agent, DeskSlug, Quant, RoleName
from qma.core.plugins.hooks import HookEvent, HookResult, build_hook_result
from qma.core.ports.mailbox import HUMAN_APPROVAL_CHANNEL
from qma.core.vocabulary.enums import DeliveryState, HookResultDecision, MessageKind
from qma.daemon import AuthoritativeJournal, PersistenceSubstrate
from qma.daemon.bus import (
    DELIVERY_RETENTION_KEYS,
    GAP_0071_LEAD_MAILBOX_CATCH_ALL,
    GAP_0079_EXTERNAL_TRANSPORT,
    MAILBOX_FOLD_ID,
    MAILBOX_SOURCE_STREAM,
    MAILBOX_STORE_NAME,
    NO_EXTERNAL_RELAY,
    MailboxStore,
)
from qma.daemon.journal import CLOSED_PROJECTIONS, v1_fold_contract
from qma.daemon.ledgers import TaskLedgerStore
from qmf.core import DataDrivenClock, Instant, is_ok, is_refusal


def _actor(desk: DeskSlug, slug: str) -> ActorId:
    minted = ActorId.mint(desk, slug)
    assert is_ok(minted)
    return minted.value


def _quant(*, slug: str = "lead", lead: bool = True, retired: bool = False) -> Quant:
    return Quant(
        actor_id=_actor(DeskSlug.RESEARCH, slug),
        desk=DeskSlug.RESEARCH,
        quant_slug=slug,
        role=RoleName.RESEARCHER,
        name=f"Quant {slug}",
        lead=lead,
        retired=retired,
    )


def _clock(*, boot: str = "boot-mailbox", n: int = 64) -> DataDrivenClock:
    base = 1_700_000_000_000_000_000
    walls = tuple(Instant(value_ns=base + i) for i in range(n))
    monos = tuple(i * 1_000 for i in range(n))
    return DataDrivenClock(boot_epoch_id=boot, wall_instants=walls, monotonic_ns=monos)


def _open_journal(
    tmp_path: Path, *, boot: str = "boot-mailbox"
) -> tuple[PersistenceSubstrate, AuthoritativeJournal]:
    substrate_result = PersistenceSubstrate.open(tmp_path, machine="test-host", boot_epoch_id=boot)
    assert is_ok(substrate_result), substrate_result
    substrate = substrate_result.value
    journal_result = AuthoritativeJournal.bind(substrate, clock=_clock(boot=boot))
    assert is_ok(journal_result), journal_result
    return substrate, journal_result.value


def _send_body(
    sender: Quant,
    recipient: Quant | ActorId,
    *,
    msg_id: str = "msg-1",
    kind: str = "notify",
    **extra: object,
) -> dict[str, object]:
    to = recipient.actor_id.value if isinstance(recipient, Quant) else recipient.value
    body: dict[str, object] = {
        "msg_id": msg_id,
        "from": sender.actor_id.value,
        "to": to,
        "kind": kind,
        "correlation_id": f"corr-{msg_id}",
        "body": "hello",
        "priority": 1,
    }
    body.update(extra)
    return body


def test_quant_owns_one_durable_mailbox_with_no_external_relay() -> None:
    store = MailboxStore()
    quant = _quant()
    first = store.open_for_quant(quant)
    again = store.open_for_quant(quant)
    assert is_ok(first) and is_ok(again)
    assert first.value is again.value
    assert first.value.owner == quant.actor_id
    assert store.mailbox_for(quant) is first.value
    assert store.external_relay is False
    assert NO_EXTERNAL_RELAY is True
    assert MAILBOX_STORE_NAME == "mailboxes_and_delivery_state"
    assert MAILBOX_STORE_NAME in CLOSED_PROJECTIONS
    fold = v1_fold_contract(MAILBOX_FOLD_ID)
    assert fold is not None
    assert fold.source_stream == MAILBOX_SOURCE_STREAM
    payload = first.value.to_payload()
    assert payload["external_relay"] is False
    assert payload["store"] == MAILBOX_STORE_NAME
    assert payload["retention"] == list(DELIVERY_RETENTION_KEYS)
    agent = Agent(id="agent-a", owner=quant.actor_id, session_id="session-1")
    refused = store.open_for_agent(agent)
    assert is_refusal(refused)
    assert refused.context["field"] == "mailbox"


def test_send_validates_closed_vocab_and_approval_request_channel() -> None:
    store = MailboxStore()
    sender = _quant(slug="alpha", lead=False)
    recipient = _quant(slug="beta", lead=False)
    assert is_ok(store.open_for_quant(sender))
    assert is_ok(store.open_for_quant(recipient))
    sent = store.send(_send_body(sender, recipient, kind="status", mission_ref="mission-1"))
    assert is_ok(sent)
    envelope = sent.value.envelope
    assert envelope.kind is MessageKind.STATUS
    assert envelope.mission_ref == "mission-1"
    assert envelope.msg_id == "msg-1"
    assert envelope.from_actor == sender.actor_id
    assert envelope.to_actor == recipient.actor_id
    assert sent.value.state is DeliveryState.QUEUED
    invented = store.send(_send_body(sender, recipient, msg_id="msg-bad", kind="escalate"))
    assert is_refusal(invented)
    approval = store.send(_send_body(sender, recipient, msg_id="msg-ask", kind="approval_request"))
    assert is_ok(approval)
    assert approval.value.envelope.kind is HUMAN_APPROVAL_CHANNEL
    assert approval.value.envelope.kind is MessageKind.APPROVAL_REQUEST


def test_delivery_is_at_least_once_with_msg_id_dedup_and_ack_cursor() -> None:
    store = MailboxStore()
    sender = _quant(slug="alpha", lead=False)
    recipient = _quant(slug="beta", lead=False)
    store.open_for_quant(sender)
    store.open_for_quant(recipient)
    first = store.send(_send_body(sender, recipient, msg_id="msg-dup"))
    second = store.send(_send_body(sender, recipient, msg_id="msg-dup", body="retry"))
    assert is_ok(first) and is_ok(second)
    assert first.value is second.value
    assert first.value.envelope.body == "hello"
    delivered = store.deliver("msg-dup")
    again = store.deliver("msg-dup")
    assert is_ok(delivered) and is_ok(again)
    assert delivered.value.state is DeliveryState.DELIVERED
    assert again.value.state is DeliveryState.DELIVERED
    mailbox = store.ack(recipient, "msg-dup")
    assert is_ok(mailbox)
    assert mailbox.value.ack_cursor == "msg-dup"
    idempotent = store.ack(recipient, "msg-dup")
    assert is_ok(idempotent)
    assert idempotent.value.ack_cursor == "msg-dup"


def test_missing_recipient_is_dead_letter_not_lead_catch_all() -> None:
    store = MailboxStore()
    lead = _quant(slug="lead", lead=True)
    sender = _quant(slug="alpha", lead=False)
    missing = _actor(DeskSlug.RESEARCH, "gone")
    store.open_for_quant(lead)
    store.open_for_quant(sender)
    sent = store.send(_send_body(sender, missing, msg_id="msg-gone"))
    assert is_ok(sent)
    assert sent.value.state is DeliveryState.DEAD_LETTER
    lead_box = store.mailbox_for(lead)
    assert lead_box is not None
    assert lead_box.record_for("msg-gone") is None
    retired = _quant(slug="old", lead=False, retired=True)
    store.open_for_quant(retired)
    to_retired = store.send(_send_body(sender, retired, msg_id="msg-retired"))
    assert is_ok(to_retired)
    assert to_retired.value.state is DeliveryState.DEAD_LETTER
    catch_all = store.send(
        _send_body(sender, missing, msg_id="msg-lead"),
        catch_all_lead=True,
    )
    assert is_refusal(catch_all)
    assert catch_all.context["gap"] == GAP_0071_LEAD_MAILBOX_CATCH_ALL
    assert catch_all.context["deferred"] is True
    relay = store.send(_send_body(sender, lead, msg_id="msg-relay"), external_relay=True)
    assert is_refusal(relay)
    assert relay.context["gap"] == GAP_0079_EXTERNAL_TRANSPORT
    assert relay.context["deferred"] is True


def test_handoff_becomes_work_only_by_writing_a_task() -> None:
    ledgers = TaskLedgerStore()
    store = MailboxStore(_task_ledgers=ledgers)
    sender = _quant(slug="alpha", lead=False)
    recipient = _quant(slug="beta", lead=False)
    store.open_for_quant(sender)
    store.open_for_quant(recipient)
    ping = store.send(
        _send_body(
            sender,
            recipient,
            msg_id="msg-handoff",
            kind="handoff",
            mission_ref="mission-1",
        )
    )
    assert is_ok(ping)
    assert ping.value.is_work is False
    assert store.handoff_is_work("msg-handoff") is False
    assert store.task_for_handoff("msg-handoff") is None
    assert ledgers.get("task-from-handoff") is None
    notify = store.send(_send_body(sender, recipient, msg_id="msg-notify", kind="notify"))
    assert is_ok(notify)
    refused = store.realize_handoff_as_task("msg-notify", task_id="task-x")
    assert is_refusal(refused)
    written = store.realize_handoff_as_task(
        "msg-handoff",
        task_id="task-from-handoff",
    )
    assert is_ok(written)
    assert written.value.id == "task-from-handoff"
    assert written.value.mission_id == "mission-1"
    assert written.value.owner == recipient.actor_id
    assert store.handoff_is_work("msg-handoff") is True
    realized = store.record_for("msg-handoff")
    assert realized is not None
    assert realized.envelope.task_ref == "task-from-handoff"
    assert ledgers.get("task-from-handoff") is not None
    again = store.realize_handoff_as_task("msg-handoff", task_id="task-other")
    assert is_ok(again)
    assert again.value.id == "task-from-handoff"


def test_before_message_send_gates_delivery() -> None:
    store = MailboxStore()
    sender = _quant(slug="alpha", lead=False)
    recipient = _quant(slug="beta", lead=False)
    store.open_for_quant(sender)
    store.open_for_quant(recipient)

    def deny(_event: HookEvent) -> HookResult:
        return build_hook_result(HookResultDecision.DENY, reason="blocked")

    registered = store.hooks.register_handler("before_message_send", deny)
    assert is_ok(registered)
    refused = store.send(_send_body(sender, recipient, msg_id="msg-blocked"))
    assert is_refusal(refused)
    assert refused.context["field"] == "before_message_send"


def test_trim_projection_never_deletes_journal_records(tmp_path: Path) -> None:
    substrate, journal = _open_journal(tmp_path)
    try:
        store = MailboxStore(_journal=journal)
        sender = _quant(slug="alpha", lead=False)
        recipient = _quant(slug="beta", lead=False)
        store.open_for_quant(sender)
        store.open_for_quant(recipient)
        queued = store.send(_send_body(sender, recipient, msg_id="msg-keep"))
        dead = store.send(_send_body(sender, _actor(DeskSlug.RESEARCH, "gone"), msg_id="msg-dead"))
        assert is_ok(queued) and is_ok(dead)
        assert is_ok(store.deliver("msg-keep"))
        assert is_ok(store.ack(recipient, "msg-keep"))
        approval = store.send(
            _send_body(sender, recipient, msg_id="msg-ask", kind="approval_request")
        )
        assert is_ok(approval)
        assert is_ok(store.deliver("msg-ask"))
        assert is_ok(store.ack(recipient, "msg-ask"))
        before = journal.read_all()
        assert is_ok(before)
        journal_count = len(before.value)
        assert journal_count >= 1
        trimmed = store.trim_delivery_projection()
        assert trimmed["journal_records_deleted"] is False
        assert trimmed["retention"] == list(DELIVERY_RETENTION_KEYS)
        assert trimmed["gap_0089"] == "deferred"
        after = journal.read_all()
        assert is_ok(after)
        assert len(after.value) == journal_count
        assert store.record_for("msg-keep") is None
        assert store.record_for("msg-dead") is None
        # unanswered approval_request is retained even when acked
        assert store.record_for("msg-ask") is not None
        events = [row["event"] for row in after.value]
        assert all(str(event).startswith("message.") for event in events)
    finally:
        journal.close()
        substrate.close()


def test_reference_usage_example_runs() -> None:
    path = Path(__file__).resolve().parents[1] / "examples" / "mailbox_usage.py"
    namespace = runpy.run_path(str(path))
    namespace["main"]()
