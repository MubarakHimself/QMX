"""Bot runtime protocol (QL-7).

A QML-owned format-versioned contract on QML's own AD-5 ladder, not CT-numbered
(DEC-0177). A conformant bot is a factory the host constructs with (declaration,
resolved assignment, injected read surfaces), returning a callback the host
drives per evaluation instant. Callbacks receive only declared-footprint
evidence and return zero-or-more CT-23 intents. The bot never sizes, never
touches venue commands, never reads a clock, and is never handed a Book module.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Protocol, TypeAlias, runtime_checkable

from qmf.core.chrono import Instant
from qmf.core.refusal import Ok, Result
from qmf.risk.door import EntryIntent, ExitIntent, ExitKind

from qml._refuse import invalid
from qml.protocol.contract import (
    PROTOCOL_CONTRACT_CLASS,
    PROTOCOL_DENIAL_SET,
    PROTOCOL_FORMAT_VERSION,
    PROTOCOL_KNOWN_FORMAT_VERSIONS,
    PROTOCOL_LADDER,
    coerce_protocol_format_version,
    protocol_contract_identity,
)
from qml.protocol.evidence import (
    FORBIDDEN_EVIDENCE_KEYS,
    FootprintEvidence,
    MappingReadSurface,
    PresenceMappedSeries,
    PresenceState,
    SeriesSample,
    StructureFold,
    collect_evidence,
    declared_evidence_keys,
)
from qml.protocol.factory import (
    FunctionFactory,
    HostedBot,
    construct_bot,
    resolve_assignment,
)
from qml.protocol.intents import (
    BOOK_SIDE_FIELDS,
    VENUE_COMMAND_FIELDS,
    accept_intents,
    intent_identity,
)

__all__ = [
    "BOOK_SIDE_FIELDS",
    "FORBIDDEN_EVIDENCE_KEYS",
    "PROTOCOL_CONTRACT_CLASS",
    "PROTOCOL_DENIAL_SET",
    "PROTOCOL_FORMAT_VERSION",
    "PROTOCOL_KNOWN_FORMAT_VERSIONS",
    "PROTOCOL_LADDER",
    "VENUE_COMMAND_FIELDS",
    "BotCallback",
    "BotFactory",
    "BotIntent",
    "FootprintEvidence",
    "FunctionFactory",
    "HostedBot",
    "MappingReadSurface",
    "PresenceMappedSeries",
    "PresenceState",
    "ReadSurface",
    "SeriesSample",
    "StructureFold",
    "accept_intents",
    "coerce_protocol_format_version",
    "collect_evidence",
    "construct_bot",
    "declared_evidence_keys",
    "intent_identity",
    "permitted_exit_kinds",
    "protocol_contract_identity",
    "resolve_assignment",
]

BotIntent: TypeAlias = EntryIntent | ExitIntent


@runtime_checkable
class ReadSurface(Protocol):
    """Host-injected evidence surface. Hosts inject read surfaces only (DEC-0178)."""

    def at(self, instant: Instant, /) -> object:
        """Evidence knowable at ``instant`` from one declared footprint key."""
        ...


@runtime_checkable
class BotCallback(Protocol):
    """Author callback: receives only declared-footprint evidence (DEC-0177)."""

    def on_instant(self, evidence: FootprintEvidence, /) -> object:
        """Return zero-or-more CT-23 intents from declared-footprint evidence."""
        ...


@runtime_checkable
class BotFactory(Protocol):
    """Constructs a callback from declaration, assignment, and read surfaces."""

    def construct(
        self,
        *,
        declaration: object,
        assignment: Mapping[str, object],
        read_surfaces: Mapping[str, ReadSurface],
    ) -> Result[BotCallback]:
        """Build the author callback the host wraps and drives per instant."""
        ...


def permitted_exit_kinds(names: Sequence[object]) -> Result[tuple[ExitKind, ...]]:
    """Validate a declared permitted EXIT-intent subset of the CT-23 vocabulary.

    ``entry`` is always permitted and is never listed. An empty set is legal
    (an entry-only bot). A name outside ``close_full | tighten_protective_stop``
    is ``invalid input`` (DEC-0173).
    """
    resolved: list[ExitKind] = []
    for name in names:
        if isinstance(name, ExitKind):
            resolved.append(name)
            continue
        if isinstance(name, str):
            try:
                resolved.append(ExitKind(name))
                continue
            except ValueError:
                pass
        return invalid(
            "permitted_exit_intents",
            "permitted EXIT-intent kinds must lie within the ratified CT-23 vocabulary",
            given=repr(name),
        )
    return Ok(tuple(resolved))
