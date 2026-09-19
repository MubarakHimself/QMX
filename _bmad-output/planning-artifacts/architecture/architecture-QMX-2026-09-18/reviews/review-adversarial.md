---
review: adversary
target: ARCHITECTURE-SPINE.md (QMX Workflows construction kit, 2026-09-18)
companions: [CONTRACTS.md, COPILOT-AND-APPS.md, CONFLICT-REGISTER.md, JOURNEYS.md, IMPLEMENTATION-SEQUENCE.md, UI-HOST.md, STACK-AND-EVALUATION.md, REQUIREMENTS-ADDENDUM.md]
parents_read: [constitution L17/L36, Workbench AD-3/AD-5/AD-8/AD-9/AD-16, QMA AD-6/AD-7/AD-12/AD-13/AD-14/AD-16/AD-21/AD-22, mill/wire DEC-0389 federated two-class freeze, QMB ResolvedRunConfig @ 270e992]
inspected: [qma.core.ontology.Session/Profile, qma.wire.federated_discovery (FEDERATED_HIT_CLASSES = knowledge|artifact), PublishedContribution, GraphTemplate/TaskGraph/TaskGraphStore, qmb.config.compiler.ResolvedRunConfig]
date: 2026-09-18
lens: 'Attack the spine as an adversary: construct two units one level down that each obey every AD to the letter yet still build incompatibly — clashing shared-data shapes, two owners of one entity, conflicting state-mutation paths. Every pair is a hole. Also check: dummy Book still possible; product session vs QMA Session mix-up; ContributionHit treated as fp1; Board treated as Mission; json-render as authority.'
---

# Adversary review — Workflows construction-kit spine (2026-09-18)

## Method

For each local AD (especially AD-2, AD-3, AD-4, AD-5, AD-7, AD-8, AD-9, AD-11, AD-12, AD-16, AD-17) and the inherited joints this sitting binds, build **two conforming units one level down** — factory epics Slice 0 / Slice 1 would actually spawn (federated DTO, operation descriptors, product-session sqlite, DAG validator, Task Graph edges, Book/non-Book compile, copilot grants, UI contribution DTOs) — and ask whether both can obey every written Rule plus every inherited parent Rule and still be unable to assemble.

Only pairs where **both readings are literal** are reported. `[PROPOSAL]` parent amendments and Deferred rows count when v1 must already pick a shape. Companions (`CONTRACTS.md` especially) count when they are the only payload a factory lane would copy. Findings end with paste-ready Rule text.

Parent spines bind read-only. A local AD that overloads a parent field (`Session`, `Profile`, `FEDERATED_HIT_CLASSES`, `ResolvedRunConfig.book_fp1`, `scope_path`) without a typed discriminator **and** a named parent amendment is a hole, not a license. Brownfield at `integration@270e992` is in-scope: the spine cites it.

Named checks demanded by this pass: dummy Book still possible; product session vs QMA Session mix-up; ContributionHit treated as fp1; Board treated as Mission; json-render as authority. Each is a Critical below.

## Verdict

**Return for amendment — do not freeze Slice 0 (ContributionHit concatenate, product-session sqlite, operation descriptors, Task Graph edges).** Intent is tight: no sixth COMP, Board ≠ Mission, Session ≠ product-session, ContributionHit ≠ fp1, dummy Book forbidden, json-render not identity. The AD set fails at the joints those epics would implement.

Five load-bearing joints let two conforming units ship incompatible products: (1) product-session is “distinct” from QMA `Session` in prose and aliased onto it in `CONTRACTS.md` / `scope_path` / `Profile`; (2) ContributionHit is a third federated `hit_class` against a frozen two-class DTO, with no durable pin except content-fp1; (3) dummy Book remains the only way to call the live compiler, because “complete CT-22” is not distinguished from a no-op wrapper; (4) Board layout has no home, so it lands in `product_session` and compiles as a Mission; (5) json-render / MCP Apps are the only v1 form/invoke surface the UI contracts name, so they become schema and authorization. High follow-ons: mapping declared twice (descriptor vs edge), Task Graph edge shape unset, grants in four places, unnamed stores (change-request, instance, recipe, private notes).

Slice 0 as written **is** the work that forks. DAG-validator wording is the exception (the Rule is closed; only code is behind).

| Tier | Count |
| --- | --- |
| Critical | 5 |
| High | 7 |
| Medium | 4 |

Pairs that could **not** be made to diverge (closures that hold): minting `COMP-WF` / a sixth application; QMA `import qmb`; `hit_class: strats` / hypothesis as Library kind; Skills compiling to Missions; Graph Template `artifact_kind` swapped for Task Graph; live/node-paper without Book (refused until L36 amendment); marketplace / HMR / execution tool; mutmut as a product dependency; json-render imported as a domain executor (the hole is authority, not an n8n-style runtime). Those are not the problem. The problem is the **new identity, owner, and mutation surfaces** AD-2/AD-3/AD-7/AD-8/AD-11/AD-16/AD-17 introduce without a single home.

---

## CRITICAL

### C-1 — AD-8 × AD-16 × QMA AD-6/AD-7/AD-14: product session vs QMA Session mix-up (named check)

**The rules as written.**

- Local AD-8: two **product-session profiles** `authoring` | `app-use` are “host/wire records **distinct** from QMA `Session` (execution container)”. Fields include session id, profile, principal, context revision, app instance, granted ops, selected object refs, dataset/run/attempt refs, broker/account **only when granted**. Tab changes do not patch context. Installation must not silently widen grants.
- Local AD-16: product sessions persist in **COMP-QMA-DAEMON sqlite** as a named closed-store-list amendment. Proposed parent amendment #3 names `product_session` records; it does **not** amend QMA AD-7 Profile law or QMA AD-5 `scope_path`.
- `CONTRACTS.md` §3 durable payload includes `"qma_session_id": "sess:…"` on the product-session record (“the execution container, not this record”).
- QMA AD-14 / code `qma.core.ontology.Session` @ 270e992: Session is a **run container**. Durable axes are `execution_model` and `autonomy` only. **Attachment is client state and is never a field on this record.**
- QMA AD-7 / code `Profile` + `assert_profile_presentation_only`: **Profile is presentation only** — client-side grouping of `desk_slug`s, **never daemon state, never a `scope_path` segment, never an index, filter, permission or routing key**.
- QMA AD-5 `scope_path` order is fixed: desk, quant, mission, task, session, agent, subagent. There is no `product_session` segment. A Task outlives the Session that runs it.
- QMA AD-6: “A store not on this list may not be created.” Session is already a fold. Amendment #3 adds `product_session` but not “private notes” (local AD-9: “product-session private notes are a **separate** scoped store”).
- Local AD-9: tool availability = intersection of (published ContributionHits, host grants, session profile, health). Copilot is “one familiar product surface over QMA infrastructure.”

**Unit A — overlay-on-Session epic (CONTRACTS / scope_path honor).** Reads “host/wire records” and the `qma_session_id` field as identity. Extends the existing Session fold with `profile`, `granted_ops`, `selected`, `app_instance`. `product_session_id == session.id` (or a 1:1 pointer). Grants live on the Agent capability set (QMA AD-16) **and** on the Session row. Tab switch is a Session patch because selected refs are now durable Session fields (AD-8 listed them). `scope_path` `session` segment **is** the product session. QMA AD-7 `Profile` is reused as `authoring`/`app-use` because the local AD used that word. Private notes are a column. Copilot **is** the QMA Agent in that Session.

**Unit B — distinct-table epic (AD-8 purist).** New `product_session` sqlite table (amendment #3). Ids are `psess:` vs `sess:`. Profile is immutable at create. One product session spawns many QMA Sessions (1:N) as execution containers per tool/Mission. `qma_session_id` is omitted from the durable row (client attachment). Grants live **only** on `granted_ops`. Selected refs mutate via an explicit wire command that bumps `context_revision`. Copilot is a wire actor that is **not** a QMA Agent; it opens QMA Sessions per invoke. Private notes are the “separate scoped store” AD-9 names — a fourth store not on amendment #3, so B either violates QMA AD-6 or stuffs notes into MemoryProvider (which AD-9 also forbids).

**Unit C — parent-Profile honor epic.** Refuses to persist `profile` in the daemon at all (QMA AD-7). Authoring vs app-use is client configuration. Grants stay on Role/toolset/Agent. Product-session overlay is wire-only, not sqlite (AD-8 “host/wire records”). Amendment #3 is treated as optional until QMA AD-7 is amended. Slice 0 “product-session records + grant intersection” cannot land.

All three obey some AD-8/AD-16/parent sentence. What diverges:

- **Shared-data shape.** One id vs two; `profile` as QMA `Profile` vs `ProductSessionProfile` vs client-only; `qma_session_id` durable vs absent; selected refs as Session attachment vs product-session fields vs client-only.
- **Two owners of one entity.** COMP-QMA-DAEMON Session fold vs a new table vs the client. Grants owned by Agent capability set **or** `granted_ops` **or** both (silent widen on install in A).
- **Conflicting mutation paths.** A patches Session on tab/select (forbidden by AD-8 **and** QMA AD-14 attachment law, but required by AD-8’s field list). B’s select command bumps `context_revision` and never touches Session. C never persists. Re-open on the other host: A’s copilot is an Agent whose `session_end` races AD-17 “UI dispose must not kill work”; B’s long-lived `psess` outlives every `sess:`; C’s grants ignore `granted_ops`.
- **Parent overload.** `Profile` and `Session` reused without a discriminator. `scope_path` has nowhere legal to put `psess:` so A overloads `session`. Proposed amendments do not name QMA AD-7 or AD-5.

**Tightened Rule (replace AD-8; amend AD-16 / proposed parent #3; fix CONTRACTS.md).**

> **AD-8.** `product_session` is a **new journal-projected record kind**, not a QMA `Session` and not a QMA `Profile`. Ids are `psess:`; QMA `Session` ids remain `sess:` and remain the execution container (AD-14 axes only). Cardinality is **1 product_session → many QMA Sessions**. `ProductSessionProfile` is a closed enum `{authoring, app-use}`, **immutable at create**, and is **not** `qma.core.ontology.Profile`. Parent amendment required: QMA AD-7 Profile law does not apply to this enum; QMA AD-5 `scope_path` does **not** gain a segment — product-session is a wire/header field beside `scope_path`, never a permission key inside it.
>
> Durable fields: `product_session_id`, `profile`, `principal`, `context_revision`, `app_instance_id` (pointer, not embedded blob — see H-3), `granted_ops` (snapshot at create/explicit re-grant), `selected_refs` (typed `{kind, id}` only). **Not durable:** `qma_session_id`, tab attachment, UI layout. Select/grant mutations are named wire commands that bump `context_revision`. Tab change is client attachment and writes nothing. Upgrade/install MUST NOT mutate an existing row’s `granted_ops` or retarget `app_instance_id`.
>
> **AD-9 private notes.** v1 = a JSON column on `product_session` (not a new store, not MemoryProvider, not Knowledge, not telemetry). Strike “separate scoped store”.
>
> **CONTRACTS.md §3.** Delete `qma_session_id` from the durable payload. Current attachment is a query, not a field.

---

### C-2 — AD-2 × AD-3 × AD-10 × AD-13 × mill/wire freeze: ContributionHit treated as fp1 (named check)

**The rules as written.**

- Local AD-2: product discovery concatenates typed hits. Frozen classes now **three**: `KnowledgeHit`, `ArtifactHit`, `ContributionHit {hit_class: contribution, plugin_id, point, qualified_id}` from live `published_contributions()` — **process-scoped; not fp1**. Prevents skills/graph-templates/mini-apps becoming **registry kinds**. Hypothesis listing refused on the facade. OPERATOR-QUESTIONS Q3: third *discovery* class on Library chrome.
- Local AD-3: every public operation publishes a versioned descriptor. **Durable file handoffs cite schema, content fp1**, source/run provenance — never a machine-local path as global id.
- Local AD-10: composition mode (1) consume artifact by **fp1/content id**; mode (4) composite app cites **contribution ids + artifact refs**. Dependency diamonds **pin versions per instance**.
- Local AD-13: semantic identity is fp1 (artifacts), `research_ref` (hypotheses), `qualified_id` (contributions). Conventions: contributions `plugin_id:local_id`.
- `CONTRACTS.md` ContributionHit has **no version**. Pack manifest `contributes` is `["tool:inspect", "graph_template:daily-brief", "view:heatmap"]` — a **different** encoding (`point:local_id`, no `plugin_id`).
- Inherited mill/wire @ 270e992 (`qma.wire.federated_discovery`): `FEDERATED_HIT_CLASSES = {knowledge, artifact}` **only**. `parse_federated_hit` refuses every other `hit_class` (tests: `hypothesis`, `strats`, `qml_candidate`, invented classes). `ArtifactHit.kind="graph-template"` is refused. `PublishedContribution` payload is `{plugin_id, point, cardinality, qualified_id?}` with **no `hit_class`**. Graph templates already carry `qualified_id` + `version` in-process (`GraphTemplate`).
- Proposed parent amendments **do not** list DEC-0389 / mill AD-9 two-class freeze. Inherited table lists mill AD-6/7/13/15, not AD-9.

**Unit A — Slice 0 concatenate epic (AD-2 purist).** Adds `hit_class: contribution` to the federated union and to Library chrome. Hits are live `published_contributions()` rows. After restart, the same `qualified_id` may resolve to a different plugin version (process-scoped, as written). Workflows and composite apps store `qualified_id` as the pin. Pack `contributes` strings are a third encoding A must guess-map. `view:heatmap` is emitted as a ContributionHit even though there is no `ui_view` point (QMA AD-1).

**Unit B — wire-honor / durable-handoff epic.** Reads DEC-0389 literally: federated DTO stays two classes. Contributions remain the existing `published_contributions()` query (no `hit_class`). To pin a contribution across restart / pack export (AD-3 durable handoff **requires content fp1**; AD-10 pins versions), B fingerprints the descriptor JSON and stores `fp1:sha256:…`. Callers then either (b1) wrap that as `ArtifactHit` with an illegal kind, (b2) stuff the fp1 into an AD-3 `artifact_ref` output, or (b3) treat `qualified_id` as if it were fp1-shaped. ContributionHit **is** fp1 in B. Graph-template `kind` still refused on the Artifact rail, so B’s pin is an untyped digest in a workflow payload.

**Unit C — copilot-only rail epic.** AD-2 binds “UI/agent search, copilot discovery, packaging” but COPILOT-AND-APPS says UI **may** show one Library chrome. C keeps Library = Artifact+Knowledge (Workbench AD-3) and puts ContributionHits only on the copilot descriptor list (AD-9). Packaging uses pack `contributes[]`. Three search APIs, three ids for one tool.

All three obey. What diverges:

- **Shared-data shape.** `{hit_class, plugin_id, point, qualified_id}` vs `{plugin_id, point, cardinality, qualified_id}` vs `point:local_id` pack strings vs `fp1:sha256:` of descriptor bytes. No version on the hit; version only on `GraphTemplate` / pack.
- **Two owners.** COMP-QMA-WIRE (federated DTO) vs COMP-QMA-DAEMON (`published_contributions`) vs COMP-QMB (`library.search`, Artifact rail) vs content-addressed qmf-core namespace (B’s digest).
- **Identity collision.** B’s descriptor-fp1 is an Artifact-rail-shaped id for a non-kind. A’s `qualified_id` is not unique across versions (AD-10 pin requirement unmet). C’s copilot list and Library search never join.
- **Parent override.** Adding `hit_class: contribution` without amending DEC-0389 is a silent freeze-break. Factory lane A’s tests fail against current `test_federated_discovery.py`; lane B’s pins fail AD-2 “not fp1”.

**Tightened Rule (replace AD-2 identity paragraph; name the parent amendment; freeze encodings).**

> **AD-2.** Federated union is `KnowledgeHit | ArtifactHit | ContributionHit`. **Named parent amendment** of mill/wire DEC-0389 (two-class freeze) and of `FEDERATED_HIT_CLASSES` @ 270e992. `ContributionHit` identity is exactly `{hit_class: "contribution", plugin_id, point, qualified_id, package_id, package_version}` where `qualified_id` is QMA’s `<plugin_id>:<local_id>`. **Never fp1, never a registry kind, never `ArtifactHit.kind`.** Workflows, composite apps, and pack pins store `(qualified_id, package_version)`, not a content digest. Live `published_contributions()` is the query; missing/disabled plugin ⇒ typed unavailability, not a stale fp1 hit.
>
> Canonical pack `contributes` entries **are** `{point, local_id}` and expand to that hit at enable. `view:*` is a wire DTO only (AD-17); it is **not** a plugin contribution point and **not** a ContributionHit until a named GAP-0081 `ui_view` increment.
>
> **AD-3.** “Content fp1” on durable **file** handoffs applies to artifact bytes, not to contribution identity. A contribution pin is the AD-2 tuple. Do not fingerprint descriptors to satisfy this sentence.
>
> **AD-13 / Conventions.** `qualified_id` + `package_version` for contributions. Strike any reading that `qualified_id ⊂ fp1`.

---

### C-3 — AD-11 × ResolvedRunConfig × L36 × C-18: dummy Book still possible (named check)

**The rules as written.**

- Local AD-11 Prevents: “fake Book/BMS fields; silent L36 inversion; ungoverned CT-32 as admission.”
- Two honest targets: (1) **default system** — sanctioned QMB compile still requires complete CT-22/CT-27; QMN operable seats still require Book. (2) **non-Book work** — ungoverned `qmb.run()` / ordinary Python / data-ML apps / QMN **sensing-only** — **no Book**, no governed evidence, no venue commands, no L17 seat.
- Alternative **policy** inside the default system = “a complete new CT-22/CT-27 in `dev` evaluated by `analysis.rerun`, never a patch and never `analysis.project`.”
- Live/node-paper without Book **refused** until L36 amendment. “optional-intelligence means a system may have no MIS consumer, not a fake MIS record.”
- JOURNEYS J03 **Forbidden:** dummy Book fp1. CONFLICT-REGISTER C-18: no dummy CT-33. IMPLEMENTATION-SEQUENCE: “Do not weaken those [compile tests] to admit dummy Book.”
- No AD defines **dummy**. “Complete document” and “dummy wrapper” are antonyms in prose, synonyms in the compiler.
- Brownfield `ResolvedRunConfig` @ 270e992: **required** `book_fp1`, `bms_fp1`, `bot_fp1`, `book_fragment_fp1`, `bms_fragment_fp1`. Ungoverned `qmb.run()` uses this type (Workbench ungoverned = no ledger, not no Book). RECON F-05 retained.

**Unit A — honest-absent epic.** Introduces a second config type (or optional fields) for ungoverned / data-ML / sensing-only with **no** `book_fp1`/`bms_fp1`/`bot_fp1` keys. Sanctioned compile tests stay green. `qmb.run()` on that path never mints CT-22. QMN sensing-only is a door that never constructs a seat. Alternative **trading** policy still goes through complete CT-22 + `analysis.rerun`.

**Unit B — complete-no-op epic (dummy Book).** Compiler stays one type (do not weaken tests). To run data-ML or “ungoverned without Book” through the only library entry, B mints a well-formed CT-22/CT-27 (all required keys, fingerprinted, `dev` zone) whose policy is identity / unlimited / pass-through, plus a dummy CT-33 because `bot_fp1` is also required. B cites AD-11’s own sentence: alternative policy **is** a complete new CT-22/CT-27. J03’s “dummy Book fp1” is commentary; the Rule never refuses a complete document. QMN sensing-only is a seat with that Book that never places CT-19 (no venue commands — AD-11 honored). L36 appears intact because a Book record exists.

Both obey every AD-11 clause they cite. What diverges:

- **Shared-data shape.** Config with absent Book keys vs config citing `fp1:sha256:<NULL_BOOK>`. Same data-ML app produces a recipe artifact in A and a CT-32-shaped run in B (or a refused compile in A if someone calls the sanctioned door).
- **Two owners of “the alternative system.”** COMP-QMB compiler (required fields) vs COMP-QMF-RISK (CT-22 meaning) vs QMN seat (operable vs sensing). A’s non-Book path has no CT-22 owner; B’s owner is a fake Book.
- **Conflicting mutation paths.** A never writes registry Book rows for research. B writes Book rows for everything that wants `qmb.run()`, then “evaluates” them with `analysis.rerun` (the alternative-policy sentence) — silent L36 inversion by occupancy of the Book slot. MIS optional-intelligence: A omits the consumer; B inserts `mis_ref: null` or a dummy MIS because the Book schema wants a field.
- **Mechanical test missing.** “Dummy” is not a schema check. Factory lanes will ship B because it keeps `test_run_config.py` green and still prints “complete CT-22”.

**Tightened Rule (replace AD-11 dummy/non-Book sentences; add a compiler law).**

> **Dummy (mechanical).** A CT-22/CT-27/CT-33 is dummy if it is minted **solely to satisfy a required field**, or if its policy is identity / no-op / unlimited / pass-through. Sentinel fps (`NULL_BOOK`, empty-object Book, `mis_ref: null` as a fake MIS) are dummy. Dummy is `INVALID_INPUT` at compile, register, and seat.
>
> **Two config types, not optional fields on one.** (1) `ResolvedRunConfig` — unchanged; `book_fp1`/`bms_fp1`/`bot_fp1`/fragments **required**; this is the default system and the only path to governed evidence, node-paper, live, L17 seats. (2) `UngovernedWorkConfig` — **those keys absent, not null**; used by ungoverned `qmb.run()`, ordinary Python, data-ML, recipes, QMN sensing-only. Sensing-only **is not a seat**.
>
> **Alternative policy inside the default system** is a complete CT-22/CT-27 that still implements Book/BMS semantics (L36 hierarchy: bot → book → BMS → operator). Evaluation is `analysis.rerun` of that fingerprint. It is not a wrapper around absent policy and not a projection.
>
> Live/node-paper without Book remains refused until a constitution amendment of L36. Do not weaken existing compile/fragment tests to admit type (2) through type (1).

---

### C-4 — AD-4 × AD-7 × AD-8 × AD-13 × Workbench AD-16: Board treated as Mission (named check)

**The rules as written.**

- Local AD-4: four layers stay distinct. (1) **Board layout** — draft arrangement; editing it does not mutate in-flight work. (2) Graph Template — authored, versioned, stateless DAG; plugin-contributed; **rebuilds on load**. (3) Task Graph — one Mission’s execution projection. (4) Ungoverned library call — writes no Mission. “Selected-subgraph execution runs a **valid** subset of a **pinned** template version, **not a live board scribble**.” Board is not a registry kind, not a Mission, not automatic execution.
- Local AD-7: one template → one Mission via Mission Compiler. ExperimentSpec successors are lineage, not control-flow.
- Local AD-8: product session carries **selected object refs**.
- Local AD-13: “Display names and Board layouts are UX.” Semantic identity list does **not** include Board or Graph Template (templates are `qualified_id`).
- Local AD-16: Graph Templates rebuild from plugins. Product sessions persist in sqlite.
- Workbench AD-16: no Project/Workspace kind; UI tabs must not mint a record. Proposed parent amendment #1: Experimentation Board is an allowed **display alias; still mints no record**.
- Brownfield: `GraphTemplate` has `qualified_id` + `version` + `edges`; `TaskGraph` has `nodes` + `tasks` and **no edges field**. Catalog is in-memory; templates rebuild from plugins (RECON F-07). `validate_graph_template_topology` is pairwise reverse-edge (F-09) — AD-6 closes that Rule, not this hole.

**Unit A — ephemeral-Board epic (Workbench AD-16 honor).** Board layout is client-only (localStorage / wire attachment). It is not a field of `product_session`, Mission, or Graph Template. “Run selection” = `MissionCompiler(template.qualified_id, template.version, node_ids: frozenset)` producing one Mission / one Task Graph. The subset is an induced DAG of the pinned plugin version. Product session may store **refs** (template id + version + node ids), never layout JSON. Editing the board writes no daemon record.

**Unit B — session-is-the-Board epic.** AD-8 lists selected object refs as durable product-session fields. B stores `board_layout` JSON (nodes, edges, positions, selected subgraph) on `product_session`. “Run board” validates `layout ⊆ pinned template` (AD-4 “not a live scribble” honored by the validate step) then compiles. The `psess:` row **is** the working-surface identity Workbench AD-16 forbade as Project. UI treats “the Board” as the running Mission (same name, same selected refs, same copilot). Because templates **rebuild on load** (AD-4/AD-16), B’s “pinned version” is whatever the plugin currently publishes at that `qualified_id` unless B also fingerprints the template JSON — which makes a Graph Template an fp1 artifact (Workbench AD-3: Graph Templates are **not** Library objects).

Both obey. What diverges:

- **Shared-data shape.** Compiler args `(qualified_id, version, node_ids)` vs durable layout JSON on `product_session`. Pin = pack version vs content fp1 of template bytes vs live rebuild.
- **Two owners of one entity (the runnable subgraph).** Mission Compiler / Task Graph (A) vs product_session (B). B’s layout edit is a product-session mutation that does not touch in-flight Tasks (AD-4 editing clause) but **is** the mutation path for “what will run next.” A has no such record.
- **Board-as-Mission.** B does not set `artifact_kind=task_graph` on the layout (type tag holds) and does not mint a registry kind (AD-4 Prevents holds). It still **uses** the Board record as the Mission’s identity in every join: occupancy, copilot context, selected refs, restart. Amendment #1 “mints no record” is false the moment layout sits on `product_session`.
- **Rebuild vs pin.** A’s pin is `GraphTemplate.version`. B’s pin after plugin reload is new bytes at the same `qualified_id` unless B invents an fp1.

**Tightened Rule (replace AD-4 selected-subgraph sentence; constrain AD-8 selected; pin law).**

> **AD-4.** Board layout is **client-only**. It MUST NOT be a field of `product_session`, Mission, Task Graph, Graph Template, or any sqlite row. Display alias only (Workbench AD-16). Selected-subgraph execution is `MissionCompiler(template.qualified_id, template.version, node_ids)` where `node_ids` is a non-empty induced DAG of that **already-registered** template version. It does not mint a Graph Template, does not persist layout, and does not treat the Board as the Mission. One compile → one Mission → one Task Graph. Editing the client layout writes nothing; running it creates a Mission whose `graph_template_ref` is the template `qualified_id`, never a board id.
>
> **AD-8 `selected_refs`.** Closed kinds: artifact fp1, `research_ref`, contribution `(qualified_id, package_version)`, template `(qualified_id, version)`, dataset/run/attempt refs, node-id sets **citing** a template. **Forbidden:** layout JSON, positions, widgets, json-render trees.
>
> **Pin.** Graph Template identity for compile is `(qualified_id, version)` from the plugin manifest at enable. Rebuild-on-load may not change bytes of an enabled `(id, version)`; a byte change is a new version or a disable. Do not fingerprint templates into the Artifact rail.

---

### C-5 — AD-17 × AD-3 × AD-9 × AD-21: json-render as authority (named check)

**The rules as written.**

- Inherited preamble: a local rule that would “treat json-render as identity is a **conflict**, not an override.”
- Local AD-17 Prevents: “every pane as MCP App; **json-render as runtime**; tab-close cancelling jobs.” Rule: contribution descriptors (navigation, commands, rich views, parameter forms, context providers, events, reconnect) are **wire-owned DTOs** — **not** a v1 `ui_view` plugin point until GAP-0081. JSON Render may assemble **registered** inspectors/forms. MCP Apps may host **tool-linked HTML**. Native panes remain first. UI mount/dispose must not start/kill durable work.
- Local AD-3: the operation descriptor’s `input_schema` is the public contract. Transport is the owner’s choice.
- Local AD-9: tool availability = intersection of ContributionHits, host grants, session profile, health. **Prose is not authorization.** App-supplied text must not grant tools.
- Local AD-21: deep behaviour of an AD-3 operation is identical across supported doors.
- UI-HOST: three presentation lanes (native, JSON Render, MCP Apps). “None own identity or permission.” Deferred: json-render not pinned.
- `CONTRACTS.md` pack `contributes` includes `view:heatmap`. QMA AD-1: **there is no `ui_view` point**; a contribution point with no wire schema may not be registered.
- DEC-0392 (docs): json-render / MCP Apps “are not identity, persistence, or authority.” Local AD-17 never repeats the word **authority**.

**Unit A — descriptor-authority epic.** `input_schema` on the AD-3 descriptor is the only parameter allowlist. json-render catalog, if present later, **projects** that schema. Missing catalog entry ⇒ native or CLI form, same schema. MCP App HTML is sandboxed display; every tool call is intercepted by the host and checked against `granted_ops`. Pack `view:*` is documentation in the manifest, not a registered contribution.

**Unit B — catalog-as-schema / MCP-as-invoke epic.** AD-17 says JSON Render **may assemble registered inspectors/forms** and MCP Apps **may host tool-linked HTML**. v1 UI sitting has not chosen a native host (Deferred / GAP-0081). B therefore ships json-render catalog ids as the parameter form (catalog-constrained generative UI **is** the allowlist of fields) and MCP Apps as the invoke path (SEP-1865 tool-linked HTML). An op with no json-render component is CLI-only (AD-21 parity broken in practice). Pack `view:heatmap` registers a json-render tree; the tree’s digest becomes the widget identity (AD-13 display names are UX — B claims the digest is the contribution id). Host grants are implied by whichever tools the HTML links — app-supplied text as authorization (AD-9 Prevents, but AD-17’s “tool-linked” sentence is the other reading).

Both obey. What diverges:

- **Shared-data shape.** AD-3 `input_schema` vs json-render catalog component tree vs MCP `ui://` resource. Widget identity = `qualified_id` vs UI-tree fp1.
- **Two owners of one entity (what may be submitted / invoked).** COMP-QMA-CORE descriptor vs `@json-render/*` catalog vs MCP Apps runtime. Permission owned by `granted_ops` (A) vs HTML tool links (B).
- **Conflicting mutation paths.** A: host checks AD-3 + grants, then places the op. B: json-render validates fields (subset/defaults differ from CLI — AD-21 hole) and MCP Apps fires the tool. Tab dispose in B can unmount the MCP App that **is** the in-flight invoke (AD-17 Prevents tab-close cancelling jobs, but B’s invoke **is** the pane).
- **Identity.** Preamble forbids json-render as identity; AD-17 never says so. B fingerprints the form.

**Tightened Rule (replace AD-17 presentation paragraph; bind AD-3/AD-9/AD-21).**

> **AD-17.** json-render and MCP Apps are **presentation adapters** for wire DTOs. They are not identity, not persistence, not a runtime, **and not authority**. The only parameter authority is the AD-3 `input_schema`. The only invoke authority is AD-9 intersection (ContributionHits ∩ host grants ∩ `product_session.granted_ops` ∩ health). A json-render catalog entry MUST name an existing AD-3 `op_id` and MUST NOT add/remove fields. Absence of a catalog entry is native/CLI using the same schema, not an error and not a different op. MCP App HTML MUST NOT grant tools; the host intercepts every tool call and refuses if outside `granted_ops`. Pack `view:*` is a wire DTO, not a plugin point, not a json-render runtime id, not an fp1. Native QMX panes remain first; GAP-0081 still owns chrome. Do not pin `@json-render/*` in this sitting.

---

## HIGH

### H-1 — AD-3 × AD-5: mapping declared twice — clashing dataflow shapes

**The rules as written.** AD-3: every operation publishes `cardinality/mapping`. AD-5: collection mapping is declared **on the edge**: `one | zip | broadcast | keyed-join | cartesian`. `CONTRACTS.md` §1 puts **both** `cardinality` and `mapping` on the operation descriptor (`"cardinality": "one", "mapping": "one"`).

**Unit A — descriptor-centric.** Mapping is a property of the op. Edges only connect. Two inbound edges to `qmb.analysis.project` share one mapping. Cartesian flag lives on the op.

**Unit B — edge-centric.** Mapping is per edge. The same op can be zipped on one inbound edge and broadcast on another. Descriptor has arity only.

What diverges: shared payload (one field on two messages); two owners (op author vs template author); mutation (changing an op version silently rewrites every template in A, only edges in B). Fan-out/join epics will not assemble.

**Tightened Rule.**

> **AD-3.** Drop `mapping` from the operation descriptor. Keep `cardinality` as native arity (`one | many` in/out) and `empty_policy`. **AD-5** remains the only mapping law, on the Graph Template **edge**. `CONTRACTS.md` §1: delete `"mapping"`. Cartesian flag is edge-only.

---

### H-2 — AD-7 × Workbench AD-8 × QMA AD-12: Task Graph edges and occupancy have two writers and no shape

**The rules as written.** AD-7: persist `task_graph_state` **and occupancy maps** in daemon sqlite; implement successor dispatch in `qma.daemon.taskgraph`; ExperimentSpec successors are **lineage, not control-flow**. QMA AD-12: Task Graph is the only place work state lives (already named on the closed list — amendment #3 “add task_graph_state” is persistence of an existing projection, not a new store). Workbench AD-8: occupancy is one QMB **run** per ExecutionEnvironment, tracked by the door / `JobHandle`. Brownfield `TaskGraph` has **no `edges` field**; `TaskGraphNode` has no successors; `TaskGraphStore` holds graphs, missions, dispatch leases, environment leases, job handles **in RAM**.

**Unit A — edge-table epic.** Adds `TaskGraph.edges: {from, to, mapping}` (AD-5) and a sqlite occupancy table. Dispatcher walks those edges. Leases remain RAM-derived.

**Unit B — successor-on-node + lease-as-occupancy epic.** Puts `successors: tuple[str, …]` on `TaskGraphNode`. Occupancy **is** `environment_lease` / `JobHandle` (already in `TaskGraphStore`); no new table (amendment #3 did not name occupancy). ExperimentSpec CT-07 is copied into node successors “so restart can walk” — lineage vs control-flow collapse AD-7 forbade.

What diverges: edge JSON vs successor lists vs CT-07; occupancy rows vs leases; QMB door occupancy vs daemon map (two writers of one slot). Restart reconstruction (Slice 1b) cannot join.

**Tightened Rule.**

> **AD-7.** Task Graph **must** persist `edges: {from, to, mapping}` (AD-5 vocab) as part of the existing `task_graph_state` projection. Nodes do not carry successor lists. ExperimentSpec CT-07 remains lineage only and MUST NOT be walked as control flow. Occupancy is **not** a new table: it is the existing `environment_lease` + Workbench AD-8 door law, folded into `task_graph_state`. QMB does not write daemon occupancy; the daemon maps `JobHandle` ↔ lease. Strike “occupancy maps” as a separate store.

---

### H-3 — AD-8 × AD-10 × AD-12 × AD-16 × AD-18 × QMA AD-6/AD-22: change-request, mini-app instance, and recipe have no home

**The rules as written.** Closed-store amendment #3 names **only** `product_session` and `task_graph_state`. AD-8 mints a **change-request staging artifact**. AD-10 needs **installed instances** (shared vs separate; diamonds pin versions). AD-12 recipes are versioned derived artifacts, not a Library kind; “if later shared as fp1 metadata, mint a CT-06 addable kind.” AD-18 install is a host operation. QMA AD-6: undeclared store forbidden. QMA AD-22 staging kinds are `prompt | memory | skill | toolset | worker_template | hook | graph_template | loop | role` — **not** change-request, not pack, not recipe. Plugin **install records** already exist (AD-21). Workbench AD-13 already has derived datasets as fingerprinted artifacts, not Library kinds.

**Unit A.** Change-request = `RefinementProposal` (illegal kind or stretched `skill`/`graph_template` edit). Instance = plugin install record (`plugin_id` = `instance_id`). Recipe = QMB-private `recipe_id: derived:…` (`CONTRACTS.md` §5), no CT-06.

**Unit B.** Change-request = new fp1 artifact (leaks toward Artifact rail / qmf-core, AD-16 Prevents). Instance = embedded `app_instance` blob on every product_session (two sessions ⇒ two drifting copies; AD-10 “shared vs separate” cannot be expressed). Recipe = immediate CT-06 kind owned by COMP-QMF-DATA (the “if later” clause taken as v1).

What diverges: three identities for instance (`plugin_id` vs `instance_id` vs session-embedded); change-request as proposal vs fp1 vs session column; recipe as `derived:…` vs CT-06 vs Workbench derived-dataset fp1. Two owners each (QMA staging vs unnamed sqlite vs QMB vs qmf-data).

**Tightened Rule.**

> **Stores v1 (amendment #3 complete list).** (1) `product_session` projection. (2) `task_graph_state` projection (already named). (3) **mini-app instance** rows in the existing plugin-install projection, keyed by `instance_id` ≠ `plugin_id` (side-by-side versions; product_session points at `instance_id`). No other new sqlite.
>
> **Change-request.** Staging-store kind `change_request` (named AD-22 addable kind). Not an fp1, not a Library object, not `promote`. Apply opens/uses an authoring `product_session` with copied refs; never mutates the source app-use row.
>
> **Recipe.** v1 identity is the **output release fp1** (existing derived-dataset law, Workbench AD-13) plus a lineage CT-07 to CT-10/CT-12 inputs. `recipe_id` is display. CT-06 kind deferred until metadata-sharing is required. Not a Library kind. Owner: COMP-QMB wrap of COMP-QMF-DATA.

---

### H-4 — AD-9 × AD-3 × AD-18 × QMA AD-16: grants live in four places

**The rules as written.** AD-9 intersection: ContributionHits ∩ host grants ∩ session profile ∩ health. AD-3: manifests **request**; host **grants**. AD-8: `granted_ops` on product_session; install must not silently widen. AD-18: pack `requests`. QMA AD-16: Agent effective capability set computed at spawn; toolsets are definition-store records of `plugin_id:local_id`.

**Unit A.** Host grants = Role/toolset; `granted_ops` is a denormalized copy; spawn recomputes Agent set from toolset (upgrade widens new Agents, old product_sessions keep the copy — or don’t, if A treats the copy as live).

**Unit B.** `granted_ops` is the live allowlist; toolset is advisory; Agent capability set is computed from the product_session. Copilot in a QMA Session (C-1-A) then has **two** effective sets.

What diverges: who mutates on install; whether a Mission can be wider than the product_session; whether AD-3 `permission_requests` are the same strings as tool ids as pack `requests` as ContributionHit `qualified_id`.

**Tightened Rule.**

> Live allowlist for app-use is `product_session.granted_ops` only (snapshot). Authoring uses the QMA Agent capability set (toolset ∩ Role ∩ Mission), never `granted_ops`. Host grant is an operator-principal wire command that **sets the snapshot**; it does not write Role/toolset as a side effect. Pack `requests` and AD-3 `permission_requests` are the same id space as `qualified_id`. Upgrade never mutates existing snapshots.

---

### H-5 — AD-3 × AD-2 × QMA AD-16: operation descriptor, Tool, and ContributionHit are three names for one invoke

**The rules as written.** Structural seed: operation descriptor types in **qma-core**; ContributionHit in **qma-wire**; `published_contributions` in **qma-daemon**. AD-3: every public operation publishes a versioned descriptor (`op_id`, owner COMP, schemas, effect class, placement…). QMA tools are `<plugin_id>:<local_id>` in the Tool Registry. Slice 0: “wrap three existing doors.”

**Unit A.** Descriptor **is** the tool record. `op_id == qualified_id`. QMB doors grow a descriptor sidecar in qma-core types.

**Unit B.** Descriptor is a new qma-core type **beside** tools. Copilot discovers ContributionHits (tools), workflows compile AD-3 `op_id`s, CLI uses QMB verbs. Three invoke paths, three id spaces (`qmb.analysis.project` vs `analysis-backtest:qmb` vs CLI `qmb analysis project`).

What diverges: owner COMP on a QMA tool (COMP-QMA-DAEMON vs COMP-QMB); placement `local-library` skipping QMA env (AD-15) vs always going through Compute Router; effect class vs occupancy.

**Tightened Rule.**

> An AD-3 `op_id` for a plugin-contributed operation **is** its `qualified_id`. QMB-owned doors (`library.search`, `analysis.project`, `qmb.run`, …) publish descriptors with `owner: COMP-QMB` and `op_id` in `qmb.*`; the analysis-backtest **tool** remains the QMA adapter that **places** those ops through CT-47, it is not a second op. No third id. Effect class `place-run` ⇔ Workbench occupancy; `read` ⇔ query.

---

### H-6 — AD-12 × AD-13: recipe vs derived dataset vs CT-10 widening

Covered in H-3 identity. Residual: AD-12 “heterogeneous non-market facts do not widen CT-10 into untyped JSON” vs recipe `transforms: [{name: asof-join}]` as untyped names. **Unit A** closes transform names. **Unit B** stores arbitrary JSON transforms (the encoding AD-12 Prevents). Tighten: v1 transform vocab is closed (`asof-join`, `filter`, `resample`); unknown name refuses. Preview ≠ export job ≠ stream remains; do not overload recipe_id as a Library kind.

---

### H-7 — AD-21 × QMA/QMN no-CLI: headless parity has no door for QMA-owned ops

AD-21: deep behaviour identical across supported doors. QMB remains the only operator CLI; QMA and QMN ship none. **Unit A:** QMA-owned ops are wire-only; “headless” means a machine-principal qma-wire client. **Unit B:** `qmb` CLI grows passthrough to qma-wire (product CLI wrapping QMA) — a QMA CLI in all but name. Tighten: supported doors are listed per descriptor. QMA-owned ops: qma-wire + in-process library. QMB-owned: library + `qmb` CLI + CT-47. QMN-owned: three doors, no CLI. `qmb` MUST NOT grow QMA passthrough.

---

## MEDIUM

### M-1 — AD-9 private notes vs MemoryProvider vs Knowledge

Closed if C-1’s “JSON column” paste lands. Until then Unit A uses MemoryProvider (desk-scoped, GAP-0072) and Unit B uses Knowledge cite-copy. AD-9 already says they are neither; it just never names the column.

### M-2 — AD-12 stream `consumer_id: psess:…` vs QMA Session vs JobHandle

`CONTRACTS.md` §7 pins `consumer_id` to a product session. Closing a tab must not cancel jobs (AD-17) and must not cancel another consumer (J17). **Unit A** keys subscriptions by `psess` (tab close ends the session ⇒ cancel — forbidden). **Unit B** keys by `JobHandle` / `sub_id` (correct) but then `consumer_id` on the contract is a lie. Tighten: `consumer_id` is `sub_id`; product session may **hold** a list of sub ids; dispose of UI does not cancel.

### M-3 — AD-6 DAG Rule is closed; Loop `stopping_condition` is not

AD-6 (refuse self-loops and directed cycles; Loops are node state) is not a two-unit hole. Memlog still names Loop `stopping_condition` as opaque string. **Unit A** keeps the string. **Unit B** structures it. Out of Slice 0; record as a later bind, not a freeze blocker.

### M-4 — AD-22 Portfolio Manager label vs QMA Role record

AD-22 is tight (`desk_slug=pm` unchanged). Residual: skills/prompts that **branch** on display label vs slug. Not a data-shape fork if the Role record is untouched. No new AD needed beyond “do not parse the label.”

---

## Closures that hold (do not re-litigate)

| Claim | Why it holds |
| --- | --- |
| Sixth COMP / extra daemon | AD-1 + L7/L8; every capability names an existing COMP or connect/extend |
| QMA `import qmb` | Inherited Workbench AD-8/AD-9; occupancy via CT-47 door |
| `hit_class: strats` / hypothesis as Library kind | AD-2 still refuses those; C-2 is the **contribution** freeze-break, not STRATS |
| Skill as Loop / Graph Template as Task Graph **type tag** | `artifact_kind` discriminator + `assert_template_not_interchanged` hold; C-4 is identity-of-run, not the tag |
| Skills compile to Missions | AD-7 last sentence |
| Live/node-paper without Book | AD-11 refuse-until-L36; C-3 is dummy-on-the-research-path, not this refuse |
| Marketplace / solver / HMR / execution tool | Graveyard DECs + AD-9/AD-14/AD-18 |
| mutmut as product dependency | AD-19 |
| json-render imported as n8n/Hermes runtime | AD-17 Prevents “as runtime”; C-5 is authority/schema, not an import |
| DAG law wording | AD-6 is executable as written (DFS, refuse A→B→C→A and A→A). Code @ 270e992 is behind the Rule, not ambiguous |

---

## Named-check index

| Check | Finding | Still possible under the letter? |
| --- | --- | --- |
| Dummy Book | C-3 | **Yes** — complete no-op CT-22 satisfies “complete document” and the live compiler |
| Product session vs QMA Session mix-up | C-1 | **Yes** — `CONTRACTS.md` `qma_session_id` + overloaded `Profile`/`scope_path` |
| ContributionHit treated as fp1 | C-2 | **Yes** — AD-3 durable-fp1 + frozen two-class DTO force a digest pin |
| Board treated as Mission | C-4 | **Yes** — layout lands on `product_session` and compiles as the run identity |
| json-render as authority | C-5 | **Yes** — catalog/MCP “may assemble / tool-linked” with no authority sentence |

---

## Apply order (editor)

1. C-1 AD-8/AD-16/CONTRACTS §3 (blocks Slice 0 product-session table).
2. C-2 AD-2 parent amendment + pin tuple (blocks Slice 0 concatenate).
3. H-1 drop descriptor `mapping`; H-5 `op_id == qualified_id` for plugin ops (blocks Slice 0 descriptors).
4. H-2 Task Graph `edges` shape + occupancy = leases (blocks Slice 0 successor dispatch).
5. C-4 Board client-only + compiler args (blocks Board-as-Mission once sessions exist).
6. C-3 two config types + mechanical dummy (blocks Slice 1 alternative-system).
7. C-5 json-render/MCP not authority (blocks UI-HOST misread; not a Slice 0 code freeze).
8. H-3/H-4/H-7 stores, grants, CLI doors.

Do not freeze Slice 0 until 1–4 land. DAG validator stories may proceed against AD-6 as written.
