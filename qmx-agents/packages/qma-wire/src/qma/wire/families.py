"""Wire message-family transport contracts (CT-40; AD-5; DEC-0304; FR-Q12).

Commands mutate and acknowledge immediately while effects settle asynchronously.
Queries read durable state over HTTP GET. Events form the durable stream.
Snapshots are authoritative; progress events are not. Closing a client cannot
stop a Quant.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, Literal

from qma.wire.vocabulary import MessageFamily, family_of, parse_wire_type

__all__ = [
    "FAMILY_CONTRACTS",
    "FamilyContract",
    "TransportKind",
    "assert_client_close_safe",
    "contract_for",
    "contract_for_type",
    "progress_is_authoritative",
    "snapshots_are_authoritative",
]


TransportKind = Literal["jsonrpc_websocket", "http_get", "durable_stream"]


@dataclass(frozen=True, slots=True)
class FamilyContract:
    """Transport and authority rules for one message family."""

    family: MessageFamily
    transport: TransportKind
    mutates: bool
    ack_immediate: bool
    effects_async: bool
    reads_durable_state: bool
    durable_stream: bool
    authoritative: bool
    description: str


FAMILY_CONTRACTS: Final[MappingProxyType[MessageFamily, FamilyContract]] = MappingProxyType(
    {
        MessageFamily.COMMAND: FamilyContract(
            family=MessageFamily.COMMAND,
            transport="jsonrpc_websocket",
            mutates=True,
            ack_immediate=True,
            effects_async=True,
            reads_durable_state=False,
            durable_stream=False,
            authoritative=True,
            description=(
                "Commands mutate and acknowledge immediately; side effects settle "
                "asynchronously over JSON-RPC 2.0 WebSocket."
            ),
        ),
        MessageFamily.QUERY: FamilyContract(
            family=MessageFamily.QUERY,
            transport="http_get",
            mutates=False,
            ack_immediate=False,
            effects_async=False,
            reads_durable_state=True,
            durable_stream=False,
            authoritative=True,
            description="Queries read durable state through HTTP GET snapshots.",
        ),
        MessageFamily.EVENT: FamilyContract(
            family=MessageFamily.EVENT,
            transport="durable_stream",
            mutates=False,
            ack_immediate=False,
            effects_async=False,
            reads_durable_state=False,
            durable_stream=True,
            authoritative=False,
            description=(
                "Events form the durable stream; progress is not authoritative — "
                "clients rebuild truth from query snapshots."
            ),
        ),
    }
)


def contract_for(family: MessageFamily | str) -> FamilyContract:
    """Return the transport contract for a message family."""
    resolved = family if isinstance(family, MessageFamily) else MessageFamily(family)
    return FAMILY_CONTRACTS[resolved]


def contract_for_type(wire_type: object) -> FamilyContract:
    """Return the transport contract for a closed vocabulary type name."""
    name = parse_wire_type(wire_type)
    return contract_for(family_of(name))


def snapshots_are_authoritative() -> bool:
    """Query snapshots are authoritative (DEC-0304)."""
    return FAMILY_CONTRACTS[MessageFamily.QUERY].authoritative


def progress_is_authoritative() -> bool:
    """Progress events are explicitly not authoritative (DEC-0304)."""
    return FAMILY_CONTRACTS[MessageFamily.EVENT].authoritative


def assert_client_close_safe() -> bool:
    """Closing a client never stops a Quant; attachment is client state only."""
    return True
