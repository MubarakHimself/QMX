"""Epic 13 — L4 property / invariant / golden-scenario tests (T13-401..406).

Universally-quantified identity laws (R-004, R-008, AD-10, disjointness, P0-13
config-side) via hypothesis, plus the SCN-0012 identity chain. Run with:
``uv run --with hypothesis pytest qa/tests/epic_13 -q``. A failing assertion is
a FINDING.
"""

from __future__ import annotations

import pytest
from hypothesis import assume, given, settings
from hypothesis import strategies as st
from qmf.core.exact import Money
from qmf.core.refusal import is_ok, is_refusal

from _fixtures import DEFAULTS, SEED, base_run_spec, build_universe, unwrap, writer
from qmb.config import (
    BMS_NAMESPACES,
    BOOK_NAMESPACES,
    LAYER_PRECEDENCE,
    ResolvedRunConfig,
    compile_run_config,
    materialize_condition_preset,
    merge_book_bms_keys,
)

# Build the fixture universe once; property examples vary only the layers.
U = build_universe()
DET = settings(max_examples=30, deadline=None, derandomize=True)


def _compile(run_spec, **over):
    kwargs = dict(
        book_fragment=U.book_fragment,
        bms_fragment=U.bms_fragment,
        run_spec=run_spec,
        workspace_defaults=dict(DEFAULTS),
    )
    kwargs.update(over)
    return compile_run_config(U.port, **kwargs)


def _fp(run_spec, **over):
    return unwrap(_compile(run_spec, **over), "compile").fingerprint


# --- T13-401 [R-004] ---------------------------------------------------------
@DET
@given(h1=st.integers(min_value=-10_000, max_value=10_000),
       h2=st.integers(min_value=-10_000, max_value=10_000))
def test_t13_401_distinct_identity_inputs_distinct_fp1(h1: int, h2: int) -> None:
    """Distinct semantic inputs ⇒ distinct config fp1: a change to an identity-classified
    field (here the run-spec horizon) changes the run identity. (13.4 AC4)"""
    assume(h1 != h2)
    fp1 = _fp({"bot": "mean-reversion", "horizon": h1, "starting_capital": SEED})
    fp2 = _fp({"bot": "mean-reversion", "horizon": h2, "starting_capital": SEED})
    assert fp1 != fp2


@DET
@given(a=st.integers(min_value=1, max_value=5_000_000),
       b=st.integers(min_value=1, max_value=5_000_000))
def test_t13_401b_distinct_seed_distinct_fp1(a: int, b: int) -> None:
    """A change to the starting_capital seed (an identity input) moves the run id."""
    assume(a != b)
    fp_a = _fp(base_run_spec(seed=Money(value=a, currency="USD", scale=2)))
    fp_b = _fp(base_run_spec(seed=Money(value=b, currency="USD", scale=2)))
    assert fp_a != fp_b


def test_t13_401c_world_and_bot_change_move_identity() -> None:
    """Provenance-derived world and the cited bot are identity fields."""
    base = _fp(base_run_spec())
    # a different world (simulated via synthetic clock+provenance) is a distinct identity
    sim = _fp(
        {"bot": "mean-reversion", "starting_capital": SEED},
        workspace_defaults={
            "account_id": "acct-replay",
            "venue_id": "venue-replay",
            "clock": "simulated",
            "data_provenance": "synthetic-tainted",
        },
    )
    assert sim != base
    # a different bot is a distinct identity
    other = build_universe(bot_alias="momentum")
    other_fp = unwrap(
        compile_run_config(
            other.port,
            book_fragment=other.book_fragment,
            bms_fragment=other.bms_fragment,
            run_spec={"bot": "momentum", "horizon": 5, "starting_capital": SEED},
            workspace_defaults=dict(DEFAULTS),
        ),
        "other-bot compile",
    ).fingerprint
    assert other_fp != base


# --- T13-402 [R-004 converse / NFR-03] ---------------------------------------
@DET
@given(h=st.integers(min_value=-10_000, max_value=10_000))
def test_t13_402_identical_inputs_byte_identical(h: int) -> None:
    """Identical inputs ⇒ byte-identical resolved artifact / equal fp1; layering is pure
    with no ambient nondeterminism. (13.4 AC1)"""
    spec = {"bot": "mean-reversion", "horizon": h, "starting_capital": SEED}
    one = unwrap(_compile(spec), "one")
    two = unwrap(_compile(spec), "two")
    assert one.fingerprint == two.fingerprint
    assert unwrap(one.artifact_bytes(), "b1") == unwrap(two.artifact_bytes(), "b2")
    # determinism across a freshly constructed universe (no shared mutable state)
    fresh = build_universe()
    three = unwrap(
        compile_run_config(
            fresh.port,
            book_fragment=fresh.book_fragment,
            bms_fragment=fresh.bms_fragment,
            run_spec=spec,
            workspace_defaults=dict(DEFAULTS),
        ),
        "three",
    )
    assert three.fingerprint == one.fingerprint


# --- T13-403 [R-008] ---------------------------------------------------------
def test_t13_403_input_shape_invariance_one_fp_one_verdict() -> None:
    """Semantically-equal input encodings — alias vs fp1, object-key ordering, CT-01
    canonical exact-rational forms — yield ONE resolved fp1 AND one accept verdict.
    (13.4 AC1/AC3) [R-008]"""
    # 1) alias vs fp1 for the bot cite
    by_alias = _compile(base_run_spec(bot_ref="mean-reversion"))
    by_fp1 = _compile(base_run_spec(bot_ref=U.bot.stable_id))
    assert is_ok(by_alias) and is_ok(by_fp1)  # one verdict: both accept
    assert by_alias.value.fingerprint == by_fp1.value.fingerprint

    # 2) object-key ordering of the run spec
    order_a = _compile({"bot": "mean-reversion", "horizon": 5, "starting_capital": SEED})
    order_b = _compile({"starting_capital": SEED, "horizon": 5, "bot": "mean-reversion"})
    assert is_ok(order_a) and is_ok(order_b)
    assert order_a.value.fingerprint == order_b.value.fingerprint

    # 3) CT-01 canonical exact-rational forms of the seed: $10,000 at two input scales,
    #    and as a Money object vs its fp1 identity mapping
    seed_scale2 = Money(value=1_000_000, currency="USD", scale=2)
    seed_scale4 = Money(value=100_000_000, currency="USD", scale=4)
    seed_mapping = seed_scale2.fp1_identity()
    fps = {
        _fp(base_run_spec(seed=seed_scale2)),
        _fp(base_run_spec(seed=seed_scale4)),
        _fp(base_run_spec(seed=seed_mapping)),
    }
    assert len(fps) == 1, f"CT-01 canonical forms forked identity: {fps}"


# --- T13-404 [AD-10] ---------------------------------------------------------
def test_t13_404_display_change_no_fp_identity_change_moves_fp() -> None:
    """A display-only field change produces NO fp1 change; an identity-field change DOES.
    (13.4 AC4)"""
    alias_cfg = unwrap(_compile(base_run_spec(bot_ref="mean-reversion")), "alias")
    fp1_cfg = unwrap(_compile(base_run_spec(bot_ref=U.bot.stable_id)), "fp1")
    # display differs (bot_alias present vs absent) ...
    assert alias_cfg.display.get("bot_alias") == "mean-reversion"
    assert "bot_alias" not in fp1_cfg.display
    # ... but the fp1 identity does NOT move on a display-only difference
    assert alias_cfg.fingerprint == fp1_cfg.fingerprint
    # an identity-field change (horizon) DOES move the fp1
    moved = _fp({"bot": "mean-reversion", "horizon": 6, "starting_capital": SEED})
    assert moved != alias_cfg.fingerprint


# --- T13-405 [disjointness, hot-spot] ----------------------------------------
def test_t13_405_book_bms_namespaces_disjoint_owner_resolved() -> None:
    """Book-fragment key namespace ∩ BMS-fragment key namespace = ∅ over the full declared
    surface; each declared key resolves to its owner domain. (13.3 AC3)"""
    assert BOOK_NAMESPACES.isdisjoint(BMS_NAMESPACES)
    assert BOOK_NAMESPACES == frozenset({"admission", "sizing", "exit-door"})
    assert BMS_NAMESPACES == frozenset({"accounting", "constraints", "kill-line", "reporting"})
    # the actual materialized fragments obey the ownership
    assert set(U.book_fragment.keys) <= BOOK_NAMESPACES
    assert set(U.bms_fragment.keys) <= BMS_NAMESPACES
    assert set(U.book_fragment.keys).isdisjoint(set(U.bms_fragment.keys))
    # the real disjoint pair merges cleanly (no collision)
    assert is_ok(merge_book_bms_keys(U.book_fragment.keys, U.bms_fragment.keys))
    # a fragment that MIXES the two owner domains is refused
    mixed = materialize_condition_preset(
        U.port,
        "scalping",
        writer("config-fragment"),
        name="mixed",
        keys={"admission": {"x": 1}, "accounting": {"y": 2}},
    )
    assert is_refusal(mixed)

    # every declared key resolves to exactly one owner domain
    for key in BOOK_NAMESPACES | BMS_NAMESPACES:
        owners = [key in BOOK_NAMESPACES, key in BMS_NAMESPACES]
        assert owners.count(True) == 1, f"{key} is not owned by exactly one domain"


# --- T13-406 [P0-13, config-side] --------------------------------------------
def test_t13_406_run_id_reproduces_or_refuses() -> None:
    """Re-resolving a run id under its stored resolved config reproduces the SAME config
    fp1 (the run-id root), or returns a typed refusal on mismatch. (NFR-03 / P0-13)"""
    config = unwrap(_compile(base_run_spec()), "compile")
    stored = config.fp1_identity()
    # reproduction: the stored resolved config re-derives the same run-id root
    reproduced = unwrap(ResolvedRunConfig.try_read(stored), "reproduce")
    assert reproduced.fingerprint == config.fingerprint == config.run_id

    # a tampered identity field does NOT silently reproduce the original run id
    tampered = dict(stored)
    tampered_keys = dict(tampered["keys"])
    tampered_keys["horizon"] = 999
    tampered["keys"] = tampered_keys
    tampered_read = ResolvedRunConfig.try_read(tampered)
    assert is_ok(tampered_read)  # still a well-formed config ...
    assert tampered_read.value.fingerprint != config.fingerprint  # ... but a DIFFERENT run id

    # a structurally-inconsistent stored identity is a typed refusal, never a best-effort id
    broken = dict(stored)
    broken["layer_precedence"] = list(reversed(LAYER_PRECEDENCE))
    broken_read = ResolvedRunConfig.try_read(broken)
    assert is_refusal(broken_read)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
