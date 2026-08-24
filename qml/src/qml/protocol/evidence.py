"""Declared-footprint evidence the callback may receive (QL-7).

Presence-mapped series (AD-22) and structure lifecycle folds (AD-25), each sample
carrying its knowable-at instant. QML never imports qmf-indicators or
qmf-structure (DEC-0171); presence states are named from
``registry:presence_map_states``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.exact import ExactRational
from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qml._refuse import clean_token, invalid
from qml.footprint._coerce import deep_freeze
from qml.footprint.manifest import Footprint

__all__ = [
    "FORBIDDEN_EVIDENCE_KEYS",
    "FootprintEvidence",
    "MappingReadSurface",
    "PresenceMappedSeries",
    "PresenceState",
    "SeriesSample",
    "StructureFold",
    "collect_evidence",
    "declared_evidence_keys",
]

FORBIDDEN_EVIDENCE_KEYS: Final[frozenset[str]] = frozenset(
    {
        "book",
        "book_module",
        "clock",
        "exit_logic",
        "full_loss_price",
        "declared_full_loss_price",
        "io",
        "network",
        "requested_r",
    }
)


class PresenceState(StrEnum):
    """Per-sample presence — ``registry:presence_map_states`` (DEC-0126).

    Named here because qml never imports ``qmf-indicators``. Provisional samples
    never enter governed evidence.
    """

    PRESENT = "present"
    PROVISIONAL = "provisional"
    NOT_READY = "not_ready"
    GAP = "gap"
    ABSENT_BY_SCHEDULE = "absent_by_schedule"


def _plain_int(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def _as_instant(value: object, field: str) -> Result[Instant]:
    if isinstance(value, Instant):
        return Ok(value)
    ns = _plain_int(value)
    if ns is None:
        return invalid(
            field,
            "every sample carries a knowable-at Instant; a missing knowledge time is refused",
            given=repr(value),
        )
    parsed = Instant.try_create(ns)
    if is_refusal(parsed):
        return invalid(
            field,
            "knowable-at is an Instant (int64 UTC ns); a missing knowledge time is refused",
            given=repr(value),
        )
    return parsed


def _refuse_float(value: object, field: str) -> Result[None]:
    if isinstance(value, float):
        return invalid(
            field,
            "evidence values are exact; a binary float is refused (AD-7)",
            given=repr(value),
        )
    return Ok(None)


def _parse_presence(value: object) -> Result[PresenceState]:
    if isinstance(value, PresenceState):
        return Ok(value)
    if isinstance(value, str):
        try:
            return Ok(PresenceState(value))
        except ValueError:
            pass
    return invalid(
        "presence",
        "a presence state is present | provisional | not_ready | gap | absent_by_schedule",
        given=repr(value),
        allowed=[member.value for member in PresenceState],
    )


@dataclass(frozen=True, slots=True)
class SeriesSample:
    """One presence-mapped sample carrying its knowable-at instant (AD-22)."""

    presence: PresenceState
    knowable_at: Instant
    value: object | None = None

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "presence": self.presence.value,
            "knowable_at": self.knowable_at.fp1_identity(),
        }
        if self.value is not None:
            if isinstance(self.value, ExactRational):
                content["value"] = self.value.fp1_identity()
            else:
                content["value"] = self.value
        return content

    @classmethod
    def try_create(
        cls,
        presence: object,
        knowable_at: object,
        value: object = None,
    ) -> Result[SeriesSample]:
        state = _parse_presence(presence)
        if is_refusal(state):
            return state
        if state.value is PresenceState.PROVISIONAL:
            return invalid(
                "presence",
                "provisional samples never enter governed evidence (AD-22)",
                given=state.value.value,
            )
        instant = _as_instant(knowable_at, "knowable_at")
        if is_refusal(instant):
            return instant
        float_guard = _refuse_float(value, "value")
        if is_refusal(float_guard):
            return float_guard
        if state.value is PresenceState.PRESENT:
            if value is None:
                return invalid(
                    "value",
                    "a present sample carries a value; absence is a presence state, "
                    "never a null value",
                )
        elif value is not None:
            return invalid(
                "value",
                "a non-present sample omits its value; presence is the parallel map, "
                "never a sentinel",
                presence=state.value.value,
            )
        return Ok(cls(presence=state.value, knowable_at=instant.value, value=value))

    @classmethod
    def try_from_payload(cls, payload: object) -> Result[SeriesSample]:
        if isinstance(payload, cls):
            return Ok(payload)
        if not isinstance(payload, Mapping):
            return invalid(
                "sample",
                "a series sample is {presence, knowable_at, value?}",
                given=type(payload).__name__,
            )
        mapping = cast("Mapping[str, object]", payload)
        return cls.try_create(
            mapping.get("presence"),
            mapping.get("knowable_at"),
            mapping.get("value"),
        )


@dataclass(frozen=True, slots=True)
class PresenceMappedSeries:
    """AD-22 presence-mapped series at one evaluation instant."""

    producer_key: str
    samples: tuple[SeriesSample, ...]

    def fp1_identity(self) -> dict[str, object]:
        return {
            "kind": "series",
            "producer_key": self.producer_key,
            "samples": [sample.fp1_identity() for sample in self.samples],
        }

    @classmethod
    def try_create(cls, producer_key: object, samples: object) -> Result[PresenceMappedSeries]:
        key = clean_token(producer_key)
        if key is None:
            return invalid(
                "producer_key",
                "a series names a declared footprint producer or stream key",
                given=repr(producer_key),
            )
        if isinstance(samples, SeriesSample):
            items: tuple[object, ...] = (samples,)
        elif isinstance(samples, (str, bytes)) or not isinstance(samples, Sequence):
            return invalid(
                "samples",
                "a presence-mapped series carries a sequence of samples",
                given=type(samples).__name__,
            )
        else:
            items = tuple(cast("Sequence[object]", samples))
        resolved: list[SeriesSample] = []
        for index, item in enumerate(items):
            sample = SeriesSample.try_from_payload(item)
            if is_refusal(sample):
                return invalid(
                    "samples",
                    "each series sample carries presence, knowable-at, and an exact "
                    "value when present",
                    index=index,
                    cause=dict(sample.context),
                )
            resolved.append(sample.value)
        return Ok(cls(producer_key=key, samples=tuple(resolved)))


@dataclass(frozen=True, slots=True)
class StructureFold:
    """AD-25 structure lifecycle fold at one evaluation instant."""

    producer_key: str
    knowable_at: Instant
    observed_at: Instant | None = None
    confirmed_at: Instant | None = None
    invalidated_at: Instant | None = None
    geometry: Mapping[str, object] = MappingProxyType({})

    def __post_init__(self) -> None:
        frozen = deep_freeze(dict(self.geometry))
        object.__setattr__(self, "geometry", frozen)

    def fp1_identity(self) -> dict[str, object]:
        content: dict[str, object] = {
            "kind": "structure_fold",
            "producer_key": self.producer_key,
            "knowable_at": self.knowable_at.fp1_identity(),
            "geometry": dict(self.geometry),
        }
        if self.observed_at is not None:
            content["observed_at"] = self.observed_at.fp1_identity()
        if self.confirmed_at is not None:
            content["confirmed_at"] = self.confirmed_at.fp1_identity()
        if self.invalidated_at is not None:
            content["invalidated_at"] = self.invalidated_at.fp1_identity()
        return content

    @classmethod
    def try_create(
        cls,
        producer_key: object,
        knowable_at: object,
        *,
        observed_at: object = None,
        confirmed_at: object = None,
        invalidated_at: object = None,
        geometry: object = None,
    ) -> Result[StructureFold]:
        key = clean_token(producer_key)
        if key is None:
            return invalid(
                "producer_key",
                "a structure fold names a declared footprint producer key",
                given=repr(producer_key),
            )
        known = _as_instant(knowable_at, "knowable_at")
        if is_refusal(known):
            return known
        observed = _optional_instant(observed_at, "observed_at")
        if is_refusal(observed):
            return observed
        confirmed = _optional_instant(confirmed_at, "confirmed_at")
        if is_refusal(confirmed):
            return confirmed
        invalidated = _optional_instant(invalidated_at, "invalidated_at")
        if is_refusal(invalidated):
            return invalidated
        if geometry is None:
            geo: Mapping[str, object] = MappingProxyType({})
        elif not isinstance(geometry, Mapping):
            return invalid(
                "geometry",
                "a structure fold's geometry is a mapping of exact values",
                given=type(geometry).__name__,
            )
        else:
            mapping = cast("Mapping[str, object]", geometry)
            for nested in mapping.values():
                float_guard = _refuse_float(nested, "geometry")
                if is_refusal(float_guard):
                    return float_guard
            geo = MappingProxyType(dict(mapping))
        return Ok(
            cls(
                producer_key=key,
                knowable_at=known.value,
                observed_at=observed.value,
                confirmed_at=confirmed.value,
                invalidated_at=invalidated.value,
                geometry=geo,
            )
        )


def _optional_instant(value: object, field: str) -> Result[Instant | None]:
    if value is None:
        return Ok(None)
    parsed = _as_instant(value, field)
    if is_refusal(parsed):
        return parsed
    return Ok(parsed.value)


@dataclass(frozen=True, slots=True)
class FootprintEvidence:
    """The only evidence a callback may see: declared-footprint series and folds."""

    evaluation_instant: Instant
    series: Mapping[str, PresenceMappedSeries] = MappingProxyType({})
    structure_folds: Mapping[str, StructureFold] = MappingProxyType({})

    def __post_init__(self) -> None:
        object.__setattr__(self, "series", MappingProxyType(dict(self.series)))
        object.__setattr__(self, "structure_folds", MappingProxyType(dict(self.structure_folds)))

    def fp1_identity(self) -> dict[str, object]:
        return {
            "evaluation_instant": self.evaluation_instant.fp1_identity(),
            "series": {key: item.fp1_identity() for key, item in sorted(self.series.items())},
            "structure_folds": {
                key: item.fp1_identity() for key, item in sorted(self.structure_folds.items())
            },
        }

    @classmethod
    def try_create(
        cls,
        evaluation_instant: object,
        series: object = None,
        structure_folds: object = None,
        *,
        declared_keys: object = None,
    ) -> Result[FootprintEvidence]:
        instant = _as_instant(evaluation_instant, "evaluation_instant")
        if is_refusal(instant):
            return instant
        allowed = _coerce_declared_keys(declared_keys)
        if is_refusal(allowed):
            return allowed
        resolved_series = _coerce_series_map(series, allowed.value, instant.value)
        if is_refusal(resolved_series):
            return resolved_series
        resolved_folds = _coerce_fold_map(structure_folds, allowed.value, instant.value)
        if is_refusal(resolved_folds):
            return resolved_folds
        return Ok(
            cls(
                evaluation_instant=instant.value,
                series=resolved_series.value,
                structure_folds=resolved_folds.value,
            )
        )


def _coerce_declared_keys(value: object) -> Result[frozenset[str] | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, (str, bytes)) or not isinstance(value, (set, frozenset, Sequence)):
        return invalid(
            "declared_keys",
            "declared evidence keys are a set of footprint producer/stream tokens",
            given=type(value).__name__,
        )
    raw_items: tuple[object, ...]
    if isinstance(value, frozenset):
        raw_items = tuple(cast("frozenset[object]", value))
    elif isinstance(value, set):
        raw_items = tuple(cast("set[object]", value))
    else:
        raw_items = tuple(cast("Sequence[object]", value))
    out: list[str] = []
    for item in raw_items:
        token = clean_token(item)
        if token is None:
            return invalid(
                "declared_keys",
                "declared evidence keys are non-empty tokens",
                given=repr(item),
            )
        out.append(token)
    return Ok(frozenset(out))


def _check_key(key: str, allowed: frozenset[str] | None) -> Result[None]:
    if key in FORBIDDEN_EVIDENCE_KEYS:
        return invalid(
            "evidence",
            "hosts inject only declared-footprint read surfaces; a clock, Book, or "
            "sizing surface is never injected into bot logic",
            key=key,
        )
    if allowed is not None and key not in allowed:
        return invalid(
            "evidence",
            "callbacks receive only the declared footprint's evidence; an undeclared "
            "producer or stream key is refused",
            key=key,
        )
    return Ok(None)


def _look_ahead(knowable_at: Instant, evaluation_instant: Instant, field: str) -> Result[None]:
    if knowable_at.value_ns > evaluation_instant.value_ns:
        return invalid(
            field,
            "evidence must be knowable at or before the evaluation instant; look-ahead is refused",
            knowable_at=knowable_at.value_ns,
            evaluation_instant=evaluation_instant.value_ns,
        )
    return Ok(None)


def _coerce_series_map(
    value: object,
    allowed: frozenset[str] | None,
    evaluation_instant: Instant,
) -> Result[Mapping[str, PresenceMappedSeries]]:
    if value is None:
        return Ok(MappingProxyType({}))
    if not isinstance(value, Mapping):
        return invalid(
            "series",
            "series evidence is a mapping of declared producer/stream key to "
            "presence-mapped series",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, PresenceMappedSeries] = {}
    for raw_key, item in mapping.items():
        key = clean_token(raw_key)
        if key is None:
            return invalid(
                "series", "series keys are declared footprint tokens", given=repr(raw_key)
            )
        guarded = _check_key(key, allowed)
        if is_refusal(guarded):
            return guarded
        series = _coerce_series(key, item)
        if is_refusal(series):
            return series
        for sample in series.value.samples:
            ahead = _look_ahead(sample.knowable_at, evaluation_instant, "knowable_at")
            if is_refusal(ahead):
                return ahead
        resolved[key] = series.value
    return Ok(MappingProxyType(resolved))


def _coerce_fold_map(
    value: object,
    allowed: frozenset[str] | None,
    evaluation_instant: Instant,
) -> Result[Mapping[str, StructureFold]]:
    if value is None:
        return Ok(MappingProxyType({}))
    if not isinstance(value, Mapping):
        return invalid(
            "structure_folds",
            "structure folds are a mapping of declared producer key to an AD-25 lifecycle fold",
            given=type(value).__name__,
        )
    mapping = cast("Mapping[object, object]", value)
    resolved: dict[str, StructureFold] = {}
    for raw_key, item in mapping.items():
        key = clean_token(raw_key)
        if key is None:
            return invalid(
                "structure_folds",
                "structure-fold keys are declared footprint tokens",
                given=repr(raw_key),
            )
        guarded = _check_key(key, allowed)
        if is_refusal(guarded):
            return guarded
        fold = _coerce_fold(key, item)
        if is_refusal(fold):
            return fold
        ahead = _look_ahead(fold.value.knowable_at, evaluation_instant, "knowable_at")
        if is_refusal(ahead):
            return ahead
        resolved[key] = fold.value
    return Ok(MappingProxyType(resolved))


def _coerce_series(key: str, value: object) -> Result[PresenceMappedSeries]:
    kind_name = type(value).__name__
    if isinstance(value, PresenceMappedSeries):
        if value.producer_key != key:
            return invalid(
                "producer_key",
                "a series producer_key must match the injected surface key",
                key=key,
                given=value.producer_key,
            )
        return Ok(value)
    if isinstance(value, SeriesSample):
        return PresenceMappedSeries.try_create(key, (value,))
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        if "samples" in mapping or mapping.get("kind") == "series":
            producer = mapping.get("producer_key", key)
            if clean_token(producer) != key:
                return invalid(
                    "producer_key",
                    "a series producer_key must match the injected surface key",
                    key=key,
                    given=repr(producer),
                )
            return PresenceMappedSeries.try_create(key, mapping.get("samples", ()))
        if "presence" in mapping:
            return PresenceMappedSeries.try_create(key, (mapping,))
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return PresenceMappedSeries.try_create(key, tuple(cast("Sequence[object]", value)))
    return invalid(
        "series",
        "a read surface yields a presence-mapped series or a sample sequence",
        key=key,
        given=kind_name,
    )


def _coerce_fold(key: str, value: object) -> Result[StructureFold]:
    if isinstance(value, StructureFold):
        if value.producer_key != key:
            return invalid(
                "producer_key",
                "a structure fold producer_key must match the injected surface key",
                key=key,
                given=value.producer_key,
            )
        return Ok(value)
    if not isinstance(value, Mapping):
        return invalid(
            "structure_folds",
            "a structure fold is a mapping of knowable-at and lifecycle instants",
            key=key,
            given=type(value).__name__,
        )
    mapping = cast("Mapping[str, object]", value)
    producer = mapping.get("producer_key", key)
    if clean_token(producer) != key:
        return invalid(
            "producer_key",
            "a structure fold producer_key must match the injected surface key",
            key=key,
            given=repr(producer),
        )
    return StructureFold.try_create(
        key,
        mapping.get("knowable_at"),
        observed_at=mapping.get("observed_at"),
        confirmed_at=mapping.get("confirmed_at"),
        invalidated_at=mapping.get("invalidated_at"),
        geometry=mapping.get("geometry"),
    )


def declared_evidence_keys(footprint: object) -> Result[frozenset[str]]:
    """Stream instrument-roles plus producer-binding fingerprints (DEC-0174)."""
    if not isinstance(footprint, Footprint):
        return invalid(
            "footprint",
            "declared evidence keys are derived from the CT-33 footprint",
            given=type(footprint).__name__,
        )
    keys: list[str] = []
    for member in footprint.stream_set:
        keys.append(member.instrument_role)
    for binding in footprint.producer_bindings:
        fp = binding.fingerprint_content()
        if is_refusal(fp):
            return fp
        keys.append(fp.value.value)
    return Ok(frozenset(keys))


def collect_evidence(
    read_surfaces: object,
    instant: object,
    *,
    declared_keys: object = None,
) -> Result[FootprintEvidence]:
    """Build FootprintEvidence from injected surfaces at the evaluation instant.

    Extra surface keys outside the declared footprint are ``invalid input``.
    Missing declared keys are omitted (no sample this instant).
    """
    known = _as_instant(instant, "evaluation_instant")
    if is_refusal(known):
        return known
    if not isinstance(read_surfaces, Mapping):
        return invalid(
            "read_surfaces",
            "hosts inject a mapping of declared-footprint key to ReadSurface",
            given=type(read_surfaces).__name__,
        )
    allowed = _coerce_declared_keys(declared_keys)
    if is_refusal(allowed):
        return allowed
    mapping = cast("Mapping[object, object]", read_surfaces)
    series: dict[str, PresenceMappedSeries] = {}
    folds: dict[str, StructureFold] = {}
    for raw_key, surface in mapping.items():
        key = clean_token(raw_key)
        if key is None:
            return invalid(
                "read_surfaces",
                "read-surface keys are declared footprint tokens",
                given=repr(raw_key),
            )
        guarded = _check_key(key, allowed.value)
        if is_refusal(guarded):
            return guarded
        slice_ = _invoke_at(surface, known.value)
        if is_refusal(slice_):
            return slice_
        payload = slice_.value
        if payload is None:
            continue
        kind = _slice_kind(payload)
        if kind == "fold":
            fold = _coerce_fold(key, payload)
            if is_refusal(fold):
                return fold
            ahead = _look_ahead(fold.value.knowable_at, known.value, "knowable_at")
            if is_refusal(ahead):
                return ahead
            folds[key] = fold.value
            continue
        series_item = _coerce_series(key, payload)
        if is_refusal(series_item):
            return series_item
        for sample in series_item.value.samples:
            ahead = _look_ahead(sample.knowable_at, known.value, "knowable_at")
            if is_refusal(ahead):
                return ahead
        series[key] = series_item.value
    return FootprintEvidence.try_create(
        known.value,
        series,
        folds,
        declared_keys=allowed.value,
    )


def _slice_kind(payload: object) -> str:
    if isinstance(payload, StructureFold):
        return "fold"
    if isinstance(payload, (PresenceMappedSeries, SeriesSample)):
        return "series"
    if isinstance(payload, Mapping):
        mapping = cast("Mapping[str, object]", payload)
        kind = mapping.get("kind")
        if (
            (kind == "structure_fold" or "observed_at" in mapping or "geometry" in mapping)
            and "samples" not in mapping
            and "presence" not in mapping
        ):
            return "fold"
        if kind == "series" or "samples" in mapping or "presence" in mapping:
            return "series"
    return "series"


def _invoke_at(surface: object, instant: Instant) -> Result[object]:
    at = getattr(surface, "at", None)
    if not callable(at):
        return invalid(
            "read_surfaces",
            "each injected surface provides at(instant); hosts inject read surfaces only",
            given=type(surface).__name__,
        )
    raw: object = at(instant)
    if isinstance(raw, TypedRefusal):
        return raw
    if isinstance(raw, Ok):
        return Ok(cast("Ok[object]", raw).value)
    return Ok(raw)


@dataclass(frozen=True, slots=True)
class MappingReadSurface:
    """Host-injected evidence frames keyed by evaluation-instant nanoseconds."""

    frames: Mapping[int, object]

    def __post_init__(self) -> None:
        object.__setattr__(self, "frames", MappingProxyType(dict(self.frames)))

    def at(self, instant: object, /) -> Result[object]:
        if not isinstance(instant, Instant):
            return invalid(
                "instant",
                "the evaluation instant rides the callback; bots never read a clock",
                given=repr(instant),
            )
        if instant.value_ns not in self.frames:
            return Ok(None)
        return Ok(self.frames[instant.value_ns])

    @classmethod
    def try_create(cls, frames: object) -> Result[MappingReadSurface]:
        if not isinstance(frames, Mapping):
            return invalid(
                "frames",
                "a mapping read surface is instant-ns (or Instant) -> evidence slice",
                given=type(frames).__name__,
            )
        mapping = cast("Mapping[object, object]", frames)
        resolved: dict[int, object] = {}
        for raw_key, payload in mapping.items():
            if isinstance(raw_key, Instant):
                ns = raw_key.value_ns
            else:
                parsed = _plain_int(raw_key)
                if parsed is None:
                    return invalid(
                        "frames",
                        "frame keys are Instant or int64 UTC ns",
                        given=repr(raw_key),
                    )
                ns = parsed
            resolved[ns] = payload
        return Ok(cls(frames=resolved))
