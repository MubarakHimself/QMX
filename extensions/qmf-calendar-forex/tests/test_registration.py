"""Story 4.3 — composition-root registration, identity participation, lineage, FM-5."""

from __future__ import annotations

import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest
from qmf import calendar_forex
from qmf.calendar_forex import (
    DISTRIBUTION_NAME,
    CalendarBinding,
    ForexCalendarRegistration,
    _tzdb,
    describe_tzdata_pin_lineage,
    register_forex_17ny,
)
from qmf.core.chrono import CalendarIdentity
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Retryability, TypedRefusal, is_ok, is_refusal

_PKG_ROOT = Path(__file__).resolve().parents[1]
_SRC = _PKG_ROOT / "src" / "qmf" / "calendar_forex"
_EXAMPLE = _PKG_ROOT / "examples" / "registration_usage.py"

# Shared nouns defined only in qmf-core (FM-5 / AD-2). This extension may import
# and consume them; it must never define a ClassDef with these names.
_FORBIDDEN_SHARED_NOUNS = frozenset(
    {
        "Venue",
        "Account",
        "Instrument",
        "WriterId",
        "TradingDate",
        "CivilDate",
    }
)

# Ambient discovery surfaces that must never appear in this extension's source.
_FORBIDDEN_DISCOVERY = frozenset(
    {
        "pkgutil",
        "importlib.metadata",
        "entry_points",
        "iter_modules",
        "pkg_resources",
    }
)


def test_register_forex_17ny_is_explicit_named_surface() -> None:
    result = register_forex_17ny()
    assert is_ok(result)
    registration = result.value
    assert isinstance(registration, ForexCalendarRegistration)
    assert registration.distribution_name == DISTRIBUTION_NAME == "qmf-calendar-forex"
    assert registration.distribution_version == calendar_forex.__version__
    assert registration.calendar_identity is calendar_forex.calendar_identity
    assert registration.provider.identity is registration.calendar_identity
    assert registration.binding == CalendarBinding()


def test_register_refuses_when_provider_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    refusal = TypedRefusal(
        category=RefusalCategory.UNAVAILABLE_DEPENDENCY,
        retryability=Retryability.NO,
        context={"field": "tzdata_version", "reason": "pin mismatch"},
    )
    monkeypatch.setattr(_tzdb, "provider_ready", False)
    monkeypatch.setattr(_tzdb, "calendar_identity", None)
    monkeypatch.setattr(_tzdb, "tzdb_verification", refusal)
    result = register_forex_17ny()
    assert is_refusal(result)
    assert result.category is RefusalCategory.UNAVAILABLE_DEPENDENCY


def test_register_refuses_blank_distribution_version() -> None:
    refusal = register_forex_17ny(distribution_version="  ")
    assert is_refusal(refusal)
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context["field"] == "distribution_version"


def test_downstream_fingerprint_includes_distribution_and_calendar() -> None:
    registered = register_forex_17ny()
    assert is_ok(registered)
    registration = registered.value
    content = registration.fp1_identity()
    assert content["class"] == "calendar-extension-artifact"
    assert content["distribution"] == DISTRIBUTION_NAME
    assert content["distribution_version"] == calendar_forex.__version__
    calendar = content["calendar"]
    assert isinstance(calendar, dict)
    assert calendar["rule_set"] == "forex-17NY"
    assert calendar["rule_set_version"] == "v1"
    assert calendar["tzdata_version"] == registration.calendar_identity.tzdata_version
    assert "binding" not in content
    assert "venue" not in content
    assert "account" not in content

    own = registration.artifact_fingerprint()
    via_core = fingerprint(registration)
    assert is_ok(own) and is_ok(via_core)
    assert own.value == via_core.value
    assert own.value.value.startswith("fp1:sha256:")


def test_binding_change_does_not_change_artifact_fingerprint() -> None:
    registered = register_forex_17ny()
    assert is_ok(registered)
    base = registered.value
    rebound = base.with_binding(
        CalendarBinding(venue_ids=("ctrader-demo", "ctrader-live"), account_ids=("a1",))
    )
    assert rebound.binding.venue_ids == ("ctrader-demo", "ctrader-live")
    assert base.binding.venue_ids == ()
    fp_base = base.artifact_fingerprint()
    fp_rebound = rebound.artifact_fingerprint()
    assert is_ok(fp_base) and is_ok(fp_rebound)
    assert fp_base.value == fp_rebound.value
    # Explicit registration with binding at the call site matches with_binding.
    wired_result = register_forex_17ny(binding=rebound.binding)
    assert is_ok(wired_result)
    wired_fp = wired_result.value.artifact_fingerprint()
    assert is_ok(wired_fp)
    assert wired_fp.value == fp_base.value


def test_tzdata_pin_change_yields_new_calendar_identity_and_lineage_edge() -> None:
    current = calendar_forex.calendar_identity
    assert current is not None
    previous = CalendarIdentity.try_create(current.rule_set, current.rule_set_version, "2024a")
    assert is_ok(previous)
    assert previous.value.tzdata_version != current.tzdata_version

    old_fp = fingerprint(previous.value)
    new_fp = fingerprint(current)
    assert is_ok(old_fp) and is_ok(new_fp)
    assert old_fp.value != new_fp.value

    edge = describe_tzdata_pin_lineage(previous.value, current)
    assert is_ok(edge)
    assert edge.value.edge_type == "supersedes"
    assert edge.value.reason == "tzdata-pin-change"
    assert edge.value.old_tzdata_version == "2024a"
    assert edge.value.new_tzdata_version == current.tzdata_version
    assert edge.value.from_ref == new_fp.value
    assert edge.value.to_ref == old_fp.value
    # Old artifact fingerprint remains addressable — never rewritten.
    assert fingerprint(previous.value).value == old_fp.value  # type: ignore[union-attr]


def test_describe_tzdata_pin_lineage_refuses_equal_or_cross_rule_set() -> None:
    current = calendar_forex.calendar_identity
    assert current is not None
    same = describe_tzdata_pin_lineage(current, current)
    assert is_refusal(same)
    assert same.context["field"] == "tzdata_version"

    other = CalendarIdentity.try_create("other-calendar", "v1", "2024a")
    assert is_ok(other)
    cross = describe_tzdata_pin_lineage(other.value, current)
    assert is_refusal(cross)
    assert cross.context["field"] == "rule_set"

    bad = describe_tzdata_pin_lineage("not-an-identity", current)  # type: ignore[arg-type]
    assert is_refusal(bad)
    assert bad.context["field"] == "previous"


def test_extension_source_never_defines_shared_nouns() -> None:
    """FM-5: Venue/Account/Instrument/WriterId/TradingDate/CivilDate stay in core."""
    offenders: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in _FORBIDDEN_SHARED_NOUNS:
                offenders.append(f"{path.name}:{node.lineno}:{node.name}")
    assert offenders == [], f"extension defined shared nouns: {offenders}"


def test_extension_source_never_uses_ambient_discovery() -> None:
    """Registration is explicit — no pkgutil / entry_points / metadata walk."""
    hits: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root = alias.name.split(".")[0]
                    if root in _FORBIDDEN_DISCOVERY or alias.name in _FORBIDDEN_DISCOVERY:
                        hits.append(f"{path.name}:import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                root = mod.split(".")[0] if mod else ""
                if root in _FORBIDDEN_DISCOVERY or mod in _FORBIDDEN_DISCOVERY:
                    hits.append(f"{path.name}:from {mod}")
            elif isinstance(node, ast.Attribute) and node.attr in {
                "entry_points",
                "iter_modules",
            }:
                hits.append(f"{path.name}:{node.lineno}:{node.attr}")
            elif isinstance(node, ast.Name) and node.id in {"pkgutil", "pkg_resources"}:
                hits.append(f"{path.name}:{node.lineno}:{node.id}")
    assert hits == [], f"ambient discovery surface found: {hits}"


def test_pyproject_declares_no_entry_points() -> None:
    text = (_PKG_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.entry-points" not in text
    assert "entry-points" not in text


def test_reference_usage_example_runs_clean() -> None:
    # Workspace install already exposes qmf.calendar_forex + qmf.core; do not
    # invent a PYTHONPATH that could shadow the locked editable installs.
    completed = subprocess.run(
        [sys.executable, str(_EXAMPLE)],
        capture_output=True,
        text=True,
        env=os.environ.copy(),
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert "explicit composition-root registration: qmf-calendar-forex" in completed.stdout
    assert "downstream fingerprint: fp1:sha256:" in completed.stdout
    assert "binding separate from identity: True" in completed.stdout
    assert "tzdata pin lineage edge: supersedes" in completed.stdout
    assert "shared nouns consumed from qmf-core only: True" in completed.stdout
