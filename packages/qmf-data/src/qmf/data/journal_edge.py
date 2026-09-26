"""CT-13 cross-stream causal linkage as typed edge records.

Split from :mod:`qmf.data.journal` so the public module stays under the Skylos
god-file limits. Callers keep importing :class:`CausalEdge` from
:mod:`qmf.data.journal`.
"""

from __future__ import annotations

from dataclasses import dataclass

from qmf.core import Fingerprint, Ok, Result, WriterId, is_refusal
from qmf.data.journal_event import JournalEvent
from qmf.data.journal_types import CONTRACT_FORMAT_VERSION, coerce_fingerprint, writer_identity
from qmf.data.store.refusals import invalid_input

__all__ = ["CausalEdge"]


@dataclass(frozen=True, slots=True)
class CausalEdge:
    """A cross-stream causal link as an AD-16 typed edge record (AC4; DEC-0114, DEC-0120).

    Causal linkage across journal streams rides **only** typed edge records — never a
    timestamp and never the ``(instant, writer, sequence)`` ordering key. An edge names its
    ``edge_type`` (a CT-07 lineage-edge type, e.g. ``enacts``, ``supersedes``,
    ``occurrence-of``), references its two endpoints by their ``fp1`` fingerprints
    (``from_ref`` the accruing/derived endpoint, ``to_ref`` the referenced one), and is
    written under a single :class:`~qmf.core.WriterId`. qmf-data emits this as a value the
    application routes to qmf-registry's lineage-edge stream (DEC-0120); it never rewrites
    a record in place.
    """

    edge_type: str
    from_ref: Fingerprint
    to_ref: Fingerprint
    writer: WriterId

    @classmethod
    def try_create(
        cls, *, edge_type: object, from_ref: object, to_ref: object, writer: object
    ) -> Result[CausalEdge]:
        """Validate and build a :class:`CausalEdge`, returning value-or-refusal.

        ``edge_type`` is a non-blank CT-07 edge-type token; ``from_ref`` and ``to_ref``
        are :class:`~qmf.core.Fingerprint`\\ s (or ``fp1:sha256:<hex>`` strings) — an edge
        references records by their fp1, never a mutable or minted id; ``writer`` is the
        single edge-stream :class:`~qmf.core.WriterId`.
        """
        parts = _resolve_causal_edge_parts(edge_type, from_ref, to_ref, writer)
        if is_refusal(parts):
            return parts
        kind, resolved_from, resolved_to, resolved_writer = parts.value
        return Ok(
            cls(
                edge_type=kind,
                from_ref=resolved_from,
                to_ref=resolved_to,
                writer=resolved_writer,
            )
        )

    @classmethod
    def link(cls, edge_type: object, from_event: object, to_event: object) -> Result[CausalEdge]:
        """Build the causal edge linking two :class:`JournalEvent`\\ s by their ``fp1``.

        The edge references ``from_event.fingerprint`` and ``to_event.fingerprint`` — the
        identity fp1s (which exclude ``correlation_id``), so a causal link never rides a
        correlation annotation, a timestamp, or the ordering key. The edge is written under
        ``from_event``'s writer. A non-event argument is an ``invalid input`` refusal.
        """
        if not isinstance(from_event, JournalEvent):
            return invalid_input(
                "from_event", "a causal link is from a JournalEvent", given=repr(from_event)
            )
        if not isinstance(to_event, JournalEvent):
            return invalid_input(
                "to_event", "a causal link is to a JournalEvent", given=repr(to_event)
            )
        return cls.try_create(
            edge_type=edge_type,
            from_ref=from_event.fingerprint,
            to_ref=to_event.fingerprint,
            writer=from_event.writer,
        )

    def to_row(self) -> dict[str, object]:
        """The CT-07-shaped typed edge record, JSON-native for a pinned-JSONL edge stream."""
        return {
            "edge_type": self.edge_type,
            "from_ref": self.from_ref.value,
            "to_ref": self.to_ref.value,
            "writer": writer_identity(self.writer),
            "contract_format_version": CONTRACT_FORMAT_VERSION,
        }


def _resolve_causal_edge_parts(
    edge_type: object, from_ref: object, to_ref: object, writer: object
) -> Result[tuple[str, Fingerprint, Fingerprint, WriterId]]:
    """Resolve a causal edge's parts, or the first ``invalid input`` refusal."""
    if not isinstance(edge_type, str) or edge_type.strip() == "":
        return invalid_input(
            "edge_type",
            "a causal edge names a non-blank CT-07 edge type (e.g. enacts, supersedes, "
            "occurrence-of)",
            given=repr(edge_type),
        )
    resolved_from = coerce_fingerprint(from_ref)
    if resolved_from is None:
        return invalid_input(
            "from_ref",
            "a causal edge references its endpoints by fp1:sha256:<hex>, never a "
            "timestamp or the ordering key (DEC-0114, DEC-0108)",
            given=repr(from_ref),
        )
    resolved_to = coerce_fingerprint(to_ref)
    if resolved_to is None:
        return invalid_input(
            "to_ref",
            "a causal edge references its endpoints by fp1:sha256:<hex>, never a "
            "timestamp or the ordering key (DEC-0114, DEC-0108)",
            given=repr(to_ref),
        )
    if not isinstance(writer, WriterId):
        return invalid_input(
            "writer",
            "a causal edge stream has exactly one holding WriterId (DEC-0113)",
            given=repr(writer),
        )
    return Ok((edge_type, resolved_from, resolved_to, writer))
