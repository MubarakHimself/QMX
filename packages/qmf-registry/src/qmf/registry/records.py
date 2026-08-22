"""CT-06 — per-kind, fingerprint-keyed registration records (COMP-QMF-REGISTRY).

Registration writes a **per-kind versioned record** — each kind its own contract —
and there is never one universal all-fields recipe card (DEC-0114). Every record
carries a tiny common header — ``kind``, the per-kind contract's format version,
at-birth parent references (identity-bearing), the ``WriterId``, and a per-writer
sequence — plus a kind-specific ``body``. A record's stable id is **derived from its
``fp1`` fingerprint and never minted**; created-at and every other occurrence fact
(the writer and the sequence included) are display-only and excluded from ``fp1``
identity, so identical work from two sandboxes deduplicates by computation identity
(DEC-0114, DEC-0108, DEC-0110).

Four laws this module pins down.

**Per-kind records, one tiny common header (DEC-0114).** :class:`RegistrationRecord`
holds the shared header plus an opaque kind-specific body. There is no universal
all-fields card: a kind's field set is owned by its own :class:`KindContract`, and a
:class:`KindRegistry` holds the addable-never-redefined roster of known kinds. A
registration naming a kind — or a body field — a kind's contract does not define is a
typed refusal (FM-1), never a silent accept.

**The stable id is derived, never minted (DEC-0114, DEC-0108).** The identity content
is exactly ``kind`` + the per-kind contract format version + the (canonically ordered)
at-birth parent references + the body; its ``fp1`` fingerprint **is** the stable id.
The ``WriterId``, the per-writer sequence, and ``created_at`` are stored on the record
as display-only occurrence facts and are **excluded** from identity — the same
occurrence/identity split :class:`~qmf.core.OccurrenceRecord` draws in qmf-core — so
two sandboxes doing identical work, with different writers and different clocks, land
on one stable id and deduplicate.

**Idempotent re-write vs true collision (FM-6).** :class:`Registrar` is a pure,
in-memory content-addressed reference guard — **not** the platform's storage (durable
persistence through qmf-data's store-seam is Story 2.4, and this guard is the same
kind of pure reference as qmf-core's :class:`~qmf.core.GovernedEvidenceLedger`). It
composes the kind check, the ``fp1`` derivation, and qmf-core's
:func:`~qmf.core.reconcile_write`: a first write is ``stored``, a byte-identical
re-write is ``idempotent`` (accepted silently), and a true collision — the same
``fp1`` stable id presented with differing bytes — is refused and alarmed, never
overwritten (DEC-0108).

**At-birth references stay in the header; later lineage is CT-07 edges only
(DEC-0114).** ``at_birth_parent_refs`` are identity-bearing and live in the header;
lineage that accrues after a record's birth is written **only** as CT-07 typed edges
(Story 2.2) and never back into the frozen record. A reader takes the header's
at-birth references and the CT-07 edge set as two separate things and never unions
them.

Default-deny holds: this module imports **only** ``qmf.core`` (every ``fp1``
fingerprint is computed there, nowhere else), no roster library imports
``qmf-registry``, and registration is invoked by the application at the composition
root (DEC-0120). Every operation succeeds or RETURNS a CT-04 :class:`TypedRefusal`;
domain failure is never raised across the boundary. Stdlib plus qmf-core only; frozen,
immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core import (
    Fingerprint,
    Instant,
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
    "CONTRACT_FORMAT_VERSION",
    "RESERVED_KIND_NAMES",
    "FieldSetKind",
    "KindContract",
    "KindRegistry",
    "Registrar",
    "RegistrationReceipt",
    "RegistrationRecord",
    "WriteOutcome",
]

# The CT-06 record-envelope contract format version — the version of the common
# header/identity SHAPE this module serializes, stamped into every record's identity
# so history stays readable and an incompatible envelope change mints the next version
# (DEC-0103; versioning-from-birth L15). It is distinct from a record's
# ``contract_format_version`` header field, which is the *per-kind* contract's version.
CONTRACT_FORMAT_VERSION: Final[int] = 1

# The reserved kind names CT-06 honors (DEC-0116, DEC-0158). They are set aside from
# birth: the generic addable path may neither register a contract under them nor mint a
# record of them. ``promotion-occurrence-card`` — the only path to live money — gets
# its human-signed body through its own dedicated contract (Story 2.3), and
# ``treasury-boundary-event`` is node territory; reserving the names here stops the
# generic path from ever forging either kind.
RESERVED_KIND_NAMES: Final[frozenset[str]] = frozenset(
    {"promotion-occurrence-card", "treasury-boundary-event"}
)

# Provenance sentinel for a reserved-kind record minted through its own dedicated,
# package-internal path (:meth:`RegistrationRecord._mint_reserved`, used only by the
# human-signed promotion card, Story 2.3). The public :meth:`RegistrationRecord.try_create`
# and the generic KindRegistry/Registrar path refuse reserved kinds outright, so a reserved
# CT-06 kind can be built ONLY through that dedicated path — and only such a record carries
# this sentinel. A forged look-alike (even one byte-identical to a genuine card) never does,
# so a persist boundary accepts the real card while refusing the forgery (H2; DEC-0116,
# DEC-0158; FM-4; ADR-0015). Object identity, never a value, so it cannot be spoofed by a
# body field.
_RESERVED_MINT_PROVENANCE: Final = object()


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a registration operation returns.

    ``retryability`` is ``no`` — a malformed header part, an unknown kind, a body
    field a kind's contract does not define, or a kind-redefinition attempt is a
    caller/wiring mistake, not a transient condition — and ``context`` always names
    the offending ``field`` and a human-legible ``reason`` (returned, never raised;
    CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    A kind name is an opaque controlled token: the returned string is the caller's
    verbatim — never stripped, cased, or parsed.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _positive_int(value: object) -> int | None:
    """Return ``value`` as a genuine positive ``int`` (a ``bool`` is rejected), or
    ``None``.

    A contract format version is a positive integer ordinal; package SemVer never
    enters here (DEC-0103).
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _deep_freeze(value: object) -> object:
    """Recursively snapshot ``value`` into a shared-safe, read-only form.

    A ``Mapping`` becomes a :class:`~types.MappingProxyType` over deep-frozen values
    and a list/tuple becomes a tuple — so a nested container reached through the
    caller's dict can never be mutated through the reference the frozen record keeps.
    A registration record is append-only evidence; it must never rewrite.
    """
    if isinstance(value, Mapping):
        mapping = cast("Mapping[object, object]", value)
        return MappingProxyType({key: _deep_freeze(item) for key, item in mapping.items()})
    if isinstance(value, (list, tuple)):
        sequence = cast("Sequence[object]", value)
        return tuple(_deep_freeze(item) for item in sequence)
    return value


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`Fingerprint` or a valid ``fp1:sha256:<hex>`` string, or
    ``None`` — parsing goes through qmf-core, never a local hash."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _coerce_parent_refs(value: object) -> tuple[Fingerprint, ...] | TypedRefusal:
    """Resolve the at-birth parent references to a canonical fingerprint tuple.

    Accepts an (order-insignificant) sequence of :class:`Fingerprint`\\ s or valid
    fingerprint strings — a bare string or bytes is refused, it is not a sequence of
    references — and returns them **deduplicated and sorted ascending by fingerprint
    string**. At-birth parent references carry no declared order significance, so
    DEC-0115's canonical multiplicity ordering applies: two sandboxes that list the
    same parents in different orders derive the same stable id. An empty sequence is
    legal (a record with no at-birth parents).
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "at_birth_parent_refs",
            "at-birth parent references are a sequence of fp1 fingerprints (a bare "
            "string is not a sequence of references)",
            given=repr(value),
        )
    resolved: dict[str, Fingerprint] = {}
    for index, item in enumerate(cast("Sequence[object]", value)):
        member = _coerce_fingerprint(item)
        if member is None:
            return _invalid(
                "at_birth_parent_refs",
                "each at-birth parent reference is a Fingerprint (or fp1:sha256:<hex> "
                "string); a minted or mutable id is never a reference",
                index=index,
                given=repr(item),
            )
        resolved[member.value] = member
    return tuple(resolved[key] for key in sorted(resolved))


# --- the per-kind record ----------------------------------------------------


def _record_identity_content(
    kind: str,
    contract_format_version: int,
    parent_refs: Sequence[Fingerprint],
    body: Mapping[str, object],
) -> dict[str, object]:
    """The record's canonical ``fp1`` identity content — the parts that ARE its
    identity.

    Built identically by :meth:`RegistrationRecord.try_create` (to derive the stable
    id) and :meth:`RegistrationRecord.fp1_identity`. It carries **only** identity
    fields: the kind, the per-kind contract format version, the canonically-ordered
    at-birth parent references, and the kind-specific body — under the CT-06 envelope
    format version. The writer, the per-writer sequence, and ``created_at`` are
    occurrence facts and are deliberately absent (DEC-0110, DEC-0114).
    """
    return {
        "class": "registration-record",
        "kind": kind,
        "contract_format_version": contract_format_version,
        # Order-significant to the serializer, so parent_refs is pre-sorted ascending
        # (DEC-0115): identical parents in any caller order derive one identity.
        "at_birth_parent_refs": [ref.value for ref in parent_refs],
        "body": dict(body),
        "format_version": CONTRACT_FORMAT_VERSION,
    }


@dataclass(frozen=True, slots=True)
class RegistrationRecord:
    """A per-kind versioned registration record whose stable id is its ``fp1``
    fingerprint (CT-06; DEC-0114, DEC-0108, DEC-0110).

    The tiny common header is ``kind``, ``contract_format_version`` (the per-kind
    contract's version), ``at_birth_parent_refs`` (identity-bearing, canonically
    ordered), ``writer`` (a :class:`~qmf.core.WriterId`), and ``sequence`` (a
    per-writer strictly-increasing ordering key); ``body`` is the opaque kind-specific
    payload; ``created_at`` is a display-only occurrence fact. ``stable_id`` is
    **derived** from the identity content (:func:`_record_identity_content`) and is
    never supplied by the caller.

    The writer, the sequence, and ``created_at`` are occurrence facts **excluded from
    identity**, so identical work from two sandboxes deduplicates by computation
    identity. The record is frozen: post-birth lineage is written only as CT-07 edges,
    never back into it, and a reader never unions :meth:`header_parent_refs` with the
    CT-07 edge set (DEC-0114).
    """

    kind: str
    contract_format_version: int
    at_birth_parent_refs: tuple[Fingerprint, ...]
    body: Mapping[str, object]
    writer: WriterId
    sequence: int
    created_at: Instant
    stable_id: Fingerprint
    # Provenance of a reserved-kind mint (identity-excluded, never part of fp1). ``None``
    # for every ordinary record and for a forged reserved look-alike; the dedicated
    # reserved-mint path stamps :data:`_RESERVED_MINT_PROVENANCE`. ``compare=False`` keeps
    # it out of equality/hash and ``repr=False`` out of the repr, so two field-identical
    # records still compare equal while a persist boundary can still tell a genuine card
    # from a forgery (H2).
    _reserved_provenance: object = field(default=None, compare=False, repr=False)

    def __post_init__(self) -> None:
        # Deep-snapshot the body so a later mutation of the caller's dict — or of a
        # nested mapping/array inside it — can never reach into this frozen,
        # append-only record.
        object.__setattr__(self, "body", _deep_freeze(self.body))

    @classmethod
    def try_create(
        cls,
        kind: object,
        contract_format_version: object,
        at_birth_parent_refs: object,
        body: object,
        writer: object,
        sequence: object,
        created_at: object,
    ) -> Result[RegistrationRecord]:
        """Validate the header and body, derive the stable id, and build a
        :class:`RegistrationRecord`, returning value-or-refusal.

        The ``kind`` must be a non-blank token that is **not** one of the two
        :data:`RESERVED_KIND_NAMES` — a reserved CT-06 kind (the human-signed
        promotion-occurrence card) is minted only through its own dedicated path, never
        this generic public factory, so a forged card can never be constructed here
        (H2; DEC-0116, DEC-0158; FM-4). ``contract_format_version`` a positive integer;
        ``at_birth_parent_refs`` a (possibly empty) sequence of fingerprints; ``body`` a
        mapping whose content is ``fp1``-clean (a float, a null, or a non-string key is
        refused when the identity is fingerprinted, via qmf-core); ``writer`` a
        :class:`~qmf.core.WriterId`; ``sequence`` a non-negative integer; and
        ``created_at`` an :class:`~qmf.core.Instant`. The stable id is **not** accepted
        from the caller — it is fingerprinted from the identity content, so a record can
        never claim an id its content does not derive (DEC-0114, DEC-0108).
        """
        kind_token = _clean_str(kind)
        if kind_token is not None and kind_token in RESERVED_KIND_NAMES:
            return _invalid(
                "kind",
                "this kind name is reserved and honored; a reserved CT-06 kind (the "
                "human-signed promotion-occurrence card) is minted only through its own "
                "dedicated path, never this generic registration factory (DEC-0116, "
                "DEC-0158; FM-1, FM-4)",
                given=repr(kind),
                kind=kind_token,
                reserved=True,
            )
        return cls._build(
            kind,
            contract_format_version,
            at_birth_parent_refs,
            body,
            writer,
            sequence,
            created_at,
            provenance=None,
        )

    @classmethod
    def _mint_reserved(
        cls,
        kind: object,
        contract_format_version: object,
        at_birth_parent_refs: object,
        body: object,
        writer: object,
        sequence: object,
        created_at: object,
    ) -> Result[RegistrationRecord]:
        """Mint a **reserved** CT-06 kind through its dedicated, package-internal path
        (H2; DEC-0116, DEC-0158).

        Identical validation to :meth:`try_create` but it does not refuse the reserved
        kind and it stamps :data:`_RESERVED_MINT_PROVENANCE` on the record, marking it as
        genuinely minted here. Only the human-signed promotion card (Story 2.3) calls this;
        it is not part of the public registration surface, so the only reserved-kind record
        that ever carries the provenance marker is one this path produced — a forged
        look-alike never does (:func:`is_genuine_reserved_record`).
        """
        return cls._build(
            kind,
            contract_format_version,
            at_birth_parent_refs,
            body,
            writer,
            sequence,
            created_at,
            provenance=_RESERVED_MINT_PROVENANCE,
        )

    @classmethod
    def _build(
        cls,
        kind: object,
        contract_format_version: object,
        at_birth_parent_refs: object,
        body: object,
        writer: object,
        sequence: object,
        created_at: object,
        *,
        provenance: object,
    ) -> Result[RegistrationRecord]:
        """Validate every header/body part, derive the stable id, and build the record.

        The single construction path shared by the public :meth:`try_create` (reserved
        kinds already refused, ``provenance`` ``None``) and the package-internal
        :meth:`_mint_reserved` (reserved kind allowed, ``provenance`` the reserved-mint
        sentinel). The stable id is fingerprinted from the identity content only.
        """
        kind_token = _clean_str(kind)
        if kind_token is None:
            return _invalid(
                "kind",
                "a registration record names a non-empty opaque kind (each kind its "
                "own contract; there is never one universal all-fields card)",
                given=repr(kind),
            )
        version = _positive_int(contract_format_version)
        if version is None:
            return _invalid(
                "contract_format_version",
                "the per-kind contract format version is a positive integer ordinal; "
                "package SemVer never enters identity (DEC-0103)",
                given=repr(contract_format_version),
            )
        refs = _coerce_parent_refs(at_birth_parent_refs)
        if isinstance(refs, TypedRefusal):
            return refs
        if not isinstance(body, Mapping):
            return _invalid(
                "body",
                "a registration record's body is a key->value mapping (the kind-specific payload)",
                given=repr(type(body).__name__),
            )
        body_map = cast("Mapping[str, object]", body)
        if not isinstance(writer, WriterId):
            return _invalid("writer", "a record header carries a WriterId", given=repr(writer))
        if isinstance(sequence, bool) or not isinstance(sequence, int) or sequence < 0:
            return _invalid(
                "sequence",
                "the per-writer sequence is a non-negative int64 ordering key; it is "
                "never an identity or dedup key (DEC-0106)",
                given=repr(sequence),
            )
        if not isinstance(created_at, Instant):
            return _invalid(
                "created_at",
                "created-at is an Instant occurrence fact (display-only, excluded from identity)",
                given=repr(created_at),
            )
        content = _record_identity_content(kind_token, version, refs, body_map)
        derived = fingerprint(content)
        if is_refusal(derived):
            # The body carried a float, a null, or a non-string key — qmf-core refuses
            # it in identity content. Surface it as a body refusal (FM-1 family).
            return _invalid(
                "body",
                "the record body is not fp1-clean identity content; a binary float, a "
                "null, or a non-string key is refused (identity numerics are integers; "
                "an absent value is an omitted key)",
                cause=dict(derived.context),
            )
        return Ok(
            cls(
                kind=kind_token,
                contract_format_version=version,
                at_birth_parent_refs=refs,
                body=body_map,
                writer=writer,
                sequence=sequence,
                created_at=created_at,
                stable_id=derived.value,
                _reserved_provenance=provenance,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the parts that ARE the
        record's identity. Its fingerprint equals :attr:`stable_id`; the writer, the
        sequence, and ``created_at`` are excluded, so identical work deduplicates."""
        return _record_identity_content(
            self.kind,
            self.contract_format_version,
            self.at_birth_parent_refs,
            self.body,
        )

    def header_parent_refs(self) -> tuple[Fingerprint, ...]:
        """The at-birth parent references, header-only (DEC-0114).

        These are the record's identity-bearing at-birth parents and nothing else.
        Lineage that accrues after birth lives exclusively in CT-07 typed edges (Story
        2.2); a reader takes this header set and the CT-07 edge set as two separate
        things and **never** unions them.
        """
        return self.at_birth_parent_refs


def is_genuine_reserved_record(record: object) -> bool:
    """Whether ``record`` is a reserved-kind CT-06 record minted through its dedicated
    package-internal path (H2; DEC-0116, DEC-0158).

    A reserved kind cannot be built through the public :meth:`RegistrationRecord.try_create`
    (which refuses reserved kinds outright) or the generic
    :class:`Registrar`/:class:`KindRegistry` path — only
    :meth:`RegistrationRecord._mint_reserved`, used by the human-signed promotion card, mints
    one and stamps :data:`_RESERVED_MINT_PROVENANCE`. A forged look-alike — even one
    byte-identical to a genuine card, with the same stable id — is never stamped, so a
    persist boundary refuses it while accepting the real card (FM-4; ADR-0015).
    """
    if not isinstance(record, RegistrationRecord):
        return False
    provenance = record._reserved_provenance  # pyright: ignore[reportPrivateUsage]
    return provenance is _RESERVED_MINT_PROVENANCE


# --- per-kind contracts and the addable kind registry -----------------------


@runtime_checkable
class KindContract(Protocol):
    """The seam a per-kind contract implements (CT-06; DEC-0114).

    A kind owns its own contract — its ``name``, its ``contract_format_version``, and a
    :meth:`validate_body` that admits a body matching the kind's field set or returns a
    typed refusal. There is never one universal all-fields card; the composition root
    declares each kind's contract and registers it in a :class:`KindRegistry`.
    :class:`FieldSetKind` is the reference implementation, but any object satisfying
    this protocol is a kind contract.
    """

    @property
    def name(self) -> str:  # pragma: no cover - protocol seam
        """The kind name this contract governs."""
        ...

    @property
    def contract_format_version(self) -> int:  # pragma: no cover - protocol seam
        """The per-kind contract's format version (a positive integer ordinal)."""
        ...

    def validate_body(
        self, body: Mapping[str, object]
    ) -> Result[Mapping[str, object]]:  # pragma: no cover - protocol seam
        """Admit a body matching this kind's field set, or return a typed refusal."""
        ...


@dataclass(frozen=True, slots=True)
class FieldSetKind:
    """A per-kind contract that admits a closed, addable field set (CT-06; DEC-0114).

    The reference :class:`KindContract`: a body is admitted when every key is drawn
    from ``required_fields ∪ optional_fields`` and every required field is present. A
    field the contract does not define is a typed refusal (FM-1) — a kind's field set
    is addable in a later contract version, never redefined. Deep ``fp1`` cleanliness
    of the values (no float, no null) is enforced downstream when the record is
    fingerprinted by qmf-core; this contract governs the field NAMES.
    """

    name: str
    contract_format_version: int
    required_fields: frozenset[str]
    optional_fields: frozenset[str]

    @classmethod
    def try_create(
        cls,
        name: object,
        contract_format_version: object,
        required_fields: object = (),
        optional_fields: object = (),
    ) -> Result[FieldSetKind]:
        """Validate and build a :class:`FieldSetKind`, returning value-or-refusal.

        ``name`` must be a non-blank token, ``contract_format_version`` a positive
        integer, and the field collections iterables of non-blank strings that do not
        overlap (a field is required or optional, never both).
        """
        name_token = _clean_str(name)
        if name_token is None:
            return _invalid("name", "a kind contract names a non-empty kind", given=repr(name))
        version = _positive_int(contract_format_version)
        if version is None:
            return _invalid(
                "contract_format_version",
                "a kind contract carries a positive integer format version",
                given=repr(contract_format_version),
            )
        required = _field_set(required_fields, "required_fields")
        if isinstance(required, TypedRefusal):
            return required
        optional = _field_set(optional_fields, "optional_fields")
        if isinstance(optional, TypedRefusal):
            return optional
        overlap = required & optional
        if overlap:
            return _invalid(
                "optional_fields",
                "a field is either required or optional, never both",
                overlap=sorted(overlap),
            )
        return Ok(
            cls(
                name=name_token,
                contract_format_version=version,
                required_fields=required,
                optional_fields=optional,
            )
        )

    def validate_body(self, body: Mapping[str, object]) -> Result[Mapping[str, object]]:
        """Admit ``body`` when its field NAMES match this kind's contract (FM-1).

        A key outside ``required_fields ∪ optional_fields`` — or a missing required
        field — is an ``invalid input`` refusal naming the offending fields; kinds are
        addable and never redefined, so an unknown field is refused, never absorbed.
        The Mapping shape is guaranteed at the boundary that reaches here (the record
        factory and the :class:`Registrar` both validate it), so this admits field
        NAMES, not the container type.
        """
        keys = frozenset(body.keys())
        allowed = self.required_fields | self.optional_fields
        unknown = keys - allowed
        if unknown:
            return _invalid(
                "body",
                "the body carries fields this kind's contract does not define; a kind "
                "field set is addable in a later version, never redefined (FM-1)",
                kind=self.name,
                unknown=sorted(unknown),
                allowed=sorted(allowed),
            )
        missing = self.required_fields - keys
        if missing:
            return _invalid(
                "body",
                "the body is missing fields this kind's contract requires (FM-1)",
                kind=self.name,
                missing=sorted(missing),
            )
        return Ok(body)


def _field_set(value: object, field: str) -> frozenset[str] | TypedRefusal:
    """Resolve an iterable of non-blank field-name strings to a frozenset, or refuse.

    A bare string is refused — it is a sequence of characters, not a field set — and
    every element must be a non-blank string.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, (Sequence, frozenset, set)):
        return _invalid(
            field,
            "a field set is a collection of field-name strings (a bare string is not a field set)",
            given=repr(value),
        )
    names: set[str] = set()
    for item in cast("Sequence[object]", value):
        token = _clean_str(item)
        if token is None:
            return _invalid(field, "each field name is a non-empty string", given=repr(item))
        names.add(token)
    return frozenset(names)


class KindRegistry:
    """The addable-never-redefined roster of known per-kind contracts (CT-06;
    DEC-0114).

    The composition root registers each kind's :class:`KindContract` here; a
    registration then resolves its kind through :meth:`contract_for`. Kinds are
    **addable** (register a new contract) and **never redefined** (re-registering an
    existing name is refused). The two :data:`RESERVED_KIND_NAMES` are honored from
    birth: the generic path may neither register under them nor mint a record of them,
    so the promotion-occurrence card — the only path to live money — can never be
    forged through this addable surface (DEC-0116, DEC-0158).
    """

    def __init__(self) -> None:
        self._kinds: dict[str, KindContract] = {}

    def register(self, contract: KindContract) -> Result[KindContract]:
        """Add ``contract`` to the roster, returning value-or-refusal.

        A blank name, a non-positive format version, a reserved name, or a name
        already registered is refused — kinds are addable but never redefined, and a
        reserved name is set aside for its own dedicated contract, never the generic
        path.
        """
        name = _clean_str(contract.name)
        if name is None:
            return _invalid("name", "a kind contract names a non-empty kind", given=repr(contract))
        if _positive_int(contract.contract_format_version) is None:
            return _invalid(
                "contract_format_version",
                "a kind contract carries a positive integer format version",
                kind=name,
                given=repr(contract.contract_format_version),
            )
        if name in RESERVED_KIND_NAMES:
            return _invalid(
                "kind",
                "this kind name is reserved and honored; its body is defined by its "
                "own dedicated contract, never the generic registration path",
                kind=name,
                reserved=True,
            )
        if name in self._kinds:
            return _invalid(
                "kind",
                "this kind is already registered; kinds are addable but never "
                "redefined (mint a new kind or a new format version instead)",
                kind=name,
            )
        self._kinds[name] = contract
        return Ok(contract)

    def contract_for(self, kind: object) -> Result[KindContract]:
        """Resolve the :class:`KindContract` for ``kind``, returning value-or-refusal.

        A registered kind resolves to its contract; a reserved kind is refused as
        reserved-and-honored (its body is not reachable through this path); any other
        name is refused as unknown — kinds are addable, so register the contract first
        (FM-1).
        """
        name = _clean_str(kind)
        if name is None:
            return _invalid("kind", "a kind is a non-empty opaque name", given=repr(kind))
        registered = self._kinds.get(name)
        if registered is not None:
            return Ok(registered)
        if name in RESERVED_KIND_NAMES:
            return _invalid(
                "kind",
                "this kind name is reserved and honored; its body is defined by its "
                "own dedicated contract, not this generic path (FM-1)",
                kind=name,
                reserved=True,
            )
        return _invalid(
            "kind",
            "unknown kind; a kind must be registered before use (kinds are addable, "
            "never redefined) (FM-1)",
            kind=name,
            known=sorted(self._kinds),
        )

    def is_reserved(self, kind: object) -> bool:
        """Whether ``kind`` is one of the honored reserved kind names."""
        return isinstance(kind, str) and kind in RESERVED_KIND_NAMES

    def known_kinds(self) -> frozenset[str]:
        """The names of every currently-registered (non-reserved) kind."""
        return frozenset(self._kinds)


# --- the in-memory reference registrar (FM-6) -------------------------------


@dataclass(frozen=True, slots=True)
class RegistrationReceipt:
    """The receipt of an admitted registration (CT-06; DEC-0108).

    ``outcome`` is ``stored`` for a first write of this stable id or ``idempotent``
    for a byte-identical re-write; a true collision is not an outcome — it is refused.
    ``record`` is the admitted :class:`RegistrationRecord`.
    """

    outcome: WriteOutcome
    record: RegistrationRecord


class Registrar:
    """A pure, in-memory content-addressed registration guard (CT-06; DEC-0114,
    DEC-0108).

    Composes the kind check (:class:`KindRegistry`), the ``fp1`` derivation, and
    qmf-core's :func:`~qmf.core.reconcile_write`: a registration is validated against
    its kind's contract, its stable id is derived from its identity content, and the
    write is admitted as ``stored``, accepted silently as ``idempotent``, or refused
    as a true collision. It is a reference guard for tests and the reference-usage
    examples — a dict of ``digest -> canonical bytes`` with no I/O — **not** the
    platform's storage; durable persistence through qmf-data's store-seam is Story 2.4
    (the same way :class:`~qmf.core.GovernedEvidenceLedger` is a pure reference guard,
    not the production store).
    """

    def __init__(self, kinds: KindRegistry) -> None:
        self._kinds: KindRegistry = kinds
        self._bytes: dict[str, bytes] = {}
        self._records: dict[str, RegistrationRecord] = {}

    def register(
        self,
        *,
        kind: object,
        body: object,
        writer: object,
        sequence: object,
        created_at: object,
        at_birth_parent_refs: object = (),
    ) -> Result[RegistrationReceipt]:
        """Validate, derive the stable id, and admit a registration.

        Resolves the kind's contract (FM-1 for an unknown or reserved kind), admits
        the body against it (FM-1 for a field the contract does not define), builds the
        record (deriving its ``fp1`` stable id), and reconciles the write: a first
        write is ``stored``, a byte-identical re-write is ``idempotent``, and the same
        stable id presented with differing bytes is a true collision — refused and
        alarmed, never overwritten (FM-6). The record's ``contract_format_version`` is
        stamped from the resolved kind contract, so the header can never disagree with
        the kind it names.
        """
        contract = self._kinds.contract_for(kind)
        if is_refusal(contract):
            return contract
        if not isinstance(body, Mapping):
            return _invalid(
                "body",
                "a registration body is a key->value mapping",
                given=repr(type(body).__name__),
            )
        admitted = contract.value.validate_body(cast("Mapping[str, object]", body))
        if is_refusal(admitted):
            return admitted
        built = RegistrationRecord.try_create(
            contract.value.name,
            contract.value.contract_format_version,
            at_birth_parent_refs,
            admitted.value,
            writer,
            sequence,
            created_at,
        )
        if is_refusal(built):
            return built
        return self._admit(built.value)

    def _admit(self, record: RegistrationRecord) -> Result[RegistrationReceipt]:
        """Reconcile ``record`` against the content-addressed store (the FM-6 rule).

        Keys on the record's ``fp1`` stable-id digest and compares canonical bytes: a
        first write stores, a byte-identical re-write is idempotent, and differing
        bytes under one stable id are a true collision — refused and alarmed, never
        overwritten (DEC-0108).
        """
        canonical = canonical_bytes(record.fp1_identity())
        if is_refusal(canonical):  # pragma: no cover - identity is canonical by construction
            return canonical
        digest = record.stable_id.digest
        existing = self._bytes.get(digest)
        decision = reconcile_write(record.stable_id, canonical.value, existing)
        if is_refusal(decision):
            return decision
        if decision.value is WriteOutcome.STORED:
            self._bytes[digest] = canonical.value
            self._records[digest] = record
        return Ok(RegistrationReceipt(outcome=decision.value, record=record))

    def record_for(self, stable_id: object) -> RegistrationRecord | None:
        """The registered record under ``stable_id``, or ``None`` if none is stored.

        A lookup miss is a normal answer, not a failure, so it is ``None`` rather than
        a refusal. Accepts a :class:`~qmf.core.Fingerprint` or a valid fingerprint
        string; anything malformed simply resolves to no record.
        """
        resolved = _coerce_fingerprint(stable_id)
        if resolved is None:
            return None
        return self._records.get(resolved.digest)

    def stable_ids(self) -> frozenset[str]:
        """The ``fp1`` stable-id strings of every currently-stored record."""
        return frozenset(record.stable_id.value for record in self._records.values())
