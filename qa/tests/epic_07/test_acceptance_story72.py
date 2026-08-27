"""L3 acceptance — Story 7.2 canonical arithmetic (T7-A4..A7). Gate 1: canonical
arithmetic is *provably* the arithmetic used."""

from __future__ import annotations

import os
import re
from types import MappingProxyType

import _fixtures as F
from qmf.core import World, is_ok, is_refusal
from qmf.indicators import (
    ArithmeticReference,
    FormulaOwner,
    FormulaOwnership,
    ReferenceKernel,
    compute_batch,
    ownership_conformance_defects,
    reference_grounded_defects,
    reference_status,
    resolve_canonical_arithmetic,
)
from qmf.indicators import _reference


# --- T7-A4 [R6] P0 — the pin resolves to lockfile-hashed 0.7.1 + 0.7.1 ------


def _worktree_root() -> str:
    """Walk up from the package source until the worktree's uv.lock is found."""
    import inspect

    import qmf.indicators as pkg

    here = os.path.dirname(inspect.getfile(pkg))
    for _ in range(10):
        if os.path.isfile(os.path.join(here, "uv.lock")):
            return here
        parent = os.path.dirname(here)
        if parent == here:
            break
        here = parent
    raise AssertionError("uv.lock not found walking up from the package source")


def test_a4_reference_resolves_to_talib_0_7_1_with_lockfile_hashes() -> None:
    """registry:canonical_indicator_reference resolves to TA-Lib C 0.7.1 + wrapper 0.7.1,
    pinned as lockfile-resolved artifact hashes. The concrete hash is READ from uv.lock,
    never fabricated. Counter-case: the installed reference differing from the lockfile pin."""
    status = reference_status()
    assert is_ok(status), f"the reference is not verified: {status}"
    ref = status.value
    assert "0.7.1" in ref.c_library
    assert "0.7.1" in ref.python_wrapper

    lock = os.path.join(_worktree_root(), "uv.lock")
    with open(lock, encoding="utf-8") as handle:
        text = handle.read()
    block = re.search(r'\[\[package\]\]\nname = "ta-lib"\nversion = "([^"]+)"(.*?)(?=\n\[\[package\]\])',
                      text, re.DOTALL)
    assert block is not None, "ta-lib package block not found in uv.lock"
    assert block.group(1) == "0.7.1", f"lockfile pins ta-lib {block.group(1)!r}, not 0.7.1"
    # Lockfile-resolved artifact hashes (distribution filename + sha256) are present:
    assert "hash = \"sha256:" in block.group(2), "no lockfile-resolved artifact hash for ta-lib"
    assert ".whl" in block.group(2), "no distribution filename recorded for ta-lib"


# --- T7-A5 [R7, R8] P0 — gate-1 anchor: import refuses on drift, never mutates


def test_a5_pin_drift_returns_unavailable_dependency() -> None:
    """A resolved artifact differing from the lockfile pin returns `unavailable dependency`
    at the assertion seam. Counter-case: a mismatched version silently accepted."""
    drifted = _reference.ResolvedReference(
        c_library_version="9.9.9",
        wrapper_version="0.7.1",
        observed_configuration=MappingProxyType(_reference.REFERENCE_CONFIGURATION),
    )
    refusal = _reference.assert_reference(drifted)
    assert is_refusal(refusal)
    assert refusal.category.value == "unavailable dependency"
    assert refusal.context["field"] == "c_library_version"


def test_a5_process_global_config_drift_returns_unavailable_dependency() -> None:
    """A process-global reference configuration differing from the record refuses at import."""
    drifted = _reference.ResolvedReference(
        c_library_version="0.7.1",
        wrapper_version="0.7.1",
        observed_configuration=MappingProxyType(
            {"compatibility_mode": "metastock", "candle_settings": "reference-default"}
        ),
    )
    refusal = _reference.assert_reference(drifted)
    assert is_refusal(refusal)
    assert refusal.category.value == "unavailable dependency"


def test_a5_matching_reference_is_accepted() -> None:
    """The accept arm: a resolved reference matching the pin AND the record verifies to a
    package-neutral ArithmeticReference (proves the refusal arms above are not vacuous)."""
    matching = _reference.ResolvedReference(
        c_library_version="0.7.1",
        wrapper_version="0.7.1",
        observed_configuration=MappingProxyType(_reference.REFERENCE_CONFIGURATION),
    )
    verified = _reference.assert_reference(matching)
    assert is_ok(verified)
    assert isinstance(verified.value, ArithmeticReference)


def test_a5_package_never_mutates_the_reference_process_global_configuration() -> None:
    """R8 non-mutation, observed through the reference's own global state as a sink: after
    the package resolves the reference, the process-global compatibility it merely READ is
    unchanged. Counter-case: the package resetting compatibility to its default."""
    import talib

    original = talib.get_compatibility()
    other = 1 if original == 0 else 0
    try:
        talib.set_compatibility(other)
        # The package reads the reference (resolve_reference calls get_compatibility) but
        # must never write it back:
        _reference.resolve_reference()
        assert talib.get_compatibility() == other, "the package mutated the reference config"
    finally:
        talib.set_compatibility(original)


# --- T7-A6 [R9, R10] P0 — wrap-not-reimplement ------------------------------


def test_a6_ownership_registry_is_conformant() -> None:
    """Every reference-owned formula names a real reference function to wrap; no
    package-owned formula names one. Counter-case: a re-implementation slipping in."""
    assert ownership_conformance_defects() == ()
    grounded = reference_grounded_defects()  # against the live reference
    assert is_ok(grounded), f"grounded conformance did not run: {grounded}"
    assert grounded.value == (), f"grounded conformance defects: {grounded.value}"


def test_a6_a_reimplementation_is_caught_as_a_contract_defect() -> None:
    """A wrapper re-implementing a reference-owned formula fails conformance. Injected into
    the checker (not source): a package-owned owner naming a reference function is a defect."""
    bad = MappingProxyType(
        {"vwap": FormulaOwner("vwap", FormulaOwnership.PACKAGE, reference_function="SMA")}
    )
    defects = ownership_conformance_defects(bad)
    assert defects != (), "a package-owned formula naming a reference function was not caught"
    assert any("FM-5" in d or "re-implement" in d.lower() for d in defects)


def test_a6_a_package_owned_formula_colliding_with_the_reference_is_caught() -> None:
    """R10 boundary: a package-owned formula the reference actually implements is a defect
    (it must be wrapped, not re-owned) — caught by the reference-grounded check."""
    bad = MappingProxyType({"sma": FormulaOwner("sma", FormulaOwnership.PACKAGE)})
    grounded = reference_grounded_defects(bad)
    assert is_ok(grounded)
    assert grounded.value != (), "a package-owned formula colliding with the reference was not caught"


def test_a6_reference_owned_formula_requires_the_verified_reference() -> None:
    """Mandatory wrapping: resolving a reference-owned formula requires the verified
    reference; a package-owned one does not. Counter-case: a reference-owned formula
    resolving while the reference is refused."""
    # With the live (verified) reference, resolution succeeds:
    assert is_ok(resolve_canonical_arithmetic("sma"))
    # Injecting a refused reference status, the reference-owned formula is refused:
    refused_status = _reference.assert_reference(
        _reference.ResolvedReference("9.9.9", "0.7.1", MappingProxyType(_reference.REFERENCE_CONFIGURATION))
    )
    assert is_refusal(resolve_canonical_arithmetic("sma", reference=refused_status))
    # A package-owned formula needs no reference:
    assert is_ok(resolve_canonical_arithmetic("vwap", reference=refused_status))


# --- T7-A7 [R11] P0 — no vendor object crosses any CT-16 boundary -----------


def _module_root(obj: object) -> str:
    return type(obj).__module__.split(".")[0]


def test_a7_no_vendor_object_crosses_on_the_success_path() -> None:
    """Over a computed result, every returned object's type is a qmf value, never a talib
    object. Counter-case: an output series or reference object whose type is `talib`."""
    cfg = F.config()
    series = F.input_series([100, 102, 101, 103, 105, 104, 106])
    result = compute_batch_ok(cfg, series)
    assert _module_root(result) == "qmf"
    for out in result.outputs.values():
        assert _module_root(out) == "qmf", f"output type leaked vendor module: {type(out)}"
    assert _module_root(reference_status().value) == "qmf"


def test_a7_no_vendor_object_crosses_on_the_refusal_path() -> None:
    """Over a refusal path, the public surface returns a CT-04 TypedRefusal (a qmf value),
    never a vendor exception or object."""
    from qmf.core import TypedRefusal

    refusal = compute_batch(
        F.config(formula_id="nonexistent-formula", supported_modes=["batch"]),
        {"close": F.input_series([1, 2, 3])},
        kernel=ReferenceKernel(),
        world=World.REPLAY,
    )
    assert isinstance(refusal, TypedRefusal)
    assert _module_root(refusal) == "qmf"


def compute_batch_ok(cfg, series):
    result = compute_batch(cfg, {"close": series}, kernel=ReferenceKernel(), world=World.REPLAY)
    return F.unwrap(result)
