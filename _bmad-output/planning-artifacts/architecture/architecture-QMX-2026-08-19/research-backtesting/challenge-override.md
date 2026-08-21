# Adversarial challenge — "extension, not override"

status: adversarial review (read-only); nothing ruled
date: 2026-08-20
target: `backtesting-direction-position.md` (DRAFT)
lens: STEELMAN the operator's "FULL OVERRIDE" claim against the paper's
"extension, not override" verdict. Hunt every place the paper quietly waters
down EITHER the dictation OR the standing law.
method: concrete failure scenarios, each citing the dossier/ruling it rests on.
Default to wounded/broken; holds only where the best attack genuinely fails.

---

## The steelman I am arguing FROM

The operator did not say "add features." He said **full override**, and he said
it about an *architecture*: the CLI is the sandbox's interface, the CLI
auto-updates from Book/BMS state, Jupyter runs anywhere, synthetic data "sorts
our earlier problem." An override can be built entirely from pre-existing parts
and still be an override — because the **organizing principle** is new. The
paper's rebuttal is a **parts count** ("~80% already ratified"). A parts count
cannot refute a gestalt claim. And the paper concedes the load-bearing centre is
new in its own words: line 21, *"NEW… No prior ruling covers a state-synced
agent interface. This is the gold."* When the crown jewel is admitted-new,
admitted-load-bearing, and reorganises the whole experimentation surface,
"extension, not override" is at best contestable. That is the frame for every
attack below.

---

## ATTACK 1 — AD-43 is internally contradictory (BROKEN)

AD-43 / §3 makes four promises at once and they cannot all be true:

1. **Deterministic**: "sandboxes carry a read-only registry **snapshot**, itself
   fingerprinted into the result label."
2. **Live auto-update**: "the state it reflects is **live**. Create a Book → the
   next invocation sees it."
3. **Portable**: "Jupyter anywhere… sandbox and laptop use the identical
   package… no server, no workstation coupling" (§4).
4. **No central service**: "no separate cloud service (DEC-0084 stays dead)"
   (§4, line 72).

A *snapshot* is by definition **not live**. The only reconciliation — "each new
invocation re-fetches a fresh snapshot" — requires the sandbox to contact a
**live, always-on registry** at invocation start. That:

- **Reintroduces the central dependency DEC-0084 killed.** DEC-0084 was rejected
  because a central service "cannot supply the required isolation and
  Book-specific variation" (`backtesting-corpus-brief.md:16`). Decentralising
  *compute* while centralising *live state* still leaves every sandbox depending
  on one shared always-on registry to resolve `--book scalping@2` — the shared
  dependency the ruling rejected, re-entered through the word "view."
- **Breaks under "Jupyter anywhere."** On an external laptop / plain VS Code /
  external agent (§1 line 22; §4) with the pip package and **no network**,
  "create a Book → the next invocation sees it" simply does not happen. There is
  no live registry to snapshot from. Auto-update — the paper's declared "gold" —
  is exactly the feature that dies in the portable context the paper
  simultaneously promises.
- Makes "nothing is rebuilt, nothing is redeployed, no version skew" misleading:
  a fresh snapshot fetched per invocation **is** a redeploy of state, and a
  laptop that fetched yesterday's snapshot **is** version-skewed against a Book
  created today.

The registry itself is "no database server… JSONL edge files" (AD-16,
`spine-index.md:26`) — the paper never says how JSONL append-only files on a
workstation become "live" to a sandbox or an off-network laptop. The
distribution/consistency model is absent, and the auto-update claim rests on it.

**Verdict: BROKEN.** The paper's headline invention is asserted, not resolved.
**Fix:** force the either/or as a ruling — (a) the registry IS a live central
read-service the CLI depends on (then amend DEC-0084's scope to "central *state*
acceptable, compute decentralised," and drop the unqualified "no server / Jupyter
anywhere over live state"), or (b) the CLI reads a **shipped immutable
snapshot** (then "auto-updates when a Book/BMS changes" is false in sandboxes and
the snapshot must be explicitly re-shipped — say so). Never claim both.

---

## ATTACK 2 — the central service comes back through the door (WOUNDED)

The paper's §1 row: *"The sandbox itself has the CLI / compute worry — Already
ratified. DEC-0084 dead: backtesting is decentralized… never a central
service."* But standing law is stronger than "no central *compute* service":
map.md:49 = "**no central backtest engine — backtesting decentralizes into
callable QMF components**"; DEC-0087 = any future capability is "a **modular
on-demand library or sandbox that can vary by Book**, not a permanent central
service" (`five-hats-and-docs-state.md:82`). AD-43's live-registry-view (Attack
1) makes the *state* a permanent shared service even if the *compute* is not.
The operator's "override" instinct is vindicated here: a **state-synced** CLI is
a genuinely different animal from "decentralized callable components," and the
paper files it under "already ratified" when it is neither ratified nor obviously
compatible with DEC-0084/0087's isolation-and-per-Book-variation rationale.

**Verdict: WOUNDED.** **Fix:** state the registry availability/consistency
posture and get an explicit ruling that a shared live registry is compatible
with DEC-0084/0087 — do not smuggle it under "the CLI is just a view."

---

## ATTACK 3 — campaign pre-registration is the friction the operator asked to remove (WOUNDED)

The operator's dictation: *"for any X strategy, Y optimizations at time t"* —
free experimentation, run any optimisation any time. §4's optimize row lands it
on: *"a search campaign (charter + split + search-space + **budget, minted
before the run** — five-hats R-1) is the counting unit,"* and the multi-TF row:
*"each combination = one run **under the campaign's budget** (prevents silent
p-hacking via permutation spam)."* Minting a budget **before** the run is a
pre-registration ceremony — precisely the friction the free-experimentation
intent removes.

Worse, the paper does this while **also** claiming the governing gap is still
deferred: §5 lists GAP-0017 as "attempt counter — **candidate** unit: the search
campaign (R-1)," and Ask 4 asks to keep 0017 "with the proper backtesting
sitting." Docs confirm it is genuinely unruled: "**no attempt-count policy
exists**… raw material accrues without policy," `registry_attempt_budget`
etc. "unresolved" (`five-hats-and-docs-state.md:59,64`). So §4 **pre-decides** an
explicitly-deferred, friction-imposing policy and presents it as a neutral
"lands on an existing seam." The operator is never asked whether pre-registration
friction is acceptable — the exact decision his dictation contests.

**Verdict: WOUNDED.** **Fix:** strip the "budget minted before the run"
commitment out of §4 (it is GAP-0017's, deferred), OR add a ruling ask that
surfaces free-experimentation-vs-pre-registration as a live operator choice.

---

## ATTACK 4 — "synthetic sorts our earlier problem" is silently overruled, and replay has no legal corpus (WOUNDED → framing BROKEN)

The operator dictated that **synthetic data generation "sorts our earlier
problem."** The paper's §1 row calls this *"Already seeded, with a hard guard,"*
then the guard (AD-13/L20/AD-45) says synthetic *"stresses infrastructure,
**never validates edge**."* If the operator's "earlier problem" was
data-scarcity or the licensing wall, then L20 **negates the very use he
asserts** — yet the paper frames the negation as agreement and provides **no
ruling ask** on it. That is siding with the standing law against the dictation,
silently. The lens's target exactly.

Two compounding facts the paper never surfaces:

- **The replay corpus is licensing-blocked.** The only recovered tick corpus
  "**failed the licensing gate** (`SOURCE_LICENSE_NOT_CANONICAL_USABLE`)"
  (`backtesting-corpus-brief.md:106-109`). "Replay-first" (AD-45) presumes a
  legal recorded corpus exists. If the operator's earlier problem *was* that the
  real data is unusable, then **neither** replay (no legal history) **nor**
  synthetic (L20 bars edge) solves it — and the paper's "replay is legal today,
  synthetic is guarded" posture leaves the operator's actual data problem
  untouched and unnamed.
- **AD-45 is nearly a no-op.** "All runs world=replay until GAP-0048; synthetic
  = stress-only per L20" merely restates AD-12's existing reservation
  (`spine-index.md:22`) and inherited L20 (`spine-index.md:104`). It mints a new
  spine AD that adds no invariant AD-12+L20 don't already carry.

**Verdict: WOUNDED** (framing of the synthetic row is close to broken — it prints
contradiction as consensus). **Fix:** add a ruling ask that names the conflict
("under L20 synthetic may not validate edge; if your 'earlier problem' was
edge-data scarcity/licensing, that intent is **refused** — confirm or override"),
and address the licensing-blocked replay corpus rather than assuming replay is
available. Drop or justify AD-45 as distinct from AD-12.

---

## ATTACK 5 — "Jupyter anywhere" guts the no-peek seal (WOUNDED)

AD-21: the **12-month seal is a no-peek `policy rejection` at every qmf-data read
boundary, enforced NOW, independent of the deferred gates**
(`spine-index.md:126`). §4 promises the library is "a normal pip/uv-installable
package… sandbox and laptop use the identical package," importable "in any
Jupyter/VS Code/external-agent context" (§3).

Concrete failure: an agent on an external laptop `pip install`s the library, then
reads the sealed Parquet directly with pandas — **bypassing the qmf-data read
boundary entirely.** A library-level `policy rejection` is only as strong as the
honour system on a machine outside enforcement. The five-hats sweep names this
precise defect — R-4: a sealed-holdout look from a sandbox that may not write is
"jointly unsatisfiable," resolvable only by modelling the seal look as "a
**write-gated operation against the live registry**… else the seal is
honor-system only" (`five-hats-and-docs-state.md:25`). That resolution **requires
a live central registry** (loops back to Attacks 1–2) and is **incompatible with
offline portability.** The paper cites neither R-4 nor the enforcement gap; it
promises unqualified "Jupyter anywhere" over what includes governed evidence.

**Verdict: WOUNDED.** **Fix:** acknowledge R-4; rule the enforcement boundary —
sealed/governed evidence never leaves controlled sandboxes; the portable library
gets only unsealed, split-governed data with purge/embargo widths (R-5). Stop
promising "Jupyter anywhere" over sealed data.

---

## ATTACK 6 — AD-44 ratifies an unexamined bundle (WOUNDED)

AD-44 packs several independent, individually-unseen ratifications into one
yes/no ask (Ask 2):

- **The LEAN C# ENGINE composition skeleton** ("one kernel, three wirings",
  §2/§3). The operator dictated the Lean **CLI**, not the engine's internal
  composition model. "One kernel three wirings" comes from the verdict doc whose
  status is **"proposal, not adopted"** (`backtesting-corpus-brief.md:159`), and
  the backtest/paper/live fidelity split is GAP-0048's substance (fidelity
  taxonomy, fill models, parity — `five-hats-and-docs-state.md:69`). Ratifying
  the skeleton now pre-empts a deferred sitting.
- **A network-exposed MCP surface.** Jesse's MCP binds `0.0.0.0`, default port
  9002, requires the app running (`jesse-docs-study.md:141-143`). AD-42 mints
  "MCP" as a permanent co-equal door and AD-44 ratifies "MCP server as a thin
  wrapper," but the operator is never asked whether he wants a network-exposed
  agent-tool surface or its security posture.
- **Jesse-specific `hyperparameters()` / `routes` shapes** — fine as shapes, but
  bundled so the operator cannot accept the Jesse research API while rejecting
  the LEAN engine skeleton.
- **"Cloud" quietly redefined.** The operator said "local + cloud"; Lean's real
  model includes `lean cloud …` and `lean private-cloud start|add-compute`
  (master/slave compute cluster, `lean-cli-study.md:42-46,67`). §4 unilaterally
  reinterprets "cloud" as "your paid sandboxes/VPS… no separate cloud service" to
  preserve DEC-0084 — a reinterpretation of dictation to fit law, never flagged
  as a ruling.

**Verdict: WOUNDED.** **Fix:** unbundle AD-44 into line-item donor ratifications;
split the "one kernel three wirings" fidelity claim out to GAP-0048; add explicit
asks for MCP surface existence/security and for the cloud-compute posture.

---

## ATTACK 7 — the four ruling asks omit the decisions that matter (WOUNDED)

The asks cover verdict-ratification, shape-vs-code, names, and gap-scope. They
**omit** every genuinely contestable decision this paper actually makes:

- registry **liveness / central-state** (AD-43, Attack 1) — asserted, not asked;
- **MCP surface** existence and security (AD-42, Attack 6) — never asked;
- **synthetic-vs-L20** dictation conflict (Attack 4) — never asked;
- **campaign pre-registration friction** (Attack 3) — never asked;
- the **"engine" vocabulary ban** — "'engine' is BANNED for backtesting"
  (`spine-index.md:152`; `five-hats-and-docs-state.md:86`); the paper brushes it
  (AD-44 "engine skeleton") and never asks the operator to confirm the naming
  discipline for the new library, though it does ask `qmx` and the
  experimentation-umbrella rename (Ask 3).

And a procedural reversal: the paper mints **four ADs** while repeatedly
conceding a **required input is still missing** — "your GPT brainstorm markdown
is still a missing required input" (§1 line 22; Ask 4) — over an area map.md
marks **"PAUSED as a decision area… nothing in them is ratified"**
(`backtesting-corpus-brief.md:54`). A paper whose thesis is "not an override"
overrides the standing "paused, do not ratify without the required input" posture
by minting AD-42..45 anyway.

**Verdict: WOUNDED.** **Fix:** hold AD-42..45 as proposals pending the GPT
brainstorm; convert the buried decisions above into explicit asks.

---

## ATTACK 8 — AD-42..45 sit on the wrong side of the framework/app boundary (WOUNDED)

The paper itself says the experimentation library is **"a QMF-built
application-side library, never a QMF roster package — DEC-0022/L21"** (§3), and
L21 puts "backtest workspaces and the QMX app… **outside this repo's scope**"
(`spine-index.md:7`). The framework-vs-node split is hard standing law: "QMF
carries only their contracts/seams" (map.md:29/70,
`backtesting-corpus-brief.md:70`). Yet AD-42 (three doors), AD-43 (registry
view), AD-44 (donors), AD-45 (replay-first) are **application-layer** design, and
the paper proposes to mint them onto the **QMF ARCHITECTURE-SPINE** (AD-1..41,
all QMF-package invariants). Extending the QMF spine with app-layer ADs blurs the
very boundary the paper elsewhere defends — an override of the framework/app
separation, committed structurally.

**Verdict: WOUNDED.** **Fix:** record these as ticket-008 / app-architecture
decisions, not QMF spine ADs; keep the QMF spine at AD-1..41.

---

## ATTACK 9 — the headline "80/20, extension not override" (WOUNDED)

The §1 table counts line-items and finds most "already ratified." But the
operator's override claim is about the **organizing principle** (CLI-primary,
state-synced, three-doors), and an architecture can be an override whose parts
all pre-exist. The paper concedes novelty at the load-bearing centre (line 21,
"the gold… no prior ruling covers a state-synced agent interface") and mints
**two brand-new ADs** (AD-42, AD-43) with no precedent. A parts-count cannot
refute a gestalt claim; the 80/20 metric measures the wrong thing.

**Verdict: WOUNDED.** **Fix:** reframe honestly — "a new organizing architecture
assembled from mostly-ratified parts; the override is real at the interface
layer (AD-42/43), contained at the invariant layer (AD-1..41)" — and let the
operator rule on the gestalt, not on a line-item tally.

---

## WHERE THE PAPER HOLDS

**§2 "Lean vs Jesse — the choice dissolves" — HOLDS.** Even pressing the
full-override steelman, neither is adoptable as **code**, and the engineering
case stands independent of D1: Jesse is crypto-only, float arithmetic, global
singletons, **no slippage model at all**, flat single-rate fee, and its
live/paper trading is a **paid closed-source plugin**
(`jesse-repo-study.md:92-96,193-195`; `jesse-docs-study.md:157-165`); lean-cli is
a logic-free Python orchestrator over a C# engine in Docker
(`lean-cli-study.md:17,89-99`). The donor-split (LEAN skeleton / Lean-CLI shapes
/ Jesse research surface) is a defensible *shape* reading. My best attack on this
section fails.

**§7 the `.qml` bot-source find — HOLDS (minor).** The second QML artifact (the
`.qml` file format + Monaco surface) is real and correctly routed to GAP-0047
(`qml-dig-verification.md:40-85`). Sound, but peripheral to the override
question.

---

## Net

The paper's engineering (Attack-proof §2) and its QML find are solid. Its
**architectural core is not**: AD-43's auto-update is internally broken (Attack
1) and, wherever it is patched, either resurrects the central dependency DEC-0084
killed (Attack 2) or dies under the "Jupyter anywhere" it also promises (Attacks
1, 5). On governance it waters down the **dictation** toward the law without
asking (campaign pre-registration, Attack 3; synthetic/L20, Attack 4); on
auto-update it waters down the **law** toward the dictation without noticing the
incoherence (Attacks 1–2). Both directions of the lens land. The four asks miss
the four decisions that matter, and mint ADs the standing "paused" posture says
should wait. The operator's "full override" instinct is closer to right than the
paper's "extension" verdict admits — not because the invariants fall, but because
the new interface architecture (AD-42/43) is a genuine, unratified,
still-incoherent reorganisation the paper labels settled.
