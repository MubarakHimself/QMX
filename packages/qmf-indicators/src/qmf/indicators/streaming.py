"""CT-16 — streaming mode, the tier-2 equality law, and restore-equivalence
(COMP-QMF-INDICATORS; Story 7.4).

Streaming mode computes a configured indicator over **incremental updates** whose
numbers are **provably equal to batch by construction**, with a versioned
snapshot/restore. Three laws this module lands (DEC-0126, DEC-0113, DEC-0103):

* **The one named stateful class.** :class:`StreamingIndicator` is the sole stateful
  class in the concurrency stance: exactly one feeder — **one WriterId holder**, not
  one input stream — and unlimited readers. Every streaming output carries the input
  sequence number that produced it (minted by a :class:`~qmf.core.WriterSequencer`
  over the held :class:`~qmf.core.WriterId`), it exposes :meth:`~StreamingIndicator.health`
  as an AD-14 long-lived-state component, and instance count scales with distinct
  configurations, not consumers (an instance carries its configuration fingerprint;
  readers never mint one).

* **The tier-2 equality law.** Where both modes are declared, streaming and batch
  results are equal same-process, same-build, under a per-configuration integer-ULP
  comparator (default 0), over canonical inputs = (series, exact parameters, cold
  initial state). The equality is **by construction**: a streaming instance holds the
  accumulated observations and recomputes each update through the *identical*
  canonical-arithmetic :class:`~qmf.indicators.batch.BatchKernel` the batch path uses
  (:func:`~qmf.indicators.batch.compute_batch`), so there is no second arithmetic that
  could drift. The seeding rule (:data:`SEEDING_RULE`) and the
  leading-undefined-prefix-to-not-ready mapping (:data:`LEADING_UNDEFINED_MAPPING`)
  are declared contract surface. Cross-OS or cross-build agreement is **never** this
  gate — it is a separate registered comparison artifact
  (:data:`CROSS_TUPLE_IS_A_REGISTERED_ARTIFACT`).

* **Restore-equivalence.** A :class:`StreamingSnapshot` is a serialized contract with
  its **own** format version (:data:`SNAPSHOT_FORMAT_VERSION`, distinct from the CT-16
  contract format version) scoped to a declared ``(OS, arithmetic-reference build)``
  tuple (:class:`SnapshotScope`). Restore-then-N-updates equals
  cold-warm-then-the-same-N-updates by construction (the snapshot captures the whole
  accumulated state and the sequencer position), and a result computed from restored
  state carries the snapshot fingerprint as an input fingerprint. Restoring across a
  different ``(OS, arithmetic-reference build)`` tuple is an ``unavailable dependency``
  refusal (FM-7).

Default-deny holds: this module imports **only** ``qmf.core`` and this package's own
modules; no reference object crosses a public boundary. The scope tuple is **injected**
at creation and restore (the composition root supplies the OS and the arithmetic-
reference build) — never read ambiently — so the module reads no clock, platform, or
entropy below the composition root. Public value types are frozen dataclasses; the one
stateful class owns mutable state deliberately (DEC-0113); every operation succeeds or
RETURNS a CT-04 refusal (DEC-0101, DEC-0109, DEC-0120).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Final, cast

from qmf.core import (
    Fingerprint,
    Instant,
    Ok,
    RefusalCategory,
    Result,
    ResultLabel,
    Retryability,
    TypedRefusal,
    World,
    WriterId,
    WriterSequencer,
    fingerprint,
    is_refusal,
)
from qmf.indicators.batch import BatchKernel, BatchResult, compute_batch
from qmf.indicators.configured_indicator import ConfiguredIndicator, SupportedMode
from qmf.indicators.series import (
    IndicatorSeries,
    InputSeries,
    PresenceState,
    encode_int64_values,
    presence_code,
    presence_from_code,
)

__all__ = [
    "CROSS_TUPLE_IS_A_REGISTERED_ARTIFACT",
    "DEFAULT_MODE_EQUALITY_ULPS",
    "LEADING_UNDEFINED_MAPPING",
    "SEEDING_RULE",
    "SNAPSHOT_FORMAT_VERSION",
    "ChannelSample",
    "ModeEqualityComparator",
    "SnapshotScope",
    "StreamingHealth",
    "StreamingIndicator",
    "StreamingObservation",
    "StreamingSample",
    "StreamingSnapshot",
    "assert_mode_equality",
    "series_equal_within_ulps",
]

# The snapshot serialized-contract format version — the version of the SNAPSHOT
# envelope this module serializes, stamped into every snapshot and distinct from a
# configuration's CT-16 contract format version (DEC-0103; versioning-from-birth L15).
# An incompatible envelope change mints the next version.
SNAPSHOT_FORMAT_VERSION: Final[int] = 1

# The per-configuration equality-law comparator default: exact equality (DEC-0126,
# DEC-0127). Tolerances are integer ULP counts at the output scale, never decimal text
# and never floats; a configuration declares its own comparator at the composition
# root / conformance harness, defaulting to this.
DEFAULT_MODE_EQUALITY_ULPS: Final[int] = 0

# The seeding rule — declared contract surface for the equality law (DEC-0126). The
# canonical input set is (series, exact parameters, cold initial state); "cold initial
# state" is an empty accumulation — a freshly created StreamingIndicator has seen no
# observations and its sequencer starts at zero.
SEEDING_RULE: Final[str] = (
    "cold-initial-state: a streaming instance begins with an empty accumulation and a "
    "zero-based sequencer; the canonical input set is (series, exact parameters, cold "
    "initial state)"
)

# The leading-undefined-prefix-to-not-ready mapping — declared contract surface
# (DEC-0126). The reference's leading-undefined prefix (its lookback) maps to a marked
# not_ready value, identical across modes; during warm-up the output is never a number.
LEADING_UNDEFINED_MAPPING: Final[str] = (
    "leading-undefined-prefix-to-not-ready: the reference's leading-undefined prefix "
    "maps to a marked not_ready value, identical across batch and streaming; a marked "
    "not_ready value is never a number"
)

# Declared contract surface: cross-OS or cross-build agreement is NEVER the equality
# gate — it is a separate AD-23 registered comparison artifact with its own integer-ULP
# tolerances (DEC-0126, DEC-0127). The same-process/same-build equality law is the gate.
CROSS_TUPLE_IS_A_REGISTERED_ARTIFACT: Final[bool] = True


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a streaming operation returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT, retryability=Retryability.NO, context=context
    )


def _unsupported(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unsupported capability`` refusal a mode/feeder guard returns (CT-04)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNSUPPORTED_CAPABILITY,
        retryability=Retryability.NO,
        context=context,
    )


def _unavailable(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``unavailable dependency`` refusal the cross-tuple restore returns (FM-7)."""
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context=context,
    )


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _nonneg_int(value: object) -> int | None:
    """Return ``value`` as a genuine non-negative ``int`` (a ``bool`` is rejected), else
    ``None`` — a sequence counter and an observation count are non-negative integers."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


# --- the snapshot scope tuple -----------------------------------------------


@dataclass(frozen=True, slots=True)
class SnapshotScope:
    """The declared ``(OS, arithmetic-reference build)`` scope of a snapshot (CT-16; FM-7).

    A snapshot is a serialized contract scoped to exactly this tuple: the ``os`` the
    state was produced on and the ``arithmetic_reference_build`` (the pinned canonical
    reference's build identity, e.g. ``ta-lib==0.7.1``). Restoring on a different tuple
    is an ``unavailable dependency`` refusal, because the reference's floating-point
    arithmetic — and therefore the resumed state — is only attestable within one tuple.
    The tuple is **injected** by the composition root, never read ambiently.
    """

    os: str
    arithmetic_reference_build: str

    @classmethod
    def try_create(cls, os: object, arithmetic_reference_build: object) -> Result[SnapshotScope]:
        """Validate and build a :class:`SnapshotScope`, returning value-or-refusal."""
        os_token = _clean_str(os)
        if os_token is None:
            return _invalid(
                "os",
                "a snapshot scope names a non-empty OS identity (injected, never read ambiently)",
                given=repr(os),
            )
        build_token = _clean_str(arithmetic_reference_build)
        if build_token is None:
            return _invalid(
                "arithmetic_reference_build",
                "a snapshot scope names a non-empty arithmetic-reference build identity",
                given=repr(arithmetic_reference_build),
            )
        return Ok(cls(os=os_token, arithmetic_reference_build=build_token))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this scope tuple."""
        return {
            "class": "snapshot-scope",
            "os": self.os,
            "arithmetic_reference_build": self.arithmetic_reference_build,
        }


# --- one incremental update --------------------------------------------------


@dataclass(frozen=True, slots=True)
class StreamingObservation:
    """One input column's incremental update at a single position (CT-16; DEC-0126).

    The value the feeder pushes for one declared input at the next position: a scaled
    integer ``value`` at the column's fixed out-of-band scale (declared at instance
    creation), a ``presence`` state, and the ``knowable_at`` instant — the earliest
    instant at which the observation was knowable. A non-present observation carries a
    placeholder ``value`` the presence map forbids reading as data (NaN and sentinels
    are prohibited).
    """

    value: int
    presence: PresenceState
    knowable_at: Instant

    @classmethod
    def try_create(
        cls, value: object, presence: object, knowable_at: object
    ) -> Result[StreamingObservation]:
        """Validate and build a :class:`StreamingObservation`, returning value-or-refusal."""
        if isinstance(value, bool) or not isinstance(value, int):
            return _invalid("value", "an observation value is a scaled integer", given=repr(value))
        resolved_presence = _coerce_presence_state(presence)
        if resolved_presence is None:
            return _invalid(
                "presence",
                "the presence is a registry:presence_map_states value",
                given=repr(presence),
            )
        if not isinstance(knowable_at, Instant):
            return _invalid("knowable_at", "the knowable-at is an Instant", given=repr(knowable_at))
        return Ok(cls(value=value, presence=resolved_presence, knowable_at=knowable_at))


def _coerce_presence_state(value: object) -> PresenceState | None:
    """Resolve a presence state (a member or its string value), or ``None``."""
    if isinstance(value, PresenceState):
        return value
    if isinstance(value, str):
        try:
            return PresenceState(value)
        except ValueError:
            return None
    return None


# --- one streaming output sample --------------------------------------------


@dataclass(frozen=True, slots=True)
class ChannelSample:
    """One output channel's newest streaming value (CT-16; DEC-0126).

    ``presence`` is the channel's presence state at the newest position; ``value`` is the
    scaled integer at ``scale`` when present or provisional, and ``None`` at a not-ready,
    gap, or absent-by-schedule position (never a NaN or sentinel). ``knowable_at`` is the
    position's knowable-at instant.
    """

    presence: PresenceState
    scale: int
    value: int | None
    knowable_at: Instant


@dataclass(frozen=True, slots=True)
class StreamingSample:
    """The output of one streaming update (CT-16; DEC-0126, DEC-0106).

    Every streaming output carries the ``sequence`` — the input sequence number that
    produced it, minted by the instance's :class:`~qmf.core.WriterSequencer` over its one
    held :class:`~qmf.core.WriterId`. ``position`` is the newest index in the accumulated
    series; ``channels`` is the per-output-channel newest value. Streaming updates are
    not individually evidence-bearing — a governed result is taken through
    :meth:`StreamingIndicator.result` — so a sample carries no result label.
    """

    sequence: int
    position: int
    channels: Mapping[str, ChannelSample]


# --- the health report ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class StreamingHealth:
    """The streaming instance's typed health report (AD-14; DEC-0113).

    Renderable and safe to expose as a metric or log line: only the configuration
    fingerprint, the held writer's ``(machine, role, stream, boot_epoch_id)`` identity,
    counts, the readiness flag, the snapshot fingerprint a restored instance was resumed
    from (or ``None``), and the injected scope. It carries no value data and no secret.
    """

    configuration_fingerprint: str
    machine: str
    role: str
    stream: str
    boot_epoch_id: str
    observations_seen: int
    next_sequence: int
    ready: bool
    restored_from: str | None
    os: str
    arithmetic_reference_build: str


# --- the equality-law comparator --------------------------------------------


@dataclass(frozen=True, slots=True)
class ModeEqualityComparator:
    """A configuration's declared integer-ULP mode-equality comparator (CT-16; DEC-0127).

    ``ulps`` is an integer count of units in the last place at the output scale — a
    scaled-integer tolerance, never decimal text and never a float. The default is 0
    (exact equality). The comparator is per configuration; it is declared at the
    composition root / conformance harness, not folded into the fp1 identity record.
    """

    ulps: int = DEFAULT_MODE_EQUALITY_ULPS

    @classmethod
    def try_create(
        cls, ulps: object = DEFAULT_MODE_EQUALITY_ULPS
    ) -> Result[ModeEqualityComparator]:
        """Validate and build a :class:`ModeEqualityComparator`, returning value-or-refusal."""
        count = _nonneg_int(ulps)
        if count is None:
            return _invalid(
                "ulps",
                "the mode-equality comparator is a non-negative integer ULP count "
                "(never decimal text, never a float)",
                given=repr(ulps),
            )
        return Ok(cls(ulps=count))


def series_equal_within_ulps(
    left: object, right: object, ulps: int = DEFAULT_MODE_EQUALITY_ULPS
) -> Result[bool]:
    """Whether two output series are equal within an integer-ULP tolerance (CT-16; DEC-0126).

    Presence maps are compared first (position for position); values are then compared
    **only at present positions**, exactly across scales, and are equal when they differ
    by at most ``ulps`` units at the finer of the two scales. ``ulps = 0`` is exact
    equality — the same rule :meth:`~qmf.indicators.series.IndicatorSeries.equals`
    applies. A ``not_ready`` / ``gap`` / ``absent_by_schedule`` position carries no
    number, so no value is read there.
    """
    if not isinstance(left, IndicatorSeries) or not isinstance(right, IndicatorSeries):
        return _invalid(
            "series", "the equality law compares two IndicatorSeries", given=repr((left, right))
        )
    tolerance = _nonneg_int(ulps)
    if tolerance is None:
        return _invalid("ulps", "the ULP tolerance is a non-negative integer", given=repr(ulps))
    if left.presence != right.presence:
        return Ok(False)
    # Compare exactly across scales on a common basis of 10**(left.scale + right.scale):
    # each side is scaled by the OTHER's factor. One ULP is one unit at the finer (larger)
    # scale, which on the common basis is 10**min(left.scale, right.scale); the integer
    # tolerance is scaled to that basis so the comparison stays exact integer arithmetic.
    left_factor = 10**right.scale
    right_factor = 10**left.scale
    common_ulp = 10 ** min(left.scale, right.scale)
    allowed = tolerance * common_ulp
    for index, state in enumerate(left.presence):
        if state is not PresenceState.PRESENT:
            continue
        delta = abs(left.value_at(index) * left_factor - right.value_at(index) * right_factor)
        if delta > allowed:
            return Ok(False)
    return Ok(True)


def assert_mode_equality(
    configuration: object,
    batch_result: object,
    streaming_result: object,
    comparator: ModeEqualityComparator | None = None,
) -> Result[bool]:
    """Run the tier-2 equality law over a batch and a streaming result (CT-16; DEC-0126).

    The law binds only when the configuration declares **both** modes. It compares the
    two results' output channels under the per-configuration integer-ULP comparator
    (default 0): the channel sets must match, and each channel's series must be equal
    within tolerance (presence maps first, then values at present positions). Returns
    ``Ok(True)`` when they agree, ``Ok(False)`` at the first channel that does not, or an
    ``invalid input`` refusal for a malformed argument or a configuration that does not
    declare both modes. Same-process, same-build only — cross-OS / cross-build agreement
    is a separate registered artifact, never this gate.
    """
    if not isinstance(configuration, ConfiguredIndicator):
        return _invalid(
            "configuration", "a ConfiguredIndicator is required", given=repr(configuration)
        )
    both = {SupportedMode.BATCH, SupportedMode.STREAMING}
    if not both.issubset(set(configuration.supported_modes)):
        return _invalid(
            "supported_modes",
            "the equality law binds only when a configuration declares both batch and "
            "streaming modes",
            declared=[mode.value for mode in configuration.supported_modes],
        )
    if not isinstance(batch_result, BatchResult) or not isinstance(streaming_result, BatchResult):
        return _invalid(
            "results", "the equality law compares two BatchResults (batch and streaming)"
        )
    resolved = comparator if comparator is not None else ModeEqualityComparator()
    if set(batch_result.outputs) != set(streaming_result.outputs):
        return Ok(False)
    for channel, batch_series in batch_result.outputs.items():
        streaming_series = streaming_result.outputs[channel]
        equal = series_equal_within_ulps(batch_series, streaming_series, resolved.ulps)
        if is_refusal(equal):  # pragma: no cover - series come from compute_batch, always valid
            return equal
        if equal.value is False:
            return Ok(False)
    return Ok(True)


# --- the serialized snapshot contract ---------------------------------------


@dataclass(frozen=True, slots=True)
class StreamingSnapshot:
    """A streaming state snapshot — a serialized contract with its own format version
    (CT-16; DEC-0126, DEC-0103).

    Captures the whole resumable state: the ``configuration_fingerprint`` the state
    belongs to, the accumulated per-column :class:`~qmf.indicators.series.InputSeries`,
    the held :class:`~qmf.core.WriterId` and the ``next_sequence`` its sequencer will
    mint, all scoped to a declared ``(OS, arithmetic-reference build)`` :class:`SnapshotScope`.
    :meth:`to_mapping` / :meth:`from_mapping` are the serialized form (JSON-safe integers
    and strings), and :meth:`fingerprint` is the snapshot's ``fp1`` — the value a result
    from restored state carries as an input fingerprint.
    """

    format_version: int
    scope: SnapshotScope
    configuration_fingerprint: Fingerprint
    writer_id: WriterId
    next_sequence: int
    columns: Mapping[str, InputSeries]

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this snapshot."""
        return {
            "class": "streaming-snapshot",
            "format_version": self.format_version,
            "scope": self.scope.fp1_identity(),
            "configuration_fingerprint": self.configuration_fingerprint.value,
            "writer_id": {
                "machine": self.writer_id.machine,
                "role": self.writer_id.role,
                "stream": self.writer_id.stream,
                "boot_epoch_id": self.writer_id.boot_epoch_id,
            },
            "next_sequence": self.next_sequence,
            "columns": {name: self.columns[name].fp1_identity() for name in sorted(self.columns)},
        }

    def fingerprint(self) -> Result[Fingerprint]:
        """The snapshot's ``fp1`` fingerprint, computed by the single qmf-core seam."""
        return fingerprint(self)

    def to_mapping(self) -> dict[str, object]:
        """The snapshot's serialized form — a JSON-safe mapping (the serialized contract).

        Every value is an integer or a string: bulk bytes are hex-encoded, presence maps
        are their integer codes, and knowable-at is int64 UTC nanoseconds. The composition
        root serializes this mapping (to JSON, Parquet, or bytes) without this package
        naming a serialization format. :meth:`from_mapping` reverses it exactly.
        """
        return {
            "class": "streaming-snapshot",
            "format_version": self.format_version,
            "scope": {
                "os": self.scope.os,
                "arithmetic_reference_build": self.scope.arithmetic_reference_build,
            },
            "configuration_fingerprint": self.configuration_fingerprint.value,
            "writer_id": {
                "machine": self.writer_id.machine,
                "role": self.writer_id.role,
                "stream": self.writer_id.stream,
                "boot_epoch_id": self.writer_id.boot_epoch_id,
            },
            "next_sequence": self.next_sequence,
            "columns": {
                name: {
                    "values_hex": self.columns[name].values.hex(),
                    "scale": self.columns[name].scale,
                    "presence": [presence_code(state) for state in self.columns[name].presence],
                    "knowable_at_ns": [
                        instant.value_ns for instant in self.columns[name].knowable_at
                    ],
                }
                for name in self.columns
            },
        }

    @classmethod
    def from_mapping(cls, mapping: object) -> Result[StreamingSnapshot]:
        """Rebuild a :class:`StreamingSnapshot` from its serialized form, value-or-refusal.

        Validates the format version, the scope tuple, the configuration fingerprint, the
        writer id, the sequence counter, and each accumulated column (hex bytes, scale,
        integer-coded presence, knowable-at nanoseconds), reconstructing the pinned
        :class:`~qmf.indicators.series.InputSeries` for each column.
        """
        if not isinstance(mapping, Mapping):
            return _invalid(
                "snapshot", "a snapshot is a mapping", given=repr(type(mapping).__name__)
            )
        body = cast("Mapping[str, object]", mapping)
        version = body.get("format_version")
        if version != SNAPSHOT_FORMAT_VERSION:
            return _invalid(
                "format_version",
                "the snapshot format version does not match this build's",
                given=repr(version),
                expected=SNAPSHOT_FORMAT_VERSION,
            )
        scope = _restore_scope(body.get("scope"))
        if isinstance(scope, TypedRefusal):
            return scope
        config_fp = Fingerprint.try_create(body.get("configuration_fingerprint"))
        if is_refusal(config_fp):
            return _invalid(
                "configuration_fingerprint",
                "the snapshot names a valid configuration fingerprint",
                given=repr(body.get("configuration_fingerprint")),
            )
        writer = _restore_writer(body.get("writer_id"))
        if isinstance(writer, TypedRefusal):
            return writer
        next_sequence = _nonneg_int(body.get("next_sequence"))
        if next_sequence is None:
            return _invalid(
                "next_sequence",
                "the snapshot names a non-negative sequence counter",
                given=repr(body.get("next_sequence")),
            )
        columns = _restore_columns(body.get("columns"))
        if isinstance(columns, TypedRefusal):
            return columns
        return Ok(
            cls(
                format_version=SNAPSHOT_FORMAT_VERSION,
                scope=scope,
                configuration_fingerprint=config_fp.value,
                writer_id=writer,
                next_sequence=next_sequence,
                columns=columns,
            )
        )


def _restore_scope(value: object) -> SnapshotScope | TypedRefusal:
    """Rebuild a :class:`SnapshotScope` from its serialized mapping, or a refusal."""
    if not isinstance(value, Mapping):
        return _invalid("scope", "the snapshot scope is a mapping", given=repr(value))
    body = cast("Mapping[str, object]", value)
    scope = SnapshotScope.try_create(body.get("os"), body.get("arithmetic_reference_build"))
    if is_refusal(scope):
        return scope
    return scope.value


def _restore_writer(value: object) -> WriterId | TypedRefusal:
    """Rebuild a :class:`~qmf.core.WriterId` from its serialized mapping, or a refusal."""
    if not isinstance(value, Mapping):
        return _invalid("writer_id", "the snapshot writer id is a mapping", given=repr(value))
    body = cast("Mapping[str, object]", value)
    writer = WriterId.try_create(
        body.get("machine"), body.get("role"), body.get("stream"), body.get("boot_epoch_id")
    )
    if is_refusal(writer):
        return _invalid(
            "writer_id", "the snapshot names a valid writer id", cause=dict(writer.context)
        )
    return writer.value


def _restore_columns(value: object) -> dict[str, InputSeries] | TypedRefusal:
    """Rebuild the accumulated per-column :class:`~qmf.indicators.series.InputSeries` set."""
    if not isinstance(value, Mapping):
        return _invalid("columns", "the snapshot columns are a mapping", given=repr(value))
    body = cast("Mapping[object, object]", value)
    columns: dict[str, InputSeries] = {}
    for name, column in body.items():
        if not isinstance(name, str):
            return _invalid("columns", "each column name is a string", given=repr(name))
        restored = _restore_column(name, column)
        if isinstance(restored, TypedRefusal):
            return restored
        columns[name] = restored
    return columns


def _restore_column(name: str, value: object) -> InputSeries | TypedRefusal:
    """Rebuild one accumulated column from its serialized mapping, or a refusal."""
    if not isinstance(value, Mapping):
        return _invalid("columns", "each column is a mapping", column=name, given=repr(value))
    body = cast("Mapping[str, object]", value)
    values_hex = body.get("values_hex")
    if not isinstance(values_hex, str):
        return _invalid("columns", "a column's values are hex-encoded bytes", column=name)
    try:
        raw = bytes.fromhex(values_hex)
    except ValueError:
        return _invalid("columns", "a column's values_hex is not valid hex", column=name)
    presence_codes = body.get("presence")
    if isinstance(presence_codes, (str, bytes)) or not isinstance(presence_codes, Sequence):
        return _invalid(
            "columns", "a column's presence is a sequence of integer codes", column=name
        )
    presence: list[PresenceState] = []
    for code in cast("Sequence[object]", presence_codes):
        state = presence_from_code(code)
        if state is None:
            return _invalid("columns", "a presence code is unknown", column=name, code=repr(code))
        presence.append(state)
    knowable_ns = body.get("knowable_at_ns")
    if isinstance(knowable_ns, (str, bytes)) or not isinstance(knowable_ns, Sequence):
        return _invalid("columns", "a column's knowable-at is a sequence of int64 ns", column=name)
    knowable_at: list[Instant] = []
    for ns in cast("Sequence[object]", knowable_ns):
        instant = Instant.try_create(ns)
        if is_refusal(instant):
            return _invalid(
                "columns", "a knowable-at nanosecond is invalid", column=name, given=repr(ns)
            )
        knowable_at.append(instant.value)
    return _built_or_refusal(InputSeries.try_create(raw, body.get("scale"), presence, knowable_at))


def _built_or_refusal(result: Result[InputSeries]) -> InputSeries | TypedRefusal:
    """Unwrap a series ``Result`` to the value or the refusal (never an ``Ok`` wrapper)."""
    if is_refusal(result):
        return result
    return result.value


# --- the one named stateful class -------------------------------------------


class StreamingIndicator:
    """The one named stateful streaming class (CT-16 concurrency stance; DEC-0113, DEC-0126).

    Exactly one feeder — **one WriterId holder**, not one input stream — and unlimited
    readers. Constructed through :meth:`try_create` from a both-modes-or-streaming
    configuration, the canonical-arithmetic :class:`~qmf.indicators.batch.BatchKernel`,
    the world, the feeder's one :class:`~qmf.core.WriterId`, the injected
    :class:`SnapshotScope`, and each declared input's fixed out-of-band scale. Each
    :meth:`update` appends one incremental observation per declared input and returns a
    :class:`StreamingSample` carrying the input sequence number that produced it; the
    numbers are **equal to batch by construction** because every update recomputes
    through the identical batch kernel over the accumulated observations.

    Deliberately not a frozen dataclass: it owns mutable accumulation and a sequencer
    (DEC-0113). Only :meth:`update` mutates (the single feeder path); :meth:`latest`,
    :meth:`result`, :meth:`health`, :meth:`snapshot`, and
    :meth:`configuration_fingerprint` are reader paths that never mutate, so an instance
    serves unlimited readers. Instance count scales with distinct configurations, not
    consumers — an instance carries its configuration fingerprint and a reader mints none.
    """

    __slots__ = (
        "_columns",
        "_configuration",
        "_configuration_fingerprint",
        "_input_scales",
        "_kernel",
        "_latest",
        "_names",
        "_restored_from",
        "_scope",
        "_sequencer",
        "_world",
        "_writer_id",
    )

    _configuration: ConfiguredIndicator
    _configuration_fingerprint: Fingerprint
    _kernel: BatchKernel
    _world: World
    _writer_id: WriterId
    _scope: SnapshotScope
    _input_scales: Mapping[str, int]
    _names: tuple[str, ...]
    _columns: dict[str, tuple[list[int], list[PresenceState], list[Instant]]]
    _sequencer: WriterSequencer
    _restored_from: Fingerprint | None
    _latest: StreamingSample | None

    def __init__(
        self,
        configuration: ConfiguredIndicator,
        configuration_fingerprint: Fingerprint,
        kernel: BatchKernel,
        world: World,
        writer_id: WriterId,
        scope: SnapshotScope,
        input_scales: Mapping[str, int],
        *,
        start_sequence: int = 0,
        restored_from: Fingerprint | None = None,
    ) -> None:
        # Unchecked trusted-internal constructor; callers use try_create / restore.
        self._configuration = configuration
        self._configuration_fingerprint = configuration_fingerprint
        self._kernel = kernel
        self._world = world
        self._writer_id = writer_id
        self._scope = scope
        self._input_scales = dict(input_scales)
        self._names = tuple(series_input.name for series_input in configuration.inputs)
        self._columns = {name: ([], [], []) for name in self._names}
        self._sequencer = WriterSequencer(writer_id, start=start_sequence)
        self._restored_from = restored_from
        self._latest = None

    @classmethod
    def try_create(
        cls,
        configuration: object,
        *,
        kernel: object,
        world: object,
        writer_id: object,
        scope: object,
        input_scales: object,
    ) -> Result[StreamingIndicator]:
        """Validate the wiring and build a cold :class:`StreamingIndicator`, value-or-refusal.

        The configuration must declare streaming mode; the ``kernel`` must be a
        :class:`~qmf.indicators.batch.BatchKernel`; ``world`` a member of the closed set;
        ``writer_id`` the feeder's one :class:`~qmf.core.WriterId`; ``scope`` an injected
        :class:`SnapshotScope`; and ``input_scales`` a scale for every declared input.
        """
        if not isinstance(configuration, ConfiguredIndicator):
            return _invalid(
                "configuration", "a ConfiguredIndicator is required", given=repr(configuration)
            )
        if SupportedMode.STREAMING not in configuration.supported_modes:
            return _unsupported(
                "supported_modes",
                "the configuration does not declare streaming mode",
                declared=[mode.value for mode in configuration.supported_modes],
            )
        if not isinstance(kernel, BatchKernel):
            return _invalid("kernel", "a BatchKernel is required", given=repr(kernel))
        resolved_world = _coerce_world(world)
        if resolved_world is None:
            return _invalid(
                "world",
                "world is one of the closed set",
                given=repr(world),
                allowed=[member.value for member in World],
            )
        if not isinstance(writer_id, WriterId):
            return _invalid(
                "writer_id", "the one feeder is identified by a WriterId", given=repr(writer_id)
            )
        if not isinstance(scope, SnapshotScope):
            return _invalid(
                "scope", "the (OS, arithmetic-reference build) scope is injected", given=repr(scope)
            )
        scales = _coerce_input_scales(configuration, input_scales)
        if isinstance(scales, TypedRefusal):
            return scales
        producer = configuration.fp1()
        if is_refusal(producer):  # pragma: no cover - config content is canonical by construction
            return producer
        return Ok(
            cls(
                configuration,
                producer.value,
                kernel,
                resolved_world,
                writer_id,
                scope,
                scales,
            )
        )

    def configuration_fingerprint(self) -> Fingerprint:
        """The configuration's ``fp1`` — the instance's dedup identity (DEC-0126).

        Instance count scales with distinct configurations, not consumers: two instances
        for the same fingerprint are interchangeable, and a reader never mints one.
        """
        return self._configuration_fingerprint

    @property
    def observations_seen(self) -> int:
        """The number of positions accumulated so far."""
        return len(self._columns[self._names[0]][0])

    def update(self, observations: object, *, feeder: object = None) -> Result[StreamingSample]:
        """Append one incremental observation per declared input and emit the newest sample.

        ``observations`` maps every declared input name to a :class:`StreamingObservation`.
        The single-feeder law binds: if ``feeder`` is supplied it must equal the held
        :class:`~qmf.core.WriterId`, else the update is refused — a second feeder is not
        permitted (one WriterId holder). The instance mints the input sequence number from
        its sequencer over the position's knowable-at (the max across inputs), recomputes
        through the batch kernel over the accumulated observations, and returns a
        :class:`StreamingSample` carrying that sequence number. Equal to batch by
        construction — the identical kernel over the identical accumulated series.
        """
        if feeder is not None:
            if not isinstance(feeder, WriterId):
                return _invalid(
                    "feeder", "the feeder is identified by a WriterId", given=repr(feeder)
                )
            if feeder != self._writer_id:
                return _unsupported(
                    "feeder",
                    "exactly one feeder is permitted — one WriterId holder; a second feeder "
                    "is refused",
                    held=self._writer_id.order_tuple(),
                    given=feeder.order_tuple(),
                )
        resolved = _coerce_observations(self._names, observations)
        if isinstance(resolved, TypedRefusal):
            return resolved
        position_knowable = max(
            (obs.knowable_at for obs in resolved.values()), key=lambda instant: instant.value_ns
        )
        for name in self._names:
            observation = resolved[name]
            values, presence, knowable_at = self._columns[name]
            values.append(observation.value)
            presence.append(observation.presence)
            knowable_at.append(observation.knowable_at)
        recomputed = self._recompute()
        if isinstance(recomputed, TypedRefusal):
            # The single feeder path rolls the position back so a refused update leaves the
            # accumulation exactly as it was — a refusal is never a partial mutation.
            for name in self._names:
                values, presence, knowable_at = self._columns[name]
                values.pop()
                presence.pop()
                knowable_at.pop()
            return recomputed
        key = self._sequencer.mint(position_knowable)
        sample = _newest_sample(self._configuration, recomputed, key.sequence)
        self._latest = sample
        return Ok(sample)

    def latest(self) -> Result[StreamingSample]:
        """The most recent :class:`StreamingSample`, or a refusal before any update (reader)."""
        if self._latest is None:
            return _invalid(
                "latest", "no update has been fed yet; the stream has produced no sample"
            )
        return Ok(self._latest)

    def result(self) -> Result[BatchResult]:
        """The full governed result over the accumulated observations (reader).

        Recomputes through the identical batch kernel, so the result equals batch over the
        same series by construction — the surface the tier-2 equality law compares. A
        result computed from **restored** state carries the snapshot fingerprint as an
        input fingerprint (restore-equivalence provenance); a cold instance's result does
        not. Refuses before any update (a batch is over a non-empty series).
        """
        if self.observations_seen == 0:
            return _invalid(
                "result", "no observation has been fed yet; there is nothing to compute"
            )
        recomputed = self._recompute()
        if isinstance(recomputed, TypedRefusal):  # pragma: no cover - update guards the inputs
            return recomputed
        if self._restored_from is None:
            return Ok(recomputed)
        return _augment_label_with_snapshot(recomputed, self._restored_from)

    def health(self) -> StreamingHealth:
        """A typed health report — configuration and writer identity, counts, readiness
        (AD-14; DEC-0113). Carries no value data and no secret (reader)."""
        ready = self._latest is not None and all(
            channel.presence is PresenceState.PRESENT for channel in self._latest.channels.values()
        )
        return StreamingHealth(
            configuration_fingerprint=self._configuration_fingerprint.value,
            machine=self._writer_id.machine,
            role=self._writer_id.role,
            stream=self._writer_id.stream,
            boot_epoch_id=self._writer_id.boot_epoch_id,
            observations_seen=self.observations_seen,
            next_sequence=self._sequencer.next_sequence,
            ready=ready,
            restored_from=None if self._restored_from is None else self._restored_from.value,
            os=self._scope.os,
            arithmetic_reference_build=self._scope.arithmetic_reference_build,
        )

    def snapshot(self) -> Result[StreamingSnapshot]:
        """Serialize the resumable state into a :class:`StreamingSnapshot` (reader).

        Captures the accumulated per-column series, the held writer id, the next sequence
        the sequencer will mint, the configuration fingerprint, and the injected scope —
        everything a :meth:`restore` needs to resume with restore-equivalence.
        """
        columns: dict[str, InputSeries] = {}
        for name in self._names:
            values, presence, knowable_at = self._columns[name]
            encoded = encode_int64_values(values)
            if is_refusal(encoded):  # pragma: no cover - accumulated values were already validated
                return encoded
            built = InputSeries.try_create(
                encoded.value, self._input_scales[name], list(presence), list(knowable_at)
            )
            if is_refusal(built):  # pragma: no cover - accumulated parts were already validated
                return built
            columns[name] = built.value
        return Ok(
            StreamingSnapshot(
                format_version=SNAPSHOT_FORMAT_VERSION,
                scope=self._scope,
                configuration_fingerprint=self._configuration_fingerprint,
                writer_id=self._writer_id,
                next_sequence=self._sequencer.next_sequence,
                columns=columns,
            )
        )

    @classmethod
    def restore(
        cls,
        snapshot: object,
        *,
        configuration: object,
        kernel: object,
        world: object,
        current_scope: object,
    ) -> Result[StreamingIndicator]:
        """Resume a :class:`StreamingIndicator` from a snapshot, value-or-refusal (FM-7).

        The ``current_scope`` must equal the snapshot's ``(OS, arithmetic-reference build)``
        scope — otherwise restore is an ``unavailable dependency`` refusal (FM-7), because
        the reference arithmetic that produced the state is only attestable within one
        tuple. The ``configuration`` must be the one the snapshot's state belongs to (its
        fingerprint must match). On success the instance resumes with the accumulated
        columns, the sequencer at the snapshot's ``next_sequence``, and the snapshot's
        fingerprint recorded so a result from restored state carries it as an input
        fingerprint. Restore-then-N-updates equals cold-warm-then-the-same-N-updates by
        construction.
        """
        if not isinstance(snapshot, StreamingSnapshot):
            return _invalid("snapshot", "a StreamingSnapshot is required", given=repr(snapshot))
        if not isinstance(current_scope, SnapshotScope):
            return _invalid(
                "current_scope",
                "the current (OS, arithmetic-reference build) scope is injected",
                given=repr(current_scope),
            )
        if current_scope != snapshot.scope:
            return _unavailable(
                "scope",
                "the snapshot was produced on a different (OS, arithmetic-reference build) "
                "tuple; a result from restored state must never attest arithmetic that was "
                "not the arithmetic used (FM-7)",
                snapshot_scope=snapshot.scope.fp1_identity(),
                current_scope=current_scope.fp1_identity(),
            )
        if not isinstance(configuration, ConfiguredIndicator):
            return _invalid(
                "configuration", "a ConfiguredIndicator is required", given=repr(configuration)
            )
        if SupportedMode.STREAMING not in configuration.supported_modes:
            return _unsupported(
                "supported_modes",
                "the configuration does not declare streaming mode",
                declared=[mode.value for mode in configuration.supported_modes],
            )
        producer = configuration.fp1()
        if is_refusal(producer):  # pragma: no cover - config content is canonical by construction
            return producer
        if producer.value != snapshot.configuration_fingerprint:
            return _invalid(
                "configuration",
                "the configuration does not match the snapshot's configuration fingerprint",
                snapshot=snapshot.configuration_fingerprint.value,
                given=producer.value,
            )
        if not isinstance(kernel, BatchKernel):
            return _invalid("kernel", "a BatchKernel is required", given=repr(kernel))
        resolved_world = _coerce_world(world)
        if resolved_world is None:
            return _invalid(
                "world",
                "world is one of the closed set",
                given=repr(world),
                allowed=[member.value for member in World],
            )
        snapshot_fp = snapshot.fingerprint()
        if is_refusal(snapshot_fp):  # pragma: no cover - snapshot content is canonical
            return snapshot_fp
        instance = cls(
            configuration,
            producer.value,
            kernel,
            resolved_world,
            snapshot.writer_id,
            snapshot.scope,
            {name: series.scale for name, series in snapshot.columns.items()},
            start_sequence=snapshot.next_sequence,
            restored_from=snapshot_fp.value,
        )
        instance._load_columns(snapshot)
        return Ok(instance)

    def _load_columns(self, snapshot: StreamingSnapshot) -> None:
        """Load a snapshot's accumulated columns into this instance's mutable buffers."""
        for name in self._names:
            series = snapshot.columns[name]
            values = [series.value_at(index) for index in range(series.length)]
            presence = list(series.presence)
            knowable_at = list(series.knowable_at)
            self._columns[name] = (values, presence, knowable_at)

    def _recompute(self) -> BatchResult | TypedRefusal:
        """Recompute the batch result over the accumulated observations (internal)."""
        columns: dict[str, InputSeries] = {}
        for name in self._names:
            values, presence, knowable_at = self._columns[name]
            built = InputSeries.from_values(
                list(values), self._input_scales[name], list(presence), list(knowable_at)
            )
            if is_refusal(built):
                return built
            columns[name] = built.value
        result = compute_batch(
            self._configuration,
            columns,
            kernel=self._kernel,
            world=self._world,
            require_batch_mode=False,
        )
        if is_refusal(result):
            return result
        return result.value


def _coerce_world(value: object) -> World | None:
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def _coerce_input_scales(
    configuration: ConfiguredIndicator, value: object
) -> dict[str, int] | TypedRefusal:
    """Resolve a fixed out-of-band scale for every declared input, else a refusal."""
    if not isinstance(value, Mapping):
        return _invalid(
            "input_scales",
            "input scales are a mapping of input name to a fixed out-of-band scale",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[object, object]", value)
    scales: dict[str, int] = {}
    for series_input in configuration.inputs:
        scale = body.get(series_input.name)
        if isinstance(scale, bool) or not isinstance(scale, int) or scale < 0:
            return _invalid(
                "input_scales",
                "each declared input needs a non-negative integer out-of-band scale",
                input=series_input.name,
                given=repr(scale),
            )
        scales[series_input.name] = scale
    return scales


def _coerce_observations(
    names: Sequence[str], value: object
) -> dict[str, StreamingObservation] | TypedRefusal:
    """Resolve one :class:`StreamingObservation` for every declared input, else a refusal."""
    if not isinstance(value, Mapping):
        return _invalid(
            "observations",
            "observations are a mapping of input name to StreamingObservation",
            given=repr(type(value).__name__),
        )
    body = cast("Mapping[object, object]", value)
    resolved: dict[str, StreamingObservation] = {}
    for name in names:
        observation = body.get(name)
        if not isinstance(observation, StreamingObservation):
            return _invalid(
                "observations",
                "each declared input needs a StreamingObservation in this update",
                input=name,
            )
        resolved[name] = observation
    return resolved


def _newest_sample(
    configuration: ConfiguredIndicator, result: BatchResult, sequence: int
) -> StreamingSample:
    """Project the newest position of every output channel into a :class:`StreamingSample`."""
    channels: dict[str, ChannelSample] = {}
    position = 0
    for channel in configuration.output_schema:
        series = result.outputs[channel.name]
        position = series.length - 1
        state = series.presence_at(position)
        has_value = state in (PresenceState.PRESENT, PresenceState.PROVISIONAL)
        channels[channel.name] = ChannelSample(
            presence=state,
            scale=series.scale,
            value=series.value_at(position) if has_value else None,
            knowable_at=series.knowable_at[position],
        )
    return StreamingSample(sequence=sequence, position=position, channels=channels)


def _augment_label_with_snapshot(
    result: BatchResult, snapshot_fp: Fingerprint
) -> Result[BatchResult]:
    """Rebuild a result's label with the snapshot fingerprint as a leading input fingerprint.

    A result from restored state carries the snapshot fingerprint as an input fingerprint
    (CT-16; DEC-0126). The output series are unchanged — restore-equivalence is about the
    computed values — only the label's provenance records the resumed state.
    """
    label = result.label
    rebuilt = ResultLabel.try_create(
        producer_contract_identity=label.producer_contract_identity,
        producer_contract_format_version=label.producer_contract_format_version,
        input_fingerprints=[snapshot_fp, *label.input_fingerprints],
        evidence_time_range=label.evidence_time_range,
        evidence_class=label.evidence_class,
        world=label.world,
    )
    if is_refusal(rebuilt):  # pragma: no cover - the parts came from a valid label
        return rebuilt
    return Ok(BatchResult(outputs=result.outputs, label=rebuilt.value))
