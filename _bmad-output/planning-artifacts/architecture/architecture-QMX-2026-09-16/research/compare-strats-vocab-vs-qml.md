# STRATS vocabulary vs QML / CT-33 / CT-34

**Superseded adoption posture:** § “Adoption posture (ontology only)” below still says meaning lives in QMA knowledge. Operator restart 2026-09-16 moved meaning types into **QML Stage 0**; QMA CT-44 remains cite transport only. See `../ARCHITECTURE-SPINE.md` AD-15/AD-16/AD-19 and `../QML-EXPANSION.md` §7. Ontology comparison table remains useful.

Date: 2026-09-16  
Scope: library/ontology comparison only (no Hermes agentics, no n8n, no Gemini, no video pipelines, no crew roles).  
Primary STRATS recovery: `research/recovery-5678-assistant.md` + live Stats locks (`schema/strategy-dna.md`, `schema/graph.yaml.md`, `dictionary/README.md`).  
QML/CT: integration-inspect `qml/declaration/{bot,confluence}.py`, `qml/generation/gaps.py`, `docs/contracts/ct-33-bot-definition.yaml`, `docs/contracts/ct-34-confluence.yaml`.

## Verdict (honest)

| Side | Richer on |
|---|---|
| **QML / CT-33 / CT-34 / QMF** | Governed **identity** (`fp1`), **registry kinds**, **footprint completeness**, **parameter space + units**, **two-layer conformance**, **logic-reference** (Python distribution identity), **producer bindings** (CT-16/CT-17), closed **exit-intent** subset for Book intents, version-graph / promote discipline. |
| **STRATS (DNA A–I + dictionary + graph)** | **Meaning**: role-neutral primitives, eligible-role flexibility, source-faithful **evidence/claims**, **exit completeness labels (F)** without inventing, **unknowns (H)**, **dependencies/transfer (G)**, Boolean/temporal/**stateful graph operators**, candidate **class** taxonomy (`entry_hypothesis` etc.), human lenses that keep invalidation ≠ stop and trigger ≠ order. |

They are complementary planes, not competing ontologies for the same artifact:

1. **Knowledge** — STRATS DNA / dictionary / `graph.yaml` (portable files).
2. **Authoring** — QML CT-33 + CT-34 + Python WHEN.
3. **Empirical evidence** — QMB CT-32.
4. **Deployment** — QMN paper|live after human promote.

`graph.yaml` is knowledge, never a QMX executor. CT-34 declares *what* is consumed and *which role*; WHEN lives in Python in V1. GAP-0085 typed mechanism nouns (`EntryMechanism`, `ExitMechanism`, …) stay **unminted**.

## Sample dictionary proof (STRATS meaning depth)

From `dictionary/market-structure-and-location/locations-and-structure.md`:

- **`swing-high`** — 12-field primitive: aliases, boundaries (≠ resistance, ≠ session high), recognition (`N`-bar fractal), parameter provenance (`published-convention` / `source-stated` / `unresolved`), **eligible roles** `location | trigger | invalidation | context | confirmation`, transfer notes, uncertainty variants.
- **`liquidity-sweep`** — event (not a level); roles `trigger | confirmation | context`; sweep-vs-breakout unresolved; “smart money intent” marked non-transferable as fact.

Neither concept exists as a QML/CT noun. At best a human later binds a CT-16/CT-17 producer (or plain Python) and cites it on a CT-34 leg with role `level|trigger|confirmation|filter`. The dictionary’s **invalidation / context / target** eligible roles have **no** CT-34 home.

## Informal role bridge (handoff aid only — not a contract mint)

| STRATS human / binding lens | Closest CT-34 leg role | Gap |
|---|---|---|
| location / level | `level` | approx |
| trigger | `trigger` | approx |
| confirmation | `confirmation` | approx |
| context / filter / veto / gate | `filter` | filter is “suppressing condition”; STRATS also has scores, regimes, ranking |
| confluence | *(composition of legs / graph)* | STRATS: confluence = graph ops; QML: confluence = **registry artifact** of legs |
| invalidation | *none* | Book / DNA F / Python — not a CT-34 role |
| exit / stop / target / management | *none on CT-34* | CT-33: optional `permitted_exit_intents` ⊂ `{close_full, tighten_protective_stop}`; source F stays STRATS |
| arming / reset / cooldown / re-entry | *none* | DNA E / `lifecycle` or Python |
| entry order semantics | *none on declaration* | `entry` always permitted; trigger ≠ order stays knowledge/Python |

## Concept table

| STRATS concept | Exists in QML / CT-33 / CT-34? | How (or missing) | If adopted globally, which QMX layer should own it |
|---|---|---|---|
| **Primitive dictionary** (role-neutral “what exists”) | **No** as a registry kind | Stats `dictionary/` families + 12 fields; QMA cites files via CT-44 locator. Not CT-16 (indicators) and not CT-34. | **QMA knowledge** (CT-44 snapshot/cite of Stats). Do **not** mint a STRATS registry kind. |
| **Dictionary entry fields** (aliases, boundaries, recognition, eligible roles, transfer, uncertainty, evidence/status) | **No** | QML has no parallel prose ontology. CT-16 configures *arithmetic producers*, not trading-concept meaning. | **QMA knowledge** / Stats corpus. Authoring may *cite*; must not rewrite into `fp1`. |
| **Eligible roles on a primitive** (location, trigger, invalidation, context, confirmation, target, …) | **Partial** | CT-34 closed-and-addable: `level \| trigger \| confirmation \| filter` only. Invalidation/target/context-as-regime not roles. GAP-0085 nouns refused. | **Knowledge** owns the open eligible-role list. **QML** owns only the closed CT-34 enum (further roles = contract-format mint). |
| **Role binding** (role + pair/TF/session/direction/timing/params for *this* candidate) | **Partial** | CT-34 leg: `role` + producer binding and/or child confluence + optional exact params. Missing: session/direction/timing/bar-close as first-class binding fields; those live in Python or footprint streams. | **QML** for governed binding shape that enters `fp1`. **Knowledge** for source-faithful binding prose (DNA D) until authored. |
| **DNA A — Identity & classification** (`complete` / `entry_hypothesis` / `fragment` / `descriptive_pattern` / `composite`) | **No** (different identity) | CT-33 identity = six semantic groups + format version + at-birth refs → `fp1`. No candidate-class enum. Entry-only bot is legal via **empty** `permitted_exit_intents`, not via `entry_hypothesis`. | **Knowledge** owns class taxonomy. Optional non-`fp1` handoff metadata on QMA StrategyHandle/`origin` only — never into CT-33 preimage. |
| **DNA B — Evidence map** (quotes, frames, claim-to-rule, evidence class) | **No** on bot | QMF has CT-10/11 source-observation/evidence-persistence and QMB CT-32 performance evidence — different plane (empirical / platform), not source-faithful strategy claim maps. | **QMA knowledge** (STRATS `evidence/`). Empirical runs → **QMB**. Do not collapse B into CT-32. |
| **DNA C — Primitive references** | **No direct** | CT-34 cites producers by fingerprint or template, or nested confluence `fp1` — not dictionary kebab slugs. Spine: do not auto-map primitive → CT-16. | **Knowledge** keeps slug/(file_path,id). **QML** only after human author chooses a producer. |
| **DNA D — Candidate-specific bindings** | **Partial** | See role binding row. | Split: meaning in **Knowledge**; governed cites in **QML**. |
| **DNA E — Logic graph** (`ALL`/`ANY`/`NOT`/`K_OF_N`/`sequence`/`within`/`arming`/`reset`/`cooldown`/`re-entry`) | **No as declaration** | Explicitly deferred: condition/WHEN in Python V1 (`FORBIDDEN_CONDITION_FIELDS` on confluence). CT-34 may opt into order-significance of legs; that is not the operator algebra. | **Knowledge** owns `graph.yaml`. **QML** owns Python logic_reference that *implements* WHEN. Never compile graph → executor. |
| **Graph node kinds** (`primitive` \| `operator` \| `state` \| `action` \| `condition`) | **No** | CT-34 has legs, not graph nodes. CT-33 has logic_reference blob identity, not an AST. | **Knowledge**. |
| **Lifecycle slots** (arming, reset, cooldown, re-entry; may be `unresolved`) | **No** | Absent from CT-33/34. May appear only inside referenced Python. | **Knowledge** (DNA E/F companion). Runtime behavior → Python under **QML** authorship, Book/QMN for live. |
| **DNA F — Exit completeness** (invalidation, stop, targets, exit, management) + labels `source_defined` / `external_policy` / `deliberately_open` / `unresolved` | **Mostly missing** | CT-33 forbids `exit_logic`; exit behaviour is Book-keyed by `strategy_family_id`. Only **intent kinds** `close_full` \| `tighten_protective_stop` (may be empty). No invalidation≠stop split, no source F labels, no invent-ban as a CT field. | **Knowledge** owns F labels and source truth. **QMF/Book (risk)** owns live exit policy. **QML** only declares permitted intents. Never invent F to “complete” a bot. |
| **Invalidation vs stop (split)** | **No** | Not modeled on CT-33/34. | **Knowledge**; live protective stop → Book/QMN. |
| **Trigger ≠ order / entry semantics** | **Partial** | CT-33: `entry` always permitted, never listed. Order type/price basis not declaration fields. | **Knowledge** + **QML** Python. Venue commands stay out of CT-33 (`FORBIDDEN_BOT_FIELDS`). |
| **Four pillars** (location, context/filter, trigger, confirmation) | **Partial** | CT-34 roles cover three pillars + `filter`; STRATS “confluence” pillar ≠ CT-34 kind name collision. | **Knowledge** for human review lenses. **QML** for leg roles when authoring. |
| **Confluence as graph composition** (AND / K_OF_N / sequence) | **Name collision — different meaning** | STRATS: composition operators. QML CT-34: **reusable registry artifact** = set of role-tagged producer legs, cited by CT-33. | Keep both names carefully. Operators → **Knowledge**/Python. Artifact kind → **QMF registry** authored via **QML**. |
| **DNA G — Dependencies & assumptions** (venue, bar construction, transfer caveats) | **Partial** | Footprint: streams, calendars, producer bindings, derived warm-up. Not the full transfer/caveat prose model. | **Knowledge** for source assumptions. **QML** footprint for governed consumption manifest. |
| **DNA H — Unknowns & ambiguity** | **No** | STRATS first-class searchable holes. QML refuses invalid/unsupported/unavailable; does not store “unresolved chart value” as ontology. | **Knowledge**. |
| **DNA I — Logical lineage** (parents, variants, composites, semantic delta) | **Different lineage** | CT-33: AD-30 `branches-from` / `continues-performance`; at-birth parent refs; CT-07 edges elsewhere. Spine: STRATS I ≠ CT-07 ≠ ExperimentSpec branches. | **Knowledge** for research lineage. **QMF/QML** for artifact version graph. **QMB** for experiment lineage. Do not merge. |
| **Research status / no-claim-of-edge** | **No on CT-33** | QMB CT-32 holds governed performance results after runs. | **Knowledge** (claims) vs **QMB** (measured). |
| **Fingerprint identity (`fp1`)** | **Yes — QML/QMF richer** | Content-addressed CT-33/34; occurrence header fields excluded; stable id derived from fingerprint. STRATS uses stable strategy ids/slugs, not `fp1`. | **QMF registry** + **QML** authoring. Knowledge locators must not pretend to be `fp1`. |
| **Footprint + completeness law** | **Yes — QML richer** | Transitive union of confluence leg producers ⊆ bot footprint; hosts supply only declared footprint. | **QML** / **QMF**. |
| **Parameter space + canonical assignment + unit-kinds** | **Yes — QML richer** | B-8-shaped space with AD-40 units; defaults = canonical assignment; promote-tuned mints new bot. STRATS has params/provenance but not this governed schema. | **QML** (declaration) + **QMB** (optimizer consumes). Source param provenance stays **Knowledge**. |
| **Two-layer conformance (declaration + sandboxed execution)** | **Yes — QML richer** | QL-8 / DEC-0178; mint only if both pass. STRATS has no conformance gate (by design — knowledge library). | **QML** (+ host). |
| **Logic reference** (distribution + version + source-manifest fingerprint) | **Yes — QML** | Two-artifact bot (declaration + Python). STRATS `graph.yaml` is not that logic half. | **QML**. |
| **Producer binding** (pinned CT-16/17 or template) | **Yes — QML/QMF** | Legs and footprint use producers. Dictionary primitives are not producers. | **QMF** (CT-16/17) authored into bots via **QML**. |
| **Strategy-family id** (exactly one opaque key) | **Yes — QML** | Book exit policy keyed by family. STRATS has methodologies/styles as mini-KBs/tags — not the same token. | **QML** / Book. Mapping from STRATS methodology tags is human authoring, not auto. |
| **GAP-0085 mechanism nouns** | **Explicitly absent** | `EntryMechanism`, `ExitMechanism`, `Filter`, `InvalidationRule`, `PositionRule`, `SessionRule` refused; write-owner `qml-host`, later. CT-34 `filter` role ≠ GAP-0085 `Filter` type. | Leave deferred. If ever minted: **QML** write-ownership — still not STRATS import. |
| **Sources / mini-KBs / catalog / lineage folders** | **No as CT-33/34** | Portable Stats tree; QMA snapshots configured include set. | **QMA knowledge**. |
| **Confidence dimensions** (extraction, rule explicitness, …) | **On knowledge rail** | CT-44 / research-corpus freeze (six dims); not CT-33 fields. | **QMA knowledge**. |

## Richness notes (do not flatten)

### Where QML is ahead
- Deduplication and comparability by construction (`fp1`).
- Registration as a ticket (conformance), not “markdown clarity.”
- Consumption safety (footprint completeness; no undeclared producers).
- Separation of declaration vs executable Python vs Book exits vs sizing/venue (forbidden on CT-33).
- Reusable confluence *artifacts* across bots without copying prose.

### Where STRATS is ahead
- Saying what a **swing-high** or **liquidity-sweep** *is*, including boundaries and unresolved variants.
- Preserving **holes** (F/H) without forcing completion.
- Temporal/stateful **strategy meaning** (`sequence`, `within`, arming lifecycle) as first-class knowledge.
- Source evidence and promotional-claim hygiene separate from edge.
- Role flexibility beyond four leg roles (especially **invalidation** and **target**).

### Naming trap
**“Confluence”** means different things. In STRATS recovery/DNA, confluence is usually **graph composition**. In QMX, **CT-34 Confluence** is a **fingerprinted leg-set registry kind**. Treat as homonyms in docs and UI.

## Adoption posture (ontology only)

- Do **not** recommend importing STRATS into CT-33/34 by auto-mint.
- Do **not** mint GAP-0085 to mirror STRATS roles.
- Do **not** make dictionary primitives into CT-16 by import.
- Global ownership if concepts are “adopted” into QMX product language:
  - **Meaning, evidence, unknowns, F labels, graph operators, dictionary** → **QMA knowledge** (Stats as CT-44 `plain_file_library`).
  - **Governed bot declaration, CT-34 legs, footprint, conformance, logic bytes** → **QML** (kinds owned by **QMF registry**).
  - **Measured performance / experiment evidence** → **QMB**.
  - **Live/paper exit & sizing policy** → Book / **QMN** path, keyed by family — not STRATS F invention.
