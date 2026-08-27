"""L3 acceptance — Story 7.1 identity (T7-A1, T7-A2, T7-A3)."""

from __future__ import annotations

import dataclasses

import _fixtures as F
from qmf.core import Fingerprint, fingerprint, is_ok
from qmf.indicators import (
    BatchKernel,
    ConfiguredIndicator,
    SupportsFp1Identity,
)


# --- T7-A1 [R1, R2] P0 ------------------------------------------------------


def test_a1_fp1_is_computed_by_the_single_qmf_core_function() -> None:
    """fp1 is exactly qmf-core's fingerprint over the declaration's identity content —
    no local hashing lives in this package. Counter-case: fp1 diverging from
    fingerprint(config) or fingerprint(config.fp1_identity())."""
    cfg = F.config()
    fp = F.unwrap(cfg.fp1())
    assert isinstance(fp, Fingerprint)
    assert fp.value.startswith("fp1:sha256:")
    assert fp == F.unwrap(fingerprint(cfg))
    assert fp == F.unwrap(fingerprint(cfg.fp1_identity()))


def test_a1_equal_declarations_reproduce_the_same_fp1() -> None:
    assert F.unwrap(F.config().fp1()).value == F.unwrap(F.config().fp1()).value


def test_a1_differing_in_exactly_one_element_yields_a_distinct_fp1() -> None:
    baseline = F.unwrap(F.config().fp1()).value
    assert F.unwrap(F.config(formula_id="ema").fp1()).value != baseline
    assert F.unwrap(F.config(warm_up=9).fp1()).value != baseline
    assert F.unwrap(F.config(parameters={"period": F.period(7)}).fp1()).value != baseline


def test_a1_fp1_is_the_only_dedup_key() -> None:
    """The configuration exposes fp1 as its identity; two byte-identical declarations
    share it and no non-identity display value forks it."""
    a, b = F.config(), F.config()
    assert F.unwrap(a.fp1()) == F.unwrap(b.fp1())
    # An ordered-element reorder is a genuine identity change (order significant):
    two = [F.series_input("close"), F.series_input("open")]
    rev = [F.series_input("open"), F.series_input("close")]
    assert F.unwrap(F.config(inputs=two).fp1()).value != F.unwrap(F.config(inputs=rev).fp1()).value


# --- T7-A2 [R3] P0 ----------------------------------------------------------


def test_a2_each_required_identity_element_is_load_bearing_in_the_fingerprint() -> None:
    """An element missing from the fingerprint is a contract defect. Dropping ANY required
    element from the hashed content changes the fingerprint — proving none is
    stored-but-unhashed. Counter-case: dropping an element leaves the fingerprint fixed."""
    content = F.config().fp1_identity()
    baseline = F.unwrap(fingerprint(content)).value
    for element in (
        "formula_id",
        "contract_format_version",
        "parameters",
        "inputs",
        "calendar_requirements",
        "alignment_policy",
        "missing_value_policy",
        "warm_up",
        "output_schema",
        "supported_modes",
        "arithmetic_reference_configuration",
    ):
        assert element in content, f"{element!r} not present in fp1 content (contract defect)"
        pruned = {k: v for k, v in content.items() if k != element}
        assert F.unwrap(fingerprint(pruned)).value != baseline, (
            f"dropping {element!r} did not change the fingerprint (silent contract defect)"
        )


def test_a2_identity_element_names_reports_the_declared_element_set() -> None:
    """identity_element_names is a conformance surface: it lists the required elements plus
    each declared optional one, so a harness can check none silently drifted out."""
    from qmf.indicators import DeclaredBudget, EmissionPolicy, EmissionTiming

    lean = F.config()
    assert set(lean.identity_element_names()) >= {
        "formula_id",
        "parameters",
        "inputs",
        "arithmetic_reference_configuration",
    }
    full = F.config(
        emission_policy=EmissionPolicy(EmissionTiming.BAR_CLOSED, "per-bar"),
        declared_budget=DeclaredBudget("live-path", True, "bounded", True),
    )
    assert "emission_policy" in full.identity_element_names()
    assert "declared_budget" in full.identity_element_names()
    assert "emission_policy" not in lean.identity_element_names()


# --- T7-A3 [R5] P1 ----------------------------------------------------------


def test_a3_public_value_types_are_frozen_dataclasses() -> None:
    """Counter-case: a public value type that is mutable (assignment succeeds)."""
    cfg = F.config()
    assert dataclasses.is_dataclass(ConfiguredIndicator)
    assert ConfiguredIndicator.__dataclass_params__.frozen  # type: ignore[attr-defined]
    try:
        cfg.formula_id = "mutated"  # type: ignore[misc]
    except dataclasses.FrozenInstanceError:
        pass
    else:  # pragma: no cover
        raise AssertionError("ConfiguredIndicator is not frozen")


def test_a3_public_seams_are_runtime_checkable_protocols() -> None:
    # The kernel and identity seams are runtime-checkable Protocols (isinstance works):
    assert getattr(BatchKernel, "_is_runtime_protocol", False), "BatchKernel is not runtime-checkable"
    assert getattr(SupportsFp1Identity, "_is_runtime_protocol", False)
    assert isinstance(F.EchoKernel(), BatchKernel)


def test_a3_pyproject_declares_every_dependency() -> None:
    """pyproject declares qmf-core and the ta-lib reference pin; the module imports only
    qmf-core statically (S1 proves the import graph)."""
    import inspect
    import os

    import qmf.indicators as pkg

    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(inspect.getfile(pkg)))))
    pyproject = os.path.join(root, "pyproject.toml")
    with open(pyproject, encoding="utf-8") as handle:
        text = handle.read()
    assert "qmf-core" in text
    assert "ta-lib==0.7.1" in text


def test_a3_versions_in_semver_lockstep() -> None:
    """The roster package version is SemVer (display-only provenance, never fp1 identity)."""
    import qmf.indicators as pkg

    parts = pkg.__version__.split(".")
    assert len(parts) == 3 and all(p.isdigit() for p in parts)
    assert "version" not in F.config().fp1_identity()  # never identity
