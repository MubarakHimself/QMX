"""Claim-class labeling and the L20 edge refusal for synthetic runs (Story 23.2).

Every synthetic run's result carries exactly one machine-readable **claim class**
in {``infra-stress``, ``robustness``, ``logic-smoke``} that bounds what it may
assert, as a field **distinct from ``world``** on the CT-32 result label (AR-59;
Epic 14) — the label states its epistemic reach and never lets synthetic evidence
be mistaken for validated edge (B-7; R3; AC1).

The permittable claim class is bounded by two things at once:

* the **generator lineage** (AC2, R3): a from-scratch ``gbm`` run may claim only
  ``infra-stress`` or ``logic-smoke`` — a ``robustness`` claim is a typed
  ``policy rejection``; a history-seeded process (``block-bootstrap`` /
  ``gaussian-resample`` / ``gaussian-noise``) may additionally claim
  ``robustness``;
* the **run world** (AC5, SC-06): a run that reads store-persisted synthetic data
  is ``world=simulated`` (Story 23.3), so no verdict-bearing (``robustness``)
  claim ships and the result refuses for governed-evidence use — ``infra-stress``
  and ``logic-smoke`` only until GAP-0048 closes. A procedure-ephemeral
  perturbation that stays ``world=replay`` keeps the lineage bound, so a
  history-seeded ``robustness`` claim is permittable there.

L20 is encoded as a **contract, not a docstring** (AC3): a request for an edge,
alpha, or validation claim on synthetic data — under any process, any class — is a
typed refusal. No synthetic run of any class may assert edge (FR-041; L20; R8).

Thresholds and pass batteries are **deferred** to the GAP-0048/0049 sittings while
the interfaces ship now (AC4; SC-07; B-14): a ``robustness``-class run's
percentile-band / p-value fields exist as interface only, with NO numeric pass
battery or threshold invented. A pass/fail threshold, when present, is a
config-declared configurable recorded BEFORE the run (never chosen after);
a post-hoc or invented threshold is refused (R7; NFR-07/L38).

Gaussian-family processes destroy real market structure, so a ``gaussian-resample``
or ``gaussian-noise`` result labeled ``robustness`` MUST carry a machine-readable
caveat that the process destroys autocorrelation / volatility clustering / fat
tails ("hides Black Swan risk") — the limitation is stated, never implied
(spec section 1, R2; AC6).

This module holds no mutable state and reads nothing ambient; every operation is a
pure ``Result``-returning function or a frozen value type.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qmb._refuse import clean_token, invalid, policy
from qmb.data.generate import (
    CLAIM_INFRA_STRESS,
    CLAIM_LOGIC_SMOKE,
    CLAIM_ROBUSTNESS,
    FROM_SCRATCH_PROCESSES,
    GAUSSIAN_NOISE,
    GAUSSIAN_RESAMPLE,
    GENERATOR_PROCESSES,
    SYNTHETIC_ORIGIN,
)

__all__ = [
    "CAVEAT_DESTROYS",
    "CAVEAT_SUMMARY",
    "CLAIMS_EDGE",
    "CLAIM_CLASS_ALPHA",
    "CLAIM_CLASS_EDGE",
    "CLAIM_CLASS_VALIDATION",
    "CLAIM_LABEL_CLASS",
    "CLAIM_LABEL_FORMAT_VERSION",
    "FORBIDDEN_CLAIM_CLASSES",
    "GAP_0048",
    "GAP_0049",
    "GAUSSIAN_FAMILY_PROCESSES",
    "GENERATOR_LINEAGES",
    "LINEAGE_FROM_SCRATCH",
    "LINEAGE_HISTORY_SEEDED",
    "REPORT_CLASS",
    "REPORT_EMITS_VERDICT",
    "REPORT_FORMAT_VERSION",
    "REPORT_INVENTS_PASS_BATTERY",
    "REPORT_INVENTS_THRESHOLD",
    "SIMULATED_PERMITS",
    "THRESHOLDS_DEFERRED_TO",
    "VERDICT_BEARING_CLAIM_CLASSES",
    "ClaimClassLabel",
    "PercentileBand",
    "PreregisteredThreshold",
    "RobustnessReportInterface",
    "SyntheticCaveat",
    "claim_class_identity",
    "generator_lineage",
    "permittable_claim_classes",
    "preregister_threshold",
    "refuse_edge_claim",
    "refuse_governed_evidence_use",
    "refuse_post_hoc_threshold",
    "resolve_claim_label",
    "robustness_report_interface",
    "synthetic_caveat",
]

# --- generator lineage that bounds the claim class (AC2, R3) ------------------

# The generator's provenance/lineage, derived from its process. History-seeded
# processes cite a real source dataset; the from-scratch gbm needs none. Lineage is
# what widens the permittable claim set to include the verdict-bearing robustness.
LINEAGE_HISTORY_SEEDED: Final[str] = "history-seeded"
LINEAGE_FROM_SCRATCH: Final[str] = "from-scratch"
GENERATOR_LINEAGES: Final[tuple[str, ...]] = (LINEAGE_HISTORY_SEEDED, LINEAGE_FROM_SCRATCH)

# --- the L20 forbidden claim family (AC3) ------------------------------------

# The edge / alpha / validation claim family. No synthetic run of any class may
# assert any of these — L20 as a contract (FR-041, R8).
CLAIM_CLASS_EDGE: Final[str] = "edge"
CLAIM_CLASS_ALPHA: Final[str] = "alpha"
CLAIM_CLASS_VALIDATION: Final[str] = "validation"
FORBIDDEN_CLAIM_CLASSES: Final[tuple[str, ...]] = (
    CLAIM_CLASS_EDGE,
    CLAIM_CLASS_ALPHA,
    CLAIM_CLASS_VALIDATION,
)

# A claim-class label never claims edge, under any process or class (L20).
CLAIMS_EDGE: Final[bool] = False

# The verdict-bearing claim classes — those that carry a percentile-band / p-value
# report. Only robustness is verdict-bearing; infra-stress and logic-smoke are not,
# so a world=simulated run (which ships no verdict-bearing claim) is bounded to them.
VERDICT_BEARING_CLAIM_CLASSES: Final[frozenset[str]] = frozenset({CLAIM_ROBUSTNESS})

# The claim classes a world=simulated run may carry until GAP-0048 closes (AC5).
SIMULATED_PERMITS: Final[tuple[str, ...]] = (CLAIM_INFRA_STRESS, CLAIM_LOGIC_SMOKE)

# --- Gaussian-family destroy-structure caveat (AC6) --------------------------

# The Gaussian-family processes assume i.i.d. Gaussian increments, so they destroy
# the real data's dependence structure. A robustness label over one of them MUST
# carry the machine-readable caveat below — the limitation is stated, never implied.
GAUSSIAN_FAMILY_PROCESSES: Final[frozenset[str]] = frozenset({GAUSSIAN_RESAMPLE, GAUSSIAN_NOISE})
CAVEAT_DESTROYS: Final[tuple[str, ...]] = (
    "autocorrelation",
    "volatility-clustering",
    "fat-tails",
)
CAVEAT_SUMMARY: Final[str] = "hides Black Swan risk"

# --- deferral of thresholds and pass batteries (AC4, SC-07) ------------------

GAP_0048: Final[str] = "GAP-0048"
GAP_0049: Final[str] = "GAP-0049"
THRESHOLDS_DEFERRED_TO: Final[str] = "GAP-0048/GAP-0049"

# --- the claim-label and robustness-report contracts -------------------------

CLAIM_LABEL_CLASS: Final[str] = "qmb-synthetic-claim-label"
CLAIM_LABEL_FORMAT_VERSION: Final[int] = 1
REPORT_CLASS: Final[str] = "qmb-robustness-report-interface"
REPORT_FORMAT_VERSION: Final[int] = 1
# The report interface emits no pass/fail verdict, invents no threshold, and invents
# no pass battery; every numeric threshold/battery stays deferred (SC-07, B-14).
REPORT_EMITS_VERDICT: Final[bool] = False
REPORT_INVENTS_THRESHOLD: Final[bool] = False
REPORT_INVENTS_PASS_BATTERY: Final[bool] = False

_CAVEAT_CLASS: Final[str] = "qmb-synthetic-caveat"
_THRESHOLD_CLASS: Final[str] = "qmb-preregistered-threshold"
_PERCENTILE_BAND_CLASS: Final[str] = "qmb-percentile-band"


# --- the machine-readable destroy-structure caveat (AC6) ---------------------


@dataclass(frozen=True, slots=True)
class SyntheticCaveat:
    """The machine-readable caveat a Gaussian-family robustness label carries (AC6).

    States that the process destroys the real data's dependence structure — the
    :data:`CAVEAT_DESTROYS` properties (autocorrelation, volatility clustering, fat
    tails) — and that this ":data:`CAVEAT_SUMMARY`". The limitation is a structured
    field, never buried in prose (spec section 1, R2).
    """

    process: str
    destroys: tuple[str, ...]
    summary: str

    @property
    def hides_black_swan_risk(self) -> bool:
        """Always ``True`` — the Gaussian family hides fat-tailed Black-Swan risk."""
        return True

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Package SemVer never enters."""
        return {
            "class": _CAVEAT_CLASS,
            "destroys": list(self.destroys),
            "hides_black_swan_risk": True,
            "process": self.process,
            "summary": self.summary,
        }


# --- the config-declared pass/fail threshold (AC4) ---------------------------


@dataclass(frozen=True, slots=True)
class PreregisteredThreshold:
    """A pass/fail threshold that is a config-declared configurable recorded BEFORE the run (AC4).

    The only way a robustness report carries a pass/fail threshold: its value is a
    UI-editable configurable resolved from the resolved run-config keys (no ratified
    value) and it is recorded before the run, never chosen after. The value is carried
    as its verbatim decimal-string token so identity stays exact — a raw binary float
    never enters (AD-7; R7; NFR-07/L38).
    """

    key: str
    value_token: str
    recorded_before_run: bool = True

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Package SemVer never enters."""
        return {
            "class": _THRESHOLD_CLASS,
            "key": self.key,
            "recorded_before_run": self.recorded_before_run,
            "value": self.value_token,
        }


# --- the interface-only percentile band (AC4) --------------------------------


@dataclass(frozen=True, slots=True)
class PercentileBand:
    """One percentile band on a robustness report — interface only (AC4).

    Mirrors the Story 22.1 distribution primitive's confidence band: a caller-declared
    probability and its exact empirical quantile, each an exact num/den pair so a raw
    binary float never enters (AD-7). The interface invents no band and no alpha level;
    it only carries one a caller has already produced as pure data.
    """

    probability_num: int
    probability_den: int
    value_num: int
    value_den: int

    @property
    def probability(self) -> Fraction:
        """The declared band probability (strictly between 0 and 1)."""
        return Fraction(self.probability_num, self.probability_den)

    @property
    def value(self) -> Fraction:
        """The exact empirical quantile at :attr:`probability`."""
        return Fraction(self.value_num, self.value_den)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content — every part an exact num/den pair."""
        return {
            "class": _PERCENTILE_BAND_CLASS,
            "probability_den": self.probability_den,
            "probability_num": self.probability_num,
            "value_den": self.value_den,
            "value_num": self.value_num,
        }

    @classmethod
    def try_create(cls, probability: object, value: object) -> Result[PercentileBand]:
        """Validate one percentile band; a raw binary float or out-of-range probability refuses."""
        prob = _as_ratio(probability, "probability")
        if is_refusal(prob):
            return prob
        quantile = _as_ratio(value, "value")
        if is_refusal(quantile):
            return quantile
        level = prob.value
        if level <= 0 or level >= 1:
            return invalid(
                "probability",
                "a percentile-band probability is strictly between 0 and 1; the interface "
                "invents no alpha level (AC4, SC-07)",
                given=str(level),
            )
        return Ok(
            cls(
                probability_num=level.numerator,
                probability_den=level.denominator,
                value_num=quantile.value.numerator,
                value_den=quantile.value.denominator,
            )
        )


# --- the robustness report interface (AC4) -----------------------------------


@dataclass(frozen=True, slots=True)
class RobustnessReportInterface:
    """Interface-only percentile-band / p-value report for a robustness-class run (AC4, R7).

    The percentile-band and p-value fields EXIST as interface; the module computes and
    invents NO number. ``p_value`` (an exact fraction in ``[0, 1]``) and
    ``percentile_bands`` are carried only when a caller supplies them as pure data.
    ``threshold`` is a config-declared :class:`PreregisteredThreshold` recorded before
    the run, or ``None`` — a post-hoc or invented threshold is refused
    (:func:`refuse_post_hoc_threshold`). It emits no pass/fail verdict and invents no
    pass battery; every threshold/battery stays deferred (SC-07, B-14, NFR-07/L38).
    """

    claim_class: str
    p_value_num: int | None = None
    p_value_den: int | None = None
    percentile_bands: tuple[PercentileBand, ...] = ()
    threshold: PreregisteredThreshold | None = None

    @property
    def p_value(self) -> Fraction | None:
        """The empirical one-tailed p-value, when carried; ``None`` when interface-only."""
        if self.p_value_num is None or self.p_value_den is None:
            return None
        return Fraction(self.p_value_num, self.p_value_den)

    @property
    def emits_verdict(self) -> bool:
        """Always ``False`` — the report is pure data, never a pass/fail verdict (AC4)."""
        return REPORT_EMITS_VERDICT

    @property
    def invents_threshold(self) -> bool:
        """Always ``False`` — a threshold is config-declared and preregistered, never invented."""
        return REPORT_INVENTS_THRESHOLD

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Package SemVer never enters."""
        content: dict[str, object] = {
            "claim_class": self.claim_class,
            "class": REPORT_CLASS,
            "emits_verdict": REPORT_EMITS_VERDICT,
            "format_version": REPORT_FORMAT_VERSION,
            "invents_pass_battery": REPORT_INVENTS_PASS_BATTERY,
            "invents_threshold": REPORT_INVENTS_THRESHOLD,
            "percentile_bands": [band.fp1_identity() for band in self.percentile_bands],
            "thresholds_deferred_to": THRESHOLDS_DEFERRED_TO,
        }
        if self.p_value_num is not None and self.p_value_den is not None:
            content["p_value_den"] = self.p_value_den
            content["p_value_num"] = self.p_value_num
        if self.threshold is not None:
            content["threshold"] = self.threshold.fp1_identity()
        return content


# --- the claim-class label (AC1) ---------------------------------------------


@dataclass(frozen=True, slots=True)
class ClaimClassLabel:
    """One machine-readable synthetic-run claim-class label (AC1, B-7, R3).

    Carries exactly one ``claim_class`` — a field DISTINCT from ``world`` — that
    bounds what the run may assert. ``claims_edge`` is always ``False`` (L20). A
    Gaussian-family robustness label carries a :class:`SyntheticCaveat`, and a
    robustness label may carry a :class:`RobustnessReportInterface`. Identity is
    qmf-core ``fp1``; package SemVer never enters.
    """

    claim_class: str
    world: str
    process: str
    lineage: str
    caveat: SyntheticCaveat | None = None
    report: RobustnessReportInterface | None = None

    @property
    def claims_edge(self) -> bool:
        """Always ``False`` — no synthetic run of any class asserts edge (L20)."""
        return CLAIMS_EDGE

    @property
    def is_verdict_bearing(self) -> bool:
        """Whether the class carries a verdict-bearing report (robustness only)."""
        return self.claim_class in VERDICT_BEARING_CLAIM_CLASSES

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content — ``claim_class`` and ``world`` are distinct keys."""
        content: dict[str, object] = {
            "claim_class": self.claim_class,
            "claims_edge": CLAIMS_EDGE,
            "class": CLAIM_LABEL_CLASS,
            "format_version": CLAIM_LABEL_FORMAT_VERSION,
            "is_verdict_bearing": self.is_verdict_bearing,
            "lineage": self.lineage,
            "origin": SYNTHETIC_ORIGIN,
            "process": self.process,
            "world": self.world,
        }
        if self.caveat is not None:
            content["caveat"] = self.caveat.fp1_identity()
        if self.report is not None:
            content["report"] = self.report.fp1_identity()
        return content

    def as_label(self) -> dict[str, object]:
        """Machine-readable label mapping (door transport); claim class distinct from world."""
        return dict(self.fp1_identity())

    def fingerprint(self) -> Result[Fingerprint]:
        """``fp1`` over the identity content, computed only by qmf-core."""
        return fingerprint(self.fp1_identity())


# --- lineage and permittability (AC2, AC5) -----------------------------------


def generator_lineage(process: object) -> Result[str]:
    """The generator lineage a claim class is bounded by, value-or-refusal (AC2, R3).

    Maps a v1 generator process to ``from-scratch`` (gbm) or ``history-seeded``
    (block-bootstrap / gaussian-resample / gaussian-noise). A process outside the
    four-process v1 menu is a typed ``invalid input`` refusal.
    """
    token = clean_token(process)
    if token is None or token not in GENERATOR_PROCESSES:
        return invalid(
            "process",
            "a synthetic run cites one of the four v1 generator processes; the claim class "
            "is bounded by the generator lineage (AC2, R3)",
            given=repr(process),
            legal=list(GENERATOR_PROCESSES),
        )
    if token in FROM_SCRATCH_PROCESSES:
        return Ok(LINEAGE_FROM_SCRATCH)
    return Ok(LINEAGE_HISTORY_SEEDED)


def permittable_claim_classes(process: object, world: object = None) -> Result[tuple[str, ...]]:
    """The claim classes permittable for a run's generator lineage and world (AC2, AC5).

    The lineage sets the base: a from-scratch gbm run permits only ``infra-stress``
    and ``logic-smoke``; a history-seeded process additionally permits ``robustness``.
    A ``world=simulated`` run (store-persisted synthetic) is then bounded to the
    non-verdict-bearing classes only until GAP-0048 closes, so ``robustness`` drops
    out even for a history-seeded process. A ``world=replay`` (procedure-ephemeral)
    run keeps the lineage base; a ``world=live`` synthetic run is a policy rejection.
    """
    lineage = generator_lineage(process)
    if is_refusal(lineage):
        return lineage
    base = _lineage_permits(lineage.value)
    if world is None:
        return Ok(base)
    coerced = _coerce_world(world)
    if is_refusal(coerced):
        return coerced
    resolved = coerced.value
    if resolved is World.LIVE:
        return policy(
            "world",
            "a synthetic run is never world=live; synthetic data cannot claim live "
            "evidence (L20, B-7)",
            world=World.LIVE.value,
        )
    if resolved is World.SIMULATED:
        return Ok(tuple(name for name in base if name in SIMULATED_PERMITS))
    return Ok(base)


def resolve_claim_label(
    *,
    process: object,
    claim_class: object,
    world: object,
    report: object = None,
) -> Result[ClaimClassLabel]:
    """Resolve one bounded, machine-readable claim-class label for a synthetic run (AC1-AC6).

    Binds the requested ``claim_class`` to the generator lineage AND the run world:
    a from-scratch ``robustness`` claim is a ``policy rejection`` (AC2); a
    ``world=simulated`` ``robustness`` claim is a ``policy rejection`` — no
    verdict-bearing claim ships until GAP-0048 (AC5); an ``edge`` / ``alpha`` /
    ``validation`` claim is refused outright (AC3, L20). A Gaussian-family robustness
    label carries the destroy-structure caveat (AC6). ``claim_class`` is carried as a
    field distinct from ``world`` (AC1). Domain failure is a CT-04 value, returned
    never raised.
    """
    lineage = generator_lineage(process)
    if is_refusal(lineage):
        return lineage
    process_token = cast("str", clean_token(process))
    run_world = _coerce_run_world(world)
    if is_refusal(run_world):
        return run_world
    world_token = run_world.value
    claim_token = clean_token(claim_class)
    if claim_token is None:
        return invalid(
            "claim_class",
            "a synthetic run carries exactly one claim class in "
            "{infra-stress, robustness, logic-smoke} (AC1, R3)",
            legal=list(_ALL_CLAIM_CLASSES),
        )
    if claim_token in FORBIDDEN_CLAIM_CLASSES:
        return refuse_edge_claim(claim_token, process=process_token)
    if claim_token not in _ALL_CLAIM_CLASSES:
        return invalid(
            "claim_class",
            "a synthetic run's claim class is one of infra-stress, robustness, logic-smoke "
            "(AC1, R3)",
            given=claim_token,
            legal=list(_ALL_CLAIM_CLASSES),
        )
    permittable = permittable_claim_classes(process_token, world_token)
    if is_refusal(permittable):
        return permittable
    if claim_token not in permittable.value:
        return _refuse_impermissible_claim(
            claim_token,
            lineage=lineage.value,
            world=world_token,
            permittable=permittable.value,
        )
    caveat = _caveat_for(claim_token, process_token)
    if is_refusal(caveat):
        return caveat
    resolved_report = _validate_report(report, claim_token)
    if is_refusal(resolved_report):
        return resolved_report
    return Ok(
        ClaimClassLabel(
            claim_class=claim_token,
            world=world_token,
            process=process_token,
            lineage=lineage.value,
            caveat=caveat.value,
            report=resolved_report.value,
        )
    )


# --- L20 edge refusal, the world gate, and the caveat (AC3, AC5, AC6) --------


def refuse_edge_claim(claim: object, *, process: object = None) -> TypedRefusal:
    """Refuse an edge / alpha / validation claim on synthetic data (AC3, L20, R8).

    L20 encoded as a contract, not a docstring: no synthetic run of any class, under
    any process, may assert edge. A request for an edge, alpha, or validation claim is
    a typed ``policy rejection`` — returned, never raised.
    """
    token = clean_token(claim)
    named = token if token is not None else repr(claim)
    context: dict[str, object] = {
        "requested_claim": named,
        "forbidden": list(FORBIDDEN_CLAIM_CLASSES),
        "permittable": list(_ALL_CLAIM_CLASSES),
    }
    proc = clean_token(process)
    if proc is not None:
        context["process"] = proc
    return policy(
        "claim_class",
        "synthetic data may stress infrastructure and probe robustness but never validates "
        "trading edge; an edge / alpha / validation claim on any synthetic run is refused "
        "(FR-041, L20, R8)",
        **context,
    )


def refuse_governed_evidence_use(source: object) -> Result[World]:
    """Refuse governed-evidence use of a world=simulated synthetic run (AC5, SC-06, B-7).

    A run that reads store-persisted synthetic data is ``world=simulated`` (Story
    23.3), so no verdict-bearing claim ships and the result is a ``policy rejection``
    for governed evidence until GAP-0048 — ``infra-stress`` and ``logic-smoke`` only.
    A ``world=replay`` (procedure-ephemeral) or ``world=live`` source passes through.
    ``source`` is a :class:`~qmf.core.fingerprint.World`, a world token, or a resolved
    run-config (any object carrying a ``world`` attribute).
    """
    coerced = _coerce_world(source)
    if is_refusal(coerced):
        return coerced
    world = coerced.value
    if world is World.SIMULATED:
        return policy(
            "world",
            "a run that reads store-persisted synthetic data is world=simulated and a policy "
            "rejection for governed evidence until GAP-0048; no verdict-bearing claim ships — "
            "infra-stress and logic-smoke only (AC5, B-7, SC-06)",
            world=World.SIMULATED.value,
            permittable=list(SIMULATED_PERMITS),
            gap=GAP_0048,
        )
    return Ok(world)


def synthetic_caveat(process: object) -> Result[SyntheticCaveat | None]:
    """The destroy-structure caveat a Gaussian-family process carries, or ``None`` (AC6).

    A ``gaussian-resample`` or ``gaussian-noise`` process assumes i.i.d. Gaussian
    increments and so destroys autocorrelation, volatility clustering, and fat tails —
    it "hides Black Swan risk". Any other v1 process carries no such caveat and returns
    ``None``. An unknown process is a typed ``invalid input`` refusal.
    """
    token = clean_token(process)
    if token is None or token not in GENERATOR_PROCESSES:
        return invalid(
            "process",
            "a caveat is derived from a v1 generator process",
            given=repr(process),
            legal=list(GENERATOR_PROCESSES),
        )
    if token not in GAUSSIAN_FAMILY_PROCESSES:
        return Ok(None)
    return Ok(SyntheticCaveat(process=token, destroys=CAVEAT_DESTROYS, summary=CAVEAT_SUMMARY))


# --- the robustness report interface and its threshold (AC4) -----------------


def robustness_report_interface(
    *,
    claim_class: object = CLAIM_ROBUSTNESS,
    p_value: object = None,
    percentile_bands: object = (),
    threshold: object = None,
) -> Result[RobustnessReportInterface]:
    """Build a robustness-class report interface — percentile band / p-value only (AC4, R7).

    The interface is for a ``robustness``-class run; infra-stress and logic-smoke carry
    no verdict-bearing report. ``p_value`` and ``percentile_bands`` are optional pure
    data (a raw binary float is refused). ``threshold`` must be a config-declared
    :class:`PreregisteredThreshold` recorded before the run — a bare number or any
    non-preregistered value is a post-hoc / invented threshold and is refused. The
    module invents no number and emits no verdict (SC-07, NFR-07/L38).
    """
    token = clean_token(claim_class)
    if token != CLAIM_ROBUSTNESS:
        return invalid(
            "claim_class",
            "the percentile-band / p-value report interface is for a robustness-class run; "
            "infra-stress and logic-smoke carry no verdict-bearing report (AC4)",
            given=repr(claim_class),
            expected=CLAIM_ROBUSTNESS,
        )
    pval = _coerce_p_value(p_value)
    if is_refusal(pval):
        return pval
    bands = _coerce_bands(percentile_bands)
    if is_refusal(bands):
        return bands
    resolved_threshold = _coerce_threshold(threshold)
    if is_refusal(resolved_threshold):
        return resolved_threshold
    ratio = pval.value
    return Ok(
        RobustnessReportInterface(
            claim_class=CLAIM_ROBUSTNESS,
            p_value_num=None if ratio is None else ratio[0],
            p_value_den=None if ratio is None else ratio[1],
            percentile_bands=bands.value,
            threshold=resolved_threshold.value,
        )
    )


def preregister_threshold(config: object, key: object) -> Result[PreregisteredThreshold]:
    """Resolve a pass/fail threshold as a config-declared configurable, recorded pre-run (AC4).

    Reads the threshold value from ``config`` — a resolved run-config (its ``keys``
    mapping) or a plain key->value mapping — under the named ``key``. An unset key is a
    typed ``invalid input`` refusal: the threshold has no ratified value and is never
    invented, and a threshold chosen after the run is never recorded here (R7,
    NFR-07/L38, SC-07). The value is carried as its verbatim decimal-string token.
    """
    token = clean_token(key)
    if token is None:
        return invalid(
            "key",
            "a threshold configurable key is a non-blank string",
            given=repr(key),
        )
    keys = _keys_of(config)
    if is_refusal(keys):
        return keys
    value = keys.value.get(token)
    if value is None:
        return invalid(
            "threshold",
            "a pass/fail threshold is a config-declared configurable recorded before the run; "
            "it has no ratified value and is never invented (AC4, R7, NFR-07, SC-07)",
            configurable=token,
            deferred_to=THRESHOLDS_DEFERRED_TO,
        )
    value_token = _threshold_token(value)
    if is_refusal(value_token):
        return value_token
    return Ok(
        PreregisteredThreshold(key=token, value_token=value_token.value, recorded_before_run=True)
    )


def refuse_post_hoc_threshold(name: object) -> TypedRefusal:
    """Refuse a pass/fail threshold chosen after the run or invented (AC4, R7, NFR-07/L38).

    A pass/fail threshold, when present, is a config-declared configurable recorded
    BEFORE the run (:func:`preregister_threshold`) — never chosen after and never
    invented. A post-hoc or bare-number threshold is a typed ``policy rejection``.
    """
    token = clean_token(name)
    named = token if token is not None else repr(name)
    return policy(
        "threshold",
        "a pass/fail threshold is a config-declared configurable recorded before the run, "
        "never chosen after; a post-hoc or invented threshold is refused, and the numeric "
        "pass batteries stay deferred (AC4, R7, NFR-07/L38, SC-07)",
        threshold=named,
        deferred_to=THRESHOLDS_DEFERRED_TO,
    )


# --- identity ----------------------------------------------------------------


def claim_class_identity() -> dict[str, object]:
    """Identity-bearing claim-class-contract fields. Package SemVer is omitted."""
    return {
        "caveat_destroys": CAVEAT_DESTROYS,
        "caveat_summary": CAVEAT_SUMMARY,
        "claim_label_class": CLAIM_LABEL_CLASS,
        "claim_label_format_version": CLAIM_LABEL_FORMAT_VERSION,
        "claims_edge": CLAIMS_EDGE,
        "forbidden_claim_classes": FORBIDDEN_CLAIM_CLASSES,
        "from_scratch_permits": _lineage_permits(LINEAGE_FROM_SCRATCH),
        "gaussian_family_processes": tuple(sorted(GAUSSIAN_FAMILY_PROCESSES)),
        "generator_lineages": GENERATOR_LINEAGES,
        "history_seeded_permits": _lineage_permits(LINEAGE_HISTORY_SEEDED),
        "report_class": REPORT_CLASS,
        "report_emits_verdict": REPORT_EMITS_VERDICT,
        "report_invents_pass_battery": REPORT_INVENTS_PASS_BATTERY,
        "report_invents_threshold": REPORT_INVENTS_THRESHOLD,
        "simulated_permits": SIMULATED_PERMITS,
        "thresholds_deferred_to": THRESHOLDS_DEFERRED_TO,
        "verdict_bearing_claim_classes": tuple(sorted(VERDICT_BEARING_CLAIM_CLASSES)),
    }


# --- internals ---------------------------------------------------------------

_ALL_CLAIM_CLASSES: Final[tuple[str, ...]] = (
    CLAIM_INFRA_STRESS,
    CLAIM_ROBUSTNESS,
    CLAIM_LOGIC_SMOKE,
)


def _lineage_permits(lineage: str) -> tuple[str, ...]:
    """The base permittable claim classes for a generator lineage (before the world gate)."""
    if lineage == LINEAGE_HISTORY_SEEDED:
        return (CLAIM_INFRA_STRESS, CLAIM_LOGIC_SMOKE, CLAIM_ROBUSTNESS)
    return (CLAIM_INFRA_STRESS, CLAIM_LOGIC_SMOKE)


def _caveat_for(claim_class: str, process: str) -> Result[SyntheticCaveat | None]:
    """The Gaussian-family caveat when the label is robustness over a Gaussian process (AC6)."""
    if claim_class != CLAIM_ROBUSTNESS:
        return Ok(None)
    return synthetic_caveat(process)


def _refuse_impermissible_claim(
    claim_class: str,
    *,
    lineage: str,
    world: str,
    permittable: tuple[str, ...],
) -> TypedRefusal:
    """A permittable-set miss: a bounded, category-appropriate policy rejection (AC2, AC5)."""
    if claim_class == CLAIM_ROBUSTNESS and lineage == LINEAGE_FROM_SCRATCH:
        return policy(
            "claim_class",
            "a robustness claim is allowed only for a history-seeded generator; a from-scratch "
            "gbm run claims infra-stress or logic-smoke, never robustness (AC2, L20, R3)",
            claim_class=claim_class,
            lineage=lineage,
            permittable=list(permittable),
        )
    if claim_class == CLAIM_ROBUSTNESS and world == World.SIMULATED.value:
        return policy(
            "claim_class",
            "a run that reads store-persisted synthetic data is world=simulated; no "
            "verdict-bearing robustness claim ships until GAP-0048 — infra-stress and "
            "logic-smoke only (AC5, B-7, SC-06)",
            claim_class=claim_class,
            world=world,
            permittable=list(permittable),
            gap=GAP_0048,
        )
    return policy(
        "claim_class",
        "the requested claim class is not permittable for this generator lineage and world "
        "(AC2, AC5, R3)",
        claim_class=claim_class,
        lineage=lineage,
        world=world,
        permittable=list(permittable),
    )


def _validate_report(report: object, claim_class: str) -> Result[RobustnessReportInterface | None]:
    """A report interface attaches only to a robustness label and must agree on the class."""
    if report is None:
        return Ok(None)
    if not isinstance(report, RobustnessReportInterface):
        return invalid(
            "report",
            "a robustness report is a RobustnessReportInterface (percentile band / p-value)",
            given=repr(type(report).__name__),
        )
    if claim_class != CLAIM_ROBUSTNESS:
        return invalid(
            "report",
            "only a robustness-class label carries a percentile-band / p-value report; "
            "infra-stress and logic-smoke carry none (AC4)",
            claim_class=claim_class,
        )
    if report.claim_class != CLAIM_ROBUSTNESS:
        return invalid(
            "report",
            "the report interface claim class must be robustness to match the label",
            given=report.claim_class,
        )
    return Ok(report)


def _coerce_world(source: object) -> Result[World]:
    """Coerce a World, a world token, or a resolved-run-config-like object to a World."""
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
    attribute = getattr(source, "world", None)
    if isinstance(attribute, World):
        return Ok(attribute)
    return invalid(
        "world",
        "a claim-class world is a World, a world token, or a resolved run-config (B-7)",
        given=repr(type(source).__name__),
    )


def _coerce_run_world(source: object) -> Result[str]:
    """The run world for a synthetic label: replay or simulated, never live (L20)."""
    coerced = _coerce_world(source)
    if is_refusal(coerced):
        return coerced
    if coerced.value is World.LIVE:
        return policy(
            "world",
            "a synthetic run is never world=live; synthetic data cannot claim live "
            "evidence (L20, B-7)",
            world=World.LIVE.value,
        )
    return Ok(coerced.value.value)


def _coerce_p_value(value: object) -> Result[tuple[int, int] | None]:
    """An optional exact p-value in ``[0, 1]``; a raw binary float is refused (AD-7)."""
    if value is None:
        return Ok(None)
    ratio = _as_ratio(value, "p_value")
    if is_refusal(ratio):
        return ratio
    magnitude = ratio.value
    if magnitude < 0 or magnitude > 1:
        return invalid(
            "p_value",
            "the empirical one-tailed p-value is an exact fraction in [0, 1]",
            given=str(magnitude),
        )
    return Ok((magnitude.numerator, magnitude.denominator))


def _coerce_bands(value: object) -> Result[tuple[PercentileBand, ...]]:
    """A sequence of PercentileBand values; the interface invents none (AC4)."""
    if value is None:
        return Ok(())
    if isinstance(value, PercentileBand):
        return Ok((value,))
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "percentile_bands",
            "percentile bands are a sequence of PercentileBand values; the interface invents "
            "none (AC4)",
            given=repr(type(value).__name__),
        )
    out: list[PercentileBand] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, PercentileBand):
            return invalid(
                "percentile_bands",
                "each percentile band is a PercentileBand (probability + exact quantile)",
                index=index,
                given=repr(type(item).__name__),
            )
        out.append(item)
    return Ok(tuple(out))


def _coerce_threshold(value: object) -> Result[PreregisteredThreshold | None]:
    """A threshold must be a preregistered configurable; anything else is post-hoc (AC4)."""
    if value is None:
        return Ok(None)
    if isinstance(value, PreregisteredThreshold):
        return Ok(value)
    return refuse_post_hoc_threshold(value)


def _threshold_token(value: object) -> Result[str]:
    """The verbatim decimal-string token of a threshold value; a raw binary float refuses."""
    if isinstance(value, bool):
        return invalid("threshold", "a threshold is a number, never a bool", given=repr(value))
    if isinstance(value, int):
        return Ok(str(value))
    if isinstance(value, str) and value.strip() != "":
        return Ok(value.strip())
    if isinstance(value, float):
        return invalid(
            "threshold",
            "a threshold is a decimal-string configurable, never a binary float (AD-7)",
            given=repr(value),
        )
    return invalid(
        "threshold",
        "a threshold is an int or decimal-string configurable",
        given=repr(type(value).__name__),
    )


def _as_ratio(value: object, field_name: str) -> Result[Fraction]:
    """An exact int or Fraction as a Fraction; a raw binary float is refused (AD-7)."""
    if isinstance(value, bool):
        return invalid(field_name, f"{field_name} is a number, not a boolean", given=repr(value))
    if isinstance(value, Fraction):
        return Ok(value)
    if isinstance(value, int):
        return Ok(Fraction(value))
    if isinstance(value, float):
        return invalid(
            field_name,
            f"{field_name} is an exact int or Fraction, never a binary float (AD-7)",
            given=repr(value),
        )
    return invalid(
        field_name,
        f"{field_name} is an exact int or Fraction",
        given=repr(type(value).__name__),
    )


def _keys_of(config: object) -> Result[Mapping[str, object]]:
    """A resolved run-config (its ``keys`` mapping) or a plain key->value mapping."""
    if isinstance(config, Mapping):
        return Ok(cast("Mapping[str, object]", config))
    keys = getattr(config, "keys", None)
    if isinstance(keys, Mapping):
        return Ok(cast("Mapping[str, object]", keys))
    return invalid(
        "config",
        "a threshold configurable resolves from a resolved run-config (its keys mapping) or a "
        "key->value mapping",
        given=repr(type(config).__name__),
    )
