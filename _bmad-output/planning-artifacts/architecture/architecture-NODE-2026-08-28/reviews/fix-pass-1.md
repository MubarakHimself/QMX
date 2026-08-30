# Fix pass 1 — reviewer gate applied at desk

**Target:** `ARCHITECTURE-SPINE.md` (Trading Node, architecture-NODE-2026-08-28)
**Date:** 2026-08-28
**Inputs:** the six reviews in `reviews/`; the memlog's GATE RULINGS entry (20 numbered rulings), which is binding and overrides any reviewer fix that says otherwise.
**Result:** 150 findings, 150 applied. 0 deliberately not applied. Spine 936 lines, TN-1..TN-25, `lint_spine.py` = 0 findings.

| Review | C | H | M | L | Total | Applied |
| --- | --- | --- | --- | --- | --- | --- |
| review-rubric | 3 | 8 | 13 | 5 | 29 | 29 |
| review-adversarial | 7 | 15 | 10 | 4 | 36 | 36 |
| review-parent-consistency | 4 | 11 | 23 | 7 | 45 | 45 |
| review-inputs-reconcile | 0 | 2 | 5 | 8 | 15 | 15 |
| review-ops-security | 1 | 6 | 9 | 3 | 19 | 19 |
| review-currency | 0 | 1 | 1 | 4 | 6 | 6 |
| **Total** | **15** | **43** | **61** | **31** | **150** | **150** |

---

## Structural additions (beyond sentence-level fixes)

- **TN-25 minted — "The accounting boundary and the virtual ledger"** (rubric H1, gate ruling 17), binding a new `qmn/ledger` module: the account-scoped day-boundary period calendar identity; the virtual-ledger equity record writer; the VIRTUAL (Book) fold named apart from the VENUE fold with every risk record declaring which; the netting attribution declaration as a bind-time check; `r_unit_price` fixed at period start with a declared recompute cadence; `book_capital` as ladder input only; the kill-line series per ruling 1; rollover/sweep/re-seed as operator-signed AD-16 treasury boundary acts that never touch positions and never re-base a frozen R; `state_carry` / `carries-ledger` on every binding; floating P&L as an explained component, never swept; the paper ledger. Binds/Prevents/Rule present; Capability-map row added; `ledger/` added to the Structural Seed; a `qmn ledger` node added to the paradigm diagram.
- **`## Open questions for the operator (Q1–Q4)`** minted (rubric M11) — each question in plain words with its options, recommendation first, cheap-veto framing. Q1 rewritten per gate ruling 5 (may a second command exist: own command / `qmb node …` via a separate proxy distribution over the HTTP door / API+HTTP only, with the blast radius named).
- **`## Assumption register (A1–A38)`** minted (rubric M11) — id, one-line assumption, owning TN, with `.memlog.md` named as the register's authority.
- **Parent-annotations section extended** with the CLI reconciliation note, the candidate AD-28 annotation, the Records-streams ↔ CT-13 bridge via CT-25 projection names, the `value-status` field mint, the stale `qmf-venue` README correction, and the new registry rows.
- **Diagrams:** paradigm (unix-socket powers channel, node-minted port, ledger); TN-3 topology (`/var/lib/qmx` trees, hub inbox and published split, bucket pushed from the VPS); TN-6 order path (protection gate above command mint, exit lane bypassing the block, standing-intent lane, flatten→`close_position`/`close_all`); TN-10 boot sequence (doors first, boot-attempt record, six checks, cursor re-fold, ordinal recovery); process internals (single-first-writer accumulator, supervisor/door keepalive owner, `resurrect`). All six mermaid blocks validated: balanced fences, at least one edge each, no `|`, no parentheses in labels.

---

## review-rubric (29 / 29)

| Finding | Where | What changed |
| --- | --- | --- |
| rubric:C1 | TN-8, Conventions | Kill line given a declared input series and cadence per gate ruling 1: evaluated per binding against that binding's virtual-ledger equity marked to the latest observed price of its own virtual positions, on every slice carrying a fill or price update on a held instrument and at every rollover; venue equity is the account/reconciliation view; `book_capital` is ladder input only; both series pinned apart in the naming row. |
| rubric:C2 | TN-12, TN-13 | Backup payload key generated on the workstation, escrowed in `qmx/backup-payload-key` plus one offline copy, delivered as a bootstrap credential, never VPS-minted; VPS KEK covers rotated session material only; host-loss restore rehearsal added and made the measurer of full-DR RTO; `backup_payload_key_custody` carries the rule. |
| rubric:C3 | TN-7 | AD-36 predicates restored verbatim — `suspend_new` and `drain` are `never-auto`, `flatten` satisfies on `scope-flat-at-reconciled-verdict`; standing-intent machinery extended to every risk-non-increasing act. |
| rubric:H1 | TN-25 (new) | The accounting boundary and virtual ledger given a rule, a module, a map row and a seed entry. |
| rubric:H2 | TN-11, TN-5, TN-21, TN-22 | `qmn.venue.VenueClientPort` minted node-side over CT-19/CT-20 with two V1 implementations; `qmf-venue` not amended; the alternative recorded as a candidate AD-28 annotation (gate ruling 13). |
| rubric:H3 | TN-6, TN-7, TN-8, TN-9 | `execution_target` resolved from the three AD-35 inputs; `disposition` mandatory on every node-minted trigger kind and classified; benched seat and kill-line stand-down route to paper while the Book stays LIVE; windows and the kill switch block paper. |
| rubric:H4 | TN-2, TN-4 | Boot-attempt record written before preflight; the crash-loop fold counts boot attempts by stage. |
| rubric:H5 | TN-3, TN-12 | Workstation boundary restated as bootstrap/provisioning material only, never rotated live session material; the wizard reports which `qmx/*` entries are stale. |
| rubric:H6 | TN-15 | Silent-degradation alert class added with its six members; the clock-band alert no longer switches off at go-live; "alarming" defined as this push class. |
| rubric:H7 | TN-19 | Seat-callback failure contract: per-callback deadline enforced through `CancelToken`, `LimitProbe` memory, typed refusal plus automatic seat quarantine, with the V1 consequence stated. |
| rubric:H8 | TN-17, TN-20 | Powers channel served over a unix domain socket with `SO_PEERCRED`; the peer credential is recorded and must be the operator principal (gate ruling 19). |
| rubric:M1 | TN-18, Deferred | Anything the soak checklist exercises is soak-blocking; the KSA-values Deferred row corrected from pre-live to pre-soak. |
| rubric:M2 | TN-3, TN-13, diagram | The VPS pushes the bucket copy; diagram edge redrawn from the timers; the backed-up room set named. |
| rubric:M3 | TN-6, TN-8 | Compound-command child identity, ordering and meet; scope resolved through the CT-30 table and refusing rather than widening. |
| rubric:M4 | TN-10, TN-23 | Rung-baseline gate scoped to `role = live`; the harness, not the loop, mints the baseline. |
| rubric:M5 | TN-5 | Slice-latency breach effect declared; accumulator bound with a typed overflow rule that never drops an execution or system observation. |
| rubric:M6 | TN-4, TN-16 | `TimeoutStopSec` at least the drain window and an explicit `WatchdogSec`; an incomplete flush keeps the node up, alarms and refuses a clean exit. |
| rubric:M7 | TN-6 | Durable command-id-binding record chosen as the V1 path, persisted before submission (gate ruling 9). |
| rubric:M8 | TN-16 | `qmn` installable on the workstation for the wizard and Python API only; the VPS checkout is the only runtime installation. |
| rubric:M9 | TN-16, Deferred | One-environment decision stated with its compensating controls; a staging-host Deferred row added. |
| rubric:M10 | TN-13 | Capacity paragraph: declared disk budget, bytes-per-day measured at the soak, purge-after-verified-copy, `disk_headroom_min` minting `no-new-entry` before the disk-full block. |
| rubric:M11 | new sections | Open questions (Q1–Q4) and the assumption register (A1–A38) added to the spine. |
| rubric:M12 | TN-18, TN-19, mint table | `governor_cpu_budget` / `governor_memory_budget` minted with TN-19/TN-23 owner scope. |
| rubric:M13 | Stack | click row carries the deliberate-pin note (8.5.0 exists 2026-08-26; a bump is a DEC-0168 contract-versioning event); inherited rows marked "inherited at `ef9bb25`, not re-verified this sitting"; chrony stated as a minimum. |
| rubric:L1 | TN-7, Conventions | CT-30 effects corrected to `suspend_new \| drain \| flatten`; `flatten` vs `close_all` pinned apart. |
| rubric:L2 | Conventions | Closed world vocabulary enumerated: `live \| replay \| simulated` (reserved-unusable). |
| rubric:L3 | TN-8 | Dead-zone "posture" sentence deleted; the disagreeing evidence recorded unmerged with no default (A8 retired). |
| rubric:L4 | TN-1 | A tier-1 check that every workspace member declares no publishable target. |
| rubric:L5 | TN-11 | The load-bearing CT-18 rows named instead of counted. |

## review-adversarial (36 / 36)

| Finding | Where | What changed |
| --- | --- | --- |
| adv:C1 | TN-6 (cited from TN-10, TN-12, TN-24(h)) | Entry-side-only block law stated once, per gate ruling 6: every node block refuses `place_order` and risk-increasing amends only; a block that cannot be entry-side-only is not minted. |
| adv:C2 | TN-4, TN-17 | In stand-down only bot- and Book-minted intents refuse; operator protective commands and the standing-intent dispatcher always pass; "reachable" means enactable. |
| adv:C3 | TN-11, TN-12 | Token refresh keyed by credential reference with at most one in flight, the sharing fact declared in the roster and verified at preflight, and a rotation-attributable auth failure being retry-after-refresh, never UNKNOWN (gate ruling 7). |
| adv:C4 | TN-18 (mirrored TN-9, TN-10, TN-19, TN-20) | Config partition rule: eligibility and identity only, never runtime state; the compiler refuses a layer supplying one (gate ruling 8). |
| adv:C5 | TN-6, TN-22 | Command ordinal and journal sequence separated; ordinal never reused, high-water mark recovered before sequencers open (gate ruling 9). |
| adv:C6 | TN-7 | KSA fold monotone non-decreasing within a level epoch, lowering only on an operator `resume`. |
| adv:C7 | TN-10, TN-11 | Exact scaled-integer arithmetic domain declared for equity and drift; unscalable or exponent-less figures refuse; epsilon 0 scoped to that domain (gate ruling 10). |
| adv:H1 | TN-22 | Pacer bucket owned by the connection per declared `throttle_scope`; every issuer admits through it; protective reserve capacity minted. |
| adv:H2 | TN-2 | `WriterId` allocated exclusively at Compose, proved pairwise distinct, journaled on the boot-epoch record, refusing on collision. |
| adv:H3 | TN-5, TN-10, TN-13, diagram | Accumulator declared single first writer with a durable interpretation cursor re-folded at boot; the process diagram reconciled to one path. |
| adv:H4 | TN-4 (cited from TN-2, TN-16, TN-17, TN-18) | Safe point defined; shutdown mints UNKNOWN for every in-flight command and exits non-zero if the safe point is unreached. |
| adv:H5 | TN-19, TN-20 | Roster declares eligibility only; seat state is a fold; activation is a journaled transition, never a config version. |
| adv:H6 | TN-18 | Registry declares schema only; the config artifact is the sole home of a resolved value. |
| adv:H7 | TN-21 | Named one-way replay import port as the single sanctioned cross-world read; `world` a component of `BotStateScope` (gate ruling 14). |
| adv:H8 | TN-6 | Submission deadline starts at wire handoff; pacer wait is a bounded local queue whose breach is a veto-path refusal. |
| adv:H9 | TN-9, TN-10 | Drift stand-down keyed on `role`, never `world`; `operator_review` defined as a journaled binding-scoped state gating only the next promotion or activation. |
| adv:H10 | TN-19, TN-8 | SQS reaches consumers only inside the signal snapshot; every producer reads as of the slice frontier or publishes `not_ready` (gate ruling 15). |
| adv:H11 | TN-8 | SQS baseline keyed `(VenueId, environment, instrument)`; a demo-conditioned baseline never satisfies a live binding. |
| adv:H12 | TN-3, TN-20, diagram | Hub split into a write-only inbox and a read-only published area, separate from the rooms; the promotion pull refuses `provenance = sandbox`. |
| adv:H13 | TN-12, Conventions | Three named secret holders and no fourth; per-unit credential delivery (gate ruling 12). |
| adv:H14 | TN-8 | Kill line declared by the Book definition, evaluated per binding, standing that binding down only (gate ruling 1). |
| adv:H15 | TN-2 | Timer units run an abbreviated ceremony over the same inputs, one `composition_fp` per deployment, own boot epoch and `WriterId`. |
| adv:M1 | TN-4 | Crash-loop fold counts boot attempts, not boot epochs. |
| adv:M2 | TN-2 | Preflight failure boots into stand-down-alive with the doors serving; only a door-bind failure exits non-zero. |
| adv:M3 | TN-6, TN-10 | `resolve_unknown` precedence: automatic on an unambiguous read-back, operator-attested otherwise, and only the second carries a signer. |
| adv:M4 | TN-6, TN-11 | A connection fault applies to every command stream bound to that connection, each journaling its own block. |
| adv:M5 | TN-15 | Backup, restore-drill and clock-band failures placed explicitly on the push tier. |
| adv:M6 | TN-9, TN-23 | Paper ledger runs so a paper capital floor is evaluable, plus an operator-signed synthetic breach drill (gate ruling 20). |
| adv:M7 | TN-16 | `deploy switch` mints a deployment record carrying commit and config version; the dry run validates that pair. |
| adv:M8 | TN-13, TN-21 | `hot_room_retention_window` minted; a replay predating it reads the evidence tier through the import port. |
| adv:M9 | TN-5 | `max_slice_latency` given a declared breach effect. |
| adv:M10 | TN-4, TN-5 | Drain-order priority applies to dequeue for interpretation only; recorded arrival order preserved. |
| adv:L1 | TN-16, TN-23 | The benchmark regression gate is evaluated on the VPS; CI runs the harness for correctness only. |
| adv:L2 | TN-1 | Naming blast radius under Q1: platform names stay, the identifier set moves together. |
| adv:L3 | TN-15 | Opaque-id mapping table homed with the roster in the config artifact. |
| adv:L4 | Structural Seed | `qa/` tree added (and `FAILURES.md`). |

## review-parent-consistency (45 / 45)

| Finding | Where | What changed |
| --- | --- | --- |
| parent:C-1 | TN-7 | `drain` restored to `never-auto`; satisfaction predicate added as a mandatory `ksa_effect_matrix` cell. |
| parent:C-2 | TN-25, TN-18, TN-20, TN-22, TN-9 | `state_carry` per counter on every binding the node mints, `carries-ledger` for any carry, `continues-performance` as its own signed act; the powers edit flow collects them and refuses when absent. |
| parent:C-3 | TN-11, Structural Seed, ports table, Stack | Transport locus declared: the socket, framing, encoder, subscription and submit path are a `qmf-venue` increment completing its existing `ConnectionManager`; `protobuf` stays qmf-venue-only; `qmn/venue/ctrader/` keeps only node-side work. [new assumption A37] |
| parent:C-4 | TN-21 | The cross-world crossing named as a one-way replay import port; replay writes only into replay-world rooms. |
| parent:H-1 | TN-25, TN-8, TN-10, TN-11, TN-24, Conventions | Virtual (Book) position vs venue position named apart, every risk record declaring which, and every ambiguous occurrence qualified. |
| parent:H-2 | TN-22, TN-6 | Netting read from CT-18 at bind time; shared-flatten signature as a binding identity field; one Book per netted account as the V1 default; indistinguishable scope refuses (gate ruling 4). |
| parent:H-3 | TN-8 | `amend_min_improvement` re-sited as Book ratchet origination policy; no node component may refuse a risk-non-increasing `amend_protection`. |
| parent:H-4 | TN-24(f) | Rewritten to AD-36's flatten authority; a money boundary is never itself a flatten trigger; a coinciding declared force-flat is honoured. |
| parent:H-5 | TN-7 | CT-30 vocabulary corrected; a `flatten` resolves at dispatch into `close_position` / `close_all`. |
| parent:H-6 | TN-6, diagram | Protection gate's blocking half is entries only; risk-reducing commands pass unconditionally and are shown bypassing it. |
| parent:H-7 | TN-7, TN-6, TN-23 | Standing-intent machinery extended to every risk-non-increasing act, with a soak-gate drill. |
| parent:H-8 | TN-10, TN-11, TN-23 | Amend atomicity becomes the sixth first-connection check, journaled into the venue-observation profile and proven at the soak. |
| parent:H-9 | TN-11, Parent annotations | Promoted to a declared conflict-to-surface; resolved per gate ruling 13 with the alternative recorded as a parent annotation. |
| parent:H-10 | TN-2, TN-6 | Risk-domain writer `(machine, risk role, binding)` added to Compose and the writer inventory; the risk dispatcher's block-on-unpersistable duty stated. |
| parent:H-11 | TN-5 | Slice frontier declared as the accumulator's receive wall instant; recorded stream order is the replay cursor order. |
| parent:M1 | TN-8 | **Gate ruling 1 overrides the review's fix:** `kill_line_capital_floor` is KEPT as the one ratified registry key and stated to BE AD-40's `loss_floor`; no second name, no alias. |
| parent:M2 | TN-8, TN-18, mint table | `decision_freshness_bound` minted, Book-scoped, mandatory and non-defaultable. |
| parent:M3 | TN-8 | `instrument_class` named as a dated AD-9 record with AD-38's missing-record rule mirrored. |
| parent:M4 | TN-8 | Dead-zone posture removed; blank-and-fail-closed only. |
| parent:M5 | TN-14 | Qualified to evidence timestamps; AD-8 civil-time bucket keys declared legal and identity-bearing. |
| parent:M6 | TN-9 | The role collapse onto `demo` declared deliberately with its consequence and the later split named. |
| parent:M7 | TN-17 | Cross-role entity projections declared, with `role` on every row. |
| parent:M8 | TN-2 | Registered extensions' distribution identity and version added to `composition_fp`. |
| parent:M9 | TN-10, TN-25 | AD-16 treasury boundary-event kind named; no money moves without one. |
| parent:M10 | TN-19 | AD-24 declaration made explicit: heavy by default, fan-out with staleness stamps, consumption under a declared maximum age. |
| parent:M11 | TN-19, TN-23 | Rung baseline sequenced into the soak's first hours, before the doors open on live bindings. |
| parent:M12 | TN-3 | Room-role placement stated per world, live and replay. |
| parent:M13 | TN-13 | `corroborates` / `disagrees-with` posture for the two tick sources. |
| parent:M14 | TN-6 | Collapse rule, compose rule and the standing invariant imported; suppression no longer blanket. |
| parent:M15 | TN-7, TN-10, Conventions | Fold contracts declared per fold, resolving by AD-37 rank and never by `WriterId` byte order. |
| parent:M16 | TN-17, TN-20 | AD-18 plain-words summary rendered, stored and identity-bearing. |
| parent:M17 | TN-24(e) | Breakevens never count under any `q`; scratches count only where the Book's declared `q` reaches them. |
| parent:M18 | Conventions, TN-8 | Node stand-down and binding `stood-down` named apart; the kill line stands a binding down, never a Book. |
| parent:M19 | TN-18 | Book/BMS fragments declared derived-with-lineage; an edit mints a new source definition version. |
| parent:M20 | TN-6 | Do-not-default roster split into values and responsibilities. |
| parent:M21 | TN-17 | The sealed period's one logged final look given a powers-channel path. |
| parent:M22 | TN-23 | Each benchmark's regression threshold stated when its baseline is recorded. |
| parent:M23 | TN-23 | Drift stand-down fault-injection drill added. |
| parent:L1 | TN-6, Conventions | `cancel_order` spelled per AD-27. |
| parent:L2 | TN-2, TN-4, TN-10, TN-13, TN-16, diagrams | Bare "calendar" removed from operational phrases; the three kinds named. |
| parent:L3 | TN-6 | `denied-locally` separated from an authority-layer veto. |
| parent:L4 | TN-17 | Door-parity scope declared. |
| parent:L5 | TN-11 | The sensing-outage narrowing cites L39 as its authority. |
| parent:L6 | TN-21 | `world` derived from data provenance, never caller-declared. |
| parent:L7 | TN-19 | QL-1's writer unit `(machine, authoring role, kind)` cited. |

## review-inputs-reconcile (15 / 15)

| Finding | Where | What changed |
| --- | --- | --- |
| inputs:H1 | TN-18, TN-20, Parent annotations | `value-status` in `blank \| provisional-evidence \| ratified` minted; a provisional value gating live money blocks `role = live` until an operator countersign; the promotion battery checks `ratified` (gate ruling 16). |
| inputs:H2 | TN-23 | Venue conformance double (FEAT-0023) bound as a required node artifact, with UNKNOWN-per-trigger fixtures and the superseded-by-fill read-back; SCN-0006/0008/0010/0011 named as the golden scenarios the node wires and proves. |
| inputs:M1 | TN-17, TN-15 | Every read model carries authority source, source time, receive time and watermark as required fields. |
| inputs:M2 | TN-15, Parent annotations | The five Records streams bound to CT-13's seven event types as CT-25 projection names, with the node's mapping stated. |
| inputs:M3 | TN-2 | `composition_fp` extended with the registry as-of set fingerprint and every calendar identity in play. |
| inputs:M4 | TN-16, TN-23 | The nightly mutation job targets the branch that carries code; a zero-mutants run fails closed and alarms. |
| inputs:M5 | TN-24(j) | `rejected-by-venue (superseded-by-terminal-subject)` added as a named outcome, never a stream-blocking UNKNOWN. |
| inputs:L1 | TN-11, TN-24(i) | A requote is an ordinary mapped venue rejection through the error map. |
| inputs:L2 | TN-10, TN-11 | Amend atomicity given a home as the sixth first-connection check. |
| inputs:L3 | TN-24(j) | CT-29 venue-initiated close reasons named with `closing_authority = venue`. |
| inputs:L4 | Inherited invariants, TN-19 | Shadow-lane row corrected to seam-named-and-deferred; no-ambient-randomness and no-authority-without-fresh-ratification stated as node invariants. |
| inputs:L5 | Parent annotations | The stale `qmf-venue` README flagged for the doc factory. |
| inputs:L6 | TN-11 | The conscious divergence from QB1a recorded with its accepted consequence. |
| inputs:L7 | TN-13 | Position and balance events named as first-class journaled ingestion kinds. |
| inputs:L8 | TN-5 | Streaming-indicator single-feeder `WriterId` and `SnapshotScope` restore-equivalence bound on the live path. |

## review-ops-security (19 / 19)

| Finding | Where | What changed |
| --- | --- | --- |
| ops:C1 | TN-12, TN-13 | Payload key escrowed off the VPS; the full-restore drill supplemented by a clean-host rehearsal that actually exercises key recovery; the host-key rationale corrected to say it survives reboot and rotation but not VPS death (gate ruling 2). |
| ops:H1 | TN-15, TN-23 | External dead-man's switch required, alerting on a missing heartbeat, with a liveness digest that survives go-live and a soak-gate drill (gate ruling 18). |
| ops:H2 | TN-15 | The allow-list reconciled with every TN that says "alarm" via the silent-degradation class, and generated from the `FAILURES.md` notification-tier column. |
| ops:H3 | TN-13, TN-15 | `disk_headroom_min` minted and alarmed; retention and rotation math named so headroom is bounded by design. |
| ops:H4 | TN-2, TN-4 | Doors, notifier and preflight-status view bind before preflight; a preflight or compose failure boots into stand-down-alive rather than an exit loop (gate ruling 11). |
| ops:H5 | TN-17 | `qmn config init` and `qmn config validate` defined as the day-one authoring affordance; "console-managed" removed as an answer. |
| ops:H6 | TN-23 | CI gate on `FAILURES.md` completeness, all six fields, and every operator affordance resolving to a real door or CLI capability. |
| ops:M1 | TN-4 | Safe point defined precisely, positions never waited on, bounded by the drain window with a typed refusal on breach. |
| ops:M2 | TN-16, TN-23 | Check mode's gate set and exit contract defined; a real-systemd `LoadCredentialEncrypted` boot added to the soak gate. |
| ops:M3 | TN-12 | Provisioning privilege path declared: a dedicated key-only SSH identity restricted to one passwordless-sudo provisioning command. |
| ops:M4 | TN-16 | Unattended upgrades configured never to restart `qmn.service`; any systemd-initiated restart routes through the drain path. |
| ops:M5 | TN-10, TN-17 | Outstanding-UNKNOWN read model with per-command read-back detail; a typed refusal where the read-back cannot support attestation. |
| ops:M6 | TN-4 | Disk-full composition stated: entry-side block, protective acts as standing intents, venue-resident stop, keepalive owned by the door layer so a storage stall is never converted into a restart. |
| ops:M7 | TN-15, TN-23 | `qmn notify test` added and end-to-end delivery proof made a soak-gate item. |
| ops:M8 | TN-13 | Two RTO numbers recorded apart: integrity-restore and full-DR. |
| ops:M9 | TN-2, TN-17 | Boot-failure diagnosis affordance: the door serves a preflight-status read model through a failing boot. |
| ops:L1 | TN-16 | Egress allow-list posture stated. |
| ops:L2 | TN-9, TN-15 | Demo drift delivered as a soak-scoped digest rather than the live alarm class. |
| ops:L3 | TN-16 | The pre-`qmn` bootstrap named as its own day-one step. |

## review-currency (6 / 6)

| Finding | Where | What changed |
| --- | --- | --- |
| currency:F1 | TN-16, TN-3, diagram | `DynamicUser` replaced by a fixed `User=qmx` account with `ProtectSystem=strict` plus `ReadWritePaths=/var/lib/qmx` and every writable tree rooted there and shown in the topology diagram (gate ruling 12). |
| currency:F2 | TN-4 | `READY=1` and `WATCHDOG=1` owned by the supervisor/door layer, never the domain slice loop, so they continue through stand-down. |
| currency:F3 | TN-4, TN-16 | Restated as `StartLimitBurst > K` with `StartLimitIntervalSec ≥ T`, and the consequence of burst ≤ K spelled out. |
| currency:F4 | TN-4, Stack | Reworded to the raw sd_notify protocol over a stdlib `AF_UNIX` datagram socket, with no `python-systemd` or `sdnotify` dependency. |
| currency:F5 | TN-12 | `--with-key=host` pinned in the wizard command, with the security boundary stated. |
| currency:F6 | Stack, TN-14, TN-16 | 26.04 forward-note added: chrony becomes default so provisioning verifies rather than installs, and the CI pin holds until `ubuntu-26.04` leaves preview. |

---

## Findings deliberately NOT applied

**None.** Every finding of every severity in all six reviews is applied. Two are applied in the form the memlog GATE RULINGS dictate rather than the form the review proposed, and both are recorded above:

- **parent:M1** — the review asked to drop `kill_line_capital_floor` or demote it to a display alias. **Gate ruling 1** keeps it as the one ratified registry key and states that it IS AD-40's `loss_floor`. Ruling wins; the defect the review named (two floors that can drift apart) is closed by the one-value-one-name sentence.
- **parent:H-9 / rubric:H2** — the review left the choice open between a node-minted seam and a `qmf-venue` amendment. **Gate ruling 13** picks the node-minted `VenueClientPort` with `qmf-venue` unamended and the alternative recorded as a candidate AD-28 annotation.

---

## New assumption ids

| Id | Assumption | Owning TN |
| --- | --- | --- |
| A31 | A fixed `qmx` service account rather than `DynamicUser`, with every writable tree under `/var/lib/qmx` | TN-16 |
| A32 | `SO_PEERCRED` over a unix socket rather than a per-operator signing key held off-node | TN-17 |
| A33 | A named one-way replay import port over an export-with-lineage copy, as the single sanctioned cross-world read | TN-21 |
| A34 | `value-status` minted as a new registry field rather than left to the blank-versus-filled split | TN-18 |
| A35 | An external dead-man's switch as a required V1 component, against the otherwise no-required-external-stack posture | TN-15 |
| A36 | A node-minted `VenueClientPort` rather than a seam realized in `qmf-venue` | TN-11 |
| A37 | The cTrader transport increment lands in `qmf-venue`, completing its existing connection manager, rather than in `qmn` | TN-11 |
| A38 | The seat-callback deadline plus automatic seat quarantine as the V1 containment line, ahead of OS confinement | TN-19 |

**Retired:** A8 (the wider dead-zone default posture) — retired by parent:M4; the width now carries no node posture and no default, and the disagreeing evidence stays recorded unmerged.

---

## Mechanical verification

- `lint_spine.py` over the workspace: `{"ok": true, "total_findings": 0}`.
- Scripted self-check: 25 TN blocks, ids TN-1..TN-25 in ascending order, every block carrying **Binds** / **Prevents** / **Rule**; zero `<!--`; 14 fences balanced across 6 mermaid blocks, each with at least one edge, no `|` and no parentheses inside `[...]` labels; banned vocabulary (`engine`, `kernel`, `plugins`, `exam`, `minimal core`, `paper node`, bare `stop out`, `timeframe`) appearing only inside its own prohibition sentences.
- Final length: 936 lines. Frontmatter `status: draft` unchanged; `provenance` updated to record the gate.

---

## Operator-round amendments

**Date:** 2026-08-28, after the fix pass. **Inputs:** the memlog's `OPERATOR RULINGS 2026-08-28` and `AMENDMENTS FROM THE OPERATOR ROUND` decision entries — binding, and the exact instruction set for this pass. **Result:** spine 950 lines, TN-1..TN-25 unchanged in count and id, `lint_spine.py` = 0 findings, six mermaid blocks valid. `status: draft` left as-is for the validation re-gate.

| # | Where | Change |
| --- | --- | --- |
| 1 | Frontmatter | `scope` no longer says "operator doors (CLI/API)" — it names the Python API, the localhost evidence channel and the unix-socket powers channel. `provenance` gains the operator round: four rulings applied, A1 narrowed, A10/A17/A26 RULED, A39 added. `status: draft` untouched |
| 2 | Design Paradigm diagram | The `qmn CLI door` node is deleted. Added the desktop UI (the operator control surface, over an SSH tunnel) and the operations toolkit as a small node, both feeding the SAME two channel doors. Still valid mermaid |
| 3 | Inherited invariants, L30 row | "TN-1 reconciliation note" becomes "TN-1 L30 annotation" — the second half of that note no longer exists |
| 4 | Corrections inherited, item 5 | Rewritten from "'One CLI' is NOT settled here… put to the operator as Q1" to a SETTLED item: the node has no operator command line, PRD FR-046 / DEC-0159 / DEC-0185 Ruling C stand unchallenged, and the toolkit is DevOps tooling |
| 5 | TN-1 | `qmn` narrowed to the distribution and import CODE NAME (the operator declined to rule the name; a rename is mechanical); the operator command-line door removed; new **NO OPERATOR COMMAND LINE** bullet; new **OPERATIONS TOOLKIT** bullet — install, switch/rollback, secrets provisioning wizard, data bootstrap, replay, config init/validate/explain, notify test and the on-demand restore drill are `just node-…` recipes in the root justfile with bodies under `qmn/deploy/`, an operations toolkit, never a trading control and never a product command line, with no privileged path around the doors; the "naming blast radius under Q1" bullet rewritten as a bounded identifier set; the reconciliation note reduced to its L30 half; A1 tagged RULED-and-narrowed |
| 6 | TN-9 | The soak is now the FULL first-deploy warm-up week, unattended, on the demo account, live binding at its end — the "roughly two-day soak / first two days" duration bullet is gone, with the operator's words quoted. Acceptance checklist explicitly unchanged. Unattended made a design constraint (alert allow-list, dead-man's switch, liveness digest stand in for a watching operator). A10 tagged RULED |
| 7 | TN-12 | The provisioning wizard is `just node-secrets-provision`, no longer a typed node command |
| 8 | TN-13 | Forex Factory's free weekly file is the SOLE V1 source; the paid impact-carrying fallback slot is deleted; the later fallback path named as a second FREE source or an agent-scraped JSON in the same CT-15 intake shape; new refresh-cadence bullet minting `news_calendar_refresh_cadence` (configurable, duration unit-kind, evidence every 2 h and before each session open, the free feed's ~2 downloads per 5 min limit respected and a breaching cadence refused at config compile); history bootstrap is `just node-data-bootstrap`; the minted-rows list gains the cadence key; A17 tagged RULED |
| 9 | TN-15 | New **OBSERVABILITY STACK** paragraph replacing the old "optional zero-authority consumers" line: a SEPARATE zero-authority Prometheus + Grafana + Loki/Promtail-class system shipped as a compose file under `qmn/deploy/observability/`; containers permitted for THIS STACK ONLY (the node stays a plain systemd service); Skylos's IaC scan gates the compose file; image versions pinned at the implementation gate and registered as external tools in `DEPENDENCIES.md`; the node ships exporters plus dashboard-as-code seeds; the push channel and the external dead-man's switch stay, explicitly not replaced. The notify test re-homed to `just node-notify-test`. A monitoring agent named as later and out of scope |
| 10 | TN-16 | The install, switch and rollback commands become `just node-install` / `just node-switch <commit>` / `just node-rollback`, stated as toolkit recipes that move code and configuration and are never trading controls; the install recipe also lays down the observability compose file |
| 11 | TN-17 | Title now "three thin doors, no command line". The node's typed command-line door is DELETED; the remaining doors are re-ordered and named (the Python API; the localhost HTTP evidence channel; the unix-socket powers channel with `SO_PEERCRED`) — see the deviation note below. New bullets: the desktop UI is the operator's control surface and consumes these doors over an SSH tunnel later; the operations toolkit makes the same read/act calls through the same doors during the soak with no privileged path; config authoring (`init` / `validate` / `explain`) moves to toolkit recipes over the same library functions; every operator moment (kill switch pressed, news window in force, stuck UNKNOWN, promotion, activation, `resurrect`, paper flip, `value-status` countersign) is a future UI story rendered from these read models and powers, walked behaviour-driven at the UI sitting; ONE versioned wire vocabulary with the coordination note that it aligns with the QMA daemon-to-UI wire-contract conventions once the QMA spine fixes them, tagged `[ASSUMPTION A39]`. Parity scope, the powers list and the settings scopes re-worded off the deleted door |
| 12 | TN-18 | Value-home and versioning rules re-worded onto the powers channel plus the authoring recipes; `news_calendar_refresh_cadence` added to the do-not-default list with its evidence; new **EXTENSIBILITY** bullet — adding a Book, a BMS, a bot or a new version of any is registry + roster config + restart-at-safe-point, never code, and a change needing node code to admit one is a design defect |
| 13 | TN-19 | Registration re-worded onto the doors. New explicit statement that no trained model is bound in V1 and the labelers stay rule-based. New **SHADOW-LANE SEAM** bullet making it V1 node work in three pieces: candidate labeler registration at the composition root (candidate role, refused into the governed consumer set), a shadow snapshot stream on its own manifest prefix under its own `WriterId` with the same schema and frontier-bound read rule, and a comparison read model; plus the never-a-live-consumer rule, enforced by a boot refusal. The old "shadow lane is Deferred" sentence narrowed to the ML/training half |
| 14 | TN-20 | Promotion re-written per Q3: it is a CLICK whose precondition battery runs SILENTLY, server-side, against fresh state and against reviewed backtest evidence; activation is explicitly the second act; "the operator sees results, never machinery" written in, with the refusing check named and journaled. A26 tagged RULED |
| 15 | TN-21 | The replay entry point is the toolkit's `just node-replay <day or range>` or the Python API, never a trading control |
| 16 | TN-22 | Extensibility sentence added at the roster: a Book, BMS, bot or new version of any is registry + roster config + restart-at-safe-point; a new account, broker or `VenueId` is the same shape |
| 17 | TN-23 | `operator affordance` now resolves to a door capability or an operations-toolkit recipe; the soak gate names the full unattended warm-up week with the checklist unchanged; one checklist item added — the observability stack stands up from the checked-in compose file and its seeded dashboards render for the whole week, with the node proven to run unchanged when the stack is stopped |
| 18 | Parent annotations | The command-line reconciliation note is deleted outright (withdrawn: no conflict with PRD FR-046 remains). The L30 annotation, the AD-28 candidate, the Records-to-CT-13 bridge and the `value-status` mint are untouched |
| 19 | Registry mint table | `news_calendar_provider_fallback` deleted; `news_calendar_provider_primary` re-stated as the sole source; `news_calendar_refresh_cadence` added with unit-kind and evidence |
| 20 | Glossary / DEC candidates | Glossary gains: operations toolkit versus the doors, the observability stack, shadow snapshot stream versus governed signal snapshot, candidate labeler. DEC-candidate lines for TN-9 and TN-17 re-worded |
| 21 | Consistency Conventions | Naming row: `qmn` is a code name, the node ships no command line, the toolkit is DevOps tooling. Bring-up phases row: FOUR became THREE — the first-deploy warm-up week **is** the soak. Doors row: three doors and no command line, the UI as control surface, the A39 alignment. Ops row: the toolkit recipes and the observability-stack container exception |
| 22 | Stack | The `click` row is replaced by an explicit NOT-TAKEN row (QMB keeps its own pin); a `just` row added (existing repo tool, recipes call `uv run` scripts with stdlib `argparse`); an observability-stack row added, marked seed-only with versions pinned at the implementation gate and registered as external tools. The "no Docker" sentence re-stated: no container for the node, containers only in the observability compose file |
| 23 | Structural Seed | `doors/cli/` dropped; `doors/{api/, http/}` kept and re-labelled; `deploy/justfile-recipes/` added (the scripts the root justfile's `just node-…` toolkit calls, DevOps only) and `deploy/observability/` added; `deploy/systemd/` kept |
| 24 | Runtime diagram | The door-layer node no longer lists a command line; it reads Python API, localhost HTTP evidence, unix-socket powers |
| 25 | Deferred | The desktop-UI row re-written (deferred but never optional; every operator moment is a UI story over TN-17's read models and powers). The MIS row split into: a new **MIS training + shadow rollout epic** row (follow-on after the paper milestone — offline job in a sandbox or on the operator's laptop, data window + RNG seed + code `fp1` recorded, versioned model artifacts registered, promotion = ratification, version bump, re-certification over one full affected-Book cycle, Kronos-class pretrained candidates carrying no authority without fresh ratification per PRD §6) and a narrowed live-path/ML row. A **dedicated monitoring agent** row added |
| 26 | Open questions section | Renamed **Operator rulings 2026-08-28** and rewritten as four rulings R1–R4, one short paragraph each, quoting the operator's decisive words as the memlog records them, plus a closing paragraph for the five side rulings from the same dumps (the UI will exist; MIS models must be trained; extensibility; alpha decay left at AD-41 primitives; QMF portability not this layer's concern) |
| 27 | Assumption register | Title `A1–A38` becomes `A1–A39`. A1 marked RULED and NARROWED (code name only, no command line); A10, A17, A26 marked RULED with their ruling text; A23 notes its command-line half was ruled away; A39 added (the wire-vocabulary alignment with QMA). A8 stays retired |

### One deviation from the instruction, stated plainly

The instruction asked both to **renumber the remaining doors** and for the self-check to show **zero occurrences of "Door 2"**. Renumbering in place would have made the HTTP evidence channel the literal "Door 2", so the two cannot both hold as written. Resolved by keeping the ordering and dropping the numerals: the doors are now "THE FIRST DOOR — the Python API", "THE SECOND DOOR — the localhost HTTP evidence channel", "THE THIRD DOOR — the powers action channel", with the TN-17 title and the Consistency Conventions row both saying "three doors and no command line". The ordering the instruction asked for is preserved and the grep is clean. Trivially reversible if the orchestrator prefers literal numerals.

### Mechanical verification

- `lint_spine.py` over the workspace: `{"ok": true, "total_findings": 0}`.
- Scripted self-check: 25 TN blocks, ids TN-1..TN-25, each carrying **Binds** / **Prevents** / **Rule**; zero `<!--`; 14 fences balanced across 6 mermaid blocks plus one `text` block, every mermaid block head-valid with balanced `[]`, `()` and `{}`; banned vocabulary (`engine`, `kernel`, `plugins`, `exam`, `minimal core`) appearing on one line only — the Naming convention row that prohibits it. The word "plug-in" was avoided in the operator quotes and rephrased as "one surface inside that UI", to keep clear of the `plugins` ban.
- Zero occurrences of the deleted command forms: `Door 2`, `qmn CLI`, the backticked `qmn` CLI, `qmn deploy install`, `qmn secrets provision`, `qmn deploy switch`, `qmn config init`, `qmn data bootstrap`, `qmn replay`, `qmn notify test`, `qmn registry`. The three surviving "CLI" tokens are prohibitions or unrelated: the withdrawn reconciliation note in TN-1, the Stack row saying no CLI framework is taken, and one inside the word "CLICK".
- Final length: 950 lines (was 936). Frontmatter `status: draft` unchanged.

---

# Residual fix pass 2 (validation re-gate, 2026-08-28)

Applied at desk over the 951-line spine. Source: the five re-gate reviews (`regate-parent-consistency.md` 2C/8H/16M/4L, `regate-adversarial.md` 7C/12H/10M/4L, `regate-rubric-ambiguity.md` 4C/10H/14M/7L, `regate-operator-reconcile.md` 1H/1M/4L, `regate-fix-regression.md` 1H/2L) = **107 findings**, each applied with the review's supplied Rule sentence tightened for terseness, **except where a GATE-2 RULING (`.memlog.md`, orchestrator, 34 rulings) decides the point — there the ruling's text wins**. Where two reviews hit one defect, one coherent amendment was written and both rows point at it. Every TN id and heading is stable. `status: draft` unchanged; `provenance` records the re-gate.

## Applied — one row per finding

### regate-parent-consistency (30)

| Finding | TN / section | Change |
| --- | --- | --- |
| RC-1 | TN-6, TN-24 (c), TN-23 | **Ruling 1 wins over the review's own fix.** "an outstanding UNKNOWN" removed from TN-6's entry-side enumeration; a new bullet makes AD-27's per-command UNKNOWN block **the one non-control block (AD-36)** — every command on the stream refused, protection included, a refused protective act standing as a journaled protection intent, cleared only by `resolve_unknown`. TN-24 (c) and the TN-23 item rewritten to match |
| RC-2 | TN-6 command mint; TN-11; TN-23 | **Ruling 2.** New PROTECTIVE-STOP ATTACHMENT bullet: entry-relative form for MARKET orders, `unsupported capability` refusal where the Book requires attachment and CT-18 does not declare it, AD-40's declaration staying the plan. The CT-18 row now names the field as the one TN-6 reads. TN-23 item added |
| RH-1 | TN-4; Parent annotations | **Ruling 4.** `resurrect` is a node lifecycle act journaling as an AD-21 `control action` **event** under the declared subtype `node_resurrect`; no CT-30 kind minted. Subtype proposed as a doc-factory mint |
| RH-2 | TN-18; TN-17; TN-20 | `admission_impact` ENFORCED: the compiler derives the impact from the diff's registry rows and stamps it; a `resign` diff makes the binding inadmissible to live until a fresh AD-32 Layer 2 + 3; `relint` re-runs Layer 1; the settings click renders it and the promotion battery reads the stamp |
| RH-3 | TN-6 Book door; TN-19 seat contract | CT-23 v2 `advisory_stop_proposal` carried on the entry intent and consumed by the per-family `ExitLogicRef`, with the ratified **adopt-the-bot's-advisory-stop module mode** named (DEC-0185 / DEC-0177); `requested_r` stays Book-resolved |
| RH-4 | TN-4 (model stated once), TN-2 (cites it) | **Ruling 5.** A DETECTED preflight refusal never exits; the crash-loop fold governs only failures that DO exit — door-binding failure, unhandled death after boot |
| RH-5 | TN-9; TN-23; Deferred | **Ruling 32.** The live connection opens for sensing and recording only as soon as credentials exist; the live binding waits on its own baselines; the Deferred row re-timed so Spotware approval and KYC gate go-live, not the soak |
| RH-6 | Parent annotations | **Ruling 31.** The PRD §3 allow-list widening — the silent-degradation class, the dead-man's switch, the liveness digest — recorded as a **proposed PRD amendment**, surfaced not settled |
| RH-7 | TN-6 door ladder; TN-25; TN-24 (a); TN-23 | **Ruling 33.** NO SCALE-IN: an entry against an instrument on which the binding already holds an open **virtual** position is a `policy rejection`, stated over virtual positions so a netted account cannot mask it. Checklist item added |
| RH-8 | TN-18 | **Ruling 30.** The invocation layer is DELETED — four layers: roster, BMS fragment, Book fragment, node defaults — with the reason stated |
| M1 | TN-6 Book door | `close_partial` is not a V1 kind; a partial exit is an `unsupported capability` refusal, never close-then-replace |
| M2 | TN-6 | Carried by RC-2's amendment — the entry-relative form, the reference price as declared CT-19 surface, the declaration never read back as the fill |
| M3 | TN-4; Parent annotations | Shutdown mints UNKNOWNs **after** session close so `disconnect` applies honestly; a `lifecycle-stop` trigger offered as a proposed CT-20 mint |
| M4 | TN-6 | `resolve_unknown` is **itself recorded as a CT-20 observation** on both paths (AD-27 verbatim) |
| M5 | TN-20 | The card carries the Book/BMS **definition fingerprint** as an identity field plus AD-32 Layer 3's one assembled page — both proofs, the binding identity, the capability-satisfaction result and the resolved BMS fingerprint |
| M6 | Parent annotations | Annotation recording `kill_line_capital_floor` and AD-40's `loss_floor` as ONE variable under one canonical registry key |
| M7 | TN-6 arbitration clause | **Ruling 33.** Arbitration resolves strictly by rank with **no arrival-order input**; **Tier 1 venue-resident actions sit outside the ordering** |
| M8 | TN-21 | The SQS door under replay reads the **recorded per-instant signal snapshot**; absent one it reads `not_ready`. A replay never recomputes a sensor value |
| M9 | TN-10 Rule preamble and the drift bullet | "Ratified by adoption" qualified with ONE declared narrowing, **L39 cited at the point of use**, exactly as TN-11 does for the sensing-outage rule |
| M10 | TN-19 | **Ruling 17.** The heavy snapshot's maximum age **IS `decision_freshness_bound`**; no second bound; a labeler that cannot publish inside it publishes `not_ready` |
| M11 | TN-7 | **Ruling 24.** A connectivity or unknown_state escalation on the live connection blocks its own scope and does **not** block paper routing to the paired demo stream |
| M12 | TN-24 (j); Conventions | Rewritten as "a venue margin liquidation (`venue_liquidation`) or a venue-initiated close"; the Conventions row now bans the bare colloquial word in a gloss as much as in a rule |
| M13 | TN-24 (j); TN-6 | **Ruling 33.** A command whose subject is absent or already terminal AT SUBMISSION resolves **without submission**, never as a naked close |
| M14 | TN-7 matrix cell | **Ruling 33.** The satisfaction predicate is drawn from AD-36's full closed vocabulary, `no-pending-orders-at-reconciled-verdict` included |
| M15 | TN-11 CT-18 rows; TN-6 | The acknowledgement-mode consequence carried onto the node's outcome path: an outcome is never derived from absence alone, the cancel read-back rule generalized to `close_position`, `close_all` and `amend_protection` |
| M16 | TN-21 | "Sealed" DEFINED as durably persisted and verified into `sealed-archive` — neither the boot composition seal nor AD-21's 12-month split seal, so TN-23's soak-day replay stays legal |
| L1 | TN-15 | Clause added: the stack is a consumer, not a second console; PRD §6's anti-goal forbids cloning it, not using it |
| L2 | TN-13, TN-14, TN-15, TN-10, Conventions, seed, map | Bare "calendar" purged from operational phrases — news-calendar refresh, news-calendar age, the news-calendar timer, "every market-hours, day-boundary and news calendar identity verified" |
| L3 | TN-6 arbitration clause | AD-37's "a lower-ranked action may never undo a higher-ranked one" carried alongside its converse |
| L4 | Deferred | New row for the AD-9 `paper-validation` / `paper-benched` role split |

### regate-adversarial (33)

| Finding | TN / section | Change |
| --- | --- | --- |
| C1 | TN-4 stand-down; TN-23 | **Ruling 3.** Stand-down refuses **ENTRY intents only, whatever the author**; every risk-non-increasing act passes — Book force-flats, `ExitLogicModule` exits, bot tightens, standing intents, operator commands |
| C2 | TN-2, TN-5, TN-11, TN-21, TN-22 | **Ruling 6.** The port is selected by **`(world, VenueId)`**; `world = replay` selects the replay implementation for every venue; a replay composition resolves no credential, holds no venue secret and opens no socket, preflight proving all three; **THREE V1 implementations** named |
| C3 | TN-8 news blackout; TN-13 | **Ruling 7.** A revision may only WIDEN or ADD an in-force or same-day window automatically; narrowing, downgrading or removing takes effect no earlier than the superseded window's end and is otherwise an operator act |
| C4 | TN-12 | **Ruling 8.** Retry-after-refresh scoped to requests carrying **no command identity**; a command that meets an auth failure is never retried |
| C5 | TN-2; TN-11; Parent annotations | **Ruling 9.** The delegated-impurity clause keeps the increment in `qmf-venue` with the **async-conformance exemption for `qmf.venue.connection`** as a parent annotation, and the "epics may not choose" fallback to `qmn.venue.ctrader` |
| C6 | TN-10 EXPLAINED DRIFT | **Ruling 10.** TWO residuals — **quantity** and **cash** — compared separately at epsilon 0; **unrealized P&L is a mark and is NEVER reconciled**; the two equity series are reported side by side with their mark instants and never differenced |
| C7 | TN-17; TN-1; TN-20; TN-23 | **Ruling 11.** Socket `/run/qmn/powers.sock`, `qmx:qmxops`, 0660, `RuntimeDirectory`; **two peer principals** by uid, neither the `qmx` account; the ops principal refused every trading, protection, promotion, activation, settings, `resurrect`, attestation and countersign power by the transport; preflight refuses to boot if any unit runs as the operator principal; `SO_PEERCRED` proves an account, not a human — named residual risk A32 |
| H1 | TN-16; TN-3; seed; TN-13 | **Ruling 12.** `/opt/qmx` = immutable per-commit trees plus an atomically flipped `current`; `node-switch` materializes beside, dry-runs the new tree, flips at the restart; prune depth declared; the deployment record stays on the version graph |
| H2 | TN-4; TN-16 | **Ruling 5.** A requested restart exits **75** with `RestartForceExitStatus=75` / `SuccessExitStatus=75` and never advances `(K, T)` |
| H3 | TN-15; TN-3; TN-12; TN-13; TN-16 | **Ruling 13.** `qmx-observability.service` under a distinct non-`qmx` account; `/var/lib/qmx-observability` as a `vps_disk_budget` line item with its own quota; `network_mode: host` bound to 127.0.0.1, scraping `/metrics` only; a dedicated read-only journal namespace; its credentials a **declared fourth secret holder**; runtime and image-registry egress provisioned for the stack alone; the node runs and passes without it |
| H4 | TN-19; TN-2 | **Ruling 14.** Candidates enter a separate **`shadow_composition_fp`**, never the governed one; heavy by construction, off the trading path, **never counted toward `max_slice_latency`**, dropped with a data-quality record on their own bound; bound by every governed-labeler rule including no ambient randomness |
| H5 | TN-4; TN-21; TN-17; TN-1 | Replay added to the sanctioned isolated-work list as a **process-per-job outside the node**, with disjoint `WriterId`s and no credential; no toolkit recipe ever constructs a composition root or imports the Python API out of process |
| H6 | TN-22; TN-25 | **Ruling 15.** Attribution declarations on a netted account must be **jointly exhaustive and disjoint — a partition proved at compile**, else `invalid input` |
| H7 | TN-2; TN-8; TN-13; mint table | **Ruling 7.** Calendar CODE identity sealed into `composition_fp`, calendar DATA a frontier-read observation; **`news_calendar_max_staleness` minted** as a per-decision-cycle fail-closed precondition |
| H8 | TN-2 timer ceremony | **Ruling 16.** Timers compose from the config version the RUNNING node sealed, read over the evidence channel; node-absent means `current` plus a `node-absent` stamp; neither readable means refuse and alarm |
| H9 | TN-23; TN-19 | **Ruling 17.** The harness never runs concurrently with a slice-driving node; governor budgets soak-blocking; lifecycle state recorded at measurement; the heavy snapshot's max age IS `decision_freshness_bound` |
| H10 | TN-12; TN-16 | **Ruling 18.** The workstation install is provisioning-only and ENFORCED: the root refuses to compose off the roster's VPS tuple, the `SecretStore` refuses a venue-session holder off that host, and tier-1 checks cover the wizard's imports and the absence of a console-script entry point and publishable target |
| H11 | TN-17; TN-19 | **Ruling 11.** The powers list is declared CLOSED and gains `restore_drill_run`, `config_version_activate`, `seat_reinstate` and `hub_publish`; leaving `quarantined` is `seat_reinstate` only, never inferred from a restart |
| H12 | Consistency Conventions (Identity and formats) | **Ruling 19.** NO float anywhere on the money path, the venue decode included; a money field arriving as a float is refused; the sanctioned crossings are non-money wire floats per CT-18's declared class and the declared comparison-rule quantize |
| M1 | TN-15; mint table | **Ruling 34.** `FAILURES.md`'s `notification tier` column is the SOLE home of alert-class membership; the registry membership row **withdrawn** |
| M2 | TN-16; TN-13; TN-3; seed; TN-23 | **Ruling 16.** `qmn-restore-sample.timer` nightly plus `qmn-restore-full.timer` monthly; the host-loss rehearsal is the `restore_drill_run` power; the unit count restated as FIVE node units plus the stack's own |
| M3 | TN-13 | Backups copy only journal segments **sealed at a committed sequence boundary**, read from the running node, with the boundary in the manifest — a restored room is always a prefix of a real stream |
| M4 | TN-11; TN-23; Ports table | Three V1 port implementations stated, the conformance double among them |
| M5 | TN-1; TN-11; Dependency direction | **Ruling 9.** The sanctioned import boundary is the **`qmn.venue` subpackage**, and the L30 lint is written against it |
| M6 | TN-17 | An ACTIVE CYCLE is the binding's open accounting period per TN-25's day-boundary calendar; a cycle-fixed edit takes effect at the next period open and the click says so |
| M7 | TN-18; mint table; Parent annotations | **Ruling 22.** `value-status` lives on the resolved config artifact's row — Book-declared values included, propagated onto generated fragments — and the registry declares **`value_status_required`** as schema |
| M8 | TN-13 | The recorder's retry policy is declared — N attempts per firing with backoff, inside the same 2-per-5-minute budget; a rate-limit or block is journaled, alarmed and never retried in the same firing |
| M9 | TN-15 | The dedicated read-only journal namespace stated beside the zero-authority claim |
| M10 | TN-3; TN-13 | Per-commit trees, the protection-intent extent and `/var/lib/qmx-observability` added to the named-tree list and to `vps_disk_budget`'s line items |
| L1 | TN-24 (j) | Bare word replaced |
| L2 | TN-3, TN-13, TN-16, seed | **Ruling 16.** The timer is renamed `qmn-news-calendar.timer` everywhere |
| L3 | Stack (`just` row); TN-1; TN-16 | `argparse` for recipe arguments only, never console scripts; the tier-1 assertion added |
| L4 | Structural Seed; TN-1; TN-16; Conventions | ONE path for recipe bodies: `qmn/deploy/justfile-recipes/` |
| adversarial's "one addition worth making" | TN-17; TN-18; TN-23 | **Ruling 22.** A `value-status` countersign is refused without the variable's EVIDENCE CITATION by `fp1`; one variable per call; it mints a config version and is journaled |

### regate-rubric-ambiguity (35)

| Finding | TN / section | Change |
| --- | --- | --- |
| C1 | TN-18; mint table | **Ruling 20.** Blanks PARTITION into `blocks-boot` / `blocks-role-live` / `blocks-soak`, tagged per mint-table row, with `blocks-soak` a GENERATED rule over the TN-23 checklist and the soak gate refusing to start otherwise |
| C2 | TN-4; TN-7; TN-3 | **Ruling 21.** A protection intent the journal room cannot take is written to a reserved extent under `/var/lib/qmx/state` sized by `disk_headroom_min`; if even that fails it is recorded UNDELIVERABLE and alarmed — never "held in memory" |
| C3 | TN-18; mint table; Parent annotations | **Ruling 22.** As adversarial M7 above |
| C4 | TN-19; TN-4; process-internals diagram | **Ruling 23.** The door layer runs a **slice-progress watch**; past the deadline by a declared factor it stops the keepalive with `WATCHDOG=trigger`, pushes on silent degradation and lets systemd restart; V1 cannot interrupt a non-cooperative callback — stated |
| H1 | TN-7; TN-15; Conventions | **Ruling 24.** The KSA level is folded **per enforcement scope** (global plus per stream), the scope part of the level identity and epoch; the effective level is the most restrictive covering scope; a `resume` names its scope; "level scope" added to the epoch list |
| H2 | TN-2; TN-4 | **Ruling 5.** As RH-4 |
| H3 | TN-2; TN-3; seed | **Ruling 25.** A reserved **SUPERVISOR `WriterId`**, a constant of the unit role, owns the boot-attempt and lifecycle stream under `/var/lib/qmx/state`; Compose may never re-issue it and the distinctness proof includes it |
| H4 | TN-3; TN-17 | **Ruling 11.** The inbox-to-published step is the operator's `hub_publish` power, signed and journaled, refusing `provenance = sandbox` at publish as well as at pull, with `just node-hub-publish` calling it; the diagram edge now matches a Rule |
| H5 | TN-3; TN-21; TN-13 | **Ruling 26.** A named **`sealed-archive`** room role per world is the sync target, read by the replay import port and the backup; the purge precondition is a verified copy there AND a verified off-host copy |
| H6 | TN-11; TN-9; Parent annotations | **Ruling 32.** The connection count is DERIVED from the roster; `SessionTopology`'s `required_connection_count = 2` recorded as a `qmf-venue` increment item to relax |
| H7 | Structural Seed; Capability map; TN-22 Binds | `promotion/` added; TN-22's Binds re-pointed to **`qmn/config` roster**; map rows added for promotion and activation and for seat hosting |
| H8 | TN-16; Stack | **Ruling 29.** `just` **pinned at v1.58.0, released 2026-08-03, web-verified 2026-08-28** and registered as an external tool; the bootstrap script installs uv, CPython, `just`, the container runtime, and clones at the pinned commit |
| H9 | TN-13; TN-15; Parent annotations | **Ruling 27.** Position and balance read-backs are CT-20 observation kinds mapped onto the existing seven AD-21 types by a **proposed CT-20 mapping-row addition**; the node adds no journal type |
| H10 | TN-4; TN-16; TN-18; TN-8; mint table | **Ruling 28.** `drain_window` and `watchdog_interval` minted — duration, configurable, `blocks-boot`; `TimeoutStopSec` and `WatchdogSec` RENDERED into the unit file by `node-install` |
| M1 | TN-6; TN-6 diagram | Arbitration sited once — the control-action dispatcher in `protection/`; the gate consumes its result; the diagram edge redrawn from that component |
| M2 | TN-6 | The compound-command outcome stated as a full table; all-rejected resolves `rejected-by-venue`, never `partially-executed` |
| M3 | TN-5; TN-10 | The interpretation cursor commits at slice end after the sinks flush; every re-folded fold is idempotent by observation identity |
| M4 | Ports table | `qmn.observability.NotificationChannel` minted with its two V1 implementations, plus `qmn.replay.ReplayImportPort` |
| M5 | TN-17; mint table | The evidence channel's access rule stated — loopback binding only, the consequence accepted — and `evidence_channel_budget` minted |
| M6 | TN-12 | The wizard carved out as a transient workstation-only holder so the VPS holder invariant stays checkable |
| M7 | TN-18 | `holdout_months` removed from the blank list and named an inherited ratified value |
| M8 | TN-23; Conventions | "refused" becomes **HELD as a standing protection intent and re-decided**; held is not refused, added to the Conventions row |
| M9 | TN-3; TN-16 | "TWO inbound crossings and no others"; the inbox write path named as a confined key-only SSH identity and reflected in the inbound posture |
| M10 | Deferred | The two confinement rows merged into one that enumerates the controls that actually exist in V1 |
| M11 | TN-10 | A deployment-tuple change invalidates the rung baseline: new live bindings blocked entry-side, alarm on silent degradation, exits and protection continuing per L39 |
| M12 | TN-4 | Counts every unrequested attempt within T regardless of stage; the stage is recorded for diagnosis, never for bucketing |
| M13 | TN-13; TN-16 | The nightly sample restore is its own `qmn-restore-sample` unit sharing the backup run's payload key; the monthly full is `qmn-restore-full` |
| M14 | Frontmatter | `A1-A37` becomes `A1-A47` |
| L1 | TN-9 | One attribution for the warm-up rider — AD-39's pre-live rider as `runbook.md:80` / DEC-0135 record it |
| L2 | TN-1 | `qmn` is "the distribution and import CODE NAME only" |
| L3 | TN-24 (j) | Rewritten |
| L4 | TN-19 | `seat_memory_ceiling` named where the mechanism is stated |
| L5 | TN-3 | The VPS provider declared deployment configuration |
| L6 | Conventions | The two senses of "provisional" distinguished |
| L7 | Frontmatter | `status: draft` kept per instruction; `provenance` records the re-gate |

### regate-operator-reconcile (6)

| Finding | TN / section | Change |
| --- | --- | --- |
| H1 | TN-16; TN-15; Stack | **Ruling 13.** The egress allow-list gains the container image registry or a vendored source; provisioning installs and pins a container runtime for the stack alone; a Stack row added for it; the node runs and passes without it |
| M1 | Capability map | Rows added for TN-5 (the loop and accumulator), TN-20 (promotion and activation) and TN-1 (identity, packaging, toolkit); TN-1 also added to the "Overall system architecture" row |
| L1 | — | No change needed: both "two days to a week" occurrences are faithful operator quotes that resolve to a week. Recorded, not applied |
| L2 | Assumption register | The authority line re-pointed at **the memlog's ruling entries as amended**, with the table named the current reconciled view |
| L3 | Frontmatter scope | "MIS-Live seam" becomes "MIS seam" |
| L4 | TN-9 | One line stating the injected-fault drills are discrete acceptance acts, distinct from the continuous unattended run |

### regate-fix-regression (3)

| Finding | TN / section | Change |
| --- | --- | --- |
| H-1 | Inherited Invariants, PRD §6 row | Corrected to "the shadow-lane **SEAM is explicit V1 node work** … while its **ML and training half is deferred**", the live-runtime guardrail unchanged |
| L-1 | TN-24 (j) | Bare word removed |
| L-2 | Stack | `just` now carries a pinned version and a verification date; the observability row and the new container-runtime row carry explicit "seed only, pinned at the implementation gate, registered in `DEPENDENCIES.md`" cells, so no row is literally blank |

## Not applied

**None.** Every finding of every severity from all five reviews is applied. Four were applied in the GATE-2 ruling's words rather than the review's, where the two differed:

- **regate-parent-consistency RC-1** — the review's fix said only "remove the UNKNOWN block from the entry-side enumeration"; **ruling 1** additionally settles that it is AD-36's **one non-control block**, refusing every command on the stream. The ruling's text is what the spine carries.
- **regate-rubric-ambiguity H6 / regate-parent-consistency RH-5** — the reviews proposed that the soak roster declare the demo binding only, with the live connection first opened at the week's end; **ruling 32** instead opens the live connection for sensing and recording as soon as credentials exist and makes the live binding wait on its own baselines. The ruling's text is what the spine carries.
- **regate-adversarial M1** — the review offered "declare `FAILURES.md` the sole home"; **ruling 34** additionally withdraws the registry membership row. Both applied.
- **regate-parent-consistency M3** — the review offered a choice: declare a `lifecycle-stop` trigger, or re-order the mint. Both taken — the mint is ordered after session close as the node's rule, and `lifecycle-stop` is recorded as a proposed CT-20 mint.

## New assumption ids

| Id | Assumption | Owning TN |
| --- | --- | --- |
| A40 | Two declared peer principals on the powers socket — operator and ops — by uid, neither the `qmx` service account | TN-17, TN-1, TN-20 |
| A41 | `/opt/qmx` as immutable per-commit trees plus an atomically flipped `current` symlink, pruned to a declared depth | TN-16 |
| A42 | The observability stack as its own unit and account, with its own storage, quota, loopback host-network binding, journal namespace and declared fourth secret holder | TN-15, TN-12, TN-16 |
| A43 | A reserved supervisor `WriterId`, a constant of the unit role, owning the boot-attempt and lifecycle stream | TN-2, TN-3 |
| A44 | A named `sealed-archive` room role per world as the sync target, the replay source and a purge precondition | TN-3, TN-21, TN-13 |
| A45 | The three-way blank partition blocks-boot / blocks-role-live / blocks-soak, tagged per row, blocks-soak generated | TN-18, TN-23 |
| A46 | A reserved protection-intent extent under `/var/lib/qmx/state` sized by `disk_headroom_min`, with UNDELIVERABLE as the honest terminal state | TN-4, TN-7 |
| A47 | The live connection opened for sensing and recording only from the moment credentials exist, so the live baselines accumulate during the soak | TN-9, TN-23 |

## Mechanical verification

- `lint_spine.py` over the workspace: `{"ok": true, "total_findings": 0}`.
- Scripted self-check: 25 TN blocks, ids TN-1..TN-25, each carrying exactly one **Binds** / **Prevents** / **Rule** — the one extra `**Rule:**` a naive scan sees after TN-25 belongs to the "Dependency direction" block, as the first re-gate already recorded; zero `<!--`; fences balanced; **six mermaid blocks, every one carrying at least one edge, with balanced brackets and no parenthesis, pipe or quote inside any node label**; banned vocabulary appearing only inside its own prohibition sentences; zero bare "stop-out" outside the prohibition; zero `Door 2`; zero `qmn <verb>` command forms; **every mint-table row carries a blank-effect tag**, and every configurable named in a TN resolves to a mint-table row — `news_calendar_max_staleness`, `drain_window`, `watchdog_interval` and `evidence_channel_budget` included; `value_status_required` present as the registry schema field.
- Web currency: `just` v1.58.0, released 2026-08-03, verified against GitHub `casey/just` on 2026-08-28.
- Final length: **1048 lines** (was 951). Frontmatter `status: draft` unchanged; `provenance` records "validation re-gate applied at desk (5 lenses, 107 findings, all applied)".
