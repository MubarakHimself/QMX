"""V1 MIS producer inventory, configuration identity, and governed registration.

Story 26.17 ships six rule-based labelers plus fitted ``liquidity_stress_v1``.
``regime_classifier_v1`` is not selected, trained, registered, or bound; Kronos,
HMM, BOCPD, and MS-GARCH remain unauthoritative (DEC-0262, AR-89, FR-072).
Identity is the entire declared configuration (CT-16); AD-24 stays heavy by
default until a live-path rung baseline exists (DEC-0128, DEC-0204).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import (
    Duration,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    Ok,
    Price,
    PriceDelta,
    Result,
    TypedRefusal,
    fingerprint,
    is_refusal,
)

from qmn.mis._refuse import clean_token, invalid, policy
from qmn.mis.signal_snapshot import SQS_PRODUCER_ID, SqsBaselineKey, SqsReading

__all__ = [
    "ALIGNMENT_POLICY_AS_OF",
    "ARITHMETIC_REFERENCE_QMX",
    "DEGRADED_SENSORS_PRODUCER_ID",
    "FEED_STATE_PRODUCER_ID",
    "FITTED_PRODUCER_IDS",
    "GAP_EVENT_PRODUCER_ID",
    "GOVERNED_ROLE",
    "IDENTITY_PRODUCER_ID",
    "LIQUIDITY_STRESS_PRODUCER_ID",
    "MIS_PRODUCER_CONTRACT_FORMAT_VERSION",
    "MIS_PRODUCER_SURFACE",
    "REGIME_CLASSIFIER_PRODUCER_ID",
    "RULE_BASED_PRODUCER_IDS",
    "SPREAD_STATE_PRODUCER_ID",
    "UNAUTHORITATIVE_CANDIDATES",
    "V1_GOVERNED_PRODUCER_IDS",
    "AlignmentPolicy",
    "ConfiguredMisProducer",
    "DeclaredFourBounds",
    "FormulaNature",
    "FrontierFrame",
    "MisFormula",
    "MisProducerCatalog",
    "MisProducerRole",
    "MissingValuePolicy",
    "ProducerEmission",
    "SpreadState",
    "SqsBaselineArtifact",
    "configure_mis_producer",
    "empty_mis_catalog",
    "mis_formula",
    "refuse_trained_regime_classifier",
    "refuse_unauthoritative_candidate",
    "register_mis_producer",
    "v1_formula_catalog",
    "v1_mis_inventory",
]

MIS_PRODUCER_SURFACE: Final[str] = "qmn.mis.catalog"
MIS_PRODUCER_CONTRACT_FORMAT_VERSION: Final[int] = 1
ARITHMETIC_REFERENCE_QMX: Final[str] = "qmx-owned"
ALIGNMENT_POLICY_AS_OF: Final[str] = "as-of"
GOVERNED_ROLE: Final[str] = "governed"

IDENTITY_PRODUCER_ID: Final[str] = "identity"
SPREAD_STATE_PRODUCER_ID: Final[str] = "spread_state"
GAP_EVENT_PRODUCER_ID: Final[str] = "gap_event"
FEED_STATE_PRODUCER_ID: Final[str] = "feed_state"
DEGRADED_SENSORS_PRODUCER_ID: Final[str] = "degraded_sensors"
LIQUIDITY_STRESS_PRODUCER_ID: Final[str] = "liquidity_stress_v1"
REGIME_CLASSIFIER_PRODUCER_ID: Final[str] = "regime_classifier_v1"

RULE_BASED_PRODUCER_IDS: Final[tuple[str, ...]] = (
    IDENTITY_PRODUCER_ID,
    SPREAD_STATE_PRODUCER_ID,
    GAP_EVENT_PRODUCER_ID,
    FEED_STATE_PRODUCER_ID,
    SQS_PRODUCER_ID,
    DEGRADED_SENSORS_PRODUCER_ID,
)
FITTED_PRODUCER_IDS: Final[tuple[str, ...]] = (LIQUIDITY_STRESS_PRODUCER_ID,)
V1_GOVERNED_PRODUCER_IDS: Final[tuple[str, ...]] = (
    *RULE_BASED_PRODUCER_IDS,
    *FITTED_PRODUCER_IDS,
)
UNAUTHORITATIVE_CANDIDATES: Final[frozenset[str]] = frozenset(
    {"kronos", "hmm", "bocpd", "ms-garch"}
)

_FORMULA_IDS: Final[dict[str, str]] = {
    IDENTITY_PRODUCER_ID: "identity_v1",
    SPREAD_STATE_PRODUCER_ID: "spread_state_v1",
    GAP_EVENT_PRODUCER_ID: "gap_event_v1",
    FEED_STATE_PRODUCER_ID: "feed_state_v1",
    SQS_PRODUCER_ID: "spread_quality_sensor_v1",
    DEGRADED_SENSORS_PRODUCER_ID: "degraded_sensors_v1",
    LIQUIDITY_STRESS_PRODUCER_ID: "liquidity_stress_v1",
}

_INPUTS: Final[dict[str, tuple[str, ...]]] = {
    IDENTITY_PRODUCER_ID: ("instrument", "resolution"),
    SPREAD_STATE_PRODUCER_ID: ("spread", "pip", "normal_max", "elevated_max"),
    GAP_EVENT_PRODUCER_ID: (
        "tick_gap",
        "bar_gap_count",
        "max_expected_tick_gap",
        "max_expected_bar_gap_count",
    ),
    FEED_STATE_PRODUCER_ID: ("feed_age", "live_max_age", "degraded_max_age"),
    SQS_PRODUCER_ID: (
        "live_spread",
        "baseline",
        "hard_block_threshold",
        "hysteresis_band",
        "outlier_guard_multiple",
        "sample_cadence",
        "staleness_horizon",
        "decision_freshness_bound",
    ),
    DEGRADED_SENSORS_PRODUCER_ID: ("peer_readiness",),
    LIQUIDITY_STRESS_PRODUCER_ID: (
        "current_spread",
        "current_depth",
        "fit_artifact",
        "spread_stress_quantile",
        "depth_stress_quantile",
    ),
}

_OUTPUTS: Final[dict[str, tuple[str, ...]]] = {
    IDENTITY_PRODUCER_ID: ("identity_key",),
    SPREAD_STATE_PRODUCER_ID: ("spread_state",),
    GAP_EVENT_PRODUCER_ID: ("gap_event",),
    FEED_STATE_PRODUCER_ID: ("feed_state",),
    SQS_PRODUCER_ID: ("sqs_score", "sqs_hard_block"),
    DEGRADED_SENSORS_PRODUCER_ID: ("degraded_sensors",),
    LIQUIDITY_STRESS_PRODUCER_ID: ("liquidity_stress",),
}

_PARAMETER_NAMES: Final[dict[str, tuple[str, ...]]] = {
    IDENTITY_PRODUCER_ID: (),
    SPREAD_STATE_PRODUCER_ID: ("normal_max", "elevated_max"),
    GAP_EVENT_PRODUCER_ID: ("max_expected_tick_gap", "max_expected_bar_gap_count"),
    FEED_STATE_PRODUCER_ID: ("live_max_age", "degraded_max_age"),
    SQS_PRODUCER_ID: (
        "hard_block_threshold",
        "hysteresis_band",
        "outlier_guard_multiple",
        "sample_cadence",
        "staleness_horizon",
        "baseline_statistic",
        "session_window_id",
    ),
    DEGRADED_SENSORS_PRODUCER_ID: (),
    LIQUIDITY_STRESS_PRODUCER_ID: ("spread_stress_quantile", "depth_stress_quantile"),
}


class FormulaNature(StrEnum):
    """Computational nature of a catalogued MIS producer (DEC-0262)."""

    RULE_BASED = "rule-based"
    FITTED = "fitted"
    TRAINED = "trained"


class MisProducerRole(StrEnum):
    """Registration role. V1 binds only GOVERNED inventory (DEC-0204)."""

    GOVERNED = "governed"
    CANDIDATE = "candidate"


class AlignmentPolicy(StrEnum):
    """CT-16 alignment. Only as-of is governed-evidence-legal."""

    AS_OF = "as-of"


class MissingValuePolicy(StrEnum):
    """Declared missing-value policy — never silent fill (CT-16)."""

    MARK_GAP = "mark-gap"
    REFUSE = "refuse"


class SpreadState(StrEnum):
    """Rule-based spread-state vocabulary (CT-MIS-01)."""

    NORMAL = "normal"
    ELEVATED = "elevated"
    EXTREME = "extreme"


@dataclass(frozen=True, slots=True)
class DeclaredFourBounds:
    """AD-24 four-bound declaration surface — not an effective-class verdict."""

    per_update_cost_rung: str
    bounded_state: bool
    window_or_anchor_rule: str
    synchronous_availability: bool

    def fp1_identity(self) -> dict[str, object]:
        return {
            "per_update_cost_rung": self.per_update_cost_rung,
            "bounded_state": self.bounded_state,
            "window_or_anchor_rule": self.window_or_anchor_rule,
            "synchronous_availability": self.synchronous_availability,
        }


@dataclass(frozen=True, slots=True)
class MisFormula:
    """Catalogued formula row — nature, inputs, outputs; no operational values."""

    producer_id: str
    formula_id: str
    version: str
    nature: FormulaNature
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    parameter_names: tuple[str, ...]

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "mis-formula",
            "producer_id": self.producer_id,
            "formula_id": self.formula_id,
            "version": self.version,
            "nature": self.nature.value,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "parameter_names": list(self.parameter_names),
            "format_version": MIS_PRODUCER_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ConfiguredMisProducer:
    """CT-16-shaped configured producer. Identity is the entire configuration."""

    producer_id: str
    formula_id: str
    version: str
    nature: FormulaNature
    contract_format_version: int
    parameters: Mapping[str, object]
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    calendar_requirements: tuple[str, ...]
    alignment_policy: AlignmentPolicy
    missing_value_policy: MissingValuePolicy
    warm_up: int
    supported_modes: tuple[str, ...]
    arithmetic_reference_configuration: str
    declared_budget: DeclaredFourBounds | None = None

    def fp1_identity(self) -> dict[str, object]:
        parameters = {
            name: _parameter_identity(value)
            for name, value in sorted(self.parameters.items(), key=lambda item: item[0])
        }
        body: dict[str, object] = {
            "class": "configured-mis-producer",
            "producer_id": self.producer_id,
            "formula_id": self.formula_id,
            "version": self.version,
            "nature": self.nature.value,
            "contract_format_version": self.contract_format_version,
            "parameters": parameters,
            "inputs": list(self.inputs),
            "outputs": list(self.outputs),
            "calendar_requirements": list(self.calendar_requirements),
            "alignment_policy": self.alignment_policy.value,
            "missing_value_policy": self.missing_value_policy.value,
            "warm_up": self.warm_up,
            "supported_modes": list(self.supported_modes),
            "arithmetic_reference_configuration": self.arithmetic_reference_configuration,
            "format_version": MIS_PRODUCER_CONTRACT_FORMAT_VERSION,
        }
        if self.declared_budget is not None:
            body["declared_budget"] = self.declared_budget.fp1_identity()
        return body

    def fingerprint(self) -> Result[Fingerprint]:
        return fingerprint(self.fp1_identity())


@dataclass(frozen=True, slots=True)
class MisProducerCatalog:
    """Immutable governed-role catalog. Candidates register on the shadow seam."""

    producers: Mapping[str, ConfiguredMisProducer]

    def __post_init__(self) -> None:
        object.__setattr__(self, "producers", MappingProxyType(dict(self.producers)))

    def governed_ids(self) -> tuple[str, ...]:
        return tuple(sorted(self.producers))


@dataclass(frozen=True, slots=True)
class SqsBaselineArtifact:
    """Fingerprinted SQS baseline input — refit does not fork producer identity."""

    key: SqsBaselineKey
    average_spread: PriceDelta
    session_window_id: str
    statistic: str
    refit_series_id: str
    refit_policy_fp: Fingerprint
    dispersion: PriceDelta | None = None

    def fp1_identity(self) -> dict[str, object]:
        body: dict[str, object] = {
            "class": "sqs-baseline-artifact",
            "key": self.key.fp1_identity(),
            "average_spread": self.average_spread.fp1_identity(),
            "session_window_id": self.session_window_id,
            "statistic": self.statistic,
            "refit_series_id": self.refit_series_id,
            "refit_policy_fp": self.refit_policy_fp.value,
        }
        if self.dispersion is not None:
            body["dispersion"] = self.dispersion.fp1_identity()
        return body


@dataclass(frozen=True, slots=True)
class FrontierFrame:
    """As-of observation bundle at the slice frontier — never wall-now."""

    frontier_instant: Instant
    instrument: Instrument
    environment: str
    resolution: str
    known_at: Instant | None = None
    bid: Price | None = None
    ask: Price | None = None
    spread: PriceDelta | None = None
    pip: PriceDelta | None = None
    last_tick_at: Instant | None = None
    bar_gap_count: int | None = None
    sample_cadence: str | None = None
    previous_sqs_hard_block: bool | None = None
    current_depth: int | None = None
    spread_points: ExactRational | None = None
    current_spread_ticks: int | None = None
    peer_emissions: tuple[ProducerEmission, ...] = ()


@dataclass(frozen=True, slots=True)
class ProducerEmission:
    """One per-instant producer output folded into a signal-snapshot slot."""

    producer_id: str
    readiness: object
    labeler_version: str
    marker_detail: str | None = None
    sqs: SqsReading | None = None
    spread_state: SpreadState | None = None
    gap_event: bool | None = None
    feed_state: object | None = None
    liquidity_stress: bool | None = None
    identity_key: str | None = None
    degraded_sensors: tuple[str, ...] | None = None


def v1_mis_inventory() -> dict[str, object]:
    """The ratified starting inventory (DEC-0262) — no trained model bound."""
    return {
        "rule_based": list(RULE_BASED_PRODUCER_IDS),
        "fitted": list(FITTED_PRODUCER_IDS),
        "trained_unbound": [REGIME_CLASSIFIER_PRODUCER_ID],
        "unauthoritative_candidates": sorted(UNAUTHORITATIVE_CANDIDATES),
        "governed_v1": list(V1_GOVERNED_PRODUCER_IDS),
        "regime_classifier_bound": False,
        "trained_model_selected": False,
    }


def v1_formula_catalog() -> tuple[MisFormula, ...]:
    """The seven V1 formulas. ``regime_classifier_v1`` is intentionally absent."""
    rows: list[MisFormula] = []
    for producer_id in V1_GOVERNED_PRODUCER_IDS:
        nature = (
            FormulaNature.FITTED if producer_id in FITTED_PRODUCER_IDS else FormulaNature.RULE_BASED
        )
        rows.append(
            MisFormula(
                producer_id=producer_id,
                formula_id=_FORMULA_IDS[producer_id],
                version="v1",
                nature=nature,
                inputs=_INPUTS[producer_id],
                outputs=_OUTPUTS[producer_id],
                parameter_names=_PARAMETER_NAMES[producer_id],
            )
        )
    return tuple(rows)


def mis_formula(producer_id: object) -> Result[MisFormula]:
    """Look up one V1 formula. Trained and unauthoritative ids refuse."""
    token = clean_token(producer_id)
    if token is None:
        return invalid(
            "producer_id",
            "a MIS formula names a non-empty producer id",
            given=repr(producer_id),
        )
    trained = refuse_trained_regime_classifier(token)
    if is_refusal(trained):
        return trained
    unauth = refuse_unauthoritative_candidate(token)
    if is_refusal(unauth):
        return unauth
    for row in v1_formula_catalog():
        if token in {row.producer_id, row.formula_id}:
            return Ok(row)
    return invalid(
        "producer_id",
        "unknown MIS producer; V1 ships the six rule-based labelers plus liquidity_stress_v1",
        given=token,
        allowed=list(V1_GOVERNED_PRODUCER_IDS),
    )


def configure_mis_producer(
    producer_id: object,
    *,
    parameters: object = (),
    calendar_requirements: object = (),
    alignment_policy: object = AlignmentPolicy.AS_OF,
    missing_value_policy: object = MissingValuePolicy.MARK_GAP,
    warm_up: object = 0,
    supported_modes: object = ("streaming",),
    declared_budget: object = None,
) -> Result[ConfiguredMisProducer]:
    """Mint a configured producer. Identity spans the entire declaration (CT-16)."""
    formula = mis_formula(producer_id)
    if is_refusal(formula):
        return formula
    row = formula.value
    alignment = _coerce_alignment(alignment_policy)
    if isinstance(alignment, TypedRefusal):
        return alignment
    missing = _coerce_missing(missing_value_policy)
    if isinstance(missing, TypedRefusal):
        return missing
    if not isinstance(warm_up, int) or isinstance(warm_up, bool) or warm_up < 0:
        return invalid(
            "warm_up",
            "warm-up is a non-negative integer count of input observations",
            given=repr(warm_up),
        )
    modes = _coerce_token_tuple(supported_modes, "supported_modes")
    if isinstance(modes, TypedRefusal):
        return modes
    if not modes:
        return invalid("supported_modes", "a configuration declares at least one mode")
    calendars = _coerce_token_tuple(calendar_requirements, "calendar_requirements")
    if isinstance(calendars, TypedRefusal):
        return calendars
    params = _coerce_parameters(parameters, row.parameter_names)
    if isinstance(params, TypedRefusal):
        return params
    budget = _coerce_budget(declared_budget)
    if isinstance(budget, TypedRefusal):
        return budget
    return Ok(
        ConfiguredMisProducer(
            producer_id=row.producer_id,
            formula_id=row.formula_id,
            version=row.version,
            nature=row.nature,
            contract_format_version=MIS_PRODUCER_CONTRACT_FORMAT_VERSION,
            parameters=MappingProxyType(params),
            inputs=row.inputs,
            outputs=row.outputs,
            calendar_requirements=calendars,
            alignment_policy=alignment,
            missing_value_policy=missing,
            warm_up=warm_up,
            supported_modes=modes,
            arithmetic_reference_configuration=ARITHMETIC_REFERENCE_QMX,
            declared_budget=budget,
        )
    )


def empty_mis_catalog() -> MisProducerCatalog:
    """An empty governed catalog."""
    return MisProducerCatalog(producers={})


def register_mis_producer(
    catalog: object,
    producer: object,
    *,
    role: object = MisProducerRole.GOVERNED,
) -> Result[MisProducerCatalog]:
    """Register a configured producer into the governed catalog.

    Trained ``regime_classifier_v1`` and unauthoritative recovered names refuse.
    Duplicate producer ids refuse. Candidate-role registration belongs on the
    shadow seam (``register_shadow_candidate``), never this catalog.
    """
    if not isinstance(catalog, MisProducerCatalog):
        return invalid(
            "catalog",
            "producers register onto a MisProducerCatalog",
            given=type(catalog).__name__,
        )
    if not isinstance(producer, ConfiguredMisProducer):
        return invalid(
            "producer",
            "registration takes a ConfiguredMisProducer",
            given=type(producer).__name__,
        )
    resolved_role = _coerce_role(role)
    if isinstance(resolved_role, TypedRefusal):
        return resolved_role
    if resolved_role is not MisProducerRole.GOVERNED:
        return policy(
            "role",
            "governed registration takes role=governed; candidate labelers "
            "register through register_shadow_candidate on the shadow seam",
            role=resolved_role.value,
        )
    trained = refuse_trained_regime_classifier(producer.producer_id)
    if is_refusal(trained):
        return trained
    trained_formula = refuse_trained_regime_classifier(producer.formula_id)
    if is_refusal(trained_formula):
        return trained_formula
    unauth = refuse_unauthoritative_candidate(producer.producer_id)
    if is_refusal(unauth):
        return unauth
    if producer.producer_id not in V1_GOVERNED_PRODUCER_IDS:
        return policy(
            "producer_id",
            "V1 governed registration is the six rule-based labelers plus liquidity_stress_v1",
            producer_id=producer.producer_id,
            allowed=list(V1_GOVERNED_PRODUCER_IDS),
        )
    if producer.nature is FormulaNature.TRAINED:
        trained_nature = refuse_trained_regime_classifier(producer.producer_id)
        if isinstance(trained_nature, TypedRefusal):
            return trained_nature
        return policy(
            "nature",
            "regime_classifier_v1 is not selected, trained, registered, or bound "
            "in V1; it remains the MIS training design story (DEC-0262, GAP-0051)",
            producer_id=producer.producer_id,
        )
    if producer.producer_id in catalog.producers:
        return invalid(
            "producer_id",
            "exactly one governed registration per producer id",
            producer_id=producer.producer_id,
        )
    next_map = dict(catalog.producers)
    next_map[producer.producer_id] = producer
    return Ok(MisProducerCatalog(producers=next_map))


def refuse_trained_regime_classifier(name: object) -> Result[None]:
    """No trained model is selected, trained, registered, or bound (DEC-0262)."""
    token = clean_token(name)
    if token is None:
        return Ok(None)
    lowered = token.lower().replace("-", "_")
    if lowered in {REGIME_CLASSIFIER_PRODUCER_ID, "regime_classifier"}:
        return policy(
            "producer_id",
            "regime_classifier_v1 is not selected, trained, registered, or bound "
            "in V1; it remains the MIS training design story (DEC-0262, GAP-0051)",
            producer_id=token,
        )
    return Ok(None)


def refuse_unauthoritative_candidate(name: object) -> Result[None]:
    """Kronos/HMM/BOCPD/MS-GARCH carry no authority without fresh ratification."""
    token = clean_token(name)
    if token is None:
        return Ok(None)
    lowered = token.lower().replace("-", "_")
    normalized = {name.replace("-", "_") for name in UNAUTHORITATIVE_CANDIDATES}
    if lowered in normalized:
        return policy(
            "producer_id",
            "recovered candidates Kronos, HMM, BOCPD, and MS-GARCH remain "
            "unauthoritative until fresh ratification (DEC-0262)",
            producer_id=token,
            unauthoritative=sorted(UNAUTHORITATIVE_CANDIDATES),
        )
    return Ok(None)


def _parameter_identity(value: object) -> object:
    if isinstance(value, Fingerprint):
        return value.value
    if isinstance(value, (ExactRational, Duration, SqsBaselineKey)):
        return value.fp1_identity()
    return value


def _coerce_alignment(value: object) -> AlignmentPolicy | TypedRefusal:
    if isinstance(value, AlignmentPolicy):
        if value is AlignmentPolicy.AS_OF:
            return value
        return policy(
            "alignment_policy",
            "only as-of alignment is governed-evidence-legal; forward-fill or "
            "interpolation across the evaluation instant is a policy rejection",
            given=value.value,
        )
    token = clean_token(value)
    if token == ALIGNMENT_POLICY_AS_OF:
        return AlignmentPolicy.AS_OF
    if token in {"forward-fill", "interpolate", "interpolation"}:
        return policy(
            "alignment_policy",
            "only as-of alignment is governed-evidence-legal; forward-fill or "
            "interpolation across the evaluation instant is a policy rejection",
            given=token,
        )
    return invalid(
        "alignment_policy",
        "alignment_policy is as-of",
        given=repr(value),
    )


def _coerce_missing(value: object) -> MissingValuePolicy | TypedRefusal:
    if isinstance(value, MissingValuePolicy):
        return value
    token = clean_token(value)
    if token is None:
        return invalid(
            "missing_value_policy",
            "missing_value_policy is mark-gap or refuse",
            given=repr(value),
        )
    try:
        return MissingValuePolicy(token)
    except ValueError:
        return invalid(
            "missing_value_policy",
            "missing_value_policy is mark-gap or refuse; silent fill is prohibited",
            given=token,
        )


def _coerce_role(value: object) -> MisProducerRole | TypedRefusal:
    if isinstance(value, MisProducerRole):
        return value
    token = clean_token(value)
    if token is None:
        return invalid("role", "role is governed or candidate", given=repr(value))
    try:
        return MisProducerRole(token)
    except ValueError:
        return invalid("role", "role is governed or candidate", given=token)


def _coerce_token_tuple(value: object, field: str) -> tuple[str, ...] | TypedRefusal:
    if value is None:
        return ()
    if isinstance(value, str):
        token = clean_token(value)
        if token is None:
            return invalid(field, f"{field} tokens are non-empty strings", given=repr(value))
        return (token,)
    if isinstance(value, (bytes, bytearray)) or not isinstance(value, Sequence):
        return invalid(field, f"{field} is a sequence of non-empty tokens", given=repr(value))
    items: list[str] = []
    for item in cast("Sequence[object]", value):
        token = clean_token(item)
        if token is None:
            return invalid(field, f"{field} tokens are non-empty strings", given=repr(item))
        items.append(token)
    return tuple(items)


def _coerce_parameters(
    value: object,
    required_names: Sequence[str],
) -> dict[str, object] | TypedRefusal:
    if value is None or value == ():
        mapping: Mapping[str, object] = {}
    elif isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
    else:
        return invalid(
            "parameters",
            "parameters is a name->value mapping of declared exact values",
            given=type(value).__name__,
        )
    out: dict[str, object] = {}
    for raw_name, raw_value in mapping.items():
        name = clean_token(raw_name)
        if name is None:
            return invalid(
                "parameters",
                "parameter names are non-empty tokens",
                given=repr(raw_name),
            )
        checked = _coerce_parameter_value(name, raw_value)
        if isinstance(checked, TypedRefusal):
            return checked
        out[name] = checked
    missing = [name for name in required_names if name not in out]
    if missing:
        return invalid(
            "parameters",
            "declared producer parameters are mandatory; the node never invents "
            "operational defaults (DEC-0157, FTR-07)",
            missing=missing,
        )
    return out


def _coerce_parameter_value(name: str, value: object) -> object | TypedRefusal:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        token = clean_token(value)
        if token is None:
            return invalid(name, "a string parameter is a non-empty token", given=repr(value))
        return token
    if isinstance(value, (ExactRational, Duration, Fingerprint, SqsBaselineKey)):
        return value
    if isinstance(value, float):
        return invalid(
            name,
            "binary float is refused in producer parameters; use ExactRational "
            "or a Duration (FM-1)",
            given=repr(value),
        )
    return invalid(
        name,
        "a producer parameter is an ExactRational, Duration, int, bool, or token",
        given=type(value).__name__,
    )


def _coerce_budget(value: object) -> DeclaredFourBounds | TypedRefusal | None:
    if value is None:
        return None
    if isinstance(value, DeclaredFourBounds):
        return value
    return invalid(
        "declared_budget",
        "a light claim carries DeclaredFourBounds; omit it for heavy-by-default (AD-24)",
        given=type(value).__name__,
    )
