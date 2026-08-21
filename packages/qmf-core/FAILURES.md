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
