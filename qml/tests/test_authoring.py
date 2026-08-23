"""Scaffold surfaces: frozen types, protocol helpers, pure conformance, fp1."""

from __future__ import annotations

from typing import get_args

from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.door import EntryIntent, ExitIntent, ExitKind
from qml.conformance import DENIAL_SET, evaluate_ticket
from qml.declaration import AuthoredArtifact, AuthoredKind
from qml.families import StrategyFamilyId
from qml.footprint import ProducerBindingForm, parse_binding_form
from qml.protocol import BotIntent, permitted_exit_kinds

import qml


def test_authored_artifact_identity_excludes_package_semver() -> None:
    made = AuthoredArtifact.try_create(AuthoredKind.BOT_DEFINITION, 1, {"family": "x"})
    assert is_ok(made)
    payload = made.value.identity_payload()
    assert "version" not in payload
    assert qml.__version__ not in payload.values()
    without_semver = fingerprint(payload)
    with_semver = fingerprint({**payload, "package_version": qml.__version__})
    assert is_ok(without_semver)
    assert is_ok(with_semver)
    assert without_semver.value.value != with_semver.value.value
    assert without_semver.value.value.startswith("fp1:sha256:")


def test_authored_artifact_refuses_unknown_kind_and_bad_format() -> None:
    unknown = AuthoredArtifact.try_create("bot-spec", 1)
    assert is_refusal(unknown)
    assert unknown.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    not_a_kind = AuthoredArtifact.try_create(1, 1)
    assert is_refusal(not_a_kind)
    zero = AuthoredArtifact.try_create("confluence", 0)
    assert is_refusal(zero)
    assert zero.category is RefusalCategory.INVALID_INPUT
    flag = AuthoredArtifact.try_create("confluence", True)
    assert is_refusal(flag)
    not_int = AuthoredArtifact.try_create("confluence", "1")
    assert is_refusal(not_int)
    not_map = AuthoredArtifact.try_create("confluence", 1, body=["nope"])
    assert is_refusal(not_map)


def test_authored_artifact_accepts_string_kind_and_freezes_body() -> None:
    made = AuthoredArtifact.try_create("bot-definition", 1, {"k": "v"})
    assert is_ok(made)
    artifact = made.value
    assert artifact.kind is AuthoredKind.BOT_DEFINITION
    assert artifact.format_version == 1
    assert artifact.body["k"] == "v"
    empty = AuthoredArtifact.try_create(AuthoredKind.CONFLUENCE, 1)
    assert is_ok(empty)
    assert dict(empty.value.body) == {}


def test_strategy_family_id_is_opaque_and_verbatim() -> None:
    made = StrategyFamilyId.try_create("trend-follow")
    assert is_ok(made)
    assert made.value.value == "trend-follow"
    blank = StrategyFamilyId.try_create("  ")
    assert is_refusal(blank)
    assert blank.category is RefusalCategory.INVALID_INPUT
    assert is_refusal(StrategyFamilyId.try_create(None))


def test_producer_binding_form_closed_vocabulary() -> None:
    pinned = parse_binding_form("pinned-fingerprint")
    assert is_ok(pinned)
    assert pinned.value is ProducerBindingForm.PINNED_FINGERPRINT
    templated = parse_binding_form(ProducerBindingForm.TEMPLATE)
    assert is_ok(templated)
    bad = parse_binding_form("archetype")
    assert is_refusal(bad)
    assert is_refusal(parse_binding_form(None))


def test_permitted_exit_kinds_allow_empty_and_refuse_unknown() -> None:
    empty = permitted_exit_kinds(())
    assert is_ok(empty)
    assert empty.value == ()
    both = permitted_exit_kinds(("close_full", ExitKind.TIGHTEN_PROTECTIVE_STOP))
    assert is_ok(both)
    assert both.value == (ExitKind.CLOSE_FULL, ExitKind.TIGHTEN_PROTECTIVE_STOP)
    partial = permitted_exit_kinds(("close_partial",))
    assert is_refusal(partial)
    assert partial.category is RefusalCategory.INVALID_INPUT
    assert is_refusal(permitted_exit_kinds((1,)))


def test_bot_intent_is_the_ct23_door_types() -> None:
    assert set(get_args(BotIntent)) == {EntryIntent, ExitIntent}


def test_evaluate_ticket_requires_both_layers() -> None:
    ticket = evaluate_ticket(layer1_passed=True, layer2_passed=True)
    assert is_ok(ticket)
    assert ticket.value.layer1_passed is True
    refused = evaluate_ticket(layer1_passed=True, layer2_passed=False)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert is_refusal(evaluate_ticket(layer1_passed=False, layer2_passed=True))
    bad = evaluate_ticket(layer1_passed="yes", layer2_passed=True)
    assert is_refusal(bad)
    assert bad.category is RefusalCategory.INVALID_INPUT


def test_denial_set_names_impure_capabilities() -> None:
    assert frozenset({"clock", "io", "network", "undeclared_randomness"}) == DENIAL_SET
