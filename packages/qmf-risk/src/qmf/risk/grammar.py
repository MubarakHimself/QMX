"""Story 10.1 — the template grammar shared by CT-22 and CT-27 (COMP-QMF-RISK).

A Book or BMS template is a structured configuration artifact (JSON-Schema-class):
declared variables under one grammar, each carrying **four mandatory parts** and,
optionally, attached recorded evidence. This module defines that grammar on
``qmf-core`` nouns and nowhere else (AD-30, AD-40; DEC-0144, DEC-0154, DEC-0157):

* a **unit-kind** from the closed ``qmf-core`` :class:`~qmf.core.UnitKind`
  vocabulary — ``money(currency) | price-delta(instrument) | quantity(unit) |
  value-factor(instrument, currency) | r-multiple | rate(money-per-r) | count |
  dimensionless-ratio | duration | instant`` — addable in a spine amendment,
  never redefined and never extended per-Book;
* an **exact-rational or scaled-integer value** with **no binary float anywhere**
  — a ``qmf-core`` exact value (:class:`~qmf.core.Money`, :class:`~qmf.core.Price`,
  :class:`~qmf.core.PriceDelta`, :class:`~qmf.core.Quantity`,
  :class:`~qmf.core.ExactRational`, :class:`~qmf.core.ValueFactor`,
  :class:`~qmf.core.Duration`, :class:`~qmf.core.Instant`) whose own unit-kind must
  match the declared one, or an explicit :class:`NotYetRuled` blank marker
  (blankness is a *declared value*, never a ``null``; AD-10);
* a **``ui-editable | uneditable`` flag** — because *configurable* means editable
  in the platform settings UI, every configurable variable declares it (L38);
* an **``admission_impact`` of ``resign | relint | none``** — so an edit's cost is
  stated (a ``resign`` re-runs admission Layers 2+3; a ``relint`` re-runs Layer 1).

A variable **missing any of the four** is an ``invalid input`` refusal (AC1). A
recorded corpus or recollection number attached to a variable is
:class:`VariableEvidence` — carrying a stated source layer and authority grade —
and is **never** the variable's ratified value or a spine constant: a configurable
variable may ship with a ``NotYetRuled`` value and non-authoritative evidence
beside it (AC3; L38, DEC-0157).

Every value here is frozen and fp1-clean: a variable's four parts and its evidence
enter the template fingerprint, so a changed number changes ``fp1`` hence a new
Book/BMS identity (CT-22, CT-27; DEC-0144, DEC-0158). Imports only ``qmf-core``;
nothing imports ``qmf.risk`` (default-deny, L30/DEC-0120). This is ratified
``defined-unwired`` surface — records reach the registry only through the
composition root, and no wiring is authorized here (DEC-0158).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from qmf.core import (
    Duration,
    ExactRational,
    Instant,
    Money,
    Price,
    PriceDelta,
    Quantity,
    UnitKind,
    ValueFactor,
)
from qmf.core import (
    Ok as _Ok,
)
from qmf.core import (
    Result as _Result,
)
from qmf.core import (
    TypedRefusal as _TypedRefusal,
)
from qmf.risk._common import clean_str, coerce_enum, invalid

__all__ = [
    "AdmissionImpact",
    "AuthorityGrade",
    "NotYetRuled",
    "SourceLayer",
    "TemplateSection",
    "TemplateVariable",
    "UiEditability",
    "VariableEvidence",
    "VariableValue",
    "value_unit_kind",
]

# The template grammar's own contract format version stamped into fp1 identity
# content; its meaning never mutates — an incompatible change mints the next
# version (versioning-from-birth, L15; DEC-0103).
_GRAMMAR_FORMAT_VERSION = 1

# The exact ``qmf-core`` value carriers a declared variable value may take — every
# one is a scaled integer or an exact rational, fp1-clean and float-free by
# construction (CT-01; DEC-0105). ``NotYetRuled`` (an explicit blank) is the only
# other legal value; a raw float, int, str, or ``None`` is refused.
VariableValue = (
    Money | Price | PriceDelta | Quantity | ExactRational | ValueFactor | Duration | Instant
)


class UiEditability(StrEnum):
    """The ``ui-editable | uneditable`` flag every declared variable carries (L38).

    *Configurable* means editable in the platform settings UI: a ``UI_EDITABLE``
    variable surfaces there and a UI edit mints a new template version; an
    ``UNEDITABLE`` one does not. Exactly one member per variable — a missing flag
    is ``invalid input`` (DEC-0144, DEC-0157).
    """

    UI_EDITABLE = "ui-editable"
    UNEDITABLE = "uneditable"


class AdmissionImpact(StrEnum):
    """The declared cost of editing a variable (AD-30; DEC-0144).

    ``RESIGN`` — the edit demands a fresh admission Layer 2 + Layer 3 (the
    ``charter``, ``money_rules``, ``admission_bar``, ``required_venue_capabilities``
    variables). ``RELINT`` — Layer 1 only (``leash_grammar``, ``control_policy``,
    ``protection_windows`` numbers). ``NONE`` — no re-admission. Exactly one per
    variable; a missing impact is ``invalid input``.
    """

    RESIGN = "resign"
    RELINT = "relint"
    NONE = "none"


class SourceLayer(StrEnum):
    """The corpus layer a recorded evidence number came from (DEC-0156, DEC-0157).

    A stated provenance for attached evidence — never authority on its own. The set
    is addable, never redefined. For risk content the GitBook and trading-node
    documentation are authoritative while the QMX-discussion layer is barred as a
    source (L37, DEC-0156); an evidence record states which layer it came from so
    that rule is checkable rather than assumed.
    """

    GITBOOK = "gitbook"
    WIKI = "wiki"
    QMX_DISCUSSION = "qmx-discussion"
    NODE_DOCS = "node-docs"
    OPERATOR_RECOLLECTION = "operator-recollection"


class AuthorityGrade(StrEnum):
    """How much weight a recorded evidence number carries (L37; DEC-0156, DEC-0157).

    Evidence is ``AUTHORITATIVE`` or ``NON_AUTHORITATIVE`` — but it is **never** a
    ratified constant or spine value whatever its grade (see
    :class:`VariableEvidence`). A corpus recollection is non-authoritative; a
    GitBook/node-docs figure for risk content is authoritative evidence, still not
    a spine value.
    """

    AUTHORITATIVE = "authoritative"
    NON_AUTHORITATIVE = "non-authoritative"


def value_unit_kind(value: object) -> UnitKind | None:
    """The unit-kind of an accepted exact value carrier, or ``None``.

    A ``qmf-core`` value that declares its own :class:`~qmf.core.UnitKind` reports
    it; a :class:`~qmf.core.Duration` is ``duration`` and an
    :class:`~qmf.core.Instant` is ``instant``. A ``bool`` (an int subclass), a
    binary ``float``, a bare ``int``, a ``str``, ``None``, or any other type is not
    an accepted carrier and returns ``None`` — the caller turns that into the right
    refusal (a float is refused off the money path; ``None`` names a *missing*
    value, distinct from an explicit :class:`NotYetRuled` blank).
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (Money, Price, PriceDelta, Quantity, ExactRational, ValueFactor)):
        return value.unit_kind
    if isinstance(value, Duration):
        return UnitKind.DURATION
    if isinstance(value, Instant):
        return UnitKind.INSTANT
    return None


@dataclass(frozen=True, slots=True)
class NotYetRuled:
    """An explicit blank value carrying its gap reference (AD-10; DEC-0146).

    Blankness is a *declared value*, never a ``null`` and never key absence: a
    configurable variable whose number is not yet ruled declares ``NotYetRuled``
    with the gap it awaits, so blankness is honest, fingerprintable, and — per the
    blank-blocks-live-money rule (a later story) — free to register and bind
    non-live while blocking a live binding.
    """

    gap_ref: str

    @classmethod
    def try_create(cls, gap_ref: object) -> _Result[NotYetRuled]:
        """Validate and build a :class:`NotYetRuled`, returning value-or-refusal.

        The gap reference is a non-blank opaque token (e.g. ``GAP-0048``); a blank
        or non-string one is ``invalid input``.
        """
        token = clean_str(gap_ref)
        if token is None:
            return invalid(
                "gap_ref",
                "a not-yet-ruled blank declares its gap reference as a non-empty token",
                given=repr(gap_ref),
            )
        return _Ok(cls(gap_ref=token))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this blank."""
        return {
            "class": "not-yet-ruled",
            "gap_ref": self.gap_ref,
            "format_version": _GRAMMAR_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class VariableEvidence:
    """A recorded corpus or recollection number attached to a variable (L38; DEC-0157).

    Evidence is **never** the variable's ratified value and **never** a spine
    constant: :attr:`is_ratified_constant` is ``False`` by construction, whatever
    the source layer or authority grade. It carries the recorded exact value, the
    stated :class:`SourceLayer` it came from, its :class:`AuthorityGrade`, and an
    optional human note — so a variable can ship with a ``NotYetRuled`` value and
    honest evidence beside it, and no recorded number is ever mistaken for a
    ratified constant (L38).
    """

    recorded_value: VariableValue
    source_layer: SourceLayer
    authority_grade: AuthorityGrade
    note: str | None = None

    @property
    def is_ratified_constant(self) -> bool:
        """Recorded evidence is never a ratified constant or spine value (L38)."""
        return False

    @classmethod
    def try_create(
        cls,
        recorded_value: object,
        source_layer: object,
        authority_grade: object,
        note: object = None,
    ) -> _Result[VariableEvidence]:
        """Validate and build a :class:`VariableEvidence`, returning value-or-refusal.

        The recorded value must be a ``qmf-core`` exact carrier (no binary float, no
        bare int, and not a :class:`NotYetRuled` — evidence records a *number*, and
        a blank has no number to record); the source layer and authority grade must
        each be members of their sets; an optional note is a non-blank string.
        """
        kind = value_unit_kind(recorded_value)
        if kind is None:
            return invalid(
                "recorded_value",
                "recorded evidence is an exact qmf-core value (scaled integer or exact "
                "rational, no binary float); a blank records no number",
                given=repr(recorded_value),
            )
        resolved_layer = coerce_enum(SourceLayer, source_layer)
        if resolved_layer is None:
            return invalid(
                "source_layer",
                "evidence declares the corpus layer it came from",
                given=repr(source_layer),
                allowed=[member.value for member in SourceLayer],
            )
        resolved_grade = coerce_enum(AuthorityGrade, authority_grade)
        if resolved_grade is None:
            return invalid(
                "authority_grade",
                "evidence declares an authority grade",
                given=repr(authority_grade),
                allowed=[member.value for member in AuthorityGrade],
            )
        clean_note: str | None = None
        if note is not None:
            clean_note = clean_str(note)
            if clean_note is None:
                return invalid(
                    "note",
                    "an evidence note, when present, is a non-empty string",
                    given=repr(note),
                )
        return _Ok(
            cls(
                recorded_value=cast("VariableValue", recorded_value),
                source_layer=resolved_layer,
                authority_grade=resolved_grade,
                note=clean_note,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this evidence."""
        content: dict[str, object] = {
            "class": "variable-evidence",
            "recorded_value": self.recorded_value.fp1_identity(),
            "source_layer": self.source_layer.value,
            "authority_grade": self.authority_grade.value,
            "is_ratified_constant": False,
            "format_version": _GRAMMAR_FORMAT_VERSION,
        }
        if self.note is not None:
            content["note"] = self.note
        return content


@dataclass(frozen=True, slots=True)
class TemplateVariable:
    """One declared template variable — the four-part grammar (AC1; DEC-0144).

    Carries a ``name``, a declared :class:`~qmf.core.UnitKind`, a ``value`` (an
    exact carrier whose own unit-kind matches, or a :class:`NotYetRuled` blank), a
    :class:`UiEditability` flag, an :class:`AdmissionImpact`, and optional attached
    :class:`VariableEvidence`. A variable missing any of the four mandatory parts
    is an ``invalid input`` refusal.
    """

    name: str
    unit_kind: UnitKind
    value: VariableValue | NotYetRuled
    ui_editable: UiEditability
    admission_impact: AdmissionImpact
    evidence: VariableEvidence | None = None

    @classmethod
    def try_create(
        cls,
        name: object,
        unit_kind: object,
        value: object,
        ui_editable: object,
        admission_impact: object,
        evidence: object = None,
    ) -> _Result[TemplateVariable]:
        """Validate and build a :class:`TemplateVariable`, returning value-or-refusal.

        Missing (or unrecognised) any of the four mandatory parts — unit-kind,
        value, ui-editable flag, admission impact — is ``invalid input``. A binary
        float or bare int value is refused (no binary float on the money path); a
        value whose own unit-kind disagrees with the declared one is refused (the
        dimensional discipline begins at declaration — a ``count`` cannot stand
        where an ``r-multiple`` is declared).
        """
        clean_name = clean_str(name)
        if clean_name is None:
            return invalid(
                "name", "a template variable declares a non-empty name", given=repr(name)
            )
        resolved_kind = coerce_enum(UnitKind, unit_kind)
        if resolved_kind is None:
            return invalid(
                "unit_kind",
                "a template variable is missing its unit-kind, or names one outside the "
                "closed AD-40 vocabulary",
                given=repr(unit_kind),
                allowed=[member.value for member in UnitKind],
            )
        value_refusal = _validate_value(resolved_kind, value)
        if value_refusal is not None:
            return value_refusal
        resolved_ui = coerce_enum(UiEditability, ui_editable)
        if resolved_ui is None:
            return invalid(
                "ui_editable",
                "a template variable is missing its ui-editable flag",
                given=repr(ui_editable),
                allowed=[member.value for member in UiEditability],
            )
        resolved_impact = coerce_enum(AdmissionImpact, admission_impact)
        if resolved_impact is None:
            return invalid(
                "admission_impact",
                "a template variable is missing its admission_impact",
                given=repr(admission_impact),
                allowed=[member.value for member in AdmissionImpact],
            )
        resolved_evidence: VariableEvidence | None = None
        if evidence is not None:
            if not isinstance(evidence, VariableEvidence):
                return invalid(
                    "evidence",
                    "attached evidence is a VariableEvidence (recorded number + source "
                    "layer + authority grade), never a bare value or a ratified constant",
                    given=repr(evidence),
                )
            resolved_evidence = evidence
        return _Ok(
            cls(
                name=clean_name,
                unit_kind=resolved_kind,
                value=cast("VariableValue | NotYetRuled", value),
                ui_editable=resolved_ui,
                admission_impact=resolved_impact,
                evidence=resolved_evidence,
            )
        )

    @property
    def is_blank(self) -> bool:
        """True when the value is an explicit :class:`NotYetRuled` blank (DEC-0146)."""
        return isinstance(self.value, NotYetRuled)

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — all four parts plus any
        evidence enter identity, so a changed number changes ``fp1`` (DEC-0144)."""
        content: dict[str, object] = {
            "class": "template-variable",
            "name": self.name,
            "unit_kind": self.unit_kind.value,
            "value": self.value.fp1_identity(),
            "ui_editable": self.ui_editable.value,
            "admission_impact": self.admission_impact.value,
            "format_version": _GRAMMAR_FORMAT_VERSION,
        }
        if self.evidence is not None:
            content["evidence"] = self.evidence.fp1_identity()
        return content


def _validate_value(declared_kind: UnitKind, value: object) -> _TypedRefusal | None:
    """Validate a variable's value against its declared unit-kind.

    Returns ``None`` when the value is legal, or the ``TypedRefusal`` to return.
    ``None`` as the value names a *missing* value — blankness must be an explicit
    :class:`NotYetRuled` marker, never a ``null`` (AD-10). A :class:`NotYetRuled`
    passes (the declared unit-kind stands). Any other value must be an exact
    carrier whose own unit-kind equals the declared one.
    """
    if value is None:
        return invalid(
            "value",
            "a template variable is missing its value; blankness is an explicit "
            "NotYetRuled marker, never a null (AD-10)",
        )
    if isinstance(value, NotYetRuled):
        return None
    resolved = value_unit_kind(value)
    if resolved is None:
        return invalid(
            "value",
            "a template variable value is an exact qmf-core value (scaled integer or "
            "exact rational, no binary float) or a NotYetRuled blank",
            given=repr(value),
        )
    if resolved is not declared_kind:
        return invalid(
            "value",
            "the value's unit-kind disagrees with the declared unit-kind; the "
            "dimensional discipline binds every declared variable (DEC-0154)",
            declared=declared_kind.value,
            value_unit_kind=resolved.value,
        )
    return None


@dataclass(frozen=True, slots=True)
class TemplateSection:
    """A named section of a Book/BMS template — a mapping of declared variables.

    A section carries a ``name`` (e.g. ``money_rules``) and its variables keyed by
    name. Sections are the unit the ten Book sections and the BMS sections are
    declared in (CT-22, CT-27; DEC-0144).
    """

    name: str
    variables: Mapping[str, TemplateVariable]

    def __post_init__(self) -> None:
        # Snapshot the variables mapping into a read-only proxy so a later mutation
        # of the caller's dict can never reach back into this frozen section.
        object.__setattr__(self, "variables", MappingProxyType(dict(self.variables)))

    @classmethod
    def try_create(cls, name: object, variables: object) -> _Result[TemplateSection]:
        """Validate and build a :class:`TemplateSection`, returning value-or-refusal.

        The name is a non-empty string; ``variables`` is a mapping whose every key
        is a non-blank string and every value a :class:`TemplateVariable` whose key
        matches its own name.
        """
        clean_name = clean_str(name)
        if clean_name is None:
            return invalid("name", "a template section declares a non-empty name", given=repr(name))
        if not isinstance(variables, Mapping):
            return invalid(
                "variables",
                "a template section's variables are a name-keyed mapping",
                given=repr(type(variables).__name__),
            )
        variable_map = cast("Mapping[object, object]", variables)
        resolved: dict[str, TemplateVariable] = {}
        for key, variable in variable_map.items():
            token = clean_str(key)
            if token is None:
                return invalid("variables", "a variable key is a non-empty string", given=repr(key))
            if not isinstance(variable, TemplateVariable):
                return invalid(
                    "variables",
                    "each section entry is a TemplateVariable",
                    key=token,
                    given=repr(variable),
                )
            if variable.name != token:
                return invalid(
                    "variables",
                    "a variable's key must equal its declared name",
                    key=token,
                    variable_name=variable.name,
                )
            resolved[token] = variable
        return _Ok(cls(name=clean_name, variables=resolved))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this section.

        Variables are carried as a name-keyed object; the canonical serializer sorts
        keys at every depth, so declaration order never forks a section's identity.
        """
        return {
            "class": "template-section",
            "name": self.name,
            "variables": {
                name: variable.fp1_identity() for name, variable in self.variables.items()
            },
            "format_version": _GRAMMAR_FORMAT_VERSION,
        }
