"""Study-creation admission over the one CT-33 parameter-space schema (B-8).

A parameter-optimization Study declares a *search space*. The typed schema it is
declared in — name; type in ``exact integer | exact rational | categorical |
boolean``; bounds; step; mandatory default; optional hard-constraint filter; an
AD-40 unit-kind — is authoritative in the CT-33 Bot definition and is read through
the ONE schema coercer (:func:`qml.declaration.parameters.coerce_parameter_space`);
QMB keeps no second local copy (DEC-0173, DEC-0183).

:class:`StudyParameterSpace` is the Study-creation admission *over* that one
schema, not a second copy of it. On top of the CT-33 schema's own validation
(``min <= max``, ``step > 0``, categorical options non-empty, default in options,
the binary-float ban) it holds the search space to the two optimization-specific
rules the default-grid validation does not (OPT-1..4, spec-optimization intake):

* **OPT-3 search room** — a numeric parameter's ``step`` must not exceed its
  ``max - min`` span; a search range with no room for a step is a typed
  ``invalid input`` refusal, never a silent clamp (AD-11).
* **OPT-4 money is exact-integer minor units** — a parameter whose unit-kind is
  money must be declared ``exact integer`` so every bound is an exact-integer
  minor-unit value; declaring money as an exact rational (or as a category /
  boolean) is refused (FR-001; AD-7/AD-22).

The validated space is **identity-bearing**: :meth:`StudyParameterSpace.fp1_identity`
is materialized as content of the resolved run-config (never a code edit to swap
the tunnel — OPT-2), and :meth:`StudyParameterSpace.fingerprint` is the space
fingerprint. Two Studies declaring the same space share it, and because the
schema admits no binary float the money path never sees a float in identity
(AD-10, AR-14). A space that would not fingerprint clean is refused at creation.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import Final, cast

from qmf.core.exact import ExactRational, UnitKind
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qml.declaration.bot import BotDefinition
from qml.declaration.parameters import (
    ParameterSpec,
    ParameterType,
    coerce_parameter_space,
)

from qmb._refuse import invalid

__all__ = [
    "STUDY_SPACE_CLASS",
    "STUDY_SPACE_FORMAT_VERSION",
    "STUDY_SPACE_KEY",
    "StudyParameterSpace",
    "coerce_study_space",
    "study_space_from_bot",
    "study_space_identity",
]

STUDY_SPACE_CLASS: Final[str] = "qmb-study-parameter-space"
STUDY_SPACE_FORMAT_VERSION: Final[int] = 1

# The resolved-run-config key the validated space is materialized under. Its
# value is identity content (:meth:`StudyParameterSpace.fp1_identity`), so a
# Study's search space rides in the run-config's fp1 identity (OPT-2, AD-10).
STUDY_SPACE_KEY: Final[str] = "study_parameter_space"

# The numeric types the OPT-3 search-room rule applies to.
_NUMERIC_TYPES: Final[frozenset[ParameterType]] = frozenset(
    {ParameterType.EXACT_INTEGER, ParameterType.EXACT_RATIONAL}
)


def study_space_identity() -> dict[str, object]:
    """Identity-bearing schema-level fields. Package SemVer is omitted."""
    return {
        "class": STUDY_SPACE_CLASS,
        "format_version": STUDY_SPACE_FORMAT_VERSION,
        "run_config_key": STUDY_SPACE_KEY,
    }


@dataclass(frozen=True, slots=True)
class StudyParameterSpace:
    """A Study's validated, identity-bearing parameter search space (B-8, OPT-1..4).

    ``parameters`` is the CT-33-authoritative :class:`ParameterSpec` tuple, in the
    schema's canonical name order. The value object is the Study-creation
    admission over the one schema; it never redeclares the schema itself.
    """

    parameters: tuple[ParameterSpec, ...]

    @property
    def parameter_names(self) -> tuple[str, ...]:
        """The declared parameter names, in the schema's canonical order."""
        return tuple(spec.name for spec in self.parameters)

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity content. Values are exact; a binary float never appears."""
        return {
            "class": STUDY_SPACE_CLASS,
            "format_version": STUDY_SPACE_FORMAT_VERSION,
            "parameter_order": [spec.name for spec in self.parameters],
            "parameters": [spec.fp1_identity() for spec in self.parameters],
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The space ``fp1``, computed only by the single qmf-core seam.

        Two Studies declaring the same space share this fingerprint (AD-10).
        """
        return fingerprint(self.fp1_identity())

    def run_config_layer(self) -> dict[str, object]:
        """The identity-bearing config layer that materializes this space (OPT-2).

        Overlaid into the run-config layers, its content lands in the resolved
        run-config's ``keys`` and thus its fp1 identity — declaring the search
        space as config, never a code edit to swap the tunnel.
        """
        return {STUDY_SPACE_KEY: self.fp1_identity()}

    @classmethod
    def try_create(cls, parameters: object) -> Result[StudyParameterSpace]:
        """Admit a CT-33 :class:`ParameterSpec` tuple as a Study search space.

        Applies the OPT-3 search-room and OPT-4 money-unit rules, then confirms
        the space fingerprints clean so a binary float can never reach identity.
        """
        if isinstance(parameters, StudyParameterSpace):
            return Ok(parameters)
        # The one CT-33 schema coercer admits both a raw declaration sequence and
        # an already-built ParameterSpec tuple, sorting to canonical name order.
        coerced = coerce_parameter_space(parameters)
        if is_refusal(coerced):
            return coerced
        specs = coerced.value
        if not specs:
            return invalid(
                "parameter_space",
                "an optimization Study declares at least one parameter to search; "
                "a zero-dimensional search space has nothing to sample (B-8, OPT-1)",
            )
        for index, spec in enumerate(specs):
            checked = _admit_search_parameter(spec, index)
            if is_refusal(checked):
                return checked
        space = cls(parameters=specs)
        derived = space.fingerprint()
        if is_refusal(derived):
            return invalid(
                "parameter_space",
                "the declared search space is not fp1-clean identity content; a "
                "binary float never enters the money path's identity (FR-001, AD-10)",
                cause=dict(derived.context),
            )
        return Ok(space)


def coerce_study_space(declaration: object) -> Result[StudyParameterSpace]:
    """Validate a Study's declared parameter space at Study creation (B-8, OPT-1..4).

    ``declaration`` is an already-built :class:`StudyParameterSpace`, a CT-33
    :class:`BotDefinition`, a mapping carrying a ``parameter_space`` list, or a
    bare sequence of typed parameter declarations. The space is read through the
    one CT-33 schema coercer and then held to the Study search-space rules; an
    invalid space is refused up front, never at trial time.
    """
    if isinstance(declaration, StudyParameterSpace):
        return Ok(declaration)
    read = _read_parameter_space(declaration)
    if is_refusal(read):
        return read
    return StudyParameterSpace.try_create(read.value)


def study_space_from_bot(declaration: object) -> Result[StudyParameterSpace]:
    """Read and admit the CT-33-authoritative space of a Bot definition (B-8, DEC-0183).

    A thin Study-creation front over :meth:`BotDefinition` — the mandatory
    defaults remain the Bot's canonical assignment; a swept non-default value is a
    B-3 run-spec override in experimentation, never a silent new default.
    """
    if isinstance(declaration, BotDefinition):
        bot = declaration
    else:
        parsed = BotDefinition.try_from_mapping(declaration)
        if is_refusal(parsed):
            return parsed
        bot = parsed.value
    return StudyParameterSpace.try_create(tuple(bot.parameter_space))


def _read_parameter_space(declaration: object) -> Result[tuple[ParameterSpec, ...]]:
    """Read the declared space through the one CT-33 schema coercer."""
    if isinstance(declaration, BotDefinition):
        return Ok(tuple(declaration.parameter_space))
    if isinstance(declaration, Mapping):
        mapping = cast("Mapping[str, object]", declaration)
        if "parameter_space" in mapping:
            return coerce_parameter_space(mapping["parameter_space"])
        return invalid(
            "declaration",
            "a Study parameter-space config declares a `parameter_space` list of "
            "typed variables, or is a CT-33 Bot definition",
            given=sorted(str(key) for key in mapping),
        )
    if isinstance(declaration, (str, bytes)) or not isinstance(declaration, Sequence):
        return invalid(
            "declaration",
            "a Study parameter space is a sequence of typed variables, a mapping "
            "carrying `parameter_space`, or a CT-33 Bot definition",
            given=repr(type(declaration).__name__),
        )
    return coerce_parameter_space(cast("Sequence[object]", declaration))


def _admit_search_parameter(spec: ParameterSpec, index: int) -> Result[ParameterSpec]:
    """Hold one CT-33 parameter to the Study search-space rules (OPT-3, OPT-4)."""
    if spec.unit_kind is UnitKind.MONEY and spec.type is not ParameterType.EXACT_INTEGER:
        return invalid(
            "parameter_space",
            "a money parameter is declared as exact integer so every bound is an "
            "exact-integer minor-unit value; a non-integer money declaration is "
            "refused (FR-001, AD-7/AD-22, OPT-4)",
            parameter=spec.name,
            declared_type=spec.type.value,
            index=index,
        )
    if spec.type not in _NUMERIC_TYPES or spec.step is None or spec.bounds is None:
        return Ok(spec)
    span = _numeric_span(spec)
    step = _numeric_magnitude(spec.step)
    if span is None or step is None:
        return Ok(spec)
    if step > span:
        return invalid(
            "parameter_space",
            "a numeric search step must not exceed the max - min span; a step "
            "wider than the range leaves no room to search (OPT-3, AD-11)",
            parameter=spec.name,
            index=index,
        )
    return Ok(spec)


def _numeric_span(spec: ParameterSpec) -> Fraction | None:
    """The ``max - min`` span of a numeric parameter as an exact Fraction."""
    bounds = spec.bounds
    if bounds is None or len(bounds) != 2:
        return None
    low = _numeric_magnitude(bounds[0])
    high = _numeric_magnitude(bounds[1])
    if low is None or high is None:
        return None
    return high - low


def _numeric_magnitude(value: object) -> Fraction | None:
    """The exact magnitude of an integer or :class:`ExactRational`, else ``None``."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return Fraction(value)
    if isinstance(value, ExactRational):
        return value.as_fraction()
    return None
