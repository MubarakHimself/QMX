"""Fixture builders for the Epic 16 (qmb CLI & doors) independent audit.

TEST SCAFFOLDING ONLY. These builders construct controlled inputs — a CT-04
refusal corpus, a resolved-run-config, a real B-15 registry universe, and
recording compiler/orchestrator seam spies — using the same public
construction API the shipped examples use. They assert NOTHING about
behaviour; the assertions live in the ``test_*`` modules and state what the
REQUIREMENT demands, never what the source happens to do. Source is read-only
evidence.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from qmf.core.chrono import Instant, WriterId
from qmf.core.fingerprint import Fingerprint, World, fingerprint
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Result,
    Retryability,
    TypedRefusal,
    is_ok,
)
from qmf.registry import RegistrationRecord

from qmb.config import ResolvedRunConfig
from qmb.orchestrator import IsolatedRun
from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, RegistryReadPort
from qmb.runloop import STREAM_SET_KEY

T = TypeVar("T")

# Repo root: qa-audit/qa/tests/epic_16/_e16.py -> parents[3] == worktree root.
ROOT = Path(__file__).resolve().parents[3]
QMB_SRC = ROOT / "qmb" / "src" / "qmb"
DOORS_SRC = QMB_SRC / "doors"
CLI_SRC = DOORS_SRC / "cli"
API_SRC = DOORS_SRC / "api"
MCP_SRC = DOORS_SRC / "mcp"

_NS = 1_700_000_000_000_000_000
SEVERITY = "workspace-declared"


def unwrap(result: Result[T], what: str = "value") -> T:
    if is_ok(result):
        return result.value
    raise AssertionError(f"FIXTURE could not construct {what}: {result!r}")


def instant(ns: int = _NS) -> Instant:
    return unwrap(Instant.try_create(ns), "instant")


def writer(stream: str = "config-fragment") -> WriterId:
    return unwrap(WriterId.try_create("node-a", "authoring", stream, "boot-1"), "writer")


def stamp(tag: str) -> Fingerprint:
    return unwrap(fingerprint({"n": "epic16", "tag": tag}), f"fp1 {tag}")


# --- CT-04 refusal corpus ----------------------------------------------------
# Shape-faithful TypedRefusal values spanning all seven categories, context both
# empty-structured and populated (never null), and each retryability arm incl.
# after-condition WITH its descriptor. A test that passes against a
# shape-unfaithful fake is itself a finding (§6).


def refusal(
    category: RefusalCategory,
    retryability: Retryability = Retryability.NO,
    *,
    context: dict[str, object] | None = None,
    descriptor: str | None = None,
) -> TypedRefusal:
    return TypedRefusal(
        category=category,
        retryability=retryability,
        context={} if context is None else context,
        after_condition_descriptor=descriptor,
    )


def refusal_corpus() -> tuple[TypedRefusal, ...]:
    """All seven categories; empty and populated context; every retryability arm."""
    seven = tuple(RefusalCategory)
    out: list[TypedRefusal] = []
    # every category, retryability=no, populated context
    for cat in seven:
        out.append(
            refusal(cat, Retryability.NO, context={"field": "x", "reason": "why", "n": 3})
        )
    # empty-but-present context (never null)
    out.append(refusal(RefusalCategory.POLICY_REJECTION, Retryability.NO, context={}))
    # retryability = yes
    out.append(
        refusal(
            RefusalCategory.TRANSIENT_VENUE_FAILURE,
            Retryability.YES,
            context={"venue": "dukascopy"},
        )
    )
    # retryability = after-condition WITH descriptor + nested context
    out.append(
        refusal(
            RefusalCategory.TRANSIENT_VENUE_FAILURE,
            Retryability.AFTER_CONDITION,
            context={"probe": {"attempt": 2}, "streams": ["eurusd", "gbpusd"]},
            descriptor="retry after 2s",
        )
    )
    # stale evidence carrying a severity key (FM-7 shape)
    out.append(
        refusal(
            RefusalCategory.STALE_EVIDENCE,
            Retryability.NO,
            context={"severity": "workspace-declared", "current_head": "fp1:sha256:" + "a" * 64},
        )
    )
    return tuple(out)


SEVEN_CATEGORY_VALUES = frozenset(member.value for member in RefusalCategory)
RETRYABILITY_VALUES = frozenset(member.value for member in Retryability)


# --- resolved-run-config + isolated-run builders (backtest seam) -------------


def resolved_config(*, tag: str = "backtest") -> ResolvedRunConfig:
    fp = stamp(tag)
    return ResolvedRunConfig(
        format_version=1,
        book_fp1=fp,
        bms_fp1=fp,
        bot_fp1=fp,
        book_fragment_fp1=fp,
        bms_fragment_fp1=fp,
        keys={STREAM_SET_KEY: ("eurusd",)},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=fp,
        binding_fp1=fp,
    )


def isolated_run(config: ResolvedRunConfig, output_root: object) -> IsolatedRun:
    return IsolatedRun(
        run_id=config.fingerprint,
        output_dir=str(output_root),
        pid=0,
        worker_pid=0,
        ct32_fingerprint=None,
        outcome_identity={"submitted": True},
    )


@dataclass
class CompilerSpy:
    """Records the compile call and returns a canned Result — a test-owned seam."""

    config: ResolvedRunConfig
    result: Result[ResolvedRunConfig] | None = None
    calls: list[dict[str, object]] = field(default_factory=list)

    def __call__(self, port: object, **kwargs: object) -> Result[ResolvedRunConfig]:
        self.calls.append({"port": port, **kwargs})
        return self.result if self.result is not None else Ok(self.config)


@dataclass
class OrchestratorSpy:
    """Records what was submitted and returns a canned Result — a test-owned seam."""

    config: ResolvedRunConfig
    result: Result[IsolatedRun] | None = None
    calls: list[dict[str, object]] = field(default_factory=list)

    def __call__(
        self,
        *,
        config: object,
        slices: object,
        output_root: object,
        cancel: object = None,
        limits: object = None,
        probe: object = None,
    ) -> Result[IsolatedRun]:
        self.calls.append(
            {
                "config": config,
                "slices": slices,
                "output_root": output_root,
                "cancel": cancel,
                "limits": limits,
                "probe": probe,
            }
        )
        if self.result is not None:
            return self.result
        assert isinstance(config, ResolvedRunConfig)
        return Ok(isolated_run(config, output_root))


# --- real B-15 registry universe (autocomplete seam) -------------------------


def _record(kind: str, alias: str, *, seq: int = 0, ns: int = _NS) -> RegistrationRecord:
    return unwrap(
        RegistrationRecord.try_create(
            kind,
            1,
            [],
            {"class": kind, "alias": alias},
            writer(kind),
            seq,
            instant(ns),
        ),
        f"{kind} record {alias}",
    )


def _pointer(alias: str, target: Fingerprint, *, ns: int = _NS) -> DatedPointer:
    return unwrap(DatedPointer.try_create(alias, target, instant(ns)), f"pointer {alias}")


@dataclass(frozen=True, slots=True)
class Universe:
    hub: PassiveHub
    port: RegistryReadPort
    book_alias: str
    bot_alias: str
    bms_alias: str


def build_universe(
    *,
    book_alias: str = "scalping",
    bot_alias: str = "mean-reversion",
    bms_alias: str = "account-bms",
) -> Universe:
    """A real registry universe with one book/bot/bms record + dated pointers,
    reachable through the ONE library-owned B-15 registry-read port.
    """
    book = _record("book-definition", book_alias)
    bot = _record("bot-definition", bot_alias)
    bms = _record("bms-definition", bms_alias)
    as_of = unwrap(
        AsOfSet.try_create(
            instant(),
            records=(book, bot, bms),
            pointers=(
                _pointer(book_alias, book.stable_id),
                _pointer(bot_alias, bot.stable_id),
                _pointer(bms_alias, bms.stable_id),
            ),
        ),
        "as-of set",
    )
    hub = unwrap(PassiveHub.try_create((as_of,)), "hub")
    port = unwrap(
        RegistryReadPort.try_create(hub, stale_evidence_severity=SEVERITY),
        "registry-read port",
    )
    return Universe(hub=hub, port=port, book_alias=book_alias, bot_alias=bot_alias, bms_alias=bms_alias)


def universe_with_fresher_book(new_book_alias: str = "newbook") -> tuple[RegistryReadPort, RegistryReadPort, str]:
    """A stale port (as-of #1) and a fresher port (as-of #2 adds a NEW Book).

    Returns ``(stale_port, fresher_port, new_book_alias)``. The new Book reaches
    the fresher port as a fresher AS-OF SET — never a door cache refresh and
    never a live-service query (B-15). Both ports are library-owned; the door
    holds no cache of its own.
    """
    book = _record("book-definition", "scalping")
    bot = _record("bot-definition", "mean-reversion")
    as_of1 = unwrap(
        AsOfSet.try_create(
            instant(),
            records=(book, bot),
            pointers=(
                _pointer("scalping", book.stable_id),
                _pointer("mean-reversion", bot.stable_id),
            ),
        ),
        "as-of #1",
    )
    later_ns = _NS + 86_400_000_000_000  # one day later
    new_book = _record("book-definition", new_book_alias, seq=1, ns=later_ns)
    as_of2 = unwrap(
        AsOfSet.try_create(
            instant(later_ns),
            records=(book, bot, new_book),
            pointers=(
                _pointer("scalping", book.stable_id),
                _pointer("mean-reversion", bot.stable_id),
                _pointer(new_book_alias, new_book.stable_id, ns=later_ns),
            ),
        ),
        "as-of #2 (fresher)",
    )
    hub1 = unwrap(PassiveHub.try_create((as_of1,)), "hub #1")
    hub2 = unwrap(PassiveHub.try_create((as_of1, as_of2)), "hub #2")
    stale_port = unwrap(
        RegistryReadPort.try_create(hub1, stale_evidence_severity=SEVERITY), "stale port"
    )
    fresher_port = unwrap(
        RegistryReadPort.try_create(hub2, stale_evidence_severity=SEVERITY), "fresher port"
    )
    return stale_port, fresher_port, new_book_alias


# --- derived door-surface enumerators (parity mechanism, no hand-list) -------
# Both sides are COMPUTED here from the live door structure — the click command
# tree (CLI) and module introspection (API) — never a hand-maintained catalog.


def derive_cli_leaves(group: object) -> set[str]:
    """Walk a click Group to its leaves. Pure function of the tree structure.

    A subcommand of a subgroup is ``group.command``; a top-level leaf command
    is its bare name. No door constant is consulted.
    """
    import click

    leaves: set[str] = set()
    assert isinstance(group, click.Group)
    for name, command in group.commands.items():
        if isinstance(command, click.Group):
            for sub in command.commands:
                leaves.add(f"{name}.{sub}")
        else:
            leaves.add(name)
    return leaves


def _callback_calls(func: object) -> set[str]:
    """Names called (``foo(...)`` / ``x.foo(...)``) inside a python function's AST."""
    import inspect
    import textwrap

    src = textwrap.dedent(inspect.getsource(func))  # type: ignore[arg-type]
    tree = ast.parse(src)
    called: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name):
                called.add(fn.id)
            elif isinstance(fn, ast.Attribute):
                called.add(fn.attr)
    return called


def cli_capability_leaves() -> set[str]:
    """CLI leaves that route to the LIBRARY (call an ``invoke_*``), derived from
    the live click callbacks — adaptation-only leaves (e.g. ``version``) drop out
    because their callback calls no ``invoke_*``.
    """
    import click

    from qmb.doors.cli import main

    caps: set[str] = set()
    for name, command in main.commands.items():
        assert isinstance(command, click.Command)
        if isinstance(command, click.Group):
            for sub, subcmd in command.commands.items():
                calls = _callback_calls(subcmd.callback)
                if any(c.startswith("invoke_") for c in calls):
                    caps.add(f"{name}.{sub}")
        else:
            calls = _callback_calls(command.callback)
            if any(c.startswith("invoke_") for c in calls):
                caps.add(name)
    return caps


def _qmb_import_map_in_tree() -> dict[str, tuple[str, str]]:
    """Map each local name ``doors/cli/tree.py`` imports from ``qmb.*`` to
    ``(real_library_name, source_module)`` — so an alias like
    ``from qmb.data import download as run_download`` resolves to ``download``.
    """
    tree = ast.parse((CLI_SRC / "tree.py").read_text(encoding="utf-8"))
    out: dict[str, tuple[str, str]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("qmb"):
            for alias in node.names:
                local = alias.asname or alias.name
                out[local] = (alias.name, node.module)
    return out


def cli_library_calls() -> dict[str, tuple[str, str]]:
    """LIBRARY functions the CLI door adapts, derived from the AST of each
    ``invoke_*`` in ``doors/cli/tree.py`` (which qmb-imported names it calls).

    Returns ``{real_library_name: (local_name, source_module)}``. Aliases are
    resolved to their real library names. No ``CAPABILITY_LIBRARY`` catalog is
    consulted — both parity sides reconcile through THIS computed set.
    """
    import inspect
    import textwrap

    from qmb.doors.cli import tree as tree_mod

    import_map = _qmb_import_map_in_tree()
    out: dict[str, tuple[str, str]] = {}
    src = textwrap.dedent(inspect.getsource(tree_mod))
    module_tree = ast.parse(src)
    for node in ast.walk(module_tree):
        if isinstance(node, ast.FunctionDef) and node.name.startswith("invoke_"):
            for call in ast.walk(node):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                    local = call.func.id
                    if local in import_map:
                        real, module = import_map[local]
                        out[real] = (local, module)
    return out


def cli_capability_targets() -> set[str]:
    """Real library names the CLI door adapts, EXCLUDING private adaptation
    vocabulary (imports from ``qmb._*`` private modules such as ``_refuse``).

    This is the CLI door's product-capability surface projected onto the
    library — the set both doors must share (B-1).
    """
    return {
        real
        for real, (_local, module) in cli_library_calls().items()
        if not module.split(".")[-1].startswith("_")
    }


def api_library_surface() -> set[str]:
    """The API door's capability surface, COMPUTED by introspection: public names
    in ``api.__all__`` that are identity-equal to a ``qmb.<name>`` object.
    """
    import qmb
    from qmb.doors import api

    library = set(qmb.__all__)
    out: set[str] = set()
    for name in api.__all__:
        if name in library and hasattr(api, name) and hasattr(qmb, name):
            if getattr(api, name) is getattr(qmb, name):
                out.add(name)
    return out
