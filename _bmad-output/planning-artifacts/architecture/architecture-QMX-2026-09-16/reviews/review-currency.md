# Review — Currency / Reality lens

**Spine:** `_bmad-output/planning-artifacts/architecture/architecture-QMX-2026-09-16/ARCHITECTURE-SPINE.md` (draft 2026-09-16, AD-1..AD-21)
**Companions consulted as a map, then re-checked:** `QML-EXPANSION.md`, `inputs/evidence-summary.md`
**Lens:** every committed technology and factual claim must be web-current or brownfield-checked, not asserted from training memory. This sitting is brownfield QMX + seed import, not a new starter.
**Inspected trees:**
- `.worktrees/integration-inspect` @ `8510c032496bb870824ecc5c4f807e8a4e4f167e` (`git rev-parse HEAD` match; spine cites `integration@8510c03`)
- Seed: `C:/Users/Mubarak/Desktop/Stats` (read-only; not edited)
- Inherited pin source: `docs/architecture/stack.md` (workspace, `verified: 2026-09-14`) plus inspect-worktree `docs/architecture/stack.md`
**Reviewer gate date of checks:** 2026-09-16

Web (primary sources, this sitting): python.org downloads + 3.14.7 release page; docs.python.org “What’s New” last-updated 2026-09-16; json-render.dev + npm `@json-render/core` + github.com/vercel-labs/json-render; modelcontextprotocol.io SEP-1865 + github.com/modelcontextprotocol/ext-apps `specification/2026-01-26`; PyPI/libraries.io optuna 5.0.0; GitHub/crates.io uv 0.12.15.

Brownfield (this sitting): `qml/src/qml/conformance/registration.py` (`graduate_to_governed`), `qml/src/qml/generation/gaps.py`, `qmb/src/qmb/registryread/library.py`, `qma-daemon/.../knowledge/plain_file.py`, `qmx-agents/plugins/research-corpus/daemon/plugin.py`, `qma-core` StrategyHandle `origin`, CT-33/CT-34/CT-44 yaml `wiring_status`.

---

## Verdict

**PASS.**

Named technologies still exist and still fit the roles the spine assigns them. Version claims this sitting restates (CPython 3.14 / 3.14.7) are independently current on 2026-09-16. Presentation candidates (json-render, MCP Apps SEP-1865) are real and correctly left unpinned. The three brownfield facts this sitting is most likely to get wrong are **honest against `integration@8510c03`**:

1. **`defined-unwired` / “no code exists” on CT-44 / CT-33 / CT-34 is stale.** Spine Consistency Conventions already stamp `source-inspected`. Code and tests exist. e2e remains unproven.
2. **research-corpus is still the two-file in-memory stub; Stats is not bound.** Spine AD-8 / AD-14 / Structural Seed name the replace, they do not claim the bind already shipped.
3. **`qml.conformance.registration.graduate_to_governed` exists** at `qml/src/qml/conformance/registration.py:326`. Stage 0 types do **not** (`qml/src/qml/research/` is absent). Spine Conventions already say both.

This sitting adds **no new runtime pin**. Optuna is not restated in the Stack table (correct). Inherited tooling patch drift is informational only.

Two brownfield **API joints** were not fully reality-checked when AD-7 / AD-21 were tightened after the adversarial pass: live `StrategyHandle` `origin` is the frozen string `"qma"`, and live `originating_research_ref` is a `Fingerprint` (`fp1:sha256:<hex>`). Those are H-1 / H-2 below. They do not invent a vanished library and they do not make the three mandated brownfield stamps false.

---

## What I verified on the web (primary sources)

### CPython — Stack row: `3.14 (inherited; 3.14.7 current stable as of 2026-08-05)`

- **Latest stable = 3.14.7, released 2026-08-05.** Confirmed: python.org “Latest: Python 3.14.7”; python.org/downloads/release/python-3147/; docs.python.org “What’s New” last-updated **2026-09-16** still lists 3.14.7 as the 3.14 tip. No 3.14.8 today.
- **3.15 is not stable.** python.org news 2026-09-01: “Python 3.15.0 candidate 2 is here!” Spine does not claim 3.15.
- **Brownfield:** inspect members declare `requires-python = ">=3.14,<3.15"`; `qmx-agents/uv.lock` is `requires-python = "==3.14.*"`. Workspace `docs/architecture/stack.md` (verified 2026-09-14) and inspect `stack.md` both pin CPython 3.14 / 3.14.7.
- **Fit:** inherited DEC-0099 pin stands. Spine dating (“as of 2026-08-05”) is the 3.14.7 release date and remains the current tip on review day.

### json-render — Stack / AD-12: presentation candidate, not pinned (json-render.dev)

- **Exists:** https://json-render.dev live; catalog-constrained generative UI (components/actions; AI emits JSON inside the catalog).
- **Upstream:** github.com/vercel-labs/json-render. npm `@json-render/core` **0.20.0** (Apache-2.0, homepage json-render.dev). Not a PyPI package — correct that this sitting does not invent a Python pin.
- **Fit:** AD-12 “render DTOs… not identity, persistence, or authority” matches the catalog-guardrail model. Spine correctly leaves it unpinned and outside the daemon dependency set. No version claim to go stale.

### MCP Apps — Stack / AD-12: `SEP-1865 stable 2026-01-26`

- **Exists and dated:** github.com/modelcontextprotocol/ext-apps Specification table: **`2026-01-26` | Stable** (`specification/2026-01-26/apps.mdx`; Status: Stable (2026-01-26)). SEP-1865 on modelcontextprotocol.io is Status **Final**; `ui://` resources + tool metadata association match AD-12 wording.
- **Blog:** MCP Apps announced official / production-ready on 2026-01-26 (blog.modelcontextprotocol.io/posts/2026-01-26-mcp-apps/).
- **Do not conflate with the QMA MCP adapter pin.** Inherited QMA stack (`docs/architecture/stack.md` QMA application stack) pins **Model Context Protocol revision 2026-07-28** as the ToolAdapter surface. That is the core protocol revision, not MCP Apps. Spine AD-12 names the Apps extension only, as a presentation candidate, not a daemon dependency. Fit is correct.

### Optuna — not named in this spine’s Stack; checked as inherited brownfield pin

- **Brownfield pin:** `qmb/pyproject.toml` and `DEPENDENCIES.md` keep **`optuna==4.9.0`**. Workspace `stack.md` restates 4.9.0 exact under DEC-0168 (`qmb_sampler_pin`).
- **Current upstream:** Optuna **5.0.0** published 2026-09-07 (libraries.io / optuna docs / PFN release). 4.9.0 (2026-06-01) still published.
- **Posture:** this spine correctly says “Inherited pins stand. This sitting adds no runtime framework” and does **not** restate Optuna. Non-bump remains correct under DEC-0168 (optuna major = contract-versioning event). See L-1.

### uv — Stack: “uv workspace + lockfile | inherited”

- Spine does not restate a uv version. Ratified `stack.md` still names **0.12.5** (QMF) / QMA stack **0.12.7**. Current uv on 2026-09-16 is **0.12.15** (GitHub latest, crates.io, docs.astral.sh; released 2026-09-15). Same 0.12.x line. Informational only (L-2).

---

## What I verified on brownfield (`integration@8510c03`)

### SHA and layout

| Spine claim | Evidence | Result |
| --- | --- | --- |
| Inspect SHA `integration@8510c03…167e` | `git rev-parse HEAD` → `8510c032496bb870824ecc5c4f807e8a4e4f167e` | Match |
| Structural seed paths | `qmx-agents/plugins/research-corpus/daemon/plugin.py`; `qma-daemon/.../knowledge/plain_file.py`; `qmb/.../registryread/library.py`; `qml/.../conformance/registration.py`; `qml/.../generation/gaps.py`; `qma-ui-contract/STUB.md` | Match |

### Knowledge adapter: stub vs Stats bind

| Spine claim | Evidence | Result |
| --- | --- | --- |
| `source_id` singleton `strats` | `plugins/research-corpus/daemon/plugin.py` `_SOURCE_ID = "strats"` | Match |
| kind `plain_file_library` | same file `kind: str = "plain_file_library"` | Match |
| Six confidence dims (exact spellings) | plugin `_DIMS` and `DEFAULT_PLAIN_FILE_CONFIDENCE_DIMENSIONS` identical to AD-3 list | Match |
| Integration plugin still in-memory stub | `StratsCorpus` with two hardcoded files `notes/liquidity.md`, `notes/session.md`; `activate()` registers `StratsCorpus()`, **not** `PlainFileLibrarySource` | Match (gap named, not papered over) |
| `PlainFileLibrarySource` exists | `qma-daemon/.../knowledge/plain_file.py`; skips path parts starting with `.`; currently hashes **all other** regular files (no AD-4 include/exclude yet) | Match; AD-4 correctly framed as adapter config to extend |
| Cite-copy / StaleSnapshot / hybrid refuse | `KnowledgeService.cite` copies bytes; retrieve against uncopied snapshot refuses; `refuse_hybrid_knowledge_indexing` is GAP-0073 | Match AD-11 / AD-9 hybrid deferral |
| `unscored` default (AD-3) | **No** `unscored` token in qma-agents. `cite` requires the caller to pass a six-key `evidence_confidence` map. Tests use `dict.fromkeys(_DIMS, 0.5)` | **Proposed, not current** (L-3) |

Pointing `PlainFileLibrarySource` at Stats **today** would hash `backend/strats.sqlite` and `backend/*.py`. AD-4 and the Structural Seed (“extend snapshot include/exclude”) correctly treat that as first-slice adapter work, not as a claim that the filter already ships.

### QMB Library refuse list

| Spine claim | Evidence | Result |
| --- | --- | --- |
| `register_library_kind("strats")` refuses | `NOT_LIBRARY_KIND_NAMES` includes `"strats"`; dedicated refuse branch; `STRATS_CORPUS = "KnowledgeSource"` | Match |
| Artifact roster is existing `fp1` kinds | `LIBRARY_KINDS` = bot-definition, confluence, strategy-family, book-definition, bms-definition, book-binding, split-manifest, source-observation, performance-result, experiment-spec (coordinated-only) | Match AD-1 |
| Saved-view / analysis.published are query hits, not registry kinds | `search_library("saved-view")` / `"analysis.published"` aliases; `is_registry_kind is False`; kinds still refused on `register_library_kind` | Match intent; **token** is `saved-view` (hyphen), not AD-9’s `saved_view` (L-4) |

### `graduate_to_governed` — exists as the spine claims

| Spine claim | Evidence | Result |
| --- | --- | --- |
| `qml.conformance.registration.graduate_to_governed` present | `qml/src/qml/conformance/registration.py:326`; exported from `qml.conformance` and `qml` | **Exists** |
| Both QL-8 layers required | Function calls `gate_registration(layer1=..., layer2=...)`; either failure refuses | Match AD-17 |
| Distinct `originating_research_ref`; self-edge refused | `if research.value.value == candidate.value.fingerprint.value: return invalid(...)` | Match AD-17 “Code on `integration@8510c03` already refuses a self-edge” |
| Host stamps `promoted-from` CT-07 edge | Returns fingerprintable `GraduationEdge`; docstring: host composition root stamps CT-07 | Match |
| Ungoverned Python tunnel without graduating | `admit_ungoverned_tunnel`; `cite_ungoverned_bot` refuses governed cites | Match AD-7 don’t-box-in |
| `spawn_governed` is **not** graduation | `qmb.orchestrator.spawn.spawn_governed` starts isolated runs; `qmb.workbench.graduate_ungoverned_via_spawn` refuses (“L33 graduation is a separate two-artifact registration act”) | Match AD-7 / AD-17 Prevents |
| Stage 0 types exist | **No** `qml/src/qml/research/`; no `qml.research` imports in inspect tree | Match Conventions: “Stage 0 types do not” |
| Homonym | `qmf.structure.research.graduate_to_governed` is **CT-17 family** graduation (`originating_experiment_ref`), not QML bot graduation | Named correctly in the spine (qml path). Implementers must not import the structure homonym (L-5) |
| `originating_research_ref` encoding | Live type is `Fingerprint`; `_coerce_fingerprint` requires `fp1:sha256:<hex>` | AD-21 “not a qmf-registry `fp1`” must still use this encoding, or the function must change (H-2) |

### Docs-vs-code: `defined-unwired`

Contract YAML on inspect still says `wiring_status: defined-unwired` with comments “no code exists”:

- `docs/contracts/ct-44-qma-knowledge-source.yaml:9`
- `docs/contracts/ct-33-bot-definition.yaml:9`
- `docs/contracts/ct-34-confluence.yaml:9`

That is **false against this SHA**. Counter-evidence:

- CT-44: `qma.core.ports.knowledge` (`KnowledgeSource`, `CorpusSnapshot`, `Citation`, `Provenance`, six-dim parse); `PlainFileLibrarySource`; `KnowledgeService`; `test_knowledge_source.py` / `test_knowledge_service.py`.
- CT-33 / CT-34: `qml.declaration.bot`, `qml.declaration.confluence`, QL-8 `gate_registration` / `graduate_to_governed`, tests under `qml/tests/test_gate_registration.py` and qa epic_12.

Spine Consistency Conventions already stamp this stale and require `source-inspected`. **The spine is current; the contract YAML is not.** e2e (live Stats bind, federated UI, graduation of a real hypothesis) remains unproven — DEC-0286 / AD-14 correctly refuse class-existence as e2e.

`qma-ui-contract` is still `STUB.md` (GAP-0081). Match AD-12 / Deferred.

GAP-0085 / GAP-0063: `qml.generation.gaps` still refuses `mint_mechanism_vocabulary` and a decided generator algorithm. Match AD-16 / Deferred.

FEAT-0045 / FEAT-0046 remain `status: planned` in `docs/knowledge/traceability.md` while knowledge/plugin code exists. That is inherited docs lag, not a spine invention.

### AD-7 origin vs live StrategyHandle

Live code (`qma.core.vocabulary.handles.QMA_OWNED_CANDIDATE_ORIGIN = "qma"`; `StrategyCandidate.try_create` **policy-rejects** any other `origin`):

```python
if origin != QMA_OWNED_CANDIDATE_ORIGIN:
    return _policy("origin", "StrategyHandle candidates carry a QMA-owned origin ...")
```

AD-7 (after adversarial C-2) now says origin on a `dev`-zone candidate / StrategyHandle **is** a QMA-owned non-`fp1` field `{ source_ref, snapshot_ref, locator }`. That triple **cannot be stored in the live `origin` field**. Implementing AD-7 as written against this SHA fails `StrategyCandidate.try_create`. See H-1.

---

## What I verified on Stats (`C:/Users/Mubarak/Desktop/Stats`)

| Spine / AD claim | Evidence | Result |
| --- | --- | --- |
| Canonical tree is Stats; `Desktop/strats` debris | Both paths exist; Stats has the full library tree; `Desktop/strats` is the debris path named in evidence-summary | Match AD-2 |
| Include set (AD-4) | Present: `README.md`, `STRATS-BUILD-STATE.md`, `IDEA.md`, `schema/`, `dictionary/`, `strategies/`, `sources/`, `knowledge/`, `lineage/`, `catalog/` | Match |
| Exclude candidates (AD-4) | Present: `.hermes/`, `.obsidian/`, `backend/strats.sqlite`, `backend/*.py` | Match (why AD-4 must configure exclude) |
| SQLite derived, disposable | BUILD-STATE: sqlite is a derived index of 239 primitives | Match |
| 239 dictionary / 229 unique / collisions keepers | BUILD-STATE + `catalog/dictionary-collisions.md`; 9 colliding slugs; `liquidity-sweep` ×3 | Match AD-5 / AD-11 |
| `STRAT-000001` + `entry_hypothesis` + F unresolved | `strategies/STRAT-000001-asian-high-london-reversal/identity.md` class `entry_hypothesis`; `logic/graph.yaml` F slots `unresolved`; “Do not invent exits” | Match AD-6 / AD-14 |
| `swing-high` dictionary entry | `dictionary/market-structure-and-location/locations-and-structure.md` `## swing-high — Swing High` | Match AD-14 vocab helper |
| Population paused | BUILD-STATE Future / pause-before-populate | Match Deferred |
| Do not rewrite the 239; 12→~25 deferred | BUILD-STATE Dictionary section | Match Deferred |
| Prop-firm overlay, not a third library | `knowledge/prop-firms/` exists | Match AD-2 |
| QMA AD-19 last sentence “empty corpus / IDEA.md only” | Parent QMA spine AD-19 still says the STRATS root “is empty today (its root holds only `IDEA.md`…)” checked 2026-08-28 | **Factually stale**; spine Open questions correctly route a docs refresh, not a law change |

---

## Findings

### H-1 — AD-7 `origin` triple was not reality-checked against live `StrategyCandidate.origin` *(high / brownfield API joint)*

**Claim:** Origin on a `dev`-zone candidate / StrategyHandle is a QMA-owned non-`fp1` field `{ source_ref, snapshot_ref, locator }`.

**Live (`integration@8510c03`):** `origin` is the frozen string `"qma"`. `StrategyCandidate.try_create` refuses anything else. There is no citation-triple field on the candidate record.

**Why it matters:** a factory story that “just fills origin” per AD-7 will fail the existing constructor. The adversarial C-2 tightening named a single home without inspecting the live type. Knowledge cite metadata needs a **new** optional non-`fp1` field (or a sibling), not a reshape of `origin: "qma"` which is “who minted this candidate.”

**Fix (spine, not code):** one sentence: live `origin` stays `"qma"`; the citation triple is a distinct optional field (name it; do not overload `origin`) that QMA copies only if the host supplied it. Until that sentence lands, treat AD-7 origin as **proposal-to-extend**, not as current StrategyHandle shape.

### H-2 — `graduate_to_governed` exists, but `originating_research_ref` is `Fingerprint` (`fp1:sha256:<hex>`) *(high / identity encoding)*

**Claim:** AD-17 binds the existing function; AD-21 says hypothesis identity is a QML-ladder `research_ref`, **not** a qmf-registry `fp1`.

**Live:** `_coerce_fingerprint(..., "originating_research_ref")` requires `fp1:sha256:<hex>`. `Graduation.originating_research_ref: Fingerprint`. Error text: “a Bot citation or research artifact is referenced by fp1:sha256:<hex>”.

**Why it matters:** Stage 0 types are new (honestly absent). Graduation of those types cannot invent a second hash dialect. Either `research_ref` is the same `Fingerprint` encoding over QML-ladder content **without** registering a registry kind (compatible with the live function), or the function’s signature is an authorized change. “Not a registry `fp1`” ≠ “not a `Fingerprint`.”

**Fix:** AD-21 one clause: `research_ref` is `qml.core`/`qmf.core.fingerprint` over `{semantic content, format version}`; it is never a registry kind and never the Bot `fp1`; it **is** legal input to existing `graduate_to_governed`. Homonym: do not call `qmf.structure.research.graduate_to_governed` from QML stories.

### L-1 — Inherited Optuna pin 4.9.0 vs upstream 5.0.0 GA *(low / docs debt; not this spine’s Stack)*

This spine does **not** name Optuna. Brownfield remains `optuna==4.9.0`; upstream is **5.0.0** (2026-09-07). Non-adoption is correct (DEC-0168). Fold into documentation-factory reconcile if any ratified note still calls 5.0.0rc1 “a pre-release.”

### L-2 — Inherited uv patch pin (0.12.5 / 0.12.7) vs current 0.12.15 *(low / informational)*

Spine inherits “uv workspace + lockfile” without restating a version. Tooling has moved on the same minor line. No new pin required from this sitting.

### L-3 — AD-3 `unscored` default is proposal, not current adapter behaviour *(low / implementation note)*

No `unscored` token in inspect qma code. `cite` requires a caller-supplied six-key map. Tests currently stuff `0.5` floats. AD-3 correctly forbids QMA-computed scalars and Memory `admission_confidence`; it should not be read as “the adapter already emits `unscored`.” First-slice cite of Stats locators must implement that default (or refuse cite until the caller supplies corpus-authored values).

### L-4 — AD-9 closed tags `saved_view` \| `analysis.published` vs live tokens `saved-view` / `analysis.published` *(low / token)*

Live QMB search kind is hyphen `saved-view`; `analysis.published` is already an alias to `analysis-publication` query hits. Underscore `saved_view` is not the live kind token. Freeze the DTO on the live tokens or declare a wire alias table. Not a vanished feature.

### L-5 — CT-17 homonym `graduate_to_governed` *(low / naming hazard)*

`qmf.structure.research.graduate_to_governed` is a different function (structure family → governed evidence, `originating_experiment_ref`). Spine’s path `qml.conformance.registration.graduate_to_governed` is the correct one and **does exist**. Record so epics do not import the wrong symbol.

### L-6 — AD-4 include/exclude is proposal-correct; code today is all-files-minus-dot *(low / implementation note)*

Already named in the spine Structural Seed. Currency lens records the gap so AD-4 is not mistaken for current behaviour.

---

## What is clean (no finding)

- CPython 3.14.7 as current stable (released 2026-08-05; still tip on 2026-09-16): independently reproduced; 3.15 not adopted; inspect `requires-python` matches.
- `source_id=strats` + six confidence dimension spellings: exact match to integration plugin and `PlainFileLibrarySource` defaults.
- json-render.dev / `@json-render/core@0.20.0`: live catalog-constrained generative UI; fit as unpinned presentation candidate; not a Python dependency.
- MCP Apps SEP-1865 / `ui://` / stable **2026-01-26**: confirmed on official ext-apps spec table and SEP Final page; fit as presentation-only. Distinct from QMA’s MCP protocol revision 2026-07-28 adapter pin.
- Stats authority path, debris `Desktop/strats`, 239/229/collisions, `STRAT-000001` class, `swing-high`, population pause, `knowledge/prop-firms` overlay: filesystem verified.
- QMB refuse of `strats` as Library kind; two-rail identity split still matches code.
- `graduate_to_governed` **exists**; self-edge refuse exists; `spawn_governed` is not graduation (`workbench.graduate_ungoverned_via_spawn` refuses).
- Stage 0 module **does not exist**; spine says so.
- research-corpus is still the two-file stub; spine says replace it with `PlainFileLibrarySource(root_path=…)`.
- CT-44/33/34 `defined-unwired` YAML is stale; spine Consistency Conventions already stamp `source-inspected`.
- GAP-0085 still refused in `qml.generation.gaps`; GAP-0081 still a stub directory.
- “Inherited pins stand; this sitting adds no runtime framework” is the correct currency posture for a brownfield mill-absorption sitting.
- No invented library, protocol, or Stats schema field asserted from training data alone.

---

## Method note

Checks were run against live primary sources and the named brownfield trees on 2026-09-16. Sitting input `inputs/evidence-summary.md` was used as a map, then re-verified (not trusted as sole proof). Stats was read, not edited. Spine was not edited.

Mandated brownfield questions:

| Question | Answer |
| --- | --- |
| Stale `defined-unwired`? | **Yes in contract YAML; spine already flags it.** Code exists for CT-44/33/34. |
| Stub vs Stats bind? | **Stub still live.** `StratsCorpus` two in-memory notes; `PlainFileLibrarySource` exists unwired. Spine AD-8/AD-14 name the replace. |
| Does `graduate_to_governed` exist as claimed? | **Yes** at `qml/src/qml/conformance/registration.py:326`. Homonym in `qmf.structure.research` is a different function. Stage 0 types do not exist. |
