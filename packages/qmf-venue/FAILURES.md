# qmf-venue — failure register

Failure-register entries for `qmf-venue`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). The six entries below cover every
typed-refusal category reachable through the CT-18 capability, CT-19 command,
CT-20 observation, and CT-21 connection boundaries. They describe what remains
safe when a live-money boundary refuses instead of guessing or raising.

### FR-1: A malformed venue request is refused before effects

- **Failure class:** `invalid input` (CT-04).
- **Detection:** the CT-18/19/20/21 factories and door functions validate value
  types, required identities, observation kinds, timestamps, exact money fields,
  declared deadlines, and legal state transitions before dispatch or persistence.
  A malformed field, an absent required value, or an out-of-sequence observation
  returns the refusal with the failing field and reason in its context.
- **Auto-recovery / retry:** no automatic retry. Correct the request or observation
  and submit it as a new call; repeating the same malformed value returns the same
  refusal and performs no effect.
- **Visible degraded state:** the rejected command is not sent and the invalid
  observation is not treated as venue truth. Existing account state and the sensing
  pipe remain available; no terminal order outcome is invented.
- **Notification tier:** operator-visible for a command or observation boundary;
  validation-only construction mistakes may be silent-log during development.
- **Product-user affordance:** the request could not be understood safely. The
  refusal names what was malformed and why. Fix that value and retry; retrying does
  not reuse or partially execute the rejected request.

### FR-2: The venue does not declare the requested capability

- **Failure class:** `unsupported capability` (CT-04).
- **Detection:** capability resolution compares the command kind, order parameter,
  protection form, acknowledgement mode, and close scope with the measured CT-18
  declaration for that venue/account. Anything outside the declared subset is
  refused before the neutral port can call the adapter.
- **Auto-recovery / retry:** no blind retry. Re-probe after the broker or adapter
  capability declaration changes, or choose a command form the current declaration
  supports; an unchanged request remains refused.
- **Visible degraded state:** only the unsupported operation is blocked. Sensing,
  reconciliation, and other declared command kinds remain available, and no fallback
  parameter or broader close scope is invented.
- **Notification tier:** operator-visible typed refusal with the requested and
  declared capability context.
- **Product-user affordance:** this account or adapter does not promise the operation
  you requested. Choose a supported form, or re-run capability discovery after the
  venue changes; QMX will not translate it into a different order behind your back.

### FR-3: A required venue fact or dependency is unavailable

- **Failure class:** `unavailable dependency` (CT-04).
- **Detection:** first-connection probing and command admission require measured
  facts such as money exponent, timestamp unit, daily boundary, bar basis, pip
  formula, settlement currency, and a usable connection/profile. A missing or
  unverified fact returns this refusal instead of applying a platform default.
- **Auto-recovery / retry:** retry only after the named dependency becomes available:
  reconnect, complete the probe, or restore the required profile fact. There is no
  package-level retry loop and no fabricated default while it is absent.
- **Visible degraded state:** commands that depend on the missing fact are blocked.
  Credential-free sensing and any command whose required facts are already verified
  may continue; the missing fact is visibly unverified rather than guessed.
- **Notification tier:** operator-visible, escalating to alarm when a required live
  dependency remains unavailable and holds the command stream.
- **Product-user affordance:** QMX lacks a broker fact or connection it must verify
  before acting. Restore that dependency or complete the probe, then retry; the retry
  performs a fresh admission check and never reuses a guessed value.

### FR-4: A well-formed venue action violates a safety policy

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** the venue boundary rejects a structurally valid request when its
  world, account binding, secret-reference use, persistence request, or command policy
  is forbidden by the active CT-18/19/20/21 rules. The applicable rule and binding
  context ride the returned refusal.
- **Auto-recovery / retry:** no automatic retry. Change the prohibited request or
  obtain the required governed state and submit a new call; retrying unchanged cannot
  override the policy.
- **Visible degraded state:** the prohibited command is not dispatched and no venue
  outcome is synthesized. Existing observations and permitted risk-reducing commands
  remain readable and independently admissible.
- **Notification tier:** operator-visible; an integrity or secret-boundary policy
  breach escalates to alarm.
- **Product-user affordance:** the request was valid in shape but QMX is not allowed to
  perform it in the current state. The refusal names the governing rule. Change the
  request or resolve that state, then retry as a new admission.

### FR-5: Venue transport loses certainty about a submitted command

- **Failure class:** `transient venue failure` (CT-04).
- **Detection:** a timeout, disconnect, transport exception, or broker-side transient
  error during submission is recorded with wall and monotonic receive evidence. When
  acceptance versus absence cannot be proved, the command resolves to explicit
  `UNKNOWN`; timeout is never re-labelled rejection.
- **Auto-recovery / retry:** QMF never resubmits the command automatically. Sensing and
  reconciliation continue, but the stream clears only after an explicit recorded
  resolution (`observed-accepted`, `observed-absent`, or operator-attested).
- **Visible degraded state:** the affected `(venue, account)` command stream is blocked
  against a duplicate submission while market-data sensing continues. A standing
  protective intent remains journaled and is re-decided after reconciliation; QMX does
  not flatten or invent a terminal state.
- **Notification tier:** alarm. Lost submission certainty on a live-money stream needs
  operator-visible reconciliation evidence.
- **Product-user affordance:** the broker connection failed while an order might have
  been accepted. Do not click retry: QMX is deliberately preventing a duplicate. Let
  reconciliation determine what happened, then record the explicit resolution; only
  then can a new decision be admitted.

### FR-6: Venue evidence cannot be recorded durably

- **Failure class:** `storage failure` (CT-04).
- **Detection:** every command, observation, reconciliation edge, and secret-rotation
  state change follows record-before-interpret. If an injected observation, journal,
  record, or secret-store sink refuses or raises at its guarded seam, qmf-venue returns
  a normalized storage refusal and does not interpret the unrecorded event.
- **Auto-recovery / retry:** no package-level retry. Restore the durable sink, then
  retry the write or allow the pending recovery record to land; stream processing may
  resume only after persistence succeeds.
- **Visible degraded state:** the writer-holding command stream is blocked because its
  next fact is not durable. The sensing pipe remains open, and a partial multi-room
  write is retained as pending recovery rather than reported complete.
- **Notification tier:** alarm for a live writer; the refusal includes the failing sink
  and recovery context for the operator.
- **Product-user affordance:** QMX could not save the command or venue fact, so it paused
  that command stream instead of acting from memory. Restore storage and retry the
  pending record; a successful retry records the fact once and then resumes the stream.
