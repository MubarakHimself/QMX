"""Story 46.5 — Quant WakePolicy definition (FR-Q61; CT-48)."""

from __future__ import annotations

from qma.core.ontology import (
    MAX_WAKES_PER_WINDOW_REGISTRY_KEY,
    QUANT_WRITE_COMMAND,
    QUIET_HOURS_REGISTRY_KEY,
    WAKE_CONDITION_ANY,
    WAKE_POLICY_EDITABILITY,
    WAKE_POLICY_HOME,
    WAKE_POLICY_SCOPE,
    DeskSlug,
    QuietHours,
    RoleName,
    SlugIndex,
    WakePolicy,
    authorize_quant_write,
    create_quant,
    parse_quiet_hours,
    parse_wake_policy,
    refuse_model_wake_policy_write,
    retire_quant,
    source_may_write_wake_policy,
    wake_conditions_match,
)
from qma.core.ports import mailbox as mailbox_port
from qma.core.refusals import OperatorPrincipalRequired
from qma.core.vocabulary.enums import (
    MessageKind,
    PrincipalClass,
    VariableEditability,
    VariableScope,
)
from qmf.core import is_ok, is_refusal


def test_wake_policy_is_operator_authored_ui_editable_quant_scoped() -> None:
    parsed = parse_wake_policy(
        {
            "wake_conditions": ["any"],
            "quiet_hours": {
                "start": "22:00",
                "end": "06:00",
                "iana_zone": "America/New_York",
            },
            "max_wakes_per_window": 3,
        }
    )
    assert is_ok(parsed)
    policy = parsed.value
    assert policy.scope is VariableScope.QUANT
    assert policy.editability is VariableEditability.UI_EDITABLE
    assert policy.ui_editable is True
    assert policy.home == "quant_record.WakePolicy"
    assert policy.SCOPE is WAKE_POLICY_SCOPE
    assert policy.EDITABILITY is WAKE_POLICY_EDITABILITY
    assert policy.HOME == WAKE_POLICY_HOME
    payload = policy.to_payload()
    assert payload["scope"] == "quant"
    assert payload["editability"] == "ui-editable"
    assert payload["home"] == WAKE_POLICY_HOME
    assert payload["quiet_hours_registry_key"] == QUIET_HOURS_REGISTRY_KEY
    assert payload["max_wakes_per_window_registry_key"] == MAX_WAKES_PER_WINDOW_REGISTRY_KEY
    assert QUIET_HOURS_REGISTRY_KEY == "registry:quant.quiet_hours"
    assert MAX_WAKES_PER_WINDOW_REGISTRY_KEY == "registry:quant.max_wakes_per_window"
    assert mailbox_port.QUIET_HOURS_REGISTRY_KEY == QUIET_HOURS_REGISTRY_KEY
    assert mailbox_port.MAX_WAKES_PER_WINDOW_REGISTRY_KEY == MAX_WAKES_PER_WINDOW_REGISTRY_KEY
    assert QUANT_WRITE_COMMAND == "quant.write"


def test_unauthored_policy_has_no_spine_default() -> None:
    index = SlugIndex(active_desk_slugs=frozenset({"research"}))
    minted = create_quant(
        desk_slug=DeskSlug.RESEARCH,
        quant_slug="nova",
        role=RoleName.RESEARCHER,
        name="Nova",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_ok(minted)
    assert minted.value.wake_policy is None
    refused = parse_wake_policy(None)
    assert is_refusal(refused)
    assert refused.context["field"] == "wake_policy"


def test_no_model_authors_alters_or_overrides_wake_policy() -> None:
    assert source_may_write_wake_policy("operator") is True
    assert source_may_write_wake_policy(QUANT_WRITE_COMMAND) is True
    assert source_may_write_wake_policy("model") is False
    assert source_may_write_wake_policy("agent") is False
    refused = refuse_model_wake_policy_write(source="model")
    assert is_refusal(refused)
    assert refused.context["command"] == QUANT_WRITE_COMMAND
    machine = authorize_quant_write(PrincipalClass.MACHINE)
    assert is_refusal(machine)
    assert OperatorPrincipalRequired.matches(machine)
    assert machine.context["command"] == QUANT_WRITE_COMMAND
    operator = authorize_quant_write("operator")
    assert is_ok(operator)
    assert operator.value is PrincipalClass.OPERATOR


def test_quiet_hours_are_daily_interval_plus_iana_zone() -> None:
    parsed = parse_quiet_hours({"start": "22:00", "end": "06:00", "iana_zone": "America/New_York"})
    assert is_ok(parsed)
    quiet = parsed.value
    assert isinstance(quiet, QuietHours)
    assert quiet.wraps_midnight is True
    assert quiet.contains_minute(23 * 60) is True
    assert quiet.contains_minute(3 * 60) is True
    assert quiet.contains_minute(6 * 60) is False
    assert quiet.contains_minute(12 * 60) is False
    assert quiet.registry_key == QUIET_HOURS_REGISTRY_KEY
    daytime = parse_quiet_hours({"start": "09:00", "end": "17:00", "iana_zone": "UTC"})
    assert is_ok(daytime)
    assert daytime.value.wraps_midnight is False
    assert daytime.value.contains_minute(10 * 60) is True
    assert daytime.value.contains_minute(17 * 60) is False
    missing_zone = parse_quiet_hours({"start": "22:00", "end": "06:00", "iana_zone": ""})
    assert is_refusal(missing_zone)


def test_wake_conditions_are_any_or_message_kind() -> None:
    parsed = parse_wake_policy({"wake_conditions": ["notify", "handoff"]})
    assert is_ok(parsed)
    assert parsed.value.matches(MessageKind.NOTIFY)
    assert parsed.value.matches("handoff")
    assert not parsed.value.matches(MessageKind.STATUS)
    assert wake_conditions_match(frozenset({WAKE_CONDITION_ANY}), MessageKind.QUESTION)
    invented = parse_wake_policy({"wake_conditions": ["escalate"]})
    assert is_refusal(invented)
    port = mailbox_port.parse_wake_policy({"wake_conditions": ["any"]})
    assert is_ok(port)


def test_retire_quant_preserves_operator_wake_policy() -> None:
    policy = WakePolicy(
        wake_conditions=frozenset({WAKE_CONDITION_ANY}),
        quiet_hours=QuietHours(start_minute=22 * 60, end_minute=6 * 60, iana_zone="UTC"),
        max_wakes_per_window=2,
    )
    index = SlugIndex(active_desk_slugs=frozenset({"research"}))
    minted = create_quant(
        desk_slug=DeskSlug.RESEARCH,
        quant_slug="keeper",
        role=RoleName.RESEARCHER,
        name="Keeper",
        principal=PrincipalClass.OPERATOR,
        index=index,
    )
    assert is_ok(minted)
    authored = minted.value.with_wake_policy(policy)
    retired, _tombstone = retire_quant(authored)
    assert retired.wake_policy == policy
    assert retired.retired is True
