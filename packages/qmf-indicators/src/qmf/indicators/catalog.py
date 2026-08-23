"""CT-16 — the one named catalog surface, extension identity, and graduation
(COMP-QMF-INDICATORS; Story 7.5).

An indicator extension enters an application through **one named catalog surface** by
**explicit registration at the composition root — never ambient scanning** (CT-16 FM-8;
DEC-0133, DEC-0100). This module lands that surface plus the two laws that bind an
extension:

* **Mandatory extension identity in every artifact (FM-8).** An extension's *distribution
  identity* and *version* are mandatory fields of every artifact it produces.
  :func:`stamp_extension_identity`
  stamps them into an artifact's identity content and :func:`require_extension_identity`
  refuses any artifact content missing either — so an extension artifact can never omit the
  identity that attributes it.

* **Graduation through the CT-16 extension shape (L33).** A concept the framework cannot yet
  articulate as a governed configuration is authorable as **plain Python outside governed
  evidence**, always. It enters governed evidence **only** by graduating through this
  extension shape — a separate versioned distribution on its own SemVer ladder — **with a
  lineage edge back to its originating research artifact** (:class:`ResearchLineage`).
  :func:`graduate` builds that :class:`RegisteredExtension`; a graduation without the lineage
  edge is refused.

The :class:`Catalog` is **immutable and functional**: :meth:`Catalog.register` returns a new
catalog carrying the added extension (refusing a duplicate distribution or a formula-id that
collides with an existing canonical owner), so the composition root threads one catalog and
readers resolve against it. There is **no scan, discover, or autoload** entry point — the
absence is the point. Each extension declares **package-owned** formula arithmetic under the
identical upgrade gate (a formula the pinned reference owns must be *wrapped*, not re-owned;
FM-5), so a formula already in the core ownership registry is refused.

Default-deny holds: this module imports **only** ``qmf.core`` and this package's own
modules. Public value types are frozen dataclasses and every operation succeeds or RETURNS a
CT-04 typed refusal (DEC-0101, DEC-0109, DEC-0120).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Ok, RefusalCategory, Result, Retryability, TypedRefusal, is_ok, is_refusal
from qmf.indicators.arithmetic import FormulaOwner, FormulaOwnership, canonical_owner

__all__ = [
    "EXTENSION_DISTRIBUTION_FIELD",
    "EXTENSION_VERSION_FIELD",
    "Catalog",
    "ExtensionIdentity",
    "RegisteredExtension",
    "ResearchLineage",
    "graduate",
    "require_extension_identity",
    "stamp_extension_identity",
]

# The two mandatory artifact-identity fields an extension stamps into every artifact it
# produces (CT-16 FM-8; DEC-0133, DEC-0100). Named once here so the stamper and the
# verifier can never drift apart.
EXTENSION_DISTRIBUTION_FIELD: Final[str] = "extension_distribution"
EXTENSION_VERSION_FIELD: Final[str] = "extension_version"


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a catalog operation returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO, context=context
    )


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


# --- extension identity -----------------------------------------------------


@dataclass(frozen=True, slots=True)
class ExtensionIdentity:
    """An extension's mandatory distribution + version identity (CT-16 FM-8; DEC-0100).

    ``distribution`` is the extension's distribution identity (a separate versioned package
    outside the roster on its own SemVer ladder) and ``version`` its version identity. Both
    are mandatory and enter every artifact the extension produces.
    """

    distribution: str
    version: str

    @classmethod
    def try_create(cls, distribution: object, version: object) -> Result[ExtensionIdentity]:
        """Validate and build an :class:`ExtensionIdentity`, returning value-or-refusal."""
        dist = _clean_str(distribution)
        if dist is None:
            return _invalid(
                "distribution",
                "an extension's distribution identity is a non-empty mandatory field",
                given=repr(distribution),
            )
        ver = _clean_str(version)
        if ver is None:
            return _invalid(
                "version",
                "an extension's version identity is a non-empty mandatory field",
                given=repr(version),
            )
        return Ok(cls(distribution=dist, version=ver))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this extension identity."""
        return {
            "class": "extension-identity",
            "distribution": self.distribution,
            "version": self.version,
        }


# --- the research lineage edge ----------------------------------------------


@dataclass(frozen=True, slots=True)
class ResearchLineage:
    """The lineage edge back to an extension's originating research artifact (L33; DEC-0133).

    ``research_artifact`` is the opaque identity of the research artifact the graduated
    extension descends from. It is mandatory for graduation: a plain-Python experiment enters
    governed evidence only carrying this edge back to where it came from.
    """

    research_artifact: str

    @classmethod
    def try_create(cls, research_artifact: object) -> Result[ResearchLineage]:
        """Validate and build a :class:`ResearchLineage`, returning value-or-refusal."""
        artifact = _clean_str(research_artifact)
        if artifact is None:
            return _invalid(
                "research_artifact",
                "the lineage edge names the originating research artifact (mandatory to graduate)",
                given=repr(research_artifact),
            )
        return Ok(cls(research_artifact=artifact))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this lineage edge."""
        return {"class": "research-lineage", "research_artifact": self.research_artifact}


# --- a registered extension -------------------------------------------------


@dataclass(frozen=True, slots=True)
class RegisteredExtension:
    """An indicator extension registered through the catalog surface (CT-16 FM-8; DEC-0133).

    ``identity`` is the mandatory distribution + version; ``formula_owners`` are the
    **package-owned** canonical owners the extension contributes (one per new formula, under
    the identical upgrade gate); ``lineage`` is the mandatory edge back to the originating
    research artifact. The frozen constructor is the trusted-internal path; :meth:`try_create`
    validates.
    """

    identity: ExtensionIdentity
    formula_owners: tuple[FormulaOwner, ...]
    lineage: ResearchLineage

    @classmethod
    def try_create(
        cls, identity: object, formula_owners: object, lineage: object
    ) -> Result[RegisteredExtension]:
        """Validate and build a :class:`RegisteredExtension`, returning value-or-refusal.

        ``identity`` an :class:`ExtensionIdentity`; ``lineage`` a :class:`ResearchLineage`;
        ``formula_owners`` a non-empty set of **package-owned**
        :class:`~qmf.indicators.FormulaOwner`\\ s whose ids are distinct, are not blank, and
        **do not collide with an existing canonical owner** — a formula the core ownership
        registry already owns is refused (each formula has exactly one canonical owner; a
        reference-owned formula must be wrapped, FM-5).
        """
        if not isinstance(identity, ExtensionIdentity):
            return _invalid("identity", "an ExtensionIdentity is required", given=repr(identity))
        if not isinstance(lineage, ResearchLineage):
            return _invalid(
                "lineage",
                "a ResearchLineage edge is required; graduation into governed evidence carries "
                "a lineage edge back to the originating research artifact (L33)",
                given=repr(lineage),
            )
        resolved = _coerce_owners(formula_owners)
        if isinstance(resolved, TypedRefusal):
            return resolved
        return Ok(cls(identity=identity, formula_owners=resolved, lineage=lineage))

    def formula_ids(self) -> tuple[str, ...]:
        """The formula ids this extension contributes, in declared order."""
        return tuple(owner.formula_id for owner in self.formula_owners)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this registered extension."""
        return {
            "class": "registered-extension",
            "identity": self.identity.fp1_identity(),
            "formula_ids": list(self.formula_ids()),
            "lineage": self.lineage.fp1_identity(),
        }


def _coerce_owners(value: object) -> tuple[FormulaOwner, ...] | TypedRefusal:
    """Resolve a non-empty set of package-owned, collision-free canonical owners, else refuse."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "formula_owners",
            "formula owners are a sequence of package-owned FormulaOwner values",
            given=repr(value),
        )
    resolved: list[FormulaOwner] = []
    seen: set[str] = set()
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, FormulaOwner):
            return _invalid(
                "formula_owners", "each owner is a FormulaOwner", index=index, given=repr(item)
            )
        if item.ownership is not FormulaOwnership.PACKAGE or item.reference_function is not None:
            return _invalid(
                "formula_owners",
                "an extension's formula is package-owned under the identical upgrade gate; a "
                "reference-owned formula must be wrapped, not re-owned (FM-5)",
                index=index,
                formula_id=item.formula_id,
            )
        if item.formula_id.strip() == "":
            return _invalid("formula_owners", "a formula id is non-empty", index=index)
        if item.formula_id in seen:
            return _invalid(
                "formula_owners", "formula ids are unique", index=index, formula_id=item.formula_id
            )
        core_owner = canonical_owner(item.formula_id)
        if is_ok(core_owner):
            return _invalid(
                "formula_owners",
                "the formula id already has a canonical owner in the core registry; an extension "
                "may not re-own it (each formula has exactly one canonical owner)",
                index=index,
                formula_id=item.formula_id,
            )
        seen.add(item.formula_id)
        resolved.append(item)
    if not resolved:
        return _invalid("formula_owners", "an extension contributes one or more formula owners")
    return tuple(resolved)


# --- the one named catalog surface ------------------------------------------


@dataclass(frozen=True, slots=True)
class Catalog:
    """The one named catalog surface for explicit extension registration (CT-16 FM-8; DEC-0133).

    Immutable and functional: :meth:`register` returns a **new** catalog carrying the added
    extension, so the composition root threads one catalog and readers resolve against it.
    Discovery is **explicit registration only** — there is no scan, discover, or autoload
    entry point; the absence is the point (FM-8). An extension is keyed by its distribution
    identity; a duplicate distribution or a formula-id collision across extensions is refused.
    """

    _extensions: Mapping[str, RegisteredExtension]

    @classmethod
    def empty(cls) -> Catalog:
        """An empty catalog — the composition root's starting point."""
        return cls(_extensions=MappingProxyType({}))

    def register(self, extension: object) -> Result[Catalog]:
        """Register an extension explicitly, returning a new catalog (CT-16 FM-8; DEC-0133).

        Refuses a non-:class:`RegisteredExtension`, a duplicate distribution identity, or a
        formula id already provided by another registered extension. On success returns a new
        immutable catalog with the extension added — never mutating this one.
        """
        if not isinstance(extension, RegisteredExtension):
            return _invalid("extension", "a RegisteredExtension is required", given=repr(extension))
        distribution = extension.identity.distribution
        if distribution in self._extensions:
            return _invalid(
                "extension",
                "an extension with this distribution identity is already registered",
                distribution=distribution,
            )
        existing_formulas = {
            formula_id: registered.identity.distribution
            for registered in self._extensions.values()
            for formula_id in registered.formula_ids()
        }
        for formula_id in extension.formula_ids():
            owner_distribution = existing_formulas.get(formula_id)
            if owner_distribution is not None:
                return _invalid(
                    "extension",
                    "another registered extension already provides this formula id",
                    formula_id=formula_id,
                    owned_by=owner_distribution,
                )
        updated = dict(self._extensions)
        updated[distribution] = extension
        return Ok(Catalog(_extensions=MappingProxyType(updated)))

    def resolve_distribution(self, distribution: object) -> Result[RegisteredExtension]:
        """The extension registered under ``distribution``, or an ``invalid input`` refusal."""
        if not isinstance(distribution, str):
            return _invalid(
                "distribution",
                "a distribution identity string is required",
                given=repr(distribution),
            )
        extension = self._extensions.get(distribution)
        if extension is None:
            return _invalid(
                "distribution",
                "no extension is registered under this distribution identity (registration is "
                "explicit; there is no ambient discovery)",
                distribution=distribution,
                registered=sorted(self._extensions),
            )
        return Ok(extension)

    def resolve_formula(self, formula_id: object) -> Result[RegisteredExtension]:
        """The extension providing ``formula_id``, or an ``invalid input`` refusal."""
        if not isinstance(formula_id, str):
            return _invalid("formula_id", "a formula id string is required", given=repr(formula_id))
        for extension in self._extensions.values():
            if formula_id in extension.formula_ids():
                return Ok(extension)
        return _invalid(
            "formula_id",
            "no registered extension provides this formula id",
            formula_id=formula_id,
        )

    def extensions(self) -> tuple[RegisteredExtension, ...]:
        """Every registered extension, ordered by distribution identity (reader)."""
        return tuple(self._extensions[key] for key in sorted(self._extensions))

    def formula_ids(self) -> tuple[str, ...]:
        """Every formula id any registered extension provides, sorted (reader)."""
        return tuple(
            sorted(
                formula_id
                for extension in self._extensions.values()
                for formula_id in extension.formula_ids()
            )
        )


# --- graduation -------------------------------------------------------------


def graduate(
    *,
    distribution: object,
    version: object,
    formula_ids: object,
    research_artifact: object,
) -> Result[RegisteredExtension]:
    """Graduate a plain-Python experiment into the CT-16 extension shape (L33; DEC-0133).

    Builds a :class:`RegisteredExtension` with the mandatory :class:`ExtensionIdentity`, a
    **package-owned** :class:`~qmf.indicators.FormulaOwner` for each new formula, and the
    **mandatory** lineage edge back to the originating research artifact. Refuses without the
    lineage edge, with an invalid identity, with no formula ids, or with a formula id that
    collides with an existing canonical owner. This is the only door from ungoverned
    plain-Python research into governed evidence.
    """
    identity = ExtensionIdentity.try_create(distribution, version)
    if is_refusal(identity):
        return identity
    lineage = ResearchLineage.try_create(research_artifact)
    if is_refusal(lineage):
        return lineage
    owners = _owners_from_ids(formula_ids)
    if isinstance(owners, TypedRefusal):
        return owners
    return RegisteredExtension.try_create(identity.value, owners, lineage.value)


def _owners_from_ids(formula_ids: object) -> tuple[FormulaOwner, ...] | TypedRefusal:
    """Build a package-owned :class:`FormulaOwner` for each declared formula id, else refuse."""
    if isinstance(formula_ids, (str, bytes)) or not isinstance(formula_ids, Sequence):
        return _invalid(
            "formula_ids",
            "formula ids are a sequence of non-empty formula-id strings",
            given=repr(formula_ids),
        )
    owners: list[FormulaOwner] = []
    for index, formula_id in enumerate(cast("Sequence[object]", formula_ids)):
        if not isinstance(formula_id, str) or formula_id.strip() == "":
            return _invalid(
                "formula_ids",
                "each formula id is a non-empty string",
                index=index,
                given=repr(formula_id),
            )
        owners.append(
            FormulaOwner(
                formula_id=formula_id, ownership=FormulaOwnership.PACKAGE, reference_function=None
            )
        )
    return tuple(owners)


# --- FM-8 artifact identity stamping ----------------------------------------


def stamp_extension_identity(identity: object, content: object) -> Result[dict[str, object]]:
    """Stamp an extension's mandatory identity into an artifact's content (CT-16 FM-8; DEC-0133).

    Returns a new identity mapping carrying every key of ``content`` plus the two mandatory
    extension identity fields (:data:`EXTENSION_DISTRIBUTION_FIELD`,
    :data:`EXTENSION_VERSION_FIELD`).
    Refuses a non-:class:`ExtensionIdentity` identity, a non-mapping content, or content that
    already carries a differing value under either mandatory field (an artifact may not
    misattribute itself).
    """
    if not isinstance(identity, ExtensionIdentity):
        return _invalid("identity", "an ExtensionIdentity is required", given=repr(identity))
    if not isinstance(content, Mapping):
        return _invalid(
            "content", "artifact identity content is a mapping", given=repr(type(content).__name__)
        )
    body = cast("Mapping[object, object]", content)
    stamped: dict[str, object] = {}
    for key, value in body.items():
        if not isinstance(key, str):
            return _invalid("content", "artifact identity keys are strings", key=repr(key))
        stamped[key] = value
    for field, expected in (
        (EXTENSION_DISTRIBUTION_FIELD, identity.distribution),
        (EXTENSION_VERSION_FIELD, identity.version),
    ):
        present = stamped.get(field)
        if present is not None and present != expected:
            return _invalid(
                "content",
                "the artifact already carries a differing extension identity field",
                offending_field=field,
                present=repr(present),
                expected=expected,
            )
        stamped[field] = expected
    return Ok(stamped)


def require_extension_identity(content: object) -> Result[None]:
    """Assert an artifact carries both mandatory extension identity fields (CT-16 FM-8).

    Every artifact an extension produces must carry its distribution identity and version. A
    content mapping missing or blanking either mandatory field is refused, so an extension
    artifact can never omit the identity that attributes it (FM-8; DEC-0133, DEC-0100).
    """
    if not isinstance(content, Mapping):
        return _invalid(
            "content", "artifact identity content is a mapping", given=repr(type(content).__name__)
        )
    body = cast("Mapping[object, object]", content)
    for field in (EXTENSION_DISTRIBUTION_FIELD, EXTENSION_VERSION_FIELD):
        value = body.get(field)
        if not isinstance(value, str) or value.strip() == "":
            return _invalid(
                "content",
                "an extension artifact must carry its distribution identity and version as "
                "mandatory fields (FM-8)",
                missing_field=field,
            )
    return Ok(None)
