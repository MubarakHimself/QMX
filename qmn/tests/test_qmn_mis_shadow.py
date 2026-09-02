"""Story 26.18 — zero-authority MIS shadow seam (TN-19 / DEC-0204)."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import TypeVar, cast

from qmf.core import (
    Duration,
    ExactRational,
    Fingerprint,
    Instant,
    Instrument,
    RefusalCategory,
    UnitKind,
    VenueId,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.core.refusal import Result
from qmn.config import config_init
from qmn.doors.http.evidence import handle_evidence_request
from qmn.doors.library import DoorRuntime, read_projections
from qmn.host.boot_ceremony import (
    CompositionFingerprintInputs,
    InMemoryBootAttemptSink,
    allocate_writer_ids,
    compute_composition_fp,
    reserved_supervisor_writer,
    run_boot_ceremony,
    run_check_mode,
)
from qmn.journal_dispatch import RecordingJournalSink
from qmn.mis import (
    IDENTITY_PRODUCER_ID,
    MONEY_PATH_CONSUMERS,
    SHADOW_COMPARISON_PROJECTION_KEY,
    SHADOW_COUNTED_TOWARD_MAX_SLICE_LATENCY,
    SHADOW_HAS_MONEY_PATH_AUTHORITY,
    SHADOW_ISOLATION_FAILURE_ID,
    SHADOW_LANE_PUBLISH_BOUND_VARIABLE,
    SHADOW_MANIFEST_PREFIX,
    SHADOW_SURFACE,
    SHADOW_WRITER_ROLE,
    SHADOW_WRITER_STREAM,
    SQS_PRODUCER_ID,
    CanonicalFeedState,
    FormulaNature,
    FrontierFrame,
    GovernedConsumer,
    ProducerReadiness,
    ProducerSlot,
    ShadowCondition,
    SignalSnapshot,
    SnapshotLane,
    allocate_shadow_writer,
    assemble_shadow_snapshot,
    compare_shadow_to_governed,
    configure_mis_producer,
    consume_signal_snapshot,
    empty_mis_catalog,
    empty_shadow_catalog,
    evaluate_shadow_lane,
    mint_signal_snapshot,
    refuse_shadow_governed_wiring,
    refuse_shadow_light_claim,
    refuse_shadow_money_path,
    register_mis_producer,
    register_shadow_candidate,
    shadow_candidate_identities,
    shadow_comparison_projection,
    shadow_writer_stream_pair,
    sqs_baseline_key,
)
from qmn.mis.catalog import DeclaredFourBounds, MisProducerRole
from qmn.mis.shadow import ShadowLaneConfig
from qmn.mis.signal_snapshot import SqsReading

T = TypeVar("T")

_MIS_SRC = Path(__file__).resolve().parents[1] / "src" / "qmn" / "mis"


def _ok(result: Result[T]) -> T:
    assert is_ok(result), result
    return result.value


def _instant(ns: int = 1_000_000_000) -> Instant:
    return _ok(Instant.try_create(ns))


def _duration(ns: int) -> Duration:
    return _ok(Duration.try_create(ns))


def _venue() -> VenueId:
    return _ok(VenueId.try_create("ctrader"))


def _instrument(symbol: str = "EURUSD") -> Instrument:
    return _ok(Instrument.try_create(_venue(), symbol))


def _score(num: int = 5, den: int = 4) -> ExactRational:
    return _ok(ExactRational.try_create(num, den, UnitKind.DIMENSIONLESS_RATIO))


def _fp(label: str) -> Fingerprint:
    return _ok(fingerprint({"class": "cite", "label": label}))


def _sqs_slot(*, environment: str = "live") -> ProducerSlot:
    key = _ok(sqs_baseline_key(_venue(), environment, _instrument()))
    reading = _ok(
        SqsReading.try_create(
            key,
            readiness=ProducerReadiness.OK,
            labeler_version="v1",
            score=_score(),
            hard_block=False,
        )
    )
    return _ok(
        ProducerSlot.try_create(
            SQS_PRODUCER_ID,
            readiness=ProducerReadiness.OK,
            labeler_version="v1",
            sqs=reading,
        )
    )


def _identity_slot(*, version: str = "v1", detail: str = "tick") -> ProducerSlot:
    return _ok(
        ProducerSlot.try_create(
            IDENTITY_PRODUCER_ID,
            readiness=ProducerReadiness.OK,
            labeler_version=version,
            marker_detail=detail,
        )
    )


def _governed_snapshot(*, detail: str = "tick") -> SignalSnapshot:
    return _ok(
        mint_signal_snapshot(
            frontier_instant=_instant(),
            environment="live",
            feed_state=CanonicalFeedState.LIVE,
            producers=(_sqs_slot(), _identity_slot(detail=detail)),
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )


def _frame(**overrides: object) -> FrontierFrame:
    instrument = _instrument()
    body: dict[str, object] = {
        "frontier_instant": _instant(),
        "instrument": instrument,
        "environment": "live",
        "resolution": "tick",
        "known_at": _instant(),
        "sample_cadence": "quote",
    }
    body.update(overrides)
    return FrontierFrame(**body)  # type: ignore[arg-type]


def _config(*, enabled: bool = True, bound_ns: int = 5_000_000) -> ShadowLaneConfig:
    return _ok(ShadowLaneConfig.try_create(enabled=enabled, publish_bound=_duration(bound_ns)))


def _writer():
    return _ok(allocate_shadow_writer(machine="vps-a", boot_epoch_id="boot-1"))


def _shadow_fp(candidates: dict[str, str] | None = None) -> Fingerprint:
    identities = candidates if candidates is not None else {"identity": "v1"}
    return _ok(
        fingerprint(
            {"class": "shadow_composition_fp", "candidates": dict(sorted(identities.items()))}
        )
    )


def _composition_inputs(
    label: str = "shadow",
    *,
    candidates: Mapping[str, str] | None = None,
) -> CompositionFingerprintInputs:
    return CompositionFingerprintInputs(
        config_fp=_fp(f"config-{label}"),
        distribution_identities={
            "qmf": "lockstep",
            "qmb": "0.1.0",
            "qml": "0.1.0",
            "qmn": "0.1.0",
        },
        extension_identities={"qmf-calendar-forex": "1.0.0"},
        proto_release_tag="proto-1",
        tzdata_version="2026a",
        adapter_capability_fps=(_fp("cap-ctrader"),),
        registry_as_of_fp=_fp("as-of-1"),
        calendar_code_identities={
            "market_hours_calendar": "mh-code-1",
            "day_boundary_calendar": "db-code-1",
            "news_calendar": "news-code-1",
        },
        os_cpu_class="linux-x86_64",
        shadow_candidate_identities=candidates or {},
    )


def _candidate_identity():
    return _ok(configure_mis_producer(IDENTITY_PRODUCER_ID))


def test_shadow_surface_constants_and_zero_authority() -> None:
    assert SHADOW_SURFACE == "qmn.mis.shadow"
    assert SHADOW_WRITER_ROLE == "mis-shadow"
    assert SHADOW_WRITER_STREAM == "shadow-snapshot"
    assert SHADOW_MANIFEST_PREFIX == "mis/shadow/"
    assert SHADOW_LANE_PUBLISH_BOUND_VARIABLE == "shadow_lane_publish_bound"
    assert SHADOW_COMPARISON_PROJECTION_KEY == "mis_shadow_comparison"
    assert SHADOW_ISOLATION_FAILURE_ID == "compose.shadow_isolation"
    assert SHADOW_COUNTED_TOWARD_MAX_SLICE_LATENCY is False
    assert SHADOW_HAS_MONEY_PATH_AUTHORITY is False
    assert GovernedConsumer.BOOK_DOOR.value in MONEY_PATH_CONSUMERS
    assert GovernedConsumer.KSA.value in MONEY_PATH_CONSUMERS
    assert shadow_writer_stream_pair() == (SHADOW_WRITER_ROLE, SHADOW_WRITER_STREAM)


def test_candidate_registration_does_not_enter_governed_catalog() -> None:
    producer = _candidate_identity()
    governed = _ok(register_mis_producer(empty_mis_catalog(), producer))
    shadow = _ok(register_shadow_candidate(empty_shadow_catalog(), producer))
    assert IDENTITY_PRODUCER_ID in governed.producers
    assert IDENTITY_PRODUCER_ID in shadow.candidates
    assert IDENTITY_PRODUCER_ID not in empty_mis_catalog().producers
    still_governed = register_mis_producer(
        empty_mis_catalog(),
        producer,
        role=MisProducerRole.CANDIDATE,
    )
    assert is_refusal(still_governed)
    assert still_governed.category is RefusalCategory.POLICY_REJECTION
    identities = _ok(shadow_candidate_identities(shadow))
    assert identities[IDENTITY_PRODUCER_ID] == producer.version


def test_trained_and_unauthoritative_candidates_still_refused() -> None:
    producer = _candidate_identity()
    catalog = _ok(register_shadow_candidate(empty_shadow_catalog(), producer))
    duplicate = register_shadow_candidate(catalog, producer)
    assert is_refusal(duplicate)
    for name in ("kronos", "hmm", "bocpd", "ms-garch", "regime_classifier_v1"):
        # configure refuses these ids; registration must also refuse a renamed sneak.
        assert is_refusal(configure_mis_producer(name))


def test_candidate_light_claim_refused_heavy_by_construction() -> None:
    producer = _candidate_identity()
    assert is_ok(refuse_shadow_light_claim(producer))
    budget = DeclaredFourBounds(
        per_update_cost_rung="live-path",
        bounded_state=True,
        window_or_anchor_rule="frontier-as-of",
        synchronous_availability=True,
    )
    light = _ok(configure_mis_producer(IDENTITY_PRODUCER_ID, declared_budget=budget))
    refused = refuse_shadow_light_claim(light)
    assert is_refusal(refused)
    assert refused.category is RefusalCategory.POLICY_REJECTION
    assert is_refusal(register_shadow_candidate(empty_shadow_catalog(), light))


def test_registering_candidates_does_not_alter_governed_composition_fp() -> None:
    base = _composition_inputs("node-config")
    governed, shadow = _ok(compute_composition_fp(base))
    assert shadow is None
    catalog = _ok(register_shadow_candidate(empty_shadow_catalog(), _candidate_identity()))
    identities = dict(_ok(shadow_candidate_identities(catalog)))
    with_candidates = _composition_inputs("node-config", candidates=identities)
    governed2, shadow2 = _ok(compute_composition_fp(with_candidates))
    assert governed2 == governed
    assert shadow2 is not None
    assert shadow2 != governed2
    changed = _composition_inputs("node-config", candidates={"identity": "v2"})
    governed3, shadow3 = _ok(compute_composition_fp(changed))
    assert governed3 == governed
    assert shadow3 != shadow2


def test_shadow_writer_is_distinct_from_supervisor_and_command() -> None:
    writer = _writer()
    assert writer.role == SHADOW_WRITER_ROLE
    assert writer.stream == SHADOW_WRITER_STREAM
    supervisor = _ok(reserved_supervisor_writer(machine="vps-a", boot_epoch_id="boot-1"))
    allocation = _ok(
        allocate_writer_ids(
            machine="vps-a",
            boot_epoch_id="boot-1",
            streams=(
                ("command", "venue-a:acct-1"),
                ("risk", "binding-1"),
                shadow_writer_stream_pair(),
            ),
        )
    )
    assert allocation.pairwise_distinct() is True
    keys = {w.order_tuple() for w in allocation.all_writers}
    assert writer.order_tuple() in keys
    assert supervisor.order_tuple() in keys
    assert writer.order_tuple() != supervisor.order_tuple()


def test_shadow_publish_uses_own_prefix_and_cannot_be_consumed() -> None:
    catalog = _ok(register_shadow_candidate(empty_shadow_catalog(), _candidate_identity()))
    snap = _ok(
        assemble_shadow_snapshot(
            catalog,
            _frame(),
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    assert snap.lane is SnapshotLane.SHADOW
    assert IDENTITY_PRODUCER_ID in snap.producers
    sink = RecordingJournalSink()
    evaluation = _ok(
        evaluate_shadow_lane(
            governed=_governed_snapshot(),
            catalog=catalog,
            frame=_frame(),
            config=_config(),
            elapsed=_duration(1_000),
            writer=_writer(),
            shadow_composition_fp=_shadow_fp(),
            sequence=0,
            journal_sink=sink,
        )
    )
    assert evaluation.publication is not None
    assert evaluation.publication.manifest_prefix == SHADOW_MANIFEST_PREFIX
    assert evaluation.publication.writer.role == SHADOW_WRITER_ROLE
    assert evaluation.publication.counted_toward_max_slice_latency is False
    assert evaluation.publication.authority == "none"
    assert evaluation.slice_delayed is False
    assert evaluation.substituted_governed is False
    assert evaluation.governed.lane is SnapshotLane.GOVERNED
    row = cast("dict[str, object]", sink.appended[0])
    assert row["manifest_prefix"] == SHADOW_MANIFEST_PREFIX
    assert row["gating"] is False
    assert row["authorizes"] is False
    for consumer in (GovernedConsumer.BOOK_DOOR, GovernedConsumer.KSA, "book_door"):
        refused = consume_signal_snapshot(snap, consumer=consumer, decision_at=_instant())
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION


def test_candidate_output_never_reaches_money_path_consumers() -> None:
    for consumer in (
        "book_door",
        "ksa",
        "bot",
        "venue",
        "command",
        "control",
        "seat",
        "command_fold",
    ):
        refused = refuse_shadow_money_path(consumer)
        assert is_refusal(refused)
        assert refused.category is RefusalCategory.POLICY_REJECTION
        assert refused.context["failure_id"] == SHADOW_ISOLATION_FAILURE_ID
    assert is_ok(refuse_shadow_governed_wiring(()))
    wired = refuse_shadow_governed_wiring(("book_door",))
    assert is_refusal(wired)


def test_wiring_shadow_into_governed_consumer_refuses_boot() -> None:
    inputs = _composition_inputs("boot-shadow")
    outcome = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-shadow-wire",
            machine="vps-a",
            composition_inputs=inputs,
            boot_attempt_sink=InMemoryBootAttemptSink(),
            shadow_consumer_wiring=("book_door",),
        )
    )
    assert outcome.stand_down_alive is True
    assert outcome.sealed is False
    assert outcome.opens_sequencer is False
    assert outcome.failure_id == SHADOW_ISOLATION_FAILURE_ID
    check = run_check_mode(
        boot_epoch_id="check-shadow-wire",
        machine="vps-a",
        composition_inputs=inputs,
        boot_attempt_sink=InMemoryBootAttemptSink(),
        shadow_consumer_wiring={"identity": "ksa"},
    )
    assert is_refusal(check)
    ok_boot = _ok(
        run_boot_ceremony(
            boot_epoch_id="boot-shadow-ok",
            machine="vps-a",
            composition_inputs=inputs,
            boot_attempt_sink=InMemoryBootAttemptSink(),
            shadow_consumer_wiring=(),
        )
    )
    assert ok_boot.sealed is True
    assert ok_boot.failure_id is None


def test_missing_late_refused_disagree_recorded_without_substitution() -> None:
    catalog = _ok(register_shadow_candidate(empty_shadow_catalog(), _candidate_identity()))
    governed = _governed_snapshot(detail="tick")
    # Missing SQS on the candidate side; identity present.
    on_time = _ok(
        evaluate_shadow_lane(
            governed=governed,
            catalog=catalog,
            frame=_frame(),
            config=_config(),
            elapsed=_duration(10),
            writer=_writer(),
            shadow_composition_fp=_shadow_fp(),
            journal_sink=RecordingJournalSink(),
        )
    )
    by_id = {row.producer_id: row for row in on_time.comparison}
    assert by_id[SQS_PRODUCER_ID].condition is ShadowCondition.MISSING
    assert IDENTITY_PRODUCER_ID in by_id
    assert on_time.substituted_governed is False
    assert on_time.governed is governed

    late_sink = RecordingJournalSink()
    late = _ok(
        evaluate_shadow_lane(
            governed=governed,
            catalog=catalog,
            frame=_frame(),
            config=_config(bound_ns=100),
            elapsed=_duration(5_000),
            writer=_writer(),
            shadow_composition_fp=_shadow_fp(),
            journal_sink=late_sink,
        )
    )
    assert late.publication is None
    assert late.slice_delayed is False
    assert late.counted_toward_max_slice_latency is False
    late_ids = set(catalog.candidate_ids())
    assert all(
        row.condition is ShadowCondition.LATE
        for row in late.comparison
        if row.producer_id in late_ids
    )
    dq = cast("dict[str, object]", late_sink.appended[0])
    assert dq["event_type"] == "data quality"
    assert dq["condition"] == ShadowCondition.LATE.value
    assert dq["slice_delayed"] is False
    assert dq["substitutes_governed"] is False

    look_ahead = _ok(
        assemble_shadow_snapshot(
            catalog,
            _frame(known_at=_instant(2_000_000_000)),
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    # identity is frontier-unbounded; a feed/spread candidate would refuse.
    assert look_ahead.lane is SnapshotLane.SHADOW

    disagree_shadow = _ok(
        mint_signal_snapshot(
            frontier_instant=_instant(),
            environment="live",
            feed_state=CanonicalFeedState.LIVE,
            producers=(_identity_slot(detail="bar"),),
            decision_freshness_bound=_duration(5_000_000_000),
            lane=SnapshotLane.SHADOW,
        )
    )
    compared = _ok(compare_shadow_to_governed(governed, disagree_shadow, catalog=catalog))
    identity_row = next(row for row in compared if row.producer_id == IDENTITY_PRODUCER_ID)
    assert identity_row.condition is ShadowCondition.DISAGREE
    assert identity_row.source_identity.startswith(IDENTITY_PRODUCER_ID)
    assert identity_row.frontier_instant == governed.frontier_instant


def test_refused_candidate_records_source_identity_without_delay() -> None:
    producer = _ok(
        configure_mis_producer(
            "feed_state",
            parameters={
                "live_max_age": _duration(1_000_000_000),
                "degraded_max_age": _duration(5_000_000_000),
            },
        )
    )
    catalog = _ok(register_shadow_candidate(empty_shadow_catalog(), producer))
    snap = _ok(
        assemble_shadow_snapshot(
            catalog,
            _frame(known_at=_instant(2_000_000_000)),
            decision_freshness_bound=_duration(5_000_000_000),
        )
    )
    slot = snap.producers["feed_state"]
    assert slot.readiness is ProducerReadiness.REFUSED
    compared = _ok(compare_shadow_to_governed(_governed_snapshot(), snap, catalog=catalog))
    feed_row = next(row for row in compared if row.producer_id == "feed_state")
    assert feed_row.condition is ShadowCondition.REFUSED
    assert "feed_state" in feed_row.source_identity


def test_disabling_or_removing_shadow_lane_does_not_change_decisions() -> None:
    governed = _governed_snapshot()
    fp_before = _ok(governed.fingerprint())
    catalog = _ok(register_shadow_candidate(empty_shadow_catalog(), _candidate_identity()))
    disabled = _ok(
        evaluate_shadow_lane(
            governed=governed,
            catalog=catalog,
            frame=_frame(),
            config=_config(enabled=False),
            elapsed=_duration(1),
            writer=_writer(),
            shadow_composition_fp=_shadow_fp(),
        )
    )
    assert disabled.lane_enabled is False
    assert disabled.publication is None
    assert disabled.comparison == ()
    assert disabled.governed is governed
    assert _ok(disabled.governed.fingerprint()) == fp_before
    removed = _ok(
        evaluate_shadow_lane(
            governed=governed,
            catalog=empty_shadow_catalog(),
            frame=_frame(),
            config=_config(),
            elapsed=_duration(1),
            writer=_writer(),
            shadow_composition_fp=_shadow_fp({}),
        )
    )
    assert removed.publication is None
    assert _ok(removed.governed.fingerprint()) == fp_before
    assert removed.slice_delayed is False


def test_comparison_projection_is_publish_only_on_evidence_channel() -> None:
    catalog = _ok(register_shadow_candidate(empty_shadow_catalog(), _candidate_identity()))
    evaluation = _ok(
        evaluate_shadow_lane(
            governed=_governed_snapshot(),
            catalog=catalog,
            frame=_frame(),
            config=_config(),
            elapsed=_duration(1),
            writer=_writer(),
            shadow_composition_fp=_shadow_fp(),
            journal_sink=RecordingJournalSink(),
        )
    )
    payload = shadow_comparison_projection(evaluation)
    assert payload["publishes"] is True
    assert payload["acts"] is False
    assert payload["gating"] is False
    assert payload["authorizes"] is False
    runtime = DoorRuntime(
        boot_epoch="boot-1",
        composition_fp="fp1:composition",
        knowledge_time_ns=1_000,
        watermark_ns=900,
        source_time_ns=950,
        receive_time_ns=980,
        evidence_channel_budget=50,
        config=_ok(config_init()),
        projections={SHADOW_COMPARISON_PROJECTION_KEY: dict(payload)},
    )
    published = _ok(read_projections(runtime))
    assert published["publishes"] is True
    assert published["acts"] is False
    stored = cast("dict[str, object]", published["projections"])
    assert SHADOW_COMPARISON_PROJECTION_KEY in stored
    http_get = _ok(handle_evidence_request(runtime, method="GET", path="/projections"))
    assert http_get["acts"] is False
    post = handle_evidence_request(runtime, method="POST", path="/projections")
    assert is_refusal(post)
    assert payload["authorizes"] is False


def test_shadow_module_stays_cpu_stdlib() -> None:
    banned = ("numpy", "torch", "sklearn", "tensorflow", "jax")
    text = (_MIS_SRC / "shadow.py").read_text(encoding="utf-8")
    for name in banned:
        assert f"import {name}" not in text
        assert f"from {name}" not in text
    assert "random" not in text
    assert "time.time" not in text
    assert FormulaNature.TRAINED.value == "trained"
