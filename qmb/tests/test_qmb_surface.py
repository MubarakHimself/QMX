"""Scaffold surfaces: identity excludes SemVer, doors, backends, CLI."""

from __future__ import annotations

from typing import get_args

from qmb._backends import VENUE_PACKAGE
from qmb._refuse import clean_token, invalid, policy, stale, unavailable, unsupported
from qmb.doors import api
from qmb.doors.cli import main
from qmb.doors.mcp import main as mcp_main
from qmb.execution import AuthorizedIntent
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qmf.risk.door import EntryIntent, ExitIntent

import qmb


def test_distribution_identity_excludes_package_semver() -> None:
    payload = qmb.identity_payload()
    assert "version" not in payload
    assert qmb.__version__ not in payload.values()
    without_semver = fingerprint(payload)
    with_semver = fingerprint({**payload, "package_version": qmb.__version__})
    assert is_ok(without_semver)
    assert is_ok(with_semver)
    assert without_semver.value.value != with_semver.value.value
    assert without_semver.value.value.startswith("fp1:sha256:")


def test_seed_identities_exclude_semver() -> None:
    payloads = (
        qmb.loop_identity(),
        qmb.layers_identity(),
        qmb.read_port_identity(),
        qmb.ports_identity(),
        qmb.data_front_identity(),
        qmb.sampler_identity(),
        qmb.ladder_identity(),
        qmb.result_identity(),
        qmb.ledger_identity(),
        qmb.orchestrator_identity(),
        qmb.fragment_identity(),
        qmb.run_config_identity(),
    )
    for payload in payloads:
        assert qmb.__version__ not in payload.values()
        stamped = fingerprint(payload)
        assert is_ok(stamped)


def test_layer_fingerprint_is_stable() -> None:
    first = qmb.fingerprint_layers()
    second = qmb.fingerprint_layers()
    assert is_ok(first)
    assert is_ok(second)
    assert first.value.value == second.value.value


def test_backends_are_the_six_qmf_packages_never_venue() -> None:
    assert qmb.BACKEND_PACKAGES == (
        "qmf-core",
        "qmf-registry",
        "qmf-data",
        "qmf-indicators",
        "qmf-structure",
        "qmf-risk",
    )
    versions = qmb.backend_display_versions()
    assert tuple(versions) == qmb.BACKEND_PACKAGES
    assert "qmf-venue" not in versions
    for version in versions.values():
        assert version == "0.1.0"


def test_registry_state_is_an_as_of_set() -> None:
    assert qmb.STATE_KIND == "as-of set"
    assert qmb.read_port_identity()["state_kind"] == "as-of set"
    assert qmb.HUB_KIND == "passive-storage"
    assert qmb.read_port_identity()["hub"] == "passive-storage"
    assert qmb.STALE_EVIDENCE_SEVERITY_KEY == "qmb_stale_evidence_severity"
    assert api.RegistryReadPort is qmb.RegistryReadPort


def test_frontier_clock_is_qmf_core_clock() -> None:
    assert qmb.frontier_clock_name() == "qmf.core.chrono.Clock"
    assert qmb.LOOP_KIND == "event-slice"
    assert len(qmb.SUBPHASES) == 6


def test_authorized_intent_is_the_ct23_door_types() -> None:
    assert set(get_args(AuthorizedIntent)) == {EntryIntent, ExitIntent}


def test_mcp_door_refuses_invocation() -> None:
    refused = mcp_main()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def test_api_door_matches_library_surface() -> None:
    assert api.__version__ == qmb.__version__
    assert api.MCP_SHIPPED is qmb.MCP_SHIPPED
    assert api.BACKEND_PACKAGES == qmb.BACKEND_PACKAGES
    assert api.identity_payload() == qmb.identity_payload()
    assert api.STATE_KIND == qmb.STATE_KIND


def test_refuse_helpers_return_typed_refusals() -> None:
    assert clean_token("book-a") == "book-a"
    assert clean_token("  ") is None
    assert clean_token(1) is None
    assert invalid("field", "reason").category is RefusalCategory.INVALID_INPUT
    assert policy("field", "reason").category is RefusalCategory.POLICY_REJECTION
    assert unsupported("field", "reason").category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert unavailable("field", "reason").category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    refused = stale("field", "reason", severity="workspace-declared")
    assert refused.category is RefusalCategory.STALE_EVIDENCE
    assert refused.context["severity"] == "workspace-declared"


def test_venue_package_is_named_and_excluded() -> None:
    assert VENUE_PACKAGE == "qmf-venue"
    assert VENUE_PACKAGE not in qmb.BACKEND_PACKAGES


def test_cli_version_is_display_only() -> None:
    from click.testing import CliRunner

    runner = CliRunner()
    versioned = runner.invoke(main, ["--version"])
    assert versioned.exit_code == 0, versioned.output
    assert qmb.__version__ in versioned.output
    shown = runner.invoke(main, ["version"])
    assert shown.exit_code == 0, shown.output
    assert shown.output.strip() == qmb.__version__
    helped = runner.invoke(main, ["--help"])
    assert helped.exit_code == 0, helped.output
    assert "experimentation/backtesting" in helped.output
