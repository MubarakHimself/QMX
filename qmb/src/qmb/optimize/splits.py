"""Train/test split discipline with fingerprinted split manifests (B-8, OPT-9).

A parameter-optimization Study names a **training split manifest** and a
**testing split manifest**, each by CT-12 fingerprint. Every trial runs twice on
the identical parameter set: the **training run computes the objective**, and the
**testing run records its measures without contributing to the objective** — the
out-of-sample result a reader judges overfit from, while the sealed holdout stays
untouched (OPT-9, B-8). "train" and "test" are **display aliases** for two such
manifests; the aliases are never substituted for the fingerprints, and the trial
label carries both fingerprints verbatim (DEC-0169).

What this module owns, and what it defers to the modules that already own it:

* **The Study-level split declaration** — :class:`StudySplits` names the two split
  fingerprints, validated at Study creation and materialized as identity-bearing
  content of the resolved run-config (never a code edit — OPT-2 discipline,
  mirroring the search space and the criteria).
* **The per-trial two-run plan** — :func:`plan_trial_runs` pairs one objective-
  bearing training run with one recorded-only testing run over one shared
  parameter-set fingerprint (:class:`TrialSplitRun`, :class:`TrialSplitPlan`), and
  :func:`admit_objective_run` refuses letting a testing run feed the objective.
* **Split-read enforcement (AC3)** is qmf-data's: :func:`serve_split_read`
  composes the CT-12 :class:`~qmf.data.HoldoutSeal` guard (the ~12-month seal and
  calendar-in-band rules) with the :class:`~qmf.data.SplitManifest` record
  partition (embargo + knowledge-time), then holds the sealed holdout out of
  default access (:func:`admit_default_split_access`).
* **The optimistic-taint / no-edge / no-split-budget rule (AC4)** is B-6's:
  :func:`refuse_split_edge_or_budget` delegates to
  :func:`~qmb.execution.ports.refuse_optimistic_edge_claim`.
* **The world=replay-only rule (AC5)** is B-7's: :func:`admit_study_world`
  delegates to
  :func:`~qmb.execution.ports.refuse_store_synthetic_governed_evidence`, and
  :class:`StudySplits` itself refuses any non-replay split at creation.
* **Warm-up length and the trading-only evidence range (AC6)** are B-2's:
  :func:`study_warmup` reads the split manifest's declared embargo as an AD-22
  observation count (never a Duration), and :func:`trading_evidence_range` is the
  trading-interval-only span re-exported from the in-loop warm-up module.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.data.seal import HoldoutSeal, ReadBoundary
from qmf.data.splits import SegmentRole, SplitManifest

from qmb._refuse import clean_token, invalid, policy
from qmb.execution.ports import (
    CLAIMS_EDGE,
    SPENDS_SPLIT_BUDGET,
    TAINT_OPTIMISTIC,
    refuse_optimistic_edge_claim,
    refuse_store_synthetic_governed_evidence,
)
from qmb.runloop.warmup import (
    SplitEmbargo,
    embargo_from_config,
    trading_evidence_range,
)

__all__ = [
    "ALIASES_ARE_DISPLAY_ONLY",
    "DEFAULT_ACCESS_ROLES",
    "OBJECTIVE_SPLIT_ALIAS",
    "SEALED_HOLDOUT_ROLE",
    "SPLIT_ALIASES",
    "SPLIT_RUN_CLAIMS_EDGE",
    "SPLIT_RUN_SPENDS_BUDGET",
    "SPLIT_RUN_TAINT",
    "STUDIES_RUN_REPLAY_ONLY",
    "STUDY_SPLITS_CLASS",
    "STUDY_SPLITS_FORMAT_VERSION",
    "STUDY_SPLITS_KEY",
    "TEST_ALIAS",
    "TRAIN_ALIAS",
    "TRIAL_SPLIT_PLAN_CLASS",
    "TRIAL_SPLIT_RUN_CLASS",
    "SplitEmbargo",
    "StudySplits",
    "TrialSplitPlan",
    "TrialSplitRun",
    "admit_default_split_access",
    "admit_objective_run",
    "admit_study_world",
    "coerce_study_splits",
    "plan_trial_runs",
    "refuse_split_edge_or_budget",
    "serve_split_read",
    "study_splits_identity",
    "study_warmup",
    "study_warmup_from_config",
    "trading_evidence_range",
]

STUDY_SPLITS_CLASS: Final[str] = "qmb-study-splits"
STUDY_SPLITS_FORMAT_VERSION: Final[int] = 1
TRIAL_SPLIT_RUN_CLASS: Final[str] = "qmb-trial-split-run"
TRIAL_SPLIT_PLAN_CLASS: Final[str] = "qmb-trial-split-plan"

# The resolved-run-config key the validated split pair is materialized under, so a
# Study's train/test split declaration rides in the run-config's fp1 identity —
# declared as config, never a code edit (OPT-2, mirroring the search space).
STUDY_SPLITS_KEY: Final[str] = "study_splits"

# "train"/"test" are DISPLAY aliases for two split-manifest fingerprints; the
# aliases are never substituted for the fingerprints in identity (B-8, DEC-0169).
TRAIN_ALIAS: Final[str] = "train"
TEST_ALIAS: Final[str] = "test"
SPLIT_ALIASES: Final[tuple[str, ...]] = (TRAIN_ALIAS, TEST_ALIAS)
ALIASES_ARE_DISPLAY_ONLY: Final[bool] = True

# The objective is computed on the training split only; the testing split is
# recorded for overfit judgment and contributes nothing to the objective (OPT-9).
OBJECTIVE_SPLIT_ALIAS: Final[str] = TRAIN_ALIAS

# Studies run world=replay only in V1; a store-tainted synthetic read resolves to
# world=simulated and is a policy rejection (B-7, SC-06).
STUDIES_RUN_REPLAY_ONLY: Final[bool] = True

# Every split-trial fill carries the optimistic taint, spends no split budget, and
# claims no edge until GAP-0048 (B-6, SC-06) — the ports module owns the rule.
SPLIT_RUN_TAINT: Final[str] = TAINT_OPTIMISTIC
SPLIT_RUN_SPENDS_BUDGET: Final[bool] = SPENDS_SPLIT_BUDGET
SPLIT_RUN_CLAIMS_EDGE: Final[bool] = CLAIMS_EDGE

# The default-access research split roster excludes the sealed holdout; only the
# authorized final look ever touches sealed-test (CT-12, AR-16 seal law).
DEFAULT_ACCESS_ROLES: Final[tuple[SegmentRole, ...]] = (
    SegmentRole.TRAIN,
    SegmentRole.VALIDATION,
)
SEALED_HOLDOUT_ROLE: Final[SegmentRole] = SegmentRole.SEALED_TEST


def study_splits_identity() -> dict[str, object]:
    """Identity-bearing split-declaration schema fields. Package SemVer is omitted."""
    return {
        "aliases_are_display_only": ALIASES_ARE_DISPLAY_ONLY,
        "class": STUDY_SPLITS_CLASS,
        "format_version": STUDY_SPLITS_FORMAT_VERSION,
        "objective_split_alias": OBJECTIVE_SPLIT_ALIAS,
        "run_config_key": STUDY_SPLITS_KEY,
        "split_aliases": SPLIT_ALIASES,
        "studies_run_replay_only": STUDIES_RUN_REPLAY_ONLY,
    }


# --- the Study-level split declaration ---------------------------------------


@dataclass(frozen=True, slots=True)
class StudySplits:
    """A Study's validated training/testing split pair, named by fingerprint (B-8, OPT-9).

    ``train_split`` and ``test_split`` are CT-12 split-manifest ``fp1`` fingerprints.
    The objective is computed on the training split; the testing split is recorded
    for overfit judgment. ``world`` is always ``replay`` — a Study over a
    store-tainted synthetic (``world = simulated``) split is a policy rejection.
    "train"/"test" are display aliases only (:meth:`display_aliases`); identity
    carries the fingerprints, never the aliases.
    """

    train_split: Fingerprint
    test_split: Fingerprint
    world: World = World.REPLAY

    @classmethod
    def try_create(
        cls,
        train_split: object,
        test_split: object,
        *,
        world: object = World.REPLAY,
    ) -> Result[StudySplits]:
        """Admit a training/testing split pair at Study creation (OPT-9, AC5).

        Each split is a :class:`~qmf.core.Fingerprint`, an ``fp1`` token, or a CT-12
        :class:`~qmf.data.SplitManifest` (its ``fingerprint`` is taken and its world
        checked). ``world`` must be ``replay``; a simulated split — declared, or
        carried by a manifest — is a policy rejection (B-7, SC-06). The two splits
        must be distinct: naming one fingerprint for both leaves no out-of-sample
        content.
        """
        resolved_world = _require_replay_world(world, "world")
        if is_refusal(resolved_world):
            return resolved_world
        train = _coerce_split(train_split, "train_split")
        if is_refusal(train):
            return train
        test = _coerce_split(test_split, "test_split")
        if is_refusal(test):
            return test
        if train.value == test.value:
            return invalid(
                "test_split",
                "a Study's training and testing splits are distinct manifests; naming "
                "one fingerprint for both leaves no out-of-sample content to judge "
                "overfit from (OPT-9, B-8)",
                given=train.value.value,
            )
        return Ok(cls(train_split=train.value, test_split=test.value, world=resolved_world.value))

    @property
    def objective_split(self) -> Fingerprint:
        """The split the objective is computed on — the training split (OPT-9)."""
        return self.train_split

    @property
    def recorded_split(self) -> Fingerprint:
        """The split recorded without contributing to the objective — the testing split."""
        return self.test_split

    def split_for(self, alias: object) -> Result[Fingerprint]:
        """Resolve a display alias to its split fingerprint (``train``/``test``)."""
        token = clean_token(alias)
        if token == TRAIN_ALIAS:
            return Ok(self.train_split)
        if token == TEST_ALIAS:
            return Ok(self.test_split)
        return invalid(
            "alias",
            "a split alias is the display token train or test; it resolves to a "
            "manifest fingerprint and is never substituted for it (B-8)",
            given=repr(alias),
            allowed=list(SPLIT_ALIASES),
        )

    def alias_for(self, split: object) -> Result[str]:
        """The display alias of a split fingerprint. Display only, never identity."""
        resolved = _coerce_split(split, "split")
        if is_refusal(resolved):
            return resolved
        if resolved.value == self.train_split:
            return Ok(TRAIN_ALIAS)
        if resolved.value == self.test_split:
            return Ok(TEST_ALIAS)
        return invalid(
            "split",
            "the fingerprint is neither this Study's training nor its testing split",
            given=resolved.value.value,
        )

    def display_aliases(self) -> dict[str, str]:
        """The display-only alias map. Never part of :meth:`fp1_identity` (B-8)."""
        return {TRAIN_ALIAS: self.train_split.value, TEST_ALIAS: self.test_split.value}

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Both fingerprints ride; aliases never do."""
        return {
            "class": STUDY_SPLITS_CLASS,
            "format_version": STUDY_SPLITS_FORMAT_VERSION,
            "objective_split_alias": OBJECTIVE_SPLIT_ALIAS,
            "test_split_fp1": self.test_split.value,
            "train_split_fp1": self.train_split.value,
            "world": self.world.value,
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. Same split pair reproduces it (NFR-03)."""
        return fingerprint(self.fp1_identity())

    def run_config_layer(self) -> dict[str, object]:
        """The identity-bearing config layer materializing this split pair (OPT-2)."""
        return {STUDY_SPLITS_KEY: self.fp1_identity()}


def coerce_study_splits(declaration: object) -> Result[StudySplits]:
    """Validate a Study's train/test split declaration at Study creation (OPT-9).

    ``declaration`` is an already-built :class:`StudySplits`, or a mapping carrying
    ``train``/``test`` (or ``train_split``/``test_split``) split fingerprints and an
    optional ``world``. A missing split, a non-replay world, or two equal splits is
    refused here — up front, never at trial time.
    """
    if isinstance(declaration, StudySplits):
        return Ok(declaration)
    if not isinstance(declaration, Mapping):
        return invalid(
            "declaration",
            "a Study split declaration is a StudySplits or a mapping naming a "
            "`train` and a `test` split-manifest fingerprint",
            given=repr(type(declaration).__name__),
        )
    body = cast("Mapping[str, object]", declaration)
    train = _pick(body, "train", "train_split")
    test = _pick(body, "test", "test_split")
    if train is None or test is None:
        return invalid(
            "declaration",
            "a Study split declaration names a `train` and a `test` split-manifest "
            "fingerprint (OPT-9)",
            given=sorted(str(key) for key in body),
        )
    return StudySplits.try_create(train, test, world=body.get("world", World.REPLAY))


# --- the per-trial two-run plan ----------------------------------------------


@dataclass(frozen=True, slots=True)
class TrialSplitRun:
    """One of a trial's two split runs: objective-bearing training, or recorded testing.

    ``split_fp1`` is the CT-12 manifest fingerprint the run reads (identity-bearing).
    ``split_alias`` is the display token (``train``/``test``) and is **never**
    substituted for the fingerprint in identity. ``contributes_to_objective`` is true
    only for the training run; the testing run records its measures and contributes
    nothing (OPT-9). Every fill carries the ``optimistic`` taint until GAP-0048 (B-6).
    """

    split_alias: str
    split_fp1: Fingerprint
    contributes_to_objective: bool
    world: World = World.REPLAY
    taint: str = TAINT_OPTIMISTIC

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The fingerprint rides; the alias never does."""
        return {
            "class": TRIAL_SPLIT_RUN_CLASS,
            "contributes_to_objective": self.contributes_to_objective,
            "split_fp1": self.split_fp1.value,
            "taint": self.taint,
            "world": self.world.value,
        }


@dataclass(frozen=True, slots=True)
class TrialSplitPlan:
    """One trial's two-run plan over a shared parameter set (OPT-9, B-8).

    Both runs execute the identical parameter set (``parameter_set_fp1``); the
    training run computes the objective and the testing run records its measures
    without contributing to it. The trial label (:meth:`trial_label`) carries both
    split fingerprints, with the aliases living only in the display block.
    """

    splits: StudySplits
    parameter_set_fp1: Fingerprint
    train_run: TrialSplitRun
    test_run: TrialSplitRun

    @property
    def objective_run(self) -> TrialSplitRun:
        """The run whose objective is computed — the training run (OPT-9)."""
        return self.train_run

    @property
    def recorded_run(self) -> TrialSplitRun:
        """The run recorded without contributing to the objective — the testing run."""
        return self.test_run

    @property
    def runs(self) -> tuple[TrialSplitRun, TrialSplitRun]:
        """Both runs of the trial, training first."""
        return (self.train_run, self.test_run)

    def trial_label(self) -> dict[str, object]:
        """The trial label content: both split fingerprints, aliases display-only (AC2).

        Both ``train_split_fp1`` and ``test_split_fp1`` are identity-bearing; the
        ``display.aliases`` map is human-facing and is never substituted for the
        fingerprints (B-8, DEC-0169).
        """
        return {
            "class": TRIAL_SPLIT_PLAN_CLASS,
            "display": {"aliases": self.splits.display_aliases()},
            "format_version": STUDY_SPLITS_FORMAT_VERSION,
            "objective_split_fp1": self.splits.train_split.value,
            "parameter_set_fp1": self.parameter_set_fp1.value,
            "test_split_fp1": self.splits.test_split.value,
            "train_split_fp1": self.splits.train_split.value,
            "world": self.splits.world.value,
        }

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. The display aliases are omitted."""
        return {
            "class": TRIAL_SPLIT_PLAN_CLASS,
            "format_version": STUDY_SPLITS_FORMAT_VERSION,
            "parameter_set_fp1": self.parameter_set_fp1.value,
            "splits": self.splits.fp1_identity(),
            "test_run": self.test_run.fp1_identity(),
            "train_run": self.train_run.fp1_identity(),
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint. Same splits + parameter set reproduce it (NFR-03)."""
        return fingerprint(self.fp1_identity())


def plan_trial_runs(splits: object, parameter_set: object) -> Result[TrialSplitPlan]:
    """Plan one trial's two runs over the identical parameter set (OPT-9, B-8).

    ``splits`` is a :class:`StudySplits` (or a mapping coerced through
    :func:`coerce_study_splits`); ``parameter_set`` is the shared parameter-set
    ``fp1`` — a :class:`~qmf.core.Fingerprint`, an ``fp1`` token, or any object with
    an ``fp1_identity`` (fingerprinted here). The plan pairs one objective-bearing
    training run with one recorded-only testing run; both cite the one parameter-set
    fingerprint, so "identical params" is identity, not convention.
    """
    resolved = coerce_study_splits(splits)
    if is_refusal(resolved):
        return resolved
    study = resolved.value
    params = _coerce_parameter_set(parameter_set)
    if is_refusal(params):
        return params
    train_run = TrialSplitRun(
        split_alias=TRAIN_ALIAS,
        split_fp1=study.train_split,
        contributes_to_objective=True,
        world=study.world,
    )
    test_run = TrialSplitRun(
        split_alias=TEST_ALIAS,
        split_fp1=study.test_split,
        contributes_to_objective=False,
        world=study.world,
    )
    return Ok(
        TrialSplitPlan(
            splits=study,
            parameter_set_fp1=params.value,
            train_run=train_run,
            test_run=test_run,
        )
    )


def admit_objective_run(run: object) -> Result[TrialSplitRun]:
    """Admit a run to feed the objective only when it is the training run (OPT-9).

    A testing run records its measures without contributing to the objective;
    letting it feed the objective would spend the out-of-sample budget on scoring,
    so it is a policy rejection (OPT-9, B-8).
    """
    if not isinstance(run, TrialSplitRun):
        return invalid(
            "run",
            "the objective is admitted from a TrialSplitRun",
            given=repr(type(run).__name__),
        )
    if not run.contributes_to_objective:
        return policy(
            "run",
            "only the training run computes the objective; the testing run records "
            "its measures without contributing to the objective (OPT-9, B-8)",
            split_alias=run.split_alias,
            split_fp1=run.split_fp1.value,
        )
    return Ok(run)


# --- AC3: split-read enforcement (delegated to qmf-data) ---------------------


def admit_default_split_access(role: object) -> Result[SegmentRole]:
    """Admit a research read to a segment role under default access (AC3, seal law).

    ``train`` and ``validation`` are the default-access roster; the sealed holdout
    (``sealed-test``) is excluded from default access — only the one authorized
    final look ever touches it — so a default read of it is a policy rejection
    (CT-12, AR-16 seal law, DEC-0119).
    """
    resolved = _coerce_role(role)
    if is_refusal(resolved):
        return resolved
    if resolved.value == SEALED_HOLDOUT_ROLE:
        return policy(
            "role",
            "the sealed holdout is excluded from default access; only the one "
            "authorized final look touches sealed-test, and it does not unseal it "
            "(CT-12, AR-16 seal law, DEC-0119)",
            given=resolved.value.value,
            default_access=[member.value for member in DEFAULT_ACCESS_ROLES],
        )
    return Ok(resolved.value)


def serve_split_read(
    *,
    seal: object,
    position: object,
    boundary: object = ReadBoundary.RESEARCH_DOOR,
    manifest: object = None,
    record: object = None,
) -> Result[object]:
    """Serve one split read through qmf-data's boundary enforcement (AC3).

    Composes what qmf-data already owns: the CT-12 :class:`~qmf.data.HoldoutSeal`
    guard enforces the ~12-month seal and the calendar-in-band rule at the named
    :class:`~qmf.data.ReadBoundary`; when a ``manifest`` and a ``record`` are given,
    :meth:`~qmf.data.SplitManifest.partition_record` enforces the embargo and
    knowledge-time rules and assigns the segment role, which is then held to
    :func:`admit_default_split_access` so the sealed holdout stays out of default
    access. Returns the admitted :class:`~qmf.data.SegmentRole` when a record is
    partitioned, else the guarded read position. Any refusal surfaces verbatim.
    """
    if not isinstance(seal, HoldoutSeal):
        return invalid(
            "seal",
            "a split read is guarded by a CT-12 HoldoutSeal (the ~12-month seal law)",
            given=repr(type(seal).__name__),
        )
    guarded = seal.guard_read(position, boundary=boundary)
    if is_refusal(guarded):
        return guarded
    if record is None:
        guarded_position: object = position
        return Ok(guarded_position)
    if not isinstance(manifest, SplitManifest):
        return invalid(
            "manifest",
            "partitioning a record by embargo and knowledge-time needs a CT-12 SplitManifest",
            given=repr(type(manifest).__name__),
        )
    partitioned = manifest.partition_record(record)
    if is_refusal(partitioned):
        return partitioned
    admitted = admit_default_split_access(partitioned.value)
    if is_refusal(admitted):
        return admitted
    admitted_role: object = admitted.value
    return Ok(admitted_role)


# --- AC4: optimistic taint, no edge, no split budget -------------------------


def refuse_split_edge_or_budget(
    *,
    taint: object = TAINT_OPTIMISTIC,
    claims_edge: bool = False,
    spends_split_budget: bool = False,
) -> Result[None]:
    """Every split-trial fill is optimistic, spends no split budget, claims no edge (AC4).

    Delegates to the B-6 rule (:func:`~qmb.execution.ports.refuse_optimistic_edge_claim`):
    a non-optimistic taint is an invalid input, and claiming edge or spending split
    budget under the optimistic taint is a policy rejection until GAP-0048 (SC-06, FM-9).
    """
    return refuse_optimistic_edge_claim(
        taint=taint,
        claims_edge=claims_edge,
        spends_split_budget=spends_split_budget,
    )


# --- AC5: world=replay only --------------------------------------------------


def admit_study_world(source: object) -> Result[World]:
    """Admit a Study's world; a store-tainted synthetic read is refused (AC5, B-7).

    Delegates to :func:`~qmb.execution.ports.refuse_store_synthetic_governed_evidence`:
    a run that would resolve to ``world = simulated`` (any read of store-persisted
    synthetic data) is a policy rejection — Studies run ``world = replay`` only in V1
    (B-7, SC-06). ``source`` is a :class:`~qmb.config.compiler.ResolvedRunConfig`, a
    :class:`~qmf.core.World`, or a data-provenance token.
    """
    return refuse_store_synthetic_governed_evidence(source)


# --- AC6: warm-up length and trading-only evidence range ---------------------


def study_warmup(observation_count: object, *, split_fp1: object = None) -> Result[SplitEmbargo]:
    """Warm-up length is the split manifest's declared embargo observation count (AC6).

    An AD-22 completed-observation count, never a Duration; the loop adds no second
    window (B-2, CT-12). ``split_fp1`` optionally cites the split manifest the
    embargo belongs to. Delegates to the in-loop warm-up module, which owns the
    Duration ban and the observation-count discipline.
    """
    return SplitEmbargo.try_create(observation_count, split_fp1)


def study_warmup_from_config(config: object) -> Result[SplitEmbargo | None]:
    """Read the split-manifest embargo observation count from a resolved run-config (AC6)."""
    return embargo_from_config(config)


# --- coercion helpers --------------------------------------------------------


def _coerce_split(value: object, field: str) -> Result[Fingerprint]:
    """Resolve a split reference to its manifest fingerprint, checking world (AC5)."""
    if isinstance(value, SplitManifest):
        world = _require_replay_world(value.world, field)
        if is_refusal(world):
            return world
        return Ok(value.fingerprint)
    if isinstance(value, Fingerprint):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            field,
            "a Study split is named by CT-12 manifest fingerprint (an fp1 token, a "
            "Fingerprint, or a SplitManifest) (OPT-9, B-8)",
            given=repr(value),
        )
    return Fingerprint.try_create(token)


def _coerce_parameter_set(value: object) -> Result[Fingerprint]:
    """Resolve the shared parameter-set fingerprint the two runs execute (OPT-9)."""
    if isinstance(value, Fingerprint):
        return Ok(value)
    identity = getattr(value, "fp1_identity", None)
    if callable(identity):
        body = identity()
        if isinstance(body, Mapping):
            return fingerprint(cast("Mapping[str, object]", body))
    if isinstance(value, Mapping):
        return fingerprint(cast("Mapping[str, object]", value))
    token = clean_token(value)
    if token is None:
        return invalid(
            "parameter_set",
            "a trial's two runs share one parameter set, named by fp1 (a Fingerprint, "
            "an fp1 token, or fp1-canonical identity content) (OPT-9)",
            given=repr(value),
        )
    return Fingerprint.try_create(token)


def _require_replay_world(value: object, field: str) -> Result[World]:
    """World must be ``replay``; simulated or live is a policy rejection (AC5, B-7)."""
    resolved = _coerce_world(value)
    if resolved is None:
        return invalid(
            field,
            "a Study world is one of the closed set live | replay | simulated",
            given=repr(value),
        )
    if resolved is not World.REPLAY:
        return policy(
            field,
            "Studies run world=replay only in V1; a simulated or live split is a "
            "policy rejection (B-7, SC-06)",
            given=resolved.value,
            allowed=World.REPLAY.value,
        )
    return Ok(resolved)


def _coerce_world(value: object) -> World | None:
    if isinstance(value, World):
        return value
    token = clean_token(value)
    if token is None:
        return None
    try:
        return World(token)
    except ValueError:
        return None


def _coerce_role(value: object) -> Result[SegmentRole]:
    if isinstance(value, SegmentRole):
        return Ok(value)
    token = clean_token(value)
    if token is not None:
        try:
            return Ok(SegmentRole(token))
        except ValueError:
            pass
    return invalid(
        "role",
        "a research segment role is one of the closed set train | validation | sealed-test",
        given=repr(value),
        allowed=[member.value for member in SegmentRole],
    )


def _pick(body: Mapping[str, object], *keys: str) -> object | None:
    for key in keys:
        if key in body:
            return body[key]
    return None
