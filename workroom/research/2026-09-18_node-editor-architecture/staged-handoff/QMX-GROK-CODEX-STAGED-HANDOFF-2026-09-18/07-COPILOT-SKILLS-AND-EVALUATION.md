# Copilot profiles, skills, hooks and evaluation — design seed

> Process update: use `10-STAGED-PROCESS-AND-REVIEW-CONTRACT.md` for the Grok → Codex → Grok handoff and the latest delegation rules. Historical evidence is unchanged.

**Status:** proposed integration design for investigation, not installed skills, API definitions or a second agent runtime. Reuse current QMA mechanisms where they fit; identify explicit amendments where they do not. Source leads: the supplied audit's Session/context/memory/plugin findings and the transcript's final authoring/app-use distinction.

## One product identity, distinct work and permission scopes

The user may experience QuantMind/QMX Copilot in a main authoring workspace or an app-specific companion panel. Both can use QMA infrastructure and configurable model routing. A new session must not inherit another session's full toolset, account target or memory indiscriminately.

An authoring session can create candidates using granted files, code, tool, test, compute and composition operations. An app-use session can inspect, ask questions, invoke exposed operations, change allowed runtime inputs, and create a change request. It cannot edit the installed implementation or its own permission profile. The number of models, agent runs and specialist instances is an implementation question, not fixed by one copilot name.

## Proposed structured context envelope responsibilities

The actual schema belongs in the architecture; these are fields to assess:

- Session and profile identity; owner/principal; context revision and timestamps.
- App definition/version and installed instance; relevant workspace/draft lineage.
- Explicit selected objects, chart interval, dataset release, models, run/attempt and outputs.
- Authorized operations and effective grants with revocation/revalidation rules.
- Broker, venue, account, role/mode, credential reference, provider and execution environment scope where relevant.
- Relevant docs/skills references and untrusted-source labels.
- Work status and explicit result/evidence refs; not a copied private reasoning transcript.

The host compiles/grants context. Changing a visible tab does not overwrite it. Selection updates have explicit target and revision checks. A command records the context and target under which it was accepted. Schema validity alone is not permission to act.

## Skill suite to adapt, not blindly install

| Proposed skill purpose | Expected behavior | Required checks |
|---|---|---|
| Discover capabilities | Find existing operations/defaults before creating new code; explain configured versus unavailable integrations. | No fabricated tool or adapter; schema and environment inspection. |
| Author a composition | Turn a goal into drafts, connected operations, bounded subflows and tests at useful granularity. | Valid ports/cardinality; no accidental whole-board execution; requirements trace. |
| Investigate an app result | Retrieve the exact run inputs/outputs/logs, distinguish observed evidence from interpretation and invoke exposed analysis. | App-use-only operations; correct version/account; citations to records. |
| Hand off an improvement | Create a scoped change-request artifact and new authoring session with declared lineage. | No source mutation in app-use; no excess private context copied. |
| Author domain components | Use QMF/QML/QMB or other legitimate owner contracts when building a policy, model, provider or strategy. | Existing interface requirements, conformance, complete input/output declaration and proposed amendments. |
| Design a data recipe | State input meaning, provider revision, point-in-time joins, units and gaps before analysis. | No look-ahead; reproducible input refs; no unapproved data-source substitution. |
| Create/evaluate a skill | Draft skill and dependency declarations, test activation and behavior, save a versioned candidate. | Installation separated from authoring; agent text cannot self-grant tools or pass its own gates. |
| Package and explain an app | Bind documented capabilities, defaults, workflows, presentation and copilot profile into a distributable candidate. | Compatibility/permissions/privacy; no mandatory private chats or credentials. |
| Plan a deployment change | Assemble a versioned readiness and transition plan using runtime state and actual requirements. | No guessed positions, permissions, hardware or external outcomes; no live activation in this assignment. |

These can be one or several skills according to QMA's actual skill system. Do not add personas simply because the table has rows. A skill's documentation, a reusable loop body, and runtime loop state remain distinct.

## Tools needed by the copilot

Audit existing equivalents for discover/query/inspect, create/edit/validate draft, run selected work, inspect attempts/logs/results, cancel/reconcile, request context, author/evaluate candidate skills, package/export, and preflight deployments/environments. Name actual APIs only after source inspection. Tool availability is derived from host-granted contributions, not implied by the skill text.

Operations callable by humans and agents should share the same deep behavior and owner-side validation, with explicit principal-specific permissions. File or CLI access is not a backdoor around installed app-use restrictions.

## Enforcement hook families to inspect/extend

Use existing QMA events first; proposed additions need complete lifecycle definition, not a name-only hook. Relevant moments are session/profile creation; context update; tool/operation invocation; draft validation; job placement; external egress; package/skill registration; dependency upgrade; deployment preflight; evidence append; cancellation; and reconnect/recovery.

For each event specify owner, before/after meaning, allowed result, side effects, timeout and failure behavior, provenance, cleanup and revalidation. Never introduce a veto that silently discards required audit/evidence records. A model-authored hook cannot approve privilege escalation or overwrite a failed deterministic check. Review current exceptional timeout laws instead of replacing them with a generic “deny everything.”

## Memory and long-work continuity

Trace currently bound MemoryProviders, scope keys, admission, recall budget, history, supersession and invalidation. Validate the default context compiler and whether compaction/RLM paths are actually integrated. Cross-session retrieval is explicit and attributed. Authoring lessons may be reusable, while private account facts and external content remain appropriately scoped.

Work records, checkpoints and account state are not memory. A durable record should be consulted for “what happened?”; a recalled lesson may inform “what should we investigate next?” Exported apps include authored docs and allowed lineage, not an implicit copy of the user's whole memory.

## Evaluation approach inspired by Caliper

Study the current Caliper repository before adoption. Evaluate conceptual transfer and any adapter work required for QMA; do not assume supported CLI runners equal QMA compatibility. Prefer objective assertions for artifact shape, effects, scope and commands. Use independent review where interpretation is necessary; record uncertainty.

Test normal, edge, adversarial and non-activation cases. Include neighboring skills so discovery/activation is exercised rather than always pasting the target skill into the prompt. Compare with the skill absent when measuring its incremental value. Pin skill, tool, model/deployment and case versions; repeat stochastic cases and record all attempts, not only the best one. Finite tests are not a universal proof.

Essential cases include app-use attempting source edits; retrieval of the wrong version/account; tab switches during long jobs; source documents requesting credentials; missing data/GPU/API access; incomplete skill outputs; generated false-success claims; cross-session memory leakage; revised package during a run; duplicate placement after a timeout; and factual explanation when the original specialist no longer exists.

Do not give the same proposed change unchecked control over both the behavior and the verifier. Human approval, code conformance, domain quality and permission to deploy are separate gates.


## September 18 contribution-awareness

A copilot discovers host-published operation descriptions, app exports, version bindings, context providers and relevant skills. Installing an extension does not automatically grant a session its requested rights or switch a running task's target. Composite-app profiles may reference component capabilities without copying private context or inventing a union of permissions. Inspect Hermes public tool dispatch and plugin/provider/context surfaces as references alongside existing QMA. Keep descriptive skills, executing loop state, middleware, hooks and authorization distinct.

Skill and scenario evaluation includes correct activation/non-activation, behavior under changed model/provider configuration, schema/refusal paths, misleading tool output, and scoped history use. The independent Codex architecture challenge and Caliper-inspired future skill tests serve different roles.
