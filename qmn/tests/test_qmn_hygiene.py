"""Story 25.13 / QMX-F064 — runtime hygiene, parameters, secrets, and boot reset."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path
from typing import TypeVar

import tomllib
from qmf.core.refusal import Result, is_ok, is_refusal
from qmn.config import (
    COMPILE_LAYERS,
    HAS_INVOCATION_OVERRIDE_LAYER,
    VALUE_STATUS_REQUIRED_ROWS,
    compile_node_config,
    config_init,
    refuse_unknown_compile_layer,
    validate_registry_row_schema,
)
from qmn.host import (
    EVENT_LOOP_COUNT,
    NODE_RESURRECT_SUBTYPE,
    OPERATOR_PRINCIPAL,
    REQUESTED_RESTART_REASON,
    CrashLoopFold,
    LifecycleState,
    LifecycleSupervisor,
    StandDownTrigger,
)
from qmn.host.supervise import (
    BootAttemptStamp,
    RecordingNotifyTransport,
    SupervisionConfig,
)

T = TypeVar("T")

_QMN_ROOT = Path(__file__).resolve().parents[1]
_SRC = _QMN_ROOT / "src" / "qmn"
_DEPLOY = _QMN_ROOT / "deploy"
_WORKSPACE = _QMN_ROOT.parent
_VENUE_SRC = _WORKSPACE / "packages" / "qmf-venue" / "src" / "qmf" / "venue"
_BANNED = ("twisted", "ctrader_open_api", "openapipy", "spotware", "openapi_client")
_MAX_SOURCE_BYTES = 1 << 20  # 1 MiB


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _load_deploy_boundary():
    path = _DEPLOY / "boundary.py"
    spec = importlib.util.spec_from_file_location("qmn_deploy_boundary_hygiene", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _imported_modules(path: Path) -> set[str]:
    """Every dotted module name imported by one source file (import + from-import).

    The path is resolved and must be a regular file inside the workspace — never a
    symlink, never resolving out of the workspace — and its size is capped before
    the read, so a planted symlink or an oversized file can neither redirect nor
    unbound it.
    """
    resolved = path.resolve()
    assert not path.is_symlink(), resolved
    assert resolved.is_file() and resolved.is_relative_to(_WORKSPACE), resolved
    size = resolved.stat().st_size
    assert size <= _MAX_SOURCE_BYTES, resolved
    tree = ast.parse(resolved.read_text(encoding="utf-8"), filename=str(resolved))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            names.add(node.module)
    return names


def _supervisor(*, k: int = 3, window_ns: int = 60_000_000_000) -> LifecycleSupervisor:
    config = _ok(
        SupervisionConfig.try_create(
            crash_loop_max_boots=k,
            crash_loop_window_ns=window_ns,
            drain_window_ns=1_000_000_000,
            watchdog_interval_ns=1_000_000_000,
            seat_callback_deadline_ns=100_000_000,
            slice_watch_trip_multiple=3,
        )
    )
    return LifecycleSupervisor(
        config=config,
        notify=RecordingNotifyTransport(),
        boot_epoch_id="boot-1",
    )


# --- AC1: Tier-1 static hygiene gates ---------------------------------------


def test_spotware_twisted_banned_in_node_and_venue() -> None:
    violations: list[str] = []
    for root in (_SRC, _VENUE_SRC):
        for path in sorted(root.rglob("*.py")):
            for imported in _imported_modules(path):
                low = imported.lower()
                root_name = low.split(".", 1)[0]
                if root_name in _BANNED or any(token in low for token in _BANNED):
                    violations.append(f"{path}:{imported}")
    assert violations == []


def test_single_event_loop_declared_no_second_loop_constructors() -> None:
    assert EVENT_LOOP_COUNT == 1
    banned_calls = ("new_event_loop", "set_event_loop", "run_until_complete")
    hits: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        text = path.read_text(encoding="utf-8")
        # Allow documenting the ban; forbid asyncio.new_event_loop / set_event_loop usage.
        if "asyncio.new_event_loop" in text or "asyncio.set_event_loop" in text:
            hits.append(str(path.relative_to(_SRC)))
        tree = ast.parse(text, filename=str(path))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and node.func.attr in banned_calls
                # venue edge / doors may call run_until_complete on the ONE loop.
                and node.func.attr != "run_until_complete"
            ):
                hits.append(f"{path.relative_to(_SRC)}:{node.func.attr}")
    assert hits == []


def test_qmf_venue_import_only_under_qmn_venue() -> None:
    violations: list[str] = []
    for path in sorted(_SRC.rglob("*.py")):
        relative = path.relative_to(_SRC)
        under_venue = relative.parts and relative.parts[0] == "venue"
        for imported in _imported_modules(path):
            is_venue = imported == "qmf.venue" or imported.startswith("qmf.venue.")
            if is_venue and not under_venue:
                violations.append(f"{relative}: {imported}")
    assert violations == []


def test_no_node_console_script() -> None:
    data = tomllib.loads((_QMN_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert not data.get("project", {}).get("scripts")
    assert "console_scripts" not in data.get("project", {}).get("entry-points", {})


def test_recipes_cannot_import_composition_root() -> None:
    boundary = _load_deploy_boundary()
    assert boundary.deploy_may_import("qmn.host") is False
    assert boundary.deploy_may_import("qmn.doors.api") is False
    for path in sorted(_DEPLOY.rglob("*.py")):
        for imported in _imported_modules(path):
            assert not (imported == "qmn" or imported.startswith("qmn.")), path


def test_secret_scanner_covers_declared_surfaces_and_rendered_config() -> None:
    sys.path.insert(0, str(_WORKSPACE / "tools"))
    import secret_scan as scanner

    assert {
        "source",
        "fixtures",
        "unit_files",
        "rendered_config",
        "logs",
        "refusal_snapshots",
    } <= scanner.COVERED_SURFACES
    scanned = {p.as_posix().replace("\\", "/") for p in scanner.iter_scanned_files(_WORKSPACE)}
    # Rendered config under qmn/deploy/fixtures must be in scope (not path-skipped).
    assert any(path.endswith("qmn/deploy/fixtures/render-values.json") for path in scanned)
    # Unit files and project fixtures stay in scope; only tools/tests/fixtures is skipped.
    assert any("/qmn/tests/" in path for path in scanned)
    assert not any(path.startswith("tools/tests/fixtures/") for path in scanned)

    root = tomllib.loads((_WORKSPACE / "pyproject.toml").read_text(encoding="utf-8"))
    assert "secret-scan" in root["tool"]["poe"]["tasks"]["check"]["sequence"]


# --- AC2: config compilation / registry-schema gates ------------------------


def test_undeclared_parameter_unknown_layer_and_missing_schema_refused() -> None:
    assert HAS_INVOCATION_OVERRIDE_LAYER is False
    assert "invocation" not in COMPILE_LAYERS

    refused_key = compile_node_config(
        node_defaults={"not_a_registry_key": {"value": 1, "value_status": "ratified"}}
    )
    assert is_refusal(refused_key)

    assert is_refusal(refuse_unknown_compile_layer("invocation"))
    assert is_refusal(refuse_unknown_compile_layer("runtime-override"))
    assert _ok(refuse_unknown_compile_layer("book")) == "book"

    missing_owner = validate_registry_row_schema(
        {
            "name": "example_row",
            "component": "COMP-QMN",
            "units": "count",
            "type": "int",
            "blank_effect": ("blocks-boot",),
            "configurable": True,
        }
    )
    assert is_refusal(missing_owner)

    missing_status = compile_node_config(
        book={"news_blackout_before": {"value": 15}}  # no value_status
    )
    assert is_refusal(missing_status)

    for row in VALUE_STATUS_REQUIRED_ROWS:
        assert is_ok(validate_registry_row_schema(row))


def test_no_literal_operational_defaults_or_hard_coded_node_values() -> None:
    artifact = _ok(config_init())
    # Compiler never invents operational defaults — blanks stay blank/None.
    for row in artifact.rows.values():
        assert row.value_status == "blank"
        assert row.value is None
        assert row.owner_scope
        assert row.configurable is True
    for name in ("ksa_effect_matrix", "max_slice_latency", "submission_deadline"):
        assert artifact.rows[name].value is None


# --- AC3: crash-loop / boot-attempt fold ------------------------------------


def test_crash_loop_durable_across_process_restart_not_reset_by_restart_alone() -> None:
    fold = CrashLoopFold(max_boots=3, window_ns=60_000_000_000)
    base = 1_000_000_000_000
    for index in range(2):
        _ok(
            fold.record(
                BootAttemptStamp(
                    boot_epoch_id=f"boot-crash-{index}",
                    at_ns=base + index,
                    reason=None,
                    exited=True,
                )
            )
        )
    # Process restart reloads durable stamps — counters do not clear.
    reloaded = _ok(
        CrashLoopFold.load(
            max_boots=3,
            window_ns=60_000_000_000,
            stamps=fold.stamps,
        )
    )
    verdict = reloaded.evaluate(now_ns=base + 10)
    assert verdict.counted_boots == 2
    assert verdict.threshold_breached is False

    # Requested restart never advances the fold.
    _ok(
        reloaded.record(
            BootAttemptStamp(
                boot_epoch_id="boot-restart",
                at_ns=base + 11,
                reason=REQUESTED_RESTART_REASON,
                exited=True,
            )
        )
    )
    assert reloaded.evaluate(now_ns=base + 11).counted_boots == 2


def test_resurrect_resets_fold_unrequested_crash_cannot_masquerade() -> None:
    supervisor = _supervisor(k=2)
    base = 2_000_000_000_000
    for index in range(2):
        _ok(
            supervisor.record_boot_attempt(
                boot_epoch_id=f"boot-{index}",
                at_ns=base + index,
                reason=None,
                exited=True,
            )
        )
    assert supervisor.state is LifecycleState.STAND_DOWN_ALIVE
    assert supervisor.stand_down_trigger is StandDownTrigger.CRASH_LOOP
    assert supervisor.crash_loop is not None
    assert len(supervisor.crash_loop.stamps) == 2

    receipt = _ok(
        supervisor.resurrect(
            principal=OPERATOR_PRINCIPAL,
            scope="global",
            new_boot_epoch_id="boot-operator-clean",
        )
    )
    assert receipt.subtype == NODE_RESURRECT_SUBTYPE
    assert supervisor.state is LifecycleState.RUNNING
    assert supervisor.crash_loop is not None
    # Operator cycle reset — prior unrequested crashes do not carry into the new epoch.
    assert supervisor.crash_loop.stamps == ()
    assert supervisor.crash_loop.evaluate(now_ns=base + 100).counted_boots == 0

    # A fresh unrequested crash after resurrect starts a new count.
    _ok(
        supervisor.record_boot_attempt(
            boot_epoch_id="boot-after-resurrect",
            at_ns=base + 101,
            reason=None,
            exited=True,
        )
    )
    assert supervisor.crash_loop.evaluate(now_ns=base + 101).counted_boots == 1
