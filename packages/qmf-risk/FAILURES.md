# qmf-risk — failure register

Failure-register entries for `qmf-risk`, per the workspace convention
(`conventions/failure-register.md`, NFR-11). The CT-22 through CT-32 risk doors
use the closed CT-04 category vocabulary. Each category below has a complete
operator-facing entry so a returned refusal is actionable rather than merely a
code. Refusals received from an injected boundary are preserved, never raised or
silently reclassified.

### FR-1: A risk artifact or money-path value is malformed

- **Failure class:** `invalid input` (CT-04).
- **Detection:** value factories and Book/BMS doors validate required fields, exact
  unit kinds and currencies, scales, fingerprints, ranks, scopes, intent families,
  and contract shapes before admission. A missing, wrong-typed, mixed-dimension, or
  internally inconsistent value returns the failing field and reason.
- **Auto-recovery / retry:** no automatic retry. Correct the value and submit a new
  admission request; repeating the same malformed artifact performs no effect.
- **Visible degraded state:** no Book definition, binding, intent, control action, or
  performance result is minted from the invalid value. Previously admitted risk state
  remains intact and exits remain independently admissible.
- **Notification tier:** operator-visible at an admission or control door;
  construction-only mistakes may be silent-log in development.
- **Product-user affordance:** the risk request is incomplete or dimensionally unsafe.
  The refusal identifies the field to fix. Correct it and retry; QMX will not coerce a
  currency, unit, float, or intent into a different meaning.

### FR-2: A requested risk contract feature is not supported

- **Failure class:** `unsupported capability` (CT-04).
- **Detection:** contract-version readers, template resolution, admission-bar operands,
  exit-policy resolution, and control scopes compare the requested feature with their
  closed V1 vocabularies. An unknown format, operator, policy form, or action capability
  is refused before evaluation.
- **Auto-recovery / retry:** no automatic retry and no best-effort downgrade. Use a
  supported V1 form, or install and explicitly bind a version that declares the feature,
  then re-admit.
- **Visible degraded state:** only the unsupported definition or action is unavailable;
  existing Books, positions, evidence, and supported risk-reducing exits are unchanged.
- **Notification tier:** operator-visible with the requested feature and supported
  vocabulary in refusal context.
- **Product-user affordance:** this QMX version does not implement the requested risk
  feature. Choose one of the declared forms or upgrade and bind a compatible contract;
  retrying unchanged will not silently reinterpret it.

### FR-3: Required evidence or a bound version is missing

- **Failure class:** `unavailable dependency` (CT-04).
- **Detection:** admission and evaluation resolve cited producer evidence, version-graph
  nodes, required admission slots, Book/BMS bindings, and live-role prerequisites. A
  missing or unverified dependency is returned explicitly rather than fabricated.
- **Auto-recovery / retry:** retry only after the named evidence, binding, or version
  node has been durably supplied. qmf-risk does not poll or invent a replacement.
- **Visible degraded state:** the affected admission or evaluation remains pending or
  blocked; no live authorization is minted. Already-admitted state and risk-reducing
  exits remain available.
- **Notification tier:** operator-visible, escalating to alarm when the missing
  dependency blocks live admission for a sustained period.
- **Product-user affordance:** QMX cannot prove a prerequisite for this risk decision.
  Supply or restore the evidence named in the refusal, then retry; the new call
  rechecks the dependency before doing anything.

### FR-4: A decision relies on stale risk evidence

- **Failure class:** `stale evidence` (CT-04).
- **Detection:** exit-record and same-seat sequencing guards compare the proposed action
  with the durable closing record and evidence knowledge-time. A later intent arriving
  before the prior exit is persisted, or an expired evidence window, is refused rather
  than folded as current truth.
- **Auto-recovery / retry:** no blind retry. Wait for the named closing record or fresh
  evidence to become durable, then submit a newly evaluated intent.
- **Visible degraded state:** the newer action remains unapplied and the position's last
  durable state stays authoritative. Existing protective exits are not cancelled or
  widened while the evidence gap is open.
- **Notification tier:** operator-visible for a held action; alarm if the stale interval
  leaves a live position awaiting durable closure evidence.
- **Product-user affordance:** the decision was based on evidence older than the risk
  state QMX must honor. Let the pending record land or refresh the evidence, then retry;
  QMX re-evaluates from the new durable state instead of replaying the stale action.

### FR-5: A well-formed risk action violates active policy

- **Failure class:** `policy rejection` (CT-04).
- **Detection:** Book/BMS admission, risk-monotonicity, role/world, control, window, and
  performance firewalls evaluate well-formed requests against the active charter. A
  non-USD numeraire, forbidden unit conversion, entry under a block, widening exit,
  cross-role result, or live gate from replay evidence is rejected with its rule.
- **Auto-recovery / retry:** no automatic retry. Change the request or satisfy the named
  policy condition, then create a new admission decision; unchanged retries stay refused.
- **Visible degraded state:** the forbidden entry, amendment, or publication does not
  take effect. Durable state is unchanged, while close/cancel/tighten and the other
  risk-reducing acts remain admissible under the exit-preservation invariant.
- **Notification tier:** operator-visible; charter-integrity and live-gating violations
  may escalate to alarm.
- **Product-user affordance:** the request is valid in shape but would break an active
  risk rule. The refusal names that rule. Resolve the condition or choose a risk-reducing
  action, then retry as a fresh decision.

### FR-6: An upstream venue operation is transiently uncertain

- **Failure class:** `transient venue failure` (CT-04), preserved from the injected
  boundary rather than translated into rejection.
- **Detection:** a risk door receiving a typed result from a venue, journal, or dispatch
  collaborator checks for `TypedRefusal` before proceeding. A transient venue category
  is returned unchanged, including its retryability and context, so uncertainty cannot
  masquerade as an accepted or rejected risk action.
- **Auto-recovery / retry:** qmf-risk never retries or resubmits the venue operation.
  Reconciliation or the owning venue boundary must resolve uncertainty; only then may
  the caller request a new risk decision.
- **Visible degraded state:** the dependent dispatch is not considered complete and no
  terminal venue outcome is invented. The durable risk intent remains available for a
  later re-decision, and unrelated risk-reducing acts remain admissible.
- **Notification tier:** alarm when a live-money action has an uncertain venue outcome.
- **Product-user affordance:** the broker-side operation may or may not have happened.
  Do not retry it through the risk door. Let venue reconciliation establish the outcome,
  then ask QMX for a new decision from that recorded state.

### FR-7: A risk action cannot be journaled before dispatch

- **Failure class:** `storage failure` (CT-04), preserved from the injected sink.
- **Detection:** `journal_before_dispatch` requires the CT-30 control-action record to be
  durably accepted before returning it for dispatch. Any typed sink refusal, including a
  storage failure, is returned unchanged and the record never reaches dispatch.
- **Auto-recovery / retry:** no automatic retry. Restore the sink and retry the same
  durable append through the owning writer; dispatch may be reconsidered only after the
  record is confirmed stored.
- **Visible degraded state:** the proposed risk action is held and unexecuted because it
  is not durable. Existing recorded state and sensing remain readable; the action is not
  lost or falsely reported dispatched.
- **Notification tier:** alarm for a live writer, with the sink's original context kept
  for diagnosis.
- **Product-user affordance:** QMX could not record the risk action, so it refused to send
  it. Restore storage and retry the pending append; once the record is durable, QMX makes
  a new dispatch decision instead of assuming the first attempt happened.
