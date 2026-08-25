"""The single library-owned registry-read port (B-15).

Every consumer — the config compiler, every door's autocomplete — resolves
through this port over one immutable as-of set. No door-side or second cache
exists, so autocomplete and resolution can never answer differently
(DEC-0165). Domain failure is a CT-04 value, returned never raised.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Final

from qmf.core.chrono import Instant
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, TypedRefusal, is_ok, is_refusal
from qmf.registry import KindRegistry, RegistrationRecord

from qmb._refuse import clean_token, invalid, stale, unavailable
from qmb.registryread.as_of import (
    AS_OF_FORMAT_VERSION,
    STATE_KIND,
    AsOfSet,
    DatedPointer,
    RegistryFragment,
)
from qmb.registryread.hub import HUB_KIND, PassiveHub

__all__ = [
    "STALE_EVIDENCE_SEVERITY_KEY",
    "RegistryCompletion",
    "RegistryReadPort",
    "ResolvedRef",
    "port_home",
    "read_port_identity",
]

# Registry key — referenced, never restated as a spine value (DEC-0157, DEC-0165).
STALE_EVIDENCE_SEVERITY_KEY: Final[str] = "qmb_stale_evidence_severity"


def port_home() -> str:
    """The registry types this port reads; one port, no second cache."""
    return f"{KindRegistry.__module__}.{KindRegistry.__qualname__}"


def read_port_identity() -> dict[str, object]:
    """Identity-bearing registry-read fields. Package SemVer is omitted."""
    return {
        "format_version": AS_OF_FORMAT_VERSION,
        "hub": HUB_KIND,
        "port": "library-owned",
        "reads": port_home(),
        "stale_evidence_severity_key": STALE_EVIDENCE_SEVERITY_KEY,
        "state_kind": STATE_KIND,
    }


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


@dataclass(frozen=True, slots=True)
class ResolvedRef:
    """A record or fragment resolved through the one registry-read port.

    The only legal identity cite is :meth:`cite` — the ``fp1`` string. A human
    alias, when present, is display-only UX.
    """

    fingerprint: Fingerprint
    registry_as_of: Instant
    set_fingerprint: Fingerprint
    record: RegistrationRecord | None = None
    fragment: RegistryFragment | None = None
    alias: str | None = None

    def cite(self) -> str:
        """The only legal identity cite: ``fp1``, never ``name@version``."""
        return self.fingerprint.value


@dataclass(frozen=True, slots=True)
class RegistryCompletion:
    """One autocomplete candidate from the B-15 registry-read port.

    ``value`` is what the shell inserts — a human alias, or an explicit
    ``fp1`` after sweep admission. ``cite`` is the only legal identity.
    """

    value: str
    fingerprint: Fingerprint
    kind: str | None
    registry_as_of: Instant
    set_fingerprint: Fingerprint

    def cite(self) -> str:
        """The only legal identity cite: ``fp1``, never ``name@version``."""
        return self.fingerprint.value


@dataclass(frozen=True, slots=True)
class RegistryReadPort:
    """ONE library-owned registry-read port over an immutable as-of set.

    Constructed over a :class:`PassiveHub`. ``bound`` is the as-of this port
    reads; ``frozen`` is set at sweep admission so every trial shares that
    as-of and thereafter resolves by explicit fingerprint, never
    ``name@latest``.
    """

    hub: PassiveHub
    bound: AsOfSet
    stale_evidence_severity: str
    frozen: bool = False

    @classmethod
    def try_create(
        cls,
        hub: object,
        *,
        stale_evidence_severity: object,
        bound: object = None,
        frozen: object = False,
    ) -> Result[RegistryReadPort]:
        """Bind the one read port to a hub as-of set, returning value-or-refusal.

        ``stale_evidence_severity`` is the operator-declared
        ``registry:qmb_stale_evidence_severity`` token — UI-editable, no spine
        value. ``bound`` is an :class:`AsOfSet`, its set fingerprint, or
        omitted (the hub's latest as-of).
        """
        if not isinstance(hub, PassiveHub):
            return invalid(
                "hub",
                "the registry-read port reads as-of sets from a PassiveHub",
                given=repr(type(hub).__name__),
            )
        severity = clean_token(stale_evidence_severity)
        if severity is None:
            return invalid(
                "stale_evidence_severity",
                "severity is the registry:qmb_stale_evidence_severity token "
                "(configurable UI-editable; no spine value)",
                given=repr(stale_evidence_severity),
                severity_key=STALE_EVIDENCE_SEVERITY_KEY,
            )
        if not isinstance(frozen, bool):
            return invalid(
                "frozen",
                "frozen is a bool: True after sweep admission",
                given=repr(frozen),
            )
        bound_set = _resolve_bound(hub, bound)
        if is_refusal(bound_set):
            return bound_set
        return Ok(
            cls(
                hub=hub,
                bound=bound_set.value,
                stale_evidence_severity=severity,
                frozen=frozen,
            )
        )

    def admit_batch(self) -> RegistryReadPort:
        """Freeze this port's as-of for every trial in a sweep (B-15, SC-11).

        After admission, :meth:`resolve` accepts explicit ``fp1`` only — never
        an alias and never ``name@latest``. Fresher as-of sets that arrive on
        the hub are not consulted; the sweep is honest about the as-of it
        stamped into the sweep label.
        """
        if self.frozen:
            return self
        return replace(self, frozen=True)

    def enumerate_aliases(self, *, kind: object = None) -> tuple[DatedPointer, ...]:
        """Dated pointers in the bound as-of, sorted — door autocomplete (B-1, B-15).

        ``kind`` is an optional registry record kind (``book-definition``,
        ``bms-definition``, ``bot-definition``). ``None`` enumerates every
        dated pointer. A blank or non-token ``kind`` yields no pointers.
        """
        pointers = tuple(sorted(self.bound.pointers, key=lambda pointer: pointer.alias))
        if kind is None:
            return pointers
        token = clean_token(kind)
        if token is None:
            return ()
        return tuple(
            pointer for pointer in pointers if _record_kind(self.bound, pointer.target) == token
        )

    def complete(
        self,
        incomplete: object = "",
        *,
        kind: object = None,
    ) -> tuple[RegistryCompletion, ...]:
        """Autocomplete candidates this port would also resolve (B-1, B-15).

        The config compiler calls :meth:`resolve` on this same port. Candidates
        are those refs ``resolve`` accepts, filtered by prefix and optional
        record kind. A frozen sweep port no longer offers aliases — after
        admission, fragments resolve by explicit fingerprint (SC-11).
        """
        if incomplete is None:
            prefix = ""
        elif isinstance(incomplete, str):
            prefix = incomplete
        else:
            return ()
        if kind is None:
            token: str | None = None
        else:
            token = clean_token(kind)
            if token is None:
                return ()
        if self.frozen:
            return self._complete_fingerprints(prefix, token)
        return self._complete_aliases(prefix, token)

    def resolve(self, ref: object) -> Result[ResolvedRef]:
        """Resolve ``ref`` through this port, returning the record/fragment or a refusal.

        A human alias is legal only before sweep admission and resolves to the
        dated pointer's ``fp1``. ``name@version`` / ``name@latest`` is always
        ``invalid input``. A ref a fresher as-of shows superseded is AD-11
        ``stale evidence`` at ``qmb_stale_evidence_severity`` — returned, not
        raised (FM-7). After :meth:`admit_batch`, ``ref`` must be an explicit
        fingerprint present in the frozen as-of.
        """
        parsed = _parse_ref(ref, frozen=self.frozen)
        if is_refusal(parsed):
            return parsed
        fingerprint, alias = parsed.value
        if fingerprint is None:
            pointer = self.bound.pointer_for(alias)
            if pointer is None:
                return unavailable(
                    "ref",
                    "no dated pointer in this as-of set names that alias",
                    alias=alias,
                )
            fingerprint = pointer.target
            alias_used = pointer.alias
        else:
            alias_used = alias
        member = self.bound.get(fingerprint)
        if member is None:
            return unavailable(
                "ref",
                "this as-of set has no record or fragment under that fp1",
                fingerprint=fingerprint.value,
            )
        stale_hit = self._stale_if_superseded(fingerprint)
        if stale_hit is not None:
            return stale_hit
        record = member if isinstance(member, RegistrationRecord) else None
        fragment = member if isinstance(member, RegistryFragment) else None
        return Ok(
            ResolvedRef(
                fingerprint=fingerprint,
                registry_as_of=self.bound.registry_as_of,
                set_fingerprint=self.bound.fingerprint,
                record=record,
                fragment=fragment,
                alias=alias_used,
            )
        )

    def _stale_if_superseded(self, fingerprint: Fingerprint) -> TypedRefusal | None:
        """AD-11 stale-evidence when a fresher (or bound) as-of shows superseded.

        A frozen sweep port does not consult later as-of sets — the as-of was
        admitted for every trial. An unfrozen port refuses a ref the bound
        as-of or any fresher hub as-of shows superseded.
        """
        if self.frozen:
            return None
        if self.bound.is_superseded(fingerprint):
            head = self.bound.current_head(fingerprint)
            return self._stale_refusal(
                fingerprint,
                fresher=self.bound,
                head=head.value if is_ok(head) else None,
            )
        for fresher in self.hub.fresher_than(self.bound.registry_as_of):
            if fresher.is_superseded(fingerprint):
                head = fresher.current_head(fingerprint)
                return self._stale_refusal(
                    fingerprint,
                    fresher=fresher,
                    head=head.value if is_ok(head) else None,
                )
        return None

    def _stale_refusal(
        self,
        fingerprint: Fingerprint,
        *,
        fresher: AsOfSet,
        head: Fingerprint | None,
    ) -> TypedRefusal:
        """Build the FM-7 stale-evidence refusal carrying the severity key."""
        context_head = head.value if head is not None else None
        return stale(
            "ref",
            "a fresher as-of set shows this ref superseded; re-resolve against "
            "the current as-of set, never mutate the ref (FM-7, DEC-0165)",
            severity=self.stale_evidence_severity,
            severity_key=STALE_EVIDENCE_SEVERITY_KEY,
            fingerprint=fingerprint.value,
            current_head=context_head,
            bound_registry_as_of=self.bound.registry_as_of.value_ns,
            bound_set_fingerprint=self.bound.fingerprint.value,
            fresher_registry_as_of=fresher.registry_as_of.value_ns,
            fresher_set_fingerprint=fresher.fingerprint.value,
        )

    def _complete_aliases(
        self,
        prefix: str,
        kind: str | None,
    ) -> tuple[RegistryCompletion, ...]:
        """Offer aliases ``resolve`` accepts under the bound as-of."""
        out: list[RegistryCompletion] = []
        for pointer in self.enumerate_aliases(kind=kind):
            if prefix and not pointer.alias.startswith(prefix):
                continue
            resolved = self.resolve(pointer.alias)
            if is_refusal(resolved):
                continue
            out.append(
                _completion(
                    pointer.alias,
                    resolved.value.fingerprint,
                    _record_kind(self.bound, resolved.value.fingerprint),
                    self.bound,
                )
            )
        return tuple(out)

    def _complete_fingerprints(
        self,
        prefix: str,
        kind: str | None,
    ) -> tuple[RegistryCompletion, ...]:
        """After admission, offer explicit ``fp1`` tokens ``resolve`` accepts."""
        candidates: list[tuple[str, Fingerprint, str | None]] = []
        for record in self.bound.records:
            rec_kind = record.kind
            if kind is not None and rec_kind != kind:
                continue
            candidates.append((record.stable_id.value, record.stable_id, rec_kind))
        for fragment in self.bound.fragments:
            rec_kind = _record_kind(self.bound, fragment.source_fp1)
            if kind is not None and rec_kind != kind:
                continue
            candidates.append((fragment.fingerprint.value, fragment.fingerprint, rec_kind))
        out: list[RegistryCompletion] = []
        for value, fingerprint, rec_kind in sorted(candidates, key=lambda item: item[0]):
            if prefix and not value.startswith(prefix):
                continue
            resolved = self.resolve(fingerprint)
            if is_refusal(resolved):
                continue
            out.append(_completion(value, fingerprint, rec_kind, self.bound))
        return tuple(out)


def _completion(
    value: str,
    fingerprint: Fingerprint,
    kind: str | None,
    bound: AsOfSet,
) -> RegistryCompletion:
    """Stamp a candidate with the bound as-of identity."""
    return RegistryCompletion(
        value=value,
        fingerprint=fingerprint,
        kind=kind,
        registry_as_of=bound.registry_as_of,
        set_fingerprint=bound.fingerprint,
    )


def _record_kind(bound: AsOfSet, fingerprint: Fingerprint) -> str | None:
    """Record kind for a pointer target, walking a fragment to its source."""
    member = bound.get(fingerprint)
    if isinstance(member, RegistrationRecord):
        return member.kind
    if isinstance(member, RegistryFragment):
        source = bound.get(member.source_fp1)
        if isinstance(source, RegistrationRecord):
            return source.kind
    return None


def _resolve_bound(hub: PassiveHub, bound: object) -> Result[AsOfSet]:
    """Resolve the as-of this port will read."""
    if bound is None:
        return hub.latest()
    if isinstance(bound, AsOfSet):
        found = hub.get(bound.fingerprint)
        if is_refusal(found):
            return unavailable(
                "bound",
                "the bound as-of set is not in this hub; deliver it through the hub first",
                fingerprint=bound.fingerprint.value,
            )
        return Ok(bound)
    resolved = _coerce_fingerprint(bound)
    if resolved is None:
        return invalid(
            "bound",
            "the port binds an AsOfSet, a set fp1, or omits bound to use the hub's latest",
            given=repr(bound),
        )
    return hub.get(resolved)


def _parse_ref(ref: object, *, frozen: bool) -> Result[tuple[Fingerprint | None, str | None]]:
    """Split ``ref`` into (fingerprint, alias). ``name@version`` is always refused."""
    if isinstance(ref, Fingerprint):
        return Ok((ref, None))
    token = clean_token(ref)
    if token is None:
        return invalid(
            "ref",
            "resolve takes an fp1 fingerprint or a human alias; name@version is not a cite",
            given=repr(ref),
        )
    if "@" in token:
        return invalid(
            "ref",
            "name@version is not a legal identity cite; after admission, fragments "
            "resolve by explicit fingerprint, never name@latest (B-13, B-15)",
            given=token,
        )
    parsed = Fingerprint.try_create(token)
    if is_ok(parsed):
        return Ok((parsed.value, None))
    if frozen:
        return invalid(
            "ref",
            "after batch admission, fragments resolve by explicit fingerprint, "
            "never name@latest (SC-11, B-15)",
            given=token,
        )
    return Ok((None, token))
