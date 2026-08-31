"""Structural-seed smoke for qma-core (Story 40.1 / 40.2)."""

from __future__ import annotations

import qma.core
import qma.core.ontology
import qma.core.plugins
import qma.core.ports
import qma.core.refusals
import qma.core.vocabulary


def test_version_display_only() -> None:
    assert qma.core.__version__ == "0.1.0"


def test_subpackages_importable() -> None:
    assert qma.core.ontology.__doc__
    assert qma.core.ports.__doc__
    assert qma.core.plugins.__doc__
    assert qma.core.refusals.__doc__
    assert qma.core.vocabulary.__doc__
