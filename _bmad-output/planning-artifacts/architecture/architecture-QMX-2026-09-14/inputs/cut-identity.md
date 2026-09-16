# Cut — Shared Library identity

**Topic:** identity (Shared Library fp1/registry kinds vs work-environment / study / candidate-databank projections).  
**Checkout:** `main` `430fb7d`. **Product inspected:** `integration` `1b451a848d897e42f6e2c7fd9f2ea86fab7295f2` via `git show` / `git ls-tree` only. No branch switch, commit, or implementation.  
**Leads (not authority):** `workroom/research/2026-09-14-qmf-qml-understanding.md`, `2026-09-14-backend-baseline.md`, `2026-09-14-ui-feature-route.md`, sitting inputs `code-qmf.md` / `code-qmb.md` / `code-qma.md` / `corpus-factory-map.md`.  
**Standing:** do **not** mint a second identity store. One `fp1` recipe (`qmf-core`). One record catalog (`qmf-registry` CT-06/07/09 through `qmf-data`). Display names are UX.

Evidence levels: `user-intent` | `documented-design` | `source-inspected`. Class/test existence is not end-to-end proof. Contract YAML `defined-unwired` / “no code exists” is stale where matching integration source exists.

## Compact classification

| Object (product language) | Identity today | Class | Missing | Notes |
|---|---|---|---|---|
| Bot declaration | CT-33 `bot-definition` fp1 | **reuse** | composition-root mint/persist (**wiring**) | QML authors content; registry owns kind |
| Logic source-manifest | field of CT-33 `logic_reference` | **reuse** | — | Code change mints a new Bot; not a sibling kind |
| Confluence | CT-34 fp1 | **reuse** | same mint path (**wiring**) | Cited by bot, fingerprint-ascending |
| Strategy family | CT-06 dated metadata kind (no new CT) | **reuse** | — | Opaque key on every bot; no authority |
| Book version | CT-22 `BookDefinition` fp1 | **reuse** | live/paper bind (**wiring**) | UI edit → new version; `branches-from` |
| BMS version | CT-27 `BmsDefinition` fp1 | **reuse** | same | `BmsInstanceId` is derived, not minted |
| Binding epoch | CT-28 binding-record fp1 | **reuse** | QMB replay mints per run; live = node | Re-bind ≠ new Bot |
| Dataset split | CT-12 `split_id` = manifest fp1 | **reuse** | QDM-like browse UX (**function** on QMB, not identity) | Seal/purge/embargo in identity |
| Source observation / window | CT-10 + store admit on fp1 | **reuse** | — | Bitemporal; corrections append |
| Performance / result | CT-32 container fp1 + AD-12 label | **reuse** | CLI/UI consume chart-series (**wiring**) | QMB fills; charts excluded from fp1 |
| QMB resolved run-config | **derived** fragment, lineage to CT-22/27 | **reuse** | — | DEC-0160: never a new kind |
| QMB Study (`study_fp`) | `StudyArtifact` fingerprint, cited on trial labels | **reuse** + **connect** | not a CT-06 kind; Library must **cite**, not re-kind | Optimize campaign, not a workspace |
| ExperimentSpec | CT-47 qma-core fp1 (`spec_fp1`) | **reuse** + **connect** | persist maps through daemon writer (**wiring**); docs stale | Not a CT-06 kind today |
| Experiment Ledger | one notebook per `spec_fp1` | **reuse** + **connect** | same persistence gap | Occurrence/provenance, not a second id |
| Dev-zone candidate | CT-06 addable kind `qma-dev-zone-candidate` | **reuse** | durable `RegistryPersistence` vs in-memory `Registrar` (**wiring**) | Sole QMA parent write |
| Candidate **databank** | **query** over ledger + as-of + staging | **connect** (AD-14) | saved-view predicates (**wiring**); no store | SQ databank is a donor **shape** |
| Work-environment tab | **not a kind** | **connect** (UX projection) | session chrome (**function**, UI) | Must cite fps; CT-46 is compute, not a tab |
| Graph Template / Skill / Routine | QMA plugin/operator records (fp1 via `content_address`) | **reuse** | — | Procedures, not Library identity of bots |
| Promotion card | reserved CT-06 `promotion-occurrence-card` | **reuse** | human signer path | Canonical; journal holds pointer only |
| Parallel Library DB / STRATS clone / `name@version` as id | **forbid** | — | — | L31; DEC-0084 stays dead; DEC-0376 Cut |

**Overall verdict:** **reuse** the existing identity store; **connect** Library / work-environment / databank / study as **projections** over those fingerprints. **extend** only if a true new semantic artifact appears (none of the three missing product nouns qualify). **new** identity store = spine amendment (AD-1). **undecided** = none for ownership of identity.

---

## 1. What already exists — fingerprint / registry kinds

### 1.1 One recipe, one registrar, no universal card

`qmf-core` owns the single `fp1` implementation (CT-05; DEC-0108). QMA does not re-hash: `content_address` is `fingerprint(value)` (`git show integration:qmx-agents/packages/qma-core/src/qma/core/content.py`).

`qmf-registry` writes **per-kind** CT-06 records: tiny header (kind, format version, at-birth parent refs) + kind body; stable id **derived** from identity content; writer/sequence/`created_at` display-only (`git show integration:packages/qmf-registry/src/qmf/registry/records.py`, module docstring + `RESERVED_KIND_NAMES`). Reserved names only: `promotion-occurrence-card`, `treasury-boundary-event`. Bot and Book are no longer reserved — bodies are CT-33 / CT-22.

Lineage after birth is CT-07 typed edges by fp1, not a graph DB (`docs/contracts/ct-07-lineage-edge.yaml`; `git show integration:packages/qmf-registry/src/qmf/registry/lineage.py`). Persistence is CT-09 through `qmf-data` rooms per world (`git show integration:packages/qmf-registry/src/qmf/registry/persistence.py`).

QMB consumes registry as **immutable as-of sets** through one library-owned port; the legal cite is `fp1`; aliases are display-only (`git show integration:qmb/src/qmb/registryread/port.py` `ResolvedRef.cite`).

Node composition root mints CT-06 kinds once per fingerprint: `book-definition`, `bms-definition`, `book-binding`, plus addable `seat` / `calendar-identity` / `capability-profile` / `producer-definition` (`git show integration:qmn/src/qmn/host/registry_mint.py` `COMPOSE_RECORD_KINDS`). Doors hold no second identity function.

### 1.2 Named kinds the Shared Library already is

| Kind / artifact | Contract | Integration type | Identity locus |
|---|---|---|---|
| `bot-definition` | CT-33 | `qml.declaration.bot.BotDefinition` (`KIND_BOT_DEFINITION = "bot-definition"`) | Six semantic groups + format + at-birth refs. Logic = dist id + version + **source-manifest fp**. Seat/rebind excluded (`git show integration:qml/src/qml/declaration/bot.py`) |
| `confluence` | CT-34 | `qml.declaration.confluence.Confluence` | Cited from the bot as ordered child fps |
| `strategy-family` | CT-06 metadata | QML `StrategyFamilyId` | Opaque operator key; exactly one per bot (DEC-0176) |
| `book-definition` | CT-22 | `qmf.risk.templates.BookDefinition` | `class: book-definition` + currency + recognised sections (`git show integration:packages/qmf-risk/src/qmf/risk/templates.py`) |
| `bms-definition` | CT-27 | `BmsDefinition` | Same template grammar; instance id derived |
| `book-binding` | CT-28 | `qmf.risk.binding` | Binding **epoch** = record fp; CT-32 populations cite it, never an interval (`docs/contracts/ct-28-book-binding.yaml`) |
| `performance-result` | CT-32 | `qmf.risk.performance.PerformanceResult`; QMB `results/ct32.py` | Full AD-12 label + population + period + measures. Chart series / trade-event refs are QMB extensions **excluded from fp1** (`git show integration:packages/qmf-risk/src/qmf/risk/performance.py`) |
| split manifest | CT-12 | `qmf.data.splits.SplitManifest` | `split_id` **is** the fingerprint (`git show integration:packages/qmf-data/src/qmf/data/splits.py`) |
| source observation | CT-10 | `qmf.data.observation` | Bitemporal + intake key; store `admit` on fp1 |
| configured indicator / structure | CT-16 / CT-17 | indicators / structure packages | Producer identity; structure objects are market facts |
| `qma-dev-zone-candidate` | CT-06 addable (QMA) | `ParentSurfaceGate.write_dev_zone_candidate` | Body: `origin`, `zone=dev`, `payload_fp1`. Kind name `qma-dev-zone-candidate` (`git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/tools/parent_writes.py`) |
| ExperimentSpec | CT-47 | `qma.core.ports.experiments.ExperimentSpec` | `spec_fp1` = `content_address` over code/config/data/env/seed/versions/costs. Ledger ref **outside** identity (`git show integration:qmx-agents/packages/qma-core/src/qma/core/ports/experiments.py`) |

Docs still stamp CT-22/27/28/32/33/47 `wiring_status: defined-unwired` / “no code exists” (`docs/contracts/ct-32-performance-result.yaml:10`, `ct-33-bot-definition.yaml:9`, `ct-47-qma-experiment-spec.yaml:9`). **Reconcile:** shapes + library types exist on integration; **composition-root persistence and product doors** are the unwired layer. Do not fork a second design from the YAML stamp.

### 1.3 Fingerprints that are **not** registry kinds (and must stay citations)

**QMB Study.** `StudyArtifact.fingerprint()` **is** `study_fp`. `admit_study` freezes one registry as-of and stamps `study_fp` plus bot/Book/BMS fps onto every trial label (`git show integration:qmb/src/qmb/optimize/sampler.py`, `StudyArtifact` / `StudyLabel` / `admit_study`). `stop_study` is lifecycle over already-spawned runs, not a new identity (`git show integration:qmb/src/qmb/orchestrator/study.py`). Ledger lines are one AD-12 object per run (`git show integration:qmb/src/qmb/ledger/line.py`). This is the same pattern as DEC-0160 **derived** run-config fragments: content-addressed, lineage back to CT-33/22/27, **never a new CT-06 kind**.

**ExperimentSpec vs Study.** ExperimentSpec is the **coordinated** (AD-2) experiment recipe + Experiment Ledger (scientist notebook, `docs/glossary.md` ExperimentSpec / Experiment Ledger). `study_fp` is the **governed** optimize-campaign declaration inside QMB. They cite the same bot/Book/split fps. Collapsing them into one “Project” kind would fork QuantConnect Project semantics onto two existing identities.

**Sweep ranking.** `rank_sweep` is a **pure read-time view** over ledger merge for one `sweep_id`; it publishes and never acts (`git show integration:qmb/src/qmb/sweep/rank.py`). That is the StrategyQuant databank **mechanism** already: filter/rank without copying rows.

### 1.4 What “work-environment” is **not**

Operator intent: a work environment opens like a tab, has a local tool set, and shares Library objects across tabs (`workroom/research/2026-09-14-ui-feature-route.md:29-30`; `_BRIEF.md` / `intent-durable.md` Shared Library). Spine AD-3: work-environment tabs and display aliases are **UX over fingerprints**. CAPABILITY-EXPANSION: work-environment roster stays UI-open.

**CT-46 `ExecutionEnvironment`** is compute placement (`local | docker | remote_* | browser | desktop`) and JobHandle occupancy — one `qmb` job per env (CT-47). It is **not** a research tab, a QuantConnect Project, or a Library folder.

No `WorkEnvironment` type exists under `packages/`, `qmb/`, `qml/`, or `qmx-agents/` on integration (`git grep` negative). Minting one as a CT-06 kind would be a **second identity** for session chrome.

---

## 2. Missing wiring vs missing function

### Missing wiring (function present; connect)

| Gap | Evidence | Do not “fix” by |
|---|---|---|
| CT YAML `defined-unwired` vs source | CT-32/33/47 headers vs packages on integration | Inventing a parallel schema |
| ExperimentSpec / ledger live only in process maps | `ExperimentSpecService._specs: dict[str, ExperimentSpec]` (`git show integration:qmx-agents/packages/qma-daemon/src/qma/daemon/experiments/service.py`). Daemon `SingleSqliteWriter` exists and is **not** wired to this service | A Library SQLite that copies specs |
| Dev-zone candidate `Registrar` is in-memory | `ParentSurfaceGate.__init__` builds a private `KindRegistry` + `Registrar` (`parent_writes.py`) | A second candidate table |
| QMA→QMB door records CLI instead of spawning | `RecordingQmbDoorTransport` (code-qma.md / CT-47 connect) | A second experiment id for the job |
| Library query / as-of enumeration | Port lists `bot-definition` / `book-definition` / `bms-definition` (`registryread/port.py`); no saved-view predicate object | New kinds for “folder” / “databank” |
| CLI coverage of sweep batch/rank and robustness | Library present; CLI partial (code-qmb.md) | Persisting rank output as identity |

### Missing function (not an identity problem)

| Gap | Class | Owner |
|---|---|---|
| Work-environment **chrome** (tab roster, local tools, agent placement) | **new** UI / **undecided** layout — identity **reuse** | UI over existing fps (GAP-0081 deferred for SDK) |
| Saved Library views (named predicates over kind+fp1) | **extend** query, not a kind | QMB as-of port + QMA ledger read |
| QDM-like coverage/gap studio | **extend** QMB data commands | AD-13; derived dataset = new fp1 + CT-07 edge |
| Structure/template **generation** | **new** authoring (AD-4) | QML authors CT-33/34; still registry identity |
| GAP-0085 mechanism nouns | **Deferred** | QML/registry; ExperimentSpec already refuses them |
| GAP-0016/0017 registration **gate** | **Deferred** | Prevention in QMB; policy not identity |

**Not missing:** a fingerprint function, a registrar, Bot/Book/BMS/split/result kinds, candidate write into `dev`, ExperimentSpec content-addressing, sweep rank, study_fp.

---

## 3. Recommended architectural ownership

Keep AD-1 / AD-3 / AD-14. Pin the remaining builder-fork:

| Noun | Owner | How Library sees it |
|---|---|---|
| Canonical bytes / `fp1` | **COMP-QMF-CORE** | Every cite is `fp1:sha256:<hex>` |
| Per-kind records, edges, promotion card, as-of delivery | **COMP-QMF-REGISTRY** (+ `qmf-data` rooms) | Kind + fp1. Addable kinds only for **new semantic artifacts** |
| Bot / confluence / family **content** | **COMP-QML** authors; registry owns | CT-33/34 |
| Book / BMS / binding / CT-32 **shapes** | **COMP-QMF-RISK**; QMB/QMN composition roots wrap | CT-22/27/28/32 |
| Splits / observations / journals | **COMP-QMF-DATA**; QMB data fronts | CT-12/10/13 |
| ExperimentSpec + Experiment Ledger | **COMP-QMA-CORE** defs; **COMP-QMA-DAEMON** runtime | **Cite `spec_fp1`**. Do **not** mint CT-06 `experiment-spec` unless a later spine amendment re-homes CT-47 (not required to share Library) |
| `study_fp` / ledger lines / sweep rank | **COMP-QMB** | **Cite** study_fp and run_id; rank is a view |
| Dev-zone candidates | **COMP-QMA-DAEMON** via CT-06 `qma-dev-zone-candidate` | Same registrar catalog; `origin=qma`; no zone mint |
| Work-environment | **UI session** (not a COMP) | Projection: ordered cites + layout. Not CT-46 |
| Candidate-databank | **query** (AD-14) | Predicates over ledger + as-of + staging. STRATS is input, not a store |
| Human live promote | outside QMA, node powers | Promotion card fp1 |

**Forbidden:** a Shared Library database; per-department fragment stores; `name@version` as identity; git-branch-per-parameter (DEC-0376); wrapping work-environment / study / databank as CT-06 kinds; QMA writing Book/BMS/binding/promotion records.

---

## 4. Open questions — AD vs Deferred

**Needs an invariant (this sitting; two builders would otherwise fork):**

> Shared Library identity **is** existing `fp1` kinds and citations. Work-environment, study collections, and candidate-databanks are **projections / queries** over those fingerprints. They are not CT-06 kinds and not a second store. ExperimentSpec remains a CT-47 qma-core record listed by `spec_fp1`; QMB `study_fp` remains a derived campaign fingerprint cited from ledger labels. Persist ExperimentSpec/candidates through the existing daemon writer / `RegistryPersistence` (connect). Do not copy payloads into a Library index.

That is the content of adopted **AD-3** and **AD-14**, plus a non-optional **connect** rule for ExperimentSpec persistence (AD-8) so Library cannot grow a shadow catalog “because the maps were in-memory.” No extra COMP. No new kind names for the three product nouns.

**Can stay Deferred:**

- Work-environment **roster** (which tabs exist) — UI-open; not identity.
- GAP-0081 UI SDK.
- GAP-0085 mechanism vocabulary (ExperimentSpec already refuses the nouns).
- GAP-0016/0017 attempt **policy** (raw material already accrues via `study_fp` + ledger roles).
- Whether ExperimentSpec is later **re-homed** as a CT-06 kind — unnecessary for Library; revisit only if as-of-set distribution must carry specs without the daemon. Default: **do not**.

---

## (1) What already exists

Fingerprint identity is implemented: `qmf-core` `fp1`; `qmf-registry` per-kind records and CT-07 edges; QML CT-33/34 content; risk CT-22/27/28/32 value types; data CT-12/10; QMB as-of port, CT-32 mint, `study_fp`, sweep rank; QMA ExperimentSpec + in-memory service + `qma-dev-zone-candidate` write; QMN composition-root mint roster. Shared Library as a **product surface** is already those objects.

## (2) Missing wiring vs missing function

**Wiring:** durable persist of ExperimentSpec/ledger and of the candidate `Registrar`; real QMB door; Library query/saved views; stale CT YAML. **Function:** work-environment chrome; named databank UX as saved queries; QDM-like browse. **Not missing:** a second identity system.

## (3) Recommended architectural ownership

Reuse COMP-QMF-CORE / COMP-QMF-REGISTRY / COMP-QMF-DATA / COMP-QMF-RISK / COMP-QML / COMP-QMB / COMP-QMA-{CORE,DAEMON}. Connect projections. Do not mint COMP-LIBRARY or CT-06 `work-environment` / `study` / `databank`.

## (4) AD vs Deferred

**recommended_ad:** Library objects are existing fp1 kinds and citations; work-environment, study, and candidate-databank are projections — never a second identity store or new kinds for those nouns. **Deferred:** tab roster, UI SDK, GAP-0085 nouns, attempt-count policy, optional later CT-06 re-home of ExperimentSpec.
