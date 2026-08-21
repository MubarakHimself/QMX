# qmf-core — failure register

Failure-register entries for `qmf-core`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). One entry per designed failure mode,
written for someone who was not in the design room.

### FR-1: Invalid typed-refusal construction (CT-04)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** `TypedRefusal.try_create` validates its parts before building a
  refusal — an unknown `category` string, an unknown `retryability` string, a
  missing `after_condition_descriptor` when `retryability = after-condition`, or a
  descriptor supplied when `retryability` is anything else. The unchecked
  dataclass constructor performs no such validation and is for trusted internal
  callers that already hold valid parts.
- **Auto-recovery / retry:** none automatic. `try_create` RETURNS an
  `invalid input` `TypedRefusal` (retryability `no`) whose `context` names the
  offending `field` and the allowed values; the caller corrects the arguments and
  calls again. Nothing is raised across the boundary.
- **Visible degraded state:** none. No global or persistent state changes —
  construction simply does not yield the requested value.
- **Notification tier:** silent-log. This is a programming or wiring mistake
  surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a
  developer wiring a component passed a bad refusal category, a bad retryability,
  or a mismatched after-condition descriptor. The returned refusal's `context`
  says which field was wrong and what is allowed — fix the call and retry, and a
  retry with corrected parts constructs the value.

### FR-2: Invalid identity construction (CT-03)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** the `try_create` factory on each identity value type validates
  its parts before building — `VenueId.try_create` (a blank or non-string token),
  `Instrument.try_create` (a missing/invalid venue, or a missing/non-string
  symbol — the symbol is presence-checked, never parsed), `Venue.try_create` and
  `Account.try_create` (an invalid VenueId, a blank account id, or a role outside
  the fixed set `live | demo | paper-validation | paper-benched | prop-firm`), and
  `DatedRecord.try_create` (a non-date, empty content, an empty key, or a **null
  value** — null is prohibited in fp1 identity content). The unchecked dataclass
  constructor performs no such validation and is for trusted internal callers.
- **Auto-recovery / retry:** none automatic. Each factory RETURNS an
  `invalid input` `TypedRefusal` (retryability `no`) whose `context` names the
  offending `field` (and, for a null metadata value, the offending `key`); the
  caller corrects the arguments and calls again. Nothing is raised across the
  boundary, and a value is never defaulted in place of a missing part.
- **Visible degraded state:** none. Construction simply does not yield the
  requested identity value; no global or persistent state changes.
- **Notification tier:** silent-log. A malformed identity part is a programming
  or wiring mistake surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a
  developer wiring an instrument, venue, account, or dated record supplied a bad
  part — a blank venue token, a missing symbol, an unknown account role, or a null
  metadata field. The returned refusal's `context` says which field (and key) was
  wrong; fix the call and retry, and a retry with corrected parts constructs the
  value. History is never rewritten to fix a past record — a correction is a new
  dated record.

### FR-3: A true fp1 collision on a governed-evidence write (CT-05, FM-6)

- **Failure class:** `policy rejection` (a CT-04 refusal category). The pure core
  surface never returns `storage failure` — that category arises at the data
  boundary, not here (FM-8).
- **Detection:** `reconcile_write` (and the `GovernedEvidenceLedger.admit` /
  `.write` / `.write_label` guards that compose it) key a write on the presented
  `fp1` fingerprint's digest and compare bytes. A first write of a fingerprint is
  `stored`; a re-write whose bytes are **byte-identical** to what the fingerprint
  already addresses is `idempotent` and accepted silently; a re-write whose bytes
  **differ** under the same fingerprint is a true collision — identity is asserted
  while content differs.
- **Auto-recovery / retry:** none, and the stored bytes are **never overwritten**.
  The collision RETURNS a `policy rejection` `TypedRefusal` (retryability `no`)
  whose `context` names the offending `fingerprint`, carries `alarm: true`, and sets
  `notification_tier: alarm`. Nothing is raised across the boundary.
- **Visible degraded state:** none in this pure guard — the prior bytes remain and
  re-write idempotently. Downstream storage (qmf-registry / qmf-data) surfaces the
  alarm operationally.
- **Notification tier:** alarm. A true collision is an integrity event, not a
  routine input mistake, so it is surfaced loudly rather than silent-logged.
- **Product-user affordance:** nothing an end user did caused this; it is an
  identity-integrity event a developer or operator must investigate. The refusal's
  `context` names the fingerprint under which two different byte sequences collided;
  the write is refused and the original evidence is preserved untouched.

### FR-4: A `world = simulated` (or non-live) governed-evidence write (CT-05, FM-7)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `governed_namespace` (and the `GovernedEvidenceLedger.write` /
  `.write_label` guards that call it) route a governed-evidence write to a storage
  namespace derived from its `world`. `world = simulated` is reserved but **unusable
  in V1** — it has no governed namespace until the backtesting sitting defines
  simulated-time typing (GAP-0048). A non-live world (`replay`) routes to its own
  non-live namespace and can therefore never resolve to the live evidence namespace
  (`LIVE_EVIDENCE_NAMESPACE`); world separation is delivered by storage separation,
  not by identity distinctness alone.
- **Auto-recovery / retry:** none automatic. A `simulated` write RETURNS a `policy
  rejection` `TypedRefusal` (retryability `no`) whose `context` names `world` and
  cites `gap: GAP-0048`. Nothing is raised across the boundary.
- **Visible degraded state:** none. No bytes are written; the world policy is
  enforced before any fingerprint is computed.
- **Notification tier:** silent-log. Attempting a reserved-unusable world is a
  wiring/policy mistake surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a
  developer routed a `simulated` result into governed evidence before V1 admits it,
  or expected a non-live result to land in the live namespace. The refusal's
  `context` says the world was rejected and points at the gap; produce evidence in a
  supported world (`live` or `replay`), whose result lands in its own namespace.

### FR-5: A binary float on the money path (CT-01, FM-1)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** every CT-01 value factory — `Money.try_create`, `Price.try_create`,
  `Quantity.try_create`, `PriceDelta.try_create`, and the numerator/denominator of
  `ExactRational.try_create` and `ValueFactor.try_create` — narrows each numeric part
  through the `_as_plain_int` helper, which accepts a genuine `int` and rejects both a
  binary `float` and a `bool` (an `int` subclass). Any value that transitively feeds an
  order quantity, price, P&L, or balance is on the money path, where a binary float is
  banned because it silently carries representation error. The named conversion
  boundary (`Money.from_float` and its siblings) is the **only** sanctioned way a float
  re-enters, and it demands an explicit rounding mode. A Tier-1 static scanner
  (`tools/money_path_scan.py`) additionally fails the gate on any such float in shipped
  source.
- **Auto-recovery / retry:** none automatic. The factory RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names the offending `field` and
  explains that a float re-enters only through the named `from_float` boundary. Nothing
  is raised across the boundary, and the float is never rounded silently in place.
- **Visible degraded state:** none. Construction simply does not yield the requested
  value; no global or persistent state changes.
- **Notification tier:** silent-log. A float on the money path is a programming
  mistake surfaced as a value, not an operational alarm.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer
  passed a binary float where an exact scaled integer belongs. Build the value from an
  integer count at a declared scale (`Money.try_create(350, "USD", 2)` is `$3.50`), or —
  when a float genuinely must be converted — cross `Money.from_float(...)` and state the
  rounding mode explicitly; then retry.

### FR-6: Mixed-scale or incompatible-operand arithmetic (CT-01, FM-4)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** the arithmetic methods on the CT-01 value types check operand
  compatibility before combining. Same-currency `Money`, same-unit `Quantity`, and
  same-instrument `Price`/`PriceDelta` operands **auto-promote losslessly to the finer
  scale** (multiplying the coarser count by a power of ten, so no digit is lost or
  invented). An operand of a different currency, unit, instrument, or value class is
  refused — there is no implicit conversion and no silent rescale. `PriceDelta.to_money`
  likewise refuses when the monetary result is **not exactly representable** at the
  requested scale rather than rounding it silently (a rounding money-path boundary is
  stated elsewhere).
- **Auto-recovery / retry:** none automatic. The method RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names the mismatch (the two
  currencies/units/instruments, or the inexact amount). Nothing is raised.
- **Visible degraded state:** none. No value is produced and no state changes.
- **Product-user affordance:** nothing failed at runtime for an end user; a developer
  tried to add two amounts that are not the same kind (a different currency or unit), to
  subtract prices of different instruments, or to force an inexact amount into too few
  decimal places. Cross-currency and cross-unit conversion goes through a **named
  value-factor boundary**, not implicit arithmetic; an inexact money result must cross a
  named **rounding** boundary. Supply compatible operands (or the right named boundary)
  and retry.
- **Notification tier:** silent-log.

### FR-7: An instrument-metadata dependency is absent — pip or value-factor (CT-01)

- **Failure class:** `unavailable dependency` (a CT-04 refusal category).
- **Detection:** two `PriceDelta` conversions require an input that is **sourced only
  from a CT-03/venue instrument-metadata record, never hardcoded**: `in_pips` needs the
  instrument pip/point size, and `to_money` needs the instrument value-factor (money per
  price-delta per quantity). When the required record is not supplied (the argument is
  `None`), the method refuses `unavailable dependency` rather than guessing a conversion.
  (A supplied-but-wrong input — a pip/value-factor belonging to a different instrument, a
  zero pip — is instead an `invalid input` refusal.)
- **Auto-recovery / retry:** none automatic. The method RETURNS an `unavailable
  dependency` `TypedRefusal` (retryability `no`) whose `context` names the missing
  `field` (`pip` or `value_factor`) and states it comes from an instrument-metadata
  record. Nothing is raised, and no conversion is fabricated.
- **Visible degraded state:** none in this pure core surface. The delta value itself is
  unchanged; only the requested conversion is withheld.
- **Notification tier:** silent-log. It is a wiring gap (the metadata was not provided),
  not an operational alarm.
- **Product-user affordance:** nothing an end user did caused this; a component asked to
  express a price move in pips, or to convert it to money, without the instrument's
  pip size / tick value on hand. Provide the instrument-metadata record (from the venue
  or CT-03 store) and retry — the same conversion then succeeds.

### FR-8: Nanosecond arithmetic overflow — refused, never wrapped (CT-02, FM-2)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** an `Instant` is an `int64` UTC-nanosecond count and a `Duration` is a
  signed `int64` nanosecond quantity; the representable range (1677–2262) **is** the
  `int64` range. Every arithmetic operation — `Instant.add_duration` / `Instant.difference`,
  `Duration.add` / `subtract` / `negate`, and `MonotonicReading.elapsed_since` — routes its
  result through the `_checked_int64` guard, and every factory range-checks its input via
  `_as_int64`. A result (or input) outside the `int64` range is refused rather than
  allowed to wrap to a wildly wrong instant. (`negate` on `int64` min is refused for the
  same reason — it has no positive `int64` counterpart.)
- **Auto-recovery / retry:** none automatic. The operation RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` carries the operands that
  overflowed. Nothing is raised, and no wrapped value is ever produced.
- **Visible degraded state:** none. No instant/duration is produced; no state changes.
- **Notification tier:** silent-log.
- **Product-user affordance:** nothing failed for an end user at runtime; a computation
  drove a timestamp or a span past the year-2262 / year-1677 boundary of the exact time
  representation. This is almost always a bad input (a corrupt or absurd timestamp);
  correct the input and retry. Time results are deliberately refused rather than silently
  wrapped, so a nonsense instant can never enter evidence.

### FR-9: Cross-calendar trading-date comparison (CT-02, FM-3)

- **Failure class:** `invalid input` (a CT-04 refusal category).
- **Detection:** a `TradingDate` carries its `CalendarIdentity` (rule set + version +
  tzdata version) **in-band**, and equality/ordering hold **only within one calendar
  identity**. `TradingDate.compare` (and `equals`, which is built on it) refuse when the
  other trading date carries a different `CalendarIdentity` — two dates from different
  calendars are genuinely incomparable, so the answer is a typed refusal, never a
  silently-wrong `True`/`False` or a coerced order.
- **Auto-recovery / retry:** none automatic. The comparison RETURNS an `invalid input`
  `TypedRefusal` (retryability `no`) whose `context` names both calendar identities.
  Nothing is raised.
- **Visible degraded state:** none. No comparison result is produced; no state changes.
- **Notification tier:** silent-log.
- **Product-user affordance:** nothing failed for an end user; a component compared two
  trading days defined under **different market calendars** (or different rule-set/tzdata
  versions) as if they were the same kind of day. Normalize both dates to one calendar
  identity before comparing, then retry — within a single calendar the comparison reads
  the civil date directly.

### FR-10: tzdata pin mismatch at a calendar extension's import (CT-02, FM-5)

- **Failure class:** `unavailable dependency` (a CT-04 refusal category).
- **Detection:** a calendar extension forces `TZPATH` to its **pinned** tzdata package
  and then calls `verify_tzdb_pin(pinned_version, resolved_version)` at import. The seam
  compares the pinned IANA tzdb version against the version actually resolved; a mismatch
  is refused `unavailable dependency`, so a fingerprint can never attest a tzdb that was
  not the one actually used. (`qmf-core` embeds no tzdata and reads no environment — the
  extension resolves both versions and this seam only compares them.)
- **Auto-recovery / retry:** none automatic. The seam RETURNS an `unavailable
  dependency` `TypedRefusal` (retryability `no`) whose `context` carries both the
  `pinned` and the `resolved` versions. Nothing is raised, and the extension refuses to
  operate on the wrong tzdb rather than producing calendar results under it.
- **Visible degraded state:** the calendar extension does not come up — any calendar
  computation that depends on it is blocked until the environment provides the pinned
  tzdb. Nothing downstream silently proceeds on the wrong time-zone rules.
- **Notification tier:** operator-visible. A wrong or missing pinned tzdb is an
  environment/deployment fault an operator must fix (install or pin the correct tzdata
  package), not a routine input mistake.
- **Product-user affordance:** a component that needed market-calendar times could not
  start because the installed time-zone database is not the exact pinned version the
  platform requires. No calendar result was produced under the wrong data. Install /
  pin the required tzdata version (the refusal names the expected and the found version)
  and retry.

### FR-11: Equal-instant causal comparison — concurrency, not a tie-break (CT-02)

- **Failure class:** `policy rejection` (a CT-04 refusal category).
- **Detection:** `compare_causal` compares two `Instant`s **only** (never the
  `(instant, writer, sequence)` ordering key). For distinct instants it returns
  `BEFORE` / `AFTER`; at **equal** instants the two events are concurrent, and the
  comparison deliberately **refuses** rather than invent an order. The ordering key
  exists for replay determinism, not causal meaning, so causality never tie-breaks
  concurrent events.
- **Auto-recovery / retry:** none, and none is wanted — this is the model's designed
  answer, not an error. The comparison RETURNS a `policy rejection` `TypedRefusal`
  (retryability `no`) whose `context` names the shared `instant`. Nothing is raised.
- **Visible degraded state:** none. The caller receives an explicit "concurrent" answer
  in place of a fabricated order.
- **Notification tier:** silent-log.
- **Product-user affordance:** nothing failed; the system was asked "did A cause B?" for
  two events stamped at the exact same instant, and it correctly answers "these are
  concurrent — causality cannot order them" instead of guessing. If a deterministic
  *replay* order is what you need (not causality), use the `(instant, writer, sequence)`
  ordering key, which is a total order with no causal meaning.

### FR-12: An unpersistable sink write blocks the command stream (Story 1.9, AR-47)

- **Failure class:** `storage failure` (a CT-04 refusal category).
- **Detection:** `qmf-core` performs no I/O; an outer package persists **only** through
  an injected `ObservationSink` / `JournalSink` / `RecordSink` protocol seam. A sink that
  cannot durably land a write returns the canonical `storage failure` refusal built by
  `unpersistable(...)`, and the writer that holds the `WriterId` recognizes it with the
  `is_unpersistable(...)` predicate. This is the **most operationally consequential**
  designed failure in the package: it does not merely reject a value, it **blocks a live
  command stream**.
- **Auto-recovery / retry:** no automatic drop and no assumed success — the intent is
  never lost. The refusal carries a `retryability` answer: an ordinary transient store
  outage is retryable, and a rotation-store failure uses `after-condition` retryability
  with the descriptor **"successful store or operator re-provision"** (the retry gate is
  a real event, not a fixed delay). The writer retries the *same* write once the gate is
  met.
- **Visible degraded state:** the writer **blocks its command stream** until the store
  recovers — it does not evaluate state on an unrecorded observation, dispatch a control
  action that was not journaled, or write a record that did not land. The stream is
  paused, not abandoned; queued intent waits rather than being dropped or duplicated.
- **Notification tier:** operator-visible (escalating to alarm for a rotation-store or a
  prolonged outage). A blocked command stream is an operational condition an operator
  must see and clear — the store is down and forward progress has stopped by design.
- **Product-user affordance:** an action could not be recorded because durable storage
  was unavailable, so the platform **paused rather than proceeding on an unsaved event or
  pretending it saved**. Nothing produced a wrong or half-applied result. Once storage is
  restored (or the operator re-provisions the rotation store), the paused write is
  retried and the stream resumes exactly where it stopped; a retry re-attempts the same
  durable write and, on success, unblocks the stream.
