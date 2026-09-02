"""Story 28.1 — paper-milestone readiness packet without serializing unrelated work."""

from __future__ import annotations

from typing import TypeVar

from qmf.core import AccountRole, Fingerprint, VenueId, World, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmf.risk.binding import BmsInstanceId
from qmn.config import (
    EXPECTED_ROW_COUNT,
    VALUE_STATUS_REQUIRED_ROWS,
    AccountBindingDecl,
    BookBindingDecl,
    PositionModelDecl,
    StateCarryChoice,
    compile_node_config,
    config_init,
    is_secret_ref_key,
)
from qmn.config.roster import STATE_CARRY_COUNTERS, ThrottleScope
from qmn.host import (
    FTR07_UNSETTABLE_NAMES,
    GO_LIVE_ONLY_HUMAN_INPUTS,
    INVENTS_KSA_OR_LATENCY,
    LIVE_SENSING_HUMAN_INPUTS,
    MACHINE_GATES,
    PROCURES_VPS,
    READINESS_PACKET_CLASS,
    READINESS_SURFACE,
    SERIALIZES_UNRELATED_WORK,
    SOAK_LOCAL_HUMAN_INPUTS,
    VPS_PROCUREMENT_STARTING_POINT,
    HumanInputScope,
    assemble_paper_milestone_readiness,
    compile_demo_roster,
    list_readiness_human_inputs,
    refuse_invented_ksa_or_latency_number,
    settings_status_from_config,
)
from qmn.observability.failures_gate import DESIGNED_TYPED_FAILURE_IDS
from qmn.paper import build_paired_demo_target

T = TypeVar("T")

_BRANCH = "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
_BASE = "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
_VENUE = VenueId(value="ic-markets")


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _refusal(result: Result[T]):
    assert is_refusal(result), result
    return result


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "readiness-test", "label": label}))


def _state_carry() -> dict[str, StateCarryChoice]:
    return dict.fromkeys(STATE_CARRY_COUNTERS, StateCarryChoice.RESET)


def _book() -> BookBindingDecl:
    return BookBindingDecl(
        binding_id="book-demo-1",
        book_definition_fp1="fp1:book:demo",
        instruments=frozenset({"EURUSD"}),
    )


def _demo_binding() -> AccountBindingDecl:
    return AccountBindingDecl(
        venue_id="ic-markets",
        account_id="acct-demo-1",
        role=AccountRole.DEMO,
        world=World.LIVE,
        environment="demo",
        credential_reference="qmx/venue-demo",
        credential_sharing="exclusive",
        bms_definition_fp1="fp1:bms:demo",
        bms_instance_id="bms-demo-1",
        book_bindings=(_book(),),
        state_carry=_state_carry(),
        throttle_scope=ThrottleScope.CONNECTION,
        position_model=PositionModelDecl.HEDGING,
        opaque_metric_id="m-demo-1",
    )


def _bms(account: str, seed: str) -> BmsInstanceId:
    return _ok(BmsInstanceId.derive(_fp(seed), account, _VENUE, World.LIVE))


def _paired():
    return _ok(
        build_paired_demo_target(
            venue_id=_VENUE,
            account_id="acct-demo-1",
            live_bms_instance_id=_bms("acct-live", "bms-live"),
            paired_bms_instance_id=_bms("acct-demo-1", "bms-demo"),
            live_binding_epoch=_fp("live-binding-demo"),
        )
    )


def _roster():
    return _ok(
        compile_demo_roster(
            demo_binding=_demo_binding(),
            paired=_paired(),
            protective_reserve_capacity=1,
        )
    )


def _layer(*, skip: frozenset[str] = frozenset(), status: str = "ratified") -> dict[str, object]:
    evidence = _fp("settings-evidence")
    body: dict[str, object] = {}
    for schema in VALUE_STATUS_REQUIRED_ROWS:
        name = schema["name"]
        if name in skip:
            continue
        value: object
        if is_secret_ref_key(name):
            value = "qmx/fixture-ref"
        elif schema["type"] in {"string", "enum"}:
            value = "fixture"
        elif schema["type"] == "declaration":
            value = {"kind": "fixture-declaration"}
        else:
            value = 1
        entry: dict[str, object] = {"value": value, "value_status": status}
        if status == "provisional-evidence":
            entry["evidence_fp1"] = evidence.value
        body[name] = entry
    return body


def _config(*, skip: frozenset[str] = frozenset(), status: str = "ratified"):
    return _ok(compile_node_config(node_defaults=_layer(skip=skip, status=status)))


def _gates(*, failed: str | None = None) -> dict[str, object]:
    body: dict[str, object] = {}
    for name in MACHINE_GATES:
        body[name] = {"ok": name != failed, "evidence_fp1": _fp(f"gate-{name}")}
    return body


def _assemble(**overrides: object):
    kwargs: dict[str, object] = {
        "config": _config(skip=FTR07_UNSETTABLE_NAMES),
        "gate_results": _gates(),
        "demo_roster": _roster(),
        "branch_commit": _BRANCH,
        "base_commit": _BASE,
    }
    kwargs.update(overrides)
    return assemble_paper_milestone_readiness(**kwargs)  # type: ignore[arg-type]


def test_surface_markers_do_not_procure_or_invent() -> None:
    assert READINESS_SURFACE == "qmn.host.readiness"
    assert READINESS_PACKET_CLASS == "paper-milestone-readiness-packet"
    assert PROCURES_VPS is False
    assert INVENTS_KSA_OR_LATENCY is False
    assert SERIALIZES_UNRELATED_WORK is False
    assert MACHINE_GATES == (
        "tier-1",
        "tier-2",
        "linux",
        "check-mode",
        "systemd",
        "conformance",
        "replay",
    )
    assert SOAK_LOCAL_HUMAN_INPUTS == (
        "vps_procurement",
        "ksa_matrix_values",
        "backblaze_bucket",
        "backup_key_escrow",
        "notification_account",
        "liveness_watcher_account",
    )
    assert VPS_PROCUREMENT_STARTING_POINT["label"] == "starting-point-only"
    assert VPS_PROCUREMENT_STARTING_POINT["ratified_minimum"] is False
    assert VPS_PROCUREMENT_STARTING_POINT["os"] == "Ubuntu 24.04"
    assert VPS_PROCUREMENT_STARTING_POINT["approx_vcpu"] == 4
    assert VPS_PROCUREMENT_STARTING_POINT["approx_ram_gib"] == 8
    assert VPS_PROCUREMENT_STARTING_POINT["approx_ssd_gib"] == 100


def test_packet_records_fingerprints_and_branch_base_commits() -> None:
    packet = _ok(_assemble())
    names = {item.name for item in packet.artifacts}
    assert names == {"node-config", "failure-register", "demo-roster"}
    for item in packet.artifacts:
        assert item.fingerprint.value.startswith("fp1:sha256:")
        assert item.branch_commit == _BRANCH
        assert item.base_commit == _BASE
    assert packet.fingerprint.value.startswith("fp1:sha256:")
    identity = packet.fp1_identity()
    assert identity["class"] == READINESS_PACKET_CLASS
    assert "version" not in identity


def test_settings_status_reports_seventy_one_rows_and_ftr07_blanks() -> None:
    config = _config(skip=FTR07_UNSETTABLE_NAMES)
    status = _ok(settings_status_from_config(config))
    assert status.row_count == EXPECTED_ROW_COUNT == 71
    assert set(status.ftr07_unfilled) == set(FTR07_UNSETTABLE_NAMES)
    assert "ksa_effect_matrix" in status.blank_soak
    assert "max_slice_latency" in status.blank_boot
    assert status.no_boot_live_soak_blanks is False
    packet = _ok(_assemble(config=config))
    assert packet.settings.row_count == 71
    assert packet.invents_ksa_or_latency is False
    for name in FTR07_UNSETTABLE_NAMES:
        assert config.rows[name].value is None
        assert config.rows[name].value_status == "blank"


def test_failure_register_completeness_is_part_of_the_packet() -> None:
    packet = _ok(_assemble())
    assert packet.failure_register.entries
    assert packet.failure_register.emitted_ids
    for failure_id in (
        "readiness.invented_ksa_or_latency",
        "readiness.ratified_vps_minimum",
        "readiness.unrelated_epic_blocker",
        "readiness.procure_vps",
        "readiness.machine_gate",
        "readiness.demo_roster",
        "readiness.failure_register",
        "readiness.settings_status",
        "readiness.commit_lineage",
    ):
        assert failure_id in DESIGNED_TYPED_FAILURE_IDS
        assert failure_id in packet.failure_register.registered_ids


def test_compiled_demo_roster_has_paired_paper_target() -> None:
    roster = _roster()
    assert roster.paired.paper_target.role is AccountRole.DEMO
    assert roster.paired.world is World.LIVE
    assert roster.paired.bot_twin_minted is False
    assert roster.paired.book_twin_minted is False
    assert roster.as_mapping()["demo_streams"]
    packet = _ok(_assemble(demo_roster=roster))
    assert packet.demo_roster.composition.sealed is True
    assert packet.machine_prerequisites_green is True


def test_soak_local_human_inputs_are_blocked_acceptance_not_unrelated() -> None:
    packet = _ok(_assemble())
    assert packet.soak_start_ready is False
    assert packet.blocks_unrelated_epics is False
    assert packet.procures_vps is False
    assert packet.vps_procurement.procured is False
    assert packet.vps_procurement.ratified_minimum is False
    assert packet.vps_procurement.label == "starting-point-only"
    assert set(packet.blocked_acceptance) == set(SOAK_LOCAL_HUMAN_INPUTS)
    by_name = {item.name: item for item in packet.human_inputs}
    for name in SOAK_LOCAL_HUMAN_INPUTS:
        row = by_name[name]
        assert row.scope is HumanInputScope.SOAK_LOCAL
        assert row.present is False
        assert row.blocked_acceptance is True
        assert row.blocks_unrelated_epics is False
    for name in LIVE_SENSING_HUMAN_INPUTS:
        row = by_name[name]
        assert row.scope is HumanInputScope.LIVE_SENSING
        assert row.blocked_acceptance is False
        assert name not in packet.blocked_acceptance
    for name in GO_LIVE_ONLY_HUMAN_INPUTS:
        row = by_name[name]
        assert row.scope is HumanInputScope.GO_LIVE_ONLY
        assert row.blocked_acceptance is False
        assert name not in packet.blocked_acceptance


def test_list_human_inputs_catalog_matches_story() -> None:
    rows = list_readiness_human_inputs()
    assert [row.name for row in rows if row.scope is HumanInputScope.SOAK_LOCAL] == list(
        SOAK_LOCAL_HUMAN_INPUTS
    )
    present = list_readiness_human_inputs({"vps_procurement": True})
    vps = next(row for row in present if row.name == "vps_procurement")
    assert vps.present is True
    assert vps.blocked_acceptance is False
    assert vps.blocks_unrelated_epics is False


def test_invented_ksa_or_latency_is_refused() -> None:
    ksa = _refusal(_assemble(invented_ksa_value={"level": 3}))
    assert ksa.category is RefusalCategory.POLICY_REJECTION
    assert ksa.context["failure_id"] == "readiness.invented_ksa_or_latency"
    latency = _refusal(_assemble(invented_latency_value=50))
    assert latency.context["failure_id"] == "readiness.invented_ksa_or_latency"
    numeric_matrix = _ok(
        compile_node_config(
            node_defaults={
                **_layer(skip=frozenset({"ksa_effect_matrix"})),
                "ksa_effect_matrix": {"value": 7, "value_status": "ratified"},
            }
        )
    )
    refused_numeric = _refusal(_assemble(config=numeric_matrix))
    assert refused_numeric.context["failure_id"] == "readiness.invented_ksa_or_latency"
    explicit = refuse_invented_ksa_or_latency_number()
    assert explicit.context["failure_id"] == "readiness.invented_ksa_or_latency"


def test_ratified_vps_minimum_and_procure_are_refused() -> None:
    ratified = _refusal(_assemble(vps_ratified_minimum=True))
    assert ratified.context["failure_id"] == "readiness.ratified_vps_minimum"
    procure = _refusal(_assemble(procure_vps=True))
    assert procure.context["failure_id"] == "readiness.procure_vps"
    unrelated = _refusal(_assemble(treat_soak_local_as_unrelated_blocker=True))
    assert unrelated.context["failure_id"] == "readiness.unrelated_epic_blocker"


def test_missing_commit_or_gate_is_refused() -> None:
    commit = _refusal(_assemble(branch_commit="not-a-sha"))
    assert commit.context["failure_id"] == "readiness.commit_lineage"
    missing_gate = dict(_gates())
    del missing_gate["replay"]
    refused_gate = _refusal(_assemble(gate_results=missing_gate))
    assert refused_gate.context["failure_id"] == "readiness.machine_gate"


def test_demo_roster_requires_demo_role_and_paired_target() -> None:
    live = AccountBindingDecl(
        venue_id="ic-markets",
        account_id="acct-live-1",
        role=AccountRole.LIVE,
        world=World.LIVE,
        environment="live",
        credential_reference="qmx/venue-live",
        credential_sharing="exclusive",
        bms_definition_fp1="fp1:bms:live",
        bms_instance_id="bms-live-1",
        book_bindings=(_book(),),
        state_carry=_state_carry(),
        throttle_scope=ThrottleScope.CONNECTION,
        position_model=PositionModelDecl.HEDGING,
        opaque_metric_id="m-live-1",
    )
    refused = _refusal(
        compile_demo_roster(
            demo_binding=live,
            paired=_paired(),
            protective_reserve_capacity=1,
        )
    )
    assert refused.context["failure_id"] == "readiness.demo_roster"


def test_green_settings_path_does_not_invent_values() -> None:
    filled = _config()
    status = _ok(settings_status_from_config(filled))
    assert status.no_boot_live_soak_blanks is True
    assert status.ftr07_unfilled == ()
    assert status.may_start_soak is True
    packet = _ok(_assemble(config=filled))
    assert packet.settings.no_boot_live_soak_blanks is True
    assert packet.invents_ksa_or_latency is False
    assert packet.soak_start_ready is False
    assert "ksa_matrix_values" in packet.blocked_acceptance
    ksa = filled.rows["ksa_effect_matrix"]
    assert not isinstance(ksa.value, (int, float))


def test_failed_gate_keeps_packet_and_clears_machine_green() -> None:
    packet = _ok(_assemble(gate_results=_gates(failed="conformance")))
    assert packet.machine_prerequisites_green is False
    assert packet.soak_start_ready is False
    conformance = next(item for item in packet.machine_gates if item.name == "conformance")
    assert conformance.ok is False


def test_blank_init_config_is_honest_about_soak_blanks() -> None:
    blank = _ok(config_init())
    status = _ok(settings_status_from_config(blank))
    assert status.row_count == 71
    assert status.may_boot is False
    assert status.may_start_soak is False
    packet = _ok(_assemble(config=blank))
    assert packet.settings.blank_soak
    assert packet.soak_start_ready is False


def test_identical_inputs_fingerprint_identically() -> None:
    first = _ok(_assemble())
    second = _ok(_assemble())
    assert first.fingerprint == second.fingerprint
    assert [item.as_mapping() for item in first.artifacts] == [
        item.as_mapping() for item in second.artifacts
    ]
