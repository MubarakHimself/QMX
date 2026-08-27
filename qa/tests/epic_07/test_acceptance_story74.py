"""L3 acceptance — Story 7.4 streaming + equality + restore (T7-A13..A16).
Gate 2 anchor: streaming ≡ batch by construction under the integer-ULP comparator."""

from __future__ import annotations

import _fixtures as F
from qmf.core import World, is_ok, is_refusal
from qmf.indicators import (
    PresenceState,
    ReferenceKernel,
    StreamingIndicator,
    assert_mode_equality,
    compute_batch,
    series_equal_within_ulps,
)


def _feed(instance, values, presence=None, start=1_000):
    states = presence or [PresenceState.PRESENT] * len(values)
    for i, (v, s) in enumerate(zip(values, states, strict=True)):
        result = instance.update({"close": F.observation(v, s, start + i)})
        assert is_ok(result), f"update {i} refused: {result}"
    return instance


def _streaming_instance(cfg, kernel=None):
    return F.unwrap(
        StreamingIndicator.try_create(
            cfg,
            kernel=kernel or ReferenceKernel(),
            world=World.REPLAY,
            writer_id=F.writer(),
            scope=F.scope(),
            input_scales={"close": 2},
        )
    )


# --- T7-A13 [R19] P0 — the equality law over the real reference -------------


def test_a13_streaming_equals_batch_under_the_default_ulp_comparator() -> None:
    """Streaming ≡ batch same-process/same-build over cold-state canonical inputs, at the
    default integer-ULP comparator (0). Counter-case: streaming diverging from batch."""
    cfg = F.config(warm_up=2)  # sma period 3 (reference lookback 2)
    values = [100, 102, 101, 103, 105, 104, 106, 108, 107]
    batch = F.unwrap(compute_batch(cfg, {"close": F.input_series(values)}, kernel=ReferenceKernel(), world=World.REPLAY))
    stream = _feed(_streaming_instance(cfg), values)
    streamed = F.unwrap(stream.result())
    equal = assert_mode_equality(cfg, batch, streamed)
    assert is_ok(equal) and equal.value is True, "streaming did not equal batch"


def test_a13_negative_control_different_series_are_not_equal() -> None:
    """Falsifiability: the equality law is not vacuously green — batch over one series and
    streaming over a different series are reported unequal."""
    cfg = F.config(warm_up=2)
    batch = F.unwrap(compute_batch(cfg, {"close": F.input_series([100, 102, 101, 103, 105])}, kernel=ReferenceKernel(), world=World.REPLAY))
    stream = _feed(_streaming_instance(cfg), [200, 150, 175, 190, 210])
    streamed = F.unwrap(stream.result())
    equal = assert_mode_equality(cfg, batch, streamed)
    assert is_ok(equal) and equal.value is False


# --- T7-A14 [R21] P0 — restore-equivalence ----------------------------------


def test_a14_restore_then_n_equals_cold_warm_then_n() -> None:
    """restore-then-N-updates equals cold-warm-then-the-same-N-updates. Counter-case: the
    restored stream diverging from the never-snapshotted one."""
    cfg = F.config(warm_up=2)
    first = [100, 102, 101, 103]
    rest = [105, 104, 106, 108]

    warm = _feed(_streaming_instance(cfg), first)
    snapshot = F.unwrap(warm.snapshot())
    restored = F.unwrap(
        StreamingIndicator.restore(
            snapshot, configuration=cfg, kernel=ReferenceKernel(), world=World.REPLAY, current_scope=F.scope()
        )
    )
    _feed_from(restored, rest, start=1_000 + len(first))
    restored_result = F.unwrap(restored.result())

    cold = _feed(_streaming_instance(cfg), first + rest)
    cold_result = F.unwrap(cold.result())

    for channel, cold_series in cold_result.outputs.items():
        equal = series_equal_within_ulps(cold_series, restored_result.outputs[channel], 0)
        assert F.unwrap(equal) is True, f"restore-equivalence broke on channel {channel}"


def test_a14_result_from_restored_state_carries_the_snapshot_fingerprint() -> None:
    """A result computed from restored state carries the snapshot fingerprint as an input
    fingerprint (restore-equivalence provenance); a cold result does not."""
    cfg = F.config(warm_up=2)
    warm = _feed(_streaming_instance(cfg), [100, 102, 101, 103])
    snapshot = F.unwrap(warm.snapshot())
    snapshot_fp = F.unwrap(snapshot.fingerprint())
    restored = F.unwrap(
        StreamingIndicator.restore(
            snapshot, configuration=cfg, kernel=ReferenceKernel(), world=World.REPLAY, current_scope=F.scope()
        )
    )
    _feed_from(restored, [105, 104], start=1_100)
    label = F.unwrap(restored.result()).label
    assert snapshot_fp in label.input_fingerprints, "snapshot fingerprint not carried as an input fingerprint"


# --- T7-A15 [R22] P0 — cross-tuple restore refusal --------------------------


def test_a15_restore_on_a_different_tuple_is_unavailable_dependency() -> None:
    """Restoring on a different (OS, arithmetic-reference build) tuple is an
    `unavailable dependency` refusal. Counter-case: a cross-tuple restore silently accepted."""
    cfg = F.config(warm_up=2)
    warm = _feed(_streaming_instance(cfg), [100, 102, 101])
    snapshot = F.unwrap(warm.snapshot())
    other_os = F.scope(os_name="linux-6", build="ta-lib==0.7.1")
    refusal = StreamingIndicator.restore(
        snapshot, configuration=cfg, kernel=ReferenceKernel(), world=World.REPLAY, current_scope=other_os
    )
    assert is_refusal(refusal)
    assert refusal.category.value == "unavailable dependency"
    other_build = F.scope(os_name="windows-11", build="ta-lib==0.8.0")
    refusal2 = StreamingIndicator.restore(
        snapshot, configuration=cfg, kernel=ReferenceKernel(), world=World.REPLAY, current_scope=other_build
    )
    assert is_refusal(refusal2)
    assert refusal2.category.value == "unavailable dependency"


# --- T7-A16 [R18] P1 — the one named stateful class -------------------------


def test_a16_exactly_one_feeder_a_second_feeder_is_refused() -> None:
    """Exactly one feeder (one WriterId holder); a second feeder is refused. Counter-case:
    a foreign WriterId permitted to feed."""
    cfg = F.config(warm_up=0)
    stream = _streaming_instance(cfg, kernel=F.EchoKernel())
    held = F.writer()
    assert is_ok(stream.update({"close": F.observation(100, PresenceState.PRESENT, 1_000)}, feeder=held))
    foreign = F.writer(stream="other-feeder", machine="m2")
    refusal = stream.update({"close": F.observation(101, PresenceState.PRESENT, 1_001)}, feeder=foreign)
    assert is_refusal(refusal)
    assert refusal.category.value == "unsupported capability"


def test_a16_every_output_carries_its_producing_input_sequence_number() -> None:
    cfg = F.config(warm_up=0)
    stream = _streaming_instance(cfg, kernel=F.EchoKernel())
    seqs = []
    for i in range(3):
        seqs.append(F.unwrap(stream.update({"close": F.observation(10 + i, PresenceState.PRESENT, 1_000 + i)})).sequence)
    assert seqs == [0, 1, 2]
    assert stream.health().next_sequence == 3


def test_a16_instance_count_scales_with_distinct_configurations_not_consumers() -> None:
    """Two instances of the same configuration carry the same configuration fingerprint (a
    reader mints none); health() is exposed."""
    cfg = F.config(warm_up=0)
    a, b = _streaming_instance(cfg), _streaming_instance(cfg)
    assert a.configuration_fingerprint() == b.configuration_fingerprint()
    other = _streaming_instance(F.config(warm_up=0, formula_id="ema"))
    assert other.configuration_fingerprint() != a.configuration_fingerprint()
    assert hasattr(a, "health") and a.health().observations_seen == 0


def _feed_from(instance, values, start):
    for i, v in enumerate(values):
        assert is_ok(instance.update({"close": F.observation(v, PresenceState.PRESENT, start + i)}))
