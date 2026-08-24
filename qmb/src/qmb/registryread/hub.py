"""Passive file-sync hub — dumb storage of as-of sets (B-15, DEC-0165).

The hub is not a service and does not revive the dead DEC-0084 central
registry. It holds already-delivered as-of sets keyed by set fingerprint.
File-sync cadence and where the store lives are node/ops sitting territory;
this library value never reads a clock, never opens a socket, and never
queries a live registry.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, cast

from qmf.core.chrono import Instant
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_ok

from qmb._refuse import invalid, unavailable
from qmb.registryread.as_of import AsOfSet

__all__ = ["HUB_KIND", "PassiveHub"]

# Dumb storage, never a service. The identity token doors and the compiler
# share so they cannot disagree about what the hub is.
HUB_KIND: Final[str] = "passive-storage"


def _coerce_fingerprint(value: object) -> Fingerprint | None:
    if isinstance(value, Fingerprint):
        return value
    parsed = Fingerprint.try_create(value)
    if is_ok(parsed):
        return parsed.value
    return None


@dataclass(frozen=True, slots=True)
class PassiveHub:
    """Dumb passive storage of immutable as-of sets.

    Not an always-on service. Identical-fingerprint arrivals are idempotent
    accepts. A caller who wants a fresher as-of constructs a new hub (or
    :meth:`with_set`) — there is no live query and no cache refresh.
    """

    sets: tuple[AsOfSet, ...]
    _by_fp: Mapping[str, AsOfSet] = field(init=False, compare=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "_by_fp",
            MappingProxyType({item.fingerprint.value: item for item in self.sets}),
        )

    @classmethod
    def try_create(cls, sets: object = ()) -> Result[PassiveHub]:
        """Admit a sequence of as-of sets as dumb storage, returning value-or-refusal."""
        if isinstance(sets, (str, bytes)):
            return invalid(
                "sets",
                "a hub holds a sequence of as-of sets, not a bare string",
                given=repr(sets),
            )
        if sets is None:
            items: tuple[object, ...] = ()
        elif not isinstance(sets, Sequence):
            return invalid(
                "sets",
                "a hub holds a sequence of as-of sets",
                given=repr(type(sets).__name__),
            )
        else:
            items = tuple(cast("Sequence[object]", sets))
        admitted: list[AsOfSet] = []
        seen: dict[str, AsOfSet] = {}
        for item in items:
            if not isinstance(item, AsOfSet):
                return invalid(
                    "sets",
                    "hub storage holds as-of sets, never a live registry query",
                    given=repr(type(item).__name__),
                )
            key = item.fingerprint.value
            existing = seen.get(key)
            if existing is not None:
                if existing == item:
                    continue
                return invalid(
                    "sets",
                    "a true fp1 collision on differing as-of-set bytes is refused "
                    "and alarmed, never overwritten",
                    fingerprint=key,
                )
            seen[key] = item
            admitted.append(item)
        ordered = tuple(
            sorted(
                admitted,
                key=lambda item: (item.registry_as_of.value_ns, item.fingerprint.value),
            )
        )
        return Ok(cls(sets=ordered))

    @property
    def kind(self) -> str:
        """``passive-storage`` — dumb storage, never a service."""
        return HUB_KIND

    def get(self, ref: object) -> Result[AsOfSet]:
        """Return the as-of set named by its set fingerprint."""
        resolved = _coerce_fingerprint(ref)
        if resolved is None:
            return invalid(
                "ref",
                "an as-of set is fetched from the hub by its set fp1",
                given=repr(ref),
            )
        found = self._by_fp.get(resolved.value)
        if found is None:
            return unavailable(
                "ref",
                "the hub has no as-of set under this fingerprint",
                fingerprint=resolved.value,
            )
        return Ok(found)

    def latest(self) -> Result[AsOfSet]:
        """The as-of set with the greatest ``registry_as_of`` instant.

        Tie-break is the set fingerprint string, matching :meth:`try_create`
        sort order. An empty hub is ``unavailable dependency``.
        """
        if not self.sets:
            return unavailable(
                "hub",
                "the hub holds no as-of set yet; the machine has not received one",
            )
        return Ok(self.sets[-1])

    def fresher_than(self, instant: object) -> tuple[AsOfSet, ...]:
        """As-of sets whose ``registry_as_of`` is strictly after ``instant``."""
        if not isinstance(instant, Instant):
            return ()
        return tuple(item for item in self.sets if item.registry_as_of.value_ns > instant.value_ns)

    def with_set(self, as_of_set: object) -> Result[PassiveHub]:
        """Return a hub that also holds ``as_of_set`` (idempotent on the same fp1).

        A new Book reaches the CLI as a fresher as-of set in a new hub value,
        never as a door cache refresh or a live service query (B-15).
        """
        if not isinstance(as_of_set, AsOfSet):
            return invalid(
                "as_of_set",
                "the hub accepts an as-of set value, never a live registry query",
                given=repr(type(as_of_set).__name__),
            )
        existing = self._by_fp.get(as_of_set.fingerprint.value)
        if existing is not None:
            if existing == as_of_set:
                return Ok(self)
            return invalid(
                "as_of_set",
                "a true fp1 collision on differing as-of-set bytes is refused "
                "and alarmed, never overwritten",
                fingerprint=as_of_set.fingerprint.value,
            )
        return PassiveHub.try_create((*self.sets, as_of_set))
