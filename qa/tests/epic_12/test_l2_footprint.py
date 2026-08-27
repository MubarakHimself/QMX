"""L2 — footprint, evidence, template, identity, and state invariants.

- E12-L2-04 (P0): footprint producer set == transitive union; a missing leg producer -> Layer-1 refusal. (FM-1)
- E12-L2-05 (P0): the callback receives only declared-footprint evidence; undeclared/forbidden is refused. (QL-7)
- E12-L2-07 (P1): an omitted AD-22 template identity field is a Layer-1 refusal; resolution is single-valued. (FM-2)
- E12-L2-08 (P0): logic identity is the source-manifest fp (build artifacts stripped); a header never enters fp1. (FM-10)
- E12-L2-09 (P0): identity is semantic content only; a changed default mints a new fp1; occurrence facts never do.
- E12-L2-10 (P1): snapshot/restore on an identical tuple is equivalent; state is bounded. (AR-67)
- E12-L2-11 (P0): a nested confluence-leg producer must reach the citing bot's footprint (transitive). (FM-1)
- E12-L2-12 (P1): each parameter carries an AD-40 unit-kind; a binary float is refused. (AD-40)
"""

from __future__ import annotations

import _world as w
from qmf.core.exact import UnitKind
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal
from qml.conformance import lint_declaration
from qml.declaration import mint_bot_definition, mint_confluence, promote_tuned_assignment
from qml.footprint import (
    AD22_IDENTITY_FIELDS,
    ProducerBinding,
    compute_transitive_union,
    mint_footprint,
    mint_producer_template,
    report_completeness,
    resolve_template,
)
from qml.logic import mint_logic_identity
from qml.protocol import (
    FootprintEvidence,
    assert_declared_state_bound,
    construct_bot,
    declared_evidence_keys,
    restore_bot,
)

_TEMPLATE: dict[str, object] = {
    "producer_kind": "indicator",
    "formula_id": "sma",
    "contract_format_version": 1,
    "inputs": [
        {
            "name": "close",
            "source": {"kind": "source-id", "id": "eurusd"},
            "bar_spec": {"kind": "time-interval", "seconds": 60},
            "channel_kind": "exact-price",
            "quote_side": "mid",
        }
    ],
    "calendar_requirements": [
        {"rule_set": "forex-17NY", "rule_set_version": "v3", "tzdata_version": "2025.2"}
    ],
    "alignment_policy": "as-of",
    "missing_value_policy": "mark-gap",
    "warm_up": 10,
    "output_schema": [
        {
            "name": "value",
            "channel_kind": "exact-price",
            "arity": "scalar-per-sample",
            "index_offset": 0,
        }
    ],
    "supported_modes": ["batch"],
    "arithmetic_reference_configuration": {
        "c_library": "talib-0.4.0",
        "python_wrapper": "ta-lib-0.4.28",
        "reference_configuration": {"mode": "classic"},
    },
}


def _lint(world: dict[str, object]) -> object:
    d = world["declaration"]
    return lint_declaration(
        d,
        family_catalog=[world["family"]],
        confluence_catalog=[world["confluence"]],
        producer_catalog=world["catalog_producers"],
        logic_catalog=[world["logic"]],
    )


# --- E12-L2-04 ---------------------------------------------------------------


def test_e12_l2_04_footprint_must_equal_transitive_union() -> None:
    """A confluence-leg producer absent from the footprint is a Layer-1 refusal."""
    complete = w.build_world()
    assert is_ok(_lint(complete)), "the complete footprint must lint clean"

    dropped = w.build_world(drop_producer=True)
    refusal = _lint(dropped)
    assert is_refusal(refusal), "a footprint missing a cited leg producer must refuse"
    assert refusal.category is RefusalCategory.INVALID_INPUT
    assert refusal.context.get("field") == "footprint"
    assert refusal.context.get("missing"), "the refusal names the missing producer key"


def test_e12_l2_04_completeness_report_is_set_equality() -> None:
    """report_completeness is exact set-equality of footprint vs union (raw invariant)."""
    world = w.build_world()
    confluence = world["confluence"]
    complete = report_completeness(
        world["footprint"], confluence.completeness_legs(), bot_direct=()  # type: ignore[attr-defined]
    )
    assert is_ok(complete) and complete.value.complete is True
    # An EXTRA footprint producer not present in the union breaks set-equality.
    extra = ProducerBinding.try_create(
        __import__("qmf.core.fingerprint", fromlist=["fingerprint"]).fingerprint(
            {"class": "qa-producer", "tag": "orphan"}
        ).value
    )
    assert is_ok(extra)
    fat_footprint = mint_footprint(
        [w._stream()], [w._calendar()], [*world["producers"], extra.value]
    )
    assert is_ok(fat_footprint)
    report = report_completeness(
        fat_footprint.value, confluence.completeness_legs(), bot_direct=()  # type: ignore[attr-defined]
    )
    assert is_ok(report) and report.value.complete is False
    assert report.value.extra, "the orphan footprint producer is reported extra"


# --- E12-L2-05 ---------------------------------------------------------------


def test_e12_l2_05_callback_sees_only_declared_footprint_evidence() -> None:
    """Undeclared and forbidden (book/clock) evidence keys are refused; declared keys pass."""
    world = w.build_world()
    d = world["declaration"]
    keys = declared_evidence_keys(d.footprint)
    assert is_ok(keys)
    declared = keys.value
    instant_ns = 1_700_000_000_000_000_000

    # An undeclared producer/stream key is never delivered to the callback.
    undeclared = FootprintEvidence.try_create(
        instant_ns, {"not-a-declared-key": _series(instant_ns)}, declared_keys=declared
    )
    assert is_refusal(undeclared) and undeclared.category is RefusalCategory.INVALID_INPUT

    # A forbidden book/clock key is refused regardless of the declared set.
    forbidden = FootprintEvidence.try_create(
        instant_ns, {"book": _series(instant_ns)}, declared_keys=declared
    )
    assert is_refusal(forbidden) and forbidden.category is RefusalCategory.INVALID_INPUT

    # A declared key is delivered.
    one_declared = sorted(declared)[0]
    ok = FootprintEvidence.try_create(
        instant_ns, {one_declared: _series(instant_ns)}, declared_keys=declared
    )
    assert is_ok(ok)


def test_e12_l2_05_construct_refuses_undeclared_read_surface() -> None:
    """A host that injects an undeclared read surface is refused at construction."""
    world = w.build_world()
    d = world["declaration"]
    refusal = construct_bot(
        world["factory"],
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces={"undeclared-token": object()},
        state_scope=w.scope_for(d),
        state_bound=w.STATE_BOUND,
    )
    assert is_refusal(refusal) and refusal.category is RefusalCategory.INVALID_INPUT


def _series(instant_ns: int) -> dict[str, object]:
    return {
        "kind": "series",
        "samples": [{"presence": "present", "knowable_at": instant_ns, "value": 1}],
    }


# --- E12-L2-07 ---------------------------------------------------------------


def test_e12_l2_07_omitted_ad22_field_is_layer1_refusal() -> None:
    """Removing any AD-22 identity field makes the template a Layer-1 refusal naming it."""
    assert is_ok(mint_producer_template(dict(_TEMPLATE))), "the complete template must build"
    for field in AD22_IDENTITY_FIELDS:
        partial = {k: v for k, v in _TEMPLATE.items() if k != field}
        refusal = mint_producer_template(partial)
        assert is_refusal(refusal), f"omitting {field} must refuse"
        assert refusal.context.get("field") == field
        assert refusal.context.get("layer") == 1


def test_e12_l2_07_template_resolution_is_single_valued() -> None:
    """resolve_template is total and single-valued: identical canonical runs fingerprint alike."""
    first = resolve_template(dict(_TEMPLATE))
    second = resolve_template(dict(_TEMPLATE))
    assert is_ok(first) and is_ok(second)
    fp1 = first.value.fingerprint_content()
    fp2 = second.value.fingerprint_content()
    assert is_ok(fp1) and is_ok(fp2)
    assert fp1.value.value == fp2.value.value


# --- E12-L2-08 ---------------------------------------------------------------


def test_e12_l2_08_logic_identity_is_source_manifest_not_build_bytes() -> None:
    """Identical source -> one logic fp1; build artifacts are stripped; different source differs."""
    base = {"pkg/a.py": "x = 1\n", "pkg/b.py": "y = 2\n"}
    a = mint_logic_identity("d", "1.0.0", dict(base))
    b = mint_logic_identity("d", "1.0.0", dict(base))
    assert is_ok(a) and is_ok(b)
    assert a.value.source_manifest.value == b.value.source_manifest.value

    # Adding wheel/build artifacts does not change identity (they are dropped).
    with_artifacts = {**base, "pkg/__pycache__/a.cpython-314.pyc": "IGNORED", "d-1.0.0.dist-info/RECORD": "x"}
    c = mint_logic_identity("d", "1.0.0", with_artifacts)
    assert is_ok(c)
    assert c.value.source_manifest.value == a.value.source_manifest.value

    # Different source content mints a different fingerprint.
    changed = {**base, "pkg/b.py": "y = 3\n"}
    diff = mint_logic_identity("d", "1.0.0", changed)
    assert is_ok(diff)
    assert diff.value.source_manifest.value != a.value.source_manifest.value


def test_e12_l2_08_ad16_header_fields_are_excluded_from_identity() -> None:
    """A writer/created-at/stable-id on the declaration is refused — occurrence, not identity."""
    for header in ("writer", "created_at", "stable_id", "sequence"):
        refusal = mint_bot_definition(w.declaration_mapping(**{header: "x"}))
        assert is_refusal(refusal), f"{header} must be refused on the declaration"
        assert refusal.category is RefusalCategory.INVALID_INPUT


# --- E12-L2-09 ---------------------------------------------------------------


def test_e12_l2_09_identity_is_semantic_content_only() -> None:
    """Identical content -> identical fp1; a tuned default mints a NEW fp1."""
    d1 = w.build_world()["declaration"]
    d2 = w.build_world()["declaration"]
    fp1 = d1.fingerprint_content()
    fp2 = d2.fingerprint_content()
    assert is_ok(fp1) and is_ok(fp2)
    assert fp1.value.value == fp2.value.value, "identical content must fingerprint alike"

    tuned = promote_tuned_assignment(d1, {"lookback": 2, "stop_distance": 500})
    assert is_ok(tuned)
    tuned_fp = tuned.value.fingerprint_content()
    assert is_ok(tuned_fp)
    assert tuned_fp.value.value != fp1.value.value, "a changed default must mint a new fp1"


def test_e12_l2_09_occurrence_facts_never_mint_a_new_bot() -> None:
    """Seat/binding/paper are occurrence facts — refused as declaration identity fields."""
    for occurrence in ("seat", "binding", "paper", "rebinding"):
        refusal = mint_bot_definition(w.declaration_mapping(**{occurrence: True}))
        assert is_refusal(refusal), f"{occurrence} must be refused"
        assert refusal.category is RefusalCategory.INVALID_INPUT


# --- E12-L2-10 ---------------------------------------------------------------


def test_e12_l2_10_snapshot_restore_roundtrip_is_equivalent() -> None:
    """Snapshot/restore on an identical tuple continues equivalently (equal state fp1)."""
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
    snap1 = hosted.value.snapshot()
    assert is_ok(snap1)
    restored = restore_bot(
        snap1.value,
        world["factory"],
        declaration=d,
        assignment=d.canonical_assignment(),
        read_surfaces=None,
        current_scope=w.scope_for(d),
    )
    assert is_ok(restored)
    snap2 = restored.value.snapshot()
    assert is_ok(snap2)
    fp1 = snap1.value.fingerprint()
    fp2 = snap2.value.fingerprint()
    assert is_ok(fp1) and is_ok(fp2)
    assert fp1.value.value == fp2.value.value


def test_e12_l2_10_state_bound_is_enforced() -> None:
    """State exceeding the declared bound is a Layer-2 policy rejection, never a silent truncate."""
    ok = assert_declared_state_bound({"ticks": 1}, 256)
    assert is_ok(ok)
    over = assert_declared_state_bound({"blob": "x" * 500}, 8)
    assert is_refusal(over)
    assert over.category is RefusalCategory.POLICY_REJECTION
    assert over.context.get("field") == "state_bound"


# --- E12-L2-11 ---------------------------------------------------------------


def test_e12_l2_11_nested_confluence_producer_must_reach_footprint() -> None:
    """A producer cited only through a NESTED confluence must still reach the footprint."""
    from qmf.core.fingerprint import fingerprint  # noqa: N813  (import here to keep scope local)

    child_prod = ProducerBinding.try_create(
        fingerprint({"class": "qa-producer", "tag": "nested-child"}).value
    )
    parent_prod = ProducerBinding.try_create(
        fingerprint({"class": "qa-producer", "tag": "parent-direct"}).value
    )
    assert is_ok(child_prod) and is_ok(parent_prod)
    child = mint_confluence([{"role": "level", "producer_binding": child_prod.value}])
    assert is_ok(child)
    child_fp = child.value.fingerprint_content()
    assert is_ok(child_fp)
    parent = mint_confluence(
        [
            {"role": "trigger", "producer_binding": parent_prod.value},
            {"role": "filter", "confluence_ref": child_fp.value},
        ]
    )
    assert is_ok(parent)

    # The transitive union spans BOTH the parent-direct and the nested-child producer.
    union = compute_transitive_union(
        parent.value.completeness_legs(),
        bot_direct=(),
        catalog={child_fp.value.value: child.value.completeness_legs()},
    )
    assert is_ok(union)
    keys = {b.fingerprint_content().value.value for b in union.value}
    assert keys == {
        child_prod.value.fingerprint_content().value.value,
        parent_prod.value.fingerprint_content().value.value,
    }

    base = w.build_world()
    family_id = base["family"].family_id.value  # type: ignore[attr-defined]
    logic = base["logic"]
    catalog_confluence = [parent.value, child.value]
    catalog_producers = [parent_prod.value, child_prod.value]

    def _declare(producers: list[object]) -> object:
        footprint = mint_footprint([w._stream()], [w._calendar()], producers)
        assert is_ok(footprint)
        return mint_bot_definition(
            {
                "strategy_family_id": family_id,
                "confluence_set": [parent.value],
                "parameter_space": w.parameter_space(),
                "footprint": footprint.value,
                "permitted_exit_intents": ["close_full"],
                "logic_reference": logic,
            }
        )

    complete = _declare([parent_prod.value, child_prod.value])
    assert is_ok(complete)
    ok = lint_declaration(
        complete.value,
        family_catalog=[base["family"]],
        confluence_catalog=catalog_confluence,
        producer_catalog=catalog_producers,
        logic_catalog=[logic],
    )
    assert is_ok(ok), f"a footprint spanning the nested producer must lint clean: {ok}"

    missing_nested = _declare([parent_prod.value])  # omits the nested-child producer
    assert is_ok(missing_nested)
    refusal = lint_declaration(
        missing_nested.value,
        family_catalog=[base["family"]],
        confluence_catalog=catalog_confluence,
        producer_catalog=catalog_producers,
        logic_catalog=[logic],
    )
    assert is_refusal(refusal), "omitting the nested-child producer must refuse"
    assert refusal.context.get("field") == "footprint"


# --- E12-L2-12 ---------------------------------------------------------------


def test_e12_l2_12_every_parameter_is_unit_kinded_no_float() -> None:
    """A missing AD-40 unit-kind and a binary-float default are each invalid input."""
    no_unit = [
        {
            "name": "lookback",
            "type": "exact integer",
            "bounds": {"min": 1, "max": 200},
            "step": 1,
            "default": 1,
            "ui": "ui-editable",
        }
    ]
    r_unit = mint_bot_definition(w.declaration_mapping(parameter_space=no_unit))
    assert is_refusal(r_unit) and r_unit.context.get("field") == "unit_kind"

    float_default = [
        {
            "name": "lookback",
            "type": "exact integer",
            "bounds": {"min": 1, "max": 200},
            "step": 1,
            "default": 1.5,
            "unit_kind": UnitKind.COUNT,
            "ui": "ui-editable",
        }
    ]
    r_float = mint_bot_definition(w.declaration_mapping(parameter_space=float_default))
    assert is_refusal(r_float) and r_float.category is RefusalCategory.INVALID_INPUT
    assert r_float.context.get("field") == "default"


def test_e12_l2_12_defaults_form_the_canonical_assignment() -> None:
    """The mandatory defaults taken together are the canonical assignment (a derived projection)."""
    d = w.build_world()["declaration"]
    assert dict(d.canonical_assignment()) == {"lookback": 1, "stop_distance": 500}
