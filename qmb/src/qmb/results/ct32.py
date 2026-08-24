"""CT-32 performance-result minting for a completed QMB run (B-10, Story 14.7).

Wired far enough to fingerprint: the AD-12 label, a fingerprinted population,
a declared period, an ordered unit-kinded measure set, and zero-default
suppression/veto accounting. Chart series and HTML are Epic 19 — they never
enter ``fp1``. Re-running a run id under its resolved config must reproduce
the fingerprint or return a typed refusal (FM-11, DEC-0163).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, cast

from qmf.core.chrono import CalendarIdentity, Interval
from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import (
    EvidenceClass,
    Fingerprint,
    ResultLabel,
    World,
    fingerprint,
)
from qmf.core.identity import AccountRole
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.risk.performance import (
    CT32_CONTRACT_FORMAT_VERSION,
    PerformanceMeasure,
    PerformanceResult,
    PopulationDeclaration,
    ResultPeriod,
    mint_performance_result,
)

from qmb._refuse import clean_token, invalid, policy
from qmb.config.compiler import ResolvedRunConfig

__all__ = [
    "ACCOUNT_ROLE_KEY",
    "CALENDAR_KEY",
    "CHART_SERIES_IN_IDENTITY",
    "CONCURRENCY_IS_SCHEDULING_ONLY",
    "HTML_PAYLOAD",
    "MEASURE_CONTRACT_FORMAT_VERSION",
    "MEASURE_IDENTITIES",
    "QMB_REPLAY_CALENDAR_RULE_SET",
    "QMB_REPLAY_CALENDAR_RULE_SET_VERSION",
    "QMB_REPLAY_CALENDAR_TZDATA",
    "RESULT_CONTRACT",
    "mint_run_performance_result",
    "require_reproduced_fingerprint",
    "result_identity",
]

RESULT_CONTRACT: Final[str] = "CT-32"
CHART_SERIES_IN_IDENTITY: Final[bool] = False
HTML_PAYLOAD: Final[bool] = False
CONCURRENCY_IS_SCHEDULING_ONLY: Final[bool] = True
MEASURE_CONTRACT_FORMAT_VERSION: Final[int] = 1
MEASURE_IDENTITIES: Final[tuple[str, ...]] = (
    "slice_count",
    "data_points_processed",
    "filled_count",
    "resting_count",
)
ACCOUNT_ROLE_KEY: Final[str] = "account_role"
CALENDAR_KEY: Final[str] = "calendar"
QMB_REPLAY_CALENDAR_RULE_SET: Final[str] = "qmb-replay"
QMB_REPLAY_CALENDAR_RULE_SET_VERSION: Final[str] = "v1"
QMB_REPLAY_CALENDAR_TZDATA: Final[str] = "UTC"
_REPLAY_ACCOUNT_ROLE: Final[AccountRole] = AccountRole.DEMO
_REPLAY_EVIDENCE_CLASS: Final[EvidenceClass] = EvidenceClass.PROVISIONAL


def result_identity() -> dict[str, object]:
    """Identity-bearing result-container fields. Package SemVer is omitted."""
    return {
        "chart_series_in_identity": CHART_SERIES_IN_IDENTITY,
        "concurrency_is_scheduling_only": CONCURRENCY_IS_SCHEDULING_ONLY,
        "container": f"{PerformanceResult.__module__}.{PerformanceResult.__qualname__}",
        "contract": RESULT_CONTRACT,
        "format_version": CT32_CONTRACT_FORMAT_VERSION,
        "html_payload": HTML_PAYLOAD,
        "measure_identities": list(MEASURE_IDENTITIES),
    }


def mint_run_performance_result(
    config: object,
    *,
    evidence_range: object,
    stream_order: object,
    slice_count: object,
    filled_count: object,
    resting_count: object,
    data_points_processed: object,
    outcome_identity: object,
) -> Result[PerformanceResult]:
    """Mint the CT-32 artifact of one completed pure ``run()`` (B-10).

    Enough fields for a content fingerprint. Chart series and HTML are not
    emitted. Domain failure is a typed refusal, returned never raised.
    """
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "a CT-32 run result is minted from a resolved run-config; the "
            "config fingerprint is the run-id root (B-3, B-10)",
            given=repr(type(config).__name__),
        )
    if config.world is not World.REPLAY:
        return policy(
            "world",
            "QMB mints CT-32 in world=replay only; a live or simulated result "
            "is not a QMB run artifact and cannot gate live money (B-7, DEC-0162)",
            world=config.world.value,
        )
    if not isinstance(evidence_range, Interval):
        return invalid(
            "evidence_range",
            "the result label's evidence range is the trading interval, never warm-up",
            given=repr(type(evidence_range).__name__),
        )
    if not isinstance(outcome_identity, Mapping):
        return invalid(
            "outcome_identity",
            "the loop outcome identity is a mapping fingerprinted as a CT-32 input",
            given=repr(type(outcome_identity).__name__),
        )
    instruments = _as_tokens("stream_order", stream_order)
    if is_refusal(instruments):
        return instruments
    slices = _as_nonneg_int("slice_count", slice_count)
    if is_refusal(slices):
        return slices
    points = _as_nonneg_int("data_points_processed", data_points_processed)
    if is_refusal(points):
        return points
    filled = _as_nonneg_int("filled_count", filled_count)
    if is_refusal(filled):
        return filled
    resting = _as_nonneg_int("resting_count", resting_count)
    if is_refusal(resting):
        return resting
    producer = fingerprint(result_identity())
    if is_refusal(producer):
        return producer
    outcome_fp = fingerprint(dict(cast("Mapping[str, object]", outcome_identity)))
    if is_refusal(outcome_fp):
        return outcome_fp
    label = ResultLabel.try_create(
        producer.value,
        CT32_CONTRACT_FORMAT_VERSION,
        (config.fingerprint, outcome_fp.value),
        evidence_range,
        _REPLAY_EVIDENCE_CLASS,
        config.world,
    )
    if is_refusal(label):
        return label
    role = _account_role(config)
    if is_refusal(role):
        return role
    cohort = fingerprint(
        {
            "bot": config.bot_fp1.value,
            "class": "qmb-decay-cohort",
            "role": role.value.value,
            "world": config.world.value,
        }
    )
    if is_refusal(cohort):
        return cohort
    population = PopulationDeclaration.try_create(
        config.bot_fp1,
        (_binding_epoch(config),),
        (),
        (role.value,),
        instruments.value,
        cohort.value,
        (),
    )
    if is_refusal(population):
        return population
    calendar = _calendar_from_config(config)
    if is_refusal(calendar):
        return calendar
    period = ResultPeriod.try_create(evidence_range, calendar.value, evidence_range.end)
    if is_refusal(period):
        return period
    measures = _measure_set(
        slice_count=slices.value,
        data_points_processed=points.value,
        filled_count=filled.value,
        resting_count=resting.value,
    )
    if is_refusal(measures):
        return measures
    return mint_performance_result(
        result_label=label.value,
        account_binding_role=role.value,
        population=population.value,
        period=period.value,
        measure_set=measures.value,
        suppression_accounting=(),
        veto_accounting=(),
    )


def require_reproduced_fingerprint(
    expected: object,
    actual: object,
    *,
    run_id: object = None,
) -> Result[Fingerprint]:
    """Refuse a CT-32 fingerprint that does not reproduce under the run id (FM-11).

    Identical inputs under the resolved config must yield the same fingerprint.
    A mismatch is a typed ``policy rejection``, never a silent accept.
    """
    if not isinstance(expected, Fingerprint):
        return invalid(
            "expected_fingerprint",
            "reproduction compares Fingerprint values of the CT-32 artifact",
            given=repr(type(expected).__name__),
        )
    if not isinstance(actual, Fingerprint):
        return invalid(
            "ct32_fingerprint",
            "reproduction compares Fingerprint values of the CT-32 artifact",
            given=repr(type(actual).__name__),
        )
    if expected != actual:
        extra: dict[str, object] = {
            "actual": actual.value,
            "expected": expected.value,
        }
        if isinstance(run_id, Fingerprint):
            extra["run_id"] = run_id.value
        return policy(
            "ct32_fingerprint",
            "re-running a run id under its resolved config must reproduce the "
            "CT-32 fingerprint; a mismatch is a typed refusal (FM-11, DEC-0163)",
            **extra,
        )
    return Ok(actual)


def _binding_epoch(config: ResolvedRunConfig) -> Fingerprint:
    """Cite the replay binding by fingerprint, never by interval (DEC-0155)."""
    if config.binding_fp1 is not None:
        return config.binding_fp1
    if config.replay_binding is not None:
        return config.replay_binding.fingerprint
    return config.fingerprint


def _account_role(config: ResolvedRunConfig) -> Result[AccountRole]:
    raw = config.keys.get(ACCOUNT_ROLE_KEY)
    if raw is None:
        return Ok(_REPLAY_ACCOUNT_ROLE)
    if isinstance(raw, AccountRole):
        return Ok(raw)
    token = clean_token(raw)
    if token is None:
        return invalid(
            ACCOUNT_ROLE_KEY,
            "the account-binding role is an AccountRole; a single result never spans roles",
            given=repr(raw),
            allowed=[member.value for member in AccountRole],
        )
    for member in AccountRole:
        if member.value == token:
            return Ok(member)
    return invalid(
        ACCOUNT_ROLE_KEY,
        "the account-binding role is an AccountRole; a single result never spans roles",
        given=token,
        allowed=[member.value for member in AccountRole],
    )


def _calendar_from_config(config: ResolvedRunConfig) -> Result[CalendarIdentity]:
    raw = config.keys.get(CALENDAR_KEY)
    if raw is None:
        return CalendarIdentity.try_create(
            QMB_REPLAY_CALENDAR_RULE_SET,
            QMB_REPLAY_CALENDAR_RULE_SET_VERSION,
            QMB_REPLAY_CALENDAR_TZDATA,
        )
    if isinstance(raw, CalendarIdentity):
        return Ok(raw)
    if isinstance(raw, Mapping):
        body = cast("Mapping[str, object]", raw)
        return CalendarIdentity.try_create(
            body.get("rule_set"),
            body.get("rule_set_version"),
            body.get("tzdata_version"),
        )
    return invalid(
        CALENDAR_KEY,
        "the result period carries a CalendarIdentity (rule set + version + tzdata)",
        given=repr(type(raw).__name__),
    )


def _measure_set(
    *,
    slice_count: int,
    data_points_processed: int,
    filled_count: int,
    resting_count: int,
) -> Result[tuple[PerformanceMeasure, ...]]:
    counts: dict[str, int] = {
        "slice_count": slice_count,
        "data_points_processed": data_points_processed,
        "filled_count": filled_count,
        "resting_count": resting_count,
    }
    ordered: list[PerformanceMeasure] = []
    for identity in MEASURE_IDENTITIES:
        measure = _count_measure(identity, counts[identity])
        if is_refusal(measure):
            return measure
        ordered.append(measure.value)
    return Ok(tuple(ordered))


def _count_measure(identity: str, count: int) -> Result[PerformanceMeasure]:
    quantity = ExactRational.try_create(count, 1, UnitKind.COUNT)
    if is_refusal(quantity):
        return quantity
    return PerformanceMeasure.try_create(identity, quantity.value, MEASURE_CONTRACT_FORMAT_VERSION)


def _as_nonneg_int(field: str, value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(
            field,
            "a CT-32 count measure is a non-negative int, never money and never a float",
            given=repr(value),
        )
    return Ok(value)


def _as_tokens(field: str, value: object) -> Result[tuple[str, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            field,
            "instruments are the stream-set declaration-order tokens",
            given=repr(type(value).__name__),
        )
    tokens: list[str] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        token = clean_token(item)
        if token is None:
            return invalid(
                field,
                "every instrument token is a non-empty string in declaration order",
                index=index,
                given=repr(item),
            )
        tokens.append(token)
    return Ok(tuple(tokens))
