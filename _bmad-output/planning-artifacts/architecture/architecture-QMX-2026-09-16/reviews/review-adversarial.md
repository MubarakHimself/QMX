---
review: adversary
target: ARCHITECTURE-SPINE.md (QMX QML research expansion, 2026-09-16 restart)
companions: [QML-EXPANSION.md, REQUIREMENTS-ADDENDUM.md]
parents_read: [QL-1/QL-2/QL-5/QL-8 (architecture-QML-2026-08-21), Workbench AD-3/AD-4 (architecture-QMX-2026-09-14), QMA AD-19/CT-44, L33, graduate_to_governed @ integration-inspect]
date: 2026-09-16
lens: 'Attack the spine as an adversary: construct two units one level down that each obey every AD to the letter yet still build incompatibly — clashing shared-data shapes, two owners of one entity, conflicting state-mutation paths. Every pair is a hole to close with a new or tightened AD.'
prior_gate: 'First-distill adversarial C-1..C-4/H-1 were applied (frozen KnowledgeHit/ArtifactHit, origin non-fp1, source_ref mapping, browse snapshot pin, cite-copy non-identity). This review attacks the restart (AD-15..AD-21 + amended AD-1/AD-7/AD-17), not the superseded STRATS-as-language facade.'
---

# Adversary review — QML research expansion spine (2026-09-16)

## Method

For each local AD (especially AD-7, AD-15, AD-17, AD-18, AD-19, AD-21) and the inherited QL-1 / QL-8 / CT-44 joints this sitting binds, build **two conforming units one level down** — factory epics a connect wave would actually spawn (`qml.research` types, host research-root persistence, `graduate_to_governed` wiring, QMA cite transport, UI research pane vs Library, ungoverned QMB tunnel, CT-34 authoring) — and ask whether both can obey every written Rule plus every inherited parent Rule and still be unable to assemble.

Only pairs where **both readings are literal** are reported. `[PROPOSAL]` parent amendments and Deferred rows count when v1 must already pick a shape. Findings end with paste-ready Rule text.

Parent spines bind read-only. A local AD that overloads a parent field (`originating_research_ref`, QL-1 surface count, CT-07 `promoted-from`) without a typed discriminator is a hole, not a license. Brownfield `qml.conformance.registration.graduate_to_governed` on `integration@8510c03` is in-scope: AD-17 cites it by name.

## Verdict

**Return for amendment — do not freeze `qml.research` types, research-root persistence, or graduation-origin epics.** Intent is tight: two-stage authoring, Stats as seed, no sixth COMP, hypotheses not Library objects, don’t-box-in, QMA cites / QML owns meaning. The AD set fails at the joints those epics would implement.

Four load-bearing joints let two conforming units ship incompatible products: (1) `research_ref` / Citation digest / `fp1` / `artifact_ref` share one untyped fingerprint slot; (2) hypothesis persistence has no named host, so QMA and a QML composition root both legally serialize; (3) AD-17 explicitly allows two different objects as `originating_research_ref` while AD-7 already owns a third origin field; (4) the proposed QL-1 four-surface amendment is optional against a ratified three-surface parent, so Stage 0 types can land in three packages. High follow-ons: unbound Stage 0 format version, KnowledgeHit-as-hypothesis, confluence homonym, Stage 0 as optional skip vs QML toll booth.

Slice 0 seed bind + cite + read-only LAYOUT-DEMO projection can proceed. Anything that **mints `research_ref`, persists a research root, or wires `graduate_to_governed`** will fork if these stay open.

| Tier | Count |
| --- | --- |
| Critical | 4 |
| High | 5 |
| Medium | 4 |

Pairs that could **not** be made to diverge (closures that hold): minting `COMP-LIB` / a sixth application; adding `strats` to `LIBRARY_KINDS`; auto-assembling CT-33 from DNA / compiling `graph.yaml` → `run_slice`; QMA `import qmb` or an execution tool; write-back into Stats; federated DTO growing `hit_class: "strats"` or a third rail; hybrid/semantic index without GAP-0073; citing Stage 0 from CT-32 / seating it. Those are not the problem. The problem is the **new identity, owner, and mutation surfaces** AD-15..AD-21 introduce without a single home.

---

## CRITICAL

### C-1 — AD-17 × AD-21 × AD-9 × QL-8 code: `research_ref` vs `source_ref` vs `fp1` vs Citation `artifact_ref` collide in one untyped slot

**The rules as written.**

- AD-21: a hypothesis is identified by a QML-ladder content hash `research_ref` (semantic content + format version). **It is not a qmf-registry `fp1`** and not a Library object.
- AD-17: graduation links a distinct `originating_research_ref` (**QML-local `research_ref` or a Knowledge Citation digest** — never the new Bot `fp1`).
- AD-9 / Conventions: CT-44 identity is `source_ref` + `snapshot_ref` + `locator`; cite-copy digest is `artifact_ref` on the Citation, **never an Artifact-rail hit**; artifacts are `fp1`.
- Brownfield (`registration.py` + `test_graduation_research_ref_must_be_fp1`): `originating_research_ref` is coerced to a qmf-core `Fingerprint`; a non-`fp1` string (`"research://exp-42"`) is `INVALID_INPUT`. Tests mint `fingerprint({"class": "research-experiment", "id": "exp-42"})`. Parent QL-8: the edge points at the **originating research artifact** of a graduating *ungoverned experiment*.

**Unit A — brownfield / QL-8 honor epic.** Ships graduation as it works today. `originating_research_ref` **must be `fp1:sha256:…`**. The object is an ungoverned-experiment (or generic “research”) fingerprint already in the qmf-core namespace. Stage 0 `research_ref` is either forced through `fingerprint()` (making it fp1-shaped despite AD-21) or cannot be passed to `graduate_to_governed`. Citation `artifact_ref` values in CT-44 tests are `artifact://knowledge/…`, which this gate **refuses**.

**Unit B — AD-21 purist epic.** `research_ref` is a QML-ladder hash **explicitly not registry `fp1`**. Host stores it as `qml-research:<hex>` or a raw sha256 over canonical JSON. Graduation is called with that string. `graduate_to_governed` refuses. B then either forks a parallel `graduate_from_hypothesis` helper or wraps the hash in `fingerprint({...})` anyway — at which point AD-21’s “not fp1” sentence is theatre and two hypotheses can collide with experiment/Bot preimages in the same `fp1:sha256:` namespace (the only check is inequality with the *new Bot* fp1, not kind).

**Unit C — AD-17 citation-digest epic.** Skips Stage 0 (AD-7 don’t-box-in). Human authors CT-33 from a cite. Passes the Citation digest (`artifact_ref`, or a fingerprint of the cite-copy bytes) as `originating_research_ref` because AD-17 lists that alternative. Lineage “bots from STRAT-000001” joins on cite-copy identity. A’s experiment-fp1 and B’s research_ref never appear.

All three obey the sentences they cite. What diverges:

- **Shared-data shape.** One JSON field, three types: `fp1:sha256:` (experiment), QML-ladder `research_ref` (not fp1), Citation `artifact_ref` (`artifact://…` or cite-copy digest). No kind discriminator.
- **Two owners of one entity.** COMP-QML (hypothesis id) vs COMP-QMA-DAEMON (Citation / cite-copy) vs qmf-core fingerprint namespace (QL-8 experiment). FR-RES-11 and FR-RES-12 are each satisfied by a different object.
- **Identity collision.** `fingerprint()` over different `class` blobs can still mint values in one string space; CT-07 `to_ref` has no kind. Registry lookup of a research_ref as `fp1` misses or hits the wrong kind.
- **Parent overload.** QL-8’s originating research artifact was an *ungoverned experiment*. This sitting reuses the same parameter for Stage 0 hypotheses **and** Knowledge Citations without amending QL-8.

**Tightened Rule (replace AD-17 origin sentence; add AD-21 hasher law; Conventions).**

> **AD-21 (identity).** A hypothesis is identified by `research_ref` = qmf-core `fingerprint` of exactly `{ "class": "qml-research-hypothesis", "contract_format_version": RESEARCH_FORMAT_VERSION, "body": <canonical Stage 0 content> }`. The value is **fp1-shaped** so `graduate_to_governed` can consume it, and **must not** be registered as a qmf-registry kind, must not appear on the Artifact rail, and must not use any `class` already used by Bot / experiment / Citation envelopes. `class` is mandatory in the preimage so namespaces cannot collide. Canonical `body` is defined by `qml.research` (C-2 / H-1), not by the host.
>
> **AD-17 (typed origin).** `originating_research_ref` is a **tagged** value, never a bare digest:
> - `{ origin_kind: "hypothesis", research_ref }` — Stage 0 graduation;
> - `{ origin_kind: "ungoverned_experiment", fp1 }` — parent QL-8 path (existing tests).
> **Knowledge Citation digest / `artifact_ref` / `source_ref` is not a legal `originating_research_ref`.** Seed cites travel on the AD-7 handle `origin` field only. `graduate_to_governed` continues to refuse a self-edge and must refuse an untagged / unknown `origin_kind` and any `origin_kind: "citation"`.
>
> **Conventions.** `research_ref` ⊂ fp1-shaped strings with `class=qml-research-hypothesis`. `source_ref` remains CT-44 provenance. Citation `artifact_ref` remains cite-copy implementation handle (AD-9), never CT-07 `to_ref`.

---

### C-2 — AD-15 × AD-19 × AD-21 × AD-8: two hosts both legally serialize hypotheses; seed cite stays on QMA — clashing bytes, two owners, two mutation paths

**The rules as written.**

- AD-15: QML library stays pure (no I/O); **“hosts own snapshot, cite, and serialization.”**
- AD-19: QMA’s Knowledge port is read-only transport (snapshot / search / retrieve / cite-copy). QML owns Stage 0 types. A later CT-44 `source_id` over a QML-owned research root is deferred until that root exists.
- AD-21: the host serializes to an operator-configured **research root** distinct from the seed corpus; **v1 may keep host-private files**; Prevents “two hosts minting different identity bases.”
- AD-8: owners named — COMP-QML (types), COMP-QMA-DAEMON (cite-copy), research-corpus (seed bind). **No package is named as research-root owner.** Seed `root_path` is plugin/daemon load config.
- AD-7: “Single writer: the QML/host composition root.”
- Deferred table: “Second CT-44 `source_id` over the research root — No QML-owned writes yet (AD-21)” — false once any host serializes.

**Unit A — QMA daemon persistence epic.** Reads AD-15 “hosts own … serialization,” AD-8 (daemon already owns I/O / cite-copy), AD-21 (research root is just a filesystem path). Adds `research_root` next to the daemon store. On “save hypothesis,” calls `qml.research` (pure) then writes files. Optionally treats those writes as the “writes exist” trigger and binds a second CT-44 source in the same increment (Deferred’s premise is already false). Seed cites and hypothesis files both live under QMA. Listing hypotheses is a daemon query. AD-19 “QMA never authors hypotheses” is kept by not *authoring* types — QMA only serializes what QML returned.

**Unit B — QML composition-root / host-private epic.** Reads AD-19 “QMA never authors hypotheses” + AD-21 “v1 may keep host-private files” + AD-8 COMP-QML owns Stage 0. The host is the QL-1 authoring composition root (CLI / UI backend / unnamed `qml-host`). Files under `~/qmx/research/` (or a new config key). QMA never sees hypothesis bytes. `research_ref` is computed in-process from QML types. Listing is a QML research-surface API, not CT-44, not AD-9.

Both obey. What diverges:

- **Two owners of one entity.** COMP-QMA-DAEMON vs the unnamed QML host. AD-21 Prevents two identity bases but never names the single writer or the canonical bytes, so two bases are the default outcome.
- **Clashing shared-data shapes.** A stores DNA-shaped markdown/YAML (AD-18 “DNA-shaped package = hypothesis”; “host-private files”). B stores QML canonical JSON from typed models. Same LAYOUT-DEMO import → two `research_ref`s.
- **Conflicting mutation paths.** A mutates via daemon write + optional CT-44 snapshot of the research root (seed-style supersedes). B mutates by overwrite of host-private files (no snapshot chain). Re-open on the other host is `unavailable dependency` or a silent duplicate.
- **Cite vs serialize split.** Seed cite remains QMA (correct). Hypothesis serialize is the unset joint. AD-15’s one sentence assigns snapshot, cite, **and** serialization to “hosts” (plural) — that is the hole.
- **Second source_id.** A binds it because writes exist; B leaves it deferred. Agents search hypotheses via CT-44 in A and via QML surface in B.

**Tightened Rule (split AD-15 host sentence; name v1 writer in AD-8 / AD-21).**

> **AD-8 addendum.** v1 persistence owner of hypotheses is the **QML authoring composition root** (the same root that already stamps CT-06/CT-07 for bots per QL-1). Config key `research_root` is distinct from seed `root_path` and is **not** a QMA daemon / research-corpus setting. COMP-QMA-DAEMON MUST NOT write the research root and MUST NOT bind a second CT-44 `source_id` in v1.
>
> **AD-15.** QML stays pure. **QMA hosts** own seed `snapshot` / `search` / `retrieve` / `cite`. **The QML authoring composition root** owns hypothesis serialization and listing. Do not say “hosts own snapshot, cite, and serialization” as one clause.
>
> **AD-21.** The host is a **blob store** keyed by `research_ref`. It persists only the canonical bytes `qml.research` returned. It must not invent a parallel schema (no DNA-file fork, no host-private markdown as identity basis). Filename / listing scheme: content-addressed `{research_ref}` with no occurrence fields. Second CT-44 source over this root stays deferred even though files exist — host-private ≠ KnowledgeSource.

---

### C-3 — AD-17 × AD-7 × AD-15: three origin channels, two writers, two mutation times — “bots from this seed” cannot join

**The rules as written.**

- AD-7: origin is optional handoff metadata, **single writer = QML/host composition root**, **single home = QMA-owned non-`fp1` field** on the `dev`-zone candidate / StrategyHandle: `{ source_ref, snapshot_ref, locator }` citing an existing Knowledge Citation. Must not enter CT-33/CT-34/`fp1` preimage. QMA may copy at register only if the host supplied it. Ungoverned Python may skip Stage 0.
- AD-17: graduation **links `originating_research_ref`** (research_ref **or Citation digest**) and the host stamps a **`promoted-from` CT-07 edge**.
- AD-15: Stage 0 **is never cited by governed evidence**.
- Prior adversarial C-2 (applied last gate): CT-07 predecessor edges for *knowledge* origin refused in v1. AD-17 reopens them via Citation digest + mandatory CT-07 stamp.

**Unit A — hypothesis-lineage epic.** Every governed mint from the mill goes through `graduate_to_governed`. CT-07 `to_ref` = `research_ref`. Handle `origin` also set from the hypothesis’s seed cites (AD-7). “Bots from STRAT-000001” = join Bot → CT-07 → hypothesis → cite locators. Stage 0 **is** cited by a governed lineage record (tension with AD-15).

**Unit B — skip-Stage-0 cite-then-author epic.** Reads AD-7 skip + AD-17’s Citation-digest alternative. Calls `gate_registration` (no graduation) **or** `graduate_to_governed(originating_research_ref=citation_digest)`. Handle `origin` = the cite triple. No `research_ref` exists. CT-07, if stamped, points at cite-copy identity (an object AD-9 forbids as an Artifact-rail hit, now living in registry lineage). “Bots from STRAT-000001” = filter handle.origin.locator.

**Unit C — origin-field-only epic.** Reads prior-gate origin law + AD-15 “never cited by governed evidence.” Uses `gate_registration` only. Stamps AD-7 `origin` on the handle. **Refuses** to stamp CT-07 toward any non-kind fingerprint. `graduate_to_governed` is unused for mill graduation (kept for ungoverned-experiment path only).

All three obey some AD-7/AD-15/AD-17 sentence. What diverges:

- **Two owners of one conceptual field (“where did this bot come from”).** QML host (CT-07 content) vs QMA (handle `origin` copy at register). Neither refuses the other; both can be present, one, or none.
- **Clashing shapes.** `{ origin_kind, research_ref }` vs Citation digest vs `{ source_ref, snapshot_ref, locator }` vs absent.
- **Conflicting mutation paths.** A mutates origin at graduation time (content-addressed, changes if hypothesis body changes). B mutates at register-as-candidate time (QMA copy). C never writes CT-07. Re-cite / re-pin rewrites B’s metadata and A’s fingerprintable edge differently.
- **AD-15 vs AD-17.** If CT-07 `to_ref` is a “cite by governed evidence,” A violates AD-15; if it is not, C’s refusal is optional and A/B still fork.

**Tightened Rule (replace AD-17 lineage paragraph; keep AD-7 origin law; resolve AD-15).**

> **AD-7 (unchanged law, restated).** Seed origin is **only** the handle field `{ source_ref, snapshot_ref, locator }` citing an existing Citation. Single writer: QML authoring composition root. QMA copies if supplied; never invents. Not in `fp1` preimage. **No CT-07 edge to a Knowledge Citation.**
>
> **AD-17.** Graduation to a hypothesis uses `origin_kind: "hypothesis"` (C-1). Host stamps `promoted-from` CT-07 with `to_ref = research_ref` (fp1-shaped, non-kind per AD-21). That edge is **lineage, not governed evidence**: CT-32 and seats continue to cite only the Bot `fp1` (AD-15 holds). Graduating an ungoverned experiment uses `origin_kind: "ungoverned_experiment"` and is a separate call path.
>
> **Skip law.** Skipping Stage 0 (ungoverned Python **or** QML `gate_registration` without a hypothesis) means **no** `originating_research_ref` and **no** mill CT-07. Optional AD-7 `origin` may still cite a seed. Do not mint a fake hypothesis to satisfy graduation.

---

### C-4 — AD-15 [PROPOSAL] QL-1 four-surface vs inherited QL-1 three-surface: factory can legally put Stage 0 in three homes

**The rules as written.**

- Inherited QL-1 (ratified, DEC-0184): QML’s whole surface is **three** thin things — (1) CT-33/CT-34 author types, (2) QL-7 protocol, (3) QL-8 gate. QML mints no CT-*. Local contracts ride AD-5’s second ladder (QL-7/QL-8 already do).
- Local AD-15: QML grows a **research** module; **[PROPOSAL]** parent QL-1 four thin things. Mechanism already legal; enumeration is what needs amendment.
- Inherited table: parent ADs bind read-only; a local rule that would treat Stage 0 as a third governed bot half is a **conflict, not an override**. Proposed amendments are “not silent overrides.”
- Open question: “Confirm proposed QL-1 four-surface amendment vs leaving Stage 0 undocumented against parent text.”
- AD-8: COMP-QML owns Stage 0 types. AD-19: QMA does not own meaning.

**Unit A — proposal-honoring COMP-QML epic.** Public `qml.research` submodule, own `RESEARCH_FORMAT_VERSION`, exported from the `qml` wheel. Stories under COMP-QML. Treats the QL-1 amendment as a documentation-factory follow-up, not a build gate.

**Unit B — ratified-QL-1 purist epic.** Parent still says three. Putting a fourth public surface on the `qml` distribution would silently override QL-1. B therefore **does not export** Stage 0 from `qml`:

- B1: host-private schema outside the wheel (AD-21 “v1 may keep host-private files”);
- B2: “helpers under (1)” — extra fields on CT-33 author types that graduation strips (the dishonest reading the legality note warned against, still available);
- B3: types in research-corpus / qma-core as parse DTOs over cited bytes (AD-5 adapter conventions; QMA “doesn’t author,” it *projects*).

A and B both claim parent-consistency. What diverges:

- **Two (or three) owners of Stage 0 types.** COMP-QML public API vs host-private vs QMA adapter DTOs.
- **Clashing shapes.** Import `from qml.research import Hypothesis` vs a YAML DNA package vs a QMA view-model. `research_ref` hasher has no single module to call.
- **QL-1 as build gate vs commentary.** Open question leaves the factory free to pick. Documentation-factory may amend QL-1 after B has already shipped types in QMA; then A’s module is a second schema.

**Tightened Rule (AD-15 build gate; close the open question).**

> **AD-15.** Stage 0 types **live in `qml.research`**, a public submodule of the `qml` distribution, on an AD-5 second-ladder contract (`RESEARCH_FORMAT_VERSION`, independent integer from QL-7/QL-8). They are **not** CT-33 helpers, **not** QMA/qma-core types, **not** host-private schemas. Hosts consume the module; they do not fork it.
>
> **QL-1 amendment is a documentation-factory obligation, not an implementation veto.** Factory implements `qml.research` now against this child AD. Until the parent sentence is amended, the honest reading is: mechanism already legal (same as QL-7/QL-8); the enumeration is stale. **It is not legal** to preserve the three-count by hiding Stage 0 in QMA or in host-private DNA files.
>
> Close the open question: do not ship a “leave Stage 0 undocumented” option.

---

## HIGH

### H-1 — AD-21 × AD-15: two hosts disagree on Stage 0 format version and canonical bytes

**Unit A — qml.research v1 types.** Pins `RESEARCH_FORMAT_VERSION = 1` inside hashed content. Canonical JSON, sorted keys, types in the wheel. Restore across versions → `unavailable dependency`.

**Unit B — host-private DNA files.** Reads AD-21 “v1 may keep host-private files” and AD-18 “DNA-shaped package = hypothesis.” Serializes `graph.yaml` + markdown matching Stats schema. Format version implicit (absent or “0”). Hasher is sha256 over file trees (include/exclude unset — AD-4 exists for seed snapshots, not for research roots). Two hosts with different ignore lists mint different `research_ref`s for the same hypothesis.

AD-21 Prevents “two hosts minting different identity bases” but the Rule never freezes serializer, field preimage, or the version constant’s owner. “The same path QL-7 and QL-8 already use” is readable as **one shared integer** (A′ bumps Stage 0 and breaks QL-7 restore) or **independent contracts** (B′).

**Tightened Rule.**

> `RESEARCH_FORMAT_VERSION` is an independent constant in `qml.research` (not QL-7 `protocol` / QL-8 `CONFORMANCE_FORMAT_VERSION`). Canonical bytes = the module’s fingerprint preimage (C-1). Additive optional fields require a version bump; unknown version is `unavailable dependency`. Host-private files, if any, are caches of those bytes, never an identity basis. Research-root include/exclude is not a second AD-4: the host stores one blob per `research_ref`.

---

### H-2 — AD-1 × AD-9 × AD-14 × AD-21: KnowledgeHit vs hypothesis — when viewing LAYOUT-DEMO mints identity, and how it leaks into Library

**Unit A — QML research-surface epic.** Opening LAYOUT-DEMO is an **authoring act**: cited bytes + vocab helpers → `qml.research` document → `research_ref` persisted (C-2). Research pane lists hypotheses. Federated Library DTO stays KnowledgeHit | ArtifactHit.

**Unit B — projection epic.** Reads AD-14 “Stage 0 hypothesis view of LAYOUT-DEMO” + AD-1 “display aliases never mint a third identity” + AD-9 (hypotheses are not this DTO). B never mints `research_ref` in slice 0. The “hypothesis view” is a UI/librarian projection over a KnowledgeHit (`source_ref, snapshot_ref, locator`). Graduation uses Citation digest (AD-17 as written). Client may badge the KnowledgeHit as “hypothesis” without a new `hit_class`.

Both obey. What diverges: FR-RES-11 (“identity is `research_ref`”) is optional in B; two “open STRAT-000001” acts in A mint one id (content hash) or two if cites/occurrence leak into preimage (H-4 below); agents federate B’s badged KnowledgeHits as if they were research objects; Workflows (AD-13) cannot take `research_ref`s that B never created.

**Tightened Rule.**

> Viewing cited seed bytes is a **read-only projection** (slice 0). It does **not** mint `research_ref`. A hypothesis exists only after an explicit QML authoring save that returns canonical bytes (C-2). Display aliases on KnowledgeHits MUST NOT say “hypothesis” / “research candidate.” Federated DTO unchanged. Librarian/json-render may render the projection; they must not persist it (AD-10 / AD-12).

---

### H-3 — AD-18 × AD-20 × QL-5: confluence homonym — two types named the same, two owners

AD-18 names the homonym (“Stage 0 confluence = graph composition; CT-34 Confluence = fingerprinted leg-set”) but does **not** freeze the Stage 0 identifier. Conventions tell people what to *say*, not what to *export*.

**Unit A — mill-vocab epic.** `qml.research.Confluence` / JSON key `confluence` (Stats `graph.yaml` composition). Graduation maps that object into CT-34 + Python WHEN.

**Unit B — QL-5 epic.** `Confluence` is only CT-34. Stage 0 field is `graph`. Stories titled “confluence” implement registry kinds. A Stage 0 document with key `confluence` is either rejected or treated as a CT-34 fingerprint list (illegal: Stage 0 must not cite registry kinds as its meaning graph — AD-6 / AD-15).

Agents “add confluence” mint the wrong artifact. Two modules export `Confluence`. Fingerprints and UI routes collide on the noun.

**Tightened Rule.**

> Stage 0 type/field name is **`graph`** (composition: Boolean / temporal / lifecycle). **Never** `Confluence` / `confluence` in `qml.research` identifiers. CT-34 remains **Confluence**. Product copy follows AD-18; code identifiers are now closed, not advisory.

---

### H-4 — AD-7 × AD-10 × AD-14 × QL-1 don’t-box-in: ungoverned Python vs Stage 0 as a QML toll booth

**Unit A — research-first QML host.** Bot-creation in QML always starts at Stage 0. `graduate_to_governed` is the only Stage 1 mint QML exposes (the function requires `originating_research_ref`). Don’t-box-in is honored **only** at the QMB tunnel: if you want Python without a hypothesis, you never open QML. Slice 0 view becomes the start of the authoring wizard (AD-10 forbids a *mandatory* wizard, but A’s wizard is “just the QML surface”).

**Unit B — three-door epic.** Reads AD-7 skip + QL-1 don’t-box-in + existing `gate_registration` (no origin) + `admit_ungoverned_tunnel`. (1) QMB ordinary Python; (2) QML Stage 1 `gate_registration` with no hypothesis; (3) Stage 0 → `graduate_to_governed`. Slice 0 view is optional.

Both obey. Governed bots from A always have mill lineage; B’s governed bots often have none. UI/agent “create bot” is two products. A can claim AD-14 slice 0 as proof Stage 0 is in the happy path; B can claim AD-10 / don’t-box-in as proof it must not be.

**Tightened Rule.**

> Three legal entries, none a toll booth for the others: (1) QMB ungoverned Python — zero QML; (2) QML `gate_registration` — CT-33 + Python, no Stage 0; (3) Stage 0 save then `graduate_to_governed` — requires `research_ref`. QML UI/agents MUST expose (2) without opening Stage 0. Slice 0 is a projection (H-2), not a wizard (AD-10).

---

### H-5 — AD-19 × AD-16 × AD-5: QMA vs QML both parse dictionary / LAYOUT-DEMO meaning

**Unit A — QML vocab-helpers epic.** AD-16 / AD-19: parse / validate / lookup / `(file_path, id)` / class taxonomy / F labels live in `qml.research`. QMA returns bytes + locators only.

**Unit B — research-corpus adapter epic.** AD-5: path/heading conventions live in the adapter; AD-4 include set already names `dictionary/` and `strategies/`. B extracts 12 fields, collision index, and `entry_hypothesis` into adapter search metadata so literal search can hit field values. Still returns locators (CT-44 frozen), but the **meaning implementation** is in QMA. Slice 0 view that trusts adapter metadata vs QML parse can disagree on class / F / collisions.

Two parsers of one markdown family; honesty envelope forks.

**Tightened Rule.**

> Dictionary meaning (12 fields, collisions, eligible roles, class taxonomy, F/H labels) is computed **only** by `qml.research` helpers over cited or seeded bytes. The adapter’s job is bytes + locators + AD-4 include/exclude. It MUST NOT emit structured dictionary/DNA fields, class labels, or F maps. CT-44 search remains literal over file bytes.

---

## MEDIUM

### M-1 — AD-21 preimage: seed cites inside vs outside `research_ref`

**Unit A** hashes cited `{ source_ref, snapshot_ref, locator }` into hypothesis `body` (the hypothesis *is* about those bytes). Re-cite / new snapshot mints a new `research_ref` for unchanged meaning.

**Unit B** treats cites as AD-7 origin / host envelope (occurrence-adjacent), excluded like writer/created-at. Same body, two ids across hosts; graduation joins break.

**Close:** hashed `body` includes **cite identities** (source_ref + locator + snapshot_ref) as semantic content; occurrence/writer/created-at stay excluded. Re-pin of the *same* retained cite-copy does not change `research_ref`; a different snapshot/locator does.

### M-2 — AD-17 “informal collapse” × AD-7 no auto-mint: graph → Python WHEN codegen

**Unit A** ships a graduation button that generates Python WHEN from Stage 0 graph operators (`ALL` / `sequence` / `within`) and CT-34 legs from bindings — “human-approved QML authoring.”

**Unit B** treats collapse as human rewrite only; graph is documentation; codegen would be silent DNA→artifacts (AD-7 Prevents).

**Close:** v1 graduation does **not** compile `graph` → Python or bindings → CT-34. Host presents the hypothesis; a human (or human-approved authoring session) supplies declaration + logic. Graph remains meaning on Stage 0.

### M-3 — Hypothesis mutation: overwrite vs append-only

AD-21 content-hash identity; Conventions “hypothesis mutation through QML/host”; no version graph.

**Unit A** overwrite in place; `research_ref` changes; existing CT-07 `to_ref` dangles.

**Unit B** append-only (Bot-like `branches-from`); every edit is a new hypothesis.

**Close:** hypotheses are content-addressed and **append-only**. An edit mints a new `research_ref`. Host may keep a display pointer “current” that is not identity (mirror AD-30 current-pointer, QML-local, not a registry kind). Graduation pins the specific `research_ref`.

### M-4 — AD-12 / AD-10 presenters as accidental hypothesis cache

**Unit A** json-render / MCP Apps / librarian emit ephemeral views of projections (H-2).

**Unit B** stores last-rendered Stage 0 JSON in `ui://` or Mission artifacts as “draft schema” (prior-gate M-1 revived).

**Close:** presenters hold no hypothesis cache; re-query host by `research_ref` or re-project from cite. Librarian output is chat/UI-only, not a StrategyHandle input type.

---

## Closures that held

- No legal pair mints `COMP-LIB`, `LIBRARY_KINDS += strats`, or CT-33 from `graph.yaml` without an explicit AD conflict.
- No legal pair gives QMA an execution tool, writes Stats from QMA, or `import qmb` from QMA.
- Federated DTO remains two classes (`KnowledgeHit` | `ArtifactHit`); `hit_class: "strats"` is banned; hypotheses are not a third rail (AD-1 / AD-9). The leak is **client aliasing** (H-2), not a third persisted class.
- Cite-copy is still not an Artifact-rail hit (AD-9) — until AD-17’s Citation-digest alternative is used as CT-07 `to_ref` (C-1 / C-3). Closing those restores this closure.
- Six confidence keys / `source_id=strats` freeze / browse `snapshot_ref` pin / include-exclude as adapter config (prior-gate C-3, C-4, H-3) still hold for the **seed** path.
- Don’t-box-in at the QMB tunnel holds; the hole is whether QML Stage 1 also skips (H-4).
- GAP-0085 / GAP-0073 / GAP-0063 remain deferred without forcing a v1 schema fork if H-5 / M-2 are applied.

## Apply order

1. Typed `originating_research_ref` + fp1-shaped non-kind `research_ref` (C-1). Stop Citation digest as graduation origin.
2. Single origin story: CT-07 → hypothesis or ungoverned experiment only; seed cites stay on AD-7 handle (C-3). Re-close prior-gate “no CT-07 to knowledge.”
3. Name the v1 serializer: QML composition root blob store; QMA does not write hypotheses; split AD-15’s host sentence (C-2).
4. Pin `qml.research` as the only Stage 0 home; close the QL-1 open question (C-4).
5. Freeze `RESEARCH_FORMAT_VERSION` + canonical bytes (H-1); projection ≠ identity (H-2); rename Stage 0 `graph` (H-3); three entry doors (H-4); QML-only dictionary parse (H-5).
6. M-1..M-4 as sentences under AD-21 / AD-17 / AD-12.

Do not freeze `qml.research` public types, `research_root` persistence, or `graduate_to_governed` mill wiring until C-1..C-4 are amended into the spine.
