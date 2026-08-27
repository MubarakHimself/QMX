"""Test-owned fixture builders for Epic 12 (qml-protocol).

Constructs a VALID conformant world through the public ``qml`` mint_* API only.
The factory/callback here is authored by the TEST — it is NOT imported from
``qml/examples`` — so the behavioural L1/L2/L3 tests do not lean on the shipped
example's recipe. (E12-L3-12 tests the shipped example separately, through its
own module.)

Nothing in this module asserts; it only builds inputs the tests drive through
public seams. A build failure raises AssertionError so a broken fixture never
masquerades as a green test.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from qmf.core.exact import PriceDelta, UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.identity import Instrument, VenueId
from qmf.core.refusal import Ok, is_ok
from qmf.risk.door import Direction, EntryIntent, ReasonCode
from qmf.risk.paper import ExecutionTarget
from qml.declaration import mint_bot_definition, mint_confluence
from qml.families import mint_strategy_family
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, PresenceState, mint_state_scope

FAMILY = "trend-follow"
STATE_BOUND = 256
_OS = "test-os-11"
_AR = "none"

# A clean, denial-set-free source tree used both as the logic-identity source
# and as the Layer-2 scan input. Contains no clock / io / network / random use.
CLEAN_SOURCE: dict[str, str] = {
    "qa_bot/__init__.py": "",
    "qa_bot/logic.py": "def build(assignment):\n    return dict(assignment)\n",
}


def unwrap(result: object, what: str = "value") -> Any:
    """Return the Ok value or raise — a broken fixture must never look green."""
    if is_ok(result):
        return result.value  # type: ignore[attr-defined]
    raise AssertionError(f"fixture build failed for {what}: {result!r}")


def _pinned(tag: str) -> ProducerBinding:
    fp = unwrap(fingerprint({"class": "qa-producer", "tag": tag}), f"producer fp {tag}")
    return unwrap(ProducerBinding.try_create(fp), f"binding {tag}")


def make_entry(stop_distance: int = 500) -> EntryIntent:
    """A conformant CT-23 entry intent carrying only an advisory stop proposal.

    Carries NO ``requested_r`` and NO bot-supplied full-loss price (the type has
    neither field). The advisory stop is the format-2 optional advisory field.
    """
    venue = unwrap(VenueId.try_create("ctrader"), "venue")
    instrument = unwrap(Instrument.try_create(venue, "EURUSD"), "instrument")
    target = unwrap(ExecutionTarget.try_create("live", venue, "acct-1"), "target")
    reason = unwrap(ReasonCode.try_create("breakout", FAMILY), "reason")
    stop = unwrap(PriceDelta.try_create(stop_distance, instrument, 5), "stop")
    return unwrap(
        EntryIntent.try_create(
            instrument, Direction.LONG, reason, target, advisory_stop_proposal=stop
        ),
        "entry",
    )


class Callback:
    """Host-driven callback. Deterministic; bounded tick state for snapshot/restore."""

    __slots__ = ("_entry", "_lookback", "_ticks")

    def __init__(self, lookback: int, entry: EntryIntent) -> None:
        self._lookback = lookback
        self._entry = entry
        self._ticks = 0

    def on_instant(self, evidence: object, /) -> object:
        self._ticks += 1
        if self._ticks < self._lookback:
            return ()
        series = getattr(evidence, "series", None)
        if not series:
            return ()
        for one in series.values():
            samples = getattr(one, "samples", ())
            if not samples or samples[-1].presence is not PresenceState.PRESENT:
                return ()
        return (self._entry,)

    def export_state(self) -> dict[str, object]:
        return {"ticks": self._ticks}

    def import_state(self, payload: Mapping[str, object]) -> None:
        value = payload.get("ticks")
        self._ticks = value if isinstance(value, int) and not isinstance(value, bool) else 0


class Factory:
    """Conformant factory: (declaration, assignment, read surfaces) -> callback."""

    def __init__(self, stop_distance: int = 500) -> None:
        self._stop_distance = stop_distance

    def construct(
        self,
        *,
        declaration: object,
        assignment: Mapping[str, object],
        read_surfaces: Mapping[str, object],
    ) -> object:
        del declaration, read_surfaces
        lookback = assignment.get("lookback", 1)
        if isinstance(lookback, bool) or not isinstance(lookback, int) or lookback < 1:
            lookback = 1
        return Ok(Callback(lookback, make_entry(self._stop_distance)))


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def _calendar() -> dict[str, object]:
    return {"rule_set": "forex-17NY", "rule_set_version": "v3", "tzdata_version": "2025.2"}


def parameter_space() -> list[dict[str, object]]:
    return [
        {
            "name": "lookback",
            "type": "exact integer",
            "bounds": {"min": 1, "max": 200},
            "step": 1,
            "default": 1,
            "unit_kind": UnitKind.COUNT,
            "ui": "ui-editable",
        },
        {
            "name": "stop_distance",
            "type": "exact integer",
            "bounds": {"min": 1, "max": 10_000},
            "step": 1,
            "default": 500,
            "unit_kind": UnitKind.COUNT,
            "ui": "ui-editable",
        },
    ]


def build_world(
    *,
    permitted: tuple[str, ...] = ("close_full",),
    drop_producer: bool = False,
) -> dict[str, object]:
    """Build a valid conformant world (declaration + drivable factory + catalogs).

    ``drop_producer=True`` omits one confluence-leg producer from the footprint so
    a Layer-1 transitive-union refusal can be exercised; the catalogs still carry
    every producer so reference-resolution succeeds and the completeness check is
    the one that fires.
    """
    zone = _pinned("zone")
    sma = _pinned("sma")
    session = _pinned("session")
    catalog_producers = [zone, sma, session]
    family = unwrap(mint_strategy_family(FAMILY), "family")
    confluence = unwrap(
        mint_confluence(
            [
                {"role": "level", "producer_binding": zone},
                {"role": "trigger", "producer_binding": sma},
                {"role": "filter", "producer_binding": session},
            ]
        ),
        "confluence",
    )
    footprint_producers = [zone, sma] if drop_producer else [zone, sma, session]
    footprint = unwrap(
        mint_footprint([_stream()], [_calendar()], footprint_producers), "footprint"
    )
    logic = unwrap(mint_logic_identity("qa-bot", "1.0.0", CLEAN_SOURCE), "logic")
    declaration = unwrap(
        mint_bot_definition(
            {
                "strategy_family_id": family.family_id.value,
                "confluence_set": [confluence],
                "parameter_space": parameter_space(),
                "footprint": footprint,
                "permitted_exit_intents": permitted,
                "logic_reference": logic,
            }
        ),
        "declaration",
    )
    return {
        "declaration": declaration,
        "family": family,
        "confluence": confluence,
        "logic": logic,
        "producers": footprint_producers,
        "catalog_producers": catalog_producers,
        "footprint": footprint,
        "factory": Factory(),
        "source": dict(CLEAN_SOURCE),
    }


def scope_for(
    declaration: object,
    *,
    os_name: str = _OS,
    arithmetic_reference_build: str = _AR,
    protocol_format_version: object = PROTOCOL_FORMAT_VERSION,
    logic_identity: object = None,
) -> object:
    return unwrap(
        mint_state_scope(
            os=os_name,
            logic_identity=logic_identity
            if logic_identity is not None
            else declaration.logic_reference,  # type: ignore[attr-defined]
            protocol_format_version=protocol_format_version,
            arithmetic_reference_build=arithmetic_reference_build,
        ),
        "scope",
    )


def declaration_mapping(**overrides: object) -> dict[str, object]:
    """A raw CT-33 declaration mapping (for refusal-path mutation tests)."""
    world = build_world()
    declaration = world["declaration"]
    family = world["family"]
    base: dict[str, object] = {
        "strategy_family_id": family.family_id.value,  # type: ignore[attr-defined]
        "confluence_set": [world["confluence"]],
        "parameter_space": parameter_space(),
        "footprint": declaration.footprint,  # type: ignore[attr-defined]
        "permitted_exit_intents": ["close_full"],
        "logic_reference": world["logic"],
    }
    base.update(overrides)
    return base
