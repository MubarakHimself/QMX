"""Epic 16 — L2 component/integration (in-process, CliRunner + direct imports).

The T2 workhorse: each door wired to a stubbed library surface or a real B-15
port, driven through public surfaces only. Effects are observed through
test-owned recorders/spies/sinks; a returned flag is never trusted as proof.

Groups A (thin tree), B (CLI refusal rendering), C (Python re-export),
D (autocomplete through the port), F (MCP scaffold).
"""

from __future__ import annotations

import ast
import importlib
import json
from pathlib import Path

import _e16 as e
import click
import pytest
from click.testing import CliRunner

import qmb
from qmb.doors import api
from qmb.doors.cli import (
    invoke_backtest,
    invoke_config_show,
    invoke_ledger_merge,
    invoke_optimize_space,
    invoke_sweep_count,
    main,
    render_refusal,
)
from qmb.doors.cli import tree as cli_tree
from qmf.core.refusal import (
    Ok,
    RefusalCategory,
    Retryability,
    TypedRefusal,
    is_ok,
    is_refusal,
)

_REQUIRED_REFUSAL_KEYS = ("category", "context", "retryability")


def _cli_refusal_payload(result: object) -> dict[str, object]:
    """A rendered CLI refusal: nonzero exit, empty stdout, machine-readable stderr JSON."""
    assert result.exit_code != 0, result.output
    assert result.stdout.strip() == ""
    body = json.loads(result.stderr)
    assert isinstance(body, dict)
    for key in _REQUIRED_REFUSAL_KEYS:
        assert key in body
    return body


# ============================ Group A — thin tree ===========================


# --- T-16.1-b ----------------------------------------------------------------
def test_t16_1_b_each_capability_forwards_to_one_library_function(monkeypatch) -> None:
    """For each enumerated CLI capability, invoking it calls exactly ONE library
    pure function with the parsed args and returns its result unchanged (observed
    through a test-owned recorder replacing the library seam). [R1]"""
    sentinel = object()

    for target, invoke, kwargs, expect_arg in (
        ("preflight_run_count", lambda: invoke_sweep_count(declaration={"axis": 1}),
         {"declaration": {"axis": 1}}, "declaration"),
        ("read_merge_view", lambda: invoke_ledger_merge(root="r", world="w", role="role"),
         {"root": "r"}, "root"),
        ("parameter_space_from_bot", lambda: invoke_optimize_space(declaration={"d": 1}),
         {"declaration": {"d": 1}}, "declaration"),
        ("run_config_identity", lambda: invoke_config_show(), {}, None),
    ):
        calls: list[tuple[tuple, dict]] = []

        def recorder(*args, _calls=calls, **kw):
            _calls.append((args, kw))
            return Ok(sentinel) if target != "run_config_identity" else sentinel

        monkeypatch.setattr(cli_tree, target, recorder)
        result = invoke()
        assert len(calls) == 1, f"{target}: expected exactly one library call, got {len(calls)}"
        assert is_ok(result), f"{target}: {result!r}"
        assert result.value is sentinel, f"{target}: door did not forward the library result verbatim"
        if expect_arg == "declaration":
            assert calls[0][0][0] == kwargs["declaration"] or calls[0][1].get("declaration") == kwargs["declaration"]
        monkeypatch.undo()


# --- T-16.1-d ----------------------------------------------------------------
def test_t16_1_d_single_surface_capability_groups_enumerable() -> None:
    """The command tree exposes the platform's single command-line surface — the
    capability groups are present as click Groups and enumerable — with exactly
    one qmb entry point. [R3]"""
    assert isinstance(main, click.Group)
    assert main.name == "qmb"
    groups = {name for name, cmd in main.commands.items() if isinstance(cmd, click.Group)}
    for expected in ("backtest", "data", "optimize", "sweep", "ledger", "config"):
        assert expected in groups, f"missing capability group: {expected}"
    # every group is enumerable to leaves
    leaves = e.derive_cli_leaves(main)
    assert {"backtest.run", "data.download", "optimize.run", "ledger.merge", "config.compile"} <= leaves


# --- T-16.1-e ----------------------------------------------------------------
def test_t16_1_e_tunnel_command_missing_prereq_returns_typed_refusal() -> None:
    """A tunnel-running command whose config/resource prerequisite is absent
    RETURNS a CT-04 typed refusal naming the missing prerequisite and does NOT
    proceed to run (the compiler/orchestrator seams are never reached). [R4]"""
    compiler = e.CompilerSpy(config=e.resolved_config())
    orchestrator = e.OrchestratorSpy(config=e.resolved_config())
    # invoke-level: no prerequisites supplied
    refused = invoke_backtest(compiler=compiler, orchestrator=orchestrator)
    assert is_refusal(refused)
    assert isinstance(refused, TypedRefusal)
    assert refused.category is RefusalCategory.UNAVAILABLE_DEPENDENCY
    missing = refused.context.get("missing")
    assert missing and "port" in missing and "book_fragment" in missing
    # it did NOT proceed to run: neither seam was reached
    assert compiler.calls == []
    assert orchestrator.calls == []
    # CLI-level: same, rendered per transport
    runner = CliRunner()
    clicked = runner.invoke(main, ["backtest", "run"])
    payload = _cli_refusal_payload(clicked)
    assert payload["category"] == RefusalCategory.UNAVAILABLE_DEPENDENCY.value


# ====================== Group B — CLI refusal rendering =====================


# --- T-16.2-a ----------------------------------------------------------------
def test_t16_2_a_library_refusal_renders_nonzero_exit_and_stderr_json() -> None:
    """A library-returned CT-04 refusal renders at the CLI as a nonzero exit code
    AND machine-readable stderr JSON carrying {category, context, retryability},
    tied to the SPECIFIC library refusal injected. [R6]"""
    chosen = e.refusal(
        RefusalCategory.POLICY_REJECTION,
        Retryability.NO,
        context={"field": "world", "reason": "simulated is reserved-unusable"},
    )
    compiler = e.CompilerSpy(config=e.resolved_config(), result=chosen)
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["backtest", "run", "mean-reversion", "--output-root", "out"],
        obj={
            "port": 1, "book_fragment": 1, "bms_fragment": 1,
            "slices": (("eurusd",),), "compiler": compiler,
            "orchestrator": e.OrchestratorSpy(config=e.resolved_config()),
        },
    )
    payload = _cli_refusal_payload(clicked)
    assert payload["category"] == chosen.category.value
    assert payload["retryability"] == chosen.retryability.value
    assert payload["context"]["field"] == "world"
    assert payload == json.loads(render_refusal(chosen))


# --- T-16.2-b ----------------------------------------------------------------
def test_t16_2_b_refusal_is_returned_and_rendered_never_raised_never_swallowed() -> None:
    """A typed refusal is RETURNED by the library and RENDERED by the door: no
    exception crosses the door boundary, and the refusal is never swallowed to a
    zero exit. [R7]"""
    chosen = e.refusal(RefusalCategory.INVALID_INPUT, context={"field": "run_spec"})
    compiler = e.CompilerSpy(config=e.resolved_config(), result=chosen)
    obj = {
        "port": 1, "book_fragment": 1, "bms_fragment": 1,
        "slices": (("eurusd",),), "compiler": compiler,
        "orchestrator": e.OrchestratorSpy(config=e.resolved_config()),
    }
    runner = CliRunner()
    # catch_exceptions=False: a raised (not returned) refusal would propagate here
    clicked = runner.invoke(
        main, ["backtest", "run", "b", "--output-root", "out"], obj=obj, catch_exceptions=False
    )
    assert clicked.exit_code != 0          # not swallowed to zero
    assert clicked.exception is None or isinstance(clicked.exception, SystemExit)
    assert json.loads(clicked.stderr)["category"] == chosen.category.value
    # invoke-level: the door returns the refusal, it does not raise
    returned = invoke_backtest(
        port=1, book_fragment=1, bms_fragment=1, run_spec={"bot": "b"},
        slices=(("eurusd",),), output_root="out",
        compiler=e.CompilerSpy(config=e.resolved_config(), result=chosen),
        orchestrator=e.OrchestratorSpy(config=e.resolved_config()),
    )
    assert returned == chosen


# --- T-16.2-c ----------------------------------------------------------------
def test_t16_2_c_successful_run_exits_zero_no_stderr_refusal() -> None:
    """A successful run exits zero with no stderr refusal JSON. [R8]"""
    config = e.resolved_config(tag="ok")
    runner = CliRunner()
    clicked = runner.invoke(
        main,
        ["backtest", "run", "mean-reversion", "--output-root", "out"],
        obj={
            "port": 1, "book_fragment": 1, "bms_fragment": 1,
            "slices": (("eurusd",),),
            "compiler": e.CompilerSpy(config=config),
            "orchestrator": e.OrchestratorSpy(config=config),
        },
    )
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stderr.strip() == ""
    assert clicked.stdout.strip() == config.fingerprint.value


# --- T-16.2-d ----------------------------------------------------------------
def test_t16_2_d_programmer_error_is_exception_distinct_from_refusal_channel() -> None:
    """A programmer error (not a typed refusal) surfaces as an EXCEPTION on a
    channel distinct from the refusal channel — never rendered as a CT-04 stderr
    JSON refusal. [R9]"""
    # the refusal renderer only accepts a TypedRefusal; a programmer error (a
    # non-refusal object) raises rather than producing a CT-04 refusal document
    with pytest.raises((AttributeError, TypeError)):
        render_refusal(object())  # type: ignore[arg-type]
    # a wrong-arity library call raises TypeError (programmer error), not a refusal
    with pytest.raises(TypeError):
        api.identity_payload("nope")  # type: ignore[call-arg]


# ===================== Group C — Python API re-export =======================


# --- T-16.3-a ----------------------------------------------------------------
def test_t16_3_a_api_names_resolve_to_library_pure_functions() -> None:
    """The Python API door's public names resolve to the library's OWN pure
    functions (identity/alias, not door re-implementations), importable from the
    uv-added qmb package. [R10]"""
    loaded = importlib.import_module("qmb.doors.api")
    assert loaded is api
    # every public-surface capability the CLI adapts is identity-equal on the API door
    for name in sorted(c for c in e.cli_capability_targets() if c in qmb.__all__):
        assert hasattr(api, name), f"API door missing library capability {name}"
        assert getattr(api, name) is getattr(qmb, name), f"{name}: not the library object"
        assert name in api.__all__ and name in qmb.__all__


# --- T-16.3-d ----------------------------------------------------------------
def test_t16_3_d_research_call_path_writes_no_governed_evidence(tmp_path: Path) -> None:
    """A door-routed library call on the research path returns values and writes
    NO governed evidence — observed by the filesystem sink (no ledger line). [R13]"""

    def _obs(stream_id: str):
        inst = e.instant()
        return e.unwrap(api.SliceObservation.try_create(stream_id, inst, True), "obs")

    outcome = api.run(
        slices=((_obs("eurusd"),),),
        stream_set=("eurusd",),
        handler=api.SilentSliceHandler(),
    )
    assert is_ok(outcome)
    assert list(tmp_path.rglob("*.jsonl")) == []
    sink = e.unwrap(
        api.LedgerSink.try_create(
            tmp_path / "ledger", machine="api-door", worker_slot=0, boot_epoch_id="boot-1"
        ),
        "ledger sink",
    )
    from qmf.core.fingerprint import World

    merged = e.unwrap(api.read_merge_view(sink.root, world=World.REPLAY, role=api.ROLE_CONFIRMATION))
    assert merged == ()


# ================== Group D — autocomplete through the port =================


# --- T-16.4-a ----------------------------------------------------------------
def test_t16_4_a_autocomplete_routes_through_the_one_port_no_door_cache() -> None:
    """Autocomplete enumerates through the single library-owned registry-read
    port: the door returns exactly the port's candidates, and a non-port yields
    nothing — never a door-side cache or a live-service query. [R14]"""
    u = e.build_universe()
    for prefix, kind in (("", "book-definition"), ("mean", "bot-definition"), ("", None)):
        door = cli_tree.complete_registry(u.port, prefix, kind=kind)
        direct = u.port.complete(prefix, kind=kind)
        assert door == direct, (prefix, kind)
    # a non-port consults no second store / live service
    assert cli_tree.complete_registry(object(), "scalp", kind="book-definition") == ()
    assert cli_tree.complete_registry(None, "") == ()


# --- T-16.4-b ----------------------------------------------------------------
def test_t16_4_b_autocomplete_and_resolution_cannot_answer_differently() -> None:
    """Every candidate autocomplete offers, resolution accepts through the SAME
    port to the SAME fp1 — one port over one as-of set, never divergent. [R15]"""
    u = e.build_universe()
    candidates = cli_tree.complete_registry(u.port, "", kind=None)
    assert candidates, "port offered no candidates"
    for cand in candidates:
        resolved = u.port.resolve(cand.value)
        assert is_ok(resolved), f"autocomplete offered {cand.value!r} that resolution rejects"
        assert resolved.value.fingerprint == cand.fingerprint


# --- T-16.4-c ----------------------------------------------------------------
def test_t16_4_c_new_book_arrives_as_fresher_as_of_not_door_cache() -> None:
    """A newly created Book reaches the CLI as a FRESHER as-of set — not a door
    cache refresh and not a live query: the door reflects whichever library port
    it is given, holding no cache of its own. [R16]"""
    stale_port, fresher_port, new_book = e.universe_with_fresher_book()
    stale = cli_tree.complete_registry(stale_port, new_book, kind="book-definition")
    assert [c.value for c in stale] == []          # not yet in the older as-of
    fresher = cli_tree.complete_registry(fresher_port, new_book, kind="book-definition")
    assert new_book in [c.value for c in fresher]   # visible via the fresher as-of
    # no door-side memo pins the first answer: re-querying the stale port is still empty
    assert cli_tree.complete_registry(stale_port, new_book, kind="book-definition") == ()


# --- T-16.4-d ----------------------------------------------------------------
def test_t16_4_d_autocomplete_uses_click_native_completion_over_the_port() -> None:
    """Autocomplete uses click's native shell-completion hook and adds no bespoke
    completion machinery; invoking a registry param's completion over a context
    carrying the port routes to the port. [R17]"""
    u = e.build_universe()
    run_cmd = main.commands["backtest"].commands["run"]
    params = {p.name: p for p in run_cmd.params}
    assert "bot" in params
    ctx = click.Context(main, obj={"port": u.port})
    # click-native completion: Parameter.shell_complete routes to the custom hook
    items = params["bot"].shell_complete(ctx, "")
    values = {getattr(it, "value", it) for it in items}
    assert u.bot_alias in values, values
    # each completion cites fp1, never name@version (port-supplied identity)
    for it in items:
        assert getattr(it, "help", "").startswith("fp1:sha256:")
    # no bespoke completion class is defined anywhere in the CLI door
    for path in sorted((e.CLI_SRC).rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                assert "Completion" not in node.name, f"bespoke completion class {node.name}"


# ======================= Group F — MCP door scaffold ========================


# --- T-16.6-a ----------------------------------------------------------------
def test_t16_6_a_mcp_scaffolded_not_shipped_invocation_refused() -> None:
    """doors/mcp is present as a sibling wrapper over the same library, and
    invoking it as a shipped door is REFUSED (unsupported capability); it is not
    in the shipped door-set and not a console script. [R22]"""
    from qmb.doors import mcp

    refused = mcp.main()
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    served = mcp.serve()
    assert is_refusal(served) and served == refused
    # not a shipped door / not a console script (real manifest, not a self-declared flag)
    import tomllib

    manifest = tomllib.loads((e.ROOT / "qmb" / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = manifest["project"].get("scripts", {})
    assert all("mcp" not in name for name in scripts)
    assert "mcp" not in qmb.__all__


# --- T-16.6-c ----------------------------------------------------------------
def test_t16_6_c_cli_v1_usable_without_mcp_and_does_not_depend_on_it() -> None:
    """CLI v1 ships first and the MCP door does not gate it: the CLI surface is
    complete and usable with doors/mcp unshipped, and no CLI module imports the
    MCP door. [R25]"""
    runner = CliRunner()
    shown = runner.invoke(main, ["config", "show"])
    assert shown.exit_code == 0, shown.output
    # no CLI door module imports qmb.doors.mcp
    for path in sorted(e.CLI_SRC.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "doors.mcp" not in node.module, f"{path.name} imports the MCP door"
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "doors.mcp" not in alias.name
