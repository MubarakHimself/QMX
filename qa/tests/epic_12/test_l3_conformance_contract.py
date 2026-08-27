"""L3 — QML-local runtime-protocol + conformance contract boundaries (isolated).

Defined-unwired CT-33/CT-34 registry kinds are asserted SHAPE-ONLY; no test
turns a defined-unwired slot into a wired mint.

- E12-L3-01 (P0): the factory contract — (declaration, assignment, surfaces) -> callback -> CT-23 intents.
- E12-L3-02 (P0): both-layers gate returns content + verdict, NEVER a stamped record (AD-25). (§8-A)
- E12-L3-03 (P0): the Layer-1 linter — an unresolvable reference is unavailable dependency.
- E12-L3-05 (P0): CT-33 shape-only — six content groups, header excluded, no exit_logic field.
- E12-L3-06 (P1): CT-34 shape-only — legs, role vocabulary, order-significance opt-in enters fp1.
- E12-L3-09 (P1): state contract — the restored-state fingerprint enters downstream labels.
- E12-L3-10 (P1): the Layer-2 verdict is the pure function's output fed by the runner's observations.
"""

from __future__ import annotations

import _world as w
from qmf.core.chrono import Instant
from qmf.core.fingerprint import fingerprint
from qmf.core.refusal import Ok, RefusalCategory, Retryability, TypedRefusal, is_ok, is_refusal
from qml.conformance import (
    LAYER1_CHECKS,
    PROMOTED_FROM_EDGE_TYPE,
    collect_layer2_observations,
    evaluate_layer2,
    gate_registration,
    graduate_to_governed,
    lint_declaration,
    run_layer2_suite,
)
from qml.declaration import mint_bot_definition, mint_confluence
from qml.footprint import ProducerBinding
from qml.protocol import FunctionFactory, construct_bot, restore_bot


def _instant() -> object:
    return Instant.try_create(1_700_000_000_000_000_000).value


def _verdicts(world: dict[str, object]) -> tuple[object, object]:
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


def _failed_layer() -> TypedRefusal:
    return TypedRefusal(
        category=RefusalCategory.POLICY_REJECTION,
        retryability=Retryability.NO,
        context={"field": "conformance"},
    )


# --- E12-L3-01 ---------------------------------------------------------------


def test_e12_l3_01_factory_contract_roundtrip() -> None:
    """A conformant factory constructs a callback that returns zero-or-more CT-23 intents."""
    world = w.build_world()
    d = world["declaration"]
    hosted = construct_bot(
        world["factory"],
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces=None,
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_ok(hosted)
    driven = hosted.value.on_instant(_instant())
    assert is_ok(driven)
    from qmf.risk.door import EntryIntent, ExitIntent

    assert all(isinstance(i, (EntryIntent, ExitIntent)) for i in driven.value)


def test_e12_l3_01_factory_shape_violations_refused() -> None:
    """A non-callback return, and a non-factory object, are each refused."""

    class NoCallbackFactory:
        def construct(self, *, declaration, assignment, read_surfaces):  # noqa: ANN001
            del declaration, assignment, read_surfaces
            return Ok(object())  # no on_instant

    world = w.build_world()
    d = world["declaration"]
    bad_callback = construct_bot(
        NoCallbackFactory(),
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces=None,
    )
    assert is_refusal(bad_callback) and bad_callback.context.get("field") == "callback"

    not_a_factory = construct_bot(
        42, declaration=d, assignment=d.canonical_assignment(), read_surfaces=None
    )
    assert is_refusal(not_a_factory) and not_a_factory.context.get("field") == "factory"


def test_e12_l3_01_non_ct23_emission_refused() -> None:
    """A callback emitting a venue command (non-CT-23) is refused at the door."""

    class VenueFactory:
        def construct(self, *, declaration, assignment, read_surfaces):  # noqa: ANN001
            del declaration, assignment, read_surfaces

            class _Cb:
                def on_instant(self, evidence, /):  # noqa: ANN001
                    del evidence
                    return [{"venue_command": "place"}]

            return Ok(_Cb())

    world = w.build_world()
    d = world["declaration"]
    hosted = construct_bot(
        VenueFactory(),
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces=None,
    )
    assert is_ok(hosted)
    driven = hosted.value.on_instant(_instant())
    assert is_refusal(driven)
    assert driven.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- E12-L3-02 ---------------------------------------------------------------


def test_e12_l3_02_gate_returns_content_and_verdict_never_a_record() -> None:
    """pass/pass returns fingerprintable content + the verdict — never a stamped CT-06 record (AD-25)."""
    world = w.build_world()
    l1v, l2v = _verdicts(world)
    result = gate_registration(layer1=l1v, layer2=l2v)
    assert is_ok(result)
    candidate = result.value
    # Content + verdict:
    assert candidate.declaration is not None
    assert candidate.fingerprint is not None
    assert candidate.ticket.layer1_passed and candidate.ticket.layer2_passed
    # NEVER a stamped record — AD-25 root-mints: no WriterId / occurrence header here.
    payload = candidate.identity_payload()
    for header in ("writer", "sequence", "stable_id", "created_at"):
        assert header not in payload, f"the gate must not stamp {header} (AD-25 inversion)"
    assert not hasattr(candidate, "record"), "a candidate is not a registry RegistrationReceipt"


def test_e12_l3_02_graduation_edge_is_authored_content_not_a_stamped_record() -> None:
    """A working experiment graduates by minting a promoted-from edge (shape only; host stamps).

    The edge PERSISTENCE rides the defined-unwired composition-root mint (§8-E,
    recorded UNPROVEN); here the AUTHORED edge shape is proven, with no WriterId.
    """
    world = w.build_world()
    l1v, l2v = _verdicts(world)
    research_ref = fingerprint({"class": "research-artifact", "id": "exp-42"}).value
    graduated = graduate_to_governed(layer1=l1v, layer2=l2v, originating_research_ref=research_ref)
    assert is_ok(graduated), graduated
    edge = graduated.value.promoted_from_edge
    assert edge.edge_type == PROMOTED_FROM_EDGE_TYPE == "promoted-from"
    assert edge.to_ref.value == research_ref.value
    assert edge.from_ref.value == graduated.value.candidate.fingerprint.value
    # Authored content only — the host composition root stamps the CT-07 record.
    assert not hasattr(edge, "writer") and not hasattr(graduated.value, "record")


def test_e12_l3_02_all_fail_combinations_are_policy_rejection() -> None:
    """pass/fail, fail/pass, fail/fail each refuse policy rejection at the contract boundary."""
    world = w.build_world()
    l1v, l2v = _verdicts(world)
    fail = _failed_layer()
    for layer1, layer2 in ((l1v, fail), (fail, l2v), (fail, fail)):
        result = gate_registration(layer1=layer1, layer2=layer2)
        assert is_refusal(result)
        assert result.category is RefusalCategory.POLICY_REJECTION


# --- E12-L3-03 ---------------------------------------------------------------


def test_e12_l3_03_unresolvable_references_are_unavailable() -> None:
    """A missing family / confluence / logic reference each refuse unavailable dependency."""
    world = w.build_world()
    d = world["declaration"]
    base = dict(
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["catalog_producers"],
        logic_catalog=[world["logic"]],
    )
    for missing in ("family_catalog", "confluence_catalog", "logic_catalog"):
        kwargs = dict(base)
        kwargs[missing] = []
        refusal = lint_declaration(d, **kwargs)
        assert is_refusal(refusal), f"empty {missing} must refuse"
        assert refusal.category is RefusalCategory.UNAVAILABLE_DEPENDENCY, missing
    # Control: the fully-resolvable declaration passes with the pinned check list.
    ok = lint_declaration(d, **base)
    assert is_ok(ok) and ok.value.checks == LAYER1_CHECKS


# --- E12-L3-05 ---------------------------------------------------------------


def test_e12_l3_05_ct33_shape_six_groups_no_exit_logic() -> None:
    """CT-33 body is exactly the six content groups; the AD-16 header and exit_logic are excluded."""
    d = w.build_world()["declaration"]
    assert set(d.body()) == {
        "strategy_family_id",
        "confluence_set",
        "parameter_space",
        "footprint",
        "permitted_exit_intents",
        "logic_reference",
    }
    assert "exit_logic" not in d.body()
    payload = d.identity_payload()
    assert set(payload) >= {"kind", "contract_format_version", "body"}
    # A declaration carrying an exit_logic field is refused (Book owns exit behaviour).
    assert is_refusal(mint_bot_definition(w.declaration_mapping(exit_logic={"module": "x"})))


def test_e12_l3_05_ct33_semantic_content_roundtrip() -> None:
    """Re-minting from the canonical identity payload reproduces the same fp1 (shape-only)."""
    d = w.build_world()["declaration"]
    fp = d.fingerprint_content()
    assert is_ok(fp)
    reminted = mint_bot_definition(d.identity_payload())
    assert is_ok(reminted)
    fp2 = reminted.value.fingerprint_content()
    assert is_ok(fp2)
    assert fp.value.value == fp2.value.value


# --- E12-L3-06 ---------------------------------------------------------------


def _prod(tag: str) -> ProducerBinding:
    return ProducerBinding.try_create(fingerprint({"class": "qa-producer", "tag": tag}).value).value


def test_e12_l3_06_ct34_shape_and_leg_rules() -> None:
    """CT-34: >=1 leg; a bad role and a producerless+childless leg are refused."""
    good = mint_confluence([{"role": "level", "producer_binding": _prod("a")}])
    assert is_ok(good)
    assert good.value.body()["legs"], "a confluence carries a leg set"
    # A role outside the closed-and-addable vocabulary is refused.
    assert is_refusal(mint_confluence([{"role": "not-a-role", "producer_binding": _prod("b")}]))
    # A leg with neither a producer binding nor a child cite is refused.
    assert is_refusal(mint_confluence([{"role": "level"}]))
    # A zero-leg confluence is refused.
    assert is_refusal(mint_confluence([]))


def test_e12_l3_06_order_significance_enters_fingerprint_only_when_declared() -> None:
    """The order-significance opt-in changes the fingerprint; the default omits ordinals."""
    legs = [
        {"role": "level", "producer_binding": _prod("p1"), "display_ordinal": 0},
        {"role": "trigger", "producer_binding": _prod("p2"), "display_ordinal": 1},
    ]
    default = mint_confluence(list(legs))
    ordered = mint_confluence(list(legs), order_significance=True)
    assert is_ok(default) and is_ok(ordered)
    fp_default = default.value.fingerprint_content().value.value
    fp_ordered = ordered.value.fingerprint_content().value.value
    assert fp_default != fp_ordered, "declaring order-significance must change identity"


# --- E12-L3-09 ---------------------------------------------------------------


def test_e12_l3_09_restored_state_fingerprint_enters_labels() -> None:
    """The restored-state fingerprint is exposed for downstream result labels."""
    world = w.build_world()
    d = world["declaration"]
    hosted = construct_bot(
        world["factory"],
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces=None,
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_ok(hosted)
    snap = hosted.value.snapshot()
    assert is_ok(snap)
    restored = restore_bot(
        snap.value,
        world["factory"],
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces=None,
        current_scope=w.scope_for(d),
    )
    assert is_ok(restored)
    labels = restored.value.label_input_fingerprints()
    snap_fp = snap.value.fingerprint()
    assert is_ok(snap_fp)
    assert snap_fp.value.value in {fp.value for fp in labels}
    # A cold (never-restored) bot exposes no restored-state fingerprint.
    assert hosted.value.restored_state_fingerprints() == ()


# --- E12-L3-10 ---------------------------------------------------------------


def test_e12_l3_10_verdict_is_the_pure_function_fed_by_observations() -> None:
    """run_layer2_suite's verdict equals evaluate_layer2(observations) — the pure surface owns it."""
    world = w.build_world()
    silent = FunctionFactory(logic=lambda evidence: ())
    d = world["declaration"]
    common = dict(declaration=d, source_tree=world["source"], state_scope=w.scope_for(d), state_bound=w.STATE_BOUND)
    suite = run_layer2_suite(factory=silent, **common)
    obs = collect_layer2_observations(factory=silent, **common)
    assert is_ok(suite) and is_ok(obs)
    pure = evaluate_layer2(obs.value)
    assert is_ok(pure)
    assert (
        suite.value.fingerprint_content().value.value
        == pure.value.fingerprint_content().value.value
    )


def test_e12_l3_10_spawned_runner_yields_the_same_pure_verdict() -> None:
    """The host runner spawns a process yet the verdict is identical (host-independent by construction).

    Best-effort: an infrastructure failure to spawn is not a conformance finding.
    """
    from qml.host.runner import run_sandbox

    world = w.build_world()
    silent = FunctionFactory(logic=lambda evidence: ())
    d = world["declaration"]
    in_process = run_layer2_suite(
        declaration=d,
        factory=silent,
        source_tree=world["source"],
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_ok(in_process)
    sandboxed = run_sandbox(
        declaration=d,
        source_tree=world["source"],
        factory_spec=None,  # 'silent' spec — reconstructable in the isolated child
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
        timeout_seconds=60,
    )
    if is_refusal(sandboxed):
        # Only an infrastructure spawn failure is tolerated; a conformance policy
        # rejection would be a real disagreement and must surface.
        assert sandboxed.context.get("field") == "sandbox_process", sandboxed
        import pytest

        pytest.skip(f"sandbox process unavailable in this environment: {sandboxed.context}")
    assert (
        sandboxed.value.fingerprint_content().value.value
        == in_process.value.fingerprint_content().value.value
    )
