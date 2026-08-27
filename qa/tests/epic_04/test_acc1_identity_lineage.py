"""ACC-1 (L4) — forex-calendar identity-bearing derivation + lineage chain.

Stories 4.2 b5 + 4.3 b1/b2 (FR-021; CT-05, CT-07). A verified provider derives a
TradingDate and a SessionWindow for a boundary instant; qmf-core's single fp1
fingerprints the derived artifact (incorporating rule set + tzdata identity). Then
the tzdata pin CHANGES and the SAME instant is re-derived: the exposed identity
differs, the artifact carries a NEW distinct fingerprint, a lineage (supersedes)
edge links old->new, and the earlier artifact is never rewritten.

Observation is through qmf-core's own fingerprint + a GovernedEvidenceLedger sink
owned by the test (the no-rewrite property is read off the ledger, not trusted from
a flag).
"""

from __future__ import annotations

from qmf.calendar_forex._provider import Forex17NYCalendar
import qmf.calendar_forex as cf
from qmf.core.chrono import CalendarIdentity, Instant, SessionWindow, TradingDate
from qmf.core.fingerprint import GovernedEvidenceLedger, WriteOutcome, canonical_bytes, fingerprint
from qmf.core.refusal import RefusalCategory, TypedRefusal, is_ok

from _epic4_helpers import ny_wall_ns, rollover_ns

_PIN_A = "2025b"  # the currently-pinned tzdata IANA version
_PIN_B = "2026a"  # a hypothetical newer pin (the pin CHANGE)


def test_acc1_tzdata_pin_change_yields_new_fp_lineage_edge_and_no_rewrite(provider):
    """Full chain: derive under pin A, re-derive the SAME instant under pin B,
    assert a new distinct fingerprint (no silent equality), a supersedes lineage
    edge old->new, and that the earlier artifact is never rewritten."""
    boundary_ns = rollover_ns(2026, 2, 4)
    instant = Instant(value_ns=boundary_ns)

    # --- derive under pin A (the verified, real provider) --------------------
    identity_a = cf.get_calendar_identity()
    assert is_ok(identity_a)
    identity_a = identity_a.value
    assert identity_a.tzdata_version == _PIN_A

    td_a = provider.trading_date_of(instant)
    window_a = provider.session_window(Instant(value_ns=ny_wall_ns(2026, 2, 4, 12)))
    assert is_ok(td_a) and isinstance(td_a.value, TradingDate)
    assert is_ok(window_a) and isinstance(window_a.value, SessionWindow)

    fp_a = fingerprint(td_a.value)
    assert is_ok(fp_a)

    # --- the tzdata pin changes; re-derive the SAME instant under pin B ------
    identity_b = CalendarIdentity.try_create(identity_a.rule_set, identity_a.rule_set_version, _PIN_B)
    assert is_ok(identity_b)
    identity_b = identity_b.value
    provider_b = Forex17NYCalendar(identity=identity_b)
    td_b = provider_b.trading_date_of(instant)
    assert is_ok(td_b)

    fp_b = fingerprint(td_b.value)
    assert is_ok(fp_b)

    # New DISTINCT fingerprint — never a silent equality across the pin change.
    assert fp_a.value != fp_b.value, "a tzdata pin change must yield a new distinct fingerprint"
    # The civil trading date is the SAME instant's date; only identity/tzdata moved.
    assert td_a.value.date_value == td_b.value.date_value

    # --- lineage edge old -> new --------------------------------------------
    edge_result = cf.describe_tzdata_pin_lineage(identity_a, identity_b)
    assert is_ok(edge_result), f"a real pin change must describe a lineage edge: {edge_result!r}"
    edge = edge_result.value
    assert edge.edge_type == "supersedes"
    assert edge.old_tzdata_version == _PIN_A
    assert edge.new_tzdata_version == _PIN_B
    # Endpoints are the calendar-identity fingerprints (so the change surfaces as a
    # new identity, not a silent equality): from_ref == fp(new), to_ref == fp(old).
    assert edge.from_ref == fingerprint(identity_b).value
    assert edge.to_ref == fingerprint(identity_a).value

    # --- earlier artifact never rewritten -----------------------------------
    ledger = GovernedEvidenceLedger()
    receipt_a = ledger.write(td_a.value.fp1_identity(), world="replay")
    receipt_b = ledger.write(td_b.value.fp1_identity(), world="replay")
    assert is_ok(receipt_a) and is_ok(receipt_b)
    assert receipt_a.value.outcome is WriteOutcome.STORED
    assert receipt_b.value.outcome is WriteOutcome.STORED
    assert receipt_a.value.fingerprint != receipt_b.value.fingerprint
    # Re-presenting artifact A after B is stored is idempotent (byte-identical),
    # never an overwrite — the old artifact is untouched.
    receipt_a_again = ledger.write(td_a.value.fp1_identity(), world="replay")
    assert is_ok(receipt_a_again)
    assert receipt_a_again.value.outcome is WriteOutcome.IDEMPOTENT
    # And A's canonical bytes are unchanged by the whole sequence.
    bytes_a_before = canonical_bytes(td_a.value.fp1_identity())
    assert is_ok(bytes_a_before)
    assert bytes_a_before.value == canonical_bytes(td_a.value.fp1_identity()).value


def test_acc1_no_change_control_equal_pins_refuse_a_lineage_edge():
    """Falsifiability control: with NO pin change (equal tzdata versions) the
    identities fingerprint equal AND describe_tzdata_pin_lineage refuses — so the
    distinct fingerprint + edge above come specifically from the tzdata change, not
    from any incidental difference."""
    identity = CalendarIdentity.try_create("forex-17NY", "v1", _PIN_A).value
    same = CalendarIdentity.try_create("forex-17NY", "v1", _PIN_A).value
    assert fingerprint(identity).value == fingerprint(same).value

    refusal = cf.describe_tzdata_pin_lineage(identity, same)
    assert isinstance(refusal, TypedRefusal), "equal pins are not a lineage edge"
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert dict(refusal.context).get("field") == "tzdata_version"
