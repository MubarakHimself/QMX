"""Tier-2 tests for the CT-16 catalog surface, extension identity, and graduation
(COMP-QMF-INDICATORS; Story 7.5).

These tests bind the story's last two acceptance criteria:

* **AC4 (FM-8)** — an extension enters an application through the one named catalog surface
  by **explicit registration, never ambient scanning**, and its **distribution identity and
  version are mandatory fields of every artifact it produces**.
* **AC5 (L33)** — a concept the framework cannot yet articulate is authorable as plain Python
  outside governed evidence, and it enters governed evidence **only** by graduating through
  the CT-16 extension shape **with a lineage edge back to its originating research artifact**.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core import Result, is_ok, is_refusal
from qmf.indicators import (
    EXTENSION_DISTRIBUTION_FIELD,
    EXTENSION_VERSION_FIELD,
    Catalog,
    ExtensionIdentity,
    FormulaOwner,
    FormulaOwnership,
    RegisteredExtension,
    ResearchLineage,
    graduate,
    require_extension_identity,
    stamp_extension_identity,
)

T = TypeVar("T")


def _unwrap(result: Result[T]) -> T:
    assert is_ok(result), f"expected Ok, got {result}"
    return result.value


# --- fixtures ---------------------------------------------------------------


def _identity(
    distribution: str = "qmf-ind-ext-zigzag", version: str = "1.2.0"
) -> ExtensionIdentity:
    return _unwrap(ExtensionIdentity.try_create(distribution, version))


def _lineage(artifact: str = "research://experiment-42") -> ResearchLineage:
    return _unwrap(ResearchLineage.try_create(artifact))


def _package_owner(formula_id: str) -> FormulaOwner:
    return FormulaOwner(
        formula_id=formula_id, ownership=FormulaOwnership.PACKAGE, reference_function=None
    )


def _extension(
    distribution: str = "qmf-ind-ext-zigzag", formula_ids: tuple[str, ...] = ("research_zigzag",)
) -> RegisteredExtension:
    return _unwrap(
        RegisteredExtension.try_create(
            _identity(distribution=distribution),
            [_package_owner(formula_id) for formula_id in formula_ids],
            _lineage(),
        )
    )


# --- extension identity is mandatory (FM-8) ---------------------------------


def test_extension_identity_requires_distribution_and_version() -> None:
    assert is_refusal(ExtensionIdentity.try_create("", "1.0.0"))
    assert is_refusal(ExtensionIdentity.try_create("qmf-ind-ext-x", "  "))
    identity = _unwrap(ExtensionIdentity.try_create("qmf-ind-ext-x", "1.0.0"))
    assert identity.distribution == "qmf-ind-ext-x"
    assert identity.version == "1.0.0"


def test_research_lineage_is_mandatory() -> None:
    assert is_refusal(ResearchLineage.try_create(""))
    assert is_refusal(ResearchLineage.try_create(None))
    assert _unwrap(ResearchLineage.try_create("research://x")).research_artifact == "research://x"


# --- registered extension validation ----------------------------------------


def test_registered_extension_requires_a_lineage_edge() -> None:
    refusal = RegisteredExtension.try_create(
        _identity(), [_package_owner("research_zigzag")], object()
    )
    assert is_refusal(refusal) and refusal.context["field"] == "lineage"


def test_registered_extension_refuses_a_reference_owned_formula() -> None:
    reference_owned = FormulaOwner(
        formula_id="my_ema", ownership=FormulaOwnership.REFERENCE, reference_function="EMA"
    )
    refusal = RegisteredExtension.try_create(_identity(), [reference_owned], _lineage())
    assert is_refusal(refusal) and refusal.context["field"] == "formula_owners"


def test_registered_extension_refuses_a_core_owned_formula() -> None:
    # "sma" already has a canonical owner in the core registry; an extension may not re-own it.
    refusal = RegisteredExtension.try_create(_identity(), [_package_owner("sma")], _lineage())
    assert is_refusal(refusal) and refusal.context["formula_id"] == "sma"


def test_registered_extension_refuses_duplicate_and_empty_formula_sets() -> None:
    duplicate = RegisteredExtension.try_create(
        _identity(),
        [_package_owner("research_zigzag"), _package_owner("research_zigzag")],
        _lineage(),
    )
    assert is_refusal(duplicate)
    empty = RegisteredExtension.try_create(_identity(), [], _lineage())
    assert is_refusal(empty)
    assert is_refusal(RegisteredExtension.try_create(_identity(), object(), _lineage()))
    assert is_refusal(RegisteredExtension.try_create(_identity(), [object()], _lineage()))
    assert is_refusal(RegisteredExtension.try_create(object(), [_package_owner("z")], _lineage()))


def test_registered_extension_reports_its_formula_ids() -> None:
    extension = _extension(formula_ids=("research_zigzag", "research_impulse"))
    assert extension.formula_ids() == ("research_zigzag", "research_impulse")


# --- the catalog surface: explicit registration only (FM-8) -----------------


def test_catalog_registration_is_explicit_and_immutable() -> None:
    empty = Catalog.empty()
    assert empty.extensions() == ()
    filled = _unwrap(empty.register(_extension()))
    # register returns a NEW catalog; the original stays empty (immutable, functional).
    assert empty.extensions() == ()
    assert len(filled.extensions()) == 1
    resolved = _unwrap(filled.resolve_distribution("qmf-ind-ext-zigzag"))
    assert resolved.identity.version == "1.2.0"
    by_formula = _unwrap(filled.resolve_formula("research_zigzag"))
    assert by_formula.identity.distribution == "qmf-ind-ext-zigzag"
    assert filled.formula_ids() == ("research_zigzag",)


def test_catalog_has_no_ambient_discovery_entry_point() -> None:
    # Discovery is explicit registration only — the surface exposes no scan/discover/autoload.
    for forbidden in ("scan", "discover", "autoload", "load_entry_points"):
        assert not hasattr(Catalog, forbidden)


def test_catalog_refuses_a_duplicate_distribution() -> None:
    catalog = _unwrap(Catalog.empty().register(_extension()))
    duplicate = catalog.register(_extension())  # same distribution identity
    assert is_refusal(duplicate) and duplicate.context["field"] == "extension"


def test_catalog_refuses_a_formula_collision_across_extensions() -> None:
    catalog = _unwrap(Catalog.empty().register(_extension(distribution="qmf-ind-ext-a")))
    collision = catalog.register(
        _extension(distribution="qmf-ind-ext-b", formula_ids=("research_zigzag",))
    )
    assert is_refusal(collision)
    assert collision.context["formula_id"] == "research_zigzag"


def test_catalog_register_refuses_a_non_extension() -> None:
    assert is_refusal(Catalog.empty().register(object()))


def test_catalog_resolve_refuses_unknown_and_bad_arguments() -> None:
    catalog = _unwrap(Catalog.empty().register(_extension()))
    assert is_refusal(catalog.resolve_distribution("nope"))
    assert is_refusal(catalog.resolve_distribution(object()))
    assert is_refusal(catalog.resolve_formula("unknown_formula"))
    assert is_refusal(catalog.resolve_formula(object()))


# --- graduation (L33) -------------------------------------------------------


def test_graduation_requires_a_lineage_edge() -> None:
    refusal = graduate(
        distribution="qmf-ind-ext-zigzag",
        version="1.0.0",
        formula_ids=["research_zigzag"],
        research_artifact="",
    )
    assert is_refusal(refusal) and refusal.context["field"] == "research_artifact"


def test_graduation_produces_a_governed_extension_with_lineage() -> None:
    extension = _unwrap(
        graduate(
            distribution="qmf-ind-ext-zigzag",
            version="1.0.0",
            formula_ids=["research_zigzag", "research_impulse"],
            research_artifact="research://experiment-42",
        )
    )
    assert extension.lineage.research_artifact == "research://experiment-42"
    assert extension.formula_ids() == ("research_zigzag", "research_impulse")
    # Every owner is package-owned under the identical upgrade gate.
    assert all(owner.ownership is FormulaOwnership.PACKAGE for owner in extension.formula_owners)
    # The graduated extension registers into the catalog.
    catalog = _unwrap(Catalog.empty().register(extension))
    assert catalog.formula_ids() == ("research_impulse", "research_zigzag")


def test_graduation_refuses_a_core_owned_formula_and_bad_inputs() -> None:
    # A formula the core already owns cannot graduate as an extension.
    assert is_refusal(
        graduate(
            distribution="qmf-ind-ext-x",
            version="1.0.0",
            formula_ids=["sma"],
            research_artifact="research://x",
        )
    )
    assert is_refusal(
        graduate(
            distribution="", version="1.0.0", formula_ids=["z"], research_artifact="research://x"
        )
    )
    assert is_refusal(
        graduate(
            distribution="qmf-ind-ext-x",
            version="1.0.0",
            formula_ids=[],
            research_artifact="research://x",
        )
    )
    assert is_refusal(
        graduate(
            distribution="qmf-ind-ext-x",
            version="1.0.0",
            formula_ids="not-a-list",
            research_artifact="research://x",
        )
    )
    assert is_refusal(
        graduate(
            distribution="qmf-ind-ext-x",
            version="1.0.0",
            formula_ids=[""],
            research_artifact="research://x",
        )
    )


# --- FM-8: mandatory extension identity in every artifact -------------------


def test_stamp_extension_identity_adds_the_mandatory_fields() -> None:
    identity = _identity()
    stamped = _unwrap(stamp_extension_identity(identity, {"class": "some-artifact", "value": 7}))
    assert stamped[EXTENSION_DISTRIBUTION_FIELD] == "qmf-ind-ext-zigzag"
    assert stamped[EXTENSION_VERSION_FIELD] == "1.2.0"
    assert stamped["class"] == "some-artifact"
    # The stamped content passes the mandatory-identity requirement.
    assert is_ok(require_extension_identity(stamped))


def test_stamp_refuses_conflicting_identity_and_bad_arguments() -> None:
    identity = _identity()
    conflicting = {EXTENSION_DISTRIBUTION_FIELD: "someone-else"}
    assert is_refusal(stamp_extension_identity(identity, conflicting))
    assert is_refusal(stamp_extension_identity(object(), {"a": 1}))
    assert is_refusal(stamp_extension_identity(identity, object()))
    assert is_refusal(stamp_extension_identity(identity, {7: "non-string-key"}))


def test_require_extension_identity_refuses_missing_fields() -> None:
    assert is_refusal(require_extension_identity({"class": "artifact"}))
    assert is_refusal(require_extension_identity({EXTENSION_DISTRIBUTION_FIELD: "qmf-ind-ext-x"}))
    assert is_refusal(
        require_extension_identity(
            {EXTENSION_DISTRIBUTION_FIELD: "qmf-ind-ext-x", EXTENSION_VERSION_FIELD: "  "}
        )
    )
    assert is_refusal(require_extension_identity(object()))
