"""Tier-1 tests for Story 7.2 — the canonical arithmetic reference asserted at import
(COMP-QMF-INDICATORS; CT-16 FM-2; DEC-0127).

These tests bind the story's acceptance criteria for the import-time assertion:

* the package resolves ``registry:canonical_indicator_reference`` to TA-Lib
  (C 0.7.1 + Python wrapper 0.7.1), pinned as lockfile-resolved artifacts with an
  identity-bearing reference-configuration record;
* importing the package asserts the record — a resolved artifact differing from the
  pin, or a process-global configuration differing from the record, is an
  ``unavailable dependency`` refusal (never a raised import error) so a fingerprint
  never attests arithmetic that was not used;
* the package never mutates the reference's process-global configuration; and
* no TA-Lib object crosses a public boundary.

The pinned reference installs on this machine (a wheel-bundled C library), so the
happy path is exercised against the real reference; the refusal paths are exercised
through the pure verification seams and synthetic resolved-identity inputs, never by
faking an installed reference.
"""

from __future__ import annotations

import importlib
from types import MappingProxyType
from typing import TypeVar

import pytest
import qmf.indicators
from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_ok, is_refusal
from qmf.indicators import _reference
from qmf.indicators._reference import (
    PINNED_C_LIBRARY_VERSION,
    PINNED_WRAPPER_DISTRIBUTION,
    PINNED_WRAPPER_VERSION,
    REFERENCE_CONFIGURATION,
    ResolvedReference,
    assert_reference,
    resolve_reference,
    verify_artifact_pin,
    verify_import_reference,
    verify_reference_configuration,
)

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


def _resolved(
    *,
    c_version: str = PINNED_C_LIBRARY_VERSION,
    wrapper_version: str = PINNED_WRAPPER_VERSION,
    config: dict[str, str] | None = None,
) -> ResolvedReference:
    """A resolved-identity value for exercising the pure assertion, not a live import."""
    return ResolvedReference(
        c_library_version=c_version,
        wrapper_version=wrapper_version,
        observed_configuration=MappingProxyType(
            config if config is not None else dict(REFERENCE_CONFIGURATION)
        ),
    )


# --- AC1: the reference resolves to the pin ---------------------------------


def test_pins_are_the_registry_canonical_reference() -> None:
    # registry:canonical_indicator_reference — TA-Lib C 0.7.1 + Python wrapper 0.7.1.
    assert PINNED_WRAPPER_DISTRIBUTION == "ta-lib"
    assert PINNED_C_LIBRARY_VERSION == "0.7.1"
    assert PINNED_WRAPPER_VERSION == "0.7.1"


def test_reference_configuration_record_is_identity_bearing() -> None:
    # The identity-bearing reference-configuration record: compatibility mode + candle
    # settings, an immutable mapping.
    assert dict(REFERENCE_CONFIGURATION) == {
        "compatibility_mode": "default",
        "candle_settings": "reference-default",
    }
    assert isinstance(REFERENCE_CONFIGURATION, MappingProxyType)


def test_resolve_reads_the_installed_reference_identity() -> None:
    resolved = resolve_reference()
    assert isinstance(resolved, ResolvedReference), f"reference should install here: {resolved}"
    assert resolved.c_library_version == PINNED_C_LIBRARY_VERSION
    assert resolved.wrapper_version == PINNED_WRAPPER_VERSION
    assert resolved.observed_configuration["compatibility_mode"] == "default"


# --- AC2: the record is asserted at import ----------------------------------


def test_import_assertion_verifies_the_reference_on_this_machine() -> None:
    status = qmf.indicators.reference_status()
    assert is_ok(status), f"the pinned reference installs here, so the assertion is Ok: {status}"
    reference = status.value
    # Artifact identity, never a bare version string; the record travels with it.
    assert reference.c_library == "ta-lib-c==0.7.1"
    assert reference.python_wrapper == "ta-lib==0.7.1"
    assert dict(reference.reference_configuration) == dict(REFERENCE_CONFIGURATION)


def test_verify_import_reference_matches_reference_status() -> None:
    assert verify_import_reference() == qmf.indicators.reference_status()


def test_artifact_pin_mismatch_is_unavailable_dependency() -> None:
    # A resolved C-library version differing from the pin refuses.
    c_mismatch = verify_artifact_pin("0.7.1", "0.6.4", "0.7.1", "0.7.1")
    assert is_refusal(c_mismatch)
    assert c_mismatch.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert c_mismatch.retryability is Retryability.NO
    assert c_mismatch.context["field"] == "c_library_version"
    # A resolved wrapper version differing from the pin refuses.
    wrapper_mismatch = verify_artifact_pin("0.7.1", "0.7.1", "0.7.1", "0.7.0")
    assert is_refusal(wrapper_mismatch)
    assert wrapper_mismatch.context["field"] == "wrapper_version"
    # Matching artifacts pass.
    assert is_ok(verify_artifact_pin("0.7.1", "0.7.1", "0.7.1", "0.7.1"))


def test_reference_configuration_mismatch_is_unavailable_dependency() -> None:
    declared = REFERENCE_CONFIGURATION
    # A differing field refuses.
    differing = verify_reference_configuration(
        declared,
        MappingProxyType(
            {"compatibility_mode": "metastock", "candle_settings": "reference-default"}
        ),
    )
    assert is_refusal(differing)
    assert differing.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert differing.context["config_field"] == "compatibility_mode"
    # A missing field refuses.
    missing = verify_reference_configuration(
        declared, MappingProxyType({"compatibility_mode": "default"})
    )
    assert is_refusal(missing)
    assert missing.context["missing_field"] == "candle_settings"
    # The matching observed configuration passes.
    assert is_ok(verify_reference_configuration(declared, declared))


def test_assert_reference_refuses_artifact_drift() -> None:
    # A resolved reference whose C library drifted from the pin never becomes usable.
    drifted = assert_reference(_resolved(c_version="0.6.4"))
    assert is_refusal(drifted)
    assert drifted.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert drifted.context["field"] == "c_library_version"


def test_assert_reference_refuses_wrapper_drift() -> None:
    drifted = assert_reference(_resolved(wrapper_version="0.7.0"))
    assert is_refusal(drifted)
    assert drifted.context["field"] == "wrapper_version"


def test_assert_reference_refuses_configuration_drift() -> None:
    drifted = assert_reference(
        _resolved(
            config={"compatibility_mode": "metastock", "candle_settings": "reference-default"}
        )
    )
    assert is_refusal(drifted)
    assert drifted.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert drifted.context["config_field"] == "compatibility_mode"


def test_assert_reference_passes_through_a_resolve_refusal() -> None:
    # A resolve-time unavailable-dependency refusal flows straight through unchanged.
    refusal = TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context={"field": "reference", "reason": "not importable"},
    )
    assert assert_reference(refusal) is refusal


def test_assert_reference_projects_verified_identity() -> None:
    reference = _unwrap(assert_reference(_resolved()))
    assert reference.c_library == "ta-lib-c==0.7.1"
    assert reference.python_wrapper == "ta-lib==0.7.1"
    assert dict(reference.reference_configuration) == dict(REFERENCE_CONFIGURATION)


# --- AC2: never mutate the reference's process-global configuration ----------


def test_package_never_mutates_reference_process_global_configuration() -> None:
    module = _reference.reference_module()
    assert module is not None, "the reference installs on this machine"
    before = module.get_compatibility()
    # A fresh resolve and assertion read the configuration; they must not change it.
    resolve_reference()
    verify_import_reference()
    _reference.reference_function("SMA")
    after = module.get_compatibility()
    assert before == after == 0  # TA_COMPATIBILITY_DEFAULT, unmutated


# --- AC5: no TA-Lib object crosses a public boundary ------------------------


def test_public_surface_exposes_no_vendor_object() -> None:
    # The package namespace never re-exports the vendor module or its objects.
    assert not hasattr(qmf.indicators, "talib")
    assert not hasattr(qmf.indicators, "numpy")
    reference = _unwrap(qmf.indicators.reference_status())
    # The neutral identity carries only strings and a plain mapping.
    assert isinstance(reference.c_library, str)
    assert isinstance(reference.python_wrapper, str)
    for key, value in reference.reference_configuration.items():
        assert isinstance(key, str)
        assert isinstance(value, str)


# --- delegation: wrapping is the arithmetic used (AC3) ----------------------


def test_reference_function_delegates_to_the_real_reference() -> None:
    import numpy as np

    sma = _reference.reference_function("SMA")
    assert sma is not None  # the reference installs here; None only when unavailable
    close = np.arange(1.0, 11.0, dtype=float)
    result = sma(close, timeperiod=3)
    assert float(result[-1]) == 9.0  # the reference's own arithmetic


def test_reference_function_none_for_unknown_or_nonstring_name() -> None:
    assert _reference.reference_function("NOT_A_REAL_FUNCTION") is None
    assert _reference.reference_function(123) is None


# --- the C-library version parser -------------------------------------------


def test_parse_c_library_version_handles_bytes_str_and_junk() -> None:
    assert _reference.parse_c_library_version(b"0.7.1 (Jul 16 2026 18:35:59)") == "0.7.1"
    assert _reference.parse_c_library_version("0.7.1") == "0.7.1"
    assert _reference.parse_c_library_version(123) is None
    assert _reference.parse_c_library_version("   ") is None


def test_resolve_refuses_when_reference_is_not_importable(monkeypatch: pytest.MonkeyPatch) -> None:
    # The story's without-the-artifact path: when the pinned reference cannot be
    # imported, the resolve returns an unavailable-dependency refusal — never a raised
    # import error — so importing the package stays safe on a machine without it (FM-2).
    def _raise(name: str) -> object:
        raise ImportError(f"simulated absence of {name}")

    monkeypatch.setattr(importlib, "import_module", _raise)
    refusal = resolve_reference()
    assert isinstance(refusal, TypedRefusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["field"] == "reference"
    # The whole import-time assertion then refuses too, without raising.
    assert is_refusal(verify_import_reference())


def test_reference_ready_flag_tracks_the_assertion() -> None:
    assert _reference.reference_ready is isinstance(_reference.reference_verification, Ok)
    assert _reference.reference_ready is True  # the reference installs on this machine
