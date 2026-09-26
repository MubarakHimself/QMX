"""COMP-DUKASCOPY public vocabulary: license tags, windows, and bounded-fetch refusals.

Split from :mod:`qmf.data.dukascopy` so the adapter module stays under the Skylos
god-file limits. Callers keep importing these names from :mod:`qmf.data.dukascopy`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Ok, Result, TypedRefusal
from qmf.data.partitions import SeriesPartition
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "DEFAULT_PRICE_SCALE",
    "DUKASCOPY_SOURCE",
    "FACTORY_MAX_WINDOW_NS",
    "NS_PER_HOUR",
    "NS_PER_MS",
    "PERSONAL_USE_LICENSE",
    "TICK_RECORD_BYTES",
    "LicenseTag",
    "LicensedSourceWindow",
    "offer_for_governed_evidence",
    "parse_license_tag",
    "refuse_complete_corpus_download",
    "refuse_external_recovery",
]

# Story 6.3 vocabulary format version — meaning never mutates in place (L15).
CONTRACT_FORMAT_VERSION: Final[int] = 1

# Read-only provenance noun for this provider (DEC-0117) — never a VenueId.
DUKASCOPY_SOURCE: Final[str] = "dukascopy"

# Personal-use posture ruled closed for own-strategy backtesting (DEC-0170).
PERSONAL_USE_LICENSE: Final[str] = "internal-only"

NS_PER_MS: Final[int] = 1_000_000
NS_PER_HOUR: Final[int] = 3_600 * 1_000_000_000
# Factory / documentation pass: only bounded adapter evidence (FM-5). One day.
FACTORY_MAX_WINDOW_NS: Final[int] = 24 * NS_PER_HOUR

TICK_RECORD_BYTES: Final[int] = 20
# Most FX majors: Dukascopy raw int / 100_000 → price; scale digits = 5.
DEFAULT_PRICE_SCALE: Final[int] = 5

_EMPTY_PROVENANCE: Final[Mapping[str, object]] = MappingProxyType({})


class LicenseTag(StrEnum):
    """Per-window usage-right tag recorded with provenance (DEC-0166, DEC-0170).

    Taxonomy mirrors the Story 18.2 gate input: a blank / unrecognized token is
    treated as :attr:`UNKNOWN` and blocks governed-evidence use. ``INTERNAL_ONLY``
    is the Dukascopy personal-use posture (DEC-0170).
    """

    REDISTRIBUTION_OK = "redistribution-ok"
    INTERNAL_ONLY = "internal-only"
    DENIED = "denied"
    UNKNOWN = "unknown"

    def grants_governed_evidence(self) -> bool:
        """Whether this tag authorizes governed-evidence citation."""
        return self in (LicenseTag.REDISTRIBUTION_OK, LicenseTag.INTERNAL_ONLY)


def parse_license_tag(value: object | None) -> LicenseTag:
    """Resolve a license token; blank / unrecognized → :attr:`LicenseTag.UNKNOWN`."""
    if value is None:
        return LicenseTag.UNKNOWN
    if isinstance(value, LicenseTag):
        return value
    if isinstance(value, str):
        token = value.strip()
        if token == "":
            return LicenseTag.UNKNOWN
        for tag in LicenseTag:
            if tag.value == token:
                return tag
        return LicenseTag.UNKNOWN
    return LicenseTag.UNKNOWN


@dataclass(frozen=True, slots=True)
class LicensedSourceWindow:
    """One acquired ``(source, instrument, time-window)`` with its license tag (AC2).

    Provenance is opaque application metadata (acquisition tool, operator, posture).
    The window may be catalogued regardless of tag; governed-evidence use is gated
    by :func:`offer_for_governed_evidence`.
    """

    partition: SeriesPartition
    license_tag: LicenseTag
    provenance: Mapping[str, object] = field(default_factory=lambda: _EMPTY_PROVENANCE)
    format_version: int = CONTRACT_FORMAT_VERSION

    @classmethod
    def try_create(
        cls,
        *,
        partition: object,
        license_tag: object | None = None,
        provenance: object | None = None,
    ) -> Result[LicensedSourceWindow]:
        """Build a licensed window; a missing / blank tag becomes ``unknown``."""
        if not isinstance(partition, SeriesPartition):
            return invalid_input(
                "partition",
                "a licensed source window is keyed by a SeriesPartition "
                "(source, instrument, time-window)",
                given=repr(partition),
            )
        if partition.source != DUKASCOPY_SOURCE:
            return invalid_input(
                "source",
                "COMP-DUKASCOPY windows carry source identity 'dukascopy'",
                given=partition.source,
            )
        tag = parse_license_tag(license_tag)
        prov: Mapping[str, object]
        if provenance is None:
            prov = _EMPTY_PROVENANCE
        elif isinstance(provenance, Mapping):
            prov = MappingProxyType(dict(cast("Mapping[str, object]", provenance)))
        else:
            return invalid_input(
                "provenance",
                "window provenance is a mapping of opaque acquisition metadata (or omitted)",
                given=repr(provenance),
            )
        return Ok(cls(partition=partition, license_tag=tag, provenance=prov))


def offer_for_governed_evidence(window: object) -> Result[LicensedSourceWindow]:
    """Admit a window for governed-evidence use, or refuse an unlicensed one (AC2).

    Tags that grant use (:attr:`LicenseTag.INTERNAL_ONLY`,
    :attr:`LicenseTag.REDISTRIBUTION_OK`) pass. ``denied``, ``unknown``, or a
    non-window value is a typed refusal — an unlicensed window never silently
    becomes governed evidence (DEC-0166, DEC-0170).
    """
    if not isinstance(window, LicensedSourceWindow):
        return invalid_input(
            "window",
            "governed-evidence use requires a LicensedSourceWindow with a recorded license tag",
            given=repr(window),
        )
    if not window.license_tag.grants_governed_evidence():
        return policy_rejection(
            "license_tag",
            "a source window without a recorded usage right cannot become governed "
            "evidence — record an authorizing license tag first (AC2, DEC-0166, "
            "DEC-0170)",
            signal="refuse-unlicensed-window",
            license_tag=window.license_tag.value,
            source=window.partition.source,
            instrument=(
                f"{window.partition.instrument.venue.value}/{window.partition.instrument.symbol}"
            ),
            window_start_ns=window.partition.window.start.value_ns,
            window_end_ns=window.partition.window.end.value_ns,
        )
    return Ok(window)


def refuse_complete_corpus_download(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse a bulk complete-corpus download during this factory pass (AC4 / FM-5).

    Only bounded adapter evidence is permitted until installation / runbook
    execution (DEC-0051, DEC-0166).
    """
    context: dict[str, object] = {
        "signal": "refuse-complete-corpus",
        "component": "COMP-DUKASCOPY",
        "contract": "CT-15",
        "posture": "download-once-bounded",
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "bounds",
        "a complete-corpus or unbounded Dukascopy download is outside this component "
        "pass — only bounded adapter evidence is permitted until installation/runbook "
        "execution (FM-5, DEC-0051, DEC-0166)",
        **context,
    )


def refuse_external_recovery(
    *,
    request: str | None = None,
) -> TypedRefusal:
    """Refuse asking QMF to own external recovery / checkpoint / retry (AC5 / FM-1).

    When a bounded transfer stops or the source is unavailable, checkpoint, retry,
    and operator-visible refusal live in the standalone application (DEC-0051,
    DEC-0119).
    """
    context: dict[str, object] = {
        "signal": "refuse-external-recovery",
        "component": "COMP-DUKASCOPY",
        "contract": "CT-15",
    }
    if request is not None:
        context["request"] = request
    return policy_rejection(
        "recovery",
        "QMF cannot require external recovery; checkpoint, retry, and supervision "
        "are application-owned (FM-1, DEC-0051, DEC-0119)",
        **context,
    )
