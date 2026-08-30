# Cross-reference table — ARCHITECTURE-SPINE.md (QMA, 2026-08-28)

Built for the coherence pass. Every closed vocabulary and every count the spine states, read
against every other place the spine states it. `OK` = the readings agree after the pass;
`FIXED-n` = a divergence closed by this pass (see §Divergences). Rows **23–27** were closed by the
closing-editor cycle 1 and row **28** by cycle 2 (2026-08-28); rows **29–31** were closed by the
final-three divergence pass (cycle 3, applied 2026-08-28, verified verbatim 2026-08-29).

## 1. Hook vocabulary

| Item | Stated where | Members / count | Verdict |
| --- | --- | --- | --- |
| v1 hook verbs | AD-10 v1 registry | `tool`, `task_create`, `task_complete`, `ledger_append`, `memory_write`, `skill_write`, `artifact_register`, `experiment_register`, `env_create`, `env_remove`, `subagent_spawn`, `message_send`, `graph_transition`, `session_start`, `session_end`, `mission_start`, `mission_complete`, `plugin_activate`, `plugin_deactivate`, `routine_fire`, `hook_register`, `proposal_stage`, `proposal_apply` = **23** | OK — counted; "twenty-three" true in AD-10 registry and in Addability |
| Phase-less controls | AD-10 phase law, registry, per-control semantics, Conventions | `agent_stop`, `review_required` = **2** | OK |
| Hook events cited elsewhere | AD-8, AD-9, AD-11, AD-14, AD-18, AD-19, AD-20, AD-22, AD-24, AD-29 | `before_ledger_append`, `before_memory_write`, `before_tool`, `before_task_complete`, `before_artifact_register`, `before_hook_register`/`after_hook_register`, `before_proposal_stage`, `before_proposal_apply`, `before_message_send`, `before_routine_fire`/`after_routine_fire`, `after_tool` | OK — every one is a member of the 23 |
| `HookResult` decisions | AD-10 precedence, phase law, Conventions | `block_stop` > `deny` > `defer` > `ask` > `allow` > `observe` = **6**, now declared closed in the phase law; `updated_input` / `updated_output` are **fields**, never decisions | FIXED-23 |
| Legal set, `before_*` | AD-10 phase law | `allow`, `deny`, `ask`, `defer`, `observe`; `block_stop` refused at registration | OK |
| Legal set, `after_tool` | AD-10 phase law + `HookResult` | `allow` (may carry the `updated_output` field) and `observe`; nothing returned → `allow` | FIXED-23 |
| Legal set, every other `after_*` | AD-10 phase law | `observe` only | OK |
| Legal set, `agent_stop` | AD-10 per-control | `block_stop`, `observe`; nothing-returned and timeout → `observe` | OK |
| Legal set, `review_required` | AD-10 per-control | `deny`, `block_stop`, `observe`; nothing-returned → `observe`, timeout → `deny` | OK |
| `HookResult` field/phase rules | AD-10 `HookResult` | `updated_input` before_tool only; `updated_output` after_tool only; `injected_context`, `ledger_entry`, `verifier_ref` had **no** phase rule | FIXED-15 |
| Hook timeout resolution | AD-10 fail-closed + per-control, Conventions | `before_ledger_append` → `allow`; `agent_stop` → `observe`; every `after_*` → `observe`; every other `before_*` and `review_required` → `deny` = **three carve-outs** | FIXED-24 |
| Agent-authored narrowing | AD-11 | `decision`, `reason` only — and the registration validator now rejects all **five** non-`decision`/`reason` fields of AD-10's union: `updated_input`, `updated_output`, `injected_context`, `ledger_entry`, `verifier_ref` | FIXED-30 |
| `HookResult` field count | AD-10 union vs AD-11 validator | 7 fields = `decision`, `reason` + the 5 above; AD-11's enumeration is closed and matches | OK — counted after FIXED-30 |

## 2. State machines

| Vocabulary | Owner | Members | Cross-checks | Verdict |
| --- | --- | --- | --- | --- |
| Task / Mission state | AD-12 | `pending`, `ready`, `running`, `blocked`, `unknown`, `done`, `failed`, `cancelled` = 8 | AD-13 "exactly one terminal state"; AD-12 "proposed terminal transition" — **terminal subset never enumerated** | FIXED-3 |
| `JobHandle` state | AD-17 | `queued`, `running`, `done`, `failed`, `cancelled`, `aborted`, `unknown` = 7; terminal = `done`, `failed`, `cancelled`, `aborted` (4); non-terminal = 3 | AD-12 cross-references, does not restate | OK |
| Job→Task mapping | AD-17 | queued→running, running→running, done→done, failed→failed, aborted→failed, cancelled→cancelled, unknown→unknown | total over all 7; AD-12 defers to it | OK |
| `validation_state` | AD-18 | proposed, validated, admitted, superseded, invalidated, expired, contradicted = 7 | AD-8 Memory retention names the 5 resting values | OK |
| `MessageKind` | AD-20 | handoff, reply, notify, review_request, status, question, approval_request = 7 | `approval_request` is AD-10's single human-approval channel | OK |
| `DeliveryState` | AD-20 | `delivered`, `queued`, `woke`, `deferred`, `dead_letter` = 5 | all five in the Conventions token list; `deferred` used by quiet hours; `dead_letter` by AD-7 and the Deferred lead-flag row | OK |
| Handle kinds | AD-14 | BacktestHandle, ExperimentHandle, TradeLogHandle, StrategyHandle, KnowledgeHandle, MarketDataHandle = 6 | AD-1 homes the vocabulary in `qma-core`; Conventions exempts them from snake_case | OK |
| `ModelClass` | AD-15 | `REASONING_HIGH`, `WORKHORSE_GENERAL`, `CODING_HIGH`, `FAST_CHEAP` = "exactly four" | Conventions casing exception | OK |
| Node kinds | AD-13 | task, conditional, parallel_branch, join, approval_gate, human_gate, deterministic_script, loop, agent, artifact_dependency = 10 | Task-emitting 3 + daemon-evaluated 7 = 10 | OK |
| `ExecutionEnvironment` kind | AD-17 | local, docker, remote_container, remote_host, browser, desktop = 6 | AD-25/AD-28/Deferred use the same tokens | OK |
| `network` | AD-28 | `none`, `allowlist` = "exactly two" | OK |
| Principal class | AD-24 | `operator`, `machine` = "exactly one class" per connection | OK |
| Routing policy | AD-15 | failover, weighted_round_robin, quota_lowest, fill_first | in the token list, absent from the Conventions closed-vocabulary enumeration | FIXED-18 |
| Edit kind | AD-22 | prompt, memory, skill, toolset, worker_template, hook, graph_template, loop, role = 9 | AD-22 Binds line names the same 9 | OK (enumeration gap → FIXED-18) |
| AD-26 scope | AD-26 | global, desk, role, quant, mission, plugin, execution_environment, routine = 8 | expresses WakePolicy (quant), max_in_flight (execution_environment), routine caps (routine) | OK |
| Session axes | AD-14 | execution model (dialogue/rlm), attachment (attached/detached), autonomy (interactive/semi/autonomous) | AD-6 fold list and Vocabulary say the **record carries all three**; AD-5/AD-14 say attachment is client state only | FIXED-21 |
| Typed refusals | 13 named | NoEnvironment, NoEligibleDeployment, NoEligibleReviewer, NoMemoryProvider, OperatorPrincipalRequired, ProhibitedMoneyPathTool, CredentialOutOfScope, SlugUnavailable, StaleSnapshot, ProvenanceShapeMismatch, UnknownHostRequest, NonLoopbackProxy, UnauthenticatedProxy | AD-5's mismatched-attach refusal was the only unnamed one; AD-18 did not name `NoMemoryProvider` | FIXED-16, FIXED-17 |

## 3. Stores, folds, backup

| Question | AD-6 closed store list | AD-8 table | AD-27 backup | Verdict |
| --- | --- | --- | --- | --- |
| Journal-derived projections | per-scope event streams; mailboxes + delivery state; operator approval queue; Task Graph state; Session and Agent records; desk ledger views; ledger quarantine stream; the definition store (16 registries) | rows for journal, Mission/Task Graph, Session/Agent, quarantine, definition store, mailbox | covered by the journal's own backup | OK |
| Declared independent stores | 3 ledgers, artifact store, telemetry store, staging store, MemoryProvider store = 7 (+ journal = 8 durable) | ledger, artifact, staging, telemetry, memory rows | "seven daemon-owned" = journal + 3 ledgers + artifact + staging + telemetry; MemoryProvider named as the eighth, provider-owned | OK — counted |
| Definition-store members | Desk, Role, Quant, Routine, `ExecutionEnvironment` declarations, toolset, worker_template, Skill, Loop, Graph Template, plugin install, Deployment, Tool, tool_adapter, hook registrations, AD-26 variables = 16 | identical 16 | n/a | OK (also identical in the Vocabulary row and in AD-6's v1 fold list) — `ExecutionEnvironment` declarations added by FIXED-28 |
| Announcement law | "Every append to a **declared store** emits a journal event carrying the record's `fp1`" | telemetry row: bounded, separate store, `correlation_id` shared | journal kept forever, never trimmed | **Contradiction**: the telemetry store is a declared store, so every trace would mint a keep-forever journal append against AD-23 and P-12 → FIXED-1 |
| Record law vs the telemetry exemption | AD-6 record law now stamps the announcement `journal_seq` only "in every store the announcement law binds"; a telemetry record carries `occurred_at`, `recorded_at`, no `journal_seq`, ordered by `recorded_at` and `correlation_id` alone | AD-8 Telemetry row (separate store, `correlation_id` shared) and the Event-journal crossing rule, which binds **evidence** records only | telemetry backed up, never trimmed of trajectories | **Contradiction left by FIXED-1**: the record law still demanded a `journal_seq` on a record whose store emits no announcement → FIXED-29 |
| Operator approval queue owner row | declared in AD-6, folded with mailbox delivery state | AD-8 Mailbox row does not name it, though AD-23's trim rule does | n/a | FIXED-14 |
| v1 folds | desk ledger views; Task/Mission/Session/Agent state; mailbox delivery + ack cursors; deployment and provider health; staging and application state; each definition-store registry — all with `journal_seq` ordering, `as_of` over `recorded_at`, equal instants by ascending `journal_seq` | same | n/a | OK; per-scope streams and the quarantine stream are declared filtered projections, not folds |
| Journal reference law | AD-6 record law stamps every durable record in an announcement-bound store with its announcement `journal_seq` | AD-8 Event-journal crossing rule permits exactly that one reference and no other, the daemon allocating the seq before the record write — and it binds **evidence** records, which telemetry is not (AD-23) | n/a | FIXED-25, re-scoped by FIXED-29 |
| Definition-store write paths | AD-6 lists Role (`role.base`, `role.overlay`) as a definition-store projection over its own `noun.verb` journal events | AD-8 definition-store row: "daemon only, as journal projections; agents propose edits only as AD-22 RefinementProposals" | n/a | AD-22 called `role.base` "versioned only by a human commit" — a VCS write path with no journal event, no store row and no wire command, and no AD-24 gate → FIXED-31: `role.set_base` (`operator` principal) recording `role.updated` |
| Trimmable | mailbox delivery projection, telemetry store — inside AD-26 windows by daemon job, outside them by `operator` act | same | never the journal, ledgers, artifact store, staging store, quarantine stream, trajectories | OK |

## 4. Leases, resume, attempts

| Fact | Stated where | Verdict |
| --- | --- | --- |
| `dispatch_lease` per Task | AD-9, AD-8, AD-10, AD-12, Conventions, Vocabulary | OK |
| `environment_lease` per environment slot | AD-17, AD-10, AD-12, Conventions | OK |
| `quant_ledger_lease` per Quant | AD-9, AD-8, Conventions, Vocabulary | OK |
| `defer` releases `environment_lease`, retains `dispatch_lease` | AD-10 | OK |
| Resume from `defer` writes no `reassigned`, `attempt_no` unchanged | AD-9 | OK — already reconciled (memlog "AD-9/AD-10 REASSIGNMENT vs RESUME"); any change of lease holder is a reassignment |
| `unknown` Task holds both leases | AD-12, AD-17 | OK |
| `attempt_no` vs `retry_index` | AD-9 counts reassignments inside one Task; AD-13's `retry_index` counts prior Tasks in the `attempt_of` chain and never `attempt_no` | OK |
| "lease" never bare | Conventions | bare at AD-5 ("lease expiry"), AD-13 ("AD-9's lease", "hold no lease") | FIXED-19 |
| `before_ledger_append` author check | AD-9 (gate), AD-8 (who-may-write), AD-10 (`ledger_entry`) | AD-9 named a **daemon-written** `reassigned` entry the lease check would refuse → FIXED-26: exactly two daemon-authored exemptions (`reassigned`; a `ledger_entry` returned by `before_task_complete` / `review_required`), both `authored_by: daemon`, both still schema-validated, set closed in AD-9 and echoed in AD-8 |

## 5. Counts stated in prose

| Count | Where | Literal check |
| --- | --- | --- |
| twenty-three daemon-owned verbs | AD-10 ×2 | 23 ✔ |
| exactly two phase-less controls | AD-10, Conventions | 2 ✔ |
| exactly four `ModelClass` values | AD-15 | 4 ✔ |
| six capability-ladder rungs | AD-16 | 6 ✔ |
| exactly six `evidence_confidence` entries | AD-19 ×2 | 6 ✔ |
| exactly two `network` values | AD-28 | 2 ✔ |
| seven daemon-owned durable stores / the eighth | AD-27 | 7 + 1 ✔ against AD-6 |
| exactly one record type in staging | AD-22 | ✔ |
| the five Desks / five Roles / five `desk_slug`s / five plugin prefixes | AD-7, Conventions, Structural Seed | 5 / 5 / 5 / 5 ✔ (Roles read Product Manager, not PM) |
| 26 wire nouns = 9 commands + 7 queries + 10 events | AD-5 | 26 ✔ — stated as the **seed** of a closed-and-addable registry, so FIXED-31's `role.set_base` command and `role.updated` event add to it without breaking the count |
| the five non-`decision`/`reason` `HookResult` fields | AD-11 | 5 ✔ against AD-10's seven-field tagged union |
| exactly two AD-23 daemon-job trims | AD-5, AD-23, AD-24 | 2 ✔ (mailbox delivery projection, telemetry store) — untouched by FIXED-29 |
| exactly nine `_ref` exceptions | Conventions | **8 of 9 hold; `producer_id` is a tenth the envelope carries** → FIXED-2 |
| D1..D23 in frontmatter `binds` | frontmatter, Capability map | 23 ✔ |
| 29 ADs, ids stable and monotonic | body | 29 ✔ |
| 22 Deferred rows | Deferred | 22 ✔ |
| three fail-closed carve-outs | AD-10 heading + body, Conventions | 3 ✔ (`before_ledger_append`, `agent_stop`, every `after_*`) |
| exactly two daemon-authored ledger exemptions | AD-9, AD-8 | 2 ✔ |

## 6. Diagrams vs their governing AD

| Diagram | Governing AD | Check | Verdict |
| --- | --- | --- | --- |
| Dependency flowchart | AD-2 | UI→wire; WORKER→wire only; PLUGIN→wire+core; DAEMON→wire+core+qmf libs; wire→core; core→qmf-core | OK — plugin worker half rides the PLUGIN node, as AD-2 states |
| Container flowchart | AD-6, AD-14, AD-22, AD-29 | ORG/COG/CTRL/EXE/RT/REC/TEL; scheduler present; **staging store absent from REC** though AD-6/AD-8 declare it and the Paradigm table and Structural Seed both carry it | FIXED-13 |
| ERD | AD-7, AD-9, AD-5 | Desk 1:N Role/Quant; exactly one lead; Role 1:N Quant; Quant 1:1 Mailbox; Quant 0..1 Quant Ledger; Quant 1:N Mission; Mission 1:N Task; Task 1:1 Task Ledger; Task 1:N Session; Task 1:N Agent; Agent N:1 Session; Agent 1:N Subagent; Experiment 1:1 Experiment Ledger | OK — matches AD-7 cardinalities and AD-5's scope_path nesting |
| Deployment flowchart | AD-25, AD-28, AD-5 | workstation default; Docker workers; remote/sandbox/computer-use all dial out; no trading-node edge, barrier label only; one `qmb` job per environment | OK |

## 7. Tables vs the ADs

| Table | Check | Verdict |
| --- | --- | --- |
| Paradigm layer table | `qma-daemon` Contains = the 13 Structural-Seed packages ✔; Extensions cell = AD-1's 8 multi points + 5 singleton bindings ✔; `qma-core` Contains omits the plugin contribution surface AD-1 homes there | FIXED-12 |
| Inherited Invariants | parent ids written bare in three rows; L17 row binds AD-22, which no longer reaches a registry zone; L31 row omits AD-2; money/time row cites AD-8 and omits AD-3 | FIXED-7, FIXED-8, FIXED-9, FIXED-10 |
| Capability map | every D row's ADs declare that D in their Binds line, except D10→AD-24 (AD-24 declares D19 only) | FIXED-11 |
| Deferred | all 22 rows resolve against the AD they cite (AD-25, AD-7/AD-20, AD-18, AD-19, AD-22, AD-17/AD-25, AD-14/AD-26, AD-21, AD-16/AD-17, AD-20, AD-14, AD-5/AD-7/AD-26, AD-9, AD-7, AD-12, AD-14, AD-13, Cut table, AD-26/AD-27, AD-6/AD-8/AD-23, AD-8/AD-14, —) | OK; `Envelope` written bare in the lead-flag row → FIXED-19 |
| Cut outright | no row contradicts an AD; the loop-registry and execution-tool cuts match AD-13 and AD-16 | OK |
| Vocabulary | rows agree with AD-7, AD-9, AD-13, AD-14, AD-15, AD-17, AD-18, AD-20, AD-21, AD-22, AD-24, AD-29; Mission Compiler and Mission Director have no row though AD-12 mints both and its Prevents line turns on the second | FIXED-20 |
| Conventions | closed-vocabulary enumeration reads as closed while omitting six vocabularies the spine mints; `_ref` whitelist short by one; own-identity clause false of `id`; carve-out count and the `authored_by` shape re-synced with AD-9 / AD-10 | FIXED-2, FIXED-18, FIXED-23, FIXED-24, FIXED-26 |
| Stack | SQLite floor wording matches AD-6 (3.51.3 or the 3.50.7 backport); every row carries a version or a stated `[UNPINNED …]` | OK |

## 8. Closed verbs and `_ref`

| Rule | Check | Verdict |
| --- | --- | --- |
| admit / apply / promote | every "promot*" occurrence is L17's live-zone act, performed outside QMA; AD-18 has no `promote` port operation; AD-22 says "applied, never promoted" | OK |
| `_id` vs `_ref` | Citation is `source_ref`/`snapshot_ref`; Mission/Task Graph crossing is `_ref`; whitelist = 9 named | FIXED-2 (ten, with `producer_id`) |

## 9. Operator-principal authority

AD-24's list is declared "the sole authority on which commands require that principal". Commands
the spine elsewhere restricts to `operator` and the list did not name: answering an
`approval_request` in the daemon-held operator approval queue (AD-6, AD-10, AD-12); a plugin
**reload** (AD-21 names install, enable *or reload*); a `desk.moved` membership change (AD-7);
Routine authoring (AD-29); and setting a registered AD-26 variable — which additionally had **no
write path at all**, since the variable registry is a definition-store projection and AD-22's
closed edit-kind list has no `variable` kind. → FIXED-4, FIXED-5.

Closing cycle 1 split that write path again: AD-26 now declares a `home` per variable, so a
`registry`-homed value moves by `variable.set` while a **record-homed** value moves only by its own
record's operator-principal write command. Two of those commands were absent from AD-24's
sole-authority list — an `ExecutionEnvironment` declaration write (AD-17) and a Mission
`approval_route` write (AD-12) — and are now on it; `WakePolicy` was already covered by the Quant
record row. → FIXED-27.

Closing cycle 2 gave that first command something durable to write: the `ExecutionEnvironment`
declaration was the only AD-24-gated, AD-26-homed record with no store. It is now the definition
store's 16th projection, folded from its own `noun.verb` journal events like every other.
→ FIXED-28.

Cycle 3 found the last hole in the same list. `role.base` — the capability ceiling every Agent is
narrowed from (AD-16) — sat in the definition store per AD-6 and AD-8, yet AD-22 said it was
"versioned only by a human commit" and AD-24's sole-authority list named no Role write. A wire
command writing `role.base` would therefore have been accepted from a `machine` principal. AD-22
now routes that write through an `operator`-principal `role.set_base` command recording a
`role.updated` journal event, and AD-24's closed list carries "a `role.base` write (AD-16, AD-22)"
after the `desk.create` / `quant.create` entry. → FIXED-31.

## 10. Tags inside ADs

One `[UNSTUDIED]` tag remained inside AD-13. Task law: an AD carries rules only. → FIXED-6;
the tag legend now records that none remains.

## Divergences fixed (31)

1. AD-6 — announcement law scoped to evidence stores; telemetry store exempt (AD-23, P-12).
2. Conventions/AD-5 — `_ref` whitelist widened to ten with `producer_id`; own-identity clause made true of `id`.
3. AD-12 — terminal Task states enumerated (`done`, `failed`, `cancelled`).
4. AD-24 — human-gate list widened to five further operator-only commands.
5. AD-26 — a registered variable's write path stated (`operator` command, `variable.set` event, never an AD-22 edit).
6. AD-13 — `[UNSTUDIED]` tag replaced by a rule sentence pointing at its Deferred row; legend updated.
7. Inherited Invariants — three rows write parent AD ids as `parent AD-n`.
8. Inherited Invariants — L17 row binds AD-24, AD-25 (not AD-22).
9. Inherited Invariants — L31 row binds AD-2, AD-3, AD-4.
10. Inherited Invariants — money/time/identity row binds AD-3, AD-6 clock law.
11. AD-24 — Binds line reads D10, D19.
12. Paradigm layer table — `qma-core` Contains names the plugin contribution surface.
13. Container diagram — RECORD node names the AD-22 staging store.
14. AD-8 — Mailbox row names the daemon-held operator approval queue.
15. AD-10 — phase rules stated for `injected_context`, `ledger_entry` and `verifier_ref`.
16. AD-5 — mismatched-attach refusal named `CursorScopeMismatch`.
17. AD-18 — names `NoMemoryProvider`.
18. Conventions — closed-vocabulary enumeration completed and declared owned by its AD.
19. AD-4, AD-5, AD-12, AD-13, AD-21, AD-23, Deferred, Conventions — bare `lease`, `envelope` and `attach` qualified; "the relevant lease" sanctioned as the one collective form.
20. Vocabulary — Mission Compiler / Mission Director row added.
21. AD-6, AD-14, Vocabulary — the Session record carries execution model and autonomy; attachment is client state, never persisted.
22. Inherited Invariants — L39 row binds AD-5, AD-6, AD-9, AD-10, AD-21, AD-25 and Conventions, the six places that actually discharge it.

**Closing-editor cycle 1 (2026-08-28):**

23. AD-10 phase law — `updated_input` and `updated_output` declared **fields of `HookResult`, never decisions**; the decision vocabulary is exactly the six precedence values; `allow` made legal on `after_tool` and is the nothing-returned resolution there. Conventions names the six decisions among the closed vocabularies.
24. AD-10 fail-closed — a timeout on any `after_*` event resolves to `observe` annotated `hook_timeout` rather than synthesizing a phase-illegal `deny`; fail-closed is now scoped to `before_*` plus `review_required`; heading and the Conventions row read **three carve-outs**.
25. AD-8 — the Event-journal crossing rule permits an evidence record's own announcement `journal_seq` stamp (AD-6 record law) and no other journal reference, with the seq allocated before the record write so the record stays append-only.
26. AD-9, AD-8 — `reassigned` is a **daemon-authored** entry carrying `authored_by: daemon`; `before_ledger_append`'s lease check has exactly two closed author exemptions (that entry kind and a hook-returned `ledger_entry`), both still schema-validated; AD-8's who-may-write cell and owner cell, AD-9's entry shape and the Conventions `_ref` whitelist all carry the `daemon` author.
27. AD-26, AD-24 — one write path **per variable**: every registered variable declares a `home` of `registry` or a named owning record type; `variable.set` is refused on a record-homed name; record-homed values (`max_in_flight`, a Mission `approval_route`'s `ask_timeout` / `on_timeout`, `WakePolicy` quiet hours and max wakes) move only by their record's operator-principal write command, and AD-24's closed human-gate list gains the `ExecutionEnvironment` declaration write and the Mission `approval_route` write. A plugin may ship a record-homed default and no `registry`-homed value.

**Closing-editor cycle 2 (2026-08-28):**

28. AD-6, AD-8, Vocabulary — `ExecutionEnvironment` declarations (AD-17, AD-26) added to the closed store list, to AD-6's v1 fold list, to AD-8's definition-store row and to the Vocabulary row. The record AD-24 gates and AD-26 homes now has a store: a definition-store projection over its own `noun.verb` journal events with `journal_seq` as ordering key. The definition store reads **16** members, identically, in all four places.

**Final-three divergence pass (cycle 3, applied 2026-08-28, verified verbatim 2026-08-29):**

29. AD-6 record law — the announcement `journal_seq` stamp is required only "in every store the announcement law binds"; a telemetry record, whose store that law exempts (FIXED-1), carries `occurred_at` and `recorded_at`, **no** `journal_seq`, and is ordered by `recorded_at` and its `correlation_id` alone (AD-23). Closes the last half of FIXED-1: without it the record law demanded a sequence number no telemetry append ever allocates, forcing one keep-forever journal entry per span. AD-8's Event-journal crossing rule already binds evidence records only, so it needed no change.
30. AD-11 — the registration validator's reject list is closed at **five**: `updated_input`, `updated_output`, `injected_context`, `ledger_entry` **or `verifier_ref`** — "the five non-`decision`/`reason` fields of AD-10's tagged union, enumerated here so the check is closed". `verifier_ref` (added to the union by FIXED-15) had been left out, so a mission-scoped agent-authored hook on `before_task_complete` / `review_required` could have named its own completion verifier — the privilege escalation AD-11's Prevents line exists to close.
31. AD-22, AD-24 — `role.base` is a definition-store record like every other (AD-6), written only by an `operator`-principal `role.set_base` wire command recording a `role.updated` journal event, never by an agent, a plugin, a hook or any other `machine` principal, and never by the AD-22 pipeline, whatever a human commits upstream of that command; `role.overlay` stays proposal-editable. AD-24's closed human-gate list gains "a `role.base` write (AD-16, AD-22)". Replaces the VCS-shaped "versioned only by a human commit", which had no journal event, no store row, no wire command and no operator gate.

## Tags remaining inside an AD

**0.** The word appears only in the tag legend under *Invariants & Rules*, which states that none remains.

## Lint after the cycle-3 pass

Re-run 2026-08-29 against the applied fixes:

`{"ok": true, "spine": "ARCHITECTURE-SPINE.md", "total_findings": 0, "by_severity": {}, "findings": []}`
