"""Story 16.3 — Python API door is a thin in-process re-export (B-1, B-13, AR-58)."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import TypeVar

import tomllib
from qmb.doors import api
from qmf.core.chrono import Instant
from qmf.core.fingerprint import World
from qmf.core.refusal import RefusalCategory, Result, TypedRefusal, is_ok, is_refusal

import qmb

T = TypeVar("T")

_QMB_ROOT = Path(__file__).resolve().parents[1]
_API_SRC = _QMB_ROOT / "src" / "qmb" / "doors" / "api"
_NS = 1_700_000_000_000_000_000
_HTTP_MODULES = frozenset(
    {
        "aiohttp",
        "django",
        "fastapi",
        "flask",
        "http",
        "httpx",
        "requests",
        "socket",
        "starlette",
        "urllib",
        "uvicorn",
    }
)
_HTTP_DEPENDENCIES = frozenset(
    {
        "aiohttp",
        "django",
        "fastapi",
        "flask",
        "httpx",
        "requests",
        "starlette",
        "uvicorn",
    }
)
_DOOR_EXTRA = (
    "CHANNEL",
    "COMPUTES_RUN_ID",
    "CONSUMER",
    "HOLDS_CACHE",
    "IN_PROCESS",
    "STACKED_OVER_HTTP",
    "TRANSPORT",
    "WRITES_GOVERNED_EVIDENCE",
    "api_door_identity",
)


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = _NS) -> Instant:
    return _ok(Instant.try_create(ns))


def _obs(stream_id: str, ns: int = _NS) -> api.SliceObservation:
    return _ok(api.SliceObservation.try_create(stream_id, _instant(ns), True))


def test_api_door_reexports_library_surface_identity_equal() -> None:
    library = set(qmb.__all__)
    door = set(api.__all__)
    assert library <= door
    assert door - library == set(_DOOR_EXTRA)
    missing = [name for name in qmb.__all__ if not hasattr(api, name)]
    assert missing == []
    for name in qmb.__all__:
        assert getattr(api, name) is getattr(qmb, name), name
    assert api.STRUCTURAL_SEED is qmb.STRUCTURAL_SEED
    assert api.run is qmb.run
    assert api.compile_run_config is qmb.compile_run_config
    assert api.refuse_aborted is qmb.refuse_aborted


def test_api_door_is_importable_from_uv_added_qmb() -> None:
    import importlib

    loaded = importlib.import_module("qmb.doors.api")
    assert loaded is api
    data = tomllib.loads((_QMB_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project = data["project"]
    assert project["name"] == "qmb"
    assert project["scripts"] == {"qmb": "qmb.doors.cli:main"}
    deps = tuple(str(item) for item in project["dependencies"])
    for dep in deps:
        token = dep.split("=", 1)[0].split(">", 1)[0].split("<", 1)[0].strip().casefold()
        assert token not in _HTTP_DEPENDENCIES
    assert api.CHANNEL == "uv add qmb"


def test_ui_backend_consumes_api_in_process_never_http() -> None:
    identity = api.api_door_identity()
    assert api.IN_PROCESS is True
    assert api.STACKED_OVER_HTTP is False
    assert api.TRANSPORT == "in-process"
    assert api.CONSUMER == "ui-backend"
    assert api.HOLDS_CACHE is False
    assert api.COMPUTES_RUN_ID is False
    assert api.WRITES_GOVERNED_EVIDENCE is False
    assert identity["in_process"] is True
    assert identity["stacked_over_http"] is False
    assert identity["transport"] == "in-process"
    assert identity["consumer"] == "ui-backend"
    assert identity["channel"] == "uv add qmb"
    assert identity["writes_governed_evidence"] is False
    assert qmb.__version__ not in identity.values()
    assert identity["stacked_over_http"] is api.STACKED_OVER_HTTP is False


def test_refusal_is_returned_verbatim_not_raised() -> None:
    refused = api.compile_run_config(
        None,
        book_fragment=None,
        bms_fragment=None,
        run_spec=None,
    )
    assert is_refusal(refused)
    assert isinstance(refused, TypedRefusal)
    assert refused.category is RefusalCategory.INVALID_INPUT
    aborted = api.refuse_aborted(
        cause=api.CAUSE_CANCEL,
        progress=api.RunProgress(
            data_points_processed=0,
            slices_completed=0,
            is_warming_up=False,
        ),
    )
    assert is_refusal(aborted)
    assert aborted.category is RefusalCategory.POLICY_REJECTION
    assert aborted.context["terminal"] == api.TERMINAL_ABORTED
    bad_run = api.run(slices="not-slices")
    assert is_refusal(bad_run)
    assert bad_run.category is RefusalCategory.INVALID_INPUT


def test_programmer_error_is_not_the_refusal_channel() -> None:
    payload: object
    try:
        payload = api.identity_payload("nope")  # type: ignore[call-arg]
    except TypeError:
        return
    raise AssertionError(f"expected TypeError, got {payload!r}")


def test_direct_api_run_produces_no_governed_evidence(tmp_path: Path) -> None:
    outcome = api.run(
        slices=((_obs("eurusd"),),),
        stream_set=("eurusd",),
        handler=api.SilentSliceHandler(),
    )
    assert is_ok(outcome)
    assert list(tmp_path.rglob("*.jsonl")) == []
    sink = _ok(
        api.LedgerSink.try_create(
            tmp_path / "ledger",
            machine="api-door",
            worker_slot=0,
            boot_epoch_id="boot-1",
        )
    )
    merged = _ok(api.read_merge_view(sink.root, world=World.REPLAY, role=api.ROLE_CONFIRMATION))
    assert merged == ()
    assert api.WRITES_GOVERNED_EVIDENCE is False
    assert api.run is qmb.run


def test_api_door_source_is_thin_reexport() -> None:
    offenders: list[str] = []
    imported: list[str] = []
    defined: list[str] = []
    for path in sorted(_API_SRC.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                defined.append(node.name)
                if node.name != "api_door_identity":
                    offenders.append(f"{path.name}: FunctionDef {node.name}")
            elif isinstance(node, ast.ClassDef):
                offenders.append(f"{path.name}: ClassDef {node.name}")
            elif isinstance(node, ast.AsyncFunctionDef):
                offenders.append(f"{path.name}: AsyncFunctionDef {node.name}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.append(node.module)
            if isinstance(node, ast.Raise) and node.exc is not None:
                target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
                name: str | None = None
                if isinstance(target, ast.Name):
                    name = target.id
                elif isinstance(target, ast.Attribute):
                    name = target.attr
                if name == "TypedRefusal":
                    offenders.append(f"{path.name}: raise TypedRefusal")
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "fingerprint"
            ):
                offenders.append(f"{path.name}: fingerprint()")
    assert defined == ["api_door_identity"]
    for name in imported:
        root = name.split(".", 1)[0]
        if name in _HTTP_MODULES or root in _HTTP_MODULES:
            offenders.append(f"imports {name}")
    assert "qmf.venue" not in imported
    assert "click" not in imported
    assert offenders == []
