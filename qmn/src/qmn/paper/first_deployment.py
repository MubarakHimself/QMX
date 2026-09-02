"""First-deployment window: full demo shape, Book routing PAPER (Story 28.2).

The paper-milestone week runs the production VPS shape against the paired demo
account. Book routing stays PAPER for the whole window. A credentialed live
environment may be added as sensing-only (record, verify, accumulate baseline)
and never as a live binding, command stream, sequencer, or execution target.
Late Spotware approval delays only live baseline/go-live, never the demo week.
This module does not procure a VPS or open live credentials.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
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
from qmf.risk.paper import BookMode, ExecutionResolution

from qmn.config.roster import (
    AccountBindingDecl,
    RosterRuntimeComposition,
    SensingOnlyDecl,
    compose_roster_runtime,
)
from qmn.paper._refuse import clean_token, invalid, policy
from qmn.paper.routing import (
    NODE_PAPER_ACCOUNT_ROLE,
    NODE_PAPER_WORLD,
    PairedDemoBinding,
    resolve_book_execution_target,
)

__all__ = [
    "DECLARED_FAULT_INJECTION_POINTS",
    "DEMO_SHAPE_DOORS",
    "DEMO_SHAPE_MACHINERY",
    "DEMO_SHAPE_NODE_TIMERS",
    "DEMO_SHAPE_PRINCIPALS",
    "DEMO_SHAPE_TREES",
    "DEMO_SHAPE_UNITS",
    "FAULT_INJECTION_MODE",
    "FIRST_DEPLOYMENT_BOOK_ROUTING",
    "FIRST_DEPLOYMENT_SURFACE",
    "FIRST_DEPLOYMENT_WINDOW_CLASS",
    "FIRST_DEPLOYMENT_WINDOW_FORMAT_VERSION",
    "LATE_LIVE_APPROVAL_DELAYS",
    "LIVE_SENSING_ALLOWED",
    "LIVE_SENSING_FORBIDDEN",
    "OPENS_LIVE_CREDENTIALS",
    "PRE_UNATTENDED_PROOFS",
    "PROCURES_VPS",
    "FirstDeploymentWindow",
    "LiveSensingAdmission",
    "PreUnattendedProof",
    "admit_live_sensing",
    "begin_unattended_interval",
    "compose_first_deployment_window",
    "record_pre_unattended_proofs",
    "refuse_continuous_supervision",
    "refuse_first_deployment_live_authority",
    "refuse_late_approval_blocks_demo",
    "refuse_open_live_credentials",
    "refuse_procure_vps",
    "require_first_deployment_book_routing",
    "resolve_first_deployment_execution_target",
]

FIRST_DEPLOYMENT_SURFACE: Final[str] = "qmn.paper.first_deployment"
FIRST_DEPLOYMENT_WINDOW_CLASS: Final[str] = "first-deployment-window"
FIRST_DEPLOYMENT_WINDOW_FORMAT_VERSION: Final[int] = 1
FIRST_DEPLOYMENT_BOOK_ROUTING: Final[BookMode] = BookMode.PAPER
PROCURES_VPS: Final[bool] = False
OPENS_LIVE_CREDENTIALS: Final[bool] = False
FAULT_INJECTION_MODE: Final[str] = "declared-boundary-only"

DEMO_SHAPE_UNITS: Final[tuple[str, ...]] = (
    "qmn.service",
    "qmn-news-calendar.service",
    "qmn-news-calendar.timer",
    "qmn-backup.service",
    "qmn-backup.timer",
    "qmn-restore-sample.service",
    "qmn-restore-sample.timer",
    "qmn-restore-full.service",
    "qmn-restore-full.timer",
    "qmx-observability.service",
)
DEMO_SHAPE_NODE_TIMERS: Final[tuple[str, ...]] = (
    "qmn-news-calendar.timer",
    "qmn-backup.timer",
    "qmn-restore-sample.timer",
    "qmn-restore-full.timer",
)
DEMO_SHAPE_TREES: Final[tuple[str, ...]] = (
    "rooms",
    "evidence",
    "hub-inbox",
    "hub-published",
)
DEMO_SHAPE_DOORS: Final[tuple[str, ...]] = ("powers", "evidence")
DEMO_SHAPE_PRINCIPALS: Final[tuple[str, ...]] = ("qmx", "qmxobs", "ops")
DEMO_SHAPE_MACHINERY: Final[tuple[str, ...]] = (
    "qmn.service",
    "four-node-timers",
    "qmx-observability.service",
    "rooms",
    "evidence",
    "hub",
    "powers-door",
    "evidence-door",
    "chrony",
    "backups",
    "news-intake",
    "ksa",
    "protection",
    "seats",
    "paired-demo-account",
    "paper-virtual-ledger",
)
LIVE_SENSING_ALLOWED: Final[tuple[str, ...]] = (
    "sensing",
    "recording",
    "capability-verification",
    "baseline-accumulation",
)
LIVE_SENSING_FORBIDDEN: Final[tuple[str, ...]] = (
    "live-binding",
    "command-stream",
    "sequencer",
    "execution-target",
)
LATE_LIVE_APPROVAL_DELAYS: Final[tuple[str, ...]] = ("live-baseline", "go-live")
PRE_UNATTENDED_PROOFS: Final[tuple[str, ...]] = (
    "synthetic-alert",
    "missing-heartbeat-notification",
)
DECLARED_FAULT_INJECTION_POINTS: Final[frozenset[str]] = frozenset({"boundary", "drill"})

_ID_ROUTING = "first_deployment.book_routing"
_ID_LIVE_BINDING = "first_deployment.live_binding"
_ID_LIVE_STREAM = "first_deployment.live_command_stream"
_ID_LIVE_SEQUENCER = "first_deployment.live_sequencer"
_ID_LIVE_TARGET = "first_deployment.live_execution_target"
_ID_PROCURE = "first_deployment.procure_vps"
_ID_OPEN_CREDS = "first_deployment.open_live_credentials"
_ID_SUPERVISION = "first_deployment.continuous_supervision"
_ID_PRE_UNATTENDED = "first_deployment.pre_unattended"
_ID_LATE_DEMO = "first_deployment.late_approval_blocks_demo"
_ID_ROSTER = "first_deployment.demo_roster"

_LIVE_AUTHORITY_IDS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "live-binding": _ID_LIVE_BINDING,
        "command-stream": _ID_LIVE_STREAM,
        "sequencer": _ID_LIVE_SEQUENCER,
        "execution-target": _ID_LIVE_TARGET,
    }
)


def refuse_procure_vps(**extra: object) -> TypedRefusal:
    """Story 28.2 does not procure a VPS."""
    return policy(
        "vps_procurement",
        "the first-deployment demo shape records the production inventory; "
        "it does not procure a VPS (DEC-0260, AR-87)",
        failure_id=_ID_PROCURE,
        **extra,
    )


def refuse_open_live_credentials(**extra: object) -> TypedRefusal:
    """Story 28.2 does not open live credentials."""
    return policy(
        "live_credentials",
        "live sensing opens only when Spotware credentials already exist; "
        "this story does not open live credentials",
        failure_id=_ID_OPEN_CREDS,
        **extra,
    )


def refuse_continuous_supervision(**extra: object) -> TypedRefusal:
    """Fault injection is only at declared boundary/drill points."""
    return policy(
        "fault_injection",
        "fault-injection drills occur only at declared boundary/drill points, "
        "not as continuous human supervision (NFR-13)",
        failure_id=_ID_SUPERVISION,
        **extra,
    )


def refuse_late_approval_blocks_demo(**extra: object) -> TypedRefusal:
    """Late live approval never blocks the demo week."""
    return policy(
        "late_live_approval",
        "a late Spotware approval delays only live baseline/go-live, never "
        "the demo week (DEC-0260/0261)",
        failure_id=_ID_LATE_DEMO,
        **extra,
    )


def refuse_first_deployment_live_authority(kind: object, **extra: object) -> TypedRefusal:
    """Refuse live binding, command stream, sequencer, or execution target."""
    token = clean_token(kind)
    failure_id = _LIVE_AUTHORITY_IDS.get(token or "", _ID_LIVE_BINDING)
    return policy(
        "live_sensing",
        "during the first-deployment window a live environment may sense, "
        "record, verify capabilities, and accumulate baseline only — no live "
        "binding, command stream, sequencer, or execution target (DEC-0260)",
        given=token,
        forbidden=list(LIVE_SENSING_FORBIDDEN),
        failure_id=failure_id,
        **extra,
    )


def require_first_deployment_book_routing(book_mode: object) -> Result[BookMode]:
    """Pin Book routing to PAPER for the whole first-deployment window."""
    mode = _as_book_mode(book_mode)
    if is_refusal(mode):
        return mode
    if mode.value is not FIRST_DEPLOYMENT_BOOK_ROUTING:
        return policy(
            "book_mode",
            "Book routing is PAPER for the whole first-deployment window (TN-9/16; DEC-0194)",
            given=mode.value.value,
            required=FIRST_DEPLOYMENT_BOOK_ROUTING.value,
            failure_id=_ID_ROUTING,
        )
    return mode


def admit_live_sensing(
    *,
    credentials_present: object,
    live_sensing: object = None,
    request_live_binding: object = False,
    request_command_stream: object = False,
    request_sequencer: object = False,
    request_execution_target: object = False,
    treat_late_live_as_demo_blocker: object = False,
) -> Result[LiveSensingAdmission]:
    """Admit sensing-only live when credentials exist; never a live money path."""
    if treat_late_live_as_demo_blocker is True:
        return refuse_late_approval_blocks_demo()
    if not isinstance(credentials_present, bool):
        return invalid(
            "credentials_present",
            "live-credential presence is a bool; this story does not open them",
            given=repr(credentials_present),
            failure_id=_ID_OPEN_CREDS,
        )
    if request_live_binding is True:
        return refuse_first_deployment_live_authority("live-binding")
    if request_command_stream is True:
        return refuse_first_deployment_live_authority("command-stream")
    if request_sequencer is True:
        return refuse_first_deployment_live_authority("sequencer")
    if request_execution_target is True:
        return refuse_first_deployment_live_authority("execution-target")
    if credentials_present is False:
        if live_sensing is not None:
            return refuse_open_live_credentials(
                given="sensing-decl-without-credentials",
            )
        return Ok(
            LiveSensingAdmission(
                credentials_present=False,
                sensing_open=False,
                may_record=False,
                may_verify_capabilities=False,
                may_accumulate_baseline=False,
                delays=LATE_LIVE_APPROVAL_DELAYS,
                demo_week_blocked=False,
            )
        )
    decl = _as_sensing_decl(live_sensing)
    if is_refusal(decl):
        return decl
    if decl.value.environment != "live":
        return policy(
            "live_sensing",
            "when credentials exist the live environment is added as sensing-only",
            environment=decl.value.environment,
            failure_id=_ID_OPEN_CREDS,
        )
    return Ok(
        LiveSensingAdmission(
            credentials_present=True,
            sensing_open=True,
            may_record=True,
            may_verify_capabilities=True,
            may_accumulate_baseline=True,
            sensing=decl.value,
            delays=(),
            demo_week_blocked=False,
        )
    )


def record_pre_unattended_proofs(
    *,
    synthetic_alert_delivered: object,
    missing_heartbeat_delivered: object,
    fault_injection_mode: object = FAULT_INJECTION_MODE,
    continuous_human_supervision: object = False,
    fault_injection_point: object = None,
) -> Result[PreUnattendedProof]:
    """Require synthetic alert and missing-heartbeat before the unattended week."""
    if continuous_human_supervision is True:
        return refuse_continuous_supervision()
    mode = clean_token(fault_injection_mode)
    if mode != FAULT_INJECTION_MODE:
        return refuse_continuous_supervision(given=repr(fault_injection_mode))
    if fault_injection_point is not None:
        point = clean_token(fault_injection_point)
        if point not in DECLARED_FAULT_INJECTION_POINTS:
            return refuse_continuous_supervision(given=repr(fault_injection_point))
    if not isinstance(synthetic_alert_delivered, bool):
        return invalid(
            "synthetic_alert_delivered",
            "synthetic-alert delivery is a bool",
            given=repr(synthetic_alert_delivered),
            failure_id=_ID_PRE_UNATTENDED,
        )
    if not isinstance(missing_heartbeat_delivered, bool):
        return invalid(
            "missing_heartbeat_delivered",
            "missing-heartbeat delivery is a bool",
            given=repr(missing_heartbeat_delivered),
            failure_id=_ID_PRE_UNATTENDED,
        )
    ready = synthetic_alert_delivered is True and missing_heartbeat_delivered is True
    return Ok(
        PreUnattendedProof(
            synthetic_alert_delivered=synthetic_alert_delivered,
            missing_heartbeat_delivered=missing_heartbeat_delivered,
            fault_injection_mode=FAULT_INJECTION_MODE,
            continuous_human_supervision=False,
            unattended_interval_may_begin=ready,
        )
    )


def begin_unattended_interval(proof: object) -> Result[PreUnattendedProof]:
    """Refuse to start the unattended interval without both end-to-end proofs."""
    if not isinstance(proof, PreUnattendedProof):
        return invalid(
            "pre_unattended",
            "unattended start reads a PreUnattendedProof",
            given=type(proof).__name__,
            failure_id=_ID_PRE_UNATTENDED,
        )
    if proof.continuous_human_supervision is True:
        return refuse_continuous_supervision()
    if (
        proof.synthetic_alert_delivered is not True
        or proof.missing_heartbeat_delivered is not True
        or proof.unattended_interval_may_begin is not True
    ):
        return policy(
            "pre_unattended",
            "a synthetic alert and a missing-heartbeat notification must already "
            "be delivered end to end before the node is left unattended (NFR-13)",
            synthetic_alert_delivered=proof.synthetic_alert_delivered,
            missing_heartbeat_delivered=proof.missing_heartbeat_delivered,
            failure_id=_ID_PRE_UNATTENDED,
        )
    return Ok(proof)


def compose_first_deployment_window(
    *,
    demo_binding: object,
    paired: object,
    book_mode: object = FIRST_DEPLOYMENT_BOOK_ROUTING,
    protective_reserve_capacity: object,
    live_credentials_present: object = False,
    live_sensing: object = None,
    live_account_binding: object = None,
    request_live_binding: object = False,
    request_command_stream: object = False,
    request_sequencer: object = False,
    request_execution_target: object = False,
    synthetic_alert_delivered: object = False,
    missing_heartbeat_delivered: object = False,
    fault_injection_mode: object = FAULT_INJECTION_MODE,
    continuous_human_supervision: object = False,
    claim_unattended_ready: object = False,
    procure_vps: object = False,
    open_live_credentials: object = False,
    treat_late_live_as_demo_blocker: object = False,
    vps_procured: object = False,
) -> Result[FirstDeploymentWindow]:
    """Seal the first-deployment demo shape with PAPER routing (TN-9/16)."""
    if procure_vps is True:
        return refuse_procure_vps()
    if open_live_credentials is True:
        return refuse_open_live_credentials()
    if PROCURES_VPS or OPENS_LIVE_CREDENTIALS:
        return policy(  # pragma: no cover - pinned False surface markers
            "first_deployment",
            "surface markers forbid procuring a VPS or opening live credentials",
            failure_id=_ID_PROCURE,
        )

    routing = require_first_deployment_book_routing(book_mode)
    if is_refusal(routing):
        return routing

    if live_account_binding is not None:
        return refuse_first_deployment_live_authority(
            "live-binding",
            offered=type(live_account_binding).__name__,
        )

    demo = _as_demo_binding(demo_binding)
    if is_refusal(demo):
        return demo
    paper = _as_paired(paired, demo.value)
    if is_refusal(paper):
        return paper

    sensing = admit_live_sensing(
        credentials_present=live_credentials_present,
        live_sensing=live_sensing,
        request_live_binding=request_live_binding,
        request_command_stream=request_command_stream,
        request_sequencer=request_sequencer,
        request_execution_target=request_execution_target,
        treat_late_live_as_demo_blocker=treat_late_live_as_demo_blocker,
    )
    if is_refusal(sensing):
        return sensing

    proofs = record_pre_unattended_proofs(
        synthetic_alert_delivered=synthetic_alert_delivered,
        missing_heartbeat_delivered=missing_heartbeat_delivered,
        fault_injection_mode=fault_injection_mode,
        continuous_human_supervision=continuous_human_supervision,
    )
    if is_refusal(proofs):
        return proofs
    if claim_unattended_ready is True:
        started = begin_unattended_interval(proofs.value)
        if is_refusal(started):
            return started

    sensing_only: tuple[SensingOnlyDecl, ...] = ()
    if sensing.value.sensing is not None:
        sensing_only = (sensing.value.sensing,)

    composition = compose_roster_runtime(
        account_bindings=(demo.value,),
        sensing_only=sensing_only,
        protective_reserve_capacity=protective_reserve_capacity,
    )
    if is_refusal(composition):
        return policy(
            "demo_roster",
            "the first-deployment window compiles a demo roster with a paired "
            "paper target and optional sensing-only live environment",
            failure_id=_ID_ROSTER,
            cause=str(composition.context.get("reason", "")),
        )
    if not _has_demo_stream(composition.value):
        return policy(
            "demo_roster",
            "compiled demo roster must seal at least one demo command stream",
            failure_id=_ID_ROSTER,
        )
    if sensing.value.sensing_open:
        live_authority = _live_authority_on_sensing(composition.value)
        if live_authority is not None:
            return refuse_first_deployment_live_authority(live_authority)

    blocked_infra: tuple[str, ...] = ()
    if vps_procured is not True:
        blocked_infra = ("vps_procurement",)

    provisional = FirstDeploymentWindow(
        format_version=FIRST_DEPLOYMENT_WINDOW_FORMAT_VERSION,
        fingerprint=Fingerprint(value="fp1:sha256:" + ("0" * 64)),
        book_routing=routing.value,
        composition=composition.value,
        paired=paper.value,
        live_sensing=sensing.value,
        pre_unattended=proofs.value,
        paper_virtual_ledger=True,
        procures_vps=False,
        opens_live_credentials=False,
        demo_week_blocked_by_late_live=False,
        blocked_infra=blocked_infra,
    )
    packet_fp = fingerprint(provisional.fp1_identity())
    if is_refusal(packet_fp):
        return packet_fp
    return Ok(
        FirstDeploymentWindow(
            format_version=FIRST_DEPLOYMENT_WINDOW_FORMAT_VERSION,
            fingerprint=packet_fp.value,
            book_routing=routing.value,
            composition=composition.value,
            paired=paper.value,
            live_sensing=sensing.value,
            pre_unattended=proofs.value,
            paper_virtual_ledger=True,
            procures_vps=False,
            opens_live_credentials=False,
            demo_week_blocked_by_late_live=False,
            blocked_infra=blocked_infra,
        )
    )


def resolve_first_deployment_execution_target(
    *,
    book_mode: object,
    seat_state: object,
    active_controls: object,
    live_target: object,
    paper_target: object,
    blocked_act: object = "entry",
) -> Result[ExecutionResolution]:
    """Resolve one intent under first-deployment PAPER routing."""
    routing = require_first_deployment_book_routing(book_mode)
    if is_refusal(routing):
        return routing
    return resolve_book_execution_target(
        book_mode=routing.value,
        seat_state=seat_state,
        active_controls=active_controls,
        live_target=live_target,
        paper_target=paper_target,
        blocked_act=blocked_act,
    )


@dataclass(frozen=True, slots=True)
class LiveSensingAdmission:
    """Live environment admitted for sensing/recording only, or deferred."""

    credentials_present: bool
    sensing_open: bool
    may_record: bool
    may_verify_capabilities: bool
    may_accumulate_baseline: bool
    sensing: SensingOnlyDecl | None = None
    has_live_binding: bool = False
    has_command_stream: bool = False
    opens_sequencer: bool = False
    resolves_execution_target: bool = False
    delays: tuple[str, ...] = ()
    demo_week_blocked: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "credentials_present": self.credentials_present,
                "delays": list(self.delays),
                "demo_week_blocked": self.demo_week_blocked,
                "has_command_stream": self.has_command_stream,
                "has_live_binding": self.has_live_binding,
                "may_accumulate_baseline": self.may_accumulate_baseline,
                "may_record": self.may_record,
                "may_verify_capabilities": self.may_verify_capabilities,
                "opens_sequencer": self.opens_sequencer,
                "resolves_execution_target": self.resolves_execution_target,
                "sensing_open": self.sensing_open,
            }
        )


@dataclass(frozen=True, slots=True)
class PreUnattendedProof:
    """End-to-end notify proofs required before the unattended interval."""

    synthetic_alert_delivered: bool
    missing_heartbeat_delivered: bool
    fault_injection_mode: str
    continuous_human_supervision: bool
    unattended_interval_may_begin: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "continuous_human_supervision": self.continuous_human_supervision,
                "fault_injection_mode": self.fault_injection_mode,
                "missing_heartbeat_delivered": self.missing_heartbeat_delivered,
                "synthetic_alert_delivered": self.synthetic_alert_delivered,
                "unattended_interval_may_begin": self.unattended_interval_may_begin,
            }
        )


@dataclass(frozen=True, slots=True)
class FirstDeploymentWindow:
    """Fingerprinted first-deployment demo shape (Story 28.2)."""

    format_version: int
    fingerprint: Fingerprint
    book_routing: BookMode
    composition: RosterRuntimeComposition
    paired: PairedDemoBinding
    live_sensing: LiveSensingAdmission
    pre_unattended: PreUnattendedProof
    paper_virtual_ledger: bool
    procures_vps: bool
    opens_live_credentials: bool
    demo_week_blocked_by_late_live: bool
    blocked_infra: tuple[str, ...]

    def fp1_identity(self) -> dict[str, object]:
        """Identity content for ``fp1``. Package SemVer is omitted."""
        return {
            "blocked_infra": list(self.blocked_infra),
            "book_routing": self.book_routing.value,
            "class": FIRST_DEPLOYMENT_WINDOW_CLASS,
            "composition_fp": self.composition.composition_fp.value,
            "demo_week_blocked_by_late_live": self.demo_week_blocked_by_late_live,
            "format_version": self.format_version,
            "live_sensing": dict(self.live_sensing.as_mapping()),
            "opens_live_credentials": self.opens_live_credentials,
            "paper_role": self.paired.paper_target.role.value,
            "paper_virtual_ledger": self.paper_virtual_ledger,
            "pre_unattended": dict(self.pre_unattended.as_mapping()),
            "procures_vps": self.procures_vps,
            "surface": FIRST_DEPLOYMENT_SURFACE,
            "world": self.paired.world.value,
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = self.fingerprint.value
        body["machinery"] = list(DEMO_SHAPE_MACHINERY)
        body["units"] = list(DEMO_SHAPE_UNITS)
        return MappingProxyType(body)


def _as_book_mode(value: object) -> Result[BookMode]:
    if isinstance(value, BookMode):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "book_mode",
            "first-deployment Book routing reads LIVE|PAPER",
            given=repr(value),
            failure_id=_ID_ROUTING,
        )
    try:
        return Ok(BookMode(token))
    except ValueError:
        return invalid(
            "book_mode",
            "first-deployment Book routing reads LIVE|PAPER",
            given=token,
            failure_id=_ID_ROUTING,
        )


def _as_demo_binding(value: object) -> Result[AccountBindingDecl]:
    if not isinstance(value, AccountBindingDecl):
        return invalid(
            "demo_binding",
            "the first-deployment window compiles an AccountBindingDecl",
            given=type(value).__name__,
            failure_id=_ID_ROSTER,
        )
    if value.environment != "demo" or value.role is not AccountRole.DEMO:
        return policy(
            "demo_binding",
            "the first-deployment roster compiles a role-demo environment-demo binding",
            environment=value.environment,
            role=value.role.value,
            failure_id=_ID_ROSTER,
        )
    if value.world is not World.LIVE:
        return policy(
            "demo_binding",
            "demo bindings keep world = live (DEC-0194)",
            world=value.world.value,
            failure_id=_ID_ROSTER,
        )
    return Ok(value)


def _as_paired(value: object, demo: AccountBindingDecl) -> Result[PairedDemoBinding]:
    if not isinstance(value, PairedDemoBinding):
        return invalid(
            "paired",
            "the first-deployment window carries a PairedDemoBinding paper target",
            given=type(value).__name__,
            failure_id=_ID_ROSTER,
        )
    if value.paper_target.role is not NODE_PAPER_ACCOUNT_ROLE:
        return policy(
            "paper_target",
            "V1 node paper routing uses role demo only",
            given=value.paper_target.role.value,
            failure_id=_ID_ROSTER,
        )
    if value.world is not NODE_PAPER_WORLD:
        return policy(
            "paper_target",
            "the paired paper target keeps world = live",
            world=value.world.value,
            failure_id=_ID_ROSTER,
        )
    if value.bot_twin_minted or value.book_twin_minted:
        return policy(
            "paper_target",
            "paper routing never mints a Bot or Book twin (DEC-0261)",
            failure_id=_ID_ROSTER,
        )
    if value.paper_target.account_id != demo.account_id:
        return invalid(
            "paper_target",
            "the paired paper target names the compiled demo account",
            demo_account=demo.account_id,
            paper_account=value.paper_target.account_id,
            failure_id=_ID_ROSTER,
        )
    return Ok(value)


def _as_sensing_decl(value: object) -> Result[SensingOnlyDecl]:
    if isinstance(value, SensingOnlyDecl):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "live_sensing",
            "live sensing is a SensingOnlyDecl when credentials exist",
            given=type(value).__name__,
            failure_id=_ID_OPEN_CREDS,
        )
    body = cast("Mapping[str, object]", value)
    venue_id = clean_token(body.get("venue_id"))
    environment = clean_token(body.get("environment"))
    account_id = clean_token(body.get("account_id"))
    credential_reference = clean_token(body.get("credential_reference"))
    opaque = clean_token(body.get("opaque_metric_id"))
    if (
        venue_id is None
        or environment is None
        or account_id is None
        or credential_reference is None
        or opaque is None
    ):
        return invalid(
            "live_sensing",
            "sensing-only requires venue_id, environment, account_id, "
            "credential_reference, and opaque_metric_id",
            failure_id=_ID_OPEN_CREDS,
        )
    return Ok(
        SensingOnlyDecl(
            venue_id=venue_id,
            environment=environment,
            account_id=account_id,
            credential_reference=credential_reference,
            opaque_metric_id=opaque,
            world=World.LIVE,
        )
    )


def _has_demo_stream(composition: RosterRuntimeComposition) -> bool:
    return any(plan.connection.environment == "demo" for plan in composition.command_streams)


def _live_authority_on_sensing(composition: RosterRuntimeComposition) -> str | None:
    for plan in composition.sensing_plans:
        if plan.has_book_binding or plan.has_bms_instance:
            return "live-binding"
        if plan.has_command_stream:
            return "command-stream"
        if plan.opens_sequencer:
            return "sequencer"
        if plan.resolves_execution_target or plan.admits_live_intent:
            return "execution-target"
    live_streams = [
        plan for plan in composition.command_streams if plan.connection.environment == "live"
    ]
    if live_streams:
        return "command-stream"
    return None
