# Modular workspace review criteria

Status: main-agent design analysis, not an approved architecture, schema or implementation plan. Prepared alongside the Sol intent/capability audit. User explicitly requested modularity and end-user extensibility. Purpose: judge the next sketch on behavior and ownership, not just visual arrangement.

## Documented foundations and limits

- `docs/components/qma-core.md`, AD-7: Desk / Role / Quant / Agent / Subagent are distinct; Session is a run container and Profile is presentation-only grouping. UI grouping does not rename identities, grant permissions or change routing. Current `pm` Role is Product Manager, unlike the operator's Portfolio Manager perspective. This is unresolved terminology/ownership, not a permitted silent rename.
- The same document, AD-1: QMA has registered tool/adapter/hook/skill/graph/model/toolset/worker contributions, but explicitly no `ui_view` contribution in v1. `docs/AGENTS.md` records the UI contract/SDK as deferred. Existing agent extensibility is not proof of an implemented or specified extensible frontend.
- `docs/components/qmf-risk.md`, Templates as configuration artifacts: Book/BMS definitions already describe editable variables, units, edit/admission effects and immutable versions. This provides a basis for configuration editors, not a blanket permission to change operating Books/BMS through an agent.
- `docs/components/qma-core.md`, read-and-calculate surface: QMA cannot mint live/writable money-path handles or mutate operating Book/BMS/binding/control records. A shared UI view must not silently expand backend authority.

These are documentation findings, not verification that the capabilities run. No ratified component or contract is modified in this review.

## Separate kinds of modularity

| Kind | User-facing example | Design question |
|---|---|---|
| Configuration | Create a variant of a strategy or Book template using exposed parameters | Which fields are editable, what validation applies, and what new version does the edit produce? |
| Composition | Arrange a notebook, agent session, chart and results; assemble existing research steps into a reusable procedure | What is being saved: an arrangement, a tool configuration or an executable procedure? Keep their identities distinct. |
| New capability | Add a new analysis method, data integration or custom viewer | What extension contract, compatibility check, permissions and execution isolation are required? Do not imply this is already available because a drawer says Add tool. |

End-user extensibility does not mean every user writes code. Parameter editing, reusable templates and composition should expose supported choices; new executable behavior is a different responsibility even when an agent helps author it.

## Proposed UI responsibility boundaries

| Boundary | Stable responsibility | Not its responsibility |
|---|---|---|
| Global shell | Floating main menu, opened context tabs, navigation/focus and restoration conventions | A mandatory list of five departments or a universal inner grid |
| Department/work arrangement | Appropriate entry points, direct work views, agents and supporting tools for the selected purpose | A duplicate Library/database or independent security system |
| Tool/view contribution | One understandable capability and its native direct-use controls, loading/error/empty states | Owning the whole shell or quietly starting unrelated work |
| Artifact renderer | Display the selected document, notebook, chart, version or evidence record with identity and provenance | Treating displayed content as instructions or granting an agent access merely because it is visible |
| Agent/session surface | Show the actor/session, intended context, delegated work, tool activity and interaction | Replacing deterministic results, masquerading as the operator or acting on an unapproved live configuration |
| Work/run lifecycle | Distinguish pane visibility, connection status and actual local/remote work state | Equating close-tab with cancel-run, or UI presence with a running backend |

This is a responsibility map, not new component names or a concrete extension-manifest schema.

## Review situations before calling the layout modular

1. **Same object, two contexts:** open a strategy version from Library and Analysis. Both views cite the same identity. A proposed edit produces a distinct candidate; another pane does not silently switch its bound version.
2. **Change focus during an agent run:** move from a source document to a result. The agent's assigned target remains explicit; screen focus alone does not retarget its task.
3. **Add or lose a tool:** opening a new viewer does not require redesigning the department. An unavailable or incompatible extension reports its own state without pretending data is empty or discarding unrelated work. Recovery behavior and isolation mechanism need specification.
4. **Leave and return:** switching tabs restores useful work context. Disconnecting or shutting down a laptop must distinguish client closure from actual remote execution; the screenshot cannot establish remote supervision.
5. **User and agent edit concurrently:** proposed changes, applied working-copy changes and immutable evidence must be distinguishable. Conflict/version handling needs a contract, not only a visual badge.
6. **Compare a proposed BMS with operating state:** simulation and version comparison are research/calculation work. Operational activation stays at the Trading Node authority boundary. A tool copied to another department does not carry live powers with it.
7. **Smaller laptop:** the operator can focus a surface and recover hidden panes through normal controls. Optional shortcuts assist; no specialized keyboard or permanent wall of narrow panes.

## What the next image can and cannot establish

It can show a meaningful capability being used, where its inputs/evidence live, how agent assistance accompanies it, and how another tool could be opened without inventing a new department. It should retain global familiarity while allowing the chosen activity to change the interior arrangement. A floating main menu and durable tabs are meaningful references; dictation overlays, donor product menus and fictional metrics are not.

It cannot prove extensibility, extension safety, performance, restoration, simultaneous edits, remote durability or scientific validity. Those become behavioral acceptance criteria and later architecture questions. Do not turn attractive controls into claims that their backend already exists.
