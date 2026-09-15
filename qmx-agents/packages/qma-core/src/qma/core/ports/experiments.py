"""Content-addressed ExperimentSpec (CT-47; AD-17; DEC-0316; FR-Q54).

Identity is inherited ``fp1`` over canonical spec content. ``code_ref`` is a git
commit and is present only for a code change. Parameter and configuration
changes use ``resolved_config_ref``. Typed strategy-mechanism nouns stay
Deferred GAP-0085.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qma.core.content import content_address
from qmf.core import Ok, Result, is_refusal
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal

__all__ = [
    "ANALYSIS_PUBLISHED_KIND",
    "CALLER_DECLARED_LANE_FIELDS",
    "COORDINATED_CONTINUITY_KIND",
    "COPIED_EXPERIMENT_EVIDENCE_KEYS",
    "CT07_V1_EDGE_TYPES",
    "EXPERIMENT_CHANGE_CODE",
    "EXPERIMENT_CHANGE_KINDS",
    "EXPERIMENT_CHANGE_RESOLVED_CONFIG",
    "EXPERIMENT_EVIDENCE_METADATA_KEYS",
    "EXPERIMENT_LEDGER_WORKBENCH_LANE",
    "EXPERIMENT_LINEAGE_EDGE_TYPE",
    "GAP_0085_STRATEGY_MECHANISMS",
    "GIT_COMMIT_REF_PREFIX",
    "QMB_LEDGER_WORKBENCH_LANE",
    "REFUSED_CONTINUITY_KINDS",
    "WORKBENCH_LANE_COORDINATED",
    "WORKBENCH_LANE_GOVERNED",
    "ExperimentSpec",
    "admit_coordinated_continuity",
    "admit_experiment_evidence_body",
    "coordinated_run_labels",
    "is_git_branch_ref",
    "is_git_commit_ref",
    "parse_experiment_spec",
    "parse_git_commit_ref",
    "refuse_caller_declared_lane_fields",
]


EXPERIMENT_CHANGE_CODE: Final[str] = "code"
EXPERIMENT_CHANGE_RESOLVED_CONFIG: Final[str] = "resolved_config"
EXPERIMENT_CHANGE_KINDS: Final[frozenset[str]] = frozenset(
    {EXPERIMENT_CHANGE_CODE, EXPERIMENT_CHANGE_RESOLVED_CONFIG}
)

GIT_COMMIT_REF_PREFIX: Final[str] = "git:commit:"
_GIT_COMMIT_RE: Final[re.Pattern[str]] = re.compile(r"^git:commit:[0-9a-f]{40}$")
_GIT_BRANCH_PREFIXES: Final[tuple[str, ...]] = (
    "git:branch:",
    "refs/heads/",
    "refs/remotes/",
    "refs/tags/",
)
_BARE_BRANCH_NAMES: Final[frozenset[str]] = frozenset(
    {"head", "main", "master", "develop", "trunk", "default"}
)

# CT-07 V1 tokens (DEC-0114). Not a second enum — ExperimentSpec lineage uses
# these strings and the daemon stamps them onto qmf-registry LineageEdge values.
CT07_V1_EDGE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "supersedes",
        "promoted-from",
        "occurrence-of",
        "corroborates",
        "disagrees-with",
        "confirmed-as",
        "confirmation",
        "invalidation",
        "interaction",
        "out-of-sequence",
        "continues-performance",
        "carries-ledger",
        "enacts",
        "branches-from",
    }
)
EXPERIMENT_LINEAGE_EDGE_TYPE: Final[str] = "branches-from"

# Deferred GAP-0085 — QML / qmf-registry own these nouns; QMA must not mint them.
GAP_0085_STRATEGY_MECHANISMS: Final[frozenset[str]] = frozenset(
    {
        "entrymechanism",
        "exitmechanism",
        "filter",
        "sessionrule",
        "positionrule",
        "invalidationrule",
        "entry_mechanism",
        "exit_mechanism",
        "session_rule",
        "position_rule",
        "invalidation_rule",
    }
)

_VERSION_KEYS: Final[frozenset[str]] = frozenset({"model", "harness"})

# Coordinated continuity is ExperimentSpec fp1. Project / Workspace are UX aliases
# only and are never identity (DEC-0284).
COORDINATED_CONTINUITY_KIND: Final[str] = "experiment_spec"
ANALYSIS_PUBLISHED_KIND: Final[str] = "analysis.published"
REFUSED_CONTINUITY_KINDS: Final[frozenset[str]] = frozenset({"project", "workspace"})

# Experiment Ledger bodies store _refs. JSONL / CT-32 copies are not product truth.
COPIED_EXPERIMENT_EVIDENCE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "jsonl",
        "qmb_jsonl",
        "run_jsonl",
        "ledger_jsonl",
        "copied_jsonl",
        "merged_jsonl",
        "ct32",
        "ct_32",
        "ct32_payload",
        "ct32_body",
        "copied_ct32",
        "merged_ct32",
        "qmb_ledger",
        "run_ledger",
        "run_ledger_lines",
        "ledger_lines",
        "jsonl_copy",
    }
)
EXPERIMENT_EVIDENCE_METADATA_KEYS: Final[frozenset[str]] = frozenset(
    {"note", "kind", "workbench_lane"}
)
WORKBENCH_LANE_GOVERNED: Final[str] = "governed"
WORKBENCH_LANE_COORDINATED: Final[str] = "coordinated"
QMB_LEDGER_WORKBENCH_LANE: Final[str] = WORKBENCH_LANE_GOVERNED
EXPERIMENT_LEDGER_WORKBENCH_LANE: Final[str] = WORKBENCH_LANE_COORDINATED
CALLER_DECLARED_LANE_FIELDS: Final[frozenset[str]] = frozenset(
    {"analysis_method", "lane", "workbench_lane"}
)
_COLLAPSED_LANE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "both_lanes",
        "lanes",
        "qmb_ledger_workbench_lane",
        "experiment_ledger_workbench_lane",
    }
)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _normalize_mechanism_token(token: str) -> str:
    return token.strip().casefold().replace("-", "_")


def is_git_commit_ref(value: object) -> bool:
    """True when ``value`` is a full ``git:commit:<40-hex>`` object id."""
    return isinstance(value, str) and _GIT_COMMIT_RE.fullmatch(value) is not None


def is_git_branch_ref(value: object) -> bool:
    """True when ``value`` names a git branch (or other non-commit git ref)."""
    if not isinstance(value, str) or value.strip() == "":
        return False
    token = value.strip()
    if is_git_commit_ref(token):
        return False
    lowered = token.casefold()
    if lowered.startswith(_GIT_BRANCH_PREFIXES):
        return True
    if lowered in _BARE_BRANCH_NAMES:
        return True
    if lowered.startswith("git:"):
        return True
    if token.startswith("refs/"):
        return True
    return "/" in token


def parse_git_commit_ref(value: object) -> Result[str]:
    """Admit a git commit object id; refuse a branch or other git ref."""
    if is_git_commit_ref(value):
        return Ok(cast("str", value))
    if is_git_branch_ref(value):
        return _policy(
            "code_ref",
            "code changes use a git commit ref; git-branch-per-parameter "
            "lineage is Cut (DEC-0316; DEC-0376; FR-Q54)",
            given=repr(value),
        )
    return _invalid(
        "code_ref",
        "code_ref is git:commit:<40-hex> and is present only when code changes (CT-47; FR-Q54)",
        given=repr(value),
    )


def _refuse_gap_0085(mechanisms: object, extra: Mapping[str, object] | None) -> TypedRefusal | None:
    if mechanisms is not None:
        return _policy(
            "mechanisms",
            "typed strategy-mechanism decomposition (EntryMechanism, "
            "ExitMechanism, Filter, SessionRule, PositionRule, "
            "InvalidationRule) is Deferred GAP-0085; ExperimentSpec does not "
            "mint those nouns (DEC-0313; FR-Q54)",
        )
    if extra is None:
        return None
    hits = [key for key in extra if _normalize_mechanism_token(key) in GAP_0085_STRATEGY_MECHANISMS]
    if hits:
        return _policy(
            "mechanisms",
            "typed strategy-mechanism decomposition is Deferred GAP-0085; "
            "QMA carries candidates and lineage edges only (DEC-0313; FR-Q54)",
            fields=hits,
        )
    return None


def _parse_required_ref(value: object, field: str) -> Result[str]:
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(field, f"ExperimentSpec requires {field}")
    return Ok(value.strip())


def _parse_fp1_ref(value: object, field: str) -> Result[str]:
    if is_git_branch_ref(value) or (
        isinstance(value, str) and value.startswith(GIT_COMMIT_REF_PREFIX)
    ):
        return _policy(
            field,
            "parameter and configuration changes use a resolved-config "
            "fp1 reference, never a git commit or branch (CT-47; FR-Q54)",
            given=repr(value),
        )
    parsed = Fingerprint.try_create(value)
    if is_refusal(parsed):
        return _invalid(
            field,
            f"{field} is an fp1 content address (fp1:sha256:<hex>)",
            given=repr(value),
        )
    return Ok(parsed.value.value)


def _parse_seed(value: object) -> Result[int]:
    if isinstance(value, bool) or not isinstance(value, int):
        return _invalid("seed", "seed is an integer (CT-47; FR-Q54)", given=repr(value))
    return Ok(value)


def _parse_version(value: object) -> Result[Mapping[str, str]]:
    if not isinstance(value, Mapping):
        return _invalid(
            "model_and_harness_version",
            "model_and_harness_version is an object with model and harness",
            given=repr(value),
        )
    body = cast("Mapping[str, object]", value)
    parsed: dict[str, str] = {}
    for key in ("model", "harness"):
        item = body.get(key)
        if not isinstance(item, str) or item.strip() == "":
            return _invalid(
                "model_and_harness_version",
                "model_and_harness_version requires non-empty model and harness",
                missing=key,
            )
        parsed[key] = item.strip()
    extra = [key for key in body if key not in _VERSION_KEYS]
    if extra:
        return _invalid(
            "model_and_harness_version",
            "model_and_harness_version carries only model and harness",
            extra=extra,
        )
    return Ok(MappingProxyType(parsed))


def _parse_cost_assumptions(value: object) -> Result[Mapping[str, int]]:
    if not isinstance(value, Mapping):
        return _invalid(
            "cost_assumptions",
            "cost_assumptions is a USD-denominated integer declaration map",
            given=repr(value),
        )
    body = cast("Mapping[object, object]", value)
    parsed: dict[str, int] = {}
    for key, item in body.items():
        if not isinstance(key, str) or key.strip() == "":
            return _invalid("cost_assumptions", "cost assumption keys are non-empty strings")
        if isinstance(item, bool) or not isinstance(item, int):
            return _invalid(
                "cost_assumptions",
                "cost assumption values are integers (USD-denominated; no floats)",
                key=key,
                given=repr(item),
            )
        parsed[key.strip()] = item
    return Ok(MappingProxyType(parsed))


def _parse_optional_ledger_ref(value: object) -> Result[str | None]:
    if value is None:
        return Ok(None)
    if not isinstance(value, str) or value.strip() == "":
        return _invalid(
            "experiment_ledger_ref",
            "experiment_ledger_ref is a non-empty ledger reference when present",
        )
    return Ok(value.strip())


def _identity_content(
    *,
    data_ref: str,
    environment_ref: str,
    seed: int,
    model_and_harness_version: Mapping[str, str],
    cost_assumptions: Mapping[str, int],
    resolved_config_ref: str,
    code_ref: str | None,
) -> dict[str, object]:
    content: dict[str, object] = {
        "class": "experiment-spec",
        "cost_assumptions": dict(cost_assumptions),
        "data_ref": data_ref,
        "environment_ref": environment_ref,
        "model_and_harness_version": dict(model_and_harness_version),
        "resolved_config_ref": resolved_config_ref,
        "seed": seed,
    }
    if code_ref is not None:
        content["code_ref"] = code_ref
    return content


@dataclass(frozen=True, slots=True)
class ExperimentSpec:
    """Content-addressed experiment recipe. Lineage accrues as CT-07 edges."""

    data_ref: str
    environment_ref: str
    seed: int
    model_and_harness_version: Mapping[str, str]
    cost_assumptions: Mapping[str, int]
    resolved_config_ref: str
    spec_fp1: str
    code_ref: str | None = None
    experiment_ledger_ref: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "model_and_harness_version",
            MappingProxyType(dict(self.model_and_harness_version)),
        )
        object.__setattr__(
            self,
            "cost_assumptions",
            MappingProxyType(dict(self.cost_assumptions)),
        )

    def identity_content(self) -> Mapping[str, object]:
        """Canonical identity; absent optional keys are omitted, never null."""
        return MappingProxyType(
            _identity_content(
                data_ref=self.data_ref,
                environment_ref=self.environment_ref,
                seed=self.seed,
                model_and_harness_version=self.model_and_harness_version,
                cost_assumptions=self.cost_assumptions,
                resolved_config_ref=self.resolved_config_ref,
                code_ref=self.code_ref,
            )
        )

    def to_payload(self) -> Mapping[str, object]:
        payload = dict(self.identity_content())
        payload["spec_fp1"] = self.spec_fp1
        if self.experiment_ledger_ref is not None:
            payload["experiment_ledger_ref"] = self.experiment_ledger_ref
        return MappingProxyType(payload)

    def with_ledger_ref(self, ledger_ref: str) -> ExperimentSpec:
        """Attach the Experiment Ledger link without changing identity."""
        return ExperimentSpec(
            data_ref=self.data_ref,
            environment_ref=self.environment_ref,
            seed=self.seed,
            model_and_harness_version=self.model_and_harness_version,
            cost_assumptions=self.cost_assumptions,
            resolved_config_ref=self.resolved_config_ref,
            spec_fp1=self.spec_fp1,
            code_ref=self.code_ref,
            experiment_ledger_ref=ledger_ref,
        )

    @classmethod
    def try_create(
        cls,
        *,
        data_ref: object,
        environment_ref: object,
        seed: object,
        model_and_harness_version: object,
        cost_assumptions: object,
        resolved_config_ref: object,
        code_ref: object = None,
        experiment_ledger_ref: object = None,
        mechanisms: object = None,
        extra: Mapping[str, object] | None = None,
    ) -> Result[ExperimentSpec]:
        blocked = _refuse_gap_0085(mechanisms, extra)
        if blocked is not None:
            return blocked
        parsed_data = _parse_required_ref(data_ref, "data_ref")
        if is_refusal(parsed_data):
            return parsed_data
        parsed_env = _parse_required_ref(environment_ref, "environment_ref")
        if is_refusal(parsed_env):
            return parsed_env
        parsed_seed = _parse_seed(seed)
        if is_refusal(parsed_seed):
            return parsed_seed
        parsed_version = _parse_version(model_and_harness_version)
        if is_refusal(parsed_version):
            return parsed_version
        parsed_cost = _parse_cost_assumptions(cost_assumptions)
        if is_refusal(parsed_cost):
            return parsed_cost
        parsed_config = _parse_fp1_ref(resolved_config_ref, "resolved_config_ref")
        if is_refusal(parsed_config):
            return parsed_config
        parsed_code: str | None = None
        if code_ref is not None:
            parsed_commit = parse_git_commit_ref(code_ref)
            if is_refusal(parsed_commit):
                return parsed_commit
            parsed_code = parsed_commit.value
        parsed_ledger = _parse_optional_ledger_ref(experiment_ledger_ref)
        if is_refusal(parsed_ledger):
            return parsed_ledger
        identity = _identity_content(
            data_ref=parsed_data.value,
            environment_ref=parsed_env.value,
            seed=parsed_seed.value,
            model_and_harness_version=parsed_version.value,
            cost_assumptions=parsed_cost.value,
            resolved_config_ref=parsed_config.value,
            code_ref=parsed_code,
        )
        addressed = content_address(identity)
        if is_refusal(addressed):
            return addressed
        return Ok(
            cls(
                data_ref=parsed_data.value,
                environment_ref=parsed_env.value,
                seed=parsed_seed.value,
                model_and_harness_version=parsed_version.value,
                cost_assumptions=parsed_cost.value,
                resolved_config_ref=parsed_config.value,
                spec_fp1=addressed.value.value,
                code_ref=parsed_code,
                experiment_ledger_ref=parsed_ledger.value,
            )
        )

    def with_change(
        self,
        *,
        change: object,
        resolved_config_ref: object = None,
        code_ref: object = None,
        data_ref: object = None,
        environment_ref: object = None,
        seed: object = None,
        model_and_harness_version: object = None,
        cost_assumptions: object = None,
        mechanisms: object = None,
        extra: Mapping[str, object] | None = None,
    ) -> Result[ExperimentSpec]:
        """Mint a successor spec. Never mutates this record."""
        if change not in EXPERIMENT_CHANGE_KINDS:
            return _invalid(
                "change",
                "experiment change is code or resolved_config (CT-47; FR-Q54)",
                given=repr(change),
            )
        if change == EXPERIMENT_CHANGE_CODE:
            if code_ref is None:
                return _invalid(
                    "code_ref",
                    "a code change carries a git commit ref (CT-47; FR-Q54)",
                )
            next_code = code_ref
            next_config = (
                self.resolved_config_ref if resolved_config_ref is None else resolved_config_ref
            )
        else:
            if code_ref is not None:
                return _policy(
                    "code_ref",
                    "an unchanged-code parameter or configuration change is "
                    "identified by its resolved-config reference rather than a "
                    "code reference (CT-47; FR-Q54)",
                    given=repr(code_ref),
                )
            if resolved_config_ref is None:
                return _invalid(
                    "resolved_config_ref",
                    "a parameter or configuration change carries a resolved-config "
                    "reference (CT-47; FR-Q54)",
                )
            next_code = None
            next_config = resolved_config_ref
        created = self.try_create(
            data_ref=self.data_ref if data_ref is None else data_ref,
            environment_ref=self.environment_ref if environment_ref is None else environment_ref,
            seed=self.seed if seed is None else seed,
            model_and_harness_version=(
                dict(self.model_and_harness_version)
                if model_and_harness_version is None
                else model_and_harness_version
            ),
            cost_assumptions=(
                dict(self.cost_assumptions) if cost_assumptions is None else cost_assumptions
            ),
            resolved_config_ref=next_config,
            code_ref=next_code,
            mechanisms=mechanisms,
            extra=extra,
        )
        if is_refusal(created):
            return created
        successor = created.value
        if successor.spec_fp1 == self.spec_fp1:
            return _invalid(
                "change",
                "a successor ExperimentSpec must differ in identity content (CT-47; FR-Q54)",
            )
        return Ok(successor)


def _normalize_continuity_token(value: str) -> str:
    return value.strip().casefold().replace(" ", "_").replace("-", "_")


def admit_coordinated_continuity(kind: object) -> Result[str]:
    """Admit ExperimentSpec fp1 as continuity; refuse Project / Workspace."""
    if not isinstance(kind, str) or kind.strip() == "":
        return _invalid(
            "continuity",
            "coordinated continuity is the ExperimentSpec fp1 "
            "(code_ref / resolved_config_ref / data_ref = CT-12 / environment_ref) "
            "(DEC-0284; FR-W16)",
            given=repr(kind),
        )
    token = _normalize_continuity_token(kind)
    if token in REFUSED_CONTINUITY_KINDS:
        return _policy(
            "continuity",
            "Project or Workspace is not the continuity object; coordinated "
            "continuity is the ExperimentSpec fp1 (code_ref / resolved_config_ref / "
            "data_ref = CT-12 / environment_ref) (DEC-0284; FR-W16)",
            given=kind,
            refused=sorted(REFUSED_CONTINUITY_KINDS),
        )
    if token in {
        COORDINATED_CONTINUITY_KIND,
        "experimentspec",
        "spec_fp1",
        "fp1",
    }:
        return Ok(COORDINATED_CONTINUITY_KIND)
    return _invalid(
        "continuity",
        "coordinated continuity is the ExperimentSpec fp1 "
        "(code_ref / resolved_config_ref / data_ref = CT-12 / environment_ref) "
        "(DEC-0284; FR-W16)",
        given=kind,
    )


def _copied_evidence_key(key: str) -> bool:
    token = key.strip().casefold().replace("-", "_")
    if token.endswith("_ref"):
        return False
    if token in COPIED_EXPERIMENT_EVIDENCE_KEYS:
        return True
    if "jsonl" in token:
        return True
    return token in {"ct32", "ct_32"}


def _copied_evidence_value(value: object) -> bool:
    if isinstance(value, list):
        items = cast("list[object]", value)
        return bool(items) and all(isinstance(item, Mapping) for item in items)
    if isinstance(value, str):
        return "\n{" in value or (value.lstrip().startswith("{") and "\n" in value)
    if isinstance(value, Mapping):
        nested_map = cast("Mapping[object, object]", value)
        nested = {
            str(key).strip().casefold().replace("-", "_")
            for key in nested_map
            if isinstance(key, str)
        }
        return bool(nested & COPIED_EXPERIMENT_EVIDENCE_KEYS) or "ct32" in nested
    return False


def refuse_caller_declared_lane_fields(
    extra: Mapping[str, object] | None = None,
    **fields: object,
) -> TypedRefusal | None:
    """Refuse payload / CT-32 / B-4 lane flags. The door selects the lane."""
    present: list[str] = []
    if extra is not None:
        present.extend(key for key in CALLER_DECLARED_LANE_FIELDS if key in extra)
    for key, value in fields.items():
        if key in CALLER_DECLARED_LANE_FIELDS and value is not None:
            present.append(key)
    if not present:
        return None
    return _policy(
        present[0],
        "lane is derived from which door is called, never a caller-declared "
        "flag on the payload, CT-32, or B-4; extending CT-32 or B-4 is a spine "
        "amendment, not a connect fix (FR-W03; FR-W07; DEC-0270)",
        given=present,
        spine_amendment=True,
        qmb_ledger_workbench_lane=QMB_LEDGER_WORKBENCH_LANE,
        experiment_ledger_workbench_lane=EXPERIMENT_LEDGER_WORKBENCH_LANE,
    )


def coordinated_run_labels() -> Mapping[str, object]:
    """Two honest labels on two objects for a CT-47 placement (DEC-0270)."""
    return MappingProxyType(
        {
            "door": WORKBENCH_LANE_COORDINATED,
            "experiment_ledger_workbench_lane": EXPERIMENT_LEDGER_WORKBENCH_LANE,
            "qmb_ledger_workbench_lane": QMB_LEDGER_WORKBENCH_LANE,
        }
    )


def admit_experiment_evidence_body(
    body: Mapping[str, object],
) -> Result[Mapping[str, object]]:
    """Admit Experiment Ledger evidence that stores _refs, never JSONL or CT-32 copies."""
    stamped: dict[str, object] = dict(body)
    for key in stamped:
        token = key.strip().casefold().replace("-", "_")
        if token in _COLLAPSED_LANE_KEYS:
            return _policy(
                key,
                "the two workbench_lane labels live on two objects and must not "
                "be collapsed into one field; QMB ledger is governed, Experiment "
                "Ledger is coordinated (FR-W06; DEC-0270)",
                qmb_ledger_workbench_lane=QMB_LEDGER_WORKBENCH_LANE,
                experiment_ledger_workbench_lane=EXPERIMENT_LEDGER_WORKBENCH_LANE,
            )
    lane_raw = stamped.get("workbench_lane")
    if lane_raw is None:
        stamped["workbench_lane"] = EXPERIMENT_LEDGER_WORKBENCH_LANE
    else:
        token = lane_raw.strip().casefold() if isinstance(lane_raw, str) else ""
        if token != WORKBENCH_LANE_COORDINATED:
            return _policy(
                "workbench_lane",
                "the Experiment Ledger entry carries workbench_lane=coordinated; "
                "the spawned run's QMB ledger line is workbench_lane=governed "
                "(FR-W06; DEC-0270)",
                given=repr(lane_raw),
                qmb_ledger_workbench_lane=QMB_LEDGER_WORKBENCH_LANE,
                experiment_ledger_workbench_lane=EXPERIMENT_LEDGER_WORKBENCH_LANE,
            )
        stamped["workbench_lane"] = EXPERIMENT_LEDGER_WORKBENCH_LANE
    for key, value in stamped.items():
        if key.strip() == "":
            return _invalid(
                "body",
                "Experiment Ledger evidence keys are non-empty strings",
                given=repr(key),
            )
        token = key.strip().casefold().replace("-", "_")
        if token.endswith("_ref"):
            if not isinstance(value, str) or value.strip() == "":
                return _invalid(
                    key,
                    "QMA stores _refs only; a ref value is a non-empty string (FR-W10; NFR-W04)",
                    given=repr(value),
                )
            continue
        if _copied_evidence_key(key) or _copied_evidence_value(value):
            return _policy(
                "body",
                "QMA stores _refs only — it does not copy or merge JSONL or CT-32 "
                "(FR-W10; NFR-W04; DEC-0276)",
                key=key,
            )
        if token not in EXPERIMENT_EVIDENCE_METADATA_KEYS:
            return _policy(
                "body",
                "QMA stores _refs only — Experiment Ledger evidence carries ref "
                "keys and small metadata, never copied QMB JSONL or CT-32 "
                "(FR-W10; NFR-W04; DEC-0276)",
                key=key,
            )
    return Ok(MappingProxyType(stamped))


def parse_experiment_spec(**fields: object) -> Result[ExperimentSpec]:
    """Result-returning ExperimentSpec constructor (CT-47; FR-Q54)."""
    extra_raw = fields.get("extra")
    extra: Mapping[str, object] | None
    if extra_raw is None:
        extra = None
    elif isinstance(extra_raw, Mapping):
        extra = cast("Mapping[str, object]", extra_raw)
    else:
        return _invalid("extra", "extra must be an object when present")
    return ExperimentSpec.try_create(
        data_ref=fields.get("data_ref"),
        environment_ref=fields.get("environment_ref"),
        seed=fields.get("seed"),
        model_and_harness_version=fields.get("model_and_harness_version"),
        cost_assumptions=fields.get("cost_assumptions"),
        resolved_config_ref=fields.get("resolved_config_ref"),
        code_ref=fields.get("code_ref"),
        experiment_ledger_ref=fields.get("experiment_ledger_ref"),
        mechanisms=fields.get("mechanisms"),
        extra=extra,
    )
