# Adversarial challenge — ECONOMICS + transferability lens

target: `backtesting-direction-position.md` (DRAFT, 2026-08-20)
reviewer stance: break the paper. Concrete failure scenarios, dossier-cited. Default
to wounded/broken; holds only where the best attack genuinely fails.
date: 2026-08-20

---

## 0. Honest steelman of the operator's fork-the-code instinct (before I break it)

The operator's instinct — "take Lean/Jesse as is, remove what we don't want" — is not
naive. The licences are clean (Jesse MIT, Lean/lean-cli Apache-2.0 — `jesse-repo-study.md:4`,
`lean-cli-study.md:14`), so vendoring is legally free under AD-6's permissive tier. And
Jesse is a **real** asset base: trade-shuffle + candle Monte-Carlo, bootstrap rule
significance, an Optuna+Ray optimize loop, 175 indicators, interactive charts, an MCP
server, and a pure-function research API (`jesse-repo-study.md:§5–§10`). If QMX were a
crypto, float-arithmetic, single-workstation system, forking Jesse would be a genuine
head start and building from scratch would be malpractice. **That is the honest case for
forking, and the paper does not state it — it jumps straight to a constitutional appeal
(D1).** The economics question the operator actually asked ("would forking be faster/
safer?") deserves a costed answer, not a citation. Below I cost it — and it does collapse
to build-our-own, but for reasons the paper never shows, while several "shapes" the paper
*does* want to adopt fail the very same surgery it uses to reject Jesse's code.

---

## 1. Costing fork-and-gut Jesse against QMX's *actual* target (the surgery deletes the wrong 90%)

Run the operator's own knife over the repo and check what survives, using repo facts.

**Rip out floats → AD-7 scaled integers.** Floats are not a layer, they are the
substrate: `Candle` stores `open/close/high/low/volume` as `FloatField`s
(`jesse-repo-study.md:§12`), `metrics.py` returns a flat dict of float ratios (`:§7`),
`order_service` computes `fee = fee_rate * notional` in float (`:§4`), and the hot
numeric path is a **pinned external Rust binary `jesse-rust==1.2.0` whose source is not
in the repo** (`:§11`) and which does float arithmetic (`subtract_floats`/`sum_floats`).
You cannot convert the money path to scaled integers without rewriting `metrics.py`,
`order_service`, the exchange math, **and the Rust crate you don't have the source to.**

**Rip out singletons → AD-15 immutable/one-writer.** `store`/`router`/`config` are
described verbatim as "the backbone" and the reason `research.backtest` needs
`_isolated_backtest` + `store.reset()` to be pickle-safe (`jesse-repo-study.md:§4, §6,
takeaway 2: "a cleaner design would pass explicit context objects"`). Removing them means
rewriting `backtest_mode.py` (1523 lines), `Strategy` (1874 lines), the `store/` and
`routes/` packages, and every service that reads `store`. That is essentially the whole
engine.

**Rip out Postgres/Redis → AD-16 JSONL/no-DB-server.** Candle storage *is* Postgres via
peewee; Redis is pub/sub (`jesse-repo-study.md:§12`). Delete `db.py`, `redis.py`, all
peewee models, the migrator; rebuild the data layer on QMX's Parquet/DuckDB/JSONL
contracts (AD-19).

**Rip out crypto → forex.** The entire data layer is bespoke per-exchange REST drivers
(Apex/Binance/Bybit/…, `jesse-repo-study.md:§12`); QMX's data enters through CT-10/CT-15
intake off a Dukascopy corpus. Delete `exchanges/` and `import_candles_mode/`.

**The one part QMX most needs is the one part Jesse does not have.** Jesse has **no
slippage model at all and a flat single fee** (`jesse-repo-study.md:§4`,
`grep -rln slippage → nothing`). The retail-forex CFD fill engine — variable spread by
hour/event, weekend gaps, swap, partial-lot rounding — has **no good reference
implementation anywhere** (`backtesting-corpus-brief.md:§3, §6.3`) and the old QMX repo's
fill simulator was itself "**unbuilt, Deferred D1**" (`backtesting-corpus-brief.md:§2`).
You build this from scratch whether or not you fork.

**What survives the surgery?** Only textbook algorithm *shapes*: trade-shuffle MC,
bootstrap significance, the `hyperparameters()`/`routes` declaration schemas, the metrics
formulas. These are (a) small, (b) standard, and (c) must be re-expressed on QMX types
anyway — typed R, R-8 seed-as-identity, CT-32 containers. So the fork keeps the ~5–10%
that is cheap to rebuild and deletes the ~90% that QMX must rebuild regardless, while
adding a comprehension tax, licence-header hygiene, and dead crypto/float/singleton
idioms that agents will re-copy from the tree (the verdict doc's exact warning about
backtrader idioms, `backtesting-corpus-brief.md:§3`). **Fork-and-gut is slower and
riskier than build-our-own.** The paper's conclusion holds; its argument is missing.
→ verdict: **build-vs-fork conclusion HOLDS, under-argued.**

---

## 2. The donor-split table is inflated — three "shapes" that do not transfer

### 2a. Jesse's "pure-function API" is a facade over global singletons (does not port)

The paper's flagship adoption (`§2` Jesse row; `§3` Python-API door) is the "pure-function
API returning plain dicts/arrays — perfect for Jupyter." **It is not pure.**
`research.backtest` wraps `_isolated_backtest`, whose "purity" is *reset the process-global
`store` and re-run* (`jesse-repo-study.md:§4 store.reset(), §6, takeaway 2`). The only
reason it exists is pickle-safety for Ray. QMX cannot copy that mechanism — AD-15 mandates
immutable values and one-writer streams, so the isolation model must be built from scratch
on explicit immutable context (the "cleaner design" Jesse itself lacks). And the **return
shape does not port either**: a plain dict of floats violates AD-7 (exact money), AD-11
(typed refusals returned not thrown), and AD-12/CT-32 (every result carries a label with
producer identity, world, fingerprints). Governed QMX evidence is a CT-32 container, *not*
the "plain dicts/arrays" the donor row sells. Only the bare function *signature*
`backtest(config, book, candles) -> result` ports — which anyone would write and is no
donation. The load-bearing 100% (isolation, determinism, typed result) is a from-scratch
build. → **wounded/broken.**

### 2b. The MCP "third door / the Jesse lesson" is a misattribution — Jesse is a counter-example

The paper's central invention — AD-42, "ONE library, THREE logic-free doors... MCP =
the same functions as tools (**the Jesse lesson**)" (`§3`) — cites Jesse for an
architecture Jesse **does not have.** Jesse's MCP server "is a thin MCP wrapper that
**calls the Jesse HTTP API** (it holds `JESSE_API_URL`/`JESSE_PASSWORD`)" and **requires
Jesse to be running** (`jesse-repo-study.md:§9`; `jesse-docs-study.md`: "Requires Jesse to
be running locally — not standalone"). So Jesse has **three heterogeneous stacks**, not one
library with three doors: (1) web controllers over the singletons, (2) `research.*` pure
functions over `_isolated_backtest`, (3) MCP-over-HTTP against the web server. The MCP door
and the "pure functions" are literally different code paths reaching the compute
differently. **The paper's "nothing can drift between the doors" is exactly what Jesse
failed to build** — its MCP can drift from its research API because they don't share a
path. Selling AD-42 as "the Jesse lesson" inverts the evidence. → **broken (attribution);
the shape must be presented as QMX's own novel design, with its cost owned, not borrowed.**

### 2c. The LEAN "composition skeleton" is already QMX's own, and its mechanism is banned

The paper (`§2` LEAN row) takes "the composition skeleton... this is literally our
contract-hub paradigm." But Lean's config-composition **is C# reflection + Docker +
assembly-qualified class names** resolved at startup (`lean-cli-study.md:§8`), whose entire
reason to exist is swapping *compiled assemblies* without recompiling inside a Docker
image. QMX has none of that constraint (pure Python, uv.lock, Docker explicitly not
required per the paper's own `§2` rejection row), and AD-2 **bans the mechanism**:
"discovery by explicit registration at the composition root, **never ambient scanning**"
(`spine-index.md:AD-2, §Extension shapes`). "One kernel, three wirings" is QMX's own prior
art already (AD-8 injected clock, AD-12 worlds, AD-35 paper mode, verdict-doc §2.1 in
`backtesting-corpus-brief.md:§3`). The row re-badges the spine's paradigm as a Lean gift
and, worse, risks an implementer reaching for reflection/Docker "because Lean is the
donor." The single genuinely borrowable Lean idea is small and belongs to the *CLI*, not
the engine: write the fully-resolved run-config out as an inspectable artifact that feeds
the fingerprint — already implied by AD-10/AD-12 (fingerprint covers the resolved config,
`lean-cli-study.md:§3`). → **wounded; demote the row.**

### 2d. Optimize + Rust rows import weaknesses or nothing

"Monte Carlo/optimize as first-class tools (Jesse shape)" quietly imports Jesse's *bad*
search: Optuna is used only as a persistence ledger while the actual sampler is home-grown
`np.random` + Ray — "a pattern, **not** best-practice Bayesian optimization; QMX could
genuinely use Optuna's samplers" (`jesse-repo-study.md:§5, takeaway 4`). And R-8/R-9 demand
seed + foreign-artifact provenance Jesse's dicts don't carry
(`five-hats-and-docs-state.md:R-8, R-9`). The "Rust (their `jesse-rust` precedent)" row is
a non-donation: the crate source **is not in the repo** (`jesse-repo-study.md:§11`), so
there is nothing to borrow but the fact that someone used Rust, and AD-13 already governs
speculative Rust (measure-then-budget). → **wounded; narrow both rows to declaration
schemas only, and explicitly reject Jesse's search mechanism.**

---

## 3. Scope creep — is three-doors + a registry-view CLI bigger than the compute problem?

**The operator's stated problem** is compute + Book-testing + portability: "the sandbox
itself has the CLI," agents backtest against a Book, decentralized (DEC-0084 dead —
`backtesting-corpus-brief.md:§1.1`), and research usable on other laptops.

**A single pip/uv-installable pure library solves all three by itself.** It runs in the
sandbox (compute, decentralized), resolves a Book from the registry snapshot
(Book-testing), and *is* "Jupyter anywhere" — the paper's own `§4` "Jupyter anywhere" row
is satisfied by the library **alone**, no CLI, no MCP. Ticket 008:24 says **agents**, not
the operator, execute backtests (`backtesting-corpus-brief.md:§1.3`); QMX's factory agents
are Python-capable and can `import` the library or already speak MCP — they do not need a
shell CLI. And the operator is **non-technical** (MEMORY: operator profile) and drives the
UI/Simulator (`backtesting-corpus-brief.md:§1.2`, Simulator is UI-driven), not
`qmx backtest --book scalping@2`. **So the CLI door has no clear primary user** — agents
prefer the library/MCP, the operator prefers the UI.

The operator *did* dictate a CLI ("our own Lean CLI") and MCP, so three surfaces are
fair as pragmatic conveniences. What is **not** fair is elevating them to AD-42's "the
capability appears at all three doors **mechanically; nothing can drift**." For a ~6–8
function surface (backtest/optimize/MC/significance/report), the honest engineering is
**three thin hand-written wrappers** — Lean's CLI proves zero-logic wrappers work fine
(`lean-cli-study.md:§0`) and a 5-line wrapper cannot drift. Read literally, "mechanically"
instead demands a **codegen/binding generator** that reflects library signatures into CLI
commands and MCP tools while threading AD-11 refusals and AD-12 labels across three
transports — a real, unbudgeted subsystem the paper hand-waves as free. Either reading
wounds AD-42: it is either not worth a spine invariant, or it is unrequested scope dressed
as elegance. → **wounded/broken on AD-42.**

---

## 4. AD-43 is half-restatement, and minting AD-42..45 now is premature

**AD-43 "the CLI auto-updates — the gold."** Books/BMS/bots are *already* versioned,
fingerprinted registry records (AD-16, `spine-index.md`). A reader reflecting current
state is the ordinary behavior of every registry consumer — the UI "auto-updates" the same
way. "If I update the BMS the CLI updates" is not a new noun; it is what reading a store
means. The genuinely load-bearing half — pin the CLI version and **fingerprint the registry
snapshot into the result label** (Lean's `:latest` trap, `lean-cli-study.md:§3`) — is a
determinism rule already owned by AD-10/AD-12 (the result label already carries input
fingerprints). AD-43 fuses an AD-16 restatement with a fingerprint rule that belongs under
AD-10/12. → **wounded; fold the real half into AD-10/12, drop the "gold" novelty claim.**

**Minting AD-42..45 into the spine now is out of sequence.** The paper's own `§5` defers
the payload — fill models, fidelity taxonomy, result-key tuple, SR* (GAP-0048/0049) — and
`map.md:76` marks fidelity taxonomy + result-key tuple as **irreversible** ("each
invalidates every prior stored result if changed later," `backtesting-corpus-brief.md:§1.2`).
The doors' signatures are payload-coupled: `§4` maps every function onto CT-32 +
`hyperparameters()`/`routes` shapes. Freezing the delivery vehicle before its irreversible
cargo is ratified means re-cutting all three "mechanically bound" doors when the deferred
sitting rules fidelity or the result-key tuple. The verdict-doc "provenance can't be
retrofitted, so commit the surface early" defense fails here precisely because AD-42 bakes
the function surface — and that surface carries the deferred, irreversible decisions.
→ **wounded/broken; keep AD-42..45 as recorded candidates for the backtesting sitting, do
not mint into the spine until GAP-0048/0049 land.**

---

## 5. The "80% already ratified" framing anchors a non-technical operator on a cheap increment

`§1`: "80% of the dictation is already ratified law; 20% is one new noun + feature
commitments." The 80/20 is counted in **dictation lines, not build cost.** Every
"already ratified" row is a ratified *contract/seam* — still **0% built.** The expensive,
risky, reference-less core (the retail-forex fill engine — no reference implementation
anywhere, `backtesting-corpus-brief.md:§6.3`; the old fill simulator "unbuilt, Deferred
D1," `§2`) is entirely ahead and, by the paper's own `§5`, deferred. Telling a
non-technical operator "80% is done, mint four ADs" anchors him on a cheap-looking sitting
while the costly, hard, deferred work goes unpriced. → **wounded; add a build-cost
paragraph separating ratified governance from unbuilt engineering, and foreground that the
fill engine is the real cost and is deferred.**

---

## 6. What holds

- **Build-our-own over fork** (`§1` last row, `§2`) — my best attack (MIT + mature Jesse
  is a head start) genuinely fails once surgery is costed; the fork deletes the load-bearing
  90% and keeps the textbook 10%. **HOLDS** (add the costing).
- **world = replay legal now, world = simulated deferred / never validates edge**
  (`§3`, `§5`) — matches AD-12, L20, `spine-index.md` collision flags 1 & 3. **HOLDS.**
- **D1 shape-not-code, no donor code in the tree** — matches DEC-0085/0086 dead,
  `map.md` build-our-own. **HOLDS** (but the donor "shapes" in §2 above are narrower than
  the table claims).
