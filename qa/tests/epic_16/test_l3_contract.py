"""Epic 16 — L3 contract conformance (the T2 workhorse).

The compiler/orchestrator submit seam, the Python refusal-verbatim contract, and
the door-parity contract — DERIVED from both door surfaces with no hand-maintained
capability map (R-006). The parity test is proven able to FAIL on real drift.

Tests: T-16.1-f [R5] · T-16.3-b [R11] · T-16.5-a [R18] · T-16.5-b [R19]
       · T-16.5-c [R20] · T-16.5-d [R21] · T-16.5-map [R18 method / R-006 FINDING]
       · T-16.5-gap [R18/R19 surface FINDING].
"""

from __future__ import annotations

import ast
import json

import _e16 as e
from click.testing import CliRunner

import qmb
from qmb.doors import api
from qmb.doors.cli import (
    BacktestSubmission,
    invoke_backtest,
    invoke_optimize_space,
    main,
    render_refusal,
)
from qmf.core.refusal import RefusalCategory, TypedRefusal, is_ok, is_refusal


# --- T-16.1-f ----------------------------------------------------------------
def test_t16_1_f_backtest_compiles_and_submits_minting_no_run_id() -> None:
    """A backtest compiles the run-config via the Epic-13 compiler seam and
    submits the resolved config to the orchestrator seam; the run identity is the
    compiler's resolved-config fp1 and the door mints NO run-id of its own. [R5]"""
    config = e.resolved_config(tag="submit-seam")
    distinctive = config.fingerprint.value
    compiler = e.CompilerSpy(config=config)
    orchestrator = e.OrchestratorSpy(config=config)
    result = invoke_backtest(
        port=1, book_fragment=1, bms_fragment=1, run_spec={"bot": "mean-reversion"},
        slices=(("eurusd",),), output_root="out",
        compiler=compiler, orchestrator=orchestrator,
    )
    assert is_ok(result), result
    submission = result.value
    assert isinstance(submission, BacktestSubmission)
    # the compiler seam was reached with the parsed inputs
    assert len(compiler.calls) == 1
    assert compiler.calls[0]["run_spec"] == {"bot": "mean-reversion"}
    # the orchestrator seam was submitted exactly the compiled config
    assert len(orchestrator.calls) == 1
    assert orchestrator.calls[0]["config"] is config
    # the run-id IS the compiler's fp1 — the door derived no identity of its own
    assert submission.run_id == config.fingerprint
    assert submission.run_id.value == distinctive
    # the CLI transport prints exactly that fingerprint
    runner = CliRunner()
    clicked = runner.invoke(
        main, ["backtest", "run", "mean-reversion", "--output-root", "out"],
        obj={"port": 1, "book_fragment": 1, "bms_fragment": 1, "slices": (("eurusd",),),
             "compiler": e.CompilerSpy(config=config), "orchestrator": e.OrchestratorSpy(config=config)},
    )
    assert clicked.exit_code == 0, clicked.output
    assert clicked.stdout.strip() == distinctive


# --- T-16.3-b ----------------------------------------------------------------
def test_t16_3_b_python_door_returns_refusal_union_verbatim() -> None:
    """A refusal returned through the Python door is the library's refusal union
    VERBATIM — returned not raised; exceptions only for programmer error. [R11]"""
    # the Python door is the library object itself (pure re-export)
    assert api.parameter_space_from_bot is qmb.parameter_space_from_bot
    refusal = api.parameter_space_from_bot({"not": "a-bot"})  # returned, not raised
    assert is_refusal(refusal)
    assert isinstance(refusal, TypedRefusal)
    # the same underlying library refusal, reached via the CLI door invoker, is equal
    via_cli = invoke_optimize_space(declaration={"not": "a-bot"})
    assert via_cli == refusal
    # and the CLI transport renders that same refusal's fields verbatim
    rendered = json.loads(render_refusal(refusal))
    assert rendered["category"] == refusal.category.value
    assert rendered["retryability"] == refusal.retryability.value


# --- T-16.5-a  (FLAGSHIP: derived-both-sides parity, no hand-maintained map) --
def test_t16_5_a_derived_parity_public_capabilities_identical_across_doors() -> None:
    """The CLI door's public-surface capabilities (derived by walking the click
    tree + AST of the invoke_* adapters) are each identity-equal on the Python API
    door's surface (derived by module introspection). Both sides COMPUTED,
    reconciled through the library — zero hand-maintained expected-capability map. [R18]
    """
    cli_leaves = e.cli_capability_leaves()          # from the live click tree
    assert cli_leaves, "no CLI capability leaves derived"
    cli_caps = {c for c in e.cli_capability_targets() if c in qmb.__all__}
    assert cli_caps, "no public CLI capability targets derived"
    api_caps = e.api_library_surface()              # from API-door introspection
    assert api_caps, "no API capabilities derived"
    missing = sorted(c for c in cli_caps if c not in api_caps)
    assert missing == [], f"public capabilities on the CLI door absent from the Python door: {missing}"
    for name in cli_caps:
        assert getattr(api, name) is getattr(qmb, name), f"{name}: not identity-equal across doors"


# --- T-16.5-b  (parity has teeth: fault injection) ---------------------------
def test_t16_5_b_parity_fails_on_injected_divergence() -> None:
    """A capability present in one door's derived surface but absent/divergent in
    the other makes the computed sets diverge and the parity check FAIL — proving
    the parity test is not decorative. The divergence is injected into TEST-OWNED
    inputs, never into source. [R19]"""

    def parity_gaps(cli_caps: set[str], api_caps: set[str]) -> dict[str, tuple[str, ...]]:
        return {
            "cli_only": tuple(sorted(cli_caps - api_caps)),
            "api_only": tuple(sorted(api_caps - cli_caps)),
        }

    base = {c for c in e.cli_capability_targets() if c in qmb.__all__}
    api_caps = e.api_library_surface()
    # aligned today for the public surface
    assert parity_gaps(base, base & api_caps) == {"cli_only": (), "api_only": ()}
    # inject: a capability dropped from the API door's derived surface -> FAILS
    dropped = next(iter(base))
    injured = parity_gaps(base, (base & api_caps) - {dropped})
    assert injured["cli_only"] == (dropped,)
    # inject: a phantom capability added to one door -> FAILS
    phantom = parity_gaps(base | {"phantom.capability"}, base)
    assert phantom["cli_only"] == ("phantom.capability",)


# --- T-16.5-c ----------------------------------------------------------------
def test_t16_5_c_parity_ranges_over_real_capabilities_landed_by_epic14() -> None:
    """The parity population is the real, currently-exposed door surface (derived,
    non-empty) and includes the Epic-14/15 run-loop capabilities the doors front
    (bounded to what both doors actually expose — §7). [R20]"""
    surface = e.api_library_surface()
    for landed in ("run", "spawn_run", "compile_run_config"):
        assert landed in surface, f"{landed} not on the derived API surface"
        assert getattr(api, landed) is getattr(qmb, landed)
    # the CLI adapts a non-empty subset of that real surface (not a frozen list)
    assert {c for c in e.cli_capability_targets() if c in qmb.__all__}


# --- T-16.5-d ----------------------------------------------------------------
def test_t16_5_d_per_transport_refusal_parity_same_library_refusal() -> None:
    """For the SAME library-returned refusal, the CLI renders nonzero exit +
    stderr JSON and the Python door returns the refusal union verbatim — the two
    transports carry identical CT-04 semantics. [R21]"""
    declaration = {"not": "a-bot"}
    library_refusal = api.parameter_space_from_bot(declaration)   # ONE library refusal
    assert is_refusal(library_refusal)
    # Python transport: the union verbatim
    assert invoke_optimize_space(declaration=declaration) == library_refusal
    # CLI transport: nonzero exit + stderr JSON carrying the identical union
    runner = CliRunner()
    clicked = runner.invoke(main, ["optimize", "space"], obj={"declaration": declaration})
    assert clicked.exit_code != 0
    assert clicked.stdout.strip() == ""
    assert json.loads(clicked.stderr) == json.loads(render_refusal(library_refusal))


# --- T-16.5-map  (FINDING: parity is anchored on a hand-maintained map) ------
def _module_level_capability_map(path) -> list[str]:
    """Module-level assignments whose value is a str->collection-of-str mapping
    literal (unwrapping MappingProxyType(...)) — a hand-maintained capability
    catalog. R-006 forbids anchoring parity on such a map."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: list[str] = []
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if value is None:
            continue
        if (
            isinstance(value, ast.Call)
            and isinstance(value.func, ast.Name)
            and value.func.id == "MappingProxyType"
            and value.args
        ):
            value = value.args[0]
        if not isinstance(value, ast.Dict):
            continue
        keys = value.keys
        vals = value.values
        str_keys = sum(1 for k in keys if isinstance(k, ast.Constant) and isinstance(k.value, str))
        collection_vals = sum(
            1 for v in vals if isinstance(v, (ast.Tuple, ast.List, ast.Set))
        )
        if str_keys >= 3 and collection_vals >= 3:
            names = (
                [t.id for t in node.targets if isinstance(t, ast.Name)]
                if isinstance(node, ast.Assign)
                else [node.target.id] if isinstance(node.target, ast.Name) else []
            )
            found.append(",".join(names) or "?")
    return found


def test_t16_5_map_parity_is_derived_not_a_hand_maintained_map() -> None:
    """R-006 / R18 method clause: door parity must be DERIVED from the door
    surfaces, never asserted from a hand-maintained capability->library map. This
    asserts the shipped parity module carries no such hand-authored catalog.

    A failure is a FINDING: the shipped parity is anchored on a hand-maintained
    map (masking real surface asymmetries), contravening R-006."""
    parity_src = e.DOORS_SRC / "parity.py"
    hand_maps = _module_level_capability_map(parity_src)
    assert hand_maps == [], (
        "shipped parity anchored on hand-maintained capability map(s): "
        + ", ".join(hand_maps)
        + " — R-006 requires both door surfaces be DERIVED and reconciled, never a hand-list"
    )


# --- T-16.5-gap  (FINDING: a CLI capability absent from the Python door) -----
def test_t16_5_gap_every_cli_capability_is_reachable_on_the_python_door() -> None:
    """R18/R19: an identical function surface across doors — no capability
    reachable via the CLI door may be absent from the Python API door.

    A failure is a FINDING: a capability the CLI door adapts is not reachable
    through the pure-re-export Python door."""
    api_caps = e.api_library_surface()
    cli_caps = e.cli_capability_targets()   # excludes private _refuse adaptation vocab
    absent = sorted(c for c in cli_caps if c not in api_caps)
    assert absent == [], (
        "capabilities reachable via the CLI door but ABSENT from the Python API door: "
        + ", ".join(absent)
    )
