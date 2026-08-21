---
review: reconcile — rulings fidelity
target: ARCHITECTURE-SPINE.md (QMB B-1..B-14)
authority: QMB .memlog.md (mid-synthesis operator direction); QMF .memlog.md entries 125–137 (no later backtesting-sitting lines exist after 137); research-backtesting/rulings-for-backtesting.md (inherited standing rules only — closed QMF ADs not re-opened)
sitting: QMB / backtesting-direction 2026-08-20
reviewer: rulings-fidelity reconcile pass
date: 2026-08-20
verdict: PASS WITH FINDINGS — 1 material, 2 medium, 5 low
---

# Reconcile review — QMB spine vs operator rulings

## Verdict

Every load-bearing operator ruling from the backtesting-direction sitting is present
in recognisable form in the B-ids — QMB/`qmb` naming, one library + CLI (never
"engine"; QMF the only framework), MCP back in after CLI v1, config + logs/ledger,
generated Book/BMS fragments, wind-tunnel-as-variables, the *sharpened* npm split,
12–14 process-per-run, fetch-at-runtime, synthetic-with-L20-still-standing, D1
shapes-only, "the Book sets the bar", and plain-Python bots until QML — **but the
two structural diagrams silently restore the snapshot + sync-hub state model the
operator rejected at memlog 132**, replacing the config-compiler he ruled. The
appendable / don't-box-in rider is practiced in the Deferred list and never stated
as a standing rule. Three dictated wants (debug, ML/RL, Rust-hybrid) were dropped
with no deferred row. The plain-words day-one explanation is a process ruling: the
spine is the wrong vehicle, not a B-id miss — and no companion is scheduled.

Nothing ratified was inverted in a B-id. The inversion is in the diagrams. No closed
QMF AD was re-opened. The four sharpened analogies (npm, config, logs/ledger, MCP
sequencing) landed as sharpened, not as raw dictation. No genuine ambiguity requires
the operator.

---

## How this pass reads the authority

- **Binding rulings** are operator decisions and the architect verdicts the operator
  invited and did not veto (memlog 136: "operator may veto; specs session ratifies").
  Raw dictation that the standing instruction required the architect to *correct*
  is checked in its sharpened form.
- **Not rulings:** donor-spec mechanisms, challenge findings, and architect-offered
  novel ideas that were never operator-asked (wind-tunnel presets, `qmb diff`) —
  recorded only when the spine silently treated a *rejected* option as law.
- **Closed QMF ADs** (AD-1..41) are inherited read-only. This pass does not re-try
  them. `rulings-for-backtesting.md` is used only for the standing rules that sitting
  was told to honor (Book-sets-the-bar, L20, D1, GAP-0016/0017 deferral,
  configurable-means-UI, don't-box-in / plain-Python).
- QMF `.memlog.md` ends at entry **137**. There are no backtesting-sitting lines
  after 140; 125–137 is the complete window.

---

## Part A — Load-bearing operator rulings (task list)

### 1. Named QMB / command `qmb`; QMX is the platform, never the library/CLI name

**Ruling:** memlog 134 — *"the backtesting library + CLI are named QMB (command qmb)
— NOT qmx: QMX is the entire platform and reusing it would confuse operator and
agents alike. Both halves (library and CLI) share the QMB name. Supersedes the
qmx-command proposal in the position paper."* Supersedes memlog 129's `qmx`
proposal and DC-5.

**Landed where:**
- Frontmatter L6: product name `QMB`; L20 vocabulary law; Conventions L144
  *"Product = QMB; command = `qmb`"*.
- Structural seed L165 `qmb/`; sequence L183 `qmb CLI`; capability map and
  diagrams use `qmb` as the command.
- QMX appears only as the platform (*"the QMX experimentation/backtesting
  product"* L6; *"QMX UI backend"* L27; *"QMX app/UI"* L201; *"QMX-original
  work"* L90). Never as the library or CLI name.

**Verdict: LANDED IN FULL.** The anti-reuse sentence is not restated as a
prohibition, but the spine never violates it. No action.

---

### 2. One library + CLI (both named QMB); never "engine"; QMF is the only framework

**Ruling:** memlog 129 (architect, then operator-accepted by 134's both-halves
naming) — *"the thing is a LIBRARY not a framework (engine banned; QMF is the
only framework)"*. Memlog 132 — *"CLI = the product face, thin library under
it"*. Memlog 134 — both halves share the QMB name.

**Landed where:**
- Paradigm L20: *"Vocabulary law: QMB is a **library** and a **CLI** — never an
  'engine', never a second framework (QMF is the only framework)."*
- B-1 L56–60: one library, thin doors, *"the CLI is the product face"*.
- B-13 L132: *"library + CLI in one wheel"*.
- Conventions L144: banned `engine` (and, post-gate, `kernel`).
- Inherited L52: L21 — QMB is an application outside the QMF repo, built with QMF.

**Verdict: LANDED IN FULL**, including the operator's "CLI is the product face"
answer. "Engine" is banned and unused. No action.

---

### 3. MCP back IN; sequenced after CLI v1; does not wait for the agentic system

**Ruling:** memlog 134 — MCP **re-ruled back IN** (operator will use it day-to-day);
open sub-question: ship with QMB or wait for the agentic system. Memlog 136
(architect recommendation, not vetoed) — *"thin wrapper over the same functions;
sequenced AFTER CLI v1 but does NOT wait for the agentic system (cheap to add;
consumers exist now incl. operator day-to-day; Jesse evidence — MCP binds to a
LOCAL project, matching per-sandbox topology, no central server)."* This
supersedes memlog 131's demotion (*"can have, do not need"*).

**Landed where:**
- Paradigm L26: `MCP[MCP door - later] --> LIB`.
- B-1 L60: *"MCP is a sibling door over the same library (never stacked over
  HTTP), localhost-bound by default, shipped after CLI v1."* Sibling-not-stacked
  and localhost-default are the Jesse-topology corrections from memlog 130/136.
- Seed L177: `doors/mcp/` lives **inside the qmb package**, not in an agentic
  system — that is the "does not wait" half in load-bearing form.
- Capability map L229: *"MCP for day-to-day agent use | doors/mcp (post-v1) | B-1"*
  — the operator's own "day-to-day" phrasing.
- Deferred L236: tool list and exposure-beyond-localhost only; shape fixed by B-1.

**Verdict: LANDED IN FULL** on all three halves. **Low provenance nits — Finding 6:**
Deferred L236 says *"post-CLI-v1 per operator"* — the operator re-ruled MCP *in*
and filed the sub-question; the *sequencing* is the architect's recommendation.
The sentence "does not wait for the agentic system" is not written; it is carried
by `qmb/doors/mcp/` belonging to QMB. A later reader could re-ask the filed
sub-question. One clause would close it.

---

### 4. Config + logs/ledger model; Book/BMS become generated config fragments; wind-tunnel variables not swapped tunnels

**Ruling:** memlog 132 — **both** snapshot+hub **and** live-registry options
rejected as heavy/premature. Counter-model: creating/updating a Book or BMS
materializes a **CONFIG** the CLI consumes (*"instead of a snapshot we get a
config"*); testing = can a bot fulfill/fit the Book's use case; **wind-tunnel**
= more turbulent wind means changing **VARIABLES**, never swapping or
snapshotting the tunnel; backtests are **LOGGED**; **SAVING** happens at
completion into a **LEDGER** carrying the unbiased pass/fail. Memlog 136
sharpened the guardrails: fragments are **generated + schema-validated +
fingerprinted, never free-hand-edited**; explicit precedence; resolved
run-config written out per run. Logs/ledger weight confirmed light (KB-scale
log, one JSON line, report JSON is the heavy one).

**Landed where (B-ids — faithful):**
- Paradigm L20: *"one tunnel, many wirings"*; *"Changing test conditions means
  changing config variables; the tunnel is never swapped."*
- B-3 L72: one resolved read-only run-config; precedence
  `invocation flags > run spec > Book config fragment + BMS config fragment >
  workspace defaults`; Book/BMS versions compile to **generated, schema-validated,
  fingerprinted** fragments — **never free-hand-edited**; artifact written to the
  run dir; fingerprint is the ledger key; named condition presets are fragments.
- B-4 L78: logs during (append-only per-run files); **exactly one** ledger line
  at completion with the unbiased verdict against the Book's bar (`unrated` when
  not yet ruled); aborted runs ledger as `aborted`.
- B-2 L66: backtest/replay/live/simulated differ **only** by which clock and
  adapters the run-config binds — the loop is never forked.
- Capability map L219: *"'CLI updates when I create a Book'"* → config compiler
  resolving registry fragments (the corrected mechanism for memlog 125's
  "auto-regenerates"; codegen was wounded at memlog 130).

**Landed where (diagrams — contradicts the ruling):**
- Sequence L185: `participant R as Registry (snapshot/config fragments)` — the
  **rejected noun** "snapshot" sits as an equal of "config fragments".
- Deployment L207–211: `HUB[(sync hub: registry + ledger files)]` with laptop
  and sandboxes syncing through it. That is option (a) from the position paper
  (memlog 128/130) — the option memlog 132 rejected.

**Verdict: LANDED IN FULL in every B-id; silently inverted in both diagrams —
see Finding 1 (material).** A factory or documentation-factory agent that
reads the pictures first will rebuild the state model the operator threw out.
The B-ids are not the problem; the pictures are.

---

### 5. npm analogy sharpened: pip/uv for the tool; name@version packages for Books/bots

**Ruling:** memlog 134 raw — *"build QMB more like npm"* (scale; producing
strategies at scale). Memlog 136 **corrected then adopted sharpened** — *"the
CLI half is really pip/uv-tool distribution (lean does exactly 'pip install
lean'); the genuinely npm-like half is STRATEGIES/BOOKS AS VERSIONED PACKAGES
resolved by name@version from the registry."* Standing instruction: check the
sharpened form, not the raw dictation.

**Landed where:** B-13 L132 — QMB is a versioned **uv/pip-installable** package
(library + CLI in one wheel); primary channel `uv add qmb` (importable library;
currency-gate correction of "uv tool" as isolated CLI-only, which further
sharpens rather than undoes 136); `uvx`/`uv tool install` demoted to CLI-only
convenience, never the sandbox channel. *"Books and bots are resolved
name@version from the registry — the npm-shaped half of distribution."*
Sequence L187: `qmb backtest bot --book scalping@2`.

**Verdict: LANDED IN FULL** as sharpened. The spine does not treat QMB itself
as an npm registry, which is the correction 136 made. No action.

---

### 6. 12–14 concurrent runs

**Ruling:** memlog 132 — *"Stated load target: 12-14 concurrent tasks at a go;
wants the system that handles that identified."*

**Landed where:** B-5 L83 — concurrent runs are separate OS processes (stdlib);
*"parallelism is bounded by cores, targeting 12–14 concurrent runs on sandbox
hardware — a motivating reference under AD-13, never a validated budget until
a fingerprinted baseline is measured."* The **system identified** is
process-per-run, no Ray / required Docker / daemon. Deployment L205
`qmb x 12-14 processes`. Deferred L240: Lean-style cloud-burst parked unless
12–14 proves insufficient by AD-13 measurement.

**Verdict: LANDED IN FULL.** The AD-13 hedge is inherited law (memlog 36: no
invented numbers as budgets), not a weakening of the target. The operator
asked for the system to be identified; B-5 names it.

---

### 7. Fetch-at-runtime data under the user's own provider; no redistribution

**Ruling:** memlog 125 wanted Dukascopy-primary data download; memlog 130
named the licensing hole (recovered tick corpus failed the gate); memlog 137
(spec campaign, operator-directed SDD) — Jesse's fetch-at-runtime-under-own-
relationship posture clears it. Combined: acquire at run-time under the user's
provider; QMB redistributes nothing.

**Landed where:** B-11 L120 — *"Acquisition posture: fetch at run-time under
the user's own provider relationship (Dukascopy primary); QMB ships and
redistributes no market data."* Data commands (download, verify, catalog,
generate) are thin fronts over qmf-data contracts.

**Verdict: LANDED IN FULL.**

---

### 8. Synthetic capability wanted, but L20 was NOT overridden

**Ruling:** memlog 133 — operator counts synthetic inside the override; wants
Lean's generator reverse-engineered and the capability adopted (*"it might
save us"*). **Explicit note in the same entry:** L20 (synthetic never
validates edge) was **NOT** explicitly overridden — stays standing until an
explicit ruling. Memlog 137 then vindicated L20 with donor evidence.

**Landed where:**
- Inherited L47: *"synthetic data stresses infrastructure, never validates edge"*.
- B-7 L96: world derived from provenance, never caller-declared; store-level
  taint; fabricated-from-scratch = infra-stress only; real-seeded perturbation
  = robustness under B-14; *"nothing synthetic validates edge (L20)"*.
- B-11 data commands include `generate`; capability map L223 names the
  capability and binds it to B-7 + L20.

**Verdict: LANDED IN FULL** — both halves, and the claim-class split that
keeps the capability without punching a hole in L20. No action.

---

### 9. Build-our-own / no donor code (shapes only)

**Ruling:** D1 standing (memlog 8, 24); memlog 125 raw *"take it as is, remove
what we do not want"* was logged as tension with D1, to be surfaced not
silently adopted. Standing instruction: CORRECT him. Memlog 131 method:
reverse-engineer HOW, *"never use the code"*. Memlog 136 DC-3 equivalent:
shape-only, code ban reaffirmed.

**Landed where:** Inherited L51 *"No donor code ever (shapes only); no central
always-on service; build-our-own"*. B-6 L90 forex content is *"QMX-original
work — no donor reference exists"*. Paradigm and B-ids cite donor *failures*
(Jesse three stacks, Lean `:latest`, no-slippage) as things to prevent, not
code to take. Optuna and click are ordinary libraries (D1-legal), not donor
engines.

**Verdict: LANDED IN FULL** as the corrected (D1) form. The raw "take it as
is" did not land, which is the required correction. The tension is not
disclosed in the spine; the memlog is its record. No action.

---

### 10. "The Book sets the bar"

**Ruling:** memlog 49 lead; memlog 108 shape (inherited, AD-32); memlog 125
agents backtest **against** a specific Book/BMS's own rules; memlog 132 testing
= can a bot fulfill/fit the Book; memlog 136 novel (not vetoed) —
completion-ledger doubles as the Book-sets-the-bar scoreboard.

**Landed where:** Inherited L50 *"Book/BMS/binding chain, 'the Book sets the
bar' … QMB consumes, never redefines"*. B-4 L78: ledger verdict is pass/fail
against the Book's declared bar, `unrated` when not yet ruled; *"it is what
'the Book sets the bar' reads."* Capability map L218. Sequence L195.

**Verdict: LANDED IN FULL**, including the scoreboard reading of the ledger.

---

### 11. Plain-Python bots until QML (GAP-0047); QML sitting is separate

**Ruling:** memlog 129 — plain-Python bots as the bridge meanwhile
(don't-box-in); QML sitting is GAP-0047, separable from this sitting; nothing
forecloses QML's uniformity mechanism (memlog 105/109, inherited). Memlog 127
— `.qml` bot-source format is **mandatory GAP-0047 input**.

**Landed where:** Deferred L239 — *"QML bot schema (GAP-0047) — QMB tests
plain-Python bots until QML lands; QML conformance gates governed evidence,
not tunnel entry."* That last clause is the don't-box-in application: QML is
not a tunnel admission ticket.

**Verdict: LANDED IN FULL** on the operator ruling. **Low — Finding 7:** the
mandatory `.qml` file-format input (memlog 127) is not named in the deferred
row, so GAP-0047 can be opened from this spine without the second QML artifact
the dig was told never to lose.

---

### 12. Extensibility: appendable, don't box in

**Ruling:** memlog 9 don't-box-in (standing). Memlog 134 rider — *"QMX keeps
growing — the spec must stay appendable (tomorrow he may need more of the use
cases QuantConnect designed for)."* Memlog 65 plain-Python escape hatch.

**Landed where (mechanism, unstated as a rule):**
- Ports (B-6, B-8 sampler) and doors (MCP later) are addable.
- Deferred list parks live wiring, UI, cloud-burst, prop-firm, GAP-0048/0049 —
  the practical appendability.
- L239 QML-does-not-gate-tunnel-entry is don't-box-in for bots.
- B-9 research surface is importable plain functions.

**Not landed:** no Inherited or B-id row states "this architecture stays
appendable" or carries don't-box-in by name. QMB's Inherited table copies D1
and L20 but not the 2026-08-18 don't-box-in constraint. "plugins" is banned
(L144), which is correct QMF vocabulary, and must not be confused with
"appendable".

**Verdict: LANDED WEAKENED — Finding 2 (medium).** Tomorrow's QuantConnect-class
use case has no standing sentence that forbids boxing the B-1..B-14 set as
closed.

---

### 13. Ratification vehicle = a PLAIN-WORDS day-one explanation

**Ruling:** QMB `.memlog.md` mid-synthesis (4) — he has lost the thread across
130 entries; *"ratification vehicle must be a PLAIN-WORDS explanation of what
QMB and the qmb CLI actually DO for him, day one; he judges good-or-not from
that, not from AD lists."* Same family as memlog 132 *"First agree on what the
CLI actually DOES before compiling everything it is meant to be."*

**Landed where:** nowhere in the spine, correctly. The spine is B-ids. The
capability map (L214–229) is the closest "what it does" list and is still an
architecture table.

**Verdict: PROCESS RULING — the spine is the wrong vehicle, not a B-id miss.**
**Sitting-process gap — Finding 3 (medium):** no companion is declared or
scheduled. Frontmatter `companions:` lists `specs/INDEX.md` and
`backtesting-direction-position.md` (the unratified v2 paper). The operator
cannot ratify this sitting from the artifact he asked for, because that
artifact does not exist yet. Record, don't pretend the spine covers it.

---

### 14. Call him only on genuine ambiguity

**Ruling:** QMB `.memlog.md` mid-synthesis (1). Standing instruction from
memlog 134: CORRECT him rather than accept when dictated analogies were wrong.

**Landed where:** not spine content. This pass finds **no genuine ambiguity**
that needs him (Part E). Snapshot vs config is already ruled (132). L20 is
already not-overridden (133). MCP sequencing is an architect recommendation
he invited (136). Rust/ML/debug are drops to disclose, not questions to reopen.

**Verdict: PROCESS RULING — honored by this review; not a spine row.**

---

## Part B — Memlog sweep, entries 125–137 (and QMB mid-synthesis)

| Entry | Ruling / direction | Landed where | Verdict |
|---|---|---|---|
| 125 | Lean-CLI-shaped own CLI; auto-reflect Book/BMS; backtest against Book rules; sandboxes have the CLI; local+cloud backtest/optimize; Jupyter outside QMX; Dukascopy download + synthetic; reports for agents and operator with in-house skills; autocomplete/debugging; MCP; simple syntax (QML); multi-TF/symbol permutations; interactive charts; ML+RL; optimize; MC+significance; Rust hybrid; "take it as is" vs D1; prop-firm socket | Capability map L218–229; B-1..B-14 as mapped in Part A; D1 Inherited L51 (the correction); prop-firm Deferred L241; live/cloud-burst Deferred L237/L240; **debug / ML+RL / Rust — Findings 4, 5, 8** | Dictated product shape landed; three wants dropped; D1 correctly overrode "take it as is" |
| 126 | Grounding delivered (event) | Sources L12 | n/a |
| 127 | `.qml` bot-source format = mandatory GAP-0047 input; plain-Python-vs-DSL ruled there | Deferred L239 names "QML bot schema" only | **Finding 7** |
| 128 | Position v1 (snapshot CLI, DC-1..5, AD-42..45) | Superseded by 131–132; spine correctly did **not** mint QMF AD-42..45 (L21, Inherited L52) | Rejected options must not re-enter — **Finding 1** |
| 129 | QML sitting separable; plain-Python bridge; library not framework; proposed name `qmx` | L239, L20; name superseded by 134 and landed as QMB | Landed (name as superseded) |
| 130 | Challenge: snapshot cannot be live; write-back; synthetic backdoor; doors carry adaptation logic; MCP not stacked; no donor code | B-1 adaptation logic + sibling MCP; B-7 taint; B-5 WriterId streams; D1 | Landed in B-ids; snapshot re-enters in diagrams (**Finding 1**) |
| 131 | Method: SDD reverse-engineer, never use the code; MCP demoted; nothing to adopt yet | Method executed (sources = intake); MCP demotion **superseded by 134** | Method honored; do not revive the demotion |
| 132 | **Q2 ruled:** config + logs/ledger; wind-tunnel = variables not swapped tunnels; 12–14; CLI = product face; first agree what the CLI does | B-3, B-4, B-5, B-1, paradigm L20 | B-ids full; diagrams invert (**Finding 1**); "what the CLI does" = Part A.13 |
| 133 | Synthetic wanted; **L20 NOT overridden**; Q4 stop designing promotion/governance; agents as quants; X-1 neither adopted nor rejected; GAP-0017 untouched | B-7 + L47; Deferred L234 GAP-0016/0017; no promotion-gate AD in QMB; B-8 every trial is a run (no campaign-budget-before-run — the v1 quiet landing was not repeated) | **LANDED IN FULL** |
| 134 | **NAMING QMB/`qmb`**; MCP back IN + sub-question; CORRECT him; npm-for-scale; **appendable** rider; navigate the three sites | Part A.1, A.3, A.5, A.12 | Naming/MCP/npm full; appendable weakened (**Finding 2**) |
| 135 | Website nav; Lean feature list captured verbatim; LEAN five-module scaffold sighted | Lean list mapped onto capability map + Deferred (live, cloud-burst). **Five-module scaffold correctly NOT adopted** (operator did not rule it) | Landed as shapes; scaffold not silently imported |
| 136 | **Sharpened verdicts** (npm, config guardrails, logs/ledger light, MCP after CLI v1 not waiting for agentic) + offered novels (presets, ledger-as-scoreboard, `qmb diff`, in-house skill) | npm B-13; guardrails B-3; logs/ledger B-4 + B-10 downsampling; MCP B-1; presets B-3 L72; scoreboard B-4; in-house skill B-10 L114. `qmb diff` not in spine (architect-offered, not operator-ruled — correctly omittable) | **Sharpened forms LANDED IN FULL** |
| 137 | Spec campaign (intake) | Sources L12; B-ids ground in the named mechanisms (config compiler, process-per-run, provenance taint, TPE-class, fetch-at-runtime) | Intake consumed. **Terminology — Finding 8:** operator mid-synthesis (3) said these are INTAKE dossiers, not specs; spine still cites them as `specs/` |
| QMB ml (1) | Call only on genuine ambiguity | This review | Honored |
| QMB ml (2) | Party mode = multi-lens gate | Process (this gate) | n/a |
| QMB ml (3) | Intake, not specs | Sources/companions still say `specs/` | **Finding 8** |
| QMB ml (4) | Plain-words day-one ratification vehicle | No companion | **Finding 3** (wrong vehicle + no placeholder) |

**Dictated Lean/Jesse wants, itemised (from 125 + 135 verbatim list):**

| Want | Spine | Verdict |
|---|---|---|
| Local + "cloud" backtest/optimize | B-5 + sandbox diagram; cloud = paid sandboxes (DEC-0084, memlog 43). Lean-style push-to-cluster **Deferred L240**, named and parked | **LANDED IN FULL** — narrowing disclosed |
| Jupyter usable outside QMX | B-9: bare uv-installed package; sealed data never leaves controlled rooms (the steelman scope, not the retracted "Jupyter anywhere") | **LANDED IN FULL** (scoped) |
| Autocomplete | B-1 L60 registry enumeration for autocomplete | **LANDED IN FULL** |
| Debugging (Lean list + 125) | nowhere | **DID NOT LAND — Finding 4** |
| Interactive charts | B-10 chart series as data; UI Deferred L238 | **LANDED** (data) + **DEFERRED EXPLICITLY** (UI) |
| ML + RL | nowhere (B-9 does not preclude notebook ML) | **DID NOT LAND as a named capability — Finding 5** |
| Optimize / hyperparameters | B-8 typed schema, TPE-class (Jesse's fake-Optuna corrected) | **LANDED IN FULL** |
| MC + significance before building | B-14 + capability map L222 | **LANDED IN FULL** |
| Multi-TF / multi-symbol permutations | B-12 | **LANDED IN FULL** |
| Simple strategy syntax | Deferred L239 QML | **DEFERRED EXPLICITLY** |
| Algorithm reports + in-house skills | B-10 L114 | **LANDED IN FULL** |
| Rust speed → hybrid | nowhere | **DID NOT LAND; correctly not adopted; undisclosed — Finding 8** |
| Live trading (Lean list) | B-2 seam holds; wiring Deferred L237 node territory | **DEFERRED EXPLICITLY** |
| Synchronize projects with cloud (Lean list) | Deployment hub L207 — **this is the rejected snapshot+hub, not a ruled sync feature** | **Finding 1** (do not treat as a landed Lean-sync want) |
| Prop-firm room | Deferred L241 DEC-0082 socket; nothing in QMB may preclude them | **DEFERRED EXPLICITLY** |

---

## Part C — Inherited standing rules (`rulings-for-backtesting.md`) this sitting may not contradict

Closed QMF ADs are not re-opened. Check only that QMB did not quietly drop a
standing rule the backtesting sitting was told to honor.

| Standing rule | QMB | Verdict |
|---|---|---|
| "The Book sets the bar" (admission bar; not-yet-ruled blocks live only) | Inherited L50; B-4 `unrated` when the bar is not yet ruled | Consumed, not redefined |
| L20 synthetic never validates edge | Inherited L47; B-7 last clause | Honored (Part A.8) |
| D1 / no donor code | Inherited L51 | Honored (Part A.9) |
| GAP-0016 / GAP-0017 deferred; attempt-counting raw material still accrues | Deferred L234; B-4/B-8 ledger completeness named as the raw material | **DEFERRED EXPLICITLY**; v1's campaign-budget-before-run was not repeated |
| Paper = world live (AD-12) | Inherited L46 `paper=world live`; `world=replay` is QMB's legal world now | Honored |
| Configurable = UI-editable (memlog 103, standing global) | Not copied into QMB's Inherited table. Book/BMS fragments inherit AD-30 flags. QMB-minted run-config variables (adapter bindings, presets, sampler settings) do not declare `ui-editable \| uneditable`. UI is Deferred L238 as platform territory | **Low — Finding 8.** Not a new ruling; the global still binds "anywhere in QMX". One Inherited row would carry it. |
| Don't-box-in / plain-Python escape hatch | Plain-Python bots L239; research surface B-9; rider itself unstated | Part A.12 |
| Corpus-precedence / QMX-discussion barred for risk | QMB does not source QMX-discussion for sizing; B-6 forex is QMX-original. Not QMB's job to restate the QMF Inherited row | Not a miss |
| Do-not-re-discuss-node | Live wiring correctly parked L237. The **sync hub diagram** is ops/node topology (memlog 52/55 filed it there) pulled into the QMB spine | Aggravates **Finding 1** |

---

## Part D — Findings

### Finding 1 — MATERIAL — Rejected snapshot + sync-hub state model re-enters through both diagrams

**Ruling (memlog 132):** both offered state models rejected as heavy/premature.
Counter-model = **config + logs/ledger**. Wind-tunnel = change variables, never
swap or **snapshot** the tunnel. Memlog 136 then ratified generated config
fragments as the viable form of that counter-model.

**What the B-ids say (correct):** B-3 is a config compiler; B-4 is logs-then-one-
ledger-line; B-13 resolves `name@version` from the registry; no snapshot
freshness contract, no hub as a QMB component.

**What the pictures say (the rejected model):**
- Sequence L185: `Registry (snapshot/config fragments)` — "snapshot" is an
  equal noun to the ruled artifact.
- Deployment L199–211: laptop and sandboxes both `<-->` a `sync hub: registry
  + ledger files`, with a nightly bucket behind it.

**How it inverts:** a reader (or the documentation factory, or a factory agent
drawing from the mermaid) rebuilds position-paper option (a) — immutable
registry snapshots plus a dumb sync hub — which is exactly what the operator
rejected in favour of "instead of a snapshot we get a config". The hub also
pulls memlog-55 ops/node topology into a QMB architecture picture, against
do-not-re-discuss-node.

**Why it happened:** v1/v2 of the position paper (memlog 128/130) centred on
snapshots; 132 replaced that centre; B-ids were rewritten; the diagrams kept
the old nouns. Classic silent-restore.

**Fix:** (a) rename the sequence participant to `Registry (generated Book/BMS
config fragments)` — no "snapshot"; (b) drop the hub from the QMB spine, or
caption it in one clause as the already-filed memlog-52/55 ops file-sync
(two machines + bucket), **not** the CLI's state model, and point at B-3/B-4
as the ruled mechanism. Do not call the operator — he already ruled.

---

### Finding 2 — MEDIUM — "The spec must stay appendable" / don't-box-in is practiced, never stated

**Ruling (memlog 134 rider + memlog 9):** QMX keeps growing; the spec stays
appendable for tomorrow's QuantConnect-class use case; don't-box-in is
standing.

**What the spine says:** Deferred L236–241 parks MCP details, live, UI, QML,
cloud-burst, prop-firm. Ports and doors are addable by construction. No
sentence states the rider. Don't-box-in is absent from the Inherited table
(D1 is present; this constraint is not).

**How it weakens:** a later sitting can treat B-1..B-14 as a closed set and
refuse a new use case as "not in the spine". That is the failure the rider
exists to prevent. Prop-firm's "nothing in QMB may preclude them" (L241) is
the right idiom — it is used once, for one socket.

**Fix:** one Inherited or Conventions row: *"QMB's B-ids are appendable:
capabilities add, they are not a closed catalogue; don't-box-in stands
(plain Python remains a legal bot until QML; strictness is at governed
evidence, not tunnel entry)."*

---

### Finding 3 — MEDIUM — Plain-words ratification vehicle is missing as a companion, and the spine cannot be it

**Ruling:** QMB memlog mid-synthesis (4); memlog 132 "first agree on what the
CLI actually DOES".

**Assessment:** this is a **process** ruling. The spine is the wrong vehicle
(B-ids, not day-one prose). That is not a B-id miss. What *is* a sitting
gap: `companions:` (L13) does not name or schedule the plain-words artifact,
so ratification has no object that matches the operator's stated test
("judges good-or-not from that, not from AD lists").

**Fix:** do not rewrite the spine into a brochure. Add a companion pointer
and actually write the day-one page (what `qmb` does for him on day one:
install, point it at a Book, run, read pass/fail on the Book's bar, logs
during, one ledger line at the end). He ratifies that; the spine binds the
factory.

---

### Finding 4 — LOW — Debugging (dictated Lean-CLI want) did not land

**Ruling (memlog 125, reinforced 135 verbatim Lean list):**
autocomplete/**debugging** kept for the operator.

**What the spine says:** B-1 L60 carries autocomplete (registry enumeration).
"Debug" / "debugging" / Jesse debug-mode does not appear.

**How it weakens:** low. Autocomplete — the half that binds door design —
landed. Debugging may mean Lean's CLI debug, Jesse's debug mode, or ordinary
pdb; the spine is silent rather than deferred. A later sitting can add it;
the miss is the missing deferred row.

**Fix:** one Deferred line: operator-facing debug (breakpoints / run-inspect)
is not in v1; autocomplete is the ruled door feature; debug is addable.

---

### Finding 5 — LOW — ML + RL experimentation silently dropped as a named capability

**Ruling (memlog 125):** wanted from Jesse: *"ML + RL experimentation"*.
Jesse-docs-study: ML pipeline exists; RL is README-only, not in the ML docs.

**What the spine says:** nothing. B-9's research surface (pure importable
functions, Jupyter on a uv-installed package) does not preclude notebook ML;
it also does not name the want. No deferred row.

**How it weakens:** low. Don't-box-in + B-9 is the correct default (plain
Python, not a QMB mode). Silence lets a later reader either invent an ML
door or conclude the operator's want was rejected.

**Fix:** one clause under B-9 or Deferred: ML/RL is notebook/plain-Python
research on the same library (B-9); not a QMB run-kind in v1; RL was absent
from the donor and is not adopted.

---

### Finding 6 — LOW — MCP "does not wait for the agentic system" is structural, not written; Deferred misattributes sequencing "per operator"

See Part A.3. Seed L177 + B-1 L60 carry the substance. Deferred L236
*"post-CLI-v1 per operator"* is the wrong attribution (operator re-ruled
MCP *in*; architect sequenced it).

**Fix:** Deferred reason: *"post-CLI-v1 per architect recommendation (memlog
136), answering the filed sub-question; MCP is a QMB door and does not wait
for the agentic system."*

---

### Finding 7 — LOW — GAP-0047 deferred row drops the mandatory `.qml` input

**Ruling (memlog 127):** the `.qml` bot-source file format is a **mandatory**
GAP-0047 input alongside `qml-original-dig.md`.

**What the spine says:** Deferred L239 "QML bot schema (GAP-0047)".

**Fix:** append: *"mandatory inputs include `qml-original-dig.md` and the
`.qml` bot-source format (memlog 127)."*

---

### Finding 8 — LOW — four disclosure / terminology nits, none load-bearing

1. **Sources range (frontmatter L12)** cites QMF `.memlog.md` entries
   **117–130**. The naming ruling, MCP re-rule, config+logs/ledger, L20-not-
   overridden, sharpened npm, 12–14, and appendable rider all live at
   **131–136**. Content landed; a downstream agent that trusts `sources:`
   will read the raw dictation (125) and the `qmx` proposal (129) and miss
   the corrections. Fix: `entries 125–137` (or 117–137).
2. **Intake vs specs (QMB memlog mid-synthesis 3):** the artifacts are intake
   dossiers; the spine still points at `research-backtesting/specs/`. Path
   can stay; the sources label should say intake.
3. **Rust hybrid (memlog 125)** was a lead, wounded by challenge-economics
   (nothing to borrow; AD-13 governs speculative acceleration), and
   correctly not adopted. The spine does not record the rejection, so the
   lead can be re-opened as if unasked. Fix: one Deferred/Conventions clause
   — no hybrid runtime in v1; AD-13 remains the gate for any later
   measure-then-budget ask.
4. **Configurable = UI-editable** (standing global, `rulings-for-backtesting.md`)
   is not in QMB's Inherited table. Book/BMS fragments already carry AD-30
   flags; QMB-minted run-config knobs do not. Fix: copy the Inherited row,
   or state that QMB run-config variables declare the same
   `ui-editable | uneditable` flag even though UI rendering is platform
   territory.

---

## Part E — Items to put to the operator

**None.** He already ruled snapshot vs config (132), L20 not overridden (133),
naming (134), and invited the MCP sequencing recommendation (136). Calling
him on diagram remnants, an unstated appendable rider, or dropped Lean-list
wants would violate mid-synthesis (1). Distill fixes them.

The **plain-words day-one page** (Finding 3) is the artifact he uses to
ratify. That is process, not a question.

---

## Sharpened-analogy check (standing instruction: CORRECT him)

| Raw dictation | Sharpened ruling (must land) | Spine | Verdict |
|---|---|---|---|
| "build QMB more like npm" (134) | pip/uv for the **tool**; `name@version` packages for **Books/bots** (136) | B-13 L132 both halves | **Sharpened form landed.** Raw "QMB is npm" did not, correctly |
| Config — "is it viable? seems like you are just accepting" (134) | Viable **with** generated + schema-validated + fingerprinted fragments, explicit precedence, resolved artifact written out (136); **not** a snapshot (132) | B-3 L72 | **Sharpened form landed in the B-id.** Diagrams still say snapshot (**Finding 1**) |
| Logs/ledger weight challenge (134) | Light: KB log, one JSON line, report JSON is the heavy one; raw ticks live once in data rooms (136) | B-4 + B-10 downsampling + B-11 rooms | **Sharpened form landed** as the mechanism (weight numbers themselves are rationale, not a B-id) |
| MCP: 125 in, 131 demoted, 134 back in + sub-question | Thin sibling wrapper; **after CLI v1**; **does not wait for the agentic system** (136) | B-1 L60; seed L177 | **Sharpened form landed.** Provenance nit Finding 6 |
| "take it as is, remove what we do not want" (125) | D1 shapes only; never the code (131, 8, 24) | Inherited L51 | **Corrected form landed.** Raw dictation correctly refused |
| "Jupyter anywhere" (125) | Tooling anywhere; sealed data never leaves controlled rooms (130 steelman) | B-9 L108 | **Scoped form landed** |
| Wind-tunnel (132) | Change **variables**, never swap the tunnel (132); one loop, adapters from run-config | Paradigm L20; B-2 L66; B-3 | **Landed verbatim** |

No raw-dictation form of a corrected analogy displaced the sharpened ruling
in a B-id.

---

## Count

| Bucket | n | Items |
|---|---|---|
| **LANDED IN FULL** | 22 | A.1 naming; A.2 library+CLI/no-engine; A.3 MCP (substance); A.5 npm sharpened; A.6 12–14; A.7 fetch-at-runtime; A.8 synthetic+L20; A.9 D1; A.10 Book sets the bar; A.11 plain-Python until QML; CLI-updates-via-compiler; backtest-against-Book; sandbox CLI; local+sandbox cloud (burst disclosed-deferred); Jupyter scoped; reports+skills; autocomplete; multi-TF/symbol; optimize; MC+significance; CLI product face; experimentation-vs-backtest vocabulary |
| **LANDED WEAKENED** | 2 | A.4 config+logs/ledger (**B-ids full, diagrams invert**); A.12 appendable/don't-box-in |
| **DID NOT LAND** | 3 | debugging (Finding 4); ML+RL as a named capability (Finding 5); Rust-hybrid rejection undisclosed (Finding 8.3) — none of these was a sharpened load-bearing ruling |
| **DEFERRED EXPLICITLY** | 6 | MCP details L236; live wiring L237; UI rendering L238; GAP-0048/0049 + 0016/0017 L233–235; cloud-burst L240; prop-firm L241. QML sitting L239 is deferred **and** the plain-Python-until-then ruling landed |
| **PROCESS (wrong vehicle / not spine content)** | 2 | A.13 plain-words ratification; A.14 call-only-on-ambiguity |

**Material miss:** Finding 1 only (snapshot/hub diagrams).

Nothing in B-1..B-14 silently broadened a ruling except the diagrams under
A.4. No closed QMF AD was re-opened.
