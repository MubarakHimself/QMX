# Reference Study: Memory Providers (Hindsight · Mem0 · Letta blocks)

Reference extractor output. All facts verified against primary docs, checked 2026-08-28.
Register decisions #43–#46: QMX does NOT build memory in-house at v1; it owns a
`MemoryProvider` contract and evaluates providers behind it. Hindsight is the leading
candidate; Mem0/Honcho are the comparison set; Letta is a pattern only.

## The six questions

**1. Target mental model.** Memory = *selective, durable, adaptive state derived from
experience that improves future decisions* (register #44) — NOT the transcript, ledger,
or knowledge corpus (Constitution: MEMORY ≠ LEDGER ≠ KNOWLEDGE ≠ ARTIFACTS ≠ CONTEXT).
A memory system that is (a) *write-gated* (arbitrary agent text is a candidate, not a
memory), (b) *provenance-carrying*, (c) *supersedable/expirable/contradictable*, and
(d) *retrieval-shaped* (recall fills a token budget, not a result count). The provider is
separate from the Context Engine (Hermes/Letta split, register #46): the provider owns
durable adaptive facts; the context engine owns what a given invocation sees.

**2. Concrete runtime/API structures** (real names, per provider) — see sections below.

**3. Failure modes solved.** Agents forget across sessions; naive vector RAG can't do
temporal ("last spring") or multi-hop ("where does Alice work?"); duplicate facts pile
up; contradictions never reconcile; no audit trail when a fact is wrong/stale; the same
fact returned twice (raw + consolidated); secrets/injection reaching storage.

**4. Reuse conceptually.** retain/recall/reflect verbs; observation *consolidation with
evidence + proof count + preserved history*; reversible *invalidate w/ reason* + audit
archive; token-budgeted recall (`max_tokens`); tag-scoping (`user:`/`session:`) inside an
isolated bank; multi-strategy retrieval (semantic+BM25+graph+temporal); Letta's
always-visible curated blocks + read-only shared blocks (→ Context Engine, not provider).

**5. Reject.** Any provider as "QMX memory" (SDK owns the contract, #43/#4820); Hindsight
`reflect` as a reasoning surface (QMX owns cognition); Mem0 OSS as graph-memory source
(graph was *removed* from OSS in v3); Letta as a backend (it's a full stateful-agent
runtime); all multi-tenant/marketplace machinery (INHERITED FASHION — see tags below).

**6. Contract QMX owns instead** — `MemoryProvider` + `MemoryCandidate → Memory`, section
"QMX-owned contract" below.

---

## Hindsight (Vectorize) — LEADING CANDIDATE

License **MIT** (Copyright 2025 Vectorize AI, Inc.) — raw LICENSE. Docker image tag
**0.4.9** current; paper arXiv:2512.12818 (Dec 2025), claims SOTA on agent memory.
SDKs: Python, TypeScript, Go, CLI, HTTP/REST, MCP.

**Three verbs / data model.** `retain()` store → `recall()` search → `reflect()` reason.
Atomic unit = *memory unit* (a fact). Fact hierarchy (checked at reflect in priority
order): **Mental Model** (user-curated summary) → **Observation** (auto-consolidated,
evidence-grounded belief, references source memories *with exact quotes* + a *proof
count*, *refined not overwritten*, history preserved, freshness-aware) → **World Fact**
(objective) / **Experience Fact** (the bank's own actions). Raw content is never stored
verbatim — only extracted facts.

**retain params:** `content` (only required); `timestamp` (ISO / omit=now / `"unset"`);
`context` (source label, injected into extraction prompt — highest-leverage quality
lever); `metadata` (str→str KV, stored + returned on every recall — the provenance
hook); `document_id` (idempotent upsert; re-retain replaces); `update_mode`
replace|append; `entities` (+ `resolve_entities`); `tags`/`document_tags` (visibility
scoping — `user:<id>`, `session:<id>`, `room:`, `topic:`); `observation_scopes`
combined|shared|per_tag|all_combinations|custom (which observations a memory feeds).
Async retain + `operation_id` for safe retries; provider Batch API 50% cost cut.

**recall params:** `query`; `types` world|experience|observation; `prefer_observations`
(observation *supersedes* the raw fact it was built from); `budget` low|mid|high;
`max_tokens` (default 4096 — fills context by tokens, "agents think in tokens");
`query_timestamp`; `temporal_window` (ranks, not filters); `include{chunks, source_facts,
entities}`; `tags` + `tags_match` any|any_strict|all|all_strict|exact; `tag_groups`
(boolean and/or/not); `trace`; `min_scores`. Retrieval = **TEMPR**: semantic + BM25 +
graph + temporal run in parallel → RRF fusion → cross-encoder rerank.
Result fields: `id, text, type, context, metadata, tags, entities, occurred_start/end,
mentioned_at, document_id, chunk_id, source_fact_ids, scores{final,reranker,semantic,keyword}`.

**Curation (supersede/expire/contradict).** `PATCH …/memories/{id}`: **edit** (text/
context/dates/fact_type/entities + `reason`; re-embeds, re-consolidates); **invalidate**
(`state=invalidated` + `reason` — reversible soft-retire; row *moved to archive*, removed
from recall/consolidation/graph, links pruned, observations recomputed, kept for audit);
**restore** (`state=valid`). Only world/experience curable; observations are derived.
`…/{id}/history` = observation refresh history. Consolidation auto-reconciles in-stream
contradictions into one observation ("likes BMW"→"likes Toyota"). *No TTL/expiration
field* (unlike Mem0).

**Scoping (multi-agent).** *Memory bank* = fully isolated container (memories, documents,
entities, relationships, directives) — one per agent/user/session/context; auto-created
on first use; banks never see each other. Sub-scoping *within* a bank via `tags` +
`tags_match`; `observation_scopes` controls shared vs per-tag consolidation.
Bank config: `mission`/`directives`/`disposition` (affect reflect only),
`retain_mission`, `retain_extraction_mode` concise|verbose|custom, `entity_labels`.
`security/overview`: Memory Defense screens every retain for secrets/injection.

**Self-host.** MIT, runs Linux/macOS/**Windows** (operator is on Win11). Docker
`ghcr.io/vectorize-io/hindsight:0.4.9` (full ~9GB / slim ~500MB), Helm/K8s (worker
StatefulSet), pip `hindsight-api`/`-slim`/`hindsight-all` (in-process `HindsightServer`/
`HindsightEmbedded`), local MCP server w/ embedded Postgres. Needs Postgres 14+ + pgvector
(embedded **pg0** for dev; Supabase/Neon/RDS for prod) + an LLM key (OpenAI/Groq/Gemini/
DeepSeek/Ollama/local). Managed "Hindsight Cloud" also exists. `HINDSIGHT_API_WORKER_ID`
gives durable task claiming across restarts.

## Mem0 — COMPARISON (open-source)

License **Apache 2.0** (README). Two products, *same core loop*: OSS (self-host) +
Platform (managed). Paper arXiv:2504.19413. "New Memory Algorithm" (April 2026, v3).
Ops on `Memory`/`AsyncMemory` (OSS) and `MemoryClient`/`AsyncMemoryClient` (Platform):
`add, search, get, get_all, update, delete, delete_all, history(memory_id)`.

**Data model / scoping.** Memory = extracted fact string. Scoped by `user_id`,
`agent_id`, `run_id` (+ `app_id` Platform-only). ≥1 identifier required; filters
AND/OR/NOT. `memory_type`: **only `procedural_memory` implemented**; `semantic`/
`episodic` enum values exist but raise validation errors (not wired).

**Provenance / supersede / expire.** `metadata` dict; `expiration_date` (memory
expiration, both editions); `history(memory_id)` = change history; `timestamp`. Extraction
pipeline (`infer=True`): context-gather → retrieve existing → LLM decides ADD/UPDATE/
DELETE per fact. BUT README's v3 is **single-pass ADD-only** — "Memories accumulate;
nothing is overwritten" (docs/README tension; ADD-only is the current direction).
Platform-only supersession = **Dream** (background consolidation: distills patterns,
supersedes outdated facts, merges duplicates); plus Temporal Reasoning, Memory Decay,
`feedback()`, webhooks, export, batch, custom categories, org/projects.

**Graph memory (the transcript's borrow reason) — CAVEAT.** Native queryable graph is
**Platform-only**. OSS **removed** the external-graph integration (Neo4j/Memgraph/Kuzu/
Apache AGE) in v3; OSS now only extracts entities to *boost ranking* — no queryable
graph, no `relations` field. So "Mem0 graph memory" is not available self-hosted.

**Self-host.** `docker compose up` (`server/`); 25 vector stores, 18 LLM providers, 11
embedders; auth on by default. Solid, but multi-tenant surface (app_id, orgs/projects,
webhooks, billing) is marketplace machinery QMX doesn't need.

## Letta — PATTERN ONLY (belongs to Context Engine, not the provider)

*Memory blocks* = structured, **always-visible** sections of the context window (no
retrieval); prepended as `<memory_blocks>` XML. Fields: `label` (unique id), `description`
(drives how the agent uses it — critical), `value` (contents), `limit` (char cap).
Agent-managed via memory tools OR developer-managed via API; `read_only` flag.
**Shareable:** create a block, attach to N agents via `block_ids` → shared memory (update
once, visible everywhere); `attach`/`detach`/`delete`; agent-scoped ops by label.
Archival memory is the separate retrieval tier. → This is a *context-assembly* pattern
(Constitution #7 "context is compiled"), NOT a memory backend. Borrow: curated
always-in-context blocks (persona/policy), read-only shared blocks, attach/detach scoping.
Reject Letta-as-backend: it is a whole stateful-agent runtime (ADE, AgentFile) — QMX owns
its runtime.

## INHERITED FASHION (single-operator QMX does not need)

- **Mem0:** `app_id`, organizations/projects + member roles, webhooks, usage billing,
  Platform/OSS split, agent self-signup, group-chat — all multi-tenant/marketplace.
- **Hindsight:** Hindsight Cloud, access-key-gated multi-user control plane, the long tail
  of per-client marketplace integrations (Vapi/n8n/ChatGPT/…), Cosign supply-chain
  signing, large-scale worker StatefulSets. Keep the engine, drop the tenancy.
- **Letta:** ADE, AgentFile portability, multi-agent marketplace framing.

---

## QMX-owned contract (what to build instead)

The SDK owns `MemoryProvider`; Hindsight/Mem0 are adapters behind it (Constitution #3/#5).
Write path is **gated** (Constitution #9, register #45/#49): agent text is a *candidate*;
a deterministic validation gate promotes it — the provider is never the promotion
authority.

```
interface MemoryProvider {
  propose(c: MemoryCandidate): MemoryId          // stage; validation_state = "proposed"
  promote(id, v: ValidationResult): Memory        // after deterministic gate → validated/promoted
  recall(q: RecallQuery): RankedMemory[]          // token-budgeted retrieval
  get(id): Memory;  list(f: MemoryFilter): Memory[];  history(id): MemoryEvent[]
  supersede(id, by: MemoryId, reason): Memory     // replace, keep audit
  invalidate(id, reason): Memory                  // reversible retire (contradicted/stale)
  expire(id): Memory                              // TTL-driven (QMX-owned; Hindsight has none)
  scopes(): ScopeRef[]                            // banks / role / bot desks
  reflect?(q, scope): Reflection                  // OPTIONAL; off by default (QMX owns cognition)
}

MemoryCandidate { text; kind; scope: ScopeRef; provenance: Provenance[];
  supporting_artifacts: ArtifactRef[]; confidence: float; proposed_by; occurred_at;
  supersedes?: MemoryId; tags }

Memory { id; text; kind: semantic|episodic|procedural|decision-lesson;
  scope; provenance: Provenance[]; confidence;
  validation_state: proposed|validated|promoted|superseded|invalidated|expired|contradicted;
  supersedes?; superseded_by?; strength/proof_count; occurred_at; mentioned_at; expires_at? }

Provenance { source_kind: artifact|ledger|experiment|paper|conversation; ref; quote?;
  proof_count; retained_at }
RecallQuery { query; scope; tags; tags_match; kinds; max_tokens; temporal_window; min_confidence }
RankedMemory { memory; score; source_refs }
```

**Mapping to Hindsight (why it fits nearly 1:1):** propose→`retain` (into a staging
bank/`validation:proposed` tag); promote→`retain` into trusted bank or set Mental Model;
recall→`recall` (`max_tokens`, `types`, `tags_match`); supersede→`prefer_observations` +
`edit`; invalidate→`PATCH state=invalidated`+reason; history→observation `history`;
provenance→`metadata`+`context`+`document_id`+`entities`+observation source quotes/
proof_count; scope→bank + `tags`. QMX carries `confidence`/`validation_state`/`expires_at`
in metadata+tags+its own ledger (Hindsight lacks native confidence/TTL fields).

## Recommendation — first backend: HINDSIGHT

1. Its native model already implements most of hygiene decision #45: consolidation with
   *evidence + exact quotes + proof count*, reversible *invalidate w/ reason* + audit
   archive, edit, observation history, prefer_observations supersession, freshness
   verification. Mem0 OSS is ADD-only accumulate with no supersession and *no self-hosted
   graph*.
2. retain/recall/reflect ↔ propose/recall/(optional)reflect; three-tier Mental Model /
   Observation / raw Fact ↔ QMX candidate→validated→promoted.
3. **MIT** (most permissive) + self-hostable on the operator's own Windows box and
   research/trading nodes (embedded pg0 or Postgres+pgvector, local MCP, in-process
   Python, Helm workers for overnight autonomy) — matches single-operator + distributed
   + away-overnight requirements.
4. TEMPR gives temporal + graph retrieval natively (a trading/research domain needs "what
   did we conclude last quarter"); Mem0 OSS dropped graph.
5. tags/tag_groups scope per role/bot/desk within a bank; token-budgeted recall aligns
   with "context is compiled" (#7).

**Guardrails QMX must keep:** do NOT let Hindsight's auto-consolidation *be* the promotion
gate — stage candidates and promote only after QMX's deterministic gate (#9). Keep
`reflect` (mission/directives/disposition) OFF — cognition is QMX's. Model
`confidence`/`validation_state`/`expires_at` in the QMX layer. Keep the adapter thin so
Mem0 (or a future in-house store) can sit behind the same contract. Re-evaluate if
Hindsight's SOTA/paper claims don't hold on QMX's own eval.

## Open questions (this reference cannot settle)
- Does Hindsight's fact-extraction preserve QMX's structured provenance ("Paper A §3 /
  Paper B eq.7", register #300) faithfully, or does the LLM flatten it? Needs an eval.
- No native `confidence` or TTL in Hindsight — is metadata+tags enough, or does QMX need a
  side-table keyed by memory id?
- Hindsight extraction requires an LLM per retain — cost/latency at "800 strategy
  variants" scale vs Mem0's lighter add? Benchmark on real load.
- Does forcing all memory through one provider conflict with per-role memory emphases
  (Researcher semantic vs Trader episodic, #291/#292)? May need bank-per-role.
- Honcho was rejected on fit (#4954) but not examined here; confirm nothing in Honcho's
  scoping model is needed before closing the provider set.
