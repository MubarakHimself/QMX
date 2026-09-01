"""Story 25.5 — bind doors first, then preflight → compose → fingerprint → seal."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Result, is_ok, is_refusal
from qmn.config import config_init
from qmn.host import (
    BOOT_BOUND_SURFACES,
    BOOT_CEREMONY_STEPS,
    BOOT_CEREMONY_SURFACE,
    BOOT_STAGES,
    CHECK_MODE_EXIT_ON_REFUSAL,
    CHECK_MODE_OPENS_SEQUENCER,
    CHECK_MODE_PREFLIGHT_CHECKS,
    COMPOSITION_ROOT_SURFACE,
    DOOR_BIND_FAILURE_EXIT_CODE,
    FULL_PREFLIGHT_CHECKS,
    HAS_OPERATOR_CLI,
    SUPERVISOR_ROLE,
    SUPERVISOR_STREAM,
    BoundSupervisorDoors,
    CompositionFingerprintInputs,
    InMemoryBootAttemptSink,
    PreflightFacts,
    allocate_writer_ids,
    bind_supervisor_doors,
    ceremony_steps,
    compute_composition_fp,
    preflight_checks_for_mode,
    reserved_supervisor_writer,
    run_boot_ceremony,
    run_check_mode,
    supervisor_writer_is_reserved,
)
from qmn.host._refuse import invalid

T = TypeVar("T")

_QMN_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "cite", "label": label}))


def _inputs(label: str = "boot-a") -> CompositionFingerprintInputs:
    return CompositionFingerprintInputs(
        config_fp=_fp(f"config-{label}"),
        distribution_identities={
            "qmf": "lockstep",
            "qmb": "0.1.0",
            "qml": "0.1.0",
            "qmn": "0.1.0",
        },
        extension_identities={"qmf-calendar-forex": "1.0.0"},
        proto_release_tag="proto-1",
        tzdata_version="2026a",
        adapter_capability_fps=(_fp("cap-ctrader"),),
        registry_as_of_fp=_fp("as-of-1"),
        calendar_code_identities={
            "market_hours_calendar": "mh-code-1",
            "day_boundary_calendar": "db-code-1",
            "news_calendar": "news-code-1",
        },
        os_cpu_class="linux-x86_64",
    )


def _streams() -> tuple[tuple[str, str], ...]:
    return (
        ("command", "venue-a:acct-1"),
        ("adapter", "venue-a:acct-1:feed"),
        ("risk", "binding-1"),
    )


def test_surface_markers_and_ordered_ceremony() -> None:
    assert BOOT_CEREMONY_SURFACE == COMPOSITION_ROOT_SURFACE == "qmn.host"
    assert ceremony_steps() == BOOT_CEREMONY_STEPS == (
        "preflight",
        "compose",
        "fingerprint",
        "seal",
    )
    assert BOOT_STAGES[0] == "doors_bound"
    assert BOOT_STAGES[-1] == "seal"
    assert BOOT_BOUND_SURFACES == (
        "evidence_channel",
        "preflight_status",
        "resurrect_power",
    )
    assert HAS_OPERATOR_CLI is False
    assert CHECK_MODE_OPENS_SEQUENCER is False
    assert CHECK_MODE_EXIT_ON_REFUSAL is True
    assert "chrony_waitsync" in FULL_PREFLIGHT_CHECKS
    assert "credential_is_set" in FULL_PREFLIGHT_CHECKS
    assert "store_reachability" in FULL_PREFLIGHT_CHECKS
    assert "chrony_waitsync" not in CHECK_MODE_PREFLIGHT_CHECKS
    assert "credential_is_set" not in CHECK_MODE_PREFLIGHT_CHECKS
    assert "store_reachability" not in CHECK_MODE_PREFLIGHT_CHECKS
    assert _ok(preflight_checks_for_mode("live")) == FULL_PREFLIGHT_CHECKS
    assert _ok(preflight_checks_for_mode("check")) == CHECK_MODE_PREFLIGHT_CHECKS


def test_doors_bind_first_boot_attempt_is_first_durable_write() -> None:
    sink = InMemoryBootAttemptSink()
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-1",
            machine="vps-a",
            composition_inputs=_inputs(),
            writer_streams=_streams(),
            boot_attempt_sink=sink,
            preflight=PreflightFacts(
                required_credential_refs=("venue-token",),
                credential_is_set={"venue-token": True},
            ),
        )
    )
    assert outcome.doors.bound is True
    assert outcome.doors.surfaces() == BOOT_BOUND_SURFACES
    assert outcome.doors.preflight_status_ready is True
    assert outcome.doors.resurrect_power_ready is True
    assert len(sink.records) == 1
    first = sink.records[0]
    assert first.sequence == 0
    assert first.stage == "seal"
    assert supervisor_writer_is_reserved(first.writer)
    assert first.writer.role == SUPERVISOR_ROLE
    assert first.writer.stream == SUPERVISOR_STREAM
    assert first.composition_fp == outcome.composition_fp
    assert outcome.sealed is True
    assert outcome.ready is True
    assert outcome.stand_down_alive is False
    assert outcome.opens_sequencer is True
    assert outcome.exit_code is None
    assert outcome.writer_allocation is not None
    assert outcome.writer_allocation.pairwise_distinct() is True
    assert supervisor_writer_is_reserved(outcome.writer_allocation.supervisor)


def test_door_bind_failure_exits_nonzero_before_stand_down() -> None:
    sink = InMemoryBootAttemptSink()

    def _failing_binder() -> Result[BoundSupervisorDoors]:
        return invalid("doors", "evidence channel address already in use")

    refused = run_boot_ceremony(
        boot_epoch_id="boot-1",
        machine="vps-a",
        composition_inputs=_inputs(),
        boot_attempt_sink=sink,
        door_binder=_failing_binder,
    )
    assert is_refusal(refused)
    assert refused.context["exits_nonzero"] is True
    assert refused.context["exit_code"] == DOOR_BIND_FAILURE_EXIT_CODE
    assert refused.context["stand_down_alive"] is False
    assert sink.records == []  # no durable write when doors cannot bind


def test_preflight_refusal_enters_stand_down_alive_with_status_evidence() -> None:
    sink = InMemoryBootAttemptSink()
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-1",
            machine="vps-a",
            composition_inputs=_inputs(),
            writer_streams=_streams(),
            boot_attempt_sink=sink,
            preflight=PreflightFacts(
                chrony_synced=False,
                required_credential_refs=("venue-token",),
                credential_is_set={"venue-token": True},
            ),
        )
    )
    assert outcome.stand_down_alive is True
    assert outcome.ready is False
    assert outcome.sealed is False
    assert outcome.opens_sequencer is False
    assert outcome.exit_code is None  # does not exit — doors keep serving
    assert outcome.failure_id == "preflight.clock.chrony"
    assert outcome.doors.bound is True
    assert outcome.preflight_status["stand_down_alive"] is True
    assert sink.records[0].failure_id == "preflight.clock.chrony"
    assert sink.records[0].stage == "preflight"


def test_compose_allocates_pairwise_distinct_writer_ids_and_reserves_supervisor() -> None:
    allocation = _ok(
        allocate_writer_ids(
            machine="vps-a",
            boot_epoch_id="boot-1",
            streams=_streams(),
        )
    )
    assert allocation.pairwise_distinct() is True
    assert supervisor_writer_is_reserved(allocation.supervisor)
    colliding = allocate_writer_ids(
        machine="vps-a",
        boot_epoch_id="boot-1",
        streams=(("command", "same"), ("command", "same")),
    )
    assert is_refusal(colliding)
    reissue = allocate_writer_ids(
        machine="vps-a",
        boot_epoch_id="boot-1",
        streams=((SUPERVISOR_ROLE, SUPERVISOR_STREAM),),
    )
    assert is_refusal(reissue)
    supervisor = _ok(reserved_supervisor_writer(machine="vps-a", boot_epoch_id="boot-1"))
    assert supervisor_writer_is_reserved(supervisor)


def test_fingerprint_computes_composition_fp_excluding_calendar_data() -> None:
    inputs = _inputs()
    governed, shadow = _ok(compute_composition_fp(inputs))
    assert shadow is None
    body = inputs.governed_identity()
    assert "calendar_code_identities" in body
    assert "calendar_data" not in body
    assert "venue_observation_profile" not in body

    with_shadow = CompositionFingerprintInputs(
        config_fp=inputs.config_fp,
        distribution_identities=dict(inputs.distribution_identities),
        calendar_code_identities=dict(inputs.calendar_code_identities),
        shadow_candidate_identities={"labeler-a": "1.0.0"},
        os_cpu_class=inputs.os_cpu_class,
        proto_release_tag=inputs.proto_release_tag,
        tzdata_version=inputs.tzdata_version,
        registry_as_of_fp=inputs.registry_as_of_fp,
        adapter_capability_fps=inputs.adapter_capability_fps,
        extension_identities=dict(inputs.extension_identities),
    )
    governed2, shadow2 = _ok(compute_composition_fp(with_shadow))
    assert shadow2 is not None
    assert governed2 == governed  # candidates never re-identify governed evidence
    assert shadow2 != governed2


def test_seal_freezes_epoch_and_stamps_composition_fp_on_boot_attempt() -> None:
    sink = InMemoryBootAttemptSink()
    inputs = _inputs("seal")
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-seal",
            machine="vps-a",
            composition_inputs=inputs,
            writer_streams=_streams(),
            boot_attempt_sink=sink,
            preflight=PreflightFacts(),
        )
    )
    expected_fp, _ = _ok(compute_composition_fp(inputs))
    assert outcome.composition_fp == expected_fp
    assert outcome.stage_reached == "seal"
    assert sink.records[0].composition_fp == expected_fp
    assert outcome.boot_attempt.as_status()["composition_fp"] == expected_fp.value


def test_check_mode_skips_venue_gates_opens_no_sequencer_exits_on_refusal() -> None:
    sink = InMemoryBootAttemptSink()
    # chrony/credentials/stores failing must NOT refuse check mode.
    ok_outcome = _ok(
        run_check_mode(
            boot_epoch_id="check-1",
            machine="vps-a",
            composition_inputs=_inputs("check"),
            writer_streams=_streams(),
            boot_attempt_sink=sink,
            preflight=PreflightFacts(
                chrony_synced=False,
                stores_reachable=False,
                required_credential_refs=("venue-token",),
                credential_is_set={},  # unset — skipped in check mode
            ),
        )
    )
    assert ok_outcome.mode == "check"
    assert ok_outcome.sealed is True
    assert ok_outcome.opens_sequencer is False
    assert ok_outcome.exit_code is None
    assert ok_outcome.stand_down_alive is False

    refused = run_check_mode(
        boot_epoch_id="check-2",
        machine="vps-a",
        composition_inputs=_inputs("check-fail"),
        boot_attempt_sink=InMemoryBootAttemptSink(),
        preflight=PreflightFacts(disk_headroom_ok=False),
    )
    assert is_refusal(refused)
    assert refused.context["exits_nonzero"] is True
    assert refused.context["exit_code"] == DOOR_BIND_FAILURE_EXIT_CODE
    assert refused.context["opens_sequencer"] is False
    assert refused.context["mode"] == "check"


def test_check_mode_refuses_runtime_state_mutation() -> None:
    refused = run_boot_ceremony(
        boot_epoch_id="check-3",
        machine="vps-a",
        mode="check",
        composition_inputs=_inputs(),
        boot_attempt_sink=InMemoryBootAttemptSink(),
        mutate_runtime_state=True,
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "mutate_runtime_state"


def test_live_boot_with_blank_boot_blocking_config_stands_down() -> None:
    blank = _ok(config_init())
    assert blank.may_boot() is False
    inputs = CompositionFingerprintInputs(
        config_fp=blank.fingerprint,
        distribution_identities={"qmn": "0.1.0"},
    )
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-blank",
            machine="vps-a",
            config=blank,
            composition_inputs=inputs,
            boot_attempt_sink=InMemoryBootAttemptSink(),
        )
    )
    assert outcome.stand_down_alive is True
    assert outcome.failure_id == "preflight.config.boot_blocking"
    assert outcome.exit_code is None


def test_bind_supervisor_doors_default_and_custom() -> None:
    from qmf.core.refusal import Ok

    bound = _ok(bind_supervisor_doors())
    assert bound.bound is True
    assert set(bound.surfaces()) == set(BOOT_BOUND_SURFACES)

    def _ok_binder() -> Result[BoundSupervisorDoors]:
        return Ok(
            BoundSupervisorDoors(
                evidence_channel="evidence_http",
                powers_channel="powers_unix",
                preflight_status_ready=True,
                resurrect_power_ready=True,
            )
        )

    custom = _ok(bind_supervisor_doors(binder=_ok_binder))
    assert custom.evidence_channel == "evidence_http"


def test_no_cli_and_only_host_owns_boot_ceremony() -> None:
    assert HAS_OPERATOR_CLI is False
    banned_roots = (
        "loop",
        "venue",
        "order",
        "protection",
        "ledger",
        "paper",
        "reconcile",
        "seats",
        "promotion",
        "mis",
        "data",
        "time",
        "secrets",
        "config",
        "observability",
        "doors",
        "replay",
        "bench",
    )
    violations: list[str] = []
    banned_modules = (
        "qmn.host.boot_ceremony",
        "qmn.host.registry_mint",
        "qmn.host.lineage_persist",
    )
    for package in banned_roots:
        root = _QMN_SRC / package
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.ImportFrom) or not node.module:
                    continue
                module = node.module
                if any(
                    module == banned or module.startswith(f"{banned}.")
                    for banned in banned_modules
                ):
                    violations.append(f"{path.relative_to(_QMN_SRC)}: imports {module}")
    assert violations == [], f"child/door boot ceremony surface leak: {violations}"


def test_requested_restart_reason_stamped_on_boot_attempt() -> None:
    sink = InMemoryBootAttemptSink()
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-restart",
            machine="vps-a",
            composition_inputs=_inputs("restart"),
            writer_streams=_streams(),
            boot_attempt_sink=sink,
            reason="requested-restart",
        )
    )
    assert outcome.boot_attempt.reason == "requested-restart"
    assert sink.records[0].reason == "requested-restart"
