"""Powers channel dispatch — authorize then enact via the shared library.

Transport authentication (Story 25.7) stays in ``powers.py``. This module
revalidates fresh state, enforces artifact-key idempotency through the library,
and journals requested versus enforced outcomes separately.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from qmf.core.refusal import Result, is_refusal

from qmn.doors._refuse import invalid
from qmn.doors.catalog import CLOSED_POWERS
from qmn.doors.http.powers import (
    POWERS_DOOR,
    PowersJournal,
    authorize_powers_call,
)
from qmn.doors.library import DoorRuntime, PowersEnactment, enact_power
from qmn.doors.wire import WIRE_FORMAT_VERSION, refusal_wire_shape

__all__ = [
    "POWERS_DISPATCH_SURFACE",
    "handle_powers_call",
    "powers_capability_surface",
    "render_powers_response",
]

POWERS_DISPATCH_SURFACE: Final[str] = "qmn.doors.http.dispatch"


def powers_capability_surface() -> frozenset[str]:
    """Library names the powers door adapts — derived from the dispatch path."""
    return frozenset({"enact_power"})


def handle_powers_call(
    runtime: object,
    *,
    peer: object,
    principals: object,
    power: object,
    artifact_key: object,
    evidence_knowledge_time_ns: object,
    requested: object,
    claimed_signer: object = None,
    journal: PowersJournal | None = None,
) -> Result[PowersEnactment]:
    """Authorize at the transport, then enact through the shared library."""
    if not isinstance(runtime, DoorRuntime):
        return invalid(
            "runtime",
            "powers dispatch requires a DoorRuntime",
            given=type(runtime).__name__,
        )
    authorized = authorize_powers_call(
        peer=peer,
        principals=principals,
        power=power,
        claimed_signer=claimed_signer,
        journal=journal,
    )
    if is_refusal(authorized):
        return authorized
    return enact_power(
        runtime,
        power=authorized.value.power,
        principal=authorized.value.principal,
        artifact_key=artifact_key,
        evidence_knowledge_time_ns=evidence_knowledge_time_ns,
        requested=requested,
    )


def render_powers_response(result: Result[PowersEnactment]) -> Mapping[str, object]:
    """Transport rendering for the unix-socket powers channel."""
    if is_refusal(result):
        return MappingProxyType(
            {
                **dict(refusal_wire_shape(result)),
                "door": POWERS_DOOR,
                "wire_format_version": WIRE_FORMAT_VERSION,
            }
        )
    body: dict[str, object] = dict(result.value.as_mapping())
    body["door"] = POWERS_DOOR
    body["ok"] = True
    return MappingProxyType(body)


def closed_power_names() -> frozenset[str]:
    """Closed powers list — the powers door's named act surface."""
    return frozenset(CLOSED_POWERS)
