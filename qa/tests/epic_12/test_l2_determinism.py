"""L2 — determinism, host-independence, denial-set, ticket-scope invariants.

- E12-L2-01 (P0): identical (declaration, assignment, evidence, state) -> identical intents. (B-2)
- E12-L2-02 (P0): the same bot's verdict is host-independent by construction. (QL-8)
- E12-L2-03 (P0): differing golden-slice intents / a non-permitted kind -> Layer-2 failure. (FM-5)
- E12-L2-06 (P0): a clock/fs/network/undeclared-random use is a scan finding before any spawn. (Story 12.5)
- E12-L2-13 (P0): technical-never-performance, ticket-scope — no complexity gate; citation+seats only. (P0-Q2)

Effects are observed through the TEST's own comparisons and crafted observations,
never the SUT's self-report as sole witness.
"""

from __future__ import annotations

import dataclasses

import _world as w
from qmf.core.chrono import Instant
from qmf.core.refusal import Ok, RefusalCategory, is_ok, is_refusal
from qml.conformance import (
    DROPPED_REGISTRATION_GATES,
    Layer2Observations,
    ScanFinding,
    ScanReport,
    admit_ungoverned_tunnel,
    cite_registered_bot,
    cite_ungoverned_bot,
    collect_layer2_observations,
    drive_golden_slice,
    evaluate_layer2,
    gate_registration,
    generate_golden_slice,
    lint_declaration,
    read_surfaces_for_slice,
    run_layer2_suite,
    scan_logic_source,
)
from qml.protocol import construct_bot


def _drive(world: dict[str, object], assignment: object = None) -> tuple[object, ...]:
    """Independently construct + drive a bot over the golden slice; return the raw trace."""
    d = world["declaration"]
    slice_ = generate_golden_slice(d.footprint)  # type: ignore[attr-defined]
    assert is_ok(slice_)
    surfaces = read_surfaces_for_slice(slice_.value)
    assert is_ok(surfaces)
    hosted = construct_bot(
        world["factory"],
        declaration=d,
        assignment=assignment if assignment is not None else d.canonical_assignment(),
        read_surfaces=surfaces.value,
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_ok(hosted), hosted
    trace = drive_golden_slice(hosted.value, slice_.value)
    assert is_ok(trace), trace
    return trace.value


# --- E12-L2-01 ---------------------------------------------------------------


def test_e12_l2_01_replay_yields_identical_intents() -> None:
    """Two independent constructions over the same slice yield byte-identical intents."""
    world = w.build_world()
    first = _drive(world)
    second = _drive(world)
    assert first == second, "identical inputs must replay identical intents"
    assert first, "the fixture bot must actually emit intents (else the test is vacuous)"


def test_e12_l2_01_nondeterministic_bot_is_discriminated() -> None:
    """Canary: a nondeterministic bot produces differing traces, so the equality is real."""
    toggles = {"n": 0}

    class FlakyFactory:
        def construct(self, *, declaration, assignment, read_surfaces):  # noqa: ANN001
            del declaration, assignment, read_surfaces
            toggles["n"] += 1
            emit = toggles["n"] % 2 == 0

            class _Cb:
                def on_instant(self, evidence, /):  # noqa: ANN001
                    del evidence
                    return (w.make_entry(),) if emit else ()

            return Ok(_Cb())

    world = w.build_world()
    world["factory"] = FlakyFactory()
    assert _drive(world) != _drive(world), "the comparator must distinguish differing traces"


def test_e12_l2_01_determinism_generalizes_over_assignment() -> None:
    """Hypothesis: for any valid lookback, two replays match (property, not a single case)."""
    import pytest

    hyp = pytest.importorskip("hypothesis")
    st = pytest.importorskip("hypothesis.strategies")

    @hyp.given(lookback=st.integers(min_value=1, max_value=3))
    @hyp.settings(max_examples=15, deadline=None)
    def _prop(lookback: int) -> None:
        world = w.build_world()
        assignment = {"lookback": lookback, "stop_distance": 500}
        assert _drive(world, assignment) == _drive(world, assignment)

    _prop()


# --- E12-L2-02 ---------------------------------------------------------------


def _observe(world: dict[str, object]) -> object:
    d = world["declaration"]
    obs = collect_layer2_observations(
        declaration=d,
        factory=world["factory"],
        source_tree=world["source"],
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_ok(obs), obs
    return obs.value


def test_e12_l2_02_verdict_is_host_independent() -> None:
    """Two independent host runs of the same bot mint one verdict fingerprint."""
    world = w.build_world()
    v_a = evaluate_layer2(_observe(world))
    v_b = evaluate_layer2(_observe(world))
    assert is_ok(v_a) and is_ok(v_b)
    fp_a = v_a.value.fingerprint_content()
    fp_b = v_b.value.fingerprint_content()
    assert is_ok(fp_a) and is_ok(fp_b)
    assert fp_a.value.value == fp_b.value.value


def test_e12_l2_02_verdict_carries_no_host_identity_field() -> None:
    """The verdict identity has no pid/host/worker field, and an injected host tag is ignored."""
    world = w.build_world()
    obs = _observe(world)
    verdict = evaluate_layer2(obs)
    assert is_ok(verdict)
    keys = set(verdict.value.fp1_identity())
    assert keys == {
        "class",
        "contract_format_version",
        "declaration_fingerprint",
        "golden_slice_fingerprint",
        "checks",
    }, keys
    # A host tag added to the observation mapping does not change the verdict.
    base = obs.fp1_identity()
    tagged = {**base, "host_id": "host-beta", "worker_pid": 4242}
    v_plain = evaluate_layer2(base)
    v_tagged = evaluate_layer2(tagged)
    if is_ok(v_plain) and is_ok(v_tagged):
        assert (
            v_plain.value.fingerprint_content().value.value
            == v_tagged.value.fingerprint_content().value.value
        )


# --- E12-L2-03 ---------------------------------------------------------------


def test_e12_l2_03_nondeterminism_and_bad_kind_fail_layer2() -> None:
    """Differing runs, a non-permitted kind, or a scan finding each fail the pure verdict."""
    world = w.build_world()
    obs = _observe(world)
    assert is_ok(evaluate_layer2(obs)), "the clean base observation must pass"

    # (a) differing golden-slice runs -> determinism failure.
    differing = dataclasses.replace(obs, second_run=obs.first_run[:-1])
    r1 = evaluate_layer2(differing)
    assert is_refusal(r1) and r1.category is RefusalCategory.POLICY_REJECTION
    assert r1.context.get("field") == "golden_slice_determinism"

    # (b) a non-permitted emitted kind -> permitted-kinds failure.
    bad_kind = dataclasses.replace(obs, emitted_kinds=("tighten_protective_stop",))
    r2 = evaluate_layer2(bad_kind)
    assert is_refusal(r2) and r2.context.get("field") == "permitted_intent_kinds"

    # (c) a scan finding -> static-scan failure.
    finding = ScanFinding(capability="clock", path="bot/x.py", lineno=1, detail="import time")
    scanned = dataclasses.replace(obs, scan=ScanReport(findings=(finding,)))
    r3 = evaluate_layer2(scanned)
    assert is_refusal(r3) and r3.context.get("field") == "static_ast_import_scan"


# --- E12-L2-06 ---------------------------------------------------------------


def test_e12_l2_06_denial_set_scan_flags_each_capability_before_spawn() -> None:
    """A clock/fs/network/undeclared-random use is a scan finding — a pure, pre-spawn check."""
    cases = {
        "clock": "import time\n",
        "io": "import os\n",
        "network": "import socket\n",
        "undeclared_randomness": "import random\n",
    }
    for capability, source in cases.items():
        report = scan_logic_source({"bot/logic.py": source})
        assert is_ok(report), report
        caps = {f.capability for f in report.value.findings}
        assert capability in caps, f"{capability!r} must be flagged; got {caps}"
    # Clean logic is clean.
    clean = scan_logic_source(dict(w.CLEAN_SOURCE))
    assert is_ok(clean) and clean.value.clean is True


def test_e12_l2_06_declared_seed_permits_random_but_not_secrets() -> None:
    """A declared seed permits `random`; `secrets`/os.urandom stay denied."""
    seeded = scan_logic_source({"bot/x.py": "import random\n"}, declared_seed=True)
    assert is_ok(seeded) and seeded.value.clean is True
    secret = scan_logic_source({"bot/x.py": "import secrets\n"}, declared_seed=True)
    assert is_ok(secret)
    assert any(f.capability == "undeclared_randomness" for f in secret.value.findings)


# --- E12-L2-13 ---------------------------------------------------------------


def _passing_verdicts(world: dict[str, object]) -> tuple[object, object]:
    d = world["declaration"]
    l1 = lint_declaration(
        d,
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["catalog_producers"],
        logic_catalog=[world["logic"]],
    )
    l2 = run_layer2_suite(
        declaration=d,
        factory=world["factory"],
        source_tree=world["source"],
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_ok(l1) and is_ok(l2)
    return l1.value, l2.value


def test_e12_l2_13_complexity_score_is_not_a_registration_gate() -> None:
    """max_acceptable_complexity_score is discarded, never consulted — technical, never performance."""
    world = w.build_world()
    l1v, l2v = _passing_verdicts(world)
    # A hostile complexity value does NOT block: it is dropped, not gated.
    for kwargs in ({"max_acceptable_complexity_score": 0}, {"complexity_score": 999}):
        result = gate_registration(layer1=l1v, layer2=l2v, **kwargs)
        assert is_ok(result), f"complexity kwarg must be discarded, not gated: {kwargs}"
        assert "complexity" not in " ".join(result.value.fp1_identity()).lower()
    assert "max_acceptable_complexity_score" in DROPPED_REGISTRATION_GATES
    # Falsifiable control: an unknown NON-dropped field is refused (the discard is specific).
    unknown = gate_registration(layer1=l1v, layer2=l2v, some_perf_metric=1)
    assert is_refusal(unknown) and unknown.category is RefusalCategory.INVALID_INPUT


def test_e12_l2_13_conformance_gates_citation_and_seats_not_tunnel() -> None:
    """A registered bot may be cited; an ungoverned bot keeps the tunnel but cannot be cited."""
    world = w.build_world()
    l1v, l2v = _passing_verdicts(world)
    candidate = gate_registration(layer1=l1v, layer2=l2v)
    assert is_ok(candidate)
    cited = cite_registered_bot(
        candidate=candidate.value, cited_fp1=candidate.value.fingerprint, kind="seat"
    )
    assert is_ok(cited), "a registered bot fp1 may be cited by a seat"
    # Ungoverned plain-Python bots keep full tunnel access...
    tunnel = admit_ungoverned_tunnel()
    assert is_ok(tunnel) and tunnel.value.fp1_identity()["tunnel_open"] is True
    # ...but cannot be cited by governed evidence or seats.
    ungoverned_cite = cite_ungoverned_bot()
    assert is_refusal(ungoverned_cite)
    assert ungoverned_cite.category is RefusalCategory.POLICY_REJECTION
