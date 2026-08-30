# Corpus verdicts — Adjudicator A (Opus), trading-node architecture sitting

Date: 2026-08-28. Seat: corpus ADJUDICATOR. Standing rule obeyed: **corpus first** — every
question answered from the corpus where the corpus answers it; only corpus-silent residue is
written up for the operator, in plain words.

Authority order applied throughout:
current operator rulings (`tracker/trading-node-notes.md`, memlogs, PRD operator-ratified lines)
> `docs/` ratified corpus (constitution, DEC ledger, contracts, ADRs, scenarios)
> architecture spines (AD / B / QL)
> PRD `[MINED]` doctrine (direction; binds nothing until ratified here)
> GitBook primer baseline
> `archive/recovery/` K-rules (evidence only; each needs fresh ratification).
QMX-discussion is BARRED for risk/sizing (L37, DEC-0156).

Vocabulary: **the trading node** — one product, modes `paper | live`. Banned words appear only
inside quotations of a cited source.

### Source note

The task named six dossiers. Five exist on disk (`dig-docs-node-doctrine.md`,
`dig-prd-docwork-tracker-qa.md`, `dig-primer-and-recovery.md`, `dig-devops-repo-facts.md`,
`dig-web-currency.md`); **`dig-spines-and-research.md` does not exist** in
`.../architecture-NODE-2026-08-28/inputs/`. Four code inventories are present and were read in
its place (`code-qmb-host.md`, `code-qmf-venue.md`, `code-qmf-data-calendar-recorder.md`,
`code-qml-core-registry-analytics.md`); the AD/B/QL spine content was picked up through
`dig-prd-docwork-tracker-qa.md` PART B5 (`discovery-architecture-sessions.md`) and verified
against `_docwork/ledger.yaml` directly. Where a dossier cite looked decisive I opened the
source; those independent checks are marked **[verified by A]**.

### Headline

**Zero genuine blockers.** Every open item below is a cheap-veto assumption the sitting can
proceed on. The single item that must be settled before real money moves — the KSA
trigger→level→effect matrix — is not an architecture blocker: the corpus's own mechanism
(`configurable: true` + "a blank value blocks live money", L38 / FR-035) lets the spine bind the
shape now and hold the values as a named pre-live operator ratification.

---

## QA1 — Naming, packaging, import/distribution name, publishing boundary, and the node's CLI

### Verdict: **PARTIAL**

### What is settled

**The node is an application-layer product built ON QMF, never a roster package.**
`docs/constitution.md:32` (L7): *"QMF is a reusable toolbox … QMF is not an application."*
`docs/constitution.md:34` (L8): *"Application loops, orchestration flows, scheduled lifecycles,
and product UI remain outside the QMF foundation unless a later contract explicitly admits
them."* `docs/constitution.md:78` (L31): *"Everything downstream of QMF — **the trading node**,
backtesting, the agentic system, and the product UI — must be built with QMF libraries and must
not re-implement or bypass the framework's contracts."* The precedent is COMP-QMB:
`docs/components/qmb.md:17` — *"an application-layer product built ON QMF, never a roster
package."*

**The node is the one consumer permitted to import `qmf-venue` — and QMB is forbidden it.**
`docs/components/qmb.md:142`: QMB may never *"add an inter-library edge into QMF beyond the six
declared dependencies — notably no edge to COMP-QMF-VENUE, whose live adapters and brokerage
ports are trading-node territory."* `docs/constitution.md:76` (L30) grants an application built
ON QMF the right to import `qmf-risk` and the qmf-venue-free contracts directly; the node is the
exception that also carries the venue edge, because the venue edge *is* the node's job
(DEC-0142, `docs/decisions/ADR-0007-venue-neutral-integration.md:40`). This is load-bearing for
the CLI question below.

**Glossary term.** "Trading Node" — *"A later QMX application that owns live-trading runtime and
orchestration. The Trading Node is not qmf-core and is outside QMF V1 documentation scope"*
(`docs/glossary.md`, Trading Node entry). Family names in play: QMF, QMB, QML, QMA.

**Workspace placement precedent (repo fact, not a ruling).** `pyproject.toml:85-92` on
integration: `[tool.uv.workspace] members = ["packages/*", "extensions/*", "qml", "qmb"]`. Roster
packages live under `packages/` and import as the `qmf.*` PEP 420 namespace; **application-layer
products sit at top level and import under their own top-level name** (`qmb/pyproject.toml:23-29`,
`qml/pyproject.toml:14-20` set `module-name`). `docs/decisions/ADR-0012-runtime-packaging-quality.md:36`
closes the roster at seven: *"One repository is a uv workspace holding seven installable packages
… No distribution may ever contain `qmf/__init__.py`."* So a node package under `packages/` or in
the `qmf.*` namespace would violate the closed roster; a top-level directory alongside `qmb/` and
`qml/` is the ratified-by-precedent shape.

**DEC-0159 and DEC-0185 Ruling C, read exactly [verified by A].**

`_docwork/ledger.yaml:1491` (DEC-0159, status ratified) — scope is explicitly *the QMB product*:
> "The QMX experimentation/backtesting product is named QMB — one library plus the qmb CLI, both
> halves sharing the name; the command is qmb, superseding the position paper's DC-5 qmx-command
> proposal (QMX names the entire platform and reuse would confuse operator and agents alike) …
> Every agent workspace provisions the SAME qmb CLI as a pinned dependency — one CLI for agents
> and operator alike."

The "one CLI for agents and operator alike" clause is about **agent workspaces all provisioning
the same `qmb`**, not about the platform having exactly one command in total. DEC-0159 also
ratifies the door shape the node should copy: *"every capability exists once, in the library, as a
pure function; doors — CLI first (the product face), Python API, MCP later — are thin hand-written
wrappers carrying only adaptation logic … door parity is enforced by a tier-2 contract test
asserting identical function surface and semantics across doors."*

`_docwork/ledger.yaml:1725` (DEC-0185, status ratified), RULING C, verbatim:
> "RULING C closes the sitting's open question 2: **QML ships NO CLI, ever in this shape** —
> QMB's CLI is the single command-line surface ('just put it under QMB… I don't know why we
> would have two command lines')."

**Answer to the pointed question: "no second CLI" was scoped to QML, not platform-wide.** The
ruling's subject is QML; the sitting it closes is the QML sitting; the operator's quoted line was
spoken about putting QML's commands under QMB. The trading node is not named, and the node is by
glossary and DEC-0142 *outside QMF V1 documentation scope* entirely. The operator's lean against
proliferating command lines is real and should be weighed — but it is a lean, not a node ruling.

### What remains

The node's package directory name, import name, distribution name, publishing boundary, and
whether its operator doors ride `qmb` or ship their own command. **No corpus layer mentions PyPI,
a private index, or publication of any QMX package [verified by A: `grep -rni "pypi|publish
to|private index|distribution name" docs/ _docwork/ledger.yaml` returns only the toolchain rows in
`docs/architecture/stack.md:28,:34` naming PyPI as the *source* of pyright and tzdata].** Nothing
in the corpus authorizes publishing anything.

### What the spine should bind

1. The node is a top-level workspace member alongside `qmb/` and `qml/`, importing under its own
   top-level name — never under `qmf.*`, never inside the closed seven-package roster (ADR-0012:36).
2. The node is the sole consumer of `qmf-venue`; `qmb` keeps its ban (`qmb.md:142`).
3. The node's doors follow the ratified DEC-0159 shape verbatim: capability once in the library as
   a pure function; thin doors; tier-2 door-parity contract test; the UI backend consumes the
   Python API in-process.
4. Nothing is published to any index until a ruling says so; the node is installed from the
   canonical checkout (NFR-10).

### Operator question — Q-QA1 · ASSUMPTION (cheap veto)

> The node needs its own way for you to type commands at it on the VPS — things like "what's the
> status", "kill everything now", "promote this bot". **Recommended: give the node its own short
> command of its own** (e.g. you'd type `qmx-node status` on the server), because the backtesting
> command `qmb` is forbidden by the corpus from touching the live broker at all, so folding live
> controls into it would break a ratified boundary. Alternatives: (a) add a `qmb node …` group
> anyway and accept the new dependency; (b) give the node no typed command at all and drive it only
> from the desktop app later.
> *Cheap veto: renaming or folding a command later costs a line of config; nothing unwinds.*

### Operator question — Q-QA1b · ASSUMPTION (cheap veto)

> **Recommended: nothing QMX is ever uploaded to a public package index** — it is installed from
> your own checkout on your own machines. Example: the VPS gets the node by pulling the repo and
> running one install command, not by downloading "qmx-node" from the internet. Alternatives: a
> private index later if you ever run several machines; a public release only if the
> open-sourcing direction in the PRD is ever taken up.

---

## QA2 — Base branch for node work

### Verdict: **RATIFIED-ANSWER** — build on `integration`, specifically `origin/integration` @ `ef9bb25`

### Cites

- `CLAUDE.md` (project rules, working tree): *"Implementation runs in the factory lanes only: the
  attended epic-factory … one background workflow per epic in a worktree, merging to
  `integration` … `main` moves only by the operator's own squash-merge click."*
- `QMX-worktrees/node-inventory/FINAL-REPORT.md:3-6`, `:102-107`: all 35 fix cards done and PROVEN
  **against `integration`**; QA Battery + Skylos green on the final push (`e874256`); *"`main`
  moves only by the operator's squash-merge click."*
- Memory `qmx-project-state.md`: integration tip `ef9bb25`; next step is the operator's
  squash-merge click.

### Verified by A (repo facts, read-only)

- `git merge-base --is-ancestor integration main` → **integration is NOT merged into main.**
- `git ls-tree --name-only main` → main contains `docs/`, `_docwork/`, `_bmad-output/`, `tracker/`,
  `adws/`, `archive/`, `workroom/`, `recorder/`, `queue/`, `pyproject.toml`, `uv.lock` — and
  **no `packages/`, no `qmb/`, no `qml/`, no `extensions/`.** All built code exists only on
  integration. There is no third option.
- `origin/integration` = `ef9bb253fc87ec3a66d5c6a78f3cb95bb45c760c` ("FIX-ROUND-1: seal the final
  report with the green CI verdicts").
- **The LOCAL branch ref `integration` is stale at `2c8d495`**, which is an ancestor of `ef9bb25`
  — i.e. it is behind by the entire QA fix round. `refs/remotes/origin/integration` and
  `refs/heads/fix/qa-round-1` both point at `ef9bb25`.

### What the spine should bind

Node epics branch from **`origin/integration` @ `ef9bb25`** (not the stale local `integration`
ref), and land back on `integration` through the factory lane exactly as the 23 foundation epics
did. If the operator performs the squash-merge to `main` first, the node lane rebases onto `main`
and `integration` re-forks from it; that is a mechanical re-point, not a design change. Any
instruction to "start the node from main" must be refused on the ground that main carries no code.

---

## QA3 — Overall topology: machines, planes, data flows, trust boundaries

### Verdict: **PARTIAL** (a strong ratified core, with placement residue)

### What is settled

**Two deployables, not three.** `tracker/map.md:50` (session accord): *"two deployables
(installable QMX app + one Trading VPS); middle node absorbed into the app (ML training ~quarterly
in cloud sandboxes, shadow rollout); no central backtest engine."* This absorbs the "middle sync
server" idea banked at `tracker/map.md:32` — it survives as an ops concept, not a deployed host.

**Backup / data topology is ratified verbatim** (AD-20, DEC-0118): *"the trading-node VPS records
and syncs down, the workstation holds the working archive, and the bucket catches nightly
copies"* — `docs/contracts/ct-14-backup-restore.yaml:22`; `docs/components/qmf-data.md:115`;
`docs/scenarios/SCN-0004-off-machine-backup.md:21`; `_docwork/ledger.yaml:1109`.

**Storage architecture (proposed, operator-recorded).** `tracker/map.md:66`: working Parquet
archive on the workstation; *"trading VPS runs the always-on tick recorder and syncs down; nightly
backup to an object-storage bucket (B2/R2 class, ~$1-5/mo); no database server"*; backup is an
inbuilt platform feature; *"Trading VPS exists by default; procuring it is Mubarak's side."*

**No database server anywhere in V1.** NFR-10 (`prd.md:573-586`, operator-ratified 2026-08-21):
works out of the box (`uv add`, no DB server, no Docker for QMB); one person can deploy, monitor
and repair. The old two-node + PostgreSQL standing store + `CT-SYNC-01` topology is **DEAD**
(`mine-node.md:284-289`; `correlate.md:165`); only its placement/authority shape survives.

**The node is one OS process.** K-03 (`KEEP`, recovery layer, needs fresh ratification):
*"Trading Node = one OS process"* hosting bots, Books, the BMS write side, MIS-Live, KSA, the
adapter + connection manager, records/data authority, and the operator powers surface; in-node
contract boundaries are **direct module calls, not a microservice network**
(`archive/recovery/trading-node-delta/trading-node-delta.md:37`). D-05 explicitly DROPs
microservice-per-component node topology (`trading-node-delta.md:182-194`).

**Trust boundaries that bind now.**
- `docs/lenses/security/security-model.md:26-32`: command caller → venue adapter is ratified
  defined-unwired surface; order-path internals stay node territory.
- `docs/contracts/ct-21-venue-secret-session.yaml:21`: **exactly one live refresher per
  credential** — *"a workstation tool never refreshes a credential a VPS session owns."*
- `tracker/trading-node-notes.md:50`: demo/paper evidence is role-scoped within `world = live`;
  **sandbox-produced evidence carries `provenance = sandbox` and cannot merge into the operator
  store.**
- AD-26: factory sandboxes never hold live secrets.
- `docs/architecture/stack.md:159`: hardened OS-level runtime confinement (seccomp-class on Linux)
  for bot isolation is *"a named deferred dependency of the node/platform sitting"*, and
  `_bmad-output/planning-artifacts/epics.md:2622-2625` adds *"V1 does not wait on it."*

**The always-on evidence tier is a placement boundary, not a deployment mandate.** `prd.md:432-441`
(`[MINED]`): *"explicitly not a database server and not a second writer: the hot path never blocks
on it (only disk physics fail-closes trading); sync is one-way, watermarked, idempotent,
resumable, under verify-before-purge … the only reverse crossing is the click-gated promotion
pull. A placement boundary, not a mandate for separately deployed services."*

### What remains

Whether the evidence tier is a second host or a second directory tree on the same VPS; the
laptop's OS at Phase 3 (Windows 11 now, Omakub Linux later — recorded as an intent, never ruled);
the cloud-sandbox provider for quarterly training (Modal/E2B named as *direction, no evaluation*,
`addendum.md:11-14`).

### What the spine should bind

Three planes, two machines, one bucket: (1) the **VPS plane** — one node process plus the tick
recorder, sharing a disk, distinguished by `WriterId` (`docs/lenses/ops/runbook.md:107-116`);
(2) the **workstation plane** — working archive, research reads, the future desktop app, and
**no live venue credential**; (3) the **bucket** — nightly encrypted versioned copies. Flows are
one-way node → workstation → bucket, with exactly one reverse crossing: the click-gated promotion
pull (K-17, `prd.md:144-150`). Cloud sandboxes are a fourth, *episodic*, plane whose evidence
carries `provenance = sandbox` and never merges.

### Operator question — Q-QA3 · ASSUMPTION (cheap veto)

> **Recommended: exactly two computers plus one online storage bucket — the always-on evidence
> side lives as its own folder tree on the same VPS, not a third machine.** It keeps the whole
> thing to one thing to pay for and one thing to patch, and the corpus only ever asked for a
> *placement* boundary, not a separate server. Example: the node writes live ticks to
> `/var/qmx/live/` and the evidence side reads and archives from `/var/qmx/evidence/` on the same
> disk. Alternatives: (a) a second cheap VPS for evidence and analytics, if you ever want heavy
> analysis to never touch the trading machine; (b) revive the separate sync server.

---

## QA4 — The live composition root: "boot = compose, fingerprint, seal", and the promotion record

### Verdict: **PARTIAL** — the mechanism is ratified; the named ceremony is not

### The "compose, fingerprint, seal" ruling does not exist [verified by A]

`grep -rni "three-tier composition|compose, fingerprint|fingerprint, seal|boot = compose"` over
the whole repo returns **only the dossier's own text**. There is no ratified boot ceremony by that
name. The phrase originates as the *code inventory's own label* for QMB's config compiler
(`code-qmb-host.md:51`, `:201`) — not as a corpus ruling. Do not cite it as one.

### What is ratified in its place

**The composition root is the platform's ratified mechanism.**
`docs/architecture/overview.md:46,:50`: *"No component below the composition root reads the system
clock … the application's composition root injects the real system clock for `world = live`, or a
data-driven replay clock … for `world = replay`."* `:209`: *"QMF has no autonomous startup or
orchestration path; a later QMX application composes the libraries and injects the clock at the
composition root."* Sinks (`ObservationSink, JournalSink, RecordSink, SecretStore`) are injected at
the root (AD-28, `docs/components/qmf-venue.md:57`); records are root-minted (AD-25); and OR-06
relocated the CT-33 mint to the composition root — *"the mint moves to the composition root (QMB /
the host), AD-25 root-mints pattern"* (`qa/_trace/rulings-corpus-verdicts.md:174-203`, RATIFIED
Option A; fixed as FC-05).

**The compose → fingerprint → freeze pattern is ratified for a *run*, in DEC-0160**, and is the
node's obvious template: *"exactly one fully-resolved, read-only, schema-validated run-config
artifact … its fingerprint is the run-id root and the ledger key"* (`_docwork/ledger.yaml:1503`).
Its implementation exists and is reusable: `compile_run_config` merges layers under a fixed
precedence, derives `world` from clock+provenance (never caller-declared), resolves cites through
the one registry-read port, then `_finish` *"Fingerprint[s] identity content and freeze[s] the
resolved artifact"* — *"Same inputs yield a byte-identical artifact"*
(`code-qmb-host.md:201-220`; `qmb/src/qmb/config/compiler.py:474,:731,:11`). Caveat the node must
carry: QMB *"never mints a live binding — Always `replay`"* (`qmb/src/qmb/config/replay.py:119`);
a `world = live` binding mint is node-new.

**Two-phase venue wiring is ratified** (DEC-0138, CT-18): static credential-free capability
declaration at construction, per-`(VenueId, account)` venue-observation profile verified before the
first command, fixed wiring order (`docs/contracts/ct-18-venue-capabilities.yaml:14,:17,:20`).

**Bind-time is where the node's real "seal" already lives.**
`docs/contracts/ct-28-book-binding.yaml:31-37` enumerates the `bind_time_capability_check`:
required venue capabilities, settlement currency equal to the Book's `accounting_currency`, the
shared-flatten signature where netted, **a present SQS baseline for every sensor**, a live-path rung
baseline on *this deployment's* `(OS, CPU-class)` tuple, and a non-contradicted rank table —
*"a shortfall refuses at bind time, never at trade time."*

### What the node must fingerprint at boot (spine binding)

Nothing in the corpus enumerates this; it is derivable and should be bound here. One frozen
`ResolvedNodeConfig` whose fp1 becomes the `boot_epoch` identity stamped on every journal row,
covering at minimum: CPython + package versions and the `uv.lock` digest; the Spotware proto
artifact tag (`registry:venue_protocol_artifact` = 91) and its descriptor-set digest; the tzdata
pin and every calendar identity in play (market-hours, day-boundary, news); the registry as-of set
fingerprint; every Book-definition and BMS-definition fp1 and every CT-28 binding-record fp; the
CT-18 capability-declaration fp and the venue-observation-profile fp per `(VenueId, account)`; the
pinned error-map rows; every injected do-not-default node constant (submission deadline, retry,
pool, throttle, drift bands, crash-loop K/T); the clock identity; the `WriterId` set; and the
`SecretRef` ids — **references only, never values** (L34, `docs/constitution.md:84`). Because
`journal.sequence` is gapless per `(writer, boot-epoch)` (`docs/contracts/ct-13-journal.yaml:34-47`),
sealing the composition into the boot epoch makes every evidence row traceable to the exact
composition that produced it, for free.

### Promotion to live: human-only, and the record shape the node must check

`docs/constitution.md:50` (L17): *"**Only a human may promote a registered artifact into the live
zone.**"* `_docwork/ledger.yaml:384` (DEC-0041, ratified). The record shape is AD-18,
`docs/decisions/ADR-0015-registry-records-and-promotion.md:43`: human-only signer; signed
immutable record; **a mandatory plain-words summary declared an identity field** — *"the signature
attests the exact words the human read"*; V1 signing is the operator's recorded approval attesting
the record's `fp1` string with reviewer identity and instant, no crypto; the journal `promotion`
event carries **only the card fingerprint plus `correlation_id`**; and *"the promotion gate itself
— workflow, UI, timing — is platform territory outside QMF."*
`docs/scenarios/SCN-0007-human-promotion.md:33`: the card carries the Book-definition (or
BMS-definition) fingerprint as an identity field so a signature *"can never attest a superseded
template."* `:21`: three-layer admission — registration linters, a technical demo/paper shakedown,
one operator signature on one assembled page, plus CT-32 performance evidence — *"with **no trial
period, probation window, or paper-performance gate** and no paper role permitted to gate live
money."*

So the node's pre-live check is mechanical: a promotion card whose `fp1` the operator signed,
carrying the plain-words summary, the Book/BMS-definition fp, reviewer identity and instant; a
CT-28 binding with `role = live`, `world = live`, passing the bind-time capability check; and the
three admission layers green. `prd.md:144-150` adds the `[MINED]` rider: the click *"re-runs its
full precondition battery server-side against fresh state — displayed-eligible is never a
guarantee, stale evidence never authorizes; the crossing is a node-initiated pull, idempotent by
artifact key, landing the unit ADMITTED (no intents, no ledger) with live activation a later,
separate boundary."*

### What remains

The `ADMITTED → activation` boundary is `REOPEN` in the recovery layer (C-15,
`trading-node-delta.md:153-176`; K-22/K-24) and `[MINED]` in the PRD. The corpus does not settle
whether one signature both admits and activates.

### Operator question — Q-QA4 · ASSUMPTION (cheap veto)

> **Recommended: promoting a bot and switching it on live are two separate clicks.** The first
> click records your signature and files the bot as approved but idle; a second, later action
> actually lets it place orders — so an approval made on Sunday can't quietly start trading before
> you meant it to. Alternatives: (a) one click does both (fewer steps, but approval and exposure
> become the same instant); (b) one click plus a fixed delay before it can trade.

---

## QA5 — Live cTrader on IC Markets: sessions, reconciliation, secrets

### Verdict: **PARTIAL** — an unusually large ratified half; the node owns transport, scheduling, and numbers

### Ratified (the node implements, never redefines)

- **Five command kinds, four outcomes.** `place_order | cancel_order | close_position | close_all |
  amend_protection` (`docs/scenarios/SCN-0005-uncertain-venue-submission.md:21`;
  `docs/contracts/ct-19-venue-command.yaml:19`). `docs/constitution.md:86` (L35): *"Every venue
  submission resolves to accepted-by-venue, rejected-by-venue, denied-locally, or UNKNOWN; a
  timeout is never a rejection, an UNKNOWN blocks its command stream until an explicit recorded
  resolution, and no QMF component retries, assumes an outcome, or invents terminal state."*
- **Command retry is prohibited**; *"session recovery … never resubmits a command"*
  (`ct-19:31`; `docs/components/ctrader.md:144` FM-1).
- **UNKNOWN clears only via `resolve_unknown`**, an application (node) call —
  `resolve_unknown(command identity, resolution ∈ observed-accepted | observed-absent |
  operator-attested)`; *"the adapter never clears its own block"* (glossary; `ct-19:30`;
  `tracker/trading-node-notes.md:46`). The block is per command stream `(VenueId, account)` and
  **clears on the resolution, never on a reconciliation verdict**.
- **Protection acts refused by the block never evaporate** — they stand as AD-36 standing
  protection intents, re-decided (not retried) and satisfied **only** against a `reconciled`
  verdict; `drift | unknown | out-of-lookback` alarm and hold (`SCN-0005:33`; `ct-30:22-23`).
- **Reconciliation**: on-demand complete read-back of orders/fills/positions/balance over a
  mandatory declared lookback (do-not-default); verdicts `reconciled | drift | unknown |
  out-of-lookback`; *"Reconciliation gates the command pipe only — the sensing pipe never blocks
  on it — and when it runs and what a verdict triggers are node/BMS authority"*
  (`docs/contracts/ct-20-venue-event.yaml:26,:44`).
- **Startup reconciliation before trading, command pipe only.** `tracker/trading-node-notes.md:32`
  (K-39): *"startup reconciliation gates the COMMAND pipe only (sensing/MIS flows from boot)."*
- **Recovered fills commit before healthy.** `docs/components/ctrader.md:144`: *"on disconnect
  in-flight commands become UNKNOWN; recovered fills commit through evidence before a session
  reports healthy."* K-43A/K-55: fills correlate by `clientMsgId` (≤100-char label).
- **Session duties are the node's to schedule.** `docs/components/qmf-venue.md:93`: heartbeat,
  token refresh, reconnect, gap replay, verification monitors — *"the adapter defines the work,
  the application runs it."* Async is permitted at the venue edge and only there (AD-15).
- **Exactly one live refresher per credential** (`ct-21:21`) — the refresh token dies on use
  (`tracker/trading-node-notes.md:49`).
- **Secrets as references.** L34 (`docs/constitution.md:84`); AD-26; CT-21 — connection manager is
  the sole in-memory value-holder through an injected `SecretStore` (read + atomic replace);
  rotation is store-before-discard; a failed store after rotation alarms and blocks the command
  pipe while sensing continues; the compromise drill is cTID re-authorization → application
  credential reset → store replacement → session restart.
- **Venue facts** (`docs/components/ctrader.md:57-67`, DEC-0135): 50 req/s non-historical + 5 req/s
  historical per connection; 10 s heartbeat bound; ~30-day access token, never-expiring refresh
  token; **no server clock — receive-time recording mandatory**; three numeric scale systems;
  demo and live are separate hosts → two simultaneous connections; proto tag 91. Independently
  confirmed against Spotware's own documentation in `dig-web-currency.md` rows 1g–1n, 10.
- **Broker identity is deployment configuration.** DEC-0139 (`ADR-0007:38`): *"IC Markets is
  stated intent, not commitment."*

### The transport-library question is already answered by constraint [verified by A]

`DEPENDENCIES.md:11-13` prohibits *"any **platform-imposing** dependency — one that dictates an
event loop, reactor, daemon, or runtime the platform must adopt — e.g. Twisted."*
`DEPENDENCIES.md:47` and `docs/components/ctrader.md:51`: Spotware's OpenApiPy SDK is
**reference-only**, rejected as a runtime dependency precisely because of its pinned Twisted
reactor; only the message definitions are consumed; **zero Spotware code runs**. `qmf-venue`
already declares `protobuf==7.36.0` and compiles the proto in-house
(`packages/qmf-venue/pyproject.toml:9-18`).

**Correction to a dossier flag.** `dig-web-currency.md` lists as its highest-priority
cross-cutting flag that `ctrader-open-api==0.9.2` hard-pins `protobuf==3.20.1`, which cannot run
on Python 3.14, and proposes process isolation or vendoring. **That conflict is moot** — the SDK it
concerns is already rejected corpus-wide, and the node compiles the descriptor set itself against
modern protobuf. The spine must not "resolve" a conflict the corpus already dissolved, and must
not adopt the SDK to create it. What the web dossier *does* usefully confirm is that no maintained
asyncio-native cTrader client exists (row 1f, UNVERIFIED) — so the node writes its own client on
stdlib `asyncio` over TLS (row 1l: *"The TCP client connection must use SSL"*), which is exactly
what AD-15 permits at the venue edge and nowhere else.

### What the node must decide or build (do-not-default, and code-verified gaps)

**Numbers the node owns, held nowhere in `variables.yaml`:** the **submission deadline** that
triggers UNKNOWN (*"declared, application-injected, do-not-default"*, `ADR-0007:36`, `ct-19:47`,
`tracker/trading-node-notes.md:47`); retry, pool, throttle and health constants
(`tracker/trading-node-notes.md:27`, R-07 numbers are RECONFIRM-grade evidence only); the
below-ceiling pacing cadence.

**Code gaps** (from `code-qmf-venue.md`, `integration@ef9bb25`): there is **no wire client, no
socket, no submit path** — `CTraderAdapter` is a frozen-dataclass facade of decoders, pacer,
topology, tokens and duties; **no message ENCODE / request builder** exists; **no descriptor-set
ships** in the package; **no volume-in-cents decoder** exists (only price and money scales are
implemented); **no equity derivation** exists (K-54 requires balance + quote-currency unrealized
PnL because cTrader supplies no equity field); wire-level `clientMsgId` generation and matching
does not exist (only the durable binding discipline does); `static_capability_facts()` supplies
**4 of 23** CT-18 fields, leaving 19 field markings and the pinned error-map rows for the node;
`ProbeTransport` is the package's only Protocol and **no concrete transport ships**; and the
`SessionTopology` requires exactly one demo + one live endpoint (`required_connection_count = 2`)
but **no code opens or holds two connections**.

### Secret store, per plane

`docs/lenses/ops/runbook.md:122` and `security-model.md:61`: values are injected at the composition
root from the deployment environment's protected store, *"`systemd-creds`-class on the VPS"*;
mechanics and key custody land at this sitting (`ct-21:28`). `dig-web-currency.md` rows 3d and 6b
confirm the substrate exists on the target OS (systemd ≥250 gives `LoadCredentialEncrypted=` with
optional TPM2 sealing; Ubuntu 24.04 ships 255.4, 26.04 ships 259) and that Windows Credential
Manager is reachable from Python via `keyring`'s `WinVaultKeyring`. **But the corpus argues the
laptop should hold no live venue credential at all**: `ct-21:21` — *"a workstation tool never
refreshes a credential a VPS session owns"* — and the refresh token dies on use. The Windows store
is therefore the right door for *workstation-local* secrets (research API keys, the SSH key to the
node), not for the live venue credential.

### Operator question — Q-QA5 · ASSUMPTION (cheap veto)

> **Recommended: the live broker login exists only on the VPS, never on your laptop.** The broker's
> refresh token is single-use — if a tool on your laptop ever refreshed it, the VPS's own session
> would be silently locked out mid-trade, which is the one failure the corpus names by hand.
> Example: you'd paste the credential once into the VPS through a guided setup step, and your
> laptop would only ever hold the SSH key that reaches the VPS. Alternatives: (a) keep a
> read-only demo credential on the laptop for testing (safe, since demo is a separate connection);
> (b) mirror the live credential to the laptop for emergencies and accept the lockout risk.

---

## QA6 — The protection set the node RUNS but does not redefine

### Verdict: **RATIFIED-ANSWER for every mechanism; PARTIAL only on named node-owned values**

Per item: binding artifact, then the constant or policy the node must own.

**Kill switch (global).** `docs/contracts/ct-30-control-action.yaml:27`; `docs/components/qmf-risk.md:429`;
glossary; AD-36 (`discovery-architecture-sessions.md:87`); `tracker/trading-node-notes.md:55` —
global black-swan authority; stops **all new trading including paper**; sensor-fed (*"MIS and SQS
are inputs never authorities"*); escalates automatically; **de-escalates only by a human**; effect
∈ `suspend_new | drain | close_all`. `ct-30:35`: *"Which effect fires at which severity is node
authority … never the trigger→level→effect matrix."*
→ **Node owns:** the trigger→level→effect matrix, the severity-policy values, and the
connection-down behaviour. **No registry variable for any of these exists** — `variables.yaml`
carries `kill_line_capital_floor` but no `kill_switch` key of any kind. The node mints them, all
`configurable: true` per L38.

**Kill switch behaviour when the broker connection is down.** `tracker/map.md:79` records this as
*"nowhere designed … the one component with unbounded failure cost."* But the corpus constrains it
so tightly that the answer is derivable and should be bound: `suspend_new` is local and instant
(no venue round-trip — `packages/qmf-venue/src/qmf/venue/blocking.py:744`), so it fires
immediately; `drain` and `close_all` are venue-facing, so under an outstanding UNKNOWN or a dead
line they become **standing protection intents** — journaled before dispatch, restart-proof,
re-decided (never retried), never time-expiring, and satisfied **only** against a `reconciled`
verdict, alarming and holding open on `drift | unknown | out-of-lookback` (`ct-30:21-23`;
`SCN-0005:33`). Nothing is retried, guessed, or assumed terminal (L35).

**Kill line (per-Book).** Named apart from the kill switch by ruling (`ct-29:52`; `ct-30:27`;
`ADR-0008:32`): a per-Book capital floor that **auto-flattens that Book's scope and stands the
Book down** — *"a 3am breach never waits for the operator"* (`qmf-risk.md:431`). `close_reason =
kill_line_flat` is minted apart from `protection_forced_flat` (`ct-29:52`).
→ **Node owns:** the detector wiring and the flatten dispatch. The **value** is Book-declared —
`registry:kill_line_capital_floor` (`variables.yaml:548`, configurable, declared-per-book, the
SAME number as `loss_floor`); a blank blocks live money (`ct-22:23`).

**Flatten authority — ASSIGNED and CLOSED.** `ct-30:25`; `SCN-0005:35`; `ADR-0008:32`: operator
unconditional; Book policy through pre-declared trigger classes; the protection authority where
the node's severity policy says `close_all`; venue-delegated where the venue manages it; **never
the adapter** (`adapter_self` is limited to `suspend_new, drain, throttle, session state`).
→ **Node owns:** which effect fires at which severity, and the required typed close scope
(`account | account-binding | instrument-within-binding`) its kill path states
(`tracker/trading-node-notes.md:48`).

**News blackout.** `docs/scenarios/SCN-0008-pair-scoped-news.md`; `docs/contracts/ct-31-control-window.yaml`
— instrument-scoped via **dated per-instrument currency-exposure records**, *"reading a currency
out of a symbol is prohibited"*; blocks **new entries only, live and paper alike**; never an exit,
protection amendment, protection action, or observation; the would-have-been decision is journaled
on the veto path as a suppressed decision (`SCN-0008:35`; `ct-25:38`); fail-closed on a missing
exposure record (treated-as-affected + blocked + `data quality` alarm); *"there is no live skip
button"*; the ±15-minute buffer is *"on record as withdrawn"*.
→ **Node owns:** `news_blackout_before` / `news_blackout_after` per window kind (configurable, no
spine value — `variables.yaml:438,:449`), and the mapping from the provider's verbatim impact
label to a window: *"QMX mints no severity scale; severity→window is node mapping"* (`ct-31:33`).

**Dead zones.** Both kinds ratified (`ct-31:17,:43`; `tracker/trading-node-notes.md:61`;
`ADR-0008:32`): a `daily_dead_zone` band and `session_handover_buffer` windows with a mandatory
anchor `pre-close | post-open | both`. Entries pause; **exits, safety, and data are never
blocked**; *"pauses TRADING ONLY; data streaming continues; NOT kill-switch logic"*
(`trading-node-notes.md:18`).
→ **Node owns:** `daily_dead_zone_width`, `session_handover_buffer_width`,
`session_handover_buffer_anchor` (`variables.yaml:669,:680,:691`). **`daily_dead_zone_width`
carries recorded contradictory evidence** — a one-hour table row against Flow 9's ~3-hour prose,
recorded as a disagreement under the corpus-precedence exemption. See Q-QA6.

**SQS (Spread Quality Sensor).** L23 (`docs/constitution.md:62`) keeps it distinct from news
controls. AD-39 / DEC-0153: formula fixed as
`registry:spread_quality_sensor_formula` = historical average session-window spread ÷ current live
spread (`variables.yaml:460`, non-configurable formula, configurable parameters); per-class hard
block, hysteresis band, outlier guard, per-quote cadence (*bar-sampled SQS is refused at the
door*); *"sensor computes, transport carries, Book door decides"*; **a live binding requires a
present baseline** (`ct-28:31-37`).
→ **Who feeds spread history:** not named in one sentence, but closed by construction — the only
source of session-window spread history in the topology is the node's own live tick recording into
the live world room, and `sqs_baseline_conditioning` / `sqs_baseline_refit_schedule` are
fingerprinted node/Book config (`variables.yaml:625,:636`). The node is the baseline producer, and
`qmf-risk.md:444` binds the shape: *"one governed producer, published once and consumed by the
door — measurement never acts."*
→ **Node owns:** `sqs_hard_block_threshold_per_class` (recorded evidence 0.60/0.55/0.45/0.65/0.50),
`sqs_hysteresis_band` (0.05), `sqs_outlier_guard_multiple` (4-sigma), `sqs_sample_cadence`,
`sqs_baseline_conditioning`, `sqs_baseline_refit_schedule`, `sqs_staleness_horizon` with markers
`ok / not_ready / unavailable / stale / refused` — all `configurable: true`, all recorded values
evidence not constants (L38).
→ **Contradiction resolved:** SRC-03 memlog entry 118 (*"SQS formula stays open pending
re-understanding pass"*) is superseded by GAP-0043 / DEC-0153 / AD-39, which are later, ratified,
and downstream of the operator's own K-38 correction closing SQS to *Spread Quality Sensor*
(`trading-node-delta.md:96`). D-09 permanently DROPs any other expansion.

**Breakeven ratchet.** AD-34; `qmf-risk.md:415,:417`; `trading-node-notes.md:62` — **V1's only
dynamic SL/TP**, risk-non-increasing against the frozen `original_risk_distance`, delivered as
`amend_protection`, never emulated by cancel-then-place, single-sided only until amend atomicity
is verified.
→ **Node owns:** `breakeven_ratchet_trigger`, `breakeven_ratchet_offset` (`variables.yaml:713,:724`),
and the amendment idempotency threshold that suppresses tick-storm duplicate amends
(PRD row 12(d), `prd.md:673`).

**Bench rules.** `docs/scenarios/SCN-0011-qualifying-loss-bench.md` — seat state `active | benched`
(`ADMITTED` is not a state); predicate `realized_r <= -q`; **breakevens never count**; scratches
and partial losses do not count by default; a forced flat counts only if it realized a qualifying
loss; the bench counter is a **read-time fold** over the exit-record stream bounded by the binding
epoch; a fill's CT-29 record must persist before any later intent on that seat, else `stale
evidence`; next-open reset is a clocked CT-24 transition and **never** a CT-30 `resume`, with no
operator signature.
→ **Node owns:** `qualifying_loss_threshold` q (per-family, ~1R recorded evidence) and
`bench_consecutive_loss_threshold` (per-bot, 2-for-scalper recorded evidence)
(`variables.yaml:493,:504`).
→ **Trap to bind against:** in the legacy money ladder the symbol `B` is *both* the bench threshold
and a divisor in `FORM-0004`/`FORM-0006` — *"Changing the how-many-losses-before-bench number
therefore silently resizes every seat"* (`10-dpr-prs-bench-dig.md:100,:188-190`). The current
registry already separates them; the spine must keep them as two independent keys and never
re-couple them.

**Same-tick priority.** `docs/scenarios/SCN-0010-risk-boundary-conflicts.md:23`; AD-37 — one
arbitration point per `(VenueId, account)` stream; class order highest-first: (0) operator action,
(1) protection actions (kill-switch class), (2) BMS/Book forced flats (kill-line stand-down,
`window_forced_flat`, hold-time or boundary force-flat), (3) fast invalidation, (4) ordinary bot
exits and protection amendments. Collapse rule: the same mechanical command collapses to one
emission, losers journal as suppressed. Conflict rule: composing effects both execute, and *"a
higher-ranked action may never reduce the protection a lower-ranked action would have delivered."*
→ **Node owns:** the `control_rank_table` values, BMS-declared, one table per stream, total order,
uniqueness checked at admission Layer 1 (`variables.yaml:757`; `ct-27:19`).

**KSA levels GREEN..BLACK, escalate-only, A1 human de-escalation — NOT in `docs/`** [verified by A].
`grep -rn "GREEN\|BLACK" docs/` returns **zero hits**. The five levels, the four trigger classes
(`scheduled_news, black_swan, connectivity, unknown_state`) and law L8 are **GitBook baseline**
(`workroom/reference/05-trading-node-primer.md:309`; `work/gitbook-baseline.md:257-262`). `docs/`
carries only the *posture*: `docs/contracts/ct-27-bms-definition.yaml:26` — *"KSA policy posture is
declared contract surface, but the KSA trigger→level→effect matrix and the node's severity-policy
values are node authority and stay OUT of this template."* Under L37 the GitBook **is**
authoritative for live-trading content, so the levels are binding baseline — but they have never
been re-ratified into `docs/`, and this sitting must adopt them explicitly.
The **matrix is `GAP-0015`, genuinely open**, with the primer saying outright *"do not invent
target state here"*; the legacy donor matrix (GREEN normal / YELLOW caution / ORANGE block new
entries / RED protective emergency posture / BLACK force-close-shutdown) is PE-5 evidence needing
ratification (`recovery-lineage-addendum.md:142`). `TIGHTEN` / half-size-through-bad-conditions is
**DEAD** (DEC-0019; `correlate.md:173`).
→ **Node owns:** the matrix. Bind the *shape* now — level enum fixed and non-configurable,
escalate-only automatic transitions, A1 human-only de-escalation, effect-per-level a
`configurable: true` UI-editable node severity policy — and let a **blank effect block live money**
(L38 / FR-035, `prd.md:304-306`). That converts the one dangerous unknown into the corpus's own
fail-closed mechanism instead of an architecture blocker.

**L39 exit preservation.** `docs/constitution.md:94`: *"no control action, of any authority, at any
scope, may block a risk-reducing act or the recording of evidence; the blocking half of any
control is entries only, and no control kind whose effect is a blanket command-pipe block may be
minted."* Note the QA finding: `check_exit_preservation` shipped **with no caller** (QMX-F001,
critical, CONFIRMED, fixed FC-01) — the node must keep it wired on the live path and prove it.

**DEC-0049 detector-pause scoping — ratified verbatim** (`_docwork/ledger.yaml:458-463`): automatic
detectors may act *"only through the existing entry-blocking control vocabulary, scoped to the
narrowest affected subject — instrument, currency cohort, Book, venue/broker, or system-wide —
never wider … and never through any act on positions or exits (the L39 exit-preservation invariant
holds). The response posture is operator-configurable and UI-editable per L38: inform when the
operator is reachable, pause when not."*
→ **Node owns:** the inform-vs-pause posture setting and the detector→subject scope resolution.

### Operator question — Q-QA6 · ASSUMPTION (cheap veto)

> The daily "quiet band" where the node stops opening new trades has two different widths written
> down in your own history — about one hour in one place, about three hours in another — and the
> corpus deliberately never merged them. **Recommended: start at the wider ~3 hours around the
> daily rollover**, because the corpus's rule everywhere else is fail-closed and it is far cheaper
> to open the window later than to explain a bad fill in thin rollover liquidity. Example: no new
> entries roughly 4pm–7pm New York; exits, protection and data recording keep running throughout.
> Alternatives: (a) ~1 hour, matching the tighter recorded row; (b) leave it blank until you've
> watched a week of live spreads — but a blank value blocks live money by design.

---

## QA7 — Paper mode

### Verdict: **RATIFIED-ANSWER**, with the K-27/AD-35 tension **reconciled, not contradictory**

### What is settled

`docs/decisions/ADR-0009-book-level-paper-mode.md:32`, verbatim: *"Paper is a Book-level mode …
expressed as a dated change of the Book's execution binding that mints a new binding epoch, never
a new Book. Book modes are `LIVE | PAPER`; `BENCHED` is a bot-seat word only … every trigger kind
declares `routes-to-paper | blocks-paper` (market-risk controls block paper too; capital and
authority controls route to paper) … One active paper-routing target per live binding; the
per-intent `execution_target` is resolved once at intent mint … Paper money is frozen evidence: a
configurable UI-editable starting balance, never hand-adjusted; a reset mints an operator-signed
paper epoch record; paper P&L never becomes Treasury cash and never buys a seat. Return to live is
automatic only for clocked mechanical causes; anything touching real money takes an operator
signature; paper performance never authorizes a return."*

Supporting: `docs/contracts/ct-24-book-mode.yaml` (mode is a read-time fold over an append-only
transition stream, never a stored field; a clocked mechanical clear mints a CT-24 transition and
**never** a CT-30 `resume`); `docs/scenarios/SCN-0006-book-paper-transition.md:21` (three
vocabularies never interchanged — Book mode, seat state, binding state; a mode field written with a
seat word is `invalid input`); AD-35 (`discovery-architecture-sessions.md:86`) — **no Bot twins**.

**Family-scoped paper balance:** `registry:paper_starting_balance` — *"Book/family-scoped
money(numeraire) frozen at flip"*, `configurable: true` (`variables.yaml:735`).

**Demo accounts are `world = live`, role-scoped.** `docs/components/qmf-data.md:55`: *"account role
carrying money-reality so paper and demo runs are `world = live`"*; role enum `live | demo |
paper-validation | paper-benched | prop-firm` (`ct-21:40`). `tracker/trading-node-notes.md:50`:
demo/paper evidence is role-scoped within `world = live`.

**A silent paper outage alarms like a live one** (`ADR-0009:36`;
`docs/lenses/observability/metrics-and-alerts.md:62-75`).

### K-27 vs AD-35 — reconciled

K-27 (`trading-node-delta.md:73`, `KEEP`): *"every live account binding has a paired demo binding
for fail-mechanism fills; sensing stays on the pinned canonical live feed."* AD-35: one active
paper-routing target per live binding. These are the **same object under two names** — and
`ADR-0009:36` says so explicitly: *"a paired demo account holds its own paired BMS instance linked
by a typed pairing record."* K-27's paired demo binding **is** the paper-routing target. No conflict.

What K-27's neighbour **K-25** claimed — *"Trading paper is **only** a fail-mechanism surface"* —
**is** superseded: GAP-0041/AD-35 make paper a standing evidence state feeding alpha-decay sensing
(`_docwork/gaps.yaml:402-410`; `tracker/tickets/002-qmf-minimal-core.md:39-48` — *"paper trading is
a STANDING STATE, not a waiting room"*). And the data-layer blueprint's stronger reading — *"every
bot runs its paper twin permanently, including while it is trading live"*
(`09-data-layer-blueprint.md:67`) — is **refused** by AD-35's no-twins rule and is in any case
unratified research synthesis (`09-data-layer-blueprint.md:3`). Three readings; the corpus settles
on: **Book-level standing state, no twins, exactly one target.**

### What "paper mode on a demo account for ~2 days" needs beyond AD-35

1. **Two simultaneous cTrader connections** — demo and live are separate hosts
   (`ctrader.md:106,:108`; `dig-web-currency.md` row 10, PRIMARY: *"At most, you should create two
   connections: one for demo accounts and one for live accounts"*), each with its own heartbeat and
   its own 50/5 rps budget. `SessionTopology` declares `required_connection_count = 2`; **no code
   opens them.**
2. The CT-24 transition record + the typed paired-demo pairing record.
3. The frozen `paper_starting_balance` and the `paper_epoch_reset` treasury-boundary path.
4. The paper-stream outage alarm class, at live severity.
5. The warm-up empirical checks: `docs/lenses/ops/runbook.md:65-71` — spot-timestamp unit,
   daily-boundary measurement (which mints a venue-scoped market-hours calendar identity), bar-basis
   reconciliation, pip-formula validation, money exponent.

**Duration conflict to surface:** the ratified operator rider is *"a ~1-week warm-up/observation
period before live trading"* (`docs/lenses/ops/runbook.md:80`, DEC-0135;
`tracker/trading-node-notes.md:21`), not two days.

### Operator question — Q-QA7 · ASSUMPTION (cheap veto)

> **Recommended: keep the paper/demo run to the full week you already ratified, not two days.** The
> daily-bar boundary check needs several rollovers to measure honestly, and getting that wrong
> quietly mis-stamps every day boundary afterwards. Example: run Monday to Monday on the demo
> account, then sign off on live. Alternatives: (a) two days, accepting the daily-boundary figure
> stays unmeasured; (b) go live sooner but only on instruments whose four venue checks have already
> passed.

---

## QA8 — Data layer, live side

### Verdict: **PARTIAL** — the rooms, journals, seal and backup *primitives* are ratified and built; the live path, the backup backend and the schedule do not exist

### Ratified and built

- **Seven room-roles per world**, instantiated per world; cross-world read is a `policy rejection`;
  only the raw archive and journal are evidence-bearing; every external fact carries
  event-time / known-at / source / revision (AD-19, `docs/decisions/ADR-0016-data-rooms-splits-journal.md:41`).
- **Journals (CT-13):** N streams, one per producing component, each under its `WriterId` with
  **gapless per-`(writer, boot-epoch)` sequences** — a gap signals loss; seven event types
  `decision | order | fill | risk transition | promotion | data quality | control action`
  (`ct-13:34-49`). Implemented (`packages/qmf-data/src/qmf/data/journal.py`), with `correlation_id`
  and `display_time` excluded from identity.
- **Receive-time stamping is mandatory** because cTrader exposes no server clock
  (`ctrader.md:57-67`; `tracker/trading-node-notes.md:10`).
- **The 12-month research seal:** `registry:historical_holdout_months` = 12, configurable, no-peek,
  frozen TradingDate (`variables.yaml:225`), enforced on restored reads (`ct-14:18`). QA fix FC-06
  landed the seal on every read path.
- **License tags / Dukascopy:** DEC-0170 — *"QMX's downloaded market data is used at a personal
  level only … QMB ships and redistributes no market data"* (`_docwork/ledger.yaml:1589`).
- **Backup design:** nightly, encrypted, versioned, off-machine to an object-storage bucket, with
  **automated sample-restore tests and a periodic full-restore rehearsal**; QMF provides backup /
  restore / verify primitives, the schedule and its execution are application- and ops-owned
  (AD-20, `ADR-0016:43`; `ct-14:13-15`). `registry:backup_cadence` = nightly, ratified
  (`variables.yaml:247`). Recoverability is claimed **only** through the verify primitives, never
  from a copy's existence (`SCN-0004:29`; `packages/qmf-data/src/qmf/data/verify.py:1-5`).
- **Retention of evidence:** NFR-06 — *"evidence append-only, retained forever"* (`prd.md:561-563`).

### Named gaps — verified in code, not inferred

1. **There is no live tick/stream ingestion path anywhere.** `code-qmf-data-calendar-recorder.md:23`:
   grep for `stream|subscribe|live|spot|websocket|realtime|push` across `packages/qmf-data/src`
   returns only the JSONL append-stream journal, the `World.live` enum value, and a calendar string.
   Every ingest path is a **bounded, called, batch fetch**: `ExternalSourcePort.fetch(request)`
   returns one bounded window (`ingest.py:305`), `SourceRequest` *"issues one call and returns; it
   never schedules the next"* (`ingest.py:258`), and the seam **refuses to own a scheduler, daemon,
   process supervisor, or retry loop** — a `policy rejection` (`ingest.py:31`). The value type for a
   venue observation exists (`MarketDataContext`, `observation.py:240`) but **no live producer
   fills it**. This is the single largest thing the node must build.
2. **No backup backend is chosen.** `ObjectStorage` is a Protocol with `put`/`get` and
   *"Object-key layout, provider selection, and credentials stay outside QMF"* (`backup.py:120-121`).
   Encryption is required (`ENCRYPTION_REQUIRED = True`, `backup.py:75`) through an injected
   `PayloadCipher` — *"the crypto dependency is node/ops-owned"*. `COMP-OBJECT-STORAGE`
   (`docs/components/object-storage.md:17,:39`) defers provider, key layout, credential and
   encryption-key custody, and the numeric objectives to this sitting.
3. **No restore command and no scheduler.** `OffMachineCycle.run_once` exists as one callable
   `CT-26 → CT-14 → sample-restore (+ optional full-restore rehearsal)` cycle with *no threads,
   cron, or daemon*; `own_schedule()` and `start_daemon()` **always return typed refusals**
   (`cycle.py:307-315`); `refuse_numeric_rpo_rto` refuses to hold the numbers.
4. **The numbers are null**: `backup_recovery_point_objective`, `backup_recovery_time_objective`,
   `backup_retention_period`, `restore_verification_cadence` — all `null`, all node/ops sitting
   (`variables.yaml:258,:270,:282,:294`; `ct-14:37`).
5. **The calendar recorder is unwired and on the wrong machine.** `recorder/` is a standalone,
   stdlib-only FairEconomy/ForexFactory weekly-calendar fetcher, explicitly *"No project imports …
   do not couple anything here to platform code"* (`recorder/README.md:5`), currently driven by a
   **Windows Scheduled Task** (`QMX-Calendar-Recorder`, daily 06:00, repeat 12h). On the VPS it must
   be re-homed onto the node's scheduler through the built `CalendarFeedAdapter`
   (`packages/qmf-data/src/qmf/data/calendar_feed.py`), which already enforces provider-native
   `(source, id, revision)` identity, **verbatim impact labels** (`refuse_minted_severity_scale`),
   a CT-13 `data quality` journal event per import, and fail-closed degradation with **no live skip
   button**.
6. **History bootstrap.** The Dukascopy adapter is built and download-once, decoding bi5 through an
   injected transport, **refusing complete-corpus/unbounded downloads** and capping a window at one
   day per call (`dukascopy.py:571-576`). FR-042's ship-no-corpus gate and deep-history evidence row
   15 (`prd.md:676`: TrueFX + HistData as companions, Databento carries no spot FX, venue-only
   backfill rate-capped into unviability) mean the node must **schedule and checkpoint a long,
   resumable bootstrap** — which nothing today does.

### News-calendar provider (DEC-0119): mechanics ratified, **provider NOT decided**

DEC-0119 (`_docwork/ledger.yaml:1118`) ratifies the *door*: seven journal event types, the seal, the
news-calendar recorder keeping provider-native identity, tick sources separately identified. The
**provider selection and the legal archiving posture remain open operator items** —
`docs/components/calendar-feed.md:39`; `ADR-0016:49` (*"remains an open operator item recorded
rather than resolved"*); and in code `LEGAL_ARCHIVING_POSTURE = "open-operator-item"`
(`calendar_feed.py:84`). PRD row 14 supplies the evidence: Forex Factory free weekly JSON as
primary (rate-limited ~2 downloads per 5 min), FMP / Trading Economics / FXStreet as
impact-carrying fallbacks, **EODHD disqualified (no impact field)**, scraping rejected
(`prd.md:675`).

### What the spine should bind

The node owns: a live venue market-data producer feeding CT-10 through the live world room under
its own `WriterId`; the scheduler that drives `run_once`, the calendar refresh, and the history
bootstrap; a concrete `ObjectStorage` backend and `PayloadCipher` with named key custody; and the
four null numbers. Evidence retention stays *forever* (NFR-06); **backup** retention depth is a
separate, bounded number.

### Operator question — Q-QA8a · ASSUMPTION (cheap veto)

> **Recommended: pin Forex Factory's free weekly calendar file as the news source**, because it is
> already what your recorder downloads today, it is free, and it carries the impact label the
> blackout window needs. Record the legal posture the same way you did for Dukascopy: personal use,
> never redistributed. Alternatives: (a) add a paid backup source (Trading Economics or FMP) so a
> bad week at one provider doesn't leave you fail-closed; (b) run two sources and let the wider
> blackout win.

### Operator question — Q-QA8b · ASSUMPTION (cheap veto)

> **Recommended: a small restore test runs automatically every night right after the backup, and
> once a quarter the node restores the whole thing to a scratch folder and checks it.** An untested
> backup is a rumour, and nightly is free because the backup already runs then. Example: every
> night it pulls back one day's file and verifies it; on the first Sunday of each quarter it pulls
> back everything. Alternatives: (a) weekly sample plus a yearly full rehearsal; (b) sample only,
> no full rehearsal — cheaper, but you'd never have proven a real recovery.

### Operator question — Q-QA8c · ASSUMPTION (cheap veto)

> **Recommended: Backblaze B2 as the backup bucket, with the encryption key held on the VPS in the
> same protected store as the broker login.** It is the cheapest of the class already named in your
> own notes (~$1–5/month) and needs no extra account plumbing. Alternatives: (a) Cloudflare R2 (no
> egress fees, useful if you ever restore often); (b) a plain second disk somewhere you control, if
> you'd rather no third party hold the file at all.

---

## QA9 — Startup/recovery doctrine, drift, stand-down, shadow lane, evidence tiers, notifications

### Verdict: **PARTIAL** — several parts are already ratified elsewhere; the rest is `[MINED]` doctrine this sitting ratifies by adoption

### Already ratified elsewhere (cite and reuse — do not re-mint)

- **Verdict vocabulary is FOUR terms, not three.** `docs/contracts/ct-20-venue-event.yaml:26,:44`:
  `reconciled | drift | unknown | out-of-lookback` — *"the fourth term added so that 'I cannot see
  that far back' is NEVER read as 'the position closed'."* The PRD's `[MINED]` line names three
  (`prd.md:406-411`). **The corpus wins**; the node carries four.
- **"A crash never resets safety counters, because there are no safety counters — only journal
  projections"** (`prd.md:396-405`) is not new: it **is** the ratified fold contract, stated once
  for order state, structure lifecycle, Book mode, standing intent, bench count and seat state
  (`docs/components/qmf-risk.md:435`; `ct-24:20`; `ct-30:22`).
- **Recovered fills commit before healthy** (`ctrader.md:144`, FM-1).
- **Startup reconciliation gates the command pipe only; sensing flows from boot**
  (`ct-20:26`; `tracker/trading-node-notes.md:32`).
- **Standing intents are restart-proof, re-decided not retried, never time-expiring**
  (`ct-30:22`).
- **An alert is evidence, not permission** — `docs/lenses/observability/metrics-and-alerts.md:79`
  (DEC-0041): *"It cannot promote an artifact, authorize an order, flatten exposure, invoke an
  exit, change Book mode, rotate a secret, restore over data, or command an external provider."*
  This is the two-plane rule's hard half and it binds now.
- **Incident authority** — `docs/lenses/ops/incident-playbook.md:20`: no agent, detector, alert,
  adapter, external acknowledgement or incident condition grants permission to trade, flatten,
  change Book mode, rotate secrets, restore over data, or bypass a contract.
- **A paper-stream outage is the same alarm class as a live outage**
  (`metrics-and-alerts.md:62-75`).
- **GitBook start sequence** (RECONFIRM-grade ancestor of the mined ordering,
  `work/gitbook-baseline.md:320-323`): ledger reconciles to broker → KSA state is known → labeler
  versions match active certificates → adapter binding and connection confirmed.

### This sitting ratifies by adoption — tag each of these `ASSUMPTION` in the memlog

- **A9-1 · Cold-start preflight + fixed per-Book startup order.** `prd.md:396-405` — a deterministic
  preflight gate *before any state mutation* (host/disk/network/pinned-version checks, fail-closed
  with a typed failure id), then per Book: connect → reconnect gap recovery (fetch deals/positions
  since the last-seen execution event, **commit recovered fills before reporting healthy**) →
  missed-rollover catch-up (boundary equity reconstructed from journals; the sweep journaled as a
  correction-style append) → protection-state projection (breakers, budgets, exposure rebuilt from
  journals) → readiness gates → the sequencer accepts intents.
- **A9-2 · Explained drift.** `prd.md:406-411` — broker-vs-virtual divergence decomposes into
  journaled components (swept-but-unwithdrawn cash, re-seed remnants, open unrealized P&L); **only
  the residual is drift**; unexplained live drift halts trading and **restart is not permission to
  resume — a fresh reconciliation review is**; the paper/demo binding is excluded from the live
  drift check. Recovery evidence R-14 and the GitBook agree, and add `reconciliation_epsilon = 0`
  with `operator_review: true` — *"operator review is mandatory before non-zero use"*
  (`05-trading-node-primer.md:294`).
- **A9-3 · Stand-down is an alive state.** `prd.md:418-422` — past a crash-loop threshold the
  process boots into stand-down: sequencers refuse-and-journal, adapter connections quiesce and
  drain, **the operator-powers surface keeps serving** so resurrection stays reachable. Paired rule
  (K-41/A5): a protection transition counts as enforced **only after** the account's connections
  have quiesced and drained.
- **A9-4 · Shadow lane.** `prd.md:424-431` — candidate labeler/model versions run as near-real-time
  replay over the captured canonical feed, off the hot path, to their own manifest prefix, never to
  live consumers, evaluated over **one full affected-Book cycle** (the one ratified-interim number,
  ENH-0005, `work/gitbook-baseline.md:159`); promotion is ratification → version bump →
  re-certification; a recovered or pre-trained model carries **no authority** without fresh
  ratification; training is an offline job that may seed its RNG provided the seed is recorded,
  while the **no-ambient-randomness invariant binds the live runtime** (OR-11, PARTIAL-hybrid,
  `rulings-corpus-verdicts.md:333-364`).
- **A9-5 · Always-on evidence tier.** `prd.md:432-441` — a placement and authority boundary:
  explicitly **not a database server and not a second writer**; the hot path never blocks on it
  (only disk physics fail-closes trading); sync is one-way, watermarked, idempotent, resumable,
  under **verify-before-purge** (the hot side purges only what the evidence side has durably
  persisted *and* content-verified); recovery re-requests carry watermarks only, never payload
  backward; the only reverse crossing is the click-gated promotion pull.
- **A9-6 · Notification allow-list + two-plane rule.** `prd.md:119-127` — notifications fire only
  on a closed ratified allow-list: **sweep, re-seed, refund, kill-switch/KSA events, supervision
  fail-closed**; everything else is console evidence, never a push. Authoritative records and
  notification delivery are separate layers with separate policies — *"losing a notification never
  erases the underlying evidence, and the notification channel is never a permission path back into
  live trading."* K-48 agrees verbatim and adds that **refund is dormant in V1**
  (`work/wiki-inventory.md:146`).

### Genuinely open

Crash-loop thresholds **K** and **T** are explicitly *unset* (K-08, `trading-node-delta.md:42`;
open-frontier item 11). Notification delivery mechanics — channels, retries, dedupe, quiet hours,
credentials — are `GAP-0002`, deferred by the PRD to the node/terminal phases.

### Operator question — Q-QA9a · ASSUMPTION (cheap veto)

> If the node keeps crashing and restarting, it should stop trying at some point and sit still with
> the controls still answering. **Recommended: three crashes inside sixty seconds puts it into
> stand-down** — it matches the setting your own factory server already runs under, so there's one
> number to remember. Example: it crashes at 3:00:05, 3:00:20 and 3:00:41 — it stops restarting,
> journals why, drains the broker connections, and waits for you. Alternatives: (a) five crashes in
> five minutes, more forgiving of a slow flap; (b) never stop restarting — rejected, because a
> reconnect loop can churn the broker connection.

### Operator question — Q-QA9b · ASSUMPTION (cheap veto)

> **Recommended: one notification channel to start — a push to your phone — carrying only the five
> allowed event kinds, with no quiet hours on any of them.** The list is already closed by ruling,
> and a second channel is easy to add later. Example: a kill-switch escalation at 4am pushes; a
> normal blocked trade does not. Alternatives: (a) email as well, for a written trail; (b) defer
> the channel decision to the desktop-app phase, as the PRD originally allowed.

---

## QA10 — MIS in V1

### Verdict: **PARTIAL** — seam only, and the corpus names the minimum

### What is settled

- **MIS is out of QMF V1.** `docs/decisions/ADR-0011-deferred-consumer-products.md:30`: *"Backtesting,
  the future modular sandbox, the visual Simulator, **MIS**, the QML Bot library, and agentic
  runtime organs are outside QMF V1."* Glossary: *"MIS: A future trading-node analytical or machine-
  learning ensemble consumer. MIS is not a QMF V1 library and is not qmf-indicators."*
- **MIS has no authority, ever.** Glossary kill-switch entry and `qmf-risk.md:429`: the kill switch
  is *"sensor-fed (MIS and SQS are inputs never authorities)."* GitBook L6: *"MIS never sizes,
  blocks, or trades."* AD-39: *"sensor computes, transport carries, Book door decides."* D-09
  permanently DROPs SQS-as-execution-authority.
- **Compute-once fan-out** is GitBook baseline: each labeler/version/param/pair/resolution computed
  **once** and fanned out (`05-trading-node-primer.md:305`); failure is conservative (degraded field
  + `degraded_sensors`; `sqs_hard_block` forces a door refusal; a dead `feed_state` blocks new
  entries).
- **Naming is disambiguated by ruling.** The deferred consumer product "MIS" (ADR-0011) and the
  node's own **MIS-Live** labeler layer are distinct things — D1, `correlate.md:49`;
  `mine-node.md:255-262`; `prd.md:85` vs `prd.md:374-379`.
- **ML training runs ~quarterly in cloud sandboxes** (`tracker/map.md:50`); training location
  local-GPU-vs-cloud is unresolved (`mine-node.md:253`).
- **Shadow rollout** default is one full affected-Book cycle (ENH-0005) — and the shadow lane is
  **ratified concept only, never built** (`mine-node.md`, Story 3.9 backlog).
- **CT-MIS-01 is an OLD contract id.** `correlate.md:168` warns that the old namespaces
  (`CT-BMS-*/CT-BOOK-*/CT-MIS-*/CT-SYNC-*`) **do not line up** with current numbering and must never
  be cited as current. Its snapshot *shape* is evidence; its identifier is not adoptable.

### Open

**MIS consumer boundary C-01 is `REOPEN`**: Book + KSA only (old Story 3.2, which forbids direct
bot delivery) versus manifest-bounded bot consumers (wiki/AD-19) —
`tracker/trading-node-notes.md:26`; `trading-node-delta.md:153`. Also open: the labeler catalog's
trained member (`regime_classifier_v1` carries a literal `"..._placeholder"` model family and an
unresolved training location) and the recovered models (Kronos, HMM, BOCPD, MS-GARCH) which carry
`NO_CURRENT_AUTHORITY`.

### The minimum MIS seam for V1 — what the spine should bind

A **compute-once, versioned, immutable per-instant signal snapshot**, computed in-process and
dispatched **synchronously** (no queue, no bus, no RPC, no cross-machine hop — `mine-node.md:208-253`)
to a closed consumer set, carrying:
(a) the SQS score and hard-block flag per instrument;
(b) `feed_state` (live / degraded / dead) on the pinned canonical live feed — K-39: *"MIS uses one
pinned live-account connection as canonical sensing feed; outage fails closed until that feed
gap-replays"*, with **no silent failover** (D-10);
(c) the `degraded_sensors` list;
(d) the labeler version stamp set (so a snapshot names exactly what produced it);
(e) explicit readiness markers `ok | not_ready | unavailable | stale | refused`
(`registry:sqs_staleness_horizon`, `variables.yaml:647`) — **never a silent default**.
Every V1 labeler is rule-based, pure and deterministic; **no fitted or trained model is bound in
V1**. That is enough for SQS to reach the Book door and for the kill switch to be sensor-fed,
without a single line of machine learning — which is exactly what "seam only" means here.

### Operator question — Q-QA10 · ASSUMPTION (cheap veto)

> **Recommended: in V1 these market-condition readings go only to the Book's door and to the kill
> switch — individual bots never read them directly.** A bot that reads a market-condition signal
> and acts on it becomes a second, unaccountable risk system, and widening this later is easy while
> narrowing it is not. Example: the spread-quality reading blocks an entry at the Book door; the bot
> just sees its trade refused, with the reason journaled. Alternative: let a bot declare in writing
> which readings it consumes and deliver only those.

---

## QA11 — Logging, monitoring, DevOps

### Verdict: **PARTIAL** — conventions bind now, every number and every deployment artifact is node-owned

### Ratified (binds now)

- **AD-14** (`docs/decisions/ADR-0014-performance-observability-concurrency.md:39`): `correlation_id`
  under that exact field name propagated across every package boundary; every component exposes a
  no-arg `health()`; *"Logs are not journals: log text is display, journals and every evidence
  stream are evidence encoded per DEC-0106. **Emitted signals must be exportable to
  Prometheus-class monitoring stacks.**"*
- **Encoding split** (`docs/lenses/observability/logging-spec.md:16`): operator/diagnostic log text
  is UTC ISO-8601 with an explicit `Z`; journals are int64 UTC nanoseconds plus writer plus
  sequence. *"The operator log-level taxonomy, logger names, file paths, and query system belong to
  the full monitoring design at the node/ops sitting."* `:66`: *"The operator diagnostic log-level
  enum is not ratified."*
- **Zero-authority external plane** (DEC-0112, DEC-0041; NFR-10 `prd.md:573-586`): any
  Prometheus/Grafana-class plane consumes exported evidence and holds no authority; K-49 agrees.
- **Nothing else in observability is ratified.** `metrics-and-alerts.md:16`: *"QMF V1 has no
  ratified metrics schema, aggregation window, dashboard, alert threshold, severity tier,
  notification destination, paging route, or automatic remediation."* Alert-fatigue policy and log
  retention have **no** corpus entry at all; the nearest binding thing is the QA9 notification
  allow-list plus *"a push alert path with no on-call rotation"* (`metrics-and-alerts.md:20`).
- **NFR-10 one canonical checkout** (operator-ratified 2026-08-21): works out of the box (`uv add`,
  no DB server, **no Docker for QMB**); a single person can deploy, monitor and repair;
  `[MINED]` — *"install, start, stop, back up, recover from one canonical checkout — never hunt
  across folders or reconstruct Git state."* Serve-both-layers: the same monitoring/evaluation
  substrate later serves QMA — never two stacks.
- **NFR-11 failure register** (`conventions/failure-register.md:1-49`): every designed failure mode
  ships a `FAILURES.md` entry with failure class, detection, auto-recovery/retry, visible degraded
  state, notification tier, product-user affordance. This binds every node failure mode the sitting
  designs.
- **Runbook has no start/stop/deploy** (`docs/lenses/ops/runbook.md:16,:26-34`): *"QMF V1 is
  design-only and has no ratified start, stop, restart, deploy, migration, rollback, or
  live-connection command"*; deployment topology is a node/ops decision.
- **Time discipline — shape ratified, numbers not** (`runbook.md:107-116`, 8 rows, all "Binds:
  Node/ops sitting"): the VPS OS clock runs chrony with ≥4 sources (iburst, makestep boot-only) and
  is the sole stamper — *"A travelling Windows laptop is declared unfit to stamp authoritative
  evidence"*; no trading before `chronyc waitsync` confirms sync; slew-only while live, a step only
  with the node stopped and observable; **drift bands with typed refusals** (ok / warn /
  no-new-entry / halt — sized to ~1s decisions), exceeding a band being a typed refusal + journal
  record + node state change, never silent; gap records for every unsynchronized, stepped or paused
  window including a VPS live-migration; Linux RTC in UTC, system tz UTC, `TZ=UTC`; `WriterId`
  stamped because the node and the tick recorder share the VPS; the prop-firm day boundary in its
  stated tz via an account-scoped day-boundary calendar.
  **The numbers `ok ≤10ms / warn ≥25ms / no-new-entry ≥100ms / halt ≥250ms` appear ONLY in the
  planning artifact `time-audit-devops.md:9` [verified by A] — RECONFIRM-grade, absent from the
  ratified runbook table.**

### Repo facts this sitting must rule against [verified by A]

- **CI is 100% Linux today**, across all four jobs: `.github/workflows/skylos.yml:36` and
  `.github/workflows/battery.yml:35,:57,:85` all `runs-on: ubuntu-latest`. There is **no
  `windows-latest` anywhere**.
- **The type gate renders a Windows view on that Linux runner**: `pyproject.toml:307-312`,
  `[tool.pyright] pythonPlatform = "Windows"` — *"Pin the analysis platform to the ratified tier-1
  OS … pinning makes the battery CI job on a Linux runner render the same byte-identical verdict the
  tier-1 machine renders."*
- **Ubuntu is ratified tier-1 but unproven**: `ADR-0012:34` names Windows 11 x86-64 and Ubuntu LTS
  x86-64 as tier-1; `:48` concedes *"the Ubuntu tier-1 target is declared and not yet proven"*; and
  `pyproject.toml:503-506` defers the clean-install smoke *"once a remote exists."* **A remote now
  exists** (`origin` = github.com/MubarakHimself/QMX) — the deferral condition is stale.
- **Zero deployment artifacts exist**: no Dockerfile, compose file, `.service` unit, terraform,
  ansible, cloud-init, Procfile or install.sh anywhere in the worktree. The only `systemd` hits are
  comments in the factory's own `adws/` describing `sdl-engine.service`; **no unit file is checked
  in**. `systemd-creds` appears only in docs and planning, never in code.
- **No logging framework, no metrics exporter, no HTTP health endpoint** exists in product code;
  typed in-process `health()` methods do exist (qmf-venue connection, qmf-indicators streaming, qmb
  orchestrator log).
- **The libraries ban background work**: `asyncio`/`threading`/`sched`/`multiprocessing` are refused
  by conformance tests, and `qmf-data` returns typed refusals from `own_schedule()` /
  `start_daemon()`. The node must own all concurrency (AD-15, NFR-09).
- **Skylos already gates deployment artifacts.** `dig-web-currency.md` row 7 (PRIMARY, Skylos
  README): Skylos scans Dockerfiles, compose files, **systemd `*.service` units**, k8s bundles and
  CI workflows — flagging root edge services, mutable `ExecStart` paths, missing sandboxing, broad
  capabilities and literal `ENV` secrets — **but not Terraform**. Since the existing gate scans the
  repo root and subtracts by name (`pyproject.toml:333-352`), a committed node unit file is gated
  the moment it lands, for free.

### What this sitting must rule

Supervision shape; the CI lane for the node's actual OS; the drift-band numbers; log level
taxonomy, file paths, rotation and retention; the metrics endpoint and its binding; rollback; VPS
hardening; and the secrets-provisioning step. Recovery evidence for the hardening set is
RECONFIRM-grade only: `Restart=on-failure`, `RestartSec=5s`,
`StartLimitBurst=3`/`StartLimitIntervalSec=60`, `DynamicUser=true`, `NoNewPrivileges=true`,
`PrivateTmp=true`, `ProtectSystem=full`, secrets via `systemd-creds` only (`mine-node.md:160-204`;
K-51, K-53). Hardened OS-level confinement for bot isolation stays a **named deferred dependency;
V1 does not wait on it** (`epics.md:2622-2625`).

### Operator question — Q-QA11a · ASSUMPTION (cheap veto)

> **Recommended: the node runs as an ordinary Linux service on the VPS, not inside a container.**
> Your rules already say no database server and no container requirement, and running as a plain
> service is what lets the machine hand the node its broker password at start-up without you
> re-solving that problem inside a container. Example: `systemctl restart qmx-node` and it comes
> back with credentials already unlocked. Alternatives: (a) a container for exact reproducibility,
> paying the credential-handling cost; (b) both — a container for the data jobs, a plain service for
> trading.

### Operator question — Q-QA11b · ASSUMPTION (cheap veto)

> **Recommended: add a CI job that actually installs and starts the node on Ubuntu, the OS the VPS
> runs.** Today every check runs on Linux but type-checks a *Windows* view of the code and never
> once installs it cleanly on Linux — so the machine that will hold your money is the least-tested
> configuration. Alternatives: (a) leave it and rely on the VPS itself as the first Linux test; (b)
> flip the primary target to Linux entirely and test Windows only for the desktop app later.

### Operator question — Q-QA11c · ASSUMPTION (cheap veto)

> **Recommended: adopt the clock-drift limits already written in your DevOps notes — fine up to
> 10ms, warn at 25ms, stop opening new trades at 100ms, halt at 250ms — as editable settings, not
> fixed constants.** They are sized for the roughly one-second decisions the node makes, and they
> were written for exactly this purpose. Example: the VPS clock drifts to 120ms, so the node quietly
> stops taking new entries and journals why, while exits keep working. Alternatives: (a) tighter
> bands if you later co-locate near the broker; (b) leave them blank and set them after a week of
> measurement — but blank means no protection in the meantime.

---

## QA12 — Doors for later phases: the desktop app and the agentic seams

### Verdict: **PARTIAL** — the *constraints* on the door are ratified; the *transport shape* is open

### What is settled

**The console spine is `[MINED]`, but its anti-goals already constrain the node.** `prd.md:449-500`:
UI-only, never a second system of record; business authority, persistence and command validation
stay server-side; the desktop app holds no trading secrets; **exactly two channels — an evidence
read channel and a powers action channel** (resurrection, ratification/promotion, review actions).
Anti-goals verbatim: no direct manual-trading surface; **no generic LIVE/PAPER toggle**; no single
global health indicator hiding independent failure domains; no stale evidence authorizing an
action; no editable setting without registry-backed configurability; no optimistic command success
without server validation and evidence; no Prometheus/Grafana clone; no assumption a future venue
is recoloured forex. **State independence**: safety, execution readiness, connection,
reconciliation, data freshness, lifecycle and sync are independent states that never collapse into
one health colour, and *"requested protection state displays separately from enforcement
completion."* Settings live in three scopes (system settings / secrets & bindings; component
settings; instance values), with Book↔account bindings console-configured, mutable, journaled, in
system scope.

**These constrain the node's door now, even though the app is Phase 3:** the node must expose a
read surface that carries **provenance and freshness per state** (never one blended health value)
and a powers surface that **re-runs every precondition server-side at click time** and lands
accept/refuse in the journal.

**The door shape is ratified for QMB and is the template.** DEC-0159 (`_docwork/ledger.yaml:1491`):
every capability exists once in the library as a pure function; doors are thin hand-written
wrappers carrying only adaptation logic; **CLI first, Python API, MCP later**; door parity enforced
by a tier-2 contract test asserting identical function surface and semantics across doors; *"the UI
backend consumes the Python API in-process; MCP is a sibling door over the same library (never
stacked over HTTP), localhost-bound by default."* In code: the API door is a thin in-process
re-export with HTTP modules **forbidden by test**, the MCP door is an *unshipped* localhost sibling,
and the shipped door is the click CLI (`code-qmb-host.md`; `qmb/tests/test_api_door.py:22-49`).

**Powers-API precedent (RECONFIRM-grade, recovery layer, needs fresh ratification).** K-03/K-50:
the powers surface lives **inside** the node process; *"Console commands go to Trading Powers API;
stale Backend evidence cannot authorize; all click-time preconditions rerun server-side"*
(`trading-node-delta.md:37,:114`). R-02/F-02: RPC over HTTP/JSON on a trusted local channel; V1
auth = loopback plus operator OS identity, or SSH-tunnelled localhost bound to operator identity
(`work/bmad-supplement.md:56`). The three named powers are **resurrection (A1 de-escalation),
periodic (Sunday) review, promotion-pull**; only `ratify_registry_value` was ever proven
(`work/bmad-supplement.md:64`). The powers surface **stays reachable in fail-closed stand-down**
(`work/wiki-inventory.md:149`).

**The agentic phrase, corrected [verified by A].** "Veins not organs" does not appear in the corpus.
The actual operator line is `tracker/map.md:38`: *"Agentic system: HANDS OFF for Claude sessions —
~5 research papers to analyze first; **'don't build organs; the veins only.'** Allowed foundational
organs: bot schema, data management."* Echoed at `_docwork/ledger.yaml:862`: *"The current blueprint
builds reusable veins and stable contracts before agentic organs."*

**Two competing egress stances are on record, unreconciled.** `prd.md:502-513` (`[MINED]`, track
input): *"an earlier ruling set the **agentic data-egress boundary as pull-only access to curated
datasets, no live-service surfaces exposed to agents at all** — a harder governance stance to weigh
vs current typed-doors posture."* Against that: DEC-0159's MCP door as a first-class sibling. And
`work/wiki-inventory.md:317` DROPs *"agentic APIs/MCP"* from the node's do-not-recover list. QMA is
research; ideation has not begun; the old agentic requirements were scrapped.

### What remains

The node's API door transport — Python API only, a local HTTP/JSON endpoint, a Unix socket, or MCP
— is **not ruled anywhere**. The node is outside QMF V1 documentation scope by definition
(glossary; DEC-0142).

### What the spine should bind

Copy DEC-0159's shape verbatim onto the node: one library, pure functions; thin doors; tier-2 door
parity test; the future desktop backend consumes the Python API in-process where co-located, and
over the powers channel where not. Bind the constraints that *are* ratified: no LIVE/PAPER toggle,
independent states, click-time server-side revalidation, requested-vs-enforced shown apart, no
stale evidence authorizing, powers reachable in stand-down.

### Operator question — Q-QA12 · ASSUMPTION (cheap veto)

> **Recommended: the node offers three ways in — a Python surface, a typed command on the server,
> and a small local-only web endpoint the future desktop app talks to over an SSH tunnel — and
> nothing an AI agent can reach.** Your own notes put agent access on the do-not-build list for now,
> and a local-only endpoint keeps the node invisible from the open internet. Example: from your
> laptop you open an SSH tunnel and the desktop app then talks to the node as if it were local.
> Alternatives: (a) skip the web endpoint entirely and drive everything over SSH commands until the
> desktop app actually exists; (b) add an agent-facing door now.

---

## QA13 — QA standard carried forward

### Verdict: **RATIFIED-ANSWER for the battery; PARTIAL on the live-milestone gate**

### Ratified / established (repo-verified)

- **Independent requirements-first tests in a `qa/` tree**: `qa/run_qa_verify.py` driven by
  `poe qa-verify` (`pyproject.toml:461`); the trace lives at `qa/_trace/`.
- **Mutation testing on the money path, nightly**: `mutmut==3.3.0` over `qmf-core` `exact.py` +
  `chrono.py`, kill-rate floor **68%** (OR-10b, from the `2c8d495` baseline 249 killed / 117
  survived = 68.03%), Linux-only, cron `17 2 * * *`, fail-closed if zero mutants are classified
  (`.github/workflows/battery.yml:9,:20-23,:80-153`).
- **The permanent CI battery**: Skylos `4.33.2`, free tier, `--no-upload`, scanning the repo root
  and subtracting by name, with hard-zero buckets for critical / high / security / reliability /
  secrets / dependency-vulnerabilities / ai-defects, plus two ratchets — `max_quality = 4084`,
  `max_dead_code = 80`, "never worse than today, ratchet down only"
  (`pyproject.toml:402-450`); a vulture dead-code ratchet at min-confidence 80 against a committed
  baseline; and `poe check` = `fmt-check, lint, types, test, cov-report, test-tools,
  money-path-scan, ambient-scan, mock-data-scan, secret-scan` (`pyproject.toml:486-494`).
- **The four tier-1 static scanners** (NFR-02, `prd.md:544-550`): money-path float scanner,
  ambient-nondeterminism scanner (forbidding `datetime.now/utcnow`, `time.time/monotonic/
  perf_counter`, `random.*`, `secrets.*`, `np.random` below the composition root), mock-data
  scanner, secret scanner.
- **Coverage**: floor 80% per package, 100% branch on the CT-01/CT-02 modules
  (`ADR-0012:38`; `variables.yaml:167`).
- **Three tiers**: `poe check` per work unit; `poe check-integration` on landing to integration;
  `poe check-release` on ship (`ADR-0012:40`).
- **NFR-11 failure register**, per package, six fields (`conventions/failure-register.md`).
- **Final state**: all 35 fix cards done and PROVEN; `poe check` fully green (3,932 passed, 86.86%
  coverage, all four scanners clean); QA Battery + Skylos green at `e874256`
  (`FINAL-REPORT.md:3-6,:48-74,:102-107`).

### The live-milestone gate — PARTIAL, and stricter than the question assumes

There is **no ratified paper-performance gate, and one is forbidden.**
`docs/scenarios/SCN-0007-human-promotion.md:21`: three-layer admission — registration linters, a
**technical demo/paper shakedown**, one operator signature — *"with **no trial period, probation
window, or paper-performance gate** and no paper role permitted to gate live money."*
`ADR-0008:32` repeats it. So a paper soak is ratified as a **technical shakedown** (does every
door, journal, reconnect, reconciliation and kill path actually fire?) and explicitly **not** as a
profitability test. The schedule gate is the operator's rider: *"a ~1-week warm-up/observation
period before live trading"* (`runbook.md:80`, DEC-0135).

### New for the node

1. **Wire the four risk golden scenarios.** `docs/lenses/testing/fixtures-and-scenarios.md:79`: SCN-0006/
   0008/0010/0011 *"stay defined-unwired until the node wires them"*; `test-strategy.md:103,:143`:
   contract tests may pass but *"no integration or runtime proof exists until the node wires them."*
2. **A venue conformance suite both a test double and the live client must pass** (FEAT-0023 venue
   test double; UNKNOWN-outcome fixtures per trigger; the superseded-by-fill cancel read-back,
   `fixtures-and-scenarios.md:76`).
3. **Inherit and discharge the verification debt.** 64 UNPROVEN + 23 VERIFICATION-DEBT findings were
   out of the fix round's scope. The node-facing five: **QMX-F045** human-only promotion signer never
   asserted (`PromotionCard.sign(signer="agent:...")` never tested); **QMX-F062** UNKNOWN block
   proven on exactly one stream, `(venue, account)` granularity untested in both directions;
   **QMX-F063** CT-18 amend-atomicity verify-or-refuse has zero tests; **QMX-F068** frozen-money-face
   R proven only on a function the door path is never shown to call; **QMX-F067** Epic-10
   cardinality and colliding-action collapse untested (`proof_map.md:35-45`; `findings.csv:47,64,65,
   69,70`).
4. **Extend mutation coverage** to the node's own money path once it exists.
5. **A `FAILURES.md` for every node failure mode** — connection loss, credential expiry, drift,
   kill-switch, stand-down, clock drift, backup failure.
6. **Skylos now gates deployment artifacts for free** — the node's systemd unit will be scanned for
   root edge services, missing sandboxing, mutable `ExecStart` and literal env secrets
   (`dig-web-currency.md` row 7). Terraform, if ever introduced, would need a separate scanner.

### Operator question — Q-QA13 · ASSUMPTION (cheap veto)

> **Recommended: the live milestone is gated on a one-week paper run that proves the machinery
> works — every alarm, reconnect, reconciliation and kill path fired and was recorded — and
> explicitly not on whether it made money.** Your own rules forbid using paper profit to authorize
> live money, so a profit gate would contradict them. Example: a deliberate mid-week disconnect, and
> you confirm the node marked the order UNKNOWN, refused to guess, and cleared it only when you
> said so. Alternatives: (a) a two-week run to catch a month-boundary rollover as well; (b) a
> shorter run with a scripted fault-injection drill instead of waiting for real faults.

---

## Contradictions and tensions on the record

1. **"One CLI" scope.** DEC-0159 is QMB-scoped; DEC-0185 **Ruling C names QML** — *"QML ships NO
   CLI, ever in this shape"*. The node's control door is unruled and the node is outside QMF V1
   documentation scope. The operator's *"I don't know why we would have two command lines"* is a
   strong lean spoken in the QML-vs-QMB context, not a node ruling.
   (`_docwork/ledger.yaml:1491` vs `:1725` vs `docs/glossary.md` Trading Node.)
2. **Reconciliation verdicts: three vs four.** `prd.md:406-411` `[MINED]` names
   `reconciled | drift | unknown`; `ct-20:26,:44` and the glossary name **four**, adding
   `out-of-lookback` precisely so *"I cannot see that far back"* is never read as *"the position
   closed"*. **Corpus wins.**
3. **`daily_dead_zone_width`** carries disagreeing recorded evidence — a one-hour table row against
   Flow 9's ~3-hour prose — recorded as a disagreement, never merged
   (`variables.yaml:669`; `ct-31:52`). See Q-QA6.
4. **Paper-mode framing, three readings.** K-25 *"only a fail-mechanism surface"* vs AD-35's
   standing Book-level state vs the blueprint's *"paper twin permanently on, including while live"*.
   AD-35/GAP-0041 wins; **twins are forbidden**; the blueprint is unratified research synthesis.
   (K-27's paired demo binding is **not** in conflict — `ADR-0009:36` names it as the pairing record.)
5. **SQS formula.** SRC-03 memlog entry 118 (*"stays open pending re-understanding pass"*) vs
   GAP-0043 / DEC-0153 / AD-39. The latter are later, ratified, and downstream of the operator's own
   K-38 correction. **DEC-0153 wins.**
6. **Warm-up duration.** The sitting's framing says "~2 days" in QA7; the ratified rider is
   **~1 week** (`runbook.md:80`, DEC-0135).
7. **Latency numbers.** Operator's ~50ms full-round-trip direction vs the GitBook's 35 / 10-45 / 100
   ms budgets. GAP-0013 forbids invented numbers; AD-13 records six named rungs **without numbers
   until measured**; node latency figures are **evidence, never spine constants**
   (`tracker/trading-node-notes.md:24`; `correlate.md:149`).
8. **KSA levels are GitBook-only.** `grep -rn "GREEN\|BLACK" docs/` → **zero hits [verified by A]**.
   `docs/` carries only the KSA *policy posture* pointer (`ct-27:26`). The five levels, four trigger
   classes and law L8 are binding GitBook baseline under L37 but have never been re-ratified into
   `docs/` — this sitting must adopt them explicitly. The matrix stays `GAP-0015`.
9. **The web dossier's protobuf red flag is moot.** `dig-web-currency.md` flags
   `ctrader-open-api==0.9.2`'s `protobuf==3.20.1` pin as *"the single largest currency-conflict the
   node spine must resolve."* The corpus already dissolved it: the SDK is **reference-only and
   rejected** (`DEPENDENCIES.md:47`; `docs/components/ctrader.md:51`), zero Spotware code runs, and
   `qmf-venue` already ships `protobuf==7.36.0` with an in-house compile. The spine must not adopt
   the SDK, and must not "resolve" a conflict that does not exist for it.
10. **The nightly mutation job runs on the wrong branch, today.** GitHub runs scheduled workflows on
    the **default branch**, and `battery.yml:167` asserts main is *"exactly where the ratified
    exact.py / chrono.py live."* **They are not** — `git ls-tree main` shows no `packages/`
    [verified by A]. Until the operator's squash-merge, the first nightly mutmut run will find
    nothing and fail closed on zero mutants classified. Fix by merging, or by pointing the schedule
    at integration.
11. **The tier-3 deferral is stale.** `pyproject.toml:503-506` defers the both-OS clean-install smoke
    *"once a remote exists"*. A remote exists (`origin` = github.com/MubarakHimself/QMX)
    [verified by A]. The condition is met; the gate has not been enabled.
12. **The local `integration` branch ref is stale** at `2c8d495`, behind `origin/integration` @
    `ef9bb25` by the entire QA fix round [verified by A]. Anything that branches from the local ref
    silently loses 35 fix cards.
13. **Trendbar basis.** The web dossier grades BID as SECONDARY (a Spotware moderator on the official
    forum, no docs page). The corpus already demoted it: *"measured-per-broker"*, never hardcoded
    (`variables.yaml:383`; GAP-0037). Do not upgrade the forum finding into a pin.
14. **MIS naming.** ADR-0011 defers a consumer product called "MIS" while `prd.md:374-379` has the
    node host **MIS-Live**. Distinct things; the disambiguation is D1 (`correlate.md:49`).
15. **Old contract identifiers.** `CT-MIS-01`, `CT-BMS-*`, `CT-BOOK-*`, `CT-SYNC-*` are a **different
    contract generation**; ids do not line up and must never be cited as current
    (`correlate.md:168`).
16. **Startup ordering has two ancestors.** The GitBook's four `Start` checks
    (`work/gitbook-baseline.md:320-323`) and the PRD's mined seven-step ordering
    (`prd.md:396-405`) are compatible but differently shaped; the mined ordering is the superset and
    should be adopted, citing the GitBook as its ancestor rather than as a competing rule.

---

## Summary of what this sitting adopts as ASSUMPTIONS (memlog tags)

`A9-1` preflight + startup ordering · `A9-2` explained drift · `A9-3` stand-down-alive ·
`A9-4` shadow lane · `A9-5` always-on evidence tier · `A9-6` notification allow-list + two-plane
rule · `KSA-SHAPE` five levels, escalate-only, A1 de-escalation, effect-per-level configurable with
blank blocking live money · `TIME-BANDS` 10/25/100/250 ms as editable starting values ·
`NODE-DOOR` own thin command + in-process Python API + loopback powers endpoint, no agent door ·
`NODE-PKG` top-level workspace member, own import name, never published ·
`MIS-C01` Book + kill switch only · `PAPER-WEEK` one-week technical shakedown, no performance gate ·
`SUPERVISION` plain systemd service, no container · `EVIDENCE-COLOCATED` evidence tier on the same
VPS · `BACKUP` B2 + VPS-held key, nightly sample restore + quarterly full rehearsal ·
`NEWS-PROVIDER` Forex Factory weekly JSON primary · `CRASH-LOOP` K=3 / T=60s ·
`ADMIT-THEN-ACTIVATE` two boundaries · `LAPTOP-NO-LIVE-CRED` live venue credential on the VPS only.

Every one is individually overturnable without unwinding another.
