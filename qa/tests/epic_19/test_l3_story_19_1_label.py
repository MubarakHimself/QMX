"""L3 acceptance — Story 19.1: the canonical CT-32 artifact and its full label.

Requirements R1-R7. The artifact is minted from a resolved run-config; identity
is label-derived via qmf-core; world comes from the typed provenance field, never
a keys flag; a multi-role result is refused and writes nothing.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from conftest import NS, config, interval, mint_args, money, ok

from qmf.core.chrono import Instant
from qmf.core.fingerprint import EvidenceClass, World, canonical_bytes, fingerprint
from qmf.core.identity import AccountRole
from qmf.core.refusal import RefusalCategory, is_refusal
from qmf.core.exact import Money
from qmf.risk.performance import PerformanceResult
from qmb.config import ResolvedRunConfig
from qmb.runloop import STREAM_SET_KEY
from qmb.results.ct32 import (
    assemble_run_performance_result,
    mint_run_performance_result,
    result_identity,
    stored_ct32_fingerprint,
)


def _mint(cfg=None, **overrides) -> PerformanceResult:
    # overrides route through mint_args (evidence/trades/equity_curve/... are its
    # kwargs), never straight into mint_run_performance_result.
    cfg = cfg if cfg is not None else config()
    return ok(mint_run_performance_result(**mint_args(cfg, **overrides)))


def _walk_has_float(value: object) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, float):
        return True
    if isinstance(value, dict):
        return any(_walk_has_float(v) for v in value.values())
    if isinstance(value, list):
        return any(_walk_has_float(v) for v in value)
    return False


# --- A1: exactly one CT-32, returns fp1, no second report JSON [R1] P0 --------


def test_a1_assembly_writes_one_ct32_and_returns_qmfcore_fp1(out_dir: Path) -> None:
    artifact = _mint()
    stamped = ok(assemble_run_performance_result(artifact, output_dir=out_dir))

    path = out_dir / "results" / "ct-32.json"
    assert path.is_file()
    assert [p.name for p in (out_dir / "results").iterdir()] == ["ct-32.json"]
    assert not (out_dir / "report.json").exists()

    # fp1 is qmf-core's fingerprint of the artifact identity. The stored body is
    # identity PLUS the AD-10-excluded QMB extension block (chart set +
    # trade-event references, DEC-0163; FC-11): stripping the block leaves the
    # byte-canonical identity.
    import json as _json

    raw = path.read_bytes()
    body = _json.loads(raw.decode("utf-8"))
    extensions = body.pop("qmb_extensions")
    assert extensions["in_identity"] is False and extensions["ad10_excluded"] is True
    assert ok(canonical_bytes(body)) == ok(canonical_bytes(artifact.fp1_identity()))
    assert stamped == ok(artifact.fingerprint())
    assert stamped == ok(fingerprint(artifact.fp1_identity()))
    # a re-read of the stored bytes re-fingerprints to the same identity
    assert ok(stored_ct32_fingerprint(out_dir)) == stamped


def test_a1_second_assembly_is_refused_exactly_one_per_run(out_dir: Path) -> None:
    artifact = _mint()
    ok(assemble_run_performance_result(artifact, output_dir=out_dir))
    again = assemble_run_performance_result(artifact, output_dir=out_dir)
    assert is_refusal(again)
    assert again.category is RefusalCategory.STORAGE_FAILURE
    assert [p.name for p in (out_dir / "results").iterdir()] == ["ct-32.json"]


# --- A2: the full AD-12 label + account-binding role [R2] P0 -----------------


def test_a2_label_carries_full_ad12_and_evidence_range_verbatim() -> None:
    ev = interval(NS + 1000, NS + 5000)
    artifact = _mint(evidence=ev)
    label = artifact.result_label

    assert label.producer_contract_identity == ok(fingerprint(result_identity()))
    assert label.producer_contract_format_version == 1
    assert label.evidence_class is EvidenceClass.PROVISIONAL
    assert label.world is World.REPLAY
    # evidence time range copied verbatim — results/ neither extends into warm-up
    # nor rewrites the interval (the warm-up EXCLUSION itself is E14-owned).
    assert label.evidence_time_range == ev
    # occurrence/computation identity is content-derived from the label parts
    assert label.computation_identity == ok(fingerprint(label.fp1_identity()))
    # input fingerprints are present, order-significant, run-id first
    assert label.input_fingerprints[0] == config().fingerprint
    # the account-binding role lives on the container, single-valued
    assert artifact.account_binding_role is AccountRole.DEMO


# --- A3: AR-59 stamps [R3] P1 ------------------------------------------------


def test_a3_ar59_stamps_enter_input_fingerprints() -> None:
    data_fp = ok(fingerprint({"class": "data-window", "n": "recorded-eurusd"}))
    split_fp = ok(fingerprint({"class": "split-manifest", "n": "holdout-a"}))
    registry_at = ok(Instant.try_create(NS + 9))
    cfg = config(
        registry_as_of=registry_at,
        data_fingerprint=data_fp,
        split_fingerprint=split_fp,
        fidelity={"adapter_id": "fill.declared-path", "taint": "optimistic"},
    )
    inputs = _mint(cfg).result_label.input_fingerprints
    # data/split fingerprints are carried verbatim into identity
    assert data_fp in inputs
    assert split_fp in inputs
    # registry-as-of is folded through the pinned class wrapper
    registry_fp = ok(fingerprint({"class": "registry-as-of",
                                  "registry_as_of": registry_at.fp1_identity()}))
    assert registry_fp in inputs


def test_a3_rng_provenance_present_only_when_supplied() -> None:
    base = _mint(config()).result_label.input_fingerprints
    stochastic = _mint(
        config(rng_provenance={"family": "qmx-pcg64", "algorithm_version": "v1", "base_seed": 7})
    ).result_label.input_fingerprints
    # a non-stochastic run carries no RNG provenance; supplying it adds one input
    assert len(stochastic) == len(base) + 1


# --- A4: fp1 label-derived via qmf-core; no float bytes [R4] P0 --------------


def test_a4_identity_is_label_derived_and_reproduces() -> None:
    artifact = _mint()
    identity = artifact.fp1_identity()
    once = ok(fingerprint(identity))
    twice = ok(fingerprint(identity))
    assert once == twice == ok(artifact.fingerprint())


def test_a4_no_float_byte_enters_identity(out_dir: Path) -> None:
    # Falsifiability: the walker flags a planted float.
    assert _walk_has_float({"a": [1, {"b": 2.5}]}) is True

    artifact = _mint(trades=(), equity_curve=())
    ok(assemble_run_performance_result(artifact, output_dir=out_dir))
    body = json.loads((out_dir / "results" / "ct-32.json").read_text(encoding="utf-8"))
    assert _walk_has_float(body) is False


# --- A5: a multi-role result is a policy rejection, writes nothing [R5] P0 ----


def test_a5_multi_role_is_policy_rejection_and_writes_nothing(out_dir: Path) -> None:
    refused = mint_run_performance_result(**mint_args(config(account_role=("demo", "live"))))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION

    assembled = assemble_run_performance_result(refused, output_dir=out_dir)
    assert is_refusal(assembled)
    assert list(out_dir.iterdir()) == []  # nothing written


# --- A6: world is data-derived, never a flag; simulated refused [R6] P0 -------


def test_a6_world_comes_from_provenance_field_not_a_keys_flag() -> None:
    stamp = ok(fingerprint({"n": "world-flag-probe"}))
    # a config whose keys carry a misleading world="live" flag, but whose typed
    # provenance world is REPLAY
    cfg = ResolvedRunConfig(
        format_version=1,
        book_fp1=stamp,
        bms_fp1=stamp,
        bot_fp1=stamp,
        book_fragment_fp1=stamp,
        bms_fragment_fp1=stamp,
        keys={STREAM_SET_KEY: ("eurusd",), "world": "live"},
        clock="replay",
        data_provenance="recorded",
        world=World.REPLAY,
        fingerprint=stamp,
        binding_fp1=stamp,
    )
    artifact = _mint(cfg)
    # the label records the typed provenance world, ignoring the keys flag
    assert artifact.result_label.world is World.REPLAY


def test_a6_simulated_world_is_refused_no_artifact_in_v1() -> None:
    refused = mint_run_performance_result(**mint_args(config(world=World.SIMULATED)))
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert refused.context["field"] == "world"


# --- A7: optimistic taint => non-edge-claiming [R7] P1 -----------------------


def test_a7_non_optimistic_taint_fidelity_is_refused() -> None:
    # default (optimistic) passes
    ok(mint_run_performance_result(
        **mint_args(config(fidelity={"adapter_id": "fill.declared-path", "taint": "optimistic"}))
    ))
    # a calibrated (edge-claiming) taint is refused pre-GAP-0048
    refused = mint_run_performance_result(
        **mint_args(config(fidelity={"adapter_id": "fill.declared-path", "taint": "calibrated"}))
    )
    assert is_refusal(refused)
    assert refused.context["field"] == "taint"


def test_a7_artifact_carries_no_verdict_bearing_edge_claim() -> None:
    # the assembled identity has no edge/verdict claim smuggled into it
    body = _mint().fp1_identity()
    flat = json.dumps(body).casefold()
    for token in ("claims_edge", "edge_claim", "verdict", "split_budget"):
        assert token not in flat, token


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-q"]))
