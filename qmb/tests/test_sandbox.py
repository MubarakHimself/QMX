"""Story 12.5 — host-owned sandbox runner within the V1 enforcement scope."""

from __future__ import annotations

import ast
import inspect
import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any, TypeVar, cast

from qmb.host import (
    V1_DEFERRED_OS_CONFINEMENT,
    V1_ENFORCEMENT_MECHANISMS,
    V1_OUT_OF_SCOPE,
    run_sandbox,
    v1_enforcement_identity,
)
from qmb.host import runner as host_runner
from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import RefusalCategory, Result, is_ok, is_refusal
from qml.conformance import Layer2Verdict, evaluate_layer2, run_layer2_suite
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope

import qml

T = TypeVar("T")

_CLEAN_SOURCE: dict[str, str] = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}
_FACTORY_SOURCE = (
    "from qml.protocol import FunctionFactory\n"
    "factory = FunctionFactory(logic=lambda evidence: ())\n"
)
_OS = "windows-11"
_AR = "none"
_BOUND = 256
_TIMEOUT = 30
_HOST = Path(__file__).resolve().parents[1] / "src" / "qmb" / "host"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _pinned(tag: str) -> ProducerBinding:
    fp = _ok(fingerprint({"class": "test-producer", "tag": tag}))
    return _ok(ProducerBinding.try_create(fp))


def _calendar() -> CalendarIdentity:
    return _ok(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"))


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def _int_param() -> dict[str, object]:
    return {
        "name": "lookback",
        "type": "exact integer",
        "bounds": {"min": 1, "max": 200},
        "step": 1,
        "default": 20,
        "unit_kind": UnitKind.COUNT,
        "ui": "ui-editable",
    }


def _declaration(*, source: dict[str, str] | None = None) -> BotDefinition:
    zone = _pinned("zone")
    sma = _pinned("sma")
    confluence = _ok(mint_confluence([{"role": "level", "producer_binding": zone}]))
    footprint = _ok(mint_footprint([_stream()], [_calendar()], [zone, sma]))
    logic = _ok(mint_logic_identity("research-bot", "1.0.0", source or _CLEAN_SOURCE))
    return _ok(
        mint_bot_definition(
            {
                "strategy_family_id": "trend-follow",
                "confluence_set": [confluence],
                "parameter_space": [_int_param()],
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        )
    )


def _scope(declaration: BotDefinition):
    return _ok(
        mint_state_scope(
            os=_OS,
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build=_AR,
        )
    )


def _sandbox(
    declaration: BotDefinition,
    *,
    source: dict[str, str] | None = None,
    factory_spec: object = None,
) -> Result[Layer2Verdict]:
    return run_sandbox(
        declaration=declaration,
        source_tree=source or _CLEAN_SOURCE,
        factory_spec=factory_spec,
        state_scope=_scope(declaration),
        state_bound=_BOUND,
        timeout_seconds=_TIMEOUT,
    )


def _host_obs(verdict: Layer2Verdict) -> dict[str, object]:
    return {
        "loaded_in_isolation": True,
        "book_present": False,
        "scan_findings": (),
        "golden_slice_fingerprint": verdict.golden_slice_fingerprint,
        "declaration_fingerprint": verdict.declaration_fingerprint,
        "first_run": ((), (), ()),
        "second_run": ((), (), ()),
        "emitted_kinds": (),
        "permitted_exit_intents": (),
        "state_bound_holds": True,
        "restore_equivalent": True,
    }


# --- AC: V1 enforcement is scan + starvation + process isolation only ---------


def test_v1_enforcement_identity_names_the_honest_scope() -> None:
    identity = v1_enforcement_identity()
    assert identity["class"] == "qmb-host-sandbox-v1"
    assert identity["mechanisms"] == list(V1_ENFORCEMENT_MECHANISMS)
    assert identity["mechanisms"] == [
        "static_ast_import_scan",
        "capability_starvation",
        "host_process_isolation",
    ]
    assert identity["deferred_os_confinement"] == list(V1_DEFERRED_OS_CONFINEMENT)
    assert V1_DEFERRED_OS_CONFINEMENT == (
        "windows_restricted_tokens",
        "windows_job_objects",
        "linux_seccomp",
    )
    assert identity["out_of_scope"] == list(V1_OUT_OF_SCOPE)
    assert V1_OUT_OF_SCOPE == ("dynamically_evasive_malicious_bot",)
    assert identity["process_management"] == "stdlib.subprocess"
    assert identity["verdict_function"] == "qml.conformance.evaluate_layer2"
    assert qml.__version__ not in identity.values()


def test_runner_uses_stdlib_subprocess_and_not_os_confinement() -> None:
    imported: set[str] = set()
    for path in sorted(_HOST.glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                assert node.func.id not in {"exec", "eval"}
    assert "subprocess" in imported
    assert "importlib" in imported or "runpy" in imported
    assert "ctypes" not in imported
    assert "win32api" not in imported
    assert "prctl" not in imported
    source = (_HOST / "runner.py").read_text(encoding="utf-8")
    assert "seccomp" in source
    assert "job_objects" in source
    assert "deferred" in source.lower()


def test_run_sandbox_signature_has_no_book_and_no_verdict_hook() -> None:
    names = inspect.signature(run_sandbox).parameters
    assert "book" not in names
    assert "book_module" not in names
    assert "verdict" not in names
    assert "evaluate" not in names


def test_pure_library_does_not_reexport_the_host_runner() -> None:
    assert not hasattr(qml, "run_sandbox")
    assert "run_sandbox" not in qml.__all__


def test_book_key_on_factory_spec_is_layer2_failure() -> None:
    declaration = _declaration()
    refused = _sandbox(declaration, factory_spec={"kind": "silent", "book": "nope"})
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "no_book_present"


# --- AC: stdlib process isolation; runner never owns the verdict --------------


def test_clean_logic_spawns_isolated_process_and_matches_in_process_verdict(
    monkeypatch: Any,
) -> None:
    declaration = _declaration()
    in_process = _ok(
        run_layer2_suite(
            declaration=declaration,
            factory=FunctionFactory(logic=lambda _evidence: ()),
            source_tree=_CLEAN_SOURCE,
            state_scope=_scope(declaration),
            state_bound=_BOUND,
        )
    )
    recorded: dict[str, object] = {}
    real_run = host_runner.subprocess.run

    def wrapped(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        completed = cast("subprocess.CompletedProcess[str]", real_run(*args, **kwargs))
        argv = args[0] if args else kwargs.get("args")
        recorded["argv"] = list(cast("list[object]", argv))
        recorded["stdout"] = completed.stdout
        return completed

    monkeypatch.setattr(host_runner.subprocess, "run", wrapped)
    isolated = _ok(_sandbox(declaration))
    assert isolated.fp1_identity() == in_process.fp1_identity()
    assert "host" not in isolated.fp1_identity()
    stdout = recorded["stdout"]
    assert isinstance(stdout, str)
    envelope = json.loads(stdout)
    assert envelope["ok"] is True
    assert envelope["worker_pid"] != os.getpid()
    assert "worker_pid" not in isolated.fp1_identity()
    argv = cast("list[object]", recorded["argv"])
    assert argv[0] == sys.executable
    assert "-m" in argv
    assert "qmb.host.worker" in argv


def test_source_factory_spec_isolated_run_passes() -> None:
    declaration = _declaration()
    verdict = _ok(_sandbox(declaration, factory_spec={"kind": "source", "source": _FACTORY_SOURCE}))
    assert isinstance(verdict, Layer2Verdict)
    assert verdict.fp1_identity()["class"] == "qml-layer2-verdict"


def test_load_factory_source_binds_factory() -> None:
    factory = _ok(
        host_runner.load_factory(
            host_runner.FactorySpec(kind=host_runner.FACTORY_KIND_SOURCE, source=_FACTORY_SOURCE)
        )
    )
    assert factory is not None


def test_load_factory_syntax_error_is_invalid() -> None:
    refused = host_runner.load_factory(
        host_runner.FactorySpec(kind=host_runner.FACTORY_KIND_SOURCE, source="def (\n")
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "factory_spec"
    assert refused.context["layer"] == 2
    assert refused.context["lineno"] == 1


def test_load_factory_missing_binding_is_invalid() -> None:
    refused = host_runner.load_factory(
        host_runner.FactorySpec(kind=host_runner.FACTORY_KIND_SOURCE, source="value = 1\n")
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "factory_spec"
    assert "lineno" not in refused.context


def test_load_factory_runtime_error_is_invalid() -> None:
    refused = host_runner.load_factory(
        host_runner.FactorySpec(
            kind=host_runner.FACTORY_KIND_SOURCE,
            source="raise RuntimeError('nope')\n",
        )
    )
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "factory_spec"
    assert refused.context["given"] == "RuntimeError"


def test_two_sandbox_hosts_mint_one_verdict() -> None:
    declaration = _declaration()
    host_a = _ok(_sandbox(declaration))
    host_b = _ok(_sandbox(declaration))
    assert host_a.fp1_identity() == host_b.fp1_identity()
    left = _ok(evaluate_layer2({**_host_obs(host_a), "host": "qmb"}))
    right = _ok(evaluate_layer2({**_host_obs(host_a), "host": "node"}))
    assert left.fp1_identity() == right.fp1_identity()


def test_worker_crash_is_unavailable(monkeypatch: Any) -> None:
    def fake_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(
            args=[sys.executable, "-m", "qmb.host.worker"],
            returncode=1,
            stdout="",
            stderr="boom",
        )

    monkeypatch.setattr(host_runner.subprocess, "run", fake_run)
    refused = _sandbox(_declaration())
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    assert refused.context["field"] == "sandbox_process"


def test_worker_module_never_imports_evaluate_layer2() -> None:
    source = (_HOST / "worker.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
            if node.names:
                assert all(alias.name != "evaluate_layer2" for alias in node.names)
    assert "qmb.host.runner" in imported
    assert "qml.conformance.layer2" not in imported
    assert "qml.conformance" not in imported


# --- AC: clock / fs / network scan is Layer-2 failure before spawn -----------


def _assert_no_spawn(monkeypatch: Any, source: dict[str, str], capability: str) -> None:
    def boom(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        raise AssertionError("scan findings must not spawn a process")

    monkeypatch.setattr(host_runner.subprocess, "run", boom)
    declaration = _declaration(source=source)
    refused = _sandbox(declaration, source=source)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "static_ast_import_scan"
    assert refused.context["capability"] == capability
    assert refused.context["layer"] == 2


def test_clock_import_fails_before_spawn(monkeypatch: Any) -> None:
    source = {"bot.py": "import time\n\ndef on_instant(self, evidence):\n    return ()\n"}
    _assert_no_spawn(monkeypatch, source, "clock")


def test_filesystem_open_fails_before_spawn(monkeypatch: Any) -> None:
    source = {"bot.py": "def on_instant(self, evidence):\n    open('x')\n    return ()\n"}
    _assert_no_spawn(monkeypatch, source, "io")


def test_network_import_fails_before_spawn(monkeypatch: Any) -> None:
    source = {"bot.py": "import socket\n\ndef on_instant(self, evidence):\n    return ()\n"}
    _assert_no_spawn(monkeypatch, source, "network")


def test_payload_starves_capabilities_and_injects_read_surfaces_only(
    monkeypatch: Any,
) -> None:
    captured: dict[str, object] = {}
    real_run = host_runner.subprocess.run

    def wrapped(*args: Any, **kwargs: Any) -> subprocess.CompletedProcess[str]:
        captured["input"] = kwargs.get("input")
        return cast("subprocess.CompletedProcess[str]", real_run(*args, **kwargs))

    monkeypatch.setattr(host_runner.subprocess, "run", wrapped)
    _ok(_sandbox(_declaration()))
    raw = captured["input"]
    assert isinstance(raw, str)
    payload = json.loads(raw)
    assert isinstance(payload, dict)
    mapping = cast("dict[str, object]", payload)
    assert "book" not in mapping
    assert "book_module" not in mapping
    assert mapping["book_present"] is False
    assert mapping["read_surfaces_only"] is True
    spec = cast("Mapping[str, object]", mapping["factory_spec"])
    assert spec["kind"] == "silent"
