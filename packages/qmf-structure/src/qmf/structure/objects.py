"""CT-17 — the causal structure object mint and the in-component emission invariant
(COMP-QMF-STRUCTURE).

A structure object is a **fact about the market at a time**, not a computation: it is
minted **once, at observation**, carrying its family's identity and version, its
exact-rational parameters, its declared confirmation rule, its anchor span, its
knowledge time (``observed_at``), and its evidence class — and it is **never mutated
afterward**. State evolves only through separate append-only lifecycle and interaction
records (later stories); the object itself is frozen evidence (CT-17; DEC-0129,
DEC-0114).

This module (Story 9.1) pins down three things.

**The object mint (DEC-0129, DEC-0114).** :class:`StructureObject` carries only
identity fields — :class:`FamilyIdentity` (opaque family id + version + declared
geometry), the exact-rational ``parameters``, the declared :class:`ConfirmationRule`,
the :class:`AnchorSpan` (start/end instants and exact-:class:`~qmf.core.Price` bounds,
frozen at observation), ``observed_at`` (the earliest instant the object was derivable
from causally-available data — **known-at, never event time**), and the
:class:`~qmf.core.EvidenceClass`. The anchor span, ``observed_at``, and every lifecycle
instant are **identity fields** and are never occurrence-classified — a structure object
is a fact, not a run.

**The emission invariant, checked in-component now (DEC-0129, DEC-0121).**
:func:`check_emission_invariant` enforces
``anchor.start <= anchor.end <= observed_at <= confirmed_at <= invalidated_at`` over
whatever lifecycle instants are present, **and** ``observed_at >= the maximum evidence
time of every input actually consumed`` — the interim look-ahead guard, independent of
the deferred GAP-0016 causality registration gate. A violation is an ``invalid input``
typed refusal (FM-1). The anchor span is payload geometry: it is permitted to precede
``observed_at`` and is **excluded from the causal-availability test** (its instants are
never compared against consumed-input evidence times), yet its own ordering
(``start <= end``) and its bound (``end <= observed_at``) are part of the invariant.
Equal instants are legal — equality is consumption, not look-ahead (DEC-0106).

**Fingerprintable content, never a stamped record (DEC-0129, DEC-0131).** The library
returns fingerprintable content — :meth:`StructureObject.fp1_identity` and
:meth:`StructureObject.content_fingerprint` — and **never** stamps records: it holds no
``WriterId`` and no per-writer sequence. The composition root holds the ``WriterId`` and
the gapless per-(writer, kind) sequence and mints the registry records (CT-06). Two
sandboxes doing identical work land on one ``fp1`` by construction, so their evidence
deduplicates.

Default-deny holds: this module imports **only** ``qmf.core`` (every ``fp1`` fingerprint
is computed there, nowhere else); no roster library imports ``qmf-structure``; and
registration, lineage, and evidence flow through the application composition root
(DEC-0120). ``typing.Protocol`` is the family seam (:class:`StructureFamily`); public
value types are frozen dataclasses. Every operation succeeds or RETURNS a CT-04
:class:`~qmf.core.TypedRefusal`; domain failure is never raised across the boundary.
Stdlib plus qmf-core only; frozen, immutable values throughout (DEC-0101, DEC-0113).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from itertools import pairwise
from types import MappingProxyType
from typing import Final, Protocol, cast, runtime_checkable

from qmf.core import (
    EvidenceClass,
    ExactRational,
    Fingerprint,
    Instant,
    Ok,
    Price,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    fingerprint,
    is_refusal,
)

__all__ = [
    "CONTRACT_FORMAT_VERSION",
    "KNOWN_GEOMETRIES",
    "AnchorSpan",
    "ConfirmationRule",
    "DeclaredFamily",
    "EmissionWitness",
    "FamilyIdentity",
    "StructureFamily",
    "StructureObject",
    "check_emission_invariant",
]

# The CT-17 causal-structure contract format version — the version of the object /
# lifecycle SHAPE this module serializes, stamped into every object's identity so
# history stays readable and an incompatible change mints the next version plus a
# migration note (DEC-0103; versioning-from-birth L15). Distinct from the package
# SemVer, which is display-only provenance and never enters identity.
CONTRACT_FORMAT_VERSION: Final[int] = 1

# The seed geometry vocabulary CT-17 names (DEC-0129). Geometry is **family-declared
# and open**: a family may declare a geometry outside this set, so it is documented as
# the known set rather than enforced as a closed enum — an unknown geometry token is a
# new declaration, not a refusal. School-named geometries are barred by FM-9, not here.
KNOWN_GEOMETRIES: Final[frozenset[str]] = frozenset(
    {"point", "level", "zone", "span", "distribution", "graph"}
)


# --- refusal builders -------------------------------------------------------


def _invalid(field: str, reason: str, **extra: object) -> TypedRefusal:
    """Build the ``invalid input`` refusal a structure operation returns (FM-1).

    ``retryability`` is ``no`` — a malformed identity part, an out-of-order lifecycle
    chain, or an ``observed_at`` behind a consumed input's evidence time is a
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


# --- validation helpers -----------------------------------------------------


def _clean_str(value: object) -> str | None:
    """Return ``value`` verbatim if it is a non-blank string, else ``None``.

    Family ids, geometry tokens, and rule descriptors are opaque: the returned token is
    the caller's string unchanged — never stripped, cased, or parsed.
    """
    if isinstance(value, str) and value.strip() != "":
        return value
    return None


def _positive_int(value: object) -> int | None:
    """Return ``value`` as a genuine positive ``int`` (a ``bool`` is rejected), else
    ``None``. A family version is a positive integer ordinal; package SemVer never enters
    identity (DEC-0103)."""
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        return None
    return value


def _coerce_evidence_class(value: object) -> EvidenceClass | None:
    """Resolve ``value`` to an :class:`~qmf.core.EvidenceClass` member, or ``None``."""
    if isinstance(value, EvidenceClass):
        return value
    if isinstance(value, str):
        try:
            return EvidenceClass(value)
        except ValueError:
            return None
    return None


def _as_family_identity(value: object) -> FamilyIdentity | None:
    """Return ``value`` if it is a :class:`FamilyIdentity`, else ``None``.

    Takes ``object`` on purpose: a ``runtime_checkable`` Protocol's isinstance proves a
    member EXISTS but never its type, so a structurally-valid :class:`StructureFamily`
    may still hand back the wrong type — this check is real, not redundant.
    """
    return value if isinstance(value, FamilyIdentity) else None


def _as_confirmation_rule(value: object) -> ConfirmationRule | None:
    """Return ``value`` if it is a :class:`ConfirmationRule`, else ``None`` (see
    :func:`_as_family_identity` for why the parameter is ``object``)."""
    return value if isinstance(value, ConfirmationRule) else None


def _coerce_instants(value: object) -> tuple[Instant, ...] | TypedRefusal:
    """Resolve the consumed-input evidence times to a tuple of :class:`~qmf.core.Instant`.

    A bare string or bytes is refused — it is not a sequence of instants — and every
    element must be an :class:`~qmf.core.Instant` (an ``int`` is **not** silently coerced;
    an evidence time is a typed instant, DEC-0106). An empty sequence is legal (a mint
    that consumed no dated input).
    """
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        return _invalid(
            "consumed_input_times",
            "consumed input evidence times are a sequence of Instants (a bare string is "
            "not a sequence of instants)",
            given=repr(value),
        )
    resolved: list[Instant] = []
    for index, item in enumerate(cast("Sequence[object]", value)):
        if not isinstance(item, Instant):
            return _invalid(
                "consumed_input_times",
                "each consumed input evidence time is an Instant (int64 UTC ns), never a "
                "bare int or an event-time proxy",
                index=index,
                given=repr(item),
            )
        resolved.append(item)
    return tuple(resolved)


def _coerce_parameters(value: object) -> dict[str, ExactRational] | TypedRefusal:
    """Resolve the exact-rational parameter set, or refuse.

    Parameters are exact rationals only — declared tolerances included as ordinary
    fingerprinted parameters (DEC-0129, DEC-0126). A binary float never appears here: a
    non-:class:`~qmf.core.ExactRational` value is refused, so the money-path float ban
    holds by construction (FM-6 family). Each key is a non-blank string; an empty
    parameter set is legal.
    """
    if not isinstance(value, Mapping):
        return _invalid(
            "parameters",
            "the parameter set is a name->ExactRational mapping (exact rationals only; "
            "a binary float never enters a structure parameter)",
            given=repr(type(value).__name__),
        )
    mapping = cast("Mapping[object, object]", value)
    out: dict[str, ExactRational] = {}
    for key, item in mapping.items():
        name = _clean_str(key)
        if name is None:
            return _invalid(
                "parameters", "each parameter name is a non-empty string", given=repr(key)
            )
        if not isinstance(item, ExactRational):
            return _invalid(
                "parameters",
                "each parameter value is an ExactRational (exact rationals only, never a "
                "binary float on the money path)",
                name=name,
                given=repr(item),
            )
        out[name] = item
    return out


# --- family identity, confirmation rule, and the family seam -----------------


@dataclass(frozen=True, slots=True)
class FamilyIdentity:
    """A chart-object family's identity: an opaque id, its version, and its declared
    geometry (CT-17; DEC-0129, DEC-0058).

    A family is a **type of chart object** — point, level, zone, span, distribution,
    graph — never a strategy, bot, or Book category, and never named after a trading
    school (FM-9). ``family_id`` is opaque, stable, and never reused (the identity
    minting discipline); ``version`` rides beside it; ``geometry`` is family-declared and
    open (:data:`KNOWN_GEOMETRIES` is the seed set, not a closed enum). No seed family is
    privileged over an operator-authored one (DEC-0133).
    """

    family_id: str
    version: int
    geometry: str

    @classmethod
    def try_create(
        cls, family_id: object, version: object, geometry: object
    ) -> Result[FamilyIdentity]:
        """Validate and build a :class:`FamilyIdentity`, returning value-or-refusal.

        ``family_id`` must be a non-blank opaque token, ``version`` a positive integer,
        and ``geometry`` a non-blank family-declared token (a value outside
        :data:`KNOWN_GEOMETRIES` is accepted — geometry is open — but a blank one is
        refused).
        """
        fid = _clean_str(family_id)
        if fid is None:
            return _invalid(
                "family_id",
                "a family id is a non-empty opaque token, stable and never reused",
                given=repr(family_id),
            )
        ver = _positive_int(version)
        if ver is None:
            return _invalid(
                "version",
                "a family version is a positive integer ordinal; package SemVer never "
                "enters identity (DEC-0103)",
                given=repr(version),
            )
        geo = _clean_str(geometry)
        if geo is None:
            return _invalid(
                "geometry",
                "geometry is a non-empty family-declared token; the seed set is "
                "point|level|zone|span|distribution|graph but the vocabulary is open",
                given=repr(geometry),
            )
        return Ok(cls(family_id=fid, version=ver, geometry=geo))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this family identity."""
        return {
            "class": "family-identity",
            "family_id": self.family_id,
            "version": self.version,
            "geometry": self.geometry,
            "format_version": CONTRACT_FORMAT_VERSION,
        }


@dataclass(frozen=True, slots=True)
class ConfirmationRule:
    """A family's declared confirmation rule — the "confirmed the moment X happens" rule
    (CT-17; DEC-0129, DEC-0132, DEC-0133).

    Identity-bearing: ``descriptor`` is the declared rule, opaque and non-blank; a family
    ships into the governed library only when its rule states "confirmed the moment X
    happens" with X knowable at that instant. ``clock_confirmed`` marks the degenerate
    (clock-confirmed) legal case. ``confirmation_delay_bound`` is a declared maximum — an
    integer count of observations at the family's BarSpec — or ``None`` for the legal
    "unbounded" exclusion (only families kept out of split-governed evidence). An
    imprecise concept has no precise descriptor and stays free in an ungoverned research
    lane (FM-2), never admitted here.
    """

    descriptor: str
    clock_confirmed: bool
    confirmation_delay_bound: int | None

    @classmethod
    def try_create(
        cls,
        descriptor: object,
        *,
        clock_confirmed: object = False,
        confirmation_delay_bound: object = None,
    ) -> Result[ConfirmationRule]:
        """Validate and build a :class:`ConfirmationRule`, returning value-or-refusal.

        ``descriptor`` must be a non-blank declared rule — a blank/absent one is the
        imprecise case that is not admitted to the governed library (FM-2).
        ``clock_confirmed`` is a bool. ``confirmation_delay_bound`` is either ``None``
        (the declared unbounded exclusion) or a non-negative integer count of
        observations; a negative or non-integer bound is refused.
        """
        rule = _clean_str(descriptor)
        if rule is None:
            return _invalid(
                "descriptor",
                "a confirmation rule states 'confirmed the moment X happens' with X "
                "knowable at that instant; an imprecise (blank) rule is not admitted to "
                "the governed library and stays free in an ungoverned research lane (FM-2)",
                given=repr(descriptor),
            )
        if not isinstance(clock_confirmed, bool):
            return _invalid(
                "clock_confirmed", "clock_confirmed is a bool", given=repr(clock_confirmed)
            )
        bound = confirmation_delay_bound
        if bound is not None and (
            isinstance(bound, bool) or not isinstance(bound, int) or bound < 0
        ):
            return _invalid(
                "confirmation_delay_bound",
                "the confirmation delay bound is a non-negative integer count of "
                "observations at the family's BarSpec, or None for the declared unbounded "
                "exclusion",
                given=repr(confirmation_delay_bound),
            )
        return Ok(
            cls(
                descriptor=rule,
                clock_confirmed=clock_confirmed,
                confirmation_delay_bound=bound,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this confirmation rule.

        ``None`` never enters identity content (fp1 prohibits null): an unbounded delay
        is carried as an explicit ``confirmation_delay: "unbounded"`` token, a bounded
        one as the integer ``confirmation_delay_bound``, so the two are unambiguous.
        """
        content: dict[str, object] = {
            "class": "confirmation-rule",
            "descriptor": self.descriptor,
            "clock_confirmed": self.clock_confirmed,
            "format_version": CONTRACT_FORMAT_VERSION,
        }
        if self.confirmation_delay_bound is None:
            content["confirmation_delay"] = "unbounded"
        else:
            content["confirmation_delay_bound"] = self.confirmation_delay_bound
        return content


@runtime_checkable
class StructureFamily(Protocol):
    """The ``typing.Protocol`` seam a chart-object family implements (CT-17; DEC-0129,
    DEC-0133).

    A family exposes its :class:`FamilyIdentity` and its declared
    :class:`ConfirmationRule`; :class:`StructureObject.try_create` mints objects against
    it. Family authoring through the extension shape is the primary use case — an
    operator-authored family is a first-class peer to any seed candidate under identical
    law — so this is a structural seam, not a closed class hierarchy.
    :class:`DeclaredFamily` is the reference implementation, but any object satisfying
    this protocol is a family.
    """

    @property
    def identity(self) -> FamilyIdentity:  # pragma: no cover - protocol seam
        """The family's opaque identity, version, and declared geometry."""
        ...

    @property
    def confirmation_rule(self) -> ConfirmationRule:  # pragma: no cover - protocol seam
        """The family's declared 'confirmed the moment X happens' rule."""
        ...


@dataclass(frozen=True, slots=True)
class DeclaredFamily:
    """A declared chart-object family: an identity plus its confirmation rule (CT-17;
    DEC-0129, DEC-0133).

    The reference :class:`StructureFamily`. It privileges no seed candidate — an
    operator-authored family is built the same way — and its ``fp1`` fingerprint is the
    family's producer-contract identity for a later result label.
    """

    identity: FamilyIdentity
    confirmation_rule: ConfirmationRule

    @classmethod
    def try_create(cls, identity: object, confirmation_rule: object) -> Result[DeclaredFamily]:
        """Validate and build a :class:`DeclaredFamily`, returning value-or-refusal."""
        if not isinstance(identity, FamilyIdentity):
            return _invalid("identity", "a family carries a FamilyIdentity", given=repr(identity))
        if not isinstance(confirmation_rule, ConfirmationRule):
            return _invalid(
                "confirmation_rule",
                "a family declares a ConfirmationRule",
                given=repr(confirmation_rule),
            )
        return Ok(cls(identity=identity, confirmation_rule=confirmation_rule))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this declared family."""
        return {
            "class": "declared-family",
            "identity": self.identity.fp1_identity(),
            "confirmation_rule": self.confirmation_rule.fp1_identity(),
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- the anchor span --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AnchorSpan:
    """The payload geometry of a structure object, frozen at observation (CT-17;
    DEC-0129, DEC-0131, DEC-0105).

    Start and end :class:`~qmf.core.Instant`\\ s plus exact-:class:`~qmf.core.Price`
    bounds (``low <= high``, one instrument). The anchor span is **explicitly permitted
    to precede** ``observed_at`` and is **excluded from every causality test** — its
    instants are never compared against consumed-input evidence times — yet its own
    ordering (``start <= end``) and its bound (``end <= observed_at``) are part of the
    emission invariant. A point sets ``start == end`` and/or ``low == high``.
    """

    start: Instant
    end: Instant
    low: Price
    high: Price

    @classmethod
    def try_create(
        cls, start: object, end: object, low: object, high: object
    ) -> Result[AnchorSpan]:
        """Validate and build an :class:`AnchorSpan`, returning value-or-refusal.

        Both instants must be :class:`~qmf.core.Instant`\\ s with ``start <= end``; both
        bounds must be :class:`~qmf.core.Price`\\ s of the **same instrument** with
        ``low <= high`` (compared as exact rationals across scales). A binary float never
        reaches here — a :class:`~qmf.core.Price` is a scaled integer (FM-6 family).
        """
        if not isinstance(start, Instant):
            return _invalid("start", "an anchor start is an Instant", given=repr(start))
        if not isinstance(end, Instant):
            return _invalid("end", "an anchor end is an Instant", given=repr(end))
        if start.value_ns > end.value_ns:
            return _invalid(
                "start",
                "an anchor span requires start <= end",
                start=start.value_ns,
                end=end.value_ns,
            )
        if not isinstance(low, Price):
            return _invalid("low", "an anchor low bound is a Price", given=repr(low))
        if not isinstance(high, Price):
            return _invalid("high", "an anchor high bound is a Price", given=repr(high))
        if low.instrument != high.instrument:
            return _invalid(
                "high",
                "the anchor price bounds are of one instrument",
                low=repr(low.instrument),
                high=repr(high.instrument),
            )
        if low.as_fraction() > high.as_fraction():
            return _invalid(
                "low",
                "an anchor span requires low <= high",
                low=str(low.as_fraction()),
                high=str(high.as_fraction()),
            )
        return Ok(cls(start=start, end=end, low=low, high=high))

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content for this anchor span.

        Instants are their nanosecond counts (identity numerics are integers) and price
        bounds take CT-01's pinned canonical form through their own ``fp1_identity``.
        """
        return {
            "class": "anchor-span",
            "start_ns": self.start.value_ns,
            "end_ns": self.end.value_ns,
            "low": self.low.fp1_identity(),
            "high": self.high.fp1_identity(),
            "format_version": CONTRACT_FORMAT_VERSION,
        }


# --- the emission invariant -------------------------------------------------


@dataclass(frozen=True, slots=True)
class EmissionWitness:
    """The positive result of a passed emission-invariant check (CT-17; DEC-0129).

    ``chain`` is the ordered, non-decreasing sequence of ``(label, instant_ns)`` pairs
    the invariant verified — ``anchor.start``, ``anchor.end``, ``observed_at``, and the
    lifecycle instants that were present — and ``max_input_ns`` is the maximum evidence
    time of the inputs actually consumed (``None`` when none were). It is a witness that
    the check ran, not a stored field of any object.
    """

    chain: tuple[tuple[str, int], ...]
    max_input_ns: int | None


def check_emission_invariant(
    *,
    anchor: object,
    observed_at: object,
    confirmed_at: object = None,
    invalidated_at: object = None,
    consumed_input_times: object = (),
) -> Result[EmissionWitness]:
    """Check the in-component emission invariant, returning a witness or a refusal (FM-1).

    Enforces, over whatever lifecycle instants are present:
    ``anchor.start <= anchor.end <= observed_at <= confirmed_at <= invalidated_at`` **and**
    ``observed_at >= the maximum evidence time of every input actually consumed`` (CT-17;
    DEC-0129, DEC-0121). Equal instants are legal — equality is consumption, not
    look-ahead (DEC-0106). The anchor span is excluded from the causal-availability test:
    its instants are never compared against consumed-input times. Any violation is an
    ``invalid input`` typed refusal — the interim look-ahead guard, independent of the
    deferred GAP-0016 registration gate. A ``confirmed_at``/``invalidated_at`` of ``None``
    is simply absent (an object carries neither at mint); a present one is validated in
    place in the chain.
    """
    if not isinstance(anchor, AnchorSpan):
        return _invalid("anchor", "the emission invariant checks an AnchorSpan", given=repr(anchor))
    if not isinstance(observed_at, Instant):
        return _invalid("observed_at", "observed-at is an Instant", given=repr(observed_at))

    chain: list[tuple[str, int]] = [
        ("anchor.start", anchor.start.value_ns),
        ("anchor.end", anchor.end.value_ns),
        ("observed_at", observed_at.value_ns),
    ]
    if confirmed_at is not None:
        if not isinstance(confirmed_at, Instant):
            return _invalid(
                "confirmed_at",
                "confirmed-at is an Instant when present (absent until a confirmation "
                "record exists)",
                given=repr(confirmed_at),
            )
        chain.append(("confirmed_at", confirmed_at.value_ns))
    if invalidated_at is not None:
        if not isinstance(invalidated_at, Instant):
            return _invalid(
                "invalidated_at",
                "invalidated-at is an Instant when present (absent until an invalidation "
                "record exists — never a placeholder instant)",
                given=repr(invalidated_at),
            )
        chain.append(("invalidated_at", invalidated_at.value_ns))

    for (earlier_label, earlier_ns), (later_label, later_ns) in pairwise(chain):
        if earlier_ns > later_ns:
            return _invalid(
                later_label,
                "the emission invariant requires a non-decreasing lifecycle chain "
                "anchor.start <= anchor.end <= observed_at <= confirmed_at <= "
                "invalidated_at (FM-1)",
                earlier=[earlier_label, earlier_ns],
                later=[later_label, later_ns],
            )

    resolved = _coerce_instants(consumed_input_times)
    if isinstance(resolved, TypedRefusal):
        return resolved
    max_input_ns = max((instant.value_ns for instant in resolved), default=None)
    if max_input_ns is not None and observed_at.value_ns < max_input_ns:
        return _invalid(
            "observed_at",
            "observed-at precedes the evidence time of a consumed input; a structure "
            "object is never derivable before the newest input it consumed (FM-1)",
            observed_at=observed_at.value_ns,
            max_input_evidence_time=max_input_ns,
        )
    return Ok(EmissionWitness(chain=tuple(chain), max_input_ns=max_input_ns))


# --- the minted structure object --------------------------------------------


def _object_identity_content(
    family: FamilyIdentity,
    parameters: Mapping[str, ExactRational],
    confirmation_rule: ConfirmationRule,
    anchor: AnchorSpan,
    observed_at: Instant,
    evidence_class: EvidenceClass,
) -> dict[str, object]:
    """The structure object's canonical ``fp1`` identity content — every part is
    identity.

    Built identically by :meth:`StructureObject.try_create` and
    :meth:`StructureObject.fp1_identity`. Anchor span, ``observed_at``, and the evidence
    class are identity fields, never occurrence-classified: a structure object is a fact
    about the market at a time, not a computation (DEC-0129, DEC-0131, DEC-0108).
    """
    return {
        "class": "structure-object",
        "family": family.fp1_identity(),
        "parameters": {name: value.fp1_identity() for name, value in parameters.items()},
        "confirmation_rule": confirmation_rule.fp1_identity(),
        "anchor_span": anchor.fp1_identity(),
        "observed_at": observed_at.value_ns,
        "evidence_class": evidence_class.value,
        "format_version": CONTRACT_FORMAT_VERSION,
    }


@dataclass(frozen=True, slots=True)
class StructureObject:
    """A chart-object family instance, minted once at observation and never mutated
    (CT-17; DEC-0129, DEC-0114).

    Every field is identity-bearing: ``family`` (:class:`FamilyIdentity`),
    ``parameters`` (exact rationals), ``confirmation_rule``, ``anchor`` (frozen payload
    geometry), ``observed_at`` (knowledge time — known-at, never event time), and
    ``evidence_class``. The object carries **no** ``WriterId``, sequence, or created-at:
    it returns fingerprintable content and the composition root stamps the registry
    record. State evolves only through separate append-only lifecycle and interaction
    records (later stories); a correction is a new artifact with a ``supersedes`` edge,
    never an in-place edit (FM-3).
    """

    family: FamilyIdentity
    parameters: Mapping[str, ExactRational]
    confirmation_rule: ConfirmationRule
    anchor: AnchorSpan
    observed_at: Instant
    evidence_class: EvidenceClass

    def __post_init__(self) -> None:
        # Snapshot the parameter mapping into a read-only, shared-safe form so a later
        # mutation of the caller's dict can never reach into this frozen, minted-once
        # fact. The values are frozen ExactRationals, so a shallow proxy suffices.
        object.__setattr__(self, "parameters", MappingProxyType(dict(self.parameters)))

    @classmethod
    def try_create(
        cls,
        family: object,
        parameters: object,
        anchor: object,
        observed_at: object,
        evidence_class: object,
        *,
        consumed_input_times: object = (),
    ) -> Result[StructureObject]:
        """Mint a :class:`StructureObject` at observation, returning value-or-refusal.

        ``family`` is a :class:`StructureFamily` (its :class:`FamilyIdentity` and
        :class:`ConfirmationRule` become identity fields of the object); ``parameters`` a
        name->:class:`~qmf.core.ExactRational` mapping; ``anchor`` an :class:`AnchorSpan`;
        ``observed_at`` an :class:`~qmf.core.Instant`; ``evidence_class`` one of the
        closed set. The **emission invariant is checked in-component** before the object
        is minted: ``anchor.start <= anchor.end <= observed_at`` and
        ``observed_at >= the maximum evidence time of every consumed input`` — a violation
        is an ``invalid input`` refusal (FM-1). ``confirmed_at`` and ``invalidated_at``
        are not mint inputs — they arrive as later append-only lifecycle records — so only
        the mint-available part of the chain is checked here.
        """
        if not isinstance(family, StructureFamily):
            return _invalid(
                "family",
                "a structure object is minted against a StructureFamily (exposing an "
                "identity and a confirmation rule)",
                given=repr(family),
            )
        # A runtime_checkable Protocol's isinstance only proves the members EXIST, never
        # their types, so a structurally-valid family may still hand back the wrong types;
        # these checks (routed through object-typed helpers) are meaningful, not redundant.
        identity = _as_family_identity(family.identity)
        if identity is None:
            return _invalid(
                "family",
                "the family's identity is a FamilyIdentity",
                given=repr(family.identity),
            )
        rule = _as_confirmation_rule(family.confirmation_rule)
        if rule is None:
            return _invalid(
                "family",
                "the family's confirmation_rule is a ConfirmationRule",
                given=repr(family.confirmation_rule),
            )
        resolved_parameters = _coerce_parameters(parameters)
        if isinstance(resolved_parameters, TypedRefusal):
            return resolved_parameters
        if not isinstance(anchor, AnchorSpan):
            return _invalid(
                "anchor", "a structure object carries an AnchorSpan", given=repr(anchor)
            )
        if not isinstance(observed_at, Instant):
            return _invalid(
                "observed_at",
                "observed-at is an Instant — the earliest instant the object was "
                "derivable from causally-available data (known-at, never event time)",
                given=repr(observed_at),
            )
        resolved_class = _coerce_evidence_class(evidence_class)
        if resolved_class is None:
            return _invalid(
                "evidence_class",
                "the evidence class is one of the closed set",
                given=repr(evidence_class),
                allowed=[member.value for member in EvidenceClass],
            )
        emission = check_emission_invariant(
            anchor=anchor,
            observed_at=observed_at,
            consumed_input_times=consumed_input_times,
        )
        if is_refusal(emission):
            return emission
        return Ok(
            cls(
                family=identity,
                parameters=resolved_parameters,
                confirmation_rule=rule,
                anchor=anchor,
                observed_at=observed_at,
                evidence_class=resolved_class,
            )
        )

    def fp1_identity(self) -> dict[str, object]:
        """The pinned canonical ``fp1`` identity content — every part is identity.

        Its fingerprint (:meth:`content_fingerprint`) is the object's stable id; two
        sandboxes minting the same fact land on one ``fp1`` and their evidence
        deduplicates. No writer, sequence, or created-at is present — the object is
        fingerprintable content, never a stamped record.
        """
        return _object_identity_content(
            self.family,
            self.parameters,
            self.confirmation_rule,
            self.anchor,
            self.observed_at,
            self.evidence_class,
        )

    def content_fingerprint(self) -> Result[Fingerprint]:
        """The object's ``fp1`` fingerprint, computed in qmf-core (CT-17; DEC-0108).

        Fingerprintable content the composition root stamps into a CT-06 record; the
        library never mints the record itself. Returns value-or-refusal — the identity
        content is canonical by construction, so a refusal here signals a programmer bug
        upstream rather than a routine input error.
        """
        return fingerprint(self.fp1_identity())
