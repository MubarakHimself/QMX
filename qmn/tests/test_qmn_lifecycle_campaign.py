"""Story 28.4 — lifecycle, recovery, and no-authority operations."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TypeVar, cast

from qmf.core import Fingerprint, RefusalCategory, Result, fingerprint
from qmf.core.refusal import is_ok, is_refusal
from qmn.host import (
    LIFECYCLE_CAMPAIGN_CLASS,
    LIFECYCLE_CAMPAIGN_SURFACE,
    LIFECYCLE_INJECTIONS,
    RUNS_LIVE_BUCKET_RESTORE,
    RUNS_LIVE_VPS_FIREWALL,
    CompositionFingerprintInputs,
    DiskHeadroomBand,
    LifecycleCampaignInputs,
    evaluate_disk_headroom,
    refuse_live_bucket_restore,
    refuse_live_vps_firewall_campaign,
    run_paper_milestone_lifecycle_campaign,
)
from qmn.observability.failures_gate import DESIGNED_TYPED_FAILURE_IDS
from qmn.time import VpsClock

T = TypeVar("T")

_NS = 1_700_000_000_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "cite", "label": label}))


def _clock() -> VpsClock:
    return _ok(
        VpsClock.try_create(
            boot_epoch_id="boot-28-4",
            wall_ns=lambda: _NS,
            monotonic_ns=lambda: _NS,
        )
    )


def _composition() -> CompositionFingerprintInputs:
    return CompositionFingerprintInputs(
        config_fp=_fp("config-28-4"),
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


def _inputs(**overrides: object) -> LifecycleCampaignInputs:
    kwargs: dict[str, object] = {
        "clock": _clock(),
        "composition_inputs": _composition(),
        "disk_headroom_min": 1_048_576,
    }
    kwargs.update(overrides)
    return LifecycleCampaignInputs(**kwargs)  # type: ignore[arg-type]


def test_surface_markers_skip_live_firewall_and_bucket() -> None:
    assert LIFECYCLE_CAMPAIGN_SURFACE == "qmn.host.lifecycle_campaign"
    assert LIFECYCLE_CAMPAIGN_CLASS == "paper-milestone-lifecycle-campaign"
    assert RUNS_LIVE_VPS_FIREWALL is False
    assert RUNS_LIVE_BUCKET_RESTORE is False
    assert LIFECYCLE_INJECTIONS == (
        "crash-loop",
        "preflight",
        "callback-wedge",
        "clock",
        "disk",
        "data-freshness",
        "shutdown",
    )


def test_campaign_proves_lifecycle_injections() -> None:
    report = _ok(run_paper_milestone_lifecycle_campaign(_inputs()))
    assert report.stand_down_doors_serving is True
    assert report.only_resurrect_clears is True
    assert report.quarantine_survives_restart is True
    assert report.seat_reinstate_required is True
    assert report.clock_no_new_entry_separate_from_halt is True
    assert report.disk_headroom_degrades_before_full is True
    assert report.sigterm_flushes is True
    assert report.sigterm_mints_unknown is True
    assert report.sigterm_never_flattens is True
    assert report.protective_acts_available_or_persistent is True
    assert report.runs_live_vps_firewall is False
    assert report.runs_live_bucket_restore is False
    assert report.restore_grants_node_authority is False
    assert report.stack_required is False
    assert report.watcher_only_notifies is True
    assert tuple(report.injections) == LIFECYCLE_INJECTIONS

    def _section(name: str) -> Mapping[str, object]:
        value = report.sections[name]
        assert isinstance(value, Mapping)
        return cast("Mapping[str, object]", value)

    crash = _section("crash-loop")
    assert crash["doors_serving"] is True
    assert crash["restart_clears"] is False
    quarantine = _section("callback-wedge")
    assert quarantine["survives_restart"] is True
    assert quarantine["state_after_restart"] == "quarantined"
    clock = _section("clock")
    assert clock["no_new_entry_stand_down"] is False
    assert clock["halt_stand_down"] is True
    disk = _section("disk")
    assert disk["degrades_before_full"] is True
    shutdown = _section("shutdown")
    assert shutdown["flattened"] is False
    recovery = _section("recovery")
    assert recovery["watcher_can_stop_entries"] is False
    assert recovery["restore_auto_cutover"] is False
    assert "fingerprint" in report.as_mapping()
    assert "measured_ns" in report.as_mapping()


def test_identical_inputs_fingerprint_identically() -> None:
    first = _ok(run_paper_milestone_lifecycle_campaign(_inputs()))
    second = _ok(run_paper_milestone_lifecycle_campaign(_inputs()))
    assert first.fingerprint == second.fingerprint


def test_disk_headroom_degrades_before_full() -> None:
    ok = _ok(evaluate_disk_headroom(free_bytes=2_000, disk_headroom_min=1_000))
    assert ok.band is DiskHeadroomBand.OK
    degraded = _ok(evaluate_disk_headroom(free_bytes=500, disk_headroom_min=1_000))
    assert degraded.band is DiskHeadroomBand.NO_NEW_ENTRY
    assert degraded.entries_refused is True
    assert degraded.silent_degradation is True
    full = _ok(evaluate_disk_headroom(free_bytes=0, disk_headroom_min=1_000))
    assert full.band is DiskHeadroomBand.FULL
    assert full.protection_persistent is True


def test_refuses_live_vps_firewall_and_bucket_restore() -> None:
    firewall = _refusal(run_paper_milestone_lifecycle_campaign(_inputs(run_live_vps_firewall=True)))
    assert firewall.category is RefusalCategory.POLICY_REJECTION
    assert firewall.context["failure_id"] == "lifecycle_campaign.live_vps_firewall"
    assert refuse_live_vps_firewall_campaign().context["failure_id"] == (
        "lifecycle_campaign.live_vps_firewall"
    )
    bucket = _refusal(run_paper_milestone_lifecycle_campaign(_inputs(run_live_bucket_restore=True)))
    assert bucket.context["failure_id"] == "lifecycle_campaign.live_bucket_restore"
    assert refuse_live_bucket_restore().context["failure_id"] == (
        "lifecycle_campaign.live_bucket_restore"
    )
    clean = _refusal(run_paper_milestone_lifecycle_campaign(_inputs(run_clean_host_rehearsal=True)))
    assert clean.context["failure_id"] == "data.restore.clean_host_tonight"
    cutover = _refusal(
        run_paper_milestone_lifecycle_campaign(_inputs(request_restore_cutover=True))
    )
    assert cutover.context["failure_id"] == "data.restore.cutover"


def test_refuses_invented_disk_headroom_constant() -> None:
    refused = _refusal(
        run_paper_milestone_lifecycle_campaign(_inputs(invent_disk_headroom_min=True))
    )
    assert refused.context["failure_id"] == "lifecycle_campaign.invented_disk_headroom"


def test_designed_failure_ids_are_registered() -> None:
    for failure_id in (
        "lifecycle_campaign.incomplete_injection",
        "lifecycle_campaign.inputs",
        "lifecycle_campaign.invented_disk_headroom",
        "lifecycle_campaign.live_bucket_restore",
        "lifecycle_campaign.live_vps_firewall",
    ):
        assert failure_id in DESIGNED_TYPED_FAILURE_IDS
