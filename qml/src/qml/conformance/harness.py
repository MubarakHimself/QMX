"""Determinism harness for Layer 2 (QL-8).

Drives a hosted bot over a golden slice. Pure: uses the runtime protocol's
in-memory factory/callback path. Hosts that spawn a process feed the same
trace shape to the verdict function (DEC-0178).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, TypeAlias, cast

from qmf.core.refusal import Ok, Result, TypedRefusal, is_refusal

from qml._refuse import invalid
from qml.conformance.slice import GoldenSlice, read_surfaces_for_slice
from qml.protocol.factory import HostedBot, construct_bot, restore_bot
from qml.protocol.intents import intent_identity
from qml.protocol.state import BotStateSnapshot

__all__ = [
    "INTENT_KIND_ENTRY",
    "drive_golden_slice",
    "intent_kind",
    "intent_trace_kinds",
    "traces_equal",
]

INTENT_KIND_ENTRY: Final[str] = "entry"
IntentTrace: TypeAlias = tuple[tuple[dict[str, object], ...], ...]


def intent_kind(identity: object) -> Result[str]:
    """CT-23 kind token of one intent identity: ``entry`` or an exit kind name."""
    if not isinstance(identity, Mapping):
        return invalid(
            "intent",
            "an intent identity is a mapping carrying intent_family",
            given=type(identity).__name__,
        )
    mapping = cast("Mapping[str, object]", identity)
    family = mapping.get("intent_family")
    if family == INTENT_KIND_ENTRY:
        return Ok(INTENT_KIND_ENTRY)
    kind = mapping.get("kind")
    if isinstance(kind, str) and kind.strip() != "":
        return Ok(kind)
    return invalid(
        "intent",
        "an intent identity names intent_family entry or an exit kind",
        given=repr(family),
    )


def intent_trace_kinds(
    trace: Sequence[tuple[Mapping[str, object], ...]],
) -> Result[tuple[str, ...]]:
    """Flatten emitted kinds from a per-instant intent-identity trace."""
    kinds: list[str] = []
    for instant in trace:
        for item in instant:
            kind = intent_kind(item)
            if is_refusal(kind):
                return kind
            kinds.append(kind.value)
    return Ok(tuple(kinds))


def traces_equal(
    first: Sequence[tuple[Mapping[str, object], ...]],
    second: Sequence[tuple[Mapping[str, object], ...]],
) -> bool:
    """True when two golden-slice runs produced identical intent identities."""
    if len(first) != len(second):
        return False
    return tuple(tuple(dict(item) for item in instant) for instant in first) == tuple(
        tuple(dict(item) for item in instant) for instant in second
    )


def drive_golden_slice(hosted: object, slice_: object) -> Result[IntentTrace]:
    """Drive one hosted bot through every golden-slice instant.

    Returns the per-instant tuple of intent ``fp1`` identities. A door refusal
    (non-permitted kind, malformed intent) is returned as-is so the verdict
    function can classify it as a Layer-2 failure.
    """
    if not isinstance(hosted, HostedBot):
        return invalid(
            "hosted",
            "the determinism harness drives a HostedBot constructed with no Book",
            given=type(hosted).__name__,
        )
    if not isinstance(slice_, GoldenSlice):
        return invalid(
            "golden_slice",
            "the determinism harness is keyed off a GoldenSlice fixture",
            given=type(slice_).__name__,
        )
    steps: list[tuple[dict[str, object], ...]] = []
    for instant in slice_.evaluation_instants:
        raw = hosted.on_instant(instant)
        if is_refusal(raw):
            return raw
        steps.append(tuple(intent_identity(item) for item in raw.value))
    return Ok(tuple(steps))


def construct_for_slice(
    factory: object,
    *,
    declaration: object,
    assignment: object,
    slice_: GoldenSlice,
    state_scope: object,
    state_bound: object,
) -> Result[HostedBot]:
    """Load logic in isolation against golden-slice read surfaces. No Book."""
    surfaces = read_surfaces_for_slice(slice_)
    if is_refusal(surfaces):
        return surfaces
    return construct_bot(
        factory,
        declaration=declaration,
        assignment=assignment,
        read_surfaces=surfaces.value,
        state_scope=state_scope,
        state_bound=state_bound,
    )


def restore_round_trip(
    factory: object,
    *,
    declaration: object,
    assignment: object,
    slice_: GoldenSlice,
    state_scope: object,
    state_bound: object,
) -> Result[bool]:
    """Snapshot after a prefix of the slice, restore, and compare state fingerprints."""
    hosted = construct_for_slice(
        factory,
        declaration=declaration,
        assignment=assignment,
        slice_=slice_,
        state_scope=state_scope,
        state_bound=state_bound,
    )
    if is_refusal(hosted):
        return hosted
    instants = slice_.evaluation_instants
    prefix = instants[:-1] if len(instants) > 1 else instants
    bot = hosted.value
    for instant in prefix:
        driven = bot.on_instant(instant)
        if is_refusal(driven):
            return driven
    captured = bot.snapshot()
    if is_refusal(captured):
        return captured
    surfaces = read_surfaces_for_slice(slice_)
    if is_refusal(surfaces):
        return surfaces
    restored = restore_bot(
        captured.value,
        factory,
        declaration=declaration,
        assignment=assignment,
        read_surfaces=surfaces.value,
        current_scope=state_scope,
    )
    if is_refusal(restored):
        return restored
    again = restored.value.snapshot()
    if is_refusal(again):
        return again
    return _snapshots_equivalent(captured.value, again.value)


def _snapshots_equivalent(first: BotStateSnapshot, second: BotStateSnapshot) -> Result[bool]:
    left = first.fingerprint()
    if is_refusal(left):
        return left
    right = second.fingerprint()
    if is_refusal(right):
        return right
    return Ok(left.value.value == right.value.value)


def drive_error_kind(refusal: TypedRefusal) -> str:
    """Map a protocol-door refusal onto a Layer-2 check name."""
    field = refusal.context.get("field")
    if field == "kind":
        return "permitted_intent_kinds"
    return "golden_slice_determinism"
