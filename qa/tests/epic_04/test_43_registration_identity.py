"""Story 4.3 — explicit registration + identity vs binding (FR-021, CT-02/05/07).

4.3-U1 (L1): the provider is made available ONLY via the named composition-root
             surface (register_forex_17ny), never ambient package scanning; the
             distribution identity + version are recorded and ride into fp1.
4.3-C1 (L2, R-CAL-IDENTITY): a fingerprint over a calendar-derived artifact
             incorporates ONLY the rule set + pinned tzdata; a binding-only change
             (which venues/accounts use it) leaves derived-artifact identity
             unchanged (binding != identity).
"""

from __future__ import annotations

import ast

import qmf.calendar_forex as cf
from qmf.calendar_forex import CalendarBinding
from qmf.core.chrono import CalendarIdentity, Instant
from qmf.core.fingerprint import Fingerprint, fingerprint
from qmf.core.refusal import is_ok

from _epic4_helpers import EXT_ROOT, EXT_SRC


# --- 4.3-U1 : explicit named registration, never ambient --------------------


def test_43_u1_registration_via_named_surface_records_distribution_identity():
    """register_forex_17ny() returns a working registration whose distribution
    identity + version are recorded and ride into the downstream fp1 identity
    content. Counter-case: no distribution identity in the fingerprinted content."""
    reg_result = cf.register_forex_17ny()
    assert is_ok(reg_result), f"named registration must succeed on a ready provider: {reg_result!r}"
    reg = reg_result.value

    assert reg.distribution_name == "qmf-calendar-forex"
    assert isinstance(reg.distribution_version, str) and reg.distribution_version.strip()

    # The registered provider actually works (registration yields a usable handle).
    td = reg.provider.trading_date_of(Instant(value_ns=1_700_000_000_000_000_000))
    assert is_ok(td)

    # Distribution identity + version are IN the fingerprinted identity content.
    identity_content = reg.fp1_identity()
    assert identity_content.get("distribution") == "qmf-calendar-forex"
    assert identity_content.get("distribution_version") == reg.distribution_version
    assert "calendar" in identity_content  # rule set + tzdata ride alongside

    fp = reg.artifact_fingerprint()
    assert is_ok(fp) and isinstance(fp.value, Fingerprint)


def _ambient_discovery_uses(source: str) -> list[str]:
    """Return the ambient-discovery constructs ACTUALLY used in `source`, parsed via
    ast so a mention in a docstring or comment (the source says it does NOT scan) is
    never counted. Detects: imports of pkgutil / pkg_resources; calls to
    entry_points / iter_entry_points / walk_packages / iter_modules; and a
    __init_subclass__ auto-registration hook."""
    tree = ast.parse(source)
    found: list[str] = []
    banned_import_modules = {"pkgutil", "pkg_resources"}
    banned_call_names = {"entry_points", "iter_entry_points", "walk_packages", "iter_modules"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in banned_import_modules:
                    found.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").split(".")[0]
            if root in banned_import_modules:
                found.append(f"from {node.module} import ...")
            for alias in node.names:
                if alias.name in banned_call_names:
                    found.append(f"from {node.module} import {alias.name}")
        elif isinstance(node, ast.Call):
            fn = node.func
            name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
            if name in banned_call_names:
                found.append(f"call {name}()")
        elif isinstance(node, ast.FunctionDef) and node.name == "__init_subclass__":
            found.append("def __init_subclass__")
    return found


def test_43_u1_no_ambient_discovery_declared_or_implemented():
    """'Never by ambient package scanning': the extension declares NO plugin
    entry-points and its source USES no ambient-discovery machinery (parsed via ast,
    so the docstrings that say it must never scan are not miscounted). Counter-case:
    a [project.entry-points] group, or an actual pkgutil / entry_points /
    __init_subclass__ auto-registration in source."""
    pyproject = (EXT_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert "[project.entry-points" not in pyproject, "extension must declare no plugin entry-points"

    for path in sorted(EXT_SRC.glob("*.py")):
        uses = _ambient_discovery_uses(path.read_text(encoding="utf-8"))
        assert uses == [], f"{path.name} uses ambient-discovery constructs: {uses}"

    # The named surface is a real callable the composition root invokes explicitly.
    assert callable(cf.register_forex_17ny)


def test_43_u1_each_registration_call_is_explicit_and_independent():
    """Explicit wiring: each call to the named surface returns its own handle;
    importing the package does not auto-populate an ambient global registry.
    Counter-case: registration being a shared global mutated at import time."""
    a = cf.register_forex_17ny()
    b = cf.register_forex_17ny()
    assert is_ok(a) and is_ok(b)
    assert a.value is not b.value  # a fresh explicit handle per call, not a global singleton


# --- 4.3-C1 : identity = rule-set + tzdata; binding is separate -------------


def test_43_c1_binding_only_change_leaves_derived_identity_unchanged():
    """A change to the binding (which venues/accounts use the calendar), with the
    rule set unchanged, does NOT change the derived-artifact fingerprint. Counter-
    case: binding leaking into identity so the fingerprint moves on a venue swap."""
    reg = cf.register_forex_17ny().value
    base_fp = reg.artifact_fingerprint()
    assert is_ok(base_fp)

    rebound = reg.with_binding(CalendarBinding(venue_ids=("venue-A",), account_ids=("acct-9",)))
    rebound_fp = rebound.artifact_fingerprint()
    assert is_ok(rebound_fp)
    assert rebound_fp.value == base_fp.value, "a binding-only change must not change identity"

    # Registering WITH a binding at call time is likewise identity-neutral.
    with_binding = cf.register_forex_17ny(binding=CalendarBinding(venue_ids=("venue-Z",))).value
    assert with_binding.artifact_fingerprint().value == base_fp.value

    # And binding fields never appear anywhere in the fingerprinted identity content.
    content_blob = str(reg.fp1_identity()).lower()
    assert "venue" not in content_blob and "account" not in content_blob and "binding" not in content_blob


def test_43_c1_identity_moves_only_on_rule_set_or_tzdata_change():
    """The sharp discriminator: the fingerprint is sensitive to the rule set and
    the pinned tzdata version, and to nothing else. Two identities differing only
    in tzdata -> different fp; differing only in rule set -> different fp."""
    base = CalendarIdentity.try_create("forex-17NY", "v1", "2025b").value
    diff_tzdata = CalendarIdentity.try_create("forex-17NY", "v1", "2026a").value
    diff_rules = CalendarIdentity.try_create("other-cal", "v1", "2025b").value

    fp_base = fingerprint(base)
    fp_tz = fingerprint(diff_tzdata)
    fp_rules = fingerprint(diff_rules)
    assert is_ok(fp_base) and is_ok(fp_tz) and is_ok(fp_rules)
    assert fp_base.value != fp_tz.value, "a tzdata change must change identity"
    assert fp_base.value != fp_rules.value, "a rule-set change must change identity"

    # Control: identical identity content -> identical fingerprint (fp1 is a single
    # canonical implementation; equal semantic input replays to equal fp).
    again = CalendarIdentity.try_create("forex-17NY", "v1", "2025b").value
    assert fingerprint(again).value == fp_base.value
