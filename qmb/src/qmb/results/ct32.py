"""CT-32 performance-result minting and results/ assembly (B-10, Story 19.1).

A completed pure ``run()`` return is assembled into exactly one CT-32
container in the run output directory. That container IS the canonical
artifact — no second report JSON. ``fp1`` is label-derived via qmf-core
only; float bytes never enter identity. Chart series and HTML stay Epic 19
and never enter ``fp1``. Re-running a run id under its resolved config must
reproduce the fingerprint or return a typed refusal (FM-11, DEC-0163).
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Final, cast

from qmf.core.chrono import CalendarIdentity, Instant, Interval
from qmf.core.exact import Money
from qmf.core.fingerprint import (
    EvidenceClass,
    Fingerprint,
    ResultLabel,
    World,
    canonical_bytes,
    fingerprint,
)
from qmf.core.identity import AccountRole
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal
from qmf.risk.numeraire import V1_NUMERAIRE
from qmf.risk.performance import (
    CT32_CONTRACT_FORMAT_VERSION,
    PerformanceResult,
    PopulationDeclaration,
    ResultPeriod,
    mint_performance_result,
)

from qmb._refuse import clean_token, invalid, policy, storage
from qmb.config.compiler import ResolvedRunConfig
from qmb.config.replay import STARTING_CAPITAL_KEY, coerce_starting_capital
from qmb.execution.fidelity import FidelityIdentity, RunFidelity
from qmb.execution.financing import (
    FINANCING_CALIBRATION_KEY,
    financing_calibration_fingerprint,
)
from qmb.execution.ports import (
    CLAIMS_EDGE,
    COMPOSITION_VERSION,
    SPENDS_SPLIT_BUDGET,
    TAINT_OPTIMISTIC,
    refuse_optimistic_edge_claim,
)
from qmb.execution.spread import SPREAD_CALIBRATION_KEY, spread_calibration_fingerprint
from qmb.results.accounting import (
    SUPPRESSION_REASON_CLASSES,
    TALLY_FIELD_GROUP,
    TALLY_UNIT_KIND,
    VETO_DOOR_IDENTITIES,
    assemble_suppression_and_veto_accounting,
)
from qmb.results.measures import (
    MEASURE_ARITHMETIC,
    MEASURE_CONTRACT_FORMAT_VERSION,
    MEASURE_IDENTITIES,
    METRIC_CONTRACT_FORMAT_VERSIONS,
    assemble_v1_measure_set,
)

__all__ = [
    "ACCOUNT_ROLE_KEY",
    "CALENDAR_KEY",
    "CHART_SERIES_IN_IDENTITY",
    "CONCURRENCY_IS_SCHEDULING_ONLY",
    "CT32_ARTIFACT_NAME",
    "CT32_ARTIFACT_RELATIVE_PATH",
    "DATA_FINGERPRINT_KEY",
    "FIDELITY_KEY",
    "HTML_PAYLOAD",
    "MEASURE_ARITHMETIC",
    "MEASURE_CONTRACT_FORMAT_VERSION",
    "MEASURE_IDENTITIES",
    "METRIC_CONTRACT_FORMAT_VERSIONS",
    "QMB_REPLAY_CALENDAR_RULE_SET",
    "QMB_REPLAY_CALENDAR_RULE_SET_VERSION",
    "QMB_REPLAY_CALENDAR_TZDATA",
    "REGISTRY_AS_OF_KEY",
    "RESULTS_DIR_NAME",
    "RESULT_CONTRACT",
    "RNG_PROVENANCE_KEY",
    "SPLIT_FINGERPRINT_KEY",
    "SUPPRESSION_REASON_CLASSES",
    "TALLY_FIELD_GROUP",
    "TALLY_UNIT_KIND",
    "VETO_DOOR_IDENTITIES",
    "assemble_run_performance_result",
    "assemble_suppression_and_veto_accounting",
    "ct32_artifact_path",
    "mint_run_performance_result",
    "require_reproduced_fingerprint",
    "result_identity",
]

RESULT_CONTRACT: Final[str] = "CT-32"
CHART_SERIES_IN_IDENTITY: Final[bool] = False
HTML_PAYLOAD: Final[bool] = False
CONCURRENCY_IS_SCHEDULING_ONLY: Final[bool] = True
ACCOUNT_ROLE_KEY: Final[str] = "account_role"
CALENDAR_KEY: Final[str] = "calendar"
REGISTRY_AS_OF_KEY: Final[str] = "registry_as_of"
DATA_FINGERPRINT_KEY: Final[str] = "data_fingerprint"
SPLIT_FINGERPRINT_KEY: Final[str] = "split_fingerprint"
FIDELITY_KEY: Final[str] = "fidelity"
RNG_PROVENANCE_KEY: Final[str] = "rng_provenance"
RESULTS_DIR_NAME: Final[str] = "results"
CT32_ARTIFACT_NAME: Final[str] = "ct-32.json"
CT32_ARTIFACT_RELATIVE_PATH: Final[str] = f"{RESULTS_DIR_NAME}/{CT32_ARTIFACT_NAME}"
QMB_REPLAY_CALENDAR_RULE_SET: Final[str] = "qmb-replay"
QMB_REPLAY_CALENDAR_RULE_SET_VERSION: Final[str] = "v1"
QMB_REPLAY_CALENDAR_TZDATA: Final[str] = "UTC"
_REPLAY_ACCOUNT_ROLE: Final[AccountRole] = AccountRole.DEMO
_REPLAY_EVIDENCE_CLASS: Final[EvidenceClass] = EvidenceClass.PROVISIONAL
_REGISTRY_AS_OF_CLASS: Final[str] = "registry-as-of"
_RNG_PROVENANCE_CLASS: Final[str] = "rng-provenance"


def result_identity() -> dict[str, object]:
    """Identity-bearing result-container fields. Package SemVer is omitted."""
    return {
        "chart_series_in_identity": CHART_SERIES_IN_IDENTITY,
        "claims_edge": CLAIMS_EDGE,
        "concurrency_is_scheduling_only": CONCURRENCY_IS_SCHEDULING_ONLY,
        "container": f"{PerformanceResult.__module__}.{PerformanceResult.__qualname__}",
        "contract": RESULT_CONTRACT,
        "format_version": CT32_CONTRACT_FORMAT_VERSION,
        "html_payload": HTML_PAYLOAD,
        "measure_arithmetic": dict(MEASURE_ARITHMETIC),
        "measure_identities": list(MEASURE_IDENTITIES),
        "metric_contract_format_versions": [
            {
                "measure_identity": identity,
                "version": METRIC_CONTRACT_FORMAT_VERSIONS[identity],
            }
            for identity in MEASURE_IDENTITIES
        ],
        "spends_split_budget": SPENDS_SPLIT_BUDGET,
        "suppression_reason_classes": list(SUPPRESSION_REASON_CLASSES),
        "tally_field_group": TALLY_FIELD_GROUP,
        "tally_unit_kind": TALLY_UNIT_KIND.value,
        "veto_door_identities": list(VETO_DOOR_IDENTITIES),
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
    trades: object = (),
    equity_curve: object = (),
    starting_capital: object = None,
    journal_events: object = (),
) -> Result[PerformanceResult]:
    """Mint the CT-32 artifact of one completed pure ``run()`` (B-10).

    Enough fields for a content fingerprint. Chart series and HTML are not
    emitted. Domain failure is a typed refusal, returned never raised. A
    multi-role span is a policy rejection and mints nothing.
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
    for field, raw in (
        ("slice_count", slice_count),
        ("data_points_processed", data_points_processed),
        ("filled_count", filled_count),
        ("resting_count", resting_count),
    ):
        counted = _as_nonneg_int(field, raw)
        if is_refusal(counted):
            return counted
    role = _account_role(config)
    if is_refusal(role):
        return role
    claimed = _refuse_edge_claim(config)
    if is_refusal(claimed):
        return claimed
    producer = fingerprint(result_identity())
    if is_refusal(producer):
        return producer
    outcome_fp = fingerprint(dict(cast("Mapping[str, object]", outcome_identity)))
    if is_refusal(outcome_fp):
        return outcome_fp
    inputs = _collect_input_fingerprints(config, outcome_fp.value)
    if is_refusal(inputs):
        return inputs
    label = ResultLabel.try_create(
        producer.value,
        CT32_CONTRACT_FORMAT_VERSION,
        inputs.value,
        evidence_range,
        _REPLAY_EVIDENCE_CLASS,
        config.world,
    )
    if is_refusal(label):
        return label
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
    capital = _starting_capital(config, starting_capital)
    if is_refusal(capital):
        return capital
    measures = assemble_v1_measure_set(
        starting_capital=capital.value,
        period=evidence_range,
        trades=trades,
        equity_curve=equity_curve,
    )
    if is_refusal(measures):
        return measures
    tallies = assemble_suppression_and_veto_accounting(journal_events, world=config.world)
    if is_refusal(tallies):
        return tallies
    return mint_performance_result(
        result_label=label.value,
        account_binding_role=role.value,
        population=population.value,
        period=period.value,
        measure_set=measures.value,
        suppression_accounting=tallies.value[0],
        veto_accounting=tallies.value[1],
    )


def assemble_run_performance_result(
    outcome: object,
    *,
    output_dir: object,
) -> Result[Fingerprint]:
    """Write exactly one CT-32 container into the run output directory (B-10).

    Consumes a completed pure ``run()`` return (or the minted
    :class:`~qmf.risk.performance.PerformanceResult`). Returns the artifact
    ``fp1`` computed only by qmf-core. A typed refusal writes nothing — no
    second report JSON is minted.
    """
    if isinstance(outcome, TypedRefusal):
        return outcome
    artifact = _as_performance_result(outcome)
    if is_refusal(artifact):
        return artifact
    claimed = refuse_optimistic_edge_claim()
    if is_refusal(claimed):
        return claimed
    identity = artifact.value.fp1_identity()
    if "chart" in identity or "html" in identity:
        return policy(
            "result_label",
            "chart series and HTML never enter CT-32 identity (B-10, DEC-0163)",
        )
    stamped = fingerprint(identity)
    if is_refusal(stamped):
        return stamped
    derived = artifact.value.fingerprint()
    if is_refusal(derived):
        return derived
    if derived.value != stamped.value:
        return policy(
            "ct32_fingerprint",
            "CT-32 fp1 is label-derived via qmf-core only; a mismatch is a typed "
            "refusal (R-RPT-6, AR-14, DEC-0163)",
            actual=derived.value.value,
            expected=stamped.value.value,
        )
    payload = canonical_bytes(identity)
    if is_refusal(payload):
        return payload
    root = _as_existing_output_dir(output_dir)
    if is_refusal(root):
        return root
    written = _write_ct32_bytes(root.value, payload.value)
    if is_refusal(written):
        return written
    return stamped


def ct32_artifact_path(output_dir: object) -> Result[Path]:
    """``results/ct-32.json`` under the run output directory."""
    root = _as_output_path(output_dir)
    if is_refusal(root):
        return root
    return Ok(root.value / RESULTS_DIR_NAME / CT32_ARTIFACT_NAME)


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
    if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
        parsed: list[AccountRole] = []
        for index, item in enumerate(cast("Sequence[object]", raw)):
            resolved = _one_account_role(item, index=index)
            if is_refusal(resolved):
                return resolved
            if resolved.value not in parsed:
                parsed.append(resolved.value)
        if len(parsed) > 1:
            return policy(
                ACCOUNT_ROLE_KEY,
                "a single result may never span account roles; a multi-role "
                "result is a policy rejection (R-RPT-7, DEC-0155)",
                roles=[member.value for member in parsed],
            )
        if len(parsed) == 1:
            return Ok(parsed[0])
        return invalid(
            ACCOUNT_ROLE_KEY,
            "the account-binding role is an AccountRole; a single result never spans roles",
            given=repr(cast("object", raw)),
            allowed=[member.value for member in AccountRole],
        )
    return _one_account_role(raw)


def _one_account_role(raw: object, *, index: int | None = None) -> Result[AccountRole]:
    if isinstance(raw, AccountRole):
        return Ok(raw)
    token = clean_token(raw)
    extra: dict[str, object] = {}
    if index is not None:
        extra["index"] = index
    if token is None:
        return invalid(
            ACCOUNT_ROLE_KEY,
            "the account-binding role is an AccountRole; a single result never spans roles",
            given=repr(raw),
            allowed=[member.value for member in AccountRole],
            **extra,
        )
    for member in AccountRole:
        if member.value == token:
            return Ok(member)
    return invalid(
        ACCOUNT_ROLE_KEY,
        "the account-binding role is an AccountRole; a single result never spans roles",
        given=token,
        allowed=[member.value for member in AccountRole],
        **extra,
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


def _starting_capital(config: ResolvedRunConfig, explicit: object) -> Result[Money]:
    if explicit is not None:
        if isinstance(explicit, Money):
            return Ok(explicit)
        return coerce_starting_capital(explicit)
    if config.replay_binding is not None:
        return Ok(config.replay_binding.starting_capital)
    raw = config.keys.get(STARTING_CAPITAL_KEY)
    if raw is not None:
        return coerce_starting_capital(raw)
    return Money.try_create(0, V1_NUMERAIRE, 2)


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


def _collect_input_fingerprints(
    config: ResolvedRunConfig,
    outcome_fp: Fingerprint,
) -> Result[tuple[Fingerprint, ...]]:
    """AD-12 input fingerprints plus the AR-59 stamps (B-10, B-13).

    Order is identity-bearing. The resolved-config fingerprint is the run-id
    root and is always first. Optional stamps are omitted when absent. RNG
    provenance is present only when the run is stochastic.
    """
    inputs: list[Fingerprint] = [config.fingerprint, outcome_fp]
    registry = _registry_as_of_input(config)
    if is_refusal(registry):
        return registry
    if registry.value is not None:
        inputs.append(registry.value)
    data_fp = _optional_fingerprint(config.keys.get(DATA_FINGERPRINT_KEY), DATA_FINGERPRINT_KEY)
    if is_refusal(data_fp):
        return data_fp
    if data_fp.value is not None:
        inputs.append(data_fp.value)
    split_fp = _split_input(config)
    if is_refusal(split_fp):
        return split_fp
    if split_fp.value is not None:
        inputs.append(split_fp.value)
    fidelity_fp = _fidelity_input(config)
    if is_refusal(fidelity_fp):
        return fidelity_fp
    if fidelity_fp.value is not None:
        inputs.append(fidelity_fp.value)
    rng_fp = _rng_input(config)
    if is_refusal(rng_fp):
        return rng_fp
    if rng_fp.value is not None:
        inputs.append(rng_fp.value)
    cited = config.keys.get(SPREAD_CALIBRATION_KEY)
    if cited is not None:
        calibration_fp = spread_calibration_fingerprint(cited)
        if is_refusal(calibration_fp):
            return calibration_fp
        inputs.append(calibration_fp.value)
    cited_financing = config.keys.get(FINANCING_CALIBRATION_KEY)
    if cited_financing is not None:
        financing_fp = financing_calibration_fingerprint(cited_financing)
        if is_refusal(financing_fp):
            return financing_fp
        inputs.append(financing_fp.value)
    return Ok(tuple(inputs))


def _registry_as_of_input(config: ResolvedRunConfig) -> Result[Fingerprint | None]:
    raw = config.keys.get(REGISTRY_AS_OF_KEY)
    if raw is None:
        return Ok(None)
    if isinstance(raw, Fingerprint):
        return _held(raw)
    if isinstance(raw, Instant):
        return _present(
            fingerprint(
                {
                    "class": _REGISTRY_AS_OF_CLASS,
                    "registry_as_of": raw.fp1_identity(),
                }
            )
        )
    if isinstance(raw, int) and not isinstance(raw, bool):
        instant = Instant.try_create(raw)
        if is_refusal(instant):
            return instant
        return _present(
            fingerprint(
                {
                    "class": _REGISTRY_AS_OF_CLASS,
                    "registry_as_of": instant.value.fp1_identity(),
                }
            )
        )
    token = clean_token(raw)
    if token is not None:
        parsed = Fingerprint.try_create(token)
        if not is_refusal(parsed):
            return _held(parsed.value)
    if not isinstance(raw, Mapping):
        return invalid(
            REGISTRY_AS_OF_KEY,
            "registry_as_of is an Instant, a set fingerprint, or a mapping of "
            "the as-of instant plus set fingerprint (B-15)",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    content: dict[str, object] = {"class": _REGISTRY_AS_OF_CLASS}
    instant_raw = body.get("registry_as_of", body.get("value_ns"))
    if instant_raw is not None:
        if isinstance(instant_raw, Instant):
            content["registry_as_of"] = instant_raw.fp1_identity()
        elif isinstance(instant_raw, Mapping):
            nested = cast("Mapping[str, object]", instant_raw)
            created = Instant.try_create(nested.get("value_ns"))
            if is_refusal(created):
                return created
            content["registry_as_of"] = created.value.fp1_identity()
        else:
            created = Instant.try_create(instant_raw)
            if is_refusal(created):
                return created
            content["registry_as_of"] = created.value.fp1_identity()
    set_fp = body.get("fingerprint")
    if set_fp is not None:
        parsed = _optional_fingerprint(set_fp, REGISTRY_AS_OF_KEY)
        if is_refusal(parsed):
            return parsed
        if parsed.value is not None:
            content["fingerprint"] = parsed.value.value
    if "registry_as_of" not in content and "fingerprint" not in content:
        return invalid(
            REGISTRY_AS_OF_KEY,
            "registry_as_of is an Instant, a set fingerprint, or a mapping of "
            "the as-of instant plus set fingerprint (B-15)",
            given=repr(sorted(body)),
        )
    return _present(fingerprint(content))


def _split_input(config: ResolvedRunConfig) -> Result[Fingerprint | None]:
    return _optional_fingerprint(config.keys.get(SPLIT_FINGERPRINT_KEY), SPLIT_FINGERPRINT_KEY)


def _fidelity_input(config: ResolvedRunConfig) -> Result[Fingerprint | None]:
    raw = config.keys.get(FIDELITY_KEY)
    if raw is None:
        return Ok(None)
    if isinstance(raw, FidelityIdentity):
        claimed = refuse_optimistic_edge_claim(taint=raw.taint)
        if is_refusal(claimed):
            return claimed
        return _present(fingerprint(raw.fp1_identity()))
    if isinstance(raw, RunFidelity):
        claimed = refuse_optimistic_edge_claim(taint=raw.taint)
        if is_refusal(claimed):
            return claimed
        return _present(fingerprint(raw.fp1_identity()))
    if isinstance(raw, Mapping):
        body = cast("Mapping[str, object]", raw)
        if body.get("class") == "run-fidelity":
            claimed = refuse_optimistic_edge_claim(taint=body.get("taint", TAINT_OPTIMISTIC))
            if is_refusal(claimed):
                return claimed
            return _present(fingerprint(dict(body)))
        stamped = FidelityIdentity.try_create(
            body.get("adapter_id"),
            composition_version=body.get("composition_version", COMPOSITION_VERSION),
            taint=body.get("taint", TAINT_OPTIMISTIC),
            calibration_ref=body.get("calibration_ref"),
            fill_basis=body.get("fill_basis"),
        )
        if is_refusal(stamped):
            return stamped
        claimed = refuse_optimistic_edge_claim(taint=stamped.value.taint)
        if is_refusal(claimed):
            return claimed
        return _present(fingerprint(stamped.value.fp1_identity()))
    return invalid(
        FIDELITY_KEY,
        "fidelity identity is adapter-id + composition-version + taint (B-6); "
        "taint is a field on the label and is omitted from fp1 (DEC-0164)",
        given=repr(type(raw).__name__),
    )


def _rng_input(config: ResolvedRunConfig) -> Result[Fingerprint | None]:
    raw = config.keys.get(RNG_PROVENANCE_KEY)
    if raw is None:
        return Ok(None)
    if isinstance(raw, Fingerprint):
        return _held(raw)
    if isinstance(raw, Mapping) and not isinstance(raw, (str, bytes)):
        body = dict(cast("Mapping[str, object]", raw))
        if "class" not in body:
            body = {"class": _RNG_PROVENANCE_CLASS, **body}
        return _present(fingerprint(body))
    return invalid(
        RNG_PROVENANCE_KEY,
        "RNG provenance is a mapping or Fingerprint, present only when the run "
        "is stochastic (B-13, AR-59)",
        given=repr(type(raw).__name__),
    )


def _optional_fingerprint(value: object, field: str) -> Result[Fingerprint | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, Fingerprint):
        return _held(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            field,
            "a CT-32 input fingerprint is fp1:sha256:<hex> via qmf-core",
            given=repr(value),
        )
    parsed = Fingerprint.try_create(token)
    if is_refusal(parsed):
        return parsed
    return _held(parsed.value)


def _held(value: Fingerprint) -> Result[Fingerprint | None]:
    found: Fingerprint | None = value
    return Ok(found)


def _present(value: Result[Fingerprint]) -> Result[Fingerprint | None]:
    if is_refusal(value):
        return value
    return _held(value.value)


def _refuse_edge_claim(config: ResolvedRunConfig) -> Result[None]:
    raw = config.keys.get(FIDELITY_KEY)
    taint: object = TAINT_OPTIMISTIC
    if isinstance(raw, (FidelityIdentity, RunFidelity)):
        taint = raw.taint
    elif isinstance(raw, Mapping):
        taint = cast("Mapping[str, object]", raw).get("taint", TAINT_OPTIMISTIC)
    return refuse_optimistic_edge_claim(taint=taint)


def _as_performance_result(value: object) -> Result[PerformanceResult]:
    if isinstance(value, PerformanceResult):
        return Ok(value)
    result = getattr(value, "performance_result", None)
    if isinstance(result, PerformanceResult):
        return Ok(result)
    if hasattr(value, "performance_result"):
        return invalid(
            "performance_result",
            "CT-32 is minted when run() completes under a resolved run-config; "
            "an aborted or config-less loop emits no governed result",
            result_contract=RESULT_CONTRACT,
        )
    return invalid(
        "outcome",
        "results assembly consumes a completed run() return or a PerformanceResult",
        given=repr(type(value).__name__),
    )


def _as_output_path(value: object) -> Result[Path]:
    if isinstance(value, Path):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "output_dir",
            "the run output directory is a filesystem path",
            given=repr(type(value).__name__),
        )
    return Ok(Path(token))


def _as_existing_output_dir(value: object) -> Result[Path]:
    path = _as_output_path(value)
    if is_refusal(path):
        return path
    root = path.value
    if root.is_symlink() or not root.is_dir():
        return storage(
            "output_dir",
            "results assembly writes the CT-32 container into an existing run output directory",
            path=str(root),
        )
    return Ok(root)


def _write_ct32_bytes(root: Path, data: bytes) -> Result[None]:
    """Exclusive write of ``results/ct-32.json``. Refusal means no artifact."""
    results_dir = root / RESULTS_DIR_NAME
    if results_dir.is_symlink():
        return storage(
            "ct32_artifact",
            "refusing to follow a symlink for the CT-32 results directory",
            path=str(results_dir),
        )
    try:
        results_dir.mkdir(parents=False, exist_ok=True)
    except OSError as exc:
        return storage(
            "ct32_artifact",
            "could not create the run results directory for the CT-32 container",
            given=type(exc).__name__,
            path=str(results_dir),
        )
    target = results_dir / CT32_ARTIFACT_NAME
    try:
        resolved = Path(os.path.realpath(target))
        root_real = Path(os.path.realpath(root))
    except OSError as exc:
        return storage(
            "ct32_artifact",
            "could not resolve the CT-32 artifact path inside the run directory",
            given=type(exc).__name__,
            path=str(target),
        )
    if target.is_symlink() or not resolved.is_relative_to(root_real):
        return storage(
            "ct32_artifact",
            "refusing to follow a symlink or a path that resolves outside the run output directory",
            path=str(target),
            root=str(root),
        )
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    try:
        fd = os.open(  # skylos: ignore[SKY-D215] contained exclusive create
            target,
            flags,
            0o600,
        )
    except FileExistsError:
        return storage(
            "ct32_artifact",
            "exactly one CT-32 container per run output directory; refusing to "
            "overwrite an existing artifact",
            path=str(target),
        )
    except OSError as exc:
        return storage(
            "ct32_artifact",
            "exclusive create of the CT-32 container failed",
            given=type(exc).__name__,
            path=str(target),
        )
    try:
        view = memoryview(data)
        offset = 0
        while offset < len(view):
            offset += os.write(fd, view[offset:])
        os.fsync(fd)
    except OSError as exc:
        os.close(fd)
        target.unlink(missing_ok=True)
        return storage(
            "ct32_artifact",
            "write of the CT-32 container failed; no artifact is retained",
            given=type(exc).__name__,
            path=str(target),
        )
    os.close(fd)
    return Ok(None)
