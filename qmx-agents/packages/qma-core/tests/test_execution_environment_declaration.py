"""Story 45.1 — ExecutionEnvironment declaration surface (FR-Q48)."""

from __future__ import annotations

import pytest
from qma.core.barriers.reachability import parse_declaration, validate_declaration_surface
from qma.core.ports.execution import (
    DECLARATION_SURFACE_FIELDS,
    EnvironmentMount,
    ExecutionEnvironmentDeclaration,
    is_control_channel_env_name,
)
from qma.core.refusals import ProhibitedReachability
from qma.core.vocabulary.enums import (
    EnvironmentLifecycle,
    ExecutionEnvironmentKind,
    NetworkPolicy,
)
from qma.core.vocabulary.registry import VocabularyError
from qmf.core import is_ok, is_refusal


def test_declaration_carries_complete_ct46_surface() -> None:
    declaration = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        mounts=({"source": "/opt/qma/readonly", "target": "/data", "mode": "ro", "shared": True},),
        environment_allowlist=("HTTP_PROXY", "NO_PROXY"),
        capabilities=("cpu", "memory"),
        lifecycle="ephemeral",
    )
    surface = declaration.surface()
    assert tuple(surface) == DECLARATION_SURFACE_FIELDS
    assert declaration.kind is ExecutionEnvironmentKind.DOCKER
    assert declaration.provider_ref == "local-docker"
    assert declaration.image == "qma-worker:isolated"
    assert declaration.mounts == (
        EnvironmentMount(
            source="/opt/qma/readonly",
            target="/data",
            mode="ro",
            shared=True,
        ),
    )
    assert declaration.environment_allowlist == ("HTTP_PROXY", "NO_PROXY")
    assert declaration.capabilities == ("cpu", "memory")
    assert declaration.network is NetworkPolicy.NONE
    assert declaration.lifecycle is EnvironmentLifecycle.EPHEMERAL


@pytest.mark.parametrize(
    ("kind", "lifecycle"),
    (
        ("local", "ephemeral"),
        ("docker", "ephemeral"),
        ("remote_container", "ephemeral"),
        ("remote_host", "persistent"),
        ("browser", "ephemeral"),
        ("desktop", "persistent"),
    ),
)
def test_closed_kind_and_lifecycle_values(kind: str, lifecycle: str) -> None:
    parsed = parse_declaration(
        kind=kind,
        network="none",
        reachable_hosts=(),
        provider_ref="workers",
        image="qma-worker:isolated",
        lifecycle=lifecycle,
        host="research-box" if kind in {"remote_host", "desktop"} else "",
    )
    assert is_ok(parsed)
    assert parsed.value.kind.value == kind
    assert parsed.value.lifecycle.value == lifecycle


def test_invented_kind_and_lifecycle_refused() -> None:
    with pytest.raises(VocabularyError):
        ExecutionEnvironmentDeclaration.try_parse(
            kind="kube",
            network="none",
            reachable_hosts=(),
            provider_ref="workers",
        )
    invented = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="workers",
        image="qma-worker:isolated",
        lifecycle="always_on",
    )
    assert is_refusal(invented)
    assert ProhibitedReachability.matches(invented)
    assert invented.context["reason"] == "invalid_lifecycle"
    assert invented.context["stage"] == "registration"
    invented_kind = parse_declaration(
        kind="kube",
        network="none",
        reachable_hosts=(),
        provider_ref="workers",
        image="qma-worker:isolated",
    )
    assert is_refusal(invented_kind)
    assert invented_kind.context["reason"] == "invalid_kind"


def test_ordinary_docker_worker_is_ephemeral_per_worker() -> None:
    ordinary = ExecutionEnvironmentDeclaration.ordinary_docker_worker()
    assert ordinary.kind is ExecutionEnvironmentKind.DOCKER
    assert ordinary.lifecycle is EnvironmentLifecycle.EPHEMERAL
    assert ordinary.mounts == ()
    assert ordinary.network is NetworkPolicy.NONE
    assert ordinary.is_docker_per_worker()
    assert not any(mount.is_shared_dirty() for mount in ordinary.mounts)


def test_shared_writable_mount_is_dirty_filesystem() -> None:
    dirty = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        mounts=(
            {"source": "/var/lib/qma/shared", "target": "/work", "mode": "rw", "shared": True},
        ),
    )
    assert is_refusal(dirty)
    assert dirty.context["reason"] == "shared_dirty_filesystem"
    assert dirty.context["stage"] == "registration"
    assert dirty.context["surface"] == "mounts"


def test_environment_allowlist_is_declarative_not_control_channel() -> None:
    ok = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        environment_allowlist=("LANG", "TZ"),
    )
    assert is_ok(ok)
    assignment = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        environment_allowlist=("QMA_CONTROL=enable",),
    )
    assert is_refusal(assignment)
    assert assignment.context["reason"] in {"control_channel", "invalid_env_var"}
    named = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        environment_allowlist=("QMA_CONTROL_CHANNEL",),
    )
    assert is_refusal(named)
    assert named.context["reason"] == "control_channel"
    assert is_control_channel_env_name("QMA_CONTROL_CHANNEL")
    assert is_control_channel_env_name("PATH=evil")
    assert not is_control_channel_env_name("LANG")


def test_network_none_or_allowlist_only() -> None:
    isolated = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
    )
    assert is_ok(isolated)
    listed = parse_declaration(
        kind="docker",
        network="allowlist",
        reachable_hosts=("pypi.org", "files.pythonhosted.org"),
        provider_ref="local-docker",
        image="qma-worker:isolated",
    )
    assert is_ok(listed)
    venue = parse_declaration(
        kind="docker",
        network="allowlist",
        reachable_hosts=("demo.ctraderapi.com",),
        provider_ref="local-docker",
        image="qma-worker:isolated",
    )
    assert is_refusal(venue)
    assert venue.context["reason"] == "denied_host"


def test_money_path_capability_refused_at_parse() -> None:
    refused = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="qma-worker:isolated",
        capabilities=("place_order",),
    )
    assert is_refusal(refused)
    assert refused.context["reason"] == "money_path_capability"
    assert refused.context["stage"] == "registration"


def test_docker_image_required() -> None:
    refused = parse_declaration(
        kind="docker",
        network="none",
        reachable_hosts=(),
        provider_ref="local-docker",
        image="",
    )
    assert is_refusal(refused)
    assert refused.context["reason"] == "missing_image"


def test_missing_provider_ref_refused() -> None:
    parsed = ExecutionEnvironmentDeclaration.try_parse(
        kind="local",
        network="none",
        reachable_hosts=(),
        provider_ref="",
    )
    refused = validate_declaration_surface(parsed)
    assert is_refusal(refused)
    assert refused.context["reason"] == "missing_provider_ref"
