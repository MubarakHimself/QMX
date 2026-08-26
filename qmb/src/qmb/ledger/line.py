"""Ledger-line schema: one AD-12 labelled object, never a stored verdict (B-4).

The orchestrator is the only writer. Direct library ``run()`` mints no line.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant, Interval
from qmf.core.fingerprint import (
    EvidenceClass,
    Fingerprint,
    ResultLabel,
    World,
    fingerprint,
    governed_namespace,
)
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal
from qmf.risk.performance import PerformanceResult

from qmb._refuse import clean_token, invalid, policy
from qmb.config.compiler import ResolvedRunConfig
from qmb.results.ct32 import mint_run_performance_result

__all__ = [
    "BOOK_BAR_READ_ROLE",
    "LEDGER_FORMAT_VERSION",
    "LEDGER_FORMAT_VERSION_1",
    "LEDGER_LINE_CLASS",
    "ONE_LINE_PER_RUN",
    "PROVENANCE_SANDBOX",
    "ROLE_ABORTED",
    "ROLE_CONFIRMATION",
    "ROLE_REPLICATE",
    "ROLE_TRIAL",
    "RUN_ROLES",
    "STORES_VERDICT",
    "LedgerLine",
    "book_bar_fingerprint",
    "book_bar_lines",
    "merge_ledger_lines",
    "mint_aborted_line",
    "mint_aborted_line_for",
    "mint_completed_line",
]

LEDGER_LINE_CLASS: Final[str] = "qmb-ledger-line"
LEDGER_FORMAT_VERSION_1: Final[int] = 1
LEDGER_FORMAT_VERSION: Final[int] = LEDGER_FORMAT_VERSION_1
ROLE_CONFIRMATION: Final[str] = "confirmation"
ROLE_TRIAL: Final[str] = "trial"
ROLE_REPLICATE: Final[str] = "replicate"
ROLE_ABORTED: Final[str] = "aborted"
RUN_ROLES: Final[tuple[str, ...]] = (
    ROLE_CONFIRMATION,
    ROLE_TRIAL,
    ROLE_REPLICATE,
    ROLE_ABORTED,
)
BOOK_BAR_READ_ROLE: Final[str] = ROLE_CONFIRMATION
PROVENANCE_SANDBOX: Final[str] = "sandbox"
ONE_LINE_PER_RUN: Final[bool] = True
STORES_VERDICT: Final[bool] = False
_VERDICT_KEYS: Final[frozenset[str]] = frozenset(
    {
        "bar-fail",
        "bar-pass",
        "fail",
        "pass",
        "rated",
        "verdict",
    }
)
_ABORTED_CONTEXT_KEYS: Final[tuple[str, ...]] = (
    "cause",
    "terminal",
    "run_id",
    "pid",
    "output_dir",
    "time_limit_key",
    "memory_limit_key",
    "time_limit_ns",
    "elapsed_ns",
    "memory_limit_bytes",
    "observed_bytes",
    "killed_os_process",
    "sibling_processes_touched",
    "enforcement",
    "slices_completed",
    "data_points_processed",
    "is_warming_up",
    "partial_governed_result",
)


@dataclass(frozen=True, slots=True)
class LedgerLine:
    """One governed ledger line. Raw measures; no pass/fail (DEC-0162)."""

    run_id: Fingerprint
    role: str
    world: World
    result_label: Mapping[str, object]
    book_bar_fp1: Fingerprint
    measures: tuple[Mapping[str, object], ...]
    ct32_fingerprint: Fingerprint | None = None
    refusal: Mapping[str, object] | None = None
    sweep_coordinates: Mapping[str, object] | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "result_label", MappingProxyType(dict(self.result_label)))
        frozen_measures = tuple(MappingProxyType(dict(item)) for item in self.measures)
        object.__setattr__(self, "measures", frozen_measures)
        if self.refusal is not None:
            object.__setattr__(self, "refusal", MappingProxyType(dict(self.refusal)))
        if self.sweep_coordinates is not None:
            object.__setattr__(
                self, "sweep_coordinates", MappingProxyType(dict(self.sweep_coordinates))
            )

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Writer/occurrence and SemVer are omitted."""
        content: dict[str, object] = {
            "book_bar_fp1": self.book_bar_fp1.value,
            "class": LEDGER_LINE_CLASS,
            "format_version": LEDGER_FORMAT_VERSION,
            "measures": [dict(item) for item in self.measures],
            "result_label": dict(self.result_label),
            "role": self.role,
            "run_id": self.run_id.value,
            "world": self.world.value,
        }
        if self.ct32_fingerprint is not None:
            content["ct32_fingerprint"] = self.ct32_fingerprint.value
        if self.refusal is not None:
            content["refusal"] = dict(self.refusal)
        if self.sweep_coordinates is not None:
            content["sweep_coordinates"] = dict(self.sweep_coordinates)
        return content

    @classmethod
    def from_mapping(cls, raw: object) -> Result[LedgerLine]:
        """Rebuild a line from one fp1-canonical JSON object."""
        if not isinstance(raw, Mapping):
            return invalid(
                "ledger_line",
                "a ledger line is one fp1-canonical object",
                given=repr(type(raw).__name__),
            )
        body = cast("Mapping[str, object]", raw)
        if body.get("class") != LEDGER_LINE_CLASS:
            return invalid(
                "class",
                "a ledger line names class qmb-ledger-line",
                given=repr(body.get("class")),
            )
        version = body.get("format_version")
        if version != LEDGER_FORMAT_VERSION:
            return invalid(
                "format_version",
                "this reader understands ledger format version 1",
                given=repr(version),
            )
        run_id = _as_fingerprint(body.get("run_id"), "run_id")
        if is_refusal(run_id):
            return run_id
        role = _as_role(body.get("role"))
        if is_refusal(role):
            return role
        world = _as_world(body.get("world"))
        if is_refusal(world):
            return world
        label = body.get("result_label")
        if not isinstance(label, Mapping):
            return invalid(
                "result_label",
                "the line carries the full AD-12 result label",
                given=repr(type(label).__name__),
            )
        book_bar = _as_fingerprint(body.get("book_bar_fp1"), "book_bar_fp1")
        if is_refusal(book_bar):
            return book_bar
        measures = _as_measure_maps(body.get("measures"))
        if is_refusal(measures):
            return measures
        ct32: Fingerprint | None = None
        if "ct32_fingerprint" in body:
            parsed_ct32 = _as_fingerprint(body.get("ct32_fingerprint"), "ct32_fingerprint")
            if is_refusal(parsed_ct32):
                return parsed_ct32
            ct32 = parsed_ct32.value
        refusal: Mapping[str, object] | None = None
        if "refusal" in body:
            raw_refusal = body.get("refusal")
            if not isinstance(raw_refusal, Mapping):
                return invalid(
                    "refusal",
                    "an aborted line carries refusal context as an object",
                    given=repr(type(raw_refusal).__name__),
                )
            refusal = cast("Mapping[str, object]", raw_refusal)
        coordinates: Mapping[str, object] | None = None
        if "sweep_coordinates" in body:
            raw_coordinates = body.get("sweep_coordinates")
            if not isinstance(raw_coordinates, Mapping):
                return invalid(
                    "sweep_coordinates",
                    "a sweep combo line carries {sweep_id, instrument, bar_spec, "
                    "param_hash} as an object",
                    given=repr(type(raw_coordinates).__name__),
                )
            coordinates = cast("Mapping[str, object]", raw_coordinates)
        banned = _verdict_keys(body)
        if banned:
            return policy(
                "verdict",
                "a ledger line stores raw unit-kinded measures, never a pass/fail verdict",
                keys=sorted(banned),
            )
        return Ok(
            cls(
                run_id=run_id.value,
                role=role.value,
                world=world.value,
                result_label=cast("Mapping[str, object]", label),
                book_bar_fp1=book_bar.value,
                measures=measures.value,
                ct32_fingerprint=ct32,
                refusal=refusal,
                sweep_coordinates=coordinates,
            )
        )


def book_bar_fingerprint(config: object) -> Result[Fingerprint]:
    """Fingerprint of the Book bar as resolved at run time (B-4)."""
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "the Book-bar fingerprint is taken from the resolved run-config",
            given=repr(type(config).__name__),
        )
    raw = config.keys.get("book_bar_fp1")
    if isinstance(raw, Fingerprint):
        return Ok(raw)
    token = clean_token(raw)
    if token is not None:
        return Fingerprint.try_create(token)
    return fingerprint(
        {
            "book_fp1": config.book_fp1.value,
            "book_fragment_fp1": config.book_fragment_fp1.value,
            "class": "book-bar-as-resolved",
        }
    )


def mint_completed_line(
    config: object,
    *,
    outcome_identity: object,
    ct32_fingerprint: object,
    role: object = ROLE_CONFIRMATION,
    factory_sandbox: object = False,
    sweep_coordinates: object = None,
) -> Result[LedgerLine]:
    """Mint the completed-run line. Role is never ``aborted``.

    ``sweep_coordinates`` — when this run is one combination of a sweep — stamps
    the ``{sweep_id, instrument, bar_spec, param_hash}`` a read-time fold groups
    by; it is omitted for a standalone run (B-4; spec R10, R11).
    """
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "a ledger line is minted from a resolved run-config",
            given=repr(type(config).__name__),
        )
    parsed_role = _as_role(role)
    if is_refusal(parsed_role):
        return parsed_role
    if parsed_role.value == ROLE_ABORTED:
        return invalid(
            "role",
            "a completed run ledgers confirmation, trial, or replicate; aborted "
            "is minted only from a typed refusal",
            given=parsed_role.value,
        )
    namespace = governed_namespace(config.world)
    if is_refusal(namespace):
        return namespace
    stamped = _as_fingerprint(ct32_fingerprint, "ct32_fingerprint")
    if is_refusal(stamped):
        return stamped
    if not isinstance(outcome_identity, Mapping):
        return invalid(
            "outcome_identity",
            "the isolated run carries the pure run() outcome identity",
            given=repr(type(outcome_identity).__name__),
        )
    outcome = cast("Mapping[str, object]", outcome_identity)
    artifact = _mint_ct32(config, outcome)
    if is_refusal(artifact):
        return artifact
    reproduced = artifact.value.fingerprint()
    if is_refusal(reproduced):
        return reproduced
    if reproduced.value != stamped.value:
        return policy(
            "ct32_fingerprint",
            "re-running a run id under its resolved config must reproduce the "
            "CT-32 fingerprint; a mismatch is a typed refusal (FM-11, DEC-0163)",
            actual=reproduced.value.value,
            expected=stamped.value.value,
            run_id=config.fingerprint.value,
        )
    bar = book_bar_fingerprint(config)
    if is_refusal(bar):
        return bar
    coordinates = _as_sweep_coordinates(sweep_coordinates)
    if is_refusal(coordinates):
        return coordinates
    label = _label_payload(artifact.value.result_label, factory_sandbox=factory_sandbox)
    measures = tuple(item.fp1_identity() for item in artifact.value.measure_set)
    return _build_line(
        run_id=config.fingerprint,
        role=parsed_role.value,
        world=config.world,
        result_label=label,
        book_bar_fp1=bar.value,
        measures=measures,
        ct32_fingerprint=stamped.value,
        refusal=None,
        sweep_coordinates=coordinates.value,
    )


def mint_aborted_line(
    config: object,
    refusal: object,
    *,
    factory_sandbox: object = False,
    sweep_coordinates: object = None,
) -> Result[LedgerLine]:
    """Mint the aborted line with refusal context. Never silently absent.

    The run id, world, and Book bar are read from the resolved run-config. A
    combination whose run-config never compiled has no such artifact; the batch
    driver mints its refused line through :func:`mint_aborted_line_for` instead.
    """
    if not isinstance(config, ResolvedRunConfig):
        return invalid(
            "config",
            "an aborted ledger line cites the resolved run-config",
            given=repr(type(config).__name__),
        )
    bar = book_bar_fingerprint(config)
    if is_refusal(bar):
        return bar
    return mint_aborted_line_for(
        run_id=config.fingerprint,
        world=config.world,
        book_bar_fp1=bar.value,
        refusal=refusal,
        factory_sandbox=factory_sandbox,
        sweep_coordinates=sweep_coordinates,
    )


def mint_aborted_line_for(
    *,
    run_id: object,
    world: object,
    book_bar_fp1: object,
    refusal: object,
    factory_sandbox: object = False,
    sweep_coordinates: object = None,
) -> Result[LedgerLine]:
    """Mint an aborted line from an explicit run id, world, and Book bar (B-4).

    The config-bearing :func:`mint_aborted_line` is the usual door; this
    lower-level minter records a combination whose refusal happened before a
    resolved run-config existed (a combo that never compiled), keyed by the
    combination's own ``fp1``. The line is never silently absent.
    """
    if not isinstance(refusal, TypedRefusal):
        return invalid(
            "refusal",
            "an aborted ledger line carries a typed refusal as context",
            given=repr(type(refusal).__name__),
        )
    parsed_run_id = _as_fingerprint(run_id, "run_id")
    if is_refusal(parsed_run_id):
        return parsed_run_id
    parsed_world = _as_world(world)
    if is_refusal(parsed_world):
        return parsed_world
    parsed_bar = _as_fingerprint(book_bar_fp1, "book_bar_fp1")
    if is_refusal(parsed_bar):
        return parsed_bar
    coordinates = _as_sweep_coordinates(sweep_coordinates)
    if is_refusal(coordinates):
        return coordinates
    namespace = governed_namespace(parsed_world.value)
    if is_refusal(namespace):
        return namespace
    producer = fingerprint(
        {
            "class": LEDGER_LINE_CLASS,
            "format_version": LEDGER_FORMAT_VERSION,
            "role": ROLE_ABORTED,
        }
    )
    if is_refusal(producer):
        return producer
    span = _empty_interval()
    if is_refusal(span):
        return span
    label = ResultLabel.try_create(
        producer.value,
        LEDGER_FORMAT_VERSION,
        (parsed_run_id.value,),
        span.value,
        EvidenceClass.PROVISIONAL,
        parsed_world.value,
    )
    if is_refusal(label):
        return label
    payload = _label_payload(label.value, factory_sandbox=factory_sandbox)
    return _build_line(
        run_id=parsed_run_id.value,
        role=ROLE_ABORTED,
        world=parsed_world.value,
        result_label=payload,
        book_bar_fp1=parsed_bar.value,
        measures=(),
        ct32_fingerprint=None,
        refusal=_refusal_payload(refusal),
        sweep_coordinates=coordinates.value,
    )


def merge_ledger_lines(
    lines: object,
    *,
    world: object,
    role: object,
) -> Result[tuple[LedgerLine, ...]]:
    """World-and-role-scoped merge. Byte-identical duplicates collapse; collisions refuse."""
    parsed_world = _as_world(world)
    if is_refusal(parsed_world):
        return parsed_world
    parsed_role = _as_role(role)
    if is_refusal(parsed_role):
        return parsed_role
    namespace = governed_namespace(parsed_world.value)
    if is_refusal(namespace):
        return namespace
    if isinstance(lines, (str, bytes)) or not isinstance(lines, Sequence):
        return invalid(
            "lines",
            "the merge view reads a sequence of ledger lines",
            given=repr(type(lines).__name__),
        )
    merged: list[LedgerLine] = []
    seen: dict[str, str] = {}
    for index, raw in enumerate(cast("Sequence[object]", lines)):
        if isinstance(raw, LedgerLine):
            line = raw
        else:
            parsed = LedgerLine.from_mapping(raw)
            if is_refusal(parsed):
                extra = dict(parsed.context)
                extra["index"] = index
                return TypedRefusal(
                    category=parsed.category,
                    retryability=parsed.retryability,
                    context=extra,
                    after_condition_descriptor=parsed.after_condition_descriptor,
                )
            line = parsed.value
        if line.world is not parsed_world.value or line.role != parsed_role.value:
            continue
        identity = fingerprint(line.fp1_identity())
        if is_refusal(identity):
            return identity
        digest = identity.value.value
        prior = seen.get(line.run_id.value)
        if prior is None:
            seen[line.run_id.value] = digest
            merged.append(line)
            continue
        if prior == digest:
            continue
        return policy(
            "run_id",
            "exactly one ledger line per run; a second differing line is a collision, "
            "never an overwrite (AR-51, B-4)",
            run_id=line.run_id.value,
            alarm=True,
        )
    return Ok(tuple(merged))


def book_bar_lines(lines: object, *, world: object) -> Result[tuple[LedgerLine, ...]]:
    """Book-bar read: ``role=confirmation`` lines only (B-4, FM-8)."""
    return merge_ledger_lines(lines, world=world, role=BOOK_BAR_READ_ROLE)


def _build_line(
    *,
    run_id: Fingerprint,
    role: str,
    world: World,
    result_label: Mapping[str, object],
    book_bar_fp1: Fingerprint,
    measures: tuple[Mapping[str, object], ...],
    ct32_fingerprint: Fingerprint | None,
    refusal: Mapping[str, object] | None,
    sweep_coordinates: Mapping[str, object] | None = None,
) -> Result[LedgerLine]:
    line = LedgerLine(
        run_id=run_id,
        role=role,
        world=world,
        result_label=result_label,
        book_bar_fp1=book_bar_fp1,
        measures=measures,
        ct32_fingerprint=ct32_fingerprint,
        refusal=refusal,
        sweep_coordinates=sweep_coordinates,
    )
    banned = _verdict_keys(line.fp1_identity())
    if banned:
        return policy(
            "verdict",
            "a ledger line stores raw unit-kinded measures, never a pass/fail verdict",
            keys=sorted(banned),
        )
    return Ok(line)


def _as_sweep_coordinates(value: object) -> Result[Mapping[str, object] | None]:
    """Validate the optional per-combo sweep coordinates carried on the line."""
    if value is None:
        return Ok(None)
    if not isinstance(value, Mapping):
        return invalid(
            "sweep_coordinates",
            "sweep coordinates are a {sweep_id, instrument, bar_spec, param_hash} object",
            given=repr(type(value).__name__),
        )
    raw = cast("Mapping[object, object]", value)
    out: dict[str, object] = {}
    for key, item in raw.items():
        if not isinstance(key, str) or key.strip() == "":
            return invalid(
                "sweep_coordinates",
                "sweep-coordinate keys are non-empty strings",
                given=repr(key),
            )
        out[key] = item
    banned = _verdict_keys(out)
    if banned:
        return policy(
            "sweep_coordinates",
            "a ledger line stores raw unit-kinded measures, never a pass/fail verdict",
            keys=sorted(banned),
        )
    return Ok(out)


def _mint_ct32(
    config: ResolvedRunConfig,
    outcome: Mapping[str, object],
) -> Result[PerformanceResult]:
    span = _interval_from_identity(outcome.get("evidence_range"))
    if is_refusal(span):
        return span
    stream_order = outcome.get("stream_order")
    slice_count = outcome.get("slice_count")
    filled = outcome.get("filled")
    resting = outcome.get("resting")
    filled_count = _sequence_len(filled)
    resting_count = _sequence_len(resting)
    if filled_count is None:
        filled_count = filled
    if resting_count is None:
        resting_count = resting
    return mint_run_performance_result(
        config,
        evidence_range=span.value,
        stream_order=stream_order,
        slice_count=slice_count,
        filled_count=filled_count,
        resting_count=resting_count,
        data_points_processed=outcome.get("data_points_processed"),
        outcome_identity=outcome,
    )


def _label_payload(label: ResultLabel, *, factory_sandbox: object) -> dict[str, object]:
    payload = dict(label.fp1_identity())
    if factory_sandbox is True:
        payload["provenance"] = PROVENANCE_SANDBOX
    return payload


def _refusal_payload(refusal: TypedRefusal) -> dict[str, object]:
    payload: dict[str, object] = {
        "category": refusal.category.value,
        "field": str(refusal.context.get("field", "terminal")),
        "reason": str(refusal.context.get("reason", "")),
    }
    retry = refusal.retryability.value
    if retry.strip() != "":
        payload["retryability"] = retry
    for key in _ABORTED_CONTEXT_KEYS:
        if key not in refusal.context:
            continue
        value = refusal.context[key]
        if isinstance(value, bool):
            payload[key] = value
            continue
        if isinstance(value, int):
            payload[key] = value
            continue
        if isinstance(value, str) and value.strip() != "":
            payload[key] = value
    return payload


def _empty_interval() -> Result[Interval]:
    origin = Instant.try_create(0)
    if is_refusal(origin):
        return origin
    return Interval.try_create(origin.value, origin.value)


def _interval_from_identity(raw: object) -> Result[Interval]:
    if isinstance(raw, Interval):
        return Ok(raw)
    if not isinstance(raw, Mapping):
        return invalid(
            "evidence_range",
            "the result label's evidence range is a half-open Interval",
            given=repr(type(raw).__name__),
        )
    body = cast("Mapping[str, object]", raw)
    start = Instant.try_create(body.get("start_ns"))
    if is_refusal(start):
        return start
    end = Instant.try_create(body.get("end_ns"))
    if is_refusal(end):
        return end
    return Interval.try_create(start.value, end.value)


def _as_fingerprint(value: object, field: str) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    if isinstance(value, str):
        return Fingerprint.try_create(value)
    return invalid(
        field,
        "a fingerprint is the string fp1:sha256:<hex>",
        given=repr(value),
    )


def _as_role(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None or token not in RUN_ROLES:
        return invalid(
            "role",
            "the discriminated run role is confirmation, trial, replicate, or aborted",
            given=repr(value),
            allowed=list(RUN_ROLES),
        )
    return Ok(token)


def _as_world(value: object) -> Result[World]:
    if isinstance(value, World):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid("world", "world is live, replay, or simulated", given=repr(value))
    try:
        return Ok(World(token))
    except ValueError:
        return invalid("world", "world is live, replay, or simulated", given=token)


def _as_measure_maps(
    raw: object,
) -> Result[tuple[Mapping[str, object], ...]]:
    if raw is None:
        return Ok(())
    if isinstance(raw, (str, bytes)) or not isinstance(raw, Sequence):
        return invalid(
            "measures",
            "the line carries an ordered sequence of AD-40 unit-kinded measures",
            given=repr(type(raw).__name__),
        )
    measures: list[Mapping[str, object]] = []
    for index, item in enumerate(cast("Sequence[object]", raw)):
        if not isinstance(item, Mapping):
            return invalid(
                "measures",
                "each measure is an fp1-canonical object with a unit-kind",
                index=index,
                given=repr(type(item).__name__),
            )
        body = cast("Mapping[str, object]", item)
        if body.get("class") == "undefined-measure":
            if "refusal" not in body:
                return invalid(
                    "measures",
                    "an undefined measure carries a typed refusal a reader can "
                    "tell apart from zero",
                    index=index,
                )
            measures.append(body)
            continue
        if "unit_kind" not in body:
            return invalid(
                "measures",
                "every emitted quantity carries a unit-kind from the closed AD-40 vocabulary",
                index=index,
            )
        measures.append(body)
    return Ok(tuple(measures))


def _verdict_keys(payload: Mapping[str, object]) -> tuple[str, ...]:
    found = [key for key in payload if key in _VERDICT_KEYS]
    return tuple(found)


def _sequence_len(value: object) -> int | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return len(cast("Sequence[object]", value))
    return None
