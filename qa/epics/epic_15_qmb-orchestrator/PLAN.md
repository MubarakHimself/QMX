# Verification PLAN — Epic 15: QMB Orchestrator, Ledger & Concurrency

**Audit tier:** T2 (high scrutiny — the sole impure component; owns every write, every process, and the one-ledger-line law).
**Package under test:** `qmb/src/qmb/orchestrator/` (`spawn.py`, `watch.py`, `worker.py`, `governor.py`, `ledger.py`, `log.py`, `paths.py`, `study.py`) and `qmb/src/qmb/ledger/` (`line.py`). Seams into the pure library `qmb/src/qmb/**` (the `run()` contract) and into qmf-data's CT-11/CT-13 append-store.
**Delivers:** all of **FR-045** — process-per-run under a governed cap; exactly one ledger line per run.
**Governing invariants:** QMB spine **B-4** (pure `run()` returns; the orchestrator writes logs and exactly ONE ledger line; WriterId-scoped JSONL fragments; merge-view reads) and **B-5** (process-per-run concurrency; min(cpu, memory) governor with enqueue-on-full; cancel tokens + per-run limits; no Ray/Docker/daemon). Supporting: **AD-15** (library spawns nothing; the application owns all concurrency), **AD-12** (result label), **AD-14** (operational logs, never evidence), **AD-40** (unit-kinded measures), **CT-04** (typed refusal register), **CT-11** (logs are not evidence-bearing), **CT-13** (WriterId / append-with-fsync / gap-signals-loss), **CT-32** (the ledgered result fingerprint).

> **PROCESS GAP (read first).** Two authorities named in the audit brief **do not exist in this worktree**:
> `_bmad-output/test-artifacts/test-design-qa.md` (the Per-Epic Test Plan Template + the L0–L6 test-level architecture) and
> `_bmad-output/test-artifacts/test-design/QMX-handoff.md` (the 15 P0/P1 assertions + this epic's risk-gate rows). `_bmad-output/test-artifacts/` is absent entirely; a full-tree search matches only `archive/recovery/*/restart-handoff.md`.
> **Consequence:** the 8-section structure follows the ratified sibling plans (`qa/epics/epic_14_qmb-run-loop/PLAN.md`, `qa/epics/epic_13_qmb-substrate/PLAN.md`), and the **L0–L6 taxonomy in §5 is adopted from Epic 13 §5 — which explicitly pre-assigns L5 ("end-to-end governed run: loop → CT-32 → ledger line") and L6 ("non-functional: performance, concurrency, governor budgets") to _this epic_.** The behaviour set in §2 is **derived from the ratified spine** (B-4/B-5 + Epic 15 ACs + SCN-0012), not transcribed from the missing handoff. The four risk gates — **R-009** (refusal-register rows), **R-010** (exactly one ledger line), **R-011** (branch behaviour by requirement), **R-017** (perf claims not invented) — are taken **verbatim from the task brief**. When the two files are restored, re-reconcile §1 template order, §3 risk-gate rows, and §5 level definitions against them before executing.

---

## Section 1 — Epic Context, Scope & Authorities

**What this epic is.** The one **impure** component of QMB — the composition root. The pure library computes and RETURNS; the orchestrator does everything the library is forbidden to do: it spawns each run as an isolated OS process (stdlib, no Ray/Docker/daemon) with its own output directory named by the run id; it runs a governor that bounds parallelism by `min(cpu budget, memory budget)` and enqueues (never oversubscribes) when full; it issues a cancel token and declared per-run time/memory limits whose breach is a typed `aborted`; it owns the injected **log sink** and **ledger sink**, streaming each run's operational log and appending **exactly ONE** ledger line per run (completed or aborted, never zero, never two) as a WriterId-scoped JSONL fragment; and it serves ledger reads as a world-and-role-scoped merge view. The library's `run()` is a **pure function** — it writes nothing; **no write may escape `run()`**.

**In scope (Stories 15.1–15.5):** process-per-run + isolated output dirs (15.1); the min(cpu,mem) governor with enqueue-on-full (15.2); cancel tokens + per-run limits + typed `aborted` (15.3); the one-ledger-line law over WriterId-scoped JSONL fragments with merge-view reads (15.4); per-run AD-14 operational logs streamed by the orchestrator (15.5).

**Out of scope (owned elsewhere, seams only here):**
- The event-slice run loop, the sub-phase order, fills, warm-up, and the CT-32 result **content** → **Epic 14** (B-2/B-6). Here `run()` is a stub/black box that RETURNS a result-or-refusal; the orchestrator's job is to spawn it, govern it, and ledger the outcome — never to compute or verify the result's numbers.
- The config compiler, the resolved-config fingerprint (= run-id root = ledger key), the registry-read port, and the `world=replay` binding mint → **Epic 13** (B-3/B-15). SCN-0012 **Branch A** (stale Book ref → stale-evidence refusal) is a registry-read behaviour owned by Epic 13; **noted, not tested here.**
- The Book-bar **read-time verdict fold** (per-requirement outcomes) → **Epic 19** / Book door. Here only the orchestrator's **write** of `role=confirmation` lines and the **role-scoped selection seam** on read are testable.
- Optimize/sweep generation-stepping (B-8) uses `study.py` in this package but is delivered by **Epic 21**; the orchestrator's spawn/governor/ledger primitives are tested here, the sampler/barrier semantics are not.
- Fidelity taxonomy / `world=simulated` unlock → **GAP-0048**. Only the refuse-until-GAP-0048 seam (a synthetic-store run never enters the governed ledger) is testable now (SCN-0012 Branch B).

**Two senses of "tier" (do not conflate).** *Audit tier* **T2** = this plan's scrutiny level. *Test tier* (`poe check` / `poe check-integration` / `poe check-release`) = the project's execution bands that §5 maps the L0–L6 levels onto. **T2 tier scope (per the brief):** L2 + L3 for every AC (the centre of gravity), targeted L1 unit/properties, L5/L6 system + non-functional checks only where a lower level cannot prove the behaviour (real OS-process isolation, real concurrency), plus the **L6 adversarial source review** (`L6-REVIEW.md` deliverable). Every P0/P1 requirement gets a proof-map row (§8).

**Authorities, in precedence order:**
1. Epic 15 section of `_bmad-output/planning-artifacts/epics.md` (Stories 15.1–15.5, ACs; lines 3082–3208).
2. `docs/` knowledge base: `docs/contracts/ct-04` (typed refusal — the seven-category register), `ct-11` (evidence persistence — per-run logs never evidence; storage-failure), `ct-13` (journal — WriterId / append-with-fsync / gap-signals-loss / correlation_id), `ct-32` (performance result — the ledgered fingerprint); `docs/scenarios/SCN-0012-qmb-replay-run.md` (the golden replay run — steps 4/6/7 + Branch B are the orchestrator/ledger path); `docs/registry/variables.yaml` (the governor/limit configurables + `typed_refusal_codes` register row).
3. `_bmad-output/planning-artifacts/architecture/architecture-QMB-2026-08-20/ARCHITECTURE-SPINE.md` (B-1…B-15; Structural Seed; Consistency Conventions) and the inherited QMX spine (AD-12/AD-14/AD-15/AD-40; AR-17/AR-31/AR-53).
4. *(Missing — see Process Gap)* test-design-qa.md; QMX-handoff.md.

---

## Section 2 — Requirements → Behaviours Traceability

Every row is a testable behaviour extracted from a ratified source. IDs are consumed by the independent test list (§4) and the matrix (§8). "Ref" cites the governing AC / spine / contract.

| # | Behaviour (requirement, stated as an assertion) | Ref | Story |
|---|---|---|---|
| R1 | The orchestrator spawns each run as a **separate OS process** via stdlib process management, with its **own isolated output directory named by the run id**. | AR-50, B-5, AC15.1 | 15.1 |
| R2 | The library's `run()` is **pure**: it spawns no thread/process/background work and **writes nothing** — the orchestrator owns ALL process management and ALL writes. **No write escapes `run()`.** | AD-15, B-4, AC15.1 | 15.1 |
| R3 | There is **no Ray, no required Docker, and no daemon** — sandbox and laptop run the same uv-installed package. | AR-50, B-5, AC15.1 | 15.1 |
| R4 | **No two live runs share a writer** for any file or stream — one-writer-per-stream. | AR-17, B-4, AC15.1 | 15.1 |
| R5 | The governor bounds parallelism by **`min(qmb_governor_cpu_budget, qmb_governor_memory_budget)`**. | AR-50, B-5, AC15.2 | 15.2 |
| R6 | A run whose projected peak memory exceeds the remaining budget gets a **typed refusal or enqueues (enqueue-on-full)** — **never silent oversubscription**. | B-5, FM-6, AC15.2 | 15.2 |
| R7 | On a run finishing in a full governor, **the next queued run is admitted** — finish, then admit next. | B-5, AC15.2 | 15.2 |
| R8 | "12–14 concurrent runs" is a **motivating reference under AD-13, never a validated budget** until a fingerprinted baseline is measured. | B-5, AD-13, AC15.2 | 15.2 |
| R9 | Every submitted run **carries a cancel token** and the declared per-run limits **`qmb_run_time_limit`** and **`qmb_run_memory_limit`**. | AR-51, B-5, AC15.3 | 15.3 |
| R10 | A **limit breach or a cancel** produces a **typed `aborted` refusal with context**. | AR-51, B-5, FM-6, AC15.3 | 15.3 |
| R11 | Aborting one run's process **kills only that process** — sibling processes are untouched. | B-5, AC15.3 | 15.3 |
| R12 | An aborted run dying mid-flight **never writes a partial governed result** — its output stays in its own room. | B-4, AC15.3 | 15.3 |
| R13 | On completing a run the orchestrator appends **exactly ONE ledger line — completed or aborted, never zero, never two** — the aborted line carrying refusal context, **never silently absent**. | AR-51, B-4, AC15.4 | 15.4 |
| R14 | The ledger line carries the full **AD-12 result label** (evidence class; `provenance=sandbox` on factory-sandbox runs), the **CT-32 fingerprint**, the run's **raw AD-40 unit-kinded measures**, the **Book-bar fingerprint as resolved at run time**, and a **discriminated run role** (`confirmation \| trial \| replicate \| aborted`) — and stores **NO pass/fail verdict**. | B-4, AR-59, AC15.4 | 15.4 |
| R15 | The physical ledger is **JSONL append-only fragment files written ONLY by the orchestrator**, one **fp1-canonical** object per line, **LF-terminated, append-with-fsync**, **WriterId-scoped per `(machine, role, worker-slot)`**; concurrent processes never share a file. | AR-53, AR-31, B-4, AC15.4 | 15.4 |
| R16 | A ledger **read** is a **world-and-role-scoped merge view** over fragments; the **Book-bar read selects `role=confirmation` lines only**. | B-4, FM-8, AC15.4 | 15.4 |
| R17 | A **direct library `run()` call** (not through the orchestrator) **produces no governed evidence** — runs enter the governed ledger only through the orchestrator. | B-4, AC15.4 | 15.4 |
| R18 | The orchestrator owns the **injected log sink** and streams each run's operational log into a **per-run log file in the run's output directory**. | B-4, Consistency Conventions, AC15.5 | 15.5 |
| R19 | Per-run logs are **AD-14 operational logs only and are NEVER evidence** — under CT-11 only the raw archive and the journal bear evidence. | B-4, CT-11, AC15.5 | 15.5 |
| R20 | Structured logs crossing package boundaries carry a **`correlation_id` excluded from fp1 identity**. | AR-35, AC15.5 | 15.5 |
| R21 | A **crashed run leaves a partial log in its own room** and **never corrupts any sibling or the ledger**. | B-4, AC15.5 | 15.5 |

**FR/NFR roots:** **FR-045** (process-per-run governor and ledger). Cross-cutting: **CT-04** (every refusal a valid returned typed value), **NFR-02** (no ambient nondeterminism / OS-neutral where feasible).

---

## Section 3 — Risk Assessment, Weak Spots & Priority

**Highest-value risk theme (from the brief + spine):** *the scoreboard and the evidence must never diverge, and nothing may write behind the orchestrator's back.* B-4 exists precisely to prevent **two ledger lines (or zero)** per run "when the library and the orchestrator each think they own the append," and **a dead process that can never report its own crash.** This is the worst-likelihood epic by coverage, and the two named ledger-loss advisory findings sit exactly on the never-zero / never-two seam.

The gates that carry the platform's evidence integrity:

1. **Exactly one ledger line per run (R13) — R-010.** Never zero (a crash must still yield an `aborted` line — the orchestrator observes the dead process and appends it), never two (a completion/observer race must collapse to one). A defect here silently loses or double-counts evidence, corrupting every downstream Book-bar fold. **P0.**
2. **No write escapes `run()` (R2/R17) — the purity law.** If any write (ledger, log, output) originates below the composition root, or a direct library call produces governed evidence, B-4 is broken and concurrent runs can fight for a file. **P0.**
3. **The governor never oversubscribes (R5/R6).** A too-large or over-budget run must be **refused or enqueued, not crashed**; concurrent admission must never exceed `min(cpu, mem)`. **P0.**
4. **Abort isolation (R11).** Killing one run must not touch siblings; each sibling still ledgers exactly one line. **P0.**

**Named weak spots (from the QA harness metrics in the brief):**

| Locus | Metric | Risk implication | Mitigation in this plan |
|---|---|---|---|
| `orchestrator/watch.py` | line **64.3%**, branch **37.0%** | The **death-observer**. 63% of branches unexercised is exactly where a crashed process fails to produce its `aborted` line (never-zero) or races the completion path into a second line (never-two). The single highest-severity blind spot. | The exactly-one-line matrix (Group D: T-15.4-a/b/c/i) and abort/limit paths (Group C: T-15.3-b/c/e) drive every terminal-cause branch of the observer; §7 raises `watch.py` branch floor. **R-011.** |
| `orchestrator/spawn.py` | line **59.8%**, branch **50.8%** | The **process spawner** — isolation, WriterId assignment, output-dir creation, admission wiring. Untested branches here are where two runs could share a writer (R4) or a dir. | Real-process isolation (Group A: T-15.1-a/e L5) + run()-purity (T-15.1-c, T-15.0-*) drive spawn branches; §7 raises `spawn.py` branch floor. **R-011.** |
| `orchestrator/governor.py` | (admission logic) | The min(cpu,mem) bound, enqueue-on-full, finish-then-admit — the oversubscription surface. | Group B (T-15.2-a/b/c/e) drives each admission branch; the governor property (L6) closes the arbitrary-interleaving space. **R-011.** |

**R-011 discipline (branch behaviour by requirement).** For `watch.py`, `spawn.py`, and `governor.py`, every covered branch must be tied to a **requirement-derived assertion**, not a line-coverage incidental. A branch hit by a test that asserts nothing about it is a finding, not coverage. The §8 matrix names, per weak-spot file, which terminal-cause / admission branch each test drives.

**R-017 discipline (perf claims not invented).** The 12–14-concurrent figure is a motivating reference under AD-13 (registry note on `qmb_governor_cpu_budget`), **never a validated budget until a fingerprinted baseline is measured.** **No test in this plan asserts any throughput, latency, or concurrency-count number as a pass criterion.** Governor budgets and per-run limits are read from registry keys (`qmb_governor_cpu_budget`, `qmb_governor_memory_budget`, `qmb_run_time_limit`, `qmb_run_memory_limit`), never invented literals; the only assertion touching the "12–14" figure is that it is **absent** from every gate (T-15.2-f). The L6 non-functional tests assert governor *behaviour* (the min-bound holds; over-budget refuses; enqueue-then-admit) — never a measured speed.

**R-009 discipline (refusal-register rows).** Every refusal Epic 15 emits must be a valid **CT-04** value — category ∈ the **seven** register rows {invalid input, unsupported capability, unavailable dependency, stale evidence, policy rejection, transient venue failure, storage failure} (`docs/registry/variables.yaml` → `typed_refusal_codes`) — **returned, not raised**, carrying machine-readable context. **Nuance to pin (finding-candidate):** `aborted` is a **run role / ledger-line kind**, *not* a CT-04 category; the `aborted` outcome's *refusal* carries one of the seven categories. A test that expects `"aborted"` as a refusal category is itself wrong. The categories are **asserted against the register, never invented** — where the AC does not pin a category (e.g. the governor's over-budget refusal), the test asserts register-membership + returned-not-raised and records the code's chosen category; an off-register or unjustified category is a finding. Categories that ARE pinned: synthetic-store → **policy rejection** (CT-11); ledger-append storage error → **storage failure** (CT-04/CT-11).

**Priority ladder (derived — see Process Gap re: the missing handoff):**
- **P0 (must-pass gate; block the epic on any failure):** R2, R4, R5, R6, R11, R13, R17.
- **P1 (high — evidence honesty & safety):** R1, R9, R10, R12, R14, R15, R19.
- **P2 (important — completeness):** R3, R7, R16, R18, R20, R21.
- **P3 / discipline:** R8 (perf-claim discipline — R-017; a negative assertion, no positive number).

---

## Section 4 — Independent Test List (authored from requirements, BEFORE any src read)

> **Discipline statement.** This section was written having read **zero implementation files** under `qmb/src/qmb/orchestrator/` or `qmb/src/qmb/ledger/`. The package's file names (`spawn.py`, `watch.py`, `governor.py`, `ledger.py`, `log.py`, `paths.py`, `worker.py`, `study.py`; `ledger/line.py`) are taken from the brief and a directory listing only — **no file contents were opened.** Every test below asserts what a *requirement* demands, derived from epics.md ACs, the QMB spine (B-4/B-5), the CT-* contracts, and SCN-0012 — never what the code happens to do. A failing test here is a **finding**, not a licence to edit source or weaken the assertion. Level assignment follows "one behaviour, one level; lower level wins" (taxonomy in §5). Property tests use `hypothesis` (`uv run --with hypothesis ...` if not synced). Every refusal assertion checks a **returned** CT-04 value of a register-legal category (§3 R-009), never a raised exception across a public boundary.

### Group A — Process-per-run & isolation (Story 15.1) → R1–R4 (weak spot: `spawn.py`)

- **T-15.1-a** *(L5)* Real stdlib spawn: submitting a run through the orchestrator starts a **separate OS process** (child PID ≠ orchestrator PID) whose output directory **exists and is named by the run id**. **[R1]** **P1**
- **T-15.1-c** *(L2)* **No write escapes `run()`.** Drive the pure `run()` with an injected **recording ledger sink** and **recording log sink**; `run()` performs **zero** writes to either and **returns** a value — every write in the trace originates from the orchestrator, never from `run()`. **[R2]** **P0**
- **T-15.1-e** *(L5)* One-writer-per-stream: two runs executing as **real concurrent processes** never open the same ledger fragment file or the same log file for writing — each holds a **distinct WriterId** and distinct paths (no shared file handle). **[R4]** **P0**
- **T-15.1-f** *(L2)* Isolated output directories: two stubbed runs receive **disjoint** output directories keyed by run id; a write attempted by one into the other's directory is structurally impossible / refused. **[R1]**

### Group B — Governor: min(cpu,mem) & enqueue-on-full (Story 15.2) → R5–R8 (weak spot: `governor.py`)

- **T-15.2-a** *(L1)* Admission bound = `min(cpu_budget, mem_budget)`: the pure admission function admits **no more than** `min(qmb_governor_cpu_budget, qmb_governor_memory_budget)` concurrent runs; over arbitrary budget pairs the admitted count equals the smaller budget's ceiling. **[R5]** **P0**
- **T-15.2-b** *(L1)* Over-budget refusal: a run whose projected peak memory exceeds the remaining memory budget is **never admitted** — it returns a typed refusal **or** enqueues; there is no path to silent oversubscription. **[R6]** **P0**
- **T-15.2-c** *(L2)* Enqueue-then-admit: with the governor full, a further submit **enqueues**; when a running slot finishes, **exactly the next queued run** is admitted (declared/FIFO order) and the concurrent-admitted count never exceeds the bound at any instant. **[R7]**
- **T-15.2-d** *(L3)* The over-budget/too-large refusal is a valid **CT-04** value: category ∈ the seven register rows (R-009), **returned not raised**, context carrying the machine-readable budget shortfall. **[R6]**
- **T-15.2-e** *(L6)* Governor non-functional property: under an **arbitrary interleaving** of submit/finish/refuse events across many runs, concurrently-admitted runs **never exceed** `min(cpu,mem)` and no over-budget run is ever admitted (hypothesis over an event-sequence model; **no throughput number asserted**). **[R5,R6]** **P0**
- **T-15.2-f** *(L0 / analysis)* **R-017 gate:** a scan of this epic's test suite and the source's admission logic asserts **no throughput/latency/concurrency-count literal is a pass criterion**; the "12–14" figure appears **only** as a documented motivating reference, never a gate; all budget/limit values resolve from registry keys, never invented literals. **[R8]**

### Group C — Cancel tokens & per-run limits (Story 15.3) → R9–R12 (weak spot: `watch.py`)

- **T-15.3-a** *(L2)* Every submitted run **carries a cancel token** and the declared per-run limits **`qmb_run_time_limit`** and **`qmb_run_memory_limit`** (values read from registry keys, referenced not restated). **[R9]** **P1**
- **T-15.3-b** *(L2)* A signalled cancel yields a typed **`aborted`** outcome carrying refusal context. **[R10]** **P1**
- **T-15.3-c** *(L2)* A per-run **time-limit** breach and a per-run **memory-limit** breach each yield a typed **`aborted`** outcome with context (two cases). **[R10]** **P1**
- **T-15.3-d** *(L3)* The `aborted` outcome's refusal is a valid **CT-04** value with a **register-legal category** (not the literal `"aborted"` — §3 R-009), returned not raised, context present. **[R10]**
- **T-15.3-e** *(L5)* Kill-one-not-siblings: with several **real** concurrent run processes, cancelling/killing one terminates **only that PID**; every sibling runs to completion and **each ledgers exactly one line**. **[R11]** **P0**
- **T-15.3-f** *(L2)* No partial governed result: after an abort mid-flight, the run's output directory holds **no CT-32 result artifact and no governed evidence** — only a partial operational log in its own room. **[R12]** **P1**

### Group D — The one-ledger-line law (Story 15.4) → R13–R17 (weak spot: `watch.py`, `ledger.py`, `ledger/line.py`) — **FLAGSHIP: R-010**

- **T-15.4-a** *(L2)* **Flagship — exactly-one-line across the abort/cancel/teardown matrix.** Built from the B-4/B-5 contract, over every terminal cause — `{normal-completion, cooperative-cancel, time-limit-breach, memory-limit-breach, hard-crash-mid-flight (process killed without returning), orchestrator-teardown-while-in-flight}` — the **injected ledger sink** receives **EXACTLY ONE** line for the run: `completed` for the clean case, `aborted` (with refusal context) for every terminal case — **never zero, never two.** **[R13]** **P0 [R-010]**
- **T-15.4-b** *(L2)* **Never-two race guard.** When the completion path and the death-observer (`watch.py`) fire for the same run **near-simultaneously** (return + observed-dead), the sink still receives **exactly one** line (single-owner arbitration / WriterId-keyed idempotent append). **[R13]** **P0 [R-010]**
- **T-15.4-c** *(L2)* **Never-zero crash guard.** A run whose process dies mid-flight **without returning** still yields **exactly one `aborted` line**, appended by the orchestrator's observer with refusal context — **never silently absent.** *(Directly targets the ledger-loss advisory finding and `watch.py`'s 37% branch gap.)* **[R13]** **P0 [R-010]**
- **T-15.4-d** *(L2)* **Admission-refusal / enqueue-cancel boundary.** A run **refused at admission** (over-budget) or **cancelled while still enqueued** (never spawned) produces **ZERO** ledger lines — because no run occurred — and returns the refusal to the caller. This is **not** a never-zero violation; the boundary is pinned so a naive "every submit ⇒ a line" reading cannot misfire. **[R13,R6]**
- **T-15.4-e** *(L3)* Ledger-line content: a `completed` line carries the full **AD-12 result label** (evidence class; `provenance=sandbox` on factory-sandbox runs), the **CT-32 fingerprint**, the run's **raw AD-40 unit-kinded measures**, the **Book-bar fingerprint as resolved at run time**, and a **discriminated run role** ∈ {confirmation,trial,replicate,aborted}; it stores **NO pass/fail verdict**. **[R14]** **P1**
- **T-15.4-f** *(L3)* Physical format: fragments are **JSONL**, one **fp1-canonical** object per line, **LF-terminated**, appended **with fsync**, written **only** by the orchestrator, **WriterId-scoped per `(machine, role, worker-slot)`**; no two concurrent processes share a fragment file. **[R15]** **P1**
- **T-15.4-g** *(L2)* Merge-view read: a ledger read is a **world-and-role-scoped merge** over fragments; a **Book-bar read selects `role=confirmation` lines only** (aborted/trial/replicate lines are excluded from a Book-bar read). **[R16]**
- **T-15.4-h** *(L2)* Direct-library-call ledgers nothing: calling the pure `run()` **directly, not via the orchestrator**, appends **no ledger line** — governed evidence enters only through the orchestrator (the read-twin of the purity law). **[R17]** **P0**
- **T-15.4-i** *(L6)* Exactly-one-line property: over **arbitrary sequences** of `{submit, admit, finish, cancel, crash, teardown}` events across N runs, the ledger-sink line count equals **exactly the number of runs that were admitted/spawned**, each appearing **exactly once** (hypothesis over the terminal-cause model). **[R13]** **P0 [R-010]**
- **T-15.4-j** *(L1)* Ledger-line builder (`ledger/line.py`): given a completed result the builder produces a **schema-valid** record with every required AD-12/CT-32/role field and **no verdict field**; given an abort it produces an **`aborted`-role** record carrying refusal context. **[R14]**
- **T-15.4-k** *(L3)* Storage-failure honesty: when the ledger append itself fails (disk-full / locked / truncated store), the orchestrator surfaces a **`storage failure`** CT-04 refusal (per CT-11/CT-13) and **does not silently drop the line** — the unpersistable append blocks and is recoverable, never a silent never-zero. **[R13,R15]**

### Group E — Per-run operational logs (Story 15.5) → R18–R21 (`log.py`)

- **T-15.5-a** *(L2)* The orchestrator owns the **injected log sink** and streams each run's operational log into a **per-run log file inside that run's output directory**. **[R18]**
- **T-15.5-b** *(L3)* Per-run logs are **AD-14 operational logs only and NEVER evidence**: under CT-11 the per-run log format is **not evidence-bearing** (`is_evidence_bearing=false`); only the raw archive and the CT-13 journal bear evidence. **[R19]** **P1**
- **T-15.5-c** *(L3)* Structured log records crossing package boundaries carry a **`correlation_id` excluded from fp1 identity** (AR-35 / CT-13 correlation-id invariant). **[R20]**
- **T-15.5-d** *(L2)* A crashed run leaves a **partial log in its own room** and corrupts **neither a sibling's log nor the ledger** (paired with T-15.4-c). **[R21]**

### Group F — Golden scenario (SCN-0012) → cross-cutting

- **T-15.SCN-a** *(L4)* **SCN-0012 orchestrator+ledger path (steps 4/7).** One backtest spawns **ONE** governed isolated process under the governor; the pure `run()` returns a **CT-32** artifact; the orchestrator appends **exactly ONE `role=confirmation`** ledger line carrying the AD-12 label + CT-32 fp + raw AD-40 measures + Book-bar fp; **no pass/fail is stored**. **[R1,R13,R14]**
- **T-15.SCN-b** *(L4)* **SCN-0012 Branch B (synthetic store).** A run whose stream set reads a store-persisted **synthetic** series is `world=simulated` and a **policy rejection** for governed evidence — the orchestrator appends **no governed (`confirmation`) ledger line** for it. **[R13,R16 / CT-11]** *(Branch A — stale Book ref — is Epic 13; noted, not tested here.)*

### Group G — Static / structural gates (L0)

- **T-15.0-purity** *(L0)* Static: the pure library surface (everything **below** `orchestrator/`) performs **no writes** — a scan finds no file-open-for-write, no ledger append, and no log-sink write outside `orchestrator/` and the door wiring. **[R2, R17]** **P0**
- **T-15.0-writer-ownership** *(L0)* Static: **all** ledger appends and **all** log writes are reachable **only** from `orchestrator/{ledger,log}.py`; no other module writes the ledger or the log. **[R2, R15, R18]** **P0**
- **T-15.0-no-spawn-below-root** *(L0)* Static: no module below the composition root imports `multiprocessing`/`threading`/`subprocess`/spawns background work; the only spawn call-sites live in `orchestrator/{spawn,worker}.py`. **[R2]**
- **T-15.0-no-runtime-platform** *(L0)* Static: no import of `ray`; no required-Docker path; no long-lived daemon — the package runs from a bare `uv` install. **[R3]**
- **T-15.0-state** *(L0)* Static: **no module-global mutable state** anywhere in `orchestrator/` or `ledger/` — all impurity lives in explicit context objects / injected sinks (Consistency Conventions). **[cross-cutting]**

---

## Section 5 — Test-Level Architecture Mapping (L0–L6)

> Adopted from **Epic 13 §5** (the ratified sibling that pre-assigns L5/L6 to _this_ epic), since `test-design-qa.md` is absent (§1 Process Gap). Rule enforced: **one behaviour, one level; the lowest level that can meaningfully assert it wins** — no behaviour is re-asserted higher except where a property/system test adds coverage a unit cannot (flagged).

| Level | Meaning here | Execution band | Epic-15 population |
|---|---|---|---|
| **L0** | Static / structural gates on source (purity, writer-ownership, no-spawn-below-root, no-runtime-platform, no module-global state, R-017 no-perf-gate). | Tier 1 (`poe check`) | T-15.0-purity, -writer-ownership, -no-spawn-below-root, -no-runtime-platform, -state; T-15.2-f **(6)** |
| **L1** | Pure unit — one pure function (governor admission arithmetic; ledger-line builder). | Tier 1 | T-15.2-a, -2-b, T-15.4-j **(3)** |
| **L2** | Component/integration in-process — the orchestrator wired to a **stub `run()`** + **injected ledger/log sinks** + a **fake process/worker**; the abort/cancel/teardown matrix observed via the injected sink, no real OS process. | **Tier 2** (`poe check-integration`) | T-15.1-c, -1-f, T-15.2-c, T-15.3-a/-b/-c/-f, T-15.4-a/-b/-c/-d/-g/-h, T-15.5-a/-d **(15)** |
| **L3** | Contract conformance — CT-04 refusal register, CT-32 fingerprint & AD-12 label in the line, CT-11 logs-not-evidence, JSONL/WriterId/fsync physical format, storage-failure. | **Tier 2** | T-15.2-d, T-15.3-d, T-15.4-e/-f/-k, T-15.5-b/-c **(7)** |
| **L4** | Scenario / golden-path — SCN-0012 orchestrator+ledger path + Branch B. | **Tier 2** | T-15.SCN-a, T-15.SCN-b **(2)** |
| **L5** | End-to-end governed run with **real OS processes** — process-per-run isolation, one-writer-per-stream across real processes, kill-one-not-siblings. | Tier 2/3 | T-15.1-a, -1-e, T-15.3-e **(3)** |
| **L6** | Non-functional / property — governor concurrency invariant, exactly-one-line invariant, concurrency-fingerprint invariance (**behaviour only; no perf number** — R-017). | Tier 3 (`poe check-release`) / property | T-15.2-e, T-15.4-i, **T-15.6-conc** *(byte-identical CT-32 fp under N real concurrent siblings — shared with Epic 14 R33; see §8)* **(3)** |

**Planned counts — L0: 6 · L1: 3 · L2: 15 · L3: 7 · L4: 2 · L5: 3 · L6: 3** → **39 planned checks.**

**Lower-level-wins applications:**
- The exactly-one-line law is proven **in-process at L2** (T-15.4-a, the full matrix via the injected sink — the cheapest level that can observe every terminal cause) with an **L6 property** (T-15.4-i) for the arbitrary-sequence space `watch.py` branches cannot enumerate by hand; it is **not** re-run as a real-process case except where a terminal cause (real crash, real kill) can only exist with a real process (T-15.3-e L5).
- Governor admission is asserted at **L1** (T-15.2-a/b, pure arithmetic) with the **L6** property (T-15.2-e) as breadth — not a duplicate concrete case.
- Purity is asserted **statically at L0** (T-15.0-purity/-writer-ownership) and **behaviourally at L2** (T-15.1-c recording-sink) — two distinct proofs (structure vs runtime), not a duplication.
- The `aborted` **refusal shape** folds once into **L3** (T-15.3-d); the *triggering* behaviours (cancel, time-breach, mem-breach) sit at **L2** (T-15.3-b/c).

---

## Section 6 — Fixtures, Data & Determinism Strategy

**Fixtures (controlled test fixtures only; no product mock data, no default strategies):**
- **Injected sinks (the spine of the R-010 proof):** a **recording ledger sink** and a **recording log sink** that capture every append with its WriterId, ordering, and payload. The exactly-one-line matrix (Group D) is observed **through the injected ledger sink** — never by reading a real file — so the count assertion is exact and deterministic.
- **Stub `run()` and fake worker/process:** a black-box `run()` that can be scripted to `{return a result, return a refusal, hang, raise, be killed}` on cue, and a fake process handle that can be driven to `{exit-0, exit-nonzero, die-without-return, be-cancelled, still-be-in-flight-at-teardown}` — the terminal-cause axis of the matrix. A **near-simultaneous return + observed-dead** harness drives the never-two race (T-15.4-b).
- **Real-process fixtures (L5 only):** a minimal real spawned child (bare uv-installed entry) used **only** where a behaviour cannot exist without a real OS process — isolation, distinct PIDs, one-writer-per-stream across processes, kill-one-not-siblings, and the concurrency-fingerprint invariant.
- **CT-04 / CT-11 / CT-13 / CT-32 fakes** are **shape-faithful** to the ratified contracts (refusal categories, `is_evidence_bearing`, WriterId/sequence, fp1-canonical line, AD-12 label fields, AD-40 unit-kinds). A test that passes against a shape-unfaithful fake is itself a finding.

**Determinism & honesty strategy:**
1. **Observe writes, don't measure speed (R-017).** The matrix is asserted on the **injected sink's line count**, never on timing. No test asserts a throughput, a latency, or the 12–14 figure as a gate (T-15.2-f). Governor/limit values are **referenced by registry key** (`qmb_governor_cpu_budget`, `qmb_governor_memory_budget`, `qmb_run_time_limit`, `qmb_run_memory_limit`), never restated as literals — the walk names keys, not numbers (SCN-0012 discipline).
2. **Build the matrix from the contract, not the code.** The terminal-cause set is enumerated from B-4/B-5 + the ACs (completion, cancel, time-breach, mem-breach, crash, teardown) **before** any src read — so a cause the code forgets to handle surfaces as a **missing line (finding)**, not an untested path.
3. **Refusal register discipline (R-009).** Every "is refused" assertion checks a **returned** CT-04 value whose category is one of the **seven** register rows and matches what the requirement pins where it pins one (synthetic-store → `policy rejection`; append failure → `storage failure`); `aborted` is asserted as a **role/kind**, never as a category. An exception raised across a public boundary, or an off-register category, is a finding.
4. **Concurrency invariance without a perf claim.** T-15.6-conc asserts a run alongside N real concurrent siblings yields a **byte-identical CT-32 fingerprint** to the isolated run (concurrency is a scheduling decision only) — an identity assertion, not a speed one; shared with Epic 14 R33.

**Refusal harness.** Assert refusals are RETURNED as one arm of a result union carrying `{category ∈ 7, context present/non-null, retryability}`; assert the **absence of prohibited side effects** — no ledger line from a direct library call (T-15.4-h), no write from the pure `run()` (T-15.1-c), no second writer on a shared stream (T-15.1-e).

---

## Section 7 — Coverage Targets & Weak-Spot Plan

**Global posture.** Coverage is a *floor and a map*, never the goal — a green line with no assertion is a finding (R-011). Targets are gates for the epic to pass audit; a shortfall is recorded, not waived.

| Target | Floor | Rationale |
|---|---|---|
| `orchestrator/` package line coverage | ≥ 85% | T2 epic; the sole impure component — every write and process passes through it. |
| `orchestrator/` package branch coverage | ≥ 80% | Branch is where the terminal-cause / admission guards live. |
| **`watch.py` branch coverage** | **≥ 85%** (from **37.0%**) | The death-observer: the 63% unexercised branch space is exactly the never-zero / never-two surface. Group D (T-15.4-a/b/c/i) + Group C (T-15.3-b/c/e) must close it, **each branch tied to a terminal-cause assertion** (R-011). |
| **`spawn.py` branch coverage** | **≥ 80%** (from **50.8%**) | Isolation, WriterId assignment, output-dir creation, admission wiring. Group A (T-15.1-a/c/e/f) + governor seam drive these; each branch tied to an isolation/purity assertion (R-011). |
| `governor.py` branch coverage | ≥ 85% | The min-bound / enqueue / finish-then-admit branches — Group B (T-15.2-a/b/c/e). |
| `ledger.py` + `ledger/line.py` branch | ≥ 85% | Append path + line schema — T-15.4-e/f/j/k. |
| Mutation sensitivity (watch.py, ledger.py) | spot-check | For the P0 guards (exactly-one-line, never-two, never-zero, no-write-escapes), a mutation that flips the guard (e.g. drop the crash-observer append, or double-append on the race) **MUST** fail a test; a surviving mutant means the test is decorative — record as a finding. |

**Explicit non-target (R-017).** There is **no** coverage or performance target expressed as a run-count or a throughput. The 12–14 figure is never a floor, a ceiling, or a gate.

**Weak-spot execution order (do the riskiest work first):**
1. `watch.py` exactly-one-line matrix incl. never-zero + never-two (Group D T-15.4-a/b/c/i) — the largest coverage gap and the highest-severity evidence loss.
2. `orchestrator/ledger.py` + `ledger/line.py` content + physical format + storage-failure (T-15.4-e/f/j/k).
3. `spawn.py` real-process isolation + purity (Group A + T-15.0-*).
4. `governor.py` min-bound + enqueue + property (Group B).
5. SCN-0012 golden path + Branch B (Group F) — depends on 1–4 being green.

---

## Section 8 — Execution, Traceability Matrix & Exit Criteria

**Execution.**
- Run from the worktree root: `uv run pytest qa/tests/epic_15 -q` for L0/L1/L2; the `poe check-integration` band for L3/L4/L5; `poe check-release` (or a marked slow lane) for L6. Properties: `uv run --with hypothesis pytest ...` if hypothesis is not in the synced dev group.
- All tests live under `qa/tests/epic_15/`; **source is read-only evidence.** A failing test is a **finding recorded in `qa/epics/epic_15_qmb-orchestrator/findings.csv`**, never a reason to edit `orchestrator/`/`ledger/` source or soften an assertion.
- **OS note (Windows host):** real hard **memory-limit enforcement** on a child process is OS-specific (Windows Job Objects vs POSIX `rlimit`). The **cooperative/observed** breach (T-15.3-c, L2) is portable and is the gate; the real-enforcement L5 case is OS-conditional — a missing enforcement mechanism is recorded as an **OS-gap finding**, not silently skipped.

**Traceability (requirement → test → priority → level → status):** every R1–R21 maps to ≥1 test.

| Req | Test IDs | Prio | Level(s) | Status |
|---|---|---|---|---|
| R1 | T-15.1-a, T-15.1-f, T-15.SCN-a | P1 | L5,L2,L4 | planned |
| R2 | T-15.1-c, T-15.0-purity, T-15.0-writer-ownership, T-15.0-no-spawn-below-root | **P0** | L2,L0 | planned |
| R3 | T-15.0-no-runtime-platform | P2 | L0 | planned |
| R4 | T-15.1-e | **P0** | L5 | planned |
| R5 | T-15.2-a, T-15.2-e | **P0** | L1,L6 | planned |
| R6 | T-15.2-b, T-15.2-d, T-15.2-e, T-15.4-d | **P0** | L1,L3,L6,L2 | planned |
| R7 | T-15.2-c | P2 | L2 | planned |
| R8 | T-15.2-f | P3 | L0 | planned (negative assertion — R-017) |
| R9 | T-15.3-a | P1 | L2 | planned |
| R10 | T-15.3-b, T-15.3-c, T-15.3-d | P1 | L2,L3 | planned |
| R11 | T-15.3-e | **P0** | L5 | planned |
| R12 | T-15.3-f | P1 | L2 | planned |
| R13 | T-15.4-a, T-15.4-b, T-15.4-c, T-15.4-d, T-15.4-i, T-15.4-k, T-15.SCN-a/-b | **P0 [R-010]** | L2,L6,L3,L4 | planned |
| R14 | T-15.4-e, T-15.4-j, T-15.SCN-a | P1 | L3,L1,L4 | planned |
| R15 | T-15.4-f, T-15.4-k, T-15.0-writer-ownership | P1 | L3,L0 | planned |
| R16 | T-15.4-g, T-15.SCN-b | P2 | L2,L4 | planned |
| R17 | T-15.4-h, T-15.0-purity | **P0** | L2,L0 | planned |
| R18 | T-15.5-a, T-15.0-writer-ownership | P2 | L2,L0 | planned |
| R19 | T-15.5-b | P1 | L3 | planned |
| R20 | T-15.5-c | P2 | L3 | planned |
| R21 | T-15.5-d, T-15.4-c | P2 | L2 | planned |

**Risk-gate proof-map (every P0/P1 gate → the tests that prove it):**

| Gate | Proven by | Prio |
|---|---|---|
| **R-010 — exactly one ledger line per run (never zero, never two), across the whole abort/cancel/teardown matrix** | **T-15.4-a** (full matrix via injected sink), **T-15.4-b** (never-two race), **T-15.4-c** (never-zero crash), **T-15.4-i** (property over arbitrary event sequences), **T-15.4-d** (admission-refusal ⇒ zero, correctly), **T-15.4-k** (append storage-failure not a silent loss), **T-15.3-e** (each real sibling ledgers exactly one) | **P0** |
| **R-009 — refusals are register rows** | **T-15.2-d** (governor refusal ∈ 7, returned), **T-15.3-d** (`aborted` refusal ∈ 7, not the literal "aborted"), **T-15.SCN-b** (synthetic-store → `policy rejection`), **T-15.4-k** (append fail → `storage failure`) | P1 |
| **R-011 — branch behaviour by requirement** | `watch.py`: T-15.4-a/b/c/i + T-15.3-b/c/e; `spawn.py`: T-15.1-a/c/e/f + T-15.0-*; `governor.py`: T-15.2-a/b/c/e — §7 floors, each covered branch tied to a named assertion; mutation spot-check on the P0 guards | P1 |
| **R-017 — perf claims not invented** | **T-15.2-f** (no throughput/count literal is a gate; "12–14" only as motivating reference; budgets by registry key), and the L6 tests assert **behaviour** not speed (T-15.2-e, T-15.4-i, T-15.6-conc identity-only) | P3 |
| **No write escapes `run()`** | **T-15.1-c** (recording sinks: run() writes nothing), **T-15.0-purity** + **T-15.0-writer-ownership** (static), **T-15.4-h** (direct library call ledgers nothing) | **P0** |
| **Governor never oversubscribes** | **T-15.2-a/-b** (min-bound + over-budget refusal), **T-15.2-e** (property), **T-15.2-c** (enqueue-then-admit) | **P0** |
| **Abort isolation** | **T-15.3-e** (kill one real process, siblings survive + ledger) | **P0** |

**Exit criteria (epic passes audit when):**
1. Every **P0** test is green and mutation-sensitive on its guard; **R-010** is green for **every** terminal cause in the matrix (T-15.4-a/b/c/i/k), and the admission-refusal boundary (T-15.4-d) is pinned.
2. `watch.py`, `spawn.py`, and `governor.py` meet their §7 branch floors, **each covered branch tied to a requirement assertion** (R-011).
3. Every refusal test asserts a **returned** CT-04 value of a **register-legal** category (R-009); no test expects `"aborted"` as a category.
4. **No test asserts any throughput/latency/run-count number as a pass criterion** (R-017); T-15.2-f confirms the "12–14" figure is absent from every gate.
5. The purity law holds: `run()` writes nothing (T-15.1-c + statics) and a direct library call ledgers nothing (T-15.4-h).
6. Every deferred/partial/OS-conditional item (below) has a recorded reason and an owning epic — none silently counted as passed or failed.

**Untestable / deferred / OS-conditional in Epic 15 isolation (findings, not omissions):**
- **R8 — the "12–14 concurrent" budget as a number.** Decided-deferred: a validated budget needs a fingerprinted baseline (AD-13); only the **min-bound behaviour** is testable, never the count. Asserting a number would invent a perf claim (R-017).
- **Real hard memory-limit enforcement (R10, memory axis).** OS-specific (Windows Job Objects vs POSIX `rlimit`). The portable gate is the cooperative/observed breach (T-15.3-c, L2); the real-enforcement L5 case is OS-conditional and any missing mechanism is an **OS-gap finding**.
- **CT-32 result *content* correctness (measure math).** Owned by **Epic 14** (run loop) / **Epic 19** (reports). Here the ledger must **faithfully carry** the fingerprint + raw AD-40 measures (T-15.4-e); their **computation** is out of Epic 15 scope.
- **The Book-bar read-time verdict fold.** Owned by **Epic 19** / the Book door. Here only the orchestrator's **write** of `role=confirmation` (T-15.SCN-a) and the **role-scoped read-selection seam** (T-15.4-g) are testable — not the per-requirement verdict.
- **SCN-0012 Branch A (stale Book ref).** A **registry-read** behaviour owned by **Epic 13**; noted, not tested here.
- **`provenance=sandbox` correctness beyond field-presence.** Depends on a factory-sandbox deployment context not reproducible in isolation; here only that the field is **present and derived** in the line (T-15.4-e).
- **Optimize/sweep generation-stepping (`study.py`).** The spawn/governor/ledger primitives are tested here; the sampler/barrier/`n_jobs=1` semantics are **Epic 21** (B-8).
- **Process authorities absent.** `test-design-qa.md` (template + L0–L6) and `QMX-handoff.md` (15 P0/P1 assertions + risk-gate rows) are missing from the worktree; §1/§3/§5 are reconstructed from the ratified sibling plans and the task brief, and must be reconciled when restored. The single largest caveat on the plan's fidelity to the intended template.

**Deliverables for this epic:** `PLAN.md` (this file), `qa/tests/epic_15/` (the tests), `RESULTS.md` (per-test PASS/FINDING/DEFERRED + evidence paths), `findings.csv` (one row per finding), and **`L6-REVIEW.md`** (the adversarial source-review pass over `orchestrator/` + `ledger/`, focused on the never-zero/never-two seam and the purity law).
