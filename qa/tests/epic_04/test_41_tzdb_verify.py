"""Story 4.1 — import-time tzdb verify-or-refuse (FR-021, CT-02, FM-1).

4.1-U1 (L1) match arm: resolved tzdb == pin -> provider ready, exposing BOTH its
rule-set identity AND the resolved tzdata version for downstream fingerprints.
4.1-U2 (L1) mismatch arm (R-CAL-TZDB): resolved tzdb != pin -> a RETURNED
`unavailable dependency` typed refusal; NOT a usable provider; NO fingerprint
attested against the unverified tzdb.

The mismatch arm drives the extension's own import-time verification seam
(`_tzdb.verify_import_tzdb`, the exact function the package import path runs) with
a REAL resolved-version mismatch: a controlled tzdata directory whose tzdata.zi
header declares a different IANA version. The observation is the returned refusal
category and that provider_state exposes NO identity / NO tzdata version — never a
parsed exception string.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import qmf.calendar_forex as cf
from qmf.calendar_forex._tzdb import provider_state, verify_import_tzdb
from qmf.core.chrono import CalendarIdentity, Instant, verify_tzdb_pin
from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_ok


# --- 4.1-U1 : FM-1 match arm ------------------------------------------------


def test_41_u1_match_arm_provider_ready_and_exposes_identity_and_tzdata(provider):
    """Match arm: the provider is a USABLE CT-02 provider (it actually produces a
    TradingDate), and the verified CalendarIdentity exposes rule-set identity AND
    the resolved tzdata version. Counter-case: get_provider() refuses, or the
    identity carries no tzdata version to ride into fingerprints."""
    identity_result = cf.get_calendar_identity()
    assert is_ok(identity_result), f"matched tzdb must expose a CalendarIdentity: {identity_result!r}"
    identity = identity_result.value
    assert isinstance(identity, CalendarIdentity)
    # Exposes rule-set identity (rule set + version)...
    assert identity.rule_set == "forex-17NY"
    assert isinstance(identity.rule_set_version, str) and identity.rule_set_version.strip()
    # ...AND the resolved tzdata version (non-empty; enters downstream fingerprints).
    assert isinstance(identity.tzdata_version, str) and identity.tzdata_version.strip()
    assert identity.tzdata_version == cf.PINNED_TZDB_VERSION

    # Ready == the provider actually works, observed behaviourally (not via a flag).
    td = provider.trading_date_of(Instant(value_ns=1_700_000_000_000_000_000))
    assert is_ok(td), f"a ready provider must resolve a trading date: {td!r}"
    assert td.value.calendar == identity  # identity carried in-band into its output

    # The resolved tzdata version participates in a real fp1 fingerprint.
    fp = provider.identity_fingerprint()
    assert is_ok(fp) and isinstance(fp.value, Fingerprint)


def test_41_u1_match_arm_verify_import_tzdb_returns_ok_identity_when_versions_agree(tzpath_guard):
    """The extension's own import-time seam returns Ok(CalendarIdentity) when the
    resolved tzdb equals the pin — exercised with a controlled directory whose
    header version matches the pin passed in. This is the positive control that
    shares the SAME machinery as the mismatch arm below (falsifiability: same seam,
    match -> Ok, mismatch -> refusal)."""
    d = Path(tempfile.mkdtemp())
    (d / "tzdata.zi").write_text("# version 2019a\n", encoding="utf-8")
    result = verify_import_tzdb(pinned="2019a", zone_dir=d)
    assert is_ok(result), f"matching resolved==pin must yield Ok(identity): {result!r}"
    assert result.value.tzdata_version == "2019a"
    identity, tzdata_version, ready = provider_state(result)
    assert ready is True and tzdata_version == "2019a" and identity is not None


# --- 4.1-U2 : FM-1 mismatch arm (R-CAL-TZDB) --------------------------------


def test_41_u2_mismatch_arm_returns_unavailable_dependency_refusal(tzpath_guard):
    """Mismatch arm: resolved tzdb (2019a in the controlled dir) != pin (2025b) ->
    a RETURNED `unavailable dependency` TypedRefusal naming pinned and resolved.
    Counter-case that would FAIL this test: verify_import_tzdb returning Ok, or
    raising, or returning any category other than unavailable dependency."""
    d = Path(tempfile.mkdtemp())
    (d / "tzdata.zi").write_text("# version 2019a\n", encoding="utf-8")
    result = verify_import_tzdb(pinned="2025b", zone_dir=d)

    assert isinstance(result, TypedRefusal), f"a pin mismatch must RETURN a refusal, got {result!r}"
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert result.retryability is Retryability.NO
    # Machine-readable context distinguishes pin from resolved (branch on structure).
    ctx = dict(result.context)
    assert ctx.get("pinned") == "2025b"
    assert ctx.get("resolved") == "2019a"


def test_41_u2_mismatch_arm_is_not_a_usable_provider_and_attests_no_tzdb(tzpath_guard):
    """No usable provider and NO fingerprint attested against the unverified tzdb:
    provider_state on the mismatch refusal exposes (identity=None, tzdata=None,
    ready=False) — so there is no CalendarIdentity to fingerprint. Counter-case:
    ready True, or a non-None tzdata version attested for the mismatched tzdb."""
    d = Path(tempfile.mkdtemp())
    (d / "tzdata.zi").write_text("# version 2019a\n", encoding="utf-8")
    result = verify_import_tzdb(pinned="2025b", zone_dir=d)

    identity, tzdata_version, ready = provider_state(result)
    assert ready is False, "a pin mismatch must not become a usable provider"
    assert identity is None, "no CalendarIdentity may be exposed against an unverified tzdb"
    assert tzdata_version is None, "no tzdata version may be attested against an unverified tzdb"


def test_41_u2_core_verify_seam_refuses_on_mismatch():
    """Reinforcement at the fully-public qmf-core seam the extension relies on:
    verify_tzdb_pin(pin, resolved) refuses `unavailable dependency` when they
    differ, so a fingerprint can never attest a tzdb that was not resolved."""
    refusal = verify_tzdb_pin("2025b", "2019a")
    assert isinstance(refusal, TypedRefusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    # Control: equal versions are accepted (both arms of the seam are reachable).
    ok = verify_tzdb_pin("2025b", "2025b")
    assert is_ok(ok) and ok.value == "2025b"
