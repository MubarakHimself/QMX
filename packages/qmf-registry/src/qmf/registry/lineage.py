"""CT-07 — append-only typed lineage edges (COMP-QMF-REGISTRY).

Lineage that accrues **after** a record's birth lives exclusively in append-only typed
edge records; at-birth parent references stay in the CT-06 record header, and a reader
never unions the header references with the edge set (DEC-0114). An edge references
**both** endpoints by their ``fp1`` fingerprint — never a mutable or minted id — and
carries an ``edge_type`` drawn from the ratified V1 set. Edge types are addable in a
later version and never redefined.

Five laws this module pins down.

**Typed edges over fingerprints, from the ratified set (CT-07; DEC-0114).**
:class:`LineageEdge` is a frozen edge record: an :class:`EdgeType`, a ``from_ref`` and
``to_ref`` that are each a :class:`~qmf.core.Fingerprint`, the CT-07 contract format
version, and the stream's :class:`~qmf.core.WriterId`. An edge whose kind is outside
:class:`EdgeType`, or whose endpoint is anything other than an ``fp1`` fingerprint, is
not admitted — a typed refusal (FM-2), never a silent accept.

**The pinned JSONL line and the derived edge fingerprint (CT-07; DEC-0108).** Every
field of an edge is identity by default (CT-05): the canonical ``fp1`` identity content
is ``edge_type`` + ``from_ref`` + ``to_ref`` + the contract format version + the writer,
and :meth:`LineageEdge.canonical_line` serializes exactly that content to the pinned
JSONL line — one ``fp1``-canonical JSON object, LF-terminated, computed only through
qmf-core. The edge's ``edge_fingerprint`` **is** the fingerprint of that content; it is
derived, never minted. Physical persistence — append-with-fsync, size-rotation with a
monotonic file ordinal, and the CT-11 append-store — is Story 2.4; this module defines
the vocabulary, the validation, and the in-memory stream, and the line it hands a
:class:`~qmf.core.RecordSink` is exactly what that store writes.

**One writer, unlimited readers (CT-07; DEC-0113).** :class:`EdgeLog` is an in-memory
edge **stream** with exactly one :class:`~qmf.core.WriterId`; an edge presented for
append whose writer is not the stream's writer is refused (a policy rejection). It is a
pure, in-memory content-addressed reference guard — **not** the platform's storage (the
same kind of pure reference as qmf-core's
:class:`~qmf.core.GovernedEvidenceLedger` and this package's
:class:`~qmf.registry.Registrar`).

**``supersedes`` is pinned linear; ``branches-from`` is not (CT-07; DEC-0158,
DEC-0144).** For ``supersedes`` the log admits **at most one outgoing edge per subject**
and **at most one incoming edge per superseded record**, and it refuses any edge that
would close a cycle — so the chain is a set of disjoint linear chains and
:meth:`EdgeLog.current_head` resolves one unambiguous "current" from any version. A
branching Book/BMS version graph instead uses ``branches-from``, where several heads are
legal; "current" is a separate dated pointer record, never inferred from the graph, so
the log places no linearity constraint on ``branches-from``.

**Append-only; a correction is a new edge (CT-07; DEC-0119, DEC-0108).** Edges are
immutable and append-only — a correction is a new edge and a superseding relationship is
a ``supersedes`` edge, never an in-place edit — and ``corroborates`` / ``disagrees-with``
edges keep source disagreements visible and are never merged away. A byte-identical
re-append is accepted silently (idempotent); a true collision — the same edge
fingerprint presented with differing bytes — is refused and alarmed, never overwritten
(FM-6-family). Indexes over the edge set are local and **rebuildable**: losing an index
costs a rebuild (:meth:`EdgeLog.rebuild_indexes`), never the evidence.

Default-deny holds: this module imports **only** ``qmf.core`` (every ``fp1`` fingerprint
is computed there, nowhere else), no roster library imports ``qmf-registry``, and the
application wires the edge stream at the composition root (DEC-0120). Every operation
succeeds or RETURNS a CT-04 :class:`~qmf.core.TypedRefusal`; domain failure is never
raised across the boundary. Stdlib plus qmf-core only; frozen, immutable values
throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

from qmf.core import (
    Fingerprint,
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    WriteOutcome,
    WriterId,
    canonical_bytes,
    fingerprint,
    is_ok,
    is_refusal,
    reconcile_write,
)

__all__ = [
    "EDGE_CONTRACT_FORMAT_VERSION",
    "EdgeAppendReceipt",
    "EdgeLog",
    "EdgeType",
    "LineageEdge",
    "WriteOutcome",
]

# The CT-07 edge contract's format version — stamped into every edge's identity (and so
# onto every serialized JSONL line) so history stays readable and an incompatible edge
# change mints the next version plus a migration note (DEC-0103; versioning-from-birth
# L15). Unlike a CT-06 record — whose ``contract_format_version`` header field is the
# *per-kind* contract's version — there is one edge contract, so this single version is
# both the envelope version and the value the caller stamps.
EDGE_CONTRACT_FORMAT_VERSION: Final[int] = 1


class EdgeType(StrEnum):
    """The ratified V1 lineage edge types (CT-07 ``enums.edge_type``; DEC-0114,
    DEC-0131, DEC-0137, DEC-0158).

    A closed set in V1 — **addable in a later contract version, never redefined**. The
    values are the canonical hyphenated strings CT-07 pins, so an :class:`EdgeType`
    round-trips through its string form on a JSONL line.

    * ``supersedes`` — a newer record replaces an older one; pinned **linear** so
      "current" is never ambiguous (:class:`EdgeLog` enforces it).
    * ``promoted-from`` — a promoted record derives from its source record.
    * ``occurrence-of`` — an occurrence links to the computation identity it realizes.
    * ``corroborates`` / ``disagrees-with`` — source observations that agree or
      disagree; kept visible and never merged away (DEC-0119).
    * ``confirmed-as`` / ``confirmation`` / ``invalidation`` / ``interaction`` — the
      AD-25 structure-object lifecycle that accrues after observation (DEC-0131).
    * ``out-of-sequence`` — an AD-27 venue observation with no legal state transition,
      forcing its command to UNKNOWN pending resolution (DEC-0137).
    * ``continues-performance`` / ``carries-ledger`` — the AD-18 human-signed
      risk-gate edges that never imply each other (DEC-0158).
    * ``enacts`` — a command or outcome enacts a CT-30 control action or CT-23 intent
      (DEC-0158).
    * ``branches-from`` — the AD-30 branching Book/BMS version graph, where several
      heads are legal and "current" is a separate dated pointer record (DEC-0144).
    """

    SUPERSEDES = "supersedes"
    PROMOTED_FROM = "promoted-from"
    OCCURRENCE_OF = "occurrence-of"
    CORROBORATES = "corroborates"
    DISAGREES_WITH = "disagrees-with"
    CONFIRMED_AS = "confirmed-as"
    CONFIRMATION = "confirmation"
    INVALIDATION = "invalidation"
    INTERACTION = "interaction"
    OUT_OF_SEQUENCE = "out-of-sequence"
    CONTINUES_PERFORMANCE = "continues-performance"
    CARRIES_LEDGER = "carries-ledger"
    ENACTS = "enacts"
    BRANCHES_FROM = "branches-from"


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal an edge-construction operation returns (FM-2).

    ``retryability`` is ``no`` — an edge kind outside the ratified set, an endpoint that
    is not an ``fp1`` fingerprint, a bad format version, or a bad writer is a
    caller/wiring mistake, not a transient condition — and ``context`` always names the
    offending ``field`` and a human-legible ``reason`` (returned, never raised; CT-04;
    DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal the stream-writer, linearity, and
    collision guards return (CT-07; DEC-0158, DEC-0108).

    A second writer on a single-writer stream, a second ``supersedes`` edge for a
    subject (or a fork/cycle in the chain), and a true edge-fingerprint collision are
    all policy rejections — the pure registry surface never returns ``storage failure``
    (that category arises only at the qmf-data boundary, FM-8, Story 2.4).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _coerce_edge_type(value: object) -> EdgeType | None:
    """Resolve ``value`` to a ratified :class:`EdgeType`, or ``None``.

    Accepts an :class:`EdgeType` member or its canonical hyphenated string. A kind
    outside the ratified V1 set resolves to ``None`` — the caller turns that into the
    FM-2 refusal — because edge types are addable in a later version, never invented at
    a call site.
    """
    if isinstance(value, EdgeType):
        return value
    if isinstance(value, str):
        try:
            return EdgeType(value)
        except ValueError:
            return None
    return None


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`Fingerprint` or a valid ``fp1:sha256:<hex>`` string, or
    ``None`` — parsing goes through qmf-core, never a local hash."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _positive_int(value: object) -> int | None:
    """Return ``value`` as a genuine positive ``int`` (a ``bool`` is rejected), or
    ``None`` — a contract format version is a positive integer ordinal (DEC-0103)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _writer_identity_content(writer: WriterId) -> dict[str, object]:
    """The writer's canonical identity content — its four opaque string parts.

    A :class:`~qmf.core.WriterId` is an occurrence noun with no ``fp1_identity`` seam,
    so it is serialized here as its ``(machine, role, stream, boot_epoch_id)`` — every
    part a non-empty string guaranteed by :meth:`WriterId.try_create`, so the mapping is
    always ``fp1``-clean. The boot/epoch id is included: a restart is a distinct writer,
    and the single-writer stream (:class:`EdgeLog`) holds one writer for its lifetime, so
    within a stream a byte-identical re-append stays idempotent.
    """
    return {
        "machine": writer.machine,
        "role": writer.role,
        "stream": writer.stream,
        "boot_epoch_id": writer.boot_epoch_id,
    }


def _edge_identity_content(
    edge_type: EdgeType,
    from_ref: Fingerprint,
    to_ref: Fingerprint,
    contract_format_version: int,
    writer: WriterId,
) -> dict[str, object]:
    """The edge's canonical ``fp1`` identity content — the parts that ARE its identity.

    Built identically by :meth:`LineageEdge.try_create` (to derive the edge fingerprint)
    and :meth:`LineageEdge.fp1_identity`. Every CT-07 edge field is identity by default
    (CT-05 makes an exclusion an explicit design choice, and CT-07 declares none): the
    edge type, both endpoint fingerprints, the contract format version, and the writer,
    under a ``class`` tag that keeps an edge's fingerprint disjoint from any other
    fingerprinted artifact.
    """
    return {
        "class": "lineage-edge",
        "edge_type": edge_type.value,
        "from_ref": from_ref.value,
        "to_ref": to_ref.value,
        "contract_format_version": contract_format_version,
        "writer": _writer_identity_content(writer),
    }


# --- the typed edge record --------------------------------------------------


@dataclass(frozen=True, slots=True)
class LineageEdge:
    """An append-only typed lineage edge whose id is its ``fp1`` fingerprint (CT-07;
    DEC-0114, DEC-0108).

    ``edge_type`` is a ratified :class:`EdgeType`; ``from_ref`` is the accruing/derived
    endpoint (the newer record for ``supersedes``, the promoted record for
    ``promoted-from``, the occurrence for ``occurrence-of``) and ``to_ref`` the
    referenced endpoint (the superseded record, the source record, the computation
    identity) — both :class:`~qmf.core.Fingerprint`\\ s, never a mutable or minted id.
    ``contract_format_version`` is the CT-07 format version stamped on every line and
    ``writer`` the stream's :class:`~qmf.core.WriterId`. ``edge_fingerprint`` is
    **derived** from the identity content and is never supplied by the caller.

    The edge is frozen: a correction is a new edge and a superseding relationship is a
    ``supersedes`` edge, never an in-place edit.
    """

    edge_type: EdgeType
    from_ref: Fingerprint
    to_ref: Fingerprint
    contract_format_version: int
    writer: WriterId
    edge_fingerprint: Fingerprint

    @classmethod
    def try_create(
        cls,
        edge_type: object,
        from_ref: object,
        to_ref: object,
        writer: object,
        contract_format_version: object = EDGE_CONTRACT_FORMAT_VERSION,
    ) -> Result[LineageEdge]:
        """Validate the edge, derive its fingerprint, and build a :class:`LineageEdge`,
        returning value-or-refusal (FM-2).

        ``edge_type`` must be a ratified :class:`EdgeType` (or its string); ``from_ref``
        and ``to_ref`` each a :class:`~qmf.core.Fingerprint` or a valid
        ``fp1:sha256:<hex>`` string — a minted or mutable id is refused; ``writer`` a
        :class:`~qmf.core.WriterId`; and ``contract_format_version`` a positive integer
        (defaulting to the CT-07 version). The edge fingerprint is **not** accepted from
        the caller — it is fingerprinted from the identity content, so an edge can never
        claim an id its content does not derive (DEC-0114, DEC-0108).
        """
        resolved_type = _coerce_edge_type(edge_type)
        if resolved_type is None:
            return _invalid(
                "edge_type",
                "the edge type is outside the ratified CT-07 set; edge types are "
                "addable in a later version, never invented at a call site (FM-2)",
                given=repr(edge_type),
                allowed=[member.value for member in EdgeType],
            )
        resolved_from = _coerce_fingerprint(from_ref)
        if resolved_from is None:
            return _invalid(
                "from_ref",
                "an edge references its endpoint by an fp1 fingerprint "
                "(fp1:sha256:<hex>); a minted or mutable id is never an endpoint (FM-2)",
                given=repr(from_ref),
            )
        resolved_to = _coerce_fingerprint(to_ref)
        if resolved_to is None:
            return _invalid(
                "to_ref",
                "an edge references its endpoint by an fp1 fingerprint "
                "(fp1:sha256:<hex>); a minted or mutable id is never an endpoint (FM-2)",
                given=repr(to_ref),
            )
        if not isinstance(writer, WriterId):
            return _invalid(
                "writer",
                "an edge stream stamps its single WriterId onto every edge",
                given=repr(writer),
            )
        version = _positive_int(contract_format_version)
        if version is None:
            return _invalid(
                "contract_format_version",
                "the edge contract format version is a positive integer ordinal; "
                "package SemVer never enters identity (DEC-0103)",
                given=repr(contract_format_version),
            )
        content = _edge_identity_content(resolved_type, resolved_from, resolved_to, version, writer)
        derived = fingerprint(content)
        if is_refusal(derived):  # pragma: no cover - identity is canonical by construction
            return derived
        return Ok(
            cls(
                edge_type=resolved_type,
                from_ref=resolved_from,
                to_ref=resolved_to,
                contract_format_version=version,
                writer=writer,
                edge_fingerprint=derived.value,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the parts that ARE the edge's
        identity. Its fingerprint equals :attr:`edge_fingerprint`."""
        return _edge_identity_content(
            self.edge_type,
            self.from_ref,
            self.to_ref,
            self.contract_format_version,
            self.writer,
        )

    def canonical_line(self) -> Result[bytes]:
        """The pinned JSONL line for this edge (CT-07; DEC-0108, DEC-0114).

        One ``fp1``-canonical JSON object — keys sorted at every depth, compact, UTF-8,
        NFC-normalized, computed only through qmf-core's single serializer — terminated
        with a single ``\\n`` (LF). This is exactly the byte sequence Story 2.4's CT-11
        append-store appends (with fsync, size-rotation, and a monotonic file ordinal);
        this module produces the line, not the file. Returns value-or-refusal, though
        the identity content is canonical by construction.
        """
        serialized = canonical_bytes(self.fp1_identity())
        if is_refusal(serialized):  # pragma: no cover - identity is canonical by construction
            return serialized
        return Ok(serialized.value + b"\n")


# --- the in-memory single-writer edge stream --------------------------------


@dataclass(frozen=True, slots=True)
class EdgeAppendReceipt:
    """The receipt of an admitted edge append (CT-07; DEC-0108).

    ``outcome`` is ``stored`` for a first append of this edge fingerprint or
    ``idempotent`` for a byte-identical re-append; a true collision, a linearity
    violation, and a wrong-writer append are not outcomes — they are refused.
    ``edge`` is the admitted :class:`LineageEdge` (for an idempotent re-append it is the
    edge already on the stream).
    """

    outcome: WriteOutcome
    edge: LineageEdge


class EdgeLog:
    """A pure, in-memory single-writer lineage edge stream (CT-07; DEC-0113, DEC-0114,
    DEC-0108).

    Holds exactly one :class:`~qmf.core.WriterId` and unlimited readers. It composes the
    edge validation, the ``fp1`` derivation, and qmf-core's
    :func:`~qmf.core.reconcile_write`: an append is content-addressed by the edge
    fingerprint (a first append is ``stored``, a byte-identical re-append is
    ``idempotent``, a true collision is refused and alarmed), ``supersedes`` is held
    linear, and a cross-writer append is refused. It is a reference guard for tests and
    the reference-usage examples — dicts and lists with no I/O — **not** the platform's
    storage; durable persistence through qmf-data's CT-11 append-store is Story 2.4 (the
    same way :class:`~qmf.registry.Registrar` is a pure reference guard, not the store).

    Evidence and index are kept distinct: :attr:`_admitted` is the append-ordered edge
    evidence, while the lookup structures are **derived** and can be dropped and
    reconstructed with :meth:`rebuild_indexes` — losing an index costs a rebuild, never
    the evidence.
    """

    def __init__(self, writer: WriterId) -> None:
        self._writer: WriterId = writer
        # Content-addressed guard: edge-fingerprint digest -> canonical identity bytes.
        self._bytes: dict[str, bytes] = {}
        # The append-ordered edge evidence — the source of truth every index derives from.
        self._admitted: list[LineageEdge] = []
        # Derived indexes (rebuildable from ``_admitted``).
        self._supersedes_out: dict[str, str] = {}
        self._supersedes_in: dict[str, str] = {}

    @property
    def writer(self) -> WriterId:
        """The single :class:`~qmf.core.WriterId` this stream stamps onto every edge."""
        return self._writer

    def append(
        self,
        *,
        edge_type: object,
        from_ref: object,
        to_ref: object,
        contract_format_version: object = EDGE_CONTRACT_FORMAT_VERSION,
    ) -> Result[EdgeAppendReceipt]:
        """Build an edge under this stream's writer and append it, returning
        value-or-refusal.

        The convenience path: it stamps the stream's :class:`~qmf.core.WriterId` and the
        CT-07 format version, builds the :class:`LineageEdge` (FM-2 for a bad edge type
        or a non-``fp1`` endpoint), and admits it through :meth:`append_edge`.
        """
        built = LineageEdge.try_create(
            edge_type,
            from_ref,
            to_ref,
            self._writer,
            contract_format_version,
        )
        if is_refusal(built):
            return built
        return self.append_edge(built.value)

    def append_edge(self, edge: object) -> Result[EdgeAppendReceipt]:
        """Admit a pre-built :class:`LineageEdge` onto the stream, returning
        value-or-refusal.

        Enforces the single-writer law first — an edge whose writer is not this stream's
        writer is a policy rejection — then reconciles the append (idempotent re-append
        vs true collision) and, for a genuinely new ``supersedes`` edge, the linearity
        law. Nothing is committed on any refusal.
        """
        if not isinstance(edge, LineageEdge):
            return _invalid("edge", "an append presents a LineageEdge", given=repr(edge))
        if edge.writer != self._writer:
            return _policy(
                "writer",
                "an edge stream has exactly one writer; an edge stamped by another "
                "writer is refused (open a stream per writer)",
                stream_writer=self._writer.order_tuple(),
                edge_writer=edge.writer.order_tuple(),
            )
        serialized = canonical_bytes(edge.fp1_identity())
        if is_refusal(serialized):  # pragma: no cover - identity is canonical by construction
            return serialized
        digest = edge.edge_fingerprint.digest
        decision = reconcile_write(edge.edge_fingerprint, serialized.value, self._bytes.get(digest))
        if is_refusal(decision):
            return decision
        if decision.value is WriteOutcome.IDEMPOTENT:
            # A byte-identical re-append: the edge is already on the stream, so return
            # the admitted one and do NOT re-run the linearity law (it already passed).
            return Ok(EdgeAppendReceipt(outcome=decision.value, edge=self._admitted_edge(digest)))
        if edge.edge_type is EdgeType.SUPERSEDES:
            violation = self._supersedes_violation(edge)
            if violation is not None:
                return violation
        self._bytes[digest] = serialized.value
        self._admitted.append(edge)
        self._index(edge)
        return Ok(EdgeAppendReceipt(outcome=decision.value, edge=edge))

    def _admitted_edge(self, digest: str) -> LineageEdge:
        """The admitted edge under ``digest`` (present on the idempotent path)."""
        for edge in self._admitted:
            if edge.edge_fingerprint.digest == digest:
                return edge
        raise AssertionError(  # pragma: no cover - an idempotent hit is always admitted
            "idempotent re-append with no admitted edge under its digest"
        )

    def _supersedes_violation(self, edge: LineageEdge) -> TypedRefusal | None:
        """The linearity refusal a new ``supersedes`` edge earns, or ``None`` (DEC-0158,
        DEC-0144).

        ``supersedes`` is pinned linear: at most one outgoing edge per subject (a record
        supersedes at most one record) and at most one incoming edge per superseded
        record (a record is superseded by at most one record, so "current" never forks),
        and no edge may close a cycle. A branching version graph uses ``branches-from``
        instead, which carries no such constraint.
        """
        subject = edge.from_ref.value
        superseded = edge.to_ref.value
        if subject == superseded:
            return _policy(
                "supersedes",
                "a supersedes edge cannot point a record at itself",
                subject=subject,
            )
        existing_out = self._supersedes_out.get(subject)
        if existing_out is not None:
            return _policy(
                "supersedes",
                "supersedes is pinned linear: a subject already has an outgoing "
                "supersedes edge, so a second would make 'current' ambiguous — record a "
                "branches-from edge for a branching version graph instead (DEC-0158)",
                subject=subject,
                existing_to=existing_out,
                attempted_to=superseded,
            )
        existing_in = self._supersedes_in.get(superseded)
        if existing_in is not None:
            return _policy(
                "supersedes",
                "supersedes is pinned linear: this record is already superseded by "
                "another, so a second superseder would fork 'current' — record a "
                "branches-from edge for a branching version graph instead (DEC-0158)",
                superseded=superseded,
                existing_from=existing_in,
                attempted_from=subject,
            )
        if self._would_cycle(subject, superseded):
            return _policy(
                "supersedes",
                "a supersedes edge would close a cycle in the version chain, leaving no "
                "resolvable head",
                subject=subject,
                superseded=superseded,
            )
        return None

    def _would_cycle(self, subject: str, superseded: str) -> bool:
        """Whether adding ``subject`` supersedes ``superseded`` would close a cycle.

        Walks the existing chain forward from ``superseded`` along outgoing supersedes
        edges; reaching ``subject`` means the new edge would loop the chain. A visited
        set bounds the walk defensively, though the two single-edge constraints already
        keep every existing chain acyclic.
        """
        seen: set[str] = set()
        cursor: str | None = superseded
        while cursor is not None and cursor not in seen:
            if cursor == subject:
                return True
            seen.add(cursor)
            cursor = self._supersedes_out.get(cursor)
        return False

    def _index(self, edge: LineageEdge) -> None:
        """Fold one admitted edge into the derived supersedes indexes."""
        if edge.edge_type is EdgeType.SUPERSEDES:
            self._supersedes_out[edge.from_ref.value] = edge.to_ref.value
            self._supersedes_in[edge.to_ref.value] = edge.from_ref.value

    def rebuild_indexes(self) -> None:
        """Discard and reconstruct every derived index from the edge evidence (CT-07;
        DEC-0114).

        Indexes over edges are local and rebuildable: losing one costs a rebuild, never
        evidence. This clears the derived lookup structures and replays the
        append-ordered :attr:`_admitted` edges through :meth:`_index`, so the indexes
        after a rebuild are identical to the incrementally-maintained ones.
        """
        self._supersedes_out = {}
        self._supersedes_in = {}
        for edge in self._admitted:
            self._index(edge)

    # --- readers (unlimited) ------------------------------------------------

    def edges(self) -> tuple[LineageEdge, ...]:
        """Every admitted edge, in append order — the raw lineage evidence."""
        return tuple(self._admitted)

    def edges_from(self, ref: object) -> tuple[LineageEdge, ...]:
        """Every admitted edge whose ``from_ref`` is ``ref`` (append order)."""
        resolved = _coerce_fingerprint(ref)
        if resolved is None:
            return ()
        return tuple(edge for edge in self._admitted if edge.from_ref == resolved)

    def edges_to(self, ref: object) -> tuple[LineageEdge, ...]:
        """Every admitted edge whose ``to_ref`` is ``ref`` (append order)."""
        resolved = _coerce_fingerprint(ref)
        if resolved is None:
            return ()
        return tuple(edge for edge in self._admitted if edge.to_ref == resolved)

    def edges_of_type(self, edge_type: object) -> tuple[LineageEdge, ...]:
        """Every admitted edge of a given :class:`EdgeType` (append order)."""
        resolved = _coerce_edge_type(edge_type)
        if resolved is None:
            return ()
        return tuple(edge for edge in self._admitted if edge.edge_type is resolved)

    def current_head(self, record: object) -> Result[Fingerprint]:
        """Resolve the one unambiguous "current" of ``record``'s supersedes chain (CT-07;
        DEC-0158).

        Because ``supersedes`` is pinned linear, following the incoming supersedes edges
        forward from ``record`` (each superseded record has at most one superseder)
        reaches exactly one head — the newest, not-yet-superseded record. A record that
        nothing supersedes is its own head. Returns value-or-refusal: a malformed
        ``record`` reference is an ``invalid input`` refusal. ``branches-from`` is
        deliberately not resolved here — a branching graph's "current" is a separate
        dated pointer record, never inferred from the graph.
        """
        resolved = _coerce_fingerprint(record)
        if resolved is None:
            return _invalid(
                "record",
                "a head is resolved for a record named by an fp1 fingerprint",
                given=repr(record),
            )
        seen: set[str] = set()
        cursor = resolved.value
        while cursor in self._supersedes_in and cursor not in seen:
            seen.add(cursor)
            cursor = self._supersedes_in[cursor]
        if cursor == resolved.value:
            return Ok(resolved)
        # ``cursor`` came from an admitted edge endpoint, so it is a valid fingerprint;
        # re-parse through qmf-core rather than construct one locally.
        head = _coerce_fingerprint(cursor)
        if head is None:  # pragma: no cover - chain endpoints are always valid fingerprints
            return _invalid("record", "the resolved head is not a valid fingerprint", given=cursor)
        return Ok(head)

    def edge_count(self) -> int:
        """The number of admitted edges on this stream."""
        return len(self._admitted)
