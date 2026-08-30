# Reviewer Gate — CURRENCY / REALITY-CHECK lens

Spine: `ARCHITECTURE-SPINE.md` (Trading Node, 2026-08-28)
Lens: currency / reality-check (configured floor). Remit: verify every committed
technology, platform, and named-mechanic claim was web-researched or
reality-checked against PRIMARY sources rather than asserted. Flag anything
out-of-date, mis-stated, or unverifiable, with the correction and a URL.
Reviewer did not edit the spine or the memlog.

Method: read the spine and memlog in full; read the pre-verified
`inputs/dig-web-currency.md` (cited, not redone); then independently verified
the claims that live ONLY in memlog-43 without a primary URL in the dig
(cryptography 50.0.1, rclone v1.75.0, click 8.4.2/8.5.0), plus the one
spine-critical claim the dig never covered (Spotware proto **tag 91**), plus the
systemd-mechanics semantics the task named.

---

## VERDICT

**PASS — no currency blocker.** This is, on the pure version/platform axis, an
unusually clean spine: every committed pin is the current release, is
primary-sourced, and the licences and Python-3.14 compatibility all check out.
The one item the dig had left unverified — the Spotware proto **release tag 91**
— is confirmed to exist and to be the newest tag, so the in-house-transport
resolution of the protobuf conflict stands on solid ground.

All surviving findings are **systemd-mechanics reality checks**, not stale
versions: two committed hardening/supervision claims (`DynamicUser=yes` +
`ProtectSystem=strict` vs the storage topology; `WatchdogSec` vs stand-down-alive)
are not fully reconciled with the rest of the design and would bite an
epic-builder at boot time. None blocks the gate; all are surgical amendments.

---

## PART A — Committed claims VERIFIED CURRENT (primary-sourced)

Recorded so the operator can see the currency floor was actually walked. Each row
was confirmed at review time (2026-08-28) against the cited primary source; rows
marked "(dig)" were already verified in `inputs/dig-web-currency.md` and are cited,
not redone.

| Spine claim | Verified | Primary source |
| --- | --- | --- |
| CPython 3.14 target | 3.14.0 final 2025-10-07; uv-installable | dig 3e |
| click ==8.4.2 (reuse QMB pin); 8.5.0 exists | 8.4.2 = 2026-06-24; **8.5.0 = 2026-08-26** (latest) | pypi.org/pypi/click/json |
| protobuf ==7.36.0 (qmf-venue only) | 7.36.0 latest; `requires_python>=3.10`; declares 3.14 | pypi.org/pypi/protobuf/json (+ dig item 1) |
| Spotware proto **release tag 91** | **tag "91" exists and is the newest tag** (91,90,89,88…) | api.github.com/repos/spotware/openapi-proto-messages/tags |
| prometheus_client ==0.26.0 (Apache-2.0) | 0.26.0 = 2026-07-24, cp314 classifier | dig 5a |
| cryptography ==50.0.1 (Apache-2.0 OR BSD-3-Clause) | 50.0.1 = **2026-08-25**; licence string exact; ships cp311-abi3 manylinux x86_64 wheels AND cp314t (free-threaded) wheels | pypi.org/pypi/cryptography/50.0.1/json |
| …"cp314 wheels are free-threaded only; GIL 3.14 resolves the cp311-abi3 wheel" | Confirmed: the only 3.14-tagged wheels are `cp314-cp314t` (free-threaded); ordinary 3.14 falls back to the `cp311-abi3` abi3 wheel | same |
| rclone v1.75.0 (MIT; B2 + S3 backends) | v1.75.0 = **2026-07-31**, latest release | api.github.com/repos/rclone/rclone/releases/latest |
| Ubuntu 24.04 LTS x86-64 + systemd 255.4 | systemd `255.4-1ubuntu8`; systemd-creds/`LoadCredentialEncrypted` available (≥v250) | dig 3c / 3d |
| GitHub runner label `ubuntu-24.04` | Valid; `ubuntu-latest`→24.04 (GA); `ubuntu-26.04` **preview only** | github.com/actions/runner-images |
| chrony provisioned by install | 4.7 (2025-06-12) / 4.8 current; 24.04 defaults to timesyncd so install must add chrony | dig 4a / 4b |
| `chronyc waitsync` preflight gate | Valid chrony subcommand | dig 4 |
| keyring ==25.7.0 (WinVaultKeyring) | 25.7.0 = 2025-11-16; `WinVaultKeyring`, `CRED_TYPE_GENERIC` | dig 6a / 6b |
| systemd-creds `encrypt --name=<ref> - <out>` reads stdin | `-` = stdin per systemd-creds(1); LoadCredentialEncrypted decrypts at start | dig 3d + memlog-43 |
| cTrader hosts/ports demo/live :5035 | PRIMARY (proxies-endpoints) | dig 1j / 1k |
| length-prefixed ProtoMessage framing | 4-byte length-prefixed serialized ProtoMessage — standard Open API framing | Spotware docs (dig item 1 transport) |
| ProtoOARefreshTokenReq in-band refresh | Real message; refresh token no expiry | dig 1n |
| rate limits 50/5 rps per connection | PRIMARY (Getting Started) | dig 1g / 1h |
| heartbeat ≤10 s (TN-4 duty cadence) | PRIMARY (FAQ) | dig 1i |
| one demo + one live connection cap | PRIMARY ("at most … two connections") | dig 10 |
| journald `SystemMaxUse` retention | Valid journald.conf setting | standard |

### Two currency conflicts the spine DISSOLVES correctly (confirmed, no action)

1. **protobuf 3.20.1 SDK-pin vs Python 3.14** — the dig's "single largest
   currency conflict." The spine ships **zero Spotware code** and compiles proto
   tag 91 in-house against `protobuf==7.36.0` (correction #4, TN-11). Because the
   node never installs `ctrader-open-api`, its `protobuf==3.20.1` pin never
   enters the resolver. Tag 91 is confirmed real and protobuf 7.36.0 supports
   3.14 — the conflict is genuinely gone. Residual (already covered by "compiled
   in-house"): the node must generate the `_pb2` modules from tag 91's `.proto`
   with a protobuf-7.x `protoc`.
2. **Twisted vs asyncio** (dig flag 2) — dissolved the same way: the Stack says
   "No Twisted"; the in-house asyncio transport means there is no Twisted reactor
   to coexist with. Confirmed consistent.

### One correctly-graded SECONDARY claim (confirmed, no action)

- **Trendbar basis = BID** is SECONDARY (dig item 2: a Spotware moderator on the
  official forum, no docs page). TN-11 labels it "secondary web evidence," and
  mitigates by measuring the basis per-broker at first connection and forcing
  TICK-based interim backtest-to-live comparison until recorded. This is exactly
  the right handling of a non-primary fact — the currency lens confirms it, no
  amendment.

---

## PART B — FINDINGS

### F1 — HIGH — `DynamicUser=yes` + `ProtectSystem=strict` is not reconciled with the node's on-disk storage topology

- **Where:** TN-16 (hardening set) vs TN-3 (planes/topology) and the Structural Seed.
- **What:** TN-16 commits to `DynamicUser=yes` + `StateDirectory=qmn` +
  `LogsDirectory` + `ProtectSystem=strict`. Under `ProtectSystem=strict` the
  ENTIRE filesystem is read-only to the service except `StateDirectory`
  (`/var/lib/private/qmn` under DynamicUser), `LogsDirectory`, `PrivateTmp`, and
  any explicit `ReadWritePaths=`. But TN-3 places large writable trees on the VPS
  that are NOT obviously under StateDirectory: the "hot rooms tree (raw archive,
  journal, live world room)", a *second* "evidence tier tree", the "passive
  file-sync hub", and the immutable Dukascopy raw archive (a bulk history
  download). With `DynamicUser=yes` the service UID is dynamic and systemd owns
  the StateDirectory path — pointing the node at an arbitrary `/opt/qmx/rooms` or
  a separate data mount requires `ReadWritePaths=` **and** ownership that a
  dynamic UID makes awkward. The spine names neither `ReadWritePaths=` nor a
  StateDirectory-rooted layout for these trees.
- **Why it matters:** As written, the two committed sections are in mechanical
  tension: a `ProtectSystem=strict` + `DynamicUser` service literally cannot
  write the evidence topology TN-3 describes unless every writable tree is either
  (a) rooted under `/var/lib/private/qmn/…` or (b) enumerated in
  `ReadWritePaths=` with pre-created, correctly-owned directories. An
  epic-builder wiring the unit file hits this at first boot (`Read-only file
  system` on the first journal write). This is a reality-check gap, not taste —
  the hardening claim and the storage claim were each adopted from evidence but
  never checked against each other.
- **Fix:** In TN-16, state the reconciliation explicitly. Simplest: root every
  writable tree under `StateDirectory` — e.g.
  `/var/lib/private/qmn/{rooms,evidence,hub,archive}` — and show that in the
  TN-3 diagram; systemd keeps those writable under `ProtectSystem=strict`
  automatically. If the evidence tier / raw archive must live on a separate data
  mount, either name it in `ReadWritePaths=` (and drop the "arbitrary path"
  ambiguity), or drop `DynamicUser=yes` for a fixed `User=qmx` service account so
  the mount can be chown'd deterministically. Pick one and pin it; do not leave
  both hardening and topology asserted without the bridge.

### F2 — MEDIUM — `WatchdogSec` will fight "stand-down is an ALIVE state" unless the keepalive owner is named

- **Where:** TN-4 (process model / stand-down-alive; `WatchdogSec` set).
- **What:** TN-4 sets `Type=notify` + `WatchdogSec` and declares stand-down "an
  ALIVE state" where "the doors keep serving." Under `WatchdogSec`, systemd
  expects a periodic `WATCHDOG=1` datagram; if the node stops sending it, systemd
  treats the service as hung → `SIGABRT` → `Restart=on-failure` → the node
  re-enters the very crash path stand-down was meant to exit, and each such
  restart increments the `StartLimit` counter. The spine does not say which
  component owns the watchdog ping, and stand-down is described as the domain
  loop quiescing ("sequencers refuse-and-journal, adapters quiesce and drain").
  If the ping was riding the domain loop, quiescing it kills the watchdog.
- **Why it matters:** The headline guarantee — "the doors keep serving so
  resurrection stays reachable" and "the node's own stand-down engages first" —
  fails silently if the watchdog keepalive stops in stand-down. This is a named
  mechanic (`WatchdogSec`) whose semantics the design depends on.
- **Fix:** In TN-4, require the `WATCHDOG=1` keepalive (and the initial
  `sd_notify READY=1`) to be owned by the supervisor / door-server layer, NOT the
  domain slice loop, so it continues through stand-down; state that explicitly.

### F3 — LOW — the StartLimit inequality is stated imprecisely (the claim holds, the wording doesn't pin the operative condition)

- **Where:** TN-4 and TN-16 ("`StartLimitBurst`/`StartLimitIntervalSec` … set
  strictly above the node's own crash-loop `(K, T)` so the node's own stand-down
  engages first").
- **What:** The claim DOES hold, but for a narrower reason than "above `(K,T)`".
  Because the node **boots INTO stand-down** (the Kth start is a *successful*
  start that stays alive and stops crashing), systemd's restart counter stops
  advancing the moment stand-down is reached. So the single operative condition
  is `StartLimitBurst > K` — systemd must be willing to perform the K restarts
  that carry the node to the boot which self-detects the loop. `StartLimitIntervalSec`
  being "above T" is neither the operative lever nor sufficient framing (a
  *longer* systemd window counts *more* starts, i.e. is stricter, not looser); it
  only needs to span the burst so the K starts are seen together, and with
  `RestartSec=5s` that span is small.
- **Why it matters:** An implementer reading "strictly above (K,T)" might tune the
  interval and leave burst ≤ K, in which case systemd hits its limit and leaves
  the node **dead** (start-limit-hit) instead of alive-in-stand-down — the exact
  opposite of the intent.
- **Fix:** Restate as: `StartLimitBurst` MUST exceed K (so systemd permits the
  restarts up to the boot that enters stand-down), with `StartLimitIntervalSec ≥
  T`; and note that once stand-down is reached the process no longer exits, so the
  counter decays.

### F4 — LOW — "sd_notify over the stdlib unix socket" implies a stdlib facility that does not exist

- **Where:** TN-4 ("`Type=notify` with `sd_notify` over the stdlib unix socket")
  and the Stack row "Python stdlib 3.14 — … sd_notify".
- **What:** Python's standard library has **no** `sd_notify` helper. Type=notify
  readiness, `WATCHDOG=1`, and `RELOADING=1` must be implemented by the node as
  the raw sd_notify wire protocol: an `AF_UNIX` `SOCK_DGRAM` `sendto($NOTIFY_SOCKET,
  b"READY=1")`, handling the leading-NUL abstract-socket form and an unset
  `NOTIFY_SOCKET`. This is entirely doable with the stdlib `socket` module (and is
  the right call — it avoids a `python-systemd`/`sdnotify` dependency), but the
  phrasing reads as if a named stdlib function exists.
- **Why it matters:** Minor, but it can send an implementer hunting for a
  non-existent call, or (worse) reaching for an external `sdnotify` package,
  contradicting the "no new runtime dependency" intent. (Note: TN-16's
  `RestrictAddressFamilies=AF_UNIX …` correctly includes `AF_UNIX`, which the
  NOTIFY_SOCKET datagram needs — that part is right.)
- **Fix:** Reword to "the node implements the sd_notify protocol over a stdlib
  `AF_UNIX` datagram socket (no `python-systemd` dependency)."

### F5 — LOW — host-only credential sealing needs an explicit `--with-key=host`

- **Where:** TN-12 ("`systemd-creds` `LoadCredentialEncrypted=` (host-key sealed,
  NOT TPM2 …)" and the wizard command `systemd-creds encrypt --name=<ref> - …`).
- **What:** `systemd-creds encrypt` defaults to `--with-key=auto`, which uses
  **TPM2 + host** when a TPM is present. To *guarantee* host-only sealing — the
  spine's explicit intent, because "cloud VPS TPMs do not survive migration or
  rebuild" — the wizard must pass `--with-key=host` (the `auto` family will
  otherwise silently bind to a TPM if the VPS exposes one, reintroducing the
  migration-fragility the design rejects). The spine's example command omits the
  flag.
- **Why it matters:** Without the explicit flag the sealing behaviour is
  environment-dependent (TPM-present VPS vs not), which is precisely the
  non-determinism TN-12 set out to avoid; a migrated host could then fail to
  decrypt every bootstrap credential.
- **Fix:** Pin `--with-key=host` in the wizard command in TN-12, and note that
  host-key sealing means the security boundary is root + filesystem
  (`/var/lib/systemd/credential.secret`), not a TPM — consistent with, and worth
  stating alongside, the compromise-drill/re-provision posture already in TN-12.

### F6 — LOW — currency forward-note: 26.04 LTS is already released; chrony becomes default on the eventual upgrade

- **Where:** TN-16 / Stack ("Ubuntu LTS x86-64 | 24.04 (26.04 planned …)"; "chrony
  | provisioned by install") and TN-14.
- **What:** Ubuntu **26.04 LTS is already GA** (2026-04-23, systemd 259 — dig
  3a/3b). The spine's choice of 24.04 is **correct and defensible today**: my
  independent check confirms `ubuntu-latest` still maps to 24.04 and `ubuntu-26.04`
  is preview-only on GitHub runners, so pinning `ubuntu-24.04` matches the CI
  runner exactly. This is NOT stale. The only forward-note: on the eventual 26.04
  upgrade, chrony is the **default** time daemon (dig 4b), so TN-14's provisioning
  step "installs chrony because 24.04 defaults to timesyncd" becomes a
  verify-not-install step; and the CI lane should not move to `ubuntu-26.04` until
  it leaves preview.
- **Why it matters:** Purely so the "26.04 planned" note carries the two
  behavioural deltas (chrony default; runner still preview) rather than reading as
  a drop-in bump.
- **Fix:** Add a one-line note under TN-16's 26.04 deferral row: "on 26.04, chrony
  is default (provisioning verifies rather than installs); hold the CI pin at
  `ubuntu-24.04` until `ubuntu-26.04` leaves runner preview."

---

## COUNTS

- Critical: 0
- High: 1 (F1)
- Medium: 1 (F2)
- Low: 4 (F3, F4, F5, F6)

No currency/version staleness anywhere; the substantive items are systemd-mechanics
reconciliations. Gate: **PASS**, amend F1/F2 before the unit files are authored.
