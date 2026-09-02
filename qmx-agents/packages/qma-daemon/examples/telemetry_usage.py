"""L27 reference usage: harness telemetry store and swappable OTel export port."""

from __future__ import annotations

from qma.core.ontology import ActorId, DeskSlug, Quant, RoleName
from qma.daemon import RetentionJob, TelemetryStore
from qma.daemon.bus import MailboxStore
from qma.daemon.telemetry import OpenTelemetryExportAdapter
from qmf.core import is_ok, is_refusal


def main() -> None:
    store = TelemetryStore()
    adapter = OpenTelemetryExportAdapter()
    store.bind_exporter(adapter)

    metric = store.append(
        {
            "kind": "metric",
            "correlation_id": "corr-demo",
            "payload": {"name": "tokens", "value": 42},
        }
    )
    assert is_ok(metric)
    traj = store.append(
        {
            "kind": "trajectory",
            "correlation_id": "corr-demo",
            "payload": {"mission": "m-1"},
        }
    )
    assert is_ok(traj)
    assert "journal_seq" not in metric.value.to_payload()
    assert metric.value.trace_ref.startswith("trace:")

    exported = store.export_pending()
    assert is_ok(exported)
    assert exported.value == 2
    assert adapter.sdk_imported is False

    sender_id = ActorId.mint(DeskSlug.RESEARCH, "alpha")
    peer_id = ActorId.mint(DeskSlug.RESEARCH, "beta")
    assert is_ok(sender_id) and is_ok(peer_id)
    sender = Quant(
        actor_id=sender_id.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="alpha",
        role=RoleName.RESEARCHER,
        name="Quant alpha",
    )
    recipient = Quant(
        actor_id=peer_id.value,
        desk=DeskSlug.RESEARCH,
        quant_slug="beta",
        role=RoleName.RESEARCHER,
        name="Quant beta",
    )
    mailbox = MailboxStore()
    assert is_ok(mailbox.open_for_quant(sender))
    assert is_ok(mailbox.open_for_quant(recipient))
    assert is_ok(
        mailbox.send(
            {
                "msg_id": "msg-1",
                "from": sender.actor_id.value,
                "to": recipient.actor_id.value,
                "kind": "notify",
                "correlation_id": "corr-demo",
                "body": "ping",
                "priority": 0,
            }
        )
    )
    assert is_ok(mailbox.deliver("msg-1"))
    assert is_ok(mailbox.ack(recipient, "msg-1"))

    job = RetentionJob(telemetry=store, mailbox=mailbox)
    report = job.run(correlation_id="corr-demo", reason="bounded_retention")
    assert is_ok(report)
    assert report.value.telemetry is not None
    assert report.value.telemetry["trimmed_count"] == 1
    assert report.value.telemetry["retained_exempt_count"] == 1
    assert report.value.mailbox_delivery is not None
    assert report.value.to_payload()["gap_0089"] == "deferred"
    assert report.value.to_payload()["gap_0090"] == "deferred"
    assert is_refusal(store.compact_context())
    assert is_refusal(store.decide_trim_window())


if __name__ == "__main__":
    main()
