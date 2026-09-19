# QMX layout-intent audit

Status: transcript-grounded correction to the current layout proposal. This is a discovery artifact, not an approved IA or wireframe.

## Scope and evidence

This audit rereads the original user messages in the local session record from the rejection of the party-mode journeys through the three image-attached dictations and the latest correction. It also visually rechecks the imported Hermes, thin-rail dashboard and Fincept screenshots, then contrasts them with `START-HERE-2026-09-12.md` and `reference-feature-mapping-2026-09-11.md`.

The three screenshots are references for different layers, not three candidate whole-product shells:

- `hermes-agent-layout-reference.png`: a deep agent workspace with session navigation, top work tabs and a conversation surface.
- `global-rail-dashboard-reference.png`: the thin left-hand entry/menu metaphor; its generic finance dashboard is not proposed QMX content.
- `fincept-terminal-layout-reference.png`: high-density global destinations, a distinct open-work tab row and a composable information canvas.

## The material correction

The current proposal reduces the layout question to two variants of one generic application shell:

1. global rail or global top navigation;
2. permanent department menu;
3. work-item tabs over one canvas;
4. contextual agent dock on the right.

That is not a faithful representation of the user's evolving model. The user's central idea is **navigation that opens durable domain/department worlds**, with each world allowed to have its own internal information architecture and layout. The global mechanism selects or opens a world; it does not force all QMX functions into one repeated rail/sidebar/canvas/dock composition.

The clearest original statement is: **“once I click ... on one of those items, a tab opens ... it has its own meaning; it’s like its own world.”** The Hermes reference was explicitly bounded: **“that’s just the agentic system”** and **“it’s one part of many.”**

Later, the user evolved the organizing unit from free-standing sections toward departments: **“when you enter a department ... [it] has its rail”** and **“it’s a dashboard for that specific department.”** The agent then becomes available inside the department and can open as a local panel/tab, but the user immediately marked the exact pattern as unsettled.

Therefore the first design question is not simply **left global rail versus top global navigation**. It is:

> What is the global workspace switcher, what kind of durable tab does it open, and what IA does the selected department/domain own after it opens?

Only after that can rail placement and agent presentation be compared meaningfully.

## Exact differences from the current two-layout proposal

| Current proposal | Transcript-grounded correction |
|---|---|
| Treats the thin rail or top bar as the principal shell choice. | Their placement is secondary. The important behavior is opening and returning to durable domain/department worlds. |
| Shows a department title and menu permanently beside a generic canvas. | A selected department owns a deeper local environment: an intentional overview plus department-specific navigation, tools and layouts. A common chrome may exist, but identical internal composition is not established. |
| Labels top tabs `Experiment \| Bot \| Scenario`, implying object/work-item tabs. | The user first described sections as browser-like tabs, then departments as possible durable workspace tabs. Whether tabs represent departments, sessions, projects, objects or a mixture is unresolved; the proposal chose too early. |
| Makes the agent a standard right-hand contextual dock. | Hermes is both a full agent world and a source of contextual agent behavior. Inside a department, the user described an agent opening as a mini-panel or mini-tab, but did not approve a permanently right-docked assistant. |
| Uses one representative content structure across departments. | The user wants daily intentionality mapped per department: “what does this department specifically need and what do the agents in this department need?” Different departments may require materially different canvases. |
| Risks treating Library, Experimentation and Trading Node as peer department menu entries. | The user distinguishes departments from global/shared or integrated product areas. STRATS Library is shared; Trading Node is one integrated operational area; Experimentation Lab is a candidate domain. Their exact relationship to the five QMA-informed departments remains open. |
| Places a generic run/connection status strip across both variants. | Status belongs to the active context. Research run state, remote-agent state and live-trading state must not be collapsed into one global status metaphor. |
| Frames Hyprland/composability as an optional wider split within one canvas. | Composability is broader: independent worlds/panels should be capable of opening together when work crosses boundaries, without requiring every surface to be a free-form window manager. |

## Firm intent to preserve

- QMX is a daily working environment for hypothesis sourcing, data mining, experimentation, analysis, development and trading—not primarily an oversight dashboard.
- Intentionality and layout precede a comprehensive journey/story catalogue. Reference products should supply concrete feature/workflow evidence, not abstract analogies.
- Global navigation, durable open-work tabs and domain-local navigation are different layers.
- Each opened area can be “its own world”; Hermes supplies the agent-world reference, not the universal QMX layout.
- Agents are leverage across the product. They work with or without the user, locally or remotely, and must receive the exact selected object/version/context.
- The Trading Node is one integrated operational area containing the relevant Books, BMS, risk and live work. Do not duplicate those as separate worlds.
- STRATS Library is a shared, versioned knowledge/strategy surface—“our GitHub” as a mental model, not a file explorer or GitHub-sync requirement.
- QMB and QML are supporting capabilities and sources of UI data/actions, not automatic top-level destinations.
- QMX must be usable on an ordinary laptop with an ordinary keyboard. Keyboard fluency may be added but cannot be required.
- The imported visual references are partial mental models. None is approval to clone its complete UI.

## Evolving ideas—not yet decisions

- **Organizing unit:** the idea moved from functional sections/worlds, to five-role/agent layers, to departments informed by the five QMA hats. The later department framing is the strongest current direction, but not a finalized department roster.
- **Agent presence:** the conversation moved between a dedicated Agentic world, agent-aware departments and an agent mini-panel/mini-tab. These can coexist, but their modes and transitions are not specified.
- **Experimentation:** Research/data-mining and Experimentation Lab were sometimes separated and sometimes combined. StrategyQuant and QuantConnect are donors for its work model; a coding-IDE-first RoboQuant layout was rejected.
- **Project:** accepted as potentially an idea, hypothesis or ML undertaking, but Project versus Workspace and its relation to department tabs remain unresolved.
- **Extensibility:** charting and other tools should behave like available extensions/contributions where appropriate. Runtime placement, discovery and lifecycle are not yet a defined UI contract.

## Unresolved ambiguities that should be tested visually

1. Does the global mechanism open a **department**, a **shared product area**, a **specific undertaking/project**, or different types of durable tabs?
2. Are department tabs persistent peer worlds, or does one department shell contain work-item tabs underneath it?
3. When an agent is invoked from selected work, does it overlay, split, open a subordinate tab, or link to a full Hermes-style Agentic world while preserving context?
4. Are Library and Trading Node global destinations outside the department model, shared worlds reachable from every department, or both?
5. What is the minimal local navigation each department needs at laptop width? The user explicitly warned that global rail + every local rail/menu could become overbuilt.
6. Which department owns Experimentation Lab, or is it a shared cross-department world used differently by Researcher, Analyst and Developer?
7. Which five QMA groupings are product departments? Repository documentation currently says `pm` means Product Manager, while the user recalls Portfolio Manager.

## Correct next layout exercise

Do not draw two complete variants that differ only by the position of global navigation. First draw one neutral **navigation/state model** showing:

`global entry → durable domain/department tab → domain-owned overview/tools → selected work context → contextual agent mode or full agent world`

Use three concrete openings to expose the hierarchy:

- enter Research/Experimentation and open a hypothesis/experiment;
- open the same bot from STRATS Library without losing the prior work state;
- enter Trading Node and inspect the bot's Book/BMS/live binding without splitting Trading Node into duplicate destinations.

Then produce layout alternatives for the unresolved transitions: department-tab versus work-tab hierarchy, and contextual agent mini-panel/tab versus full agent-world handoff. Global rail versus global top bar can be varied inside those alternatives, but should not be the only difference.

This preserves the user's stated sequence: daily departmental intent → owned surfaces and cross-world transitions → layout → grounded journeys → components/specification.
