"""Composition-root light/heavy gate (Story 25.14 / E7-R28 / AD-24).

Compose evaluates the inherited four-bound declaration over assembled indicator,
structure, labeler, and seat definitions and refuses a contradiction before Seal.
The effective composition class is assigned only here — child modules never
self-approve. Until the live-path rung has a recorded baseline on the deployment
tuple, every configuration is heavy by default and a light claim is refused.
Numeric budgets are never invented: proof is an injected harness flag, not a
hard-coded threshold (DEC-0128, DEC-0111, DEC-0208).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmn.host._refuse import clean_token, invalid, policy, unsupported

__all__ = [
    "CHILD_MODULES_MAY_SELF_APPROVE",
    "LIGHT_HEAVY_SURFACE",
    "WORKLOAD_KINDS",
    "CompositionClass",
    "CompositionClassAssignment",
    "FourBoundDeclaration",
    "ResolvedCompositionClasses",
    "WorkloadClaim",
    "WorkloadKind",
    "evaluate_workload_claim",
    "guard_synchronous_placement",
    "resolve_composition_classes",
    "workload_claim_identity_content",
]

LIGHT_HEAVY_SURFACE: Final[str] = "qmn.host.light_heavy"
# Effective class is root-owned; child packages never stamp it (E7-R28).
CHILD_MODULES_MAY_SELF_APPROVE: Final[bool] = False

WORKLOAD_KINDS: Final[tuple[str, ...]] = (
    "indicator",
    "structure",
    "labeler",
    "seat",
    "producer-definition",
)


class WorkloadKind(StrEnum):
    """Registered definition kinds Compose classifies under AD-24."""

    INDICATOR = "indicator"
    STRUCTURE = "structure"
    LABELER = "labeler"
    SEAT = "seat"
    PRODUCER = "producer-definition"


class CompositionClass(StrEnum):
    """Display-only effective composition class (never identity; DEC-0128)."""

    LIGHT = "light"
    HEAVY = "heavy"


@dataclass(frozen=True, slots=True)
class FourBoundDeclaration:
    """Declared light-claim bounds — contract surface, not a verdict (AD-24).

    Tokens and booleans only. No numeric latency or memory budgets live here;
    those await measured baselines (DEC-0111, DEC-0208).
    """

    per_update_cost_rung: str
    bounded_state: bool
    window_or_anchor_rule: str
    synchronous_availability: bool

    @classmethod
    def try_create(
        cls,
        *,
        per_update_cost_rung: object,
        bounded_state: object,
        window_or_anchor_rule: object,
        synchronous_availability: object,
    ) -> Result[FourBoundDeclaration]:
        """Validate and build a four-bound declaration."""
        rung = clean_token(per_update_cost_rung)
        if rung is None:
            return invalid(
                "per_update_cost_rung",
                "the per-update cost rung is a non-empty declared token",
                given=repr(per_update_cost_rung),
            )
        if not isinstance(bounded_state, bool):
            return invalid(
                "bounded_state",
                "bounded declared state size is a boolean bound",
                given=repr(bounded_state),
            )
        rule = clean_token(window_or_anchor_rule)
        if rule is None:
            return invalid(
                "window_or_anchor_rule",
                "the bounded evidence window or anchor-reset rule is a non-empty token",
                given=repr(window_or_anchor_rule),
            )
        if not isinstance(synchronous_availability, bool):
            return invalid(
                "synchronous_availability",
                "synchronous availability is a boolean bound",
                given=repr(synchronous_availability),
            )
        return Ok(
            cls(
                per_update_cost_rung=rung,
                bounded_state=bounded_state,
                window_or_anchor_rule=rule,
                synchronous_availability=synchronous_availability,
            )
        )

    def identity_content(self) -> dict[str, object]:
        """Fingerprintable declared-budget body (contract surface)."""
        return {
            "per_update_cost_rung": self.per_update_cost_rung,
            "bounded_state": self.bounded_state,
            "window_or_anchor_rule": self.window_or_anchor_rule,
            "synchronous_availability": self.synchronous_availability,
        }


@dataclass(frozen=True, slots=True)
class WorkloadClaim:
    """One registered definition's light/heavy declaration for Compose.

    ``declared_bounds`` present means the definition *claims* light. Absence is
    heavy by default (an Ok heavy verdict, not a refusal). ``benchmark_proven``
    is harness evidence that the four bounds cleared against a recorded baseline
    — never a numeric threshold invented here. ``self_approved_class`` is refused
    when set: only this module assigns the effective class.
    """

    kind: WorkloadKind
    definition_fp: Fingerprint
    declared_bounds: FourBoundDeclaration | None
    live_path_baseline_present: bool
    benchmark_proven: bool = False
    dependency_fps: tuple[Fingerprint, ...] = ()
    self_approved_class: CompositionClass | None = None

    @classmethod
    def try_create(
        cls,
        *,
        kind: object,
        definition_fp: object,
        declared_bounds: object = None,
        live_path_baseline_present: object,
        benchmark_proven: object = False,
        dependency_fps: object = (),
        self_approved_class: object = None,
    ) -> Result[WorkloadClaim]:
        """Validate and build one Compose workload claim."""
        if isinstance(kind, WorkloadKind):
            resolved_kind = kind
        else:
            token = clean_token(kind)
            if token is None or token not in WORKLOAD_KINDS:
                return invalid(
                    "kind",
                    "Compose classifies indicator, structure, labeler, seat, "
                    "or producer-definition workloads",
                    given=repr(kind),
                    allowed=list(WORKLOAD_KINDS),
                )
            resolved_kind = WorkloadKind(token)
        if not isinstance(definition_fp, Fingerprint):
            return invalid(
                "definition_fp",
                "a workload claim cites a Fingerprint definition identity",
                given=repr(definition_fp),
            )
        bounds: FourBoundDeclaration | None
        if declared_bounds is None:
            bounds = None
        elif isinstance(declared_bounds, FourBoundDeclaration):
            bounds = declared_bounds
        else:
            return invalid(
                "declared_bounds",
                "a light claim carries a FourBoundDeclaration or is omitted (heavy)",
                given=type(declared_bounds).__name__,
            )
        if not isinstance(live_path_baseline_present, bool):
            return invalid(
                "live_path_baseline_present",
                "baseline presence on the deployment tuple is a bool",
                given=repr(live_path_baseline_present),
            )
        if not isinstance(benchmark_proven, bool):
            return invalid(
                "benchmark_proven",
                "benchmark proof is a bool harness flag, never an invented budget",
                given=repr(benchmark_proven),
            )
        deps = _coerce_fp_tuple(dependency_fps, "dependency_fps")
        if is_refusal(deps):
            return deps
        approved: CompositionClass | None
        if self_approved_class is None:
            approved = None
        elif isinstance(self_approved_class, CompositionClass):
            approved = self_approved_class
        else:
            token = clean_token(self_approved_class)
            if token in {CompositionClass.LIGHT.value, CompositionClass.HEAVY.value}:
                approved = CompositionClass(token)
            else:
                return invalid(
                    "self_approved_class",
                    "self-approved class is light, heavy, or omitted",
                    given=repr(self_approved_class),
                )
        return Ok(
            cls(
                kind=resolved_kind,
                definition_fp=definition_fp,
                declared_bounds=bounds,
                live_path_baseline_present=live_path_baseline_present,
                benchmark_proven=benchmark_proven,
                dependency_fps=deps.value,
                self_approved_class=approved,
            )
        )

    def declaration_identity(self) -> dict[str, object]:
        """Class-affecting identity body (declared budget in; verdict out).

        Omits ``declared_bounds`` when absent — null is prohibited in fp1 content.
        """
        body: dict[str, object] = {
            "kind": self.kind.value,
            "definition_fp": self.definition_fp.value,
            "dependency_fps": [fp.value for fp in self.dependency_fps],
        }
        if self.declared_bounds is not None:
            body["declared_bounds"] = self.declared_bounds.identity_content()
        return body


@dataclass(frozen=True, slots=True)
class CompositionClassAssignment:
    """Root-assigned effective class for one workload (display-only)."""

    kind: WorkloadKind
    definition_fp: Fingerprint
    effective_class: CompositionClass
    reasons: tuple[str, ...]
    declared_bounds: FourBoundDeclaration | None


@dataclass(frozen=True, slots=True)
class ResolvedCompositionClasses:
    """Compose-time graph classification before Seal (Story 25.14)."""

    assignments: tuple[CompositionClassAssignment, ...]
    identity_content: Mapping[str, object]

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "identity_content", MappingProxyType(dict(self.identity_content))
        )

    def effective_class_for(self, definition_fp: Fingerprint) -> CompositionClass | None:
        for assignment in self.assignments:
            if assignment.definition_fp == definition_fp:
                return assignment.effective_class
        return None

    def by_definition(self) -> Mapping[str, str]:
        return {
            assignment.definition_fp.value: assignment.effective_class.value
            for assignment in self.assignments
        }


def _coerce_fp_tuple(value: object, field: str) -> Result[tuple[Fingerprint, ...]]:
    if value is None:
        return Ok(())
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(field, "dependency fingerprints are a sequence", given=type(value).__name__)
    out: list[Fingerprint] = []
    for item in cast("Sequence[object]", value):
        if not isinstance(item, Fingerprint):
            return invalid(
                field,
                "each dependency cite is a Fingerprint",
                given=repr(item),
            )
        out.append(item)
    return Ok(tuple(out))


def evaluate_workload_claim(claim: object) -> Result[CompositionClassAssignment]:
    """Evaluate one claim under AD-24; only the root returns the effective class.

    Heavy by default when no light claim is declared. A light claim without a
    recorded live-path baseline, unmet declared bounds, or missing benchmark
    proof is refused (policy rejection). A child-supplied
    ``self_approved_class`` is always refused.
    """
    if not isinstance(claim, WorkloadClaim):
        return invalid(
            "claim",
            "Compose evaluates a WorkloadClaim at the composition root",
            given=type(claim).__name__,
        )
    if claim.self_approved_class is not None:
        return policy(
            "self_approved_class",
            "no child module self-approves its effective composition class; "
            "only qmn.host.light_heavy assigns it (E7-R28)",
            kind=claim.kind.value,
            definition_fp=claim.definition_fp.value,
            attempted=claim.self_approved_class.value,
        )
    if claim.declared_bounds is None:
        return Ok(
            CompositionClassAssignment(
                kind=claim.kind,
                definition_fp=claim.definition_fp,
                effective_class=CompositionClass.HEAVY,
                reasons=(
                    "no declared four-bound budget: heavy by default until the "
                    "live-path rung has a recorded baseline (DEC-0128)",
                ),
                declared_bounds=None,
            )
        )
    if not claim.live_path_baseline_present:
        return policy(
            "declared_bounds",
            "a light claim without a recorded live-path rung baseline is refused "
            "at the composition-root gate; every configuration is heavy by default "
            "(AD-24, DEC-0128)",
            kind=claim.kind.value,
            definition_fp=claim.definition_fp.value,
            failure_id="compose.light_heavy.no_baseline",
        )
    unmet: list[str] = []
    bounds = claim.declared_bounds
    if not bounds.bounded_state:
        unmet.append("bound 2 (bounded declared state size) is not declared")
    if not bounds.synchronous_availability:
        unmet.append("bound 4 (synchronous availability) is not declared")
    if not claim.benchmark_proven:
        unmet.append(
            "bounds 1 and 3 are not benchmark-proven: the harness has not cleared "
            "the claim against the recorded baseline (no invented numeric budget)"
        )
    if unmet:
        return policy(
            "declared_bounds",
            "the light claim misses a declared or proven bound; the configuration "
            "is heavy by default (FM-6, DEC-0128)",
            kind=claim.kind.value,
            definition_fp=claim.definition_fp.value,
            unmet=tuple(unmet),
            failure_id="compose.light_heavy.unmet_bounds",
        )
    return Ok(
        CompositionClassAssignment(
            kind=claim.kind,
            definition_fp=claim.definition_fp,
            effective_class=CompositionClass.LIGHT,
            reasons=(
                "four bounds declared and benchmark-proven against the recorded "
                "live-path rung baseline on this deployment tuple",
                f"window-or-anchor rule: {bounds.window_or_anchor_rule}",
                f"per-update cost rung: {bounds.per_update_cost_rung}",
            ),
            declared_bounds=bounds,
        )
    )


def resolve_composition_classes(claims: object) -> Result[ResolvedCompositionClasses]:
    """Classify the assembled Compose graph and refuse contradictions before Seal.

    Each claim is evaluated at the root. A light assignment that depends on a
    heavy definition is a contradiction — light cannot place a heavy dependency
    on the synchronous trading path.
    """
    if not isinstance(claims, Sequence) or isinstance(claims, (str, bytes)):
        return invalid(
            "claims",
            "Compose resolves a sequence of WorkloadClaim values",
            given=type(claims).__name__,
        )
    typed: list[WorkloadClaim] = []
    for item in cast("Sequence[object]", claims):
        if not isinstance(item, WorkloadClaim):
            return invalid(
                "claims",
                "every assembled definition is a WorkloadClaim",
                given=type(item).__name__,
            )
        typed.append(item)

    seen: set[str] = set()
    for claim in typed:
        key = claim.definition_fp.value
        if key in seen:
            return invalid(
                "claims",
                "each definition fingerprint appears once in the Compose graph",
                definition_fp=key,
            )
        seen.add(key)

    assignments: list[CompositionClassAssignment] = []
    by_fp: dict[str, CompositionClassAssignment] = {}
    for claim in typed:
        evaluated = evaluate_workload_claim(claim)
        if is_refusal(evaluated):
            return evaluated
        assignments.append(evaluated.value)
        by_fp[claim.definition_fp.value] = evaluated.value

    for claim in typed:
        parent = by_fp[claim.definition_fp.value]
        if parent.effective_class is not CompositionClass.LIGHT:
            continue
        for dep_fp in claim.dependency_fps:
            child = by_fp.get(dep_fp.value)
            if child is None:
                return policy(
                    "dependency_fps",
                    "a light claim's assembled dependency must be present in the "
                    "Compose graph so the root can evaluate the contradiction",
                    parent=claim.definition_fp.value,
                    missing_dependency=dep_fp.value,
                    failure_id="compose.light_heavy.missing_dependency",
                )
            if child.effective_class is CompositionClass.HEAVY:
                return policy(
                    "dependency_fps",
                    "a light claim that depends on a heavy definition contradicts "
                    "the four-bound envelope; Compose refuses before Seal (AD-24)",
                    parent=claim.definition_fp.value,
                    parent_kind=claim.kind.value,
                    heavy_dependency=dep_fp.value,
                    heavy_kind=child.kind.value,
                    failure_id="compose.light_heavy.heavy_dependency",
                )

    identity = workload_claim_identity_content(typed)
    return Ok(
        ResolvedCompositionClasses(
            assignments=tuple(assignments),
            identity_content=identity,
        )
    )


def workload_claim_identity_content(
    claims: Sequence[WorkloadClaim],
) -> dict[str, object]:
    """Fingerprintable class-affecting declaration set (verdict excluded)."""
    bodies = sorted(
        (claim.declaration_identity() for claim in claims),
        key=lambda body: (str(body["kind"]), str(body["definition_fp"])),
    )
    return {"class": "workload_claim_declarations", "claims": bodies}


def guard_synchronous_placement(assignment: object) -> Result[None]:
    """Keep heavy definitions off the synchronous trading path (FM-3 / DEC-0128).

    A heavy effective class returns ``unsupported capability``; light is permitted.
    """
    if not isinstance(assignment, CompositionClassAssignment):
        return invalid(
            "assignment",
            "synchronous placement guards a root CompositionClassAssignment",
            given=type(assignment).__name__,
        )
    if assignment.effective_class is CompositionClass.HEAVY:
        return unsupported(
            "synchronous_placement",
            "a heavy configuration's synchronous entry point returns unsupported "
            "capability; heavy runs off the trading path, computed once and fanned "
            "out through the same contract (FM-3, DEC-0128)",
            kind=assignment.kind.value,
            definition_fp=assignment.definition_fp.value,
            effective_class=assignment.effective_class.value,
        )
    return Ok(None)
