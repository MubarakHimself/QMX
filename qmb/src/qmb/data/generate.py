"""``qmb data generate`` — config-selected synthetic-series adapters (Story 23.1).

``qmb data generate`` is a thin front over the ratified QMF data contracts
(CT-10/CT-15) that produces forex-CFD synthetic series by *selecting* a generator
process and its variables through one resolved, schema-validated, fingerprinted
generator config (R1; B-3; AR-14 fp1). The v1 process menu is exactly four
config-selected adapters — ``block-bootstrap`` (default), ``gaussian-resample``,
``gaussian-noise``, ``gbm`` — and the library/tunnel is NEVER swapped: changing
the test conditions means changing config variables, not editing or replacing an
adapter (B-1 extensibility law, R2).

The three history-seeded processes (``block-bootstrap`` / ``gaussian-resample`` /
``gaussian-noise``) MUST cite a source-dataset id resolved from a qmf-data room
(CT-10); the from-scratch ``gbm`` needs no source and records its source-dataset
id as :data:`SOURCE_DATASET_NONE` (R2).

Every price the adapters emit is exact scaled-integer money quantized to the
instrument's tick size, and every timestamp is int64 UTC-ns on a market-hours-
aware grid (Sunday-open / Friday-close weekend gap, session boundaries) resolved
from a CT-02 market-hours calendar (R6). Any float statistic internal to a
process (a Gaussian draw, a log-return exponent) re-enters the integer money path
ONLY through the named AD-7 :meth:`~qmf.core.exact.Price.from_float` conversion
boundary under the config's declared rounding mode (R6). When a bar completes the
OHLC integrity gate holds on integers — ``low <= open, close <= high`` and strict
positivity — else a typed ``invalid input`` refusal names the offending bar; a
bar is never silently corrected and never silently dropped (R6, R8).

Generated series carry a store-level synthetic-origin taint
(:data:`SYNTHETIC_ORIGIN`, provenance :data:`GENERATOR_PROVENANCE`) so any run
that reads them derives ``world = simulated`` — legal for infrastructure stress
and strategy-logic smoke tests only, never edge (L20). A config may not bind a
replay clock to synthetic-tainted data: world is provenance-derived and B-7 wins,
so such a request is a typed ``invalid input`` (FM-3, DEC-0164). Refusals are
typed throughout: an unknown process is ``unsupported capability``; a
process x instrument mismatch (e.g. corporate-action events on a forex
instrument) is a category-appropriate ``invalid input`` (R2, R8).
"""

from __future__ import annotations

import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.exact import Price, RoundingMode
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import clean_token, invalid, storage, unavailable, unsupported
from qmb.config.compiler import (
    CLOCK_REPLAY,
    CLOCK_SIMULATED,
    PROVENANCE_SYNTHETIC_TAINTED,
)
from qmb.data.gap_check import MarketHoursCalendar

__all__ = [
    "ASSET_CLASS_FOREX_CFD",
    "BLOCK_BOOTSTRAP",
    "CLAIM_CLASSES",
    "CLAIM_INFRA_STRESS",
    "CLAIM_LOGIC_SMOKE",
    "CLAIM_ROBUSTNESS",
    "DEFAULT_GENERATOR_PROCESS",
    "DEFERRED_PROCESSES",
    "EQUITY_ONLY_EVENTS",
    "FROM_SCRATCH_PROCESSES",
    "GAUSSIAN_NOISE",
    "GAUSSIAN_RESAMPLE",
    "GBM",
    "GENERATOR_CONFIG_ARTIFACT_NAME",
    "GENERATOR_CONFIG_CLASS",
    "GENERATOR_CONFIG_FORMAT_VERSION",
    "GENERATOR_PROCESSES",
    "GENERATOR_PROVENANCE",
    "GENERATOR_WORLD",
    "HISTORY_SEEDED_PROCESSES",
    "RNG_FAMILY",
    "SEED_DERIVATION_RULE",
    "SOURCE_DATASET_NONE",
    "SYNTHETIC_ORIGIN",
    "GenerateReceipt",
    "ResolvedGeneratorConfig",
    "SourceDatasetRef",
    "SyntheticBar",
    "generate",
    "generate_identity",
    "has_generator_config",
    "resolve_generator_config",
]

# --- the v1 process menu (R2) — exactly four config-selected adapters --------

BLOCK_BOOTSTRAP: Final[str] = "block-bootstrap"
GAUSSIAN_RESAMPLE: Final[str] = "gaussian-resample"
GAUSSIAN_NOISE: Final[str] = "gaussian-noise"
GBM: Final[str] = "gbm"

# Ordered menu; block-bootstrap is the default and recommended process (R2).
GENERATOR_PROCESSES: Final[tuple[str, ...]] = (
    BLOCK_BOOTSTRAP,
    GAUSSIAN_RESAMPLE,
    GAUSSIAN_NOISE,
    GBM,
)
DEFAULT_GENERATOR_PROCESS: Final[str] = BLOCK_BOOTSTRAP

# History-seeded processes cite a CT-10 source dataset; gbm is from-scratch (R2).
HISTORY_SEEDED_PROCESSES: Final[frozenset[str]] = frozenset(
    {BLOCK_BOOTSTRAP, GAUSSIAN_RESAMPLE, GAUSSIAN_NOISE}
)
FROM_SCRATCH_PROCESSES: Final[frozenset[str]] = frozenset({GBM})

# Open questions, deferred (spec section 5 Q1/Q2): a multi-state regime process
# and a heavy-tailed process are candidates, not v1 — naming one is an
# ``unsupported capability`` refusal, never a silent substitution (R2, R8).
DEFERRED_PROCESSES: Final[frozenset[str]] = frozenset(
    {"regime-switching", "regime-switch", "heavy-tailed", "student-t", "jump-diffusion"}
)

SOURCE_DATASET_NONE: Final[str] = "none"

# --- claim-class labels (L20) — infra-stress / robustness / logic-smoke ------

CLAIM_INFRA_STRESS: Final[str] = "infra-stress"
CLAIM_ROBUSTNESS: Final[str] = "robustness"
CLAIM_LOGIC_SMOKE: Final[str] = "logic-smoke"
CLAIM_CLASSES: Final[tuple[str, ...]] = (
    CLAIM_INFRA_STRESS,
    CLAIM_ROBUSTNESS,
    CLAIM_LOGIC_SMOKE,
)

# --- store-level synthetic-origin taint (derives world = simulated) ----------

SYNTHETIC_ORIGIN: Final[str] = "synthetic"
GENERATOR_PROVENANCE: Final[str] = PROVENANCE_SYNTHETIC_TAINTED
GENERATOR_WORLD: Final[str] = World.SIMULATED.value

# --- the pinned RNG (R5 foundation) ------------------------------------------

RNG_FAMILY: Final[str] = "python-stdlib-random-mt19937"
SEED_DERIVATION_RULE: Final[str] = "base_seed + scenario_index"
_DEFAULT_SEED: Final[int] = 0
_DEFAULT_SCENARIO_COUNT: Final[int] = 1

# --- the config artifact (R1; B-3; AR-14) ------------------------------------

GENERATOR_CONFIG_CLASS: Final[str] = "qmb-generator-config"
GENERATOR_CONFIG_FORMAT_VERSION: Final[int] = 1
GENERATOR_CONFIG_ARTIFACT_NAME: Final[str] = "generator-config.json"

# --- asset class and the events a forex-CFD generator cannot honor (R2) ------

ASSET_CLASS_FOREX_CFD: Final[str] = "forex-cfd"
# Corporate-action events (splits, dividends, renames) are equity-only; a forex
# CFD instrument cannot honor them — requesting one is a category-appropriate
# ``invalid input`` mismatch, never a silent drop (R2, R8).
EQUITY_ONLY_EVENTS: Final[frozenset[str]] = frozenset(
    {"corporate-action", "corporate-actions", "split", "dividend", "rename"}
)

# Per-process parameter menus. block-bootstrap needs a block length; gaussian-noise
# a stress sigma; gbm a start price and volatility. gaussian-resample derives its
# sigma from the source data. Every param is a UI-editable config variable with no
# ratified spine value.
_PROCESS_REQUIRED_PARAMS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        BLOCK_BOOTSTRAP: ("block_length",),
        GAUSSIAN_RESAMPLE: (),
        GAUSSIAN_NOISE: ("sigma",),
        GBM: ("seed_price", "volatility"),
    }
)

_NANOS: Final[int] = 1_000_000_000
_HOUR_NS: Final[int] = 3_600_000_000_000


# --- the OHLC integrity gate (R6, R8) ----------------------------------------


@dataclass(frozen=True, slots=True)
class SyntheticBar:
    """One synthetic OHLC bar: exact strictly-positive scaled-integer prices (R6).

    ``open``, ``high``, ``low``, and ``close`` are exact scaled integers quantized
    to the instrument tick — never binary floats. A valid bar brackets its body:
    ``high`` is at least the open and close, ``low`` at most the open and close,
    and every price is strictly positive. :meth:`try_create` is the completed-bar
    integrity gate: a violation is a typed ``invalid input``, never a silently
    corrected bar (R6, R8, AC4).
    """

    instant_ns: int
    open: int
    high: int
    low: int
    close: int
    scale: int

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Package SemVer never enters."""
        return {
            "class": "qmb-synthetic-bar",
            "close": self.close,
            "high": self.high,
            "instant_ns": self.instant_ns,
            "low": self.low,
            "open": self.open,
            "scale": self.scale,
        }

    def as_mapping(self) -> dict[str, object]:
        """Machine-readable bar row (door transport)."""
        return {
            "instant_ns": self.instant_ns,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "scale": self.scale,
        }

    @classmethod
    def try_create(
        cls,
        instant_ns: object,
        open_price: object,
        high: object,
        low: object,
        close: object,
        scale: object,
    ) -> Result[SyntheticBar]:
        """Validate one strictly-positive, high/low-bounded OHLC bar on integers."""
        stamp = _as_int(instant_ns, "instant_ns")
        if is_refusal(stamp):
            return stamp
        scale_v = _as_positive_int(scale, "scale")
        if is_refusal(scale_v):
            return scale_v
        prices: dict[str, int] = {}
        for field, value in (
            ("open", open_price),
            ("high", high),
            ("low", low),
            ("close", close),
        ):
            checked = _as_positive_int(value, field)
            if is_refusal(checked):
                return checked
            prices[field] = checked.value
        o, h, low_v, c = prices["open"], prices["high"], prices["low"], prices["close"]
        if h < max(o, c) or h < low_v:
            return invalid(
                "high",
                "a completed bar high is at least its open, close, and low; the bar "
                "is refused, never silently corrected (R6, R8)",
                instant_ns=stamp.value,
                open=o,
                high=h,
                low=low_v,
                close=c,
            )
        if low_v > min(o, c):
            return invalid(
                "low",
                "a completed bar low is at most its open and close; the bar is "
                "refused, never silently corrected (R6, R8)",
                instant_ns=stamp.value,
                open=o,
                high=h,
                low=low_v,
                close=c,
            )
        return Ok(
            cls(instant_ns=stamp.value, open=o, high=h, low=low_v, close=c, scale=scale_v.value)
        )


# --- the source-dataset citation (CT-10, R2) ---------------------------------


@dataclass(frozen=True, slots=True)
class SourceDatasetRef:
    """A CT-10 source-dataset citation: the opaque ``(venue, symbol, resolution, side)``."""

    venue: str
    symbol: str
    resolution: str
    side: str

    @property
    def dataset_id(self) -> str:
        """The stable source-dataset id a history-seeded config cites (R2)."""
        return f"{self.venue}:{self.symbol}:{self.resolution}:{self.side}"

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content."""
        return {
            "class": "qmb-source-dataset-ref",
            "resolution": self.resolution,
            "side": self.side,
            "symbol": self.symbol,
            "venue": self.venue,
        }


# --- the resolved generator config (R1; B-3; AR-14) --------------------------


@dataclass(frozen=True, slots=True)
class ResolvedGeneratorConfig:
    """One fully-resolved, read-only, schema-validated generator config (R1, B-3).

    The config selects exactly one process from the v1 menu and pins every
    variable the chosen adapter consumes. Identity is qmf-core ``fp1`` over
    :meth:`fp1_identity`; the fingerprint is the artifact's content-addressed id
    (AR-14). Float-valued process variables (a Gaussian sigma, a GBM drift) are
    carried as their verbatim decimal-string tokens so identity stays exact and
    reproducible — a raw float never enters identity content.
    """

    process: str
    asset_class: str
    venue: str
    symbol: str
    scale: int
    tick_size: int
    resolution: str
    bar_step_ns: int
    start_ns: int
    end_ns: int
    calendar_rule_set: str
    source_dataset_id: str
    seed: int
    scenario_count: int
    claim_class: str
    rounding_mode: str
    process_params: Mapping[str, str]
    events: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "process_params", MappingProxyType(dict(self.process_params)))
        object.__setattr__(self, "events", tuple(self.events))

    @property
    def instrument(self) -> Result[Instrument]:
        """The CT-03 instrument identity ``(venue, venue's own symbol)``."""
        venue = VenueId.try_create(self.venue)
        if is_refusal(venue):
            return venue
        return Instrument.try_create(venue.value, self.symbol)

    @property
    def is_history_seeded(self) -> bool:
        """Whether the process cites a CT-10 source dataset (R2)."""
        return self.process in HISTORY_SEEDED_PROCESSES

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content (AR-14). No SemVer, no float."""
        return {
            "asset_class": self.asset_class,
            "bar_step_ns": self.bar_step_ns,
            "calendar_rule_set": self.calendar_rule_set,
            "claim_class": self.claim_class,
            "class": GENERATOR_CONFIG_CLASS,
            "end_ns": self.end_ns,
            "events": list(self.events),
            "format_version": GENERATOR_CONFIG_FORMAT_VERSION,
            "origin": SYNTHETIC_ORIGIN,
            "process": self.process,
            "process_params": {
                key: self.process_params[key] for key in sorted(self.process_params)
            },
            "resolution": self.resolution,
            "rng_family": RNG_FAMILY,
            "rounding_mode": self.rounding_mode,
            "scale": self.scale,
            "scenario_count": self.scenario_count,
            "seed": self.seed,
            "source_dataset_id": self.source_dataset_id,
            "start_ns": self.start_ns,
            "symbol": self.symbol,
            "tick_size": self.tick_size,
            "venue": self.venue,
            "world": GENERATOR_WORLD,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """``fp1`` over the identity content, computed only by qmf-core (AR-14)."""
        return fingerprint(self.fp1_identity())

    def artifact_relative_path(self, run_id: Fingerprint) -> str:
        """The run-scoped path the config artifact is recorded at, alongside its run."""
        return f"{run_id.value.replace(':', '-')}/{GENERATOR_CONFIG_ARTIFACT_NAME}"

    def as_mapping(self) -> dict[str, object]:
        """Machine-readable resolved config (door transport)."""
        return dict(self.fp1_identity())


# --- the generation receipt --------------------------------------------------


@dataclass(frozen=True, slots=True)
class GenerateReceipt:
    """Machine-readable ``qmb data generate`` outcome (door transport)."""

    command: str
    process: str
    venue: str
    symbol: str
    scale: int
    tick_size: int
    resolution: str
    world: str
    origin: str
    claim_class: str
    source_dataset_id: str
    config_fingerprint: str
    config_artifact_path: str
    config_artifact_written: bool
    store_partition: str
    store_provenance: Mapping[str, object]
    store_provenance_path: str
    store_provenance_written: bool
    bar_count: int
    start_ns: int
    end_ns: int
    seed: int
    scenario_count: int
    rng_family: str
    bars: tuple[SyntheticBar, ...]

    def as_mapping(self) -> dict[str, object]:
        """Door-transport payload; ``command`` keeps CLI/API naming stable."""
        return {
            "command": self.command,
            "process": self.process,
            "venue": self.venue,
            "symbol": self.symbol,
            "scale": self.scale,
            "tick_size": self.tick_size,
            "resolution": self.resolution,
            "world": self.world,
            "origin": self.origin,
            "claim_class": self.claim_class,
            "source_dataset_id": self.source_dataset_id,
            "config_fingerprint": self.config_fingerprint,
            "config_artifact_path": self.config_artifact_path,
            "config_artifact_written": self.config_artifact_written,
            "store_partition": self.store_partition,
            "store_provenance": dict(self.store_provenance),
            "store_provenance_path": self.store_provenance_path,
            "store_provenance_written": self.store_provenance_written,
            "bar_count": self.bar_count,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "seed": self.seed,
            "scenario_count": self.scenario_count,
            "rng_family": self.rng_family,
            "bars": tuple(bar.as_mapping() for bar in self.bars),
        }


def generate_identity() -> dict[str, object]:
    """Identity-bearing generator-front fields. Package SemVer is omitted."""
    return {
        "generator_processes": GENERATOR_PROCESSES,
        "default_process": DEFAULT_GENERATOR_PROCESS,
        "history_seeded_processes": tuple(sorted(HISTORY_SEEDED_PROCESSES)),
        "from_scratch_processes": tuple(sorted(FROM_SCRATCH_PROCESSES)),
        "deferred_processes": tuple(sorted(DEFERRED_PROCESSES)),
        "claim_classes": CLAIM_CLASSES,
        "source_dataset_none": SOURCE_DATASET_NONE,
        "generator_config_class": GENERATOR_CONFIG_CLASS,
        "generator_config_format_version": GENERATOR_CONFIG_FORMAT_VERSION,
        "generator_config_artifact_name": GENERATOR_CONFIG_ARTIFACT_NAME,
        "synthetic_origin": SYNTHETIC_ORIGIN,
        "generator_provenance": GENERATOR_PROVENANCE,
        "generator_world": GENERATOR_WORLD,
        "rng_family": RNG_FAMILY,
        "asset_class": ASSET_CLASS_FOREX_CFD,
        "library_is_never_swapped": True,
    }


def has_generator_config(resources: object) -> bool:
    """Whether ``resources`` names a generator config (a ``process`` to resolve).

    A door hands the thin front only a destination when it wants the generator's
    capability surface; a resolved config carries a ``process`` token, which is
    what turns the front into a generation run.
    """
    if not isinstance(resources, Mapping):
        return False
    body = cast("Mapping[str, object]", resources)
    return clean_token(body.get("process")) is not None or isinstance(
        body.get("generator_config"), Mapping
    )


# --- config resolution (R1, R2, R8) ------------------------------------------


def resolve_generator_config(resources: object) -> Result[ResolvedGeneratorConfig]:
    """Validate door/library resources into a :class:`ResolvedGeneratorConfig`.

    Selects exactly one process from the v1 menu (R2), refuses an unknown process
    (``unsupported capability``) and a process x instrument mismatch
    (``invalid input``) (R2, R8), requires a cited source dataset for a
    history-seeded process and records ``none`` for from-scratch gbm (R2), and
    refuses a config that binds a replay clock to synthetic-tainted data
    (``invalid input``; world is provenance-derived, B-7 wins) (FM-3).
    """
    if not isinstance(resources, Mapping):
        return invalid(
            "resources",
            "a generator config is a key->value mapping",
            given=repr(type(resources).__name__),
        )
    body = cast("Mapping[str, object]", resources)
    inner = body.get("generator_config")
    if isinstance(inner, Mapping):
        merged: dict[str, object] = dict(cast("Mapping[str, object]", inner))
        for key in ("destination", "output_root", "calendar", "source_series"):
            if key in body and key not in merged:
                merged[key] = body[key]
        body = merged

    clock_refusal = _refuse_replay_clock_on_synthetic(body)
    if clock_refusal is not None:
        return clock_refusal

    process = _resolve_process(body.get("process"))
    if is_refusal(process):
        return process

    asset_class = clean_token(body.get("asset_class")) or ASSET_CLASS_FOREX_CFD
    if asset_class != ASSET_CLASS_FOREX_CFD:
        return unsupported(
            "asset_class",
            "the v1 generator produces forex-CFD series only",
            given=asset_class,
            legal=[ASSET_CLASS_FOREX_CFD],
        )

    instrument = _resolve_instrument(body)
    if is_refusal(instrument):
        return instrument
    venue_symbol = instrument.value

    events = _resolve_events(body, process.value, asset_class)
    if is_refusal(events):
        return events

    scale = _as_positive_int(body.get("scale"), "scale")
    if is_refusal(scale):
        return scale
    tick = _as_positive_int(body.get("tick_size", body.get("tick")), "tick_size")
    if is_refusal(tick):
        return tick
    resolution = clean_token(body.get("resolution"))
    if resolution is None:
        return invalid("resolution", "a generator config names a non-empty resolution label")
    step = _as_positive_int(body.get("bar_step_ns", body.get("expected_step_ns")), "bar_step_ns")
    if is_refusal(step):
        return step
    start = _as_int(body.get("start_ns", body.get("start")), "start_ns")
    if is_refusal(start):
        return start
    end = _as_int(body.get("end_ns", body.get("end")), "end_ns")
    if is_refusal(end):
        return end
    if end.value <= start.value:
        return invalid(
            "window",
            "the generation window is a non-empty half-open [start, end)",
            start_ns=start.value,
            end_ns=end.value,
        )

    source_dataset_id = _resolve_source_dataset_id(body, process.value)
    if is_refusal(source_dataset_id):
        return source_dataset_id

    seed = _as_non_negative_int(body.get("seed", _DEFAULT_SEED), "seed")
    if is_refusal(seed):
        return seed
    scenario_count = _as_positive_int(
        body.get("scenario_count", _DEFAULT_SCENARIO_COUNT), "scenario_count"
    )
    if is_refusal(scenario_count):
        return scenario_count

    claim = _resolve_claim_class(body.get("claim_class"), process.value)
    if is_refusal(claim):
        return claim

    rounding = _resolve_rounding(body.get("rounding_mode", body.get("rounding")))
    if is_refusal(rounding):
        return rounding

    params = _resolve_process_params(body, process.value, scale=scale.value)
    if is_refusal(params):
        return params

    config = ResolvedGeneratorConfig(
        process=process.value,
        asset_class=asset_class,
        venue=venue_symbol.venue.value,
        symbol=venue_symbol.symbol,
        scale=scale.value,
        tick_size=tick.value,
        resolution=resolution,
        bar_step_ns=step.value,
        start_ns=start.value,
        end_ns=end.value,
        calendar_rule_set=clean_token(body.get("calendar_rule_set", body.get("rule_set")))
        or "forex-17NY",
        source_dataset_id=source_dataset_id.value,
        seed=seed.value,
        scenario_count=scenario_count.value,
        claim_class=claim.value,
        rounding_mode=rounding.value.value,
        process_params=params.value,
        events=events.value,
    )
    return Ok(config)


# --- the generation entry point ----------------------------------------------


def generate(
    resources: object,
    *,
    calendar: MarketHoursCalendar | None = None,
    source_series: object = None,
    output_root: object = None,
    generated_at_ns: int | None = None,
) -> Result[GenerateReceipt]:
    """Produce one synthetic series from a resolved generator config (R1, R2, R6, R8).

    Resolves the config, resolves the CT-10 source dataset for a history-seeded
    process, builds the market-hours-aware int64 UTC-ns grid from the CT-02
    calendar, runs the config-selected adapter, gates every completed bar's OHLC
    integrity on integers, and materializes the fingerprinted config artifact
    alongside the run it produces. The library/tunnel is never swapped; only
    config variables select the process.

    The produced series carries a store-level ``origin = synthetic`` taint (Story
    23.3): a :class:`~qmb.data.store_taint.SyntheticStoreProvenance` record — the
    process, seed, source-dataset id, config ``fp1``, generation timestamp, and QMX
    generator version — routed into the synthetic-tainted store partition, never a
    governed namespace (AR-33). ``generated_at_ns`` injects the generation timestamp
    (defaulting to the wall clock); the timestamp is recorded provenance, never fp1
    identity, so the run id stays the deterministic config fingerprint.
    """
    resolved = resolve_generator_config(resources)
    if is_refusal(resolved):
        return resolved
    config = resolved.value
    body: Mapping[str, object] = (
        cast("Mapping[str, object]", resources) if isinstance(resources, Mapping) else {}
    )

    instrument = config.instrument
    if is_refusal(instrument):
        return instrument
    rounding = RoundingMode(config.rounding_mode)

    source_bars: tuple[SyntheticBar, ...] | None = None
    if config.is_history_seeded:
        loaded = _resolve_source_series(
            config,
            explicit=source_series if source_series is not None else body.get("source_series"),
            store=body.get("store"),
        )
        if is_refusal(loaded):
            return loaded
        source_bars = loaded.value

    active_calendar = _resolve_calendar(config, calendar=calendar, resources=body)
    if is_refusal(active_calendar):
        return active_calendar

    grid = _market_hours_grid(
        active_calendar.value,
        start_ns=config.start_ns,
        end_ns=config.end_ns,
        step_ns=config.bar_step_ns,
    )
    if is_refusal(grid):
        return grid
    if not grid.value:
        return invalid(
            "window",
            "the market-hours grid is empty for the requested window and calendar; "
            "no open session bar falls in [start, end)",
            start_ns=config.start_ns,
            end_ns=config.end_ns,
        )

    produced = _run_adapter(
        config,
        instrument=instrument.value,
        rounding=rounding,
        grid=grid.value,
        source_bars=source_bars,
    )
    if is_refusal(produced):
        return produced
    bars = produced.value

    materialized = _materialize_config(config, output_root=output_root, resources=body)
    if is_refusal(materialized):
        return materialized
    run_id, artifact_path, written = materialized.value

    tainted = _store_taint(
        config,
        run_id=run_id,
        generated_at_ns=generated_at_ns,
        output_root=output_root,
        resources=body,
    )
    if is_refusal(tainted):
        return tainted
    partition, provenance_record, provenance_path, provenance_written = tainted.value

    return Ok(
        GenerateReceipt(
            command="generate",
            process=config.process,
            venue=config.venue,
            symbol=config.symbol,
            scale=config.scale,
            tick_size=config.tick_size,
            resolution=config.resolution,
            world=GENERATOR_WORLD,
            origin=SYNTHETIC_ORIGIN,
            claim_class=config.claim_class,
            source_dataset_id=config.source_dataset_id,
            config_fingerprint=run_id.value,
            config_artifact_path=artifact_path,
            config_artifact_written=written,
            store_partition=partition,
            store_provenance=provenance_record,
            store_provenance_path=provenance_path,
            store_provenance_written=provenance_written,
            bar_count=len(bars),
            start_ns=config.start_ns,
            end_ns=config.end_ns,
            seed=config.seed,
            scenario_count=config.scenario_count,
            rng_family=RNG_FAMILY,
            bars=bars,
        )
    )


# --- the config-selected adapters (R2, R6) -----------------------------------


@dataclass(frozen=True, slots=True)
class _Draw:
    """One per-bar draw: the bar close and non-negative intrabar range widths."""

    close: int
    high_ext: int
    low_ext: int


def _run_adapter(
    config: ResolvedGeneratorConfig,
    *,
    instrument: Instrument,
    rounding: RoundingMode,
    grid: tuple[int, ...],
    source_bars: tuple[SyntheticBar, ...] | None,
) -> Result[tuple[SyntheticBar, ...]]:
    """Dispatch to the config-selected adapter and assemble gated bars.

    The process token selects one adapter from a fixed table; the assembly
    skeleton (continuity, tick quantization, the OHLC integrity gate) is shared
    and never swapped — extensibility is config selection, not a code change (B-1).
    """
    count = len(grid)
    convert = _FloatToScaledInt(instrument=instrument, scale=config.scale, rounding=rounding)

    draws: Result[tuple[_Draw, ...]]
    if config.process == GBM:  # the only from-scratch process
        draws = _draw_gbm(config, count, convert)
    elif source_bars is None:
        return _refuse_missing_source(config)
    elif config.process == BLOCK_BOOTSTRAP:
        draws = _draw_block_bootstrap(config, source_bars, count)
    elif config.process == GAUSSIAN_RESAMPLE:
        draws = _draw_gaussian_resample(config, source_bars, count, convert)
    else:  # GAUSSIAN_NOISE
        draws = _draw_gaussian_noise(config, source_bars, count, convert)
    if is_refusal(draws):
        return draws

    seed_close = _seed_close(config, source_bars)
    if is_refusal(seed_close):
        return seed_close
    return _assemble_bars(
        grid,
        seed_close=seed_close.value,
        draws=draws.value,
        tick=config.tick_size,
        scale=config.scale,
        rounding=rounding,
    )


def _assemble_bars(
    grid: tuple[int, ...],
    *,
    seed_close: int,
    draws: tuple[_Draw, ...],
    tick: int,
    scale: int,
    rounding: RoundingMode,
) -> Result[tuple[SyntheticBar, ...]]:
    """Shared assembly: close-to-close continuity, tick quantization, OHLC gate.

    Each bar opens at the previous bar's tick-quantized close (the seed close for
    the first bar). The high and low are the body extremes widened by the draw's
    non-negative intrabar extents, so ``high >= max(open, close)`` and
    ``low <= min(open, close)`` hold by construction; every price is quantized to
    the instrument tick, and the completed bar is gated — a violation refuses,
    never silently corrects (R6, R8).
    """
    previous = _quantize_to_tick(seed_close, tick, rounding)
    bars: list[SyntheticBar] = []
    for index, draw in enumerate(draws):
        open_int = previous
        close_int = _quantize_to_tick(draw.close, tick, rounding)
        body_max = max(open_int, close_int)
        body_min = min(open_int, close_int)
        high = _quantize_to_tick(body_max + max(0, draw.high_ext), tick, rounding)
        low = _quantize_to_tick(body_min - max(0, draw.low_ext), tick, rounding)
        built = SyntheticBar.try_create(grid[index], open_int, high, low, close_int, scale)
        if is_refusal(built):
            return built
        bars.append(built.value)
        previous = close_int
    return Ok(tuple(bars))


def _draw_block_bootstrap(
    config: ResolvedGeneratorConfig,
    source_bars: tuple[SyntheticBar, ...],
    count: int,
) -> Result[tuple[_Draw, ...]]:
    """Moving-block bootstrap of exact-integer OHLC deltas (R2 default process).

    Reduces the source series to exact-integer ``(open, high, low, close)`` offsets
    from a running anchor, resamples overlapping length-``block_length`` blocks to
    the grid length with a per-run seeded MT19937 generator, and cumulative-sums
    them back onto the seed price with exact-integer money math — preserving
    short-horizon dependence (autocorrelation, local volatility clustering).
    """
    if len(source_bars) < 2:
        return invalid(
            "source_series",
            "block-bootstrap needs at least two source bars to form OHLC deltas",
            source_bar_count=len(source_bars),
        )
    block_length = int(config.process_params["block_length"])
    n = len(source_bars)
    if block_length < 1 or block_length > n - 1:
        return invalid(
            "block_length",
            "the block length is in [1, source_bar_count - 1]",
            block_length=block_length,
            source_bar_count=n,
        )
    deltas = _ohlc_deltas(source_bars)
    resampled = _resample_blocks(deltas, block_length, config.seed, count)
    anchor = _seed_price_of(source_bars)
    draws: list[_Draw] = []
    for od, hd, ld, cd in resampled:
        close = anchor + cd
        body_max = max(od, cd)
        body_min = min(od, cd)
        draws.append(
            _Draw(close=close, high_ext=max(0, hd - body_max), low_ext=max(0, body_min - ld))
        )
        anchor = close
    return Ok(tuple(draws))


def _draw_gaussian_resample(
    config: ResolvedGeneratorConfig,
    source_bars: tuple[SyntheticBar, ...],
    count: int,
    convert: _FloatToScaledInt,
) -> Result[tuple[_Draw, ...]]:
    """Data-derived Gaussian resample: matched volatility magnitude (R2).

    Estimates the source series' own close-to-close delta statistics (data-derived
    sigma) and regenerates an i.i.d. Gaussian close path of the grid length, with
    intrabar ranges resampled from the source high-close and close-low gap
    statistics. This preserves the real data's volatility magnitude but assumes
    Gaussian i.i.d. increments — it destroys autocorrelation, volatility
    clustering, and fat tails (a robustness caveat, recorded in provenance).
    """
    if len(source_bars) < 2:
        return invalid(
            "source_series",
            "gaussian-resample needs at least two source bars for delta statistics",
            source_bar_count=len(source_bars),
        )
    scale_div = float(10**config.scale)
    close_deltas = [
        source_bars[i].close - source_bars[i - 1].close for i in range(1, len(source_bars))
    ]
    mean_delta, std_delta = _mean_std(close_deltas)
    hi_gaps = [bar.high - max(bar.open, bar.close) for bar in source_bars]
    lo_gaps = [min(bar.open, bar.close) - bar.low for bar in source_bars]
    _, hi_std = _mean_std(hi_gaps)
    _, lo_std = _mean_std(lo_gaps)
    rng = random.Random(config.seed)  # noqa: S311 — a reproducible resample, never a cryptographic use
    anchor = float(_seed_price_of(source_bars)) / scale_div
    mean_real = mean_delta / scale_div
    std_real = std_delta / scale_div
    hi_std_real = hi_std / scale_div
    lo_std_real = lo_std / scale_div
    draws: list[_Draw] = []
    for _ in range(count):
        close_real = anchor + rng.gauss(mean_real, std_real)
        close = convert.price(close_real)
        if is_refusal(close):
            return close
        hi_ext = convert.offset(abs(rng.gauss(0.0, hi_std_real)))
        if is_refusal(hi_ext):
            return hi_ext
        lo_ext = convert.offset(abs(rng.gauss(0.0, lo_std_real)))
        if is_refusal(lo_ext):
            return lo_ext
        draws.append(_Draw(close=close.value, high_ext=hi_ext.value, low_ext=lo_ext.value))
        anchor = float(close.value) / scale_div
    return Ok(tuple(draws))


def _draw_gaussian_noise(
    config: ResolvedGeneratorConfig,
    source_bars: tuple[SyntheticBar, ...],
    count: int,
    convert: _FloatToScaledInt,
) -> Result[tuple[_Draw, ...]]:
    """Explicit-sigma cumulative Gaussian noise on the source close path (R2).

    Walks the real source close path and adds a cumulative Gaussian walk with the
    operator's explicit ``sigma`` amplitude — a perturbation stress knob, not
    data-derived. Intrabar ranges reuse the source bars' own exact-integer high-
    close and close-low gaps, so the real intrabar shape is preserved.
    """
    if len(source_bars) < count:
        return invalid(
            "source_series",
            "gaussian-noise perturbs the source close path and needs at least one "
            "source bar per grid slot",
            source_bar_count=len(source_bars),
            grid_slots=count,
        )
    sigma = _fraction_token(config.process_params.get("sigma"), "sigma")
    if is_refusal(sigma):
        return sigma
    sigma_real = float(sigma.value)
    rng = random.Random(config.seed)  # noqa: S311 — a reproducible perturbation, never a cryptographic use
    scale_div = float(10**config.scale)
    cumulative = 0.0
    draws: list[_Draw] = []
    for index in range(count):
        cumulative += rng.gauss(0.0, sigma_real)
        base = float(source_bars[index].close) / scale_div
        close = convert.price(base + cumulative)
        if is_refusal(close):
            return close
        bar = source_bars[index]
        hi_ext = bar.high - max(bar.open, bar.close)
        lo_ext = min(bar.open, bar.close) - bar.low
        draws.append(_Draw(close=close.value, high_ext=max(0, hi_ext), low_ext=max(0, lo_ext)))
    return Ok(tuple(draws))


def _draw_gbm(
    config: ResolvedGeneratorConfig,
    count: int,
    convert: _FloatToScaledInt,
) -> Result[tuple[_Draw, ...]]:
    """From-scratch geometric Brownian motion — a correct log-normal walk (R2).

    A true GBM: Gaussian log-returns ``r ~ Normal(drift, volatility)`` compound the
    price multiplicatively (``P_next = P * exp(r)``), staying strictly positive by
    construction. It needs no real data and is infrastructure-stress only. Every
    float — the log-return, its exponent, the intrabar range — re-enters the
    integer money path through the named AD-7 conversion boundary under the
    declared rounding mode (R6).
    """
    seed_price = int(config.process_params["seed_price"])
    volatility = _fraction_token(config.process_params.get("volatility"), "volatility")
    if is_refusal(volatility):
        return volatility
    drift = _fraction_token(config.process_params.get("drift", "0"), "drift")
    if is_refusal(drift):
        return drift
    sigma = float(volatility.value)
    mu = float(drift.value)
    rng = random.Random(config.seed)  # noqa: S311 — a reproducible GBM path, never a cryptographic use
    scale_div = float(10**config.scale)
    anchor = float(seed_price) / scale_div
    draws: list[_Draw] = []
    for _ in range(count):
        log_return = rng.gauss(mu, sigma)
        try:
            stepped = anchor * math.exp(log_return)
        except OverflowError:
            stepped = math.inf
        if not math.isfinite(stepped):
            return invalid(
                "volatility",
                "the GBM path diverged to a non-finite price; lower the volatility",
                volatility=config.process_params.get("volatility"),
            )
        close = convert.price(stepped)
        if is_refusal(close):
            return close
        anchor = float(close.value) / scale_div
        hi_ext = convert.offset(abs(rng.gauss(0.0, sigma / 2.0)) * anchor)
        if is_refusal(hi_ext):
            return hi_ext
        lo_ext = convert.offset(abs(rng.gauss(0.0, sigma / 2.0)) * anchor)
        if is_refusal(lo_ext):
            return lo_ext
        draws.append(_Draw(close=close.value, high_ext=hi_ext.value, low_ext=lo_ext.value))
    return Ok(tuple(draws))


# --- the named AD-7 float -> scaled-integer conversion boundary (R6) ---------


@dataclass(frozen=True, slots=True)
class _FloatToScaledInt:
    """The single named float->integer money boundary a process re-enters through.

    Every float statistic internal to a process (a Gaussian draw, an exp of a
    log-return) crosses back onto the integer money path here and nowhere else,
    via qmf-core's AD-7 :meth:`~qmf.core.exact.Price.from_float` under the config's
    declared rounding mode (R6). A price magnitude is converted as a Price; a
    range-width offset is converted the same way and its scaled integer taken.
    """

    instrument: Instrument
    scale: int
    rounding: RoundingMode

    def price(self, value: float) -> Result[int]:
        """Convert a real price magnitude to its exact scaled integer (AD-7)."""
        if not math.isfinite(value):
            return invalid("price", "a synthetic price must be finite", given=repr(value))
        built = Price.from_float(
            value, instrument=self.instrument, scale=self.scale, rounding=self.rounding
        )
        if is_refusal(built):
            return built
        return Ok(built.value.value)

    def offset(self, value: float) -> Result[int]:
        """Convert a non-negative real range-width to a scaled-integer offset (AD-7)."""
        if not math.isfinite(value) or value < 0.0:
            return invalid(
                "offset", "a synthetic range width is finite and non-negative", given=repr(value)
            )
        built = Price.from_float(
            value, instrument=self.instrument, scale=self.scale, rounding=self.rounding
        )
        if is_refusal(built):
            return built
        return Ok(built.value.value)


# --- the market-hours-aware int64 UTC-ns grid (R6) ---------------------------


def _market_hours_grid(
    calendar: MarketHoursCalendar, *, start_ns: int, end_ns: int, step_ns: int
) -> Result[tuple[int, ...]]:
    """Bar-open instants inside open sessions only — the market-hours grid (R6).

    Enumerates the calendar's open sessions in ``[start, end)`` (weekend gap,
    session boundaries) and steps each by ``step_ns``; a slot outside an open
    session is never emitted. Every stamp is an int64 UTC-ns :class:`Instant`.
    """
    spans = _open_spans(calendar, start_ns=start_ns, end_ns=end_ns)
    if is_refusal(spans):
        return spans
    slots: list[int] = []
    for span_start, span_end in spans.value:
        count = (span_end - span_start) // step_ns
        for index in range(count):
            stamp = span_start + (index * step_ns)
            checked = Instant.try_create(stamp)
            if is_refusal(checked):
                return checked
            slots.append(checked.value.value_ns)
    slots.sort()
    return Ok(tuple(slots))


def _open_spans(
    calendar: MarketHoursCalendar, *, start_ns: int, end_ns: int
) -> Result[tuple[tuple[int, int], ...]]:
    """Clipped open-session spans over ``[start, end)`` (mirrors gap-check, B-11)."""
    if getattr(calendar, "always_open", False):
        return Ok(((start_ns, end_ns),))
    spans: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    probe = start_ns
    max_steps = max(8, ((end_ns - start_ns) // _HOUR_NS) + 64)
    steps = 0
    while probe < end_ns and steps < max_steps:
        steps += 1
        instant = Instant.try_create(probe)
        if is_refusal(instant):
            return instant
        window = calendar.session_window(instant.value)
        if is_refusal(window):
            if window.context.get("field") == "instant":
                probe += _HOUR_NS
                continue
            return window
        if window.value is None:
            probe += _HOUR_NS
            continue
        open_ns = window.value.open_instant.value_ns
        close_ns = window.value.close_instant.value_ns
        key = (open_ns, close_ns)
        if key not in seen:
            seen.add(key)
            clipped_start = max(open_ns, start_ns)
            clipped_end = min(close_ns, end_ns)
            if clipped_start < clipped_end:
                spans.append((clipped_start, clipped_end))
        probe = close_ns if close_ns > probe else probe + _HOUR_NS
    spans.sort(key=lambda item: item[0])
    return Ok(tuple(spans))


def _resolve_calendar(
    config: ResolvedGeneratorConfig,
    *,
    calendar: MarketHoursCalendar | None,
    resources: Mapping[str, object],
) -> Result[MarketHoursCalendar]:
    """Resolve a CT-02 market-hours calendar — injected, always-open, or forex."""
    if calendar is not None:
        return Ok(calendar)
    raw = resources.get("calendar")
    if isinstance(raw, MarketHoursCalendar):
        return Ok(raw)
    rule = config.calendar_rule_set.lower()
    if rule in {"always-open", "always_open", "24/7", "247"}:
        from qmf.core.chrono import CalendarIdentity  # noqa: PLC0415

        from qmb.data.gap_check import AlwaysOpenCalendar  # noqa: PLC0415 — sibling front reuse

        identity = CalendarIdentity.try_create("always-open", "v1", "none")
        if is_refusal(identity):
            return identity
        return Ok(cast("MarketHoursCalendar", AlwaysOpenCalendar(identity=identity.value)))
    try:
        from qmf.calendar_forex import get_provider  # noqa: PLC0415 — optional extension
    except ImportError as exc:  # pragma: no cover - env without extension
        return unavailable(
            "calendar",
            "qmf-calendar-forex is required for a forex market-hours grid and is not importable",
            calendar_rule_set=config.calendar_rule_set,
            detail=str(exc),
        )
    provider = get_provider()
    if is_refusal(provider):
        return provider
    return Ok(cast("MarketHoursCalendar", provider.value))


# --- source-dataset resolution (CT-10, R2) -----------------------------------


def _resolve_source_series(
    config: ResolvedGeneratorConfig,
    *,
    explicit: object,
    store: object,
) -> Result[tuple[SyntheticBar, ...]]:
    """Resolve the cited CT-10 source series a history-seeded process seeds from.

    An injected ``source_series`` (the resolved bars of the cited dataset) is used
    directly; otherwise the citation must resolve to present coverage in a qmf-data
    room. A history-seeded process with no resolvable source dataset is an
    ``unavailable dependency`` refusal, never a silent from-scratch fallback (R2).
    """
    if explicit is not None:
        return _coerce_source_bars(explicit, scale=config.scale)
    if store is not None:
        return unavailable(
            "source_series",
            "the cited source dataset was not resolved to bars; supply the resolved "
            "source_series for the cited CT-10 room",
            source_dataset_id=config.source_dataset_id,
        )
    return unavailable(
        "source_series",
        "a history-seeded process cites a CT-10 source dataset; its resolved bars "
        "were not provided",
        process=config.process,
        source_dataset_id=config.source_dataset_id,
    )


def _coerce_source_bars(value: object, *, scale: int) -> Result[tuple[SyntheticBar, ...]]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid("source_series", "the source series is a sequence of OHLC bars")
    items = cast("Sequence[object]", value)
    bars: list[SyntheticBar] = []
    for index, item in enumerate(items):
        if isinstance(item, SyntheticBar):
            bars.append(item)
            continue
        if not isinstance(item, Mapping):
            return invalid(
                "source_series", "each source bar is a mapping or SyntheticBar", index=index
            )
        row = cast("Mapping[str, object]", item)
        built = SyntheticBar.try_create(
            row.get("instant_ns", row.get("instant")),
            row.get("open"),
            row.get("high"),
            row.get("low"),
            row.get("close"),
            row.get("scale", scale),
        )
        if is_refusal(built):
            return built
        bars.append(built.value)
    if not bars:
        return invalid(
            "source_series", "the source series is non-empty for a history-seeded process"
        )
    return Ok(tuple(bars))


# --- config-artifact materialization (R1; AR-14) -----------------------------


def _materialize_config(
    config: ResolvedGeneratorConfig,
    *,
    output_root: object,
    resources: Mapping[str, object],
) -> Result[tuple[Fingerprint, str, bool]]:
    """Fingerprint the resolved config and record it alongside the run it produces.

    The config's ``fp1`` fingerprint is the run's content-addressed id; the
    artifact is written under ``<root>/<run-id>/generator-config.json`` when a
    writable root (an explicit ``output_root`` or the ``destination`` room) is
    available, so the config is a first-class artifact recorded alongside its run
    (R1). Absent a root, the fingerprint and relative path are still reported.
    """
    run_id = config.fingerprint()
    if is_refusal(run_id):
        return run_id
    relative = config.artifact_relative_path(run_id.value)
    root = _resolve_output_root(output_root, resources)
    if root is None:
        return Ok((run_id.value, relative, False))
    written = _write_artifact(root, relative, config)
    if is_refusal(written):
        return written
    return Ok((run_id.value, relative, True))


def _resolve_output_root(output_root: object, resources: Mapping[str, object]) -> Path | None:
    candidate = output_root
    if candidate is None:
        candidate = resources.get("output_root", resources.get("destination"))
    if isinstance(candidate, Path):
        return candidate
    if isinstance(candidate, str) and candidate.strip() != "":
        return Path(candidate)
    return None


def _write_artifact(root: Path, relative: str, config: ResolvedGeneratorConfig) -> Result[None]:
    import json  # noqa: PLC0415 — local, keeps the module import-light

    from qmb.orchestrator.paths import (  # noqa: PLC0415 — import-cycle with orchestrator
        write_bytes_exclusive_no_follow,
    )

    target = root / relative
    try:
        root.mkdir(parents=True, exist_ok=True)
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return storage(
            "generator_config",
            "could not create the generator-config artifact directory",
            given=type(exc).__name__,
            path=str(root),
        )
    # The artifact is content-addressed by its fp1 fingerprint, so an existing
    # regular file at this path already holds identical content — re-recording it
    # is idempotent, never an exclusive-write storage failure.
    if target.is_file() and not target.is_symlink():
        return Ok(None)
    payload = json.dumps(config.as_mapping(), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return write_bytes_exclusive_no_follow(
        target, payload, contain_within=root, field="generator_config"
    )


# --- store-level synthetic taint (Story 23.3; R4, AR-33) ---------------------


def _store_taint(
    config: ResolvedGeneratorConfig,
    *,
    run_id: Fingerprint,
    generated_at_ns: int | None,
    output_root: object,
    resources: Mapping[str, object],
) -> Result[tuple[str, dict[str, object], str, bool]]:
    """Tag the persisted series with a store-level synthetic taint and route it (R4, AR-33).

    Builds a :class:`~qmb.data.store_taint.SyntheticStoreProvenance` (process, seed,
    source-dataset id, config ``fp1``, generation timestamp, generator version),
    routes it into the synthetic-tainted store partition — never a governed namespace
    (AR-33) — and, when a writable root is available, writes the store-level provenance
    record as a partition sidecar (not merely a filename). Returns the partition
    namespace, the record mapping, its relative path, and whether it was written.
    """
    from qmb.data.store_taint import (  # noqa: PLC0415 — import-cycle with store_taint
        ARTIFACT_SERIES,
        route_synthetic_persist,
        tag_synthetic_artifact,
    )

    stamp = generated_at_ns
    if stamp is None:
        import time  # noqa: PLC0415 — the generation timestamp is provenance, never identity

        stamp = time.time_ns()
    provenance = tag_synthetic_artifact(
        config,
        artifact_kind=ARTIFACT_SERIES,
        generation_timestamp_ns=stamp,
    )
    if is_refusal(provenance):
        return provenance
    partition = route_synthetic_persist(provenance.value)
    if is_refusal(partition):
        return partition
    record = provenance.value.as_record()
    relative = partition.value.relative_path
    root = _resolve_output_root(output_root, resources)
    if root is None:
        return Ok((partition.value.namespace, record, relative, False))
    written = _write_provenance(root, relative, record)
    if is_refusal(written):
        return written
    return Ok((partition.value.namespace, record, relative, True))


def _write_provenance(root: Path, relative: str, record: Mapping[str, object]) -> Result[None]:
    import json  # noqa: PLC0415 — local, keeps the module import-light

    from qmb.orchestrator.paths import (  # noqa: PLC0415 — import-cycle with orchestrator
        write_bytes_exclusive_no_follow,
    )

    target = root / relative
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return storage(
            "store_provenance",
            "could not create the synthetic-tainted store partition directory",
            given=type(exc).__name__,
            path=str(target.parent),
        )
    # The record's reproducible identity is content-addressed by the config fp1, so an
    # existing regular file at this path already holds the same taint identity —
    # re-recording it is idempotent, never an exclusive-write storage failure.
    if target.is_file() and not target.is_symlink():
        return Ok(None)
    payload = json.dumps(dict(record), ensure_ascii=False, sort_keys=True).encode("utf-8")
    return write_bytes_exclusive_no_follow(
        target, payload, contain_within=root, field="store_provenance"
    )


# --- resolution helpers ------------------------------------------------------


def _resolve_process(value: object) -> Result[str]:
    token = clean_token(value)
    if token is None:
        return invalid(
            "process",
            "a generator config selects exactly one process",
            legal=list(GENERATOR_PROCESSES),
        )
    if token in GENERATOR_PROCESSES:
        return Ok(token)
    reason = (
        "the v1 process menu is exactly four processes; regime-switching and "
        "heavy-tailed processes are deferred open questions (spec section 5 Q1/Q2)"
        if token in DEFERRED_PROCESSES
        else "the v1 process menu is exactly four processes"
    )
    return unsupported("process", reason, given=token, legal=list(GENERATOR_PROCESSES))


def _resolve_instrument(body: Mapping[str, object]) -> Result[Instrument]:
    venue = clean_token(body.get("venue"))
    if venue is None:
        return invalid("venue", "a generator config names a non-empty venue token")
    symbol = clean_token(body.get("symbol"))
    if symbol is None:
        return invalid("symbol", "a generator config names a non-empty instrument symbol")
    venue_id = VenueId.try_create(venue)
    if is_refusal(venue_id):
        return venue_id
    return Instrument.try_create(venue_id.value, symbol)


def _resolve_events(
    body: Mapping[str, object], process: str, asset_class: str
) -> Result[tuple[str, ...]]:
    raw = body.get("events")
    if raw is None:
        return Ok(())
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
        return invalid("events", "events are a list of event tokens", given=repr(raw))
    events: list[str] = []
    for item in cast("Sequence[object]", raw):
        token = clean_token(item)
        if token is None:
            return invalid("events", "each event is a non-empty token", given=repr(item))
        if token in EQUITY_ONLY_EVENTS:
            return invalid(
                "events",
                "corporate-action events are equity-only; a forex-CFD instrument "
                "cannot honor them — the config x instrument combination is refused, "
                "never silently dropped (R2, R8)",
                event=token,
                asset_class=asset_class,
                process=process,
            )
        return invalid(
            "events",
            "the v1 forex-CFD generator emits no discrete events; the requested "
            "event is not honored for this instrument",
            event=token,
            asset_class=asset_class,
        )
    return Ok(tuple(events))


def _resolve_source_dataset_id(body: Mapping[str, object], process: str) -> Result[str]:
    ref = _coerce_source_dataset_ref(body)
    if is_refusal(ref):
        return ref
    if process in FROM_SCRATCH_PROCESSES:
        if ref.value is not None:
            return invalid(
                "source_dataset",
                "a from-scratch gbm config records no source dataset; it needs none",
                process=process,
            )
        return Ok(SOURCE_DATASET_NONE)
    if ref.value is None:
        return invalid(
            "source_dataset",
            "a history-seeded process must cite a source-dataset id resolved from a "
            "qmf-data room (CT-10)",
            process=process,
        )
    return Ok(ref.value.dataset_id)


def _coerce_source_dataset_ref(body: Mapping[str, object]) -> Result[SourceDatasetRef | None]:
    raw = body.get("source_dataset")
    if raw is None:
        # A bare id string is also accepted as the citation.
        token = clean_token(body.get("source_dataset_id"))
        if token is None:
            return Ok(None)
        if token == SOURCE_DATASET_NONE:
            return Ok(None)
        parts = token.split(":")
        if len(parts) != 4 or any(part.strip() == "" for part in parts):
            return invalid(
                "source_dataset_id",
                "a source-dataset id is venue:symbol:resolution:side",
                given=token,
            )
        return Ok(SourceDatasetRef(parts[0], parts[1], parts[2], parts[3]))
    if isinstance(raw, str):
        if raw.strip() == "" or raw == SOURCE_DATASET_NONE:
            return Ok(None)
        parts = raw.split(":")
        if len(parts) != 4 or any(part.strip() == "" for part in parts):
            return invalid(
                "source_dataset", "a source-dataset id is venue:symbol:resolution:side", given=raw
            )
        return Ok(SourceDatasetRef(parts[0], parts[1], parts[2], parts[3]))
    if isinstance(raw, Mapping):
        row = cast("Mapping[str, object]", raw)
        venue = clean_token(row.get("venue"))
        symbol = clean_token(row.get("symbol"))
        resolution = clean_token(row.get("resolution"))
        side = clean_token(row.get("side"))
        if None in (venue, symbol, resolution, side):
            return invalid(
                "source_dataset",
                "a source-dataset citation names venue, symbol, resolution, and side",
                given=repr(row),
            )
        return Ok(
            SourceDatasetRef(
                cast("str", venue),
                cast("str", symbol),
                cast("str", resolution),
                cast("str", side),
            )
        )
    return invalid("source_dataset", "a source-dataset citation is a string id or a mapping")


def _resolve_claim_class(value: object, process: str) -> Result[str]:
    if value is None:
        return Ok(CLAIM_INFRA_STRESS)
    token = clean_token(value)
    if token is None or token not in CLAIM_CLASSES:
        return invalid(
            "claim_class",
            "the claim class is one of infra-stress, robustness, logic-smoke",
            given=repr(value),
            legal=list(CLAIM_CLASSES),
        )
    if token == CLAIM_ROBUSTNESS and process in FROM_SCRATCH_PROCESSES:
        return invalid(
            "claim_class",
            "a robustness claim is allowed only for a history-seeded process; a "
            "from-scratch gbm run claims infra-stress or logic-smoke, never robustness (L20)",
            process=process,
        )
    return Ok(token)


def _resolve_rounding(value: object) -> Result[RoundingMode]:
    if value is None:
        return Ok(RoundingMode.HALF_UP)
    if isinstance(value, RoundingMode):
        return Ok(value)
    token = clean_token(value)
    if token is not None:
        try:
            return Ok(RoundingMode(token))
        except ValueError:
            pass
    return invalid(
        "rounding_mode",
        "the declared rounding mode is a RoundingMode member",
        given=repr(value),
        legal=[member.value for member in RoundingMode],
    )


def _resolve_process_params(
    body: Mapping[str, object], process: str, *, scale: int
) -> Result[Mapping[str, str]]:
    raw = body.get("process_params")
    supplied: dict[str, object] = {}
    if isinstance(raw, Mapping):
        supplied.update(cast("Mapping[str, object]", raw))
    # Top-level convenience keys also feed the process menu.
    for key in ("block_length", "sigma", "seed_price", "volatility", "drift"):
        if key in body and key not in supplied:
            supplied[key] = body[key]

    params: dict[str, str] = {}
    for key in _PROCESS_REQUIRED_PARAMS[process]:
        if key not in supplied:
            return invalid(
                "process_params",
                f"process {process} requires the '{key}' variable; it has no ratified "
                "default and is never silently applied",
                process=process,
                missing=key,
            )
    if process == BLOCK_BOOTSTRAP:
        block = _as_positive_int(supplied.get("block_length"), "block_length")
        if is_refusal(block):
            return block
        params["block_length"] = str(block.value)
    elif process == GAUSSIAN_NOISE:
        sigma = _fraction_token(supplied.get("sigma"), "sigma")
        if is_refusal(sigma):
            return sigma
        if sigma.value <= 0:
            return invalid(
                "sigma",
                "the gaussian-noise sigma is a positive decimal",
                given=repr(supplied.get("sigma")),
            )
        params["sigma"] = _decimal_token(supplied.get("sigma"))
    elif process == GBM:
        seed_price = _as_positive_int(supplied.get("seed_price"), "seed_price")
        if is_refusal(seed_price):
            return seed_price
        params["seed_price"] = str(seed_price.value)
        volatility = _fraction_token(supplied.get("volatility"), "volatility")
        if is_refusal(volatility):
            return volatility
        if volatility.value <= 0:
            return invalid(
                "volatility",
                "the gbm volatility is a positive decimal",
                given=repr(supplied.get("volatility")),
            )
        params["volatility"] = _decimal_token(supplied.get("volatility"))
        if "drift" in supplied:
            drift = _fraction_token(supplied.get("drift"), "drift")
            if is_refusal(drift):
                return drift
            params["drift"] = _decimal_token(supplied.get("drift"))
    return Ok(MappingProxyType(params))


def _refuse_replay_clock_on_synthetic(body: Mapping[str, object]) -> TypedRefusal | None:
    """A config may not bind a replay clock to synthetic-tainted data (FM-3).

    World is provenance-derived and generated store data is synthetic-tainted, so a
    caller-declared replay clock (or a non-simulated world) is a typed ``invalid
    input`` — B-7 wins, a caller may not declare world (DEC-0164).
    """
    clock = clean_token(body.get("clock"))
    if clock is not None and clock == CLOCK_REPLAY:
        return invalid(
            "clock",
            "a replay clock bound to synthetic-tainted data is invalid input; generated "
            "data is world=simulated and the clock is provenance-derived (FM-3, DEC-0164)",
            given=clock,
            legal=[CLOCK_SIMULATED],
        )
    world = clean_token(body.get("world"))
    if world is not None and world != World.SIMULATED.value:
        return invalid(
            "world",
            "generated store data derives world=simulated; a caller may not declare a "
            "non-simulated world for synthetic data (FM-3, DEC-0164)",
            given=world,
            legal=[World.SIMULATED.value],
        )
    return None


# --- small numeric helpers ---------------------------------------------------


def _ohlc_deltas(bars: tuple[SyntheticBar, ...]) -> tuple[tuple[int, int, int, int], ...]:
    """Reduce a bar series to exact-integer ``(open, high, low, close)`` offsets."""
    anchor = _seed_price_of(bars)
    deltas: list[tuple[int, int, int, int]] = []
    for bar in bars:
        deltas.append((bar.open - anchor, bar.high - anchor, bar.low - anchor, bar.close - anchor))
        anchor = bar.close
    return tuple(deltas)


def _resample_blocks(
    deltas: tuple[tuple[int, int, int, int], ...], block_length: int, seed: int, count: int
) -> tuple[tuple[int, int, int, int], ...]:
    """Moving-block bootstrap: overlapping length-``block_length`` blocks to ``count``."""
    n = len(deltas)
    num_starts = n - block_length + 1
    blocks_needed = -(-count // block_length)  # ceil division
    rng = random.Random(seed)  # noqa: S311 — a reproducible resample, never a cryptographic use
    resampled: list[tuple[int, int, int, int]] = []
    for _ in range(blocks_needed):
        start = rng.randrange(num_starts)
        resampled.extend(deltas[start : start + block_length])
    return tuple(resampled[:count])


def _refuse_missing_source(config: ResolvedGeneratorConfig) -> TypedRefusal:
    """A history-seeded process reached the adapter without its resolved source."""
    return unavailable(
        "source_series",
        "a history-seeded process needs the resolved bars of its cited source dataset",
        process=config.process,
        source_dataset_id=config.source_dataset_id,
    )


def _seed_price_of(bars: tuple[SyntheticBar, ...]) -> int:
    """The cumulative-sum seed price: the first source bar's open."""
    return bars[0].open


def _seed_close(
    config: ResolvedGeneratorConfig, source_bars: tuple[SyntheticBar, ...] | None
) -> Result[int]:
    """The first bar's opening price the assembly seeds continuity from."""
    if config.process in FROM_SCRATCH_PROCESSES:
        return Ok(int(config.process_params["seed_price"]))
    if source_bars is None or not source_bars:
        return invalid("source_series", "a history-seeded process needs a non-empty source series")
    return Ok(_seed_price_of(source_bars))


def _quantize_to_tick(value: int, tick: int, rounding: RoundingMode) -> int:
    """Quantize a scaled integer to the nearest tick multiple under ``rounding``."""
    if tick <= 1:
        return value
    quotient, remainder = divmod(value, tick)
    if remainder == 0:
        return value
    twice = remainder * 2
    if rounding is RoundingMode.FLOOR or rounding is RoundingMode.DOWN:
        chosen = quotient
    elif rounding is RoundingMode.CEILING or rounding is RoundingMode.UP:
        chosen = quotient + 1
    elif rounding is RoundingMode.HALF_EVEN:
        if twice > tick:
            chosen = quotient + 1
        elif twice < tick:
            chosen = quotient
        else:
            chosen = quotient if quotient % 2 == 0 else quotient + 1
    else:  # HALF_UP — ties round up
        chosen = quotient + 1 if twice >= tick else quotient
    return chosen * tick


def _mean_std(values: Sequence[int]) -> tuple[float, float]:
    """Population mean and standard deviation of integer samples (a float statistic)."""
    n = len(values)
    if n == 0:
        return (0.0, 0.0)
    mean = sum(values) / n
    variance = sum((float(value) - mean) ** 2 for value in values) / n
    return (mean, math.sqrt(variance))


def _fraction_token(value: object, field: str) -> Result[Fraction]:
    """Parse a decimal-string (or int) config variable to an exact Fraction."""
    if isinstance(value, bool):
        return invalid(field, f"{field} is a decimal number, never a bool", given=repr(value))
    if isinstance(value, int):
        return Ok(Fraction(value))
    token = clean_token(value)
    if token is None:
        return invalid(field, f"{field} is a decimal-string config variable", given=repr(value))
    try:
        return Ok(Fraction(token))
    except (ValueError, ZeroDivisionError):
        return invalid(field, f"{field} is a decimal-string config variable", given=token)


def _decimal_token(value: object) -> str:
    """The verbatim decimal token stored in identity (never a raw float)."""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _as_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool):
        return invalid(field, f"{field} is an int64, never a bool", given=repr(value))
    if isinstance(value, int):
        return Ok(value)
    if isinstance(value, str) and value.strip() != "":
        token = value.strip()
        if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
            return Ok(int(token))
    return invalid(field, f"{field} is required as an int64", given=repr(value))


def _as_positive_int(value: object, field: str) -> Result[int]:
    checked = _as_int(value, field)
    if is_refusal(checked):
        return checked
    if checked.value <= 0:
        return invalid(field, f"{field} is a strictly positive integer", given=checked.value)
    return Ok(checked.value)


def _as_non_negative_int(value: object, field: str) -> Result[int]:
    checked = _as_int(value, field)
    if is_refusal(checked):
        return checked
    if checked.value < 0:
        return invalid(field, f"{field} is a non-negative integer", given=checked.value)
    return Ok(checked.value)
