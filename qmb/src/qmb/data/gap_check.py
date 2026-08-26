"""``qmb data gap-check`` — calendar-aware gap detection (Story 18.5, B-11).

Resolves expected sessions from a CT-02 versioned market-hours calendar,
computes expected-bars-minus-present-bars inside open sessions, and reports
gaps as ``(start, end, expected, present)``. Calendar-closed absence is
closure, not a gap. Missing or unresolvable calendar is ``unavailable
dependency`` (CT-04) — never silently treated as always-open. Never writes
interior fill (Epic 23 / ``world=simulated``; policy rejection until GAP-0048).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core.chrono import CalendarIdentity, Instant, SessionWindow
from qmf.core.fingerprint import World
from qmf.core.refusal import Ok, Result, is_refusal
from qmf.data.observation import SourceObservation
from qmf.data.store import EvidenceStore, ParquetColumnarEngine, StoreEngineError
from qmf.data.store.rooms import namespace_for_write

from qmb._refuse import clean_token, invalid, policy, unavailable
from qmb.data.ports import DOWNLOAD_SIDES, DownloadSide

__all__ = [
    "GAP_CHECK_KIND",
    "AlwaysOpenCalendar",
    "GapCheckReport",
    "GapCheckRequest",
    "ReportedGap",
    "gap_check",
    "gap_check_identity",
    "parse_gap_check_request",
]

GAP_CHECK_KIND: Final[str] = "qmb-data-gap-check"
_RAW_ARCHIVE: Final[str] = "immutable-raw-archive"
_HOUR_NS: Final[int] = 3_600_000_000_000
_FX_VENUE_MARKERS: Final[tuple[str, ...]] = ("fx", "forex", "dukascopy")
_FOREX_RULE_SETS: Final[frozenset[str]] = frozenset({"forex-17NY", "forex", "qmf-calendar-forex"})


@runtime_checkable
class MarketHoursCalendar(Protocol):
    """Minimal CT-02 market-hours surface gap-check consumes."""

    identity: CalendarIdentity

    def session_window(self, instant: object) -> Result[SessionWindow | None]:
        """Open session containing ``instant``, or ``None`` when closed."""
        ...


@dataclass(frozen=True, slots=True)
class AlwaysOpenCalendar:
    """CT-02 always-open market-hours calendar for 24/7 venues.

    Every interior non-present interval inside the requested window is a
    genuine gap — no closure exemption applies.
    """

    identity: CalendarIdentity
    always_open: bool = True

    def session_window(self, instant: object) -> Result[SessionWindow | None]:
        if not isinstance(instant, Instant):
            return invalid(
                "instant",
                "session_window takes an Instant",
                given=repr(instant),
            )
        # Wide open span containing the probe; enumeration special-cases always_open.
        open_ns = instant.value_ns - (_HOUR_NS * 24 * 365)
        close_ns = instant.value_ns + (_HOUR_NS * 24 * 365)
        opened = Instant.try_create(open_ns)
        if is_refusal(opened):
            opened = Instant.try_create(instant.value_ns)
            if is_refusal(opened):
                return opened
        closed = Instant.try_create(close_ns)
        if is_refusal(closed):
            closed = Instant.try_create(instant.value_ns + 1)
            if is_refusal(closed):
                return closed
        window = SessionWindow.try_create(opened.value, closed.value, "UTC")
        if is_refusal(window):
            return window
        return Ok(cast("SessionWindow | None", window.value))


@dataclass(frozen=True, slots=True)
class ReportedGap:
    """One calendar-open shortfall — never filled."""

    start_ns: int
    end_ns: int
    expected: int
    present: int

    def as_mapping(self) -> dict[str, object]:
        return {
            "start": self.start_ns,
            "end": self.end_ns,
            "expected": self.expected,
            "present": self.present,
            "filled": False,
        }


@dataclass(frozen=True, slots=True)
class GapCheckRequest:
    """Parsed window + bar step + calendar resolution inputs."""

    archive: str
    venue: str
    symbol: str
    start_ns: int
    end_ns: int
    resolution: str
    side: DownloadSide
    bar_step_ns: int
    world: World
    calendar_rule_set: str | None
    always_open: bool
    ticks: tuple[Mapping[str, object], ...] | None


@dataclass(frozen=True, slots=True)
class GapCheckReport:
    """Deterministic gap set for one window + one CT-02 calendar version."""

    command: str
    kind: str
    venue: str
    symbol: str
    resolution: str
    side: str
    start_ns: int
    end_ns: int
    bar_step_ns: int
    calendar: Mapping[str, object]
    gaps: tuple[ReportedGap, ...]
    open_session_count: int
    fills_gaps: bool

    def as_mapping(self) -> dict[str, object]:
        return {
            "command": self.command,
            "kind": self.kind,
            "venue": self.venue,
            "symbol": self.symbol,
            "resolution": self.resolution,
            "side": self.side,
            "start_ns": self.start_ns,
            "end_ns": self.end_ns,
            "bar_step_ns": self.bar_step_ns,
            "calendar": dict(self.calendar),
            "gaps": tuple(item.as_mapping() for item in self.gaps),
            "open_session_count": self.open_session_count,
            "fills_gaps": self.fills_gaps,
        }


def gap_check_identity() -> dict[str, object]:
    """Identity-bearing gap-check fields. Package SemVer is omitted."""
    return {
        "gap_check_kind": GAP_CHECK_KIND,
        "fills_gaps": False,
        "calendar_authority": "CT-02",
        "missing_calendar_is_unavailable_dependency": True,
        "never_guess_always_open": True,
        "synthetic_fill_deferred_to": "GAP-0048",
    }


def parse_gap_check_request(resources: Mapping[str, object]) -> Result[GapCheckRequest]:
    """Validate door/library resources into a :class:`GapCheckRequest`."""
    fill_flag = resources.get("fill", resources.get("fabricate", resources.get("write_fill")))
    if fill_flag is True or fill_flag in {"true", 1}:
        return policy(
            "fill",
            "gap-check only reports gaps and never writes interior fill; "
            "synthetic fill is world=simulated / Epic 23 and a policy rejection "
            "for governed evidence until GAP-0048",
            signal="refuse-interior-fill",
            gap="GAP-0048",
            fills_gaps=False,
        )

    archive = clean_token(resources.get("archive", resources.get("destination")))
    if archive is None:
        return invalid(
            "archive",
            "gap-check names a non-empty archive / destination root",
            given=repr(resources.get("archive", resources.get("destination"))),
        )
    venue = clean_token(resources.get("venue"))
    if venue is None:
        return invalid(
            "venue",
            "gap-check names a non-empty venue token",
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
                    "gap-check checks one symbol window at a time",
                    given=repr(tokens),
                )
        if symbol is None:
            return invalid(
                "symbol",
                "gap-check names a non-empty symbol token",
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
            "gap-check window is a non-empty half-open [start, end)",
            start_ns=start.value,
            end_ns=end.value,
        )
    resolution = clean_token(resources.get("resolution")) or "tick"
    side = _as_side(resources.get("side", DownloadSide.BOTH.value))
    if is_refusal(side):
        return side
    step = _positive_ns(
        resources.get("bar_step_ns", resources.get("expected_step_ns")),
        field="bar_step_ns",
    )
    if is_refusal(step):
        return step
    world = _as_world(resources.get("world", World.REPLAY))
    if is_refusal(world):
        return world
    rule_set = clean_token(
        resources.get(
            "calendar_rule_set",
            resources.get("calendar_provider", resources.get("rule_set")),
        )
    )
    always_open = _as_bool_flag(resources.get("always_open"), field="always_open")
    if is_refusal(always_open):
        return always_open
    ticks = _optional_ticks(resources.get("ticks", resources.get("observations")))
    if is_refusal(ticks):
        return ticks
    return Ok(
        GapCheckRequest(
            archive=archive,
            venue=venue,
            symbol=symbol,
            start_ns=start.value,
            end_ns=end.value,
            resolution=resolution,
            side=side.value,
            bar_step_ns=step.value,
            world=world.value,
            calendar_rule_set=rule_set,
            always_open=always_open.value,
            ticks=ticks.value,
        )
    )


def gap_check(
    resources: Mapping[str, object],
    *,
    store: EvidenceStore | None = None,
    calendar: MarketHoursCalendar | None = None,
) -> Result[GapCheckReport]:
    """Detect calendar-aware gaps; never fabricate fill."""
    parsed = parse_gap_check_request(resources)
    if is_refusal(parsed):
        return parsed
    request = parsed.value

    resolved = calendar
    if resolved is None:
        raw_cal = resources.get("calendar")
        if raw_cal is not None:
            if not isinstance(raw_cal, MarketHoursCalendar):
                return invalid(
                    "calendar",
                    "calendar must expose CT-02 identity and session_window",
                    given=repr(type(raw_cal).__name__),
                )
            resolved = raw_cal
        else:
            resolved_result = _resolve_calendar(request, resources=resources)
            if is_refusal(resolved_result):
                return resolved_result
            resolved = resolved_result.value

    identity = resolved.identity

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
    present_ns = _present_timestamps(rows.value)
    if is_refusal(present_ns):
        return present_ns

    spans = _open_spans(resolved, start_ns=request.start_ns, end_ns=request.end_ns)
    if is_refusal(spans):
        return spans

    gaps = _gaps_for_spans(
        spans=spans.value,
        present=present_ns.value,
        step_ns=request.bar_step_ns,
    )
    calendar_payload = {
        "rule_set": identity.rule_set,
        "rule_set_version": identity.rule_set_version,
        "tzdata_version": identity.tzdata_version,
    }
    return Ok(
        GapCheckReport(
            command="gap-check",
            kind=GAP_CHECK_KIND,
            venue=request.venue,
            symbol=request.symbol,
            resolution=request.resolution,
            side=request.side.value,
            start_ns=request.start_ns,
            end_ns=request.end_ns,
            bar_step_ns=request.bar_step_ns,
            calendar=calendar_payload,
            gaps=gaps,
            open_session_count=len(spans.value),
            fills_gaps=False,
        )
    )


# --- calendar resolution ----------------------------------------------------


def _resolve_calendar(
    request: GapCheckRequest, *, resources: Mapping[str, object]
) -> Result[MarketHoursCalendar]:
    """Resolve a CT-02 calendar or refuse unavailable-dependency — never guess."""
    if request.always_open:
        identity = _always_open_identity(resources)
        if is_refusal(identity):
            return identity
        return Ok(cast("MarketHoursCalendar", AlwaysOpenCalendar(identity=identity.value)))

    rule = request.calendar_rule_set
    if rule is not None and rule.lower() in {"always-open", "always_open", "24/7", "247"}:
        identity = _always_open_identity(resources)
        if is_refusal(identity):
            return identity
        return Ok(cast("MarketHoursCalendar", AlwaysOpenCalendar(identity=identity.value)))

    wants_forex = (rule is not None and rule in _FOREX_RULE_SETS) or _looks_like_fx_venue(
        request.venue
    )
    if wants_forex:
        return _load_forex_calendar(venue=request.venue, symbol=request.symbol, rule_set=rule)

    return unavailable(
        "calendar",
        "gap-check cannot decide open-vs-closed without a resolvable CT-02 "
        "market-hours calendar; an unknown calendar is never treated as always-open",
        venue=request.venue,
        symbol=request.symbol,
        calendar_rule_set=rule,
        signal="unavailable-calendar",
    )


def _always_open_identity(resources: Mapping[str, object]) -> Result[CalendarIdentity]:
    raw = resources.get("calendar_identity")
    if isinstance(raw, CalendarIdentity):
        return Ok(raw)
    rule_set = clean_token(resources.get("rule_set")) or "always-open"
    version = clean_token(resources.get("rule_set_version")) or "v1"
    tzdata = clean_token(resources.get("tzdata_version")) or "none"
    return CalendarIdentity.try_create(rule_set, version, tzdata)


def _looks_like_fx_venue(venue: str) -> bool:
    lowered = venue.lower()
    return any(marker in lowered for marker in _FX_VENUE_MARKERS)


def _load_forex_calendar(
    *, venue: str, symbol: str, rule_set: str | None
) -> Result[MarketHoursCalendar]:
    try:
        from qmf.calendar_forex import get_provider  # noqa: PLC0415 — optional extension
    except ImportError as exc:  # pragma: no cover - env without extension
        return unavailable(
            "calendar",
            "qmf-calendar-forex is required for FX venue gap-check and is not importable",
            venue=venue,
            symbol=symbol,
            calendar_rule_set=rule_set,
            detail=str(exc),
            signal="unavailable-calendar",
        )
    provider = get_provider()
    if is_refusal(provider):
        # Preserve the extension's unavailable-dependency refusal (tzdb pin / readiness).
        return provider
    return Ok(cast("MarketHoursCalendar", provider.value))


# --- open-session enumeration -----------------------------------------------


def _open_spans(
    calendar: MarketHoursCalendar, *, start_ns: int, end_ns: int
) -> Result[tuple[tuple[int, int], ...]]:
    if getattr(calendar, "always_open", False):
        return Ok(((start_ns, end_ns),))

    spans: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    probe = start_ns
    # Cap iterations: window hours + sessions, with a hard safety bound.
    max_steps = max(8, ((end_ns - start_ns) // _HOUR_NS) + 64)
    steps = 0
    while probe < end_ns and steps < max_steps:
        steps += 1
        instant = Instant.try_create(probe)
        if is_refusal(instant):
            return instant
        window = calendar.session_window(instant.value)
        if is_refusal(window):
            # Boundary refusals: advance one hour rather than abort the scan.
            if window.context.get("field") == "instant":
                probe += _HOUR_NS
                continue
            return window
        if window.value is None:
            probe += _HOUR_NS
            continue
        open_ns = window.value.open_instant.value_ns
        close_ns = window.value.close_instant.value_ns
        key = (open_ns, close_ns)
        if key not in seen:
            seen.add(key)
            clipped_start = max(open_ns, start_ns)
            clipped_end = min(close_ns, end_ns)
            if clipped_start < clipped_end:
                spans.append((clipped_start, clipped_end))
        next_probe = close_ns if close_ns > probe else probe + _HOUR_NS
        probe = next_probe

    spans.sort(key=lambda item: item[0])
    return Ok(tuple(spans))


def _gaps_for_spans(
    *,
    spans: Sequence[tuple[int, int]],
    present: Sequence[int],
    step_ns: int,
) -> tuple[ReportedGap, ...]:
    """Contiguous missing expected-bar runs inside open spans only."""
    present_sorted = sorted(present)
    gaps: list[ReportedGap] = []
    for span_start, span_end in spans:
        expected_slots = _expected_slots(span_start, span_end, step_ns)
        if not expected_slots:
            continue
        run_start: int | None = None
        run_slots = 0
        for slot in expected_slots:
            occupied = _slot_occupied(slot, step_ns, span_end, present_sorted)
            if occupied:
                if run_start is not None:
                    gaps.append(
                        ReportedGap(
                            start_ns=run_start,
                            end_ns=slot,
                            expected=run_slots,
                            present=0,
                        )
                    )
                    run_start = None
                    run_slots = 0
                continue
            if run_start is None:
                run_start = slot
                run_slots = 1
            else:
                run_slots += 1
        if run_start is not None:
            gaps.append(
                ReportedGap(
                    start_ns=run_start,
                    end_ns=span_end,
                    expected=run_slots,
                    present=0,
                )
            )
    gaps.sort(key=lambda item: (item.start_ns, item.end_ns))
    return tuple(gaps)


def _expected_slots(start_ns: int, end_ns: int, step_ns: int) -> tuple[int, ...]:
    if step_ns <= 0 or end_ns <= start_ns:
        return ()
    count = (end_ns - start_ns) // step_ns
    return tuple(start_ns + (index * step_ns) for index in range(count))


def _slot_occupied(slot: int, step_ns: int, span_end: int, present: Sequence[int]) -> bool:
    hi = min(slot + step_ns, span_end)
    # present is sorted; linear scan is fine for tier-1 windows.
    for stamp in present:
        if stamp >= hi:
            break
        if stamp >= slot:
            return True
    return False


# --- loaders ----------------------------------------------------------------


def _load_rows(
    request: GapCheckRequest,
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
    store: EvidenceStore, *, request: GapCheckRequest
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
            rows.append(
                {
                    "t_ns": event_ns,
                    "event_time_ns": event_ns,
                    "source_native_id": rebuilt.value.source_native_id,
                }
            )
    rows.sort(key=lambda item: int(cast("int", item.get("t_ns", 0))))
    return Ok(tuple(rows))


def _present_timestamps(rows: Sequence[Mapping[str, object]]) -> Result[tuple[int, ...]]:
    stamps: list[int] = []
    for index, row in enumerate(rows):
        raw = row.get("t_ns", row.get("event_time_ns"))
        if isinstance(raw, (bool, float)):
            return invalid(
                "timestamp",
                "timestamps are monotonic int64 UTC-ns, never float or bool",
                index=index,
                given=repr(raw),
            )
        if isinstance(raw, int):
            stamps.append(raw)
            continue
        return invalid(
            "timestamp",
            "timestamps are monotonic int64 UTC-ns",
            index=index,
            given=repr(raw),
        )
    return Ok(tuple(stamps))


# --- value helpers ----------------------------------------------------------


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


def _positive_ns(value: object, *, field: str) -> Result[int]:
    """Bar step is required and positive — never invented (SC-07)."""
    if value is None or (isinstance(value, str) and value.strip() == ""):
        return invalid(
            field,
            f"{field} is required: gap-check needs an explicit bar step to compute "
            "expected bars; no default is invented",
            given=repr(value),
        )
    if isinstance(value, bool):
        return invalid(
            field,
            f"{field} is a positive int64 ns count, never a bool",
            given=repr(value),
        )
    if isinstance(value, float):
        return invalid(
            field,
            f"{field} is a positive int64 ns count, never a float",
            given=repr(value),
        )
    if isinstance(value, int):
        if value <= 0:
            return invalid(field, f"{field} is a positive int64 ns count", given=value)
        return Ok(value)
    if isinstance(value, str) and value.strip().isdigit():
        parsed = int(value.strip())
        if parsed <= 0:
            return invalid(field, f"{field} is a positive int64 ns count", given=parsed)
        return Ok(parsed)
    return invalid(field, f"{field} is a positive int64 ns count", given=repr(value))


def _as_bool_flag(value: object, *, field: str) -> Result[bool]:
    if value is None:
        return Ok(False)
    if isinstance(value, bool):
        return Ok(value)
    if isinstance(value, str):
        token = value.strip().lower()
        if token in {"", "0", "false", "no"}:
            return Ok(False)
        if token in {"1", "true", "yes"}:
            return Ok(True)
    return invalid(field, f"{field} is a boolean flag", given=repr(value))


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
                "each tick is a mapping with int64 timestamps",
                index=index,
                given=repr(type(item).__name__),
            )
        rows.append(cast("Mapping[str, object]", item))
    return Ok(tuple(rows))
