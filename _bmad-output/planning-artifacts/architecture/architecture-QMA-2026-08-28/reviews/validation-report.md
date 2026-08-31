# Validation report — ARCHITECTURE-SPINE.md (QMA, 2026-08-28)

*Rewritten 2026-08-28; closed 2026-08-29. The 2026-08-28 versions of this file first over-claimed a clean result, then recorded the truthful not-dry state. The 2026-08-29 closing pass below is the final record.*

## 1. Verdict

**Export-ready (closed 2026-08-29).** The final full-spine verification returned **zero** divergences: verified = true, dry = true, remaining = 0. The bar was the strict one used throughout — a finding exists only where two careful builders reading the same sentence would build incompatible systems. Six surgical fixes closed the last divergences between the 2026-08-28 pause and this verdict: AD-6 (telemetry records carry no `journal_seq`), AD-11 (the validator also rejects `verifier_ref`), AD-22 + AD-24 (`role.base` is written only by an `operator`-principal `role.set_base` command), AD-9 + AD-8 (`unknown_tail` is the second daemon-authored Task Ledger entry kind), AD-8 (the definition store's single closed exception for AD-11 mission-scoped hooks), and AD-15 + AD-10 (`model_family` is optional, operator-assigned, review-ineligible while unset). Lint: 0 findings. The spine may go to the documentation factory (next-session prompt 12).

## 2. What was validated, and how

- **Validation pass 1** ran two rounds and **was not dry**: 27 residual findings remained when it stopped.
- **Validation loop 2** ran four rounds, at **16, 15, 13 and 13** findings, and **was not dry** either.
- **The coherence-close run** did one whole-document coherence edit first — the whole spine read against itself, 22 inconsistencies fixed, the working table left at `reviews/xref-table.md` — and then divergence-only verification, which found 5 findings after the coherence edit, 1 after closing cycle 1, and 3 after closing cycle 2. It **ended dry = false**, with those three standing: AD-6's telemetry `journal_seq`, AD-11's `verifier_ref` gap, and AD-22's `role.base` write path.
- **Those three were then applied surgically** — each finding's own replacement text, nothing else in the spine touched. All three edits are in the file now, and are recorded in §3 under AD-6, AD-11 and AD-22.
- **Final verification (2026-08-28): verified = true, dry = false.** Both verifiers ran and returned; no verifier died twice, so this report is a real reading of the spine, not a gap being reported as silence. Two high findings stand, listed verbatim in §5.
- The bar was deliberately narrow: a wording preference or a missing example was not a finding, only a place where the spine tells two builders two different things. The mechanical lint is clean (0 findings, JSON at the end) — that means the file's structure is sound; it does not read meaning, which is why it says nothing about the two findings below.

- **Closing pass (2026-08-29):** the three standing divergences applied; a full-spine verification then found two more (`unknown_tail`; the definition store's AD-11 exception), applied; the next found one (`model_family` required vs optional), applied; the last found **zero**. Sequence of divergence counts across the whole validation: 27 → 16 → 15 → 13 → 13 → 5 → 1 → 3 → 2 → 1 → 0.

## 3. Material rule changes made during validation, by AD

- **AD-1** — contribution surface closed: 8 multi points, 5 singleton keys; the ContextCompiler is a default binding one plugin may replace, not a registration; an unbound key errors only when something loaded needs it; the phantom `command` and `ui_view` points removed.
- **AD-2** — the plugin's worker half is covered by the plugin node in the diagram; the two QMF edges narrowed to read-and-calculate with an enumerated default-deny surface.
- **AD-3** — one content-addressing construction only, tree digests included; a second hash scheme is never defined.
- **AD-4** — the RLM kernel lives inside the Analysis worker's container, never in the daemon; hooks and verifiers run in the daemon.
- **AD-5** — dial-out corrected (no inbound port on the *deployed* side); `scope_path` order fixed with Session between Task and Agent; `producer_id` minted on the envelope; `correlation_id` origins split from operator-gated acts; the one unnamed refusal named `CursorScopeMismatch`.
- **AD-6** — the store list closed and completed (definition store named, 16 members, quarantine stream, operator approval queue, `ExecutionEnvironment` declarations); the announcement law scoped to evidence stores; every fold given its contract; sole-writer restated as a write law with the SQLite claim checked against the primary source; clock law split wall-clock from duration. **Closing fix applied:** the Record law now demands an announcement `journal_seq` only in the stores the announcement law binds, and states the telemetry record's own shape — `occurred_at` and `recorded_at`, no `journal_seq`, ordered by `recorded_at` and `correlation_id` (AD-23).
- **AD-7** — a Subagent is a leaf; the lead-flag assumption resolved from the operator's own ruling; `desk_moved` renamed `desk.moved`; `ActorId` made opaque to every consumer; the fifth Role reads Product Manager.
- **AD-8** — a named writer per ledger; memory retention restated against the real vocabulary; the artifact row widened to the citation copy; the mailbox row names the operator approval queue; the journal crossing rule permits a record's own `journal_seq` stamp and nothing else.
- **AD-9** — three named leases replace one bare "lease"; `reassigned` is a daemon-authored entry; a resume from `defer` writes none; the append gate has exactly two closed author exemptions.
- **AD-10** — phase law amended then narrowed; two phase-less controls; six decisions, declared closed; `updated_input`/`updated_output` are fields, never decisions; fail-closed carve-outs went one to two to three; ask routing reconciled with the approval route; the registry widened to 23 verbs.
- **AD-11** — the undefined `stop` field deleted from the result union; the undefined mission audit record replaced by a named wire query. **Closing fix applied:** the registration validator's reject list is closed at five fields — `verifier_ref` added to `updated_input`, `updated_output`, `injected_context` and `ledger_entry` — so an agent can never name its own completion verifier.
- **AD-12** — `approval_route` defined and then made satisfiable (a Quant's mailbox, or the reserved `operator` route); terminal Task states enumerated; a Mission owned by exactly one Quant; Mission Compiler and Mission Director homed.
- **AD-13** — compilation law and its two gates stated; task and agent node kinds defined; `retry_index` separated from `attempt_no`; the last unstudied tag replaced by a rule.
- **AD-14** — the undefined "admission handle" replaced by a `JobHandle`; `host_request` specified as a wire family; `StrategyHandle` mutates nothing; the invented "QMA zone" removed; the Session record carries two axes, not three.
- **AD-15** — operator rulings applied: QMA never pools accounts, a proxy Deployment must bind loopback, OpenCodex sits behind the Deployment contract and not behind the Credential Broker.
- **AD-16** — the effective capability set is an ordered narrowing computed once at spawn; `toolset` and `tool_adapter` minted as records and split from their binding; "settings" replaced by a real store.
- **AD-17** — UNKNOWN reconciled with the lease law; terminal `JobHandle` states named and the job-to-Task mapping made total.
- **AD-18** — the admission seam with AD-22 closed; the refusal named `NoMemoryProvider`.
- **AD-19** — corpus provenance resolved from source; search closed to literal and locator-based; the evidence label made buildable; the citation copy's gate named.
- **AD-20** — `WakePolicy` owned by, and scoped to, the Quant record.
- **AD-21** — a load-time refusal law minted, so every "hard startup error" in this spine has one shape.
- **AD-22** — staging holds exactly one record type; edit kinds widened to nine with `toolset`; every application needs an operator principal; the registry-reachability claim corrected. **Closing fix applied:** `role.base` has exactly one write path — an `operator`-principal `role.set_base` wire command recording a `role.updated` journal event, never a VCS commit and never a `machine` principal — with the matching row added to AD-24's closed human-gate list.
- **AD-23** — retention split: the event journal is evidence and never trimmed; only two bounded streams trim; a trim may never remove an unacked message or an unanswered approval.
- **AD-24** — the money-path contradiction closed; the human-gate list completed and declared the sole authority; Binds reads D10 and D19.
- **AD-25** — the live boundary restated: promotion is a human act performed outside QMA; the Windows VPS is planned, not provisioned.
- **AD-26** — self-contradiction fixed; phantom variables removed; a write path minted, then split per variable with a declared `home`.
- **AD-27** — the parent's full-restore rehearsal restored; backup contents restated as the seven daemon-owned stores, with the eighth named as provider-owned.
- **AD-28** — no rule changed; its environment-kind tokens re-cased to `remote_container` and `remote_host` to match the casing law.
- **AD-29** — the Routine record carries the Goal it supplies, not a template it instantiates.
- **Inherited Invariants** — five traceability rows fixed: parent ids written as parent ids, and the L17, L31, L39 and money/time rows now bind the ADs that actually discharge them.
- **Conventions** — the closed-vocabulary list completed and given owners; the `_ref` whitelist went 4 to 9 to 10; token casing minted; every bare "lease", "envelope" and "attach" qualified.
- **Vocabulary, Paradigm table, Structural Seed, Stack, Deferred, and the diagrams** — caught up with the ADs: the SQLite floor aligned, three Deferred rows given testable revisit conditions, the three remote edges reversed to dial-out, the ERD given its Task-to-Session edge and the correct Quant Ledger cardinality, and the container diagram given the staging store.

## 4. How every former [ASSUMPTION] / [UNVERIFIED] tag was disposed

| Was tagged | How it ended |
| --- | --- |
| AD-15 multi-account pooling under provider terms | **Resolved from an operator ruling**: QMA never pools; pooling, where it happens, is his own proxy under his own account terms, outside QMA. |
| AD-15 unauthenticated loopback proxy | **Resolved from an operator ruling**: permitted as the v1 default, carried by the registered variable `proxy.allow_unauthenticated_loopback` plus startup evidence. |
| AD-7 desk-level lead Quant | **Resolved from the operator's own words** ("task-level ledgers confirmed correct; desk-level quant ledgers OK"). The half he never ruled — one lead flag per desk, and the lead's mailbox as catch-all — moved to the Deferred row *"One lead flag per desk…"*. |
| AD-14 RLM performance envelope | **Moved to Deferred**: the rule stands, the doubt sits in *"RLM kernel performance envelope"*, now naming `rlm.fanout_cost_ceiling_usd` as its testable threshold. |
| AD-19 corpus shape | **Resolved from source** — the operator's own STRATS plain-file library. The indexing question sits in the Deferred row *"Knowledge indexing"*. |
| AD-13 graph engine | **Retagged, then removed**: a provenance note, not a doubt; the implementation choice sits in the Deferred row *"Graph engine implementation choice"*. |
| AD-21 in-house threading node | **Moved to Deferred**: only he can supply its spec, so its shape and contribution point sit in *"The in-house threading node's shape…"*. |
| The word "plugin", and "RLM kernel" | **Resolved from source**: the glossary ties the parent's ban to QMB and no law bans "plugin". Retagged adopted in all three places; the surfaced-conflict tag class is gone from the spine. |
| AD-25 Windows VPS | **Resolved as planned, not provisioned**: the rule stands and the Deferred row registers it only once an environment record exists. |
| AD-26 "sticky limit" / "budget hint" | **Deleted** — phantom variables with no owning AD. |

Result: **no assumption, unverified, unstudied or surfaced-conflict tag remains inside any AD.** The only tag class in use is `[ADOPTED 2026-08-28]`, plus the legend that says so and two `[UNPINNED …]` rows in the Stack table.

## 5. What remains open

**None meets the divergence bar** (last sweep 2026-08-29, zero findings). Three silences the verifier noted and deliberately excluded, recorded here for the documentation factory: AD-26's parenthetical list of record-homed values does not name `model_family` or the Routine max-concurrent cap (the list is not declared closed; AD-24 gates `model_family` separately); AD-7 says "any `desk_slug` beyond the five" while `desk_slug` is not a declared closed vocabulary (the Deferred row contemplates fewer desks, never more); the `to` field type of an `approval_request` routed to the daemon-held operator queue is unstated. Each is silence, not two instructions.

## 6. The ADs, and the final counts

| # | Title | # | Title |
| --- | --- | --- | --- |
| AD-1 | Contract-hub packages, namespaces, port cardinality | AD-16 | Tool Registry, capability ladder, and the tool that does not exist |
| AD-2 | Dependency direction | AD-17 | Execution environments, compute placement, JobHandle |
| AD-3 | No parallel base for anything qmf-core defines | AD-18 | Memory: the contract now, the engine later |
| AD-4 | Daemon language: one Python runtime, workers over the wire | AD-19 | Knowledge: a read-only corpus and two different confidences |
| AD-5 | The daemon-to-UI wire contract | AD-20 | Agent Bus: durable, addressed, non-authoritative |
| AD-6 | One journal, one writer, one clock | AD-21 | Plugin model: reversible code, declared-reversible data |
| AD-7 | Ontology, cardinality and address grammar | AD-22 | Admission gate: nothing agent-produced becomes runtime state by itself |
| AD-8 | State ownership | AD-23 | Telemetry is a separate system from the ledgers |
| AD-9 | Ledgers: task, quant, experiment; everything else is a view | AD-24 | Permissions and secret custody |
| AD-10 | Hooks are the single enforcement surface | AD-25 | Deployment envelope and the live boundary |
| AD-11 | Mission-scoped, agent-authored hooks | AD-26 | Configurable-variable registry |
| AD-12 | Mission and Task Graph: deterministic daemon state | AD-27 | Daemon store lifecycle: versioning, migration, backup, restore |
| AD-13 | Graph Template, Loop, Skill; the Task Graph name split | AD-28 | Money-path reachability boundary |
| AD-14 | Two runtimes, session axes, handles | AD-29 | Routines, scheduled triggers and continuation |
| AD-15 | Model proxy: ModelClass to Deployment to Credential Broker | | |

- **ADs: 29.** Ids stable and monotonic; every one adopted, none tagged open.
- **Hook verbs: 23** daemon-owned, each with its before/after events, plus **2** phase-less controls (`agent_stop`, `review_required`) and **6** closed decisions.
- **Node kinds: 10** — 3 that emit a Task, 7 the daemon evaluates itself.
- **Stores: 8 durable** — 7 daemon-owned (the event journal, three ledger stores, the artifact store, the staging store, the telemetry store) plus an admitted memory provider's own, which is provider-owned. The "definition store" is a name for **16** journal projections, not a ninth store. The list is closed: a store not on it may not be created.
- **Folds: 21** — 5 fold families (desk ledger views; Task/Mission/Session/Agent state; mailbox delivery and ack cursors; deployment and provider health; staging and application state) plus the definition store's 16 registries. Per-scope event streams and the ledger quarantine stream are filtered projections, not folds. A new fold is a change to the spine.
- **Variables:** the spine states no total, and none is invented here. AD-26 requires *every* number the spine mints to be registered, across **8** scopes; **5** of them live on a record (`max_in_flight`, a Mission's `ask_timeout` and `on_timeout`, and the WakePolicy's quiet hours and max wakes per window) and move only by that record's own operator command; everything else lives in the registry and moves by `variable.set`.
- Also fixed and reconciled: **23** capabilities (D1..D23), **22** Deferred rows, **3** named leases, **13** named refusals, **10** `_ref` exceptions, **9** edit kinds, **6** handle kinds.

## 7. Operator rulings the validation was forbidden to touch

- The transcript is the **seed and highest-authority input** — build on it, never transcribe it.
- Only genuine operator calls reach him (money, vocabulary he cares about, irreversible scope); technical choices are the architect's to research.
- **QMA = QuantMind Agents**, the SDK's name only; Python namespace `qma.*`; no blanket `qmx.` prefix.
- The persistent named actor is a **Quant**, never a Bot — Bot belongs to the trading platform.
- **Ledgers attach to the unit of work**: task ledgers confirmed, desk-level quant ledgers OK, no global and no per-desk store; desk ledgers are read-time views.
- **Everything gets hooks** — every primitive exposes hook events; hooks are the control surface, not an optional feature.
- The **UI is not started**: the wire contract is fixed now, the UI SDK and its packaging are deferred to their own session.
- **Daemon, data layer, wire API and DevOps first**, with a Quant reachable through models.
- **QMA never pools accounts**; pooling, where it exists, is his own proxy under his own terms, outside QMA.
- The **Windows VPS is planned, not provisioned**; Modal, Daytona and E2B were rejected on cost and fit, and Egolite is the starting point he named.
- **Nothing above a bot touches the market**, and promotion into the live zone is a human act performed outside QMA (L36, L17); `workroom/agentic-system-planning` is **not an input** — salvage nothing from it.

## Lint

```json
{
  "ok": true,
  "spine": "ARCHITECTURE-SPINE.md",
  "total_findings": 0,
  "by_severity": {},
  "findings": []
}
```
