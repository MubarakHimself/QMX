"""Scaffold surfaces: identity excludes SemVer, doors, backends, CLI."""

from __future__ import annotations

from typing import get_args

from qmb._backends import VENUE_PACKAGE
from qmb._refuse import clean_token, invalid, policy, stale, storage, unavailable, unsupported
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
        qmb.composition_identity(),
        qmb.spread_identity(),
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
    assert qmb.SUBPHASES == (
        "frontier-advance",
        "scheduled-position-events",
        "resting-orders",
        "closed-data-indicators-structure",
        "strategy-callbacks",
        "new-intents-rest",
    )
    assert qmb.SAME_SLICE_NEW_INTENT_FILL is False
    assert qmb.COMPLETED_BOUNDARY_ONLY is True
    assert qmb.FORMING_BAR_ACTIONABLE is False
    assert qmb.FORMING_BAR_VISIBLE is False
    assert qmb.LOOKAHEAD_PREVENTION_INDEPENDENT_OF_GAP_0048 is True
    assert api.run is qmb.run
    assert api.run_slice is qmb.run_slice
    assert api.act_on_bar is qmb.act_on_bar
    assert api.consume_same_slice is qmb.consume_same_slice
    assert qmb.WARMUP_MECHANISM == "in-loop-locked"
    assert qmb.WARMUP_UNIT == "observation-count"
    assert qmb.WARMUP_ADDS_SECOND_WINDOW is False
    assert qmb.PRESEED_IS_WARMUP is False
    assert api.WARMUP_MECHANISM is qmb.WARMUP_MECHANISM
    assert api.preseed_indicator_buffers is qmb.preseed_indicator_buffers
    assert api.SplitEmbargo is qmb.SplitEmbargo
    assert qmb.CANCEL_AT == "slice-boundary"
    assert qmb.TERMINAL_ABORTED == "aborted"
    assert qmb.PARTIAL_GOVERNED_RESULT_ON_ABORT is False
    assert qmb.TIME_LIMIT_KEY == "qmb_run_time_limit"
    assert qmb.MEMORY_LIMIT_KEY == "qmb_run_memory_limit"
    assert api.CancelToken is qmb.CancelToken
    assert api.ProgressSink is qmb.ProgressSink
    assert api.ScriptedLimitProbe is qmb.ScriptedLimitProbe
    assert api.check_slice_boundary is qmb.check_slice_boundary
    assert api.refuse_aborted is qmb.refuse_aborted
    assert qmb.RESULT_CONTRACT == "CT-32"
    assert qmb.CHART_SERIES_IN_IDENTITY is False
    assert qmb.HTML_PAYLOAD is False
    assert qmb.CONCURRENCY_IS_SCHEDULING_ONLY is True
    assert api.reproduce_run is qmb.reproduce_run
    assert api.mint_run_performance_result is qmb.mint_run_performance_result
    assert api.require_reproduced_fingerprint is qmb.require_reproduced_fingerprint
    assert api.PerformanceResult is qmb.PerformanceResult
    assert api.construct_conformant_bot is qmb.construct_conformant_bot
    assert api.drive_instant is qmb.drive_instant
    assert api.ConformantSliceHandler is qmb.ConformantSliceHandler
    assert api.FunctionFactory is qmb.FunctionFactory
    assert api.HostedBot is qmb.HostedBot
    assert api.fold_canonical_assignment is qmb.fold_canonical_assignment
    assert api.parameter_space_from_bot is qmb.parameter_space_from_bot
    assert not hasattr(qmb, "run_sandbox")
    assert "run_sandbox" not in qmb.__all__
    assert api.spawn_run is qmb.spawn_run
    assert api.start_run is qmb.start_run
    assert api.collect_run is qmb.collect_run
    assert api.abort_run is qmb.abort_run
    assert api.ProcessLimitProbe is qmb.ProcessLimitProbe
    assert api.spawn_concurrent is qmb.spawn_concurrent
    assert api.spawn_governed is qmb.spawn_governed
    assert api.ResourceGovernor is qmb.ResourceGovernor
    assert qmb.SPAWN_MODEL == "process-per-run"
    assert qmb.ABORT_KILLS_SIBLINGS is False
    assert qmb.orchestrator_identity()["time_limit_key"] == qmb.TIME_LIMIT_KEY
    assert qmb.orchestrator_identity()["memory_limit_key"] == qmb.MEMORY_LIMIT_KEY
    assert qmb.PROCESS_MANAGEMENT == "stdlib.subprocess"
    assert qmb.CPU_BUDGET_KEY == "qmb_governor_cpu_budget"
    assert qmb.MEMORY_BUDGET_KEY == "qmb_governor_memory_budget"
    assert qmb.orchestrator_identity()["ray"] == "absent"
    assert qmb.orchestrator_identity()["docker"] == "not-required"
    assert qmb.orchestrator_identity()["daemon"] == "not-required"
    assert qmb.orchestrator_identity()["one_writer_per_stream"] is True
    assert qmb.orchestrator_identity()["cpu_budget_key"] == qmb.CPU_BUDGET_KEY
    assert qmb.orchestrator_identity()["sandbox_concurrent_motivating_reference"] == (
        "not-a-validated-budget"
    )
    assert qmb.ONE_LINE_PER_RUN is True
    assert qmb.STORES_VERDICT is False
    assert qmb.BOOK_BAR_READ_ROLE == "confirmation"
    assert qmb.PROVENANCE_SANDBOX == "sandbox"
    assert api.finish_run is qmb.finish_run
    assert api.LedgerSink is qmb.LedgerSink
    assert api.read_book_bar is qmb.read_book_bar
    assert api.read_merge_view is qmb.read_merge_view
    assert api.mint_completed_line is qmb.mint_completed_line
    assert api.mint_aborted_line is qmb.mint_aborted_line
    assert qmb.ledger_identity()["writer_scope"] == ("machine", "role", "worker-slot")
    assert qmb.orchestrator_identity()["ledger_writes"] == "orchestrator"
    assert api.LogSink is qmb.LogSink
    assert api.OperationalRecord is qmb.OperationalRecord
    assert api.propagate_correlation is qmb.propagate_correlation
    assert api.read_run_log is qmb.read_run_log
    assert qmb.LOG_IS_EVIDENCE is False
    assert qmb.CORRELATION_ID_EXCLUDED_FROM_FP1 is True
    assert qmb.orchestrator_identity()["log_writes"] == "orchestrator"
    assert qmb.orchestrator_identity()["log_is_evidence"] is False
    assert qmb.orchestrator_identity()["evidence_bearing_formats"] == ("raw archive", "journal")


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
    assert api.STRUCTURAL_SEED is qmb.STRUCTURAL_SEED
    assert api.fingerprint_layers is qmb.fingerprint_layers


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
    assert storage("ledger", "disk full").category is RefusalCategory.STORAGE_FAILURE


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
    for group in ("backtest", "data", "optimize", "ledger", "config"):
        assert group in helped.output
