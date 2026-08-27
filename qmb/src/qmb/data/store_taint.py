"""Store-level synthetic taint, provenance & world derivation (Story 23.3).

This module closes the exact gap where a from-scratch generator writes data files
indistinguishable from real data (spec section 2A.8, R4): every persisted
synthetic artifact carries ``origin = synthetic`` **at the store level** — a
structured provenance record in a dedicated store partition, not merely a taint in
a filename. World is then **derived from that store provenance, never
caller-declared** (B-7): any run that reads store-persisted synthetic data is
``world = simulated`` and a ``policy rejection`` for governed evidence until
GAP-0048 — infra-stress and logic-smoke only, closing the synthetic backdoor LEAN
ships (FM-2; SC-06).

The store-level contract has six load-bearing parts:

* **the provenance record** (:class:`SyntheticStoreProvenance`, AC1): when a
  synthetic series, tick series, or derived aggregate is persisted it records the
  process id, seed, source-dataset id (or ``none``), the generator-config ``fp1``
  (AR-14), the generation timestamp (UTC-ns), and the QMX generator version. The
  ``fp1`` identity is the reproducible taint content (the config fingerprint and
  its lineage); the wall-clock timestamp and the SemVer version are recorded
  provenance, never identity (B-13, DEC-0167);
* **world derivation** (:func:`derive_world_from_store_provenance`,
  :func:`read_synthetic_store`, AC2): a store read derives ``world = simulated``
  from provenance; a caller-declared non-simulated world is ``invalid input``
  (B-7). The read is a ``policy rejection`` for governed evidence until GAP-0048;
* **the clock/adapter binding refusal** (:func:`resolve_store_clock_binding`,
  AC3): a resolved run-config that binds a replay clock — or a replay/live adapter
  — to synthetic-tainted store data is ``invalid input``; B-7 wins over B-2
  (FM-3, DEC-0164);
* **non-promotability** (:func:`refuse_synthetic_load`,
  :func:`refuse_promote_synthetic`, AC4): loading synthetic data into a
  ``world = replay`` or ``world = live`` context, or promoting a synthetic
  artifact toward live money, is a typed refusal — the synthetic backdoor is
  closed by construction (R4, R8);
* **the procedure-ephemeral contrast** (:func:`procedure_ephemeral_taint`, AC5): a
  block-bootstrap or B-14 trade-shuffle that perturbs a ``world = replay`` run
  **without persisting** a synthetic series creates NO store partition — world
  stays replay, the procedure identity and seed enter the CT-32 label, and the
  claim class is robustness-only, never edge, never admission evidence (B-7);
* **the partition router** (:func:`route_synthetic_persist`, AC6): a generation
  persists only into the synthetic-tainted store partition, never the live or
  governed-evidence namespace; a ``world = simulated`` write into a governed/live
  namespace refuses (AR-33; qmf-core :func:`governed_namespace` refuses simulated).

This module holds no mutable state and reads nothing ambient; every operation is a
pure ``Result``-returning function or a frozen value type.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.fingerprint import (
    LIVE_EVIDENCE_NAMESPACE,
    Fingerprint,
    World,
    fingerprint,
    governed_namespace,
)
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._display import __version__ as _QMB_GENERATOR_VERSION
from qmb._refuse import clean_token, invalid, policy
from qmb.config.compiler import (
    CLOCK_REPLAY,
    CLOCK_SIMULATED,
    PROVENANCE_PROCEDURE_EPHEMERAL,
    PROVENANCE_SYNTHETIC_TAINTED,
)
from qmb.data.claim_class import SIMULATED_PERMITS, refuse_governed_evidence_use
from qmb.data.generate import (
    CLAIM_ROBUSTNESS,
    GENERATOR_PROCESSES,
    SOURCE_DATASET_NONE,
    SYNTHETIC_ORIGIN,
    ResolvedGeneratorConfig,
)
from qmb.data.rng import RNG_ALGORITHM, RNG_FAMILY, RNG_VERSION

__all__ = [
    "ARTIFACT_DERIVED_AGGREGATE",
    "ARTIFACT_SERIES",
    "ARTIFACT_TICK_SERIES",
    "GAP_0048",
    "GENERATOR_VERSION",
    "GOVERNED_EVIDENCE_NAMESPACES",
    "STORE_ARTIFACT_KINDS",
    "STORE_DATA_PROVENANCE",
    "STORE_PROVENANCE_ARTIFACT_NAME",
    "STORE_PROVENANCE_CLASS",
    "STORE_PROVENANCE_FORMAT_VERSION",
    "STORE_WORLD",
    "SYNTHETIC_IS_PROMOTABLE",
    "SYNTHETIC_STORE_PARTITION",
    "EphemeralPerturbationTaint",
    "StoreReadClassification",
    "SyntheticStorePartition",
    "SyntheticStoreProvenance",
    "derive_world_from_store_provenance",
    "procedure_ephemeral_taint",
    "read_synthetic_store",
    "refuse_ephemeral_as_admission_evidence",
    "refuse_governed_evidence_use",
    "refuse_promote_synthetic",
    "refuse_replay_clock_on_synthetic_store",
    "refuse_synthetic_load",
    "refuse_synthetic_write_into_governed_namespace",
    "resolve_store_clock_binding",
    "route_synthetic_persist",
    "store_provenance_relative_path",
    "store_taint_identity",
    "synthetic_is_promotable",
    "tag_synthetic_artifact",
]

# --- the synthetic-tainted store partition (AC6, AR-33) ----------------------

# The dedicated store partition every persisted synthetic artifact is routed into.
# It is deliberately DISTINCT from the qmf-core governed-evidence namespaces
# (``live`` / ``replay``): world separation is delivered by storage separation, so
# synthetic data can never share a partition with recorded governed evidence
# (AR-33, DEC-0110). A ``world = simulated`` write into a governed namespace is
# refused by qmf-core :func:`governed_namespace` (FM-7).
SYNTHETIC_STORE_PARTITION: Final[str] = "synthetic-tainted"


def _resolve_governed_namespaces() -> frozenset[str]:
    """The governed-evidence namespaces a synthetic write may never occupy (AR-33)."""
    names: set[str] = {LIVE_EVIDENCE_NAMESPACE}
    replay = governed_namespace(World.REPLAY)
    if is_refusal(replay):  # pragma: no cover - replay always resolves
        return frozenset(names)
    names.add(replay.value)
    return frozenset(names)


GOVERNED_EVIDENCE_NAMESPACES: Final[frozenset[str]] = _resolve_governed_namespaces()

# --- the store-level taint constants -----------------------------------------

# ``world`` and ``data_provenance`` are DERIVED from the store taint, never declared.
STORE_WORLD: Final[str] = World.SIMULATED.value
STORE_DATA_PROVENANCE: Final[str] = PROVENANCE_SYNTHETIC_TAINTED

# The claim classes a store-persisted synthetic (world=simulated) read may carry
# until GAP-0048 closes — infra-stress and logic-smoke only, never verdict-bearing
# robustness (AC2, SC-06). Reused from the Story 23.2 claim-class contract.
STORE_PERMITTED_CLAIM_CLASSES: Final[tuple[str, ...]] = SIMULATED_PERMITS

# Synthetic artifacts are non-promotable by construction (R4, AC4).
SYNTHETIC_IS_PROMOTABLE: Final[bool] = False

# The QMX generator version recorded on every store provenance record (AC1). It is
# display-only SemVer provenance and never enters fp1 identity (B-13, DEC-0167).
GENERATOR_VERSION: Final[str] = _QMB_GENERATOR_VERSION

GAP_0048: Final[str] = "GAP-0048"

# --- the store-persisted artifact kinds a taint record tags (AC1) ------------

ARTIFACT_SERIES: Final[str] = "synthetic-series"
ARTIFACT_TICK_SERIES: Final[str] = "synthetic-tick-series"
ARTIFACT_DERIVED_AGGREGATE: Final[str] = "synthetic-derived-aggregate"
STORE_ARTIFACT_KINDS: Final[tuple[str, ...]] = (
    ARTIFACT_SERIES,
    ARTIFACT_TICK_SERIES,
    ARTIFACT_DERIVED_AGGREGATE,
)

# --- the store provenance record contract ------------------------------------

STORE_PROVENANCE_CLASS: Final[str] = "qmb-synthetic-store-provenance"
STORE_PROVENANCE_FORMAT_VERSION: Final[int] = 1
STORE_PROVENANCE_ARTIFACT_NAME: Final[str] = "synthetic-provenance.json"

_EPHEMERAL_TAINT_CLASS: Final[str] = "qmb-procedure-ephemeral-taint"

# A replay/live adapter declares real provenance; binding one to synthetic-tainted
# store data is a clock/adapter-versus-provenance mismatch (AC3, FM-3).
_NON_SIMULATED_ADAPTERS: Final[frozenset[str]] = frozenset({CLOCK_REPLAY, World.LIVE.value})


# --- the store-level provenance record (AC1) ---------------------------------


@dataclass(frozen=True, slots=True)
class SyntheticStoreProvenance:
    """The store-level ``origin = synthetic`` taint a persisted artifact carries (AC1, R4).

    Tags a persisted synthetic series, tick series, or derived aggregate at the
    store level — not merely in a filename — recording the process id, seed,
    source-dataset id (or :data:`~qmb.data.generate.SOURCE_DATASET_NONE`), the
    generator-config ``fp1`` (AR-14), the generation timestamp (UTC-ns), and the QMX
    generator version. ``origin`` is always ``synthetic`` and the derived world is
    always ``simulated``; the artifact is non-promotable by construction (R4).

    Identity (:meth:`fp1_identity`) is the reproducible taint content — the config
    fingerprint and its lineage. The wall-clock ``generation_timestamp_ns`` and the
    SemVer ``generator_version`` are recorded provenance carried by :meth:`as_record`,
    never fp1 identity (B-13, DEC-0167), so the same generator config taints to a
    byte-identical fingerprint whenever it was generated.
    """

    origin: str
    artifact_kind: str
    process: str
    seed: int
    source_dataset_id: str
    config_fp1: str
    generation_timestamp_ns: int
    generator_version: str
    venue: str
    symbol: str
    resolution: str

    @property
    def world(self) -> World:
        """Always ``simulated`` — derived from the store taint, never declared (B-7)."""
        return World.SIMULATED

    @property
    def data_provenance(self) -> str:
        """Always ``synthetic-tainted`` — the provenance world derivation reads (B-7)."""
        return STORE_DATA_PROVENANCE

    @property
    def is_promotable(self) -> bool:
        """Always ``False`` — a synthetic artifact never promotes toward live money (R4)."""
        return SYNTHETIC_IS_PROMOTABLE

    @property
    def permittable_claim_classes(self) -> tuple[str, ...]:
        """Infra-stress and logic-smoke only until GAP-0048 (AC2, SC-06)."""
        return STORE_PERMITTED_CLAIM_CLASSES

    def fp1_identity(self) -> dict[str, object]:
        """The reproducible taint identity. Timestamp and SemVer never enter (B-13)."""
        return {
            "artifact_kind": self.artifact_kind,
            "class": STORE_PROVENANCE_CLASS,
            "config_fp1": self.config_fp1,
            "data_provenance": STORE_DATA_PROVENANCE,
            "format_version": STORE_PROVENANCE_FORMAT_VERSION,
            "is_promotable": SYNTHETIC_IS_PROMOTABLE,
            "origin": self.origin,
            "process": self.process,
            "resolution": self.resolution,
            "seed": self.seed,
            "source_dataset_id": self.source_dataset_id,
            "symbol": self.symbol,
            "venue": self.venue,
            "world": STORE_WORLD,
        }

    def as_record(self) -> dict[str, object]:
        """The full store-level provenance record (door transport / persisted sidecar).

        Adds the recorded-not-identity provenance fields AC1 enumerates — the
        generation timestamp (UTC-ns) and the QMX generator version — to the fp1
        identity content, plus the QMX-owned pinned-RNG algorithm and version the
        generator drew through (Story 23.4, AC2; recorded provenance, never fp1 identity,
        since the config ``fp1`` already binds the RNG). The generator never draws through
        a runtime stdlib Random (spec section 2A.3).
        """
        record = dict(self.fp1_identity())
        record["generation_timestamp_ns"] = self.generation_timestamp_ns
        record["generator_version"] = self.generator_version
        record["rng_algorithm"] = RNG_ALGORITHM
        record["rng_family"] = RNG_FAMILY
        record["rng_version"] = RNG_VERSION
        record["rng_is_runtime_stdlib_random"] = False
        return record

    def fingerprint(self) -> Result[Fingerprint]:
        """``fp1`` over the reproducible taint identity, computed only by qmf-core (AR-14)."""
        return fingerprint(self.fp1_identity())

    @classmethod
    def try_create(
        cls,
        *,
        artifact_kind: object,
        process: object,
        seed: object,
        source_dataset_id: object,
        config_fp1: object,
        generation_timestamp_ns: object,
        venue: object,
        symbol: object,
        resolution: object,
        generator_version: object = GENERATOR_VERSION,
    ) -> Result[SyntheticStoreProvenance]:
        """Validate a store-level synthetic provenance record (AC1)."""
        kind = clean_token(artifact_kind)
        if kind is None or kind not in STORE_ARTIFACT_KINDS:
            return invalid(
                "artifact_kind",
                "a store taint tags a synthetic series, tick series, or derived aggregate",
                given=repr(artifact_kind),
                legal=list(STORE_ARTIFACT_KINDS),
            )
        proc = clean_token(process)
        if proc is None or proc not in GENERATOR_PROCESSES:
            return invalid(
                "process",
                "the store taint records the v1 generator process that produced the artifact",
                given=repr(process),
                legal=list(GENERATOR_PROCESSES),
            )
        seed_v = _non_negative_int(seed, "seed")
        if is_refusal(seed_v):
            return seed_v
        source = clean_token(source_dataset_id) or SOURCE_DATASET_NONE
        config_token = _fingerprint_token(config_fp1)
        if is_refusal(config_token):
            return config_token
        stamp = _non_negative_int(generation_timestamp_ns, "generation_timestamp_ns")
        if is_refusal(stamp):
            return stamp
        venue_token = clean_token(venue)
        symbol_token = clean_token(symbol)
        resolution_token = clean_token(resolution)
        if venue_token is None or symbol_token is None or resolution_token is None:
            return invalid(
                "instrument",
                "the store taint records the tainted artifact's venue, symbol, and resolution",
                venue=repr(venue),
                symbol=repr(symbol),
                resolution=repr(resolution),
            )
        version_token = clean_token(generator_version)
        if version_token is None:
            return invalid(
                "generator_version",
                "the store taint records the QMX generator version",
                given=repr(generator_version),
            )
        return Ok(
            cls(
                origin=SYNTHETIC_ORIGIN,
                artifact_kind=kind,
                process=proc,
                seed=seed_v.value,
                source_dataset_id=source,
                config_fp1=config_token.value,
                generation_timestamp_ns=stamp.value,
                generator_version=version_token,
                venue=venue_token,
                symbol=symbol_token,
                resolution=resolution_token,
            )
        )


def tag_synthetic_artifact(
    config: object,
    *,
    artifact_kind: object = ARTIFACT_SERIES,
    generation_timestamp_ns: object,
    generator_version: object = GENERATOR_VERSION,
) -> Result[SyntheticStoreProvenance]:
    """Tag a persisted synthetic artifact with a store-level provenance record (AC1, R4).

    Reads the process, seed, source-dataset id, and instrument from a resolved
    generator config, cites the config's ``fp1`` (AR-14), and records the generation
    timestamp (UTC-ns) and the QMX generator version. The result is the store-level
    ``origin = synthetic`` taint — not a filename convention — from which world is
    derived. ``config`` is a :class:`~qmb.data.generate.ResolvedGeneratorConfig`.
    """
    if not isinstance(config, ResolvedGeneratorConfig):
        return invalid(
            "config",
            "a store taint is derived from a resolved generator config",
            given=repr(type(config).__name__),
        )
    fp = config.fingerprint()
    if is_refusal(fp):
        return fp
    return SyntheticStoreProvenance.try_create(
        artifact_kind=artifact_kind,
        process=config.process,
        seed=config.seed,
        source_dataset_id=config.source_dataset_id,
        config_fp1=fp.value,
        generation_timestamp_ns=generation_timestamp_ns,
        venue=config.venue,
        symbol=config.symbol,
        resolution=config.resolution,
        generator_version=generator_version,
    )


# --- the synthetic-tainted store partition (AC6) -----------------------------


@dataclass(frozen=True, slots=True)
class SyntheticStorePartition:
    """A routed synthetic-tainted store partition — never a governed namespace (AC6, AR-33).

    A generation persists only here: ``namespace`` is always
    :data:`SYNTHETIC_STORE_PARTITION`, distinct from the live and governed-evidence
    namespaces, and ``relative_path`` locates the store-level provenance record under
    the run id. ``world`` is ``simulated``; qmf-core :func:`governed_namespace`
    refuses a governed write for that world (FM-7).
    """

    namespace: str
    relative_path: str
    provenance: SyntheticStoreProvenance

    @property
    def world(self) -> World:
        """Always ``simulated`` — a synthetic partition is never governed evidence."""
        return World.SIMULATED

    @property
    def is_governed_namespace(self) -> bool:
        """Always ``False`` — the synthetic partition is never a governed namespace (AR-33)."""
        return self.namespace in GOVERNED_EVIDENCE_NAMESPACES

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content — the partition plus its provenance taint."""
        return {
            "class": "qmb-synthetic-store-partition",
            "namespace": self.namespace,
            "provenance": self.provenance.fp1_identity(),
            "relative_path": self.relative_path,
            "world": STORE_WORLD,
        }


def store_provenance_relative_path(provenance: SyntheticStoreProvenance) -> str:
    """The run-scoped path the store-level provenance record is recorded at (AC1, AC6).

    ``<synthetic-tainted>/<run-id>/synthetic-provenance.json`` with a
    filesystem-safe run-id directory (colon is not a legal Windows path character).
    """
    run_id = provenance.config_fp1.replace(":", "-")
    return f"{SYNTHETIC_STORE_PARTITION}/{run_id}/{STORE_PROVENANCE_ARTIFACT_NAME}"


def route_synthetic_persist(
    provenance: object,
    *,
    requested_namespace: object = None,
) -> Result[SyntheticStorePartition]:
    """Route a synthetic persist into the tainted partition, never a governed namespace (AC6).

    A generation persists ONLY into :data:`SYNTHETIC_STORE_PARTITION`. A caller that
    requests the live or governed-evidence namespace for a ``world = simulated``
    synthetic write is a typed refusal — world separation is storage separation
    (AR-33, B-7). qmf-core :func:`governed_namespace` independently refuses a governed
    write for ``world = simulated`` (FM-7).
    """
    if not isinstance(provenance, SyntheticStoreProvenance):
        return invalid(
            "provenance",
            "a synthetic persist routes a store-level SyntheticStoreProvenance taint",
            given=repr(type(provenance).__name__),
        )
    requested = clean_token(requested_namespace)
    if requested is not None:
        if requested in GOVERNED_EVIDENCE_NAMESPACES:
            return refuse_synthetic_write_into_governed_namespace(requested)
        if requested != SYNTHETIC_STORE_PARTITION:
            return invalid(
                "requested_namespace",
                "a synthetic persist targets only the synthetic-tainted store partition",
                given=requested,
                legal=[SYNTHETIC_STORE_PARTITION],
            )
    return Ok(
        SyntheticStorePartition(
            namespace=SYNTHETIC_STORE_PARTITION,
            relative_path=store_provenance_relative_path(provenance),
            provenance=provenance,
        )
    )


def refuse_synthetic_write_into_governed_namespace(namespace: object) -> TypedRefusal:
    """Refuse a ``world = simulated`` synthetic write into a governed/live namespace (AC6, AR-33).

    A non-live world never writes the live evidence namespace, and ``world =
    simulated`` writes are routed to the synthetic-tainted partition only. A caller
    aiming a synthetic write at the live or governed-evidence namespace is a typed
    ``policy rejection`` — returned, never raised (AR-33, B-7, FM-7).
    """
    token = clean_token(namespace)
    named = token if token is not None else repr(namespace)
    return policy(
        "namespace",
        "a world=simulated synthetic write never enters the live or governed-evidence "
        "namespace; it is routed to the synthetic-tainted store partition only "
        "(AR-33, B-7, FM-7)",
        requested_namespace=named,
        synthetic_partition=SYNTHETIC_STORE_PARTITION,
        governed_namespaces=sorted(GOVERNED_EVIDENCE_NAMESPACES),
        world=STORE_WORLD,
    )


# --- world derivation from store provenance (AC2) ----------------------------


def derive_world_from_store_provenance(source: object) -> Result[World]:
    """Derive ``world = simulated`` from a store taint, never caller-declared (AC2, B-7).

    ``source`` is a :class:`SyntheticStoreProvenance`, a :class:`SyntheticStorePartition`,
    or a store-read mapping carrying ``origin = synthetic`` (or ``data_provenance =
    synthetic-tainted``). World is provenance-derived: a caller-declared non-simulated
    ``world`` on the source is ``invalid input`` — a caller may not declare world (B-7).
    """
    taint = _coerce_store_taint(source)
    if is_refusal(taint):
        return taint
    declared = taint.value.get("world")
    if declared is not None:
        token = clean_token(declared)
        if token != World.SIMULATED.value:
            return invalid(
                "world",
                "world is derived from store provenance and must be simulated for "
                "synthetic-tainted data; a caller may not declare world (B-7, FM-3)",
                given=repr(declared),
                derived=World.SIMULATED.value,
            )
    return Ok(World.SIMULATED)


@dataclass(frozen=True, slots=True)
class StoreReadClassification:
    """The classification of a run that reads store-persisted synthetic data (AC2).

    World is ``simulated`` (provenance-derived); the read is inadmissible as governed
    evidence until GAP-0048; the permittable claim classes are infra-stress and
    logic-smoke only. :meth:`refuse_governed_evidence` returns the policy rejection.
    """

    world: str
    data_provenance: str
    governed_evidence_admissible: bool
    permittable_claim_classes: tuple[str, ...]
    gap: str

    def refuse_governed_evidence(self) -> Result[World]:
        """The ``policy rejection`` a governed-evidence use of this read returns (AC2, SC-06)."""
        return refuse_governed_evidence_use(self.world)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content."""
        return {
            "class": "qmb-synthetic-store-read",
            "data_provenance": self.data_provenance,
            "gap": self.gap,
            "governed_evidence_admissible": self.governed_evidence_admissible,
            "permittable_claim_classes": list(self.permittable_claim_classes),
            "world": self.world,
        }


def read_synthetic_store(source: object) -> Result[StoreReadClassification]:
    """Classify a run that reads store-persisted synthetic data (AC2, SC-06, B-7).

    Derives ``world = simulated`` from provenance and returns the read classification:
    a ``policy rejection`` for governed evidence until GAP-0048, permittable claim
    classes infra-stress and logic-smoke only. Use
    :meth:`StoreReadClassification.refuse_governed_evidence` for the refusal itself.
    """
    world = derive_world_from_store_provenance(source)
    if is_refusal(world):
        return world
    return Ok(
        StoreReadClassification(
            world=World.SIMULATED.value,
            data_provenance=STORE_DATA_PROVENANCE,
            governed_evidence_admissible=False,
            permittable_claim_classes=STORE_PERMITTED_CLAIM_CLASSES,
            gap=GAP_0048,
        )
    )


# --- the clock/adapter binding refusal (AC3) ---------------------------------


def resolve_store_clock_binding(
    source: object,
    *,
    clock: object,
    adapters: object = (),
) -> Result[World]:
    """Bind a clock/adapters to synthetic-tainted store data — B-7 wins over B-2 (AC3, FM-3).

    A ``replay`` clock — or any replay/live adapter — bound to synthetic-tainted store
    data is ``invalid input``: world is provenance-derived and a replay clock (or a
    replay/live adapter) implies real recorded provenance (B-2), which B-7 overrules
    (a caller may not declare world). A ``simulated`` clock with no non-simulated
    adapter derives ``world = simulated``.
    """
    world = derive_world_from_store_provenance(source)
    if is_refusal(world):
        return world
    clock_token = clean_token(clock)
    if clock_token == CLOCK_REPLAY:
        return refuse_replay_clock_on_synthetic_store(clock_token)
    adapter_tokens = _coerce_adapter_tokens(adapters)
    if is_refusal(adapter_tokens):
        return adapter_tokens
    bound = sorted(adapter_tokens.value & _NON_SIMULATED_ADAPTERS)
    if bound:
        return invalid(
            "adapters",
            "a replay/live adapter bound to synthetic-tainted store data is invalid input; "
            "world is provenance-derived and B-7 wins over B-2 (FM-3, DEC-0164)",
            adapters=bound,
            data_provenance=STORE_DATA_PROVENANCE,
            legal_clock=CLOCK_SIMULATED,
        )
    if clock_token != CLOCK_SIMULATED:
        return invalid(
            "clock",
            "synthetic-tainted store data derives world=simulated; only a simulated clock "
            "binds it (B-7, FM-3)",
            given=repr(clock),
            legal=[CLOCK_SIMULATED],
        )
    return Ok(World.SIMULATED)


def refuse_replay_clock_on_synthetic_store(clock: object) -> TypedRefusal:
    """Refuse a replay clock bound to synthetic-tainted store data (AC3, B-2/B-7, FM-3).

    World is provenance-derived: a ``replay`` clock bound to synthetic-tainted store
    data is a typed ``invalid input`` — B-7 (a caller may not declare world) and B-2
    (the replay clock reads recorded data) both point at the same rejection, and B-7
    wins (DEC-0164). Returned, never raised.
    """
    token = clean_token(clock)
    return invalid(
        "clock",
        "a replay clock bound to synthetic-tainted store data is invalid input; world is "
        "provenance-derived and B-7 wins over B-2 (FM-3, DEC-0164)",
        clock=token if token is not None else repr(clock),
        data_provenance=STORE_DATA_PROVENANCE,
        legal=[CLOCK_SIMULATED],
    )


# --- non-promotability — the closed synthetic backdoor (AC4) -----------------


def synthetic_is_promotable() -> bool:
    """Always ``False`` — a synthetic artifact is non-promotable by construction (R4, AC4)."""
    return SYNTHETIC_IS_PROMOTABLE


def refuse_synthetic_load(target_world: object) -> Result[None]:
    """Guard loading synthetic data into a world=replay or world=live context (AC4, R4, R8).

    Loading store-persisted synthetic data into a ``world = replay`` or ``world =
    live`` context is a typed ``policy rejection`` — the synthetic backdoor (LEAN's
    indistinguishable-data gap) is closed by construction. A ``world = simulated``
    target is the synthetic data's legal home and passes through.
    """
    coerced = _coerce_world(target_world)
    if is_refusal(coerced):
        return coerced
    world = coerced.value
    if world is World.SIMULATED:
        return Ok(None)
    return policy(
        "world",
        "synthetic data may never be loaded into a world=replay or world=live context; "
        "it is store-tainted world=simulated and non-promotable — the synthetic backdoor is "
        "closed by construction (R4, R8, B-7)",
        target_world=world.value,
        synthetic_world=STORE_WORLD,
        is_promotable=SYNTHETIC_IS_PROMOTABLE,
    )


def refuse_promote_synthetic(artifact: object = None) -> TypedRefusal:
    """Refuse promoting a synthetic artifact toward live money (AC4, R4, R8).

    A synthetic artifact is non-promotable by construction: any attempt to promote it
    toward live money is a typed ``policy rejection`` — returned, never raised. L20
    stands; nothing synthetic reaches the live money path (R4, R8).
    """
    token = clean_token(artifact)
    context: dict[str, object] = {
        "is_promotable": SYNTHETIC_IS_PROMOTABLE,
        "origin": SYNTHETIC_ORIGIN,
        "world": STORE_WORLD,
    }
    if token is not None:
        context["artifact"] = token
    return policy(
        "promotion",
        "a synthetic artifact is non-promotable; promoting store-tainted synthetic data "
        "toward live money is refused by construction — the synthetic backdoor is closed "
        "(R4, R8, L20)",
        **context,
    )


# --- the procedure-ephemeral contrast (AC5) ----------------------------------


@dataclass(frozen=True, slots=True)
class EphemeralPerturbationTaint:
    """A procedure-ephemeral perturbation that creates NO store partition (AC5, B-7).

    A block-bootstrap or B-14 trade-shuffle that perturbs a ``world = replay`` run
    without persisting a synthetic series stays ``world = replay``: no synthetic store
    partition is created, provenance is ``procedure-ephemeral``, and the claim class is
    robustness-only — never edge, never admission evidence. The procedure identity and
    seed enter the CT-32 label (:meth:`label_content`).
    """

    procedure: str
    seed: int
    world: str
    data_provenance: str
    claim_class: str
    creates_store_partition: bool

    def label_content(self) -> dict[str, object]:
        """The procedure identity + seed that enter the CT-32 label (AC5, B-7)."""
        return {"procedure": self.procedure, "seed": self.seed}

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content."""
        return {
            "claim_class": self.claim_class,
            "class": _EPHEMERAL_TAINT_CLASS,
            "creates_store_partition": self.creates_store_partition,
            "data_provenance": self.data_provenance,
            "procedure": self.procedure,
            "seed": self.seed,
            "world": self.world,
        }


def procedure_ephemeral_taint(
    procedure: object, seed: object
) -> Result[EphemeralPerturbationTaint]:
    """Classify a procedure-ephemeral perturbation that persists no synthetic series (AC5, B-7).

    A block-bootstrap or trade-shuffle perturbation of a ``world = replay`` run that
    never persists a synthetic series into a data room creates NO store partition, so
    world stays ``replay``, provenance is ``procedure-ephemeral``, and the claim class
    is robustness-only. The procedure identity and seed enter the CT-32 label — never
    an edge or admission claim (B-7, L20).
    """
    token = clean_token(procedure)
    if token is None:
        return invalid(
            "procedure",
            "a procedure-ephemeral taint names the perturbation procedure",
            given=repr(procedure),
        )
    seed_v = _non_negative_int(seed, "seed")
    if is_refusal(seed_v):
        return seed_v
    return Ok(
        EphemeralPerturbationTaint(
            procedure=token,
            seed=seed_v.value,
            world=World.REPLAY.value,
            data_provenance=PROVENANCE_PROCEDURE_EPHEMERAL,
            claim_class=CLAIM_ROBUSTNESS,
            creates_store_partition=False,
        )
    )


def refuse_ephemeral_as_admission_evidence(procedure: object) -> TypedRefusal:
    """Refuse citing a procedure-ephemeral robustness run as admission evidence (AC5, B-7).

    A procedure-ephemeral perturbation's claim class is robustness-only — never edge,
    never admission evidence. Citing it as admission evidence is a typed ``policy
    rejection`` — returned, never raised (B-7, L20).
    """
    token = clean_token(procedure)
    named = token if token is not None else repr(procedure)
    return policy(
        "claim_class",
        "a procedure-ephemeral perturbation is robustness-only; it is never edge and never "
        "admission evidence (AC5, B-7, L20)",
        procedure=named,
        claim_class=CLAIM_ROBUSTNESS,
        world=World.REPLAY.value,
        data_provenance=PROVENANCE_PROCEDURE_EPHEMERAL,
    )


# --- identity ----------------------------------------------------------------


def store_taint_identity() -> dict[str, object]:
    """Identity-bearing store-taint-contract fields. Package SemVer is omitted (B-13)."""
    return {
        "governed_evidence_namespaces": tuple(sorted(GOVERNED_EVIDENCE_NAMESPACES)),
        "store_artifact_kinds": STORE_ARTIFACT_KINDS,
        "store_data_provenance": STORE_DATA_PROVENANCE,
        "store_permitted_claim_classes": STORE_PERMITTED_CLAIM_CLASSES,
        "store_provenance_artifact_name": STORE_PROVENANCE_ARTIFACT_NAME,
        "store_provenance_class": STORE_PROVENANCE_CLASS,
        "store_provenance_format_version": STORE_PROVENANCE_FORMAT_VERSION,
        "store_world": STORE_WORLD,
        "synthetic_governed_evidence_unlocks_at": GAP_0048,
        "synthetic_is_promotable": SYNTHETIC_IS_PROMOTABLE,
        "synthetic_store_partition": SYNTHETIC_STORE_PARTITION,
    }


# --- internals ---------------------------------------------------------------


def _coerce_store_taint(source: object) -> Result[Mapping[str, object]]:
    """A store taint as a mapping: a provenance record, a partition, or a store read."""
    if isinstance(source, SyntheticStoreProvenance):
        return Ok(source.fp1_identity())
    if isinstance(source, SyntheticStorePartition):
        return Ok(source.provenance.fp1_identity())
    if isinstance(source, Mapping):
        body = cast("Mapping[str, object]", source)
        origin = clean_token(body.get("origin"))
        provenance = clean_token(body.get("data_provenance"))
        if origin == SYNTHETIC_ORIGIN or provenance == STORE_DATA_PROVENANCE:
            return Ok(body)
        return invalid(
            "source",
            "a store read carries origin=synthetic or data_provenance=synthetic-tainted "
            "to derive world; world is provenance-derived (B-7)",
            origin=repr(body.get("origin")),
            data_provenance=repr(body.get("data_provenance")),
        )
    return invalid(
        "source",
        "world derivation reads a SyntheticStoreProvenance, a SyntheticStorePartition, or a "
        "synthetic store-read mapping",
        given=repr(type(source).__name__),
    )


def _coerce_world(source: object) -> Result[World]:
    """Coerce a World or a world token to a World member."""
    if isinstance(source, World):
        return Ok(source)
    token = clean_token(source)
    if token is not None:
        for member in World:
            if member.value == token:
                return Ok(member)
        return invalid(
            "world",
            "world is one of live, replay, simulated (B-7)",
            given=token,
            legal=[member.value for member in World],
        )
    return invalid(
        "world",
        "a target world is a World or a world token",
        given=repr(type(source).__name__),
    )


def _coerce_adapter_tokens(value: object) -> Result[frozenset[str]]:
    """A set of adapter provenance tokens (replay/live/simulated), or empty."""
    if value is None:
        return Ok(frozenset())
    if isinstance(value, str):
        token = clean_token(value)
        return Ok(frozenset() if token is None else frozenset({token}))
    if isinstance(value, (list, tuple, set, frozenset)):
        tokens: set[str] = set()
        for item in cast("Sequence[object]", value):
            token = clean_token(item)
            if token is None:
                return invalid(
                    "adapters",
                    "each adapter provenance is a non-empty token",
                    given=repr(item),
                )
            tokens.add(token)
        return Ok(frozenset(tokens))
    return invalid(
        "adapters",
        "adapters are a token or a sequence of provenance tokens",
        given=repr(type(value).__name__),
    )


def _fingerprint_token(value: object) -> Result[str]:
    """The generator-config fp1 token a store taint cites (AR-14)."""
    if isinstance(value, Fingerprint):
        return Ok(value.value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "config_fp1",
            "the store taint cites the generator-config fp1 fingerprint (AR-14)",
            given=repr(value),
        )
    return Ok(token)


def _non_negative_int(value: object, field: str) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return invalid(field, f"{field} is a non-negative exact integer", given=repr(value))
    return Ok(value)
