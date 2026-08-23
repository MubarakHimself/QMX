"""Closed vocabularies for the footprint consumption manifest (QL-4).

These names are CT-16 / B-12 contract surface, authored here because qml never
imports ``qmf-indicators`` or ``qmf-structure`` (DEC-0171). Values match the
ratified enumerations so a resolved template fingerprints as an ordinary
configured producer.
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final, TypeVar

from qmf.core.refusal import Ok, Result

from qml._refuse import invalid

__all__ = [
    "AD22_IDENTITY_FIELDS",
    "BARSPEC_KINDS",
    "CT16_FORMAT_VERSION",
    "FORBIDDEN_HORIZON_FIELDS",
    "AlignmentPolicy",
    "BarSpecKind",
    "ChannelKind",
    "EmissionTiming",
    "MissingValuePolicy",
    "OutputArity",
    "ProducerBindingForm",
    "ProducerKind",
    "QuoteSide",
    "StreamRole",
    "SupportedMode",
    "parse_binding_form",
]

# CT-16/CT-17 envelope format version stamped into configured-producer identity
# (DEC-0103). Distinct from a configuration's per-producer contract_format_version.
CT16_FORMAT_VERSION: Final[int] = 1

# AD-22 identity fields a template must carry; an omitted field is a Layer-1
# registration refusal (DEC-0174). Parameters are not listed: a template omits
# only the space-bound parameter *values*.
AD22_IDENTITY_FIELDS: Final[tuple[str, ...]] = (
    "formula_id",
    "contract_format_version",
    "inputs",
    "calendar_requirements",
    "alignment_policy",
    "missing_value_policy",
    "warm_up",
    "output_schema",
    "supported_modes",
    "arithmetic_reference_configuration",
)

# Hand-declared window aliases that must never appear on the declaration (DEC-0174).
FORBIDDEN_HORIZON_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "warm_up_horizon",
        "warmup_horizon",
        "embargo_horizon",
        "embargo_window",
        "warm_up_window",
        "warmup_window",
        "horizon",
    }
)

BARSPEC_KINDS: Final[frozenset[str]] = frozenset(
    {
        "time-interval",
        "tick-count",
        "volume-threshold",
        "notional-threshold",
        "price-brick",
        "range",
        "session",
    }
)

EnumT = TypeVar("EnumT", bound=StrEnum)


class ProducerBindingForm(StrEnum):
    """Closed producer-binding forms; addable never redefined (DEC-0174)."""

    PINNED_FINGERPRINT = "pinned-fingerprint"
    TEMPLATE = "template"


class ProducerKind(StrEnum):
    """Configured-producer kind a template resolves to (CT-16 or CT-17)."""

    INDICATOR = "indicator"
    STRUCTURE = "structure"


class StreamRole(StrEnum):
    """B-12 stream roles nested inside the footprint (DEC-0174)."""

    TRADING = "trading"
    DATA_ONLY = "data-only"


class BarSpecKind(StrEnum):
    """``registry:barspec_kinds`` — BarSpec never bare 'timeframe' (DEC-0126)."""

    TIME_INTERVAL = "time-interval"
    TICK_COUNT = "tick-count"
    VOLUME_THRESHOLD = "volume-threshold"
    NOTIONAL_THRESHOLD = "notional-threshold"
    PRICE_BRICK = "price-brick"
    RANGE = "range"
    SESSION = "session"


class AlignmentPolicy(StrEnum):
    """Declared alignment; ``as-of`` is the only governed-evidence-legal value."""

    AS_OF = "as-of"


class MissingValuePolicy(StrEnum):
    """Declared missing-value policy; never silent filling (DEC-0126)."""

    MARK_GAP = "mark-gap"
    REFUSE = "refuse"


class SupportedMode(StrEnum):
    """CT-16 supported modes (DEC-0126)."""

    BATCH = "batch"
    STREAMING = "streaming"


class ChannelKind(StrEnum):
    """CT-16 channel kind (DEC-0126)."""

    EXACT_PRICE = "exact-price"
    EXACT_QUANTITY = "exact-quantity"
    FLOAT_ANALYTIC = "float-analytic"
    INTEGER_CODE = "integer-code"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"


class QuoteSide(StrEnum):
    """CT-16 quote side (DEC-0126)."""

    BID = "bid"
    ASK = "ask"
    MID = "mid"
    LAST = "last"


class OutputArity(StrEnum):
    """CT-16 output-channel arity (DEC-0126)."""

    SCALAR_PER_SAMPLE = "scalar-per-sample"
    FIXED_VECTOR = "fixed-vector"
    KEYED_BY_PRICE_BIN = "keyed-by-price-bin"


class EmissionTiming(StrEnum):
    """Bar-closed vs in-progress emission timing (DEC-0126)."""

    BAR_CLOSED = "bar-closed"
    IN_PROGRESS = "in-progress"


def parse_binding_form(value: object) -> Result[ProducerBindingForm]:
    """Resolve a producer-binding form, value-or-refusal."""
    if isinstance(value, ProducerBindingForm):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(ProducerBindingForm(value))
        except ValueError:
            pass
    return invalid(
        "form",
        "a producer binding is pinned-fingerprint or template",
        given=repr(value),
    )


def coerce_enum(enum_cls: type[EnumT], value: object) -> EnumT | None:
    """Resolve ``value`` to a member of ``enum_cls``, or ``None``."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return None
    return None
