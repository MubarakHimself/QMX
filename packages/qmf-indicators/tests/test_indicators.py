"""Tier-1 tests for the `qmf.indicators` scaffold: the package version and public surface."""

from __future__ import annotations

import qmf.indicators


def test_version_is_semver_0x() -> None:
    assert qmf.indicators.__version__ == "0.1.0"


def test_story_7_5_public_surface_is_exported() -> None:
    # The Story 7.5 surface — the conformance register, the benchmark budgets, and the
    # catalog surface — is re-exported from the package root alongside the earlier stories.
    for name in (
        "CONCEPT_WALK_REGISTER",
        "run_conformance",
        "regression_gate",
        "evaluate_light_claim",
        "guard_synchronous_entry",
        "Catalog",
        "graduate",
        "require_extension_identity",
    ):
        assert name in qmf.indicators.__all__
        assert hasattr(qmf.indicators, name)
