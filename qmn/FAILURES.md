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
  typing a different name in the request does not change the principal. Inspect
  `read_failure_detail` on the evidence channel for the recorded peer and claim.

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
  restart via the operations toolkit; automation must never share the operator
  principal.

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
  budget. Reduce scrape rate or raise `evidence_channel_budget`, inspect
  `read_status`, then restart at a safe point if a higher budget is required.

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
- **Product-user affordance:** Clock drift is elevated. Monitor chrony offset
  via the evidence channel (`read_status`); no trading block yet.

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
  restore chrony sync, watch `read_status` on the evidence channel, and wait
  for the next ok/warn cycle.

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
  before any clock step, record the gap, resync, then restart via the
  operations toolkit.

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
  amount against the destination account via `read_status` on the evidence
  channel; no trading control is implied.

### FR-14: Money-boundary re-seed

- **Failure class:** money boundary
- **Detection:** a treasury `re_seed` act is journaled on the money-boundary
  stream (`money.boundary.re_seed`).
- **Auto-recovery / retry:** none — operator-signed; never auto-retry.
- **Visible degraded state:** n/a — notification only; ledger already records
  the re-seed.
- **Notification tier:** money-boundary
- **Product-user affordance:** A capital re-seed completed. Confirm the
  journaled amount via `read_status` on the evidence channel; the notification
  authorizes nothing further.

### FR-15: Money-boundary refund (dormant V1)

- **Failure class:** money boundary
- **Detection:** a treasury `refund` act would journal on the money-boundary
  stream (`money.boundary.refund`); the act is dormant in V1 and cannot fire.
- **Auto-recovery / retry:** n/a — dormant; no automatic path exists.
- **Visible degraded state:** n/a — dormant.
- **Notification tier:** money-boundary
- **Product-user affordance:** Refund is reserved and dormant in V1. Inspect
  `read_failure_detail` on the evidence channel; no refund alert can fire until
  a later story activates the act.

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
  on the synchronous path (`compose.light_heavy` /
  `compose.light_heavy.no_baseline` / `compose.light_heavy.unmet_bounds` /
  `compose.light_heavy.missing_dependency` / `compose.light_heavy.heavy_dependency`).
- **Auto-recovery / retry:** none within the boot epoch — record the live-path
  baseline on this deployment tuple, drop the light claim (heavy by default),
  or remove the heavy dependency; then restart at a safe point.
- **Visible degraded state:** boot does not Seal; stand-down-alive after doors
  bind; heavy configs stay off the trading path.
- **Notification tier:** alarm / operator-visible (compose refusal).
- **Product-user affordance:** The node refused to seal because a producer,
  labeler, or seat claimed light without proven four bounds. Leave it heavy
  (fan-out) or wait for the VPS baseline before claiming light. Inspect
  `read_failure_detail`; restart via the operations toolkit after the claim is
  dropped.

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
  seat-state clear. V1 has no hardened OS-level memory or security
  confinement (GAP-0054 stays deferred; this entry does not close it).
- **Visible degraded state:** the seat emits no further intents; the command
  stream does not fail and the node does not restart on a cooperative breach;
  quarantine is a read-time fold over the seat-transition stream.
- **Notification tier:** protection-escalation
- **Product-user affordance:** The bot seat was quarantined after a deadline,
  memory-ceiling, or callback-exception breach. Inspect the journaled
  transition, then reinstate from the operator principal over the powers
  channel; a restart will not re-arm the seat.

### FR-20: Promotion silent-battery refusal

- **Failure class:** policy rejection
- **Detection:** the operator `promotion_sign` click runs the silent
  precondition battery against fresh state (`qmn.promotion.run_silent_battery`
  / `promote_to_admitted`); any of the three admission layers, Book/BMS/bot/
  config fingerprints, CT-18 capabilities, live-conditioned baselines,
  un-discharged resign `admission_impact`, blanks, or non-ratified live-gating
  value-status fails.
- **Auto-recovery / retry:** none — the operator re-runs promotion after the
  named check is repaired; displayed-eligible is never a trade grant.
- **Visible degraded state:** promotion does not occur; no seat lands; no
  intent, ledger, or exposure is opened. The operator sees a passed-or-refused
  list in plain words with the refusing check named.
- **Notification tier:** operator-visible (journaled powers refusal).
- **Product-user affordance:** Promotion was refused. Read the named check
  (admission layers, fingerprints, venue capabilities, live baselines,
  admission impact, blanks, or value-status) and retry the promotion click
  from the operator principal after it passes.

### FR-21: Sandbox provenance at hub publish or promotion pull

- **Failure class:** policy rejection
- **Detection:** a hub fragment or as-of artifact carries `provenance =
  sandbox` at `hub_publish` or at the node-initiated promotion pull
  (`qmn.promotion.refuse_sandbox_provenance` / `pull_published_as_of`). An
  as-of set containing one sandbox artifact refuses the whole pull.
- **Auto-recovery / retry:** none — sandbox artifacts never enter the
  published area or a live-zone landing. Publish only live-provenance
  fragments and pull only the published area.
- **Visible degraded state:** publish or pull refused; the seat does not
  land ADMITTED; refusal journaled and alarmed.
- **Notification tier:** operator-visible (journaled).
- **Product-user affordance:** A sandbox-provenance artifact was refused at
  publish or at the promotion pull. Remove it from the as-of set and retry
  from the published area; factory-sandbox evidence cannot authorize live
  money.

### FR-22: Same-day activation trade path

- **Failure class:** policy rejection
- **Detection:** an activation click requests a manual override, warm-up,
  ramp, or same-day trade, or a first intent is attempted before the next
  boundary of the account-scoped day-boundary calendar
  (`qmn.promotion.request_activation` /
  `revalidate_before_first_intent`).
- **Auto-recovery / retry:** none — there is no override. Wait for the next
  account-scoped day-boundary, then revalidate before the first intent.
- **Visible degraded state:** the activation record is accepted (when the
  click itself is legal) but remains ineffective; the seat stays `admitted`
  with no exposure; the first intent is refused.
- **Notification tier:** operator-visible (journaled).
- **Product-user affordance:** Activation does not trade until the next
  account-scoped day-boundary. There is no same-day path, warm-up, or ramp.
  Retry the first intent after that boundary, after revalidation passes.

### FR-23: Intervening refusal after activation day-boundary

- **Failure class:** policy rejection
- **Detection:** at or after the activation day-boundary, fresh
  config/capability/baseline/protection state fails
  (`qmn.promotion.revalidate_before_first_intent` /
  `admit_first_intent`).
- **Auto-recovery / retry:** none automatic — the bot remains admitted but
  inactive. Repair the refusing check and revalidate again; do not infer
  exposure from the earlier activation click.
- **Visible degraded state:** seat stays `admitted`; `may_mint_intent` is
  false; no first intent is admitted.
- **Notification tier:** operator-visible (journaled).
- **Product-user affordance:** Activation reached the day-boundary but
  fresh state no longer passes. The bot is still admitted and not trading.
  Fix the named config, capability, baseline, or protection check, then
  revalidate before the first intent.

### FR-24: Runtime risk population mismatch at Compose

- **Failure class:** invalid input / unavailable dependency / policy rejection
- **Detection:** Compose Layer-1 admission over the assembled risk graph
  finds a cardinality or referential-integrity mismatch: total unique rank,
  declared scopes, netting partitions, one-BMS-per-account/many-Books,
  one-Book-per-bot, or one active paper target
  (`compose.risk_population` / `compose.risk_population.referential_integrity` /
  `compose.risk_population.total_unique_rank` /
  `compose.risk_population.declared_scopes` /
  `compose.risk_population.netting_partitions` /
  `compose.risk_population.one_bms_per_account` /
  `compose.risk_population.one_book_per_bot` /
  `compose.risk_population.one_active_paper_target` /
  `compose.risk_population.cardinalities`).
- **Auto-recovery / retry:** none — repair the assembled roster/BMS/Book/
  binding/seat/window/priority/capability records and reboot; the node
  does not Seal an invalid population.
- **Visible degraded state:** boot stands down alive at the compose stage;
  sequencer stays closed; doors serve the refusal. A mismatch never
  reaches Seal.
- **Notification tier:** alarm / operator-visible (compose refusal).
- **Product-user affordance:** The node refused to seal because the
  assembled risk graph is internally inconsistent. Valid individual
  records still fail together if cardinalities or references disagree.
  Fix the named check (rank table, scopes, netting partition, BMS/Book/
  bot cardinality, or paper target) and restart via the operations toolkit.

### FR-25: Layer-2 shakedown on a live binding or incomplete machinery

- **Failure class:** policy rejection
- **Detection:** `qmn.host.run_demo_shakedown` is asked to run on
  `role = live`, to treat shakedown evidence as performance proof, to
  invent soak/KSA numbers, or to skip a required exercise (windows,
  protection effects, paper ledger, kill line, reconciliation, SQS
  baseline conditioning, callback containment, command-path dry run).
- **Auto-recovery / retry:** none — shakedown runs only on a demo or
  paper-validation binding without a live binding. Re-run after the
  missing prerequisite or invented value is removed.
- **Visible degraded state:** Layer-2 proof is not assembled; Layer-3
  human signature cannot attest the page; promotion battery admission
  layers remain unproven.
- **Notification tier:** operator-visible (journaled admission refusal).
- **Product-user affordance:** Technical shakedown proves the machinery
  works and proves nothing about edge. It cannot run live, cannot mint
  soak or KSA numbers, and its evidence is for your signature — not a
  performance certificate. Inspect `read_status` on the evidence channel.

### FR-26: Bot-supplied final size at the Book door

- **Failure class:** invalid input
- **Detection:** an inbound CT-23 mapping carries `requested_r`, `quantity`,
  `volume`, `size`, `lots`, or `original_risk_amount`
  (`qmn.order.reject_bot_supplied_final_size` /
  `admit_entry_at_book_door` / `mint_place_order_from_authorized`).
- **Auto-recovery / retry:** none — the bot may not size. The Book resolves
  `requested_r` and derives quantity from frozen original risk.
- **Visible degraded state:** the intent is refused before command mint; no
  venue command is constructed; the decision is journaled as refused-by-door.
- **Notification tier:** operator-visible (journaled).
- **Product-user affordance:** The bot proposed a size. QMX refuses that: the
  Book sizes every entry. Remove quantity/`requested_r` from the bot intent
  and let the Book door freeze R. Inspect `read_failure_detail` on the
  evidence channel.

### FR-27: Command mint without frozen R faces

- **Failure class:** invalid input
- **Detection:** `mint_place_order_from_authorized` or
  `mint_virtual_from_authorized` is called without an `AuthorizedIntent`
  whose three R faces were frozen at the Book door
  (`qmn.order.refuse_command_mint_without_frozen_r`).
- **Auto-recovery / retry:** none — admit the entry at the Book door first.
- **Visible degraded state:** no `place_order` is minted; the order path
  never sees an unauthorized command.
- **Notification tier:** operator-visible (journaled door refusal).
- **Product-user affordance:** An order cannot be minted until the Book has
  frozen original risk. The entry must pass the Book door (full-loss price,
  Book-resolved `requested_r`, dimensional checks) first. Inspect
  `read_failure_detail` on the evidence channel.

### FR-28: Frozen R mutated except the journaled partial-entry rebase

- **Failure class:** policy rejection
- **Detection:** a protection amendment, rollover, configuration change, or
  treasury act would change frozen R faces, or a second distinct
  terminal-partial-entry rebase is requested
  (`qmn.order.preserve_frozen_r` /
  `journal_terminal_partial_entry_rebase`).
- **Auto-recovery / retry:** none for a distinct second rebase. A repeat of
  the same journaled rebase is idempotent and does not append again.
- **Visible degraded state:** the act is refused; virtual-position faces and
  CT-29 original risk stay as admitted (or as the one journaled rebase).
- **Notification tier:** operator-visible (journaled).
- **Product-user affordance:** Frozen R does not move with stops, rollover,
  settings, or treasury. Only a short ENTRY fill at first terminal state
  re-bases `original_risk_amount`, once, and that rebase is journaled.
  Inspect `read_failure_detail` on the evidence channel.

### FR-29: Boot-blocking config at preflight

- **Failure class:** policy rejection
- **Detection:** preflight finds a blank or non-ratified row whose blank
  effect is `blocks-boot` (`preflight.config.boot_blocking`).
- **Auto-recovery / retry:** none within the boot epoch — fill or countersign
  the named row, then restart at a safe point.
- **Visible degraded state:** boot does not Seal; stand-down-alive after
  doors bind; sequencer stays closed.
- **Notification tier:** alarm / operator-visible (preflight refusal).
- **Product-user affordance:** A boot-blocking config row is blank or not
  ratified. Fill it or countersign from the operator principal over the
  powers channel, then restart via the operations toolkit.

### FR-30: Boot-attempt journal write or amend failed

- **Failure class:** storage failure
- **Detection:** the supervisor WriterId cannot persist or amend the
  boot-attempt record (`boot.attempt.write` / `boot.attempt.amend`).
- **Auto-recovery / retry:** none while the journal room is unpersistable —
  restore capacity, then restart.
- **Visible degraded state:** check mode exits; live boot stands down alive
  if doors already bound; sequencer stays closed.
- **Notification tier:** silent-degradation
- **Product-user affordance:** The node could not journal the boot-attempt
  record. Free disk / restore the journal room, then restart via the
  operations toolkit. Entries stay blocked while storage is down.

### FR-31: Writer-id allocation refused at Compose

- **Failure class:** invalid input / policy rejection
- **Detection:** Compose cannot allocate reserved supervisor and stream
  WriterIds (`compose.writer_ids`).
- **Auto-recovery / retry:** none — repair the writer roster and reboot.
- **Visible degraded state:** boot stands down at compose; sequencer closed.
- **Notification tier:** alarm / operator-visible (compose refusal).
- **Product-user affordance:** Writer-id allocation failed at Compose.
  Inspect `read_failure_detail`, fix the roster, then restart via the
  operations toolkit.

### FR-32: composition_fp fingerprint refused

- **Failure class:** invalid input
- **Detection:** Compose cannot fingerprint the sealed node-config
  (`fingerprint.composition_fp`).
- **Auto-recovery / retry:** none — the cite set must be fingerprintable.
- **Visible degraded state:** boot does not Seal; stand-down-alive.
- **Notification tier:** alarm / operator-visible (compose refusal).
- **Product-user affordance:** The composition fingerprint could not be
  minted. Inspect `read_failure_detail` and the cite set, then restart via
  the operations toolkit.

### FR-33: Journal-before-dispatch storage failure

- **Failure class:** storage failure
- **Detection:** a command, control, protection, promotion, activation,
  treasury, or settings effect cannot persist its journal first
  (`storage.journal_before_dispatch` / `storage.partial_write` /
  `storage.log_only_path` / `storage.best_effort_path`). A partial write is
  a storage failure. A log line or best-effort write is refused.
- **Auto-recovery / retry:** none while unpersistable — restore the journal
  room; the act is re-decided, never blindly retried.
- **Visible degraded state:** the effect does not dispatch; entries are
  blocked; exits and standing protection remain enactable (L39).
- **Notification tier:** silent-degradation
- **Product-user affordance:** The node refused to apply an effect because
  the journal write did not land. Restore journal capacity via the
  operations toolkit, then retry the act from the operator principal over
  the powers channel. A log line is not evidence.

### FR-34: Preflight detected a refusal without a more specific id

- **Failure class:** policy rejection / unavailable dependency
- **Detection:** preflight returns a typed refusal whose context does not
  name a more specific id (`preflight.detected`).
- **Auto-recovery / retry:** none — inspect the preflight status, repair
  the named check, then resurrect or restart.
- **Visible degraded state:** stand-down-alive after doors bind; sequencer
  closed.
- **Notification tier:** alarm / operator-visible (preflight refusal).
- **Product-user affordance:** Preflight refused boot. Read `read_failure_detail`
  and the preflight-status view on the evidence channel, repair the cause,
  then resurrect from the operator principal over the powers channel.

### FR-35: Runtime risk contract importable but unwired

- **Failure class:** policy rejection
- **Detection:** the D010 runtime risk gate finds a required CT-22/23/24/25/27/28/29/30/31/32
  path that is importable from qmf-risk but not called through the node
  composition root (`risk_gate.unwired_contract`).
- **Auto-recovery / retry:** none — wire the missing runtime path and re-run
  the gate. Import-only surface is not proof.
- **Visible degraded state:** the runtime risk gate refuses; soak is blocked;
  no live role opens on an unwired risk contract.
- **Notification tier:** operator-visible (journaled).
- **Product-user affordance:** A risk contract is defined but not wired into
  the node. The gate names the missing runtime path and traceability ID.
  Inspect `read_failure_detail` on the evidence channel; do not treat paper
  profit as a substitute.

### FR-36: Paper profit or manual observation offered as risk-gate proof

- **Failure class:** policy rejection
- **Detection:** the D010 runtime risk gate is handed a paper-profit figure or
  a manual observation as proof (`risk_gate.paper_profit` /
  `risk_gate.manual_observation`). Measurement publishes and never acts
  (CT-32); paper P&L never becomes treasury cash.
- **Auto-recovery / retry:** none — re-run the gate against the conformance
  double, injected clock, and seeded fixtures only.
- **Visible degraded state:** the gate refuses; no soak or live claim is
  minted from profit or observation.
- **Notification tier:** operator-visible (journaled).
- **Product-user affordance:** Paper profit and eyeballing the books cannot
  prove the runtime risk gate. Run the executable composition-root path.
  Inspect `read_failure_detail` on the evidence channel.
