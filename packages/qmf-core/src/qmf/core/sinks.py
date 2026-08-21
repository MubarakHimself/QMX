"""The injected persistence seams: ObservationSink, JournalSink, RecordSink
(COMP-QMF-CORE).

``qmf-core`` performs no I/O and spawns no work (AD-15; DEC-0113). An outer package
that must persist something does it **only** through a core-defined
:class:`typing.Protocol` seam injected at the composition root — it never imports a
store, registry, or venue package, so injecting a sink creates no dependency edge
(DEC-0138). Three streams, three distinct seams:

* :class:`ObservationSink` — records a raw inbound observation **verbatim, before
  any state evaluation** (recording precedes interpretation; AR-47).
* :class:`JournalSink` — appends a journal event to a gapless, append-only
  per-``(writer, boot-epoch)`` sequence (CT-13; DEC-0119).
* :class:`RecordSink` — writes a registry record (the root-mints pattern holds the
  ``WriterId`` and sees every refusal; DEC-0138, DEC-0171).

Each is generic over the payload it persists — the payload's concrete shape lives
in the package that produces it, and the composition root supplies the type when it
wires the real sink, so ``qmf-core`` names no foreign type. Each returns
``Result[SinkAck] = Ok[SinkAck] | TypedRefusal``: a successful, durable write
returns an :class:`Ok` acknowledgment, and an **unpersistable** write returns a
CT-04 ``storage failure`` typed refusal carrying category, context, and
retryability (AR-47).

**Block-on-unpersistable.** The writer that holds the ``WriterId`` sees every sink
refusal. A ``storage failure`` means the write did not land, so the writer must
**block its command stream** until the store recovers — never drop the intent, and
never assume success. :func:`unpersistable` builds the canonical refusal a sink
returns, and :func:`is_unpersistable` is the predicate a caller branches on to
implement that block; neither performs any I/O.

Stdlib only (DEC-0104). Frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Protocol, TypeAlias, TypeVar, runtime_checkable

from qmf.core.refusal import RefusalCategory, Result, Retryability, TypedRefusal

__all__ = [
    "JournalSink",
    "ObservationSink",
    "RecordSink",
    "SinkAck",
    "SinkResult",
    "is_unpersistable",
    "unpersistable",
]

# Contravariant: a sink that accepts a wider payload type is usable wherever a sink
# for a narrower one is expected. The type appears only in the input position.
_PayloadT_contra = TypeVar("_PayloadT_contra", contravariant=True)

# One shared immutable empty detail mapping; an acknowledgment always carries a
# present mapping, never null (the same idiom as a refusal's context).
_EMPTY_DETAIL: Final[Mapping[str, object]] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class SinkAck:
    """The acknowledgment of a successful, durable sink write (CT-13; AR-47).

    Returned wrapped in :class:`~qmf.core.refusal.Ok` as the success arm of a
    sink's ``Result[SinkAck]``: the write landed and the caller may proceed.
    ``detail`` carries optional sink-specific confirmation (a stored offset, a
    sequence position); it is present and read-only, never null.
    """

    detail: Mapping[str, object] = field(default=_EMPTY_DETAIL)

    def __post_init__(self) -> None:
        # Snapshot detail into a read-only mapping so a later mutation of the
        # caller's dict can never reach back into this frozen acknowledgment.
        object.__setattr__(self, "detail", MappingProxyType(dict(self.detail)))


SinkResult: TypeAlias = Result[SinkAck]
"""A sink's return: the success acknowledgment ``Ok[SinkAck]`` or a typed refusal."""


@runtime_checkable
class ObservationSink(Protocol[_PayloadT_contra]):
    """Records a raw observation verbatim before any interpretation (AR-47).

    A definitions-only seam injected at the composition root; the caller stamps
    writer and sequence before emitting, and this port only persists. A
    ``storage failure`` refusal means the observation did not land — the writer
    blocks its command stream rather than evaluating state on an unrecorded event.
    """

    def emit(
        self, observation: _PayloadT_contra, /
    ) -> SinkResult:  # pragma: no cover - protocol seam
        """Persist ``observation`` verbatim (value-or-refusal)."""
        ...


@runtime_checkable
class JournalSink(Protocol[_PayloadT_contra]):
    """Appends a journal event to a gapless append-only sequence (CT-13; DEC-0119).

    Events land in per-``(writer, boot-epoch)`` order with no gaps; an unavailable
    journal surfaces as a ``storage failure`` typed refusal, never a silent drop, so
    a control action is journaled before it is dispatched and a failed append blocks
    the stream rather than losing the intent.
    """

    def append(self, event: _PayloadT_contra, /) -> SinkResult:  # pragma: no cover - protocol seam
        """Append ``event`` to the journal (value-or-refusal)."""
        ...


@runtime_checkable
class RecordSink(Protocol[_PayloadT_contra]):
    """Writes a registry record (the root-mints pattern; DEC-0138, DEC-0171).

    The composition root holds the ``WriterId`` and the gapless per-``(writer,
    kind)`` sequence, mints the record, and sees every refusal from this port; a
    ``storage failure`` blocks the write path (block-on-unpersistable).
    """

    def write(self, record: _PayloadT_contra, /) -> SinkResult:  # pragma: no cover - protocol seam
        """Write ``record`` to the store (value-or-refusal)."""
        ...


def unpersistable(
    reason: str,
    *,
    retryability: Retryability = Retryability.NO,
    context: Mapping[str, object] | None = None,
    after_condition_descriptor: str | None = None,
) -> TypedRefusal:
    """Build the canonical ``storage failure`` refusal a sink returns (CT-04; AR-47).

    A sink that cannot durably persist a write returns this: a CT-04 typed refusal
    (returned, never raised) with category ``storage failure``, the ``reason`` and
    any extra ``context`` merged into machine-readable context, and a
    ``retryability`` answer. Use ``retryability = Retryability.AFTER_CONDITION`` with
    an ``after_condition_descriptor`` for a rotation-store failure whose retry gate is
    "successful store or operator re-provision" (AR-38). The caller recognizes it
    with :func:`is_unpersistable` and blocks its command stream.
    """
    merged: dict[str, object] = {"reason": reason}
    if context is not None:
        merged.update(context)
    return TypedRefusal(
        category=RefusalCategory.STORAGE_FAILURE,
        retryability=retryability,
        context=merged,
        after_condition_descriptor=after_condition_descriptor,
    )


def is_unpersistable(result: object) -> bool:
    """True when ``result`` is a ``storage failure`` typed refusal (AR-47).

    The predicate a writer branches on to implement block-on-unpersistable: given a
    sink's ``Result[SinkAck]`` (or any value), it is ``True`` only for a
    :class:`~qmf.core.refusal.TypedRefusal` whose category is ``storage failure`` — a
    successful ``Ok`` acknowledgment and every other refusal category are ``False``.
    """
    return isinstance(result, TypedRefusal) and result.category is RefusalCategory.STORAGE_FAILURE
