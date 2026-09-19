# Taskade official research

**Research scope.** Taskade app/workspace, Genesis app-building, projects as data assets, AI agents, automations/flows, connections, runs, templates and public access. Read-only public web/docs/repository review; no Taskade account, token, workflow, app, or publication was created. Access timestamps below are UTC.

**Access time.** 2026-09-18T08:31:08Z (and immediately following reads in the same session).

## Access and observed public surfaces

### TSK-OBS-01 — public landing/create surface

- **Classification:** `OBSERVED_INTERACTION` plus `UNVERIFIED` for gated behavior.
- **Source:** https://www.taskade.com/create (accessed 2026-09-18T08:31:08Z UTC).
- **Access mode/preconditions:** public unauthenticated HTTP read; no account or sign-in.
- **Observed:** the returned public page contains only the title “One Prompt. One App.” and the line “Powered by your workspace.” No editor, prompt box, generated app, run controls, or account state was exposed through this public read.
- **Limitation:** this does not prove the editor is unavailable; the official getting-started guide says an account and workspace are required and instructs the user to log in. An interactive editor journey, generation progress, preview, refinement, or publish flow was therefore not observed.

### TSK-OBS-02 — public community/app gallery

- **Classification:** `OBSERVED_INTERACTION` / `DOCUMENTED_CAPABILITY`.
- **Source:** https://www.taskade.com/community (redirects to https://www.taskade.com/apps; accessed 2026-09-18T08:31:08Z UTC).
- **Access mode/preconditions:** public unauthenticated page.
- **Observed:** page exposes Create / Connect / Clone navigation; searchable “Explore App Kits” with category filters (Quick Apps, Tools, Websites, Projects, Dashboards, Forms, Workflows, Commerce, etc.) and Free/Paid filters. Cards expose “Clone app free” links. Examples visible in the public response include Application Tracker Board, Airtable Sync Dashboard, Finance Tracker Dashboard, Investor Dashboard, and Broker Calendar.
- **Limitation:** opening or cloning a kit was not performed because it would enter an account/persistent-write journey. Card counts and labels are page content, not evidence that an app executes correctly.

### TSK-OBS-03 — public agent gallery

- **Classification:** `OBSERVED_INTERACTION` / `VENDOR_CLAIM`.
- **Source:** https://www.taskade.com/agents (accessed 2026-09-18T08:31:08Z UTC).
- **Access mode/preconditions:** public unauthenticated page.
- **Observed:** public page labels the product “AI Agent Platform - Your AI Workforce” and says agents can remember workspace, use tools, work together, receive instructions/knowledge/commands, and be used in projects, teams, or public embeds. It lists featured and category cards such as Math Problem Solver, To-Do List Management, Blog Post Creation, AI App Data Model Agent and AI Approval Matrix Agent.
- **Limitation:** cards are marketing/gallery entries; no agent chat or tool action was executed. The advertised agent behavior is therefore not independently verified here.

## Documented product model

### TSK-DOC-01 — app versus workspace and data assets

- **Classification:** `DOCUMENTED_CAPABILITY` (with vendor framing where noted).
- **Source:** https://docs.taskade.com/platform/workspace-dna.md (accessed 2026-09-18T08:31:08Z UTC).
- Taskade describes one unified workspace with three pillars: Memory (Projects & Databases), Intelligence (AI Agents), and Execution (Automations). Projects store tasks, notes, custom fields, documents and media; the docs list nine project views, custom fields, real-time sync and file/media uploads.
- The docs explicitly state that a Genesis app runs on the workspace rather than a separate backend, so apps share the workspace’s knowledge, agents and automations. This is a useful documented app/workspace relationship, but not evidence of implementation internals.
- The docs describe a workspace “DNA” graph of project, agent and automation nodes and directed edges showing reads/triggers/writes. They also describe EVE modes for Genesis, Projects, Agents and Automations and assistant-driven creation/management/editing. These graph/canvas and EVE descriptions are documentation claims; no signed-in canvas was observed.
- Structured data implication: projects may act as databases with custom fields and filtering/sorting; field changes can be automation triggers.

### TSK-DOC-02 — Genesis creation, refinement and deployment journey

- **Classification:** `DOCUMENTED_CAPABILITY` and `VENDOR_CLAIM` where outcomes are asserted.
- **Source:** https://docs.taskade.com/taskade-genesis/genesis/getting-started.md (accessed 2026-09-18T08:31:08Z UTC).
- Preconditions in the guide are a Taskade account, a business problem and a workspace. It gives two starting paths: blank prompt or cloning a ready-made app/community kit, both landing in the Genesis editor.
- Documented journey: describe who uses the app, actions, automatic responses and desired data outcome; log in at `/create`; navigate to a workspace; use the AI prompt box; generate; preview/test; refine through natural-language edits; then choose private workspace use, custom domain, community sharing or public link. The guide also documents a hosted Genesis App MCP option for Business+.
- Claimed generated components are a database, AI assistant, automations and file management. Optional context files may include brand assets, forms, screenshots, documents and data samples; the guide says these are stored in the project’s Media tab. Because this is a written guide, generation time (30–90 seconds), correctness and “fully functional” output remain vendor claims until exercised in an authorized account.
- The guide explicitly says publishing is a side effect and warns about API secrets; no publishing was attempted.

### TSK-DOC-03 — agents, knowledge, commands and multi-agent execution

- **Classification:** `DOCUMENTED_CAPABILITY` / `VENDOR_CLAIM`.
- **Source:** https://docs.taskade.com/ai-features/ai-features/ai-agents-getting-started.md (accessed 2026-09-18T08:31:08Z UTC).
- Agents are documented as specialized assistants that read documents/projects, answer questions, create tasks, send emails, update spreadsheets and specialize by role. Creation paths include natural-language description, manual configuration, ready-made templates and community templates.
- Knowledge inputs documented: uploaded PDFs/Word docs/spreadsheets, websites, linked Taskade projects (kept updated as projects change), and YouTube videos. Memory is split into session memory (conversation), knowledge memory (uploaded permanent information), and project memory (live workspace project connection).
- Invocation paths documented: Agents tab → select agent → New chat; project chat → choose agent; slash commands such as `/write-summary`; and an agent sidebar. The guide documents file attachments for images, documents, spreadsheets and code, with visible processing/status context in EVE chats.
- Agent tools documented include Taskade task/project/data tools, web search, Gmail, Slack/Teams/Discord, Sheets/databases and automation triggers. Multi-agent teams are described as concurrent/background agents with collaboration and context retention; human-in-the-loop controls are claimed for action approval, escalation, audit trails and overrides.
- The guide documents agent-centric automations: choose connector trigger, configure trigger, set agent as processing component, add actions, then test/deploy. It does not expose a public run-log schema or guarantee exactly-once behavior.

### TSK-DOC-04 — flow/automation shape and runs

- **Classification:** `DOCUMENTED_CAPABILITY`; execution outcomes remain `UNVERIFIED`.
- **Source:** https://docs.taskade.com/automations/automation.md (accessed 2026-09-18T08:31:08Z UTC).
- The documented flow shape is `Trigger → optional Condition/Filter → Actions`, with optional EVE AI steps and integration steps. Examples include form → classify → create task → notify, webhook → normalize → update CRM → log result, and schedule → weekly summary → digest.
- Triggers include project events (task added/completed/assigned/due, comment, custom field update, project created, media file added), webhook, form, schedule, mailhook and connected services. Actions include create/update tasks, update fields, call webhooks and send notifications. Conditions/branches route cases; loops and AI classify/extract/draft steps are documented in the workspace overview and automation catalog.
- “Run” is described operationally as background 24/7 execution, but public docs reviewed here do not provide a stable run identifier, execution event schema, replay/idempotency contract, per-step result model, or public run-history UI. These are `UNVERIFIED` and should not be inferred from the marketing phrase “run 24/7.”

## Official repository/API evidence

### TSK-REPO-01 — Workspace MCP repository

- **Classification:** `REPOSITORY_SOURCE` (official association verified from the Taskade GitHub organization and repo links).
- **Sources:** https://github.com/taskade/mcp and https://raw.githubusercontent.com/taskade/mcp/main/README.md (accessed 2026-09-18T08:31:08Z UTC).
- The README identifies this as Taskade’s official Workspace MCP and says it exposes 62 tools for workspaces, projects, tasks, AI agents, agent chat, webhooks, knowledge bases, templates, media and sharing. It distinguishes three MCP surfaces: Workspace MCP (local stdio/personal token, read/write content), hosted Genesis App MCP (OAuth, editing published app code, Business+), and in-product MCP Connectors for external services.
- Tool taxonomy gives a concrete capability/data model: workspace listing/folders; project details/copy/complete/restore/members/fields/share links/blocks/tasks; task CRUD, move, assignees, dates, notes and field values; agent generation/configuration/public access/conversations; project/media knowledge attachment; templates (`folderProjectTemplatesGet`, `projectFromTemplate`); media list/details/delete; agent chat (`promptAgent`, conversation reads); and real-time webhooks (`subscribeWebhook`, `unsubscribeWebhook`). This is repository/API surface evidence, not proof that each tool is enabled on every plan.
- The README says some endpoints are gated on free accounts and that paid plans cover automation access. It requires a personal token for local MCP. No token was requested or entered.
- The repository lists API v1/v2 base URLs and says the server talks only to Taskade public API endpoints. It also includes examples that chain template copy, task creation/movement, assignees, knowledge attachment and public agent publication. These are example recipes, not executed runs.
- The same README says OpenAPI 3.0+ specs can be code-generated into MCP tools. This suggests a reusable adapter boundary for QMX integrations, but it is an adaptation opportunity, not a claim about QMX implementation.

### TSK-REPO-02 — official docs repository

- **Classification:** `REPOSITORY_SOURCE`.
- **Source:** https://github.com/taskade/docs (accessed 2026-09-18T08:31:08Z UTC).
- GitHub identifies `taskade/docs` as public official documentation for Taskade, with REST and Action APIs, MCP and Genesis documentation; the README links back to `docs.taskade.com`. This verifies repository association. The product source itself is not public in this repository, so no internal architecture should be inferred.

## Relevant capability implications for QMX (proposals, not observed Taskade behavior)

1. **Enabling requirement candidate — explicit app/workspace scope.** QMX app authoring should bind an app to an explicit workspace/project scope and expose which data, agents and automations are shared. Preserve a distinction between an authoring copilot (can propose/edit definitions) and an app-use copilot (can query/operate only within granted runtime scope).
2. **Enabling requirement candidate — typed flow graph and job handle.** Represent a workflow as trigger, condition/filter, action and AI-step nodes with typed inputs/outputs, a durable run/job handle, step status, logs, retries and cancellation. Taskade’s public material establishes the useful shape but leaves run IDs, replay and idempotency `UNVERIFIED`; QMX should make those explicit rather than copying the omission.
3. **Enabling requirement candidate — data assets and knowledge links.** Treat files/media, structured records, projects, datasets and agent knowledge links as first-class versioned assets. Preserve provenance and live-vs-snapshot semantics when an agent consumes a project or uploaded file.
4. **Reference scenario — natural-language editing with preview.** An author can prompt an app/flow change, see a diff/preview and test with non-production fixtures before saving/publishing. Genesis’s documented prompt → preview → refine journey is evidence for the scenario; no live editor was observed.
5. **Reference scenario — template/kit reuse.** Support discoverable, versioned templates that can be copied into a new workspace/project with parameter substitution, ownership and rollback. Taskade’s public gallery and MCP `projectFromTemplate` are evidence for the relationship, not a demand that QMX mirror its UI.
6. **Optional future app — connector catalog and external action adapters.** A connector registry should declare auth requirements, trigger schemas, action schemas, scopes and plan/permission gates. Taskade’s 100+ integrations and MCP connector split are vendor claims/documented surfaces; QMX should not imply external execution until a connector is configured and authorized.
7. **Enabling requirement candidate — approval/audit boundary.** Any agent action that sends, publishes, mutates external data or consumes paid compute should expose an approval gate, audit event and stop/override control. Taskade documents these controls, but their production behavior was not tested.

## Unknowns and non-observations

- No signed-in Taskade workspace, Genesis editor, agent chat, automation builder, preview, run history, failure state, plan-gated endpoint or live external connector was accessed.
- No account was created; no API key/token was entered; no file was uploaded; no app/workflow/agent was created, cloned, saved or published.
- Official public docs are rich but combine normative instructions with promotional claims. Claims such as “real-time sync,” “24/7,” “persistent memory,” exact tool counts, model routing and generated-app completeness should be treated as vendor claims until independently tested under an authorized account and plan.
- Nothing here establishes Taskade’s backend implementation, storage model, consistency guarantees, security boundary, pricing entitlement, or production readiness for trading/ML workloads.

## Source index

1. https://www.taskade.com/create — public create surface.
2. https://www.taskade.com/apps — public gallery/community apps.
3. https://www.taskade.com/agents — public agent gallery.
4. https://docs.taskade.com/platform/workspace-dna.md — workspace, memory/intelligence/execution, projects/databases, EVE and graph model.
5. https://docs.taskade.com/taskade-genesis/genesis/getting-started.md — Genesis prompt, context files, preview/refine/publish journey.
6. https://docs.taskade.com/ai-features/ai-features/ai-agents-getting-started.md — agent creation, knowledge, tools, chats, teams, approvals.
7. https://docs.taskade.com/automations/automation.md — trigger/action/condition/AI flow shape and trigger catalog.
8. https://github.com/taskade/mcp — official MCP repository.
9. https://raw.githubusercontent.com/taskade/mcp/main/README.md — MCP tool taxonomy, auth/plan notes, examples and API surfaces.
10. https://github.com/taskade/docs — official docs repository association.

