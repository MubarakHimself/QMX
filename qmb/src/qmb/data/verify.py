"""``qmb data verify`` — window integrity (Story 18.4, B-11).

Checks an acquired window for bid/ask presence, monotonic int64 UTC-ns
timestamps, and exact scaled-integer prices with no float taint. Never
fabricates or fills gaps. Edge tolerance is a configurable interface with no
invented default — blank leaves the guard un-armed and reports raw offsets.
Pass/fail is a factual data-quality verdict (never an edge claim), journaled
through CT-13 with a propagated ``correlation_id``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, cast

from qmf.core.chrono import WriterId
from qmf.core.fingerprint import World
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.data.journal_producer import JournalWriter
from qmf.data.observation import SourceObservation
from qmf.data.store import EvidenceStore, ParquetColumnarEngine, StoreEngineError
from qmf.data.store.rooms import namespace_for_write

from qmb._refuse import clean_token, invalid, policy
from qmb.data.catalog import NOT_PRESENT, PRESENT, scan_coverage_rows
from qmb.data.ports import DOWNLOAD_SIDES, DownloadSide

__all__ = [
    "INTEGRITY_KIND",
    "IntegrityCounts",
    "IntegrityDefect",
    "InteriorGap",
    "VerifyRequest",
    "VerifyVerdict",
    "parse_verify_request",
    "verify",
    "verify_identity",
]

INTEGRITY_KIND: Final[str] = "qmb-data-window-integrity"
_RAW_ARCHIVE: Final[str] = "immutable-raw-archive"
_JOURNAL_STREAM: Final[str] = "dq"
_VERDICT_PASS: Final[str] = "pass"  # noqa: S105 — verdict token, not a secret
_VERDICT_FAIL: Final[str] = "fail"


@dataclass(frozen=True, slots=True)
class IntegrityDefect:
    """One machine-readable integrity defect (never a silent pass)."""

    code: str
    detail: str
    context: Mapping[str, object]

    def as_mapping(self) -> dict[str, object]:
        return {
            "code": self.code,
            "detail": self.detail,
            "context": dict(self.context),
        }


@dataclass(frozen=True, slots=True)
class InteriorGap:
    """Reported interior hole — never filled (synthetic fill is Epic 23)."""

    start_ns: int
    end_ns: int
    expected_step_ns: int
    delta_ns: int

    def as_mapping(self) -> dict[str, object]:
        return {
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "expected_step_ns": self.expected_step_ns,
            "delta_ns": self.delta_ns,
            "filled": False,
        }


@dataclass(frozen=True, slots=True)
class IntegrityCounts:
    """Observation / defect / gap tallies for the typed verify result."""

    observation_count: int
    bid_present: int
    ask_present: int
    defect_count: int
    interior_gap_count: int
    price_taint_count: int
    non_monotonic_count: int

    def as_mapping(self) -> dict[str, object]:
        return {
            "observation_count": self.observation_count,
            "bid_present": self.bid_present,
            "ask_present": self.ask_present,
            "defect_count": self.defect_count,
            "interior_gap_count": self.interior_gap_count,
            "price_taint_count": self.price_taint_count,
            "non_monotonic_count": self.non_monotonic_count,
        }


@dataclass(frozen=True, slots=True)
class VerifyRequest:
    """Parsed window + integrity-guard configuration."""

    archive: str
    venue: str
    symbol: str
    start_ns: int
    end_ns: int
    resolution: str
    side: DownloadSide
    edge_tolerance_ns: int | None
    expected_step_ns: int | None
    world: World
    correlation_id: str | None
    ticks: tuple[Mapping[str, object], ...] | None


@dataclass(frozen=True, slots=True)
class VerifyVerdict:
    """Factual data-quality pass payload (never an edge- or verdict-bearing claim)."""

    command: str
    kind: str
    verdict: str
    is_edge_claim: bool
    venue: str
    symbol: str
    resolution: str
    side: str
    start_ns: int
    end_ns: int
    edge_tolerance_ns: int | None
    edge_guard_armed: bool
    edge_start_offset_ns: int | None
    edge_end_offset_ns: int | None
    counts: IntegrityCounts
    defects: tuple[IntegrityDefect, ...]
    interior_gaps: tuple[InteriorGap, ...]
    correlation_id: str | None
    journaled: bool
    journal_sequence: int | None

    def as_mapping(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "command": self.command,
            "kind": self.kind,
            "verdict": self.verdict,
            "is_edge_claim": self.is_edge_claim,
            "venue": self.venue,
            "symbol": self.symbol,
            "resolution": self.resolution,
            "side": self.side,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "edge_guard_armed": self.edge_guard_armed,
            "counts": self.counts.as_mapping(),
            "defects": tuple(item.as_mapping() for item in self.defects),
            "interior_gaps": tuple(item.as_mapping() for item in self.interior_gaps),
            "journaled": self.journaled,
            "fills_gaps": False,
        }
        # fp1 forbids null — omit blank optional keys.
        if self.edge_tolerance_ns is not None:
            payload["edge_tolerance_ns"] = self.edge_tolerance_ns
        if self.edge_start_offset_ns is not None:
            payload["edge_start_offset_ns"] = self.edge_start_offset_ns
        if self.edge_end_offset_ns is not None:
            payload["edge_end_offset_ns"] = self.edge_end_offset_ns
        if self.correlation_id is not None:
            payload["correlation_id"] = self.correlation_id
        if self.journal_sequence is not None:
            payload["journal_sequence"] = self.journal_sequence
        return payload


def verify_identity() -> dict[str, object]:
    """Identity-bearing verify fields. Package SemVer is omitted.

    No invented edge-tolerance number is recorded: the guard arms only when the
    caller supplies ``edge_tolerance_ns`` (SC-07). ``null`` is omitted from fp1.
    """
    return {
        "integrity_kind": INTEGRITY_KIND,
        "edge_guard_requires_explicit_tolerance": True,
        "fills_gaps": False,
        "verdict_is_edge_claim": False,
        "journals_ct13_data_quality": True,
    }


def parse_verify_request(resources: Mapping[str, object]) -> Result[VerifyRequest]:
    """Validate door/library resources into a :class:`VerifyRequest`."""
    archive = clean_token(resources.get("archive", resources.get("destination")))
    if archive is None:
        return invalid(
            "archive",
            "verify names a non-empty archive / destination root",
            given=repr(resources.get("archive", resources.get("destination"))),
        )
    venue = clean_token(resources.get("venue"))
    if venue is None:
        return invalid(
            "venue",
            "verify names a non-empty venue token",
            given=repr(resources.get("venue")),
        )
    symbol = clean_token(resources.get("symbol", resources.get("symbols")))
    if symbol is None:
        raw_symbols = resources.get("symbol", resources.get("symbols"))
        if isinstance(raw_symbols, Sequence) and not isinstance(raw_symbols, (str, bytes)):
            items = cast("Sequence[object]", raw_symbols)
            tokens = tuple(token for token in (clean_token(item) for item in items) if token)
            if len(tokens) == 1:
                symbol = tokens[0]
            elif len(tokens) > 1:
                return invalid(
                    "symbol",
                    "verify checks one symbol window at a time",
                    given=repr(tokens),
                )
        if symbol is None:
            return invalid(
                "symbol",
                "verify names a non-empty symbol token",
                given=repr(resources.get("symbol", resources.get("symbols"))),
            )
    start = _as_ns(resources.get("start", resources.get("start_ns")), field="start")
    if is_refusal(start):
        return start
    end = _as_ns(resources.get("end", resources.get("end_ns")), field="end")
    if is_refusal(end):
        return end
    if end.value <= start.value:
        return invalid(
            "window",
            "verify window is a non-empty half-open [start, end)",
            start_ns=start.value,
            end_ns=end.value,
        )
    resolution = clean_token(resources.get("resolution")) or "tick"
    side = _as_side(resources.get("side", DownloadSide.BOTH.value))
    if is_refusal(side):
        return side
    tolerance = _optional_nonneg_ns(
        resources.get("edge_tolerance_ns", resources.get("edge_tolerance")),
        field="edge_tolerance_ns",
    )
    if is_refusal(tolerance):
        return tolerance
    step = _optional_nonneg_ns(
        resources.get("expected_step_ns", resources.get("expected_step")),
        field="expected_step_ns",
    )
    if is_refusal(step):
        return step
    world = _as_world(resources.get("world", World.REPLAY))
    if is_refusal(world):
        return world
    correlation = _optional_correlation(resources.get("correlation_id"))
    if is_refusal(correlation):
        return correlation
    ticks = _optional_ticks(resources.get("ticks", resources.get("observations")))
    if is_refusal(ticks):
        return ticks
    return Ok(
        VerifyRequest(
            archive=archive,
            venue=venue,
            symbol=symbol,
            start_ns=start.value,
            end_ns=end.value,
            resolution=resolution,
            side=side.value,
            edge_tolerance_ns=tolerance.value,
            expected_step_ns=step.value,
            world=world.value,
            correlation_id=correlation.value,
            ticks=ticks.value,
        )
    )


def verify(
    resources: Mapping[str, object],
    *,
    store: EvidenceStore | None = None,
    writer: WriterId | None = None,
    journal_writer: JournalWriter | None = None,
) -> Result[VerifyVerdict]:
    """Check window integrity; defects are CT-04 refusals with context."""
    parsed = parse_verify_request(resources)
    if is_refusal(parsed):
        return parsed
    request = parsed.value

    evidence = store
    if evidence is None:
        raw_store = resources.get("store")
        if isinstance(raw_store, EvidenceStore):
            evidence = raw_store
        else:
            evidence = EvidenceStore(Path(request.archive))

    rows = _load_rows(request, evidence=evidence, resources=resources)
    if is_refusal(rows):
        return rows

    defects: list[IntegrityDefect] = []
    interior_gaps: list[InteriorGap] = []
    bid_present = 0
    ask_present = 0
    price_taint = 0
    non_monotonic = 0
    timestamps: list[int] = []

    if not rows.value:
        defects.append(
            IntegrityDefect(
                code="empty_provider_return",
                detail="provider/window returned no observations for the requested range",
                context={
                    "venue": request.venue,
                    "symbol": request.symbol,
                    "start_ns": request.start_ns,
                    "end_ns": request.end_ns,
                },
            )
        )
    else:
        for index, row in enumerate(rows.value):
            ts = _row_timestamp_ns(row)
            if is_refusal(ts):
                defects.append(
                    IntegrityDefect(
                        code="non_integer_timestamp",
                        detail="timestamps must be monotonic int64 UTC-ns",
                        context={
                            "index": index,
                            "given": repr(row.get("t_ns", row.get("event_time_ns"))),
                        },
                    )
                )
                continue
            if timestamps and ts.value < timestamps[-1]:
                non_monotonic += 1
                defects.append(
                    IntegrityDefect(
                        code="non_monotonic_timestamp",
                        detail="timestamps must be monotonic non-decreasing int64 UTC-ns",
                        context={
                            "index": index,
                            "previous_ns": timestamps[-1],
                            "event_time_ns": ts.value,
                        },
                    )
                )
            timestamps.append(ts.value)

            bid = _row_side_price(row, side="bid")
            ask = _row_side_price(row, side="ask")
            if bid.present:
                bid_present += 1
            if ask.present:
                ask_present += 1
            if bid.tainted:
                price_taint += 1
                defects.append(
                    IntegrityDefect(
                        code="non_integer_price_taint",
                        detail="prices are exact scaled integers with no float taint (CT-01/AR-15)",
                        context={"index": index, "side": "bid", "given": repr(bid.given)},
                    )
                )
            if ask.tainted:
                price_taint += 1
                defects.append(
                    IntegrityDefect(
                        code="non_integer_price_taint",
                        detail="prices are exact scaled integers with no float taint (CT-01/AR-15)",
                        context={"index": index, "side": "ask", "given": repr(ask.given)},
                    )
                )
            lone = _row_lone_price(row)
            if lone.tainted:
                price_taint += 1
                defects.append(
                    IntegrityDefect(
                        code="non_integer_price_taint",
                        detail="prices are exact scaled integers with no float taint (CT-01/AR-15)",
                        context={"index": index, "side": "price", "given": repr(lone.given)},
                    )
                )

        if request.side is DownloadSide.BOTH:
            missing = _missing_both_sides(
                request=request,
                evidence=evidence,
                bid_present=bid_present,
                ask_present=ask_present,
                rows=rows.value,
            )
            if is_refusal(missing):
                return missing
            defects.extend(missing.value)

        if request.expected_step_ns is not None and len(timestamps) >= 2:
            step = request.expected_step_ns
            for index in range(1, len(timestamps)):
                delta = timestamps[index] - timestamps[index - 1]
                if delta > step:
                    interior_gaps.append(
                        InteriorGap(
                            start_ns=timestamps[index - 1],
                            end_ns=timestamps[index],
                            expected_step_ns=step,
                            delta_ns=delta,
                        )
                    )

    edge_start: int | None = None
    edge_end: int | None = None
    if timestamps:
        edge_start = max(0, timestamps[0] - request.start_ns)
        edge_end = max(0, request.end_ns - timestamps[-1])
        if request.edge_tolerance_ns is not None:
            limit = request.edge_tolerance_ns
            if edge_start > limit:
                defects.append(
                    IntegrityDefect(
                        code="edge_offset_beyond_tolerance",
                        detail="leading edge offset exceeds armed edge tolerance",
                        context={
                            "edge": "start",
                            "offset_ns": edge_start,
                            "tolerance_ns": limit,
                            "first_ns": timestamps[0],
                            "start_ns": request.start_ns,
                        },
                    )
                )
            if edge_end > limit:
                defects.append(
                    IntegrityDefect(
                        code="edge_offset_beyond_tolerance",
                        detail="trailing edge offset exceeds armed edge tolerance",
                        context={
                            "edge": "end",
                            "offset_ns": edge_end,
                            "tolerance_ns": limit,
                            "last_ns": timestamps[-1],
                            "end_ns": request.end_ns,
                        },
                    )
                )

    counts = IntegrityCounts(
        observation_count=len(rows.value),
        bid_present=bid_present,
        ask_present=ask_present,
        defect_count=len(defects),
        interior_gap_count=len(interior_gaps),
        price_taint_count=price_taint,
        non_monotonic_count=non_monotonic,
    )
    verdict_token = _VERDICT_FAIL if defects else _VERDICT_PASS
    journal_sequence = _journal_verdict(
        request=request,
        evidence=evidence,
        writer=writer,
        journal_writer=journal_writer,
        resources=resources,
        verdict=verdict_token,
        counts=counts,
        defects=tuple(defects),
        interior_gaps=tuple(interior_gaps),
        edge_start_offset_ns=edge_start,
        edge_end_offset_ns=edge_end,
    )
    if is_refusal(journal_sequence):
        return journal_sequence

    payload = VerifyVerdict(
        command="verify",
        kind=INTEGRITY_KIND,
        verdict=verdict_token,
        is_edge_claim=False,
        venue=request.venue,
        symbol=request.symbol,
        resolution=request.resolution,
        side=request.side.value,
        start_ns=request.start_ns,
        end_ns=request.end_ns,
        edge_tolerance_ns=request.edge_tolerance_ns,
        edge_guard_armed=request.edge_tolerance_ns is not None,
        edge_start_offset_ns=edge_start,
        edge_end_offset_ns=edge_end,
        counts=counts,
        defects=tuple(defects),
        interior_gaps=tuple(interior_gaps),
        correlation_id=request.correlation_id,
        journaled=True,
        journal_sequence=journal_sequence.value,
    )
    if defects:
        return policy(
            "window_integrity",
            "window integrity defects refuse governed use of this window (CT-04)",
            signal="window-integrity-defect",
            kind=INTEGRITY_KIND,
            verdict=_VERDICT_FAIL,
            is_edge_claim=False,
            fills_gaps=False,
            result=payload.as_mapping(),
        )
    return Ok(payload)


# --- loaders ----------------------------------------------------------------


def _load_rows(
    request: VerifyRequest,
    *,
    evidence: EvidenceStore,
    resources: Mapping[str, object],
) -> Result[tuple[Mapping[str, object], ...]]:
    if request.ticks is not None:
        return Ok(request.ticks)
    injected = resources.get("rows")
    if isinstance(injected, Sequence) and not isinstance(injected, (str, bytes)):
        parsed = _optional_ticks(cast("Sequence[object]", injected))
        if is_refusal(parsed):
            return parsed
        if parsed.value is not None:
            return Ok(parsed.value)
    return _scan_observation_rows(evidence, request=request)


def _scan_observation_rows(
    store: EvidenceStore, *, request: VerifyRequest
) -> Result[tuple[Mapping[str, object], ...]]:
    namespace = namespace_for_write(request.world)
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
            mapping = cast("Mapping[str, object]", item)
            if mapping.get("kind") == "qmb-data-coverage":
                continue
            rebuilt = SourceObservation.from_row(mapping)
            if is_refusal(rebuilt):
                # Non-observation artifacts (coverage already skipped) stay out.
                if "event_time_ns" not in mapping:
                    continue
                # Persist float-tainted / corrupt rows as raw material for defect checks.
                event = mapping.get("event_time_ns")
                if (
                    isinstance(event, int)
                    and not isinstance(event, bool)
                    and request.start_ns <= event < request.end_ns
                ):
                    rows.append(dict(mapping))
                continue
            event_ns = rebuilt.value.event_time.value_ns
            if event_ns < request.start_ns or event_ns >= request.end_ns:
                continue
            native = rebuilt.value.source_native_id
            # Symbol scoping for archive scans rides coverage / caller ticks;
            # CT-10 rows are kept when their event-time falls in the window.
            row: dict[str, object] = {
                "t_ns": event_ns,
                "event_time_ns": event_ns,
                "source_native_id": native,
                "fingerprint": rebuilt.value.fingerprint.value,
            }
            money = rebuilt.value.foreign_money
            if money is not None:
                row["price"] = {"verbatim": money.verbatim, "scale": money.scale}
            # Coverage-backed bid/ask presence is checked separately; CT-10 rows
            # may carry only foreign_money when quotes were not persisted.
            rows.append(row)
    rows.sort(key=lambda item: int(cast("int", item.get("t_ns", 0))))
    return Ok(tuple(rows))


def _missing_both_sides(
    *,
    request: VerifyRequest,
    evidence: EvidenceStore,
    bid_present: int,
    ask_present: int,
    rows: Sequence[Mapping[str, object]],
) -> Result[list[IntegrityDefect]]:
    defects: list[IntegrityDefect] = []
    # Prefer explicit tick-side fields when the window carries them.
    has_side_fields = any("bid" in row or "ask" in row for row in rows)
    if has_side_fields:
        if bid_present == 0:
            defects.append(
                IntegrityDefect(
                    code="missing_requested_side",
                    detail="side=both requires bid stream present",
                    context={"side": "bid", "bid_present": bid_present, "ask_present": ask_present},
                )
            )
        if ask_present == 0:
            defects.append(
                IntegrityDefect(
                    code="missing_requested_side",
                    detail="side=both requires ask stream present",
                    context={"side": "ask", "bid_present": bid_present, "ask_present": ask_present},
                )
            )
        return Ok(defects)

    scanned = scan_coverage_rows(evidence, world=request.world)
    if is_refusal(scanned):
        return scanned
    present_sides: set[str] = set()
    for row in scanned.value:
        if row.get("kind") != "qmb-data-coverage" and row.get("status") not in {PRESENT, None}:
            continue
        if str(row.get("venue", "")) != request.venue:
            continue
        if str(row.get("symbol", "")) != request.symbol:
            continue
        resolution = str(row.get("resolution", "tick"))
        if resolution != request.resolution:
            continue
        status = str(row.get("status", PRESENT))
        if status != PRESENT:
            continue
        side_token = clean_token(row.get("side"))
        if side_token in {DownloadSide.BID.value, DownloadSide.ASK.value}:
            present_sides.add(side_token)
    if DownloadSide.BID.value not in present_sides and bid_present == 0:
        defects.append(
            IntegrityDefect(
                code="missing_requested_side",
                detail="side=both requires bid stream present",
                context={
                    "side": "bid",
                    "coverage_status": NOT_PRESENT,
                    "present_sides": sorted(present_sides),
                },
            )
        )
    if DownloadSide.ASK.value not in present_sides and ask_present == 0:
        defects.append(
            IntegrityDefect(
                code="missing_requested_side",
                detail="side=both requires ask stream present",
                context={
                    "side": "ask",
                    "coverage_status": NOT_PRESENT,
                    "present_sides": sorted(present_sides),
                },
            )
        )
    return Ok(defects)


def _journal_verdict(
    *,
    request: VerifyRequest,
    evidence: EvidenceStore,
    writer: WriterId | None,
    journal_writer: JournalWriter | None,
    resources: Mapping[str, object],
    verdict: str,
    counts: IntegrityCounts,
    defects: tuple[IntegrityDefect, ...],
    interior_gaps: tuple[InteriorGap, ...],
    edge_start_offset_ns: int | None,
    edge_end_offset_ns: int | None,
) -> Result[int]:
    """Record pass/fail through CT-13 data quality; propagate correlation_id."""
    active = journal_writer
    if active is None:
        raw_jw = resources.get("journal_writer")
        if isinstance(raw_jw, JournalWriter):
            active = raw_jw
    if active is None:
        world_store = evidence.for_world(request.world)
        if is_refusal(world_store):
            return world_store
        active_writer = writer
        if active_writer is None:
            raw_writer = resources.get("writer")
            if isinstance(raw_writer, WriterId):
                active_writer = raw_writer
        if active_writer is None:
            minted = WriterId.try_create("qmb", "data", "verify", "boot-1")
            if is_refusal(minted):
                return minted
            active_writer = minted.value
        active = JournalWriter(
            world_store.value.journal,
            active_writer,
            stream_name=_JOURNAL_STREAM,
        )

    payload: dict[str, object] = {
        "signal": "window-integrity",
        "component": "COMP-QMB",
        "contract": "CT-13",
        "event_type_wire": "data quality",
        "kind": INTEGRITY_KIND,
        "command": "verify",
        "verdict": verdict,
        "is_edge_claim": False,
        "fills_gaps": False,
        "venue": request.venue,
        "symbol": request.symbol,
        "resolution": request.resolution,
        "side": request.side.value,
        "start_ns": request.start_ns,
        "end_ns": request.end_ns,
        "edge_guard_armed": request.edge_tolerance_ns is not None,
        "counts": counts.as_mapping(),
        "defects": [item.as_mapping() for item in defects],
        "interior_gaps": [item.as_mapping() for item in interior_gaps],
    }
    # fp1 identity forbids null — omit blank optional keys rather than store None.
    if request.edge_tolerance_ns is not None:
        payload["edge_tolerance_ns"] = request.edge_tolerance_ns
    if edge_start_offset_ns is not None:
        payload["edge_start_offset_ns"] = edge_start_offset_ns
    if edge_end_offset_ns is not None:
        payload["edge_end_offset_ns"] = edge_end_offset_ns
    instant = resources.get("journal_instant", request.end_ns)
    recorded = active.record_data_quality(
        payload,
        instant=instant,
        correlation_id=request.correlation_id,
    )
    if is_refusal(recorded):
        return recorded
    return Ok(recorded.value.event.sequence)


# --- row / value helpers ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class _SidePrice:
    present: bool
    tainted: bool
    given: object


def _row_side_price(row: Mapping[str, object], *, side: str) -> _SidePrice:
    if side not in row:
        return _SidePrice(present=False, tainted=False, given=None)
    value = row.get(side)
    if value is None:
        return _SidePrice(present=False, tainted=False, given=None)
    check = _price_exact(value)
    if check is None:
        return _SidePrice(present=True, tainted=False, given=value)
    return _SidePrice(present=True, tainted=True, given=check)


def _row_lone_price(row: Mapping[str, object]) -> _SidePrice:
    if "price" not in row and "foreign_money" not in row:
        return _SidePrice(present=False, tainted=False, given=None)
    value = row.get("price", row.get("foreign_money"))
    check = _price_exact(value)
    if check is None:
        return _SidePrice(present=True, tainted=False, given=value)
    return _SidePrice(present=True, tainted=True, given=check)


def _price_exact(value: object) -> object | None:
    """Return a taint marker when ``value`` is not an exact scaled integer."""
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return None
    if isinstance(value, float):
        return value
    if isinstance(value, Mapping):
        body = cast("Mapping[str, object]", value)
        verbatim = body.get("verbatim")
        scale = body.get("scale")
        if isinstance(verbatim, bool) or isinstance(scale, bool):
            return cast("object", value)
        if isinstance(verbatim, float) or isinstance(scale, float):
            return cast("object", value)
        if isinstance(verbatim, int) and isinstance(scale, int) and scale >= 0:
            return None
        return cast("object", value)
    return value


def _row_timestamp_ns(row: Mapping[str, object]) -> Result[int]:
    raw = row.get("t_ns", row.get("event_time_ns"))
    if isinstance(raw, (bool, float)):
        return invalid(
            "timestamp",
            "timestamps are monotonic int64 UTC-ns, never float or bool",
            given=repr(raw),
        )
    if isinstance(raw, int):
        return Ok(raw)
    return invalid(
        "timestamp",
        "timestamps are monotonic int64 UTC-ns",
        given=repr(raw),
    )


def _as_side(value: object) -> Result[DownloadSide]:
    if isinstance(value, DownloadSide):
        return Ok(value)
    token = clean_token(value)
    if token is None:
        return invalid(
            "side",
            "side is one of bid, ask, both",
            given=repr(value),
            legal=list(DOWNLOAD_SIDES),
        )
    try:
        return Ok(DownloadSide(token))
    except ValueError:
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


def _as_ns(value: object, *, field: str) -> Result[int]:
    if isinstance(value, bool):
        return invalid(field, f"{field} is int64 UTC-ns, never a bool", given=repr(value))
    if isinstance(value, int):
        return Ok(value)
    if isinstance(value, float):
        return invalid(field, f"{field} is int64 UTC-ns, never a float", given=repr(value))
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
            return invalid(field, f"{field} is int64 UTC-ns or ISO-8601", given=value)
    return invalid(field, f"{field} is required int64 UTC-ns", given=repr(value))


def _optional_nonneg_ns(value: object, *, field: str) -> Result[int | None]:
    """Blank / omitted stays ``None`` (guard un-armed); never invent a default."""
    if value is None:
        return Ok(None)
    if isinstance(value, str) and value.strip() == "":
        return Ok(None)
    if isinstance(value, bool):
        return invalid(
            field, f"{field} is a non-negative int64 ns count, never a bool", given=repr(value)
        )
    if isinstance(value, float):
        return invalid(
            field, f"{field} is a non-negative int64 ns count, never a float", given=repr(value)
        )
    if isinstance(value, int):
        if value < 0:
            return invalid(field, f"{field} is a non-negative int64 ns count", given=value)
        return Ok(value)
    if isinstance(value, str) and value.strip().isdigit():
        return Ok(int(value.strip()))
    return invalid(field, f"{field} is a non-negative int64 ns count or blank", given=repr(value))


def _optional_correlation(value: object) -> Result[str | None]:
    if value is None:
        return Ok(None)
    if isinstance(value, str) and value.strip() == "":
        return Ok(None)
    token = clean_token(value)
    if token is None:
        return invalid(
            "correlation_id",
            "correlation_id, when present, is a non-blank linking annotation",
            given=repr(value),
        )
    return Ok(token)


def _optional_ticks(value: object) -> Result[tuple[Mapping[str, object], ...] | None]:
    if value is None:
        return Ok(None)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return invalid(
            "ticks",
            "ticks is a sequence of observation mappings",
            given=repr(type(value).__name__),
        )
    items = cast("Sequence[object]", value)
    rows: list[Mapping[str, object]] = []
    for index, item in enumerate(items):
        if not isinstance(item, Mapping):
            return invalid(
                "ticks",
                "each tick is a mapping with int64 timestamps and exact prices",
                index=index,
                given=repr(type(item).__name__),
            )
        rows.append(cast("Mapping[str, object]", item))
    return Ok(tuple(rows))
