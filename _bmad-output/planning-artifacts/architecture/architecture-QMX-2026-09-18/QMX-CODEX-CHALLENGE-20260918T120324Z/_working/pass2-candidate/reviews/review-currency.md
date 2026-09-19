# Review — Currency / Reality lens

**Spine:** `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/ARCHITECTURE-SPINE.md` (draft 2026-09-18, AD-1..AD-22)
**Companions consulted as a map, then re-checked:** `STACK-AND-EVALUATION.md`, `UI-HOST.md`, `COPILOT-AND-APPS.md`, `RECON-RETURN.md`
**Lens:** every committed technology and factual claim must be web-current or brownfield-checked, not asserted from training memory. This sitting is brownfield composition-kit, not a new starter.
**Inspected trees:**
- `C:/Users/Mubarak/Desktop/QMX-worktrees/epic-051-skylos-mill-split` @ `270e992995c2378ca63cf6343254ef8140a8c97e` (`git rev-parse HEAD` exact match; spine cites `integration@270e992`)
- Inherited pin source: workspace `docs/architecture/stack.md` (`verified: 2026-09-16`) plus worktree `docs/architecture/stack.md` (`verified: 2026-08-29`)
**Reviewer gate date of checks:** 2026-09-18

Web (primary sources, this sitting): python.org downloads + 3.14.7 release page + PEP 790; npm `@json-render/core` + github.com/vercel-labs/json-render; modelcontextprotocol.io SEP-1865 + ext-apps `specification/2026-01-26` + MCP spec 2026-07-28; PyPI JSON optuna 5.0.0 / mutmut 3.8.0 / duckdb 1.5.5; GitHub boxed/mutmut README (fork/WSL/`apply`); GitHub n8n 2.39.8, QuantConnect/LEAN 18106, OpenBB widgets.json/apps.json docs, NousResearch/hermes-agent; GitHub/crates.io uv 0.12.16; edonadei/caliper.

Brownfield (this sitting): `.python-version`; `qmb/pyproject.toml` `optuna==4.9.0` + `click==8.4.2`; `packages/qmf-data/pyproject.toml` `duckdb==1.5.5`; `qml/src/qml/research/` + `qml/src/qml/host/research_store.py`; `validate_graph_template_topology`; `MissionCompiler._expand_template`; `TaskGraph` fields; `topological_plugin_order`; `published_contributions`; QMA `import qmb` barrier; federated hit tokens.

---

## Verdict

**PASS.**

Named technologies still exist and still fit the roles the spine assigns them. Version claims this sitting restates were independently reproduced today. Presentation candidates (json-render, MCP Apps SEP-1865) are real and correctly left unpinned. Mutation testing (mutmut) is real, POSIX/`os.fork`-only, and correctly refused as a product dependency. The brownfield pins this sitting restates match `270e992`. This sitting adds **no required runtime**.

Three low findings record inherited drift and CONNECT-style notes this Stack table omits. None invent a vanished library, a wrong current version, or a brownfield pin that is not on the inspected SHA.

---

## What I verified on the web (primary sources)

### CPython — Stack row: `3.14 (observed 3.14.6 at 270e992; docs 3.14.7 current at last stack verify — not upgraded here)`

- **Latest stable = 3.14.7, released 2026-08-05.** Confirmed: python.org “Latest: Python 3.14.7”; python.org/downloads/release/python-3147/; python.org/downloads/ lists 3.14 as bugfix (PEP 745). No 3.14.8 today.
- **3.15 is not stable.** PEP 790: 3.15.0rc2 actual 2026-09-01; **3.15.0 final expected 2026-10-01**. python.org news 2026-09-01: “Python 3.15.0 candidate 2 is here!” Spine does not claim 3.15. See L-2.
- **Brownfield:** worktree `.python-version` is `3.14`; this machine `python --version` → **3.14.6** (tags/v3.14.6, Jun 10 2026); `sqlite3.sqlite_version` → **3.50.4**. Matches the Stack observation and the QMA 2026-08-28 currency finding. This sitting does not re-pin SQLite.
- **Fit:** inherited DEC-0099 pin of the 3.14 line still holds. Observed 3.14.6 vs docs 3.14.7 is the same minor line; “not upgraded here” is the right posture.

### json-render — Stack / AD-17: not pinned; `@json-render/*`, latest v0.20.0 as of 2026-08-18

- **Exists:** https://json-render.dev live; catalog-constrained generative UI (define catalog, register components, AI emits JSON inside the catalog).
- **Upstream:** github.com/vercel-labs/json-render latest release **v0.20.0** (2026-08-18). npm `@json-render/core` **0.20.0** (Apache-2.0, homepage json-render.dev, fetched registry.npmjs.org 2026-09-18). Still the tip; no 0.21.x. Not a PyPI package — correct that this sitting does not invent a Python pin.
- **Fit:** AD-17 “may assemble **registered** inspectors/forms” and “json-render as runtime” in Prevents matches the catalog-guardrail model. Native QMX panes remain first. Unpinned presentation candidate is the correct currency posture.

### MCP Apps — Stack / AD-17: `SEP-1865 stable 2026-01-26`

- **Exists and dated:** github.com/modelcontextprotocol/ext-apps Specification table: **`2026-01-26` | Stable** (`specification/2026-01-26/apps.mdx`; Status: Stable (2026-01-26)). A `draft` folder exists beside it; the spine names the stable dated spec, not the draft. SEP-1865 on modelcontextprotocol.io is Status **Final**. `ui://` resources + tool-linked sandboxed HTML match AD-17 wording.
- **Do not conflate with the QMA MCP adapter pin.** Inherited QMA stack pins **Model Context Protocol revision 2026-07-28** as the ToolAdapter surface. That is still the latest core protocol (modelcontextprotocol.io “Version 2026-07-28 (latest)” as of 2026-09-13). Spine AD-17 names the Apps extension only, as a presentation candidate, not a daemon dependency. Fit is correct.

### Optuna — Stack: `optuna==4.9.0` in qmb — TPE search only

- **Brownfield pin:** `qmb/pyproject.toml` `optuna==4.9.0`; `uv.lock` wheel/sdist **4.9.0** (upload-time 2026-06-01); `DEPENDENCIES.md` and `registry:qmb_sampler_pin` agree.
- **Current upstream:** PyPI JSON `info.version = 5.0.0`, `release_url = …/optuna/5.0.0/` (2026-09-07). Classifiers include `Programming Language :: Python :: 3.14`. 4.9.0 remains published.
- **Posture:** this sitting restates the lockfile pin and does **not** bump. Correct under DEC-0168 (optuna major = contract-versioning event). Stack row does not write that 5.0.0 exists and is not adopted. See L-1.
- **Fit:** TPE-class sampler adapter only. Mental-model refuse of “TPE as generation” is inherited Workbench AD-4 / B-family law, not a vendor disappearance.

### mutmut — AD-19 / Stack: not a dependency; optional WSL/POSIX later; requires `os.fork`

- **Exists:** PyPI `mutmut` **3.8.0** (`release_url` pypi.org/project/mutmut/3.8.0/; `requires_python >=3.10`; classifiers include Python 3.14 and 3.15). GitHub boxed/mutmut README (main, fetched 2026-09-18): “Mutmut must be run on a system with fork support. This means that if you want to run on windows, you must run inside WSL.” Both `fork` and `forkserver` “require `os.fork`, so they are POSIX-only.” `mutmut apply <mutant>` still writes mutants to disk; README: “You should **REALLY** have the file you mutate under source code control.”
- **Fit:** AD-19 “not a product dependency; `mutmut apply` on shared worktrees; mutation score as architecture proof” matches live docs. Optional later on disposable copies. Windows host = WSL is still the vendor constraint, not a QMX invention.
- Spine “current docs 2026-09-18” is a sitting-date stamp, not a version pin. Independently re-verified today. No version to go stale.

### Inherited stores / tooling this sitting does not bump

| Pin | Spine posture | Web / brownfield 2026-09-18 |
| --- | --- | --- |
| uv workspace + lockfile | inherited (`stack.md`) | Current uv **0.12.16** (GitHub/crates.io, released 2026-09-17). Ratified stack still names 0.12.5 (QMF) / 0.12.7 (QMA). Same 0.12.x line. Informational only. |
| DuckDB | inherited store, no version restated here | Brownfield `duckdb==1.5.5`. PyPI latest **stable still 1.5.5** (2026-07-22); 1.6.0 and 2.0.0 are `.dev` pre-releases. |
| Parquet / SQLite / JSONL | inherited store engines | Still exist; still fit behind QMF contracts. No new version claimed. |
| click (QMB CLI) | not restated | Brownfield `click==8.4.2`. Not a node/QMA dependency (AD-17/AD-21). |
| Caliper | AD-19 later adapter, not a CLI assumption | Real: github.com/edonadei/caliper; `pipx install caliper-eval`; backends include Claude Code / Codex / Pi / Hermes. Correctly deferred; not pinned. |

### Named donor technologies — still exist, still fit the refuse/borrow split

Fetched / confirmed 2026-09-18:

| Named in spine | Exists? | Fit of the sitting’s use |
| --- | --- | --- |
| Hermes Agent | Yes — NousResearch/hermes-agent; docs v2026.9.14; Plugin Catalog launched 2026-09-16 | Mental model: schema/handler split, config vs state. AD-18 fail-closed missing deps still diverges from Hermes warning-and-continue (discovery/missing-env failures remain WARNING, not hard enable errors). Catalog does not revive DEC-0361 marketplace. |
| n8n | Yes — n8n@**2.39.8** stable (2026-09-18); fair-code; node descriptors, connections, subworkflows | Mental model for Board vs Template vs run. Not imported. |
| OpenBB | Yes — docs.openbb.co widgets.json / apps.json + shared params still the Workspace contract (docs updated 2026-08-24) | Provider + mini-app declarations only. Do not adopt OpenBB runtime. |
| QuantConnect / LEAN | Yes — QuantConnect/Lean build **18106** (2026-09-17); Paper brokerage still a distinct live-data simulation | Mental model only. DEC-0085: no donor engine. |
| Caliper | Yes — edonadei/caliper skill-eval harness | Later QMA adapter question, not a product CLI. |

---

## What I verified on brownfield (`integration@270e992`)

### SHA, runtime, layout

| Spine claim | Evidence | Result |
| --- | --- | --- |
| Inspect SHA `integration@270e992` | `git rev-parse HEAD` → `270e992995c2378ca63cf6343254ef8140a8c97e`; subject `story 51.s7: load collapse test helpers without SKY-D222` | Match |
| CPython 3.14.6 observed | `python --version` → 3.14.6; `.python-version` → `3.14` | Match |
| `qml/src/qml/research/` exists @ 270e992 | `stage0.py`, vocab, projection, collapse present | Match Structural Seed (supersedes 8510c03 “Stage 0 absent”) |
| `qml/src/qml/host/research_store.py` | Present | Match AD-16 / seed |
| `qma.daemon.taskgraph` | `compiler.py`, `dispatcher.py`, `execution.py`, `records.py`, `state.py` | Match seed |
| `published_contributions()` | `qma.daemon.plugins.loader.PluginLoader.published_contributions` | Match AD-2 contribution rail |

### Pins this sitting restates

| Spine claim | Evidence | Result |
| --- | --- | --- |
| `optuna==4.9.0` in qmb | `qmb/pyproject.toml`; `uv.lock` specifier `==4.9.0`; `DEPENDENCIES.md` | Match |
| uv workspace + lockfile | worktree + workspace `docs/architecture/stack.md` | Match (inherited; versions not restated) |
| QMF stores Parquet/DuckDB/SQLite/JSONL | DEC-0117; `duckdb==1.5.5` in `qmf-data` | Match |
| QMA sqlite single writer | inherited AD-6; `CLOSED_PROJECTIONS` includes `task_graph_state` and `session_records` | Match as named store list; product-session **tables** are the proposed amendment (no `product_session` symbol in tree) |

### Graph Template DAG hole (AD-6) — inspected, not papered over

Live `validate_graph_template_topology` (`qma/daemon/taskgraph/execution.py:172`) only refuses **pairwise reverse-edges**:

```python
if (dst, src) in forward:
    return policy_rejection(..., "back-edges are rejected ...")
forward.add((src, dst))
```

`A→B→C→A` is admitted. A first `A→A` self-loop is also admitted (`(A,A)` is not already in `forward`). Plugin-loader DFS (`topological_plugin_order`, `loader.py:184`) **does** refuse cycles on plugin `requires`. AD-6 “reuse the plugin-loader DFS” / “pairwise reverse-edge checks are insufficient” is an honest amendment of an inspected hole, not a claim that DAG law already ships.

### Task Graph edges dropped (AD-4 / AD-7) — inspected

`MissionCompiler._expand_template` validates template edges then constructs `TaskGraph(id=..., mission_id=..., nodes=..., tasks=..., graph_template_ref=..., state=...)`. `TaskGraph` (`records.py:319`) has **no `edges` field**. Dispatcher has no successor walk over stored edges. AD-4 “today edges are dropped — that is a hole this AD binds closed” matches `270e992`. `task_graph_state` is already in the closed projection list (`stores.py:92`); persistence of edges is the named connect, not a new store.

### Discovery rails (AD-2)

| Spine claim | Evidence | Result |
| --- | --- | --- |
| `KnowledgeHit` / `ArtifactHit` | `qma.wire.federated_discovery` classes exist | Match |
| Query-hit tags `saved-view` \| `analysis.published` | `ARTIFACT_QUERY_HIT_TAGS`; hyphen `saved-view` (not underscore) | Match live tokens |
| Hypothesis refused on facade | KnowledgeHit aliases refuse `hypothesis` / `entry_hypothesis` | Match |
| `ContributionHit` | **No** `ContributionHit` type. Live surface is `published_contributions()` → `PublishedContribution` / `ContributionDecl` | **Proposed DTO** (STACK-AND-EVALUATION already lists it as a proposed change). Not a vanished library. |

### Other brownfield joints the spine names as connect/amend, not as current behaviour

| Spine claim | Evidence | Result |
| --- | --- | --- |
| QMA never `import qmb` | `qma.core.barriers.dependencies`; tests assert the string is refused | Match AD-1 / inherited DEC-0347 |
| No `ui_view` plugin point until GAP-0081 | contracts + component docs: `ui_view` excluded; `UiContributionDeferred` | Match AD-17 |
| `desk_slug=pm` unchanged | docs + Role “Product Manager”; pack `pm-coordination` | Match AD-22 (label-only) |
| product sessions absent | no `product_session` symbol | Match AD-8 as overlay to add |
| sensing-only without Book | `qmn` roster `sensing_only` legal compiled state; smuggled Book/BMS refused | Match AD-11 |
| Hypothesis persistence is `research_root` blobs | `qml.host.research_store` | Match AD-16 |

Class/test existence ≠ e2e — spine Consistency Conventions already stamp DEC-0286. Currency lens does not treat that as a defect.

---

## Findings

### L-1 — Optuna Stack row names the lockfile pin and omits that 5.0.0 GA exists *(low / CONNECT-style note)*

**Where:** Stack table “Optuna \| `optuna==4.9.0` in qmb — TPE search only”.

The sitting correctly **does not bump**. Brownfield is 4.9.0. Upstream **5.0.0** (PyPI 2026-09-07; 3.14 classifier; MIT) is the first default-sampler change since Optuna 1.5 (multivariate TPE + constant liar) — exactly the DEC-0168 contract-versioning event. The 2026-09-14 workbench currency review already required naming both facts. This sitting names the pin (good) and drops the “5.0.0 exists, not adopted” clause.

**Fix (editor, optional):** one parenthetical: current upstream 5.0.0 (2026-09-07); this sitting does not adopt it.

### L-2 — CPython Stack row does not date 3.15 *(low)*

3.15.0rc2 is real (2026-09-01); final expected 2026-10-01 (~13 days). “Not adopted” is implicit in “3.14 … not upgraded here” and is the right call. Undated, a later reader may think 3.15 does not exist. Restore a memlog-style clause if the editor wants CONNECT parity with 2026-09-14.

### L-3 — Inherited `qmb_sampler_pin` notes at 270e992 still call 5.0.0rc1 a pre-release *(low / docs debt; not this spine’s prose)*

Worktree `docs/registry/variables.yaml` `qmb_sampler_pin` notes: “5.0.0rc1 is a pre-release, not pinned; web-verified 2026-08-20.” False since 2026-09-07. Workspace `docs/architecture/stack.md` (`verified: 2026-09-16`) already records “Upstream Optuna 5.0.0 exists (2026-09-07); … `optuna==4.9.0` stays.” Fold remaining worktree- lag into documentation-factory reconcile. This spine does not repeat the stale sentence.

---

## What is clean (no finding)

- CPython 3.14.7 as current stable (released 2026-08-05; still tip on 2026-09-18): independently reproduced; 3.15 not adopted; observed 3.14.6 at 270e992 matches.
- json-render / `@json-render/core@0.20.0` (released 2026-08-18): still latest on 2026-09-18; catalog-constrained generative UI; fit as unpinned presentation candidate; not a Python dependency.
- MCP Apps SEP-1865 / `ui://` / stable **2026-01-26**: confirmed on official ext-apps spec table and SEP Final page; fit as presentation-only. Distinct from QMA’s MCP protocol revision 2026-07-28 (still latest).
- mutmut: live; `os.fork` / Windows=WSL / `mutmut apply` writes mutants — all in current README + PyPI 3.8.0 description. Correctly not a product dep.
- `optuna==4.9.0` lockfile pin matches `qmb/pyproject.toml` / `uv.lock` / `DEPENDENCIES.md`.
- DuckDB 1.5.5 still latest stable; 1.6/2.0 remain `.dev`.
- n8n, OpenBB, LEAN, Hermes still exist; refuse/borrow split matches current vendor docs. Hermes Plugin Catalog (2026-09-16) does not reopen DEC-0361.
- Caliper (edonadei/caliper) exists; AD-19 correctly defers it as a later adapter, not a CLI pin.
- Graph Template pairwise-only topology and TaskGraph-without-edges are **honest holes** AD-6 / AD-4 / AD-7 bind closed.
- `qml.research` and `research_store.py` exist at 270e992 as the Structural Seed claims.
- `saved-view` (hyphen) matches live federated tokens (the 2026-09-16 underscore mismatch is not repeated).
- “Inherited pins stand. This sitting adds **no** required runtime.” is the correct currency posture for a brownfield construction-kit sitting.
- No invented library, protocol, or vanished vendor asserted from training data alone.

---

## Method note

Checks were run against live primary sources and the named brownfield tree on 2026-09-18. Sitting companions (`STACK-AND-EVALUATION.md`, `RECON-RETURN.md`) were used as a map, then re-verified (not trusted as sole proof). Spine was not edited.

Mandated web questions:

| Named tech | Still exists? | Version / date | Fits assigned role? |
| --- | --- | --- | --- |
| json-render | Yes | `@json-render/core` **0.20.0** (2026-08-18; still latest 2026-09-18) | Unpinned catalog UI; not identity/runtime |
| MCP Apps | Yes | SEP-1865 stable **2026-01-26** | Tool-linked HTML in supporting chats |
| mutmut | Yes | PyPI **3.8.0**; fork/WSL/`apply` still documented | Optional test-strength; not a product dep |
| CPython 3.14 | Yes | **3.14.7** current stable; **3.14.6** on this host / 270e992 | Inherited runtime; not upgraded |
| optuna 4.9.0 | Yes (pin); upstream **5.0.0** | Lockfile **==4.9.0**; 5.0.0 not adopted | TPE search adapter only |

Brownfield pins vs `270e992`: CPython 3.14 line, `optuna==4.9.0`, `duckdb==1.5.5`, `click==8.4.2`, qml.research + research_store present, taskgraph edge/DAG holes present as named.

---

## Review path

C:/Users/Mubarak/Desktop/QMX/_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-18/reviews/review-currency.md
