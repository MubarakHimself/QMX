"""CT-33 declared parameter space — B-8 schema completed with AD-40 unit-kinds.

One schema, never two (DEC-0173, DEC-0183). Each variable carries a type in
``exact integer | exact rational | categorical | boolean``, bounds, step, a
mandatory default, an optional hard-constraint filter, an AD-40 unit-kind, and
exactly one ``ui-editable | uneditable`` flag. Defaults together are the
canonical assignment — a derived projection, never a separate declared field.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core.exact import ExactRational, UnitKind
from qmf.core.refusal import Ok, Result, is_ok, is_refusal

from qml._refuse import clean_token, invalid
from qml.footprint._coerce import coerce_exact_rational, fp1_clean

__all__ = [
    "CONSTRAINT_OPS",
    "PARAMETER_TYPES",
    "HardConstraintFilter",
    "ParameterSpec",
    "ParameterType",
    "UiFlag",
    "canonical_assignment_of",
    "coerce_parameter_space",
    "parse_parameter_type",
    "parse_ui_flag",
]

_KNOWN_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "name",
        "type",
        "bounds",
        "min",
        "max",
        "step",
        "default",
        "hard_constraint",
        "hard_constraint_filter",
        "unit_kind",
        "ui",
        "ui_flag",
        "ui_editable",
        "options",
    }
)


class ParameterType(StrEnum):
    """B-8 closed parameter-type vocabulary (DEC-0173)."""

    EXACT_INTEGER = "exact integer"
    EXACT_RATIONAL = "exact rational"
    CATEGORICAL = "categorical"
    BOOLEAN = "boolean"


PARAMETER_TYPES: Final[frozenset[str]] = frozenset(member.value for member in ParameterType)


class UiFlag(StrEnum):
    """AD-30 template discipline — exactly one flag per declared variable (DEC-0144)."""

    UI_EDITABLE = "ui-editable"
    UNEDITABLE = "uneditable"


CONSTRAINT_OPS: Final[frozenset[str]] = frozenset({"<", "<=", ">", ">=", "=", "!="})


def parse_parameter_type(value: object) -> Result[ParameterType]:
    """Resolve a parameter type, value-or-refusal."""
    if isinstance(value, ParameterType):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(ParameterType(value))
        except ValueError:
            pass
    return invalid(
        "type",
        "a parameter type is exact integer | exact rational | categorical | boolean",
        given=repr(value),
        allowed=sorted(PARAMETER_TYPES),
    )


def parse_ui_flag(value: object) -> Result[UiFlag]:
    """Resolve the AD-30 ui-editable | uneditable flag."""
    if isinstance(value, UiFlag):
        return Ok(value)
    if isinstance(value, bool):
        return Ok(UiFlag.UI_EDITABLE if value else UiFlag.UNEDITABLE)
    if isinstance(value, str):
        try:
            return Ok(UiFlag(value))
        except ValueError:
            pass
        if value in {"editable", "ui_editable"}:
            return Ok(UiFlag.UI_EDITABLE)
        if value in {"locked", "ui_uneditable"}:
            return Ok(UiFlag.UNEDITABLE)
    return invalid(
        "ui",
        "every declared variable carries exactly one ui-editable | uneditable flag",
        given=repr(value),
    )


def _plain_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _coerce_unit_kind(value: object) -> Result[UnitKind]:
    if value is None:
        return invalid(
            "unit_kind",
            "a parameter missing its AD-40 unit-kind is invalid input",
            given=repr(value),
        )
    if isinstance(value, UnitKind):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(UnitKind(value))
        except ValueError:
            pass
    return invalid(
        "unit_kind",
        "a parameter unit-kind is a member of the closed AD-40 vocabulary",
        given=repr(value),
        allowed=[member.value for member in UnitKind],
    )


def _value_identity(value: object) -> object:
    if isinstance(value, ExactRational):
        return value.fp1_identity()
    return value


@dataclass(frozen=True, slots=True)
class HardConstraintFilter:
    """Optional metric-operator-value filter on a declared parameter (B-8)."""

    measure_identity: str
    op: str
    value: object

    def fp1_identity(self) -> dict[str, object]:
        return {
            "measure_identity": self.measure_identity,
            "op": self.op,
            "value": _value_identity(self.value),
        }

    @classmethod
    def try_create(cls, payload: object) -> Result[HardConstraintFilter]:
        if isinstance(payload, cls):
            return Ok(payload)
        if not isinstance(payload, Mapping):
            return invalid(
                "hard_constraint",
                "a hard-constraint filter is {measure_identity, op, value}",
                given=type(payload).__name__,
            )
        mapping = cast("Mapping[str, object]", payload)
        measure = clean_token(mapping.get("measure_identity", mapping.get("measure")))
        if measure is None:
            return invalid(
                "hard_constraint",
                "a hard-constraint filter names a non-empty measure identity",
                given=repr(mapping.get("measure_identity", mapping.get("measure"))),
            )
        op = mapping.get("op", mapping.get("operator"))
        if not isinstance(op, str) or op not in CONSTRAINT_OPS:
            return invalid(
                "hard_constraint",
                "a hard-constraint operator is < | <= | > | >= | = | !=",
                given=repr(op),
            )
        raw_value = mapping.get("value")
        if raw_value is None:
            return invalid(
                "hard_constraint",
                "a hard-constraint filter carries a value; an absent value is an "
                "omitted filter, never a null (AD-10)",
            )
        if isinstance(raw_value, float):
            return invalid(
                "hard_constraint",
                "hard-constraint values are exact; a binary float is refused (AD-7)",
                given=repr(raw_value),
            )
        coerced: object = raw_value
        parsed = coerce_exact_rational(raw_value, field="hard_constraint")
        if is_ok(parsed):
            coerced = parsed.value
        elif isinstance(raw_value, ExactRational):
            return parsed
        clean = fp1_clean(_value_identity(coerced), "hard_constraint")
        if clean is not None:
            return clean
        return Ok(cls(measure_identity=measure, op=op, value=coerced))


@dataclass(frozen=True, slots=True)
class ParameterSpec:
    """One declared bot-space variable. Defaults enter the canonical assignment."""

    name: str
    type: ParameterType
    unit_kind: UnitKind
    default: object
    ui: UiFlag
    bounds: tuple[object, ...] | None = None
    step: object | None = None
    hard_constraint: HardConstraintFilter | None = None

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "name": self.name,
            "type": self.type.value,
            "unit_kind": self.unit_kind.value,
            "default": _value_identity(self.default),
            "ui": self.ui.value,
        }
        if self.bounds is not None:
            content["bounds"] = self._bounds_identity()
        if self.step is not None:
            content["step"] = _value_identity(self.step)
        if self.hard_constraint is not None:
            content["hard_constraint"] = self.hard_constraint.fp1_identity()
        return content

    def _bounds_identity(self) -> object:
        bounds = self.bounds
        if bounds is None:
            return {}
        if len(bounds) == 2 and self.type in {
            ParameterType.EXACT_INTEGER,
            ParameterType.EXACT_RATIONAL,
        }:
            return {"min": _value_identity(bounds[0]), "max": _value_identity(bounds[1])}
        return [_value_identity(item) for item in bounds]

    def assignment_value(self) -> object:
        """The default as the canonical-assignment cell for this name."""
        return self.default

    def with_default(self, default: object) -> Result[ParameterSpec]:
        """Mint a copy whose default is ``default`` (a tuned assignment promotion)."""
        payload: dict[str, object] = {
            "name": self.name,
            "type": self.type,
            "unit_kind": self.unit_kind,
            "default": default,
            "ui": self.ui,
        }
        encoded = self._bounds_payload()
        if encoded is not None:
            payload["bounds"] = encoded
        if self.step is not None:
            payload["step"] = self.step
        if self.hard_constraint is not None:
            payload["hard_constraint"] = self.hard_constraint
        return self.try_create(payload)

    def _bounds_payload(self) -> object | None:
        if self.bounds is None:
            return None
        if (
            self.type in {ParameterType.EXACT_INTEGER, ParameterType.EXACT_RATIONAL}
            and len(self.bounds) == 2
        ):
            return {"min": self.bounds[0], "max": self.bounds[1]}
        return self.bounds

    @classmethod
    def try_create(cls, payload: object, *, index: int = 0) -> Result[ParameterSpec]:
        """Validate one parameter; a missing unit-kind is ``invalid input``."""
        if isinstance(payload, cls):
            return Ok(payload)
        if not isinstance(payload, Mapping):
            return invalid(
                "parameter_space",
                "each declared variable is a mapping of name, type, bounds, step, "
                "mandatory default, optional hard-constraint filter, and unit-kind",
                given=type(payload).__name__,
                index=index,
            )
        mapping = cast("Mapping[str, object]", payload)
        unknown = sorted(set(mapping) - _KNOWN_FIELDS)
        if unknown:
            return invalid(
                "parameter_space",
                "a declared variable carries name, type, bounds, step, default, "
                "optional hard_constraint, unit_kind, and ui only",
                unknown=unknown,
                index=index,
            )
        name = clean_token(mapping.get("name"))
        if name is None:
            return invalid(
                "name",
                "a declared parameter names a non-empty token",
                given=repr(mapping.get("name")),
                index=index,
            )
        parsed_type = parse_parameter_type(mapping.get("type"))
        if is_refusal(parsed_type):
            return parsed_type
        kind = _coerce_unit_kind(mapping.get("unit_kind"))
        if is_refusal(kind):
            return kind
        if "ui" not in mapping and "ui_flag" not in mapping and "ui_editable" not in mapping:
            return invalid(
                "ui",
                "every declared variable carries exactly one ui-editable | uneditable flag",
                index=index,
                name=name,
            )
        ui = parse_ui_flag(mapping.get("ui", mapping.get("ui_flag", mapping.get("ui_editable"))))
        if is_refusal(ui):
            return ui
        raw_constraint = mapping.get("hard_constraint", mapping.get("hard_constraint_filter"))
        constraint: HardConstraintFilter | None = None
        if raw_constraint is not None:
            parsed_constraint = HardConstraintFilter.try_create(raw_constraint)
            if is_refusal(parsed_constraint):
                return parsed_constraint
            constraint = parsed_constraint.value
        built = _build_typed(
            name=name,
            param_type=parsed_type.value,
            unit_kind=kind.value,
            ui=ui.value,
            mapping=mapping,
            index=index,
            constraint=constraint,
        )
        if is_refusal(built):
            return built
        return built


def _build_typed(
    *,
    name: str,
    param_type: ParameterType,
    unit_kind: UnitKind,
    ui: UiFlag,
    mapping: Mapping[str, object],
    index: int,
    constraint: HardConstraintFilter | None,
) -> Result[ParameterSpec]:
    if param_type is ParameterType.EXACT_INTEGER:
        return _build_integer(name, unit_kind, ui, mapping, index, constraint)
    if param_type is ParameterType.EXACT_RATIONAL:
        return _build_rational(name, unit_kind, ui, mapping, index, constraint)
    if param_type is ParameterType.CATEGORICAL:
        return _build_categorical(name, unit_kind, ui, mapping, index, constraint)
    return _build_boolean(name, unit_kind, ui, mapping, index, constraint)


def _require_default(mapping: Mapping[str, object], index: int, name: str) -> Result[object]:
    if "default" not in mapping:
        return invalid(
            "default",
            "every declared parameter carries a mandatory default; defaults together "
            "are the canonical assignment",
            index=index,
            name=name,
        )
    if mapping["default"] is None:
        return invalid(
            "default",
            "a default is a declared value, never null (AD-10)",
            index=index,
            name=name,
        )
    return Ok(mapping["default"])


def _bounds_map(mapping: Mapping[str, object]) -> Mapping[str, object] | None:
    raw = mapping.get("bounds")
    if isinstance(raw, Mapping):
        return cast("Mapping[str, object]", raw)
    return None


def _build_integer(
    name: str,
    unit_kind: UnitKind,
    ui: UiFlag,
    mapping: Mapping[str, object],
    index: int,
    constraint: HardConstraintFilter | None,
) -> Result[ParameterSpec]:
    default_raw = _require_default(mapping, index, name)
    if is_refusal(default_raw):
        return default_raw
    default = _plain_int(default_raw.value)
    if default is None:
        return invalid(
            "default",
            "an exact-integer default is a scaled integer; a binary float is refused",
            given=repr(default_raw.value),
            index=index,
        )
    bounds = _bounds_map(mapping)
    raw_min = mapping.get("min") if bounds is None else bounds.get("min", mapping.get("min"))
    raw_max = mapping.get("max") if bounds is None else bounds.get("max", mapping.get("max"))
    low = _plain_int(raw_min)
    high = _plain_int(raw_max)
    if low is None or high is None:
        return invalid(
            "bounds",
            "an exact-integer parameter carries integer min/max bounds",
            given=repr({"min": raw_min, "max": raw_max}),
            index=index,
        )
    if low > high:
        return invalid("bounds", "min must not exceed max", min=low, max=high, index=index)
    step = _plain_int(mapping.get("step"))
    if step is None or step < 1:
        return invalid(
            "step",
            "an exact-integer step is a positive integer",
            given=repr(mapping.get("step")),
            index=index,
        )
    if default < low or default > high:
        return invalid(
            "default",
            "the default must lie within the declared bounds",
            default=default,
            min=low,
            max=high,
            index=index,
        )
    if (default - low) % step != 0:
        return invalid(
            "default",
            "the default must land on the declared step grid",
            default=default,
            min=low,
            step=step,
            index=index,
        )
    return Ok(
        ParameterSpec(
            name=name,
            type=ParameterType.EXACT_INTEGER,
            unit_kind=unit_kind,
            default=default,
            ui=ui,
            bounds=(low, high),
            step=step,
            hard_constraint=constraint,
        )
    )


def _rational_at(
    value: object, *, field: str, unit_kind: UnitKind, index: int
) -> Result[ExactRational]:
    if isinstance(value, float):
        return invalid(
            field,
            "an exact-rational value is an ExactRational; a binary float is refused (AD-7)",
            given=repr(value),
            index=index,
        )
    parsed = coerce_exact_rational(value, field=field)
    if is_refusal(parsed):
        if _plain_int(value) is not None:
            parsed = ExactRational.try_create(value, 1, unit_kind)
        if is_refusal(parsed):
            return invalid(
                field,
                "an exact-rational value is an ExactRational (num/den + AD-40 unit-kind)",
                given=repr(value),
                index=index,
            )
    if parsed.value.unit_kind is not unit_kind:
        return invalid(
            field,
            "the value's unit-kind must match the declared parameter unit-kind",
            given=parsed.value.unit_kind.value,
            unit_kind=unit_kind.value,
            index=index,
        )
    return parsed


def _build_rational(
    name: str,
    unit_kind: UnitKind,
    ui: UiFlag,
    mapping: Mapping[str, object],
    index: int,
    constraint: HardConstraintFilter | None,
) -> Result[ParameterSpec]:
    default_raw = _require_default(mapping, index, name)
    if is_refusal(default_raw):
        return default_raw
    default = _rational_at(default_raw.value, field="default", unit_kind=unit_kind, index=index)
    if is_refusal(default):
        return default
    bounds = _bounds_map(mapping)
    raw_min = mapping.get("min") if bounds is None else bounds.get("min", mapping.get("min"))
    raw_max = mapping.get("max") if bounds is None else bounds.get("max", mapping.get("max"))
    low = _rational_at(raw_min, field="bounds", unit_kind=unit_kind, index=index)
    if is_refusal(low):
        return low
    high = _rational_at(raw_max, field="bounds", unit_kind=unit_kind, index=index)
    if is_refusal(high):
        return high
    if low.value.as_fraction() > high.value.as_fraction():
        return invalid("bounds", "min must not exceed max", index=index)
    step = _rational_at(mapping.get("step"), field="step", unit_kind=unit_kind, index=index)
    if is_refusal(step):
        return step
    if step.value.as_fraction() <= 0:
        return invalid("step", "an exact-rational step is a positive exact rational", index=index)
    default_q = default.value.as_fraction()
    if default_q < low.value.as_fraction() or default_q > high.value.as_fraction():
        return invalid(
            "default",
            "the default must lie within the declared bounds",
            index=index,
        )
    offset = default_q - low.value.as_fraction()
    step_q = step.value.as_fraction()
    if (offset / step_q).denominator != 1:
        return invalid(
            "default",
            "the default must land on the declared step grid",
            index=index,
        )
    return Ok(
        ParameterSpec(
            name=name,
            type=ParameterType.EXACT_RATIONAL,
            unit_kind=unit_kind,
            default=default.value,
            ui=ui,
            bounds=(low.value, high.value),
            step=step.value,
            hard_constraint=constraint,
        )
    )


def _build_categorical(
    name: str,
    unit_kind: UnitKind,
    ui: UiFlag,
    mapping: Mapping[str, object],
    index: int,
    constraint: HardConstraintFilter | None,
) -> Result[ParameterSpec]:
    default_raw = _require_default(mapping, index, name)
    if is_refusal(default_raw):
        return default_raw
    default = default_raw.value
    if not isinstance(default, str) or default.strip() == "":
        return invalid(
            "default",
            "a categorical default is a non-empty option token",
            given=repr(default),
            index=index,
        )
    raw_options = mapping.get("options", mapping.get("bounds"))
    if isinstance(raw_options, Mapping):
        nested = cast("Mapping[str, object]", raw_options)
        raw_options = nested.get("options", nested.get("values"))
    if isinstance(raw_options, (str, bytes)) or not isinstance(raw_options, Sequence):
        return invalid(
            "bounds",
            "a categorical parameter's bounds are a non-empty options list",
            given=type(raw_options).__name__,
            index=index,
        )
    options: list[str] = []
    seen: set[str] = set()
    for item in cast("Sequence[object]", raw_options):
        token = clean_token(item)
        if token is None:
            return invalid(
                "bounds",
                "categorical options are non-empty strings",
                given=repr(item),
                index=index,
            )
        if token in seen:
            return invalid("bounds", "categorical options are unique", option=token, index=index)
        seen.add(token)
        options.append(token)
    if not options:
        return invalid(
            "bounds", "a categorical parameter declares one or more options", index=index
        )
    if default not in seen:
        return invalid(
            "default",
            "the categorical default must be one of the declared options",
            default=default,
            index=index,
        )
    step = mapping.get("step")
    if step is not None:
        return invalid(
            "step",
            "a categorical parameter has no numeric step; options are the bounds",
            given=repr(step),
            index=index,
        )
    return Ok(
        ParameterSpec(
            name=name,
            type=ParameterType.CATEGORICAL,
            unit_kind=unit_kind,
            default=default,
            ui=ui,
            bounds=tuple(options),
            step=None,
            hard_constraint=constraint,
        )
    )


def _build_boolean(
    name: str,
    unit_kind: UnitKind,
    ui: UiFlag,
    mapping: Mapping[str, object],
    index: int,
    constraint: HardConstraintFilter | None,
) -> Result[ParameterSpec]:
    default_raw = _require_default(mapping, index, name)
    if is_refusal(default_raw):
        return default_raw
    default = default_raw.value
    if not isinstance(default, bool):
        return invalid(
            "default",
            "a boolean default is true or false",
            given=repr(default),
            index=index,
        )
    if mapping.get("step") is not None:
        return invalid(
            "step",
            "a boolean parameter has no numeric step; the domain is {true, false}",
            given=repr(mapping.get("step")),
            index=index,
        )
    raw_bounds = mapping.get("bounds")
    if raw_bounds is not None:
        return invalid(
            "bounds",
            "a boolean parameter's domain is {true, false}; bounds are not declared",
            given=repr(raw_bounds),
            index=index,
        )
    return Ok(
        ParameterSpec(
            name=name,
            type=ParameterType.BOOLEAN,
            unit_kind=unit_kind,
            default=default,
            ui=ui,
            bounds=None,
            step=None,
            hard_constraint=constraint,
        )
    )


def coerce_parameter_space(value: object) -> Result[tuple[ParameterSpec, ...]]:
    """Admit a sequence of declared variables, canonically ordered by name."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "parameter_space",
            "the declared parameter space is a sequence of variables",
            given=type(value).__name__,
        )
    resolved: list[ParameterSpec] = []
    seen: set[str] = set()
    for index, item in enumerate(cast("Sequence[object]", value)):
        spec = ParameterSpec.try_create(item, index=index)
        if is_refusal(spec):
            return spec
        if spec.value.name in seen:
            return invalid(
                "parameter_space",
                "parameter names are unique within the declared space",
                name=spec.value.name,
                index=index,
            )
        seen.add(spec.value.name)
        resolved.append(spec.value)
    resolved.sort(key=lambda spec: spec.name)
    return Ok(tuple(resolved))


def canonical_assignment_of(space: Sequence[ParameterSpec]) -> Mapping[str, object]:
    """Mandatory-default projection — one identity locus, not a declared field."""
    return MappingProxyType({spec.name: spec.assignment_value() for spec in space})
