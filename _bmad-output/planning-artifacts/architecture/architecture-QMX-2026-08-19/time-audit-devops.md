# Time-model audit — DevOps/SRE lens (2026-08-19)

57 operational rules delivered; condensed here by theme with severities. These are architecture-stated RULES (mostly node/ops obligations), not qmf-core code.

## Clock trust (blockers)
- One authoritative clock per machine; VPS OS clock (NTP-disciplined) is the sole stamper of QMF-owned event times.
- No component stamps local events from a broker/provider clock; foreign time enters only as a foreign field.
- VPS runs chrony (≥4 sources, iburst, makestep boot-only). Windows w32time declared unfit to stamp authoritative evidence (travelling laptop = least trustworthy clock).
- Numeric drift bands with actions (ok ≤10ms / warn ≥25ms / no-new-entry ≥100ms / halt ≥250ms — sized to ~1s decisions); exceeding a band = typed refusal + journal record + node state change, never silent.
- "Unsynchronized" (no NTP source for N min) is a distinct state from "measured drift". Clock health is a per-decision-cycle precondition, not a startup check.

## Wall vs monotonic (blockers)
- Two clock kinds, type-level distinct: wall (UTC ns) = event meaning; monotonic = every duration (latency, timeouts, cooldowns, cadence).
- Never subtract wall timestamps for durations; never publish monotonic as a timestamp. State CLOCK_MONOTONIC vs BOOTTIME choice (suspend!).
- Cross-machine "latency" is an offset-contaminated estimate, never a measured duration.
- In-process ordering uses a sequence counter, never wall time.

## Clock steps during live trading (blockers)
- Slew-only while live; steps only with node stopped; any step must be observable (wall-vs-monotonic divergence detector → journal + suspect-window marking).
- VPS may be live-migrated/paused without notice: on resume, gap over threshold = recorder data-gap record + node no-trade window.
- Linux: RTC in UTC, system tz UTC, TZ=UTC. Windows RTC local-time caveat for the Omakub dual-boot window (RealTimeIsUniversal=1 or never dual-boot a recording machine).
- DST invisible BECAUSE no local time is ever stored/keyed/compared — state as enforced invariant. Pinned tzdata version recorded as input to every session-calendar resolution and backtest.
- A session calendar may never be a fixed UTC offset from "broker server time" (cTrader-class servers run EET/EEST; feeds GAP-0037).

## Ordering (blockers)
- Cross-machine timestamps form a partial order only; arrival order ≠ timestamp order even on one machine.
- Every record stream carries per-writer strictly-increasing u64 sequence = ordering authority; timestamp is data.
- Deterministic tie-break (ts_ns, writer_id, seq), stable across replays. Store each source's actual resolution alongside ns value. Timestamps never primary/dedup keys. Replay order reproducible from stored fields alone.

## Broker/provider desync (blockers)
- Every foreign event stores THREE times: source-as-received (verbatim + declared zone/offset/resolution), local receive wall, local receive monotonic.
- CT-10 knowledge time = local-receive wall on the named authoritative clock.
- Rolling per-venue offset series (local_receive − source) min/median/p99; windowed minimum = skew estimate. Alarms push to operator; signal cannot distinguish broker clock error from network-path change — no auto-correction.
- Foreign timestamps never rewritten; corrections are annotations.
- Prop-firm platform clock = a third separately-identified clock; daily-loss/trading-day boundaries evaluated in the PROP FIRM's stated timezone.
- No cTrader timestamp trusted as UTC until verified against docs + live capture (GAP-0037).

## Leap seconds
- State posture (smear vs step), one policy across all machines, never mix smearing/non-smearing sources (up to 1s skew for a day otherwise).
- int64 UTC ns is POSIX time — cannot represent 23:59:60; state the exactness limitation. No leap second currently scheduled; abolition planned 2035.

## Sandbox/replay clocks (blockers)
- Simulated/replayed time is a DIFFERENT TYPE (SimNanos vs UtcNanos), not a flag.
- Every persisted record carries non-nullable time_domain (live | replay | simulated) participating in identity; replay may never write into the live evidence namespace.
- Clock access injected via a Clock port; nothing below the composition root calls the system clock. Replay clock = pure function of the data cursor.
- Factory sandboxes forbidden from producing timestamps that enter the evidence store; libfaketime-style overrides forbidden for anything with real-store write access.

## Solo-operator VPS flags
- Node must not trade before sync confirmed (chronyc waitsync, after time-sync.target).
- Every unsynchronized/stepped/paused window = explicit gap record (else backtests read holes as "no ticks").
- Logs/journals: UTC ISO-8601 with Z and stated precision, everywhere.
- Clock policy codified as provisioning config = precondition of the node running (next VPS won't remember).
- Export chrony offset/stratum/sync-age + per-venue skew + step counter as metrics with a PUSH alert path (no on-call rotation).
- Operator-facing times always labelled with timezone, UTC alongside.
- Writer identity in every record (node and tick recorder share the VPS).
- Large clock error breaks TLS/OAuth with misleading errors — document the diagnosis path.
- Filesystem/object-store mtimes are never evidence times; backup round-trips preserve stored timestamps as data.
- int64-ns overflow 2262; checked arithmetic on ns math. Prefer NTS or provider-internal NTP.
