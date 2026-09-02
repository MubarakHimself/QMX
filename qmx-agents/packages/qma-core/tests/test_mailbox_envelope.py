"""Story 46.4 — mailbox Envelope record, closed vocabularies (FR-Q60; CT-48)."""

from __future__ import annotations

from qma.core.content import content_address
from qma.core.ontology import ActorId, DeskSlug
from qma.core.ports.mailbox import (
    DELIVERY_STATE_VALUES,
    ENVELOPE_FP1_EXCLUDED_FIELDS,
    ENVELOPE_OPTIONAL_REFS,
    ENVELOPE_REQUIRED_FIELDS,
    GAP_0071_LEAD_MAILBOX_CATCH_ALL,
    GAP_0079_EXTERNAL_TRANSPORT,
    HUMAN_APPROVAL_CHANNEL,
    MESSAGE_KIND_VALUES,
    envelope_identity_content,
    is_human_approval_channel,
    parse_delivery_state,
    parse_envelope,
    parse_message_kind,
    refuse_external_agent_transport,
    refuse_lead_mailbox_catch_all,
)
from qma.core.vocabulary import CLOSED_VOCABULARIES, DeliveryState, MessageKind, parse_closed
from qmf.core import is_ok, is_refusal


def _owner(*, slug: str = "lead") -> ActorId:
    minted = ActorId.mint(DeskSlug.RESEARCH, slug)
    assert is_ok(minted)
    return minted.value


def _envelope_body(**overrides: object) -> dict[str, object]:
    owner = _owner()
    peer = _owner(slug="peer")
    body: dict[str, object] = {
        "msg_id": "msg-1",
        "from": owner.value,
        "to": peer.value,
        "kind": "notify",
        "correlation_id": "corr-1",
        "body": "ping",
        "priority": 0,
        "created_at": 1_700_000_000_000_000_000,
        "artifact_refs": [],
    }
    body.update(overrides)
    return body


def test_closed_vocabs_cover_message_kind_and_delivery_state() -> None:
    names = {entry.name for entry in CLOSED_VOCABULARIES}
    assert "message_kind" in names
    assert "delivery_state" in names
    assert parse_closed(MessageKind, "approval_request") is MessageKind.APPROVAL_REQUEST
    assert parse_closed(DeliveryState, "dead_letter") is DeliveryState.DEAD_LETTER
    assert {
        "handoff",
        "reply",
        "notify",
        "review_request",
        "status",
        "question",
        "approval_request",
    } == MESSAGE_KIND_VALUES
    assert {
        "delivered",
        "queued",
        "woke",
        "deferred",
        "dead_letter",
    } == DELIVERY_STATE_VALUES
    assert HUMAN_APPROVAL_CHANNEL is MessageKind.APPROVAL_REQUEST
    assert is_human_approval_channel("approval_request")
    assert is_human_approval_channel(MessageKind.APPROVAL_REQUEST)
    assert not is_human_approval_channel("handoff")
    assert not is_human_approval_channel("review_request")


def test_envelope_carries_required_fields_and_omits_optional_nulls() -> None:
    parsed = parse_envelope(_envelope_body(mission_ref="mission-1", causation_id="cause-1"))
    assert is_ok(parsed)
    payload = parsed.value.to_payload()
    assert payload["msg_id"] == "msg-1"
    assert payload["from"] == _owner().value
    assert payload["to"] == _owner(slug="peer").value
    assert payload["kind"] == "notify"
    assert payload["correlation_id"] == "corr-1"
    assert payload["body"] == "ping"
    assert payload["priority"] == 0
    assert payload["created_at"] == 1_700_000_000_000_000_000
    assert payload["artifact_refs"] == []
    assert payload["mission_ref"] == "mission-1"
    assert payload["causation_id"] == "cause-1"
    assert "task_ref" not in payload
    assert "reply_to_ref" not in payload
    assert {
        "msg_id",
        "from",
        "to",
        "kind",
        "correlation_id",
        "body",
        "priority",
        "created_at",
    } == ENVELOPE_REQUIRED_FIELDS
    assert {
        "mission_ref",
        "task_ref",
        "reply_to_ref",
        "causation_id",
    } == ENVELOPE_OPTIONAL_REFS


def test_optional_refs_are_omitted_never_null() -> None:
    refused = parse_envelope(_envelope_body(mission_ref=None))
    assert is_refusal(refused)
    assert refused.context["field"] == "mission_ref"
    from_refused = parse_envelope({**_envelope_body(), "from_ref": "quant:research/lead"})
    assert is_refusal(from_refused)
    assert from_refused.context["field"] == "from"


def test_correlation_id_is_mandatory() -> None:
    body = _envelope_body()
    body.pop("correlation_id")
    refused = parse_envelope(body)
    assert is_refusal(refused)
    assert refused.context["field"] == "envelope"
    blank = parse_envelope(_envelope_body(correlation_id=""))
    assert is_refusal(blank)
    assert blank.context["field"] == "correlation_id"


def test_invented_kind_and_delivery_state_are_refused() -> None:
    invented = parse_message_kind("escalate")
    assert is_refusal(invented)
    assert invented.context["field"] == "kind"
    human = parse_message_kind("human_approval")
    assert is_refusal(human)
    bounced = parse_delivery_state("bounced")
    assert is_refusal(bounced)
    assert bounced.context["field"] == "delivery_state"
    dropped = parse_delivery_state("dropped")
    assert is_refusal(dropped)


def test_agent_is_never_a_to_address() -> None:
    refused = parse_envelope(_envelope_body(to="agent:runner-1"))
    assert is_refusal(refused)
    assert refused.context["field"] == "to"


def test_fp1_identity_excludes_correlation_and_causation() -> None:
    first = parse_envelope(_envelope_body(correlation_id="corr-a", causation_id="cause-a"))
    second = parse_envelope(_envelope_body(correlation_id="corr-b", causation_id="cause-b"))
    assert is_ok(first) and is_ok(second)
    identity_a = envelope_identity_content(first.value)
    identity_b = envelope_identity_content(second.value)
    assert "correlation_id" not in identity_a
    assert "causation_id" not in identity_a
    assert {"correlation_id", "causation_id"} == ENVELOPE_FP1_EXCLUDED_FIELDS
    hashed_a = content_address(dict(identity_a))
    hashed_b = content_address(dict(identity_b))
    assert is_ok(hashed_a) and is_ok(hashed_b)
    assert hashed_a.value == hashed_b.value
    distinct = content_address(dict(first.value.to_payload()))
    other = content_address(dict(second.value.to_payload()))
    assert is_ok(distinct) and is_ok(other)
    assert distinct.value != other.value


def test_deferred_gaps_stay_open() -> None:
    external = refuse_external_agent_transport()
    assert external.context["gap"] == GAP_0079_EXTERNAL_TRANSPORT
    assert external.context["deferred"] is True
    lead = refuse_lead_mailbox_catch_all()
    assert lead.context["gap"] == GAP_0071_LEAD_MAILBOX_CATCH_ALL
    assert lead.context["deferred"] is True
    assert GAP_0071_LEAD_MAILBOX_CATCH_ALL == "GAP-0071"
    assert GAP_0079_EXTERNAL_TRANSPORT == "GAP-0079"
