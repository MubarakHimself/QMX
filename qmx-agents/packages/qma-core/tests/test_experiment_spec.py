"""Story 45.7 — content-addressed ExperimentSpec identity (FR-Q54; CT-47)."""

from __future__ import annotations

from collections.abc import Mapping

from qma.core.content import content_address
from qma.core.ports.experiments import (
    CT07_V1_EDGE_TYPES,
    EXPERIMENT_CHANGE_CODE,
    EXPERIMENT_CHANGE_KINDS,
    EXPERIMENT_CHANGE_RESOLVED_CONFIG,
    EXPERIMENT_LINEAGE_EDGE_TYPE,
    GAP_0085_STRATEGY_MECHANISMS,
    GIT_COMMIT_REF_PREFIX,
    ExperimentSpec,
    is_git_branch_ref,
    is_git_commit_ref,
    parse_experiment_spec,
    parse_git_commit_ref,
)
from qmf.core import fingerprint, is_ok, is_refusal

_COMMIT = GIT_COMMIT_REF_PREFIX + ("a" * 40)


def _fp(label: str) -> str:
    addressed = content_address({"label": label})
    assert is_ok(addressed)
    return addressed.value.value


def _spec(
    *,
    data_ref: str = "data:eurusd-m1",
    environment_ref: str = "env:docker-analysis",
    seed: int = 7,
    model_and_harness_version: Mapping[str, str] | None = None,
    cost_assumptions: Mapping[str, int] | None = None,
    resolved_config_ref: str | None = None,
    code_ref: str | None = None,
) -> ExperimentSpec:
    created = ExperimentSpec.try_create(
        data_ref=data_ref,
        environment_ref=environment_ref,
        seed=seed,
        model_and_harness_version=(
            {"model": "analyst-v1", "harness": "qmb-replay-1"}
            if model_and_harness_version is None
            else model_and_harness_version
        ),
        cost_assumptions=(
            {"spread_usd_cents": 20, "commission_usd_cents": 0}
            if cost_assumptions is None
            else cost_assumptions
        ),
        resolved_config_ref=_fp("config-a") if resolved_config_ref is None else resolved_config_ref,
        code_ref=code_ref,
    )
    assert is_ok(created)
    return created.value


def test_spec_carries_required_axes_and_fp1_identity() -> None:
    spec = _spec()
    payload = spec.to_payload()
    assert payload["data_ref"] == "data:eurusd-m1"
    assert payload["environment_ref"] == "env:docker-analysis"
    assert payload["seed"] == 7
    assert payload["model_and_harness_version"] == {
        "model": "analyst-v1",
        "harness": "qmb-replay-1",
    }
    assert spec.cost_assumptions["spread_usd_cents"] == 20
    assert "code_ref" not in spec.identity_content()
    assert "experiment_ledger_ref" not in spec.identity_content()
    assert spec.experiment_ledger_ref is None
    addressed = content_address(dict(spec.identity_content()))
    via_core = fingerprint(dict(spec.identity_content()))
    assert is_ok(addressed) and is_ok(via_core)
    assert spec.spec_fp1 == addressed.value.value == via_core.value.value
    assert spec.spec_fp1.startswith("fp1:sha256:")


def test_equivalent_specs_collapse_to_one_identity() -> None:
    first = _spec(resolved_config_ref=_fp("same"))
    second = _spec(resolved_config_ref=_fp("same"))
    assert first.spec_fp1 == second.spec_fp1
    linked = first.with_ledger_ref("experiment-ledger:x")
    assert linked.spec_fp1 == first.spec_fp1
    assert linked.experiment_ledger_ref == "experiment-ledger:x"
    assert "experiment_ledger_ref" not in linked.identity_content()


def test_code_change_uses_git_commit_ref_only() -> None:
    base = _spec()
    successor = base.with_change(change=EXPERIMENT_CHANGE_CODE, code_ref=_COMMIT)
    assert is_ok(successor)
    assert successor.value.code_ref == _COMMIT
    assert successor.value.resolved_config_ref == base.resolved_config_ref
    assert successor.value.spec_fp1 != base.spec_fp1
    assert is_git_commit_ref(_COMMIT)
    branch = parse_git_commit_ref("git:branch:paramsweep")
    assert is_refusal(branch)
    assert branch.context["field"] == "code_ref"
    bare = parse_git_commit_ref("main")
    assert is_refusal(bare)
    missing = base.with_change(change=EXPERIMENT_CHANGE_CODE)
    assert is_refusal(missing)


def test_parameter_change_uses_resolved_config_not_code_ref() -> None:
    base = _spec()
    next_config = _fp("config-b")
    successor = base.with_change(
        change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
        resolved_config_ref=next_config,
    )
    assert is_ok(successor)
    assert successor.value.code_ref is None
    assert successor.value.resolved_config_ref == next_config
    assert successor.value.spec_fp1 != base.spec_fp1
    assert "code_ref" not in successor.value.identity_content()
    with_code = base.with_change(
        change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
        resolved_config_ref=next_config,
        code_ref=_COMMIT,
    )
    assert is_refusal(with_code)
    assert with_code.context["field"] == "code_ref"
    branch_config = base.with_change(
        change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
        resolved_config_ref="refs/heads/params",
    )
    assert is_refusal(branch_config)
    assert is_git_branch_ref("refs/heads/params")
    assert {
        EXPERIMENT_CHANGE_CODE,
        EXPERIMENT_CHANGE_RESOLVED_CONFIG,
    } == EXPERIMENT_CHANGE_KINDS


def test_predecessor_is_not_mutated_by_successor_construction() -> None:
    base = _spec()
    original = dict(base.to_payload())
    created = base.with_change(
        change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
        resolved_config_ref=_fp("config-c"),
    )
    assert is_ok(created)
    assert dict(base.to_payload()) == original
    assert created.value.spec_fp1 != base.spec_fp1


def test_gap_0085_strategy_mechanisms_are_excluded() -> None:
    assert "entry_mechanism" in GAP_0085_STRATEGY_MECHANISMS
    refused = parse_experiment_spec(
        data_ref="data:x",
        environment_ref="env:x",
        seed=1,
        model_and_harness_version={"model": "m", "harness": "h"},
        cost_assumptions={},
        resolved_config_ref=_fp("cfg"),
        extra={"EntryMechanism": {"kind": "breakout"}},
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "mechanisms"
    named = ExperimentSpec.try_create(
        data_ref="data:x",
        environment_ref="env:x",
        seed=1,
        model_and_harness_version={"model": "m", "harness": "h"},
        cost_assumptions={},
        resolved_config_ref=_fp("cfg"),
        mechanisms={"ExitMechanism": {}},
    )
    assert is_refusal(named)
    base = _spec()
    successor = base.with_change(
        change=EXPERIMENT_CHANGE_RESOLVED_CONFIG,
        resolved_config_ref=_fp("cfg-gap"),
        extra={"SessionRule": {"open": "london"}},
    )
    assert is_refusal(successor)


def test_lineage_edge_type_is_ct07_branches_from() -> None:
    assert EXPERIMENT_LINEAGE_EDGE_TYPE == "branches-from"
    assert EXPERIMENT_LINEAGE_EDGE_TYPE in CT07_V1_EDGE_TYPES
    assert "supersedes" in CT07_V1_EDGE_TYPES


def test_invalid_seed_and_missing_axes_are_refused() -> None:
    refused = parse_experiment_spec(
        data_ref="data:x",
        environment_ref="env:x",
        seed=1.5,
        model_and_harness_version={"model": "m", "harness": "h"},
        cost_assumptions={},
        resolved_config_ref=_fp("cfg"),
    )
    assert is_refusal(refused)
    missing = parse_experiment_spec(
        data_ref="",
        environment_ref="env:x",
        seed=1,
        model_and_harness_version={"model": "m", "harness": "h"},
        cost_assumptions={},
        resolved_config_ref=_fp("cfg"),
    )
    assert is_refusal(missing)
    no_change = _spec().with_change(change="git_branch")
    assert is_refusal(no_change)
