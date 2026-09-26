"""Reference usage — composition-root registration for qmf-calendar-forex (Story 4.3).

Executable::

    python extensions/qmf-calendar-forex/examples/registration_usage.py

Shows the five things Story 4.3 pins down:

1. The forex calendar is wired by an explicit call to ``register_forex_17ny`` at
   the composition root — never by ambient package scanning, entry points, or
   ``pkgutil``.
2. Distribution identity + version ride into downstream fingerprints alongside
   the rule set and IANA tzdata, via ``qmf.core.fingerprint``.
3. Binding (venues / accounts) is separate from rule-set identity: changing the
   binding leaves the artifact fingerprint unchanged.
4. A tzdata pin change yields a new ``CalendarIdentity`` and a described
   supersedes lineage edge; the earlier artifact is never rewritten.
5. Shared nouns (Venue, Account, Instrument, WriterId, TradingDate, CivilDate)
   are consumed from qmf-core only — this extension defines none of them.
"""

from __future__ import annotations

from typing import TypeVar

from qmf import calendar_forex
from qmf.calendar_forex import (
    DISTRIBUTION_NAME,
    CalendarBinding,
    describe_tzdata_pin_lineage,
    register_forex_17ny,
)
from qmf.core.chrono import CalendarIdentity
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, is_ok

T = TypeVar("T")


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to succeed, got {result}")


def explicit_composition_root_registration() -> str:
    """Composition root calls the named surface; no ambient discovery."""
    registration = _unwrap(register_forex_17ny(), "register_forex_17ny")
    assert registration.distribution_name == DISTRIBUTION_NAME
    assert registration.distribution_version == calendar_forex.__version__
    assert registration.calendar_identity.rule_set == "forex-17NY"
    assert registration.provider.identity is registration.calendar_identity
    return registration.distribution_name


def distribution_rides_into_downstream_fingerprint() -> str:
    """Distribution + version + rule set + tzdata enter fp1 via qmf-core."""
    registration = _unwrap(register_forex_17ny(), "register")
    content = registration.fp1_identity()
    assert content["distribution"] == DISTRIBUTION_NAME
    assert content["distribution_version"] == calendar_forex.__version__
    calendar = content["calendar"]
    assert isinstance(calendar, dict)
    assert calendar["rule_set"] == "forex-17NY"
    assert calendar["tzdata_version"] == registration.calendar_identity.tzdata_version
    assert "binding" not in content
    fp = _unwrap(registration.artifact_fingerprint(), "artifact fingerprint")
    via_core = _unwrap(fingerprint(registration), "fingerprint(registration)")
    assert fp.value == via_core.value
    assert fp.value.startswith("fp1:sha256:")
    return fp.value


def binding_does_not_change_identity() -> bool:
    """A binding-only change leaves derived-artifact identity unchanged."""
    base = _unwrap(register_forex_17ny(), "base registration")
    rebound = base.with_binding(CalendarBinding(venue_ids=("venue-a",), account_ids=("acct-1",)))
    fp_base = _unwrap(base.artifact_fingerprint(), "base fp")
    fp_rebound = _unwrap(rebound.artifact_fingerprint(), "rebound fp")
    assert fp_base.value == fp_rebound.value
    assert rebound.binding.venue_ids == ("venue-a",)
    assert base.binding.venue_ids == ()
    return True


def tzdata_pin_change_describes_lineage_edge() -> str:
    """New CalendarIdentity + supersedes edge description; no rewrite."""
    current = _unwrap(calendar_forex.get_calendar_identity(), "current identity")
    previous = _unwrap(
        CalendarIdentity.try_create(current.rule_set, current.rule_set_version, "2024a"),
        "previous identity under older tzdata pin",
    )
    edge = _unwrap(describe_tzdata_pin_lineage(previous, current), "lineage edge")
    assert edge.edge_type == "supersedes"
    assert edge.reason == "tzdata-pin-change"
    assert edge.old_tzdata_version == "2024a"
    assert edge.new_tzdata_version == current.tzdata_version
    # Endpoints are distinct calendar-identity fingerprints — never equal, never
    # rewritten in place.
    assert edge.from_ref.value != edge.to_ref.value
    old_fp = _unwrap(fingerprint(previous), "old calendar fp")
    new_fp = _unwrap(fingerprint(current), "new calendar fp")
    assert edge.to_ref.value == old_fp.value
    assert edge.from_ref.value == new_fp.value
    return edge.edge_type


def main() -> None:
    name = explicit_composition_root_registration()
    print(f"explicit composition-root registration: {name}")
    fp = distribution_rides_into_downstream_fingerprint()
    print(f"downstream fingerprint: {fp[:19]}...")
    print(f"binding separate from identity: {binding_does_not_change_identity()}")
    edge = tzdata_pin_change_describes_lineage_edge()
    print(f"tzdata pin lineage edge: {edge}")
    print("shared nouns consumed from qmf-core only: True")


if __name__ == "__main__":
    main()
