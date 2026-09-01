"""QMX-F064 structural gates absorbed by Story 25.13 (node + venue hygiene).

Four cheap structural clauses the Epic-8 L6 review flagged as UNPROVEN:
(a) Spotware SDK / Twisted / OpenApiPy ban across venue sources and pyprojects
(b) tier-1 secret-scan rides ``poe check``
(c) undeclared order-parameter refusal against CT-18 ``order_parameter_subset``
(d) per-writer sequence resets only on boot, durable through the observation sink
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import _helpers as H
import tomllib
from qmf.core import RefusalCategory, is_ok, is_refusal
from qmf.venue import (
    SEQUENCE_CURSOR_RECORD_CLASS,
    ConnectionManager,
    OrderType,
    TimeInForce,
    venue_writer_id,
)

_ROOT = Path(__file__).resolve().parents[3]
_VENUE_SRC = _ROOT / "packages" / "qmf-venue" / "src" / "qmf" / "venue"
_BANNED = ("twisted", "ctrader_open_api", "openapipy", "spotware", "openapi_client")


def _imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def test_f064_a_spotware_twisted_openapi_banned_in_venue_and_pyprojects() -> None:
    """8.2-AC2 / AR-07: no Spotware SDK, Twisted, or OpenApiPy in sources or deps."""
    offending_imports: list[str] = []
    for path in sorted(_VENUE_SRC.rglob("*.py")):
        for imported in _imported_modules(path):
            root = imported.split(".", 1)[0].lower()
            if root in _BANNED or any(token in imported.lower() for token in _BANNED):
                offending_imports.append(f"{path.relative_to(_ROOT)}:{imported}")
    assert offending_imports == []

    manifests = sorted((_ROOT / "packages").glob("*/pyproject.toml")) + sorted(
        (_ROOT / "extensions").glob("*/pyproject.toml")
    )
    manifests.append(_ROOT / "qmn" / "pyproject.toml")
    dep_hits: list[str] = []
    for manifest in manifests:
        data = tomllib.loads(manifest.read_text(encoding="utf-8"))
        deps = data.get("project", {}).get("dependencies", [])
        for dep in deps:
            name = dep.split("==")[0].split(">=")[0].split("[")[0].strip().lower()
            if name in {"twisted", "ctrader-open-api", "openapipy"} or "spotware" in name:
                dep_hits.append(f"{manifest.relative_to(_ROOT)}:{dep}")
    assert dep_hits == []


def test_f064_b_tier1_secret_scan_rides_poe_check() -> None:
    """8.3-AC1 / NFR-05: ``poe check`` sequence includes secret-scan."""
    config = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    tasks = config["tool"]["poe"]["tasks"]
    assert "secret-scan" in tasks
    assert "secret-scan" in tasks["check"]["sequence"]


def test_f064_c_undeclared_order_parameter_is_unsupported() -> None:
    """CT-18/CT-19: undeclared order type / TIF is unsupported-capability, never emulated."""
    market_only = H.build_declaration(
        order_parameter_subset={
            "order_types": ["market"],
            "time_in_force": ["good-till-cancel"],
        }
    )
    admitted = market_only.order_parameter(
        order_type=OrderType.MARKET, time_in_force=TimeInForce.GOOD_TILL_CANCEL
    )
    assert is_ok(admitted)

    limit = market_only.order_parameter(order_type=OrderType.LIMIT)
    assert is_refusal(limit)
    assert limit.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert limit.context["field"] == "order_type"

    ioc = market_only.order_parameter(time_in_force=TimeInForce.IMMEDIATE_OR_CANCEL)
    assert is_refusal(ioc)
    assert ioc.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    assert ioc.context["field"] == "time_in_force"


def test_f064_d_sequence_resets_only_on_boot_cursor_durable_through_obs_sink() -> None:
    """CT-19: sequence continues across reconnect, resets on new boot, cursor durable."""
    v = H.mk_venue()
    a = H.mk_account(v)
    obs = H.RecordingSink()
    cm = H.build_connection_manager(v, a, observation_sink=obs)

    k1 = H.ok(cm.next_command_key(H.mk_instant(1000)))
    k2 = H.ok(cm.next_command_key(H.mk_instant(1001)))
    assert k1.sequence < k2.sequence

    cursor_emits = [
        payload
        for kind, payload in obs.calls
        if kind == "emit"
        and isinstance(payload, dict)
        and payload.get("class") == SEQUENCE_CURSOR_RECORD_CLASS
    ]
    assert len(cursor_emits) == 2
    assert cursor_emits[-1]["boot_epoch_id"] == H.BOOT_EPOCH
    assert cursor_emits[-1]["next_sequence"] == cm.next_sequence

    # Reconnect never resets the per-writer sequence.
    before = H.ok(cm.note_reconnect())
    assert before == cm.next_sequence
    k3 = H.ok(cm.next_command_key(H.mk_instant(1002)))
    assert k3.sequence == k2.sequence + 1

    # Recovering the durable cursor within the same boot continues, never rewinds.
    recovered = H.ok(cm.recover_sequence_cursor(cm.next_sequence))
    assert recovered == cm.next_sequence

    # A new boot epoch constructs a fresh manager — sequence resets to zero.
    writer2 = H.ok(venue_writer_id(H.MACHINE, H.ADAPTER_ROLE, v, a, "boot-epoch-2"))
    cm2 = H.ok(
        ConnectionManager.try_create(
            writer2,
            H.FakeSecretStore(),
            H.RecordingSink(),
            H.RecordingSink(),
            H.RecordingSink(),
        )
    )
    assert cm2.next_sequence == 0
    first_new_boot = H.ok(cm2.next_command_key(H.mk_instant(2000)))
    assert first_new_boot.sequence == 0
    assert writer2.boot_epoch_id != H.BOOT_EPOCH


def test_f064_no_second_event_loop_loaded_by_venue_compile() -> None:
    """AR-74 companion: venue path never loads Twisted / a second reactor."""
    forbidden = ("twisted", "openapipy", "ctrader_open_api", "spotware")
    loaded = {name for name in sys.modules if name.lower().startswith(forbidden)}
    assert loaded == set()
