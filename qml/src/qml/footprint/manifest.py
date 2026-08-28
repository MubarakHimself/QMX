"""Footprint manifest: nested stream set, calendars, producer bindings (QL-4).

The footprint is the single canonical consumption manifest. Hosts provide only
this declared footprint to bot logic. Completeness is the set-equality of the
footprint's producer-binding set with the transitive union of cited confluence
leg producers plus bot-direct producers (DEC-0174).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import cast

from qmf.core.chrono import CalendarIdentity
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_ok, is_refusal

from qml._refuse import clean_token, invalid, unavailable
from qml.footprint._coerce import (
    coerce_bar_spec,
    coerce_calendars,
    coerce_fingerprint,
    deep_freeze,
    fp1_clean,
)
from qml.footprint.template import ProducerTemplate
from qml.footprint.vocab import (
    BARSPEC_KINDS,
    CT16_FORMAT_VERSION,
    FORBIDDEN_HORIZON_FIELDS,
    ProducerBindingForm,
    StreamRole,
    coerce_enum,
    parse_binding_form,
)

__all__ = [
    "CompletenessReport",
    "Footprint",
    "ProducerBinding",
    "StreamMember",
    "compute_transitive_union",
    "mint_footprint",
    "report_completeness",
]


def _as_sequence(value: object, field: str) -> Result[tuple[object, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(field, "expected a sequence", given=type(value).__name__)
    return Ok(tuple(cast("Sequence[object]", value)))


@dataclass(frozen=True, slots=True)
class StreamMember:
    """One instrument-role + BarSpec list, trading vs data-only (B-12 nested in QL-4)."""

    instrument_role: str
    bar_specs: tuple[Mapping[str, object], ...]
    stream_role: StreamRole

    def __post_init__(self) -> None:
        frozen = tuple(cast("Mapping[str, object]", deep_freeze(item)) for item in self.bar_specs)
        object.__setattr__(self, "bar_specs", frozen)

    def fp1_identity(self) -> dict[str, object]:
        return {
            "instrument_role": self.instrument_role,
            "bar_specs": [dict(spec) for spec in self.bar_specs],
            "stream_role": self.stream_role.value,
        }

    @classmethod
    def try_create(
        cls,
        instrument_role: object,
        bar_specs: object,
        stream_role: object,
    ) -> Result[StreamMember]:
        role_name = clean_token(instrument_role)
        if role_name is None:
            return invalid(
                "instrument_role",
                "a stream member names a non-empty instrument-role token",
                given=repr(instrument_role),
            )
        role = coerce_enum(StreamRole, stream_role)
        if role is None:
            return invalid(
                "stream_role",
                "a stream role is trading or data-only (B-12)",
                given=repr(stream_role),
            )
        if isinstance(bar_specs, (str, bytes)) or not isinstance(bar_specs, Sequence):
            return invalid(
                "bar_specs",
                "a stream member carries a BarSpec list (B-12); never a bare timeframe",
                given=type(bar_specs).__name__,
            )
        specs: list[Mapping[str, object]] = []
        for index, item in enumerate(cast("Sequence[object]", bar_specs)):
            if isinstance(item, Mapping):
                mapping = cast("Mapping[str, object]", item)
                kind = mapping.get("kind")
                if kind in BARSPEC_KINDS:
                    content = dict(mapping)
                    refusal = fp1_clean(content, "bar_specs")
                    if refusal is not None:
                        return refusal
                    specs.append(MappingProxyType(content))
                    continue
            coerced = coerce_bar_spec(cast("object", item))
            if is_refusal(coerced):
                return invalid(
                    "bar_specs",
                    "each BarSpec is a canonical identity mapping or fp1 reference",
                    index=index,
                    cause=dict(coerced.context),
                )
            specs.append(MappingProxyType(coerced.value))
        if not specs:
            return invalid("bar_specs", "a stream member declares one or more BarSpecs")
        return Ok(cls(instrument_role=role_name, bar_specs=tuple(specs), stream_role=role))


@dataclass(frozen=True, slots=True)
class ProducerBinding:
    """A pinned CT-16/CT-17 fingerprint or a complete producer template (DEC-0174)."""

    form: ProducerBindingForm
    pinned: Fingerprint | None = None
    template: ProducerTemplate | None = None

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "form": self.form.value,
            "format_version": CT16_FORMAT_VERSION,
        }
        if self.form is ProducerBindingForm.PINNED_FINGERPRINT and self.pinned is not None:
            content["fingerprint"] = self.pinned.value
        elif self.form is ProducerBindingForm.TEMPLATE and self.template is not None:
            content["template"] = self.template.fp1_identity()
        return content

    def fingerprint_content(self) -> Result[Fingerprint]:
        return fingerprint(self)

    @classmethod
    def try_create(
        cls,
        value: object = None,
        *,
        form: object = None,
        fingerprint: object = None,
        template: object = None,
    ) -> Result[ProducerBinding]:
        if isinstance(value, cls):
            return Ok(value)
        if isinstance(value, ProducerTemplate):
            return Ok(cls(form=ProducerBindingForm.TEMPLATE, template=value))
        if isinstance(value, Fingerprint):
            return Ok(cls(form=ProducerBindingForm.PINNED_FINGERPRINT, pinned=value))
        payload: dict[str, object] = {}
        if isinstance(value, Mapping):
            payload.update(cast("Mapping[str, object]", value))
        if form is not None:
            payload["form"] = form
        if fingerprint is not None:
            payload["fingerprint"] = fingerprint
        if template is not None:
            payload["template"] = template
        if not payload and isinstance(value, str):
            payload["fingerprint"] = value
            payload["form"] = ProducerBindingForm.PINNED_FINGERPRINT.value
        resolved_form: Result[ProducerBindingForm]
        if "form" in payload:
            resolved_form = parse_binding_form(payload["form"])
        elif "template" in payload or "space_bound" in payload or "formula_id" in payload:
            resolved_form = Ok(ProducerBindingForm.TEMPLATE)
        elif "fingerprint" in payload:
            resolved_form = Ok(ProducerBindingForm.PINNED_FINGERPRINT)
        else:
            return invalid(
                "form",
                "a producer binding is pinned-fingerprint or template",
                given=repr(cast("object", value)),
            )
        if is_refusal(resolved_form):
            return resolved_form
        if resolved_form.value is ProducerBindingForm.PINNED_FINGERPRINT:
            raw_fp = payload.get("fingerprint")
            if raw_fp is None and isinstance(value, str):
                raw_fp = value
            pinned = coerce_fingerprint(raw_fp)
            if is_refusal(pinned):
                return pinned
            return Ok(cls(form=resolved_form.value, pinned=pinned.value))
        tmpl = ProducerTemplate.try_create(payload.get("template", payload))
        if is_refusal(tmpl):
            return tmpl
        return Ok(cls(form=resolved_form.value, template=tmpl.value))


def _binding_key(binding: ProducerBinding) -> Result[str]:
    fp = binding.fingerprint_content()
    if is_refusal(fp):
        return fp
    return Ok(fp.value.value)


@dataclass(frozen=True, slots=True)
class Footprint:
    """The single canonical consumption manifest (DEC-0174).

    Stream set is nested here — never a second top-level field. Warm-up/embargo
    horizon is derived from the resolved producer chain, never stored here.
    """

    stream_set: tuple[StreamMember, ...]
    required_calendars: tuple[CalendarIdentity, ...]
    producer_bindings: tuple[ProducerBinding, ...]

    def fp1_identity(self) -> dict[str, object]:
        return {
            "class": "footprint",
            "stream_set": [member.fp1_identity() for member in self.stream_set],
            "required_calendars": [cal.fp1_identity() for cal in self.required_calendars],
            "producer_bindings": [binding.fp1_identity() for binding in self.producer_bindings],
            "format_version": CT16_FORMAT_VERSION,
        }

    def fingerprint_content(self) -> Result[Fingerprint]:
        return fingerprint(self)

    def host_manifest(self) -> Mapping[str, object]:
        """The only evidence locus a host may feed to bot logic (DEC-0174)."""
        return MappingProxyType(self.fp1_identity())

    @classmethod
    def try_create(
        cls,
        stream_set: object,
        required_calendars: object,
        producer_bindings: object,
        **rejected: object,
    ) -> Result[Footprint]:
        forbidden = sorted(FORBIDDEN_HORIZON_FIELDS.intersection(rejected))
        if forbidden:
            return invalid(
                "horizon",
                "the warm-up/embargo horizon is derived at resolution from the resolved "
                "producer chain (AD-21/AD-22); there is no second, hand-declared window "
                "field on the declaration",
                forbidden=forbidden,
            )
        extra = sorted(set(rejected) - FORBIDDEN_HORIZON_FIELDS)
        if extra:
            return invalid(
                "footprint",
                "the footprint carries stream_set, required_calendars, and "
                "producer_bindings only; the stream set is nested here, never a "
                "second top-level field",
                extra=extra,
            )
        return cls._build(stream_set, required_calendars, producer_bindings)

    @classmethod
    def try_from_mapping(cls, payload: object) -> Result[Footprint]:
        if isinstance(payload, cls):
            return Ok(payload)
        if not isinstance(payload, Mapping):
            return invalid(
                "footprint",
                "a footprint is a mapping of stream_set, required_calendars, and producer_bindings",
                given=type(payload).__name__,
            )
        mapping = cast("Mapping[str, object]", payload)
        nested = mapping.get("footprint")
        if isinstance(nested, Mapping) and "stream_set" not in mapping:
            mapping = cast("Mapping[str, object]", nested)
        forbidden = sorted(FORBIDDEN_HORIZON_FIELDS.intersection(mapping))
        if forbidden:
            return invalid(
                "horizon",
                "the warm-up/embargo horizon is derived at resolution from the resolved "
                "producer chain (AD-21/AD-22); there is no second, hand-declared window "
                "field on the declaration",
                forbidden=forbidden,
            )
        # The closed set try_create enforces, plus the self-emitted serialization
        # envelope (``class``/``format_version`` from fp1_identity/host_manifest) so a
        # footprint's own canonical mapping round-trips; a genuinely foreign top-level
        # field is still refused.
        extra = sorted(
            set(mapping)
            - {"stream_set", "required_calendars", "producer_bindings"}
            - {"class", "format_version"}
            - FORBIDDEN_HORIZON_FIELDS
        )
        if extra:
            return invalid(
                "footprint",
                "the footprint carries stream_set, required_calendars, and "
                "producer_bindings only; the stream set is nested here, never a "
                "second top-level field",
                extra=extra,
            )
        if "stream_set" not in mapping:
            return invalid(
                "stream_set",
                "the stream set (instrument-role + BarSpec list, trading vs data-only) "
                "is nested inside the footprint, the one stream-set locus",
            )
        return cls._build(
            mapping.get("stream_set"),
            mapping.get("required_calendars", ()),
            mapping.get("producer_bindings", ()),
        )

    @classmethod
    def _build(
        cls,
        stream_set: object,
        required_calendars: object,
        producer_bindings: object,
    ) -> Result[Footprint]:
        streams = _coerce_stream_set(stream_set)
        if is_refusal(streams):
            return streams
        calendars = coerce_calendars(required_calendars)
        if is_refusal(calendars):
            return calendars
        bindings = _coerce_bindings(producer_bindings, "producer_bindings")
        if is_refusal(bindings):
            return bindings
        return Ok(
            cls(
                stream_set=streams.value,
                required_calendars=calendars.value,
                producer_bindings=bindings.value,
            )
        )


def mint_footprint(
    stream_set: object,
    required_calendars: object,
    producer_bindings: object,
) -> Result[Footprint]:
    """Mint the canonical consumption manifest. Horizon is not a field."""
    return Footprint.try_create(stream_set, required_calendars, producer_bindings)


def _coerce_stream_set(value: object) -> Result[tuple[StreamMember, ...]]:
    items = _as_sequence(value, "stream_set")
    if is_refusal(items):
        return invalid(
            "stream_set",
            "the stream set is an instrument-role + BarSpec list in B-12's shape, "
            "nested inside the footprint",
            given=type(value).__name__,
        )
    resolved: list[StreamMember] = []
    seen: set[str] = set()
    for index, item in enumerate(items.value):
        member: Result[StreamMember]
        if isinstance(item, StreamMember):
            member = Ok(item)
        elif isinstance(item, Mapping):
            mapping = cast("Mapping[str, object]", item)
            member = StreamMember.try_create(
                mapping.get("instrument_role"),
                mapping.get("bar_specs"),
                mapping.get("stream_role"),
            )
        else:
            return invalid(
                "stream_set",
                "each stream is instrument-role + BarSpec list + trading vs data-only",
                index=index,
                given=type(item).__name__,
            )
        if is_refusal(member):
            return member
        key = member.value.instrument_role
        if key in seen:
            return invalid(
                "stream_set",
                "instrument-role tokens are unique within the stream set",
                instrument_role=key,
            )
        seen.add(key)
        resolved.append(member.value)
    if not resolved:
        return invalid("stream_set", "a footprint declares one or more streams")
    return Ok(tuple(resolved))


def _coerce_bindings(value: object, field: str) -> Result[tuple[ProducerBinding, ...]]:
    items = _as_sequence(value, field)
    if is_refusal(items):
        return invalid(
            field, "producer bindings are a sequence of pinned fingerprints or templates"
        )
    resolved: list[ProducerBinding] = []
    for index, item in enumerate(items.value):
        binding = ProducerBinding.try_create(item)
        if is_refusal(binding):
            return invalid(
                field,
                "each producer binding is a pinned CT-16/CT-17 fingerprint or a complete "
                "template minus only space-bound values",
                index=index,
                cause=dict(binding.context),
            )
        resolved.append(binding.value)
    return Ok(tuple(resolved))


@dataclass(frozen=True, slots=True)
class CompletenessReport:
    """Whether the footprint producer-binding set equals the transitive union.

    Raw material the Epic 12 Layer-1 linter consumes: ``complete`` is set-equality;
    ``missing`` are union members absent from the footprint; ``extra`` are footprint
    members absent from the union.
    """

    complete: bool
    missing: tuple[str, ...]
    extra: tuple[str, ...]
    union: tuple[str, ...]
    footprint: tuple[str, ...]


def _leg_producer(leg: object) -> Result[ProducerBinding | None]:
    """Extract a producer binding from a confluence leg, if the leg carries one."""
    if isinstance(leg, (ProducerBinding, ProducerTemplate, Fingerprint)):
        binding = ProducerBinding.try_create(leg)
        if is_refusal(binding):
            return binding
        return Ok(binding.value)
    if isinstance(leg, Mapping):
        mapping = cast("Mapping[str, object]", leg)
        if "producer_binding" in mapping:
            binding = ProducerBinding.try_create(mapping["producer_binding"])
            if is_refusal(binding):
                return binding
            return Ok(binding.value)
        if (
            "form" in mapping
            or "fingerprint" in mapping
            or "template" in mapping
            or "formula_id" in mapping
        ):
            binding = ProducerBinding.try_create(mapping)
            if is_refusal(binding):
                return binding
            return Ok(binding.value)
        return Ok(None)
    if isinstance(leg, str):
        parsed = Fingerprint.try_create(leg)
        if is_ok(parsed):
            return Ok(
                ProducerBinding(form=ProducerBindingForm.PINNED_FINGERPRINT, pinned=parsed.value)
            )
        return Ok(None)
    return Ok(None)


def _leg_child_ref(leg: object) -> str | None:
    if isinstance(leg, Mapping):
        mapping = cast("Mapping[str, object]", leg)
        ref = mapping.get("confluence_ref", mapping.get("confluence_id"))
        token = clean_token(ref)
        if token is not None:
            return token
    if isinstance(leg, str) and is_refusal(Fingerprint.try_create(leg)):
        return leg
    return None


def _catalog_legs(catalog: object, confluence_id: str) -> Result[tuple[object, ...]]:
    if isinstance(catalog, Mapping):
        mapping = cast("Mapping[object, object]", catalog)
        if confluence_id not in mapping:
            return unavailable(
                "confluence_ref",
                "an unresolvable cited child confluence is an unavailable dependency",
                confluence_id=confluence_id,
                journal=True,
            )
        legs: object = mapping[confluence_id]
        if isinstance(legs, Mapping):
            nested = cast("Mapping[str, object]", legs)
            if "legs" not in nested:
                return invalid(
                    "catalog",
                    "each catalog mapping entry must carry a legs sequence",
                    confluence_id=confluence_id,
                )
            legs = nested["legs"]
        items = _as_sequence(legs, "legs")
        if is_refusal(items):
            return invalid(
                "catalog",
                "each catalog entry is a sequence of confluence legs",
                confluence_id=confluence_id,
            )
        return items
    return unavailable(
        "confluence_ref",
        "an unresolvable cited child confluence is an unavailable dependency",
        confluence_id=confluence_id,
        journal=True,
    )


def compute_transitive_union(
    confluence_legs: object,
    bot_direct: object = (),
    catalog: object = (),
) -> Result[tuple[ProducerBinding, ...]]:
    """Union of cited confluence-leg producers (transitively) plus bot-direct producers."""
    collected: list[ProducerBinding] = []
    seen_keys: set[str] = set()
    visiting: set[str] = set()

    def _add(binding: ProducerBinding) -> Result[None]:
        key = _binding_key(binding)
        if is_refusal(key):
            return key
        if key.value not in seen_keys:
            seen_keys.add(key.value)
            collected.append(binding)
        return Ok(None)

    def _walk_legs(legs: Sequence[object], *, via: str | None) -> Result[None]:
        for index, leg in enumerate(legs):
            binding = _leg_producer(leg)
            if is_refusal(binding):
                return binding
            if binding.value is not None:
                added = _add(binding.value)
                if is_refusal(added):
                    return added
            child = _leg_child_ref(leg)
            if child is None:
                continue
            if child in visiting:
                return invalid(
                    "confluence_ref",
                    "confluence composition must be acyclic",
                    confluence_id=child,
                    via=via,
                    index=index,
                )
            visiting.add(child)
            child_legs = _catalog_legs(catalog, child)
            if is_refusal(child_legs):
                return child_legs
            walked = _walk_legs(child_legs.value, via=child)
            visiting.discard(child)
            if is_refusal(walked):
                return walked
        return Ok(None)

    roots = _as_sequence(confluence_legs, "confluence_legs")
    if is_refusal(roots):
        return invalid(
            "confluence_legs",
            "cited confluence legs are a sequence of producer bindings and/or child cites",
            given=type(confluence_legs).__name__,
        )
    walked = _walk_legs(roots.value, via=None)
    if is_refusal(walked):
        return walked
    directs = _coerce_bindings(bot_direct, "bot_direct")
    if is_refusal(directs):
        return directs
    for binding in directs.value:
        added = _add(binding)
        if is_refusal(added):
            return added
    keyed: list[tuple[str, ProducerBinding]] = []
    for binding in collected:
        key = _binding_key(binding)
        if is_refusal(key):
            return key
        keyed.append((key.value, binding))
    keyed.sort(key=lambda pair: pair[0])
    return Ok(tuple(item[1] for item in keyed))


def report_completeness(
    footprint: object,
    confluence_legs: object = (),
    bot_direct: object = (),
    catalog: object = (),
) -> Result[CompletenessReport]:
    """Report whether the footprint producer-binding set equals the transitive union.

    Does not refuse an incomplete footprint — that is the Epic 12 Layer-1 linter's
    job. Malformed inputs still refuse as ``invalid input``.
    """
    if isinstance(footprint, Footprint):
        declared = Ok(footprint)
    else:
        declared = Footprint.try_from_mapping(footprint)
    if is_refusal(declared):
        return declared
    union = compute_transitive_union(confluence_legs, bot_direct=bot_direct, catalog=catalog)
    if is_refusal(union):
        return union
    footprint_keys: list[str] = []
    for binding in declared.value.producer_bindings:
        key = _binding_key(binding)
        if is_refusal(key):
            return key
        footprint_keys.append(key.value)
    union_keys: list[str] = []
    for binding in union.value:
        key = _binding_key(binding)
        if is_refusal(key):
            return key
        union_keys.append(key.value)
    footprint_set = frozenset(footprint_keys)
    union_set = frozenset(union_keys)
    missing = tuple(sorted(union_set - footprint_set))
    extra = tuple(sorted(footprint_set - union_set))
    return Ok(
        CompletenessReport(
            complete=not missing and not extra,
            missing=missing,
            extra=extra,
            union=tuple(sorted(union_set)),
            footprint=tuple(sorted(footprint_set)),
        )
    )
