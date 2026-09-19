# MCP Apps and modular departmental workspaces

Date: 2026-09-14. Status: research and design propositions, not an adopted UI contract or implementation plan. Continues the [platform inventory](qma-current-system-ux-inventory-2026-09-14.md). No DESIGN.md or EXPERIENCE.md finalization.

## User direction captured

Mubarak proposes a persistent UI with replaceable tools, substantial departmental worlds, and room to extend QMX. He identifies QMA as the agent SDK and asks whether MCP Apps can help with a separate UI extension layer. Local versus remote execution must be visible. Portfolio management should accommodate different mandates and methods, including crypto and FX, beyond the existing Book/BMS surface. The proposed Desk-to-Role-to-Agent layout hierarchy is an exploration, not an agreed navigation tree.

## What the references establish

**MCP Apps:** tools can declare HTML UI resources that a supporting host renders in a sandboxed iframe. An app communicates with its host and can invoke tools through it. The SDK offers an AppBridge for host developers; the project provides a basic host example rather than a supported complete host product. This is a practical extension route, not a ready-made QMX desktop. [Official API overview](https://apps.extensions.modelcontextprotocol.io/api/), [AppBridge module](https://apps.extensions.modelcontextprotocol.io/api/modules/app-bridge.html).

The stable specification negotiates host capabilities and inline/fullscreen/picture-in-picture display modes. App-only tool visibility is scoped to the same server connection; it is not an operator permission grant. QMX-specific docking, cross-panel selection and durable view restoration need additional host design. Do not assume standardized persistent application state merely because an app can be reopened. [Stable specification](https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx).

**DeepSeek Harness:** the Cordis primer describes service access, dependency injection, events and reversible plugin registration. These are useful lifecycle ideas, not a desktop layout prescription or a reason to replace QMA with another runtime. [Cordis primer](https://deepseek-harness.github.io/deepseek-harness/en/reference/cordis-primer).

The more relevant UI references are its typed, owned extension slots and its per-session right sidebar. Features contribute views through declared locations. The sidebar opens addressable resources in tabs and panes, with open/split/float/close operations. Reopening the same resource/view identity can select the existing tab. Crucially, its documented sidebar resets on refresh, and its internal layout engine is not a stable extension interface. Borrow the composition idea; specify QMX persistence independently. [Slots](https://deepseek-harness.github.io/deepseek-harness/reference/subsystems/slots), [Right sidebar](https://deepseek-harness.github.io/deepseek-harness/reference/subsystems/sidebar-right).

## Proposed division of responsibility

| Layer | QMX responsibility |
| --- | --- |
| QMA and the existing platform services | Durable actors, missions, tasks, execution, authority, evidence and domain operations. Preserve ordinary Python use. |
| QMX desktop host | Department/world navigation; opened work; selected context; pane layout; execution-location and attention indicators; restoring views by stable references. |
| Native UI contributions | Department-specific overviews, navigation entries and tightly integrated views with explicit contribution contracts and cleanup. |
| MCP App adapter | Mount compatible interactive tools inside the host and mediate their calls through existing platform authority. One extension mechanism, not the only renderer. |

This division is a design proposal. An MCP connection alone does not give a tool the departmental context, permissions, data or lifecycle semantics it needs. A result-comparison app is plausible; an arbitrary market-data app is not automatically a QMX portfolio manager.

## Layout proposition to test

Keep **global entry → opened world → world-owned local navigation and content**. Consistent controls and identity do not require identical department interiors.

1. A departmental overview answers: what does this desk own, who is responsible, what is underway, and what needs attention? It links to durable work and shared artifacts. It need not default to a KPI dashboard.
2. Opening a mission or investigation brings its discussion, activity and appropriate working surfaces together. Performance evidence, scenario tables, charts or a graph can occupy those surfaces. Source and changes remain available when relevant.
3. Quants are persistent members with inspectable responsibilities, memory/mailbox scope and current work. Roles are contracts/configuration; executing agents and subagents are inspectable within activity. Do not require five successive layouts just because the backend has five ontology levels.
4. Tool surfaces may be opened, hidden, pinned or replaced without changing the identity of the work. Cross-department references should open the same underlying artifact, with provenance and owning scope retained.

“Message this department” still needs an explicit routing contract. Do not invent a universal lead inbox: the prior inventory records unresolved lead/catch-all behavior.

## Execution and state representation

Show ownership and execution placement separately: the responsible Quant/desk can remain the same while workers run elsewhere. Proposed readable labels include “Local · running”, “Remote: research-node · running”, and “Remote: research-node · connection lost; last confirmed running at …”. Color and icons supplement these labels.

A client losing contact does not prove a job stopped. Distinguish connection state, last observed run state and backend `unknown`. Closing a panel is a view action, not a cancellation. Laptop-off continuation requires a reachable running backend; a remote-looking layout cannot supply it.

Reserve distinct concepts for **saved workspace arrangement** and **execution environment** until naming is reconciled. Current QMA documentation treats Project/Workspace as presentation aliases, and execution environments include local, Docker, remote container, remote host, browser and desktop. A workspace is not necessarily a server.

## Portfolio expansion

Provide an extension seam for mandate-specific portfolio views and analyses without assuming asset class alone requires a separate underlying system. Crypto and FX may need different data, exposure conventions, venues, valuation assumptions and policies. Comparable totals must expose those assumptions. Book/BMS remains an operational concept; it does not close the user's broader portfolio-product ambition.

The `pm` conflict remains open: current QMA documentation says Product Manager; the desired UX lens says Portfolio Manager. Do not silently relabel the backend role.

## Local evidence and remaining contract work

Current documentation explicitly defers UI SDK/contribution surfaces under GAP-0081 and excludes `ui_view` from the v1 QMA plugin manifest. Sources: [QMA core](../../../../../docs/components/qma-core.md), [QMA wire](../../../../../docs/components/qma-wire.md), [plugin contract CT-42](../../../../../docs/contracts/ct-42-qma-plugin-manifest-context.yaml), [execution environment CT-46](../../../../../docs/contracts/ct-46-qma-execution-environment-job.yaml), [Sept 14 architecture spine](../../../architecture/architecture-QMX-2026-09-14/ARCHITECTURE-SPINE.md).

Targeted searches found no MCP Apps protocol markers in the inspected docs or tracked `integration` source. This is not an exhaustive audit of every branch or concurrent unpublished change. Documented/source-inspected contracts are not proof that the complete runtime works end to end.

For reconciliation with Grok: agree the stable context references supplied to a mounted view; distinguish operator tool actions from agent actions; define how calls pass through existing authority; define view-state persistence and resource freshness; define extension removal and unsupported-host behavior. High-volume grids and market streams also need a measured rendering/data-update path rather than assuming a chat tool response is sufficient.

## Bounded next experiment — proposed, not executed

Test one read-only cost-sensitivity comparison surface against sample data. Use native QMX framing for department, mission, selection and execution status; mount the comparison as an MCP App. Test opening and replacing a view, changing instrument selection, and restoring context after closing/reopening. Add docking and persistence as explicit host behavior. Simulate remote disconnection without changing the job's last confirmed state. Ordinary UI filtering should not require an LLM turn.

This experiment would answer whether the extension boundary feels coherent before investing in a full SDK or another polished screen generation. Its sample data and simulated execution must be labelled. No backend implementation, service installation, trading action, or external design generation was performed in this research pass.
