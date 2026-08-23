"""CT-16 — the configured-indicator declaration record and its fp1 identity
(COMP-QMF-INDICATORS).

A configured indicator's identity is the **entire declared configuration**, and its
``fp1`` fingerprint is the only dedup key. This module lands that declaration record
(Story 7.1): a frozen :class:`ConfiguredIndicator` whose ``fp1`` — computed by the
single ``qmf-core`` fingerprint function and **nowhere else** (CT-05; DEC-0108) —
spans every identity element, so no configuration element can silently drift out of
identity and two configurations differing in any one element receive distinct
fingerprints (DEC-0126).

The identity spans, exactly (CT-16 ``schema.fields``; DEC-0126):

* ``formula_id`` — the opaque, stable formula identity (never reused; an operator
  discipline the type cannot enforce, so construction validates only non-blankness).
* ``contract_format_version`` — the per-configured-indicator integer format version,
  which mints on an output-changing arithmetic upgrade (DEC-0127, DEC-0103).
* ``parameters`` — a named set of **exact rationals only** (:class:`~qmf.core.ExactRational`
  — scaled integers or numerator/denominator pairs); a binary float is refused, so a
  float never appears in a parameter or in identity (FM-1; DEC-0105, DEC-0108).
* ``inputs`` — the **ordered** named set of one or more :class:`SeriesInput` references,
  each carrying instrument-or-source identity, a ``BarSpec`` identity, channel kind,
  quote side, and — for a derived input — the upstream artifact's fingerprint.
* ``calendar_requirements`` — the declared :class:`~qmf.core.CalendarIdentity` set
  (rule set + version + **tzdata version**), canonically ordered (DEC-0106).
* ``alignment_policy`` and ``missing_value_policy`` — the declared policies; only
  as-of alignment is governed-evidence-legal, and missing values never silent-fill
  (DEC-0126).
* ``warm_up`` — an integer count of completed input observations, identical across
  modes (and the optional :attr:`~ConfiguredIndicator.warm_up_time_bound` when a
  time bound is declared).
* ``output_schema`` — the **ordered** named :class:`OutputChannel` set.
* ``supported_modes`` — batch, streaming, or both (canonically ordered).
* ``arithmetic_reference_configuration`` — the identity-bearing
  :class:`ArithmeticReference` record of ``registry:canonical_indicator_reference``.

The ``BarSpec`` series vocabulary is a ``qmf-core`` noun (no other package may define
it; DEC-0126), so a :class:`SeriesInput` **references** a bar spec by its identity
content — a :class:`~qmf.core.Fingerprint`, a value exposing
:class:`SupportsFp1Identity`, or a canonical identity mapping — and never redefines
the type here.

Default-deny holds: this module imports **only** ``qmf.core`` (every ``fp1``
fingerprint is computed there); nothing imports ``qmf-indicators`` under default-deny,
and a configuration is assembled by the application at the composition root (DEC-0120).
Every public operation succeeds or RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`;
domain failure is never raised across the boundary (DEC-0109, DEC-0112). Public value
types are frozen dataclasses and the public seam is a :class:`typing.Protocol` (DEC-0101).
Stdlib plus ``qmf-core`` only; frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, Protocol, TypeVar, cast, runtime_checkable

from qmf.core import (
    CalendarIdentity,
    Duration,
    ExactRational,
    Fingerprint,
    Instrument,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    canonical_bytes,
    fingerprint,
    is_ok,
    is_refusal,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "IDENTITY_ELEMENTS",
    "OPTIONAL_IDENTITY_ELEMENTS",
    "AlignmentPolicy",
    "ArithmeticReference",
    "ChannelKind",
    "ConfiguredIndicator",
    "DeclaredBudget",
    "EmissionPolicy",
    "EmissionTiming",
    "MissingValuePolicy",
    "OutputArity",
    "OutputChannel",
    "QuoteSide",
    "SeriesInput",
    "SupportedMode",
    "SupportsFp1Identity",
]

# The CT-16 configured-indicator declaration-record contract format version — the
# version of the identity SHAPE this module serializes, stamped into every
# configuration's identity so history stays readable and an incompatible envelope
# change mints the next version (DEC-0103; versioning-from-birth L15). It is distinct
# from a configuration's ``contract_format_version`` field, which is the
# per-configured-indicator format version that mints on an arithmetic upgrade (DEC-0127).
CONTRACT_FORMAT_VERSION: Final[int] = 1

# The required identity elements — the entire declared configuration a fingerprint
# must span (CT-16 AC; DEC-0126). Every one of these keys MUST appear in
# :meth:`ConfiguredIndicator.fp1_identity`; an element missing from the fingerprint is
# a contract defect (the conformance test fails). The order here is documentation only
# — the canonical serializer sorts object keys lexicographically (DEC-0108).
IDENTITY_ELEMENTS: Final[tuple[str, ...]] = (
    "formula_id",
    "contract_format_version",
    "parameters",
    "inputs",
    "calendar_requirements",
    "alignment_policy",
    "missing_value_policy",
    "warm_up",
    "output_schema",
    "supported_modes",
    "arithmetic_reference_configuration",
)

# Identity-bearing elements that are declared per configuration and enter the
# fingerprint WHEN present, omitted (never a null) otherwise: the emission policy, the
# optional warm-up time bound (null exactly when the BarSpec is event-driven), and the
# light-claim declared budget (absent means heavy-by-default) (DEC-0126, DEC-0128).
OPTIONAL_IDENTITY_ELEMENTS: Final[tuple[str, ...]] = (
    "emission_policy",
    "warm_up_time_bound",
    "declared_budget",
)


# --- enums (CT-16 contract vocabulary) --------------------------------------


class ChannelKind(StrEnum):
    """A declared channel kind (CT-16 ``enums.channel_kind``; DEC-0126)."""

    EXACT_PRICE = "exact-price"
    EXACT_QUANTITY = "exact-quantity"
    FLOAT_ANALYTIC = "float-analytic"
    INTEGER_CODE = "integer-code"
    BOOLEAN = "boolean"
    CATEGORICAL = "categorical"


class QuoteSide(StrEnum):
    """A declared quote side (CT-16 ``enums.quote_side``; DEC-0126).

    ``mid`` is a derived series with a stated rounding mode; the rounding declaration
    is a later-story concern, so this enum names the side only.
    """

    BID = "bid"
    ASK = "ask"
    MID = "mid"
    LAST = "last"


class SupportedMode(StrEnum):
    """A conformant mode a configuration declares (CT-16; DEC-0126).

    A configuration declares ``batch``, ``streaming``, or both; the equality law binds
    only when both are declared. A batch-only configuration is heavy on the live path
    by definition (DEC-0128).
    """

    BATCH = "batch"
    STREAMING = "streaming"


class OutputArity(StrEnum):
    """The arity of an output channel (CT-16 ``schema.output_schema``; DEC-0126)."""

    SCALAR_PER_SAMPLE = "scalar-per-sample"
    FIXED_VECTOR = "fixed-vector"
    KEYED_BY_PRICE_BIN = "keyed-by-price-bin"


class AlignmentPolicy(StrEnum):
    """A declared alignment policy (CT-16; DEC-0126).

    ``as-of`` (the last value known at or before the evaluation instant) is the **only**
    governed-evidence-legal value; forward-fill or interpolation across the evaluation
    instant is a policy-rejection refusal on the compute path (a later story). This enum
    names the declared policy that enters identity.
    """

    AS_OF = "as-of"


class MissingValuePolicy(StrEnum):
    """A declared missing-value policy (CT-16 FM-1; DEC-0126, DEC-0109).

    A calendar-open position with no data follows the declared policy, never silent
    filling: it is either marked as a gap in the presence map or refused. Forward-fill
    and interpolation are deliberately absent — across the evaluation instant they are a
    policy rejection, not a legal missing-value policy.
    """

    MARK_GAP = "mark-gap"
    REFUSE = "refuse"


class EmissionTiming(StrEnum):
    """The bar-closed vs in-progress emission timing a configuration declares (CT-16;
    DEC-0126, DEC-0110).

    A provisional (in-progress) sample never enters governed evidence; the timing is a
    declared identity-bearing part of the emission policy.
    """

    BAR_CLOSED = "bar-closed"
    IN_PROGRESS = "in-progress"


# --- the public identity-content seam ---------------------------------------


@runtime_checkable
class SupportsFp1Identity(Protocol):
    """A value that exposes its own canonical ``fp1`` identity content (CT-05; DEC-0108).

    The public seam a :class:`SeriesInput` accepts for a bar-spec (or instrument-or-source)
    identity that is not a bare :class:`~qmf.core.Fingerprint`: any ``qmf-core`` value
    that enters identity satisfies it (Instrument, CalendarIdentity, ExactRational, and
    the eventual ``BarSpec`` noun), so a bar spec can be referenced by its identity
    content without ``qmf-indicators`` redefining the type (DEC-0126).
    """

    def fp1_identity(self) -> Mapping[str, object]:  # pragma: no cover - protocol seam
        ...


# --- refusal + validation helpers -------------------------------------------


EnumT = TypeVar("EnumT", bound=StrEnum)


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a declaration operation returns.

    ``retryability`` is ``no`` — a malformed configuration part, a binary-float
    parameter, or an unknown enum member is a caller/wiring mistake, not a transient
    condition — and ``context`` always names the offending ``field`` and a
    human-legible ``reason`` (returned, never raised; CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    An opaque declared token (a formula id, a policy or granularity token) is returned
    exactly as the caller minted it — never stripped, cased, or parsed.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _positive_int(value: object) -> int | None:
    """Return ``value`` as a genuine positive ``int`` (a ``bool`` is rejected), else
    ``None`` — a contract format version is a positive integer ordinal (DEC-0103)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _nonneg_int(value: object) -> int | None:
    """Return ``value`` as a genuine non-negative ``int`` (a ``bool`` is rejected),
    else ``None`` — a warm-up is an integer count of observations (DEC-0126)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _coerce_enum(enum_cls: type[EnumT], value: object) -> EnumT | None:
    """Resolve ``value`` to a member of ``enum_cls``, or ``None`` if it names none."""
    if isinstance(value, enum_cls):
        return value
    if isinstance(value, str):
        try:
            return enum_cls(value)
        except ValueError:
            return None
    return None


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`~qmf.core.Fingerprint` or a valid ``fp1:sha256:<hex>`` string,
    else ``None`` — parsing routes through qmf-core, never a local hash."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _deep_freeze(value: object) -> object:
    """Recursively snapshot ``value`` into a shared-safe, read-only form.

    A ``Mapping`` becomes a :class:`~types.MappingProxyType` over deep-frozen values and
    a list/tuple becomes a tuple — so a nested container reached through the caller's
    dict can never be mutated through the reference a frozen declaration keeps. A
    configuration is immutable identity; it must never rewrite.
    """
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return MappingProxyType({key: _deep_freeze(item) for key, item in mapping.items()})
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return tuple(_deep_freeze(item) for item in sequence)
    return value


def _fp1_clean(content: object, field: str) -> TypedRefusal | None:
    """Return a refusal if ``content`` is not ``fp1``-clean identity content, else ``None``.

    Routes the candidate through qmf-core's one canonical serializer: a binary float, a
    null, a non-string key, or an unsupported type is refused there, and this surfaces
    it as an ``invalid input`` refusal naming ``field`` — the same guard the record
    factory applies before a value is admitted into identity (DEC-0108).
    """
    serialized = canonical_bytes(content)
    if is_refusal(serialized):
        return _invalid(
            field,
            "the value is not fp1-clean identity content; a binary float, a null, a "
            "non-string key, or an unsupported type is refused (identity numerics are "
            "integers; an absent value is an omitted key) (DEC-0108)",
            cause=dict(serialized.context),
        )
    return None


# --- series input reference -------------------------------------------------


@dataclass(frozen=True, slots=True)
class SeriesInput:
    """One named series reference in a configuration's ordered input set (CT-16;
    DEC-0126).

    Each input carries its ``name`` (the ordered named key), its instrument-or-source
    identity (``source`` — an :class:`~qmf.core.Instrument` or an opaque source-id
    token), its ``bar_spec`` identity (a :class:`~qmf.core.Fingerprint`, a value exposing
    :class:`SupportsFp1Identity`, or a canonical identity mapping — the ``BarSpec`` value
    type stays a ``qmf-core`` noun and is only referenced here), its ``channel_kind`` and
    ``quote_side``, and — for a **derived** input — ``upstream_fingerprint``, the upstream
    artifact's fingerprint that enters downstream identity (composition is law).
    """

    name: str
    source: Instrument | str
    bar_spec: str | Mapping[str, object] | SupportsFp1Identity
    channel_kind: ChannelKind
    quote_side: QuoteSide
    upstream_fingerprint: Fingerprint | None = None

    @classmethod
    def try_create(
        cls,
        name: object,
        source: object,
        bar_spec: object,
        channel_kind: object,
        quote_side: object,
        upstream_fingerprint: object = None,
    ) -> Result[SeriesInput]:
        """Validate and build a :class:`SeriesInput`, returning value-or-refusal.

        ``name`` is a non-blank key; ``source`` an :class:`~qmf.core.Instrument` or a
        non-blank source-id token; ``bar_spec`` an fp1-clean identity reference
        (:class:`~qmf.core.Fingerprint`, a :class:`SupportsFp1Identity` value, or a
        canonical mapping); ``channel_kind`` and ``quote_side`` members of their closed
        sets; and ``upstream_fingerprint`` — present only for a derived input — a
        :class:`~qmf.core.Fingerprint` (or fp string) or ``None``.
        """
        key = _clean_str(name)
        if key is None:
            return _invalid("name", "a series input names a non-empty key", given=repr(name))
        resolved_source = _coerce_source(source)
        if isinstance(resolved_source, TypedRefusal):
            return resolved_source
        resolved_spec = _coerce_bar_spec(bar_spec)
        if isinstance(resolved_spec, TypedRefusal):
            return resolved_spec
        channel = _coerce_enum(ChannelKind, channel_kind)
        if channel is None:
            return _invalid(
                "channel_kind",
                "the channel kind is one of the closed set",
                given=repr(channel_kind),
                allowed=[member.value for member in ChannelKind],
            )
        side = _coerce_enum(QuoteSide, quote_side)
        if side is None:
            return _invalid(
                "quote_side",
                "the quote side is one of the closed set",
                given=repr(quote_side),
                allowed=[member.value for member in QuoteSide],
            )
        upstream: Fingerprint | None = None
        if upstream_fingerprint is not None:
            upstream = _coerce_fingerprint(upstream_fingerprint)
            if upstream is None:
                return _invalid(
                    "upstream_fingerprint",
                    "a derived input's upstream fingerprint is a Fingerprint (or "
                    "fp1:sha256:<hex> string); omit it for a non-derived input",
                    given=repr(upstream_fingerprint),
                )
        return Ok(
            cls(
                name=key,
                source=resolved_source,
                bar_spec=resolved_spec,
                channel_kind=channel,
                quote_side=side,
                upstream_fingerprint=upstream,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this input (DEC-0126,
        DEC-0108).

        The ``upstream_fingerprint`` is present exactly when the input is derived; an
        absent value is an omitted key, never a null.
        """
        content: dict[str, object] = {
            "class": "series-input",
            "name": self.name,
            "source": _source_content(self.source),
            "bar_spec": _bar_spec_content(self.bar_spec),
            "channel_kind": self.channel_kind.value,
            "quote_side": self.quote_side.value,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.upstream_fingerprint is not None:
            content["upstream_fingerprint"] = self.upstream_fingerprint.value
        return content


def _coerce_source(value: object) -> Instrument | str | TypedRefusal:
    """Resolve an instrument-or-source identity to an :class:`~qmf.core.Instrument` or a
    non-blank source-id token, else a refusal."""
    if isinstance(value, Instrument):
        return value
    token = _clean_str(value)
    if token is not None:
        return token
    return _invalid(
        "source",
        "a series input carries instrument-or-source identity: an Instrument or a "
        "non-empty opaque source-id token",
        given=repr(value),
    )


def _source_content(source: Instrument | str) -> dict[str, object]:
    """The canonical identity fragment for an instrument-or-source identity.

    The ``kind`` discriminator keeps an instrument and a source-id token in distinct
    identity spaces, so a source string can never collide with an instrument's content.
    An :class:`~qmf.core.Instrument` carries no ``fp1_identity`` of its own (its identity
    is the opaque ``(venue, symbol)`` pair), so the canonical fragment is built from those
    two opaque parts directly (CT-03; DEC-0107).
    """
    if isinstance(source, Instrument):
        return {
            "kind": "instrument",
            "venue": source.venue.value,
            "symbol": source.symbol,
        }
    return {"kind": "source-id", "id": source}


def _coerce_bar_spec(
    value: object,
) -> str | Mapping[str, object] | SupportsFp1Identity | TypedRefusal:
    """Resolve a bar-spec identity reference to fp1-clean identity content, else a refusal.

    A :class:`~qmf.core.Fingerprint` (or fp string) is stored as its opaque value; a
    :class:`SupportsFp1Identity` value or a canonical mapping is validated fp1-clean and
    stored as-is. The ``BarSpec`` value type is a ``qmf-core`` noun; this only references
    it by identity (DEC-0126).
    """
    if isinstance(value, Fingerprint):
        return value.value
    if isinstance(value, str):
        parsed = Fingerprint.try_create(value)
        if is_ok(parsed):
            # Return the validated fingerprint STRING (not the Ok's Fingerprint), so a
            # Fingerprint and its string form resolve to one identical bar-spec reference.
            return parsed.value.value
        return _invalid(
            "bar_spec",
            "a string bar-spec reference must be an fp1:sha256:<hex> fingerprint; pass a "
            "Fingerprint, a value exposing fp1_identity, or a canonical identity mapping",
            given=repr(value),
        )
    if isinstance(value, SupportsFp1Identity):
        refusal = _fp1_clean(value.fp1_identity(), "bar_spec")
        if refusal is not None:
            return refusal
        return value
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        refusal = _fp1_clean(mapping, "bar_spec")
        if refusal is not None:
            return refusal
        return mapping
    return _invalid(
        "bar_spec",
        "a bar spec is referenced by identity: a Fingerprint, a value exposing "
        "fp1_identity, or a canonical identity mapping (the BarSpec type is a qmf-core noun)",
        given=repr(value),
    )


def _bar_spec_content(
    bar_spec: str | Mapping[str, object] | SupportsFp1Identity,
) -> dict[str, object]:
    """The canonical identity fragment for a bar-spec reference, discriminated by form."""
    if isinstance(bar_spec, str):
        return {"kind": "fingerprint-ref", "ref": bar_spec}
    if isinstance(bar_spec, Mapping):
        return {"kind": "identity-content", "content": dict(bar_spec)}
    return {"kind": "identity", "identity": bar_spec.fp1_identity()}


# --- output channel ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OutputChannel:
    """One named output channel in a configuration's ordered output schema (CT-16;
    DEC-0126).

    A channel carries its ``name``, its ``channel_kind``, its ``arity``
    (scalar-per-sample, fixed vector, or keyed-by-price-bin), and its ``index_offset``
    into the index-aligned output.
    """

    name: str
    channel_kind: ChannelKind
    arity: OutputArity
    index_offset: int

    @classmethod
    def try_create(
        cls, name: object, channel_kind: object, arity: object, index_offset: object
    ) -> Result[OutputChannel]:
        """Validate and build an :class:`OutputChannel`, returning value-or-refusal."""
        key = _clean_str(name)
        if key is None:
            return _invalid("name", "an output channel names a non-empty key", given=repr(name))
        channel = _coerce_enum(ChannelKind, channel_kind)
        if channel is None:
            return _invalid(
                "channel_kind",
                "the channel kind is one of the closed set",
                given=repr(channel_kind),
                allowed=[member.value for member in ChannelKind],
            )
        resolved_arity = _coerce_enum(OutputArity, arity)
        if resolved_arity is None:
            return _invalid(
                "arity",
                "the output arity is one of the closed set",
                given=repr(arity),
                allowed=[member.value for member in OutputArity],
            )
        if isinstance(index_offset, bool) or not isinstance(index_offset, int):
            return _invalid(
                "index_offset",
                "the index offset is an integer position into the index-aligned output",
                given=repr(index_offset),
            )
        return Ok(
            cls(
                name=key,
                channel_kind=channel,
                arity=resolved_arity,
                index_offset=index_offset,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this output channel."""
        return {
            "class": "output-channel",
            "name": self.name,
            "channel_kind": self.channel_kind.value,
            "arity": self.arity.value,
            "index_offset": self.index_offset,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- emission policy --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class EmissionPolicy:
    """A configuration's declared emission policy (CT-16; DEC-0126, DEC-0110).

    The ``timing`` is bar-closed vs in-progress, and ``evidence_granularity`` is the
    declared evidence emission granularity token; streaming updates are not individually
    evidence-bearing, so the granularity is declared contract surface.
    """

    timing: EmissionTiming
    evidence_granularity: str

    @classmethod
    def try_create(cls, timing: object, evidence_granularity: object) -> Result[EmissionPolicy]:
        """Validate and build an :class:`EmissionPolicy`, returning value-or-refusal."""
        resolved_timing = _coerce_enum(EmissionTiming, timing)
        if resolved_timing is None:
            return _invalid(
                "timing",
                "the emission timing is one of the closed set",
                given=repr(timing),
                allowed=[member.value for member in EmissionTiming],
            )
        granularity = _clean_str(evidence_granularity)
        if granularity is None:
            return _invalid(
                "evidence_granularity",
                "the evidence emission granularity is a non-empty declared token",
                given=repr(evidence_granularity),
            )
        return Ok(cls(timing=resolved_timing, evidence_granularity=granularity))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this emission policy."""
        return {
            "class": "emission-policy",
            "timing": self.timing.value,
            "evidence_granularity": self.evidence_granularity,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- declared light-claim budget --------------------------------------------


@dataclass(frozen=True, slots=True)
class DeclaredBudget:
    """A configuration's declared light-claim bounds (CT-16; DEC-0128).

    Contract surface distinct from the display-only light/heavy verdict: the four
    declared bounds a light claim rests on — the per-update cost rung, whether declared
    state size is bounded, the bounded evidence window or declared anchor-reset rule,
    and synchronous availability. A configuration with no declared budget is heavy by
    default until the live-path rung has a recorded baseline; the numeric rungs
    themselves await first measured baselines (a deferred measurement, not a gap).
    """

    per_update_cost_rung: str
    bounded_state: bool
    window_or_anchor_rule: str
    synchronous_availability: bool

    @classmethod
    def try_create(
        cls,
        per_update_cost_rung: object,
        bounded_state: object,
        window_or_anchor_rule: object,
        synchronous_availability: object,
    ) -> Result[DeclaredBudget]:
        """Validate and build a :class:`DeclaredBudget`, returning value-or-refusal."""
        rung = _clean_str(per_update_cost_rung)
        if rung is None:
            return _invalid(
                "per_update_cost_rung",
                "the per-update cost rung is a non-empty declared token",
                given=repr(per_update_cost_rung),
            )
        if not isinstance(bounded_state, bool):
            return _invalid(
                "bounded_state",
                "bounded-state is a declared boolean bound",
                given=repr(bounded_state),
            )
        rule = _clean_str(window_or_anchor_rule)
        if rule is None:
            return _invalid(
                "window_or_anchor_rule",
                "the bounded evidence window or declared anchor-reset rule is a non-empty token",
                given=repr(window_or_anchor_rule),
            )
        if not isinstance(synchronous_availability, bool):
            return _invalid(
                "synchronous_availability",
                "synchronous-availability is a declared boolean bound",
                given=repr(synchronous_availability),
            )
        return Ok(
            cls(
                per_update_cost_rung=rung,
                bounded_state=bounded_state,
                window_or_anchor_rule=rule,
                synchronous_availability=synchronous_availability,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this declared budget."""
        return {
            "class": "declared-budget",
            "per_update_cost_rung": self.per_update_cost_rung,
            "bounded_state": self.bounded_state,
            "window_or_anchor_rule": self.window_or_anchor_rule,
            "synchronous_availability": self.synchronous_availability,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- arithmetic-reference configuration -------------------------------------


@dataclass(frozen=True, slots=True)
class ArithmeticReference:
    """The identity-bearing arithmetic-reference configuration record (CT-16; DEC-0127).

    The identity of ``registry:canonical_indicator_reference`` as it enters a
    configuration's fingerprint: the pinned canonical-reference artifacts (the C library
    and the Python wrapper, each identified by its lockfile-resolved artifact identity —
    never a bare version string) plus the identity-bearing reference-configuration record
    (compatibility mode, candle settings) asserted at import and never mutated at runtime.
    The concrete artifact identities and configuration are supplied by the composition
    root against the pinned registry value — never hardcoded here.
    """

    c_library: str
    python_wrapper: str
    reference_configuration: Mapping[str, object]

    def __post_init__(self) -> None:
        # Deep-snapshot the reference-configuration mapping so a later mutation of the
        # caller's dict can never reach into this frozen identity record.
        object.__setattr__(
            self, "reference_configuration", _deep_freeze(self.reference_configuration)
        )

    @classmethod
    def try_create(
        cls, c_library: object, python_wrapper: object, reference_configuration: object
    ) -> Result[ArithmeticReference]:
        """Validate and build an :class:`ArithmeticReference`, returning value-or-refusal.

        The two artifact identities must be non-blank tokens, and the
        reference-configuration mapping must be fp1-clean identity content (no float,
        no null, string keys only) with at least one field.
        """
        c_lib = _clean_str(c_library)
        if c_lib is None:
            return _invalid(
                "c_library",
                "the canonical-reference C library is a non-empty lockfile-resolved "
                "artifact identity (never a bare version string)",
                given=repr(c_library),
            )
        wrapper = _clean_str(python_wrapper)
        if wrapper is None:
            return _invalid(
                "python_wrapper",
                "the canonical-reference Python wrapper is a non-empty lockfile-resolved "
                "artifact identity (never a bare version string)",
                given=repr(python_wrapper),
            )
        if not isinstance(reference_configuration, Mapping):
            return _invalid(
                "reference_configuration",
                "the reference-configuration record is a key->value mapping "
                "(compatibility mode, candle settings)",
                given=repr(type(reference_configuration).__name__),
            )
        config_map = cast("Mapping[str, object]", reference_configuration)
        if len(config_map) == 0:
            return _invalid(
                "reference_configuration",
                "the reference-configuration record must carry at least one asserted field",
            )
        refusal = _fp1_clean(config_map, "reference_configuration")
        if refusal is not None:
            return refusal
        return Ok(
            cls(
                c_library=c_lib,
                python_wrapper=wrapper,
                reference_configuration=config_map,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this reference config."""
        return {
            "class": "arithmetic-reference",
            "c_library": self.c_library,
            "python_wrapper": self.python_wrapper,
            "reference_configuration": dict(self.reference_configuration),
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- the configured-indicator declaration record ----------------------------


def _coerce_parameters(value: object) -> Mapping[str, ExactRational] | TypedRefusal:
    """Resolve a named parameter set of **exact rationals only**, else a refusal (FM-1).

    Each value must be an :class:`~qmf.core.ExactRational` (a scaled integer or a
    numerator/denominator pair); a binary float is refused so a float never appears in a
    parameter or in identity, and every key must be a non-blank string. An empty set is
    legal (a parameterless formula) (DEC-0105, DEC-0108).
    """
    if not isinstance(value, Mapping):
        return _invalid(
            "parameters",
            "parameters are a name->ExactRational mapping (exact rationals only)",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, ExactRational] = {}
    for key, param in mapping.items():
        name = _clean_str(key)
        if name is None:
            return _invalid(
                "parameters", "each parameter name is a non-empty string", key=repr(key)
            )
        if isinstance(param, float):
            return _invalid(
                "parameters",
                "a parameter expressed as a binary float is refused; parameters are exact "
                "rationals only (scaled integers or numerator/denominator pairs), so a "
                "float never appears in a parameter or in identity (FM-1; DEC-0105)",
                parameter=name,
                given=repr(param),
            )
        if not isinstance(param, ExactRational):
            return _invalid(
                "parameters",
                "each parameter is an ExactRational (scaled integer or num/den pair); "
                "build it via ExactRational.try_create so a float can never enter identity",
                parameter=name,
                given=repr(param),
            )
        resolved[name] = param
    return resolved


def _coerce_inputs(value: object) -> tuple[SeriesInput, ...] | TypedRefusal:
    """Resolve the ordered named input set: a sequence of one or more distinctly-named
    :class:`SeriesInput`\\ s, else a refusal.

    Order is significant (composition over an ordered named set), and names are unique —
    a duplicate name is refused rather than silently collapsed (DEC-0126).
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "inputs",
            "inputs are an order-significant sequence of SeriesInput references",
            given=repr(value),
        )
    resolved: list[SeriesInput] = []
    seen: set[str] = set()
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, SeriesInput):
            return _invalid(
                "inputs",
                "each input is a SeriesInput; build it via SeriesInput.try_create",
                index=index,
                given=repr(item),
            )
        if item.name in seen:
            return _invalid(
                "inputs",
                "input names are unique within a configuration's named set",
                index=index,
                name=item.name,
            )
        seen.add(item.name)
        resolved.append(item)
    if not resolved:
        return _invalid("inputs", "a configuration declares one or more inputs")
    return tuple(resolved)


def _coerce_calendars(value: object) -> tuple[CalendarIdentity, ...] | TypedRefusal:
    """Resolve the declared calendar-requirement set to a canonically-ordered tuple of
    :class:`~qmf.core.CalendarIdentity`\\ s, else a refusal.

    Calendar requirements carry no declared order significance, so they are deduplicated
    and sorted by (rule set, version, tzdata version): two callers listing the same
    calendars in different orders derive the same identity. An empty set is legal (an
    event-driven configuration with no calendar requirement) (DEC-0106).
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "calendar_requirements",
            "calendar requirements are a sequence of CalendarIdentity values",
            given=repr(value),
        )
    resolved: dict[tuple[str, str, str], CalendarIdentity] = {}
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, CalendarIdentity):
            return _invalid(
                "calendar_requirements",
                "each calendar requirement is a CalendarIdentity (rule set + version + "
                "tzdata version)",
                index=index,
                given=repr(item),
            )
        resolved[(item.rule_set, item.rule_set_version, item.tzdata_version)] = item
    return tuple(resolved[key] for key in sorted(resolved))


def _coerce_modes(value: object) -> tuple[SupportedMode, ...] | TypedRefusal:
    """Resolve the declared supported-mode set to a canonically-ordered tuple, else a
    refusal — one or more of ``batch`` / ``streaming``, deduplicated and sorted."""
    if isinstance(value, (str, bytes)) or not isinstance(value, (Sequence, frozenset, set)):
        return _invalid(
            "supported_modes",
            "supported modes are a collection of batch/streaming members (a bare string "
            "is not a mode set)",
            given=repr(value),
        )
    resolved: dict[str, SupportedMode] = {}
    for item in cast("Sequence[object]", value):
        mode = _coerce_enum(SupportedMode, item)
        if mode is None:
            return _invalid(
                "supported_modes",
                "each supported mode is one of the closed set",
                given=repr(item),
                allowed=[member.value for member in SupportedMode],
            )
        resolved[mode.value] = mode
    if not resolved:
        return _invalid("supported_modes", "a configuration declares one or more supported modes")
    return tuple(resolved[key] for key in sorted(resolved))


@dataclass(frozen=True, slots=True)
class ConfiguredIndicator:
    """A configured indicator's declaration record whose ``fp1`` is its whole identity
    (CT-16; DEC-0126, DEC-0108).

    Identity is the **entire declared configuration** — every field named in
    :data:`IDENTITY_ELEMENTS`, plus the identity-bearing
    :data:`OPTIONAL_IDENTITY_ELEMENTS` when declared — and the derived ``fp1``
    (:meth:`fp1`) is the **only** dedup key. Two configurations differing in any one
    element receive distinct fingerprints, and an element missing from the fingerprint is
    a contract defect. Deduplication itself is per-process and application-owned; this
    package ships no global instance registry, only the identity (DEC-0126).

    The frozen dataclass constructor is the unchecked trusted-internal path;
    :meth:`try_create` is the validating factory returning value-or-refusal.
    """

    formula_id: str
    contract_format_version: int
    parameters: Mapping[str, ExactRational]
    inputs: tuple[SeriesInput, ...]
    calendar_requirements: tuple[CalendarIdentity, ...]
    alignment_policy: AlignmentPolicy
    missing_value_policy: MissingValuePolicy
    warm_up: int
    output_schema: tuple[OutputChannel, ...]
    supported_modes: tuple[SupportedMode, ...]
    arithmetic_reference_configuration: ArithmeticReference
    emission_policy: EmissionPolicy | None = None
    warm_up_time_bound: Duration | None = None
    declared_budget: DeclaredBudget | None = None

    def __post_init__(self) -> None:
        # Deep-snapshot the parameter mapping so a later mutation of the caller's dict
        # can never reach into this frozen identity record.
        object.__setattr__(self, "parameters", _deep_freeze(self.parameters))

    @classmethod
    def try_create(
        cls,
        *,
        formula_id: object,
        contract_format_version: object,
        parameters: object,
        inputs: object,
        calendar_requirements: object,
        alignment_policy: object,
        missing_value_policy: object,
        warm_up: object,
        output_schema: object,
        supported_modes: object,
        arithmetic_reference_configuration: object,
        emission_policy: object = None,
        warm_up_time_bound: object = None,
        declared_budget: object = None,
    ) -> Result[ConfiguredIndicator]:
        """Validate the entire declared configuration and build a
        :class:`ConfiguredIndicator`, returning value-or-refusal.

        Every identity element is validated: ``formula_id`` a non-blank opaque token;
        ``contract_format_version`` a positive integer; ``parameters`` exact rationals
        only (a binary float is refused, FM-1); ``inputs`` one or more distinctly-named
        :class:`SeriesInput`\\ s; ``calendar_requirements`` a :class:`~qmf.core.CalendarIdentity`
        set; ``alignment_policy`` and ``missing_value_policy`` members of their sets;
        ``warm_up`` a non-negative integer count; ``output_schema`` one or more
        :class:`OutputChannel`\\ s; ``supported_modes`` one or more of the closed set;
        and ``arithmetic_reference_configuration`` an :class:`ArithmeticReference`. The
        optional ``emission_policy``, ``warm_up_time_bound`` (a
        :class:`~qmf.core.Duration`), and ``declared_budget`` enter identity when declared.
        """
        formula = _clean_str(formula_id)
        if formula is None:
            return _invalid(
                "formula_id",
                "a formula id is a non-empty opaque, stable token (never reused)",
                given=repr(formula_id),
            )
        version = _positive_int(contract_format_version)
        if version is None:
            return _invalid(
                "contract_format_version",
                "the per-configured-indicator contract format version is a positive "
                "integer ordinal; it mints on an output-changing arithmetic upgrade (DEC-0127)",
                given=repr(contract_format_version),
            )
        params = _coerce_parameters(parameters)
        if isinstance(params, TypedRefusal):
            return params
        resolved_inputs = _coerce_inputs(inputs)
        if isinstance(resolved_inputs, TypedRefusal):
            return resolved_inputs
        calendars = _coerce_calendars(calendar_requirements)
        if isinstance(calendars, TypedRefusal):
            return calendars
        alignment = _coerce_enum(AlignmentPolicy, alignment_policy)
        if alignment is None:
            return _invalid(
                "alignment_policy",
                "the alignment policy is one of the closed set; as-of is the only "
                "governed-evidence-legal value",
                given=repr(alignment_policy),
                allowed=[member.value for member in AlignmentPolicy],
            )
        missing = _coerce_enum(MissingValuePolicy, missing_value_policy)
        if missing is None:
            return _invalid(
                "missing_value_policy",
                "the missing-value policy is one of the closed set; forward-fill and "
                "interpolation are never legal (they are a policy rejection on compute)",
                given=repr(missing_value_policy),
                allowed=[member.value for member in MissingValuePolicy],
            )
        warm = _nonneg_int(warm_up)
        if warm is None:
            return _invalid(
                "warm_up",
                "warm-up is a non-negative integer count of completed input observations, "
                "identical across modes (never ticks, never a Duration)",
                given=repr(warm_up),
            )
        schema = _coerce_output_schema(output_schema)
        if isinstance(schema, TypedRefusal):
            return schema
        modes = _coerce_modes(supported_modes)
        if isinstance(modes, TypedRefusal):
            return modes
        if not isinstance(arithmetic_reference_configuration, ArithmeticReference):
            return _invalid(
                "arithmetic_reference_configuration",
                "the arithmetic-reference configuration is an ArithmeticReference record "
                "(the identity of registry:canonical_indicator_reference)",
                given=repr(arithmetic_reference_configuration),
            )
        optional = _coerce_optional_elements(emission_policy, warm_up_time_bound, declared_budget)
        if isinstance(optional, TypedRefusal):
            return optional
        emission, bound, budget = optional
        return Ok(
            cls(
                formula_id=formula,
                contract_format_version=version,
                parameters=params,
                inputs=resolved_inputs,
                calendar_requirements=calendars,
                alignment_policy=alignment,
                missing_value_policy=missing,
                warm_up=warm,
                output_schema=schema,
                supported_modes=modes,
                arithmetic_reference_configuration=arithmetic_reference_configuration,
                emission_policy=emission,
                warm_up_time_bound=bound,
                declared_budget=budget,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the entire declared
        configuration (CT-16; DEC-0126, DEC-0108).

        Every key in :data:`IDENTITY_ELEMENTS` is present, plus each declared member of
        :data:`OPTIONAL_IDENTITY_ELEMENTS`. An element missing here is a contract defect
        the conformance test catches. The ordered elements (``inputs``, ``output_schema``)
        keep their declared order; the unordered ones (``parameters``,
        ``calendar_requirements``, ``supported_modes``) are canonically ordered.
        """
        content: dict[str, object] = {
            "class": "configured-indicator",
            "formula_id": self.formula_id,
            "contract_format_version": self.contract_format_version,
            "parameters": {name: param.fp1_identity() for name, param in self.parameters.items()},
            "inputs": [series_input.fp1_identity() for series_input in self.inputs],
            "calendar_requirements": [
                calendar.fp1_identity() for calendar in self.calendar_requirements
            ],
            "alignment_policy": self.alignment_policy.value,
            "missing_value_policy": self.missing_value_policy.value,
            "warm_up": self.warm_up,
            "output_schema": [channel.fp1_identity() for channel in self.output_schema],
            "supported_modes": [mode.value for mode in self.supported_modes],
            "arithmetic_reference_configuration": (
                self.arithmetic_reference_configuration.fp1_identity()
            ),
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.emission_policy is not None:
            content["emission_policy"] = self.emission_policy.fp1_identity()
        if self.warm_up_time_bound is not None:
            content["warm_up_time_bound"] = self.warm_up_time_bound.fp1_identity()
        if self.declared_budget is not None:
            content["declared_budget"] = self.declared_budget.fp1_identity()
        return content

    def fp1(self) -> Result[Fingerprint]:
        """The configuration's ``fp1`` fingerprint — its only dedup identity (DEC-0126).

        Computed by the single ``qmf-core`` fingerprint function over the canonical
        identity content, so two conformant producers and two merging sandboxes agree on
        identity by construction. The content is canonical by construction, so this
        succeeds; the ``Result`` return keeps the one identity contract uniform.
        """
        return fingerprint(self)

    def identity_element_names(self) -> tuple[str, ...]:
        """The identity elements this configuration actually contributes to its ``fp1``
        (CT-16 conformance; DEC-0126).

        Every required :data:`IDENTITY_ELEMENTS` key plus each declared optional element —
        the set a conformance harness checks against the fingerprint content so no
        declared element silently drifts out of identity.
        """
        present_optional = tuple(
            name for name in OPTIONAL_IDENTITY_ELEMENTS if name in self.fp1_identity()
        )
        return IDENTITY_ELEMENTS + present_optional


def _coerce_output_schema(value: object) -> tuple[OutputChannel, ...] | TypedRefusal:
    """Resolve the ordered output schema: a sequence of one or more distinctly-named
    :class:`OutputChannel`\\ s, else a refusal (order is significant; DEC-0126)."""
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "output_schema",
            "the output schema is an order-significant sequence of OutputChannels",
            given=repr(value),
        )
    resolved: list[OutputChannel] = []
    seen: set[str] = set()
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, OutputChannel):
            return _invalid(
                "output_schema",
                "each output channel is an OutputChannel; build it via OutputChannel.try_create",
                index=index,
                given=repr(item),
            )
        if item.name in seen:
            return _invalid(
                "output_schema",
                "output channel names are unique within a configuration's schema",
                index=index,
                name=item.name,
            )
        seen.add(item.name)
        resolved.append(item)
    if not resolved:
        return _invalid("output_schema", "a configuration declares one or more output channels")
    return tuple(resolved)


def _coerce_optional_elements(
    emission_policy: object, warm_up_time_bound: object, declared_budget: object
) -> tuple[EmissionPolicy | None, Duration | None, DeclaredBudget | None] | TypedRefusal:
    """Resolve the three optional identity-bearing elements, each ``None`` when absent
    and its declared type when present, else a refusal."""
    emission: EmissionPolicy | None = None
    if emission_policy is not None:
        if not isinstance(emission_policy, EmissionPolicy):
            return _invalid(
                "emission_policy",
                "the emission policy is an EmissionPolicy (bar-closed vs in-progress plus "
                "evidence granularity); omit it when undeclared",
                given=repr(emission_policy),
            )
        emission = emission_policy
    bound: Duration | None = None
    if warm_up_time_bound is not None:
        if not isinstance(warm_up_time_bound, Duration):
            return _invalid(
                "warm_up_time_bound",
                "the warm-up time bound is a Duration; it is null exactly when the BarSpec "
                "is event-driven",
                given=repr(warm_up_time_bound),
            )
        bound = warm_up_time_bound
    budget: DeclaredBudget | None = None
    if declared_budget is not None:
        if not isinstance(declared_budget, DeclaredBudget):
            return _invalid(
                "declared_budget",
                "the declared budget is a DeclaredBudget (the light-claim bounds); omit it "
                "for a heavy-by-default configuration",
                given=repr(declared_budget),
            )
        budget = declared_budget
    return emission, bound, budget
