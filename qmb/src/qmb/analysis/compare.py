"""compare_runs is a readout of cited CT-32 fields, not an analysis method.

Story 35.5: overlaying two CT-32s stamps nothing. The function reads cited
fields and returns a readout. It mints no artifact, no ledger line, no
confirmation label, and consumes no ExecutionEnvironment occupancy
(FR-W26, SCN-0016 Then (3), DEC-0273).

F07 synthetic portfolio combination is deferred: neither analysis.project nor
analysis.rerun implements combining two bots' equity/trade streams
(FR-W21, AR-W06). Labels stay parent-shaped — CT-32 and B-4 gain no ``lane``
or ``analysis_method`` field (FR-W28, NFR-W07, DEC-0283). L20 still forbids
gating live money on replay-world verdicts.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Final, cast

from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal
from qmf.risk.performance import PerformanceResult

from qmb._refuse import clean_token, invalid, policy
from qmb.analysis.deferred import (
    F07_FEATURE,
    F07_FIELDS,
    refuse_live_money_gating,
    refuse_synthetic_portfolio,
)

if TYPE_CHECKING:
    from qmb.results.interpret import FieldDiff

__all__ = [
    "COMPARE_RUNS_CLASS",
    "COMPARE_RUNS_IS_ANALYSIS_METHOD",
    "COMPARE_RUNS_MINTS_CT32",
    "COMPARE_RUNS_MINTS_EXPERIMENT_SPEC",
    "COMPARE_RUNS_OCCUPANCY",
    "F07_FEATURE",
    "F07_FIELDS",
    "CompareReadout",
    "compare_runs",
    "compare_runs_identity",
    "refuse_live_money_gating",
    "refuse_synthetic_portfolio",
]

COMPARE_RUNS_CLASS: Final[str] = "qmb-compare-readout"
COMPARE_RUNS_OCCUPANCY: Final[str] = "query"
COMPARE_RUNS_MINTS_CT32: Final[bool] = False
COMPARE_RUNS_MINTS_EXPERIMENT_SPEC: Final[bool] = False
COMPARE_RUNS_IS_ANALYSIS_METHOD: Final[bool] = False
_INTERPRETATION_SOURCE: Final[str] = "ct-32"
_OCCUPANCY_RUN_TOKENS: Final[frozenset[str]] = frozenset({"job", "run"})
_LEDGER_FIELDS: Final[tuple[str, ...]] = ("append_ledger", "ledger", "ledger_line")
_CT32_FIELDS: Final[tuple[str, ...]] = ("mint_ct32", "new_ct32")
_SPEC_FIELDS: Final[tuple[str, ...]] = (
    "experiment_spec",
    "mint_experiment_spec",
    "successor",
)
_LABEL_FIELDS: Final[tuple[str, ...]] = ("analysis_method", "lane", "workbench_lane")
_ROLE_FIELDS: Final[tuple[str, ...]] = ("b4_role", "confirmation_label", "role")
_FALSE_TOKENS: Final[frozenset[str]] = frozenset({"0", "false", "no"})
_F07_SET: Final[frozenset[str]] = frozenset(F07_FIELDS)


@dataclass(frozen=True, slots=True)
class CompareReadout:
    """Field-wise readout of two cited CT-32s. Not an artifact and not a method."""

    same_world: bool
    same_account_binding_role: bool
    matching_paths: tuple[str, ...]
    differing: tuple[FieldDiff, ...]
    occupancy: str = COMPARE_RUNS_OCCUPANCY
    mints_ct32: bool = False
    mints_experiment_spec: bool = False
    appends_ledger: bool = False
    confirmation_label: None = None
    is_analysis_method: bool = False
    is_admission_evidence: bool = False
    b4_role: None = None
    consumes_occupancy: bool = False
    source: str = _INTERPRETATION_SOURCE
    parsed_html: bool = False
    publish_only: bool = True

    def fp1_identity(self) -> dict[str, object]:
        """Identity-bearing readout. Package SemVer is omitted; nothing is minted."""
        return {
            "appends_ledger": False,
            "class": COMPARE_RUNS_CLASS,
            "command": "compare_runs",
            "consumes_occupancy": False,
            "differing_paths": [row.path for row in self.differing],
            "is_admission_evidence": False,
            "is_analysis_method": False,
            "matching_path_count": len(self.matching_paths),
            "mints_ct32": False,
            "mints_experiment_spec": False,
            "occupancy": COMPARE_RUNS_OCCUPANCY,
            "same_account_binding_role": self.same_account_binding_role,
            "same_world": self.same_world,
            "source": _INTERPRETATION_SOURCE,
        }


def compare_runs_identity() -> dict[str, object]:
    """Identity-bearing compare_runs fields. Package SemVer is omitted."""
    return {
        "appends_ledger": False,
        "class": COMPARE_RUNS_CLASS,
        "command": "compare_runs",
        "consumes_occupancy": False,
        "is_analysis_method": COMPARE_RUNS_IS_ANALYSIS_METHOD,
        "mints_ct32": COMPARE_RUNS_MINTS_CT32,
        "mints_experiment_spec": COMPARE_RUNS_MINTS_EXPERIMENT_SPEC,
        "occupancy": COMPARE_RUNS_OCCUPANCY,
    }


def compare_runs(
    left: object = None,
    right: object = None,
    *,
    occupancy: object = None,
    ledger: object = None,
    append_ledger: object = None,
    ledger_line: object = None,
    mint_ct32: object = None,
    new_ct32: object = None,
    experiment_spec: object = None,
    successor: object = None,
    mint_experiment_spec: object = None,
    role: object = None,
    b4_role: object = None,
    confirmation_label: object = None,
    analysis_method: object = None,
    lane: object = None,
    workbench_lane: object = None,
    gating_live: object = None,
    portfolio: object = None,
    synthetic_portfolio: object = None,
    combine: object = None,
    combination: object = None,
    **extra: object,
) -> Result[CompareReadout]:
    """Read cited CT-32 fields and return a readout. Stamp nothing (FR-W26)."""
    blocked = refuse_synthetic_portfolio(
        extra=extra,
        portfolio=portfolio,
        synthetic_portfolio=synthetic_portfolio,
        combine=combine,
        combination=combination,
    )
    if blocked is not None:
        return blocked
    extra_blocked = _refuse_unknown_extra(extra)
    if extra_blocked is not None:
        return extra_blocked
    side = _refuse_side_effects(
        occupancy=occupancy,
        ledger=ledger,
        append_ledger=append_ledger,
        ledger_line=ledger_line,
        mint_ct32=mint_ct32,
        new_ct32=new_ct32,
        experiment_spec=experiment_spec,
        successor=successor,
        mint_experiment_spec=mint_experiment_spec,
        role=role,
        b4_role=b4_role,
        confirmation_label=confirmation_label,
        analysis_method=analysis_method,
        lane=lane,
        workbench_lane=workbench_lane,
    )
    if side is not None:
        return side
    if left is None or right is None:
        return invalid(
            "left" if left is None else "right",
            "compare_runs reads two cited CT-32 performance-results",
        )
    gated = refuse_live_money_gating(gating_live=gating_live, world=_cited_world(left))
    if gated is not None:
        return gated
    from qmb.results.interpret import (  # noqa: PLC0415 — avoid qmb.results import cycle
        compare_runs as read_cited_fields,
    )

    compared = read_cited_fields(left, right)
    if is_refusal(compared):
        return compared
    body = compared.value
    return Ok(
        CompareReadout(
            same_world=body.same_world,
            same_account_binding_role=body.same_account_binding_role,
            matching_paths=body.matching_paths,
            differing=body.differing,
            parsed_html=body.parsed_html,
            publish_only=body.publish_only,
            source=body.source,
        )
    )


def _refuse_side_effects(**fields: object) -> TypedRefusal | None:
    occupancy = fields.get("occupancy")
    if occupancy is not None:
        token = _fold(clean_token(occupancy) or "")
        if token in _OCCUPANCY_RUN_TOKENS:
            return policy(
                "occupancy",
                "compare_runs is a query: it consumes no ExecutionEnvironment occupancy, "
                "mints no artifact, and mints no confirmation label (FR-W26, DEC-0276)",
                occupancy=COMPARE_RUNS_OCCUPANCY,
                mints_ct32=False,
                mints_experiment_spec=False,
                confirmation_label=None,
                is_analysis_method=False,
            )
        if token not in {"", "none", "query"}:
            return invalid(
                "occupancy",
                "compare_runs occupancy is query — a readout, never a run",
                given=repr(occupancy),
                occupancy=COMPARE_RUNS_OCCUPANCY,
            )
    ledger = _requested_field(fields, _LEDGER_FIELDS)
    if ledger is not None:
        return policy(
            ledger,
            "compare_runs appends no QMB ledger line; it is a readout, not a run "
            "(FR-W26, SCN-0016, DEC-0273)",
            occupancy=COMPARE_RUNS_OCCUPANCY,
            appends_ledger=False,
            mints_ct32=False,
        )
    minted = _requested_field(fields, _CT32_FIELDS)
    if minted is not None:
        return policy(
            minted,
            "compare_runs mints no artifact; it reads cited CT-32 fields "
            "(FR-W26, SCN-0016, DEC-0273)",
            occupancy=COMPARE_RUNS_OCCUPANCY,
            mints_ct32=False,
        )
    spec = _requested_field(fields, _SPEC_FIELDS)
    if spec is not None:
        return policy(
            spec,
            "compare_runs mints no ExperimentSpec successor; it is a query (FR-W11, DEC-0276)",
            occupancy=COMPARE_RUNS_OCCUPANCY,
            mints_experiment_spec=False,
        )
    labels = _requested_field(fields, _LABEL_FIELDS)
    if labels is not None:
        return policy(
            labels,
            "analysis_method and lane are not CT-32 or B-4 fields; compare_runs is "
            "not an analysis method and stamps no workbench label "
            "(FR-W26, FR-W28, NFR-W07, DEC-0283)",
            occupancy=COMPARE_RUNS_OCCUPANCY,
            is_analysis_method=False,
            confirmation_label=None,
        )
    role = _requested_field(fields, _ROLE_FIELDS)
    if role is not None:
        return policy(
            role,
            "compare_runs mints no confirmation label and no B-4 role; it is a "
            "readout of cited CT-32 fields (FR-W26, FR-W28, SCN-0016)",
            occupancy=COMPARE_RUNS_OCCUPANCY,
            confirmation_label=None,
            b4_role=None,
            is_admission_evidence=False,
        )
    return None


def _refuse_unknown_extra(extra: Mapping[str, object]) -> TypedRefusal | None:
    unknown = [name for name, value in extra.items() if value is not None]
    if not unknown:
        return None
    folded = _fold(unknown[0])
    if folded in _F07_SET:
        return refuse_synthetic_portfolio(extra={unknown[0]: extra[unknown[0]]})
    return invalid(
        unknown[0],
        "compare_runs reads two cited CT-32s; extra fields that would combine "
        "equity/trade streams are F07 deferred, and workbench labels are not "
        "CT-32 or B-4 fields (FR-W21, FR-W26, FR-W28)",
        given=unknown[0],
        extra=unknown,
        occupancy=COMPARE_RUNS_OCCUPANCY,
        is_analysis_method=False,
    )


def _cited_world(source: object) -> str | None:
    if isinstance(source, PerformanceResult):
        return source.result_label.world.value
    if isinstance(source, Mapping) and not isinstance(source, (str, bytes)):
        body = cast("Mapping[str, object]", source)
        label = body.get("result_label")
        if isinstance(label, Mapping):
            world = cast("Mapping[str, object]", label).get("world")
            if isinstance(world, str) and world.strip() != "":
                return world
    return None


def _requested_field(fields: Mapping[str, object], names: tuple[str, ...]) -> str | None:
    for name in names:
        if _is_requested(fields.get(name)):
            return name
    return None


def _is_requested(value: object) -> bool:
    if value is None or value is False:
        return False
    token = clean_token(value)
    return not (token is not None and _fold(token) in _FALSE_TOKENS)


def _fold(token: str) -> str:
    return token.strip().replace("-", "_").replace(" ", "_").casefold()
