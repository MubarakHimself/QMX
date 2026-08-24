"""DEC-0183 QML-aware config-compiler extensions (B-3).

When a run cites a CT-33 Bot definition, the compiler stamps
``assignment_is_canonical`` (mirroring ``seed_overridden``) and resolves each
producer template to one configured-producer fingerprint. Ungoverned
plain-Python bot cites skip this path — tunnel entry stays ungated (QL-1).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.exact import ExactRational
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.registry import RegistrationRecord
from qml.declaration.bot import BotDefinition
from qml.declaration.parameters import ParameterType
from qml.footprint.template import resolve_template
from qml.footprint.vocab import ProducerBindingForm
from qml.protocol.factory import resolve_assignment

from qmb._refuse import invalid

__all__ = [
    "ASSIGNMENT_IS_CANONICAL_KEY",
    "ASSIGNMENT_KEY",
    "RESOLVED_PRODUCERS_KEY",
    "Ct33CompileExtension",
    "apply_ct33_compiler_extensions",
    "ct33_from_record",
]

ASSIGNMENT_KEY: Final[str] = "assignment"
ASSIGNMENT_IS_CANONICAL_KEY: Final[str] = "assignment_is_canonical"
RESOLVED_PRODUCERS_KEY: Final[str] = "resolved_producers"


@dataclass(frozen=True, slots=True)
class Ct33CompileExtension:
    """Stamps and resolved producers for a CT-33-cited run (DEC-0183)."""

    assignment: Mapping[str, object]
    assignment_is_canonical: bool
    resolved_producers: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "assignment", MappingProxyType(dict(self.assignment)))


def ct33_from_record(record: object) -> Result[BotDefinition | None]:
    """Parse a CT-33 body when present; ungoverned cites yield ``None``.

    A stub ``bot-definition`` body without the six semantic groups is an
    ungoverned plain-Python cite — not a compile refusal.
    """
    if record is None:
        return Ok(None)
    if not isinstance(record, RegistrationRecord):
        return Ok(None)
    if not _looks_like_ct33(record.body):
        return Ok(None)
    parsed = BotDefinition.try_from_mapping(record.body)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value)


def apply_ct33_compiler_extensions(
    record: object,
    *,
    run_spec: Mapping[str, object],
    invocation_flags: Mapping[str, object],
) -> Result[Ct33CompileExtension | None]:
    """Stamp canonical-assignment and resolve producer templates (DEC-0183).

    ``None`` means the cite is ungoverned: the QL-7 / CT-33 path is not required.
    A non-canonical assignment is a run-spec override, never a governed-seat
    execution.
    """
    bot = ct33_from_record(record)
    if is_refusal(bot):
        return bot
    if bot.value is None:
        return Ok(None)
    definition = bot.value
    names = {spec.name for spec in definition.parameter_space}
    overlay = _overlay_assignment(names, run_spec)
    overlay.update(_overlay_assignment(names, invocation_flags))
    canonical = dict(definition.canonical_assignment())
    merged = dict(canonical)
    merged.update(overlay)
    checked = resolve_assignment(definition, merged)
    if is_refusal(checked):
        return checked
    resolved = dict(checked.value)
    canonical_stamp = _assignments_equal(resolved, canonical)
    producers = _resolve_producers(definition, resolved)
    if is_refusal(producers):
        return producers
    return Ok(
        Ct33CompileExtension(
            assignment=_plain_assignment(resolved),
            assignment_is_canonical=canonical_stamp,
            resolved_producers=producers.value,
        )
    )


def _looks_like_ct33(body: Mapping[str, object]) -> bool:
    nested = body.get("body")
    source: Mapping[str, object] = body
    if isinstance(nested, Mapping) and "strategy_family_id" not in body:
        source = cast("Mapping[str, object]", nested)
    return "strategy_family_id" in source and "footprint" in source


def _overlay_assignment(
    names: set[str],
    layer: Mapping[str, object],
) -> dict[str, object]:
    overlay: dict[str, object] = {}
    raw = layer.get(ASSIGNMENT_KEY)
    if isinstance(raw, Mapping):
        overlay.update(cast("Mapping[str, object]", raw))
    for name in names:
        if name in layer:
            overlay[name] = layer[name]
    return overlay


def _assignments_equal(
    resolved: Mapping[str, object],
    canonical: Mapping[str, object],
) -> bool:
    if set(resolved) != set(canonical):
        return False
    return all(_same_assigned(value, canonical[name]) for name, value in resolved.items())


def _same_assigned(left: object, right: object) -> bool:
    if isinstance(left, ExactRational) and isinstance(right, ExactRational):
        return left.fp1_identity() == right.fp1_identity()
    return left == right


def _plain_assignment(assignment: Mapping[str, object]) -> dict[str, object]:
    out: dict[str, object] = {}
    for name, value in assignment.items():
        identity = getattr(value, "fp1_identity", None)
        out[name] = identity() if callable(identity) else value
    return out


def _resolve_producers(
    definition: BotDefinition,
    assignment: Mapping[str, object],
) -> Result[tuple[str, ...]]:
    template_values = _template_assignment(definition, assignment)
    if is_refusal(template_values):
        return template_values
    fps: list[str] = []
    for binding in definition.footprint.producer_bindings:
        if binding.form is ProducerBindingForm.PINNED_FINGERPRINT:
            if binding.pinned is None:
                return invalid(
                    "producer_bindings",
                    "a pinned producer binding carries a configured-producer fp1",
                )
            fps.append(binding.pinned.value)
            continue
        if binding.form is ProducerBindingForm.TEMPLATE:
            if binding.template is None:
                return invalid(
                    "producer_bindings",
                    "a template producer binding carries a complete CT-16/CT-17 template",
                )
            resolved = resolve_template(binding.template, template_values.value)
            if is_refusal(resolved):
                return resolved
            stamped = resolved.value.fingerprint_content()
            if is_refusal(stamped):
                return stamped
            fps.append(stamped.value.value)
            continue
        return invalid(
            "producer_bindings",
            "a producer binding is pinned-fingerprint or template",
            given=binding.form.value,
        )
    return Ok(tuple(fps))


def _template_assignment(
    definition: BotDefinition,
    assignment: Mapping[str, object],
) -> Result[dict[str, ExactRational]]:
    specs = {spec.name: spec for spec in definition.parameter_space}
    out: dict[str, ExactRational] = {}
    for name, value in assignment.items():
        if isinstance(value, ExactRational):
            out[name] = value
            continue
        spec = specs.get(name)
        if spec is None:
            continue
        if (
            spec.type is ParameterType.EXACT_INTEGER
            and isinstance(value, int)
            and not isinstance(value, bool)
        ):
            coerced = ExactRational.try_create(value, 1, spec.unit_kind)
            if is_refusal(coerced):
                return coerced
            out[name] = coerced.value
    return Ok(out)
