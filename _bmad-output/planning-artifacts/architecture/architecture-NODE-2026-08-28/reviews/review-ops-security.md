# Reviewer gate — OPERATIONS + SECURITY lens

Spine: architecture-NODE-2026-08-28/ARCHITECTURE-SPINE.md (24 TN blocks, A1-A30)
Lens: senior SRE / sole operator. NFR-10 (one canonical checkout, one person operates), NFR-11
(failure register), CT-21/L34 secrets, DevOps gating lens, the day-one runbook.
Reviewer: ops-security. Verdict: **CHANGES REQUIRED — one disaster-recovery gap is a live-money
data-loss risk; a cluster of silent-degradation gaps defeat the one-person unattended premise.**

The spine is unusually complete on secret *hygiene* (references-not-values, in-memory holder, no
secrets in logs/labels, SSH-stdin wizard) and on hardening *primitives* (DynamicUser, ProtectSystem,
LoadCredentialEncrypted, ufw, key-only SSH). The DynamicUser + LoadCredentialEncrypted + StateDirectory
rotation-without-root mechanism is **mechanically sound** — verified below. The failures are at the
seams an SRE lives in: what the operator *sees*, what *reaches* him when he is not looking, what
survives the machine dying, and what "safe point" / "check mode" concretely mean.

Vocabulary policed: no "engine/kernel/plugins/exam/minimal core" misuse found; "the trading node…
paper|live" held throughout; "paper node" not present. Clean on naming.

---

## CRITICAL

### C1 — The backup encryption key is sealed to the dying machine: off-site backups are undecryptable after VPS loss, and the restore drill can never detect it
**Where:** TN-12 (secrets, KEK store), TN-13 (backup + restore drill), `backup_key_custody` row.

**What.** Trace the key custody:
- `systemd-creds LoadCredentialEncrypted` is **host-key sealed** (TN-12 explicitly, "NOT TPM2"). It
  delivers the KEK at service start.
- "The object-storage/backup encryption key … ride[s] the same store" (TN-12); backups are encrypted
  "key from the KEK store" (TN-13).
- The systemd host key (`/var/lib/systemd/credential.secret`) is per-machine on the VPS disk.

So the key that decrypts every off-site backup exists **only** on the VPS. When the VPS dies (disk
loss, provider incident, unrecoverable rebuild — the exact event nightly off-site backups exist to
survive), the host key is gone, the KEK/backup key are unrecoverable, and **every ciphertext object in
the bucket is permanently undecryptable.** Evidence that NFR-06 says is "retained forever" is retained
as undecryptable bytes. This is total DR failure at the one event DR is for.

**Compounding:** the spine's own rationale is muddled and hides the gap. TN-12 chose host-key over TPM2
*because* "cloud VPS TPMs do not survive migration or rebuild" — but the host-key file does not survive
a disk-loss rebuild either. Host-key vs TPM only affects reboot/restart survival (needed for
rotation-without-root); **neither** survives VPS death. The choice does not buy the DR property it
appears aimed at, and no escrow rule fills the gap.

**Why it matters.** A one-person always-on money node whose entire evidence + journal history is one
provider-incident away from unrecoverable is not operable. `backup_key_custody` being a registry row
does not close it — a variable with no escrow rule and no stated DR consequence is not a design.

**And the drill cannot catch it:** the monthly full restore (TN-13) runs "into a scratch directory"
**on the same VPS**, using the live host key. It proves ciphertext integrity but exercises none of the
key-availability path. It will pass green forever while DR is broken, giving false confidence.

**Fix (all three):**
1. **Escrow the backup key off the VPS.** Either encrypt backups under a key the operator holds
   independently of the VPS (passphrase-derived, or a key kept in the workstation `qmx/*` Credential
   Manager and never VPS-minted), or escrow `/var/lib/systemd/credential.secret` (or a wrapped copy of
   the KEK) into the operator's possession at provisioning. State it as a TN-12/TN-13 invariant, not a
   blank variable.
2. **Make the monthly full-restore drill a true DR rehearsal:** restore on a machine that does **not**
   already hold the original host key (a fresh scratch VPS/container), so the drill actually exercises
   key recovery. A drill that reuses the live key is not a DR test.
3. Correct the TN-12 rationale: state plainly that host-key sealing survives reboot/rotation but **not**
   VPS death, and that DR therefore depends on the escrow in (1).

---

## HIGH

### H1 — The entire notification plane lives inside the node: node death or VPS death is silent (no dead-man's switch)
**Where:** TN-15 (alerts), TN-4 (supervision), TN-9 (soak).

**What.** Every push path is in-process: the node evaluates the allow-list and calls the
`NotificationChannel` webhook. TN-15 correctly makes Prometheus/Grafana "optional zero-authority
consumers" — so nothing external is required. The consequence: if the process is gone (OOM-kill, kernel
panic, segfault below the notifier), or the VPS is gone (host down, network partition), **no alert
fires.** Silence reads to the operator as "all fine." During a ~2-day *unattended* soak (TN-9) and in
unattended live, node death is the single most important thing to be told about, and it is precisely
the event the design cannot signal.

**Why it matters.** "One person can operate this" requires that the absence of the node reaches the
person. Stand-down-alive covers the case where the node is up enough to refuse; it cannot cover the node
being gone.

**Fix.** Require an **external liveness signal** independent of the node: either an outbound heartbeat
the node emits on a cadence to a dead-man's-switch service (healthchecks.io-class; alerts on *missing*
ping), or a required external uptime monitor on an SSH/door liveness probe. Add "the dead-man's switch
alerts the operator's device when the heartbeat stops" to the TN-23 soak acceptance checklist. This is
the one place the spine's "no required external stack" posture is wrong.

### H2 — The "closed allow-list" is the ONLY push tier, yet several must-alarm conditions other TNs promise are not on it → they degrade the node silently in live
**Where:** TN-15 (allow-list) vs TN-13, TN-14, TN-10.

**What.** TN-15 declares the allow-list "the ONLY push tier … everything else is console evidence."
But other TNs promise alarms that the list does not carry:
- **Restore-drill failure / backup failure** — TN-13 says "failures alarm[]"; not on the TN-15 list.
- **Calendar refresh fail-closed** — TN-13 blocks entries on a failed refresh; not on the list.
- **Live clock `no-new-entry` band (suspend_new)** — TN-14; only `halt`→stand-down is covered by
  "supervision fail-closed/stand-down." The clock-band-breach alert is **soak-only and switches off at
  go-live** (TN-15), so in live a `no-new-entry` clock band stops new entries with no push at all.
- **Binding-level entry stand-down on unexplained live drift** — TN-10 stands a binding down for
  entries; a per-binding stand-down is not the node-wide "stand-down" on the list.
- **First-connection / data-quality verification failure in live** — the first-connection-check alert
  is also soak-only.

Because the list is declared *closed* and *the only* push tier, each of these is console-only: an
unattended operator is never told the node stopped trading or lost a protective input.

**Why it matters.** The allow-list is tuned against alert fatigue (correct instinct) but it
under-covers the "the node quietly stopped protecting/trading" class — worse for a sole operator than
over-alerting.

**Fix.** Reconcile the allow-list with every TN that says "alarm/fail-closed." Add a distinct
notification *tier* for silent-degradation (restore/backup failure, calendar stale, live clock
no-new-entry, per-binding entry stand-down, live verification failure). Keep it out of the
critical-action tier to preserve the two-plane discipline, but it must push, not sit on the console.
Make the FAILURES.md `notification tier` field (H6) the single source that the allow-list is generated
from, so the two can never drift again.

### H3 — Disk headroom is measured but never alarmed; disk exhaustion blocks the command pipe silently
**Where:** TN-15 (metrics: "disk headroom"), TN-4 / TN-24(h) (block-on-unpersistable).

**What.** Disk headroom is exported as a metric but has **no threshold, no threshold owner, and is
absent from the alert allow-list.** The failure sequence for an always-on node is textbook: journals +
rooms + raw archive + backup staging grow, disk fills, block-on-unpersistable engages (an unflushed
write keeps the sequence unadvanced and blocks the command stream), and the node effectively stops. The
operator learns of it only when a *downstream* symptom happens to alarm — not proactively while
headroom is still recoverable.

**Why it matters.** Silent disk exhaustion is one of the most common single-VPS outage causes; here it
also blocks the money path.

**Fix.** Mint an alarmed `disk_headroom_min` threshold (registry row, node/ops owner) on the evidence
tier and the hot-rooms volume, put low-disk on the push tier (H2), and name the owner. Also state the
retention/rotation math (journald `SystemMaxUse`, room retention, backup staging) so headroom is
*bounded by design*, not just watched.

### H4 — Stand-down-alive's "doors keep serving, resurrection stays reachable" only holds if boot reaches door bring-up; an early-stage crash-loop ends in systemd `failed` with no doors and possibly no alert
**Where:** TN-4 (stand-down, StartLimit above (K,T)), TN-2 (boot ceremony ordering).

**What.** TN-4's guarantee — past the crash-loop fold the node "BOOTS INTO STAND-DOWN: … the doors
keep serving so resurrection stays reachable" — presumes each crash-loop iteration reaches the stage
where doors are up and the fold is evaluated. But if the crash is in **preflight or compose** (store
unreachable, disk full at boot, config compile refusal, `chronyc waitsync` never returns, a bad
credential), the node exits before the door/notifier exist. systemd restarts, repeats, and because
StartLimit is set *above* (K,T) it eventually trips into **`failed`** with **no doors serving and no
alert** (the notifier may not be composed yet). The worst failure — cannot even boot — is the most
silent, and the operator's only recourse is raw SSH + journalctl. This directly contradicts NFR-10's
one-person-repair claim.

**Why it matters.** The interplay is inverted: node-stand-down preempts systemd only when the node
stays *alive*; an early exit-loop never reaches stand-down, so the systemd StartLimit is the *only*
backstop and it terminates into a doorless, silent state.

**Fix.** Bring the door + notifier + a minimal "degraded shell" up **as early as possible** — before
the risky compose/venue steps — so a compose/preflight failure still (a) serves a diagnostic `/health`
+ refusal on the door and (b) pushes a supervision-fail alert. Define what the node does when it cannot
even complete preflight: a persistent degraded-shell state systemd keeps alive, not an exit-loop into
`failed`. Add "preflight/compose failure still serves the door and pushes an alert" to the soak gate.

### H5 — Day-one authoring of the first roster / Book / BMS config has no defined affordance for a non-technical operator — contradicts NFR-10
**Where:** TN-18 (config compiled from roster + BMS + Book fragments), TN-17 ("system … bindings —
console-managed"), TN-1, NFR-10.

**What.** The node composes from ONE resolved config (TN-18): invocation > deployment roster (account
bindings `(VenueId, AccountId, role, world)` + credential references + adapter selection + machine
tuple) > BMS fragment > Book fragment > node defaults, a JSON-Schema-class artifact with exact
rationals, unit-kinds, `fp1` cites of Book/BMS, `admission_impact`, format version. TN-17's powers
channel `settings edit` **mints a new version of an existing artifact** — it does not author the first
one. TN-17 calls system bindings "console-managed," which is unspecified hand-waving. There is **no
`qmn config init` / scaffold** and no defined path by which a *non-technical* operator produces the
first roster + Book + BMS artifact. Hand-authoring fp1-cited JSON-Schema is a senior-engineer task.

**Why it matters.** NFR-10 and TN-16 claim "one person can deploy and repair from one canonical
checkout." The very first gate of day-one — author the config the node boots from — is undefined and,
as described, beyond a non-technical operator. The whole runbook stalls before first boot.

**Fix.** Define a concrete bootstrap affordance: a `qmn config init` that scaffolds a schema-valid
roster + minimal Book/BMS skeleton with blanks flagged, plus a `qmn config validate` that renders each
blank-blocks-live and each missing fp1 as a typed, operator-readable refusal. Or explicitly downgrade
the NFR-10 claim: state that first-config authoring is an assisted/technical step and name who performs
it. Do not leave "console-managed" as the answer.

### H6 — NFR-11 is bound in name but its completeness is never gated; TN-23 forbids "debt discharged silently" yet provides no register-completeness check
**Where:** TN-23 ("every node failure mode ships a FAILURES.md entry with NFR-11's six fields"),
Inherited-invariants NFR-11 row.

**What.** The binding exists. What is missing is any *gate* that the register is actually complete and
that each entry's six fields — notably **operator affordance** and **visible degraded state** — are
real. The spine designs dozens of failure modes (preflight fail, rotation-store failure, unmapped venue
code, undeliverable protection intent, fold-cannot-resolve, missing scope record, paper-stream outage,
disk-full block, clock-unsynchronized, restore-drill failure, calendar-refresh failure, verification
failure, KEK-store failure, …). Nothing in the soak acceptance gate (TN-23) or CI verifies that every
one has a populated entry, and nothing checks that the `operator affordance` field names a **concrete
door/CLI action** that exists. TN-23's own charter is "PREVENTS … debt discharged silently" — the
register itself is the debt most likely to be discharged silently.

**Why it matters.** A failure register whose "operator affordance" cells are prose, or absent, is
exactly the thing that fails the sole operator at 3am. And H2's allow-list drift is a direct symptom of
the register not being the single source of the `notification tier` field.

**Fix.** Add a TN-23 soak-gate line and a CI check: FAILURES.md has an entry for every
typed-failure-id the node can emit (cross-checked against the failure-id enum), every entry has all six
fields populated, and every `operator affordance` resolves to a named door/CLI capability. Generate the
alert allow-list (H2) from the register's `notification tier` column so they cannot diverge.

---

## MEDIUM (rolled into counts; recorded for the doc-factory increment)

- **M1 — "restart-at-safe-point / drain-aware" is undefined and unbounded.** Used in TN-2, TN-4,
  TN-16, TN-18 as the mechanism for config change, upgrade, rollback and shutdown, but "safe point" and
  "drain-aware" are never given a concrete definition or a bound. Does `qmn deploy switch` return in
  seconds (waits for the current slice to commit) or hang indefinitely (waits for an outstanding UNKNOWN
  to resolve, or positions to close)? The operator has no way to know. Define safe-point precisely (e.g.
  slice boundary + suspend_new drained; standing intents survive as folds, positions are **not** waited
  on) and give it a timeout with a typed refusal on breach.

- **M2 — "boot in check mode" is load-bearing but undefined, and the systemd credential path is never
  runtime-tested.** TN-16 uses "dry-run boot in check mode" for both `deploy switch` and the CI Linux
  lane, but never defines which preflight gates run vs skip. In CI there are no secrets, no venue, no
  chrony sync — so check mode must skip credential-presence, store-reachability, `chronyc waitsync` and
  venue connect, which makes it a *different* path than a real boot, proving less than "the node boots."
  Separately, the CI lane boots outside systemd (GitHub runner), so DynamicUser + LoadCredentialEncrypted
  + StateDirectory — the highest-risk, hardest-to-debug production surface — is only *statically* scanned
  (Skylos IaC), never runtime-exercised until the operator's day-one VPS. Define check mode's gate set and
  exit contract explicitly, and add a "boot under the real systemd unit with LoadCredentialEncrypted from
  a scratch credstore" item to the soak gate (and, ideally, a container/VM smoke that runs the actual unit).

- **M3 — provisioning wizard vs SSH hardening: the privilege path is unreconciled.** The wizard streams
  into `systemd-creds encrypt --name=<ref> - /etc/credstore.encrypted/<ref>` and mints the KEK — writing
  root-owned `/etc/credstore.encrypted` requires **root/sudo** on the VPS. TN-16 hardening is "SSH
  key-only, no password" and good practice is no root SSH login. The spine never states how the wizard
  escalates (root key? passwordless sudo? and how that squares with "no password"). Define the
  provisioning privilege path and its interaction with the runtime DynamicUser posture.

- **M4 — "no automatic reboot" ≠ "no automatic service restart."** TN-16 enables unattended security
  upgrades with no auto-reboot, but a security update (e.g. openssl) can trigger a needrestart/DPkg
  service restart of `qmn.service` **outside** an operator maintenance window, bypassing
  restart-at-safe-point and possibly mid-trade. State that unattended-upgrades must be configured to
  never restart `qmn.service` (or that any systemd-initiated restart is routed through the drain path).

- **M5 — resolve_unknown has no read-side and no inconclusive path.** TN-6/TN-10 make resolution
  operator-attested "from the read-back," but the evidence channel (TN-17) exposes only an UNKNOWN
  *count* (TN-15 metric), not a **list of outstanding UNKNOWNs with their per-command read-back evidence**
  to attest against. And there is no defined path when the read-back itself is UNKNOWN/out-of-lookback —
  the operator is asked to attest accepted|absent for something the system could not determine. Add an
  evidence-channel "outstanding UNKNOWNs with read-back detail" read model and a defined refusal when the
  read-back cannot support attestation.

- **M6 — block-on-unpersistable vs L39 exit-preservation under disk-full is undefined, and can form a
  hard loop with the watchdog.** Evidence-first + block-on-unpersistable (TN-24h) means a full disk blocks
  *all* persistence — including the exit/protection actions L39 says must never be blocked. Meanwhile a
  blocked synchronous slice can miss the `WatchdogSec` ping → systemd kills and restarts → back into the
  full disk; and stand-down itself must "refuse-and-journal," which also needs disk. Under disk-full the
  node can neither protect, nor journal, nor cleanly stand down. Define whether protection/exit bypasses
  the block (act-then-journal-on-recovery) or relies solely on the venue-resident stop (AD-33), and how
  the watchdog behaves when the loop is legitimately blocked on storage.

- **M7 — the notification channel is never proven end-to-end before the unattended soak.** TN-23's soak
  gate says "metrics, health and alerts are observed" — passive observation, not delivery proof. There is
  no `qmn notify test` affordance and no gate item that a synthetic alert is actually **delivered to the
  operator's device** before he leaves it unattended for ~2 days. Add both.

- **M8 — measured RTO understates true disaster RTO.** TN-13 measures RTO at the first monthly rehearsal,
  but the rehearsal runs on the live VPS into a scratch dir — it excludes VPS re-procurement,
  re-provisioning, and key recovery (C1). The number the operator will trust is the wrong number. Measure
  RTO on the bare-machine DR rehearsal from C1, and record the two numbers apart (integrity-restore RTO vs
  full-DR RTO).

- **M9 — boot-failure diagnosis for a non-technical operator is undefined.** A preflight failure exits
  before the door is up, so the only signal is `systemctl status` / `journalctl` — journald reading, which
  the "non-technical operator" premise disallows. There is no defined "why did it refuse to start"
  affordance that survives a door-down boot (ties to H4's degraded shell).

## LOW (rolled into counts)

- **L1 — no egress firewall posture.** ufw is default-deny *inbound*; outbound is unrestricted (cTrader,
  webhook, S3, Dukascopy, Forex Factory, NTP). For a money node, an egress allow-list narrows the
  exfil/pivot surface if the process is ever compromised. Low given the single-tenant threat model, but
  worth a stated posture.

- **L2 — demo drift alarms during the soak risk desensitizing the operator to the drift class.** TN-9
  deliberately alarms (not halts) on demo-account drift residuals for ~2 days — training the operator to
  dismiss drift alarms immediately before go-live, where drift is critical. Consider a soak-specific
  "demo drift" digest rather than the live alarm class.

- **L3 — uv/CPython bootstrap before `qmn` exists is undefined.** TN-16's `qmn deploy install` lives in
  the checkout, but `qmn` does not exist until `uv sync --frozen` has run, which needs uv + CPython
  installed first. The pre-`qmn` bootstrap (install uv, provision CPython) is the true first day-one step
  and is unspecified.

---

## Verified sound (checked, not findings)

- **DynamicUser + LoadCredentialEncrypted + StateDirectory rotation-without-root** works: systemd
  decrypts credentials at start into `$CREDENTIALS_DIRECTORY` (tmpfs, 0400, owned by the dynamic service
  user) — readable without root; StateDirectory (`/var/lib/qmn`, remapped to the dynamic UID each start)
  is writable by the service user, so re-encrypting rotated material as AEAD ciphertext under the KEK is
  ordinary unprivileged file I/O. The rotation mechanism does not need root. (Confirmed against the
  memlog's 2026-08-28 systemd-creds 255.4 verification.)
- **Secret hygiene** (references-not-values above the connection manager, sole in-memory holder, no
  secret values or account numbers in logs/labels/health, SSH-stdin wizard never touching argv/file/log)
  is correct and complete.
- **Two-plane notification rule** ("an alert is evidence, not permission") is clean; the fatigue concern
  is the reverse — under-notification (H2), not over.
- **StartLimit-above-(K,T)** ordering is correct *for the post-boot case*; the gap is only the
  early-crash case (H4).
