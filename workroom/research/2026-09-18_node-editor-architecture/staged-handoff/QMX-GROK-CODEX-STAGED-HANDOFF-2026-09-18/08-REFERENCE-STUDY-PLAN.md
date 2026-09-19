# Primary-source reference study plan

> Process update: use `10-STAGED-PROCESS-AND-REVIEW-CONTRACT.md` for the Grok → Codex → Grok handoff and the latest delegation rules. Historical evidence is unchanged.

**Status:** research targets, not fresh verification in this packaging turn and not adopted dependencies. The URLs below come from the conversation or its source manifests. Reopen current primary documentation, resolve redirects, inspect relevant current repository code, record dates/revisions, and verify actual capabilities/licensing before drawing implementation conclusions.

Existing QMX studies may already contain useful adoption/rejection decisions. Start by finding them in `docs/`, `_docwork/`, `_bmad-output/`, `workroom/` and other applicable research directories. Do not redo a settled comparison without explaining the new requirement or changed evidence.

## References and specific questions

| Reference | Primary starting point | What to study for QMX |
|---|---|---|
| n8n | https://docs.n8n.io/ ; https://github.com/n8n-io/n8n | Node descriptors, exported workflow representation, explicit connections, code steps, subflows, triggers, logs/retries, draft/run/version lifecycles and AI authoring. Verify licence and embedding terms; do not call all code permissively open-source or assume JSON performs computation. |
| Taskade | https://www.taskade.com/ ; https://help.taskade.com/ | App/workspace versus workflows, agent tools, context-aware assistant, data/projects, connections, templates, preview and published use. Separate observed UI and documentation from inferred backend ownership. |
| OpenBB | https://docs.openbb.co/ ; https://github.com/OpenBB-finance/OpenBB | Provider contracts, standard/provider-specific parameters, data processing extensions, query discovery, app/widget definitions, linked parameters, API/config separation and packaging. Verify current open-source boundaries rather than assume an announcement released everything. |
| QuantConnect | https://www.quantconnect.com/docs/v2/ ; https://github.com/QuantConnect/Lean | Provider/broker separation, custom data, history/live subscriptions, security/universe identity, resolutions/consolidation, data normalization and calendars. Borrow mental models; do not adopt LEAN as QMX's execution engine by default. |
| StrategyQuant | https://strategyquant.com/ | Strategy generation versus parameter optimization, what-if/robustness methods, evidence and interactive experimental workflow. Verify claims; do not infer QMB speed parity or an existing GA from resemblance. |
| London Strategic Edge | https://londonstrategicedge.com/ ; https://londonstrategicedge.com/data | Dataset discovery/builders, API/WebSocket concepts, backtesting and ML studio user journeys. Verify endpoints, rights, data quality and actual behavior before proposing integration. Detailed browser study can proceed separately; it need not block architecture. |
| JSON Render | https://json-render.dev/ ; https://json-render.dev/docs/catalog ; https://github.com/vercel-labs/json-render | Component/action catalogue, rich registered components, state/data bindings, validation and supported renderers. Establish fit to the actual desktop host; not a domain runtime or authorization mechanism. |
| MCP Apps | https://modelcontextprotocol.io/extensions/apps/overview ; https://apps.extensions.modelcontextprotocol.io/api/ | Tool-associated views, host/app messages, context updates, capability negotiation, sandboxing and lifecycle. Native QMX views need not all be MCP Apps. |
| VS Code | https://code.visualstudio.com/api ; https://code.visualstudio.com/api/references/extension-manifest | Declarative contributions, activation, settings, compatibility, extension hosts, local/remote responsibilities and webviews/editors. Distinguish supported public extension surfaces from arbitrary host mutation. |
| Zed | https://zed.dev/docs/extensions/developing-extensions | Actual extension types, version/lifecycle, runtime and limitations. Do not assume all VS Code UI affordances are supported. |
| Cordis / DeepSeek Harness | https://deepseek-harness.github.io/deepseek-harness/reference/cordis-primer | Reversible contribution lifecycle, declared service dependencies and typed event/registration patterns. Check QMA's prior adoption scope; do not transplant agent-plugin privileges onto trading. |
| LangGraph | https://docs.langchain.com/oss/python/langgraph/overview | Workflow/agent composition, persistence, interrupts and state semantics as reference patterns. Current QMA decisions may reject hosting foreign runtimes; distinguish mental-model reuse from importing one. |
| Hermes | https://github.com/NousResearch/hermes-agent | Existing QMA inspiration: skill/tool/context/stateful-agent patterns. Audit local adoption first; no wholesale runtime replacement. |
| Caliper | https://github.com/edonadei/caliper | Skill activation, deterministic assertions, expectations, ablation, repeat attempts, isolated environments, stored results and backend adapters. Verify compatibility with QMA; do not assume listed CLI runners include QMA. |
| BMAD / CIS | https://docs.bmad-method.org/ ; https://cis-docs.bmad-method.org/ | Use installed workflows/skills first, verify conventions. CIS supports opportunity and user-journey exploration, not automatic architecture approval. |
| TypeSafe / Jev | https://typesafe.ai/blog/introducing-system-one-models-and-jev | Optional typed-model-output experiment; verify interface and evaluation semantics. Not presumed equivalent to a function-calling model or deterministic verifier. |
| Omarchy | Discover current official documentation/repository from the operator-named project. | Optional configuration, distribution and user-customization mental models. Do not port a Linux desktop's packaging assumptions into QMX without comparison. |
| Model subscription integrations | Current official documentation of the chosen provider. | Supported auth/API/CLI routes, usage boundaries and billing, only if needed for design. No implied embedding right, credential extraction or guaranteed provider availability. |

## Required study note format

`reference | exact URL/revision and checked date | observed fact | source type | existing QMX analogue | proposed adaptation | mismatch/licence/authority concern | what would falsify the fit`

Prioritize load-bearing questions. A long list of vendor features is not architecture. Citations must support the exact claim; a marketing page is a vendor statement, not a measured experiment.

## Browser-reconnaissance boundaries

Discover actual browser capabilities before promising interactive inspection. Use ordinary page navigation or code/docs when those suffice. An authorized signed-in session is not permission to purchase, change accounts, run costly training or bulk-download datasets. Record accessible versus gated surfaces, and collect concise screenshots only where interaction/design evidence matters. Do not capture credentials or unrelated personal data.

UI observations inform backend requirements and later journeys. They do not freeze layout or compel feature parity with the donor.


## September 18 additions and browser plan

Add the Hermes general plugin guide, Desktop Plugin SDK and dashboard/provider/context references listed in `14-REFERENCE-AND-TESTING-ADDENDUM.md`. Inspect their actual contribution, state, compatibility and trust behavior; do not call all of them one interchangeable plugin system.

The separate prompt `11-CODEX-BROWSER-RECON-LSE-AND-REFERENCE-JOURNEYS.md` provides LSE-first interactive reconnaissance and selected OpenBB/Taskade journeys. Run only where real browser controls and authorization exist. It returns evidence before/alongside Stage A, not a mandatory pause after every page or a reason to repeat the whole audit. Study internal APIs/file handoffs, BDD/stateful testing and mutmut as documented references for the new scope. Read installed BMAD/CIS skills rather than assuming public site instructions reflect custom local additions.
