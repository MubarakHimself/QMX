---
review: reconcile — parent-spine fidelity (QMB vs QMF AD-1..41)
target: architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md
authority: architecture-QMX-2026-08-19/ARCHITECTURE-SPINE.md (AD-1..AD-41, Inherited Invariants, Deferred)
sitting: QMB / backtesting sitting 2026-08-20
reviewer: reconcile-lens (independent parent pass)
date: 2026-08-20
verdict: FAIL WITH FINDINGS — 5 material conflicts, 2 silent weakenings, 2 inherited-claim mismatches, hygiene
---

# Reconcile review — QMB spine vs parent QMF spine (AD-1..AD-41)

## Verdict

QMB is the right *kind* of child — L21 application, B-ids not a second AD series, GAP-0048 fill seam held with `optimistic` taint, GAP-0016/0017/0047/0049 left deferred — but it does not consume AD-1..41 read-only. Three B-ids (B-4, B-10, B-13) rewrite parent identity and evidence law; B-6/B-7/B-14 quietly invert or pre-settle Book-door, world, and L20 rules the inherited table claims to honour; the HUB diagram re-opens the always-on service DEC-0084 killed. A new B-id that contradicts an inherited AD is a conflict, not a local override. Nothing here is a licence to reopen AD-1..41; every fix is a QMB-side amendment that names the parent rule and defers to it.

Prior QMB-side amendments (kernel ban restored, config fragments derived-not-kind, Python door return-not-raise, frontier clock not AD-8 monotonic, swap→financing/admin fee, 12–14 framed as motivating reference, WriterId ledger fragments, `uv add` as primary channel) are **not re-raised**. They are checked-clean below.

---

## Hunt matrix

| Hunt | Parent law | QMB claim | Verdict |
| --- | --- | --- | --- |
| AD-7 exact money vs metrics / optuna / chart series | Binary float banned on the money path and in parameters/identity; named conversion to re-enter; analytic floats off-path with **label-derived** identity (AD-10/AD-41) | Inherited row narrows carve-out to "indicator math"; B-10 "unit-kinded exact-money metrics"; B-8 Optuna TPE; B-10 downsampled chart series | **CONFLICT** — Finding 4 |
| AD-8 Clock protocol vs B-2 frontier clock | qmf-core Clock protocol; composition root injects; replay = data-driven; monotonic ≠ Instant; nothing below root reads the system clock | B-2 injected frontier clock, monotonically non-decreasing, emits wall/replay Instants, explicitly not the diagnostic kind | **Vocabulary collision fixed.** Residual: frontier clock not identified as the core protocol; config-selected clock vs provenance-derived world; simulated typed as replay Instants — Findings 3, 8 |
| AD-11 typed refusals vs CLI/MCP rendering | Public boundaries **return** unions; exceptions = programmer error only; doors may render per transport, never swallow | CLI → nonzero + stderr JSON; Python **returns** unions; MCP "returns error objects" | **Python/CLI hold.** MCP unspecified — Finding 10 |
| AD-12 worlds vs B-7 provenance-derived world | `replay` legal; `simulated` reserved-unusable (policy rejection into governed evidence) until GAP-0048 typing; paper/demo = `world = live` (role carries money-reality); package SemVer never enters identity; `provenance = sandbox` blocks operator-store merge | Inherited row restates worlds correctly; B-7 derives world from data taint, never caller-declared; B-2 lets run-config bind the clock; B-13 puts QMB/QMF SemVer in the label | **CONFLICT** — Findings 2, 3, 8 |
| AD-13 measure-then-budget vs B-5 "12–14 concurrent" | No invented numbers; motivating references legal; baselines fingerprinted per (OS, CPU-class) | "motivating reference under AD-13, never a validated budget until a fingerprinted baseline is measured" | **HOLDS.** Harness obligation itself is unnamed (note under What holds) |
| AD-15 no threads in library / one-writer-per-stream vs B-5 process-per-run + ledger merge | Application owns concurrency; library never spawns threads/background work; one WriterId per stream | Process-per-run; WriterId-scoped ledger fragments; merge is a read view | **Ledger holds.** Trial-runner placement fights the library-purity claim — Finding 9 |
| AD-16/19/21 registry + rooms + 12-month seal vs B-9 Jupyter-anywhere + B-11 data | Rooms per world; seal = policy rejection at every qmf-data read; portable path = split-governed research door; kinds addable never redefined; identity = fp1 | B-9 unsealed split-governed only; seal's one look stays write-gated on the controlled side; B-11 thin fronts over CT-10/CT-15 | **Mostly holds.** Book `name@version` fights AD-16/AD-30 identity — Finding 5; `timeframe` fights AD-22 — Finding 10 |
| AD-21 split manifests vs B-8 train/test | Fingerprinted, time-ordered, non-overlapping manifests; knowledge-time partition; purge/embargo in-band; calendar identity in-band; seal independent of GAP-0016 | "Train/test separation is declared in the run spec and enforced by split-manifest reads (AD-21)" | **SILENT WEAKENING** — Finding 7 |
| AD-29..41 Book/BMS/bar/exits/R vs QMB consuming them | Consumes, never redefines: CT-23 door, AD-32 per-requirement bar (no composite), CT-32 one result kind, AD-33 Book-owned exits, AD-40 R freeze, AD-41 measurement publishes | Inherited row: "QMB consumes, never redefines"; frontmatter `binds: [CT-32]`; B-4 singular pass/fail; B-10 parallel canonical artifact; B-6 `order intent × market state → Fill` | **CONFLICT** — Finding 1 |
| L20 synthetic never validates edge vs B-7 / `data generate` | Synthetic stresses infrastructure, never validates edge; writing `world = simulated` into governed evidence is policy rejection until GAP-0048 | Store-level taint + claim classes (infra-stress / robustness); B-14 "validation ladder" / "pre-build **edge** testing" including candle perturbation; those runs still ledger | **CONFLICT / pretends to settle deferred** — Finding 3 |
| DEC-0084 no central always-on service vs deployment HUB | DEC-0084 **dead**: no centralized always-on backtesting service; companion DC-2 hub is legal only as dumb file-sync that computes nothing | Inherited row restates "no central always-on service"; diagram `HUB[(sync hub: registry + ledger files)]` with bidirectional CLI arrows; no B-id, no "files only" rider | **SILENT WEAKENING** — Finding 6 |
| AD-2 no reflection / CPython 3.14 / uv workspace vs QMB packaging | CPython 3.14; uv workspace of **seven qmf-\*** packages; discovery = explicit registration, never ambient scanning; QMB is L21 *outside* that repo | CPython 3.14 + uv/ruff/pyright/pytest/poe claimed on QMB code; "uv workspace" restated onto QMB; one `qmb` wheel; no ambient discovery in the paradigm | **Mostly holds.** "uv workspace" collides with L21 — Finding 9 |

---

## Part A — Findings (most-severe first)

### Finding 1 — MATERIAL CONFLICT — AD-29..41 are claimed consumed and then redefined (bar, result kind, Book door)

**Parent (verbatim load-bearing bits):**

- Inherited-invariants discipline for the child: a B-id may not contradict or weaken an inherited AD; QMB's own table says AD-29..41 are consumed, never redefined.
- AD-32: the bar is a **set** of named requirements; **no composite score**; each requirement passes or fails on its own terms; `not yet ruled` is a declared value; `evidence_requirements` include world and account role; measurement does not act.
- AD-41: **CT-32 is the one kind** serving both admission-bar evidence and the analyst's report (AD-12 label, declared population of **binding-record fingerprints**, declared period, unit-kinded measures, veto/suppression accounting, float discipline). A performance metric is an AD-23 governed producer. Measurement **publishes**; the Book door (or the operator) acts.
- AD-33/CT-23: bot proposes; **Book resolves `requested_r` and sizes**; exits are Book-owned and risk-monotonic. A bot that sizes itself inverts constitution L1 / AD-29.
- AD-40: every position declares a planned full-loss price; R is frozen at admission; `realized_r` lives on the CT-29 exit record.
- AD-29: `world` is `live` for every V1 **binding**; a replay of a binding mints a **different** binding identity; replay-derived and live evidence are deliberately incomparable by binding — "the backtesting sitting inherits a stated position, not an accident."

**What QMB says:**

- Frontmatter `binds: [GAP-0048-seams, CT-32, ticket-008]` — CT-32 is named and then never appears in any B-id.
- B-4: one ledger line with "the unbiased end verdict (**pass/fail** against the Book's declared bar; `unrated` when the bar is not yet ruled") — a **singular composite**, computed by QMB, stored as the thing "the Book sets the bar" reads.
- B-10: "one canonical machine-readable result artifact: unit-kinded exact-money metrics (the named metric set, versioned — metric arithmetic changes mint a contract version), chart series as data … and the trade record." Parallel container. No CT-32, no binding-record population, no veto/suppression accounting, no AD-40 unit-kinds, no "a single result may never span account roles."
- B-6: fill port is `order intent × market state → Fill | NoFill + itemized costs`. No CT-23 door, no Book-resolved `requested_r`, no AD-40 full-loss declaration, no CT-29 exit record, no risk-monotonic exit kinds.
- Capability map: "Backtest against a Book/BMS's own rules | config/ + runloop/ | B-2, B-3, AD-29..41" — the claim of consumption without a single named consume of CT-23/29/32.

**How it conflicts (not a local override):**

1. **Composite verdict.** AD-32 forbids expressing a bar as one pass/fail. B-4's ledger verdict is that forbidden composite, and it is the artifact the bar is said to read. `unrated` correctly consumes the blank-threshold half and then throws the rest away.
2. **Second result kind.** AD-41 minted one kind on purpose so admission evidence and the analyst report cannot drift. B-10 mints another. The frontmatter bind on CT-32 makes this an inherited-claim mismatch as well as a conflict: the spine tells a reader CT-32 is in force and then specifies a different object.
3. **Book door skipped.** A fill port that takes bot `order intent` is the inversion AD-33 names. QMB can still *simulate* fills; it cannot, under AD-29..41, let the bot size or close. Without CT-23 on the inbound path, "backtest against a Book's own rules" is a slogan over a Jesse-shaped bot-goes-straight-to-market loop.
4. **R and exits unconsumed.** Itemized costs as exact money (B-6) is necessary and not sufficient. AD-41's `cost_components` set is identity-bearing; AD-40's three R faces and the CT-29 exit record are how a Book bar *and* the bench fold even exist. QMB's "trade record" is an unnamed substitute.

**What is not a conflict, so it is not used as cover:** testing against a Book *definition* (template fingerprint) rather than a live binding is the AD-29-correct reading — replay must not share a binding with live. That reading is available and unused. name@version (Finding 5) points the other way.

**Fix (QMB-side, no parent re-open):**

- B-10: the metrics section **is** a CT-32 performance-result (AD-41). Chart series and renderings are declared display-only (AD-10) and add no measure. Cite AD-23 for arithmetic versioning; do not mint a second version ladder.
- B-4: ledger line carries the CT-32 fingerprint plus **per-requirement** outcomes against the cited bar (and `unrated` per blank/`pending` slot). No singular pass/fail. QMB publishes; it does not bench, promote, or bind.
- B-6/B-2: inbound path is CT-23 (Book-resolved intent) or a typed refusal. Fill/slippage/fee ports execute an *authorized* intent against market state. Full-loss price required before open (AD-40). Closes produce CT-29 records. State the AD-29 consequence: a QMB replay mints its own binding identity; it is incomparable to any live binding by construction.

**Class:** conflict (plus inherited-claim mismatch on the CT-32 frontmatter bind).

---

### Finding 2 — MATERIAL CONFLICT — B-13 (and the inherited AD-12 restatement) put package SemVer into identity and drop load-bearing label parts

**Parent AD-12 / AD-10 / AD-5:**

- Result identity = producer **contract identity** (configured-producer fingerprint, distinct from format version) + producer **contract format version** + input fingerprints + evidence range + occurrence id + **evidence class** (confirmed / unconfirmed / provisional) + world.
- "**package SemVer never enters identity** and may ride only as display-only provenance."
- Factory-sandbox evidence carries identity-bearing `provenance = sandbox`, **blocking dedup-merge into the operator store**.
- Non-live worlds may never write into the live evidence namespace; rooms are per-world (AD-19); a cross-world read is `policy rejection`.
- Floats are refused in identity content (AD-10); float-bearing artifacts take label-derived identity.

**What QMB says:**

- Inherited row AD-10/AD-12: "Fingerprints + the full result label (**producer version**, input fingerprints, evidence range, occurrence id, world)" — "producer version" is not a parent field. Evidence class is gone. The SemVer ban is gone.
- B-13: "Every result label carries: **QMB version, QMF roster version** (separate ladders), resolved-config fingerprint, registry-state as-of (Book/BMS fragment fingerprints), data/split fingerprints, world, and RNG provenance where stochastic."
- B-4 merge view over WriterId fragments via the HUB, with no world-namespace split and no `provenance = sandbox` field.
- Sequence diagram: sandboxes and the laptop both write through the same HUB.

**How it conflicts:**

Two version ladders (QMB vs QMF roster) are the correct *display* story under AD-5. Putting those SemVer strings **in the result label** makes them identity. AD-12 forbade that so a patch of qmf-indicators cannot fork every stored computation. QMB's restatement of AD-12 as "producer version" is the mechanism of the conflict: a reader of the child spine never sees the ban, so B-13 looks faithful.

Dropped **evidence class** means a QMB artifact cannot satisfy AD-25/AD-12 confirmed-evidence reads. Dropped **`provenance = sandbox`** means 12–14 sandbox ledger lines, synced through the HUB (Finding 6), idempotent-merge into the operator store — the exact failure AD-12's sandbox clause exists to prevent. Dropped per-world rooms on the merge view re-opens "worlds mixing in merged ledgers" (AD-12's own Prevents line).

**Fix:**

- Inherited AD-12 row: quote the parent field set, including evidence class, and the SemVer-is-display-only sentence. Do not paraphrase "producer version."
- B-13: QMB SemVer and QMF roster SemVer are **display-only provenance** on the occurrence record, never identity. Identity is AD-12's set plus the resolved-config fingerprint as an *input* fingerprint. `provenance = sandbox` is mandatory on factory-sandbox artifacts.
- B-4 merge view is per-world and role-scoped (AD-12/AD-19). Cross-world union is a `policy rejection`, not a hub feature.

**Class:** conflict (the inherited restatement is also an inherited-claim mismatch).

---

### Finding 3 — MATERIAL CONFLICT — B-7/B-14 pretend to settle inherited Deferred cargo (GAP-0048 simulated-time, AD-12 reserved world, L20)

**Parent, still deferred / reserved:**

- AD-12: `simulated` = synthetic data; **reserved but unusable in V1**; writing `world = simulated` into governed evidence is a `policy rejection` until the backtesting sitting defines **simulated-time typing** (Deferred row: GAP-0048, "operator not ready").
- L6/L20 (parent inherited row): synthetic data stresses infrastructure, **never validates edge**.
- Memlog 133: the operator wanted Lean's generator reverse-engineered; **L20 was not overridden**.
- GAP-0048 also still owns fidelity taxonomy (B-6 correctly holds that half with `optimistic` taint).

**What QMB says it is doing:**

- Deferred: GAP-0048 still owns "simulated-time typing that unlocks world=simulated." Honest on the page.
- B-7: store-level taint; any run consuming synthetic-origin data is `world=simulated` (policy rejection for governed evidence until GAP-0048). Then, in the same rule, a **claim-class taxonomy**: fabricated-from-scratch → infrastructure stress only; **real-seeded perturbation (block-bootstrap) → may additionally claim robustness** under B-14; "nothing synthetic validates edge (L20)."
- B-14: the **validation ladder** ships as library functions, including Monte Carlo **real-seeded candle perturbation**, as "**pre-build edge testing**", each producing **labeled runs and ledger entries** under B-3/B-4.
- B-4: the ledger is what "the Book sets the bar" reads — i.e. governed evidence.
- B-2: backtest/replay/live/**simulated** differ only by which clock the run-config binds; that clock "**emits AD-8 wall/replay Instants**" for all of them.

**How it pretends to settle, and how it weakens L20:**

1. **Simulated-time typing (GAP-0048) is decided in B-2.** Typing the simulated clock as AD-8 wall/replay Instants *is* the deferred typing. The Deferred row says it is not decided. Two pages of the same spine disagree; an implementer will ship B-2.
2. **`world = simulated` is written into the ledger.** B-7 admits that is a policy rejection for governed evidence, then B-14 does it anyway for "robustness" runs. The ledger is the bar's evidence. That is writing simulated into governed evidence.
3. **Claim classes are a local override of L20.** "Robustness" from perturbed candles is evidence *about the edge*. B-14 names it "pre-build **edge** testing." L20 does not have a robustness carve-out. The operator did not grant one. B-7's last clause ("nothing synthetic validates edge") is then false in the same document as B-14's first sentence.
4. **Trade-shuffle vs candle perturbation are not typed.** Trade-shuffle of a replay run's trades may not taint the data store at all under B-7's "synthetic-origin data" rule, so a third world-labelling walks in unspecified.

This is the failure mode the job asked for: an inherited Deferred item the child pretends to leave deferred while its B-ids settle it.

**Fix:**

- B-2: drop `simulated` from the legal-now clock set, or mark simulated-clock typing as **refused until GAP-0048** (the loop seam may exist; the Instant kind may not be asserted).
- B-7: keep store-level taint and the policy rejection. **Delete the robustness claim class** (or mark it candidate-for-GAP-0048, non-binding). L20 stands: synthetic → infrastructure stress only; no edge, no bar, no admission evidence.
- B-14: candle-perturbation MC may ship as infra-stress tooling (B-7's first class) producing **unusable-as-evidence** runs (`world = simulated` → cannot ledger into the bar's store). Trade-shuffle of a `world = replay` run stays replay only if it does not mint synthetic market data — say so. Rename "pre-build edge testing" so L20 is not contradicted by the section title.
- Leave GAP-0048's simulated-time sitting actually unopened.

**Class:** conflict, and inherited Deferred pretended-settled.

---

### Finding 4 — MATERIAL CONFLICT — AD-7 / AD-10 vs Optuna floats, B-10 metrics, and downsampled chart series

**Parent:**

- AD-7: money path is a taint; binary float banned on it; **binary floats never appear in parameters or identity**; re-entry only via a **named** conversion with stated rounding. Analytic floats are legal *off* the money path; identity is label-derived (AD-10), never a hash of float bytes.
- AD-22: two named conversions (exact→analytic, analytic→exact), one qmf-core implementation each. `Bar`/`Price` are exact; `mid` is a derived series with stated rounding.
- AD-10: floats refused in identity content.
- AD-32: a float-valued measure compared to an exact-rational bar threshold crosses AD-22's analytic→exact boundary, comparison rule identity-bearing.
- AD-41: Sharpe/drawdown are float-valued, **label-derived identity**, never hashed float bytes; every emitted quantity carries an AD-40 unit-kind (`r-multiple`, `dimensionless-ratio`, `count`, `money(currency)`, …), not "exact-money" only.

**What QMB says:**

- Inherited AD-7 row: "Exact integer money everywhere on the money path; **floats only in the AD-7 carve-outs (indicator math)**, re-entry via named conversion." The parent carve-out is *off-path analytic series*, not "indicator math." Sharpe, SQS-as-ratio (exact rational in AD-39), and AD-32's float-valued measures are not indicator math.
- B-8: Optuna 4.9.0 TPE-class default adapter; bot parameter space is `name, type, bounds, step, default` — no exact-rational requirement, no named float→exact conversion. Every trial's resolved run-config is fingerprinted and **is the ledger key** (B-3).
- B-10: "unit-kinded **exact-money** metrics"; chart series (candles, execution markers, indicator overlays) "**downsampled by a declared sampler**" inside the canonical artifact. No display-only classification. No named conversion. No AD-41 float discipline. No AD-40 unit-kind vocabulary.

**How it conflicts:**

1. **Inherited restatement silently narrows AD-7**, then the B-ids do not even keep the narrowed version. A child restatement that drops parent law is itself a conflict vehicle (same pattern as Finding 2's "producer version").
2. **Optuna internals may float; identity may not.** TPE sampling in float space is an adapter detail. The sampled value **entering the resolved run-config** is identity content (B-3). AD-7/AD-10 refuse binary floats there, including non-money parameters (exact-rational type). No named boundary exists in B-8. As written, every optimize trial either violates AD-10 (float in fp1) or cannot be fingerprinted.
3. **B-10's "exact-money metrics" cannot express the measures AD-41/AD-32 already require** (Sharpe, drawdown, R, counts). Forcing them to `Money` is a redefinition of AD-40's dimensional law. Omitting them is a redefinition of "the Book sets the bar," which reads those measures.
4. **Downsampled candles and execution markers are money-path Prices.** Putting a lossy sampler's output in the canonical (identity-bearing) artifact is an unnamed conversion *and* a silent mutation of evidence. AD-10 requires an explicit versioned display-only declaration to exclude a field from identity; B-10 has none. Downsampling for a renderer is legal; downsampling inside the canonical artifact is not, unless it is display-only and the exact series remains the cited input.

**Fix:**

- Inherited AD-7 row: restore the parent sentence (money-path taint; analytic floats off-path; named conversion; parameters are exact rationals). Do not say "indicator math."
- B-8: parameter schema types ∈ exact integer | exact rational | categorical | boolean. The Optuna adapter converts at a **named AD-7/AD-22 boundary** (rounding mode + target scale, identity-bearing) *before* values enter the resolved run-config. Sampler internals may float; identity content may not.
- B-10: metrics are AD-40 unit-kinded, AD-23 versioned, CT-32-hosted (Finding 1). Float-valued measures take **label-derived** identity (AD-41). Chart series: exact `Bar`/`Price` (AD-22) cited as inputs; any downsample is a display-only derivative with a declared sampler identity, never the canonical payload.

**Class:** conflict (inherited restatement is the silent-weakening mechanism).

---

### Finding 5 — CONFLICT — Books resolved `name@version` vs AD-30 "by fingerprint, never a version string"

**Parent AD-30 / AD-16 / AD-5:**

- "A binding cites a Book definition by **fingerprint**, never a version string."
- Book identity is `fp1` of template content. Version graph is `branches-from` (multiple heads legal); "current" is a separate dated pointer, **never inferred**. `supersedes` is linear and is not this graph.
- Kinds addable, never redefined; stable id derived from `fp1`.

**What QMB says:**

- B-13: "Books and bots are resolved **name@version** from the registry — the npm-shaped half of distribution."
- Sequence diagram: `qmb backtest bot --book scalping@2` then "resolve Book/BMS fragments (name@version)."
- B-3 does fingerprint the *compiled fragment* and puts that fingerprint in the label — so content identity exists downstream, while the *cite* remains a version string.

**How it conflicts:**

`scalping@2` is a linear SemVer/tag cite. AD-30's version graph is not SemVer: two heads can be live, "current" is a pointer record, and two templates with different money rules must not share an identity. An npm tag is the floating alias AD-30 spent a paragraph killing. Door-level UX may accept a name plus a pointer ("current", a dated alias, a display ordinal) **if and only if** the resolved run-config cites the Book/BMS **definition fingerprint** (and refuses `stale evidence` when a fresher snapshot shows that ref superseded — DC-2, currently ungoverned; Finding 6). As written, B-13 makes the version string the resolution rule.

B-3's "derived fragment with AD-16 lineage, not a new kind" (post-prior-review amendment) is still correct and is not this finding.

**Fix:** invocation may take a human alias; the resolved artifact **must** cite `fp1` (Book definition, BMS definition, binding if any). `name@version` is not a legal cite. If a convenience alias is wanted, it is a dated pointer record in the registry snapshot, never a SemVer ladder for Books.

**Class:** conflict.

---

### Finding 6 — SILENT WEAKENING — DEC-0084 (dead: no always-on service) vs the HUB, plus AD-12 merge into the operator store

**Parent / companion:**

- DEC-0084 is **dead**: no centralized always-on backtesting service. Inherited QMB row restates "no central always-on service."
- AD-16: registry is JSONL-append, no database server.
- Companion `backtesting-direction-position.md` DC-2 (recommended, **not operator-ratified as a B-id**): a *dumb* file-sync hub that **stores files, computes nothing**; immutable fingerprinted snapshots; `registry_as_of` + snapshot fingerprint on every label; stale-evidence refusal; WriterId write-back. That shape keeps DEC-0084 dead. Alternative (b) — live registry read-service — **amends DEC-0084**.
- AD-12 sandbox provenance (Finding 2) and per-world rooms.

**What QMB says:**

- Diagram: `HUB[(sync hub: registry + ledger files)]` with `CLI1 <--> HUB`, `CLI2 <--> HUB`, `HUB --> BUCKET`. Capability map cites DEC-0084 as governing "Local + sandbox runs."
- B-5 / B-9: no daemon, no server, no Docker **on the compute path**. The HUB is not mentioned in any B-id or Deferred row.
- No "computes nothing / files only / not always-on" rider. No snapshot fingerprint. No `registry_as_of`. No stale-evidence rule.

**How it weakens:**

A box named "sync hub" with bidirectional arrows to every CLI, sitting above a nightly bucket, is the always-on service DEC-0084 killed — unless the spine says it is not. B-5's "no daemon" on the *runner* does not constrain the hub. An implementer can put a registry read-service there (companion option (b)) and still match the diagram. That is a silent amendment of a dead DEC, which the inherited table claims is in force.

Second-order: even a dumb hub that merges ledger fragments without world-scoping and without `provenance = sandbox` (Finding 2) is a storage-layer violation of AD-12, performed at the one place the child invented to satisfy DEC-0084.

**Fix:** either (i) promote DC-2 into a B-id: dumb file-sync, computes nothing, not a service, not always-on, snapshots fingerprinted, `registry_as_of` on the label, stale-evidence refusal, WriterId write-back, per-world rooms — DEC-0084 stays dead; or (ii) move the hub to Deferred as "operator-unratified DC-2 candidate" and remove it from the deployment diagram until ratified. Do not leave a central box unnamed against a dead DEC.

**Class:** silent weakening (DEC-0084), with an inherited-claim mismatch (the table says the DEC binds; the diagram does not).

---

### Finding 7 — SILENT WEAKENING — B-8 "train/test" vs AD-21 split manifests

**Parent AD-21:** splits are fingerprinted, time-ordered, **non-overlapping** manifests; each pins **exactly one calendar identity + version in-band**; boundaries are stored TradingDates or instants (never civil dates); records partition by **knowledge time** (confirmed-at / knowable-at), not event time; a manifest refuses observed-at-before / confirmed-at-after rows unless a declared **embargo** covers the gap; **purge and embargo widths are required fields** and enter the fingerprint; the **12-month seal** is a `policy rejection` at every qmf-data read, independent of deferred GAP-0016/0017.

**What QMB says:** "Train/test separation is declared in the run spec and enforced by split-manifest reads (AD-21)." B-14 walk-forward is a library function with no split-manifest rule of its own. Inherited row claims "12-month seal + split manifests enforced at every read."

**How it weakens:** "train/test" is a two-bucket event-time cut. It does not mention knowledge-time, embargo/purge, in-band calendar, frozen seal TradingDate, or walk-forward's N manifests. An implementer can ship a boolean `split: train|test` in the run spec, read two date ranges, and claim AD-21. That is how look-ahead returns (the thing GAP-0016 was deferred *because* AD-21 already had to hold the line without it).

GAP-0016/0017 themselves are honestly deferred (B-4/B-8 accrue raw material, no campaign budgets minted). That honesty does not license thinning AD-21.

**Fix:** B-8/B-12/B-14: every run names split-manifest fingerprints; reads go through qmf-data and therefore inherit seal/embargo/knowledge-time/calendar-in-band. "Train/test" is at most a display alias for two such manifests, never a substitute. Walk-forward = a sequence of manifests, each a first-class run (already B-14's "every procedure produces labeled runs") with its own split fingerprint in the label.

**Class:** silent weakening.

---

### Finding 8 — INHERITED-CLAIM MISMATCH — B-2 config-selected clock vs B-7 derived world vs AD-8's core Clock protocol

**Parent AD-8:** Clock access is a **qmf-core protocol**; the composition root injects the real clock or a data-driven replay clock; nothing below the root reads the system clock; two *kinds* (wall/Instant vs monotonic diagnostic). AD-12 defines what each **world** means; the clock is how that world is implemented, not how it is chosen.

**What QMB says:**

- Inherited AD-8 row: "Clock is an injected protocol; nothing below the composition root reads the system clock." Faithful as far as it goes; does not say *which* protocol.
- Paradigm / B-2: QMB exposes a **clock port**; the run-config binds it; "Backtest/replay/live/simulated differ only by which clock and adapters the run-config binds."
- B-7: "world is derived from input data provenance, **never caller-declared**."

**How the claim misses:**

The inherited table says QMB honours AD-8's injected protocol and AD-12's worlds. B-2 then mints a QMB-owned clock port selected by config (caller-declared world) and B-7 forbids caller-declared world. Those two B-ids cannot both be true, and neither is an implementation of the parent seam until the frontier clock is named as **the AD-8 Clock protocol, injected at QMB's composition root (the door), implemented as a data-driven replay clock over recorded Instants**.

A config that binds a replay clock to synthetic-tainted data is the test: B-7 says `world = simulated` (data wins); B-2 says replay (clock wins). Parent AD-12 says simulated, and writing it into governed evidence refuses (Finding 3). The child must refuse the mismatch, not pick a winner in two places.

Warm-up as a "pre-seeded, trading-locked phase" is compatible with AD-22 (warm-up = integer observation count, never a Duration) only if B-2 states that unit. It currently does not. Low, bundled here.

**Fix:** B-2: the frontier clock **is** an implementation of qmf-core's AD-8 Clock protocol (replay: pure function of the data cursor; live: injected real clock at the door, deferred). It does not choose `world`. B-7 remains the world function: provenance → world, mismatch with bound adapters → `invalid input` / `policy rejection`. Simulated stays untyped until GAP-0048 (Finding 3). Warm-up unit = AD-22 observation count.

**Class:** inherited-claim mismatch (internal B-id contradiction riding on it).

---

### Finding 9 — INHERITED-CLAIM MISMATCH — AD-15 library purity vs `optimize/` trial runner; AD-2 "uv workspace" vs L21

**AD-15 / inherited row:** "The library never spawns threads/background work; values immutable; one-writer-per-stream." AD-15 itself: QMF never spawns; **the application owns all concurrency**.

**AD-2 / L21:** QMF is one uv workspace of seven `qmf-*` packages; applications (explicitly including backtest workspaces) are **outside this repo's scope**. Discovery is explicit registration, never ambient scanning / reflection.

**What QMB says:**

- L21 row: QMB is an application outside the QMF repo, built with QMF. Correct.
- AD-1/AD-2/AD-3 row: "CPython 3.14 pinned; **uv workspace**; ruff/pyright-strict/pytest/poe gates apply to QMB code."
- Structural seed: `optimize/` lives *inside* the library and is "parameter schema, sampler port, **trial runner** (B-8)." B-5 (process-per-run, stdlib process management) binds "all concurrent execution."
- Paradigm: no ambient discovery. Holds.
- Packaging: one `qmb` wheel, `uv add qmb`, qmf-* consumed lockstep. Holds as an application distribution.

**How the claims miss:**

1. If `optimize/`'s trial runner is the process supervisor, the **library** owns concurrency and spawns — contradicting the inherited AD-15 sentence. If the door/runner owns processes and `optimize/` only proposes trial configs + a sampler port, AD-15 holds — but the seed currently says "trial runner." Optuna `n_jobs` / heartbeat threads inside the default adapter would also be library-spawned background work unless the adapter is pinned `n_jobs=1` and the process fan-out stays in B-5's runner.
2. "uv workspace" on the AD-2 inherited row reads as "QMB is a member of the QMF workspace," which L21 forbids. QMB may *be* its own uv workspace, or a single package; it may not be the eighth roster package. The Stack table ("qmf-* workspace packages | lockstep QMF release") already says the right thing; the inherited row says the wrong one.

Ambient-discovery / no-reflection: **holds** (explicit registration, config-composition, hand-written doors). CPython 3.14 and the toolchain applied to QMB's *own* source: **holds** (AD-3's don't-box-in governs QMB's consumers — notebooks, bots — not QMB's own tree).

**Fix:** move process fan-out fully under B-5 (door/runner); `optimize/` = schema + sampler **port** + trial-config compiler, no process spawn, Optuna adapter `n_jobs=1`. Inherited AD-2 row: drop "uv workspace" or say "QMB is its own installable package (L21), not a QMF roster member; it consumes the QMF workspace's lockstep pins."

**Class:** inherited-claim mismatch.

---

### Finding 10 — HYGIENE — vocabulary, AD-11 MCP rendering, inherited-table ids

1. **`BarSpec`, never bare "timeframe" (parent Conventions / AD-22).** QMB B-11 "resolution", B-12 "timeframe list" / "timeframes" / binds "multi-timeframe". Parent: `BarSpec` is the noun; no other package may define `Bar`. QMB chart "candles" must be `Bar` + `BarSpec` or they are a second series vocabulary. Not a money-path conflict by itself (Finding 4 covers prices); it is an inherited-convention violation that will fork live/replay series identity.

2. **AD-11 MCP.** Python door now returns unions (prior finding closed). CLI → nonzero + stderr JSON is legitimate transport rendering **if** the JSON is the typed refusal (category, context, retryability). "MCP returns error objects" does not bind those three fields; JSON-RPC `InternalError` would swallow AD-11. State that MCP `error.data` carries the refusal union verbatim, same as stderr JSON.

3. **Inherited-table hygiene.**
   - Ids are **not renumbered**. Good; required.
   - Restatements currently rewrite law (Findings 2, 4). Quote or cite; do not paraphrase field sets.
   - `D1 / DEC-0084..0086 | kernel rulings` — `D1` is not a parent spine id (parent build-our-own is DEC-0013; D1/DC-1 live in the companion). `kernel` is parent-banned vocabulary, just restored to QMB's own ban list. Rename the source cell.
   - Load-bearing parent ADs QMB actually exercises are absent from the table and then tripped over: **AD-5** (two ladders, SemVer display-only), **AD-22** (BarSpec, named conversions), **AD-23** (metric producers), **AD-32** (bar shape). Absence is not a conflict; it is how Findings 1–5 got written as if they were greenfield.

4. **Configurable = UI-editable** (parent standing inherited row, 2026-08-20) is not in QMB's table. Bot parameter schemas (B-8) and named condition presets (B-3) are configurable variables minted in QMX. Either declare `ui-editable | uneditable` on them or explicitly defer the flag to platform templates. Not a B-id conflict at this altitude; record so the documentation factory does not drop the standing rule.

5. **Prior reconcile-qmf findings, re-checked closed (do not re-open):**
   - "kernel" as product noun — gone from paradigm/B-2/seed; restored to the ban list.
   - Config fragments = derived artifacts with AD-16 lineage, not a new kind.
   - Python door returns unions; exceptions = programmer error.
   - `R-4` / `R-8` dangling cites — gone.
   - Frontier clock "monotonic" kind collision — amended to monotonically non-decreasing + not the diagnostic kind.
   - "swap" → financing/admin fee, colloquial aside only.
   - 12–14 framed as AD-13 motivating reference.
   - Ledger = WriterId-scoped fragments (currency-lens Windows/PIPE_BUF issue closed).
   - Primary install channel = `uv add qmb`; `uvx`/`uv tool` CLI-only.

**Class:** hygiene.

---

## Part B — Inherited Deferred: what QMB honestly left vs what it pretended to settle

| Parent Deferred | QMB Deferred / body | Honest? |
| --- | --- | --- |
| GAP-0016 look-ahead registration gate | Deferred with 0049/0017; B-4/B-8 accrue raw material; **no** campaign-budget mint (the retracted v1 move) | **Yes** |
| GAP-0017 attempt counter | Same row; every trial is a run (raw material) without a budget policy | **Yes** |
| GAP-0049 SR* / search-quality threshold | Same row; pass batteries explicit candidates, not values | **Yes** |
| GAP-0047 QML | Deferred; plain-Python bots until then; QML gates governed evidence, not tunnel entry | **Yes** — don't-box-in + non-foreclosure held |
| GAP-0048 fidelity taxonomy + **simulated-time typing** (unlocks `world = simulated`) + backtest-mimics-live | Fidelity: B-6 `optimistic` taint, cannot spend split budget, cannot claim edge — **seam held**. Simulated-time: Deferred row says wait; B-2/B-7/B-14 settle typing, claim classes, and ledgered simulated runs | **No — Finding 3** |
| Admission-bar **threshold values** | Pass batteries / thresholds deferred; B-4 still emits a composite pass/fail | Thresholds honest; **verdict shape is Finding 1** |
| Alpha-decay mathematics | Unmentioned (correct: AD-41 primitives, math later) | **Yes** |
| Prop-firm extension | "socketed upstream (DEC-0082); nothing in QMB may preclude them" | **Yes** |
| Live / UI / MCP details / cloud-burst | Deferred as application/platform territory | **Yes** (MCP rendering still needs the AD-11 sentence — Finding 10) |

---

## Part C — What holds (checked, no finding)

- **L21 shape.** QMB is an application, not an eighth roster package, not a second framework. B-ids, not AD-42+. Vocabulary: library + CLI, "engine" banned. Paradigm (config-composition, one tunnel, thin doors) matches DEC-0022's "no loop in qmf-core."
- **AD-13 / B-5 "12–14".** Motivating reference, gated on a future fingerprinted baseline. Same idiom as the parent's ~40-bot ladder. Not an invented budget.
- **AD-15 ledger merge (the Windows/PIPE_BUF half).** WriterId-scoped fragments, merge on read, one writer per file. Matches one-writer-per-stream.
- **AD-11 Python/CLI half.** Return-not-raise at the Python door; CLI rendering as transport. (MCP: Finding 10.)
- **AD-16 fragment kind.** Derived artifact + lineage to CT-22/CT-27, not a newly minted registry kind.
- **AD-12 paper = live.** Inherited row states it. B-7's data-provenance rule does not re-declare paper as a QMB world; live wiring is correctly deferred to the node. A paper *account* replayed from recorded history is `world = replay` with a paper *role* — that is the parent split, available when needed.
- **B-6 GAP-0048 fill seam.** `optimistic` taint; cannot spend split budget; cannot claim edge; forex cost content named as QMX-original; "swap" only colloquial. This half of GAP-0048 is held.
- **B-9 / B-11 rooms and seal (the consume half).** Portable Jupyter gets unsealed split-governed data; sealed evidence never leaves controlled rooms; one final look stays a write-gated occurrence on the controlled side; data commands are thin fronts over CT-10/CT-15; no shipped market data; Dukascopy is a **source** (already named in parent AD-21), not a venue, so AD-9's no-named-broker rule is intact; bid+ask preserved.
- **B-1 door parity.** Tier-2 contract test; MCP sibling not stacked over HTTP; UI consumes the Python API in-process. Matches the Jesse three-stacks counterexample the parent sitting recorded.
- **AD-2 no ambient discovery.** Config-composition; explicit registration; hand-written doors. LEAN-style reflection stays banned.
- **CPython 3.14 + toolchain on QMB's own source.** Legitimate. don't-box-in still protects QMB's consumers.
- **Two ladders as a packaging story.** QMB version ≠ QMF roster version. The *display* half of AD-5 is right; the *identity* half is Finding 2.
- **B-3 resolved run-config.** One frozen, schema-validated artifact per run, fingerprint in the label, Book/BMS compiled not hand-edited. Compatible with AD-10/AD-30's "numbers live inline and are identity-bearing" once Finding 5's cite is a fingerprint.
- **Prop-firm non-foreclosure, QML non-foreclosure, no donor code (shapes only), no Ray/Docker/daemon on the compute path.**

---

## Part D — Items to put to the operator

None of these reopen AD-1..41. They are QMB-side choices where the child currently conflicts and the parent already ruled.

1. **Finding 1 / CT-32.** Confirm QMB's canonical result **is** CT-32 (plus display-only charts), and that the ledger stores per-requirement outcomes, not one pass/fail. That is consumption, not a new kind.
2. **Finding 3 / L20.** Confirm synthetic candle-perturbation is infra-stress only and **cannot** feed the Book bar, until and unless the operator explicitly overrides L20. Memlog 133 did not.
3. **Finding 6 / HUB.** Confirm DC-2 (dumb file-sync hub, computes nothing) as a B-id, or strip the box from the diagram until ratified. Leaving it drawn while DEC-0084 is claimed in force is how the always-on service returns.
4. **Finding 5.** Confirm Book/BMS cites are fingerprints, with human aliases as pointer records — not `scalping@2` SemVer.

Finding 2 (SemVer out of identity, `provenance = sandbox`) and Finding 4 (named Optuna conversion, display-only downsample, restore AD-7 restatement) are recorded parent law and do not need a new ruling.

---

## Bottom line

The child spine is buildable only if factory agents treat B-4/B-10/B-13/B-6/B-7/B-14 as *local* law. Against AD-1..41 they are not: they mint a second result kind, a composite bar, a version-string Book cite, SemVer-in-identity labels, a float-bearing optimize key, a simulated-world evidence path, and a central hub. That is the opposite of L21-on-QMF. Amend the B-ids to consume; do not amend the ADs to accommodate.
