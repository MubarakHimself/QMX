"""Story 25.14 / E7-R28 — enforce light/heavy claims at the composition root."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar, cast

from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qmn.host import (
    CHILD_MODULES_MAY_SELF_APPROVE,
    LIGHT_HEAVY_SURFACE,
    WORKLOAD_KINDS,
    CompositionClass,
    CompositionFingerprintInputs,
    FourBoundDeclaration,
    InMemoryBootAttemptSink,
    PreflightFacts,
    WorkloadClaim,
    WorkloadKind,
    compute_composition_fp,
    evaluate_workload_claim,
    guard_synchronous_placement,
    resolve_composition_classes,
    run_boot_ceremony,
    workload_claim_identity_content,
)

T = TypeVar("T")

_QMN_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn"
_HOST_LIGHT_HEAVY = _QMN_SRC / "host" / "light_heavy.py"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "cite", "label": label}))


def _bounds(
    *,
    bounded_state: bool = True,
    synchronous_availability: bool = True,
    rung: str = "live-path",
    rule: str = "bounded-window",
) -> FourBoundDeclaration:
    return _ok(
        FourBoundDeclaration.try_create(
            per_update_cost_rung=rung,
            bounded_state=bounded_state,
            window_or_anchor_rule=rule,
            synchronous_availability=synchronous_availability,
        )
    )


def _claim(
    *,
    kind: WorkloadKind = WorkloadKind.INDICATOR,
    label: str = "ind-a",
    bounds: FourBoundDeclaration | None = None,
    baseline: bool = False,
    proven: bool = False,
    deps: tuple[Fingerprint, ...] = (),
    self_approved: CompositionClass | None = None,
) -> WorkloadClaim:
    return _ok(
        WorkloadClaim.try_create(
            kind=kind,
            definition_fp=_fp(label),
            declared_bounds=bounds,
            live_path_baseline_present=baseline,
            benchmark_proven=proven,
            dependency_fps=deps,
            self_approved_class=self_approved,
        )
    )


def _inputs(label: str = "boot-a") -> CompositionFingerprintInputs:
    return CompositionFingerprintInputs(
        config_fp=_fp(f"config-{label}"),
        distribution_identities={
            "qmf": "lockstep",
            "qmb": "0.1.0",
            "qml": "0.1.0",
            "qmn": "0.1.0",
        },
        extension_identities={"qmf-calendar-forex": "1.0.0"},
        proto_release_tag="proto-1",
        tzdata_version="2026a",
        adapter_capability_fps=(_fp("cap-ctrader"),),
        registry_as_of_fp=_fp("as-of-1"),
        calendar_code_identities={
            "market_hours_calendar": "mh-code-1",
            "day_boundary_calendar": "db-code-1",
            "news_calendar": "news-code-1",
        },
        os_cpu_class="linux-x86_64",
    )


def _streams() -> tuple[tuple[str, str], ...]:
    return (
        ("command", "venue-a:acct-1"),
        ("adapter", "venue-a:acct-1:feed"),
        ("risk", "binding-1"),
    )


# --- Surface / ownership ----------------------------------------------------


def test_surface_markers_and_closed_kinds() -> None:
    assert LIGHT_HEAVY_SURFACE == "qmn.host.light_heavy"
    assert CHILD_MODULES_MAY_SELF_APPROVE is False
    assert WORKLOAD_KINDS == (
        "indicator",
        "structure",
        "labeler",
        "seat",
        "producer-definition",
    )


def test_only_host_light_heavy_assigns_effective_class() -> None:
    """Child modules never stamp CompositionClass / effective_class (E7-R28)."""
    violations: list[str] = []
    for path in sorted(_QMN_SRC.rglob("*.py")):
        if path.resolve() == _HOST_LIGHT_HEAVY.resolve():
            continue
        if path.name == "__init__.py" and path.parent.name == "host":
            # Re-exports only — still must not assign.
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "effective_class":
                            violations.append(f"{path}: assigns effective_class")
            continue
        rel = path.relative_to(_QMN_SRC)
        if rel.parts[0] == "host":
            continue
        text = path.read_text(encoding="utf-8")
        if "CompositionClass" in text or "effective_class" in text:
            violations.append(str(rel))
    assert violations == [], f"child modules must not self-approve class: {violations}"


# --- AC1: evaluate four-bound declaration; refuse contradiction before Seal -


def test_no_declared_budget_is_heavy_by_default() -> None:
    assignment = _ok(evaluate_workload_claim(_claim()))
    assert assignment.effective_class is CompositionClass.HEAVY
    assert "heavy by default" in assignment.reasons[0]


def test_light_claim_without_baseline_is_refused() -> None:
    refused = evaluate_workload_claim(_claim(bounds=_bounds(), baseline=False))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["failure_id"] == "compose.light_heavy.no_baseline"


def test_light_claim_without_benchmark_proof_is_refused() -> None:
    refused = evaluate_workload_claim(
        _claim(bounds=_bounds(), baseline=True, proven=False)
    )
    assert is_refusal(refused)
    assert "unmet" in refused.context
    unmet_raw = refused.context["unmet"]
    assert isinstance(unmet_raw, tuple)
    unmet_items = cast("tuple[object, ...]", unmet_raw)
    assert any("benchmark-proven" in str(item) for item in unmet_items)


def test_proven_light_claim_is_admitted() -> None:
    assignment = _ok(
        evaluate_workload_claim(_claim(bounds=_bounds(), baseline=True, proven=True))
    )
    assert assignment.effective_class is CompositionClass.LIGHT


def test_self_approved_class_is_refused() -> None:
    refused = evaluate_workload_claim(
        _claim(self_approved=CompositionClass.LIGHT)
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "self_approved_class"


def test_light_depending_on_heavy_is_refused_before_seal() -> None:
    heavy = _claim(kind=WorkloadKind.STRUCTURE, label="struct-heavy")
    light = _claim(
        kind=WorkloadKind.SEAT,
        label="seat-light",
        bounds=_bounds(),
        baseline=True,
        proven=True,
        deps=(heavy.definition_fp,),
    )
    refused = resolve_composition_classes((heavy, light))
    assert is_refusal(refused)
    assert refused.context["failure_id"] == "compose.light_heavy.heavy_dependency"


def test_compose_refuses_light_without_baseline_before_seal() -> None:
    sink = InMemoryBootAttemptSink()
    claim = _claim(
        kind=WorkloadKind.LABELER,
        label="labeler-light",
        bounds=_bounds(),
        baseline=False,
    )
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-1",
            machine="vps-a",
            composition_inputs=_inputs(),
            writer_streams=_streams(),
            workload_claims=(claim,),
            boot_attempt_sink=sink,
            preflight=PreflightFacts(
                required_credential_refs=("venue-token",),
                credential_is_set={"venue-token": True},
            ),
        )
    )
    assert outcome.stand_down_alive is True
    assert outcome.sealed is False
    assert outcome.ready is False
    assert outcome.failure_id == "compose.light_heavy.no_baseline"
    assert sink.records[0].stage == "compose"
    assert sink.records[0].failure_id == "compose.light_heavy.no_baseline"


def test_compose_admits_heavy_and_proven_light_graph() -> None:
    sink = InMemoryBootAttemptSink()
    indicator = _claim(
        kind=WorkloadKind.INDICATOR,
        label="ind-proven",
        bounds=_bounds(),
        baseline=True,
        proven=True,
    )
    labeler = _claim(
        kind=WorkloadKind.LABELER,
        label="lab-proven",
        bounds=_bounds(),
        baseline=True,
        proven=True,
        deps=(indicator.definition_fp,),
    )
    seat = _claim(kind=WorkloadKind.SEAT, label="seat-heavy")
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-1",
            machine="vps-a",
            composition_inputs=_inputs(),
            writer_streams=_streams(),
            workload_claims=(indicator, labeler, seat),
            boot_attempt_sink=sink,
            preflight=PreflightFacts(
                required_credential_refs=("venue-token",),
                credential_is_set={"venue-token": True},
            ),
        )
    )
    assert outcome.sealed is True
    assert outcome.composition_classes is not None
    classes = outcome.composition_classes.by_definition()
    assert classes[indicator.definition_fp.value] == "light"
    assert classes[labeler.definition_fp.value] == "light"
    assert classes[seat.definition_fp.value] == "heavy"


def test_heavy_synchronous_placement_is_unsupported() -> None:
    heavy = _ok(evaluate_workload_claim(_claim()))
    refused = guard_synchronous_placement(heavy)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    light = _ok(
        evaluate_workload_claim(_claim(bounds=_bounds(), baseline=True, proven=True))
    )
    assert is_ok(guard_synchronous_placement(light))


# --- AC2: class-affecting change updates identity; prior composition readable -


def test_class_affecting_declaration_changes_composition_identity() -> None:
    claim_a = _claim(
        kind=WorkloadKind.PRODUCER,
        label="prod-a",
        bounds=_bounds(rule="bounded-window"),
        baseline=True,
        proven=True,
    )
    claim_b = _claim(
        kind=WorkloadKind.PRODUCER,
        label="prod-a",
        bounds=_bounds(rule="anchor-reset"),
        baseline=True,
        proven=True,
    )
    base = _inputs("id-change")
    inputs_a = CompositionFingerprintInputs(
        config_fp=base.config_fp,
        distribution_identities=dict(base.distribution_identities),
        extension_identities=dict(base.extension_identities),
        proto_release_tag=base.proto_release_tag,
        tzdata_version=base.tzdata_version,
        adapter_capability_fps=base.adapter_capability_fps,
        registry_as_of_fp=base.registry_as_of_fp,
        calendar_code_identities=dict(base.calendar_code_identities),
        os_cpu_class=base.os_cpu_class,
        workload_claim_identities=workload_claim_identity_content((claim_a,)),
    )
    inputs_b = CompositionFingerprintInputs(
        config_fp=base.config_fp,
        distribution_identities=dict(base.distribution_identities),
        extension_identities=dict(base.extension_identities),
        proto_release_tag=base.proto_release_tag,
        tzdata_version=base.tzdata_version,
        adapter_capability_fps=base.adapter_capability_fps,
        registry_as_of_fp=base.registry_as_of_fp,
        calendar_code_identities=dict(base.calendar_code_identities),
        os_cpu_class=base.os_cpu_class,
        workload_claim_identities=workload_claim_identity_content((claim_b,)),
    )
    fp_a, _ = _ok(compute_composition_fp(inputs_a))
    fp_b, _ = _ok(compute_composition_fp(inputs_b))
    assert fp_a != fp_b


def test_prior_composition_remains_readable_after_claim_change() -> None:
    sink = InMemoryBootAttemptSink()
    heavy = _claim(kind=WorkloadKind.INDICATOR, label="ind-v1")
    first = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-1",
            machine="vps-a",
            composition_inputs=_inputs("v1"),
            writer_streams=_streams(),
            workload_claims=(heavy,),
            boot_attempt_sink=sink,
            preflight=PreflightFacts(
                required_credential_refs=("venue-token",),
                credential_is_set={"venue-token": True},
            ),
        )
    )
    prior_fp = first.composition_fp
    assert prior_fp is not None

    sink2 = InMemoryBootAttemptSink()
    light = _claim(
        kind=WorkloadKind.INDICATOR,
        label="ind-v1",
        bounds=_bounds(),
        baseline=True,
        proven=True,
    )
    second = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-2",
            machine="vps-a",
            composition_inputs=_inputs("v1"),
            writer_streams=_streams(),
            workload_claims=(light,),
            boot_attempt_sink=sink2,
            preflight=PreflightFacts(
                required_credential_refs=("venue-token",),
                credential_is_set={"venue-token": True},
            ),
        )
    )
    assert second.composition_fp is not None
    assert second.composition_fp != prior_fp
    # Prior sealed outcome remains intact (readable) — not mutated by the next compose.
    assert first.sealed is True
    assert first.composition_fp == prior_fp
    assert first.composition_classes is not None
    assert first.composition_classes.by_definition()[heavy.definition_fp.value] == "heavy"


def test_verdict_never_enters_declaration_identity() -> None:
    claim = _claim(bounds=_bounds(), baseline=True, proven=True)
    body = claim.declaration_identity()
    assert "effective_class" not in body
    assert "verdict" not in body
    assert body["declared_bounds"] is not None
    heavy = _claim(label="heavy-omit")
    heavy_body = heavy.declaration_identity()
    assert "declared_bounds" not in heavy_body  # omit, never null
    identity = workload_claim_identity_content((claim,))
    assert identity["class"] == "workload_claim_declarations"
    assert "effective_class" not in identity
    assert "verdict" not in identity
    claims_body = identity["claims"]
    assert isinstance(claims_body, list)
    for raw_entry in cast("list[object]", claims_body):
        assert isinstance(raw_entry, dict)
        entry = cast("dict[str, object]", raw_entry)
        assert "effective_class" not in entry
        assert "verdict" not in entry
        assert None not in entry.values()
