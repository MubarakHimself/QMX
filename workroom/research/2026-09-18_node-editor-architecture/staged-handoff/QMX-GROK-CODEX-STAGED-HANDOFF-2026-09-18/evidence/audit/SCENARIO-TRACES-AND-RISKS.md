# Scenario traces and risks

These traces are diagnostic probes, not accepted requirements or UI designs. Each trace has a stable id for later requirements and UX work.

## Representative journeys

### RECON-SCN-01 — app-use result to authoring change request

- Goal: inspect a macro/sector result in an installed app, query its originating run/specialist, produce a scoped change-request artifact, and open a separate authoring session for v2 without mutating v1.
- Prerequisites/scope: app definition/version, installed instance, selected result, run/attempt/evidence ids, dataset release, operator principal and allowed operation names.
- Interfaces/records: app query/operation interface; QMA EvidenceHandle/context; durable work record; immutable change-request artifact; separate authoring session with a new candidate revision.
- Execution/outcome: app-use may read and invoke only exposed operations. Authoring may create files/definitions and tests. The authoritative outcome is the new candidate artifact plus lineage to v1, never an in-place edit.
- Interruption: reconnect by session id and immutable result/change-request ids.
- Observed support: QMA has handle references, evidence records and frozen Agent capabilities. The current Session record has only execution_model/autonomy and no app instance/version or profile.
- Missing seam/risk: product-session/app-context contract, app-use permission profile and change-request artifact. Without them, app content or visible navigation can retarget privileged work. Priority: critical/high.

### RECON-SCN-02 — concurrent session isolation

- Goal: workflow-building, strategy-authoring and ML sessions coexist; navigation and reconnect never mix targets, permissions, history or memory.
- Prerequisites/scope: three session ids, explicit owner, profile, app/workspace/asset refs, environment refs and capability snapshots.
- Interfaces/records: durable product session record; QMA Agent spawn capability snapshot; scoped context update events; memory retrieval with provenance.
- Execution/outcome: every command carries the session/context version and target ref. UI tab state is merely an attachment.
- Interruption: reconnect resumes the chosen session, not “current tab”.
- Observed support: QMA execution sessions are independent and Agent capabilities freeze at spawn; attachment is deliberately non-durable. V1 MemoryProvider is only a protocol/NoMemoryProvider and scopes do not establish app/session isolation.
- Missing seam/risk: durable product-session context and explicit cross-session retrieval. Automatic global memory merge would create authority leakage. Priority: critical/high.

### RECON-SCN-03 — default versus alternative system policy

- Goal: compare system A using Book/BMS/SQS/MIS with system B using another allocation/risk/sizing composition and optional/no MIS.
- Prerequisites/scope: common market data and evaluation protocol; separate policy definitions; exact semantic/package/config/model/input versions.
- Interfaces/records: QML or another authorized authoring owner emits behavior; QMB compiles an evaluation config; QMF data/evidence stores inputs/results; QMN hosts an approved deployment.
- Execution/outcome: results must use the same evaluation semantics where comparable and explicitly label non-comparable accounting.
- Observed support: QMB compares complete Book/BMS candidates. Its compiler requires Book/BMS fingerprints/fragments and CT-28 replay binding; QMN compiles BMS/Book layers and runs Book/BMS rulebook modules.
- Missing seam/risk: a framework-owned system-policy contract and policy-neutral run/deployment envelope. Fake Book/BMS wrappers would change meaning. Priority: critical/high.

### RECON-SCN-04 — two MIS versions and authority

- Goal: production consumes MIS v1 while MIS v2 runs shadow; separately, distinct active consumers can use pinned versions without two writers claiming one authority.
- Prerequisites/scope: model/data/config fingerprints, consumer ids, output stream authority, deployment version and account/system binding.
- Interfaces/records: model artifact registry; shadow output journal; comparison projection; consumer binding; activation decision.
- Execution/outcome: shadow writes a non-authoritative stream. An active consumer cites exactly one authoritative version.
- Interruption: restart restores producer/consumer binding and sequence; unknown tail remains unknown.
- Observed support: QMN has MIS catalog/training/shadow-shaped modules and durable journaling patterns. Complete versioned consumer authority was not demonstrated.
- Missing seam/risk: model/package identity and active-consumer binding contract. Priority: high/medium.

### RECON-SCN-05 — multiple brokers and accounts

- Goal: same instrument label exists at two venues/brokers and several accounts; dashboard aggregates authorized reads without cross-account commands.
- Prerequisites/scope: VenueId, Instrument, account, role, environment, credential reference, source-provider id and command ownership.
- Interfaces/records: QMF identity; QMN account-binding roster; VenueClientPort; read-model query returning source/account/currency/freshness/mode metadata.
- Execution/outcome: command stream key is venue/account; UI filters do not mutate command target.
- Interruption: reconnect and reconciliation happen per command stream; unknown submission outcome blocks unsafe retry.
- Observed support: multi-account roster is implemented, rejects a global default and keys command streams by venue/account. Source provider is orthogonal to VenueId. Production venue selection is fixed to cTrader/conformance/replay.
- Missing seam/risk: external broker adapter discovery and dashboard-to-command anti-confusion contract. Priority: critical/high.

### RECON-SCN-06 — point-in-time multi-source study

- Goal: combine sector membership, prices and macro/sentiment data with different timestamps/revisions; changing provider must not alter the old study.
- Prerequisites/scope: provider/native id/revision, event time, known-at, units/currency, entity mapping, license/permission, dataset recipe version.
- Interfaces/records: QMF source observation/intake; QMB data provider adapters; immutable dataset manifest/recipe; derived dataset artifact.
- Execution/outcome: study pins each input release and produces a rebuildable dataset id.
- Interruption: checkpoints retain completed partitions and quota/refusal state.
- Observed support: QMF preserves event_time, known_at, source and revision; QMB has market-data ProviderAdapter. The generic ProviderRecord/SourceObservation path has no general typed payload for the requested non-quote domains and no recipe contract was found.
- Missing seam/risk: typed multimodal fact payloads, entity/schema catalog and point-in-time recipe/builder. Priority: high/high.

### RECON-SCN-07 — compute placement and GPU request

- Goal: run notebook/model operation on provisioned local GPU, provisioned remote GPU, missing entitlement and no-compatible-environment paths.
- Prerequisites/scope: ComputeRequirements, hardware inventory, image/dependency/CUDA version, credentials/entitlements, data upload policy, budget and cancellation/checkpoint contract.
- Interfaces/records: QMA ExecutionEnvironment and ComputeProvider; JobHandle; task/outbox/log/artifact records.
- Execution/outcome: “requested” never means “available”; placement returns chosen environment or a typed unsupported/unavailable refusal.
- Interruption: cancellation and unknown-tail state are durable; checkpoint compatibility is validated before resume.
- Observed support: environment/compute/job-handle ports and placement tests exist. No audited GPU-specific capability, provisioned environment or end-to-end job was found; concrete always-on host is GAP-0062.
- Missing seam/risk: GPU/image/entitlement declaration and artifact return contract. Priority: high/medium.

### RECON-SCN-08 — install and run a mini-app on another installation

- Goal: another user installs a package, configures their own credentials, opens its app and invokes its workflow without the author's private chats, permissions or files.
- Prerequisites/scope: signed/versioned package, dependencies, exported operations, presentation, defaults, docs, optional copilot profile and migration/rollback metadata.
- Interfaces/records: package definition; installed instance; credential bindings; run; deployment; dependency lock; install journal.
- Execution/outcome: host grants requested capabilities; app profile cannot grant them. Private authoring lineage is excluded unless deliberately exported.
- Interruption: partial install rolls back or remains explicitly inactive; uninstall detects dependants.
- Observed support: QMA plugins and QMF registry/migration primitives exist. No unified app envelope, dependency solver, UI contribution SDK or install lifecycle was demonstrated.
- Missing seam/risk: package/instance/run/deployment split and compatibility lifecycle. Priority: high/high.

### RECON-SCN-09 — headless reuse parity

- Goal: invoke one capability directly, through CLI/tool, and as a selected node with equivalent inputs, outputs, errors, permissions and evidence.
- Prerequisites/scope: registered operation descriptor and schemas; caller principal/profile; execution environment.
- Interfaces/records: QMB Python/API/CLI/MCP doors or QMA ToolAdapter; operation invocation/attempt/log/output.
- Execution/outcome: every door calls the same deep module interface; presentation is optional.
- Interruption: cancellation/retry semantics belong to invocation, not terminal UI.
- Observed support: QMB has multiple doors and parity tests; QMA→QMB CLI transport tests passed in this audit. No generic node descriptor/typed port catalog spans arbitrary capabilities.
- Missing seam/risk: exported-operation descriptor and one authority check across all doors. Priority: high/high.

### RECON-SCN-10 — sequential rollout

- Goal: develop/evaluate a new system then replace a flat, stopped predecessor; separately handle non-flat or unknown-command cases.
- Prerequisites/scope: package/deployment versions, account binding, open positions/orders, command ownership, reconciliation state and operator approval.
- Interfaces/records: deployment plan; drain/stop/reconcile state; activation record; account command-owner lease; rollback record.
- Execution/outcome: flat predecessor may hand over after proof. Non-flat/unknown cases block or use an explicitly approved shared-account plan. Rollback never claims to undo fills.
- Interruption: disappearance after submit yields UNKNOWN and reconciliation; restart restores ownership before commands.
- Observed support: QMN has deployment switch, command identity, unknown outcomes, reconciliation and safe restart machinery for the current node.
- Missing seam/risk: generic system deployment/version and command-ownership contract across different policy packages. Priority: critical/medium.

### RECON-SCN-11 — specialist skill lifecycle

- Goal: authoring agent drafts a skill, evaluates correct/non-activation, versions it and requests supported registration.
- Prerequisites/scope: plugin/skill id, version, tests, requested tools/context and signer/principal.
- Interfaces/records: QMA Skill/procedure definitions; plugin manifest; validation report; install/registration request.
- Execution/outcome: skill text guides behavior but cannot grant tools or permissions.
- Interruption: failed validation leaves an inactive candidate; previous installed version remains.
- Observed support: QMA distinguishes Skill from Loop, validates plugin manifests and freezes capability grants at Agent spawn.
- Missing seam/risk: product-facing skill package install/rollback and evaluation record. Priority: medium/medium.

### RECON-SCN-12 — exported dependency between apps

- Goal: app B invokes exported operation/output from app A; upgrade/removal remains pinned, migrates explicitly or reports incompatibility.
- Prerequisites/scope: exported operation version/schema, dependency constraint, installed instance ids and permission grant.
- Interfaces/records: package manifest; exported operation descriptor; dependency lock; migration/uninstall plan.
- Execution/outcome: no visual automation; B invokes A's supported domain interface. Removal checks dependants.
- Interruption: partial upgrade leaves old compatible version active or marks B inactive with evidence.
- Observed support: QMF registry/versioning and QMA plugin dependencies/migrations provide primitives. No cross-app export contract or app lifecycle exists.
- Missing seam/risk: exported-operation compatibility and install dependency graph. Priority: high/medium.

## Sequential deployment state probes

| State | Safe interpretation | Required record/check |
|---|---|---|
| Old flat, no pending orders | Eligible for stopped handover after reconciliation and explicit activation | flat proof, pending-order proof, predecessor stop, new deployment version and account owner |
| Old draining; candidate demo only | Parallel evidence is safe when accounts/environments are distinct and labels remain explicit | separate account/environment refs and non-authoritative candidate status |
| Versions on distinct accounts | May run concurrently if credentials, data, exposure and command owners remain separated | per-account command streams and dashboard source/account labels |
| Versions share account | Not safe by version labels alone | explicit exposure partition, order/position attribution, single command-owner rules and reconciliation |
| Process vanishes after submit, before ack | External outcome is UNKNOWN, never automatic retry | command fingerprint, venue-native identity lookup, reconciliation journal |
| Rollback after new version changed external state | Restore software/config only; external positions/orders remain real | reconciliation, ownership reassignment and operator decision |

## Cross-cutting failure matrix

| Failure | Consequence | Existing mitigation | Residual/missing seam | Priority |
|---|---|---|---|---|
| Stale app/session context | Wrong asset/account/app is acted on | Session ids and frozen Agent capabilities | Durable app-context version and target pin absent | Critical |
| Concurrent edits | Candidate meaning silently changes | Fingerprinted immutable artifacts in registry | Draft revision/merge contract for workflows/apps absent | High |
| Revoked access/missing secret | Work continues with invalid authority | Credential references and typed refusals | Revocation propagation across running app/workflow not proven | Critical |
| Unknown external order outcome | Duplicate or conflicting trade | QMF venue UNKNOWN and QMN reconcile paths | Cross-system command owner during rollout absent | Critical |
| Duplicate events/submissions | Repeated side effect | Writer sequence, fingerprints, QMA producer/id dedupe | Generic workflow side-effect idempotency descriptor absent | High |
| Corrupted checkpoint/artifact | False resume or evidence | Fingerprints, staged migrations/backups | Cross-store linked restore proof absent | High |
| Provider revision/gap | Backtest meaning changes | source/native id/revision, known-at, corrections | Dataset recipe/release pin absent for heterogeneous data | High |
| Unsupported schema/package version | Silent semantic drift | format versions and typed refusals | App dependency/compatibility resolver absent | High |
| Exhausted quota | Partial study/job | typed provider refusal and QMA job states | Shared subscription/quota policy and checkpoint semantics incomplete | Medium |
| Inactive/partial app install | Calls missing capability | plugin load refusal/migrations | App activation and rollback journal absent | High |
| Expired product session | Stale commands/replay | wire principals/correlation primitives | Product-session expiry/re-auth contract absent | High |
| Cross-scope memory retrieval | Private/wrong context leaks | desk-scoped MemoryProvider concept | app/session scopes and provenance filter absent | Critical |
| Untrusted document/tool output | Privilege escalation/social injection | QMA capabilities and money-path deny-list | app profile/context sanitization contract absent | Critical |
| Changed model weights | Reproduction impossible | general fingerprint/artifact patterns | model artifact/deployment identity not uniformly wired | High |
| No compatible GPU/environment | False capacity promise | ComputeRequirements/JobHandle | GPU/image/entitlement declaration not demonstrated | Medium |

## Smallest representative falsification proof

A later architecture should be rejected if it cannot pass this one compact proof without fake wrappers:

1. Register two complete system packages against the same historical dataset: A uses current Book/BMS; B uses a materially different risk/sizing policy and no MIS.
2. Invoke both through the same exported headless operation from direct Python and a workflow node.
3. Produce comparable, provenance-complete QMB results without naming B a Book/BMS where that changes meaning.
4. Package B as an installed app instance with an app-use copilot that can inspect/rerun exposed operations but cannot edit source or switch account.
5. Deploy neither live; prove QMN (or a policy-neutral host interface) can validate B's deployment configuration for a distinct demo account, then refuse an unsupported shared-account transition.

Today the proof fails at steps 1 and 3 because QMB requires Book/BMS bindings, at step 4 because app/session/package contracts do not exist, and at step 5 because QMN's host and policy rulebook are not separated.
