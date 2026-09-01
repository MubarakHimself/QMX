"""Story 44.6 — daemon registration and placement of the reachability barrier."""

from __future__ import annotations

from qma.core.barriers.reachability import (
    GAP_0070_DESKTOP_EXCLUSION,
    REACHABILITY_DENIAL_NOT_LIFTABLE_BY,
)
from qma.core.ports.execution import (
    ComputerUseProfile,
    ExecutionEnvironmentDeclaration,
    WorkerImageManifest,
)
from qma.core.ports.model import DeploymentRecord
from qma.core.ports.tools import ToolKind
from qma.core.refusals import NoEnvironment, ProhibitedMoneyPathTool, ProhibitedReachability
from qma.core.vocabulary.enums import ExecutionEnvironmentKind, ModelClass, NetworkPolicy
from qma.daemon.envs import ExecutionEnvironmentRegistry
from qma.daemon.proxy import DeploymentRegistry
from qma.daemon.tools import ToolRegistry
from qmf.core import is_ok, is_refusal


class _EnvStub:
    """Structural ExecutionEnvironment stand-in."""


def test_register_refuses_missing_network_before_binding() -> None:
    registry = ExecutionEnvironmentRegistry()
    refused = registry.register(ExecutionEnvironmentKind.DOCKER, _EnvStub())
    assert is_refusal(refused)
    assert ProhibitedReachability.matches(refused)
    assert refused.context["reason"] == "unenumerated_hosts"
    assert refused.context["stage"] == "registration"
    assert registry.is_empty()


def test_register_accepts_isolated_none_network() -> None:
    registry = ExecutionEnvironmentRegistry()
    declaration = ExecutionEnvironmentDeclaration.isolated(
        ExecutionEnvironmentKind.DOCKER,
        provider_ref="local-docker",
    )
    assert declaration.network is NetworkPolicy.NONE
    assert declaration.reachable_hosts == ()
    accepted = registry.register(
        ExecutionEnvironmentKind.DOCKER,
        _EnvStub(),
        declaration=declaration,
        provider_id="local-docker",
    )
    assert is_ok(accepted)
    lease = registry.evaluate_environment_lease(
        task_id="task:1",
        kind=ExecutionEnvironmentKind.DOCKER,
    )
    assert is_ok(lease)
    assert lease.value.provider_id == "local-docker"


def test_allowlist_naming_venue_host_is_refused_at_registration() -> None:
    registry = ExecutionEnvironmentRegistry()
    parsed = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="allowlist",
        reachable_hosts=("demo.ctraderapi.com",),
        provider_ref="workers",
        image="qma-worker:isolated",
    )
    refused = registry.register(
        ExecutionEnvironmentKind.DOCKER,
        _EnvStub(),
        declaration=parsed,
    )
    assert is_refusal(refused)
    assert refused.context["reason"] == "denied_host"
    assert refused.context["host"] == "demo.ctraderapi.com"
    assert registry.get("docker") is None


def test_wildcard_allowlist_covering_deny_list_is_refused() -> None:
    registry = ExecutionEnvironmentRegistry()
    parsed = ExecutionEnvironmentDeclaration.try_parse(
        kind="docker",
        network="allowlist",
        reachable_hosts=("*.ctraderapi.com",),
        provider_ref="workers",
    )
    refused = registry.register(
        ExecutionEnvironmentKind.DOCKER,
        _EnvStub(),
        declaration=parsed,
    )
    assert is_refusal(refused)
    assert refused.context["reason"] == "denied_host"


def test_role_mission_plugin_policy_hook_cannot_waive_host_denial() -> None:
    registry = ExecutionEnvironmentRegistry()
    for via in sorted(REACHABILITY_DENIAL_NOT_LIFTABLE_BY):
        waiver = registry.refuse_waiver(via=via, host="live.ctraderapi.com")
        assert ProhibitedReachability.matches(waiver)
        assert waiver.context["via"] == via
        assert waiver.context["stage"] == "registration"
        assert waiver.context["reason"] == "waiver_not_liftable"


def test_image_with_qmf_venue_or_node_client_refused() -> None:
    registry = ExecutionEnvironmentRegistry()
    venue = registry.register_worker_image(
        WorkerImageManifest.from_values(imports=("qmf.venue",), packages=("qmf-venue",))
    )
    assert is_refusal(venue)
    assert venue.context["reason"] == "forbidden_image"
    node = registry.register_worker_image(
        WorkerImageManifest.from_values(packages=("qmn",), image="qmn:latest")
    )
    assert is_refusal(node)
    broker_sdk = registry.register_worker_image(WorkerImageManifest.from_values(packages=("ccxt",)))
    assert is_refusal(broker_sdk)
    clean = registry.register_worker_image(
        WorkerImageManifest.from_values(image="qma-worker:isolated", packages=("qma-core",))
    )
    assert is_ok(clean)


def test_trading_node_vps_refused_at_registration_and_placement() -> None:
    registry = ExecutionEnvironmentRegistry()
    declaration = ExecutionEnvironmentDeclaration.try_parse(
        kind="remote_host",
        network="none",
        reachable_hosts=(),
        provider_ref="trading-node-vps",
        host="trading-node-vps",
    )
    registered = registry.register(
        ExecutionEnvironmentKind.REMOTE_HOST,
        _EnvStub(),
        declaration=declaration,
    )
    assert is_refusal(registered)
    assert registered.context["reason"] == "trading_node_host"
    assert registered.context["stage"] == "registration"

    placement = registry.place(
        task_id="task:place",
        kind=ExecutionEnvironmentKind.REMOTE_HOST,
        host="trading-node-vps",
    )
    assert is_refusal(placement)
    assert ProhibitedReachability.matches(placement)
    assert placement.context["stage"] == "placement"
    assert not NoEnvironment.matches(placement)


def test_unbound_kind_still_returns_no_environment() -> None:
    registry = ExecutionEnvironmentRegistry()
    missing = registry.evaluate_environment_lease(
        task_id="task:desktop",
        kind=ExecutionEnvironmentKind.DESKTOP,
    )
    assert is_refusal(missing)
    assert NoEnvironment.matches(missing)


def test_computer_use_profile_and_handed_login_refused() -> None:
    registry = ExecutionEnvironmentRegistry()
    dirty = registry.register_computer_use_profile(
        ComputerUseProfile.from_values(
            cookie_hosts=("live.ctraderapi.com",),
            venue_logins=("ctrader",),
        )
    )
    assert is_refusal(dirty)
    assert dirty.context["reason"] == "venue_profile_state"

    handed = registry.hand_profile_secret(via="knowledge", payload="broker-login")
    assert handed.context["reason"] == "handed_venue_login"
    assert handed.context["via"] == "knowledge"
    assert handed.context["stage"] == "registration"

    clean = registry.register_computer_use_profile(
        ComputerUseProfile.from_values(reachable_hosts=("pypi.org",))
    )
    assert is_ok(clean)


def test_gap_0070_host_is_not_provisioned() -> None:
    registry = ExecutionEnvironmentRegistry()
    assert GAP_0070_DESKTOP_EXCLUSION["provisioned"] == "false"
    assert ExecutionEnvironmentKind.DESKTOP.value not in registry.kinds()
    missing = registry.place(
        task_id="task:cu",
        kind=ExecutionEnvironmentKind.DESKTOP,
    )
    assert is_refusal(missing)
    assert NoEnvironment.matches(missing)


def test_trading_desk_stays_read_only_including_paper() -> None:
    tools = ToolRegistry()
    refused = tools.register(
        tool_id="trading-readonly:paper_place_order",
        kind=ToolKind.PLUGIN,
        schema={"name": "paper_place_order"},
        acts=("paper_only_submit_order",),
        tags=("paper_only",),
    )
    assert is_refusal(refused)
    assert ProhibitedMoneyPathTool.matches(refused)
    allowed = tools.register(
        tool_id="trading-readonly:positions",
        kind=ToolKind.PLUGIN,
        schema={"name": "positions"},
        acts=("read_positions",),
    )
    assert is_ok(allowed)


def test_openrouter_deployment_refused_at_registration() -> None:
    deployments = DeploymentRegistry()
    refused = deployments.register(
        DeploymentRecord(
            deployment_id="openrouter-workhorse",
            model_class=ModelClass.WORKHORSE_GENERAL,
            adapter="openrouter",
            context_tokens=8_000,
        )
    )
    assert is_refusal(refused)
    assert ProhibitedReachability.matches(refused)
    assert refused.context["reason"] == "openrouter_forbidden"
