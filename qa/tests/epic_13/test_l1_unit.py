"""Epic 13 — L1 unit tests (T13-101..112).

Pure-function behaviour over injected inputs. A failing assertion is a FINDING:
the assertion states what the REQUIREMENT demands, never what the source does.
"""

from __future__ import annotations

import pytest
from qmf.core.exact import Money
from qmf.core.refusal import RefusalCategory, is_ok, is_refusal

import qmb.doors.mcp as mcp
from _fixtures import DEFAULTS, SEED, base_run_spec, build_universe, unwrap, writer
from qmb.config import (
    CLOCK_REPLAY,
    FOLD_UNRATED,
    PROVENANCE_RECORDED,
    PROVENANCE_SYNTHETIC_TAINTED,
    SANCTIONED_OVERLAP_KEYS,
    STARTING_CAPITAL_KEY,
    ResolvedRunConfig,
    compile_run_config,
    materialize_condition_preset,
    merge_book_bms_keys,
    resolve_starting_capital,
)
from qmb.doors import MCP_SHIPPED
from qmb.registryread import RegistryReadPort


def _compile(u, **over):
    kwargs = dict(
        book_fragment=u.book_fragment,
        bms_fragment=u.bms_fragment,
        run_spec=base_run_spec(),
        workspace_defaults=dict(DEFAULTS),
    )
    kwargs.update(over)
    return compile_run_config(u.port, **kwargs)


# --- T13-101 -----------------------------------------------------------------
def test_t13_101_mcp_scaffolded_not_shipped() -> None:
    """The MCP door is scaffolded but not shipped/wired in V1. (13.1 AC2 / SC-08)"""
    assert MCP_SHIPPED is False
    assert mcp.SHIPPED is False
    assert mcp.is_shipped() is False
    # invoking the door in V1 is refused as an unsupported capability, not served
    served = mcp.serve()
    assert is_refusal(served)
    assert served.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    launched = mcp.main()
    assert is_refusal(launched)
    assert launched.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- T13-102 -----------------------------------------------------------------
def test_t13_102_alias_resolves_by_fp1() -> None:
    """A human alias resolves to the record BY fp1; the handle cites by fingerprint,
    never name@version. (13.2 AC2)"""
    u = build_universe()
    resolved = unwrap(u.port.resolve("scalping"), "alias resolve")
    assert resolved.cite() == u.book_record.stable_id.value
    assert resolved.cite().startswith("fp1:sha256:")
    assert "@" not in resolved.cite()
    # the same record resolved by its fp1 yields the identical cite
    by_fp = unwrap(u.port.resolve(u.book_record.stable_id), "fp1 resolve")
    assert by_fp.cite() == resolved.cite()


# --- T13-103 -----------------------------------------------------------------
def test_t13_103_superseded_ref_stale_evidence_returned() -> None:
    """A ref a fresher as-of shows superseded returns an AD-11 stale-evidence refusal
    carrying the severity key — RETURNED, not raised. (13.2 AC3 / FM-7)"""
    from _fixtures import CREATED_NS, SEVERITY, book_definition, definition_record, instant
    from qmb.registryread import AsOfSet, DatedPointer, PassiveHub, SupersedesRef

    first = definition_record("book-definition", book_definition())
    second = definition_record("book-definition", book_definition(loss_floor=900_000))
    older = unwrap(
        AsOfSet.try_create(
            instant(CREATED_NS),
            records=(first,),
            pointers=(unwrap(DatedPointer.try_create("scalping", first.stable_id, instant())),),
        ),
    )
    fresher = unwrap(
        AsOfSet.try_create(
            instant(CREATED_NS + 1),
            records=(first, second),
            pointers=(
                unwrap(DatedPointer.try_create("scalping", second.stable_id, instant(CREATED_NS + 1))),
            ),
            supersedes=(unwrap(SupersedesRef.try_create(second.stable_id, first.stable_id)),),
        ),
    )
    hub = unwrap(PassiveHub.try_create((older, fresher)))
    port = unwrap(RegistryReadPort.try_create(hub, stale_evidence_severity=SEVERITY, bound=older))
    stale = port.resolve(first.stable_id)  # returned, never raised
    assert is_refusal(stale)
    assert stale.category is RefusalCategory.STALE_EVIDENCE
    assert stale.context["severity_key"] == "qmb_stale_evidence_severity"
    assert stale.context["severity"] == SEVERITY


# --- T13-104 -----------------------------------------------------------------
def test_t13_104_named_condition_preset_is_ordinary_fragment() -> None:
    """A named condition preset materializes as an ordinary config fragment under the
    same grammar/fingerprint/lineage discipline. (13.3 AC5)"""
    u = build_universe()
    preset = unwrap(
        materialize_condition_preset(
            u.port,
            "scalping",
            writer("config-fragment"),
            name="stress-spread",
            keys={"spread-schedule": {"name": "stress-spread", "widening_bps": 20}},
        ),
        "stress-spread preset",
    )
    assert preset.source_kind == "named-condition-preset"
    assert preset.preset_name == "stress-spread"
    assert preset.fingerprint.value.startswith("fp1:sha256:")
    # derived, lineaged back to the resolved source definition fp1
    assert preset.lineage is not None
    assert preset.lineage.from_ref == preset.fingerprint
    assert preset.lineage.to_ref == u.book_fragment.source_fp1


# --- T13-105 -----------------------------------------------------------------
def test_t13_105_compiler_precedence_layers() -> None:
    """Layers resolve invocation flags > run spec > BMS > Book > defaults; a higher
    layer overrides the lower on a resolvable key. (13.4 AC1)"""
    from qmb.config import LAYER_PRECEDENCE

    assert LAYER_PRECEDENCE == (
        "invocation-flags",
        "run-spec",
        "bms-fragment",
        "book-fragment",
        "workspace-defaults",
    )
    u = build_universe()
    defaults = dict(DEFAULTS)
    defaults["region"] = "from-defaults"
    defaults["fill"] = "from-defaults"
    defaults["admission"] = "DEFAULT-SENTINEL"  # a book-fragment namespace key
    spec = base_run_spec()
    spec["region"] = "from-spec"
    spec["fill"] = "from-spec"

    with_flags = unwrap(
        _compile(u, run_spec=spec, workspace_defaults=defaults, invocation_flags={"fill": "from-flags"}),
        "with flags",
    )
    # invocation flags win over run spec on the same key
    assert with_flags.keys["fill"] == "from-flags"
    # run spec wins over workspace defaults
    assert with_flags.keys["region"] == "from-spec"
    # book fragment (its 'admission' namespace) wins over a workspace-default sentinel
    from collections.abc import Mapping

    assert with_flags.keys["admission"] != "DEFAULT-SENTINEL"
    assert isinstance(with_flags.keys["admission"], Mapping)

    no_flags = unwrap(_compile(u, run_spec=spec, workspace_defaults=defaults), "no flags")
    # with no flag, the run spec value stands
    assert no_flags.keys["fill"] == "from-spec"


# --- T13-106 -----------------------------------------------------------------
def test_t13_106_exactly_one_readonly_schema_valid_config() -> None:
    """The compiler emits exactly ONE fully-resolved, read-only, schema-validated
    run-config. (13.4 AC1)"""
    u = build_universe()
    result = _compile(u)
    assert is_ok(result)
    config = result.value
    assert isinstance(config, ResolvedRunConfig)
    # read-only artifact: frozen dataclass, and its keys mapping rejects mutation
    with pytest.raises((AttributeError, TypeError)):
        config.fingerprint = config.fingerprint  # type: ignore[misc]
    with pytest.raises(TypeError):
        config.keys["injected"] = 1  # type: ignore[index]
    # schema-valid: re-reads through the declared schema
    assert is_ok(ResolvedRunConfig.try_read(config.fp1_identity()))


# --- T13-107 -----------------------------------------------------------------
def test_t13_107_unsanctioned_collision_refuses_no_silent_overwrite() -> None:
    """An unsanctioned Book/BMS key collision is a compile-time CT-04 refusal; the
    colliding value is never silently overwritten. (13.4 AC2 / FM-1) [R-004]"""
    collision = merge_book_bms_keys(
        {"admission": {"x": 1}, "accounting": {"stolen": "book"}},
        {"accounting": {"y": "bms"}},
    )
    assert is_refusal(collision)
    assert collision.category is RefusalCategory.INVALID_INPUT
    assert "accounting" in collision.context.get("colliding", [])
    # a real disjoint Book+BMS pair does NOT false-trip the collision guard
    u = build_universe()
    merged = merge_book_bms_keys(u.book_fragment.keys, u.bms_fragment.keys)
    assert is_ok(merged)


# --- T13-108 -----------------------------------------------------------------
def test_t13_108_sanctioned_overlap_bms_outranks_book() -> None:
    """In a sanctioned overlap the BMS value outranks the Book value. (13.4 AC2)"""
    assert SANCTIONED_OVERLAP_KEYS == frozenset()  # V1 has no sanctioned overlap
    ranked = unwrap(
        merge_book_bms_keys(
            {"admission": {"x": 1}, "reporting": {"from": "book"}},
            {"reporting": {"from": "bms"}},
            sanctioned_overlap={"reporting"},
        ),
        "sanctioned overlap",
    )
    assert ranked["reporting"] == {"from": "bms"}


# --- T13-109 -----------------------------------------------------------------
def test_t13_109_cites_by_fp1_even_from_alias() -> None:
    """The resolved artifact cites Book, BMS, and bot by fp1 even when the invocation
    used a human alias; no name@version leaks. (13.4 AC3)"""
    u = build_universe()
    config = unwrap(_compile(u, run_spec=base_run_spec(bot_ref="mean-reversion")), "alias compile")
    assert config.bot_fp1 == u.bot.stable_id
    assert config.bot_fp1.value.startswith("fp1:sha256:")
    assert "@" not in config.bot_fp1.value
    assert "@" not in config.book_fp1.value
    assert "@" not in config.bms_fp1.value
    assert "@" not in str(config.fp1_identity())
    # name@version is never a legal cite
    banned = _compile(u, run_spec={"bot": "mean-reversion@1", STARTING_CAPITAL_KEY: SEED})
    assert is_refusal(banned)
    assert banned.category is RefusalCategory.INVALID_INPUT


# --- T13-110 -----------------------------------------------------------------
def test_t13_110_replay_clock_on_synthetic_tainted_is_invalid_input() -> None:
    """A replay clock bound to synthetic-tainted data is invalid input; world is
    provenance-derived and a caller may not declare world. (13.4 AC5 / FM-3)"""
    u = build_universe()
    tainted = _compile(
        u,
        run_spec={"bot": "mean-reversion", STARTING_CAPITAL_KEY: SEED},
        workspace_defaults={
            "account_id": "acct-replay",
            "venue_id": "venue-replay",
            "clock": CLOCK_REPLAY,
            "data_provenance": PROVENANCE_SYNTHETIC_TAINTED,
        },
    )
    assert is_refusal(tainted)
    assert tainted.category is RefusalCategory.INVALID_INPUT
    # a caller may not declare world at all
    declared = _compile(u, run_spec={"bot": "mean-reversion", STARTING_CAPITAL_KEY: SEED, "world": "replay"})
    assert is_refusal(declared)
    assert declared.category is RefusalCategory.INVALID_INPUT


# --- T13-111 -----------------------------------------------------------------
def test_t13_111_starting_capital_mandatory_book_may_default() -> None:
    """starting_capital is a mandatory run-spec field; the Book fragment may default it.
    (13.5 AC1)"""
    # mandatory: absent everywhere -> refusal naming the field
    absent = resolve_starting_capital(invocation_flags={}, run_spec={}, book_fragment_keys={})
    assert is_refusal(absent)
    assert absent.context["field"] == STARTING_CAPITAL_KEY
    # run spec supplies it
    from_spec = resolve_starting_capital(
        invocation_flags={}, run_spec={STARTING_CAPITAL_KEY: SEED}, book_fragment_keys={}
    )
    assert is_ok(from_spec)
    capital, overridden = from_spec.value
    assert capital == SEED and overridden is False
    # the Book fragment MAY default it when the run spec omits it
    from_book = resolve_starting_capital(
        invocation_flags={},
        run_spec={},
        book_fragment_keys={"sizing": {STARTING_CAPITAL_KEY: SEED}},
    )
    assert is_ok(from_book)
    book_capital, book_overridden = from_book.value
    assert book_capital == SEED and book_overridden is False
    # integration: real Book fragment has no starting_capital default -> compile refuses
    u = build_universe()
    missing = _compile(u, run_spec={"bot": "mean-reversion"})
    assert is_refusal(missing)
    assert missing.context["field"] == STARTING_CAPITAL_KEY


# --- T13-112 -----------------------------------------------------------------
def test_t13_112_seed_override_stamps_and_forces_unrated() -> None:
    """A seed-overriding invocation flag stamps the binding seed_overridden and forces
    the run's fold to unrated. (13.5 AC2 / FM-12)"""
    u = build_universe()
    base = unwrap(_compile(u), "base compile")
    overridden = unwrap(
        _compile(u, invocation_flags={STARTING_CAPITAL_KEY: Money(value=2_000_000, currency="USD", scale=2)}),
        "overridden compile",
    )
    assert overridden.replay_binding is not None
    assert overridden.replay_binding.seed_overridden is True
    assert overridden.fold_rating == FOLD_UNRATED
    assert overridden.starting_capital == Money(value=2_000_000, currency="USD", scale=2)
    # the overridden binding is a different identity from the un-overridden one
    assert overridden.binding_fp1 != base.binding_fp1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
