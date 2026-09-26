"""Reference usage — QMB composition-root sandbox runner (Story 12.5).

Executable::

    python qmb/examples/sandbox_usage.py

Shows the things QL-8 / Story 12.5 pin down:

1. V1 enforcement of no-clock / no-I-O / no-network is static AST/import
   scanning, capability starvation (read surfaces only), and host process
   isolation — nothing else is promised.
2. Hardened OS-level confinement (job objects, seccomp) is a named deferred
   dependency; V1 does not wait on it.
3. A dynamically-evasive malicious bot is out of V1's threat model.
4. The runner uses stdlib process management, isolates the bot, and feeds
   observations to QML's pure verdict function — it never owns the verdict.
5. A clock, filesystem, or network finding is a Layer-2 failure before spawn.
"""

from __future__ import annotations

from typing import TypeVar

from qmb.host import (
    V1_DEFERRED_OS_CONFINEMENT,
    V1_ENFORCEMENT_MECHANISMS,
    V1_OUT_OF_SCOPE,
    run_sandbox,
    v1_enforcement_identity,
)
from qmf.core.chrono import CalendarIdentity
from qmf.core.exact import UnitKind
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Result, TypedRefusal, is_ok
from qml.conformance import CONFORMANCE_FORMAT_VERSION, Layer2Verdict, run_layer2_suite
from qml.declaration import BotDefinition, mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding, mint_footprint
from qml.logic import mint_logic_identity
from qml.protocol import PROTOCOL_FORMAT_VERSION, FunctionFactory, mint_state_scope

T = TypeVar("T")

_CLEAN = {
    "research_bot/__init__.py": "",
    "research_bot/bot.py": "def on_instant(self, evidence):\n    return ()\n",
}


def _unwrap(result: Result[T], what: str) -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"expected {what} to construct, got {result}")


def _pinned(tag: str) -> ProducerBinding:
    fp = _unwrap(fingerprint({"class": "example-producer", "tag": tag}), "producer fp")
    return _unwrap(ProducerBinding.try_create(fp), "binding")


def _calendar() -> CalendarIdentity:
    return _unwrap(CalendarIdentity.try_create("forex-17NY", "v3", "2025.2"), "calendar")


def _stream() -> dict[str, object]:
    return {
        "instrument_role": "primary",
        "bar_specs": [{"kind": "time-interval", "seconds": 60}],
        "stream_role": "trading",
    }


def _declaration(source: dict[str, str] | None = None) -> BotDefinition:
    zone = _pinned("zone")
    sma = _pinned("sma")
    confluence = _unwrap(
        mint_confluence([{"role": "level", "producer_binding": zone}]),
        "confluence",
    )
    footprint = _unwrap(mint_footprint([_stream()], [_calendar()], [zone, sma]), "footprint")
    logic = _unwrap(mint_logic_identity("research-bot", "1.0.0", source or _CLEAN), "logic")
    return _unwrap(
        mint_bot_definition(
            {
                "strategy_family_id": "trend-follow",
                "confluence_set": [confluence],
                "parameter_space": [
                    {
                        "name": "lookback",
                        "type": "exact integer",
                        "bounds": {"min": 1, "max": 200},
                        "step": 1,
                        "default": 20,
                        "unit_kind": UnitKind.COUNT,
                        "ui": "ui-editable",
                    }
                ],
                "footprint": footprint,
                "permitted_exit_intents": (),
                "logic_reference": logic,
            }
        ),
        "declaration",
    )


def _scope(declaration: BotDefinition) -> object:
    return _unwrap(
        mint_state_scope(
            os="windows-11",
            logic_identity=declaration.logic_reference,
            protocol_format_version=PROTOCOL_FORMAT_VERSION,
            arithmetic_reference_build="none",
        ),
        "scope",
    )


def _run(declaration: BotDefinition, source: dict[str, str] | None = None) -> Result[Layer2Verdict]:
    return run_sandbox(
        declaration=declaration,
        source_tree=source or _CLEAN,
        state_scope=_scope(declaration),
        state_bound=256,
        timeout_seconds=30,
    )


def v1_scope_is_honest() -> bool:
    identity = v1_enforcement_identity()
    assert identity["mechanisms"] == list(V1_ENFORCEMENT_MECHANISMS)
    assert "linux_seccomp" in V1_DEFERRED_OS_CONFINEMENT
    assert "windows_job_objects" in V1_DEFERRED_OS_CONFINEMENT
    assert "dynamically_evasive_malicious_bot" in V1_OUT_OF_SCOPE
    assert identity["process_management"] == "stdlib.subprocess"
    return True


def isolated_run_matches_in_process() -> bool:
    declaration = _declaration()
    in_process = _unwrap(
        run_layer2_suite(
            declaration=declaration,
            factory=FunctionFactory(logic=lambda evidence: ()),
            source_tree=_CLEAN,
            state_scope=_scope(declaration),
            state_bound=256,
        ),
        "in-process",
    )
    isolated = _unwrap(_run(declaration), "sandbox")
    assert isolated.fp1_identity() == in_process.fp1_identity()
    assert isolated.fp1_identity()["contract_format_version"] == CONFORMANCE_FORMAT_VERSION
    assert "host" not in isolated.fp1_identity()
    return True


def two_hosts_identical_verdict() -> bool:
    declaration = _declaration()
    host_a = _unwrap(_run(declaration), "host-a")
    host_b = _unwrap(_run(declaration), "host-b")
    return host_a.fp1_identity() == host_b.fp1_identity()


def _denied(source: dict[str, str]) -> str:
    refused = _run(_declaration(source), source)
    assert isinstance(refused, TypedRefusal)
    assert refused.context["field"] == "static_ast_import_scan"
    capability = refused.context["capability"]
    assert isinstance(capability, str)
    return capability


def clock_scan_fails_before_spawn() -> str:
    source = {"bot.py": "import time\n\ndef on_instant(self, evidence):\n    return ()\n"}
    return _denied(source)


def filesystem_scan_fails_before_spawn() -> str:
    source = {"bot.py": "def on_instant(self, evidence):\n    open('x')\n    return ()\n"}
    return _denied(source)


def network_scan_fails_before_spawn() -> str:
    source = {"bot.py": "import socket\n\ndef on_instant(self, evidence):\n    return ()\n"}
    return _denied(source)


def main() -> None:
    identity = v1_enforcement_identity()
    assert identity["class"] == "qmb-host-sandbox-v1"
    print(f"v1 mechanisms: {','.join(V1_ENFORCEMENT_MECHANISMS)}")
    print(f"deferred os confinement: {','.join(V1_DEFERRED_OS_CONFINEMENT)}")
    print(f"out of scope: {','.join(V1_OUT_OF_SCOPE)}")
    print(f"v1 scope is honest: {v1_scope_is_honest()}")
    print(f"isolated run matches in-process: {isolated_run_matches_in_process()}")
    print(f"two hosts identical verdict: {two_hosts_identical_verdict()}")
    print(f"clock import before spawn: {clock_scan_fails_before_spawn()}")
    print(f"filesystem open before spawn: {filesystem_scan_fails_before_spawn()}")
    print(f"network import before spawn: {network_scan_fails_before_spawn()}")
    print("sandbox runner ok")


if __name__ == "__main__":
    main()
