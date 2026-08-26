"""Tier-1 tests for the ship-no-corpus licensing gate (Story 18.2, B-11)."""

from __future__ import annotations

import zipfile
from pathlib import Path
from typing import TypeVar

from qmb.data import (
    AUTHORITY_OPERATOR_RULING,
    CORPUS_EXTENSIONS,
    DUKASCOPY_PERSONAL_USE_AUTHORITY,
    DUKASCOPY_PERSONAL_USE_POLICY,
    LICENSE_TAG_STATES,
    NON_EVIDENCE_USES,
    AuthorityKind,
    NonEvidenceUse,
    SourceWindowRef,
    VenueLicensePolicy,
    admit_governed_evidence,
    allow_non_evidence_use,
    assert_distribution_has_no_corpus,
    data_front_identity,
    distribution_corpus_bytes,
    entitlement_lineage_edge,
    licensing_gate_identity,
    resolve_license_tag,
)
from qmf.core import RefusalCategory, Result, WriterId, fingerprint, is_ok, is_refusal
from qmf.data.dukascopy import PERSONAL_USE_LICENSE, LicenseTag
from qmf.registry import EdgeType

T = TypeVar("T")

_START = 1_705_316_400_000_000_000
_END = _START + 3_600_000_000_000


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _window(
    *,
    license_tag: object | None = PERSONAL_USE_LICENSE,
    venue: str = "dukascopy-fx",
    symbol: str = "EURUSD",
) -> SourceWindowRef:
    return SourceWindowRef(
        venue=venue,
        symbol=symbol,
        window_start_ns=_START,
        window_end_ns=_END,
        license_tag=license_tag,
        side="bid",
        source="dukascopy",
    )


def _policies() -> dict[str, VenueLicensePolicy]:
    return {DUKASCOPY_PERSONAL_USE_POLICY.venue: DUKASCOPY_PERSONAL_USE_POLICY}


def test_license_tag_taxonomy_is_explicit_interface() -> None:
    assert LICENSE_TAG_STATES == (
        "redistribution-ok",
        "internal-only",
        "denied",
        "unknown",
    )
    assert resolve_license_tag(None) is LicenseTag.UNKNOWN
    assert resolve_license_tag("") is LicenseTag.UNKNOWN
    assert resolve_license_tag("  ") is LicenseTag.UNKNOWN
    assert resolve_license_tag("internal-only") is LicenseTag.INTERNAL_ONLY
    assert resolve_license_tag("not-a-tag") is LicenseTag.UNKNOWN


def test_internal_only_with_operator_ruling_admits_governed_evidence() -> None:
    admitted = _ok(admit_governed_evidence(_window(), policies=_policies()))
    assert admitted.license_tag is LicenseTag.INTERNAL_ONLY
    assert admitted.granting_authority == DUKASCOPY_PERSONAL_USE_AUTHORITY
    assert admitted.authority_kind is AuthorityKind.OPERATOR_RULING
    assert admitted.authority_kind.value == AUTHORITY_OPERATOR_RULING
    payload = admitted.lineage_payload()
    assert payload["license_tag"] == "internal-only"
    assert payload["granting_authority"] == "DEC-0170"
    assert payload["venue"] == "dukascopy-fx"
    assert payload["symbol"] == "EURUSD"
    assert payload["window_start_ns"] == _START
    assert payload["window_end_ns"] == _END


def test_redistribution_ok_with_matching_venue_policy_passes() -> None:
    policy = VenueLicensePolicy(
        venue="open-feed",
        license_tag=LicenseTag.REDISTRIBUTION_OK,
        granting_authority="venue-policy:open-feed-tos",
        authority_kind=AuthorityKind.VENUE_POLICY,
    )
    window = _window(license_tag="redistribution-ok", venue="open-feed")
    admitted = _ok(admit_governed_evidence(window, policies={policy.venue: policy}))
    assert admitted.license_tag is LicenseTag.REDISTRIBUTION_OK
    assert admitted.granting_authority == "venue-policy:open-feed-tos"


def test_denied_unknown_absent_refuse_with_window_context() -> None:
    for tag in (LicenseTag.DENIED, LicenseTag.UNKNOWN, None, "", "bogus"):
        refused = admit_governed_evidence(_window(license_tag=tag), policies=_policies())
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["signal"] == "refuse-unlicensed-window"
        assert refused.context["venue"] == "dukascopy-fx"
        assert refused.context["symbol"] == "EURUSD"
        assert refused.context["window_start_ns"] == _START
        assert refused.context["window_end_ns"] == _END
        assert refused.context["license_tag"] in {
            "denied",
            "unknown",
        }


def test_granting_tag_without_policy_authority_is_refused() -> None:
    refused = admit_governed_evidence(_window(), policies=None)
    assert is_refusal(refused)
    assert refused.context["field"] == "granting_authority"
    assert refused.context["license_tag"] == "internal-only"


def test_recorded_tag_disagreeing_with_policy_is_refused() -> None:
    refused = admit_governed_evidence(
        _window(license_tag="redistribution-ok"),
        policies=_policies(),
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "granting_authority"
    assert refused.context["policy_license_tag"] == "internal-only"


def test_dukascopy_blank_tag_allows_non_evidence_but_blocks_governed() -> None:
    blank = _window(license_tag=None)
    refused = admit_governed_evidence(blank, policies=_policies())
    assert is_refusal(refused)
    assert refused.context["license_tag"] == "unknown"

    smoke = _ok(allow_non_evidence_use(blank, use=NonEvidenceUse.STRATEGY_LOGIC_SMOKE))
    assert smoke.venue == "dukascopy-fx"
    stress = _ok(allow_non_evidence_use(blank, use="infra-stress"))
    assert stress.symbol == "EURUSD"
    assert NON_EVIDENCE_USES == ("infra-stress", "strategy-logic-smoke")


def test_non_evidence_use_rejects_unknown_use_class() -> None:
    refused = allow_non_evidence_use(_window(license_tag=None), use="edge-claim")
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.INVALID_INPUT
    assert refused.context["field"] == "use"


def test_gate_is_pure_read_time_check_writes_nothing(tmp_path: Path) -> None:
    marker = tmp_path / "untouched.txt"
    marker.write_text("keep", encoding="utf-8")
    before = list(tmp_path.iterdir())
    _ok(admit_governed_evidence(_window(), policies=_policies()))
    allow_non_evidence_use(_window(license_tag=None))
    admit_governed_evidence(_window(license_tag=None), policies=_policies())
    after = list(tmp_path.iterdir())
    assert before == after
    assert marker.read_text(encoding="utf-8") == "keep"
    assert licensing_gate_identity()["writes"] is False


def test_passing_admission_rides_into_ct07_lineage() -> None:
    admitted = _ok(admit_governed_evidence(_window(), policies=_policies()))
    citing = _ok(fingerprint({"class": "citing-artifact", "run": "demo-1"}))
    writer = _ok(WriterId.try_create("node-a", "qmb", "license-gate", "boot-1"))
    edge = _ok(entitlement_lineage_edge(admitted, citing_ref=citing, writer=writer))
    assert edge.edge_type is EdgeType.OCCURRENCE_OF
    assert edge.from_ref == citing
    assert edge.to_ref == _ok(admitted.entitlement_fingerprint())


def test_distribution_bundles_zero_corpus_bytes(tmp_path: Path) -> None:
    clean = tmp_path / "clean-pkg"
    clean.mkdir()
    (clean / "qmb").mkdir()
    (clean / "qmb" / "__init__.py").write_text("# no corpus\n", encoding="utf-8")
    assert _ok(assert_distribution_has_no_corpus(clean)) == 0

    dirty = tmp_path / "dirty-pkg"
    dirty.mkdir()
    payload = dirty / "ticks.bi5"
    payload.write_bytes(b"\x00" * 32)
    measured = _ok(distribution_corpus_bytes(dirty))
    assert measured == 32
    refused = assert_distribution_has_no_corpus(dirty)
    assert is_refusal(refused)
    assert refused.context["signal"] == "refuse-ship-corpus"
    assert refused.context["corpus_bytes"] == 32

    wheel = tmp_path / "qmb-0.1.0-py3-none-any.whl"
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("qmb/__init__.py", "# clean\n")
        archive.writestr("qmb/data/corpus/ticks.bi5", b"\x01" * 8)
    refused_wheel = assert_distribution_has_no_corpus(wheel)
    assert is_refusal(refused_wheel)
    assert refused_wheel.context["corpus_bytes"] == 8

    qmb_src = Path(__file__).resolve().parents[1] / "src" / "qmb"
    assert _ok(assert_distribution_has_no_corpus(qmb_src)) == 0
    assert ".bi5" in CORPUS_EXTENSIONS


def test_data_front_identity_includes_licensing_gate() -> None:
    identity = data_front_identity()
    assert identity["ship_no_corpus"] is True
    assert identity["writes"] is False
    assert identity["license_tag_states"] == LICENSE_TAG_STATES
    assert identity["non_evidence_uses"] == NON_EVIDENCE_USES
    assert identity["dukascopy_personal_use_authority"] == DUKASCOPY_PERSONAL_USE_AUTHORITY


def test_mapping_window_shape_is_accepted() -> None:
    admitted = _ok(
        admit_governed_evidence(
            {
                "venue": "dukascopy-fx",
                "symbol": "EURUSD",
                "window_start_ns": _START,
                "window_end_ns": _END,
                "license_tag": "internal-only",
            },
            policies=_policies(),
        )
    )
    assert admitted.symbol == "EURUSD"
