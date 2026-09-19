"""ContributionHit pin / invoke / tombstone (Story 53.3; SCN-0018).

Pins store ``(qualified_id, package_version, availability_revision)``. Invoke
revalidates against the live published roster and that revision. Disable,
uninstall, or leave-roster yields typed ``unavailable`` or ``tombstone`` —
never another ``package_version``, never another contribution, never a stale
fp1. A matching live tuple may proceed to grant checks later (54/55); the pin
alone is not a grant. In-flight ``pin_leases`` keep the bytes they started
with; GC only when leases are empty and no dependant remains. Pin leases live
on the existing ``plugin_install_records`` projection — no sixth sqlite class
(AR-WF-05; DEC-0429).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Final, Literal, cast

from qma.core.vocabulary.enums import PrincipalClass
from qma.daemon.plugins.loader import LoadedPlugin, PluginLoader, PublishedContribution
from qma.wire.contribution_pin import (
    CONTRIBUTION_PIN_IS_GRANT,
    CONTRIBUTION_PIN_PERSISTENCE_STORE,
    CONTRIBUTION_PIN_SIXTH_STORE_MINTED,
    CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA,
    ContributionPin,
    refuse_contribution_pin_fp1,
    refuse_contribution_pin_grant,
)
from qma.wire.federated_discovery import ContributionHit
from qmf.core import Ok, Result, is_refusal
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal
from qmf.data.store.refusals import invalid_input, policy_rejection

__all__ = [
    "CONTRIBUTION_PIN_IS_GRANT",
    "CONTRIBUTION_PIN_PERSISTENCE_STORE",
    "CONTRIBUTION_PIN_SIXTH_STORE_MINTED",
    "CONTRIBUTION_PIN_WIRED_AT_INSPECT_SHA",
    "PIN_LEASE_STORE",
    "ContributionPinService",
    "DepartedContribution",
    "PackDepartureReceipt",
    "PinInvokeAdmission",
    "PinLease",
    "contribution_tombstone",
    "contribution_unavailable",
]

PIN_LEASE_STORE: Final[str] = CONTRIBUTION_PIN_PERSISTENCE_STORE
AvailabilityOutcome = Literal["unavailable", "tombstone"]
DepartureCause = Literal["disabled", "uninstalled", "left_roster"]


def contribution_unavailable(
    pin: ContributionPin,
    *,
    cause: str,
    **extra: object,
) -> TypedRefusal:
    """Disabled / not-live pin — CT-04 unavailable-dependency, not a new category."""
    context: dict[str, object] = {
        "availability": "unavailable",
        "availability_revision": pin.availability_revision,
        "cause": cause,
        "decision": "DEC-0443",
        "is_grant": False,
        "package_version": pin.package_version,
        "pin_is_grant": False,
        "qualified_id": pin.qualified_id,
        "silent_retarget": False,
        "store": PIN_LEASE_STORE,
    }
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.AFTER_CONDITION,
        context=MappingProxyType(context),
        after_condition_descriptor=(
            "the pinned contribution is live at the same "
            "(qualified_id, package_version, availability_revision)"
        ),
    )


def contribution_tombstone(
    pin: ContributionPin,
    *,
    cause: str,
    **extra: object,
) -> TypedRefusal:
    """Missing / uninstalled pin — CT-04 unavailable-dependency tombstone."""
    context: dict[str, object] = {
        "availability": "tombstone",
        "availability_revision": pin.availability_revision,
        "cause": cause,
        "decision": "DEC-0443",
        "is_grant": False,
        "package_version": pin.package_version,
        "pin_is_grant": False,
        "qualified_id": pin.qualified_id,
        "silent_retarget": False,
        "store": PIN_LEASE_STORE,
    }
    context.update(extra)
    return TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context=MappingProxyType(context),
    )


@dataclass(frozen=True, slots=True)
class PinInvokeAdmission:
    """Live pin may proceed to grant checks — the pin itself is not a grant."""

    pin: ContributionPin
    live: ContributionHit
    is_grant: Literal[False] = False
    grant_checks_pending: Literal[True] = True
    grant_id: None = None

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "grant_checks_pending": True,
                "grant_id": None,
                "is_grant": False,
                "live": dict(self.live.to_payload()),
                "pin": dict(self.pin.to_payload()),
            }
        )


@dataclass(frozen=True, slots=True)
class PinLease:
    """In-flight work already pinned to an instance (FR-WF-11; RC-14)."""

    lease_id: str
    pin: ContributionPin
    plugin_id: str
    package_version: str
    started_bytes: Mapping[str, object]

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "lease_id": self.lease_id,
                "package_version": self.package_version,
                "pin": dict(self.pin.to_payload()),
                "plugin_id": self.plugin_id,
                "started_bytes": dict(self.started_bytes),
                "store": PIN_LEASE_STORE,
            }
        )


@dataclass(frozen=True, slots=True)
class DepartedContribution:
    """A pin tuple that left the live published roster."""

    pin: ContributionPin
    plugin_id: str
    package_version: str
    availability: AvailabilityOutcome
    cause: DepartureCause


@dataclass(frozen=True, slots=True)
class PackDepartureReceipt:
    """Disable / uninstall names dependants and in-flight pin_leases."""

    plugin_id: str
    availability: AvailabilityOutcome
    cause: DepartureCause
    dependants: tuple[str, ...]
    pin_leases: tuple[str, ...]
    bytes_retained: bool
    gc_eligible: bool
    scope_disposed: bool
    data_intact: bool
    rolled_back: Literal[False] = False
    is_grant: Literal[False] = False

    def to_payload(self) -> Mapping[str, object]:
        return MappingProxyType(
            {
                "availability": self.availability,
                "bytes_retained": self.bytes_retained,
                "cause": self.cause,
                "data_intact": self.data_intact,
                "dependants": list(self.dependants),
                "gc_eligible": self.gc_eligible,
                "is_grant": False,
                "pin_leases": list(self.pin_leases),
                "plugin_id": self.plugin_id,
                "rolled_back": False,
                "scope_disposed": self.scope_disposed,
                "store": PIN_LEASE_STORE,
            }
        )


def _row_field(row: object, name: str) -> object:
    if isinstance(row, Mapping):
        return cast("Mapping[str, object]", row).get(name)
    return getattr(row, name, None)


def _hit_from_row(row: object) -> Result[ContributionHit]:
    qualified = _row_field(row, "qualified_id")
    if not isinstance(qualified, str) or qualified.strip() == "":
        return invalid_input(
            "qualified_id",
            "ContributionHit pin requires a qualified_id on the published row",
            given=repr(qualified),
        )
    package_id = _row_field(row, "package_id")
    plugin_id = _row_field(row, "plugin_id")
    return ContributionHit.try_create(
        plugin_id=plugin_id,
        point=_row_field(row, "point"),
        qualified_id=qualified,
        package_id=package_id if package_id is not None else plugin_id,
        package_version=_row_field(row, "package_version"),
        availability_revision=_row_field(row, "availability_revision"),
        availability=_row_field(row, "availability") or "enabled",
    )


@dataclass
class ContributionPinService:
    """Host pin / revalidate / invoke / lease / GC over a PluginLoader."""

    loader: PluginLoader
    _leases: dict[str, PinLease] = field(default_factory=dict[str, PinLease], init=False)
    _departed: dict[tuple[str, str, int], DepartedContribution] = field(
        default_factory=dict[tuple[str, str, int], DepartedContribution],
        init=False,
    )
    _parked: dict[tuple[str, str], tuple[LoadedPlugin, tuple[PublishedContribution, ...]]] = field(
        default_factory=dict[
            tuple[str, str],
            tuple[LoadedPlugin, tuple[PublishedContribution, ...]],
        ],
        init=False,
    )

    @property
    def pin_is_grant(self) -> bool:
        return CONTRIBUTION_PIN_IS_GRANT

    @property
    def sixth_store_minted(self) -> bool:
        return CONTRIBUTION_PIN_SIXTH_STORE_MINTED

    @property
    def pin_lease_store(self) -> str:
        return PIN_LEASE_STORE

    def pin_leases(self) -> tuple[PinLease, ...]:
        return tuple(self._leases.values())

    def leases_for(
        self, plugin_id: str, package_version: str | None = None
    ) -> tuple[PinLease, ...]:
        rows = [lease for lease in self._leases.values() if lease.plugin_id == plugin_id]
        if package_version is not None:
            rows = [lease for lease in rows if lease.package_version == package_version]
        return tuple(rows)

    def started_bytes(self, lease_id: str) -> Mapping[str, object] | None:
        lease = self._leases.get(lease_id)
        if lease is None:
            return None
        return lease.started_bytes

    def inflight_plugin(self, plugin_id: str, package_version: str) -> LoadedPlugin | None:
        parked = self._parked.get((plugin_id, package_version))
        if parked is None:
            return None
        return parked[0]

    def _live_row_for(self, pin: ContributionPin) -> object | None:
        target = pin.as_tuple()
        for row in self.loader.published_contributions():
            qualified = _row_field(row, "qualified_id")
            version = _row_field(row, "package_version")
            revision = _row_field(row, "availability_revision")
            if (qualified, version, revision) == target:
                return row
        return None

    def _other_live_version(self, pin: ContributionPin) -> object | None:
        """A live row with the same qualified_id but a different version/rev.

        Used only to prove silent retarget is refused — never returned as the pin.
        """
        for row in self.loader.published_contributions():
            if _row_field(row, "qualified_id") != pin.qualified_id:
                continue
            version = _row_field(row, "package_version")
            revision = _row_field(row, "availability_revision")
            if (version, revision) != (pin.package_version, pin.availability_revision):
                return row
        return None

    def pin(self, hit: object) -> Result[ContributionPin]:
        """Store the pin tuple from a live ContributionHit. Not a grant."""
        built = ContributionPin.from_hit(hit)
        if is_refusal(built):
            return built
        pin = built.value
        live = self._live_row_for(pin)
        if live is None:
            return contribution_unavailable(pin, cause="not_live")
        mapped = _hit_from_row(live)
        if is_refusal(mapped):
            return mapped
        if mapped.value.availability != "enabled":
            return contribution_unavailable(pin, cause="not_enabled")
        if CONTRIBUTION_PIN_IS_GRANT:
            return refuse_contribution_pin_grant(field="pin")
        payload = pin.to_payload()
        if "fp1" in payload or "digest" in payload:
            return refuse_contribution_pin_fp1(field="pin")
        return Ok(pin)

    def revalidate(self, pin: ContributionPin) -> Result[PinInvokeAdmission]:
        """Revalidate the exact tuple against the live roster (FR-WF-08)."""
        live_row = self._live_row_for(pin)
        if live_row is not None:
            mapped = _hit_from_row(live_row)
            if is_refusal(mapped):
                return mapped
            hit = mapped.value
            if hit.availability == "enabled":
                return Ok(
                    PinInvokeAdmission(
                        pin=pin,
                        live=hit,
                        is_grant=False,
                        grant_checks_pending=True,
                        grant_id=None,
                    )
                )
            if hit.availability in {"disabled", "unavailable"}:
                return contribution_unavailable(pin, cause="live_not_enabled")
            return contribution_tombstone(pin, cause="live_tombstone")
        other = self._other_live_version(pin)
        departed = self._departed.get(pin.as_tuple())
        extra: dict[str, object] = {}
        if other is not None:
            extra["other_package_version"] = _row_field(other, "package_version")
            extra["retarget_refused"] = True
        if departed is not None:
            extra["plugin_id"] = departed.plugin_id
            if departed.availability == "unavailable":
                return contribution_unavailable(pin, cause=departed.cause, **extra)
            return contribution_tombstone(pin, cause=departed.cause, **extra)
        cause = "missing"
        if other is not None:
            cause = "other_version_live"
        return contribution_tombstone(pin, cause=cause, **extra)

    def invoke(self, pin: ContributionPin) -> Result[PinInvokeAdmission]:
        """Invoke revalidates the pin; a live match is still not a grant."""
        admitted = self.revalidate(pin)
        if is_refusal(admitted):
            return admitted
        if admitted.value.is_grant or admitted.value.grant_id is not None:
            return refuse_contribution_pin_grant(field="invoke")
        return admitted

    def acquire_lease(self, pin: ContributionPin, *, lease_id: str) -> Result[PinLease]:
        """Hold started bytes for in-flight work already pinned (FR-WF-11)."""
        if not lease_id.strip():
            return invalid_input("lease_id", "pin_lease id is a non-empty string")
        if lease_id in self._leases:
            return policy_rejection(
                "lease_id",
                "pin_lease id is unique on plugin_install_records (AR-WF-05)",
                lease_id=lease_id,
                store=PIN_LEASE_STORE,
            )
        admitted = self.revalidate(pin)
        if is_refusal(admitted):
            return admitted
        live = admitted.value.live
        published = [
            row
            for row in self.loader.published_contributions()
            if row.plugin_id == live.plugin_id
            and row.qualified_id == pin.qualified_id
            and row.package_version == pin.package_version
            and row.availability_revision == pin.availability_revision
        ]
        started = published[0].to_payload() if published else live.to_payload()
        lease = PinLease(
            lease_id=lease_id,
            pin=pin,
            plugin_id=live.plugin_id,
            package_version=pin.package_version,
            started_bytes=MappingProxyType(dict(started)),
        )
        self._leases[lease_id] = lease
        return Ok(lease)

    def release_lease(self, lease_id: str) -> Result[PinLease]:
        lease = self._leases.pop(lease_id, None)
        if lease is None:
            return invalid_input(
                "lease_id",
                "pin_lease is not held",
                lease_id=lease_id,
                store=PIN_LEASE_STORE,
            )
        return Ok(lease)

    def gc_eligible(self, plugin_id: str, package_version: str | None = None) -> bool:
        leases = self.leases_for(plugin_id, package_version)
        dependants = self.loader.dependants_of(plugin_id)
        return not leases and not dependants

    def gc(self, plugin_id: str, package_version: str) -> Result[bool]:
        """Dispose parked bytes only when leases empty and no dependant remains."""
        if not self.gc_eligible(plugin_id, package_version):
            return policy_rejection(
                "pin_leases",
                "GC is eligible only when pin_leases is empty and no dependant remains "
                "(FR-WF-11; RC-14; SCN-0018 Then 4)",
                plugin_id=plugin_id,
                package_version=package_version,
                pin_leases=[
                    lease.lease_id for lease in self.leases_for(plugin_id, package_version)
                ],
                dependants=list(self.loader.dependants_of(plugin_id)),
                store=PIN_LEASE_STORE,
            )
        parked = self._parked.pop((plugin_id, package_version), None)
        if parked is not None:
            parked[0].exit_stack.close()
        return Ok(True)

    def _mark_departed(
        self,
        plugin_id: str,
        rows: tuple[PublishedContribution, ...],
        *,
        availability: AvailabilityOutcome,
        cause: DepartureCause,
    ) -> None:
        for row in rows:
            if row.qualified_id is None:
                continue
            pin = ContributionPin(
                qualified_id=row.qualified_id,
                package_version=row.package_version,
                availability_revision=row.availability_revision,
            )
            self._departed[pin.as_tuple()] = DepartedContribution(
                pin=pin,
                plugin_id=plugin_id,
                package_version=row.package_version,
                availability=availability,
                cause=cause,
            )
        for key, departed in list(self._departed.items()):
            if departed.plugin_id != plugin_id:
                continue
            self._departed[key] = DepartedContribution(
                pin=departed.pin,
                plugin_id=plugin_id,
                package_version=departed.package_version,
                availability=availability,
                cause=cause,
            )

    def _depart(
        self,
        plugin_id: str,
        *,
        availability: AvailabilityOutcome,
        cause: DepartureCause,
        principal: object,
        command: Literal["plugin.enable", "plugin.install"],
    ) -> Result[PackDepartureReceipt]:
        gated = self.loader.require_operator(command, principal)
        if is_refusal(gated):
            return gated
        loaded = self.loader.get(plugin_id)
        parked_existing = [key for key in self._parked if key[0] == plugin_id]
        published = tuple(
            row for row in self.loader.published_contributions() if row.plugin_id == plugin_id
        )
        if loaded is not None:
            package_version = loaded.manifest.version
        elif parked_existing:
            package_version = parked_existing[0][1]
        else:
            package_version = ""
        leases = self.leases_for(plugin_id, package_version or None)
        dependants = self.loader.dependants_of(plugin_id)
        retain = bool(leases) or bool(dependants)
        self._mark_departed(plugin_id, published, availability=availability, cause=cause)
        if parked_existing and loaded is None:
            bytes_retained = True
            scope_disposed = False
        elif loaded is None:
            bytes_retained = False
            scope_disposed = True
        elif retain:
            detached = self.loader.detach_keep_bytes(plugin_id)
            if detached is None:
                return invalid_input(
                    "plugin_id",
                    "plugin scope could not be parked for in-flight pin_leases",
                    plugin_id=plugin_id,
                )
            parked_plugin, parked_published = detached
            self._parked[(plugin_id, parked_plugin.manifest.version)] = (
                parked_plugin,
                parked_published,
            )
            bytes_retained = True
            scope_disposed = False
        else:
            disabled = self.loader.disable(plugin_id, principal=principal)
            if is_refusal(disabled):
                return disabled
            bytes_retained = False
            scope_disposed = disabled.value.scope_disposed
        gc_ok = self.gc_eligible(plugin_id, package_version or None)
        if cause == "uninstalled" and gc_ok:
            for key in list(self._parked):
                if key[0] == plugin_id:
                    parked = self._parked.pop(key)
                    parked[0].exit_stack.close()
            if self.loader.get(plugin_id) is not None:
                self.loader.unload(plugin_id)
            bytes_retained = False
            scope_disposed = True
        return Ok(
            PackDepartureReceipt(
                plugin_id=plugin_id,
                availability=availability,
                cause=cause,
                dependants=dependants,
                pin_leases=tuple(lease.lease_id for lease in leases),
                bytes_retained=bytes_retained,
                gc_eligible=gc_ok,
                scope_disposed=scope_disposed,
                data_intact=True,
                rolled_back=False,
                is_grant=False,
            )
        )

    def disable(
        self,
        plugin_id: str,
        *,
        principal: object | None = None,
    ) -> Result[PackDepartureReceipt]:
        """Drop the live roster; in-flight leases keep started bytes."""
        actor = PrincipalClass.OPERATOR if principal is None else principal
        return self._depart(
            plugin_id,
            availability="unavailable",
            cause="disabled",
            principal=actor,
            command="plugin.enable",
        )

    def uninstall(
        self,
        plugin_id: str,
        *,
        principal: object | None = None,
    ) -> Result[PackDepartureReceipt]:
        """Leave-roster as tombstone; names dependants and pin_leases."""
        actor = PrincipalClass.OPERATOR if principal is None else principal
        return self._depart(
            plugin_id,
            availability="tombstone",
            cause="uninstalled",
            principal=actor,
            command="plugin.install",
        )
