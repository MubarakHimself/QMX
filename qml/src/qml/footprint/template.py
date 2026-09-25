"""Producer templates and total single-valued resolution (QL-4).

A template is a complete CT-16/CT-17 configuration minus only the space-bound
parameter values. Substituting those values is a total, single-valued function
producing one deterministic configured-producer fingerprint, so dedup lands on
ordinary CT-16/CT-17 producer fingerprints (DEC-0174).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import ExactRational
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qml._refuse import clean_token, invalid
from qml.footprint._coerce import (
    arithmetic_reference_identity,
    coerce_calendars,
    coerce_duration,
    coerce_inputs,
    coerce_modes,
    coerce_output_schema,
    coerce_parameters,
    declared_budget_identity,
    deep_freeze,
    emission_policy_identity,
    nonneg_int,
    positive_int,
)
from qml.footprint.vocab import (
    AD22_IDENTITY_FIELDS,
    CT16_FORMAT_VERSION,
    AlignmentPolicy,
    MissingValuePolicy,
    ProducerKind,
    coerce_enum,
)

__all__ = [
    "ProducerTemplate",
    "ResolvedProducer",
    "mint_producer_template",
    "resolve_template",
]


def _missing_identity_field(field: str) -> TypedRefusal:
    """Layer-1 registration refusal: an omitted AD-22 identity field is a defect."""
    return invalid(
        field,
        "a producer template is a complete CT-16/CT-17 configuration minus only the "
        "space-bound parameter values; an omitted AD-22 identity field is a Layer-1 "
        "registration refusal (a missing element is a contract defect)",
        layer=1,
        journal=True,
    )


def _space_bound_map(value: object) -> Result[dict[str, str]]:
    if value is None:
        return Ok({})
    if not isinstance(value, Mapping):
        return invalid(
            "space_bound",
            "space-bound parameters map producer parameter names onto named bot-space parameters",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, str] = {}
    for key, target in mapping.items():
        name = clean_token(key)
        bot_name = clean_token(target)
        if name is None or bot_name is None:
            return invalid(
                "space_bound",
                "each space-bound entry is a non-empty producer parameter name bound to "
                "a non-empty bot-space parameter name",
                key=repr(key),
                target=repr(target),
            )
        resolved[name] = bot_name
    return Ok(resolved)


def _confirmation_delay(value: object) -> Result[int | None]:
    """``None`` means omitted (embargo 0); ``'unbounded'`` is the declared exclusion."""
    candidate: object = value
    if candidate is None:
        return Ok(None)
    if candidate == "unbounded":
        return Ok(None)
    if isinstance(candidate, Mapping):
        mapping = cast("Mapping[str, object]", candidate)
        if mapping.get("confirmation_delay") == "unbounded":
            return Ok(None)
        bound_value: object = mapping.get("confirmation_delay_bound")
        if bound_value is None:
            return invalid(
                "confirmation_delay_bound",
                "the confirmation delay bound is a non-negative integer count of "
                "observations at the family's BarSpec, or the declared 'unbounded' exclusion",
                given="mapping",
            )
        candidate = bound_value
    bound = nonneg_int(candidate)
    if bound is None:
        return invalid(
            "confirmation_delay_bound",
            "the confirmation delay bound is a non-negative integer count of "
            "observations at the family's BarSpec, or the declared 'unbounded' exclusion",
            given=repr(candidate),
        )
    return Ok(bound)


@dataclass(frozen=True, slots=True)
class _TemplateIdentity:
    kind: ProducerKind
    formula: str
    version: int


@dataclass(frozen=True, slots=True)
class _TemplateShape:
    inputs: tuple[Mapping[str, object], ...]
    calendars: tuple[CalendarIdentity, ...]
    alignment: AlignmentPolicy
    missing_policy: MissingValuePolicy
    warm: int


@dataclass(frozen=True, slots=True)
class _TemplateSpace:
    schema: tuple[Mapping[str, object], ...]
    modes: tuple[str, ...]
    arithmetic: Mapping[str, object]
    space: dict[str, str]
    fixed: Mapping[str, ExactRational]


@dataclass(frozen=True, slots=True)
class _TemplateBounds:
    emission: Mapping[str, object] | None
    warm_up_time_bound: Mapping[str, object] | None
    budget: Mapping[str, object] | None
    delay: int | None
    unbounded: bool


def _template_identity(mapping: Mapping[str, object]) -> Result[_TemplateIdentity]:
    kind = coerce_enum(ProducerKind, mapping.get("producer_kind", ProducerKind.INDICATOR))
    if kind is None:
        return invalid(
            "producer_kind",
            "a producer template is indicator (CT-16) or structure (CT-17)",
            given=repr(mapping.get("producer_kind")),
        )
    formula = clean_token(mapping.get("formula_id"))
    if formula is None:
        return _missing_identity_field("formula_id")
    version = positive_int(mapping.get("contract_format_version"))
    if version is None:
        return invalid(
            "contract_format_version",
            "the per-configured-producer contract format version is a positive integer ordinal",
            given=repr(mapping.get("contract_format_version")),
            layer=1,
            journal=True,
        )
    return Ok(_TemplateIdentity(kind=kind, formula=formula, version=version))


def _template_shape(mapping: Mapping[str, object]) -> Result[_TemplateShape]:
    inputs = coerce_inputs(mapping.get("inputs"))
    if is_refusal(inputs):
        return inputs
    calendars = coerce_calendars(mapping.get("calendar_requirements"))
    if is_refusal(calendars):
        return calendars
    alignment = coerce_enum(AlignmentPolicy, mapping.get("alignment_policy"))
    if alignment is None:
        return invalid(
            "alignment_policy",
            "the alignment policy is one of the closed set; as-of is the only "
            "governed-evidence-legal value",
            given=repr(mapping.get("alignment_policy")),
            layer=1,
            journal=True,
        )
    missing_policy = coerce_enum(MissingValuePolicy, mapping.get("missing_value_policy"))
    if missing_policy is None:
        return invalid(
            "missing_value_policy",
            "the missing-value policy is one of the closed set; forward-fill and "
            "interpolation are never legal",
            given=repr(mapping.get("missing_value_policy")),
            layer=1,
            journal=True,
        )
    warm = nonneg_int(mapping.get("warm_up"))
    if warm is None:
        return invalid(
            "warm_up",
            "warm-up is a non-negative integer count of completed input observations, "
            "identical across modes (never ticks, never a Duration)",
            given=repr(mapping.get("warm_up")),
            layer=1,
            journal=True,
        )
    return Ok(
        _TemplateShape(
            inputs=inputs.value,
            calendars=calendars.value,
            alignment=alignment,
            missing_policy=missing_policy,
            warm=warm,
        )
    )


def _template_space(mapping: Mapping[str, object]) -> Result[_TemplateSpace]:
    schema = coerce_output_schema(mapping.get("output_schema"))
    if is_refusal(schema):
        return schema
    modes = coerce_modes(mapping.get("supported_modes"))
    if is_refusal(modes):
        return modes
    arithmetic = arithmetic_reference_identity(
        mapping.get("arithmetic_reference_configuration")
    )
    if is_refusal(arithmetic):
        return arithmetic
    space = _space_bound_map(mapping.get("space_bound"))
    if is_refusal(space):
        return space
    fixed = coerce_parameters(mapping.get("fixed_parameters", mapping.get("parameters")))
    if is_refusal(fixed):
        return fixed
    overlap = sorted(set(space.value).intersection(fixed.value))
    if overlap:
        return invalid(
            "space_bound",
            "a parameter is either fixed or space-bound, never both",
            overlap=overlap,
        )
    return Ok(
        _TemplateSpace(
            schema=schema.value,
            modes=modes.value,
            arithmetic=arithmetic.value,
            space=space.value,
            fixed=fixed.value,
        )
    )


def _template_bounds(mapping: Mapping[str, object]) -> Result[_TemplateBounds]:
    emission = _optional_emission(mapping)
    if is_refusal(emission):
        return emission
    bound_identity = _optional_warm_up_time_bound(mapping)
    if is_refusal(bound_identity):
        return bound_identity
    budget = _optional_declared_budget(mapping)
    if is_refusal(budget):
        return budget
    delay = _confirmation_delay(
        mapping.get("confirmation_delay_bound", mapping.get("confirmation_delay"))
    )
    if is_refusal(delay):
        return delay
    unbounded = mapping.get("confirmation_delay") == "unbounded" or (
        isinstance(mapping.get("confirmation_delay_bound"), str)
        and mapping.get("confirmation_delay_bound") == "unbounded"
    )
    return Ok(
        _TemplateBounds(
            emission=emission.value,
            warm_up_time_bound=bound_identity.value,
            budget=budget.value,
            delay=None if unbounded else delay.value,
            unbounded=unbounded,
        )
    )


def _optional_emission(mapping: Mapping[str, object]) -> Result[Mapping[str, object] | None]:
    if mapping.get("emission_policy") is None:
        return Ok(None)
    built = emission_policy_identity(mapping["emission_policy"])
    if is_refusal(built):
        return built
    return Ok(built.value)


def _optional_warm_up_time_bound(
    mapping: Mapping[str, object],
) -> Result[Mapping[str, object] | None]:
    if mapping.get("warm_up_time_bound") is None:
        return Ok(None)
    duration = coerce_duration(mapping["warm_up_time_bound"])
    if is_refusal(duration):
        return duration
    return Ok(duration.value.fp1_identity())


def _optional_declared_budget(
    mapping: Mapping[str, object],
) -> Result[Mapping[str, object] | None]:
    if mapping.get("declared_budget") is None:
        return Ok(None)
    built_budget = declared_budget_identity(mapping["declared_budget"])
    if is_refusal(built_budget):
        return built_budget
    return Ok(built_budget.value)


@dataclass(frozen=True, slots=True)
class ProducerTemplate:
    """A complete CT-16/CT-17 configuration minus only space-bound parameter values."""

    producer_kind: ProducerKind
    formula_id: str
    contract_format_version: int
    inputs: tuple[Mapping[str, object], ...]
    calendar_requirements: tuple[CalendarIdentity, ...]
    alignment_policy: AlignmentPolicy
    missing_value_policy: MissingValuePolicy
    warm_up: int
    output_schema: tuple[Mapping[str, object], ...]
    supported_modes: tuple[str, ...]
    arithmetic_reference_configuration: Mapping[str, object]
    space_bound: Mapping[str, str]
    fixed_parameters: Mapping[str, ExactRational]
    emission_policy: Mapping[str, object] | None = None
    warm_up_time_bound: Mapping[str, object] | None = None
    declared_budget: Mapping[str, object] | None = None
    confirmation_delay_bound: int | None = None
    confirmation_delay_unbounded: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "inputs", tuple(deep_freeze(item) for item in self.inputs))
        object.__setattr__(
            self, "output_schema", tuple(deep_freeze(item) for item in self.output_schema)
        )
        object.__setattr__(
            self,
            "arithmetic_reference_configuration",
            deep_freeze(self.arithmetic_reference_configuration),
        )
        object.__setattr__(self, "space_bound", MappingProxyType(dict(self.space_bound)))
        object.__setattr__(self, "fixed_parameters", MappingProxyType(dict(self.fixed_parameters)))
        if self.emission_policy is not None:
            object.__setattr__(self, "emission_policy", deep_freeze(self.emission_policy))
        if self.warm_up_time_bound is not None:
            object.__setattr__(self, "warm_up_time_bound", deep_freeze(self.warm_up_time_bound))
        if self.declared_budget is not None:
            object.__setattr__(self, "declared_budget", deep_freeze(self.declared_budget))

    def fp1_identity(self) -> dict[str, object]:
        """Template identity — space-bound *names*, never assignment values."""
        content: dict[str, object] = {
            "class": "producer-template",
            "producer_kind": self.producer_kind.value,
            "formula_id": self.formula_id,
            "contract_format_version": self.contract_format_version,
            "inputs": [dict(item) for item in self.inputs],
            "calendar_requirements": [cal.fp1_identity() for cal in self.calendar_requirements],
            "alignment_policy": self.alignment_policy.value,
            "missing_value_policy": self.missing_value_policy.value,
            "warm_up": self.warm_up,
            "output_schema": [dict(item) for item in self.output_schema],
            "supported_modes": list(self.supported_modes),
            "arithmetic_reference_configuration": dict(self.arithmetic_reference_configuration),
            "space_bound": dict(self.space_bound),
            "format_version": CT16_FORMAT_VERSION,
        }
        if self.fixed_parameters:
            content["fixed_parameters"] = {
                name: param.fp1_identity() for name, param in self.fixed_parameters.items()
            }
        if self.emission_policy is not None:
            content["emission_policy"] = dict(self.emission_policy)
        if self.warm_up_time_bound is not None:
            content["warm_up_time_bound"] = dict(self.warm_up_time_bound)
        if self.declared_budget is not None:
            content["declared_budget"] = dict(self.declared_budget)
        if self.confirmation_delay_unbounded:
            content["confirmation_delay"] = "unbounded"
        elif self.confirmation_delay_bound is not None:
            content["confirmation_delay_bound"] = self.confirmation_delay_bound
        return content

    def fingerprint_content(self) -> Result[Fingerprint]:
        """``fp1`` over the template (not the resolved producer), via qmf-core only."""
        return fingerprint(self)

    @classmethod
    def try_create(cls, payload: object = None, **fields: object) -> Result[ProducerTemplate]:
        """Validate a complete template minus only space-bound values, value-or-refusal."""
        mapping: dict[str, object] = {}
        if payload is not None:
            if isinstance(payload, cls):
                return Ok(payload)
            if not isinstance(payload, Mapping):
                return invalid(
                    "template",
                    "a producer template is a mapping of AD-22 identity fields plus "
                    "space-bound parameter names",
                    given=type(payload).__name__,
                )
            mapping.update(cast("Mapping[str, object]", payload))
        mapping.update(fields)
        nested = mapping.get("template")
        if isinstance(nested, Mapping) and "formula_id" not in mapping:
            mapping = {**cast("Mapping[str, object]", nested), **fields}
        missing = [name for name in AD22_IDENTITY_FIELDS if name not in mapping]
        if missing:
            return _missing_identity_field(missing[0])
        return cls._from_complete(mapping)

    @classmethod
    def _from_complete(cls, mapping: Mapping[str, object]) -> Result[ProducerTemplate]:
        identity = _template_identity(mapping)
        if is_refusal(identity):
            return identity
        shape = _template_shape(mapping)
        if is_refusal(shape):
            return shape
        space = _template_space(mapping)
        if is_refusal(space):
            return space
        bounds = _template_bounds(mapping)
        if is_refusal(bounds):
            return bounds
        return Ok(
            cls(
                producer_kind=identity.value.kind,
                formula_id=identity.value.formula,
                contract_format_version=identity.value.version,
                inputs=shape.value.inputs,
                calendar_requirements=shape.value.calendars,
                alignment_policy=shape.value.alignment,
                missing_value_policy=shape.value.missing_policy,
                warm_up=shape.value.warm,
                output_schema=space.value.schema,
                supported_modes=space.value.modes,
                arithmetic_reference_configuration=space.value.arithmetic,
                space_bound=space.value.space,
                fixed_parameters=space.value.fixed,
                emission_policy=bounds.value.emission,
                warm_up_time_bound=bounds.value.warm_up_time_bound,
                declared_budget=bounds.value.budget,
                confirmation_delay_bound=bounds.value.delay,
                confirmation_delay_unbounded=bounds.value.unbounded,
            )
        )


def mint_producer_template(payload: object = None, **fields: object) -> Result[ProducerTemplate]:
    """Mint a producer template (complete configuration minus space-bound values)."""
    return ProducerTemplate.try_create(payload, **fields)


@dataclass(frozen=True, slots=True)
class ResolvedProducer:
    """A fully-bound CT-16/CT-17 configured producer whose ``fp1`` is its identity."""

    producer_kind: ProducerKind
    formula_id: str
    contract_format_version: int
    parameters: Mapping[str, ExactRational]
    inputs: tuple[Mapping[str, object], ...]
    calendar_requirements: tuple[CalendarIdentity, ...]
    alignment_policy: AlignmentPolicy
    missing_value_policy: MissingValuePolicy
    warm_up: int
    output_schema: tuple[Mapping[str, object], ...]
    supported_modes: tuple[str, ...]
    arithmetic_reference_configuration: Mapping[str, object]
    emission_policy: Mapping[str, object] | None = None
    warm_up_time_bound: Mapping[str, object] | None = None
    declared_budget: Mapping[str, object] | None = None
    confirmation_delay_bound: int | None = None
    confirmation_delay_unbounded: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))
        object.__setattr__(self, "inputs", tuple(deep_freeze(item) for item in self.inputs))
        object.__setattr__(
            self, "output_schema", tuple(deep_freeze(item) for item in self.output_schema)
        )
        object.__setattr__(
            self,
            "arithmetic_reference_configuration",
            deep_freeze(self.arithmetic_reference_configuration),
        )

    def fp1_identity(self) -> dict[str, object]:
        """Configured-producer identity — the entire declared configuration (AD-22)."""
        producer_class = (
            "configured-indicator"
            if self.producer_kind is ProducerKind.INDICATOR
            else "configured-structure"
        )
        content: dict[str, object] = {
            "class": producer_class,
            "formula_id": self.formula_id,
            "contract_format_version": self.contract_format_version,
            "parameters": {name: param.fp1_identity() for name, param in self.parameters.items()},
            "inputs": [dict(item) for item in self.inputs],
            "calendar_requirements": [cal.fp1_identity() for cal in self.calendar_requirements],
            "alignment_policy": self.alignment_policy.value,
            "missing_value_policy": self.missing_value_policy.value,
            "warm_up": self.warm_up,
            "output_schema": [dict(item) for item in self.output_schema],
            "supported_modes": list(self.supported_modes),
            "arithmetic_reference_configuration": dict(self.arithmetic_reference_configuration),
            "format_version": CT16_FORMAT_VERSION,
        }
        if self.emission_policy is not None:
            content["emission_policy"] = dict(self.emission_policy)
        if self.warm_up_time_bound is not None:
            content["warm_up_time_bound"] = dict(self.warm_up_time_bound)
        if self.declared_budget is not None:
            content["declared_budget"] = dict(self.declared_budget)
        if self.producer_kind is ProducerKind.STRUCTURE:
            if self.confirmation_delay_unbounded:
                content["confirmation_delay"] = "unbounded"
            elif self.confirmation_delay_bound is not None:
                content["confirmation_delay_bound"] = self.confirmation_delay_bound
        return content

    def fingerprint_content(self) -> Result[Fingerprint]:
        """The configured-producer ``fp1`` — ordinary CT-16/CT-17 dedup identity."""
        return fingerprint(self)

    def upstream_fingerprints(self) -> tuple[str, ...]:
        """Upstream configured-producer fps cited by derived inputs, declared order."""
        found: list[str] = []
        for item in self.inputs:
            upstream = item.get("upstream_fingerprint")
            if isinstance(upstream, str):
                found.append(upstream)
        return tuple(found)


def resolve_template(template: object, assignment: object = None) -> Result[ResolvedProducer]:
    """Substitute space-bound values: a total, single-valued function (DEC-0174).

    Every space-bound producer parameter is replaced by the named bot-space value.
    The same complete assignment always yields one fingerprint; assignment-key
    insertion order never forks identity. Extra assignment keys are ignored.
    """
    built = ProducerTemplate.try_create(template)
    if is_refusal(built):
        return built
    tmpl = built.value
    values = coerce_parameters({} if assignment is None else assignment)
    if is_refusal(values):
        return values
    assigned = values.value
    bound: dict[str, ExactRational] = dict(tmpl.fixed_parameters)
    for producer_name, bot_name in tmpl.space_bound.items():
        if bot_name not in assigned:
            return invalid(
                "assignment",
                "template resolution is total: every space-bound producer parameter "
                "must be substituted from the bot-space assignment",
                producer_parameter=producer_name,
                bot_space_parameter=bot_name,
            )
        bound[producer_name] = assigned[bot_name]
    return Ok(
        ResolvedProducer(
            producer_kind=tmpl.producer_kind,
            formula_id=tmpl.formula_id,
            contract_format_version=tmpl.contract_format_version,
            parameters=bound,
            inputs=tmpl.inputs,
            calendar_requirements=tmpl.calendar_requirements,
            alignment_policy=tmpl.alignment_policy,
            missing_value_policy=tmpl.missing_value_policy,
            warm_up=tmpl.warm_up,
            output_schema=tmpl.output_schema,
            supported_modes=tmpl.supported_modes,
            arithmetic_reference_configuration=tmpl.arithmetic_reference_configuration,
            emission_policy=tmpl.emission_policy,
            warm_up_time_bound=tmpl.warm_up_time_bound,
            declared_budget=tmpl.declared_budget,
            confirmation_delay_bound=tmpl.confirmation_delay_bound,
            confirmation_delay_unbounded=tmpl.confirmation_delay_unbounded,
        )
    )
