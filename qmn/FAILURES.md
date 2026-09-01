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
