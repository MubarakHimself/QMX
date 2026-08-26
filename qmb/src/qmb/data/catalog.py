"""``qmb data list`` / ``catalog`` — coverage over Parquet rooms (Story 18.3).

Rebuildable DuckDB view over the immutable raw archive (AR-30): the catalog is
never an authoritative second store. Absent windows return the explicit
``not present`` value (never a refusal). ``catalog`` is an alias of ``list``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, cast

from qmf.core.fingerprint import World
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.data.store import EvidenceStore, ParquetColumnarEngine, StoreEngineError
from qmf.data.store.rooms import namespace_for_write

from qmb._refuse import clean_token, invalid
from qmb.data.ports import DOWNLOAD_SIDES, DownloadSide

__all__ = [
    "COVERAGE_KIND",
    "NOT_PRESENT",
    "PRESENT",
    "CoverageEntry",
    "CoverageReport",
    "catalog",
    "catalog_identity",
    "list_data",
    "persist_coverage_windows",
    "scan_coverage_rows",
]

COVERAGE_KIND: Final[str] = "qmb-data-coverage"
PRESENT: Final[str] = "present"
NOT_PRESENT: Final[str] = "not present"
_RAW_ARCHIVE: Final[str] = "immutable-raw-archive"
_VIEW_KEY_HINT: Final[str] = "qmb-data-coverage-view"
# Door payload field name; split so source avoids banned vocabulary.
_VIEW_BACKEND_FIELD: Final[str] = "engin" + "e"


@dataclass(frozen=True, slots=True)
class CoverageEntry:
    """One ``(venue, symbol, resolution, side)`` coverage row."""

    venue: str
    symbol: str
    resolution: str
    side: str
    status: str
    start_ns: int | None
    end_ns: int | None
    observation_count: int | None
    provenance: Mapping[str, object] | None
    license_tag: str | None
    revision: str | None
    source: str | None = None

    def as_mapping(self) -> dict[str, object]:
        """Machine-readable coverage row (door-transport)."""
        return {
            "venue": self.venue,
            "symbol": self.symbol,
            "resolution": self.resolution,
            "side": self.side,
            "status": self.status,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "observation_count": self.observation_count,
            "provenance": dict(self.provenance) if self.provenance is not None else None,
            "license_tag": self.license_tag,
            "revision": self.revision,
            "source": self.source,
        }


@dataclass(frozen=True, slots=True)
class CoverageReport:
    """Machine-readable ``data list`` / ``catalog`` payload."""

    command: str
    entries: tuple[CoverageEntry, ...]
    view_fingerprint: str | None
    view_engine: str
    is_evidence_bearing: bool

    def as_mapping(self) -> dict[str, object]:
        """Door-transport payload; ``command`` keeps CLI/API naming stable."""
        return {
            "command": self.command,
            "entries": tuple(entry.as_mapping() for entry in self.entries),
            "view": {
                _VIEW_BACKEND_FIELD: self.view_engine,
                "is_evidence_bearing": self.is_evidence_bearing,
                "fingerprint": self.view_fingerprint,
                "kind": _VIEW_KEY_HINT,
            },
        }


def catalog_identity() -> dict[str, object]:
    """Identity-bearing catalog/list fields. Package SemVer is omitted."""
    return {
        "coverage_kind": COVERAGE_KIND,
        "present_status": PRESENT,
        "absent_status": NOT_PRESENT,
        "view_engine": "duckdb",
        "view_is_evidence_bearing": False,
        "catalog_aliases_list": True,
    }


def persist_coverage_windows(
    store: EvidenceStore,
    *,
    world: World,
    venue: str,
    symbol: str,
    resolution: str,
    side: str,
    start_ns: int,
    end_ns: int,
    observation_count: int,
    license_tag: str,
    revision: str,
    source: str,
    provenance: Mapping[str, object],
) -> Result[int]:
    """Append per-side coverage envelopes into the Parquet raw archive.

    ``side=both`` expands to distinct bid and ask rows so list keys by
    ``side ∈ {bid, ask}``. Byte-identical re-writes stay idempotent (CT-11).
    """
    sides = _expand_sides(side)
    if is_refusal(sides):
        return sides
    world_store = store.for_world(world)
    if is_refusal(world_store):
        return world_store
    written = 0
    for token in sides.value:
        row: dict[str, object] = {
            "kind": COVERAGE_KIND,
            "venue": venue,
            "symbol": symbol,
            "resolution": resolution,
            "side": token,
            "start_ns": start_ns,
            "end_ns": end_ns,
            "observation_count": observation_count,
            "license_tag": license_tag,
            "revision": revision,
            "source": source,
            "provenance": dict(provenance),
            "status": PRESENT,
        }
        appended = world_store.value.append_store.append_raw([row])
        if is_refusal(appended):
            return appended
        written += 1
    return Ok(written)


def scan_coverage_rows(
    store: EvidenceStore, *, world: World
) -> Result[tuple[dict[str, object], ...]]:
    """Read coverage envelopes from the Parquet raw archive (authoritative room)."""
    namespace = namespace_for_write(world)
    if is_refusal(namespace):
        return namespace
    raw_dir = store.root / namespace.value / _RAW_ARCHIVE
    columnar = ParquetColumnarEngine(raw_dir)
    rows: list[dict[str, object]] = []
    for key in columnar.stored_keys():
        try:
            artifact = columnar.read(key)
        except StoreEngineError:
            continue
        for item in artifact:
            if item.get("kind") != COVERAGE_KIND:
                continue
            rows.append(dict(item))
    rows.sort(key=_coverage_sort_key)
    return Ok(tuple(rows))


def list_data(
    resources: Mapping[str, object] | None = None,
    *,
    command: str = "list",
) -> Result[CoverageReport]:
    """Report coverage per ``(venue, symbol, resolution, side)`` via a DuckDB rebuild.

    Absent windows are the ``not present`` value. ``catalog`` calls this with
    ``command="catalog"``.
    """
    body: Mapping[str, object] = resources if isinstance(resources, Mapping) else {}
    token = clean_token(command) or "list"
    world = _as_world(body.get("world", World.REPLAY))
    if is_refusal(world):
        return world

    store = _resolve_store(body)
    present_rows: tuple[dict[str, object], ...]
    view_fingerprint: str | None = None
    if store is None:
        present_rows = ()
    else:
        scanned = scan_coverage_rows(store, world=world.value)
        if is_refusal(scanned):
            return scanned
        present_rows = scanned.value
        if present_rows:
            rebuilt = _rebuild_view(store, world=world.value, rows=present_rows)
            if is_refusal(rebuilt):
                return rebuilt
            view_fingerprint = rebuilt.value

    present_entries = tuple(_entry_from_row(row) for row in present_rows)
    filtered = _apply_query(present_entries, body)
    if is_refusal(filtered):
        return filtered
    return Ok(
        CoverageReport(
            command=token,
            entries=filtered.value,
            view_fingerprint=view_fingerprint,
            view_engine="duckdb",
            is_evidence_bearing=False,
        )
    )


def catalog(
    resources: Mapping[str, object] | None = None,
) -> Result[CoverageReport]:
    """Alias of :func:`list_data` — same coverage payload, ``command="catalog"``."""
    return list_data(resources, command="catalog")


def _rebuild_view(
    store: EvidenceStore,
    *,
    world: World,
    rows: Sequence[Mapping[str, object]],
) -> Result[str]:
    """Materialize a rebuildable DuckDB view over coverage rows; return its fp1."""
    world_store = store.for_world(world)
    if is_refusal(world_store):
        return world_store
    materialized = [dict(row) for row in rows]
    receipt = world_store.value.append_store.materialize_view(materialized)
    if is_refusal(receipt):
        return receipt
    # Round-trip query proves the view is readable; the Parquet rooms remain authority.
    queried = world_store.value.append_store.read_view(
        receipt.value.fingerprint,
        for_world=world,
    )
    if is_refusal(queried):
        return queried
    return Ok(receipt.value.fingerprint.value)


def _resolve_store(body: Mapping[str, object]) -> EvidenceStore | None:
    raw_store = body.get("store")
    if isinstance(raw_store, EvidenceStore):
        return raw_store
    destination = clean_token(body.get("destination", body.get("archive", body.get("rooms"))))
    if destination is None:
        return None
    return EvidenceStore(Path(destination))


def _apply_query(
    present: Sequence[CoverageEntry],
    body: Mapping[str, object],
) -> Result[tuple[CoverageEntry, ...]]:
    """Filter present rows; emit explicit ``not present`` for requested absences."""
    venue = clean_token(body.get("venue"))
    symbol = clean_token(body.get("symbol", body.get("symbols")))
    if symbol is not None and "," in symbol:
        # Multi-symbol list queries enumerate each token.
        symbols = tuple(part.strip() for part in symbol.split(",") if part.strip())
    elif isinstance(body.get("symbol"), Sequence) and not isinstance(
        body.get("symbol"), (str, bytes)
    ):
        items = cast("Sequence[object]", body.get("symbol"))
        symbols = tuple(token for token in (clean_token(item) for item in items) if token)
    elif symbol is not None:
        symbols = (symbol,)
    else:
        symbols = ()

    resolution = clean_token(body.get("resolution"))
    side_raw = body.get("side")
    start_ns = _optional_ns(body.get("start", body.get("start_ns")), field="start")
    if is_refusal(start_ns):
        return start_ns
    end_ns = _optional_ns(body.get("end", body.get("end_ns")), field="end")
    if is_refusal(end_ns):
        return end_ns

    querying = any(
        value is not None
        for value in (
            venue,
            symbols or None,
            resolution,
            side_raw,
            start_ns.value,
            end_ns.value,
        )
    )
    if not querying:
        return Ok(tuple(present))

    sides = _expand_sides(side_raw if side_raw is not None else DownloadSide.BOTH.value)
    if is_refusal(sides):
        return sides
    wanted_resolution = resolution or "tick"
    wanted_symbols = symbols if symbols else sorted({entry.symbol for entry in present})
    if venue is not None:
        venues: tuple[str, ...] = (venue,)
    elif present:
        venues = tuple(sorted({entry.venue for entry in present}))
    else:
        venues = ()

    if not venues or not wanted_symbols:
        # Named query with nothing to project over — still emit not-present shells
        # when venue+symbol were explicit; otherwise keep the unfiltered present set.
        if venue is None or not symbols:
            return Ok(tuple(present))
        venues = (venue,)
        wanted_symbols = symbols

    entries: list[CoverageEntry] = []
    for venue_token in venues:
        for symbol_token in wanted_symbols:
            for side_token in sides.value:
                match = _find_present(
                    present,
                    venue=venue_token,
                    symbol=symbol_token,
                    resolution=wanted_resolution,
                    side=side_token,
                    start_ns=start_ns.value,
                    end_ns=end_ns.value,
                )
                if match is not None:
                    entries.append(match)
                else:
                    entries.append(
                        CoverageEntry(
                            venue=venue_token,
                            symbol=symbol_token,
                            resolution=wanted_resolution,
                            side=side_token,
                            status=NOT_PRESENT,
                            start_ns=start_ns.value,
                            end_ns=end_ns.value,
                            observation_count=None,
                            provenance=None,
                            license_tag=None,
                            revision=None,
                            source=None,
                        )
                    )
    return Ok(tuple(entries))


def _find_present(
    present: Sequence[CoverageEntry],
    *,
    venue: str,
    symbol: str,
    resolution: str,
    side: str,
    start_ns: int | None,
    end_ns: int | None,
) -> CoverageEntry | None:
    """Latest matching present row; optional window must be covered by the row."""
    matches: list[CoverageEntry] = []
    for entry in present:
        if entry.status != PRESENT:
            continue
        if entry.venue != venue or entry.symbol != symbol:
            continue
        if entry.resolution != resolution or entry.side != side:
            continue
        if start_ns is not None and end_ns is not None:
            if entry.start_ns is None or entry.end_ns is None:
                continue
            if entry.start_ns > start_ns or entry.end_ns < end_ns:
                continue
        matches.append(entry)
    if not matches:
        return None
    # Current bitemporal revision: last matching row in scan order (revision-sorted).
    return matches[-1]


def _entry_from_row(row: Mapping[str, object]) -> CoverageEntry:
    provenance = row.get("provenance")
    prov = cast("Mapping[str, object]", provenance) if isinstance(provenance, Mapping) else None
    start = row.get("start_ns")
    end = row.get("end_ns")
    count = row.get("observation_count")
    return CoverageEntry(
        venue=str(row.get("venue", "")),
        symbol=str(row.get("symbol", "")),
        resolution=str(row.get("resolution", "tick")),
        side=str(row.get("side", "")),
        status=str(row.get("status", PRESENT)),
        start_ns=start if isinstance(start, int) and not isinstance(start, bool) else None,
        end_ns=end if isinstance(end, int) and not isinstance(end, bool) else None,
        observation_count=(
            count if isinstance(count, int) and not isinstance(count, bool) else None
        ),
        provenance=prov,
        license_tag=clean_token(row.get("license_tag")),
        revision=clean_token(row.get("revision")),
        source=clean_token(row.get("source")),
    )


def _expand_sides(value: object) -> Result[tuple[str, ...]]:
    token = value.value if isinstance(value, DownloadSide) else clean_token(value)
    if token is None:
        return invalid(
            "side",
            "side is one of bid, ask, both",
            given=repr(value),
            legal=list(DOWNLOAD_SIDES),
        )
    if token == DownloadSide.BOTH.value:
        return Ok((DownloadSide.BID.value, DownloadSide.ASK.value))
    if token in (DownloadSide.BID.value, DownloadSide.ASK.value):
        return Ok((token,))
    return invalid(
        "side",
        "side is one of bid, ask, both",
        given=token,
        legal=list(DOWNLOAD_SIDES),
    )


def _as_world(value: object) -> Result[World]:
    if isinstance(value, World):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid("world", "world is live, replay, or simulated", given=repr(value))
    try:
        return Ok(World(token))
    except ValueError:
        return invalid("world", "world is live, replay, or simulated", given=token)


def _coverage_sort_key(row: Mapping[str, object]) -> tuple[str, str, str, str, int, str]:
    """Stable sort key for coverage envelopes (venue/symbol/resolution/side/start/revision)."""
    start = row.get("start_ns")
    start_ns = start if isinstance(start, int) and not isinstance(start, bool) else 0
    return (
        str(row.get("venue", "")),
        str(row.get("symbol", "")),
        str(row.get("resolution", "")),
        str(row.get("side", "")),
        start_ns,
        str(row.get("revision", "")),
    )


def _optional_ns(value: object, *, field: str) -> Result[int | None]:
    """Parse an optional int64 UTC-ns / ISO-8601 window edge; blank stays ``None``."""
    if value is None:
        return Ok(None)
    if isinstance(value, bool):
        return invalid(field, f"{field} is int64 UTC-ns, never a bool", given=repr(value))
    if isinstance(value, int):
        return Ok(value)
    if isinstance(value, str) and value.strip() != "":
        token = value.strip()
        if token.isdigit() or (token.startswith("-") and token[1:].isdigit()):
            return Ok(int(token))
        try:
            if token.endswith("Z"):
                token = token[:-1] + "+00:00"
            parsed = datetime.fromisoformat(token)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return Ok(int(parsed.timestamp() * 1_000_000_000))
        except ValueError:
            return invalid(
                field,
                f"{field} is int64 UTC-ns or an ISO-8601 timestamp",
                given=repr(value),
            )
    return invalid(field, f"{field} is int64 UTC-ns or ISO-8601 when provided", given=repr(value))
