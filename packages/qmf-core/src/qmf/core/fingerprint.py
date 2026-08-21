"""CT-05 — the canonical serializer, fp1 fingerprint, result label, and worlds
(COMP-QMF-CORE).

The single identity implementation the whole framework shares, defined here in
``qmf-core`` and **nowhere else**: no other package computes a fingerprint except
by calling this module (CT-05; DEC-0108). Two conformant producers and two merging
sandboxes agree on identity because they hash the same canonical bytes with the
same recipe.

Four things this module pins down.

**The canonical serializer and the fp1 fingerprint.** :func:`canonical_bytes`
turns identity content into the one canonical byte form; :func:`fingerprint` hashes
it and emits the self-describing string ``fp1:sha256:<hex>`` (:class:`Fingerprint`).
The recipe is pinned (DEC-0108, DEC-0158): UTF-8 JSON; object keys sorted
lexicographically at every depth; no insignificant whitespace; strings
NFC-normalized; all identity numerics are integers (a binary ``float`` is **refused**
in identity content); exact rationals and money-class values take CT-01's pinned
canonical form (reached through each value's ``fp1_identity`` — reduced to lowest
terms, two keys always present); ``null`` is prohibited (an absent value is an
omitted key, never a null); arrays are order-significant; hashed SHA-256. The
``fp1`` prefix versions the recipe — a future upgrade mints ``fp2`` and every old
fingerprint stays valid forever. Every contract field is identity by default; a
display-only exclusion is an explicit design choice a value type makes by leaving a
part out of its ``fp1_identity`` (as :class:`~qmf.core.chrono.DisplayTime` and
:class:`OccurrenceRecord` do), never an implementer's per-call judgment.

**The result label and its worlds.** A computed result entering evidence carries a
:class:`ResultLabel`: producer contract identity, producer contract format version,
input fingerprints, evidence time range (a half-open :class:`~qmf.core.chrono.Interval`
over int64 UTC nanoseconds), computation identity, evidence class, and
:class:`World` — and those parts together **ARE** its identity. The
:attr:`~ResultLabel.computation_identity` is content-derived from the other parts,
so identical work from two sandboxes deduplicates and merges. The
:class:`OccurrenceRecord` — when, where, and by whom a computation ran — is separate
provenance **outside** identity, never folded into the label.

**World policy and storage separation.** :class:`World` is ``live | replay |
simulated``. ``simulated`` is reserved but **UNUSABLE** in V1 — routing a simulated
result into governed evidence is a ``policy rejection`` typed refusal until the
backtesting sitting defines simulated-time typing (FM-7, GAP-0048). A non-live world
never writes the live evidence namespace: :func:`governed_namespace` routes each
world to its own namespace, so world separation is delivered by storage separation,
not by identity distinctness alone (DEC-0110).

**Idempotent re-write vs true collision (FM-6).** :func:`reconcile_write` is the
pure decision: presenting an existing ``fp1`` hash with byte-identical content is
accepted silently (idempotent); differing bytes under the same hash — a true
collision — are refused and alarmed, never overwritten (DEC-0108).
:class:`GovernedEvidenceLedger` is a small in-memory reference guard that composes
the world policy and the FM-6 decision; it is a pure identity guard for tests and
examples, **not** the platform's storage (the governed rooms live in qmf-registry
and qmf-data), the same way :class:`~qmf.core.chrono.DataDrivenClock` is a pure
reference Clock.

Two version ladders never conflate (DEC-0103): package SemVer
(``qmf.core.__version__``) is display-only provenance that **never** enters identity,
while every serialized artifact stamps its own integer contract **format version**
whose meaning never mutates — an incompatible change mints the next version.

Stdlib only (DEC-0104). Frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core.chrono import Instant, Interval, WriterId
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "LIVE_EVIDENCE_NAMESPACE",
    "EvidenceClass",
    "Fingerprint",
    "GovernedEvidenceLedger",
    "OccurrenceRecord",
    "ResultLabel",
    "World",
    "WriteOutcome",
    "WriteReceipt",
    "canonical_bytes",
    "fingerprint",
    "governed_namespace",
    "reconcile_write",
]

# Every serialized CT-05 artifact stamps this integer contract format version; its
# meaning never mutates — an incompatible change mints the next version plus a
# migration note (DEC-0103; versioning-from-birth L15). Reached as
# ``qmf.core.fingerprint.CONTRACT_FORMAT_VERSION``; each contract owns its own.
CONTRACT_FORMAT_VERSION: Final[int] = 1

# The one minted recipe prefix and the one hash algorithm. A recipe upgrade mints
# ``fp2`` while every ``fp1`` fingerprint stays valid forever (DEC-0108).
_FP1_PREFIX: Final[str] = "fp1"
_SHA256: Final[str] = "sha256"
_HEX_DIGEST: Final[re.Pattern[str]] = re.compile(r"\A[0-9a-f]{64}\Z")

# Governed-evidence namespaces. World separation is storage separation: a non-live
# world routes to its own namespace and can never resolve to the live one
# (DEC-0110). ``simulated`` has no namespace — it is refused (FM-7).
LIVE_EVIDENCE_NAMESPACE: Final[str] = "live"
_REPLAY_EVIDENCE_NAMESPACE: Final[str] = "replay"


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal an identity operation returns.

    ``retryability`` is ``no`` — a float in identity content, a null value, a
    malformed fingerprint, or a bad label part is a caller mistake, not a transient
    condition — and ``context`` always names the offending ``field`` and a
    human-legible ``reason`` (returned, never raised; CT-04; DEC-0109).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.INVALID_INPUT,
        retryability=Retryability.NO,
        context=context,
    )


def _policy(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``policy rejection`` refusal the world policy and the FM-6
    collision guard return (CT-05; DEC-0110, DEC-0108).

    ``simulated`` into governed evidence, a non-live world reaching the live
    namespace, and a true fingerprint collision are all policy rejections — the
    pure core surface never returns ``storage failure`` (that category arises at
    the data boundary, FM-8).
    """
    context: dict[str, object] = {"field": field, "reason": reason}
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context=context,
    )


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``."""
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


# --- the canonical serializer -----------------------------------------------


@runtime_checkable
class _HasFp1Identity(Protocol):
    """A value that exposes its own canonical ``fp1`` identity content.

    Every qmf-core value type that enters identity implements this (Money, Price,
    Instant, Interval, CalendarIdentity, ResultLabel, …). The serializer resolves
    such a value to its content at any depth, so exact rationals and money-class
    values always take CT-01's pinned canonical form.
    """

    def fp1_identity(self) -> Mapping[str, object]:  # pragma: no cover - protocol seam
        ...


def _canonicalize(node: object) -> object | TypedRefusal:
    """Resolve, validate, and NFC-normalize one identity-content node.

    Returns a JSON-native tree of ``dict[str, object]`` / ``list[object]`` / ``str``
    / ``int`` / ``bool`` — or a :class:`TypedRefusal`. A value exposing
    ``fp1_identity`` is resolved to its content first; a binary ``float`` and a
    ``null`` are refused (floats never enter identity; an absent value is an omitted
    key); an unsupported type (bytes, Decimal, Fraction, set, an arbitrary object) is
    refused so callers pass canonical content, never a lossy or ambiguous value.
    """
    if isinstance(node, _HasFp1Identity):
        node = node.fp1_identity()
    # bool is an int subclass; it is a distinct JSON true/false, resolved first.
    if isinstance(node, bool):
        return node
    if isinstance(node, int):
        return node
    if isinstance(node, str):
        return unicodedata.normalize("NFC", node)
    if isinstance(node, Mapping):
        return _canonicalize_mapping(cast("Mapping[object, object]", node))
    if isinstance(node, (list, tuple)):
        return _canonicalize_array(cast("Sequence[object]", node))
    if node is None:
        return _invalid(
            "value",
            "null is prohibited in identity content; an absent value is an omitted "
            "key, never a null (DEC-0108)",
        )
    if isinstance(node, float):
        return _invalid(
            "value",
            "a binary float is refused in identity content; identity numerics are "
            "integers, and exact rationals take CT-01's num/den canonical form (FM-1)",
            given=repr(node),
        )
    return _invalid(
        "value",
        "unsupported type in identity content; pass a canonical value (a value with "
        "fp1_identity, or JSON-native str/int/bool/list/object)",
        given=repr(type(node).__name__),
    )


def _canonicalize_mapping(node: Mapping[object, object]) -> dict[str, object] | TypedRefusal:
    """Canonicalize an object: string keys only, NFC-normalized, no null values,
    no post-normalization key collision. Ordering is left to the JSON encoder's
    lexicographic key sort at emit time."""
    out: dict[str, object] = {}
    for key, value in node.items():
        # bool is an int subclass, so exclude it explicitly; keys are strings.
        if isinstance(key, bool) or not isinstance(key, str):
            return _invalid(
                "key",
                "identity object keys must be strings",
                given=repr(key),
            )
        if key.strip() == "":
            # An empty or whitespace-only key is refused for consistency with
            # DatedRecord's identity-content rule (a blank key carries no meaning and
            # would let two records fork identity on a key that renders identically).
            return _invalid(
                "key",
                "identity object keys must be non-empty, not blank or whitespace-only",
                given=repr(key),
            )
        if value is None:
            return _invalid(
                "value",
                "null is prohibited in identity content; omit the key instead",
                key=key,
            )
        clean_key = unicodedata.normalize("NFC", key)
        if clean_key in out:
            return _invalid(
                "key",
                "two keys normalize (NFC) to the same identity key; a fingerprint "
                "must not fork or collapse on normalization",
                key=clean_key,
            )
        clean_value = _canonicalize(value)
        if isinstance(clean_value, TypedRefusal):
            return clean_value
        out[clean_key] = clean_value
    return out


def _canonicalize_array(node: Sequence[object]) -> list[object] | TypedRefusal:
    """Canonicalize an order-significant array; a null element is refused."""
    out: list[object] = []
    for item in node:
        if item is None:
            return _invalid(
                "value",
                "null is prohibited in identity content, arrays included",
            )
        clean_item = _canonicalize(item)
        if isinstance(clean_item, TypedRefusal):
            return clean_item
        out.append(clean_item)
    return out


def canonical_bytes(value: object) -> Result[bytes]:
    """Serialize identity content to the one canonical byte form (CT-05; DEC-0108).

    Returns ``Ok(bytes)`` — UTF-8 JSON, keys sorted lexicographically at every
    depth, compact (no insignificant whitespace), strings NFC-normalized, arrays
    order-significant — or a :class:`TypedRefusal` when the content carries a float,
    a null, a non-string key, or an unsupported type. This is the only serializer;
    :func:`fingerprint` and every consumer's fingerprint call route through it.
    """
    clean = _canonicalize(value)
    if isinstance(clean, TypedRefusal):
        return clean
    text = json.dumps(
        clean,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return Ok(text.encode("utf-8"))


# --- the fp1 fingerprint ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class Fingerprint:
    """A self-describing identity string ``fp1:sha256:<hex>`` (CT-05; DEC-0108).

    The ``fp1`` prefix names the recipe, ``sha256`` the hash, and the 64-character
    lowercase hex is the digest. Produced only by :func:`fingerprint` (over canonical
    bytes) or parsed from an existing string via :meth:`try_create`. The unchecked
    constructor is the trusted-internal path.
    """

    value: str

    @classmethod
    def try_create(cls, value: object) -> Result[Fingerprint]:
        """Validate and build a :class:`Fingerprint` from a string, returning
        value-or-refusal.

        The string must be ``fp1:sha256:<hex>`` with exactly the minted recipe and
        algorithm and a 64-character lowercase hex digest; anything else is an
        ``invalid input`` refusal.
        """
        if not isinstance(value, str):
            return _invalid(
                "value", "a fingerprint is the string fp1:sha256:<hex>", given=repr(value)
            )
        parts = value.split(":")
        if len(parts) != 3:
            return _invalid(
                "value",
                "a fingerprint has three colon-separated parts: recipe:algorithm:digest",
                given=value,
            )
        recipe, algorithm, digest = parts
        if recipe != _FP1_PREFIX:
            return _invalid(
                "recipe",
                "fp1 is the only minted recipe prefix",
                given=recipe,
                allowed=[_FP1_PREFIX],
            )
        if algorithm != _SHA256:
            return _invalid(
                "algorithm", "sha256 is the only minted hash", given=algorithm, allowed=[_SHA256]
            )
        if _HEX_DIGEST.match(digest) is None:
            return _invalid("digest", "the digest is 64 lowercase hex characters", given=digest)
        return Ok(cls(value=value))

    @property
    def recipe(self) -> str:
        """The recipe prefix (``fp1``)."""
        return self.value.split(":", 2)[0]

    @property
    def algorithm(self) -> str:
        """The hash algorithm (``sha256``)."""
        return self.value.split(":", 2)[1]

    @property
    def digest(self) -> str:
        """The lowercase hex digest — the content-addressed key (DEC-0108)."""
        return self.value.split(":", 2)[2]


def _fingerprint_of_bytes(canonical: bytes) -> Fingerprint:
    """Hash canonical bytes and stamp the ``fp1:sha256:<hex>`` form."""
    digest = hashlib.sha256(canonical).hexdigest()
    return Fingerprint(value=f"{_FP1_PREFIX}:{_SHA256}:{digest}")


def fingerprint(value: object) -> Result[Fingerprint]:
    """Fingerprint identity content, returning value-or-refusal (CT-05; DEC-0108).

    Serializes ``value`` to canonical bytes via :func:`canonical_bytes` and hashes
    them SHA-256, emitting ``fp1:sha256:<hex>``. Equal value implies equal
    fingerprint by construction — the same canonical form for a Money stored at two
    scales, or ``6/4`` versus ``3/2``, hashes to one identity. A float, a null, or
    an unsupported type in identity content comes back as the underlying refusal.
    """
    canonical = canonical_bytes(value)
    if is_refusal(canonical):
        return canonical
    return Ok(_fingerprint_of_bytes(canonical.value))


# --- worlds, evidence classes, and the result label -------------------------


class World(StrEnum):
    """The world a result was produced in (CT-05 ``enums.world``; DEC-0110).

    ``live`` is real venue clocks and quotes (paper and demo runs are ``live`` and
    stay comparable for alpha-decay sensing); ``replay`` is a data-driven injected
    clock over recorded history; ``simulated`` is synthetic data — **reserved but
    unusable in V1** (routing it into governed evidence is a policy rejection until
    the backtesting sitting defines simulated-time typing, GAP-0048).
    """

    LIVE = "live"
    REPLAY = "replay"
    SIMULATED = "simulated"


class EvidenceClass(StrEnum):
    """The evidence class of a result (``registry:evidence_classes``; DEC-0129,
    DEC-0131).

    A named, identity-bearing part of the result label. An ``unconfirmed`` output
    links to its confirmed successor elsewhere; a read requesting confirmed evidence
    refuses unconfirmed rows rather than filtering silently (a registry-layer rule).
    """

    CONFIRMED = "confirmed"
    UNCONFIRMED = "unconfirmed"
    PROVISIONAL = "provisional"


def _coerce_world(value: object) -> World | None:
    """Resolve ``value`` to a :class:`World` member, or ``None``."""
    if isinstance(value, World):
        return value
    if isinstance(value, str):
        try:
            return World(value)
        except ValueError:
            return None
    return None


def _coerce_evidence_class(value: object) -> EvidenceClass | None:
    """Resolve ``value`` to an :class:`EvidenceClass` member, or ``None``."""
    if isinstance(value, EvidenceClass):
        return value
    if isinstance(value, str):
        try:
            return EvidenceClass(value)
        except ValueError:
            return None
    return None


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    """Resolve a :class:`Fingerprint` or a valid fingerprint string, or ``None``."""
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


def _label_content(
    producer_value: str,
    format_version: int,
    input_values: Sequence[str],
    evidence_time_range: Interval,
    evidence_class: str,
    world: str,
) -> dict[str, object]:
    """The result label's canonical identity content — the parts that ARE its
    identity. Built identically by :meth:`ResultLabel.try_create` (to derive the
    computation identity) and :meth:`ResultLabel.fp1_identity`."""
    return {
        "class": "result-label",
        "producer_contract_identity": producer_value,
        "producer_contract_format_version": format_version,
        # Order-significant: the fp1 array rule makes the stored ordering significant.
        "input_fingerprints": list(input_values),
        "evidence_time_range": evidence_time_range.fp1_identity(),
        "evidence_class": evidence_class,
        "world": world,
        "format_version": CONTRACT_FORMAT_VERSION,
    }


@dataclass(frozen=True, slots=True)
class ResultLabel:
    """A computed result's identity — the AD-12 result label (CT-05; DEC-0110,
    DEC-0131).

    Its parts together **ARE** its identity: ``producer_contract_identity`` (the
    configured producer's fingerprint, distinct from the format version so two
    formulas can never share a label), ``producer_contract_format_version`` (the
    artifact's integer format version — the second version ladder, never package
    SemVer), ``input_fingerprints`` (the fp1 fingerprints of every identity-bearing
    input, order-significant), ``evidence_time_range`` (a half-open
    :class:`~qmf.core.chrono.Interval` over int64 UTC nanoseconds), ``evidence_class``,
    ``world``, and the derived ``computation_identity``. The computation identity is
    content-derived from the other parts, so identical work from two sandboxes
    deduplicates and merges. The occurrence record — when, where, by whom — is
    separate provenance outside identity (:class:`OccurrenceRecord`), never folded in.

    Human display names live outside identity; parts are addable in later label
    versions, never redefined.
    """

    producer_contract_identity: Fingerprint
    producer_contract_format_version: int
    input_fingerprints: tuple[Fingerprint, ...]
    evidence_time_range: Interval
    evidence_class: EvidenceClass
    world: World
    computation_identity: Fingerprint

    @classmethod
    def try_create(
        cls,
        producer_contract_identity: object,
        producer_contract_format_version: object,
        input_fingerprints: object,
        evidence_time_range: object,
        evidence_class: object,
        world: object,
    ) -> Result[ResultLabel]:
        """Validate the identity parts, derive the computation identity, and build
        a :class:`ResultLabel`, returning value-or-refusal.

        The producer identity and each input must be a :class:`Fingerprint` (or a
        valid fingerprint string); the format version a positive integer; the time
        range an :class:`~qmf.core.chrono.Interval`; the evidence class and world
        members of their closed sets. The computation identity is **not** supplied —
        it is fingerprinted from the other parts so identical work deduplicates.
        """
        producer = _coerce_fingerprint(producer_contract_identity)
        if producer is None:
            return _invalid(
                "producer_contract_identity",
                "the producer contract identity is a Fingerprint (or fp1:sha256:<hex> string)",
                given=repr(producer_contract_identity),
            )
        version = producer_contract_format_version
        if isinstance(version, bool) or not isinstance(version, int) or version < 1:
            return _invalid(
                "producer_contract_format_version",
                "the contract format version is a positive integer ordinal; package "
                "SemVer never enters here (DEC-0103)",
                given=repr(producer_contract_format_version),
            )
        inputs = _coerce_input_fingerprints(input_fingerprints)
        if isinstance(inputs, TypedRefusal):
            return inputs
        if not isinstance(evidence_time_range, Interval):
            return _invalid(
                "evidence_time_range",
                "the evidence time range is a half-open Interval over int64 UTC ns",
                given=repr(evidence_time_range),
            )
        resolved_class = _coerce_evidence_class(evidence_class)
        if resolved_class is None:
            return _invalid(
                "evidence_class",
                "the evidence class is one of the closed set",
                given=repr(evidence_class),
                allowed=[member.value for member in EvidenceClass],
            )
        resolved_world = _coerce_world(world)
        if resolved_world is None:
            return _invalid(
                "world",
                "world is one of the closed set",
                given=repr(world),
                allowed=[member.value for member in World],
            )
        content = _label_content(
            producer.value,
            version,
            [fp.value for fp in inputs],
            evidence_time_range,
            resolved_class.value,
            resolved_world.value,
        )
        computation = fingerprint(content)
        if is_refusal(computation):  # pragma: no cover - content is canonical by construction
            return computation
        return Ok(
            cls(
                producer_contract_identity=producer,
                producer_contract_format_version=version,
                input_fingerprints=inputs,
                evidence_time_range=evidence_time_range,
                evidence_class=resolved_class,
                world=resolved_world,
                computation_identity=computation.value,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — the parts that ARE the
        label's identity. Its fingerprint equals :attr:`computation_identity`; the
        derived identity itself is not re-folded in, so there is no circularity."""
        return _label_content(
            self.producer_contract_identity.value,
            self.producer_contract_format_version,
            [fp.value for fp in self.input_fingerprints],
            self.evidence_time_range,
            self.evidence_class.value,
            self.world.value,
        )


def _coerce_input_fingerprints(value: object) -> tuple[Fingerprint, ...] | TypedRefusal:
    """Resolve an order-significant sequence of input fingerprints (empty allowed).

    A bare string or bytes is refused — it is not a sequence of fingerprints — and
    any element that is not a :class:`Fingerprint` or a valid fingerprint string is
    refused, naming its position.
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "input_fingerprints",
            "input fingerprints are an order-significant sequence of Fingerprints",
            given=repr(value),
        )
    resolved: list[Fingerprint] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        member = _coerce_fingerprint(item)
        if member is None:
            return _invalid(
                "input_fingerprints",
                "each input is a Fingerprint (or fp1:sha256:<hex> string)",
                index=index,
                given=repr(item),
            )
        resolved.append(member)
    return tuple(resolved)


@dataclass(frozen=True, slots=True)
class OccurrenceRecord:
    """When, where, and by whom a computation ran (CT-05; DEC-0110).

    Separate provenance that sits **outside** identity and is never folded into a
    :class:`ResultLabel`: ``ran_at`` (when), and the :class:`~qmf.core.chrono.WriterId`
    (its machine is where, its role and stream are by whom). Deliberately exposes no
    ``fp1_identity`` — two results sharing one label identity but produced by
    different occurrences dedup to the one computation identity, and fingerprinting an
    occurrence record is refused as unsupported identity content.
    """

    ran_at: Instant
    writer: WriterId

    @classmethod
    def try_create(cls, ran_at: object, writer: object) -> Result[OccurrenceRecord]:
        """Validate and build an :class:`OccurrenceRecord`, returning value-or-refusal."""
        if not isinstance(ran_at, Instant):
            return _invalid("ran_at", "the occurrence instant is an Instant", given=repr(ran_at))
        if not isinstance(writer, WriterId):
            return _invalid("writer", "the occurrence writer is a WriterId", given=repr(writer))
        return Ok(cls(ran_at=ran_at, writer=writer))


# --- world policy and the FM-6 idempotent/collision guard -------------------


def governed_namespace(world: object) -> Result[str]:
    """The governed-evidence storage namespace a result of this world may occupy
    (CT-05; DEC-0110, FM-7).

    ``simulated`` returns a ``policy rejection`` — it is reserved but unusable in V1
    until the backtesting sitting defines simulated-time typing (GAP-0048). ``live``
    resolves to :data:`LIVE_EVIDENCE_NAMESPACE`; ``replay`` resolves to its own
    non-live namespace. Because the namespace is derived from the world, a non-live
    world can never resolve to the live namespace — world separation is delivered by
    storage separation, not by identity distinctness alone.
    """
    resolved = _coerce_world(world)
    if resolved is None:
        return _invalid(
            "world",
            "world is one of the closed set",
            given=repr(world),
            allowed=[member.value for member in World],
        )
    if resolved is World.SIMULATED:
        return _policy(
            "world",
            "world=simulated is reserved-unusable in V1; writing it into governed "
            "evidence is refused until the backtesting sitting defines simulated-time "
            "typing (FM-7, GAP-0048)",
            world=resolved.value,
            gap="GAP-0048",
        )
    if resolved is World.LIVE:
        return Ok(LIVE_EVIDENCE_NAMESPACE)
    return Ok(_REPLAY_EVIDENCE_NAMESPACE)


class WriteOutcome(StrEnum):
    """The outcome of an accepted governed-evidence write (CT-05; DEC-0108).

    ``stored`` is a first write of this fingerprint; ``idempotent`` is a byte-identical
    re-write, accepted silently. A true collision is not an outcome — it is refused.
    """

    STORED = "stored"
    IDEMPOTENT = "idempotent"


@dataclass(frozen=True, slots=True)
class WriteReceipt:
    """The receipt of an accepted governed-evidence write."""

    outcome: WriteOutcome
    fingerprint: Fingerprint
    namespace: str


def reconcile_write(fp: object, canonical: object, existing: object) -> Result[WriteOutcome]:
    """The pure FM-6 idempotent/collision decision (CT-05; DEC-0108).

    Given a presented ``fp`` fingerprint, the ``canonical`` bytes being written, and
    the ``existing`` bytes already stored under that fingerprint (``None`` when the
    fingerprint is unseen): an unseen fingerprint is ``stored``; byte-identical
    ``existing`` is ``idempotent`` (accepted silently); differing bytes under the
    same fingerprint — a true collision — are refused and alarmed, never overwritten.
    The caller owns the actual bytes and storage; this is the decision only, so the
    same rule holds wherever real storage lives.
    """
    if not isinstance(fp, Fingerprint):
        return _invalid("fp", "a write presents a Fingerprint", given=repr(fp))
    if not isinstance(canonical, bytes):
        return _invalid(
            "canonical", "the written content is canonical bytes", given=repr(canonical)
        )
    if existing is None:
        return Ok(WriteOutcome.STORED)
    if not isinstance(existing, bytes):
        return _invalid(
            "existing", "the stored content is canonical bytes or None", given=repr(existing)
        )
    if existing == canonical:
        return Ok(WriteOutcome.IDEMPOTENT)
    return _policy(
        "fingerprint",
        "a write presented an existing fp1 hash with differing bytes (a true "
        "collision); it is refused and alarmed, never overwritten (FM-6)",
        fingerprint=fp.value,
        alarm=True,
        notification_tier="alarm",
    )


class GovernedEvidenceLedger:
    """A pure, in-memory content-addressed identity guard (CT-05; DEC-0108,
    DEC-0110).

    Composes the world policy (:func:`governed_namespace`) and the FM-6 decision
    (:func:`reconcile_write`): a write is routed to its world's namespace, then
    accepted as ``stored``, accepted silently as ``idempotent``, or refused as a
    collision. It is a reference guard for tests and examples — a dict of
    ``namespace -> {digest -> canonical bytes}`` with no I/O — **not** the platform's
    storage, whose governed rooms live in qmf-registry and qmf-data (the same way
    :class:`~qmf.core.chrono.DataDrivenClock` is a pure reference Clock, not the
    production clock).
    """

    def __init__(self) -> None:
        self._namespaces: dict[str, dict[str, bytes]] = {}

    def admit(self, fp: object, canonical: object, *, namespace: object) -> Result[WriteReceipt]:
        """Admit ``canonical`` bytes under fingerprint ``fp`` into ``namespace``.

        The low-level FM-6 primitive: it keys on the presented fingerprint's digest
        and compares bytes, so it detects a true collision (same hash, differing
        bytes) — the one path where identity is asserted but content differs. First
        write stores; a byte-identical re-write is idempotent; a collision is refused.

        The presented fingerprint is re-derived from the presented bytes and a
        mismatch is refused (``invalid input``) **before** anything is stored. Without
        this guard a caller bug — admitting real bytes under the wrong fingerprint —
        would be stored and then turn the next *correct* write under that fingerprint
        into a spurious "true collision" alarm, the one signal that must never be
        noise (FM-6; DEC-0108).
        """
        if not isinstance(fp, Fingerprint):
            return _invalid("fp", "a write presents a Fingerprint", given=repr(fp))
        if not isinstance(canonical, bytes):
            return _invalid(
                "canonical", "the written content is canonical bytes", given=repr(canonical)
            )
        room = _clean_str(namespace)
        if room is None:
            return _invalid("namespace", "a namespace is a non-empty string", given=repr(namespace))
        computed = _fingerprint_of_bytes(canonical)
        if computed.value != fp.value:
            return _invalid(
                "fp",
                "the presented fingerprint does not match the presented bytes; a "
                "write is content-addressed, so admitting bytes under the wrong "
                "fingerprint is refused rather than manufacturing a false collision",
                given=fp.value,
                computed=computed.value,
            )
        existing = self._namespaces.get(room, {}).get(fp.digest)
        decision = reconcile_write(fp, canonical, existing)
        if is_refusal(decision):
            return decision
        if decision.value is WriteOutcome.STORED:
            self._namespaces.setdefault(room, {})[fp.digest] = canonical
        return Ok(WriteReceipt(outcome=decision.value, fingerprint=fp, namespace=room))

    def write(self, content: object, *, world: object) -> Result[WriteReceipt]:
        """Fingerprint ``content``, route by ``world``, and admit it.

        ``world=simulated`` is refused before any bytes are computed (FM-7); a
        non-live world routes to its own namespace and never the live one; the
        content's canonical bytes and fp1 fingerprint drive the FM-6 decision.
        """
        room = governed_namespace(world)
        if is_refusal(room):
            return room
        canonical = canonical_bytes(content)
        if is_refusal(canonical):
            return canonical
        fp = _fingerprint_of_bytes(canonical.value)
        return self.admit(fp, canonical.value, namespace=room.value)

    def write_label(self, label: object) -> Result[WriteReceipt]:
        """Write a governed result by its :class:`ResultLabel`.

        The label's world routes the write and its computation identity is the
        content-addressed key, so identical work from two sandboxes deduplicates
        (idempotent) and ``simulated`` labels are refused (FM-7).
        """
        if not isinstance(label, ResultLabel):
            return _invalid("label", "a governed write presents a ResultLabel", given=repr(label))
        return self.write(label, world=label.world)
