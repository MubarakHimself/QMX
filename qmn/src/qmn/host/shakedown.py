"""Layer-2 technical demo shakedown (Story 26.11 / AD-32 / QMX-F067).

Runs on a demo or paper-validation binding — never a live binding. It exercises
required windows, protection effects, the paper ledger, the kill line,
reconciliation, SQS baseline conditioning, callback containment, and a
command-path dry run. Evidence is assembled for the human signature and is
never performance proof. FTR-07: soak duration and KSA matrix values are not
invented here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    AccountRole,
    Duration,
    Fingerprint,
    Instant,
    Instrument,
    Money,
    Ok,
    Result,
    TypedRefusal,
    VenueId,
    World,
    is_refusal,
)
from qmf.risk.admission import Layer2Result, run_layer2_shakedown

from qmn.capital.kill_line import evaluate_kill_line, refuse_invented_kill_line_floor
from qmn.host._refuse import clean_token, invalid, policy
from qmn.ledger.binding_ledger import BindingVirtualLedger, seed_binding_ledger
from qmn.mis.signal_snapshot import SqsBaselineKey, sqs_baseline_key
from qmn.order.pacer import admission_class_for
from qmn.order.protection import require_venue_resident_protective_stop
from qmn.protection.effect_matrix import (
    VALUE_STATUS_BLANK,
    CompiledEffectMatrix,
    compile_effect_matrix,
    matrix_blocks_role_live,
    matrix_blocks_soak,
    matrix_supplies_no_default_values,
)
from qmn.protection.windows import (
    ResolvedWindowSettings,
    refuse_invented_window_minutes,
    require_resolved_window_settings,
)
from qmn.reconcile.engine import (
    LookbackStatus,
    ReadbackStatus,
    ReconciliationReport,
    ReconciliationTrigger,
    run_reconciliation,
)
from qmn.seats.host import (
    FORBIDDEN_SEAT_SURFACE_KEYS,
    SeatContainment,
    refuse_invented_seat_bounds,
)
from qmn.venue import Command, ConformanceDouble, VenueClientKind

__all__ = [
    "SHAKEDOWN_EXERCISES",
    "SHAKEDOWN_FOR_HUMAN_SIGNATURE",
    "SHAKEDOWN_IS_PERFORMANCE_PROOF",
    "SHAKEDOWN_SURFACE",
    "ShakedownEvidence",
    "ShakedownPlan",
    "ShakedownSignaturePage",
    "assemble_shakedown_signature_page",
    "refuse_invented_soak_or_ksa_number",
    "refuse_shakedown_as_performance_proof",
    "run_demo_shakedown",
]

SHAKEDOWN_SURFACE: Final[str] = "qmn.host.shakedown"
SHAKEDOWN_FOR_HUMAN_SIGNATURE: Final[bool] = True
SHAKEDOWN_IS_PERFORMANCE_PROOF: Final[bool] = False
# Same tokens as the promotion battery — demo shakedown never claims live SQS.
_DEMO_BASELINE_ENVIRONMENT: Final[str] = "demo"
_LIVE_BASELINE_ENVIRONMENT: Final[str] = "live"

SHAKEDOWN_EXERCISES: Final[tuple[str, ...]] = (
    "required_windows",
    "protection_effects",
    "paper_ledger",
    "kill_line",
    "reconciliation",
    "sqs_baseline_conditioning",
    "callback_containment",
    "command_path_dry_run",
)

_ALLOWED_SHAKEDOWN_ROLES: Final[frozenset[AccountRole]] = frozenset(
    {AccountRole.DEMO, AccountRole.PAPER_VALIDATION}
)


def refuse_shakedown_as_performance_proof(**extra: object) -> TypedRefusal:
    """Shakedown evidence is for the human signature, never a performance proof."""
    return policy(
        "shakedown",
        "Layer-2 technical shakedown proves the machinery works and proves "
        "nothing about edge; evidence is assembled for the human signature, "
        "never treated as performance proof (AD-32)",
        is_performance_proof=False,
        for_human_signature=True,
        **extra,
    )


def refuse_invented_soak_or_ksa_number(**extra: object) -> TypedRefusal:
    """FTR-07: shakedown invents no soak duration or KSA matrix values."""
    return policy(
        "invented-value",
        "KSA matrix values remain a pre-soak operator ratification and numeric "
        "soak/latency gates remain unset until measured baselines exist; the "
        "shakedown invents neither (FTR-07)",
        **extra,
    )


@dataclass(frozen=True, slots=True)
class ShakedownPlan:
    """Caller-supplied demo/paper fixtures. No live binding, no invented numbers."""

    binding_identity: str
    shakedown_role: AccountRole
    live_path_rung_baseline_present: bool
    sensor_baselines_present: bool
    window_settings: ResolvedWindowSettings
    ledger_binding_epoch: Fingerprint
    ledger_seed: Money
    ledger_recorded_at: Instant
    kill_line_capital_floor: Money
    kill_line_equity: Money
    kill_line_evaluated_at: Instant
    sqs_venue: VenueId
    sqs_environment: str
    sqs_instrument: Instrument
    callback_deadline: Duration
    memory_ceiling_bytes: int
    dry_run_command: Command
    protective_stop_forms: Mapping[str, str]
    effect_matrix_value_status: str = VALUE_STATUS_BLANK
    effect_matrix_cells: tuple[Mapping[str, object], ...] | None = None
    treat_as_performance_proof: bool = False
    soak_duration: object | None = None
    ksa_numeric_value: object | None = None
    invented_window_minutes: object | None = None
    claim_sqs_live_conditioned: bool = False

    @classmethod
    def try_create(
        cls,
        *,
        binding_identity: object,
        shakedown_role: object,
        live_path_rung_baseline_present: object,
        sensor_baselines_present: object,
        window_settings: object,
        ledger_binding_epoch: object,
        ledger_seed: object,
        ledger_recorded_at: object,
        kill_line_capital_floor: object,
        kill_line_equity: object,
        kill_line_evaluated_at: object,
        sqs_venue: object,
        sqs_environment: object,
        sqs_instrument: object,
        callback_deadline: object,
        memory_ceiling_bytes: object,
        dry_run_command: object,
        protective_stop_forms: object,
        effect_matrix_value_status: object = VALUE_STATUS_BLANK,
        effect_matrix_cells: object = None,
        treat_as_performance_proof: object = False,
        soak_duration: object | None = None,
        ksa_numeric_value: object | None = None,
        invented_window_minutes: object | None = None,
        claim_sqs_live_conditioned: object = False,
    ) -> Result[ShakedownPlan]:
        identity = clean_token(binding_identity)
        if identity is None:
            return invalid(
                "binding_identity",
                "the shakedown names the binding identity it ran on",
                given=repr(binding_identity),
            )
        if not isinstance(shakedown_role, AccountRole):
            return invalid(
                "shakedown_role",
                "the shakedown declares an AccountRole",
                given=repr(shakedown_role),
            )
        if not isinstance(live_path_rung_baseline_present, bool):
            return invalid(
                "live_path_rung_baseline_present",
                "the live-path rung baseline prerequisite is a bool",
                given=repr(live_path_rung_baseline_present),
            )
        if not isinstance(sensor_baselines_present, bool):
            return invalid(
                "sensor_baselines_present",
                "the sensor-baseline prerequisite is a bool",
                given=repr(sensor_baselines_present),
            )
        if not isinstance(window_settings, ResolvedWindowSettings):
            return invalid(
                "window_settings",
                "required windows resolve through ResolvedWindowSettings; "
                "blank invents nothing",
                given=type(window_settings).__name__,
            )
        if not isinstance(ledger_binding_epoch, Fingerprint):
            return invalid(
                "ledger_binding_epoch",
                "the paper ledger seeds a CT-28 binding epoch fingerprint",
                given=repr(ledger_binding_epoch),
            )
        if not isinstance(ledger_seed, Money):
            return invalid(
                "ledger_seed",
                "paper ledger seed is Money; the shakedown invents no balance",
                given=repr(ledger_seed),
            )
        if not isinstance(ledger_recorded_at, Instant):
            return invalid(
                "ledger_recorded_at",
                "ledger seed carries an Instant",
                given=repr(ledger_recorded_at),
            )
        if kill_line_capital_floor is None:
            return refuse_invented_kill_line_floor(given="None")
        if not isinstance(kill_line_capital_floor, Money):
            return refuse_invented_kill_line_floor(given=repr(kill_line_capital_floor))
        if not isinstance(kill_line_equity, Money):
            return invalid(
                "kill_line_equity",
                "kill-line equity is marked virtual-ledger Money",
                given=repr(kill_line_equity),
            )
        if not isinstance(kill_line_evaluated_at, Instant):
            return invalid(
                "kill_line_evaluated_at",
                "kill-line evaluation carries an Instant",
                given=repr(kill_line_evaluated_at),
            )
        if not isinstance(sqs_venue, VenueId):
            return invalid(
                "sqs_venue",
                "SQS baseline key names a VenueId",
                given=repr(sqs_venue),
            )
        env = clean_token(sqs_environment)
        if env is None:
            return invalid(
                "sqs_environment",
                "SQS baseline is keyed by a non-empty environment token",
                given=repr(sqs_environment),
            )
        if not isinstance(sqs_instrument, Instrument):
            return invalid(
                "sqs_instrument",
                "SQS baseline key names an Instrument",
                given=repr(sqs_instrument),
            )
        if callback_deadline is None:
            return refuse_invented_seat_bounds("seat_callback_deadline", given="None")
        if not isinstance(callback_deadline, Duration):
            return refuse_invented_seat_bounds(
                "seat_callback_deadline", given=repr(callback_deadline)
            )
        if memory_ceiling_bytes is None:
            return refuse_invented_seat_bounds("seat_memory_ceiling", given="None")
        if not isinstance(dry_run_command, Command):
            return invalid(
                "dry_run_command",
                "command-path dry run reads a typed CT-19 Command",
                given=type(dry_run_command).__name__,
            )
        if not isinstance(protective_stop_forms, Mapping):
            return invalid(
                "protective_stop_forms",
                "command-path dry run reads declared CT-18 protective-stop forms",
                given=type(protective_stop_forms).__name__,
            )
        forms = {
            str(key): str(value)
            for key, value in cast("Mapping[object, object]", protective_stop_forms).items()
        }
        status = clean_token(effect_matrix_value_status) or VALUE_STATUS_BLANK
        cells: tuple[Mapping[str, object], ...] | None
        if effect_matrix_cells is None:
            cells = None
        elif isinstance(effect_matrix_cells, Sequence) and not isinstance(
            effect_matrix_cells, (str, bytes)
        ):
            parsed: list[Mapping[str, object]] = []
            for item in cast("Sequence[object]", effect_matrix_cells):
                if not isinstance(item, Mapping):
                    return invalid(
                        "effect_matrix_cells",
                        "each matrix cell declaration is a mapping",
                        given=type(item).__name__,
                    )
                parsed.append(cast("Mapping[str, object]", item))
            cells = tuple(parsed)
        else:
            return invalid(
                "effect_matrix_cells",
                "matrix cells are a sequence of mappings when supplied",
                given=type(effect_matrix_cells).__name__,
            )
        if not isinstance(treat_as_performance_proof, bool):
            return invalid(
                "treat_as_performance_proof",
                "treat_as_performance_proof is a bool",
                given=repr(treat_as_performance_proof),
            )
        if not isinstance(claim_sqs_live_conditioned, bool):
            return invalid(
                "claim_sqs_live_conditioned",
                "claim_sqs_live_conditioned is a bool",
                given=repr(claim_sqs_live_conditioned),
            )
        if not isinstance(memory_ceiling_bytes, int) or isinstance(
            memory_ceiling_bytes, bool
        ):
            return refuse_invented_seat_bounds(
                "seat_memory_ceiling", given=repr(memory_ceiling_bytes)
            )
        return Ok(
            cls(
                binding_identity=identity,
                shakedown_role=shakedown_role,
                live_path_rung_baseline_present=live_path_rung_baseline_present,
                sensor_baselines_present=sensor_baselines_present,
                window_settings=window_settings,
                ledger_binding_epoch=ledger_binding_epoch,
                ledger_seed=ledger_seed,
                ledger_recorded_at=ledger_recorded_at,
                kill_line_capital_floor=kill_line_capital_floor,
                kill_line_equity=kill_line_equity,
                kill_line_evaluated_at=kill_line_evaluated_at,
                sqs_venue=sqs_venue,
                sqs_environment=env,
                sqs_instrument=sqs_instrument,
                callback_deadline=callback_deadline,
                memory_ceiling_bytes=memory_ceiling_bytes,
                dry_run_command=dry_run_command,
                protective_stop_forms=MappingProxyType(forms),
                effect_matrix_value_status=status,
                effect_matrix_cells=cells,
                treat_as_performance_proof=treat_as_performance_proof,
                soak_duration=soak_duration,
                ksa_numeric_value=ksa_numeric_value,
                invented_window_minutes=invented_window_minutes,
                claim_sqs_live_conditioned=claim_sqs_live_conditioned,
            )
        )


@dataclass(frozen=True, slots=True)
class ShakedownEvidence:
    """Assembled Layer-2 proof for the human signature — not performance."""

    binding_identity: str
    shakedown_role: AccountRole
    exercises_run: tuple[str, ...]
    layer2: Layer2Result
    window_settings: ResolvedWindowSettings
    effect_matrix: CompiledEffectMatrix
    paper_ledger: BindingVirtualLedger
    kill_line_breached: bool
    reconciliation: ReconciliationReport
    sqs_baseline: SqsBaselineKey
    sqs_live_conditioned: bool
    containment: SeatContainment
    command_path_submitted_live: bool
    venue_client_kind: str
    for_human_signature: bool = True
    is_performance_proof: bool = False
    live_binding_used: bool = False
    invented_ksa_or_soak_numbers: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "binding_identity": self.binding_identity,
                "command_path_submitted_live": self.command_path_submitted_live,
                "exercises_run": self.exercises_run,
                "for_human_signature": self.for_human_signature,
                "invented_ksa_or_soak_numbers": self.invented_ksa_or_soak_numbers,
                "is_performance_proof": self.is_performance_proof,
                "kill_line_breached": self.kill_line_breached,
                "layer2": self.layer2.fp1_identity(),
                "live_binding_used": self.live_binding_used,
                "shakedown_role": self.shakedown_role.value,
                "sqs_live_conditioned": self.sqs_live_conditioned,
                "surface": SHAKEDOWN_SURFACE,
                "venue_client_kind": self.venue_client_kind,
            }
        )


@dataclass(frozen=True, slots=True)
class ShakedownSignaturePage:
    """Layer-3 human-signature payload: Layer-1 proof plus Layer-2 evidence."""

    layer1_checks_run: tuple[str, ...]
    shakedown: ShakedownEvidence
    for_human_signature: bool = True
    is_performance_proof: bool = False

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "for_human_signature": self.for_human_signature,
                "is_performance_proof": self.is_performance_proof,
                "layer1_checks_run": self.layer1_checks_run,
                "shakedown": dict(self.shakedown.as_mapping()),
            }
        )


def assemble_shakedown_signature_page(
    *,
    layer1_checks_run: object,
    shakedown: object,
) -> Result[ShakedownSignaturePage]:
    """Assemble shakedown evidence for the human signature (AD-32 Layer 3)."""
    if not isinstance(shakedown, ShakedownEvidence):
        return invalid(
            "shakedown",
            "the signature page carries ShakedownEvidence",
            given=type(shakedown).__name__,
        )
    if shakedown.is_performance_proof or not shakedown.for_human_signature:
        return refuse_shakedown_as_performance_proof()
    if not isinstance(layer1_checks_run, Sequence) or isinstance(
        layer1_checks_run, (str, bytes)
    ):
        return invalid(
            "layer1_checks_run",
            "the signature page cites the Layer-1 checks that already passed",
            given=type(layer1_checks_run).__name__,
        )
    checks = tuple(str(item) for item in cast("Sequence[object]", layer1_checks_run))
    return Ok(
        ShakedownSignaturePage(
            layer1_checks_run=checks,
            shakedown=shakedown,
            for_human_signature=True,
            is_performance_proof=False,
        )
    )


def run_demo_shakedown(plan: object) -> Result[ShakedownEvidence]:
    """Exercise the technical demo shakedown without a live binding."""
    if not isinstance(plan, ShakedownPlan):
        return invalid(
            "plan",
            "the demo shakedown reads a ShakedownPlan",
            given=type(plan).__name__,
        )
    if plan.shakedown_role is AccountRole.LIVE:
        return policy(
            "shakedown_role",
            "the Layer-2 technical shakedown runs on a demo/paper binding, "
            "never a live one; it proves the machinery works and proves "
            "nothing about edge",
        )
    if plan.shakedown_role not in _ALLOWED_SHAKEDOWN_ROLES:
        return policy(
            "shakedown_role",
            "node shakedown uses role demo or paper-validation; live and "
            "unused paper-benched namespaces are refused",
            given=plan.shakedown_role.value,
        )
    if plan.treat_as_performance_proof:
        return refuse_shakedown_as_performance_proof()
    if plan.soak_duration is not None or plan.ksa_numeric_value is not None:
        return refuse_invented_soak_or_ksa_number(
            soak_duration=repr(plan.soak_duration),
            ksa_numeric_value=repr(plan.ksa_numeric_value),
        )
    if plan.invented_window_minutes is not None:
        return refuse_invented_window_minutes(plan.invented_window_minutes)

    windows = _exercise_windows(plan)
    if is_refusal(windows):
        return windows
    effects = _exercise_protection_effects(plan)
    if is_refusal(effects):
        return effects
    ledger = _exercise_paper_ledger(plan)
    if is_refusal(ledger):
        return ledger
    kill = _exercise_kill_line(plan)
    if is_refusal(kill):
        return kill
    recon = _exercise_reconciliation(plan)
    if is_refusal(recon):
        return recon
    sqs = _exercise_sqs_baseline(plan)
    if is_refusal(sqs):
        return sqs
    containment = _exercise_callback_containment(plan)
    if is_refusal(containment):
        return containment
    command = _exercise_command_path_dry_run(plan)
    if is_refusal(command):
        return command

    layer2 = run_layer2_shakedown(
        plan.binding_identity,
        plan.shakedown_role,
        plan.live_path_rung_baseline_present,
        plan.sensor_baselines_present,
    )
    if is_refusal(layer2):
        return layer2

    return Ok(
        ShakedownEvidence(
            binding_identity=plan.binding_identity,
            shakedown_role=plan.shakedown_role,
            exercises_run=SHAKEDOWN_EXERCISES,
            layer2=layer2.value,
            window_settings=windows.value,
            effect_matrix=effects.value,
            paper_ledger=ledger.value,
            kill_line_breached=kill.value,
            reconciliation=recon.value,
            sqs_baseline=sqs.value,
            sqs_live_conditioned=False,
            containment=containment.value,
            command_path_submitted_live=False,
            venue_client_kind=command.value,
            for_human_signature=SHAKEDOWN_FOR_HUMAN_SIGNATURE,
            is_performance_proof=SHAKEDOWN_IS_PERFORMANCE_PROOF,
            live_binding_used=False,
            invented_ksa_or_soak_numbers=False,
        )
    )


def _exercise_windows(plan: ShakedownPlan) -> Result[ResolvedWindowSettings]:
    settings = plan.window_settings
    rebuilt = require_resolved_window_settings(
        news_blackout_before=settings.news_blackout_before,
        news_blackout_after=settings.news_blackout_after,
        daily_dead_zone_width=settings.daily_dead_zone_width,
        session_handover_buffer_width=settings.session_handover_buffer_width,
        session_handover_buffer_anchor=settings.session_handover_buffer_anchor,
        news_calendar_max_staleness=settings.news_calendar_max_staleness,
    )
    if is_refusal(rebuilt):
        return rebuilt
    return Ok(rebuilt.value)


def _exercise_protection_effects(plan: ShakedownPlan) -> Result[CompiledEffectMatrix]:
    if not matrix_supplies_no_default_values():
        return refuse_invented_soak_or_ksa_number(matrix_defaults=True)
    compiled = compile_effect_matrix(
        value_status=plan.effect_matrix_value_status,
        cells=plan.effect_matrix_cells,
    )
    if is_refusal(compiled):
        return compiled
    matrix = compiled.value
    if matrix.value_status == VALUE_STATUS_BLANK and (
        not matrix_blocks_role_live(matrix) or not matrix_blocks_soak(matrix)
    ):
        return policy(
            "ksa_effect_matrix",
            "a blank matrix blocks role=live and soak; shakedown must not "
            "invent cell values that would pass those gates (FTR-07)",
        )
    return Ok(matrix)


def _exercise_paper_ledger(plan: ShakedownPlan) -> Result[BindingVirtualLedger]:
    return seed_binding_ledger(
        binding_epoch=plan.ledger_binding_epoch,
        seed=plan.ledger_seed,
        recorded_at=plan.ledger_recorded_at,
        currency=plan.ledger_seed.currency,
    )


def _exercise_kill_line(plan: ShakedownPlan) -> Result[bool]:
    evaluation = evaluate_kill_line(
        binding_scope_ref=plan.binding_identity,
        equity=plan.kill_line_equity,
        kill_line_capital_floor=plan.kill_line_capital_floor,
        evaluated_at=plan.kill_line_evaluated_at,
        loss_floor=plan.kill_line_capital_floor,
    )
    if is_refusal(evaluation):
        return evaluation
    return Ok(evaluation.value.breached)


def _exercise_reconciliation(plan: ShakedownPlan) -> Result[ReconciliationReport]:
    if plan.shakedown_role is AccountRole.LIVE:
        return policy(
            "role",
            "shakedown reconciliation never runs against a live binding",
        )
    return run_reconciliation(
        trigger=ReconciliationTrigger.STARTUP,
        role=plan.shakedown_role,
        lookback_status=LookbackStatus.INSIDE,
        readback_status=ReadbackStatus.PRESENT,
        quantity_pairs=(),
    )


def _exercise_sqs_baseline(plan: ShakedownPlan) -> Result[SqsBaselineKey]:
    if plan.sqs_environment == _LIVE_BASELINE_ENVIRONMENT:
        return policy(
            "sqs_environment",
            "demo shakedown SQS baseline is demo-conditioned; a live-conditioned "
            "baseline is not a Layer-2 shakedown input",
            given=plan.sqs_environment,
        )
    if plan.claim_sqs_live_conditioned:
        return policy(
            "sqs_baseline",
            "a demo-conditioned SQS baseline never satisfies a role=live binding",
            environment=plan.sqs_environment,
            live_environment=_LIVE_BASELINE_ENVIRONMENT,
        )
    if plan.sqs_environment != _DEMO_BASELINE_ENVIRONMENT:
        return invalid(
            "sqs_environment",
            "shakedown SQS baseline environment is demo",
            given=plan.sqs_environment,
            required=_DEMO_BASELINE_ENVIRONMENT,
        )
    return sqs_baseline_key(plan.sqs_venue, plan.sqs_environment, plan.sqs_instrument)


def _exercise_callback_containment(plan: ShakedownPlan) -> Result[SeatContainment]:
    if not FORBIDDEN_SEAT_SURFACE_KEYS:
        return policy(
            "callback_containment",
            "seat callback containment requires the forbidden-surface set",
        )
    return SeatContainment.try_create(
        callback_deadline=plan.callback_deadline,
        memory_ceiling_bytes=plan.memory_ceiling_bytes,
    )


def _exercise_command_path_dry_run(plan: ShakedownPlan) -> Result[str]:
    if plan.dry_run_command.account.role is AccountRole.LIVE:
        return policy(
            "dry_run_command",
            "command-path dry run exercises the path without a live binding",
            given=plan.dry_run_command.account.role.value,
        )
    double = ConformanceDouble.try_create(World.LIVE, plan.dry_run_command.venue_id)
    if is_refusal(double):
        return double
    if double.value.kind is not VenueClientKind.CONFORMANCE:
        return policy(
            "venue_client",
            "command-path dry run binds the conformance double, never a live "
            "cTrader client",
            kind=double.value.kind.value,
        )
    stop = require_venue_resident_protective_stop(
        plan.dry_run_command,
        forms_per_order_type=plan.protective_stop_forms,
    )
    if is_refusal(stop):
        return stop
    klass = admission_class_for(plan.dry_run_command)
    if is_refusal(klass):
        return klass
    return Ok(double.value.kind.value)
