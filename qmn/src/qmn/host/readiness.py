"""Paper-milestone readiness packet (Story 28.1 / FR-059 / AR-87 / FTR-07).

Assembles one fingerprinted assessment of machine prerequisites — gates,
the 71-row settings status, FAILURES.md completeness, and a compiled demo
roster with a paired paper target — without procuring a VPS or inventing
KSA/latency numbers. Soak-local human inputs are listed as blocked
acceptance, never as blockers for an unrelated epic.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    AccountRole,
    Fingerprint,
    Ok,
    Result,
    TypedRefusal,
    World,
    fingerprint,
    is_refusal,
)

from qmn.config.compiler import VALUE_STATUS_BLANK, ResolvedNodeConfig
from qmn.config.registry_catalog import (
    BLANK_EFFECT_BOOT,
    BLANK_EFFECT_LIVE,
    BLANK_EFFECT_SOAK,
    EXPECTED_ROW_COUNT,
)
from qmn.config.roster import (
    AccountBindingDecl,
    RosterRuntimeComposition,
    compose_roster_runtime,
)
from qmn.host._refuse import clean_token, invalid, policy
from qmn.observability.failures_gate import (
    FailuresCompletenessReport,
    validate_failures_completeness,
)
from qmn.paper.routing import (
    NODE_PAPER_ACCOUNT_ROLE,
    NODE_PAPER_WORLD,
    PairedDemoBinding,
)

__all__ = [
    "FTR07_UNSETTABLE_NAMES",
    "GO_LIVE_ONLY_HUMAN_INPUTS",
    "INVENTS_KSA_OR_LATENCY",
    "LIVE_SENSING_HUMAN_INPUTS",
    "MACHINE_GATES",
    "PROCURES_VPS",
    "READINESS_PACKET_CLASS",
    "READINESS_PACKET_FORMAT_VERSION",
    "READINESS_SURFACE",
    "SERIALIZES_UNRELATED_WORK",
    "SOAK_LOCAL_HUMAN_INPUTS",
    "VPS_PROCUREMENT_STARTING_POINT",
    "ArtifactCitation",
    "CompiledDemoRoster",
    "GateResult",
    "HumanInputRecord",
    "HumanInputScope",
    "ReadinessPacket",
    "SettingsStatusReport",
    "VpsProcurementEvidence",
    "assemble_paper_milestone_readiness",
    "compile_demo_roster",
    "list_readiness_human_inputs",
    "refuse_invented_ksa_or_latency_number",
    "refuse_procure_vps",
    "refuse_ratified_vps_minimum",
    "refuse_unrelated_epic_blocker",
    "settings_status_from_config",
]

READINESS_SURFACE: Final[str] = "qmn.host.readiness"
READINESS_PACKET_CLASS: Final[str] = "paper-milestone-readiness-packet"
READINESS_PACKET_FORMAT_VERSION: Final[int] = 1
PROCURES_VPS: Final[bool] = False
INVENTS_KSA_OR_LATENCY: Final[bool] = False
SERIALIZES_UNRELATED_WORK: Final[bool] = False

MACHINE_GATES: Final[tuple[str, ...]] = (
    "tier-1",
    "tier-2",
    "linux",
    "check-mode",
    "systemd",
    "conformance",
    "replay",
)

SOAK_LOCAL_HUMAN_INPUTS: Final[tuple[str, ...]] = (
    "vps_procurement",
    "ksa_matrix_values",
    "backblaze_bucket",
    "backup_key_escrow",
    "notification_account",
    "liveness_watcher_account",
)

LIVE_SENSING_HUMAN_INPUTS: Final[tuple[str, ...]] = (
    "spotware_app_approval",
    "sandbox_token",
    "live_credentials",
)

GO_LIVE_ONLY_HUMAN_INPUTS: Final[tuple[str, ...]] = (
    "live_kyc",
    "swap_free_admin_fee_schedule",
)

FTR07_UNSETTABLE_NAMES: Final[frozenset[str]] = frozenset(
    {
        "ksa_effect_matrix",
        "max_slice_latency",
        "submission_deadline",
        "local_queue_bound",
    }
)

# DEC-0261 engineering starting point — never a ratified minimum or a gate.
VPS_PROCUREMENT_STARTING_POINT: Final[Mapping[str, object]] = MappingProxyType(
    {
        "approx_ram_gib": 8,
        "approx_ssd_gib": 100,
        "approx_vcpu": 4,
        "label": "starting-point-only",
        "os": "Ubuntu 24.04",
        "ratified_minimum": False,
        "siting": "near the cTrader server",
    }
)

_COMMIT_SHA = re.compile(r"^[0-9a-f]{40}([0-9a-f]{24})?$")
_ID_INVENTED = "readiness.invented_ksa_or_latency"
_ID_VPS_MIN = "readiness.ratified_vps_minimum"
_ID_UNRELATED = "readiness.unrelated_epic_blocker"
_ID_GATE = "readiness.machine_gate"
_ID_ROSTER = "readiness.demo_roster"
_ID_PROCURE = "readiness.procure_vps"
_ID_COMMIT = "readiness.commit_lineage"
_ID_REGISTER = "readiness.failure_register"
_ID_SETTINGS = "readiness.settings_status"


class HumanInputScope(StrEnum):
    """Where a human-only input gates — never an unrelated epic."""

    SOAK_LOCAL = "soak-local"
    LIVE_SENSING = "live-sensing"
    GO_LIVE_ONLY = "go-live-only"


def refuse_invented_ksa_or_latency_number(**extra: object) -> TypedRefusal:
    """FTR-07: the packet never fills KSA matrix values or latency gates."""
    return policy(
        "invented-value",
        "KSA matrix values remain a pre-soak operator ratification and numeric "
        "hot-path/latency gates remain unset until measured baselines exist; "
        "the readiness packet invents neither (FTR-07)",
        failure_id=_ID_INVENTED,
        **extra,
    )


def refuse_ratified_vps_minimum(**extra: object) -> TypedRefusal:
    """DEC-0261: the procurement starting point is not a ratified minimum."""
    return policy(
        "vps_procurement",
        "Ubuntu 24.04 / about 4 vCPU / 8 GB / about 100 GB SSD near the "
        "cTrader server is a starting point only; no minimum is ratified "
        "until the node benchmark measures the deployed tuple (DEC-0261)",
        failure_id=_ID_VPS_MIN,
        **extra,
    )


def refuse_unrelated_epic_blocker(**extra: object) -> TypedRefusal:
    """AR-87: soak-local human inputs never block an unrelated epic."""
    return policy(
        "human_input",
        "VPS procurement, KSA matrix values, Backblaze, backup-key escrow, "
        "notification, and liveness-watcher accounts are soak-local gates; "
        "none is a blocker for an unrelated epic (AR-87)",
        failure_id=_ID_UNRELATED,
        **extra,
    )


def refuse_procure_vps(**extra: object) -> TypedRefusal:
    """Story 28.1 does not procure a VPS."""
    return policy(
        "vps_procurement",
        "the readiness packet records procurement evidence; it does not "
        "procure a VPS (DEC-0260, AR-87)",
        failure_id=_ID_PROCURE,
        **extra,
    )


@dataclass(frozen=True, slots=True)
class GateResult:
    """One recorded machine-gate outcome plus its evidence fingerprint."""

    name: str
    ok: bool
    evidence_fp1: Fingerprint

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "evidence_fp1": self.evidence_fp1.value,
                "name": self.name,
                "ok": self.ok,
            }
        )


@dataclass(frozen=True, slots=True)
class ArtifactCitation:
    """One packet artifact recorded by fp1 and branch/base commit."""

    name: str
    fingerprint: Fingerprint
    branch_commit: str
    base_commit: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "base_commit": self.base_commit,
                "branch_commit": self.branch_commit,
                "fingerprint": self.fingerprint.value,
                "name": self.name,
            }
        )


@dataclass(frozen=True, slots=True)
class SettingsStatusReport:
    """Value-status of all 71 ``value_status_required`` rows."""

    row_count: int
    config_fingerprint: Fingerprint
    blank_boot: tuple[str, ...]
    blank_live: tuple[str, ...]
    blank_soak: tuple[str, ...]
    ftr07_unfilled: tuple[str, ...]
    no_boot_live_soak_blanks: bool
    may_boot: bool
    may_bind_role_live: bool
    may_start_soak: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "blank_boot": list(self.blank_boot),
                "blank_live": list(self.blank_live),
                "blank_soak": list(self.blank_soak),
                "config_fingerprint": self.config_fingerprint.value,
                "ftr07_unfilled": list(self.ftr07_unfilled),
                "may_bind_role_live": self.may_bind_role_live,
                "may_boot": self.may_boot,
                "may_start_soak": self.may_start_soak,
                "no_boot_live_soak_blanks": self.no_boot_live_soak_blanks,
                "required_count": EXPECTED_ROW_COUNT,
                "row_count": self.row_count,
            }
        )


@dataclass(frozen=True, slots=True)
class CompiledDemoRoster:
    """Sealed demo roster plus the single paired paper target (TN-9/22)."""

    composition: RosterRuntimeComposition
    paired: PairedDemoBinding

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "bot_twin_minted": self.paired.bot_twin_minted,
                "book_twin_minted": self.paired.book_twin_minted,
                "composition_fp": self.composition.composition_fp.value,
                "demo_streams": [
                    plan.stream.token
                    for plan in self.composition.command_streams
                    if plan.connection.environment == "demo"
                ],
                "paper_role": self.paired.paper_target.role.value,
                "paper_target": dict(self.paired.as_mapping()),
                "world": self.paired.world.value,
            }
        )


@dataclass(frozen=True, slots=True)
class HumanInputRecord:
    """One human-only input with its local gate and blocked-AC flag."""

    name: str
    scope: HumanInputScope
    present: bool
    blocked_acceptance: bool
    blocks_unrelated_epics: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "blocked_acceptance": self.blocked_acceptance,
                "blocks_unrelated_epics": self.blocks_unrelated_epics,
                "name": self.name,
                "present": self.present,
                "scope": self.scope.value,
            }
        )


@dataclass(frozen=True, slots=True)
class VpsProcurementEvidence:
    """Recorded starting-point tuple — never a ratified capacity gate."""

    procured: bool
    os: str
    approx_vcpu: int
    approx_ram_gib: int
    approx_ssd_gib: int
    siting: str
    label: str
    ratified_minimum: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "approx_ram_gib": self.approx_ram_gib,
                "approx_ssd_gib": self.approx_ssd_gib,
                "approx_vcpu": self.approx_vcpu,
                "label": self.label,
                "os": self.os,
                "procured": self.procured,
                "ratified_minimum": self.ratified_minimum,
                "siting": self.siting,
            }
        )


@dataclass(frozen=True, slots=True)
class ReadinessPacket:
    """Fingerprinted paper-milestone readiness assessment (Story 28.1)."""

    format_version: int
    fingerprint: Fingerprint
    artifacts: tuple[ArtifactCitation, ...]
    machine_gates: tuple[GateResult, ...]
    settings: SettingsStatusReport
    failure_register: FailuresCompletenessReport
    demo_roster: CompiledDemoRoster
    human_inputs: tuple[HumanInputRecord, ...]
    vps_procurement: VpsProcurementEvidence
    machine_prerequisites_green: bool
    soak_start_ready: bool
    blocked_acceptance: tuple[str, ...]
    procures_vps: bool = False
    invents_ksa_or_latency: bool = False
    blocks_unrelated_epics: bool = False

    def fp1_identity(self) -> dict[str, object]:
        """Identity content for ``fp1``. Package SemVer is omitted."""
        return {
            "artifacts": [dict(item.as_mapping()) for item in self.artifacts],
            "blocked_acceptance": list(self.blocked_acceptance),
            "blocks_unrelated_epics": self.blocks_unrelated_epics,
            "class": READINESS_PACKET_CLASS,
            "demo_roster": dict(self.demo_roster.as_mapping()),
            "failure_register": {
                "designed_ids": sorted(self.failure_register.designed_ids),
                "emitted_ids": sorted(self.failure_register.emitted_ids),
                "entry_count": len(self.failure_register.entries),
                "registered_ids": sorted(self.failure_register.registered_ids),
            },
            "format_version": self.format_version,
            "human_inputs": [dict(item.as_mapping()) for item in self.human_inputs],
            "invents_ksa_or_latency": self.invents_ksa_or_latency,
            "machine_gates": [dict(item.as_mapping()) for item in self.machine_gates],
            "machine_prerequisites_green": self.machine_prerequisites_green,
            "procures_vps": self.procures_vps,
            "settings_status": dict(self.settings.as_mapping()),
            "soak_start_ready": self.soak_start_ready,
            "surface": READINESS_SURFACE,
            "vps_procurement": dict(self.vps_procurement.as_mapping()),
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = self.fingerprint.value
        return MappingProxyType(body)


def settings_status_from_config(config: object) -> Result[SettingsStatusReport]:
    """Report blank/boot/live/soak status of the 71-row resolved config."""
    if not isinstance(config, ResolvedNodeConfig):
        return invalid(
            "config",
            "settings status reads a ResolvedNodeConfig",
            given=type(config).__name__,
            failure_id=_ID_SETTINGS,
        )
    if len(config.rows) != EXPECTED_ROW_COUNT:
        return invalid(
            "rows",
            "resolved node-config carries exactly 71 value_status_required rows",
            given=len(config.rows),
            failure_id=_ID_SETTINGS,
        )
    blank_boot = tuple(
        sorted(
            name
            for name, row in config.rows.items()
            if BLANK_EFFECT_BOOT in row.blank_effect and row.value_status == VALUE_STATUS_BLANK
        )
    )
    blank_live = tuple(
        sorted(
            name
            for name, row in config.rows.items()
            if BLANK_EFFECT_LIVE in row.blank_effect and row.value_status == VALUE_STATUS_BLANK
        )
    )
    blank_soak = tuple(
        sorted(
            name
            for name, row in config.rows.items()
            if BLANK_EFFECT_SOAK in row.blank_effect and row.value_status == VALUE_STATUS_BLANK
        )
    )
    ftr07 = tuple(
        sorted(
            name
            for name in FTR07_UNSETTABLE_NAMES
            if name in config.rows and config.rows[name].value_status == VALUE_STATUS_BLANK
        )
    )
    no_blanks = not blank_boot and not blank_live and not blank_soak
    return Ok(
        SettingsStatusReport(
            row_count=len(config.rows),
            config_fingerprint=config.fingerprint,
            blank_boot=blank_boot,
            blank_live=blank_live,
            blank_soak=blank_soak,
            ftr07_unfilled=ftr07,
            no_boot_live_soak_blanks=no_blanks,
            may_boot=config.may_boot(),
            may_bind_role_live=config.may_bind_role_live(),
            may_start_soak=config.may_start_soak(),
        )
    )


def list_readiness_human_inputs(
    presence: Mapping[str, bool] | None = None,
) -> tuple[HumanInputRecord, ...]:
    """Catalog human-only inputs. Missing soak-local rows are blocked ACs."""
    present_map = dict(presence) if presence is not None else {}
    records: list[HumanInputRecord] = []
    for name in SOAK_LOCAL_HUMAN_INPUTS:
        is_present = bool(present_map.get(name, False))
        records.append(
            HumanInputRecord(
                name=name,
                scope=HumanInputScope.SOAK_LOCAL,
                present=is_present,
                blocked_acceptance=not is_present,
                blocks_unrelated_epics=False,
            )
        )
    for name in LIVE_SENSING_HUMAN_INPUTS:
        records.append(
            HumanInputRecord(
                name=name,
                scope=HumanInputScope.LIVE_SENSING,
                present=bool(present_map.get(name, False)),
                blocked_acceptance=False,
                blocks_unrelated_epics=False,
            )
        )
    for name in GO_LIVE_ONLY_HUMAN_INPUTS:
        records.append(
            HumanInputRecord(
                name=name,
                scope=HumanInputScope.GO_LIVE_ONLY,
                present=bool(present_map.get(name, False)),
                blocked_acceptance=False,
                blocks_unrelated_epics=False,
            )
        )
    return tuple(records)


def compile_demo_roster(
    *,
    demo_binding: object,
    paired: object,
    extra_bindings: object = (),
    sensing_only: object = (),
    protective_reserve_capacity: object,
) -> Result[CompiledDemoRoster]:
    """Compose a demo roster and require the paired paper target (TN-9)."""
    if not isinstance(demo_binding, AccountBindingDecl):
        return invalid(
            "demo_binding",
            "the demo roster compiles an AccountBindingDecl",
            given=type(demo_binding).__name__,
            failure_id=_ID_ROSTER,
        )
    if demo_binding.environment != "demo" or demo_binding.role is not AccountRole.DEMO:
        return policy(
            "demo_binding",
            "the paper-milestone roster compiles a role-demo environment-demo binding",
            environment=demo_binding.environment,
            role=demo_binding.role.value,
            failure_id=_ID_ROSTER,
        )
    if demo_binding.world is not World.LIVE:
        return policy(
            "demo_binding",
            "demo bindings keep world = live (DEC-0194)",
            world=demo_binding.world.value,
            failure_id=_ID_ROSTER,
        )
    if not isinstance(paired, PairedDemoBinding):
        return invalid(
            "paired",
            "the demo roster carries a PairedDemoBinding paper target",
            given=type(paired).__name__,
            failure_id=_ID_ROSTER,
        )
    if paired.paper_target.role is not NODE_PAPER_ACCOUNT_ROLE:
        return policy(
            "paper_target",
            "V1 node paper routing uses role demo only",
            given=paired.paper_target.role.value,
            failure_id=_ID_ROSTER,
        )
    if paired.world is not NODE_PAPER_WORLD:
        return policy(
            "paper_target",
            "the paired paper target keeps world = live",
            world=paired.world.value,
            failure_id=_ID_ROSTER,
        )
    if paired.bot_twin_minted or paired.book_twin_minted:
        return policy(
            "paper_target",
            "paper routing never mints a Bot or Book twin (DEC-0261)",
            failure_id=_ID_ROSTER,
        )
    if paired.paper_target.account_id != demo_binding.account_id:
        return invalid(
            "paper_target",
            "the paired paper target names the compiled demo account",
            demo_account=demo_binding.account_id,
            paper_account=paired.paper_target.account_id,
            failure_id=_ID_ROSTER,
        )
    extras = _as_binding_tuple(extra_bindings)
    if is_refusal(extras):
        return extras
    composition = compose_roster_runtime(
        account_bindings=(demo_binding, *extras.value),
        sensing_only=sensing_only,
        protective_reserve_capacity=protective_reserve_capacity,
    )
    if is_refusal(composition):
        return composition
    demo_streams = [
        plan for plan in composition.value.command_streams if plan.connection.environment == "demo"
    ]
    if not demo_streams:
        return policy(
            "demo_roster",
            "compiled demo roster must seal at least one demo command stream",
            failure_id=_ID_ROSTER,
        )
    return Ok(CompiledDemoRoster(composition=composition.value, paired=paired))


def assemble_paper_milestone_readiness(
    *,
    config: object,
    gate_results: object,
    demo_roster: object,
    branch_commit: object,
    base_commit: object,
    human_input_presence: object = None,
    vps_procured: object = False,
    vps_ratified_minimum: object = False,
    procure_vps: object = False,
    invented_ksa_value: object = None,
    invented_latency_value: object = None,
    treat_soak_local_as_unrelated_blocker: object = False,
) -> Result[ReadinessPacket]:
    """Assemble the Story 28.1 readiness packet from recorded machine evidence."""
    if procure_vps is True:
        return refuse_procure_vps()
    if invented_ksa_value is not None or invented_latency_value is not None:
        return refuse_invented_ksa_or_latency_number(
            invented_ksa_value=repr(invented_ksa_value),
            invented_latency_value=repr(invented_latency_value),
        )
    if vps_ratified_minimum is True:
        return refuse_ratified_vps_minimum()
    if treat_soak_local_as_unrelated_blocker is True:
        return refuse_unrelated_epic_blocker()
    if PROCURES_VPS or INVENTS_KSA_OR_LATENCY or SERIALIZES_UNRELATED_WORK:
        return policy(  # pragma: no cover - pinned False surface markers
            "readiness",
            "surface markers forbid procuring a VPS, inventing KSA/latency, "
            "or serializing unrelated work",
            failure_id=_ID_UNRELATED,
        )

    branch = _as_commit(branch_commit, "branch_commit")
    if is_refusal(branch):
        return branch
    base = _as_commit(base_commit, "base_commit")
    if is_refusal(base):
        return base

    settings = settings_status_from_config(config)
    if is_refusal(settings):
        return settings
    if not isinstance(config, ResolvedNodeConfig):
        return invalid("config", "settings status reads a ResolvedNodeConfig")

    numeric = _refuse_numeric_ftr07(config)
    if numeric is not None:
        return numeric

    gates = _parse_gate_results(gate_results)
    if is_refusal(gates):
        return gates

    if not isinstance(demo_roster, CompiledDemoRoster):
        return invalid(
            "demo_roster",
            "the packet carries a CompiledDemoRoster",
            given=type(demo_roster).__name__,
            failure_id=_ID_ROSTER,
        )

    presence = _parse_presence(human_input_presence)
    if is_refusal(presence):
        return presence
    humans = list_readiness_human_inputs(presence.value)

    register = validate_failures_completeness()
    if is_refusal(register):
        return policy(
            "failure_register",
            "FAILURES.md completeness is required for the readiness packet",
            failure_id=_ID_REGISTER,
            cause=str(register.context.get("reason", "")),
        )

    if not isinstance(vps_procured, bool):
        return invalid(
            "vps_procured",
            "vps_procured is a bool; this story does not procure a VPS",
            given=repr(vps_procured),
            failure_id=_ID_PROCURE,
        )

    vps = VpsProcurementEvidence(
        procured=vps_procured,
        os=str(VPS_PROCUREMENT_STARTING_POINT["os"]),
        approx_vcpu=int(cast("int", VPS_PROCUREMENT_STARTING_POINT["approx_vcpu"])),
        approx_ram_gib=int(cast("int", VPS_PROCUREMENT_STARTING_POINT["approx_ram_gib"])),
        approx_ssd_gib=int(cast("int", VPS_PROCUREMENT_STARTING_POINT["approx_ssd_gib"])),
        siting=str(VPS_PROCUREMENT_STARTING_POINT["siting"]),
        label=str(VPS_PROCUREMENT_STARTING_POINT["label"]),
        ratified_minimum=False,
    )

    register_fp = fingerprint(_register_identity(register.value))
    if is_refusal(register_fp):
        return register_fp
    roster_fp = demo_roster.composition.composition_fp
    artifacts = (
        ArtifactCitation(
            name="node-config",
            fingerprint=settings.value.config_fingerprint,
            branch_commit=branch.value,
            base_commit=base.value,
        ),
        ArtifactCitation(
            name="failure-register",
            fingerprint=register_fp.value,
            branch_commit=branch.value,
            base_commit=base.value,
        ),
        ArtifactCitation(
            name="demo-roster",
            fingerprint=roster_fp,
            branch_commit=branch.value,
            base_commit=base.value,
        ),
    )

    gates_green = all(item.ok for item in gates.value)
    machine_green = gates_green and bool(demo_roster.as_mapping()["demo_streams"])
    blocked = tuple(
        item.name
        for item in humans
        if item.scope is HumanInputScope.SOAK_LOCAL and item.blocked_acceptance
    )
    soak_ready = (
        machine_green
        and settings.value.no_boot_live_soak_blanks
        and settings.value.may_start_soak
        and not blocked
        and vps.procured
    )

    provisional = ReadinessPacket(
        format_version=READINESS_PACKET_FORMAT_VERSION,
        fingerprint=Fingerprint(value="fp1:sha256:" + ("0" * 64)),
        artifacts=artifacts,
        machine_gates=gates.value,
        settings=settings.value,
        failure_register=register.value,
        demo_roster=demo_roster,
        human_inputs=humans,
        vps_procurement=vps,
        machine_prerequisites_green=machine_green,
        soak_start_ready=soak_ready,
        blocked_acceptance=blocked,
        procures_vps=False,
        invents_ksa_or_latency=False,
        blocks_unrelated_epics=False,
    )
    packet_fp = fingerprint(provisional.fp1_identity())
    if is_refusal(packet_fp):
        return packet_fp
    return Ok(
        ReadinessPacket(
            format_version=READINESS_PACKET_FORMAT_VERSION,
            fingerprint=packet_fp.value,
            artifacts=artifacts,
            machine_gates=gates.value,
            settings=settings.value,
            failure_register=register.value,
            demo_roster=demo_roster,
            human_inputs=humans,
            vps_procurement=vps,
            machine_prerequisites_green=machine_green,
            soak_start_ready=soak_ready,
            blocked_acceptance=blocked,
            procures_vps=False,
            invents_ksa_or_latency=False,
            blocks_unrelated_epics=False,
        )
    )


def _as_commit(value: object, field: str) -> Result[str]:
    token = clean_token(value)
    if token is None or _COMMIT_SHA.match(token) is None:
        return invalid(
            field,
            "each artifact records a git SHA-1 or SHA-256 commit",
            given=repr(value),
            failure_id=_ID_COMMIT,
        )
    return Ok(token)


def _as_binding_tuple(value: object) -> Result[tuple[AccountBindingDecl, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, AccountBindingDecl):
        return Ok((value,))
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "extra_bindings",
            "extra bindings are a sequence of AccountBindingDecl",
            given=type(value).__name__,
            failure_id=_ID_ROSTER,
        )
    items: list[AccountBindingDecl] = []
    for item in cast("Sequence[object]", value):
        if not isinstance(item, AccountBindingDecl):
            return invalid(
                "extra_bindings",
                "each extra binding is an AccountBindingDecl",
                given=type(item).__name__,
                failure_id=_ID_ROSTER,
            )
        items.append(item)
    return Ok(tuple(items))


def _parse_gate_results(value: object) -> Result[tuple[GateResult, ...]]:
    if not isinstance(value, Mapping):
        return invalid(
            "gate_results",
            "machine gates are a mapping of gate name to GateResult or {ok, evidence_fp1}",
            given=type(value).__name__,
            failure_id=_ID_GATE,
        )
    body = cast("Mapping[str, object]", value)
    missing = [name for name in MACHINE_GATES if name not in body]
    if missing:
        return invalid(
            "gate_results",
            "the packet records every machine gate",
            missing=tuple(missing),
            required=list(MACHINE_GATES),
            failure_id=_ID_GATE,
        )
    extra = [name for name in body if name not in MACHINE_GATES]
    if extra:
        return invalid(
            "gate_results",
            "unknown machine gate",
            given=tuple(sorted(extra)),
            allowed=list(MACHINE_GATES),
            failure_id=_ID_GATE,
        )
    parsed: list[GateResult] = []
    for name in MACHINE_GATES:
        raw = body[name]
        if isinstance(raw, GateResult):
            if raw.name != name:
                return invalid(
                    "gate_results",
                    "gate result name must match the mapping key",
                    given=raw.name,
                    expected=name,
                    failure_id=_ID_GATE,
                )
            parsed.append(raw)
            continue
        if not isinstance(raw, Mapping):
            return invalid(
                name,
                "a gate result is GateResult or a mapping with ok and evidence_fp1",
                given=type(raw).__name__,
                failure_id=_ID_GATE,
            )
        entry = cast("Mapping[str, object]", raw)
        ok = entry.get("ok")
        if not isinstance(ok, bool):
            return invalid(
                name,
                "gate ok is a bool",
                given=repr(ok),
                failure_id=_ID_GATE,
            )
        evidence = entry.get("evidence_fp1")
        if isinstance(evidence, Fingerprint):
            fp = evidence
        else:
            parsed_fp = Fingerprint.try_create(evidence)
            if is_refusal(parsed_fp):
                return invalid(
                    name,
                    "gate evidence_fp1 is a Fingerprint",
                    given=repr(evidence),
                    failure_id=_ID_GATE,
                )
            fp = parsed_fp.value
        parsed.append(GateResult(name=name, ok=ok, evidence_fp1=fp))
    return Ok(tuple(parsed))


def _parse_presence(value: object) -> Result[Mapping[str, bool]]:
    if value is None:
        return Ok({})
    if not isinstance(value, Mapping):
        return invalid(
            "human_input_presence",
            "human-input presence is a mapping of catalog names to bool",
            given=type(value).__name__,
        )
    known = (
        set(SOAK_LOCAL_HUMAN_INPUTS)
        | set(LIVE_SENSING_HUMAN_INPUTS)
        | set(GO_LIVE_ONLY_HUMAN_INPUTS)
    )
    parsed: dict[str, bool] = {}
    for raw_name, raw_flag in cast("Mapping[object, object]", value).items():
        name = clean_token(raw_name)
        if name is None or name not in known:
            return invalid(
                "human_input_presence",
                "unknown human-input name",
                given=repr(raw_name),
                allowed=sorted(known),
            )
        if not isinstance(raw_flag, bool):
            return invalid(
                name,
                "human-input presence is a bool",
                given=repr(raw_flag),
            )
        parsed[name] = raw_flag
    return Ok(parsed)


def _refuse_numeric_ftr07(config: ResolvedNodeConfig) -> TypedRefusal | None:
    """Refuse a numeric payload on KSA matrix — values stay operator-owned."""
    row = config.rows.get("ksa_effect_matrix")
    if row is None or row.value_status == VALUE_STATUS_BLANK:
        return None
    if isinstance(row.value, (int, float)):
        return refuse_invented_ksa_or_latency_number(
            name="ksa_effect_matrix",
            given=repr(row.value),
        )
    return None


def _register_identity(report: FailuresCompletenessReport) -> dict[str, object]:
    return {
        "class": "failure-register",
        "designed_ids": sorted(report.designed_ids),
        "emitted_ids": sorted(report.emitted_ids),
        "entry_count": len(report.entries),
        "registered_ids": sorted(report.registered_ids),
        "surface": "qmn.observability.failures_gate",
    }
