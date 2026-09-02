"""Story 44.6 — environment, image, host, and profile reachability barrier."""

from __future__ import annotations

from pathlib import Path

import pytest
from qma.core.barriers.reachability import (
    DENIED_HOST_PATTERNS,
    FORBIDDEN_IMAGE_TOKENS,
    FORBIDDEN_MODEL_ADAPTERS,
    GAP_0070_DESKTOP_EXCLUSION,
    HANDED_VIA_SURFACES,
    REACHABILITY_DENIAL_NOT_LIFTABLE_BY,
    REACHABILITY_DENY_LIST_OWNER,
    DeniedHostClass,
    ReachabilityBarrierError,
    assert_deny_list_not_waivable,
    classify_denied_host,
    is_denied_host,
    is_forbidden_image_token,
    is_forbidden_model_adapter,
    parse_declaration,
    refuse_forbidden_model_adapter,
    refuse_handed_venue_login,
    refuse_reachability_waiver,
    validate_computer_use_profile,
    validate_network_posture,
    validate_worker_image,
)
from qma.core.ports.execution import ComputerUseProfile, WorkerImageManifest
from qma.core.ports.model import LOCAL_PROXY_ADAPTERS, OPENCODEX_ADAPTER
from qma.core.refusals import ProhibitedReachability
from qma.core.vocabulary.enums import NetworkPolicy
from qmf.core import is_ok, is_refusal

AGENTS_ROOT = Path(__file__).resolve().parents[3]


def test_network_requires_none_or_allowlist_no_open_default() -> None:
    missing = validate_network_posture(None, ())
    assert is_refusal(missing)
    assert ProhibitedReachability.matches(missing)
    assert missing.context["reason"] == "missing_network"
    assert missing.context["stage"] == "registration"

    opened = validate_network_posture("open", ("pypi.org",))
    assert is_refusal(opened)
    assert opened.context["reason"] == "open_network"

    invented = validate_network_posture("bridge", ("pypi.org",))
    assert is_refusal(invented)
    assert invented.context["reason"] == "invalid_network"

    none_ok = validate_network_posture(NetworkPolicy.NONE, ())
    assert is_ok(none_ok)
    assert none_ok.value[0] is NetworkPolicy.NONE
    assert none_ok.value[1] == ()


def test_none_enumerates_empty_set_unenumerated_refused() -> None:
    unenumerated = validate_network_posture(NetworkPolicy.NONE, None)
    assert is_refusal(unenumerated)
    assert unenumerated.context["reason"] == "unenumerated_hosts"

    extra = validate_network_posture(NetworkPolicy.NONE, ("pypi.org",))
    assert is_refusal(extra)
    assert extra.context["reason"] == "none_with_hosts"

    empty_allowlist = validate_network_posture(NetworkPolicy.ALLOWLIST, ())
    assert is_refusal(empty_allowlist)
    assert empty_allowlist.context["reason"] == "unenumerated_hosts"

    listed = validate_network_posture("allowlist", ("pypi.org", "files.pythonhosted.org"))
    assert is_ok(listed)
    assert listed.value[1] == ("pypi.org", "files.pythonhosted.org")


@pytest.mark.parametrize(
    "host",
    (
        "demo.ctraderapi.com",
        "live.ctraderapi.com",
        "*.ctraderapi.com",
        "api.icmarkets.com",
        "trading-node-vps",
        "qmn-vps",
        "openrouter.ai",
        "https://demo.ctraderapi.com:5035/path",
    ),
)
def test_deny_list_refuses_direct_names_and_wildcards(host: str) -> None:
    assert is_denied_host(host)
    refused = validate_network_posture("allowlist", (host,))
    assert is_refusal(refused)
    assert ProhibitedReachability.matches(refused)
    assert refused.context["reason"] == "denied_host"
    assert refused.context["stage"] == "registration"


def test_deny_list_is_code_declared_and_not_waivable() -> None:
    assert REACHABILITY_DENY_LIST_OWNER == "AD-28"
    assert "demo.ctraderapi.com" in DENIED_HOST_PATTERNS
    assert classify_denied_host("demo.ctraderapi.com") is DeniedHostClass.VENUE
    assert classify_denied_host("trading-node-vps") is DeniedHostClass.TRADING_NODE
    assert classify_denied_host("openrouter.ai") is DeniedHostClass.OPENROUTER
    assert_deny_list_not_waivable()
    with pytest.raises(ReachabilityBarrierError, match="may not be waived"):
        assert_deny_list_not_waivable(DENIED_HOST_PATTERNS - {"demo.ctraderapi.com"})
    for via in REACHABILITY_DENIAL_NOT_LIFTABLE_BY:
        waiver = refuse_reachability_waiver(via=via, host="demo.ctraderapi.com")
        assert ProhibitedReachability.matches(waiver)
        assert waiver.context["via"] == via
        assert waiver.context["reason"] == "waiver_not_liftable"
        assert waiver.context["stage"] == "registration"


def test_image_validation_refuses_venue_broker_and_node_client() -> None:
    assert "qmf-venue" in FORBIDDEN_IMAGE_TOKENS
    assert is_forbidden_image_token("qmf.venue.connection") in {
        "qmf.venue",
        "qmf_venue",
        "qmf-venue",
    }
    assert is_forbidden_image_token("qmn.client") == "qmn.client"
    assert is_forbidden_image_token("ccxt") == "ccxt"
    assert is_forbidden_image_token("qma-core") is None

    venue = validate_worker_image(
        WorkerImageManifest.from_values(imports=("qmf.venue",), packages=("qmf-venue",))
    )
    assert is_refusal(venue)
    assert venue.context["reason"] == "forbidden_image"
    assert venue.context["matched"] in {"qmf.venue", "qmf_venue", "qmf-venue"}

    node = validate_worker_image(
        WorkerImageManifest.from_values(image="registry.local/qmn-client:latest")
    )
    assert is_refusal(node)
    assert node.context["reason"] == "forbidden_image"

    clean = validate_worker_image(
        WorkerImageManifest.from_values(image="qma-worker:isolated", packages=("qma-core",))
    )
    assert is_ok(clean)


def test_remote_host_and_desktop_refused_by_host_identity() -> None:
    vps = parse_declaration(
        kind="remote_host",
        network="none",
        reachable_hosts=(),
        provider_ref="trading-node-vps",
        host="trading-node-vps",
    )
    assert is_refusal(vps)
    assert vps.context["reason"] == "trading_node_host"
    assert vps.context["kind"] == "remote_host"
    assert vps.context["stage"] == "registration"

    credentialed = parse_declaration(
        kind="desktop",
        network="none",
        reachable_hosts=(),
        provider_ref="operator-workstation",
        host="operator-workstation",
        carries_trading_credential=True,
    )
    assert is_refusal(credentialed)
    assert credentialed.context["reason"] == "trading_credential_host"

    running = parse_declaration(
        kind="remote_host",
        network="none",
        reachable_hosts=(),
        provider_ref="research-box",
        host="research-box",
        running_node=True,
    )
    assert is_refusal(running)
    assert running.context["reason"] == "running_node_host"


def test_computer_use_profile_carries_no_venue_state() -> None:
    clean = validate_computer_use_profile(
        ComputerUseProfile.from_values(reachable_hosts=("pypi.org",))
    )
    assert is_ok(clean)

    cookies = validate_computer_use_profile(
        ComputerUseProfile.from_values(cookie_hosts=("demo.ctraderapi.com",))
    )
    assert is_refusal(cookies)
    assert cookies.context["reason"] == "venue_profile_state"

    login = validate_computer_use_profile(
        ComputerUseProfile.from_values(venue_logins=("ctrader-session",))
    )
    assert is_refusal(login)
    assert login.context["reason"] == "venue_profile_state"

    creds = validate_computer_use_profile(
        ComputerUseProfile.from_values(saved_credential_refs=("cred://broker/icmarkets",))
    )
    assert is_refusal(creds)
    assert creds.context["reason"] == "venue_profile_state"


@pytest.mark.parametrize("via", sorted(HANDED_VIA_SURFACES))
def test_venue_login_cannot_be_handed_through_agent_surfaces(via: str) -> None:
    handed = validate_computer_use_profile(ComputerUseProfile.from_values(handed_via=via))
    assert is_refusal(handed)
    assert handed.context["reason"] == "handed_venue_login"
    assert handed.context["via"] == via
    assert handed.context["stage"] == "registration"
    direct = refuse_handed_venue_login(via=via, payload="spotware-login")
    assert ProhibitedReachability.matches(direct)
    assert direct.context["stage"] == "registration"


def test_gap_0070_planned_host_is_not_provisioned() -> None:
    assert GAP_0070_DESKTOP_EXCLUSION["gap"] == "GAP-0070"
    assert GAP_0070_DESKTOP_EXCLUSION["status"] == "deferred"
    assert GAP_0070_DESKTOP_EXCLUSION["provisioned"] == "false"


def test_openrouter_is_not_a_qma_path() -> None:
    assert "openrouter" in FORBIDDEN_MODEL_ADAPTERS
    assert is_forbidden_model_adapter("openrouter")
    assert not is_forbidden_model_adapter(OPENCODEX_ADAPTER)
    assert frozenset({OPENCODEX_ADAPTER}) == LOCAL_PROXY_ADAPTERS
    refused = refuse_forbidden_model_adapter("openrouter")
    assert refused is not None
    assert refused.context["reason"] == "openrouter_forbidden"
    for path in (AGENTS_ROOT / "packages").rglob("*.py"):
        if "tests" in path.parts or "__pycache__" in path.parts:
            continue
        if "openrouter" in path.read_text(encoding="utf-8").casefold():
            assert path.name in {"reachability.py", "registry.py", "context.py"}
