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
