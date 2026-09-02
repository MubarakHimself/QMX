"""History bootstrap and venue continuity-gap bridge (TN-13 / Story 27.2).

``just node-data-bootstrap`` is the only sanctioned acquisition. Dukascopy
history lands in the immutable raw archive under personal-use licence with
provider identity and provenance; the venue pages only the recent continuity
gap inside the documented rate and one-week span cap. Runs never fetch ad hoc.
Factory tests inject a transport — they never hit the live datafeed.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType
from typing import Final, cast

from qmf.core import Instant, Ok, Result, TypedRefusal, World, WriterId, is_refusal
from qmf.data.dukascopy import (
    DUKASCOPY_SOURCE,
    PERSONAL_USE_LICENSE,
    DukascopyAdapter,
    LicensedSourceWindow,
    LicenseTag,
    parse_license_tag,
)
from qmf.data.ingest import (
    ExternalSourceIngest,
    IntakeOutcome,
    ProviderRecord,
    SourceRequest,
)
from qmf.data.source_boundary import SourceObservationBoundary

from qmn.data._refuse import invalid, policy

__all__ = [
    "BOOTSTRAP_CONTEXT",
    "CHECKPOINT_NAME",
    "DUKASCOPY_SOURCE",
    "PERSONAL_USE_LICENSE",
    "VENUE_HISTORICAL_RATE_PER_S",
    "VENUE_SPAN_CAP_NS",
    "BootstrapCheckpoint",
    "BootstrapReceipt",
    "HistoryBootstrap",
    "RefusingLiveTransport",
    "VenueContinuityBridge",
    "VenueHistoryPage",
    "refuse_ad_hoc_fetch",
    "refuse_live_network",
    "refuse_venue_span_cap",
]


BOOTSTRAP_CONTEXT: Final[str] = "node-data-bootstrap"
CHECKPOINT_NAME: Final[str] = "bootstrap-checkpoint.json"
VENUE_HISTORICAL_RATE_PER_S: Final[int] = 5
NS_PER_WEEK: Final[int] = 7 * 24 * 3_600 * 1_000_000_000
VENUE_SPAN_CAP_NS: Final[int] = NS_PER_WEEK


def refuse_ad_hoc_fetch(*, context: object) -> TypedRefusal:
    """Refuse any fetch that is not the operations-toolkit bootstrap recipe."""
    return policy(
        "context",
        "runs never fetch data ad hoc; history bootstrap is just node-data-bootstrap "
        "only (TN-13, DEC-0198, DEC-0119)",
        failure_id="data.bootstrap.ad_hoc",
        given=repr(context),
        allowed=BOOTSTRAP_CONTEXT,
    )


def refuse_live_network(*, target: object) -> TypedRefusal:
    """Refuse a live Dukascopy/HTTPS download from this factory path."""
    return policy(
        "transport",
        "factory and check-mode bootstrap never perform a live Dukascopy download; "
        "inject a fixture transport (TN-13, DEC-0051)",
        failure_id="data.bootstrap.live_network",
        given=repr(target),
    )


def refuse_venue_span_cap(*, gap_ns: object, cap_ns: int = VENUE_SPAN_CAP_NS) -> TypedRefusal:
    """Refuse venue paging that exceeds the documented one-week span cap."""
    return policy(
        "span",
        "venue paging bridges only the recent continuity gap within the one-week "
        "tick-history span cap and the recorded historical rate (TN-13, DEC-0135)",
        failure_id="data.bootstrap.span_cap",
        gap_ns=gap_ns,
        cap_ns=cap_ns,
        rate_per_s=VENUE_HISTORICAL_RATE_PER_S,
    )


class RefusingLiveTransport:
    """Default transport: every hour fetch is a live-network refusal."""

    def fetch_hour(self, key: object, /) -> Result[bytes]:
        path = getattr(key, "path_reference", repr(key))
        return refuse_live_network(target=path)


@dataclass(frozen=True, slots=True)
class BootstrapCheckpoint:
    """Idempotent resume cursor for one symbol in the immutable raw archive."""

    symbol: str
    last_end_ns: int
    hours_completed: int
    source: str
    license_tag: str

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "symbol": self.symbol,
                "last_end_ns": self.last_end_ns,
                "hours_completed": self.hours_completed,
                "source": self.source,
                "license_tag": self.license_tag,
            }
        )


@dataclass(frozen=True, slots=True)
class BootstrapReceipt:
    """One bootstrap run: produced vs idempotent counts, checkpoint, provenance."""

    source: str
    license_tag: str
    produced: int
    idempotent: int
    admitted: int
    checkpoint: BootstrapCheckpoint
    provenance: Mapping[str, object]
    windows: tuple[Mapping[str, object], ...]

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "source": self.source,
                "license_tag": self.license_tag,
                "produced": self.produced,
                "idempotent": self.idempotent,
                "admitted": self.admitted,
                "checkpoint": dict(self.checkpoint.as_mapping()),
                "provenance": dict(self.provenance),
                "windows": [dict(item) for item in self.windows],
            }
        )


@dataclass(frozen=True, slots=True)
class VenueHistoryPage:
    """One hasMore-class venue tick-history page for the continuity gap."""

    from_ns: int
    to_ns: int
    has_more: bool

    def as_mapping(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "from_ns": self.from_ns,
                "to_ns": self.to_ns,
                "has_more": self.has_more,
                "source": "ctrader",
                "rate_per_s": VENUE_HISTORICAL_RATE_PER_S,
            }
        )


@dataclass
class VenueContinuityBridge:
    """Venue tick-history paging for the gap after the Dukascopy archive only."""

    rate_per_s: int = VENUE_HISTORICAL_RATE_PER_S
    span_cap_ns: int = VENUE_SPAN_CAP_NS

    def plan(
        self,
        *,
        archive_end_ns: object,
        go_live_ns: object,
    ) -> Result[tuple[VenueHistoryPage, ...]]:
        """Page ``(archive_end, go_live]`` newest-first within the span cap."""
        start = _as_ns(archive_end_ns, field="archive_end_ns")
        if is_refusal(start):
            return start
        end = _as_ns(go_live_ns, field="go_live_ns")
        if is_refusal(end):
            return end
        if end.value <= start.value:
            return Ok(())
        gap = end.value - start.value
        if gap > self.span_cap_ns:
            return refuse_venue_span_cap(gap_ns=gap, cap_ns=self.span_cap_ns)
        # hasMore paging: one page per hour, shifted bound, never a bulk dump.
        hour_ns = 3_600 * 1_000_000_000
        pages: list[VenueHistoryPage] = []
        cursor = start.value
        while cursor < end.value:
            nxt = min(cursor + hour_ns, end.value)
            pages.append(
                VenueHistoryPage(
                    from_ns=cursor,
                    to_ns=nxt,
                    has_more=nxt < end.value,
                )
            )
            cursor = nxt
        return Ok(tuple(pages))


@dataclass
class HistoryBootstrap:
    """Application-owned Dukascopy bootstrap: called port, checkpointed, licensed."""

    adapter: DukascopyAdapter
    ingest: ExternalSourceIngest
    writer: WriterId
    archive_root: Path
    world: World = World.LIVE
    boundary: SourceObservationBoundary | None = None
    context: str = BOOTSTRAP_CONTEXT
    _windows: list[Mapping[str, object]] = field(default_factory=list[Mapping[str, object]])

    def run(
        self,
        *,
        symbol: object,
        start_ns: object,
        end_ns: object,
        receive_wall_ns: object,
        license_tag: object = PERSONAL_USE_LICENSE,
        revision: object = "r1",
    ) -> Result[BootstrapReceipt]:
        """Fetch one bounded window through the injected adapter into the archive."""
        if self.context != BOOTSTRAP_CONTEXT:
            return refuse_ad_hoc_fetch(context=self.context)
        token = _clean(symbol)
        if token is None:
            return invalid(
                "symbol",
                "bootstrap names a non-empty provider symbol",
                given=repr(symbol),
            )
        start = _as_ns(start_ns, field="start_ns")
        if is_refusal(start):
            return start
        end = _as_ns(end_ns, field="end_ns")
        if is_refusal(end):
            return end
        wall = _as_ns(receive_wall_ns, field="receive_wall_ns")
        if is_refusal(wall):
            return wall
        if end.value <= start.value:
            return invalid(
                "window",
                "bootstrap window is a non-empty half-open [start_ns, end_ns)",
                start_ns=start.value,
                end_ns=end.value,
            )
        tag = parse_license_tag(license_tag)
        if tag is LicenseTag.UNKNOWN or not tag.grants_governed_evidence():
            return policy(
                "license_tag",
                "Dukascopy bootstrap records a personal-use licence tag before "
                "governed-evidence use (DEC-0170)",
                license_tag=tag.value,
            )
        rev = _clean(revision) or "r1"
        prior = self._load_checkpoint(token)
        window_start = start.value
        hours_done = 0
        if prior is not None and prior.last_end_ns >= start.value:
            window_start = prior.last_end_ns
            hours_done = prior.hours_completed
            if window_start >= end.value:
                return Ok(
                    BootstrapReceipt(
                        source=DUKASCOPY_SOURCE,
                        license_tag=tag.value,
                        produced=0,
                        idempotent=0,
                        admitted=0,
                        checkpoint=prior,
                        provenance=_provenance(tag, resumed=True),
                        windows=(),
                    )
                )

        request = SourceRequest(
            source=DUKASCOPY_SOURCE,
            bounds=MappingProxyType(
                {
                    "symbol": token,
                    "start_ns": window_start,
                    "end_ns": end.value,
                    "revision": rev,
                    "license_tag": tag.value,
                    "known_at_ns": wall.value,
                }
            ),
        )
        fetched = self.adapter.fetch(request)
        if is_refusal(fetched):
            return fetched
        records: Sequence[ProviderRecord] = fetched.value

        produced = 0
        idempotent = 0
        admitted = 0
        sequence = hours_done
        for record in records:
            sequence += 1
            taken = self.ingest.intake(
                record,
                writer=self.writer,
                sequence=sequence,
                world=self.world,
                receive_wall_time=wall.value,
            )
            if is_refusal(taken):
                return taken
            receipt = taken.value
            if receipt.outcome is IntakeOutcome.IDEMPOTENT:
                idempotent += 1
            else:
                produced += 1
            if self.boundary is not None:
                stored = self.boundary.admit(receipt.observation)
                if is_refusal(stored):
                    return stored
                admitted += 1
            else:
                admitted += 1

        window = self.adapter.last_window
        provenance = _provenance(tag, resumed=prior is not None)
        if window is not None:
            self._windows.append(_window_row(window, provenance))
        checkpoint = BootstrapCheckpoint(
            symbol=token,
            last_end_ns=end.value,
            hours_completed=sequence,
            source=DUKASCOPY_SOURCE,
            license_tag=tag.value,
        )
        written = self._store_checkpoint(checkpoint)
        if is_refusal(written):
            return written
        return Ok(
            BootstrapReceipt(
                source=DUKASCOPY_SOURCE,
                license_tag=tag.value,
                produced=produced,
                idempotent=idempotent,
                admitted=admitted,
                checkpoint=checkpoint,
                provenance=provenance,
                windows=tuple(self._windows),
            )
        )

    def _checkpoint_path(self) -> Path:
        return self.archive_root / CHECKPOINT_NAME

    def _load_checkpoint(self, symbol: str) -> BootstrapCheckpoint | None:
        path = self._checkpoint_path()
        if not path.is_file():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if not isinstance(payload, Mapping):
            return None
        body = cast("Mapping[str, object]", payload)
        if body.get("symbol") != symbol:
            return None
        last_end = body.get("last_end_ns")
        hours = body.get("hours_completed")
        if not isinstance(last_end, int) or isinstance(last_end, bool):
            return None
        if not isinstance(hours, int) or isinstance(hours, bool):
            return None
        source = body.get("source", DUKASCOPY_SOURCE)
        license_tag = body.get("license_tag", PERSONAL_USE_LICENSE)
        if not isinstance(source, str) or not isinstance(license_tag, str):
            return None
        return BootstrapCheckpoint(
            symbol=symbol,
            last_end_ns=last_end,
            hours_completed=hours,
            source=source,
            license_tag=license_tag,
        )

    def _store_checkpoint(self, checkpoint: BootstrapCheckpoint) -> Result[bool]:
        self.archive_root.mkdir(parents=True, exist_ok=True)
        path = self._checkpoint_path()
        path.write_text(
            json.dumps(dict(checkpoint.as_mapping()), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return Ok(True)


def _clean(value: object) -> str | None:
    if isinstance(value, str) and value.strip() != "":
        return value.strip()
    return None


def _as_ns(value: object, *, field: str) -> Result[int]:
    if isinstance(value, Instant):
        return Ok(value.value_ns)
    if isinstance(value, bool) or not isinstance(value, int):
        return invalid(
            field,
            f"{field} is an int64 UTC-ns instant",
            given=repr(value),
        )
    return Ok(value)


def _provenance(tag: LicenseTag, *, resumed: bool) -> Mapping[str, object]:
    return MappingProxyType(
        {
            "provider": DUKASCOPY_SOURCE,
            "licence": tag.value,
            "posture": "personal-use",
            "acquisition": BOOTSTRAP_CONTEXT,
            "resumed": resumed,
            "live_network": False,
        }
    )


def _window_row(
    window: LicensedSourceWindow, provenance: Mapping[str, object]
) -> Mapping[str, object]:
    partition = window.partition
    return MappingProxyType(
        {
            "source": partition.source,
            "symbol": partition.instrument.symbol,
            "start_ns": partition.window.start.value_ns,
            "end_ns": partition.window.end.value_ns,
            "license_tag": window.license_tag.value,
            "provenance": dict(provenance),
        }
    )
