"""Story 10.10 — CT-32 performance-result container, publish-never-act (COMP-QMF-RISK).

One performance-result container kind serving both the AD-32 admission-bar evidence
and the analyst's report (AD-41; DEC-0155, DEC-0146):

* the full AD-12 :class:`~qmf.core.ResultLabel` plus the account-binding role — a
  single result may never span account roles;
* a fingerprinted population (binding-record fingerprints, never intervals) that
  consumes ``continues-performance`` edges only;
* a declared period (AD-8 Interval + calendar + knowledge-time bound);
* an ordered measure set with a unit-kind on every emitted quantity;
* suppression accounting (by authority and reason) and veto accounting (by door);
* **measurement publishes, never acts** — no score/rating/tier/weighted composite;
  the authority to act on a published measure belongs to the Book door (bench) or
  the operator (promotion);
* the bench fold publishes a crossing as **one governed producer** consumed by the
  Book door; a ``world = replay`` result can never gate live money.

qmf-risk imports **only** ``qmf-core`` (default-deny, L30/DEC-0120) and sibling
``qmf.risk`` modules; nothing imports ``qmf.risk``. Ratified ``defined-unwired``
surface — no live binding or order is authorized here (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, cast

from qmf.core import (
    AccountRole,
    CalendarIdentity,
    ExactRational,
    Fingerprint,
    Instant,
    Interval,
    Money,
    Result,
    ResultLabel,
    TypedRefusal,
    UnitKind,
    World,
    fingerprint,
    is_refusal,
)
from qmf.core import (
    Ok as _Ok,
)
from qmf.risk._common import clean_str, coerce_enum, invalid, policy, type_name, unavailable
from qmf.risk.binding import ContinuesPerformanceEdge
from qmf.risk.control_action import AuthorityKind
from qmf.risk.exit_record import BenchFoldResult

__all__ = [
    "CT32_CONTRACT_FORMAT_VERSION",
    "FORBIDDEN_COMPOSITE_EXPRESSIONS",
    "FORBIDDEN_MEASURE_ACTS",
    "BenchCrossingPublication",
    "PerformanceMeasure",
    "PerformanceResult",
    "PopulationDeclaration",
    "PublishAct",
    "ResultPeriod",
    "SuppressionCount",
    "UndefinedMeasure",
    "VetoCount",
    "check_publish_never_act",
    "check_replay_never_gates_live",
    "consume_bench_crossing_at_door",
    "mint_performance_result",
    "publish_bench_crossing",
    "reject_composite_expression",
    "reject_multi_role_result",
    "require_baseline_for_decay",
]

CT32_CONTRACT_FORMAT_VERSION: Final[int] = 1

FORBIDDEN_COMPOSITE_EXPRESSIONS: Final[frozenset[str]] = frozenset(
    {
        "score",
        "rating",
        "tier",
        "tier-band",
        "weighted-composite",
        "weighted-aggregate",
        "composite-score",
        "composite",
    }
)


class PublishAct(StrEnum):
    """Acts a measurement producer may never take (DEC-0155).

    The authority to act on a published measure belongs to the Book door (bench)
    or the operator (promotion) — never to the measurement producer itself.
    """

    SIZE = "size"
    ALLOCATE = "allocate"
    PROMOTE = "promote"
    DEMOTE = "demote"
    BENCH = "bench"
    CHANGE_MODE = "change_mode"


FORBIDDEN_MEASURE_ACTS: Final[frozenset[PublishAct]] = frozenset(PublishAct)


# --- population / period / measures ------------------------------------------


@dataclass(frozen=True, slots=True)
class PopulationDeclaration:
    """Fingerprinted population declaration — never prose (DEC-0155, DEC-0143).

    Binding epochs are cited by fingerprint, never by interval. Track-record
    assertions ride human-signed ``continues-performance`` edges only; they move
    no money.
    """

    bot_identity: Fingerprint
    binding_epochs_in: tuple[Fingerprint, ...]
    binding_epochs_out: tuple[Fingerprint, ...]
    account_roles: tuple[AccountRole, ...]
    instruments: tuple[str, ...]
    decay_cohort_key: Fingerprint
    continues_performance_edges: tuple[ContinuesPerformanceEdge, ...]

    @classmethod
    def try_create(
        cls,
        bot_identity: object,
        binding_epochs_in: object,
        binding_epochs_out: object,
        account_roles: object,
        instruments: object,
        decay_cohort_key: object,
        continues_performance_edges: object,
    ) -> Result[PopulationDeclaration]:
        """Validate and build a :class:`PopulationDeclaration`, value-or-refusal."""
        if not isinstance(bot_identity, Fingerprint):
            return invalid(
                "bot_identity",
                "the population declares a fingerprinted Bot identity",
                given=repr(bot_identity),
            )
        epochs_in = _fp_tuple(binding_epochs_in, "binding_epochs_in")
        if isinstance(epochs_in, TypedRefusal):
            return epochs_in
        epochs_out = _fp_tuple(binding_epochs_out, "binding_epochs_out")
        if isinstance(epochs_out, TypedRefusal):
            return epochs_out
        roles = _role_tuple(account_roles)
        if isinstance(roles, TypedRefusal):
            return roles
        if not isinstance(instruments, Sequence) or isinstance(instruments, (str, bytes)):
            return invalid(
                "instruments",
                "the population declares an ordered sequence of instrument tokens",
                given=type_name(instruments),
            )
        instrument_tokens: list[str] = []
        for index, item in enumerate(cast("Sequence[object]", instruments)):
            token = clean_str(item)
            if token is None:
                return invalid(
                    "instruments",
                    "every instrument token is a non-blank string",
                    index=index,
                    given=repr(item),
                )
            instrument_tokens.append(token)
        if not isinstance(decay_cohort_key, Fingerprint):
            return invalid(
                "decay_cohort_key",
                "the AD-35 decay cohort key is a fingerprinted declaration",
                given=repr(decay_cohort_key),
            )
        if not isinstance(continues_performance_edges, Sequence) or isinstance(
            continues_performance_edges, (str, bytes)
        ):
            return invalid(
                "continues_performance_edges",
                "population track-record assertions consume continues-performance edges only",
                given=type_name(continues_performance_edges),
            )
        edges: list[ContinuesPerformanceEdge] = []
        for index, item in enumerate(cast("Sequence[object]", continues_performance_edges)):
            if not isinstance(item, ContinuesPerformanceEdge):
                return invalid(
                    "continues_performance_edges",
                    "a population consumes ContinuesPerformanceEdge values only — "
                    "never carries-ledger (DEC-0158)",
                    index=index,
                    given=type_name(item),
                )
            edges.append(item)
        return _Ok(
            cls(
                bot_identity=bot_identity,
                binding_epochs_in=epochs_in,
                binding_epochs_out=epochs_out,
                account_roles=roles,
                instruments=tuple(instrument_tokens),
                decay_cohort_key=decay_cohort_key,
                continues_performance_edges=tuple(edges),
            )
        )

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint of this population declaration."""
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this population."""
        return {
            "class": "population-declaration",
            "bot_identity": self.bot_identity.value,
            "binding_epochs_in": [fp.value for fp in self.binding_epochs_in],
            "binding_epochs_out": [fp.value for fp in self.binding_epochs_out],
            "account_roles": [role.value for role in self.account_roles],
            "instruments": list(self.instruments),
            "decay_cohort_key": self.decay_cohort_key.value,
            "continues_performance_edges": [
                edge.fp1_identity() for edge in self.continues_performance_edges
            ],
            "format_version": CT32_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ResultPeriod:
    """Declared period: AD-8 Interval + calendar + knowledge-time bound (DEC-0155)."""

    interval: Interval
    calendar: CalendarIdentity
    knowledge_time_bound: Instant

    @classmethod
    def try_create(
        cls, interval: object, calendar: object, knowledge_time_bound: object
    ) -> Result[ResultPeriod]:
        """Validate and build a :class:`ResultPeriod`, value-or-refusal."""
        if not isinstance(interval, Interval):
            return invalid(
                "interval",
                "the period is a declared AD-8 Interval",
                given=type_name(interval),
            )
        if not isinstance(calendar, CalendarIdentity):
            return invalid(
                "calendar",
                "the period carries calendar identity + version",
                given=type_name(calendar),
            )
        if not isinstance(knowledge_time_bound, Instant):
            return invalid(
                "knowledge_time_bound",
                "the knowledge-time bound the result was computed under is an Instant",
                given=repr(knowledge_time_bound),
            )
        return _Ok(
            cls(interval=interval, calendar=calendar, knowledge_time_bound=knowledge_time_bound)
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this period."""
        return {
            "class": "result-period",
            "interval": self.interval.fp1_identity(),
            "calendar": self.calendar.fp1_identity(),
            "knowledge_time_bound": self.knowledge_time_bound.fp1_identity(),
            "format_version": CT32_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class PerformanceMeasure:
    """One ordered emitted measure with a mandatory unit-kind (DEC-0155, DEC-0154).

    Float discipline: identity is label-derived; no binary float enters identity.
    Money measures carry :class:`~qmf.core.Money` (exact scaled integers at the
    declared currency scale). Ratios, counts, and durations carry
    :class:`~qmf.core.ExactRational`. A null unit-kind is a refusal, never a default.
    """

    measure_identity: str
    quantity: ExactRational | Money
    metric_contract_format_version: int

    @classmethod
    def try_create(
        cls,
        measure_identity: object,
        quantity: object,
        metric_contract_format_version: object,
    ) -> Result[PerformanceMeasure]:
        """Validate and build a :class:`PerformanceMeasure`, value-or-refusal."""
        token = clean_str(measure_identity)
        if token is None:
            return invalid(
                "measure_identity",
                "every emitted measure declares a non-blank identity",
                given=repr(measure_identity),
            )
        lowered = token.casefold()
        for forbidden in FORBIDDEN_COMPOSITE_EXPRESSIONS:
            if forbidden in lowered:
                return reject_composite_expression(token)
        if not isinstance(quantity, (ExactRational, Money)):
            return invalid(
                "quantity",
                "every emitted quantity is Money or ExactRational carrying a unit-kind "
                "from the closed AD-40 vocabulary; a null unit-kind is a refusal, "
                "never a default",
                given=repr(quantity),
            )
        if (
            isinstance(metric_contract_format_version, bool)
            or not isinstance(metric_contract_format_version, int)
            or metric_contract_format_version < 1
        ):
            return invalid(
                "metric_contract_format_version",
                "each metric's arithmetic is pinned by a positive contract format version",
                given=repr(metric_contract_format_version),
            )
        return _Ok(
            cls(
                measure_identity=token,
                quantity=quantity,
                metric_contract_format_version=metric_contract_format_version,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this measure."""
        return {
            "class": "performance-measure",
            "measure_identity": self.measure_identity,
            "quantity": self.quantity.fp1_identity(),
            "unit_kind": self.quantity.unit_kind.value,
            "metric_contract_format_version": self.metric_contract_format_version,
            "format_version": CT32_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class UndefinedMeasure:
    """An ordered measure-set slot whose arithmetic is undefined or under-sampled.

    Distinct from a zero quantity: a reader branches on this type (and the
    nested typed refusal), never on magnitude. Never a magic cap of 10 and
    never NaN coerced to 0 (R-RPT-3, DEC-0155).
    """

    measure_identity: str
    metric_contract_format_version: int
    refusal: TypedRefusal

    @classmethod
    def try_create(
        cls,
        measure_identity: object,
        metric_contract_format_version: object,
        refusal: object,
    ) -> Result[UndefinedMeasure]:
        """Validate and build an :class:`UndefinedMeasure`, value-or-refusal."""
        token = clean_str(measure_identity)
        if token is None:
            return invalid(
                "measure_identity",
                "every emitted measure declares a non-blank identity",
                given=repr(measure_identity),
            )
        lowered = token.casefold()
        for forbidden in FORBIDDEN_COMPOSITE_EXPRESSIONS:
            if forbidden in lowered:
                return reject_composite_expression(token)
        if (
            isinstance(metric_contract_format_version, bool)
            or not isinstance(metric_contract_format_version, int)
            or metric_contract_format_version < 1
        ):
            return invalid(
                "metric_contract_format_version",
                "each metric's arithmetic is pinned by a positive contract format version",
                given=repr(metric_contract_format_version),
            )
        if not isinstance(refusal, TypedRefusal):
            return invalid(
                "refusal",
                "an undefined measure carries a TypedRefusal a reader can tell apart from zero",
                given=type_name(refusal),
            )
        return _Ok(
            cls(
                measure_identity=token,
                metric_contract_format_version=metric_contract_format_version,
                refusal=refusal,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this undefined slot."""
        return {
            "class": "undefined-measure",
            "measure_identity": self.measure_identity,
            "metric_contract_format_version": self.metric_contract_format_version,
            "refusal": _refusal_identity(self.refusal),
            "format_version": CT32_CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class SuppressionCount:
    """Count of actions suppressed in the period by authority and reason (DEC-0155)."""

    authority: AuthorityKind
    reason_class: str
    count: int

    @classmethod
    def try_create(
        cls, authority: object, reason_class: object, count: object
    ) -> Result[SuppressionCount]:
        """Validate and build a :class:`SuppressionCount`, value-or-refusal."""
        resolved = coerce_enum(AuthorityKind, authority)
        if resolved is None:
            return invalid(
                "authority",
                "suppression accounting is keyed by issuing authority",
                given=repr(authority),
                allowed=[member.value for member in AuthorityKind],
            )
        reason = clean_str(reason_class)
        if reason is None:
            return invalid(
                "reason_class",
                "suppression accounting is keyed by reason class",
                given=repr(reason_class),
            )
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            return invalid(
                "count",
                "suppression accounting is a typed non-negative count, never money",
                given=repr(count),
            )
        quantity = ExactRational.try_create(count, 1, UnitKind.COUNT)
        if is_refusal(quantity):
            return quantity
        return _Ok(cls(authority=resolved, reason_class=reason, count=count))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this suppression count."""
        return {
            "class": "suppression-count",
            "authority": self.authority.value,
            "reason_class": self.reason_class,
            "count": self.count,
            "unit_kind": UnitKind.COUNT.value,
        }


@dataclass(frozen=True, slots=True)
class VetoCount:
    """Count of door refusals in the period keyed by refusing-door identity (DEC-0155)."""

    door_identity: str
    count: int

    @classmethod
    def try_create(cls, door_identity: object, count: object) -> Result[VetoCount]:
        """Validate and build a :class:`VetoCount`, value-or-refusal."""
        door = clean_str(door_identity)
        if door is None:
            return invalid(
                "door_identity",
                "veto accounting is keyed by refusing-door identity",
                given=repr(door_identity),
            )
        if isinstance(count, bool) or not isinstance(count, int) or count < 0:
            return invalid(
                "count",
                "veto accounting is a typed non-negative count, never money",
                given=repr(count),
            )
        quantity = ExactRational.try_create(count, 1, UnitKind.COUNT)
        if is_refusal(quantity):
            return quantity
        return _Ok(cls(door_identity=door, count=count))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this veto count."""
        return {
            "class": "veto-count",
            "door_identity": self.door_identity,
            "count": self.count,
            "unit_kind": UnitKind.COUNT.value,
        }


# --- the container -----------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PerformanceResult:
    """One CT-32 performance-result container (DEC-0155).

    Serves admission-bar evidence and the analyst's report. Measurement publishes;
    it never sizes, allocates, promotes, demotes, benches, or changes a mode.
    """

    result_label: ResultLabel
    account_binding_role: AccountRole
    population: PopulationDeclaration
    period: ResultPeriod
    measure_set: tuple[PerformanceMeasure | UndefinedMeasure, ...]
    suppression_accounting: tuple[SuppressionCount, ...]
    veto_accounting: tuple[VetoCount, ...]
    baseline_pointer: Fingerprint | None

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint of this performance result."""
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this result.

        Float discipline: identity is label-derived; measure quantities enter as
        exact rationals, never float bytes (DEC-0155, DEC-0158).
        """
        content: dict[str, object] = {
            "class": "performance-result",
            "result_label": self.result_label.fp1_identity(),
            "account_binding_role": self.account_binding_role.value,
            "population": self.population.fp1_identity(),
            "period": self.period.fp1_identity(),
            "measure_set": [measure.fp1_identity() for measure in self.measure_set],
            "suppression_accounting": [row.fp1_identity() for row in self.suppression_accounting],
            "veto_accounting": [row.fp1_identity() for row in self.veto_accounting],
            "format_version": CT32_CONTRACT_FORMAT_VERSION,
        }
        if self.baseline_pointer is not None:
            content["baseline_pointer"] = self.baseline_pointer.value
        return content


def mint_performance_result(
    *,
    result_label: object,
    account_binding_role: object,
    population: object,
    period: object,
    measure_set: object,
    suppression_accounting: object = (),
    veto_accounting: object = (),
    baseline_pointer: object = None,
) -> Result[PerformanceResult]:
    """Mint a CT-32 performance-result container, value-or-refusal (DEC-0155).

    Suppression and veto accounting default to empty (zero) rather than omitted so
    a quiet period reads as zero suppressions and zero vetoes, never as missing
    evidence. A multi-role result is a policy rejection.
    """
    if not isinstance(result_label, ResultLabel):
        return invalid(
            "result_label",
            "every result carries the full AD-12 ResultLabel",
            given=type_name(result_label),
        )
    role = coerce_enum(AccountRole, account_binding_role)
    if role is None:
        return invalid(
            "account_binding_role",
            "the account-binding role is always present on the label; a single result "
            "never spans roles",
            given=repr(account_binding_role),
            allowed=[member.value for member in AccountRole],
        )
    multi = reject_multi_role_result(account_binding_role=role, population=population)
    if is_refusal(multi):
        return multi
    if not isinstance(population, PopulationDeclaration):
        return invalid(
            "population",
            "the population is a fingerprinted PopulationDeclaration",
            given=type_name(population),
        )
    if not isinstance(period, ResultPeriod):
        return invalid(
            "period",
            "the period is a declared ResultPeriod with knowledge-time bound",
            given=type_name(period),
        )
    measures = _measure_tuple(measure_set)
    if isinstance(measures, TypedRefusal):
        return measures
    suppressions = _suppression_tuple(suppression_accounting)
    if isinstance(suppressions, TypedRefusal):
        return suppressions
    vetoes = _veto_tuple(veto_accounting)
    if isinstance(vetoes, TypedRefusal):
        return vetoes
    baseline: Fingerprint | None
    if baseline_pointer is None:
        baseline = None
    elif isinstance(baseline_pointer, Fingerprint):
        baseline = baseline_pointer
    else:
        return invalid(
            "baseline_pointer",
            "the baseline pointer is a Fingerprint when present",
            given=repr(baseline_pointer),
        )
    return _Ok(
        PerformanceResult(
            result_label=result_label,
            account_binding_role=role,
            population=population,
            period=period,
            measure_set=measures,
            suppression_accounting=suppressions,
            veto_accounting=vetoes,
            baseline_pointer=baseline,
        )
    )


def reject_composite_expression(expression: object) -> TypedRefusal:
    """Refuse a score, rating, tier band, or weighted composite (DEC-0155).

    Alpha decay ships as evidence primitives only; no composite may express a result.
    """
    return policy(
        "measure_identity",
        "no score, rating, tier band, or weighted composite may express a result — "
        "alpha-decay mathematics is deferred and the evidence primitives are collected "
        "now because they cannot be back-filled",
        given=repr(expression),
        forbidden=sorted(FORBIDDEN_COMPOSITE_EXPRESSIONS),
    )


def reject_multi_role_result(*, account_binding_role: object, population: object) -> Result[None]:
    """Refuse a result that spans account roles (DEC-0155).

    The container carries exactly one account-binding role. A population declaring
    more than one role while the result claims a single-role span is a policy
    rejection when those roles differ from the binding role set of size > 1.
    """
    role = coerce_enum(AccountRole, account_binding_role)
    if role is None:
        return invalid(
            "account_binding_role",
            "a single result carries exactly one account-binding role",
            given=repr(account_binding_role),
            allowed=[member.value for member in AccountRole],
        )
    if not isinstance(population, PopulationDeclaration):
        return invalid(
            "population",
            "multi-role check reads a PopulationDeclaration",
            given=type_name(population),
        )
    if len(population.account_roles) > 1:
        return policy(
            "account_binding_role",
            "a single result may never span account roles; a multi-role population on "
            "one result is a policy rejection",
            roles=[member.value for member in population.account_roles],
        )
    if population.account_roles and population.account_roles[0] is not role:
        return policy(
            "account_binding_role",
            "the result's account-binding role must equal the population's declared role",
            result_role=role.value,
            population_role=population.account_roles[0].value,
        )
    return _Ok(None)


def check_publish_never_act(act: object) -> Result[None]:
    """Refuse any act a measurement producer might attempt (DEC-0155).

    Measurement publishes, never acts. Sizing, allocation, promotion, demotion,
    benching, and mode changes belong to the Book door or the operator.
    """
    resolved = coerce_enum(PublishAct, act)
    if resolved is None:
        # Also accept raw strings that name forbidden acts outside the enum casing.
        token = clean_str(act)
        if token is not None:
            lowered = token.casefold().replace("-", "_").replace(" ", "_")
            for member in PublishAct:
                if member.value.replace("-", "_") == lowered or member.name.casefold() == lowered:
                    resolved = member
                    break
        if resolved is None:
            return invalid(
                "act",
                "publish-never-act checks a named PublishAct",
                given=repr(act),
                allowed=[member.value for member in PublishAct],
            )
    return policy(
        "act",
        "measurement publishes, never acts: a measurement producer may not size, "
        "allocate, promote, demote, bench, or change a mode — authority belongs to "
        "the Book door (bench) or the operator (promotion)",
        act=resolved.value,
    )


def check_replay_never_gates_live(result: object, *, gating_live: object) -> Result[None]:
    """Refuse a replay-world result gating live money (DEC-0162, DEC-0169).

    A ``world = replay`` (or pre-GAP-0048) result can never gate live money; the
    admission-bar verdict over these results is a reader-derived fold, never a
    stored pass/fail that authorizes a live binding.
    """
    if not isinstance(result, PerformanceResult):
        return invalid(
            "result",
            "replay-never-gates-live reads a PerformanceResult",
            given=type_name(result),
        )
    if not isinstance(gating_live, bool):
        return invalid(
            "gating_live",
            "gating_live is a bool naming whether the caller would gate live money",
            given=repr(gating_live),
        )
    if gating_live and result.result_label.world is World.REPLAY:
        return policy(
            "world",
            "a replay-world result can never gate live money; the bar verdict is a "
            "reader-derived per-requirement fold, never a live authorization",
            world=World.REPLAY.value,
        )
    if gating_live and result.result_label.world is World.SIMULATED:
        return policy(
            "world",
            "a simulated-world result is reserved-unusable in V1 and can never gate live money",
            world=World.SIMULATED.value,
        )
    return _Ok(None)


# --- bench crossing as governed producer -------------------------------------


@dataclass(frozen=True, slots=True)
class BenchCrossingPublication:
    """Bench fold crossing published once as a governed producer (DEC-0155).

    The fold itself never benches: this publication is consumed by the Book door.
    Measurement publishes; the door acts.
    """

    binding_epoch: Fingerprint
    qualifying_loss_count: int
    threshold: int
    threshold_crossed: bool
    producer_contract_format_version: int

    def fingerprint(self) -> Result[Fingerprint]:
        """Content fingerprint of this publication."""
        return fingerprint(self.fp1_identity())

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this publication."""
        return {
            "class": "bench-crossing-publication",
            "binding_epoch": self.binding_epoch.value,
            "qualifying_loss_count": self.qualifying_loss_count,
            "threshold": self.threshold,
            "threshold_crossed": self.threshold_crossed,
            "producer_contract_format_version": self.producer_contract_format_version,
            "format_version": CT32_CONTRACT_FORMAT_VERSION,
        }


def publish_bench_crossing(
    fold: object, *, binding_epoch: object
) -> Result[BenchCrossingPublication]:
    """Publish a bench-fold crossing as one governed producer (DEC-0155).

    Does **not** bench, demote, or change a mode — it publishes the crossing for
    the Book door to consume.
    """
    if not isinstance(fold, BenchFoldResult):
        return invalid(
            "fold",
            "the bench crossing publishes a BenchFoldResult from the exit-record fold",
            given=type_name(fold),
        )
    if not isinstance(binding_epoch, Fingerprint):
        return invalid(
            "binding_epoch",
            "the bench crossing cites the binding epoch by fingerprint",
            given=repr(binding_epoch),
        )
    return _Ok(
        BenchCrossingPublication(
            binding_epoch=binding_epoch,
            qualifying_loss_count=fold.qualifying_loss_count,
            threshold=fold.threshold,
            threshold_crossed=fold.threshold_crossed,
            producer_contract_format_version=CT32_CONTRACT_FORMAT_VERSION,
        )
    )


def consume_bench_crossing_at_door(
    publication: object, *, door_identity: object
) -> Result[BenchCrossingPublication]:
    """Book-door consumption of a published bench crossing (DEC-0155).

    Returns the publication unchanged after validating the door identity — the
    act of benching (if any) is the door's authority, never the measurement
    producer's. A measurement producer calling this with intent to act is still
    refused via :func:`check_publish_never_act`.
    """
    if not isinstance(publication, BenchCrossingPublication):
        return invalid(
            "publication",
            "the Book door consumes a BenchCrossingPublication",
            given=type_name(publication),
        )
    door = clean_str(door_identity)
    if door is None:
        return invalid(
            "door_identity",
            "the consuming Book door names a non-blank identity",
            given=repr(door_identity),
        )
    return _Ok(publication)


def require_baseline_for_decay(result: object, *, for_decay_judgment: object) -> Result[None]:
    """Refuse a decay judgment without a baseline pointer (DEC-0155)."""
    if not isinstance(result, PerformanceResult):
        return invalid(
            "result",
            "baseline check reads a PerformanceResult",
            given=type_name(result),
        )
    if not isinstance(for_decay_judgment, bool):
        return invalid(
            "for_decay_judgment",
            "for_decay_judgment is a bool",
            given=repr(for_decay_judgment),
        )
    if for_decay_judgment and result.baseline_pointer is None:
        return unavailable(
            "baseline_pointer",
            "the baseline pointer is present for any result used in a decay judgment; "
            "its absence is an unavailable-dependency refusal",
        )
    return _Ok(None)


# --- helpers -----------------------------------------------------------------


def _fp_tuple(value: object, field: str) -> tuple[Fingerprint, ...] | TypedRefusal:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            field,
            f"{field} is a sequence of Fingerprint values",
            given=type_name(value),
        )
    out: list[Fingerprint] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, Fingerprint):
            return invalid(
                field,
                "binding epochs are cited by fingerprint, never by interval",
                index=index,
                given=repr(item),
            )
        out.append(item)
    return tuple(out)


def _role_tuple(value: object) -> tuple[AccountRole, ...] | TypedRefusal:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "account_roles",
            "the population declares which account roles are in scope",
            given=type_name(value),
        )
    out: list[AccountRole] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        role = coerce_enum(AccountRole, item)
        if role is None:
            return invalid(
                "account_roles",
                "every population role is an AccountRole",
                index=index,
                given=repr(item),
                allowed=[member.value for member in AccountRole],
            )
        out.append(role)
    return tuple(out)


def _measure_tuple(
    value: object,
) -> tuple[PerformanceMeasure | UndefinedMeasure, ...] | TypedRefusal:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "measure_set",
            "the measure set is an ordered sequence of PerformanceMeasure and "
            "UndefinedMeasure values",
            given=type_name(value),
        )
    out: list[PerformanceMeasure | UndefinedMeasure] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, (PerformanceMeasure, UndefinedMeasure)):
            return invalid(
                "measure_set",
                "every emitted measure is a PerformanceMeasure with a unit-kind or an "
                "UndefinedMeasure typed refusal a reader can tell apart from zero",
                index=index,
                given=type_name(item),
            )
        out.append(item)
    return tuple(out)


def _refusal_identity(refusal: TypedRefusal) -> dict[str, object]:
    content: dict[str, object] = {
        "category": refusal.category.value,
        "retryability": refusal.retryability.value,
        "context": _jsonish(refusal.context),
    }
    if refusal.after_condition_descriptor is not None:
        content["after_condition_descriptor"] = refusal.after_condition_descriptor
    return content


def _jsonish(value: object) -> object:
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return {str(key): _jsonish(item) for key, item in mapping.items()}
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return [_jsonish(item) for item in sequence]
    if isinstance(value, StrEnum):
        return value.value
    return value


def _suppression_tuple(value: object) -> tuple[SuppressionCount, ...] | TypedRefusal:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "suppression_accounting",
            "suppression accounting is a sequence of SuppressionCount values "
            "(empty means zero, never omitted)",
            given=type_name(value),
        )
    out: list[SuppressionCount] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, SuppressionCount):
            return invalid(
                "suppression_accounting",
                "every suppression row is a SuppressionCount",
                index=index,
                given=type_name(item),
            )
        out.append(item)
    return tuple(out)


def _veto_tuple(value: object) -> tuple[VetoCount, ...] | TypedRefusal:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "veto_accounting",
            "veto accounting is a sequence of VetoCount values (empty means zero, never omitted)",
            given=type_name(value),
        )
    out: list[VetoCount] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, VetoCount):
            return invalid(
                "veto_accounting",
                "every veto row is a VetoCount",
                index=index,
                given=type_name(item),
            )
        out.append(item)
    return tuple(out)
