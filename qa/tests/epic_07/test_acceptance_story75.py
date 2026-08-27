"""L3 acceptance — Story 7.5 conformance / benchmark / catalog (T7-A17..A21)."""

from __future__ import annotations

import _fixtures as F
from qmf.core import is_ok, is_refusal
from qmf.indicators import (
    CONCEPT_WALK_REGISTER,
    BenchmarkBaseline,
    BenchmarkMeasurement,
    BenchmarkRung,
    Catalog,
    ChannelKind,
    ConceptExpression,
    DeclaredBudget,
    NoOpTickMeasurement,
    RegressionTolerance,
    RungMeasurement,
    check_expressible,
    evaluate_light_claim,
    graduate,
    guard_synchronous_entry,
    regression_gate,
    require_extension_identity,
    run_conformance,
    stamp_extension_identity,
)
from qmf.indicators.conformance import ConceptWalk


# --- T7-A17 [R25] P0 — light/heavy budget gate ------------------------------


def test_a17_no_declared_budget_is_heavy_by_default() -> None:
    verdict = F.unwrap(evaluate_light_claim(F.config()))
    assert verdict.verdict.value == "heavy"


def test_a17_light_claim_without_a_baseline_is_refused() -> None:
    """A configuration claiming light (declares a budget) without a recorded live-path rung
    baseline is refused at the tier-2 gate. Counter-case: light accepted with no baseline."""
    cfg = F.config(declared_budget=DeclaredBudget("live-path", True, "bounded-window", True))
    refusal = evaluate_light_claim(cfg, baseline=None)
    assert is_refusal(refusal), "a light claim with no baseline was not refused"


def test_a17_heavy_synchronous_entry_returns_unsupported_capability() -> None:
    """A heavy configuration's synchronous entry returns `unsupported capability`; a light
    one is permitted (proves the gate discriminates)."""
    heavy = F.unwrap(evaluate_light_claim(F.config()))
    refusal = guard_synchronous_entry(heavy)
    assert is_refusal(refusal)
    assert refusal.category.value == "unsupported capability"


def test_a17_a_fully_proven_light_claim_is_admitted() -> None:
    """The accept arm: a declared budget with a baseline and a passing benchmark measurement
    yields a light verdict whose synchronous entry is permitted."""
    cfg = F.config(declared_budget=DeclaredBudget("live-path", True, "bounded-window", True))
    fp = F.unwrap(cfg.fp1()).value
    baseline = F.unwrap(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=fp, os="windows-11", cpu_class="x86-64",
            burst_throughput_per_second=1_000, per_tick_latency_ns=500, peak_bytes=1_000,
        )
    )
    measurement = _measurement(fp, latency_ns=400, throughput=1_200, peak=900)
    verdict = evaluate_light_claim(cfg, baseline=baseline, measurement=measurement)
    assert is_ok(verdict) and verdict.value.verdict.value == "light"
    assert is_ok(guard_synchronous_entry(verdict.value))


# --- T7-A18 [R24] P1 — the benchmark two rungs + memory regression ----------


def test_a18_two_rungs_and_separate_noop_path_are_distinct() -> None:
    """The harness records two rungs and measures the no-op tick path separately (a distinct
    value type, never folded into a rung)."""
    assert {r.value for r in BenchmarkRung} == {"burst-throughput", "per-tick-latency"}
    assert NoOpTickMeasurement is not RungMeasurement


def test_a18_peak_memory_regression_fails_the_gate_exactly_as_a_slowdown() -> None:
    """A peak-memory regression fails the tier-2 gate exactly as a latency slowdown.
    Counter-case: a memory blow-up passing the gate."""
    fp = F.unwrap(F.config().fp1()).value
    baseline = F.unwrap(
        BenchmarkBaseline.try_create(
            configuration_fingerprint=fp, os="windows-11", cpu_class="x86-64",
            burst_throughput_per_second=1_000, per_tick_latency_ns=500, peak_bytes=1_000,
        )
    )
    clean = regression_gate(baseline, _measurement(fp, 400, 1_200, 900))
    assert is_ok(clean), "a within-budget measurement was refused"
    mem_regress = regression_gate(baseline, _measurement(fp, 400, 1_200, 5_000))
    assert is_refusal(mem_regress) and mem_regress.category.value == "policy rejection"
    latency_regress = regression_gate(baseline, _measurement(fp, 5_000, 1_200, 900))
    assert is_refusal(latency_regress) and latency_regress.category.value == "policy rejection"


# --- T7-A19 [R23] P1 — conformance concept-walk stays expressible -----------


def _concept_config(concept: ConceptWalk):
    """A configuration that structurally expresses `concept` (built from qmf-core nouns)."""
    if concept is ConceptWalk.MULTI_INSTRUMENT:
        return F.config(inputs=[
            F.series_input("a", source=F.instrument("EURUSD")),
            F.series_input("b", source=F.instrument("GBPUSD")),
        ])
    if concept is ConceptWalk.MULTI_BARSPEC:
        return F.config(inputs=[
            F.series_input("a", bar_spec={"kind": "time-interval", "seconds": 60}),
            F.series_input("b", bar_spec={"kind": "time-interval", "seconds": 300}),
        ])
    if concept is ConceptWalk.DERIVED_SERIES_CHAINING:
        up = F.unwrap(F.config().fp1())
        return F.config(inputs=[F.series_input("a", upstream_fingerprint=up)])
    if concept is ConceptWalk.NON_TIME_BAR_KINDS:
        return F.config(inputs=[F.series_input("a", bar_spec={"kind": "tick-count", "count": 100})])
    if concept is ConceptWalk.CALENDAR_SCOPED_WINDOWS:
        from qmf.core import Duration
        return F.config(warm_up_time_bound=F.unwrap(Duration.try_create(3_600_000_000_000)))
    if concept is ConceptWalk.CALENDAR_ANCHORED_SAMPLING:
        return F.config(inputs=[F.series_input("a", bar_spec={"kind": "session", "session": "NY"})])
    if concept is ConceptWalk.PROJECTED_OUTPUTS_KNOWABLE_AT:
        return F.config(output_schema=[F.output_channel("sma", index_offset=1)])
    if concept is ConceptWalk.BATCH_ONLY_STATISTICAL:
        return F.config(supported_modes=["batch"])
    if concept is ConceptWalk.PRICE_VALUED_REENTRY:
        return F.config(output_schema=[F.output_channel("px", channel_kind=ChannelKind.EXACT_PRICE)])
    if concept is ConceptWalk.DELTA_TYPED_PRICE_DIFFERENCES:
        return F.config(
            formula_id="mom",
            output_schema=[F.output_channel("mom", channel_kind=ChannelKind.EXACT_PRICE)],
        )
    raise AssertionError(f"unhandled concept {concept}")


def test_a19_every_register_concept_is_expressible() -> None:
    """Each of the ten CT-16 concept-walk concepts is expressible as a governed
    configuration whose fp1 computes. Counter-case: a concept that cannot be expressed."""
    for concept in CONCEPT_WALK_REGISTER:
        check = F.unwrap(check_expressible(concept, _concept_config(concept)))
        assert check.expressible is True, f"{concept.value} not expressible: {check.defect}"
        assert check.fingerprint is not None


def test_a19_full_conformance_suite_passes_and_fails_closed() -> None:
    """The suite passes only when every register concept is covered and expressible; a
    configuration NOT expressing its concept fails the check (fails closed)."""
    expressions = [ConceptExpression(c, _concept_config(c)) for c in CONCEPT_WALK_REGISTER]
    report = F.unwrap(run_conformance(expressions))
    assert report.passed is True and report.missing == ()
    # Fail-closed control: a config that does not express multi-instrument is not expressible.
    bad = F.unwrap(check_expressible(ConceptWalk.MULTI_INSTRUMENT, F.config()))
    assert bad.expressible is False


# --- T7-A20 [R26] P1 — explicit registration through the one catalog --------


def test_a20_catalog_has_no_ambient_scan_surface() -> None:
    """Discovery is explicit registration; there is no scan/discover/autoload entry point.
    Counter-case: an ambient discovery method existing on the catalog."""
    catalog = Catalog.empty()
    for banned in ("scan", "discover", "autoload", "register_global"):
        assert not hasattr(catalog, banned), f"catalog exposes ambient discovery {banned!r}"


def test_a20_extension_identity_is_mandatory_in_every_artifact() -> None:
    """An artifact missing its distribution/version identity is non-conformant; stamping
    adds both mandatory fields."""
    extension = F.unwrap(
        graduate(distribution="qmf-ext-demo", version="1.0.0", formula_ids=["demo_formula"], research_artifact="RA-1")
    )
    catalog = F.unwrap(Catalog.empty().register(extension))
    assert catalog.resolve_distribution("qmf-ext-demo").value.identity.version == "1.0.0"
    stamped = F.unwrap(stamp_extension_identity(extension.identity, {"kind": "artifact"}))
    assert is_ok(require_extension_identity(stamped))
    assert is_refusal(require_extension_identity({"kind": "artifact"}))


# --- T7-A21 [R27] P1 — graduation with a lineage edge -----------------------


def test_a21_graduation_requires_a_research_lineage_edge() -> None:
    """A concept enters governed evidence only by graduating through the CT-16 extension
    shape WITH a lineage edge. Counter-case: graduation without a research artifact accepted."""
    ok = graduate(distribution="qmf-ext", version="0.1.0", formula_ids=["novel_formula"], research_artifact="RA-42")
    assert is_ok(ok)
    assert ok.value.lineage.research_artifact == "RA-42"
    missing = graduate(distribution="qmf-ext", version="0.1.0", formula_ids=["novel_formula"], research_artifact="  ")
    assert is_refusal(missing)


def test_a21_graduation_cannot_reown_a_core_formula() -> None:
    """A graduated formula colliding with an existing canonical owner is refused (each
    formula has exactly one canonical owner; a reference-owned formula must be wrapped)."""
    assert is_refusal(
        graduate(distribution="qmf-ext", version="0.1.0", formula_ids=["sma"], research_artifact="RA-1")
    )


def _measurement(fp: str, latency_ns: int, throughput: int, peak: int) -> BenchmarkMeasurement:
    burst = F.unwrap(RungMeasurement.try_create(BenchmarkRung.BURST_THROUGHPUT, throughput, 1_000_000_000, peak))
    latency = F.unwrap(RungMeasurement.try_create(BenchmarkRung.PER_TICK_LATENCY, 1, latency_ns, peak))
    noop = NoOpTickMeasurement(iterations=1, elapsed_ns=10, peak_bytes=peak)
    return BenchmarkMeasurement(configuration_fingerprint=fp, burst=burst, latency=latency, noop_tick=noop, peak_bytes=peak)
