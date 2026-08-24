"""Deterministic golden-slice generator keyed off the declared footprint (QL-8).

The slice is an identity-bearing conformance fixture: the same footprint always
yields the same frames, and the footprint's ``fp1`` enters the slice identity.
No clock is read; instants are synthesized from a pinned origin and the
footprint's first time-interval BarSpec (DEC-0178).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qml._refuse import invalid
from qml.conformance.contract import CONFORMANCE_FORMAT_VERSION
from qml.declaration.bot import BotDefinition
from qml.footprint import Footprint
from qml.protocol.evidence import MappingReadSurface, declared_evidence_keys

__all__ = [
    "GOLDEN_SLICE_CLASS",
    "GOLDEN_SLICE_INSTANT_COUNT",
    "GOLDEN_SLICE_ORIGIN_NS",
    "GoldenSlice",
    "generate_golden_slice",
    "read_surfaces_for_slice",
]

GOLDEN_SLICE_CLASS: Final[str] = "qml-golden-slice"
GOLDEN_SLICE_INSTANT_COUNT: Final[int] = 3
GOLDEN_SLICE_ORIGIN_NS: Final[int] = 1_700_000_000_000_000_000
_DEFAULT_STEP_NS: Final[int] = 60_000_000_000
_NS_PER_SECOND: Final[int] = 1_000_000_000


@dataclass(frozen=True, slots=True)
class GoldenSlice:
    """Identity-bearing conformance fixture keyed off a CT-33 footprint."""

    footprint_fingerprint: Fingerprint
    evaluation_instants: tuple[Instant, ...]
    frames: Mapping[int, Mapping[str, object]]
    format_version: int = CONFORMANCE_FORMAT_VERSION

    def __post_init__(self) -> None:
        frozen = {ns: MappingProxyType(dict(payload)) for ns, payload in self.frames.items()}
        object.__setattr__(self, "frames", MappingProxyType(frozen))

    def fp1_identity(self) -> dict[str, object]:
        """Canonical identity. Package SemVer never enters."""
        return {
            "class": GOLDEN_SLICE_CLASS,
            "contract_format_version": self.format_version,
            "footprint_fingerprint": self.footprint_fingerprint.value,
            "evaluation_instants": [item.value_ns for item in self.evaluation_instants],
            "frames": {str(ns): dict(payload) for ns, payload in sorted(self.frames.items())},
        }

    def fingerprint_content(self) -> Result[Fingerprint]:
        """``fp1`` over the slice, computed only by qmf-core."""
        return fingerprint(self)


def generate_golden_slice(footprint: object) -> Result[GoldenSlice]:
    """Build a deterministic golden slice from the declared footprint (DEC-0178).

    Evidence keys are the footprint's declared stream roles plus producer-binding
    fingerprints. Each instant carries a present series sample whose value is the
    1-based instant index — exact integer, never a binary float.
    """
    resolved = _as_footprint(footprint)
    if is_refusal(resolved):
        return resolved
    manifest = resolved.value
    fp = manifest.fingerprint_content()
    if is_refusal(fp):
        return fp
    keys = declared_evidence_keys(manifest)
    if is_refusal(keys):
        return keys
    step = _step_ns(manifest)
    instants: list[Instant] = []
    frames: dict[int, dict[str, object]] = {}
    for index in range(GOLDEN_SLICE_INSTANT_COUNT):
        ns = GOLDEN_SLICE_ORIGIN_NS + index * step
        instant = Instant.try_create(ns)
        if is_refusal(instant):
            return instant
        instants.append(instant.value)
        payload: dict[str, object] = {}
        for key in sorted(keys.value):
            payload[key] = {
                "kind": "series",
                "samples": [
                    {
                        "presence": "present",
                        "knowable_at": ns,
                        "value": index + 1,
                    }
                ],
            }
        frames[ns] = payload
    return Ok(
        GoldenSlice(
            footprint_fingerprint=fp.value,
            evaluation_instants=tuple(instants),
            frames=frames,
            format_version=CONFORMANCE_FORMAT_VERSION,
        )
    )


def read_surfaces_for_slice(slice_: GoldenSlice) -> Result[Mapping[str, MappingReadSurface]]:
    """Host-injectable read surfaces for one golden slice. No Book, no clock."""
    by_key: dict[str, dict[int, object]] = {}
    for ns, payload in slice_.frames.items():
        for key, evidence in payload.items():
            by_key.setdefault(key, {})[ns] = evidence
    surfaces: dict[str, MappingReadSurface] = {}
    for key, frames in by_key.items():
        made = MappingReadSurface.try_create(frames)
        if is_refusal(made):
            return made
        surfaces[key] = made.value
    return Ok(MappingProxyType(surfaces))


def _as_footprint(value: object) -> Result[Footprint]:
    if isinstance(value, Footprint):
        return Ok(value)
    if isinstance(value, BotDefinition):
        return Ok(value.footprint)
    if isinstance(value, Mapping):
        mapping = cast("Mapping[str, object]", value)
        nested = mapping.get("footprint")
        if isinstance(nested, Footprint):
            return Ok(nested)
        if isinstance(nested, Mapping) or "stream_set" in mapping:
            return Footprint.try_from_mapping(mapping)
        return invalid(
            "footprint",
            "the golden-slice generator is keyed off the bot's declared footprint",
            given=type(mapping).__name__,
        )
    return invalid(
        "footprint",
        "the golden-slice generator is keyed off the bot's declared footprint",
        given=type(value).__name__,
    )


def _step_ns(footprint: Footprint) -> int:
    """First time-interval BarSpec seconds, else a 60-second default."""
    for member in footprint.stream_set:
        for spec in member.bar_specs:
            if spec.get("kind") != "time-interval":
                continue
            seconds = spec.get("seconds")
            if isinstance(seconds, bool) or not isinstance(seconds, int) or seconds < 1:
                continue
            return seconds * _NS_PER_SECOND
    return _DEFAULT_STEP_NS
