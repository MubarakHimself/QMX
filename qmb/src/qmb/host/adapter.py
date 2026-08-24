"""QL-7 runtime-protocol adapter at QMB's composition root (DEC-0177).

A run spec that cites a CT-33 Bot by ``fp1`` constructs the bot via
``qml.protocol.construct_bot`` / ``FunctionFactory`` / ``HostedBot`` and drives
it per evaluation instant with declared-footprint evidence only. Ungoverned
plain-Python bots never require this path (QL-1).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

from qmf.core.chrono import Instant
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Ok, Result, is_refusal
from qml.protocol import FunctionFactory, HostedBot, construct_bot
from qml.protocol.intents import BotIntent

from qmb._refuse import invalid
from qmb.runloop.loop import RestingIntent, SilentSliceHandler

__all__ = [
    "ConformantSliceHandler",
    "FunctionFactory",
    "HostedBot",
    "construct_conformant_bot",
    "drive_instant",
]


def construct_conformant_bot(
    factory: object,
    *,
    declaration: object,
    assignment: object,
    read_surfaces: object,
    protocol_format_version: object = None,
    state_scope: object = None,
    state_bound: object = None,
) -> Result[HostedBot]:
    """Construct via the QL-7 factory (declaration, assignment, read surfaces).

    Hosts inject only declared-footprint evidence. No Book module, clock, or
    venue command surface is ever passed through.
    """
    kwargs: dict[str, object] = {
        "declaration": declaration,
        "assignment": assignment,
        "read_surfaces": read_surfaces,
    }
    if protocol_format_version is not None:
        kwargs["protocol_format_version"] = protocol_format_version
    if state_scope is not None:
        kwargs["state_scope"] = state_scope
    if state_bound is not None:
        kwargs["state_bound"] = state_bound
    return construct_bot(factory, **kwargs)


def drive_instant(hosted: object, instant: object) -> Result[tuple[BotIntent, ...]]:
    """Drive a hosted CT-33 bot at one evaluation instant (QL-7, AR-65)."""
    if not isinstance(hosted, HostedBot):
        return invalid(
            "hosted",
            "QMB drives a HostedBot constructed through the QL-7 factory",
            given=type(hosted).__name__,
        )
    return hosted.on_instant(instant)


@dataclass(frozen=True, slots=True)
class ConformantSliceHandler(SilentSliceHandler):
    """SliceHandler that mints from a HostedBot on one declared stream.

    Strategy callbacks (sub-phase 5) drive the QL-7 callback at the frontier
    Instant. Other streams in the same slice emit no tokens, so a multi-stream
    slice does not duplicate intents. New intents rest for a later slice.
    """

    hosted: HostedBot
    stream_id: str

    def mint_intents(self, stream_id: str, frontier: Instant) -> Result[object]:
        if stream_id != self.stream_id:
            return Ok(())
        intents = drive_instant(self.hosted, frontier)
        if is_refusal(intents):
            return intents
        tokens = _to_resting(intents.value, stream_id)
        if is_refusal(tokens):
            return tokens
        return Ok(cast("object", tokens.value))


def _to_resting(intents: object, stream_id: str) -> Result[tuple[RestingIntent, ...]]:
    if intents is None:
        return Ok(())
    if isinstance(intents, Mapping):
        return invalid(
            "intents",
            "QL-7 callbacks return zero-or-more CT-23 intents, never a mapping",
            given="mapping",
        )
    if isinstance(intents, (tuple, list)):
        sequence = tuple(cast("Sequence[object]", intents))
    else:
        sequence = (intents,)
    tokens: list[RestingIntent] = []
    for index, intent in enumerate(sequence):
        identity = getattr(intent, "fp1_identity", None)
        if not callable(identity):
            return invalid(
                "intents",
                "each QL-7 intent carries fp1 identity so resting tokens are deterministic",
                index=index,
                given=type(intent).__name__,
            )
        stamped = fingerprint(identity())
        if is_refusal(stamped):
            return stamped
        token = RestingIntent.try_create(f"{stamped.value.value}:{index}", stream_id)
        if is_refusal(token):
            return token
        tokens.append(token.value)
    return Ok(tuple(tokens))
