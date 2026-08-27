"""Epic 13 — L3 contract-conformance tests (T13-301..309).

CT-* round-trip / boundary / invalid-refusal and fp1 identity via the single
qmf-core implementation. A failing assertion is a FINDING.
"""

from __future__ import annotations

import pytest
from qmf.core.exact import Money
from qmf.core.fingerprint import World, canonical_bytes, fingerprint
from qmf.core.identity import VenueId
from qmf.core.refusal import RefusalCategory, Retryability, is_ok, is_refusal
from qmf.registry import RESERVED_KIND_NAMES, EdgeType, KindRegistry
from qmf.risk.binding import (
    STATE_CARRY_COUNTERS,
    BmsInstanceId,
    BookBindingRecord,
    BookInstanceId,
    CapabilityCheckResult,
    PositionModel,
    StateCarry,
    StateCarryChoice,
)

import qmb
from _fixtures import DEFAULTS, SEED, base_run_spec, build_universe, unwrap, writer
from qmb.config import (
    CONFIG_FRAGMENT_CLASS,
    DISPLAY_FIELDS,
    FRAGMENT_FORMAT_VERSION,
    IDENTITY_FIELDS,
    RUN_CONFIG_FORMAT_VERSION,
    ConfigFragment,
    ResolvedRunConfig,
    check_incomparable_to_live,
    coerce_starting_capital,
    compile_run_config,
    fragment_identity,
    layers_identity,
    materialize_bms_fragment,
    materialize_book_fragment,
    merge_book_bms_keys,
    run_config_identity,
)
from qmb.registryread import read_port_identity


def _compiled(u):
    return unwrap(
        compile_run_config(
            u.port,
            book_fragment=u.book_fragment,
            bms_fragment=u.bms_fragment,
            run_spec=base_run_spec(),
            workspace_defaults=dict(DEFAULTS),
        ),
        "compile",
    )


# --- T13-301 -----------------------------------------------------------------
def test_t13_301_book_fragment_derived_lineaged_not_a_kind() -> None:
    """The Book fragment is a schema-valid, fingerprinted DERIVED artifact with a CT-07
    lineage edge back to the CT-22 source; not a registry kind, not free-hand. (13.3 AC1)"""
    u = build_universe()
    frag = u.book_fragment
    assert frag.fingerprint.value.startswith("fp1:sha256:")
    assert frag.source_kind == "book"
    assert frag.lineage is not None
    assert frag.lineage.edge_type is EdgeType.OCCURRENCE_OF
    assert frag.lineage.from_ref == frag.fingerprint
    assert frag.lineage.to_ref == frag.source_fp1
    # not a newly minted registry kind
    assert CONFIG_FRAGMENT_CLASS not in RESERVED_KIND_NAMES
    assert is_refusal(KindRegistry().contract_for(CONFIG_FRAGMENT_CLASS))
    # not free-hand-edited: it must project a real CT-22 book record, never a bms record
    wrong = materialize_book_fragment(u.port, "account-bms", writer("config-fragment"))
    assert is_refusal(wrong)
    assert wrong.category is RefusalCategory.INVALID_INPUT


# --- T13-302 -----------------------------------------------------------------
def test_t13_302_bms_fragment_derived_lineaged_to_ct27() -> None:
    """The BMS fragment is a derived, fingerprinted artifact carrying a CT-07 lineage
    edge back to the CT-27 source. (13.3 AC2)"""
    u = build_universe()
    frag = u.bms_fragment
    assert frag.fingerprint.value.startswith("fp1:sha256:")
    assert frag.source_kind == "bms"
    assert frag.lineage is not None
    assert frag.lineage.edge_type is EdgeType.OCCURRENCE_OF
    assert frag.lineage.from_ref == frag.fingerprint
    assert frag.lineage.to_ref == frag.source_fp1
    # a BMS materializer will not read a Book record
    wrong = materialize_bms_fragment(u.port, "scalping", writer("config-fragment"))
    assert is_refusal(wrong)
    assert wrong.category is RefusalCategory.INVALID_INPUT


# --- T13-303 -----------------------------------------------------------------
def test_t13_303_fragment_ad5_format_version_old_readable_unknown_refused() -> None:
    """A fragment stamps an AD-5 integer format version; format-N stays readable after
    N+1 ships; an unknown format version is unsupported, never best-effort. (13.3 AC4)"""
    u = build_universe()
    frag = u.book_fragment
    assert isinstance(frag.format_version, int) and frag.format_version == FRAGMENT_FORMAT_VERSION
    # format-1 fragment stays readable under a later-format reader
    reread = unwrap(
        ConfigFragment.try_read(frag.fp1_identity(), reader_format_version=2),
        "format-1 re-read under a newer reader",
    )
    assert reread.fingerprint == frag.fingerprint
    # a fragment claiming a newer format than the reader -> unsupported capability
    newer = dict(frag.fp1_identity())
    newer["format_version"] = 2
    newer_read = ConfigFragment.try_read(newer, reader_format_version=1)
    assert is_refusal(newer_read)
    assert newer_read.category is RefusalCategory.UNSUPPORTED_CAPABILITY
    # an unknown format version is unsupported, never a best-effort read
    unknown = dict(frag.fp1_identity())
    unknown["format_version"] = 999
    unknown_read = ConfigFragment.try_read(unknown, reader_format_version=999)
    assert is_refusal(unknown_read)
    assert unknown_read.category is RefusalCategory.UNSUPPORTED_CAPABILITY


# --- T13-304 -----------------------------------------------------------------
def test_t13_304_resolved_config_ad5_and_ad10_classification() -> None:
    """The resolved run-config stamps an AD-5 format version and declares its AD-10
    identity-vs-display classification; old artifacts stay readable. (13.4 AC4)"""
    u = build_universe()
    config = _compiled(u)
    assert config.format_version == RUN_CONFIG_FORMAT_VERSION == 1
    identity = config.fp1_identity()
    assert identity["identity_fields"]  # AD-10 identity set declared
    assert identity["display_fields"]  # AD-10 display set declared
    assert set(IDENTITY_FIELDS).isdisjoint(set(DISPLAY_FIELDS))
    # re-reads to the same identity/fingerprint
    reread = unwrap(ResolvedRunConfig.try_read(identity), "re-read")
    assert reread.fingerprint == config.fingerprint
    # readable under a later reader; a newer-format artifact refuses under a format-1 reader
    assert is_ok(ResolvedRunConfig.try_read(identity, reader_format_version=2))
    newer = dict(identity)
    newer["format_version"] = 2
    newer_read = ResolvedRunConfig.try_read(newer, reader_format_version=1)
    assert is_refusal(newer_read)
    assert newer_read.category is RefusalCategory.UNSUPPORTED_CAPABILITY


def _live_binding(config) -> BookBindingRecord:
    """A world=LIVE CT-28 binding of the same Book/BMS/account/venue as the run."""
    return unwrap(
        BookBindingRecord.try_create(
            unwrap(BookInstanceId.try_create("live-book-inst-1"), "live instance"),
            unwrap(
                BmsInstanceId.derive(
                    config.bms_fp1, "acct-replay", VenueId(value="venue-replay"), World.LIVE
                ),
                "live bms instance",
            ),
            VenueId(value="venue-replay"),
            "acct-replay",
            World.LIVE,
            config.book_fp1,
            config.bms_fp1,
            unwrap(
                StateCarry.try_create(dict.fromkeys(STATE_CARRY_COUNTERS, StateCarryChoice.RESET)),
                "state carry",
            ),
            CapabilityCheckResult(
                position_model=PositionModel.HEDGING,
                settlement_currency="USD",
                satisfied_capabilities=frozenset(),
                shared_flatten_signature=None,
                satisfied_sensor_baselines=frozenset(),
                live_path_rung_baseline_present=True,
                rank_table_non_contradicted=True,
            ),
        ),
        "live binding",
    )


# --- T13-305 -----------------------------------------------------------------
def test_t13_305_replay_binding_distinct_incomparable_to_live() -> None:
    """The minted binding is a valid CT-28 world=replay record, a different identity
    from any live binding of the same Book instance and incomparable to it. (13.5 AC3)"""
    u = build_universe()
    config = _compiled(u)
    binding = config.replay_binding
    assert binding is not None
    assert binding.world is World.REPLAY
    assert binding.record.world is World.REPLAY
    live = _live_binding(config)
    live_epoch = unwrap(live.fingerprint(), "live epoch")
    # different identity
    assert binding.fingerprint != live_epoch
    # incomparable: a cross-world read is refused, not merged
    compared = check_incomparable_to_live(binding, live)
    assert is_refusal(compared)
    assert compared.category is RefusalCategory.POLICY_REJECTION


# --- T13-306 -----------------------------------------------------------------
def test_t13_306_no_silent_idempotent_accept_across_worlds() -> None:
    """A replay binding never collapses into a live binding of the same Book instance:
    it fingerprints apart, and the incomparability check refuses rather than silently
    accepting (never AD-10's byte-identical idempotent accept). (13.5 AC3) [R-004]"""
    u = build_universe()
    config = _compiled(u)
    binding = config.replay_binding
    assert binding is not None
    live = _live_binding(config)
    live_epoch = unwrap(live.fingerprint(), "live epoch")
    # equal-fingerprint collapse is structurally prevented (world is in identity)
    assert binding.fingerprint != live_epoch
    # the check never returns a silent accept for a valid replay/live pair
    result = check_incomparable_to_live(binding, live)
    assert not is_ok(result)
    assert is_refusal(result)


# --- T13-307 -----------------------------------------------------------------
def test_t13_307_semver_display_only_excluded_from_identity() -> None:
    """QMB SemVer rides as display-only provenance, excluded from every fp1/identity
    computation; a SemVer change moves no fingerprint. (13.1 AC4)"""
    version = qmb.__version__
    u = build_universe()
    config = _compiled(u)
    identities = [
        qmb.identity_payload(),
        u.book_fragment.fp1_identity(),
        u.bms_fragment.fp1_identity(),
        config.fp1_identity(),
        read_port_identity(),
        run_config_identity(),
        layers_identity(),
        fragment_identity(),
    ]
    for identity in identities:
        assert version not in str(identity), f"SemVer leaked into identity: {identity}"
    # AD-10 classification: package_version is display, never identity
    assert "package_version" in DISPLAY_FIELDS
    assert "package_version" not in IDENTITY_FIELDS
    # the version string is absent from the config's canonical identity bytes
    raw = unwrap(canonical_bytes(config.fp1_identity()), "canonical bytes")
    assert version.encode() not in raw


# --- T13-308 -----------------------------------------------------------------
def test_t13_308_every_refusal_is_a_valid_ct04_value_returned() -> None:
    """Every refusal on an Epic-13 path is a valid CT-04 value: category in the seven,
    machine-readable context present (never null), retryability present — RETURNED
    across the boundary, never raised. (cross-cutting, CT-04)"""
    from _fixtures import CREATED_NS, SEVERITY, book_definition, definition_record, instant
    from qmb.registryread import (
        AsOfSet,
        DatedPointer,
        PassiveHub,
        RegistryReadPort,
        SupersedesRef,
    )

    u = build_universe()

    # a stale-evidence refusal from the read port
    first = definition_record("book-definition", book_definition())
    second = definition_record("book-definition", book_definition(loss_floor=900_000))
    older = unwrap(
        AsOfSet.try_create(
            instant(CREATED_NS),
            records=(first,),
            pointers=(unwrap(DatedPointer.try_create("scalping", first.stable_id, instant())),),
        )
    )
    fresher = unwrap(
        AsOfSet.try_create(
            instant(CREATED_NS + 1),
            records=(first, second),
            pointers=(
                unwrap(DatedPointer.try_create("scalping", second.stable_id, instant(CREATED_NS + 1))),
            ),
            supersedes=(unwrap(SupersedesRef.try_create(second.stable_id, first.stable_id)),),
        )
    )
    stale_hub = unwrap(PassiveHub.try_create((older, fresher)))
    stale_port = unwrap(
        RegistryReadPort.try_create(stale_hub, stale_evidence_severity=SEVERITY, bound=older)
    )

    refusals = {
        "stale": stale_port.resolve(first.stable_id),
        "synthetic_clock": compile_run_config(
            u.port,
            book_fragment=u.book_fragment,
            bms_fragment=u.bms_fragment,
            run_spec={"bot": "mean-reversion", "starting_capital": SEED},
            workspace_defaults={
                "account_id": "acct-replay",
                "venue_id": "venue-replay",
                "clock": "replay",
                "data_provenance": "synthetic-tainted",
            },
        ),
        "missing_seed": compile_run_config(
            u.port,
            book_fragment=u.book_fragment,
            bms_fragment=u.bms_fragment,
            run_spec={"bot": "mean-reversion"},
            workspace_defaults=dict(DEFAULTS),
        ),
        "collision": merge_book_bms_keys(
            {"accounting": {"a": 1}}, {"accounting": {"b": 2}}
        ),
        "name_at_version": compile_run_config(
            u.port,
            book_fragment=u.book_fragment,
            bms_fragment=u.bms_fragment,
            run_spec={"bot": "mean-reversion@1", "starting_capital": SEED},
            workspace_defaults=dict(DEFAULTS),
        ),
        "unknown_format": ConfigFragment.try_read(
            {**dict(u.book_fragment.fp1_identity()), "format_version": 999},
            reader_format_version=999,
        ),
        "non_usd_seed": coerce_starting_capital(Money(value=1_000, currency="EUR", scale=2)),
        "mcp_unsupported": __import__("qmb.doors.mcp", fromlist=["serve"]).serve(),
    }
    seven = set(RefusalCategory)
    retryabilities = set(Retryability)
    from collections.abc import Mapping

    for name, refusal in refusals.items():
        assert is_refusal(refusal), f"{name}: expected a RETURNED refusal, got {refusal!r}"
        assert refusal.category in seven, f"{name}: category {refusal.category} not one of seven"
        assert refusal.context is not None, f"{name}: context is null"
        assert isinstance(refusal.context, Mapping), f"{name}: context not a mapping"
        assert refusal.retryability in retryabilities, f"{name}: retryability missing"


# --- T13-309 (PARTIAL — config/binding seam; runtime open is Epic 14) --------
def test_t13_309_full_loss_price_required_before_open_PARTIAL() -> None:
    """PARTIAL: an AD-40 full-loss price is required before any open — enforced as a
    returned CT-04 refusal at the seam. Runtime open execution is Epic 14. (13.5 AC4)"""
    from qmb.execution import require_full_loss_before_open

    absent = require_full_loss_before_open(None)  # returned, not raised
    assert is_refusal(absent)
    present = require_full_loss_before_open("a-declared-full-loss-price")
    assert is_ok(present)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
