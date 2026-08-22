"""Tier-1 tests for `qmf.calendar_forex`: identity, tzdb pin, benchmark harness."""

from __future__ import annotations

import zoneinfo
from pathlib import Path

import qmf.calendar_forex
import tzdata
from qmf.calendar_forex import _bench, _tzdb
from qmf.core.chrono import CalendarIdentity
from qmf.core.refusal import RefusalCategory, TypedRefusal, is_ok, is_refusal


def test_version_is_semver_0x() -> None:
    assert qmf.calendar_forex.__version__ == "0.1.0"


def test_tzdata_pin_constants_match_installed_package() -> None:
    assert qmf.calendar_forex.PINNED_TZDATA_PACKAGE == "2025.2"
    assert qmf.calendar_forex.PINNED_TZDB_VERSION == "2025b"
    assert tzdata.__version__ == qmf.calendar_forex.PINNED_TZDATA_PACKAGE
    assert tzdata.IANA_VERSION == qmf.calendar_forex.PINNED_TZDB_VERSION


def test_import_forces_tzpath_to_pinned_tzdata() -> None:
    zone_dir = Path(tzdata.__file__).resolve().parent / "zoneinfo"
    assert (str(zone_dir),) == zoneinfo.TZPATH
    assert Path(zoneinfo.TZPATH[0]) == zone_dir


def test_import_verification_ready_exposes_calendar_identity() -> None:
    assert qmf.calendar_forex.provider_ready is True
    identity = qmf.calendar_forex.calendar_identity
    assert isinstance(identity, CalendarIdentity)
    assert identity.rule_set == "forex-17NY"
    assert identity.rule_set_version == "v1"
    assert identity.tzdata_version == "2025b"
    assert qmf.calendar_forex.tzdata_version == "2025b"

    result = qmf.calendar_forex.get_calendar_identity()
    assert is_ok(result) and result.value is identity
    assert is_ok(qmf.calendar_forex.tzdb_verification)


def test_provider_state_clears_provider_on_refusal() -> None:
    refusal = _tzdb.verify_import_tzdb(pinned="1990a")
    assert is_refusal(refusal)
    identity, version, ready = _tzdb.provider_state(refusal)
    assert identity is None
    assert version is None
    assert ready is False


def test_verify_import_tzdb_refuses_mismatch() -> None:
    refusal = _tzdb.verify_import_tzdb(pinned="1990a")
    assert is_refusal(refusal)
    assert isinstance(refusal, TypedRefusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["pinned"] == "1990a"
    assert refusal.context["resolved"] == "2025b"


def test_verify_import_tzdb_refuses_unreadable_zone_dir(tmp_path: Path) -> None:
    empty = tmp_path / "empty-zoneinfo"
    empty.mkdir()
    refusal = _tzdb.verify_import_tzdb(zone_dir=empty)
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refusal.context["field"] == "tzdata_version"
    # Restore the process TZPATH to the real pin after the empty-dir force.
    _tzdb.force_tzpath()


def test_read_resolved_requires_tzdata_zi_on_forced_path(tmp_path: Path) -> None:
    bare = tmp_path / "bare-zoneinfo"
    bare.mkdir()
    # No tzdata.zi on the forced path — do not invent a version from metadata.
    assert _tzdb.read_resolved_tzdb_version(bare) is None
    zone_dir = Path(tzdata.__file__).resolve().parent / "zoneinfo"
    assert _tzdb.read_resolved_tzdb_version(zone_dir) == "2025b"


def test_bench_harness_runs_full_ladder() -> None:
    results = _bench.run()
    assert [result.load for result in results] == list(_bench.DEFAULT_LADDER)
    assert all(result.seconds >= 0.0 for result in results)
    assert all(result.peak_bytes >= 0 for result in results)
    assert all(result.module == "qmf.calendar_forex" for result in results)
