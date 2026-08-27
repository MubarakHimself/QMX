"""L0 static / documentation gates for Epic 4 (qmf-calendar-forex).

G1 extension-boundary / namespace, G2 single-pinned-tzdata, G3 no-shared-noun /
no-own-fingerprint / dependency boundary. These read the extension's pyproject
and source as read-only static evidence (a failing gate is a FINDING, never a
source edit). Each gate names the concrete counter-case that would fail it.

Traces: Story 4.1 b1/b4 (FR-021, CT-02, AR-02/AR-27, FM-5); Story 4.2 b5 /
Story 4.3 b4 (FM-5, no shared noun, no own fp1).
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from qmf.core.chrono import (
    CivilDate,
    Instant,
    SessionWindow,
    TradingDate,
    WriterId,
)

from _epic4_helpers import EXT_ROOT, EXT_SRC

# Shared nouns that qmf-core owns and the extension may NEVER define (FM-5).
_SHARED_NOUN_NAMES = (
    "Venue",
    "Account",
    "Instrument",
    "WriterId",
    "TradingDate",
    "CivilDate",
    "Instant",
    "SessionWindow",
)

# Roster packages the extension must NOT import (it depends only on qmf-core).
_FORBIDDEN_ROSTER_IMPORTS = (
    "qmf.registry",
    "qmf.data",
    "qmf.indicators",
    "qmf.structure",
    "qmf.venue",
    "qmf.risk",
)


def _src_files() -> list[Path]:
    return sorted(p for p in EXT_SRC.glob("*.py"))


def _pyproject_text() -> str:
    return (EXT_ROOT / "pyproject.toml").read_text(encoding="utf-8")


# --- G1: extension-boundary / namespace gate --------------------------------


def test_g1_extension_has_own_pyproject_under_extensions_tree():
    """Counter-case: no pyproject, or the package living under packages/ (roster)."""
    assert (EXT_ROOT / "pyproject.toml").is_file(), "extension needs its own pyproject.toml"
    assert EXT_ROOT.parent.name == "extensions", "extension must live under extensions/, not packages/"


def test_g1_ships_no_namespace_owning_qmf_init():
    """PEP 420 implicit namespace: there is NO src/qmf/__init__.py anywhere in the
    distribution. Counter-case: an __init__.py at src/qmf/ that would claim the
    qmf.* roster namespace (FM-5 boundary)."""
    qmf_dir_init = EXT_ROOT / "src" / "qmf" / "__init__.py"
    assert not qmf_dir_init.exists(), (
        "extension must ship NO src/qmf/__init__.py (PEP 420 implicit namespace); "
        f"found {qmf_dir_init}"
    )
    # The actual submodule package DOES exist (it is the extension's own module).
    assert (EXT_SRC / "__init__.py").is_file()


def test_g1_declares_only_the_forex_submodule_not_a_roster_package():
    """The build declares module-name qmf.calendar_forex and does not redefine a
    roster package. Counter-case: module-name shadowing qmf.core / another roster
    member, or a version tied to the roster lockstep instead of its own ladder."""
    text = _pyproject_text()
    assert 'module-name = "qmf.calendar_forex"' in text, (
        "uv_build module-name must be the off-roster submodule qmf.calendar_forex"
    )
    # Its own SemVer version line exists and is not marked dynamic/lockstep-synced.
    version_match = re.search(r'^\s*version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert version_match is not None, "extension must carry its own explicit SemVer version"
    assert version_match.group(1).strip() != "", "version must be a concrete SemVer string"
    # It must not re-declare qmf-core or any roster module as something it provides.
    assert 'module-name = "qmf.core"' not in text


# --- G2: single-pinned-tzdata gate ------------------------------------------


def test_g2_exactly_one_pinned_tzdata_dependency():
    """Counter-case: zero tzdata deps, two tzdata deps, or a tzdata version RANGE
    instead of an exact pin — any of which breaks 'exactly one pinned tzdata' and
    'no alternate/fallback tzdb path' (AR-27, DEC-0104)."""
    text = _pyproject_text()
    tzdata_pins = re.findall(r'"tzdata\s*([^"]*)"', text)
    assert len(tzdata_pins) == 1, f"expected exactly one tzdata dependency, found {tzdata_pins!r}"
    spec = tzdata_pins[0].strip()
    assert spec.startswith("=="), f"tzdata must be an exact pin (==x.y), not a range: {spec!r}"
    # The pin must have a concrete version after '=='.
    assert re.fullmatch(r"==\s*\d[\w.]*", spec), f"tzdata pin must name a concrete version: {spec!r}"


def test_g2_source_declares_no_alternate_or_fallback_tzdb_path():
    """The extension's pinned-package constant is the ONE tzdb source. Counter-case:
    a second tzdb source or a fallback to the OS/system tzdb path in source."""
    import qmf.calendar_forex as cf

    assert isinstance(cf.PINNED_TZDATA_PACKAGE, str) and cf.PINNED_TZDATA_PACKAGE.strip()
    joined = "\n".join(p.read_text(encoding="utf-8") for p in _src_files()).lower()
    # No fallback to a system/OS tzdb directory (the classic silent-default hole).
    for hole in ("/usr/share/zoneinfo", "fallback", "system tzdb", "except zoneinfonotfounderror"):
        assert hole not in joined, f"source must declare no alternate/fallback tzdb path (found {hole!r})"


# --- G3: no-shared-noun / no-own-fingerprint / dependency gate --------------


@pytest.mark.parametrize("noun", _SHARED_NOUN_NAMES)
def test_g3_extension_defines_no_shared_noun(noun):
    """FM-5: shared nouns are defined only in qmf-core. Counter-case: a
    `class TradingDate` / `class Venue` / ... defined inside the extension source."""
    pattern = re.compile(rf"^\s*class\s+{re.escape(noun)}\b", re.MULTILINE)
    for path in _src_files():
        text = path.read_text(encoding="utf-8")
        assert pattern.search(text) is None, (
            f"extension file {path.name} defines shared noun `class {noun}` — "
            "shared nouns are defined only in qmf-core (FM-5)"
        )


def test_g3_shared_nouns_used_are_the_qmf_core_types():
    """Behavioral corollary: the TradingDate/CivilDate/etc. the provider produces
    ARE the qmf-core classes, not extension-local redefinitions."""
    import qmf.calendar_forex as cf
    from qmf.core.refusal import is_ok

    provider = cf.get_provider()
    assert is_ok(provider)
    # A valid mid-range instant (~2023-11-14 UTC); the exact value is irrelevant here.
    td = provider.value.trading_date_of(Instant(value_ns=1_700_000_000_000_000_000))
    assert is_ok(td)
    assert type(td.value) is TradingDate
    assert type(td.value.date_value) is CivilDate
    assert type(td.value.calendar).__name__ == "CalendarIdentity"
    # sanity: the WriterId / SessionWindow symbols exist only as core imports here
    assert WriterId.__module__ == "qmf.core.chrono"
    assert SessionWindow.__module__ == "qmf.core.chrono"


def test_g3_extension_computes_no_fingerprint_of_its_own():
    """Only qmf-core's fp1 hashes identity. Counter-case: hashlib/sha256 or a local
    canonical serializer in the extension source (it must call qmf.core.fingerprint)."""
    for path in _src_files():
        text = path.read_text(encoding="utf-8")
        low = text.lower()
        assert "hashlib" not in low, f"{path.name} must not hash locally (fp1 is qmf-core's only)"
        assert "sha256" not in low, f"{path.name} must not compute a digest locally"
        assert "def canonical_bytes" not in low, f"{path.name} must not define a local serializer"


def test_g3_extension_imports_only_qmf_core_not_other_roster_packages():
    """Dependency boundary: the extension depends on qmf-core (+ pinned tzdata + stdlib)
    only. Counter-case: an import of qmf.registry / qmf.data / any other roster peer."""
    for path in _src_files():
        text = path.read_text(encoding="utf-8")
        for forbidden in _FORBIDDEN_ROSTER_IMPORTS:
            assert forbidden not in text, (
                f"{path.name} imports {forbidden}; the extension may depend only on qmf-core"
            )
