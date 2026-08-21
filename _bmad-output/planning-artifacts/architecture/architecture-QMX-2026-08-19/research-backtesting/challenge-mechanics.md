# Adversarial challenge — MECHANICS of AD-42 / AD-43 / AD-45

Lens: the operational plumbing of "one surface, three doors" (AD-42), "the CLI is a
stateless registry view" (AD-43), and "replay-first" (AD-45). Job: break the mechanism
with concrete failure scenarios, cite the dossier/ruling behind each. Read-only.

Date: 2026-08-20. Target: `backtesting-direction-position.md` §3, §4, §6 (AD-42/43/45).

---

## Attack 1 — AD-43 says the snapshot is BOTH frozen and live. In an offline sandbox it is frozen, and "create a Book → next invocation sees it" is false.

**The paper's own words collide.** §3: "sandboxes carry a **read-only registry snapshot**,
itself **fingerprinted** into the result label" AND "Create a Book → **the next invocation
sees it**" AND "the state it reflects is **live**." A fingerprinted, read-only *snapshot*
cannot also be *live*. These are two different mechanisms wearing one sentence.

**Why the offline case is the real case, not an edge case.** DEC-0084 is DEAD precisely
because a central always-on service "could not supply enough compute for concurrent work"
and "cannot supply the required isolation" (`backtesting-corpus-brief.md:16-19`;
`five-hats-and-docs-state.md:81`). The ratified shape is decentralized, **on-demand in
agent sandboxes / bare-metal Ryzen 9 VPS, never centralized** (ticket 008:82;
`backtesting-corpus-brief.md:17-18`). The registry itself is "JSONL edge files; **no
database server**" (AD-16, `spine-index.md:26`). So there is no live service for an offline
paid VPS to query — the snapshot is a *copy of JSONL files as-of some sync instant*.

**Concrete failure (the prompt's scenario).** Sandbox A spun up Tuesday with a snapshot
pinning `scalping@2`. Wednesday the operator mints `scalping@3` (a VERSION change —
template-level, `VERSION != COPY`, memlog:100/107; UI edits mint new versions never mutate,
`rulings-for-backtesting.md:59`). The agent in A runs `qmx backtest --book scalping@2` all
Wednesday and Thursday. The paper promises the next invocation "sees" @3. It does not: A is
offline with a Tuesday snapshot. The longer the paid VPS lives (its whole economic point),
the staler its view. **The headline dictated feature — "if I update the BMS, the CLI
updates" — is satisfied only for the laptop reading a live local registry, and is FALSE for
the decentralized sandboxes the architecture is built around.** The paper applies one
mechanism to two topologies that behave oppositely and never says so.

**What must the label carry, and what still breaks.** The label is not a *lie*: `@2` is
immutable (append-only, meanings never mutate — AD-5, `spine-index.md:15`), so a run stamped
`book=scalping@2 + snapshot_fp` is honestly labelled. The failure is **operational, not a
mislabel**: (a) agent work silently accumulates against a **superseded** Book (AD-16
`supersedes` is linear, `spine-index.md:26`) with no reconciliation or notification path —
the paper provides none; (b) AD-11 has a `stale evidence` refusal category
(`spine-index.md:21`) and the paper never rules whether a run against a snapshot older than
the live registry's supersession should raise it. The operator's mental model ("the CLI
tracks my Books") is quietly violated on exactly the surface agents use.

**Fix.** Split the two claims. Declare a **snapshot freshness contract**: the label carries
the snapshot fingerprint *and* its as-of knowledge-time; a sandbox run is `world=replay,
provenance=sandbox` (AD-12) with an explicit `registry_as_of` instant; define the re-sync
trigger and bound; and rule whether a run whose resolved ref was superseded after the
snapshot's as-of raises `stale evidence`. Stop calling a frozen snapshot "live."

Verdict: **broken** (internal contradiction, and the auto-update promise fails on the
decentralized topology).

---

## Attack 2 — AD-43 solves READS and ignores WRITES. Parallel minting collides with AD-15 one-writer and AD-16 append-only, with no merge authority.

The operator dictated "**parallel agents minting campaign/occurrence records from many
sandboxes**." §3 describes only the *read* path (a read-only snapshot). Campaigns (R-1) and
evaluation occurrences (R-8) are **writes** to the registry, and the paper never addresses
the write-back path at all.

**Collision with AD-15.** "one-writer-per-stream for stateful resource owners"
(`spine-index.md:25`); registry = append-only JSONL, no DB server (AD-16); journals = N
writer-scoped streams (AD-21, `spine-index.md:31`). N offline VPS sandboxes each want to
append occurrence/campaign records. Either:
- each sandbox writes its **own** writer-scoped stream (writer = agent/sandbox identity) —
  AD-15-legal — but then **merging N append streams into the canonical registry is an
  unspecified operation**: who merges, when, under what authority? This is a distributed-append
  problem (git-branch-shaped) and the paper offers no merge cadence, no merge authority, no
  operator gate; or
- they write a shared stream — a direct AD-15 one-writer violation across offline machines
  with no lock server (DEC-0084 killed the server).

**Collision semantics (AD-10 vs R-7).** Two sandboxes independently mint a campaign for the
same `(charter, split, search-space, budget)` (`five-hats-and-docs-state.md:17`), or two
sandboxes produce one label with **differing float bytes** — R-7 flags this as "the
researcher's **normal** case," and AD-10 today classes same-hash/differing-bytes as a **true
collision (refused + alarmed)** (`five-hats-and-docs-state.md:34`; AD-10 `spine-index.md:20`).
The paper cites R-8 (seeds) in §4 but **never resolves R-7**, so legitimate parallel minting
will trip AD-10 collision alarms. The "three doors" abstraction does nothing here because the
collision lives in the registry *write* layer, beneath all three doors.

**Fix.** AD-43 must own a write-back contract, not only a read-view: per-sandbox writer-scoped
occurrence/campaign streams; a named **merge authority + cadence** (operator-gated import, or
a designated reducer) with idempotent `fp1` accept vs true-collision split (AD-10) explicitly
extended by R-7's "label-identified float artifacts differing in content checksum are lineage
siblings, not collisions." Until then AD-43 is a half-contract.

Verdict: **broken** (the dictated parallel-write workflow is unspecified and collides with
AD-15/AD-16/AD-10 as they stand).

---

## Attack 3 — "No door carries logic" leaks the moment you build any of the three doors.

AD-42: "three **logic-free** doors"; §3: "No door carries logic; nothing can drift between
them." The named donors show where this leaks:

- **CLI.** Lean's "thin" CLI still does arg parsing, **config synthesis** (`get_complete_lean_config`
  injects defaults and resolves precedence: CLI flag > project config > `lean.json` > synthesized
  defaults, `lean-cli-study.md:79,83`), **path resolution** (walk-up to find the config root,
  `lean-cli-study.md:79`), image/version pinning, and mount orchestration. That is a great deal
  of *adaptation* logic. A QMX CLI must additionally do **auth/identity**, **snapshot resolution**,
  **12-month-seal enforcement translation** (AD-21 policy rejection at the read boundary,
  `spine-index.md:126`), **world selection**, and **refusal rendering** (AD-11 typed refusals →
  CLI exit codes + stderr; `spine-index.md:21`).
- **MCP.** Jesse's MCP is a "thin wrapper" but holds `JESSE_API_URL`/`JESSE_PASSWORD` (**auth**),
  FastMCP **streamable-http transport**, `json_response` marshalling (`jesse-repo-study.md:145`;
  `jesse-docs-study.md:138-143`) — transport + auth + serialization logic per door.
- **Refusal rendering differs per door** by necessity: Python raises/returns, CLI sets exit
  codes, MCP emits error objects. AD-11 refusals (`spine-index.md:21`) cannot appear "at all
  three doors mechanically" without door-specific rendering.

**Sharpest form — the operator's own ask breaks the claim.** The operator wants **autocomplete**.
Completing `--book scalping@?` requires the CLI to **enumerate live registry state** — a registry
read living in the door's completion path. Lean's autocomplete is only "Click's native shell
completion" (a static command tree, `lean-cli-study.md:69`) and cannot complete dynamic registry
values without door-side state-reading logic. So dynamic autocomplete is simultaneously (a) logic
in the door and (b) state in the "stateless" CLI — contradicting both AD-42 and AD-43. The feature
the operator explicitly requested is the counterexample.

**Fix.** Reword to "doors carry no **domain/business** logic; they necessarily carry adaptation
logic — parse, auth, transport, config resolution, refusal rendering, and registry enumeration
for completion." Then locate seal/world/auth enforcement in the shared library with a thin
per-door renderer, and accept that autocomplete reads registry state (bounding the staleness of
what it completes).

Verdict: **wounded** (the flat "no logic" claim is false; the honest claim is "no domain logic,"
which the paper does not make).

---

## Attack 4 — The UI backend: AD-42 *binds* it but never says whether it is a fourth door; the donor's own topology stacks MCP on HTTP.

AD-42 "**Binds:** the experimentation library, sandbox images, **UI backend**" (§6) — yet names
exactly **three** doors (Python, CLI, MCP). The UI backend is neither. Two readings, both
unresolved by the paper:

- **(a) It is a fourth (HTTP) door** — then "three logic-free doors" is wrong/incomplete, and
  interactive charts + the Simulator need it. The Simulator is ratified as **UI-driven**
  (`backtesting-corpus-brief.md:60`, map.md:63); §4 punts interactive-chart rendering to
  "UI/platform territory." Something must serve chart-data JSON and Simulator runs over HTTP.
- **(b) It is a consumer that calls one of the three doors** — then "binds UI backend" is
  meaningless as stated, and you must say *which* door it uses.

**The donor contradicts the clean picture.** Jesse — the named MCP/research-API donor — is
**web-app-first**: a FastAPI backend + Vue SPA, and its **MCP server is "a thin wrapper over the
Jesse HTTP API"** (`jesse-repo-study.md:145,193`; `jesse-docs-study.md:138`). In the donor, MCP
sits **on top of** the HTTP/UI door, not beside it. If QMX imitates the donor shape, the doors are
**stacked** (MCP → HTTP → library), not three parallel siblings into one library. The paper's
symmetric "three doors into one library" does not match the topology of the very system it is
copying, and it never rules the UI backend's status.

**Fix.** Explicitly rule: either (i) the UI backend is a declared fourth HTTP door subject to the
same no-domain-logic contract (and AD-42 must say "four doors"), or (ii) the UI backend is a plain
Python-API consumer and MCP is a peer door over the same library **in-process, not over HTTP** —
and then say so, so QMX does not inherit Jesse's MCP-over-HTTP stacking by default.

Verdict: **wounded** (a bound surface with undefined door-status, contradicted by the donor's
topology).

---

## Attack 5 — The three doors are not symmetric: the MCP door is a long-lived stateful server, and the auto-update promise is *worst* exactly where agents live.

The paper treats the doors as interchangeable ("the same functions... at all three doors
mechanically"). Their **lifecycles are fundamentally different**, and AD-43's statelessness
argument only holds for one of them:

- **Python API** = in-process call (snapshot = whatever the host process loaded).
- **CLI** = one-shot process; a *fresh* process could re-read a local registry each invocation —
  this is the only door for which "stateless, re-resolves each time" is naturally true.
- **MCP** = a **long-running server**, port-bound (Jesse: FastMCP, binds `0.0.0.0:9002`, "requires
  Jesse running," `jesse-docs-study.md:141-143`). A long-lived server **holds** its loaded snapshot,
  session, and port binding until restart — it is **stateful by construction**.

**Consequence.** The registry snapshot goes stale **fastest** at the MCP door, because the server
holds one snapshot across many tool calls until it is restarted, whereas a fresh CLI process could
re-resolve. But ticket 008 says "**agents, not Mubarak, execute backtests**" (008:24,
`backtesting-corpus-brief.md:88`), and MCP is the agent-facing door. So the operator's headline
"the CLI auto-updates when I change a Book" is **least true precisely at the door the primary users
(agents) use** — a long-lived MCP server keeps serving `scalping@2` after the operator mints `@3`,
until someone restarts it. The paper's uniform "three doors" framing hides this asymmetry.

**Fix.** State per-door snapshot lifecycle explicitly: define when the MCP server re-resolves the
snapshot (per-call re-read vs cached-until-restart), and carry `registry_as_of` in every MCP tool
result so an agent can detect it is operating on a stale view.

Verdict: **wounded** (door symmetry is asserted, not real; the auto-update property inverts across
door lifecycles).

---

## Attack 6 — AD-45 blesses `data generate` shipping early AND declares every run `world=replay`. A run over generated data is `world=simulated` by definition — so `data generate` is the edge-validation backdoor unless synthetic taint propagates to the run's world, which the paper never specifies.

AD-45 (§6): "**All experimentation runs are world=replay** until GAP-0048"; §3: "`data generate`
**may ship early** but its outputs stress infrastructure and **never validate edge** (L20)."

**The mechanical hole.** `data generate` writes synthetic candles into the sandbox data room
(Lean's Brownian RandomDataGenerator with `--random-seed`, `lean-cli-study.md:123`; Jesse's
`candle_pipelines` gaussian-noise / moving-block-bootstrap, `jesse-repo-study.md:25,137`). Then
`qmx backtest --book X --bot Y` runs over **whatever is in the data room** — and Lean's own model
is explicit: generated data lands in `data/` "so **subsequent backtests can consume them**"
(`lean-cli-study.md:124`). At *consumption* time the run cannot tell recorded Dukascopy history
from synthetic candles unless provenance is enforced at the **data** level.

But `world=replay` is defined as "recorded history, real UTC instants" (AD-12,
`spine-index.md:22`). Synthetic candles have **no recorded UTC provenance** — they are
`world=simulated`, which is a **`policy rejection` in V1** until GAP-0048 defines simulated-time
typing (`spine-index.md:22,110`; `five-hats-and-docs-state.md:69`). So a run consuming generated
data is either:
- **mislabelled `world=replay`** — synthetic data masquerading as recorded history: the exact
  edge-validation backdoor the prompt warns of. An agent generates favourable candles, backtests a
  bot, gets a great Sharpe, and the label says `replay` because the door never learned the data was
  synthetic; or
- **correctly `world=simulated`** → `policy rejection`, produces no governed evidence — in which
  case "`data generate` may ship early" delivers nothing beyond AD-13 infrastructure stress, and
  AD-13 already requires benchmark data be "generated at runtime or controlled fixtures — **never
  shipped as product**" (`spine-index.md:23,130`), which cuts against a persisted `data generate`
  artifact in the data room at all.

The only safe construction is a **taint that is a property of the data, propagating to the run's
world** — precisely the AD-7 pattern ("money path is a taint **not a location**," AD-7
`spine-index.md:17`). The paper never specifies this propagation, so as written AD-45 permits the
backdoor.

**Fix.** AD-45 must state: synthetic-origin data rooms are tainted at the store level (AD-19
per-world rooms, `spine-index.md:29`); any run consuming a tainted room is **forced** to
`world=simulated` → `policy rejection` for governed evidence, independent of what the door was
asked for. World is derived from input provenance, never declared by the caller.

Verdict: **broken** (without specified taint propagation, `data generate` + replay-labelling is the
edge backdoor the paper claims to have closed).

---

## Attack 7 — "replay-first ships now" oversells AD-12. The clock is legal now; the fill model that makes a replay a *backtest* is GAP-0048, deferred.

§3: "every run the doors produce is **world=replay**... **legal under AD-12 now**." True but
misleading: AD-12 makes the **injected data-driven clock over recorded history** legal today
(`spine-index.md:22`; AD-8 replay clock, `spine-index.md:18`). It does **not** make an
edge-validating **backtest** legal today, because the thing that turns a clocked replay into a
backtest — the **fill model / fidelity taxonomy** — is exactly GAP-0048, deferred
(`five-hats-and-docs-state.md:69`; `spine-index.md:158`).

**Concrete gap.** A `world=replay` run needs to fill orders against recorded candles. The paper's
own §2 disqualifies Jesse precisely because it has "**no slippage model at all and a flat fee
rate**" (`jesse-repo-study.md:92,195`) and says retail-forex fill "has **no reference
implementation anywhere; we must build that part regardless**." The fidelity taxonomy
(bar_close/intrabar/tick) is a **candidate, not ratified**, and is one of the "six irreversible
decisions — each invalidates every prior stored result if changed later" (map.md:76,
`backtesting-corpus-brief.md:64,254`; GAP-0048 `five-hats-and-docs-state.md:69`). So any interim
fill model a "ships-now" replay uses will be **invalidated** by GAP-0048, and every result stored
under it is retro-invalidated. "Replay ships now" therefore delivers a **clock without a
verdict-bearing fill** — you can replay bars, but you cannot produce a governed edge result, which
is the whole point. The paper's framing lets a reader believe backtests can start now; they cannot.

**Fix.** Say plainly: the replay *clock + data-cursor + split-governed reads* ship now (legal,
AD-8/12/21); **fill, fidelity, and any edge verdict wait on GAP-0048**, and interim fill
experiments are `fidelity=optimistic`-tainted and cannot spend split budget or claim edge (the
verdict doc's own taint rule, `backtesting-corpus-brief.md:194`). Separate "replay mechanism ships"
from "backtests ship."

Verdict: **wounded** (the "legal now" clause is true about the clock and false about backtests; the
gap that matters is deferred).

---

## Attack 8 — AD-43's result label is a two-item list; a comparable, reproducible replay result needs more, and AD-12 + R-8 already demand more.

AD-43 (§6): "runs stamp **both** [pinned CLI + fingerprinted registry snapshot] into the result
label." Taken literally that is a two-axis label. It is insufficient on three counts:

1. **The QMF library version is a separate ladder from the CLI version.** A backtester is "an
   application built **with** QMF, not a QMF package" (`spine-index.md:7,144`); the roster carries
   its own SemVer lockstep (AD-2/AD-5, `spine-index.md:12,15`). Two runs with identical CLI version
   and identical snapshot fp but a different underlying `qmf-*` patch can differ, and the two-item
   label cannot distinguish them. §3 names only "two ladders" (CLI + registry state) and even
   conflates the CLI's version with the library's.
2. **Stochastic provenance has no home in the AD-43 label.** R-8: seed + generator identity +
   (parallel) reduction order are needed or a stochastic search result "is **not reproducible** from
   AD-12's five parts alone" (`five-hats-and-docs-state.md:35`). Optimize/Monte-Carlo/significance
   doors are stochastic (Optuna+Ray, `np.random` sampler, bootstrap RNG — `jesse-repo-study.md:102-103,
   136,139`). §4 mentions seeds for MC in passing but AD-43's *label definition* omits them; a door
   result that omits the seed is silently non-reproducible.
3. **Fidelity / fill-assumptions id does not yet exist** (GAP-0048) yet belongs in the key — the
   verdict doc keys its baseline on `fill_assumptions_id, fidelity, ...`
   (`backtesting-corpus-brief.md:234`). AD-43 cannot claim a complete label while the fidelity axis
   is an unratified candidate.

Note in fairness: the **snapshot fingerprint** does capture all registry-resolved refs
(book@2, bound BMS version, bot fp, split manifest — if splits are registry records per AD-21), so
the label is complete *for the deterministic registry-resolved part*. The incompleteness is the
non-registry axes above. AD-43 as drafted under-specifies against AD-12's already-mandated label
(producer identity, format version, input fingerprints, evidence time range, evidence class, world
— `spine-index.md:22`).

**Fix.** Do not enumerate a bespoke two-item label in AD-43. Make AD-43 say "the run stamps the CLI
version, the QMF roster version, the registry-snapshot fingerprint **and its as-of**, plus every
axis AD-12 already mandates; stochastic doors additionally stamp R-8 seed/generator/reduction-order;
the fidelity/fill id is added when GAP-0048 lands." Reference AD-12 rather than restating a shorter
list that reads as the whole truth.

Verdict: **wounded** (the drafted label is narrower than AD-12 and R-8 already require).

---

## Summary of the mechanical breaks

The paper's §3 is elegant about **reads** and silent about **writes, freshness, and door
lifecycle** — the three places the mechanism actually meets the decentralized reality it inherited
from DEC-0084. The two hardest breaks: (Attack 1) "snapshot" and "live" cannot both be true in an
offline sandbox, so the auto-update headline fails on the very topology the architecture is built
for; and (Attack 2/6) the parallel-write path and the synthetic-data taint path are both unspecified,
leaving AD-43 a half-contract and AD-45 an open edge-validation backdoor. AD-42's "no logic / three
symmetric doors" is an idealization the named donors themselves violate (adaptation logic per door;
MCP stacked on HTTP; long-lived stateful MCP server; the bound-but-undefined UI backend). None of
these is fatal to the *direction* — replay-first, registry-as-state, one library many doors are all
sound instincts — but each names a mechanism as *solved* that is in fact *deferred or contradictory*,
and the ruling asks (§8) should not be answered "ratify AD-42..45" until the write-back, freshness,
taint-propagation, and label-completeness clauses are written.
