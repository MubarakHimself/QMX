"""Click-free CLI command tree: groups, prerequisites, and transport (B-1).

Every capability lives once in the library. This module sequences declared
library entry points — ``compile_run_config`` then ``qmb.orchestrator.spawn_run``
— and never computes a run-id or holds a cache (DEC-0159, DEC-0160).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Final, cast

from qmf.core.fingerprint import Fingerprint
from qmf.core.refusal import Ok, Result, is_refusal

from qmb._refuse import clean_token, invalid, unavailable
from qmb.config import ResolvedRunConfig, compile_run_config, run_config_identity
from qmb.data import DATA_COMMANDS, data_front_identity
from qmb.doors import CLI_PIN_KEY, CLI_PROG
from qmb.ledger import LedgerLine
from qmb.optimize import parameter_space_from_bot
from qmb.orchestrator import IsolatedRun, read_book_bar, read_merge_view, spawn_run

__all__ = [
    "COMMAND_GROUPS",
    "COMPUTES_RUN_ID",
    "HOLDS_CACHE",
    "ORCHESTRATOR_ENTRY",
    "BacktestSubmission",
    "cli_tree_identity",
    "command_prerequisites",
    "command_tree",
    "invoke_backtest",
    "invoke_config_compile",
    "invoke_config_show",
    "invoke_data",
    "invoke_ledger_bar",
    "invoke_ledger_merge",
    "invoke_optimize_run",
    "invoke_optimize_space",
    "require_prerequisites",
]

COMMAND_GROUPS: Final[tuple[str, ...]] = (
    "backtest",
    "data",
    "optimize",
    "ledger",
    "config",
)
COMPUTES_RUN_ID: Final[bool] = False
HOLDS_CACHE: Final[bool] = False
ORCHESTRATOR_ENTRY: Final[str] = "qmb.orchestrator.spawn_run"

_COMMAND_TREE: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "backtest": ("run",),
        "data": DATA_COMMANDS,
        "optimize": ("run", "space"),
        "ledger": ("merge", "bar"),
        "config": ("compile", "show"),
    }
)

_BACKTEST_PREREQS: Final[tuple[str, ...]] = (
    "port",
    "book_fragment",
    "bms_fragment",
    "run_spec",
    "slices",
    "output_root",
)

_COMMAND_PREREQS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType(
    {
        "backtest.run": _BACKTEST_PREREQS,
        "data.download": ("destination",),
        "data.verify": ("archive",),
        "data.catalog": (),
        "data.generate": ("destination",),
        "optimize.run": ("declaration", *_BACKTEST_PREREQS),
        "optimize.space": ("declaration",),
        "ledger.merge": ("root", "world", "role"),
        "ledger.bar": ("root", "world"),
        "config.compile": ("port", "book_fragment", "bms_fragment", "run_spec"),
        "config.show": (),
    }
)

_CompileFn = Callable[..., Result[ResolvedRunConfig]]
_OrchFn = Callable[..., Result[IsolatedRun]]


@dataclass(frozen=True, slots=True)
class BacktestSubmission:
    """Compiler artifact plus the orchestrator's isolated outcome.

    ``run_id`` is the resolved-config fingerprint the compiler already stamped.
    The door never mints a second identity.
    """

    config: ResolvedRunConfig
    isolated: IsolatedRun

    @property
    def run_id(self) -> Fingerprint:
        """Run-id root: the compiler's fingerprint, never a door-local recipe."""
        return self.config.fingerprint


def command_tree() -> dict[str, tuple[str, ...]]:
    """Platform command groups and their subcommands (B-1, AR-10)."""
    return dict(_COMMAND_TREE)


def cli_tree_identity() -> dict[str, object]:
    """Identity-bearing CLI-door fields. The click pin value is not restated."""
    return {
        "adaptation": ("parsing", "transport", "refusal-rendering", "autocomplete"),
        "computes_run_id": COMPUTES_RUN_ID,
        "groups": COMMAND_GROUPS,
        "holds_cache": HOLDS_CACHE,
        "orchestrator_entry": ORCHESTRATOR_ENTRY,
        "pin_key": CLI_PIN_KEY,
        "prog": CLI_PROG,
    }


def command_prerequisites(command: object) -> Result[tuple[str, ...]]:
    """Declared config/resource prerequisites for one tree command."""
    token = clean_token(command)
    if token is None:
        return invalid("command", "a CLI command name is a non-blank token")
    required = _COMMAND_PREREQS.get(token)
    if required is None:
        return invalid("command", "unknown CLI command", given=token, tree=COMMAND_GROUPS)
    return Ok(required)


def require_prerequisites(command: object, provided: object) -> Result[None]:
    """Return a typed refusal when declared command resources are absent (CT-04)."""
    required = command_prerequisites(command)
    if is_refusal(required):
        return required
    if not isinstance(provided, Mapping):
        return invalid(
            "provided",
            "command prerequisites are a key->value mapping",
            given=repr(type(provided).__name__),
        )
    body = cast("Mapping[str, object]", provided)
    missing = [name for name in required.value if not _present(body.get(name))]
    if missing:
        token = clean_token(command)
        return unavailable(
            "prerequisites",
            "command config or resource prerequisites are absent",
            command=token,
            missing=missing,
            required=list(required.value),
        )
    return Ok(None)


def invoke_config_show() -> Result[Mapping[str, object]]:
    """Show the resolved-run-config identity schema (no I/O)."""
    checked = require_prerequisites("config.show", {})
    if is_refusal(checked):
        return checked
    return Ok(run_config_identity())


def invoke_config_compile(
    *,
    port: object = None,
    book_fragment: object = None,
    bms_fragment: object = None,
    run_spec: object = None,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    compiler: object = None,
) -> Result[ResolvedRunConfig]:
    """Compile one resolved run-config through the Epic 13 compiler (B-3)."""
    checked = require_prerequisites(
        "config.compile",
        {
            "port": port,
            "book_fragment": book_fragment,
            "bms_fragment": bms_fragment,
            "run_spec": run_spec,
        },
    )
    if is_refusal(checked):
        return checked
    compile_fn = _as_compiler(compiler)
    if is_refusal(compile_fn):
        return compile_fn
    return compile_fn.value(
        port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec=run_spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
    )


def invoke_backtest(
    *,
    port: object = None,
    book_fragment: object = None,
    bms_fragment: object = None,
    run_spec: object = None,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    slices: object = None,
    output_root: object = None,
    compiler: object = None,
    orchestrator: object = None,
    cancel: object = None,
    limits: object = None,
    probe: object = None,
) -> Result[BacktestSubmission]:
    """Compile via ``compile_run_config`` and submit to ``spawn_run`` (B-1, B-3).

    The run-id root is the compiled artifact's fingerprint. This door does not
    call ``fp1`` and does not name a run directory of its own.
    """
    checked = require_prerequisites(
        "backtest.run",
        {
            "port": port,
            "book_fragment": book_fragment,
            "bms_fragment": bms_fragment,
            "run_spec": run_spec,
            "slices": slices,
            "output_root": output_root,
        },
    )
    if is_refusal(checked):
        return checked
    compiled = invoke_config_compile(
        port=port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec=run_spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
        compiler=compiler,
    )
    if is_refusal(compiled):
        return compiled
    orch = _as_orchestrator(orchestrator)
    if is_refusal(orch):
        return orch
    submitted = orch.value(
        config=compiled.value,
        slices=slices,
        output_root=output_root,
        cancel=cancel,
        limits=limits,
        probe=probe,
    )
    if is_refusal(submitted):
        return submitted
    return Ok(BacktestSubmission(config=compiled.value, isolated=submitted.value))


def invoke_optimize_space(*, declaration: object = None) -> Result[object]:
    """Read the CT-33-authoritative parameter-space schema (B-8)."""
    checked = require_prerequisites("optimize.space", {"declaration": declaration})
    if is_refusal(checked):
        return checked
    parsed = parameter_space_from_bot(declaration)
    if is_refusal(parsed):
        return parsed
    space: object = parsed.value
    return Ok(space)


def invoke_optimize_run(
    *,
    declaration: object = None,
    port: object = None,
    book_fragment: object = None,
    bms_fragment: object = None,
    run_spec: object = None,
    invocation_flags: object = None,
    workspace_defaults: object = None,
    condition_presets: object = (),
    slices: object = None,
    output_root: object = None,
    compiler: object = None,
    orchestrator: object = None,
    cancel: object = None,
    limits: object = None,
    probe: object = None,
) -> Result[BacktestSubmission]:
    """One optimize trial is a first-class backtest run (B-8, B-3)."""
    checked = require_prerequisites(
        "optimize.run",
        {
            "declaration": declaration,
            "port": port,
            "book_fragment": book_fragment,
            "bms_fragment": bms_fragment,
            "run_spec": run_spec,
            "slices": slices,
            "output_root": output_root,
        },
    )
    if is_refusal(checked):
        return checked
    return invoke_backtest(
        port=port,
        book_fragment=book_fragment,
        bms_fragment=bms_fragment,
        run_spec=run_spec,
        invocation_flags=invocation_flags,
        workspace_defaults=workspace_defaults,
        condition_presets=condition_presets,
        slices=slices,
        output_root=output_root,
        compiler=compiler,
        orchestrator=orchestrator,
        cancel=cancel,
        limits=limits,
        probe=probe,
    )


def invoke_data(command: object, provided: object = None) -> Result[Mapping[str, object]]:
    """Thin data-command front over the ratified qmf-data contracts (B-11)."""
    token = clean_token(command)
    if token is None or token not in DATA_COMMANDS:
        return invalid(
            "command",
            "data commands are download, verify, catalog, generate",
            given=repr(command),
            legal=list(DATA_COMMANDS),
        )
    resources: Mapping[str, object]
    if provided is None:
        resources = {}
    elif isinstance(provided, Mapping):
        resources = cast("Mapping[str, object]", provided)
    else:
        return invalid(
            "provided",
            "command prerequisites are a key->value mapping",
            given=repr(type(provided).__name__),
        )
    checked = require_prerequisites(f"data.{token}", resources)
    if is_refusal(checked):
        return checked
    payload: dict[str, object] = {"command": token}
    payload.update(data_front_identity())
    return Ok(payload)


def invoke_ledger_merge(
    *,
    root: object = None,
    world: object = None,
    role: object = None,
) -> Result[tuple[LedgerLine, ...]]:
    """World-and-role-scoped ledger merge view (B-4)."""
    checked = require_prerequisites("ledger.merge", {"root": root, "world": world, "role": role})
    if is_refusal(checked):
        return checked
    return read_merge_view(root, world=world, role=role)


def invoke_ledger_bar(
    *,
    root: object = None,
    world: object = None,
) -> Result[tuple[LedgerLine, ...]]:
    """Book-bar read: confirmation lines only (B-4)."""
    checked = require_prerequisites("ledger.bar", {"root": root, "world": world})
    if is_refusal(checked):
        return checked
    return read_book_bar(root, world=world)


def _present(value: object) -> bool:
    if value is None:
        return False
    return not (isinstance(value, str) and value.strip() == "")


def _as_compiler(compiler: object) -> Result[_CompileFn]:
    if compiler is None:
        return Ok(compile_run_config)
    if not callable(compiler):
        return invalid(
            "compiler",
            "a backtest compiles through qmb.config.compile_run_config",
            given=repr(type(compiler).__name__),
        )
    return Ok(cast("_CompileFn", compiler))


def _as_orchestrator(orchestrator: object) -> Result[_OrchFn]:
    if orchestrator is None:
        return Ok(spawn_run)
    if not callable(orchestrator):
        return invalid(
            "orchestrator",
            "a backtest submits to qmb.orchestrator.spawn_run",
            given=repr(type(orchestrator).__name__),
        )
    return Ok(cast("_OrchFn", orchestrator))
