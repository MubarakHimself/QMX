"""Story 45.2 — ExecutionEnvironment slot capacity (FR-Q49)."""

from __future__ import annotations

import pytest
from qma.core.barriers.reachability import parse_declaration
from qma.core.ports.execution import (
    ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT,
    ENVIRONMENT_MAX_IN_FLIGHT_KEY,
    PINNED_SINGLE_SLOT_KINDS,
    ExecutionEnvironmentDeclaration,
    is_pinned_single_slot_kind,
    max_in_flight_editability,
    resolve_max_in_flight,
)
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, VariableEditability
from qmf.core import is_ok, is_refusal


def test_default_capacity_cites_registry_key() -> None:
    ordinary = ExecutionEnvironmentDeclaration.ordinary_docker_worker()
    assert ordinary.max_in_flight == ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT
    capacity = ordinary.capacity()
    assert capacity["registry_key"] == ENVIRONMENT_MAX_IN_FLIGHT_KEY
    assert capacity["max_in_flight"] == ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT
    assert capacity["editability"] == VariableEditability.UI_EDITABLE.value
    assert capacity["pinned_single_slot"] is False
    resolved = resolve_max_in_flight(ExecutionEnvironmentKind.DOCKER)
    assert is_ok(resolved)
    assert resolved.value == ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT


@pytest.mark.parametrize(
    "kind",
    ("local", "docker", "remote_container", "browser"),
)
def test_editable_kinds_accept_declared_capacity(kind: str) -> None:
    assert not is_pinned_single_slot_kind(kind)
    assert max_in_flight_editability(kind) is VariableEditability.UI_EDITABLE
    parsed = parse_declaration(
        kind=kind,
        network="none",
        reachable_hosts=(),
        provider_ref="workers",
        image="qma-worker:isolated" if kind in {"docker", "remote_container"} else "",
        max_in_flight=3,
    )
    assert is_ok(parsed)
    assert parsed.value.max_in_flight == 3
    assert parsed.value.capacity()["editability"] == "ui-editable"


@pytest.mark.parametrize("kind", ("remote_host", "desktop"))
def test_pinned_kinds_are_uneditable_single_slot(kind: str) -> None:
    assert is_pinned_single_slot_kind(kind)
    assert max_in_flight_editability(kind) is VariableEditability.UNEDITABLE
    assert ExecutionEnvironmentKind(kind) in PINNED_SINGLE_SLOT_KINDS
    ok = parse_declaration(
        kind=kind,
        network="none",
        reachable_hosts=(),
        provider_ref="research-box",
        host="research-box",
        lifecycle="persistent",
    )
    assert is_ok(ok)
    assert ok.value.max_in_flight == ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT
    assert ok.value.capacity()["pinned_single_slot"] is True
    assert ok.value.capacity()["editability"] == "uneditable"

    refused = parse_declaration(
        kind=kind,
        network="none",
        reachable_hosts=(),
        provider_ref="research-box",
        host="research-box",
        lifecycle="persistent",
        max_in_flight=2,
    )
    assert is_refusal(refused)
    assert refused.context["reason"] == "max_in_flight_pinned"
    assert refused.context["registry_key"] == ENVIRONMENT_MAX_IN_FLIGHT_KEY
    assert refused.context["pinned"] == ENVIRONMENT_MAX_IN_FLIGHT_DEFAULT


def test_invalid_max_in_flight_refused() -> None:
    zero = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        max_in_flight=0,
    )
    assert is_refusal(zero)
    assert zero.context["reason"] == "invalid_max_in_flight"
    not_int = resolve_max_in_flight("docker", "two")
    assert is_refusal(not_int)
    assert not_int.context["reason"] == "invalid_max_in_flight"
