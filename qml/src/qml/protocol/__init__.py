"""Bot runtime protocol seams (QL-7).

A conformant bot is a factory the host constructs with declaration, resolved
assignment, and injected read surfaces; callbacks receive only declared-footprint
evidence and return zero-or-more CT-23 intents. The bot never sizes, never
touches venue commands, never reads a clock, and is never handed a Book module
(DEC-0177). Format version is QML-local (AD-5 second ladder), not CT-numbered.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Final, Protocol, TypeAlias, runtime_checkable

from qmf.core.chrono import Instant
from qmf.core.refusal import Ok, Result
from qmf.risk.door import EntryIntent, ExitIntent, ExitKind

from qml._refuse import invalid

__all__ = [
    "PROTOCOL_FORMAT_VERSION",
    "BotCallback",
    "BotFactory",
    "BotIntent",
    "ReadSurface",
    "permitted_exit_kinds",
]

PROTOCOL_FORMAT_VERSION: Final[int] = 1

BotIntent: TypeAlias = EntryIntent | ExitIntent


@runtime_checkable
class ReadSurface(Protocol):
    """Host-injected evidence surface. Hosts inject read surfaces only (DEC-0178)."""

    def at(self, instant: Instant, /) -> Mapping[str, object]:  # pragma: no cover - protocol seam
        """Evidence knowable at ``instant`` from the declared footprint."""
        ...


@runtime_checkable
class BotCallback(Protocol):
    """Host-driven per-evaluation-instant callback (DEC-0177)."""

    def on_instant(  # pragma: no cover - protocol seam
        self, instant: Instant, /
    ) -> Result[tuple[BotIntent, ...]]:
        """Return zero-or-more CT-23 intents at ``instant``."""
        ...


@runtime_checkable
class BotFactory(Protocol):
    """Constructs a callback from declaration, assignment, and read surfaces."""

    def construct(  # pragma: no cover - protocol seam
        self,
        *,
        declaration: object,
        assignment: Mapping[str, object],
        read_surfaces: Mapping[str, ReadSurface],
    ) -> Result[BotCallback]:
        """Build the callback object the host drives per evaluation instant."""
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
