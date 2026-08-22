"""Tier-1 tests for CT-12 dataset splits (Story 3.4; AC1, AC2, AC3, AC5)."""

from __future__ import annotations

from qmf.core import (
    CalendarIdentity,
    CivilDate,
    Duration,
    Instant,
    RefusalCategory,
    TemporalOrder,
    TradingDate,
    World,
    fingerprint,
    is_ok,
    is_refusal,
)
from qmf.data.splits import (
    CONTRACT_FORMAT_VERSION,
    DEFAULT_SPLIT_ROLES,
    KnowledgeKind,
    KnowledgeRecord,
    ProducerHorizon,
    SegmentRole,
    SplitBoundary,
    SplitManifest,
    SplitSegment,
)


def _calendar(version: str = "v3") -> CalendarIdentity:
    built = CalendarIdentity.try_create("forex-17NY", version, "2025a")
    assert is_ok(built)
    return built.value


def _instant(value_ns: int) -> Instant:
    built = Instant.try_create(value_ns)
    assert is_ok(built)
    return built.value


def _instant_boundary(value_ns: int) -> SplitBoundary:
    built = SplitBoundary.try_create(_instant(value_ns))
    assert is_ok(built)
    return built.value


def _trading_boundary(calendar: CalendarIdentity, year: int, month: int, day: int) -> SplitBoundary:
    civil = CivilDate.try_create(year, month, day)
    assert is_ok(civil)
    trading = TradingDate.try_create(calendar, civil.value)
    assert is_ok(trading)
    built = SplitBoundary.try_create(trading.value)
    assert is_ok(built)
    return built.value


def _producer(name: str = "indicator:sma-20", bound_ns: int = 50) -> ProducerHorizon:
    built = ProducerHorizon.try_create(name, bound_ns)
    assert is_ok(built)
    return built.value


def _manifest(
    *,
    calendar: CalendarIdentity | None = None,
    purge_ns: int = 100,
    embargo_ns: int = 100,
    world: World = World.REPLAY,
    producers: tuple[ProducerHorizon, ...] = (),
) -> SplitManifest:
    cal = calendar if calendar is not None else _calendar()
    segments = SplitManifest.default_split_segments(
        [_instant_boundary(1_000), _instant_boundary(2_000), _instant_boundary(3_000)]
    )
    assert is_ok(segments)
    built = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_trading_boundary(cal, 2025, 1, 1),
        purge_width=purge_ns,
        embargo_width=embargo_ns,
        world=world,
        cited_producers=producers,
    )
    assert is_ok(built)
    return built.value


# --- SplitBoundary ----------------------------------------------------------


def test_boundary_from_trading_date_and_instant() -> None:
    cal = _calendar()
    trading = _trading_boundary(cal, 2025, 1, 1)
    assert trading.kind == "trading-date"
    assert trading.calendar_identity == cal
    instant = _instant_boundary(1_000)
    assert instant.kind == "instant"
    assert instant.calendar_identity is None


def test_boundary_accepts_int_nanoseconds() -> None:
    built = SplitBoundary.try_create(1_500)
    assert is_ok(built)
    assert built.value.kind == "instant"
    assert built.value.instant is not None
    assert built.value.instant.value_ns == 1_500


def test_boundary_refuses_civil_date() -> None:
    civil = CivilDate.try_create(2025, 1, 1)
    assert is_ok(civil)
    result = SplitBoundary.try_create(civil.value)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context.get("field") == "boundary"


def test_boundary_refuses_junk() -> None:
    result = SplitBoundary.try_create("2025-01-01")
    assert is_refusal(result)
    assert result.context.get("field") == "boundary"


def test_boundary_compare_instants() -> None:
    low = _instant_boundary(1_000)
    high = _instant_boundary(2_000)
    before = low.compare(high)
    after = high.compare(low)
    equal = low.compare(_instant_boundary(1_000))
    assert is_ok(before) and before.value is TemporalOrder.BEFORE
    assert is_ok(after) and after.value is TemporalOrder.AFTER
    assert is_ok(equal) and equal.value is TemporalOrder.EQUAL


def test_boundary_compare_cross_kind_refuses() -> None:
    cal = _calendar()
    result = _instant_boundary(1_000).compare(_trading_boundary(cal, 2025, 1, 1))
    assert is_refusal(result)
    assert result.context.get("field") == "kind"


def test_boundary_compare_cross_calendar_refuses() -> None:
    left = _trading_boundary(_calendar("v3"), 2025, 1, 1)
    right = _trading_boundary(_calendar("v4"), 2025, 1, 1)
    result = left.compare(right)
    assert is_refusal(result)


def test_boundary_compare_non_boundary_refuses() -> None:
    result = _instant_boundary(1_000).compare(1_000)
    assert is_refusal(result)
    assert result.context.get("field") == "other"


def test_boundary_label_and_identity() -> None:
    cal = _calendar()
    trading = _trading_boundary(cal, 2025, 1, 2)
    assert trading.label() == "forex-17NY:v3:2025a:2025-01-02"
    instant = _instant_boundary(1_500)
    assert instant.label() == "1500"
    identity = trading.fp1_identity()
    assert identity["kind"] == "trading-date"
    assert identity["format_version"] == CONTRACT_FORMAT_VERSION
    assert "trading_date" in identity
    assert "instant" in instant.fp1_identity()


# --- SplitSegment -----------------------------------------------------------


def test_segment_try_create_and_identity() -> None:
    segment = SplitSegment.try_create(SegmentRole.TRAIN, _instant_boundary(1_000))
    assert is_ok(segment)
    assert segment.value.role is SegmentRole.TRAIN
    # role accepts its value string too
    from_str = SplitSegment.try_create("validation", _instant_boundary(2_000))
    assert is_ok(from_str)
    assert from_str.value.role is SegmentRole.VALIDATION
    identity = segment.value.fp1_identity()
    assert identity["role"] == "train"


def test_segment_refuses_bad_role_and_boundary() -> None:
    bad_role = SplitSegment.try_create("nonsense", _instant_boundary(1_000))
    assert is_refusal(bad_role)
    assert bad_role.context.get("field") == "role"
    bad_boundary = SplitSegment.try_create(SegmentRole.TRAIN, 1_000)
    assert is_refusal(bad_boundary)
    assert bad_boundary.context.get("field") == "boundary"


# --- ProducerHorizon --------------------------------------------------------


def test_producer_try_create_and_max_bound() -> None:
    producer = ProducerHorizon.try_create("  indicator:rsi  ", Duration(value_ns=30))
    assert is_ok(producer)
    assert producer.value.producer == "indicator:rsi"
    assert producer.value.warmup_plus_confirmation.value_ns == 30
    widest = ProducerHorizon.max_bound([_producer(bound_ns=10), _producer(bound_ns=70)])
    assert widest.value_ns == 70
    assert ProducerHorizon.max_bound([]).value_ns == 0


def test_producer_refuses_blank_and_bad_bound() -> None:
    blank = ProducerHorizon.try_create("  ", 10)
    assert is_refusal(blank)
    assert blank.context.get("field") == "producer"
    negative = ProducerHorizon.try_create("p", -1)
    assert is_refusal(negative)
    assert negative.context.get("field") == "warmup_plus_confirmation"
    not_a_number = ProducerHorizon.try_create("p", "soon")
    assert is_refusal(not_a_number)


def test_producer_identity() -> None:
    identity = _producer().fp1_identity()
    assert identity["producer"] == "indicator:sma-20"
    assert identity["class"] == "producer-horizon"


# --- KnowledgeRecord --------------------------------------------------------


def test_knowledge_record_try_create() -> None:
    record = KnowledgeRecord.try_create(
        observed_at=1_400, knowledge_time=1_500, kind=KnowledgeKind.INDICATOR
    )
    assert is_ok(record)
    assert record.value.observed_at.value_ns == 1_400
    assert record.value.kind is KnowledgeKind.INDICATOR
    assert record.value.calendar_identity is None


def test_knowledge_record_refusals() -> None:
    assert is_refusal(
        KnowledgeRecord.try_create(observed_at="x", knowledge_time=1, kind=KnowledgeKind.STRUCTURE)
    )
    assert is_refusal(
        KnowledgeRecord.try_create(observed_at=1, knowledge_time="x", kind=KnowledgeKind.STRUCTURE)
    )
    bad_kind = KnowledgeRecord.try_create(observed_at=1, knowledge_time=2, kind="guess")
    assert is_refusal(bad_kind)
    assert bad_kind.context.get("field") == "kind"
    bad_cal = KnowledgeRecord.try_create(
        observed_at=1, knowledge_time=2, kind=KnowledgeKind.STRUCTURE, calendar_identity="forex"
    )
    assert is_refusal(bad_cal)
    assert bad_cal.context.get("field") == "calendar_identity"


def test_knowledge_record_accepts_matching_calendar() -> None:
    cal = _calendar()
    record = KnowledgeRecord.try_create(
        observed_at=1, knowledge_time=2, kind=KnowledgeKind.STRUCTURE, calendar_identity=cal
    )
    assert is_ok(record)
    assert record.value.calendar_identity == cal


# --- H4: knowledge-time can never precede observed-at (no negative-gap leak) --


def test_knowledge_record_refuses_negative_gap() -> None:
    # observed 2500 after knowledge 500: a fact cannot become knowable before it becomes
    # observable, and the negative gap is exactly what slipped sealed-region data into
    # training past the embargo check (H4; DEC-0131).
    result = KnowledgeRecord.try_create(
        observed_at=2_500, knowledge_time=500, kind=KnowledgeKind.STRUCTURE
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context.get("field") == "knowledge_time"


def test_knowledge_record_allows_equal_observed_and_knowledge() -> None:
    # The boundary case: knowledge-time equal to observed-at (gap 0) is allowed.
    result = KnowledgeRecord.try_create(
        observed_at=1_500, knowledge_time=1_500, kind=KnowledgeKind.INDICATOR
    )
    assert is_ok(result)


def test_partition_record_defends_against_negative_gap_record() -> None:
    # A KnowledgeRecord built through the trusted-internal frozen constructor can carry a
    # negative gap; partition_record defends against it rather than placing sealed-region
    # data (observed 2500, in sealed-test) into an earlier segment by its knowledge time
    # (500, in train) — the exact AC3 leak (H4; DEC-0131).
    manifest = _manifest()
    leaking = KnowledgeRecord(
        observed_at=_instant(2_500),
        knowledge_time=_instant(500),
        kind=KnowledgeKind.STRUCTURE,
    )
    result = manifest.partition_record(leaking)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context.get("field") == "knowledge_time"


def test_partition_record_boundary_equal_lands_by_knowledge_time() -> None:
    # observed == knowledge (gap 0): the embargo covers it and the record is placed by its
    # knowledge time — the documented boundary-equal embargo rule.
    manifest = _manifest()
    record = KnowledgeRecord.try_create(
        observed_at=2_500, knowledge_time=2_500, kind=KnowledgeKind.STRUCTURE
    )
    assert is_ok(record)
    result = manifest.partition_record(record.value)
    assert is_ok(result)
    assert result.value is SegmentRole.SEALED_TEST


# --- SplitManifest: construction & identity ---------------------------------


def test_manifest_split_id_is_derived_and_deterministic() -> None:
    manifest = _manifest(producers=(_producer(bound_ns=50),))
    assert manifest.split_id.startswith("fp1:sha256:")
    assert manifest.split_id == manifest.fingerprint.value
    # The id is derived: re-fingerprinting the read-back identity content reproduces it.
    recomputed = fingerprint(manifest.fp1_identity())
    assert is_ok(recomputed)
    assert recomputed.value.value == manifest.split_id


def test_manifest_id_is_order_independent_in_producers() -> None:
    a = _producer("indicator:a", 20)
    b = _producer("indicator:b", 40)
    left = _manifest(producers=(a, b))
    right = _manifest(producers=(b, a))
    assert left.split_id == right.split_id


def test_manifest_default_roles_and_boundary_kind() -> None:
    manifest = _manifest()
    assert [segment.role for segment in manifest.segments] == list(DEFAULT_SPLIT_ROLES)
    assert manifest.boundary_kind == "instant"


def test_manifest_refuses_bad_calendar() -> None:
    segments = SplitManifest.default_split_segments(
        [_instant_boundary(1_000), _instant_boundary(2_000), _instant_boundary(3_000)]
    )
    assert is_ok(segments)
    result = SplitManifest.try_create(
        calendar_identity="forex-17NY",
        segments=segments.value,
        seal_boundary=_instant_boundary(3_000),
        purge_width=1,
        embargo_width=1,
        world=World.REPLAY,
    )
    assert is_refusal(result)
    assert result.context.get("field") == "calendar_identity"


def test_manifest_refuses_empty_and_non_sequence_segments() -> None:
    cal = _calendar()
    empty = SplitManifest.try_create(
        calendar_identity=cal,
        segments=[],
        seal_boundary=_instant_boundary(1),
        purge_width=0,
        embargo_width=0,
        world=World.REPLAY,
    )
    assert is_refusal(empty)
    assert empty.context.get("field") == "segments"
    non_seq = SplitManifest.try_create(
        calendar_identity=cal,
        segments="train",
        seal_boundary=_instant_boundary(1),
        purge_width=0,
        embargo_width=0,
        world=World.REPLAY,
    )
    assert is_refusal(non_seq)
    assert non_seq.context.get("field") == "segments"


def test_manifest_refuses_non_segment_element() -> None:
    cal = _calendar()
    result = SplitManifest.try_create(
        calendar_identity=cal,
        segments=["not-a-segment"],
        seal_boundary=_instant_boundary(1),
        purge_width=0,
        embargo_width=0,
        world=World.REPLAY,
    )
    assert is_refusal(result)
    assert result.context.get("field") == "segments"


def test_manifest_refuses_mixed_kind_segments() -> None:
    cal = _calendar()
    train = SplitSegment.try_create(SegmentRole.TRAIN, _instant_boundary(1_000))
    validation = SplitSegment.try_create(SegmentRole.VALIDATION, _trading_boundary(cal, 2025, 1, 1))
    assert is_ok(train)
    assert is_ok(validation)
    result = SplitManifest.try_create(
        calendar_identity=cal,
        segments=[train.value, validation.value],
        seal_boundary=_instant_boundary(3_000),
        purge_width=0,
        embargo_width=0,
        world=World.REPLAY,
    )
    assert is_refusal(result)
    assert result.context.get("field") == "segments"


def test_manifest_refuses_non_increasing_segments() -> None:
    cal = _calendar()
    train = SplitSegment.try_create(SegmentRole.TRAIN, _instant_boundary(2_000))
    validation = SplitSegment.try_create(SegmentRole.VALIDATION, _instant_boundary(1_000))
    assert is_ok(train)
    assert is_ok(validation)
    result = SplitManifest.try_create(
        calendar_identity=cal,
        segments=[train.value, validation.value],
        seal_boundary=_instant_boundary(3_000),
        purge_width=0,
        embargo_width=0,
        world=World.REPLAY,
    )
    assert is_refusal(result)
    assert result.context.get("field") == "segments"


def test_manifest_refuses_foreign_calendar_segment_boundary() -> None:
    cal = _calendar("v3")
    foreign = _calendar("v4")
    train = SplitSegment.try_create(SegmentRole.TRAIN, _trading_boundary(foreign, 2025, 1, 1))
    assert is_ok(train)
    result = SplitManifest.try_create(
        calendar_identity=cal,
        segments=[train.value],
        seal_boundary=_trading_boundary(cal, 2025, 2, 1),
        purge_width=0,
        embargo_width=0,
        world=World.REPLAY,
    )
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("field") == "segments"


def test_manifest_refuses_bad_and_foreign_seal_boundary() -> None:
    cal = _calendar()
    segments = SplitManifest.default_split_segments(
        [_instant_boundary(1_000), _instant_boundary(2_000), _instant_boundary(3_000)]
    )
    assert is_ok(segments)
    not_a_boundary = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary="2025-01-01",
        purge_width=0,
        embargo_width=0,
        world=World.REPLAY,
    )
    assert is_refusal(not_a_boundary)
    assert not_a_boundary.context.get("field") == "seal_boundary"
    foreign_seal = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_trading_boundary(_calendar("v9"), 2025, 1, 1),
        purge_width=0,
        embargo_width=0,
        world=World.REPLAY,
    )
    assert is_refusal(foreign_seal)
    assert foreign_seal.category is RefusalCategory.POLICY_REJECTION
    assert foreign_seal.context.get("field") == "seal_boundary"


def test_manifest_requires_purge_and_embargo() -> None:
    cal = _calendar()
    segments = SplitManifest.default_split_segments(
        [_instant_boundary(1_000), _instant_boundary(2_000), _instant_boundary(3_000)]
    )
    assert is_ok(segments)
    no_purge = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_instant_boundary(3_000),
        purge_width=None,
        embargo_width=1,
        world=World.REPLAY,
    )
    assert is_refusal(no_purge)
    assert no_purge.category is RefusalCategory.INVALID_INPUT
    assert no_purge.context.get("field") == "purge_width"
    no_embargo = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_instant_boundary(3_000),
        purge_width=1,
        embargo_width=None,
        world=World.REPLAY,
    )
    assert is_refusal(no_embargo)
    assert no_embargo.context.get("field") == "embargo_width"
    negative = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_instant_boundary(3_000),
        purge_width=-5,
        embargo_width=1,
        world=World.REPLAY,
    )
    assert is_refusal(negative)
    assert negative.context.get("field") == "purge_width"


def test_manifest_width_must_cover_producer_bound() -> None:
    cal = _calendar()
    segments = SplitManifest.default_split_segments(
        [_instant_boundary(1_000), _instant_boundary(2_000), _instant_boundary(3_000)]
    )
    assert is_ok(segments)
    wide = _producer("indicator:slow", 500)
    short_purge = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_instant_boundary(3_000),
        purge_width=100,
        embargo_width=500,
        world=World.REPLAY,
        cited_producers=[wide],
    )
    assert is_refusal(short_purge)
    assert short_purge.context.get("field") == "purge_width"
    short_embargo = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_instant_boundary(3_000),
        purge_width=500,
        embargo_width=100,
        world=World.REPLAY,
        cited_producers=[wide],
    )
    assert is_refusal(short_embargo)
    assert short_embargo.context.get("field") == "embargo_width"


def test_manifest_refuses_bad_world() -> None:
    cal = _calendar()
    segments = SplitManifest.default_split_segments(
        [_instant_boundary(1_000), _instant_boundary(2_000), _instant_boundary(3_000)]
    )
    assert is_ok(segments)
    result = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_instant_boundary(3_000),
        purge_width=0,
        embargo_width=0,
        world="nowhere",
    )
    assert is_refusal(result)
    assert result.context.get("field") == "world"


def test_manifest_accepts_world_string() -> None:
    cal = _calendar()
    segments = SplitManifest.default_split_segments(
        [_instant_boundary(1_000), _instant_boundary(2_000), _instant_boundary(3_000)]
    )
    assert is_ok(segments)
    result = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_instant_boundary(3_000),
        purge_width=0,
        embargo_width=0,
        world="live",
    )
    assert is_ok(result)
    assert result.value.world is World.LIVE


# --- default_split_segments -------------------------------------------------


def test_default_split_segments_pairs_roles() -> None:
    segments = SplitManifest.default_split_segments(
        [_instant_boundary(1_000), _instant_boundary(2_000), _instant_boundary(3_000)]
    )
    assert is_ok(segments)
    assert [segment.role for segment in segments.value] == list(DEFAULT_SPLIT_ROLES)


def test_default_split_segments_accepts_raw_values() -> None:
    segments = SplitManifest.default_split_segments([1_000, 2_000, 3_000])
    assert is_ok(segments)
    assert segments.value[0].boundary.kind == "instant"


def test_default_split_segments_wrong_count_refused() -> None:
    result = SplitManifest.default_split_segments([_instant_boundary(1_000)])
    assert is_refusal(result)
    assert result.context.get("field") == "boundaries"


def test_default_split_segments_bad_boundary_refused() -> None:
    result = SplitManifest.default_split_segments(["a", "b", "c"])
    assert is_refusal(result)


# --- admits_calendar / admits_producer --------------------------------------


def test_admits_calendar() -> None:
    cal = _calendar()
    manifest = _manifest(calendar=cal)
    assert is_ok(manifest.admits_calendar(cal))
    foreign = manifest.admits_calendar(_calendar("v4"))
    assert is_refusal(foreign)
    assert foreign.category is RefusalCategory.POLICY_REJECTION
    bad = manifest.admits_calendar("forex")
    assert is_refusal(bad)
    assert bad.category is RefusalCategory.INVALID_INPUT


def test_admits_producer_reuse_guard() -> None:
    manifest = _manifest(purge_ns=100, embargo_ns=100, producers=(_producer(bound_ns=50),))
    assert is_ok(manifest.admits_producer(_producer("indicator:ok", 80)))
    leaking = manifest.admits_producer(_producer("indicator:slow", 200))
    assert is_refusal(leaking)
    assert leaking.category is RefusalCategory.POLICY_REJECTION
    assert leaking.context.get("field") == "producer"
    bad = manifest.admits_producer("indicator:slow")
    assert is_refusal(bad)
    assert bad.category is RefusalCategory.INVALID_INPUT


# --- partition_record -------------------------------------------------------


def test_partition_record_by_knowledge_time() -> None:
    manifest = _manifest()
    train = KnowledgeRecord.try_create(
        observed_at=500, knowledge_time=500, kind=KnowledgeKind.INDICATOR
    )
    validation = KnowledgeRecord.try_create(
        observed_at=1_500, knowledge_time=1_500, kind=KnowledgeKind.INDICATOR
    )
    sealed = KnowledgeRecord.try_create(
        observed_at=2_500, knowledge_time=2_500, kind=KnowledgeKind.STRUCTURE
    )
    assert is_ok(train)
    assert is_ok(validation)
    assert is_ok(sealed)
    train_seg = manifest.partition_record(train.value)
    validation_seg = manifest.partition_record(validation.value)
    sealed_seg = manifest.partition_record(sealed.value)
    assert is_ok(train_seg) and train_seg.value is SegmentRole.TRAIN
    assert is_ok(validation_seg) and validation_seg.value is SegmentRole.VALIDATION
    assert is_ok(sealed_seg) and sealed_seg.value is SegmentRole.SEALED_TEST


def test_partition_record_refuses_non_record() -> None:
    result = _manifest().partition_record({"knowledge_time": 1})
    assert is_refusal(result)
    assert result.context.get("field") == "record"


def test_partition_record_refuses_foreign_calendar_row() -> None:
    manifest = _manifest(calendar=_calendar("v3"))
    record = KnowledgeRecord.try_create(
        observed_at=1_500,
        knowledge_time=1_500,
        kind=KnowledgeKind.INDICATOR,
        calendar_identity=_calendar("v4"),
    )
    assert is_ok(record)
    result = manifest.partition_record(record.value)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("field") == "calendar_identity"


def test_partition_record_accepts_matching_calendar_row() -> None:
    cal = _calendar()
    manifest = _manifest(calendar=cal)
    record = KnowledgeRecord.try_create(
        observed_at=1_500, knowledge_time=1_500, kind=KnowledgeKind.INDICATOR, calendar_identity=cal
    )
    assert is_ok(record)
    result = manifest.partition_record(record.value)
    assert is_ok(result)
    assert result.value is SegmentRole.VALIDATION


def test_partition_record_refuses_trading_date_split() -> None:
    cal = _calendar()
    train = SplitSegment.try_create(SegmentRole.TRAIN, _trading_boundary(cal, 2025, 1, 1))
    sealed = SplitSegment.try_create(SegmentRole.SEALED_TEST, _trading_boundary(cal, 2025, 6, 1))
    assert is_ok(train)
    assert is_ok(sealed)
    manifest = SplitManifest.try_create(
        calendar_identity=cal,
        segments=[train.value, sealed.value],
        seal_boundary=_trading_boundary(cal, 2025, 6, 1),
        purge_width=0,
        embargo_width=0,
        world=World.REPLAY,
    )
    assert is_ok(manifest)
    assert manifest.value.boundary_kind == "trading-date"
    record = KnowledgeRecord.try_create(
        observed_at=1_500, knowledge_time=1_500, kind=KnowledgeKind.INDICATOR
    )
    assert is_ok(record)
    result = manifest.value.partition_record(record.value)
    assert is_refusal(result)
    assert result.category is RefusalCategory.INVALID_INPUT
    assert result.context.get("field") == "segments"


def test_partition_record_beyond_last_boundary_refused() -> None:
    manifest = _manifest()
    record = KnowledgeRecord.try_create(
        observed_at=3_500, knowledge_time=3_500, kind=KnowledgeKind.STRUCTURE
    )
    assert is_ok(record)
    result = manifest.partition_record(record.value)
    assert is_refusal(result)
    assert result.context.get("field") == "knowledge_time"


def test_partition_record_straddle_refused_without_embargo() -> None:
    manifest = _manifest(purge_ns=100, embargo_ns=100)
    # observed in validation (1900), knowledge in sealed-test (2100), gap 200 > embargo 100.
    record = KnowledgeRecord.try_create(
        observed_at=1_900, knowledge_time=2_100, kind=KnowledgeKind.STRUCTURE
    )
    assert is_ok(record)
    result = manifest.partition_record(record.value)
    assert is_refusal(result)
    assert result.category is RefusalCategory.POLICY_REJECTION
    assert result.context.get("gap_ns") == 200


def test_partition_record_straddle_accepted_with_embargo() -> None:
    manifest = _manifest(purge_ns=300, embargo_ns=300)
    # Same straddle; gap 200 <= embargo 300, so it is admitted to the knowledge-time segment.
    record = KnowledgeRecord.try_create(
        observed_at=1_900, knowledge_time=2_100, kind=KnowledgeKind.STRUCTURE
    )
    assert is_ok(record)
    result = manifest.partition_record(record.value)
    assert is_ok(result)
    assert result.value is SegmentRole.SEALED_TEST


def test_partition_record_purge_zone_excludes_boundary_adjacent_record() -> None:
    # L9: purge_width is applied at partition time — a cleanly-placed (non-straddling) record
    # whose knowledge time lands within the purge width of a split boundary is excluded from
    # BOTH adjacent segments, not admitted to either. Default manifest boundaries 1000/2000/3000.
    manifest = _manifest(purge_ns=100, embargo_ns=100)
    # 1950 is 50ns before the 2000 boundary (validation side): within the 100ns purge, refused.
    validation_side = KnowledgeRecord.try_create(
        observed_at=1_950, knowledge_time=1_950, kind=KnowledgeKind.INDICATOR
    )
    assert is_ok(validation_side)
    refused_validation = manifest.partition_record(validation_side.value)
    assert is_refusal(refused_validation)
    assert refused_validation.category is RefusalCategory.POLICY_REJECTION
    assert refused_validation.context.get("boundary_ns") == 2_000
    assert refused_validation.context.get("purge_ns") == 100
    # 2050 is 50ns after the SAME boundary (sealed-test side): also within purge — BOTH sides.
    sealed_side = KnowledgeRecord.try_create(
        observed_at=2_050, knowledge_time=2_050, kind=KnowledgeKind.STRUCTURE
    )
    assert is_ok(sealed_side)
    refused_sealed = manifest.partition_record(sealed_side.value)
    assert is_refusal(refused_sealed)
    assert refused_sealed.category is RefusalCategory.POLICY_REJECTION
    assert refused_sealed.context.get("boundary_ns") == 2_000


def test_partition_record_at_purge_width_edge_is_admitted() -> None:
    # A record exactly purge_width from the boundary is at the edge and admitted (the width
    # covers strictly inside it): 1900 is exactly 100ns before the 2000 boundary.
    manifest = _manifest(purge_ns=100, embargo_ns=100)
    edge = KnowledgeRecord.try_create(
        observed_at=1_900, knowledge_time=1_900, kind=KnowledgeKind.INDICATOR
    )
    assert is_ok(edge)
    result = manifest.partition_record(edge.value)
    assert is_ok(result)
    assert result.value is SegmentRole.VALIDATION


def test_partition_record_zero_purge_has_no_purge_zone() -> None:
    # A zero purge width means no purge zone — a boundary-adjacent record is admitted.
    manifest = _manifest(purge_ns=0, embargo_ns=0)
    adjacent = KnowledgeRecord.try_create(
        observed_at=1_999, knowledge_time=1_999, kind=KnowledgeKind.INDICATOR
    )
    assert is_ok(adjacent)
    result = manifest.partition_record(adjacent.value)
    assert is_ok(result)
    assert result.value is SegmentRole.VALIDATION


# --- coercion edge cases (defensive branches) -------------------------------


def test_knowledge_record_accepts_instant_objects() -> None:
    record = KnowledgeRecord.try_create(
        observed_at=_instant(1_400), knowledge_time=_instant(1_500), kind=KnowledgeKind.STRUCTURE
    )
    assert is_ok(record)
    assert record.value.observed_at.value_ns == 1_400


def test_knowledge_record_refuses_non_string_kind() -> None:
    result = KnowledgeRecord.try_create(observed_at=1, knowledge_time=2, kind=7)
    assert is_refusal(result)
    assert result.context.get("field") == "kind"


def test_segment_refuses_non_string_role() -> None:
    result = SplitSegment.try_create(7, _instant_boundary(1_000))
    assert is_refusal(result)
    assert result.context.get("field") == "role"


def test_producer_accepts_duration_passthrough() -> None:
    producer = ProducerHorizon.try_create("p", Duration(value_ns=25))
    assert is_ok(producer)
    assert producer.value.warmup_plus_confirmation.value_ns == 25


def test_manifest_refuses_non_string_world() -> None:
    cal = _calendar()
    segments = SplitManifest.default_split_segments([1_000, 2_000, 3_000])
    assert is_ok(segments)
    result = SplitManifest.try_create(
        calendar_identity=cal,
        segments=segments.value,
        seal_boundary=_instant_boundary(3_000),
        purge_width=0,
        embargo_width=0,
        world=7,
    )
    assert is_refusal(result)
    assert result.context.get("field") == "world"
