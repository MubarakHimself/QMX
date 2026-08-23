"""Private coercion helpers for footprint identity content."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType
from typing import cast

from qmf.core.chrono import CalendarIdentity, Duration
from qmf.core.exact import ExactRational
from qmf.core.fingerprint import Fingerprint, canonical_bytes
from qmf.core.identity import Instrument
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal

from qml._refuse import clean_token, invalid
from qml.footprint.vocab import (
    BARSPEC_KINDS,
    CT16_FORMAT_VERSION,
    ChannelKind,
    EmissionTiming,
    OutputArity,
    QuoteSide,
    SupportedMode,
    coerce_enum,
)

__all__ = [
    "arithmetic_reference_identity",
    "coerce_bar_spec",
    "coerce_calendar",
    "coerce_calendars",
    "coerce_duration",
    "coerce_exact_rational",
    "coerce_fingerprint",
    "coerce_input",
    "coerce_inputs",
    "coerce_modes",
    "coerce_output_channel",
    "coerce_output_schema",
    "coerce_parameters",
    "declared_budget_identity",
    "deep_freeze",
    "emission_policy_identity",
    "fp1_clean",
    "nonneg_int",
    "positive_int",
]


def deep_freeze(value: object) -> object:
    """Recursively snapshot ``value`` into a shared-safe, read-only form."""
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return MappingProxyType({key: deep_freeze(item) for key, item in mapping.items()})
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return tuple(deep_freeze(item) for item in sequence)
    return value


def fp1_clean(content: object, field: str) -> TypedRefusal | None:
    """Refuse if ``content`` is not fp1-clean identity content."""
    serialized = canonical_bytes(content)
    if is_refusal(serialized):
        return invalid(
            field,
            "the value is not fp1-clean identity content; a binary float, a null, a "
            "non-string key, or an unsupported type is refused (DEC-0108)",
            cause=dict(serialized.context),
        )
    return None


def positive_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def nonneg_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def coerce_fingerprint(value: object) -> Result[Fingerprint]:
    if isinstance(value, Fingerprint):
        return Ok(value)
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed
    return invalid(
        "fingerprint",
        "a pinned producer fingerprint is fp1:sha256:<hex>, computed by qmf-core",
        given=repr(value),
    )


def coerce_exact_rational(value: object, *, field: str) -> Result[ExactRational]:
    """Admit an ExactRational or a {num, den, unit_kind} mapping; refuse a float."""
    if isinstance(value, ExactRational):
        return Ok(value)
    if isinstance(value, float):
        return invalid(
            field,
            "a parameter expressed as a binary float is refused; parameters are exact "
            "rationals only (DEC-0105)",
            given=repr(value),
        )
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        num = mapping.get("num", mapping.get("numerator"))
        den = mapping.get("den", mapping.get("denominator", 1))
        kind = mapping.get("unit_kind")
        built = ExactRational.try_create(num, den, kind)
        if is_refusal(built):
            return invalid(
                field,
                "each parameter is an ExactRational (num/den + AD-40 unit-kind)",
                cause=dict(built.context),
            )
        return built
    return invalid(
        field,
        "each parameter is an ExactRational or a num/den/unit_kind mapping",
        given=type(value).__name__,
    )


def coerce_parameters(value: object) -> Result[dict[str, ExactRational]]:
    if value is None:
        return Ok({})
    if not isinstance(value, Mapping):
        return invalid(
            "parameters",
            "parameters are a name->ExactRational mapping (exact rationals only)",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, ExactRational] = {}
    for key, param in mapping.items():
        name = clean_token(key)
        if name is None:
            return invalid("parameters", "each parameter name is a non-empty string", key=repr(key))
        coerced = coerce_exact_rational(param, field="parameters")
        if is_refusal(coerced):
            return invalid(
                "parameters",
                "each parameter is an ExactRational; a binary float never enters identity",
                parameter=name,
                cause=dict(coerced.context),
            )
        resolved[name] = coerced.value
    return Ok(resolved)


def coerce_calendar(value: object) -> Result[CalendarIdentity]:
    if isinstance(value, CalendarIdentity):
        return Ok(value)
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        built = CalendarIdentity.try_create(
            mapping.get("rule_set"),
            mapping.get("rule_set_version"),
            mapping.get("tzdata_version"),
        )
        if is_refusal(built):
            return invalid(
                "calendar_requirements",
                "each calendar requirement is a CalendarIdentity (rule set + version + "
                "tzdata version per AD-8)",
                cause=dict(built.context),
            )
        return built
    return invalid(
        "calendar_requirements",
        "each calendar requirement is a CalendarIdentity (rule set + version + tzdata version)",
        given=type(value).__name__,
    )


def coerce_calendars(value: object) -> Result[tuple[CalendarIdentity, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "calendar_requirements",
            "calendar requirements are a sequence of CalendarIdentity values",
            given=repr(value),
        )
    resolved: dict[tuple[str, str, str], CalendarIdentity] = {}
    for index, item in enumerate(cast("Sequence[object]", value)):
        calendar = coerce_calendar(item)
        if is_refusal(calendar):
            return invalid(
                "calendar_requirements",
                "each calendar requirement is a CalendarIdentity (rule set + version + "
                "tzdata version)",
                index=index,
                cause=dict(calendar.context),
            )
        ident = calendar.value
        resolved[(ident.rule_set, ident.rule_set_version, ident.tzdata_version)] = ident
    return Ok(tuple(resolved[key] for key in sorted(resolved)))


def coerce_bar_spec(value: object) -> Result[dict[str, object]]:
    """Normalize a BarSpec identity reference to the CT-16 series-input fragment."""
    if isinstance(value, Fingerprint):
        ref: dict[str, object] = {"kind": "fingerprint-ref", "ref": value.value}
        return Ok(ref)
    if isinstance(value, str):
        parsed = Fingerprint.try_create(value)
        if is_ok(parsed):
            parsed_ref: dict[str, object] = {
                "kind": "fingerprint-ref",
                "ref": parsed.value.value,
            }
            return Ok(parsed_ref)
        return invalid(
            "bar_spec",
            "a string bar-spec reference must be an fp1:sha256:<hex> fingerprint, or "
            "pass a canonical identity mapping (the BarSpec type is a qmf-core noun)",
            given=repr(value),
        )
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        if mapping.get("kind") == "fingerprint-ref" and isinstance(mapping.get("ref"), str):
            refusal = fp1_clean(dict(mapping), "bar_spec")
            if refusal is not None:
                return refusal
            copied: dict[str, object] = dict(mapping)
            return Ok(copied)
        if mapping.get("kind") == "identity-content" and isinstance(
            mapping.get("content"), Mapping
        ):
            refusal = fp1_clean(dict(mapping), "bar_spec")
            if refusal is not None:
                return refusal
            inner = cast("Mapping[str, object]", mapping["content"])
            wrapped: dict[str, object] = {"kind": "identity-content", "content": dict(inner)}
            return Ok(wrapped)
        kind = mapping.get("kind")
        if not isinstance(kind, str) or kind not in BARSPEC_KINDS:
            return invalid(
                "bar_spec",
                "a BarSpec kind is one of registry:barspec_kinds; never a bare timeframe",
                given=repr(kind),
                allowed=sorted(BARSPEC_KINDS),
            )
        content: dict[str, object] = dict(mapping)
        refusal = fp1_clean(content, "bar_spec")
        if refusal is not None:
            return refusal
        identity: dict[str, object] = {"kind": "identity-content", "content": content}
        return Ok(identity)
    return invalid(
        "bar_spec",
        "a bar spec is referenced by identity: a Fingerprint, an fp1 string, or a "
        "canonical identity mapping",
        given=repr(value),
    )


def _source_content(source: object) -> Result[dict[str, object]]:
    if isinstance(source, Instrument):
        instrument: dict[str, object] = {
            "kind": "instrument",
            "venue": source.venue.value,
            "symbol": source.symbol,
        }
        return Ok(instrument)
    if isinstance(source, Mapping):
        mapping = cast("Mapping[str, object]", source)
        kind = mapping.get("kind")
        if kind == "instrument":
            venue = clean_token(mapping.get("venue"))
            symbol = clean_token(mapping.get("symbol"))
            if venue is None or symbol is None:
                return invalid(
                    "source",
                    "an instrument source carries venue and the venue's own symbol",
                    given="mapping",
                )
            instrument_src: dict[str, object] = {
                "kind": "instrument",
                "venue": venue,
                "symbol": symbol,
            }
            return Ok(instrument_src)
        if kind == "source-id":
            token = clean_token(mapping.get("id"))
            if token is None:
                return invalid("source", "a source-id token is a non-empty opaque id")
            source_id: dict[str, object] = {"kind": "source-id", "id": token}
            return Ok(source_id)
        return invalid("source", "source kind is instrument or source-id", given=repr(kind))
    token = clean_token(source)
    if token is not None:
        opaque: dict[str, object] = {"kind": "source-id", "id": token}
        return Ok(opaque)
    return invalid(
        "source",
        "a series input carries instrument-or-source identity: an Instrument or a "
        "non-empty opaque source-id token",
        given=repr(source),
    )


def coerce_input(value: object) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return invalid(
            "inputs",
            "each input is a mapping of name, source, bar_spec, channel_kind, quote_side",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
    name = clean_token(mapping.get("name"))
    if name is None:
        return invalid(
            "name", "a series input names a non-empty key", given=repr(mapping.get("name"))
        )
    source = _source_content(mapping.get("source"))
    if is_refusal(source):
        return source
    bar_spec = coerce_bar_spec(mapping.get("bar_spec"))
    if is_refusal(bar_spec):
        return bar_spec
    channel = coerce_enum(ChannelKind, mapping.get("channel_kind"))
    if channel is None:
        return invalid(
            "channel_kind",
            "the channel kind is one of the closed set",
            given=repr(mapping.get("channel_kind")),
            allowed=[member.value for member in ChannelKind],
        )
    side = coerce_enum(QuoteSide, mapping.get("quote_side"))
    if side is None:
        return invalid(
            "quote_side",
            "the quote side is one of the closed set",
            given=repr(mapping.get("quote_side")),
            allowed=[member.value for member in QuoteSide],
        )
    content: dict[str, object] = {
        "class": "series-input",
        "name": name,
        "source": source.value,
        "bar_spec": bar_spec.value,
        "channel_kind": channel.value,
        "quote_side": side.value,
        "format_version": CT16_FORMAT_VERSION,
    }
    upstream = mapping.get("upstream_fingerprint")
    if upstream is not None:
        parsed = coerce_fingerprint(upstream)
        if is_refusal(parsed):
            return invalid(
                "upstream_fingerprint",
                "a derived input's upstream fingerprint is fp1:sha256:<hex>; omit it "
                "for a non-derived input",
                given=repr(upstream),
            )
        content["upstream_fingerprint"] = parsed.value.value
    refusal = fp1_clean(content, "inputs")
    if refusal is not None:
        return refusal
    return Ok(content)


def coerce_inputs(value: object) -> Result[tuple[dict[str, object], ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "inputs",
            "inputs are an order-significant sequence of named series references",
            given=repr(value),
        )
    resolved: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, item in enumerate(cast("Sequence[object]", value)):
        coerced = coerce_input(item)
        if is_refusal(coerced):
            return invalid(
                "inputs",
                "each input is a named series reference (instrument-or-source, BarSpec, "
                "channel, quote side)",
                index=index,
                cause=dict(coerced.context),
            )
        name = str(coerced.value["name"])
        if name in seen:
            return invalid(
                "inputs",
                "input names are unique within a configuration's named set",
                index=index,
                name=name,
            )
        seen.add(name)
        resolved.append(coerced.value)
    if not resolved:
        return invalid("inputs", "a configuration declares one or more inputs")
    return Ok(tuple(resolved))


def coerce_output_channel(value: object) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return invalid(
            "output_schema",
            "each output channel is a mapping of name, channel_kind, arity, index_offset",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
    name = clean_token(mapping.get("name"))
    if name is None:
        return invalid("name", "an output channel names a non-empty key")
    channel = coerce_enum(ChannelKind, mapping.get("channel_kind"))
    if channel is None:
        return invalid(
            "channel_kind",
            "the channel kind is one of the closed set",
            given=repr(mapping.get("channel_kind")),
            allowed=[member.value for member in ChannelKind],
        )
    arity = coerce_enum(OutputArity, mapping.get("arity"))
    if arity is None:
        return invalid(
            "arity",
            "the output arity is one of the closed set",
            given=repr(mapping.get("arity")),
            allowed=[member.value for member in OutputArity],
        )
    offset = mapping.get("index_offset")
    if isinstance(offset, bool) or not isinstance(offset, int):
        return invalid(
            "index_offset",
            "the index offset is an integer position into the index-aligned output",
            given=repr(offset),
        )
    content: dict[str, object] = {
        "class": "output-channel",
        "name": name,
        "channel_kind": channel.value,
        "arity": arity.value,
        "index_offset": offset,
        "format_version": CT16_FORMAT_VERSION,
    }
    return Ok(content)


def coerce_output_schema(value: object) -> Result[tuple[dict[str, object], ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return invalid(
            "output_schema",
            "the output schema is an order-significant sequence of output channels",
            given=repr(value),
        )
    resolved: list[dict[str, object]] = []
    seen: set[str] = set()
    for index, item in enumerate(cast("Sequence[object]", value)):
        coerced = coerce_output_channel(item)
        if is_refusal(coerced):
            return invalid(
                "output_schema",
                "each output channel is a named channel (kind, arity, index offset)",
                index=index,
                cause=dict(coerced.context),
            )
        name = str(coerced.value["name"])
        if name in seen:
            return invalid(
                "output_schema",
                "output channel names are unique within a configuration's schema",
                index=index,
                name=name,
            )
        seen.add(name)
        resolved.append(coerced.value)
    if not resolved:
        return invalid("output_schema", "a configuration declares one or more output channels")
    return Ok(tuple(resolved))


def coerce_modes(value: object) -> Result[tuple[str, ...]]:
    if isinstance(value, (str, bytes)) or not isinstance(value, (Sequence, frozenset, set)):
        return invalid(
            "supported_modes",
            "supported modes are a collection of batch/streaming members (a bare string "
            "is not a mode set)",
            given=repr(value),
        )
    resolved: dict[str, str] = {}
    for item in cast("Sequence[object]", value):
        mode = coerce_enum(SupportedMode, item)
        if mode is None:
            return invalid(
                "supported_modes",
                "each supported mode is one of the closed set",
                given=repr(item),
                allowed=[member.value for member in SupportedMode],
            )
        resolved[mode.value] = mode.value
    if not resolved:
        return invalid("supported_modes", "a configuration declares one or more supported modes")
    return Ok(tuple(resolved[key] for key in sorted(resolved)))


def arithmetic_reference_identity(value: object) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return invalid(
            "arithmetic_reference_configuration",
            "the arithmetic-reference configuration is the identity of "
            "registry:canonical_indicator_reference (c library, python wrapper, "
            "reference-configuration record)",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
    c_lib = clean_token(mapping.get("c_library"))
    if c_lib is None:
        return invalid(
            "c_library",
            "the canonical-reference C library is a non-empty lockfile-resolved "
            "artifact identity (never a bare version string)",
            given=repr(mapping.get("c_library")),
        )
    wrapper = clean_token(mapping.get("python_wrapper"))
    if wrapper is None:
        return invalid(
            "python_wrapper",
            "the canonical-reference Python wrapper is a non-empty lockfile-resolved "
            "artifact identity (never a bare version string)",
            given=repr(mapping.get("python_wrapper")),
        )
    config = mapping.get("reference_configuration")
    if not isinstance(config, Mapping):
        return invalid(
            "reference_configuration",
            "the reference-configuration record is a key->value mapping "
            "(compatibility mode, candle settings)",
            given=repr(type(config).__name__),
        )
    config_map = cast("Mapping[str, object]", config)
    if len(config_map) == 0:
        return invalid(
            "reference_configuration",
            "the reference-configuration record must carry at least one asserted field",
        )
    refusal = fp1_clean(dict(config_map), "reference_configuration")
    if refusal is not None:
        return refusal
    content: dict[str, object] = {
        "class": "arithmetic-reference",
        "c_library": c_lib,
        "python_wrapper": wrapper,
        "reference_configuration": dict(config_map),
        "format_version": CT16_FORMAT_VERSION,
    }
    return Ok(content)


def emission_policy_identity(value: object) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return invalid(
            "emission_policy",
            "the emission policy is bar-closed vs in-progress plus evidence granularity",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
    timing = coerce_enum(EmissionTiming, mapping.get("timing"))
    if timing is None:
        return invalid(
            "timing",
            "the emission timing is one of the closed set",
            given=repr(mapping.get("timing")),
            allowed=[member.value for member in EmissionTiming],
        )
    granularity = clean_token(mapping.get("evidence_granularity"))
    if granularity is None:
        return invalid(
            "evidence_granularity",
            "the evidence emission granularity is a non-empty declared token",
        )
    content: dict[str, object] = {
        "class": "emission-policy",
        "timing": timing.value,
        "evidence_granularity": granularity,
        "format_version": CT16_FORMAT_VERSION,
    }
    return Ok(content)


def declared_budget_identity(value: object) -> Result[dict[str, object]]:
    if not isinstance(value, Mapping):
        return invalid(
            "declared_budget",
            "the declared budget is the four light-claim bounds",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
    rung = clean_token(mapping.get("per_update_cost_rung"))
    if rung is None:
        return invalid("per_update_cost_rung", "the per-update cost rung is a non-empty token")
    if not isinstance(mapping.get("bounded_state"), bool):
        return invalid("bounded_state", "bounded-state is a declared boolean bound")
    rule = clean_token(mapping.get("window_or_anchor_rule"))
    if rule is None:
        return invalid(
            "window_or_anchor_rule",
            "the bounded evidence window or declared anchor-reset rule is a non-empty token",
        )
    if not isinstance(mapping.get("synchronous_availability"), bool):
        return invalid(
            "synchronous_availability", "synchronous-availability is a declared boolean bound"
        )
    content: dict[str, object] = {
        "class": "declared-budget",
        "per_update_cost_rung": rung,
        "bounded_state": mapping["bounded_state"],
        "window_or_anchor_rule": rule,
        "synchronous_availability": mapping["synchronous_availability"],
        "format_version": CT16_FORMAT_VERSION,
    }
    return Ok(content)


def coerce_duration(value: object) -> Result[Duration]:
    if isinstance(value, Duration):
        return Ok(value)
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        built = Duration.try_create(mapping.get("value_ns"))
        if is_refusal(built):
            return invalid(
                "warm_up_time_bound",
                "the warm-up time bound is a Duration (int64 nanoseconds)",
                cause=dict(built.context),
            )
        return built
    built = Duration.try_create(value)
    if is_refusal(built):
        return invalid(
            "warm_up_time_bound",
            "the warm-up time bound is a Duration; it is omitted exactly when the "
            "BarSpec is event-driven",
            given=repr(value),
        )
    return built
