---
name: cut-extensibility
sitting: architecture-QMX-2026-09-14
checkout: main (planning)
product: integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2
evidence_method: git ls-tree / git show; docs on this checkout
status: investigation-only
---

# Cut — user-facing extensibility

Architecture only. No implementation. Product code inspected on `integration` @ `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`. Class/test existence is not end-to-end proof. CT YAML `defined-unwired` / “no code exists” on CT-40..51 is **stale** relative to integration source.

**Audience of this cut:** a QMX user who will not read our source. What they can change, install, or author — versus what is only a composition-root catalog, versus what is GAP-0081 deferred.

Spine already adopted **AD-12** (four rungs). This cut confirms it from source and pins the one remaining builder fork: QMB adapters are **closed catalogs**, not drop-in packs.

## Compact table

| Surface | Class | Evidence | Owner | Non-source user sees | Gap |
|---|---|---|---|---|---|
| ui-editable config on Book/BMS/Bot templates + AD-26 registry | **reuse** | documented-design + source-inspected | qmf-risk CT-22/27; QML CT-33 `UiFlag`; `docs/registry/variables.yaml`; QMA `variable.set` | Edit flagged numbers (once a client exists) | UI chrome = GAP-0081; wire binds now |
| Ordinary Python / QML two-artifact bot | **reuse** | source-inspected | COMP-QML + QMB host | Write a `.py` callback; graduate later | Host CT-06 mint is wiring |
| QMB fill/slippage/cost/financing + data `ProviderAdapter` | **reuse** (select) / **extend** (new id) | source-inspected | COMP-QMB catalogs | Pick an adapter-id in run-config. **Not** a drop-in folder | Calibration content GAP-0048 |
| QMA plugins, skills, graph templates, desk packs | **reuse** | source-inspected | COMP-QMA-CORE defines; COMP-QMA-DAEMON loads | Install a first-party `{desk}-*` pack | No store (Cut); live process wiring |
| Operator Routines | **reuse** | documented-design + source | COMP-QMA-DAEMON | Author a Routine that names a graph template | Live scheduler wiring |
| UI contribution SDK / `ui_view` / `qma-ui-contract` | **deferred** (reuse the deferral) | source-inspected + documented-design | later UI sitting | **Nothing.** Widgets are not a V1 extension point | **GAP-0081** |
| Plugin marketplace / trust tiers / capability solver | **cut** (do not revive) | source-inspected | — | Not a product | DEC-0361/0362 |
| No-code / `.qml` DSL / GAP-0085 mechanism kit | **deferred** | documented-design | QML increment if ever | Not promised | GAP-0085; DEC-0172 |
| QMF calendar / indicator **extensions** (roster-outside packages) | **reuse** (platform) | documented-design | composition root | Not the user ladder | L14 / L33 |

**Overall verdict:** **reuse** rungs 1–3; **connect** operator-facing `variable.set` / `plugin.install` over a live wire; **do not new** a UI plugin SDK or a sixth extensibility package.

---

## Ladder (AD-12 confirmed)

From [`ARCHITECTURE-SPINE.md`](../ARCHITECTURE-SPINE.md) AD-12:

1. ui-editable config variables on templates
2. ordinary Python logic **and** QMB ports/adapters (split below)
3. QMA plugins, skills, graph templates, desk packs
4. UI contribution SDK — **GAP-0081 deferred**

Rungs 1–3 bind now. Rung 4 stays deferred. No-code authoring is not promised. QMA “plugin” vocabulary stays QMA-scoped (DEC-0346). QMB/QMF still say **extensions**, never plugins (`docs/AGENTS.md` hard rules).

Lead only: `workroom/research/2026-09-14-ui-feature-route.md:64` already noted backend extension vs missing UI contribution — source inspection below settles that split.

---

## Rung 1 — config variables (reuse)

**Law.** Configurable ≡ UI-editable at platform level (L38, `docs/constitution.md:92`; DEC-0157). Recorded numbers are evidence, never spine constants.

**Templates (user-facing numbers).**

- Book/BMS templates: per-variable `ui-editable | uneditable` (AD-30, DEC-0144; `docs/components/qml.md:60` restates AD-30 on CT-33).
- CT-33 parameter space: every declared variable carries exactly one `UiFlag` (`ui-editable` / `uneditable`) — `git show integration:qml/src/qml/declaration/parameters.py` (`UiFlag`, `parse_ui_flag`, `ParameterSpec.ui`). Defaults are the canonical assignment; promoting a tuned assignment mints a **new Bot version**.
- QMB wind tunnel: changing test conditions means changing config, never swapping the tunnel (`docs/components/qmb.md:64`, B-3). Compiler layers: invocation flags > run spec > BMS fragment > Book fragment > workspace defaults. Fragments are derived fp1 artifacts, never free-hand-edited (`git show integration:qmb/src/qmb/config/fragments.py`).

**Platform registry (AD-26).** `docs/registry/variables.yaml` is the machine-readable schema. QMB governor/limits (`qmb_governor_cpu_budget` …) and the QMA AD-26 set (`quant.quiet_hours`, `hook.timeout_*`, `wire.deprecation_minors`, `environment.max_in_flight`, … from `:1672`) are `configurable: true`. QMA registry-homed rows move only by an `operator`-principal **`variable.set`** (`docs/components/qma-wire.md:116`; `git show integration:qmx-agents/packages/qma-wire/src/qma/wire/principals.py:84`). Record-homed rows (Quant `WakePolicy`) move by `quant.write`, never `variable.set`.

**What the non-source user does:** edit flagged fields on a template, or `variable.set` through a client. They do not edit YAML in git.

**Missing:** a live daemon + a settings surface over the wire. That is **wiring / GAP-0081 chrome**, not a missing variable model.

---

## Rung 2 — ordinary Python (reuse) vs QMB adapters (reuse select / extend catalog)

### 2a. Ordinary Python — the real user-authored extension

**Law.** L9 ordinary Python; L33 plain-Python authoring outside governed evidence is always legal; graduation is a versioned package registered at a composition root (`docs/constitution.md:34,82`).

**QML.** Governed bot = CT-33 declaration + versioned plain-Python logic. `.qml` DSL is not revived (DEC-0172; `docs/components/qml.md:19,60`). Ungoverned bots need **zero `qml` imports**:

- `git show integration:qml/tests/plain_research_bot.py` — `PlainResearchBot.on_instant`; module must not import qml.
- `admit_ungoverned_tunnel()` at `qml/src/qml/conformance/registration.py:318` — tunnel stays open; conformance tickets governed evidence and seats only.
- QMB `qml_compile` skips ungoverned cites (`git show integration:qmb/src/qmb/config/qml_compile.py`).

**QMB host.**

- QL-7 adapter for conformant bots: `git show integration:qmb/src/qmb/host/adapter.py` — `construct_conformant_bot` / `ConformantSliceHandler`. Ungoverned bots never require this path.
- Injected `SliceHandler` protocol on the run loop: `git show integration:qmb/src/qmb/runloop/loop.py:600` — five hooks (`update_stream`, `scheduled_position_event`, `execute_resting`, `update_closed_data`, `mint_intents`). A research author implements this (or a QML `on_instant`) without reading daemon internals.

**QMF escape hatches (same rung, not a second product):** custom indicators and structure families stay legal as plain Python until graduated as separate SemVer packages (`docs/components/qmf-indicators.md` escape hatch; L33). Not a UI widget.

**Missing wiring, not function:** host CT-06 Bot-kind mint (OR-06 — QML returns fingerprintable content; composition root stamps the envelope). Node/QMB seat binding is outside QML.

### 2b. QMB adapters — closed catalogs, not user drop-ins

This is the builder fork AD-12’s “ports/adapters” wording can hide.

**Execution (B-6).** Fill, slippage, cost, financing are **separate** `Protocol` ports, bound **only** from the resolved run-config. Ambient discovery is illegal:

- `AMBIENT_DISCOVERY = False` — `git show integration:qmb/src/qmb/execution/adapters.py`
- `BOUND_FROM_RESOLVED_CONFIG = True`; keys `fill_adapter`, `slippage_adapter`, `cost_adapter`, `financing_schedule` — `git show integration:qmb/src/qmb/execution/binder.py`
- Closed catalogs: fill `declared-path`; slippage `zero | constant-percent | spread-crossing | gap-volatility | size-tiered`; cost `zero | per-lot | percent-of-notional | notional-minimum`; financing `scheduled`
- Unknown adapter-id → typed refusal. Passing a port object is refused. Calibration *content* stays GAP-0048.

**Data.** `ProviderAdapter` protocol (`fetch`, `earliest_available`, `list_symbols`, …) — `git show integration:qmb/src/qmb/data/ports.py`. Dukascopy is adapter #1; persistence stays CT-15/CT-10 (`docs/contracts/ct-15-external-source-adapter.yaml`). A new vendor is a **platform catalog extend**, registered at the composition root, not a user pack.

**Venue adapters** are **not** this ladder. Nothing but `qmn.venue` imports `qmf-venue` (L30). QMB/QML/QMA never grow a venue-adapter drop-in.

**What the non-source user does:** choose adapter-ids (and named condition presets) in run-config / CLI. They do **not** drop a `FillPort` class into a folder.

**QMB’s own extensibility law** (`docs/components/qmb.md:53`): add adapters, config fragments, or library functions — never re-architect the tunnel. “Add adapters” means **catalog amendment by the platform**, then config selection by the user.

---

## Rung 3 — QMA plugins / skills / graph templates (reuse)

Backend extension **already exists** as library source. Trust is first-party only. There is no `ui_view`.

**Contribution surface (CT-42).** `qma-core` defines; daemon implements; packs import `qma-core` never `qma-daemon`.

- Manifest + roster: `git show integration:qmx-agents/packages/qma-core/src/qma/core/plugins/manifest.py`
- `PluginContext` registration methods: `git show integration:qmx-agents/packages/qma-core/src/qma/core/plugins/context.py` — singletons (MemoryProvider, KnowledgeSource, ExecutionEnvironment, ComputeProvider, ContextCompiler) and eight multi points: `tool`, `tool_adapter`, `hook`, `skill`, `graph_template`, `model_deployment`, `toolset`, `worker_template`
- Cardinality law: `git show integration:qmx-agents/packages/qma-core/src/qma/core/ports/cardinality.py` — `RETIRED_CONTRIBUTION_POINTS = {ui_view, command, mission_template}` (`:91`). A point with no `qma-wire` schema may not register (`docs/components/qma-core.md:59`; CT-42 invariant).
- Loader: `git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/plugins/loader.py` — `FILE_WATCHER_ENABLED = False`; load phases; LIFO unload; `plugin.install` / `enable` / `reload` are operator-gated.
- Cut surfaces: `git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/plugins/load_refusal.py` — `CUT_PLUGIN_SURFACES = {trust_tier, marketplace, plugin_store, install_count, capability_solver}`; `GAP_0081_STATUS = "deferred"`; excluded points `ui_view` / `ui_package` / `ui_extension`; `DAEMON_PLUGIN_RENDERS = False`.

**Five first-party desk packs** (`qmx-agents/plugins/` on integration), each `manifest.json` + `daemon/plugin.py` `activate(ctx)`:

| Pack | Contributions a user could name |
|---|---|
| `analysis-backtest` | tool `qmb`, skill `replay`, graph template `notebook`, toolset `replay-tools` |
| `research-corpus` | MemoryProvider (in-process), KnowledgeSource `strats`, skill `survey-skill`, graph `survey` |
| `dev-factory` | tool `plan`, hook `lint`, skill `factory`, worker template |
| `trading-readonly` | read-only tools + MCP adapter; skill `tape-read`; **no** money-path acts |
| `pm-coordination` | tool `status`, hook `review`, skill `coordinate`, graph `standup` |

Packs declare `"daemon_renders": false` and `"peer_integration": "qma_wire_only"` (e.g. `analysis-backtest/manifest.json:17`). Every pack has empty `ui/` (`.gitkeep` only) — a slot for a later UI half, **not** a contribution point.

**Skills ≠ capability.** `skill_payload(..., grants_capability=False)` in `git show integration:qmx-agents/packages/qma-core/src/qma/core/plugins/packs.py`. A skill may invoke a Loop; it does not grant tools.

**Graph templates** are authored, versioned, **stateless** topology; the daemon compiler expands them into a Task Graph (AD-13). Seed examples: `analysis-backtest:notebook`, `research-corpus:survey`, `pm-coordination:standup`. GAP-0086 (graph engine) and GAP-0084 (Mission Template registry) stay deferred.

**Operator install path (when a process exists).** Human-gate commands include `plugin.install`, `plugin.enable`, `plugin.reload`, `routine.write`, `variable.set` — `git show integration:qmx-agents/packages/qma-wire/src/qma/wire/principals.py:61-84`. A non-source operator installs a **first-party** pack and writes Routines that cite fully-qualified `<plugin_id>:<local_id>` ids. They do not browse a store.

**Missing wiring:** composed asyncio daemon that actually loads the roster and publishes contributions on a live wire (`code-qma.md` already: library, not observed listener). Default QMB door transport still **records** invocations. That is connect-wave (AD-8), not a new plugin model.

**Stale docs:** CT-42 `wiring_status: defined-unwired` / “no code exists” (`docs/contracts/ct-42-qma-plugin-manifest-context.yaml:9,79`) is false against integration. Documentation-factory debt, not an architectural fork.

---

## Rung 4 — UI contribution (GAP-0081 deferred, not missing-by-accident)

**Gap text** (`docs/gap-report.md:224`): UI presentation architecture, Rust extension technology, UI SDK surfaces, contribution points, UI plugin packaging, and `qma-ui-contract` beyond a stub. Revisit once the daemon API is live. Wire (AD-5) and variables (AD-26) **are not deferred**. UI reads as a trading/research terminal, not a generic agent dashboard (DEC-0304, DEC-0333).

**Source:** `git show integration:qmx-agents/packages/qma-ui-contract/STUB.md` — no `pyproject.toml`, no `src/`, not a workspace member. Explicit: do not add UI SDK / contribution point / packaging in this increment.

**What this sitting must not do:** invent `ui_view`, a Rust plugin ABI, a widget pack format, or a parallel UI extension COMP. First-party packs may later grow a UI half that talks **only** over `qma-wire` (`docs/contracts/ct-42-qma-plugin-manifest-context.yaml` “halves communicate only over the wire”; daemon never renders). That half is GAP-0081’s session.

**What a future UI *can* bind without a SDK:** existing wire commands/queries/events; AD-26 `variable.set`; plugin install/preflight; Routine write; QMB CLI/API; CT-33 parameter `ui` flags. Chrome is not an extension point.

---

## What a user who will not read source can actually do

| They can (product intent, rungs 1–3) | They cannot (V1) |
|---|---|
| Change ui-editable numbers on a Bot/Book/BMS template | Add a UI widget / panel / menu via a pack |
| Override experiment parameters in QMB (non-canonical); promote by minting a new Bot version | Ambient-scan a `FillPort` from a folder |
| Drop a plain-Python `on_instant` / `SliceHandler` module into a project and `import qmb` | Author a `.qml` DSL or typed Entry/Exit/Filter kit (GAP-0085) |
| Select fill/slippage/cost adapter-ids and named condition presets in run-config | Install a third-party plugin from a store |
| (Operator) install/enable a first-party `{desk}-*` pack; write a Routine citing a graph template / skill | Have QMA execute, size, or promote; paper included |
| (Operator) `variable.set` registry-homed AD-26 rows | Edit uneditable pins (`qmb_cli_pin`, `qmb_sampler_pin`) |

Extensibility that requires reading source (implement a new catalog adapter, a new CT-15 provider, a new QMF indicator package, a new desk pack’s `activate()`) is **platform extend**, not the user-facing ladder.

---

## (1) What already exists

- L38/AD-30/AD-26 variable discipline + CT-33 `UiFlag` + QMB config compiler/fragments + wire `variable.set`.
- L33/QL-1 ungoverned Python; two-artifact QML library; QMB `SliceHandler` + QL-7 host adapter.
- QMB closed execution/data adapter catalogs bound from resolved run-config (`AMBIENT_DISCOVERY=false`).
- QMA CT-42 contribution surface, daemon loader, five seed packs with skills/graph templates/tools, first-party trust, `ui_view` retired, `qma-ui-contract` stub, GAP-0081 encoded in load-refusal.
- Human-gate install/reload/routine/variable commands on `qma-wire` (library).

## (2) Missing wiring vs missing function

| Missing wiring (function present) | Missing function (deferred / cut / not promised) |
|---|---|
| Live `qma-daemon` process loading the roster and serving `plugin.install` / `variable.set` | UI SDK, Rust extension ABI, `ui_view`, UI pack format (**GAP-0081**) |
| Settings/template editors over the wire (chrome) | Plugin store, trust tiers, capability solver (**Cut**) |
| Host CT-06 mint of CT-33 content; QMB CLI coverage of every library rung | No-code authoring; `.qml` DSL; GAP-0085 mechanism recombination |
| Real QMB CLI transport behind `analysis-backtest` (AD-8 connect) | New execution adapter *classes* as user packs (must stay catalog-extend) |
| CT-40..51 / CT-42 `defined-unwired` stamp refresh (docs drift) | GAP-0048 adapter calibration *values*; GAP-0086 graph engine |

## (3) Recommended architectural ownership

| Concern | Owner | Class |
|---|---|---|
| ui-editable numbers, templates, AD-26 rows | qmf-risk + QML declarations + `variables.yaml`; QMA `variable.set` | reuse |
| User-authored strategy/research code | COMP-QML + QMB `SliceHandler` / ungoverned tunnel | reuse |
| Execution/data adapter **ids** in a run | COMP-QMB catalogs + config compiler | reuse (select) |
| New adapter **implementation** | COMP-QMB catalog extend at composition root | extend (platform) |
| Desk packs, skills, graph templates, hooks, toolsets | COMP-QMA-CORE (types) + COMP-QMA-DAEMON (loader) + `qmx-agents/plugins/*` | reuse |
| Install / enable / Routine authoring | `qma-wire` human-gate; future UI is a client | connect |
| UI widgets / SDK | **none now** — GAP-0081; stub `qma-ui-contract` | deferred |
| New COMP-EXT / marketplace / UI plugin runtime | **forbidden** | new would violate AD-1/AD-12/DEC-0361 |

Do not mint a sixth application for “extensibility.” Do not treat source-only catalog amendment as the product’s user-facing promise.

## (4) Open questions — AD vs Deferred

| Question | Route |
|---|---|
| Four-rung ladder; no UI SDK this sitting; no-code not promised | **Already AD-12.** Confirm; do not reopen. |
| Are QMB adapters user drop-ins or closed catalogs? | **Pin in AD-12 (this cut):** closed catalogs, `AMBIENT_DISCOVERY=false`, bind from resolved run-config. New ids = platform extend. This is the one invariant two builders could otherwise choose incompatibly. |
| UI presentation / Rust / contribution packaging | **Stay Deferred GAP-0081.** Wire + variables already bind. |
| Plugin store / third-party trust | **Stay Cut.** First-party only. |
| GAP-0085 typed mechanism recombination | **Stay Deferred** (QML increment). Not an extensibility-SDK substitute. |
| GAP-0084 Mission Template vs Graph Template | **Stay Deferred.** |
| How a non-developer *installs* a first-party pack (path vs uv extra vs wire upload) | **Can wait** — operator `plugin.install` already named; packaging UX is GAP-0081-adjacent, not a new contribution point. |
| Refresh CT-42/CT-40 `wiring_status` | Docs-factory hygiene, not an AD. |

**recommended_ad:** pin AD-12’s rung 2 so QMB adapters stay closed catalogs (no ambient discovery, no user FillPort drop-in); GAP-0081 remains the UI-SDK deferral. No new numbered AD if the spine absorbs that one sentence. If the sitting will not amend AD-12 prose, treat the pin as the AD; do not leave “QMB adapters” as a drop-in reading.

---

## Citations (primary)

**Docs (this checkout):**
- `docs/constitution.md:34` L9; `:82` L33; `:92` L38
- `docs/gap-report.md:224` GAP-0081
- `docs/components/qma-core.md:59` no `ui_view`
- `docs/components/qma-wire.md:108-116` human-gate + deferred UI + `variable.set`
- `docs/components/qmb.md:23-25,53,64` no “plugin”; extensibility = adapters/fragments/functions; B-3 no ambient bind
- `docs/components/qml.md:19,60` two-artifact + ungoverned Python
- `docs/contracts/ct-42-qma-plugin-manifest-context.yaml:31,63` retired `ui_view`
- `docs/contracts/ct-15-external-source-adapter.yaml` data adapters
- `docs/registry/variables.yaml` AD-26 / QMB / node configurables
- `ARCHITECTURE-SPINE.md` AD-12 (this sitting)

**Integration (`git show integration:<path>`):**
- `qmx-agents/packages/qma-ui-contract/STUB.md`
- `qmx-agents/packages/qma-core/src/qma/core/plugins/{context,manifest,packs}.py`
- `qmx-agents/packages/qma-core/src/qma/core/ports/cardinality.py:91`
- `qmx-agents/packages/qma-daemon/src/qma/daemon/plugins/{loader,load_refusal}.py`
- `qmx-agents/packages/qma-wire/src/qma/wire/principals.py:61-84`
- `qmx-agents/plugins/{analysis-backtest,research-corpus,dev-factory,trading-readonly,pm-coordination}/`
- `qml/src/qml/declaration/parameters.py` (`UiFlag`)
- `qml/src/qml/conformance/registration.py:318` (`admit_ungoverned_tunnel`)
- `qml/tests/plain_research_bot.py`
- `qmb/src/qmb/execution/{ports,adapters,binder}.py`
- `qmb/src/qmb/data/ports.py`
- `qmb/src/qmb/runloop/loop.py:600` (`SliceHandler`)
- `qmb/src/qmb/host/adapter.py`
- `qmb/src/qmb/config/{compiler,fragments,qml_compile}.py`

*Planning checkout `main`. Product cited at `integration@1b451a848d897e42f6e2c7fd9f2ea86fab7295f2`. No branch switch, commit, or implementation.*
