# Rubric review 3 — venue increment (AD-26 / AD-27 / AD-28 + AD-8/AD-9 amendments)

**Target:** `ARCHITECTURE-SPINE.md` (AD-1..AD-28 read in full).
**Increment under judgment:** AD-26 (venue secret lifecycle), AD-27 (venue commands + uncertainty law), AD-28 (venue adapter contract + capability discovery), the AD-8 cTrader/GAP-0037 clauses, the AD-9 broker-is-config clause, the updated Deferred table and the two new/changed Stack rows. Closes GAP-0035..GAP-0038.
**Cross-referenced:** `trading-node-corpus-brief.md`, `trading-node-order-path-study.md`, `ctrader-venue-facts.md`, `.memlog.md` (venue sitting entries), `docs/gap-report.md` (GAP-0035..0038 text), `docs/contracts/ct-18..ct-21` stubs.
**Method note:** earlier ADs treated as settled except where the increment touches them. Prior rubric findings (review-rubric-2) were re-checked and are resolved — AD-22's output schema and bulk-form type are now pinned, and extension packaging now has explicit AD-2 treatment.

---

## Verdict

The venue increment is corpus-faithful — it ratifies the node's rules rather than inventing parallel ones, and AD-27's uncertainty law is the strongest single rule added to this spine — but it closes GAP-0036/0038 on the **command and event** half while leaving the **market-data** half of the same port unnamed, and it quietly requires `qmf-venue` to write into `qmf-data` and `qmf-registry` across a dependency edge the spine's own default-deny rule forbids. Those two, plus the unaddressed raw-double execution-price system on the money path, are day-one divergence points for the units this increment exists to serve. **REVISE before treating GAP-0036/0038 as fully closed.**

---

## Findings by checklist item

### (1) Do the new ADs fix the real divergence points one level down, and miss none?

**Fixed well** — for a venue-adapter implementer and a future command caller:

- The four-kind command vocabulary, typed per kind on core nouns, with `amend_order` structurally barred from arriving as an opaque payload (closes baseline tension T-18 at the framework layer).
- `fp1`-derived command identity mapped into the venue client-id field, with idempotent re-present and refuse-and-alarm on reused-id-different-content. This is the single highest-value rule in the increment: it makes "did my order go through twice" answerable by construction.
- The three-outcome law with `UNKNOWN` as a *state*, plus the stream-level block while an `UNKNOWN` is outstanding. It correctly refuses the industry's most expensive default (timeout-read-as-rejection).
- Capability-record-before-use with `unsupported capability` on anything undeclared — the right shape for letting a CCXT-class adapter arrive later without a core change.
- Secret *references* rather than values, with the composition root as the only injection point and a named compromise drill.

**Missed** — three genuine divergence points, all one level down:

- **Market-data has no contract** (Finding 1). The port is CT-18 capability / CT-19 command / CT-20 event+reconciliation / CT-21 secret+session. AD-27 scopes CT-20 to order/fill/position observations. Ticks, live bars, historical bars, tick history, and depth therefore have *no named contract anywhere in the four-contract port* — only capability *flags* in CT-18 ("market-data kinds", "canonical-sensing-feed support with gap-replay", "span caps and paging model"). GAP-0038's own question text names "market-data subscriptions" as one of the six dimensions to standardize. A data-ingest implementer cannot tell whether the broker feed enters through CT-20, through qmf-data's CT-15 external-source-adapter contract (which AD-21 already uses for "the broker feed" as a tick source), or through a fifth contract nobody has minted.
- **Venue-native bars cannot be given a legal `BarSpec`** (Finding 5). AD-22: a time-based BarSpec must carry "the anchoring calendar identity + version". AD-8 (amended tonight): the venue's actual daily slicing is "measured per broker ... and stored as **broker-scoped configuration**". Broker-scoped configuration is not a calendar identity, so a venue D1 bar is unexpressible as governed evidence — yet AD-28's verification suite reconciles those very bars and CT-18 declares "live bars" as a capability. Either the measured boundary must mint a calendar identity (AD-8's own definition permits it — identity *is* the rule set), or venue bars must be declared ungoverned. Neither is said.
- **Position model and order-type vocabulary are undeclared** (Finding 7). `place_order` and `close_position` mean materially different things on a netting venue versus a hedging one (cTrader ships both account types), and the spine names neither the position model nor whether order type (market / limit / stop / stop-limit), time-in-force, and protective-stop attachment are QMF-owned addable-never-redefined vocabulary or per-adapter declarations. CT-18's declared surface says "order kinds", which reads ambiguously as either the four command kinds or the order types — under either reading one of the two is silent.

### (2) Is every new AD's Rule enforceable, and does it prevent its stated divergence?

- **AD-26 — partly.** The refusal path, the store-before-discard ordering, and the demo-only testing rule are concrete. But "secrets never appear in repositories, configuration artifacts, docs/chat, `.env` files, CLI arguments, journals, evidence, fingerprints, or logs" is a prohibition with **no mechanism** — no typed `SecretRef` whose `__repr__` cannot render a value, no tier-1 secret-scan gate. Every other prohibition of this weight in the spine got a mechanism (AD-3's pyright strict, AD-10's single fingerprint implementation, AD-8's import-time tzdata assertion). Second gap: "the adapter's connection manager is the sole owner of token refresh" is a *within-process* rule, but the ratified venue fact is that a refresh token is invalidated by use — so a workstation backfill tool refreshing the same credential silently kills the live VPS session. AD-15 has the right idiom (one writer per stream); no one-refresher-per-credential rule is stated.
- **AD-27 — mostly yes, with two soft edges.** The stream block on outstanding `UNKNOWN` is mechanically checkable. But (a) the *trigger* for `UNKNOWN` is a deadline nobody owns — "retry/pool/health constants are node values" does not obviously cover a submission deadline, and without one, adapter A declares `UNKNOWN` at 5s and adapter B at 60s (Finding 10); (b) "after-condition = reconciliation" does not say whether the block clears when reconciliation *ran* or only when it returned `reconciled` — and PE-7's open-position case forces `unknown`, so the difference decides whether the pipe ever reopens without a human (Finding 9). Also, `denied-locally` sits inside the same four-value outcome union as `accepted`/`rejected`/`UNKNOWN`, while AD-11 says public boundaries fail by *returning a typed refusal* — an implementer must guess whether `denied-locally` is an outcome value or an AD-11 refusal (Finding 12).
- **AD-28 — mostly yes, one hole.** Capability-declared-or-refused is genuinely enforceable. The verification suite is named "a part of the adapter contract" and its assertions are journaled — but the **failure semantics are stated for exactly one of the five checks** (missing `moneyDigits` → refusal). The companion ratifies these as *verify-or-refuse* obligations (C1 "refuse on mismatch", B2 "the bars are refused"); the spine downgrades four of them to "journaled". Journaling a failed spot-timestamp magnitude check does not prevent the divergence AD-28 claims to prevent (Finding 8). Separately, the unmapped-error-code default (`transient venue failure`) carries retryable semantics by name — a fail-open default inside an otherwise fail-closed law (Finding 11).

### (3) Could anything under Deferred let two units diverge anyway?

Mostly clean. Checked each new or venue-touching row:

- `amend_order` / partial-close → safe: kinds are addable-never-redefined and the payload smuggling route is explicitly barred.
- Flatten/resume authority, dead-zone, paper-scope → safe: AD-27 binds the mechanical surface and forbids adapter-initiated flatten, so the deferral cannot produce two adapter behaviours.
- Numeric latency budgets for the six AD-28 rungs → safe, and correctly mirrors AD-13's established pattern (rungs named now, numbers after measurement).
- Pool/retry/health constants (do-not-default) → safe for retries; **does not cover the submission deadline** that triggers `UNKNOWN` (Finding 10).
- L2 depth / footprint vocabulary → **a small leak**: the row licenses "raw recording possible now" while the governed series vocabulary stays deferred. Raw recording with no declared raw encoding means two recorders produce mutually unreadable archives of the most expensive-to-recollect data in the system (Finding 18, low — it is licensed divergence, not hidden divergence, but the archive is forever per AD-19/AD-20).
- Bar-builder derivation details → this row is where Finding 5 will otherwise land silently: it defers *aggregation rules per BarSpec kind*, not "whether venue-native bars have a BarSpec at all".

### (4) Named tech verified-current?

Verified independently at this gate:

| Claim | Verification |
| --- | --- |
| Spotware `openapi-proto-messages` "latest observed 91, verified 2026-08-20" | **Confirmed.** GitHub releases API: latest `tag_name` = `91`, published 2024-07-15. Tags 90 and 89 precede it. The pin is current; note it has been the head for ~2 years, so the "tag change = gated re-verification" gate will fire rarely. |
| TA-Lib "0.7.1 + 0.7.1, verified current 2026-08-20" | **Confirmed.** PyPI `info.version` = `0.7.1`; GitHub `TA-Lib/ta-lib-python` latest release `v0.7.1`, published 2026-07-16 ("build with TA-Lib C 0.7.1 properly"), wheels for CPython 3.9–3.14 — consistent with AD-1's 3.14 pin. |
| Rest of Stack (CPython 3.14.7, uv 0.12.5, ruff 0.16.3, pyright 1.1.411, pytest 9.1.1, poethepoet 0.48.0, numpy/pandas/pyarrow, duckdb 1.5.5) | Carried unchanged from the 2026-08-19 gate; not re-verified here (out of increment scope). |

**Gap found (Finding 13):** the spine pins the proto *artifact* and says it is "compiled in-house", but the generated Python modules require the **`protobuf` runtime library** at import — a real, named, versioned runtime dependency of `qmf-venue` that appears nowhere in the Stack table and is not licence-registered in the AD-6 register text. (It is BSD-3, so it passes AD-6's licence tier — but "verified-current named tech" is exactly what this checklist item tests, and this one is invisible.) Minor consistency nit: the Stack header still reads "verified 2026-08-19, re-verified at reviewer gate" while two rows now carry 2026-08-20 dates in-cell (Finding 17).

### (5) Do the venue ADs ratify rather than contradict the corpus?

Ratified faithfully, item by item, against both companions:

- Four-command vocabulary — CT-ADAPTER-01 verbatim, K-44's no-smuggling rider carried.
- K-42 (CM inside the adapter, sole session owner, no second venue client) — carried and strengthened into a WriterId ownership claim.
- K-27 paired demo — carried as secret-reference-only bindings, now grounded on the verified two-connection topology.
- K-06 / E-03 sequencer evidence — carried as an opaque field, correctly leaving the sequencer to the node.
- K-54 derived equity, K-43A recovered-fills-before-healthy, three-outcome model, SCN-0005 no-invented-state — all carried verbatim.
- The reconciliation correction (command pipe only, sensing never blocks) — carried with the operator confirmation, which is the study's single most important correction.
- Node authority correctly *excluded*: KSA matrix, verdict consequences, flatten authority, `reconciliation_epsilon`, pool/retry constants. The framework-vs-node line is drawn in the right place throughout.

**One corpus rule not carried (Finding 15):** K-39 / D-10 — "ONE pinned live-account connection as canonical sensing feed; **no silent sibling-feed failover**; outage fails closed until that same feed gap-replays". AD-28 turns the *capability* into a declaration ("canonical-sensing-feed support with gap-replay") but never carries the *prohibition*. The prohibition is the load-bearing half: a helpful adapter author will failover to the demo connection during a live-feed outage precisely because it looks like resilience. This is the same class of rule as AD-27's no-auto-retry, and it belongs at the same altitude. Minor: K-55's ≤100-char `label` attribution field is dropped in favour of the client-id mapping alone (Finding 19, low — probably intentional, but the corpus correlates by `clientMsgId` *and attributes by* `label`).

### (6) Does any new AD weaken or contradict an earlier AD?

Three real collisions, one soft.

- **Dependency direction (AD-2 + the default-deny rule) — hard contradiction, Finding 2.** AD-27: "every observation emits AD-21 `order`/`fill` journal events" and "an unpersistable journal event is a typed refusal that blocks new commands" (the journal is CT-13, owned by `qmf-data`). AD-28: "the adapter emits instrument/account metadata snapshots **as registry records**" (record kinds owned by `qmf-registry` per AD-2). The ratified rule is: "Until an inter-library edge is ratified, no package may depend on any package other than `qmf-core`; adding an edge is a spine amendment. One edge is ratified: `qmf-registry → qmf-data`." No `qmf-venue → qmf-data` or `qmf-venue → qmf-registry` edge exists, the Mermaid diagram still shows `VEN --> CORE` only, and the Deferred table still says inter-library edges are default-deny. AD-25 solved this exact problem for `qmf-structure` — "the library returns fingerprintable content, never stamped records", minted by the composition root, which holds the WriterId — but AD-28 says the *adapter's* CM holds the WriterId, pointing the opposite way. So the increment neither ratifies the edge nor adopts the returns-content escape. Whichever answer is right, two implementers will pick differently today.
- **AD-15 concurrency — contradiction, Finding 6.** AD-15: "QMF never spawns threads or background work — the application owns all concurrency; async APIs exist only at the venue network edge." The increment then hands the CM: heartbeat (venue-mandated cadence), token refresh, reconnect, gap recovery, and — new tonight in AD-8/AD-28 — a **continuous** daily-boundary monitor. That is background work with wall-clock cadence living inside a QMF package. The "async at the venue edge" clause grants a *style*, not a *scheduler*. Either AD-15 needs an explicit venue-adapter carve-out, or AD-28 must say the application drives the adapter (a pump/step surface the composition root calls). Silence here is worse than either answer because the adapter is also the one component AD-15's own one-writer rule leans on.
- **AD-7 money path + AD-10 identity — unaddressed collision, Finding 3.** The ratified venue facts state three numeric systems, and system (ii) is **raw doubles** for execution prices (position price, SL/TP, deal `executionPrice`, conversion rates) — the companion's own warning is that a uniform /100000 would corrupt the execution path. AD-7's foreign-money clause covers only "a venue's **raw integers** ... stored verbatim with their declared scales". AD-10 refuses floats in identity content. AD-28 says payloads are "stored raw with their declared scales (for cTrader, the three ratified scale systems)" — but a double has no scale, so the sentence is vacuous for exactly the system that carries fill prices. Consequence: a fill's execution price cannot enter a fingerprinted observation record under current law, and every adapter author will invent a different double→exact rule (`Decimal(repr(x))` vs `round(x * 10**digits)` vs string formatting at `digits`) at the boundary AD-7 designates as *the* named money-path crossing. This is the money path, in evidence, on the live account.
- **Soft, worth noting:** AD-9's amendment says "no rule anywhere may name a specific broker" — the increment honours it (no broker is named), but AD-26/27/28 name the *platform* cTrader six times in parentheticals inside venue-neutral rules. Not a violation; a discipline risk (see item 8).

Checked and clean: AD-8 (receive stamps, per-field ms, epoch exceptions, calendar identity separation) is consistent with AD-28's stamping rule; AD-11's categories are used correctly and none is redefined; AD-12's world separation is respected (sandboxes never hold live secrets); AD-21's seven journal event types absorb everything the increment emits (`order`, `fill`, `data quality`, `control action`) with no eighth type invented; AD-5's addable-never-redefined discipline is applied to both command kinds and capability records.

### (7) Every owned dimension decided, deferred, or an open question?

Silently skipped (neither decided nor deferred nor flagged):

| Dimension | Where it should have landed |
| --- | --- |
| Market-data subscription / delivery contract | GAP-0038 names it; no contract in the port (Finding 1) |
| Position model: netting vs hedging | CT-18 capability record; changes what `close_position` means (Finding 7) |
| Order type / TIF / protective-stop attachment vocabulary | CT-19 per-kind typing (Finding 7) |
| Inbound venue-event idempotency key | CT-20; AD-21 already has the idiom, never extended (Finding 4) |
| BarSpec for venue-native bars | AD-8 amendment ↔ AD-22 (Finding 5) |
| Submission deadline / `UNKNOWN` trigger owner | AD-27 or the do-not-default row (Finding 10) |
| `protobuf` runtime dependency | Stack table + AD-6 register (Finding 13) |

Correctly handled, not silent: token lifecycle (capability-declared class), rate-limit window semantics (adapter-declared conservative model), span caps and paging (declared), equity nativeness (declared), server-clock absence (declared, receive-stamping mandatory), error mapping (versioned per-adapter table), demo/live topology (declared), broker identity (ruled config, not architecture), latency numbers (rungs without numbers, awaiting AD-13).

### (8) Terse-spine discipline

The increment is the largest single addition to this spine and carries visible rationale that belongs in `.memlog.md`:

- **Provenance parentheticals in normative text:** "(the node's CT-ADAPTER-01 vocabulary, adopted verbatim)", "(operator-confirmed)", "(the node's Book-after-doors is that caller, assigned at the node sitting)", "(Precedent: …)" — a builder does not need to know which document a rule came from; the memlog and the ledger already carry it.
- **AD-28's second bullet is a CT-18 field list** — twelve enumerated capability fields inside the spine. This is contract surface, and putting it here means the spine must be amended whenever a field is added, which fights AD-5's addable-never-redefined design. The spine should state *that* the record is versioned, fingerprinted, consumed-before-use, and refusal-backed, and let CT-18 own the field roster.
- **Platform-specific facts in venue-neutral rules** — six cTrader parentheticals across AD-26/27/28. They read as illustrative to the author and as normative to a second-adapter implementer. AD-8 set this precedent, so it is not new, but the venue ADs are where it most risks being mistaken for law.

Not bloat: AD-27's three-outcome and order-state paragraphs earn their length — every clause is a rule with a consequence.

---

## Findings summary

| # | Severity | Finding |
| --- | --- | --- |
| 1 | **Critical** | **No market-data contract in the port.** CT-18/19/20/21 cover capability, command, order-event+reconciliation, and secrets; ticks, live bars, historical bars and depth get capability *flags* but no contract. GAP-0038 names "market-data subscriptions" as a required dimension. A data-ingest implementer cannot tell whether the broker feed enters via CT-20, via qmf-data's CT-15 (which AD-21 already uses for "the broker feed"), or via an unminted fifth contract. Subscribe-snapshot semantics, non-instantaneous unsubscribe, gap-replay request shape, and historical paging are all ratified *facts* with no contract to live in. |
| 2 | **Critical** | **`qmf-venue`'s write path violates the default-deny dependency rule.** AD-27 has the adapter emitting AD-21 journal events (CT-13, `qmf-data`) and blocking on their persistence; AD-28 has it emitting "registry records" (`qmf-registry`). Neither edge is ratified, the Mermaid diagram still shows `VEN --> CORE` only, and AD-25's returns-content-not-stamped-records escape is not restated — indeed AD-28 assigns the WriterId to the adapter's CM, pointing the other way. Either ratify two edges or adopt AD-25's pattern explicitly. |
| 3 | **Critical** | **Raw-double execution prices are unhandled on the money path.** Ratified venue fact A6(ii): execution prices are raw doubles. AD-7's foreign-money clause covers only "raw integers … with declared scales"; AD-10 refuses floats in identity content; AD-28's "stored raw with their declared scales" is vacuous for a scale-less double. No double→exact rule, rounding mode, or refusal path is stated at the very boundary AD-7 names as *the* money-path crossing — so fill prices are simultaneously unstorable as identity and free-form per adapter. |
| 4 | High | **Inbound venue-event idempotency/dedup key is unstated while gap-replay is a declared capability.** AD-21 already has the idiom — "idempotent intake keyed on (source, source-native id, revision)" — but AD-27/28 never extend it to CT-20. Since receive stamps are mandatory and identity-by-default (AD-10), a fill redelivered after reconnect fingerprints differently and lands as a *second* fill in evidence. Redelivery is designed-in, not exceptional. |
| 5 | High | **Venue-native bars have no expressible `BarSpec`.** AD-22 requires an anchoring calendar identity + version for time-based BarSpecs; tonight's AD-8 amendment stores the measured broker daily boundary as "broker-scoped configuration", which is not a calendar identity. AD-28's suite reconciles those bars and CT-18 declares "live bars" as a capability, so the gap is load-bearing. Either mint the measured boundary as a calendar identity (AD-8's rule-set definition allows it) or declare venue bars ungoverned. |
| 6 | High | **AD-15 contradiction.** "QMF never spawns threads or background work — the application owns all concurrency", yet the CM owns heartbeat cadence, token refresh, reconnect, gap recovery, and a *continuous* daily-boundary monitor. Needs either an explicit adapter carve-out in AD-15 or an application-drives-the-adapter (pump/step) statement in AD-28. |
| 7 | High | **Position model and order-type vocabulary undeclared.** Netting vs hedging changes what `close_position` means and whether position ids exist; order type / time-in-force / protective-stop attachment are never stated as QMF-owned addable-never-redefined vocabulary or per-adapter declarations. CT-18's "order kinds" reads ambiguously as either the four command kinds or the order types — under either reading, one of the two is silent. |
| 8 | Medium | **Verification-suite failure semantics stated for one check of five.** Only missing-`moneyDigits` gets a refusal; spot-timestamp magnitude, daily-boundary measurement, BID-bar reconciliation, and pip-formula validation are merely "journaled". The companion ratifies all of them as *verify-or-refuse* (C1 "refuse on mismatch"; B2 "the bars are refused"). Journaling a failure does not prevent the divergence AD-28 claims to prevent. |
| 9 | Medium | **"After-condition = reconciliation" is ambiguous.** Does the command block clear when reconciliation *ran*, or only on verdict `reconciled`? PE-7 forces `unknown` whenever a position is open, so the difference decides whether the pipe ever reopens without a human. Verdict *consequences* are node authority, but the adapter's own unblock condition is QMF's. |
| 10 | Medium | **The submission deadline that triggers `UNKNOWN` has no owner.** "Retry/pool/health constants are node values" plausibly excludes a per-command deadline. Without it, adapter A declares `UNKNOWN` at 5s and adapter B at 60s — divergence in the one law the increment most wants uniform. |
| 11 | Medium | **Unmapped venue codes default to `transient venue failure`** — a category whose name and AD-11 retryability semantics say "retry", inside an otherwise fail-closed law. A permanent failure (account disabled, permission revoked) arriving as an unmapped code becomes a retryable refusal. The default should carry retryability=no / after-condition=human. |
| 12 | Medium | **`denied-locally` straddles outcome and refusal.** It sits in the same four-value union as `accepted`/`rejected`/`UNKNOWN`, while AD-11 says public boundaries fail by *returning a typed refusal*. An implementer must guess whether a locally-denied command returns `Outcome.denied_locally` or an AD-11 refusal — and callers branch differently on each. |
| 13 | Medium | **`protobuf` runtime dependency is invisible.** The spine pins the proto artifact and says it is "compiled in-house", but the generated modules import `google.protobuf` at runtime — a named, versioned dependency of `qmf-venue` absent from the Stack table and unaddressed in the AD-6 register text. (Licence-clean, BSD-3; the issue is that it is unnamed and unpinned.) |
| 14 | Medium | **AD-26 has no enforcement mechanism and no cross-process refresh rule.** The never-in-logs/journals/fingerprints prohibition gets no typed `SecretRef` and no tier-1 scan gate, unlike every comparable prohibition in the spine. Separately, "the CM is the sole owner of token refresh" is within-process, while the ratified fact is that a refresh token dies on use — a workstation tool refreshing the same credential silently kills the live session. AD-15's one-writer idiom is the missing rule: one refresher per credential. |
| 15 | Medium | **K-39/D-10's "no silent sibling-feed failover" is not carried.** AD-28 declares canonical-sensing-feed *support* as a capability but omits the prohibition, which is the load-bearing half — a helpful adapter author will failover to the demo connection during a live-feed outage precisely because it looks like resilience. |
| 16 | Low | Terse-spine bloat: provenance parentheticals ("adopted verbatim", "operator-confirmed", "Precedent:"), AD-28's twelve-field CT-18 roster inside the spine (which forces a spine amendment per added field, fighting AD-5), and six cTrader-specific parentheticals inside venue-neutral rules. |
| 17 | Low | Stack table header still reads "verified 2026-08-19, re-verified at reviewer gate" while two rows carry in-cell 2026-08-20 dates. |
| 18 | Low | Deferred row licenses depth "raw recording possible now" with no declared raw encoding — two recorders produce mutually unreadable archives of data AD-19/AD-20 keep forever. |
| 19 | Low | K-55's ≤100-char `label` attribution field is dropped; the corpus correlates by client id *and attributes by* label. Probably intentional, but unstated. |

**Counts:** critical 3, high 4, medium 8, low 4.

---

## What is genuinely solid

- **AD-27's three-outcome law** is the best rule in this spine's live-money half: it names the industry's most expensive default error, refuses it structurally, and backs the refusal with a stream-level block rather than a comment. The no-retry / no-assume / no-flatten / no-invented-terminal quadruple is exactly the right set.
- **Command identity as an `fp1` fingerprint** reuses AD-10's idempotent-rewrite split instead of minting a parallel idempotency concept — one mechanism, two uses, no new vocabulary.
- **The framework-vs-node line held under pressure.** Every temptation to absorb node authority (reconciliation verdict consequences, KSA matrix, flatten authority, retry constants, `reconciliation_epsilon`) was declined with a named owner. The corrected reconciliation scoping — command pipe gated, sensing pipe never — is stated precisely enough that no builder can misread "before any trading" as "before any data".
- **AD-9's broker-is-config amendment** is a genuinely load-bearing simplification: it closes GAP-0037's broker half without freezing a vendor, and it composes cleanly with AD-9's pre-existing opaque `VenueId` discipline.
- **AD-26's store-before-discard rotation rule** with a failed-store alarm is the correct ordering for a never-expiring refresh token, and the cTID-reauthorization drill gives compromise recovery a real, testable anchor instead of a policy sentence.
- **Capability-declared-or-refused** is the right abstraction for keeping a future CCXT-class adapter from forcing a core change, and the increment resisted the obvious mistake of typing the capability record around cTrader's shape.
- **Tech currency verified true.** Both new/changed Stack claims (proto tag 91, TA-Lib 0.7.1 + 0.7.1) check out against primary sources at this gate.
