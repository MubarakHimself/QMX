"""TN-23 live-readiness verdict packet and checklist fold (Story 28.8).

Folds journaled soak-acceptance items into one fingerprinted machinery
verdict. Does not run an unattended paper week, does not procure a VPS,
does not invent KSA or latency numbers, and never opens a live binding.
Profit, loss, win rate, and paper performance never enter the packet
(AD-32 / DEC-0208 / FR-076). Promotion and activation stay separate powers;
this epic grants no live-money authority (DEC-0261).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Fingerprint, Ok, Result, TypedRefusal, fingerprint, is_refusal
from qmf.risk.performance import PublishAct, check_publish_never_act

from qmn.host._refuse import clean_token, invalid, policy
from qmn.host.qa_debt_matrix import QaDebtClosureMatrix, run_paper_milestone_qa_debt_gate
from qmn.ledger import refuse_paper_pnl_to_treasury
from qmn.paper.first_deployment import (
    DECLARED_FAULT_INJECTION_POINTS,
    DEMO_SHAPE_MACHINERY,
)

__all__ = [
    "ACTIVATION_WAITS_FOR_DAY_BOUNDARY",
    "BLOCKED_INFRA_ITEMS",
    "BLOCKED_INFRA_SCOPES",
    "FORBIDDEN_VERDICT_KEYS",
    "LIVE_INSTRUMENT_REQUIREMENTS",
    "OPENS_LIVE_BINDING",
    "PAPER_MILESTONE_IMMUTABLE",
    "PRE_WEEK_STORIES",
    "PROFIT_ENTERS_VERDICT",
    "PROMOTION_AND_ACTIVATION_ARE_SEPARATE",
    "REQUIRED_CHECKLIST_ITEM_IDS",
    "RUNS_UNATTENDED_PAPER_WEEK",
    "TN23_CHECKLIST_ITEMS",
    "VERDICT_PACKET_CLASS",
    "VERDICT_PACKET_FORMAT_VERSION",
    "VERDICT_SURFACE",
    "WHOLE_SYSTEM_SURFACES",
    "ChecklistItemFold",
    "ChecklistItemStatus",
    "LiveInstrumentReadiness",
    "LiveReadinessVerdict",
    "OperatorProceeding",
    "WeekClockDecision",
    "WeekInterruptionClass",
    "apply_week_interruption",
    "evaluate_live_instrument_readiness",
    "fold_tn23_checklist",
    "publish_live_readiness_verdict",
    "record_operator_proceed",
    "refuse_invented_ksa_or_latency_number",
    "refuse_live_binding",
    "refuse_merged_promotion_activation",
    "refuse_procure_vps",
    "refuse_profit_in_verdict",
    "refuse_same_day_activation",
    "refuse_unattended_paper_week",
    "run_unattended_paper_week",
]

VERDICT_SURFACE: Final[str] = "qmn.host.verdict"
VERDICT_PACKET_CLASS: Final[str] = "tn23-live-readiness-verdict"
VERDICT_PACKET_FORMAT_VERSION: Final[int] = 1
RUNS_UNATTENDED_PAPER_WEEK: Final[bool] = False
OPENS_LIVE_BINDING: Final[bool] = False
PROFIT_ENTERS_VERDICT: Final[bool] = False
PROMOTION_AND_ACTIVATION_ARE_SEPARATE: Final[bool] = True
ACTIVATION_WAITS_FOR_DAY_BOUNDARY: Final[bool] = True
PAPER_MILESTONE_IMMUTABLE: Final[bool] = True

PRE_WEEK_STORIES: Final[tuple[str, ...]] = (
    "28.1",
    "28.2",
    "28.3",
    "28.4",
    "28.5",
    "28.6",
    "28.7",
)

BLOCKED_INFRA_SCOPES: Final[tuple[str, ...]] = (
    "vps_procurement",
    "ksa_matrix_values",
    "paper_week",
)

LIVE_INSTRUMENT_REQUIREMENTS: Final[tuple[str, ...]] = (
    "verified_capability_profile",
    "live_conditioned_sqs_baseline",
    "live_path_rung_baseline",
    "kyc",
    "written_fee_schedule",
    "current_config",
    "silent_battery_pass",
)

WHOLE_SYSTEM_SURFACES: Final[tuple[str, ...]] = DEMO_SHAPE_MACHINERY

FORBIDDEN_VERDICT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "expectancy",
        "loss",
        "p_and_l",
        "paper_performance",
        "paper_pnl",
        "pnl",
        "profit",
        "roi",
        "sharpe",
        "win_rate",
        "winrate",
    }
)

TN23_CHECKLIST_ITEMS: Final[tuple[str, ...]] = (
    "first-connection-checks",
    "unknown-mid-order-stream-block",
    "protective-stop-capability",
    "no-scale-in",
    "reconnect-gap-fills-before-healthy",
    "reconciliation-four-verdicts",
    "ksa-escalation",
    "ad37-compose-pair",
    "kill-line-paper-flatten",
    "news-deadzone-exit-preservation",
    "amend-protection-under-unknown",
    "sqs-and-live-baselines",
    "bench-fold",
    "residual-operator-review",
    "restart-standing-intent-paper",
    "crash-loop-stand-down-resurrect",
    "quarantine-seat-reinstate",
    "shutdown-contract",
    "backup-restore-host-loss",
    "systemd-load-credential-encrypted",
    "clock-band-no-new-entry",
    "powers-peer-and-ops-principal",
    "value-status-countersign",
    "next-day-activation",
    "liveness-heartbeat",
    "conformance-and-golden-scenarios",
    "replay-soak-day",
    "observability-stack",
    "benchmark-and-storage",
    "unattended-week-continuous",
)

BLOCKED_INFRA_ITEMS: Final[Mapping[str, str]] = MappingProxyType(
    {
        "backup-restore-host-loss": "vps_procurement",
        "ksa-escalation": "ksa_matrix_values",
        "observability-stack": "paper_week",
        "replay-soak-day": "paper_week",
        "sqs-and-live-baselines": "paper_week",
        "systemd-load-credential-encrypted": "vps_procurement",
        "unattended-week-continuous": "paper_week",
    }
)

REQUIRED_CHECKLIST_ITEM_IDS: Final[tuple[str, ...]] = tuple(
    item_id for item_id in TN23_CHECKLIST_ITEMS if item_id not in BLOCKED_INFRA_ITEMS
)

_ID_PROFIT = "verdict.profit"
_ID_WEEK = "verdict.unattended_week"
_ID_LIVE = "verdict.live_binding"
_ID_PROCURE = "verdict.procure_vps"
_ID_INVENTED = "verdict.invented_ksa_or_latency"
_ID_INPUTS = "verdict.inputs"
_ID_INCOMPLETE = "verdict.incomplete_checklist"
_ID_POWERS = "verdict.promotion_activation"

_ALLOWED_ITEM_STATUSES: Final[frozenset[str]] = frozenset({"pass", "refuse"})


class ChecklistItemStatus(StrEnum):
    """Published fold outcome for one TN-23 checklist item."""

    PASSED = "pass"
    REFUSED = "refuse"
    SKIPPED_BLOCKED_INFRA = "skipped-blocked-infra"


class WeekInterruptionClass(StrEnum):
    """Whether an interruption restarts the full-week clock (FR-059)."""

    PLANNED_DRILL_BOUNDARY = "planned-drill-boundary"
    UNPLANNED = "unplanned"


def refuse_profit_in_verdict(**extra: object) -> TypedRefusal:
    """Profit, loss, win rate, and paper performance never enter the verdict."""
    _ = check_publish_never_act(PublishAct.SIZE)
    _ = refuse_paper_pnl_to_treasury(extra.get("amount"))
    return policy(
        "profit",
        "profit, loss, win rate, and paper performance never enter the TN-23 "
        "live-readiness verdict; the packet is machinery evidence only "
        "(AD-32; DEC-0208; FR-076)",
        failure_id=_ID_PROFIT,
        profit_enters_verdict=False,
        **extra,
    )


def refuse_unattended_paper_week(**extra: object) -> TypedRefusal:
    """Story 28.8 does not run the unattended paper week."""
    return policy(
        "paper_week",
        "the factory story folds the TN-23 checklist; it does not run an "
        "unattended paper week (AR-87)",
        failure_id=_ID_WEEK,
        runs_unattended_paper_week=False,
        **extra,
    )


def refuse_live_binding(**extra: object) -> TypedRefusal:
    """This epic opens no live binding and grants no live-money authority."""
    return policy(
        "live_binding",
        "Epic 28 opens no live binding and grants no live-money authority; "
        "promotion and activation remain separate powers (DEC-0261)",
        failure_id=_ID_LIVE,
        opens_live_binding=False,
        **extra,
    )


def refuse_procure_vps(**extra: object) -> TypedRefusal:
    """Story 28.8 does not procure a VPS."""
    return policy(
        "vps_procurement",
        "the live-readiness verdict records skipped VPS acceptance; it does "
        "not procure a VPS (DEC-0260, AR-87)",
        failure_id=_ID_PROCURE,
        **extra,
    )


def refuse_invented_ksa_or_latency_number(**extra: object) -> TypedRefusal:
    """FTR-07: the verdict never fills KSA matrix values or latency gates."""
    return policy(
        "invented-value",
        "KSA matrix values remain a pre-soak operator ratification and numeric "
        "hot-path/latency gates remain unset until measured baselines exist; "
        "the verdict packet invents neither (FTR-07)",
        failure_id=_ID_INVENTED,
        **extra,
    )


def refuse_merged_promotion_activation(**extra: object) -> TypedRefusal:
    """Promotion and activation stay two powers (DEC-0213 / DEC-0261)."""
    return policy(
        "promotion_activation",
        "promotion and activation remain separate powers; this epic never "
        "merges them or treats a passing verdict as exposure (DEC-0261)",
        failure_id=_ID_POWERS,
        **extra,
    )


def refuse_same_day_activation(**extra: object) -> TypedRefusal:
    """Activation still waits for the next account day boundary."""
    return policy(
        "activation",
        "activation takes effect at the next account-scoped day boundary; "
        "no same-day trade path exists (DEC-0261)",
        failure_id=_ID_POWERS,
        **extra,
    )


def run_unattended_paper_week(**extra: object) -> TypedRefusal:
    """Closed: the factory lane never starts the soak week."""
    return refuse_unattended_paper_week(**extra)


def apply_week_interruption(kind: object) -> Result[WeekClockDecision]:
    """Unplanned interruption restarts the full-week clock (FR-059)."""
    token = clean_token(kind)
    if token is None:
        return invalid(
            "interruption",
            "week interruption is planned-drill-boundary, unplanned, or a "
            "declared boundary/drill point",
            given=repr(kind),
            failure_id=_ID_INPUTS,
        )
    if token in {WeekInterruptionClass.PLANNED_DRILL_BOUNDARY.value} | set(
        DECLARED_FAULT_INJECTION_POINTS
    ):
        return Ok(
            WeekClockDecision(
                interruption=WeekInterruptionClass.PLANNED_DRILL_BOUNDARY,
                restart_full_week_clock=False,
                week_complete=False,
            )
        )
    if token == WeekInterruptionClass.UNPLANNED.value:
        return Ok(
            WeekClockDecision(
                interruption=WeekInterruptionClass.UNPLANNED,
                restart_full_week_clock=True,
                week_complete=False,
            )
        )
    return invalid(
        "interruption",
        "unknown week interruption class",
        given=token,
        allowed=(
            WeekInterruptionClass.PLANNED_DRILL_BOUNDARY.value,
            WeekInterruptionClass.UNPLANNED.value,
            *sorted(DECLARED_FAULT_INJECTION_POINTS),
        ),
        failure_id=_ID_INPUTS,
    )


@dataclass(frozen=True, slots=True)
class WeekClockDecision:
    """Clock fold for one interruption — never a duration gate."""

    interruption: WeekInterruptionClass
    restart_full_week_clock: bool
    week_complete: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "interruption": self.interruption.value,
                "restart_full_week_clock": self.restart_full_week_clock,
                "week_complete": self.week_complete,
            }
        )


@dataclass(frozen=True, slots=True)
class ChecklistItemFold:
    """One journaled TN-23 item with pass/refuse and evidence."""

    item_id: str
    status: ChecklistItemStatus
    evidence_fp1: Fingerprint | None
    incidents: tuple[str, ...]
    recovery_proof_fp1: Fingerprint | None
    blocked_infra: str | None
    value_status: str | None

    def as_mapping(self) -> Mapping[str, object]:
        body: dict[str, object] = {
            "incidents": list(self.incidents),
            "item_id": self.item_id,
            "status": self.status.value,
        }
        if self.blocked_infra is not None:
            body["blocked_infra"] = self.blocked_infra
        if self.evidence_fp1 is not None:
            body["evidence_fp1"] = self.evidence_fp1.value
        if self.recovery_proof_fp1 is not None:
            body["recovery_proof_fp1"] = self.recovery_proof_fp1.value
        if self.value_status is not None:
            body["value_status"] = self.value_status
        return MappingProxyType(body)


@dataclass(frozen=True, slots=True)
class LiveInstrumentReadiness:
    """Per-instrument live-binding preconditions (TN-9/20)."""

    instrument: str
    verified_capability_profile: bool
    live_conditioned_sqs_baseline: bool
    live_path_rung_baseline: bool
    kyc: bool
    written_fee_schedule: bool
    current_config: bool
    silent_battery_pass: bool
    ready: bool
    missing: tuple[str, ...]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "current_config": self.current_config,
                "instrument": self.instrument,
                "kyc": self.kyc,
                "live_conditioned_sqs_baseline": self.live_conditioned_sqs_baseline,
                "live_path_rung_baseline": self.live_path_rung_baseline,
                "missing": list(self.missing),
                "ready": self.ready,
                "silent_battery_pass": self.silent_battery_pass,
                "verified_capability_profile": self.verified_capability_profile,
                "written_fee_schedule": self.written_fee_schedule,
            }
        )


@dataclass(frozen=True, slots=True)
class OperatorProceeding:
    """Recorded operator choice after a passing verdict — never a live grant."""

    live_binding_open: bool
    grants_live_money_authority: bool
    promotion_activation_separate: bool
    activation_waits_for_day_boundary: bool
    paper_milestone_immutable: bool
    paper_milestone_fp1: Fingerprint

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "activation_waits_for_day_boundary": self.activation_waits_for_day_boundary,
                "grants_live_money_authority": self.grants_live_money_authority,
                "live_binding_open": self.live_binding_open,
                "paper_milestone_fp1": self.paper_milestone_fp1.value,
                "paper_milestone_immutable": self.paper_milestone_immutable,
                "promotion_activation_separate": self.promotion_activation_separate,
            }
        )


@dataclass(frozen=True, slots=True)
class LiveReadinessVerdict:
    """Fingerprinted TN-23 machinery verdict (Story 28.8)."""

    format_version: int
    fingerprint: Fingerprint
    items: tuple[ChecklistItemFold, ...]
    qa_debt_matrix_fp1: Fingerprint
    first_hours_fp1: Fingerprint
    value_status: Mapping[str, str]
    incidents: tuple[str, ...]
    recovery_proofs: tuple[str, ...]
    live_instruments: tuple[LiveInstrumentReadiness, ...]
    live_credentials_present: bool
    live_ready: bool
    live_delayed: bool
    demo_milestone_invalidated: bool
    week_complete: bool
    unattended_week_ran: bool
    live_binding_open: bool
    grants_live_money_authority: bool
    profit_enters_verdict: bool
    blocked_infra: tuple[str, ...]
    ok: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "blocked_infra": list(self.blocked_infra),
            "class": VERDICT_PACKET_CLASS,
            "demo_milestone_invalidated": self.demo_milestone_invalidated,
            "first_hours_fp1": self.first_hours_fp1.value,
            "format_version": self.format_version,
            "grants_live_money_authority": self.grants_live_money_authority,
            "incidents": list(self.incidents),
            "items": [dict(item.as_mapping()) for item in self.items],
            "live_binding_open": self.live_binding_open,
            "live_credentials_present": self.live_credentials_present,
            "live_delayed": self.live_delayed,
            "live_instruments": [dict(row.as_mapping()) for row in self.live_instruments],
            "live_ready": self.live_ready,
            "ok": self.ok,
            "profit_enters_verdict": self.profit_enters_verdict,
            "qa_debt_matrix_fp1": self.qa_debt_matrix_fp1.value,
            "recovery_proofs": list(self.recovery_proofs),
            "surface": VERDICT_SURFACE,
            "unattended_week_ran": self.unattended_week_ran,
            "value_status": dict(self.value_status),
            "week_complete": self.week_complete,
        }

    def as_mapping(self) -> Mapping[str, object]:
        body = self.fp1_identity()
        body["fingerprint"] = self.fingerprint.value
        body["opens_live_binding"] = OPENS_LIVE_BINDING
        body["promotion_activation_separate"] = PROMOTION_AND_ACTIVATION_ARE_SEPARATE
        body["activation_waits_for_day_boundary"] = ACTIVATION_WAITS_FOR_DAY_BOUNDARY
        body["paper_milestone_immutable"] = PAPER_MILESTONE_IMMUTABLE
        body["runs_unattended_paper_week"] = RUNS_UNATTENDED_PAPER_WEEK
        body["whole_system_surfaces"] = list(WHOLE_SYSTEM_SURFACES)
        body["pre_week_stories"] = list(PRE_WEEK_STORIES)
        return MappingProxyType(body)


def fold_tn23_checklist(journaled_items: object) -> Result[tuple[ChecklistItemFold, ...]]:
    """Fold journaled items onto the closed TN-23 catalog."""
    forbidden = _scan_forbidden_keys(journaled_items)
    if forbidden is not None:
        return refuse_profit_in_verdict(given=forbidden)
    parsed = _parse_journaled_items(journaled_items)
    if is_refusal(parsed):
        return parsed
    by_id = parsed.value
    folded: list[ChecklistItemFold] = []
    missing: list[str] = []
    for item_id in TN23_CHECKLIST_ITEMS:
        if item_id in by_id:
            folded.append(by_id[item_id])
            continue
        blocked = BLOCKED_INFRA_ITEMS.get(item_id)
        if blocked is not None:
            folded.append(
                ChecklistItemFold(
                    item_id=item_id,
                    status=ChecklistItemStatus.SKIPPED_BLOCKED_INFRA,
                    evidence_fp1=None,
                    incidents=(),
                    recovery_proof_fp1=None,
                    blocked_infra=blocked,
                    value_status=None,
                )
            )
            continue
        missing.append(item_id)
    if missing:
        return policy(
            "checklist",
            "every non-blocked TN-23 checklist item needs a journaled "
            "pass/refuse with an evidence fingerprint",
            failure_id=_ID_INCOMPLETE,
            missing=tuple(missing),
        )
    extra = sorted(item_id for item_id in by_id if item_id not in TN23_CHECKLIST_ITEMS)
    if extra:
        return invalid(
            "journaled_items",
            "unknown TN-23 checklist item",
            given=tuple(extra),
            allowed=list(TN23_CHECKLIST_ITEMS),
            failure_id=_ID_INPUTS,
        )
    return Ok(tuple(folded))


def evaluate_live_instrument_readiness(
    *,
    live_credentials_present: object,
    instruments: object = (),
) -> Result[tuple[LiveInstrumentReadiness, ...]]:
    """Evaluate per-instrument live preconditions; absence delays live only."""
    if not isinstance(live_credentials_present, bool):
        return invalid(
            "live_credentials_present",
            "live-credential presence is a bool; this story does not open them",
            given=repr(live_credentials_present),
            failure_id=_ID_INPUTS,
        )
    forbidden = _scan_forbidden_keys(instruments)
    if forbidden is not None:
        return refuse_profit_in_verdict(given=forbidden)
    rows = _parse_live_instruments(instruments, live_credentials_present)
    if is_refusal(rows):
        return rows
    return Ok(rows.value)


def publish_live_readiness_verdict(
    *,
    journaled_items: object,
    first_hours_fp1: object,
    live_credentials_present: object = False,
    live_instruments: object = (),
    value_status: object = None,
    incidents: object = (),
    recovery_proofs: object = (),
    qa_debt_matrix: object = None,
    run_unattended_week: object = False,
    claim_week_complete: object = False,
    open_live_binding: object = False,
    procure_vps: object = False,
    invented_ksa_value: object = None,
    invented_latency_value: object = None,
    soak_duration: object = None,
    profit: object = None,
    loss: object = None,
    win_rate: object = None,
    paper_performance: object = None,
) -> Result[LiveReadinessVerdict]:
    """Publish the Story 28.8 TN-23 verdict packet from journaled evidence."""
    if run_unattended_week is True or claim_week_complete is True:
        return refuse_unattended_paper_week(
            run_unattended_week=run_unattended_week,
            claim_week_complete=claim_week_complete,
        )
    if open_live_binding is True:
        return refuse_live_binding()
    if procure_vps is True:
        return refuse_procure_vps()
    if (
        invented_ksa_value is not None
        or invented_latency_value is not None
        or soak_duration is not None
    ):
        return refuse_invented_ksa_or_latency_number(
            invented_ksa_value=repr(invented_ksa_value),
            invented_latency_value=repr(invented_latency_value),
            soak_duration=repr(soak_duration),
        )
    if (
        profit is not None
        or loss is not None
        or win_rate is not None
        or paper_performance is not None
    ):
        return refuse_profit_in_verdict(
            profit=repr(profit),
            loss=repr(loss),
            win_rate=repr(win_rate),
            paper_performance=repr(paper_performance),
        )
    if RUNS_UNATTENDED_PAPER_WEEK or OPENS_LIVE_BINDING or PROFIT_ENTERS_VERDICT:
        return policy(  # pragma: no cover - pinned False surface markers
            "verdict",
            "surface markers forbid running the paper week, opening a live "
            "binding, or admitting profit into the verdict",
            failure_id=_ID_WEEK,
        )

    hours_fp = _as_fingerprint(first_hours_fp1, "first_hours_fp1")
    if is_refusal(hours_fp):
        return hours_fp

    folded = fold_tn23_checklist(journaled_items)
    if is_refusal(folded):
        return folded

    live_rows = evaluate_live_instrument_readiness(
        live_credentials_present=live_credentials_present,
        instruments=live_instruments,
    )
    if is_refusal(live_rows):
        return live_rows
    if not isinstance(live_credentials_present, bool):
        return invalid(
            "live_credentials_present",
            "live-credential presence is a bool",
            given=repr(live_credentials_present),
            failure_id=_ID_INPUTS,
        )

    statuses = _parse_value_status(value_status)
    if is_refusal(statuses):
        return statuses
    numeric = _refuse_numeric_ksa(statuses.value)
    if numeric is not None:
        return numeric

    incident_ids = _parse_token_tuple(incidents, "incidents")
    if is_refusal(incident_ids):
        return incident_ids
    recovery_ids = _parse_token_tuple(recovery_proofs, "recovery_proofs")
    if is_refusal(recovery_ids):
        return recovery_ids

    matrix = _as_qa_debt_matrix(qa_debt_matrix)
    if is_refusal(matrix):
        return matrix

    blocked = tuple(
        sorted(
            {
                item.blocked_infra
                for item in folded.value
                if item.status is ChecklistItemStatus.SKIPPED_BLOCKED_INFRA
                and item.blocked_infra is not None
            }
        )
    )
    item_ok = all(item.status is not ChecklistItemStatus.REFUSED for item in folded.value)
    live_ready = (
        live_credentials_present is True
        and bool(live_rows.value)
        and all(row.ready for row in live_rows.value)
    )
    live_delayed = not live_ready
    packet = LiveReadinessVerdict(
        format_version=VERDICT_PACKET_FORMAT_VERSION,
        fingerprint=Fingerprint(value="fp1:sha256:" + ("0" * 64)),
        items=folded.value,
        qa_debt_matrix_fp1=matrix.value.fingerprint,
        first_hours_fp1=hours_fp.value,
        value_status=MappingProxyType(dict(statuses.value)),
        incidents=incident_ids.value,
        recovery_proofs=recovery_ids.value,
        live_instruments=live_rows.value,
        live_credentials_present=live_credentials_present,
        live_ready=live_ready,
        live_delayed=live_delayed,
        demo_milestone_invalidated=False,
        week_complete=False,
        unattended_week_ran=False,
        live_binding_open=False,
        grants_live_money_authority=False,
        profit_enters_verdict=False,
        blocked_infra=blocked,
        ok=item_ok,
    )
    stamped = fingerprint(packet.fp1_identity())
    if is_refusal(stamped):
        return stamped
    return Ok(
        LiveReadinessVerdict(
            format_version=VERDICT_PACKET_FORMAT_VERSION,
            fingerprint=stamped.value,
            items=folded.value,
            qa_debt_matrix_fp1=matrix.value.fingerprint,
            first_hours_fp1=hours_fp.value,
            value_status=MappingProxyType(dict(statuses.value)),
            incidents=incident_ids.value,
            recovery_proofs=recovery_ids.value,
            live_instruments=live_rows.value,
            live_credentials_present=live_credentials_present,
            live_ready=live_ready,
            live_delayed=live_delayed,
            demo_milestone_invalidated=False,
            week_complete=False,
            unattended_week_ran=False,
            live_binding_open=False,
            grants_live_money_authority=False,
            profit_enters_verdict=False,
            blocked_infra=blocked,
            ok=item_ok,
        )
    )


def record_operator_proceed(
    verdict: object,
    *,
    request_live_binding: object = False,
    merge_promotion_activation: object = False,
    same_day_activation: object = False,
) -> Result[OperatorProceeding]:
    """A passing verdict still opens no live binding (DEC-0261)."""
    if not isinstance(verdict, LiveReadinessVerdict):
        return invalid(
            "verdict",
            "operator proceed reads a LiveReadinessVerdict",
            given=type(verdict).__name__,
            failure_id=_ID_INPUTS,
        )
    if request_live_binding is True:
        return refuse_live_binding()
    if merge_promotion_activation is True:
        return refuse_merged_promotion_activation()
    if same_day_activation is True:
        return refuse_same_day_activation()
    return Ok(
        OperatorProceeding(
            live_binding_open=False,
            grants_live_money_authority=False,
            promotion_activation_separate=True,
            activation_waits_for_day_boundary=True,
            paper_milestone_immutable=True,
            paper_milestone_fp1=verdict.fingerprint,
        )
    )


def _normalize_key(name: str) -> str:
    return name.strip().lower().replace("-", "_").replace(" ", "_")


def _scan_forbidden_keys(value: object) -> str | None:
    if isinstance(value, Mapping):
        for raw_key, raw_value in cast("Mapping[object, object]", value).items():
            if isinstance(raw_key, str):
                token = _normalize_key(raw_key)
                if token in FORBIDDEN_VERDICT_KEYS:
                    return token
            nested = _scan_forbidden_keys(raw_value)
            if nested is not None:
                return nested
        return None
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        for item in cast("Sequence[object]", value):
            nested = _scan_forbidden_keys(item)
            if nested is not None:
                return nested
    return None


def _as_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return invalid(
            field,
            "evidence fingerprint is a Fingerprint",
            given=repr(value),
            failure_id=_ID_INPUTS,
        )
    return Ok(parsed.value)


def _as_qa_debt_matrix(value: object) -> Result[QaDebtClosureMatrix]:
    if isinstance(value, QaDebtClosureMatrix):
        return Ok(value)
    if value is not None:
        return invalid(
            "qa_debt_matrix",
            "qa_debt_matrix is a QaDebtClosureMatrix or omitted",
            given=type(value).__name__,
            failure_id=_ID_INPUTS,
        )
    return run_paper_milestone_qa_debt_gate()


def _parse_journaled_items(
    value: object,
) -> Result[dict[str, ChecklistItemFold]]:
    if value is None:
        return Ok({})
    if isinstance(value, Mapping):
        body = cast("Mapping[object, object]", value)
        items: list[object] = []
        for raw_key, raw_item in body.items():
            token = clean_token(raw_key)
            if token is None:
                return invalid(
                    "journaled_items",
                    "journal keys are checklist item ids",
                    given=repr(raw_key),
                    failure_id=_ID_INPUTS,
                )
            if isinstance(raw_item, ChecklistItemFold):
                if raw_item.item_id != token:
                    return invalid(
                        "journaled_items",
                        "fold item_id must match the mapping key",
                        given=raw_item.item_id,
                        expected=token,
                        failure_id=_ID_INPUTS,
                    )
                items.append(raw_item)
                continue
            if not isinstance(raw_item, Mapping):
                return invalid(
                    token,
                    "a journaled item is ChecklistItemFold or a mapping",
                    given=type(raw_item).__name__,
                    failure_id=_ID_INPUTS,
                )
            entry = dict(cast("Mapping[str, object]", raw_item))
            entry.setdefault("item_id", token)
            items.append(entry)
        return _parse_journaled_sequence(items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return _parse_journaled_sequence(cast("Sequence[object]", value))
    return invalid(
        "journaled_items",
        "journaled items are a mapping or sequence of checklist folds",
        given=type(value).__name__,
        failure_id=_ID_INPUTS,
    )


def _parse_journaled_sequence(
    value: Sequence[object],
) -> Result[dict[str, ChecklistItemFold]]:
    parsed: dict[str, ChecklistItemFold] = {}
    for raw in value:
        item = _parse_one_item(raw)
        if is_refusal(item):
            return item
        if item.value.item_id in parsed:
            return invalid(
                "journaled_items",
                "checklist item ids must be unique",
                given=item.value.item_id,
                failure_id=_ID_INPUTS,
            )
        parsed[item.value.item_id] = item.value
    return Ok(parsed)


def _parse_one_item(value: object) -> Result[ChecklistItemFold]:
    if isinstance(value, ChecklistItemFold):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "journaled_items",
            "a journaled item is ChecklistItemFold or a mapping",
            given=type(value).__name__,
            failure_id=_ID_INPUTS,
        )
    body = cast("Mapping[str, object]", value)
    forbidden = _scan_forbidden_keys(body)
    if forbidden is not None:
        return refuse_profit_in_verdict(given=forbidden)
    item_id = clean_token(body.get("item_id"))
    if item_id is None or item_id not in TN23_CHECKLIST_ITEMS:
        return invalid(
            "item_id",
            "journaled item_id must be a TN-23 checklist id",
            given=repr(body.get("item_id")),
            allowed=list(TN23_CHECKLIST_ITEMS),
            failure_id=_ID_INPUTS,
        )
    status_token = clean_token(body.get("status"))
    if status_token not in _ALLOWED_ITEM_STATUSES:
        return invalid(
            "status",
            "journaled status is pass or refuse",
            given=repr(body.get("status")),
            failure_id=_ID_INPUTS,
        )
    evidence_raw = body.get("evidence_fp1")
    if evidence_raw is None:
        return invalid(
            "evidence_fp1",
            "a journaled pass/refuse carries an evidence fingerprint",
            item_id=item_id,
            failure_id=_ID_INPUTS,
        )
    evidence = _as_fingerprint(evidence_raw, "evidence_fp1")
    if is_refusal(evidence):
        return evidence
    recovery_raw = body.get("recovery_proof_fp1")
    recovery: Fingerprint | None = None
    if recovery_raw is not None:
        parsed_recovery = _as_fingerprint(recovery_raw, "recovery_proof_fp1")
        if is_refusal(parsed_recovery):
            return parsed_recovery
        recovery = parsed_recovery.value
    incidents = _parse_token_tuple(body.get("incidents", ()), "incidents")
    if is_refusal(incidents):
        return incidents
    value_status = body.get("value_status")
    status_text: str | None = None
    if value_status is not None:
        token = clean_token(value_status)
        if token is None:
            return invalid(
                "value_status",
                "item value_status is blank, provisional-evidence, or ratified",
                given=repr(value_status),
                failure_id=_ID_INPUTS,
            )
        status_text = token
    blocked = BLOCKED_INFRA_ITEMS.get(item_id)
    return Ok(
        ChecklistItemFold(
            item_id=item_id,
            status=ChecklistItemStatus(status_token),
            evidence_fp1=evidence.value,
            incidents=incidents.value,
            recovery_proof_fp1=recovery,
            blocked_infra=blocked,
            value_status=status_text,
        )
    )


def _parse_live_instruments(
    value: object,
    credentials_present: bool,
) -> Result[tuple[LiveInstrumentReadiness, ...]]:
    if value is None:
        return Ok(())
    entries: Sequence[object]
    if isinstance(value, Mapping):
        built: list[object] = []
        for raw_key, raw_item in cast("Mapping[object, object]", value).items():
            token = clean_token(raw_key)
            if token is None:
                return invalid(
                    "live_instruments",
                    "live instrument keys are instrument ids",
                    given=repr(raw_key),
                    failure_id=_ID_INPUTS,
                )
            if isinstance(raw_item, LiveInstrumentReadiness):
                if raw_item.instrument != token:
                    return invalid(
                        "live_instruments",
                        "instrument id must match the mapping key",
                        given=raw_item.instrument,
                        expected=token,
                        failure_id=_ID_INPUTS,
                    )
                built.append(raw_item)
                continue
            if not isinstance(raw_item, Mapping):
                return invalid(
                    token,
                    "live instrument evidence is a mapping of requirement flags",
                    given=type(raw_item).__name__,
                    failure_id=_ID_INPUTS,
                )
            entry = dict(cast("Mapping[str, object]", raw_item))
            entry.setdefault("instrument", token)
            built.append(entry)
        entries = built
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        entries = cast("Sequence[object]", value)
    else:
        return invalid(
            "live_instruments",
            "live instruments are a mapping or sequence",
            given=type(value).__name__,
            failure_id=_ID_INPUTS,
        )
    rows: list[LiveInstrumentReadiness] = []
    seen: set[str] = set()
    for raw in entries:
        row = _parse_one_instrument(raw, credentials_present)
        if is_refusal(row):
            return row
        if row.value.instrument in seen:
            return invalid(
                "live_instruments",
                "live instrument ids must be unique",
                given=row.value.instrument,
                failure_id=_ID_INPUTS,
            )
        seen.add(row.value.instrument)
        rows.append(row.value)
    return Ok(tuple(rows))


def _parse_one_instrument(
    value: object,
    credentials_present: bool,
) -> Result[LiveInstrumentReadiness]:
    if isinstance(value, LiveInstrumentReadiness):
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "live_instruments",
            "each live instrument is LiveInstrumentReadiness or a mapping",
            given=type(value).__name__,
            failure_id=_ID_INPUTS,
        )
    body = cast("Mapping[str, object]", value)
    instrument = clean_token(body.get("instrument"))
    if instrument is None:
        return invalid(
            "instrument",
            "each live instrument names an instrument id",
            given=repr(body.get("instrument")),
            failure_id=_ID_INPUTS,
        )
    flags: dict[str, bool] = {}
    for name in LIVE_INSTRUMENT_REQUIREMENTS:
        raw = body.get(name, False)
        if not isinstance(raw, bool):
            return invalid(
                name,
                "live-instrument requirement flags are bools",
                given=repr(raw),
                instrument=instrument,
                failure_id=_ID_INPUTS,
            )
        flags[name] = raw and credentials_present
    missing = tuple(name for name in LIVE_INSTRUMENT_REQUIREMENTS if not flags[name])
    return Ok(
        LiveInstrumentReadiness(
            instrument=instrument,
            verified_capability_profile=flags["verified_capability_profile"],
            live_conditioned_sqs_baseline=flags["live_conditioned_sqs_baseline"],
            live_path_rung_baseline=flags["live_path_rung_baseline"],
            kyc=flags["kyc"],
            written_fee_schedule=flags["written_fee_schedule"],
            current_config=flags["current_config"],
            silent_battery_pass=flags["silent_battery_pass"],
            ready=not missing,
            missing=missing,
        )
    )


def _parse_value_status(value: object) -> Result[Mapping[str, str]]:
    if value is None:
        return Ok({})
    if not isinstance(value, Mapping):
        return invalid(
            "value_status",
            "value_status is a mapping of variable name to status",
            given=type(value).__name__,
            failure_id=_ID_INPUTS,
        )
    body = cast("Mapping[object, object]", value)
    forbidden = _scan_forbidden_keys(body)
    if forbidden is not None:
        return refuse_profit_in_verdict(given=forbidden)
    parsed: dict[str, str] = {}
    for raw_name, raw_status in body.items():
        name = clean_token(raw_name)
        status = clean_token(raw_status)
        if name is None or status is None:
            return invalid(
                "value_status",
                "value_status entries are name -> blank|provisional-evidence|ratified",
                given=repr(raw_name),
                failure_id=_ID_INPUTS,
            )
        parsed[name] = status
    return Ok(parsed)


def _refuse_numeric_ksa(statuses: Mapping[str, str]) -> TypedRefusal | None:
    if "ksa_effect_matrix" in statuses and statuses["ksa_effect_matrix"] not in {
        "blank",
        "provisional-evidence",
        "ratified",
    }:
        return refuse_invented_ksa_or_latency_number(
            name="ksa_effect_matrix",
            given=statuses["ksa_effect_matrix"],
        )
    return None


def _parse_token_tuple(value: object, field: str) -> Result[tuple[str, ...]]:
    if value is None:
        return Ok(())
    if isinstance(value, str):
        token = clean_token(value)
        if token is None:
            return invalid(
                field,
                "incident and recovery ids are non-blank strings",
                given=repr(value),
                failure_id=_ID_INPUTS,
            )
        if _normalize_key(token) in FORBIDDEN_VERDICT_KEYS:
            return refuse_profit_in_verdict(given=_normalize_key(token), field=field)
        return Ok((token,))
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            field,
            "incidents and recovery proofs are sequences of ids",
            given=type(value).__name__,
            failure_id=_ID_INPUTS,
        )
    items: list[str] = []
    for raw in cast("Sequence[object]", value):
        token = clean_token(raw)
        if token is None:
            return invalid(
                field,
                "each incident or recovery id is a non-blank string",
                given=repr(raw),
                failure_id=_ID_INPUTS,
            )
        if _normalize_key(token) in FORBIDDEN_VERDICT_KEYS:
            return refuse_profit_in_verdict(given=_normalize_key(token), field=field)
        items.append(token)
    return Ok(tuple(items))
