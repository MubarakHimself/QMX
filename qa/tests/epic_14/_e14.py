"""Shared fixtures/helpers for the INDEPENDENT Epic 14 (qmb-run-loop) audit tests.

Assertions in the test modules assert what the RATIFIED requirements demand
(epics.md ACs + the QMB spine + CT-* contracts, per this epic's PLAN.md), never
what the source happens to do. This module only supplies construction mechanics
(building Instants, a resolved run-config, stub ports) so the requirement-level
assertions can run. A failing test is a FINDING, never a licence to soften an
assertion or edit source.
"""

from __future__ import annotations

from typing import TypeVar

from qmf.core.chrono import Instant
from qmf.core.fingerprint import World, fingerprint
from qmf.core.refusal import Ok, Result, is_ok
from qmb.config import ResolvedRunConfig
from qmb.runloop import RestingIntent, SliceObservation

STREAM_SET_KEY = "stream_set"

T = TypeVar("T")

# A fixed replay instant well inside the int64 (1677..2262) range.
NS: int = 1_700_000_000_000_000_000


def ok(result: Result[T]) -> T:
    """Unwrap an ``Ok`` or fail loudly with the refusal context."""
    assert is_ok(result), f"expected Ok, got refusal: {getattr(result, 'context', result)!r}"
    return result.value


def inst(ns: int = NS) -> Instant:
    return ok(Instant.try_create(ns))


def obs(stream_id: str, ns: int = NS, *, closed: bool = True) -> SliceObservation:
    return ok(SliceObservation.try_create(stream_id, inst(ns), closed))


def config(streams: tuple[str, ...] = ("eurusd", "gbpusd"), **keys: object) -> ResolvedRunConfig:
    """A resolved, world=replay run-config sufficient to mint a CT-32 witness.

    Built via the frozen dataclass (the trusted-internal constructor) so the
    loop's identity/determinism behaviour can be exercised without standing up
    the whole B-3 compiler. Same ``streams`` + same ``keys`` => same fingerprint.
    """
    stamp = ok(fingerprint({"n": "e14-cfg", "streams": list(streams), "keys": sorted(keys)}))
    payload: dict[str, object] = {STREAM_SET_KEY: streams}
    payload.update(keys)
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys=payload,
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )


def slices(
    streams: tuple[str, ...] = ("eurusd", "gbpusd"),
    n: int = 2,
) -> tuple[tuple[SliceObservation, ...], ...]:
    """``n`` completed event slices, one instant apart, over the declared streams."""
    return tuple(tuple(obs(s, NS + i) for s in streams) for i in range(n))


class RecordingHandler:
    """A SliceHandler (runtime Protocol) that records what each sub-phase saw.

    ``mint_on`` names a stream to mint one intent on in sub-phase 5 (or a count
    via ``mint_count``); ``fill`` is what execute_resting returns in sub-phase 3.
    """

    def __init__(
        self,
        *,
        mint_on: str | None = None,
        mint_count: int = 1,
        fill: bool = False,
    ) -> None:
        self.stream_updates: list[str] = []
        self.scheduled: list[str] = []
        self.executed: list[str] = []
        self.closed_updates: list[str] = []
        self._mint_on = mint_on
        self._mint_count = mint_count
        self._fill = fill
        self._minted = 0

    def update_stream(
        self,
        stream_id: str,
        observation: object,
        frontier: Instant,
    ) -> Result[None]:
        del observation, frontier
        self.stream_updates.append(stream_id)
        return Ok(None)

    def scheduled_position_event(self, stream_id: str, frontier: Instant) -> Result[None]:
        del frontier
        self.scheduled.append(stream_id)
        return Ok(None)

    def execute_resting(
        self,
        intent: RestingIntent,
        observation: object,
        frontier: Instant,
    ) -> Result[bool]:
        del observation, frontier
        self.executed.append(intent.intent_id)
        return Ok(self._fill)

    def update_closed_data(
        self,
        stream_id: str,
        observation: object,
        frontier: Instant,
    ) -> Result[None]:
        del observation, frontier
        self.closed_updates.append(stream_id)
        return Ok(None)

    def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
        del frontier
        if self._mint_on is None or stream_id != self._mint_on:
            return Ok(())
        tokens: list[RestingIntent] = []
        for _ in range(self._mint_count):
            self._minted += 1
            built = RestingIntent.try_create(f"mint-{stream_id}-{self._minted}", stream_id)
            tokens.append(ok(built))
        return Ok(tuple(tokens))
