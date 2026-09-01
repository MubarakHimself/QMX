# qmn failure register (NFR-11)

Designed failure modes for the trading-node package. Append one entry per
designed failure; every typed refusal the node can emit belongs here.

### FR-1: Unknown or service-account powers peer

- **Failure class:** policy rejection
- **Detection:** `SO_PEERCRED` uid is neither the declared operator nor ops
  principal, or equals the fixed `qmx` service account
  (`qmn.doors.http.powers.resolve_peer_principal` / `authorize_powers_call`).
- **Auto-recovery / retry:** none — the peer must reconnect as a declared
  principal.
- **Visible degraded state:** call refused before handler dispatch; no power
  runs; refusal journaled as a control action.
- **Notification tier:** operator-visible (journaled powers-transport refusal).
- **Product-user affordance:** The node refused the action because the calling
  account is not your operator or ops identity. Retry from the desktop UI
  (operator) or an ops-toolkit recipe (ops only); never from the `qmx` service
  account.

### FR-2: Ops principal calls a trading or human-only power

- **Failure class:** policy rejection
- **Detection:** authenticated principal is `ops` and the named power is outside
  `{notify_test, restore_drill_run, config_validate, hub_publish}`
  (`authorize_powers_call`).
- **Auto-recovery / retry:** none — the ops principal cannot acquire the power;
  an operator-principal call is required.
- **Visible degraded state:** refused by the transport before handler dispatch;
  journaled.
- **Notification tier:** operator-visible (journaled).
- **Product-user affordance:** DevOps recipes cannot promote, activate, flatten,
  resurrect, edit settings, countersign, or attest. Perform the act from the
  operator principal (desktop UI over the powers channel).

### FR-3: Agent or non-human claimed signer

- **Failure class:** policy rejection
- **Detection:** `claimed_signer` carries an `agent:` / `machine:` / `service:` /
  `bot:` / `qma:` / `automation:` / `cron:` / `systemd:` prefix
  (`is_human_signer` / `authorize_powers_call`; QMX-F045).
- **Auto-recovery / retry:** none — a human signer identity is required.
- **Visible degraded state:** refused by the transport; peer credential still
  recorded; no handler runs.
- **Notification tier:** operator-visible (journaled).
- **Product-user affordance:** Only a human signer may authorize live acts.
  Retry with your operator identity; agents and automation cannot mint live
  authority by claiming a name in the payload.

### FR-4: Claimed identity cannot override peer credentials

- **Failure class:** (not a separate refusal — invariant of admit path)
- **Detection:** every admitted `PowersCallAuthorization` sets
  `peer_overrides_claim=True`; principal is always derived from `SO_PEERCRED`,
  never from the payload's claimed signer.
- **Auto-recovery / retry:** n/a — invariant.
- **Visible degraded state:** n/a — admit records both peer and claim.
- **Notification tier:** silent-log (journaled admit carries both fields).
- **Product-user affordance:** Who you are on the socket is who the node trusts;
  typing a different name in the request does not change the principal.

### FR-5: Unit under operator UID at preflight

- **Failure class:** policy rejection
- **Detection:** `evaluate_unit_principals` finds any host unit UID equal to the
  declared operator UID; boot preflight's `unit_principals` check fails.
- **Auto-recovery / retry:** none — reconfigure units so no automated unit runs
  as the operator; node stands down on detected preflight refusal.
- **Visible degraded state:** boot does not open the sequencer; stand-down-alive
  with doors serving when the refusal is detected after door bind.
- **Notification tier:** alarm / operator-visible (preflight refusal).
- **Product-user affordance:** The node refused to boot because a systemd unit
  would run as your operator account. Move that unit off the operator UID and
  restart; automation must never share the operator principal.

### FR-6: Evidence channel budget exhausted

- **Failure class:** policy rejection
- **Detection:** `DoorRuntime.evidence_reads` reaches
  `evidence_channel_budget` (unit: request-count-per-boot-epoch) on an evidence
  read (`qmn.doors.library._consume_budget`).
- **Auto-recovery / retry:** none within the boot epoch — budget resets on the
  next boot epoch after a supervised restart.
- **Visible degraded state:** further evidence GETs refuse; powers channel
  unaffected; node keeps serving.
- **Notification tier:** operator-visible (evidence refusal on the wire).
- **Product-user affordance:** The evidence channel hit its per-boot request
  budget. Reduce scrape rate or raise `evidence_channel_budget`, then restart
  at a safe point if a higher budget is required.

### FR-7: Stale evidence cited for a powers call

- **Failure class:** stale evidence
- **Detection:** `enact_power` compares caller `evidence_knowledge_time_ns` to
  the runtime's current `knowledge_time_ns`; a lagging stamp refuses.
- **Auto-recovery / retry:** after-condition — re-read evidence, then retry the
  powers call with the fresh knowledge-time.
- **Visible degraded state:** no act runs; requested is not journaled as
  enforced; refusal shape identical on the Python API and powers door.
- **Notification tier:** operator-visible (powers refusal).
- **Product-user affordance:** The UI or recipe used an outdated evidence
  snapshot. Refresh status/health from the evidence channel and retry.

### FR-8: Chrony waitsync failed at preflight

- **Failure class:** unavailable dependency
- **Detection:** `chrony_waitsync` preflight check / `evaluate_sync_posture`
  with `chrony_waitsync_passed=False` (`preflight.clock.chrony`).
- **Auto-recovery / retry:** none while unsynchronized — wait for chrony sync;
  check mode skips this gate.
- **Visible degraded state:** node cannot trade; stand-down-alive after doors
  bind; unsynchronized intervals recorded as explicit no-entry data-gaps.
- **Notification tier:** silent-degradation
- **Product-user affordance:** The VPS clock is not synchronized. Fix chrony
  sources, confirm `chronyc waitsync`, then resurrect after a clean preflight.

### FR-9: Clock band warn

- **Failure class:** policy rejection (per-cycle precondition)
- **Detection:** machine-versus-truth abs offset ≥ `clock_drift_warn` and below
  `clock_drift_no_new_entry` (`clock.band.warn`).
- **Auto-recovery / retry:** clears automatically on a later cycle whose drift
  returns below warn — never a standing CT-30 action.
- **Visible degraded state:** evidence published; entries still allowed.
- **Notification tier:** operator-visible (journaled band evidence).
- **Product-user affordance:** Clock drift is elevated. Monitor chrony offset;
  no trading block yet.

### FR-10: Clock band no-new-entry

- **Failure class:** policy rejection (per-cycle precondition)
- **Detection:** machine-versus-truth abs offset ≥ `clock_drift_no_new_entry`
  and below `clock_drift_halt` (`clock.band.no_new_entry`).
- **Auto-recovery / retry:** clears on a later cycle below the band — entry-side
  only (L39); exits and protection remain enactable.
- **Visible degraded state:** `place_order` and risk-increasing amends refused
  for the cycle; protection/exits preserved.
- **Notification tier:** silent-degradation
- **Product-user affordance:** The node stopped accepting new entries because
  clock drift crossed the no-new-entry band. Open positions stay protected;
  restore chrony sync and wait for the next ok/warn cycle.

### FR-11: Clock band halt

- **Failure class:** policy rejection (lifecycle)
- **Detection:** machine-versus-truth abs offset ≥ `clock_drift_halt`, or
  unsynchronized posture (`clock.band.halt` / `clock.sync.unsynchronized`).
- **Auto-recovery / retry:** none — only an operator `resurrect` leaves
  stand-down-alive (`StandDownTrigger.CLOCK_HALT`).
- **Visible degraded state:** stand-down-alive; entries refused; exits and
  protection preserved; doors keep serving.
- **Notification tier:** silent-degradation; protection-escalation
- **Product-user affordance:** Clock discipline halted the node. Fix time sync,
  then resurrect from the operator principal over the powers channel.

### FR-12: Wall-versus-monotonic suspect window

- **Failure class:** data quality / sync
- **Detection:** `WallMonotonicDivergenceDetector` finds wall delta diverging
  from monotonic elapsed beyond tolerance (`clock.divergence.suspect_window`).
- **Auto-recovery / retry:** none while the window is open — a step is only
  legal with the node stopped; the window is an explicit no-entry data-gap.
- **Visible degraded state:** suspect window journaled; no-entry until cleared
  by a stopped-node step and fresh sync.
- **Notification tier:** silent-degradation
- **Product-user affordance:** The host clock stepped or paused. Stop the node
  before any clock step, record the gap, resync, then restart.

### FR-13: Money-boundary sweep

- **Failure class:** money boundary
- **Detection:** a treasury `sweep` act is journaled on the money-boundary
  stream (`money.boundary.sweep`).
- **Auto-recovery / retry:** none — money-boundary acts are operator-signed and
  never auto-retry.
- **Visible degraded state:** n/a — the act itself is the event; trading posture
  is unchanged by the notification.
- **Notification tier:** money-boundary
- **Product-user affordance:** A capital sweep completed. Confirm the journaled
  amount against the destination account; no trading control is implied.

### FR-14: Money-boundary re-seed

- **Failure class:** money boundary
- **Detection:** a treasury `re_seed` act is journaled on the money-boundary
  stream (`money.boundary.re_seed`).
- **Auto-recovery / retry:** none — operator-signed; never auto-retry.
- **Visible degraded state:** n/a — notification only; ledger already records
  the re-seed.
- **Notification tier:** money-boundary
- **Product-user affordance:** A capital re-seed completed. Confirm the
  journaled amount; the notification authorizes nothing further.

### FR-15: Money-boundary refund (dormant V1)

- **Failure class:** money boundary
- **Detection:** a treasury `refund` act would journal on the money-boundary
  stream (`money.boundary.refund`); the act is dormant in V1 and cannot fire.
- **Auto-recovery / retry:** n/a — dormant; no automatic path exists.
- **Visible degraded state:** n/a — dormant.
- **Notification tier:** money-boundary
- **Product-user affordance:** Refund is reserved and dormant in V1. No refund
  alert can fire until a later story activates the act.

### FR-16: Kill-switch / KSA escalation

- **Failure class:** protection escalation
- **Detection:** KSA level escalates or the global kill-switch engages
  (`protection.ksa.escalation` / `protection.kill_switch`).
- **Auto-recovery / retry:** none — only an operator `de_escalate` /
  `resurrect` path leaves the escalated state.
- **Visible degraded state:** entry-side (and severity-policy) effects per the
  KSA matrix; exits and standing protection continue per L39.
- **Notification tier:** protection-escalation
- **Product-user affordance:** Protection escalated. Review the KSA level and
  journal; de-escalate or resurrect only from the operator principal.

### FR-17: Supervision fail-closed / node stand-down

- **Failure class:** protection escalation
- **Detection:** supervisor enters stand-down-alive for crash-loop, preflight
  refusal, or other fail-closed trigger (`supervision.fail_closed` /
  `lifecycle.stand_down`).
- **Auto-recovery / retry:** none — restart alone never clears stand-down;
  only operator `resurrect`.
- **Visible degraded state:** stand-down-alive; doors keep serving; entries
  refused; exits and protection preserved.
- **Notification tier:** protection-escalation
- **Product-user affordance:** The node stood down fail-closed. Inspect the
  stand-down trigger, fix the cause, then resurrect from the operator
  principal.

### FR-18: Light claim refused at composition root

- **Failure class:** policy rejection
- **Detection:** Compose evaluates a workload's four-bound light claim without
  a recorded live-path baseline, with unmet declared bounds, without harness
  proof, with a child-supplied self-approved class, or with a heavy dependency
  on the synchronous path (`qmn.host.light_heavy` /
  `compose.light_heavy.*`).
- **Auto-recovery / retry:** none within the boot epoch — record the live-path
  baseline on this deployment tuple, drop the light claim (heavy by default),
  or remove the heavy dependency; then restart at a safe point.
- **Visible degraded state:** boot does not Seal; stand-down-alive after doors
  bind; heavy configs stay off the trading path.
- **Notification tier:** alarm / operator-visible (compose refusal).
- **Product-user affordance:** The node refused to seal because a producer,
  labeler, or seat claimed light without proven four bounds. Leave it heavy
  (fan-out) or wait for the VPS baseline before claiming light.

### FR-19: Seat callback containment breach / automatic quarantine

- **Failure class:** policy rejection
- **Detection:** a QL-7 seat callback breaches `registry:seat_callback_deadline`
  (slice-driver `CancelToken` / `LimitProbe` elapsed),
  `registry:seat_memory_ceiling` (`LimitProbe` memory bytes), or raises
  (`qmn.seats.host.drive_governed_seat`; triggers `deadline-breach`,
  `memory-ceiling-breach`, `callback-exception`).
- **Auto-recovery / retry:** none — the seat quarantines automatically and
  stays `quarantined` across restart, boot epoch, and config version; only
  operator-signed `seat_reinstate` exits. A non-returning callback is the
  door-layer slice-progress watch / supervised restart of last resort, not a
  seat-state clear.
- **Visible degraded state:** the seat emits no further intents; the command
  stream does not fail and the node does not restart on a cooperative breach;
  quarantine is a read-time fold over the seat-transition stream.
- **Notification tier:** protection-escalation
- **Product-user affordance:** The bot seat was quarantined after a deadline,
  memory-ceiling, or callback-exception breach. Inspect the journaled
  transition, then reinstate from the operator principal over the powers
  channel; a restart will not re-arm the seat.
