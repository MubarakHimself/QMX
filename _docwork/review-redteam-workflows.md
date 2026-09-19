---
id: REVIEW-REDTEAM-WORKFLOWS
title: Stage 7 Pass 2 adversarial review — Workflows construction kit (docs/ only)
type: review
status: draft
generated: 2026-09-19
scope: docs/ (constitution, AGENTS, glossary, gap-report, components, contracts, decisions, scenarios)
forbidden_reads: [_docwork/ (except this file), architecture sitting folder, transcripts, ledger.yaml]
inspect_sha_cited_by_docs: integration@270e992995c2378ca63cf6343254ef8140a8c97e
---

# Stage 7 Pass 2 — adversarial review (Workflows)

Fresh reader. Docs corpus only. Fail loudly. Every forced assumption is a finding.

## Counts

| Bucket | Count |
|---|---:|
| **Findings (fail)** | **24** |
| blocker | 6 |
| high | 10 |
| medium | 7 |
| low | 1 |
| **doc-fix** | 16 |
| **new GAP** | 7 |
| **doc-fix or new GAP** (sitting may have ruled off-corpus) | 1 |
| **Passes** (attack vector survived) | **5** |
| Forced assumptions (each mapped to a finding) | 24 |

Do not treat this review as architecture. Do not invent the missing machines.

## Attack results (the five briefs)

### 1. Plan adding ContributionHit — where docs run out

Docs name the class, the live tuple, the pin tuple, the owners, and the honesty scenario. They do **not** give a factory agent a buildable wire surface.

Run out at:

- `docs/contracts/ct-40-qma-wire-envelope.yaml` — additive family is an **invariant annotation**, not `schema.fields` / query / command names.
- Pin field `availability_revision` is **not** on the published hit DTO.
- `unavailable` vs `tombstone` are used as synonyms; neither is a CT-04 category (`tombstone`) / variant.
- Pin **store** is unnamed (and FEAT-0051 does not depend on product_session FEAT-0053).
- `published vs configured vs granted vs reachable vs healthy` has no enum.
- Pack `contributes` / `point` is not mapped onto CT-42’s closed contribution points.
- CT-40 still carries a live mill invariant that the facade is two-class only.

Forced assumptions: F-01, F-02, F-03, F-04, F-05, F-07, F-08, F-09, F-10, F-23, F-24.

### 2. Plan ATC without Book keys through QMB then QMN — does L36 stop you? Dummy Book?

| Question | Verdict |
|---|---|
| Dummy Book forbidden clearly? | **YES (pass).** Constitution L36 amendment, ADR-0024 option 2 / DEC-0424 / DEC-0451, CT-04, CT-22, CT-27, CT-33, `qmf-risk` FM-11, SCN-0020 Branch A, AGENTS hard rules. Sentinel fps, identity/no-op/unlimited/pass-through, `NULL_BOOK`, empty-object Book, fake MIS — `invalid input` at compile, register, validate, simulate, and seat. |
| L36 stop ATC-without-**Book** keys? | **No.** Named amendment (DEC-0448) says Book/BMS are default implementations, not the ceiling; PolicyPair may occupy those roles without dummy records. |
| L36 stop ATC-without-**bot** keys? | **Unresolved / likely yes if read strictly.** L36’s unamended first sentence still says “Bots trade … nothing above a bot touches the market.” `AlternativeRunConfig` omits bot keys. Amendment never says the bot role is optional. |
| QMB then QMN without inventing architecture? | **NO. Dead end.** B-3 compiler still requires Book/BMS fragments and an AD-29 binding; CT-23 is still the one bot-to-Book door; QMN still runs Book/BMS/risk **verbatim**; PolicyPair closed fields live in sitting `CONTRACTS §11`, not `docs/contracts/`; CT-07 has no PolicyPair lineage annotation. |

Forced assumptions: F-11, F-12, F-13, F-14, F-15, F-16, F-17, F-18, F-19.

### 3. Follow ADR-0024 → component specs → contracts. Dead ends?

Yes. The ADR names types and owners. Specs repeat prose. Contracts mostly gained **usage notes**, not schema.

| Type | ADR-0024 owner | Spec prose | Contract schema in `docs/contracts/` |
|---|---|---|---|
| ContributionHit | COMP-QMA-WIRE + daemon `published_contributions()` | qma-wire, qma-daemon, qma-core, glossary, SCN-0018 | CT-40 **annotation only** |
| InvocationEnvelope / GrantRecord | COMP-QMA-CORE + COMP-QMA-WIRE | qma-wire field list in prose; GAP-0096 timing | **absent** from CT-40 `schema.fields` |
| Operation descriptor | COMP-QMA-CORE | qma-core field catalogue in prose | **no CT**; CT-42 still forbids a contribution point with no qma-wire schema |
| product_session | COMP-QMA-DAEMON | qma-daemon durable fields | **no CT** |
| AlternativeRunConfig / PolicyPair | QMB+QML+QMN+QMF-RISK | three-class prose | CT-22/27/33/04 say “keys absent / dummy invalid”; **no PolicyPair fields** |
| RecipeDefinition | COMP-QMB wrap of QMF-DATA | identity tuple | CT-06 kind **deferred** (A5) |
| fencing_token / AD-25 records | COMP-QMN (+ QMB simulate tokens) | trading-node state enum | **no CT** |
| CheckpointManifest | COMP-QMA-DAEMON | restore order in prose (A6) | **no CT** |

Dead-end rule: DEC-0446 “no new CT” + AGENTS.md “every `CT-*` must resolve in `docs/contracts/`” + types that are public operations. A factory agent either mints CT-52+ (forbidden) or invents additive JSON Schema (unspecified). See F-01, F-10, F-11, F-16, F-23.

### 4. Where would a naive agent mint COMP-WF, a new CT, or claim the code already does this?

| Trap | Where it is invited | What actually forbids it |
|---|---|---|
| Mint **COMP-WF / COMP-LIB** | Product nouns capability / extension / workflow / mini-app / widget in overview + AGENTS with **no** `docs/components/workflows.md` and no preflight row for widget | L7/L31 annotations, ADR-0024 option 1 / DEC-0414 / DEC-0446 / DEC-0451, AGENTS hard rules, overview “no sixth box in C4” |
| Mint **CT-52+** | AGENTS change protocol + architecture preflight “every contract at its boundary”; huge public types with no CT file | DEC-0446 “additive CT-40 family annotations only” |
| Claim **code already does this** | CT-40 `wiring_status: source-inspected`; ADR-0024 “TaskGraph classes exist”; daemon names `published_contributions()` as if a method; mill two-class freeze still in CT-40 | DEC-0450, SCN-0018 Branch D, SCN-0020 Branch E, AGENTS “do not claim ContributionHit or product_session exist at `270e992`” |

See F-20, F-21, F-22, F-08, F-09.

### 5. Read constitution L36 alone — does it contain the named amendment?

**YES (pass).** `docs/constitution.md` L36 includes the 2026-09-19 Workflows named amendment (DEC-0448, DEC-0424, DEC-0436): Book/BMS default-not-ceiling; complete PolicyPair without dummy records; QML/QMB/optional MIS/QMN/paper/live adopt; L17 + sequential paper-then-live; QMN sole venue importer; dummy remains INVALID_INPUT; sensing/research is not a trading composition.

Isolation caveat (F-12): the **first sentence is not rewritten**. A reader of L36 alone still has “Bots trade … nothing above a bot touches the market” as standing law, plus a bracket that only relaxes Book/BMS implementations.

---

## Passes (do not “fix” these)

| ID | Attack | Result | Docs |
|---|---|---|---|
| P-1 | L36 named amendment in constitution | Present on L36 itself, not only in ADR-0024 | `docs/constitution.md` |
| P-2 | Dummy Book | Explicitly `invalid input` / INVALID_INPUT at every gate; no-op/sentinel/NULL_BOOK/empty Book/fake MIS named | constitution L36; ADR-0024; CT-04; CT-22; CT-27; CT-33; qmf-risk FM-11; SCN-0020 |
| P-3 | COMP-WF | Named and refused; minting is a spine amendment | L7, L31, ADR-0024, AGENTS, overview, gap-report DEC-0451 |
| P-4 | No new CT / no new COMP preflight | Recorded as reuse in ADR-0024 Architecture-preflight verdict | ADR-0024; dependencies.yaml notes |
| P-5 | Wiring honesty @ 270e992 | Repeated; scenarios have a dedicated failure branch for claiming implemented | DEC-0450; SCN-0018 D; SCN-0020 E; overview Honesty paragraph |

---

## Findings

Severity: **blocker** = cannot implement from docs without inventing architecture. **high** = will implement the wrong thing. **medium** = stall or silent mismatch. **low** = naming.

Kind: **doc-fix** = decided (or claimed decided) but not absorbed into the factory-readable contract/spec. **new GAP** = not decided; do not fill in prose.

### F-01 — CT-40 additive family has no schema, query, or command names

| | |
|---|---|
| **Severity** | blocker |
| **Kind** | doc-fix |
| **Doc** | `docs/contracts/ct-40-qma-wire-envelope.yaml`; `docs/components/qma-wire.md`; `docs/scenarios/SCN-0018-contribution-hit-honesty.md`; `docs/knowledge/traceability.md` FEAT-0051 |
| **Finding** | FEAT-0051 is “ContributionHit concatenate + pin/tombstone” on “additive CT-40 family, no new CT.” CT-40 `schema.fields` is still the envelope (`v`, `type`, `id`, `producer_id`, `correlation_id`, `scope_path`, `seq`, `payload`). Seed queries remain the original seven (`get quant` … `get provider health`). No federated-discovery query name, no pin command, no invoke-revalidate command, no hit payload schema. DEC-0446 forbids a new CT number. A factory agent must invent the wire verbs and JSON Schema. |
| **Suggested fix** | Stamp additive CT-40 schema: hit union discriminant, ContributionHit fields, pin tuple, pin/revalidate/invoke commands, listing query. Keep format-version additive-within-major. Do **not** mint CT-52. |

### F-02 — `availability_revision` is required to pin and is not on the hit

| | |
|---|---|
| **Severity** | high |
| **Kind** | doc-fix |
| **Doc** | glossary ContributionHit; qma-wire Workflows section; SCN-0018; ADR-0024 AD-2 / A4 |
| **Finding** | Hit identity is `{hit_class, plugin_id, point, qualified_id, package_id, package_version}`. Pins store `(qualified_id, package_version, availability_revision)`. The live DTO does not carry `availability_revision`. A caller cannot pin from a hit without inventing a second lookup or stuffing the field into identity. A4 froze the pin tuple, not how it is obtained. |
| **Suggested fix** | Declare `availability_revision` as an **occurrence** field on the live hit (not identity). Identity remains the published tuple. Pin copies that occurrence. Bump of availability_revision without version change is specified (roster republish? enable?). |

### F-03 — `unavailable` vs `tombstone` are unmapped to CT-04

| | |
|---|---|
| **Severity** | high |
| **Kind** | new GAP (unless sitting CONTRACTS already distinguished them — then doc-fix absorb) |
| **Doc** | SCN-0018; CT-04; qma-core FM-6 (slug tombstone is a different noun) |
| **Finding** | Disable/uninstall/missing “yields typed `unavailable` or `tombstone`.” No rule which event produces which. CT-04 categories are exactly seven; `tombstone` is not one. QMA already uses “tombstone” for retired `desk_slug`/`quant_slug`. Factory will either mint a new category (L15 / DEC-0109 forbid silent category mint) or overload `unavailable dependency` for both and lose the honesty distinction SCN-0018 titles on. |
| **Suggested fix** | If sitting ruled the mapping, absorb it as qma-core refusal variants of CT-04 (`unavailable dependency` vs a named tombstone variant) plus disable vs uninstall vs missing. If not ruled, mint a GAP under GAP-0094 rather than filling SCN with invented branches. |

### F-04 — Pin persistence location unnamed; FEAT-0051 epic graph is dishonest

| | |
|---|---|
| **Severity** | blocker |
| **Kind** | doc-fix |
| **Doc** | SCN-0018; traceability FEAT-0051 vs FEAT-0053; qma-daemon product_session fields; ADR-0024 DEC-0429 closed sqlite list |
| **Finding** | “A caller pins that hit.” Store is not named. Candidates a naive agent will invent: client memory (then pin honesty is not testable server-side); `product_session.selected_refs` (FEAT-0053; FEAT-0051 does **not** depend on it); a new sqlite table (DEC-0429 closed list forbids it). DEC-0429 v1 additions are product_session, task_graph_state+outbox, mini-app instance rows, GrantRecord rows, CheckpointManifest — not “pins.” |
| **Suggested fix** | Name the pin store. If pins are `product_session.selected_refs` (or GrantRecord audience), make FEAT-0051 depend on FEAT-0053 or shrink FEAT-0051 to **listing concatenate only** and move pin/tombstone to FEAT-0053. Do not add a sixth sqlite class. |

### F-05 — Five listing states have no schema

| | |
|---|---|
| **Severity** | medium |
| **Kind** | doc-fix |
| **Doc** | ADR-0024 AD-2 / Consequences; qma-wire; SCN-0018 Given |
| **Finding** | “Discovery listings distinguish published vs configured vs granted vs reachable vs healthy.” No field, enum, cardinality, or which combinations are legal. Tool availability is a **four-way intersection** (published hits ∩ host grants ∩ product-session GrantRecords ∩ health) in AD-9 — a fifth “configured” is unnamed there. Factory will invent flags or collapse them. |
| **Suggested fix** | Closed enum + which are filters vs annotations. If “configured” is pack-enablement, say so and distinguish from `granted_ops`. |

### F-06 — “Four discovery rails” vs three frozen hit classes

| | |
|---|---|
| **Severity** | low |
| **Kind** | doc-fix |
| **Doc** | ADR-0024 AD-2 title; DEC-0415 body; traceability DEC-0415 row |
| **Finding** | AD-2 title: “four discovery rails.” Frozen facade hits: KnowledgeHit, ArtifactHit, ContributionHit (three). Fourth is implied as `qml.research` / `research_ref` **refused on the facade**. A naive agent will mint a fourth `hit_class`. |
| **Suggested fix** | Name the four rails explicitly (three facade hits + off-facade hypothesis listing) in ADR-0024 AD-2 and qma-wire. |

### F-07 — FEAT-0051 is blocked on PROPOSED mill FEAT-0050

| | |
|---|---|
| **Severity** | medium |
| **Kind** | doc-fix |
| **Doc** | `docs/knowledge/traceability.md` FEAT-0050 / FEAT-0051; ADR-0023 still provisional; DEC-0449 “do not set DEC-0389 superseded_by” |
| **Finding** | First Workflows epic depends on FEAT-0050 (federated KnowledgeHit\|ArtifactHit DTO) which is mill-package **PROPOSED**. DEC-0449 named-amends the two-class freeze without accepting the mill package. Factory either waits on a provisional package or dual-implements federation. |
| **Suggested fix** | State that FEAT-0051 may extend the CT-40 federated DTO **without** mill-package acceptance; FEAT-0050 remains mill-provisional for hypothesis-off-facade rules. Or drop FEAT-0050 from FEAT-0051 blockers. |

### F-08 — CT-40 still asserts the two-class freeze as a live invariant

| | |
|---|---|
| **Severity** | high |
| **Kind** | doc-fix |
| **Doc** | `docs/contracts/ct-40-qma-wire-envelope.yaml` invariants (QML RESEARCH USAGE vs WORKFLOWS NAMED AMENDMENT); `docs/components/qma-wire.md` mill section vs Workflows section |
| **Finding** | Same ratified contract: mill invariant “two-class freeze text remains KnowledgeHit \| ArtifactHit only” **and** Workflows invariant adding ContributionHit. qma-wire mill section is still written as current two-class law, then a later section amends it. Top-to-bottom reader implements FEAT-0050 as two-class and refuses ContributionHit (or the reverse). |
| **Suggested fix** | Mill bullet: “DEC-0389 two-class freeze **named-amended by DEC-0449** for the facade; remainder of DEC-0389 stands (occupancy, no strats/qml_candidate, hypotheses off Library).” Do not leave both as coequal live invariants. |

### F-09 — `published_contributions()` is written as if it were a present method

| | |
|---|---|
| **Severity** | medium |
| **Kind** | doc-fix |
| **Doc** | qma-daemon Workflows section; ADR-0024 AD-2; CT-40 provenance; DEC-0450 |
| **Finding** | “Query owner remains COMP-QMA-DAEMON `published_contributions()`.” Combined with CT-40 `wiring_status: source-inspected` and “TaskGraph classes exist,” a naive agent claims the query already exists at 270e992. DEC-0450 says ContributionHit is not on the wire. Python method vs wire query is also unspecified (F-01). |
| **Suggested fix** | “Specified query owner; **absent** at 270e992 (DEC-0450, GAP-0094).” Distinguish daemon method vs CT-40 query. |

### F-10 — Pack `contributes.point` vs CT-42 closed contribution points

| | |
|---|---|
| **Severity** | high |
| **Kind** | doc-fix |
| **Doc** | SCN-0018 Given; SCN-0022; CT-42 enums (tool \| tool_adapter \| hook \| skill \| graph_template \| model_deployment \| toolset \| worker_template); qma-core AD-3 operation descriptor; ADR-0024 AD-3 / AD-18 / AD-30 |
| **Finding** | “Pack `contributes` entries expand to ContributionHit at enable.” ContributionHit has `point`. CT-42’s multi points are a closed set with no generic `operation` / `capability`. AD-3 operation descriptors are a different object (qma-core prose, no CT). Pack lifecycle (downloaded→…→uninstalled) is not CT-42 plugin roster. Factory will collapse packs into plugins or mint a new contribution point (CT-42 says a point with no qma-wire schema may not be registered). |
| **Suggested fix** | Map pack `contributes` → existing CT-42 point **or** to AD-3 operation id (`qualified_id`). State pack ≠ plugin if they differ. Add the mapping to CT-42 as a usage annotation, not a new point, unless a spine amendment adds one. |

### F-11 — PolicyPair / AlternativeRunConfig have no docs-owned field catalogue

| | |
|---|---|
| **Severity** | blocker |
| **Kind** | doc-fix |
| **Doc** | ADR-0024 cheap-veto A1 (“CONTRACTS §11”); GAP-0097; glossary ATC; qmb.md three config classes; CT-22/27/33 usage notes |
| **Finding** | A1: “PolicyPair field catalogue (AccountingPolicy / RiskPolicy closed fields in CONTRACTS §11)” with default **proceed**. That catalogue is sitting-folder `CONTRACTS.md`, **not** in `docs/contracts/`. CT-22/27/33 only say keys are absent-not-null and dummy is invalid. Completeness under “the dummy test” cannot be executed: there is no required-field list. A factory agent implementing from `docs/` must invent AccountingPolicy/RiskPolicy or read the forbidden sitting folder. GAP-0097 is **when they appear in code**, not what the fields are. |
| **Suggested fix** | Absorb the closed field lists as usage schema on existing contracts / qmb spec (no new CT number), marked A1 sitting machinery. If §11 was never closed, convert A1 into a GAP and do not proceed FEAT-0056 ATC fixtures. |

### F-12 — L36 amendment does not make bot keys optional; ATC omits them

| | |
|---|---|
| **Severity** | blocker |
| **Kind** | new GAP |
| **Doc** | constitution L36; SCN-0020 Given (AlternativeRunConfig omits Book/BMS/**bot** keys); ADR-0024 AD-11 / AD-23; qmb.md |
| **Finding** | L36 still: “Bots trade; books control bots; BMS accounts for and constrains books; nothing above a bot touches the market.” Amendment relaxes **Book/BMS implementations**, not the bot-as-sole-market-actor clause. `AlternativeRunConfig` requires bot keys **absent**. SCN-0020 Given mentions “command binding” with no schema. Who submits CT-19 commands on the ATC path? A PolicyPair occupying accounting + risk/sizing roles is not a bot. Implementing ATC-without-bot as “complete second trading system” that reaches QMN live `VenueClientKind` invents a market actor L36 still forbids. |
| **Suggested fix** | **Do not invent.** Either (a) named-amend L36’s bot sentence to admit a complete PolicyPair-bound command owner, or (b) require an ATC command-side actor that is not a dummy CT-33, or (c) GAP the market-actor / command-binding noun. FEAT-0056 must not seat live ATC until this is ruled. |

### F-13 — QMB B-3 compiler still requires Book/BMS fragments; three-class split is a sticker

| | |
|---|---|
| **Severity** | high |
| **Kind** | doc-fix |
| **Doc** | `docs/components/qmb.md` Authority / B-3 (DEC-0160) vs Workflows three config classes; FM-1 still Book/BMS key collision only; ADR-0017 (no Workflows follow-up) |
| **Finding** | B-3: every run compiles invocation > run spec (**bot layer**) > **BMS fragment** > **Book fragment** > defaults; resolved artifact **MUST cite Book and BMS by fp1**; every run mints one AD-29 binding; sizing/exits consume CT-23. Workflows later says three **distinct types**, keys absent-not-null on AlternativeRunConfig, and “do not weaken ResolvedRunConfig tests” (SCN-0020 Branch D). No B-3 amendment, no AlternativeRunConfig schema, no FM for “Book keys present on AlternativeRunConfig” / “Book keys absent on ResolvedRunConfig.” Factory will make Book fields optional on one type (forbidden) or cannot compile ATC. |
| **Suggested fix** | Rewrite B-3: three compile entrypoints, not optional keys. FM rows for wrong-class keys. Dated follow-up on ADR-0017 (missing today; blast radius listed ADR-0020/22/23 only). |

### F-14 — CT-23 remains the only intent door; ATC has none

| | |
|---|---|
| **Severity** | blocker |
| **Kind** | new GAP |
| **Doc** | `docs/contracts/ct-23-risk-evaluation.yaml` (“one bot-to-Book inbound port”); qmb B-3 “CT-23 inbound”; trading-node order path; SCN-0020 “command binding” |
| **Finding** | CT-23: exactly two intent families, Book resolves `requested_r` and full-loss, bot must not size (else L36 inversion). ATC has no bot and no Book, so it cannot legally call CT-23. No replacement door is named in any CT. Extending CT-23 to PolicyPair mixes the default path with ATC (and would look like dummy Book). New CT forbidden. This is a hard dead end on ADR-0024 → contracts. |
| **Suggested fix** | New GAP: ATC command/intent port. Options (operator, not this review): annotate an existing CT; later CT mint (spine amendment of DEC-0446); or ATC-simulate stays QMB-JSONL-only until a door sitting. Do not let FEAT-0056 invent a door. |

### F-15 — QMN “verbatim Book/BMS/risk” vs “must not stay secretly Book-shaped”

| | |
|---|---|
| **Severity** | high |
| **Kind** | doc-fix |
| **Doc** | `docs/components/trading-node.md` TN order-path / “runs the Book/BMS/venue/risk protection set VERBATIM” vs Workflows ATC venue path; ADR-0019 (no Workflows follow-up) |
| **Finding** | Node spec: L36 chain wired without redefining a step; live loop is QMB `run_slice` unforked; protection set verbatim. Workflows: when ATC is selected the node **hosts that composition** and does not stay secretly Book-shaped. Both are ratified. A factory agent seating ATC on `run_slice`+CT-23 is secretly Book-shaped (DEC-0436 forbid). A factory agent forking the node loop invents a second trading runtime (TN-1 forbid). ADR-0019 has no dated follow-up. |
| **Suggested fix** | Fence the verbatim clause to `ResolvedRunConfig` / default Book path. State what `run_slice` does under AlternativeRunConfig **or** GAP it (ties F-14). Dated follow-up on ADR-0019. |

### F-16 — CT-07 lineage to “PolicyPair hash” has no contract home

| | |
|---|---|
| **Severity** | high |
| **Kind** | doc-fix |
| **Doc** | ADR-0024 AD-23; qmb.md ATC evidence; SCN-0020 Then (2); `docs/contracts/ct-07-lineage-edge.yaml` (no PolicyPair/ATC annotation) |
| **Finding** | ATC evidence is QMB JSONL `composition_class: alternative` plus CT-07 lineage to the PolicyPair hash. PolicyPair is not a registry kind (ContributionHit law’s cousin: don’t register it). Hash recipe is unnamed (fp1 over which canonical JSON? which format version?). CT-07 was not annotated. Factory will fp1 an invented struct or skip lineage. |
| **Suggested fix** | CT-07 usage annotation: edge type, endpoints (QMB ledger line ↔ PolicyPair content hash), hash = imported fp1 over named canonical form. PolicyPair remains not a CT-06 kind. |

### F-17 — ADR-0008 still quotes L36 as absolute; no Workflows follow-up

| | |
|---|---|
| **Severity** | high |
| **Kind** | doc-fix |
| **Doc** | `docs/decisions/ADR-0008-book-and-risk-boundary.md` Decision paragraph; ADR-0024 blast radius (follow-ups only ADR-0020/22/23); AGENTS reading order |
| **Finding** | ADR-0008: “The authority order is constitutional and verbatim: bots trade; books control bots; … nothing above a bot touches the market — bot → book → BMS → operator (L36).” No 2026-09-19 follow-up. A factory agent who reads ADR-0008 (the Book ADR) after AGENTS will treat Book keys as always required and dummy-Book as the only way to “satisfy L36” for a second composition — exactly the path DEC-0424 forbids. Same hole on ADR-0017 (QMB) and ADR-0019 (node). |
| **Suggested fix** | Dated follow-ups on ADR-0008, ADR-0017, ADR-0019 pointing at DEC-0448 / three config classes / dummy INVALID_INPUT / “do not read this Decision as blocking ATC class.” Do not silently rewrite 2026-08-20 Decision text. |

### F-18 — “Conserved measures” for Book vs ATC compare are unnamed

| | |
|---|---|
| **Severity** | medium |
| **Kind** | new GAP |
| **Doc** | qmb.md “Compare Book vs ATC only on conserved measures both policies define; do not force ATC into the Book R vocabulary” |
| **Finding** | No list of conserved measures. R is L24 / Book vocabulary. Factory will either compare on R (forbidden) or invent a measure set. |
| **Suggested fix** | GAP the conserved-measure catalogue (or absorb if sitting CONTRACTS named it). FEAT-0056 must not assert numeric parity. |

### F-19 — Optional MIS on ATC is a dangling noun on a deferred gap

| | |
|---|---|
| **Severity** | medium |
| **Kind** | new GAP |
| **Doc** | glossary ATC “optional MIS binding”; SCN-0020 When (B); dummy test includes `mis_ref: null` as fake MIS; GAP-0051 MIS training deferred |
| **Finding** | Optional MIS must be absent-not-null (else dummy). How a complete ATC binds or omits MIS, and how that interacts with GAP-0051 “seam is V1, models are not,” is unspecified. Factory will put `mis_ref: null` (dummy) or invent a MIS PolicyPair. |
| **Suggested fix** | Note on GAP-0051 / GAP-0097: ATC optional MIS means the key omitted; no fake MIS; models still not this sitting. Do not specify a MIS PolicyPair here. |

### F-20 — Mini-app / widget have no preflight owner; COMP-WF trap stays baited

| | |
|---|---|
| **Severity** | medium |
| **Kind** | doc-fix |
| **Doc** | overview “capability, extension, workflow, mini-app, widget”; ADR-0024 preflight table (no mini-app/widget row); glossary Experimentation Board; DEC-0429 mini-app instance rows |
| **Finding** | COMP-WF is refused, but the kit’s product nouns are not assigned except in passing (mini-app → existing plugin-install projection; widget/Board → client-only, writes nothing). AGENTS preflight: “prove reuse-or-new” for a new module. Naive agent mints COMP-WF for “the construction kit” or COMP-LIB for Artifact Library. |
| **Suggested fix** | Preflight table rows: mini-app = plugin-install projection (`instance_id` ≠ `plugin_id`); widget = Board layout (DEC-0417), not durable; workflow = Graph Template + Task Graph in QMA; capability = AD-3 descriptor + ContributionHit. Repeat “no COMP-WF” next to those nouns in overview. |

### F-21 — “No new CT” vs AGENTS “every boundary is a CT-* file” — factory will mint CT-52

| | |
|---|---|
| **Severity** | high |
| **Kind** | doc-fix |
| **Doc** | AGENTS.md “Before changing anything” / architecture preflight item 4; ADR-0024 DEC-0446; the type list in Attack 3 |
| **Finding** | Public types: ContributionHit, Operation descriptor, InvocationEnvelope, GrantRecord, product_session, AlternativeRunConfig, PolicyPair, RecipeDefinition, CheckpointManifest, fencing_token. None have a `docs/contracts/ct-*.yaml` schema. AGENTS says every CT at a boundary must resolve in `docs/contracts/`. DEC-0446 says no new CT. Naive agent mints CT-52–CT-60. Disciplined agent cannot pass their own preflight. |
| **Suggested fix** | ADR-0024 / AGENTS mapping table: type → existing CT to **annotate** (CT-40 family for wire DTOs; CT-04 for dummy; CT-22/27/33 for default-path keys; CT-07 for ATC lineage; CT-06 recipe kind still deferred). Explicit: annotating is the preflight verdict, not a missing CT file. |

### F-22 — `source-inspected` on CT-40 invites “code already does ContributionHit”

| | |
|---|---|
| **Severity** | high |
| **Kind** | doc-fix |
| **Doc** | CT-40 `wiring_status: source-inspected` (1b451a8 **and** 270e992 note); ADR-0024 “TaskGraph classes exist but store is in-memory”; DEC-0286; DEC-0450 |
| **Finding** | `source-inspected` previously meant matching packages exist. Envelope/types at 1b451a8 ≠ ContributionHit/product_session/ATC at 270e992. ADR-0024 itself says TaskGraph **classes exist**. Naive agent treats class presence as FEAT-0051/0055 done. SCN Branch D exists; the stamp still lies. |
| **Suggested fix** | Split the stamp: envelope `source-inspected`; ContributionHit / InvocationEnvelope / product_session / PolicyPair `specified-unwired` (or keep DEC-0450 and **change** `wiring_status` so it cannot be read as “ContributionHit exists”). Repeat “classes ≠ e2e” on the TaskGraph sentence in qma-daemon. |

### F-23 — Operation descriptor / InvocationEnvelope / GrantRecord: prose without a contract, and CT-42 will refuse registration

| | |
|---|---|
| **Severity** | blocker |
| **Kind** | doc-fix |
| **Doc** | qma-core Workflows section (descriptor field catalogue); qma-wire InvocationEnvelope field list; GAP-0096 (timing only); A3 cheap-veto; CT-42 “contribution point with no qma-wire schema may not be registered” |
| **Finding** | AD-3: every public operation publishes a versioned descriptor; every public call carries InvocationEnvelope. Field lists live in markdown. CT-40 schema does not include them. CT-42 will refuse to register operations until a qma-wire schema exists. GAP-0096 is when they land in code, not the schema. A3 says proceed with sitting machinery — not absorbed. FEAT-0051 invoke-revalidate (SCN-0018 When 4) needs GrantRecord intersection (AD-9) which is FEAT-0052. |
| **Suggested fix** | Absorb A3 field lists as additive CT-40 family schema. FEAT-0051 must not include invoke-as-grant-check; that is FEAT-0052. Until the schema exists, CT-42’s “no schema → may not register” will block ContributionHit enablement (F-10). |

### F-24 — FEAT-0056 “thin fixtures” cannot close GAP-0098 / P2-INT-001 and will be claimed as e2e

| | |
|---|---|
| **Severity** | medium |
| **Kind** | new GAP (already GAP-0098 — **doc-fix** to stop the claim) |
| **Doc** | GAP-0098; DEC-0450; SCN-0020 When (B) “QML authoring, QMB backtest/optimize, optional MIS, QMN adopt”; traceability FEAT-0056 |
| **Finding** | SCN-0020’s happy path is cross-component adoption. GAP-0098 defers QML→QMB→QMN e2e. FEAT-0056 is “thin proof fixtures.” A naive agent will mark SCN-0020 done and close GAP-0098. DEC-0286 already says class/test ≠ e2e; this sitting adds a golden scenario that **looks** like e2e. |
| **Suggested fix** | SCN-0020 header already says specification not proof — add: FEAT-0056 fixtures **do not** close GAP-0098. Keep P2-INT-001 named. |

---

## Forced assumptions (index)

Each line is a finding. Implementers must not silently pick.

| Assumption a factory agent would make | Finding |
|---|---|
| Federated discovery query is `library.search` / a new query I name | F-01 |
| ContributionHit JSON equals the identity tuple | F-01, F-02 |
| `availability_revision` is `package_version` or a descriptor digest | F-02 (forbidden by DEC-0415) |
| Disable and uninstall both return `unavailable dependency` | F-03 |
| Pins live in product_session / client / a new table | F-04 |
| Listing flags are booleans I invent | F-05 |
| Fourth rail is a fourth `hit_class` | F-06 |
| Wait for mill FEAT-0050 / ADR-0023 acceptance | F-07 |
| Two-class freeze still binds the facade | F-08 |
| `published_contributions()` already exists at 270e992 | F-09, F-22 |
| Pack `point` is a new CT-42 contribution point | F-10 |
| AccountingPolicy fields = a subset of CT-22 | F-11 (dummy Book trap) |
| ATC without a bot is allowed because L36 was amended | F-12 |
| Make `book_fp1` optional on ResolvedRunConfig | F-13 (SCN-0020 Branch D) |
| ATC intents still go through CT-23 | F-14 |
| Seat ATC on existing `run_slice` | F-15 |
| PolicyPair hash = fp1 of JSON I invent | F-16 |
| ADR-0008 still requires Book always | F-17 |
| Compare ATC to Book on R | F-18 |
| `mis_ref: null` means optional MIS | F-19 (dummy) |
| Workflows needs COMP-WF | F-20 |
| Mint CT-52 for ContributionHit / PolicyPair | F-21 |
| `source-inspected` means ContributionHit is in code | F-22 |
| Operation descriptors can register without a wire schema | F-23 |
| SCN-0020 + FEAT-0056 closes e2e | F-24 |

---

## Naive-agent traps (COMP-WF / new CT / code-already-does-this)

1. **COMP-WF:** overview product-noun heading without a component file. Mitigation exists in L7/ADR-0024/AGENTS but is easy to miss if the agent starts at overview C4 “Workflows composition.” F-20.
2. **New CT:** AGENTS preflight vs DEC-0446. F-01, F-11, F-14, F-21, F-23.
3. **Code already does this:** CT-40 source-inspected; TaskGraph classes; method name `published_contributions()`; mill section still two-class (so they “implement the third class” on top of imagined two-class code). DEC-0450 is adequate **if read**; the stamps fight it. F-08, F-09, F-22.

Dummy Book as L36 satisfaction is the ATC analogue of these traps and is **already forbidden clearly** (P-2). The remaining ATC trap is the opposite: inventing a market actor because bot keys are absent (F-12, F-14).

---

## L36 isolation (verbatim)

From `docs/constitution.md` L36, read alone:

> **L36.** Bots trade; books control bots; BMS accounts for and constrains books; nothing above a bot touches the market. Hierarchy: bot -> book -> BMS -> operator. This authority order is re-ratified 2026-08-20, and nothing in QMF may invert or shortcut it. (DEC-0143) [Workflows named amendment, 2026-09-19: Book and BMS remain the **default** implementations of portfolio accounting and risk/position-sizing roles, not the only implementations the framework may host. A complete alternative PolicyPair may occupy those roles without dummy Book/BMS records. Downstream QML, QMB, optional MIS, QMN, paper, and live **adopt** the selected composition. Human L17 promote and sequential paper-then-live remain. QMN remains the only venue importer. Dummy Book/BMS remains INVALID_INPUT. Sensing/research is not a trading composition. (DEC-0448, DEC-0424, DEC-0436)]

- Named amendment: **present** (P-1).
- Dummy Book: **present** (P-2).
- Book keys absent: **allowed** by the bracket.
- Bot keys absent / non-bot market touch: **not allowed** by the unamended first sentence (F-12).
- Spelling `INVALID_INPUT` vs CT-04 `invalid input`: map in CT-04 already; constitution uses the screaming form. Not counted separately.

---

## What must not happen next

- Do not invent PolicyPair fields, an ATC intent door, pin storage, or wire query names in this review.
- Do not mint COMP-WF or CT-52 in a “fix.”
- Do not close GAP-0092–GAP-0100 in prose.
- Do not claim 270e992 implements any of this.
- Doc-fixes absorb **already-ruled** sitting machinery into `docs/contracts/` / specs / ADR follow-ups.
- New GAPs record **unruled** machines (bot-optional vs L36, ATC door, unavailable vs tombstone, conserved measures, optional MIS).

## Finding ID index

| ID | Severity | Kind | One-line |
|---|---|---|---|
| F-01 | blocker | doc-fix | CT-40 has no ContributionHit schema/query/commands |
| F-02 | high | doc-fix | Pin needs availability_revision; hit DTO omits it |
| F-03 | high | new GAP | unavailable vs tombstone unmapped to CT-04 |
| F-04 | blocker | doc-fix | Pin store unnamed; FEAT-0051 vs 0053 |
| F-05 | medium | doc-fix | Five listing states have no enum |
| F-06 | low | doc-fix | Four rails vs three hit classes |
| F-07 | medium | doc-fix | FEAT-0051 blocked on PROPOSED FEAT-0050 |
| F-08 | high | doc-fix | CT-40 two-class freeze still live next to DEC-0449 |
| F-09 | medium | doc-fix | published_contributions() written as present |
| F-10 | high | doc-fix | Pack contributes.point vs CT-42 closed points |
| F-11 | blocker | doc-fix | PolicyPair fields not in docs/contracts |
| F-12 | blocker | new GAP | L36 still requires a bot; ATC omits bot keys |
| F-13 | high | doc-fix | QMB B-3 still requires Book/BMS fragments |
| F-14 | blocker | new GAP | No ATC replacement for CT-23 |
| F-15 | high | doc-fix | QMN verbatim Book vs not-secretly-Book-shaped |
| F-16 | high | doc-fix | CT-07 PolicyPair hash unannotated |
| F-17 | high | doc-fix | ADR-0008/0017/0019 lack Workflows follow-up |
| F-18 | medium | new GAP | Conserved measures unnamed |
| F-19 | medium | new GAP | Optional MIS vs dummy null |
| F-20 | medium | doc-fix | Mini-app/widget unowned; COMP-WF bait |
| F-21 | high | doc-fix | No-new-CT vs AGENTS every-boundary-is-a-CT |
| F-22 | high | doc-fix | source-inspected invites code-already-does-this |
| F-23 | blocker | doc-fix | Operation/envelope/grant have no CT schema |
| F-24 | medium | new GAP | FEAT-0056 must not close GAP-0098 |

**24 findings. 5 passes. 6 blockers. Fail the fold for factory implementation of ContributionHit pin/tombstone and of ATC-without-Book through QMB then QMN until the blocker doc-fixes and new GAPs are placed.**
