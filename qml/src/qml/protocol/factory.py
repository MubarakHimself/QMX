"""Bot factory: declaration + assignment + read surfaces -> host-driven callback.

A conformant bot is a factory the host constructs with (declaration, resolved
assignment, injected read surfaces), returning a callback the host drives per
evaluation instant (DEC-0177). No Book module, clock, or venue command surface
is ever injected.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Final, cast

from qmf.core.chrono import Clock, Instant
from qmf.core.exact import ExactRational
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qml._refuse import invalid
from qml.protocol.contract import (
    PROTOCOL_FORMAT_VERSION,
    coerce_protocol_format_version,
)
from qml.protocol.evidence import (
    FORBIDDEN_EVIDENCE_KEYS,
    FootprintEvidence,
    collect_evidence,
    declared_evidence_keys,
)
from qml.protocol.intents import BotIntent, accept_intents

if TYPE_CHECKING:
    from qml.declaration.bot import BotDefinition
    from qml.declaration.parameters import ParameterSpec

__all__ = [
    "FunctionFactory",
    "HostedBot",
    "construct_bot",
    "resolve_assignment",
]

_EMPTY: Final[Mapping[str, object]] = MappingProxyType({})


def _unwrap_ok(raw: object) -> object:
    if isinstance(raw, Ok):
        return cast("Ok[object]", raw).value
    return raw


def resolve_assignment(declaration: object, assignment: object) -> Result[Mapping[str, object]]:
    """Validate a host-resolved assignment against the declaration's parameter space."""
    bot = _as_bot_definition(declaration)
    if is_refusal(bot):
        return bot
    space = bot.value.parameter_space
    if assignment is None:
        if space:
            return invalid(
                "assignment",
                "a resolved assignment maps every declared parameter name to a value",
            )
        return Ok(_EMPTY)
    if not isinstance(assignment, Mapping):
        return invalid(
            "assignment",
            "a resolved assignment is a mapping of declared parameter name to value",
            given=type(assignment).__name__,
        )
    mapping = cast("Mapping[str, object]", assignment)
    names = {spec.name: spec for spec in space}
    extra = sorted(set(mapping) - set(names))
    missing = sorted(set(names) - set(mapping))
    if extra:
        return invalid(
            "assignment",
            "a resolved assignment carries only declared parameter names",
            extra=tuple(extra),
        )
    if missing:
        return invalid(
            "assignment",
            "a resolved assignment supplies every declared parameter",
            missing=tuple(missing),
        )
    resolved: dict[str, object] = {}
    for name, spec in names.items():
        checked = _check_assigned(spec, mapping[name])
        if is_refusal(checked):
            return checked
        resolved[name] = mapping[name]
    return Ok(MappingProxyType(resolved))


def _check_assigned(spec: ParameterSpec, value: object) -> Result[None]:
    from qml.declaration.parameters import ParameterType  # noqa: PLC0415

    if spec.type is ParameterType.EXACT_INTEGER:
        if isinstance(value, bool) or not isinstance(value, int):
            return invalid(
                "assignment",
                "an exact-integer assignment is a scaled integer; a binary float is refused",
                name=spec.name,
                given=repr(value),
            )
        return _int_in_bounds(spec, value)
    if spec.type is ParameterType.EXACT_RATIONAL:
        if not isinstance(value, ExactRational):
            return invalid(
                "assignment",
                "an exact-rational assignment is an ExactRational (AD-7)",
                name=spec.name,
                given=repr(value),
            )
        if value.unit_kind is not spec.unit_kind:
            return invalid(
                "assignment",
                "the assignment's unit-kind must match the declared parameter unit-kind",
                name=spec.name,
                given=value.unit_kind.value,
                unit_kind=spec.unit_kind.value,
            )
        return _rational_in_bounds(spec, value)
    if spec.type is ParameterType.CATEGORICAL:
        if not isinstance(value, str) or spec.bounds is None or value not in spec.bounds:
            return invalid(
                "assignment",
                "a categorical assignment is one of the declared options",
                name=spec.name,
                given=repr(value),
            )
        return Ok(None)
    if spec.type is ParameterType.BOOLEAN:
        if not isinstance(value, bool):
            return invalid(
                "assignment",
                "a boolean assignment is true or false",
                name=spec.name,
                given=repr(value),
            )
        return Ok(None)
    return invalid("assignment", "unknown parameter type", name=spec.name)


def _int_in_bounds(spec: ParameterSpec, value: int) -> Result[None]:
    bounds = spec.bounds
    if bounds is None or len(bounds) != 2:
        return Ok(None)
    low = bounds[0]
    high = bounds[1]
    if not isinstance(low, int) or not isinstance(high, int):
        return Ok(None)
    if value < low or value > high:
        return invalid(
            "assignment",
            "the assigned value must lie within the declared bounds",
            name=spec.name,
            given=value,
            min=low,
            max=high,
        )
    step = spec.step
    if isinstance(step, int) and step >= 1 and (value - low) % step != 0:
        return invalid(
            "assignment",
            "the assigned value must land on the declared step grid",
            name=spec.name,
            given=value,
            min=low,
            step=step,
        )
    return Ok(None)


def _rational_in_bounds(spec: ParameterSpec, value: ExactRational) -> Result[None]:
    bounds = spec.bounds
    if bounds is None or len(bounds) != 2:
        return Ok(None)
    low, high = bounds
    if not isinstance(low, ExactRational) or not isinstance(high, ExactRational):
        return Ok(None)
    quantity = value.as_fraction()
    if quantity < low.as_fraction() or quantity > high.as_fraction():
        return invalid(
            "assignment",
            "the assigned value must lie within the declared bounds",
            name=spec.name,
        )
    step = spec.step
    if isinstance(step, ExactRational) and step.as_fraction() > 0:
        offset = quantity - low.as_fraction()
        if (offset / step.as_fraction()).denominator != 1:
            return invalid(
                "assignment",
                "the assigned value must land on the declared step grid",
                name=spec.name,
            )
    return Ok(None)


def construct_bot(
    factory: object,
    *,
    declaration: object,
    assignment: object,
    read_surfaces: object,
    protocol_format_version: object = PROTOCOL_FORMAT_VERSION,
) -> Result[HostedBot]:
    """Construct the host-driven callback from declaration, assignment, and surfaces."""
    version = coerce_protocol_format_version(protocol_format_version)
    if is_refusal(version):
        return version
    bot = _as_bot_definition(declaration)
    if is_refusal(bot):
        return bot
    resolved = resolve_assignment(bot.value, assignment)
    if is_refusal(resolved):
        return resolved
    keys = declared_evidence_keys(bot.value.footprint)
    if is_refusal(keys):
        return keys
    surfaces = _coerce_surfaces(read_surfaces, keys.value)
    if is_refusal(surfaces):
        return surfaces
    definition = bot.value
    callback = _invoke_factory(
        factory,
        declaration=definition,
        assignment=resolved.value,
        read_surfaces=surfaces.value,
    )
    if is_refusal(callback):
        return callback
    return Ok(
        HostedBot(
            protocol_format_version=version.value,
            declaration=definition,
            assignment=resolved.value,
            _surfaces=surfaces.value,
            _logic=callback.value,
            _declared_keys=keys.value,
            _permitted_exits=tuple(definition.permitted_exit_intents),
        )
    )


def _as_bot_definition(value: object) -> Result[BotDefinition]:
    from qml.declaration.bot import BotDefinition  # noqa: PLC0415

    if isinstance(value, BotDefinition):
        return Ok(value)
    return BotDefinition.try_from_mapping(value)


def _invoke_factory(
    factory: object,
    *,
    declaration: object,
    assignment: Mapping[str, object],
    read_surfaces: Mapping[str, object],
) -> Result[object]:
    construct = getattr(factory, "construct", None)
    raw: object
    if callable(construct):
        raw = construct(
            declaration=declaration,
            assignment=assignment,
            read_surfaces=read_surfaces,
        )
    elif callable(factory):
        raw = factory(
            declaration=declaration,
            assignment=assignment,
            read_surfaces=read_surfaces,
        )
    else:
        return invalid(
            "factory",
            "a conformant bot is a factory taking (declaration, resolved assignment, "
            "injected read surfaces) and returning a callback",
            given=type(factory).__name__,
        )
    if isinstance(raw, TypedRefusal):
        return raw
    callback = _unwrap_ok(raw)
    on_instant = getattr(callback, "on_instant", None)
    if not callable(on_instant):
        return invalid(
            "callback",
            "the factory returns a callback the host drives per evaluation instant",
            given=type(callback).__name__,
        )
    return Ok(callback)


def _coerce_surfaces(value: object, declared: frozenset[str]) -> Result[Mapping[str, object]]:
    if value is None:
        return Ok(_EMPTY)
    if not isinstance(value, Mapping):
        return invalid(
            "read_surfaces",
            "hosts inject a mapping of declared-footprint key to ReadSurface",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, object] = {}
    extra: list[str] = []
    for raw_key, surface in mapping.items():
        if not isinstance(raw_key, str) or raw_key.strip() == "":
            return invalid(
                "read_surfaces",
                "read-surface keys are declared footprint tokens",
                given=repr(raw_key),
            )
        if raw_key in FORBIDDEN_EVIDENCE_KEYS:
            return invalid(
                "read_surfaces",
                "no Book module, clock, or sizing surface is ever injected into bot logic",
                key=raw_key,
            )
        if raw_key not in declared:
            extra.append(raw_key)
            continue
        if isinstance(surface, Clock):
            return invalid(
                "read_surfaces",
                "the evaluation instant rides the callback; no Clock access below the host",
                key=raw_key,
            )
        resolved[raw_key] = surface
    if extra:
        return invalid(
            "read_surfaces",
            "hosts inject only the declared footprint's read surfaces",
            extra=tuple(sorted(extra)),
        )
    return Ok(MappingProxyType(resolved))


@dataclass(frozen=True, slots=True)
class HostedBot:
    """Host-facing callback: driven per evaluation instant (DEC-0177).

    Collects declared-footprint evidence from injected read surfaces, hands it to
    author logic, and admits zero-or-more CT-23 intents through the door. Never
    derives a full-loss price and never injects a Book module.
    """

    protocol_format_version: int
    declaration: object
    assignment: Mapping[str, object]
    _surfaces: Mapping[str, object]
    _logic: object
    _declared_keys: frozenset[str]
    _permitted_exits: tuple[str, ...]

    def on_instant(self, instant: object, /) -> Result[tuple[BotIntent, ...]]:
        """Host drive: evaluation instant in, zero-or-more CT-23 intents out."""
        if not isinstance(instant, Instant):
            return invalid(
                "instant",
                "the evaluation instant rides the callback; bots never read a clock",
                given=repr(instant),
            )
        evidence = collect_evidence(self._surfaces, instant, declared_keys=self._declared_keys)
        if is_refusal(evidence):
            return evidence
        on_instant = getattr(self._logic, "on_instant", None)
        if not callable(on_instant):
            return invalid(
                "callback",
                "the factory returns a callback the host drives per evaluation instant",
                given=type(self._logic).__name__,
            )
        raw = on_instant(evidence.value)
        return accept_intents(
            raw,
            permitted_exit_intents=self._permitted_exits,
            protocol_format_version=self.protocol_format_version,
        )


@dataclass(frozen=True, slots=True)
class FunctionFactory:
    """Author helper: wrap a pure ``(evidence) -> intents`` function as a factory."""

    logic: Callable[[FootprintEvidence], object]

    def construct(
        self,
        *,
        declaration: object,
        assignment: Mapping[str, object],
        read_surfaces: Mapping[str, object],
    ) -> Result[_FunctionCallback]:
        del read_surfaces
        return Ok(
            _FunctionCallback(
                logic=self.logic,
                declaration=declaration,
                assignment=MappingProxyType(dict(assignment)),
            )
        )


@dataclass(frozen=True, slots=True)
class _FunctionCallback:
    logic: Callable[[FootprintEvidence], object]
    declaration: object
    assignment: Mapping[str, object]

    def on_instant(self, evidence: FootprintEvidence, /) -> object:
        return self.logic(evidence)
