"""ModelDeployment port and ReviewPolicy catalog (CT-45; AD-1, AD-10, AD-15).

ReviewPolicy compares optional Deployment ``model_family`` values. The catalog
is core-defined so the completion gate is contract-testable without a
production model Deployment (FR-Q34).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from qma.core.refusals.variants import NoEligibleReviewer
from qma.core.vocabulary.enums import ModelClass
from qma.core.vocabulary.registry import VocabularyError, parse_closed
from qmf.core import Ok, Result

__all__ = [
    "DeploymentRecord",
    "ModelDeployment",
    "ReviewPolicy",
    "select_reviewer",
]


@runtime_checkable
class ModelDeployment(Protocol):
    """Definitions-only ModelDeployment seam; keyed ``<plugin_id>:<local_id>``.

    Cardinality: multi (see ``PORT_CONTRACTS``).
    """


@dataclass(frozen=True, slots=True)
class DeploymentRecord:
    """Core-defined Deployment catalog row for ReviewPolicy (CT-45; AD-15).

    ``model_family`` is optional and never defaulted or synthesized. An
    unassigned family is routable but ineligible for every ReviewPolicy
    comparison (DEC-0314, DEC-0309).
    """

    deployment_id: str
    model_class: ModelClass
    model_family: str | None = None

    def __post_init__(self) -> None:
        if self.deployment_id.strip() == "":
            msg = "deployment_id must be a non-empty string (CT-45)"
            raise VocabularyError(msg)
        if self.model_family is not None and self.model_family.strip() == "":
            msg = (
                "model_family must be a non-empty string when assigned; "
                "omit the field for an unassigned family (CT-45; AD-15)"
            )
            raise VocabularyError(msg)


@dataclass(frozen=True, slots=True)
class ReviewPolicy:
    """AD-10 ReviewPolicy: ``author_family != reviewer_family`` (FR-Q34; CT-45).

    Empty catalog or no qualifying reviewer returns ``NoEligibleReviewer``.
    """

    model_class: ModelClass | str = ModelClass.WORKHORSE_GENERAL

    def select_reviewer(
        self,
        author_family: str | None,
        catalog: Sequence[DeploymentRecord],
    ) -> Result[DeploymentRecord]:
        """Pick the first eligible reviewer under family inequality."""
        return select_reviewer(
            author_family,
            catalog,
            model_class=self.model_class,
        )


def select_reviewer(
    author_family: str | None,
    catalog: Sequence[DeploymentRecord],
    *,
    model_class: ModelClass | str = ModelClass.WORKHORSE_GENERAL,
) -> Result[DeploymentRecord]:
    """Enforce ``author_family != reviewer_family`` over a core-defined catalog.

    Unassigned ``model_family`` (``None``) is ineligible as a reviewer. Empty
    catalog and no qualifying row both return ``NoEligibleReviewer``.
    """
    resolved_class = (
        model_class
        if isinstance(model_class, ModelClass)
        else parse_closed(ModelClass, model_class)
    )
    if author_family is not None and author_family.strip() == "":
        return NoEligibleReviewer.of(model_class=resolved_class.value)
    if not catalog:
        return NoEligibleReviewer.of(model_class=resolved_class.value)
    for entry in catalog:
        family = entry.model_family
        if family is None:
            continue
        if family == author_family:
            continue
        return Ok(entry)
    return NoEligibleReviewer.of(model_class=resolved_class.value)
